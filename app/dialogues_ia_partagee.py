"""Fenêtre « IA PhilFactory : dossier commun » (0.9.46) : où ranger les modèles d'IA locale pour tous les logiciels
PhilFactory, et transfert des modèles déjà téléchargés (déplacement sur le même disque, copie vérifiée sinon)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QVBoxLayout)

from . import ia_partagee as IP, packs_ia as P
from .config import VERSION, dossier_programme, est_portable
from .langue import _
from .taches import Tache
from .widgets import CaseLongue


class DialogueIACommune(QDialog):
    def __init__(self, fenetre, params):
        super().__init__(fenetre)
        self.fenetre, self.params, self.tache = fenetre, params, None
        self.setWindowTitle(_("IA PhilFactory : dossier commun"))
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        n, octets = IP.a_transferer(P.dossier_modeles_propre())
        rdv = IP.lire_rdv()
        autres = [x for x in (rdv.get("logiciels") or {}) if x != P.LOGICIEL]
        t = _("<b>Un modèle d'IA locale n'est téléchargé qu'une fois pour tous les logiciels PhilFactory</b> (PhilCut, PhilMusic, "
              "PhilPic…) : ils le rangent dans ce dossier commun et se le partagent. Vous choisissez où il est.")
        if autres and rdv.get("dossier"):
            t += "<br><br>" + _("{l} range déjà ses IA dans « {d} ».", l=", ".join(sorted(autres)), d=rdv["dossier"])
        if n:
            t += "<br><br>" + _("PhilCut a déjà {t} de modèles dans son propre dossier : ils seront <b>rangés dans le dossier commun</b> "
                                "(déplacés si c'est le même disque, sinon copiés puis vérifiés avant que l'original soit effacé). "
                                "Un modèle déjà présent n'est pas recopié.", t=P.taille_texte(octets))
        lb = QLabel(t)
        lb.setWordWrap(True)
        lb.setTextFormat(Qt.RichText)
        v.addWidget(lb)
        h = QHBoxLayout()
        actuel = params.get("ia_dossier_commun") or rdv.get("dossier") or IP.dossier_propose(dossier_programme(), est_portable())
        self.chemin = QLineEdit(actuel)
        h.addWidget(self.chemin, 1)
        b = QPushButton(_("Choisir…"))
        b.clicked.connect(self._choisir)
        h.addWidget(b)
        v.addLayout(h)
        self.partage = CaseLongue(_("Partager mes IA avec les autres logiciels PhilFactory (un petit fichier dans votre profil dit où "
                                    "est ce dossier, pour qu'un logiciel installé plus tard le trouve tout de suite)"))
        self.partage.setChecked(bool(params.get("ia_partage", not est_portable())))
        v.addWidget(self.partage)
        if est_portable():
            note = QLabel(_("Version portable : sans cette case, rien n'est écrit dans votre profil ; les autres logiciels portables "
                            "rangés à côté de PhilCut trouvent quand même ce dossier."))
            note.setWordWrap(True)
            note.setStyleSheet("color:#9aa4b2")
            v.addWidget(note)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hb = QHBoxLayout()
        hb.addStretch(1)
        self.b_ok = QPushButton(_("Ranger mes IA ici") if n else _("Utiliser ce dossier"))
        self.b_ok.setStyleSheet("font-weight:600")
        self.b_ok.clicked.connect(self.valider)
        hb.addWidget(self.b_ok)
        self.b_annuler = QPushButton(_("Plus tard"))
        self.b_annuler.clicked.connect(self.reject)
        hb.addWidget(self.b_annuler)
        v.addLayout(hb)

    def _choisir(self):
        d = QFileDialog.getExistingDirectory(self, _("Dossier commun des IA PhilFactory"), self.chemin.text() or os.path.expanduser("~"))
        if d:
            if os.path.basename(d.rstrip("/\\")) != IP.NOM_DOSSIER and not os.path.isfile(os.path.join(d, IP.INDEX)):
                d = os.path.join(d, IP.NOM_DOSSIER)
            self.chemin.setText(d)

    def valider(self):
        commun = self.chemin.text().strip()
        if not commun:
            return
        try:
            IP.preparer(commun, P.LOGICIEL)
        except OSError as e:
            QMessageBox.warning(self, self.windowTitle(), _("Impossible de créer ce dossier : {e}", e=e))
            return
        self.b_ok.setEnabled(False)
        source = P.dossier_modeles_propre()

        def travail(t):
            r = IP.transferer(source, commun, P.LOGICIEL, progression=lambda f, nom="": t.avancer(f, _("Rangement : {n}", n=nom)),
                              arret=lambda: t.arret)
            P.regler_commun(commun)
            return r, P.adopter()
        self.tache = Tache(travail, _("IA PhilFactory"))
        self.tache.progression.connect(lambda f, txt: self.etat.setText(f"{int(f * 100)} % — {txt}"), Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, e: self._fini(commun, r, e), Qt.QueuedConnection)
        self.tache.start()

    def _fini(self, commun, r, e):
        if e:
            self.b_ok.setEnabled(True)
            self.etat.setText(_("✕ Rangement interrompu : {e}. Ce qui était déjà rangé reste dans le dossier commun ; relancez pour "
                                "finir.", e=e))
            return
        (n, doubles), repris = r
        self.params["ia_dossier_commun"] = commun
        self.params["ia_partage"] = self.partage.isChecked()
        self.params["ia_commun_propose"] = True
        if self.partage.isChecked():
            try:
                IP.annoncer(commun, P.LOGICIEL, VERSION, dossier_programme())
            except OSError:
                pass
        else:
            try:
                IP.retirer_rdv(P.LOGICIEL)
            except OSError:
                pass
        self.params.enregistrer()
        msg = _("✓ Dossier commun : {d}. {n} fichier(s) rangé(s).", d=commun, n=n)
        if doubles:
            msg += " " + _("{t} en double libérés.", t=P.taille_texte(doubles))
        if repris:
            msg += " " + _("{n} modèle(s) d'un autre logiciel repris ici, sans téléchargement.", n=len(repris))
        self.etat.setText(msg)
        self.b_annuler.setText(_("Fermer"))

    def reject(self):
        if self.tache is not None and self.tache.isRunning():
            return                                    # un rangement ne s'interrompt pas en fermant la fenêtre
        super().reject()


def demarrage(fenetre, params):
    """Au démarrage : dossier commun réglé (et modèles d'un autre logiciel repris), ou proposition sur l'Accueil."""
    commun = params.get("ia_dossier_commun")
    if commun and os.path.isdir(commun):
        P.regler_commun(commun)
        try:
            P.adopter()
            if params.get("ia_partage"):
                IP.annoncer(commun, P.LOGICIEL, VERSION, dossier_programme())
        except Exception:      # noqa: BLE001
            pass
        return
    if commun:                                        # disque débranché, dossier déplacé : on le dit, rien n'est perdu
        fenetre.accueil.proposer(_("Le dossier commun des IA PhilFactory est introuvable ({d}) : disque débranché ou dossier déplacé ? "
                                   "En attendant, les IA locales qui y sont rangées ne sont pas utilisables.", d=commun),
                                 _("Le retrouver…"), lambda: DialogueIACommune(fenetre, params).exec())
        return
    if params.get("ia_commun_propose"):
        return
    n, octets = IP.a_transferer(P.dossier_modeles_propre())
    rdv = IP.lire_rdv()
    if rdv.get("dossier") and os.path.isdir(rdv["dossier"]):
        texte = _("Un autre logiciel PhilFactory range ses IA locales dans « {d} » : PhilCut peut s'en servir, sans rien retélécharger.",
                  d=rdv["dossier"])
    elif n:
        texte = _("Vos IA locales ({t}) peuvent être rangées dans un dossier commun à tous les logiciels PhilFactory (PhilMusic, PhilPic…) : "
                  "elles ne seront jamais téléchargées deux fois.", t=P.taille_texte(octets))
    else:
        return                                        # rien à ranger : la question viendra au premier modèle installé
    fenetre.accueil.proposer(texte, _("Choisir le dossier commun…"), lambda: DialogueIACommune(fenetre, params).exec())
