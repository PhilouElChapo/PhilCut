"""Fenêtre « Séquence IA » (0.9.33) : histoire → personnages et lieux → plans (consigne, image de départ, répliques)
→ fabrication plan par plan (IA de ce poste, générateur cloud avec votre clef, ou Google Flow pas à pas) → on regarde
→ « Monter la séquence » pose les plans, les répliques et la musique à la ligne rouge."""
import copy
import os
import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
                               QPushButton, QScrollArea, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget, QApplication)

from . import sequence_ia as Q
from .langue import _
from .taches import Tache
from .widgets import SuiviAttente

AIDE_FLOW = _(
    "<b>Avec Google Flow (votre abonnement)</b>, plan par plan :<br>"
    "1. « Copier pour Flow » : PhilCut met la consigne du plan dans le presse-papiers, ouvre Flow et le dossier des images "
    "de référence du plan.<br>"
    "2. Dans Flow : nouveau projet, puis le mode qui part d'images (« Ingrédients » ou « Images → vidéo » selon la version) ; "
    "glissez-y les images des personnages et du lieu depuis le dossier ouvert ; cliquez dans la zone de texte, <b>Ctrl+V</b>, "
    "puis la flèche pour générer.<br>"
    "3. Sur la vidéo réussie : <b>Télécharger</b>. PhilCut la repère dans vos Téléchargements, l'attache au plan et vous la "
    "montre.<br>"
    "Gardez les mêmes images de référence d'un plan à l'autre : c'est ce qui garde les personnages identiques.")


class DialogueSequence(QDialog):
    def __init__(self, ed, seq=None):
        super().__init__(ed)
        self.ed, self.params = ed, ed.params
        self.seq = copy.deepcopy(seq) if seq else Q.nouvelle(ed.projet.format)
        self.taches, self._courant = [], -1
        self.setWindowTitle(_("Séquence IA : une histoire en plusieurs plans"))
        self.resize(1080, 760)
        v = QVBoxLayout(self)
        intro = QLabel(_("Racontez une petite histoire ; PhilCut la découpe en plans, garde les mêmes personnages d'un plan à "
                         "l'autre (description constante et images de référence), fait dire les répliques avec la manière de parler "
                         "de chacun, puis monte le tout avec une musique. « A la manière de » décrit un style (allure, jeu, voix "
                         "posée), jamais un visage ni une voix copiée."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.onglets = QTabWidget()
        v.addWidget(self.onglets, 1)
        self._onglet_histoire()
        self._onglet_personnages()
        self._onglet_plans()
        # ---- bas : moteurs, musique, actions
        g = QGroupBox(_("Fabrication"))
        f = QFormLayout(g)
        self.moteur = QComboBox()
        self.moteur.addItem(_("Google Flow (votre abonnement, pas à pas)"), "flow")
        self.moteur.addItem(_("IA de ce poste (gratuite ; plans courts, lents à calculer)"), "locale")
        from . import generateurs_video as GV
        dispo = {m["id"] for m in GV.disponibles(self.params)}
        for m in GV.modeles(self.params):
            lib = _("Cloud : {n} — {p:.2f} $/s (votre clef)", n=m["nom"], p=m.get("prix_s", 0))
            self.moteur.addItem(lib, m["id"])
            if m["id"] not in dispo:
                self.moteur.model().item(self.moteur.count() - 1).setEnabled(False)
                self.moteur.setItemData(self.moteur.count() - 1, _("Clef à saisir : Fabrique › Plan généré par IA › Connecter une IA"),
                                        Qt.ToolTipRole)
        i = self.moteur.findData(self.seq.get("moteur"))
        self.moteur.setCurrentIndex(max(0, i))
        self.moteur.currentIndexChanged.connect(self._maj_moteur)
        f.addRow(_("Vidéo"), self.moteur)
        self.voix = QComboBox()
        self.voix.addItem(_("Voix de ce poste (gratuite)"), "local")
        self.voix.addItem(_("Voix Gemini (joue vraiment la phrase ; votre clef, payant)"), "gemini")
        self.voix.setCurrentIndex(max(0, self.voix.findData(self.seq.get("voix", "local"))))
        f.addRow(_("Répliques"), self.voix)
        hm = QHBoxLayout()
        self.musique = QCheckBox(_("Musique sous la séquence (IA de ce poste)"))
        self.musique.setChecked(bool(self.seq["musique"].get("active", True)))
        hm.addWidget(self.musique)
        self.phrase_musique = QLineEdit(self.seq["musique"].get("phrase", ""))
        self.phrase_musique.setPlaceholderText(_("ex. : jazz léger des années 60, guitare et cuivres"))
        hm.addWidget(self.phrase_musique, 1)
        f.addRow(_("Musique"), hm)
        self.prix = QLabel("")
        f.addRow(self.prix)
        v.addWidget(g)
        self.suivi = SuiviAttente()
        v.addWidget(self.suivi)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hb = QHBoxLayout()
        self.b_tout = QPushButton(_("Fabriquer les plans manquants"))
        self.b_tout.setToolTip(_("Chaque plan sans vidéo est fabriqué l'un après l'autre ; vous les regardez ensuite dans l'onglet Plans"))
        self.b_tout.clicked.connect(self.fabriquer_tout)
        hb.addWidget(self.b_tout)
        self.b_monter = QPushButton(_("Monter la séquence à la ligne rouge"))
        self.b_monter.setToolTip(_("Pose les plans fabriqués l'un après l'autre (la suite du film est décalée), les répliques sur la "
                                   "piste Voix et la musique ; Ctrl+Z revient"))
        self.b_monter.clicked.connect(self.monter)
        hb.addWidget(self.b_monter)
        hb.addStretch(1)
        b_f = QPushButton(_("Fermer"))
        b_f.clicked.connect(self.reject)
        hb.addWidget(b_f)
        v.addLayout(hb)
        self._remplir_tables()
        self._remplir_plans()
        self._maj_moteur()
        if self.seq["plans"]:
            self.onglets.setCurrentIndex(2)

    # ------------------------------------------------------------------ onglet 1 : histoire
    def _onglet_histoire(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.histoire = QPlainTextEdit(self.seq.get("histoire", ""))
        self.histoire.setPlaceholderText(_(
            "ex. : Deux pilotes arrivent sur un petit aérodrome au printemps. Ils se préparent dans le hangar, puis font la visite "
            "prévol de l'avion. L'un, à la manière d'Alain Delon, parle peu ; l'autre, à la manière de Simon Templar, plaisante. "
            "Enfin on les voit décoller."))
        v.addWidget(self.histoire, 1)
        h = QHBoxLayout()
        for lib, niveau, aide in ((_("Découper en plans (IA de ce poste)"), "locale", _("Rien ne sort de ce poste")),
                                  (_("Découper en plans (IA cloud)"), "cloud", _("Votre clef Claude ou Gemini ; texte seulement")),
                                  (_("Sans IA : une phrase = un plan"), "", _("Chaque phrase (ou « puis ») devient un plan"))):
            b = QPushButton(lib)
            b.setToolTip(aide)
            b.clicked.connect(lambda _c=False, n=niveau: self.decouper(n))
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        aide = QLabel(_("L'IA propose les personnages (apparence constante), les lieux, les plans avec leur cadrage et des répliques "
                        "écrites dans la manière de parler de chacun. Vous corrigez tout ensuite, dans les onglets suivants."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.onglets.addTab(w, _("1. Histoire"))

    def decouper(self, niveau):
        self.seq["histoire"] = self.histoire.toPlainText().strip()
        if not self.seq["histoire"]:
            self.etat.setText(_("Ecrivez d'abord l'histoire."))
            return
        if not niveau:
            self.seq["plans"] = Q.decouper_simple(self.seq["histoire"])
            noms = [p["nom"] for p in self.seq["personnages"]]
            li = self.seq["lieux"][0]["nom"] if self.seq["lieux"] else ""
            for p in self.seq["plans"]:
                p["personnages"], p["lieu"] = list(noms), li
            self._apres_decoupe()
            return
        seq = copy.deepcopy(self.seq)
        t = Tache(lambda tache: Q.decouper_ia(seq, self.params, niveau), _("Découpage"))
        self.taches.append(t)
        self.suivi.demarrer(_("L'IA découpe l'histoire en plans"), t,
                            _("IA de ce poste : une à plusieurs minutes.") if niveau == "locale" else _("IA cloud : quelques secondes."))

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ Découpage impossible : {e}", e=str(e)[:300]))
                return
            self.seq = r
            self._apres_decoupe()
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _apres_decoupe(self):
        self._remplir_tables()
        self._remplir_plans()
        self.onglets.setCurrentIndex(1 if not self.seq["personnages"] else 2)
        self.etat.setText(_("{n} plans proposés. Vérifiez les personnages et les lieux, puis chaque plan.", n=len(self.seq["plans"])))

    # ------------------------------------------------------------------ onglet 2 : personnages et lieux
    def _onglet_personnages(self):
        w = QWidget()
        v = QVBoxLayout(w)
        avert = QLabel(_("<b>Images de référence</b> : seulement des personnes qui ont donné leur accord (vous, vos proches, vos acteurs), "
                         "jamais la photo d'une célébrité : pour l'allure d'un acteur, le « style » suffit. Pour les lieux : vos photos "
                         "(aérodrome, avion, paysage)."))
        avert.setWordWrap(True)
        v.addWidget(avert)
        v.addWidget(QLabel("<b>" + _("Personnages") + "</b>"))
        self.t_persos = QTableWidget(0, 5)
        self.t_persos.setHorizontalHeaderLabels([_("Nom"), _("Apparence (âge, tenue…)"), _("Style « à la manière de »"),
                                                 _("Manière de parler"), _("Images")])
        self.t_persos.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.t_persos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_persos.itemChanged.connect(self._lire_tables)
        v.addWidget(self.t_persos, 1)
        h = QHBoxLayout()
        for lib, f in ((_("Ajouter un personnage"), lambda: self._ajouter("perso")), (_("Retirer"), lambda: self._retirer("perso")),
                       (_("Choisir le style…"), self._style_perso), (_("Images du personnage…"), lambda: self._images("perso"))):
            b = QPushButton(lib)
            b.clicked.connect(f)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        v.addWidget(QLabel("<b>" + _("Lieux") + "</b>"))
        self.t_lieux = QTableWidget(0, 3)
        self.t_lieux.setHorizontalHeaderLabels([_("Nom"), _("Description (lumière, saison, détails)"), _("Images")])
        self.t_lieux.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.t_lieux.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_lieux.itemChanged.connect(self._lire_tables)
        v.addWidget(self.t_lieux, 1)
        h = QHBoxLayout()
        for lib, f in ((_("Ajouter un lieu"), lambda: self._ajouter("lieu")), (_("Retirer"), lambda: self._retirer("lieu")),
                       (_("Images du lieu…"), lambda: self._images("lieu"))):
            b = QPushButton(lib)
            b.clicked.connect(f)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        self.onglets.addTab(w, _("2. Personnages et lieux"))

    def _remplir_tables(self):
        from . import diction as D
        for t in (self.t_persos, self.t_lieux):
            t.blockSignals(True)
        self.t_persos.setRowCount(0)
        for p in self.seq["personnages"]:
            r = self.t_persos.rowCount()
            self.t_persos.insertRow(r)
            for c, val in enumerate((p["nom"], p["description"], p["style"])):
                self.t_persos.setItem(r, c, QTableWidgetItem(val))
            cb = QComboBox()
            cb.addItem(_("Selon le style ({m})", m=D.STYLES.get(Q.maniere_de_parler(dict(p, maniere="")), D.STYLES["naturel"])[0]), "")
            for k, (lib, _r) in D.STYLES.items():
                cb.addItem(lib, k)
            cb.setCurrentIndex(max(0, cb.findData(p.get("maniere", ""))))
            cb.currentIndexChanged.connect(lambda _i, p=p, cb=cb: p.__setitem__("maniere", cb.currentData()))
            self.t_persos.setCellWidget(r, 3, cb)
            it = QTableWidgetItem(str(len(p.get("images") or [])))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            it.setToolTip("\n".join(p.get("images") or []))
            self.t_persos.setItem(r, 4, it)
        self.t_lieux.setRowCount(0)
        for l_ in self.seq["lieux"]:
            r = self.t_lieux.rowCount()
            self.t_lieux.insertRow(r)
            self.t_lieux.setItem(r, 0, QTableWidgetItem(l_["nom"]))
            self.t_lieux.setItem(r, 1, QTableWidgetItem(l_["description"]))
            it = QTableWidgetItem(str(len(l_.get("images") or [])))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            it.setToolTip("\n".join(l_.get("images") or []))
            self.t_lieux.setItem(r, 2, it)
        for t in (self.t_persos, self.t_lieux):
            t.blockSignals(False)
            t.resizeColumnToContents(0)
        self.t_persos.resizeColumnToContents(2)
        self.t_persos.resizeColumnToContents(3)
        self.t_persos.setColumnWidth(2, max(self.t_persos.columnWidth(2), 200))
        self.t_persos.setColumnWidth(3, max(self.t_persos.columnWidth(3), 260))

    def _lire_tables(self, *_a):
        for r, p in enumerate(self.seq["personnages"]):
            for c, k in ((0, "nom"), (1, "description"), (2, "style")):
                it = self.t_persos.item(r, c)
                if it:
                    p[k] = it.text().strip()
        for r, l_ in enumerate(self.seq["lieux"]):
            for c, k in ((0, "nom"), (1, "description")):
                it = self.t_lieux.item(r, c)
                if it:
                    l_[k] = it.text().strip()

    def _ajouter(self, quoi):
        if quoi == "perso":
            self.seq["personnages"].append(Q.personnage(_("Personnage {n}", n=len(self.seq["personnages"]) + 1)))
        else:
            self.seq["lieux"].append(Q.lieu(_("Lieu {n}", n=len(self.seq["lieux"]) + 1)))
        self._remplir_tables()

    def _retirer(self, quoi):
        t, liste = (self.t_persos, self.seq["personnages"]) if quoi == "perso" else (self.t_lieux, self.seq["lieux"])
        r = t.currentRow()
        if 0 <= r < len(liste):
            del liste[r]
            self._remplir_tables()

    def _style_perso(self):
        r = self.t_persos.currentRow()
        if not (0 <= r < len(self.seq["personnages"])):
            self.etat.setText(_("Cliquez d'abord sur la ligne du personnage."))
            return
        from .dialogues_creatif import choisir_style
        nom = choisir_style(self, self.params, "video", _("Donner ce style"))
        if nom:
            self.seq["personnages"][r]["style"] = nom
            self._remplir_tables()

    def _images(self, quoi):
        t, liste = (self.t_persos, self.seq["personnages"]) if quoi == "perso" else (self.t_lieux, self.seq["lieux"])
        r = t.currentRow()
        if not (0 <= r < len(liste)):
            self.etat.setText(_("Cliquez d'abord sur la ligne voulue."))
            return
        from .widgets import ouvrir_fichiers
        ps = ouvrir_fichiers(self, _("Images de référence"), _("Images") + " (*.jpg *.jpeg *.png *.webp)", "images", self.params)
        if ps:
            liste[r]["images"] = (liste[r].get("images") or []) + list(ps)
            self._remplir_tables()

    # ------------------------------------------------------------------ onglet 3 : plans
    def _onglet_plans(self):
        from .dialogues_creatif import ApercuCreation
        w = QSplitter()
        self.liste = QListWidget()
        self.liste.setWordWrap(True)
        self.liste.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.liste.setTextElideMode(Qt.ElideNone)
        self.liste.setToolTip(_("Glissez un plan pour changer l'ordre ; ✓ = vidéo prête, ○ = à fabriquer"))
        self.liste.setDragDropMode(QAbstractItemView.InternalMove)
        self.liste.model().rowsMoved.connect(self._ordre_change)
        self.liste.currentRowChanged.connect(self._montrer_plan)
        gauche = QWidget()
        vg = QVBoxLayout(gauche)
        vg.setContentsMargins(0, 0, 0, 0)
        vg.addWidget(self.liste, 1)
        h = QHBoxLayout()
        b = QPushButton(_("Ajouter un plan"))
        b.clicked.connect(self._ajouter_plan)
        h.addWidget(b)
        b = QPushButton(_("Retirer"))
        b.clicked.connect(self._retirer_plan)
        h.addWidget(b)
        vg.addLayout(h)
        w.addWidget(gauche)
        droite = QScrollArea()
        droite.setWidgetResizable(True)
        cont = QWidget()
        droite.setWidget(cont)
        f = QFormLayout(cont)
        self.p_action = QPlainTextEdit()
        self.p_action.setMaximumHeight(60)
        f.addRow(_("Ce qu'on voit"), self.p_action)
        self.p_persos = QLineEdit()
        self.p_persos.setPlaceholderText(_("Noms des personnages présents, séparés par des virgules"))
        f.addRow(_("Personnages"), self.p_persos)
        hl = QHBoxLayout()
        self.p_lieu = QComboBox()
        self.p_lieu.setEditable(True)
        hl.addWidget(self.p_lieu, 1)
        self.p_duree = QSpinBox()
        self.p_duree.setRange(3, 10)
        self.p_duree.setSuffix(" s")
        hl.addWidget(QLabel(_("Durée")))
        hl.addWidget(self.p_duree)
        f.addRow(_("Lieu"), hl)
        self.p_camera = QLineEdit()
        self.p_camera.setPlaceholderText(_("ex. : plan large, travelling latéral lent ; gros plan sur les mains"))
        f.addRow(_("Caméra"), self.p_camera)
        self.p_repliques = QPlainTextEdit()
        self.p_repliques.setMaximumHeight(70)
        self.p_repliques.setPlaceholderText(_("Une réplique par ligne : « Nom : texte ». ex. :\nMarc : On y va.\nPaul : Après vous, mon cher."))
        f.addRow(_("Répliques"), self.p_repliques)
        self.p_consigne = QPlainTextEdit()
        self.p_consigne.setMaximumHeight(110)
        self.p_consigne.setPlaceholderText(_("La consigne envoyée au moteur (en anglais, sans aucun nom de célébrité) : « Rédiger »"))
        f.addRow(_("Consigne"), self.p_consigne)
        hc = QHBoxLayout()
        for lib, fn, aide in ((_("Rédiger la consigne"), self._rediger, _("Construite à partir du plan, des personnages et du lieu")),
                              (_("Améliorer (IA de ce poste)"), lambda: self._ameliorer("locale"), _("Plus de détails de lumière, de cadrage, d'ambiance")),
                              (_("Améliorer (IA cloud)"), lambda: self._ameliorer("cloud"), _("Votre clef Claude ou Gemini ; texte seulement"))):
            b = QPushButton(lib)
            b.setToolTip(aide)
            b.clicked.connect(fn)
            hc.addWidget(b)
        hc.addStretch(1)
        f.addRow(hc)
        hi = QHBoxLayout()
        self.p_vignette = QLabel(_("Pas d'image de départ"))
        self.p_vignette.setFixedSize(160, 90)
        self.p_vignette.setAlignment(Qt.AlignCenter)
        self.p_vignette.setStyleSheet("border:1px solid palette(mid);border-radius:4px")
        hi.addWidget(self.p_vignette)
        vi = QVBoxLayout()
        for lib, fn, aide in ((_("Choisir une image…"), self._choisir_image, _("Une de vos photos comme première image du plan")),
                              (_("Composer avec Gemini"), lambda: self._composer("gemini"),
                               _("Gemini réunit les images des personnages et du lieu en une première image (votre clef, quelques centimes)")),
                              (_("Composer sur ce poste"), lambda: self._composer("locale"), _("L'IA de ce poste retravaille l'image du lieu")),
                              (_("Retirer l'image"), self._retirer_image, "")):
            b = QPushButton(lib)
            b.setToolTip(aide)
            b.clicked.connect(fn)
            vi.addWidget(b)
        hi.addLayout(vi)
        hi.addStretch(1)
        f.addRow(_("Image de départ"), hi)
        hf = QHBoxLayout()
        self.b_plan = QPushButton(_("Fabriquer ce plan"))
        self.b_plan.clicked.connect(self._fabriquer_courant)
        hf.addWidget(self.b_plan)
        self.b_flow = QPushButton(_("Copier pour Flow…"))
        self.b_flow.clicked.connect(self._copier_flow)
        hf.addWidget(self.b_flow)
        b = QPushButton(_("Vidéo déjà prête…"))
        b.setToolTip(_("Attacher à ce plan une vidéo que vous avez déjà (téléchargée de Flow, filmée…)"))
        b.clicked.connect(self._attacher)
        hf.addWidget(b)
        hf.addStretch(1)
        f.addRow(hf)
        self.aide_flow = QLabel(AIDE_FLOW)
        self.aide_flow.setWordWrap(True)
        self.aide_flow.setTextFormat(Qt.RichText)
        self.aide_flow.setStyleSheet("padding:6px 8px;border:1px solid palette(mid);border-radius:6px")
        f.addRow(self.aide_flow)
        self.apercu = ApercuCreation(self)
        f.addRow(self.apercu)
        for wd in (self.p_action, self.p_repliques, self.p_consigne):
            wd.textChanged.connect(self._lire_plan)
        self.p_persos.textChanged.connect(self._lire_plan)
        self.p_camera.textChanged.connect(self._lire_plan)
        self.p_lieu.currentTextChanged.connect(self._lire_plan)
        self.p_duree.valueChanged.connect(self._lire_plan)
        w.addWidget(droite)
        w.setSizes([300, 760])
        self.onglets.addTab(w, _("3. Plans"))

    def _libelle(self, i, p):
        signe = "✓" if p.get("fichier") and os.path.exists(p["fichier"]) else "○"
        return f"{signe} {i + 1}. {p.get('action') or _('(plan vide)')}"

    def _remplir_plans(self):
        self.liste.blockSignals(True)
        self.liste.clear()
        for i, p in enumerate(self.seq["plans"]):
            it = QListWidgetItem(self._libelle(i, p))
            it.setData(Qt.UserRole, id(p))
            self.liste.addItem(it)
        self.liste.blockSignals(False)
        self.p_lieu.blockSignals(True)
        self.p_lieu.clear()
        self.p_lieu.addItems([l_["nom"] for l_ in self.seq["lieux"]])
        self.p_lieu.blockSignals(False)
        if self.seq["plans"]:
            self.liste.setCurrentRow(min(max(0, self._courant), len(self.seq["plans"]) - 1))
        else:
            self._courant = -1
        self._maj_prix()

    def _ordre_change(self, *_a):
        par_id = {id(p): p for p in self.seq["plans"]}
        self.seq["plans"] = [par_id[self.liste.item(i).data(Qt.UserRole)] for i in range(self.liste.count())]
        for i, p in enumerate(self.seq["plans"]):
            self.liste.item(i).setText(self._libelle(i, p))

    def _ajouter_plan(self):
        self.seq["plans"].append(Q.plan("", [p["nom"] for p in self.seq["personnages"]],
                                        self.seq["lieux"][0]["nom"] if self.seq["lieux"] else ""))
        self._courant = len(self.seq["plans"]) - 1
        self._remplir_plans()

    def _retirer_plan(self):
        i = self.liste.currentRow()
        if 0 <= i < len(self.seq["plans"]):
            del self.seq["plans"][i]
            self._courant = min(i, len(self.seq["plans"]) - 1)
            self._remplir_plans()

    def _plan(self):
        return self.seq["plans"][self._courant] if 0 <= self._courant < len(self.seq["plans"]) else None

    def _montrer_plan(self, i):
        self._courant = i
        p = self._plan()
        self._charge = True
        if p:
            self.p_action.setPlainText(p.get("action", ""))
            self.p_persos.setText(", ".join(p.get("personnages") or []))
            self.p_lieu.setCurrentText(p.get("lieu", ""))
            self.p_duree.setValue(int(p.get("duree") or Q.DUREE_PLAN))
            self.p_camera.setText(p.get("camera", ""))
            self.p_repliques.setPlainText("\n".join(f"{r['qui']} : {r['texte']}" for r in p.get("repliques") or []))
            self.p_consigne.setPlainText(p.get("consigne", ""))
            self._maj_vignette()
            self.apercu.arreter()
            if p.get("fichier") and os.path.exists(p["fichier"]):
                self.apercu.charger(p["fichier"], video=True)
                self.apercu.show()
            else:
                self.apercu.hide()
        self._charge = False

    def _lire_plan(self, *_a):
        p = self._plan()
        if not p or getattr(self, "_charge", False):
            return
        p["action"] = self.p_action.toPlainText().strip()
        p["personnages"] = [x.strip() for x in self.p_persos.text().split(",") if x.strip()]
        p["lieu"] = self.p_lieu.currentText().strip()
        p["duree"] = self.p_duree.value()
        p["camera"] = self.p_camera.text().strip()
        reps = []
        for ligne in self.p_repliques.toPlainText().splitlines():
            if ":" in ligne:
                qui, texte = ligne.split(":", 1)
                if texte.strip():
                    reps.append({"qui": qui.strip(), "texte": texte.strip()})
            elif ligne.strip():
                reps.append({"qui": "", "texte": ligne.strip()})
        p["repliques"] = reps
        p["voix"] = []                     # répliques changées : voix à refaire
        p["consigne"] = self.p_consigne.toPlainText().strip()
        it = self.liste.item(self._courant)
        if it:
            it.setText(self._libelle(self._courant, p))
        self._maj_prix()

    def _rediger(self):
        p = self._plan()
        if p:
            self.p_consigne.setPlainText(Q.consigne(self.seq, p, self.params))

    def _ameliorer(self, niveau):
        p = self._plan()
        if not p:
            return
        texte = self.p_consigne.toPlainText().strip() or Q.consigne(self.seq, p, self.params)
        t = Tache(lambda tache: Q.ameliorer(texte, self.params, niveau), _("Consigne"))
        self.taches.append(t)
        self.suivi.demarrer(_("L'IA détaille la consigne du plan"), t)
        i = self._courant

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ {e}", e=str(e)[:300]))
                return
            self.seq["plans"][i]["consigne"] = r
            if self._courant == i:
                self.p_consigne.setPlainText(r)
            self.etat.setText(_("Consigne détaillée : relisez-la, modifiez-la si besoin."))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _maj_vignette(self):
        p = self._plan()
        img = (p or {}).get("image")
        if img and os.path.exists(img):
            self.p_vignette.setPixmap(QPixmap(img).scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.p_vignette.setPixmap(QPixmap())
            self.p_vignette.setText(_("Pas d'image de départ"))

    def _choisir_image(self):
        p = self._plan()
        if not p:
            return
        from .widgets import ouvrir_fichiers
        ps = ouvrir_fichiers(self, _("Image de départ du plan"), _("Images") + " (*.jpg *.jpeg *.png *.webp)", "images", self.params)
        if ps:
            p["image"] = ps[0]
            self._maj_vignette()

    def _retirer_image(self):
        p = self._plan()
        if p:
            p["image"] = ""
            self._maj_vignette()

    def _composer(self, moteur):
        p = self._plan()
        if not p:
            return
        i = self._courant
        if moteur == "gemini" and QMessageBox.question(self, _("Image de départ"), _(
                "Envoyer la consigne et les images de référence de ce plan à Gemini pour composer la première image "
                "(votre clef, quelques centimes) ?")) != QMessageBox.Yes:
            return
        seq = copy.deepcopy(self.seq)
        t = Tache(lambda tache: Q.image_depart(seq, i, self.params, moteur), _("Image de départ"))
        self.taches.append(t)
        self.suivi.demarrer(_("Composition de l'image de départ du plan {n}", n=i + 1), t,
                            _("Gemini : 10 à 60 s.") if moteur == "gemini" else _("IA de ce poste : une à plusieurs minutes."))

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ Image impossible : {e}", e=str(e)[:300]))
                return
            self.seq["plans"][i]["image"] = r
            if self._courant == i:
                self._maj_vignette()
            self.etat.setText(_("Image de départ prête : regardez-la (vignette) ; elle sert de première image au plan."))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    # ------------------------------------------------------------------ fabrication
    def _maj_moteur(self, *_a):
        m = self.moteur.currentData()
        self.seq["moteur"] = m
        flow = m == "flow"
        self.b_flow.setVisible(flow)
        self.aide_flow.setVisible(flow)
        self.b_plan.setVisible(not flow)
        self.b_tout.setVisible(not flow)
        self._maj_prix()

    def _maj_prix(self):
        m = self.moteur.currentData() if hasattr(self, "moteur") else "flow"
        if not hasattr(self, "prix"):
            return
        manquants = sum(1 for p in self.seq["plans"] if not (p.get("fichier") and os.path.exists(p["fichier"])))
        if m == "flow":
            self.prix.setText(_("{n} plan(s) à faire dans Flow, compris dans votre abonnement.", n=manquants))
        elif m == "locale":
            self.prix.setText(_("{n} plan(s) à calculer sur ce poste : gratuit, environ 2 à 15 min par plan selon la carte graphique.",
                                n=manquants))
        else:
            self.prix.setText(_("{n} plan(s) à fabriquer : jusqu'à {p} $ environ sur votre clef ; confirmation avant l'envoi.",
                                n=manquants, p=Q.prix_total(self.seq, m, self.params)))

    def _confirmer(self, indices):
        m = self.moteur.currentData()
        if m in ("locale", "flow"):
            return True
        from . import generateurs_video as GV
        mo = GV.modele(m, self.params)
        prix = round(sum(GV.prix(mo, int(self.seq["plans"][i].get("duree") or Q.DUREE_PLAN)) for i in indices), 2) if mo else 0
        return QMessageBox.question(self, _("Séquence IA"), _("Fabriquer {n} plan(s) avec {m} pour au plus {p} $ environ (votre clef) ?",
                                                              n=len(indices), m=(mo or {}).get("nom", m), p=prix)) == QMessageBox.Yes

    def _fabriquer_courant(self):
        if self._plan():
            self._fabriquer([self._courant])

    def fabriquer_tout(self):
        self._lire_tables()
        manquants = [i for i, p in enumerate(self.seq["plans"]) if not (p.get("fichier") and os.path.exists(p["fichier"]))]
        if not manquants:
            self.etat.setText(_("Tous les plans ont leur vidéo : regardez-les, puis « Monter la séquence »."))
            return
        self._fabriquer(manquants)

    def _fabriquer(self, indices):
        if not self._confirmer(indices):
            return
        m = self.moteur.currentData()
        for i in indices:
            p = self.seq["plans"][i]
            if not p.get("consigne"):
                p["consigne"] = Q.consigne(self.seq, p, self.params)
        seq = copy.deepcopy(self.seq)

        def travail(tache):
            faits = {}
            for k, i in enumerate(indices):
                if tache.arret:
                    break
                tache.avancer(k / len(indices), _("plan {i} ({k} sur {n})", i=i + 1, k=k + 1, n=len(indices)))
                faits[i] = Q.fabriquer_plan(seq, i, self.params, m,
                                            progression=lambda f, k=k: tache.avancer((k + f) / len(indices)), arret=lambda: tache.arret)
            return faits
        t = Tache(travail, _("Séquence IA"))
        self.taches.append(t)
        self.suivi.demarrer(_("Fabrication de {n} plan(s)", n=len(indices)), t,
                            _("IA de ce poste : plusieurs minutes par plan.") if m == "locale" else _("Cloud : 1 à 6 min par plan."))
        t.progression.connect(lambda f, txt: txt and self.suivi.etape(_("Fabrication : {t} — {p} %", t=txt, p=int(f * 100))),
                              Qt.QueuedConnection)

        def fin(r, e):
            self.suivi.finir()
            for i, chemin in (r or {}).items():
                self.seq["plans"][i]["fichier"] = chemin
            Q.enregistrer(self.seq)
            self._remplir_plans()
            if e:
                self.etat.setText(_("✕ {e}", e=str(e)[:300]))
            else:
                self.etat.setText(_("{n} plan(s) prêts : regardez-les un par un (onglet Plans), refaites ceux qui ne vont pas, "
                                    "puis « Monter la séquence ».", n=len(r or {})))
                self.onglets.setCurrentIndex(2)
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _copier_flow(self):
        """Flow à la main : consigne copiée, Flow et dossier des images ouverts, puis attente du téléchargement."""
        p = self._plan()
        if not p:
            return
        from . import fabrique as FAB
        i = self._courant
        texte = self.p_consigne.toPlainText().strip() or Q.consigne(self.seq, p, self.params)
        p["consigne"] = texte
        self.p_consigne.setPlainText(texte)
        refs = Q.images_du_plan(self.seq, p) + ([p["image"]] if p.get("image") else [])
        if refs:                                    # un dossier qui ne contient que les images de ce plan, à glisser dans Flow
            import shutil
            d = os.path.join(Q.dossier(self.seq), f"plan{i + 1:02d}_images_pour_flow")
            os.makedirs(d, exist_ok=True)
            for r in refs:
                try:
                    shutil.copy2(r, d)
                except OSError:
                    pass
            ouvrir = getattr(self.ed.window(), "_ouvrir_dans_systeme", None)
            if ouvrir:
                ouvrir(d)
        dossier = self.params.get("dossier_flow") or os.path.join(os.path.expanduser("~"), "Downloads")
        avant = FAB.preparer_flow(texte, dossier)
        t = Tache(lambda tache: FAB.attendre_clip(dossier, avant, tache), _("Clip Flow"))
        self.taches.append(t)
        self.suivi.demarrer(_("Plan {n} : consigne copiée, Flow ouvert ; PhilCut attend la vidéo téléchargée", n=i + 1), t,
                            _("Dans Flow : images de référence, Ctrl+V, générer, puis « Télécharger »."))

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ {e}", e=str(e)[:300]))
                return
            if r:
                self.seq["plans"][i]["fichier"] = r[0]
                Q.enregistrer(self.seq)
                self._remplir_plans()
                self.liste.setCurrentRow(i)
                self.etat.setText(_("Vidéo du plan {n} reçue : regardez-la ; passez au plan suivant.", n=i + 1))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _attacher(self):
        p = self._plan()
        if not p:
            return
        from .widgets import ouvrir_fichiers
        ps = ouvrir_fichiers(self, _("Vidéo du plan"), _("Vidéos") + " (*.mp4 *.mov *.webm *.mkv)", "videos", self.params)
        if ps:
            p["fichier"] = ps[0]
            Q.enregistrer(self.seq)
            i = self._courant
            self._remplir_plans()
            self.liste.setCurrentRow(i)

    # ------------------------------------------------------------------ montage
    def monter(self):
        self._lire_tables()
        prets = [i for i, p in enumerate(self.seq["plans"]) if p.get("fichier") and os.path.exists(p["fichier"])]
        if not prets:
            self.etat.setText(_("Aucun plan n'a encore sa vidéo : fabriquez-les d'abord."))
            return
        if len(prets) < len(self.seq["plans"]) and QMessageBox.question(self, _("Séquence IA"), _(
                "{n} plan(s) sur {t} ont leur vidéo. Monter seulement ceux-là ?", n=len(prets), t=len(self.seq["plans"]))) != QMessageBox.Yes:
            return
        moteur_voix = self.voix.currentData()
        self.seq["voix"] = moteur_voix
        self.seq["musique"] = {"active": self.musique.isChecked(), "phrase": self.phrase_musique.text().strip()}
        if moteur_voix == "gemini" and any(self.seq["plans"][i].get("repliques") for i in prets):
            from . import diction as D
            cout = round(sum(D.prix(r["texte"], "gemini") for i in prets for r in self.seq["plans"][i].get("repliques") or []), 3)
            if QMessageBox.question(self, _("Séquence IA"), _("Faire dire les répliques par Gemini pour environ {p} $ (votre clef) ?",
                                                              p=cout)) != QMessageBox.Yes:
                return
        seq = copy.deepcopy(self.seq)
        musique = self.musique.isChecked()

        def travail(tache):
            from . import moteur, creatif
            out = {"voix": {}, "musique": ""}
            for k, i in enumerate(prets):
                if seq["plans"][i].get("repliques") and not seq["plans"][i].get("voix"):
                    tache.avancer(k / (len(prets) + 1), _("répliques du plan {n}", n=i + 1))
                    out["voix"][i] = Q.voix_du_plan(seq, i, self.params, moteur_voix)
            if musique and not tache.arret:
                duree = sum(float((moteur.sonder(seq["plans"][i]["fichier"]) or {}).get("duree") or 0) for i in prets)
                phrase = seq["musique"]["phrase"] or "light elegant 1960s jazz, guitar and brass, adventurous mood"
                try:
                    from . import styles_ia as S
                    from .traduction_recherche import phrase_en_anglais
                    tr = S.transposer(phrase, "musique", self.params)
                    phrase = (phrase_en_anglais(tr["texte"])[0] + (", " + tr["ajout"] if tr.get("ajout") else "")).strip(", ")
                except Exception:      # noqa: BLE001
                    pass
                tache.avancer(len(prets) / (len(prets) + 1), _("musique ({d} s)", d=int(duree)))
                sortie = os.path.join(Q.dossier(seq), "musique.wav")
                try:
                    creatif.musique(phrase, sortie, duree=max(10.0, duree), params=self.params, instrumental=True,
                                    progression=lambda f: tache.avancer((len(prets) + f) / (len(prets) + 1)), arret=lambda: tache.arret)
                    out["musique"] = sortie
                except Exception as e:      # noqa: BLE001
                    out["erreur_musique"] = str(e)
            return out
        t = Tache(travail, _("Séquence IA"))
        self.taches.append(t)
        self.suivi.demarrer(_("Préparation du montage (répliques, musique)"), t)
        t.progression.connect(lambda f, txt: txt and self.suivi.etape(_("Préparation : {t} — {p} %", t=txt, p=int(f * 100))),
                              Qt.QueuedConnection)

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ {e}", e=str(e)[:300]))
                return
            for i, v in (r.get("voix") or {}).items():
                self.seq["plans"][i]["voix"] = v
            p = self.ed.projet
            p.marquer()
            t0 = self.ed.timeline.position
            n, duree = Q.monter(p, self.seq, t0)
            if r.get("musique"):
                from . import moteur
                m = p.ajouter_media(r["musique"], moteur.sonder(r["musique"]))
                m["nom"] = _("Musique de la séquence")
                c = p.ajouter_clip(m["id"], "audio", t0, 0.0, duree)
                c.update(volume=0.35, fondu_entree=1.0, fondu_sortie=2.0)
            p.d.setdefault("sequences_ia", [])
            p.d["sequences_ia"] = [s for s in p.d["sequences_ia"] if s.get("cree") != self.seq.get("cree")] + [copy.deepcopy(self.seq)]
            Q.enregistrer(self.seq)
            self.ed.biblio.remplir(p)
            self.ed.rafraichir()
            msg = _("Séquence montée : {n} plans, {d} s, à partir de la ligne rouge (Ctrl+Z pour revenir).", n=n, d=int(duree))
            if r.get("erreur_musique"):
                msg += " " + _("Musique non faite : {e}", e=r["erreur_musique"][:200])
            self.ed.encart.message(msg, 9000)
            self.accept()
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def done(self, r):
        self._lire_tables()
        self.seq["histoire"] = self.histoire.toPlainText().strip()
        self.seq["musique"] = {"active": self.musique.isChecked(), "phrase": self.phrase_musique.text().strip()}
        self.seq["voix"] = self.voix.currentData()
        try:
            self.apercu.arreter()
        except Exception:      # noqa: BLE001
            pass
        if self.seq["plans"] or self.seq["histoire"]:
            p = self.ed.projet
            p.d["sequences_ia"] = [s for s in p.d.get("sequences_ia") or [] if s.get("cree") != self.seq.get("cree")] + [copy.deepcopy(self.seq)]
            p.modifie = True
            try:
                Q.enregistrer(self.seq)
            except OSError:
                pass
        for t in self.taches:
            if t.isRunning():
                t.stopper()
        super().done(r)
