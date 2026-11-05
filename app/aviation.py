"""Lot Aviation (0.4.0) : tout est réglé par l'utilisateur, rien n'est lu dans la caméra.

- Profil de vol : quelques chiffres (altitude du terrain, de croisière, vitesse, durées des phases, caps) donnent les
  courbes de tous les instruments du tableau de bord (altimètre, anémomètre, cap, variomètre, horizon, compte-tours),
  cohérentes entre elles et sans à-coups. Chaque courbe reste modifiable point par point.
- Trajet : des étapes (aérodromes de la liste, ou coordonnées saisies). La carte animée dessine le trait au fil de la
  vidéo et l'avion avance dessus, orienté selon sa route ; la mini-carte fait de même dans un coin.
- Manche à air : direction et force du vent saisies, rafales ; elle se gonfle et oscille.
- Radio : les échanges radio trouvés par l'écoute locale (whisper.cpp) sont reconnus à leur phraséologie et proposés
  en sous-titres « radio ».
"""
import math, re

from .langue import _

# Aérodromes (code OACI, nom, latitude, longitude) : positions arrondies, suffisantes pour une carte de vidéo ; modifiables.
AERODROMES = [
    ("LFMD", "Cannes-Mandelieu", 43.548, 6.954), ("LFMN", "Nice-Côte d'Azur", 43.658, 7.216), ("LFMF", "Fayence", 43.611, 6.703),
    ("LFTZ", "La Môle - Saint-Tropez", 43.205, 6.482), ("LFMC", "Le Luc - Le Cannet", 43.385, 6.387), ("LFTH", "Toulon-Hyères", 43.097, 6.146),
    ("LFMQ", "Le Castellet", 43.253, 5.786), ("LFML", "Marseille-Provence", 43.439, 5.221), ("LFMA", "Aix-les-Milles", 43.505, 5.368),
    ("LFMV", "Avignon-Provence", 43.907, 4.902), ("LFTW", "Nîmes-Garons", 43.757, 4.416), ("LFMT", "Montpellier", 43.576, 3.963),
    ("LFMX", "Château-Arnoux - Saint-Auban", 44.060, 5.996), ("LFNA", "Gap-Tallard", 44.455, 6.038), ("LFMR", "Barcelonnette", 44.387, 6.609),
    ("LFKJ", "Ajaccio", 41.924, 8.803), ("LFKB", "Bastia", 42.553, 9.484), ("LFKC", "Calvi", 42.531, 8.793), ("LFKF", "Figari", 41.501, 9.098),
    ("LIMG", "Albenga", 44.050, 8.127), ("LFLL", "Lyon Saint-Exupéry", 45.726, 5.081), ("LFLS", "Grenoble-Isère", 45.363, 5.329),
    ("LFLB", "Chambéry", 45.638, 5.880), ("LFBO", "Toulouse-Blagnac", 43.629, 1.364), ("LFMK", "Carcassonne", 43.216, 2.306),
    ("LFBD", "Bordeaux-Mérignac", 44.828, -0.716), ("LFBZ", "Biarritz", 43.468, -1.523), ("LFRS", "Nantes", 47.153, -1.611),
    ("LFPG", "Paris-Charles de Gaulle", 49.010, 2.548), ("LFPO", "Paris-Orly", 48.723, 2.379), ("LFPN", "Toussus-le-Noble", 48.752, 2.106),
    ("LSGG", "Genève", 46.238, 6.109), ("LFSB", "Bâle-Mulhouse", 47.590, 7.529), ("LFST", "Strasbourg", 48.538, 7.628),
]


def aerodrome(code):
    for a in AERODROMES:
        if a[0] == code.upper():
            return {"nom": f"{a[0]} {a[1]}", "code": a[0], "lat": a[2], "lon": a[3]}
    return None


# ------------------------------------------------------------------ trajet
def distance_nm(a, b):
    R = 3440.065
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def cap(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dl = math.radians(b["lon"] - a["lon"])
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def longueurs(etapes):
    return [distance_nm(a, b) for a, b in zip(etapes, etapes[1:])]


def position(etapes, frac):
    """(lat, lon, cap, indice du tronçon) à la fraction frac (0..1) du trajet, au prorata des distances."""
    if not etapes:
        return 0.0, 0.0, 0.0, 0
    if len(etapes) == 1:
        return etapes[0]["lat"], etapes[0]["lon"], 0.0, 0
    ls = longueurs(etapes)
    total = sum(ls) or 1.0
    reste = max(0.0, min(1.0, frac)) * total
    for i, l in enumerate(ls):
        if reste <= l or i == len(ls) - 1:
            u = 0.0 if l <= 0 else min(1.0, reste / l)
            a, b = etapes[i], etapes[i + 1]
            return a["lat"] + (b["lat"] - a["lat"]) * u, a["lon"] + (b["lon"] - a["lon"]) * u, cap(a, b), i
        reste -= l
    return etapes[-1]["lat"], etapes[-1]["lon"], cap(etapes[-2], etapes[-1]), len(ls) - 1


def avancement(g, t):
    """Fraction du trajet parcourue à l'instant t : de 0 au début du Goodie à 1 à sa fin (marges de départ / arrivée)."""
    opts = g.get("options") or {}
    from .goodies import bornes
    d, f = bornes(g)
    attente = float(opts.get("attente", 0.0) or 0.0)            # secondes immobile au départ (roulage)
    d2, f2 = d + attente, f - float(opts.get("arrivee", 0.0) or 0.0)
    if f2 <= d2:
        return 1.0
    u = max(0.0, min(1.0, (t - d2) / (f2 - d2)))
    return u * u * (3 - 2 * u) if opts.get("lisse", True) else u


# ------------------------------------------------------------------ profil de vol -> courbes des instruments
PROFIL_DEFAUT = {"terrain_ft": 50, "croisiere_ft": 3500, "arrivee_ft": 50, "vitesse_kt": 110, "roulage_s": 20, "montee_s": 300,
                 "descente_s": 360, "atterrissage_s": 20, "regime_croisiere": 2350, "cap_depart": 0, "cap_arrivee": 0}


def profil(duree, p=None, etapes=None):
    """Courbes [(t relatif, valeur)] pour chaque instrument sur `duree` secondes. Si un trajet est donné, le cap suit les
    tronçons ; sinon il va du cap de départ au cap d'arrivée."""
    q = dict(PROFIL_DEFAUT)
    q.update(p or {})
    D = max(10.0, float(duree))
    r, m, de, at = (max(0.0, float(q[k])) for k in ("roulage_s", "montee_s", "descente_s", "atterrissage_s"))
    s = (r + m + de + at) / max(1.0, D)
    if s > 0.95:                                                 # vidéo plus courte que les phases : on les resserre
        r, m, de, at = (x / s * 0.95 for x in (r, m, de, at))
    t1, t2 = r, r + m
    t4 = D - at
    t3 = t4 - de
    zt, zc, za = float(q["terrain_ft"]), float(q["croisiere_ft"]), float(q["arrivee_ft"])
    v = float(q["vitesse_kt"])
    vit = [(0, 0), (max(0.0, t1 - 8), 12), (t1, 60), (t1 + min(20, m / 3), 0.75 * v), (t2, 0.9 * v), (t2 + 15, v), (t3, v),
           (t3 + 10, 0.85 * v), (t4, 65), (t4 + min(8, at), 15), (D, 0)]
    rm, rd = min(5.0, m / 4), min(5.0, de / 4)                   # rampes du variomètre
    vm = (zc - zt) / max(0.5, m - rm) * 60                       # ft/min : la montée arrive pile à l'altitude de croisière
    vd = (za - zc) / max(0.5, de - rd) * 60
    vario = [(0, 0), (t1, 0), (t1 + rm, vm), (t2 - rm, vm), (t2, 0), (t3, 0), (t3 + rd, vd), (t4 - rd, vd), (t4, 0), (D, 0)]
    # l'altitude est l'intégrale du variomètre (aiguilles cohérentes entre elles)
    gv = {"genre": "variometre", "valeurs": vario, "debut": 0, "fin": D, "options": {"lisse": False}}
    from .goodies import valeur as _val
    pas = max(0.5, D / 300)
    alt, z, t = [(0.0, zt)], zt, 0.0
    while t < D - 1e-6:
        dt = min(pas, D - t)
        z += (_val(gv, t) + _val(gv, t + dt)) / 2 * dt / 60
        t += dt
        alt.append((round(t, 2), z))
    tangage = [(t, max(-12, min(15, vv / 120.0))) for t, vv in vario]
    regime = float(q["regime_croisiere"])
    rpm = [(0, 900), (t1 - 2 if t1 > 2 else 0, 1100), (t1, 2600), (t2, 2600), (t2 + 10, regime), (t3, regime), (t3 + 10, 1700),
           (t4, 1200), (D, 900)]
    if etapes and len(etapes) > 1:
        ls = longueurs(etapes)
        tot = sum(ls) or 1
        caps, acc = [], 0.0
        for i, l in enumerate(ls):
            c = cap(etapes[i], etapes[i + 1])
            caps.append((t1 + (t4 - t1) * acc / tot + (2 if i else 0), c))
            acc += l
            caps.append((t1 + (t4 - t1) * acc / tot - 2, c))
        caps = [(0, caps[0][1])] + caps + [(D, caps[-1][1])]
    else:
        caps = [(0, float(q["cap_depart"])), (t1, float(q["cap_depart"])), (t3, float(q["cap_arrivee"])), (D, float(q["cap_arrivee"]))]
    caps = _caps_continus(caps)
    roulis = [(0, 0)]
    for (ta, ca), (tb, cb) in zip(caps, caps[1:]):
        if abs(cb - ca) > 2 and tb > ta:
            sens = 1 if cb > ca else -1
            roulis += [(ta, 0), (ta + min(3, (tb - ta) / 3), 20 * sens), (tb - min(3, (tb - ta) / 3), 20 * sens), (tb, 0)]
    roulis.append((D, 0))
    return {"altimetre": alt, "anemometre": vit, "variometre": vario, "horizon": tangage, "compas": caps,
            "compte_tours": rpm, "roulis": sorted(roulis)}


def _caps_continus(pts):
    """Caps sans saut 359° -> 0° (l'aiguille tourne par le plus court)."""
    out = []
    for t, c in pts:
        if out:
            p = out[-1][1]
            while c - p > 180:
                c -= 360
            while c - p < -180:
                c += 360
        out.append((t, c))
    return out


INSTRUMENTS = [("altimetre", _("Altimètre")), ("anemometre", _("Anémomètre")), ("compas", _("Cap")), ("variometre", _("Variomètre")),
               ("horizon", _("Horizon artificiel")), ("compte_tours", _("Compte-tours"))]


def poser_tableau(projet, debut, fin, instruments, reglages=None, etapes=None, taille=0.17, groupe=None, y=0.86):
    """Pose (ou remplace) le tableau de bord : un Goodie par instrument, côte à côte en bas, valeurs du profil de vol.
    Renvoie la liste des Goodies posés. Ils partagent un même « groupe » (régler le profil les met tous à jour)."""
    from .projet import _id
    groupe = groupe or _id()
    anciens = {g["genre"]: g for g in projet.goodies if (g.get("options") or {}).get("groupe") == groupe}
    courbes = profil(fin - debut, reglages, etapes)
    out = []
    n = len(instruments)
    for i, genre in enumerate(instruments):
        g = anciens.pop(genre, None)
        if g is None:
            g = projet.ajouter_goodie(genre, debut, fin, taille=taille, x=round(0.5 + (i - (n - 1) / 2) * taille * 0.62, 4), y=y)
        g["debut"], g["fin"] = float(debut), float(fin)
        g["valeurs"] = [(round(debut + t, 2), round(v, 1)) for t, v in courbes[genre]]
        g.setdefault("options", {}).update(groupe=groupe, profil=dict(reglages or {}), lisse=genre != "altimetre")   # altitude : points serrés, en ligne droite
        if genre == "horizon":
            g["options"]["roulis_valeurs"] = [(round(debut + t, 2), round(v, 1)) for t, v in courbes["roulis"]]
        out.append(g)
    for g in anciens.values():                     # instrument décoché
        projet.retirer_element(g["id"])
    return out


# ------------------------------------------------------------------ dessin (carte, mini-carte, manche à air)
def dessiner(p, g, t, taille, cache):
    if g["genre"] == "manche_air":
        _manche(p, g, t, taille)
    else:
        _carte(p, g, t, taille, cache, mini=g["genre"] == "mini_carte")


def _projection(etapes, taille, marge):
    """Fonction (lat, lon) -> (x, y) qui cadre toutes les étapes dans le carré, nord en haut."""
    lats = [e["lat"] for e in etapes] or [0]
    lons = [e["lon"] for e in etapes] or [0]
    lat0 = (max(lats) + min(lats)) / 2
    k = math.cos(math.radians(lat0))
    w = max(1e-3, (max(lons) - min(lons)) * k)
    h = max(1e-3, max(lats) - min(lats))
    ech = (taille - 2 * marge) / max(w, h, 0.05)
    cx, cy = (max(lons) + min(lons)) / 2, lat0

    def pr(lat, lon):
        return taille / 2 + (lon - cx) * k * ech, taille / 2 - (lat - cy) * ech
    return pr


def _carte(p, g, t, taille, cache, mini=False):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF
    opts = g.get("options") or {}
    etapes = [e for e in opts.get("etapes") or [] if e.get("lat") is not None]
    sombre = opts.get("fond", "sombre") != "clair"
    fond = QColor(16, 24, 36, 225) if sombre else QColor(236, 228, 205, 235)
    trait = QColor(255, 210, 74) if sombre else QColor(190, 40, 40)
    texte = QColor(235, 235, 240) if sombre else QColor(40, 40, 40)
    chemin = QPainterPath()
    if mini:
        chemin.addEllipse(QRectF(taille * 0.03, taille * 0.03, taille * 0.94, taille * 0.94))
    else:
        chemin.addRoundedRect(QRectF(taille * 0.02, taille * 0.02, taille * 0.96, taille * 0.96), taille * 0.05, taille * 0.05)
    p.setPen(Qt.NoPen)
    p.setBrush(fond)
    p.drawPath(chemin)
    p.save()
    p.setClipPath(chemin)
    # quadrillage léger (méridiens / parallèles)
    p.setPen(QPen(QColor(255, 255, 255, 25) if sombre else QColor(0, 0, 0, 25), max(1.0, taille * 0.003)))
    for k in range(1, 8):
        p.drawLine(QPointF(taille * k / 8, 0), QPointF(taille * k / 8, taille))
        p.drawLine(QPointF(0, taille * k / 8), QPointF(taille, taille * k / 8))
    if len(etapes) >= 2:
        frac = avancement(g, t)
        lat, lon, cp, idx = position(etapes, frac)
        if mini:                                    # mini-carte : centrée sur l'avion, zoomée
            rayon = max(0.15, sum(longueurs(etapes)) / 60.0 * 0.35)
            vue = [{"lat": lat - rayon, "lon": lon - rayon}, {"lat": lat + rayon, "lon": lon + rayon}]
            pr = _projection(vue, taille, taille * 0.05)
        else:
            pr = _projection(etapes, taille, taille * 0.14)
        pts = [QPointF(*pr(e["lat"], e["lon"])) for e in etapes]
        # trajet prévu en pointillé, trajet parcouru en plein
        p.setPen(QPen(QColor(trait.red(), trait.green(), trait.blue(), 110), taille * 0.008, Qt.DashLine))
        p.drawPolyline(QPolygonF(pts))
        fait = pts[:idx + 1] + [QPointF(*pr(lat, lon))]
        p.setPen(QPen(trait, taille * (0.016 if not mini else 0.02), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline(QPolygonF(fait))
        # étapes
        f = QFont("Nunito")
        f.setBold(True)
        f.setPointSizeF(max(5.0, taille * (0.032 if not mini else 0.045)))
        p.setFont(f)
        for e, q in zip(etapes, pts):
            p.setPen(QPen(texte, taille * 0.004))
            p.setBrush(fond)
            p.drawEllipse(q, taille * 0.014, taille * 0.014)
            if not mini or True:
                nom = (e.get("code") or e.get("nom") or "")[:18] if mini else (e.get("nom") or "")[:26]
                p.setPen(texte)
                p.drawText(QRectF(q.x() - taille * 0.3, q.y() + taille * 0.018, taille * 0.6, taille * 0.06), Qt.AlignHCenter | Qt.AlignTop, nom)
        # l'avion, orienté selon sa route
        av = QPointF(*pr(lat, lon))
        p.save()
        p.translate(av)
        p.rotate(cp)
        s = taille * (0.045 if not mini else 0.07)
        p.setPen(QPen(QColor(20, 20, 26), max(1.0, s * 0.08)))
        p.setBrush(QColor(255, 255, 255))
        avion = QPolygonF([QPointF(0, -s), QPointF(s * 0.18, -s * 0.3), QPointF(s, s * 0.05), QPointF(s, s * 0.22), QPointF(s * 0.16, s * 0.05),
                           QPointF(s * 0.12, s * 0.7), QPointF(s * 0.4, s * 0.9), QPointF(s * 0.4, s), QPointF(0, s * 0.88),
                           QPointF(-s * 0.4, s), QPointF(-s * 0.4, s * 0.9), QPointF(-s * 0.12, s * 0.7), QPointF(-s * 0.16, s * 0.05),
                           QPointF(-s, s * 0.22), QPointF(-s, s * 0.05), QPointF(-s * 0.18, -s * 0.3)])
        p.drawPolygon(avion)
        p.restore()
        if not mini and opts.get("infos", True):
            ls = longueurs(etapes)
            fait_nm = sum(ls) * frac
            f.setPointSizeF(max(5.0, taille * 0.03))
            p.setFont(f)
            p.setPen(texte)
            p.drawText(QRectF(taille * 0.06, taille * 0.87, taille * 0.88, taille * 0.08), Qt.AlignLeft | Qt.AlignVCenter,
                       f"{fait_nm:.0f} / {sum(ls):.0f} NM · {cp:03.0f}°")
    else:
        f = QFont("Nunito")
        f.setPointSizeF(max(5.0, taille * 0.04))
        p.setFont(f)
        p.setPen(texte)
        p.drawText(QRectF(0, 0, taille, taille), Qt.AlignCenter | Qt.TextWordWrap, _("Ajoutez au moins deux étapes"))
    p.restore()
    p.setPen(QPen(QColor(255, 255, 255, 150) if sombre else QColor(90, 70, 40), taille * 0.008))
    p.setBrush(Qt.NoBrush)
    p.drawPath(chemin)
    if mini:                                        # repère du nord
        f = QFont("Nunito")
        f.setBold(True)
        f.setPointSizeF(max(5.0, taille * 0.06))
        p.setFont(f)
        p.setPen(QColor(255, 90, 90))
        p.drawText(QRectF(0, taille * 0.04, taille, taille * 0.1), Qt.AlignHCenter | Qt.AlignTop, "N")


def vent(g, t):
    """(force en kt, direction d'où vient le vent en degrés) à l'instant t, rafales comprises."""
    opts = g.get("options") or {}
    force = float(opts.get("vent_kt", 10) or 0)
    rafales = float(opts.get("rafales_kt", 0) or 0)
    if rafales > force:
        u = 0.5 + 0.5 * math.sin(t * 1.3) * math.sin(t * 0.37 + 1.1)
        force += (rafales - force) * max(0.0, u)
    return force, float(opts.get("vent_dir", 270) or 0) % 360


def _manche(p, g, t, taille):
    """Manche à air vue de côté (rayée rouge et blanc), gonflée selon la force, avec la direction et la force du vent."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QPen, QPolygonF
    opts = g.get("options") or {}
    force, direction = vent(g, t)
    vers_droite = opts.get("sens", "droite") != "gauche"
    gonfle = max(0.0, min(1.0, force / 15.0))              # pleinement gonflée à 15 kt (convention)
    mat_x, haut = taille * (0.28 if vers_droite else 0.72), taille * 0.2
    p.setPen(QPen(QColor(200, 200, 205), taille * 0.025, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(mat_x, taille * 0.9), QPointF(mat_x, haut))
    longueur = taille * 0.55
    angle = math.radians(80 - 78 * gonfle + 3 * math.sin(t * 6.0 + math.sin(t * 2.1)) * (0.3 + gonfle))   # 80° : pend ; 2° : à l'horizontale
    sens = 1 if vers_droite else -1
    n = 5
    for k in range(n):
        u0, u1 = k / n, (k + 1) / n
        r0, r1 = taille * 0.07 * (1 - 0.45 * u0), taille * 0.07 * (1 - 0.45 * u1)
        ondule = math.sin(t * 9 + k) * taille * 0.006 * (1 - gonfle * 0.5)
        x0, y0 = mat_x + sens * math.cos(angle) * longueur * u0, haut + math.sin(angle) * longueur * u0
        x1, y1 = mat_x + sens * math.cos(angle) * longueur * u1, haut + math.sin(angle) * longueur * u1
        nx, ny = -math.sin(angle) * sens, math.cos(angle)
        poly = QPolygonF([QPointF(x0 + nx * r0, y0 - ny * r0 * sens * sens + ondule), QPointF(x1 + nx * r1, y1 - ny * r1 + ondule),
                          QPointF(x1 - nx * r1, y1 + ny * r1 + ondule), QPointF(x0 - nx * r0, y0 + ny * r0 + ondule)])
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(230, 60, 40) if k % 2 == 0 else QColor(245, 245, 245))
        p.drawPolygon(poly)
    if opts.get("infos", True):
        f = QFont("Nunito")
        f.setBold(True)
        f.setPointSizeF(max(5.0, taille * 0.065))
        p.setFont(f)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(0, taille * 0.88, taille, taille * 0.12), Qt.AlignCenter, f"{direction:03.0f}° / {force:.0f} kt")


# ------------------------------------------------------------------ radio
MOTS_RADIO = ["piste", "qnh", "qfu", "tour", "sol", "info", "autoris", "rappel", "vent", "fréquence", "frequence", "transpondeur", "squawk",
              "établi", "etabli", "vent arrière", "finale", "niveau", "pieds", "roger", "reçu", "recu", "affirm", "négatif", "negatif",
              "contact", "décollage", "decollage", "atterrissage", "alignez", "maintenez", "verticale", "entrée", "sortie", "point",
              "approche", "runway", "cleared", "tower", "ground", "wind", "feet", "squawk", "report", "downwind", "final", "base",
              "fox", "foxtrot", "golf", "hotel", "india", "juliett", "kilo", "lima", "mike", "november", "oscar", "papa", "québec",
              "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whisky", "whiskey", "x-ray", "yankee", "zulu", "alpha",
              "bravo", "charlie", "delta", "echo", "unité", "décimal", "decimal"]


def score_radio(texte):
    """Indice qu'une phrase est un échange radio (phraséologie, alphabet, immatriculation, fréquences)."""
    t = (texte or "").lower()
    n = sum(1 for m in MOTS_RADIO if re.search(r"\b" + re.escape(m), t))
    if re.search(r"\bf-?[a-z]{4}\b", t):                     # immatriculation F-GABC
        n += 2
    if re.search(r"\b1[1-3]\d[.,]\d{1,3}\b", t):             # fréquence 118.700
        n += 2
    return n


def detecter_radio(projet, params=None, progression=None, seuil=2):
    """Phrases du son des plans, écoutées dans la bande de la radio (300-3400 Hz) : [(debut, fin, texte, score)]."""
    from . import sous_titres as ST
    segs = ST.transcrire_projet(projet, params, progression=progression, langue="auto", decouper=False,
                                filtre="highpass=f=300,lowpass=f=3400,dynaudnorm")
    return [(a, b, t, score_radio(t)) for a, b, t, *_r in segs]
