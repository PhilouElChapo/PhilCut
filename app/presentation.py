"""Présentation de photos animée (0.9.27) : une série d'images fixes devient un clip vidéo animé, dessiné image par
image sur ce poste (QPainter) puis encodé par FFmpeg. Huit animations :
  - cartes : les photos sont lancées comme des cartes sur une table et s'empilent ;
  - explosion : la photo éclate en morceaux (les particules sont des fragments de la photo), la suivante se reforme ;
  - puzzle : les pièces de chaque photo tombent et s'assemblent ;
  - pile : une pile de photos, celle du dessus s'envole d'un geste ;
  - mur : un mur de toutes les photos, la caméra plonge sur chacune puis recule ;
  - carrousel : les photos tournent sur un manège en 3D, celle de devant s'éclaire ;
  - eventail : les photos s'ouvrent en éventail comme une main de cartes, puis viennent une à une ;
  - corde : des polaroïds suspendus à une corde par des pinces, qui se balancent, la caméra longe la corde.
Les variantes (fond, durée, nombre de fragments…) peuvent arriver par le catalogue en ligne sans réinstaller.
"""
import math
import os
import random
import subprocess

from .langue import _

STYLES = {
    "cartes": (_("Lancer de cartes"), _("Chaque photo arrive en tournoyant comme une carte lancée sur la table et s'empile sur les autres.")),
    "explosion": (_("Explosion de particules"), _("La photo éclate en dizaines de fragments qui s'envolent ; les fragments de la suivante "
                                                  "convergent et la reforment.")),
    "puzzle": (_("Puzzle qui s'assemble"), _("Les pièces de chaque photo tombent une à une et s'emboîtent avec un petit rebond.")),
    "pile": (_("Pile de photos"), _("Une pile de tirages ; celle du dessus s'envole d'un geste et découvre la suivante.")),
    "mur": (_("Mur de photos"), _("Toutes les photos en mosaïque ; la caméra plonge sur chacune, puis recule pour montrer le mur.")),
    "carrousel": (_("Carrousel 3D"), _("Les photos tournent sur un manège en perspective ; celle de devant s'éclaire et s'agrandit.")),
    "eventail": (_("Éventail"), _("Les photos s'ouvrent en éventail comme une main de cartes, puis chacune vient au premier plan.")),
    "corde": (_("Polaroïds sur une corde"), _("Des polaroïds suspendus par des pinces se balancent ; la caméra longe la corde.")),
}
VARIANTES = {}             # id -> {nom, desc, style, fond, options, duree_image} : variantes venues du catalogue en ligne
FONDS = {"flou": _("La photo floutée"), "sombre": _("Sombre"), "table": _("Table en bois"), "clair": _("Clair")}


def _lisse(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _sortie_douce(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _rebond(x):
    x = max(0.0, min(1.0, x))
    if x < 0.7:
        return (x / 0.7) ** 2
    y = (x - 0.7) / 0.3
    return 1 - 0.12 * math.sin(y * math.pi)


def trier_par_date(chemins):
    """Ordre de prise de vue (EXIF), sinon date du fichier."""
    def cle(c):
        try:
            from PIL import Image
            with Image.open(c) as im:
                d = (im.getexif().get_ifd(0x8769) or {}).get(36867) or im.getexif().get(306)
                if d:
                    return str(d)
        except Exception:     # noqa: BLE001
            pass
        try:
            import datetime
            return datetime.datetime.fromtimestamp(os.path.getmtime(c)).strftime("%Y:%m:%d %H:%M:%S")
        except OSError:
            return ""
    return sorted(chemins, key=cle)


def duree_totale(n, style, duree_image):
    n = max(1, n)
    d = float(duree_image)
    return {"cartes": n * d + 1.2, "explosion": n * d + 0.9, "mur": 1.2 + n * d + 1.4, "eventail": 1.2 + n * d + 0.6}.get(style, n * d)


class _Rendu:
    def __init__(self, chemins, style, duree_image, L, H, fond, graine, options):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage, QImageReader
        self.style, self.d, self.L, self.H, self.fond = style, float(duree_image), L, H, fond
        self.options = options or {}
        self.rnd = random.Random(graine)
        self.photos, self.couvre, self.flous = [], [], []
        carte_h = int(H * (0.62 if style not in ("mur", "carrousel") else 0.5))
        for c in chemins:
            r = QImageReader(c)
            r.setAutoTransform(True)
            img = r.read()
            if img.isNull():
                continue
            img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
            self.photos.append(img.scaled(int(carte_h * 1.6), carte_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            if style in ("explosion", "puzzle", "mur"):
                self.couvre.append(self._couvrir(img))
            petit = img.scaled(48, 27, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.flous.append(petit.scaled(L, H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        if not self.photos:
            raise ValueError(_("Aucune image lisible."))
        self.n = len(self.photos)
        self.T = duree_totale(self.n, style, self.d)
        self.fragments = int(self.options.get("fragments", 14 if style == "explosion" else 6))
        self._preparer()

    def _couvrir(self, img):
        from PySide6.QtCore import Qt
        g = img.scaled(self.L, self.H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return g.copy((g.width() - self.L) // 2, (g.height() - self.H) // 2, self.L, self.H)

    def _preparer(self):
        R = self.rnd
        L, H = self.L, self.H
        self.lancers = []
        for _i in range(self.n):
            cote = R.choice(("g", "d", "b", "h"))
            depart = {"g": (-0.4 * L, R.uniform(0.2, 0.8) * H), "d": (1.4 * L, R.uniform(0.2, 0.8) * H),
                      "b": (R.uniform(0.2, 0.8) * L, 1.5 * H), "h": (R.uniform(0.2, 0.8) * L, -0.5 * H)}[cote]
            self.lancers.append({"depart": depart, "arrivee": (L / 2 + R.uniform(-0.07, 0.07) * L, H / 2 + R.uniform(-0.06, 0.06) * H),
                                 "rot0": R.uniform(-260, 260), "rot1": R.uniform(-11, 11)})
        nx = self.fragments
        ny = max(2, round(nx * H / L))
        self.grille = (nx, ny)
        self.eclats = []
        for _i in range(self.n):
            e = []
            for gx in range(nx):
                for gy in range(ny):
                    cx, cy = (gx + 0.5) / nx * L, (gy + 0.5) / ny * H
                    a = math.atan2(cy - H / 2, cx - L / 2) + R.uniform(-0.6, 0.6)
                    v = R.uniform(0.5, 1.3) * max(L, H)
                    e.append({"g": (gx, gy), "dir": (math.cos(a) * v, math.sin(a) * v), "rot": R.uniform(-540, 540),
                              "venue": (R.uniform(-0.3, 1.3) * L, R.uniform(-0.3, 1.3) * H), "rotv": R.uniform(-360, 360),
                              "delai": R.uniform(0, 0.35), "ordre": R.random()})
            self.eclats.append(e)
        self.pile = [(R.uniform(-0.02, 0.02) * L, R.uniform(-0.02, 0.02) * H, R.uniform(-7, 7)) for _i in range(self.n)]
        self.sorties = [R.choice((-1, 1)) for _i in range(self.n)]
        self.balance = [(R.uniform(0.8, 1.4), R.uniform(0, 6.28)) for _i in range(self.n)]

    # ---- dessin commun
    def _fond(self, p, t):
        from PySide6.QtGui import QColor, QLinearGradient
        L, H = self.L, self.H
        if self.fond == "flou":
            i = min(self.n - 1, int(t / self.d)) if self.style not in ("mur", "eventail") else min(self.n - 1, max(0, int((t - 1.2) / self.d)))
            p.drawImage(0, 0, self.flous[i])
            p.fillRect(0, 0, L, H, QColor(0, 0, 0, 120))
            return
        g = QLinearGradient(0, 0, 0, H)
        if self.fond == "table":
            g.setColorAt(0, QColor("#7a4a26"))
            g.setColorAt(1, QColor("#4a2b14"))
        elif self.fond == "clair":
            g.setColorAt(0, QColor("#f4f1ea"))
            g.setColorAt(1, QColor("#d9d3c7"))
        else:
            g.setColorAt(0, QColor("#22252b"))
            g.setColorAt(1, QColor("#0d0f12"))
        p.fillRect(0, 0, L, H, g)
        if self.fond == "table":                          # veinage du bois
            from PySide6.QtGui import QPen
            p.setPen(QPen(QColor(0, 0, 0, 28), max(1, H // 360)))
            for k in range(14):
                y = H * k / 14 + 6 * math.sin(k * 1.7)
                p.drawLine(0, int(y), L, int(y + 10 * math.sin(k)))

    def _carte(self, p, img, cx, cy, echelle, rot, opacite=1.0, hauteur=0.0, polaroid=False, lumiere=1.0):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QColor
        w, h = img.width() * echelle, img.height() * echelle
        b = max(4.0, 0.045 * min(w, h))
        bas = b * (3.2 if polaroid else 1)
        p.save()
        p.setOpacity(max(0.0, min(1.0, opacite)))
        p.translate(cx, cy)
        p.rotate(rot)
        dec = 6 + 40 * hauteur
        p.fillRect(QRectF(-w / 2 - b + dec * 0.6, -h / 2 - b + dec, w + 2 * b, h + b + bas), QColor(0, 0, 0, int(70 - 30 * hauteur)))
        p.fillRect(QRectF(-w / 2 - b, -h / 2 - b, w + 2 * b, h + b + bas), QColor("#fbfaf7"))
        p.drawImage(QRectF(-w / 2, -h / 2, w, h), img)
        if lumiere < 1.0:
            p.fillRect(QRectF(-w / 2 - b, -h / 2 - b, w + 2 * b, h + b + bas), QColor(0, 0, 0, int(255 * (1 - lumiere))))
        p.restore()
        return h / 2 + bas

    def _fragment(self, p, img, gx, gy, x, y, rot, s, opacite):
        from PySide6.QtCore import QRectF
        nx, ny = self.grille
        fw, fh = self.L / nx, self.H / ny
        p.save()
        p.setOpacity(max(0.0, min(1.0, opacite)))
        p.translate(x, y)
        p.rotate(rot)
        p.scale(s, s)
        p.drawImage(QRectF(-fw / 2 - 0.5, -fh / 2 - 0.5, fw + 1, fh + 1), img, QRectF(gx * fw, gy * fh, fw, fh))
        p.restore()

    # ---- les animations
    def dessiner(self, p, t):
        self._fond(p, t)
        getattr(self, "_" + self.style)(p, t)

    def _cartes(self, p, t):
        vol = 0.65
        for i in range(self.n):
            s = i * self.d
            if t < s:
                break
            u = _sortie_douce((t - s) / vol)
            L0 = self.lancers[i]
            (x0, y0), (x1, y1) = L0["depart"], L0["arrivee"]
            x = x0 + (x1 - x0) * u
            y = y0 + (y1 - y0) * u - math.sin(u * math.pi) * 0.12 * self.H
            rot = L0["rot0"] + (L0["rot1"] - L0["rot0"]) * u
            ech = 1.25 - 0.25 * u
            vieux = (t - s) / self.d
            op = 1.0 if i >= self.n - 1 or vieux < 5 else max(0.0, 1 - (vieux - 5))       # les plus anciennes s'effacent
            self._carte(p, self.photos[i], x, y, ech, rot, op, hauteur=1 - u)

    def _explosion(self, p, t):
        entree = 0.9
        if t < entree:                                     # la première se forme
            self._former(p, 0, t / entree)
            return
        t2 = t - entree
        i = min(self.n - 1, int(t2 / self.d))
        u = t2 - i * self.d
        tr = min(1.0, self.d * 0.45)
        if i < self.n - 1 and u > self.d - tr:
            k = (u - (self.d - tr)) / tr
            self._former(p, i + 1, k)
            self._eclater(p, i, k)
        else:
            p.drawImage(0, 0, self.couvre[i])

    def _eclater(self, p, i, k):
        nx, ny = self.grille
        fw, fh = self.L / nx, self.H / ny
        for e in self.eclats[i]:
            u = max(0.0, (k - e["delai"] * 0.5) / (1 - e["delai"] * 0.5))
            if u <= 0:
                gx, gy = e["g"]
                self._fragment(p, self.couvre[i], gx, gy, (gx + 0.5) * fw, (gy + 0.5) * fh, 0, 1, 1)
                continue
            gx, gy = e["g"]
            v = u * u
            self._fragment(p, self.couvre[i], gx, gy, (gx + 0.5) * fw + e["dir"][0] * v, (gy + 0.5) * fh + e["dir"][1] * v + 0.4 * self.H * v * v,
                           e["rot"] * v, 1 - 0.6 * u, 1 - u)

    def _former(self, p, i, k):
        nx, ny = self.grille
        fw, fh = self.L / nx, self.H / ny
        for e in self.eclats[i]:
            u = _sortie_douce((k - e["delai"]) / (1 - e["delai"]) if k > e["delai"] else 0)
            if u <= 0:
                continue
            gx, gy = e["g"]
            x1, y1 = (gx + 0.5) * fw, (gy + 0.5) * fh
            x0, y0 = e["venue"]
            self._fragment(p, self.couvre[i], gx, gy, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, e["rotv"] * (1 - u), 0.4 + 0.6 * u, min(1, u * 2))

    def _puzzle(self, p, t):
        i = min(self.n - 1, int(t / self.d))
        if i > 0:
            p.drawImage(0, 0, self.couvre[i - 1])
        u = t - i * self.d
        pose = min(1.4, self.d * 0.6)
        nx, ny = self.grille
        fw, fh = self.L / nx, self.H / ny
        ordre = sorted(self.eclats[i], key=lambda e: e["ordre"])
        for r, e in enumerate(ordre):
            s = r / len(ordre) * pose * 0.75
            k = (u - s) / (pose * 0.35)
            if k <= 0:
                continue
            gx, gy = e["g"]
            y1 = (gy + 0.5) * fh
            y = -fh + (y1 + fh) * _rebond(k)
            self._fragment(p, self.couvre[i], gx, gy, (gx + 0.5) * fw, y, (1 - min(1, k)) * 20, 1, 1)

    def _pile(self, p, t):
        i = min(self.n - 1, int(t / self.d))
        u = t - i * self.d
        geste = 0.55
        for j in range(self.n - 1, i - 1, -1):                    # du dessous vers le dessus
            dx, dy, r = self.pile[j]
            x, y, rot, op = self.L / 2 + dx, self.H / 2 + dy, r, 1.0
            if j == i and i < self.n - 1 and u > self.d - geste:
                k = _lisse((u - (self.d - geste)) / geste)
                sens = self.sorties[i]
                x += sens * k * self.L * 0.9
                y -= math.sin(k * math.pi) * 0.1 * self.H
                rot += sens * 28 * k
                op = 1 - k * 0.3
            self._carte(p, self.photos[j], x, y, 1.0, rot, op, hauteur=0.15 if j == i else 0)

    def _mur(self, p, t):
        from PySide6.QtCore import QRectF
        n = self.n
        col = max(1, math.ceil(math.sqrt(n * 16 / 9 * self.H / self.L * 1.0)))
        col = max(col, math.ceil(math.sqrt(n)))
        lig = math.ceil(n / col)
        cw, ch = self.L, self.H
        marge = 0.04
        mur_w, mur_h = col * cw, lig * ch

        def centre(k):
            return ((k % col) + 0.5) * cw, ((k // col) + 0.5) * ch
        loin = min(self.L / mur_w, self.H / mur_h) * 0.92
        vue_loin = (mur_w / 2, mur_h / 2, loin)
        if t < 1.2:
            a, b, k = vue_loin, (*centre(0), 0.82), _lisse(t / 1.2)
        elif t < 1.2 + n * self.d:
            i = int((t - 1.2) / self.d)
            u = t - 1.2 - i * self.d
            k = _lisse(u / 0.8)
            a = (*centre(i - 1), 0.82) if i > 0 else (*centre(0), 0.82)
            b = (*centre(i), 0.82)
            if i > 0:                                              # on recule un peu pendant le trajet
                mid = 0.45
                z = 0.82 - (0.82 - mid) * math.sin(k * math.pi)
                x = a[0] + (b[0] - a[0]) * k
                y = a[1] + (b[1] - a[1]) * k
                a = b = (x, y, z)
                k = 1
        else:
            a, b, k = (*centre(n - 1), 0.82), vue_loin, _lisse((t - 1.2 - n * self.d) / 1.4)
        x = a[0] + (b[0] - a[0]) * k
        y = a[1] + (b[1] - a[1]) * k
        z = a[2] + (b[2] - a[2]) * k
        p.save()
        p.translate(self.L / 2, self.H / 2)
        p.scale(z, z)
        p.translate(-x, -y)
        for j in range(n):
            cx, cy = centre(j)
            r = QRectF(cx - cw / 2 + cw * marge / 2, cy - ch / 2 + ch * marge / 2, cw * (1 - marge), ch * (1 - marge))
            p.drawImage(r, self.couvre[j])
        p.restore()

    def _carrousel(self, p, t):
        n = self.n
        pas = 2 * math.pi / max(n, 3)
        i = t / self.d
        base = int(i)
        u = i - base
        k = _lisse(max(0.0, (u - 0.7) / 0.3))                   # on reste devant 70 % du temps, puis on tourne
        angle = -(min(base, n - 1) + (k if base < n - 1 else 0)) * pas
        R = self.L * 0.36
        cartes = []
        for j in range(n):
            a = j * pas + angle
            z = math.cos(a)
            cartes.append((z, j, math.sin(a)))
        for z, j, s in sorted(cartes):
            ech = 0.42 + 0.48 * (z + 1) / 2
            self._carte(p, self.photos[j], self.L / 2 + s * R, self.H / 2 - z * 0.04 * self.H, ech, s * -8, 1.0,
                        hauteur=0.2 * (z + 1) / 2, lumiere=0.45 + 0.55 * (z + 1) / 2)

    def _eventail(self, p, t):
        n = self.n
        ouv = _sortie_douce(t / 1.2)
        etendue = min(110.0, 16.0 * n)
        pivot_y = self.H * 1.05
        actif, k_actif = -1, 0.0
        if t >= 1.2:
            actif = min(n - 1, int((t - 1.2) / self.d))
            u = t - 1.2 - actif * self.d
            k_actif = _lisse(u / 0.45) * (1 - _lisse((u - (self.d - 0.45)) / 0.45)) if actif < n else 0
        for j in range(n):
            if j == actif:
                continue
            a = (-etendue / 2 + etendue * j / max(1, n - 1)) * ouv if n > 1 else 0
            self._eventail_carte(p, j, a, pivot_y, 0.62, 1.0)
        if actif >= 0:
            a = (-etendue / 2 + etendue * actif / max(1, n - 1)) if n > 1 else 0
            ra = math.radians(a * (1 - k_actif))
            dist = self.H * 0.75 * (1 - k_actif)
            x = self.L / 2 + math.sin(ra) * dist
            y = pivot_y - math.cos(ra) * dist - k_actif * (pivot_y - self.H / 2) * 1.0 + (1 - k_actif) * 0
            if k_actif > 0.0:
                y = (pivot_y - math.cos(ra) * self.H * 0.75) * (1 - k_actif) + (self.H / 2) * k_actif
            self._carte(p, self.photos[actif], x, y, 0.62 + 0.4 * k_actif, a * (1 - k_actif), 1.0, hauteur=k_actif)

    def _eventail_carte(self, p, j, a, pivot_y, ech, op):
        ra = math.radians(a)
        dist = self.H * 0.75
        x = self.L / 2 + math.sin(ra) * dist
        y = pivot_y - math.cos(ra) * dist
        self._carte(p, self.photos[j], x, y, ech, a, op, hauteur=0.05)

    def _corde(self, p, t):
        from PySide6.QtCore import QPointF, QRectF
        from PySide6.QtGui import QColor, QPainterPath, QPen
        n = self.n
        ecart = self.L * 0.55
        pos = t / self.d - 0.5
        cam = max(0.0, min(n - 1, pos)) * ecart
        x0 = self.L / 2 - cam
        y_corde = self.H * 0.14
        p.setPen(QPen(QColor("#d8c7a8"), max(2, self.H // 270)))
        chemin = QPainterPath(QPointF(x0 - ecart, y_corde))
        for j in range(n + 1):
            xa, xb = x0 + (j - 1) * ecart, x0 + j * ecart
            chemin.quadTo(QPointF((xa + xb) / 2, y_corde + self.H * 0.04), QPointF(xb, y_corde))
        p.drawPath(chemin)
        for j in range(n):
            x = x0 + j * ecart
            if x < -ecart or x > self.L + ecart:
                continue
            f, ph = self.balance[j]
            ang = math.sin(t * f + ph) * 5
            img = self.photos[j]
            ech = 0.82
            h = img.height() * ech
            p.save()
            p.translate(x, y_corde)
            p.rotate(ang)
            self._carte(p, img, 0, h / 2 + self.H * 0.03, ech, 0, 1.0, hauteur=0.1, polaroid=True)
            p.fillRect(QRectF(-self.H * 0.008, -self.H * 0.02, self.H * 0.016, self.H * 0.06), QColor("#c49a6c"))
            p.restore()


def fabriquer(chemins, sortie, style="cartes", duree_image=2.5, taille=(1920, 1080), cadence=30, fond="flou", graine=7, options=None,
              progression=None, arret=lambda: False):
    """Dessine la présentation image par image et l'encode en MP4 (H.264) ; renvoie le chemin."""
    from PySide6.QtGui import QImage, QPainter
    from . import moteur
    L, H = int(taille[0]) // 2 * 2, int(taille[1]) // 2 * 2
    rd = _Rendu(chemins, style if style in STYLES else "cartes", duree_image, L, H, fond, graine, options)
    nb = max(1, int(round(rd.T * cadence)))
    cmd = [moteur.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{L}x{H}",
           "-r", str(cadence), "-i", "pipe:0", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", sortie]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **moteur._sans_console())
    img = QImage(L, H, QImage.Format_ARGB32)
    try:
        for k in range(nb):
            if arret():
                raise InterruptedError()
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
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


def apercu_image(chemins, style, t, taille=(640, 360), fond="flou", duree_image=2.5):
    """Une image de l'animation à l'instant t (vignettes de la fenêtre, tests)."""
    from PySide6.QtGui import QImage, QPainter
    rd = _Rendu(chemins, style, duree_image, taille[0], taille[1], fond, 7, None)
    img = QImage(taille[0], taille[1], QImage.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    rd.dessiner(p, t)
    p.end()
    return img
