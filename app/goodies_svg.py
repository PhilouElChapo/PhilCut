"""Goodies dessinés en SVG venus du catalogue en ligne (0.9.26) : de petites illustrations (cœur, pouce, soleil…)
animées par PhilCut (pop, rebond, flottement, rotation, battement, balancement). Ajoutés sans réinstaller : la veille
mensuelle les dépose dans catalogue/nouveautes.json."""
import math

SVG = {}                   # id -> {"nom", "svg", "animation", "pack"}
ANIMATIONS = ("pop", "rebond", "flotte", "tourne", "battement", "balance")
_RENDUS = {}


def genre(ident):
    return "svg:" + ident


def enregistrer(ident, e):
    SVG[ident] = e
    _RENDUS.pop(ident, None)


def _rendu(ident):
    from PySide6.QtCore import QByteArray
    from PySide6.QtSvg import QSvgRenderer
    r = _RENDUS.get(ident)
    if r is None:
        r = QSvgRenderer(QByteArray(SVG[ident]["svg"].encode("utf-8")))
        _RENDUS[ident] = r
    return r


def valide(svg):
    from PySide6.QtCore import QByteArray
    from PySide6.QtSvg import QSvgRenderer
    return QSvgRenderer(QByteArray((svg or "").encode("utf-8"))).isValid()


def dessiner(p, g, t, taille):
    from PySide6.QtCore import QRectF
    ident = g["genre"][4:]
    e = SVG.get(ident)
    if not e:
        return
    r = _rendu(ident)
    if not r.isValid():
        return
    anim = (g.get("options") or {}).get("animation") or e.get("animation", "pop")
    u = max(0.0, float(t) - float(g.get("debut", 0)))
    arrivee = min(1.0, u / 0.35)
    s, ang, dy = 1.0, 0.0, 0.0
    if anim == "pop":
        s = 0.2 + 0.8 * arrivee + (0.12 * math.sin(arrivee * math.pi) if arrivee < 1 else 0)
    elif anim == "rebond":
        dy = -abs(math.sin(u * 3.2)) * 0.12 * taille
    elif anim == "flotte":
        dy = math.sin(u * 1.6) * 0.05 * taille
    elif anim == "tourne":
        ang = (u * 90) % 360
    elif anim == "battement":
        s = 1 + 0.1 * max(0.0, math.sin(u * 7.5)) ** 3
    elif anim == "balance":
        ang = math.sin(u * 2.5) * 12
    p.save()
    p.setOpacity(min(1.0, arrivee * 2))
    p.translate(taille / 2, taille / 2 + dy)
    p.rotate(ang)
    p.scale(s, s)
    m = taille * 0.42
    r.render(p, QRectF(-m, -m, 2 * m, 2 * m))
    p.restore()
