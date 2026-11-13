"""La page d'Accueil : nouveau projet, projets recents, projets ouverts sur les autres postes, propositions
laissees ici (reprise, synchronisation), jamais de fenetre bloquante au demarrage."""
import datetime, os

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QFrame, QScrollArea,
                               QMenu, QSizePolicy)

from . import theme
from .config import VERSION, est_portable
from .icones import icone, logo
from .langue import _
from .projet import FORMATS


class PageAccueil(QWidget):
    nouveau = Signal(str)            # format
    ouvrir = Signal(str)
    ouvrir_dialogue = Signal()
    importer_rushes = Signal()
    reprendre = Signal(str, list)    # machine, fichiers
    synchroniser = Signal()
    action_fichier = Signal(str, str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.propositions = []
        racine = QVBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setFrameShape(QFrame.NoFrame)
        corps = QWidget()
        v = QVBoxLayout(corps)
        v.setContentsMargins(40, 28, 40, 28)
        v.setSpacing(18)
        # ---- en-tete
        h = QHBoxLayout()
        lg = QLabel()
        lg.setPixmap(logo(72).pixmap(72, 72))
        h.addWidget(lg)
        t = QLabel(f"<span style='font-size:30px;font-weight:700'>PhilCut</span>&nbsp;&nbsp;<span style='color:{theme.COULEURS['texte2']}'>{VERSION}"
                   f"{' · ' + _('version portable') if est_portable() else ''}</span><br><span style='color:{theme.COULEURS['texte2']}'>"
                   + _("Montage vidéo simple, efficace, effet wahou. Vos rushes restent où ils sont.") + "</span>")
        h.addWidget(t, 1)
        v.addLayout(h)
        # ---- actions
        ha = QHBoxLayout()
        for ic, lib, aide, f in (("clap", _("Nouveau projet 16:9"), _("YouTube, écran, télévision"), lambda: self.nouveau.emit("16:9")),
                                 ("format", _("Nouveau projet 9:16"), _("Instagram, Reels, Shorts, écran LED"), lambda: self.nouveau.emit("9:16")),
                                 ("importer", _("Rushes → projet"), _("Choisir des vidéos : PhilCut crée le projet et lance l'assistant"), self.importer_rushes.emit),
                                 ("ouvrir", _("Ouvrir un projet"), _("Un fichier .philcut"), self.ouvrir_dialogue.emit)):
            b = QPushButton(icone(ic, "#ffffff" if ic == "clap" else theme.COULEURS["texte"]), "  " + lib)
            b.setToolTip(aide)
            b.setIconSize(QSize(22, 22))
            b.setMinimumHeight(44)
            if ic == "clap":
                b.setProperty("primaire", True)
            b.clicked.connect(f)
            ha.addWidget(b)
        ha.addStretch(1)
        v.addLayout(ha)
        # ---- propositions (reprise, synchro)
        self.zone_prop = QVBoxLayout()
        v.addLayout(self.zone_prop)
        # ---- recents
        v.addWidget(QLabel(_("<b>Projets récents</b>")))
        self.liste = QListWidget()
        self.liste.setIconSize(QSize(96, 54))
        self.liste.setStyleSheet("QListWidget::item{padding:6px}")
        self.liste.itemActivated.connect(self._activer)
        self.liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._menu)
        self.liste.setMinimumHeight(220)
        v.addWidget(self.liste, 1)
        # ---- autres postes
        self.lbl_autres = QLabel("")
        self.lbl_autres.setWordWrap(True)
        self.lbl_autres.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
        v.addWidget(self.lbl_autres)
        self.astuce = QLabel(_("Astuce : glissez des vidéos sur la fenêtre pour créer un projet. Raccourcis : Espace lecture, C couper, Suppr supprimer, molette sur la timeline : zoom."))
        self.astuce.setWordWrap(True)
        self.astuce.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
        v.addWidget(self.astuce)
        zone.setWidget(corps)
        racine.addWidget(zone)
        self.rafraichir()

    def rafraichir(self, autres=None, ailleurs=None):
        """autres = [(machine, date, nb)] ; ailleurs = [(machine, date, fichiers)] : les projets ouverts sur les autres
        postes, ajoutés en gris à la liste (double-clic : PhilCut les cherche ici et les ouvre)."""
        if autres is not None:
            self._autres, self._ailleurs = autres, ailleurs or []
        autres, ailleurs = getattr(self, "_autres", None), getattr(self, "_ailleurs", [])
        self.liste.clear()
        dates = self.params.get("recents_dates") or {}
        from . import cloud_projets as CP
        for p in self.params.get("recents") or []:
            it = QListWidgetItem(os.path.splitext(os.path.basename(p))[0])
            d = dates.get(p, "")
            o = CP.origine(self.params, p)                     # 0.9.58 : projet d'un cloud (rouvert là-bas si besoin)
            absent = not os.path.exists(p) and not o
            if o:
                it.setToolTip(_("Sur {l} : {c}\nChaque Enregistrer l'y renvoie ; double-clic : ouvert (repris du cloud si besoin).",
                                l=o.get("lieu", ""), c=o.get("chemin", "")))
            else:
                it.setToolTip(p + ("\n" + _("Introuvable pour l'instant (disque, NAS ou Drive non branché ?)") if absent else ""))
            it.setData(Qt.UserRole, p)
            vign = p[:-8] + "_vignette.png" if p.lower().endswith(".philcut") else ""
            if vign and os.path.exists(vign):
                it.setIcon(QIcon(vign))
            else:
                it.setIcon(icone("projet", theme.COULEURS["desactive"] if absent else theme.COULEURS["accent"], 48))
            if absent:
                it.setForeground(Qt.gray)
            ou = ("☁ " + o.get("lieu", "") + " : " + (os.path.dirname(o.get("chemin", "")) or "/")) if o else os.path.dirname(p)
            it.setText(it.text() + (f"   —   {_date(d)}" if d else "") + f"\n{ou}")
            self.liste.addItem(it)
        deja = {os.path.normcase(os.path.abspath(p)) for p in self.params.get("recents") or []}
        for machine, dte, fichiers in ailleurs:
            for f in fichiers:
                p = f.get("chemin") or ""
                if not p.lower().endswith(".philcut") or os.path.normcase(os.path.abspath(p)) in deja:
                    continue
                deja.add(os.path.normcase(os.path.abspath(p)))
                nom = os.path.splitext(f.get("nom") or os.path.basename(p))[0]
                dist = f.get("distant") or {}
                ou = ("☁ " + dist.get("lieu", "") + " : " + (os.path.dirname(dist.get("chemin", "")) or "/")) if dist else os.path.dirname(p)
                it = QListWidgetItem(nom + "   —   " + _("ouvert sur « {m} » ({d})", m=machine, d=_date(dte)) + f"\n{ou}")
                it.setIcon(icone("projet", theme.COULEURS["desactive"], 48))
                it.setForeground(Qt.gray)
                it.setToolTip(_("Projet ouvert sur un autre poste. Double-clic : PhilCut le cherche sur ce poste "
                                "(même dossier, Drive, NAS…) et l'ouvre.") + "\n" + p)
                it.setData(Qt.UserRole, p)
                it.setData(Qt.UserRole + 1, (machine, f))
                self.liste.addItem(it)
        if not self.liste.count():                 # aucun projet encore : dire quoi faire plutôt qu'un cadre vide
            it = QListWidgetItem(_("Aucun projet pour l'instant. Pour commencer : « Nouveau projet 16:9 » (YouTube) ou « 9:16 » "
                                   "(Insta, écran LED), ou glissez vos vidéos sur cette fenêtre."))
            it.setFlags(Qt.NoItemFlags)
            it.setIcon(icone("info", theme.COULEURS["texte2"], 32))
            self.liste.addItem(it)
        self.liste.setWordWrap(True)
        if autres:
            self.lbl_autres.setText(_("Sur vos autres postes : ") + " · ".join(_("{m} ({n} projets, {d})", m=m, n=n, d=_date(dte)) for m, dte, n in autres))
        else:
            self.lbl_autres.setText("")

    def _activer(self, it):
        ailleurs = it.data(Qt.UserRole + 1)
        if ailleurs:
            self.reprendre.emit(ailleurs[0], [ailleurs[1]])
        elif it.data(Qt.UserRole):
            self.ouvrir.emit(it.data(Qt.UserRole))

    def proposer(self, texte, bouton, action, cle=None):
        """Une proposition non bloquante, laissee sur l'Accueil jusqu'a ce qu'on la traite ou la ferme."""
        f = QFrame()
        f.setStyleSheet("QFrame{background:%s;border:1px solid %s;border-radius:8px}" % (theme.COULEURS["surface"], theme.COULEURS["bord"]))
        h = QHBoxLayout(f)
        lb = QLabel(texte)
        lb.setWordWrap(True)
        lb.setStyleSheet("border:none;background:transparent")
        h.addWidget(lb, 1)
        b = QPushButton(bouton)
        b.setProperty("primaire", True)
        b.clicked.connect(lambda: (action(), f.deleteLater()))
        h.addWidget(b)
        x = QPushButton(_("Plus tard"))
        x.clicked.connect(f.deleteLater)
        h.addWidget(x)
        self.zone_prop.addWidget(f)

    def _menu(self, pos):
        it = self.liste.itemAt(pos)
        if not it:
            return
        p = it.data(Qt.UserRole)
        if not p:
            return
        m = QMenu(self)
        if it.data(Qt.UserRole + 1):
            machine, f = it.data(Qt.UserRole + 1)
            m.addAction(_("Chercher sur ce poste et ouvrir"), lambda: self.reprendre.emit(machine, [f]))
            m.exec(self.liste.mapToGlobal(pos))
            return
        m.addAction(_("Ouvrir"), lambda: self.ouvrir.emit(p))
        m.addAction(_("Montrer dans le dossier"), lambda: self.action_fichier.emit(p, "dossier"))
        m.addAction(_("Retirer de la liste"), lambda: self.action_fichier.emit(p, "retirer"))
        m.exec(self.liste.mapToGlobal(pos))


def _date(iso):
    try:
        d = datetime.datetime.fromisoformat(iso)
        return d.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return iso or ""
