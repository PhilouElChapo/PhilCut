"""Detourage de personne, sur ce poste.

Avec un modele de detourage coche dans Preferences > IA locale (U2-Net, execute par onnxruntime embarque dans
PhilCut, range dans son dossier) : vrai masque de la personne. A defaut, rembg s'il est installe (lancement depuis
les sources). Sans rien : masque approche a partir des visages (OpenCV), suffisant pour un halo ou un feu d'artifice.
"""
import os

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

_session = None


def _portable():
    from . import packs_ia
    return packs_ia.modele_actif("detourage") is not None and packs_ia.onnx_present()


def _rembg_present():
    try:
        import rembg, onnxruntime     # noqa: F401
        return True
    except ImportError:
        return False


def pack_present():
    return _portable() or _rembg_present()


def _rembg():
    global _session
    if _session is None:
        from rembg import new_session
        _session = new_session("u2netp")
    return _session


def _cascade():
    return cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))


def masque_image(img_bgr):
    """Masque 0..255 (H x L) de la ou des personnes."""
    H, L = img_bgr.shape[:2]
    if _portable():
        from . import packs_ia
        m = packs_ia.masque_personne(img_bgr)
        if m is not None:
            return m
    if _rembg_present():
        from rembg import remove
        rgba = remove(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), session=_rembg(), only_mask=True)
        m = np.asarray(rgba)
        return m if m.ndim == 2 else m[..., 0]
    gris = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    visages = _cascade().detectMultiScale(gris, 1.2, 4, minSize=(max(24, H // 20),) * 2)
    m = np.zeros((H, L), dtype=np.uint8)
    for (x, y, w, h) in visages:
        # tete + buste approches : une ellipse pour la tete, un rectangle arrondi pour les epaules
        cv2.ellipse(m, (x + w // 2, y + h // 2), (int(w * 0.65), int(h * 0.8)), 0, 0, 360, 255, -1)
        cv2.ellipse(m, (x + w // 2, min(H - 1, y + int(h * 2.2))), (int(w * 1.5), int(h * 1.4)), 0, 180, 360, 255, -1)
    return m


def cadrer(img, clip, L, H, t_source):
    """Même cadrage que l'export (export._cadrage) : l'image source mise au format du projet, pour que le masque tombe
    exactement sur la personne. Les bandes ajoutées (contenir) restent hors masque."""
    h, w = img.shape[:2]
    mode = (clip or {}).get("ajustement", "remplir")
    if mode == "suivi" and ((clip or {}).get("suivi_cadre") or {}).get("positions"):
        from . import suivi
        x, y, cw, ch = suivi.fenetre_source(clip["suivi_cadre"], t_source, w, h, L, H)
        return cv2.resize(img[int(y):int(y + ch), int(x):int(x + cw)], (L, H), interpolation=cv2.INTER_AREA)
    if mode in ("contenir_noir", "contenir_flou"):
        e = min(L / w, H / h)
        nw, nh = max(1, int(round(w * e))), max(1, int(round(h * e)))
        fond = np.zeros((H, L, 3), dtype=img.dtype)
        x0, y0 = (L - nw) // 2, (H - nh) // 2
        fond[y0:y0 + nh, x0:x0 + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
        return fond
    e = max(L / w, H / h)
    nw, nh = int(round(w * e)), int(round(h * e))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    x0, y0 = (nw - L) // 2, (nh - H) // 2
    return r[y0:y0 + H, x0:x0 + L]


def masques(chemin, debut, L, H, cadence, pas_images=3, clip=None):
    """masques(i) -> masque à l'image i du plan (temps du montage, vitesse comprise), recalculé toutes les
    `pas_images` images ; même cadrage que l'export."""
    cap = cv2.VideoCapture(chemin)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, debut) * 1000)
    v = float((clip or {}).get("vitesse", 1.0) or 1.0)
    cache = {"i": -1, "m": None, "img": None, "t": -1.0}

    def f(i):
        if i == cache["i"]:
            return cache["m"]
        t_voulu = debut + i / float(cadence) * v
        while cache["t"] < t_voulu - 0.5 / max(1.0, cadence):       # on avance dans la source jusqu'à l'instant voulu
            ok, fr = cap.read()
            if not ok:
                break
            cache["img"] = fr
            cache["t"] = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if cache["img"] is None:
            return cache["m"]
        if i % pas_images == 0 or cache["m"] is None:
            cache["m"] = masque_image(cadrer(cache["img"], clip, L, H, t_voulu))
        cache["i"] = i
        return cache["m"]
    f.fermer = cap.release
    return f


def sequence(chemin, debut, duree, L, H, cadence, dossier, clip=None):
    """Ecrit les masques en PNG gris (pour alphamerge) ; renvoie le motif."""
    n = int(duree * cadence)
    f = masques(chemin, debut, L, H, cadence, clip=clip)
    for i in range(n):
        m = f(i)
        if m is None:
            m = np.zeros((H, L), dtype=np.uint8)
        cv2.imwrite(os.path.join(dossier, f"{i:05d}.png"), m)
    f.fermer()
    return os.path.join(dossier, "%05d.png")
