"""Tri des rushes (0.9.49) : ce qui cloche dans chaque rush, calculé sur ce poste, sans IA ni envoi.

Proposé à l'import (Préférences › Import : proposer, toujours, jamais), relancé par clic droit dans la bibliothèque, le
bouton IA ou « trie les rushes ». Pour chaque média, `media["tri"]` garde les mesures et la liste des pastilles :
- doublon : même fichier (empreinte) ou mêmes images et même durée qu'un autre rush ;
- tremblé : la caméra sautille (secousses rapides du cadre, un panoramique régulier n'en est pas) ;
- flou : peu de détails nets sur la plupart des images ;
- son : saturé (crête écrêtée), très faible, ou vent probable (grondement grave) ;
- silences : de longs blancs (au moins le tiers du rush, ou un blanc de plus de 5 s).
Rien n'est retiré : les pastilles disent, vous décidez. Les seuils sont volontairement prudents.
"""
import os

from . import moteur
from .langue import _

VERSION_TRI = 2                          # 2 : tremblement par flux optique (0.9.51)
# pastille → (lettre, couleur, libellé) ; la lettre se lit sur la vignette, le libellé dans l'info-bulle
PASTILLES = {
    "doublon": ("D", "#a56bff", _("Doublon")),
    "tremble": ("T", "#ff9f1a", _("Tremblé")),
    "flou": ("F", "#ff9f1a", _("Flou")),
    "son": ("S", "#ff4f4f", _("Son raté")),
    "silences": ("…", "#8a94a6", _("Silences")),
}
TAUX = 48000                             # son lu à sa cadence native : l'écrêtage reste visible
LARG, HAUT = 160, 90                     # images réduites pour les mesures de mouvement


# ---------------------------------------------------------------- lecture des images et du son
def _images_grises(chemin, duree, n_max=120, cadence=8.0, largeur=LARG, hauteur=HAUT, debut=0.0):
    """Images grises (numpy) à `cadence` par seconde, au plus n_max, à partir de `debut`."""
    import numpy as np
    duree_lue = min(max(0.5, duree - debut), n_max / cadence)
    try:
        brut = moteur.sortie(["-ss", f"{debut:.3f}", "-t", f"{duree_lue:.3f}", "-i", chemin, "-an",
                              "-vf", f"fps={cadence},scale={largeur}:{hauteur},format=gray", "-f", "rawvideo", "pipe:1"], delai=300)
    except moteur.ErreurMoteur:
        return []
    t = largeur * hauteur
    n = len(brut) // t
    return [np.frombuffer(brut[i * t:(i + 1) * t], dtype=np.uint8).reshape(hauteur, largeur).astype("float32") for i in range(n)]


def tremblement(images, cadence=12.0):
    """Secousses du cadre, en part de la largeur : déplacement global entre deux images (flux optique, médiane), cumulé
    en trajectoire ; on mesure l'écart entre cette trajectoire et la même lissée sur une demi-seconde. Un panoramique
    ou une marche régulière suit la trajectoire lissée ; une main qui tremble ou le pas qui secoue s'en écarte."""
    import cv2
    import numpy as np
    pas = []
    for a, b in zip(images, images[1:]):
        if float(a.std()) < 4 or float(b.std()) < 4:
            pas.append((0.0, 0.0))
            continue
        a8, b8 = a.astype(np.uint8), b.astype(np.uint8)
        dx = dy = None
        pts = cv2.goodFeaturesToTrack(a8, 120, 0.01, 6)      # points suivis d'une image à l'autre (comme un stabilisateur)
        if pts is not None and len(pts) >= 8:
            nouv, ok, _e = cv2.calcOpticalFlowPyrLK(a8, b8, pts, None, winSize=(21, 21), maxLevel=3)
            ok = ok.reshape(-1).astype(bool)
            if ok.sum() >= 8:
                m, _in = cv2.estimateAffinePartial2D(pts[ok], nouv[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
                if m is not None:
                    dx, dy = float(m[0, 2]), float(m[1, 2])
        if dx is None:
            (dx, dy), _r = cv2.phaseCorrelate(a, b)
        pas.append((dx / a.shape[1], dy / a.shape[1]))
    if len(pas) < 8:
        return 0.0
    chemin = np.cumsum(np.array(pas), axis=0)
    n = max(3, int(cadence / 2) | 1)
    noyau = np.ones(n) / n
    lisse = np.stack([np.convolve(np.pad(chemin[:, i], (n // 2, n // 2), mode="edge"), noyau, mode="valid") for i in (0, 1)], axis=1)
    ecart = chemin - lisse
    return float(np.sqrt((ecart ** 2).sum(axis=1)).mean())


def nettete(chemin, duree, fiche=None, n=5):
    """Netteté médiane (variance du laplacien sur des images de 640 pixels de large)."""
    import cv2
    import numpy as np
    valeurs = []
    for i in range(n):
        t = duree * (i + 0.5) / n if duree else 0.0
        try:
            png = moteur.image(chemin, t, 640, fiche)
        except moteur.ErreurMoteur:
            continue
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None or float(img.std()) < 8:              # image noire ou unie : elle ne dit rien de la netteté
            continue
        valeurs.append(float(cv2.Laplacian(img, cv2.CV_64F).var()))
    return float(np.median(valeurs)) if valeurs else None


def empreinte_visuelle(chemin, duree, fiche=None):
    """Quatre petites images moyennées en 8×8 bits : deux copies du même rush (réencodées, renommées) se ressemblent."""
    import cv2
    import numpy as np
    bits = []
    for f in (0.2, 0.4, 0.6, 0.8):
        try:
            png = moteur.image(chemin, duree * f if duree else 0.0, 160, fiche)
        except moteur.ErreurMoteur:
            return None
        img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        p = cv2.resize(img, (8, 8), interpolation=cv2.INTER_AREA).astype("float32")
        bits.append("".join("1" if x > p.mean() else "0" for x in p.flatten()))
    return "".join(bits)


def _distance(a, b):
    return sum(x != y for x, y in zip(a, b)) if a and b and len(a) == len(b) else 999


def son(chemin):
    """Mesures du son : part d'échantillons écrêtés, niveau moyen (dB), part du grave sous 120 Hz (vent)."""
    import numpy as np
    try:
        brut = moteur.sortie(["-t", "900", "-i", chemin, "-vn", "-ac", "1", "-ar", str(TAUX), "-f", "s16le", "pipe:1"], delai=600)
    except moteur.ErreurMoteur:
        return None
    a = np.frombuffer(brut[: len(brut) - len(brut) % 2], dtype=np.int16).astype("float32")
    if a.size < TAUX // 10:
        return None
    crete = float(np.abs(a).max())
    if crete < 33:                                            # moins de -60 dB partout : piste muette
        return {"muet": True}
    haut = np.abs(a) >= 32000                                  # écrêtage : au moins trois échantillons de suite collés au maximum
    ecretes = float((haut[:-2] & haut[1:-1] & haut[2:]).mean())
    rms = float(np.sqrt((a ** 2).mean()))
    db = 20 * np.log10(max(rms, 1.0) / 32768.0)
    # vent : énergie sous 120 Hz par blocs d'une seconde, part médiane
    parts = []
    for i in range(0, a.size - TAUX, TAUX * 3):              # une seconde sur trois suffit
        s = np.abs(np.fft.rfft(a[i:i + TAUX])) ** 2             # 1 Hz par case
        tot = float(s[20:].sum())                             # au-dessus de 20 Hz
        if tot > 0:
            parts.append(float(s[20:120].sum()) / tot)
    return {"muet": False, "ecretes": round(ecretes, 5), "db": round(float(db), 1), "grave": round(float(np.median(parts)) if parts else 0.0, 3)}


# ---------------------------------------------------------------- verdicts
SEUIL_TREMBLE = 0.006      # écart moyen à la trajectoire lissée (part de la largeur) ; marche douce ≈ 0,003, pas qui secoue ≈ 0,015
SEUIL_FLOU = 45.0          # variance du laplacien (640 px)
SEUIL_ECRETE = 0.0002      # 0,02 % d'échantillons pris dans un plateau écrêté
SEUIL_FAIBLE = -45.0       # dB
SEUIL_VENT = 0.55          # plus de la moitié de l'énergie sous 120 Hz


def verdict(mesures):
    """Les pastilles et, pour chacune, la phrase qui l'explique."""
    out = {}
    if mesures.get("doublon_de"):
        out["doublon"] = _("Même rush que « {n} »", n=mesures.get("doublon_nom", ""))
    if (mesures.get("tremblement") or 0) > SEUIL_TREMBLE:
        out["tremble"] = _("La caméra tremble : Image du plan › Stabiliser peut le corriger")
    if mesures.get("nettete") is not None and mesures["nettete"] < SEUIL_FLOU:
        out["flou"] = _("Peu de détails nets : mise au point ratée ou bougé")
    s = mesures.get("son") or {}
    if s and not s.get("muet"):
        raisons = []
        if s.get("ecretes", 0) > SEUIL_ECRETE:
            raisons.append(_("saturé (le son crache)"))
        if s.get("db", 0) < SEUIL_FAIBLE:
            raisons.append(_("très faible"))
        if s.get("grave", 0) > SEUIL_VENT:
            raisons.append(_("vent probable (grondement grave)"))
        if raisons:
            out["son"] = _("Son {r}", r=", ".join(raisons))
    sil = mesures.get("silences") or []
    duree = mesures.get("duree") or 0
    total = sum(b - a for a, b in sil)
    if sil and duree and (total >= duree / 3 or any(b - a > 5 for a, b in sil)):
        out["silences"] = _("{n} blanc(s), {s} s en tout sur {d} s", n=len(sil), s=int(round(total)), d=int(round(duree)))
    return out


def mesurer(media, arret=lambda: False):
    """Toutes les mesures d'un média (sans le doublon, qui se juge sur l'ensemble)."""
    chemin, fiche = media.get("chemin", ""), media.get("fiche") or {}
    duree = float(fiche.get("duree") or 0)
    genre = media.get("genre")
    out = {"version": VERSION_TRI, "duree": duree}
    if genre == "video":
        imgs = _images_grises(chemin, duree, n_max=180, cadence=12.0, debut=min(1.0, duree * 0.05))
        if arret():
            raise InterruptedError()
        out["tremblement"] = round(tremblement(imgs), 4)
        out["nettete"] = nettete(chemin, duree, fiche)
        out["visuel"] = empreinte_visuelle(chemin, duree, fiche)
    elif genre == "image":
        import cv2
        img = cv2.imread(chemin, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            h, w = img.shape[:2]
            img = cv2.resize(img, (640, max(2, int(640 * h / max(1, w)))))
            out["nettete"] = float(cv2.Laplacian(img, cv2.CV_64F).var()) if float(img.std()) >= 8 else None
            p = cv2.resize(img, (8, 8), interpolation=cv2.INTER_AREA).astype("float32")
            out["visuel"] = "".join("1" if x > p.mean() else "0" for x in p.flatten()) * 4
    if arret():
        raise InterruptedError()
    if genre in ("video", "audio") and (fiche.get("audio") is None or fiche.get("audio")):
        out["son"] = son(chemin)
        if out["son"] and not out["son"].get("muet"):
            seuil = int(max(-65, min(-42, out["son"]["db"] - 18)))   # un rush enregistré bas n'est pas « tout en silence »
            out["silences"] = [(round(a, 2), round(b, 2)) for a, b in moteur.silences(chemin, seuil, 2.0)]
    return out


def trier(projet, ids=None, progression=None, arret=lambda: False):
    """Mesure les médias (tous, ou `ids`), puis repère les doublons ; écrit media["tri"]. Renvoie {id: pastilles}."""
    medias = [m for m in projet.medias if (ids is None or m["id"] in ids) and m.get("genre") in ("video", "image", "audio")]
    resultats = {}
    for i, m in enumerate(medias):
        if arret():
            raise InterruptedError()
        if progression:
            progression(i / max(1, len(medias)), m.get("nom", ""))
        anc = m.get("tri") or {}
        if anc.get("version") == VERSION_TRI and anc.get("empreinte") == m.get("empreinte") and "mesures" in anc:
            mes = anc["mesures"]                               # déjà mesuré : rien à refaire
        else:
            mes = mesurer(m, arret)
        resultats[m["id"]] = mes
    # doublons sur l'ensemble du projet : même empreinte de fichier, ou mêmes images et même durée
    tous = {m["id"]: m for m in projet.medias}
    mes_de = {k: v for k, v in resultats.items()}
    for m in projet.medias:
        if m["id"] not in mes_de and (m.get("tri") or {}).get("mesures"):
            mes_de[m["id"]] = m["tri"]["mesures"]
    ordre = [m["id"] for m in projet.medias]
    for k in resultats:
        mes = resultats[k]
        mes.pop("doublon_de", None)
        mes.pop("doublon_nom", None)
        m = tous[k]
        for autre in ordre:
            if autre == k:
                break                                          # le premier importé garde son rang : seul le suivant est « doublon »
            o, mo = tous[autre], mes_de.get(autre) or {}
            if o.get("genre") != m.get("genre"):
                continue
            meme_fichier = m.get("empreinte") and m.get("empreinte") == o.get("empreinte")
            d1, d2 = float(mes.get("duree") or 0), float(mo.get("duree") or 0)
            meme_duree = abs(d1 - d2) <= max(0.3, 0.01 * max(d1, d2))
            n1, n2 = mes.get("nettete"), mo.get("nettete")
            meme_nettete = not (n1 and n2) or max(n1, n2) / max(1e-3, min(n1, n2)) < 3      # une version floue n'est pas une copie
            s1, s2 = mes.get("son") or {}, mo.get("son") or {}
            meme_son = not (s1.get("db") is not None and s2.get("db") is not None) or abs(s1["db"] - s2["db"]) < 6
            t1, t2 = mes.get("tremblement") or 0, mo.get("tremblement") or 0
            meme_mouvement = abs(t1 - t2) < SEUIL_TREMBLE / 2       # une prise tremblée n'est pas la copie d'une prise stable
            if meme_fichier or (mes.get("visuel") and meme_duree and meme_nettete and meme_son and meme_mouvement
                                and _distance(mes.get("visuel"), mo.get("visuel")) <= 12):
                mes["doublon_de"], mes["doublon_nom"] = autre, o.get("nom", "")
                break
    out = {}
    for k, mes in resultats.items():
        v = verdict(mes)
        tous[k]["tri"] = {"version": VERSION_TRI, "empreinte": tous[k].get("empreinte"), "mesures": mes, "pastilles": v}
        out[k] = v
    if progression:
        progression(1.0, "")
    return out


def a_trier(projet):
    """Les médias pas encore triés (ou modifiés depuis)."""
    return [m["id"] for m in projet.medias if m.get("genre") in ("video", "image", "audio") and
            ((m.get("tri") or {}).get("version") != VERSION_TRI or (m.get("tri") or {}).get("empreinte") != m.get("empreinte"))]


def pastilles(media):
    return (media.get("tri") or {}).get("pastilles") or {}


def texte(media):
    """Le résumé lisible (info-bulle, recherche) : « Flou : …  ·  Son raté : … »."""
    return "\n".join(f"{PASTILLES[k][2]} : {v}" for k, v in sorted(pastilles(media).items()) if k in PASTILLES)


def mesures_lisibles(media):
    """Les chiffres mesurés (pour régler les seuils sur de vrais rushes) : tremblement, netteté, son."""
    m = (media.get("tri") or {}).get("mesures") or {}
    out = []
    if m.get("tremblement") is not None:
        out.append(_("tremblement {v} (seuil {s})", v=f"{m['tremblement'] * 1000:.1f}", s=f"{SEUIL_TREMBLE * 1000:.1f}"))
    if m.get("nettete") is not None:
        out.append(_("netteté {v} (seuil {s})", v=int(m["nettete"]), s=int(SEUIL_FLOU)))
    so = m.get("son") or {}
    if so.get("muet"):
        out.append(_("son muet"))
    elif so:
        out.append(_("son {d} dB, écrêté {e} ‰, grave {g} %", d=so.get("db"), e=f"{so.get('ecretes', 0) * 1000:.2f}",
                     g=int(so.get("grave", 0) * 100)))
    return " · ".join(out)


def dessiner(pixmap, media):
    """Les pastilles en haut à gauche de la vignette du média (lettre blanche sur rond de couleur)."""
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
    p_ = pastilles(media)
    if not p_ or pixmap.isNull():
        return pixmap
    pm = QPixmap(pixmap)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    d = max(15, int(pm.width() * 0.15))            # la vignette est réduite à l'affichage : la pastille suit sa taille
    f = QFont()
    f.setPixelSize(int(d * 0.68))
    f.setBold(True)
    p.setFont(f)
    x = d * 0.2
    for k in ("doublon", "flou", "silences", "son", "tremble"):
        if k not in p_:
            continue
        lettre, couleur, _lib = PASTILLES[k]
        rc = QRectF(x, d * 0.2, d, d)
        p.setPen(QColor(0, 0, 0, 160))
        p.setBrush(QColor(couleur))
        p.drawEllipse(rc)
        p.setPen(QColor("#ffffff"))
        p.drawText(rc, Qt.AlignCenter, lettre)
        x += d * 1.15
    p.end()
    return pm
