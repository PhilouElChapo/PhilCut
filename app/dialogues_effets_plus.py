"""Fenêtres des effets ajoutés en 0.4.1 : image figée, bruitages."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout)

from . import bruitages as B
from .langue import _
from .widgets import boutons_fr


class DialogueFiger(QDialog):
    """Image figée : durée, présentation, légende, flash, déclic."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Figer l'image"))
        v = QVBoxLayout(self)
        aide = QLabel(_("Le plan s'arrête sur l'image de la tête de lecture, puis reprend. La suite du montage est décalée d'autant. "
                        "L'image figée devient un plan à part : on peut la rogner, lui ajouter des effets ou la supprimer."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        f = QFormLayout()
        self.duree = QDoubleSpinBox()
        self.duree.setRange(0.5, 30)
        self.duree.setValue(3.0)
        self.duree.setSuffix(" s")
        f.addRow(_("Durée"), self.duree)
        self.style = QComboBox()
        self.style.addItem(_("Cadre photo sur fond flou"), "cadre")
        self.style.addItem(_("Image simple, plein cadre"), "simple")
        f.addRow(_("Présentation"), self.style)
        self.zoom = QCheckBox(_("Zoom lent vers l'avant"))
        self.zoom.setChecked(True)
        f.addRow(self.zoom)
        self.legende = QLineEdit()
        self.legende.setPlaceholderText(_("Légende (facultatif) : « Arrivée à Calvi »"))
        f.addRow(_("Légende"), self.legende)
        self.flash = QCheckBox(_("Flash blanc au moment où l'image se fige"))
        self.flash.setChecked(True)
        f.addRow(self.flash)
        self.declic = QCheckBox(_("Bruit de déclic d'appareil photo"))
        self.declic.setChecked(True)
        f.addRow(self.declic)
        v.addLayout(f)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Figer l'image"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def options(self):
        return {"duree": self.duree.value(), "style": self.style.currentData(), "zoom": self.zoom.isChecked(),
                "legende": self.legende.text().strip(), "flash": self.flash.isChecked(), "declic": self.declic.isChecked()}


class DialogueBruitages(QDialog):
    """Liste des bruitages : écouter, puis poser au curseur."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Bruitages"))
        self.resize(520, 420)
        v = QVBoxLayout(self)
        aide = QLabel(_("Sons fabriqués sur ce poste, libres de droits. Cliquez pour écouter ; « Poser » le met à la tête de lecture, sur une "
                        "piste de son libre."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.liste = QListWidget()
        for k, (nom, desc, *_r) in B.SONS.items():
            it = QListWidgetItem(f"{nom} — {desc}")
            it.setData(Qt.UserRole, k)
            self.liste.addItem(it)
        self.liste.setCurrentRow(0)
        self.liste.itemDoubleClicked.connect(lambda _it: self.accept())
        v.addWidget(self.liste, 1)
        h = QHBoxLayout()
        self.b_ecoute = QPushButton(_("▶ Ecouter"))
        self.b_ecoute.clicked.connect(self.ecouter)
        h.addWidget(self.b_ecoute)
        h.addStretch(1)
        v.addLayout(h)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Poser à la tête de lecture"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.lecteur = None

    def choix(self):
        it = self.liste.currentItem()
        return it.data(Qt.UserRole) if it else None

    def ecouter(self):
        k = self.choix()
        if not k:
            return
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            return
        if self.lecteur is None:
            self.lecteur = QMediaPlayer(self)
            self.sortie = QAudioOutput(self)
            self.lecteur.setAudioOutput(self.sortie)
        self.lecteur.setSource(QUrl.fromLocalFile(B.chemin(k)))
        self.lecteur.play()
