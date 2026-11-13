"""Atelier IA (0.6, 0.7) : effets IA locaux sur une image du film, sur la partie en jaune, pour un logo ou une musique.

A gauche, le catalogue (par famille, cherchable) ; à droite, la phrase modifiable, la force, l'image source et le résultat
côte à côte. Rien ne part sur Internet ; « Créer » lance le moteur du poste en tâche de fond (barre du bas).
"""
import os, time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QProgressBar, QPushButton, QSlider, QSplitter, QVBoxLayout, QWidget)

from . import creatif as C, effets_ia as EI, moteur, traduction_recherche as TR
from .langue import _
from .projet import fin_clip
from .taches import Tache


def _dossier_sorties():
    from .creations import dossier
    return dossier()


class DialogueAtelierIA(QDialog):
    """Non bloquante (0.9.51) : on continue à travailler dans le film pendant le calcul ; la fermer pendant un calcul la
    range seulement (« Afficher l'Atelier » dans la barre du bas)."""

    def __init__(self, ed, famille="image"):
        super().__init__(ed)
        self.setModal(False)
        self.ed = ed
        self.setWindowTitle(_("Atelier IA (sur ce poste)"))
        self.resize(1040, 680)
        self.tache, self.resultat, self.source = None, None, None
        v = QVBoxLayout(self)
        aide = QLabel(_("Effets IA qui tournent sur votre ordinateur : gratuits, rien n'est envoyé (sauf votre phrase au service de traduction "
                        "gratuit MyMemory si elle n'est pas en anglais). Choisissez un effet, modifiez sa phrase si vous voulez (vos changements "
                        "sont gardés), puis « Créer ». Sans carte graphique, comptez plus longtemps."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        sp = QSplitter(Qt.Horizontal)
        gauche = QWidget()
        vg = QVBoxLayout(gauche)
        vg.setContentsMargins(0, 0, 0, 0)
        self.famille = QComboBox()
        for k, lib in EI.FAMILLES.items():
            self.famille.addItem(lib, k)
        self.famille.setCurrentIndex(max(0, self.famille.findData(famille)))
        self.famille.currentIndexChanged.connect(self._remplir)
        vg.addWidget(self.famille)
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(_("Chercher un effet…"))
        self.cherche.textChanged.connect(self._remplir)
        vg.addWidget(self.cherche)
        self.liste = QListWidget()
        self.liste.setWordWrap(True)                  # noms longs à la ligne : jamais de défilement horizontal
        self.liste.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.liste.setTextElideMode(Qt.ElideNone)
        self.liste.setResizeMode(QListWidget.Adjust)
        self.liste.currentItemChanged.connect(self._choisi)
        vg.addWidget(self.liste, 1)
        sp.addWidget(gauche)
        droite = QWidget()
        vd = QVBoxLayout(droite)
        vd.setContentsMargins(6, 0, 0, 0)
        self.titre = QLabel("")
        self.titre.setStyleSheet("font-weight:600;font-size:15px")
        vd.addWidget(self.titre)
        self.etat_modele = QLabel("")
        self.etat_modele.setWordWrap(True)
        vd.addWidget(self.etat_modele)
        self.lbl_prompt = QLabel(_("Phrase pour l'IA : écrivez dans votre langue, PhilCut la traduit en anglais (la seule langue que les moteurs comprennent bien)"))
        self.lbl_prompt.setWordWrap(True)
        vd.addWidget(self.lbl_prompt)
        self.prompt = QPlainTextEdit()
        self.prompt.setMaximumHeight(70)
        self.prompt.setPlaceholderText(_("ex. : « une ballade chantée à la manière de Sinatra », « un cow-boy à la John Wayne, look Star Wars »"))
        hp_ = QHBoxLayout()
        hp_.addWidget(self.prompt, 1)
        self.b_styles = QPushButton(_("Style « à la manière de »…"))
        self.b_styles.setToolTip(_("Choisir un chanteur, un groupe, un acteur, un film ou un réalisateur : PhilCut ajoute « à la manière de … » "
                                   "à la phrase et le remplace par la description de son style (voix, orchestre, image, jeu)"))
        self.b_styles.clicked.connect(self._choisir_style)
        hp_.addWidget(self.b_styles, 0, Qt.AlignTop)
        vd.addLayout(hp_)
        # 0.9.61 : l'anglais envoyé au moteur, visible et modifiable pendant qu'on écrit (règle : on voit les deux)
        from .consigne_bilingue import AnglaisEnDirect
        self.prompt_en = AnglaisEnDirect(self.prompt, self._anglais_de)
        vd.addWidget(self.prompt_en)
        self.envoye = QLabel("")
        self.envoye.setWordWrap(True)
        self.envoye.setStyleSheet("color:#9aa4b2")
        self.envoye.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.envoye.hide()
        vd.addWidget(self.envoye)
        # « à la manière de Sinatra », « un cow-boy à la John Wayne » : le nom devient la description du style (0.9.20)
        self.style_info = QLabel("")
        self.style_info.setWordWrap(True)
        self.style_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.style_info.hide()
        vd.addWidget(self.style_info)
        self.boite_style = QWidget()
        hs = QHBoxLayout(self.boite_style)
        hs.setContentsMargins(0, 0, 0, 0)
        self.niveau_style = QComboBox()
        self.niveau_style.addItem(_("IA locale (sur ce poste)"), "locale")
        self.niveau_style.addItem(_("IA cloud (votre clef)"), "cloud")
        self.niveau_style.setCurrentIndex(1 if (self.ed.params.get("assistant_niveau") or "") == "cloud" else 0)
        hs.addWidget(self.niveau_style)
        self.b_style = QPushButton(_("Transposer ce style avec l'IA"))
        self.b_style.setToolTip(_("L'IA décrit le style de ce nom (voix, orchestre, époque, image, jeu d'acteur) sans le nommer ni copier "
                                  "la personne ; la description est gardée dans Préférences › Assistant et IA › Styles. Rien n'est envoyé sans ce clic."))
        self.b_style.clicked.connect(self._transposer_ia)
        hs.addWidget(self.b_style)
        hs.addStretch(1)
        self.boite_style.hide()
        vd.addWidget(self.boite_style)
        self.prompt.textChanged.connect(self._maj_style)
        hf = QHBoxLayout()
        self.lbl_force = QLabel(_("Force"))
        hf.addWidget(self.lbl_force)
        self.force = QSlider(Qt.Horizontal)
        self.force.setRange(5, 100)
        hf.addWidget(self.force, 1)
        self.val_force = QLabel("")
        self.val_force.setMinimumWidth(130)
        self.force.valueChanged.connect(self._texte_force)
        hf.addWidget(self.val_force)
        vd.addLayout(hf)
        # musique
        self.boite_musique = QWidget()
        hm = QHBoxLayout(self.boite_musique)
        hm.setContentsMargins(0, 0, 0, 0)
        hm.addWidget(QLabel(_("Durée")))
        self.duree = QDoubleSpinBox()
        self.duree.setRange(10, 240)
        self.duree.setSuffix(" s")
        self.duree.setValue(max(10.0, min(240.0, round(self.ed.projet.duree() or 60.0))))
        hm.addWidget(self.duree)
        self.instrumental = QCheckBox(_("Sans paroles"))
        self.instrumental.setChecked(True)
        hm.addWidget(self.instrumental)
        from . import paroles as PA
        self.voix_chant = QComboBox()
        for k, (lib, _en) in PA.VOIX.items():
            self.voix_chant.addItem(lib, k)
        self.voix_chant.setToolTip(_("Qui chante, et de quelle manière (crooner, rauque, soul, lyrique…). Une manière plus précise : "
                                     "écrivez-la dans la phrase (« chanté à la manière de … », « voix de crooner »)."))
        hm.addWidget(self.voix_chant)
        self.b_essai_voix = QPushButton("▶ " + _("Essayer la voix"))
        self.b_essai_voix.setToolTip(_("Fabrique 15 secondes avec cette voix et cette langue pour l'écouter avant le vrai morceau "
                                       "(une à quelques minutes sur ce poste)"))
        self.b_essai_voix.clicked.connect(self._essayer_voix)
        hm.addWidget(self.b_essai_voix)
        self.langue_chant = QComboBox()
        for k, lib in PA.LANGUES.items():
            self.langue_chant.addItem(lib, k)
        from .langue import LANGUE
        self.langue_chant.setCurrentIndex(max(0, self.langue_chant.findData(LANGUE)))
        self.langue_chant.setToolTip(_("Langue des paroles"))
        hm.addWidget(self.langue_chant)
        hm.addStretch(1)
        # paroles : plusieurs lignes, écrites à la main ou par l'IA (thème + début de paroles)
        self.boite_paroles = QWidget()
        vp = QVBoxLayout(self.boite_paroles)
        vp.setContentsMargins(0, 0, 0, 0)
        self.paroles = QPlainTextEdit()
        self.paroles.setPlaceholderText(_("Paroles : tapez-les, ou seulement le début, puis « Écrire les paroles par l'IA ». Balises "
                                          "possibles : [verse] couplet, [chorus] refrain, [bridge], [outro]."))
        self.paroles.setMaximumHeight(130)
        vp.addWidget(self.paroles)
        hpa = QHBoxLayout()
        self.niveau_paroles = QComboBox()
        self.niveau_paroles.addItem(_("IA locale (sur ce poste)"), "locale")
        self.niveau_paroles.addItem(_("IA cloud (votre clef)"), "cloud")
        self.niveau_paroles.setCurrentIndex(1 if (self.ed.params.get("assistant_niveau") or "") == "cloud" else 0)
        hpa.addWidget(self.niveau_paroles)
        self.b_paroles = QPushButton(_("Écrire les paroles par l'IA (thème + début)"))
        self.b_paroles.setToolTip(_("L'IA écrit des paroles sur le thème de la phrase ci-dessus ; si vous avez tapé un début, elle le "
                                    "garde et continue. Rien n'est envoyé sans ce clic."))
        self.b_paroles.clicked.connect(self._ecrire_paroles)
        hpa.addWidget(self.b_paroles)
        hpa.addStretch(1)
        vp.addLayout(hpa)
        self.boite_paroles.setVisible(False)

        def bascule(sans):
            self.boite_paroles.setVisible(not sans)
            self.voix_chant.setEnabled(not sans)
            self.b_essai_voix.setEnabled(not sans)
            self.langue_chant.setEnabled(not sans)
        self.instrumental.toggled.connect(bascule)
        bascule(True)
        vd.addWidget(self.boite_musique)
        vd.addWidget(self.boite_paroles)
        self._construire_replique(vd)
        hi = QHBoxLayout()
        self.img_source = QLabel()
        self.img_resultat = QLabel()
        for lb, t in ((self.img_source, _("Image du film (ligne rouge)")), (self.img_resultat, _("Résultat"))):
            lb.setFixedSize(360, 203)
            lb.setAlignment(Qt.AlignCenter)
            lb.setStyleSheet("background:#000;border-radius:6px;color:#888")
            lb.setText(t)
            hi.addWidget(lb)
        hi.addStretch(1)
        vd.addLayout(hi)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vd.addWidget(self.info)
        from .widgets import SuiviAttente
        self.suivi = SuiviAttente()                       # attente sans pourcentage : on voit que ça travaille (0.9.31)
        vd.addWidget(self.suivi)
        self.apercu_media = ApercuCreation(self)          # musique, clip : écouter / regarder et garder le morceau avant de poser
        vd.addWidget(self.apercu_media)
        # avancement de l'IA, visible dans la fenêtre (en plus de la barre du bas et du Centre d'activité)
        self.etape = QLabel("")
        self.etape.setWordWrap(True)
        self.etape.hide()
        vd.addWidget(self.etape)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        vd.addWidget(self.barre)
        self._horloge = QTimer(self)
        self._horloge.setInterval(1000)
        self._horloge.timeout.connect(self._tic)
        self._t0, self._fraction = 0.0, 0.0
        hb = QHBoxLayout()
        self.b_creer = QPushButton(_("Créer"))
        self.b_creer.setStyleSheet("font-weight:600;padding:6px 18px")
        self.b_creer.clicked.connect(self.creer)
        hb.addWidget(self.b_creer)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.hide()
        self.b_arreter.clicked.connect(self.arreter)
        hb.addWidget(self.b_arreter)
        self.b_garder = QPushButton(_("Garder ma phrase"))
        self.b_garder.setToolTip(_("La phrase et la force modifiées remplacent celles de l'effet (« Rétablir » revient à l'original)."))
        self.b_garder.clicked.connect(lambda: self._enregistrer(False))
        hb.addWidget(self.b_garder)
        self.b_nouveau = QPushButton(_("Enregistrer comme mon effet"))
        self.b_nouveau.clicked.connect(lambda: self._enregistrer(True))
        hb.addWidget(self.b_nouveau)
        self.b_retablir = QPushButton(_("Rétablir"))
        self.b_retablir.clicked.connect(self._retablir)
        hb.addWidget(self.b_retablir)
        hb.addStretch(1)
        vd.addLayout(hb)
        self.actions = QHBoxLayout()
        vd.addLayout(self.actions)
        from .dialogues_diagnostic import PanneauDiagnostic
        self.diagnostic = PanneauDiagnostic(self, self.ed.params, reessayer=self.creer)       # échec : cause et solutions
        vd.addWidget(self.diagnostic)
        vd.addStretch(1)
        b_pref = QPushButton(_("Modèles IA du poste (Préférences)…"))
        b_pref.setStyleSheet("text-align:left;padding:3px 8px")
        b_pref.clicked.connect(self._preferences)
        hp = QHBoxLayout()
        hp.addWidget(b_pref)
        hp.addStretch(1)
        vd.addLayout(hp)
        sp.addWidget(droite)
        sp.setSizes([290, 750])
        v.addWidget(sp, 1)
        self._remplir()
        self._charger_source()

    # ---- catalogue
    def _remplir(self, *_a):
        fam = self.famille.currentData()
        txt = self.cherche.text().strip().lower()
        self.liste.blockSignals(True)
        self.liste.clear()
        import unicodedata

        def cle(e):                                   # ordre alphabétique (accents ignorés), vos effets ★ d'abord
            n = unicodedata.normalize("NFD", e["nom"]).encode("ascii", "ignore").decode().lower()
            return (not e.get("perso"), n)
        for e in sorted(EI.tous(self.ed.params), key=cle):
            if e["famille"] != fam or (txt and txt not in e["nom"].lower() and txt not in e.get("prompt", "").lower()):
                continue
            ok, _m = EI.disponible(e, self.ed.params)
            it = QListWidgetItem(("★ " if e.get("perso") else "") + e["nom"] + ("" if ok else "  ⚠"))
            it.setData(Qt.UserRole, e)
            if not ok:
                it.setToolTip(_m)
            self.liste.addItem(it)
        self.liste.blockSignals(False)
        if self.liste.count():
            self.liste.setCurrentRow(0)
        self._choisi(self.liste.currentItem(), None)

    def effet(self):
        it = self.liste.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _choisi(self, it, _avant=None):
        e = it.data(Qt.UserRole) if it else None
        if not e:
            return
        self.titre.setText(e["nom"])
        ok, manque = EI.disponible(e, self.ed.params)
        self.etat_modele.setText(("✓ " + _("Prêt sur ce poste.")) if ok else ("⚠ " + manque))
        self.etat_modele.setStyleSheet("color:#7fd18b" if ok else "color:#ffb347")
        avec_phrase = e["moteur"] in ("image", "video", "musique")
        self.prompt.setVisible(avec_phrase)
        self.prompt_en.setVisible(avec_phrase and (e["famille"] in ("musique", "image", "logo") or e["moteur"] == "video"))
        self.lbl_prompt.setVisible(avec_phrase)
        self.b_styles.setVisible(avec_phrase)
        self.prompt.setPlainText(e.get("prompt", ""))
        self.boite_musique.setVisible(e["moteur"] == "musique")
        self.boite_replique.setVisible(e["famille"] == "video")
        reglable = e["moteur"] in ("image", "profondeur", "photo3d", "upscale", "interpolation", "video", "transition3d")
        for w in (self.force, self.lbl_force, self.val_force):
            w.setVisible(reglable)
        f = float(e.get("force", 0.5))
        self.force.blockSignals(True)
        self.force.setValue(int({"profondeur": f / 30, "photo3d": f / 0.15, "upscale": f / 4, "interpolation": f / 8, "video": f / 5, "transition3d": f / 2}.get(e["moteur"], f) * 100))
        self.force.blockSignals(False)
        self._texte_force()
        self.img_source.setVisible(e["famille"] != "musique" and not e.get("sans_source"))
        self.img_resultat.setVisible(e["famille"] != "musique")
        self.b_garder.setEnabled(avec_phrase or reglable)
        self.b_retablir.setEnabled(bool(e.get("modifie")))
        self.info.setText(self._explication(e))

    def _valeur_force(self, e=None):
        e = e or self.effet() or {}
        x = self.force.value() / 100
        return {"profondeur": round(x * 30), "photo3d": round(x * 0.15, 3), "upscale": 4 if x > 0.75 else 2,
                "interpolation": 8 if x > 0.75 else (4 if x > 0.35 else 2), "video": round(1 + x * 4, 1),
                "transition3d": round(max(0.6, x * 2), 1)}.get(e.get("moteur"), round(x, 2))

    def _texte_force(self):
        e = self.effet() or {}
        v = self._valeur_force(e)
        self.val_force.setText({"image": _("{p} % de l'image refaite", p=int(v * 100)), "profondeur": _("flou {v}", v=v),
                                "photo3d": _("mouvement {p} %", p=int(v * 100)), "upscale": f"×{v}", "interpolation": _("ralenti ×{v}", v=v),
                                "video": _("{v} s", v=v), "transition3d": _("{v} s", v=v)}.get(e.get("moteur"), str(v)))

    def _explication(self, e):
        m = e["moteur"]
        if e["famille"] == "video":
            z = self._partie()
            ou = _("de {a} à {b}", a=_tc(z[0]), b=_tc(z[1])) if z else _("— placez la ligne rouge sur un plan ou choisissez une partie en jaune")
            if m == "transition3d":
                return _("La caméra plonge dans la dernière image du plan qui part et ressort de la première du suivant ; le clip est posé "
                         "au-dessus du raccord le plus proche de la ligne rouge.")
            if m in ("photo3d", "video"):
                return _("A partir de l'image à la ligne rouge ; le clip créé est posé au-dessus (piste Vidéo 2).")
            return _("Passage traité : {o}. Le résultat est posé au-dessus, sur la piste Vidéo 2 (supprimable, l'original reste).", o=ou)
        if e["famille"] == "musique":
            return _("Le morceau est posé sur la piste Musique, à la durée choisie, avec des fondus.")
        if e.get("sans_source"):
            return _("Image créée à partir de la phrase seule.")
        return _("L'image du film à la ligne rouge est redessinée selon la phrase ; « Force » règle combien elle change.")

    def _enregistrer(self, nouveau):
        e = self.effet()
        if not e:
            return
        nom = None
        if nouveau:
            from PySide6.QtWidgets import QInputDialog
            nom, ok = QInputDialog.getText(self, _("Mon effet"), _("Nom de l'effet"), text=e["nom"])
            if not ok or not nom.strip():
                return
        EI.enregistrer(self.ed.params, e, self.prompt.toPlainText().strip(), self._valeur_force(e), nom, nouveau)
        self._remplir()
        self.info.setText(_("Effet enregistré."))

    def _retablir(self):
        e = self.effet()
        if e:
            EI.retablir(self.ed.params, e["id"])
            self._remplir()

    def _preferences(self):
        f = self.ed.window()
        if hasattr(f, "preferences"):
            f.preferences("IA locale")
        self._remplir()

    # ---- source
    def _charger_source(self):
        from .dialogues_video import image_projet
        t = self.ed.timeline.position
        png = image_projet(self.ed.projet, t, 768)
        if png:
            chemin = os.path.join(_dossier_sorties(), "_source.png")
            with open(chemin, "wb") as f:
                f.write(png)
            self.source = chemin
            px = QPixmap(chemin)
            self.img_source.setPixmap(px.scaled(360, 203, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _raccord(self):
        """(dernière image du plan qui part, première du plan qui arrive, instant du raccord) le plus proche de la tête."""
        import cv2
        import numpy as np
        t = self.ed.timeline.position
        cs = sorted(self.ed.projet.clips_piste("video"), key=lambda c: c["debut"])
        paires = [(a, b) for a, b in zip(cs, cs[1:]) if abs(fin_clip(a) - b["debut"]) < 0.05]
        if not paires:
            return None
        a, b = min(paires, key=lambda p: abs(p[1]["debut"] - t))
        imgs = []
        for c, instant in ((a, float(a["src_fin"]) - 0.05), (b, float(b["src_debut"]) + 0.02)):
            med = self.ed.projet.media(c["media"])
            if not med:
                return None
            if med.get("genre") == "image":
                imgs.append(cv2.imread(med["chemin"]))
            else:
                png = moteur.image(med["chemin"], max(0.0, instant), 960)
                imgs.append(cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR))
        return imgs[0], imgs[1], b["debut"]

    def _partie(self):
        tl = self.ed.timeline
        z = tl.zone_valide() if hasattr(tl, "zone_valide") else None
        if z:
            return z
        c = self.ed.projet.clip_a(tl.position, "video")
        if c:
            return (c["debut"], min(fin_clip(c), c["debut"] + 10.0))
        return None

    # ---- réplique dite (0.9.21) : un moteur de voix à part, avec le phrasé du style, mêlé au clip
    def _construire_replique(self, vd):
        from . import diction as DI
        self.boite_replique = QWidget()
        vr = QVBoxLayout(self.boite_replique)
        vr.setContentsMargins(0, 4, 0, 0)
        t = QLabel(_("Réplique dite (facultatif) : un moteur de voix à part la dit avec la manière de parler choisie, puis elle est "
                     "mêlée au clip. La vidéo donne le jeu, la voix donne le phrasé."))
        t.setWordWrap(True)
        vr.addWidget(t)
        self.replique = QPlainTextEdit()
        self.replique.setPlaceholderText(_("ex. : Ici, c'est moi qui fais la loi."))
        self.replique.setMaximumHeight(52)
        vr.addWidget(self.replique)
        h1 = QHBoxLayout()
        self.diction = QComboBox()
        self.diction.addItem(_("Manière de parler : celle du style de la phrase"), "auto")
        for k, (lib, _r) in DI.STYLES.items():
            self.diction.addItem(lib, k)
        h1.addWidget(self.diction, 1)
        self.moteur_replique = QComboBox()
        self.moteur_replique.addItem(_("Voix locale (sur ce poste, gratuit)"), "local")
        self.moteur_replique.addItem(_("Voix Gemini (joue vraiment la phrase ; votre clef, payant)"), "gemini")
        h1.addWidget(self.moteur_replique, 1)
        vr.addLayout(h1)
        h2 = QHBoxLayout()
        self.niveau_replique = QComboBox()
        self.niveau_replique.addItem(_("IA locale (sur ce poste)"), "locale")
        self.niveau_replique.addItem(_("IA cloud (votre clef)"), "cloud")
        self.niveau_replique.setCurrentIndex(1 if (self.ed.params.get("assistant_niveau") or "") == "cloud" else 0)
        h2.addWidget(self.niveau_replique)
        self.b_reecrire = QPushButton(_("Récrire la réplique à sa manière (IA)"))
        self.b_reecrire.setToolTip(_("L'IA garde le sens et change les tournures (gouaille, laconisme…) ; elle invente, ne cite aucune "
                                     "réplique de film. Rien n'est envoyé sans ce clic."))
        self.b_reecrire.clicked.connect(self._reecrire_replique)
        h2.addWidget(self.b_reecrire)
        self.b_ecouter_replique = QPushButton("▶ " + _("Écouter la réplique"))
        self.b_ecouter_replique.clicked.connect(self._ecouter_replique)
        h2.addWidget(self.b_ecouter_replique)
        h2.addStretch(1)
        vr.addLayout(h2)
        self.etat_replique = QLabel("")
        self.etat_replique.setWordWrap(True)
        self.etat_replique.setStyleSheet("color:#9aa4b2")
        vr.addWidget(self.etat_replique)
        self.boite_replique.hide()
        vd.addWidget(self.boite_replique)
        self.diction.currentIndexChanged.connect(self._maj_diction)
        self.prompt.textChanged.connect(self._maj_diction)

    def _style_replique(self):
        from . import diction as DI
        k = self.diction.currentData()
        if k and k != "auto":
            return k, ""
        e = self.effet() or {}
        return DI.style_depuis(self.prompt.toPlainText(), e.get("famille", "video"), self.ed.params)

    def _maj_diction(self, *_a):
        if not hasattr(self, "etat_replique"):
            return
        from . import diction as DI
        k, ref = self._style_replique()
        lib = DI.STYLES[k][0]
        self.etat_replique.setText(_("Phrasé : {s}", s=lib) + (_(" (d'après « {r} »)", r=ref) if ref else ""))

    def _reecrire_replique(self):
        from . import diction as DI
        texte = self.replique.toPlainText().strip()
        if not texte:
            self.etat_replique.setText(_("Écrivez d'abord la réplique."))
            return
        niveau = self.niveau_replique.currentData()
        if niveau == "cloud":
            from . import ia
            if not ia.confirmer_cout(self, self.ed.params, 400, 0, _("Réplique")):
                return
        k, ref = self._style_replique()
        params = self.ed.params
        self.b_reecrire.setEnabled(False)
        t = Tache(lambda tache: DI.reecrire(texte, k, params, niveau, ref), _("Réplique"))
        self._tache_replique = t
        self.suivi.demarrer(_("L'IA récrit la réplique"), t)

        def fin(r, err):
            try:
                self.suivi.finir()
                self.b_reecrire.setEnabled(True)
                if err:
                    self.etat_replique.setText(_("✕ Réplique non récrite : {e}", e=texte_erreur(err)[:300]))
                    return
                self.replique.setPlainText(r)
                self.etat_replique.setText(_("Réplique récrite : écoutez-la, modifiez-la si besoin."))
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _confirmer_voix(self):
        """Voix Gemini : prix affiché et confirmation avant l'envoi."""
        if self.moteur_replique.currentData() != "gemini":
            return True
        from . import ia
        return ia.confirmer_cout(self, self.ed.params, len(self.replique.toPlainText()) + 120, 0, _("Voix de la réplique (Gemini)"))

    def _ecouter_replique(self):
        from . import diction as DI
        texte = self.replique.toPlainText().strip()
        if not texte or not self._confirmer_voix():
            return
        k, _ref = self._style_replique()
        m, params = self.moteur_replique.currentData(), self.ed.params
        sortie = os.path.join(_dossier_sorties(), f"_replique_{int(time.time())}.wav")
        self.b_ecouter_replique.setEnabled(False)
        t = Tache(lambda tache: DI.dire(texte, sortie, params, k, m), _("Réplique"))
        self._tache_ecoute = t
        self.suivi.demarrer(_("La voix dit la réplique"), t)

        def fin(r, err):
            try:
                self.suivi.finir()
                self.b_ecouter_replique.setEnabled(True)
                if err:
                    self.etat_replique.setText(_("✕ Voix impossible : {e}", e=texte_erreur(err)[:300]))
                    return
                self._maj_diction()
                self.apercu_media.charger(r, video=False)
                self.apercu_media.show()
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _refaire_voix(self):
        """Garde le clip, refait seulement la voix (autre réplique, autre manière de parler, autre moteur)."""
        brut = getattr(self, "_clip_brut", None)
        if not brut or not os.path.exists(brut) or not self.replique.toPlainText().strip() or not self._confirmer_voix():
            return
        from . import diction as DI
        texte, (k, _r), m, params = self.replique.toPlainText().strip(), self._style_replique(), self.moteur_replique.currentData(), self.ed.params
        sortie = brut.replace("_brut.mp4", f"_voix{int(time.time()) % 10000}.mp4")
        e = self.effet()

        def travail(t):
            t.avancer(0.2, _("La voix dit la réplique…"))
            w = sortie[:-4] + ".wav"
            DI.dire(texte, w, params, k, m)
            t.avancer(0.7, _("Réplique mêlée au clip…"))
            DI.mixer(brut, w, sortie)
            return sortie
        self._recette = dict(getattr(self, "_recette", {}), replique=texte, diction=self.diction.currentData(), moteur_replique=m)
        self.tache = Tache(travail, _("Réplique"))
        self.tache.progression.connect(self._progression, Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, err, e=e: self._fini(e, r, err), Qt.QueuedConnection)
        self.b_creer.setEnabled(False)
        self._t0, self._fraction = time.monotonic(), 0.0
        self._fin_calcul, self._derniere_nouvelle, self._texte_etape = None, time.monotonic(), ""
        self.barre.setValue(0)
        self.barre.show()
        self._horloge.start()
        self.tache.start()

    # ---- styles « à la manière de »
    def _choisir_style(self):
        """Liste des styles connus (et de vos styles), avec leur description : un double-clic l'ajoute à la phrase (0.9.31)."""
        e = self.effet() or {}
        fam = e.get("famille", "image")
        nom = choisir_style(self, self.ed.params, fam)
        if nom:
            lien = _("chanté à la manière de") if fam == "musique" else _("à la manière de")
            p = self.prompt.toPlainText().rstrip(" ,")
            self.prompt.setPlainText((p + ", " if p else "") + f"{lien} {nom}")

    def _anglais_de(self, _texte):
        """L'anglais qui partira au moteur : la phrase traduite, plus la description du style « à la manière de »."""
        from . import traduction_recherche as TR
        tr = self._transposition()
        en, _c, manque = TR.phrase_en_anglais(tr["texte"]) if tr["texte"] else ("", "deja", [])
        if tr.get("ajout"):
            en = ", ".join(x for x in (en, tr["ajout"]) if x)
        return en, list(dict.fromkeys(manque))

    def _transposition(self):
        from . import styles_ia as S
        e = self.effet() or {}
        return S.transposer(self.prompt.toPlainText().strip(), e.get("famille", "image"), self.ed.params)

    def _maj_style(self):
        tr = self._transposition()
        lignes = [_("🎭 « {n} » → {d}", n=n, d=d) for n, d in tr["styles"]]
        if tr["inconnus"]:
            lignes.append(_("❓ Style inconnu : {n}. Le moteur ne connaît pas les noms : transposez-le avec l'IA, ou décrivez-le "
                            "(voix, orchestre, époque, image, attitude).", n=", ".join(tr["inconnus"])))
        if tr["styles"]:
            lignes.append(_("Le nom n'est pas envoyé au moteur : seule cette description l'est (un style n'est à personne ; la voix exacte, "
                            "le visage, les personnages et les logos, si)."))
        self.style_info.setText("\n".join(lignes))
        self.style_info.setStyleSheet("color:#9ad0ff")
        self.style_info.setVisible(bool(lignes) and self.prompt.isVisible())
        self.boite_style.setVisible(bool(tr["inconnus"]) and self.prompt.isVisible())

    def _transposer_ia(self):
        from . import styles_ia as S
        tr = self._transposition()
        if not tr["inconnus"]:
            return
        niveau = self.niveau_style.currentData()
        if niveau == "cloud":
            from . import ia
            if not ia.confirmer_cout(self, self.ed.params, 600, 0, _("Transposer un style")):
                return
        e = self.effet() or {}
        noms, fam, ctx, params = tr["inconnus"], e.get("famille", "image"), self.prompt.toPlainText(), self.ed.params
        self.b_style.setEnabled(False)
        t = Tache(lambda tache: S.transposer_ia(noms, fam, ctx, params, niveau), _("Style"))
        self._tache_style = t
        self.suivi.demarrer(_("L'IA décrit le style de {n}", n=", ".join(noms)), t)

        def fin(r, err):
            try:
                self.suivi.finir()
                self.b_style.setEnabled(True)
                if err or not r:
                    self.info.setText(_("✕ Style non transposé : {e}", e=str(err or _("réponse vide"))[:300]))
                    return
                S.retenir(params, r)
                self._maj_style()
                self.info.setText(_("Style transposé et gardé dans vos styles : relisez la description, puis « Créer »."))
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    # ---- création
    def _reafficher(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def reject(self):
        if self._en_calcul():
            self.hide()                     # le calcul continue ; la barre du bas le suit et la rouvre
            return
        super().reject()

    def closeEvent(self, ev):
        if self._en_calcul():
            ev.ignore()
            self.hide()
            return
        super().closeEvent(ev)

    def creer(self):
        e = self.effet()
        if not e:
            return
        if hasattr(self, "diagnostic"):
            self.diagnostic.hide()
        if hasattr(self, "apercu_media"):
            self.apercu_media.arreter()
            self.apercu_media.hide()
        ok, manque = EI.disponible(e, self.ed.params)
        if not ok:
            self.info.setText("⚠ " + manque)
            return
        prompt, force, params = self.prompt.toPlainText().strip(), self._valeur_force(e), self.ed.params
        tr = self._transposition() if prompt else {"texte": "", "ajout": "", "styles": []}
        horo = time.strftime("%Y%m%d_%H%M%S")
        projet = self.ed.projet
        m = e["moteur"]
        ph = {"en": prompt, "comment": "deja"}
        self._ph = ph
        if e["famille"] == "musique":
            sortie = os.path.join(_dossier_sorties(), f"musique_{horo}.mp3")
            duree, instr, paroles = self.duree.value(), self.instrumental.isChecked(), self.paroles.toPlainText()
            from . import paroles as PA
            voix_en = PA.VOIX.get(self.voix_chant.currentData(), ("", ""))[1]
            langue_ch = self.langue_chant.currentData()
            travail = lambda t: C.musique(ph["en"], sortie, duree, params, instr, paroles, langue=langue_ch, progression=t.avancer,
                                          arret=t.arret_demande, voix=voix_en)
        elif e["famille"] in ("image", "logo"):
            if not e.get("sans_source") and not self.source:
                self.info.setText(_("Placez la ligne rouge sur une image du film."))
                return
            sortie = os.path.join(_dossier_sorties(), f"{e['id']}_{horo}.png")
            init = None if e.get("sans_source") else self.source
            travail = lambda t: C.image(ph["en"], sortie, params, init=init, force=force, progression=t.avancer, arret=t.arret_demande)
        else:
            sortie = os.path.join(_dossier_sorties(), f"{e['id']}_{horo}.mp4")
            if m == "transition3d":
                r = self._raccord()
                if not r:
                    self.info.setText(_("Placez la ligne rouge près d'un raccord entre deux plans de la piste Vidéo 1."))
                    return
                img_a, img_b, coupe = r
                travail = lambda t: C.transition_3d(img_a, img_b, sortie, force, projet.cadence, params, t.avancer)
                self._pose_tr = coupe - force / 2
            elif m in ("photo3d", "video"):
                if not self.source:
                    self.info.setText(_("Placez la ligne rouge sur une image du film."))
                    return
                src = self.source
                if m == "photo3d":
                    import cv2
                    travail = lambda t: C.photo_3d(cv2.imread(src), sortie, 3.0, projet.cadence, amplitude=force, params=params, progression=t.avancer)
                else:
                    travail = lambda t: C.video(ph["en"], sortie, params, init=src, secondes=force, progression=t.avancer, arret=t.arret_demande)
            else:
                z = self._partie()
                c = projet.clip_a(z[0] + 0.01, "video") if z else None
                med = projet.media(c["media"]) if c else None
                if not med or med.get("genre") != "video":
                    self.info.setText(_("Choisissez une partie en jaune (ou placez la ligne rouge) sur un plan vidéo."))
                    return
                v = float(c.get("vitesse", 1.0) or 1.0)
                debut = float(c["src_debut"]) + (z[0] - c["debut"]) * v
                duree = (min(z[1], fin_clip(c)) - z[0]) * v
                chemin, ips = med["chemin"], projet.cadence
                if m == "anime":
                    cle = None
                    travail = lambda t: C.traiter_video(chemin, sortie, lambda img: C.anime_image(img, cle, params), debut, duree, ips,
                                                        progression=t.avancer, arret=t.arret_demande)
                elif m == "profondeur":
                    travail = lambda t: C.traiter_video(chemin, sortie, lambda img: C.flou_arriere_plan(img, force, params), debut, duree, ips,
                                                        progression=t.avancer, arret=t.arret_demande)
                elif m == "upscale":
                    travail = lambda t: C.agrandir(chemin, sortie, int(force), debut, duree, ips, params, t.avancer, t.arret_demande)[0]
                else:
                    travail = lambda t: C.ralentir(chemin, sortie, int(force), debut, duree, ips, params, t.avancer, t.arret_demande)
                self._pose = z[0]
        if m == "transition3d":
            self._pose = self._pose_tr
        else:
            self._pose = getattr(self, "_pose", None) if e["famille"] == "video" and m not in ("photo3d", "video") else self.ed.timeline.position
        a_traduire = bool(prompt) and (e["famille"] in ("musique", "image", "logo") or m == "video")
        base = travail

        en_main = self.prompt_en.texte() if (a_traduire and self.prompt_en.retouche()) else ""

        def travail(t, base=base):
            if a_traduire and en_main:           # traduction corrigée à la main : c'est elle qui part
                ph.update(en=en_main, comment="main")
                t.avancer(0.0, _("Phrase envoyée au moteur, en anglais : « {t} »", t=en_main[:160]))
            elif a_traduire:                     # les moteurs ne comprennent bien que l'anglais
                t.avancer(0.0, _("Traduction de la phrase en anglais…"))
                en, comment, manque = TR.phrase_en_anglais(tr["texte"]) if tr["texte"] else ("", "deja", [])
                if manque and comment != "service":
                    raise C.ErreurCreatif(_("Pas de traduction pour « {m} » (pas de réseau ?) : écrivez ces mots en anglais dans la phrase.",
                                            m=", ".join(dict.fromkeys(manque))))
                if tr["ajout"]:                  # « à la manière de … » : la description du style, jamais le nom
                    en = ", ".join(x for x in (en, tr["ajout"]) if x)
                    comment = "style" if comment == "deja" else comment
                ph.update(en=en, comment=comment)
                if comment != "deja":
                    t.avancer(0.0, _("Phrase envoyée au moteur, en anglais : « {t} »", t=en[:160]))
            return base(t)
        texte_rep = self.replique.toPlainText().strip() if e["famille"] == "video" else ""
        self._clip_brut = None
        if texte_rep:
            if not self._confirmer_voix():
                return
            from . import diction as DI
            k_rep, _ref = self._style_replique()
            m_rep = self.moteur_replique.currentData()
            sortie_finale = sortie
            brut = sortie[:-4] + "_brut.mp4"
            self._clip_brut = brut
            base2 = travail

            def travail(t, base2=base2):
                r = base2(t)
                chemin = r if isinstance(r, str) else (r[0] if isinstance(r, (tuple, list)) else r)
                os.replace(chemin, brut)
                t.avancer(0.95, _("La voix dit la réplique ({s})…", s=DI.STYLES[k_rep][0]))
                w = sortie_finale[:-4] + ".wav"
                DI.dire(texte_rep, w, params, k_rep, m_rep)
                t.avancer(0.98, _("Réplique mêlée au clip…"))
                return DI.mixer(brut, w, sortie_finale)
        self._recette = {"famille": e["famille"], "effet": e["id"], "prompt": prompt, "force": force, "sans_source": bool(e.get("sans_source"))}
        if texte_rep:
            self._recette.update(replique=texte_rep, diction=self.diction.currentData(), moteur_replique=m_rep)
        if e["famille"] == "musique":
            self._recette.update(duree=self.duree.value(), instrumental=self.instrumental.isChecked(), paroles=self.paroles.toPlainText(),
                                 voix=self.voix_chant.currentData(), langue=self.langue_chant.currentData())
        self.envoye.hide()
        self.info.setStyleSheet("")
        self.tache = Tache(travail, _("Atelier IA"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("IA locale : {n}", n=e["nom"]), pendant=(_("Afficher l'Atelier"), self._reafficher),
                             action=(_("Voir le résultat"), self._reafficher))
        self.tache.progression.connect(self._progression, Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, err, e=e: self._fini(e, r, err), Qt.QueuedConnection)
        self.b_creer.setEnabled(False)
        self.b_arreter.show()
        self.info.setText(_("Création en cours sur ce poste… vous pouvez continuer à travailler ; la barre du bas suit aussi l'avancement."))
        self._t0, self._fraction = time.monotonic(), 0.0
        self.etape.setText(_("Préparation…"))
        self.etape.show()
        self.barre.setValue(0)
        self.barre.show()
        self._fin_calcul, self._derniere_nouvelle, self._texte_etape = None, time.monotonic(), ""
        self._tic()
        self._horloge.start()
        self.tache.start()

    def _progression(self, f, texte):
        self._fraction = f
        self._derniere_nouvelle = time.monotonic()
        if f >= 0.995 and not getattr(self, "_fin_calcul", None):
            self._fin_calcul = time.monotonic()
        if texte:
            self._texte_etape = texte
            self.etape.setText(texte)
        ph = getattr(self, "_ph", None)
        if ph and ph.get("comment") not in (None, "deja"):
            self.envoye.setText(_("Envoyé au moteur, en anglais : « {t} »", t=ph["en"]))
            self.envoye.show()
        self._tic()

    def _tic(self):
        """Toutes les secondes : temps écoulé, temps restant estimé, et ce qui se passe quand le moteur se tait (0.9.31)."""
        mm = lambda s_: f"{int(s_) // 60}:{int(s_) % 60:02d}"
        maintenant = time.monotonic()
        ecoule = maintenant - self._t0
        f = self._fraction
        en_cours = self.tache is not None and self.tache.isRunning()
        fin_calcul = getattr(self, "_fin_calcul", None)
        if en_cours and fin_calcul:
            # le calcul est fini (100 %) mais le moteur travaille encore : décodage du son, écriture du fichier
            self.barre.setRange(0, 0)                         # barre animée : ça bouge, ça ne plante pas
            self.barre.setFormat("")
            fam = (self.effet() or {}).get("famille") if hasattr(self, "effet") else None
            if fam == "musique":
                self.etape.setText(_("Finition : le moteur transforme le calcul en son et écrit le fichier (souvent 1 à 3 minutes pour un "
                                     "long morceau). Toujours en cours : {t} depuis la fin du calcul, {e} en tout.", t=mm(maintenant - fin_calcul),
                                     e=mm(ecoule)))
            else:
                self.etape.setText(_("Finition : le moteur assemble les images et écrit le fichier. Toujours en cours : {t} depuis la fin "
                                     "du calcul, {e} en tout.", t=mm(maintenant - fin_calcul), e=mm(ecoule)))
            return
        self.barre.setRange(0, 1000)
        self.barre.setValue(int(f * 1000))
        reste = ""
        if en_cours and 0.03 < f < 0.995 and ecoule > 8:
            reste = " · " + _("reste environ {t}", t=mm(ecoule * (1 - f) / f))
        self.barre.setFormat(_("{p} % · temps écoulé {t}", p=int(f * 100), t=mm(ecoule)) + reste)
        silence = maintenant - getattr(self, "_derniere_nouvelle", self._t0)
        if en_cours and silence > 45:
            self.etape.setText((getattr(self, "_texte_etape", "") or "") + "  —  " +
                               _("toujours en cours : le moteur ne donne pas de nouvelles depuis {t}, c'est normal pendant cette étape.",
                                 t=mm(silence)))

    def arreter(self):
        if self.tache is not None:
            self.tache.stopper()

    def _vider_actions(self):
        while self.actions.count():
            it = self.actions.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def _action(self, texte, fonction):
        b = QPushButton(texte)
        b.clicked.connect(fonction)
        aides = {
            _("Garder dans les médias (sans poser)"): _("Le fichier rejoint les médias du projet (à gauche), sans être posé dans le "
                                                        "film : vous le glisserez plus tard où vous voulez."),
            _("Poser sous la vidéo (piste Musique)"): _("Posé au début du film, sur la piste Musique."),
            _("Poser à la ligne rouge"): _("Posé à l'endroit de la ligne rouge."),
            _("Ranger dans ma bibliothèque"): _("Gardé dans « Ma bibliothèque » (Montage › Tampons vidéo) pour tous vos projets."),
            _("Enregistrer sous…"): _("Une copie du fichier où vous voulez sur le disque (dossier Musique, Images ou Vidéos)."),
            _("Recréer (une autre version)"): _("Mêmes réglages, nouvelle version (l'IA ne refait jamais exactement la même)."),
        }
        if texte in aides:
            b.setToolTip(aides[texte])
        self.actions.addWidget(b)

    def _fini(self, e, r, err):
        self.b_creer.setEnabled(True)
        self.b_arreter.hide()
        self._horloge.stop()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        self.etape.hide()
        self._vider_actions()
        if err:
            if isinstance(err, InterruptedError) or getattr(self.tache, "arret", False):
                self.info.setText(_("Création arrêtée."))
                return
            self.info.setStyleSheet("color:#ff8a80")
            moteur_err = getattr(err, "genre", None)
            if moteur_err or getattr(err, "code", None):           # un moteur a échoué : la cause en clair et les solutions
                self.info.setText(_("✕ La création n'a pas abouti. Voici pourquoi, et ce que vous pouvez faire :"))
                genre = (moteur_err or "").replace("_gpu", "") or {"logo": "image"}.get(e["famille"], e["famille"])
                self.diagnostic.montrer(str(err), genre, getattr(err, "journal", None), moteur_err)
            else:
                from .taches import texte_erreur
                self.info.setText(_("✕ La création n'a pas abouti : {e}", e=texte_erreur(err)[:700]))
            self._action(_("Réessayer"), self.creer)
            return
        self.info.setStyleSheet("")
        self.resultat = r if isinstance(r, str) else (r[0] if isinstance(r, (tuple, list)) else r)
        if isinstance(self.resultat, str) and os.path.exists(self.resultat):          # pour pouvoir la reprendre et la modifier
            from . import creations
            rec = dict(getattr(self, "_recette", {}), anglais=self._ph.get("en", ""))
            src = getattr(self, "source", None)
            if rec.get("famille") in ("image", "logo") and src and os.path.exists(src) and self.resultat.lower().endswith(".png"):
                import shutil                     # l'image de départ voyage avec la recette : la création se refait ailleurs
                try:
                    shutil.copy2(src, self.resultat + ".source.png")
                    rec["source_image"] = os.path.basename(self.resultat + ".source.png")
                except OSError:
                    pass
            creations.ecrire(self.resultat, rec)
        if e["famille"] in ("image", "logo"):
            px = QPixmap(self.resultat)
            self.img_resultat.setPixmap(px.scaled(360, 203, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.info.setText(_("Image créée. Choisissez ce que vous en faites :"))
            self._action(_("Poser au-dessus du film (3 s)"), lambda: self.ed.poser_au_dessus(self.resultat, self._pose or 0.0, e["nom"], 3.0))
            self._action(_("Insérer dans le film (3 s, décale la suite)"), lambda: self.ed.inserer_image(self.resultat, self._pose, 3.0, e["nom"]))
            self._action(_("Ajouter aux médias"), lambda: self.ed.importer([self.resultat]))
            self._action(_("Logo dans la Fabrique…"), lambda: self.ed.window().fabrique(image=self.resultat))
            self._action(_("Enregistrer en JPG (miniature)…"), self._enregistrer_jpg)
            self._action(_("Enregistrer sous…"), self._enregistrer_sous)
        elif e["famille"] == "musique":
            # rien n'est posé tant que l'utilisateur n'a pas écouté et choisi
            self.info.setText(_("Musique créée. Écoutez-la, gardez le morceau voulu, puis choisissez :"))
            self.apercu_media.charger(self.resultat, video=False)
            self._action(_("Poser sous la vidéo (piste Musique)"), self._poser_musique)
            self._action(_("Poser à la ligne rouge"), lambda: self._poser_musique(self.ed.timeline.position))
            self._action(_("Garder dans les médias (sans poser)"), lambda: (self.ed.importer([self.resultat]),
                                                                           self.info.setText(_("Ajoutée aux médias du projet (à gauche), sans être posée."))))
            if getattr(self, "_remplace", None):
                self._action(_("Remplacer le morceau d'origine"), self._remplacer)
            self._action(_("Ranger dans ma bibliothèque"), self._ranger)
            self._action(_("Enregistrer sous…"), self._enregistrer_sous)
            self._action(_("Recréer (une autre version)"), self.creer)
        else:
            png = moteur.image(self.resultat, 0.5, 360)
            px = QPixmap()
            px.loadFromData(png)
            self.img_resultat.setPixmap(px.scaled(360, 203, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.info.setText(_("Clip créé. Regardez-le, gardez le morceau voulu, puis choisissez :"))
            self.apercu_media.charger(self.resultat, video=True)
            self._action(_("Poser au-dessus du film"), self._poser_clip)
            self._action(_("Garder dans les médias (sans poser)"), lambda: (self.ed.importer([self.resultat]),
                                                                           self.info.setText(_("Ajouté aux médias du projet (à gauche), sans être posé."))))
            if getattr(self, "_clip_brut", None) and os.path.exists(self._clip_brut):
                self._action(_("Refaire seulement la voix"), self._refaire_voix)
            if getattr(self, "_remplace", None):
                self._action(_("Remplacer le plan d'origine"), self._remplacer)
            self._action(_("Ranger dans ma bibliothèque"), self._ranger)
            self._action(_("Enregistrer sous…"), self._enregistrer_sous)
            self._action(_("Recréer"), self.creer)

    def reprendre(self, recette, clip_id=None):
        """Rouvre une création : même effet, même phrase, mêmes paroles, même durée ; « Remplacer » remettra le résultat
        à la place du plan d'origine."""
        self._remplace = clip_id
        fam = recette.get("famille")
        i = self.famille.findData(fam) if hasattr(self, "famille") else -1
        if i >= 0:
            self.famille.setCurrentIndex(i)
        for k in range(self.liste.count()):
            if (self.liste.item(k).data(Qt.UserRole) or {}).get("id") == recette.get("effet"):
                self.liste.setCurrentRow(k)
                break
        self.prompt.setPlainText(recette.get("prompt") or recette.get("anglais") or "")
        if fam == "musique":
            self.duree.setValue(float(recette.get("duree") or self.duree.value()))
            self.instrumental.setChecked(bool(recette.get("instrumental", True)))
            self.paroles.setPlainText(recette.get("paroles") or "")
            self.voix_chant.setCurrentIndex(max(0, self.voix_chant.findData(recette.get("voix") or "auto")))
            self.langue_chant.setCurrentIndex(max(0, self.langue_chant.findData(recette.get("langue") or "fr")))
        if recette.get("replique"):
            self.replique.setPlainText(recette["replique"])
            self.diction.setCurrentIndex(max(0, self.diction.findData(recette.get("diction") or "auto")))
            self.moteur_replique.setCurrentIndex(max(0, self.moteur_replique.findData(recette.get("moteur_replique") or "local")))
        self.info.setText(_("Création reprise : modifiez la phrase, les paroles ou la durée, puis « Créer ». Le résultat pourra "
                            "remplacer l'original."))

    def _remplacer(self):
        r = self.apercu_media.reglages()
        self.apercu_media.arreter()
        if self.ed.remplacer_media_clip(self._remplace, self.resultat, r):
            self.info.setText(_("✓ Remplacé dans le film (Annuler pour revenir à l'ancienne version)."))

    def _enregistrer_sous(self):
        c = enregistrer_copie(self, self.resultat, self.ed.params)
        if c:
            self.info.setText(_("✓ Copie enregistrée : {f}", f=c))

    def _ranger(self):
        """La création rejoint la bibliothèque (celle des tampons : sons et clips, rangée, synchronisée), avec sa phrase."""
        from . import tampons as T
        e = self.effet() or {}
        r = self.apercu_media.reglages()
        params, f = self.ed.params, self.resultat
        nom = f"{e.get('nom', _('Création IA'))} — {time.strftime('%d/%m %H:%M')}"
        mots = [_("IA"), e.get("nom", ""), e.get("famille", "")]
        debut, duree = r["src_debut"], r["src_fin"] - r["src_debut"]
        t = Tache(lambda tache: T.ajouter_fichier(params, f, nom, [m for m in mots if m], debut=debut, duree=duree), _("Bibliothèque"))
        self._tache_ranger = t
        t.fini.connect(lambda res, err: self.info.setText(("✕ " + texte_erreur(err)) if err else
                                                          _("✓ Rangé dans votre bibliothèque (Montage › Tampons vidéo › Ma bibliothèque) : « {n} ».",
                                                            n=nom)), Qt.QueuedConnection)
        t.start()

    def _essayer_voix(self):
        """15 s chantées avec la voix et la langue choisies, sur les deux premiers vers (ou un « la la la »), pour écouter."""
        from . import creatif as C, paroles as PA
        e = self.effet() or {}
        params = self.ed.params
        voix_en = PA.VOIX.get(self.voix_chant.currentData(), ("", ""))[1]
        langue = self.langue_chant.currentData()
        vers = [l for l in self.paroles.toPlainText().splitlines() if l.strip() and not l.strip().startswith("[")][:2]
        paroles = "[verse]\n" + ("\n".join(vers) if vers else PA.ESSAIS.get(langue, PA.ESSAIS["en"]))
        style = e.get("prompt") or "pop song"
        sortie = os.path.join(_dossier_sorties(), f"_essai_voix_{int(time.time())}.mp3")
        self.b_essai_voix.setEnabled(False)
        t = Tache(lambda tache: C.musique(style, sortie, 15.0, params, False, paroles, langue=langue, progression=tache.avancer,
                                          arret=tache.arret_demande, voix=voix_en), _("Essai de voix"))
        self._tache_essai = t
        self.suivi.demarrer(_("Essai de la voix « {v} »", v=self.voix_chant.currentText()), t,
                            _("15 secondes de chant : une à quelques minutes sur ce poste."))

        def fin(r, err):
            try:
                self.suivi.finir()
                self.b_essai_voix.setEnabled(True)
                if err:
                    self.info.setText(_("✕ Essai impossible : {e}", e=texte_erreur(err)[:300]))
                    return
                self.apercu_media.charger(r if isinstance(r, str) else sortie, video=False)
                self.apercu_media.show()
                self.info.setText(_("Écoutez l'essai ; changez de voix et réessayez, ou « Créer » le vrai morceau."))
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _ecrire_paroles(self):
        from . import paroles as PA
        theme = self.prompt.toPlainText().strip()
        debut = self.paroles.toPlainText()
        niveau = self.niveau_paroles.currentData()
        if niveau == "cloud":
            from . import ia
            if not ia.confirmer_cout(self, self.ed.params, 1500, 0, _("Paroles de chanson")):
                return
        args = (theme, debut, self.langue_chant.currentData(), self.voix_chant.currentData(), self.duree.value(), self.ed.params, niveau)
        self.b_paroles.setEnabled(False)
        self.info.setText("")
        t = Tache(lambda tache: PA.ecrire(*args), _("Paroles"))
        self._tache_paroles = t
        self.suivi.demarrer(_("L'IA écrit les paroles"), t, _("IA locale : le modèle démarre d'abord (une à plusieurs minutes la première "
                                                              "fois), puis écrit.") if niveau == "locale" else _("IA cloud : quelques secondes."))

        def fin(r, err):
            try:
                self.suivi.finir()
                self.b_paroles.setEnabled(True)
                if err:
                    self.info.setText(_("✕ Paroles non écrites : {e}", e=texte_erreur(err)[:300]))
                    return
                self.paroles.setPlainText(r)
                self.info.setText(_("Paroles écrites : relisez-les, modifiez-les si besoin, puis « Créer »."))
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _poser_musique(self, debut=0.0):
        r = self.apercu_media.reglages()
        self.apercu_media.arreter()
        reg = dict(r, volume=0.8, _couper_fin=True)
        self.ed._piste_depot = ("audio", float(debut or 0.0), reg)
        self.ed.importer([self.resultat])
        self.info.setText(_("Morceau posé ({d:.1f} s) sur la piste Musique : réglez-le ensuite dans l'Inspecteur.",
                            d=r["src_fin"] - r["src_debut"]))

    def _poser_clip(self):
        r = self.apercu_media.reglages()
        self.apercu_media.arreter()
        ci = self.ed.poser_au_dessus(self.resultat, self._pose or 0.0, self.effet()["nom"] if self.effet() else "",
                                     r["src_fin"] - r["src_debut"])
        if ci is not None:
            ci["src_debut"], ci["src_fin"] = r["src_debut"], r["src_fin"]
            self.ed.rafraichir()
        self.info.setText(_("Clip posé au-dessus, sur une piste vidéo du dessus : supprimez-le pour revenir à l'original."))

    def _ouvrir(self, chemin):
        import pathlib, webbrowser
        webbrowser.open(pathlib.Path(chemin).resolve().as_uri())

    def _enregistrer_jpg(self):
        from .session import dossier_systeme
        p, _f = QFileDialog.getSaveFileName(self, _("Miniature"), os.path.join(self.ed.params.get("dossier_images") or dossier_systeme("images"),
                                                                                 "miniature.jpg"), "JPEG (*.jpg)")
        if p:
            moteur.lancer(["-y", "-i", self.resultat, "-q:v", "2", p if p.lower().endswith(".jpg") else p + ".jpg"])
            self.info.setText(_("Miniature enregistrée."))

    def done(self, r):
        if hasattr(self, "apercu_media"):
            self.apercu_media.arreter()
        if self.tache is not None and self.tache.isRunning():
            self.info.setText(_("La création continue en tâche de fond ; le résultat arrivera dans le projet."))
        super().done(r)


def _tc(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


class ApercuCreation(QWidget):
    """Ecouter ou regarder ce que l'IA vient de créer, et garder seulement le morceau voulu, AVANT de le poser :
    lecture / pause, curseur, « Début ici » et « Fin ici », fondus. Le fichier créé n'est jamais modifié : le plan posé
    commence et finit où l'on a dit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QSlider, QDoubleSpinBox
        self.chemin, self.duree, self.lecteur, self.video = None, 0.0, None, None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.titre = QLabel("")
        self.titre.setStyleSheet("font-weight:600")
        v.addWidget(self.titre)
        self.zone_video = QWidget()
        self.zone_video.setFixedHeight(240)
        self.zone_video.setStyleSheet("background:#000;border-radius:6px")
        QVBoxLayout(self.zone_video).setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.zone_video)
        self.curseur = QSlider(Qt.Horizontal)
        self.curseur.setRange(0, 1000)
        self.curseur.sliderMoved.connect(lambda x: self.lecteur and self.lecteur.setPosition(x * 100))
        v.addWidget(self.curseur)
        h = QHBoxLayout()
        self.b_lire = QPushButton("▶ " + _("Écouter"))
        self.b_lire.clicked.connect(self.basculer)
        h.addWidget(self.b_lire)
        self.temps = QLabel("0:00")
        h.addWidget(self.temps)
        h.addStretch(1)
        b = QPushButton("[ " + _("Début ici"))
        b.setToolTip(_("Le morceau gardé commence à l'endroit écouté"))
        b.clicked.connect(lambda: self.debut.setValue(self.position()))
        h.addWidget(b)
        b = QPushButton(_("Fin ici") + " ]")
        b.setToolTip(_("Le morceau gardé s'arrête à l'endroit écouté"))
        b.clicked.connect(lambda: self.fin.setValue(self.position()))
        h.addWidget(b)
        v.addLayout(h)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel(_("Garder de")))
        self.debut = QDoubleSpinBox()
        self.debut.setSuffix(" s")
        self.debut.setDecimals(1)
        h2.addWidget(self.debut)
        h2.addWidget(QLabel(_("à")))
        self.fin = QDoubleSpinBox()
        self.fin.setSuffix(" s")
        self.fin.setDecimals(1)
        h2.addWidget(self.fin)
        self.fondu_e = QCheckBox(_("Fondu au début"))
        self.fondu_e.setChecked(True)
        h2.addWidget(self.fondu_e)
        self.fondu_s = QCheckBox(_("Fondu à la fin"))
        self.fondu_s.setChecked(True)
        h2.addWidget(self.fondu_s)
        h2.addStretch(1)
        v.addLayout(h2)
        self.resume = QLabel("")
        self.resume.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.resume)
        for w in (self.debut, self.fin):
            w.valueChanged.connect(self._maj)
        self._tic = QTimer(self)
        self._tic.setInterval(100)
        self._tic.timeout.connect(self._boucle)
        self.hide()

    def charger(self, chemin, video=False):
        self.chemin = chemin
        self.duree = float((moteur.sonder(chemin) or {}).get("duree") or 0) or 1.0
        for w, val in ((self.debut, 0.0), (self.fin, self.duree)):
            w.blockSignals(True)
            w.setRange(0.0, self.duree)
            w.setValue(val)
            w.blockSignals(False)
        self.titre.setText(_("Écoutez, gardez le morceau voulu, puis posez-le :") if not video else
                           _("Regardez, gardez le morceau voulu, puis posez-le :"))
        self.zone_video.setVisible(video)
        self.b_lire.setText("▶ " + (_("Regarder") if video else _("Écouter")))
        self.fondu_e.setVisible(not video)
        self.fondu_s.setVisible(not video)
        self._maj()
        self.show()
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":       # tests automatiques : pas de lecture réelle
            return
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            return
        if self.lecteur is None:
            self.lecteur = QMediaPlayer(self)
            self.sortie = QAudioOutput(self)
            self.lecteur.setAudioOutput(self.sortie)
            self.lecteur.positionChanged.connect(self._position)
        if video and self.video is None:
            from PySide6.QtMultimediaWidgets import QVideoWidget
            self.video = QVideoWidget()
            self.zone_video.layout().addWidget(self.video)
        self.lecteur.setVideoOutput(self.video if video else None)
        self.lecteur.setSource(QUrl.fromLocalFile(chemin))

    def position(self):
        return round((self.lecteur.position() / 1000.0) if self.lecteur is not None else self.curseur.value() * self.duree / 1000.0, 1)

    def _position(self, ms):
        if not self.curseur.isSliderDown():
            self.curseur.setRange(0, int(self.duree * 10))
            self.curseur.setValue(int(ms / 100))
        s_ = ms / 1000.0
        self.temps.setText(f"{int(s_ // 60)}:{int(s_ % 60):02d}")

    def basculer(self):
        if self.lecteur is None:
            return
        from PySide6.QtMultimedia import QMediaPlayer
        if self.lecteur.playbackState() == QMediaPlayer.PlayingState:
            self.lecteur.pause()
            self._tic.stop()
            self.b_lire.setText("▶ " + _("Reprendre"))
        else:
            if not (self.debut.value() <= self.position() < self.fin.value()):
                self.lecteur.setPosition(int(self.debut.value() * 1000))
            self.lecteur.play()
            self._tic.start()
            self.b_lire.setText("❚❚ " + _("Pause"))

    def _boucle(self):
        if self.lecteur is not None and self.position() >= self.fin.value():     # on n'entend que le morceau gardé
            self.lecteur.pause()
            self._tic.stop()
            self.lecteur.setPosition(int(self.debut.value() * 1000))
            self.b_lire.setText("▶ " + _("Réécouter le morceau"))

    def _maj(self):
        if self.fin.value() <= self.debut.value() + 0.5:
            self.fin.blockSignals(True)
            self.fin.setValue(min(self.duree, self.debut.value() + 0.5))
            self.fin.blockSignals(False)
        d = self.fin.value() - self.debut.value()
        self.resume.setText(_("Morceau gardé : {d:.1f} s sur {t:.1f} s.", d=d, t=self.duree))

    def reglages(self):
        """Réglages du plan à poser : début et fin dans le fichier, fondus."""
        r = {"src_debut": round(self.debut.value(), 2), "src_fin": round(self.fin.value(), 2)}
        if self.fondu_e.isVisible() or not self.zone_video.isVisible():
            d = self.fin.value() - self.debut.value()
            r["fondu_entree"] = min(1.5, d / 4) if self.fondu_e.isChecked() else 0.0
            r["fondu_sortie"] = min(3.0, d / 3) if self.fondu_s.isChecked() else 0.0
        return r

    def arreter(self):
        if self.lecteur is not None:
            self.lecteur.stop()
        self._tic.stop()


def enregistrer_copie(parent, chemin, params=None):
    """Copie d'un fichier (créé par l'IA ou non) là où l'on veut : dossier Musique, Images ou Vidéos du système la première
    fois, puis le dernier dossier choisi pour ce genre de copie. La recette IA (paroles, phrase…) suit la copie."""
    from .widgets import dossier_depart, retenir_dossier
    from . import creations
    if not chemin or not os.path.exists(chemin):
        return None
    ext = os.path.splitext(chemin)[1].lower()
    genre = "musique" if ext in (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac") else \
        "images" if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp") else "videos"
    cle = "copie_" + genre
    p = params if params is not None else None
    depart = (p or {}).get("dossier_" + cle) if p is not None else ""
    if not depart or not os.path.isdir(depart):
        from .session import dossier_systeme
        depart = dossier_systeme(genre)
    cible, _f = QFileDialog.getSaveFileName(parent, _("Enregistrer une copie"), os.path.join(depart, os.path.basename(chemin)),
                                            f"*{ext}")
    if not cible:
        return None
    if not cible.lower().endswith(ext):
        cible += ext
    if os.path.abspath(cible) != os.path.abspath(chemin):
        creations.copier(chemin, cible)
    retenir_dossier(parent, cle, cible, params)
    return cible


def choisir_style(parent, params, fam="video", bouton=None):
    """Fenêtre des styles « à la manière de » (chanteurs, groupes, compositeurs, acteurs, films…) avec ce que reçoit le
    moteur ; renvoie le nom choisi. fam="voix" : seulement les références qui décrivent une manière de chanter (0.9.63)."""
    from PySide6.QtWidgets import QDialog, QLineEdit, QTreeWidget, QTreeWidgetItem
    from . import styles_ia as S
    d = QDialog(parent)
    d.setWindowTitle(_("Voix « à la manière de »") if fam == "voix" else _("Style « à la manière de »"))
    d.resize(780, 580)
    v = QVBoxLayout(d)
    t = QLabel((_("Double-cliquez sur un nom : « chanté à la manière de … » est ajouté à votre phrase. Le moteur ne reçoit jamais le nom "
                  "ni la voix de la personne, seulement la description de sa manière de chanter (à droite).") if fam == "voix" else
                _("Double-cliquez sur un nom : « à la manière de … » est ajouté à votre phrase. Le moteur ne reçoit jamais le nom, "
                  "seulement la description du style (à droite).")) + " " +
               _("La liste s'enrichit en ligne, sans nouvelle version. Un nom absent marche aussi : tapez-le, puis « Utiliser » ; "
                 "l'IA le transposera sur votre clic."))
    t.setWordWrap(True)
    v.addWidget(t)
    hc = QHBoxLayout()
    genre = QComboBox()
    genre.addItem(_("Toutes les familles"), "")
    asp_fam = "musique" if fam == "voix" else fam
    refs = S._toutes(params)
    lignes, vus = [], set()
    for cle, (nom, asp) in refs.items():
        if nom in vus:
            continue
        vus.add(nom)
        desc = asp.get("voix", "") if fam == "voix" and "perso" not in asp else S._description(asp, asp_fam)
        if not desc:
            continue
        lignes.append((nom.title() if nom.islower() else nom, desc, S.genre(nom) if "perso" not in asp else "perso", S.mots_cles(nom)))
    presents = {g for _n, _d, g, _m in lignes}
    for k, lib in sorted(S.GENRES.items(), key=lambda kv: S._net(kv[1])):
        if k in presents:
            genre.addItem(lib, k)
    if "perso" in presents:
        genre.addItem(_("Mes styles"), "perso")
    hc.addWidget(genre)
    cherche = QLineEdit()
    cherche.setPlaceholderText(_("Chercher : metal, Einaudi, western, piano, années 80…"))
    hc.addWidget(cherche, 1)
    v.addLayout(hc)
    arbre = QTreeWidget()
    arbre.setHeaderLabels([_("Nom"), _("Ce que reçoit le moteur")])
    arbre.setColumnWidth(0, 210)
    arbre.setWordWrap(True)
    for nom, desc, g, mots in sorted(lignes, key=lambda x: S._net(x[0])):
        it = QTreeWidgetItem([nom, desc])
        it.setToolTip(1, desc)
        it.setData(0, Qt.UserRole, g)
        it.setData(1, Qt.UserRole, mots)
        arbre.addTopLevelItem(it)
    v.addWidget(arbre, 1)
    vide = QLabel("")
    vide.setWordWrap(True)
    vide.setStyleSheet("color:#c98a00")
    vide.hide()
    v.addWidget(vide)
    compte = QLabel("")
    compte.setStyleSheet("color:#9aa4b2")
    v.addWidget(compte)

    def filtrer(*_a):
        txt, g = cherche.text().strip(), genre.currentData()
        n = 0
        for i in range(arbre.topLevelItemCount()):
            it = arbre.topLevelItem(i)
            ok = (not g or it.data(0, Qt.UserRole) == g) and (not txt or S.correspond(txt, it.text(0) + " " + it.text(1) + " " +
                                                                                          (it.data(1, Qt.UserRole) or "")))
            it.setHidden(not ok)
            n += ok
        compte.setText(_("{n} référence(s).", n=n))
        vide.setVisible(n == 0 and bool(txt))
        b_nom.setVisible(bool(txt))
        b_nom.setText(_("Utiliser « {t} »", t=txt[:40]))
        if n == 0 and txt:
            vide.setText(_("« {t} » n'est pas dans la liste. « Utiliser » l'ajoute quand même à votre phrase : l'IA décrira ce style "
                           "sur votre clic (« Améliorer avec l'IA »), sans jamais envoyer le nom au moteur.", t=txt))
    choix = []

    def prendre(it, _c=0):
        choix.append(it.text(0))
        d.accept()
    arbre.itemDoubleClicked.connect(prendre)
    h = QHBoxLayout()
    b_nom = QPushButton("")
    b_nom.clicked.connect(lambda: (choix.append(cherche.text().strip()), d.accept()))
    b_nom.hide()
    h.addWidget(b_nom)
    h.addStretch(1)
    b_ok = QPushButton(bouton or _("Ajouter à la phrase"))
    b_ok.clicked.connect(lambda: arbre.currentItem() and not arbre.currentItem().isHidden() and prendre(arbre.currentItem()))
    h.addWidget(b_ok)
    b_f = QPushButton(_("Fermer"))
    b_f.clicked.connect(d.reject)
    h.addWidget(b_f)
    v.addLayout(h)
    cherche.textChanged.connect(filtrer)
    genre.currentIndexChanged.connect(filtrer)
    filtrer()
    d._cherche, d._arbre, d._genre, d._b_nom = cherche, arbre, genre, b_nom       # tests
    if getattr(parent, "_test_style", None):
        parent._test_style(d)
        return choix[0] if choix else None
    d.exec()
    return choix[0] if choix else None
