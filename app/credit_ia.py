"""Crédit restant chez le fournisseur d'IA choisi, et un clic pour le recharger (0.9.72).

fal.ai donne le solde du compte (API Platform) ; Google ne publie pas le solde d'une clef Gemini (la facture suit le
projet Google Cloud) : on montre alors le lien vers la page de suivi des dépenses.
"""
import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .langue import _

NOMS = {"fal": "fal.ai", "google": "Gemini"}


def fournisseur_du_moteur(ident, params=None):
    """« kling-o3-ref » → « fal » ; « locale » ou « flow » → None."""
    if not ident or ident in ("locale", "flow"):
        return None
    from . import generateurs_video as GV
    m = GV.modele(ident, params)
    return (m or {}).get("fournisseur")


def texte_credit(fournisseur, solde):
    nom = NOMS.get(fournisseur, fournisseur)
    if solde is None:
        if fournisseur == "google":
            return _("Crédit {n} : Google ne le donne pas ici ; « Recharger » ouvre le suivi des dépenses.", n=nom)
        return _("Crédit {n} : inconnu (clef sans droit de lecture du solde, ou hors ligne).", n=nom)
    montant, devise = solde
    m = f"{montant:.2f}".replace(".", ",")
    return _("Crédit {n} restant : {m} {d}", n=nom, m=m, d="$" if devise == "USD" else devise) + \
        ("  ⚠ " + _("presque épuisé") if montant < 2 else "")


class LigneCredit(QWidget):
    """« Crédit fal.ai restant : 12,40 $ [Recharger…] » ; se met à jour quand le moteur change (montrer(fournisseur))."""

    def __init__(self, params, fournisseur=None, parent=None):
        super().__init__(parent)
        self.params, self.fournisseur, self.tache = params, None, None
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.lbl = QLabel("")
        self.lbl.setWordWrap(True)
        self.lbl.setStyleSheet("color:#9aa4b2")
        h.addWidget(self.lbl, 1)
        self.b = QPushButton(_("Recharger…"))
        self.b.setToolTip(_("Ouvre la page de votre compte pour ajouter du crédit"))
        self.b.clicked.connect(self.recharger)
        h.addWidget(self.b)
        self.montrer(fournisseur)

    def montrer(self, fournisseur):
        self.fournisseur = fournisseur
        self.setVisible(bool(fournisseur))
        if not fournisseur:
            return
        from . import generateurs_video as GV
        if not GV.clef(self.params, fournisseur):
            self.lbl.setText(_("Pas de clef {n} sur ce poste : Préférences › IA › Connecter une IA.", n=NOMS.get(fournisseur, fournisseur)))
            return
        self.lbl.setText(_("Crédit {n} : lecture…", n=NOMS.get(fournisseur, fournisseur)))
        # simple lecture réseau de quelques secondes au plus : un fil Python, relevé par une minuterie (pas une tâche suivie)
        import threading
        res = {}

        def lire(f=fournisseur):
            try:
                res["r"] = GV.credit(self.params, f)
            except Exception:      # noqa: BLE001
                res["r"] = None
            res["fini"] = True
        threading.Thread(target=lire, daemon=True).start()

        def relever(f=fournisseur, n=[0]):
            try:
                if res.get("fini"):
                    if f == self.fournisseur:
                        self.lbl.setText(texte_credit(f, res.get("r")))
                    return
                n[0] += 1
                if n[0] < 100:
                    QTimer.singleShot(200, relever)
            except RuntimeError:
                pass
        QTimer.singleShot(200, relever)

    def recharger(self):
        from . import generateurs_video as GV
        url = GV.PAGES_CREDIT.get(self.fournisseur or "fal")
        if getattr(self, "_test_ouvert", None) is not None:
            self._test_ouvert.append(url)
            return
        webbrowser.open(url)
