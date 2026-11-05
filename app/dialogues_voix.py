"""Fenêtres de la voix : enregistrer au micro, faire lire un texte par une voix de synthèse, doubler la vidéo."""
import os

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSlider, QVBoxLayout)

from . import voix as V
from .langue import _

RETOUCHES = [("a_studio", _("Voix studio, façon Insta (conseillé) : débruitage par IA locale, présence, niveau régulier"), True),
             ("a_harmonieuse", _("Voix harmonieuse (avec un léger espace)"), False), ("a_debruit", _("Enlever le souffle"), False),
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
        self.niveau = QProgressBar()
        self.niveau.setRange(0, 100)
        self.niveau.setTextVisible(False)
        self.niveau.setFixedHeight(12)
        self.niveau.setToolTip(_("Niveau du micro en direct : parlez normalement, la barre doit monter vers les trois quarts sans toucher le bout."))
        f.addRow(_("Niveau"), self.niveau)
        m, s = divmod(debut, 60)
        f.addRow(_("Début"), QLabel(_("{m}:{s:04.1f} (position du curseur)", m=int(m), s=s)))
        lay.addLayout(f)
        self.lecture = QCheckBox(_("Faire défiler la vidéo pendant que je parle (casque conseillé)"))
        self.lecture.setChecked(apercu is not None)
        self.lecture.setEnabled(apercu is not None)
        lay.addWidget(self.lecture)
        from .export import NARRATION
        fa = QFormLayout()
        self.amelioration = QComboBox()
        for eid, lib in NARRATION:
            self.amelioration.addItem(_(lib), eid)
        self.amelioration.setCurrentIndex(1)
        self.amelioration.setToolTip(_("Traitement complet de la voix parlée : coupe-bas, débruitage, silence propre entre les phrases, "
                                       "« s » adoucis, présence, compression et niveau régulier. Le fichier enregistré n'est jamais abîmé."))
        self.amelioration.currentIndexChanged.connect(lambda _i: self._preparer_apres())
        fa.addRow(_("Amélioration de la voix"), self.amelioration)
        self.blancs = QCheckBox(_("Retirer les blancs du début et de la fin"))
        self.blancs.setChecked(True)
        self.blancs.toggled.connect(lambda _on: self._preparer_apres())
        fa.addRow("", self.blancs)
        lay.addLayout(fa)
        self.cases = []
        h = QHBoxLayout()
        self.b_rec = QPushButton(_("● Enregistrer"))
        self.b_rec.setEnabled(bool(self._appareils))
        self.b_rec.clicked.connect(self.basculer)
        self.temps = QLabel("0:00.0")
        h.addWidget(self.b_rec)
        self.b_ecoute = QPushButton(_("▶ Avant (brut)"))
        self.b_ecoute.setToolTip(_("Ecouter la prise telle qu'enregistrée"))
        self.b_ecoute.setEnabled(False)
        self.b_ecoute.clicked.connect(lambda: self.ecouter(False))
        h.addWidget(self.b_ecoute)
        self.b_apres = QPushButton(_("▶ Après (amélioré)"))
        self.b_apres.setToolTip(_("Ecouter la prise avec l'amélioration choisie, exactement comme elle sera dans la vidéo"))
        self.b_apres.setEnabled(False)
        self.b_apres.clicked.connect(lambda: self.ecouter(True))
        h.addWidget(self.b_apres)
        h.addWidget(self.temps)
        h.addStretch(1)
        lay.addLayout(h)
        self._apres = None            # fichier d'écoute « après »
        self._prise = None            # prise retenue (blancs retirés si coché)
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
        self.lecteur = None
        self.source = self.flux = None
        self.micro.currentIndexChanged.connect(lambda _i: self._vumetre())
        self.vu = QTimer(self)
        self.vu.timeout.connect(self._lire_niveau)
        self._vumetre()

    # ---- vumètre : le micro est écouté dès l'ouverture, pour vérifier qu'il capte avant d'enregistrer
    def _vumetre(self):
        self._arreter_vumetre()
        if not self._appareils:
            return
        try:
            from PySide6.QtMultimedia import QAudioFormat, QAudioSource
            fmt = QAudioFormat()
            fmt.setSampleRate(16000)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.Int16)
            self.source = QAudioSource(self._appareils[self.micro.currentIndex()], fmt, self)
            self.flux = self.source.start()
            self.vu.start(60)
        except Exception:       # noqa: BLE001 : pas de vumètre, l'enregistrement reste possible
            self.source = self.flux = None

    def _arreter_vumetre(self):
        self.vu.stop()
        if self.source is not None:
            try:
                self.source.stop()
            except Exception:       # noqa: BLE001
                pass
        self.source = self.flux = None

    def _lire_niveau(self):
        if self.flux is None:
            return
        d = bytes(self.flux.readAll())
        if len(d) < 2:
            return
        import array
        a = array.array("h", d[: len(d) // 2 * 2])
        crete = max(abs(min(a)), abs(max(a))) / 32768.0
        import math
        db = 20 * math.log10(max(crete, 1e-4))          # -80 dB … 0 dB
        self.niveau.setValue(int(max(0, min(100, (db + 60) / 60 * 100))))

    def ecouter(self, apres=False):
        """Avant / après : on compare la prise brute et la prise améliorée avant de la poser."""
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        if self.lecteur is None:
            self.lecteur = QMediaPlayer(self)
            self._sortie = QAudioOutput(self)
            self.lecteur.setAudioOutput(self._sortie)
            self.lecteur.playbackStateChanged.connect(
                lambda st: st == QMediaPlayer.StoppedState and (self.b_ecoute.setText(_("▶ Avant (brut)")), self.b_apres.setText(_("▶ Après (amélioré)"))))
        en_cours = self.lecteur.playbackState() == QMediaPlayer.PlayingState
        meme = getattr(self, "_ecoute_apres", None) == apres
        self.lecteur.stop()
        if en_cours and meme:
            return
        f = self._apres if apres else self.chemin
        if apres and not (f and os.path.exists(f)):
            self.info.setText(_("Préparation de l'écoute améliorée…"))
            self._preparer_apres(jouer=True)
            return
        self._ecoute_apres = apres
        self.lecteur.setSource(QUrl.fromLocalFile(f))
        self.lecteur.play()
        (self.b_apres if apres else self.b_ecoute).setText(_("■ Arrêter"))
        (self.b_ecoute if apres else self.b_apres).setText(_("▶ Avant (brut)") if apres else _("▶ Après (amélioré)"))

    def _preparer_apres(self, jouer=False):
        """Calcule la prise retenue (blancs retirés) et sa version améliorée, en arrière-plan."""
        if not self.chemin or not os.path.exists(self.chemin):
            return
        from .taches import Tache
        brut, eid, blancs = self.chemin, self.amelioration.currentData(), self.blancs.isChecked()
        base = os.path.splitext(brut)[0]

        def travail(t):
            prise = V.couper_blancs(brut, base + "_net.wav") if blancs else brut
            apres = V.rendu_ecoute(prise, [eid] if eid else [], base + "_ecoute.wav")
            return prise, apres
        self._n_prep = getattr(self, "_n_prep", 0) + 1
        n = self._n_prep
        t = Tache(travail, _("Ecoute améliorée"))
        self._tache_prep = t

        def fini(r, e):
            if n != self._n_prep:
                return
            if e:
                self.info.setText(_("Ecoute impossible : {e}", e=str(e)[:150]))
                return
            self._prise, self._apres = r
            d = V.duree_wav(self._prise)
            self.info.setText(_("Prise prête ({d:.1f} s). Comparez « Avant » et « Après », puis « Poser sur la piste Voix » ou « Recommencer ».", d=d))
            self.b_apres.setEnabled(True)
            if jouer:
                self.ecouter(True)
        t.fini.connect(fini)
        t.start()

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
        self.b_ecoute.setEnabled(False)
        self.b_apres.setEnabled(False)
        if self.lecteur is not None:
            self.lecteur.stop()
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
        self.b_ecoute.setEnabled(ok)
        self._prise = self._apres = None
        self.info.setText(_("Prise enregistrée : préparation de l'écoute améliorée…") if ok
                          else _("Rien n'a été enregistré : vérifiez le micro (et l'autorisation du micro dans Windows)."))
        if ok:
            self._preparer_apres()

    def _tic(self):
        import time
        m, s = divmod(time.monotonic() - self._t0, 60)
        self.temps.setText(f"{int(m)}:{s:04.1f}")

    def accepter(self):
        eid = self.amelioration.currentData()
        self.effets = [eid] if eid else []
        if self.blancs.isChecked():
            if not (self._prise and os.path.exists(self._prise)):
                try:
                    self._prise = V.couper_blancs(self.chemin, os.path.splitext(self.chemin)[0] + "_net.wav")
                except Exception:       # noqa: BLE001
                    self._prise = None
            if self._prise:
                self.chemin = self._prise
        self._arreter_vumetre()
        if self.lecteur is not None:
            self.lecteur.stop()
        self.accept()

    def reject(self):
        if self.enregistreur and self.enregistreur.recorderState() != self.enregistreur.RecorderState.StoppedState:
            self.enregistreur.stop()
        self._arreter_vumetre()
        if self.lecteur is not None:
            self.lecteur.stop()
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


class DialogueAutotune(QDialog):
    """Vraie correction de justesse d'un chant : tonalité, force, écoute avant / après, puis appliquer (nouveau fichier)."""

    def __init__(self, parent, chemin, params, debut=0.0, duree=None):
        super().__init__(parent)
        from . import autotune as A
        self.setWindowTitle(_("Autotune (correction de justesse)"))
        self.chemin, self.params, self.debut, self.duree = chemin, params, debut, duree
        self.resultat = None
        lay = QVBoxLayout(self)
        intro = QLabel(_("PhilCut mesure la hauteur de la voix et ramène chaque note sur la note juste la plus proche. "
                         "« Naturel » corrige en douceur ; « Robot » colle instantanément à la note (l'effet des tubes des années 2000). "
                         "Le fichier d'origine est gardé : « Revenir à l'original » reste possible."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        f = QFormLayout()
        self.tonalite = QComboBox()
        self.tonalite.addItem(_("Toutes les notes (chromatique)"), (0, "chromatique"))
        for g, lib in (("majeure", _("majeur")), ("mineure", _("mineur"))):
            for i, n in enumerate(A.NOTES):
                self.tonalite.addItem(f"{n} {lib}", (i, g))
        f.addRow(_("Tonalité"), self.tonalite)
        self.force = QComboBox()
        for k, lib in (("naturel", _("Naturel (doux)")), ("net", _("Net")), ("robot", _("Robot (effet marqué)"))):
            self.force.addItem(lib, k)
        f.addRow(_("Force"), self.force)
        lay.addLayout(f)
        h = QHBoxLayout()
        self.b_avant = QPushButton(_("▶ Avant"))
        self.b_avant.clicked.connect(lambda: self._jouer(False))
        self.b_apres = QPushButton(_("▶ Après (10 s corrigées)"))
        self.b_apres.clicked.connect(lambda: self._jouer(True))
        h.addWidget(self.b_avant)
        h.addWidget(self.b_apres)
        h.addStretch(1)
        lay.addLayout(h)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Appliquer au plan"))
        bb.accepted.connect(self.appliquer)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.lecteur = None
        self.tonalite.currentIndexChanged.connect(lambda _i: setattr(self, "_essai", None))
        self.force.currentIndexChanged.connect(lambda _i: setattr(self, "_essai", None))
        self._essai = None

    def _reglages(self):
        tonique, gamme = self.tonalite.currentData()
        return tonique, gamme, self.force.currentData()

    def _extrait(self):
        import tempfile
        base = os.path.join(tempfile.gettempdir(), f"philcut_autotune_{os.getpid()}")
        src = base + "_avant.wav"
        if not os.path.exists(src):
            from . import moteur
            moteur.lancer(["-ss", f"{self.debut:.3f}", "-t", f"{min(10.0, self.duree or 10.0):.3f}", "-i", self.chemin,
                           "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", src])
        return base, src

    def _jouer(self, apres):
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from .taches import Tache
        from . import autotune as A
        if self.lecteur is None:
            self.lecteur = QMediaPlayer(self)
            self._sortie = QAudioOutput(self)
            self.lecteur.setAudioOutput(self._sortie)
        self.lecteur.stop()
        if not apres:
            base, src = self._extrait()
            self.lecteur.setSource(QUrl.fromLocalFile(src))
            self.lecteur.play()
            return
        if self._essai and os.path.exists(self._essai):
            self.lecteur.setSource(QUrl.fromLocalFile(self._essai))
            self.lecteur.play()
            return
        self.info.setText(_("Correction des 10 premières secondes…"))
        reglages = self._reglages()

        def travail(t):
            base, src = self._extrait()
            sortie = base + f"_apres_{reglages[0]}_{reglages[1]}_{reglages[2]}.wav"
            bilan = A.corriger(src, sortie, *reglages)
            return sortie, bilan
        t = Tache(travail, _("Autotune"))
        self._tache = t

        def fini(r, e):
            if e:
                self.info.setText(_("Autotune impossible : {e}", e=str(e)[:200]))
                return
            self._essai, bilan = r
            self.info.setText(_("Ecart moyen corrigé : {c} centièmes de demi-ton sur {n} instants chantés.", c=bilan["ecart_cents"], n=bilan["notes"]))
            self.lecteur.setSource(QUrl.fromLocalFile(self._essai))
            self.lecteur.play()
        t.fini.connect(fini)
        t.start()

    def appliquer(self):
        from . import autotune as A
        if self.lecteur is not None:
            self.lecteur.stop()
        sortie = V.nouveau_nom(self.params, "autotune")
        self.info.setText(_("Correction du plan entier…"))
        self.repaint()
        try:
            tonique, gamme, force = self._reglages()
            A.corriger(self.chemin, sortie, tonique, gamme, force)
        except Exception as e:      # noqa: BLE001
            QMessageBox.warning(self, _("Autotune"), str(e))
            return
        self.resultat = sortie
        self.accept()
