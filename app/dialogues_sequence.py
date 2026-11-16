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
from .widgets import garder_calcul, suivre_en_fond
from .taches import Tache
from .widgets import SuiviAttente
from .taches import texte_erreur

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
        # 0.9.43 : plus lisible (texte un peu plus grand, l'essentiel en gras)
        taille = QApplication.font().pointSizeF() + 1.5
        self.setStyleSheet(f"QWidget{{font-size:{taille:.1f}pt}} QGroupBox{{font-weight:600}} QTabBar::tab{{font-weight:600}}")
        v = QVBoxLayout(self)
        intro = QLabel(_("<b>Racontez une petite histoire</b> ; PhilCut la découpe en plans, garde <b>les mêmes personnages</b> d'un "
                         "plan à l'autre (description constante et images de référence), fait dire <b>les répliques</b> avec la "
                         "manière de parler de chacun, puis monte le tout avec <b>une musique</b>. « A la manière de » décrit un "
                         "style (allure, jeu, voix posée), jamais un visage ni une voix copiée."))
        intro.setTextFormat(Qt.RichText)
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
        self.moteur = QComboBox()                      # ordre : ce poste (gratuit), Gemini, autres clefs, Flow en dernier
        self.moteur.addItem(_("IA de ce poste (gratuite ; plans courts, lents à calculer)"), "locale")
        from . import generateurs_video as GV
        dispo = {m["id"] for m in GV.disponibles(self.params)}
        modeles = sorted(GV.modeles(self.params), key=lambda m: (m.get("fournisseur") != "google", m["id"] not in dispo))
        for m in modeles:
            lib = _("Cloud : {n} — {p} $/s (votre clef)", n=m["nom"], p=f"{m.get('prix_s', 0):.3f}".rstrip("0").replace(".", ","))
            self.moteur.addItem(lib, m["id"])
            if m["id"] not in dispo:
                self.moteur.model().item(self.moteur.count() - 1).setEnabled(False)
                self.moteur.setItemData(self.moteur.count() - 1, _("Clef à saisir : Fabrique IA › Vidéo › Plan vidéo à partir d'une phrase › Connecter une IA"),
                                        Qt.ToolTipRole)
        self.moteur.addItem(_("Google Flow (votre abonnement, pas à pas)"), "flow")
        i = self.moteur.findData(self.seq.get("moteur"))
        self.moteur.setCurrentIndex(max(0, i))
        self.moteur.currentIndexChanged.connect(self._maj_moteur)
        f.addRow(self._gras(_("Vidéo")), self.moteur)
        self.explication_moteur = QLabel("")              # 0.9.55 : ce que chaque moteur garde du personnage
        self.explication_moteur.setWordWrap(True)
        self.explication_moteur.setStyleSheet("color:#9aa4b2")
        f.addRow("", self.explication_moteur)
        self.voix = QComboBox()
        self.voix.addItem(_("Aucune voix : personne ne parle"), "aucune")
        self.voix.addItem(_("Voix de ce poste (gratuite)"), "local")
        self.voix.addItem(_("Voix Gemini (joue vraiment la phrase ; votre clef, payant)"), "gemini")
        self.voix.addItem(_("Voix du moteur vidéo : il fait parler les personnages avec la vidéo (lèvres naturelles)"), "moteur")
        self.voix.setToolTip(_("Un seul réglage pour la voix : personne ne parle, voix posée ensuite par PhilCut, ou voix fabriquée "
                               "avec la vidéo par le moteur (Kling, Seedance, Gemini ; un peu plus cher chez Kling)"))
        self.voix.setCurrentIndex(max(0, self.voix.findData(self.seq.get("voix", "local"))))
        self.voix.currentIndexChanged.connect(lambda _i: (self.seq.__setitem__("voix", self.voix.currentData()), self._maj_prix()))
        f.addRow(self._gras(_("Répliques")), self.voix)
        hm = QHBoxLayout()
        self.image_auto = QCheckBox(_("Image de départ par Gemini (0,04 $ par plan)"))
        self.image_auto.setToolTip(_("Composée avec les images des personnages et du lieu : le personnage ressemble à son image. "
                                     "Sans elle, le moteur réinvente le personnage d'après sa description."))
        self.image_auto.setChecked(bool(self.seq.get("image_auto", True)))
        self.image_auto.setEnabled(bool(self.params.get("clef_gemini")))
        self.image_auto.toggled.connect(lambda v: (self.seq.__setitem__("image_auto", v), self._maj_prix()))
        f.addRow(self._gras(_("Visages")), self.image_auto)
        self.image_fin = QCheckBox(_("Image d'arrivée et fiche personnage (moteur Référence)"))
        self.image_fin.setToolTip(_("Avec « Kling O3 Référence » : une planche du personnage (face, profil, en pied) et l'image de fin "
                                    "de chaque plan sont composées par Gemini (0,04 $ chacune). Le moteur garde le visage et doit "
                                    "rejoindre la pose finale : plus de personnage qui change ni de passage à travers la table."))
        self.image_fin.setChecked(bool(self.seq.get("image_fin_auto", True)))
        self.image_fin.setEnabled(bool(self.params.get("clef_gemini")))
        self.image_fin.toggled.connect(lambda v: (self.seq.__setitem__("image_fin_auto", v), self._maj_prix()))
        f.addRow("", self.image_fin)
        self.musique = QCheckBox(_("Musique sous la séquence (IA de ce poste)"))
        self.musique.setChecked(bool(self.seq["musique"].get("active", True)))
        hm.addWidget(self.musique)
        self.phrase_musique = QLineEdit(self.seq["musique"].get("phrase", ""))
        self.phrase_musique.setPlaceholderText(_("ex. : jazz léger des années 60, guitare et cuivres"))
        hm.addWidget(self.phrase_musique, 1)
        f.addRow(self._gras(_("Musique")), hm)
        self.prix = QLabel("")
        f.addRow(self.prix)
        from .credit_ia import LigneCredit, fournisseur_du_moteur
        self.credit = LigneCredit(self.params, fournisseur_du_moteur(self.seq.get("moteur"), self.params))
        f.addRow(self.credit)
        v.addWidget(g)
        self.suivi = SuiviAttente()
        v.addWidget(self.suivi)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hb = QHBoxLayout()
        b_nv = QPushButton(_("Nouvelle histoire…"))
        b_nv.setToolTip(_("Repartir d'une histoire vide ; les séquences déjà montées restent dans le projet."))
        b_nv.clicked.connect(self._nouvelle)
        hb.addWidget(b_nv)
        self.b_tout = QPushButton(_("Fabriquer les plans manquants"))
        self.b_tout.setToolTip(_("Chaque plan sans vidéo est fabriqué l'un après l'autre ; vous les regardez ensuite dans l'onglet Plans"))
        self.b_tout.clicked.connect(self.fabriquer_tout)
        self.b_images = QPushButton(_("Images des plans…"))
        self.b_images.setToolTip(_("Voir, refaire ou remplacer l'image de départ et d'arrivée de chaque plan avant la vidéo "
                                   "(moteur Référence)"))
        self.b_images.clicked.connect(lambda: self.verifier_images(None))
        hb.addWidget(self.b_images)
        hb.addWidget(self.b_tout)
        self.b_monter = QPushButton(_("Monter la séquence à la ligne rouge"))
        self.b_monter.setToolTip(_("Pose les plans fabriqués l'un après l'autre (la suite du film est décalée), les répliques sur la "
                                   "piste Voix et la musique ; Ctrl+Z revient"))
        self.b_monter.clicked.connect(self.monter)
        hb.addWidget(self.b_monter)
        for b in (self.b_tout, self.b_monter):
            b.setStyleSheet("font-weight:600")
        hb.addStretch(1)
        # 0.9.68 : la fenêtre ne bloque plus PhilCut ; pendant un calcul, « Réduire » la range (la barre du bas suit)
        self.b_reduire = QPushButton(_("Réduire (suivi dans la barre du bas)"))
        self.b_reduire.setToolTip(_("La fabrication continue ; « Afficher la fenêtre » dans la barre du bas la rouvre"))
        self.b_reduire.clicked.connect(self.hide)
        self.b_reduire.hide()
        hb.addWidget(self.b_reduire)
        self._veille_reduire = QTimer(self)
        self._veille_reduire.timeout.connect(lambda: self.b_reduire.setVisible(any(t.isRunning() for t in self.taches)))
        self._veille_reduire.start(500)
        b_f = QPushButton(_("Fermer"))
        b_f.clicked.connect(self.reject)
        hb.addWidget(b_f)
        v.addLayout(hb)
        self._remplir_tables()
        self._remplir_plans()
        self._maj_moteur()
        if self.seq["plans"]:
            self.onglets.setCurrentIndex(2)

    @staticmethod
    def _gras(texte):
        lb = QLabel(f"<b>{texte}</b>")
        lb.setTextFormat(Qt.RichText)
        return lb

    def _nouvelle(self):
        if any(t.isRunning() for t in self.taches):
            QMessageBox.information(self, _("Nouvelle histoire"), _("Une fabrication est en cours : attendez la fin, ou « Arrêter », "
                                                                    "avant de repartir d'une histoire vide."))
            return
        if (self.seq.get("histoire") or self.seq.get("plans")) and QMessageBox.question(
                self, _("Nouvelle histoire"), _("Repartir d'une histoire vide ? L'histoire en cours reste dans le projet "
                                                "(elle n'est pas effacée).")) != QMessageBox.Yes:
            return
        self.nouvelle_demandee = True
        self.reject()

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
        suivre_en_fond(self, t, _("Séquence IA"))
        self.suivi.demarrer(_("L'IA découpe l'histoire en plans"), t,
                            _("IA de ce poste : une à plusieurs minutes.") if niveau == "locale" else _("IA cloud : quelques secondes."))

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ Découpage impossible : {e}", e=texte_erreur(e)[:300]))
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
                       (_("Choisir le style…"), self._style_perso), (_("Images du personnage…"), lambda: self._images("perso")),
                       (_("Fiche personnage…"), self._planche)):
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
            fiche = bool(p.get("planche") and os.path.exists(p["planche"]))
            it = QTableWidgetItem(str(len(p.get("images") or [])) + (" + " + _("fiche") if fiche else ""))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            it.setToolTip("\n".join((p.get("images") or []) + ([p["planche"]] if fiche else [])))
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
        if quoi == "perso" and not liste[r].get("accord") and not self._accord_personne(liste[r].get("nom", "")):
            return
        from .widgets import ouvrir_fichiers
        ps = ouvrir_fichiers(self, _("Images de référence"), _("Images") + " (*.jpg *.jpeg *.png *.webp)", "images", self.params)
        if ps:
            if quoi == "perso":
                liste[r]["accord"] = True
            liste[r]["images"] = (liste[r].get("images") or []) + list(ps)
            self._remplir_tables()

    def _planche(self):
        """0.9.72 : planche du personnage (face, trois quarts, profil, en pied) d'après ses images, montrée avant d'être gardée."""
        r = self.t_persos.currentRow()
        if not (0 <= r < len(self.seq["personnages"])):
            self.etat.setText(_("Cliquez d'abord sur la ligne du personnage."))
            return
        p = self.seq["personnages"][r]
        if not [i for i in p.get("images") or [] if os.path.exists(i)]:
            self.etat.setText(_("Ajoutez d'abord une image du personnage (« Images du personnage… »)."))
            return
        if not self.params.get("clef_gemini"):
            self.etat.setText(_("La fiche se compose avec Gemini : Préférences › IA › Connecter une IA."))
            return
        if QMessageBox.question(self, _("Fiche personnage"), _("Composer la planche de « {n} » (face, trois quarts, profil, en pied) "
                                "avec Gemini, d'après ses images (votre clef, 0,04 $ environ) ?", n=p.get("nom") or "?")) != QMessageBox.Yes:
            return
        seq = copy.deepcopy(self.seq)
        t = Tache(lambda tache: Q.planche_personnage(seq, seq["personnages"][r], self.params), _("Fiche personnage"))
        self.taches.append(t)
        suivre_en_fond(self, t, _("Séquence IA"))
        self.suivi.demarrer(_("Fiche du personnage « {n} »", n=p.get("nom") or "?"), t, _("Gemini : 10 à 60 s."))

        def fin(chemin, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
                return
            if apercu_planche(self, chemin, p.get("nom") or ""):
                p["planche"] = chemin
                Q.enregistrer(self.seq)
                self._remplir_tables()
                self.etat.setText(_("✓ Fiche gardée : le moteur Référence s'en sert pour garder le personnage identique."))
            else:
                self.etat.setText(_("Fiche écartée ; refaites-la, ou changez les images du personnage."))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _accord_personne(self, nom):
        """0.9.52 : l'image d'une personne réelle ne sert qu'avec son accord, que l'auteur certifie (case engageante)."""
        from PySide6.QtWidgets import QDialogButtonBox
        from .widgets import CaseLongue
        d = QDialog(self)
        d.setWindowTitle(_("Accord de la personne"))
        v = QVBoxLayout(d)
        t = QLabel(_("Les images de « {n} » vont servir à lui faire jouer une scène et dire des répliques. PhilCut ne le fait "
                     "qu'avec l'accord de la personne : vous-même, un proche, un ami qui a accepté. Jamais une personne connue "
                     "ni quelqu'un qui n'a pas donné son accord.", n=nom or _("ce personnage")))
        t.setWordWrap(True)
        v.addWidget(t)
        case = CaseLongue(_("Je certifie que la personne sur ces images a donné son accord pour cette utilisation, et j'en prends "
                            "la responsabilité."))
        v.addWidget(case)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Continuer"))
        bb.button(QDialogButtonBox.Ok).setEnabled(False)
        case.toggled.connect(bb.button(QDialogButtonBox.Ok).setEnabled)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        v.addWidget(bb)
        d.setMinimumWidth(520)
        return d.exec() == QDialog.Accepted

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
        self.b_une_action = QPushButton(_("Une action par plan"))
        self.b_une_action.setToolTip(_("Chaque plan qui enchaîne deux actions (« contourne le bureau et s'assoit ») devient deux plans"))
        self.b_une_action.clicked.connect(self._couper_tous)
        vg.addWidget(self.b_une_action)
        w.addWidget(gauche)
        droite = QScrollArea()
        droite.setWidgetResizable(True)
        droite.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)          # 0.9.72 : jamais de défilement horizontal
        cont = QWidget()
        droite.setWidget(cont)
        f = QFormLayout(cont)
        self.p_action = QPlainTextEdit()
        self.p_action.setMaximumHeight(60)
        f.addRow(_("Ce qu'on voit"), self.p_action)
        # 0.9.70 : une seule action simple par plan, sinon le moteur enchaîne mal (traverser une table pour s'asseoir…)
        self.boite_multi = QWidget()
        hm2 = QHBoxLayout(self.boite_multi)
        hm2.setContentsMargins(0, 0, 0, 0)
        self.lbl_multi = QLabel(_("⚠ Deux actions dans ce plan : les moteurs vidéo n'en réussissent bien qu'une (sinon gestes "
                                  "incohérents)."))
        self.lbl_multi.setWordWrap(True)
        self.lbl_multi.setStyleSheet("color:#c98a00")
        hm2.addWidget(self.lbl_multi, 1)
        b = QPushButton(_("Couper en deux plans"))
        b.clicked.connect(self._couper_courant)
        hm2.addWidget(b)
        self.boite_multi.hide()
        f.addRow("", self.boite_multi)
        self.p_persos = QLineEdit()
        self.p_persos.setPlaceholderText(_("Noms des personnages présents, séparés par des virgules"))
        f.addRow(_("Personnages"), self.p_persos)
        hl = QHBoxLayout()
        self.p_lieu = QComboBox()
        self.p_lieu.setEditable(True)
        hl.addWidget(self.p_lieu, 1)
        self.p_duree = QSpinBox()
        self.p_duree.setRange(3, 15)
        self.p_duree.setSuffix(" s")
        hl.addWidget(QLabel(_("Durée")))
        hl.addWidget(self.p_duree)
        f.addRow(_("Lieu"), hl)
        self.p_enchainer = QCheckBox(_("Démarrer sur la dernière image du plan précédent"))
        self.p_enchainer.setToolTip(_("Raccord parfait : même personnage, même place, même lumière (moteur Référence)"))
        self.p_enchainer.toggled.connect(self._lire_plan)
        f.addRow(_("Enchaîner"), self.p_enchainer)
        self.p_camera = QLineEdit()
        self.p_camera.setPlaceholderText(_("ex. : plan large, travelling latéral lent ; gros plan sur les mains"))
        f.addRow(_("Caméra"), self.p_camera)
        self.p_repliques = QPlainTextEdit()
        self.p_repliques.setMaximumHeight(70)
        self.p_repliques.setPlaceholderText(_("Une réplique par ligne : « Nom : texte ». ex. :\nMarc : On y va.\nPaul : Après vous, mon cher."))
        f.addRow(_("Répliques"), self.p_repliques)
        from .consigne_bilingue import ConsigneBilingue
        self.p_consigne = ConsigneBilingue(60)                   # votre langue + l'anglais envoyé, les deux visibles
        self.p_consigne.setMaximumHeight(110)
        self.p_consigne.setPlaceholderText(_("La consigne, sans aucun nom de célébrité ; ou « Rédiger la consigne »"))
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

    def _couper_courant(self):
        if 0 <= self._courant < len(self.seq["plans"]) and Q.couper_plan(self.seq, self._courant):
            self._remplir_plans()
            self.etat.setText(_("Plan coupé en deux : une action chacun."))

    def _couper_tous(self):
        n, i = 0, 0
        while i < len(self.seq["plans"]):
            if not self.seq["plans"][i].get("fichier") and Q.couper_plan(self.seq, i):
                n += 1
                continue                       # le premier morceau peut encore contenir deux actions
            i += 1
        self._remplir_plans()
        self.etat.setText(_("{n} plan(s) coupé(s) : une action par plan.", n=n) if n else _("Chaque plan n'a déjà qu'une action."))

    def _libelle(self, i, p):
        signe = "✓" if p.get("fichier") and os.path.exists(p["fichier"]) else ("⚠" if Q.actions_multiples(p.get("action")) else "○")
        return f"{signe} {i + 1}. {p.get('action') or _('(plan vide)')}"

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
            self.p_enchainer.setChecked(bool(p.get("enchainer", True)))
            self.p_enchainer.setEnabled(i > 0)
            self.p_repliques.setPlainText("\n".join(f"{r['qui']} : {r['texte']}" for r in p.get("repliques") or []))
            self.p_consigne.setPlainText(p.get("consigne", ""))
            self.boite_multi.setVisible(bool(Q.actions_multiples(p.get("action", ""))))
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
        p["enchainer"] = self.p_enchainer.isChecked()
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
        self.boite_multi.setVisible(bool(Q.actions_multiples(p["action"])))
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
        suivre_en_fond(self, t, _("Séquence IA"))
        self.suivi.demarrer(_("L'IA détaille la consigne du plan"), t)
        i = self._courant

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
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
        suivre_en_fond(self, t, _("Séquence IA"))
        self.suivi.demarrer(_("Composition de l'image de départ du plan {n}", n=i + 1), t,
                            _("Gemini : 10 à 60 s.") if moteur == "gemini" else _("IA de ce poste : une à plusieurs minutes."))

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ Image impossible : {e}", e=texte_erreur(e)[:300]))
                return
            self.seq["plans"][i]["image"] = r
            if self._courant == i:
                self._maj_vignette()
            self.etat.setText(_("Image de départ prête : regardez-la (vignette) ; elle sert de première image au plan."))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    # ------------------------------------------------------------------ fabrication
    def _expliquer_moteur(self):
        m = self.moteur.currentData()
        if m == "locale":
            t = _("IA de ce poste : gratuite. Elle part de l'image du personnage, mais le visage dérive pendant le plan (5 s) et "
                  "change d'un plan à l'autre ; les lèvres ne bougent pas avec la réplique (dite par une voix posée par-dessus). "
                  "Bien pour un plan court, un paysage, une silhouette.")
        elif m == "flow":
            t = _("Google Flow : votre abonnement, pas à pas dans le navigateur ; mêmes possibilités que Gemini.")
        else:
            from . import generateurs_video as GV
            mo = GV.modele(m, self.params) or {}
            if mo.get("references"):
                t = _("Le plus fidèle (votre clef fal.ai, coût affiché avant) : il reçoit la fiche du personnage et la garde "
                      "identique, part de l'image de départ (ou de la fin du plan précédent) et rejoint l'image d'arrivée ; jusqu'à "
                      "15 s par plan.")
            elif mo.get("fournisseur") == "fal":
                t = _("{n} (votre clef fal.ai, coût affiché avant) : part de l'image de départ ; le visage peut dériver pendant le "
                      "plan. Pour garder le personnage, préférez « Kling O3 Référence ».", n=mo.get("nom", m))
            else:
                t = _("Gemini (votre clef, coût affiché avant) : il mélange les images du personnage et du lieu et joue la réplique ; "
                      "le visage peut dériver. Pour garder le personnage, préférez « Kling O3 Référence ».")
        self.explication_moteur.setText(t)

    def _maj_moteur(self, *_a):
        self._expliquer_moteur()
        m = self.moteur.currentData()
        self.seq["moteur"] = m
        flow = m == "flow"
        self.b_flow.setVisible(flow)
        self.aide_flow.setVisible(flow)
        self.b_plan.setVisible(not flow)
        self.b_tout.setVisible(not flow)
        if hasattr(self, "credit"):
            from .credit_ia import fournisseur_du_moteur
            f_ = fournisseur_du_moteur(m, self.params)
            if f_ != self.credit.fournisseur:
                self.credit.montrer(f_)
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
                                n=manquants, p=f"{Q.prix_total(self.seq, m, self.params):.2f}".replace(".", ",")))

    def _confirmer(self, indices):
        m = self.moteur.currentData()
        if m in ("locale", "flow"):
            return True
        from . import generateurs_video as GV
        mo = GV.modele(m, self.params)
        son = self.seq.get("voix") == "moteur"
        from .recettes_ia import PRIX_GEMINI
        auto = self.seq.get("image_auto", True) and self.params.get("clef_gemini")
        fin = bool((mo or {}).get("references")) and self.seq.get("image_fin_auto", True) and self.params.get("clef_gemini")
        prix = round(sum(GV.prix(mo, int(self.seq["plans"][i].get("duree") or Q.DUREE_PLAN), son) +
                         (PRIX_GEMINI["image"] if auto and not self.seq["plans"][i].get("image") and
                          Q.images_du_plan(self.seq, self.seq["plans"][i]) else 0.0) +
                         (PRIX_GEMINI["image"] if fin and not self.seq["plans"][i].get("image_fin") else 0.0)
                         for i in indices), 2) if mo else 0
        if fin:
            prix = round(prix + PRIX_GEMINI["image"] * len(Q.sans_planche(self.seq, indices)), 2)
        doubles = [i + 1 for i in indices if Q.actions_multiples(self.seq["plans"][i].get("action"))]
        avert = ("\n\n" + _("⚠ Plan(s) {l} : deux actions enchaînées, les gestes risquent d'être incohérents. « Une action par "
                             "plan » les coupe en deux.", l=", ".join(map(str, doubles)))) if doubles else ""
        return QMessageBox.question(self, _("Séquence IA"), _("Fabriquer {n} plan(s) avec {m} pour au plus {p} $ environ (votre clef) ?",
                                                              n=len(indices), m=(mo or {}).get("nom", m), p=prix) + avert) == QMessageBox.Yes

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

    def verifier_images(self, indices=None):
        """0.9.73 : départ et arrivée de chaque plan vus et validés avant la vidéo."""
        self._lire_tables()
        if indices is None:
            indices = [i for i, p in enumerate(self.seq["plans"]) if not p.get("fichier")] or list(range(len(self.seq["plans"])))
        if not indices:
            self.etat.setText(_("Pas encore de plan : découpez d'abord l'histoire."))
            return None
        if not self.params.get("clef_gemini"):
            self.etat.setText(_("Les images se composent avec Gemini : Préférences › IA › Connecter une IA."))
            return None
        anc = getattr(self, "_revue", None)
        try:
            if anc is not None and (anc.isVisible() or anc._en_calcul()):
                anc.show()
                anc.raise_()
                return anc
        except RuntimeError:
            pass
        from . import dialogues_images_plans as DI
        self._revue = DI.ouvrir(self, self.seq, self.params, indices, self.ed)
        self._revue.finished.connect(lambda _r: (self._remplir_plans(), self._maj_prix()))
        return self._revue

    def _fabriquer(self, indices):
        a_voir = Q.images_a_verifier(self.seq, indices, self.params, self.moteur.currentData())
        if a_voir:
            r = QMessageBox.question(self, _("Séquence IA"), _(
                "Avant la vidéo, regardez l'image de départ et d'arrivée des plans {l} (Gemini les compose, quelques centimes) : "
                "s'il se trompe, la vidéo serait forcée vers l'erreur. Les préparer et les voir maintenant ?",
                l=", ".join(str(i + 1) for i in a_voir)))
            if r == QMessageBox.Yes:
                self.verifier_images(a_voir)
            return
        if not self._confirmer(indices):
            return
        m = self.moteur.currentData()
        for i in indices:
            p = self.seq["plans"][i]
            ancienne = p.get("consigne", "")
            if not ancienne or (ancienne.startswith("Cinematic shot,") and "One single simple action" not in ancienne):
                p["consigne"] = Q.consigne(self.seq, p, self.params)      # écrite par PhilCut avant 0.9.70 : refaite
        seq = copy.deepcopy(self.seq)

        def travail(tache):
            faits, erreur = {}, None
            for k, i in enumerate(indices):
                if tache.arret:
                    break
                tache.avancer(k / len(indices), _("plan {i} ({k} sur {n})", i=i + 1, k=k + 1, n=len(indices)))
                try:
                    Q.planches_manquantes(seq, seq["plans"][i], self.params, m)
                    f = Q.fabriquer_plan(seq, i, self.params, m,
                                         progression=lambda f, k=k: tache.avancer((k + f) / len(indices)), arret=lambda: tache.arret)
                except InterruptedError:
                    break
                except Exception as e:      # noqa: BLE001 : les plans déjà payés sont gardés, l'erreur est dite
                    erreur = e
                    break
                seq["plans"][i]["fichier"] = f                    # le plan suivant peut démarrer sur sa dernière image
                faits[i] = (f, seq["plans"][i].get("image", ""), seq["plans"][i].get("image_fin", ""))
            return {"faits": faits, "erreur": erreur, "planches": {p["nom"]: p.get("planche", "") for p in seq["personnages"]}}
        t = Tache(travail, _("Séquence IA"))
        self.taches.append(t)
        suivre_en_fond(self, t, _("Séquence IA"))
        self.suivi.demarrer(_("Fabrication de {n} plan(s)", n=len(indices)), t,
                            _("IA de ce poste : plusieurs minutes par plan.") if m == "locale" else _("Cloud : 1 à 6 min par plan."))
        t.progression.connect(lambda f, txt: txt and self.suivi.etape(_("Fabrication : {t} — {p} %", t=txt, p=int(f * 100))),
                              Qt.QueuedConnection)

        def fin(r, e):
            self.suivi.finir()
            r = r or {}
            e = e or r.get("erreur")
            for i, (chemin, image, image_fin) in (r.get("faits") or {}).items():
                self.seq["plans"][i]["fichier"] = chemin
                if image:
                    self.seq["plans"][i]["image"] = image
                if image_fin:
                    self.seq["plans"][i]["image_fin"] = image_fin
            for p in self.seq["personnages"]:
                if (r.get("planches") or {}).get(p["nom"]) and not p.get("planche"):
                    p["planche"] = r["planches"][p["nom"]]
            r = r.get("faits") or {}
            Q.enregistrer(self.seq)
            self._remplir_plans()
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
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
        suivre_en_fond(self, t, _("Séquence IA"))
        self.suivi.demarrer(_("Plan {n} : consigne copiée, Flow ouvert ; PhilCut attend la vidéo téléchargée", n=i + 1), t,
                            _("Dans Flow : images de référence, Ctrl+V, générer, puis « Télécharger »."))

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
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
                if moteur_voix not in ("aucune", "moteur") and seq["plans"][i].get("repliques") and not seq["plans"][i].get("voix"):
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
        suivre_en_fond(self, t, _("Séquence IA"))
        self.suivi.demarrer(_("Préparation du montage (répliques, musique)"), t)
        t.progression.connect(lambda f, txt: txt and self.suivi.etape(_("Préparation : {t} — {p} %", t=txt, p=int(f * 100))),
                              Qt.QueuedConnection)

        def fin(r, e):
            self.suivi.finir()
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
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
        if garder_calcul(self, any(t.isRunning() for t in self.taches)):     # 0.9.64 : rangée, le calcul continue
            return
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


def apercu_planche(parent, chemin, nom=""):
    """Montre la planche du personnage avant de la garder (aperçu avant intégration)."""
    from PySide6.QtWidgets import QDialogButtonBox
    d = QDialog(parent)
    d.setWindowTitle(_("Fiche du personnage « {n} »", n=nom))
    v = QVBoxLayout(d)
    lbl = QLabel()
    lbl.setPixmap(QPixmap(chemin).scaled(900, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    lbl.setAlignment(Qt.AlignCenter)
    v.addWidget(lbl, 1)
    t = QLabel(_("Même visage, même tenue sur les quatre vues ? Gardez-la : elle servira à chaque plan. Sinon, écartez-la et refaites."))
    t.setWordWrap(True)
    v.addWidget(t)
    bb = QDialogButtonBox()
    bb.addButton(_("Garder cette fiche"), QDialogButtonBox.AcceptRole)
    bb.addButton(_("Ecarter"), QDialogButtonBox.RejectRole)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    v.addWidget(bb)
    if getattr(parent, "_test_planche", None) is not None:
        return parent._test_planche
    return d.exec() == QDialog.Accepted
