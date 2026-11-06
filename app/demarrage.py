"""Ecran de lancement : logo, version, ce que PhilCut est en train de faire et barre de progression, affiché dès le
démarrage jusqu'à l'ouverture de la fenêtre (comme PhilPDF)."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QApplication, QWidget


class EcranDemarrage(QWidget):
    def __init__(self, version):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.version = version
        self.texte = ""
        self.fraction = 0.0
        self.resize(560, 320)
        ecran = QApplication.primaryScreen()
        if ecran:
            g = ecran.availableGeometry()
            self.move(g.center().x() - self.width() // 2, g.center().y() - self.height() // 2)
        try:
            from .icones import logo
            self.logo = logo(112).pixmap(112, 112)
        except Exception:    # noqa: BLE001
            self.logo = None

    def etape(self, texte, fraction):
        """Affiche l'étape en cours (texte) et la progression (0 à 1), puis laisse Qt redessiner tout de suite."""
        self.texte = texte
        self.fraction = max(self.fraction, min(1.0, float(fraction)))
        if not self.isVisible():
            self.show()
        self.repaint()
        QApplication.processEvents()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        fond = QLinearGradient(0, 0, r.width(), r.height())
        fond.setColorAt(0, QColor("#1d1630"))
        fond.setColorAt(1, QColor("#0e0e14"))
        chemin = QPainterPath()
        chemin.addRoundedRect(r, 18, 18)
        p.fillPath(chemin, QBrush(fond))
        p.setPen(QPen(QColor(155, 123, 255, 90), 1.2))
        p.drawPath(chemin)
        if self.logo:
            p.drawPixmap(40, 60, self.logo)
        p.setPen(QColor("#ffffff"))
        f = QFont("Poppins")
        f.setPixelSize(46)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(176, 58, 360, 60), Qt.AlignLeft | Qt.AlignVCenter, "PhilCut")
        f.setPixelSize(15)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor("#b9b2d6"))
        try:
            from .langue import _
            sous = _("Montage vidéo simple, efficace, effet wahou.")
            ver = _("Version {v}", v=self.version)
        except Exception:    # noqa: BLE001
            sous, ver = "", self.version
        p.drawText(QRectF(178, 118, 360, 24), Qt.AlignLeft | Qt.AlignVCenter, sous)
        p.setPen(QColor("#8d86a8"))
        p.drawText(QRectF(178, 142, 360, 22), Qt.AlignLeft | Qt.AlignVCenter, ver)
        # étape en cours et barre de progression
        f.setPixelSize(14)
        p.setFont(f)
        p.setPen(QColor("#e6e2f5"))
        p.drawText(QRectF(40, 222, 480, 26), Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine,
                   p.fontMetrics().elidedText(self.texte, Qt.ElideRight, 480))
        barre = QRectF(40, 256, 480, 8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(barre, 4, 4)
        if self.fraction > 0:
            g = QLinearGradient(barre.left(), 0, barre.right(), 0)
            g.setColorAt(0, QColor("#6d3fc6"))
            g.setColorAt(1, QColor("#b39aff"))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(barre.left(), barre.top(), max(8.0, barre.width() * self.fraction), barre.height()), 4, 4)
        p.setPen(QColor("#8d86a8"))
        f.setPixelSize(12)
        p.setFont(f)
        p.drawText(QRectF(40, 270, 480, 22), Qt.AlignRight | Qt.AlignVCenter, f"{int(self.fraction * 100)} %")
        p.end()
