"""Cartes de l'assistant (0.9.80) : la brique d'interface de la méthode « de l'idée au résultat » (assistant_idee.py),
réutilisable par les autres parties de PhilCut et par les autres logiciels PhilFactory.

- CarteElement : ce qui a été compris (pré-rempli, modifiable), d'où cela vient (toutes les sources, chacune expliquée, la
  conseillée cochée), les réglages de la source choisie, et ce qui manque encore (orange) ou ✓ (vert).
- ChampAmeliorable : un texte avec « ✨ Améliorer avec l'IA » ; la proposition est montrée à côté du texte de
  l'utilisateur, qui choisit (rien n'est remplacé sans son accord).
- ImageCadres : l'image du plan avec un cadre numéroté par personne ou objet ; cliquer ou tracer corrige le cadre de la
  carte active.
"""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QRadioButton,
                               QVBoxLayout, QWidget)

from .langue import _

VERT, ORANGE, GRIS = "#2fa36b", "#c98a00", "#9aa4b2"
COULEURS = ["#3b82f6", "#e5484d", "#2fa36b", "#c98a00", "#a855f7", "#0ea5e9", "#f97316", "#64748b"]


def vider(layout):
    """Retire tout d'une mise en page, sans que l'ancien contenu reste visible le temps de sa destruction."""
    while layout.count():
        it = layout.takeAt(0)
        w = it.widget()
        if w:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif it.layout():
            vider(it.layout())


def aide(texte, couleur=GRIS):
    lb = QLabel(texte)
    lb.setWordWrap(True)
    lb.setStyleSheet(f"color:{couleur}")
    return lb


def choisir_proposition(parent, ancien, neuf, pourquoi=""):
    """Votre texte / la proposition de l'IA, côte à côte ; renvoie le texte retenu (None = rien ne change)."""
    d = QDialog(parent)
    d.setWindowTitle(_("Proposition de l'IA"))
    v = QVBoxLayout(d)
    if pourquoi:
        v.addWidget(aide(pourquoi))
    h = QHBoxLayout()
    champs = []
    for titre, texte in ((_("Votre texte"), ancien), (_("Proposé par l'IA (modifiable)"), neuf)):
        b = QVBoxLayout()
        lb = QLabel(f"<b>{titre}</b>")
        b.addWidget(lb)
        t = QPlainTextEdit(texte)
        t.setMinimumWidth(300)
        b.addWidget(t, 1)
        h.addLayout(b, 1)
        champs.append(t)
    champs[0].setReadOnly(True)
    v.addLayout(h, 1)
    hb = QHBoxLayout()
    hb.addStretch(1)
    r = {}
    for lib, val, prim in ((_("Garder le mien"), None, False), (_("Prendre la proposition"), 1, True)):
        bt = QPushButton(lib)
        if prim:
            bt.setStyleSheet("font-weight:600")
        bt.clicked.connect(lambda _c=False, val=val: (r.update(v=val), d.accept()))
        hb.addWidget(bt)
    v.addLayout(hb)
    d.resize(760, 360)
    if getattr(parent, "_test_prendre", None) is not None:          # essais automatiques
        return neuf if parent._test_prendre else None
    d.exec()
    return champs[1].toPlainText().strip() if r.get("v") else None


class ChampAmeliorable(QWidget):
    """Un texte (une ligne ou plusieurs) et son bouton « ✨ Améliorer avec l'IA ». `ameliorer(champ)` est fourni par la
    fenêtre (elle sait quelle IA utiliser et suit le calcul)."""
    change = Signal()

    def __init__(self, texte="", quoi="idee", lignes=3, ameliorer=None, indication=""):
        super().__init__()
        self.quoi, self._ameliorer = quoi, ameliorer
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        if lignes == 1:
            self.t = QLineEdit(texte)
            self.t.textChanged.connect(lambda _x: self.change.emit())
        else:
            self.t = QPlainTextEdit(texte)
            if lignes > 0:
                self.t.setFixedHeight(22 * lignes + 12)
            self.t.textChanged.connect(self.change.emit)
        if indication:
            self.t.setPlaceholderText(indication)
        h.addWidget(self.t, 1)
        self.b = QPushButton(_("✨ Améliorer"))
        self.b.setToolTip(_("L'IA reformule pour qu'elle comprenne mieux, sans changer le sens ; vous voyez les deux textes et choisissez"))
        self.b.clicked.connect(lambda: self._ameliorer and self._ameliorer(self))
        self.b.setVisible(ameliorer is not None)
        h.addWidget(self.b, 0, Qt.AlignTop)

    def texte(self):
        return (self.t.text() if isinstance(self.t, QLineEdit) else self.t.toPlainText()).strip()

    def mettre(self, texte):
        self.t.blockSignals(True)
        (self.t.setText if isinstance(self.t, QLineEdit) else self.t.setPlainText)(texte or "")
        self.t.blockSignals(False)
        self.change.emit()


class CarteElement(QFrame):
    """Une carte : nom, description, sources possibles (radios expliquées), réglages de la source, ce qui manque.
    `options(carte, source)` rend le widget des réglages de la source (ou None) ; `manque(element)` le texte de ce qui
    manque (assistant_idee.manque) ; `ameliorer` comme ChampAmeliorable."""
    change = Signal()
    active = Signal(object)

    def __init__(self, element, sources, options=None, manque=None, ameliorer=None, couleur=None, retirer=None, titre_type="",
                 garder=None):
        super().__init__()
        self.e, self._options, self._manque = element, options, manque
        self.setFrameShape(QFrame.StyledPanel)
        self._couleur = couleur or COULEURS[0]
        self.setStyleSheet(f"CarteElement{{border:2px solid {self._couleur};border-radius:8px}}")
        v = QVBoxLayout(self)
        h = QHBoxLayout()
        self.pastille = QLabel("●")
        h.addWidget(self.pastille)
        if titre_type:
            h.addWidget(QLabel(f"<b>{titre_type}</b>"))
        self.nom = QLineEdit(element.get("nom", ""))
        self.nom.setToolTip(_("Le nom qui sert dans les plans ; jamais celui d'une personne réelle connue"))
        self.nom.textChanged.connect(self._modifie)
        h.addWidget(self.nom, 1)
        if garder:
            bg = QPushButton(_("☆ Garder"))
            bg.setToolTip(_("Ranger cet élément dans « Ma bibliothèque de créations » pour le réutiliser tel quel, ici et sur vos "
                            "autres postes"))
            bg.clicked.connect(lambda: garder(self))
            h.addWidget(bg)
        if retirer:
            b = QPushButton(_("Retirer"))
            b.clicked.connect(lambda: retirer(self))
            h.addWidget(b)
        v.addLayout(h)
        self.desc = ChampAmeliorable(element.get("description", ""), element.get("genre") or element.get("type", "idee"), 2, ameliorer,
                                     _("Ce qu'on doit voir ou entendre…"))
        self.desc.change.connect(self._modifie)
        v.addWidget(self.desc)
        v.addWidget(QLabel(_("D'où vient-il ?")))
        self.groupe = QButtonGroup(self)
        self.radios, self.zones = {}, {}
        for k, lib, expl in sources:
            r = QRadioButton(lib)
            r.setToolTip(expl)
            self.groupe.addButton(r)
            self.radios[k] = r
            v.addWidget(r)
            lb = aide(expl)
            lb.setContentsMargins(24, 0, 0, 0)
            v.addWidget(lb)
            z = QVBoxLayout()                       # les réglages de cette source, juste sous elle
            v.addLayout(z)
            self.zones[k] = z
            r.toggled.connect(lambda on, k=k: on and self._source(k))
        self.l_manque = QLabel("")
        self.l_manque.setWordWrap(True)
        v.addWidget(self.l_manque)
        if element.get("source") in self.radios:
            self.radios[element["source"]].setChecked(True)
        else:
            self._remplir_zone()
        self.maj()

    def mousePressEvent(self, e):
        self.active.emit(self)
        super().mousePressEvent(e)

    def _modifie(self, *_a):
        self.e["nom"] = self.nom.text().strip()
        self.e["description"] = self.desc.texte()
        self.maj()
        self.change.emit()

    def _source(self, k):
        self.e["source"] = k
        self._remplir_zone()
        self.active.emit(self)
        self.maj()
        self.change.emit()

    def _remplir_zone(self):
        for z in self.zones.values():
            vider(z)
        src = self.e.get("source", "")
        w = self._options(self, src) if self._options and src in self.zones else None
        if w is not None:
            self.zones[src].addWidget(w)

    def rafraichir(self):
        """Les réglages de la source refaits (après un fichier choisi, une analyse finie…)."""
        self._remplir_zone()
        self.maj()

    def maj(self):
        m = self._manque(self.e) if self._manque else ""
        self.pastille.setStyleSheet(f"color:{ORANGE if m else VERT};font-size:16px")
        self.l_manque.setText(("⚠ " + m) if m else ("✓ " + _("Complet")))
        self.l_manque.setStyleSheet(f"color:{ORANGE if m else VERT}")
        return not m

    def mettre_description(self, texte):
        self.desc.mettre(texte)


class ImageCadres(QLabel):
    """L'image avec les cadres numérotés ; un clic place un cadre de personne debout, un tracé le dessine exactement.
    `cadres` = [(numéro, couleur, [x0, y0, x1, y1])] ; le cadre corrigé est rendu par le signal `trace(liste)`."""
    trace = Signal(list)

    def __init__(self, chemin, largeur=420):
        super().__init__()
        self.pix = QPixmap(chemin) if chemin else QPixmap()
        self.cadres, self.actif, self._depart, self._courant = [], -1, None, None
        if not self.pix.isNull():
            self.pix = self.pix.scaled(largeur, int(largeur * 1.2), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setFixedSize(self.pix.size())
        self.setCursor(Qt.CrossCursor)
        self.setToolTip(_("Cliquez la personne ou l'objet de la carte choisie, ou tracez son cadre"))

    def _frac(self, p):
        return max(0.0, min(1.0, p.x() / max(1, self.width()))), max(0.0, min(1.0, p.y() / max(1, self.height())))

    def mousePressEvent(self, e):
        self._depart = self._frac(e.position())
        self._courant = None

    def mouseMoveEvent(self, e):
        if self._depart:
            self._courant = self._frac(e.position())
            self.update()

    def mouseReleaseEvent(self, e):
        if not self._depart:
            return
        a, b = self._depart, self._frac(e.position())
        self._depart, self._courant = None, None
        if abs(a[0] - b[0]) > 0.03 and abs(a[1] - b[1]) > 0.03:
            self.trace.emit([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])])
        else:
            from .assistant_creation import boite_autour
            self.trace.emit(boite_autour(*b))
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        if not self.pix.isNull():
            p.drawPixmap(0, 0, self.pix)
        w, h = self.width(), self.height()
        f = QFont()
        f.setBold(True)
        p.setFont(f)
        for k, (num, coul, b) in enumerate(self.cadres):
            if not b:
                continue
            pen = QPen(QColor(coul), 4 if k == self.actif else 2)
            if k != self.actif:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            r = QRectF(b[0] * w, b[1] * h, (b[2] - b[0]) * w, (b[3] - b[1]) * h)
            p.drawRect(r)
            p.fillRect(QRectF(r.left(), r.top(), 22, 20), QColor(coul))
            p.setPen(QColor("white"))
            p.drawText(QRectF(r.left(), r.top(), 22, 20), Qt.AlignCenter, str(num))
        if self._depart and self._courant:
            p.setPen(QPen(QColor("white"), 1, Qt.DashLine))
            a, b = self._depart, self._courant
            p.drawRect(QRectF(QPointF(a[0] * w, a[1] * h), QPointF(b[0] * w, b[1] * h)))
        p.end()
