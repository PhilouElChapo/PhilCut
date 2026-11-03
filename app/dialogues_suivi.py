"""Désigner la personne (ou l'objet) à suivre : l'image du plan, les personnes trouvées numérotées ; un clic en choisit
une, ou l'on trace un cadre à la souris autour de n'importe quoi (un avion, une voiture)."""
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox, QDialogButtonBox, QWidget, QFormLayout,
                               QSizePolicy)

from . import suivi
from .langue import _
from .widgets import boutons_fr


class _Image(QWidget):
    choisi = Signal()

    def __init__(self, img_bgr, boites):
        super().__init__()
        h, w = img_bgr.shape[:2]
        rgb = img_bgr[:, :, ::-1].copy()
        self.qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        self.boites = boites
        self.choix = 0 if boites else None
        self.trace = None             # cadre tracé à la souris (normalisé)
        self._depart = None
        self.setMinimumSize(360, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.CrossCursor)

    def _zone(self):
        r = self.rect()
        iw, ih = self.qimg.width(), self.qimg.height()
        e = min(r.width() / iw, r.height() / ih)
        w, h = iw * e, ih * e
        return QRectF((r.width() - w) / 2, (r.height() - h) / 2, w, h)

    def _norm(self, p):
        z = self._zone()
        return (min(1, max(0, (p.x() - z.x()) / z.width())), min(1, max(0, (p.y() - z.y()) / z.height())))

    def boite(self):
        if self.trace and self.trace[2] > 0.01 and self.trace[3] > 0.01:
            return self.trace
        if self.choix is not None and self.choix < len(self.boites):
            return self.boites[self.choix][:4]
        return None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        z = self._zone()
        p.drawImage(z, self.qimg)
        f = QFont()
        f.setBold(True)
        f.setPointSize(11)
        p.setFont(f)

        def dessiner(b, coul, texte=""):
            r = QRectF(z.x() + b[0] * z.width(), z.y() + b[1] * z.height(), b[2] * z.width(), b[3] * z.height())
            p.setPen(QPen(QColor(coul), 3))
            p.setBrush(Qt.NoBrush)
            p.drawRect(r)
            if texte:
                p.fillRect(QRectF(r.x(), r.y() - 22, 26, 22), QColor(coul))
                p.setPen(QColor("#000"))
                p.drawText(QRectF(r.x(), r.y() - 22, 26, 22), Qt.AlignCenter, texte)
        for i, b in enumerate(self.boites):
            actif = self.trace is None and i == self.choix
            dessiner(b, "#7cf28a" if actif else "#ffd24a", str(i + 1))
        if self.trace:
            dessiner(self.trace, "#7cf28a")

    def mousePressEvent(self, e):
        self._depart = self._norm(e.position())
        self.trace = None

    def mouseMoveEvent(self, e):
        if self._depart:
            a, b = self._depart, self._norm(e.position())
            self.trace = (min(a[0], b[0]), min(a[1], b[1]), abs(a[0] - b[0]), abs(a[1] - b[1]))
            self.update()

    def mouseReleaseEvent(self, e):
        a, b = self._depart or (0, 0), self._norm(e.position())
        self._depart = None
        if abs(a[0] - b[0]) < 0.01 and abs(a[1] - b[1]) < 0.01:      # simple clic : la personne sous la souris
            self.trace = None
            dedans = [i for i, bo in enumerate(self.boites) if bo[0] <= b[0] <= bo[0] + bo[2] and bo[1] <= b[1] <= bo[1] + bo[3]]
            if dedans:
                self.choix = min(dedans, key=lambda i: self.boites[i][2] * self.boites[i][3])
        self.update()
        self.choisi.emit()


class DialogueSuivi(QDialog):
    def __init__(self, parent, media, t_source, recadrage=True, cadre=None):
        super().__init__(parent)
        self.setWindowTitle(_("Suivre une personne") if recadrage else _("Accrocher à une personne"))
        self.resize(820, 640)
        v = QVBoxLayout(self)
        try:
            img = suivi.image_a(media.get("proxy") or media["chemin"], t_source, largeur=960)
            boites = suivi.detecter(img)
        except suivi.ErreurSuivi as e:
            img, boites = None, []
            v.addWidget(QLabel(_("Image illisible : {e}", e=e)))
        n = len(boites)
        aide = (_("{n} personne(s) trouvée(s) : cliquez sur celle à suivre.", n=n) if n else _("Aucune personne trouvée automatiquement.")) + " " + \
            _("Ou tracez un cadre à la souris autour de ce que vous voulez suivre (un avion, une voiture…).")
        lab = QLabel(aide)
        lab.setWordWrap(True)
        v.addWidget(lab)
        self.image = _Image(img, boites) if img is not None else None
        if self.image is not None:
            if cadre and cadre.get("boite"):
                self.image.trace = tuple(cadre["boite"])
            v.addWidget(self.image, 1)
        f = QFormLayout()
        self.zoom = QDoubleSpinBox()
        self.zoom.setRange(1.0, 3.0)
        self.zoom.setSingleStep(0.1)
        self.zoom.setValue(float((cadre or {}).get("zoom", 1.0)))
        self.zoom.setToolTip(_("1,0 = le plus large possible au format du projet ; plus haut = plus serré sur la personne."))
        if recadrage:
            f.addRow(_("Zoom"), self.zoom)
        self.lissage = QComboBox()
        for k, lib in (("doux", _("Doux (cinéma)")), ("normal", _("Normal")), ("reactif", _("Réactif (mouvements rapides)"))):
            self.lissage.addItem(lib, k)
        self.lissage.setCurrentIndex(max(0, self.lissage.findData((cadre or {}).get("lissage", "normal"))))
        f.addRow(_("Mouvement du cadre") if recadrage else _("Mouvement"), self.lissage)
        v.addLayout(f)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self._valider)
        bb.rejected.connect(self.reject)
        self.ok = bb.button(QDialogButtonBox.Ok)
        self.ok.setEnabled(bool(self.image and self.image.boite()))
        if self.image is not None:
            self.image.choisi.connect(lambda: self.ok.setEnabled(bool(self.image.boite())))
        v.addWidget(bb)

    def _valider(self):
        if self.image and self.image.boite():
            self.accept()

    def resultat(self):
        return tuple(self.image.boite()), self.zoom.value(), self.lissage.currentData()
