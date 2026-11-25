"""Personnage animé, façon pantin articulé (1.3.0, décisions de Philippe du 25/11/2026).

Le personnage est un dessin en pose en T (bras écartés, jambes un peu ouvertes), sans yeux ni bouche ; PhilCut le découpe
en pièces aux articulations (corps, tête, bras, avant-bras, cuisses, jambes), chaque pièce tourne autour de son pivot.
Les yeux et les bouches sont des pièces à part, posées sur la tête : la bouche suit la voix (formes de Rhubarb Lip Sync :
X repos, A à F), les yeux clignent et changent avec l'expression.

Tout est calculé ici, en local et gratuit : la découpe, les mouvements, le rendu image par image (l'aperçu de la fenêtre
est la vidéo finale). Seule la fabrication des dessins passe par une IA (pantin_ia.py), avec le prix demandé avant.

Repères : coordonnées de l'image d'origine en pixels, y vers le bas ; un angle positif tourne dans le sens des aiguilles
d'une montre à l'écran. « g » et « d » sont les côtés de l'écran (le bras « g » pointe vers la gauche en pose en T).
"""
import json
import math
import os
import shutil
import subprocess

from .langue import _

# ------------------------------------------------------------------ squelette
POINTS = ("tete", "cou", "epaule_g", "coude_g", "poignet_g", "epaule_d", "coude_d", "poignet_d", "bassin",
          "hanche_g", "genou_g", "cheville_g", "hanche_d", "genou_d", "cheville_d")
NOMS_POINTS = {"tete": "Haut de la tête", "cou": "Cou", "epaule_g": "Epaule gauche", "coude_g": "Coude gauche",
               "poignet_g": "Poignet gauche", "epaule_d": "Epaule droite", "coude_d": "Coude droit",
               "poignet_d": "Poignet droit", "bassin": "Bassin", "hanche_g": "Hanche gauche", "genou_g": "Genou gauche",
               "cheville_g": "Cheville gauche", "hanche_d": "Hanche droite", "genou_d": "Genou droit",
               "cheville_d": "Cheville droite"}
# pièce : (parent, pivot, os pour la découpe [segments], ordre d'affichage)
PIECES = {
    "corps": (None, "bassin", (("cou", "bassin"), ("epaule_g", "epaule_d"), ("hanche_g", "hanche_d")), 3),
    "tete": ("corps", "cou", (("cou", "tete"),), 6),
    "bras_haut_g": ("corps", "epaule_g", (("epaule_g", "coude_g"),), 4),
    "bras_bas_g": ("bras_haut_g", "coude_g", (("coude_g", "poignet_g", 1.6),), 5),
    "bras_haut_d": ("corps", "epaule_d", (("epaule_d", "coude_d"),), 4),
    "bras_bas_d": ("bras_haut_d", "coude_d", (("coude_d", "poignet_d", 1.6),), 5),
    "cuisse_g": ("corps", "hanche_g", (("hanche_g", "genou_g"),), 1),
    "jambe_g": ("cuisse_g", "genou_g", (("genou_g", "cheville_g", 1.5),), 2),
    "cuisse_d": ("corps", "hanche_d", (("hanche_d", "genou_d"),), 1),
    "jambe_d": ("cuisse_d", "genou_d", (("genou_d", "cheville_d", 1.5),), 2),
}
ARTICULATIONS = tuple(k for k in PIECES if k != "corps")
BOUCHES = ("X", "A", "B", "C", "D", "E", "F")          # formes de Rhubarb Lip Sync (X : repos, bouche fermée)
YEUX = ("ouverts", "fermes", "joie", "surprise", "colere", "triste")
EXPRESSIONS = {"neutre": "ouverts", "joie": "joie", "surprise": "surprise", "colere": "colere", "triste": "triste"}
NOMS_EXPRESSIONS = {"colere": "Colère", "joie": "Joie", "neutre": "Neutre", "surprise": "Surprise", "triste": "Tristesse"}

# ------------------------------------------------------------------ mouvements tout faits
# Angles en degrés, relatifs à la pose en T. Bras « g » vers le bas : angle négatif ; bras « d » vers le bas : positif.
# « y » : saut ou rebond, en part de la hauteur du personnage (négatif : vers le haut) ; « x » : pas de côté.
REPOS = {"bras_haut_g": -72, "bras_bas_g": -8, "bras_haut_d": 72, "bras_bas_d": 8}


def _p(**k):
    d = dict(REPOS)
    d.update(k)
    return d


MOUVEMENTS = {
    "applaudir": {"nom": "Applaudir", "duree": 1.2, "boucle": True, "cles": [
        (0.0, _p(bras_haut_g=-35, bras_bas_g=-95, bras_haut_d=35, bras_bas_d=95)),
        (0.5, _p(bras_haut_g=-38, bras_bas_g=-120, bras_haut_d=38, bras_bas_d=120)),
        (1.0, _p(bras_haut_g=-35, bras_bas_g=-95, bras_haut_d=35, bras_bas_d=95))], "pas": 0.25},
    "attendre": {"nom": "Attendre (respirer)", "duree": 3.0, "boucle": True, "cles": [
        (0.0, _p(y=0.0)), (0.5, _p(y=-0.006, bras_haut_g=-70, bras_haut_d=70, tete=-2)), (1.0, _p(y=0.0))]},
    "courir": {"nom": "Courir", "duree": 0.6, "boucle": True, "cles": [
        (0.0, _p(cuisse_g=14, jambe_g=-10, cuisse_d=-4, jambe_d=2, bras_haut_g=-60, bras_bas_g=-95, bras_haut_d=80,
                 bras_bas_d=40, y=-0.035)),
        (0.25, _p(y=0.0, bras_bas_g=-60, bras_bas_d=60)),
        (0.5, _p(cuisse_g=4, jambe_g=-2, cuisse_d=-14, jambe_d=10, bras_haut_g=-80, bras_bas_g=-40, bras_haut_d=60,
                 bras_bas_d=95, y=-0.035)),
        (0.75, _p(y=0.0, bras_bas_g=-60, bras_bas_d=60)),
        (1.0, _p(cuisse_g=14, jambe_g=-10, cuisse_d=-4, jambe_d=2, bras_haut_g=-60, bras_bas_g=-95, bras_haut_d=80,
                 bras_bas_d=40, y=-0.035))]},
    "danser": {"nom": "Danser", "duree": 1.6, "boucle": True, "cles": [
        (0.0, _p(bras_haut_g=-20, bras_bas_g=-60, bras_haut_d=20, bras_bas_d=60, corps=-6, tete=6, y=0.0)),
        (0.25, _p(bras_haut_g=10, bras_bas_g=-30, bras_haut_d=60, bras_bas_d=20, corps=0, y=-0.02, cuisse_g=10,
                  jambe_g=-15)),
        (0.5, _p(bras_haut_g=-20, bras_bas_g=-60, bras_haut_d=20, bras_bas_d=60, corps=6, tete=-6, y=0.0)),
        (0.75, _p(bras_haut_g=-60, bras_bas_g=-20, bras_haut_d=-10, bras_bas_d=30, corps=0, y=-0.02, cuisse_d=-10,
                  jambe_d=15)),
        (1.0, _p(bras_haut_g=-20, bras_bas_g=-60, bras_haut_d=20, bras_bas_d=60, corps=-6, tete=6, y=0.0))]},
    "marcher": {"nom": "Marcher", "duree": 1.0, "boucle": True, "cles": [
        (0.0, _p(cuisse_g=7, jambe_g=-5, cuisse_d=-2, bras_haut_g=-64, bras_haut_d=80, y=0.0, corps=-1.5)),
        (0.25, _p(y=-0.012)),
        (0.5, _p(cuisse_g=2, cuisse_d=-7, jambe_d=5, bras_haut_g=-80, bras_haut_d=64, y=0.0, corps=1.5)),
        (0.75, _p(y=-0.012)),
        (1.0, _p(cuisse_g=7, jambe_g=-5, cuisse_d=-2, bras_haut_g=-64, bras_haut_d=80, y=0.0, corps=-1.5))]},
    "montrer": {"nom": "Montrer du doigt", "duree": 1.5, "boucle": False, "cles": [
        (0.0, _p()), (0.35, _p(bras_haut_d=-8, bras_bas_d=-4, tete=4, corps=2)),
        (1.0, _p(bras_haut_d=-8, bras_bas_d=-4, tete=4, corps=2))]},
    "parler": {"nom": "Parler avec les mains", "duree": 2.4, "boucle": True, "cles": [
        (0.0, _p(bras_haut_g=-55, bras_bas_g=-70, bras_haut_d=60, bras_bas_d=65)),
        (0.3, _p(bras_haut_g=-45, bras_bas_g=-95, bras_haut_d=62, bras_bas_d=60, tete=-3)),
        (0.6, _p(bras_haut_g=-58, bras_bas_g=-65, bras_haut_d=45, bras_bas_d=95, tete=3)),
        (1.0, _p(bras_haut_g=-55, bras_bas_g=-70, bras_haut_d=60, bras_bas_d=65))]},
    "reflechir": {"nom": "Réfléchir", "duree": 2.0, "boucle": False, "cles": [
        (0.0, _p()), (0.3, _p(bras_haut_d=95, bras_bas_d=-165, tete=8, bras_haut_g=-80, bras_bas_g=-75)),
        (1.0, _p(bras_haut_d=95, bras_bas_d=-165, tete=8, bras_haut_g=-80, bras_bas_g=-75))],
        "expression": "neutre"},
    "saluer": {"nom": "Saluer", "duree": 2.0, "boucle": False, "cles": [
        (0.0, _p()), (0.15, _p(bras_haut_d=-50, bras_bas_d=-60)),
        (0.3, _p(bras_haut_d=-50, bras_bas_d=-30)), (0.45, _p(bras_haut_d=-50, bras_bas_d=-75)),
        (0.6, _p(bras_haut_d=-50, bras_bas_d=-30)), (0.75, _p(bras_haut_d=-50, bras_bas_d=-75)),
        (1.0, _p())], "expression": "joie"},
    "sauter": {"nom": "Sauter", "duree": 1.0, "boucle": False, "cles": [
        (0.0, _p()), (0.2, _p(y=0.03, cuisse_g=25, jambe_g=-45, cuisse_d=-25, jambe_d=45, bras_haut_g=-40,
                              bras_haut_d=40)),
        (0.5, _p(y=-0.22, bras_haut_g=-150, bras_haut_d=150, cuisse_g=5, cuisse_d=-5)),
        (0.8, _p(y=0.02, cuisse_g=20, jambe_g=-35, cuisse_d=-20, jambe_d=35)), (1.0, _p())], "expression": "joie"},
    "sursauter": {"nom": "Sursauter", "duree": 1.2, "boucle": False, "cles": [
        (0.0, _p()), (0.12, _p(y=-0.05, bras_haut_g=-20, bras_bas_g=-40, bras_haut_d=20, bras_bas_d=40, tete=-6,
                               corps=-3)),
        (0.6, _p(y=0.0, bras_haut_g=-30, bras_bas_g=-60, bras_haut_d=30, bras_bas_d=60)), (1.0, _p())],
        "expression": "surprise"},
}


def liste_mouvements():
    """[(clef, nom traduit)] par ordre alphabétique du nom affiché."""
    import unicodedata
    return sorted(((k, _(v["nom"])) for k, v in MOUVEMENTS.items()),
                  key=lambda x: unicodedata.normalize("NFD", x[1].lower()).encode("ascii", "ignore"))


def _lisse(u):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, u)))


def pose_mouvement(clef, u):
    """Pose d'un mouvement à la fraction u (0..1) de sa durée : angles et décalages, interpolés en douceur."""
    m = MOUVEMENTS.get(clef)
    if not m:
        return dict(REPOS)
    cles = sorted(m["cles"], key=lambda c: c[0])
    u = max(0.0, min(1.0, u))
    for (t0, p0), (t1, p1) in zip(cles, cles[1:]):
        if t0 <= u <= t1:
            k = _lisse((u - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return melanger(_complet(p0), _complet(p1), k)
    return _complet(cles[-1][1])


def _complet(p):
    d = {k: 0.0 for k in PIECES}
    d.update({"x": 0.0, "y": 0.0})
    d.update(p)
    return d


def melanger(a, b, k):
    a, b = _complet(a), _complet(b)
    return {c: a.get(c, 0.0) + (b.get(c, 0.0) - a.get(c, 0.0)) * k for c in set(a) | set(b)}


# ------------------------------------------------------------------ un pantin : données
def nouveau(nom, dossier, image, points, style=""):
    return {"version": 1, "nom": nom, "style": style, "dossier": dossier, "image": image, "points": dict(points),
            "pieces": {}, "bouches": {}, "yeux": {}, "visage": {}}


def charger(chemin):
    with open(chemin, encoding="utf-8") as f:
        p = json.load(f)
    p["dossier"] = os.path.dirname(os.path.abspath(chemin))
    return p


def enregistrer(pantin, chemin=None):
    chemin = chemin or os.path.join(pantin["dossier"], "pantin.json")
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    d = dict(pantin)
    d.pop("dossier", None)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)
    return chemin


def _chemin(pantin, nom):
    return nom if os.path.isabs(nom) else os.path.join(pantin["dossier"], nom)


# ------------------------------------------------------------------ découpe
def _masque(chemin):
    """(rgba numpy HxWx4 uint8, alpha booléen) d'un PNG transparent."""
    import numpy as np
    from PySide6.QtGui import QImage
    q = QImage(chemin).convertToFormat(QImage.Format_RGBA8888)
    if q.isNull():
        raise ValueError(_("Image illisible : {f}", f=chemin))
    w, h = q.width(), q.height()
    a = np.frombuffer(q.constBits(), np.uint8, count=q.bytesPerLine() * h).reshape(h, q.bytesPerLine())[:, :w * 4]
    a = np.array(a.reshape(h, w, 4))
    return a, a[..., 3] > 24


def _distance_segment(xs, ys, a, b):
    import numpy as np
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-6:
        return np.hypot(xs - ax, ys - ay)
    t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / l2, 0.0, 1.0)
    return np.hypot(xs - (ax + t * dx), ys - (ay + t * dy))


def _os(points, seg):
    a, b = points[seg[0]], points[seg[1]]
    if len(seg) > 2:          # prolongé au-delà du dernier point (main, pied)
        k = seg[2]
        b = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    return a, b


def epaisseur(alpha, centre, direction):
    """Demi-épaisseur du dessin en `centre`, mesurée perpendiculairement à `direction` (en pixels)."""
    h, w = alpha.shape
    dx, dy = direction
    n = math.hypot(dx, dy) or 1.0
    px, py = -dy / n, dx / n
    total = 0
    for sens in (1, -1):
        for k in range(1, max(w, h)):
            x, y = int(round(centre[0] + sens * px * k)), int(round(centre[1] + sens * py * k))
            if not (0 <= x < w and 0 <= y < h) or not alpha[y, x]:
                break
            total += 1
    return max(4.0, total / 2.0)


def decouper(pantin):
    """Découpe l'image en pose en T en pièces PNG (dans le dossier du pantin). Chaque pixel va à l'os le plus proche ;
    chaque pièce enfant garde un bout arrondi autour de son pivot, qui recouvre la jointure quand elle tourne."""
    import numpy as np
    from PySide6.QtGui import QImage
    rgba, alpha = _masque(_chemin(pantin, pantin["image"]))
    h, w = alpha.shape
    pts = {k: tuple(map(float, v)) for k, v in pantin["points"].items()}
    manque = [k for k in POINTS if k not in pts]
    if manque:
        raise ValueError(_("Points du squelette manquants : {m}", m=", ".join(manque)))
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    noms = list(PIECES)
    dist = np.full((len(noms), h, w), np.inf, np.float32)
    for i, n in enumerate(noms):
        for seg in PIECES[n][2]:
            a, b = _os(pts, seg)
            dd = _distance_segment(xs, ys, a, b)
            if PIECES[n][0]:        # un membre ne prend rien « derrière » son pivot (la tête ou le buste à côté de l'épaule)
                vx, vy = b[0] - a[0], b[1] - a[1]
                dd = np.where((xs - a[0]) * vx + (ys - a[1]) * vy < 0, np.inf, dd)
            dist[i] = np.minimum(dist[i], dd)
    proche = np.argmin(dist, axis=0)
    pieces = {}
    for i, n in enumerate(noms):
        parent, pivot, segs, z = PIECES[n]
        m = alpha & (proche == i)
        if parent:                # bout arrondi : le disque de la jointure, pris aussi au parent
            a, b = _os(pts, segs[0])
            lg = math.hypot(b[0] - a[0], b[1] - a[1])
            mesure = (a[0] + (b[0] - a[0]) * 0.3, a[1] + (b[1] - a[1]) * 0.3)     # épaisseur du membre, pas du buste
            r = min(epaisseur(alpha, mesure, (b[0] - a[0], b[1] - a[1])) * 1.1, lg * 0.45)
            m = m | (alpha & (np.hypot(xs - pts[pivot][0], ys - pts[pivot][1]) <= r))
        yy, xx = np.nonzero(m)
        if not len(xx):
            raise ValueError(_("Pièce vide : {p} (points du squelette à vérifier)", p=n))
        x0, x1, y0, y1 = xx.min(), xx.max() + 1, yy.min(), yy.max() + 1
        morceau = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        sous = m[y0:y1, x0:x1]
        morceau[sous] = rgba[y0:y1, x0:x1][sous]
        morceau = np.ascontiguousarray(morceau)
        fichier = f"piece_{n}.png"
        QImage(morceau.data, x1 - x0, y1 - y0, (x1 - x0) * 4, QImage.Format_RGBA8888).copy().save(
            os.path.join(pantin["dossier"], fichier), "PNG")
        pieces[n] = {"png": fichier, "origine": [int(x0), int(y0)], "pivot": list(pts[pivot]), "parent": parent, "z": z}
    pantin["pieces"] = pieces
    if not pantin.get("visage"):
        pantin["visage"] = visage_par_defaut(pantin)
    return pantin


def visage_par_defaut(pantin):
    """Place des yeux et de la bouche sur la tête : d'après la forme de la tête (modifiable à la souris)."""
    p = pantin["points"]
    tx, ty = p["tete"]
    cx, cy = p["cou"]
    haut = math.hypot(cx - tx, cy - ty) or 100.0
    return {"yeux": [tx + (cx - tx) * 0.45, ty + (cy - ty) * 0.45], "bouche": [tx + (cx - tx) * 0.72, ty + (cy - ty) * 0.72],
            "largeur_yeux": haut * 0.62, "largeur_bouche": haut * 0.30}


def hauteur(pantin):
    p = pantin["points"]
    bas = max(p["cheville_g"][1], p["cheville_d"][1])
    return max(1.0, bas - p["tete"][1]) * 1.08


# ------------------------------------------------------------------ pistes : ce que fait le personnage dans le temps
def piste_vide():
    return {"actions": [], "expressions": [], "bouches": [], "place": {"x": 0.5, "y": 0.92, "echelle": 0.8, "miroir": False},
            "deplacements": [], "clignement": True}


def pose_a(piste, t, transition=0.3):
    """Pose du personnage à l'instant t : l'action en cours (ou le repos), avec un fondu entre deux actions."""
    actions = sorted(piste.get("actions", []), key=lambda a: a["debut"])

    def pose_de(a, tt):
        m = MOUVEMENTS.get(a["mouvement"], {})
        d = max(0.05, float(a.get("duree") or m.get("duree", 1.0)))
        dm = float(m.get("duree", d))
        if m.get("boucle"):
            u = ((tt - a["debut"]) % dm) / dm
        else:
            u = (tt - a["debut"]) / d
        return pose_mouvement(a["mouvement"], u)
    en_cours, avant = None, None
    for a in actions:
        if a["debut"] <= t:
            if t < a["debut"] + float(a.get("duree") or 0):
                en_cours = a
            else:
                avant = a
    repos = _complet(REPOS)
    if en_cours:
        p = pose_de(en_cours, t)
        prec = [a for a in actions if a["debut"] + float(a.get("duree") or 0) <= en_cours["debut"] + 1e-6]
        depuis = prec[-1] if prec and en_cours["debut"] - (prec[-1]["debut"] + prec[-1]["duree"]) < transition else None
        k = (t - en_cours["debut"]) / transition
        if k < 1.0:
            base = pose_de(depuis, depuis["debut"] + depuis["duree"] - 1e-3) if depuis else repos
            p = melanger(base, p, _lisse(k))
        return p
    if avant:
        fin = avant["debut"] + float(avant.get("duree") or 0)
        k = (t - fin) / transition
        if k < 1.0:
            return melanger(pose_de(avant, fin - 1e-3), repos, _lisse(k))
    return repos


def expression_a(piste, t):
    e = "neutre"
    for a in sorted(piste.get("expressions", []), key=lambda a: a["t"]):
        if a["t"] <= t:
            e = a["expression"]
    for a in piste.get("actions", []):          # un mouvement peut porter son expression (saluer : joie)
        m = MOUVEMENTS.get(a["mouvement"], {})
        if m.get("expression") and a["debut"] <= t < a["debut"] + a["duree"] and not any(
                a["debut"] <= x["t"] <= t for x in piste.get("expressions", [])):
            e = m["expression"]
    return e


def bouche_a(piste, t):
    forme = "X"
    for (t0, f) in piste.get("bouches", []):
        if t0 <= t:
            forme = f
        else:
            break
    return forme


def yeux_fermes(piste, t):
    """Clignement automatique : environ toutes les 3,5 s, 0,12 s, à des instants réguliers mais pas mécaniques."""
    if not piste.get("clignement", True):
        return False
    base = 3.5
    n = int(t // base)
    decale = ((n * 7919) % 13) / 13.0 * 1.2
    debut = n * base + 0.8 + decale
    return debut <= t < debut + 0.12


def place_a(piste, t):
    """Position (fractions de l'image), échelle, miroir, à l'instant t (déplacements interpolés)."""
    p = dict(piste.get("place") or {})
    cles = sorted(piste.get("deplacements", []), key=lambda d: d["t"])
    if cles:
        if t <= cles[0]["t"]:
            p.update({k: cles[0][k] for k in ("x", "y", "echelle") if k in cles[0]})
        elif t >= cles[-1]["t"]:
            p.update({k: cles[-1][k] for k in ("x", "y", "echelle") if k in cles[-1]})
        else:
            for a, b in zip(cles, cles[1:]):
                if a["t"] <= t <= b["t"]:
                    k = _lisse((t - a["t"]) / max(1e-6, b["t"] - a["t"]))
                    for c in ("x", "y", "echelle"):
                        if c in a and c in b:
                            p[c] = a[c] + (b[c] - a[c]) * k
                    break
    return p


# ------------------------------------------------------------------ dessin
class Dessinateur:
    """Garde les images des pièces en mémoire et dessine un pantin dans une pose donnée."""

    def __init__(self, pantin):
        from PySide6.QtGui import QPixmap, QImage
        self.p = pantin
        self.img = {}
        for n, d in pantin.get("pieces", {}).items():
            self.img[n] = QImage(_chemin(pantin, d["png"]))
        self.bouches = {f: QImage(_chemin(pantin, c)) for f, c in pantin.get("bouches", {}).items()}
        self.yeux = {f: QImage(_chemin(pantin, c)) for f, c in pantin.get("yeux", {}).items()}
        self.H = hauteur(pantin)
        pts = pantin["points"]
        self.pieds = (pts["bassin"][0], max(pts["cheville_g"][1], pts["cheville_d"][1]) + self.H * 0.03)

    def _transformations(self, pose):
        """Transformations (QTransform) de chaque pièce, dans le repère de l'image d'origine."""
        from PySide6.QtGui import QTransform
        tr = {}

        def de(n):
            if n in tr:
                return tr[n]
            d = self.p["pieces"][n]
            px, py = d["pivot"]
            local = QTransform().translate(px, py).rotate(pose.get(n, 0.0)).translate(-px, -py)
            tr[n] = local * de(d["parent"]) if d["parent"] else local
            return tr[n]
        for n in self.p.get("pieces", {}):
            de(n)
        return tr

    def dessiner(self, painter, pose, cadre, place, expression="neutre", bouche="X", fermes=False):
        """Dessine dans `cadre` (QRectF de l'image finale) : place = {x, y (fractions, pieds), echelle (part de la
        hauteur du cadre), miroir}."""
        from PySide6.QtGui import QTransform
        from PySide6.QtCore import QPointF, QRectF
        ech = cadre.height() * float(place.get("echelle", 0.8)) / self.H
        bx = cadre.left() + cadre.width() * float(place.get("x", 0.5)) + pose.get("x", 0.0) * self.H * ech
        by = cadre.top() + cadre.height() * float(place.get("y", 0.92)) + pose.get("y", 0.0) * self.H * ech
        monde = QTransform().translate(bx, by).scale(-ech if place.get("miroir") else ech, ech).translate(
            -self.pieds[0], -self.pieds[1])
        tr = self._transformations(pose)
        for n in sorted(self.p.get("pieces", {}), key=lambda n: self.p["pieces"][n]["z"]):
            d = self.p["pieces"][n]
            painter.save()
            painter.setTransform(tr[n] * monde, True)
            painter.drawImage(QPointF(*d["origine"]), self.img[n])
            painter.restore()
        v = self.p.get("visage") or {}
        if "tete" in tr and v:
            painter.save()
            painter.setTransform(tr["tete"] * monde, True)
            oeil = self.yeux.get("fermes" if fermes else EXPRESSIONS.get(expression, "ouverts")) or self.yeux.get("ouverts")
            if oeil is not None and not oeil.isNull():
                lw = v["largeur_yeux"]
                lh = lw * oeil.height() / max(1, oeil.width())
                painter.drawImage(QRectF(v["yeux"][0] - lw / 2, v["yeux"][1] - lh / 2, lw, lh), oeil)
            b = self.bouches.get(bouche) or self.bouches.get("X")
            if b is not None and not b.isNull():
                lw = v["largeur_bouche"]
                lh = lw * b.height() / max(1, b.width())
                painter.drawImage(QRectF(v["bouche"][0] - lw / 2, v["bouche"][1] - lh / 2, lw, lh), b)
            painter.restore()


# ------------------------------------------------------------------ scène : fond et personnages
def scene_vide(L=1920, H=1080):
    return {"version": 1, "taille": [L, H], "cadence": 30, "duree": 6.0, "fond": {"type": "couleur", "couleur": "#F4EFE6"},
            "personnages": [], "son": ""}


def duree_scene(scene):
    d = float(scene.get("duree") or 0)
    for c in scene.get("personnages", []):
        for a in c["piste"].get("actions", []):
            d = max(d, a["debut"] + a["duree"])
    return max(0.5, d)


class RenduScene:
    def __init__(self, scene):
        from PySide6.QtGui import QImage
        self.s = scene
        self.L, self.H = scene.get("taille") or (1920, 1080)
        self.persos = []
        for c in scene.get("personnages", []):
            try:
                self.persos.append((Dessinateur(charger(c["pantin"])), c["piste"]))
            except (OSError, ValueError, KeyError):
                continue
        f = scene.get("fond") or {}
        self.fond = QImage(f["image"]) if f.get("type") == "image" and f.get("image") else None

    def dessiner(self, painter, t, L=None, H=None):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor
        L, H = L or self.L, H or self.H
        cadre = QRectF(0, 0, L, H)
        f = self.s.get("fond") or {}
        if f.get("type") == "couleur":
            painter.fillRect(cadre, QColor(f.get("couleur") or "#FFFFFF"))
        elif self.fond is not None and not self.fond.isNull():
            k = max(L / self.fond.width(), H / self.fond.height())
            w, h = self.fond.width() * k, self.fond.height() * k
            painter.drawImage(QRectF((L - w) / 2, (H - h) / 2, w, h), self.fond)
        ordre = sorted(self.persos, key=lambda dp: place_a(dp[1], t).get("y", 0.9))
        for d, piste in ordre:
            d.dessiner(painter, pose_a(piste, t), cadre, place_a(piste, t), expression_a(piste, t), bouche_a(piste, t),
                       yeux_fermes(piste, t))


def image_scene(scene, t, taille=None):
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import Qt
    rd = RenduScene(scene)
    L, H = taille or (rd.L, rd.H)
    img = QImage(int(L), int(H), QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    rd.dessiner(p, t, L, H)
    p.end()
    return img


def fabriquer(scene, sortie, progression=None, arret=lambda: False):
    """La vidéo, image par image : MP4 (avec le son de la scène s'il y en a), ou MOV ProRes 4444 transparent quand le
    fond est transparent (pour poser le personnage sur le film)."""
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import Qt
    from . import moteur
    rd = RenduScene(scene)
    L, H = rd.L // 2 * 2, rd.H // 2 * 2
    cadence = int(scene.get("cadence") or 30)
    nb = max(1, int(round(duree_scene(scene) * cadence)))
    transparent = (scene.get("fond") or {}).get("type") == "transparent"
    sons = sons_scene(scene)
    duree = nb / cadence
    entree = ["-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{L}x{H}", "-r", str(cadence), "-i", "pipe:0"]
    audio, filtre = [], []
    for i, (son, debut) in enumerate(sons):         # voix des personnages et son de la scène, chacun à son instant
        audio += ["-i", son]
        ms = int(round(max(0.0, debut) * 1000))
        filtre.append(f"[{i + 1}:a]aresample=48000,adelay={ms}|{ms}[s{i}]")
    if sons:
        filtre.append("".join(f"[s{i}]" for i in range(len(sons))) + f"amix=inputs={len(sons)}:normalize=0,"
                      f"apad,atrim=0:{duree:.3f}[a]")
        carte = ["-filter_complex", ";".join(filtre), "-map", "0:v", "-map", "[a]"]
    else:
        carte = []
    if transparent:
        sortie = os.path.splitext(sortie)[0] + ".mov"
        enc = carte + ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"] + (
            ["-c:a", "pcm_s16le"] if sons else []) + ["-t", f"{duree:.3f}", sortie]
    else:
        if not sons:
            audio = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            carte = ["-map", "0:v", "-map", "1:a"]
        enc = carte + ["-t", f"{duree:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", sortie]
    cmd = [moteur.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y"] + entree + audio + enc
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            **moteur._sans_console())
    img = QImage(L, H, QImage.Format_ARGB32)
    try:
        for k in range(nb):
            if arret():
                raise InterruptedError()
            img.fill(Qt.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            rd.dessiner(p, k / cadence, L, H)
            p.end()
            proc.stdin.write(bytes(img.constBits())[: L * H * 4])
            if progression and k % 5 == 0:
                progression(k / nb, _("Image {k} sur {n}", k=k, n=nb))
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        if proc.wait() != 0 or not os.path.exists(sortie):
            raise RuntimeError(_("Encodage impossible : {e}", e=err[-300:]))
    except BaseException:
        try:
            proc.kill()
        except OSError:
            pass
        raise
    return sortie


def sons_scene(scene):
    """[(fichier, début)] : le son de la scène (à 0) et la voix de chaque personnage, s'ils existent."""
    out = []
    if scene.get("son") and os.path.exists(scene["son"]):
        out.append((scene["son"], 0.0))
    for c in scene.get("personnages", []):
        v = (c.get("piste") or {}).get("voix") or {}
        if v.get("son") and os.path.exists(v["son"]):
            out.append((v["son"], float(v.get("debut") or 0.0)))
    return out


# ------------------------------------------------------------------ rangement : mes personnages, mes scènes
def dossier_pantins():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "pantins")
    os.makedirs(d, exist_ok=True)
    return d


def nouveau_dossier(nom):
    import re
    import time
    slug = re.sub(r"[^a-z0-9]+", "_", nom.lower()).strip("_")[:30] or "personnage"
    d = os.path.join(dossier_pantins(), f"{time.strftime('%Y%m%d_%H%M%S')}_{slug}")
    os.makedirs(d, exist_ok=True)
    return d


def mes_personnages():
    """[(chemin de pantin.json, nom)] par ordre alphabétique."""
    import unicodedata
    out = []
    for n in os.listdir(dossier_pantins()):
        c = os.path.join(dossier_pantins(), n, "pantin.json")
        if os.path.exists(c):
            try:
                out.append((c, charger(c).get("nom") or n))
            except (OSError, ValueError):
                continue
    return sorted(out, key=lambda x: unicodedata.normalize("NFD", x[1].lower()).encode("ascii", "ignore"))


def dossier_scenes():
    d = os.path.join(dossier_pantins(), "_scenes")
    os.makedirs(d, exist_ok=True)
    return d


def enregistrer_scene(scene, chemin):
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(scene, f, ensure_ascii=False, indent=1)
    os.replace(tmp, chemin)
    return chemin


def charger_scene(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ bouche : Rhubarb Lip Sync
def rhubarb():
    """Exécutable de Rhubarb Lip Sync (moteur « bouches » installé par PhilCut), ou None."""
    from . import packs_ia
    try:
        if not packs_ia.moteur_installe("bouches"):
            return None
        exe = packs_ia.executable("bouches")
    except Exception:          # noqa: BLE001
        return None
    return exe if exe and os.path.exists(exe) else None


def lire_rhubarb(texte):
    """Sortie TSV de Rhubarb (« 0.00\\tX ») → [(t, forme)] ; G et H (formes étendues) ramenées à F et C."""
    out = []
    for ligne in (texte or "").splitlines():
        morceaux = ligne.strip().split()
        if len(morceaux) >= 2:
            try:
                t = float(morceaux[0])
            except ValueError:
                continue
            f = {"G": "F", "H": "C"}.get(morceaux[1].upper(), morceaux[1].upper())
            if f in BOUCHES:
                out.append((t, f))
    return out


def bouches_depuis_son(son, texte="", progression=None, arret=lambda: False):
    """Formes de bouche d'une voix (WAV conseillé). Reconnaissance « phonétique » : elle marche pour toutes les langues."""
    exe = rhubarb()
    if not exe:
        raise RuntimeError(_("Le moteur des bouches (Rhubarb Lip Sync) n'est pas installé : Aide › Mises à jour des IA."))
    from . import moteur
    import tempfile
    d = tempfile.mkdtemp(prefix="philcut_rhubarb_")
    try:
        wav = os.path.join(d, "voix.wav")
        r = subprocess.run([moteur.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", son, "-ac", "1", "-ar", "16000",
                            "-c:a", "pcm_s16le", wav], capture_output=True, **moteur._sans_console())
        if r.returncode != 0:
            raise RuntimeError(_("Son illisible : {e}", e=r.stderr.decode("utf-8", "replace")[-200:]))
        cmd = [exe, "-r", "phonetic", "-f", "tsv", "--extendedShapes", "GHX", wav]      # le texte ne sert qu'en anglais
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(exe),
                                **moteur._sans_console())
        sortie, err = proc.communicate()
        if arret():
            raise InterruptedError()
        if proc.returncode != 0:
            raise RuntimeError(_("Synchro des bouches impossible : {e}", e=err.decode("utf-8", "replace")[-300:]))
        return lire_rhubarb(sortie.decode("utf-8", "replace"))
    finally:
        shutil.rmtree(d, ignore_errors=True)
