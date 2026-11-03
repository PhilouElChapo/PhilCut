"""La page de montage d'un projet : barre d'outils en flux (personnalisable), bibliotheque a gauche, apercu au
centre, volet a droite (Proposition de l'assistant, Proprietes), timeline en bas, encart de progression."""
import os

from PySide6.QtCore import Qt, QTimer, Signal, QMimeData, QSize, QByteArray
from PySide6.QtGui import QPixmap, QIcon, QDrag, QAction, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem, QLabel, QPushButton, QToolButton,
                               QFrame, QProgressBar, QTabWidget, QScrollArea, QCheckBox, QComboBox, QLineEdit, QSpinBox, QMenu, QMessageBox,
                               QFileDialog, QSizePolicy, QFormLayout, QPlainTextEdit, QAbstractItemView, QInputDialog)

from . import moteur, outils as O, recettes, assistant as A, suivi, theme
from .apercu import Apercu
from .icones import icone
from .langue import _
from .projet import fin_clip, duree_clip
from .taches import Tache, importer_media
from .timeline import Timeline, MIME_MEDIA
from .widgets import FluxLayout, _SurveilleTaille
from .dialogues_video import DialogueTitre, DialogueEffets, DialogueGoodie, DialogueVitesse, DialogueFiche


class Encart(QFrame):
    """Encart non bloquant : une operation longue, sa progression, son resultat, un bouton d'action."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("encart")
        self.setStyleSheet("QFrame#encart{background:%s;border-top:1px solid %s}" % (theme.COULEURS["surface"], theme.COULEURS["bord"]))
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 4, 10, 4)
        self.lbl = QLabel("")
        self.lbl.setMinimumWidth(240)
        h.addWidget(self.lbl, 1)
        self.barre = QProgressBar()
        self.barre.setMaximumWidth(260)
        self.barre.setRange(0, 1000)
        h.addWidget(self.barre)
        self.bouton = QPushButton("")
        self.bouton.hide()
        h.addWidget(self.bouton)
        self.b_stop = QPushButton(_("Arrêter"))
        h.addWidget(self.b_stop)
        self.hide()
        self.tache = None

    def suivre(self, tache, texte, action=None):
        """action : (libelle, fonction) proposee a la fin."""
        self.tache = tache
        self.lbl.setText(texte)
        self.barre.setValue(0)
        self.bouton.hide()
        self.b_stop.show()
        try:
            self.b_stop.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.b_stop.clicked.connect(tache.stopper)
        tache.progression.connect(lambda f, t: (self.barre.setValue(int(f * 1000)), self.lbl.setText(texte + (" — " + t if t else ""))))
        tache.fini.connect(lambda r, e: self._fin(texte, e, action))
        self.show()

    def _fin(self, texte, erreur, action):
        self.b_stop.hide()
        if erreur:
            self.lbl.setText(_("✕ {t} : {e}", t=texte, e=str(erreur)[:180]))
            self.lbl.setToolTip(str(erreur))
            self.bouton.setText(_("Fermer"))
            self.bouton.show()
            try:
                self.bouton.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.bouton.clicked.connect(self.hide)
            return
        self.barre.setValue(1000)
        self.lbl.setText(_("✓ {t}", t=texte))
        if action:
            self.bouton.setText(action[0])
            self.bouton.show()
            try:
                self.bouton.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.bouton.clicked.connect(lambda: (action[1](), self.hide()))
            QTimer.singleShot(60000, self.hide)
        else:
            QTimer.singleShot(4000, self.hide)

    def message(self, texte, duree=5000):
        self.tache = None
        self.lbl.setText(texte)
        self.barre.setValue(1000)
        self.b_stop.hide()
        self.bouton.hide()
        self.show()
        QTimer.singleShot(duree, self.hide)


class Bibliotheque(QListWidget):
    """Les medias du projet : vignette, nom, resume ; glisser vers la timeline ; double-clic = ajouter a la fin."""
    ajouter = Signal(str)
    fiche = Signal(str)
    retirer = Signal(str)
    importer = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(128, 72))
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Static)
        self.setSpacing(6)
        self.setWordWrap(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemDoubleClicked.connect(lambda it: self.ajouter.emit(it.data(Qt.UserRole)))
        self.projet = None

    def remplir(self, projet):
        self.projet = projet
        self.clear()
        for m in projet.medias:
            it = QListWidgetItem(m["nom"])
            it.setData(Qt.UserRole, m["id"])
            px = QPixmap(m["vignettes"]) if m.get("vignettes") and os.path.exists(m["vignettes"]) else QPixmap()
            if not px.isNull():
                it.setIcon(QIcon(px.copy(0, 0, min(px.width(), int(px.height() * 16 / 9) if px.height() else px.width()), px.height())))
            else:
                it.setIcon(icone({"audio": "musique", "image": "image"}.get(m.get("genre"), "camera"), theme.COULEURS["texte2"], 64))
            res = (m.get("analyse") or {}).get("resume") or moteur.resume_fiche(m.get("fiche"))
            it.setToolTip(f"{m['chemin']}\n{res}" + ("" if os.path.exists(m["chemin"]) else "\n" + _("INTROUVABLE")))
            if not os.path.exists(m["chemin"]):
                it.setForeground(QColor("#ff5c5c"))
            self.addItem(it)

    def startDrag(self, actions):
        ids = [it.data(Qt.UserRole) for it in self.selectedItems()]
        if not ids:
            return
        md = QMimeData()
        md.setData(MIME_MEDIA, QByteArray(";".join(ids).encode("utf-8")))
        d = QDrag(self)
        d.setMimeData(md)
        d.exec(Qt.CopyAction)

    def _menu(self, pos):
        it = self.itemAt(pos)
        m = QMenu(self)
        m.addAction(icone("importer"), _("Importer…"), self.importer.emit)
        if it:
            ident = it.data(Qt.UserRole)
            m.addAction(icone("plus"), _("Ajouter à la fin de la timeline"), lambda: self.ajouter.emit(ident))
            m.addAction(icone("liste_fichiers"), _("Fiche vidéo"), lambda: self.fiche.emit(ident))
            m.addAction(icone("supprimer"), _("Retirer du projet"), lambda: self.retirer.emit(ident))
        m.exec(self.mapToGlobal(pos))


class VoletProposition(QWidget):
    """Le volet de l'assistant : analyser, proposer, cocher, autre idee, appliquer."""
    analyser = Signal()
    appliquer = Signal(dict, bool)      # recette filtree, remplacer
    autre_idee = Signal(str)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.params = params
        self.recette = None
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        f = QFormLayout()
        self.indices = QLineEdit()
        self.indices.setPlaceholderText(_("Indications : « vol au-dessus de Cannes », « pour Insta »…"))
        f.addRow(_("Indications"), self.indices)
        self.format = QComboBox()
        for k, lib in (("", _("Selon les rushes")), ("16:9", _("16:9 YouTube")), ("9:16", _("9:16 Insta / Shorts"))):
            self.format.addItem(lib, k)
        f.addRow(_("Format"), self.format)
        self.duree = QSpinBox()
        self.duree.setRange(0, 3600)
        self.duree.setSpecialValueText(_("auto"))
        self.duree.setSuffix(" s")
        f.addRow(_("Durée cible"), self.duree)
        self.niveau = QComboBox()
        for k, lib in (("recettes", _("Recettes sans IA (gratuit)")), ("locale", _("IA locale (sur ce poste)")), ("cloud", _("IA cloud (Claude / Gemini)"))):
            self.niveau.addItem(lib, k)
            if k == (params.get("assistant_niveau") or "recettes"):
                self.niveau.setCurrentIndex(self.niveau.count() - 1)
        f.addRow(_("Niveau"), self.niveau)
        v.addLayout(f)
        self.b_go = QPushButton(icone("assistant", "#ffffff"), _("Analyser et proposer"))
        self.b_go.setProperty("primaire", True)
        self.b_go.clicked.connect(self.analyser.emit)
        v.addWidget(self.b_go)
        self.resume = QLabel("")
        self.resume.setWordWrap(True)
        v.addWidget(self.resume)
        self.zone = QScrollArea()
        self.zone.setWidgetResizable(True)
        self.corps = QWidget()
        self.vc = QVBoxLayout(self.corps)
        self.vc.setAlignment(Qt.AlignTop)
        self.zone.setWidget(self.corps)
        v.addWidget(self.zone, 1)
        h = QHBoxLayout()
        self.b_remplacer = QPushButton(_("Appliquer (remplace la timeline)"))
        self.b_remplacer.setProperty("primaire", True)
        self.b_remplacer.clicked.connect(lambda: self.appliquer.emit(self.recette_filtree(), True))
        self.b_ajouter = QPushButton(_("Ajouter à la suite"))
        self.b_ajouter.clicked.connect(lambda: self.appliquer.emit(self.recette_filtree(), False))
        h.addWidget(self.b_remplacer)
        h.addWidget(self.b_ajouter)
        v.addLayout(h)
        self.b_remplacer.setEnabled(False)
        self.b_ajouter.setEnabled(False)
        self.cases = {}

    def montrer(self, recette):
        self.recette = recette
        self.cases = {}
        while self.vc.count():
            it = self.vc.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not recette:
            self.resume.setText("")
            return
        src = {"recettes": _("recette sans IA"), }.get(recette.get("source"), recette.get("source", ""))
        self.resume.setText(f"<b>{recette.get('type_nom') or recette.get('type', '')}</b> — {recette.get('resume', '')}<br><span style='color:#999'>{src}</span>"
                            + (f"<br><span style='color:#ff8c5c'>{recette['avertissement']}</span>" if recette.get("avertissement") else ""))

        def ligne(cle, titre, detail, pourquoi=""):
            w = QFrame()
            w.setStyleSheet("QFrame{border:1px solid %s;border-radius:6px;background:%s}" % (theme.COULEURS["bord_leger"], theme.COULEURS["surface"]))
            hl = QHBoxLayout(w)
            hl.setContentsMargins(6, 4, 6, 4)
            c = QCheckBox()
            c.setChecked(True)
            self.cases[cle] = c
            hl.addWidget(c)
            lb = QLabel(f"<b>{titre}</b><br>{detail}" + (f"<br><span style='color:#999'>{pourquoi}</span>" if pourquoi else ""))
            lb.setWordWrap(True)
            lb.setStyleSheet("border:none;background:transparent")
            hl.addWidget(lb, 1)
            b = QToolButton()
            b.setIcon(icone("retablir", theme.COULEURS["texte2"]))
            b.setToolTip(_("Autre idée pour cet élément"))
            b.clicked.connect(lambda _c, cle=cle: self.autre_idee.emit(cle))
            hl.addWidget(b)
            self.vc.addWidget(w)
        lg = recette.get("logo") or {}
        if lg:
            ligne("logo", _("Logo d'ouverture"), _("« {t} », animation {m}, {d} s", t=lg.get("texte", ""), m=lg.get("modele", ""), d=lg.get("duree", 2.5)), lg.get("pourquoi", ""))
        mu = recette.get("musique") or {}
        if mu:
            ligne("musique", _("Musique"), _("ambiance {a}, ≈ {b} BPM", a=mu.get("ambiance", ""), b=mu.get("bpm", "?")) + ("" if mu.get("media") else _(" — aucune musique importée : ajoutez-en une dans la bibliothèque")), mu.get("pourquoi", ""))
        if recette.get("look"):
            ligne("look", _("Look"), recette["look"])
        for i, p in enumerate(recette.get("plans") or []):
            ligne(f"plan:{i}", _("Plan {n} — {nom}", n=i + 1, nom=p.get("nom", "")),
                  _("{a} → {b} s, ×{v}{e}{t}", a=p.get("src_debut"), b=p.get("src_fin"), v=p.get("vitesse", 1),
                    e=(", " + ", ".join(e["id"] for e in p.get("effets") or [])) if p.get("effets") else "",
                    t=(", transition " + (p.get("transition") or {}).get("id", "")) if p.get("transition") else ""), p.get("pourquoi", ""))
        for i, t in enumerate(recette.get("textes") or []):
            ligne(f"texte:{i}", _("Texte « {t} »", t=t.get("texte", "")), _("{a} → {b} s, {an}{s}", a=t.get("debut"), b=t.get("fin"), an=t.get("animation", ""),
                                                                            s=_(" (étiquette accrochée)") if t.get("suivre_visage") else ""), t.get("pourquoi", ""))
        for i, g in enumerate(recette.get("goodies") or []):
            ligne(f"goodie:{i}", _("Goodie {g}", g=g.get("genre", "")), _("{a} → {b} s", a=g.get("debut"), b=g.get("fin")), g.get("pourquoi", ""))
        for i, pg in enumerate(recette.get("plans_a_generer") or []):
            lb = QLabel(_("<b>Plan à générer ({u}, {d} s)</b> : {c}<br><span style='color:#999'>Fabrique › Plan généré par IA</span>", u=pg.get("usage", ""), d=pg.get("duree", 8), c=pg.get("consigne", "")))
            lb.setWordWrap(True)
            self.vc.addWidget(lb)
        pub = recette.get("publication") or {}
        if pub:
            lb = QLabel(_("<b>Publication</b> : {t}<br>{d}<br><span style='color:#999'>{m}</span>", t=pub.get("titre", ""), d=pub.get("description", ""), m=", ".join(pub.get("mots_clefs") or [])))
            lb.setWordWrap(True)
            self.vc.addWidget(lb)
        self.b_remplacer.setEnabled(True)
        self.b_ajouter.setEnabled(True)

    def recette_filtree(self):
        return {"recette": self.recette, "choix": {k: c.isChecked() for k, c in self.cases.items()}}


class Editeur(QWidget):
    titre_change = Signal()
    demande_outil = Signal(str)

    def __init__(self, fenetre, projet, params):
        super().__init__()
        self.fenetre = fenetre
        self.projet = projet
        self.params = params
        self.taches = []
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addWidget(self._barre())
        self.split_v = QSplitter(Qt.Vertical)
        self.split_h = QSplitter(Qt.Horizontal)
        # ---- gauche : bibliotheque
        g = QWidget()
        vg = QVBoxLayout(g)
        vg.setContentsMargins(6, 6, 6, 6)
        hg = QHBoxLayout()
        lb = QLabel(_("<b>Bibliothèque</b>"))
        hg.addWidget(lb)
        hg.addStretch(1)
        b_imp = QToolButton()
        b_imp.setIcon(icone("importer", theme.COULEURS["accent"]))
        b_imp.setToolTip(_("Importer des rushes, musiques ou images"))
        b_imp.clicked.connect(self.importer)
        hg.addWidget(b_imp)
        vg.addLayout(hg)
        self.biblio = Bibliotheque()
        self.biblio.ajouter.connect(lambda i: self.ajouter_a_la_timeline(i))
        self.biblio.fiche.connect(self.montrer_fiche)
        self.biblio.retirer.connect(self.retirer_media)
        self.biblio.importer.connect(self.importer)
        vg.addWidget(self.biblio, 1)
        self.split_h.addWidget(g)
        # ---- centre : apercu + transport
        c = QWidget()
        vc = QVBoxLayout(c)
        vc.setContentsMargins(0, 0, 0, 0)
        vc.setSpacing(0)
        self.apercu = Apercu(projet, params)
        vc.addWidget(self.apercu, 1)
        vc.addWidget(self._transport())
        self.split_h.addWidget(c)
        # ---- droite : volet
        self.volet = QTabWidget()
        self.proposition = VoletProposition(params)
        self.proposition.analyser.connect(self.analyser)
        self.proposition.appliquer.connect(self.appliquer_recette)
        self.proposition.autre_idee.connect(self.autre_idee)
        self.volet.addTab(self.proposition, icone("assistant", theme.COULEURS["texte2"]), _("Proposition"))
        self.proprietes = QLabel(_("Sélectionnez un plan, un texte ou un Goodie."))
        self.proprietes.setWordWrap(True)
        self.proprietes.setAlignment(Qt.AlignTop)
        self.proprietes.setContentsMargins(8, 8, 8, 8)
        self.volet.addTab(self.proprietes, icone("liste_fichiers", theme.COULEURS["texte2"]), _("Propriétés"))
        self.split_h.addWidget(self.volet)
        self.split_h.setSizes([260, 900, 340])
        self.split_h.setStretchFactor(1, 1)
        self.split_v.addWidget(self.split_h)
        # ---- bas : timeline
        self.timeline = Timeline(projet)
        self.timeline.position_changee.connect(self._curseur)
        self.timeline.modifie.connect(self._modifie)
        self.timeline.proprietes.connect(self.editer_element)
        self.timeline.media_depose.connect(self._depose)
        self.timeline.selection_changee.connect(self._selection)
        self.timeline.demande_menu.connect(self._demande_menu)
        self.split_v.addWidget(self.timeline)
        self.split_v.setSizes([620, 260])
        v.addWidget(self.split_v, 1)
        self.encart = Encart(self)
        v.addWidget(self.encart)
        self.apercu.position_changee.connect(lambda t: self.timeline.aller_a(t, emettre=False) if self.apercu.en_lecture else None)
        self.apercu.position_changee.connect(self._temps)
        self.apercu.etat_lecture.connect(self._etat_lecture)
        self.biblio.remplir(projet)
        self.rafraichir()

    # ---------------------------------------------------------------- barre d'outils en flux
    def _barre(self):
        w = QFrame()
        w.setObjectName("barre")
        w.setStyleSheet("QFrame#barre{background:%s;border-bottom:1px solid %s} QToolButton{font-size:11px}" % (theme.COULEURS["surface"], theme.COULEURS["bord_leger"]))
        self.flux = FluxLayout(w, marge=6, espace=2)
        self.barre_w = w
        w.setContextMenuPolicy(Qt.CustomContextMenu)
        w.customContextMenuRequested.connect(lambda p: self._menu_barre(w.mapToGlobal(p)))
        self.construire_barre()
        return w

    def _bouton(self, ic, texte, f, aide=""):
        b = QToolButton()
        b.setIcon(icone(ic, theme.COULEURS["texte"]))
        b.setText(texte)
        style = self.params.get("barre_style", "auto")
        b.setToolButtonStyle({"icone": Qt.ToolButtonIconOnly, "nom": Qt.ToolButtonTextOnly}.get(style, Qt.ToolButtonTextUnderIcon))
        taille = int(self.params.get("barre_taille", 22))
        b.setIconSize(QSize(taille, taille))
        b.setToolTip(aide or texte)
        b.clicked.connect(f)
        b.setAutoRaise(True)
        return b

    def construire_barre(self):
        fl = self.flux
        while fl.count():
            it = fl.takeAt(0)
            w = it.widget() if it is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        for cle in self.params.get("barre") or O.BARRE_DEFAUT:
            if cle == "|":
                s = QFrame()
                s.setFrameShape(QFrame.VLine)
                s.setStyleSheet("color:%s" % theme.COULEURS["bord"])
                fl.addWidget(s)
            elif cle == "annuler":
                fl.addWidget(self._bouton("annuler", _("Annuler|action"), self.annuler, _("Annuler (Ctrl+Z)")))
            elif cle == "retablir":
                fl.addWidget(self._bouton("retablir", _("Rétablir"), self.refaire, _("Rétablir (Ctrl+Y)")))
            elif cle == "lecture":
                fl.addWidget(self._bouton("lecture", _("Lecture"), lambda: self.apercu.basculer(), _("Lecture / pause (Espace)")))
            elif cle == "zoom":
                z = QWidget()
                hz = QHBoxLayout(z)
                hz.setContentsMargins(0, 0, 0, 0)
                hz.setSpacing(0)
                hz.addWidget(self._bouton("zoom_moins", "", lambda: self.timeline.zoomer(1 / 1.3), _("Zoom arrière de la timeline")))
                hz.addWidget(self._bouton("zoom_plus", "", lambda: self.timeline.zoomer(1.3), _("Zoom avant de la timeline")))
                hz.addWidget(self._bouton("format", "", lambda: self.timeline.ajuster(), _("Tout voir")))
                fl.addWidget(z)
            elif cle == "aimant":
                b = self._bouton("aimant", _("Aimant"), lambda: None, _("Coller les plans entre eux et au curseur"))
                b.setCheckable(True)
                b.setChecked(getattr(getattr(self, "timeline", None), "aimant", True))
                b.toggled.connect(lambda on: setattr(self.timeline, "aimant", on))
                fl.addWidget(b)
            elif cle == "volet":
                b = self._bouton("liste_fichiers", _("Volet"), self.basculer_volet, _("Volet de droite : complet → icônes → masqué"))
                fl.addWidget(b)
            else:
                o = O.outil(cle)
                if o:
                    fl.addWidget(self._bouton(o[2], o[3], lambda _c=False, oid=cle: self.outil(oid), o[5]))
        fl.invalidate()

    def _menu_barre(self, pos):
        m = QMenu(self)
        sm = m.addMenu(_("Boutons"))
        for lib, st in ((_("Icône et nom"), "auto"), (_("Icône seule"), "icone"), (_("Nom seul"), "nom")):
            a = sm.addAction(lib, lambda st=st: self._style_barre("barre_style", st))
            a.setCheckable(True)
            a.setChecked(self.params.get("barre_style", "auto") == st)
        st = m.addMenu(_("Taille des icônes"))
        for lib, t in ((_("Petites"), 18), (_("Moyennes"), 22), (_("Grandes"), 28)):
            a = st.addAction(lib, lambda t=t: self._style_barre("barre_taille", t))
            a.setCheckable(True)
            a.setChecked(int(self.params.get("barre_taille", 22)) == t)
        m.addSeparator()
        m.addAction(_("Personnaliser la barre…"), self.fenetre.personnaliser_barre)
        m.exec(pos)

    def _style_barre(self, cle, val):
        self.params[cle] = val
        self.params.enregistrer()
        self.fenetre.reconstruire_barres()

    def basculer_volet(self):
        mode = self.params.get("volet", "complet")
        suivant = {"complet": "icones", "icones": "masque", "masque": "complet"}[mode]
        self.params["volet"] = suivant
        self.params.enregistrer()
        self.appliquer_volet()

    def appliquer_volet(self):
        mode = self.params.get("volet", "complet")
        if mode == "masque":
            self.volet.hide()
        else:
            self.volet.show()
            tailles = self.split_h.sizes()
            if mode == "icones":
                self.volet.setMaximumWidth(44)
                self.volet.tabBar().setExpanding(False)
                for i in range(self.volet.count()):
                    self.volet.setTabText(i, "")
            else:
                self.volet.setMaximumWidth(16777215)
                self.volet.setTabText(0, _("Proposition"))
                self.volet.setTabText(1, _("Propriétés"))
                if tailles and tailles[-1] < 120:
                    tailles[-1] = 340
                    self.split_h.setSizes(tailles)

    # ---------------------------------------------------------------- transport
    def _transport(self):
        w = QFrame()
        w.setStyleSheet("QFrame{background:%s;border-top:1px solid %s}" % (theme.COULEURS["surface"], theme.COULEURS["bord_leger"]))
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 2, 8, 2)
        self.lbl_temps = QLabel("0:00.0")
        self.lbl_temps.setStyleSheet("font-family:Consolas,monospace;font-size:14px;font-weight:600")
        h.addWidget(self.lbl_temps)
        h.addStretch(1)
        for ic, aide, f in (("debut", _("Début (Origine)"), lambda: self.aller_a(0)), ("image_prec", _("Image précédente (←)"), lambda: self.aller_a(self.timeline.position - 1 / self.projet.cadence))):
            h.addWidget(self._petit(ic, aide, f))
        self.b_lecture = self._petit("lecture", _("Lecture / pause (Espace)"), self.apercu.basculer)
        self.b_lecture.setIconSize(QSize(30, 30))
        h.addWidget(self.b_lecture)
        for ic, aide, f in (("image_suiv", _("Image suivante (→)"), lambda: self.aller_a(self.timeline.position + 1 / self.projet.cadence)), ("fin", _("Fin"), lambda: self.aller_a(self.projet.duree()))):
            h.addWidget(self._petit(ic, aide, f))
        b_boucle = self._petit("boucle", _("Lire en boucle"), lambda: None)
        b_boucle.setCheckable(True)
        b_boucle.toggled.connect(lambda on: setattr(self.apercu, "boucle", on))
        h.addWidget(b_boucle)
        h.addStretch(1)
        self.lbl_duree = QLabel("")
        self.lbl_duree.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
        h.addWidget(self.lbl_duree)
        b_rendu = QPushButton(_("Aperçu rendu"))
        b_rendu.setToolTip(_("Exporte en petit les 10 secondes autour du curseur, avec tous les effets, et l'ouvre."))
        b_rendu.clicked.connect(self.apercu_rendu)
        h.addWidget(b_rendu)
        return w

    def _petit(self, ic, aide, f):
        b = QToolButton()
        b.setIcon(icone(ic, theme.COULEURS["texte"]))
        b.setIconSize(QSize(22, 22))
        b.setToolTip(aide)
        b.setAutoRaise(True)
        b.clicked.connect(f)
        return b

    def _etat_lecture(self, on):
        self.b_lecture.setIcon(icone("pause" if on else "lecture", theme.COULEURS["texte"]))

    def _temps(self, t):
        m, s = divmod(t, 60)
        self.lbl_temps.setText(f"{int(m)}:{s:04.1f}")

    def _curseur(self, t):
        if not self.apercu.en_lecture:
            self.apercu.aller_a(t)
        self._temps(t)

    def aller_a(self, t):
        self.apercu.pause()
        self.timeline.aller_a(max(0.0, min(t, self.projet.duree())))

    # ---------------------------------------------------------------- etat
    def rafraichir(self):
        self.timeline.reconstruire()
        self.apercu.aller_a(self.timeline.position, forcer=True)
        self.lbl_duree.setText(_("Durée : {d} · {f}", d=moteur.duree_texte(self.projet.duree()), f=self.projet.format))
        self.titre_change.emit()

    def _modifie(self):
        self.projet.modifie = True
        self.lbl_duree.setText(_("Durée : {d} · {f}", d=moteur.duree_texte(self.projet.duree()), f=self.projet.format))
        self.apercu.aller_a(self.timeline.position, forcer=True)
        self.titre_change.emit()

    def annuler(self):
        if self.projet.annuler():
            self.rafraichir()

    def refaire(self):
        if self.projet.refaire():
            self.rafraichir()

    def _selection(self, ids):
        if not ids:
            self.proprietes.setText(_("Sélectionnez un plan, un texte ou un Goodie."))
            return
        c = self.projet.clip(ids[0])
        if c:
            m = self.projet.media(c["media"]) or {}
            self.proprietes.setText(_("<b>{n}</b><br>Piste : {p}<br>Position : {d:.2f} s → {f:.2f} s (durée {du:.2f} s)<br>Dans le rush : {a:.2f} → {b:.2f} s<br>Vitesse ×{v}<br>"
                                      "Cadrage : {c}<br>Effets : {e}<br>Transition : {t}<br><br><span style='color:#999'>{r}</span><br><br>Double-clic sur le plan : effets et transition.",
                                      n=c.get("nom", ""), p=c["piste"], d=c["debut"], f=fin_clip(c), du=duree_clip(c), a=c["src_debut"], b=c["src_fin"], v=c.get("vitesse", 1),
                                      c=c.get("ajustement", "remplir"), e=", ".join(e["id"] for e in c.get("effets") or []) or "—", t=(c.get("transition") or {}).get("id") or "—",
                                      r=(m.get("analyse") or {}).get("resume") or moteur.resume_fiche(m.get("fiche"))))
            return
        for t in self.projet.titres:
            if t["id"] == ids[0]:
                self.proprietes.setText(_("<b>Texte</b> « {t} »<br>{a:.2f} → {b:.2f} s · {an}{s}", t=t["texte"], a=t["debut"], b=t["fin"], an=t.get("animation", ""),
                                          s=_(" · accroché à une personne") if t.get("suivi") else ""))
        for g in self.projet.goodies:
            if g["id"] == ids[0]:
                self.proprietes.setText(_("<b>Goodie</b> {g}<br>{a:.2f} → {b:.2f} s · {n} valeurs", g=g["genre"], a=g["debut"], b=g["fin"], n=len(g.get("valeurs") or [])))

    # ---------------------------------------------------------------- medias
    def importer(self, chemins=None):
        if not chemins:
            filtres = _("Vidéos, sons, images") + " (*.mp4 *.mov *.mkv *.m4v *.webm *.avi *.mts *.m2ts *.3gp *.mp3 *.wav *.m4a *.aac *.flac *.ogg *.jpg *.jpeg *.png *.webp *.heic);;" + _("Tous") + " (*)"
            chemins, _f = QFileDialog.getOpenFileNames(self, _("Importer"), self.params.get("dernier_dossier") or "", filtres)
        if not chemins:
            return
        self.params["dernier_dossier"] = os.path.dirname(chemins[0])
        self.params.enregistrer()
        self._file_import = list(chemins)
        self._importer_suivant()

    def _importer_suivant(self):
        if not self._file_import:
            return
        chemin = self._file_import.pop(0)
        if not os.path.exists(chemin):
            self._importer_suivant()
            return
        t = Tache(lambda tache: importer_media(tache, chemin, self.params), _("Import"))
        self.taches.append(t)
        reste = len(self._file_import)
        self.encart.suivre(t, _("Import de {n}", n=os.path.basename(chemin)) + (_(" (+{r})", r=reste) if reste else ""))
        t.fini.connect(lambda r, e, chemin=chemin, t=t: self._importe(chemin, r, e, t))
        t.start()

    def _importe(self, chemin, r, e, t):
        if t in self.taches:
            self.taches.remove(t)
        if e:
            QMessageBox.warning(self, _("Import"), _("{f} : {e}", f=os.path.basename(chemin), e=e))
        else:
            self.projet.marquer()
            m = self.projet.ajouter_media(chemin, r["fiche"])
            m.update(proxy=r.get("proxy", ""), vignettes=r.get("vignettes", ""), onde=r.get("onde") or [], niveaux=r.get("niveaux"))
            self.biblio.remplir(self.projet)
            if not self.projet.clips and m["genre"] in ("video", "image") and self.params.get("ajout_auto", True):
                self.ajouter_a_la_timeline(m["id"])
            self._modifie()
        self._importer_suivant()

    def ajouter_a_la_timeline(self, ident, piste=None, debut=None):
        m = self.projet.media(ident)
        if not m:
            return
        self.projet.marquer()
        c = self.projet.ajouter_clip(ident, piste, debut)
        if m.get("genre") == "video" and m.get("fiche", {}).get("vertical") and self.projet.format != "9:16":
            c["ajustement"] = "contenir_flou"
        self.projet.ranger(c["piste"])
        self.rafraichir()
        self.timeline.selectionner(c["id"])

    def _depose(self, ident, piste, t):
        if ident.startswith("fichier:"):
            self._piste_depot = (piste, t)
            self.importer([ident[8:]])
            return
        self.ajouter_a_la_timeline(ident, piste, t)

    def retirer_media(self, ident):
        m = self.projet.media(ident)
        if not m:
            return
        if any(c["media"] == ident for c in self.projet.clips):
            if QMessageBox.question(self, _("Retirer"), _("« {n} » est utilisé dans la timeline. Le retirer quand même (ses plans disparaissent) ?", n=m["nom"])) != QMessageBox.Yes:
                return
        self.projet.marquer()
        self.projet.retirer_media(ident)
        self.biblio.remplir(self.projet)
        self.rafraichir()

    def montrer_fiche(self, ident):
        m = self.projet.media(ident)
        if not m:
            return
        if not m.get("analyse"):
            t = Tache(lambda tache: __import__("app.fiche", fromlist=["depuis_media"]).depuis_media(m, self.params, progression=tache.avancer), _("Fiche"))
            self.taches.append(t)
            self.encart.suivre(t, _("Analyse de {n}", n=m["nom"]), (_("Voir la fiche"), lambda: DialogueFiche(self, m).exec()))
            t.fini.connect(lambda r, e: self.biblio.remplir(self.projet))
            t.start()
            return
        DialogueFiche(self, m).exec()

    # ---------------------------------------------------------------- outils
    def outil(self, oid):
        if oid == "importer":
            self.importer()
        elif oid == "couper":
            self.timeline.couper_au_curseur()
        elif oid == "supprimer":
            self.timeline.supprimer_selection(True)
        elif oid == "vitesse":
            self.vitesse()
        elif oid == "recadrer":
            self.cadrage()
        elif oid == "stabiliser":
            self._ajouter_effet_selection("stabiliser")
        elif oid == "assistant":
            self.volet.show()
            self.volet.setCurrentIndex(0)
            if self.params.get("volet") == "masque":
                self.params["volet"] = "complet"
                self.appliquer_volet()
        elif oid == "fiche":
            ids = self.timeline.selection()
            c = self.projet.clip(ids[0]) if ids else None
            if c:
                self.montrer_fiche(c["media"])
            elif self.biblio.currentItem():
                self.montrer_fiche(self.biblio.currentItem().data(Qt.UserRole))
        elif oid == "texte":
            self.nouveau_texte()
        elif oid == "effets":
            ids = self.timeline.selection()
            if ids:
                self.effets_du_clip(ids[0])
            else:
                self.encart.message(_("Sélectionnez d'abord un plan dans la timeline."))
        elif oid == "goodies":
            self.nouveau_goodie()
        elif oid in ("sous_titres", "musique", "voix", "fabrique", "exporter", "partager"):
            self.demande_outil.emit(oid)

    def _clip_selectionne(self):
        ids = self.timeline.selection()
        if not ids:
            c = self.projet.clip_a(self.timeline.position, "video")
            return c
        return self.projet.clip(ids[0])

    def vitesse(self):
        c = self._clip_selectionne()
        if not c:
            return
        d = DialogueVitesse(self, c)
        if d.exec() != d.Accepted:
            return
        self.projet.marquer()
        if d.ramp.isChecked():
            # lent, rapide, lent : trois morceaux
            a, b = c["src_debut"], c["src_fin"]
            tiers = (b - a) / 3
            c2 = self.projet.couper(c["id"], c["debut"] + tiers / c.get("vitesse", 1.0))
            if c2:
                c3 = self.projet.couper(c2["id"], c2["debut"] + tiers / c2.get("vitesse", 1.0))
                self.projet.vitesse(c["id"], 0.5)
                self.projet.vitesse(c2["id"], d.v.value() if d.v.value() > 1 else 3.0)
                if c3:
                    self.projet.vitesse(c3["id"], 0.5)
                    for x in (c, c3):
                        x["effets"] = [e for e in x.get("effets") or [] if e["id"] != "ralenti_fluide"] + ([{"id": "ralenti_fluide", "params": {}}] if d.fluide.isChecked() else [])
        else:
            self.projet.vitesse(c["id"], d.v.value())
            c["effets"] = [e for e in c.get("effets") or [] if e["id"] != "ralenti_fluide"]
            if d.fluide.isChecked() and d.v.value() < 1:
                c["effets"].append({"id": "ralenti_fluide", "params": {}})
        self.rafraichir()

    def _demande_menu(self, ident, quoi):
        if quoi == "suivi":
            c = self.projet.clip(ident)
            if c:
                self.recadrer_suivi(c)
        elif quoi in ("accrocher", "decrocher"):
            el = next((e for e in self.projet.titres + self.projet.goodies if e["id"] == ident), None)
            if el and quoi == "accrocher":
                self.accrocher(el)
            elif el:
                self.projet.marquer()
                el["suivi"] = None
                self.rafraichir()
        else:
            self.effets_du_clip(ident)

    def recadrer_suivi(self, clip):
        """Le plan suit une personne : on la désigne sur l'image, puis le suivi tourne en tâche de fond."""
        from .dialogues_suivi import DialogueSuivi
        m = self.projet.media(clip["media"])
        if not m or m.get("genre") != "video":
            self.encart.message(_("Le recadrage par suivi s'applique à une vidéo."))
            return
        d = DialogueSuivi(self, m, clip["src_debut"], recadrage=True, cadre=clip.get("suivi_cadre"))
        if d.exec() != d.Accepted:
            return
        boite, zoom, lissage = d.resultat()
        self.projet.marquer()
        t = Tache(lambda tache: suivi.recadrer(self.projet, clip, boite, zoom, lissage, progression=lambda f: tache.avancer(f),
                                               arret=lambda: tache.arret), _("Suivi"))
        self.taches.append(t)
        self.encart.suivre(t, _("Recadrage qui suit la personne dans « {n} »", n=m["nom"]))
        t.fini.connect(lambda r, e: (self.rafraichir(), self.apercu.rafraichir() if hasattr(self.apercu, "rafraichir") else None))
        t.start()

    def accrocher(self, element):
        """Texte ou Goodie qui suit une personne du plan présent à son début."""
        from .dialogues_suivi import DialogueSuivi
        clip = next((c for c in self.projet.clips_piste("video") if c["debut"] - 0.05 <= element["debut"] < fin_clip(c)), None)
        m = self.projet.media(clip["media"]) if clip else None
        if not m or m.get("genre") != "video":
            self.encart.message(_("Placez l'élément au-dessus d'un plan vidéo pour l'accrocher à une personne."))
            return
        t_src = clip["src_debut"] + (element["debut"] - clip["debut"]) * clip.get("vitesse", 1.0)
        d = DialogueSuivi(self, m, t_src, recadrage=False)
        if d.exec() != d.Accepted:
            return
        boite, _zoom, lissage = d.resultat()
        self.projet.marquer()
        decalage = (0.0, -0.5) if element in self.projet.titres else (0.0, -0.6)
        if element in self.projet.titres:
            element["style"] = "etiquette"
        t = Tache(lambda tache: suivi.accrocher(self.projet, element, m, boite, decalage, lissage, progression=lambda f: tache.avancer(f),
                                                arret=lambda: tache.arret), _("Suivi"))
        self.taches.append(t)
        self.encart.suivre(t, _("Accroché à la personne dans « {n} »", n=m["nom"]))
        t.fini.connect(lambda r, e: self.rafraichir())
        t.start()

    def cadrage(self):
        c = self._clip_selectionne()
        if not c:
            return
        m = QMenu(self)
        for lib, mode in ((_("Remplir (recadrer)"), "remplir"), (_("Contenir, bandes noires"), "contenir_noir"), (_("Contenir, fond flou"), "contenir_flou")):
            a = m.addAction(lib, lambda mode=mode: (self.projet.marquer(), c.__setitem__("ajustement", mode), self.rafraichir()))
            a.setCheckable(True)
            a.setChecked(c.get("ajustement", "remplir") == mode)
        m.addSeparator()
        m.addAction(_("Suivre la personne (recadrage automatique)…"), lambda: self.recadrer_suivi(c))
        m.exec(self.cursor().pos())

    def _ajouter_effet_selection(self, eid):
        c = self._clip_selectionne()
        if not c:
            return
        self.projet.marquer()
        if not any(e["id"] == eid for e in c.get("effets") or []):
            c.setdefault("effets", []).append({"id": eid, "params": {}})
        self.rafraichir()
        self.encart.message(_("Effet « {e} » posé sur « {n} » (visible à l'export et dans l'aperçu rendu).", e=eid, n=c.get("nom", "")))

    def effets_du_clip(self, cid):
        c = self.projet.clip(cid)
        if not c:
            return
        d = DialogueEffets(self, c, self.params, self.projet.medias)
        if d.exec() == d.Accepted:
            self.projet.marquer()
            c["effets"], c["transition"] = d.resultat()
            self.rafraichir()

    def nouveau_texte(self):
        d = DialogueTitre(self, None, self.timeline.position, max(10.0, self.projet.duree()), self._medias_visages())
        if d.exec() != d.Accepted:
            return
        t = d.resultat()
        if not t["texte"]:
            return
        self.projet.marquer()
        self.projet.ajouter_titre(**{k: v for k, v in t.items() if k != "id"})
        if t.get("suivi"):
            self._suivre(self.projet.titres[-1])
        self.rafraichir()

    def _medias_visages(self):
        out = []
        for m in self.projet.medias:
            inst = ((m.get("analyse") or {}).get("visages") or {}).get("instants") or []
            if inst:
                out.append((m, inst[0]["boite"]))
        return out

    def _suivre(self, titre):
        t = Tache(lambda tache: recettes.suivre_visage(self.projet, titre, self.params), _("Suivi"))
        self.taches.append(t)
        self.encart.suivre(t, _("Suivi de la personne pour « {t} »", t=titre["texte"]))
        t.fini.connect(lambda r, e: self.rafraichir())
        t.start()

    def nouveau_goodie(self):
        d = DialogueGoodie(self, None, self.timeline.position, max(10.0, self.projet.duree()), self.params)
        if d.exec() != d.Accepted:
            return
        self.projet.marquer()
        g = d.resultat()
        self.projet.ajouter_goodie(**{k: v for k, v in g.items() if k != "id"})
        self.rafraichir()

    def editer_element(self, ident):
        c = self.projet.clip(ident)
        if c:
            self.effets_du_clip(ident)
            return
        for t in self.projet.titres:
            if t["id"] == ident:
                d = DialogueTitre(self, t, medias_visages=self._medias_visages())
                if d.exec() == d.Accepted:
                    self.projet.marquer()
                    t.update(d.resultat())
                    if t.get("suivi") and not t["suivi"].get("positions"):
                        self._suivre(t)
                    self.rafraichir()
                return
        for g in self.projet.goodies:
            if g["id"] == ident:
                d = DialogueGoodie(self, g, params=self.params)
                if d.exec() == d.Accepted:
                    self.projet.marquer()
                    g.update(d.resultat())
                    self.rafraichir()
                return

    # ---------------------------------------------------------------- assistant
    def analyser(self):
        if not self.projet.medias:
            self.encart.message(_("Importez d'abord des rushes."))
            return
        self.params["assistant_niveau"] = self.proposition.niveau.currentData()
        self.params.enregistrer()
        indices = self.proposition.indices.text().strip()
        fmt = self.proposition.format.currentData() or None
        duree = self.proposition.duree.value() or None
        niveau = self.proposition.niveau.currentData()
        if niveau == "cloud":
            from . import ia, dialogues_ia
            if not dialogues_ia.verifier_cle(self, self.params):
                return
            if not ia.confirmer_envoi(self, indices + " " + " ".join(m["nom"] for m in self.projet.medias), ia.nom_moteur(self.params)):
                return

        def travail(tache):
            fiches = A.preparer(self.projet, self.params, progression=lambda f, t: tache.avancer(f * 0.7, t))
            tache.avancer(0.72, _("recette"))
            return A.proposer(self.projet, self.params, fiches, indices=indices, format_=fmt, duree_cible=duree, niveau_force=niveau,
                              rapporter=lambda t: tache.avancer(0.8, t))
        t = Tache(travail, _("Assistant"))
        self.taches.append(t)
        self.encart.suivre(t, _("Analyse des rushes et recette"))
        t.fini.connect(self._recette_prete)
        t.start()
        self.proposition.b_go.setEnabled(False)

    def _recette_prete(self, r, e):
        self.proposition.b_go.setEnabled(True)
        self.biblio.remplir(self.projet)
        if e:
            QMessageBox.warning(self, _("Assistant"), str(e))
            return
        self.proposition.montrer(r)
        self.volet.setCurrentIndex(0)
        from .journal import ecrire
        ecrire("assistant", f"recette {r.get('source')} : {r.get('resume')}")

    def appliquer_recette(self, paquet, remplacer):
        r, choix = paquet["recette"], paquet["choix"]
        if remplacer and self.projet.clips and QMessageBox.question(self, _("Appliquer la recette"), _("Remplacer la timeline actuelle par la proposition ? (Annuler possible)")) != QMessageBox.Yes:
            return
        recettes.appliquer(r, self.projet, self.params, choix, remplacer=remplacer)
        for t in self.projet.titres:
            if t.get("suivi") and len(t["suivi"].get("positions") or []) <= 2:
                self._suivre(t)
        self.apercu.changer_projet(self.projet)
        self.rafraichir()
        self.timeline.ajuster()
        self._apprendre(r, choix)

    def _apprendre(self, r, choix):
        """Memorise ce qui a ete garde ou refuse (partage entre postes) : les recettes sans IA s'ameliorent."""
        try:
            from . import apprentissage
            d = apprentissage.lire(self.params, "recettes.json") or {}
            for k, v in choix.items():
                cle = f"{r.get('type')}:{k.split(':')[0]}"
                e = d.setdefault(cle, {"garde": 0, "refuse": 0})
                e["garde" if v else "refuse"] += 1
            apprentissage.ecrire(self.params, "recettes.json", d)
        except Exception:
            pass

    def autre_idee(self, cle):
        if not self.proposition.recette:
            return
        t = Tache(lambda tache: A.autre_idee(self.projet, self.params, self.proposition.recette, cle), _("Autre idée"))
        self.taches.append(t)
        self.encart.suivre(t, _("Autre idée pour « {c} »", c=cle))
        t.fini.connect(lambda r, e: self.proposition.montrer(r) if r and not e else None)
        t.start()

    # ---------------------------------------------------------------- apercu rendu
    def apercu_rendu(self):
        from . import export
        import copy, tempfile
        debut = max(0.0, self.timeline.position - 5.0)
        fin = min(self.projet.duree(), debut + 10.0)
        if fin <= debut:
            return
        sortie = os.path.join(tempfile.gettempdir(), "philcut_apercu.mp4")

        def travail(tache):
            p = copy.deepcopy(self.projet)
            # on garde seulement la fenetre [debut, fin] : couper et decaler
            for piste in ("video", "audio"):
                for c in list(p.clips_piste(piste)):
                    if fin_clip(c) <= debut or c["debut"] >= fin:
                        p.d["clips"].remove(c)
                        continue
                    if c["debut"] < debut:
                        c["src_debut"] += (debut - c["debut"]) * c.get("vitesse", 1.0)
                        c["debut"] = debut
                    if fin_clip(c) > fin:
                        c["src_fin"] = c["src_debut"] + (fin - c["debut"]) * c.get("vitesse", 1.0)
                    c["debut"] -= debut
            for x in p.titres + p.goodies:
                x["debut"], x["fin"] = max(0.0, x["debut"] - debut), max(0.0, min(fin, x["fin"]) - debut)
            p.d["titres"] = [t for t in p.titres if t["fin"] > 0.05]
            p.d["goodies"] = [g for g in p.goodies if g["fin"] > 0.05]
            ex = export.Exportateur(p, sortie, "whatsapp", qualite="allegee", encodeur="libx264", params=self.params)
            try:
                return ex.lancer(progression=lambda f: tache.avancer(f), arret=lambda: tache.arret)
            finally:
                ex.nettoyer()
        t = Tache(travail, _("Aperçu rendu"))
        self.taches.append(t)
        self.encart.suivre(t, _("Aperçu rendu ({a:.0f} → {b:.0f} s)", a=debut, b=fin), (_("Ouvrir"), lambda: self.fenetre.ouvrir_externe(sortie)))
        t.start()
