"""Consigne bilingue (0.9.61, règle de Philippe) : quand un prompt doit être en anglais (les moteurs d'IA ne comprennent
bien que l'anglais), on l'écrit dans la langue du système, PhilCut le traduit, et on voit les deux : la traduction
reste modifiable pour l'améliorer. Une consigne rédigée par l'IA (en anglais) est traduite dans l'autre sens pour
qu'on la lise dans sa langue.

ConsigneBilingue se pose à la place d'un QPlainTextEdit : toPlainText() / setPlainText() / textChanged parlent de
l'anglais (ce qui part au moteur) ; la langue du système est dans .source. Les traductions se font en arrière-plan
(jamais d'attente à la frappe) ; le résultat est relevé par un minuteur (aucun signal Qt depuis un fil)."""
import queue, threading

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from . import langue as L
from .langue import _

DELAI_FRAPPE = 900          # ms sans frappe avant de traduire


def langue_systeme():
    return (L.LANGUE or "fr")[:2]


def vers_anglais(texte):
    """(anglais, mots restés intraduits)."""
    from . import traduction_recherche as TR
    en, _comment, manque = TR.phrase_en_anglais(texte)
    return en, manque


def depuis_anglais(texte, langue=None):
    """Traduction d'une consigne anglaise dans la langue du système (même service que l'autre sens) ; '' si impossible."""
    import json, os, urllib.parse, urllib.request
    from . import traduction_recherche as TR
    langue = (langue or langue_systeme())[:2]
    texte = (texte or "").strip()
    if not texte or langue == "en" or os.environ.get("PHILCUT_SANS_RESEAU"):
        return texte if langue == "en" else ""
    sortie = []
    import re
    morceaux, cour = [], ""
    for bout in re.split(r"(?<=[.;,!?\n])\s*", texte):
        if cour and len(cour) + len(bout) + 1 > 380:
            morceaux.append(cour)
            cour = ""
        cour = (cour + " " + bout).strip()
    if cour:
        morceaux.append(cour)
    for m in morceaux:
        try:
            url = TR.API + "?" + urllib.parse.urlencode({"q": m[:400], "langpair": f"en|{langue}", "mt": "1"})
            with urllib.request.urlopen(urllib.request.Request(url, headers=TR._agent()), timeout=6) as r:
                d = json.loads(r.read().decode("utf-8"))
            t = ((d or {}).get("responseData") or {}).get("translatedText") or ""
        except Exception:      # noqa: BLE001 : hors ligne
            return ""
        sortie.append(t)
    return " ".join(sortie).strip()


class ConsigneBilingue(QWidget):
    textChanged = Signal()          # l'anglais a changé (ce qui part au moteur)

    def __init__(self, hauteur=70, exemple="", parent=None):
        super().__init__(parent)
        self._file, self._num, self._retouche, self._silence = queue.Queue(), 0, False, False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        self.lbl_source = QLabel(_("Dans votre langue :"))
        v.addWidget(self.lbl_source)
        self.source = QPlainTextEdit()
        self.source.setFixedHeight(hauteur)
        if exemple:
            self.source.setPlaceholderText(exemple)
        v.addWidget(self.source)
        self.lbl_anglais = QLabel(_("En anglais, envoyé au moteur (corrigez la traduction si besoin) :"))
        self.lbl_anglais.setWordWrap(True)
        v.addWidget(self.lbl_anglais)
        self.anglais = QPlainTextEdit()
        self.anglais.setFixedHeight(hauteur)
        v.addWidget(self.anglais)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.etat)
        self._minuteur = QTimer(self)
        self._minuteur.setSingleShot(True)
        self._minuteur.timeout.connect(self._traduire)
        self._releve = QTimer(self)
        self._releve.setInterval(150)
        self._releve.timeout.connect(self._relever)
        self.source.textChanged.connect(self._source_change)
        self.anglais.textChanged.connect(self._anglais_change)
        if langue_systeme() == "en":                       # PhilCut en anglais : une seule case
            for w in (self.lbl_source, self.source, self.lbl_anglais):
                w.hide()

    # ---- compatibilité QPlainTextEdit (l'anglais)
    def toPlainText(self):
        return self.anglais.toPlainText()

    def setPlainText(self, texte, source=None):
        """Consigne anglaise posée par PhilCut ou l'IA : traduite dans la langue du système pour être lue (sauf si
        source est donnée)."""
        self._silence = True
        self.anglais.setPlainText(texte or "")
        self._retouche = False
        self._silence = False
        self._num += 1
        if source is not None or langue_systeme() == "en":
            self._poser_source(source or "")
            self.etat.setText("")
        elif (texte or "").strip():
            self._poser_source("")
            self.etat.setText(_("Traduction dans votre langue…"))
            self._lancer("depuis", texte, self._num)
        else:
            self._poser_source("")
        self.textChanged.emit()

    def setPlaceholderText(self, texte):
        self.source.setPlaceholderText(texte)

    def setMaximumHeight(self, h):
        self.source.setFixedHeight(min(self.source.height(), h))
        self.anglais.setFixedHeight(min(self.anglais.height(), h))

    def setFixedHeight(self, h):                           # hauteur d'UNE case (comme l'ancien champ)
        self.source.setFixedHeight(h)
        self.anglais.setFixedHeight(h)

    def setAcceptRichText(self, _oui):
        pass

    def texte_source(self):
        return self.source.toPlainText()

    # ---- traductions
    def _poser_source(self, texte):
        self.source.blockSignals(True)
        self.source.setPlainText(texte)
        self.source.blockSignals(False)

    def _source_change(self):
        self._num += 1
        self.etat.setText(_("Traduction en anglais…") if self.source.toPlainText().strip() else "")
        self._minuteur.start(DELAI_FRAPPE)

    def _anglais_change(self):
        if self._silence:
            return
        self._retouche = True
        self._num += 1                                     # une traduction en route ne l'écrase plus
        self.etat.setText(_("Traduction corrigée à la main : c'est elle qui part au moteur."))
        self.textChanged.emit()

    def _traduire(self):
        t = self.source.toPlainText().strip()
        if not t:
            self._silence = True
            self.anglais.setPlainText("")
            self._silence = False
            self.textChanged.emit()
            return
        self._lancer("vers", t, self._num)

    def _lancer(self, sens, texte, num):
        f = self._file

        def fil():
            try:
                r = vers_anglais(texte) if sens == "vers" else (depuis_anglais(texte), [])
            except Exception:      # noqa: BLE001
                r = ("", [])
            f.put((sens, num, r))
        threading.Thread(target=fil, daemon=True).start()
        self._releve.start()

    def _relever(self):
        try:
            sens, num, (texte, manque) = self._file.get_nowait()
        except queue.Empty:
            return
        if self._file.empty():
            self._releve.stop()
        if num != self._num:                               # dépassée par une frappe ou une correction
            return
        if sens == "vers":
            self._silence = True
            self.anglais.setPlainText(texte)
            self._silence = False
            self._retouche = False
            self.etat.setText(_("Pas de traduction pour « {m} » : écrivez ces mots en anglais ci-dessous.", m=", ".join(manque))
                              if manque else _("✓ Traduit en anglais."))
            self.textChanged.emit()
        else:
            self._poser_source(texte)
            self.etat.setText("" if texte else _("Traduction dans votre langue impossible (pas de réseau ?) : la consigne anglaise "
                                                 "reste utilisable."))

    def attendre(self, secondes=10):
        """Pour les tests : laisse finir les traductions en cours."""
        import time
        from PySide6.QtWidgets import QApplication
        t0 = time.time()
        while time.time() - t0 < secondes and (self._minuteur.isActive() or self._releve.isActive()):
            QApplication.processEvents()
            time.sleep(0.02)


class AnglaisEnDirect(QWidget):
    """Sous un champ déjà écrit dans la langue du système (Fabrique) : l'anglais qui partira au moteur, traduit en
    direct et modifiable. calcul(texte) -> (anglais, mots intraduits) tourne en arrière-plan. retouche() dit si
    l'utilisateur a corrigé la traduction : c'est alors elle qui part."""

    def __init__(self, champ, calcul, parent=None):
        super().__init__(parent)
        self.champ, self.calcul = champ, calcul
        self._file, self._num, self._retouche, self._silence = queue.Queue(), 0, False, False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        self.lbl = QLabel(_("En anglais, envoyé au moteur (corrigez la traduction si besoin) :"))
        self.lbl.setWordWrap(True)
        v.addWidget(self.lbl)
        self.anglais = QPlainTextEdit()
        self.anglais.setFixedHeight(50)
        v.addWidget(self.anglais)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.etat)
        self._minuteur = QTimer(self)
        self._minuteur.setSingleShot(True)
        self._minuteur.timeout.connect(self._traduire)
        self._releve = QTimer(self)
        self._releve.setInterval(150)
        self._releve.timeout.connect(self._relever)
        champ.textChanged.connect(self.relancer)
        self.anglais.textChanged.connect(self._corrige)

    def relancer(self):
        self._num += 1
        self._retouche = False
        self.etat.setText(_("Traduction en anglais…") if self.champ.toPlainText().strip() else "")
        self._minuteur.start(DELAI_FRAPPE)

    def retouche(self):
        return self._retouche and bool(self.anglais.toPlainText().strip())

    def texte(self):
        return self.anglais.toPlainText().strip()

    def _corrige(self):
        if self._silence:
            return
        self._retouche = True
        self._num += 1
        self.etat.setText(_("Traduction corrigée à la main : c'est elle qui part au moteur."))

    def _traduire(self):
        t = self.champ.toPlainText().strip()
        if not t:
            self._poser("")
            return
        num, f, calcul = self._num, self._file, self.calcul

        def fil():
            try:
                r = calcul(t)
            except Exception:      # noqa: BLE001
                r = ("", [])
            f.put((num, r))
        threading.Thread(target=fil, daemon=True).start()
        self._releve.start()

    def _poser(self, texte):
        self._silence = True
        self.anglais.setPlainText(texte)
        self._silence = False

    def _relever(self):
        try:
            num, (texte, manque) = self._file.get_nowait()
        except queue.Empty:
            return
        if self._file.empty():
            self._releve.stop()
        if num != self._num:
            return
        self._poser(texte)
        self.etat.setText(_("Pas de traduction pour « {m} » : écrivez ces mots en anglais ci-dessus.", m=", ".join(manque))
                          if manque else (_("✓ Traduit en anglais.") if texte else ""))

    def attendre(self, secondes=10):
        import time
        from PySide6.QtWidgets import QApplication
        t0 = time.time()
        while time.time() - t0 < secondes and (self._minuteur.isActive() or self._releve.isActive()):
            QApplication.processEvents()
            time.sleep(0.02)
