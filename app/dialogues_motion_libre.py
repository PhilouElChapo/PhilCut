"""1.1.0 : fenêtre « Animation libre » : vous décrivez, l'IA construit la composition, vous regardez l'aperçu,
vous demandez des changements, puis PhilCut la fabrique en qualité et la pose dans le film.
1.1.2 : au choix, HyperFrames ou Remotion (Philippe, 21/11 20h12 : « le projet sera distribué : laisser le choix aux
utilisateurs ») ; le plan de l'IA (une ligne par étape) est montré et vérifié contre la durée."""
import copy
import os
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QScrollArea,
                               QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget)

from . import motion as M, motion_libre as ML
from .langue import _
from .taches import Tache, texte_erreur

FORMATS = (("16:9", (1920, 1080)), ("9:16", (1080, 1920)), ("1:1", (1080, 1080)))


def _prix(p):
    return f"{p:.2f}".replace(".", ",")


class DialogueMotionLibre(QDialog):
    def __init__(self, ed, anim=None):
        super().__init__(ed)
        from . import charte as CH
        from .credit_ia import LigneCredit
        from .dialogues_creatif import ApercuCreation
        self.ed, self.params = ed, ed.params
        self.tache, self.taches, self.apercu_fichier, self.resultat = None, [], "", ""
        self.setWindowTitle(_("Motion design IA (look pro) : décrivez-la, l'IA la construit"))
        h = QHBoxLayout(self)
        gauche = QVBoxLayout()
        intro = QLabel(_("Décrivez l'animation comme à un graphiste : ce qui apparaît, comment ça bouge, dans quel ordre. L'IA "
                         "écrit une vraie composition (dessins, graphiques, particules, textes) avec votre charte ; vous regardez "
                         "l'aperçu et demandez des changements, autant de fois qu'il faut."))
        intro.setWordWrap(True)
        gauche.addWidget(intro)
        self.description = QPlainTextEdit()
        self.description.setPlaceholderText(_("ex. : un cadeau apparaît tout petit et grandit pendant qu'un compteur monte de 0 à 40 ; un "
                                              "graphique monte en même temps ; à 40, feu d'artifice ; puis l'image part en confettis."))
        self.description.setFixedHeight(100)
        gauche.addWidget(self.description)
        f = QFormLayout()
        self.format = QComboBox()
        L, H = ed.projet.taille
        for nom, t in FORMATS:
            self.format.addItem(nom, t)
        self.format.setCurrentIndex(1 if H > L else (2 if H == L else 0))
        f.addRow(_("Format"), self.format)
        self.duree = QDoubleSpinBox()
        self.duree.setRange(0, ML.DUREE_MAX)
        self.duree.setSingleStep(1)
        self.duree.setSuffix(" s")
        self.duree.setSpecialValueText(_("au choix de l'IA"))
        f.addRow(_("Durée"), self.duree)
        self.charte = QComboBox()
        act = CH.active(self.params)
        for ch in CH.toutes(self.params):
            self.charte.addItem(ch.get("nom") or _("Charte"), ch)
            if ch.get("nom") == (act or {}).get("nom"):
                self.charte.setCurrentIndex(self.charte.count() - 1)
        f.addRow(_("Charte"), self.charte)
        self.moteur_libre = QComboBox()
        for k in ML.MOTEURS_LIBRES:
            self.moteur_libre.addItem(ML.NOMS_MOTEURS[k].split(" (")[0], k)
            self.moteur_libre.setItemData(self.moteur_libre.count() - 1, ML.NOMS_MOTEURS[k], Qt.ToolTipRole)
        k = (anim or {}).get("moteur_libre") or self.params.get("motion_libre_moteur") or "hyperframes"
        self.moteur_libre.setCurrentIndex(max(0, self.moteur_libre.findData(k)))
        self.moteur_libre.currentIndexChanged.connect(self._moteur_change)
        f.addRow(_("Ecrite pour"), self.moteur_libre)
        self.aide_moteur = QLabel("")
        self.aide_moteur.setWordWrap(True)
        self.aide_moteur.setStyleSheet("color:#9aa4c0")
        f.addRow("", self.aide_moteur)
        self.licence = QCheckBox(_("J'ai droit à la licence gratuite de Remotion (ou j'ai une licence entreprise)"))
        self.licence.setToolTip(_("Gratuite pour un particulier, une structure de 3 personnes au plus ou une association ; au-delà, "
                                  "licence entreprise Remotion obligatoire (remotion.dev/license)"))
        self.licence.setChecked(bool(self.params.get("remotion_licence")))
        self.licence.toggled.connect(self._licence)
        f.addRow("", self.licence)
        self.transparent = QCheckBox(_("Fond transparent : posée au-dessus du film"))
        f.addRow("", self.transparent)
        self.bruitages = QCheckBox(_("Bruitages placés par l'IA"))
        self.bruitages.setToolTip(_("Bruitages : l'IA les place sur son plan (posés avec l'animation, modifiables)"))
        self.bruitages.setChecked(bool(self.params.get("motion_libre_bruitages", True)))
        self.bruitages.toggled.connect(lambda v: self.params.__setitem__("motion_libre_bruitages", bool(v)))
        f.addRow("", self.bruitages)
        self.caler = QCheckBox(_("Calée sur la musique du film"))
        self.caler.setToolTip(_("Caler les moments forts sur la musique du film (à partir de la ligne rouge)") + " — " +
                              _("Les temps forts de la musique posée dans le montage sont donnés à l'IA ; l'animation sera posée à la "
                                "ligne rouge où elle est maintenant, pour rester calée"))
        a_musique = any(True for _c in ed.projet.clips_piste("audio")) if hasattr(ed.projet, "clips_piste") else False
        self.caler.setEnabled(a_musique)
        self.caler.setChecked(a_musique and bool(self.params.get("motion_libre_caler", True)))
        self.caler.toggled.connect(lambda v: self.params.__setitem__("motion_libre_caler", bool(v)))
        f.addRow("", self.caler)
        gauche.addLayout(f)
        gauche.addWidget(self._groupe_pro())
        self.credit = LigneCredit(self.params, "anthropic", self, compact=True)
        gauche.addWidget(self.credit)
        self.b_creer = QPushButton(_("✨ Construire l'animation (environ {p} $)", p=_prix(ML.PRIX_CREER)))
        self.b_creer.clicked.connect(self.creer)
        gauche.addWidget(self.b_creer)
        # changements
        self.remarque = QLineEdit()
        self.remarque.setPlaceholderText(_("ce qu'il faut changer (ex. : le cadeau plus grand, le feu d'artifice plus long)"))
        hb = QHBoxLayout()
        hb.addWidget(self.remarque, 1)
        self.b_corriger = QPushButton(_("Changer (environ {p} $)", p=_prix(ML.PRIX_CORRIGER)))
        self.b_corriger.clicked.connect(lambda: self.corriger())
        hb.addWidget(self.b_corriger)
        gauche.addLayout(hb)
        self.erreurs = QLabel("")
        self.erreurs.setWordWrap(True)
        self.erreurs.setStyleSheet("color:#e0a030")
        gauche.addWidget(self.erreurs)
        self.b_erreurs = QPushButton(_("Faire corriger ces erreurs par l'IA (environ {p} $)", p=_prix(ML.PRIX_CORRIGER)))
        self.b_erreurs.clicked.connect(lambda: self.corriger(erreur="\n".join(self._erreurs or getattr(self, "_manquants", []))))
        self.b_erreurs.hide()
        gauche.addWidget(self.b_erreurs)
        hv = QHBoxLayout()
        self.b_avant = QPushButton(_("‹ Version d'avant"))
        self.b_avant.clicked.connect(self.version_avant)
        self.b_projet = QPushButton(_("Ouvrir le projet"))
        self.b_projet.setToolTip(_("Le dossier de l'animation (HyperFrames : index.html ; Remotion : src/LibreCode.tsx) : le studio du "
                                   "moteur ou Claude Code peuvent la retoucher"))
        self.b_projet.clicked.connect(self.ouvrir_projet)
        hv.addWidget(self.b_avant)
        hv.addWidget(self.b_projet)
        hv.addStretch(1)
        gauche.addLayout(hv)
        hmod = QHBoxLayout()                     # 1.1.3 : mes modèles d'animation (bibliothèque, sur tous les postes)
        b_rep = QPushButton(_("Reprendre un modèle…"))
        b_rep.clicked.connect(self.reprendre_modele)
        self.b_garder_modele = QPushButton(_("☆ Garder comme modèle…"))
        self.b_garder_modele.clicked.connect(self.garder_modele)
        hmod.addWidget(b_rep)
        hmod.addWidget(self.b_garder_modele)
        hmod.addStretch(1)
        gauche.addLayout(hmod)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        gauche.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        gauche.addWidget(self.etat)
        gauche.addStretch(1)
        w_g = QWidget()
        w_g.setLayout(gauche)
        zg = QScrollArea()                       # 1.1.16 : la colonne s'est allongée (look pro) ; elle défile sur un petit écran
        zg.setWidgetResizable(True)
        zg.setFrameShape(QScrollArea.NoFrame)
        zg.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zg.setWidget(w_g)
        zg.setFixedWidth(490)
        h.addWidget(zg)
        droite = QVBoxLayout()
        self.message = QLabel(_("L'aperçu apparaîtra ici (rendu léger sur ce poste, gratuit)."))
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        zm = QScrollArea()                    # 1.1.8 : le plan entier se lit (il était coupé sous l'aperçu)
        zm.setWidgetResizable(True)
        zm.setFrameShape(QScrollArea.NoFrame)
        zm.setWidget(self.message)
        zm.setMaximumHeight(230)
        droite.addWidget(zm)
        self.b_verifier = QPushButton(_("Vérifier les étapes sur l'aperçu (IA, environ {p} $)", p=_prix(ML.PRIX_VERIFIER)))
        self.b_verifier.setToolTip(_("Une image au milieu de chaque étape du plan est montrée à l'IA, qui dit lesquelles ne se voient "
                                     "pas ; vous pouvez ensuite les faire corriger"))
        self.b_verifier.clicked.connect(self.verifier_etapes)
        droite.addWidget(self.b_verifier, 0, Qt.AlignLeft)
        self.apercu = ApercuCreation(self)
        droite.addWidget(self.apercu)
        droite.addStretch(1)
        self.b_installer = QPushButton("")
        self.b_installer.clicked.connect(self.installer)
        droite.addWidget(self.b_installer)
        hf = QHBoxLayout()
        self.moteur = QComboBox()
        hf.addWidget(self.moteur, 1)
        self.b_fabriquer = QPushButton(_("Fabriquer en qualité et poser…"))
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hf.addWidget(self.b_fabriquer)
        droite.addLayout(hf)
        hb2 = QHBoxLayout()                    # 1.1.2 : Réduire toujours là ; fermer range la fenêtre, le travail est gardé
        b_nouvelle = QPushButton(_("Nouvelle animation"))
        b_nouvelle.setToolTip(_("Repartir d'une description vide (l'animation en cours est oubliée)"))
        b_nouvelle.clicked.connect(self.nouvelle)
        hb2.addWidget(b_nouvelle)
        hb2.addStretch(1)
        self.b_reduire = QPushButton(_("Réduire"))
        self.b_reduire.setToolTip(_("Range la fenêtre ; la barre du bas ou Fabrique IA › Animation la rouvrent, telle quelle"))
        self.b_reduire.clicked.connect(self.reduire)
        hb2.addWidget(self.b_reduire)
        b_fermer = QPushButton(_("Fermer"))
        b_fermer.setToolTip(_("Votre animation reste gardée : Fabrique IA › Animation › Animation libre la rouvre"))
        b_fermer.clicked.connect(self.close)
        hb2.addWidget(b_fermer)
        droite.addLayout(hb2)
        h.addLayout(droite, 1)
        self._erreurs = []
        self.anim = anim or None
        if anim:
            self.description.setPlainText(anim.get("description", ""))
        self.resize(1000, 700)
        self._moteur_change()
        from . import en_cours as EC                 # 1.2.1 : gardée à chaque changement (code, dessins, vidéos déjà payés)
        EC.suivre(self, "motion_ia", self._etat_en_cours,
                  lambda: (self.anim or {}).get("titre") or self.description.toPlainText().strip()[:60])

    def _etat_en_cours(self):
        if not self.a_garder():
            return None
        a = self.lire()
        return {"anim": {k: v for k, v in a.items() if k != "charte"}}

    def _groupe_pro(self):
        """1.1.16 : la méthode des outils en ligne, réglable (chaque coût est demandé avant de payer)."""
        from PySide6.QtWidgets import QGridLayout, QGroupBox, QSpinBox
        from . import motion_pro as MP
        g = QGroupBox(_("Look pro"))
        gl = QGridLayout(g)
        p = self.params
        self.pro_dessins = QCheckBox(_("Vrais dessins (Gemini)"))
        self.pro_dessins.setToolTip(_("Les objets (canon, avion, cadeau…) sont dessinés par Gemini puis détourés, au lieu de dessins "
                                      "faits en code ; environ {p} $ le dessin", p=_prix(MP.PRIX_IMAGE)))
        self.pro_dessins.setChecked(bool(p.get("motion_pro_dessins", True)))
        self.pro_videos = QCheckBox(_("Effets réalistes en vidéo IA"))
        self.pro_videos.setToolTip(_("Feu, fumée, explosion, eau… filmés par votre générateur vidéo sur fond noir, posés en mode "
                                     "écran au bon instant ; le prix est demandé"))
        self.pro_videos.setChecked(bool(p.get("motion_pro_videos", True)))
        self.pro_blocs = QCheckBox(_("Blocs éprouvés (HyperFrames)"))
        self.pro_blocs.setToolTip(_("236 composants du registre officiel HyperFrames (HeyGen, Apache 2.0) : textes, particules, "
                                    "transitions, compteurs… et 124 plans tout prêts de Video ShotCraft (Apache 2.0 : mouvements "
                                    "de caméra, ouvertures, transitions) ; l'IA choisit ceux qui servent et s'en inspire"))
        self.pro_blocs.setChecked(bool(p.get("motion_pro_blocs", True)))
        self.pro_3d = QCheckBox(_("3D, physique et effets pixel"))         # 1.3.1
        self.pro_3d.setToolTip(_("Vraie 3D (Three.js : objets, lumière, ombres, caméra), physique réelle (Rapier : ça tombe, "
                                 "rebondit, s'effondre), lueur, grain, flou, et 244 effets pixel art (pixelfx) ; gratuits, "
                                 "calculés sur ce poste ; l'IA s'en sert quand la description le demande"))
        self.pro_3d.setChecked(bool(p.get("motion_pro_3d", True)))
        gl.addWidget(self.pro_dessins, 0, 0)
        gl.addWidget(self.pro_videos, 0, 1)
        gl.addWidget(self.pro_blocs, 1, 0)
        hr = QHBoxLayout()
        hr.addWidget(QLabel(_("Relectures")))
        self.pro_tours = QSpinBox()
        self.pro_tours.setRange(0, 3)
        self.pro_tours.setValue(int(p.get("motion_pro_tours", 2)))
        self.pro_tours.setToolTip(_("L'IA regarde une image par étape de son aperçu et corrige ce qui ne se voit pas, ce nombre de "
                                    "fois au plus (0 : jamais)"))
        hr.addWidget(self.pro_tours)
        hr.addStretch(1)
        gl.addLayout(hr, 1, 1)
        hm = QHBoxLayout()
        hm.addWidget(QLabel(_("Modèle qui écrit")))
        self.pro_modele = QComboBox()
        for k, lib in (("auto", _("Selon la complexité")), ("rapide", _("Rapide (moins cher)")), ("meilleur", _("Le meilleur"))):
            self.pro_modele.addItem(lib, k)
        self.pro_modele.setCurrentIndex(max(0, self.pro_modele.findData(p.get("motion_pro_modele") or "auto")))
        hm.addWidget(self.pro_modele, 1)
        gl.addLayout(hm, 2, 0, 1, 2)
        gl.addWidget(self.pro_3d, 3, 0, 1, 2)
        for w, cle in ((self.pro_dessins, "motion_pro_dessins"), (self.pro_videos, "motion_pro_videos"),
                       (self.pro_blocs, "motion_pro_blocs"), (self.pro_3d, "motion_pro_3d")):
            w.toggled.connect(lambda v, c=cle: self.params.__setitem__(c, bool(v)))
        self.pro_tours.valueChanged.connect(lambda v: self.params.__setitem__("motion_pro_tours", int(v)))
        self.pro_modele.currentIndexChanged.connect(lambda _i: self.params.__setitem__("motion_pro_modele",
                                                                                       self.pro_modele.currentData()))
        return g

    def _pro_actif(self):
        return any(w.isChecked() for w in (self.pro_dessins, self.pro_videos, self.pro_blocs, self.pro_3d)) or self.pro_tours.value() > 0 \
            or self.pro_modele.currentData() != "rapide"

    # ------------------------------------------------------------------ état
    def moteur_choisi(self):
        return self.moteur_libre.currentData() or "hyperframes"

    def _pret_ici(self):
        """Le moteur choisi peut rendre l'aperçu sur ce poste."""
        from . import motion_html as MH, motion_remotion as MR
        if self.moteur_choisi() == "remotion":
            return MH.local_pret() and MR.pret() and bool(self.params.get("remotion_licence"))
        return MH.local_pret()

    def _licence(self, oui):
        self.params["remotion_licence"] = bool(oui)
        if hasattr(self.params, "enregistrer"):          # 1.3.0 : gardé tout de suite (l'ancien appel n'existait pas)
            self.params.enregistrer()
        self._maj()

    def _moteur_change(self, *_a):
        k = self.moteur_choisi()
        self.aide_moteur.setText(ML.NOMS_MOTEURS[k])
        self.licence.setVisible(k == "remotion")
        self.moteur.clear()
        if k == "remotion":
            self.moteur.addItem(_("Remotion sur ce poste (gratuit)"), "remotion")
        else:
            self.moteur.addItem(_("HyperFrames sur ce poste (gratuit)"), "hyperframes_local")
            self.moteur.addItem(_("HyperFrames chez HeyGen (payant)"), "hyperframes_cloud")
        if self.anim and ML.code_de(self.anim) and ML.code_de(self.anim) != k:
            self.etat.setText(_("L'animation est écrite pour {a} : « Changer » la fera réécrire pour {b} (même allure, même "
                                "minutage).", a=ML.NOMS_MOTEURS[ML.code_de(self.anim)].split(" (")[0],
                                b=ML.NOMS_MOTEURS[k].split(" (")[0]))
        self._maj()

    def _maj(self):
        occupe = bool(self.tache and self.tache.isRunning())
        a_code = bool(self.anim and ML.code_de(self.anim))
        a_jour = a_code and ML.code_de(self.anim) == self.moteur_choisi()
        remotion = self.moteur_choisi() == "remotion"
        self.b_creer.setEnabled(not occupe and (not remotion or self.licence.isChecked()))
        self.b_corriger.setEnabled(a_code and not occupe and (not remotion or self.licence.isChecked()))
        self.b_erreurs.setEnabled(a_code and not occupe)
        self.b_avant.setEnabled(a_code and bool((self.anim.get("libre") or {}).get("historique")) and not occupe)
        self.b_projet.setEnabled(a_jour)
        self.b_verifier.setEnabled(bool(a_jour and self.apercu_fichier and (self.anim.get("libre") or {}).get("plan")) and not occupe)
        self.b_fabriquer.setEnabled(a_jour and not occupe and not self._erreurs and (not remotion or self.licence.isChecked()))
        manque = not self._pret_ici() and (not remotion or self.licence.isChecked())
        self.b_installer.setText(_("Installer Remotion sur ce poste (environ 250 Mo, une fois)…") if remotion else
                                 _("Installer HyperFrames sur ce poste (environ 200 Mo, une fois)…"))
        self.b_installer.setVisible(manque)
        self.b_installer.setEnabled(not occupe)

    def lire(self):
        a = copy.deepcopy(self.anim) if self.anim else ML.fiche(self.description.toPlainText())
        a["description"] = self.description.toPlainText().strip()
        a["taille"] = list(self.format.currentData())
        a["charte"] = self.charte.currentData()
        a["transparent"] = self.transparent.isChecked()
        a["moteur_libre"] = self.moteur_choisi()
        a["bruitages"] = self.bruitages.isChecked()
        if self.duree.value() > 0:
            a["duree"], a["duree_imposee"] = float(self.duree.value()), True
        else:
            a.pop("duree_imposee", None)
            a["duree"] = a.get("duree") or 0.0
        return a

    def _lancer(self, travail, titre, fin):
        self.tache = Tache(travail, titre)
        self.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, titre)
        self.barre.setValue(0)
        self.barre.show()
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)

        def fini(r, e):
            try:
                self.barre.hide()
                self.tache = None
                fin(r, e)
                self._maj()
            except RuntimeError:
                pass
        self.tache.fini.connect(fini, Qt.QueuedConnection)
        self.tache.start()
        self._maj()

    def _accord(self, texte, prix):
        if getattr(self, "_test_oui", False):
            return True
        return QMessageBox.question(self, self.windowTitle(), _("{t} : environ {p} $ (votre clef d'IA). Continuer ?", t=texte,
                                                                p=_prix(prix))) == QMessageBox.Yes

    # ------------------------------------------------------------------ l'IA écrit, PhilCut vérifie et montre
    def _verifier_et_apercu(self, t, a):
        """Règles du rendu image par image, « hyperframes lint », puis aperçu léger : (anim, aperçu, erreurs)."""
        from . import motion_html as MH
        fautes = ML.fautes(a)
        if fautes:
            return a, "", [_("Règle non respectée : {f}", f=x) for x in fautes]
        if ML.code_de(a) == "remotion":
            return self._apercu_remotion(t, a)
        if not MH.local_pret():
            return a, "", []
        t.avancer(0.55, _("Vérification de la composition (sur ce poste)…"))
        d = os.path.join(M.dossier(), "projets", "libre_verification")
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        MH.preparer_projet(a, d)
        erreurs = MH.verifier(d)
        if erreurs:
            return a, "", erreurs
        t.avancer(0.6, _("Aperçu léger (sur ce poste, gratuit)…"))
        sortie = os.path.join(M.dossier(), f"apercu_libre_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
        leger = ML.apercu_leger(dict(a, transparent=False))
        r = MH.rendre_local(self.params, leger, sortie,
                            lambda f, x: t.avancer(0.6 + 0.4 * f, _("Aperçu léger : {x}", x=x)), t.arret_demande)
        return a, self._avec_sons(a, r), []

    def _avec_sons(self, a, video):
        """L'aperçu avec ses bruitages, pour les entendre ; un échec laisse l'aperçu muet."""
        if not a.get("bruitages", True) or not (a.get("libre") or {}).get("sons") or not video:
            return video
        try:
            return ML.mixer_sons(video, a["libre"]["sons"], os.path.splitext(video)[0] + "_sons.mp4")
        except Exception:      # noqa: BLE001
            return video

    def _apercu_remotion(self, t, a):
        """Remotion compile le code de l'IA en rendant l'aperçu léger : une erreur de compilation ou d'exécution revient à l'IA."""
        from . import motion_remotion as MR
        if not self._pret_ici():
            return a, "", []
        t.avancer(0.55, _("Remotion compile l'animation et rend l'aperçu léger (sur ce poste, gratuit)…"))
        sortie = os.path.join(M.dossier(), f"apercu_libre_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
        leger = ML.apercu_leger(dict(a, transparent=False))
        try:
            r = MR.rendre(self.params, leger, sortie,
                          lambda f, x: t.avancer(0.55 + 0.45 * f, _("Aperçu léger : {x}", x=x)), t.arret_demande)
        except MR.ErreurRemotion as e:
            return a, "", [e.journal or str(e)]
        return a, self._avec_sons(a, r), []

    def _fin_ia(self, r, e):
        if e:
            self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:400]))
            return
        if not r:
            self.etat.setText(_("Arrêté."))
            return
        a, apercu, erreurs = r
        self.anim = a
        self._erreurs = erreurs
        self._manquants = []
        if a.get("duree") and not a.get("duree_imposee"):
            self.duree.blockSignals(True)
            self.duree.setValue(0)
            self.duree.blockSignals(False)
        lib = a.get("libre") or {}
        plan, sons = ML.plan_texte(a), ML.sons_texte(a)
        pro = a.get("pro") or {}
        resume_pro = ""
        if pro.get("modele"):
            from . import motion_pro as MP
            res = lib.get("ressources") or {}
            morceaux = [_("écrite par {m}", m=MP.nom_modele(pro["modele"]))]
            if res.get("blocs"):
                morceaux.append(_("blocs : {l}", l=", ".join(res["blocs"])))
            if res.get("images"):
                morceaux.append(_("dessins : {l}", l=", ".join(res["images"])))
            if res.get("videos"):
                morceaux.append(_("effets vidéo : {l}", l=", ".join(res["videos"])))
            if pro.get("relectures"):
                morceaux.append(_("relectures : {l}", l=" ; ".join(pro["relectures"])))
            if pro.get("ratees"):
                morceaux.append(_("pas fait : {l}", l=" ; ".join(pro["ratees"])))
            resume_pro = "\n" + _("Look pro : {l}.", l=" · ".join(morceaux))
        self.message.setText(_("« {t} », {d} s — {m}", t=a.get("titre", ""), d=f"{a.get('duree', 0):g}", m=lib.get("message", ""))
                             + resume_pro
                             + (("\n" + _("Plan :") + "\n" + plan) if plan else "")
                             + (("\n" + _("Bruitages : {s}", s=sons)) if sons and a.get("bruitages", True) else "")
                             + (("\n" + _("Calée sur la musique (posée à {t} s).", t=f"{a['pose']:g}".replace(".", ",")))
                                if a.get("musique") and a.get("pose") is not None else ""))
        if erreurs:
            self.erreurs.setText(_("La composition a {n} erreur(s) qui gâcheraient le rendu :\n{e}", n=len(erreurs),
                                   e="\n".join("• " + x[:220] for x in erreurs[:5])))
            self.b_erreurs.show()
            self.etat.setText(_("Faites-les corriger par l'IA (le prix est demandé), ou décrivez autrement."))
        else:
            self.erreurs.setText("")
            self.b_erreurs.hide()
        if apercu:
            self.apercu_fichier = apercu
            self.apercu.charger(apercu, video=True)
            self.etat.setText(_("Regardez l'aperçu (léger, en petit) ; demandez des changements, ou fabriquez en qualité."))
        elif not erreurs:
            self.etat.setText(_("Animation écrite pour Remotion. Pour la voir ici, installez Remotion sur ce poste.")
                              if ML.code_de(a) == "remotion" else
                              _("Composition écrite. Pour la voir ici, installez HyperFrames sur ce poste ; ou fabriquez-la chez "
                                "HeyGen."))
        self.credit.montrer("anthropic")

    def _caler_musique(self, a):
        """Temps forts de la musique du film, en secondes de l'animation posée à la ligne rouge (calculés dans la tâche)."""
        if not self.caler.isChecked() or not self.caler.isEnabled():
            a.pop("musique", None)
            return a
        t0 = float(a["pose"]) if a.get("pose") is not None else float(self.ed.timeline.position)
        try:
            temps, forts = M.temps_musique(self.ed.projet)
        except Exception:      # noqa: BLE001 : sans calage plutôt que sans animation
            return a
        rel = [round(t - t0, 2) for t in forts if t0 <= t <= t0 + ML.DUREE_MAX]
        ecarts = [b - x for x, b in zip(temps, temps[1:])]
        bpm = round(60 / (sum(ecarts) / len(ecarts)), 1) if ecarts else 0
        tous = [round(t - t0, 2) for t in temps if t0 <= t <= t0 + ML.DUREE_MAX]      # 1.3.1 : toute la grille des temps
        if len(rel) >= 2:
            a["musique"], a["pose"] = {"forts": rel, "temps": tous, "bpm": bpm}, t0
        return a

    def verifier_etapes(self):
        """1.1.8 (Philippe, 21/11 23h02 : « il manque des animations ») : l'IA regarde une image par étape du plan."""
        if not self.apercu_fichier or not self.anim:
            return
        if not self._accord(_("L'IA va regarder l'aperçu, étape par étape"), ML.PRIX_VERIFIER):
            return
        a, video, params = copy.deepcopy(self.anim), self.apercu_fichier, self.params

        def travail(t):
            t.avancer(0.1, _("Images de chaque étape…"))
            return ML.verifier_etapes(params, a, video)

        def fin(r, e):
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
                return
            manquent = [x for x in r if not x.get("vue")]
            if not manquent:
                self.etat.setText(_("✓ Toutes les étapes du plan se voient dans l'aperçu."))
                return
            self._manquants = [_("Etape {n} ({a}–{b} s) : {t} — {r}", n=x["n"], a=x["a"], b=x["b"], t=x["texte"],
                                 r=x.get("remarque") or _("ne se voit pas")) for x in manquent]
            self.erreurs.setText(_("Ces étapes ne se voient pas dans l'aperçu :") + "\n" +
                                 "\n".join("• " + x[:220] for x in self._manquants))
            self.b_erreurs.show()               # « Faire corriger » ; la fabrication reste possible (ce n'est pas une erreur de code)
            self.etat.setText(_("Faites-les corriger par l'IA : elle reçoit la liste exacte de ce qui manque."))
        self._lancer(travail, _("Animation libre : vérification des étapes"), fin)

    def creer(self):
        if not self.description.toPlainText().strip():
            self.etat.setText(_("Décrivez d'abord l'animation, en quelques phrases."))
            return
        pro = self._pro_actif()
        from . import motion_pro as MP
        if not self._accord(_("L'IA va préparer l'animation (blocs, dessins, effets, modèle)") if pro else
                            _("L'IA va écrire l'animation"), MP.PRIX_PREPARER if pro else ML.PRIX_CREER):
            return
        a = self.lire()
        a.pop("libre", None)
        self._vider_apercu()
        self._erreurs = []
        self.erreurs.setText("")
        self.b_erreurs.hide()
        self.message.setText(_("L'IA écrit l'animation ; l'aperçu de cette nouvelle animation apparaîtra ici."))
        a = ML.fiche(a["description"], a["taille"], a.get("duree") if a.get("duree_imposee") else 0, a["charte"], a["transparent"],
                     a["moteur_libre"]) \
            | ({"duree_imposee": True} if a.get("duree_imposee") else {})

        a["pose"] = float(self.ed.timeline.position) if self.caler.isChecked() else None
        a["bruitages"] = self.bruitages.isChecked()
        if not pro:
            def travail(t):
                t.avancer(0.03, _("Musique du film : temps forts…") if self.caler.isChecked() else "")
                self._caler_musique(a)
                t.avancer(0.05, _("L'IA écrit l'animation (une à deux minutes)…"))
                b = ML.creer(self.params, a)
                return self._verifier_et_apercu(t, b)
            self._lancer(travail, _("Animation libre : écriture"), self._fin_ia)
            return
        dessins, videos, blocs = self.pro_dessins.isChecked(), self.pro_videos.isChecked(), self.pro_blocs.isChecked()
        from . import ia
        dessins = dessins and bool(ia.nettoyer_clef(self.params.get("clef_gemini", "")))
        videos = videos and MP.modele_video(self.params) is not None
        params = self.params

        a["avec_3d"] = a["avec_pixel"] = self.pro_3d.isChecked()
        a["avec_plans"] = blocs

        def travail(t):
            t.avancer(0.2, _("L'IA prépare : blocs, dessins, effets, complexité…"))
            prep = MP.preparer(params, dict(a, moteur_libre=a["moteur_libre"] if blocs or a["avec_pixel"] else "remotion"),
                               dessins, videos)
            if not blocs:
                prep["blocs"] = []
            return prep
        self._lancer(travail, _("Motion design IA : préparation"), lambda r, e: self._apres_preparation(a, r, e))

    def _apres_preparation(self, a, prep, e):
        from . import motion_pro as MP
        if e:
            self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:400]))
            return
        fam, modele = MP.modele(self.params, prep["complexite"], self.pro_modele.currentData())
        tours = self.pro_tours.value()
        prix = MP.prix(prep, modele, self.params, tours)
        lignes = [prep.get("pourquoi") or "",
                  _("Complexité {c}/3 : écrite par {m}.", c=prep["complexite"], m=MP.nom_modele(modele))]
        if prep["blocs"]:
            lignes.append(_("Blocs : {l}.", l=", ".join(prep["blocs"])))
        if prep.get("pixel"):
            lignes.append(_("Effets pixel (gratuits) : {l}.", l=", ".join(prep["pixel"])))
        if prep.get("plans"):
            lignes.append(_("Plans tout prêts (Video ShotCraft) : {l}.", l=", ".join(prep["plans"])))
        if prep["images"]:
            lignes.append(_("Dessins ({p} $) : {l}.", p=_prix(prix["dessins"]), l=", ".join(x["id"] for x in prep["images"])))
        if prep["videos"]:
            m = MP.modele_video(self.params)
            lignes.append(_("Effets vidéo par {m} ({p} $) : {l}.", m=(m or {}).get("nom", "?"), p=_prix(prix["videos"]),
                            l=", ".join(x["id"] for x in prep["videos"])))
        lignes.append(_("Ecriture : {p} $ ; relectures ({n} au plus) : jusqu'à {r} $.", p=_prix(prix["ecrire"]), n=tours,
                        r=_prix(prix["relecture"])))
        texte = "\n".join(x for x in lignes if x)
        self.message.setText(texte)
        if not self._accord(texte + "\n\n" + _("Total au plus"), prix["total"]):
            self.etat.setText(_("Rien n'a été fabriqué ; changez les réglages « Look pro » ou la description, puis reconstruisez."))
            return
        params, params_m = self.params, MP.params_modele(self.params, fam, modele)
        dossier = os.path.join(M.dossier(), "ressources", time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(dossier, exist_ok=True)
        format_ = "9:16" if a["taille"][1] > a["taille"][0] else ("1:1" if a["taille"][0] == a["taille"][1] else "16:9")
        a["pro"] = {"prep": prep, "famille": fam, "modele": modele, "relectures": []}

        def travail(t):
            res = {"images": {}, "videos": {}, "blocs": {}, "pixel": {}, "plans": {}}
            ratees = []
            n = len(prep["images"]) + len(prep["videos"]) + len(prep["blocs"]) + len(prep.get("plans") or [])
            infos = {e["id"]: e for e in MP.catalogue_pixel()}           # 1.3.1 : effets pixel, rien à télécharger
            for i in prep.get("pixel") or []:
                if i in infos:
                    res["pixel"][i] = infos[i]
            k = 0
            for img in prep["images"]:
                k += 1
                t.avancer(0.02 + 0.25 * k / max(1, n), _("Dessin « {i} » (Gemini)…", i=img["id"]))
                try:
                    res["images"][img["id"]] = dict(MP.dessiner(params, img, dossier), en=img["en"])
                except Exception as err:      # noqa: BLE001 : sans ce dessin plutôt que sans animation
                    ratees.append(_("dessin « {i} » : {e}", i=img["id"], e=texte_erreur(err)[:120]))
                if t.arret_demande():
                    return None
            for vid in prep["videos"]:
                k += 1
                t.avancer(0.02 + 0.25 * k / max(1, n), _("Effet vidéo « {i} » (une à trois minutes)…", i=vid["id"]))
                try:
                    res["videos"][vid["id"]] = dict(MP.filmer(params, vid, dossier, format_, arret=t.arret_demande), en=vid["en"])
                except Exception as err:      # noqa: BLE001
                    ratees.append(_("effet « {i} » : {e}", i=vid["id"], e=texte_erreur(err)[:120]))
                if t.arret_demande():
                    return None
            for nom in prep["blocs"]:
                k += 1
                t.avancer(0.02 + 0.25 * k / max(1, n), _("Bloc « {i} » (bibliothèque HyperFrames)…", i=nom))
                try:
                    res["blocs"][nom] = MP.source_bloc(nom)
                except Exception as err:      # noqa: BLE001
                    ratees.append(_("bloc « {i} » : {e}", i=nom, e=texte_erreur(err)[:120]))
            for nom in prep.get("plans") or []:
                k += 1
                t.avancer(0.02 + 0.25 * k / max(1, n), _("Plan « {i} » (Video ShotCraft)…", i=nom))
                try:
                    res["plans"][nom] = MP.source_plan(nom, avec_demo=a.get("moteur_libre") == "remotion")
                except Exception as err:      # noqa: BLE001
                    ratees.append(_("plan « {i} » : {e}", i=nom, e=texte_erreur(err)[:120]))
            a["libre"] = {"ressources": res}
            a["pro"]["ratees"] = ratees
            self._caler_musique(a)
            t.avancer(0.3, _("{m} écrit l'animation (une à trois minutes)…", m=MP.nom_modele(modele)))
            b = ML.creer(params_m, a)
            return self._relire(t, b, params, params_m, self.pro_tours.value())
        self._lancer(travail, _("Motion design IA : fabrication"), self._fin_ia)

    def _relire(self, t, b, params, params_m, tours):
        """1.1.16 : l'IA regarde son rendu (une image par étape) et fait corriger ce qui ne se voit pas, `tours` fois au plus ;
        une erreur de code est aussi renvoyée à corriger. Renvoie (anim, aperçu, erreurs) comme _verifier_et_apercu."""
        b, apercu, erreurs = self._verifier_et_apercu(t, b)
        for n in range(tours):
            if t.arret_demande():
                break
            if erreurs:
                t.avancer(0.62, _("Relecture {n}/{m} : l'IA corrige une erreur de code…", n=n + 1, m=tours))
                b = ML.corriger(params_m, b, erreur="\n".join(erreurs))
                b.setdefault("pro", {}).setdefault("relectures", []).append(_("erreur de code corrigée"))
            elif apercu:
                t.avancer(0.62, _("Relecture {n}/{m} : l'IA regarde son aperçu, étape par étape…", n=n + 1, m=tours))
                try:
                    vus = ML.verifier_etapes(params, b, apercu)
                except Exception:      # noqa: BLE001 : la relecture est un plus
                    break
                manquent = [x for x in vus if not x.get("vue")]
                if not manquent:
                    b.setdefault("pro", {}).setdefault("relectures", []).append(_("tout se voit"))
                    break
                remarque = "These steps are not visible in the render, fix them so each one clearly shows: " + "; ".join(
                    f"step {x['n']} ({x['a']:g}-{x['b']:g} s) {x['texte']} -> {x.get('remarque') or 'not visible'}" for x in manquent)
                t.avancer(0.66, _("Relecture {n}/{m} : {k} étape(s) à corriger…", n=n + 1, m=tours, k=len(manquent)))
                b = ML.corriger(params_m, b, remarque=remarque)
                b.setdefault("pro", {}).setdefault("relectures", []).append(_("{k} étape(s) corrigée(s)", k=len(manquent)))
            else:
                break
            b, apercu, erreurs = self._verifier_et_apercu(t, b)
        return b, apercu, erreurs

    def corriger(self, erreur=""):
        remarque = self.remarque.text().strip() if not erreur else ""
        transposer = bool(self.anim and ML.code_de(self.anim) and ML.code_de(self.anim) != self.moteur_choisi())
        if not erreur and not remarque and not transposer:
            self.etat.setText(_("Ecrivez d'abord ce qu'il faut changer."))
            return
        if not self._accord(_("L'IA va reprendre l'animation"), ML.PRIX_CORRIGER):
            return
        a = self.lire()

        pro = a.get("pro") or {}
        from . import motion_pro as MP
        params = MP.params_modele(self.params, pro["famille"], pro["modele"]) if pro.get("modele") else self.params

        def travail(t):
            self._caler_musique(a)
            t.avancer(0.05, _("L'IA reprend l'animation…"))
            b = ML.corriger(params, a, remarque, erreur)
            return self._verifier_et_apercu(t, b)

        def fin(r, e):
            if not e:
                self.remarque.clear()
            self._fin_ia(r, e)
        self._lancer(travail, _("Animation libre : changements"), fin)

    def version_avant(self):
        if not self.anim:
            return
        a = ML.revenir(self.lire())
        self._lancer(lambda t: self._verifier_et_apercu(t, a), _("Animation libre : version d'avant"), self._fin_ia)

    def installer(self):
        from . import packs_ia, motion_remotion as MR
        remotion = self.moteur_choisi() == "remotion"

        def travail(t):
            if not packs_ia.moteur_installe("motion"):
                packs_ia.installer("motion_html", (lambda f, x: t.avancer(f * (0.5 if remotion else 1), x)), t.arret_demande)
            if remotion and not MR.pret():
                MR.installer(self.params, lambda f, x: t.avancer(0.5 + 0.5 * f, x), t.arret_demande)
            return True
        nom = "Remotion" if remotion else "HyperFrames"
        self._lancer(travail, _("Installation de {m}", m=nom),
                     lambda r, e: self.etat.setText("✕ " + texte_erreur(e) if e else _("✓ {m} est installé.", m=nom)))

    def ouvrir_projet(self):
        from . import motion_html as MH, motion_remotion as MR
        a = self.lire()
        d = os.path.join(M.dossier(), "projets", time.strftime("%Y%m%d_%H%M%S") + "_libre")
        if ML.code_de(a) == "remotion":
            MR.projet_libre(a, d + "_remotion")
            d += "_remotion"
        else:
            MH.preparer_projet(a, d, gsap_en_ligne=not MH.gsap_local())
        if not getattr(self, "_test_oui", False):
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        return d

    def fabriquer(self):
        from .dialogues_motion import ResultatAnimation
        a, k = self.lire(), self.moteur.currentData()
        ok, quoi = M.etat(k, self.params)
        if not ok:
            self.etat.setText(_("Moteur « {m} » : {e}.", m=M.MOTEURS[k]["nom"], e=quoi))
            return
        p = M.prix(a, k)
        if p and not getattr(self, "_test_oui", False) and QMessageBox.question(
                self, _("Rendu payant"), _("HeyGen va rendre l'animation : environ {p} $ sur votre crédit HeyGen. Continuer ?",
                                           p=_prix(p))) != QMessageBox.Yes:
            return
        sortie = M.sortie_pour(a)

        def fin(r, e):
            if e or not r:
                self.etat.setText("✕ " + (texte_erreur(e) if e else _("rien n'a été fabriqué")))
                return
            self.resultat = r
            self.etat.setText(_("✓ Animation fabriquée."))
            if not getattr(self, "_test_oui", False):
                ResultatAnimation(self.ed, r, a).exec()
        self._lancer(lambda t: M.fabriquer(self.params, a, sortie, k, t.avancer, t.arret_demande),
                     _("Animation libre : {m}", m=M.MOTEURS[k]["nom"]), fin)

    # ------------------------------------------------------------------ modèles (1.1.3)
    def garder_modele(self):
        from .dialogues_bibliotheque_creations import garder_rapide
        a = self.lire()
        if not ML.code_de(a) and not a.get("description"):
            self.etat.setText(_("Décrivez d'abord l'animation (ou faites-la construire) pour la garder."))
            return None
        garde = {k: a.get(k) for k in ("description", "taille", "duree", "duree_imposee", "transparent", "moteur_libre", "titre",
                                       "libre", "genre", "cadence")}
        garde["libre"] = {k: v for k, v in (a.get("libre") or {}).items() if k != "historique"}
        x = garder_rapide(self, self.params, "modele_animation", a.get("titre") or a.get("description", "")[:50] or _("Animation"),
                          a.get("description", ""), None, {"anim": garde})
        if x:
            self.etat.setText(_("✓ Modèle « {n} » gardé : « Reprendre un modèle… » le remet, sans repayer l'IA.", n=x["nom"]))
        return x

    def reprendre_modele(self):
        from .dialogues_bibliotheque_creations import choisir_entree
        e = choisir_entree(self, self.params, ("modele_animation",))
        if e is None:
            return None
        self.appliquer_anim((e.get("donnees") or {}).get("anim") or {}, e["nom"])
        return e

    def appliquer_anim(self, anim, nom=""):
        """Une animation remise telle quelle (modèle gardé, ou création en cours reprise, 1.2.1) : rien de payé n'est refait."""
        a = dict(ML.fiche(""), **(anim or {}))
        a.setdefault("libre", {}).setdefault("historique", [])
        a["charte"] = self.charte.currentData()
        self.anim = a
        self.description.setPlainText(a.get("description", ""))
        t = list(a.get("taille") or (1920, 1080))
        i = next((k for k in range(self.format.count()) if list(self.format.itemData(k)) == t), 0)
        self.format.setCurrentIndex(i)
        self.duree.setValue(float(a.get("duree") or 0) if a.get("duree_imposee") else 0)
        self.transparent.setChecked(bool(a.get("transparent")))
        self.moteur_libre.setCurrentIndex(max(0, self.moteur_libre.findData(ML.moteur_de(a))))
        self.etat.setText(_("✓ « {n} » repris.", n=nom))
        if ML.code_de(a):
            self._lancer(lambda t: self._verifier_et_apercu(t, self.lire()), _("Animation libre : modèle"), self._fin_ia)
        self._maj()
        return a

    # ------------------------------------------------------------------ fenêtre
    def a_garder(self):
        """Il y a un travail à ne pas perdre (description écrite ou animation construite)."""
        try:
            return bool(self.anim or self.description.toPlainText().strip())
        except RuntimeError:
            return False

    def _vider_apercu(self):
        """1.1.9 : l'aperçu d'une autre animation ne reste jamais affiché (Philippe : « ça reprend l'ancienne animation »)."""
        try:
            self.apercu.arreter()
            from PySide6.QtCore import QUrl
            if getattr(self.apercu, "lecteur", None) is not None:
                self.apercu.lecteur.setSource(QUrl())
        except Exception:      # noqa: BLE001
            pass
        self.apercu_fichier = ""

    def reduire(self):
        from .widgets import reafficher
        self.apercu.arreter() if hasattr(self.apercu, "arreter") else None
        self.hide()
        e = getattr(self.ed, "encart", None)
        if e is not None and getattr(e, "tache", None) is None:
            e.suivre_message(_("Animation libre rangée : votre travail est gardé."),
                             (_("Afficher l'animation libre"), lambda: reafficher(self)), 20000)

    def nouvelle(self):
        if self.tache and self.tache.isRunning():
            self.etat.setText(_("Attendez la fin du calcul en cours."))
            return
        if self.anim and not getattr(self, "_test_oui", False) and QMessageBox.question(
                self, self.windowTitle(), _("Oublier l'animation en cours et repartir de zéro ?")) != QMessageBox.Yes:
            return
        self.anim, self._erreurs, self.apercu_fichier, self.resultat = None, [], "", ""
        self._vider_apercu()
        self.description.clear()
        self.remarque.clear()
        self.erreurs.setText("")
        self.b_erreurs.hide()
        self.message.setText(_("L'aperçu apparaîtra ici (rendu léger sur ce poste, gratuit)."))
        self.apercu.arreter() if hasattr(self.apercu, "arreter") else None
        self.etat.setText("")
        self._maj()

    def done(self, r):
        from .widgets import calcul_en_cours, garder_calcul
        if garder_calcul(self, calcul_en_cours(self)):
            return
        if self.a_garder():                    # fermer ne perd jamais le travail (Philippe, 21/11 20h15)
            self.reduire()
            return
        self.apercu.arreter() if hasattr(self.apercu, "arreter") else None
        super().done(r)
