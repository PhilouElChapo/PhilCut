"""Fenêtres de la bibliothèque toute faite (0.9.89) : choisir une entrée du catalogue (tenue, lieu, véhicule, avion, personnage
type) pour la ranger dans « Ma bibliothèque », et composer une tenue pièce par pièce (haut, bas, chaussures, chapeau,
matière…)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout)

from . import catalogue_prompts as CP
from .cartes_assistant import aide
from .langue import _
from .taches import texte_erreur


class DialogueCatalogue(QDialog):
    """La bibliothèque toute faite : rubrique, femme / homme, recherche ; « Ajouter à ma bibliothèque » range l'entrée."""

    def __init__(self, parent, params, genres=None):
        super().__init__(parent)
        self.params, self.ajoutees = params, []
        self.setWindowTitle(_("Bibliothèque toute faite"))
        self.resize(900, 600)
        v = QVBoxLayout(self)
        v.addWidget(aide(_("Des descriptions toutes prêtes (et leurs mots anglais pour les IA) : prenez-en une, elle arrive dans votre "
                           "bibliothèque où vous pouvez la modifier, ajouter vos photos, faire sa fiche ou sa planche. Vos propres "
                           "créations s'ajoutent à côté.")))
        h = QHBoxLayout()
        self.rubrique = QComboBox()
        rubs = [r for r in CP.rubriques(genres or ("tenue", "lieu", "objet", "personnage"))]
        self.rubrique.addItem(_("Tout"), [r[0] for r in rubs])
        for k, nom, _g in rubs:
            self.rubrique.addItem(nom, k)
        self.rubrique.currentIndexChanged.connect(lambda _i: self.remplir())
        h.addWidget(self.rubrique)
        self.pour = QComboBox()
        for k, lib in CP.POUR:
            self.pour.addItem(lib, k)
        self.pour.currentIndexChanged.connect(lambda _i: self.remplir())
        h.addWidget(self.pour)
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(_("Chercher : piscine, cuir, berline, hélicoptère…"))
        self.cherche.textChanged.connect(lambda _t: self.remplir())
        h.addWidget(self.cherche, 1)
        v.addLayout(h)
        h = QHBoxLayout()
        self.liste = QListWidget()
        self.liste.setWordWrap(True)
        self.liste.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.liste.currentRowChanged.connect(self._detail)
        self.liste.itemDoubleClicked.connect(lambda _i: self.ajouter())
        h.addWidget(self.liste, 1)
        dv = QVBoxLayout()
        self.l_image = QLabel()
        self.l_image.setFixedSize(300, 200)
        self.l_image.setAlignment(Qt.AlignCenter)
        self.l_image.setStyleSheet("border:1px solid #888; border-radius:4px")
        dv.addWidget(self.l_image)
        self.l_desc = QLabel("")
        self.l_desc.setWordWrap(True)
        self.l_desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
        dv.addWidget(self.l_desc)
        dv.addStretch(1)
        h.addLayout(dv)
        v.addLayout(h, 1)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hb = QHBoxLayout()
        b = QPushButton(_("Ajouter à ma bibliothèque"))
        b.setProperty("primaire", True)
        b.clicked.connect(self.ajouter)
        hb.addWidget(b)
        hb.addStretch(1)
        bf = QPushButton(_("Fermer"))
        bf.clicked.connect(self.accept)
        hb.addWidget(bf)
        v.addLayout(hb)
        self.remplir()

    def remplir(self):
        self.items = CP.entrees(self.rubrique.currentData(), self.pour.currentData(), self.cherche.text())
        self.liste.blockSignals(True)
        self.liste.clear()
        noms = {k: n for k, n, _g in CP.rubriques()}
        for e in self.items:
            QListWidgetItem(f"{e['nom_affiche']} — {noms.get(e['rubrique'], '')}", self.liste)
        self.liste.blockSignals(False)
        if self.items:
            self.liste.setCurrentRow(0)
        self._detail(0 if self.items else -1)

    def _detail(self, r):
        e = self.items[r] if 0 <= r < len(self.items) else None
        if e is None:
            self.l_desc.setText(_("Rien ne correspond."))
            self.l_image.clear()
            return
        self.l_desc.setText(f"<b>{e['nom_affiche']}</b><br>{e['description_affichee']}<br><i>{e['en']}</i>")
        im = CP.image(e, reseau=False)
        if im:
            self.l_image.setPixmap(QPixmap(im).scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.l_image.setText(_("Pas d'image d'exemple"))

    def ajouter(self):
        r = self.liste.currentRow()
        if not 0 <= r < len(self.items):
            return
        e = self.items[r]
        try:
            x = CP.vers_bibliotheque(self.params, e)
        except ValueError as err:
            self.etat.setText("✕ " + texte_erreur(err))
            return
        self.ajoutees.append(x)
        self.etat.setText(_("✓ « {n} » est dans votre bibliothèque.", n=x["nom"]))


class ComposerTenue(QDialog):
    """Une tenue pièce par pièce : femme ou homme, haut, bas (ou robe, ensemble), veste, chaussures, chapeau, accessoire,
    matière ; la description française et anglaise se forme au fil des choix."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(_("Composer une tenue"))
        self.resultat = None
        v = QVBoxLayout(self)
        v.addWidget(aide(_("Choisissez pièce par pièce ; laissez « — » pour ne rien imposer.")))
        f = QFormLayout()
        self.pour = QComboBox()
        for k, lib in CP.POUR:
            self.pour.addItem(lib, k)
        self.pour.currentIndexChanged.connect(lambda _i: self._remplir())
        f.addRow(_("Pour"), self.pour)
        self.combos = {}
        for k, nom, _g in CP.rubriques("piece"):
            c = QComboBox()
            self.combos[k] = c
            c.currentIndexChanged.connect(lambda _i: self._maj())
            f.addRow(nom, c)
        v.addLayout(f)
        self.apercu = QLabel("")
        self.apercu.setWordWrap(True)
        v.addWidget(self.apercu)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._remplir()

    def _remplir(self):
        for k, c in self.combos.items():
            garde = c.currentData()
            c.blockSignals(True)
            c.clear()
            c.addItem("—", "")
            for e in CP.entrees(k, self.pour.currentData()):
                c.addItem(e["nom_affiche"], e["id"])
            c.setCurrentIndex(max(0, c.findData(garde)))
            c.blockSignals(False)
        self._maj()

    def _maj(self):
        pieces = [c.currentData() for k, c in self.combos.items() if k != "matiere"]
        m = self.combos.get("matiere")
        self.resultat = CP.composer(pieces, m.currentData() if m else None)
        self.apercu.setText(_("Tenue : {t}", t=self.resultat[0] or "—"))
