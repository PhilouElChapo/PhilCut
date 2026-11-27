"""Multicaméra (1.4.2, choix de Philippe le 27/11 après la comparaison avec FilmCraft).

Jusqu'à 4 rushes du même moment (GoPro du cockpit, téléphone, lunettes…) sont calés entre eux :
- par le son d'abord : FFmpeg extrait le son de chaque rush, NumPy cherche le décalage par corrélation croisée ;
- sinon par l'heure de création des fichiers ;
- sinon à la main (chaque décalage reste modifiable).
Le « plan multicaméra » posé sur la timeline est un plan normal (l'angle 1 au départ) ; une seule source son court
dessous, sur sa propre piste. Couper à un angle (mosaïque, touches 1 à 4) ou « Changer d'angle » au clic droit ne fait
que changer le rush d'un plan : chaque coupe reste un plan normal, re-modifiable, et tout se défait d'un seul Annuler.
L'assistant peut proposer un premier montage des angles (mouvement de l'image, durée des plans), sur ce poste.
"""
import datetime, os, tempfile

from .langue import _

MAX_ANGLES = 4
TAUX = 4000                 # Hz : assez pour caler à 1/4000 s près, assez léger pour une heure de vol
FENETRE_MAX = 20 * 60       # s : le son comparé (les 20 premières minutes de chaque rush suffisent)


# ------------------------------------------------------------------ synchronisation
def _son(chemin, duree=FENETRE_MAX):
    """Le son d'un rush, mono, TAUX Hz, en nombres (NumPy) ; None s'il n'a pas de son."""
    import numpy as np
    from . import moteur
    try:
        brut = moteur.sortie(["-i", chemin, "-vn", "-t", f"{duree:.0f}", "-ac", "1", "-ar", str(TAUX), "-f", "f32le", "-"], delai=900)
    except moteur.ErreurMoteur:
        return None
    x = np.frombuffer(brut, dtype=np.float32)
    if x.size < TAUX or float(np.abs(x).max() if x.size else 0) < 1e-4:
        return None
    return x


def _enveloppe(x):
    """Son ramené à ses variations (moyenne retirée, niveau égalisé) : deux micros différents se ressemblent mieux."""
    import numpy as np
    x = x - x.mean()
    return x / (np.sqrt(np.mean(x * x)) + 1e-9)


def correlation(a, b):
    """(décalage en s, confiance) : b commence `décalage` secondes après a. Confiance : hauteur du pic sur le bruit."""
    import numpy as np
    a, b = _enveloppe(a), _enveloppe(b)
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    c = np.concatenate((c[-(len(b) - 1):], c[:len(a)]))           # décalages de -(len(b)-1) à len(a)-1
    k = int(np.argmax(c))
    pic = float(c[k])
    bruit = float(np.median(np.abs(c))) + 1e-9
    return (k - (len(b) - 1)) / TAUX, pic / bruit


def _date(fiche):
    t = (fiche or {}).get("date") or ""
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def synchroniser(medias, progression=None, arret=lambda: False):
    """[{media, nom, decalage (s, sur l'axe commun), methode: son|heure|main, confiance}] pour 2 à 4 médias vidéo.
    L'angle de référence est le premier qui a du son ; les décalages sont ramenés pour que le plus tôt soit à 0."""
    if not 2 <= len(medias) <= MAX_ANGLES:
        raise ValueError(_("Choisissez de 2 à {n} vidéos du même moment.", n=MAX_ANGLES))
    av = lambda f, t="": progression and progression(f, t)
    sons = []
    for k, m in enumerate(medias):
        if arret():
            raise InterruptedError
        av(0.7 * k / len(medias), _("Lecture du son de « {n} »", n=m.get("nom", "")))
        sons.append(_son(m["chemin"]))
    ref = next((k for k, s in enumerate(sons) if s is not None), None)
    dates = [_date(m.get("fiche")) for m in medias]
    out = []
    for k, m in enumerate(medias):
        r = {"media": m["id"], "nom": m.get("nom", ""), "decalage": 0.0, "methode": "main", "confiance": 0.0}
        if k == ref:
            r["methode"] = "son"
            r["confiance"] = 99.0
        elif ref is not None and sons[k] is not None:
            av(0.7 + 0.3 * k / len(medias), _("Calage de « {n} » par le son", n=m.get("nom", "")))
            d, conf = correlation(sons[ref], sons[k])
            if conf >= 8:                                           # pic net : calé par le son
                r.update(decalage=d, methode="son", confiance=round(conf, 1))
        if r["methode"] == "main" and dates[k] is not None and ref is not None and dates[ref] is not None:
            r.update(decalage=dates[k] - dates[ref], methode="heure")
        out.append(r)
    mini = min(r["decalage"] for r in out)
    for r in out:
        r["decalage"] = round(r["decalage"] - mini, 4)
    av(1.0, _("Angles calés"))
    return out


# ------------------------------------------------------------------ plan multicaméra
def creer(projet, angles, son=None, debut=None):
    """Pose le plan multicaméra : l'angle 1 sur la piste vidéo (muet), et la source son choisie sur une piste audio,
    calée sur le même axe. Renvoie l'identifiant du multicaméra. `angles` : la sortie de synchroniser (modifiée ou non)."""
    from . import projet as P
    import uuid
    mc_id = uuid.uuid4().hex[:8]
    duree = {a["media"]: float((projet.media(a["media"]).get("fiche") or {}).get("duree") or 0) for a in angles}
    debut_axe = min(a["decalage"] for a in angles)
    fin_axe = max(a["decalage"] + duree[a["media"]] for a in angles)
    projet.d.setdefault("multicams", {})[mc_id] = {
        "angles": [{"media": a["media"], "nom": a.get("nom", ""), "decalage": float(a["decalage"])} for a in angles[:MAX_ANGLES]],
        "son": son or angles[0]["media"]}
    t0 = projet.fin_piste("video") if debut is None else float(debut)
    a1 = angles[0]
    c = projet.ajouter_clip(a1["media"], "video", t0 + a1["decalage"] - debut_axe, 0.0, duree[a1["media"]])
    c.update(multicam=mc_id, angle=0, muet=True)
    projet.ranger("video")
    origine = c["debut"] - a1["decalage"]                    # instant de la timeline où commence l'axe commun
    c["origine_mc"] = origine
    # la source son, sur sa propre piste audio : sous tous les angles, sans saut à chaque coupe
    s = next((a for a in angles if a["media"] == (son or a1["media"])), a1)
    piste = next((p for p in projet.pistes_audio() if not projet.clips_piste(p)), None) or projet.ajouter_piste("audio")
    d0 = origine + s["decalage"]
    cs = projet.ajouter_clip(s["media"], piste, max(0.0, d0), max(0.0, -d0), duree[s["media"]])
    cs.update(multicam=mc_id, son_multicam=True)
    projet.renommer_piste(piste, _("Son multicaméra"))
    projet.modifie = True
    return mc_id


def infos(projet, clip):
    """Le multicaméra d'un plan, s'il en vient : son dict (angles, son), sinon None."""
    return (projet.d.get("multicams") or {}).get((clip or {}).get("multicam") or "")


def angle_couvre(projet, mc, k, u0, u1):
    """L'angle k a-t-il des images sur [u0, u1] de l'axe commun ?"""
    a = mc["angles"][k]
    d = float((projet.media(a["media"]).get("fiche") or {}).get("duree") or 0)
    return a["decalage"] - 0.02 <= u0 and u1 <= a["decalage"] + d + 0.02


def changer_angle(projet, clip, k):
    """Le plan montre l'angle k sur le même moment. Renvoie vrai si fait ; faux si l'angle n'a pas d'image à ce moment."""
    mc = infos(projet, clip)
    if not mc or not 0 <= k < len(mc["angles"]) or k == clip.get("angle"):
        return False
    cur = mc["angles"][int(clip.get("angle") or 0)]
    u0 = clip["src_debut"] + cur["decalage"]
    u1 = clip["src_fin"] + cur["decalage"]
    if not angle_couvre(projet, mc, k, u0, u1):
        return False
    nv = mc["angles"][k]
    m = projet.media(nv["media"])
    clip.update(media=nv["media"], src_debut=round(u0 - nv["decalage"], 4), src_fin=round(u1 - nv["decalage"], 4), angle=k,
                nom=m.get("nom", ""), muet=True)
    projet.modifie = True
    return True


def couper_angle(projet, t, k):
    """Coupe le plan multicaméra à l'instant t et montre l'angle k à partir de là (jusqu'à la coupe suivante).
    Renvoie le plan qui montre l'angle k, ou None."""
    from .projet import fin_clip
    c = next((x for x in projet.clips_piste("video") if x.get("multicam") and x["debut"] - 0.01 <= t < fin_clip(x) - 0.01), None)
    if c is None:
        return None
    mc = infos(projet, c)
    if not mc or not 0 <= k < len(mc["angles"]):
        return None
    d_cur = mc["angles"][int(c.get("angle") or 0)]["decalage"]
    v = float(c.get("vitesse") or 1.0)
    if k != c.get("angle"):
        a = mc["angles"][k]
        fin_k = a["decalage"] + float((projet.media(a["media"]).get("fiche") or {}).get("duree") or 0)
        u_t = c["src_debut"] + d_cur + (t - c["debut"]) * v
        if not a["decalage"] - 0.02 <= u_t < fin_k - 0.1:
            return None                              # rien n'est coupé si l'angle ne filme pas à ce moment
        if c["src_fin"] + d_cur > fin_k + 0.02:      # l'angle s'arrête avant la fin du plan : la suite garde l'angle d'avant
            projet.couper(c["id"], c["debut"] + (fin_k - d_cur - c["src_debut"]) / v)
    if c["debut"] + 0.04 < t:
        c = projet.couper(c["id"], t) or c
    return c if changer_angle(projet, c, k) or c.get("angle") == k else None


def activite(dossier, n_angles):
    """Le mouvement de chaque angle dans le temps, lu sur les images de la mosaïque : {k: [(t, mouvement 0..1)]}."""
    import numpy as np
    from PySide6.QtGui import QImage
    out = {}
    for k in range(n_angles):
        imgs = images_angle(dossier, k)
        prec, pts = None, []
        for t, ch in imgs:
            q = QImage(ch).convertToFormat(QImage.Format_Grayscale8).scaled(48, 27)
            b = q.constBits()
            a = np.frombuffer(b, dtype=np.uint8, count=q.bytesPerLine() * q.height()).reshape(q.height(), q.bytesPerLine())[:, :48]
            a = a.astype(np.float32)
            pts.append((t, float(np.mean(np.abs(a - prec))) / 255.0 if prec is not None else 0.0))
            prec = a
        out[k] = pts
    return out


def proposer(projet, mc_id, dossier, mini=3.0, maxi=10.0):
    """Premier montage des angles, sur ce poste : [(t_debut sur l'axe, angle)]. Un plan dure de `mini` à `maxi` secondes ;
    à chaque coupe, on prend l'angle qui bouge le plus à ce moment (sans reprendre le même), parmi ceux qui ont des images."""
    mc = projet.d["multicams"][mc_id]
    n = len(mc["angles"])
    act = activite(dossier, n)
    durees = [float((projet.media(a["media"]).get("fiche") or {}).get("duree") or 0) for a in mc["angles"]]
    u_deb = min(a["decalage"] for a in mc["angles"])
    u_fin = max(a["decalage"] + d for a, d in zip(mc["angles"], durees))

    def mouvement(k, u0, u1):
        a = mc["angles"][k]
        vals = [v for t, v in act.get(k, []) if u0 <= t + a["decalage"] <= u1]
        return sum(vals) / len(vals) if vals else 0.0

    plans, u, cour = [], u_deb, None
    pas = (mini + maxi) / 2
    while u < u_fin - 0.5:
        u1 = min(u_fin, u + pas)
        dispo = [k for k in range(n) if angle_couvre(projet, mc, k, u, u1)]
        if not dispo:
            dispo = [k for k in range(n) if mc["angles"][k]["decalage"] <= u < mc["angles"][k]["decalage"] + durees[k]]
        if not dispo:
            u = u1
            continue
        choix = sorted(dispo, key=lambda k: (k == cour, -mouvement(k, u, u1)))[0]
        if choix != cour:
            plans.append((round(u, 3), choix))
            cour = choix
        # plan plus court si l'image bouge beaucoup, plus long si elle est calme
        m = mouvement(choix, u, u1)
        pas = max(mini, min(maxi, maxi - (maxi - mini) * min(1.0, m * 25)))
        u = u1
    return plans


def appliquer_proposition(projet, mc_id, plans):
    """Coupe le plan multicaméra selon la proposition (instants de l'axe commun). Renvoie le nombre de coupes faites."""
    clips = [c for c in projet.clips_piste("video") if c.get("multicam") == mc_id]
    if not clips:
        return 0
    origine = float(clips[0].get("origine_mc") or 0.0)
    n = 0
    for u, k in plans:
        if couper_angle(projet, origine + u, k) is not None:
            n += 1
    return n


# ------------------------------------------------------------------ images de la mosaïque
def dossier_images(projet, mc_id):
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "multicam", mc_id)
    os.makedirs(d, exist_ok=True)
    return d


def preparer_images(projet, mc_id, progression=None, arret=lambda: False):
    """Petites images de chaque angle (2 par seconde, une par seconde au-delà de 20 min) : la mosaïque suit la ligne
    rouge sans rien décoder pendant la lecture. Déjà faites : rien n'est refait."""
    from . import moteur
    mc = projet.d["multicams"][mc_id]
    d = dossier_images(projet, mc_id)
    for k, a in enumerate(mc["angles"]):
        if arret():
            raise InterruptedError
        sous = os.path.join(d, f"angle{k}")
        if os.path.exists(os.path.join(sous, "fini")):
            continue
        os.makedirs(sous, exist_ok=True)
        m = projet.media(a["media"])
        duree = float((m.get("fiche") or {}).get("duree") or 0)
        fps = 2 if duree <= 20 * 60 else 1
        moteur.lancer(["-y", "-i", m["chemin"], "-an", "-vf", f"fps={fps},scale=320:-2", "-q:v", "6",
                       os.path.join(sous, "%06d.jpg")], progression=progression and (lambda f, k=k: progression(
                           (k + f) / len(mc["angles"]), _("Images de l'angle {n}", n=k + 1))), duree=duree, arret=arret)
        with open(os.path.join(sous, "fini"), "w") as f:
            f.write(str(fps))
    return d


def images_angle(dossier, k):
    """[(t dans le rush, chemin)] des images d'un angle."""
    sous = os.path.join(dossier, f"angle{k}")
    try:
        fps = float(open(os.path.join(sous, "fini")).read().strip() or 2)
    except (OSError, ValueError):
        return []
    noms = sorted(n for n in os.listdir(sous) if n.endswith(".jpg"))
    return [((i + 0.5) / fps, os.path.join(sous, n)) for i, n in enumerate(noms)]


def image_a(dossier, mc, k, u):
    """L'image de l'angle k à l'instant u de l'axe commun (ou None : pas d'image à ce moment)."""
    a = mc["angles"][k]
    sous = os.path.join(dossier, f"angle{k}")
    try:
        fps = float(open(os.path.join(sous, "fini")).read().strip() or 2)
    except (OSError, ValueError):
        return None
    i = int((u - a["decalage"]) * fps)
    if i < 0:
        return None
    ch = os.path.join(sous, f"{i + 1:06d}.jpg")
    return ch if os.path.exists(ch) else None
