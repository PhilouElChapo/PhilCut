"""Crédit restant chez le fournisseur d'IA choisi, et un clic pour le recharger (0.9.72).

fal.ai donne le solde du compte (API Platform) ; Google ne publie pas le solde d'une clef Gemini (la facture suit le
projet Google Cloud) : on montre alors le lien vers la page de suivi des dépenses.
"""
import webbrowser

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from .langue import _

NOMS = {"anthropic": "Claude", "fal": "fal.ai", "google": "Gemini"}


def fournisseur_du_moteur(ident, params=None):
    """« kling-o3-ref » → « fal » ; « locale » ou « flow » → None."""
    if not ident or ident in ("locale", "flow"):
        return None
    from . import generateurs_video as GV
    m = GV.modele(ident, params)
    return (m or {}).get("fournisseur")


def a_clef(params, fournisseur):
    if fournisseur == "anthropic":
        from .ia import nettoyer_clef
        return bool(nettoyer_clef((params or {}).get("clef_claude", "")))
    from . import generateurs_video as GV
    try:
        return bool(GV.clef(params, fournisseur))
    except KeyError:
        return False


def texte_court(fournisseur, solde):
    """Une ligne étroite (0.9.86, plusieurs comptes côte à côte) : « fal.ai : 12,40 $ », « Claude : solde non donné »."""
    nom = NOMS.get(fournisseur, fournisseur)
    if solde is None:
        return _("{n} : solde non donné", n=nom)
    montant, devise = solde
    return f"{nom} : " + f"{montant:.2f}".replace(".", ",") + " " + ("$" if devise == "USD" else devise) + \
        ("  ⚠" if montant < 2 else "")


def texte_credit(fournisseur, solde):
    nom = NOMS.get(fournisseur, fournisseur)
    if solde is None:
        if fournisseur == "google":
            return _("Crédit {n} : Google ne le donne pas ici ; « Recharger » ouvre le suivi des dépenses.", n=nom)
        if fournisseur == "anthropic":
            return _("Crédit {n} : Anthropic ne le donne pas ici ; « Recharger » ouvre votre compte.", n=nom)
        return _("Crédit {n} : inconnu (clef sans droit de lecture du solde, ou hors ligne).", n=nom)
    montant, devise = solde
    m = f"{montant:.2f}".replace(".", ",")
    return _("Crédit {n} restant : {m} {d}", n=nom, m=m, d="$" if devise == "USD" else devise) + \
        ("  ⚠ " + _("presque épuisé") if montant < 2 else "")


class LigneCredit(QWidget):
    """« Crédit fal.ai restant : 12,40 $ [Recharger…] » ; se met à jour quand le moteur change (montrer(fournisseur))."""

    def __init__(self, params, fournisseur=None, parent=None, compact=False):
        super().__init__(parent)
        self.params, self.fournisseur, self.tache = params, None, None
        self.compact = compact
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
        if not a_clef(self.params, fournisseur):
            self.lbl.setText(_("Pas de clef {n} sur ce poste : Préférences › IA › Connecter une IA.", n=NOMS.get(fournisseur, fournisseur)))
            return
        self.lbl.setText(_("Crédit {n} : lecture…", n=NOMS.get(fournisseur, fournisseur)))
        # simple lecture réseau de quelques secondes au plus : un fil Python, relevé par une minuterie (pas une tâche suivie)
        import threading
        res = {}

        def lire(f=fournisseur):
            try:
                res["r"] = None if f == "anthropic" else GV.credit(self.params, f)
            except Exception:      # noqa: BLE001
                res["r"] = None
            res["fini"] = True
        threading.Thread(target=lire, daemon=True).start()

        def relever(f=fournisseur, n=[0]):
            try:
                if res.get("fini"):
                    if f == self.fournisseur:
                        self.lbl.setText(texte_court(f, res.get("r")) if self.compact else texte_credit(f, res.get("r")))
                        self.lbl.setToolTip(texte_credit(f, res.get("r")))
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


# ------------------------------------------------------------------ 0.9.95 : crédit et « Recharger… » partout
def fournisseur_epuise(texte):
    """Le service dont le crédit est épuisé d'après un message d'erreur ("google", "anthropic", "fal"), sinon ""."""
    from .taches import credit_epuise
    t = credit_epuise(texte or "")
    if not t:
        return ""
    return "google" if "Gemini" in t else ("anthropic" if "Claude" in t else "fal")


class LignesCredit(QWidget):
    """Les lignes de crédit des services qu'une fenêtre utilise (compactes, chacune avec « Recharger… »). signaler(texte) :
    après une erreur de crédit épuisé, la ligne du service est relue et son bouton mis en avant."""

    def __init__(self, params, fournisseurs, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        self.lignes = {}
        for f in fournisseurs:
            ligne = LigneCredit(params, f, self, compact=True)
            self.lignes[f] = ligne
            v.addWidget(ligne)

    def signaler(self, texte):
        f = fournisseur_epuise(texte)
        ligne = self.lignes.get(f)
        if ligne is None:
            return False
        ligne.montrer(f)
        ligne.b.setStyleSheet("background:#c62828;color:white;font-weight:600")
        return True

    def surveiller(self, etiquette):
        """Chaque message posé dans `etiquette` (la ligne d'état de la fenêtre) est lu : crédit épuisé = ligne mise en avant."""
        origine = etiquette.setText

        def poser(texte):
            origine(texte)
            try:
                self.signaler(texte)
            except RuntimeError:              # fenêtre détruite
                pass
        etiquette.setText = poser
        return self
