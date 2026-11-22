"""Fenêtre « Demander à l'aide » (1.1.12) : une discussion avec une IA qui connaît PhilCut (voir aide_ia).

Non bloquante, à côté du film ; « Réduire » toujours là. Chaque réponse peut montrer les menus (« Montrez-moi »), ouvrir
l'outil (« Le faire pour moi ») ou passer une phrase à « Dites-le en clair ». Rien ne part sans un clic sur « Envoyer ».
"""
import html

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QTextBrowser,
                               QVBoxLayout, QWidget)

from . import aide_ia as AI
from .langue import _
from .taches import Tache, texte_erreur

EXEMPLE = _("Comment rallonger un plan à partir d'une photo ?")


class DialogueAideIA(QDialog):
    def __init__(self, fenetre, question=""):
        super().__init__(fenetre)
        self.fenetre = fenetre
        self.params = fenetre.params
        self.setWindowTitle(_("Demander à l'aide"))
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.resize(620, 680)
        self.historique = []                # [(question, réponse en texte)]
        self.derniere = None
        self.tache = None
        self._test_envoi = None             # essais : fonction (consignes, texte, images, niveau) -> réponse
        v = QVBoxLayout(self)
        intro = QLabel(_("Posez votre question comme à un formateur : l'aide lit les menus de PhilCut, ses guides et ce qui est à "
                         "l'écran, puis vous montre où cliquer. Rien n'est envoyé avant « Envoyer »."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.fil = QTextBrowser()
        self.fil.setOpenLinks(False)
        v.addWidget(self.fil, 1)
        self.zone_actions = QWidget()
        from .widgets import FluxLayout
        self.flux = FluxLayout(self.zone_actions, marge=0, espace=4)
        v.addWidget(self.zone_actions)
        self.question = QPlainTextEdit(question)
        self.question.setPlaceholderText(EXEMPLE)
        self.question.setMaximumHeight(84)
        v.addWidget(self.question)
        h = QHBoxLayout()
        self.capture = QCheckBox(_("Joindre ce que je vois (capture de PhilCut)"))
        self.capture.setToolTip(_("Une image de la fenêtre de PhilCut (et de la fenêtre de travail ouverte) part avec la question : "
                                  "l'aide voit où vous en êtes"))
        self.capture.setChecked(bool(self.params.get("aide_ia_capture", True)))
        self.capture.toggled.connect(lambda on: (self.params.__setitem__("aide_ia_capture", on), self._maj_prix()))
        h.addWidget(self.capture, 1)
        self.b_envoyer = QPushButton(_("Envoyer"))
        self.b_envoyer.setStyleSheet("font-weight:600")
        self.b_envoyer.setToolTip(_("Ctrl + Entrée"))
        self.b_envoyer.clicked.connect(self.envoyer)
        h.addWidget(self.b_envoyer)
        v.addLayout(h)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.envoyer)
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Répondre avec")))
        from . import assistant_creation as A
        self.niveau = QComboBox()
        for k, lib in A.niveaux(self.params):
            self.niveau.addItem(lib, k)
        self.niveau.setCurrentIndex(max(0, self.niveau.findData(self.params.get("aide_ia_niveau") or "")))
        self.niveau.currentIndexChanged.connect(lambda _i: (self.params.__setitem__("aide_ia_niveau", self.niveau.currentData()),
                                                            self._maj_prix()))
        h.addWidget(self.niveau, 1)
        self.l_prix = QLabel("")
        h.addWidget(self.l_prix)
        v.addLayout(h)
        from .credit_ia import LignesCredit
        self.credits = LignesCredit(self.params, ["anthropic", "google"], self)
        v.addWidget(self.credits)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        self.credits.surveiller(self.etat)
        h = QHBoxLayout()
        b = QPushButton(_("Nouvelle discussion"))
        b.clicked.connect(self.nouvelle)
        h.addWidget(b)
        b = QPushButton(_("Guides pas à pas…"))
        b.setToolTip(_("Les cas concrets déjà écrits, sans IA"))
        b.clicked.connect(lambda: self.fenetre.guides())
        h.addWidget(b)
        h.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        h.addWidget(b)
        v.addLayout(h)
        self._accueil()
        self._maj_prix()

    # ------------------------------------------------------------------ affichage
    def _accueil(self):
        self.fil.setHtml("<p style='color:#888'>" + html.escape(_("Exemples : « {a} », « {b} », « {c} »",
                         a=EXEMPLE, b=_("Comment garder les mêmes musiciens dans tous mes clips ?"),
                         c=_("Où changer le moteur vidéo de l'assistant ?"))) + "</p>")

    def _ed(self):
        return self.fenetre.editeur_courant()

    def _maj_prix(self):
        niveau = self.niveau.currentData()
        if niveau == "locale":
            self.l_prix.setText(_("gratuit"))
            return
        c = AI.prix_question(self.params, niveau, 60000 if not self.historique else 9000, 1 if self.capture.isChecked() else 0)
        self.l_prix.setText(_("environ {p} $ la question", p=f"{max(c, 0.01):.2f}".replace(".", ",")))
        self.l_prix.setToolTip(_("Indicatif : le manuel de PhilCut part avec la première question ; les suivantes coûtent moins "
                                 "(il est gardé en cache par le service). Facturé sur votre clef."))

    def nouvelle(self):
        if self.tache is not None and self.tache.isRunning():
            return
        self.historique = []
        self.derniere = None
        self._actions(None)
        self._accueil()
        self.etat.setText("")
        self._maj_prix()

    def _ajouter(self, qui, texte, couleur):
        if not self.historique and self.derniere is None and qui == _("Vous"):
            self.fil.clear()
        self.fil.append(f"<p><b style='color:{couleur}'>{html.escape(qui)}</b><br>{texte}</p>")
        self.fil.verticalScrollBar().setValue(self.fil.verticalScrollBar().maximum())

    @staticmethod
    def texte_reponse(r):
        """La réponse en HTML : texte, étapes numérotées (chemins en gras), ce qui manque."""
        out = [html.escape(r["reponse"]).replace("\n", "<br>")] if r["reponse"] else []
        if r["etapes"]:
            out.append("<ol>" + "".join(f"<li>{html.escape(e['texte'])}" + (" 👁" if e["montrer"] else "") + "</li>"
                                         for e in r["etapes"]) + "</ol>")
        if r["manque"]:
            out.append("<i>" + html.escape(_("Pas encore dans PhilCut : {m}", m=r["manque"])) + "</i>")
        return "".join(out)

    @staticmethod
    def texte_brut(r):
        lignes = [r["reponse"]] + [f"{k}. {e['texte']}" for k, e in enumerate(r["etapes"], 1)]
        if r["manque"]:
            lignes.append("Manque : " + r["manque"])
        return "\n".join(x for x in lignes if x)

    def _actions(self, r):
        while self.flux.count():
            it = self.flux.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not r:
            return
        for k, e in enumerate(r["etapes"], 1):
            if e["montrer"]:
                b = QPushButton(_("Montrez-moi l'étape {n}", n=k))
                b.setToolTip(" › ".join(e["montrer"].get("menu") or [_("Clic droit sur le plan")] + e["montrer"]["clic_droit"]))
                b.clicked.connect(lambda _c=False, m=e["montrer"]: self._montrer(m))
                self.flux.addWidget(b)
        if r["faire"]:
            m = r["faire"]
            b = QPushButton("▶ " + _("Le faire pour moi"))
            b.setStyleSheet("font-weight:600")
            b.setToolTip(_("Ouvre : {c}", c=" › ".join(m.get("menu") or [_("Clic droit sur le plan")] + m.get("clic_droit", []))))
            b.clicked.connect(lambda _c=False: self._faire(m))
            self.flux.addWidget(b)
        if r["dites_le"] and self._ed() is not None:
            b = QPushButton(_("Dites-le en clair : « {p} »", p=r["dites_le"][:60]))
            b.setToolTip(_("PhilCut montre les actions ; rien n'est fait avant « Faire »"))
            b.clicked.connect(lambda _c=False, p=r["dites_le"]: self._ed().dites_le(p))
            self.flux.addWidget(b)

    def _montrer(self, m):
        if not AI.montrer(self.fenetre, self._ed(), m):
            self.etat.setText(_("Je n'ai pas pu ouvrir ce menu ici (ouvrez d'abord un projet avec un plan, puis réessayez)."))

    def _faire(self, m):
        if AI.faire(self.fenetre, self._ed(), m):
            self.etat.setText(_("✓ Ouvert : suivez les étapes, l'aide reste à côté."))
        else:
            self.etat.setText(_("Je n'ai pas pu le faire ici : utilisez « Montrez-moi »."))

    # ------------------------------------------------------------------ envoi
    def envoyer(self):
        q = self.question.toPlainText().strip()
        if not q or (self.tache is not None and self.tache.isRunning()):
            return
        niveau = self.niveau.currentData() or "claude"
        ed = self._ed()
        try:
            consignes, texte = AI.preparer(self.fenetre, ed, self.params, q, self.historique, niveau)
            images = AI.capture(self.fenetre) if self.capture.isChecked() else []
        except Exception as err:                      # lire les menus ne doit jamais empêcher de poser la question
            self.etat.setText("✕ " + texte_erreur(err))
            return
        self._ajouter(_("Vous"), html.escape(q).replace("\n", "<br>"), "#2a7de1")
        self.question.clear()
        self.b_envoyer.setEnabled(False)
        self.etat.setText(_("L'aide lit le manuel de PhilCut et prépare sa réponse…"))
        envoi = self._test_envoi or (lambda c, t, i, n: AI.envoyer(self.params, c, t, i, n))
        self.tache = Tache(lambda _t: envoi(consignes, texte, images, niveau), _("Aide"))
        self.tache.lier(self)
        self.tache.progression.connect(lambda f, t: self.etat.setText(t) if t else None)
        self.tache.fini.connect(lambda r, e, q_=q: self._fin(q_, r, e))
        self.tache.start()

    def _fin(self, q, r, err):
        self.b_envoyer.setEnabled(True)
        if err is not None:
            self.etat.setText("✕ " + texte_erreur(err))
            self.credits.signaler(texte_erreur(err))
            self.question.setPlainText(q)
            return
        r = AI.lire_reponse(r) if not (isinstance(r, dict) and "etapes" in r and "faire" in r) else r
        retires = AI.verifier(r, self.fenetre, self._ed())
        self.derniere = r
        self.historique.append((q, self.texte_brut(r)))
        self._ajouter(_("Aide"), self.texte_reponse(r), "#1a9e5a")
        self._actions(r)
        self.etat.setText(_("{n} chemin(s) cité(s) par l'IA introuvable(s) dans les menus : pas de bouton pour eux.", n=retires)
                          if retires else "")
        self._maj_prix()

    def en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def a_garder(self):
        return bool(self.historique)

    def closeEvent(self, ev):
        from .widgets import garder_calcul
        if garder_calcul(self, self.en_calcul()):
            ev.ignore()
            return
        super().closeEvent(ev)


def ouvrir(fenetre, question=""):
    """Une seule fenêtre d'aide ; une question passée est écrite (pas envoyée : rien ne part sans clic)."""
    from .widgets import non_bloquante
    d = non_bloquante(fenetre, "aide_ia", lambda: DialogueAideIA(fenetre, question))
    if question and not d.question.toPlainText().strip():
        d.question.setPlainText(question)
    return d
