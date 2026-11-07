"""Carte OpenStreetMap interactive (0.9.18) : déplacer à la souris, zoomer à la molette, double-clic (ou clic droit)
pour poser un point. Les étapes du trajet et le trait sont dessinés par-dessus.

Tuiles OpenStreetMap (© les contributeurs d'OpenStreetMap, licence ODbL), demandées une à une avec l'identification de
PhilCut, gardées sur le disque (pas de nouveau téléchargement) et seulement pendant que la carte est affichée,
conformément aux règles d'usage des tuiles d'OpenStreetMap.
"""
import math
import os

from PySide6.QtCore import QPointF, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QWidget

from .langue import _

TUILE = 256
URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


def _dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "tuiles_osm")
    os.makedirs(d, exist_ok=True)
    return d


def vers_pixels(lat, lon, z):
    n = TUILE * (2 ** z)
    x = (lon + 180.0) / 360.0 * n
    la = math.radians(max(-85.0, min(85.0, lat)))
    y = (1.0 - math.log(math.tan(la) + 1.0 / math.cos(la)) / math.pi) / 2.0 * n
    return x, y


def vers_degres(x, y, z):
    n = TUILE * (2 ** z)
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


class CarteOSM(QWidget):
    point_demande = Signal(float, float)          # double-clic ou clic droit › « Ajouter un point ici »

    def __init__(self, parent=None, lat=43.55, lon=6.95, zoom=8):
        super().__init__(parent)
        self.lat, self.lon, self.z = lat, lon, int(zoom)
        self.etapes = []
        self._tuiles = {}
        self._en_cours = set()
        self._glisse = None
        self._reseau = None
        self.setMinimumSize(320, 300)
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.setToolTip(_("Glisser : déplacer · molette : zoomer · double-clic : poser un point ici"))

    # ---- tuiles
    def _tuile(self, x, y, z):
        cle = (z, x, y)
        if cle in self._tuiles:
            return self._tuiles[cle]
        f = os.path.join(_dossier(), f"{z}_{x}_{y}.png")
        if os.path.exists(f):
            px = QPixmap(f)
            self._tuiles[cle] = px
            return px
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or os.environ.get("PHILCUT_SANS_RESEAU"):
            return None
        if cle not in self._en_cours and len(self._en_cours) < 6:
            self._demander(cle, f)
        return None

    def _demander(self, cle, f):
        from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
        from .config import VERSION
        if self._reseau is None:
            self._reseau = QNetworkAccessManager(self)
        z, x, y = cle
        req = QNetworkRequest(QUrl(URL.format(z=z, x=x, y=y)))
        req.setRawHeader(b"User-Agent", f"PhilCut/{VERSION} (+https://github.com/PhilouElChapo/PhilCut)".encode())
        rep = self._reseau.get(req)
        self._en_cours.add(cle)

        def fini():
            self._en_cours.discard(cle)
            donnees = bytes(rep.readAll())
            rep.deleteLater()
            if donnees[:4] == b"\x89PNG":
                with open(f, "wb") as g:
                    g.write(donnees)
                px = QPixmap()
                px.loadFromData(donnees)
                self._tuiles[cle] = px
                self.update()
        rep.finished.connect(fini)

    # ---- dessin
    def centrer(self, etapes):
        """Cadre la carte sur les étapes."""
        if not etapes:
            return
        las, los = [e["lat"] for e in etapes], [e["lon"] for e in etapes]
        self.lat, self.lon = (min(las) + max(las)) / 2, (min(los) + max(los)) / 2
        for z in range(14, 2, -1):
            x0, y0 = vers_pixels(max(las), min(los), z)
            x1, y1 = vers_pixels(min(las), max(los), z)
            if x1 - x0 < self.width() * 0.8 and y1 - y0 < self.height() * 0.8:
                self.z = z
                break
        self.update()

    def _origine(self):
        cx, cy = vers_pixels(self.lat, self.lon, self.z)
        return cx - self.width() / 2, cy - self.height() / 2

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#cfd8dc"))
        ox, oy = self._origine()
        n = 2 ** self.z
        for tx in range(int(ox // TUILE), int((ox + self.width()) // TUILE) + 1):
            for ty in range(int(oy // TUILE), int((oy + self.height()) // TUILE) + 1):
                if 0 <= ty < n:
                    px = self._tuile(tx % n, ty, self.z)
                    if px is not None and not px.isNull():
                        p.drawPixmap(int(tx * TUILE - ox), int(ty * TUILE - oy), px)
        p.setRenderHint(QPainter.Antialiasing)
        pts = []
        for e in self.etapes:
            x, y = vers_pixels(e["lat"], e["lon"], self.z)
            pts.append(QPointF(x - ox, y - oy))
        if len(pts) > 1:
            p.setPen(QPen(QColor("#ff9f0a"), 4))
            for a, b in zip(pts, pts[1:]):
                p.drawLine(a, b)
        f = QFont()
        f.setPixelSize(12)
        f.setBold(True)
        p.setFont(f)
        for i, (pt, e) in enumerate(zip(pts, self.etapes)):
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.setBrush(QColor("#d62828"))
            p.drawEllipse(pt, 7, 7)
            texte = f"{i + 1}. {e.get('nom', '')}"
            w = p.fontMetrics().horizontalAdvance(texte) + 6
            x = pt.x() + 9 if pt.x() + 9 + w < self.width() else pt.x() - 9 - w      # étiquette jamais coupée par le bord
            r = QRectF(x, pt.y() - 19, w, 16)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 210))
            p.drawRoundedRect(r, 4, 4)
            p.setPen(QColor("#111111"))
            p.drawText(r, Qt.AlignCenter, texte)
        # attribution obligatoire
        f.setPixelSize(10)
        f.setBold(False)
        p.setFont(f)
        r = QRectF(self.width() - 190, self.height() - 16, 188, 14)
        p.fillRect(r, QColor(255, 255, 255, 200))
        p.setPen(QColor("#333333"))
        p.drawText(r, Qt.AlignCenter, "© OpenStreetMap contributors")
        p.end()

    # ---- souris
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._glisse = (e.position(), vers_pixels(self.lat, self.lon, self.z))

    def mouseMoveEvent(self, e):
        if self._glisse is not None:
            (p0, (cx, cy)) = self._glisse
            d = e.position() - p0
            self.lat, self.lon = vers_degres(cx - d.x(), cy - d.y(), self.z)
            self.update()

    def mouseReleaseEvent(self, _e):
        self._glisse = None

    def wheelEvent(self, e):
        ancien = self.z
        self.z = max(2, min(17, self.z + (1 if e.angleDelta().y() > 0 else -1)))
        if self.z != ancien:                          # le point sous la souris reste sous la souris
            ox, oy = self._origine_z(ancien)
            la, lo = vers_degres(ox + e.position().x(), oy + e.position().y(), ancien)
            mx, my = vers_pixels(la, lo, self.z)
            cx, cy = mx - e.position().x() + self.width() / 2, my - e.position().y() + self.height() / 2
            self.lat, self.lon = vers_degres(cx, cy, self.z)
            self.update()

    def _origine_z(self, z):
        cx, cy = vers_pixels(self.lat, self.lon, z)
        return cx - self.width() / 2, cy - self.height() / 2

    def degres_sous(self, pos):
        ox, oy = self._origine()
        return vers_degres(ox + pos.x(), oy + pos.y(), self.z)

    def mouseDoubleClickEvent(self, e):
        la, lo = self.degres_sous(e.position())
        self.point_demande.emit(la, lo)

    def _menu(self, pos):
        la, lo = self.degres_sous(QPointF(pos))
        m = QMenu(self)
        m.addAction(_("Ajouter un point ici ({a:.4f}, {o:.4f})", a=la, o=lo), lambda: self.point_demande.emit(la, lo))
        m.addAction(_("Zoomer ici"), lambda: (setattr(self, "lat", la), setattr(self, "lon", lo), setattr(self, "z", min(17, self.z + 2)),
                                              self.update()))
        m.exec(self.mapToGlobal(pos))
