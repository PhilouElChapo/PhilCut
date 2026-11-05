"""La page de montage d'un projet : barre d'outils en flux (personnalisable), bibliotheque a gauche, apercu au
centre, volet a droite (Proposition de l'assistant, Proprietes), timeline en bas, encart de progression."""
import os

from PySide6.QtCore import Qt, QTimer, Signal, QMimeData, QSize, QByteArray
from PySide6.QtGui import QPixmap, QIcon, QDrag, QAction, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem, QLabel, QPushButton, QToolButton,
                               QFrame, QProgressBar, QTabWidget, QScrollArea, QCheckBox, QComboBox, QLineEdit, QSpinBox, QMenu, QMessageBox,
                               QFileDialog, QSizePolicy, QFormLayout, QPlainTextEdit, QAbstractItemView, QInputDialog, QDialog)

from . import moteur, outils as O, recettes, assistant as A, suivi, theme
from .apercu import Apercu
from .icones import icone
from .langue import _
from .projet import fin_clip, duree_clip
from .taches import Tache, importer_media
from .timeline import Timeline, MIME_MEDIA
from .widgets import FluxLayout, _SurveilleTaille
from .timeline import _tc
from .session import dossier_systeme
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
        """action : (libelle, fonction) proposee a la fin. La tâche est aussi inscrite au Centre d'activité."""
        from . import activite
        activite.centre().suivre(tache, texte)
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

    def suivre_message(self, texte, action, duree=20000):
        """Message avec un bouton d'action (ex. « Voir l'aperçu rendu »)."""
        self.message(texte, duree)
        self.bouton.setText(action[0])
        self.bouton.show()
        try:
            self.bouton.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.bouton.clicked.connect(lambda: (self.hide(), action[1]()))

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
            m.addAction(icone("info"), _("Fiche vidéo"), lambda: self.fiche.emit(ident))
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
        lb = QLabel(_("<b>Médias du projet</b>"))
        lb.setToolTip(_("Vos rushes, musiques et images importés dans ce projet. Ils restent à leur place sur le disque. "
                        "Glissez-les sur la timeline, ou double-cliquez pour les ajouter à la fin."))
        hg.addWidget(lb)
        hg.addStretch(1)
        b_imp = QToolButton()
        b_imp.setIcon(icone("importer", theme.COULEURS["accent"]))
        b_imp.setToolTip(_("Importer des rushes, musiques ou images"))
        b_imp.clicked.connect(self.importer)
        hg.addWidget(b_imp)
        vg.addLayout(hg)
        aide = QLabel(_("Vos rushes, musiques et images. Glissez-les sur la timeline."))
        aide.setWordWrap(True)
        aide.setStyleSheet("color:%s;font-size:11px" % theme.COULEURS["texte2"])
        vg.addWidget(aide)
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
        from .inspecteur import Inspecteur
        self.inspecteur = Inspecteur(self)
        self.inspecteur.demande_effets.connect(self.effets_du_clip)
        self.inspecteur.demande_edition.connect(self.editer_element)
        self.volet.addTab(self.inspecteur, icone("liste_fichiers", theme.COULEURS["texte2"]), _("Inspecteur"))
        # bouton « agrandir » : le volet s'ouvre dans une fenêtre à part quand il devient trop petit
        self.b_agrandir = QToolButton()
        self.b_agrandir.setIcon(icone("plein_ecran", theme.COULEURS["texte2"]))
        self.b_agrandir.setAutoRaise(True)
        self.b_agrandir.setToolTip(_("Ouvrir ce volet dans une fenêtre plus grande"))
        self.b_agrandir.clicked.connect(self.agrandir_volet)
        self.volet.setCornerWidget(self.b_agrandir)
        self.split_h.addWidget(self.volet)
        # volet réduit : une colonne d'icônes nommées ; un clic rouvre le volet sur l'onglet choisi
        self.volet_icones = QFrame()
        self.volet_icones.setStyleSheet("QFrame{background:%s;border-left:1px solid %s}" % (theme.COULEURS["surface"], theme.COULEURS["bord_leger"]))
        vi = QVBoxLayout(self.volet_icones)
        vi.setContentsMargins(4, 8, 4, 8)
        vi.setSpacing(6)
        for i, (ic, lib, aide) in enumerate(((("assistant"), _("Proposition"), _("Ouvrir la proposition de l'assistant de montage")),
                                             ("liste_fichiers", _("Inspecteur"), _("Ouvrir l'Inspecteur : réglages du plan, de l'effet, du texte ou du Goodie sélectionné")))):
            b = QToolButton()
            b.setIcon(icone(ic, theme.COULEURS["texte"]))
            b.setIconSize(QSize(22, 22))
            b.setText(lib)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setToolTip(aide)
            b.setAutoRaise(True)
            b.setStyleSheet("QToolButton{font-size:10px}")
            b.clicked.connect(lambda _c=False, i=i: self._ouvrir_volet(i))
            vi.addWidget(b)
        vi.addStretch(1)
        self.volet_icones.setFixedWidth(78)
        self.volet_icones.hide()
        self.split_h.addWidget(self.volet_icones)
        self.split_h.setSizes([260, 900, 340, 0])
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
        self.timeline.zone_changee.connect(self._zone_changee)
        self.timeline.element_clique.connect(self._element_clique)
        self.timeline.element_change.connect(lambda cid: self.inspecteur.rafraichir(cid))
        self.split_v.addWidget(self.timeline)
        self.split_v.setSizes([620, 260])
        v.addWidget(self.split_v, 1)
        self.encart = Encart(self)
        v.addWidget(self.encart)
        self.apercu.position_changee.connect(lambda t: self.timeline.aller_a(t, emettre=False) if self.apercu.en_lecture else None)
        self.apercu.position_changee.connect(self._temps)
        self.apercu.taches_hote = self.taches
        self.apercu.calque_deplace.connect(self._calque_deplace)
        self.apercu.calque_clique.connect(lambda ident: (self._ouvrir_volet(1), self.inspecteur.montrer_selection([ident])))
        self.apercu.pas_image.connect(lambda n: self.aller_a(self.timeline.position + n / self.projet.cadence))
        self.apercu.viewport().setContextMenuPolicy(Qt.CustomContextMenu)
        self.apercu.viewport().customContextMenuRequested.connect(self._menu_apercu)
        self.apercu.etat_lecture.connect(self._etat_lecture)
        self.biblio.remplir(projet)
        self.rafraichir()

    # ---------------------------------------------------------------- barre d'outils en flux
    def _barre(self):
        w = QFrame()
        w.setObjectName("barre")
        w.setStyleSheet("QFrame#barre{background:%s;border-bottom:1px solid %s} QToolButton{font-size:11px}" % (theme.COULEURS["surface"], theme.COULEURS["bord_leger"]))
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 6, 0)
        h.setSpacing(0)
        zone_flux = QWidget()
        self.flux = FluxLayout(zone_flux, marge=6, espace=2)
        h.addWidget(zone_flux, 1)
        self.coin_droit = QHBoxLayout()           # le bouton Volet reste toujours à l'extrême droite
        self.coin_droit.setContentsMargins(0, 6, 0, 6)
        h.addLayout(self.coin_droit)
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
        for lay in (fl, self.coin_droit):
            while lay.count():
                it = lay.takeAt(0)
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
                fl.addWidget(self._bouton_historique("annuler", _("Annuler|action"), self.annuler,
                                                     _("Annuler (Ctrl+Z) — la flèche montre la liste des actions à annuler"), True))
            elif cle == "retablir":
                fl.addWidget(self._bouton_historique("retablir", _("Rétablir"), self.refaire,
                                                     _("Rétablir (Ctrl+Y) — la flèche montre la liste des actions à rétablir"), False))
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
                b = self._bouton("volet_droit", _("Volet"), self.basculer_volet,
                                 _("Volet de droite (Proposition de l'assistant, Propriétés du plan) : affiché → réduit à une colonne d'icônes → masqué. Touche F4."))
                self.coin_droit.addWidget(b)
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

    def _ouvrir_volet(self, onglet):
        self.params["volet"] = "complet"
        self.params.enregistrer()
        self.appliquer_volet()
        self.volet.setCurrentIndex(onglet)

    def appliquer_volet(self):
        mode = self.params.get("volet", "complet")
        self.volet.setVisible(mode == "complet")
        self.volet_icones.setVisible(mode == "icones")
        tailles = self.split_h.sizes()
        if len(tailles) == 4:
            if mode == "complet" and tailles[2] < 120:
                tailles[1] -= 340 - tailles[2]
                tailles[2] = 340
            if mode == "icones":
                tailles[1] += tailles[3] - 78
                tailles[3] = 78
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
        self.b_lire_rendu = QToolButton()
        self.b_lire_rendu.setText("▶✦")
        self.b_lire_rendu.setAutoRaise(True)
        self.b_lire_rendu.setStyleSheet("QToolButton{font-weight:700;color:%s}" % theme.COULEURS["accent"])
        self.b_lire_rendu.setToolTip(_("Lire avec les effets : PhilCut prépare les 15 secondes à partir du curseur (effets, transitions, "
                                       "incrustations, textes, son mélangé) puis les lit ici même."))
        self.b_lire_rendu.clicked.connect(self.lire_rendu)
        h.addWidget(self.b_lire_rendu)
        for ic, aide, f in (("image_suiv", _("Image suivante (→)"), lambda: self.aller_a(self.timeline.position + 1 / self.projet.cadence)), ("fin", _("Fin"), lambda: self.aller_a(self.projet.duree()))):
            h.addWidget(self._petit(ic, aide, f))
        b_boucle = self._petit("boucle", _("Lire en boucle"), lambda: None)
        b_boucle.setCheckable(True)
        b_boucle.toggled.connect(lambda on: setattr(self.apercu, "boucle", on))
        h.addWidget(b_boucle)
        # son de l'aperçu : tout couper, ou écouter une seule piste (la voix off seule, par exemple)
        self.b_son = QToolButton()
        self.b_son.setIcon(icone("volume", theme.COULEURS["texte"]))
        self.b_son.setIconSize(QSize(22, 22))
        self.b_son.setAutoRaise(True)
        self.b_son.setToolTip(_("Son de l'aperçu : clic pour couper / remettre ; flèche pour choisir les pistes écoutées (vidéo, musique, voix)"))
        self.b_son.setPopupMode(QToolButton.MenuButtonPopup)
        self.b_son.clicked.connect(lambda: self._son(None))
        ms = QMenu(self.b_son)
        self._actions_son = {}
        for piste, lib in (("video", _("Son des plans vidéo")), ("audio", _("Musique")), ("voix", _("Voix off"))):
            a = ms.addAction(lib)
            a.setCheckable(True)
            a.setChecked(True)
            a.toggled.connect(lambda on, p=piste: self.apercu.couper_son(p, not on))
            self._actions_son[piste] = a
        ms.addSeparator()
        ms.addAction(_("Ecouter seulement la voix off"), lambda: self._seulement("voix"))
        ms.addAction(_("Ecouter seulement la musique"), lambda: self._seulement("audio"))
        ms.addAction(_("Tout réentendre"), lambda: self._seulement(None))
        self.b_son.setMenu(ms)
        h.addWidget(self.b_son)
        self.b_fidele = QToolButton()
        self.b_fidele.setIcon(icone("effets", theme.COULEURS["texte"]))
        self.b_fidele.setIconSize(QSize(22, 22))
        self.b_fidele.setAutoRaise(True)
        self.b_fidele.setCheckable(True)
        self.b_fidele.setChecked(bool(self.params.get("apercu_fidele", True)))
        self.b_fidele.setToolTip(_("Image fidèle à l'arrêt : quand la lecture est en pause, l'image affichée est calculée avec les effets, "
                                   "transitions, textes et Goodies (moins d'une seconde). Décochez sur un poste lent."))
        self.b_fidele.toggled.connect(self.apercu.regler_fidele)
        h.addWidget(self.b_fidele)
        h.addWidget(self._petit("image", _("Enregistrer l'image affichée (PNG, pleine définition)"), self.extraire_image))
        h.addStretch(1)
        self.lbl_duree = QLabel("")
        self.lbl_duree.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
        h.addWidget(self.lbl_duree)
        b_rendu = QPushButton(_("Aperçu rendu"))
        b_rendu.setToolTip(_("Exporte en petit les 10 secondes autour du curseur, avec tous les effets, et l'ouvre."))
        b_rendu.clicked.connect(self.apercu_rendu)
        h.addWidget(b_rendu)
        return w

    def _son(self, coupe=None):
        self.apercu.couper_son(None, coupe)
        self.b_son.setIcon(icone("muet" if self.apercu.muet_general else "volume", theme.COULEURS["texte"]))

    def _seulement(self, piste):
        for p, a in self._actions_son.items():
            a.setChecked(piste is None or p == piste)
        if self.apercu.muet_general:
            self._son(False)

    def _menu_apercu(self, pos):
        m = QMenu(self)
        m.addAction(icone("image", theme.COULEURS["texte"]), _("Enregistrer cette image (PNG, pleine définition)…"), self.extraire_image)
        m.addAction(_("Lecture / pause"), self.apercu.basculer)
        m.addAction(_("Aperçu rendu (avec les effets)"), self.apercu_rendu)
        m.exec(self.apercu.viewport().mapToGlobal(pos))

    def extraire_image(self):
        """Enregistre l'image sous le curseur, depuis le rush d'origine (pleine définition)."""
        t = self.timeline.position
        c = self.projet.clip_a(t, "video")
        m = self.projet.media(c["media"]) if c else None
        if not m:
            QMessageBox.information(self, _("Image"), _("Placez le curseur sur un plan vidéo."))
            return
        src = c["src_debut"] + (t - c["debut"]) * c.get("vitesse", 1.0)
        dossier = self.params.get("dossier_images") or dossier_systeme("images")
        nom = f"{os.path.splitext(m['nom'])[0]}_{src:.2f}s.png".replace(".", "_", 1)
        chemin, _f = QFileDialog.getSaveFileName(self, _("Enregistrer l'image"), os.path.join(dossier, nom), "PNG (*.png);;JPEG (*.jpg)")
        if not chemin:
            return
        self.params["dossier_images"] = os.path.dirname(chemin)
        self.params.enregistrer()
        largeur = int((m.get("fiche") or {}).get("largeur") or 3840)
        try:
            from . import moteur
            png = moteur.image(m["chemin"], src, largeur)
            if chemin.lower().endswith((".jpg", ".jpeg")):
                pm = QPixmap()
                pm.loadFromData(png)
                pm.save(chemin, "JPG", 95)
            else:
                with open(chemin, "wb") as f:
                    f.write(png)
            self.encart.message(_("Image enregistrée : {f}", f=chemin))
        except Exception as e:      # noqa: BLE001
            QMessageBox.warning(self, _("Image"), str(e))

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

    def _bouton_historique(self, ic, texte, f, aide, annuler):
        """Annuler / Rétablir avec la liste des actions : on voit ce qui sera annulé ; un clic annule jusque-là."""
        b = self._bouton(ic, texte, f, aide)
        b.setPopupMode(QToolButton.MenuButtonPopup)
        m = QMenu(b)

        def remplir():
            m.clear()
            annul, retab = self.projet.historique()
            liste = annul if annuler else retab
            if not liste:
                m.addAction(_("Rien à annuler") if annuler else _("Rien à rétablir")).setEnabled(False)
                return
            for i, lib in enumerate(liste[:20]):
                m.addAction(f"{i + 1}. {lib}", lambda n=i + 1: self._plusieurs(annuler, n))
        m.aboutToShow.connect(remplir)
        b.setMenu(m)
        return b

    def _plusieurs(self, annuler, n):
        for _i in range(n):
            if not (self.projet.annuler() if annuler else self.projet.refaire()):
                break
        self.rafraichir()
        self.encart.message(_("{n} action(s) annulée(s).", n=n) if annuler else _("{n} action(s) rétablie(s).", n=n), 3000)

    def annuler(self):
        a = (self.projet.historique()[0] or [""])[0]
        if self.projet.annuler():
            self.rafraichir()
            self.encart.message(_("Annulé : {a}", a=a), 3000)

    def refaire(self):
        a = (self.projet.historique()[1] or [""])[0]
        if self.projet.refaire():
            self.rafraichir()
            self.encart.message(_("Rétabli : {a}", a=a), 3000)

    def _selection(self, ids):
        self.inspecteur.montrer_selection(ids)

    def _calque_deplace(self, ident, x, y):
        """Un texte ou un Goodie déplacé à la souris dans l'image."""
        for e in self.projet.titres + self.projet.goodies:
            if e["id"] == ident:
                self.projet.marquer()
                e["x"], e["y"] = round(x, 4), round(y, 4)
                self._modifie()
                if self.inspecteur._cible and self.inspecteur._cible[1] == ident:
                    self.inspecteur.montrer_selection([ident])
                return

    def _element_clique(self, clip_id, genre, i):
        """Clic sur une étiquette d'effet ou une transition dans la timeline : l'Inspecteur s'ouvre dessus."""
        self._ouvrir_volet(1)
        if genre == "calque":
            self.inspecteur.montrer_selection([clip_id])
        else:
            self.inspecteur.montrer_element(clip_id, genre, i)

    def agrandir_volet(self):
        """Le volet de droite dans une fenêtre à part, redimensionnable ; il revient à sa place à la fermeture."""
        w = self.volet.currentWidget()
        if w is None:
            return
        i = self.volet.currentIndex()
        titre, ic = self.volet.tabText(i), self.volet.tabIcon(i)
        d = QDialog(self)
        d.setWindowTitle(titre)
        d.setModal(False)
        d.resize(760, 640)
        lay = QVBoxLayout(d)
        lay.setContentsMargins(6, 6, 6, 6)
        self.volet.removeTab(i)
        lay.addWidget(w)

        def retour(*_a):
            w.setParent(None)
            self.volet.insertTab(i, w, ic, titre)
            self.volet.setCurrentIndex(i)
        d.finished.connect(retour)
        d.show()

    # ---------------------------------------------------------------- medias
    def importer(self, chemins=None):
        if not chemins:
            filtres = _("Vidéos, sons, images") + " (*.mp4 *.mov *.mkv *.m4v *.webm *.avi *.mts *.m2ts *.3gp *.mp3 *.wav *.m4a *.aac *.flac *.ogg *.jpg *.jpeg *.png *.webp *.heic);;" + _("Tous") + " (*)"
            chemins, _f = QFileDialog.getOpenFileNames(self, _("Importer des rushes, musiques ou images"),
                                                       self.params.get("dernier_dossier") or dossier_systeme("videos"), filtres)
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
            depot = getattr(self, "_piste_depot", None)
            self._piste_depot = None
            if depot:                     # fichier déposé ou posé sur une piste précise (musique, voix off…)
                c = self.ajouter_a_la_timeline(m["id"], depot[0], depot[1])
                if c and len(depot) > 2:          # réglages du plan posé (retouches de voix…)
                    c.update(depot[2])
                    self.rafraichir()
            elif not self.projet.clips and m["genre"] in ("video", "image") and self.params.get("ajout_auto", True):
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
        self._zoom_auto()
        return c

    def _zoom_auto(self):
        """Un montage court dans une grande timeline : on zoome pour qu'il remplisse la largeur (images lisibles)."""
        tl = self.timeline
        largeur = tl.viewport().width()
        if largeur > 200 and 0 < self.projet.duree() * tl.pps < 0.45 * largeur:
            tl.ajuster()

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
            self.stabiliser()
        elif oid == "assistant":
            self._ouvrir_volet(0)
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
            z = self.timeline.zone_valide()
            if z:                                  # partie choisie (I / O) : on isole ce morceau du plan, puis ses effets
                c = self.morceau_de_partie(*z)
                if c:
                    self.effets_du_clip(c["id"])
                return
            c = self._clip_selectionne()          # le plan cliqué, sinon celui sous le curseur
            if c:
                self.effets_du_clip(c["id"])
            else:
                self.encart.message(_("Cliquez d'abord sur un plan dans la timeline, puis sur Effets."))
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
        if quoi == "corriger":
            self.corriger_suivi(ident)
        elif quoi == "suivi":
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
        elif quoi == "image":
            self.extraire_image()
        elif quoi in ("partie_supprimer", "partie_garder"):
            self.partie(quoi == "partie_garder")
        elif quoi == "effets_partie":
            z = self.timeline.zone_valide()
            c = self.morceau_de_partie(*z) if z else None
            if c:
                self.effets_du_clip(c["id"])
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

    def caler_rythme(self, forts=False):
        """Chaque coupe vidéo tombe sur un temps (ou un début de mesure) de la musique de la piste audio."""
        from . import rythme
        musique = next(iter(self.projet.clips_piste("audio")), None)
        if not musique or len(self.projet.clips_piste("video")) < 2:
            self.encart.message(_("Il faut au moins deux plans vidéo et une musique sur la piste audio."))
            return
        m = self.projet.media(musique["media"])

        def travail(tache):
            tache.avancer(0.1, _("écoute de la musique"))
            if not m.get("rythme"):
                m["rythme"] = rythme.analyser(m["chemin"])
            return m["rythme"]

        def fin(analyse, err):
            if err or not analyse or not analyse.get("temps"):
                self.encart.message(_("Pas de rythme net dans cette musique : coupes inchangées."))
                return
            self.projet.marquer()
            n = rythme.caler(self.projet, musique, analyse, forts)
            self.rafraichir()
            self.encart.message(_("{n} coupe(s) calée(s) sur la musique ({b} BPM).", n=n, b=int(round(analyse.get("bpm") or 0))))
        t = Tache(travail, _("Rythme"))
        self.taches.append(t)
        self.encart.suivre(t, _("Coupes calées sur « {n} »", n=m["nom"]))
        t.fini.connect(fin)
        t.start()

    def corriger_suivi(self, ident):
        """Le suivi a décroché (personne cachée, sortie du cadre) : on la redésigne à la tête de lecture, le reste est refait."""
        from .dialogues_suivi import DialogueSuivi
        t = self.timeline.position
        clip = self.projet.clip(ident)
        element = None if clip else next((e for e in self.projet.titres + self.projet.goodies if e["id"] == ident), None)
        if clip:
            if not (clip["debut"] <= t < fin_clip(clip)):
                self.encart.message(_("Placez la tête de lecture sur ce plan, au moment où le suivi se trompe."))
                return
            m = self.projet.media(clip["media"])
        elif element and element.get("suivi"):
            if not (element["debut"] <= t < element["fin"]):
                self.encart.message(_("Placez la tête de lecture pendant l'élément, au moment où le suivi se trompe."))
                return
            m = self.projet.media(element["suivi"].get("media"))
            clip = next((c for c in self.projet.clips_piste("video") if c["media"] == m["id"] and c["debut"] <= t < fin_clip(c)), None) if m else None
        else:
            return
        if not m or not clip:
            return
        t_src = clip["src_debut"] + (t - clip["debut"]) * clip.get("vitesse", 1.0)
        d = DialogueSuivi(self, m, t_src, recadrage=False)
        d.setWindowTitle(_("Corriger le suivi à {t}", t=moteur.duree_texte(t)))
        if d.exec() != d.Accepted:
            return
        boite, _z, _l = d.resultat()
        self.projet.marquer()
        if element is None:
            fonction = lambda tache: suivi.corriger_cadre(self.projet, clip, t, boite, progression=lambda f: tache.avancer(f), arret=lambda: tache.arret)
        else:
            fonction = lambda tache: suivi.corriger_accroche(self.projet, element, t, boite, progression=lambda f: tache.avancer(f), arret=lambda: tache.arret)
        tache = Tache(fonction, _("Suivi"))
        self.taches.append(tache)
        self.encart.suivre(tache, _("Correction du suivi à partir de {t}", t=moteur.duree_texte(t)))
        tache.fini.connect(lambda r, e: self.rafraichir())
        tache.start()

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

    def _zone_changee(self):
        z = self.timeline.zone_valide()
        a, b = self.timeline.zone
        if z:
            self.encart.message(_("Partie en jaune : {a} → {b} ({d:.1f} s). Clic droit dessus : effets sur cette partie, la supprimer "
                                  "ou ne garder qu'elle.", a=_tc(z[0]), b=_tc(z[1]), d=z[1] - z[0]), 12000)
        elif a is not None or b is not None:
            self.encart.message(_("Début de la partie marqué. Clic droit à la fin voulue › Partie de la vidéo › « La partie finit ici ».") if a is not None else
                                _("Fin de la partie marquée. Clic droit au début voulu › Partie de la vidéo › « La partie commence ici »."), 8000)

    def morceau_de_partie(self, a, b):
        """Coupe le plan vidéo aux bornes de la partie choisie (I / O) et renvoie le morceau du milieu : un effet posé
        dessus ne touche que ces secondes-là."""
        c = self.projet.clip_a((a + b) / 2, "video")
        if not c:
            self.encart.message(_("Pas de plan vidéo dans la partie choisie."))
            return None
        self.projet.marquer()
        for t in (a, b):
            for x in list(self.projet.clips_piste("video")):
                if x["debut"] + 0.04 < t < fin_clip(x) - 0.04:
                    self.projet.couper(x["id"], t)
        m = self.projet.clip_a((a + b) / 2, "video")
        self.timeline.zone = [None, None]
        self.rafraichir()
        self.timeline.selectionner(m["id"])
        self.encart.message(_("Le plan est coupé à {a} et {b} : les effets ne s'appliqueront qu'à ce morceau.", a=_tc(a), b=_tc(b)), 8000)
        return m

    def partie(self, garder):
        z = self.timeline.zone_valide()
        if not z:
            QMessageBox.information(self, _("Partie de la vidéo"), _(
                "Pour choisir une partie de la vidéo, le plus simple : glissez avec la souris sur la règle des temps (au-dessus des pistes) "
                "du début à la fin voulus. La partie apparaît en jaune.\n\nOu bien : clic droit dans la timeline à l'endroit voulu › "
                "Partie de la vidéo › « La partie commence ici », puis de même « La partie finit ici ».\n\nEnsuite, clic droit sur la partie : "
                "effets sur cette partie, la supprimer, ou ne garder qu'elle."))
            return
        self.projet.marquer()
        if self.projet.partie(z[0], z[1], garder):
            self.timeline.zone = [None, None]
            self.rafraichir()
            self.timeline.aller_a(0.0 if garder else z[0])
            self.encart.message(_("Seule la partie sélectionnée est gardée (Annuler pour revenir).") if garder else
                                _("Partie supprimée, la suite s'est recollée (Annuler pour revenir)."), 6000)
        else:
            self.projet.annuler()

    def stabiliser(self):
        c = self._clip_selectionne()
        if not c:
            QMessageBox.information(self, _("Stabiliser"), _("Stabiliser enlève les tremblements d'un plan filmé à la main, en marchant ou "
                                                            "depuis un avion.\n\nCliquez d'abord sur un plan dans la timeline, puis sur Stabiliser."))
            return
        deja = any(e["id"] == "stabiliser" for e in c.get("effets") or [])
        m = QMessageBox(self)
        m.setWindowTitle(_("Stabiliser « {n} »", n=c.get("nom", "")))
        m.setText(_("<b>Stabiliser</b> enlève les tremblements d'un plan filmé à la main (marche, voiture, avion).<br><br>"
                    "PhilCut recadre très légèrement chaque image pour compenser les secousses : le bord de l'image est un peu rogné. "
                    "Le résultat se voit avec « Aperçu rendu » (sous la vidéo) et à l'export, pas pendant la lecture normale.<br><br>"
                    "Pour un horizon penché, utilisez l'effet « Redresser l'horizon » (Effets)."))
        b_ok = m.addButton(_("Retirer la stabilisation") if deja else _("Stabiliser ce plan"), QMessageBox.AcceptRole)
        m.addButton(_("Annuler"), QMessageBox.RejectRole)
        m.exec()
        if m.clickedButton() is not b_ok:
            return
        self.projet.marquer()
        if deja:
            c["effets"] = [e for e in c["effets"] if e["id"] != "stabiliser"]
            self.rafraichir()
            self.encart.message(_("Stabilisation retirée."))
        else:
            c.setdefault("effets", []).append({"id": "stabiliser", "params": {}})
            self.rafraichir()
            self.encart.message(_("Plan stabilisé : regardez le résultat avec « Aperçu rendu »."), 6000)

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
            self.timeline.selectionner(cid)
            self.inspecteur.montrer_clip(cid)
            self._ouvrir_volet(1)
            n = len(c["effets"]) + (1 if c.get("transition") else 0)
            if n:
                def voir():
                    self.timeline.aller_a(c["debut"] + 5.0 - (1.0 if c.get("transition") else 0.0))
                    self.apercu_rendu()
                self.encart.suivre_message(_("{n} effet(s) sur « {p} » : étiquettes sur le plan (clic pour régler), résultat visible dans l'aperçu "
                                             "à l'arrêt ; en mouvement : « Aperçu rendu ».", n=n, p=c.get("nom", "")),
                                           (_("Voir en mouvement"), voir))

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
            videos = [m for m in self.projet.medias if m.get("genre") == "video"]
            if not ia.confirmer_cout(self, self.params, 3000 + 900 * len(self.projet.medias), min(12, 4 * len(videos))):
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
        if (self.proposition.recette.get("source") or "").startswith("cloud"):
            from . import ia
            if not ia.confirmer_cout(self, self.params, 4500, 0, _("Autre idée pour « {c} »", c=cle)):
                return
        t = Tache(lambda tache: A.autre_idee(self.projet, self.params, self.proposition.recette, cle), _("Autre idée"))
        self.taches.append(t)
        self.encart.suivre(t, _("Autre idée pour « {c} »", c=cle))
        t.fini.connect(lambda r, e: self.proposition.montrer(r) if r and not e else None)
        t.start()

    # ---------------------------------------------------------------- apercu rendu
    def lire_rendu(self, duree_max=15.0):
        """Lecture avec effets : le passage à venir est rendu en arrière-plan (720p) puis joué dans l'aperçu."""
        from . import export
        import copy, tempfile
        debut = self.timeline.position
        fin = min(self.projet.duree(), debut + duree_max)
        if fin - debut < 0.2:
            self.encart.message(_("Placez le curseur avant la fin du montage."))
            return
        self._n_segment = getattr(self, "_n_segment", 0) + 1
        sortie = os.path.join(tempfile.gettempdir(), f"philcut_lecture_{os.getpid()}_{self._n_segment % 4}.mp4")
        projet = copy.deepcopy(self.projet)
        st = list(self.projet.d.get("sous_titres") or [])

        def travail(tache):
            p = export.extrait(projet, debut, fin)
            ex = export.Exportateur(p, sortie, "whatsapp", qualite="allegee", encodeur="libx264", params=self.params)
            try:
                return ex.lancer(progression=lambda f: tache.avancer(f), arret=lambda: tache.arret,
                                 sous_titres=[(a - debut, b - debut) + tuple(x[2:]) for x in st for a, b in [(x[0], x[1])] if b > debut and a < fin])
            finally:
                ex.nettoyer()
        t = Tache(travail, _("Lecture avec effets"))
        self.taches.append(t)
        self.encart.suivre(t, _("Préparation de la lecture avec effets ({a} → {b})", a=_tc(debut), b=_tc(fin)))

        def fini(r, e):
            if e or not r:
                return
            self.apercu.jouer_segment(debut, fin, r)
        t.fini.connect(fini)
        t.start()

    def apercu_rendu(self):
        from . import export
        import copy, tempfile
        debut = max(0.0, self.timeline.position - 5.0)
        fin = min(self.projet.duree(), debut + 10.0)
        if fin <= debut:
            return
        sortie = os.path.join(tempfile.gettempdir(), "philcut_apercu.mp4")

        def travail(tache):
            p = export.extrait(self.projet, debut, fin)
            ex = export.Exportateur(p, sortie, "whatsapp", qualite="allegee", encodeur="libx264", params=self.params)
            try:
                return ex.lancer(progression=lambda f: tache.avancer(f), arret=lambda: tache.arret)
            finally:
                ex.nettoyer()
        t = Tache(travail, _("Aperçu rendu"))
        self.taches.append(t)
        self.encart.suivre(t, _("Aperçu rendu ({a:.0f} → {b:.0f} s)", a=debut, b=fin), (_("Ouvrir"), lambda: self.fenetre.ouvrir_externe(sortie)))
        t.start()
