"""Fenêtre « Nouveautés du catalogue » (0.9.26) : ce que la veille mensuelle a ajouté (Goodies, modèles de montage,
styles, tampons IA), ✦ pour ce que vous n'avez pas encore vu ; « Vérifier maintenant » interroge GitHub ; un
double-clic ouvre l'endroit où l'utiliser."""
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from . import nouveautes as NV
from .langue import _
from .taches import Tache


class DialogueNouveautes(QDialog):
    def __init__(self, fenetre, params, fermer_seulement=False):
        super().__init__(fenetre)
        self.fenetre, self.params, self.tache, self.fermer_seulement = fenetre, params, None, fermer_seulement
        self.setWindowTitle(_("Nouveautés du catalogue"))
        self.resize(640, 520)
        v = QVBoxLayout(self)
        t = QLabel(_("Chaque mois, de nouveaux Goodies, modèles de montage, styles et tampons IA arrivent sans réinstaller PhilCut. "
                     "✦ = pas encore vu. Double-clic : l'ouvrir là où on l'utilise."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        self.liste = QListWidget()
        self.liste.setWordWrap(True)
        self.liste.itemDoubleClicked.connect(self.ouvrir)
        v.addWidget(self.liste, 1)
        h = QHBoxLayout()
        self.b_verifier = QPushButton(_("Vérifier maintenant"))
        self.b_verifier.clicked.connect(self.verifier)
        h.addWidget(self.b_verifier)
        b_vus = QPushButton(_("Tout marquer comme vu"))
        b_vus.clicked.connect(lambda: (NV.marquer_vus(self.params), self.remplir()))
        h.addWidget(b_vus)
        h.addStretch(1)
        b_f = QPushButton(_("Fermer"))
        b_f.clicked.connect(self.accept)
        h.addWidget(b_f)
        v.addLayout(h)
        self.remplir()

    def remplir(self):
        self.liste.clear()
        items = NV.liste(self.params)
        items.sort(key=lambda a: (not a["nouveau"], list(NV.CATEGORIES).index(a["cat"]), a["nom"]))
        for a in items:
            it = QListWidgetItem(("✦ " if a["nouveau"] else "") + f"{NV.CATEGORIES[a['cat']]} — {a['nom']}" + (f"\n{a['desc']}" if a.get("desc") else ""))
            it.setData(Qt.UserRole, a)
            self.liste.addItem(it)
        n = sum(1 for a in items if a["nouveau"])
        quand = self.params.get("nouveautes_verifie") or ""
        txt = _("{t} élément(s) dans le catalogue, dont {n} nouveau(x) pour vous.", t=len(items), n=n)
        if quand:
            txt += " " + _("Dernière vérification : {d}.", d=quand)
        self.etat.setText(txt)

    def verifier(self):
        self.b_verifier.setEnabled(False)
        self.etat.setText(_("Vérification du catalogue en ligne…"))
        avant = {f"{a['cat']}:{a['id']}" for a in NV.liste(self.params)}
        self.tache = Tache(lambda t: __import__("app.catalogue_ligne", fromlist=["telecharger"]).telecharger(NV.FICHIER, 10), _("Nouveautés"))

        def fin(r, err):
            try:
                self.b_verifier.setEnabled(True)
                NV.integrer(reseau=False)
                self.params["nouveautes_verifie"] = datetime.datetime.now().strftime("%d/%m/%Y %Hh%M")
                self.remplir()
                apres = {f"{a['cat']}:{a['id']}" for a in NV.liste(self.params)}
                if r is None:
                    self.etat.setText(_("Pas de réseau ou GitHub injoignable : voici la dernière copie gardée sur ce poste."))
                elif apres - avant:
                    self.etat.setText(_("✓ {n} nouveauté(s) arrivée(s).", n=len(apres - avant)) + " " + self.etat.text())
                else:
                    self.etat.setText(_("✓ Catalogue à jour : rien de nouveau depuis la dernière fois. La veille en ajoute chaque mois.")
                                      + " " + self.etat.text())
            except RuntimeError:
                pass
        self.tache.fini.connect(fin, Qt.QueuedConnection)
        self.tache.start()

    def ouvrir(self, it):
        a = it.data(Qt.UserRole)
        vus = set(self.params.get("nouveautes_vues") or [])
        vus.add(f"{a['cat']}:{a['id']}")
        self.params["nouveautes_vues"] = sorted(vus)
        if self.fermer_seulement:
            self.accept()
            return
        ed = self.fenetre.editeur_courant() if hasattr(self.fenetre, "editeur_courant") else None
        if ed is None and hasattr(self.fenetre, "_editeur_ou_nouveau"):
            ed = self.fenetre._editeur_ou_nouveau()
        self.accept()
        if ed is None:
            return
        if a["cat"] == "goodies":
            ed.outil("goodies")
        elif a["cat"] == "modeles_montage":
            ed.modeles_montage()
        elif a["cat"] == "tampons_ia":
            ed.tampons(3)                       # onglet « Tampons IA »
        elif a["cat"] == "styles":
            from .preferences import DialoguePreferences
            DialoguePreferences(self.fenetre, self.params, "Assistant").exec()
