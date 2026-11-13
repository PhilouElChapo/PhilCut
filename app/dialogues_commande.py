"""Fenêtre « Dites-le en clair » : la phrase, ce que PhilCut a compris (cochable), puis « Faire » (annulable)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from . import commande_ia as C
from .langue import _
from .taches import Tache
from .widgets import boutons_fr
from .taches import texte_erreur

EXEMPLES = [_("mets une musique calme et coupe-la à la fin de la vidéo"), _("titre « Notre week-end » au début"),
            _("effet vintage sur tous les plans"), _("ralenti sur le plan 2"), _("une flèche rouge courbe à 5 s"),
            _("fondu de la musique 2 s et 4 s"), _("baisse la musique")]

# 0.9.48 : actions d'un clic (la phrase, en français car les règles sans IA la lisent ainsi, est écrite pour vous, le plan montré, rien n'est fait avant « Faire ») ; ordre alphabétique
RAPIDES = sorted([
    (_("Étalonnage auto de toute la séquence"), "étalonnage auto sur toute la séquence"),
    (_("Mêmes couleurs partout (comme le plan 1)"), "mêmes couleurs partout comme le plan 1"),
    (_("Toute la séquence un peu plus chaude"), "toute la séquence un peu plus chaude"),
    (_("Effet vintage sur toute la séquence"), "effet vintage sur tous les plans"),
    (_("Ranger les rushes par date"), "range les rushes par date"),
    (_("Ranger les rushes par type"), "range les rushes par type"),
    (_("Un marqueur à chaque plan"), "un marqueur à chaque plan"),
    (_("Trier les rushes (doublons, flou, tremblé, son)"), "trie les rushes"),
    (_("Marqueurs sur les temps forts de la musique"), "marqueurs sur les temps forts de la musique"),
], key=lambda x: __import__("unicodedata").normalize("NFD", x[0]).encode("ascii", "ignore").decode().lower())


class DialogueCommande(QDialog):
    def __init__(self, ed, phrase=""):
        super().__init__(ed)
        self.ed = ed
        self.setWindowTitle(_("Dites-le en clair"))
        self.resize(640, 520)
        self.actions = []
        self.tache = None
        v = QVBoxLayout(self)
        aide = QLabel(_("Ecrivez ce que vous voulez, comme à quelqu'un : PhilCut le traduit en actions de montage, vous les montre, "
                        "et ne fait rien avant votre clic sur « Faire ». Tout se défait d'un coup (Edition › Annuler)."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.phrase = QLineEdit(phrase)
        self.phrase.setPlaceholderText(EXEMPLES[0])
        self.phrase.returnPressed.connect(self.comprendre)
        v.addWidget(self.phrase)
        ex = QLabel(_("<small>Exemples : {e}</small>", e=" · ".join(f"« {x} »" for x in EXEMPLES[1:])))
        ex.setWordWrap(True)
        v.addWidget(ex)
        from .widgets import FluxLayout
        zr = QWidget()
        fr = FluxLayout(zr, marge=0, espace=4)
        for lib, phrase_r in RAPIDES:
            b = QPushButton(lib)
            b.setToolTip(_("Écrit « {p} » et montre ce que PhilCut va faire", p=phrase_r))
            b.clicked.connect(lambda _c=False, p_=phrase_r: (self.phrase.setText(p_), self.comprendre()))
            fr.addWidget(b)
        v.addWidget(zr)
        self.rapides = zr
        bg = QPushButton(_("Comment faire… (guides pas à pas)"))         # 0.9.52
        bg.setToolTip(_("Des cas concrets expliqués étape par étape ; PhilCut ouvre lui-même les bons menus"))
        bg.clicked.connect(lambda: self._guides())
        hg = QHBoxLayout()                                   # de l'aide, pas une action : sur sa ligne, hors de la liste triée
        hg.addWidget(bg)
        hg.addStretch(1)
        v.addLayout(hg)
        h = QHBoxLayout()
        self.niveau = QComboBox()
        for k, lib in (("recettes", _("Sans IA (gratuit, instantané)")), ("locale", _("IA locale (sur ce poste)")),
                       ("cloud", _("IA cloud (Claude / Gemini, payant, confirmé)"))):
            self.niveau.addItem(lib, k)
        self.niveau.setCurrentIndex(max(0, self.niveau.findData(ed.params.get("commande_niveau") or "recettes")))
        h.addWidget(QLabel(_("Comprendre avec")))
        h.addWidget(self.niveau, 1)
        self.b_comprendre = QPushButton(_("Comprendre"))
        self.b_comprendre.clicked.connect(self.comprendre)
        h.addWidget(self.b_comprendre)
        v.addLayout(h)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        self.zone = QScrollArea()
        self.zone.setWidgetResizable(True)
        self.zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.corps = QWidget()
        self.vc = QVBoxLayout(self.corps)
        self.vc.setAlignment(Qt.AlignTop)
        self.zone.setWidget(self.corps)
        v.addWidget(self.zone, 1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        self.b_faire = bb.button(QDialogButtonBox.Ok)
        self.b_faire.setText(_("Faire"))
        self.b_faire.setEnabled(False)
        bb.accepted.connect(self.faire)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.cases = []
        if phrase:
            self.comprendre()

    def comprendre(self):
        phrase = self.phrase.text().strip()
        if not phrase:
            self.etat.setText(_("Ecrivez d'abord ce que vous voulez."))
            return
        if self._guide_pour(phrase):
            return
        niv = self.niveau.currentData()
        self.ed.params["commande_niveau"] = niv
        if niv == "cloud":
            from . import ia
            if not ia.confirmer_cout(self, self.ed.params, 1200, 0, _("Comprendre la phrase « {p} »", p=phrase[:80])):
                return
        self.etat.setText(_("Je lis votre demande…"))
        self.b_comprendre.setEnabled(False)
        self._occupe(True)
        projet, params = self.ed.projet, self.ed.params
        self._demande = getattr(self, "_demande", 0) + 1     # seule la dernière demande compte
        n = self._demande
        self.tache = Tache(lambda t: C.comprendre(phrase, projet, params, niv), _("Dites-le en clair"))
        self.tache.fini.connect(lambda r, e, n=n: self._si_ouvert(n, r, e))
        self.tache.lier(self)
        self.tache.start()

    def _si_ouvert(self, n, r, e):
        if n != self._demande:
            return
        try:
            self._compris(r, e)
        except RuntimeError:          # fenêtre déjà fermée pendant que l'IA réfléchissait : rien à afficher
            pass

    def _guides(self, guide=None):
        f = self.ed.window()
        if hasattr(f, "guides"):
            f.guides(guide)

    def _guide_pour(self, phrase):
        """« comment retirer la voix ? » : une question, pas un ordre → le guide qui y répond."""
        from . import guides as G
        p = phrase.strip().lower()
        if not (p.startswith(("comment", "je ne sais pas", "aide", "où ", "ou trouver")) or p.endswith("?")):
            return False
        gs = G.chercher(phrase)
        if not gs:
            return False
        self._guides(gs[0]["id"])
        self.etat.setText(_("Guide ouvert à droite : « {t} ».", t=gs[0]["titre"]))
        return True

    def _occupe(self, oui):
        """Pendant que l'IA lit la demande, les boutons d'actions attendent (un clic à la fois)."""
        if getattr(self, "rapides", None) is not None:
            self.rapides.setEnabled(not oui)

    def _compris(self, r, err):
        self.b_comprendre.setEnabled(True)
        self._occupe(False)
        while self.vc.count():
            it = self.vc.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.cases = []
        if err:
            self.etat.setText(_("✕ {e}", e=texte_erreur(err)))
            return
        self.actions = r.get("actions") or []
        src = {"regles": _("compris sans IA")}.get(r.get("source"), r.get("source", ""))
        if not self.actions:
            self.etat.setText(_("Je n'ai pas compris d'action dans cette phrase. Essayez avec des mots comme musique, titre, effet, "
                                "flèche, ralenti, couper… ou choisissez l'IA locale ou cloud.") +
                              (f"<br><span style='color:#ff8c5c'>{r['avertissement']}</span>" if r.get("avertissement") else ""))
            self.b_faire.setEnabled(False)
            return
        self.etat.setText(_("Voici ce que je vais faire ({s}) ; décochez ce que vous ne voulez pas :", s=src) +
                          (f"<br><span style='color:#ff8c5c'>{r['avertissement']}</span>" if r.get("avertissement") else ""))
        for a in self.actions:
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(4, 2, 4, 2)
            c = QCheckBox()
            c.setChecked(True)
            hl.addWidget(c, 0, Qt.AlignTop)
            lb = QLabel(C.decrire(a))
            lb.setWordWrap(True)                 # les longues lignes passent à la ligne : jamais de défilement horizontal
            lb.mousePressEvent = lambda _e, c=c: c.toggle()
            hl.addWidget(lb, 1)
            self.vc.addWidget(w)
            self.cases.append(c)
        self.b_faire.setEnabled(True)

    def choisies(self):
        return [a for a, c in zip(self.actions, self.cases) if c.isChecked()]

    def faire(self):
        acts = self.choisies()
        if not acts:
            self.reject()
            return
        if C.a_preparer(acts) and not all("_par_plan" in a for a in C.a_preparer(acts)):
            # étalonnage auto ou accordé : une image de chaque plan est lue d'abord, avec la progression
            ed = self.ed
            sel = ed._clip_selectionne() if hasattr(ed, "_clip_selectionne") else None
            projet, t0 = ed.projet, ed.timeline.position
            self.b_faire.setEnabled(False)
            self.b_comprendre.setEnabled(False)
            self.etat.setText(_("Lecture d'une image de chaque plan…"))
            self.tache = Tache(lambda t: C.preparer(acts, projet, sel, t0, lambda f, nom="": t.avancer(f, nom), lambda: t.arret),
                               _("Étalonnage de la séquence"))
            self.tache.progression.connect(lambda f, txt: self.etat.setText(_("Lecture des plans : {p} % — {n}", p=int(f * 100), n=txt)),
                                           Qt.QueuedConnection)
            self.tache.fini.connect(lambda r, e: self._prepare(acts, e), Qt.QueuedConnection)
            self.tache.start()
            return
        self._faire(acts)

    def _prepare(self, acts, err):
        self.b_comprendre.setEnabled(True)
        if err:
            self.b_faire.setEnabled(True)
            self.etat.setText(_("✕ {e}", e=texte_erreur(err)))
            return
        self._faire(acts)

    def _faire(self, acts):
        n = C.appliquer(acts, self.ed)
        if any(a.get("action") == "ranger_rushes" for a in acts) and hasattr(self.ed, "biblio"):
            self.ed.biblio.remplir(self.ed.projet)
        self.ed.rafraichir()
        self.ed.encart.message(_("{n} action(s) faite(s). Edition › Annuler défait tout d'un coup.", n=n), 8000)
        self.accept()

    def done(self, r):
        if self.tache is not None and self.tache.isRunning():
            self.tache.wait(500)
            if self.tache.isRunning():
                from . import dialogues_musiques as DM
                DM._EN_ROUTE.append(self.tache)
        super().done(r)
