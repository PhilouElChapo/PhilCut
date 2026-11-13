"""Fenêtre « Prolonger ce plan » (0.9.24) : durée à ajouter, au début ou à la fin, manière (image tenue, ralenti, IA),
son ; on regarde le résultat avant de le poser."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from . import prolonger as PR
from .langue import _
from .taches import Tache
from .taches import texte_erreur


class DialogueProlonger(QDialog):
    def __init__(self, ed, clip):
        super().__init__(ed)
        self.ed, self.clip, self.resultat, self.tache = ed, clip, None, None
        self.setWindowTitle(_("Prolonger ce plan"))
        self.resize(640, 560)
        v = QVBoxLayout(self)
        t = QLabel(_("Un plan un peu trop court ? PhilCut fabrique quelques secondes de plus, posées juste après (ou juste avant) ; "
                     "la suite du montage est décalée. Regardez le résultat avant de le poser ; Ctrl+Z l'enlève."))
        t.setWordWrap(True)
        v.addWidget(t)
        f = QFormLayout()
        self.duree = QDoubleSpinBox()
        self.duree.setRange(0.5, 6.0)
        self.duree.setSingleStep(0.5)
        self.duree.setValue(2.0)
        self.duree.setSuffix(" s")
        f.addRow(_("Durée ajoutée"), self.duree)
        self.cote = QComboBox()
        self.cote.addItem(_("A la fin du plan"), "fin")
        self.cote.addItem(_("Au début du plan"), "debut")
        f.addRow(_("Où"), self.cote)
        self.methode = QComboBox()
        from . import packs_ia
        ia_ok = bool(packs_ia.modele_actif("video", ed.params))
        for k, lib in PR.METHODES.items():
            self.methode.addItem(lib if (k != "ia" or ia_ok) else lib + "  " + _("(installez un modèle vidéo : Préférences › IA locale)"), k)
        if not ia_ok:
            self.methode.model().item(2).setEnabled(False)
        f.addRow(_("Comment"), self.methode)
        self.son = QComboBox()
        for k, lib in PR.SONS.items():
            self.son.addItem(lib, k)
        f.addRow(_("Son"), self.son)
        v.addLayout(f)
        h = QHBoxLayout()
        self.b_fabriquer = QPushButton(_("Fabriquer"))
        self.b_fabriquer.setDefault(True)
        self.b_fabriquer.clicked.connect(self.fabriquer)
        h.addWidget(self.b_fabriquer)
        self.b_poser = QPushButton(_("Poser dans le film"))
        self.b_poser.setEnabled(False)
        self.b_poser.clicked.connect(self.poser)
        h.addWidget(self.b_poser)
        h.addStretch(1)
        v.addLayout(h)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        self.apercu.hide()
        v.addWidget(self.apercu, 1)

    def fabriquer(self):
        p = self.ed.projet
        media = p.media(self.clip["media"])
        if not media or not os.path.exists(media.get("chemin", "")):
            self.etat.setText(_("Le rush de ce plan est introuvable."))
            return
        args = dict(media=media, clip=dict(self.clip), duree=self.duree.value(), methode=self.methode.currentData(), cote=self.cote.currentData(),
                    son=self.son.currentData(), taille=p.taille, cadence=p.cadence, params=self.ed.params)
        self.b_fabriquer.setEnabled(False)
        self.b_poser.setEnabled(False)
        self.apercu.arreter()
        self.barre.setValue(0)
        self.barre.show()
        self.tache = Tache(lambda t: PR.fabriquer(progression=t.avancer, arret=t.arret_demande, **args), _("Prolonger un plan"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("Prolonger un plan"))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)), Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self.tache.start()

    def _fini(self, r, err):
        try:
            self.b_fabriquer.setEnabled(True)
            self.barre.hide()
            if err:
                self.etat.setText(_("✕ Prolongement impossible : {e}", e=texte_erreur(err)[:300]))
                return
            self.resultat = r
            self.apercu.charger(r, video=True)
            self.apercu.show()
            self.b_poser.setEnabled(True)
            self.etat.setText(_("Regardez le prolongement ; s'il convient, « Poser dans le film », sinon changez la manière et refabriquez."))
        except RuntimeError:
            pass

    def poser(self):
        if not self.resultat:
            return None
        self.apercu.arreter()
        p = self.ed.projet
        p.marquer()
        ci = PR.poser(p, self.clip, self.resultat, self.cote.currentData(), _("{n} (prolongé)", n=self.clip.get("nom", "")))
        self.ed.biblio.remplir(p)
        self.ed.rafraichir()
        if ci:
            self.ed.encart.message(_("Plan prolongé de {d:.1f} s ; la suite est décalée (Ctrl+Z pour revenir).", d=self.duree.value()), 6000)
        self.accept()
        return ci

    def done(self, r):
        self.apercu.arreter()
        super().done(r)
