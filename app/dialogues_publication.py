"""Publier : YouTube en direct (compte relié une fois), Instagram, TikTok, Facebook en publication assistée.
Titre, description et mots-clefs repris de la recette de l'assistant, modifiables ; rien ne part sans le clic final."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QVBoxLayout, QLineEdit, QPlainTextEdit, QPushButton, QComboBox, QLabel,
                               QCheckBox, QFileDialog, QMessageBox, QDialogButtonBox, QGroupBox)

from . import publication as P
from .langue import _
from .taches import Tache
from .widgets import boutons_fr


class DialoguePublier(QDialog):
    def __init__(self, parent, projet, params, fichier=""):
        super().__init__(parent)
        self.setWindowTitle(_("Publier"))
        self.resize(640, 600)
        self.projet, self.params = projet, params
        self.taches = []
        pub = (projet.d.get("recette") or {}).get("publication") or {}
        v = QVBoxLayout(self)
        f = QFormLayout()
        h = QHBoxLayout()
        self.fichier = QLineEdit(fichier or projet.d.get("dernier_export") or "")
        b = QPushButton(_("Parcourir…"))
        b.clicked.connect(self._parcourir)
        h.addWidget(self.fichier, 1)
        h.addWidget(b)
        f.addRow(_("Vidéo"), h)
        self.titre = QLineEdit(pub.get("titre") or projet.nom or "")
        self.titre.setMaxLength(100)
        f.addRow(_("Titre"), self.titre)
        self.desc = QPlainTextEdit(pub.get("description") or "")
        self.desc.setMaximumHeight(110)
        f.addRow(_("Description"), self.desc)
        self.mots = QLineEdit(", ".join(pub.get("mots_clefs") or []))
        self.mots.setPlaceholderText(_("aviation, Cannes, vol, …"))
        f.addRow(_("Mots-clefs"), self.mots)
        v.addLayout(f)
        gy = QGroupBox(_("YouTube (envoi direct)"))
        fy = QFormLayout(gy)
        self.yt = QCheckBox(_("Envoyer sur ma chaîne YouTube"))
        fy.addRow(self.yt)
        hy = QHBoxLayout()
        self.etat_yt = QLabel()
        self.b_relier = QPushButton()
        self.b_relier.clicked.connect(self._relier)
        hy.addWidget(self.etat_yt, 1)
        hy.addWidget(self.b_relier)
        fy.addRow(hy)
        self.visi = QComboBox()
        for k, lib in P.VISIBILITES:
            self.visi.addItem(lib, k)
        fy.addRow(_("Visibilité"), self.visi)
        self.cat = QComboBox()
        for k, lib in (("19", _("Voyages et événements")), ("22", _("Vlog, personnes")), ("2", _("Auto et véhicules")),
                       ("24", _("Divertissement")), ("28", _("Science et technologie"))):
            self.cat.addItem(lib, k)
        fy.addRow(_("Catégorie"), self.cat)
        note = QLabel(_("<span style='color:#999'>Tant que PhilCut n'a pas passé l'audit YouTube de Google, la vidéo arrive en « privé » : "
                        "passez-la en public d'un clic dans YouTube Studio.</span>"))
        note.setWordWrap(True)
        fy.addRow(note)
        v.addWidget(gy)
        ga = QGroupBox(_("Autres réseaux (publication assistée)"))
        la = QVBoxLayout(ga)
        lab = QLabel(_("PhilCut copie la légende (titre, description, #mots-clefs), ouvre la page d'envoi du réseau et le dossier de la "
                       "vidéo : il reste à glisser le fichier et coller la légende. Prenez la version verticale (double export) pour Instagram et TikTok."))
        lab.setWordWrap(True)
        la.addWidget(lab)
        hr = QHBoxLayout()
        for k in ("instagram", "tiktok", "facebook"):
            b = QPushButton(P.RESEAUX[k]["nom"])
            b.clicked.connect(lambda _c=False, k=k: self._assiste(k))
            hr.addWidget(b)
        la.addLayout(hr)
        v.addWidget(ga)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.etat.setOpenExternalLinks(True)
        v.addWidget(self.etat)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close))
        self.b_ok = bb.button(QDialogButtonBox.Ok)
        self.b_ok.setText(_("Publier sur YouTube"))
        self.b_ok.clicked.connect(self._publier)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._etat_youtube()

    def _mots(self):
        return [m.strip() for m in self.mots.text().replace(";", ",").split(",") if m.strip()]

    def _parcourir(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Vidéo à publier"), os.path.dirname(self.fichier.text()), "MP4 (*.mp4)")
        if p:
            self.fichier.setText(p)

    def _etat_youtube(self):
        from . import oauth
        relie = P.youtube_relie()
        self.etat_yt.setText(_("✓ Compte YouTube relié") if relie else _("Compte YouTube pas encore relié"))
        self.b_relier.setText(_("Délier") if relie else _("Relier mon compte YouTube…"))
        self.b_relier.setEnabled(oauth.disponible("youtube"))
        self.yt.setChecked(relie)
        self.b_ok.setEnabled(relie)

    def _relier(self):
        if P.youtube_relie():
            P.delier_youtube()
            self._etat_youtube()
            return
        self.etat.setText(_("Le navigateur s'ouvre : choisissez le compte Google de votre chaîne et acceptez « Gérer vos vidéos YouTube »."))
        t = Tache(lambda tache: P.relier_youtube(arret=lambda: tache.arret), _("YouTube"))
        self.taches.append(t)
        t.fini.connect(lambda r, e: (self.etat.setText(_("✕ {e}", e=e) if e else _("✓ Compte relié.")), self._etat_youtube()))
        t.start()

    def _assiste(self, reseau):
        chemin = self.fichier.text().strip()
        if not os.path.exists(chemin):
            QMessageBox.information(self, _("Publier"), _("Choisissez d'abord la vidéo exportée."))
            return
        P.preparer_assistee(reseau, chemin, self.titre.text().strip(), self.desc.toPlainText().strip(), self._mots())
        self.etat.setText(_("Légende copiée. Sur {r} : nouvelle publication, glissez « {f} », collez la légende (Ctrl+V).",
                            r=P.RESEAUX[reseau]["nom"], f=os.path.basename(chemin)))

    def _publier(self):
        chemin = self.fichier.text().strip()
        if not self.yt.isChecked():
            return
        if not os.path.exists(chemin):
            QMessageBox.information(self, _("Publier"), _("Choisissez d'abord la vidéo exportée."))
            return
        if QMessageBox.question(self, _("Publier sur YouTube"), _("Envoyer « {t} » sur votre chaîne, en « {v} » ?",
                                t=self.titre.text().strip(), v=self.visi.currentText())) != QMessageBox.Yes:
            return
        self.b_ok.setEnabled(False)
        args = (chemin, self.titre.text().strip(), self.desc.toPlainText().strip(), self._mots(), self.visi.currentData(), self.cat.currentData())
        t = Tache(lambda tache: P.envoyer_youtube(*args, progression=lambda f: tache.avancer(f), arret=lambda: tache.arret), _("YouTube"))
        self.taches.append(t)
        t.progression.connect(lambda f, _t: self.etat.setText(_("Envoi sur YouTube : {p} %", p=int(f * 100))))
        t.fini.connect(self._fini)
        t.start()

    def _fini(self, url, err):
        self.b_ok.setEnabled(True)
        if err:
            self.etat.setText(_("✕ {e}", e=err))
            return
        pub = self.projet.d.setdefault("publications", [])
        pub.append({"reseau": "youtube", "url": url, "titre": self.titre.text().strip(), "date": __import__("time").strftime("%Y-%m-%d %H:%M")})
        self.projet.modifie = True
        self.etat.setText(_("✓ Envoyée : <a href='{u}'>{u}</a> — vérifiez la visibilité dans YouTube Studio.", u=url))

    def done(self, r):
        for t in self.taches:
            if t.isRunning():
                t.stopper()
                t.wait(5000)
        super().done(r)
