"""« Connecter une IA » : pour chaque fournisseur, à quoi il sert, comment obtenir sa propre clef en trois étapes,
le lien direct, un test gratuit. Les clefs restent sur ce poste (coffre du système) ; la synchro chiffrée les transmet
aux autres postes de l'utilisateur s'il l'a cochée. PhilCut ne contient aucune clef."""
import json, urllib.error, urllib.request

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QWidget, QDialogButtonBox,
                               QPlainTextEdit)

from . import generateurs_video as GV
from .langue import _
from .widgets import boutons_fr, oeil

FOURNISSEURS_TEXTE = {
    "claude": {"nom": "Claude (Anthropic)", "clef": "clef_claude", "page": "https://console.anthropic.com/",
               "role": _("Assistant de montage (idées, recette, textes pour les réseaux). Quelques centimes par vidéo."),
               "etapes": [_("Ouvrez la console Anthropic et créez un compte (e-mail)."),
                          _("Ajoutez un peu de crédit (Facturation), puis « API Keys » › « Create Key », nommée PhilCut."),
                          _("Copiez la clef (elle commence par « sk-ant- ») et collez-la ici.")]},
    "gemini": {"nom": "Gemini (Google)", "clef": "clef_gemini", "page": GV.FOURNISSEURS["google"]["page"],
               "role": _("Assistant de montage, et plans vidéo générés (Gemini Omni Flash) avec la même clef."),
               "etapes": GV.FOURNISSEURS["google"]["etapes"]},
    "fal": {"nom": GV.FOURNISSEURS["fal"]["nom"], "clef": "clef_fal", "page": GV.FOURNISSEURS["fal"]["page"],
            "role": _("Plans vidéo générés par d'autres modèles (Kling, Seedance…), paiement à l'usage, une seule clef."),
            "etapes": GV.FOURNISSEURS["fal"]["etapes"]},
}


def tester(cle_fournisseur, cle):
    if cle_fournisseur == "gemini":
        return GV.tester_clef("google", cle)
    if cle_fournisseur == "fal":
        return GV.tester_clef("fal", cle)
    if not cle:
        return False, _("Aucune clef saisie.")
    req = urllib.request.Request("https://api.anthropic.com/v1/models?limit=5", headers={"x-api-key": cle, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            n = len(json.loads(r.read().decode("utf-8")).get("data", []))
        return True, _("Clef Claude valide ({n} modèles).", n=n)
    except urllib.error.HTTPError as e:
        return False, _("Clef Claude refusée (HTTP {c}).", c=e.code)
    except Exception as e:      # noqa: BLE001
        return False, _("Test impossible : {e}", e=e)


class DialogueConnexionIA(QDialog):
    def __init__(self, parent, params, onglet=None):
        super().__init__(parent)
        self.setWindowTitle(_("Connecter une IA"))
        self.resize(640, 460)
        self.params = params
        v = QVBoxLayout(self)
        intro = QLabel(_("Chaque utilisateur se sert de <b>sa propre clef</b>, payée à l'usage chez le fournisseur : PhilCut n'en contient aucune. "
                         "La clef reste sur ce poste, dans le coffre du système ; cochez « Synchroniser aussi les mots de passe et clefs » "
                         "(Préférences › Comptes et synchro) pour la retrouver sur vos autres postes. Rien n'est envoyé sans votre clic, "
                         "et le prix estimé s'affiche avant chaque envoi."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.onglets = QTabWidget()
        v.addWidget(self.onglets, 1)
        self.champs = {}
        for k, f in FOURNISSEURS_TEXTE.items():
            w = QWidget()
            lv = QVBoxLayout(w)
            r = QLabel(f"<b>{f['nom']}</b> — {f['role']}")
            r.setWordWrap(True)
            lv.addWidget(r)
            et = QLabel("<ol>" + "".join(f"<li>{e}</li>" for e in f["etapes"]) + "</ol>")
            et.setWordWrap(True)
            et.setTextFormat(Qt.RichText)
            lv.addWidget(et)
            b = QPushButton(_("Ouvrir la page pour créer ma clef"))
            b.clicked.connect(lambda _c=False, u=f["page"]: QDesktopServices.openUrl(QUrl(u)))
            lv.addWidget(b, 0, Qt.AlignLeft)
            h = QHBoxLayout()
            champ = QLineEdit(params.get(f["clef"], ""))
            champ.setEchoMode(QLineEdit.Password)
            champ.setPlaceholderText(_("Collez votre clef ici"))
            oeil(champ)
            bt = QPushButton(_("Tester (gratuit)"))
            res = QLabel("")
            res.setWordWrap(True)
            bt.clicked.connect(lambda _c=False, k=k, champ=champ, res=res: self._tester(k, champ, res))
            h.addWidget(champ, 1)
            h.addWidget(bt)
            lv.addLayout(h)
            lv.addWidget(res)
            if k == "fal":
                lab = QLabel(_("Modèles fal supplémentaires (facultatif) : un par ligne, « identifiant du modèle | prix en $ par seconde ». "
                               "L'identifiant se copie sur la page du modèle, sur fal.ai."))
                lab.setWordWrap(True)
                lv.addWidget(lab)
                self.perso = QPlainTextEdit("\n".join(f"{m.get('modele')} | {m.get('prix_s', '')}" for m in params.get("modeles_video_perso") or []))
                self.perso.setPlaceholderText("fal-ai/…/text-to-video | 0.12")
                self.perso.setMaximumHeight(70)
                lv.addWidget(self.perso)
            lv.addStretch(1)
            self.champs[k] = champ
            self.onglets.addTab(w, f["nom"])
            if onglet == k:
                self.onglets.setCurrentIndex(self.onglets.count() - 1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self._valider)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _tester(self, k, champ, res):
        from .ia import nettoyer_clef
        res.setText(_("Test en cours…"))
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        ok, msg = tester(k, nettoyer_clef(champ.text()))
        res.setText(("✓ " if ok else "✕ ") + msg)

    def _valider(self):
        from .ia import nettoyer_clef
        for k, champ in self.champs.items():
            self.params[FOURNISSEURS_TEXTE[k]["clef"]] = nettoyer_clef(champ.text())
        perso = []
        for ligne in self.perso.toPlainText().splitlines():
            parts = [p.strip() for p in ligne.split("|")]
            if parts and parts[0]:
                try:
                    prix = float(parts[1].replace(",", ".")) if len(parts) > 1 and parts[1] else 0.2
                except ValueError:
                    prix = 0.2
                perso.append({"modele": parts[0], "prix_s": prix, "nom": parts[0].split("/")[-2] if parts[0].count("/") >= 2 else parts[0]})
        self.params["modeles_video_perso"] = perso
        self.params.enregistrer()
        self.accept()
