"""Fenêtre « Plan de liaison » (0.9.56) : non bloquante. En haut, la dernière image du plan A et la première du plan B ;
puis les propositions de passage (règles gratuites tout de suite, ou analyse par une IA qui regarde les deux images) ;
la consigne reste modifiable ; on choisit comment fabriquer (coût affiché avant), on regarde le résultat, puis on le pose
entre les deux plans (un seul Annuler)."""
import os, tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
                               QProgressBar, QPushButton, QRadioButton, QScrollArea, QSpinBox, QTextEdit, QVBoxLayout, QWidget)

from . import liaison as L
from .langue import _
from .taches import Tache, texte_erreur

MODES = ("3d", "locale", "omni")


def libelle_mode(mode, duree=5, params=None):
    if mode == "3d":
        return _("Transition 3D (gratuite)")
    if mode == "locale":
        return _("IA vidéo de ce poste (gratuite)")
    return _("Gemini Omni (au plus {p} $)", p=f"{L.prix_omni(duree, params):.2f}".replace(".", ","))


def explication_mode(mode):
    if mode == "3d":
        return _("Calculée sur ce poste, immédiate. Elle dure 1 à 4 s et ne suit pas la consigne : la caméra plonge dans "
                 "l'image A puis ressort de l'image B.")
    if mode == "locale":
        return _("Calculée sur ce poste, rien n'est envoyé, mais lente sans carte graphique. L'IA part de l'image A et suit la "
                 "consigne, puis rejoint l'image B par un fondu (elle ne sait pas viser une image d'arrivée).")
    return _("Votre clef Google, prix affiché et demandé avant. Le plan part exactement de l'image A et arrive exactement sur "
             "l'image B, en suivant la consigne (3 à 10 s).")


class DialogueLiaison(QDialog):
    def __init__(self, ed, a, b):
        super().__init__(ed)
        self.ed, self.a, self.b = ed, a, b
        self.setModal(False)
        self.setWindowTitle(_("Plan de liaison"))
        self.setMinimumWidth(620)
        self.tache, self.images, self.mesures, self.resultat = None, None, None, None
        self.dossier = tempfile.mkdtemp(prefix="philcut-liaison-")
        racine = QVBoxLayout(self)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zone.setFrameShape(QFrame.NoFrame)
        racine.addWidget(zone, 1)
        corps = QWidget()
        zone.setWidget(corps)
        v = QVBoxLayout(corps)
        intro = QLabel(_("Un plan qui part de la <b>dernière image de « {a} »</b> et arrive à la <b>première image de « {b} »</b> : "
                         "on passe d'un lieu à l'autre sans coupe sèche. Choisissez une proposition (ou écrivez la vôtre), "
                         "fabriquez, regardez, puis posez.", a=a.get("nom", ""), b=b.get("nom", "")))
        intro.setWordWrap(True)
        v.addWidget(intro)
        # les deux images
        hi = QHBoxLayout()
        self.vue_a, self.vue_b = QLabel(_("Image A…")), QLabel(_("Image B…"))
        for w in (self.vue_a, self.vue_b):
            w.setFixedSize(240, 135)
            w.setAlignment(Qt.AlignCenter)
            w.setStyleSheet("background:#000;border-radius:6px;color:#9aa4b2")
        hi.addStretch(1)
        hi.addWidget(self.vue_a)
        fl = QLabel("→")
        fl.setStyleSheet("font-size:22px")
        hi.addWidget(fl)
        hi.addWidget(self.vue_b)
        hi.addStretch(1)
        v.addLayout(hi)
        self.lab_mesures = QLabel("")
        self.lab_mesures.setWordWrap(True)
        self.lab_mesures.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.lab_mesures)
        # propositions
        v.addWidget(QLabel(_("<b>Propositions</b>")))
        hp = QHBoxLayout()
        self.b_ia_locale = QPushButton(_("Analyser avec l'IA de ce poste"))
        self.b_ia_locale.setToolTip(_("L'IA de vision de ce poste regarde les deux images et propose trois passages ; gratuit, "
                                      "rien n'est envoyé"))
        self.b_ia_locale.clicked.connect(lambda: self.analyser(True))
        hp.addWidget(self.b_ia_locale)
        self.b_ia_cloud = QPushButton(_("Analyser avec l'IA cloud…"))
        self.b_ia_cloud.setToolTip(_("Claude ou Gemini (votre clef) regarde les deux images ; coût affiché avant l'envoi"))
        self.b_ia_cloud.clicked.connect(lambda: self.analyser(False))
        hp.addWidget(self.b_ia_cloud)
        hp.addStretch(1)
        v.addLayout(hp)
        self.lab_descr = QLabel("")
        self.lab_descr.setWordWrap(True)
        self.lab_descr.setStyleSheet("color:#9aa4b2")
        self.lab_descr.hide()
        v.addWidget(self.lab_descr)
        self.boite_props = QVBoxLayout()
        v.addLayout(self.boite_props)
        self.groupe = QButtonGroup(self)
        self.props = []
        v.addWidget(QLabel(_("Consigne pour le générateur vidéo (en anglais, modifiable) :")))
        self.consigne = QTextEdit()
        self.consigne.setAcceptRichText(False)
        self.consigne.setFixedHeight(76)
        v.addWidget(self.consigne)
        hd = QHBoxLayout()
        hd.addWidget(QLabel(_("Durée")))
        self.duree = QSpinBox()
        self.duree.setRange(3, 10)
        self.duree.setValue(5)
        self.duree.setSuffix(" s")
        self.duree.valueChanged.connect(self._maj_modes)
        hd.addWidget(self.duree)
        hd.addSpacing(12)
        hd.addStretch(1)
        v.addLayout(hd)
        hm = QHBoxLayout()
        hm.addWidget(QLabel(_("Fabriquer avec")))
        self.mode = QComboBox()
        self.mode.currentIndexChanged.connect(self._maj_mode)
        hm.addWidget(self.mode)
        hm.addStretch(1)
        v.addLayout(hm)
        self.expl_mode = QLabel("")
        self.expl_mode.setWordWrap(True)
        self.expl_mode.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.expl_mode)
        self._maj_modes()
        self.manque = QLabel("")
        self.manque.setWordWrap(True)
        self.manque.setStyleSheet("color:#e3b341")
        v.addWidget(self.manque)
        self.accord = QCheckBox(_("Les personnes visibles sur ces deux images sont d'accord pour être animées par l'IA "
                                  "(je m'y engage)."))
        self.accord.setToolTip(_("Obligatoire pour l'IA : on n'anime que des personnes qui ont donné leur accord"))
        self.accord.toggled.connect(self._maj_mode)
        v.addWidget(self.accord)
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
        v.addWidget(self.apercu)
        v.addStretch(1)
        hb = QHBoxLayout()
        hb.addStretch(1)
        self.b_fabriquer = QPushButton(_("Fabriquer le plan"))
        self.b_fabriquer.setStyleSheet("font-weight:600")
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hb.addWidget(self.b_fabriquer)
        self.b_poser = QPushButton(_("Poser entre les deux plans"))
        self.b_poser.setEnabled(False)
        self.b_poser.clicked.connect(self.poser)
        hb.addWidget(self.b_poser)
        self.b_fermer = QPushButton(_("Fermer"))
        self.b_fermer.clicked.connect(self.close)
        hb.addWidget(self.b_fermer)
        racine.addLayout(hb)
        self.resize(680, 700)
        self.preparer()

    # ------------------------------------------------------------------ état
    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _occupe(self, oui):
        for b in (self.b_fabriquer, self.b_ia_locale, self.b_ia_cloud):
            b.setEnabled(not oui and self.images is not None)
        self.barre.setVisible(oui)
        if oui:
            self.barre.setValue(0)
        if not oui:
            self._maj_mode()

    def _maj_modes(self, *_a):
        i = max(0, self.mode.currentIndex())
        self.mode.blockSignals(True)
        self.mode.clear()
        for m in MODES:
            self.mode.addItem(libelle_mode(m, self.duree.value(), self.ed.params), m)
        self.mode.setCurrentIndex(i)
        self.mode.blockSignals(False)
        self._maj_mode()

    def _maj_mode(self, *_a):
        if not hasattr(self, "accord"):
            return
        m = self.mode.currentData()
        manque = L.manque(m, self.ed.params)
        ia = m in ("locale", "omni")
        self.accord.setVisible(ia)
        self.duree.setEnabled(m != "3d")
        self.expl_mode.setText(explication_mode(m))
        self.manque.setText(manque or "")
        self.manque.setVisible(bool(self.manque.text()))
        pret = self.images is not None and not self._en_calcul()
        self.b_fabriquer.setEnabled(pret and not manque and (not ia or self.accord.isChecked()))

    # ------------------------------------------------------------------ images et mesures
    def preparer(self):
        p, a, b, d = self.ed.projet, self.a, self.b, self.dossier
        self._occupe(True)
        self.etat.setText(_("Lecture des deux images du raccord et mesure du mouvement…"))

        def travail(t):
            t.avancer(0.1, _("Images du raccord"))
            imgs = L.images_raccord(p, a, b, d)
            t.avancer(0.5, _("Mouvement de la caméra"))
            return imgs, L.mesurer(p, a, b, *imgs)
        self._lancer(travail, _("Plan de liaison : images du raccord"), self._prepare)

    def _prepare(self, r, err):
        self._occupe(False)
        if err or not r:
            self.etat.setText(_("✕ Images du raccord illisibles : {e}", e=texte_erreur(err)))
            return
        self.images, self.mesures = r
        for w, ch in zip((self.vue_a, self.vue_b), self.images):
            w.setPixmap(QPixmap(ch).scaled(w.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        mes = self.mesures
        mvt = {"right": _("vers la droite"), "left": _("vers la gauche"), "up": _("vers le haut"), "down": _("vers le bas"), "": _("immobile")}
        self.lab_mesures.setText(_("Lumière {la} % → {lb} % ; couleurs proches à {c} % ; caméra à la fin de A : {ma} ; au début de B : {mb}.",
                                   la=round(mes["lumiere_a"] / 2.55), lb=round(mes["lumiere_b"] / 2.55), c=int(mes["couleurs"] * 100),
                                   ma=mvt.get(mes["mouvement_a"], ""), mb=mvt.get(mes["mouvement_b"], "")))
        self.montrer_propositions(L.propositions_regles(mes))
        self.etat.setText(_("Propositions calculées sur ce poste. Pour des idées qui tiennent compte de ce que montrent les images, "
                            "« Analyser avec l'IA »."))
        self._occupe(False)

    # ------------------------------------------------------------------ propositions
    def montrer_propositions(self, props, descr=None):
        for rb, cadre, _p in self.props:
            self.groupe.removeButton(rb)
            cadre.deleteLater()
        self.props = []
        if descr:
            self.lab_descr.setText(_("A : {a}\nB : {b}", a=descr.get("a", ""), b=descr.get("b", "")))
        self.lab_descr.setVisible(bool(descr))
        for p in props:
            cadre = QFrame()
            cadre.setObjectName("prop")
            cadre.setStyleSheet("QFrame#prop{border:1px solid #3a3f4b;border-radius:6px}")
            vc = QVBoxLayout(cadre)
            rb = QRadioButton(f"{p['titre']} — {p['duree']} s")
            rb.setStyleSheet("font-weight:600")
            vc.addWidget(rb)
            lb = QLabel(p["idee"])
            lb.setWordWrap(True)
            vc.addWidget(lb)
            self.groupe.addButton(rb)
            rb.toggled.connect(lambda oui, p_=p: oui and self._choisir(p_))
            self.boite_props.addWidget(cadre)
            self.props.append((rb, cadre, p))
        if self.props:
            self.props[0][0].setChecked(True)

    def _choisir(self, p):
        self.consigne.setPlainText(p["consigne"])
        self.duree.setValue(int(p["duree"]))

    def analyser(self, locale):
        if self._en_calcul() or not self.images:
            return
        params = self.ed.params
        if not locale:
            from . import ia
            if not ia.confirmer_cout(self, params, 1500, 2, _("Analyse des deux images du raccord pour proposer un plan de liaison.")):
                return
        imgs, mes = self.images, self.mesures
        self._occupe(True)
        self.etat.setText(_("L'IA regarde les deux images…"))
        self._lancer(lambda t: L.analyser_ia(*imgs, mes, params, locale=locale), _("Plan de liaison : analyse"), self._analyse)

    def _analyse(self, r, err):
        self._occupe(False)
        if err or not r:
            self.etat.setText(_("✕ L'analyse n'a pas abouti : {e}", e=texte_erreur(err)))
            return
        self.montrer_propositions(r["propositions"], r)
        self.etat.setText(_("✓ {n} propositions de l'IA. Choisissez, modifiez la consigne si besoin, puis « Fabriquer le plan ».",
                            n=len(r["propositions"])))

    # ------------------------------------------------------------------ fabrication
    def fabriquer(self):
        if self._en_calcul() or not self.images:
            return
        mode, duree, params = self.mode.currentData(), self.duree.value(), self.ed.params
        consigne = self.consigne.toPlainText().strip()
        if mode != "3d" and not consigne:
            self.etat.setText(_("Ecrivez la consigne (ou choisissez une proposition)."))
            return
        if mode != "3d" and not self.accord.isChecked():
            return
        if mode == "omni":
            prix = f"{L.prix_omni(duree, params):.2f}".replace(".", ",")
            if QMessageBox.question(self, _("Gemini Omni (payant)"),
                                    _("Les deux images et la consigne partent chez Google, qui fabrique le plan.\n"
                                      "Coût : au plus {p} $, facturé sur votre clef (la console Google fait foi).\n\nFabriquer ?", p=prix),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        sortie = os.path.join(L.dossier_sorties(), f"liaison_{os.getpid()}_{id(self) % 10000}_{mode}_{len(os.listdir(L.dossier_sorties()))}.mp4")
        imgs, fmt = self.images, self._format()
        self._occupe(True)
        self.apercu.hide()
        self.b_poser.setEnabled(False)
        self.etat.setText(_("Fabrication du plan de liaison…"))
        self._lancer(lambda t: L.fabriquer(mode, *imgs, consigne, sortie, duree, params, fmt,
                                           progression=lambda f, txt="": t.avancer(f, txt), arret=lambda: t.arret),
                     _("Plan de liaison"), self._fabrique)

    def _format(self):
        return "9:16" if getattr(self.ed.projet, "format", "16:9") in ("9:16", "4:5") else "16:9"

    def _fabrique(self, r, err):
        self._occupe(False)
        if err or not r or not os.path.exists(r):
            self.etat.setText(_("✕ Le plan de liaison n'a pas été fabriqué : {e}", e=texte_erreur(err)))
            return
        self.resultat = r
        self.apercu.charger(r, video=True)
        self.b_poser.setEnabled(True)
        self.etat.setText(_("✓ Plan fabriqué. Regardez-le, gardez le morceau voulu, puis « Poser entre les deux plans ». "
                            "Pas convaincu ? Changez de proposition ou de consigne et refabriquez."))

    def poser(self):
        if not self.resultat:
            return
        from . import moteur
        rg = self.apercu.reglages()
        c = L.poser(self.ed.projet, self.a, self.b, self.resultat, moteur.sonder(self.resultat),
                    src=(rg.get("src_debut", 0.0), rg.get("src_fin", 1e9)))
        self.ed.rafraichir()
        self.apercu.arreter()
        self.b_poser.setEnabled(False)
        self.etat.setText(_("✓ Plan de liaison posé entre les deux plans ({d:.1f} s). Edition › Annuler pour revenir.",
                            d=c["src_fin"] - c["src_debut"]))

    # ------------------------------------------------------------------ outils
    def _lancer(self, fonction, titre, fin):
        self.tache = Tache(fonction, titre)
        self.tache.lier(self)
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(fin, Qt.QueuedConnection)
        self.tache.start()

    def closeEvent(self, ev):
        self.apercu.arreter()
        if self._en_calcul():
            self.tache.stopper()
        super().closeEvent(ev)
