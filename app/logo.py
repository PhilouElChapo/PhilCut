"""Logos : description éditable (JSON) et rendu (QPainter), gabarits, propositions par l'IA (cahier des charges 17.1).

Un logo : {"nom", "largeur", "hauteur", "fond": None | "#rrggbb", "elements": [...]}, éléments dessinés dans l'ordre :
- texte : {"type": "texte", "texte", "police", "taille" (px), "gras", "italique", "couleur", "x", "y" (centre, px),
           "rotation", "effet": aucun | contour | ombre | lueur | degrade, "couleur2", "epaisseur", "espacement" (%)}
- forme : {"type": "forme", "forme": cercle | rectangle | arrondi | bandeau | etoile | losange | anneau | ailes | croix | chevron,
           "x", "y", "l", "h", "couleur", "contour", "epaisseur", "rotation", "opacite"}
- image : {"type": "image", "chemin", "x", "y", "l", "h", "rotation", "opacite"}
Le même rendu sert à l'éditeur, au PNG exporté et à l'animation de la Fabrique : ce qu'on voit est ce qu'on obtient.
"""
import copy, json, math, os, re

from .langue import _

FORMES = [("cercle", _("Cercle")), ("anneau", _("Anneau")), ("rectangle", _("Rectangle")), ("arrondi", _("Rectangle arrondi")),
          ("bandeau", _("Bandeau")), ("etoile", _("Etoile")), ("losange", _("Losange")), ("ailes", _("Ailes (aviation)")),
          ("croix", _("Croix (pharmacie)")), ("chevron", _("Chevron"))]
EFFETS = [("aucun", _("Aucun")), ("contour", _("Contour")), ("ombre", _("Ombre")), ("lueur", _("Lueur")), ("degrade", _("Dégradé"))]


def nouveau(nom="Mon logo", largeur=1024, hauteur=1024):
    return {"nom": nom, "largeur": largeur, "hauteur": hauteur, "fond": None, "elements": []}


def texte(t, x=512, y=512, taille=150, couleur="#ffffff", **extra):
    e = {"type": "texte", "texte": t, "police": "Nunito", "taille": taille, "gras": True, "italique": False, "couleur": couleur,
         "x": x, "y": y, "rotation": 0, "effet": "aucun", "couleur2": "#000000", "epaisseur": 8, "espacement": 0, "opacite": 1.0}
    e.update(extra)
    return e


def forme(f, x=512, y=512, l=600, h=600, couleur="#6d3fc6", **extra):
    e = {"type": "forme", "forme": f, "x": x, "y": y, "l": l, "h": h, "couleur": couleur, "contour": "", "epaisseur": 0,
         "rotation": 0, "opacite": 1.0}
    e.update(extra)
    return e


def gabarits(nom="PhilCut"):
    """Points de départ prêts à modifier."""
    court = nom if len(nom) <= 14 else nom[:14]
    return {
        _("Badge rond"): dict(nouveau(nom), elements=[forme("cercle", couleur="#14213d", contour="#fca311", epaisseur=24, l=860, h=860),
                                                     texte(court, y=530, taille=150 if len(court) < 9 else 110, couleur="#ffffff")]),
        _("Aviation (ailes)"): dict(nouveau(nom), elements=[forme("ailes", y=380, l=900, h=260, couleur="#d9d9d9"),
                                                           texte(court, y=640, taille=140 if len(court) < 9 else 100, couleur="#ffffff",
                                                                 effet="contour", couleur2="#1d3557", epaisseur=10)]),
        _("Pharmacie (croix)"): dict(nouveau(nom), elements=[forme("croix", y=380, l=420, h=420, couleur="#2a9d4b"),
                                                            texte(court, y=760, taille=120, couleur="#2a9d4b")]),
        _("Bandeau"): dict(nouveau(nom, 1600, 600), elements=[forme("bandeau", x=800, y=300, l=1500, h=300, couleur="#e63946"),
                                                             texte(court, x=800, y=300, taille=170, couleur="#ffffff", effet="ombre")]),
        _("Néon"): dict(nouveau(nom, 1600, 800), fond="#0b0b12",
                        elements=[forme("arrondi", x=800, y=400, l=1400, h=560, couleur="#00000000", contour="#ff4fd8", epaisseur=14),
                                  texte(court, x=800, y=400, taille=190, couleur="#ffffff", effet="lueur", couleur2="#ff4fd8")]),
        _("Texte seul"): dict(nouveau(nom, 1600, 600), elements=[texte(court, x=800, y=300, taille=220, couleur="#ffffff", effet="degrade",
                                                                      couleur2="#9b7bff")]),
    }


# ------------------------------------------------------------------ rendu
def rendre(logo, largeur=None, selection=None):
    """QImage (ARGB, fond transparent sauf « fond ») du logo ; largeur : taille de sortie (même proportions)."""
    from PySide6.QtCore import Qt, QRectF, QPointF
    from PySide6.QtGui import QImage, QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QLinearGradient, QFontMetricsF, QTransform
    L, H = int(logo.get("largeur", 1024)), int(logo.get("hauteur", 1024))
    e_sortie = (largeur / L) if largeur else 1.0
    img = QImage(max(1, int(L * e_sortie)), max(1, int(H * e_sortie)), QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(logo["fond"]) if logo.get("fond") else Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.scale(e_sortie, e_sortie)
    for i, el in enumerate(logo.get("elements") or []):
        p.save()
        p.translate(float(el.get("x", L / 2)), float(el.get("y", H / 2)))
        p.rotate(float(el.get("rotation", 0)))
        p.setOpacity(max(0.0, min(1.0, float(el.get("opacite", 1.0)))))
        t = el.get("type")
        if t == "forme":
            _forme(p, el)
        elif t == "texte":
            _texte(p, el)
        elif t == "image":
            from PySide6.QtGui import QImage as QI
            src = QI(el.get("chemin") or "")
            if not src.isNull():
                w, h = float(el.get("l", src.width())), float(el.get("h", src.height()))
                p.drawImage(QRectF(-w / 2, -h / 2, w, h), src)
        if selection == i:
            r = boite(el)
            p.setOpacity(1.0)
            p.setPen(QPen(QColor("#7cf28a"), 3 / e_sortie, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(-r[2] / 2, -r[3] / 2, r[2], r[3]))
        p.restore()
    p.end()
    return img


def _couleur(c):
    from PySide6.QtGui import QColor
    if not c:
        return QColor(0, 0, 0, 0)
    c = str(c)
    if len(c) == 9 and c.startswith("#"):          # #rrggbbaa
        q = QColor(c[:7])
        q.setAlpha(int(c[7:9], 16))
        return q
    return QColor(c)


def _chemin_forme(f, w, h):
    from PySide6.QtCore import QRectF, QPointF, Qt
    from PySide6.QtGui import QPainterPath, QPolygonF
    c = QPainterPath()
    c.setFillRule(Qt.WindingFill)         # les morceaux qui se chevauchent s'additionnent (croix, ailes)
    r = QRectF(-w / 2, -h / 2, w, h)
    if f == "cercle":
        c.addEllipse(r)
    elif f == "anneau":
        c.setFillRule(Qt.OddEvenFill)     # anneau : le trou reste vide
        c.addEllipse(r)
        c.addEllipse(r.adjusted(w * 0.14, h * 0.14, -w * 0.14, -h * 0.14))
    elif f == "rectangle":
        c.addRect(r)
    elif f == "arrondi":
        c.addRoundedRect(r, min(w, h) * 0.18, min(w, h) * 0.18)
    elif f == "bandeau":
        e = h * 0.35
        c.addPolygon(QPolygonF([QPointF(-w / 2, -h / 2), QPointF(w / 2, -h / 2), QPointF(w / 2 - e, 0), QPointF(w / 2, h / 2),
                                QPointF(-w / 2, h / 2), QPointF(-w / 2 + e, 0), QPointF(-w / 2, -h / 2)]))
    elif f == "etoile":
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = 0.5 if k % 2 == 0 else 0.21
            pts.append(QPointF(math.cos(a) * w * rr, math.sin(a) * h * rr))
        c.addPolygon(QPolygonF(pts + [pts[0]]))
    elif f == "losange":
        c.addPolygon(QPolygonF([QPointF(0, -h / 2), QPointF(w / 2, 0), QPointF(0, h / 2), QPointF(-w / 2, 0), QPointF(0, -h / 2)]))
    elif f == "croix":
        b = 0.34
        c.addRect(QRectF(-w * b / 2, -h / 2, w * b, h))
        c.addRect(QRectF(-w / 2, -h * b / 2, w, h * b))
        c = c.simplified()
    elif f == "chevron":
        c.addPolygon(QPolygonF([QPointF(-w / 2, -h / 2), QPointF(0, h * 0.1), QPointF(w / 2, -h / 2), QPointF(w / 2, -h / 6),
                                QPointF(0, h / 2), QPointF(-w / 2, -h / 6), QPointF(-w / 2, -h / 2)]))
    elif f == "ailes":                               # deux ailes stylisées et un médaillon central
        for s in (-1, 1):
            for k, (lg, ep) in enumerate(((0.47, 0.20), (0.40, 0.16), (0.32, 0.13))):
                y0 = -h * 0.28 + k * h * 0.24
                c.addPolygon(QPolygonF([QPointF(s * w * 0.08, y0), QPointF(s * w * lg, y0 - h * 0.08), QPointF(s * w * (lg - 0.04), y0 + h * ep),
                                        QPointF(s * w * 0.08, y0 + h * ep * 0.9)]))
        c.addEllipse(QRectF(-w * 0.09, -h * 0.4, w * 0.18, h * 0.8))
        c = c.simplified()
    else:
        c.addRect(r)
    return c


def _forme(p, el):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPen, QBrush
    c = _chemin_forme(el.get("forme"), float(el.get("l", 300)), float(el.get("h", 300)))
    p.setBrush(QBrush(_couleur(el.get("couleur"))))
    ep = float(el.get("epaisseur") or 0)
    p.setPen(QPen(_couleur(el.get("contour")), ep, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin) if ep > 0 and el.get("contour") else Qt.NoPen)
    p.drawPath(c)


def _police(el):
    from PySide6.QtGui import QFont
    f = QFont(el.get("police") or "Nunito")
    f.setPixelSize(max(4, int(el.get("taille", 120))))
    f.setBold(bool(el.get("gras", True)))
    f.setItalic(bool(el.get("italique", False)))
    if el.get("espacement"):
        f.setLetterSpacing(QFont.PercentageSpacing, 100 + float(el["espacement"]))
    return f


def _chemin_texte(el):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPainterPath, QFontMetricsF
    f = _police(el)
    fm = QFontMetricsF(f)
    c = QPainterPath()
    lignes = str(el.get("texte", "")).split("\n")
    haut = fm.height() * len(lignes)
    for k, ligne in enumerate(lignes):
        larg = fm.horizontalAdvance(ligne)
        c.addText(QPointF(-larg / 2, -haut / 2 + fm.ascent() + k * fm.height()), f, ligne)
    return c


def _texte(p, el):
    from PySide6.QtCore import Qt, QPointF
    from PySide6.QtGui import QPen, QBrush, QLinearGradient, QColor
    c = _chemin_texte(el)
    effet = el.get("effet") or "aucun"
    c2 = _couleur(el.get("couleur2") or "#000000")
    ep = float(el.get("epaisseur", 8) or 8)
    if effet == "ombre":
        p.save()
        p.translate(ep * 0.8, ep * 0.8)
        o = QColor(0, 0, 0, 150)
        p.fillPath(c, o)
        p.restore()
    if effet == "lueur":
        for k in range(6, 0, -1):
            g = QColor(c2)
            g.setAlpha(28)
            p.strokePath(c, QPen(g, ep * k * 0.9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if effet == "contour":
        p.strokePath(c, QPen(c2, ep * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if effet == "degrade":
        r = c.boundingRect()
        g = QLinearGradient(QPointF(0, r.top()), QPointF(0, r.bottom()))
        g.setColorAt(0, _couleur(el.get("couleur", "#ffffff")))
        g.setColorAt(1, c2)
        p.fillPath(c, QBrush(g))
    else:
        p.fillPath(c, _couleur(el.get("couleur", "#ffffff")))


def boite(el):
    """(x, y, largeur, hauteur) de l'élément, centré sur (x, y), avant rotation."""
    if el.get("type") == "texte":
        r = _chemin_texte(el).boundingRect()
        return (float(el.get("x", 0)), float(el.get("y", 0)), r.width() + 20, r.height() + 20)
    return (float(el.get("x", 0)), float(el.get("y", 0)), float(el.get("l", 100)), float(el.get("h", 100)))


def element_sous(logo, x, y):
    """Index de l'élément le plus haut sous le point (coordonnées du logo), ou None."""
    for i in range(len(logo.get("elements") or []) - 1, -1, -1):
        el = logo["elements"][i]
        cx, cy, w, h = boite(el)
        a = -math.radians(float(el.get("rotation", 0)))
        dx, dy = x - cx, y - cy
        rx, ry = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
        if abs(rx) <= w / 2 and abs(ry) <= h / 2:
            return i
    return None


# ------------------------------------------------------------------ bibliothèque
def dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "logos")
    os.makedirs(d, exist_ok=True)
    return d


def _fichier(nom):
    propre = re.sub(r"[^\w\- ]+", "_", nom).strip() or "logo"
    return os.path.join(dossier(), propre)


def enregistrer(logo, largeur_png=1024):
    """logos/<nom>.json (modifiable) + <nom>.png (transparent, prêt pour la vidéo et la Fabrique). Renvoie le PNG."""
    base = _fichier(logo.get("nom") or "logo")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(logo, f, ensure_ascii=False, indent=1)
    rendre(logo, largeur_png).save(base + ".png")
    return base + ".png"


def liste():
    out = []
    for f in sorted(os.listdir(dossier())):
        if f.endswith(".json"):
            try:
                with open(os.path.join(dossier(), f), encoding="utf-8") as g:
                    out.append(json.load(g))
            except (OSError, ValueError):
                pass
    return out


# ------------------------------------------------------------------ propositions par l'IA
CONSIGNES_IA = """Tu es graphiste. Tu dessines des logos simples et lisibles, utilisables en petit sur une vidéo (YouTube, Instagram).
Tu réponds UNIQUEMENT par un objet JSON : {"propositions": [logo, logo, logo]} avec trois logos différents.
Chaque logo : {"nom": str, "largeur": int, "hauteur": int, "fond": null ou "#rrggbb", "elements": [...]}.
Eléments possibles, dessinés dans l'ordre (le premier au fond), coordonnées en pixels, (x, y) = centre :
- {"type": "forme", "forme": "cercle|anneau|rectangle|arrondi|bandeau|etoile|losange|ailes|croix|chevron", "x", "y", "l", "h",
   "couleur": "#rrggbb" ou "#rrggbbaa", "contour": "#rrggbb" ou "", "epaisseur": int, "rotation": degrés, "opacite": 0..1}
- {"type": "texte", "texte": str (\\n pour aller à la ligne), "police": une police courante (Nunito, Montserrat, Georgia, Impact,
   Arial Black, Segoe Script…), "taille": px, "gras": bool, "couleur": "#rrggbb", "x", "y", "rotation",
   "effet": "aucun|contour|ombre|lueur|degrade", "couleur2": "#rrggbb", "epaisseur": int, "espacement": pourcentage (0 à 40)}
Règles : 2 à 6 éléments ; le texte reste entièrement dans le cadre ; contraste fort ; pas de marque déposée existante ;
fond null (transparent) sauf demande contraire ; tailles cohérentes avec largeur et hauteur (1024 × 1024 ou 1600 × 600)."""


def nettoyer(d):
    """Garde un logo valide (champs connus, valeurs bornées) à partir de ce que renvoie l'IA."""
    if not isinstance(d, dict):
        return None
    L = int(min(4096, max(128, float(d.get("largeur") or 1024))))
    H = int(min(4096, max(128, float(d.get("hauteur") or 1024))))
    out = nouveau(str(d.get("nom") or _("Logo proposé"))[:60], L, H)
    if isinstance(d.get("fond"), str) and re.match(r"^#[0-9a-fA-F]{6}$", d["fond"]):
        out["fond"] = d["fond"]
    formes = {k for k, _l in FORMES}
    effets = {k for k, _l in EFFETS}
    for el in (d.get("elements") or [])[:12]:
        if not isinstance(el, dict):
            continue
        try:
            if el.get("type") == "forme":
                e = forme(el.get("forme") if el.get("forme") in formes else "cercle", float(el.get("x", L / 2)), float(el.get("y", H / 2)),
                          float(el.get("l", 300)), float(el.get("h", 300)), str(el.get("couleur") or "#6d3fc6"),
                          contour=str(el.get("contour") or ""), epaisseur=float(el.get("epaisseur") or 0),
                          rotation=float(el.get("rotation") or 0), opacite=float(el.get("opacite", 1.0)))
            elif el.get("type") == "texte" and str(el.get("texte") or "").strip():
                e = texte(str(el["texte"])[:80], float(el.get("x", L / 2)), float(el.get("y", H / 2)), float(el.get("taille", 120)),
                          str(el.get("couleur") or "#ffffff"), police=str(el.get("police") or "Nunito"), gras=bool(el.get("gras", True)),
                          rotation=float(el.get("rotation") or 0), effet=el.get("effet") if el.get("effet") in effets else "aucun",
                          couleur2=str(el.get("couleur2") or "#000000"), epaisseur=float(el.get("epaisseur") or 8),
                          espacement=float(el.get("espacement") or 0))
            else:
                continue
        except (TypeError, ValueError):
            continue
        out["elements"].append(e)
    return out if out["elements"] else None


def proposer_ia(params, nom, style="", details="", base=None):
    """Trois logos éditables proposés par Claude ou Gemini (selon les Préférences)."""
    from . import ia
    demande = _("Nom à mettre dans le logo : « {n} ».\nStyle souhaité : {s}.\nPrécisions : {d}",
                n=nom, s=style or _("au choix, moderne et lisible"), d=details or _("aucune"))
    if base:
        demande += "\n" + _("Logo actuel à améliorer (garde l'idée, propose trois variantes) :") + "\n" + json.dumps(base, ensure_ascii=False)[:6000]
    r = ia.demander(params, CONSIGNES_IA, demande, json_attendu=True, max_jetons=6000)
    d = ia.lire_json(r) or {}
    props = d.get("propositions") if isinstance(d, dict) else d if isinstance(d, list) else None
    out = [x for x in (nettoyer(p) for p in (props or [])) if x]
    if not out:
        raise ia.ErreurIA(_("L'IA n'a pas renvoyé de logo utilisable."))
    return out


def image_ia(params, consigne, sortie):
    """Image de logo dessinée par Gemini (modèle d'image), enregistrée en PNG ; renvoie le chemin."""
    from . import ia
    from PySide6.QtGui import QImage
    png = ia.generer_image(params, _("Logo pour une vidéo : {c}. Fond uni très clair ou transparent, formes nettes, "
                                     "texte parfaitement lisible et correctement orthographié, centré, sans autre texte.", c=consigne))
    q = QImage()
    q.loadFromData(png)
    if q.isNull():
        raise ia.ErreurIA(_("Image illisible."))
    q.save(sortie)
    return sortie


def copie(logo):
    return copy.deepcopy(logo)
