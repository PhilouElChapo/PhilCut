"""Fabrique musique (0.9.37) et Musique en ligne : fenêtres communes à PhilCut et PhilMusic.

Elles ne dépendent pas du montage : PhilCut leur passe un « hôte » (poser dans le film, garder dans les médias,
remplacer un morceau) ; PhilMusic passera le sien (ouvrir dans l'éditeur audio). Sans hôte, le morceau est enregistré.
"""
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
                               QSlider, QSpinBox, QVBoxLayout, QWidget)

from . import musique_ia as MI
from .langue import _
from .taches import Tache

ALERTE = _("Le morceau reste sur ce poste : rien n'est envoyé. PhilCut n'en garde que le style (tempo, tonalité, instruments, ambiance, "
           "déroulé) ; la mélodie et les paroles ne sont jamais recopiées. Une voix de chanteur ou de personne connue n'est jamais "
           "reproduite : sa manière de chanter est seulement décrite. Pour réorchestrer le morceau lui-même, il doit être libre de droits "
           "ou à vous.")


class Hote:
    """Ce que la fenêtre peut faire du morceau créé ; chaque logiciel fournit le sien (None : enregistrer seulement)."""
    poser = None              # poser(chemin, reglages, a_la_ligne_rouge)
    garder = None             # garder(chemin) : dans les médias / la bibliothèque
    remplacer = None          # remplacer(chemin, reglages) : à la place du morceau repris


def _dossier_sorties():
    from .creations import dossier
    return dossier()


class DialogueFabriqueMusique(QDialog):
    def __init__(self, parent, params, hote=None, fiche=None, duree=None):
        super().__init__(parent)
        self.params, self.hote = params, hote or Hote()
        self.tache, self.resultat, self.inspiration, self._taches = None, None, None, []
        self.setWindowTitle(_("Fabrique musique (sur ce poste)"))
        self.resize(1000, 800)
        v = QVBoxLayout(self)
        aide = QLabel(_("Décrivez la musique avec la fiche : chaque réglage rend la consigne plus précise. « Améliorer avec l'IA » la "
                        "réécrit comme un producteur. « S'inspirer d'un morceau » reprend le style d'un morceau. La musique est créée sur "
                        "ce poste, gratuitement."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        corps = QWidget()
        vc = QVBoxLayout(corps)
        zone.setWidget(corps)
        v.addWidget(zone, 1)
        # --- style
        g = QGroupBox(_("Style et ambiance"))
        f = QFormLayout(g)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.famille = QComboBox()
        self.famille.addItem(_("Tous les styles"), "")
        for k, lib in MI.FAMILLES.items():
            self.famille.addItem(lib, k)
        self.style = QComboBox()
        self.famille.currentIndexChanged.connect(self._remplir_styles)
        hs = QHBoxLayout()
        hs.addWidget(self.famille)
        hs.addWidget(self.style, 1)
        f.addRow(_("Style"), hs)
        self.ambiance = QComboBox()
        for k, lib in MI.AMBIANCES:
            self.ambiance.addItem(lib, k)
        f.addRow(_("Ambiance"), self.ambiance)
        self.phrase = QPlainTextEdit()
        self.phrase.setMaximumHeight(56)
        self.phrase.setPlaceholderText(_("En plus, avec vos mots : « une valse triste sous la pluie », « chanté à la manière de Sinatra »…"))
        hp = QHBoxLayout()
        hp.addWidget(self.phrase, 1)
        b = QPushButton(_("Style « à la manière de »…"))
        b.setToolTip(_("Un chanteur, un groupe, un compositeur : son style est décrit au moteur, jamais son nom ni sa voix exacte"))
        b.clicked.connect(self._choisir_style)
        hp.addWidget(b, 0, Qt.AlignTop)
        f.addRow(_("Phrase"), hp)
        self.style_info = QLabel("")
        self.style_info.setWordWrap(True)
        self.style_info.setStyleSheet("color:#9ad0ff")
        self.style_info.hide()
        f.addRow(self.style_info)
        vc.addWidget(g)
        # --- fiche
        g = QGroupBox(_("Fiche musicale (laisser « auto » : le moteur choisit)"))
        f = QFormLayout(g)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.tempo = QSpinBox()
        self.tempo.setRange(0, 220)
        self.tempo.setSpecialValueText(_("Auto (selon le style)"))
        self.tempo.setSuffix(_(" battements par minute"))
        f.addRow(_("Tempo"), self.tempo)
        self.tonalite = QComboBox()
        for t in MI.TONALITES:
            self.tonalite.addItem(MI.tonalite_fr(t) if t else _("Auto (selon le style)"), t)
        self.mesure = QComboBox()
        for m in MI.MESURES:
            self.mesure.addItem(m or _("Auto"), m)
        ht = QHBoxLayout()
        ht.addWidget(self.tonalite, 1)
        ht.addWidget(QLabel(_("Mesure")))
        ht.addWidget(self.mesure)
        f.addRow(_("Tonalité"), ht)
        self.instruments = QLineEdit()
        self.instruments.setPlaceholderText(_("ex. : violoncelle, piano, cor"))
        f.addRow(_("Instruments"), self.instruments)
        self.structure = QComboBox()
        for k, lib in MI.STRUCTURES:
            self.structure.addItem(lib, k)
        f.addRow(_("Déroulé"), self.structure)
        self.epoque = QLineEdit()
        self.epoque.setPlaceholderText(_("ex. : son de gramophone des années 30, enregistrement de concert, studio moderne"))
        f.addRow(_("Epoque, son"), self.epoque)
        self.duree = QDoubleSpinBox()
        self.duree.setRange(10, 240)
        self.duree.setSuffix(" s")
        self.duree.setValue(float(duree or 60))
        f.addRow(_("Durée"), self.duree)
        self.instrumental = QCheckBox(_("Sans paroles"))
        self.instrumental.setChecked(True)
        self.voix = QComboBox()
        for k, (lib, _en) in MI.voix_disponibles().items():
            self.voix.addItem(lib, k)
        from . import paroles as PA
        self.langue = QComboBox()
        for k, lib in PA.LANGUES.items():
            self.langue.addItem(lib, k)
        from .langue import LANGUE
        self.langue.setCurrentIndex(max(0, self.langue.findData(LANGUE)))
        hv = QHBoxLayout()
        hv.addWidget(self.instrumental)
        hv.addWidget(self.voix, 1)
        hv.addWidget(self.langue)
        f.addRow(_("Voix"), hv)
        self.paroles = QPlainTextEdit()
        self.paroles.setMaximumHeight(110)
        self.paroles.setPlaceholderText(_("Paroles : tapez-les, ou seulement le début, puis « Écrire les paroles par l'IA ». Balises "
                                          "possibles : [verse] couplet, [chorus] refrain, [bridge], [outro]."))
        self.b_paroles = QPushButton(_("Écrire les paroles par l'IA (thème + début)"))
        self.b_paroles.clicked.connect(self._ecrire_paroles)
        self.niveau_paroles = self._choix_niveau()
        hpa = QHBoxLayout()
        hpa.addWidget(self.niveau_paroles)
        hpa.addWidget(self.b_paroles)
        hpa.addStretch(1)
        self.boite_paroles = QWidget()
        vp = QVBoxLayout(self.boite_paroles)
        vp.setContentsMargins(0, 0, 0, 0)
        vp.addWidget(self.paroles)
        vp.addLayout(hpa)
        f.addRow(self.boite_paroles)
        self.instrumental.toggled.connect(self._bascule_paroles)
        vc.addWidget(g)
        # --- s'inspirer d'un morceau
        g = QGroupBox(_("S'inspirer d'un morceau"))
        vi = QVBoxLayout(g)
        hi = QHBoxLayout()
        b = QPushButton(_("Choisir un morceau…"))
        b.clicked.connect(self._choisir_inspiration)
        hi.addWidget(b)
        self.b_sans_insp = QPushButton(_("Ne plus s'en inspirer"))
        self.b_sans_insp.clicked.connect(self._sans_inspiration)
        self.b_sans_insp.hide()
        hi.addWidget(self.b_sans_insp)
        hi.addStretch(1)
        vi.addLayout(hi)
        self.insp_info = QLabel(_("Aucun morceau choisi."))
        self.insp_info.setWordWrap(True)
        self.insp_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vi.addWidget(self.insp_info)
        alerte = QLabel(ALERTE)
        alerte.setWordWrap(True)
        alerte.setStyleSheet("color:#c98a00")
        vi.addWidget(alerte)
        self.partir = QCheckBox(_("Partir de ce morceau (le réorchestrer dans le style choisi) — morceau libre de droits ou à vous"))
        self.partir.setEnabled(False)
        self.partir.toggled.connect(self._maj)
        vi.addWidget(self.partir)
        hf = QHBoxLayout()
        hf.addWidget(QLabel(_("Proche du morceau")))
        self.proximite = QSlider(Qt.Horizontal)
        self.proximite.setRange(5, 100)
        self.proximite.setValue(50)
        hf.addWidget(self.proximite, 1)
        hf.addWidget(QLabel(_("Libre")))
        self.fidele = QCheckBox(_("Garder sa structure de près"))
        hf.addWidget(self.fidele)
        self.boite_partir = QWidget()
        self.boite_partir.setLayout(hf)
        self.boite_partir.setEnabled(False)
        vi.addWidget(self.boite_partir)
        self.b_declarer = QPushButton(_("Ce morceau est libre de droits ou à moi…"))
        self.b_declarer.clicked.connect(self._declarer_libre)
        self.b_declarer.hide()
        vi.addWidget(self.b_declarer, 0, Qt.AlignLeft)
        vc.addWidget(g)
        # --- voix de référence
        g = QGroupBox(_("Voix de référence (facultatif)"))
        vr = QVBoxLayout(g)
        t = QLabel(_("Un enregistrement de votre voix, ou de celle d'une personne qui est d'accord : le moteur s'en sert comme timbre. "
                     "Jamais la voix d'un chanteur ou d'une personne connue."))
        t.setWordWrap(True)
        vr.addWidget(t)
        hr = QHBoxLayout()
        b = QPushButton(_("Choisir l'enregistrement…"))
        b.clicked.connect(self._choisir_reference)
        hr.addWidget(b)
        self.b_sans_ref = QPushButton(_("Sans voix de référence"))
        self.b_sans_ref.clicked.connect(lambda: (setattr(self, "reference", None), self._maj()))
        hr.addWidget(self.b_sans_ref)
        hr.addStretch(1)
        vr.addLayout(hr)
        self.ref_info = QLabel("")
        self.ref_info.setWordWrap(True)
        vr.addWidget(self.ref_info)
        self.reference = None
        vc.addWidget(g)
        # --- consigne
        g = QGroupBox(_("Consigne envoyée au moteur (en anglais)"))
        vg = QVBoxLayout(g)
        self.apercu_consigne = QLabel("")
        self.apercu_consigne.setWordWrap(True)
        self.apercu_consigne.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.apercu_consigne.setStyleSheet("color:#9aa4b2")
        vg.addWidget(self.apercu_consigne)
        ha = QHBoxLayout()
        self.niveau_ia = self._choix_niveau()
        ha.addWidget(self.niveau_ia)
        self.b_ameliorer = QPushButton(_("Améliorer avec l'IA"))
        self.b_ameliorer.setToolTip(_("L'IA réécrit la fiche en une consigne de producteur (instruments et leur rôle, rythme, harmonie, "
                                      "déroulé, son) ; vous la relisez avant de créer. Rien n'est envoyé sans ce clic."))
        self.b_ameliorer.clicked.connect(self._ameliorer)
        ha.addWidget(self.b_ameliorer)
        ha.addStretch(1)
        vg.addLayout(ha)
        self.utiliser_ia = QCheckBox(_("Utiliser la consigne améliorée (modifiable)"))
        self.utiliser_ia.hide()
        self.utiliser_ia.toggled.connect(self._maj)
        vg.addWidget(self.utiliser_ia)
        self.consigne_ia = QPlainTextEdit()
        self.consigne_ia.setMaximumHeight(90)
        self.consigne_ia.hide()
        self.consigne_ia.textChanged.connect(self._maj)
        vg.addWidget(self.consigne_ia)
        vc.addWidget(g)
        vc.addStretch(1)
        # --- bas : créer, avancement, écoute, actions
        self.info = QLabel("")
        self.info.setWordWrap(True)
        v.addWidget(self.info)
        self.etape = QLabel("")
        self.etape.setWordWrap(True)
        self.etape.hide()
        v.addWidget(self.etape)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        from .widgets import SuiviAttente
        self.suivi = SuiviAttente()
        v.addWidget(self.suivi)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        self.apercu.hide()
        v.addWidget(self.apercu)
        hb = QHBoxLayout()
        self.b_creer = QPushButton(_("Créer la musique"))
        self.b_creer.setStyleSheet("font-weight:600;padding:6px 18px")
        self.b_creer.clicked.connect(self.creer)
        hb.addWidget(self.b_creer)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.hide()
        self.b_arreter.clicked.connect(lambda: self.tache and self.tache.stopper())
        hb.addWidget(self.b_arreter)
        self.actions = QHBoxLayout()
        hb.addLayout(self.actions)
        hb.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.reject)
        hb.addWidget(b)
        v.addLayout(hb)
        self._horloge = QTimer(self)
        self._horloge.setInterval(1000)
        self._horloge.timeout.connect(self._tic)
        for w in (self.style, self.ambiance, self.tonalite, self.mesure, self.structure, self.voix):
            w.currentIndexChanged.connect(self._maj)
        for w in (self.tempo, self.duree):
            w.valueChanged.connect(self._maj)
        for w in (self.instruments, self.epoque):
            w.textChanged.connect(self._maj)
        self.phrase.textChanged.connect(self._maj)
        self.instrumental.toggled.connect(self._maj)
        self._remplir_styles()
        self._bascule_paroles(True)
        if fiche:
            self.appliquer_fiche(fiche)
        self._maj()

    # ---- petits outils
    def _choix_niveau(self):
        """Pour écrire (consigne, paroles) : Claude d'abord, le meilleur pour cela ; Gemini ou l'IA locale au choix."""
        c = QComboBox()
        from . import ia
        clefs = {m for m, _k in ia.moteurs(dict(self.params, ia_moteur="claude"))}
        if "claude" in clefs:
            c.addItem(_("Claude (cloud, le meilleur pour écrire)"), "claude")
        if "gemini" in clefs:
            c.addItem(_("Gemini (cloud)"), "gemini")
        c.addItem(_("IA locale (sur ce poste, gratuit)"), "locale")
        voulu = self.params.get("musique_ia_ecrire") or ("claude" if "claude" in clefs else "locale")
        c.setCurrentIndex(max(0, c.findData(voulu)))
        c.currentIndexChanged.connect(lambda _i: self.params.__setitem__("musique_ia_ecrire", c.currentData()))
        return c

    def _remplir_styles(self, *_a):
        fam = self.famille.currentData() or ""
        actuel = self.style.currentData()
        self.style.blockSignals(True)
        self.style.clear()
        for s in MI.STYLES:
            if not fam or s[2] == fam:
                self.style.addItem(s[1] if fam else f"{s[1]}  ·  {MI.FAMILLES[s[2]]}", s[0])
        i = self.style.findData(actuel)
        self.style.setCurrentIndex(max(0, i))
        self.style.blockSignals(False)
        self._maj()

    def _bascule_paroles(self, sans):
        self.boite_paroles.setVisible(not sans)
        self.voix.setEnabled(not sans)
        self.langue.setEnabled(not sans)

    def fiche(self):
        f = MI.fiche_vide()
        f.update(style=self.style.currentData() or "pop_aerienne", ambiance=self.ambiance.currentData() or "", phrase=self.phrase.toPlainText().strip(),
                 tempo=self.tempo.value(), tonalite=self.tonalite.currentData() or "", mesure=self.mesure.currentData() or "",
                 instruments=self.instruments.text().strip(), structure=self.structure.currentData() or "", voix=self.voix.currentData() or "auto",
                 epoque=self.epoque.text().strip(), duree=self.duree.value(), instrumental=self.instrumental.isChecked(),
                 paroles=self.paroles.toPlainText(), langue=self.langue.currentData() or "fr", inspiration=self.inspiration,
                 consigne_ia=self.consigne_ia.toPlainText().strip(), utiliser_ia=self.utiliser_ia.isChecked() and self.utiliser_ia.isVisible())
        if self.inspiration and self.partir.isChecked():
            f["source"] = {"chemin": self.inspiration.get("chemin"), "force": self.proximite.value() / 100, "fidele": self.fidele.isChecked()}
        if self.reference:
            f["voix_reference"] = {"chemin": self.reference}
        return f

    def appliquer_fiche(self, f):
        f = dict(MI.fiche_vide(), **(f or {}))
        st = MI._STYLE.get(f["style"])
        if st:
            self.famille.setCurrentIndex(0)
            self.style.setCurrentIndex(max(0, self.style.findData(f["style"])))
        for w, k in ((self.ambiance, "ambiance"), (self.tonalite, "tonalite"), (self.mesure, "mesure"), (self.structure, "structure"),
                     (self.voix, "voix"), (self.langue, "langue")):
            w.setCurrentIndex(max(0, w.findData(f.get(k) or "")))
        self.phrase.setPlainText(f.get("phrase") or "")
        self.tempo.setValue(int(f.get("tempo") or 0))
        self.instruments.setText(f.get("instruments") or "")
        self.epoque.setText(f.get("epoque") or "")
        self.duree.setValue(float(f.get("duree") or 60))
        self.instrumental.setChecked(bool(f.get("instrumental", True)))
        self.paroles.setPlainText(f.get("paroles") or "")
        if f.get("consigne_ia"):
            self.consigne_ia.setPlainText(f["consigne_ia"])
            self.consigne_ia.show()
            self.utiliser_ia.show()
            self.utiliser_ia.setChecked(bool(f.get("utiliser_ia")))
        if f.get("inspiration"):
            self._montrer_inspiration(dict(f["inspiration"]))

    def _maj(self, *_a):
        f = self.fiche()
        c = MI.consigne(f, self.params)
        reglages = [f"{c['bpm']} bpm" if c["bpm"] else "", MI.tonalite_fr(c["keyscale"]), c["mesure"]]
        texte = c["caption"] + "\n" + " · ".join(x for x in reglages if x)
        if f.get("phrase") or f.get("instruments") or f.get("epoque"):
            texte += "\n" + _("(vos mots sont traduits en anglais au moment de créer)")
        if f.get("source"):
            texte += "\n" + _("Réorchestration du morceau « {n} », proximité {p} %.", n=os.path.basename(f["source"]["chemin"] or ""),
                              p=int(100 - self.proximite.value() + 5))
        self.apercu_consigne.setText(texte)
        lignes = [_("🎭 « {n} » → {d}", n=n, d=d) for n, d in c["styles"]]
        if c["inconnus"]:
            lignes.append(_("❓ Style inconnu : {n}. Décrivez-le (voix, orchestre, époque) ou « Améliorer avec l'IA ».", n=", ".join(c["inconnus"])))
        if c["styles"]:
            lignes.append(_("Le nom n'est pas envoyé au moteur : seule cette description l'est."))
        self.style_info.setText("\n".join(lignes))
        self.style_info.setVisible(bool(lignes))
        self.boite_partir.setEnabled(self.partir.isChecked())
        if self.reference:
            self.ref_info.setText(_("Voix de référence : {f}", f=os.path.basename(self.reference)))
        else:
            self.ref_info.setText(_("Aucune : le moteur choisit la voix décrite par la fiche."))
        self.b_sans_ref.setVisible(bool(self.reference))

    def _choisir_style(self):
        from .dialogues_creatif import choisir_style
        nom = choisir_style(self, self.params, "musique")
        if nom:
            p = self.phrase.toPlainText().rstrip(" ,")
            self.phrase.setPlainText((p + ", " if p else "") + _("chanté à la manière de") + " " + nom)

    # ---- tâches courtes (suivi d'attente)
    def _lancer(self, travail, titre, quoi, conseil, fin):
        t = Tache(travail, titre)
        self._taches.append(t)
        self.suivi.demarrer(quoi, t, conseil)

        def fini(r, err):
            try:
                self.suivi.finir()
                fin(r, err)
            except RuntimeError:          # fenêtre fermée entre-temps
                pass
        t.fini.connect(fini, Qt.QueuedConnection)
        t.start()
        return t

    def _ecrire_paroles(self):
        from . import paroles as PA
        niveau = self.niveau_paroles.currentData()
        if niveau != "locale":
            from . import ia
            if not _avec_moteur(niveau, lambda: ia.confirmer_cout(self, self.params, 1500, 0, _("Paroles de chanson"))):
                return
        theme = self.phrase.toPlainText().strip() or self.style.currentText()
        args = (theme, self.paroles.toPlainText(), self.langue.currentData(), self.voix.currentData(), self.duree.value(), self.params, niveau)
        self.b_paroles.setEnabled(False)

        def fin(r, err):
            self.b_paroles.setEnabled(True)
            if err:
                self.info.setText(_("✕ Paroles non écrites : {e}", e=str(err)[:300]))
                return
            self.paroles.setPlainText(r)
            self.info.setText(_("Paroles écrites : relisez-les, modifiez-les si besoin, puis « Créer la musique »."))
        self._lancer(lambda t: _avec_moteur(niveau, lambda: PA.ecrire(*args[:-1], "locale" if niveau == "locale" else "cloud")), _("Paroles"), _("L'IA écrit les paroles"),
                     _("IA locale : le modèle démarre d'abord, puis écrit.") if niveau == "locale" else _("IA cloud : quelques secondes."), fin)

    def _ameliorer(self):
        niveau = self.niveau_ia.currentData()
        if niveau != "locale":
            from . import ia
            if not _avec_moteur(niveau, lambda: ia.confirmer_cout(self, self.params, 900, 0, _("Améliorer la consigne musicale"))):
                return
        fiche, params = self.fiche(), self.params
        from . import traduction_recherche as TR
        traduire = lambda x: TR.phrase_en_anglais(x)[0]
        self.b_ameliorer.setEnabled(False)

        def fin(r, err):
            self.b_ameliorer.setEnabled(True)
            if err or not r or not r.get("caption"):
                self.info.setText(_("✕ Consigne non améliorée : {e}", e=str(err or _("réponse vide"))[:300]))
                return
            self.consigne_ia.setPlainText(r["caption"])
            self.consigne_ia.show()
            self.utiliser_ia.show()
            self.utiliser_ia.setChecked(True)
            if r.get("bpm") and not self.tempo.value():
                self.tempo.setValue(r["bpm"])
            if r.get("keyscale") and not self.tonalite.currentData():
                i = self.tonalite.findData(r["keyscale"])
                if i >= 0:
                    self.tonalite.setCurrentIndex(i)
            self.info.setText(_("Consigne améliorée : relisez-la (vous pouvez la modifier), puis « Créer la musique »."))
        self._lancer(lambda t: _avec_moteur(niveau, lambda: MI.ameliorer(fiche, params, "locale" if niveau == "locale" else "cloud", traduire)),
                     _("Consigne"), _("L'IA améliore la consigne"),
                     _("IA locale : le modèle démarre d'abord, puis écrit.") if niveau == "locale" else _("IA cloud : quelques secondes."), fin)

    # ---- inspiration
    def _choisir_inspiration(self):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Morceau dont s'inspirer"), _("Sons") + " (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.mp4 *.mkv *.webm)",
                            "musique", self.params)
        if not ch:
            return
        params = self.params

        def fin(r, err):
            if err:
                if not isinstance(err, InterruptedError):
                    self.info.setText(_("✕ Analyse impossible : {e}", e=str(err)[:300]))
                return
            r["chemin"] = ch
            self._montrer_inspiration(r, appliquer=True)
        self._lancer(lambda t: MI.analyser(ch, params, t.avancer, lambda: t.arret), _("Analyse"),
                     _("Analyse de « {n} » sur ce poste", n=os.path.basename(ch)),
                     _("Quelques secondes ; plus si le moteur de musique écoute aussi le genre et les instruments."), fin)

    def _montrer_inspiration(self, r, appliquer=False):
        self.inspiration = r
        resume = r.get("resume") or ""
        txt = _("« {n} » : {r}.", n=r.get("fichier") or os.path.basename(r.get("chemin") or ""), r=resume)
        if r.get("compris"):
            txt += "\n" + _("Le moteur de musique l'a aussi écouté : {c}", c=r.get("caption_en", "")[:300])
        txt += "\n" + _("Ce style est ajouté à la consigne ; le tempo, la tonalité et la mesure aussi, si vous les laissez sur « auto ».")
        self.insp_info.setText(txt)
        self.b_sans_insp.show()
        ch = r.get("chemin") or ""
        libre = bool(ch and os.path.exists(ch) and MI.peut_partir_de(ch))
        self.partir.setEnabled(libre)
        if not libre:
            self.partir.setChecked(False)
        self.b_declarer.setVisible(bool(ch and os.path.exists(ch)) and not libre)
        self._maj()

    def _sans_inspiration(self):
        self.inspiration = None
        self.partir.setChecked(False)
        self.partir.setEnabled(False)
        self.b_declarer.hide()
        self.b_sans_insp.hide()
        self.insp_info.setText(_("Aucun morceau choisi."))
        self._maj()

    def _declarer_libre(self):
        from .musique_en_ligne import LEGAL_MUSIQUE
        ch = (self.inspiration or {}).get("chemin")
        if not ch:
            return
        d = QMessageBox(self)
        d.setWindowTitle(_("Morceau libre de droits ou à vous"))
        d.setTextFormat(Qt.RichText)
        d.setText(LEGAL_MUSIQUE + "<br><br>" + _("Ce morceau (l'œuvre <b>et</b> cet enregistrement) est-il libre de droits, ou à vous ?"))
        b_libre = d.addButton(_("Libre de droits"), QMessageBox.AcceptRole)
        b_moi = d.addButton(_("C'est le mien"), QMessageBox.AcceptRole)
        d.addButton(_("Non, m'en inspirer seulement"), QMessageBox.RejectRole)
        d.exec()
        if d.clickedButton() is b_libre:
            MI.declarer(ch, libre=True)
        elif d.clickedButton() is b_moi:
            MI.declarer(ch, a_moi=True)
        else:
            return
        self._montrer_inspiration(self.inspiration)
        self.partir.setChecked(True)

    def _choisir_reference(self):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Enregistrement de la voix"), _("Sons") + " (*.mp3 *.wav *.flac *.ogg *.m4a)", "musique", self.params)
        if not ch:
            return
        d = MI.droits(ch)
        if not (d.get("voix_a_moi") or d.get("voix_accord")):
            m = QMessageBox(self)
            m.setWindowTitle(_("Voix de référence"))
            m.setText(_("De qui est cette voix ? PhilCut ne reproduit que votre voix, ou celle d'une personne qui vous a donné son accord. "
                        "Jamais un chanteur ou une personne connue : pour cela, décrivez sa manière de chanter (« à la manière de »)."))
            b_moi = m.addButton(_("C'est ma voix"), QMessageBox.AcceptRole)
            b_acc = m.addButton(_("Une personne d'accord"), QMessageBox.AcceptRole)
            m.addButton(_("Annuler"), QMessageBox.RejectRole)
            m.exec()
            if m.clickedButton() is b_moi:
                MI.declarer(ch, voix_a_moi=True)
            elif m.clickedButton() is b_acc:
                MI.declarer(ch, voix_accord=True)
            else:
                return
        self.reference = ch
        self._maj()

    # ---- création
    def creer(self):
        if self.tache is not None and self.tache.isRunning():
            return
        fiche, params = self.fiche(), self.params
        horo = time.strftime("%Y%m%d_%H%M%S")
        sortie = os.path.join(_dossier_sorties(), f"musique_{horo}.mp3")
        from . import traduction_recherche as TR

        def travail(t):
            def traduire(x):
                en, comment, manque = TR.phrase_en_anglais(x)
                if manque and comment != "service":
                    raise RuntimeError(_("Pas de traduction pour « {m} » (pas de réseau ?) : écrivez ces mots en anglais.",
                                         m=", ".join(dict.fromkeys(manque))))
                return en
            t.avancer(0.0, _("Préparation de la consigne…"))
            return MI.creer(fiche, sortie, params, t.avancer, lambda: t.arret, traduire)
        self.tache = Tache(travail, _("Fabrique musique"))
        self.tache.progression.connect(self._progression, Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, e, fiche=fiche: self._fini(fiche, r, e), Qt.QueuedConnection)
        self._vider_actions()
        self.apercu.arreter()
        self.apercu.hide()
        self.b_creer.setEnabled(False)
        self.b_arreter.show()
        self.info.setText(_("Création en cours sur ce poste… vous pouvez continuer à travailler."))
        self._t0 = time.monotonic()
        self._fraction, self._texte = 0.0, _("Préparation…")
        self.etape.setText(self._texte)
        self.etape.show()
        self.barre.setValue(0)
        self.barre.show()
        self._horloge.start()
        self.tache.start()

    def _progression(self, f, texte):
        self._fraction = max(0.0, min(1.0, f))
        if texte:
            self._texte = texte
        self.barre.setValue(int(self._fraction * 1000))
        self._tic()

    def _tic(self):
        e = time.monotonic() - getattr(self, "_t0", time.monotonic())
        txt = f"{self._texte} — " + _("écoulé {e}", e=_hms(e))
        if 0.05 < self._fraction < 0.995:
            txt += " · " + _("reste environ {r}", r=_hms(e / self._fraction - e))
        elif self._fraction >= 0.995:
            txt += " · " + _("la barre est pleine : le moteur termine et enregistre le morceau")
        self.etape.setText(txt)

    def _vider_actions(self):
        while self.actions.count():
            w = self.actions.takeAt(0).widget()
            if w:
                w.deleteLater()

    def _action(self, texte, fn):
        b = QPushButton(texte)
        b.clicked.connect(fn)
        self.actions.addWidget(b)

    def _fini(self, fiche, r, err):
        self._horloge.stop()
        self.b_creer.setEnabled(True)
        self.b_arreter.hide()
        self.barre.hide()
        self.etape.hide()
        if err:
            if isinstance(err, InterruptedError) or getattr(self.tache, "arret", False):
                self.info.setText(_("Création arrêtée."))
            else:
                self.info.setText(_("✕ La création n'a pas abouti : {e}", e=str(err)[:600]))
            return
        chemin, c = r
        self.resultat = chemin
        from . import creations
        creations.ecrire(chemin, MI.recette(fiche, c))
        self.info.setText(_("Musique créée. Écoutez-la, gardez le passage voulu, puis choisissez :"))
        self.apercu.charger(chemin, video=False)
        self.apercu.show()
        h = self.hote
        if h.poser:
            self._action(_("Poser sous la vidéo"), lambda: self._poser(False))
            self._action(_("Poser à la ligne rouge"), lambda: self._poser(True))
        if h.garder:
            self._action(_("Garder sans poser"), lambda: (h.garder(self.resultat), self.info.setText(_("Gardée dans les médias, sans être posée."))))
        if h.remplacer:
            self._action(_("Remplacer le morceau d'origine"), lambda: (self.apercu.arreter(), h.remplacer(self.resultat, self.apercu.reglages()),
                                                                      self.info.setText(_("✓ Remplacé (Annuler pour revenir à l'ancien)."))))
        self._action(_("Enregistrer sous…"), self._enregistrer_sous)
        self._action(_("Recréer"), self.creer)

    def _poser(self, a_la_ligne):
        r = self.apercu.reglages()
        self.apercu.arreter()
        self.hote.poser(self.resultat, r, a_la_ligne)
        self.info.setText(_("Morceau posé ({d:.1f} s) sur la piste Musique.", d=r["src_fin"] - r["src_debut"]))

    def _enregistrer_sous(self):
        from .dialogues_creatif import enregistrer_copie
        c = enregistrer_copie(self, self.resultat, self.params)
        if c:
            self.info.setText(_("✓ Copie enregistrée : {f}", f=c))

    def done(self, r):
        self.apercu.arreter()
        for t in self._taches:
            if t.isRunning():
                t.stopper()
        if self.tache is not None and self.tache.isRunning():
            self.info.setText(_("La création continue en tâche de fond."))
        super().done(r)


def _avec_moteur(niveau, fn):
    """Le temps d'une demande, l'IA cloud choisie (Claude ou Gemini) passe avant celle des Préférences."""
    from . import ia
    ancien = ia.MOTEUR_FORCE
    ia.MOTEUR_FORCE = niveau if niveau in ("claude", "gemini") else ancien
    try:
        return fn()
    finally:
        ia.MOTEUR_FORCE = ancien


def _hms(s):
    s = int(max(0, s))
    return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


# ------------------------------------------------------------------ musique en ligne
class DialogueMusiqueEnLigne(QDialog):
    """Chercher, écouter, télécharger un son (YouTube Music, YouTube, archives libres), avec ce qui est permis expliqué."""

    def __init__(self, parent, params, poser=None):
        super().__init__(parent)
        from . import musique_en_ligne as ML, musiques
        self.params, self.poser, self.ML = params, poser, ML
        self.resultats, self._taches, self.lecteur, self.dernier = [], [], None, None
        self.setWindowTitle(_("Musique en ligne"))
        self.resize(940, 680)
        v = QVBoxLayout(self)
        legal = QLabel(ML.LEGAL_MUSIQUE)
        legal.setWordWrap(True)
        legal.setTextFormat(Qt.RichText)
        legal.setStyleSheet("color:#c98a00")
        v.addWidget(legal)
        h = QHBoxLayout()
        self.source = QComboBox()
        for k, lib in ML.SOURCES:
            self.source.addItem(lib, k)
        self.source.setCurrentIndex(max(0, self.source.findData(params.get("musique_en_ligne_source") or "ytmusic")))
        h.addWidget(self.source)
        self.texte = QLineEdit()
        self.texte.setPlaceholderText(_("ex. : Dies irae chant grégorien, Requiem Mozart 1937, valse musette"))
        self.texte.returnPressed.connect(self.chercher)
        h.addWidget(self.texte, 1)
        b = QPushButton(_("Chercher"))
        b.clicked.connect(self.chercher)
        h.addWidget(b)
        v.addLayout(h)
        self.liste = QListWidget()
        self.liste.setWordWrap(True)
        self.liste.itemDoubleClicked.connect(lambda _it: self.ecouter())
        v.addWidget(self.liste, 1)
        # lecture : ce qui est lu, où on en est, et choisir le passage
        self.lu = QLabel("")
        self.lu.setWordWrap(True)
        self.lu.setStyleSheet("color:#9ad0ff")
        v.addWidget(self.lu)
        hl = QHBoxLayout()
        self.position = QSlider(Qt.Horizontal)
        self.position.setRange(0, 0)
        self.position.setEnabled(False)
        self.position.sliderMoved.connect(lambda ms: self.lecteur and self.lecteur.setPosition(ms))
        hl.addWidget(self.position, 1)
        self.temps = QLabel("0:00 / 0:00")
        hl.addWidget(self.temps)
        v.addLayout(hl)
        self.avert = QLabel("")
        self.avert.setWordWrap(True)
        self.avert.setStyleSheet("color:#c98a00")
        self.avert.hide()
        v.addWidget(self.avert)
        self.libre = QCheckBox(_("Ce morceau est libre de droits (domaine public, licence libre ou accord) : je pourrai aussi le réorchestrer"))
        v.addWidget(self.libre)
        self.dossier = musiques.dossier(params)
        self.lbl_dossier = QLabel(_("Enregistré dans : {d}", d=self.dossier))
        self.lbl_dossier.setWordWrap(True)
        v.addWidget(self.lbl_dossier)
        from .widgets import SuiviAttente
        self.suivi = SuiviAttente()
        v.addWidget(self.suivi)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        v.addWidget(self.info)
        hb = QHBoxLayout()
        self.b_installer = QPushButton(_("Installer yt-dlp (programme officiel)…"))
        self.b_installer.clicked.connect(self.installer)
        hb.addWidget(self.b_installer)
        self.b_maj = QPushButton(_("Mettre à jour yt-dlp"))
        self.b_maj.setToolTip(_("Télécharge la dernière version de yt-dlp et de Deno (programmes officiels) : à faire quand YouTube refuse "
                                "la lecture ou le téléchargement."))
        self.b_maj.clicked.connect(self.installer)
        hb.addWidget(self.b_maj)
        self.b_ecouter = QPushButton("▶ " + _("Écouter"))
        self.b_ecouter.clicked.connect(self.ecouter)
        hb.addWidget(self.b_ecouter)
        self.b_telecharger = QPushButton(_("Télécharger"))
        self.b_telecharger.clicked.connect(self.telecharger)
        hb.addWidget(self.b_telecharger)
        self.b_poser = QPushButton(_("Poser dans le film"))
        self.b_poser.clicked.connect(lambda: self.dernier and self.poser and self.poser(self.dernier))
        self.b_poser.setVisible(poser is not None)
        self.b_poser.setEnabled(False)
        hb.addWidget(self.b_poser)
        hb.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.reject)
        hb.addWidget(b)
        v.addLayout(hb)
        self.source.currentIndexChanged.connect(self._maj)
        self.liste.currentRowChanged.connect(self._choisi)
        self._maj()

    def _ytdlp(self):
        from . import videos_en_ligne as VL
        return VL.ytdlp_installe()

    def _maj(self, *_a):
        src = self.source.currentData()
        self.params["musique_en_ligne_source"] = src
        besoin = src != "archive" and not self._ytdlp()
        self.b_installer.setVisible(besoin)
        self.b_maj.setVisible(src != "archive" and not besoin)
        if besoin:
            self.info.setText(_("YouTube et YouTube Music passent par yt-dlp, le programme officiel : « Installer yt-dlp » le télécharge "
                                "depuis son dépôt GitHub (une fois)."))

    def _accord(self):
        if self.params.get("musique_en_ligne_ok"):
            return True
        r = QMessageBox.question(self, _("Musique en ligne"), self.ML.CONFIRMATION)
        if r == QMessageBox.Yes:
            self.params["musique_en_ligne_ok"] = True
            return True
        return False

    def _lancer(self, travail, titre, quoi, fin, barre=False):
        t = Tache(travail, titre)
        self._taches.append(t)
        if barre:
            self.barre.setValue(0)
            self.barre.show()
            t.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.info.setText(txt)), Qt.QueuedConnection)
        self.suivi.demarrer(quoi, t)

        def fini(r, err):
            try:
                self.suivi.finir()
                self.barre.hide()
                fin(r, err)
            except RuntimeError:
                pass
        t.fini.connect(fini, Qt.QueuedConnection)
        t.start()

    def installer(self):
        from . import videos_en_ligne as VL

        def travail(t):
            VL.installer_ytdlp(t.avancer, lambda: t.arret)
            try:
                VL.installer_deno(t.avancer, lambda: t.arret)
            except Exception:      # noqa: BLE001 : Deno n'est utile que pour certaines vidéos
                pass
        self._lancer(travail, _("yt-dlp"), _("Installation de yt-dlp"), lambda r, e: (self.info.setText(("✕ " + str(e)) if e else
                                                                                                       _("yt-dlp est installé.")), self._maj()), True)

    def chercher(self):
        texte = self.texte.text().strip()
        if not texte:
            return
        src = self.source.currentData()
        if src != "archive" and not self._ytdlp():
            self._maj()
            return
        ML = self.ML

        def fin(r, err):
            if err:
                self.info.setText(_("✕ Recherche impossible : {e}", e=str(err)[:300]))
                return
            self.resultats = r or []
            self.liste.clear()
            for x in self.resultats:
                d = int(x.get("duree") or 0)
                duree = f"{d // 60}:{d % 60:02d}" if d else ""
                lic = (" · " + _("licence annoncée : {l}", l=x["licence"][:60])) if x.get("licence") else ""
                details = "  ·  ".join(y for y in (x.get("artiste", ""), x.get("album", ""), x.get("annee", ""), duree) if y)
                it = QListWidgetItem(f"{x.get('titre', '')}\n{details or _('(artiste inconnu)')}{lic}")
                self.liste.addItem(it)
            if self.resultats:
                info = _("{n} résultat(s). Double-clic pour écouter.", n=len(self.resultats))
                if src == "archive":
                    info += " " + _("Les archives libres ne montrent que les enregistrements dont la licence est indiquée : il y en a peu pour "
                                    "un morceau récent, c'est normal.")
            else:
                info = _("Aucun résultat.")
            self.info.setText(info)
        self._lancer(lambda t: ML.chercher(texte, src), _("Recherche"), _("Recherche « {t} »", t=texte), fin)

    def _choisi(self, i):
        x = self.resultats[i] if 0 <= i < len(self.resultats) else None
        self.libre.setChecked(False)              # jamais coché d'office : c'est vous qui le déclarez
        if x and x.get("source") == "archive" and x.get("licence"):
            self.avert.setText(_("Licence annoncée par la personne qui a déposé ce fichier : {l}. Vérifiez qu'elle en avait le droit : un "
                                 "extrait ou une reprise d'un morceau connu n'est pas libre pour autant.", l=x["licence"]))
            self.avert.show()
        else:
            self.avert.hide()
        # changer de morceau arrête l'écoute en cours : le bouton dit de nouveau « Écouter »
        if self.lecteur is not None and getattr(self, "_ecoute", None) != (x or {}).get("page"):
            self.lecteur.stop()
            self.b_ecouter.setText("▶ " + _("Écouter"))

    def _courant(self):
        i = self.liste.currentRow()
        return self.resultats[i] if 0 <= i < len(self.resultats) else None

    def ecouter(self):
        x = self._courant()
        if not x:
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        if self.lecteur is None:
            self.lecteur, self._sortie = QMediaPlayer(self), QAudioOutput(self)
            self.lecteur.setAudioOutput(self._sortie)
            self.lecteur.durationChanged.connect(lambda ms: (self.position.setRange(0, int(ms)), self.position.setEnabled(ms > 0)))
            self.lecteur.positionChanged.connect(self._avance)
            self.lecteur.playbackStateChanged.connect(
                lambda e: self.b_ecouter.setText(("⏸ " + _("Pause")) if e == QMediaPlayer.PlayingState else ("▶ " + _("Écouter"))))
        if getattr(self, "_ecoute", None) == x.get("page") and self.lecteur.source().isValid():
            if self.lecteur.playbackState() == QMediaPlayer.PlayingState:
                self.lecteur.pause()
            else:
                self.lecteur.play()                # reprend où il en était
            return
        self._ecoute = x.get("page")

        def adresse(t):
            if x.get("source") == "archive":
                return self.ML._fichier_archive(x["id"])[0]
            from . import videos_en_ligne as VL
            return VL.flux_lecture(x["page"])

        def fin(url, err):
            if err:
                self.info.setText(_("✕ Ecoute impossible : {e}", e=str(err)[:300]))
                return
            self.lecteur.setSource(QUrl(url))
            self.lecteur.play()
            self.lu.setText(_("Lecture : {t} — {a}. Glissez le curseur pour aller au passage voulu.", t=x.get("titre", ""),
                              a=x.get("artiste", "") or _("artiste inconnu")))
        self._lancer(adresse, _("Ecoute"), _("Préparation de l'écoute"), fin)

    def _avance(self, ms):
        if not self.position.isSliderDown():
            self.position.setValue(int(ms))
        tot = self.position.maximum()
        f = lambda v: f"{int(v // 60000)}:{int(v // 1000) % 60:02d}"
        self.temps.setText(f"{f(ms)} / {f(tot)}")

    def telecharger(self):
        x = self._courant()
        if not x or not self._accord():
            return
        libre, dossier, ML = self.libre.isChecked(), self.dossier, self.ML

        def fin(r, err):
            if err:
                if not isinstance(err, InterruptedError):
                    self.info.setText(_("✕ Téléchargement impossible : {e}", e=str(err)[:300]))
                return
            self.dernier = r
            self.b_poser.setEnabled(True)
            self.info.setText(_("✓ Téléchargé : {f}", f=r) + ("\n" + _("Déclaré libre : la Fabrique musique pourra le réorchestrer.") if libre else
                                                              "\n" + _("Non déclaré libre : la Fabrique musique pourra seulement s'en inspirer.")))
        self._lancer(lambda t: ML.telecharger(x, dossier, libre, t.avancer, lambda: t.arret), _("Téléchargement"),
                     _("Téléchargement de « {t} »", t=x.get("titre", "")), fin, barre=True)

    def done(self, r):
        if self.lecteur is not None:
            self.lecteur.stop()
        for t in self._taches:
            if t.isRunning():
                t.stopper()
        super().done(r)
