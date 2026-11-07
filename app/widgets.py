"""Petits composants communs (repris de PhilCut) : disposition en flux, liste ordonnable, boutons en francais,
icone oeil des mots de passe, saisie d'un secret."""
import os
from PySide6.QtCore import Qt, QRect, QSize, QPoint, QObject, QEvent, QTimer, Signal
from PySide6.QtGui import QIcon, QAction, QColor, QPainter
from PySide6.QtWidgets import (QLayout, QWidget, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QVBoxLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton, QAbstractItemView, QWidgetItem)
from .icones import icone
from .langue import _


def boutons_fr(bb):
    """Libelles francais pour les boutons standard."""
    noms = {QDialogButtonBox.Ok: "OK", QDialogButtonBox.Cancel: _('Annuler'), QDialogButtonBox.Save: _('Enregistrer'),
            QDialogButtonBox.Discard: _('Ne pas enregistrer'), QDialogButtonBox.Close: _('Fermer'),
            QDialogButtonBox.Yes: "Oui", QDialogButtonBox.No: "Non", QDialogButtonBox.Apply: _('Appliquer')}
    for k, v in noms.items():
        b = bb.button(k)
        if b:
            b.setText(v)
    return bb


def question_fr(parent, titre, texte, boutons, defaut=None):
    """QMessageBox.question avec des boutons toujours en français (même si la traduction de Qt manque)."""
    from PySide6.QtWidgets import QMessageBox
    m = QMessageBox(QMessageBox.Question, titre, texte, boutons, parent)
    noms = {QMessageBox.Save: _("Enregistrer"), QMessageBox.Discard: _("Ne pas enregistrer"), QMessageBox.Cancel: _("Annuler"),
            QMessageBox.Yes: _("Oui"), QMessageBox.No: _("Non"), QMessageBox.Ok: "OK", QMessageBox.Close: _("Fermer")}
    for k, v in noms.items():
        b = m.button(k)
        if b:
            b.setText(v)
    if defaut is not None:
        m.setDefaultButton(defaut)
    return m.exec()


def installer_traduction_qt(app, langue):
    """Textes propres à Qt (Oui, Non, Annuler, Copier, Coller, boîtes de fichiers…) dans la langue de PhilCut."""
    import os, sys
    from PySide6.QtCore import QTranslator, QLibraryInfo
    dossiers = [QLibraryInfo.path(QLibraryInfo.TranslationsPath)]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        dossiers += [os.path.join(base, "PySide6", "Qt", "translations"), os.path.join(base, "PySide6", "translations")]
    tr = QTranslator(app)
    for d in dossiers:
        if d and tr.load(f"qtbase_{langue}", d):
            app.installTranslator(tr)
            app._traduction_qt = tr          # garder une référence
            return True
    return False


# ------------------------------------------------------------------ choix d'une zone

class FluxLayout(QLayout):
    """Disposition « en flux » : les elements vont a la ligne quand la place manque (barre d'outils sur plusieurs
    lignes quand la fenetre est etroite, au lieu d'icones cachees)."""

    def __init__(self, parent=None, marge=6, espace=2):
        super().__init__(parent)
        self._items = []
        self.droite = None                            # element colle a droite (volet), hors du flux
        self.setContentsMargins(marge, 2, marge, 2)
        self.setSpacing(espace)

    def addItem(self, item):
        self._items.append(item)

    def set_droite(self, w):
        from PySide6.QtWidgets import QWidgetItem
        if w is None:
            self.droite = None
        else:
            self.addChildWidget(w)
            self.droite = QWidgetItem(w)
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largeur):
        return self._placer(QRect(0, 0, largeur, 0), simuler=True)

    def setGeometry(self, r):
        super().setGeometry(r)
        self._placer(r, simuler=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        t = QSize()
        for it in self._items:
            t = t.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return t + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _placer(self, r, simuler):
        m = self.contentsMargins()
        zone = r.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, haut_ligne = zone.x(), zone.y(), 0
        e = self.spacing()
        bas_droite = zone.y()
        if self.droite is not None and not self.droite.widget().isHidden():
            td = self.droite.sizeHint()
            if not simuler:
                self.droite.setGeometry(QRect(QPoint(zone.right() - td.width() + 1, zone.y()), td))
            zone = zone.adjusted(0, 0, -(td.width() + e), 0)
            bas_droite = zone.y() + td.height()
        for it in self._items:
            if it.widget() is not None and it.widget().isHidden():
                continue
            t = it.sizeHint()
            if x + t.width() > zone.right() + 1 and haut_ligne > 0:
                x = zone.x()
                y += haut_ligne + e
                haut_ligne = 0
            if not simuler:
                it.setGeometry(QRect(QPoint(x, y), t))
            x += t.width() + e
            haut_ligne = max(haut_ligne, t.height())
        return max(y + haut_ligne, bas_droite) - r.y() + m.bottom()


def defilable(w):
    """Barre d'outils qui defile horizontalement quand la fenetre est etroite (au lieu d'empecher de la reduire)."""
    from PySide6.QtWidgets import QScrollArea, QFrame as _F
    z = QScrollArea()
    z.setWidget(w)
    z.setWidgetResizable(True)
    z.setFrameShape(_F.NoFrame)
    z.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    z.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    z.setStyleSheet("QScrollArea{background:transparent} QScrollBar:horizontal{height:6px}")

    def ajuster():
        z.setFixedHeight(w.sizeHint().height() + (8 if z.horizontalScrollBar().isVisible() else 0))
    z.horizontalScrollBar().rangeChanged.connect(lambda *_a: ajuster())
    ajuster()
    return z



class _SurveilleTaille(QObject):
    def __init__(self, w, rappel):
        super().__init__(w)
        self.rappel = rappel
        w.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() in (ev.Type.Resize, ev.Type.Show):
            QTimer.singleShot(0, self.rappel)
        return False



class _ListeOrdonnable(QListWidget):
    """Grille d'apercus que l'on reordonne en glissant un element a sa nouvelle place."""

    def __init__(self, rappel):
        super().__init__()
        self.rappel = rappel
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def place_depot(self, pos):
        """(index d'insertion, element voisin) pour un depot a cet endroit : sur un element, ou entre deux
        (l'element le plus proche ; a gauche de son milieu = avant lui, a droite = apres)."""
        if self.count() == 0:
            return 0, None
        proche, dmin = None, None
        for i in range(self.count()):
            r = self.visualItemRect(self.item(i))
            c = r.center()
            dist = (c.x() - pos.x()) ** 2 + ((c.y() - pos.y()) * 2) ** 2      # la rangee compte plus que la colonne
            if dmin is None or dist < dmin:
                proche, dmin = i, dist
        r = self.visualItemRect(self.item(proche))
        return (proche if pos.x() < r.center().x() else proche + 1), self.item(proche)

    # Qt refuse le depot quand la souris passe SUR un element (les elements ne sont pas « deposables ») : seul
    # l'espace vide en fin de liste acceptait. On accepte partout et on dessine nous-memes la barre d'insertion.
    def _interne(self, ev):
        return ev.source() is self or (ev.source() is None and
                                       ev.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"))

    def dragEnterEvent(self, ev):
        if self._interne(ev):
            ev.setDropAction(Qt.MoveAction)
            ev.accept()
        else:
            super().dragEnterEvent(ev)

    def dragMoveEvent(self, ev):
        if not self._interne(ev):
            return super().dragMoveEvent(ev)
        ev.setDropAction(Qt.MoveAction)
        ev.accept()
        self._barre = self._rect_barre(ev.position().toPoint())
        self.viewport().update()
        # defilement automatique pres des bords
        y, h = ev.position().y(), self.viewport().height()
        sb = self.verticalScrollBar()
        if y < 20:
            sb.setValue(sb.value() - 12)
        elif y > h - 20:
            sb.setValue(sb.value() + 12)

    def dragLeaveEvent(self, ev):
        self._barre = None
        self.viewport().update()
        super().dragLeaveEvent(ev)

    def _rect_barre(self, pos):
        """Barre verticale bleue la ou l'element sera insere."""
        i, _it = self.place_depot(pos)
        if self.count() == 0:
            return None
        if i < self.count():
            r = self.visualItemRect(self.item(i))
            x = r.left() - 3
        else:
            r = self.visualItemRect(self.item(self.count() - 1))
            x = r.right() + 3
        return QRect(x - 2, r.top() + 4, 4, r.height() - 8)

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if getattr(self, "_barre", None) is not None:
            p = QPainter(self.viewport())
            p.fillRect(self._barre, QColor("#1462c2"))
            p.end()

    def dropEvent(self, ev):
        self._barre = None
        self.viewport().update()
        if not self._interne(ev):
            return super().dropEvent(ev)
        src = self.currentRow()
        dst, it = self.place_depot(ev.position().toPoint())
        ev.setDropAction(Qt.IgnoreAction)
        ev.accept()
        if src < 0 or dst in (src, src + 1):
            return
        ids = [self.item(i).data(Qt.UserRole)["id"] for i in range(self.count())]
        x = ids.pop(src)
        ids.insert(dst - 1 if dst > src else dst, x)
        cat = (it.data(Qt.UserRole) or {}).get("categorie", "") if it is not None else None
        self.rappel(ids, x, cat)



def oeil(champ):
    """Champ de mot de passe masque, avec un oeil a droite pour l'afficher ou le masquer."""
    from .icones import icone
    from . import theme
    teinte = theme.COULEURS.get("texte2", "#888888")
    champ.setEchoMode(QLineEdit.Password)
    a = champ.addAction(icone("oeil", teinte), QLineEdit.TrailingPosition)
    a.setToolTip(_("Afficher le mot de passe"))

    def basculer():
        visible = champ.echoMode() == QLineEdit.Password
        champ.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        a.setIcon(icone("oeil_barre" if visible else "oeil", teinte))
        a.setToolTip(_("Masquer le mot de passe") if visible else _("Afficher le mot de passe"))
    a.triggered.connect(basculer)
    return champ


def demander_secret(parent, titre, texte, indice="", avec_indice=False):
    """Comme QInputDialog.getText en mode mot de passe, avec l'oeil et un indice eventuel. Renvoie (texte, ok) ;
    avec_indice (aucun indice encore) : un champ pour en ecrire un, renvoie (texte, ok, indice)."""
    d = QDialog(parent)
    d.setWindowTitle(titre)
    d.setMinimumWidth(420)
    v = QVBoxLayout(d)
    lb = QLabel(texte)
    lb.setWordWrap(True)
    v.addWidget(lb)
    if indice:
        li = QLabel(_("Indice : {indice}", indice=indice))
        li.setWordWrap(True)
        li.setStyleSheet("color:#8a5a00")
        v.addWidget(li)
    champ = oeil(QLineEdit())
    v.addWidget(champ)
    ind = None
    if avec_indice and not indice:
        li = QLabel(_("Indice pour vous souvenir du mot de passe principal (facultatif, enregistré en clair et envoyé à vos "
                      "autres postes ; jamais le mot de passe lui-même) :"))
        li.setWordWrap(True)
        li.setStyleSheet("color:#555;font-size:12px")
        v.addWidget(li)
        ind = QLineEdit()
        ind.setPlaceholderText(_("ex. « le code du carnet bleu »"))
        v.addWidget(ind)
    bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    v.addWidget(bb)
    champ.setFocus()
    ok = d.exec() == QDialog.Accepted
    if avec_indice:
        return champ.text(), ok, (ind.text().strip() if ind is not None else "")
    return champ.text(), ok



# ------------------------------------------------------------------ mise en page : jamais de défilement horizontal
class CaseLongue(QWidget):
    """Case à cocher dont le texte passe à la ligne (une QCheckBox ne sait pas le faire et élargit toute la fenêtre).
    Mêmes appels que QCheckBox : isChecked, setChecked, toggled, text, setText, setToolTip, setEnabled."""
    toggled = Signal(bool)

    def __init__(self, texte="", parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QCheckBox, QSizePolicy
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.case = QCheckBox()
        self.libelle = QLabel(texte)
        self.libelle.setWordWrap(True)
        self.libelle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.libelle.mousePressEvent = lambda e: self.case.isEnabled() and self.case.toggle()
        h.addWidget(self.case, 0, Qt.AlignTop)
        h.addWidget(self.libelle, 1)
        self.case.toggled.connect(self.toggled.emit)

    def isChecked(self):
        return self.case.isChecked()

    def setChecked(self, v):
        self.case.setChecked(bool(v))

    def text(self):
        return self.libelle.text()

    def setText(self, t):
        self.libelle.setText(t)

    def setToolTip(self, t):
        super().setToolTip(t)
        self.case.setToolTip(t)
        self.libelle.setToolTip(t)


def a_gauche(*widgets):
    """Boutons à leur taille, alignés à gauche (règle commune : pas de bouton étiré sur toute la largeur)."""
    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        h.addWidget(w)
    h.addStretch(1)
    return h


def page_a_largeur(zone):
    """Zone défilante qui suit la largeur de la fenêtre : défilement vertical seulement, textes repliés."""
    zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    w = zone.widget()
    if w is not None:
        for lbl in w.findChildren(QLabel):
            if not lbl.pixmap() or lbl.pixmap().isNull():
                lbl.setWordWrap(True)
    return zone


# ---------------------------------------------------------------------- choisir un fichier (0.9.14)
# Règle : la première fois, le dossier du système qui va avec (Images, Vidéos, Musique, Téléchargements, Documents) ;
# ensuite, le dernier dossier où l'utilisateur a pris un fichier de ce genre (retenu dans les réglages de ce poste).
CLEFS_DOSSIER = {"images": "dossier_images", "videos": "dossier_rushes", "musique": "dossier_musique_import",
                 "telechargements": "dossier_telechargements", "documents": "dossier_documents"}


def _params_de(parent):
    w = parent
    while w is not None:
        for nom in ("params",):
            p = getattr(w, nom, None)
            if p is not None and hasattr(p, "get"):
                return p
        ed = getattr(w, "ed", None)
        if ed is not None and hasattr(getattr(ed, "params", None), "get"):
            return ed.params
        w = w.parent() if hasattr(w, "parent") else None
    try:
        from .config import Parametres
        return Parametres()
    except Exception:      # noqa: BLE001
        return {}


def dossier_depart(parent, genre, params=None):
    from .session import dossier_systeme
    p = params if params is not None else _params_de(parent)
    d = p.get(CLEFS_DOSSIER.get(genre, "dossier_" + genre)) if p is not None else ""
    return d if d and os.path.isdir(d) else dossier_systeme(genre if genre != "telechargements" else "telechargements")


def retenir_dossier(parent, genre, chemin, params=None):
    p = params if params is not None else _params_de(parent)
    if p is None or not chemin:
        return
    p[CLEFS_DOSSIER.get(genre, "dossier_" + genre)] = os.path.dirname(chemin) if os.path.isfile(chemin) else chemin
    try:
        p.enregistrer()
    except AttributeError:
        pass


def ouvrir_fichier(parent, titre, filtre, genre="images", params=None):
    """Un fichier ; part du dossier du système (Images…) puis du dernier dossier utilisé pour ce genre."""
    from PySide6.QtWidgets import QFileDialog
    p, _f = QFileDialog.getOpenFileName(parent, titre, dossier_depart(parent, genre, params), filtre)
    if p:
        retenir_dossier(parent, genre, p, params)
    return p


def ouvrir_fichiers(parent, titre, filtre, genre="videos", params=None):
    from PySide6.QtWidgets import QFileDialog
    ps, _f = QFileDialog.getOpenFileNames(parent, titre, dossier_depart(parent, genre, params), filtre)
    if ps:
        retenir_dossier(parent, genre, ps[0], params)
    return ps
