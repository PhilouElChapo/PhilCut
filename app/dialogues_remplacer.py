"""1.0.5 : fenêtre « Remplacer un élément de l'image par un de ma bibliothèque » (non bloquante, une par plan)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QProgressBar, QPushButton, QVBoxLayout, QWidget)

from . import remplacer_element as R
from .langue import _
from .taches import Tache, texte_erreur


class DialogueRemplacer(QDialog):
    def __init__(self, ed, clip):
        super().__init__(ed)
        from .cartes_assistant import ImageCadres
        from .credit_ia import LigneCredit
        self.ed, self.clip, self.params = ed, clip, ed.params
        self.zone, self.resultat, self.tache = None, "", None
        self.setWindowTitle(_("Remplacer un élément de l'image par un de ma bibliothèque"))
        self.source = self._image_source()
        v = QVBoxLayout(self)
        aide = QLabel(_("Tracez sur l'image un cadre autour de ce qui doit disparaître, dites ce que c'est, choisissez dans votre "
                        "bibliothèque ce qui le remplace. Le reste de l'image (personnes, décor, lumière) ne change pas. Vous "
                        "regardez le résultat avant de le poser."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        h = QHBoxLayout()
        gauche = QVBoxLayout()
        self.image = ImageCadres(self.source, 440)
        self.image.trace.connect(self._zone)
        gauche.addWidget(self.image)
        self.l_zone = QLabel(_("Tracez le cadre de ce qui doit disparaître (prenez-le entier, avec un peu de marge)."))
        self.l_zone.setWordWrap(True)
        gauche.addWidget(self.l_zone)
        gauche.addStretch(1)
        h.addLayout(gauche)
        droite = QVBoxLayout()
        f = QFormLayout()
        self.quoi = QLineEdit()
        self.quoi.setPlaceholderText(_("ex. : la voiture rouge, le panneau, l'avion blanc"))
        f.addRow(_("Ce qui disparaît"), self.quoi)
        self.choix = QComboBox()
        self.choix.setIconSize(QPixmap(48, 48).size())
        for e in R.entrees(self.params):
            from . import bibliotheque_creations as B
            self.choix.addItem(QIcon(B.apercu(e)), f"{e['nom']} ({B.GENRES.get(e['genre'], (e['genre'],))[0]})", e)
        f.addRow(_("Ce qui le remplace"), self.choix)
        droite.addLayout(f)
        self.vignette = QLabel()
        self.vignette.setFixedHeight(130)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        droite.addWidget(self.vignette)
        droite.addWidget(self.desc)
        self.accord = QCheckBox(_("Les personnes de l'image sont d'accord pour qu'elle soit modifiée par l'IA (ou c'est moi)"))
        self.accord.setToolTip(_("L'image est envoyée à Gemini avec votre clef : seulement avec l'accord des personnes qu'on y voit"))
        droite.addWidget(self.accord)
        self.prix = QLabel(_("Gemini (votre clef) : environ {p} $ par essai.", p=f"{R.PRIX:.2f}".replace(".", ",")))
        droite.addWidget(self.prix)
        self.credit = LigneCredit(self.params, "google", self, compact=True)
        droite.addWidget(self.credit)
        self.b_go = QPushButton(_("Remplacer (environ {p} $)", p=f"{R.PRIX:.2f}".replace(".", ",")))
        self.b_go.clicked.connect(self.lancer)
        droite.addWidget(self.b_go)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        droite.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        droite.addWidget(self.etat)
        self.apres = QLabel()
        droite.addWidget(self.apres)
        droite.addStretch(1)
        h.addLayout(droite, 1)
        v.addLayout(h)
        hb = QHBoxLayout()
        image_plan = (self.ed.projet.media(clip.get("media")) or {}).get("genre") == "image"
        self.b_poser = QPushButton(_("Poser à la place de l'image") if image_plan else _("Insérer l'image à la ligne rouge"))
        self.b_poser.clicked.connect(self.poser)
        self.b_poser.setEnabled(False)
        self.b_garder = QPushButton(_("Garder dans les médias"))
        self.b_garder.clicked.connect(self.garder)
        self.b_garder.setEnabled(False)
        b_fermer = QPushButton(_("Fermer"))
        b_fermer.clicked.connect(self.close)
        hb.addWidget(self.b_poser)
        hb.addWidget(self.b_garder)
        hb.addStretch(1)
        hb.addWidget(b_fermer)
        v.addLayout(hb)
        self.image_plan = image_plan
        for w in (self.quoi.textChanged, self.accord.toggled):
            w.connect(self._maj)
        self.choix.currentIndexChanged.connect(self._entree)
        self._entree()
        if not self.choix.count():
            self.etat.setText(_("Votre bibliothèque n'a encore aucun élément avec une image : Fabrique IA › « Ma bibliothèque de "
                                "créations… » pour en créer un."))

    def _image_source(self):
        p = self.ed.projet
        m = p.media(self.clip.get("media")) or {}
        if m.get("genre") == "image" and os.path.exists(m.get("chemin") or ""):
            return m["chemin"]
        from .cartes_assistant import image_ligne_rouge
        return image_ligne_rouge(self.ed)

    def _zone(self, b):
        self.zone = b
        self.image.cadres = [(1, "#E53935", b)]
        self.image.actif = 0
        self.image.update()
        self.l_zone.setText(_("Cadre tracé ; tracez-en un autre pour le corriger."))
        self._maj()

    def _entree(self):
        e = self.choix.currentData()
        if e:
            from . import bibliotheque_creations as B
            pm = QPixmap(B.apercu(e))
            if not pm.isNull():
                self.vignette.setPixmap(pm.scaledToHeight(124, Qt.SmoothTransformation))
            self.desc.setText(e.get("description") or "")
        self._maj()

    def _maj(self):
        pret = bool(self.source and self.zone and self.quoi.text().strip() and self.choix.currentData() and self.accord.isChecked())
        self.b_go.setEnabled(pret and not (self.tache and self.tache.isRunning()))

    def lancer(self):
        if not getattr(self, "_test_oui", False) and QMessageBox.question(
                self, self.windowTitle(), _("Envoyer l'image à Gemini (votre clef) pour remplacer « {q} » par « {n} » : environ "
                                            "{p} $ ?", q=self.quoi.text().strip(), n=self.choix.currentData()["nom"],
                                            p=f"{R.PRIX:.2f}".replace(".", ","))) != QMessageBox.Yes:
            return
        args = (self.params, self.source, list(self.zone), self.quoi.text(), self.choix.currentData())
        self.b_go.setEnabled(False)
        self.barre.setValue(0)
        self.barre.show()
        self.etat.setText(_("Gemini prépare l'image…"))
        self.tache = Tache(lambda t: R.remplacer(*args, progression=t.avancer), _("Remplacer un élément de l'image"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("Remplacer un élément de l'image"))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self.tache.start()

    def _fini(self, r, err):
        try:
            self.barre.hide()
            self._maj()
            self.credit.montrer("google")
            if err:
                self.etat.setText(_("✕ Remplacement impossible : {e}", e=texte_erreur(err)[:300]))
                return
            self.resultat = r
            pm = QPixmap(r)
            self.apres.setPixmap(pm.scaled(440, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.b_poser.setEnabled(True)
            self.b_garder.setEnabled(True)
            self.b_go.setText(_("Refaire (environ {p} $)", p=f"{R.PRIX:.2f}".replace(".", ",")))
            self.etat.setText(_("Regardez le résultat : s'il convient, posez-le ; sinon corrigez le cadre ou le texte et refaites."))
        except RuntimeError:
            pass

    def poser(self):
        if not self.resultat:
            return False
        if self.image_plan:
            ok = self.ed.remplacer_media_clip(self.clip["id"], self.resultat)
        else:
            ok = bool(self.ed.inserer_image(self.resultat, self.ed.timeline.position, nom=os.path.basename(self.resultat)))
        if ok:
            self.close()
        return ok

    def garder(self):
        if self.resultat:
            from . import moteur
            self.ed.projet.ajouter_media(self.resultat, moteur.sonder(self.resultat))
            self.ed.biblio.remplir(self.ed.projet)
            self.ed.encart.message(_("Image gardée dans les médias du projet."), 5000)

    def done(self, r):
        from .widgets import calcul_en_cours, garder_calcul
        if garder_calcul(self, calcul_en_cours(self)):
            return
        super().done(r)
