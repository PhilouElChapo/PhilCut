"""Fenêtre « Modèles de montage » (0.9.25) : une liste de modèles (nom, explication), la durée et le format, puis
« Monter avec ce modèle » : les rushes sont analysés sur ce poste et le montage est posé ; Ctrl+Z revient."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QProgressBar, QPushButton,
                               QSpinBox, QVBoxLayout)

from . import modeles_montage as MM
from .langue import _
from .taches import Tache


class DialogueModeles(QDialog):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed, self.tache = ed, None
        self.setWindowTitle(_("Modèles de montage"))
        self.resize(720, 560)
        v = QVBoxLayout(self)
        t = QLabel(_("Choisissez un modèle : PhilCut monte VOS rushes à sa façon (rythme des coupes, transitions, look, titre animé, "
                     "écran de fin) ; la musique du projet est calée sur les temps forts. Tout reste modifiable ensuite."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.liste = QListWidget()
        self.liste.setWordWrap(True)
        self.liste.setSpacing(3)
        for k, m in MM.tous(ed.params).items():
            it = QListWidgetItem(("✦ " if m.get("nouveau") else "") + f"{m['nom']}\n{m['desc']}")
            it.setData(Qt.UserRole, k)
            it.setToolTip(m["desc"])
            self.liste.addItem(it)
        self.liste.currentItemChanged.connect(self._choisi)
        self.liste.itemDoubleClicked.connect(lambda _i: self.monter())
        v.addWidget(self.liste, 1)
        f = QFormLayout()
        self.duree = QSpinBox()
        self.duree.setRange(5, 600)
        self.duree.setSuffix(" s")
        f.addRow(_("Durée visée"), self.duree)
        self.format = QComboBox()
        for k, lib in (("16:9", _("Horizontal 16:9 (YouTube)")), ("9:16", _("Vertical 9:16 (Reels, Shorts, TikTok)")), ("1:1", _("Carré 1:1"))):
            self.format.addItem(lib, k)
        f.addRow(_("Format"), self.format)
        v.addLayout(f)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        h = QHBoxLayout()
        b_imp = QPushButton(_("Ajouter des rushes…"))
        b_imp.clicked.connect(self._importer)
        h.addWidget(b_imp)
        h.addStretch(1)
        self.b_monter = QPushButton(_("Monter avec ce modèle"))
        self.b_monter.setDefault(True)
        self.b_monter.clicked.connect(self.monter)
        h.addWidget(self.b_monter)
        b_f = QPushButton(_("Fermer"))
        b_f.clicked.connect(self.reject)
        h.addWidget(b_f)
        v.addLayout(h)
        self.liste.setCurrentRow(0)
        self._etat_rushes()

    def _choisi(self, it, _avant=None):
        if not it:
            return
        m = MM.tous(self.ed.params)[it.data(Qt.UserRole)]
        self.duree.setValue(int(m["duree"]))
        self.format.setCurrentIndex(max(0, self.format.findData(m["format"])))

    def _etat_rushes(self):
        p = self.ed.projet
        nv = sum(1 for m in p.medias if m.get("genre") == "video")
        ni = sum(1 for m in p.medias if m.get("genre") == "image")
        na = sum(1 for m in p.medias if m.get("genre") == "audio")
        txt = _("Dans le projet : {v} vidéo(s), {i} photo(s), {a} musique(s).", v=nv, i=ni, a=na)
        if not na:
            txt += " " + _("Sans musique dans le projet, le montage n'en aura pas : ajoutez-en une (ou Mes musiques) avant ou après.")
        if p.clips:
            txt += " " + _("Le montage actuel sera remplacé (Ctrl+Z revient en arrière).")
        self.etat.setText(txt)
        self.b_monter.setEnabled(bool(nv or ni))

    def _importer(self):
        self.ed.importer()
        self._etat_rushes()

    def monter(self):
        it = self.liste.currentItem()
        if not it or self.tache is not None:
            return
        from . import assistant as A
        p, params = self.ed.projet, self.ed.params
        self.b_monter.setEnabled(False)
        self.barre.setValue(0)
        self.barre.show()
        self._choix = (it.data(Qt.UserRole), self.duree.value(), self.format.currentData())
        self.tache = Tache(lambda t: A.preparer(p, params, progression=lambda f, txt: t.avancer(f * 0.95, _("Analyse : {n}", n=txt))),
                           _("Modèle de montage"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("Analyse des rushes pour le modèle"))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)), Qt.QueuedConnection)
        self.tache.fini.connect(self._analyse, Qt.QueuedConnection)
        self.tache.start()

    def _analyse(self, r, err):
        try:
            self.tache = None
            self.barre.hide()
            self.b_monter.setEnabled(True)
            if err:
                self.etat.setText(_("✕ Analyse impossible : {e}", e=str(err)[:300]))
                return
            k, duree, fmt = self._choix
            rec = MM.appliquer(self.ed.projet, k, self.ed.params, duree, fmt)
            self.ed.biblio.remplir(self.ed.projet)
            self.ed.rafraichir()
            self.ed.encart.message(_("Montage « {m} » posé : {r}. Ctrl+Z revient en arrière.", m=MM.tous(self.ed.params)[k]["nom"],
                                     r=rec.get("resume", "")), 9000)
            self.resultat = rec
            self.accept()
        except RuntimeError:
            pass
