"""Transitions automatiques (0.5.2) : à chaque coupe, PhilCut choisit la transition qui va avec les images et la musique.

Pour chaque raccord entre deux plans de la piste Vidéo 1 :
- le mouvement de la caméra à la fin du plan qui part et au début de celui qui arrive (corrélation de phase sur de
  petites images) : un panoramique rapide appelle un filé dans le même sens, un mouvement vertical un filé vertical ;
- la ressemblance des deux images (histogrammes) : même scène → coupe franche (la transition serait de trop) ;
  changement de lieu ou de lumière → fondu, passage par le gris ou au noir selon le style ;
- les temps forts de la musique : une coupe sur un temps fort reçoit une transition courte et percutante.
Trois styles (Punchy, Clean, Cinéma) ; tout est montré dans une liste cochable avant d'être posé, et annulable.
"""
from . import effets as E, moteur
from .langue import _
from .projet import duree_clip, fin_clip

STYLES = {"punchy": _("Punchy (réseaux)"), "clean": _("Clean minimal"), "cinema": _("Cinéma")}


def _gris(png, taille=160):
    import cv2
    import numpy as np
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None, None
    h, w = img.shape[:2]
    img = cv2.resize(img, (taille, max(2, int(taille * h / max(1, w)))))
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype("float32"), img


def _mouvement(images):
    """Déplacement moyen (dx, dy) en part de la largeur par image analysée."""
    import cv2
    dxs, dys = [], []
    for a, b in zip(images, images[1:]):
        if a is None or b is None:
            continue
        if float(a.std()) < 6 or float(b.std()) < 6:       # image unie : aucun mouvement mesurable
            continue
        (dx, dy), r = cv2.phaseCorrelate(a, b)
        if r < 0.15:                                       # corrélation trop faible : mesure peu sûre
            continue
        dxs.append(dx / a.shape[1])
        dys.append(dy / a.shape[1])
    if not dxs:
        return 0.0, 0.0
    return sum(dxs) / len(dxs), sum(dys) / len(dys)


def _ressemblance(img_a, img_b):
    import cv2
    if img_a is None or img_b is None:
        return 0.5
    ha = cv2.calcHist([cv2.cvtColor(img_a, cv2.COLOR_BGR2HSV)], [0, 1], None, [24, 16], [0, 180, 0, 256])
    hb = cv2.calcHist([cv2.cvtColor(img_b, cv2.COLOR_BGR2HSV)], [0, 1], None, [24, 16], [0, 180, 0, 256])
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    return float(cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL))


def analyser_raccord(projet, a, b, n=3, pas=0.12):
    """Mesures d'un raccord : mouvement en fin de A et début de B, ressemblance des deux images."""
    ma, mb = projet.media(a["media"]), projet.media(b["media"])
    out = {"dx": 0.0, "dy": 0.0, "ressemblance": 0.5}
    if not ma or not mb or ma.get("genre") == "image" and mb.get("genre") == "image":
        return out
    va = float(a.get("vitesse", 1.0) or 1.0)
    fin_a = float(a["src_fin"])
    deb_b = float(b["src_debut"])
    try:
        imgs_a = [] if ma.get("genre") == "image" else [_gris(moteur.image(ma["chemin"], max(0.0, fin_a - (n - k) * pas * va), 240)) for k in range(n)]
        imgs_b = [] if mb.get("genre") == "image" else [_gris(moteur.image(mb["chemin"], deb_b + k * pas, 240)) for k in range(n)]
    except moteur.ErreurMoteur:
        return out
    ga = [g for g, _c in imgs_a]
    gb = [g for g, _c in imgs_b]
    dxa, dya = _mouvement(ga)
    dxb, dyb = _mouvement(gb)
    out["dx"], out["dy"] = (dxa + dxb) / 2, (dya + dyb) / 2
    if imgs_a and imgs_b:
        out["ressemblance"] = _ressemblance(imgs_a[-1][1], imgs_b[0][1])
    return out


def temps_forts(projet):
    """Temps forts de la musique sur la timeline (première musique de la piste Musique), [] sans musique."""
    from . import rythme
    for c in sorted(projet.clips_piste("audio"), key=lambda x: x["debut"]):
        m = projet.media(c["media"])
        if not m:
            continue
        an = m.get("rythme")
        if not an:
            an = rythme.analyser(m["chemin"])
            m["rythme"] = an
        return rythme.temps_montage(c, an, forts=True)
    return []


def choisir(mesure, style, sur_temps_fort, numero):
    """(identifiant de transition ou None pour une coupe franche, durée, raison)."""
    dx, dy, ress = mesure["dx"], mesure["dy"], mesure["ressemblance"]
    vite = max(abs(dx), abs(dy))
    if vite > 0.03:                                       # la caméra bouge vite : on prolonge son geste
        if abs(dy) > abs(dx):
            return "t_file_vertical", 0.3, _("mouvement vertical rapide de la caméra")
        return "t_file", 0.3, _("panoramique rapide : le filé prolonge le geste")
    if style == "punchy":
        if sur_temps_fort:
            return ("t_zoom_avant", 0.35, _("coupe sur un temps fort de la musique")) if numero % 2 == 0 else \
                ("t_choc", 0.3, _("temps fort de la musique : impact"))
        if ress > 0.85:
            return None, 0.0, _("même scène : coupe franche, plus nerveuse")
        return ("t_glitch", 0.3, _("changement de scène, style réseaux")) if numero % 3 == 2 else \
            ("t_lisse", 0.35, _("changement de scène : poussée rapide"))
    if style == "cinema":
        if ress < 0.25:
            return "t_fondu_noir", 1.0, _("grand changement de lieu ou de lumière : passage au noir")
        if ress > 0.8:
            return None, 0.0, _("même scène : coupe franche, comme au cinéma")
        return ("t_gris", 0.9, _("changement de scène en douceur")) if numero % 2 else \
            ("t_fondu_enchaine", 1.0, _("changement de scène : fondu enchaîné lent"))
    # clean
    if ress > 0.8:
        return None, 0.0, _("même scène : coupe franche")
    if sur_temps_fort:
        return "t_lisse", 0.5, _("temps fort de la musique : poussée douce")
    return "t_fondu_enchaine", 0.6, _("changement de scène : fondu enchaîné")


def proposer(projet, style="clean", progression=None):
    """[{clip (celui qui arrive), eid, duree, raison, mesure}] pour chaque raccord de la piste Vidéo 1."""
    cs = sorted(projet.clips_piste("video"), key=lambda c: c["debut"])
    forts = temps_forts(projet)
    out = []
    for i, (a, b) in enumerate(zip(cs, cs[1:])):
        if abs(fin_clip(a) - b["debut"]) > 0.05:          # pas un raccord (trou entre les plans)
            continue
        m = analyser_raccord(projet, a, b)
        sur = any(abs(b["debut"] - t) < 0.12 for t in forts)
        eid, d, raison = choisir(m, style, sur, i)
        if eid:
            d = min(d, duree_clip(a) * 0.45, duree_clip(b) * 0.45)
        out.append({"clip": b["id"], "eid": eid, "duree": round(d, 2), "raison": raison, "mesure": m, "temps_fort": sur})
        progression and progression((i + 1) / max(1, len(cs) - 1))
    return out


def appliquer(projet, propositions):
    """Pose les transitions retenues (une seule étape d'annulation) ; une coupe franche retire la transition."""
    projet.marquer()
    n = 0
    for p in propositions:
        c = projet.clip(p["clip"])
        if not c:
            continue
        if p["eid"]:
            par = dict(E.defauts(p["eid"]))
            if "duree" in par:
                par["duree"] = p["duree"]
            c["transition"] = {"id": p["eid"], "params": par, "auto": True}
        else:
            c.pop("transition", None)
        n += 1
    projet.modifie = True
    return n
