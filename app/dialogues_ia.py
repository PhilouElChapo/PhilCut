"""Fenetres communes de l'assistant IA : tache d'attente, avancement, verification de la clef, consigne personnelle."""
import datetime, os, re, shutil

from PySide6.QtCore import Qt, QThread, Signal, QEventLoop
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox,
                               QPushButton, QDialogButtonBox, QTextBrowser, QCheckBox, QProgressDialog, QFileDialog,
                               QMessageBox, QApplication, QListWidget, QListWidgetItem, QPlainTextEdit)

from .langue import _
from . import ia, apprentissage
from .taches import FilProtege


# ------------------------------------------------------------------ tache d'attente
class _Tache(FilProtege):
    fini = Signal(object, object)
    info = Signal(str)

    def __init__(self, fonction):
        super().__init__()
        self.fonction = fonction

    def run(self):
        ia.suivre(self.info.emit)
        try:
            self.fini.emit(self.fonction(), None)
        except Exception as e:                          # remonte a l'interface
            self.fini.emit(None, e)


def executer(parent, texte, fonction):
    """Lance fonction() hors de l'interface avec une fenetre d'attente ; renvoie son resultat ou leve son erreur."""
    pd = QProgressDialog(texte, None, 0, 0, parent)
    pd.setWindowTitle("PhilCut")
    pd.setWindowModality(Qt.WindowModal)
    pd.setMinimumDuration(300)
    t = _Tache(fonction)
    res = {}
    boucle = QEventLoop()
    import time
    debut = time.monotonic()
    t.info.connect(lambda m: pd.setLabelText(f"{texte}\n\n[{int(time.monotonic() - debut)} s] {m}"))

    def fin(r, e):
        res["r"], res["e"] = r, e
        boucle.quit()
    t.fini.connect(fin)
    t.start()
    boucle.exec()
    t.wait()
    pd.close()
    if res.get("e"):
        raise res["e"]
    return res.get("r")


class _TacheSuivie(FilProtege):
    etape = Signal(str, int, int)          # texte, valeur, total
    detail = Signal(str)
    fini = Signal(object, object)

    def __init__(self, fonction):
        super().__init__()
        self.fonction, self.stop = fonction, False

    def run(self):
        ia.suivre(self.detail.emit)
        try:
            self.fini.emit(self.fonction(self), None)
        except Exception as e:
            self.fini.emit(None, e)

    def avancer(self, texte, valeur=0, total=0):
        if self.stop:
            raise InterruptedError(_("Arrêté à votre demande."))
        self.etape.emit(texte, valeur, total)

    def noter(self, texte):
        self.detail.emit(texte)


class Avancement(QDialog):
    """Fenetre d'avancement : etape en cours, barre (page x / y), detail des operations, bouton Arreter."""

    def __init__(self, parent, titre):
        from PySide6.QtWidgets import QProgressBar, QPlainTextEdit
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.setMinimumWidth(560)
        self.setWindowModality(Qt.WindowModal)
        v = QVBoxLayout(self)
        self.etat = QLabel(_("Préparation..."))
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        self.barre = QProgressBar()
        self.barre.setRange(0, 0)
        v.addWidget(self.barre)
        self.journal = QPlainTextEdit()
        self.journal.setReadOnly(True)
        self.journal.setMaximumHeight(150)
        self.journal.setStyleSheet("font-size:12px;color:#444")
        v.addWidget(self.journal)
        h = QHBoxLayout()
        h.addStretch(1)
        self.b_stop = QPushButton(_("Arrêter"))
        h.addWidget(self.b_stop)
        v.addLayout(h)

    def etape(self, texte, valeur, total):
        self.etat.setText(texte)
        if total:
            self.barre.setRange(0, total)
            self.barre.setValue(valeur)
            self.barre.setFormat(f"{valeur} / {total}")
        else:
            self.barre.setRange(0, 0)

    def noter(self, texte):
        import time
        self.journal.appendPlainText(time.strftime("%H:%M:%S  ") + texte)


def executer_suivi(parent, titre, fonction):
    """Comme executer(), avec une fenetre d'avancement : fonction(tache) appelle tache.avancer(texte, n, total)
    et tache.noter(detail). Leve l'erreur de fonction, ou InterruptedError si l'utilisateur arrete."""
    dlg = Avancement(parent, titre)
    t = _TacheSuivie(fonction)
    res = {}
    boucle = QEventLoop()
    t.etape.connect(dlg.etape)
    t.detail.connect(dlg.noter)
    t.fini.connect(lambda r, e: (res.update(r=r, e=e), boucle.quit()))
    dlg.b_stop.clicked.connect(lambda: (setattr(t, "stop", True), dlg.etat.setText(_("Arrêt en cours..."))))
    t.start()
    dlg.show()
    boucle.exec()
    t.wait()
    dlg.close()
    if res.get("e"):
        raise res["e"]
    return res.get("r")


def verifier_cle(parent, params):
    if ia.disponible(params):
        return True
    QMessageBox.information(parent, _("Assistant IA"), _(
        "Pour utiliser l'assistant IA, renseignez votre clef Claude ou Gemini dans Edition › Préférences › IA.\n\n"
        "Rien n'est envoyé sans votre clic, et PhilCut vous prévient si la vidéo ou ses textes contiennent des données sensibles."))
    return False


def preparer_envoi(parent, params, texte):
    """Clef presente + rappel des donnees sensibles. True = on peut envoyer."""
    return verifier_cle(parent, params) and ia.confirmer_envoi(parent, texte, ia.nom_moteur(params))


def montrer_erreur(parent, e):
    QMessageBox.warning(parent, _("Assistant IA"), _("L'IA n'a pas pu répondre :\n{e}", e=e))



def demander_consigne(parent, params, titre, cle, consigne_philcut):
    """Fenetre avant l'envoi : consigne personnelle ajoutee a celle de PhilCut (None si annule).
    Les 10 dernieres consignes sont gardees (et synchronisees entre postes) pour les reprendre d'un clic."""
    d = QDialog(parent)
    d.setWindowTitle(titre)
    d.resize(640, 420)
    v = QVBoxLayout(d)
    lb = QLabel(_("Vous pouvez ajouter votre propre consigne à celle de PhilCut (facultatif). "
                  "Ex. : « insiste sur les montants », « fais un résumé en 3 lignes », « dis-moi si je dois répondre »."))
    lb.setWordWrap(True)
    v.addWidget(lb)
    historique = list(params.get(cle) or [])
    cb = QComboBox()
    cb.addItem(_("— consignes déjà utilisées —"), "")
    for h in historique:
        cb.addItem(h if len(h) < 90 else h[:87] + "...", h)
    cb.setEnabled(bool(historique))
    hc = QHBoxLayout()
    hc.addWidget(cb, 1)
    b_sup = QPushButton(_("Supprimer"))
    b_sup.setToolTip(_("Retirer cette consigne de la liste des consignes déjà utilisées"))
    hc.addWidget(b_sup)
    v.addLayout(hc)

    def supprimer():
        x = cb.currentData()
        if not x:
            return
        params[cle] = [h for h in (params.get(cle) or []) if h != x]
        params.enregistrer()
        cb.removeItem(cb.currentIndex())
        cb.setCurrentIndex(0)
        zone.clear()
        b_sup.setEnabled(cb.count() > 1)
        cb.setEnabled(cb.count() > 1)
    b_sup.clicked.connect(supprimer)
    b_sup.setEnabled(bool(historique))
    zone = QPlainTextEdit()
    zone.setPlaceholderText(_("Votre consigne (laisser vide pour la consigne habituelle)"))
    v.addWidget(zone, 1)
    cb.currentIndexChanged.connect(lambda i: cb.itemData(i) and zone.setPlainText(cb.itemData(i)))
    voir = QPushButton(_("Voir la consigne de PhilCut"))
    voir.setCheckable(True)
    texte_ph = QTextBrowser()
    texte_ph.setPlainText(consigne_philcut)
    texte_ph.hide()
    voir.toggled.connect(texte_ph.setVisible)
    v.addWidget(voir, 0, Qt.AlignLeft)
    v.addWidget(texte_ph, 1)
    hm = QHBoxLayout()
    hm.addWidget(QLabel(_("Envoyer à :")))
    cb_ia = QComboBox()
    for m, _clef in ia.moteurs(params):
        cb_ia.addItem({"claude": "Claude (Anthropic)", "gemini": "Gemini (Google)"}[m], m)
    cb_ia.setToolTip(_("L'IA choisie dans les Préférences est proposée ; vous pouvez en prendre une autre pour cette "
                       "demande seulement"))
    hm.addWidget(cb_ia)
    hm.addStretch(1)
    if cb_ia.count() > 1:
        v.addLayout(hm)
    bb = QDialogButtonBox()
    bb.addButton(_("Lancer l'analyse"), QDialogButtonBox.AcceptRole)
    bb.addButton(_("Annuler"), QDialogButtonBox.RejectRole)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    v.addWidget(bb)
    zone.setFocus()
    if d.exec() != QDialog.Accepted:
        return None
    ia.MOTEUR_FORCE = cb_ia.currentData() if cb_ia.count() > 1 else None   # pour cette demande
    perso = zone.toPlainText().strip()
    if perso:
        params[cle] = [perso] + [h for h in historique if h != perso][:9]
        params.enregistrer()
    return perso


def ajouter_consigne(consignes, perso):
    if not perso:
        return consignes
    return consignes + ("\n\nConsigne supplémentaire de l'utilisateur (à suivre en priorité, en gardant le format de réponse "
                        "demandé) :\n" + perso)


