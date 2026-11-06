"""Phrase secrète de la synchronisation des mots de passe et clefs : choisie une fois sur le premier poste, puis
redonnée une fois sur chaque autre poste. Elle reste dans le coffre du système de chaque poste ; elle ne voyage jamais."""
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox

from . import coffre, reglages
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
    p1 = QLineEdit()
    p1.setEchoMode(QLineEdit.Password)
    f.addRow(_("Phrase secrète"), p1)
    p2 = QLineEdit()
    p2.setEchoMode(QLineEdit.Password)
    ind = QLineEdit()
    if nouvelle:
        f.addRow(_("Encore une fois"), p2)
        ind.setPlaceholderText(_("Facultatif, visible sur vos autres postes"))
        f.addRow(_("Indice"), ind)
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
