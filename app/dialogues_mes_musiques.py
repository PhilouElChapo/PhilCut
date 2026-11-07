"""Mes musiques (0.9.0) : fenêtre qui remplace l'ancien sous-menu, devenu illisible avec beaucoup de morceaux.

Recherche instantanée (titre, artiste, album, dossier), classement au choix (retenu), groupes repliables, écoute,
« Poser sous la vidéo » ou double-clic. Le dossier est parcouru en tâche de fond et les étiquettes inconnues sont lues
en arrière-plan : jamais de gel, même sur un disque réseau.
"""
import os

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from . import musiques as MU
from .langue import _
from .taches import Tache


def _duree(d):
    d = float(d or 0)
    return f"{int(d // 60)}:{int(d % 60):02d}" if d else ""


class DialogueMesMusiques(QDialog):
    def __init__(self, parent, params):
        super().__init__(parent)
        self.params = params
        self.chemin = None
        self.liste = []
        self.lecteur = None
        self.tache = None
        self.setWindowTitle(_("Mes musiques"))
        self.resize(900, 620)
        v = QVBoxLayout(self)
        hd = QHBoxLayout()
        self.lbl_dossier = QLabel("")
        self.lbl_dossier.setWordWrap(True)
        hd.addWidget(self.lbl_dossier, 1)
        self.b_dossier = QPushButton("")
        self.b_dossier.clicked.connect(self.choisir_dossier)
        hd.addWidget(self.b_dossier)
        v.addLayout(hd)
        hr = QHBoxLayout()
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(_("Chercher un titre, un artiste, un album ou un dossier…"))
        self.cherche.setClearButtonEnabled(True)
        self.cherche.textChanged.connect(lambda _t: self._delai.start())
        hr.addWidget(self.cherche, 1)
        hr.addWidget(QLabel(_("Classer")))
        self.classement = QComboBox()
        for k, lib in MU.CLASSEMENTS:
            self.classement.addItem(lib, k)
        self.classement.setCurrentIndex(max(0, self.classement.findData(self.params.get("musiques_classement", "dossier"))))
        self.classement.currentIndexChanged.connect(self._classement_change)
        hr.addWidget(self.classement)
        v.addLayout(hr)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderLabels([_("Titre"), _("Artiste"), _("Album"), _("Durée")])
        self.arbre.setRootIsDecorated(True)
        self.arbre.setUniformRowHeights(True)
        self.arbre.setContextMenuPolicy(Qt.CustomContextMenu)
        self.arbre.customContextMenuRequested.connect(self._menu)
        self.arbre.itemDoubleClicked.connect(lambda it, _c: self.poser(it))
        self.arbre.currentItemChanged.connect(lambda *_a: self._boutons())
        h = self.arbre.header()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in (1, 2):
            h.setSectionResizeMode(c, QHeaderView.Interactive)
            self.arbre.setColumnWidth(c, 180)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.arbre.setWordWrap(False)
        self.arbre.setTextElideMode(Qt.ElideNone)
        v.addWidget(self.arbre, 1)
        hb = QHBoxLayout()
        self.b_ecouter = QPushButton("▶ " + _("Écouter"))
        self.b_ecouter.clicked.connect(self.ecouter)
        hb.addWidget(self.b_ecouter)
        self.b_stop = QPushButton("■ " + _("Arrêter l'écoute"))
        self.b_stop.clicked.connect(self._stop)
        self.b_stop.hide()
        hb.addWidget(self.b_stop)
        hb.addStretch(1)
        self.b_poser = QPushButton(_("Poser sous la vidéo"))
        self.b_poser.setStyleSheet("font-weight:600;padding:6px 16px")
        self.b_poser.clicked.connect(lambda: self.poser(self.arbre.currentItem()))
        hb.addWidget(self.b_poser)
        b_fermer = QPushButton(_("Fermer"))
        b_fermer.clicked.connect(self.reject)
        hb.addWidget(b_fermer)
        v.addLayout(hb)
        self.etat = QLabel("")            # barre d'information du bas : ce qui se passe
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.etat)
        self._delai = QTimer(self)
        self._delai.setSingleShot(True)
        self._delai.setInterval(180)
        self._delai.timeout.connect(self.remplir)
        self._veille = QTimer(self)            # fin de la lecture des étiquettes en arrière-plan : on rafraîchit
        self._veille.setInterval(1500)
        self._veille.timeout.connect(self._veiller)
        self._dossier_txt()
        self._boutons()
        self.charger()

    # ---- dossier et parcours
    def _perso(self):
        return self.params.get("musiques_dossier") or ""

    def _dossier_txt(self):
        perso = self._perso()
        self.lbl_dossier.setText(_("Dossier : {d}  (et les musiques libres téléchargées)", d=perso) if perso else
                                 _("Aucun dossier de musiques choisi : seules les musiques libres téléchargées sont listées."))
        self.b_dossier.setText(_("Changer de dossier…") if perso else _("Choisir mon dossier de musiques…"))

    def choisir_dossier(self):
        from .session import dossier_systeme
        d = QFileDialog.getExistingDirectory(self, _("Mon dossier de musiques"), self._perso() or dossier_systeme("musique"))
        if d:
            self.params["musiques_dossier"] = d
            self.params.enregistrer()
            self._dossier_txt()
            self.charger()

    def charger(self):
        if self.tache is not None and self.tache.isRunning():
            return
        self.etat.setText(_("Recherche des morceaux…"))
        perso, params = self._perso(), self.params
        # tout ce qui touche au disque (dossier réseau, NAS endormi) se fait en tâche de fond : la fenêtre ne gèle jamais
        self.tache = Tache(lambda t: MU.morceaux([perso, MU.dossier(params)], limite=20000, rapide=True, delai=20.0), _("Mes musiques"))
        self.tache.fini.connect(self._charge, Qt.QueuedConnection)
        self.tache.start()

    def _charge(self, liste, err):
        if err:
            self.etat.setText(_("✕ {e}", e=str(err)[:300]))
            return
        self.liste = liste or []
        n = MU.lire_en_fond(self.liste)
        self.remplir()
        if n:
            self.etat.setText(_("{t} morceau(x). Lecture des titres, artistes et albums de {n} morceau(x) en arrière-plan : "
                                "la liste se complète toute seule.", t=len(self.liste), n=n))
            self._veille.start()

    def _veiller(self):
        """Pendant la lecture des étiquettes : l'avancement en bas, et la liste mise à jour toutes les 6 s (sans perdre le
        groupe ouvert ni le morceau choisi) ; à la fin, une dernière fois."""
        fil = MU._LECTURE.get("fil")
        fini = fil is None or not fil.is_alive()
        self._tours = getattr(self, "_tours", 0) + 1
        if fini or self._tours % 4 == 0:
            ouverts = {self.arbre.topLevelItem(i).text(0).rsplit("  (", 1)[0] for i in range(self.arbre.topLevelItemCount())
                       if self.arbre.topLevelItem(i).isExpanded()}
            choisi = self._chemin()
            self.liste = [dict(MU.etiquettes(m["chemin"], lire=False), chemin=m["chemin"], dossier=m.get("dossier", "")) for m in self.liste]
            self.remplir()
            for i in range(self.arbre.topLevelItemCount()):
                it = self.arbre.topLevelItem(i)
                if it.text(0).rsplit("  (", 1)[0] in ouverts:
                    it.setExpanded(True)
                    for j in range(it.childCount()):
                        if choisi and it.child(j).data(0, Qt.UserRole) == choisi:
                            self.arbre.setCurrentItem(it.child(j))
        if fini:
            self._veille.stop()
            self.etat.setText(_("{t} morceau(x), titres, artistes et albums lus. Double-clic, ou « Poser sous la vidéo », pour le mettre "
                                "sur la piste Musique.", t=len(self.liste)))
        else:
            self.etat.setText(_("Lecture des étiquettes (titre, artiste, album, n° de piste) : {f} / {n}. La liste se complète toute seule.",
                                f=MU._LECTURE.get("faits", 0), n=MU._LECTURE.get("total", 0)))

    # ---- liste
    def _classement_change(self):
        self.params["musiques_classement"] = self.classement.currentData()
        self.params.enregistrer()
        self.remplir()

    def _filtre(self):
        mots = [m for m in self.cherche.text().lower().split() if m]
        if not mots:
            return self.liste
        def garde(m):
            txt = " ".join(str(m.get(k) or "") for k in ("titre", "artiste", "album", "dossier")).lower() + " " + os.path.basename(m["chemin"]).lower()
            return all(x in txt for x in mots)
        return [m for m in self.liste if garde(m)]

    def remplir(self):
        self.arbre.setUpdatesEnabled(False)
        self.arbre.clear()
        liste = self._filtre()
        groupes = MU.classer(liste, self.classement.currentData())
        cherche = bool(self.cherche.text().strip())
        plat = len(groupes) == 1
        for g, ms in groupes:
            parent = None
            if not plat:
                parent = QTreeWidgetItem(self.arbre, [f"{g}  ({len(ms)})"])
                parent.setFirstColumnSpanned(True)
                f = parent.font(0)
                f.setBold(True)
                parent.setFont(0, f)
                parent.setFlags(Qt.ItemIsEnabled)
            for m in ms:
                it = QTreeWidgetItem([m.get("titre") or os.path.basename(m["chemin"]), m.get("artiste") or "", m.get("album") or "", _duree(m.get("duree"))])
                it.setData(0, Qt.UserRole, m["chemin"])
                it.setToolTip(0, m["chemin"])
                (parent.addChild(it) if parent else self.arbre.addTopLevelItem(it))
            if parent and (cherche or len(groupes) <= 3):
                parent.setExpanded(True)
        self.arbre.setUpdatesEnabled(True)
        if not self.liste:
            self.etat.setText(_("Aucun morceau : choisissez votre dossier de musiques, ou téléchargez des musiques libres (Bibliothèque musicale)."))
        elif cherche:
            self.etat.setText(_("{n} morceau(x) trouvé(s) sur {t}.", n=len(liste), t=len(self.liste)))
        elif not (self.tache is not None and self._veille.isActive()):
            self.etat.setText(_("{t} morceau(x). Double-clic, ou « Poser sous la vidéo », pour le mettre sur la piste Musique ; "
                                "clic droit pour écouter.", t=len(self.liste)))
        self._boutons()

    def _chemin(self, it=None):
        it = it if it is not None else self.arbre.currentItem()
        return it.data(0, Qt.UserRole) if it is not None else None

    def _boutons(self):
        ok = bool(self._chemin())
        self.b_poser.setEnabled(ok)
        self.b_ecouter.setEnabled(ok)

    def _menu(self, pos):
        it = self.arbre.itemAt(pos)
        p = self._chemin(it)
        if not p:
            return
        self.arbre.setCurrentItem(it)
        m = QMenu(self)
        m.addAction(_("Poser sous la vidéo"), lambda: self.poser(it))
        m.addAction("▶ " + _("Écouter"), self.ecouter)
        if self.lecteur is not None:
            m.addAction("■ " + _("Arrêter l'écoute"), self._stop)
        m.addSeparator()
        m.addAction(_("Ouvrir le dossier du morceau"), lambda: self._ouvrir(os.path.dirname(p)))
        m.exec(self.arbre.viewport().mapToGlobal(pos))

    def _ouvrir(self, d):
        import pathlib, webbrowser
        webbrowser.open(pathlib.Path(d).resolve().as_uri())

    # ---- écoute et pose
    def ecouter(self):
        p = self._chemin()
        if not p:
            return
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":     # tests automatiques : pas de carte son
            self.etat.setText(_("▶ Écoute : {t}", t=self.arbre.currentItem().text(0)))
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            self.etat.setText(_("Ecoute impossible sur ce poste."))
            return
        if self.lecteur is None:
            self.lecteur = QMediaPlayer(self)
            self.sortie = QAudioOutput(self)
            self.lecteur.setAudioOutput(self.sortie)
        self.lecteur.setSource(QUrl.fromLocalFile(p))
        self.lecteur.play()
        self.b_stop.show()
        self.etat.setText(_("▶ Écoute : {t}", t=self.arbre.currentItem().text(0)))

    def _stop(self):
        if self.lecteur is not None:
            self.lecteur.stop()
        self.b_stop.hide()
        self.etat.setText(_("Écoute arrêtée."))

    def poser(self, it):
        p = self._chemin(it)
        if not p:
            return
        self.chemin = p
        if self.lecteur is not None:
            self.lecteur.stop()
        self.accept()

    def done(self, r):
        if self.lecteur is not None:
            self.lecteur.stop()
        self._veille.stop()
        super().done(r)
