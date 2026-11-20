"""Fenêtres des animations (0.9.99) : « Ma charte » (couleurs, polices, logo, allure ; tirée d'un logo, d'une image ou d'un
site) et « Animation » (chiffres, barres, courbe, titre animé : décrire, coller ses données, voir trois propositions, régler
au curseur, choisir le moteur conseillé, fabriquer, regarder, poser)."""
import copy, os, webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QRadioButton, QScrollArea, QSlider,
                               QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from . import charte as CH, motion as M
from .langue import _
from .taches import Tache, texte_erreur
from .widgets import boutons_fr


def _alpha(t):
    import unicodedata
    return "".join(x for x in unicodedata.normalize("NFD", t or "") if unicodedata.category(x) != "Mn").casefold()


# ====================================================================== Ma charte
class DialogueCharte(QDialog):
    """Une charte à régler ; « Tirer d'un logo ou d'une image… », « Tirer de mon site… » proposent couleurs, polices et logo,
    toujours modifiables. Ce qui se lirait mal est dit en orange, avec « Rendre lisible »."""

    def __init__(self, parent, params, ident=None):
        super().__init__(parent)
        self.params = params
        self.setWindowTitle(_("Ma charte (couleurs, polices, logo)"))
        self.resize(720, 640)
        v = QVBoxLayout(self)
        intro = QLabel(_("Renseignée une fois, la charte est reprise par toutes les animations (chiffres, graphiques, titres) et "
                         "vous suit sur vos autres postes. Rien n'est envoyé à une IA ici."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        h = QHBoxLayout()
        self.liste = QComboBox()
        self.liste.currentIndexChanged.connect(self._choisie)
        h.addWidget(QLabel(_("Charte")))
        h.addWidget(self.liste, 1)
        for lib, f in ((_("Nouvelle"), self.nouvelle), (_("Tirer d'un logo ou d'une image…"), self.depuis_image),
                       (_("Tirer de mon site…"), self.depuis_site)):
            b = QPushButton(lib)
            b.clicked.connect(f)
            h.addWidget(b)
        v.addLayout(h)
        self.b_retirer = QPushButton(_("Retirer cette charte"))
        self.b_retirer.clicked.connect(self.retirer)
        g = QGroupBox(_("Réglages"))
        f = QFormLayout(g)
        self.nom = QLineEdit()
        f.addRow(_("Nom"), self.nom)
        self.boutons = {}
        hc = QHBoxLayout()
        for role in CH.ROLES:
            b = QPushButton(CH.NOMS_ROLES[role])
            b.setToolTip(_("Choisir la couleur « {r} »", r=CH.NOMS_ROLES[role]))
            b.clicked.connect(lambda _c=False, r=role: self._couleur(r))
            self.boutons[role] = b
            hc.addWidget(b)
        f.addRow(_("Couleurs"), hc)
        from .vignette import polices_proposees
        livrees, systeme = polices_proposees()
        self.p_titre, self.p_texte = QComboBox(), QComboBox()
        for c in (self.p_titre, self.p_texte):
            c.setEditable(True)
            c.addItems(livrees + systeme)
            c.setMaxVisibleItems(18)
        f.addRow(_("Police des titres et chiffres"), self.p_titre)
        f.addRow(_("Police des textes"), self.p_texte)
        hl = QHBoxLayout()
        self.logo = QLabel("")
        self.logo.setFixedHeight(48)
        hl.addWidget(self.logo, 1)
        b = QPushButton(_("Logo…"))
        b.clicked.connect(self._logo)
        hl.addWidget(b)
        b = QPushButton(_("Sans logo"))
        b.clicked.connect(lambda: self._poser_logo(""))
        hl.addWidget(b)
        f.addRow(_("Logo"), hl)
        self.allure, self.mouvement = QComboBox(), QComboBox()
        for k, lib in CH.ALLURES.items():
            self.allure.addItem(lib, k)
        for k, lib in CH.MOUVEMENTS.items():
            self.mouvement.addItem(lib, k)
        f.addRow(_("Allure"), self.allure)
        f.addRow(_("Mouvement"), self.mouvement)
        self.interdits = QLineEdit()
        self.interdits.setPlaceholderText(_("Ce qu'il ne faut jamais faire : « pas de rouge », « pas de police fantaisie »…"))
        f.addRow(_("A éviter"), self.interdits)
        v.addWidget(g)
        self.apercu = QLabel()
        self.apercu.setFixedHeight(200)
        self.apercu.setAlignment(Qt.AlignCenter)
        v.addWidget(self.apercu)
        self.avert = QLabel("")
        self.avert.setWordWrap(True)
        self.avert.setStyleSheet("color:#e0a030")
        v.addWidget(self.avert)
        hb = QHBoxLayout()
        self.b_lisible = QPushButton(_("Rendre lisible"))
        self.b_lisible.setToolTip(_("Ajuste le texte et l'accent pour qu'ils se lisent sur le fond, sans changer l'esprit de la charte"))
        self.b_lisible.clicked.connect(self._lisible)
        hb.addWidget(self.b_lisible)
        hb.addWidget(self.b_retirer)
        hb.addStretch(1)
        v.addLayout(hb)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.valider)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        for w in (self.nom, self.interdits):
            w.textChanged.connect(self._maj)
        for w in (self.p_titre, self.p_texte):
            w.currentTextChanged.connect(self._maj)
        for w in (self.allure, self.mouvement):
            w.currentIndexChanged.connect(self._maj)
        self.ch = None
        self._remplir_liste(ident or (params.get("charte_active") or "defaut"))

    def _remplir_liste(self, ident):
        self.liste.blockSignals(True)
        self.liste.clear()
        self.chartes = CH.toutes(self.params)
        for c in self.chartes:
            self.liste.addItem(c["nom"], c["id"])
        i = max(0, next((k for k, c in enumerate(self.chartes) if c["id"] == ident), 0))
        self.liste.setCurrentIndex(i)
        self.liste.blockSignals(False)
        self._choisie(i)

    def _choisie(self, i):
        if 0 <= i < len(self.chartes):
            self.charger(copy.deepcopy(self.chartes[i]))

    def charger(self, ch):
        self.ch = CH.complete(ch)
        self._charge = True
        self.nom.setText(self.ch["nom"])
        self.p_titre.setCurrentText(self.ch["police_titre"])
        self.p_texte.setCurrentText(self.ch["police_texte"])
        self.allure.setCurrentIndex(max(0, self.allure.findData(self.ch.get("allure"))))
        self.mouvement.setCurrentIndex(max(0, self.mouvement.findData(self.ch.get("mouvement"))))
        self.interdits.setText(self.ch.get("interdits") or "")
        self.b_retirer.setEnabled(self.ch["id"] != "defaut")
        self._charge = False
        self._poser_logo(self.ch.get("logo") or "", maj=False)
        self._maj()

    def _lire(self):
        self.ch["nom"] = self.nom.text().strip() or _("Ma charte")
        self.ch["police_titre"] = self.p_titre.currentText().strip() or "Poppins"
        self.ch["police_texte"] = self.p_texte.currentText().strip() or "Poppins"
        self.ch["allure"] = self.allure.currentData()
        self.ch["mouvement"] = self.mouvement.currentData()
        self.ch["interdits"] = self.interdits.text().strip()
        return self.ch

    def _maj(self, *_a):
        if self.ch is None or getattr(self, "_charge", False):
            return
        self._lire()
        for role, b in self.boutons.items():
            c = self.ch["couleurs"][role]
            b.setStyleSheet(f"background:{c};color:{CH.lisible_sur(c)};padding:4px 8px")
        a = M.nouvelle("compteur", self.ch, (1920, 1080))
        a["duree"] = 4.5
        from . import motion_maison as MM
        self.apercu.setPixmap(QPixmap.fromImage(MM.apercu_image(a, 3.4, (356, 200))))
        av = CH.avertissements(self.ch)
        self.avert.setText("⚠ " + " ".join(av) if av else "")
        self.b_lisible.setEnabled(bool(av))

    def _couleur(self, role):
        c = QColorDialog.getColor(QColor(self.ch["couleurs"][role]), self, CH.NOMS_ROLES[role])
        if c.isValid():
            self.ch["couleurs"][role] = c.name().upper()
            self._maj()

    def _lisible(self):
        self.charger(CH.corriger(self._lire()))

    def _logo(self):
        from .widgets import ouvrir_fichier
        f = ouvrir_fichier(self, _("Votre logo"), _("Images (*.png *.jpg *.jpeg *.webp *.svg)"), "images", self.params)
        if f:
            self._poser_logo(f)

    def _poser_logo(self, f, maj=True):
        self.ch["logo"] = f
        pm = QPixmap(f) if f and os.path.exists(f) else QPixmap()
        if pm.isNull():
            self.logo.setPixmap(QPixmap())
            self.logo.setText(_("aucun logo"))
        else:
            self.logo.setPixmap(pm.scaledToHeight(44, Qt.SmoothTransformation))
        if maj:
            self._maj()

    def nouvelle(self):
        ch = copy.deepcopy(CH.DEFAUT)
        ch["id"], ch["nom"] = "", _("Ma charte")
        self.charger(ch)

    def depuis_image(self):
        from .widgets import ouvrir_fichier
        f = ouvrir_fichier(self, _("Logo ou image de votre identité"), _("Images (*.png *.jpg *.jpeg *.webp)"), "images", self.params)
        if not f:
            return
        try:
            self.charger(CH.depuis_image(f))
            self.avert.setText(_("✓ Couleurs tirées de l'image : modifiez ce qui ne vous plaît pas, puis OK."))
        except Exception as e:      # noqa: BLE001
            self.avert.setText("✕ " + texte_erreur(e))

    def depuis_site(self):
        url, ok = QInputDialog.getText(self, _("Tirer de mon site"), _("Adresse de votre site (la page d'accueil est lue, rien d'autre) :"))
        if not ok or not url.strip():
            return
        self.avert.setText(_("Lecture du site…"))
        QApplication.processEvents()
        try:
            self.charger(CH.depuis_site(url.strip(), CH.dossier_logos()))
            self.avert.setText(_("✓ Couleurs, polices et logo tirés du site : vérifiez-les, puis OK."))
        except Exception as e:      # noqa: BLE001
            self.avert.setText("✕ " + _("Site illisible : {e}", e=texte_erreur(e)))

    def retirer(self):
        if self.ch and self.ch["id"] != "defaut" and QMessageBox.question(self, _("Retirer"), _("Retirer la charte « {n} » ?",
                                                                                                 n=self.ch["nom"])) == QMessageBox.Yes:
            CH.retirer(self.params, self.ch["id"])
            self._remplir_liste("defaut")

    def valider(self):
        ch = self._lire()
        if ch["id"] == "defaut":
            if ch == CH.complete(CH.DEFAUT):
                self.params["charte_active"] = "defaut"
                self.resultat = CH.complete(CH.DEFAUT)
                self.params.enregistrer() if hasattr(self.params, "enregistrer") else None
                self.accept()
                return
            ch["id"] = ""                                    # la charte par défaut modifiée devient « Ma charte »
            if ch["nom"] == CH.DEFAUT["nom"]:
                ch["nom"] = _("Ma charte")
        self.resultat = CH.garder(self.params, ch)
        self.params.enregistrer() if hasattr(self.params, "enregistrer") else None
        self.accept()


# ====================================================================== Animation
class DialogueMotion(QDialog):
    """La fenêtre « Animation » (non bloquante, une seule)."""

    def __init__(self, ed, anim=None):
        super().__init__(ed)
        self.ed, self.params = ed, ed.params
        self.tache, self.taches, self.resultat = None, [], None
        self.setWindowTitle(_("Animation : chiffres, graphiques, titres"))
        self.resize(1000, 720)
        taille = tuple(getattr(ed.projet, "taille", (1920, 1080)) or (1920, 1080))
        self.anim = anim or M.nouvelle("chiffres", CH.active(self.params), taille)
        if self.anim.get("pose") is None:
            self.anim["pose"] = float(ed.timeline.position)
        self.anim["cadence"] = int(round(float(getattr(ed.projet, "cadence", 30) or 30))) if not anim else self.anim.get("cadence", 30)
        racine = QVBoxLayout(self)
        corps = QHBoxLayout()
        racine.addLayout(corps, 1)
        # ---------------------------------------------- gauche : ce qu'on veut
        gauche = QWidget()
        gv = QVBoxLayout(gauche)
        gv.setContentsMargins(0, 0, 6, 0)
        self.demande = QPlainTextEdit()
        self.demande.setPlaceholderText(_("Dites ce que vous voulez, par exemple : « le chiffre d'affaires de l'année, 1,2 million, "
                                          "+8 %, puis les ventes par trimestre en barres »"))
        self.demande.setMaximumHeight(70)
        gv.addWidget(self.demande)
        hi = QHBoxLayout()
        self.b_ia = QPushButton(_("✨ Préparer avec l'IA"))
        self.b_ia.setToolTip(_("Votre IA (celle choisie dans l'assistant) remplit la fiche d'après votre phrase : quelques centimes au plus ; "
                               "elle n'invente aucun chiffre"))
        self.b_ia.clicked.connect(self.preparer_ia)
        hi.addWidget(self.b_ia)
        # 1.0.1 : le crédit de l'IA qui prépare et corrige (Claude ou Gemini), avec « Recharger… »
        from .credit_ia import LigneCredit
        self.credit_cerveau = LigneCredit(self.params, {"claude": "anthropic", "gemini": "google"}.get(self._niveau()), self, compact=True)
        hi.addWidget(self.credit_cerveau, 1)
        hi.addStretch(1)
        gv.addLayout(hi)
        f = QFormLayout()
        self.genre = QComboBox()
        for k, d in M.GENRES.items():
            self.genre.addItem(d["nom"], k)
            self.genre.setItemData(self.genre.count() - 1, d["aide"], Qt.ToolTipRole)
        f.addRow(_("Animation"), self.genre)
        self.titre, self.sous_titre, self.badge = QLineEdit(), QLineEdit(), QLineEdit()
        f.addRow(_("Titre"), self.titre)
        f.addRow(_("Sous-titre"), self.sous_titre)
        hv = QHBoxLayout()
        self.prefixe, self.suffixe = QLineEdit(), QLineEdit()
        self.prefixe.setPlaceholderText(_("avant"))
        self.suffixe.setPlaceholderText(_("après : €, %"))
        self.prefixe.setMaximumWidth(70)
        self.suffixe.setMaximumWidth(110)
        self.valeur = QLineEdit()
        self.valeur.setPlaceholderText(_("le total des données"))
        hv.addWidget(self.prefixe)
        hv.addWidget(self.valeur, 1)
        hv.addWidget(self.suffixe)
        self.w_chiffre = QWidget()
        self.w_chiffre.setLayout(hv)
        hv.setContentsMargins(0, 0, 0, 0)
        f.addRow(_("Chiffre"), self.w_chiffre)
        f.addRow(_("Pastille"), self.badge)
        # 1.0.1 : les lignes (chronologie, liste) et le bouton (appel à l'action)
        self.lignes = QPlainTextEdit()
        self.lignes.setPlaceholderText(_("Une ligne par élément ; pour une chronologie : « 2020 : ce qui s'est passé »"))
        self.lignes.setFixedHeight(110)
        f.addRow(_("Lignes"), self.lignes)
        self.bouton = QLineEdit()
        self.bouton.setPlaceholderText(_("le texte du bouton"))
        f.addRow(_("Bouton"), self.bouton)
        self.form1 = f
        gv.addLayout(f)
        # 1.0.0 : sous-titres animés, habillage, calage sur la voix ou la musique
        self.g_contexte = QGroupBox(_("Dans le film"))
        fc = QFormLayout(self.g_contexte)
        hp = QHBoxLayout()
        self.l_pose = QLabel("")
        self.l_pose.setWordWrap(True)
        hp.addWidget(self.l_pose, 1)
        b = QPushButton(_("Reprendre"))
        b.setToolTip(_("La partie en jaune si elle existe, sinon la ligne rouge : là où l'animation sera posée"))
        b.clicked.connect(self.prendre_position)
        hp.addWidget(b)
        fc.addRow(_("Posée à"), hp)
        self.style_st = QComboBox()
        for k, lib in M.STYLES_ST.items():
            self.style_st.addItem(lib, k)
        self.majuscules = QCheckBox(_("En majuscules"))
        self.b_mots = QPushButton(_("Prendre les mots dits"))
        self.b_mots.setToolTip(_("Les mots transcrits du montage, de la partie en jaune (ou de la ligne rouge jusqu'à la prochaine "
                                 "pause) ; PhilCut transcrit d'abord ce qui ne l'est pas encore (sur ce poste, gratuit)"))
        self.b_mots.clicked.connect(self.prendre_mots)
        self.l_mots = QLabel("")
        self.l_mots.setWordWrap(True)
        fc.addRow(_("Style"), self.style_st)
        hm2 = QHBoxLayout()
        hm2.addWidget(self.majuscules)
        hm2.addWidget(self.b_mots)
        self.w_mots = QWidget()
        self.w_mots.setLayout(hm2)
        hm2.setContentsMargins(0, 0, 0, 0)
        fc.addRow("", self.w_mots)
        fc.addRow("", self.l_mots)
        self.b_capture = QPushButton(_("Choisir la capture…"))
        self.b_capture.clicked.connect(self.choisir_capture)
        fc.addRow(_("Capture"), self.b_capture)
        self.b_toute = QPushButton(_("Toute la vidéo, avec les repères comme chapitres"))
        self.b_toute.clicked.connect(self.toute_la_video)
        fc.addRow(_("Durée"), self.b_toute)
        hcal = QHBoxLayout()
        self.calage = QComboBox()
        for k, lib in M.CALAGES.items():
            self.calage.addItem(lib, k)
        hcal.addWidget(self.calage, 1)
        self.b_caler = QPushButton(_("Caler"))
        self.b_caler.setToolTip(_("Recalcule quand chaque élément arrive : quand le chiffre, le mois ou le mot est dit, ou sur les temps "
                                  "de la musique du montage"))
        self.b_caler.clicked.connect(self.caler)
        hcal.addWidget(self.b_caler)
        self.w_calage = QWidget()
        self.w_calage.setLayout(hcal)
        hcal.setContentsMargins(0, 0, 0, 0)
        fc.addRow(_("Caler sur"), self.w_calage)
        self.form_ctx = fc
        gv.addWidget(self.g_contexte)
        for c in (self.style_st, self.calage, self.genre):                 # G7 : les longs libellés ne dictent pas la largeur
            c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(16)
        self.style_st.currentIndexChanged.connect(self._lire_et_dessiner)
        self.majuscules.toggled.connect(self._lire_et_dessiner)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([_("Libellé"), _("Valeur")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setMinimumHeight(140)
        gv.addWidget(self.table, 1)
        hd = QHBoxLayout()
        for lib, aide, fn in ((_("Coller un tableau"), _("Collez des lignes copiées d'Excel, de Sheets ou d'un texte « Janvier 3120 »"), self.coller),
                              (_("Excel ou CSV…"), _("Les deux premières colonnes du fichier"), self.fichier),
                              ("+", _("Ajouter une ligne"), lambda: self.table.insertRow(self.table.rowCount())),
                              ("−", _("Retirer la ligne choisie"), self._retirer_ligne)):
            b = QPushButton(lib)
            b.setToolTip(aide)
            b.clicked.connect(fn)
            hd.addWidget(b)
        self.w_donnees = QWidget()
        self.w_donnees.setLayout(hd)
        hd.setContentsMargins(0, 0, 0, 0)
        gv.addWidget(self.w_donnees)
        f2 = QFormLayout()
        self.source = QLineEdit()
        self.source.setPlaceholderText(_("d'où viennent les chiffres (affiché en petit)"))
        f2.addRow(_("Source"), self.source)
        hc = QHBoxLayout()
        self.charte = QComboBox()
        hc.addWidget(self.charte, 1)
        b = QPushButton(_("Ma charte…"))
        b.clicked.connect(self.ouvrir_charte)
        hc.addWidget(b)
        f2.addRow(_("Charte"), hc)
        hf = QHBoxLayout()
        self.format = QComboBox()
        for lib, t in ((_("Celui du film"), tuple(taille)), ("16:9 (1920×1080)", (1920, 1080)), ("9:16 (1080×1920)", (1080, 1920)),
                       ("1:1 (1080×1080)", (1080, 1080)), ("4:5 (1080×1350)", (1080, 1350))):
            self.format.addItem(lib, list(t))
        hf.addWidget(self.format, 1)
        self.duree = QDoubleSpinBox()
        self.duree.setRange(2.0, 60.0)
        self.duree.setDecimals(1)
        from PySide6.QtCore import QLocale
        self.duree.setLocale(QLocale(QLocale.French))
        self.duree.setSuffix(" s")
        hf.addWidget(self.duree)
        f2.addRow(_("Format, durée"), hf)
        self.transparent = QCheckBox(_("Transparent (posé sur le film)"))
        self.transparent.setToolTip(_("Sans fond : un panneau discret garde le graphique lisible sur l'image"))
        self.zones = QCheckBox(_("Zones sûres des réseaux"))
        self.zones.setToolTip(_("En vertical : rien sous les boutons et la légende de Reels, Shorts et TikTok"))
        f2.addRow("", self.transparent)
        f2.addRow("", self.zones)
        gv.addLayout(f2)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(gauche)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setMinimumWidth(min(470, gauche.sizeHint().width() + 24))      # G7 : rien de coupé à droite
        sc.setMaximumWidth(470)
        corps.addWidget(sc)
        # ---------------------------------------------- droite : voir, choisir, régler
        droite = QVBoxLayout()
        corps.addLayout(droite, 1)
        self.vue = QLabel()
        self.vue.setMinimumSize(320, 180)
        from PySide6.QtWidgets import QSizePolicy
        self.vue.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)      # l'image suit la place, jamais l'inverse
        self.vue.setAlignment(Qt.AlignCenter)
        self.vue.setStyleSheet("background:#000;border-radius:6px")
        droite.addWidget(self.vue, 1)
        hl = QHBoxLayout()
        self.b_lire = QPushButton("▶")
        self.b_lire.setFixedWidth(40)
        self.b_lire.clicked.connect(self.lire)
        hl.addWidget(self.b_lire)
        self.temps = QSlider(Qt.Horizontal)
        self.temps.setRange(0, 1000)
        self.temps.valueChanged.connect(lambda _v: self._dessiner())
        hl.addWidget(self.temps, 1)
        self.l_temps = QLabel("0,0 s")
        self.l_temps.setMinimumWidth(48)
        hl.addWidget(self.l_temps)
        droite.addLayout(hl)
        hp = QHBoxLayout()
        self.props = []
        self.g_props = QButtonGroup(self)
        for k in (0, 1, 2):
            b = QToolButton()
            b.setCheckable(True)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setText(M.VARIANTES[k])
            b.setMinimumWidth(150)
            b.clicked.connect(lambda _c=False, k=k: self.choisir_variante(k))
            self.g_props.addButton(b, k)
            self.props.append(b)
            hp.addWidget(b)
        droite.addLayout(hp)
        g = QGroupBox(_("Réglages (le même film, quel que soit le moteur)"))
        fg = QFormLayout(g)
        self.curseurs = {}
        for cle, lib, lo, hi, _d in M.REGLAGES:
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 100)
            s.valueChanged.connect(lambda _v, c=cle: self._curseur(c))
            self.curseurs[cle] = (s, lo, hi)
            fg.addRow(lib, s)
        droite.addWidget(g)
        hr = QHBoxLayout()
        self.remarque = QLineEdit()
        self.remarque.setPlaceholderText(_("Ce qui ne va pas, à cet instant (ou « à 0:03 la barre de juin est trop rouge »)"))
        hr.addWidget(self.remarque, 1)
        b = QPushButton(_("Corriger par l'IA"))
        b.clicked.connect(self.corriger_ia)
        hr.addWidget(b)
        droite.addLayout(hr)
        # ---------------------------------------------- bas : le moteur, fabriquer
        gm = QGroupBox(_("Moteur"))
        mv = QVBoxLayout(gm)
        self.g_moteurs = QButtonGroup(self)
        self.r_moteurs = {}
        hm = QHBoxLayout()
        for k, d in M.MOTEURS.items():
            r = QRadioButton(d["nom"])
            r.setToolTip(d["aide"])
            r.toggled.connect(lambda on, k=k: on and self._moteur_change(k))
            self.g_moteurs.addButton(r)
            self.r_moteurs[k] = r
            hm.addWidget(r)
        mv.addLayout(hm)
        self.l_moteur = QLabel("")
        self.l_moteur.setWordWrap(True)
        mv.addWidget(self.l_moteur)
        hx = QHBoxLayout()
        self.b_installer = QPushButton(_("Installer…"))
        self.b_installer.clicked.connect(self.installer)
        hx.addWidget(self.b_installer)
        self.licence = QCheckBox(_("J'ai droit à la licence gratuite de Remotion (particulier, 3 personnes au plus, association) ou "
                                   "j'ai une licence entreprise"))
        self.licence.setChecked(bool(self.params.get("remotion_licence")))
        self.licence.toggled.connect(self._licence)
        hx.addWidget(self.licence, 1)
        b = QPushButton(_("Lire la licence"))
        b.clicked.connect(lambda: webbrowser.open("https://www.remotion.dev/docs/license"))
        self.b_licence = b
        hx.addWidget(b)
        mv.addLayout(hx)
        from .credit_ia import LigneCredit
        self.credit = LigneCredit(self.params, None, self, compact=True)
        mv.addWidget(self.credit)
        racine.addWidget(gm)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        racine.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        racine.addWidget(self.etat)
        hb = QHBoxLayout()
        b = QPushButton(_("Projet HTML (HyperFrames, Claude Code)…"))
        b.setToolTip(_("Ecrit l'animation en projet HyperFrames autonome et ouvre son dossier : pour la retoucher à la main dans "
                       "HyperFrames Studio ou Claude Code si vous le souhaitez ; PhilCut suffit pour tout le reste"))
        b.clicked.connect(self.projet_html)
        hb.addWidget(b)
        hb.addStretch(1)
        self.b_fabriquer = QPushButton(_("Fabriquer"))
        self.b_fabriquer.setDefault(True)
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hb.addWidget(self.b_fabriquer)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        hb.addWidget(b)
        racine.addLayout(hb)
        self._minuterie = QTimer(self)
        self._minuterie.timeout.connect(self._avancer)
        self._remplir_chartes()
        self.charger(self.anim)
        for w in (self.titre, self.sous_titre, self.badge, self.prefixe, self.suffixe, self.valeur, self.source, self.bouton, self.lignes):
            w.textChanged.connect(self._lire_et_dessiner)
        self.genre.currentIndexChanged.connect(self._genre_change)
        self.charte.currentIndexChanged.connect(self._lire_et_dessiner)
        self.format.currentIndexChanged.connect(self._lire_et_dessiner)
        self.duree.valueChanged.connect(self._lire_et_dessiner)
        self.transparent.toggled.connect(self._lire_et_dessiner)
        self.zones.toggled.connect(self._lire_et_dessiner)
        self.table.itemChanged.connect(self._lire_et_dessiner)
        moteur = self.params.get("motion_moteur") or M.conseiller(self.anim, self.params)[0]
        self.r_moteurs.get(moteur, self.r_moteurs["maison"]).setChecked(True)
        self._moteur_change(self._moteur())

    # ---------------------------------------------- fiche <-> champs
    def _remplir_chartes(self):
        self.charte.blockSignals(True)
        self.charte.clear()
        for c in CH.toutes(self.params):
            self.charte.addItem(c["nom"], c["id"])
        act = (self.anim.get("charte") or {}).get("id") or self.params.get("charte_active") or "defaut"
        self.charte.setCurrentIndex(max(0, self.charte.findData(act)))
        self.charte.blockSignals(False)

    def charger(self, a):
        self._charge = True
        self.anim = copy.deepcopy(a)
        self.genre.setCurrentIndex(max(0, self.genre.findData(a.get("genre"))))
        self.titre.setText(a.get("titre") or "")
        self.sous_titre.setText(a.get("sous_titre") or "")
        self.badge.setText(a.get("badge") or "")
        self.lignes.setPlainText("\n".join(a.get("lignes") or []))
        self.bouton.setText(a.get("bouton") or "")
        self.prefixe.setText(a.get("prefixe") or "")
        self.suffixe.setText(a.get("suffixe") or "")
        self.valeur.setText(M.nombre(a["valeur"]) if a.get("valeur") is not None else "")
        self.source.setText(a.get("source") or "")
        self.duree.setValue(float(a.get("duree") or 6))
        self.transparent.setChecked(bool(a.get("transparent")))
        self.zones.setChecked(bool(a.get("zones_sures", True)))
        i = next((k for k in range(self.format.count()) if self.format.itemData(k) == list(a.get("taille") or [])), 0)
        self.format.setCurrentIndex(i)
        self.table.setRowCount(0)
        for lib, val in a.get("donnees") or []:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(lib)))
            self.table.setItem(r, 1, QTableWidgetItem(M.nombre(val)))
        for cle, (s, lo, hi) in self.curseurs.items():
            s.setValue(int(round((M.reglage(a, cle) - lo) / (hi - lo) * 100)))
        self.props[int(a.get("variante") or 0)].setChecked(True)
        self.style_st.setCurrentIndex(max(0, self.style_st.findData(a.get("style_st") or "surligne")))
        self.majuscules.setChecked(bool(a.get("majuscules", True)))
        self.calage.setCurrentIndex(max(0, self.calage.findData(a.get("cale") or "")))
        self._charge = False
        self._contexte()
        self._lire_et_dessiner()
        self._vignettes()

    def lire_fiche(self):
        a = self.anim
        a["genre"] = self.genre.currentData()
        a["titre"], a["sous_titre"], a["badge"] = self.titre.text(), self.sous_titre.text(), self.badge.text()
        a["prefixe"], a["suffixe"], a["source"] = self.prefixe.text(), self.suffixe.text(), self.source.text()
        a["lignes"] = [l.strip() for l in self.lignes.toPlainText().splitlines() if l.strip()]
        a["bouton"] = self.bouton.text()
        d = []
        for r in range(self.table.rowCount()):
            lib = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            try:
                val = M._valeur(self.table.item(r, 1).text() if self.table.item(r, 1) else "")
            except ValueError:
                continue
            d.append([lib, val])
        a["donnees"] = d or [list(x) for x in M.EXEMPLE]
        try:
            a["valeur"] = M._valeur(self.valeur.text()) if self.valeur.text().strip() else sum(v for _l, v in a["donnees"])
        except ValueError:
            a["valeur"] = sum(v for _l, v in a["donnees"])
        ch = next((c for c in CH.toutes(self.params) if c["id"] == self.charte.currentData()), CH.DEFAUT)
        a["charte"] = copy.deepcopy(ch)
        a["taille"] = list(self.format.currentData() or [1920, 1080])
        a["duree"] = float(self.duree.value())
        a["transparent"] = self.transparent.isChecked()
        a["zones_sures"] = self.zones.isChecked()
        a["style_st"] = self.style_st.currentData()
        a["majuscules"] = self.majuscules.isChecked()
        h = a.get("horaire")
        if isinstance(h, dict) and abs(float(h.get("duree", 0)) - a["duree"]) > 0.05:
            a["horaire"], a["cale"] = None, ""          # la durée a changé : le calage est à refaire
        return a

    def _lire_et_dessiner(self, *_a):
        if getattr(self, "_charge", False):
            return
        self.lire_fiche()
        self._dessiner()
        self._maj_prix()
        if not self._minuterie.isActive():
            QTimer.singleShot(0, self._vignettes_plus_tard)

    def _vignettes_plus_tard(self):
        if not hasattr(self, "_vig_timer"):
            self._vig_timer = QTimer(self)
            self._vig_timer.setSingleShot(True)
            self._vig_timer.timeout.connect(self._vignettes)
        self._vig_timer.start(500)

    def _genre_change(self):
        if getattr(self, "_charge", False):
            return
        a = M.preparer_genre(self.lire_fiche(), self.genre.currentData())
        if a["genre"] == "progression" and self.ed.projet.duree() > 1:
            a.update(pose=0.0, duree=round(self.ed.projet.duree(), 2), chapitres=M.chapitres(self.ed.projet, 0.0))
        self.charger(a)
        if a["genre"] == "sous_titres" and not a.get("mots"):
            self.etat.setText(_("Sous-titres : mettez la partie en jaune sur ce qui est dit (ou la ligne rouge au début), puis "
                                "« Prendre les mots dits »."))

    # ---------------------------------------------- 1.0.0 : dans le film
    def _contexte(self):
        g = self.anim.get("genre")
        chiffres = g in M.A_DONNEES
        for w in (self.table, self.w_donnees):
            w.setVisible(chiffres)
        for w, vu in ((self.w_chiffre, g in ("compteur", "chiffres", "jauge")), (self.badge, g in ("compteur", "chiffres")),
                      (self.lignes, g in M.A_LIGNES), (self.bouton, g == "appel")):
            w.setVisible(vu)
            self.form1.labelForField(w).setVisible(vu)
        self.valeur.setPlaceholderText(_("de 0 à 100") if g == "jauge" else _("le total des données"))
        st = g == "sous_titres"
        for w in (self.style_st, self.w_mots, self.l_mots):
            w.setVisible(st)
            lab = self.form_ctx.labelForField(w)
            if lab:
                lab.setVisible(st)
        self.b_capture.setVisible(g == "defilement")
        self.form_ctx.labelForField(self.b_capture).setVisible(g == "defilement")
        self.b_toute.setVisible(g == "progression")
        self.form_ctx.labelForField(self.b_toute).setVisible(g == "progression")
        cal = g in ("compteur", "barres", "courbe", "chiffres", "titre", "bandeau", "camembert", "jauge", "comparaison", "classement",
                    "chiffres_cles", "chronologie", "liste", "citation", "appel")
        self.w_calage.setVisible(cal)
        self.form_ctx.labelForField(self.w_calage).setVisible(cal)
        for w in (self.titre, self.sous_titre):
            vu = g not in ("sous_titres", "progression", "defilement")
            w.setVisible(vu)
            self.form1.labelForField(w).setVisible(vu)
        self.titre.setPlaceholderText({"bandeau": _("le nom"), "citation": _("la citation")}.get(g, ""))
        self.sous_titre.setPlaceholderText({"bandeau": _("la fonction"), "citation": _("l'auteur")}.get(g, ""))
        p = float(self.anim.get("pose") if self.anim.get("pose") is not None else self.ed.timeline.position)
        m, sec = divmod(p, 60)
        cal_txt = {"voix": _(" ; calée sur la voix"), "musique": _(" ; calée sur la musique")}.get(self.anim.get("cale") or "", "")
        self.l_pose.setText(f"{int(m)}:{sec:04.1f}".replace(".", ",") + cal_txt)
        n = len(self.anim.get("mots") or [])
        self.l_mots.setText(_("{n} mot(s) pris.", n=n) if n else _("Aucun mot pour l'instant."))
        if hasattr(self, "r_moteurs"):
            self._moteur_change(self._moteur())

    def _position(self):
        tl = self.ed.timeline
        z = getattr(tl, "zone", [None, None])
        if z and z[0] is not None and z[1] is not None and z[1] - z[0] > 0.2:
            return float(z[0]), float(z[1])
        return float(tl.position), None

    def prendre_position(self):
        a = self.lire_fiche()
        a["pose"], fin = self._position()
        if fin is not None and a.get("genre") in M.HABILLAGE + ("titre",):
            a["duree"] = round(fin - a["pose"], 2)
        a["horaire"], a["cale"] = None, ""
        self.charger(a)

    def prendre_mots(self):
        projet = self.ed.projet
        debut, fin = self._position()

        def poser(r=None, e=None):
            if e:
                self.etat.setText("✕ " + texte_erreur(e))
                return
            mots, duree = M.mots_pour_sous_titres(projet, debut, fin)
            if not mots:
                self.etat.setText(_("Aucun mot dit à cet endroit (ou la transcription n'a rien trouvé)."))
                return
            a = self.lire_fiche()
            a.update(mots=mots, duree=duree, pose=debut, horaire=None)
            self.charger(a)
            self.etat.setText(_("{n} mot(s) sur {d} s : regardez (▶).", n=len(mots), d=f"{duree:.1f}".replace(".", ",")))
        if M.a_transcrire(projet):
            from . import sous_titres as ST
            if not ST.disponible():
                self.etat.setText(_("La transcription demande le modèle de voix (Préférences › IA locale)."))
                return
            self._lancer(lambda t: M.transcrire(projet, self.params, t.avancer, t.arret_demande), _("Transcription des paroles"), poser)
        else:
            poser()

    def choisir_capture(self):
        from .widgets import ouvrir_fichier
        f = ouvrir_fichier(self, _("Capture à faire défiler"), _("Images (*.png *.jpg *.jpeg *.webp)"), "images", self.params)
        if f:
            a = self.lire_fiche()
            a["image"] = f
            self.charger(a)

    def toute_la_video(self):
        a = self.lire_fiche()
        a.update(pose=0.0, duree=round(max(2.0, self.ed.projet.duree()), 2), chapitres=M.chapitres(self.ed.projet, 0.0), horaire=None)
        self.charger(a)
        self.etat.setText(_("{n} chapitre(s) tirés de vos repères (touche M sur la timeline).", n=len(a["chapitres"])))

    def caler(self):
        quoi = self.calage.currentData()
        a = self.lire_fiche()
        if a.get("pose") is None:
            a["pose"] = self._position()[0]
        if not quoi:
            a["horaire"], a["cale"] = None, ""
            self.charger(a)
            self.etat.setText(_("Horaire par défaut."))
            return
        projet, debut = self.ed.projet, float(a["pose"])

        def appliquer(r, e):
            if e:
                self.etat.setText("✕ " + texte_erreur(e))
                return
            h, n = r
            if not n:
                self.etat.setText(_("Rien à caler : aucun mot reconnu ici.") if quoi == "voix" else _("Pas de musique rythmée sous l'animation."))
                return
            b = self.lire_fiche()
            b.update(horaire=h, cale=quoi, pose=debut)
            self.charger(b)
            self.etat.setText(_("✓ Calée : {n} élément(s) suivent la {q}. Regardez (▶).", n=n, q=_("voix") if quoi == "voix" else _("musique")))

        def travail(t):
            if quoi == "voix":
                if M.a_transcrire(projet):
                    M.transcrire(projet, self.params, t.avancer, t.arret_demande)
                return M.caler_voix(a, M.mots_dans(M.mots_montage(projet), debut, float(a["duree"])))
            temps, forts = M.temps_musique(projet)
            rel = lambda l: [x - debut for x in l if debut <= x <= debut + float(a["duree"])]
            return M.caler_musique(a, rel(temps), rel(forts))
        self._lancer(travail, _("Calage de l'animation"), appliquer)

    def _curseur(self, cle):
        if getattr(self, "_charge", False):
            return
        s, lo, hi = self.curseurs[cle]
        self.anim.setdefault("reglages", {})[cle] = round(lo + (hi - lo) * s.value() / 100, 3)
        self._dessiner()
        self._vignettes_plus_tard()

    # ---------------------------------------------- aperçu
    def instant(self):
        return self.temps.value() / 1000 * float(self.anim.get("duree") or 6)

    def _dessiner(self):
        from . import motion_maison as MM
        t = self.instant()
        self.l_temps.setText(f"{t:.1f} s".replace(".", ","))
        w, h = max(160, self.vue.width() - 4), max(90, self.vue.height() - 4)
        img = MM.apercu_image(self.anim, t, (w, h))
        self.vue.setPixmap(QPixmap.fromImage(img))

    def _vignettes(self):
        from . import motion_maison as MM
        t = M.instant_vignette(self.anim)
        for k, b in enumerate(self.props):
            a = M.avec_variante(dict(self.anim, reglages=dict(self.anim.get("reglages") or {})), k)
            # dessinée trois fois plus grande puis réduite : les petits textes gardent leurs proportions (pas de taille plancher)
            b.setIcon(QPixmap.fromImage(MM.apercu_image(a, t, (432, 243)).scaled(144, 81, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            from PySide6.QtCore import QSize
            b.setIconSize(QSize(144, 81))

    def choisir_variante(self, k):
        a = M.avec_variante(self.lire_fiche(), k)
        self.charger(a)
        self.etat.setText(_("Proposition « {p} » : les curseurs ont suivi ; réglez-les si besoin.", p=M.VARIANTES[k]))

    def lire(self):
        if self._minuterie.isActive():
            self._minuterie.stop()
            self.b_lire.setText("▶")
            return
        if self.temps.value() >= 999:
            self.temps.setValue(0)
        self.b_lire.setText("■")
        self._minuterie.start(66)

    def _avancer(self):
        d = float(self.anim.get("duree") or 6)
        v = self.temps.value() + int(1000 * 0.066 / d)
        if v >= 1000:
            self.temps.setValue(1000)
            self._minuterie.stop()
            self.b_lire.setText("▶")
            return
        self.temps.setValue(v)

    # ---------------------------------------------- données
    def coller(self):
        d = M.lire_donnees(QApplication.clipboard().text())
        if not d:
            self.etat.setText(_("Rien de lisible dans le presse-papiers : copiez deux colonnes (libellé, valeur)."))
            return
        self._poser_donnees(d)

    def fichier(self):
        from .widgets import ouvrir_fichier
        f = ouvrir_fichier(self, _("Vos données"), _("Tableaux (*.xlsx *.xlsm *.csv *.txt)"), "documents", self.params)
        if not f:
            return
        try:
            d = M.lire_fichier(f)
        except Exception as e:      # noqa: BLE001
            self.etat.setText("✕ " + texte_erreur(e))
            return
        if not d:
            self.etat.setText(_("Aucune ligne « libellé, valeur » trouvée dans ce fichier."))
            return
        self._poser_donnees(d)

    def _poser_donnees(self, d):
        a = self.lire_fiche()
        a["donnees"] = d
        a["valeur"] = sum(v for _l, v in d)
        self.charger(a)
        self.etat.setText(_("{n} ligne(s) prises ; le chiffre total est leur somme (modifiable).", n=len(d)))

    def _retirer_ligne(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)
            self._lire_et_dessiner()

    # ---------------------------------------------- charte
    def ouvrir_charte(self):
        d = DialogueCharte(self, self.params, self.charte.currentData())
        if d.exec() == QDialog.Accepted:
            self._remplir_chartes()
            self.charte.setCurrentIndex(max(0, self.charte.findData(getattr(d, "resultat", {}).get("id"))))
            self._lire_et_dessiner()
            self._vignettes()

    # ---------------------------------------------- IA
    def _niveau(self):
        from . import assistant_creation as A
        n = A.niveaux(self.params)
        voulu = self.params.get("musique_ia_ecrire") or (n[0][0] if n else "locale")
        return voulu if any(k == voulu for k, _l in n) else (n[0][0] if n else "locale")

    def _lancer(self, travail, titre, fin):
        self.tache = Tache(travail, titre)
        self.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, titre)
        self.barre.setValue(0)
        self.barre.show()
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)

        def fini(r, e):
            try:
                self.barre.hide()
                self.tache = None
                fin(r, e)
            except RuntimeError:
                pass
        self.tache.fini.connect(fini, Qt.QueuedConnection)
        self.tache.start()

    def preparer_ia(self):
        texte = self.demande.toPlainText().strip()
        if not texte:
            self.etat.setText(_("Ecrivez d'abord ce que vous voulez, en une ou deux phrases."))
            return
        a, niveau = copy.deepcopy(self.lire_fiche()), self._niveau()

        def fin(r, e):
            if e or not r:
                self.etat.setText("✕ " + (texte_erreur(e) if e else _("pas de réponse")))
                return
            self.charger(r[0])
            self.etat.setText("✓ " + (r[1] or _("Fiche remplie : vérifiez les chiffres, puis regardez.")))
        self._lancer(lambda t: M.preparer_ia(self.params, texte, a, niveau), _("L'IA prépare l'animation"), fin)

    def corriger_ia(self):
        texte = self.remarque.text().strip()
        if not texte:
            return
        a, niveau, t0 = copy.deepcopy(self.lire_fiche()), self._niveau(), self.instant()

        def fin(r, e):
            if e or not r:
                self.etat.setText("✕ " + (texte_erreur(e) if e else _("pas de réponse")))
                return
            self.remarque.clear()
            self.charger(r[0])
            self.etat.setText("✓ " + (r[1] or _("Corrigé : regardez.")))
        self._lancer(lambda t: M.corriger_ia(self.params, a, texte, t0, niveau), _("L'IA corrige l'animation"), fin)

    # ---------------------------------------------- moteur
    def _moteur(self):
        return next((k for k, r in self.r_moteurs.items() if r.isChecked()), "maison")

    def _moteur_change(self, k):
        self.params["motion_moteur"] = k
        ok, quoi = M.etat(k, self.params)
        conseil, raison = M.conseiller(self.lire_fiche(), self.params)
        txt = M.MOTEURS[k]["aide"] + "  " + (_("Etat : {e}.", e=quoi))
        txt += "\n" + ("★ " + _("Conseillé ici : {r}.", r=raison) if conseil == k else
                       _("Conseillé ici : {m} ({r}).", m=M.MOTEURS[conseil]["nom"], r=raison))
        self.l_moteur.setText(txt)
        for kk, r in self.r_moteurs.items():
            r.setText(M.MOTEURS[kk]["nom"] + ("  ★" if kk == conseil else ""))
        a_installer = bool(k in ("hyperframes_local", "remotion") and not ok and (k != "remotion" or self.params.get("remotion_licence")))
        self.b_installer.setVisible(a_installer)
        self.licence.setVisible(k == "remotion")
        self.b_licence.setVisible(k == "remotion")
        self.credit.montrer("heygen" if k == "hyperframes_cloud" else None)
        self._maj_prix()

    def _licence(self, on):
        self.params["remotion_licence"] = bool(on)
        self._moteur_change(self._moteur())

    def _maj_prix(self):
        if not hasattr(self, "r_moteurs"):
            return
        k = self._moteur()
        p = M.prix(self.anim, k)
        self.b_fabriquer.setText(_("Fabriquer (environ {p} $)", p=f"{p:.2f}".replace(".", ",")) if p else _("Fabriquer (gratuit)"))

    def installer(self):
        k = self._moteur()
        from . import packs_ia

        def travail(t):
            if not packs_ia.moteur_installe("motion"):
                packs_ia.installer("motion_html", t.avancer, t.arret_demande)
            if k == "remotion":
                from . import motion_remotion as MR
                MR.installer(self.params, t.avancer, t.arret_demande)
            return True

        def fin(r, e):
            self.etat.setText("✕ " + texte_erreur(e) if e else _("✓ Installé : vous pouvez fabriquer."))
            self._moteur_change(self._moteur())
        self._lancer(travail, _("Installation du moteur d'animation"), fin)

    # ---------------------------------------------- fabriquer, poser
    def fabriquer(self):
        if self.tache is not None:
            return
        a = copy.deepcopy(self.lire_fiche())
        k = self._moteur()
        ok, quoi = M.etat(k, self.params)
        if not ok:
            self.etat.setText(_("Moteur « {m} » : {e}. Choisissez-en un autre, ou installez-le.", m=M.MOTEURS[k]["nom"], e=quoi))
            return
        p = M.prix(a, k)
        if p and getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Rendu payant"), _("HeyGen va rendre l'animation : environ {p} $ sur votre crédit HeyGen. Continuer ?",
                                           p=f"{p:.2f}".replace(".", ","))) != QMessageBox.Yes:
            return
        sortie = M.sortie_pour(a)
        self.b_fabriquer.setEnabled(False)

        def fin(r, e):
            self.b_fabriquer.setEnabled(True)
            if e or not r:
                self.etat.setText("✕ " + (texte_erreur(e) if e else _("rien n'a été fabriqué")))
                return
            self.resultat = r
            self.etat.setText(_("✓ Animation prête : regardez-la, puis posez-la."))
            if getattr(self, "_test_oui", None) is None:
                ResultatAnimation(self.ed, r, a).exec()
        self._lancer(lambda t: M.fabriquer(self.params, a, sortie, k, t.avancer, t.arret_demande),
                     _("Animation : {m}", m=M.MOTEURS[k]["nom"]), fin)

    def projet_html(self):
        from . import motion_html as MH
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        import time as _t
        a = self.lire_fiche()
        d = os.path.join(M.dossier(), "projets", _t.strftime("%Y%m%d_%H%M%S") + "_html")
        MH.preparer_projet(a, d, gsap_en_ligne=not MH.gsap_local())
        self.etat.setText(_("Projet HyperFrames écrit dans {d} (index.html). Pour le retoucher : HyperFrames Studio, ou Claude Code "
                            "dans ce dossier ; « Fabriquer » ici suffit pour tout le reste.", d=d))
        if getattr(self, "_test_oui", None) is None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        return d

    def closeEvent(self, e):
        self._minuterie.stop()
        super().closeEvent(e)

    def done(self, r):
        from .widgets import calcul_en_cours, garder_calcul
        if garder_calcul(self, calcul_en_cours(self)):
            return
        self._minuterie.stop()
        super().done(r)


class ResultatAnimation(QDialog):
    """L'animation fabriquée : on la regarde avant de la poser (au-dessus du film, ou insérée à la ligne rouge)."""

    def __init__(self, ed, chemin, anim):
        super().__init__(ed)
        from .dialogues_creatif import ApercuCreation
        self.ed, self.chemin, self.anim = ed, chemin, anim
        self.setWindowTitle(_("Animation fabriquée"))
        v = QVBoxLayout(self)
        self.apercu = ApercuCreation(self)
        self.apercu.charger(chemin, video=True)
        v.addWidget(self.apercu)
        h = QHBoxLayout()
        b1 = QPushButton(_("Poser au-dessus du film (ligne rouge)"))
        b1.setToolTip(_("Sur une piste vidéo libre, sans couper ni décaler le film (idéal en transparent)"))
        b1.clicked.connect(self.dessus)
        b2 = QPushButton(_("Insérer à la ligne rouge"))
        b2.setToolTip(_("Le film est décalé d'autant (Ctrl+Z revient)"))
        b2.clicked.connect(self.inserer)
        b3 = QPushButton(_("Garder dans les médias"))
        b3.clicked.connect(self.garder)
        for b in (b1, b2, b3):
            h.addWidget(b)
        h.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.reject)
        h.addWidget(b)
        v.addLayout(h)
        self.resize(760, 440)

    def dessus(self):
        self.apercu.arreter()
        pose = self.anim.get("pose")
        self.ed.poser_au_dessus(self.chemin, float(pose) if pose is not None else self.ed.timeline.position,
                                M.GENRES.get(self.anim.get("genre"), {}).get("nom", ""),
                                float(self.anim.get("duree") or 0) or None)
        self.accept()

    def inserer(self):
        from . import prolonger
        self.apercu.arreter()
        p = self.ed.projet
        p.marquer()
        prolonger.inserer(p, self.chemin, self.ed.timeline.position, "video", M.GENRES.get(self.anim.get("genre"), {}).get("nom", ""))
        self.ed.biblio.remplir(p)
        self.ed.rafraichir()
        self.ed.encart.message(_("Animation insérée ; la suite est décalée (Ctrl+Z pour revenir)."), 6000)
        self.accept()

    def garder(self):
        from . import moteur
        p = self.ed.projet
        m = p.ajouter_media(self.chemin, moteur.sonder(self.chemin))
        m["nom"] = M.GENRES.get(self.anim.get("genre"), {}).get("nom", "") or os.path.basename(self.chemin)
        self.ed.biblio.remplir(p)
        self.accept()
