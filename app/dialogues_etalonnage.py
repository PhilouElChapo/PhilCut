"""Fenêtre « Étalonnage » (0.9.28) : l'image du plan à la ligne rouge, avant / après avec un rideau que l'on fait glisser,
trois roues de couleur (ombres, tons moyens, hautes lumières), cinq curseurs, « Auto », « Accorder sur un autre plan »,
« Copier sur les autres plans ». Tout est réversible (Annuler, Ctrl+Z)."""
import math
import os
import subprocess
import tempfile

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QConicalGradient, QImage, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
                               QWidget)

from . import etalonnage as ET
from . import moteur
from .langue import _
from .projet import duree_clip


class RoueCouleur(QWidget):
    """Disque des teintes ; la pastille indique vers quelle couleur on pousse. Double-clic : retour au centre."""
    change = Signal(float, float)

    def __init__(self, titre, parent=None):
        super().__init__(parent)
        self.titre, self.x, self.y = titre, 0.0, 0.0
        self.setMinimumSize(130, 150)
        self.setToolTip(_("Glissez la pastille vers la couleur à ajouter ; plus elle est loin du centre, plus c'est fort. Double-clic : neutre."))

    def valeur(self, x, y, emettre=False):
        n = math.hypot(x, y)
        if n > 1:
            x, y = x / n, y / n
        self.x, self.y = x, y
        self.update()
        if emettre:
            self.change.emit(x, y)

    def _geo(self):
        r = min(self.width(), self.height() - 22) / 2 - 6
        return QPointF(self.width() / 2, 20 + r + 2), r

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c, r = self._geo()
        p.setPen(self.palette().windowText().color())
        p.drawText(QRectF(0, 0, self.width(), 18), Qt.AlignCenter, self.titre)
        g = QConicalGradient(c, 0)
        # angle 0 = rouge (droite), puis vert à 120°, bleu à 240° (sens trigonométrique, y vers le haut)
        for k, coul in ((0, "#ff4040"), (1 / 6, "#ffff40"), (2 / 6, "#40ff40"), (3 / 6, "#40ffff"), (4 / 6, "#4040ff"), (5 / 6, "#ff40ff"), (1, "#ff4040")):
            g.setColorAt(k, QColor(coul))
        p.setBrush(g)
        p.setPen(QPen(QColor("#2a2e35"), 2))
        p.drawEllipse(c, r, r)
        rg = QRadialGradient(c, r)
        rg.setColorAt(0, QColor(128, 128, 128, 255))
        rg.setColorAt(1, QColor(128, 128, 128, 0))
        p.setBrush(rg)
        p.setPen(Qt.NoPen)
        p.drawEllipse(c, r, r)
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.drawLine(QPointF(c.x() - 6, c.y()), QPointF(c.x() + 6, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 6), QPointF(c.x(), c.y() + 6))
        pt = QPointF(c.x() + self.x * r, c.y() - self.y * r)
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawEllipse(pt, 7, 7)
        p.end()

    def _depuis(self, pos):
        c, r = self._geo()
        self.valeur((pos.x() - c.x()) / r, -(pos.y() - c.y()) / r, True)

    def mousePressEvent(self, e):
        self._depuis(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._depuis(e.position())

    def mouseDoubleClickEvent(self, _e):
        self.valeur(0, 0, True)


class VueAvantApres(QWidget):
    """L'image ; à gauche du rideau l'original, à droite l'étalonné. On fait glisser le rideau à la souris."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.avant, self.apres, self.rideau = QImage(), QImage(), 0.5
        self.setMinimumSize(480, 270)
        self.setToolTip(_("Faites glisser le rideau : à gauche avant, à droite après"))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#111"))
        if self.apres.isNull():
            p.end()
            return
        img = self.apres
        w, h = self.width(), self.height()
        s = min(w / img.width(), h / img.height())
        cible = QRectF((w - img.width() * s) / 2, (h - img.height() * s) / 2, img.width() * s, img.height() * s)
        p.drawImage(cible, self.apres)
        if not self.avant.isNull():
            xr = cible.left() + cible.width() * self.rideau
            p.save()
            p.setClipRect(QRectF(cible.left(), cible.top(), xr - cible.left(), cible.height()))
            p.drawImage(cible, self.avant)
            p.restore()
            p.setPen(QPen(QColor("#ffd60a"), 2))
            p.drawLine(QPointF(xr, cible.top()), QPointF(xr, cible.bottom()))
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(cible.left() + 6, cible.top() + 4, 120, 18), Qt.AlignLeft, _("AVANT"))
            p.drawText(QRectF(cible.right() - 126, cible.top() + 4, 120, 18), Qt.AlignRight, _("APRÈS"))
        self._cible = cible
        p.end()

    def mousePressEvent(self, e):
        self.mouseMoveEvent(e)

    def mouseMoveEvent(self, e):
        c = getattr(self, "_cible", None)
        if c is not None and c.width() > 0:
            self.rideau = max(0.0, min(1.0, (e.position().x() - c.left()) / c.width()))
            self.update()


def image_du_plan(projet, clip, t=None, largeur=640):
    """Image du rush de ce plan (à l'instant t de la timeline, sinon au milieu du plan), largeur donnée, en QImage."""
    m = projet.media(clip["media"]) or {}
    if not m.get("chemin"):
        return QImage()
    if t is None or not (clip["debut"] <= t < clip["debut"] + duree_clip(clip)):
        t = clip["debut"] + duree_clip(clip) / 2
    src = float(clip["src_debut"]) + (t - clip["debut"]) * float(clip.get("vitesse", 1.0) or 1.0)
    f = os.path.join(tempfile.gettempdir(), f"philcut_etal_{clip['id']}.png")
    if m.get("genre") == "image":
        moteur.lancer(["-y", "-i", m["chemin"], "-vf", f"scale={largeur}:-2", "-frames:v", "1", f])
    else:
        moteur.lancer(["-y", "-ss", f"{max(0.0, src):.3f}", "-i", m["chemin"], "-vf", f"scale={largeur}:-2", "-frames:v", "1", f])
    return QImage(f)


def etalonner_image(img, reglages):
    """L'image avec les réglages, par FFmpeg (la même chaîne qu'à l'export)."""
    ch = ET.filtre(reglages)
    if not ch or img.isNull():
        return img
    d = tempfile.gettempdir()
    a, b = os.path.join(d, "philcut_etal_a.png"), os.path.join(d, "philcut_etal_b.png")
    img.save(a)
    moteur.lancer(["-y", "-i", a, "-vf", ch, "-frames:v", "1", b])
    out = QImage(b)
    return out if not out.isNull() else img


def tableau(img):
    import numpy as np
    i = img.convertToFormat(QImage.Format_RGB888)
    w, h, bpl = i.width(), i.height(), i.bytesPerLine()
    a = np.frombuffer(bytes(i.constBits())[: bpl * h], dtype=np.uint8).reshape(h, bpl)[:, : w * 3].reshape(h, w, 3)
    return a.copy()


class DialogueEtalonnage(QDialog):
    CURSEURS = (("exposition", _("Exposition")), ("contraste", _("Contraste")), ("saturation", _("Saturation")),
                ("temperature", _("Température (froid ← → chaud)")), ("teinte", _("Teinte (vert ← → magenta)")))

    def __init__(self, ed, clip):
        super().__init__(ed)
        self.ed, self.clip = ed, clip
        self.setWindowTitle(_("Étalonnage — {n}", n=clip.get("nom", "")))
        self.resize(1000, 700)
        self.r = ET.reglages_de(clip)
        self.depart = dict(self.r)
        v = QVBoxLayout(self)
        aide = QLabel(_("Corrigez la lumière et les couleurs du plan. Faites glisser le rideau jaune pour comparer avant et après. "
                        "Les roues poussent une couleur dans les ombres, les tons moyens ou les hautes lumières."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        h = QHBoxLayout()
        self.vue = VueAvantApres()
        h.addWidget(self.vue, 3)
        droite = QVBoxLayout()
        g = QGridLayout()
        self.roues = {}
        for i, (cle, titre) in enumerate((("ombres", _("Ombres")), ("moyens", _("Tons moyens")), ("hautes", _("Hautes lumières")))):
            rw = RoueCouleur(titre)
            rw.valeur(self.r[cle + "_x"], self.r[cle + "_y"])
            rw.change.connect(lambda x, y, cle=cle: self._roue(cle, x, y))
            self.roues[cle] = rw
            g.addWidget(rw, 0, i)
        droite.addLayout(g)
        f = QFormLayout()
        self.curseurs = {}
        for cle, lib in self.CURSEURS:
            s = QSlider(Qt.Horizontal)
            s.setRange(-100, 100)
            s.setValue(int(round(self.r[cle] * 100)))
            s.valueChanged.connect(lambda val, cle=cle: self._curseur(cle, val))
            self.curseurs[cle] = s
            f.addRow(lib, s)
        droite.addLayout(f)
        hb = QHBoxLayout()
        b_auto = QPushButton(_("Auto"))
        b_auto.setToolTip(_("Retire une dominante de couleur et redonne du peps à une image terne"))
        b_auto.clicked.connect(self.auto)
        hb.addWidget(b_auto)
        b_zero = QPushButton(_("Réinitialiser"))
        b_zero.clicked.connect(lambda: self._poser(ET.neutre()))
        hb.addWidget(b_zero)
        droite.addLayout(hb)
        ha = QHBoxLayout()
        self.ref = QComboBox()
        for c in ed.projet.clips_piste("video"):
            if c["id"] != clip["id"]:
                self.ref.addItem(f"{c.get('nom', '')} ({c['debut']:.1f} s)", c["id"])
        ha.addWidget(self.ref, 1)
        b_acc = QPushButton(_("Accorder sur ce plan"))
        b_acc.setToolTip(_("Donne à ce plan la lumière et les couleurs du plan choisi (deux caméras, deux heures de la journée)"))
        b_acc.clicked.connect(self.accorder)
        b_acc.setEnabled(self.ref.count() > 0)
        ha.addWidget(b_acc)
        droite.addLayout(ha)
        hc = QHBoxLayout()
        self.copie = QComboBox()
        self.copie.addItem(_("Copier sur les plans du même rush"), "rush")
        self.copie.addItem(_("Copier sur tous les plans vidéo"), "tous")
        hc.addWidget(self.copie, 1)
        b_cp = QPushButton(_("Copier"))
        b_cp.clicked.connect(self.copier)
        hc.addWidget(b_cp)
        droite.addLayout(hc)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        droite.addWidget(self.etat)
        droite.addStretch(1)
        h.addLayout(droite, 2)
        v.addLayout(h, 1)
        hf = QHBoxLayout()
        hf.addStretch(1)
        b_ok = QPushButton(_("Appliquer"))
        b_ok.setDefault(True)
        b_ok.clicked.connect(self.valider)
        b_an = QPushButton(_("Annuler"))
        b_an.clicked.connect(self.reject)
        hf.addWidget(b_ok)
        hf.addWidget(b_an)
        v.addLayout(hf)
        self._minuterie = QTimer(self)
        self._minuterie.setSingleShot(True)
        self._minuterie.timeout.connect(self._rendre)
        self.source = image_du_plan(ed.projet, clip, ed.timeline.position)
        self.vue.avant = self.source
        self._rendre()

    # ---- réglages
    def _roue(self, cle, x, y):
        self.r[cle + "_x"], self.r[cle + "_y"] = round(x, 3), round(y, 3)
        self._minuterie.start(120)

    def _curseur(self, cle, val):
        self.r[cle] = val / 100.0
        self._minuterie.start(120)

    def _poser(self, r):
        self.r = dict(ET.neutre(), **r)
        for cle, s in self.curseurs.items():
            s.blockSignals(True)
            s.setValue(int(round(self.r[cle] * 100)))
            s.blockSignals(False)
        for cle, rw in self.roues.items():
            rw.valeur(self.r[cle + "_x"], self.r[cle + "_y"])
        self._rendre()

    def _rendre(self):
        try:
            self.vue.apres = etalonner_image(self.source, self.r)
        except Exception as e:     # noqa: BLE001
            self.etat.setText(_("Aperçu impossible : {e}", e=str(e)[:200]))
            self.vue.apres = self.source
        self.vue.update()

    def auto(self):
        if self.source.isNull():
            return
        self._poser(ET.auto(tableau(self.source)))
        self.etat.setText(_("Réglages automatiques : ajustez-les si besoin."))

    def accorder(self):
        c = self.ed.projet.clip(self.ref.currentData())
        if not c or self.source.isNull():
            return
        ref = image_du_plan(self.ed.projet, c, None)
        ref_et = etalonner_image(ref, ET.reglages_de(c))            # le plan de référence tel qu'il est vu, étalonnage compris
        if ref_et.isNull():
            return
        self._poser(ET.accorder(tableau(self.source), tableau(ref_et)))
        self.etat.setText(_("Plan accordé sur « {n} ».", n=c.get("nom", "")))

    def copier(self):
        p = self.ed.projet
        p.marquer()
        m = self.clip["media"]
        cibles = [c for c in p.clips_piste("video") if c["id"] != self.clip["id"] and (self.copie.currentData() == "tous" or c["media"] == m)]
        for c in cibles:
            ET.appliquer(c, self.r)
        ET.appliquer(self.clip, self.r)
        p.modifie = True
        self.ed.rafraichir()
        self.etat.setText(_("Étalonnage copié sur {n} plan(s) (Ctrl+Z pour revenir).", n=len(cibles)))

    def valider(self):
        p = self.ed.projet
        if self.r != ET.reglages_de(self.clip):
            p.marquer()
            ET.appliquer(self.clip, self.r)
            p.modifie = True
            self.ed.rafraichir()
            self.ed.encart.message(_("Étalonnage appliqué (Ctrl+Z pour revenir)."), 5000)
        self.accept()
