"""Fenêtre « Retirer le fond » (0.9.5) : avant / après sur damier, méthode et tolérance, PNG transparent enregistré à
côté de l'original (jamais modifié)."""
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSlider, QVBoxLayout)

from . import fond as F
from .langue import _
from .taches import Tache
from .taches import texte_erreur


def _damier(w, h, c=12):
    px = QPixmap(w, h)
    px.fill(QColor("#cfcfcf"))
    p = QPainter(px)
    for y in range(0, h, c):
        for x in range((y // c) % 2 * c, w, 2 * c):
            p.fillRect(x, y, c, c, QColor("#f4f4f4"))
    p.end()
    return px


def _pixmap(img, w, h):
    import cv2
    rgba = cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA)
    q = QImage(rgba.data, rgba.shape[1], rgba.shape[0], 4 * rgba.shape[1], QImage.Format_RGBA8888).copy()
    pm = QPixmap.fromImage(q).scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    fond = _damier(w, h)
    p = QPainter(fond)
    p.drawPixmap((w - pm.width()) // 2, (h - pm.height()) // 2, pm)
    p.end()
    return fond


class DialogueFond(QDialog):
    def __init__(self, parent, chemin):
        super().__init__(parent)
        self.chemin = chemin
        self.resultat = None          # chemin du PNG transparent enregistré
        self.image = F.lire(chemin)
        self.sortie = None
        self.tache = None
        self.setWindowTitle(_("Retirer le fond de l'image"))
        self.resize(980, 600)
        v = QVBoxLayout(self)
        info = QLabel(_("« {n} » devient une copie PNG transparente, sur ce poste (rien n'est envoyé). L'original n'est pas modifié.",
                        n=os.path.basename(chemin)))
        info.setWordWrap(True)
        v.addWidget(info)
        h = QHBoxLayout()
        self.vue_avant, self.vue_apres = QLabel(), QLabel()
        for titre, vue in ((_("Avant"), self.vue_avant), (_("Après (le damier = transparent)"), self.vue_apres)):
            c = QVBoxLayout()
            c.addWidget(QLabel(titre))
            vue.setFixedSize(460, 380)
            vue.setAlignment(Qt.AlignCenter)
            c.addWidget(vue)
            h.addLayout(c)
        v.addLayout(h)
        self.vue_avant.setPixmap(_pixmap(self.image, 460, 380))
        hr = QHBoxLayout()
        hr.addWidget(QLabel(_("Méthode")))
        self.methode = QComboBox()
        for k, lib in F.METHODES.items():
            self.methode.addItem(lib, k)
        self.methode.currentIndexChanged.connect(self._regle)
        hr.addWidget(self.methode)
        self.lbl_tol = QLabel(_("Tolérance"))
        hr.addWidget(self.lbl_tol)
        self.tolerance = QSlider(Qt.Horizontal)
        self.tolerance.setRange(5, 90)
        self.tolerance.setValue(30)
        self.tolerance.setToolTip(_("Plus haut : retire aussi les couleurs proches du fond (ombres, dégradés) ; plus bas : garde plus de détails"))
        self.tolerance.valueChanged.connect(self._regle)
        hr.addWidget(self.tolerance, 1)
        self.recadrer = QCheckBox(_("Recadrer au sujet"))
        self.recadrer.setChecked(True)
        self.recadrer.setToolTip(_("Retire les bords devenus vides : le logo remplit sa place"))
        self.recadrer.toggled.connect(self._regle)
        hr.addWidget(self.recadrer)
        v.addLayout(hr)
        self.enferme = QCheckBox(_("Retirer aussi le fond enfermé (intérieur des lettres, d'un anneau)"))
        self.enferme.toggled.connect(self._regle)
        v.addWidget(self.enferme)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.setMaximumHeight(12)
        self.barre.setTextVisible(False)
        self.barre.hide()
        v.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.etat)
        hb = QHBoxLayout()
        hb.addStretch(1)
        self.b_ok = QPushButton(_("Garder l'image sans fond"))
        self.b_ok.setStyleSheet("font-weight:600;padding:6px 14px")
        self.b_ok.setEnabled(False)
        self.b_ok.clicked.connect(self.garder)
        hb.addWidget(self.b_ok)
        b = QPushButton(_("Annuler"))
        b.clicked.connect(self.reject)
        hb.addWidget(b)
        v.addLayout(hb)
        self._delai = QTimer(self)
        self._delai.setSingleShot(True)
        self._delai.setInterval(200)
        self._delai.timeout.connect(self._lancer)
        if F.a_deja_transparence(self.image):
            self.etat.setText(_("Cette image a déjà de la transparence : elle est gardée, et le fond restant est retiré en plus."))
        self._regle()

    def _regle(self):
        uni = self.methode.currentData() in ("uni", "auto")
        self.lbl_tol.setEnabled(uni)
        self.tolerance.setEnabled(uni)
        self.enferme.setEnabled(uni)
        self._delai.start()

    def _lancer(self):
        if self.tache is not None and self.tache.isRunning():
            self._delai.start()
            return
        img, m, tol, rec = self.image, self.methode.currentData(), self.tolerance.value(), self.recadrer.isChecked()
        enf = self.enferme.isChecked()

        def travail(t):
            out, utilisee = F.retirer_fond(img, m, tol, progression=t.avancer, enferme=enf)
            return (F.recadrer_au_sujet(out) if rec else out), utilisee
        self.tache = Tache(travail, _("Retirer le fond"))
        self.tache.progression.connect(lambda f, x: (self.barre.show(), self.barre.setValue(int(f * 1000)), self.etat.setText(x)),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self._t0 = time.monotonic()
        self.tache.start()

    def _fini(self, r, err):
        self.barre.hide()
        if err:
            self.etat.setText(_("✕ {e}", e=texte_erreur(err)[:300]))
            return
        self.sortie, utilisee = r
        self.vue_apres.setPixmap(_pixmap(self.sortie, 460, 380))
        self.b_ok.setEnabled(True)
        self.etat.setText(_("Fait en {s:.1f} s ({m}). Pas parfait ? Changez la méthode ou la tolérance.",
                            s=time.monotonic() - self._t0, m=F.METHODES[utilisee]))

    def garder(self):
        if self.sortie is None:
            return
        self.resultat = F.enregistrer(self.sortie, F.chemin_copie(self.chemin))
        self.accept()


def retirer_fond(parent, chemin):
    """Ouvre la fenêtre ; renvoie le chemin du PNG transparent, ou None."""
    d = DialogueFond(parent, chemin)
    return d.resultat if d.exec() == QDialog.Accepted else None
