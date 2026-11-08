"""Fenêtre « Présentation de photos animée » (0.9.27) : les photos (celles du projet, ou choisies), l'animation (avec une
vignette qui montre son mouvement), la durée par photo et le fond ; « Fabriquer », regarder, puis « Poser à la ligne
rouge » ou « Ranger dans ma bibliothèque »."""
import os
import time

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QListView, QListWidget,
                               QListWidgetItem, QProgressBar, QPushButton, QVBoxLayout)

from . import presentation as PR
from .langue import _
from .taches import Tache


class DialoguePresentation(QDialog):
    def __init__(self, ed, chemins=None):
        super().__init__(ed)
        self.ed, self.resultat, self.tache = ed, None, None
        self.setWindowTitle(_("Présentation de photos animée"))
        self.resize(820, 720)
        v = QVBoxLayout(self)
        t = QLabel(_("Une série de photos devient un clip animé : lancer de cartes, explosion en particules, puzzle, mur de photos… "
                     "Choisissez l'animation (la vignette bouge quand on la survole), fabriquez, regardez, puis posez-la."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.photos = list(chemins or [m["chemin"] for m in ed.projet.medias if m.get("genre") == "image" and os.path.exists(m.get("chemin", ""))])
        hp = QHBoxLayout()
        self.nb = QLabel("")
        hp.addWidget(self.nb, 1)
        b_ch = QPushButton(_("Choisir les photos…"))
        b_ch.clicked.connect(self._choisir)
        hp.addWidget(b_ch)
        v.addLayout(hp)
        self.styles = QListWidget()
        self.styles.setViewMode(QListView.IconMode)
        self.styles.setIconSize(QSize(176, 99))
        self.styles.setGridSize(QSize(196, 140))
        self.styles.setResizeMode(QListView.Adjust)
        self.styles.setMovement(QListView.Static)
        self.styles.setWordWrap(True)
        self.styles.setMouseTracking(True)
        self.styles.itemEntered.connect(self._survol)
        self.styles.currentItemChanged.connect(self._choisi)
        self.styles.setMinimumHeight(300)
        v.addWidget(self.styles, 1)
        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        v.addWidget(self.desc)
        f = QFormLayout()
        self.duree = QDoubleSpinBox()
        self.duree.setRange(0.8, 10.0)
        self.duree.setSingleStep(0.5)
        self.duree.setSuffix(_(" s par photo"))
        self.duree.setValue(float(ed.params.get("presentation_duree", 2.5)))
        self.duree.valueChanged.connect(self._maj_nb)
        f.addRow(_("Durée"), self.duree)
        self.fond = QComboBox()
        for k, lib in PR.FONDS.items():
            self.fond.addItem(lib, k)
        self.fond.setCurrentIndex(max(0, self.fond.findData(ed.params.get("presentation_fond", "flou"))))
        f.addRow(_("Fond"), self.fond)
        self.par_date = QCheckBox(_("Dans l'ordre de prise de vue (date des photos)"))
        self.par_date.setChecked(True)
        f.addRow(self.par_date)
        v.addLayout(f)
        h = QHBoxLayout()
        self.b_fabriquer = QPushButton(_("Fabriquer"))
        self.b_fabriquer.setDefault(True)
        self.b_fabriquer.clicked.connect(self.fabriquer)
        h.addWidget(self.b_fabriquer)
        self.b_poser = QPushButton(_("Poser à la ligne rouge"))
        self.b_poser.setEnabled(False)
        self.b_poser.clicked.connect(self.poser)
        h.addWidget(self.b_poser)
        self.b_ranger = QPushButton(_("Ranger dans ma bibliothèque"))
        self.b_ranger.setEnabled(False)
        self.b_ranger.clicked.connect(self.ranger)
        h.addWidget(self.b_ranger)
        h.addStretch(1)
        v.addLayout(h)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        self.apercu.hide()
        v.addWidget(self.apercu, 1)
        self._anim = QTimer(self)
        self._anim.timeout.connect(self._animer)
        self._anim_item, self._anim_t = None, 0.0
        self._remplir_styles()
        self._maj_nb()

    # ---- photos et vignettes
    def _exemples(self):
        return self.photos[:6] if self.photos else []

    def _remplir_styles(self):
        self.styles.clear()
        ex = self._exemples()
        from . import nouveautes as NV
        entrees = [(k, nom, desc, k, None, None) for k, (nom, desc) in PR.STYLES.items()]
        entrees += [(vid, ("✦ " if NV.est_nouveau(self.ed.params, "presentations", vid) else "") + v["nom"], v["desc"], v["style"], v["fond"],
                     v["options"]) for vid, v in PR.VARIANTES.items()]
        for k, nom, desc, style, fond, opts in entrees:
            it = QListWidgetItem(nom)
            it.setData(Qt.UserRole, k)
            it.setData(Qt.UserRole + 1, {"style": style, "fond": fond, "options": opts, "desc": desc})
            it.setToolTip(desc)
            if ex:
                try:
                    t = PR.duree_totale(len(ex), style, 1.5) * 0.45
                    it.setIcon(QIcon(QPixmap.fromImage(PR.apercu_image(ex, style, t, (176, 99), fond or (self.fond.currentData() if hasattr(self, "fond") else "flou"), 1.5))))
                except Exception:     # noqa: BLE001
                    pass
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            self.styles.addItem(it)
        i = list(PR.STYLES).index(self.ed.params.get("presentation_style", "cartes")) if self.ed.params.get("presentation_style") in PR.STYLES else 0
        self.styles.setCurrentRow(i)

    def _choisi(self, it, _avant=None):
        if not it:
            return
        e = it.data(Qt.UserRole + 1) or {}
        self.desc.setText(e.get("desc", ""))
        if e.get("fond") and hasattr(self, "fond"):
            self.fond.setCurrentIndex(max(0, self.fond.findData(e["fond"])))

    def _style(self, it=None):
        it = it or self.styles.currentItem()
        e = (it.data(Qt.UserRole + 1) if it else None) or {}
        return e.get("style") or "cartes", e.get("options")

    def _survol(self, it):
        if not self._exemples():
            return
        self._anim_item, self._anim_t = it, 0.0
        self._anim.start(90)

    def _animer(self):
        it = self._anim_item
        if it is None or not self.isVisible():
            self._anim.stop()
            return
        k, _o = self._style(it)
        ex = self._exemples()
        T = PR.duree_totale(len(ex), k, 1.5)
        self._anim_t = (self._anim_t + 0.18) % T
        try:
            it.setIcon(QIcon(QPixmap.fromImage(PR.apercu_image(ex, k, self._anim_t, (176, 99), self.fond.currentData(), 1.5))))
        except Exception:     # noqa: BLE001
            self._anim.stop()

    def _choisir(self):
        from .widgets import ouvrir_fichiers
        l = ouvrir_fichiers(self, _("Choisir les photos"), _("Images (*.jpg *.jpeg *.png *.webp *.bmp *.heic)"), "images", self.ed.params)
        if l:
            self.photos = l
            self._remplir_styles()
            self._maj_nb()

    def _maj_nb(self, *_a):
        k, _o = self._style() if hasattr(self, "styles") else ("cartes", None)
        n = len(self.photos)
        d = PR.duree_totale(n, k, self.duree.value()) if n else 0
        self.nb.setText(_("{n} photo(s) — clip d'environ {d:.0f} s", n=n, d=d) if n else
                        _("Aucune photo dans le projet : « Choisir les photos… »"))
        self.b_fabriquer.setEnabled(n >= 1)

    # ---- fabrication
    def fabriquer(self):
        it = self.styles.currentItem()
        if not it or not self.photos:
            return
        k, opts = self._style(it)
        p = self.ed.projet
        self.ed.params.update(presentation_style=k, presentation_duree=self.duree.value(), presentation_fond=self.fond.currentData())
        photos = PR.trier_par_date(self.photos) if self.par_date.isChecked() else list(self.photos)
        from .creations import dossier
        sortie = os.path.join(dossier(), f"presentation_{k}_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
        args = dict(style=k, duree_image=self.duree.value(), taille=p.taille, cadence=p.cadence, fond=self.fond.currentData(), options=opts)
        self.apercu.arreter()
        self.b_fabriquer.setEnabled(False)
        self.barre.setValue(0)
        self.barre.show()
        self.tache = Tache(lambda t: PR.fabriquer(photos, sortie, progression=t.avancer, arret=t.arret_demande, **args), _("Présentation de photos"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("Présentation de photos animée"))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)), Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self.tache.start()

    def _fini(self, r, err):
        try:
            self.b_fabriquer.setEnabled(True)
            self.barre.hide()
            if err:
                self.etat.setText(_("✕ Présentation impossible : {e}", e=str(err)[:300]))
                return
            self.resultat = r
            from . import creations
            it = self.styles.currentItem()
            creations.ecrire(r, {"famille": "presentation", "style": self._style(it)[0], "photos": self.photos,
                                 "duree": self.duree.value(), "fond": self.fond.currentData()})
            self.apercu.charger(r, video=True)
            self.apercu.show()
            self.b_poser.setEnabled(True)
            self.b_ranger.setEnabled(True)
            self.etat.setText(_("Regardez la présentation ; si elle convient, posez-la, sinon changez l'animation et refabriquez."))
        except RuntimeError:
            pass

    def poser(self):
        if not self.resultat:
            return None
        from . import prolonger
        self.apercu.arreter()
        p = self.ed.projet
        p.marquer()
        it = self.styles.currentItem()
        ci = prolonger.inserer(p, self.resultat, self.ed.timeline.position, "video",
                               _("Photos : {s}", s=PR.STYLES[self._style(it)[0]][0]))
        self.ed.biblio.remplir(p)
        self.ed.rafraichir()
        self.ed.encart.message(_("Présentation posée ; la suite est décalée (Ctrl+Z pour revenir)."), 6000)
        self.accept()
        return ci

    def ranger(self):
        from . import tampons as T
        it = self.styles.currentItem()
        T.ajouter_fichier(self.ed.params, self.resultat, _("Photos : {s}", s=PR.STYLES[self._style(it)[0]][0]))
        self.etat.setText(_("✓ Rangée dans « Ma bibliothèque » (Montage › Tampons vidéo)."))

    def done(self, r):
        self._anim.stop()
        self.apercu.arreter()
        super().done(r)
