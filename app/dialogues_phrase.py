"""Phrase secrète de la synchronisation des mots de passe et clefs : choisie une fois sur le premier poste, puis
redonnée une fois sur chaque autre poste. Elle reste dans le coffre du système de chaque poste ; elle ne voyage jamais."""
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox

from . import coffre, reglages
from .widgets import oeil
from .langue import _


def demander_phrase(parent, params, nouvelle=True):
    """nouvelle=True : choisir la phrase (deux fois, indice facultatif). Sinon : la redonner pour lire celles des autres
    postes. Renvoie True si une phrase valable est gardée dans le coffre de ce poste."""
    d = QDialog(parent)
    d.setWindowTitle(_("Phrase secrète de la synchronisation"))
    f = QFormLayout(d)
    if nouvelle:
        texte = _("Vos mots de passe et clefs (IA, Pixabay, Pexels, comptes) vont être envoyés à vos autres postes, chiffrés "
                  "par une phrase secrète. Choisissez-la : il faudra la redonner une fois sur chaque autre poste. "
                  "Elle n'est jamais envoyée ; si vous la perdez, il suffit de recopier les clefs à la main.")
    else:
        indice = reglages.lire_indice(params)
        texte = _("Vos autres postes ont partagé des mots de passe et clefs, chiffrés par votre phrase secrète. "
                  "Donnez-la une fois : ils seront repris sur ce poste.") + (("\n" + _("Indice : {i}", i=indice)) if indice else "")
    aide = QLabel(texte)
    aide.setWordWrap(True)
    aide.setMinimumWidth(460)
    f.addRow(aide)
    ind = QLineEdit()                        # l'indice d'abord, la phrase ensuite
    if nouvelle:
        ind.setPlaceholderText(_("Facultatif, visible sur vos autres postes"))
        f.addRow(_("Indice"), ind)
    p1 = QLineEdit()
    oeil(p1)                                 # œil : afficher la phrase pour vérifier ce qu'on tape
    f.addRow(_("Phrase secrète"), p1)
    p2 = QLineEdit()
    oeil(p2)
    if nouvelle:
        f.addRow(_("Encore une fois"), p2)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    f.addRow(bb)
    while d.exec():
        phrase = p1.text()
        if len(phrase) < 6:
            QMessageBox.warning(d, d.windowTitle(), _("La phrase doit faire au moins 6 caractères."))
            continue
        if nouvelle:
            if phrase != p2.text():
                QMessageBox.warning(d, d.windowTitle(), _("Les deux phrases sont différentes."))
                continue
            coffre.enregistrer(reglages.PHRASE, phrase)
            reglages.ecrire_indice(params, ind.text().strip())
            params["secrets_empreinte"] = ""
            reglages.synchro_secrets_auto(params)
            return True
        try:
            reglages.lire_secrets_drive(params, phrase)
        except reglages.PhraseRequise:
            QMessageBox.warning(d, d.windowTitle(), _("Ce n'est pas la bonne phrase."))
            continue
        except (OSError, ValueError, KeyError):
            pass
        coffre.enregistrer(reglages.PHRASE, phrase)
        n = reglages.synchro_secrets_auto(params)
        QMessageBox.information(d, d.windowTitle(), _("{n} mot(s) de passe ou clef(s) repris de vos autres postes.", n=n))
        return True
    return False


def changer_phrase(parent, params):
    """Changer la phrase secrète ou son indice (0.9.62) : la phrase actuelle, puis la nouvelle (deux fois). Les secrets
    partagés sont rechiffrés ; vos autres postes redemanderont la phrase une fois."""
    d = QDialog(parent)
    d.setWindowTitle(_("Changer la phrase secrète ou l'indice"))
    f = QFormLayout(d)
    aide = QLabel(_("Pour changer seulement l'indice, redonnez la phrase actuelle dans les trois cases. Si vous changez la phrase, "
                    "vos autres postes vous la demanderont une fois."))
    aide.setWordWrap(True)
    aide.setMinimumWidth(460)
    f.addRow(aide)
    ind = QLineEdit(reglages.lire_indice(params))                 # l'indice en haut, les phrases plus bas
    ind.setPlaceholderText(_("Facultatif, visible sur vos autres postes (jamais la phrase elle-même)"))
    f.addRow(_("Indice"), ind)
    a, p1, p2 = QLineEdit(), QLineEdit(), QLineEdit()
    for x in (a, p1, p2):
        oeil(x)
    f.addRow(_("Phrase actuelle"), a)
    f.addRow(_("Nouvelle phrase"), p1)
    f.addRow(_("Encore une fois"), p2)
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.accepted.connect(d.accept)
    bb.rejected.connect(d.reject)
    f.addRow(bb)
    while d.exec():
        if len(p1.text()) < 6:
            QMessageBox.warning(d, d.windowTitle(), _("La phrase doit faire au moins 6 caractères."))
            continue
        if p1.text() != p2.text():
            QMessageBox.warning(d, d.windowTitle(), _("Les deux phrases sont différentes."))
            continue
        try:
            reglages.changer_phrase(params, a.text(), p1.text(), ind.text().strip())
        except reglages.PhraseRequise:
            QMessageBox.warning(d, d.windowTitle(), _("Ce n'est pas la phrase actuelle."))
            continue
        except (OSError, ValueError, KeyError) as e:
            QMessageBox.warning(d, d.windowTitle(), str(e))
            continue
        params.enregistrer()
        return True
    return False
