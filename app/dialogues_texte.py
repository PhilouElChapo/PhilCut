"""Fenêtre « Monter par le texte » (0.9.23) : le texte de ce qui est dit, dans l'ordre du montage. Sélectionner des mots
puis « Couper » (ou la touche Suppr) enlève ce passage de la vidéo ; un clic sur un mot y amène la ligne rouge ; pendant
la lecture, le mot entendu est surligné."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QCheckBox, QDialog, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QTextEdit,
                               QVBoxLayout)

from . import montage_texte as MT
from .langue import _
from .taches import Tache
from .taches import texte_erreur


class DialogueMontageTexte(QDialog):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed = ed
        self.setWindowTitle(_("Monter par le texte"))
        self.resize(760, 620)
        self.mots, self.positions, self.tache = [], [], None
        v = QVBoxLayout(self)
        intro = QLabel(_("Le texte de ce qui est dit, dans l'ordre du montage. Sélectionnez des mots puis « Couper ce passage » "
                         "(ou Suppr) : la vidéo est coupée et la suite se recolle. Un clic sur un mot y amène la ligne rouge. "
                         "Ctrl+Z annule."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        h0 = QHBoxLayout()
        self.b_transcrire = QPushButton(_("Transcrire les rushes (sur ce poste)"))
        self.b_transcrire.clicked.connect(self.transcrire)
        h0.addWidget(self.b_transcrire)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        h0.addWidget(self.barre, 1)
        v.addLayout(h0)
        hc = QHBoxLayout()
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(_("Chercher un mot dans le texte…"))
        self.cherche.returnPressed.connect(self.chercher)
        hc.addWidget(self.cherche, 1)
        bc = QPushButton(_("Chercher"))
        bc.clicked.connect(self.chercher)
        hc.addWidget(bc)
        v.addLayout(hc)
        self.texte = QTextEdit()
        self.texte.setReadOnly(True)
        self.texte.setStyleSheet("QTextEdit{font-size:15px;line-height:150%}")
        self.texte.cursorPositionChanged.connect(self._clic)
        v.addWidget(self.texte, 1)
        h1 = QHBoxLayout()
        self.b_couper = QPushButton(_("✂ Couper ce passage"))
        self.b_couper.setToolTip(_("Enlève de la vidéo les mots sélectionnés (touche Suppr)"))
        self.b_couper.clicked.connect(self.couper_selection)
        h1.addWidget(self.b_couper)
        self.b_garder = QPushButton(_("Garder seulement ce passage"))
        self.b_garder.clicked.connect(self.garder_selection)
        h1.addWidget(self.b_garder)
        h1.addStretch(1)
        self.b_annuler = QPushButton(_("↶ Annuler"))
        self.b_annuler.clicked.connect(self.annuler)
        h1.addWidget(self.b_annuler)
        v.addLayout(h1)
        h2 = QHBoxLayout()
        self.b_euh = QPushButton(_("Retirer les « euh »"))
        self.b_euh.clicked.connect(self.retirer_euh)
        h2.addWidget(self.b_euh)
        self.b_silences = QPushButton(_("Retirer les silences de plus de"))
        self.b_silences.clicked.connect(self.retirer_silences)
        h2.addWidget(self.b_silences)
        self.seuil = QDoubleSpinBox()
        self.seuil.setRange(0.3, 5.0)
        self.seuil.setSingleStep(0.1)
        self.seuil.setSuffix(" s")
        self.seuil.setValue(float(ed.params.get("texte_seuil_silence", 0.8)))
        self.seuil.valueChanged.connect(self._maj_boutons)
        h2.addWidget(self.seuil)
        h2.addStretch(1)
        v.addLayout(h2)
        self.musique_continue = QCheckBox(_("La musique continue sous les coupes (les pistes de musique ne sont pas coupées)"))
        self.musique_continue.setChecked(bool(ed.params.get("texte_musique_continue", True)))
        v.addWidget(self.musique_continue)
        QShortcut(QKeySequence.Delete, self, self.couper_selection)
        QShortcut(QKeySequence("Backspace"), self, self.couper_selection)
        QShortcut(QKeySequence.Undo, self, self.annuler)
        self._suivi = QTimer(self)
        self._suivi.timeout.connect(self._surligner_lecture)
        self._suivi.start(200)
        self._dernier = -1
        self.remplir()

    # ---- texte
    def remplir(self):
        self.mots = MT.mots_du_montage(self.ed.projet)
        reste = MT.rushes_a_transcrire(self.ed.projet)
        paras = MT.paragraphes(self.mots)
        self.positions = []
        morceaux, pos = [], 0
        for i, x in enumerate(self.mots):
            sep = "" if i == 0 else ("\n\n" if i in paras else " ")
            morceaux.append(sep)
            pos += len(sep)
            self.positions.append((pos, pos + len(x["mot"])))
            morceaux.append(x["mot"])
            pos += len(x["mot"])
        self.texte.blockSignals(True)
        self.texte.setPlainText("".join(morceaux))
        self.texte.blockSignals(False)
        if reste:
            self.etat.setText(_("{n} rush(es) pas encore transcrit(s) : « Transcrire les rushes » (une seule fois, gardé dans le projet).",
                                n=len(reste)))
            self.b_transcrire.show()
        elif not self.mots:
            self.etat.setText(_("Aucune parole dans les plans de la piste Vidéo 1 (ou rushes sans son)."))
            self.b_transcrire.hide()
        else:
            self.etat.setText(_("{n} mots, {d} de montage.", n=len(self.mots), d=_duree(self.ed.projet.duree())))
            self.b_transcrire.hide()
        self._maj_boutons()

    def _maj_boutons(self, *_a):
        n = len(MT.hesitations(self.mots))
        self.b_euh.setText(_("Retirer les « euh » ({n})", n=n))
        self.b_euh.setEnabled(n > 0)
        s = MT.silences(self.mots, self.ed.projet, self.seuil.value())
        self.b_silences.setText(_("Retirer les {n} silence(s) de plus de", n=len(s)))
        self.b_silences.setEnabled(bool(s))
        ok = bool(self.mots)
        self.b_couper.setEnabled(ok)
        self.b_garder.setEnabled(ok)

    def _rang(self, pos):
        for i, (a, b) in enumerate(self.positions):
            if pos <= b:
                return i if pos >= a or i == 0 else i
        return len(self.positions) - 1 if self.positions else -1

    def selection(self):
        c = self.texte.textCursor()
        if not c.hasSelection() or not self.mots:
            return None
        i, j = self._rang(c.selectionStart()), self._rang(max(c.selectionStart(), c.selectionEnd() - 1))
        return (i, j) if i >= 0 and j >= 0 else None

    def _clic(self):
        c = self.texte.textCursor()
        if c.hasSelection() or not self.mots:
            return
        i = self._rang(c.position())
        if 0 <= i < len(self.mots):
            self.ed.aller_a(self.mots[i]["t0"])

    def _surligner(self, i, couleur):
        sel = QTextEdit.ExtraSelection()
        a, b = self.positions[i]
        cur = self.texte.textCursor()
        cur.setPosition(a)
        cur.setPosition(b, QTextCursor.KeepAnchor)
        sel.cursor = cur
        f = QTextCharFormat()
        f.setBackground(QColor(couleur))
        f.setForeground(QColor("#111111"))
        sel.format = f
        return sel

    def _surligner_lecture(self):
        if not self.mots or not self.isVisible():
            return
        t = self.ed.timeline.position
        i = next((k for k, x in enumerate(self.mots) if x["t0"] <= t < x["t1"] + 0.1), -1)
        if i == self._dernier:
            return
        self._dernier = i
        self.texte.setExtraSelections([self._surligner(i, "#ffd60a")] if i >= 0 else [])

    def chercher(self):
        mot = self.cherche.text().strip().lower()
        if not mot:
            return
        depart = self._dernier + 1 if self._dernier >= 0 else 0
        ordre = list(range(depart, len(self.mots))) + list(range(0, depart))
        for i in ordre:
            if mot in self.mots[i]["mot"].lower():
                a, b = self.positions[i]
                cur = self.texte.textCursor()
                cur.setPosition(a)
                cur.setPosition(b, QTextCursor.KeepAnchor)
                self.texte.setTextCursor(cur)
                self.ed.aller_a(self.mots[i]["t0"])
                self._dernier = i
                return
        self.etat.setText(_("« {m} » n'est pas dans le texte.", m=mot))

    # ---- coupes
    def _sauf(self):
        self.ed.params["texte_musique_continue"] = self.musique_continue.isChecked()
        return tuple(self.ed.projet.pistes_audio()) if self.musique_continue.isChecked() else ()

    def _appliquer(self, plages, quoi):
        if not plages:
            return 0.0
        self.ed.projet.marquer()
        enleve = MT.couper(self.ed.projet, plages, self._sauf())
        self.ed.rafraichir()
        self.remplir()
        self.etat.setText(_("{q} : {d} en moins. Ctrl+Z annule.", q=quoi, d=_duree(enleve)))
        return enleve

    def couper_selection(self):
        s = self.selection()
        if not s:
            self.etat.setText(_("Sélectionnez d'abord des mots à la souris."))
            return 0.0
        return self._appliquer([MT.plage(self.mots, *s)], _("Passage coupé"))

    def garder_selection(self):
        s = self.selection()
        if not s:
            self.etat.setText(_("Sélectionnez d'abord des mots à la souris."))
            return
        a, b = MT.plage(self.mots, *s)
        self.ed.projet.marquer()
        self.ed.projet.partie(a, b, True, sauf=self._sauf())
        self.ed.rafraichir()
        self.remplir()

    def retirer_euh(self):
        return self._appliquer([MT.plage(self.mots, i, i) for i in MT.hesitations(self.mots)], _("Hésitations retirées"))

    def retirer_silences(self):
        self.ed.params["texte_seuil_silence"] = self.seuil.value()
        return self._appliquer(MT.silences(self.mots, self.ed.projet, self.seuil.value()), _("Silences retirés"))

    def annuler(self):
        self.ed.annuler()
        self.remplir()

    # ---- transcription
    def transcrire(self):
        from . import sous_titres as ST
        if not ST.disponible():
            self.etat.setText(_("Aucun modèle de voix sur ce poste : installez-en un dans Préférences › IA locale (« Voix vers texte »)."))
            return
        projet, params = self.ed.projet, self.ed.params
        self.b_transcrire.setEnabled(False)
        self.barre.setValue(0)
        self.barre.show()
        self.tache = Tache(lambda t: MT.transcrire(projet, params, progression=t.avancer, arret=t.arret_demande), _("Transcription"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("Transcription des rushes pour le montage par le texte"))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)),
                                                       self.etat.setText(_("Transcription : {t}", t=txt) if txt else self.etat.text())),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(self._transcrit, Qt.QueuedConnection)
        self.tache.start()

    def _transcrit(self, r, err):
        try:
            self.b_transcrire.setEnabled(True)
            self.barre.hide()
            if err:
                self.etat.setText(_("✕ Transcription impossible : {e}", e=texte_erreur(err)[:300]))
                return
            self.remplir()
        except RuntimeError:
            pass

    def done(self, r):
        self._suivi.stop()
        super().done(r)


def _duree(s):
    s = max(0.0, float(s or 0))
    return f"{int(s // 60)} min {s % 60:04.1f} s" if s >= 60 else f"{s:.1f} s"
