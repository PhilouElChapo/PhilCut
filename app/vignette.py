"""Vignettes YouTube et images fixes composées à partir d'une image du film (0.9.3).

Principe : l'IA décide, PhilCut dessine. L'image reste celle du film ; les flèches, textes, badges et contours sont
dessinés par PhilCut d'après un kit de style cohérent (une famille de flèches, une police, trois couleurs tirées de
l'image) : jamais l'aspect « catalogue de prompts » des vignettes faites par IA.

L'utilisateur entoure des zones sur l'image ; la couleur dit le rôle :
- rouge : ce qu'on veut montrer (détouré, agrandi, contour, reste assombri) ; une personne du film se détoure ainsi ;
- jaune : désigner (flèche ou cercle, choisis selon la taille de la zone) ;
- bleu : le texte (titre) ;
- vert : les éléments précisés dans la phrase (pastilles, avec validé ✓ ou non ✗) ;
- blanc (facultatif) : zone à laisser libre (rien ne s'y pose).

Tout est décrit par une « recette » (dict) gardée dans le projet : la vignette se rouvre et se modifie.
Le calcul se fait sur ce poste, sans IA (détourage par OpenCV GrabCut, amélioré par le modèle de détourage s'il est
installé) ; l'IA (locale ou cloud) peut proposer le titre, les éléments et le kit.
"""
import math
import os
import random
import uuid

import numpy as np

from .langue import _

try:
    import cv2
except ImportError:      # pragma: no cover
    cv2 = None

FORMATS = {"youtube": (_("Miniature YouTube 16:9 (1280 × 720)"), 1280, 720), "short": (_("Short / Reels 9:16 (1080 × 1920)"), 1080, 1920),
           "projet": (_("Format du projet"), 0, 0)}

COULEURS_ZONES = {
    "rouge": ("#ff3b30", _("Rouge : le sujet à montrer"),
              _("<b>Rouge : le sujet à montrer.</b> Entourez l'objet ou la personne du film qui doit attirer l'œil. PhilCut le détoure, "
                "lui met un contour et assombrit le reste. Exemple : le moteur posé sur l'établi.")),
    "jaune": ("#ffd60a", _("Jaune : une flèche vers un détail"),
              _("<b>Jaune : une flèche ou un cercle vers un détail.</b> Entourez le détail à désigner : petite zone, une flèche y pointe ; "
                "grande zone, un cercle l'entoure. Le texte de la zone s'écrit au départ de la flèche. Exemple : « la fissure ».")),
    "bleu": ("#0a84ff", _("Bleu : la place du titre"),
             _("<b>Bleu : la place du titre.</b> Entourez l'endroit libre où écrire le titre : il s'ajuste tout seul à la zone. "
               "Le texte de la zone remplace le titre général pour cette zone. Exemple : « 3 erreurs à éviter ».")),
    "vert": ("#30d158", _("Vert : une liste de pastilles"),
             _("<b>Vert : une liste de pastilles (étapes, points, outils).</b> Entourez la place de la liste, puis écrivez ses éléments "
               "dans le texte de la zone, séparés par des virgules, avec ✓ (fait) ou ✗ (pas fait). Exemple : « Isolation ✓, Fenêtre ✓, "
               "Électricité ✗ ».")),
    "blanc": ("#f2f2f7", _("Blanc : ne rien poser ici"),
              _("<b>Blanc : ne rien poser ici (facultatif).</b> Entourez ce qui doit rester visible : un visage, le logo de la chaîne, "
                "une information. Ni texte, ni flèche, ni pastille n'y sera posé.")),
}

# ce qu'on écrit dans le champ « Qu'y a-t-il ici ? » de chaque zone : exemple affiché en grisé
EXEMPLES_ZONES = {"rouge": _("Ex. : le moteur, la personne de gauche"), "jaune": _("Ex. : la fissure (écrit au départ de la flèche)"),
                  "bleu": _("Ex. : 3 erreurs à éviter (le titre de cette zone)"),
                  "vert": _("Ex. : Isolation ✓, Fenêtre ✓, Électricité ✗"), "blanc": _("Ex. : visage, logo de la chaîne")}


# Kits : un seul style par vignette, c'est ce qui fait propre
KITS = {
    "punchy": {"nom": _("Punchy YouTube (propre)"), "police": "Anton", "poids": 400, "majuscules": True, "contour": 0.11, "ombre": "dure",
               "fleche": "grosse", "detoure": "blanc", "fond": "assombrir", "bandeau": False},
    "editorial": {"nom": _("Éditorial (sobre, magazine)"), "police": "Poppins", "poids": 900, "majuscules": False, "contour": 0.0,
                  "ombre": "douce", "fleche": "fine", "detoure": "ombre", "fond": "doux", "bandeau": False},
    "documentaire": {"nom": _("Documentaire"), "police": "Bebas Neue", "poids": 400, "majuscules": True, "contour": 0.0, "ombre": "douce",
                     "fleche": "trait", "detoure": "ombre", "fond": "doux", "bandeau": True},
    "tech": {"nom": _("Tech (néon discret)"), "police": "Poppins", "poids": 700, "majuscules": True, "contour": 0.0, "ombre": "lueur",
             "fleche": "neon", "detoure": "lueur", "fond": "sombre", "bandeau": False},
    "aviation": {"nom": _("Aviation (instruments, balisage)"), "police": "Bebas Neue", "poids": 400, "majuscules": True, "contour": 0.06,
                 "ombre": "dure", "fleche": "trait", "detoure": "blanc", "fond": "assombrir", "bandeau": True,
                 "accent": "#ff6a00"},
}

EFFETS_ROUGE = {"detoure": _("Détouré, contour et reste assombri"), "zoom": _("Détouré et agrandi (effet loupe)"),
                "projecteur": _("Projecteur (le reste dans l'ombre)"), "rien": _("Aucun effet")}
FLECHES = {"auto": _("Selon la zone (flèche ou cercle)"), "fleche": _("Flèche"), "cercle": _("Cercle"), "rien": _("Rien")}

PROMPTS = {
    "valeur": (_("Mettre en valeur"), _("Mettre en valeur ce qui est entouré en rouge ; titre court et percutant (3 à 5 mots) sur le sujet de la vidéo.")),
    "etapes": (_("Avancement, étapes validées"), _("Montrer l'avancement : la zone verte liste les étapes (ex. isolation ✓, fenêtre ✓, électricité ✗) ; titre qui résume où on en est.")),
    "revelation": (_("Curiosité, révélation"), _("Créer la curiosité : la flèche montre un détail surprenant ; titre sous forme de question ou d'exclamation.")),
    "avant_apres": (_("Avant / après"), _("Avant / après : l'image coupée en diagonale montre la différence ; titre qui annonce le résultat.")),
    "tuto": (_("Tutoriel"), _("Tutoriel : titre « Comment … » ; la zone verte liste les éléments ou outils utilisés.")),
    "comparatif": (_("Comparatif"), _("Comparatif : deux éléments face à face, la zone verte liste les points forts validés ou non.")),
}

ACCENTS = ["#ffd60a", "#ff7a00", "#ff2d55", "#00e5ff", "#a6ff00", "#ff3bf5"]


def nouvelle_recette(format_="youtube"):
    return {"id": uuid.uuid4().hex[:10], "nom": _("Vignette"), "format": format_, "source_t": 0.0, "source2_t": None, "cadrage": 0.5,
            "kit": "punchy", "zones": [], "titre": "", "accent_mots": "", "elements": "", "effet_rouge": "detoure", "fleche": "auto",
            "avant_apres": False, "prompt_id": "valeur", "prompt": PROMPTS["valeur"][1], "graine": 0}


def taille_sortie(recette, projet=None):
    f = FORMATS.get(recette.get("format") or "youtube", FORMATS["youtube"])
    if f[1]:
        return f[1], f[2]
    if projet is not None:
        return projet.taille
    return 1280, 720


# ------------------------------------------------------------------ image du film
def image_du_film(projet, t, largeur=1920):
    """Image (BGR) du film à l'instant t de la timeline, depuis le rush d'origine."""
    c = projet.plan_visible(t) if hasattr(projet, "plan_visible") else projet.clip_a(t, "video")
    m = projet.media(c["media"]) if c else None
    if not m:
        return None
    if m.get("genre") == "image":
        img = cv2.imread(m["chemin"])
        return img
    from . import moteur
    src = c["src_debut"] + (t - c["debut"]) * c.get("vitesse", 1.0)
    png = moteur.image(m["chemin"], src, largeur)
    if not png:
        return None
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)


def cadrer(img, L, H, cadrage=0.5):
    """Remplit L × H (rognage) ; cadrage 0..1 choisit la partie gardée sur l'axe rogné."""
    h, w = img.shape[:2]
    k = max(L / w, H / h)
    nw, nh = max(L, int(round(w * k))), max(H, int(round(h * k)))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    x = int((nw - L) * min(1.0, max(0.0, cadrage)))
    y = int((nh - H) * (min(1.0, max(0.0, cadrage)) if nh - H > nw - L else 0.5))
    return r[y:y + H, x:x + L].copy()


# ------------------------------------------------------------------ couleurs
def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _teinte(rgb):
    r, g, b = [x / 255 for x in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0.0
    if mx == r:
        h = (g - b) / (mx - mn) % 6
    elif mx == g:
        h = (b - r) / (mx - mn) + 2
    else:
        h = (r - g) / (mx - mn) + 4
    return h * 60


def palette(img, kit="punchy", graine=0):
    """Trois couleurs tirées de l'image : accent (qui ressort sur l'image), texte, contour."""
    k = KITS.get(kit, KITS["punchy"])
    petite = cv2.resize(img, (64, 36), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(petite, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(float)
    sat = hsv[hsv[:, 1] > 60]
    dominante = float(np.median(sat[:, 0]) * 2) if len(sat) > 20 else None      # 0..360
    lum = float(hsv[:, 2].mean())
    if k.get("accent"):
        accent = k["accent"]
    else:
        def ecart(c):
            if dominante is None:
                return 1.0
            d = abs(_teinte(_hex(c)) - dominante) % 360
            return min(d, 360 - d) / 180
        cands = sorted(ACCENTS, key=ecart, reverse=True)
        accent = cands[graine % 3]
    return {"accent": accent, "texte": "#ffffff", "contour": "#111111", "sombre": lum < 90, "dominante": dominante}


# ------------------------------------------------------------------ zones
def _pts(z, L, H):
    return np.array([[int(x * L), int(y * H)] for x, y in z["points"]], dtype=np.int32)


def _bbox(z, L, H):
    p = _pts(z, L, H)
    x0, y0 = p.min(axis=0)
    x1, y1 = p.max(axis=0)
    return int(x0), int(y0), int(max(x1, x0 + 2)), int(max(y1, y0 + 2))


def zones(recette, couleur):
    return [z for z in recette.get("zones") or [] if z.get("couleur") == couleur and len(z.get("points") or []) >= 3]


_CACHE_MASQUES = {}


def masque_sujet(img, z, L, H):
    """Masque 0..255 du sujet entouré : GrabCut amorcé par le tracé (sur ce poste, sans modèle), affiné par le modèle de
    détourage s'il est installé et que le sujet est une personne."""
    cle = (img.shape, float(img[::37, ::41].mean()), tuple(map(tuple, z["points"])))
    if cle in _CACHE_MASQUES:
        return _CACHE_MASQUES[cle]
    poly = _pts(z, L, H)
    m_poly = np.zeros((H, L), np.uint8)
    cv2.fillPoly(m_poly, [poly], 255)
    x0, y0, x1, y1 = _bbox(z, L, H)
    marge = int(0.08 * max(x1 - x0, y1 - y0)) + 4
    x0, y0, x1, y1 = max(0, x0 - marge), max(0, y0 - marge), min(L, x1 + marge), min(H, y1 + marge)
    crop = img[y0:y1, x0:x1]
    mp = m_poly[y0:y1, x0:x1]
    res = None
    try:
        echelle = min(1.0, 480 / max(crop.shape[:2]))
        c2 = cv2.resize(crop, None, fx=echelle, fy=echelle, interpolation=cv2.INTER_AREA) if echelle < 1 else crop
        m2 = cv2.resize(mp, (c2.shape[1], c2.shape[0]), interpolation=cv2.INTER_NEAREST)
        gc = np.where(m2 > 0, cv2.GC_PR_FGD, cv2.GC_BGD).astype(np.uint8)
        noyau = cv2.erode(m2, np.ones((5, 5), np.uint8), iterations=max(1, int(min(c2.shape[:2]) * 0.06)))
        gc[noyau > 0] = cv2.GC_PR_FGD
        bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        cv2.grabCut(c2, gc, None, bg, fg, 4, cv2.GC_INIT_WITH_MASK)
        r = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        r = cv2.resize(r, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_LINEAR)
        part = (r > 127).sum() / max(1, (mp > 0).sum())
        if 0.12 < part < 1.05:
            res = r
    except Exception:          # noqa: BLE001 : à défaut, le tracé lui-même
        res = None
    try:
        from . import segmentation
        if segmentation._portable():
            mp_pers = segmentation.masque_image(crop)
            if mp_pers is not None and (mp_pers > 127).sum() > 0.25 * (mp > 0).sum():
                res = np.minimum(mp_pers, cv2.dilate(mp, np.ones((15, 15), np.uint8)))
    except Exception:          # noqa: BLE001
        pass
    if res is None:
        res = mp
    res = cv2.GaussianBlur(res, (0, 0), 1.2)
    out = np.zeros((H, L), np.uint8)
    out[y0:y1, x0:x1] = res
    if len(_CACHE_MASQUES) > 24:
        _CACHE_MASQUES.clear()
    _CACHE_MASQUES[cle] = out
    return out


# ------------------------------------------------------------------ dessin (Qt)
def _polices():
    from PySide6.QtGui import QFontDatabase
    if "Anton" in QFontDatabase.families():
        return
    import sys
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(base, "fonts")
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(d, f))


def _qimage(bgr):
    from PySide6.QtGui import QImage
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()


def _depuis_qimage(q):
    from PySide6.QtGui import QImage
    q = q.convertToFormat(QImage.Format_RGB888)
    w, h = q.width(), q.height()
    a = np.frombuffer(q.constBits(), np.uint8, q.bytesPerLine() * h).reshape(h, q.bytesPerLine())[:, :w * 3].reshape(h, w, 3)
    return cv2.cvtColor(a, cv2.COLOR_RGB2BGR)


def _qcolor(c, alpha=255):
    from PySide6.QtGui import QColor
    q = QColor(c)
    q.setAlpha(alpha)
    return q


def _police(kit, taille):
    from PySide6.QtGui import QFont
    k = KITS.get(kit, KITS["punchy"])
    f = QFont(k["police"])
    f.setPixelSize(max(6, int(taille)))
    f.setWeight(QFont.Weight(k.get("poids", 700)))
    return f


def _lignes(mots, n):
    """Coupe la liste de mots en n lignes de longueurs proches."""
    if n <= 1 or len(mots) <= 1:
        return [mots]
    total = sum(len(m) for m in mots) + len(mots) - 1
    cible = total / n
    out, cour, long_ = [], [], 0
    for m in mots:
        if cour and long_ + len(m) > cible * 1.15 and len(out) < n - 1:
            out.append(cour)
            cour, long_ = [], 0
        cour.append(m)
        long_ += len(m) + 1
    out.append(cour)
    return out


def _titre(p, recette, kit, pal, boite, L, H):
    """Titre ajusté à la zone bleue (jusqu'à 3 lignes), mots d'accent en couleur. Renvoie la taille de police."""
    from PySide6.QtGui import QFontMetrics, QPainterPath, QPen
    from PySide6.QtCore import Qt, QPointF
    k = KITS.get(kit, KITS["punchy"])
    texte = (recette.get("titre") or "").strip()
    if not texte:
        return 0
    if k["majuscules"]:
        texte = texte.upper()
    accents = {m.strip().upper() for m in (recette.get("accent_mots") or "").replace(",", " ").split() if m.strip()}
    mots = texte.split()
    x0, y0, x1, y1 = boite
    bw, bh = x1 - x0, y1 - y0
    meilleur = None
    for n in (1, 2, 3):
        lignes = _lignes(mots, n)
        bas, haut = 8, int(bh / n / 1.02)
        while bas < haut:                          # plus grande taille qui tient
            mi = (bas + haut + 1) // 2
            fm = QFontMetrics(_police(kit, mi))
            if max(fm.horizontalAdvance(" ".join(lg)) for lg in lignes) <= bw and fm.height() * 0.92 * n <= bh:
                bas = mi
            else:
                haut = mi - 1
        if meilleur is None or bas > meilleur[0]:
            meilleur = (bas, lignes)
    taille, lignes = meilleur
    f = _police(kit, taille)
    fm = QFontMetrics(f)
    hl = fm.height() * 0.92
    ytot = hl * len(lignes)
    y = y0 + (bh - ytot) / 2 + fm.ascent() * 0.98
    p.setRenderHint(p.RenderHint.Antialiasing)
    for lg in lignes:
        largeur = fm.horizontalAdvance(" ".join(lg))
        x = x0 + (bw - largeur) / 2
        if k.get("bandeau"):
            p.fillRect(int(x - taille * 0.2), int(y - fm.ascent() * 0.95), int(largeur + taille * 0.4), int(hl), _qcolor(pal["accent"], 235))
        for m in lg:
            chemin = QPainterPath()
            chemin.addText(QPointF(x, y), f, m)
            accent = m.strip(".,!?:;«»\"'").upper() in accents
            if k.get("bandeau"):                      # texte sombre sur le bandeau, mots d'accent en blanc ; ni ombre ni contour
                p.fillPath(chemin, _qcolor("#ffffff" if accent else "#111111"))
                x += fm.horizontalAdvance(m + " ")
                continue
            couleur = pal["accent"] if accent else pal["texte"]
            if k["ombre"] == "dure":
                p.fillPath(chemin.translated(taille * 0.05, taille * 0.06), _qcolor("#000000", 200))
            elif k["ombre"] == "douce":
                for i in range(1, 5):
                    p.fillPath(chemin.translated(i * taille * 0.012, i * taille * 0.015), _qcolor("#000000", 40))
            elif k["ombre"] == "lueur":
                for i in (6, 4, 2):
                    p.strokePath(chemin, QPen(_qcolor(pal["accent"], 45), taille * 0.02 * i, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            if k["contour"]:
                p.strokePath(chemin, QPen(_qcolor(pal["contour"]), taille * k["contour"] * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.fillPath(chemin, _qcolor(couleur))
            x += fm.horizontalAdvance(m + " ")
        y += hl
    return taille


def _elements(texte):
    """« pistons ✓ / soupapes ✗ / arbre à cames » → [(libellé, "ok"|"non"|"")]. Une ligne ou une virgule par élément."""
    out = []
    for brut in texte.replace(";", "\n").replace(",", "\n").split("\n"):
        b = brut.strip()
        if not b:
            continue
        etat = ""
        bas = b.lower()
        for s, e in (("✓", "ok"), ("✔", "ok"), (" ok", "ok"), (" oui", "ok"), (" v", "ok"), ("✗", "non"), ("✘", "non"), ("❌", "non"),
                     (" non", "non"), (" x", "non")):
            if bas.endswith(s):
                etat = e
                b = b[: len(b) - len(s)].strip()
                break
        out.append((b, etat))
    return out[:8]


def _pastilles(p, elements, kit, pal, boite):
    from PySide6.QtGui import QFontMetrics, QPen, QPainterPath
    from PySide6.QtCore import Qt, QRectF, QPointF
    if not elements:
        return
    k = KITS.get(kit, KITS["punchy"])
    x0, y0, x1, y1 = boite
    bw, bh = x1 - x0, y1 - y0
    n = len(elements)
    en_ligne = bw / max(1, bh) > 1.6
    cols = n if en_ligne else 1
    rangs = 1 if en_ligne else n
    cw, ch = bw / cols, bh / rangs
    hauteur = min(ch * 0.82, cw * 0.42 if en_ligne else ch * 0.82)
    p.setRenderHint(p.RenderHint.Antialiasing)
    for i, (lib, etat) in enumerate(elements):
        cx = x0 + (i % cols) * cw + cw / 2
        cy = y0 + (i // cols) * ch + ch / 2
        texte = lib.upper() if k["majuscules"] else lib
        tp = hauteur * 0.42
        while tp > 8:                                  # le libellé tient toujours en entier dans sa pastille
            f = _police(kit, tp)
            fm = QFontMetrics(f)
            if hauteur * 1.15 + fm.horizontalAdvance(texte) + hauteur * 0.5 <= cw * 0.94:
                break
            tp *= 0.92
        largeur = min(cw * 0.94, hauteur * 1.15 + fm.horizontalAdvance(texte) + hauteur * 0.5)
        r = QRectF(cx - largeur / 2, cy - hauteur / 2, largeur, hauteur)
        p.setPen(Qt.NoPen)
        p.setBrush(_qcolor("#000000", 90))
        p.drawRoundedRect(r.translated(hauteur * 0.05, hauteur * 0.07), hauteur / 2, hauteur / 2)
        p.setBrush(_qcolor("#141414", 235))
        p.setPen(QPen(_qcolor(pal["accent"]), max(2.0, hauteur * 0.06)))
        p.drawRoundedRect(r, hauteur / 2, hauteur / 2)
        # pastille ronde : initiale, ou coche / croix
        d = hauteur * 0.78
        rc = QRectF(r.left() + hauteur * 0.11, cy - d / 2, d, d)
        fond = {"ok": "#30d158", "non": "#ff3b30"}.get(etat, pal["accent"])
        p.setPen(Qt.NoPen)
        p.setBrush(_qcolor(fond))
        p.drawEllipse(rc)
        p.setPen(QPen(_qcolor("#ffffff"), d * 0.13, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if etat == "ok":
            ch_ = QPainterPath(QPointF(rc.left() + d * 0.27, rc.top() + d * 0.53))
            ch_.lineTo(rc.left() + d * 0.44, rc.top() + d * 0.70)
            ch_.lineTo(rc.left() + d * 0.75, rc.top() + d * 0.33)
            p.setBrush(Qt.NoBrush)
            p.drawPath(ch_)
        elif etat == "non":
            p.drawLine(QPointF(rc.left() + d * 0.32, rc.top() + d * 0.32), QPointF(rc.right() - d * 0.32, rc.bottom() - d * 0.32))
            p.drawLine(QPointF(rc.right() - d * 0.32, rc.top() + d * 0.32), QPointF(rc.left() + d * 0.32, rc.bottom() - d * 0.32))
        else:
            fi = _police(kit, d * 0.55)
            p.setFont(fi)
            p.setPen(_qcolor("#111111"))
            p.drawText(rc, Qt.AlignCenter, (lib[:1] or "•").upper())
        p.setFont(f)
        p.setPen(_qcolor("#ffffff"))
        zone_txt = QRectF(rc.right() + hauteur * 0.18, r.top(), r.right() - rc.right() - hauteur * 0.3, hauteur)
        p.drawText(zone_txt, Qt.AlignVCenter | Qt.AlignLeft, fm.elidedText(texte, Qt.ElideNone, int(zone_txt.width())))


def _fleche(p, depart, arrivee, kit, pal, epaisseur, courbe=0.22):
    from PySide6.QtGui import QPainterPath, QPen, QPolygonF
    from PySide6.QtCore import Qt, QPointF
    k = KITS.get(kit, KITS["punchy"])
    style = k["fleche"]
    ax, ay = depart
    bx, by = arrivee
    dx, dy = bx - ax, by - ay
    long_ = math.hypot(dx, dy) or 1
    nx, ny = -dy / long_, dx / long_
    cx, cy = (ax + bx) / 2 + nx * long_ * courbe, (ay + by) / 2 + ny * long_ * courbe
    w = epaisseur * {"grosse": 1.0, "fine": 0.45, "trait": 0.6, "neon": 0.55}.get(style, 0.8)
    tete = w * 3.2
    # direction finale : tangente de la courbe à l'arrivée
    tx, ty = bx - cx, by - cy
    tl = math.hypot(tx, ty) or 1
    tx, ty = tx / tl, ty / tl
    base = (bx - tx * tete, by - ty * tete)
    chemin = QPainterPath(QPointF(ax, ay))
    chemin.quadTo(QPointF(cx, cy), QPointF(*base))
    tri = QPolygonF([QPointF(bx, by), QPointF(base[0] - ty * tete * 0.62, base[1] + tx * tete * 0.62),
                     QPointF(base[0] + ty * tete * 0.62, base[1] - tx * tete * 0.62)])
    p.setRenderHint(p.RenderHint.Antialiasing)
    p.setBrush(Qt.NoBrush)
    if style == "neon":
        for i, a in ((4.0, 40), (2.6, 70), (1.7, 110)):
            p.setPen(QPen(_qcolor(pal["accent"], a), w * i, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(chemin)
            p.drawPolygon(tri)
    else:
        p.setPen(QPen(_qcolor("#000000", 110), w + epaisseur * 0.35, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(chemin.translated(w * 0.25, w * 0.3))
        if k["contour"] or style == "grosse":
            p.setPen(QPen(_qcolor(pal["contour"]), w + max(4.0, w * 0.5), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(chemin)
            p.setBrush(_qcolor(pal["contour"]))
            p.drawPolygon(tri)
    p.setPen(QPen(_qcolor(pal["accent"] if style != "neon" else "#ffffff"), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(chemin)
    p.setPen(QPen(_qcolor(pal["accent"] if style != "neon" else "#ffffff"), max(1.0, w * 0.3), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(_qcolor(pal["accent"] if style != "neon" else "#ffffff"))
    p.drawPolygon(tri)


def _cercle(p, boite, kit, pal, epaisseur, graine):
    from PySide6.QtGui import QPainterPath, QPen
    from PySide6.QtCore import Qt, QPointF
    x0, y0, x1, y1 = boite
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 * 1.12, (y1 - y0) / 2 * 1.15
    rnd = random.Random(graine)
    chemin = QPainterPath()
    n = 64
    debut = rnd.uniform(0, math.pi * 2)
    for i in range(n + 6):                               # un tour et un peu plus : trait « à la main », propre
        a = debut + i / n * math.pi * 2
        k = 1 + 0.035 * math.sin(a * 2 + graine) + i / n * 0.05
        pt = QPointF(cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k)
        chemin.moveTo(pt) if i == 0 else chemin.lineTo(pt)
    w = epaisseur * 0.55
    p.setRenderHint(p.RenderHint.Antialiasing)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(_qcolor("#000000", 120), w * 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(chemin.translated(w * 0.3, w * 0.35))
    p.setPen(QPen(_qcolor(pal["accent"]), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(chemin)


def _dans(boite, pt, marge=0):
    x0, y0, x1, y1 = boite
    return x0 - marge <= pt[0] <= x1 + marge and y0 - marge <= pt[1] <= y1 + marge


def _bord(boite, depuis, marge):
    """Point au bord de la boîte (élargie de marge) sur la droite qui va du centre vers depuis."""
    x0, y0, x1, y1 = boite
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = depuis[0] - cx, depuis[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    rx, ry = (x1 - x0) / 2 + marge, (y1 - y0) / 2 + marge
    k = min(rx / abs(dx) if dx else 1e9, ry / abs(dy) if dy else 1e9)
    return cx + dx * k, cy + dy * k


def depart_fleche(cible, interdites, bleues, L, H, graine=0):
    """Où partir pour désigner la zone jaune : depuis le texte s'il y en a, sinon le côté le plus dégagé."""
    cx, cy = (cible[0] + cible[2]) / 2, (cible[1] + cible[3]) / 2
    if bleues:
        b = min(bleues, key=lambda b: math.hypot((b[0] + b[2]) / 2 - cx, (b[1] + b[3]) / 2 - cy))
        return _bord(b, (cx, cy), 8)
    d = 0.24 * min(L, H) + 0.5 * max(cible[2] - cible[0], cible[3] - cible[1])
    cands = []
    for i in range(12):
        a = (i / 12 + graine * 0.07) * math.pi * 2
        pt = (cx + math.cos(a) * d, cy + math.sin(a) * d)
        if not (0.05 * L < pt[0] < 0.95 * L and 0.06 * H < pt[1] < 0.94 * H):
            continue
        pen = sum(1 for z in interdites if _dans(z, pt, 10))
        cands.append((pen, -min(pt[0], L - pt[0], pt[1], H - pt[1]), pt))
    if not cands:
        return (max(0.08 * L, min(0.92 * L, cx - d)), max(0.1 * H, min(0.9 * H, cy - d)))
    cands.sort(key=lambda c: (c[0], c[1]))
    return cands[0][2]


# ------------------------------------------------------------------ composition
def composer(recette, img, img2=None, L=1280, H=720, progression=None):
    """L'image finale (QImage) de la recette, à partir de l'image du film (BGR) ; img2 pour l'avant / après.
    Renvoie (QImage, infos) ; infos : taille du titre, avertissements de lisibilité."""
    from PySide6.QtGui import QPainter, QImage
    from PySide6.QtCore import Qt, QRectF

    def av(f, t):
        if progression:
            progression(f, t)
    _polices()
    kit = recette.get("kit") or "punchy"
    k = KITS.get(kit, KITS["punchy"])
    graine = int(recette.get("graine") or 0)
    av(0.05, _("Cadrage de l'image du film…"))
    base = cadrer(img, L, H, recette.get("cadrage", 0.5))
    if recette.get("avant_apres") and img2 is not None:
        b2 = cadrer(img2, L, H, recette.get("cadrage", 0.5))
        m = np.zeros((H, L), np.uint8)
        cv2.fillPoly(m, [np.array([[0, 0], [int(L * 0.58), 0], [int(L * 0.42), H], [0, H]], np.int32)], 255)
        base = np.where(m[..., None] > 0, base, b2)
    pal = palette(base, kit, graine)
    # étalonnage léger : contraste et couleurs, comme un graphiste
    hsv = cv2.cvtColor(base, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.15, 0, 255)
    base = cv2.convertScaleAbs(cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR), alpha=1.07, beta=-4)
    rouges = zones(recette, "rouge")
    effet = recette.get("effet_rouge") or "detoure"
    fond = base.copy()
    sujets = []
    if rouges and effet != "rien":
        av(0.2, _("Détourage du sujet entouré en rouge…"))
        masque = np.zeros((H, L), np.uint8)
        for z in rouges:
            mz = masque_sujet(base, z, L, H)
            masque = np.maximum(masque, mz)
            sujets.append((z, mz))
        force = {"assombrir": 0.62, "doux": 0.78, "sombre": 0.5}.get(k["fond"], 0.65)
        if effet == "projecteur":
            force *= 0.55
        flou = cv2.GaussianBlur(base, (0, 0), 3 if effet != "projecteur" else 6)
        fond = cv2.convertScaleAbs(flou, alpha=force)
        a = (masque.astype(np.float32) / 255)[..., None]
        fond = (base * a + fond * (1 - a)).astype(np.uint8)
    av(0.5, _("Couleurs et dessin du kit « {k} »…", k=k["nom"]))
    q = _qimage(fond)
    p = QPainter(q)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    epaisseur = max(6.0, min(L, H) * 0.028)
    # sujets détourés : contour, ombre ou lueur, et agrandissement (effet loupe)
    for z, mz in sujets:
        x0, y0, x1, y1 = _bbox(z, L, H)
        zoom = 1.22 if effet == "zoom" else 1.0
        rgba = np.dstack([cv2.cvtColor(base, cv2.COLOR_BGR2RGB), mz])
        cont = int(max(3, min(L, H) * (0.012 if k["detoure"] == "blanc" else 0.008)))
        dil = cv2.dilate(mz, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * cont + 1, 2 * cont + 1)))
        couche_c = np.zeros((H, L, 4), np.uint8)
        coul = {"blanc": "#ffffff", "lueur": pal["accent"], "ombre": "#000000"}.get(k["detoure"], "#ffffff")
        couche_c[..., :3] = _hex(coul)
        couche_c[..., 3] = cv2.GaussianBlur(dil, (0, 0), cont * (1.5 if k["detoure"] in ("lueur", "ombre") else 0.4))
        if k["detoure"] == "ombre":
            couche_c[..., 3] = (couche_c[..., 3] * 0.55).astype(np.uint8)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for couche in (couche_c, rgba):
            qi = QImage(np.ascontiguousarray(couche).data, L, H, 4 * L, QImage.Format_RGBA8888).copy()
            p.save()
            p.translate(cx, cy)
            p.scale(zoom, zoom)
            p.translate(-cx, -cy)
            if couche is couche_c and k["detoure"] == "ombre":
                p.translate(cont * 0.8, cont * 1.1)
            p.drawImage(0, 0, qi)
            p.restore()
    if recette.get("avant_apres") and img2 is not None:
        from PySide6.QtGui import QPen
        p.setPen(QPen(_qcolor("#000000", 120), epaisseur * 0.9))
        p.drawLine(int(L * 0.58) + 3, -2, int(L * 0.42) + 3, H + 2)
        p.setPen(QPen(_qcolor("#ffffff"), epaisseur * 0.55))
        p.drawLine(int(L * 0.58), -2, int(L * 0.42), H + 2)
        for lib, x in ((_("AVANT"), 0.04), (_("APRÈS"), 0.96)):
            f = _police(kit, H * 0.07)
            p.setFont(f)
            from PySide6.QtGui import QFontMetrics
            fm = QFontMetrics(f)
            w = fm.horizontalAdvance(lib) + H * 0.05
            r = QRectF(L * x - (w if x > 0.5 else 0), H * 0.84, w, H * 0.1)
            p.setPen(Qt.NoPen)
            p.setBrush(_qcolor(pal["accent"] if x > 0.5 else "#141414", 235))
            p.drawRoundedRect(r, H * 0.02, H * 0.02)
            p.setPen(_qcolor("#111111" if x > 0.5 else "#ffffff"))
            p.drawText(r, Qt.AlignCenter, lib)
    av(0.7, _("Pastilles, texte et flèche…"))
    for z in zones(recette, "vert"):
        _pastilles(p, _elements((z.get("texte") or "").strip() or recette.get("elements") or ""), kit, pal, _bbox(z, L, H))
    taille_titre = 0
    bleues = [_bbox(z, L, H) for z in zones(recette, "bleu")]
    for z in zones(recette, "bleu"):
        propre = (z.get("texte") or "").strip()
        rec_z = dict(recette, titre=propre) if propre else recette
        taille_titre = max(taille_titre, _titre(p, rec_z, kit, pal, _bbox(z, L, H), L, H))
    interdites = [_bbox(z, L, H) for z in zones(recette, "blanc") + rouges] + bleues + [_bbox(z, L, H) for z in zones(recette, "vert")]
    mode = recette.get("fleche") or "auto"
    for i, z in enumerate(zones(recette, "jaune")):
        b = _bbox(z, L, H)
        grande = max(b[2] - b[0], b[3] - b[1]) > 0.28 * min(L, H)
        if mode == "rien":
            continue
        if mode == "cercle" or (mode == "auto" and grande):
            _cercle(p, b, kit, pal, epaisseur, graine + i)
        else:
            dep = depart_fleche(b, interdites, bleues, L, H, graine + i)
            arr = _bord(b, dep, epaisseur * 0.4)
            _fleche(p, dep, arr, kit, pal, epaisseur, courbe=0.22 if (graine + i) % 2 == 0 else -0.22)
            if (z.get("texte") or "").strip():
                _etiquette(p, z["texte"].strip(), dep, kit, pal, L, H)
    p.end()
    infos = {"taille_titre": taille_titre, "palette": pal, "avertissements": lisibilite(recette, taille_titre, L, H)}
    av(1.0, _("Vignette prête."))
    return q, infos


def _etiquette(p, texte, point, kit, pal, L, H):
    """Petit texte au départ de la flèche jaune (« la fissure »), dans une pastille lisible, gardé dans l'image."""
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QFontMetrics
    f = _police(kit, max(14, int(H * 0.045)))
    p.setFont(f)
    fm = QFontMetrics(f)
    texte = texte[:40]
    w, h = fm.horizontalAdvance(texte) + H * 0.03, fm.height() * 1.25
    x = min(max(0.0, point[0] - w / 2), L - w)
    y = min(max(0.0, point[1] - h - H * 0.01), H - h)
    r = QRectF(x, y, w, h)
    p.setPen(Qt.NoPen)
    p.setBrush(_qcolor("#141414", 225))
    p.drawRoundedRect(r, h * 0.3, h * 0.3)
    p.setPen(_qcolor(pal["accent"]))
    p.drawText(r, Qt.AlignCenter, texte)


def lisibilite(recette, taille_titre, L, H):
    """Ce qui gêne en taille téléphone (vignette affichée vers 168 px de large dans les listes YouTube)."""
    out = []
    titre = (recette.get("titre") or "").strip()
    echelle = 168 / max(1, L)
    if not titre and zones(recette, "bleu") and not any((z.get("texte") or "").strip() for z in zones(recette, "bleu")):
        out.append(_("Zone bleue sans titre : écrivez-le dans « Qu'y a-t-il ici ? » de la zone, ou dans « Titre »."))
    if titre and not zones(recette, "bleu"):
        out.append(_("Le titre n'apparaît pas : entourez en bleu la place du texte."))
    if titre and zones(recette, "bleu") and taille_titre * echelle < 8:
        out.append(_("Titre trop petit en taille téléphone : agrandissez la zone bleue ou raccourcissez le titre."))
    if len(titre.split()) > 6:
        out.append(_("Titre long ({n} mots) : 3 à 5 mots se lisent mieux en petit.", n=len(titre.split())))
    if len(_elements(recette.get("elements") or "")) > 5:
        out.append(_("Plus de 5 pastilles : illisibles en petit."))
    if any(not (z.get("texte") or "").strip() for z in zones(recette, "vert")) and not (recette.get("elements") or "").strip():
        out.append(_("Zone verte sans éléments : écrivez-les dans « Qu'y a-t-il ici ? » de la zone (ex. Isolation ✓, Fenêtre ✗), "
                     "ou laissez l'IA les proposer."))
    return out


def variantes(recette, n=3):
    """Variantes proposées d'un clic : autre couleur d'accent et côté de flèche, puis deux autres kits."""
    import copy
    out = []
    kits = [k for k in KITS if k != recette.get("kit")]
    for i in range(n):
        r = copy.deepcopy(recette)
        r["graine"] = int(recette.get("graine") or 0) + i + 1
        if i:
            r["kit"] = kits[(i - 1 + int(recette.get("graine") or 0)) % len(kits)]
        out.append(r)
    return out


def enregistrer(q, chemin):
    """PNG ou JPG (qualité 92)."""
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    if chemin.lower().endswith((".jpg", ".jpeg")):
        return q.save(chemin, "JPG", 92)
    return q.save(chemin, "PNG")


# ------------------------------------------------------------------ IA : titre, éléments, kit
CONSIGNES_IA = """Tu prépares une vignette de vidéo (ou une image fixe insérée dans la vidéo) à partir d'une image du film.
Le logiciel dessine lui-même le texte, la flèche et les pastilles ; tu choisis seulement les contenus et le style.
Réponds en JSON : {"titre": "3 à 6 mots, dans la langue de l'utilisateur", "accent_mots": "1 ou 2 mots du titre à mettre en couleur",
"elements": "éléments de la zone verte, un par ligne, chacun suivi de ✓ (validé), ✗ (non) ou rien ; vide si aucune zone verte",
"kit": "punchy | editorial | documentaire | tech | aviation", "effet_rouge": "detoure | zoom | projecteur", "fleche": "auto | fleche | cercle",
"pourquoi": "une phrase"}.
Pas d'emoji dans le titre, pas de majuscules partout (le logiciel s'en charge), rien de racoleur ni de mensonger."""


def demande_ia(recette, contexte=""):
    roles = {"rouge": "sujet à montrer", "jaune": "détail désigné par une flèche", "bleu": "place du titre",
             "vert": "liste de pastilles", "blanc": "à laisser libre"}
    lignes = [f"- {z['couleur']} ({roles.get(z['couleur'], '')}) : {(z.get('texte') or '').strip() or '(non précisé)'}"
              for z in recette.get("zones") or []]
    zs = ("\n" + "\n".join(lignes)) if lignes else " aucune"
    return (f"Consigne de l'utilisateur : {recette.get('prompt') or ''}\n"
            f"Zones tracées (couleur, rôle, ce que l'utilisateur y a écrit) :{zs}\nTitre actuel : {recette.get('titre') or '(vide)'}\n"
            f"Éléments actuels : {recette.get('elements') or '(vide)'}\n{contexte}")


def proposer_ia(recette, png, params, niveau="cloud", rapporter=None, contexte=""):
    """Propositions de l'IA (dict) à fusionner dans la recette. niveau : "locale" ou "cloud"."""
    from . import ia
    texte = demande_ia(recette, contexte)
    if niveau == "locale":
        from . import ia_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise RuntimeError(_("Aucun modèle de vision local : cochez-en un dans Préférences › IA locale."))
        rapporter and rapporter(_("IA locale ({m}) : démarrage du modèle et lecture de l'image (une à plusieurs minutes sans carte graphique)…", m=modele))
        r = ia_locale.generer(modele, texte, [png], systeme=CONSIGNES_IA, json_attendu=True, params=params)
        d = ia.lire_json(r)
    else:
        rapporter and rapporter(_("IA cloud ({m}) : envoi de l'image et de la consigne…", m=ia.nom_moteur(params)))
        d = ia.demander(params, CONSIGNES_IA, texte, images=[png], json_attendu=True, max_jetons=1500)
    rapporter and rapporter(_("Réponse reçue : mise en place…"))
    out = {}
    for c in ("titre", "accent_mots", "elements", "pourquoi"):
        if isinstance(d.get(c), str):
            out[c] = d[c].strip()
    if isinstance(d.get("elements"), list):
        out["elements"] = "\n".join(str(x) for x in d["elements"])
    if d.get("kit") in KITS:
        out["kit"] = d["kit"]
    if d.get("effet_rouge") in EFFETS_ROUGE:
        out["effet_rouge"] = d["effet_rouge"]
    if d.get("fleche") in FLECHES:
        out["fleche"] = d["fleche"]
    return out
