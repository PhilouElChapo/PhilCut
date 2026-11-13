"""Fenêtre « Transitions automatiques » : PhilCut propose une transition par raccord, on coche, on change, on pose."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget)

from . import effets as E, transitions_auto as TA
from .langue import _
from .projet import fin_clip
from .taches import Tache
from .widgets import boutons_fr
from .taches import texte_erreur


def _tc(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


class DialogueTransitionsAuto(QDialog):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed = ed
        self.setWindowTitle(_("Transitions automatiques"))
        self.resize(720, 560)
        self.props, self.lignes, self.tache = [], [], None
        v = QVBoxLayout(self)
        aide = QLabel(_("PhilCut regarde chaque raccord : le mouvement de la caméra, la ressemblance des deux images et les temps forts "
                        "de la musique, puis propose une transition (ou une coupe franche quand elle serait de trop). Rien n'est posé "
                        "avant « Poser » ; tout s'annule d'un coup."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Style")))
        self.style = QComboBox()
        for k, lib in TA.STYLES.items():
            self.style.addItem(lib, k)
        self.style.setCurrentIndex(max(0, self.style.findData(ed.params.get("transitions_style") or "clean")))
        self.style.currentIndexChanged.connect(self.analyser)
        h.addWidget(self.style, 1)
        v.addLayout(h)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        self.zone = QScrollArea()
        self.zone.setWidgetResizable(True)
        self.zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.corps = QWidget()
        self.vc = QVBoxLayout(self.corps)
        self.vc.setAlignment(Qt.AlignTop)
        self.zone.setWidget(self.corps)
        v.addWidget(self.zone, 1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        self.b_ok = bb.button(QDialogButtonBox.Ok)
        self.b_ok.setText(_("Poser"))
        self.b_ok.setEnabled(False)
        bb.accepted.connect(self.poser)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.analyser()

    def analyser(self, *_a):
        style = self.style.currentData()
        self.ed.params["transitions_style"] = style
        self.etat.setText(_("Analyse des raccords…"))
        self.b_ok.setEnabled(False)
        projet = self.ed.projet
        self.tache = Tache(lambda t: TA.proposer(projet, style, progression=lambda f: t.avancer(f)), _("Transitions automatiques"))
        self.tache.fini.connect(self._resultat)
        self.tache.start()

    def _resultat(self, props, err):
        while self.vc.count():
            it = self.vc.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.lignes = []
        if err:
            self.etat.setText(_("✕ {e}", e=texte_erreur(err)))
            return
        self.props = props or []
        if not self.props:
            self.etat.setText(_("Aucun raccord : il faut au moins deux plans qui se suivent sur la piste Vidéo 1."))
            return
        n_tr = sum(1 for p in self.props if p["eid"])
        self.etat.setText(_("{n} raccord(s) : {t} transition(s) et {c} coupe(s) franche(s) proposées. Changez ou décochez ce que vous voulez.",
                            n=len(self.props), t=n_tr, c=len(self.props) - n_tr))
        transitions = [(k, v[1]) for k, v in E.CATALOGUE.items() if v[0] == "transition" and k in E.XFADE or k in ("t_choc", "t_glitch", "t_fondu_noir", "t_zoom")]
        for p in self.props:
            c = self.ed.projet.clip(p["clip"])
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(2, 2, 2, 2)
            cb = QCheckBox(_tc(c["debut"]) if c else "?")
            cb.setChecked(True)
            hl.addWidget(cb)
            co = QComboBox()
            co.addItem(_("Coupe franche"), None)
            for k, lib in transitions:
                co.addItem(lib, k)
            co.setCurrentIndex(max(0, co.findData(p["eid"])))
            hl.addWidget(co)
            lb = QLabel(p["raison"] + ("  ♪" if p.get("temps_fort") else ""))
            lb.setWordWrap(True)
            hl.addWidget(lb, 1)
            self.vc.addWidget(w)
            self.lignes.append((p, cb, co))
        self.b_ok.setEnabled(True)

    def poser(self):
        retenues = []
        for p, cb, co in self.lignes:
            if cb.isChecked():
                q = dict(p)
                if co.currentData() != p["eid"]:
                    q["eid"] = co.currentData()
                    q["duree"] = E.defauts(q["eid"]).get("duree", 0.5) if q["eid"] else 0.0
                retenues.append(q)
        n = TA.appliquer(self.ed.projet, retenues)
        self.ed.rafraichir()
        self.ed.encart.message(_("{n} raccord(s) traités. Edition › Annuler défait tout d'un coup.", n=n), 8000)
        self.accept()

    def done(self, r):
        if self.tache is not None and self.tache.isRunning():
            self.tache.wait(3000)
        super().done(r)
