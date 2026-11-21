"""1.1.0 : fenêtre « Animation libre » : vous décrivez, l'IA construit la composition HyperFrames, vous regardez l'aperçu,
vous demandez des changements, puis PhilCut la fabrique en qualité et la pose dans le film."""
import copy
import os
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
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
        self.setWindowTitle(_("Animation libre : décrivez-la, l'IA la construit"))
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
        self.description.setFixedHeight(120)
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
        self.transparent = QCheckBox(_("Fond transparent : posée au-dessus du film"))
        f.addRow("", self.transparent)
        gauche.addLayout(f)
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
        self.b_erreurs.clicked.connect(lambda: self.corriger(erreur="\n".join(self._erreurs)))
        self.b_erreurs.hide()
        gauche.addWidget(self.b_erreurs)
        hv = QHBoxLayout()
        self.b_avant = QPushButton(_("‹ Version d'avant"))
        self.b_avant.clicked.connect(self.version_avant)
        self.b_projet = QPushButton(_("Ouvrir le projet HyperFrames"))
        self.b_projet.setToolTip(_("Le dossier de la composition (index.html) : HyperFrames Studio ou Claude Code peuvent la retoucher"))
        self.b_projet.clicked.connect(self.ouvrir_projet)
        hv.addWidget(self.b_avant)
        hv.addWidget(self.b_projet)
        hv.addStretch(1)
        gauche.addLayout(hv)
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
        w_g.setFixedWidth(470)
        h.addWidget(w_g)
        droite = QVBoxLayout()
        self.message = QLabel(_("L'aperçu apparaîtra ici (rendu léger sur ce poste, gratuit)."))
        self.message.setWordWrap(True)
        droite.addWidget(self.message)
        self.apercu = ApercuCreation(self)
        droite.addWidget(self.apercu)
        droite.addStretch(1)
        self.b_installer = QPushButton(_("Installer HyperFrames sur ce poste (environ 200 Mo, une fois)…"))
        self.b_installer.clicked.connect(self.installer)
        droite.addWidget(self.b_installer)
        hf = QHBoxLayout()
        self.moteur = QComboBox()
        self.moteur.addItem(_("HyperFrames sur ce poste (gratuit)"), "hyperframes_local")
        self.moteur.addItem(_("HyperFrames chez HeyGen (payant)"), "hyperframes_cloud")
        hf.addWidget(self.moteur, 1)
        self.b_fabriquer = QPushButton(_("Fabriquer en qualité et poser…"))
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hf.addWidget(self.b_fabriquer)
        droite.addLayout(hf)
        b_fermer = QPushButton(_("Fermer"))
        b_fermer.clicked.connect(self.close)
        droite.addWidget(b_fermer, 0, Qt.AlignRight)
        h.addLayout(droite, 1)
        self._erreurs = []
        self.anim = anim or None
        if anim:
            self.description.setPlainText(anim.get("description", ""))
        self.resize(1000, 700)
        self._maj()

    # ------------------------------------------------------------------ état
    def _maj(self):
        from . import motion_html as MH
        occupe = bool(self.tache and self.tache.isRunning())
        a_code = bool(self.anim and (self.anim.get("libre") or {}).get("js"))
        self.b_creer.setEnabled(not occupe)
        self.b_corriger.setEnabled(a_code and not occupe)
        self.b_erreurs.setEnabled(a_code and not occupe)
        self.b_avant.setEnabled(a_code and bool((self.anim.get("libre") or {}).get("historique")) and not occupe)
        self.b_projet.setEnabled(a_code)
        self.b_fabriquer.setEnabled(a_code and not occupe and not self._erreurs)
        self.b_installer.setVisible(not MH.local_pret())

    def lire(self):
        a = copy.deepcopy(self.anim) if self.anim else ML.fiche(self.description.toPlainText())
        a["description"] = self.description.toPlainText().strip()
        a["taille"] = list(self.format.currentData())
        a["charte"] = self.charte.currentData()
        a["transparent"] = self.transparent.isChecked()
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
        lib = a.get("libre") or {}
        fautes = ML.verifier_code(lib.get("js", ""), lib.get("html", ""))
        if fautes:
            return a, "", [_("Règle non respectée : {f}", f=x) for x in fautes]
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
        return a, r, []

    def _fin_ia(self, r, e):
        if e:
            self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:400]))
            return
        a, apercu, erreurs = r
        self.anim = a
        self._erreurs = erreurs
        if a.get("duree") and not a.get("duree_imposee"):
            self.duree.blockSignals(True)
            self.duree.setValue(0)
            self.duree.blockSignals(False)
        lib = a.get("libre") or {}
        self.message.setText(_("« {t} », {d} s — {m}", t=a.get("titre", ""), d=f"{a.get('duree', 0):g}", m=lib.get("message", "")))
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
            self.etat.setText(_("Composition écrite. Pour la voir ici, installez HyperFrames sur ce poste ; ou fabriquez-la chez "
                                "HeyGen."))
        self.credit.montrer("anthropic")

    def creer(self):
        if not self.description.toPlainText().strip():
            self.etat.setText(_("Décrivez d'abord l'animation, en quelques phrases."))
            return
        if not self._accord(_("L'IA va écrire l'animation"), ML.PRIX_CREER):
            return
        a = self.lire()
        a.pop("libre", None)
        a = ML.fiche(a["description"], a["taille"], a.get("duree") if a.get("duree_imposee") else 0, a["charte"], a["transparent"]) \
            | ({"duree_imposee": True} if a.get("duree_imposee") else {})

        def travail(t):
            t.avancer(0.05, _("L'IA écrit l'animation (une à deux minutes)…"))
            b = ML.creer(self.params, a)
            return self._verifier_et_apercu(t, b)
        self._lancer(travail, _("Animation libre : écriture"), self._fin_ia)

    def corriger(self, erreur=""):
        remarque = self.remarque.text().strip() if not erreur else ""
        if not erreur and not remarque:
            self.etat.setText(_("Ecrivez d'abord ce qu'il faut changer."))
            return
        if not self._accord(_("L'IA va reprendre l'animation"), ML.PRIX_CORRIGER):
            return
        a = self.lire()

        def travail(t):
            t.avancer(0.05, _("L'IA reprend l'animation…"))
            b = ML.corriger(self.params, a, remarque, erreur)
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
        from . import packs_ia

        def travail(t):
            if not packs_ia.moteur_installe("motion"):
                packs_ia.installer("motion_html", t.avancer, t.arret_demande)
            return True
        self._lancer(travail, _("Installation de HyperFrames"),
                     lambda r, e: self.etat.setText("✕ " + texte_erreur(e) if e else _("✓ HyperFrames est installé.")))

    def ouvrir_projet(self):
        from . import motion_html as MH
        d = os.path.join(M.dossier(), "projets", time.strftime("%Y%m%d_%H%M%S") + "_libre")
        MH.preparer_projet(self.lire(), d, gsap_en_ligne=not MH.gsap_local())
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

    def done(self, r):
        from .widgets import calcul_en_cours, garder_calcul
        if garder_calcul(self, calcul_en_cours(self)):
            return
        self.apercu.arreter() if hasattr(self.apercu, "arreter") else None
        super().done(r)
