"""Fenêtre « Personnage animé (pantin) » (1.3.0).

A gauche, l'aperçu : exactement la vidéo finale, image par image (gratuit, sur ce poste), avec lecture, curseur de temps et,
en mode « Squelette », les articulations et le visage à déplacer à la souris. A droite, quatre onglets : Personnages,
Mouvements, Visage et voix, Scène. En bas : la ligne d'état, la barre de progression, « Fabriquer et poser… », « Réduire »,
« Fermer » (fermer range la fenêtre : rien n'est perdu ; la scène est aussi gardée à chaque changement).
"""
import copy
import os
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSlider, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from . import pantin as P, pantin_ia as PI
from .langue import _
from .taches import Tache, texte_erreur

FORMATS = (("16:9", (1920, 1080)), ("9:16", (1080, 1920)), ("1:1", (1080, 1080)))


def _prix(p):
    return f"{p:.2f}".replace(".", ",")


# ------------------------------------------------------------------ aperçu
class Apercu(QWidget):
    """La scène à l'instant t ; en mode squelette, le dessin d'origine du personnage choisi et ses points à déplacer."""

    def __init__(self, dlg):
        super().__init__(dlg)
        self.dlg = dlg
        self.t = 0.0
        self.rendu = None
        self.squelette = None          # (pantin) en mode squelette
        self.image_source = None
        self.prise = None
        self.setMinimumSize(380, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def recharger(self):
        self.rendu = P.RenduScene(self.dlg.scene)
        self.update()

    def _cadre(self, L, H):
        k = min(self.width() / L, self.height() / H)
        w, h = L * k, H * k
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h), k

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor("#1e2228"))
        if self.squelette is not None:
            self._peindre_squelette(p)
        elif self.rendu is not None:
            cadre, _k = self._cadre(self.rendu.L, self.rendu.H)
            if (self.dlg.scene.get("fond") or {}).get("type") == "transparent":
                taille = 16
                for i in range(int(cadre.width() // taille) + 1):
                    for j in range(int(cadre.height() // taille) + 1):
                        if (i + j) % 2:
                            p.fillRect(QRectF(cadre.left() + i * taille, cadre.top() + j * taille, taille, taille).intersected(cadre),
                                       QColor("#3a3f47"))
            p.save()
            p.translate(cadre.topLeft())
            p.setClipRect(QRectF(0, 0, cadre.width(), cadre.height()))
            self.rendu.dessiner(p, self.t, cadre.width(), cadre.height())
            p.restore()
        p.end()

    # ---------------------------------------------- squelette
    def montrer_squelette(self, pantin):
        from PySide6.QtGui import QImage
        self.squelette = pantin
        self.image_source = QImage(os.path.join(pantin["dossier"], pantin["image"])) if pantin else None
        self.update()

    def _repere(self):
        im = self.image_source
        cadre, k = self._cadre(im.width(), im.height())
        return cadre, k

    def _points_visage(self):
        v = self.squelette.get("visage") or {}
        return {"yeux": v.get("yeux"), "bouche": v.get("bouche")}

    def _peindre_squelette(self, p):
        im = self.image_source
        if im is None or im.isNull():
            return
        cadre, k = self._repere()
        p.drawImage(cadre, im)
        pts = self.squelette["points"]

        def ec(pt):
            return QPointF(cadre.left() + pt[0] * k, cadre.top() + pt[1] * k)
        p.setPen(QPen(QColor("#ffcc00"), 3))
        for n, (parent, pivot, segs, _z) in P.PIECES.items():
            for seg in segs:
                p.drawLine(ec(pts[seg[0]]), ec(pts[seg[1]]))
        for n in P.POINTS:
            p.setBrush(QColor("#ff5722" if self.prise == n else "#ffcc00"))
            p.setPen(QPen(QColor("#202020"), 1))
            p.drawEllipse(ec(pts[n]), 7, 7)
        for n, pt in self._points_visage().items():
            if pt:
                p.setBrush(QColor("#29b6f6"))
                p.drawRect(QRectF(ec(pt).x() - 7, ec(pt).y() - 7, 14, 14))
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(8, 6, self.width() - 16, 40), Qt.TextWordWrap,
                   _("Glissez les points jaunes sur les articulations, les carrés bleus sur les yeux et la bouche ; "
                     "puis « Appliquer le squelette »."))

    def _plus_proche(self, pos):
        cadre, k = self._repere()
        best, dmin = None, 14.0
        cand = list(self.squelette["points"].items()) + [(n, pt) for n, pt in self._points_visage().items() if pt]
        for n, pt in cand:
            x, y = cadre.left() + pt[0] * k, cadre.top() + pt[1] * k
            d = ((x - pos.x()) ** 2 + (y - pos.y()) ** 2) ** 0.5
            if d < dmin:
                best, dmin = n, d
        return best

    def mousePressEvent(self, e):
        if self.squelette is not None:
            self.prise = self._plus_proche(e.position())
            self.update()

    def mouseMoveEvent(self, e):
        if self.squelette is not None and self.prise and e.buttons() & Qt.LeftButton:
            cadre, k = self._repere()
            x = (e.position().x() - cadre.left()) / k
            y = (e.position().y() - cadre.top()) / k
            if self.prise in ("yeux", "bouche"):
                self.squelette.setdefault("visage", P.visage_par_defaut(self.squelette))[self.prise] = [x, y]
            else:
                self.squelette["points"][self.prise] = [x, y]
            self.update()

    def mouseReleaseEvent(self, _e):
        self.prise = None
        self.update()


# ------------------------------------------------------------------ créer un personnage
class DialogueCreer(QDialog):
    """Créer un personnage par l'IA, ou depuis une photo (personne d'accord) : style, description, prix, consigne envoyée."""

    def __init__(self, parent, params, photo=False):
        super().__init__(parent)
        from .credit_ia import LigneCredit
        self.params, self.photo = params, photo
        self.setWindowTitle(_("Nouveau personnage : depuis une photo") if photo else _("Nouveau personnage : créé par l'IA"))
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.nom = QLineEdit()
        self.nom.setPlaceholderText(_("ex. : Léa la boulangère"))
        f.addRow(_("Nom"), self.nom)
        self.style = QComboBox()
        for k, n in PI.liste_styles():
            self.style.addItem(n, k)
        i = self.style.findData(params.get("pantin_style") or "plat")
        self.style.setCurrentIndex(max(0, i))
        f.addRow(_("Style"), self.style)
        if photo:
            hp = QHBoxLayout()
            self.chemin_photo = QLineEdit()
            self.chemin_photo.setReadOnly(True)
            hp.addWidget(self.chemin_photo, 1)
            b = QPushButton(_("Choisir…"))
            b.clicked.connect(self.choisir_photo)
            hp.addWidget(b)
            f.addRow(_("Photo"), hp)
            self.accord = QCheckBox(_("Cette personne est d'accord pour être mise en personnage animé (ou c'est moi)"))
            self.accord.setToolTip(_("Votre déclaration fait foi. Jamais une célébrité ni une personne qui n'a pas donné son accord."))
            self.accord.toggled.connect(self._maj)
            f.addRow("", self.accord)
            self.description = QLineEdit()
            self.description.setPlaceholderText(_("facultatif : tenue, accessoire…"))
            f.addRow(_("Précisions"), self.description)
        else:
            self.description = QPlainTextEdit()
            self.description.setPlaceholderText(_("ex. : une boulangère souriante, tablier rouge, cheveux bruns en chignon"))
            self.description.setFixedHeight(70)
            f.addRow(_("Description"), self.description)
        v.addLayout(f)
        self.consigne = QLabel("")
        self.consigne.setWordWrap(True)
        self.consigne.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.consigne.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.consigne)
        self.prix = QLabel(_("Coût : environ {p} $ (deux dessins Gemini : le corps, puis les yeux et les bouches ; et la lecture "
                             "des articulations). La découpe, les mouvements et le rendu sont gratuits, sur ce poste.",
                             p=_prix(PI.prix())))
        self.prix.setWordWrap(True)
        v.addWidget(self.prix)
        v.addWidget(LigneCredit(params, "google", self, compact=True))
        h = QHBoxLayout()
        h.addStretch(1)
        self.ok = QPushButton(_("Créer (environ {p} $)", p=_prix(PI.prix())))
        self.ok.clicked.connect(self.accept)
        h.addWidget(self.ok)
        b = QPushButton(_("Annuler"))
        b.clicked.connect(self.reject)
        h.addWidget(b)
        v.addLayout(h)
        self.style.currentIndexChanged.connect(self._maj)
        self.resize(620, 420)
        self._maj()

    def choisir_photo(self):
        from .widgets import ouvrir_fichier
        f = ouvrir_fichier(self, _("Photo de la personne"), _("Images (*.png *.jpg *.jpeg *.webp)"), "images", self.params)
        if f:
            self.chemin_photo.setText(f)
            if not self.nom.text().strip():
                self.nom.setText(os.path.splitext(os.path.basename(f))[0][:30])
            self._maj()

    def texte(self):
        d = self.description
        return (d.toPlainText() if isinstance(d, QPlainTextEdit) else d.text()).strip()

    def valeurs(self):
        return {"nom": self.nom.text().strip() or _("Personnage"), "style": self.style.currentData(), "description": self.texte(),
                "photo": self.chemin_photo.text() if self.photo else None}

    def _maj(self):
        v = self.valeurs()
        en = PI.consigne_corps(v["description"], v["style"], depuis_photo=self.photo)
        self.consigne.setText(_("Consigne envoyée (en anglais) : {c}", c=en) + "\n" +
                              _("Traduction : un personnage en pose en T, de face, bras tendus à l'horizontale, jambes un peu "
                                "écartées, visage sans yeux ni bouche (ajoutés à part), dans le style choisi, sur un fond vert uni."))
        ok = True
        if self.photo:
            ok = bool(self.chemin_photo.text()) and self.accord.isChecked()
        self.ok.setEnabled(ok)


# ------------------------------------------------------------------ la fenêtre
class DialoguePantin(QDialog):
    def __init__(self, ed, scene=None, chemin_scene=None, clip_id=None):
        super().__init__(ed)
        from .credit_ia import LigneCredit
        self.ed, self.params = ed, ed.params
        self.tache, self.taches, self.clip_id = None, [], clip_id
        self.chemin_scene = chemin_scene or os.path.join(P.dossier_scenes(), time.strftime("%Y%m%d_%H%M%S") + ".json")
        if scene is None:
            L, H = getattr(getattr(ed, "projet", None), "taille", (1920, 1080))
            scene = P.scene_vide(int(L), int(H))
        self.scene = scene
        self.setWindowTitle(_("Personnage animé (pantin)"))
        h = QHBoxLayout(self)
        # ---- gauche : aperçu et lecture
        g = QVBoxLayout()
        self.apercu = Apercu(self)
        g.addWidget(self.apercu, 1)
        hl = QHBoxLayout()
        self.b_lire = QPushButton(_("▶ Lire"))
        self.b_lire.clicked.connect(self.lire)
        hl.addWidget(self.b_lire)
        self.temps = QSlider(Qt.Horizontal)
        self.temps.setRange(0, 1000)
        self.temps.valueChanged.connect(self._temps_change)
        hl.addWidget(self.temps, 1)
        self.l_temps = QLabel("0,0 s")
        self.l_temps.setMinimumWidth(self.l_temps.fontMetrics().horizontalAdvance("000,0 / 000,0 s") + 8)
        hl.addWidget(self.l_temps)
        g.addLayout(hl)
        h.addLayout(g, 3)
        # ---- droite : onglets
        d = QVBoxLayout()
        self.onglets = QTabWidget()
        self.onglets.addTab(self._onglet_personnages(), _("Personnages"))
        self.onglets.addTab(self._onglet_mouvements(), _("Mouvements"))
        self.onglets.addTab(self._onglet_visage(), _("Visage"))
        self.onglets.addTab(self._onglet_scene(), _("Scène"))
        self.onglets.tabBar().setUsesScrollButtons(False)     # les quatre onglets toujours entiers (G7)
        self.onglets.tabBar().setElideMode(Qt.ElideNone)
        d.addWidget(self.onglets, 1)
        self.credit = LigneCredit(self.params, "google", self, compact=True)
        d.addWidget(self.credit)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        d.addWidget(self.etat)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        d.addWidget(self.barre)
        hb = QHBoxLayout()
        self.b_fabriquer = QPushButton(_("Fabriquer et poser…"))
        self.b_fabriquer.setToolTip(_("La vidéo, image par image, sur ce poste (gratuit) ; vous la regardez, puis vous la posez"))
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hb.addWidget(self.b_fabriquer)
        hb.addStretch(1)
        self.b_reduire = QPushButton(_("Réduire"))
        self.b_reduire.clicked.connect(self.reduire)
        hb.addWidget(self.b_reduire)
        b = QPushButton(_("Fermer"))
        b.setToolTip(_("La scène reste gardée : Fabrique IA › Reprendre une création en cours la rouvre"))
        b.clicked.connect(self.close)
        hb.addWidget(b)
        d.addLayout(hb)
        droite = QWidget()
        droite.setLayout(d)
        droite.setMinimumWidth(430)
        droite.setMaximumWidth(520)
        h.addWidget(droite, 2)
        self._lecture = QTimer(self)
        self._lecture.setInterval(33)
        self._lecture.timeout.connect(self._avancer)
        self._debut_lecture = None
        self._lecteur = None
        self.resize(1000, 700)
        self._remplir()
        from . import en_cours as EC
        EC.suivre(self, "pantin", self._etat_en_cours,
                  lambda: ", ".join(self._nom(c) for c in self.scene.get("personnages", [])) or _("Scène sans personnage"))

    # ---------------------------------------------- onglets
    def _onglet_personnages(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.liste = QListWidget()
        self.liste.currentRowChanged.connect(self._choisi)
        v.addWidget(self.liste, 1)
        h = QHBoxLayout()
        b = QPushButton(_("+ Nouveau personnage…"))
        m = QMenu(b)
        m.addAction(_("Créé par l'IA…"), lambda: self.creer(photo=False))
        m.addAction(_("Depuis une photo (personne d'accord)…"), lambda: self.creer(photo=True))
        m.addAction(_("Un de mes personnages…"), self.ajouter_garde)
        b.setMenu(m)
        h.addWidget(b)
        self.b_retirer = QPushButton(_("Retirer"))
        self.b_retirer.setToolTip(_("Retire le personnage de la scène (il reste dans « Mes personnages »)"))
        self.b_retirer.clicked.connect(self.retirer)
        h.addWidget(self.b_retirer)
        v.addLayout(h)
        self.b_squelette = QPushButton(_("Squelette…"))
        self.b_squelette.setCheckable(True)
        self.b_squelette.setToolTip(_("Montre le dessin d'origine : déplacez les articulations, les yeux et la bouche à la souris"))
        self.b_squelette.toggled.connect(self.mode_squelette)
        self.b_appliquer = QPushButton(_("Appliquer le squelette"))
        self.b_appliquer.clicked.connect(self.appliquer_squelette)
        self.b_appliquer.hide()
        h2 = QHBoxLayout()
        h2.addWidget(self.b_squelette)
        h2.addWidget(self.b_appliquer)
        h2.addStretch(1)
        v.addLayout(h2)
        f = QFormLayout()
        self.s_x, self.s_y, self.s_taille = QSlider(Qt.Horizontal), QSlider(Qt.Horizontal), QSlider(Qt.Horizontal)
        self.s_x.setRange(0, 100)
        self.s_y.setRange(30, 110)
        self.s_taille.setRange(10, 150)
        for s in (self.s_x, self.s_y, self.s_taille):
            s.valueChanged.connect(self._place_change)
        f.addRow(_("Gauche ↔ droite"), self.s_x)
        f.addRow(_("Hauteur des pieds"), self.s_y)
        f.addRow(_("Taille"), self.s_taille)
        self.miroir = QCheckBox(_("Retourné (regarde de l'autre côté)"))
        self.miroir.toggled.connect(self._place_change)
        f.addRow("", self.miroir)
        v.addLayout(f)
        h3 = QHBoxLayout()
        b = QPushButton(_("Noter la place à cet instant"))
        b.setToolTip(_("Le personnage ira d'une place notée à la suivante (pour qu'il traverse l'image en marchant, par exemple)"))
        b.clicked.connect(self.noter_place)
        h3.addWidget(b)
        b = QPushButton(_("Effacer les déplacements"))
        b.clicked.connect(self.effacer_deplacements)
        h3.addWidget(b)
        v.addLayout(h3)
        self.l_depl = QLabel("")
        self.l_depl.setWordWrap(True)
        v.addWidget(self.l_depl)
        return w

    def _onglet_mouvements(self):
        w = QWidget()
        v = QVBoxLayout(w)
        h = QHBoxLayout()
        self.mouvement = QComboBox()
        for k, n in P.liste_mouvements():
            self.mouvement.addItem(n, k)
        h.addWidget(self.mouvement, 1)
        b = QPushButton(_("Ajouter à cet instant"))
        b.setToolTip(_("Le mouvement commence à l'instant du curseur de temps ; sa durée se change dans la liste"))
        b.clicked.connect(self.ajouter_mouvement)
        h.addWidget(b)
        v.addLayout(h)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([_("Mouvement"), _("Début (s)"), _("Durée (s)")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        v.addWidget(self.table, 1)
        h = QHBoxLayout()
        b = QPushButton(_("Retirer le mouvement"))
        b.clicked.connect(self.retirer_mouvement)
        h.addWidget(b)
        b = QPushButton(_("Aller au début"))
        b.clicked.connect(self.aller_mouvement)
        h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        return w

    def _onglet_visage(self):
        w = QWidget()
        v = QVBoxLayout(w)
        h = QHBoxLayout()
        self.expression = QComboBox()
        import unicodedata
        for k, n in sorted(((k, _(n)) for k, n in P.NOMS_EXPRESSIONS.items()),
                           key=lambda x: unicodedata.normalize("NFD", x[1].lower()).encode("ascii", "ignore")):
            self.expression.addItem(n, k)
        h.addWidget(self.expression, 1)
        b = QPushButton(_("Poser à cet instant"))
        b.clicked.connect(self.poser_expression)
        h.addWidget(b)
        v.addLayout(h)
        self.l_expr = QListWidget()
        self.l_expr.setMaximumHeight(110)
        v.addWidget(self.l_expr)
        b = QPushButton(_("Retirer l'expression choisie"))
        b.clicked.connect(self.retirer_expression)
        v.addWidget(b)
        self.cligner = QCheckBox(_("Les yeux clignent tout seuls"))
        self.cligner.toggled.connect(self._cligner)
        v.addWidget(self.cligner)
        v.addWidget(QLabel(_("Voix du personnage choisi (la bouche la suit) :")))
        h = QHBoxLayout()
        b = QPushButton(_("Voix…"))
        m = QMenu(b)
        m.addAction(_("Un fichier son…"), self.voix_fichier)
        m.addAction(_("La partie en jaune (ou le plan sous la ligne rouge)"), self.voix_timeline)
        m.addAction(_("Ecrire le texte (voix de synthèse, gratuite)…"), self.voix_texte)
        b.setMenu(m)
        h.addWidget(b)
        self.b_sync = QPushButton(_("Synchroniser les bouches (gratuit)"))
        self.b_sync.setToolTip(_("Rhubarb Lip Sync lit la voix sur ce poste et donne la forme de la bouche à chaque instant"))
        self.b_sync.clicked.connect(self.synchroniser)
        h.addWidget(self.b_sync)
        v.addLayout(h)
        self.l_voix = QLabel("")
        self.l_voix.setWordWrap(True)
        v.addWidget(self.l_voix)
        b = QPushButton(_("Retirer la voix"))
        b.clicked.connect(self.retirer_voix)
        v.addWidget(b)
        v.addStretch(1)
        return w

    def _onglet_scene(self):
        w = QWidget()
        f = QFormLayout(w)
        self.format = QComboBox()
        for nom, t in FORMATS:
            self.format.addItem(nom, t)
        self.format.currentIndexChanged.connect(self._scene_change)
        f.addRow(_("Format"), self.format)
        self.duree = QDoubleSpinBox()
        self.duree.setRange(0.5, 600)
        self.duree.setDecimals(1)
        self.duree.setSuffix(" s")
        self.duree.setToolTip(_("Allongée d'office si un mouvement ou une voix va plus loin"))
        self.duree.valueChanged.connect(self._scene_change)
        f.addRow(_("Durée"), self.duree)
        self.fond = QComboBox()
        self.fond.addItem(_("Couleur unie"), "couleur")
        self.fond.addItem(_("Image…"), "image")
        self.fond.addItem(_("Transparent (pour poser le personnage sur le film)"), "transparent")
        self.fond.activated.connect(self._fond_choisi)
        f.addRow(_("Fond"), self.fond)
        self.b_couleur = QPushButton(_("Couleur…"))
        self.b_couleur.clicked.connect(self.choisir_couleur)
        f.addRow("", self.b_couleur)
        self.l_fond = QLabel("")
        self.l_fond.setWordWrap(True)
        f.addRow("", self.l_fond)
        return w

    # ---------------------------------------------- état
    def _nom(self, c):
        try:
            return P.charger(c["pantin"]).get("nom") or "?"
        except (OSError, ValueError, KeyError):
            return "?"

    def courant(self):
        i = self.liste.currentRow()
        ps = self.scene.get("personnages", [])
        return ps[i] if 0 <= i < len(ps) else None

    def _etat_en_cours(self):
        return {"scene": self.scene, "chemin": self.chemin_scene}

    def a_garder(self):
        return bool(self.scene.get("personnages"))

    def _change(self):
        """Après chaque changement : la scène est gardée sur le disque, l'aperçu est refait."""
        try:
            P.enregistrer_scene(self.scene, self.chemin_scene)
        except OSError:
            pass
        self.apercu.recharger()
        self._maj_temps()

    def _remplir(self):
        i = self.liste.currentRow()
        self.liste.blockSignals(True)
        self.liste.clear()
        for c in self.scene.get("personnages", []):
            self.liste.addItem(self._nom(c))
        self.liste.blockSignals(False)
        n = self.liste.count()
        self.liste.setCurrentRow(min(max(0, i), n - 1) if n else -1)
        L, H = self.scene.get("taille") or (1920, 1080)
        k = next((j for j, (_n, t) in enumerate(FORMATS) if list(t) == [L, H]), -1)
        self.format.blockSignals(True)
        if k < 0:
            self.format.addItem(f"{L}×{H}", (L, H))
            k = self.format.count() - 1
        self.format.setCurrentIndex(k)
        self.format.blockSignals(False)
        self.duree.blockSignals(True)
        self.duree.setValue(float(self.scene.get("duree") or 6))
        self.duree.blockSignals(False)
        f = self.scene.get("fond") or {}
        self.fond.setCurrentIndex(max(0, self.fond.findData(f.get("type") or "couleur")))
        self.b_couleur.setVisible(f.get("type") == "couleur")
        self.l_fond.setText(os.path.basename(f.get("image") or "") if f.get("type") == "image" else "")
        self._choisi(self.liste.currentRow())
        self._change()

    def _choisi(self, _i):
        c = self.courant()
        actif = c is not None
        for wd in (self.s_x, self.s_y, self.s_taille, self.miroir, self.b_retirer, self.b_squelette):
            wd.setEnabled(actif)
        self.table.setRowCount(0)
        self.l_expr.clear()
        if not actif:
            self.l_voix.setText("")
            self.l_depl.setText("")
            return
        piste = c["piste"]
        pl = piste.get("place") or {}
        for s, v in ((self.s_x, pl.get("x", 0.5) * 100), (self.s_y, pl.get("y", 0.92) * 100),
                     (self.s_taille, pl.get("echelle", 0.8) * 100)):
            s.blockSignals(True)
            s.setValue(int(round(v)))
            s.blockSignals(False)
        self.miroir.blockSignals(True)
        self.miroir.setChecked(bool(pl.get("miroir")))
        self.miroir.blockSignals(False)
        self.cligner.blockSignals(True)
        self.cligner.setChecked(piste.get("clignement", True))
        self.cligner.blockSignals(False)
        self._remplir_table()
        for e in sorted(piste.get("expressions", []), key=lambda x: x["t"]):
            it = QListWidgetItem(f"{e['t']:.1f} s : {_(P.NOMS_EXPRESSIONS.get(e['expression'], e['expression']))}".replace(".", ","))
            it.setData(Qt.UserRole, e)
            self.l_expr.addItem(it)
        v = piste.get("voix") or {}
        self.l_voix.setText(_("Voix : {f}, à {t} s ; {n} formes de bouche.", f=os.path.basename(v["son"]),
                              t=f"{float(v.get('debut') or 0):.1f}".replace(".", ","), n=len(piste.get("bouches", [])))
                            if v.get("son") else _("Pas de voix : la bouche reste fermée."))
        n = len(piste.get("deplacements", []))
        self.l_depl.setText(_("{n} place(s) notée(s) : le personnage va de l'une à l'autre.", n=n) if n else "")

    def _remplir_table(self):
        c = self.courant()
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        if c:
            for a in sorted(c["piste"].get("actions", []), key=lambda a: a["debut"]):
                r = self.table.rowCount()
                self.table.insertRow(r)
                it = QTableWidgetItem(_(P.MOUVEMENTS.get(a["mouvement"], {}).get("nom", a["mouvement"])))
                it.setData(Qt.UserRole, a)
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, 0, it)
                for col, cle in ((1, "debut"), (2, "duree")):
                    sp = QDoubleSpinBox()
                    sp.setRange(0.0 if cle == "debut" else 0.2, 600)
                    sp.setSingleStep(0.1)
                    sp.setDecimals(1)
                    sp.setValue(float(a[cle]))
                    sp.valueChanged.connect(lambda val, a=a, cle=cle: self._action_change(a, cle, val))
                    self.table.setCellWidget(r, col, sp)
        self.table.blockSignals(False)

    def _action_change(self, a, cle, val):
        a[cle] = float(val)
        self._change()

    # ---------------------------------------------- temps et lecture
    def duree_totale(self):
        d = P.duree_scene(self.scene)
        for c in self.scene.get("personnages", []):
            v = c["piste"].get("voix") or {}
            if v.get("son") and v.get("duree"):
                d = max(d, float(v.get("debut") or 0) + float(v["duree"]))
        return d

    def _maj_temps(self):
        D = self.duree_totale()
        self.l_temps.setText(f"{self.apercu.t:.1f} / {D:.1f} s".replace(".", ","))

    def _temps_change(self, v):
        self.apercu.t = v / 1000.0 * self.duree_totale()
        self._maj_temps()
        self.apercu.update()

    def aller(self, t):
        D = self.duree_totale()
        self.temps.blockSignals(True)
        self.temps.setValue(int(round(1000 * max(0.0, min(t, D)) / D)))
        self.temps.blockSignals(False)
        self.apercu.t = max(0.0, min(t, D))
        self._maj_temps()
        self.apercu.update()

    def lire(self):
        if self._lecture.isActive():
            self._arreter_lecture()
            return
        if self.apercu.squelette is not None:
            self.b_squelette.setChecked(False)
        if self.apercu.t >= self.duree_totale() - 0.05:
            self.aller(0.0)
        self._debut_lecture = (time.monotonic(), self.apercu.t)
        self.b_lire.setText(_("⏸ Pause"))
        self._jouer_sons(self.apercu.t)
        self._lecture.start()

    def _jouer_sons(self, t):
        """Le son pendant la lecture : la première voix (ou le son de la scène), calée sur le temps."""
        sons = P.sons_scene(self.scene)
        if not sons or getattr(self, "_test_oui", None) is not None:
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtCore import QUrl
            son, debut = sons[0]
            if self._lecteur is None:
                self._lecteur = QMediaPlayer(self)
                self._sortie = QAudioOutput(self)
                self._lecteur.setAudioOutput(self._sortie)
            self._lecteur.setSource(QUrl.fromLocalFile(son))
            decal = t - debut
            if decal >= 0:
                self._lecteur.setPosition(int(decal * 1000))
                self._lecteur.play()
            else:
                QTimer.singleShot(int(-decal * 1000), lambda: self._lecture.isActive() and self._lecteur.play())
        except Exception:          # noqa: BLE001 : sans son, l'aperçu reste juste
            self._lecteur = None

    def _arreter_lecture(self):
        self._lecture.stop()
        self.b_lire.setText(_("▶ Lire"))
        if self._lecteur is not None:
            try:
                self._lecteur.stop()
            except RuntimeError:
                pass

    def _avancer(self):
        t0, a = self._debut_lecture
        t = a + (time.monotonic() - t0)
        if t >= self.duree_totale():
            self.aller(self.duree_totale())
            self._arreter_lecture()
            return
        self.aller(t)

    # ---------------------------------------------- personnages
    def creer(self, photo=False):
        if self.tache is not None:
            self.etat.setText(_("Attendez la fin du calcul en cours."))
            return
        d = DialogueCreer(self, self.params, photo=photo)
        if getattr(self, "_test_creer", None) is not None:
            v = self._test_creer
        else:
            if d.exec() != QDialog.Accepted:
                return
            v = d.valeurs()
        self.params["pantin_style"] = v["style"]
        if hasattr(self.params, "enregistrer"):
            self.params.enregistrer()
        params = dict(self.params)
        dossier = P.nouveau_dossier(v["nom"])

        def travail(t):
            t.avancer(0.05, _("Dessin du corps (Gemini)…"))
            corps = PI.fabriquer_corps(params, dossier, v["description"], v["style"], photo=v.get("photo"))
            t.avancer(0.40, _("Yeux et bouches (Gemini)…"))
            visage = PI.fabriquer_visage(params, dossier, v["style"])
            t.avancer(0.75, _("Lecture des articulations…"))
            pts = PI.trouver_points(params, dossier, corps)
            pan = P.nouveau(v["nom"], dossier, corps, pts, v["style"])
            pan.update(visage)
            if v.get("photo"):
                pan["photo_accord"] = True
            t.avancer(0.9, _("Découpe des pièces…"))
            P.decouper(pan)
            PI.ajuster_visage(pan)
            return P.enregistrer(pan)

        def fin(r, e):
            if e or not r:
                self.etat.setText("✕ " + (texte_erreur(e) if e else _("rien n'a été créé")))
                return
            self.ajouter_personnage(r)
            self.etat.setText(_("✓ Personnage créé. Vérifiez son squelette (les points jaunes sur les articulations), puis "
                                "ajoutez-lui des mouvements."))
            self.b_squelette.setChecked(True)
        self._lancer(travail, _("Nouveau personnage : {n}", n=v["nom"]), fin)

    def ajouter_garde(self):
        liste = P.mes_personnages()
        if not liste:
            self.etat.setText(_("Aucun personnage gardé sur ce poste : créez-en un d'abord."))
            return
        from PySide6.QtWidgets import QInputDialog
        noms = [n for _c, n in liste]
        nom, ok = QInputDialog.getItem(self, _("Mes personnages"), _("Personnage :"), noms, 0, False)
        if ok:
            self.ajouter_personnage(liste[noms.index(nom)][0])

    def ajouter_personnage(self, chemin):
        piste = P.piste_vide()
        n = len(self.scene.setdefault("personnages", []))
        piste["place"]["x"] = [0.5, 0.3, 0.7, 0.15, 0.85][n % 5]
        self.scene["personnages"].append({"pantin": chemin, "piste": piste})
        self._remplir()
        self.liste.setCurrentRow(self.liste.count() - 1)

    def retirer(self):
        i = self.liste.currentRow()
        if i < 0:
            return
        del self.scene["personnages"][i]
        self._remplir()

    def mode_squelette(self, actif):
        c = self.courant()
        if actif and c:
            self._arreter_lecture()
            self._pantin_edite = P.charger(c["pantin"])
            self.apercu.montrer_squelette(self._pantin_edite)
            self.b_appliquer.show()
        else:
            self.apercu.montrer_squelette(None)
            self.b_appliquer.hide()
            self.apercu.recharger()

    def appliquer_squelette(self):
        pan = getattr(self, "_pantin_edite", None)
        if not pan:
            return
        try:
            P.decouper(pan)
            P.enregistrer(pan)
        except (ValueError, OSError) as e:
            self.etat.setText("✕ " + texte_erreur(e))
            return
        self.etat.setText(_("✓ Squelette appliqué : les pièces sont redécoupées."))
        self.b_squelette.setChecked(False)
        self._change()

    def _place_change(self, *_a):
        c = self.courant()
        if not c:
            return
        pl = c["piste"].setdefault("place", {})
        pl.update({"x": self.s_x.value() / 100.0, "y": self.s_y.value() / 100.0, "echelle": self.s_taille.value() / 100.0,
                   "miroir": self.miroir.isChecked()})
        # pendant les déplacements, la place notée la plus proche de l'instant suit aussi les curseurs
        for dpl in c["piste"].get("deplacements", []):
            if abs(dpl["t"] - self.apercu.t) < 0.05:
                dpl.update({"x": pl["x"], "y": pl["y"], "echelle": pl["echelle"]})
        self._change()

    def noter_place(self):
        c = self.courant()
        if not c:
            return
        pl = c["piste"]["place"]
        ds = [x for x in c["piste"].get("deplacements", []) if abs(x["t"] - self.apercu.t) >= 0.05]
        ds.append({"t": round(self.apercu.t, 2), "x": pl["x"], "y": pl["y"], "echelle": pl["echelle"]})
        c["piste"]["deplacements"] = sorted(ds, key=lambda x: x["t"])
        self._choisi(self.liste.currentRow())
        self._change()

    def effacer_deplacements(self):
        c = self.courant()
        if c:
            c["piste"]["deplacements"] = []
            self._choisi(self.liste.currentRow())
            self._change()

    # ---------------------------------------------- mouvements
    def ajouter_mouvement(self):
        c = self.courant()
        if not c:
            self.etat.setText(_("Ajoutez d'abord un personnage (onglet Personnages)."))
            return
        k = self.mouvement.currentData()
        m = P.MOUVEMENTS[k]
        duree = m["duree"] * (3 if m.get("boucle") else 1)
        c["piste"].setdefault("actions", []).append({"mouvement": k, "debut": round(self.apercu.t, 2), "duree": round(duree, 2)})
        self._remplir_table()
        self._change()
        self.aller(self.apercu.t + 0.01)

    def _action_choisie(self):
        r = self.table.currentRow()
        it = self.table.item(r, 0) if r >= 0 else None
        return it.data(Qt.UserRole) if it else None

    def retirer_mouvement(self):
        c, a = self.courant(), self._action_choisie()
        if c and a:
            c["piste"]["actions"] = [x for x in c["piste"]["actions"] if x is not a and x != a]
            self._remplir_table()
            self._change()

    def aller_mouvement(self):
        a = self._action_choisie()
        if a:
            self.aller(float(a["debut"]))

    # ---------------------------------------------- visage et voix
    def poser_expression(self):
        c = self.courant()
        if not c:
            return
        es = [x for x in c["piste"].get("expressions", []) if abs(x["t"] - self.apercu.t) >= 0.05]
        es.append({"t": round(self.apercu.t, 2), "expression": self.expression.currentData()})
        c["piste"]["expressions"] = sorted(es, key=lambda x: x["t"])
        self._choisi(self.liste.currentRow())
        self._change()

    def retirer_expression(self):
        c, it = self.courant(), self.l_expr.currentItem()
        if c and it:
            e = it.data(Qt.UserRole)
            c["piste"]["expressions"] = [x for x in c["piste"]["expressions"] if x != e]
            self._choisi(self.liste.currentRow())
            self._change()

    def _cligner(self, v):
        c = self.courant()
        if c:
            c["piste"]["clignement"] = bool(v)
            self._change()

    def poser_voix(self, son):
        c = self.courant()
        if not c:
            self.etat.setText(_("Choisissez d'abord le personnage qui parle (onglet Personnages)."))
            return False
        from . import moteur
        duree = float((moteur.sonder(son) or {}).get("duree") or 0)
        c["piste"]["voix"] = {"son": son, "debut": round(self.apercu.t, 2), "duree": duree}
        c["piste"]["bouches"] = []
        self.scene["duree"] = max(float(self.scene.get("duree") or 0), self.apercu.t + duree)
        self.duree.blockSignals(True)
        self.duree.setValue(self.scene["duree"])
        self.duree.blockSignals(False)
        self._choisi(self.liste.currentRow())
        self._change()
        self.etat.setText(_("Voix posée à {t} s. « Synchroniser les bouches » la fait suivre par la bouche (gratuit, sur ce poste).",
                            t=f"{self.apercu.t:.1f}".replace(".", ",")))
        return True

    def voix_fichier(self):
        from .widgets import ouvrir_fichier
        f = ouvrir_fichier(self, _("Voix du personnage"), _("Sons (*.wav *.mp3 *.m4a *.ogg *.flac)"), "musique", self.params)
        if f:
            self.poser_voix(f)

    def voix_timeline(self):
        try:
            son = self.ed.son_pour_voix()
        except Exception as e:      # noqa: BLE001
            self.etat.setText("✕ " + texte_erreur(e))
            return
        self.poser_voix(son)

    def voix_texte(self):
        from . import voix as V
        locales = V.voix_locales()
        if not locales:
            self.etat.setText(_("Aucune voix de synthèse sur ce poste : Aide › IA sur ce poste, puis une voix française."))
            return
        from PySide6.QtWidgets import QInputDialog
        texte, ok = QInputDialog.getMultiLineText(self, _("Ce que dit le personnage"), _("Texte :"))
        if not ok or not texte.strip():
            return
        cle = V.voix_locale_langue("fr") or locales[0][0]
        sortie = os.path.join(P.dossier_scenes(), time.strftime("voix_%Y%m%d_%H%M%S.wav"))
        params = dict(self.params)
        self._lancer(lambda t: V.lire(texte, sortie, params, "local", cle), _("Voix de synthèse"),
                     lambda r, e: self.etat.setText("✕ " + texte_erreur(e)) if e else self.poser_voix(sortie))

    def synchroniser(self):
        c = self.courant()
        v = (c or {}).get("piste", {}).get("voix") or {}
        if not v.get("son"):
            self.etat.setText(_("Posez d'abord une voix (bouton « Voix… »)."))
            return
        if P.rhubarb() is None:
            self.etat.setText(_("Le moteur des bouches (Rhubarb Lip Sync, gratuit) n'est pas installé : Aide › Mises à jour des IA "
                                "› Sur ce poste."))
            return
        son = v["son"]

        def fin(r, e):
            if e:
                self.etat.setText("✕ " + texte_erreur(e))
                return
            decal = float(v.get("debut") or 0)
            c["piste"]["bouches"] = [(round(t + decal, 3), f) for t, f in (r or [])]
            self._choisi(self.liste.currentRow())
            self._change()
            self.etat.setText(_("✓ Bouches synchronisées : {n} changements.", n=len(r or [])))
        self._lancer(lambda t: P.bouches_depuis_son(son, arret=t.arret_demande), _("Synchro des bouches"), fin)

    def retirer_voix(self):
        c = self.courant()
        if c:
            c["piste"].pop("voix", None)
            c["piste"]["bouches"] = []
            self._choisi(self.liste.currentRow())
            self._change()

    # ---------------------------------------------- scène
    def _scene_change(self, *_a):
        t = self.format.currentData()
        if t:
            self.scene["taille"] = list(t)
        self.scene["duree"] = float(self.duree.value())
        self._change()

    def _fond_choisi(self, _i):
        k = self.fond.currentData()
        f = self.scene.setdefault("fond", {})
        if k == "image":
            from .widgets import ouvrir_fichier
            fichier = ouvrir_fichier(self, _("Image de fond"), _("Images (*.png *.jpg *.jpeg *.webp)"), "images", self.params)
            if not fichier:
                self.fond.setCurrentIndex(max(0, self.fond.findData(f.get("type") or "couleur")))
                return
            f.update({"type": "image", "image": fichier})
        else:
            f["type"] = k
            f.setdefault("couleur", "#F4EFE6")
        self.b_couleur.setVisible(k == "couleur")
        self.l_fond.setText(os.path.basename(f.get("image") or "") if k == "image" else "")
        self._change()

    def choisir_couleur(self):
        from PySide6.QtWidgets import QColorDialog
        f = self.scene.setdefault("fond", {"type": "couleur"})
        c = QColorDialog.getColor(QColor(f.get("couleur") or "#F4EFE6"), self)
        if c.isValid():
            f["couleur"] = c.name()
            self._change()

    # ---------------------------------------------- calculs
    def _lancer(self, travail, titre, fin):
        self.tache = Tache(travail, titre)
        self.taches.append(self.tache)
        enc = getattr(self.ed, "encart", None)
        if enc is not None:
            enc.suivre(self.tache, titre)
        self.barre.setValue(0)
        self.barre.show()
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)

        def fini(r, e):
            try:
                self.barre.hide()
                self.tache = None
                if e and getattr(self, "credit", None) is not None:
                    from .credit_ia import fournisseur_epuise
                    if fournisseur_epuise(str(e)) == "google":
                        self.credit.b.setStyleSheet("background:#c62828;color:white;font-weight:600")
                fin(r, e)
            except RuntimeError:
                pass
        self.tache.fini.connect(fini, Qt.QueuedConnection)
        self.tache.start()

    def fabriquer(self):
        if not self.scene.get("personnages"):
            self.etat.setText(_("Ajoutez d'abord un personnage."))
            return
        if self.tache is not None:
            self.etat.setText(_("Attendez la fin du calcul en cours."))
            return
        from .creations import dossier, ecrire
        sc = copy.deepcopy(self.scene)
        sc["duree"] = self.duree_totale()
        sortie = os.path.join(dossier(), time.strftime("pantin_%Y%m%d_%H%M%S.mp4"))
        self.b_fabriquer.setEnabled(False)

        def fin(r, e):
            self.b_fabriquer.setEnabled(True)
            if e or not r:
                self.etat.setText("✕ " + (texte_erreur(e) if e else _("rien n'a été fabriqué")))
                return
            ecrire(r, {"outil": "pantin", "famille": "pantin", "scene": self.chemin_scene,
                       "resume": ", ".join(self._nom(c) for c in self.scene.get("personnages", []))})
            self.resultat = r
            self.etat.setText(_("✓ Vidéo prête : regardez-la, puis posez-la."))
            if getattr(self, "_test_oui", None) is None:
                from .dialogues_motion import ResultatAnimation
                ResultatAnimation(self.ed, r, {"duree": sc["duree"], "genre": "pantin"}).exec()
        self._lancer(lambda t: P.fabriquer(sc, sortie, t.avancer, t.arret_demande), _("Personnage animé : fabrication"), fin)

    # ---------------------------------------------- fermer sans rien perdre
    def reduire(self):
        from .widgets import reafficher
        self._arreter_lecture()
        self.hide()
        e = getattr(self.ed, "encart", None)
        if e is not None and getattr(e, "tache", None) is None:
            e.suivre_message(_("Personnage animé rangé : votre travail est gardé."),
                             (_("Afficher le personnage animé"), lambda: reafficher(self)), 20000)

    def done(self, r):
        from .widgets import calcul_en_cours, garder_calcul
        if garder_calcul(self, calcul_en_cours(self)):
            return
        self._arreter_lecture()
        if self.a_garder() and not getattr(self, "_jeter", False):
            self.reduire()
            return
        super().done(r)
