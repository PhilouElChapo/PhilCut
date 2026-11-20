"""« Crédits et recharges des IA » (1.0.1) : tous les services payants dans une seule fenêtre, ce que chacun fabrique dans
PhilCut, son crédit (quand le service le donne), ce que PhilCut y a dépensé ce mois, « Recharger… » et « Connecter… ».

Rien n'est envoyé au service sans clef ; la lecture du solde est une simple question au service, sans frais.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .langue import _
from .widgets import boutons_fr

ORDRE = ("anthropic", "google", "fal", "higgsfield", "heygen")   # l'ordre du choix des IA : le cerveau, puis la vidéo, puis l'animation


def usages(params, fournisseur):
    """Ce que le service fabrique dans PhilCut, en clair : une phrase, puis les modèles vidéo s'il y en a."""
    from . import generateurs_video as GV
    fixes = {"anthropic": _("Le cerveau des assistants : scénarios, plans, animations préparées et corrigées, Réalisateur."),
             "google": _("Le cerveau des assistants (si Gemini est choisi), les images dessinées, les voix, et la vidéo :"),
             "fal": _("La vidéo, les lèvres qui suivent le son, la transformation de voix :"),
             "higgsfield": _("La vidéo, payée à l'usage en dollars sur la console développeur (open.higgsfield.ai). Les crédits du "
                            "site higgsfield.ai ne servent pas ici. Modèles :"),
             "heygen": _("Le rendu dans le cloud des animations HyperFrames (motion design).")}
    noms = sorted(m["nom"] for m in GV.modeles(params) if m.get("fournisseur") == fournisseur)
    return fixes.get(fournisseur, ""), noms


class DialogueCredits(QDialog):
    """Une ligne par service : à quoi il sert, son crédit, la dépense du mois par PhilCut, Recharger…, Connecter…"""

    def __init__(self, parent, params):
        super().__init__(parent)
        from .credit_ia import NOMS, LigneCredit
        self.params = params
        self.setWindowTitle(_("Crédits et recharges des IA"))
        self.resize(820, 600)
        v = QVBoxLayout(self)
        intro = QLabel(_("Chaque service payant que PhilCut sait utiliser, avec votre compte : à quoi il sert, son crédit quand le "
                         "service le donne, et ce que PhilCut y a dépensé ce mois sur ce poste. « Recharger… » ouvre la page de votre "
                         "compte ; PhilCut ne paie jamais rien sans vous montrer le prix et vous demander."))
        intro.setWordWrap(True)
        intro.setAlignment(Qt.AlignJustify)
        v.addWidget(intro)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        interieur = QWidget()
        vi = QVBoxLayout(interieur)
        self.lignes = {}
        for f in ORDRE:
            g = QGroupBox(NOMS.get(f, f))
            gl = QGridLayout(g)
            phrase, noms = usages(params, f)
            lb = QLabel(phrase + ("\n" + " ; ".join(noms) + "." if noms else ""))
            lb.setWordWrap(True)
            gl.addWidget(lb, 0, 0, 1, 2)
            ligne = LigneCredit(params, f, g)
            ligne.setVisible(True)
            self.lignes[f] = ligne
            gl.addWidget(ligne, 1, 0)
            b = QPushButton(_("Connecter…"))
            b.setToolTip(_("Obtenir, coller et tester la clef de ce service (elle va dans le coffre du système)"))
            b.clicked.connect(lambda _c=False, f=f: self.connecter(f))
            gl.addWidget(b, 1, 1)
            gl.setColumnStretch(0, 1)
            vi.addWidget(g)
        vi.addStretch(1)
        zone.setWidget(interieur)
        v.addWidget(zone, 1)
        hb = QHBoxLayout()
        b = QPushButton(_("Relire les soldes"))
        b.clicked.connect(self.relire)
        hb.addWidget(b)
        hb.addStretch(1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Close))
        bb.rejected.connect(self.close)
        hb.addWidget(bb)
        v.addLayout(hb)

    def relire(self):
        for f, ligne in self.lignes.items():
            ligne.montrer(f)

    def connecter(self, fournisseur):
        from .dialogues_connexion_ia import DialogueConnexionIA
        onglet = {"anthropic": "claude", "google": "gemini"}.get(fournisseur, fournisseur)
        d = DialogueConnexionIA(self, self.params, onglet=onglet)
        if getattr(self, "_test_oui", False):
            self._test_connexion = d
            return
        d.exec()
        self.relire()
