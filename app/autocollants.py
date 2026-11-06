"""Autocollants (0.4.1) : polaroïd, post-it et flèche, dessinés comme les Goodies (export et aperçu identiques).

Options : texte, couleur, angle (inclinaison du polaroïd ou du post-it, direction de la flèche), chemin (photo du
polaroïd). Ils arrivent avec une petite animation (le polaroïd tombe, le post-it se colle, la flèche se trace) et
peuvent suivre une personne comme tout Goodie.
"""
import math

from .langue import _

GENRES = {"polaroid": (_("Polaroïd"), "", (0, 0)), "post_it": (_("Post-it"), "", (0, 0)), "fleche": (_("Flèche"), "", (0, 0)),
          "bandeau_tendance": (_("Titre bandeau (style YouTube)"), "", (0, 0)), "surligne": (_("Mot surligné"), "", (0, 0))}

STYLES_FLECHE = [("courbe", _("Courbe dessinée à la main")), ("droite", _("Droite")), ("boucle", _("Avec une boucle")),
                 ("zigzag", _("Eclair (zigzag)"))]
STYLES_BANDEAU = [("incline", _("Boîte inclinée")), ("deux", _("Deux lignes, deux couleurs")), ("contour", _("Lettres à gros contour")),
                  ("etiquette", _("Etiquette noire, texte jaune"))]
COULEURS_TENDANCE = ["#ff3b30", "#ff8c1a", "#ffd21f", "#ffffff", "#1e90ff", "#2ecc40", "#ff4fa3", "#111111"]


def _chemin_fleche(style, L, sens=1.0):
    """Tracé de la flèche, de (-L, 0) vers (L, 0), en QPainterPath ; renvoie (chemin, angle d'arrivée en radians)."""
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPainterPath
    ch = QPainterPath(QPointF(-L, 0))
    if style == "droite":
        ch.lineTo(QPointF(L, 0))
        return ch, 0.0
    if style == "boucle":
        ch.cubicTo(QPointF(-L * 0.3, -L * 0.55 * sens), QPointF(L * 0.25, -L * 0.6 * sens), QPointF(0.05 * L, -L * 0.2 * sens))
        ch.cubicTo(QPointF(-L * 0.12, L * 0.05 * sens), QPointF(L * 0.35, L * 0.25 * sens), QPointF(L, L * 0.05 * sens))
        return ch, math.atan2(-0.2 * sens, 0.65)
    if style == "zigzag":
        for x, y in ((-0.45, -0.22), (-0.1, 0.18), (0.25, -0.18), (1.0, 0.0)):
            ch.lineTo(QPointF(x * L, y * L * sens))
        return ch, math.atan2(0.18 * sens, 0.75)
    # courbe « à la main » : un arc légèrement irrégulier
    ch.cubicTo(QPointF(-L * 0.45, -L * 0.62 * sens), QPointF(L * 0.4, -L * 0.7 * sens), QPointF(L, -L * 0.08 * sens))
    return ch, math.atan2(0.62 * sens, 0.6)


def _dessiner_fleche(p, g, t, taille, u):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QPainterPath, QPen, QPolygonF
    from . import cles as K
    opts = g.get("options") or {}
    p.rotate(K.angle_goodie(g, t))                    # 0 = vers la droite, 90 = vers le bas ; s'anime avec les images clefs
    if opts.get("miroir"):
        p.scale(1, -1)
    couleur = QColor(opts.get("couleur") or "#ff3b30")
    contour = QColor(opts.get("contour") or ("#ffffff" if couleur.lightness() < 200 else "#111111"))
    pulse = 1 + 0.04 * math.sin(t * 6) if u >= 1 and opts.get("pulse", True) else 1
    p.scale(pulse, pulse)
    L = taille * 0.36
    e = taille * float(opts.get("epaisseur", 0.055))
    ch, ang_fin = _chemin_fleche(opts.get("style") or "droite", L)
    # tracé progressif : seule la partie déjà « dessinée » est montrée
    n = 60
    k = max(1, int(n * (u if opts.get("dessin", True) else 1.0)))
    pts = [ch.pointAtPercent(i / n) for i in range(k + 1)]
    trace = QPainterPath(pts[0])
    for q in pts[1:]:
        trace.lineTo(q)
    bout = pts[-1]
    if len(pts) > 1:
        a = math.atan2(bout.y() - pts[-2].y(), bout.x() - pts[-2].x())
    else:
        a = ang_fin
    tete = QPolygonF([QPointF(bout.x() + math.cos(a) * e * 1.9, bout.y() + math.sin(a) * e * 1.9),
                      QPointF(bout.x() + math.cos(a + 2.45) * e * 2.4, bout.y() + math.sin(a + 2.45) * e * 2.4),
                      QPointF(bout.x() + math.cos(a - 2.45) * e * 2.4, bout.y() + math.sin(a - 2.45) * e * 2.4)])
    # ombre, contour épais (blanc), puis la flèche : le style des miniatures YouTube
    for dx, coul, ep in ((taille * 0.012, QColor(0, 0, 0, 110), e + e * 1.1), (0, contour, e + e * 0.9), (0, couleur, e)):
        p.save()
        p.translate(dx, dx)
        p.setPen(QPen(coul, ep, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(trace)
        if u > 0.55:
            p.setPen(QPen(coul, ep - e, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin) if ep > e else Qt.NoPen)
            p.setBrush(coul)
            p.drawPolygon(tete)
        p.restore()


def _dessiner_bandeau(p, g, t, taille, u):
    """Titre façon miniature : MAJUSCULES grasses sur une boîte colorée inclinée, qui arrive en « pop »."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainterPath, QPen
    from . import cles as K
    opts = g.get("options") or {}
    style = opts.get("style") or "incline"
    texte = str(opts.get("texte") or _("TITRE CHOC")).strip()
    lignes = [x.strip() for x in texte.replace(" | ", "\n").replace("|", "\n").split("\n") if x.strip()] or [texte]
    if style == "deux" and len(lignes) == 1 and " " in texte:
        mots = texte.split()
        lignes = [" ".join(mots[:max(1, len(mots) // 2)]), " ".join(mots[max(1, len(mots) // 2):])]
    if opts.get("majuscules", True):
        lignes = [x.upper() for x in lignes]
    fond = QColor(opts.get("couleur") or ("#111111" if style == "etiquette" else "#ff8c1a"))
    fond2 = QColor(opts.get("couleur2") or "#ffd21f")
    coul_txt = QColor(opts.get("couleur_texte") or ("#ffd21f" if style == "etiquette" else ("#ffffff" if fond.lightness() < 170 else "#111111")))
    pop = u if u >= 1 else (1 - (1 - u) ** 3) * (1 + 0.18 * math.sin(u * math.pi))
    p.rotate((K.angle_goodie(g, t) if "angle" in opts or g.get("cles") else -4.0) * min(1.0, u * 1.2))
    p.scale(max(0.05, pop), max(0.05, pop))
    f = QFont(opts.get("police") or "Anton")
    f.setBold(True)
    f.setStretch(QFont.Condensed if style != "contour" else QFont.Unstretched)
    taille_pt = taille * (0.2 if style == "contour" else 0.17)
    f.setPixelSize(max(6, int(taille_pt)))
    fm = QFontMetricsF(f)
    if len(lignes) == 1 and " " in lignes[0] and fm.horizontalAdvance(lignes[0]) > taille * 0.95:
        mots = lignes[0].split()                       # trop long : deux lignes équilibrées
        coupe = min(range(1, len(mots)), key=lambda k: abs(len(" ".join(mots[:k])) - len(" ".join(mots[k:]))))
        lignes = [" ".join(mots[:coupe]), " ".join(mots[coupe:])]
    largeur_max = max(fm.horizontalAdvance(x) for x in lignes)
    if largeur_max > taille * 0.86:                   # le texte tient dans le carré du Goodie
        f.setPixelSize(max(6, int(taille_pt * taille * 0.86 / largeur_max)))
        fm = QFontMetricsF(f)
    h_ligne = fm.height() * 1.02
    p.setFont(f)
    y0 = -h_ligne * len(lignes) / 2
    for i, ligne in enumerate(lignes):
        w = fm.horizontalAdvance(ligne)
        r = QRectF(-w / 2, y0 + i * h_ligne, w, h_ligne)
        marge = h_ligne * 0.22
        boite = r.adjusted(-marge * 1.2, -marge * 0.25, marge * 1.2, marge * 0.25)
        if style in ("incline", "deux", "etiquette"):
            cf = fond2 if (style == "deux" and i % 2) else fond
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 120))
            p.drawRect(boite.translated(taille * 0.012, taille * 0.014))
            p.setBrush(cf)
            p.drawRect(boite)
            ct = coul_txt if not (style == "deux" and i % 2) else QColor("#111111" if cf.lightness() > 150 else "#ffffff")
            chemin = QPainterPath()
            chemin.addText(r.x(), r.y() + fm.ascent() + (h_ligne - fm.height()) / 2, f, ligne)
            p.setPen(Qt.NoPen)
            p.setBrush(ct)
            p.drawPath(chemin)
        else:                                          # lettres à gros contour noir, remplies de couleur
            chemin = QPainterPath()
            chemin.addText(r.x(), r.y() + fm.ascent(), f, ligne)
            p.setPen(QPen(QColor(0, 0, 0, 120), h_ligne * 0.26, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(Qt.NoBrush)
            p.drawPath(chemin.translated(taille * 0.01, taille * 0.012))
            p.setPen(QPen(QColor("#111111"), h_ligne * 0.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(chemin)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(opts.get("couleur") or "#ffd21f"))
            p.drawPath(chemin)


def _dessiner_surligne(p, g, t, taille, u):
    """Un mot passé au surligneur : la bande de couleur se pose de gauche à droite derrière le texte."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainterPath
    opts = g.get("options") or {}
    texte = str(opts.get("texte") or _("Incroyable"))
    f = QFont(opts.get("police") or "Nunito")
    f.setBold(True)
    f.setPixelSize(max(6, int(taille * 0.17)))
    fm = QFontMetricsF(f)
    w = fm.horizontalAdvance(texte)
    if w > taille * 0.9:
        f.setPixelSize(max(6, int(taille * 0.17 * taille * 0.9 / w)))
        fm = QFontMetricsF(f)
        w = fm.horizontalAdvance(texte)
    h = fm.height()
    coul = QColor(opts.get("couleur") or "#ffe14d")
    coul.setAlpha(225)
    from . import cles as K
    p.rotate(K.angle_goodie(g, t) if "angle" in opts or g.get("cles") else -2.0)
    p.setPen(Qt.NoPen)
    p.setBrush(coul)
    p.drawRoundedRect(QRectF(-w / 2 - h * 0.15, -h * 0.05, (w + h * 0.3) * min(1.0, u * 1.4), h * 0.62), h * 0.12, h * 0.12)
    ch = QPainterPath()
    ch.addText(-w / 2, fm.ascent() * 0.5, f, texte)
    p.setBrush(QColor(opts.get("couleur_texte") or "#111111"))
    p.drawPath(ch)


def _arrivee(g, t, duree=0.35):
    duree = float(((g.get("options") or {}).get("duree_trace")) or duree)
    from .goodies import bornes
    d0 = bornes(g)[0]
    u = max(0.0, min(1.0, (t - d0) / duree))
    return 1 - (1 - u) ** 3


def dessiner(p, g, t, taille, cache):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage
    opts = g.get("options") or {}
    genre = g["genre"]
    u = _arrivee(g, t)
    c = taille / 2
    p.save()
    p.translate(c, c)
    if genre in ("fleche", "bandeau_tendance", "surligne"):
        {"fleche": _dessiner_fleche, "bandeau_tendance": _dessiner_bandeau, "surligne": _dessiner_surligne}[genre](p, g, t, taille, u)
        p.restore()
        return
    ang = float(opts.get("angle", -6 if genre == "polaroid" else 4))
    p.rotate(ang * (0.4 + 0.6 * u) + (1 - u) * 18)
    s = 1.12 - 0.12 * u if genre == "polaroid" else 0.9 + 0.1 * u
    p.scale(s, s)
    p.setOpacity(min(1.0, u * 2))
    if genre == "polaroid":
        w, h = taille * 0.72, taille * 0.84
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRect(QRectF(-w / 2 + taille * 0.02, -h / 2 + taille * 0.025, w, h))
        p.setBrush(QColor(250, 250, 246))
        p.drawRect(QRectF(-w / 2, -h / 2, w, h))
        zone = QRectF(-w / 2 + w * 0.07, -h / 2 + w * 0.07, w * 0.86, w * 0.86)
        if "photo" not in cache:
            cache["photo"] = QImage(opts["chemin"]) if opts.get("chemin") else QImage()
        img = cache["photo"]
        if not img.isNull():
            src = img.rect()
            k = min(src.width(), src.height())
            p.drawImage(zone, img, QRectF((src.width() - k) / 2, (src.height() - k) / 2, k, k))
        else:
            p.setBrush(QColor(60, 70, 85))
            p.drawRect(zone)
        texte = str(opts.get("texte") or "")
        if texte:
            f = QFont("Nunito")
            f.setPointSizeF(max(5.0, taille * 0.06))
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(40, 40, 60))
            p.drawText(QRectF(-w / 2, zone.bottom(), w, h / 2 - zone.bottom()), Qt.AlignCenter, texte)
    else:                                              # post-it
        w = taille * 0.8
        couleur = QColor(opts.get("couleur") or "#ffe066")
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRect(QRectF(-w / 2 + taille * 0.015, -w / 2 + taille * 0.02, w, w))
        p.setBrush(couleur)
        p.drawRect(QRectF(-w / 2, -w / 2, w, w))
        p.setBrush(couleur.darker(110))
        p.drawRect(QRectF(-w / 2, -w / 2, w, w * 0.1))
        p.setBrush(QColor(255, 255, 255, 120))                  # ruban adhésif
        p.drawRect(QRectF(-w * 0.18, -w / 2 - w * 0.05, w * 0.36, w * 0.1))
        f = QFont("Nunito")
        f.setPointSizeF(max(5.0, taille * 0.075))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(40, 40, 50))
        p.drawText(QRectF(-w / 2 + w * 0.08, -w / 2 + w * 0.14, w * 0.84, w * 0.8), Qt.AlignCenter | Qt.TextWordWrap,
                   str(opts.get("texte") or _("Note")))
    p.restore()
