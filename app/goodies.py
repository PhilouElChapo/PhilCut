"""Module Goodies : instruments, cadrans, badges et petits objets animes dedies a l'esprit de la video.

Un Goodie du projet : {"genre": "altimetre", "debut", "fin", "x", "y" (centre, 0..1), "taille" (fraction de la
hauteur), "style": "cadran" | "hud", "valeurs": [(t, valeur), ...] (interpolees), "options": {...}}.
Les valeurs viennent de la telemetrie (GoPro, trace GPX) quand elle existe, sinon de quelques points saisis a la
main, sinon le cadran est un simple decor anime. Rendu en images PNG transparentes (QPainter) superposees a l'export.
"""
import math, os

from .langue import _

PACKS = {
    "aviation": {"nom": _("Aviation"), "description": _("Altimètre, anémomètre, cap, horizon, variomètre, compte-tours, chrono, immatriculation, mini-carte."),
                 "goodies": ["altimetre", "anemometre", "compas", "horizon", "variometre", "compte_tours", "chrono", "immatriculation", "carte_trajet", "mini_carte", "manche_air"]},
    "balade": {"nom": _("Balade et randonnée"), "description": _("Altitude, distance, boussole, météo, dénivelé."),
               "goodies": ["altitude", "distance", "boussole", "meteo", "denivele"]},
    "route": {"nom": _("Route"), "description": _("Compteur de vitesse, carte, kilométrage."), "goodies": ["compteur", "mini_carte", "distance"]},
    "pharmacie": {"nom": _("Pharmacie"), "description": _("Croix verte, horaires, pastille d'annonce, prix."), "goodies": ["croix", "horaires", "pastille", "prix"]},
    "fete": {"nom": _("Fête"), "description": _("Compte à rebours, confettis, date, bandeau."), "goodies": ["compte_a_rebours", "confettis", "date", "bandeau"]},
    "autocollants": {"nom": _("Autocollants"), "description": _("Polaroïd avec votre photo, post-it, flèche qui se trace : à poser ou à accrocher à une personne."),
                     "goodies": ["polaroid", "post_it", "fleche"]},
    "perso": {"nom": _("Mes images"), "description": _("Logo, autocollant, photo en PNG transparent : à poser, ou à accrocher à une personne qui bouge."),
              "goodies": ["image"]},
    "maison": {"nom": _("Maison et jardin"), "description": _("Horloge, lune, température, altitude du lieu."), "goodies": ["horloge", "lune", "temperature", "altitude"]},
}

GENRES = {
    "altimetre": (_("Altimètre"), "ft", (0, 10000)), "anemometre": (_("Anémomètre"), "kt", (0, 200)),
    "compas": (_("Compas / cap"), "°", (0, 360)), "horizon": (_("Horizon artificiel"), "°", (-30, 30)),
    "variometre": (_("Variomètre"), "ft/min", (-2000, 2000)), "compte_tours": (_("Compte-tours"), "tr/min", (0, 3000)),
    "chrono": (_("Chrono de vol"), "s", (0, 36000)), "immatriculation": (_("Immatriculation"), "", (0, 0)),
    "mini_carte": (_("Mini-carte"), "", (0, 0)), "manche_air": (_("Manche à air"), "kt", (0, 40)),
    "carte_trajet": (_("Carte animée du trajet"), "", (0, 0)),
    "polaroid": (_("Polaroïd"), "", (0, 0)), "post_it": (_("Post-it"), "", (0, 0)), "fleche": (_("Flèche"), "", (0, 0)),
    "altitude": (_("Altitude"), "m", (0, 4000)), "distance": (_("Distance"), "km", (0, 1000)), "boussole": (_("Boussole"), "°", (0, 360)),
    "meteo": (_("Météo"), "°C", (-20, 45)), "denivele": (_("Dénivelé"), "m", (0, 3000)), "compteur": (_("Compteur"), "km/h", (0, 240)),
    "croix": (_("Croix de pharmacie"), "", (0, 0)), "horaires": (_("Horaires"), "", (0, 0)), "pastille": (_("Pastille d'annonce"), "", (0, 0)),
    "prix": (_("Prix"), "€", (0, 0)), "compte_a_rebours": (_("Compte à rebours"), "s", (0, 0)), "confettis": (_("Confettis"), "", (0, 0)),
    "date": (_("Date"), "", (0, 0)), "bandeau": (_("Bandeau"), "", (0, 0)), "horloge": (_("Horloge"), "", (0, 0)), "lune": (_("Lune"), "", (0, 0)),
    "temperature": (_("Température"), "°C", (-20, 45)), "image": (_("Image ou logo"), "", (0, 0)),
}


def bornes(g):
    """Début et fin « réels » du Goodie : un extrait (aperçu, préparation) le raccourcit mais garde son déroulé d'origine."""
    o = (g.get("options") or {}).get("_origine")
    return (float(o[0]), float(o[1])) if o else (float(g["debut"]), float(g["fin"]))


def valeur(g, t):
    """Valeur interpolee a l'instant t (lineaire entre les points saisis ; constante avant/apres)."""
    pts = sorted(g.get("valeurs") or [])
    if not pts:
        mini, maxi = GENRES.get(g["genre"], ("", "", (0, 100)))[2]
        d, f = bornes(g)
        f = max(f, d + 0.01)
        return mini + (maxi - mini) * (0.3 + 0.2 * math.sin((t - d) / (f - d) * 6.28))      # decor anime
    if t <= pts[0][0]:
        return pts[0][1]
    doux = (g.get("options") or {}).get("lisse", True)        # montée et descente progressives (pas d'à-coups)
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / max(1e-6, t1 - t0)
            if doux:
                u = u * u * (3 - 2 * u)
            return v0 + (v1 - v0) * u
    return pts[-1][1]


def depuis_gpx(chemin, origine=None):
    """Points (t, altitude m, vitesse km/h, cap) d'une trace GPX ; t relatif au premier point (ou a `origine`)."""
    import datetime, xml.etree.ElementTree as ET
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    try:
        racine = ET.parse(chemin).getroot()
    except (OSError, ET.ParseError):
        return []
    pts = []
    for p in racine.iter("{http://www.topografix.com/GPX/1/1}trkpt"):
        try:
            lat, lon = float(p.get("lat")), float(p.get("lon"))
            ele = p.find("g:ele", ns)
            tm = p.find("g:time", ns)
            if tm is None:
                continue
            t = datetime.datetime.fromisoformat(tm.text.replace("Z", "+00:00"))
            pts.append((t, lat, lon, float(ele.text) if ele is not None else 0.0))
        except (TypeError, ValueError):
            continue
    if not pts:
        return []
    t0 = origine or pts[0][0]
    out = []
    for i, (t, lat, lon, ele) in enumerate(pts):
        v, cap = 0.0, 0.0
        if i:
            tp, la, lo, _e = pts[i - 1]
            dt = (t - tp).total_seconds() or 1
            d = _haversine(la, lo, lat, lon)
            v = d / dt * 3.6
            cap = (math.degrees(math.atan2(math.sin(math.radians(lon - lo)) * math.cos(math.radians(lat)),
                                           math.cos(math.radians(la)) * math.sin(math.radians(lat))
                                           - math.sin(math.radians(la)) * math.cos(math.radians(lat)) * math.cos(math.radians(lon - lo)))) + 360) % 360
        out.append(((t - t0).total_seconds(), ele, v, cap, lat, lon))
    return out


def _haversine(la1, lo1, la2, lo2):
    R = 6371000.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ------------------------------------------------------------------ rendu
IPS_GOODIES = 15                # images par seconde des Goodies à l'export (aiguilles fluides, rendu trois fois plus court)


def cote(g, H):
    return max(48, int(H * float(g.get("taille", 0.22))))


def rendre(dossier, g, L, H, cadence, texte_extra=None):
    """Ecrit les images PNG du Goodie entre debut et fin ; renvoie (motif, nb_images, x, y en pixels du coin)."""
    taille = cote(g, H)
    n = int((g["fin"] - g["debut"]) * cadence)
    cache = {}
    for i in range(max(1, n)):
        t = g["debut"] + i / cadence
        image(g, t, taille, texte_extra, cache).save(os.path.join(dossier, f"{i:05d}.png"))
    x = int(float(g.get("x", 0.88)) * L - taille / 2)
    y = int(float(g.get("y", 0.85)) * H - taille / 2)
    return os.path.join(dossier, "%05d.png"), max(1, n), x, y


def image(g, t, taille, texte_extra=None, cache=None):
    """L'image (QImage carrée, transparente) du Goodie à l'instant t du montage : export et aperçu dessinent pareil."""
    from PySide6.QtCore import Qt, QRectF, QPointF
    from PySide6.QtGui import QImage, QPainter, QColor, QPen, QFont, QBrush, QPainterPath
    cache = {} if cache is None else cache
    genre, style = g["genre"], g.get("style", "cadran")
    nom, unite, (mini, maxi) = GENRES.get(genre, (genre, "", (0, 100)))
    opts = g.get("options") or {}
    police = QFont("Nunito")
    if genre == "image" and "source" not in cache:
        cache["source"] = QImage(opts.get("chemin") or "")
    img_source = cache.get("source")
    if True:
        v = valeur(g, t)
        img = QImage(taille, taille, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        c = taille / 2
        r = taille * 0.46
        if genre in ("carte_trajet", "mini_carte", "manche_air"):
            from . import aviation
            aviation.dessiner(p, g, t, taille, cache)
        elif genre in ("polaroid", "post_it", "fleche"):
            from . import autocollants
            autocollants.dessiner(p, g, t, taille, cache)
        elif genre == "image":
            if not img_source.isNull():
                s = img_source.size().scaled(taille, taille, Qt.KeepAspectRatio)
                p.drawImage(QRectF((taille - s.width()) / 2, (taille - s.height()) / 2, s.width(), s.height()), img_source)
        elif style == "cadran" and genre in ("altimetre", "anemometre", "compas", "variometre", "compte_tours", "boussole", "compteur", "horloge"):
            p.setBrush(QColor(15, 15, 20, 225))
            p.setPen(QPen(QColor(230, 230, 230), taille * 0.02))
            p.drawEllipse(QPointF(c, c), r, r)
            # graduations
            nb = 36 if genre in ("compas", "boussole") else 12 if genre == "horloge" else 10
            for k in range(nb):
                ang = -90 + 360 * k / nb if genre in ("compas", "boussole", "horloge") else -135 + 270 * k / (nb - 1)
                a = math.radians(ang)
                r1, r2 = r * (0.86 if k % 3 == 0 or genre == "horloge" else 0.92), r * 0.98
                p.setPen(QPen(QColor(235, 235, 235), taille * (0.012 if k % 3 == 0 else 0.007)))
                p.drawLine(QPointF(c + r1 * math.cos(a), c + r1 * math.sin(a)), QPointF(c + r2 * math.cos(a), c + r2 * math.sin(a)))
            police.setPointSizeF(max(6.0, taille * 0.07))
            police.setBold(True)
            p.setFont(police)
            p.setPen(QColor(240, 240, 240))
            if genre in ("compas", "boussole"):
                for lettre, ang in (("N", -90), ("E", 0), ("S", 90), ("W", 180)):
                    a = math.radians(ang - v)
                    p.drawText(QRectF(c + r * 0.7 * math.cos(a) - taille * 0.08, c + r * 0.7 * math.sin(a) - taille * 0.06, taille * 0.16, taille * 0.12), Qt.AlignCenter, lettre)
                self_ang = -90
                p.drawText(QRectF(0, c + r * 0.2, taille, taille * 0.18), Qt.AlignCenter, f"{v % 360:03.0f}°")
            elif genre == "horloge":
                import datetime
                h0 = opts.get("heure")
                base = datetime.datetime.fromisoformat(h0) if h0 else datetime.datetime(2000, 1, 1, 21, 0)
                now = base + datetime.timedelta(seconds=(t - bornes(g)[0]) * float(opts.get("accelere", 1)))
                self_ang = -90 + (now.hour % 12 + now.minute / 60) * 30
                am = math.radians(-90 + now.minute * 6)
                p.setPen(QPen(QColor(240, 240, 240), taille * 0.014, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(QPointF(c, c), QPointF(c + r * 0.85 * math.cos(am), c + r * 0.85 * math.sin(am)))
            else:
                frac = (v - mini) / max(1e-6, (maxi - mini))
                self_ang = -135 + 270 * min(1.0, max(0.0, frac))
                p.drawText(QRectF(0, c + r * 0.25, taille, taille * 0.2), Qt.AlignCenter, f"{v:,.0f} {unite}".replace(",", " "))
            police.setPointSizeF(max(5.0, taille * 0.05))
            p.setFont(police)
            p.setPen(QColor(180, 180, 190))
            if genre not in ("compas", "boussole"):           # sur le compas, les lettres tournent : pas de titre par-dessus
                p.drawText(QRectF(0, c - r * 0.55, taille, taille * 0.15), Qt.AlignCenter, nom.upper())
            # aiguille
            a = math.radians(self_ang)
            p.setPen(QPen(QColor(255, 120, 60), taille * 0.02, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(c, c), QPointF(c + r * 0.78 * math.cos(a), c + r * 0.78 * math.sin(a)))
            p.setBrush(QColor(255, 255, 255))
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(c, c), taille * 0.03, taille * 0.03)
        elif genre == "horizon":
            path = QPainterPath()
            path.addEllipse(QPointF(c, c), r, r)
            p.setClipPath(path)
            roulis = float(opts.get("roulis", 0.0))
            if opts.get("roulis_valeurs"):                    # inclinaison en virage (profil de vol)
                roulis = valeur({"genre": "horizon", "valeurs": opts["roulis_valeurs"], "debut": g["debut"], "fin": g["fin"]}, t)
            tangage = v
            p.translate(c, c)
            p.rotate(-roulis)
            dy = tangage / 30.0 * r * 0.6
            p.fillRect(QRectF(-r * 1.5, -r * 1.5 + dy, r * 3, r * 1.5), QColor(70, 140, 230, 230))
            p.fillRect(QRectF(-r * 1.5, dy, r * 3, r * 1.5), QColor(140, 90, 40, 230))
            p.setPen(QPen(QColor(255, 255, 255), taille * 0.015))
            p.drawLine(QPointF(-r, dy), QPointF(r, dy))
            p.resetTransform()
            p.setClipping(False)
            p.setPen(QPen(QColor(255, 180, 40), taille * 0.025, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(c - r * 0.45, c), QPointF(c - r * 0.12, c))
            p.drawLine(QPointF(c + r * 0.12, c), QPointF(c + r * 0.45, c))
            p.setPen(QPen(QColor(230, 230, 230), taille * 0.02))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(c, c), r, r)
        else:
            # style HUD / badges texte : fond arrondi sombre, valeur en grand
            p.setBrush(QColor(10, 10, 14, 200))
            p.setPen(QPen(QColor(255, 255, 255, 180), taille * 0.012))
            p.drawRoundedRect(QRectF(taille * 0.04, taille * 0.3, taille * 0.92, taille * 0.4), taille * 0.08, taille * 0.08)
            police.setPointSizeF(max(6.0, taille * 0.12))
            police.setBold(True)
            p.setFont(police)
            p.setPen(QColor(120, 255, 170) if style == "hud" else QColor(255, 255, 255))
            if genre in ("immatriculation", "date", "bandeau", "horaires", "prix", "pastille"):
                texte = str(opts.get("texte") or texte_extra or nom)
            elif genre in ("chrono", "compte_a_rebours"):
                s = int(v if genre == "chrono" else max(0, float(opts.get("depuis", 10)) - (t - bornes(g)[0])))
                texte = f"{s // 60:02d}:{s % 60:02d}"
            else:
                texte = f"{v:,.0f} {unite}".replace(",", " ")
            p.drawText(QRectF(0, taille * 0.3, taille, taille * 0.4), Qt.AlignCenter, texte)
            police.setPointSizeF(max(5.0, taille * 0.055))
            police.setBold(False)
            p.setFont(police)
            p.setPen(QColor(200, 200, 210))
            p.drawText(QRectF(0, taille * 0.16, taille, taille * 0.14), Qt.AlignCenter, nom.upper())
        p.end()
        return img
