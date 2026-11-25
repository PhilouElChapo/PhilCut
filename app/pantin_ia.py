"""Fabrication d'un pantin par l'IA (1.3.0) : trois dessins Gemini et une lecture du squelette, prix demandé avant.

1. Le corps en pose en T, de face, sans yeux ni bouche, sur un fond vert uni (PhilCut retire le vert).
2. Une planche du visage, à partir du corps (même style, même peau) : 6 paires d'yeux en haut, 7 bouches en bas.
3. La lecture des articulations (vision), corrigée ensuite à la souris.
Une photo réelle peut servir de modèle (personne consentante, case d'accord) : le personnage en est une version cartoon.
La consigne envoyée est en anglais ; la fenêtre la montre avec sa traduction.
"""
import os

from .langue import _
from . import pantin as P

PRIX_IMAGE = 0.04
PRIX_POINTS = 0.005
PRIX_PANTIN = round(2 * PRIX_IMAGE + PRIX_POINTS, 3)

# styles proposés (le choix est mémorisé dans les Préférences) : (nom affiché, consigne anglaise)
STYLES = {
    "bd": ("Bande dessinée", "comic book style, bold ink outlines, flat cel shading, vivid colors"),
    "cartoon3d": ("3D cartoon", "stylized 3D cartoon render, soft clay-like materials, smooth studio lighting, "
                                "toy-like proportions"),
    "papier": ("Papier découpé", "cut paper craft style, layered paper textures, soft drop edges, handmade look"),
    "plat": ("Plat vectoriel", "flat vector explainer-video style, clean geometric shapes, no outlines, simple "
                               "two-tone shading, limited modern palette"),
    "trait": ("Trait minimaliste", "minimalist line art, clean black outlines, flat pastel fills"),
}
YEUX_EN = {"ouverts": "neutral open eyes", "fermes": "closed eyes (blink)", "joie": "happy eyes (smiling, curved)",
           "surprise": "surprised wide eyes, raised eyebrows", "colere": "angry eyes, frowning eyebrows",
           "triste": "sad eyes, eyebrows tilted up in the middle"}
BOUCHES_EN = {"X": "closed relaxed mouth", "A": "closed mouth with lips pressed (M, B, P sounds)",
              "B": "slightly open mouth with clenched teeth (K, S, T sounds)", "C": "open mouth (EH, AE sounds)",
              "D": "wide open mouth (AA sound)", "E": "slightly rounded mouth (AO, ER sounds)",
              "F": "puckered small round mouth (UW, OW, W sounds)"}


def liste_styles():
    import unicodedata
    return sorted(((k, _(v[0])) for k, v in STYLES.items()),
                  key=lambda x: unicodedata.normalize("NFD", x[1].lower()).encode("ascii", "ignore"))


def consigne_corps(description_en, style, depuis_photo=False):
    st = STYLES.get(style, STYLES["plat"])[1]
    qui = ("a cartoon version of the person in the reference photo (same hair, skin tone, build and clothes, "
           "friendly and recognizable but clearly stylized)" if depuis_photo else description_en.strip() or "a friendly character")
    return (f"Full-body character sheet of {qui}. Style: {st}. STRICT T-POSE, front view, standing straight, "
            "both arms stretched out horizontally to the sides at shoulder height with open flat hands, legs straight "
            "and slightly apart, both feet fully visible. The face is BLANK: draw the head shape, hair and ears, "
            "but NO eyes, NO eyebrows, NO mouth, NO nose lines (they are added separately). Arms and legs must not "
            "overlap the body. Whole character centered with a margin, on a perfectly uniform pure green (#00FF00) "
            "background, no shadow, no floor, no text, no other object.")


def consigne_visage(style):
    st = STYLES.get(style, STYLES["plat"])[1]
    yeux = "; ".join(f"{i + 1}. {YEUX_EN[k]}" for i, k in enumerate(P.YEUX))
    bouches = "; ".join(f"{i + 1}. {BOUCHES_EN[k]}" for i, k in enumerate(P.BOUCHES))
    return (f"Facial features sheet for the character in the reference image, same style ({st}), same skin and colors. "
            f"TOP ROW, left to right, {len(P.YEUX)} pairs of eyes WITH their eyebrows, each pair drawn as one small "
            f"group: {yeux}. BOTTOM ROW, left to right, {len(P.BOUCHES)} mouths: {bouches}. Every item drawn "
            "front-facing at the same scale, with LARGE empty gaps between items, nothing else (no face, no head, no "
            "skin patch, no labels, no numbers), on a perfectly uniform pure green (#00FF00) background, no shadow.")


def consigne_points():
    noms = ", ".join(P.POINTS)
    return ("Tu regardes le dessin d'un personnage en pose en T, de face, sur fond transparent ou uni. Donne la position "
            "de ses articulations, en coordonnées normalisées de 0 à 1000 (x de gauche à droite, y de haut en bas, sur "
            f"toute l'image). Points : {noms}. « tete » est le haut du crâne ; « cou » la base du cou ; « bassin » le "
            "milieu des hanches ; « _g » : côté GAUCHE DE L'IMAGE ; « _d » : côté DROIT DE L'IMAGE ; « poignet » : là où "
            "la main commence ; « cheville » : là où le pied commence. Réponds par un objet JSON {\"nom\": [x, y], …}.")


def prix(avec_visage=True):
    return round(PRIX_IMAGE * (2 if avec_visage else 1) + PRIX_POINTS, 3)


def separer_planche(chemin, lignes):
    """Découpe une planche transparente en objets : `lignes` = nombre d'objets attendus par ligne (de haut en bas).
    Les morceaux proches (deux yeux et leurs sourcils) sont regroupés. Renvoie [[QImage, …] par ligne]."""
    import cv2
    import numpy as np
    from PySide6.QtGui import QImage
    rgba, alpha = P._masque(chemin)
    h, w = alpha.shape
    m = alpha.astype(np.uint8) * 255
    attendus = sum(lignes)
    for k in (0.012, 0.02, 0.03, 0.045):        # rapprochement de plus en plus large, jusqu'au bon nombre d'objets
        r = max(2, int(w * k))
        gros = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        n, etiq, stats, centres = cv2.connectedComponentsWithStats(gros, 8)
        objets = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > (w * h) * 0.0004]
        if len(objets) == attendus:
            break
    else:
        raise ValueError(_("La planche compte {n} objets au lieu de {a} : refaites-la.", n=len(objets), a=attendus))
    objets.sort(key=lambda i: centres[i][1])
    sortie, debut = [], 0
    for nb in lignes:
        rangee = sorted(objets[debut:debut + nb], key=lambda i: centres[i][0])
        debut += nb
        ims = []
        for i in rangee:
            x, y, ww, hh = stats[i, 0], stats[i, 1], stats[i, 2], stats[i, 3]
            sel = (etiq[y:y + hh, x:x + ww] == i) & alpha[y:y + hh, x:x + ww]
            morceau = np.zeros((hh, ww, 4), np.uint8)
            morceau[sel] = rgba[y:y + hh, x:x + ww][sel]
            ys, xs = np.nonzero(morceau[..., 3] > 0)
            morceau = np.ascontiguousarray(morceau[ys.min():ys.max() + 1, xs.min():xs.max() + 1])
            hh2, ww2 = morceau.shape[:2]
            ims.append(QImage(morceau.data, ww2, hh2, ww2 * 4, QImage.Format_RGBA8888).copy())
        sortie.append(ims)
    return sortie


def lire_points(reponse, largeur, hauteur):
    """Réponse JSON de la vision (0..1000) → points en pixels ; un point manquant ou faux lève une erreur."""
    pts = {}
    for k in P.POINTS:
        v = (reponse or {}).get(k)
        if not (isinstance(v, (list, tuple)) and len(v) >= 2):
            raise ValueError(_("L'IA n'a pas donné le point « {p} » : placez-le à la souris.", p=_(P.NOMS_POINTS[k])))
        x, y = float(v[0]), float(v[1])
        pts[k] = [max(0.0, min(1000.0, x)) * largeur / 1000.0, max(0.0, min(1000.0, y)) * hauteur / 1000.0]
    # côtés inversés par l'IA (gauche du personnage / gauche de l'image) : on remet « _g » à gauche de l'image
    for a in ("epaule", "coude", "poignet", "hanche", "genou", "cheville"):
        g, d = pts[a + "_g"], pts[a + "_d"]
        if g[0] > d[0]:
            pts[a + "_g"], pts[a + "_d"] = d, g
    return pts


def fabriquer_corps(params, dossier, description_en, style, photo=None):
    """Le corps (PNG transparent) dans `dossier` ; renvoie le nom du fichier."""
    from . import ia
    from .motion_pro import retirer_vert
    os.makedirs(dossier, exist_ok=True)
    consigne = consigne_corps(description_en, style, depuis_photo=bool(photo))
    octets = ia.generer_image_refs(params, consigne, [photo]) if photo else ia.generer_image(params, consigne)
    brut = os.path.join(dossier, "corps_brut.png")
    with open(brut, "wb") as f:
        f.write(octets)
    retirer_vert(brut, os.path.join(dossier, "corps.png"))
    return "corps.png"


def fabriquer_visage(params, dossier, style):
    """Yeux et bouches, d'après le corps : {"yeux": {forme: fichier}, "bouches": {forme: fichier}}."""
    from . import ia
    from .motion_pro import retirer_vert
    octets = ia.generer_image_refs(params, consigne_visage(style), [os.path.join(dossier, "corps.png")])
    brut = os.path.join(dossier, "visage_brut.png")
    with open(brut, "wb") as f:
        f.write(octets)
    net = os.path.join(dossier, "visage.png")
    retirer_vert(brut, net)
    return enregistrer_visage(dossier, separer_planche(net, [len(P.YEUX), len(P.BOUCHES)]))


def enregistrer_visage(dossier, rangees):
    yeux, bouches = {}, {}
    for forme, img in zip(P.YEUX, rangees[0]):
        yeux[forme] = f"yeux_{forme}.png"
        img.save(os.path.join(dossier, yeux[forme]))
    for forme, img in zip(P.BOUCHES, rangees[1]):
        bouches[forme] = f"bouche_{forme}.png"
        img.save(os.path.join(dossier, bouches[forme]))
    return {"yeux": yeux, "bouches": bouches}


def trouver_points(params, dossier, image="corps.png"):
    from . import ia
    from PySide6.QtGui import QImage
    chemin = os.path.join(dossier, image)
    q = QImage(chemin)
    r = ia.demander(params, consigne_points(), "Articulations de ce personnage.", [chemin], json_attendu=True, max_jetons=800)
    return lire_points(r, q.width(), q.height())


def ajuster_visage(pantin):
    """Taille des yeux et de la bouche d'après la largeur de la tête découpée (les planches n'ont pas d'échelle)."""
    from PySide6.QtGui import QImage
    tete = pantin["pieces"].get("tete")
    if not tete:
        return pantin
    q = QImage(os.path.join(pantin["dossier"], tete["png"]))
    v = pantin.setdefault("visage", P.visage_par_defaut(pantin))
    v["largeur_yeux"] = q.width() * 0.62
    v["largeur_bouche"] = q.width() * 0.30
    return pantin
