"""La page de montage d'un projet : barre d'outils en flux (personnalisable), bibliotheque a gauche, apercu au
centre, volet a droite (Proposition de l'assistant, Proprietes), timeline en bas, encart de progression."""
import os, time

from PySide6.QtCore import Qt, QTimer, Signal, QMimeData, QSize, QByteArray
from PySide6.QtGui import QPixmap, QIcon, QDrag, QAction, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem, QLabel, QPushButton, QToolButton,
                               QFrame, QProgressBar, QTabWidget, QScrollArea, QCheckBox, QComboBox, QLineEdit, QSpinBox, QMenu, QMessageBox,
                               QFileDialog, QSizePolicy, QFormLayout, QPlainTextEdit, QAbstractItemView, QInputDialog, QDialog, QGroupBox)

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

    analyser = Signal(object)              # liste d'ids à analyser avec l'IA locale (vide = tous)
    etiquette = Signal(str, str)           # media_id, texte lu : poser une étiquette

    def filtrer(self, texte):
        self._filtre = texte or ""
        if self.projet:
            self.remplir(self.projet)

    def remplir(self, projet):
        from . import analyse_locale as AL
        self.projet = projet
        self.clear()
        for m in projet.medias:
            if getattr(self, "_filtre", "") and not AL.correspond(m, self._filtre):
                continue
            a = m.get("ia_locale") or {}
            it = QListWidgetItem(m["nom"] + (f"\n{a['nom']}" if a.get("nom") else ""))
            it.setData(Qt.UserRole, m["id"])
            px = QPixmap(m["vignettes"]) if m.get("vignettes") and os.path.exists(m["vignettes"]) else QPixmap()
            if not px.isNull():
                it.setIcon(QIcon(px.copy(0, 0, min(px.width(), int(px.height() * 16 / 9) if px.height() else px.width()), px.height())))
            else:
                it.setIcon(icone({"audio": "musique", "image": "image"}.get(m.get("genre"), "camera"), theme.COULEURS["texte2"], 64))
            res = a.get("resume") or (m.get("analyse") or {}).get("resume") or moteur.resume_fiche(m.get("fiche"))
            if a.get("textes"):
                res += "\n" + _("Textes lus : {t}", t=", ".join(a["textes"]))
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
            m.addSeparator()
            ids = [x.data(Qt.UserRole) for x in self.selectedItems()] or [ident]
            m.addAction(icone("ia"), _("Analyser avec l'IA locale ({n})", n=len(ids)), lambda: self.analyser.emit(ids))
            med = self.projet.media(ident) if self.projet else None
            for t in ((med or {}).get("ia_locale") or {}).get("textes") or []:
                m.addAction(_("Etiquette « {t} » (texte lu)", t=t), lambda t=t: self.etiquette.emit(ident, t))
            m.addSeparator()
            m.addAction(icone("supprimer"), _("Retirer du projet"), lambda: self.retirer.emit(ident))
        m.addAction(icone("ia"), _("Analyser tous les rushes avec l'IA locale"), lambda: self.analyser.emit([]))
        m.exec(self.mapToGlobal(pos))


def MARGE_G_TL():
    from .timeline import MARGE_G
    return MARGE_G


def E_defauts(eid):
    from . import effets as E
    return E.defauts(eid)


class VoletProposition(QWidget):
    """Le volet de l'assistant : analyser, proposer, cocher, autre idee, appliquer."""
    analyser = Signal()
    appliquer = Signal(dict, bool)      # recette filtree, remplacer
    autre_idee = Signal(str)
    commande = Signal(str)              # « Dites-le en clair »

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.params = params
        self.recette = None
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        gd = QGroupBox(_("Dites-le en clair"))
        vd = QVBoxLayout(gd)
        self.phrase = QLineEdit()
        self.phrase.setPlaceholderText(_("« mets une musique calme et coupe-la à la fin »"))
        self.phrase.setToolTip(_("Une phrase devient des actions de montage, montrées avant d'être faites (annulables)."))
        self.phrase.returnPressed.connect(lambda: self.commande.emit(self.phrase.text()))
        vd.addWidget(self.phrase)
        bd = QPushButton(icone("assistant", theme.COULEURS["texte2"]), _("Faire ce que je demande…"))
        bd.setStyleSheet("text-align:left;padding:4px 8px")
        bd.clicked.connect(lambda: self.commande.emit(self.phrase.text()))
        hd = QHBoxLayout()
        hd.addWidget(bd)
        hd.addStretch(1)
        vd.addLayout(hd)
        v.addWidget(gd)
        f = QFormLayout()
        self.indices = QLineEdit()
        self.indices.setPlaceholderText(_("Indications : « balade en montagne », « pour Insta »…"))
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
            ligne("musique", _("Musique"), _("ambiance {a}, ≈ {b} BPM", a=mu.get("ambiance", ""), b=mu.get("bpm", "?")) + ("" if mu.get("media") else _(" — prise dans vos dossiers de musiques, sinon une musique libre est téléchargée")), mu.get("pourquoi", ""))
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
        b_rep = QToolButton()
        b_rep.setText("◂")
        b_rep.setToolTip(_("Replier la colonne des médias (elle devient une colonne d'icônes)"))
        b_rep.setAutoRaise(True)
        b_rep.clicked.connect(lambda: self.replier_gauche(True))
        hg.addWidget(b_rep)
        vg.addLayout(hg)
        aide = QLabel(_("Vos rushes, musiques et images. Glissez-les sur la timeline."))
        aide.setWordWrap(True)
        aide.setStyleSheet("color:%s;font-size:11px" % theme.COULEURS["texte2"])
        vg.addWidget(aide)
        self.recherche_medias = QLineEdit()
        self.recherche_medias.setPlaceholderText(_("Rechercher : nom, lieu, objet, texte lu…"))
        self.recherche_medias.setClearButtonEnabled(True)
        self.recherche_medias.setToolTip(_("Cherche dans les noms et dans ce que l'IA locale a vu dans chaque rush (clic droit › Analyser)."))
        vg.addWidget(self.recherche_medias)
        self.biblio = Bibliotheque()
        self.recherche_medias.textChanged.connect(self.biblio.filtrer)
        self.biblio.analyser.connect(self.analyser_rushes)
        self.biblio.etiquette.connect(self._etiquette_texte_lu)
        self.biblio.ajouter.connect(lambda i: self.ajouter_a_la_timeline(i))
        self.biblio.fiche.connect(self.montrer_fiche)
        self.biblio.retirer.connect(self.retirer_media)
        self.biblio.importer.connect(self.importer)
        vg.addWidget(self.biblio, 1)
        # colonne repliée : deux icônes nommées
        self.gauche_icones = QFrame()
        self.gauche_icones.setStyleSheet("QFrame{background:%s;border-right:1px solid %s}" % (theme.COULEURS["surface"], theme.COULEURS["bord_leger"]))
        vi_g = QVBoxLayout(self.gauche_icones)
        vi_g.setContentsMargins(4, 8, 4, 8)
        vi_g.setSpacing(6)
        for ic, lib, aide, f in (("dossier", _("Médias"), _("Rouvrir la colonne des médias du projet"), lambda: self.replier_gauche(False)),
                                 ("importer", _("Importer"), _("Importer des rushes, musiques ou images"), self.importer)):
            bi = QToolButton()
            bi.setIcon(icone(ic, theme.COULEURS["texte"]))
            bi.setIconSize(QSize(22, 22))
            bi.setText(lib)
            bi.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            bi.setToolTip(aide)
            bi.setAutoRaise(True)
            bi.setStyleSheet("QToolButton{font-size:10px}")
            bi.clicked.connect(f)
            vi_g.addWidget(bi)
        vi_g.addStretch(1)
        self.gauche_complet = g
        conteneur = QWidget()
        hc = QHBoxLayout(conteneur)
        hc.setContentsMargins(0, 0, 0, 0)
        hc.setSpacing(0)
        hc.addWidget(g)
        hc.addWidget(self.gauche_icones)
        self.gauche = conteneur
        self.split_h.addWidget(conteneur)
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
        self.volet.setUsesScrollButtons(False)          # trois onglets toujours visibles : les noms s'abrègent si le volet est étroit
        self.volet.setElideMode(Qt.ElideRight)
        self.volet.tabBar().setStyleSheet("QTabBar::tab{padding:7px 7px}QTabBar::tab:selected{font-weight:normal}")   # noms entiers même étroit
        self.proposition = VoletProposition(params)
        self.proposition.analyser.connect(self.analyser)
        self.proposition.appliquer.connect(self.appliquer_recette)
        self.proposition.autre_idee.connect(self.autre_idee)
        self.proposition.commande.connect(self.dites_le)
        self.volet.addTab(self.proposition, icone("assistant", theme.COULEURS["texte2"]), _("Proposition"))
        from .inspecteur import Inspecteur
        self.inspecteur = Inspecteur(self)
        self.inspecteur.demande_effets.connect(self.effets_du_clip)
        self.inspecteur.demande_edition.connect(self.editer_element)
        self.volet.addTab(self.inspecteur, icone("liste_fichiers", theme.COULEURS["texte2"]), _("Inspecteur"))
        from .catalogue_effets import CatalogueEffets
        self.catalogue = CatalogueEffets(self)
        self.volet.addTab(self.catalogue, icone("effets", theme.COULEURS["texte2"]), _("Effets"))
        self.volet.setTabToolTip(2, _("Catalogue des effets et transitions : vignettes animées, à glisser sur la timeline"))
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
                                             ("liste_fichiers", _("Inspecteur"), _("Ouvrir l'Inspecteur : réglages du plan, de l'effet, du texte ou du Goodie sélectionné")),
                                             ("effets", _("Effets"), _("Catalogue des effets et transitions : vignettes animées, à glisser sur la timeline")))):
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
        self.timeline.effet_depose.connect(self.poser_effet)
        self.timeline.message.connect(lambda t: self.encart.message(t))
        self.timeline.modifie.connect(self._modifie)
        self.timeline.proprietes.connect(self.editer_element)
        self.timeline.media_depose.connect(self._depose)
        self.timeline.selection_changee.connect(self._selection)
        self.timeline.demande_menu.connect(self._demande_menu)
        self.timeline.zone_changee.connect(self._zone_changee)
        self.timeline.balayage.connect(lambda on: self.apercu.regler_balayage(on))
        # préparation automatique des passages avec effets (0.3.1)
        from .preparation import Preparation
        self.preparation = Preparation(self)
        self.apercu.fournisseur = self.preparation.tranche_prete
        self.timeline.etats_preparation = self.preparation.etats
        self.preparation.change.connect(self._preparation_change)
        self.timeline.element_clique.connect(self._element_clique)
        self.timeline.element_change.connect(lambda cid: self.inspecteur.rafraichir(cid))
        # petite barre au-dessus de la timeline : aller au début / à la fin, zoom, tout voir (tout à la souris)
        bas = QWidget()
        vb = QVBoxLayout(bas)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)
        barre_tl = QHBoxLayout()
        barre_tl.setContentsMargins(6, 2, 6, 2)
        barre_tl.setSpacing(2)
        for texte, aide, f in (("⇤", _("Aller au début du montage"), lambda: self.timeline.aller_a(0.0)),
                               ("⇥", _("Aller à la fin du montage (et la montrer)"), self._aller_fin),
                               ("−", _("Réduire : voir plus de durée à la fois"), lambda: self.timeline.zoomer(1 / 1.6)),
                               ("+", _("Agrandir : voir plus de détail"), lambda: self.timeline.zoomer(1.6)),
                               (_("Tout voir"), _("Tout le montage dans la largeur"), self.timeline.ajuster),
                               ("↕", _("Images de la timeline plus grandes / plus petites (clic droit pour réduire)"), lambda: self.timeline.hauteur_images(1.3))):
            b = QToolButton()
            b.setText(texte)
            b.setToolTip(aide)
            b.setAutoRaise(True)
            b.setMinimumWidth(26)
            b.clicked.connect(f)
            if texte == "↕":
                b.setContextMenuPolicy(Qt.CustomContextMenu)
                b.customContextMenuRequested.connect(lambda _p: self.timeline.hauteur_images(1 / 1.3))
            barre_tl.addWidget(b)
        self.info_tl = QLabel("")
        self.info_tl.setStyleSheet(f"color:{theme.COULEURS['texte2']}")
        barre_tl.addSpacing(10)
        barre_tl.addWidget(self.info_tl, 1)
        vb.addLayout(barre_tl)
        vb.addWidget(self.timeline, 1)
        self.split_v.addWidget(bas)
        self.split_v.setSizes([620, 260])
        # la part lecteur / timeline et les largeurs des volets sont mémorisées sur ce poste
        tailles = self.params.get("tailles_vue") or {}
        if tailles.get("v") and len(tailles["v"]) == 2:
            self.split_v.setSizes(tailles["v"])
        if tailles.get("h") and len(tailles["h"]) == 4:
            self.split_h.setSizes(tailles["h"])
        self._appliquer_gauche()
        self.split_v.splitterMoved.connect(lambda *_a: self._memoriser_tailles())
        self.split_h.splitterMoved.connect(lambda *_a: self._memoriser_tailles())
        v.addWidget(self.split_v, 1)
        self.encart = Encart(self)
        v.addWidget(self.encart)
        self.apercu.position_changee.connect(lambda t: self.timeline.aller_a(t, emettre=False) if self.apercu.en_lecture else None)
        self.apercu.position_changee.connect(self._temps)
        self.apercu.taches_hote = self.taches
        self.apercu.calque_deplace.connect(self._calque_deplace)
        self.apercu.calque_taille.connect(self._calque_taille)
        self.apercu.calque_cadre.connect(self._calque_cadre)
        self.apercu.zone_tracee.connect(self._zone_tracee)
        self.apercu.segment_fini.connect(self._segment_fini)
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

    def couper_son_fin(self, cid):
        """Le plan de son s'arrête avec la vidéo (fin du dernier plan vidéo)."""
        c = self.projet.clip(cid)
        fin_v = max([fin_clip(x) for x in self.projet.clips_piste("video")] or [0.0])
        if not c or fin_v <= c["debut"] or fin_clip(c) <= fin_v + 0.01:
            self.encart.message(_("Ce son s'arrête déjà avant la fin de la vidéo."))
            return
        self.couper_son_a(cid, fin_v)

    def couper_son_a(self, cid, t):
        c = self.projet.clip(cid)
        if not c or not (c["debut"] + 0.1 < t < fin_clip(c)):
            self.encart.message(_("Placez la tête de lecture sur le plan de son, à l'endroit où il doit s'arrêter."))
            return
        self.projet.marquer()
        v = float(c.get("vitesse", 1.0) or 1.0)
        c["src_fin"] = round(c["src_debut"] + (t - c["debut"]) * v, 3)
        c.setdefault("fondu_sortie", 1.5)
        self.rafraichir()
        self.encart.message(_("Son coupé à {t}, avec un fondu de sortie (réglable dans l'Inspecteur).", t=_tc(t)))

    def _aller_fin(self):
        fin = self.projet.duree()
        self.timeline.aller_a(fin)
        x = int(MARGE_G_TL() + fin * self.timeline.pps - self.timeline.viewport().width() * 0.8)
        self.timeline.horizontalScrollBar().setValue(max(0, x))

    def replier_gauche(self, replie=None):
        """Colonne des médias : complète, ou repliée en une colonne d'icônes (place gagnée pour l'image) ; mémorisé."""
        if replie is None:
            replie = self.params.get("colonne_gauche", "complet") != "icones"
        self.params["colonne_gauche"] = "icones" if replie else "complet"
        self.params.enregistrer()
        self._appliquer_gauche()

    def _appliquer_gauche(self):
        replie = self.params.get("colonne_gauche", "complet") == "icones"
        self.gauche_complet.setVisible(not replie)
        self.gauche_icones.setVisible(replie)
        tailles = self.split_h.sizes()
        if replie:
            self.gauche.setMaximumWidth(72)
            self.gauche.setMinimumWidth(72)
            if tailles and tailles[0] > 72:
                tailles[1] += tailles[0] - 72
                tailles[0] = 72
        else:
            self.gauche.setMinimumWidth(150)
            self.gauche.setMaximumWidth(16777215)
            if tailles and tailles[0] < 150:
                tailles[1] -= 240 - tailles[0]
                tailles[0] = 240
        if tailles:
            self.split_h.setSizes(tailles)

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
        self.b_prepa = QToolButton()
        self.b_prepa.setIcon(icone("synchro", theme.COULEURS["texte"]))
        self.b_prepa.setIconSize(QSize(22, 22))
        self.b_prepa.setAutoRaise(True)
        self.b_prepa.setCheckable(True)
        self.b_prepa.setChecked(bool(self.params.get("preparation_auto", True)))
        self.b_prepa.setToolTip(_("Préparation automatique de la lecture (barre rouge / verte au-dessus de la timeline) : les passages avec "
                                  "effets sont rendus en arrière-plan et la lecture les montre. Décochez sur un poste lent."))
        self.b_prepa.toggled.connect(lambda on: self.preparation.regler(on))
        h.addWidget(self.b_prepa)
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
        m.addSeparator()
        m.addAction(icone("recadrer", theme.COULEURS["texte"]), _("Tracer une zone à flouter, pixelliser ou cacher…"), self.tracer_zone)
        m.addAction(_("Figer l'image ici (cadre photo, légende)…"), self.figer_image)
        m.addAction(_("Bruitage ici…"), self.bruitage)
        m.addAction(_("Tampon vidéo ici…"), self.tampons)
        av = m.addMenu(icone("goodies", theme.COULEURS["texte"]), _("Aviation"))
        av.addAction(_("Tableau de bord de vol…"), self.tableau_de_bord)
        av.addAction(_("Carte animée du trajet et mini-carte…"), self.trajet)
        av.addAction(_("Manche à air…"), self.manche_air)
        av.addAction(_("Sous-titres des échanges radio…"), self.radio)
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
        cib = self.inspecteur._cible
        if cib and not self.apercu.en_lecture:          # élément animé : les curseurs suivent la tête de lecture
            el = self.projet.clip(cib[1]) if cib[0] == "clip" else next((x for x in self.projet.titres + self.projet.goodies if x["id"] == cib[1]), None)
            if el is not None and el.get("cles"):
                if not hasattr(self, "_minut_insp"):
                    self._minut_insp = QTimer(self)
                    self._minut_insp.setSingleShot(True)
                    self._minut_insp.setInterval(150)
                    self._minut_insp.timeout.connect(lambda: self.inspecteur.montrer_selection([self.inspecteur._cible[1]]) if self.inspecteur._cible else None)
                self._minut_insp.start()
        if self.catalogue.isVisible():
            c = self.projet.clip_a(t, "video")
            if c and (c["media"], round(c["src_debut"], 1), round(c["src_fin"], 1)) != self.catalogue.fabrique.cle:
                self.catalogue.actualiser()

    def aller_a(self, t):
        self.apercu.pause()
        self.timeline.aller_a(max(0.0, min(t, self.projet.duree())))

    # ---------------------------------------------------------------- etat
    def rafraichir(self):
        if hasattr(self, "preparation"):
            self.preparation.revoir()
        self.timeline.reconstruire()
        self.apercu.aller_a(self.timeline.position, forcer=True)
        self.lbl_duree.setText(_("Durée : {d} · {f}", d=moteur.duree_texte(self.projet.duree()), f=self.projet.format))
        self.titre_change.emit()

    def _preparation_change(self):
        self.timeline.viewport().update()
        prets, n = self.preparation.resume()
        if hasattr(self, "b_prepa"):
            self.b_prepa.setToolTip(_("Préparation automatique de la lecture : {p} passage(s) prêt(s) sur {n}. Barre au-dessus de la "
                                      "timeline : rouge = à préparer, orange = en cours, vert = prêt (la lecture montre les effets).", p=prets, n=n))

    def _modifie(self):
        if hasattr(self, "preparation"):
            self.preparation.revoir()
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
                if e.get("genre") == "zone":
                    from . import zones as Z
                    Z.deplacer(e, x, y, self.timeline.position)
                else:
                    from . import cles as K
                    K.regler(e, self.timeline.position, x=x, y=y)        # animé : image clef à la tête de lecture
                    self.timeline.reconstruire()
                self._modifie()
                if self.inspecteur._cible and self.inspecteur._cible[1] == ident:
                    self.inspecteur.montrer_selection([ident])
                return

    def autotune(self, c):
        """Vraie correction de justesse : le plan passe sur un nouveau fichier corrigé ; l'original est gardé."""
        from .dialogues_voix import DialogueAutotune
        m = self.projet.media(c["media"]) or {}
        if not m.get("chemin"):
            return
        d = DialogueAutotune(self, m["chemin"], self.params, c["src_debut"], c["src_fin"] - c["src_debut"])
        if d.exec() != QDialog.Accepted or not d.resultat:
            return
        from . import moteur
        fiche = moteur.sonder(d.resultat)
        self.projet.marquer()
        nm = self.projet.ajouter_media(d.resultat, fiche)
        nm["onde"] = m.get("onde") or []
        c.setdefault("media_origine", c["media"])
        c["media"] = nm["id"]
        c["nom"] = nm["nom"]
        self.biblio.remplir(self.projet)
        self.rafraichir()
        self.inspecteur.montrer_clip(c["id"])
        self.encart.message(_("Autotune appliqué : le plan utilise la version corrigée (l'original reste dans les médias)."), 6000)

    def annuler_autotune(self, c):
        if not c.get("media_origine"):
            return
        self.projet.marquer()
        c["media"] = c.pop("media_origine")
        c["nom"] = (self.projet.media(c["media"]) or {}).get("nom", c.get("nom"))
        self.rafraichir()
        self.inspecteur.montrer_clip(c["id"])

    def _calque_taille(self, ident, facteur):
        """Molette sur un texte ou un Goodie dans l'image : plus grand ou plus petit."""
        for e in self.projet.titres + self.projet.goodies:
            if e["id"] == ident and e.get("genre") == "zone":
                from . import zones as Z
                x, y, l, h = Z.rect_a(e, self.timeline.position)
                self.inspecteur._marquer(("taille", ident))
                Z.redimensionner(e, x, y, min(1.0, l * facteur), min(1.0, h * facteur), self.timeline.position)
                self._modifie()
                self.inspecteur.montrer_selection([ident])
                return
            if e["id"] == ident:
                self.inspecteur._marquer(("taille", ident))
                defaut = 1.0 if e in self.projet.titres else 0.22
                if e in self.projet.titres and e.get("cles"):           # texte animé : image clef à la tête de lecture
                    from . import cles as K
                    v = K.valeurs_a(e, self.timeline.position)["taille"]
                    K.regler(e, self.timeline.position, taille=round(min(4.0, max(0.2, v * facteur)), 3))
                    self.timeline.reconstruire()
                else:
                    e["taille"] = round(min(4.0 if e in self.projet.titres else 0.9, max(0.2 if e in self.projet.titres else 0.05, float(e.get("taille", defaut)) * facteur)), 3)
                self._modifie()
                if self.inspecteur._cible and self.inspecteur._cible[1] == ident:
                    self.inspecteur.montrer_selection([ident])
                return

    # ---------------------------------------------------------------- zones tracées (flou, mosaïque, cache…)
    def _zone(self, ident):
        return next((g for g in self.projet.goodies if g["id"] == ident and g.get("genre") == "zone"), None)

    def _calque_cadre(self, ident, x, y, l, h):
        """Une zone redimensionnée à la souris par un de ses coins."""
        z = self._zone(ident)
        if z:
            from . import zones as Z
            self.projet.marquer()
            Z.redimensionner(z, x, y, l, h, self.timeline.position)
            self._modifie()
            self._ouvrir_volet(1)
            self.inspecteur.montrer_selection([ident])

    def tracer_zone(self):
        """Tracer à la souris, dans l'image, une zone à flouter, pixelliser, cacher…"""
        if not self.projet.clip_a(self.timeline.position, "video"):
            self.encart.message(_("Placez la tête de lecture sur un plan vidéo, puis tracez la zone dans l'image."))
            return
        if self.apercu.en_lecture:
            self.apercu.pause()
        self._zone_a_corriger = None
        self.apercu.tracer_zone(True)
        self.encart.message(_("Tracez la zone dans l'image : cliquez à un coin et tirez jusqu'au coin opposé (Echap : abandonner)."))

    def retracer_zone(self, z):
        t = self.timeline.position
        if not (z["debut"] <= t < z["fin"]):
            self.encart.message(_("Placez la tête de lecture pendant la zone, au moment où le suivi se trompe, puis retracez-la."))
            return
        if self.apercu.en_lecture:
            self.apercu.pause()
        self._zone_a_corriger = z["id"]
        self.apercu.tracer_zone(True)
        self.encart.message(_("Retracez la zone à sa bonne place : le suivi sera refait à partir d'ici (Echap : abandonner)."))

    def _zone_tracee(self, x, y, l, h):
        from . import zones as Z
        corr = getattr(self, "_zone_a_corriger", None)
        self._zone_a_corriger = None
        if l <= 0:
            self.encart.message(_("Tracé abandonné."))
            return
        t = self.timeline.position
        if corr:
            z = self._zone(corr)
            if z:
                self.suivre_zone(z, depuis=t, depart=(x, y, l, h))
            return
        c = self.projet.clip_a(t, "video")
        fin = fin_clip(c) if c else t + 5.0
        self.projet.marquer()
        z = Z.nouvelle(t, max(t + 0.5, fin), x, y, l, h)
        self.projet.goodies.append(z)
        self.timeline.reconstruire()
        self._modifie()
        self._ouvrir_volet(1)
        self.inspecteur.montrer_selection([z["id"]])
        self.encart.message(_("Zone posée de {a} à {b} (floutée). Changez l'effet dans l'Inspecteur ; « Suivre ce qu'elle couvre » "
                              "la fait bouger avec le visage ou l'objet.", a=_tc(z["debut"]), b=_tc(z["fin"])))

    def suivre_zone(self, z, depuis=None, depart=None):
        """Analyse de l'image : la zone suit ce qu'elle couvre (en arrière-plan, suivi dans le Centre d'activité)."""
        from . import zones as Z
        self.projet.marquer()
        if depart is not None:          # correction : position retracée à l'instant `depuis`
            pos = (z.get("suivi") or {}).get("positions") or []
            gardes = [p for p in pos if p[0] < depuis - 0.02]
            z["suivi"] = {"media": (z.get("suivi") or {}).get("media"), "positions": gardes + [(round(depuis, 3),) + tuple(round(v, 4) for v in depart)]}
            if not gardes:
                z["suivi"] = None
                z["x"], z["y"], z["l"], z["h"] = (round(v, 4) for v in depart)
        projet = self.projet

        def travail(tache):
            return Z.suivre_zone(projet, z, depuis, progression=lambda f: tache.avancer(f), arret=lambda: tache.arret)
        t = Tache(travail, _("Suivi de la zone"))
        self.taches.append(t)
        self.encart.suivre(t, _("Analyse de l'image : la zone suit ce qu'elle couvre"))

        def fini(r, err, t=t):
            if t in self.taches:
                self.taches.remove(t)
            if err:
                self.encart.message(_("Suivi impossible : {e}", e=str(err)))
            else:
                n = len((z.get("suivi") or {}).get("positions") or [])
                self.encart.message(_("Zone suivie : {n} positions. Lisez le passage pour vérifier ; si elle décroche, « Corriger à la tête "
                                      "de lecture ».", n=n))
            self.timeline.reconstruire()
            self._modifie()
            if self.inspecteur._cible == ("zone", z["id"]):
                self.inspecteur.montrer_selection([z["id"]])
        t.fini.connect(fini)
        t.start()

    def figer_zone(self, z):
        from . import zones as Z
        self.projet.marquer()
        Z.figer(z, self.timeline.position)
        self.timeline.reconstruire()
        self._modifie()
        self.inspecteur.montrer_selection([z["id"]])

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
                                                       self.params.get("dossier_rushes") or dossier_systeme("videos"), filtres)
        if not chemins:
            return
        self.params["dossier_rushes"] = os.path.dirname(chemins[0])
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
                    reg = dict(depot[2])
                    couper = reg.pop("_couper_fin", False)
                    c.update(reg)
                    self.rafraichir()
                    if couper:
                        self.couper_son_fin(c["id"])
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
        if c["piste"] not in ("voix",) and not c["piste"].startswith("video"):
            fin_v = max([fin_clip(x) for x in self.projet.clips_piste("video")] or [0.0])
            if fin_v > c["debut"] + 1 and fin_clip(c) > fin_v + 2:
                self.encart.suivre_message(_("« {n} » dure plus longtemps que la vidéo ({d} de trop).", n=m["nom"], d=_tc(fin_clip(c) - fin_v)),
                                           (_("Couper à la fin de la vidéo"), lambda cid=c["id"]: self.couper_son_fin(cid)), 30000)
        return c

    def musique_auto(self, ambiance=None):
        """La musique demandée par la proposition : d'abord un morceau de mes dossiers qui colle à l'ambiance, sinon un
        morceau libre (Openverse, gratuit) téléchargé ; posé sous la vidéo et coupé à sa fin, avec un fondu."""
        from . import musiques as MU
        duree = max([fin_clip(x) for x in self.projet.clips_piste("video")] or [self.projet.duree()])
        mots = {"energique": "energ upbeat rock electro dance", "douce": "doux douce calm piano soft", "cinema": "cinema epic film orchestr",
                "chaleureuse": "acoust guitar warm folk", "mysterieuse": "myst dark ambient", "legere": "happy joy pop ukulele",
                "calme": "calm ambient piano", "joyeuse": "happy joy pop", "aventure": "adventure epic inspir"}.get(ambiance or "", "")
        liste = MU.morceaux([self.params.get("musiques_dossier") or "", MU.dossier(self.params)])

        def note(x):
            texte = " ".join(str(x.get(k) or "") for k in ("titre", "album", "artiste", "dossier", "chemin")).lower()
            return (sum(1 for w in mots.split() if w in texte) * 10) + (5 if (x.get("duree") or 0) >= duree else 0)
        if liste:
            x = max(liste, key=note)
            self._piste_depot = ("audio", 0.0, {"volume": 0.8, "_couper_fin": True})
            self.importer([x["chemin"]])
            self.encart.message(_("Musique : « {t} » de vos dossiers, ambiance {a}.", t=x.get("titre", ""), a=ambiance or "?"))
            return
        from . import packs_ia as P_
        if P_.modele_actif("musique", self.params):     # musique IA sur ce poste : gratuite, à la bonne durée
            from . import creatif as C
            style = {"energique": "electro", "douce": "piano", "cinema": "cinema", "chaleureuse": "acoustique", "mysterieuse": "ambient",
                     "legere": "pop_aerienne", "calme": "lofi", "joyeuse": "pop_aerienne", "aventure": "rock"}.get(ambiance or "", "pop_aerienne")
            from .config import dossier_donnees
            sortie = os.path.join(dossier_donnees(), "ia_creations", f"musique_{style}_{int(time.time())}.mp3")
            os.makedirs(os.path.dirname(sortie), exist_ok=True)
            t = Tache(lambda tache: C.musique(style, sortie, max(15.0, duree + 2), self.params, progression=tache.avancer, arret=tache.arret_demande),
                      _("Musique IA"))
            self.taches.append(t)
            self.encart.suivre(t, _("Musique IA sur ce poste, style « {s} »", s=style))

            def fini_ia(chemin, err):
                if err or not chemin:
                    self.encart.message(_("Musique IA impossible : {e}", e=str(err or "")[:160]))
                    return
                self._piste_depot = ("audio", 0.0, {"volume": 0.8, "fondu_entree": 1.0, "fondu_sortie": 3.0, "_couper_fin": True})
                self.importer([chemin])
            t.fini.connect(fini_ia)
            t.start()
            return
        corresp = {"chaleureuse": "acoustique", "douce": "calme", "legere": "joyeuse", "mysterieuse": "calme"}
        amb = corresp.get(ambiance, ambiance)

        def travail(tache):
            tache.avancer(0.1, _("recherche d'une musique libre"))
            res = MU.chercher("", amb if amb in dict((k, 1) for k, _l, _m in MU.AMBIANCES) else None, "long" if duree > 120 else None)
            if not res:
                raise MU.ErreurMusique(_("Aucune musique libre trouvée pour cette ambiance."))
            assez = [r for r in res if r["duree"] >= duree] or sorted(res, key=lambda r: -r["duree"])
            tache.avancer(0.3, _("téléchargement de « {t} »", t=assez[0]["titre"]))
            return MU.telecharger(assez[0], self.params, progression=lambda f: tache.avancer(0.3 + 0.7 * f))
        t = Tache(travail, _("Musique"))
        self.taches.append(t)
        self.encart.suivre(t, _("Musique libre pour l'ambiance « {a} »", a=ambiance or "?"))

        def fini(chemin, err):
            if err or not chemin:
                self.encart.suivre_message(_("Pas de musique posée : {e}", e=str(err or "")[:120]),
                                           (_("Choisir une musique…"), lambda: self.fenetre.musique()), 30000)
                return
            self._piste_depot = ("audio", 0.0, {"volume": 0.8, "_couper_fin": True})
            self.importer([chemin])
        t.fini.connect(fini)
        t.start()

    def _memoriser_tailles(self):
        self.params["tailles_vue"] = {"v": self.split_v.sizes(), "h": self.split_h.sizes()}
        self.params.enregistrer()

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
                c = self.projet.clip_a((z[0] + z[1]) / 2, "video")
                if c:
                    self.effets_du_clip(c["id"], partie=z)
                else:
                    self.encart.message(_("Pas de plan vidéo dans la partie choisie."))
                return
            c = self._clip_selectionne()          # le plan cliqué, sinon celui sous le curseur
            if c:
                self.effets_du_clip(c["id"])
            else:
                self.encart.message(_("Cliquez d'abord sur un plan dans la timeline, puis sur Effets."))
        elif oid == "goodies":
            self.nouveau_goodie()
        elif oid == "zone":
            self.tracer_zone()
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
        if d.exec() != QDialog.Accepted:
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
        elif quoi == "vignette":
            self.projet.marquer()
            self.projet.d["vignette_t"] = round(self.timeline.position, 3)
            self.rafraichir()
            self.encart.message(_("Vignette du fichier : l'image à {t}. A l'export, elle est intégrée à la vidéo (explorateur de fichiers, "
                                  "lecteurs) et enregistrée à côté en JPG pour la miniature YouTube.", t=_tc(self.timeline.position)), 9000)
        elif quoi == "vignette_retirer":
            self.projet.marquer()
            self.projet.d.pop("vignette_t", None)
            self.rafraichir()
            self.encart.message(_("Vignette retirée : le fichier montrera sa première image."))
        elif quoi == "son_fin":
            self.couper_son_fin(ident)
        elif quoi == "whoosh":
            c = self.projet.clip(ident)
            if c:
                self.bruitage("whoosh", max(0.0, c["debut"] - 0.35))
        elif quoi == "tampon":
            self.tampons()
        elif quoi == "figer":
            self.figer_image()
        elif quoi in ("zone_suivre", "zone_retracer", "zone_figer"):
            z = self._zone(ident)
            if z:
                {"zone_suivre": self.suivre_zone, "zone_retracer": self.retracer_zone, "zone_figer": self.figer_zone}[quoi](z)
        elif quoi == "image":
            self.extraire_image()
        elif quoi in ("partie_supprimer", "partie_garder"):
            self.partie(quoi == "partie_garder")
        elif quoi == "effets_partie":
            z = self.timeline.zone_valide()
            c = self.projet.clip_a((z[0] + z[1]) / 2, "video") if z else None
            if c:
                self.effets_du_clip(c["id"], partie=z)
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
        if d.exec() != QDialog.Accepted:
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
        if d.exec() != QDialog.Accepted:
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
        if d.exec() != QDialog.Accepted:
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

    def poser_effet(self, cid, eid):
        """Effet ou transition du catalogue posé sur un plan (glissé sur la timeline, double-clic, clic droit).
        cid None : le plan sélectionné, sinon celui sous la tête de lecture."""
        from . import effets as E
        c = self.projet.clip(cid) if cid else self._clip_selectionne()
        fi = E.fiche(eid)
        if not c or not fi:
            self.encart.message(_("Cliquez d'abord sur un plan dans la timeline (ou glissez la vignette directement sur le plan)."))
            return
        if fi["pack"] and not E.pack_pret(fi["pack"], self.params):
            self.encart.message(_("« {n} » demande le pack « {p} » : cochez-le dans Edition › Préférences.", n=fi["nom"],
                                  p=E.PACKS.get(fi["pack"], {}).get("nom", fi["pack"])))
            return
        transition = fi["famille"] == "transition"
        if transition and not any(x["debut"] < c["debut"] - 0.01 for x in self.projet.clips_piste(c.get("piste", "video"))):
            self.encart.message(_("Une transition se pose sur le raccord entre deux plans : glissez-la sur le début du plan qui arrive."))
            return
        self.projet.marquer()
        if transition:
            c["transition"] = {"id": eid, "params": dict(E.defauts(eid))}
            genre, i = "transition", 0
        else:
            c.setdefault("effets", [])
            ef = {"id": eid, "params": dict(E.defauts(eid))}
            z = self.timeline.zone_valide()
            if z and z[1] > c["debut"] + 0.05 and z[0] < fin_clip(c) - 0.05:      # partie en jaune sur ce plan : l'effet s'y limite
                ef["de"] = round(max(0.0, z[0] - c["debut"]), 2)
                ef["a"] = round(min(duree_clip(c), z[1] - c["debut"]), 2)
            c["effets"].append(ef)
            genre, i = "effet", len(c["effets"]) - 1
        rec = [k for k in (self.params.get("effets_recents") or []) if k != eid]
        self.params["effets_recents"] = [eid] + rec[:19]
        self.rafraichir()
        self.timeline.selectionner(c["id"])
        self.inspecteur.montrer_element(c["id"], genre, i)
        self.encart.message(_("« {n} » posé sur « {p} » : étiquette sur le plan, réglages dans l'onglet Inspecteur ; Annuler le retire.", n=fi["nom"], p=c.get("nom", "")))

    def effets_du_clip(self, cid, partie=None):
        """Fenêtre des effets d'un plan. partie (a, b) en temps du montage : les effets AJOUTES ne couvrent que ces
        secondes-là (bande bleue sur le plan, bords tirables) ; le plan n'est pas coupé."""
        c = self.projet.clip(cid)
        if not c:
            return
        avant = [dict(e) for e in c.get("effets") or []]
        d = DialogueEffets(self, c, self.params, self.projet.medias)
        if d.exec() == QDialog.Accepted:
            self.projet.marquer()
            c["effets"], c["transition"] = d.resultat()
            if partie:
                de = round(max(0.0, partie[0] - c["debut"]), 2)
                a = round(min(duree_clip(c), partie[1] - c["debut"]), 2)
                for e in c["effets"]:
                    if e not in avant and a - de > 0.05:
                        e["de"], e["a"] = de, a
                self.timeline.zone = [None, None]
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
        if d.exec() != QDialog.Accepted:
            return
        t = d.resultat()
        if not t["texte"]:
            return
        self.projet.marquer()
        modele = d.moderne.currentData()
        if modele:                               # style moderne animé : rendu par le moteur des intros, sur la piste Goodies
            L_, H_ = self.projet.taille
            self.projet.ajouter_goodie("intro_titre", t["debut"], max(t["fin"], t["debut"] + 2.0), x=0.5, y=0.5, taille=L_ / max(1, H_),
                                       options={"texte": t["texte"], "sous_texte": d.sous_moderne.text().strip(), "modele": modele})
            self.rafraichir()
            self.encart.message(_("Texte animé posé sur la piste Goodies : cliquez-le pour changer le texte ou le style."))
            return
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
        """Galerie des Goodies (vignettes) ; les instruments d'aviation, la carte et la manche ouvrent leur fenêtre dédiée."""
        from .dialogues_effets_plus import GalerieGoodies
        d = GalerieGoodies(self, self.params)
        if d.exec() != QDialog.Accepted or not d.choix():
            return
        gid = d.choix()
        if gid in ("carte_trajet", "mini_carte"):
            self.trajet()
            return
        if gid == "manche_air":
            self.manche_air()
            return
        t = self.timeline.position
        self.projet.marquer()
        g = self.projet.ajouter_goodie(gid, t, min(max(t + 5.0, self.projet.duree()), t + 8.0))
        if gid in ("polaroid", "post_it", "fleche", "bandeau_tendance", "surligne"):
            g["taille"], g["x"], g["y"] = {"fleche": (0.26, 0.5, 0.5), "bandeau_tendance": (0.5, 0.3, 0.22),
                                           "surligne": (0.42, 0.5, 0.75)}.get(gid, (0.32, 0.5, 0.45))
        if gid == "fleche":
            g["options"].update(style="courbe", couleur="#ff3b30", contour="#ffffff", dessin=True)
        elif gid == "bandeau_tendance":
            g["options"].update(texte=_("TITRE CHOC"), style="incline", couleur="#ff8c1a", angle=-4)
        elif gid == "surligne":
            g["options"].update(texte=_("Incroyable"), couleur="#ffe14d")
        elif gid == "intro_titre":
            L_, H_ = self.projet.taille
            g.update(x=0.5, y=0.5, taille=L_ / max(1, H_), fin=g["debut"] + 3.5)
            g["options"].update(texte=self.projet.d.get("chaine") or _("Votre titre"), modele="masque")
        self.rafraichir()
        self._ouvrir_volet(1)
        self.inspecteur.montrer_selection([g["id"]])
        self.encart.message(_("Goodie posé de {a} à {b} : glissez-le et tirez ses coins dans l'image ; réglages dans l'Inspecteur.",
                              a=_tc(g["debut"]), b=_tc(g["fin"])))

    # ---------------------------------------------------------------- IA locale sur les rushes
    def analyser_rushes(self, ids):
        """Analyse des rushes par le modèle de vision local, en arrière-plan, un par un (rien n'est envoyé)."""
        from . import analyse_locale as AL
        if not AL.disponible(self.params):
            QMessageBox.information(self, _("IA locale"), _("L'analyse se fait sur ce poste, sans rien envoyer ni payer, avec un modèle de "
                                                            "vision : cochez-en un dans Edition › Préférences › IA locale (il se télécharge une fois)."))
            return
        medias = [m for m in self.projet.medias if (not ids or m["id"] in ids) and m.get("genre") in ("video", "image")]
        if not medias:
            return
        params = self.params

        def travail(tache):
            faits = 0
            for k, m in enumerate(medias):
                if tache.arret:
                    break
                tache.avancer(k / len(medias), m["nom"])
                try:
                    AL.analyser(m, params, progression=lambda f, k=k: tache.avancer((k + f) / len(medias), m["nom"]))
                    faits += 1
                except AL.ErreurAnalyse:
                    raise
                except Exception:       # noqa: BLE001 : un rush illisible n'arrête pas les autres
                    continue
            return faits
        t = Tache(travail, _("Analyse des rushes (IA locale)"))
        self.taches.append(t)
        self.encart.suivre(t, _("Analyse de {n} rush(es) par l'IA locale, sur ce poste", n=len(medias)))

        def fini(r, err):
            if t in self.taches:
                self.taches.remove(t)
            if err:
                self.encart.message(_("Analyse impossible : {e}", e=str(err)))
                return
            self.projet.modifie = True
            self.biblio.remplir(self.projet)
            self.encart.message(_("{n} rush(es) analysés : survolez un média pour lire ce que l'IA locale y a vu ; la recherche au-dessus "
                                  "des médias porte aussi dessus.", n=r or 0))
        t.fini.connect(fini)
        t.start()

    def _etiquette_texte_lu(self, ident, texte):
        """Un texte lu dans un rush (immatriculation, panneau) devient une étiquette posée sur le premier plan de ce rush."""
        c = next((x for x in self.projet.clips if x["media"] == ident), None)
        t0 = c["debut"] if c else self.timeline.position
        self.projet.marquer()
        t = self.projet.ajouter_titre(texte, t0, t0 + 4.0, style="etiquette", y=0.12)
        self.rafraichir()
        self._ouvrir_volet(1)
        self.inspecteur.montrer_selection([t["id"]])

    # ---------------------------------------------------------------- image figée, bruitages
    def figer_image(self, t=None):
        """Image figée à la tête de lecture : le plan s'arrête sur cette image pendant quelques secondes (cadre photo,
        légende, flash, déclic au choix), puis reprend. La suite du montage est décalée d'autant."""
        from .dialogues_effets_plus import DialogueFiger
        from . import bruitages as B
        t = self.timeline.position if t is None else t
        c = self.projet.clip_a(t, "video")
        m = self.projet.media(c["media"]) if c else None
        if not m or m.get("genre") != "video":
            self.encart.message(_("Placez la tête de lecture sur un plan vidéo, à l'image à figer."))
            return
        d = DialogueFiger(self)
        if d.exec() != QDialog.Accepted:
            return
        o = d.options()
        src = c["src_debut"] + (t - c["debut"]) * c.get("vitesse", 1.0)
        from .config import dossier_donnees
        dossier = os.path.join(dossier_donnees(), "images_figees")
        os.makedirs(dossier, exist_ok=True)
        png = os.path.join(dossier, f"{os.path.splitext(m['nom'])[0]}_{src:.2f}s.png".replace(" ", "_"))
        try:
            largeur = int(((m.get("fiche") or {}).get("video") or {}).get("largeur") or 1920)
            with open(png, "wb") as f:
                f.write(moteur.image(m["chemin"], src, min(3840, largeur)))
        except Exception as e:      # noqa: BLE001
            QMessageBox.warning(self, _("Image figée"), str(e))
            return
        self.projet.marquer()
        if c["debut"] + 0.04 < t < fin_clip(c) - 0.04:
            self.projet.couper(c["id"], t)
        n = o["duree"]
        for x in self.projet.clips:                 # la suite du montage est décalée de la durée de l'image figée
            if x["debut"] >= t - 1e-3:
                x["debut"] += n
        for x in self.projet.titres + self.projet.goodies:
            if x["debut"] >= t - 1e-3:
                x["debut"] += n
                x["fin"] += n
        mi = self.projet.ajouter_media(png, moteur.sonder(png))
        mi["nom"] = _("Image figée {t}", t=_tc(t))
        ci = self.projet.ajouter_clip(mi["id"], "video", t, 0.0, n)
        ci["nom"] = mi["nom"]
        if o["style"] == "cadre":
            ci["effets"].append({"id": "cadre_photo", "params": dict(E_defauts("cadre_photo"))})
        if o["zoom"]:
            ci["effets"].insert(0, {"id": "zoom_lent", "params": {"force": 0.12, "sens": "avant"}})
        if o["style"] == "bullet":
            ci["effets"].append({"id": "orbite", "params": {"amplitude": 1.0, "vitesse": 1.0}})
            ci["effets"].append({"id": "matrix_vert", "params": {}})
            o["declic"] = False
            B.poser(self.projet, "whoosh", t)
        if o["flash"]:
            ci["transition"] = {"id": "t_fondu_blanc", "params": {"duree": 0.3}}
        if o["legende"]:
            self.projet.ajouter_titre(o["legende"], t + 0.2, t + n - 0.1, style="etiquette", y=0.95, animation="fondu")
        if o["declic"]:
            B.poser(self.projet, "declic", t)
        self.rafraichir()
        self.timeline.selectionner(ci["id"])
        self._ouvrir_volet(1)
        self.inspecteur.montrer_clip(ci["id"])
        self.encart.message(_("Image figée de {n:.1f} s posée à {t} : c'est un plan comme un autre (rognez-le pour changer sa durée, "
                              "Supprimer pour l'enlever).", n=n, t=_tc(t)))

    def bruitage(self, ident=None, t=None):
        """Pose un bruitage au curseur (ou à t) ; sans ident, la fenêtre des bruitages s'ouvre pour choisir et écouter."""
        from . import bruitages as B
        if ident is None:
            from .dialogues_effets_plus import DialogueBruitages
            d = DialogueBruitages(self)
            if d.exec() != QDialog.Accepted or not d.choix():
                return
            ident = d.choix()
        t = self.timeline.position if t is None else t
        self.projet.marquer()
        try:
            c = B.poser(self.projet, ident, t)
        except Exception as e:      # noqa: BLE001
            QMessageBox.warning(self, _("Bruitage"), str(e))
            return
        self.rafraichir()
        self.timeline.selectionner(c["id"])
        self.encart.message(_("Bruitage « {n} » posé à {t} sur la piste {p} : réglez son volume dans l'Inspecteur.",
                              n=B.SONS[ident][0], t=_tc(t), p=self.timeline.libelle_piste(c["piste"])))

    # ---------------------------------------------------------------- aviation (tout réglé par l'utilisateur)
    def _etapes_projet(self):
        for g in self.projet.goodies:
            if g.get("genre") in ("carte_trajet", "mini_carte") and (g.get("options") or {}).get("etapes"):
                return g["options"]["etapes"]
        return []

    def tableau_de_bord(self, groupe=None):
        """Tableau de bord de vol : instruments et profil de vol (nouveau, ou celui d'un groupe déjà posé)."""
        from .dialogues_aviation import DialogueTableau
        from . import aviation as A
        anciens = [g for g in self.projet.goodies if groupe and (g.get("options") or {}).get("groupe") == groupe]
        debut = anciens[0]["debut"] if anciens else 0.0
        fin = anciens[0]["fin"] if anciens else max(10.0, self.projet.duree())
        reg = (anciens[0].get("options") or {}).get("profil") if anciens else None
        d = DialogueTableau(self, debut, fin, reg, [g["genre"] for g in anciens] or None, self._etapes_projet())
        if d.exec() != QDialog.Accepted or not d.instruments():
            return
        self.projet.marquer()
        gs = A.poser_tableau(self.projet, d.debut.value(), max(d.debut.value() + 1, d.fin.value()), d.instruments(), d.reglages(),
                             d.etapes_suivies(), taille=d.taille.value(), groupe=groupe)
        self.rafraichir()
        self._ouvrir_volet(1)
        self.inspecteur.montrer_selection([gs[0]["id"]])
        self.encart.message(_("Tableau de bord posé : {n} instruments. Glissez-les dans l'image ; « Profil de vol… » dans l'Inspecteur pour "
                              "changer les chiffres.", n=len(gs)))

    def trajet(self, goodie=None):
        """Carte animée du trajet et mini-carte (mêmes étapes)."""
        from .dialogues_aviation import DialogueTrajet
        cartes = [g for g in self.projet.goodies if g.get("genre") in ("carte_trajet", "mini_carte")]
        ref = goodie or (cartes[0] if cartes else None)
        debut = ref["debut"] if ref else 0.0
        fin = ref["fin"] if ref else max(10.0, self.projet.duree())
        d = DialogueTrajet(self, debut, fin, (ref or {}).get("options"), avec_mini=not cartes or any(g["genre"] == "mini_carte" for g in cartes))
        if cartes:
            d.c_carte.setChecked(any(g["genre"] == "carte_trajet" for g in cartes))
        if d.exec() != QDialog.Accepted:
            return
        self.projet.marquer()
        opts = d.options()
        voulus = {"carte_trajet": d.c_carte.isChecked(), "mini_carte": d.c_mini.isChecked()}
        for genre, oui in voulus.items():
            g = next((x for x in cartes if x["genre"] == genre), None)
            if oui and g is None:
                g = self.projet.ajouter_goodie(genre, d.debut.value(), d.fin.value(), **(
                    {"taille": 0.42, "x": 0.77, "y": 0.3} if genre == "carte_trajet" else {"taille": 0.2, "x": 0.11, "y": 0.17}))
            if not oui and g is not None:
                self.projet.retirer_element(g["id"])
                continue
            if g is not None:
                g["debut"], g["fin"] = d.debut.value(), max(d.debut.value() + 1, d.fin.value())
                g.setdefault("options", {}).update(opts)
        self.rafraichir()
        self.encart.message(_("Trajet : {n} étapes. La carte se dessine pendant la vidéo ; glissez-la ou tirez ses coins dans l'image.",
                              n=len(opts["etapes"])))

    def manche_air(self, goodie=None):
        from .dialogues_aviation import DialogueManche
        d = DialogueManche(self, goodie["debut"] if goodie else 0.0, goodie["fin"] if goodie else max(10.0, self.projet.duree()),
                           (goodie or {}).get("options"))
        if d.exec() != QDialog.Accepted:
            return
        self.projet.marquer()
        if goodie is None:
            goodie = self.projet.ajouter_goodie("manche_air", d.debut.value(), d.fin.value(), taille=0.2, x=0.9, y=0.2)
        goodie["debut"], goodie["fin"] = d.debut.value(), max(d.debut.value() + 1, d.fin.value())
        goodie.setdefault("options", {}).update(d.options())
        self.rafraichir()
        self._ouvrir_volet(1)
        self.inspecteur.montrer_selection([goodie["id"]])

    def radio(self):
        """Ecoute du son des plans dans la bande radio ; les échanges trouvés sont proposés en sous-titres « radio »."""
        from . import aviation as A, sous_titres as ST
        if not ST.disponible():
            QMessageBox.information(self, _("Echanges radio"), _("L'écoute se fait sur ce poste avec le modèle « Voix » : cochez-le dans "
                                                                  "Edition › Préférences › IA locale (il se télécharge une fois), puis recommencez."))
            return
        projet = self.projet

        def travail(tache):
            return A.detecter_radio(projet, self.params, progression=lambda f, *_a: tache.avancer(f))
        t = Tache(travail, _("Ecoute des échanges radio"))
        self.taches.append(t)
        self.encart.suivre(t, _("Ecoute des échanges radio dans le son des plans"))

        def fini(r, err):
            if t in self.taches:
                self.taches.remove(t)
            if err:
                self.encart.message(_("Ecoute impossible : {e}", e=str(err)))
                return
            if not r:
                self.encart.message(_("Aucune parole trouvée dans le son des plans."))
                return
            from .dialogues_aviation import DialogueRadio
            d = DialogueRadio(self, r)
            if d.exec() == QDialog.Accepted:
                self.projet.marquer()
                self.projet.d["sous_titres_radio"] = d.resultat()
                self.rafraichir()
                self.encart.message(_("{n} sous-titre(s) radio posés (en haut de l'image, style radio). Montage › Aviation › Sous-titres radio "
                                      "pour les revoir.", n=len(d.resultat())))
        t.fini.connect(fini)
        t.start()

    def editer_element(self, ident):
        if self._zone(ident):
            self._ouvrir_volet(1)
            self.inspecteur.montrer_selection([ident])
            return
        c = self.projet.clip(ident)
        if c:
            self.effets_du_clip(ident)
            return
        for t in self.projet.titres:
            if t["id"] == ident:
                d = DialogueTitre(self, t, medias_visages=self._medias_visages())
                if d.exec() == QDialog.Accepted:
                    self.projet.marquer()
                    t.update(d.resultat())
                    if t.get("suivi") and not t["suivi"].get("positions"):
                        self._suivre(t)
                    self.rafraichir()
                return
        for g in self.projet.goodies:
            if g["id"] == ident and (g.get("options") or {}).get("groupe"):
                self.tableau_de_bord(g["options"]["groupe"])
                return
            if g["id"] == ident and g.get("genre") in ("carte_trajet", "mini_carte"):
                self.trajet(g)
                return
            if g["id"] == ident and g.get("genre") == "manche_air":
                self.manche_air(g)
                return
            if g["id"] == ident:
                d = DialogueGoodie(self, g, params=self.params)
                if d.exec() == QDialog.Accepted:
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
        mu = r.get("musique") or {}
        if mu and choix.get("musique", True) and not (mu.get("media") and self.projet.media(mu["media"])) and not self.projet.clips_piste("audio"):
            self.musique_auto(mu.get("ambiance"))       # aucune musique importée : on en trouve une (mes dossiers, sinon libre)
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

    def atelier_ia(self, famille="image"):
        """Atelier IA local : image du film retouchée, effet sur la partie en jaune, logo, musique."""
        from .dialogues_creatif import DialogueAtelierIA
        DialogueAtelierIA(self, famille).exec()

    def inserer_image(self, png, t, duree=3.0, nom=""):
        """Insère une image à l'instant t (la suite du montage se décale), avec un zoom lent ; annulable."""
        self.projet.marquer()
        c = self.projet.clip_a(t, "video")
        if c and c["debut"] + 0.04 < t < fin_clip(c) - 0.04:
            self.projet.couper(c["id"], t)
        for x in self.projet.clips:
            if x["debut"] >= t - 1e-3:
                x["debut"] += duree
        for x in self.projet.titres + self.projet.goodies:
            if x["debut"] >= t - 1e-3:
                x["debut"] += duree
                x["fin"] += duree
        mi = self.projet.ajouter_media(png, moteur.sonder(png))
        mi["nom"] = nom or os.path.basename(png)
        ci = self.projet.ajouter_clip(mi["id"], "video", t, 0.0, duree)
        ci["nom"] = mi["nom"]
        ci["effets"].insert(0, {"id": "zoom_lent", "params": {"force": 0.08, "sens": "avant"}})
        self.biblio.remplir(self.projet)
        self.rafraichir()
        self.timeline.selectionner(ci["id"])
        self.encart.message(_("Image insérée à {t} ; la suite du montage est décalée de {d} s.", t=_tc(t), d=duree))
        return ci

    def inserer_tampon(self, video, t, nom=""):
        """Insère un tampon vidéo (avec son son) à l'instant t sur la piste Vidéo 1 ; la suite du montage se décale. Annulable."""
        f = moteur.sonder(video)
        duree = float(f.get("duree") or 2.0)
        self.projet.marquer()
        c = self.projet.clip_a(t, "video")
        if c and c["debut"] + 0.04 < t < fin_clip(c) - 0.04:
            self.projet.couper(c["id"], t)
        for x in self.projet.clips:
            if x["debut"] >= t - 1e-3:
                x["debut"] += duree
        for x in self.projet.titres + self.projet.goodies:
            if x["debut"] >= t - 1e-3:
                x["debut"] += duree
                x["fin"] += duree
        mi = self.projet.ajouter_media(video, f)
        mi["nom"] = nom or os.path.basename(video)
        ci = self.projet.ajouter_clip(mi["id"], "video", t, 0.0, duree)
        ci["nom"] = mi["nom"]
        ci["ajustement"] = "contenir_flou"
        self.biblio.remplir(self.projet)
        self.rafraichir()
        self.timeline.selectionner(ci["id"])
        self.encart.message(_("Tampon « {n} » inséré à {t} ({d:.1f} s) ; la suite du montage est décalée. Supprimer le plan le retire.",
                              n=mi["nom"], t=_tc(t), d=duree), 8000)
        return ci

    def poser_son(self, son, t, nom=""):
        """Pose un tampon sonore (réplique, bruit) à l'instant t sur une piste de son libre, sans décaler le film. Annulable."""
        from . import bruitages
        f = moteur.sonder(son)
        d = float(f.get("duree") or 1.0)
        self.projet.marquer()
        mi = self.projet.ajouter_media(son, f)
        mi["nom"] = nom or os.path.basename(son)
        piste = bruitages.piste_libre(self.projet, t, d)
        ci = self.projet.ajouter_clip(mi["id"], piste, t)
        ci["nom"] = mi["nom"]
        self.projet.ranger(piste)
        self.biblio.remplir(self.projet)
        self.rafraichir()
        self.timeline.selectionner(ci["id"])
        self.encart.message(_("Son « {n} » posé à {t} sur la piste {p} ({d:.1f} s) ; réglez son volume dans l'Inspecteur.",
                              n=mi["nom"], t=_tc(t), p=piste, d=d), 8000)
        return ci

    def tampons(self, onglet=0):
        """Bibliothèque de tampons vidéo : les vôtres, les tampons maison, les clips libres trouvés en ligne."""
        from .dialogues_tampons import DialogueTampons
        DialogueTampons(self, onglet).exec()

    def poser_au_dessus(self, video, t, nom=""):
        """Pose un clip créé (effet IA) au-dessus du film, plein cadre, sur la première piste vidéo libre."""
        from .projet import duree_clip
        f = moteur.sonder(video)
        d = float(f.get("duree") or 1.0)
        self.projet.marquer()
        piste = None
        for p in self.projet.pistes_video()[1:]:
            if not any(x["debut"] < t + d and fin_clip(x) > t for x in self.projet.clips_piste(p)):
                piste = p
                break
        if piste is None:
            piste = self.projet.ajouter_piste("video")
        mi = self.projet.ajouter_media(video, f)
        mi["nom"] = nom or os.path.basename(video)
        ci = self.projet.ajouter_clip(mi["id"], piste, t, 0.0, d)
        ci["nom"] = mi["nom"]
        ci["incrust"] = {"echelle": 1.0, "x": 0.5, "y": 0.5, "opacite": 1.0}
        ci["muet"] = True
        self.biblio.remplir(self.projet)
        self.rafraichir()
        self.timeline.selectionner(ci["id"])
        self.encart.message(_("« {n} » posé au-dessus ({p}), {d} : supprimez-le pour revenir à l'original.", n=mi["nom"], p=piste,
                              d=_tc(duree_clip(ci))))
        return ci

    def transitions_auto(self):
        from .dialogues_transitions import DialogueTransitionsAuto
        DialogueTransitionsAuto(self).exec()

    def dites_le(self, phrase=""):
        """« Dites-le en clair » : une phrase → des actions montrées, cochables, faites d'un coup (annulables)."""
        from .dialogues_commande import DialogueCommande
        DialogueCommande(self, (phrase or "").strip()).exec()

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
        """Lecture avec effets : le passage à venir est rendu en arrière-plan (720p) puis joué dans l'aperçu ; pendant
        qu'il se joue, le passage suivant se prépare, pour enchaîner sans arrêt."""
        debut = self.timeline.position
        if self.projet.duree() - debut < 0.2:
            self.encart.message(_("Placez le curseur avant la fin du montage."))
            return
        self._preparer_segment(debut, duree_max, jouer=True)

    def _preparer_segment(self, debut, duree_max=15.0, jouer=False):
        from . import export
        import copy, tempfile
        fin = min(self.projet.duree(), debut + duree_max)
        if fin - debut < 0.2:
            return
        cle = (round(debut, 2), round(fin, 2), self.apercu._etat_projet())
        cache = getattr(self, "_segments_rendus", {})
        if cle in cache and os.path.exists(cache[cle]):          # déjà prêt pour cet état du montage
            if jouer:
                self.apercu.jouer_segment(debut, fin, cache[cle])
                self._preparer_segment(fin, duree_max)
            return
        en_cours = getattr(self, "_segments_en_cours", set())
        if cle in en_cours:
            return
        en_cours.add(cle)
        self._segments_en_cours = en_cours
        self._n_segment = getattr(self, "_n_segment", 0) + 1
        sortie = os.path.join(tempfile.gettempdir(), f"philcut_lecture_{os.getpid()}_{self._n_segment % 6}.mp4")
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
        self.encart.suivre(t, _("Préparation de la lecture avec effets ({a} → {b})", a=_tc(debut), b=_tc(fin)) if jouer else
                           _("Préparation du passage suivant ({a} → {b})", a=_tc(debut), b=_tc(fin)))

        def fini(r, e):
            self._segments_en_cours.discard(cle)
            if e or not r:
                return
            cache = {k: v for k, v in getattr(self, "_segments_rendus", {}).items() if v != r}
            cache[cle] = r
            self._segments_rendus = cache
            if jouer:
                self.apercu.jouer_segment(debut, fin, r)
                self._preparer_segment(fin, duree_max)
            elif self.apercu.en_lecture and self.apercu.segment is None and debut - 0.05 <= self.apercu.t < fin - 0.3:
                # la suite arrive en retard (poste lent) : la lecture, repartie sur les rushes, la rejoint sans revenir en arrière
                self.apercu.segment = (debut, fin, r)
                self.apercu.clip = None
                self.apercu._source = None
                self.apercu.aller_a(self.apercu.t, forcer=True)
                self._preparer_segment(fin, duree_max)
        t.fini.connect(fini)
        t.start()

    def _segment_fini(self, fin):
        """Le passage rendu est fini : si le suivant est prêt pour cet état du montage, on enchaîne."""
        for (d, f, etat), chemin in getattr(self, "_segments_rendus", {}).items():
            if abs(d - fin) < 0.05 and etat == self.apercu._etat_projet() and os.path.exists(chemin):
                self.apercu.segment = (d, f, chemin)
                self.apercu.clip = None
                self.apercu._source = None
                self._preparer_segment(f, f - d)
                return

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
