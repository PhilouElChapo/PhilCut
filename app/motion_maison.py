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

    # -------------------------------------------------- scènes
    def scene_compteur(self, p, t, D, dernier=False):
        from PySide6.QtGui import QLinearGradient, QPainterPath
        from PySide6.QtCore import QPointF, QRectF, Qt
        u, cx = self.u, self.zx + self.zw / 2
        cy = self.zy + self.zh * (0.48 if not self.vertical else 0.42)
        sortie = 0.0 if dernier else entre(t, D - 0.6, D, lambda x: x ** 3)
        p.save()
        p.setOpacity(1 - sortie)
        p.translate(cx, cy)
        p.scale(1 - sortie * 0.08, 1 - sortie * 0.08)
        p.translate(-cx, -cy)
        self.panneau(p, 1.0)
        a0 = entre(t, 0, 0.6)
        lab_y = cy - 170 * u + (1 - entre(t, 0, 0.6, SORTIE)) * 20 * u
        self.texte(p, cx, lab_y, (self.a.get("titre") or "").upper(), self.police(False, 34 * u, 600), self.C["doux"], "centre",
                   espacement=6 * u, opacite=a0)
        v = float(self.a.get("valeur") if self.a.get("valeur") is not None else sum(x for _l, x in self.donnees))
        n = v * entre(t, 0.3, 2.6, DOUCE)
        grand = self.police(True, 260 * u * (0.8 if self.vertical else 1.0), 700)
        path = self.chemin_chiffres(M.nombre_texte(self.a, round(n, self.a.get("decimales") or 0)), grand, cx, cy + 90 * u)
        self.lueur_chemin(p, path, "accent", self.lueur * entre(t, 0.3, 1.2))
        r = path.boundingRect()
        g = QLinearGradient(QPointF(r.left(), r.top()), QPointF(r.right(), r.bottom()))
        g.setColorAt(0.3, self.C["texte"])
        g.setColorAt(0.7, self.C["accent"])
        g.setColorAt(1.0, self.C["accent2"])
        p.fillPath(path, g)
        badge = (self.a.get("badge") or "").strip()
        if badge:
            k = ressort(t - 2.4, self.rebond, 160)
            if k > 0.001:
                f = self.police(False, 38 * u, 600)
                from PySide6.QtGui import QFontMetricsF
                w = QFontMetricsF(f).horizontalAdvance(badge) + 60 * u
                h = 66 * u
                by = cy + 150 * u
                p.save()
                p.setOpacity(p.opacity() * min(1.0, k))
                p.translate(cx, by + h / 2)
                p.scale(k, k)
                gb = QLinearGradient(QPointF(-w / 2, 0), QPointF(w / 2, 0))
                gb.setColorAt(0, self.C["accent2"])
                gb.setColorAt(1, self.C["accent"])
                p.setPen(Qt.NoPen)
                p.setBrush(gb)
                p.drawRoundedRect(QRectF(-w / 2, -h / 2, w, h), h / 2, h / 2)
                self.texte(p, 0, 13 * u, badge, f, self.C["fond"], "centre")
                p.restore()
        self.source(p, a0)
        p.restore()

    def scene_barres(self, p, t, D, dernier=False):
        from PySide6.QtGui import QLinearGradient, QPainterPath
        from PySide6.QtCore import QPointF, QRectF, Qt
        u = self.u
        entree = entre(t, 0, 0.5, SORTIE)
        sortie = 0.0 if dernier else entre(t, D - 0.5, D, lambda x: x ** 3)
        p.save()
        p.setOpacity(entree * (1 - sortie))
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
            trace = entre(t, 0.2 + i * 0.1, 0.9 + i * 0.1, SORTIE)
            self.texte(p, x0, yy + 8 * u, M.nombre(gval), self.police(False, 22 * u, 400), self.C["doux"], opacite=trace)
            p.setPen(self.couleur("texte", 0.11))
            p.drawLine(QPointF(gauche, yy), QPointF(gauche + (self.zx + self.zw - gauche) * trace, yy))
        n = len(self.donnees)
        ecart = 46 * u * (0.6 if n > 8 else 1.0)
        larg = ((self.zx + self.zw - gauche) - ecart * (n - 1)) / n
        larg_barre = larg * (0.45 + 0.55 * self.epaisseur)
        rec = max(range(n), key=lambda i: self.donnees[i][1])
        for i, (lib, val) in enumerate(self.donnees):
            k = ressort(t - 0.6 - i * self.decalage, self.rebond, 90)
            bx = gauche + i * (larg + ecart) + (larg - larg_barre) / 2
            h = (val / vmax) * H * k
            record = i == rec
            halo = entre(t, 2.6, 3.2) if record else 0.0
            r = QRectF(bx, bas - h, larg_barre, max(0.0, h))
            if h > 0.5:
                g = QLinearGradient(QPointF(0, r.top()), QPointF(0, r.bottom()))
                if record:
                    g.setColorAt(0, self.C["accent2"])
                    g.setColorAt(1, self.C["accent"])
                else:
                    g.setColorAt(0, self.couleur("accent", 0.8))
                    g.setColorAt(1, self.couleur("accent", 0.27))
                path = QPainterPath()
                rr = min(18 * u, larg_barre / 2, h)
                path.addRoundedRect(r, rr, rr)
                if record and halo > 0 and self.lueur > 0:
                    self.lueur_chemin(p, path, "accent2", halo * self.lueur)
                p.fillPath(path, g)
            self.texte(p, bx + larg_barre / 2, bas - h - 12 * u, M.nombre_texte(self.a, val * min(1.0, k)),
                       self.police(True, 32 * u * (0.8 if n > 8 else 1.0), 700),
                       self.C["accent2"] if record else self.C["texte"], "centre", opacite=min(1.0, k))
            self.texte(p, bx + larg_barre / 2, bas + 38 * u, lib, self.police(False, 26 * u * (0.8 if n > 8 else 1.0), 400),
                       self.C["doux"], "centre")
        self.source(p, 1.0)
        p.restore()

    def scene_courbe(self, p, t, D, dernier=True):
        from PySide6.QtGui import QLinearGradient, QPainterPath, QPen, QColor
        from PySide6.QtCore import QPointF, QRectF, Qt
        u = self.u
        entree = entre(t, 0, 0.5, SORTIE)
        sortie = 0.0 if dernier else entre(t, D - 0.5, D, lambda x: x ** 3)
        p.save()
        p.setOpacity(entree * (1 - sortie))
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
        prog = entre(t, 0.4, 2.8, ALLER_RETOUR)
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
            if k >= i - 1e-6:
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
        r = ressort(t - 2.8, self.rebond, 140)
        if r > 0.001:
            q = pts[rec]
            w, h = 300 * u, 96 * u
            x = min(max(self.zx, q.x() - w - 40 * u), self.zx + self.zw - w)
            y = max(y0 + 130 * u, q.y() - 60 * u - h + (1 - min(1.0, r)) * 30 * u)
            p.save()
            p.setOpacity(p.opacity() * min(1.0, r))
            p.setPen(QPen(QColor(255, 255, 255, 48), 1.5 * u))
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawRoundedRect(QRectF(x, y, w, h), 20 * u, 20 * u)
            self.texte(p, x + 28 * u, y + 40 * u, _("Record"), self.police(False, 24 * u, 400), self.C["doux"])
            self.texte(p, x + 28 * u, y + 78 * u, M.nombre_texte(self.a, self.donnees[rec][1]), self.police(True, 38 * u, 700),
                       self.C["texte"])
            p.restore()
        self.source(p, 1.0)
        p.restore()

    def scene_titre(self, p, t, D, dernier=True):
        from PySide6.QtGui import QFontMetricsF
        from PySide6.QtCore import QRectF, Qt
        u = self.u
        sortie = 0.0 if not dernier else entre(t, D - 0.6, D, lambda x: x ** 3)
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
                r = ressort(t - 0.15 - k * self.decalage, self.rebond, 150)
                op = min(1.0, max(0.0, r))
                p.save()
                p.translate(0, (1 - min(1.0, r)) * 60 * u)
                self.texte(p, x, y, m, f, self.C["accent"] if m == cle_mot else self.C["texte"], opacite=op)
                p.restore()
                x += fm.horizontalAdvance(m + " ")
                k += 1
            y += hl
        trait = entre(t, 0.4 + k * self.decalage * 0.5, 1.2 + k * self.decalage * 0.5, SORTIE)
        lt = self.zw * 0.22 * trait
        p.setPen(Qt.NoPen)
        p.setBrush(self.C["accent2"])
        p.drawRoundedRect(QRectF(self.zx + self.zw / 2 - lt / 2, y - hl * 0.55, lt, 8 * u * (0.5 + self.epaisseur)), 4 * u, 4 * u)
        st = self.a.get("sous_titre") or ""
        if st:
            self.texte(p, self.zx + self.zw / 2, y + 10 * u, st, self.police(False, 40 * u, 400), self.C["doux"], "centre",
                       opacite=entre(t, 0.8, 1.4))
        p.restore()

    # -------------------------------------------------- une image
    def dessiner(self, p, t):
        """L'image à l'instant t (en secondes du film)."""
        tt = t * self.vitesse
        D = self.D * self.vitesse
        self.fond(p, t)
        g = self.a.get("genre")
        if g == "compteur":
            self.scene_compteur(p, tt, D, dernier=True)
        elif g == "barres":
            self.scene_barres(p, tt, D, dernier=True)
        elif g == "courbe":
            self.scene_courbe(p, tt, D)
        elif g == "titre":
            self.scene_titre(p, tt, D)
        else:                                          # chiffres : les trois à la suite (proportions de l'étalon : 4,3 + 5,4 + le reste)
            d1, d2 = D * 4.3 / 14, D * 5.4 / 14
            t2, t3 = D * 4.0 / 14, D * 9.2 / 14
            if tt < d1:
                self.scene_compteur(p, tt, d1)
            if t2 <= tt < t2 + d2:
                self.scene_barres(p, tt - t2, d2)
            if tt >= t3:
                self.scene_courbe(p, tt - t3, D - t3)
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
