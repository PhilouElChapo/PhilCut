"""Fenêtre « Transformer la voix » (0.9.75) : sur ce poste (hauteur, timbre, préréglages ; écoute immédiate) ou par l'IA
cloud (voix toute faite, plus naturelle, prix demandé, aperçu avant de poser)."""
import os
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QVBoxLayout)

from . import voix_transfo as VT
from .langue import _
from .taches import Tache, texte_erreur


class DialogueVoixTransfo(QDialog):
    def __init__(self, ed, clip):
        super().__init__(ed)
        self.ed, self.clip, self.tache, self.taches, self.resultat = ed, clip, None, [], None
        self.setWindowTitle(_("Transformer la voix de « {n} »", n=clip.get("nom", "")))
        self.resize(640, 560)
        v = QVBoxLayout(self)
        intro = QLabel(_("Sur ce poste, la voix change de hauteur et de timbre (gratuit, réglable, s'entend tout de suite ; un peu "
                         "artificiel si on force). Par l'IA cloud, elle est redite par une voix toute faite, avec vos intonations : "
                         "plus naturel, payant."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        # --- sur ce poste
        g = QGroupBox(_("Sur ce poste (gratuit)"))
        f = QFormLayout(g)
        self.preset = QComboBox()
        for k, (lib, _h, _t) in VT.PRESETS.items():
            self.preset.addItem(lib, k)
        self.preset.currentIndexChanged.connect(self._preset)
        f.addRow(_("Voix"), self.preset)
        tr = clip.get("voix_transfo") or {}
        self.hauteur = QDoubleSpinBox()
        self.hauteur.setRange(-12.0, 12.0)
        self.hauteur.setSingleStep(0.5)
        self.hauteur.setSuffix(" " + _("demi-tons"))
        self.hauteur.setValue(float(tr.get("hauteur", 0.0)))
        f.addRow(_("Hauteur"), self.hauteur)
        self.timbre = QDoubleSpinBox()
        self.timbre.setRange(-25.0, 30.0)
        self.timbre.setSingleStep(1.0)
        self.timbre.setSuffix(" %")
        self.timbre.setValue(round((float(tr.get("timbre", 1.0)) - 1.0) * 100, 1))
        self.timbre.setToolTip(_("Négatif : voix plus « grande », plus masculine ; positif : plus « petite », plus féminine"))
        f.addRow(_("Timbre"), self.timbre)
        hb = QHBoxLayout()
        b = QPushButton(_("▶ Ecouter"))
        b.clicked.connect(self.ecouter)
        hb.addWidget(b)
        b = QPushButton(_("Appliquer au plan"))
        b.setStyleSheet("font-weight:600")
        b.clicked.connect(self.appliquer)
        hb.addWidget(b)
        b = QPushButton(_("Retirer"))
        b.clicked.connect(self.retirer)
        hb.addWidget(b)
        hb.addStretch(1)
        f.addRow(hb)
        v.addWidget(g)
        # --- IA cloud
        gc = QGroupBox(_("IA cloud (plus naturel, votre clef fal.ai)"))
        fc = QFormLayout(gc)
        self.voix = QComboBox()
        for lib, k in VT.VOIX_CLOUD:
            self.voix.addItem(lib, k)
        fc.addRow(_("Nouvelle voix"), self.voix)
        self.debruiter = QCheckBox(_("Retirer aussi le bruit de fond"))
        self.debruiter.setChecked(True)
        fc.addRow(self.debruiter)
        self.accord = QCheckBox(_("La voix du plan est la mienne ou celle d'une personne d'accord"))
        self.accord.toggled.connect(lambda _v: self._maj())
        fc.addRow(self.accord)
        d = float(clip["src_fin"]) - float(clip["src_debut"])
        self.cout = QLabel(_("Environ {p} $ pour {d} s (0,30 $ la minute), demandé avant l'envoi.", p=f"{VT.prix_cloud(d):.2f}".replace(".", ","),
                             d=int(round(d))))
        self.cout.setWordWrap(True)
        fc.addRow(self.cout)
        from .credit_ia import LigneCredit
        fc.addRow(LigneCredit(ed.params, "fal"))
        hc = QHBoxLayout()
        self.b_cloud = QPushButton(_("Transformer par l'IA cloud"))
        self.b_cloud.clicked.connect(self.cloud)
        hc.addWidget(self.b_cloud)
        self.b_poser = QPushButton(_("Poser sur la piste Voix"))
        self.b_poser.setEnabled(False)
        self.b_poser.clicked.connect(self.poser)
        hc.addWidget(self.b_poser)
        hc.addStretch(1)
        fc.addRow(hc)
        v.addWidget(gc)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        self.apercu.hide()
        v.addWidget(self.apercu)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hf = QHBoxLayout()
        hf.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        hf.addWidget(b)
        v.addLayout(hf)
        self._maj()

    def _transfo(self):
        return {"hauteur": round(self.hauteur.value(), 2), "timbre": round(1.0 + self.timbre.value() / 100.0, 4)}

    def _preset(self, *_a):
        _lib, h, t = VT.PRESETS[self.preset.currentData()]
        self.hauteur.setValue(h)
        self.timbre.setValue(round((t - 1.0) * 100, 1))

    def _maj(self):
        from . import generateurs_video as GV
        ok = bool(GV.clef(self.ed.params, "fal"))
        self.b_cloud.setEnabled(ok and self.accord.isChecked() and not self._en_calcul())
        self.b_cloud.setToolTip("" if ok else _("Il faut une clef fal.ai : Préférences › IA › Connecter une IA."))

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    # ------------------------------------------------------------------ sur ce poste
    def ecouter(self):
        c = dict(self.clip, voix_transfo=self._transfo())
        self.ed.inspecteur.ecouter(c)

    def appliquer(self):
        self.ed.projet.marquer()
        t = self._transfo()
        if abs(t["hauteur"]) < 0.05 and abs(t["timbre"] - 1.0) < 0.005:
            self.clip.pop("voix_transfo", None)
        else:
            self.clip["voix_transfo"] = t
        self.ed.rafraichir()
        self.etat.setText(_("✓ Voix transformée sur le plan (rendue à l'export ; Ctrl+Z pour revenir)."))

    def retirer(self):
        self.ed.projet.marquer()
        self.clip.pop("voix_transfo", None)
        self.preset.setCurrentIndex(0)
        self.ed.rafraichir()
        self.etat.setText(_("Transformation retirée."))

    # ------------------------------------------------------------------ IA cloud
    def cloud(self):
        d = float(self.clip["src_fin"]) - float(self.clip["src_debut"])
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Transformer la voix"), _("Envoyer le son du plan ({d} s) à fal.ai pour qu'il soit redit par « {v} », environ "
                                                  "{p} $ sur votre compte ?", d=int(round(d)), v=self.voix.currentText(),
                                                  p=f"{VT.prix_cloud(d):.2f}".replace(".", ","))) != QMessageBox.Yes:
            return
        projet, clip, params, voix = self.ed.projet, dict(self.clip), self.ed.params, self.voix.currentData()
        t = Tache(lambda tc: VT.transformer_cloud(params, projet, clip, voix, self.debruiter.isChecked(), tc.avancer, tc.arret_demande),
                  _("Transformer la voix"))
        self.tache = t
        self.taches.append(t)
        from .widgets import suivre_en_fond
        suivre_en_fond(self, t, _("Voix transformée par l'IA cloud"))
        self.etat.setText(_("Envoi et transformation… (souvent moins d'une minute)"))
        t.progression.connect(lambda f, _t="": self.etat.setText(_("Envoi et transformation… (souvent moins d'une minute)") +
                                                                f" {int(f * 100)} %"), Qt.QueuedConnection)
        self._maj()

        def fin(r, e):
            self._maj()
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
                return
            self.resultat = r
            self.apercu.charger(r, video=False)
            self.apercu.show()
            self.b_poser.setEnabled(True)
            self.etat.setText(_("Ecoutez ; si elle convient, « Poser sur la piste Voix » (le son d'origine du plan est coupé)."))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def poser(self):
        if not self.resultat:
            return
        self.apercu.arreter()
        VT.poser_cloud(self.ed.projet, self.clip, self.resultat, _("Voix transformée — {v}", v=self.voix.currentData()))
        self.ed.biblio.remplir(self.ed.projet)
        self.ed.rafraichir()
        self.etat.setText(_("✓ Posée sur la piste Voix ; Ctrl+Z pour revenir."))
        self.b_poser.setEnabled(False)

    def done(self, r):
        from .widgets import garder_calcul
        if garder_calcul(self, self._en_calcul()):
            return
        self.apercu.arreter()
        super().done(r)
