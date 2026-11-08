"""Panneau « ce qui ne va pas et que faire » (0.9.9), sous un essai de modèle ou une création de l'Atelier IA qui a
échoué : la cause en clair, des boutons qui appliquent la solution (installer Visual C++, passer sur le processeur,
réinstaller le moteur, mettre à jour le pilote), puis on réessaie. Les détails techniques restent repliés."""
import os
import shutil

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout

from . import diagnostic_ia as D
from .langue import _
from .taches import Tache


def genres_moteur(genre):
    """Moteurs (programmes) qu'utilise le modèle actif d'un genre : version processeur et version carte graphique."""
    from . import packs_ia as P
    out = []
    try:
        cle = P.modele_actif(genre)
        m = P.modeles(avec_essai=True).get(cle) or {}
        for g in (P.moteur_du_modele(m), P.moteur_gpu_du_modele(m)):
            if g and g not in out:
                out.append(g)
    except Exception:      # noqa: BLE001
        pass
    return out or [genre]


def reinstaller(genre, progression=None, arret=lambda: False):
    """Retire puis retélécharge les moteurs du genre (le modèle, lui, est gardé)."""
    from . import packs_ia as P
    try:                                       # catalogue à jour : une archive corrigée depuis a une autre empreinte
        P.manifeste(rafraichir=True)
    except Exception:      # noqa: BLE001 : hors ligne, la copie locale sert
        pass
    faits = []
    for g in genres_moteur(genre):
        if not P.moteur_info(g):
            continue
        shutil.rmtree(P.dossier_moteur(g), ignore_errors=True)
        P.installer_moteur(g, progression=progression, arret=arret)
        faits.append(g)
    return faits


class PanneauDiagnostic(QFrame):
    """texte : message d'erreur ; genre : genre du modèle (musique, upscale…) ; reessayer : fonction rappelée après une
    solution appliquée."""

    def __init__(self, parent=None, params=None, reessayer=None):
        super().__init__(parent)
        self.params = params if params is not None else {}
        self.reessayer = reessayer
        self.genre = None
        self.genre_moteur = None
        self.texte = ""
        self.journal = None
        self.tache = None
        self.setObjectName("diagnostic")
        self.setStyleSheet("QFrame#diagnostic{background:#2a1f22;border:1px solid #6b3a40;border-radius:6px}")
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        self.titre = QLabel("")
        self.titre.setWordWrap(True)
        self.titre.setStyleSheet("color:#ff8a80;font-weight:600")
        v.addWidget(self.titre)
        self.explication = QLabel("")
        self.explication.setWordWrap(True)
        self.explication.setStyleSheet("color:#e6e6e6")
        v.addWidget(self.explication)
        self.ligne_actions = QHBoxLayout()
        self.ligne_actions.setSpacing(6)
        v.addLayout(self.ligne_actions)
        self.ligne2 = QHBoxLayout()
        self.b_details = QPushButton(_("Détails techniques"))
        self.b_details.setCheckable(True)
        self.b_details.toggled.connect(lambda on: self.details.setVisible(on))
        self.ligne2.addWidget(self.b_details)
        self.b_journal = QPushButton(_("Voir le journal du moteur"))
        self.b_journal.clicked.connect(self._ouvrir_journal)
        self.ligne2.addWidget(self.b_journal)
        self.b_copier = QPushButton(_("Copier"))
        self.b_copier.setToolTip(_("Copie le message, l'explication et les détails techniques (et la fin du journal du moteur) pour les "
                                   "coller dans un message"))
        self.b_copier.clicked.connect(self._copier)
        self.ligne2.addWidget(self.b_copier)
        self.ligne2.addStretch(1)
        v.addLayout(self.ligne2)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(140)
        self.details.hide()
        v.addWidget(self.details)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:#9aa4b2")
        self.etat.hide()
        v.addWidget(self.etat)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.setMaximumHeight(12)
        self.barre.setTextVisible(False)
        self.barre.hide()
        v.addWidget(self.barre)
        self.hide()

    def _copier(self):
        from PySide6.QtWidgets import QApplication
        txt = "\n".join(x for x in (self.titre.text(), self.explication.text(), self.details.toPlainText()) if x)
        if self.journal and os.path.exists(self.journal):
            try:
                with open(self.journal, encoding="utf-8", errors="replace") as f:
                    txt += "\n\n--- journal du moteur (fin) ---\n" + f.read()[-6000:]
            except OSError:
                pass
        QApplication.clipboard().setText(txt)
        self.b_copier.setText(_("✓ Copié"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1800, lambda: self.b_copier.setText(_("Copier")))

    def montrer(self, texte, genre=None, journal=None, genre_moteur=None, materiel=""):
        """materiel : la carte graphique du poste, pour proposer le bon pilote (Nvidia, AMD, Intel)."""
        self.texte, self.genre, self.journal = str(texte or ""), genre, journal
        self.genre_moteur = genre_moteur
        if not materiel:
            try:
                from . import packs_ia as P
                materiel = P.carte_graphique() or ""
            except Exception:      # noqa: BLE001
                materiel = ""
        d = D.diagnostiquer(self.texte + ("\n" + materiel if materiel else ""), genre_moteur or genre)
        code = f" (code {d['code']:#010x})" if d.get("code") else ""
        self.titre.setText("✕ " + d["titre"] + code)
        self.explication.setText(d["explication"])
        while self.ligne_actions.count():
            it = self.ligne_actions.takeAt(0)
            if it.widget():
                it.widget().hide()
                it.widget().deleteLater()
        for ident, lib in d["actions"]:
            b = QPushButton(lib)
            b.clicked.connect(lambda _c=False, a=ident: self.agir(a))
            self.ligne_actions.addWidget(b)
        self.ligne_actions.addStretch(1)
        self.details.setPlainText(self.texte + (f"\n\n{journal}" if journal else ""))
        self.b_journal.setVisible(bool(journal and os.path.exists(journal)))
        self.etat.hide()
        self.barre.hide()
        self.show()
        return d

    def agir(self, action):
        if D.ouvrir_lien(action):
            msg = {"vcredist": _("Le téléchargement de Visual C++ (Microsoft) s'ouvre dans le navigateur : lancez le fichier, installez, "
                                 "puis cliquez « Réessayer ».")}.get(action, _("La page du pilote s'ouvre dans le navigateur : installez-le, "
                                                                                "redémarrez l'ordinateur si demandé, puis réessayez."))
            self._etat(msg)
            self._bouton_reessayer()
            return
        if action == "reinstaller":
            self._reinstaller()
            return
        if action == "reessayer":
            self._relancer()
            return
        if D.appliquer(action, self.genre_moteur or self.genre, self.params):
            try:
                self.params.enregistrer()
            except AttributeError:
                pass
            self._etat({"processeur": _("C'est noté : ce modèle utilisera le processeur (la version processeur du moteur s'installe au "
                                        "besoin). Nouvel essai…"),
                        "carte": _("C'est noté : la carte graphique sera utilisée. Nouvel essai…"),
                        "carte_dediee": _("Nouvel essai : la carte dédiée sera cherchée…")}.get(action, _("Nouvel essai…")))
            self._relancer()

    def _etat(self, texte):
        self.etat.setText(texte)
        self.etat.show()

    def _bouton_reessayer(self):
        if self.reessayer is None:
            return
        for i in range(self.ligne_actions.count()):
            w = self.ligne_actions.itemAt(i).widget()
            if w is not None and w.property("reessayer"):
                return
        b = QPushButton(_("Réessayer"))
        b.setProperty("reessayer", True)
        b.setStyleSheet("font-weight:600")
        b.clicked.connect(self._relancer)
        self.ligne_actions.insertWidget(0, b)

    def _relancer(self):
        if self.reessayer is not None:
            self.reessayer()

    def _reinstaller(self):
        if self.tache is not None and self.tache.isRunning():
            return
        genre = self.genre
        self._etat(_("Réinstallation du moteur…"))
        self.barre.setValue(0)
        self.barre.show()
        t = Tache(lambda tache: reinstaller(genre, progression=lambda f, *_a: tache.avancer(f, _("Réinstallation du moteur : {p} %",
                                                                                                     p=int(f * 100))),
                                            arret=tache.arret_demande), _("Réinstallation du moteur"))
        self.tache = t
        t.progression.connect(lambda f, x: (self.barre.setValue(int(f * 1000)), x and self.etat.setText(x)), Qt.QueuedConnection)
        t.fini.connect(self._reinstalle, Qt.QueuedConnection)
        t.start()

    def _reinstalle(self, r, err):
        self.barre.hide()
        if err:
            self._etat(_("✕ Réinstallation impossible : {e}", e=str(err)[:300]))
            return
        self._etat(_("Moteur réinstallé. Nouvel essai…"))
        self._relancer()

    def _ouvrir_journal(self):
        if self.journal and os.path.exists(self.journal):
            import pathlib, webbrowser
            webbrowser.open(pathlib.Path(self.journal).resolve().as_uri())
