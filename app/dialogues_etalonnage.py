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
            p.setPen(QColor("#cccccc"))
            p.drawText(self.rect().adjusted(20, 20, -20, -20), Qt.AlignCenter | Qt.TextWordWrap, getattr(self, "message", "") or
                       _("Image du plan introuvable : choisissez un autre instant avec le curseur « Image du plan » sous l'image."))
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


def _dossier_tmp():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "tmp_etalonnage")
    os.makedirs(d, exist_ok=True)
    return d


def image_du_plan(projet, clip, t=None, largeur=640, src=None):
    """Image du rush de ce plan (src = instant dans le rush ; sinon l'instant t de la timeline, sinon le milieu du plan),
    en QImage. Plusieurs essais : un instant mal tombé (fin de fichier, image noire de début) ne donne pas une vue vide."""
    m = projet.media(clip["media"]) or {}
    if not m.get("chemin") or not os.path.exists(m["chemin"]):
        return QImage()
    a, b = float(clip["src_debut"]), float(clip["src_fin"])
    if src is None:
        if t is None or not (clip["debut"] <= t < clip["debut"] + duree_clip(clip)):
            t = clip["debut"] + duree_clip(clip) / 2
        src = a + (t - clip["debut"]) * float(clip.get("vitesse", 1.0) or 1.0)
    f = os.path.join(_dossier_tmp(), f"plan_{clip['id']}.png")
    essais = [src, (a + b) / 2, a, 0.0] if m.get("genre") != "image" else [None]
    for s_ in essais:
        try:
            if os.path.exists(f):
                os.remove(f)
            av = ["-ss", f"{max(0.0, min(s_, b - 0.05)):.3f}"] if s_ is not None else []
            moteur.lancer(["-y"] + av + ["-i", m["chemin"], "-vf", f"scale={largeur}:-2", "-frames:v", "1", "-update", "1", f])
        except Exception:     # noqa: BLE001
            continue
        img = QImage(f)
        if not img.isNull():
            return img.convertToFormat(QImage.Format_RGB32)
    return QImage()


def etalonner_image(img, reglages):
    """L'image avec les réglages, par FFmpeg (la même chaîne qu'à l'export)."""
    ch = ET.filtre(reglages)
    if not ch or img.isNull():
        return img
    d = _dossier_tmp()
    a, b = os.path.join(d, "avant.png"), os.path.join(d, "apres.png")
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
        gauche = QVBoxLayout()
        self.vue = VueAvantApres()
        gauche.addWidget(self.vue, 1)
        expl = QLabel(_("Le trait jaune est un rideau : à sa gauche l'image d'origine (AVANT), à sa droite l'image corrigée (APRÈS). "
                        "Cliquez ou faites-le glisser sur l'image pour comparer n'importe quelle zone."))
        expl.setWordWrap(True)
        gauche.addWidget(expl)
        hi = QHBoxLayout()
        hi.addWidget(QLabel(_("Image du plan")))
        self.instant = QSlider(Qt.Horizontal)
        self.instant.setRange(0, 1000)
        self.instant.setToolTip(_("Choisissez à la souris l'image du plan qui sert à régler (l'étalonnage s'applique à tout le plan)"))
        self.instant.sliderReleased.connect(self._changer_image)
        self.instant.valueChanged.connect(lambda _v: self._minuterie_image.start(250))
        hi.addWidget(self.instant, 1)
        self.l_instant = QLabel("")
        hi.addWidget(self.l_instant)
        gauche.addLayout(hi)
        h.addLayout(gauche, 3)
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
        self._minuterie_image = QTimer(self)
        self._minuterie_image.setSingleShot(True)
        self._minuterie_image.timeout.connect(self._changer_image)
        a, b = float(clip["src_debut"]), float(clip["src_fin"])
        t = ed.timeline.position
        src = a + (t - clip["debut"]) * float(clip.get("vitesse", 1.0) or 1.0) if clip["debut"] <= t < clip["debut"] + duree_clip(clip) else (a + b) / 2
        self.instant.blockSignals(True)
        self.instant.setValue(int(1000 * (src - a) / max(0.01, b - a)))
        self.instant.blockSignals(False)
        self.source = QImage()
        self._changer_image()

    def _changer_image(self):
        a, b = float(self.clip["src_debut"]), float(self.clip["src_fin"])
        src = a + (b - a) * self.instant.value() / 1000.0
        self.l_instant.setText(f"{src - a:.1f} s")
        img = image_du_plan(self.ed.projet, self.clip, src=src)
        if not img.isNull():
            self.source = img
            self.vue.avant = img
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
