"""Préférences (jamais « Paramètres ») : Général, Apparence, Export, Assistant et IA, IA locale, Effets et Goodies (packs à
cocher), Comptes, Synchronisation, Mises à jour. Reglages communs a tous les postes ou propres a celui-ci."""
import os, subprocess, sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QTabWidget, QWidget, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
                               QPushButton, QDialogButtonBox, QSpinBox, QFileDialog, QGroupBox, QPlainTextEdit, QMessageBox, QScrollArea, QProgressBar)

from . import effets as E, goodies as GO, ia_locale, moteur, packs_ia, theme
from .config import VERSION, est_portable, dossier_donnees
from .langue import _, disponibles as langues_disponibles
from .widgets import CaseLongue as QCheckBox, a_gauche, page_a_largeur, boutons_fr, oeil


class DialoguePreferences(QDialog):
    def __init__(self, parent, params, onglet=None):
        super().__init__(parent)
        self.setWindowTitle(_("Préférences"))
        self.resize(760, 600)
        self.params = params
        self.fenetre = parent
        v = QVBoxLayout(self)
        self.onglets = QTabWidget()
        v.addWidget(self.onglets, 1)
        self._general()
        self._apparence()
        self._export()
        self._assistant()
        self._tampons()
        self._ia_locale()
        self._packs()
        self._comptes()
        self._maj()
        for i in range(self.onglets.count()):
            page_a_largeur(self.onglets.widget(i))
        self.onglets.setUsesScrollButtons(True)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.valider)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        if onglet is not None:
            noms = [self.onglets.tabText(i) for i in range(self.onglets.count())]
            for i, n in enumerate(noms):
                if onglet.lower() in n.lower():
                    self.onglets.setCurrentIndex(i)

    def _page(self, titre):
        w = QWidget()
        f = QFormLayout(w)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        z = QScrollArea()
        z.setWidgetResizable(True)
        z.setWidget(w)
        z.setFrameShape(QScrollArea.NoFrame)
        self.onglets.addTab(z, titre)
        return f

    # ---------------------------------------------------------------- Général
    def _general(self):
        f = self._page(_("Général"))
        self.auteur = QLineEdit(self.params.get("auteur", ""))
        f.addRow(_("Votre nom (crédits, écran de fin)"), self.auteur)
        self.chaine = QLineEdit(self.params.get("chaine_nom", ""))
        f.addRow(_("Nom de la chaîne / signature"), self.chaine)
        self.langue = QComboBox()
        self.langue.addItem(_("Langue du système"), "auto")
        for code, nom in langues_disponibles():
            self.langue.addItem(nom, code)
            if code == self.params.get("langue"):
                self.langue.setCurrentIndex(self.langue.count() - 1)
        f.addRow(_("Langue (relancer PhilCut)"), self.langue)
        self.machine = QLineEdit(self.params.get("machine", ""))
        f.addRow(_("Nom de ce poste"), self.machine)
        self.proxys = QCheckBox(_("Fabriquer des proxys (copies légères) à l'import — conseillé"))
        self.proxys.setChecked(self.params.get("proxys", True))
        f.addRow(self.proxys)
        h = QHBoxLayout()
        self.dossier_proxys = QLineEdit(self.params.get("dossier_proxys") or moteur.dossier_proxys(self.params))
        b = QPushButton(_("Dossier…"))
        b.clicked.connect(lambda: self._dossier(self.dossier_proxys))
        h.addWidget(self.dossier_proxys, 1)
        h.addWidget(b)
        b2 = QPushButton(_("Vider"))
        b2.clicked.connect(self._vider_proxys)
        h.addWidget(b2)
        f.addRow(_("Dossier des proxys (ce poste)"), h)
        self.ajout_auto = QCheckBox(_("Poser automatiquement le premier rush importé dans la timeline"))
        self.ajout_auto.setChecked(self.params.get("ajout_auto", True))
        f.addRow(self.ajout_auto)
        self.assoc = QCheckBox(_("Ouvrir les fichiers .philcut avec PhilCut (Windows) — les vidéos ne sont jamais associées"))
        self.assoc.setChecked(self.params.get("association_video", False))
        self.assoc.setEnabled(sys.platform == "win32")
        f.addRow(self.assoc)
        f.addRow(QLabel(_("<span style='color:#999'>Données de ce poste : {d}</span>", d=dossier_donnees())))

    # ---------------------------------------------------------------- Apparence
    def _apparence(self):
        f = self._page(_("Apparence"))
        self.theme = QComboBox()
        self.theme.addItem(_("Sombre (vidéo, conseillé)"), "sombre")
        self.theme.addItem(_("Clair (comme PhilPDF)"), "clair")
        self.theme.setCurrentIndex(0 if self.params.get("theme", "sombre") == "sombre" else 1)
        f.addRow(_("Thème (relancer PhilCut)"), self.theme)
        self.barre_style = QComboBox()
        for lib, st in ((_("Icône et nom"), "auto"), (_("Icône seule"), "icone"), (_("Nom seul"), "nom")):
            self.barre_style.addItem(lib, st)
            if st == self.params.get("barre_style", "auto"):
                self.barre_style.setCurrentIndex(self.barre_style.count() - 1)
        f.addRow(_("Boutons de la barre d'outils"), self.barre_style)
        self.barre_taille = QSpinBox()
        self.barre_taille.setRange(14, 40)
        self.barre_taille.setValue(int(self.params.get("barre_taille", 22)))
        f.addRow(_("Taille des icônes"), self.barre_taille)
        b = QPushButton(_("Personnaliser la barre d'outils…"))
        b.clicked.connect(lambda: self.fenetre.personnaliser_barre())
        f.addRow(a_gauche(b))
        self.volet = QComboBox()
        for lib, m in ((_("Complet"), "complet"), (_("Icônes seules"), "icones"), (_("Masqué"), "masque")):
            self.volet.addItem(lib, m)
            if m == self.params.get("volet", "complet"):
                self.volet.setCurrentIndex(self.volet.count() - 1)
        f.addRow(_("Volet de droite"), self.volet)
        self.apercu_images = QCheckBox(_("Aperçu par images (sans lecteur multimédia) — si la lecture plante ou reste noire sur ce poste"))
        self.apercu_images.setChecked(self.params.get("apercu_images", False))
        f.addRow(self.apercu_images)

    # ---------------------------------------------------------------- Export
    def _export(self):
        f = self._page(_("Export"))
        self.dest = QComboBox()
        for k, d in moteur.DESTINATIONS.items():
            self.dest.addItem(d[0], k)
            if k == self.params.get("export_destination", "youtube"):
                self.dest.setCurrentIndex(self.dest.count() - 1)
        f.addRow(_("Destination par défaut"), self.dest)
        self.enc = QComboBox()
        self.enc.addItem(_("Automatique (le plus rapide disponible)"), "")
        for e in moteur.encodeurs():
            self.enc.addItem(moteur.nom_encodeur(e), e)
            if e == self.params.get("encodeur"):
                self.enc.setCurrentIndex(self.enc.count() - 1)
        f.addRow(_("Encodeur (ce poste)"), self.enc)
        f.addRow(QLabel(_("<span style='color:#999'>FFmpeg {v} · encodeurs trouvés : {e}</span>", v=moteur.version() or "?", e=", ".join(moteur.nom_encodeur(x) for x in moteur.encodeurs()))))
        self.ducking = QCheckBox(_("Baisser automatiquement la musique sous la voix (ducking)"))
        self.ducking.setChecked(self.params.get("ducking", True))
        f.addRow(self.ducking)
        h = QHBoxLayout()
        self.musiques = QLineEdit(self.params.get("musiques_dossier", ""))
        b = QPushButton(_("Dossier…"))
        b.clicked.connect(lambda: self._dossier(self.musiques))
        h.addWidget(self.musiques, 1)
        h.addWidget(b)
        f.addRow(_("Dossier de musiques personnel"), h)

    # ---------------------------------------------------------------- Assistant et IA
    def _assistant(self):
        f = self._page(_("Assistant et IA"))
        self.niveau = QComboBox()
        for k, lib in (("recettes", _("Recettes sans IA (gratuit, hors ligne)")), ("locale", _("IA locale (Ollama sur ce poste)")), ("cloud", _("IA cloud (Claude ou Gemini, clef API)"))):
            self.niveau.addItem(lib, k)
            if k == self.params.get("assistant_niveau", "recettes"):
                self.niveau.setCurrentIndex(self.niveau.count() - 1)
        f.addRow(_("Niveau de l'assistant"), self.niveau)
        self.consignes = QPlainTextEdit(self.params.get("ia_consignes_recette", ""))
        self.consignes.setPlaceholderText(_("Vos consignes permanentes : « toujours un plan large au début », « pas de glitch »…"))
        self.consignes.setMaximumHeight(70)
        f.addRow(_("Consignes personnelles"), self.consignes)
        g = QGroupBox(_("IA cloud"))
        fg = QFormLayout(g)
        self.moteur = QComboBox()
        for k, lib in (("claude", _("Claude d'abord, Gemini en secours")), ("gemini", _("Gemini d'abord, Claude en secours"))):
            self.moteur.addItem(lib, k)
            if k == self.params.get("ia_moteur", "claude"):
                self.moteur.setCurrentIndex(self.moteur.count() - 1)
        fg.addRow(_("Ordre"), self.moteur)
        self.clef_claude = QLineEdit(self.params.get("clef_claude", ""))
        self.clef_claude.setEchoMode(QLineEdit.Password)
        oeil(self.clef_claude)
        fg.addRow(_("Clef Claude (sk-ant-…)"), self.clef_claude)
        self.clef_gemini = QLineEdit(self.params.get("clef_gemini", ""))
        self.clef_gemini.setEchoMode(QLineEdit.Password)
        oeil(self.clef_gemini)
        fg.addRow(_("Clef Gemini (Google AI Studio)"), self.clef_gemini)
        self.clef_fal = QLineEdit(self.params.get("clef_fal", ""))
        self.clef_fal.setEchoMode(QLineEdit.Password)
        oeil(self.clef_fal)
        fg.addRow(_("Clef fal.ai (Kling, Seedance…)"), self.clef_fal)
        b_conn = QPushButton(_("Connecter une IA : obtenir et tester ma clef…"))
        b_conn.clicked.connect(self._connecter)
        fg.addRow(a_gauche(b_conn))
        fg.addRow(QLabel(_("<span style='color:#999'>Rien n'est envoyé sans votre clic. Avant chaque envoi, PhilCut vérifie s'il y a des données sensibles et vous demande confirmation. "
                           "Les clefs vont dans le coffre du système, jamais dans un fichier en clair.</span>")))
        self.confirmer_cout = QCheckBox(_("Afficher le coût estimé et demander confirmation avant chaque envoi à l'IA cloud"))
        self.confirmer_cout.setChecked(self.params.get("ia_confirmer_cout", True))
        fg.addRow(self.confirmer_cout)
        self.veo = QCheckBox(_("Autoriser les plans vidéo générés par IA payante (Google, fal.ai… ; prix affiché et confirmation avant chaque plan)"))
        self.veo.setChecked(self.params.get("veo_actif", False))
        fg.addRow(self.veo)
        h = QHBoxLayout()
        self.flow = QLineEdit(self.params.get("dossier_flow", ""))
        self.flow.setPlaceholderText(_("Dossier où Flow / votre navigateur dépose les clips (Téléchargements)"))
        b = QPushButton(_("Dossier…"))
        b.clicked.connect(lambda: self._dossier(self.flow))
        h.addWidget(self.flow, 1)
        h.addWidget(b)
        fg.addRow(_("Dossier surveillé (Flow)"), h)
        f.addRow(g)
        f.addRow(QLabel(_("<span style='color:#999'>L'IA locale (modèles, test du poste, mode poste léger) se règle dans l'onglet « IA locale ».</span>")))

    # ---------------------------------------------------------------- Tampons et extraits en ligne (0.9.9)
    def _tampons(self):
        f = self._page(_("Tampons et extraits"))
        from . import tampons as T0
        from .dialogues_tampons import AJUSTER, CADRAGES, COMMENT, QUAND, placement_defaut
        intro = QLabel(_("Les tampons vidéo sont de petites séquences toutes faites (rembobinage, « tadaa », bip…), vos propres clips et les "
                         "extraits pris en ligne. Montage › Tampons vidéo pour les poser. Ces réglages suivent sur vos autres postes "
                         "(Comptes et synchro), comme la bibliothèque, son ordre et ses favoris."))
        intro.setWordWrap(True)
        f.addRow(intro)
        g0 = QGroupBox(_("Bibliothèque des tampons"))
        f0 = QFormLayout(g0)
        dossier = T0.dossier_tampons(self.params)
        lbl = QLabel(dossier)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f0.addRow(_("Dossier"), lbl)
        sync = "PhilCut" in dossier and dossier != os.path.join(dossier_donnees(), "tampons")
        n0 = QLabel(_("Sur le lieu de synchronisation : la bibliothèque, son ordre et ses favoris sont les mêmes sur tous vos postes.") if sync else
                    _("Sur ce poste seulement. Choisissez un lieu de synchronisation (Comptes et synchro) pour la retrouver sur vos autres postes."))
        n0.setWordWrap(True)
        n0.setStyleSheet("color:#9aa4b2")
        f0.addRow(n0)
        bo = QPushButton(_("Ouvrir le dossier"))
        bo.clicked.connect(lambda: self._ouvrir(dossier))
        f0.addRow(a_gauche(bo))
        self.classement_tampons = QComboBox()
        for k, lib in T0.CLASSEMENTS.items():
            self.classement_tampons.addItem(lib, k)
        self.classement_tampons.setCurrentIndex(max(0, self.classement_tampons.findData(self.params.get("tampons_classement", "perso"))))
        f0.addRow(_("Classer la bibliothèque"), self.classement_tampons)
        n1 = QLabel(_("« Mon ordre » : dans la fenêtre des tampons, glissez les vignettes pour les ranger, ou clic droit › Monter, Descendre, "
                      "★ Favori (toujours en tête)."))
        n1.setWordWrap(True)
        n1.setStyleSheet("color:#9aa4b2")
        f0.addRow(n1)
        f.addRow(g0)
        gp = QGroupBox(_("Poser un tampon dans le film"))
        fp = QFormLayout(gp)
        d = placement_defaut(self.params)
        self.pl_quand = QComboBox()
        for k, lib in QUAND.items():
            self.pl_quand.addItem(lib, k)
        self.pl_quand.setCurrentIndex(max(0, self.pl_quand.findData(d["quand"])))
        fp.addRow(_("Où, par défaut"), self.pl_quand)
        self.pl_comment = QComboBox()
        for k, lib in COMMENT.items():
            self.pl_comment.addItem(lib, k)
        self.pl_comment.setCurrentIndex(max(0, self.pl_comment.findData(d["comment"])))
        fp.addRow(_("Comment"), self.pl_comment)
        self.pl_ajuster = QComboBox()
        for k, lib in AJUSTER.items():
            self.pl_ajuster.addItem(lib, k)
        self.pl_ajuster.setCurrentIndex(max(0, self.pl_ajuster.findData(d["ajuster"])))
        fp.addRow(_("S'il n'a pas la durée de la partie en jaune"), self.pl_ajuster)
        self.pl_cadrage = QComboBox()
        for k, lib in CADRAGES.items():
            self.pl_cadrage.addItem(lib, k)
        self.pl_cadrage.setCurrentIndex(max(0, self.pl_cadrage.findData(d["cadrage"])))
        fp.addRow(_("S'il n'a pas le format du projet (16:9, 9:16…)"), self.pl_cadrage)
        self.pl_son = QCheckBox(_("Par-dessus : garder le son du tampon (sinon on entend le film)"))
        self.pl_son.setChecked(d["son"])
        fp.addRow(self.pl_son)
        self.pl_demander = QCheckBox(_("Toujours demander où et comment, avec ces choix proposés"))
        self.pl_demander.setChecked(d["demander"])
        fp.addRow(self.pl_demander)
        n2 = QLabel(_("La ligne rouge, c'est l'instant affiché dans l'aperçu, sur la ligne de temps. La partie en jaune se choisit par un "
                      "double-clic sur la règle des temps, au début puis à la fin."))
        n2.setWordWrap(True)
        n2.setStyleSheet("color:#9aa4b2")
        fp.addRow(n2)
        f.addRow(gp)
        # banques de vidéos et de sons libres (tampons vidéo, musiques) : clefs gratuites de l'utilisateur
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from . import coffre, tampons as T
        g2 = QGroupBox(_("Vidéos libres pour les tampons (Pixabay, Pexels)"))
        f2 = QFormLayout(g2)
        f2.addRow(QLabel(_("<span style='color:#999'>Clefs gratuites : créez un compte sur le site, copiez la clef de l'API et collez-la ici. "
                           "Elles vont dans le coffre du système et suivent sur vos autres postes si « Synchroniser aussi les mots de passe "
                           "et clefs » est coché (Comptes et synchro). Wikimedia Commons n'a pas besoin de clef.</span>")))
        self.clefs_banques = {}
        for k in ("pixabay", "pexels"):
            h = QHBoxLayout()
            champ = QLineEdit(coffre.lire(T.CLEFS[k]) or "")
            oeil(champ)
            champ.setPlaceholderText(_("Collez votre clef ici"))
            b = QPushButton(_("Créer ma clef…"))
            b.clicked.connect(lambda _c=False, k=k: QDesktopServices.openUrl(QUrl(T.PAGES_CLEF[k])))
            h.addWidget(champ, 1)
            h.addWidget(b)
            f2.addRow(_("Clef {s}", s=T.SOURCES[k]), h)
            self.clefs_banques[k] = champ
        f.addRow(g2)
        # extraits en ligne : guet des téléchargements, yt-dlp (installé au premier usage), accord sur ce qui est permis
        from . import videos_en_ligne as VL
        g3 = QGroupBox(_("Extraits en ligne (sons, films, YouTube)"))
        f3 = QFormLayout(g3)
        self.guetter_tel = QCheckBox(_("Ajouter tout seul à la bibliothèque des tampons ce que je télécharge depuis un site ouvert par PhilCut"))
        self.guetter_tel.setChecked(self.params.get("tampons_guetter", True) is not False)
        f3.addRow(self.guetter_tel)
        self.lbl_ytdlp = QLabel(_("yt-dlp installé sur ce poste.") if VL.ytdlp_installe() else
                                _("yt-dlp pas encore installé : il le sera au premier usage (Tampons vidéo › Vidéos en ligne)."))
        self.lbl_ytdlp.setWordWrap(True)
        hy = QHBoxLayout()
        hy.addWidget(self.lbl_ytdlp, 1)
        by = QPushButton(_("Mettre à jour yt-dlp") if VL.ytdlp_installe() else _("Installer yt-dlp"))
        by.clicked.connect(lambda: self._ytdlp(by))
        hy.addWidget(by)
        f3.addRow(hy)
        legal = QLabel(VL.LEGAL)
        legal.setWordWrap(True)
        legal.setTextFormat(Qt.RichText)
        legal.setStyleSheet("color:#999")
        f3.addRow(legal)
        self.accord_ytdlp = QCheckBox(VL.CONFIRMATION)
        self.accord_ytdlp.setChecked(bool(self.params.get("ytdlp_accord")))
        f3.addRow(self.accord_ytdlp)
        f.addRow(g3)
        gy = QGroupBox(_("Téléchargement des extraits YouTube"))
        fy = QFormLayout(gy)
        self.ytdlp_hauteur = QComboBox()
        for h_, lib in VL.HAUTEURS.items():
            self.ytdlp_hauteur.addItem(lib, h_)
        self.ytdlp_hauteur.setCurrentIndex(max(0, self.ytdlp_hauteur.findData(int(self.params.get("ytdlp_hauteur") or 1080))))
        fy.addRow(_("Qualité maximale"), self.ytdlp_hauteur)
        self.ytdlp_son_seul = QCheckBox(_("Cocher « Le son seulement » par défaut (répliques, musiques)"))
        self.ytdlp_son_seul.setChecked(bool(self.params.get("ytdlp_son_seul")))
        fy.addRow(self.ytdlp_son_seul)
        self.ytdlp_resultats = QSpinBox()
        self.ytdlp_resultats.setRange(10, 100)
        self.ytdlp_resultats.setValue(int(self.params.get("ytdlp_resultats") or 30))
        fy.addRow(_("Résultats par recherche"), self.ytdlp_resultats)
        f.addRow(gy)

    def _ytdlp(self, bouton):
        from . import videos_en_ligne as VL
        from .taches import Tache
        bouton.setEnabled(False)
        self.lbl_ytdlp.setText(_("Mise à jour de yt-dlp…") if VL.ytdlp_installe() else _("Installation de yt-dlp…"))
        def travail(tache):
            r = VL.mettre_a_jour_ytdlp() if VL.ytdlp_installe() else VL.installer_ytdlp(progression=lambda f: tache.avancer(f * 0.3),
                                                                                       arret=tache.arret_demande)
            if not VL.deno_installe():                  # YouTube : yt-dlp a besoin de Deno pour lire les vidéos
                VL.installer_deno(progression=lambda f: tache.avancer(0.3 + f * 0.7), arret=tache.arret_demande)
            return r
        t = Tache(travail, _("yt-dlp"))
        self._tache_ytdlp = t
        t.progression.connect(lambda f, x: self.lbl_ytdlp.setText(_("yt-dlp : {p} %", p=int(f * 100))), Qt.QueuedConnection)

        def fin(r, err):
            try:
                bouton.setEnabled(True)
                bouton.setText(_("Mettre à jour yt-dlp"))
                self.lbl_ytdlp.setText(("✕ " + str(err)[:200]) if err else _("✓ yt-dlp installé et à jour."))
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    # ---------------------------------------------------------------- IA locale (portable)
    def _ia_locale(self):
        f = self._page(_("IA locale"))
        intro = QLabel(_("Tout se range dans le dossier de PhilCut : rien ne s'installe sur le poste, rien ne démarre avec le système. "
                         "Le moteur se lance seulement pendant une analyse, puis s'arrête. Rien ne quitte ce poste. "
                         "Cocher télécharge (taille indiquée), décocher libère la place ; supprimer le dossier de PhilCut efface tout."))
        intro.setWordWrap(True)
        f.addRow(intro)
        self.poste_leger = QCheckBox(_("Mode poste léger : moitié des cœurs, priorité basse (le poste reste utilisable, l'analyse est plus lente)"))
        self.poste_leger.setChecked(self.params.get("ia_poste_leger", True))
        f.addRow(self.poste_leger)
        carte = packs_ia.carte_graphique()
        self.ia_gpu = QCheckBox(_("Utiliser la carte graphique (Vulkan) : {c}", c=carte) if carte else
                                _("Utiliser la carte graphique (Vulkan) si ce poste en a une — aucune carte dédiée détectée ici"))
        self.ia_gpu.setChecked(self.params.get("ia_gpu", True))
        self.ia_gpu.setEnabled(bool(carte))
        self.ia_gpu.setToolTip(_("Bien plus rapide. Rien à installer : le moteur Vulkan est rangé dans le dossier de PhilCut ; "
                                 "si la carte ou son pilote pose problème, le processeur prend le relais."))
        f.addRow(self.ia_gpu)
        self.cases_ia = {}
        try:
            catalogue = packs_ia.modeles()
            erreur = None
        except packs_ia.ErreurIA as e:
            catalogue, erreur = {}, e
        if not catalogue:
            f.addRow(QLabel(_("Catalogue des modèles injoignable pour l'instant (hors ligne ?). Revenez ici une fois connecté. {e}", e=erreur or "")))
        etat = self.params.get("ia_locale") or {}
        conseil = etat.get("conseil") or ia_locale.modele_conseille(etat.get("materiel") or ia_locale.materiel())
        from . import essai_ia
        self.lbl_essais = {}
        # vérifier que les modèles installés marchent vraiment ici (progression visible, non bloquant)
        gv = QGroupBox(_("Vérifier les modèles installés"))
        fv = QVBoxLayout(gv)
        lv = QLabel(_("Chaque modèle fait un petit travail réel, chronométré : on sait qu'il marche sur ce poste, avec la carte graphique ou le "
                      "processeur, et en combien de temps. Vous pouvez continuer à travailler pendant le test."))
        lv.setWordWrap(True)
        fv.addWidget(lv)
        self.essai_etape = QLabel("")
        self.essai_etape.setWordWrap(True)
        self.essai_barre = QProgressBar()
        self.essai_barre.setRange(0, 1000)
        self.essai_etape.hide()
        self.essai_barre.hide()
        fv.addWidget(self.essai_etape)
        fv.addWidget(self.essai_barre)
        hv = QHBoxLayout()
        self.b_essais = QPushButton(_("Tester les modèles installés"))
        self.b_essais.clicked.connect(lambda: self._tester_modeles(None))
        self.b_essais_stop = QPushButton(_("Arrêter le test"))
        self.b_essais_stop.hide()
        hv.addWidget(self.b_essais)
        hv.addWidget(self.b_essais_stop)
        hv.addStretch(1)
        fv.addLayout(hv)
        f.addRow(gv)
        for genre, titre in packs_ia.GENRES.items():
            items = {k: m for k, m in catalogue.items() if m.get("genre") == genre}
            if not items:
                continue
            g = QGroupBox(titre)
            fg = QFormLayout(g)
            for k, m in items.items():
                deja = packs_ia.installe(k)
                taille = packs_ia.taille_texte(m.get("taille", 0))
                lib = f"{m['nom']}  —  {taille}"
                gestion = getattr(self.fenetre, "telechargements", None)
                if gestion is not None and gestion.en_file(k):
                    lib += "  ⬇ " + _("en cours de téléchargement")
                elif deja:
                    lib += "  ✓ " + _("sur ce poste")
                elif k == conseil:
                    lib += "  ★ " + _("conseillé ici")
                c = QCheckBox(lib)
                c.setChecked(deja)
                note = m.get("note") or ""
                if m.get("memoire_go"):
                    note += " " + _("Mémoire conseillée : {n} Go.", n=m["memoire_go"])
                c.setToolTip((note + "\n" + _("Source : {s}", s=m.get("source", ""))).strip())
                self.cases_ia[k] = c
                fg.addRow(c)
                if note:
                    ln = QLabel(f"<span style='color:#999'>{note.strip()}</span>")
                    ln.setWordWrap(True)
                    fg.addRow(ln)
            if genre in essai_ia.ESSAIS and any(packs_ia.installe(k) for k in items):
                if genre in ("image", "video"):
                    av = QLabel(_("Sans carte graphique dédiée, les images et vidéos IA sont lentes et le résultat reste faible."))
                    av.setWordWrap(True)
                    av.setStyleSheet("color:#e0a040")
                    fg.addRow(av)
                re_ = ResultatEssai(self.params, genre, lambda g=genre: self._tester_modeles([g]))
                re_.montrer((self.params.get("essais_ia") or {}).get(genre))
                self.lbl_essais[genre] = re_
                fg.addRow(re_)
            f.addRow(g)
        h = QHBoxLayout()
        self.lbl_place = QLabel(_("Place utilisée par l'IA locale : {t}", t=packs_ia.taille_texte(packs_ia.taille_dossier()) if packs_ia.installes() else "0"))
        bo = QPushButton(_("Ouvrir le dossier"))
        bo.clicked.connect(lambda: self._ouvrir(packs_ia.dossier()))
        bt = QPushButton(_("Voir les téléchargements…"))
        bt.setToolTip(_("Ce qui se télécharge : progression, vitesse, temps restant, file d'attente"))
        bt.clicked.connect(lambda: hasattr(self.fenetre, "voir_telechargements") and self.fenetre.voir_telechargements())
        h.addWidget(self.lbl_place, 1)
        h.addWidget(bt)
        h.addWidget(bo)
        f.addRow(h)
        g2 = QGroupBox(_("Test de ce poste"))
        fl = QFormLayout(g2)
        self.lbl_locale = QLabel(etat.get("avis") or _("Pas encore testé. Le test regarde le matériel, démarre le moteur, chronomètre une petite question, puis l'arrête."))
        self.lbl_locale.setWordWrap(True)
        fl.addRow(self.lbl_locale)
        mat = etat.get("materiel")
        if mat:
            fl.addRow(QLabel(_("<span style='color:#999'>{s} · {p} ({c} cœurs) · {m} Go · {g}{v}</span>", s=mat.get("systeme"), p=mat.get("processeur", "")[:40], c=mat.get("coeurs"),
                               m=mat.get("memoire_go"), g=mat.get("gpu") or _("carte inconnue"), v=f" {mat.get('vram_go')} Go" if mat.get("vram_go") else "")))
        self.b_test = QPushButton(_("Tester l'IA locale maintenant"))
        self.b_test.clicked.connect(self._tester_locale)
        fl.addRow(a_gauche(self.b_test))
        f.addRow(g2)

    def _ouvrir(self, chemin):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(chemin))

    def _connecter(self):
        from .dialogues_connexion_ia import DialogueConnexionIA
        from .ia import nettoyer_clef
        for k, champ in (("clef_claude", self.clef_claude), ("clef_gemini", self.clef_gemini), ("clef_fal", self.clef_fal)):
            self.params[k] = nettoyer_clef(champ.text())
        d = DialogueConnexionIA(self, self.params)
        if d.exec() == QDialog.Accepted:
            self.clef_claude.setText(self.params.get("clef_claude", ""))
            self.clef_gemini.setText(self.params.get("clef_gemini", ""))
            self.clef_fal.setText(self.params.get("clef_fal", ""))

    def _tester_modeles(self, genres=None):
        from . import essai_ia
        from .taches import Tache
        import time as _t
        self.params["ia_gpu"] = self.ia_gpu.isChecked()
        genres = genres or essai_ia.genres_installes(self.params)
        if not genres:
            self.essai_etape.setText(_("Aucun modèle installé à tester : cochez-en un ci-dessous."))
            self.essai_etape.show()
            return
        t = Tache(lambda tache: essai_ia.tester_tout(self.params, genres, tache.avancer, tache.arret_demande), _("Test des modèles d'IA"))
        self._tache_essais = t
        from . import activite
        activite.centre().suivre(t, _("Test des modèles d'IA locale"))
        if hasattr(self.fenetre, "taches"):
            self.fenetre.taches.append(t)
        t0 = _t.monotonic()
        self.b_essais.setEnabled(False)
        self.b_essais_stop.show()
        try:
            self.b_essais_stop.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.b_essais_stop.clicked.connect(t.stopper)
        self.essai_etape.setText(_("Préparation du test…"))
        self.essai_etape.show()
        for g in genres:
            if g in self.lbl_essais:
                self.lbl_essais[g].en_cours(_("En attente du test…") if len(genres) > 1 else "")
        rang = {g: i for i, g in enumerate(genres)}
        self.essai_barre.setValue(0)
        self.essai_barre.show()

        def prog(f, texte):
            try:
                e = int(_t.monotonic() - t0)
                self.essai_barre.setValue(int(f * 1000))
                self.essai_barre.setFormat(_("{p} % · temps écoulé {t}", p=int(f * 100), t=f"{e // 60}:{e % 60:02d}"))
                if texte:
                    self.essai_etape.setText(texte)
                i = min(len(genres) - 1, int(f * len(genres)))           # le modèle testé en ce moment montre son avancement
                g = genres[i]
                if g in self.lbl_essais:
                    sous = texte.split(" : ", 1)[-1] if texte else ""
                    self.lbl_essais[g].avancer(f * len(genres) - i, sous)
            except RuntimeError:
                pass

        def fin(res, err):
            self.params.enregistrer()
            try:
                self.b_essais.setEnabled(True)
                self.b_essais_stop.hide()
                self.essai_barre.hide()
                for g, r in (res or {}).items():
                    if g in self.lbl_essais:
                        self.lbl_essais[g].montrer(r)
                for g in genres:                                   # interrompu : on remet le résultat précédent
                    if g not in (res or {}) and g in self.lbl_essais:
                        self.lbl_essais[g].montrer((self.params.get("essais_ia") or {}).get(g))
                ok = sum(1 for r in (res or {}).values() if r.get("ok"))
                self.essai_etape.setText(_("Test interrompu : {e}", e=err) if err else
                                         _("Test terminé : {o} modèle(s) sur {n} fonctionnent.", o=ok, n=len(res or {})))
            except RuntimeError:
                pass
        t.progression.connect(prog, Qt.QueuedConnection)
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _tester_locale(self):
        from .taches import Tache
        self.params["ia_poste_leger"] = self.poste_leger.isChecked()
        self.params["ia_gpu"] = self.ia_gpu.isChecked()
        self.lbl_locale.setText(_("Test en cours : démarrage du moteur et chargement du modèle (jusqu'à quelques minutes)…"))
        self.b_test.setEnabled(False)
        t = Tache(lambda tache: ia_locale.tester(self.params), _("Test IA locale"))
        self._tache_test = t
        from . import activite
        activite.centre().suivre(t, _("Test de l'IA locale sur ce poste"))
        if hasattr(self.fenetre, "taches"):
            self.fenetre.taches.append(t)

        def fin(res, err):
            if not err:
                self.params["ia_locale"] = res
                self.params.enregistrer()
            try:                    # la fenêtre des préférences a pu être fermée entre-temps
                self.b_test.setEnabled(True)
                self.lbl_locale.setText(_("Test interrompu : {e}", e=err) if err else res.get("avis", ""))
            except RuntimeError:
                pass
        t.fini.connect(fin)
        t.start()

    # ---------------------------------------------------------------- Effets et Goodies (packs)
    def _packs(self):
        f = self._page(_("Effets et Goodies"))
        f.addRow(QLabel(_("Tous les effets sont listés dans PhilCut. Ceux qui demandent un téléchargement se cochent ici : cocher télécharge sur ce poste, décocher libère la place. "
                          "Le catalogue se met à jour en ligne.")))
        self.cases_packs = {}
        coches = set(self.params.get("effets_coches") or [])
        for k, p in E.PACKS.items():
            if p.get("ia"):
                pret = packs_ia.modele_actif(p["ia"]) is not None
                f.addRow(QLabel(f"{p['nom']}  —  " + (_("✓ sur ce poste") if pret else _("se règle dans l'onglet « IA locale »"))))
                continue
            c = QCheckBox(f"{p['nom']}  —  {p.get('taille', '')}")
            c.setToolTip(p.get("description", ""))
            c.setChecked(k in coches)
            self.cases_packs[k] = c
            f.addRow(c, QLabel(f"<span style='color:#999'>{p.get('description', '')}</span>"))
        f.addRow(QLabel(_("<b>Packs de Goodies</b>")))
        self.cases_goodies = {}
        gc = set(self.params.get("goodies_coches") or ["aviation", "maison"])
        for k, p in GO.PACKS.items():
            c = QCheckBox(p["nom"])
            c.setToolTip(p["description"])
            c.setChecked(k in gc)
            self.cases_goodies[k] = c
            f.addRow(c, QLabel(f"<span style='color:#999'>{p['description']}</span>"))
        b = QPushButton(_("Chercher de nouveaux effets en ligne"))
        b.clicked.connect(lambda: QMessageBox.information(self, _("Catalogue"), _("{n} effet(s) ajouté(s).", n=E.catalogue_en_ligne())))
        f.addRow(a_gauche(b))

    # ---------------------------------------------------------------- Comptes et synchro (repris de PhilPDF)
    def _comptes(self):
        f = self._page(_("Comptes et synchro"))
        try:
            from .dialogues_distant import PanneauComptes
            self.panneau_comptes = PanneauComptes(self, self.params)
            f.addRow(self.panneau_comptes)
        except Exception as e:      # noqa: BLE001
            self.panneau_comptes = None
            f.addRow(QLabel(_("Comptes indisponibles : {e}", e=e)))
        self.synchro = QCheckBox(_("Synchroniser les projets ouverts et les préférences entre mes postes"))
        self.synchro.setChecked(self.params.get("synchro", True))
        f.addRow(self.synchro)
        self.synchro_secrets = QCheckBox(_("Synchroniser aussi les mots de passe et clefs (chiffrés par une phrase secrète)"))
        self.synchro_secrets.setChecked(self.params.get("synchro_secrets", False))
        f.addRow(self.synchro_secrets)
        b = QPushButton(_("Choisir l'emplacement de synchronisation…"))
        b.clicked.connect(lambda: self.fenetre.bienvenue(seulement_synchro=True))
        f.addRow(a_gauche(b))
        h = QHBoxLayout()
        be = QPushButton(_("Exporter les préférences…"))
        be.clicked.connect(lambda: self.fenetre.exporter_reglages(self))
        bi = QPushButton(_("Importer des préférences…"))
        bi.clicked.connect(lambda: self.fenetre.importer_reglages())
        h.addWidget(be)
        h.addWidget(bi)
        h.addStretch(1)
        f.addRow(h)

    # ---------------------------------------------------------------- Mises a jour
    def _maj(self):
        f = self._page(_("Mises à jour"))
        self.maj_auto = QCheckBox(_("Vérifier au démarrage (une fois par jour) ; la mise à jour est proposée, jamais imposée"))
        self.maj_auto.setChecked(self.params.get("maj_auto", True))
        f.addRow(self.maj_auto)
        self.maj_source = QComboBox()
        self.maj_source.addItem(_("GitHub (PhilouElChapo/PhilCut)"), "github")
        self.maj_source.addItem(_("Dossier synchronisé (Drive, NAS)"), "dossier")
        self.maj_source.setCurrentIndex(0 if self.params.get("maj_source", "github") == "github" else 1)
        f.addRow(_("Source"), self.maj_source)
        b = QPushButton(_("Vérifier maintenant"))
        b.clicked.connect(lambda: self.fenetre.verifier_maj(silencieux=False))
        f.addRow(a_gauche(b))
        f.addRow(QLabel(_("<span style='color:#999'>PhilCut {v} · FFmpeg {f} · Les moteurs open source sont surveillés chaque semaine sur GitHub : une nouvelle version recompilée et testée vous est proposée.</span>", v=VERSION, f=moteur.version() or "?")))

    # ---------------------------------------------------------------- outils
    def _dossier(self, champ):
        p = QFileDialog.getExistingDirectory(self, _("Choisir un dossier"), champ.text() or os.path.expanduser("~"))
        if p:
            champ.setText(p)

    def _vider_proxys(self):
        d = self.dossier_proxys.text()
        n = 0
        try:
            for f in os.listdir(d):
                if f.endswith(".mp4"):
                    os.remove(os.path.join(d, f))
                    n += 1
        except OSError:
            pass
        QMessageBox.information(self, _("Proxys"), _("{n} proxy(s) supprimé(s). Ils seront refaits à la demande.", n=n))

    def valider(self):
        p = self.params
        p["auteur"] = self.auteur.text().strip()
        p["chaine_nom"] = self.chaine.text().strip()
        p["langue"] = self.langue.currentData()
        p["machine"] = self.machine.text().strip() or p.get("machine")
        p["tampons_guetter"] = self.guetter_tel.isChecked()
        p["ytdlp_accord"] = self.accord_ytdlp.isChecked()
        p["ytdlp_hauteur"] = self.ytdlp_hauteur.currentData()
        p["ytdlp_son_seul"] = self.ytdlp_son_seul.isChecked()
        p["ytdlp_resultats"] = self.ytdlp_resultats.value()
        p["tampons_classement"] = self.classement_tampons.currentData()
        p["tampons_placement"] = {"quand": self.pl_quand.currentData(), "comment": self.pl_comment.currentData(),
                                  "ajuster": self.pl_ajuster.currentData(), "son": self.pl_son.isChecked(), "demander": self.pl_demander.isChecked(),
                                  "cadrage": self.pl_cadrage.currentData()}
        p["proxys"] = self.proxys.isChecked()
        p["dossier_proxys"] = self.dossier_proxys.text().strip()
        p["ajout_auto"] = self.ajout_auto.isChecked()
        if self.assoc.isChecked() != p.get("association_video", False):
            from .config import associer_projets
            try:
                associer_projets(self.assoc.isChecked())
            except Exception:
                pass
        p["association_video"] = self.assoc.isChecked()
        p["theme"] = self.theme.currentData()
        p["barre_style"] = self.barre_style.currentData()
        p["barre_taille"] = self.barre_taille.value()
        p["volet"] = self.volet.currentData()
        p["apercu_images"] = self.apercu_images.isChecked()
        p["export_destination"] = self.dest.currentData()
        p["encodeur"] = self.enc.currentData()
        p["ducking"] = self.ducking.isChecked()
        p["musiques_dossier"] = self.musiques.text().strip()
        p["assistant_niveau"] = self.niveau.currentData()
        p["ia_consignes_recette"] = self.consignes.toPlainText().strip()
        p["ia_moteur"] = self.moteur.currentData()
        p["clef_claude"] = self.clef_claude.text().strip()
        from . import coffre, tampons as T
        for k, champ in getattr(self, "clefs_banques", {}).items():      # clefs Pixabay, Pexels : coffre du système
            v = champ.text().strip()
            if v != (coffre.lire(T.CLEFS[k]) or ""):
                coffre.enregistrer(T.CLEFS[k], v) if v else coffre.supprimer(T.CLEFS[k])
        p["clef_gemini"] = self.clef_gemini.text().strip()
        p["clef_fal"] = self.clef_fal.text().strip()
        p["veo_actif"] = self.veo.isChecked()
        p["ia_confirmer_cout"] = self.confirmer_cout.isChecked()
        p["dossier_flow"] = self.flow.text().strip()
        avant = set(p.get("effets_coches") or [])
        apres = {k for k, c in self.cases_packs.items() if c.isChecked()}
        p["effets_coches"] = sorted(apres)
        p["goodies_coches"] = sorted(k for k, c in self.cases_goodies.items() if c.isChecked())
        p["synchro"] = self.synchro.isChecked()
        p["synchro_secrets"] = self.synchro_secrets.isChecked()
        p["maj_auto"] = self.maj_auto.isChecked()
        p["maj_source"] = self.maj_source.currentData()
        if self.panneau_comptes is not None and hasattr(self.panneau_comptes, "appliquer"):
            try:
                self.panneau_comptes.appliquer()
            except Exception:
                pass
        p["ia_poste_leger"] = self.poste_leger.isChecked()
        p["ia_gpu"] = self.ia_gpu.isChecked()
        gestion = getattr(self.fenetre, "telechargements", None)
        a_installer = [k for k, c in self.cases_ia.items() if c.isChecked() and not packs_ia.installe(k)
                       and not (gestion is not None and gestion.en_file(k))]
        a_retirer = [k for k, c in self.cases_ia.items() if not c.isChecked() and packs_ia.installe(k)]
        if a_installer or a_retirer:
            lignes = []
            if a_installer:
                total = sum(packs_ia.a_telecharger(k) for k in a_installer)
                lignes.append(_("Télécharger dans le dossier de PhilCut : {l} ({t} en tout).", l=", ".join(packs_ia.modeles()[k]["nom"] for k in a_installer),
                                t=packs_ia.taille_texte(total)))
            if a_retirer:
                lignes.append(_("Retirer de ce poste : {l}.", l=", ".join((packs_ia.etat().get(k) or {}).get("nom", k) for k in a_retirer)))
            if QMessageBox.question(self, _("IA locale"), "\n\n".join(lignes) + "\n\n" + _("Continuer ?")) != QMessageBox.Yes:
                return
            for k in a_retirer:
                packs_ia.supprimer(k)
        p.enregistrer()
        if p.get("synchro_secrets"):                 # clefs et mots de passe vers les autres postes : phrase secrète une fois
            from . import coffre, reglages
            from .dialogues_phrase import demander_phrase
            if not coffre.lire(reglages.PHRASE):
                deja = reglages.chemin_secrets(p) and os.path.exists(reglages.chemin_secrets(p))
                demander_phrase(self, p, nouvelle=not deja)
            else:
                reglages.synchro_secrets_auto(p)
        for k in apres - avant:
            self.fenetre.telecharger_pack(k)
        if a_installer:
            self.fenetre.installer_ia(a_installer)
        self.accept()


class ResultatEssai(QWidget):
    """Résultat du test d'un modèle, lisible : une ligne verte ou rouge (marche ou non, en combien de temps), sur quoi et
    quand, le bouton « Tester » ; en cas d'échec, la cause en clair et les solutions en boutons (PanneauDiagnostic)."""

    def __init__(self, params, genre, tester):
        super().__init__()
        from .dialogues_diagnostic import PanneauDiagnostic
        self.genre = genre
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 4, 0, 4)
        self.ligne = QLabel("")
        self.ligne.setWordWrap(True)
        v.addWidget(self.ligne)
        self.sous = QLabel("")
        self.sous.setWordWrap(True)
        self.sous.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.sous)
        # test en cours : on le dit tout de suite (l'ancien résultat disparaît), avec sa progression
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.setMaximumHeight(12)
        self.barre.setTextVisible(False)
        self.barre.hide()
        v.addWidget(self.barre)
        self.panneau = PanneauDiagnostic(self, params, reessayer=tester)
        from PySide6.QtWidgets import QSizePolicy
        self.panneau.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        v.addWidget(self.panneau)
        from . import essai_ia
        self.b_tester = QPushButton(_("Tester ce modèle"))
        self.b_tester.setToolTip(_("Fait un petit travail réel avec ce modèle et chronomètre : {q}", q=essai_ia.ESSAIS.get(genre, "")))
        self.b_tester.clicked.connect(tester)
        v.addLayout(a_gauche(self.b_tester))
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

    def _relayout(self):
        """Le cadre grandit ou rétrécit avec son contenu : rien ne s'écrase dans le groupe ni dans la page."""
        w = self
        while w is not None:
            if w.layout() is not None:
                w.layout().invalidate()
                w.layout().activate()
            w.updateGeometry()
            w = w.parentWidget()

    def en_cours(self, texte=""):
        self.panneau.hide()
        self.sous.hide()
        self.ligne.setStyleSheet("color:#c8ced8;font-weight:600")
        self.ligne.setText("⏳ " + (texte or _("Test en cours…")))
        self.barre.setValue(0)
        self.barre.show()
        self.b_tester.setEnabled(False)
        self._relayout()

    def avancer(self, f, texte=""):
        self.barre.setValue(int(max(0.0, min(1.0, f)) * 1000))
        if texte:
            self.ligne.setText("⏳ " + texte)

    def montrer(self, r):
        from . import essai_ia
        self.barre.hide()
        self.b_tester.setEnabled(True)
        self.ligne.setText(essai_ia.resume(r))
        couleur = "#9aa4b2" if not r else ("#5bd27a" if r.get("ok") else "#ff8a80")
        self.ligne.setStyleSheet(f"color:{couleur};font-weight:600")
        self.sous.setText(essai_ia.sous_titre(r))
        self.sous.setVisible(bool(r))
        if r and not r.get("ok") and r.get("message") != _("Test arrêté."):
            self.panneau.montrer(r.get("detail") or r.get("message", ""), self.genre, r.get("journal") or None, r.get("moteur") or None,
                                 r.get("peripherique") or "")
        else:
            self.panneau.hide()
        self._relayout()

    def setText(self, texte):              # compatibilité : ancien libellé simple
        self.ligne.setText(texte)
