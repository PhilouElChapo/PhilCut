"""Detourage de personne, sur ce poste.

Avec le pack « segmentation » (rembg + onnxruntime, coche dans Preferences > Effets) : vrai masque de la personne.
Sans le pack : masque approche a partir des visages (OpenCV), suffisant pour un halo ou un feu d'artifice derriere.
"""
import os

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

_session = None


def pack_present():
    try:
        import rembg, onnxruntime     # noqa: F401
        return True
    except ImportError:
        return False


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
    if pack_present():
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


def masques(chemin, debut, L, H, cadence, pas_images=3):
    """masques(i) -> masque a l'image i (recalcule toutes les `pas_images` images, lisse entre deux)."""
    cap = cv2.VideoCapture(chemin)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, debut) * 1000)
    cache = {"i": -1, "m": None, "suiv": -1}

    def f(i):
        while cache["suiv"] < i:
            ok, fr = cap.read()
            cache["suiv"] += 1
            if not ok:
                return cache["m"]
            if cache["suiv"] % pas_images == 0 or cache["m"] is None:
                fr = cv2.resize(fr, (L, H), interpolation=cv2.INTER_AREA)
                cache["m"] = masque_image(fr)
        return cache["m"]
    f.fermer = cap.release
    return f


def sequence(chemin, debut, duree, L, H, cadence, dossier):
    """Ecrit les masques en PNG gris (pour alphamerge) ; renvoie le motif."""
    n = int(duree * cadence)
    f = masques(chemin, debut, L, H, cadence)
    for i in range(n):
        m = f(i)
        if m is None:
            m = np.zeros((H, L), dtype=np.uint8)
        cv2.imwrite(os.path.join(dossier, f"{i:05d}.png"), m)
    f.fermer()
    return os.path.join(dossier, "%05d.png")
