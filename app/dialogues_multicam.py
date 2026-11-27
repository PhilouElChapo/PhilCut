"""Fenêtres du multicaméra (1.4.2) : caler les angles, puis la mosaïque qui suit la ligne rouge.

Caler : jusqu'à 4 rushes ; « Caler les angles » (son, sinon heure des fichiers) tourne sur ce poste, gratuit ; chaque
décalage reste modifiable à la main ; on choisit l'angle principal et la source son. Mosaïque : les 4 angles à la ligne
rouge ; un clic sur un angle, ou les touches 1 à 4, coupe à cet endroit et montre cet angle ; « Proposer les angles »
fait un premier montage sur ce poste. Chaque coupe est un plan normal (clic droit › « Changer d'angle »).
"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from . import multicam as MC
from .langue import _
from .taches import Tache, texte_erreur


def _methode(m):
    return {"son": _("par le son"), "heure": _("par l'heure des fichiers"), "main": _("à caler à la main")}.get(m, m)


class DialogueMulticam(QDialog):
    def __init__(self, ed, media_ids):
        super().__init__(ed)
        self.ed, self.projet = ed, ed.projet
        self.setWindowTitle(_("Multicaméra : caler les angles"))
        ms = [self.projet.media(i) for i in media_ids]
        ms = [m for m in ms if m and m.get("genre") == "video"]
        # angle principal d'office : le plus long (le plan multicaméra le montre au départ)
        self.medias = sorted(ms, key=lambda m: -float((m.get("fiche") or {}).get("duree") or 0))[:MC.MAX_ANGLES]
        self.angles = [{"media": m["id"], "nom": m.get("nom", ""), "decalage": 0.0, "methode": "main", "confiance": 0.0}
                       for m in self.medias]
        self.tache = None
        self.mc_id = None
        v = QVBoxLayout(self)
        aide = QLabel(_("Plusieurs caméras du même moment (4 au plus). PhilCut les cale entre elles par le son, sinon par l'heure "
                        "des fichiers ; vous pouvez corriger chaque décalage à la main. La première ligne est l'angle principal."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([_("Angle"), _("Rush"), _("Décalage (s)"), _("Calé")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        v.addWidget(self.table, 1)
        h = QHBoxLayout()
        b = QPushButton(_("Monter d'un rang"))
        b.setToolTip(_("La ligne choisie passe avant : la première est l'angle principal"))
        b.clicked.connect(self._monter)
        h.addWidget(b)
        h.addStretch(1)
        h.addWidget(QLabel(_("Son du film :")))
        self.son = QComboBox()
        self.son.setToolTip(_("Une seule source son court sous tous les angles (pas de saut de son à chaque coupe)"))
        h.addWidget(self.son, 1)
        v.addLayout(h)
        self.etat = QLabel(_("« Caler les angles » : sur ce poste, gratuit, quelques secondes à quelques minutes."))
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hb = QHBoxLayout()
        self.b_caler = QPushButton(_("Caler les angles"))
        self.b_caler.clicked.connect(self.caler)
        hb.addWidget(self.b_caler)
        hb.addStretch(1)
        self.b_creer = QPushButton(_("Créer le plan multicaméra"))
        self.b_creer.clicked.connect(self.creer)
        hb.addWidget(self.b_creer)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.reject)
        hb.addWidget(b)
        v.addLayout(hb)
        self._remplir()
        self.resize(720, 420)

    def _remplir(self):
        self.table.setRowCount(0)
        for k, a in enumerate(self.angles):
            self.table.insertRow(k)
            self.table.setItem(k, 0, QTableWidgetItem(str(k + 1)))
            self.table.setItem(k, 1, QTableWidgetItem(a["nom"]))
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 36000.0)
            sp.setDecimals(3)
            sp.setSingleStep(0.04)
            sp.setValue(a["decalage"])
            sp.setToolTip(_("Quand ce rush commence sur l'axe commun : augmentez-le si cet angle est en avance"))
            sp.valueChanged.connect(lambda val, k=k: self._decalage(k, val))
            self.table.setCellWidget(k, 2, sp)
            self.table.setItem(k, 3, QTableWidgetItem(_methode(a["methode"])))
            for c in (0, 1, 3):
                self.table.item(k, c).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        garde = self.son.currentData()
        self.son.clear()
        for a in self.angles:
            self.son.addItem(a["nom"], a["media"])
        self.son.setCurrentIndex(max(0, self.son.findData(garde)))
        self.b_creer.setEnabled(len(self.angles) >= 2)

    def _decalage(self, k, val):
        self.angles[k]["decalage"] = float(val)
        if self.angles[k]["methode"] != "main":
            self.angles[k]["methode"] = "main"
            self.table.item(k, 3).setText(_methode("main"))

    def _monter(self):
        k = self.table.currentRow()
        if k > 0:
            self.angles[k - 1], self.angles[k] = self.angles[k], self.angles[k - 1]
            self._remplir()
            self.table.selectRow(k - 1)

    def caler(self):
        if self.tache is not None and self.tache.isRunning():
            return
        medias = [self.projet.media(a["media"]) for a in self.angles]
        self.b_caler.setEnabled(False)
        self.tache = Tache(lambda t: MC.synchroniser(medias, lambda f, x="": t.avancer(f, x), lambda: t.arret),
                           _("Calage des angles"))
        self.tache.lier(self)
        self.tache.progression.connect(lambda f, x: self.etat.setText(f"{int(f * 100)} % — {x}"), Qt.QueuedConnection)
        self.tache.fini.connect(self._cale, Qt.QueuedConnection)
        if hasattr(self.ed, "encart"):
            self.ed.encart.suivre(self.tache, _("Calage des angles"))
        self.tache.start()

    def _cale(self, r, e):
        self.b_caler.setEnabled(True)
        if e or not r:
            self.etat.setText(_("✕ {e}", e=texte_erreur(e)) if e else "")
            return
        self.angles = r
        self._remplir()
        par_son = sum(1 for a in r if a["methode"] == "son")
        main = [a["nom"] for a in r if a["methode"] == "main"]
        self.etat.setText(_("✓ {n} angle(s) calé(s) par le son.", n=par_son) +
                          ((" " + _("A caler à la main : {l} (pas de son commun ni d'heure dans le fichier).", l=", ".join(main)))
                           if main else ""))

    def creer(self):
        if len(self.angles) < 2:
            return
        self.projet.marquer()
        self.mc_id = MC.creer(self.projet, self.angles, self.son.currentData())
        self.ed.rafraichir()
        self.ed.encart.message(_("Plan multicaméra posé. La mosaïque s'ouvre : cliquez un angle (ou touches 1 à 4) pendant la "
                                 "lecture pour couper. Edition › Annuler revient."), 10000)
        self.accept()
        if not getattr(self, "_test_sans_mosaique", False):
            self.ed.mosaique(self.mc_id)


class DialogueMosaique(QDialog):
    """Les 4 angles à la ligne rouge ; un clic (ou 1 à 4) coupe et montre cet angle à partir de là."""
    def __init__(self, ed, mc_id):
        super().__init__(ed)
        self.ed, self.projet, self.mc_id = ed, ed.projet, mc_id
        self.mc = self.projet.d["multicams"][mc_id]
        self.dossier = MC.dossier_images(self.projet, mc_id)
        self.tache = None
        self.setWindowTitle(_("Mosaïque multicaméra"))
        v = QVBoxLayout(self)
        g = QGridLayout()
        self.cases = []
        for k in range(MC.MAX_ANGLES):
            lb = QLabel()
            lb.setAlignment(Qt.AlignCenter)
            lb.setMinimumSize(240, 135)
            lb.setStyleSheet("background:#111;border:3px solid #222;color:#888")
            lb.setCursor(Qt.PointingHandCursor)
            if k < len(self.mc["angles"]):
                lb.setToolTip(_("Angle {n} : {r} — clic (ou touche {n}) : couper ici et montrer cet angle", n=k + 1,
                                r=self.mc["angles"][k]["nom"]))
                lb.mousePressEvent = lambda _e, k=k: self.couper(k)
            g.addWidget(lb, k // 2, k % 2)
            self.cases.append(lb)
        v.addLayout(g, 1)
        self.etat = QLabel(_("Lancez la lecture (Espace) et cliquez l'angle voulu au bon moment ; chaque coupe est un plan normal."))
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        h = QHBoxLayout()
        b = QPushButton(_("Proposer les angles"))
        b.setToolTip(_("Un premier montage sur ce poste, gratuit : des plans de 3 à 10 s, l'angle qui bouge le plus à chaque coupe ; "
                       "vous corrigez ensuite"))
        b.clicked.connect(self.proposer)
        h.addWidget(b)
        b = QPushButton(_("▶ / ❚❚"))
        b.setToolTip(_("Lecture / pause (Espace)"))
        b.clicked.connect(lambda: hasattr(self.ed, "lecture_auto") and self.ed.lecture_auto())
        h.addWidget(b)
        h.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        h.addWidget(b)
        v.addLayout(h)
        self.resize(560, 420)
        tl = getattr(ed, "timeline", None)
        if tl is not None:
            tl.position_changee.connect(self.afficher)
        if getattr(ed, "apercu", None) is not None:
            ed.apercu.position_changee.connect(self.afficher)
        self.preparer()

    def preparer(self):
        pj, mc_id = self.projet, self.mc_id
        self.tache = Tache(lambda t: MC.preparer_images(pj, mc_id, lambda f, x="": t.avancer(f, x), lambda: t.arret),
                           _("Images de la mosaïque"))
        self.tache.lier(self)
        self.tache.progression.connect(lambda f, x: self.etat.setText(_("Préparation de la mosaïque : {p} %", p=int(f * 100))),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, e: (self.etat.setText(_("✕ {e}", e=texte_erreur(e)) if e else _(
            "Prête : cliquez un angle (ou touches 1 à 4) pour couper à la ligne rouge.")), self.afficher()), Qt.QueuedConnection)
        if hasattr(self.ed, "encart"):
            self.ed.encart.suivre(self.tache, _("Images de la mosaïque"))
        self.tache.start()

    def _origine(self):
        c = next((x for x in self.projet.clips_piste("video") if x.get("multicam") == self.mc_id), None)
        return float((c or {}).get("origine_mc") or 0.0)

    def afficher(self, t=None):
        if not self.isVisible() and t is not None:
            return
        try:
            if t is None:
                t = float(self.ed.timeline.position)
        except (AttributeError, RuntimeError):
            return
        u = t - self._origine()
        c = next((x for x in self.projet.clips_piste("video") if x.get("multicam") == self.mc_id and
                  x["debut"] - 0.01 <= t < x["debut"] + (x["src_fin"] - x["src_debut"])), None)
        actif = int(c.get("angle") or 0) if c else -1
        for k, lb in enumerate(self.cases):
            if k >= len(self.mc["angles"]):
                lb.setText(_("(pas d'angle)"))
                continue
            ch = MC.image_a(self.dossier, self.mc, k, u)
            if ch:
                px = QPixmap(ch).scaled(lb.width() - 6, lb.height() - 6, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lb.setPixmap(px)
            else:
                lb.setPixmap(QPixmap())
                lb.setText(_("Angle {n} : pas d'image à ce moment", n=k + 1))
            lb.setStyleSheet("background:#111;border:3px solid %s;color:#888" % ("#ff3b3b" if k == actif else "#222"))

    def keyPressEvent(self, ev):
        k = ev.key() - Qt.Key_1
        if 0 <= k < len(self.mc["angles"]):
            self.couper(k)
            return
        if ev.key() == Qt.Key_Space and hasattr(self.ed, "lecture_auto"):
            self.ed.lecture_auto()
            return
        super().keyPressEvent(ev)

    def couper(self, k, t=None):
        if t is None:
            t = float(self.ed.timeline.position)
        self.projet.marquer()
        c = MC.couper_angle(self.projet, t, k)
        if c is None:
            self.projet.annuler()
            self.etat.setText(_("L'angle {n} n'a pas d'image à ce moment, ou la ligne rouge n'est pas sur le plan multicaméra.", n=k + 1))
            return False
        self.ed.rafraichir()
        self.etat.setText(_("Angle {n} à partir de {t} s.", n=k + 1, t=f"{t:.1f}"))
        self.afficher(t)
        return True

    def proposer(self):
        if self.tache is not None and self.tache.isRunning():
            self.etat.setText(_("Attendez la fin de la préparation de la mosaïque."))
            return
        if not getattr(self, "_test_oui", False) and QMessageBox.question(
                self, _("Proposer les angles"), _("Couper tout le plan multicaméra selon la proposition de l'assistant (l'angle qui "
                                                  "bouge le plus, plans de 3 à 10 s) ? Les coupes déjà faites sont remplacées. "
                                                  "Edition › Annuler revient.")) != QMessageBox.Yes:
            return
        self.projet.marquer()
        # repartir d'un seul plan : les coupes faites à la main sont refondues
        clips = [c for c in self.projet.clips_piste("video") if c.get("multicam") == self.mc_id]
        if len(clips) > 1:
            premier = clips[0]
            for c in clips[1:]:
                self.projet.retirer_clip(c["id"], refermer=False)
            MC.changer_angle(self.projet, premier, 0)
            a0 = self.mc["angles"][0]
            d0 = float((self.projet.media(a0["media"]).get("fiche") or {}).get("duree") or 0)
            premier.update(src_debut=0.0, src_fin=d0, debut=premier["origine_mc"] + a0["decalage"])
        n = MC.appliquer_proposition(self.projet, self.mc_id, MC.proposer(self.projet, self.mc_id, self.dossier))
        self.ed.rafraichir()
        self.etat.setText(_("{n} changement(s) d'angle proposé(s). Corrigez en cliquant un angle pendant la lecture.", n=n))
        self.afficher()
