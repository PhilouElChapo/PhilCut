"""Autocollants (0.4.1) : polaroïd, post-it et flèche, dessinés comme les Goodies (export et aperçu identiques).

Options : texte, couleur, angle (inclinaison du polaroïd ou du post-it, direction de la flèche), chemin (photo du
polaroïd). Ils arrivent avec une petite animation (le polaroïd tombe, le post-it se colle, la flèche se trace) et
peuvent suivre une personne comme tout Goodie.
"""
import math

from .langue import _

GENRES = {"polaroid": (_("Polaroïd"), "", (0, 0)), "post_it": (_("Post-it"), "", (0, 0)), "fleche": (_("Flèche"), "", (0, 0))}


def _arrivee(g, t, duree=0.35):
    from .goodies import bornes
    d0 = bornes(g)[0]
    u = max(0.0, min(1.0, (t - d0) / duree))
    return 1 - (1 - u) ** 3


def dessiner(p, g, t, taille, cache):
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPen, QPolygonF
    opts = g.get("options") or {}
    genre = g["genre"]
    u = _arrivee(g, t)
    c = taille / 2
    p.save()
    p.translate(c, c)
    if genre == "fleche":
        ang = float(opts.get("angle", 0))               # 0 = vers la droite, 90 = vers le bas
        p.rotate(ang)
        couleur = QColor(opts.get("couleur") or "#ff3b30")
        pulse = 1 + 0.05 * math.sin(t * 6) if u >= 1 else 1
        p.scale(pulse, pulse)
        L = taille * 0.42 * u
        e = taille * 0.07
        p.setPen(QPen(QColor(0, 0, 0, 120), e * 1.5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(-taille * 0.42 + 3, 3), QPointF(-taille * 0.42 + 2 * L + 3, 3))
        p.setPen(QPen(couleur, e, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(-taille * 0.42, 0), QPointF(-taille * 0.42 + 2 * L, 0))
        if u > 0.6:
            x = -taille * 0.42 + 2 * L
            tete = QPolygonF([QPointF(x + e * 1.4, 0), QPointF(x - e * 1.6, -e * 2.0), QPointF(x - e * 1.6, e * 2.0)])
            p.setPen(Qt.NoPen)
            p.setBrush(couleur)
            p.drawPolygon(tete)
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
