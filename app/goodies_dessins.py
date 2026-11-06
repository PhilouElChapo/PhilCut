"""Goodies dessinés des packs Balade, Route, Fête, Maison et Commerce : petites illustrations animées (montagne qui
monte, sentier qui se parcourt, soleil, thermomètre, anneau de compte à rebours, page de calendrier, ruban, étiquette
de prix, pastille étoilée…) à la place des simples badges de texte. Le style « HUD » garde le badge sobre.

dessiner(p, g, t, taille, v, nom, unite, mini, maxi) dessine dans un QPainter déjà ouvert sur une image carrée
transparente ; tout est proportionnel à `taille`, donc net à toutes les tailles."""
import datetime, math

from .langue import _

GENRES = {"altitude", "distance", "meteo", "denivele", "temperature", "compte_a_rebours", "date", "bandeau", "horaires",
          "prix", "pastille", "compteur"}

CIELS = {"soleil": _("Soleil"), "eclaircies": _("Eclaircies"), "nuages": _("Nuageux"), "pluie": _("Pluie"), "neige": _("Neige")}


def _police(taille, frac, gras=True, famille="Poppins"):
    from PySide6.QtGui import QFont
    f = QFont(famille)
    f.setPointSizeF(max(5.0, taille * frac))
    f.setBold(gras)
    return f


def _texte_ajuste(p, rect, texte, police, largeur_max, align=None):
    """Ecrit le texte en réduisant la police jusqu'à ce qu'il tienne dans la largeur voulue."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontMetricsF
    while police.pointSizeF() > 5 and QFontMetricsF(police).horizontalAdvance(texte) > largeur_max:
        police.setPointSizeF(police.pointSizeF() * 0.92)
    p.setFont(police)
    p.drawText(rect, align if align is not None else Qt.AlignCenter, texte)


def _entree(g, t, duree=0.45):
    """0 → 1 pendant l'apparition (ressort doux), 1 ensuite : chaque Goodie arrive au lieu d'apparaître d'un coup."""
    from .goodies import bornes
    u = max(0.0, min(1.0, (t - bornes(g)[0]) / duree))
    return 1 - (1 - u) ** 3


def _progression(g, t, v, mini, maxi):
    if g.get("valeurs"):
        return max(0.0, min(1.0, (v - mini) / max(1e-6, maxi - mini)))
    from .goodies import bornes
    d, f = bornes(g)
    return max(0.0, min(1.0, (t - d) / max(0.01, f - d)))


def _valeur_txt(v, unite):
    return f"{v:,.0f} {unite}".replace(",", " ").strip()


def _carte(p, taille, y0, h, alpha=215):
    """Fond commun : carte sombre arrondie, fine bordure claire (lisible sur tout fond)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QPen
    p.setPen(QPen(QColor(255, 255, 255, 70), max(1.0, taille * 0.008)))
    p.setBrush(QColor(14, 14, 20, alpha))
    p.drawRoundedRect(QRectF(taille * 0.05, y0, taille * 0.9, h), taille * 0.07, taille * 0.07)


def dessiner(p, g, t, taille, v, nom, unite, mini, maxi):
    from PySide6.QtCore import Qt, QRectF, QPointF
    from PySide6.QtGui import QColor, QPen, QBrush, QPainterPath, QLinearGradient, QPolygonF
    genre = g["genre"]
    opts = g.get("options") or {}
    T = taille
    e = _entree(g, t)
    accent = QColor(opts.get("couleur") or {"altitude": "#4fc3f7", "distance": "#ffb74d", "denivele": "#81c784",
                                            "temperature": "#ff7043", "compte_a_rebours": "#ff4081", "bandeau": "#7c4dff",
                                            "horaires": "#26a69a", "prix": "#ffca28", "pastille": "#ff5252",
                                            "compteur": "#40c4ff"}.get(genre, "#6d3fc6"))
    p.save()
    p.translate(T / 2, T / 2)
    p.scale(0.6 + 0.4 * e, 0.6 + 0.4 * e)
    p.translate(-T / 2, -T / 2)
    p.setOpacity(e)

    if genre == "altitude":                                  # montagne, repère qui grimpe avec la valeur
        _carte(p, T, T * 0.12, T * 0.76)
        frac = _progression(g, t, v, mini, maxi)
        mont = QPolygonF([QPointF(T * 0.1, T * 0.7), QPointF(T * 0.34, T * 0.36), QPointF(T * 0.45, T * 0.48),
                          QPointF(T * 0.6, T * 0.24), QPointF(T * 0.9, T * 0.7)])
        grad = QLinearGradient(0, T * 0.24, 0, T * 0.7)
        grad.setColorAt(0, QColor(220, 235, 255))
        grad.setColorAt(0.25, accent)
        grad.setColorAt(1, QColor(30, 60, 90))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPolygon(mont)
        y = T * 0.7 - (T * 0.7 - T * 0.24) * frac
        p.setPen(QPen(QColor(255, 255, 255, 160), T * 0.008, Qt.DashLine))
        p.drawLine(QPointF(T * 0.1, y), QPointF(T * 0.9, y))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QPointF(T * 0.6 - (1 - frac) * T * 0.2, y), T * 0.025, T * 0.025)
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(0, T * 0.71, T, T * 0.15), _valeur_txt(v, unite), _police(T, 0.1), T * 0.8)
    elif genre == "distance":                                # sentier en S parcouru par un point lumineux
        _carte(p, T, T * 0.12, T * 0.76)
        frac = _progression(g, t, v, mini, maxi)
        chemin = QPainterPath(QPointF(T * 0.16, T * 0.62))
        chemin.cubicTo(QPointF(T * 0.4, T * 0.72), QPointF(T * 0.3, T * 0.25), QPointF(T * 0.55, T * 0.34))
        chemin.cubicTo(QPointF(T * 0.75, T * 0.42), QPointF(T * 0.7, T * 0.2), QPointF(T * 0.86, T * 0.22))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 90), T * 0.018, Qt.DotLine, Qt.RoundCap))
        p.drawPath(chemin)
        fait = QPainterPath(chemin.pointAtPercent(0))
        for k in range(1, 41):
            fait.lineTo(chemin.pointAtPercent(frac * k / 40))
        p.setPen(QPen(accent, T * 0.022, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(fait)
        pt = chemin.pointAtPercent(frac)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 90))
        p.drawEllipse(pt, T * 0.05, T * 0.05)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(pt, T * 0.025, T * 0.025)
        drapeau = chemin.pointAtPercent(1)
        p.setPen(QPen(QColor(255, 255, 255), T * 0.01))
        p.drawLine(drapeau, drapeau + QPointF(0, -T * 0.09))
        p.setPen(Qt.NoPen)
        p.setBrush(accent)
        p.drawPolygon(QPolygonF([drapeau + QPointF(0, -T * 0.09), drapeau + QPointF(T * 0.06, -T * 0.07), drapeau + QPointF(0, -T * 0.05)]))
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(0, T * 0.71, T, T * 0.15), _valeur_txt(v, unite), _police(T, 0.1), T * 0.8)
    elif genre == "denivele":                                # profil du parcours, rempli au fil de la vidéo
        _carte(p, T, T * 0.12, T * 0.76)
        frac = _progression(g, t, v, mini, maxi)
        pts = [0.62, 0.55, 0.58, 0.44, 0.36, 0.4, 0.28, 0.24, 0.33, 0.3, 0.42]
        x0, x1 = T * 0.12, T * 0.88
        profil = QPainterPath(QPointF(x0, T * 0.68))
        for k, yy in enumerate(pts):
            profil.lineTo(QPointF(x0 + (x1 - x0) * k / (len(pts) - 1), T * yy))
        profil.lineTo(QPointF(x1, T * 0.68))
        profil.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawPath(profil)
        p.save()
        p.setClipRect(QRectF(x0, 0, (x1 - x0) * frac, T))
        grad = QLinearGradient(0, T * 0.24, 0, T * 0.68)
        grad.setColorAt(0, accent)
        grad.setColorAt(1, QColor(accent.red(), accent.green(), accent.blue(), 60))
        p.setBrush(QBrush(grad))
        p.drawPath(profil)
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 200), T * 0.006))
        p.drawLine(QPointF(x0 + (x1 - x0) * frac, T * 0.2), QPointF(x0 + (x1 - x0) * frac, T * 0.68))
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(0, T * 0.71, T, T * 0.15), "↗ " + _valeur_txt(v, unite), _police(T, 0.1), T * 0.8)
    elif genre in ("meteo", "temperature") and genre == "meteo":   # icône de ciel animée + température
        _carte(p, T, T * 0.12, T * 0.76)
        ciel = opts.get("ciel") or "soleil"
        cx, cy = T * 0.4, T * 0.4
        if ciel in ("soleil", "eclaircies"):
            p.save()
            p.translate(cx, cy)
            p.rotate(t * 20)
            p.setPen(QPen(QColor(255, 200, 60), T * 0.018, Qt.SolidLine, Qt.RoundCap))
            for k in range(10):
                a = math.radians(k * 36)
                p.drawLine(QPointF(math.cos(a) * T * 0.13, math.sin(a) * T * 0.13), QPointF(math.cos(a) * T * 0.18, math.sin(a) * T * 0.18))
            p.restore()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 205, 70))
            p.drawEllipse(QPointF(cx, cy), T * 0.1, T * 0.1)
        if ciel != "soleil":
            dx = math.sin(t * 0.8) * T * 0.02
            nuage = QPainterPath()
            nuage.setFillRule(Qt.WindingFill)
            for (x, y, r) in ((0.5, 0.45, 0.09), (0.62, 0.4, 0.11), (0.74, 0.46, 0.08), (0.62, 0.5, 0.08)):
                nuage.addEllipse(QPointF(T * x + dx, T * y), T * r, T * r * 0.85)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(235, 240, 248) if ciel != "pluie" else QColor(170, 180, 195))
            p.drawPath(nuage.simplified())
            if ciel in ("pluie", "neige"):
                for k in range(6):
                    x = T * (0.5 + 0.05 * k) + dx
                    y = T * 0.56 + ((t * T * 0.25 + k * T * 0.05) % (T * 0.1))
                    if ciel == "pluie":
                        p.setPen(QPen(QColor(120, 190, 255), T * 0.01, Qt.SolidLine, Qt.RoundCap))
                        p.drawLine(QPointF(x, y), QPointF(x - T * 0.01, y + T * 0.03))
                    else:
                        p.setPen(Qt.NoPen)
                        p.setBrush(QColor(255, 255, 255))
                        p.drawEllipse(QPointF(x, y), T * 0.01, T * 0.01)
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(0, T * 0.66, T, T * 0.18), _valeur_txt(v, unite), _police(T, 0.12), T * 0.8)
    elif genre == "temperature":                             # thermomètre dont le liquide suit la valeur
        _carte(p, T, T * 0.1, T * 0.8)
        frac = max(0.0, min(1.0, (v - mini) / max(1e-6, maxi - mini)))
        chaud = QColor(int(80 + 175 * frac), int(170 - 90 * frac), int(255 - 200 * frac))
        x, haut, bas = T * 0.32, T * 0.2, T * 0.68
        p.setPen(QPen(QColor(255, 255, 255, 200), T * 0.012))
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(QRectF(x - T * 0.04, haut, T * 0.08, bas - haut), T * 0.04, T * 0.04)
        p.drawEllipse(QPointF(x, bas + T * 0.02), T * 0.07, T * 0.07)
        p.setPen(Qt.NoPen)
        p.setBrush(chaud)
        niveau = bas - (bas - haut - T * 0.04) * frac
        p.drawRoundedRect(QRectF(x - T * 0.028, niveau, T * 0.056, bas - niveau + T * 0.02), T * 0.025, T * 0.025)
        p.drawEllipse(QPointF(x, bas + T * 0.02), T * 0.055, T * 0.055)
        p.setPen(QPen(QColor(255, 255, 255, 140), T * 0.006))
        for k in range(5):
            yy = haut + T * 0.04 + (bas - haut - T * 0.08) * k / 4
            p.drawLine(QPointF(x + T * 0.06, yy), QPointF(x + T * 0.1, yy))
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(T * 0.42, T * 0.36, T * 0.5, T * 0.2), f"{v:.0f}{unite}", _police(T, 0.13), T * 0.46)
        p.setPen(QColor(200, 200, 210))
        _texte_ajuste(p, QRectF(T * 0.42, T * 0.55, T * 0.5, T * 0.1), nom.upper(), _police(T, 0.045, False), T * 0.46)
    elif genre == "compte_a_rebours":                        # anneau qui se vide, chiffre qui bat
        from .goodies import bornes
        depuis = float(opts.get("depuis", 10))
        reste = max(0.0, depuis - (t - bornes(g)[0]))
        s = int(math.ceil(reste)) if reste > 0 else 0
        r = T * 0.38
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(14, 14, 20, 210))
        p.drawEllipse(QPointF(T / 2, T / 2), r * 1.08, r * 1.08)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 50), T * 0.04))
        p.drawEllipse(QPointF(T / 2, T / 2), r, r)
        p.setPen(QPen(accent, T * 0.045, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(T / 2 - r, T / 2 - r, 2 * r, 2 * r), 90 * 16, int(360 * 16 * (reste / max(0.01, depuis))))
        battement = 1 + 0.12 * max(0.0, 1 - (math.ceil(reste) - reste) * 4) if reste > 0 else 1
        p.save()
        p.translate(T / 2, T / 2)
        p.scale(battement, battement)
        p.setPen(QColor(255, 255, 255))
        texte = str(s) if s < 60 else f"{s // 60}:{s % 60:02d}"
        _texte_ajuste(p, QRectF(-T / 2, -T * 0.2, T, T * 0.4), texte, _police(T, 0.24 if len(texte) < 3 else 0.15), r * 1.5)
        p.restore()
    elif genre == "date":                                    # page de calendrier
        from . import langue
        from PySide6.QtCore import QLocale
        jour = None
        txt = str(opts.get("texte") or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
            try:
                jour = datetime.datetime.strptime(txt, fmt).date()
                break
            except ValueError:
                pass
        jour = jour or (datetime.date.fromisoformat(opts["jour"]) if opts.get("jour") else datetime.date.today())
        loc = QLocale(getattr(langue, "LANGUE", "fr") or "fr")
        x0, y0, w, h = T * 0.18, T * 0.14, T * 0.64, T * 0.7
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(QRectF(x0 + T * 0.02, y0 + T * 0.03, w, h), T * 0.06, T * 0.06)
        p.setBrush(QColor(250, 250, 252))
        p.drawRoundedRect(QRectF(x0, y0, w, h), T * 0.06, T * 0.06)
        haut = QPainterPath()
        haut.setFillRule(Qt.WindingFill)
        haut.addRoundedRect(QRectF(x0, y0, w, h * 0.28), T * 0.06, T * 0.06)
        haut.addRect(QRectF(x0, y0 + h * 0.18, w, h * 0.1))
        p.setBrush(QColor(opts.get("couleur") or "#e53935"))
        p.drawPath(haut.simplified())
        p.setBrush(QColor(60, 60, 70))
        for k in (0.3, 0.7):
            p.drawRoundedRect(QRectF(x0 + w * k - T * 0.015, y0 - T * 0.04, T * 0.03, T * 0.08), T * 0.015, T * 0.015)
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(x0, y0 + h * 0.07, w, h * 0.2), loc.monthName(jour.month).upper(), _police(T, 0.06), w * 0.8)
        p.setPen(QColor(30, 30, 38))
        _texte_ajuste(p, QRectF(x0, y0 + h * 0.28, w, h * 0.5), str(jour.day), _police(T, 0.26), w * 0.9)
        p.setPen(QColor(110, 110, 125))
        _texte_ajuste(p, QRectF(x0, y0 + h * 0.76, w, h * 0.2), loc.dayName(jour.isoweekday()).capitalize() + f" {jour.year}",
                      _police(T, 0.055, False), w * 0.9)
    elif genre == "bandeau":                                 # ruban moderne qui se déroule, texte qui glisse
        texte = str(opts.get("texte") or nom)
        dep = min(1.0, e * 1.3)
        y0, h = T * 0.38, T * 0.24
        p.setPen(Qt.NoPen)
        p.setBrush(accent.darker(160))
        p.drawPolygon(QPolygonF([QPointF(T * 0.02, y0 + h * 0.25), QPointF(T * 0.12, y0 + h * 0.25), QPointF(T * 0.12, y0 + h * 1.15),
                                 QPointF(T * 0.02, y0 + h * 1.15), QPointF(T * 0.06, y0 + h * 0.7)]))
        p.drawPolygon(QPolygonF([QPointF(T * 0.98, y0 + h * 0.25), QPointF(T * 0.88, y0 + h * 0.25), QPointF(T * 0.88, y0 + h * 1.15),
                                 QPointF(T * 0.98, y0 + h * 1.15), QPointF(T * 0.94, y0 + h * 0.7)]))
        largeur = T * 0.84 * dep
        grad = QLinearGradient(0, y0, 0, y0 + h)
        grad.setColorAt(0, accent.lighter(125))
        grad.setColorAt(1, accent)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(T / 2 - largeur / 2, y0, largeur, h), T * 0.02, T * 0.02)
        p.save()
        p.setClipRect(QRectF(T / 2 - largeur / 2, y0, largeur, h))
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(0, y0, T, h), texte.upper(), _police(T, 0.1), T * 0.76)
        p.restore()
        # reflet qui passe
        u = ((t * 0.5) % 1.6) - 0.3
        p.save()
        p.setClipRect(QRectF(T / 2 - largeur / 2, y0, largeur, h))
        reflet = QLinearGradient(T * u, 0, T * (u + 0.15), 0)
        reflet.setColorAt(0, QColor(255, 255, 255, 0))
        reflet.setColorAt(0.5, QColor(255, 255, 255, 70))
        reflet.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(0, y0, T, h), QBrush(reflet))
        p.restore()
    elif genre == "horaires":                                # panneau suspendu avec horloge et horaires
        texte = str(opts.get("texte") or _("Ouvert 9h – 19h"))
        balance = math.sin(t * 1.6) * 3
        p.save()
        p.translate(T / 2, T * 0.12)
        p.rotate(balance)
        p.setPen(QPen(QColor(220, 220, 225), T * 0.01))
        p.drawLine(QPointF(-T * 0.2, 0), QPointF(-T * 0.28, T * 0.18))
        p.drawLine(QPointF(T * 0.2, 0), QPointF(T * 0.28, T * 0.18))
        p.setBrush(QColor(255, 255, 255))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), T * 0.025, T * 0.025)
        p.setBrush(QColor(14, 14, 20, 225))
        p.setPen(QPen(accent, T * 0.012))
        p.drawRoundedRect(QRectF(-T * 0.42, T * 0.18, T * 0.84, T * 0.5), T * 0.06, T * 0.06)
        p.setPen(QPen(accent, T * 0.014))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, T * 0.32), T * 0.07, T * 0.07)
        p.drawLine(QPointF(0, T * 0.32), QPointF(0, T * 0.27))
        p.drawLine(QPointF(0, T * 0.32), QPointF(T * 0.04, T * 0.34))
        p.setPen(QColor(255, 255, 255))
        lignes = texte.split("|")
        hl = T * 0.24 / max(1, len(lignes))
        for k, ligne in enumerate(lignes):
            _texte_ajuste(p, QRectF(-T * 0.4, T * 0.41 + k * hl, T * 0.8, hl), ligne.strip(), _police(T, 0.075), T * 0.76)
        p.restore()
    elif genre == "prix":                                    # étiquette de prix suspendue
        texte = str(opts.get("texte") or "9,90 €")
        p.save()
        p.translate(T / 2, T / 2)
        p.rotate(-12 + math.sin(t * 2) * 3)
        tag = QPainterPath()
        w, h = T * 0.72, T * 0.36
        tag.moveTo(-w / 2, -h / 2)
        tag.lineTo(w / 2 - h * 0.45, -h / 2)
        tag.lineTo(w / 2, 0)
        tag.lineTo(w / 2 - h * 0.45, h / 2)
        tag.lineTo(-w / 2, h / 2)
        tag.closeSubpath()
        trou = QPainterPath()
        trou.addEllipse(QPointF(w / 2 - h * 0.4, 0), T * 0.025, T * 0.025)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawPath(tag.translated(T * 0.015, T * 0.02))
        p.setBrush(accent)
        p.drawPath(tag.subtracted(trou))
        p.setPen(QPen(QColor(255, 255, 255, 200), T * 0.008, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(-w / 2 + T * 0.03, -h / 2 + T * 0.03, w - h * 0.45 - T * 0.03, h - T * 0.06), T * 0.02, T * 0.02)
        p.setPen(QColor(30, 25, 10))
        _texte_ajuste(p, QRectF(-w / 2, -h / 2, w - h * 0.4, h), texte, _police(T, 0.13), w - h * 0.55)
        p.restore()
    elif genre == "pastille":                                # pastille étoilée qui tourne doucement et pulse
        texte = str(opts.get("texte") or _("PROMO"))
        pulse = 1 + 0.05 * math.sin(t * 5)
        p.save()
        p.translate(T / 2, T / 2)
        p.scale(pulse, pulse)
        p.rotate(t * 15)
        etoile = QPolygonF()
        for k in range(32):
            r = T * (0.42 if k % 2 == 0 else 0.36)
            a = math.pi * k / 16
            etoile.append(QPointF(math.cos(a) * r, math.sin(a) * r))
        p.setPen(Qt.NoPen)
        p.setBrush(accent)
        p.drawPolygon(etoile)
        p.setPen(QPen(QColor(255, 255, 255, 180), T * 0.008, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(0, 0), T * 0.3, T * 0.3)
        p.rotate(-t * 15 - 12)
        p.setPen(QColor(255, 255, 255))
        lignes = texte.split("|")
        hl = T * 0.36 / max(1, len(lignes))
        for k, ligne in enumerate(lignes):
            _texte_ajuste(p, QRectF(-T * 0.3, -T * 0.18 + k * hl, T * 0.6, hl), ligne.strip().upper(), _police(T, 0.11), T * 0.52)
        p.restore()
    elif genre == "compteur":                                # compteur de vitesse moderne en arc
        frac = max(0.0, min(1.0, (v - mini) / max(1e-6, maxi - mini)))
        r = T * 0.4
        rect = QRectF(T / 2 - r, T / 2 - r, 2 * r, 2 * r)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(14, 14, 20, 215))
        p.drawEllipse(QPointF(T / 2, T / 2), r * 1.1, r * 1.1)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 45), T * 0.05, Qt.SolidLine, Qt.FlatCap))
        p.drawArc(rect, 225 * 16, -270 * 16)
        grad = QLinearGradient(T * 0.1, 0, T * 0.9, 0)
        grad.setColorAt(0, accent)
        grad.setColorAt(1, QColor(255, 82, 82))
        p.setPen(QPen(QBrush(grad), T * 0.05, Qt.SolidLine, Qt.FlatCap))
        p.drawArc(rect, 225 * 16, int(-270 * 16 * frac))
        p.setPen(QColor(255, 255, 255))
        _texte_ajuste(p, QRectF(0, T * 0.36, T, T * 0.22), f"{v:.0f}", _police(T, 0.2), T * 0.6)
        p.setPen(QColor(190, 190, 200))
        _texte_ajuste(p, QRectF(0, T * 0.56, T, T * 0.1), unite, _police(T, 0.06, False), T * 0.5)
    p.restore()
