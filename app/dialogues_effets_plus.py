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
        aide = QLabel(_("Le plan s'arrête sur l'image de la ligne rouge, puis reprend. La suite du montage est décalée d'autant. "
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
        self.style.addItem(_("Bullet time (la caméra tourne autour, whoosh)"), "bullet")
        f.addRow(_("Présentation"), self.style)
        self.zoom = QCheckBox(_("Zoom lent vers l'avant"))
        self.zoom.setChecked(True)
        f.addRow(self.zoom)
        self.legende = QLineEdit()
        self.legende.setPlaceholderText(_("Légende (facultatif) : « Arrivée au sommet »"))
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
        self.resize(640, 560)
        v = QVBoxLayout(self)
        aide = QLabel(_("Sons fabriqués sur ce poste, libres de droits. Cliquez pour écouter ; « Poser » le met à la ligne rouge, sur une "
                        "piste de son libre."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.liste = QListWidget()
        for k, (nom, desc, *_r) in B.SONS.items():
            it = QListWidgetItem(f"{nom} — {desc}")
            it.setData(Qt.UserRole, k)
            self.liste.addItem(it)
        self.liste.setCurrentRow(0)
        self.liste.setWordWrap(True)
        self.liste.itemDoubleClicked.connect(lambda _it: self.accept())
        self.liste.itemClicked.connect(lambda _it: self.ecouter())              # comme une table de sons : un clic, on entend
        v.addWidget(self.liste, 1)
        h = QHBoxLayout()
        self.b_ecoute = QPushButton(_("▶ Ecouter"))
        self.b_ecoute.clicked.connect(self.ecouter)
        h.addWidget(self.b_ecoute)
        h.addStretch(1)
        b_plus = QPushButton(_("Plus de sons : mes sons, répliques, sons en ligne…"))
        b_plus.setToolTip(_("La bibliothèque des tampons : vos propres sons, répliques de films, sons libres trouvés en ligne"))
        b_plus.clicked.connect(self._plus)
        h.addWidget(b_plus)
        v.addLayout(h)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Poser à la ligne rouge"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.lecteur = None

    def choix(self):
        it = self.liste.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _plus(self):
        ed = self.parent()
        self.reject()
        if ed is not None and hasattr(ed, "tampons"):
            ed.tampons()

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


class GalerieGoodies(QDialog):
    """Choisir un Goodie en le voyant : vignettes dessinées par famille ; un double-clic le pose à la ligne rouge."""

    def __init__(self, parent=None, params=None):
        super().__init__(parent)
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QIcon, QPixmap
        from PySide6.QtWidgets import QListView
        from . import goodies as GO
        self.setWindowTitle(_("Goodies"))
        self.resize(760, 560)
        v = QVBoxLayout(self)
        aide = QLabel(_("Cliquez un Goodie puis « Poser », ou double-cliquez : il arrive à la ligne rouge ; vous le placez et le "
                        "redimensionnez ensuite dans l'image, ses réglages sont dans l'Inspecteur."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.famille = QComboBox()
        self.famille.addItem(_("Toutes les familles"), "")
        for k, pk in GO.PACKS.items():
            self.famille.addItem(pk["nom"], k)
        i = self.famille.findData((params or {}).get("goodies_famille", ""))
        self.famille.setCurrentIndex(max(0, i))
        h = QHBoxLayout()
        h.addWidget(self.famille, 1)
        b_tdb = QPushButton(_("Tableau de bord complet…"))
        b_tdb.setToolTip(_("Plusieurs instruments posés ensemble (altimètre, vitesse, cap…) avec un profil de vol réglable"))
        b_tdb.clicked.connect(lambda: (setattr(self, "_choix_special", "tableau_de_bord"), self.accept()))
        h.addWidget(b_tdb)
        b_nv = QPushButton(_("Nouveautés…"))
        b_nv.setToolTip(_("Ce que la veille mensuelle a ajouté (Goodies, modèles, styles) ; « Vérifier maintenant » interroge le catalogue en ligne"))
        b_nv.clicked.connect(self._nouveautes)
        h.addWidget(b_nv)
        v.addLayout(h)
        self._choix_special = None
        self.liste = QListWidget()
        self.liste.setViewMode(QListView.IconMode)
        self.liste.setIconSize(QSize(96, 96))
        self.liste.setGridSize(QSize(120, 132))
        self.liste.setResizeMode(QListView.Adjust)
        self.liste.setMovement(QListView.Static)
        self.liste.setWordWrap(True)
        self.liste.itemDoubleClicked.connect(lambda _it: self.accept())
        v.addWidget(self.liste, 1)
        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        v.addWidget(self.desc)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Poser à la ligne rouge"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.params = params if params is not None else {}
        self._GO, self._QIcon, self._QPixmap = GO, QIcon, QPixmap
        self.famille.currentIndexChanged.connect(self._remplir)
        self.liste.currentItemChanged.connect(lambda it, _p: it and self.desc.setText(it.toolTip()))
        self._remplir()

    def _remplir(self):
        GO = self._GO
        fam = self.famille.currentData() or ""
        self.params["goodies_famille"] = fam
        self.liste.clear()
        vus = set()
        for k, pk in GO.PACKS.items():
            if fam and k != fam:
                continue
            for gid in pk["goodies"]:
                if gid in vus:
                    continue
                vus.add(gid)
                g = {"genre": gid, "debut": 0, "fin": 10, "x": 0.5, "y": 0.5, "taille": 0.3, "style": "cadran", "valeurs": [],
                     "options": {"etapes": [{"nom": "A", "code": "A", "lat": 45.0, "lon": 4.0}, {"nom": "B", "code": "B", "lat": 44.6, "lon": 4.6}],
                                 "texte": GO.GENRES.get(gid, (gid,))[0], "angle": 30}}
                if gid == "fleche":
                    g["options"].update(style="courbe", angle=10)
                elif gid == "bandeau_tendance":
                    g["options"].update(texte="WAHOU !", angle=-4)
                elif gid == "surligne":
                    g["options"].update(texte="Top", angle=-2)
                try:
                    img = GO.image(g, 5.0, 96)
                    icone_ = self._QIcon(self._QPixmap.fromImage(img))
                except Exception:       # noqa: BLE001
                    icone_ = self._QIcon()
                from . import nouveautes as NV
                it = QListWidgetItem(icone_, ("✦ " if NV.est_nouveau(self.params, "goodies", gid) else "") + GO.GENRES.get(gid, (gid,))[0])
                it.setData(Qt.UserRole, gid)
                it.setToolTip(f"{pk['nom']} — {pk['description']}")
                it.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
                self.liste.addItem(it)
        self.liste.setCurrentRow(0)

    def _nouveautes(self):
        from .dialogues_nouveautes import DialogueNouveautes
        w = self.parent()
        while w is not None and not hasattr(w, "voir_nouveautes"):
            w = w.parent()
        d = DialogueNouveautes(w or self, self.params, fermer_seulement=True)      # depuis la galerie : on y reste
        d.exec()
        self._remplir()

    def choix(self):
        if getattr(self, "_choix_special", None):
            return self._choix_special
        it = self.liste.currentItem()
        return it.data(Qt.UserRole) if it else None
