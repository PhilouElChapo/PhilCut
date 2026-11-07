"""Retirer le fond d'une image (0.9.5) : un JPG (logo sur fond blanc, photo d'un objet ou d'une personne) devient un
PNG transparent, sur ce poste, sans envoyer l'image nulle part. L'original n'est jamais modifié : on travaille sur
une copie.

Méthodes :
- « fond uni » (logo, dessin, capture sur fond blanc ou de couleur) : la couleur des bords est retirée par remplissage
  depuis les bords, avec une tolérance réglable ; les bords du sujet sont adoucis ;
- « sujet d'une photo » : modèle de détourage installé (personnes) sinon OpenCV GrabCut sur toute l'image ;
- « automatique » : fond uni si les bords de l'image sont d'une seule couleur, sinon sujet d'une photo.
"""
import os

import numpy as np

from .langue import _

try:
    import cv2
except ImportError:      # pragma: no cover
    cv2 = None

METHODES = {"auto": _("Automatique"), "uni": _("Fond uni (logo, dessin, fond blanc)"), "photo": _("Sujet d'une photo (objet, personne)")}


def lire(chemin):
    """Image BGRA (le canal alpha existant est gardé)."""
    img = cv2.imdecode(np.fromfile(chemin, np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(_("Image illisible : {c}", c=os.path.basename(chemin)))
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    elif img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img


def a_deja_transparence(img):
    return img.shape[2] == 4 and int(img[..., 3].min()) < 250


def _bords(img):
    h, w = img.shape[:2]
    b = max(2, min(h, w) // 50)
    return np.concatenate([img[:b].reshape(-1, 3), img[-b:].reshape(-1, 3), img[:, :b].reshape(-1, 3), img[:, -b:].reshape(-1, 3)])


def fond_uni_probable(img):
    """Les bords sont-ils d'une seule couleur (logo, capture) ?"""
    px = _bords(img[..., :3]).astype(np.float32)
    med = np.median(px, axis=0)
    return float(np.mean(np.linalg.norm(px - med, axis=1) < 28)) > 0.85


def _fond_uni(bgr, tolerance, enferme=False):
    h, w = bgr.shape[:2]
    px = _bords(bgr).astype(np.float32)
    med = np.median(px, axis=0)
    # pixels proches de la couleur du fond ET reliés aux bords (on ne troue pas le blanc à l'intérieur d'un logo)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    ref = cv2.cvtColor(np.uint8([[med]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
    dist = np.linalg.norm(lab - ref, axis=2)
    proche = (dist < tolerance).astype(np.uint8)
    n, etiquettes = cv2.connectedComponents(proche, connectivity=4)
    bordure = set(np.unique(np.concatenate([etiquettes[0], etiquettes[-1], etiquettes[:, 0], etiquettes[:, -1]])).tolist())
    fond = np.isin(etiquettes, [e for e in bordure if e != 0]) & (proche > 0)
    if enferme:                  # aussi le fond enfermé : intérieur des lettres, d'un anneau (assez grand pour ne pas trouer les reflets)
        for e in range(1, n):
            zone_e = etiquettes == e
            if e not in bordure and zone_e.sum() > 0.0015 * h * w:
                fond |= zone_e
    alpha = np.where(fond, 0, 255).astype(np.uint8)
    # bord adouci : transition selon la distance à la couleur du fond (anti-crénelage, pas de liseré blanc)
    zone = cv2.dilate((alpha == 0).astype(np.uint8), np.ones((3, 3), np.uint8)) & (alpha == 255)
    douce = np.clip((dist - tolerance * 0.6) / (tolerance * 0.8 + 1e-6) * 255, 0, 255).astype(np.uint8)
    alpha = np.where(zone > 0, np.minimum(alpha, douce), alpha)
    return alpha


def _photo(bgr):
    try:
        from . import segmentation
        if segmentation._portable():
            m = segmentation.masque_image(bgr)
            if m is not None and (m > 127).mean() > 0.03:
                return m
    except Exception:          # noqa: BLE001 : à défaut, GrabCut
        pass
    h, w = bgr.shape[:2]
    k = min(1.0, 640 / max(h, w))
    petit = cv2.resize(bgr, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k < 1 else bgr
    ph, pw = petit.shape[:2]
    rect = (int(pw * 0.03), int(ph * 0.03), int(pw * 0.94), int(ph * 0.94))
    masque = np.zeros((ph, pw), np.uint8)
    bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(petit, masque, rect, bg, fg, 5, cv2.GC_INIT_WITH_RECT)
    m = np.where((masque == cv2.GC_FGD) | (masque == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(m, (0, 0), 1.0)


def retirer_fond(img, methode="auto", tolerance=30, progression=None, enferme=False):
    """Image BGRA dont le fond est transparent. Renvoie (image, méthode utilisée)."""
    def av(f, t):
        if progression:
            progression(f, t)
    bgr = img[..., :3].copy()
    if methode == "auto":
        methode = "uni" if fond_uni_probable(bgr) else "photo"
    av(0.2, _("Fond uni : retrait de la couleur des bords…") if methode == "uni" else _("Sujet d'une photo : détourage…"))
    alpha = _fond_uni(bgr, float(tolerance), enferme) if methode == "uni" else _photo(bgr)
    if img.shape[2] == 4:
        alpha = np.minimum(alpha, img[..., 3])
    av(0.9, _("Bords adoucis…"))
    out = np.dstack([bgr, alpha])
    return out, methode


def recadrer_au_sujet(img, marge=0.03):
    """Retire les bords entièrement transparents (le logo remplit sa place)."""
    ys, xs = np.where(img[..., 3] > 8)
    if len(xs) == 0:
        return img
    h, w = img.shape[:2]
    m = int(max(h, w) * marge)
    return img[max(0, ys.min() - m):min(h, ys.max() + m + 1), max(0, xs.min() - m):min(w, xs.max() + m + 1)].copy()


def chemin_copie(chemin):
    """« logo.jpg » → « logo_sans_fond.png » à côté (ou numéroté s'il existe déjà) ; dossier des données si le dossier
    d'origine n'est pas modifiable."""
    base = os.path.splitext(chemin)[0] + "_sans_fond"
    dossier = os.path.dirname(chemin)
    if not os.access(dossier or ".", os.W_OK):
        from .config import dossier_donnees
        dossier = os.path.join(dossier_donnees(), "images")
        os.makedirs(dossier, exist_ok=True)
        base = os.path.join(dossier, os.path.basename(base))
    p, i = base + ".png", 2
    while os.path.exists(p):
        p, i = f"{base}_{i}.png", i + 1
    return p


def enregistrer(img, chemin):
    ok, data = cv2.imencode(".png", img)
    if not ok:
        raise OSError(_("Enregistrement impossible : {c}", c=chemin))
    data.tofile(chemin)
    return chemin
