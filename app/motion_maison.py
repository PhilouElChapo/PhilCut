"""Le moteur maison des animations (0.9.99) : dessiné image par image par PhilCut (QPainter), encodé par FFmpeg.

Reprend le look de l'étalon « Chiffres » validé par Philippe le 19/11 (fond sombre qui respire, grille estompée, chiffre en
dégradé avec lueur, pastille qui arrive en rebond, barres qui poussent l'une après l'autre, courbe qui se trace), avec les
couleurs et polices de la charte, les curseurs de la fenêtre et les zones sûres du vertical.
"""
import math, os, subprocess

from .langue import _
from . import motion as M


# ------------------------------------------------------------------ courbes de temps
def bezier(x1, y1, x2, y2):
    def f(t):
        if t <= 0:
            return 0.0
        if t >= 1:
            return 1.0
        u = t
        for _i in range(8):                      # Newton sur x(u) = t
            x = 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u ** 2 * x2 + u ** 3 - t
            dx = 3 * (1 - u) ** 2 * x1 + 6 * (1 - u) * u * (x2 - x1) + 3 * u ** 2 * (1 - x2)
            if abs(dx) < 1e-6:
                break
            u = min(1.0, max(0.0, u - x / dx))
        return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u ** 2 * y2 + u ** 3
    return f


SORTIE = bezier(0.16, 1, 0.3, 1)
DOUCE = bezier(0.22, 1, 0.36, 1)
ALLER_RETOUR = bezier(0.65, 0, 0.35, 1)


def entre(t, t0, t1, ease=None):
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    x = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return ease(x) if ease else x


def ressort(t, rebond=0.35, raideur=120.0):
    """Ressort amorti (comme spring() de Remotion) : 0 → 1 ; rebond 0 = sans dépassement, 1 = très élastique."""
    if t <= 0:
        return 0.0
    w = math.sqrt(raideur)
    z = 1.0 - 0.7 * max(0.0, min(1.0, rebond))          # amortissement relatif : 1 (critique) à 0,3
    if z >= 0.999:
        return 1 - math.exp(-w * t) * (1 + w * t)
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * t) * (math.cos(wd * t) + z * w / wd * math.sin(wd * t))


def borne_haut(v):
    """Le haut joli d'un axe : 9 820 → 10 000 ; 37 → 40."""
    if v <= 0:
        return 1.0
    e = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= v:
            return m * e
    return 10 * e


# ------------------------------------------------------------------ le rendu
class Rendu:
    def __init__(self, anim):
        from PySide6.QtGui import QColor
        from . import charte as CH
        from .vignette import _polices
        _polices()
        self.a = anim
        self.L, self.H = [int(x) // 2 * 2 for x in (anim.get("taille") or (1920, 1080))]
        self.ch = CH.complete(anim.get("charte"))
        c = self.ch["couleurs"]
        self.C = {k: QColor(v) for k, v in c.items()}
        self.zx, self.zy, self.zw, self.zh = M.zone_sure(dict(anim, taille=[self.L, self.H]))
        self.vertical = self.H > self.L
        base = min(self.zw / 950.0, self.zh / 1300.0) if self.vertical else min(self.zw / 1600.0, self.zh / 880.0)
        self.u = base * M.reglage(anim, "taille_texte")
        self.vitesse = M.reglage(anim, "vitesse")
        mouv = {"doux": 0.5, "vif": 1.0, "rebond": 1.6}.get(self.ch.get("mouvement"), 1.0)
        self.rebond = max(0.0, min(1.0, M.reglage(anim, "rebond") * mouv))
        self.lueur = M.reglage(anim, "lueur") * (0.0 if self.ch.get("allure") == "sobre" else 1.0)
        self.decalage = 0.06 + 0.22 * M.reglage(anim, "decalage")
        self.epaisseur = M.reglage(anim, "epaisseur")
        self.transparent = bool(anim.get("transparent"))
        self.D = float(anim.get("duree") or M.duree_conseillee(anim.get("genre")))
        self.vertical = self.H > self.L
        self._grille = None
        self._logo = None
        self._capture = None
        self.h = M.horaire(anim)
        d = [x for x in anim.get("donnees") or [] if len(x) >= 2]
        self.donnees = [(str(l), float(v)) for l, v in d] or [(l, float(v)) for l, v in M.EXEMPLE]

    # -------------------------------------------------- outils
    def police(self, titre=True, taille=40, poids=600):
        from PySide6.QtGui import QFont
        f = QFont(self.ch.get("police_titre" if titre else "police_texte") or "Poppins")
        f.setPixelSize(max(6, int(taille)))
        f.setWeight(QFont.Weight(int(poids)))
        return f

    def couleur(self, cle, alpha=1.0):
        from PySide6.QtGui import QColor
        c = QColor(self.C[cle])
        c.setAlphaF(max(0.0, min(1.0, alpha * c.alphaF())))
        return c

    def texte(self, p, x, y, t, font, couleur, ancre="gauche", espacement=0.0, opacite=1.0):
        """Ecrit t ; y = ligne de base ; renvoie la largeur."""
        from PySide6.QtGui import QFont, QFontMetricsF
        if espacement:
            font = QFont(font)
            font.setLetterSpacing(QFont.AbsoluteSpacing, espacement)
        fm = QFontMetricsF(font)
        w = fm.horizontalAdvance(t)
        if ancre == "centre":
            x -= w / 2
        elif ancre == "droite":
            x -= w
        p.save()
        p.setOpacity(p.opacity() * opacite)
        p.setFont(font)
        p.setPen(couleur)
        p.drawText(int(round(x)), int(round(y)), t)
        p.restore()
        return w

    def chemin_chiffres(self, texte, font, cx, y):
        """Le chiffre en chasse fixe (les chiffres ne dansent pas pendant qu'il monte), centré sur cx."""
        from PySide6.QtGui import QFontMetricsF, QPainterPath
        fm = QFontMetricsF(font)
        cell = max(fm.horizontalAdvance(c) for c in "0123456789")
        largeurs = [cell if ch.isdigit() else fm.horizontalAdvance(ch) for ch in texte]
        x = cx - sum(largeurs) / 2
        path = QPainterPath()
        for ch, w in zip(texte, largeurs):
            dx = (w - fm.horizontalAdvance(ch)) / 2
            path.addText(x + dx, y, font, ch)
            x += w
        return path

    def lueur_chemin(self, p, path, couleur, force):
        """Lueur douce autour d'un tracé (plusieurs traits larges et transparents)."""
        from PySide6.QtGui import QPen
        from PySide6.QtCore import Qt
        if force <= 0.01:
            return
        for k in range(6, 0, -1):
            c = self.couleur(couleur, 0.05 * force)
            pen = QPen(c, k * 9 * self.u)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setCapStyle(Qt.RoundCap)
            p.strokePath(path, pen)

    # -------------------------------------------------- le fond
    def fond(self, p, t):
        from PySide6.QtGui import QRadialGradient, QColor
        from PySide6.QtCore import QPointF, Qt
        if self.transparent:
            return
        p.fillRect(0, 0, self.L, self.H, self.C["fond"])
        allure = self.ch.get("allure")
        if allure == "sobre" or self.a.get("variante") == 2:
            return
        f = t * 30
        L, H = self.L, self.H
        e = max(L, H) / 1920
        for (cx, cy, r, cle, a) in ((-300 * e + 700 * e + math.sin(f / 90) * 60 * e, -700 * e + 700 * e + math.cos(f / 110) * 50 * e,
                                     700 * e, "accent", 0.20),
                                    (L + 400 * e - 600 * e + math.cos(f / 80) * 50 * e, H + 700 * e - 600 * e + math.sin(f / 100) * 40 * e,
                                     600 * e, "accent2", 0.13)):
            g = QRadialGradient(QPointF(cx, cy), r)
            g.setColorAt(0, self.couleur(cle, a * (0.4 + 0.6 * max(self.lueur, 0.3))))
            g.setColorAt(0.6, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawEllipse(QPointF(cx, cy), r, r)
        p.drawImage(0, 0, self.grille())

    def grille(self):
        from PySide6.QtGui import QImage, QPainter, QColor, QRadialGradient
        from PySide6.QtCore import QPointF, Qt
        if self._grille is not None:
            return self._grille
        img = QImage(self.L, self.H, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        q = QPainter(img)
        pas = max(20, int(80 * max(self.L, self.H) / 1920))
        q.setPen(QColor(255, 255, 255, 16 if self.ch.get("allure") != "tech" else 30))
        for x in range(0, self.L, pas):
            q.drawLine(x, 0, x, self.H)
        for y in range(0, self.H, pas):
            q.drawLine(0, y, self.L, y)
        q.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        g = QRadialGradient(QPointF(self.L / 2, self.H / 2), max(self.L, self.H) * 0.55)
        g.setColorAt(0.0, QColor(0, 0, 0, 255))
        g.setColorAt(0.45, QColor(0, 0, 0, 255))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        q.fillRect(0, 0, self.L, self.H, g)
        q.end()
        self._grille = img
        return img

    def panneau(self, p, opacite):
        """En transparence (posé sur le film), un panneau discret derrière le graphique pour qu'il se lise."""
        from PySide6.QtCore import QRectF, Qt
        if not self.transparent or opacite <= 0:
            return
        m = 30 * self.u
        p.save()
        p.setOpacity(opacite)
        p.setPen(Qt.NoPen)
        p.setBrush(self.couleur("fond", 0.72))
        p.drawRoundedRect(QRectF(self.zx - m, self.zy - m, self.zw + 2 * m, self.zh + 2 * m), 36 * self.u, 36 * self.u)
        p.restore()

    def logo(self, p):
        from PySide6.QtGui import QImage
        chemin = self.ch.get("logo") or ""
        if not chemin or not os.path.exists(chemin) or self.a.get("logo") is False:
            return
        if self._logo is None:
            img = QImage(chemin)
            if img.isNull():
                self._logo = False
                return
            h = int(70 * self.u * (1.3 if self.vertical else 1.0))
            from PySide6.QtCore import Qt
            self._logo = img.scaledToHeight(max(8, h), Qt.SmoothTransformation)
        if self._logo:
            p.save()
            p.setOpacity(0.9)
            p.drawImage(int(self.zx + self.zw - self._logo.width()), int(self.zy - self._logo.height() * 0.2 - 30 * self.u), self._logo)
            p.restore()

    def source(self, p, opacite):
        s = (self.a.get("source") or "").strip()
        if s:
            self.texte(p, self.zx, self.zy + self.zh + 40 * self.u, _("Source : {s}", s=s), self.police(False, 22 * self.u, 400),
                       self.C["doux"], opacite=opacite)

    # -------------------------------------------------- scènes (1.0.0 : sur l'horaire commun, en secondes de l'animation)
    def _k(self, t, debut, raideur=120.0):
        """Ressort à partir de « debut », au rythme de la vitesse."""
        return ressort((t - debut) * self.vitesse, self.rebond, raideur)

    def _fondu(self, p, t, a, b, dernier):
        V = self.vitesse
        entree = entre(t, a, a + 0.5 / V, SORTIE)
        sortie = 0.0 if dernier else entre(t, b - 0.5 / V, b, lambda x: x ** 3)
        return entree * (1 - sortie), sortie

    def scene_compteur(self, p, t, a, b, dernier):
        from PySide6.QtGui import QLinearGradient, QFontMetricsF
        from PySide6.QtCore import QPointF, QRectF, Qt
        h = self.h["compteur"]
        u, cx, V = self.u, self.zx + self.zw / 2, self.vitesse
        cy = self.zy + self.zh * (0.48 if not self.vertical else 0.42)
        sortie = 0.0 if dernier else entre(t, b - 0.6 / V, b, lambda x: x ** 3)
        p.save()
        p.setOpacity(1 - sortie)
        p.translate(cx, cy)
        p.scale(1 - sortie * 0.08, 1 - sortie * 0.08)
        p.translate(-cx, -cy)
        self.panneau(p, 1.0)
        a0 = entre(t, a, a + 0.6 / V)
        lab_y = cy - 170 * u + (1 - entre(t, a, a + 0.6 / V, SORTIE)) * 20 * u
        self.texte(p, cx, lab_y, (self.a.get("titre") or "").upper(), self.police(False, 34 * u, 600), self.C["doux"], "centre",
                   espacement=6 * u, opacite=a0)
        v = float(self.a.get("valeur") if self.a.get("valeur") is not None else sum(x for _l, x in self.donnees))
        n = v * entre(t, h["debut"], h["fin"], DOUCE)
        grand = self.police(True, 260 * u * (0.8 if self.vertical else 1.0), 700)
        path = self.chemin_chiffres(M.nombre_texte(self.a, round(n, self.a.get("decimales") or 0)), grand, cx, cy + 90 * u)
        self.lueur_chemin(p, path, "accent", self.lueur * entre(t, h["debut"], h["debut"] + 0.9 / V))
        r = path.boundingRect()
        g = QLinearGradient(QPointF(r.left(), r.top()), QPointF(r.right(), r.bottom()))
        g.setColorAt(0.3, self.C["texte"])
        g.setColorAt(0.7, self.C["accent"])
        g.setColorAt(1.0, self.C["accent2"])
        p.fillPath(path, g)
        badge = (self.a.get("badge") or "").strip()
        if badge:
            k = self._k(t, h["badge"], 160)
            if k > 0.001:
                f = self.police(False, 38 * u, 600)
                w = QFontMetricsF(f).horizontalAdvance(badge) + 60 * u
                hh = 66 * u
                by = cy + 150 * u
                p.save()
                p.setOpacity(p.opacity() * min(1.0, k))
                p.translate(cx, by + hh / 2)
                p.scale(k, k)
                gb = QLinearGradient(QPointF(-w / 2, 0), QPointF(w / 2, 0))
                gb.setColorAt(0, self.C["accent2"])
                gb.setColorAt(1, self.C["accent"])
                p.setPen(Qt.NoPen)
                p.setBrush(gb)
                p.drawRoundedRect(QRectF(-w / 2, -hh / 2, w, hh), hh / 2, hh / 2)
                self.texte(p, 0, 13 * u, badge, f, self.C["fond"], "centre")
                p.restore()
        self.source(p, a0)
        p.restore()

    def scene_barres(self, p, t, a, b, dernier):
        from PySide6.QtGui import QLinearGradient, QPainterPath
        from PySide6.QtCore import QPointF, QRectF
        h = self.h["barres"]
        u, V = self.u, self.vitesse
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        x0, y0 = self.zx, self.zy
        self.texte(p, x0, y0 + 60 * u, self.a.get("titre_barres") or self.a.get("titre") or "", self.police(True, 64 * u, 700),
                   self.C["texte"])
        self.texte(p, x0, y0 + 110 * u, self.a.get("sous_titre") or "", self.police(False, 30 * u, 400), self.C["doux"])
        haut, bas = y0 + 190 * u, self.zy + self.zh - 60 * u
        H = bas - haut
        vmax = borne_haut(max(v for _l, v in self.donnees))
        gauche = x0 + 110 * u
        for i in range(5):
            gval = vmax * i / 4
            yy = bas - (gval / vmax) * H
            g0 = h["grille"] + i * 0.1 / V
            trace = entre(t, g0, g0 + 0.7 / V, SORTIE)
            self.texte(p, x0, yy + 8 * u, M.nombre(gval), self.police(False, 22 * u, 400), self.C["doux"], opacite=trace)
            p.setPen(self.couleur("texte", 0.11))
            p.drawLine(QPointF(gauche, yy), QPointF(gauche + (self.zx + self.zw - gauche) * trace, yy))
        n = len(self.donnees)
        ecart = 46 * u * (0.6 if n > 8 else 1.0)
        larg = ((self.zx + self.zw - gauche) - ecart * (n - 1)) / n
        larg_barre = larg * (0.45 + 0.55 * self.epaisseur)
        rec = max(range(n), key=lambda i: self.donnees[i][1])
        entrees = list(h["entrees"]) + [h["entrees"][-1] if h["entrees"] else a] * max(0, n - len(h["entrees"]))
        for i, (lib, val) in enumerate(self.donnees):
            k = self._k(t, entrees[i], 90)
            bx = gauche + i * (larg + ecart) + (larg - larg_barre) / 2
            hb = (val / vmax) * H * k
            record = i == rec
            halo = entre(t, h["halo"], h["halo"] + 0.6 / V) if record else 0.0
            r = QRectF(bx, bas - hb, larg_barre, max(0.0, hb))
            if hb > 0.5:
                g = QLinearGradient(QPointF(0, r.top()), QPointF(0, r.bottom()))
                if record:
                    g.setColorAt(0, self.C["accent2"])
                    g.setColorAt(1, self.C["accent"])
                else:
                    g.setColorAt(0, self.couleur("accent", 0.8))
                    g.setColorAt(1, self.couleur("accent", 0.27))
                path = QPainterPath()
                rr = min(18 * u, larg_barre / 2, hb)
                path.addRoundedRect(r, rr, rr)
                if record and halo > 0 and self.lueur > 0:
                    self.lueur_chemin(p, path, "accent2", halo * self.lueur)
                p.fillPath(path, g)
            self.texte(p, bx + larg_barre / 2, bas - hb - 12 * u, M.nombre_texte(self.a, val * min(1.0, k)),
                       self.police(True, 32 * u * (0.8 if n > 8 else 1.0), 700),
                       self.C["accent2"] if record else self.C["texte"], "centre", opacite=min(1.0, k))
            self.texte(p, bx + larg_barre / 2, bas + 38 * u, lib, self.police(False, 26 * u * (0.8 if n > 8 else 1.0), 400),
                       self.C["doux"], "centre")
        self.source(p, 1.0)
        p.restore()

    def scene_courbe(self, p, t, a, b, dernier):
        from PySide6.QtGui import QLinearGradient, QPainterPath, QPen, QColor
        from PySide6.QtCore import QPointF, QRectF, Qt
        h = self.h["courbe"]
        u = self.u
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        x0, y0 = self.zx, self.zy
        self.texte(p, x0, y0 + 60 * u, self.a.get("titre_courbe") or self.a.get("titre") or "", self.police(True, 64 * u, 700),
                   self.C["texte"])
        self.texte(p, x0, y0 + 110 * u, self.a.get("sous_titre_courbe") or self.a.get("sous_titre") or "",
                   self.police(False, 30 * u, 400), self.C["doux"])
        haut, bas = y0 + 230 * u, self.zy + self.zh - 90 * u
        gauche, droite = x0 + 20 * u, self.zx + self.zw - 20 * u
        vmax = borne_haut(max(v for _l, v in self.donnees))
        n = len(self.donnees)
        pts = [QPointF(gauche + (i / max(1, n - 1)) * (droite - gauche), bas - (v / vmax) * (bas - haut)) for i, (_l, v) in
               enumerate(self.donnees)]
        d = QPainterPath(pts[0])
        for i in range(1, n):
            a_, b_ = pts[i - 1], pts[i]
            cxm = (a_.x() + b_.x()) / 2
            d.cubicTo(QPointF(cxm, a_.y()), QPointF(cxm, b_.y()), b_)
        prog = entre(t, h["debut"], h["fin"], ALLER_RETOUR)
        k = min(n - 1, prog * (n - 1))
        i0 = int(math.floor(k))
        tt = k - i0
        a_, b_ = pts[i0], pts[min(n - 1, i0 + 1)]
        point = QPointF(a_.x() + (b_.x() - a_.x()) * tt, a_.y() + (b_.y() - a_.y()) * tt)
        aire = QPainterPath(d)
        aire.lineTo(QPointF(droite, bas))
        aire.lineTo(QPointF(gauche, bas))
        aire.closeSubpath()
        p.save()
        p.setClipRect(QRectF(0, 0, point.x() + 1, self.H))
        ga = QLinearGradient(QPointF(0, haut), QPointF(0, bas))
        ga.setColorAt(0, self.couleur("accent", 0.35))
        ga.setColorAt(1, self.couleur("accent", 0.0))
        p.fillPath(aire, ga)
        self.lueur_chemin(p, d, "accent", 0.7 * self.lueur)
        gt = QLinearGradient(QPointF(gauche, 0), QPointF(droite, 0))
        gt.setColorAt(0, self.C["accent"])
        gt.setColorAt(1, self.C["accent2"])
        pen = QPen(gt, 8 * u * (0.5 + self.epaisseur))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.strokePath(d, pen)
        p.restore()
        for i, q in enumerate(pts):
            if prog > 0 and k >= i - 1e-6:
                p.setPen(QPen(self.C["texte"], 3 * u))
                p.setBrush(self.C["fond"])
                p.drawEllipse(q, 7 * u, 7 * u)
            self.texte(p, q.x(), bas + 40 * u, self.donnees[i][0], self.police(False, 24 * u, 400), self.C["doux"], "centre")
        if prog > 0:
            for k2 in range(4, 0, -1):
                p.setPen(Qt.NoPen)
                p.setBrush(self.couleur("accent2", 0.08 * self.lueur))
                p.drawEllipse(point, (16 + k2 * 8) * u, (16 + k2 * 8) * u)
            p.setBrush(self.C["accent2"])
            p.drawEllipse(point, 16 * u, 16 * u)
        rec = max(range(n), key=lambda i: self.donnees[i][1])
        r = self._k(t, h["record"], 140)
        if r > 0.001:
            q = pts[rec]
            w, hh = 300 * u, 96 * u
            x = min(max(self.zx, q.x() - w - 40 * u), self.zx + self.zw - w)
            y = max(y0 + 130 * u, q.y() - 60 * u - hh + (1 - min(1.0, r)) * 30 * u)
            p.save()
            p.setOpacity(p.opacity() * min(1.0, r))
            p.setPen(QPen(QColor(255, 255, 255, 48), 1.5 * u))
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(x, y, w, hh), 20 * u, 20 * u)
            self.texte(p, x + 28 * u, y + 40 * u, _("Record"), self.police(False, 24 * u, 400), self.C["doux"])
            self.texte(p, x + 28 * u, y + 78 * u, M.nombre_texte(self.a, self.donnees[rec][1]), self.police(True, 38 * u, 700),
                       self.C["texte"])
            p.restore()
        self.source(p, 1.0)
        p.restore()

    def scene_titre(self, p, t, a, b, dernier):
        from PySide6.QtGui import QFontMetricsF
        from PySide6.QtCore import QRectF, Qt
        h = self.h["titre"]
        u, V = self.u, self.vitesse
        sortie = entre(t, b - 0.6 / V, b, lambda x: x ** 3)
        p.save()
        p.setOpacity(1 - sortie)
        self.panneau(p, 1.0)
        mots = (self.a.get("titre") or "").split()
        f = self.police(True, 120 * u * (0.75 if self.vertical else 1.0), 700)
        fm = QFontMetricsF(f)
        lignes, cour = [], []
        for m in mots:                                 # retour à la ligne dans la zone sûre
            if cour and fm.horizontalAdvance(" ".join(cour + [m])) > self.zw:
                lignes.append(cour)
                cour = []
            cour.append(m)
        if cour:
            lignes.append(cour)
        cle_mot = max(mots, key=lambda m: len(m.strip(".,;:!?«»\"'"))) if len(mots) > 2 else ""   # le mot fort en couleur
        hl = fm.height() * 1.05
        y = self.zy + self.zh / 2 - hl * len(lignes) / 2 + fm.ascent()
        k = 0
        for ligne in lignes:
            x = self.zx + (self.zw - fm.horizontalAdvance(" ".join(ligne))) / 2
            for m in ligne:
                r = self._k(t, h["mots"][k] if k < len(h["mots"]) else a, 150)
                op = min(1.0, max(0.0, r))
                p.save()
                p.translate(0, (1 - min(1.0, r)) * 60 * u)
                self.texte(p, x, y, m, f, self.C["accent"] if m == cle_mot else self.C["texte"], opacite=op)
                p.restore()
                x += fm.horizontalAdvance(m + " ")
                k += 1
            y += hl
        trait = entre(t, h["trait"], h["trait"] + 0.8 / V, SORTIE)
        lt = self.zw * 0.22 * trait
        p.setPen(Qt.NoPen)
        p.setBrush(self.C["accent2"])
        p.drawRoundedRect(QRectF(self.zx + self.zw / 2 - lt / 2, y - hl * 0.55, lt, 8 * u * (0.5 + self.epaisseur)), 4 * u, 4 * u)
        st = self.a.get("sous_titre") or ""
        if st:
            self.texte(p, self.zx + self.zw / 2, y + 10 * u, st, self.police(False, 40 * u, 400), self.C["doux"], "centre",
                       opacite=entre(t, h["sous_titre"], h["sous_titre"] + 0.6 / V))
        p.restore()

    # -------------------------------------------------- 1.0.0 : habillage
    def scene_bandeau(self, p, t, a, b, dernier):
        """Bandeau nom et fonction (tiers inférieur) : le trait d'accent glisse, le nom monte, la fonction suit ; sortie."""
        from PySide6.QtGui import QFontMetricsF
        from PySide6.QtCore import QRectF, Qt
        h = self.h["bandeau"]
        u, V = self.u * 1.15, self.vitesse
        k = self._k(t, h["entree"], 160)
        sortie = entre(t, h["sortie"], h["sortie"] + 0.5 / V, lambda x: x ** 3)
        if k <= 0.001:
            return
        nom, fonction = self.a.get("titre") or "", self.a.get("sous_titre") or ""
        fn, ff = self.police(True, 54 * u, 700), self.police(False, 32 * u, 400)
        w = max(QFontMetricsF(fn).horizontalAdvance(nom), QFontMetricsF(ff).horizontalAdvance(fonction)) + 80 * u
        x = self.zx
        y = self.zy + self.zh - 170 * u
        p.save()
        p.setOpacity(1 - sortie)
        p.setPen(Qt.NoPen)
        largeur = w * min(1.0, k) * (1 - sortie * 0.3)
        p.setBrush(self.couleur("fond", 0.86))
        p.drawRoundedRect(QRectF(x, y, largeur, 150 * u), 14 * u * self.ch.get("coins", 0.6), 14 * u * self.ch.get("coins", 0.6))
        p.setBrush(self.C["accent"])
        p.drawRoundedRect(QRectF(x, y, 10 * u * (0.5 + self.epaisseur), 150 * u), 4 * u, 4 * u)
        p.setClipRect(QRectF(x, y, largeur, 150 * u))
        kt = self._k(t, h["texte"], 140)
        self.texte(p, x + 40 * u, y + 70 * u + (1 - min(1.0, kt)) * 30 * u, nom, fn, self.C["texte"], opacite=min(1.0, kt))
        kf = self._k(t, h["texte"] + 0.15 / V, 140)
        self.texte(p, x + 40 * u, y + 120 * u + (1 - min(1.0, kf)) * 30 * u, fonction, ff, self.C["accent2"], opacite=min(1.0, kf))
        p.restore()

    def scene_progression(self, p, t, a, b, dernier):
        """Barre de progression fine en bas (au-dessus des zones mortes en vertical), avec les chapitres."""
        from PySide6.QtCore import QRectF, QPointF, Qt
        from PySide6.QtGui import QLinearGradient
        u = max(self.L, self.H) / 1920
        haut = max(4.0, 8 * u * (0.5 + self.epaisseur))
        y = (self.zy + self.zh + 40 * u) if self.vertical else (self.H - haut - 18 * u)
        x0, x1 = 24 * u, self.L - 24 * u
        prog = min(1.0, max(0.0, t / max(0.01, self.D)))
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(self.couleur("texte", 0.18))
        p.drawRoundedRect(QRectF(x0, y, x1 - x0, haut), haut / 2, haut / 2)
        g = QLinearGradient(QPointF(x0, 0), QPointF(x1, 0))
        g.setColorAt(0, self.C["accent"])
        g.setColorAt(1, self.C["accent2"])
        p.setBrush(g)
        p.drawRoundedRect(QRectF(x0, y, (x1 - x0) * prog, haut), haut / 2, haut / 2)
        chap = [c for c in self.a.get("chapitres") or [] if 0 < float(c[0]) < self.D]
        actif = None
        for tc, nom in chap:
            xc = x0 + (x1 - x0) * float(tc) / self.D
            p.setBrush(self.C["fond"])
            p.drawRect(QRectF(xc - 1.5 * u, y - 1, 3 * u, haut + 2))
            if float(tc) <= t:
                actif = nom
        if actif is None and chap:
            actif = None
        if actif:
            self.texte(p, x0, y - 14 * u, actif, self.police(False, 26 * u, 600), self.C["texte"],
                       opacite=0.9 * min(1.0, 0.3 + prog * 10))
        p.restore()

    def scene_defilement(self, p, t, a, b, dernier):
        """Une capture dans un cadre arrondi, qui entre en grossissant puis défile de haut en bas."""
        from PySide6.QtGui import QImage, QPainterPath, QColor
        from PySide6.QtCore import QRectF, Qt
        V = self.vitesse
        if self._capture is None:
            img = QImage(self.a.get("image") or "")
            self._capture = img if not img.isNull() else False
        cadre_w = self.zw * (0.62 if not self.vertical else 0.92)
        cadre_h = self.zh * 0.9
        cx, cy = self.zx + self.zw / 2, self.zy + self.zh / 2
        k = self._k(t, a + 0.1, 110)
        p.save()
        p.translate(cx, cy + (1 - min(1.0, k)) * 80 * self.u)
        sc = 0.85 + 0.15 * min(1.2, k)
        p.scale(sc, sc)
        p.setOpacity(min(1.0, max(0.0, k)) * (1 - entre(t, b - 0.5 / V, b)))
        r = QRectF(-cadre_w / 2, -cadre_h / 2, cadre_w, cadre_h)
        rayon = 28 * self.u * (0.4 + self.ch.get("coins", 0.6))
        for e in range(6, 0, -1):                       # ombre douce
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 14))
            p.drawRoundedRect(r.adjusted(-e * 5 * self.u, -e * 3 * self.u, e * 5 * self.u, e * 7 * self.u), rayon + e * 5, rayon + e * 5)
        chemin = QPainterPath()
        chemin.addRoundedRect(r, rayon, rayon)
        p.setClipPath(chemin)
        p.fillRect(r, QColor("#FFFFFF"))
        if self._capture:
            img = self._capture
            ech = cadre_w / img.width()
            hi = img.height() * ech
            prog = entre(t, a + 0.9 / V, b - 0.9 / V, ALLER_RETOUR)
            dy = -max(0.0, hi - cadre_h) * prog
            p.drawImage(QRectF(-cadre_w / 2, -cadre_h / 2 + dy, cadre_w, hi), img)
        else:
            self.texte(p, 0, 0, _("Choisissez une capture"), self.police(False, 40 * self.u, 400), QColor("#666666"), "centre")
        p.setClipping(False)
        p.setPen(self.couleur("accent", 0.9))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, rayon, rayon)
        p.restore()

    def scene_sous_titres(self, p, t, a, b, dernier):
        """Les mots dits, animés au rythme de la voix (style choisi)."""
        from PySide6.QtGui import QFontMetricsF, QColor
        from PySide6.QtCore import QRectF, Qt
        style = self.a.get("style_st") or "surligne"
        maj = bool(self.a.get("majuscules", True))
        mots = self.a.get("mots") or []
        u = self.u * 1.1
        if style == "un_mot":
            m = next((x for x in mots if x[0] <= t < max(x[1], x[0] + 0.25)), None)
            if not m:
                return
            k = ressort((t - m[0]) * 1.4, max(0.3, self.rebond), 220)
            f = self.police(True, 150 * u * (0.8 if self.vertical else 1.0), 800)
            txt = m[2].upper() if maj else m[2]
            p.save()
            cx, cy = self.zx + self.zw / 2, self.zy + self.zh * 0.62
            p.translate(cx, cy)
            p.scale(0.6 + 0.4 * min(1.2, k), 0.6 + 0.4 * min(1.2, k))
            fm = QFontMetricsF(f)
            from PySide6.QtGui import QPainterPath, QPen
            path = QPainterPath()
            path.addText(-fm.horizontalAdvance(txt) / 2, fm.ascent() / 3, f, txt)
            p.strokePath(path, QPen(QColor(0, 0, 0, 200), 14 * u, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.fillPath(path, self.C["accent2"] if len(txt) > 6 else self.C["texte"])
            p.restore()
            return
        lignes = M.lignes_st(mots, max_car=M.ST_VERTICAL_CAR if self.vertical else M.ST_HORIZONTAL_CAR)
        ligne = next((l for l in lignes if l["t0"] - 0.05 <= t < l["t1"] + 0.25), None)
        if not ligne:
            return
        f = self.police(True, 64 * u * (M.ST_VERTICAL_TAILLE if self.vertical else 1.0), 800)
        fm = QFontMetricsF(f)
        textes = [(m[2].upper() if maj else m[2]) for m in ligne["mots"]]
        esp = fm.horizontalAdvance(" ")
        largeur = sum(fm.horizontalAdvance(x) for x in textes) + esp * (len(textes) - 1)
        x = self.zx + (self.zw - largeur) / 2
        y = self.zy + self.zh * (0.80 if not self.vertical else 0.74)
        from PySide6.QtGui import QPainterPath, QPen
        for (t0, t1, _w), txt in zip(ligne["mots"], textes):
            w = fm.horizontalAdvance(txt)
            dit = t0 <= t
            courant = t0 <= t < max(t1, t0 + 0.15)
            p.save()
            if style == "saute":
                if not dit:
                    p.restore()
                    x += w + esp
                    continue
                k = ressort((t - t0) * 1.3, max(0.3, self.rebond), 260)
                p.translate(x + w / 2, y)
                p.scale(min(1.25, 0.5 + 0.5 * k), min(1.25, 0.5 + 0.5 * k))
                p.translate(-(x + w / 2), -y)
            if style == "surligne" and courant:
                k = entre(t, t0, t0 + 0.08)
                p.setPen(Qt.NoPen)
                p.setBrush(self.C["accent"])
                m_ = 10 * u
                p.drawRoundedRect(QRectF(x - m_, y - fm.ascent() * 0.86 - m_ * 0.4, (w + 2 * m_) * k, fm.ascent() * 1.05 + m_),
                                  10 * u, 10 * u)
            path = QPainterPath()
            path.addText(x, y, f, txt)
            p.strokePath(path, QPen(QColor(0, 0, 0, 190), 10 * u, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            if style == "karaoke":
                coul = self.C["accent2"] if dit else self.C["texte"]
            elif style == "surligne":
                coul = self.C["texte"]
            else:
                coul = self.C["accent2"] if courant else self.C["texte"]
            p.fillPath(path, coul)
            p.restore()
            x += w + esp

    # -------------------------------------------------- 1.0.1 : plus de types
    def _titre_haut(self, p):
        u = self.u
        self.texte(p, self.zx, self.zy + 60 * u, self.a.get("titre") or "", self.police(True, 64 * u, 700), self.C["texte"])
        if self.a.get("sous_titre"):
            self.texte(p, self.zx, self.zy + 110 * u, self.a["sous_titre"], self.police(False, 30 * u, 400), self.C["doux"])

    def _lignes(self, texte, font, largeur):
        from PySide6.QtGui import QFontMetricsF
        fm = QFontMetricsF(font)
        lignes, cour = [], []
        for m in str(texte).split():
            if cour and fm.horizontalAdvance(" ".join(cour + [m])) > largeur:
                lignes.append(" ".join(cour))
                cour = []
            cour.append(m)
        if cour:
            lignes.append(" ".join(cour))
        return lignes

    def _couleur_hex(self, c, alpha=1.0):
        from PySide6.QtGui import QColor
        q = QColor(c)
        q.setAlphaF(alpha)
        return q

    def scene_camembert(self, p, t, a, b, dernier):
        from PySide6.QtGui import QPainterPath, QPen
        from PySide6.QtCore import QPointF, QRectF, Qt
        h, u, V = self.h["camembert"], self.u, self.vitesse
        el = M.elements(self.a)
        tot = sum(v for _l, v, _t in el) or 1.0
        cols = M.palette(self.ch, len(el))
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        self._titre_haut(p)
        if self.vertical:
            cx, cy, rr = self.zx + self.zw / 2, self.zy + self.zh * 0.42, min(self.zw * 0.36, self.zh * 0.22)
        else:
            cx, cy, rr = self.zx + self.zw * 0.3, self.zy + self.zh * 0.58, min(self.zh * 0.32, self.zw * 0.22)
        ep = rr * (0.22 + 0.3 * self.epaisseur)
        p.setPen(QPen(self.couleur("texte", 0.08), ep, Qt.SolidLine, Qt.FlatCap))
        p.drawEllipse(QPointF(cx, cy), rr, rr)
        angle = 90.0
        for i, (lib, v, _x) in enumerate(el):
            k = entre(t, h["entrees"][i], h["entrees"][i] + 0.7 / V, SORTIE)
            balay = -360.0 * v / tot
            if k > 0:
                pen = QPen(self._couleur_hex(cols[i]), ep, Qt.SolidLine, Qt.FlatCap)
                p.setPen(pen)
                p.drawArc(QRectF(cx - rr, cy - rr, 2 * rr, 2 * rr), int(angle * 16), int(balay * k * 16))
            angle += balay
            # légende
            if self.vertical:
                lx, ly = self.zx + (i % 2) * self.zw / 2, cy + rr + ep + 60 * u + (i // 2) * 56 * u
            else:
                lx, ly = self.zx + self.zw * 0.6, self.zy + self.zh * 0.28 + i * 62 * u
            ap = entre(t, h["entrees"][i], h["entrees"][i] + 0.5 / V)
            p.setPen(Qt.NoPen)
            p.setBrush(self._couleur_hex(cols[i], ap))
            p.drawRoundedRect(QRectF(lx, ly - 22 * u, 26 * u, 26 * u), 6 * u, 6 * u)
            self.texte(p, lx + 44 * u, ly, lib, self.police(False, 30 * u, 400), self.C["texte"], opacite=ap)
            self.texte(p, lx + (self.zw / 2 - 30 * u if self.vertical else self.zw * 0.4), ly, f"{M.nombre(100 * v / tot, 0)} %",
                       self.police(True, 30 * u, 700), self.C["accent2"], "droite", opacite=ap)
        rec = max(range(len(el)), key=lambda i: el[i][1]) if el else 0
        if el:
            kf = entre(t, h["fin"] - 0.4 / V, h["fin"] + 0.2 / V)
            self.texte(p, cx, cy + 20 * u, f"{M.nombre(100 * el[rec][1] / tot, 0)} %", self.police(True, 72 * u, 700), self.C["texte"],
                       "centre", opacite=kf)
            self.texte(p, cx, cy + 62 * u, el[rec][0], self.police(False, 26 * u, 400), self.C["doux"], "centre", opacite=kf)
        self.source(p, 1.0)
        p.restore()

    def scene_jauge(self, p, t, a, b, dernier):
        from PySide6.QtGui import QPen, QConicalGradient
        from PySide6.QtCore import QPointF, QRectF, Qt
        h, u = self.h["jauge"], self.u
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        cx, cy = self.zx + self.zw / 2, self.zy + self.zh * 0.5
        rr = min(self.zw, self.zh) * 0.3
        ep = rr * (0.12 + 0.18 * self.epaisseur)
        v = max(0.0, min(100.0, float(self.a.get("valeur") or 0)))
        k = entre(t, h["debut"], h["fin"], DOUCE)
        p.setPen(QPen(self.couleur("texte", 0.1), ep, Qt.SolidLine, Qt.RoundCap))
        p.drawEllipse(QPointF(cx, cy), rr, rr)
        g = QConicalGradient(QPointF(cx, cy), 90)
        g.setColorAt(0, self.C["accent2"])
        g.setColorAt(1, self.C["accent"])
        if k > 0:
            from PySide6.QtGui import QPainterPath
            arc = QPainterPath()
            arc.arcMoveTo(QRectF(cx - rr, cy - rr, 2 * rr, 2 * rr), 90)
            arc.arcTo(QRectF(cx - rr, cy - rr, 2 * rr, 2 * rr), 90, -3.6 * v * k)
            self.lueur_chemin(p, arc, "accent", 0.6 * self.lueur)
            p.strokePath(arc, QPen(g, ep, Qt.SolidLine, Qt.RoundCap))
        path = self.chemin_chiffres(M.nombre_texte(self.a, round(v * k)), self.police(True, rr * 0.55, 700), cx, cy + rr * 0.18)
        p.fillPath(path, self.C["texte"])
        self.texte(p, cx, cy - rr - ep - 40 * u, self.a.get("titre") or "", self.police(True, 56 * u, 700), self.C["texte"], "centre")
        self.texte(p, cx, cy + rr + ep + 60 * u, self.a.get("sous_titre") or "", self.police(False, 32 * u, 400), self.C["doux"], "centre",
                   opacite=entre(t, h["fin"] - 0.3, h["fin"] + 0.3))
        p.restore()

    def scene_comparaison(self, p, t, a, b, dernier):
        from PySide6.QtGui import QLinearGradient
        from PySide6.QtCore import QPointF, QRectF, Qt
        h, u, V = self.h["comparaison"], self.u, self.vitesse
        el = M.elements(self.a)
        if len(el) < 2:
            el = el + [("", 0.0, "")] * (2 - len(el))
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        self._titre_haut(p)
        vmax = max(1e-9, max(v for _l, v, _x in el))
        bas = self.zy + self.zh - 60 * u
        haut_barres = self.zh * (0.38 if not self.vertical else 0.3)
        for i, (lib, v, _x) in enumerate(el[:2]):
            k = self._k(t, h["entrees"][i], 110)
            cx = self.zx + self.zw * (0.27 if i == 0 else 0.73)
            hb = haut_barres * v / vmax * min(1.0, k)
            lb = self.zw * 0.16 * (0.6 + 0.6 * self.epaisseur)
            g = QLinearGradient(QPointF(0, bas - hb), QPointF(0, bas))
            g.setColorAt(0, self.C["accent2"] if i else self.couleur("accent", 0.9))
            g.setColorAt(1, self.couleur("accent", 0.3))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(QRectF(cx - lb / 2, bas - hb, lb, hb), 16 * u, 16 * u)
            self.texte(p, cx, bas - haut_barres - 110 * u, M.nombre_texte(self.a, v * min(1.0, k)), self.police(True, 96 * u, 700),
                       self.C["accent2"] if i else self.C["texte"], "centre", opacite=min(1.0, k))
            self.texte(p, cx, bas + 44 * u, lib, self.police(False, 32 * u, 600), self.C["doux"], "centre")
        if el[0][1]:
            d = (el[1][1] - el[0][1]) / abs(el[0][1]) * 100
            kb = self._k(t, h["fin"], 160)
            if kb > 0.001:
                txt = ("▲ +" if d >= 0 else "▼ ") + M.nombre(d, 0 if abs(d) >= 10 else 1) + " %"
                f = self.police(True, 44 * u, 700)
                from PySide6.QtGui import QFontMetricsF
                w = QFontMetricsF(f).horizontalAdvance(txt) + 50 * u
                cx, cy = self.zx + self.zw / 2, bas - haut_barres * 0.5
                p.save()
                p.translate(cx, cy)
                p.scale(min(1.2, kb), min(1.2, kb))
                p.setBrush(self.C["accent2"] if d >= 0 else self.C["accent"])
                p.drawRoundedRect(QRectF(-w / 2, -36 * u, w, 72 * u), 36 * u, 36 * u)
                self.texte(p, 0, 15 * u, txt, f, self.C["fond"], "centre")
                p.restore()
        self.source(p, 1.0)
        p.restore()

    def scene_classement(self, p, t, a, b, dernier):
        from PySide6.QtGui import QLinearGradient
        from PySide6.QtCore import QPointF, QRectF, Qt
        h, u = self.h["classement"], self.u
        el = M.elements(self.a)
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        self._titre_haut(p)
        n = max(1, len(el))
        y0 = self.zy + 170 * u
        pas = min(110 * u, (self.zy + self.zh - 30 * u - y0) / n)
        vmax = max(1e-9, max(v for _l, v, _x in el)) if el else 1
        g0 = self.zx + 90 * u + self.zw * 0.22
        largeur = self.zx + self.zw - 170 * u - g0
        for i, (lib, v, _x) in enumerate(el):
            k = self._k(t, h["entrees"][i], 100)
            y = y0 + i * pas
            hb = pas * (0.35 + 0.35 * self.epaisseur)
            ap = min(1.0, max(0.0, k))
            p.setPen(Qt.NoPen)
            p.setBrush(self._couleur_hex(self.ch["couleurs"]["accent2" if i == 0 else "accent"], ap))
            p.drawEllipse(QPointF(self.zx + 30 * u, y + hb / 2), 26 * u, 26 * u)
            self.texte(p, self.zx + 30 * u, y + hb / 2 + 11 * u, str(i + 1), self.police(True, 30 * u, 700), self.C["fond"], "centre", opacite=ap)
            self.texte(p, self.zx + 80 * u, y + hb / 2 + 11 * u, lib, self.police(False, 32 * u, 600), self.C["texte"], opacite=ap)
            w = largeur * v / vmax * min(1.0, k)
            g = QLinearGradient(QPointF(g0, 0), QPointF(g0 + largeur, 0))
            g.setColorAt(0, self.C["accent"])
            g.setColorAt(1, self.C["accent2"])
            p.setBrush(g)
            p.drawRoundedRect(QRectF(g0, y, max(0.0, w), hb), hb / 2, hb / 2)
            self.texte(p, g0 + w + 16 * u, y + hb / 2 + 11 * u, M.nombre_texte(self.a, v * min(1.0, k)), self.police(True, 32 * u, 700),
                       self.C["texte"], opacite=ap)
        self.source(p, 1.0)
        p.restore()

    def scene_chiffres_cles(self, p, t, a, b, dernier):
        from PySide6.QtCore import QRectF, Qt
        h, u = self.h["chiffres_cles"], self.u
        el = M.elements(self.a)
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        self._titre_haut(p)
        n = max(1, len(el))
        top = self.zy + 170 * u
        if self.vertical:
            cols, rows = 1, n
        else:
            cols, rows = (n, 1) if n <= 3 else (2, 2)
        gap = 30 * u
        tw = (self.zw - gap * (cols - 1)) / cols
        th = min((self.zy + self.zh - top - gap * (rows - 1)) / rows, 360 * u)
        for i, (lib, v, _x) in enumerate(el):
            k = self._k(t, h["entrees"][i], 120)
            x = self.zx + (i % cols) * (tw + gap)
            y = top + (i // cols) * (th + gap) + (1 - min(1.0, k)) * 40 * u
            ap = min(1.0, max(0.0, k))
            p.setPen(Qt.NoPen)
            p.setBrush(self.couleur("texte", 0.07 * ap))
            p.drawRoundedRect(QRectF(x, y, tw, th), 24 * u, 24 * u)
            p.setBrush(self._couleur_hex(self.ch["couleurs"]["accent2" if i % 2 else "accent"], ap))
            p.drawRoundedRect(QRectF(x, y, 10 * u, th), 5 * u, 5 * u)
            cpt = entre(t, h["entrees"][i], h["entrees"][i] + 1.4 / self.vitesse, DOUCE)
            taille = min(th * 0.42, tw / max(4, len(M.nombre_texte(self.a, v))) * 1.5)
            self.texte(p, x + tw / 2, y + th * 0.55, M.nombre_texte(self.a, v * cpt), self.police(True, taille, 700),
                       self.C["texte"], "centre", opacite=ap)
            self.texte(p, x + tw / 2, y + th * 0.55 + 56 * u, lib, self.police(False, 36 * u, 500), self.C["texte"], "centre", opacite=ap * 0.75)
        p.restore()

    def scene_chronologie(self, p, t, a, b, dernier):
        from PySide6.QtGui import QPen
        from PySide6.QtCore import QPointF, Qt
        h, u = self.h["chronologie"], self.u
        el = M.elements(self.a)
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        self._titre_haut(p)
        n = max(1, len(el))
        prog = entre(t, h["entrees"][0] - 0.3 if el else a, h["fin"], ALLER_RETOUR)
        if self.vertical:
            x, y0, y1 = self.zx + 40 * u, self.zy + 190 * u, self.zy + self.zh - 40 * u
            p.setPen(QPen(self.C["accent"], 6 * u * (0.5 + self.epaisseur), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x, y0), QPointF(x, y0 + (y1 - y0) * prog))
            for i, (d, _v, txt) in enumerate(el):
                y = y0 + (y1 - y0) * (i + 0.5) / n
                k = self._k(t, h["entrees"][i], 140)
                ap = min(1.0, max(0.0, k))
                p.setPen(Qt.NoPen)
                p.setBrush(self._couleur_hex(self.ch["couleurs"]["accent2"], ap))
                p.drawEllipse(QPointF(x, y), 14 * u * min(1.2, k), 14 * u * min(1.2, k))
                self.texte(p, x + 40 * u, y - 6 * u, d, self.police(True, 40 * u, 700), self.C["accent2"], opacite=ap)
                for j, l in enumerate(self._lignes(txt, self.police(False, 30 * u, 400), self.zw - 80 * u)[:2]):
                    self.texte(p, x + 40 * u, y + 36 * u + j * 36 * u, l, self.police(False, 30 * u, 400), self.C["texte"], opacite=ap)
        else:
            y, x0, x1 = self.zy + self.zh * 0.52, self.zx + 20 * u, self.zx + self.zw - 20 * u
            p.setPen(QPen(self.C["accent"], 6 * u * (0.5 + self.epaisseur), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(x0, y), QPointF(x0 + (x1 - x0) * prog, y))
            larg = (x1 - x0) / n
            for i, (d, _v, txt) in enumerate(el):
                x = x0 + larg * (i + 0.5)
                k = self._k(t, h["entrees"][i], 140)
                ap = min(1.0, max(0.0, k))
                p.setPen(Qt.NoPen)
                p.setBrush(self._couleur_hex(self.ch["couleurs"]["accent2"], ap))
                p.drawEllipse(QPointF(x, y), 16 * u * min(1.2, k), 16 * u * min(1.2, k))
                haut = i % 2 == 0
                self.texte(p, x, y - 60 * u if haut else y + 80 * u, d, self.police(True, 44 * u, 700), self.C["accent2"], "centre",
                           opacite=ap)
                lignes = self._lignes(txt, self.police(False, 28 * u, 400), larg - 20 * u)[:3]
                for j, l in enumerate(lignes):
                    yy = (y - 120 * u - (len(lignes) - 1 - j) * 34 * u) if haut else (y + 126 * u + j * 34 * u)
                    self.texte(p, x, yy, l, self.police(False, 28 * u, 400), self.C["texte"], "centre", opacite=ap)
        p.restore()

    def scene_liste(self, p, t, a, b, dernier):
        from PySide6.QtGui import QPen, QPainterPath
        from PySide6.QtCore import QPointF, Qt
        h, u = self.h["liste"], self.u
        el = M.elements(self.a)
        op, _s = self._fondu(p, t, a, b, dernier)
        p.save()
        p.setOpacity(op)
        self.panneau(p, 1.0)
        self._titre_haut(p)
        n = max(1, len(el))
        y0 = self.zy + 200 * u
        pas = min(120 * u, (self.zy + self.zh - y0) / n)
        f = self.police(False, 40 * u * (0.9 if self.vertical else 1.0), 600)
        for i, (_d, _v, txt) in enumerate(el):
            k = self._k(t, h["entrees"][i], 130)
            ap = min(1.0, max(0.0, k))
            y = y0 + i * pas
            dx = (1 - min(1.0, k)) * -60 * u
            p.setPen(Qt.NoPen)
            p.setBrush(self._couleur_hex(self.ch["couleurs"]["accent"], ap))
            c = QPointF(self.zx + 26 * u + dx, y - 14 * u)
            p.drawEllipse(c, 24 * u, 24 * u)
            coche = QPainterPath(QPointF(c.x() - 10 * u, c.y()))
            coche.lineTo(QPointF(c.x() - 2 * u, c.y() + 8 * u))
            coche.lineTo(QPointF(c.x() + 11 * u, c.y() - 9 * u))
            p.strokePath(coche, QPen(self._couleur_hex(self.ch["couleurs"]["fond"], ap), 5 * u, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            l = self._lignes(txt, f, self.zw - 90 * u)
            self.texte(p, self.zx + 76 * u + dx, y, l[0] if l else "", f, self.C["texte"], opacite=ap)
        p.restore()

    def scene_citation(self, p, t, a, b, dernier):
        from PySide6.QtGui import QFontMetricsF
        from PySide6.QtCore import QRectF, Qt
        h, u, V = self.h["citation"], self.u, self.vitesse
        sortie = entre(t, b - 0.6 / V, b, lambda x: x ** 3)
        p.save()
        p.setOpacity(1 - sortie)
        self.panneau(p, 1.0)
        f = self.police(True, 70 * u * (0.85 if self.vertical else 1.0), 600)
        fm = QFontMetricsF(f)
        lignes = self._lignes(self.a.get("titre") or "", f, self.zw * 0.86)
        hl = fm.height() * 1.15
        y = self.zy + self.zh / 2 - hl * len(lignes) / 2 + fm.ascent()
        kq = self._k(t, a + 0.1, 120)
        self.texte(p, self.zx + self.zw * 0.05, y - fm.ascent() * 0.2, "«", self.police(True, 220 * u, 700), self.C["accent"],
                   opacite=min(1.0, max(0.0, kq)) * 0.9)
        k = 0
        for l in lignes:
            x = self.zx + (self.zw - fm.horizontalAdvance(l)) / 2
            for m in l.split():
                r = self._k(t, h["mots"][k] if k < len(h["mots"]) else a, 150)
                self.texte(p, x, y + (1 - min(1.0, r)) * 30 * u, m, f, self.C["texte"], opacite=min(1.0, max(0.0, r)))
                x += fm.horizontalAdvance(m + " ")
                k += 1
            y += hl
        auteur = self.a.get("sous_titre") or ""
        if auteur:
            ka = entre(t, h["auteur"], h["auteur"] + 0.6 / V, SORTIE)
            p.setPen(Qt.NoPen)
            p.setBrush(self.C["accent2"])
            p.drawRoundedRect(QRectF(self.zx + self.zw / 2 - 160 * u, y - 10 * u, 60 * u * ka, 5 * u), 2 * u, 2 * u)
            self.texte(p, self.zx + self.zw / 2 - 80 * u, y + 2 * u, auteur, self.police(False, 36 * u, 400), self.C["doux"], opacite=ka)
        p.restore()

    def scene_appel(self, p, t, a, b, dernier):
        from PySide6.QtGui import QFontMetricsF, QPainterPath, QColor, QPen
        from PySide6.QtCore import QPointF, QRectF, Qt
        h, u, V = self.h["appel"], self.u * 1.2, self.vitesse
        sortie = entre(t, b - 0.5 / V, b)
        k = self._k(t, h["entree"], 150)
        if k <= 0.001:
            return
        p.save()
        p.setOpacity((1 - sortie) * min(1.0, k))
        cx, cy = self.zx + self.zw / 2, self.zy + self.zh * (0.62 if not self.vertical else 0.55)
        if self.a.get("transparent"):                     # posé sur le film : un fond discret pour qu'il se lise
            lw = self.zw * (0.95 if self.vertical else 0.6)
            p.setPen(Qt.NoPen)
            p.setBrush(self.couleur("fond", 0.75))
            p.drawRoundedRect(QRectF(cx - lw / 2, cy - 230 * u, lw, 360 * u), 30 * u, 30 * u)
        self.texte(p, cx, cy - 130 * u, self.a.get("titre") or "", self.police(True, 56 * u, 700), self.C["texte"], "centre")
        clique = t >= h["clic"]
        txt = (self.a.get("bouton_fait") or _("Abonné ✓")) if clique else (self.a.get("bouton") or _("S'abonner"))
        f = self.police(True, 46 * u, 700)
        w = QFontMetricsF(f).horizontalAdvance(txt) + 120 * u
        hb = 100 * u
        appui = 1 - 0.08 * math.sin(math.pi * entre(t, h["clic"] - 0.08, h["clic"] + 0.18))
        p.save()
        p.translate(cx, cy)
        p.scale(min(1.15, k) * appui, min(1.15, k) * appui)
        p.setPen(Qt.NoPen)
        p.setBrush(self.couleur("doux", 0.5) if clique else self.C["accent"])
        p.drawRoundedRect(QRectF(-w / 2, -hb / 2, w, hb), hb / 2 * self.ch.get("coins", 0.6) + 8 * u, hb / 2 * self.ch.get("coins", 0.6) + 8 * u)
        self.texte(p, 0, 16 * u, txt, f, self.C["fond"] if not clique else self.C["texte"], "centre")
        p.restore()
        if self.a.get("sous_titre"):
            self.texte(p, cx, cy + hb / 2 + 60 * u, self.a["sous_titre"], self.police(False, 32 * u, 400), self.C["doux"], "centre")
        # la souris arrive sur le bouton, clique, repart
        kc = entre(t, h["curseur"], h["clic"] - 0.05, SORTIE)
        if kc > 0 and t < h["clic"] + 0.9:
            px = cx + w * 0.25 + (1 - kc) * self.zw * 0.35
            py = cy + 10 * u + (1 - kc) * self.zh * 0.3
            fl = QPainterPath(QPointF(px, py))
            for dx, dy in ((0, 46), (12, 35), (21, 54), (29, 50), (20, 32), (36, 32)):
                fl.lineTo(QPointF(px + dx * u, py + dy * u))
            fl.closeSubpath()
            p.setPen(QPen(QColor(0, 0, 0, 200), 3 * u))
            p.setBrush(QColor("#FFFFFF"))
            p.drawPath(fl)
            if clique:
                r = entre(t, h["clic"], h["clic"] + 0.5) * 60 * u
                p.setPen(QPen(self._couleur_hex(self.ch["couleurs"]["accent2"], 1 - r / (60 * u)), 4 * u))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(px, py), r, r)
        p.restore()

    # -------------------------------------------------- une image
    def dessiner(self, p, t):
        """L'image à l'instant t (en secondes de l'animation), sur l'horaire commun."""
        self.fond(p, t)
        fins = max((b for _a, b in self.h["scenes"].values()), default=self.D)
        for nom, (a, b) in sorted(self.h["scenes"].items(), key=lambda x: x[1][0]):
            if a - 0.01 <= t <= b + 0.01:
                getattr(self, "scene_" + nom)(p, t, a, b, b >= fins - 1e-6)
        self.logo(p)


def apercu_image(anim, t, taille=(640, 360)):
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import Qt
    L, H = anim.get("taille") or (1920, 1080)
    k = min(taille[0] / L, taille[1] / H)
    a = dict(anim, taille=[max(2, int(L * k)) // 2 * 2, max(2, int(H * k)) // 2 * 2])
    rd = Rendu(a)
    img = QImage(rd.L, rd.H, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    rd.dessiner(p, t)
    p.end()
    return img


def fabriquer(anim, sortie, progression=None, arret=lambda: False):
    """Image par image, encodée en MP4 (H.264), ou en MOV ProRes 4444 avec transparence pour poser sur le film."""
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtCore import Qt
    from . import moteur
    rd = Rendu(anim)
    L, H = rd.L, rd.H
    cadence = int(anim.get("cadence") or 30)
    nb = max(1, int(round(rd.D * cadence)))
    if anim.get("transparent"):
        sortie = os.path.splitext(sortie)[0] + ".mov"
        enc = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0", sortie]
        audio = []
    else:
        enc = ["-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac",
               "-b:a", "128k", "-movflags", "+faststart", sortie]
        audio = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd = [moteur.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{L}x{H}",
           "-r", str(cadence), "-i", "pipe:0"] + audio + enc
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **moteur._sans_console())
    img = QImage(L, H, QImage.Format_ARGB32)
    try:
        for k in range(nb):
            if arret():
                raise InterruptedError()
            img.fill(Qt.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.TextAntialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            rd.dessiner(p, k / cadence)
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
