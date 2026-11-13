"""Fenêtre « Continuer avec ma voix » (0.9.57) : non bloquante. On choisit l'extrait de voix (le plan, ou un fichier), on
coche l'accord (sa propre voix, ou une personne d'accord : jamais une personne connue), on écrit la phrase ; PhilCut la
fait dire avec cette voix sur ce poste, on l'écoute, puis on la pose à la ligne rouge (ou au début du plan de liaison)."""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout, QLabel,
                               QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget)

from . import voix_clone as V
from .langue import _
from .taches import Tache, texte_erreur

NOMS_LANGUES = {"ar": "العربية", "da": "Dansk", "de": "Deutsch", "el": "Ελληνικά", "en": "English", "es": "Español", "fi": "Suomi",
                "fr": "Français", "he": "עברית", "hi": "हिन्दी", "it": "Italiano", "ja": "日本語", "ko": "한국어", "ms": "Bahasa Melayu",
                "nl": "Nederlands", "no": "Norsk", "pl": "Polski", "pt": "Português", "ru": "Русский", "sv": "Svenska",
                "sw": "Kiswahili", "tr": "Türkçe", "zh": "中文"}
# langues que PhilCut sait préparer sans module en plus (le japonais, le chinois, le coréen et l'hébreu demandent un
# découpage propre à leur écriture)
LANGUES_PROPOSEES = V.LANGUES_SIMPLES


def _temps(t):
    m, s = divmod(max(0.0, t), 60)
    return f"{int(m)}:{s:04.1f}".replace(".", ",")


class DialogueVoixSuite(QDialog):
    def __init__(self, ed, clip=None, debut=None, sur_liaison=None):
        super().__init__(ed)
        self.ed, self.clip, self.sur_liaison = ed, clip, sur_liaison
        self.debut = float(ed.timeline.position if debut is None else debut)
        self.fichier, self.resultat, self.tache, self.lecteur, self._sortie = None, None, None, None, None
        self.setModal(False)
        self.setWindowTitle(_("Continuer avec ma voix"))
        self.setMinimumWidth(560)
        racine = QVBoxLayout(self)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zone.setFrameShape(QFrame.NoFrame)
        racine.addWidget(zone, 1)
        corps = QWidget()
        zone.setWidget(corps)
        v = QVBoxLayout(corps)
        intro = QLabel(_("PhilCut fait dire une phrase avec la voix d'un extrait de 5 à 15 secondes : pratique pour continuer un "
                         "commentaire (« Et maintenant, passons à autre chose… ») sans tout réenregistrer. Tout se fait sur ce poste."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        # --- extrait de voix
        v.addWidget(QLabel(_("<b>Voix à reprendre</b>")))
        self.source = QLabel("")
        self.source.setWordWrap(True)
        v.addWidget(self.source)
        f = QFormLayout()
        self.ref_debut = QDoubleSpinBox()
        self.ref_debut.setRange(0, 1e6)
        self.ref_debut.setDecimals(1)
        self.ref_debut.setSuffix(" s")
        self.ref_duree = QDoubleSpinBox()
        self.ref_duree.setRange(V.REF_MIN, V.REF_MAX)
        self.ref_duree.setDecimals(1)
        self.ref_duree.setSuffix(" s")
        f.addRow(_("Début de l'extrait"), self.ref_debut)
        f.addRow(_("Durée de l'extrait"), self.ref_duree)
        v.addLayout(f)
        he = QHBoxLayout()
        self.b_ecoute_ref = QPushButton(_("▶ Ecouter l'extrait"))
        self.b_ecoute_ref.clicked.connect(self.ecouter_extrait)
        he.addWidget(self.b_ecoute_ref)
        self.b_fichier = QPushButton(_("Prendre la voix d'un fichier…"))
        self.b_fichier.setToolTip(_("Un enregistrement de votre voix (WAV, MP3, vidéo…), au lieu du plan"))
        self.b_fichier.clicked.connect(self.choisir_fichier)
        he.addWidget(self.b_fichier)
        he.addStretch(1)
        v.addLayout(he)
        self.isoler = QCheckBox(_("Isoler d'abord la voix (musique ou bruit derrière)"))
        self.isoler.setToolTip(_("Utilise « Séparer voix, musique et bruits » sur l'extrait : la voix copiée sera plus propre"))
        v.addWidget(self.isoler)
        self.accord = QCheckBox(_("C'est ma voix, ou j'ai l'accord de la personne"))
        self.accord.setStyleSheet("font-weight:600")
        self.accord.toggled.connect(self._maj)
        v.addWidget(self.accord)
        engage = QLabel(_("En cochant, je m'engage : on ne fait parler que sa propre voix, ou celle d'une personne qui a donné son "
                          "accord pour la faire parler ainsi. Jamais la voix d'une personne connue."))
        engage.setWordWrap(True)
        engage.setStyleSheet("color:#9aa4b2")
        v.addWidget(engage)
        # --- texte
        v.addWidget(QLabel(_("<b>Ce que la voix doit dire</b>")))
        self.texte = QPlainTextEdit()
        self.texte.setPlaceholderText(_("Ex. : Et maintenant, passons à autre chose."))
        self.texte.setFixedHeight(80)
        self.texte.textChanged.connect(self._maj)
        v.addWidget(self.texte)
        g = QFormLayout()
        self.langue = QComboBox()
        for code in sorted(LANGUES_PROPOSEES, key=lambda c: NOMS_LANGUES[c].lower()):
            self.langue.addItem(NOMS_LANGUES[code], code)
        self.langue.setCurrentIndex(max(0, self.langue.findData(V.langue_defaut(ed.params))))
        g.addRow(_("Langue"), self.langue)
        hx = QHBoxLayout()
        hx.addWidget(QLabel(_("calme")))
        self.expr = QSlider(Qt.Horizontal)
        self.expr.setRange(25, 100)
        self.expr.setValue(50)
        self.expr.setToolTip(_("0,5 convient le plus souvent ; plus haut, la voix est plus animée (et un peu plus rapide)"))
        hx.addWidget(self.expr, 1)
        hx.addWidget(QLabel(_("animée")))
        g.addRow(_("Expressivité"), hx)
        v.addLayout(g)
        self.ou = QLabel("")
        self.ou.setWordWrap(True)
        self.ou.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.ou)
        self.manque = QLabel("")
        self.manque.setWordWrap(True)
        self.manque.setStyleSheet("color:#e3b341")
        v.addWidget(self.manque)
        self.b_installer = QPushButton(_("Installer le modèle…"))
        self.b_installer.clicked.connect(self._installer)
        v.addWidget(self.b_installer, 0, Qt.AlignLeft)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        v.addStretch(1)
        hb = QHBoxLayout()
        self.b_fabriquer = QPushButton(_("Fabriquer la voix"))
        self.b_fabriquer.setStyleSheet("font-weight:600")
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hb.addWidget(self.b_fabriquer)
        self.b_ecouter = QPushButton(_("▶ Ecouter"))
        self.b_ecouter.setEnabled(False)
        self.b_ecouter.clicked.connect(self.ecouter)
        hb.addWidget(self.b_ecouter)
        hb.addStretch(1)
        self.b_poser = QPushButton(_("Poser dans le film"))
        self.b_poser.setEnabled(False)
        self.b_poser.clicked.connect(self.poser)
        hb.addWidget(self.b_poser)
        self.b_fermer = QPushButton(_("Fermer"))
        self.b_fermer.clicked.connect(self.close)
        hb.addWidget(self.b_fermer)
        racine.addLayout(hb)
        self._source_plan()
        self._maj()
        self.resize(620, 680)

    # ------------------------------------------------------------------ extrait
    def _media(self):
        if self.fichier:
            return self.fichier
        if self.clip:
            m = self.ed.projet.media(self.clip["media"]) or {}
            return m.get("chemin")
        return None

    def _source_plan(self):
        if self.clip:
            d, l = V.extrait_par_defaut(self.clip, self.ed.timeline.position)
            self.ref_debut.setValue(d)
            self.ref_duree.setValue(max(V.REF_MIN, min(V.REF_MAX, l)))
            self.source.setText(_("Le plan « {n} » : par défaut, les dernières secondes de voix avant la ligne rouge.",
                                  n=self.clip.get("nom", "")))
        else:
            self.source.setText(_("Aucun plan choisi : prenez la voix d'un fichier (un enregistrement de votre voix)."))

    def choisir_fichier(self):
        from .widgets import ouvrir_fichier
        p = ouvrir_fichier(self, _("Enregistrement de la voix"), _("Sons et vidéos (*.wav *.mp3 *.m4a *.flac *.ogg *.mp4 *.mov *.mkv);;"
                                                                    "Tous les fichiers (*)"), "musique", self.ed.params)
        if not p:
            return
        self.fichier = p
        self.ref_debut.setValue(0.0)
        self.ref_duree.setValue(12.0)
        self.source.setText(_("Le fichier « {n} ».", n=os.path.basename(p)))
        self._maj()

    def _jouer(self, chemin, debut=0.0):
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        if self.lecteur is None:
            self.lecteur, self._sortie = QMediaPlayer(self), QAudioOutput(self)
            self.lecteur.setAudioOutput(self._sortie)
        if self.lecteur.playbackState() == QMediaPlayer.PlayingState:
            self.lecteur.stop()
            return False
        self.lecteur.setSource(QUrl.fromLocalFile(chemin))
        self.lecteur.setPosition(int(debut * 1000))
        self.lecteur.play()
        return True

    def ecouter_extrait(self):
        m = self._media()
        if m:
            self._jouer(m, self.ref_debut.value())
            from PySide6.QtCore import QTimer
            QTimer.singleShot(int(self.ref_duree.value() * 1000), lambda: self.lecteur and self.lecteur.stop())

    def ecouter(self):
        if self.resultat:
            self._jouer(self.resultat)

    # ------------------------------------------------------------------ état
    def _installer(self):
        f = self.ed.window()
        if hasattr(f, "preferences"):
            f.preferences("IA locale")
        self._maj()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _maj(self, *_a):
        from . import separation as S
        m = V.manquant(self.ed.params)
        self.manque.setText(m or "")
        self.manque.setVisible(bool(m))
        self.b_installer.setVisible(bool(m))
        sep = S.manquant(self.ed.params) is None
        self.isoler.setEnabled(sep)
        if not sep:
            self.isoler.setChecked(False)
            self.isoler.setToolTip(_("Installez « Séparer voix, musique et bruits » (Préférences › IA locale) pour isoler la voix"))
        if self.sur_liaison:
            self.ou.setText(_("Elle sera posée au début du plan de liaison ({t}), sur la piste Voix.", t=_temps(self.debut)))
        else:
            self.ou.setText(_("Elle sera posée à la ligne rouge ({t}), sur la piste Voix.", t=_temps(self.debut)))
        pret = (not m and self.accord.isChecked() and bool(self.texte.toPlainText().strip()) and bool(self._media())
                and not self._en_calcul())
        self.b_fabriquer.setEnabled(pret)
        if not self.accord.isChecked():
            self.b_fabriquer.setToolTip(_("Cochez d'abord l'accord : on ne fait parler que sa propre voix ou celle d'une personne d'accord"))
        else:
            self.b_fabriquer.setToolTip("")

    # ------------------------------------------------------------------ fabrication
    def fabriquer(self):
        if self._en_calcul() or not self.accord.isChecked():
            return
        source, d0, dl = self._media(), self.ref_debut.value(), self.ref_duree.value()
        texte, langue, expr = self.texte.toPlainText().strip(), self.langue.currentData(), self.expr.value() / 100.0
        isoler, params = self.isoler.isChecked() and self.isoler.isEnabled(), self.ed.params
        sortie = os.path.join(V.dossier_sorties(), f"voix_{len(os.listdir(V.dossier_sorties())) + 1:04d}.wav")

        def travail(t):
            src, deb = source, d0
            if isoler:
                from . import separation as S
                import tempfile
                r = S.separer(source, tempfile.mkdtemp(prefix="philcut-voix-"), d0, dl, params,
                              progression=lambda f, txt="": t.avancer(0.25 * f, _("Isolement de la voix")), arret=lambda: t.arret)
                src, deb = r["voix"], 0.0
            ref = V.lire_reference(src, deb, dl)
            return V.dire(texte, ref, sortie, langue, expr, params,
                          progression=lambda f, txt="": t.avancer((0.25 if isoler else 0.0) + (0.75 if isoler else 1.0) * f, txt),
                          arret=lambda: t.arret)
        self.b_ecouter.setEnabled(False)
        self.b_poser.setEnabled(False)
        self.barre.setValue(0)
        self.barre.show()
        self.etat.setText(_("Fabrication de la voix sur ce poste…"))
        self.tache = Tache(travail, _("Continuer avec ma voix"))
        self.tache.lier(self)
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self.tache.start()
        self._maj()

    def _fini(self, r, err):
        self.barre.hide()
        self._maj()
        if err or not r:
            self.etat.setText(_("✕ La voix n'a pas été fabriquée : {e}", e=texte_erreur(err)))
            return
        self.resultat, duree = r
        self.b_ecouter.setEnabled(True)
        self.b_poser.setEnabled(True)
        self.etat.setText(_("✓ Voix fabriquée ({d} s). Ecoutez-la ; pas tout à fait ça ? Changez l'extrait, la ponctuation ou "
                            "l'expressivité et refabriquez. Puis « Poser dans le film ».", d=f"{duree:.1f}".replace(".", ",")))

    def poser(self):
        if not self.resultat:
            return
        c = V.poser(self.ed.projet, self.resultat, self.debut, sur_liaison=self.sur_liaison)
        self.ed.rafraichir()
        if self.lecteur:
            self.lecteur.stop()
        self.b_poser.setEnabled(False)
        self.etat.setText(_("✓ Voix posée à {t} sur la piste « {p} ». Edition › Annuler pour revenir.", t=_temps(c["debut"]),
                            p=c["piste"]))

    def closeEvent(self, ev):
        if self.lecteur:
            self.lecteur.stop()
        if self._en_calcul():
            self.tache.stopper()
        super().closeEvent(ev)
