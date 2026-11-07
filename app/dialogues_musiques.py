"""Bibliothèque musicale libre : chercher par ambiance ou mots, écouter, télécharger et poser sous la vidéo. Les
licences proposées autorisent une vidéo publiée (même monétisée) ; le crédit est préparé pour la description."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QComboBox, QLabel, QTreeWidget, QTreeWidgetItem,
                               QDialogButtonBox, QHeaderView)

from . import musiques as MU
from .langue import _
from .taches import Tache
from .widgets import boutons_fr

_EN_ROUTE = []


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
        self.texte.setPlaceholderText(_("Dans votre langue (traduit en anglais) : « coucher de soleil », « piano », « épique »…"))
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
        self.b_chercher = QPushButton(_("Chercher"))
        self.b_chercher.clicked.connect(self.chercher)
        self.b_arret = QPushButton(_("■ Arrêter la recherche"))
        self.b_arret.clicked.connect(self.arreter_recherche)
        self.b_arret.hide()
        h.addWidget(self.texte, 1)
        h.addWidget(self.ambiance)
        h.addWidget(self.longueur)
        h.addWidget(self.b_chercher)
        h.addWidget(self.b_arret)
        v.addLayout(h)
        hd = QHBoxLayout()
        self.lbl_dossier = QLabel("")
        self.lbl_dossier.setWordWrap(True)
        hd.addWidget(self.lbl_dossier, 1)
        b_d = QPushButton(_("Changer de dossier…"))
        b_d.setToolTip(_("Où ranger les musiques téléchargées (retenu pour la prochaine fois)."))
        b_d.clicked.connect(self.changer_dossier)
        hd.addWidget(b_d)
        b_o = QPushButton(_("Ouvrir le dossier"))
        b_o.clicked.connect(lambda: __import__("PySide6.QtGui", fromlist=["QDesktopServices"]).QDesktopServices.openUrl(QUrl.fromLocalFile(MU.dossier(self.params))))
        hd.addWidget(b_o)
        v.addLayout(hd)
        self._montrer_dossier()
        self.liste = QTreeWidget()
        self.liste.setHeaderLabels([_("Titre"), _("Auteur"), _("Durée"), _("Licence"), _("Source")])
        hdr = self.liste.header()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        for i, w in enumerate((330, 170, 60, 90, 110)):
            self.liste.setColumnWidth(i, w)
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

    def _montrer_dossier(self):
        self.lbl_dossier.setText(_("Dossier de téléchargement : {d}", d=MU.dossier(self.params, creer=False)))

    def changer_dossier(self):
        from PySide6.QtWidgets import QFileDialog
        d = QFileDialog.getExistingDirectory(self, _("Dossier des musiques téléchargées"), MU.dossier(self.params, creer=False))
        if d:
            self.params["musiques_telechargement"] = d
            try:
                self.params.enregistrer()
            except AttributeError:
                pass
            self._montrer_dossier()

    def chercher(self):
        self.etat.setText(_("Recherche… (« Arrêter la recherche » pour l'abandonner)"))
        texte, amb, lg = self.texte.text(), self.ambiance.currentData(), self.longueur.currentData()
        self._numero = getattr(self, "_numero", 0) + 1
        n = self._numero
        def travail(tache):
            from . import traduction_recherche as TR
            tr = TR.en_anglais(texte)
            return MU.chercher(tr[0], amb, lg), TR.message(texte, tr)
        t = Tache(travail, _("Musique"))
        self.taches.append(t)
        t.fini.connect(lambda r, e, n=n: self._resultats(r, e) if n == self._numero else None)
        self.b_chercher.hide()
        self.b_arret.show()
        t.start()

    def arreter_recherche(self):
        """La réponse en route sera ignorée ; on peut relancer une autre recherche tout de suite."""
        self._numero = getattr(self, "_numero", 0) + 1
        self.b_arret.hide()
        self.b_chercher.show()
        self.etat.setText(_("Recherche arrêtée."))

    def _resultats(self, res, err):
        res, note = res if isinstance(res, tuple) else (res, "")
        self.b_arret.hide()
        self.b_chercher.show()
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
        self.etat.setText((_("{n} morceau(x). Double-clic pour écouter.", n=len(res)) if res else _("Rien trouvé : essayez d'autres mots (en anglais)."))
                          + ("  " + note if note else ""))

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
        self._numero = getattr(self, "_numero", 0) + 1
        for t in self.taches:
            if not t.wait(1500):
                _EN_ROUTE.append(t)          # une recherche abandonnée finit seule, sans bloquer la fenêtre
                t.fini.connect(lambda *_a, t=t: _EN_ROUTE.remove(t) if t in _EN_ROUTE else None)
        super().done(r)
