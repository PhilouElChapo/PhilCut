"""Fenêtres de la voix : enregistrer au micro, faire lire un texte par une voix de synthèse, doubler la vidéo."""
import os

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QPushButton, QSlider, QVBoxLayout)

from . import voix as V
from .langue import _

RETOUCHES = [("a_harmonieuse", _("Voix harmonieuse (conseillé)"), True), ("a_debruit", _("Enlever le souffle"), False),
             ("a_desser", _("Adoucir les « s »"), False), ("a_chaude", _("Voix chaude"), False),
             ("a_claire", _("Voix claire"), False), ("a_radio", _("Voix radio"), False)]


def _retouches(parent, lay):
    from .export import VOIX
    connus = {e for e, _l in VOIX}
    cases = []
    for eid, lib, defaut in RETOUCHES:
        if eid in connus:
            c = QCheckBox(lib)
            c.setChecked(defaut)
            c.eid = eid
            lay.addWidget(c)
            cases.append(c)
    lay.addWidget(QLabel(_("<small>Les retouches restent modifiables ensuite (bouton Voix) : le fichier enregistré n'est jamais abîmé.</small>")))
    return cases


def micros():
    """Micros du poste et celui par défaut."""
    try:
        from PySide6.QtMultimedia import QMediaDevices
        return list(QMediaDevices.audioInputs()), QMediaDevices.defaultAudioInput()
    except Exception:       # noqa: BLE001
        return [], None


class DialogueEnregistrement(QDialog):
    """Enregistre une voix off au micro, pendant que la vidéo défile (facultatif), à partir du curseur."""

    def __init__(self, parent, params, debut=0.0, apercu=None):
        super().__init__(parent)
        self.setWindowTitle(_("Enregistrer une voix off"))
        self.params, self.debut, self.apercu = params, debut, apercu
        self.chemin, self.effets = None, []
        self._t0 = 0
        lay = QVBoxLayout(self)
        f = QFormLayout()
        self.micro = QComboBox()
        self._appareils, defaut = micros()
        for a in self._appareils:
            self.micro.addItem(a.description())
            if defaut is not None and a.id() == defaut.id():
                self.micro.setCurrentIndex(self.micro.count() - 1)
        if not self._appareils:
            self.micro.addItem(_("Aucun micro trouvé"))
            self.micro.setEnabled(False)
        f.addRow(_("Micro"), self.micro)
        m, s = divmod(debut, 60)
        f.addRow(_("Début"), QLabel(_("{m}:{s:04.1f} (position du curseur)", m=int(m), s=s)))
        lay.addLayout(f)
        self.lecture = QCheckBox(_("Faire défiler la vidéo pendant que je parle (casque conseillé)"))
        self.lecture.setChecked(apercu is not None)
        self.lecture.setEnabled(apercu is not None)
        lay.addWidget(self.lecture)
        self.cases = _retouches(self, lay)
        h = QHBoxLayout()
        self.b_rec = QPushButton(_("● Enregistrer"))
        self.b_rec.setEnabled(bool(self._appareils))
        self.b_rec.clicked.connect(self.basculer)
        self.temps = QLabel("0:00.0")
        h.addWidget(self.b_rec)
        h.addWidget(self.temps)
        h.addStretch(1)
        lay.addLayout(h)
        self.info = QLabel(_("Parlez à 15-20 cm du micro, dans une pièce calme."))
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        self.bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bb.button(QDialogButtonBox.Ok).setText(_("Poser sur la piste Voix"))
        self.bb.button(QDialogButtonBox.Ok).setEnabled(False)
        self.bb.accepted.connect(self.accepter)
        self.bb.rejected.connect(self.reject)
        lay.addWidget(self.bb)
        self.minuteur = QTimer(self)
        self.minuteur.timeout.connect(self._tic)
        self.session = self.enregistreur = None

    def basculer(self):
        if self.enregistreur and self.enregistreur.recorderState() != self.enregistreur.RecorderState.StoppedState:
            self.arreter()
        else:
            self.demarrer()

    def demarrer(self):
        from PySide6.QtMultimedia import QAudioInput, QMediaCaptureSession, QMediaFormat, QMediaRecorder
        import time
        self.chemin = V.nouveau_nom(self.params)
        self.session = QMediaCaptureSession(self)
        self.entree = QAudioInput(self._appareils[self.micro.currentIndex()], self)
        self.session.setAudioInput(self.entree)
        self.enregistreur = QMediaRecorder(self)
        self.session.setRecorder(self.enregistreur)
        fmt = QMediaFormat()
        fmt.setFileFormat(QMediaFormat.FileFormat.Wave)
        self.enregistreur.setMediaFormat(fmt)
        self.enregistreur.setAudioSampleRate(48000)
        self.enregistreur.setAudioChannelCount(1)
        self.enregistreur.setQuality(QMediaRecorder.Quality.VeryHighQuality)
        self.enregistreur.setOutputLocation(QUrl.fromLocalFile(self.chemin))
        self.enregistreur.errorOccurred.connect(lambda _e, msg: self.info.setText(_("Micro : {m}", m=msg)))
        self.enregistreur.record()
        if self.lecture.isChecked() and self.apercu is not None:
            self.apercu.lire()
        self._t0 = time.monotonic()
        self.minuteur.start(100)
        self.b_rec.setText(_("■ Arrêter"))
        self.bb.button(QDialogButtonBox.Ok).setEnabled(False)
        self.micro.setEnabled(False)

    def arreter(self):
        self.enregistreur.stop()
        self.minuteur.stop()
        if self.apercu is not None:
            self.apercu.pause()
        self.b_rec.setText(_("● Recommencer"))
        self.micro.setEnabled(True)
        # Qt finit d'écrire le fichier juste après l'arrêt
        QTimer.singleShot(400, self._fichier_pret)

    def _fichier_pret(self):
        ok = bool(self.chemin) and os.path.exists(self.chemin) and os.path.getsize(self.chemin) > 2000
        self.bb.button(QDialogButtonBox.Ok).setEnabled(ok)
        self.info.setText(_("Prise enregistrée. « Poser sur la piste Voix », ou « Recommencer ».") if ok
                          else _("Rien n'a été enregistré : vérifiez le micro (et l'autorisation du micro dans Windows)."))

    def _tic(self):
        import time
        m, s = divmod(time.monotonic() - self._t0, 60)
        self.temps.setText(f"{int(m)}:{s:04.1f}")

    def accepter(self):
        self.effets = [c.eid for c in self.cases if c.isChecked()]
        self.accept()

    def reject(self):
        if self.enregistreur and self.enregistreur.recorderState() != self.enregistreur.RecorderState.StoppedState:
            self.enregistreur.stop()
        super().reject()


class _ChoixVoix(QComboBox):
    """Voix locales installées, puis voix Gemini si une clef est là."""

    def __init__(self, params, langue=None):
        super().__init__()
        for c, nom in V.voix_locales():
            self.addItem(_("{n} — sur ce poste, gratuit", n=nom), ("local", c))
        if params.get("clef_gemini"):
            for nom, lib in V.VOIX_GEMINI:
                self.addItem(_("Gemini {n} ({l}) — en ligne, payant", n=nom, l=lib), ("gemini", nom))
        if langue:
            c = V.voix_locale_langue(langue)
            for i in range(self.count()):
                if self.itemData(i) == ("local", c):
                    self.setCurrentIndex(i)

    def choix(self):
        return self.currentData() or ("local", None)


class DialogueSynthese(QDialog):
    """Un texte lu par une voix de synthèse, posé sur la piste Voix au curseur."""

    def __init__(self, parent, params, debut=0.0):
        super().__init__(parent)
        self.setWindowTitle(_("Voix off de synthèse"))
        self.params, self.debut, self.chemin, self.effets = params, debut, None, []
        lay = QVBoxLayout(self)
        self.texte = QPlainTextEdit()
        self.texte.setPlaceholderText(_("Le texte que la voix doit lire…"))
        lay.addWidget(self.texte)
        f = QFormLayout()
        self.choix = _ChoixVoix(params, "fr")
        f.addRow(_("Voix"), self.choix)
        self.vitesse = QSlider(Qt.Horizontal)
        self.vitesse.setRange(70, 140)
        self.vitesse.setValue(100)
        f.addRow(_("Vitesse"), self.vitesse)
        lay.addLayout(f)
        self.prix = QLabel()
        self.prix.setWordWrap(True)
        lay.addWidget(self.prix)
        if not self.choix.count():
            self.prix.setText(_("Aucune voix sur ce poste : cochez une voix dans Préférences › IA locale (rubrique « Voix de synthèse », "
                                "environ 60 Mo, rien n'est installé dans Windows). Ou connectez Gemini (Outils › Connecter une IA)."))
        self.cases = _retouches(self, lay)
        for c in self.cases:
            c.setChecked(False)
        self.texte.textChanged.connect(self._prix)
        self.choix.currentIndexChanged.connect(self._prix)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Lire et poser sur la piste Voix"))
        bb.button(QDialogButtonBox.Ok).setEnabled(self.choix.count() > 0)
        bb.accepted.connect(self.accepter)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(520, 420)

    def _prix(self):
        m, _v = self.choix.choix()
        if m == "gemini":
            self.prix.setText(_("Lecture par Gemini : environ {p} $ (votre clef, votre compte).", p=f"{V.prix_gemini(self.texte.toPlainText()):.3f}".replace(".", ",")))
        elif self.choix.count():
            self.prix.setText(_("Lecture sur ce poste : gratuit, rien ne sort de l'ordinateur."))

    def accepter(self):
        texte = self.texte.toPlainText().strip()
        if not texte:
            return
        m, v = self.choix.choix()
        if m == "gemini":
            from . import ia
            if not ia.confirmer_envoi(self, texte, "Gemini"):
                return
        self.reglages = {"texte": texte, "moteur": m, "voix": v, "vitesse": self.vitesse.value() / 100.0}
        self.effets = [c.eid for c in self.cases if c.isChecked()]
        self.accept()


class DialogueDoublage(QDialog):
    """Doublage : la voix des plans est écoutée, traduite puis relue par une voix de synthèse dans la langue choisie."""

    def __init__(self, parent, params):
        super().__init__(parent)
        self.setWindowTitle(_("Doubler la vidéo dans une autre langue"))
        self.params = params
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(_("PhilCut écoute la voix de vos plans (sur ce poste), la traduit, puis la fait relire par une voix "
                               "de synthèse, chaque phrase à son moment. La voix d'origine reste en fond, plus bas.")))
        lay.itemAt(0).widget().setWordWrap(True)
        f = QFormLayout()
        self.langue = QComboBox()
        for c, n in V.LANGUES:
            self.langue.addItem(n, c)
        self.langue.setCurrentIndex(1)
        f.addRow(_("Langue du doublage"), self.langue)
        self.trad = QComboBox()
        from . import ia_locale
        if ia_locale.modele_actif(params):
            self.trad.addItem(_("Sur ce poste (modèle local, gratuit)"), False)
        from . import ia
        if ia.disponible(params):
            self.trad.addItem(_("Claude ou Gemini (en ligne, quelques centimes)"), True)
        f.addRow(_("Traduction"), self.trad)
        self.voix = _ChoixVoix(params, "en")
        f.addRow(_("Voix"), self.voix)
        self.langue.currentIndexChanged.connect(self._langue)
        self.st = QCheckBox(_("Ajouter les sous-titres traduits"))
        self.st.setChecked(True)
        lay.addLayout(f)
        lay.addWidget(self.st)
        self.alerte = QLabel()
        self.alerte.setWordWrap(True)
        lay.addWidget(self.alerte)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Doubler"))
        bb.accepted.connect(self.accepter)
        bb.rejected.connect(self.reject)
        self.b_ok = bb.button(QDialogButtonBox.Ok)
        lay.addWidget(bb)
        self._verifier()

    def _langue(self):
        c = V.voix_locale_langue(self.langue.currentData())
        for i in range(self.voix.count()):
            if self.voix.itemData(i) == ("local", c):
                self.voix.setCurrentIndex(i)
                break
        self._verifier()

    def _verifier(self):
        from . import packs_ia
        manque = []
        if not packs_ia.modele_actif("whisper", self.params):
            manque.append(_("un modèle « Voix (sous-titres automatiques) »"))
        if not self.trad.count():
            manque.append(_("un modèle de vision local, ou une clef Claude ou Gemini, pour traduire"))
        m, v = self.voix.choix()
        if m == "local" and not V.voix_locale_langue(self.langue.currentData()):
            manque.append(_("une voix de synthèse en {l}", l=self.langue.currentText().lower()))
        self.alerte.setText(_("Il manque : {m}. A cocher dans Préférences › IA locale.", m=" ; ".join(manque)) if manque else "")
        self.b_ok.setEnabled(not manque)

    def accepter(self):
        m, v = self.voix.choix()
        if m == "local" and (V.voix_locale_langue(self.langue.currentData()) != v):
            v = V.voix_locale_langue(self.langue.currentData())
        self.reglages = {"langue": self.langue.currentData(), "moteur": m, "voix": v,
                         "en_ligne": bool(self.trad.currentData()), "sous_titres": self.st.isChecked()}
        if self.reglages["en_ligne"]:
            if QMessageBox.question(self, _("Doublage"), _("Le texte prononcé dans la vidéo va être envoyé à l'IA en ligne pour être traduit "
                                                           "(quelques centimes). Continuer ?")) != QMessageBox.Yes:
                return
        if m == "gemini":
            if QMessageBox.question(self, _("Doublage"), _("La lecture par Gemini est payante (environ 0,02 $ par minute de voix). Continuer ?")) != QMessageBox.Yes:
                return
        self.accept()
