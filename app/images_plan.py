"""Images tirées d'une vidéo du montage (0.9.29) : la dernière image d'un plan, ou plusieurs images choisies dans le plan,
pour une présentation de photos animée. Les images sont enregistrées en pleine définition dans le dossier des créations."""
import os
import tempfile
import time

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout

from . import moteur
from .langue import _


def extraire(projet, clip, temps_src):
    """Images du rush du plan aux instants donnés (temps du rush) ; renvoie leurs chemins (PNG pleine définition)."""
    from .creations import dossier
    m = projet.media(clip["media"]) or {}
    out = []
    for k, t in enumerate(temps_src):
        t = max(0.0, min(float(t), float(clip["src_fin"]) - 0.02))
        f = os.path.join(dossier(), f"image_{clip['id']}_{int(t * 1000)}_{time.strftime('%H%M%S')}_{k}.png")
        moteur.lancer(["-y", "-ss", f"{t:.3f}", "-i", m["chemin"], "-frames:v", "1", f])
        if not os.path.exists(f):                         # tout au bout : un peu avant
            moteur.lancer(["-y", "-ss", f"{max(0.0, t - 0.2):.3f}", "-i", m["chemin"], "-frames:v", "1", f])
        if os.path.exists(f):
            out.append(f)
    return out


class DialogueImagesPlan(QDialog):
    """Une planche d'images du plan ; on coche celles à garder (ou « Répartir » en coche N régulièrement)."""

    def __init__(self, parent, projet, clip, n=24):
        super().__init__(parent)
        self.projet, self.clip, self.choisies = projet, clip, []
        self.setWindowTitle(_("Images de « {n} »", n=clip.get("nom", "")))
        self.resize(820, 600)
        v = QVBoxLayout(self)
        t = QLabel(_("Cochez les images à mettre dans la présentation (un clic sur une image la coche ou la décoche)."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.liste = QListWidget()
        self.liste.setViewMode(QListView.IconMode)
        self.liste.setIconSize(QSize(176, 99))
        self.liste.setGridSize(QSize(190, 130))
        self.liste.setResizeMode(QListView.Adjust)
        self.liste.setMovement(QListView.Static)
        self.liste.itemClicked.connect(lambda it: it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked))
        v.addWidget(self.liste, 1)
        h = QHBoxLayout()
        self.nombre = QSpinBox()
        self.nombre.setRange(2, n)
        self.nombre.setValue(min(6, n))
        h.addWidget(QLabel(_("Nombre d'images")))
        h.addWidget(self.nombre)
        b_rep = QPushButton(_("Répartir sur tout le plan"))
        b_rep.clicked.connect(self.repartir)
        h.addWidget(b_rep)
        b_aucune = QPushButton(_("Tout décocher"))
        b_aucune.clicked.connect(lambda: [self.liste.item(i).setCheckState(Qt.Unchecked) for i in range(self.liste.count())])
        h.addWidget(b_aucune)
        h.addStretch(1)
        b_ok = QPushButton(_("Ajouter les images cochées"))
        b_ok.setDefault(True)
        b_ok.clicked.connect(self.valider)
        h.addWidget(b_ok)
        b_an = QPushButton(_("Annuler"))
        b_an.clicked.connect(self.reject)
        h.addWidget(b_an)
        v.addLayout(h)
        self._planche(n)

    def _planche(self, n):
        m = self.projet.media(self.clip["media"]) or {}
        a, b = float(self.clip["src_debut"]), float(self.clip["src_fin"])
        d = tempfile.mkdtemp(prefix="philcut-planche-")
        duree = max(0.1, b - a)
        moteur.lancer(["-y", "-ss", f"{a:.3f}", "-t", f"{duree:.3f}", "-i", m.get("chemin", ""), "-vf", f"fps={n / duree:.4f},scale=352:-2",
                       "-frames:v", str(n), os.path.join(d, "i%03d.png")])
        fichiers = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        for k, f in enumerate(fichiers):
            t = a + (k + 0.5) * duree / max(1, len(fichiers))
            it = QListWidgetItem(QIcon(QPixmap(os.path.join(d, f))), f"{t - a:.1f} s")
            it.setData(Qt.UserRole, t)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
            self.liste.addItem(it)
        if self.liste.count():
            self.nombre.setMaximum(self.liste.count())
            self.repartir()

    def repartir(self):
        n, tot = self.nombre.value(), self.liste.count()
        garder = {round(k * (tot - 1) / max(1, n - 1)) for k in range(n)} if tot else set()
        for i in range(tot):
            self.liste.item(i).setCheckState(Qt.Checked if i in garder else Qt.Unchecked)

    def valider(self):
        temps = [self.liste.item(i).data(Qt.UserRole) for i in range(self.liste.count()) if self.liste.item(i).checkState() == Qt.Checked]
        self.choisies = extraire(self.projet, self.clip, temps) if temps else []
        self.accept()
