"""Bibliothèque musicale libre : chercher par ambiance ou mots, écouter, télécharger et poser sous la vidéo. Les
licences proposées autorisent une vidéo publiée (même monétisée) ; le crédit est préparé pour la description."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QComboBox, QLabel, QTreeWidget, QTreeWidgetItem,
                               QDialogButtonBox, QHeaderView)

from . import musiques as MU
from .langue import _
from .taches import Tache
from .widgets import boutons_fr


class DialogueMusiques(QDialog):
    def __init__(self, parent, params, ambiance=None):
        super().__init__(parent)
        self.setWindowTitle(_("Bibliothèque musicale libre"))
        self.resize(860, 560)
        self.params = params
        self.taches = []
        self.chemin = None
        self.morceau = None
        self.lecteur = None
        v = QVBoxLayout(self)
        intro = QLabel(_("Musiques sous licence Creative Commons (Jamendo, ccMixter, Freesound…, via Openverse) : seulement celles qu'on peut "
                         "utiliser dans une vidéo publiée, même monétisée. Le crédit de l'auteur est préparé et ajouté à la description lors de la publication."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        h = QHBoxLayout()
        self.texte = QLineEdit()
        self.texte.setPlaceholderText(_("Mots en anglais de préférence : « drone », « sunset », « piano »…"))
        self.texte.returnPressed.connect(self.chercher)
        self.ambiance = QComboBox()
        self.ambiance.addItem(_("Toutes ambiances"), None)
        for k, lib, _m in MU.AMBIANCES:
            self.ambiance.addItem(lib, k)
        if ambiance:
            self.ambiance.setCurrentIndex(max(0, self.ambiance.findData(ambiance)))
        self.longueur = QComboBox()
        for k, lib in ((None, _("Toutes durées")), ("short", _("Courte (< 30 s)")), ("medium", _("Moyenne (30 s à 2 min)")), ("long", _("Longue (> 2 min)"))):
            self.longueur.addItem(lib, k)
        b = QPushButton(_("Chercher"))
        b.clicked.connect(self.chercher)
        h.addWidget(self.texte, 1)
        h.addWidget(self.ambiance)
        h.addWidget(self.longueur)
        h.addWidget(b)
        v.addLayout(h)
        self.liste = QTreeWidget()
        self.liste.setHeaderLabels([_("Titre"), _("Auteur"), _("Durée"), _("Licence"), _("Source")])
        self.liste.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.liste.setRootIsDecorated(False)
        self.liste.itemDoubleClicked.connect(lambda *_a: self.ecouter())
        v.addWidget(self.liste, 1)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hb = QHBoxLayout()
        self.b_ecouter = QPushButton(_("▶ Ecouter"))
        self.b_ecouter.clicked.connect(self.ecouter)
        b_stop = QPushButton(_("■ Stop"))
        b_stop.clicked.connect(self._stop)
        hb.addWidget(self.b_ecouter)
        hb.addWidget(b_stop)
        hb.addStretch(1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        self.b_ok = bb.button(QDialogButtonBox.Ok)
        self.b_ok.setText(_("Télécharger et poser sous la vidéo"))
        bb.accepted.connect(self.telecharger)
        bb.rejected.connect(self.reject)
        hb.addWidget(bb)
        v.addLayout(hb)

    def chercher(self):
        self.etat.setText(_("Recherche…"))
        texte, amb, lg = self.texte.text(), self.ambiance.currentData(), self.longueur.currentData()
        t = Tache(lambda tache: MU.chercher(texte, amb, lg), _("Musique"))
        self.taches.append(t)
        t.fini.connect(self._resultats)
        t.start()

    def _resultats(self, res, err):
        self.liste.clear()
        if err:
            self.etat.setText(_("✕ {e}", e=err))
            return
        for m in res:
            it = QTreeWidgetItem([m["titre"], m["auteur"], f"{int(m['duree'] // 60)}:{int(m['duree'] % 60):02d}" if m["duree"] else "?",
                                  m["licence"], m["source"]])
            it.setData(0, Qt.UserRole, m)
            it.setToolTip(0, m["attribution"] + ("\n" + ", ".join(m["tags"]) if m["tags"] else ""))
            self.liste.addTopLevelItem(it)
        self.etat.setText(_("{n} morceau(x). Double-clic pour écouter.", n=len(res)) if res else _("Rien trouvé : essayez d'autres mots (en anglais)."))

    def _courant(self):
        it = self.liste.currentItem()
        return it.data(0, Qt.UserRole) if it else None

    def ecouter(self):
        m = self._courant()
        if not m:
            return
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        except ImportError:
            self.etat.setText(_("Ecoute impossible sur ce poste : téléchargez pour écouter."))
            return
        if self.lecteur is None:
            self.lecteur = QMediaPlayer(self)
            self.sortie = QAudioOutput(self)
            self.lecteur.setAudioOutput(self.sortie)
        self.lecteur.setSource(QUrl(m["url"]))
        self.lecteur.play()
        self.etat.setText(_("▶ {t} — {a}", t=m["titre"], a=m["auteur"]))

    def _stop(self):
        if self.lecteur:
            self.lecteur.stop()

    def telecharger(self):
        m = self._courant()
        if not m:
            self.etat.setText(_("Choisissez d'abord un morceau."))
            return
        self._stop()
        self.b_ok.setEnabled(False)
        self.etat.setText(_("Téléchargement…"))
        t = Tache(lambda tache: MU.telecharger(m, self.params, progression=lambda f: tache.avancer(f)), _("Musique"))
        self.taches.append(t)
        t.fini.connect(lambda r, e: self._telecharge(m, r, e))
        t.start()

    def _telecharge(self, m, chemin, err):
        self.b_ok.setEnabled(True)
        if err:
            self.etat.setText(_("✕ {e}", e=err))
            return
        self.chemin, self.morceau = chemin, m
        self.accept()

    def done(self, r):
        self._stop()
        for t in self.taches:
            t.wait(20000)
        super().done(r)
