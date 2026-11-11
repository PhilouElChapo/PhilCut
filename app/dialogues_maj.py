"""Fenêtre de mise à jour (0.9.8) : on voit tout de suite que le téléchargement démarre, sa progression (Mo, vitesse,
temps restant), on peut l'arrêter ; à la fin, « Installer et redémarrer ». Fenêtre non bloquante : on peut continuer à
travailler pendant le téléchargement."""
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from . import mise_a_jour
from .langue import _
from .taches import Tache


def _duree(s):
    s = int(max(0, s))
    return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


class DialogueMaj(QDialog):
    def __init__(self, parent, version, paquet):
        super().__init__(parent)
        self.paquet = paquet
        self.fichier = None
        self.setWindowTitle(_("Mise à jour de PhilCut"))
        self.setMinimumWidth(560)
        self.setModal(False)
        # comme PhilPDF (0.9.44) : pas de bouton de réduction de Windows ; « Réduire » range la fenêtre dans la barre du bas,
        # la croix et Echap aussi tant que le téléchargement continue (rien ne s'arrête en cachette)
        self.setWindowFlags((self.windowFlags() | Qt.WindowCloseButtonHint) & ~Qt.WindowMinimizeButtonHint
                            & ~Qt.WindowMaximizeButtonHint & ~Qt.WindowContextHelpButtonHint)
        v = QVBoxLayout(self)
        titre = QLabel(_("Téléchargement de PhilCut {v}", v=version))
        titre.setStyleSheet("font-size:16px;font-weight:600")
        v.addWidget(titre)
        self.detail = QLabel(_("Connexion à GitHub…"))
        self.detail.setWordWrap(True)
        v.addWidget(self.detail)
        self.barre = QProgressBar()
        self.barre.setRange(0, 0)                # animée tant que la taille n'est pas connue
        v.addWidget(self.barre)
        aide = QLabel(_("Vous pouvez continuer à travailler pendant le téléchargement. Rien n'est changé tant que vous n'avez pas cliqué "
                        "« Installer et redémarrer »."))
        aide.setWordWrap(True)
        aide.setStyleSheet("color:#9aa4b2")
        v.addWidget(aide)
        h = QHBoxLayout()
        self.b_reduire = QPushButton(_("Réduire"))
        self.b_reduire.setToolTip(_("La fenêtre se range ; le téléchargement continue et se suit dans la barre du bas. Elle revient d'elle-même "
                                    "quand la mise à jour est prête, ou par « Afficher » dans la barre."))
        self.b_reduire.clicked.connect(self.reduire)
        h.addWidget(self.b_reduire)
        h.addStretch(1)
        self.b_installer = QPushButton(_("Installer et redémarrer"))
        self.b_installer.setStyleSheet("font-weight:600;padding:6px 14px")
        self.b_installer.hide()
        self.b_installer.clicked.connect(self.installer)
        h.addWidget(self.b_installer)
        self.b_arreter = QPushButton(_("Arrêter le téléchargement"))
        self.b_arreter.clicked.connect(self.arreter)
        h.addWidget(self.b_arreter)
        v.addLayout(h)
        self._t0 = time.monotonic()
        self.tache = Tache(lambda t: mise_a_jour.recuperer(paquet, progression=self._progression_fond(t), arret=lambda: t.arret),
                           _("Mise à jour"))
        self.tache.progression.connect(self._progression, Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)

    def _progression_fond(self, t):
        def suivre(fait, total=0):
            self._fait, self._total = fait, total
            t.avancer(fait / total if total else 0.0,
                      _("{f} / {t} Mo", f=round(fait / 1e6), t=round(total / 1e6)) if total else _("{f} Mo reçus", f=round(fait / 1e6)))
        return suivre

    def demarrer(self):
        self.show()
        self.raise_()
        self.tache.start()
        return self.tache

    def _progression(self, f, texte):
        fait, total = getattr(self, "_fait", 0), getattr(self, "_total", 0)
        ecoule = max(0.1, time.monotonic() - self._t0)
        vitesse = fait / ecoule
        if total:
            self.barre.setRange(0, 1000)
            self.barre.setValue(int(fait / total * 1000))
            if ecoule < 3 and fait < 20e6:               # pas d'estimation fantaisiste dans les premières secondes
                self.detail.setText(_("{f} / {t} Mo · mesure de la vitesse…", f=round(fait / 1e6), t=round(total / 1e6)))
                return
            reste = (total - fait) / vitesse if vitesse > 0 else 0
            self.detail.setText(_("{f} / {t} Mo · {v:.1f} Mo/s · encore environ {r}", f=round(fait / 1e6), t=round(total / 1e6),
                                  v=vitesse / 1e6, r=_duree(reste)))
        else:
            self.detail.setText(_("{f} Mo reçus · {v:.1f} Mo/s", f=round(fait / 1e6), v=vitesse / 1e6))

    def _fini(self, fichier, erreur):
        self.barre.setRange(0, 1000)
        if erreur or not fichier:
            self.barre.setValue(0)
            arrete = "annule" in str(erreur or "")
            self.detail.setText(_("Téléchargement arrêté.") if arrete else
                                _("✕ Le téléchargement n'a pas abouti : {e}. Réessayez, ou téléchargez la nouvelle version à la main sur GitHub "
                                  "(Aide › Rechercher une mise à jour).", e=str(erreur or _("fichier vide"))[:200]))
            self.b_arreter.setText(_("Fermer"))
            return
        if not mise_a_jour.fichier_valide(fichier):
            self.detail.setText(_("Le fichier téléchargé n'est pas valide : rien n'a été changé."))
            self.b_arreter.setText(_("Fermer"))
            return
        self.fichier = fichier
        self.barre.setValue(1000)
        self.detail.setText(_("✓ Mise à jour téléchargée en {d}. Enregistrez vos projets, puis « Installer et redémarrer ».",
                              d=_duree(time.monotonic() - self._t0)))
        self.b_installer.show()
        self.b_reduire.hide()
        self.b_arreter.setText(_("Plus tard"))
        self.show()
        self.raise_()

    def arreter(self):
        if self.tache.isRunning():
            self.tache.arret = True
            self.detail.setText(_("Arrêt du téléchargement…"))
        else:
            self.close()

    def reduire(self):
        """Rangée dans la barre du bas (« Afficher » la rouvre) ; le téléchargement continue."""
        self.hide()
        p = self.parent()
        if p is not None and hasattr(p, "statusBar"):
            try:
                p.statusBar().showMessage(_("Mise à jour : le téléchargement continue (barre du bas, « Afficher » pour revoir la fenêtre)."), 6000)
            except RuntimeError:
                pass

    def closeEvent(self, e):
        if self.tache.isRunning():                      # la croix range la fenêtre, le téléchargement continue
            e.ignore()
            self.reduire()
            return
        super().closeEvent(e)

    def reject(self):                                   # Echap : pareil que la croix
        if self.tache.isRunning():
            self.reduire()
            return
        super().reject()

    def installer(self):
        """Ferme PhilCut proprement (questions d'enregistrement, arrêt des tâches et du son), lance l'installation, qui
        attend la fin de PhilCut avant de remplacer ses fichiers, puis le relance."""
        if not self.fichier:
            return
        p = self.parent()
        self.hide()
        if p is not None and hasattr(p, "quitter_pour_maj"):
            if not p.quitter_pour_maj(lambda: mise_a_jour.appliquer(self.fichier)):
                self.show()
            return
        mise_a_jour.appliquer(self.fichier)
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
