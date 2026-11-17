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
        from . import generateurs_video as GV
        if not GV.clef(ed.params, "fal"):
            i = self.methode.findData("cloud")
            self.methode.setItemText(i, self.methode.itemText(i) + "  " + _("(clef fal.ai : Préférences › IA)"))
            self.methode.model().item(i).setEnabled(False)
        self.methode.currentIndexChanged.connect(self._methode_changee)
        f.addRow(_("Comment"), self.methode)
        ba = QPushButton(_("Une vraie suite avec des personnages ? Mode assisté…"))
        ba.setToolTip(_("L'assistant prépare les fiches des personnes, découpe en plans, montre les images avant la vidéo et relit"))
        ba.clicked.connect(lambda: (ed.assistant_creation(self.clip), self.close()))
        f.addRow("", ba)
        from .consigne_bilingue import ConsigneBilingue
        self.suite = ConsigneBilingue(50)
        self.suite.setPlaceholderText(_("Facultatif : ce qui se passe ensuite (ex. : elle ouvre l'ordinateur et sourit)"))
        self.lbl_suite = QLabel(_("Suite"))
        f.addRow(self.lbl_suite, self.suite)
        self.prix = QLabel("")
        self.prix.setWordWrap(True)
        f.addRow("", self.prix)
        from .credit_ia import LigneCredit
        self.credit = LigneCredit(ed.params, None)
        f.addRow("", self.credit)
        self.duree.valueChanged.connect(lambda _v: self._methode_changee())
        self.suite.textChanged.connect(lambda: self._methode_changee())
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
        self._methode_changee()

    def _methode_changee(self, *_a):
        cloud = self.methode.currentData() == "cloud"
        self.duree.setMaximum(60.0 if cloud else 6.0)
        self.suite.setVisible(cloud)
        self.lbl_suite.setVisible(cloud)
        self.prix.setVisible(cloud)
        if hasattr(self, "credit") and (self.credit.fournisseur == "fal") != cloud:
            self.credit.montrer("fal" if cloud else None)
        if cloud:
            et = self._etapes()
            lignes = "".join(f"<br>{k + 1}. {fr} ({str(dk).replace('.', ',')} s)" for k, (_en, dk, fr) in enumerate(et))
            self.prix.setText(_("PhilCut fera {n} étape(s), une action chacune, enchaînées seules (chaque étape part de la dernière image "
                                "de la précédente) :", n=len(et)) + lignes + "<br>" +
                              _("En tout {d} s, environ {p} $ (votre clef fal.ai), demandé avant l'envoi. Décrivez toute la suite "
                                "d'un coup, avec « puis » entre les actions.", d=str(round(sum(x[1] for x in et), 1)).replace(".", ","),
                                p=f"{PR.prix_etapes(et, self.ed.params):.2f}".replace(".", ",")))

    def _etapes(self):
        src = getattr(self.suite, "source", None)
        return PR.etapes_suite(self.suite.toPlainText(), self.duree.value(), src.toPlainText() if src is not None else "")

    def fabriquer(self):
        p = self.ed.projet
        etapes = None
        if self.methode.currentData() == "cloud":
            from PySide6.QtWidgets import QMessageBox
            etapes = self._etapes()
            prix = f"{PR.prix_etapes(etapes, self.ed.params):.2f}".replace(".", ",")
            photo = (p.media(self.clip["media"]) or {}).get("genre") == "image"
            if getattr(self, "_test_confirmer", None) is None and QMessageBox.question(
                    self, _("Prolonger ce plan"),
                    (_("Envoyer la photo (point de départ et modèle des personnes) et la consigne à fal.ai (Kling O3) pour {n} étape(s), "
                       "environ {p} $ sur votre compte ?", n=len(etapes), p=prix) if photo else
                     _("Envoyer à fal.ai (Kling O3) la dernière image du plan (point de départ) et deux autres images du plan (le "
                       "début et le milieu, pour que le moteur connaisse les personnes sous plusieurs angles), avec la consigne : {n} "
                       "étape(s), environ {p} $ sur votre compte ?", n=len(etapes), p=prix))) != QMessageBox.Yes:
                return
        media = p.media(self.clip["media"])
        if not media or not os.path.exists(media.get("chemin", "")):
            self.etat.setText(_("Le rush de ce plan est introuvable."))
            return
        args = dict(media=media, clip=dict(self.clip), duree=self.duree.value(), methode=self.methode.currentData(), cote=self.cote.currentData(),
                    son=self.son.currentData(), taille=p.taille, cadence=p.cadence, params=self.ed.params,
                    suite=self.suite.toPlainText() if self.methode.currentData() == "cloud" else "", etapes=etapes)
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
        from .widgets import calcul_en_cours, garder_calcul
        if garder_calcul(self, calcul_en_cours(self)):         # 0.9.68 : rangée, le calcul continue
            return
        self.apercu.arreter()
        super().done(r)
