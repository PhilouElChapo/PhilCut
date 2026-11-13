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
from .taches import texte_erreur


class DialoguePublier(QDialog):
    def __init__(self, parent, projet, params, fichier=""):
        super().__init__(parent)
        self.setWindowTitle(_("Publier"))
        self.resize(640, 600)
        self.projet, self.params = projet, params
        from .taches import ListeTaches
        self.taches = ListeTaches(self)
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
        from . import musiques
        description = pub.get("description") or ""
        for c in musiques.credits_projet(projet):         # crédit obligatoire des musiques sous licence CC BY
            if c not in description:
                description = (description + "\n\n" + c).strip()
        self.desc = QPlainTextEdit(description)
        self.desc.setMaximumHeight(110)
        f.addRow(_("Description"), self.desc)
        self.mots = QLineEdit(", ".join(pub.get("mots_clefs") or []))
        self.mots.setPlaceholderText(_("voyage, vlog, montagne, …"))
        f.addRow(_("Mots-clefs"), self.mots)
        v.addLayout(f)
        gy = QGroupBox(_("YouTube (envoi direct)"))
        fy = QFormLayout(gy)
        self.yt = QCheckBox(_("Envoyer sur ma chaîne YouTube"))
        fy.addRow(self.yt)
        hy = QHBoxLayout()                                  # 0.9.50 : plusieurs chaînes reliées, on choisit la chaîne
        self.etat_yt = QLabel()
        self.chaine = QComboBox()
        self.chaine.setToolTip(_("La chaîne qui reçoit la vidéo"))
        self.chaine.activated.connect(lambda _i: P.choisir_compte(self.chaine.currentData()))
        self.b_relier = QPushButton()
        self.b_relier.clicked.connect(self._relier)
        self.b_delier = QPushButton(_("Délier"))
        self.b_delier.setToolTip(_("Délie la chaîne choisie ; les autres restent reliées"))
        self.b_delier.clicked.connect(self._delier)
        hy.addWidget(self.etat_yt)
        hy.addWidget(self.chaine, 1)
        hy.addWidget(self.b_relier)
        hy.addWidget(self.b_delier)
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
        hv = QHBoxLayout()                                 # 0.9.44 : la vignette de la vidéo, envoyée avec elle
        self.vignette = QLabel()
        self.vignette.setFixedSize(160, 90)
        self.vignette.setAlignment(Qt.AlignCenter)
        self.vignette.setStyleSheet("background:#111;border-radius:4px;color:#999")
        hv.addWidget(self.vignette)
        bv = QPushButton(_("Composer la vignette…"))
        bv.setToolTip(_("L'image qu'on voit sur YouTube avant de cliquer : à partir d'une image du film, avec titre et logo."))
        bv.clicked.connect(self._composer_vignette)
        hv.addWidget(bv)
        hv.addStretch(1)
        fy.addRow(_("Vignette"), hv)
        self._montrer_vignette()
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
        comptes = P.comptes_youtube()
        relie = bool(comptes)
        self.chaine.clear()
        for k, nom in comptes:
            self.chaine.addItem("✓ " + nom, k)
        i = self.chaine.findData(P.compte_actif())
        if i >= 0:
            self.chaine.setCurrentIndex(i)
        self.chaine.setVisible(relie)
        self.b_delier.setVisible(relie)
        self.etat_yt.setText(_("Chaîne :") if relie else _("Compte YouTube pas encore relié"))
        self.b_relier.setText(_("Ajouter une chaîne…") if relie else _("Relier mon compte YouTube…"))
        self.b_relier.setToolTip(_("Relier une autre chaîne (autre compte Google, ou chaîne de marque) : le navigateur demande "
                                   "laquelle") if relie else "")
        self.b_relier.setEnabled(oauth.disponible("youtube"))
        self.yt.setChecked(relie)
        self.b_ok.setEnabled(relie)

    def _delier(self):
        nom = self.chaine.currentText().lstrip("✓ ")
        if QMessageBox.question(self, _("Délier"), _("Délier la chaîne « {n} » de PhilCut ? Les autres restent reliées.", n=nom)) \
                != QMessageBox.Yes:
            return
        P.delier_youtube(self.chaine.currentData())
        self._etat_youtube()

    def _relier(self):
        self.etat.setText(_("Le navigateur s'ouvre : choisissez le compte Google de votre chaîne et acceptez « Gérer vos vidéos YouTube »."))
        t = Tache(lambda tache: P.relier_youtube(arret=lambda: tache.arret), _("YouTube"))
        self.taches.append(t)
        t.fini.connect(self._relie)
        t.start()

    def _relie(self, r, e):
        if e or not r:
            self.etat.setText(_("✕ {e}", e=texte_erreur(e)))
            self._etat_youtube()
            return
        if not r.get("nom_trouve"):                    # YouTube n'a pas donné le nom : on le demande, pour s'y retrouver
            from PySide6.QtWidgets import QInputDialog
            nom, ok = QInputDialog.getText(self, _("Nom de la chaîne"), _("Comment s'appelle cette chaîne ?"), text=r["nom"])
            if ok and nom.strip():
                P.renommer_compte(r["id"], nom)
                r["nom"] = nom.strip()
        self.etat.setText(_("✓ Chaîne « {n} » reliée.", n=r["nom"]))
        self._etat_youtube()

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
        compte = self.chaine.currentData()
        if QMessageBox.question(self, _("Publier sur YouTube"), _("Envoyer « {t} » sur la chaîne « {c} », en « {v} » ?",
                                t=self.titre.text().strip(), c=self.chaine.currentText().lstrip("✓ "),
                                v=self.visi.currentText())) != QMessageBox.Yes:
            return
        self.b_ok.setEnabled(False)
        args = (chemin, self.titre.text().strip(), self.desc.toPlainText().strip(), self._mots(), self.visi.currentData(), self.cat.currentData())
        vignette = self.projet.d.get("vignette_image") or ""

        def travail(tache):
            url = P.envoyer_youtube(*args, progression=lambda f: tache.avancer(f), arret=lambda: tache.arret, compte=compte)
            self._note_vignette = None
            if url and vignette and os.path.exists(vignette):
                tache.avancer(1.0, _("Envoi de la vignette…"))
                self._note_vignette = P.envoyer_vignette(url.rsplit("/", 1)[-1], vignette, compte=compte)
            return url
        t = Tache(travail, _("YouTube"))
        self.taches.append(t)
        t.progression.connect(lambda f, _t: self.etat.setText(_("Envoi sur YouTube : {p} %", p=int(f * 100))))
        t.fini.connect(self._fini)
        t.start()

    def _montrer_vignette(self):
        from PySide6.QtGui import QPixmap
        ch = self.projet.d.get("vignette_image") or ""
        if ch and os.path.exists(ch):
            self.vignette.setPixmap(QPixmap(ch).scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.vignette.setText(_("aucune"))

    def _composer_vignette(self):
        ed = self.parent().editeur_courant() if hasattr(self.parent(), "editeur_courant") else None
        if ed is None:
            return
        ed.vignette_composee("vignette")
        self._montrer_vignette()

    def _fini(self, url, err):
        self.b_ok.setEnabled(True)
        if err:
            self.etat.setText(_("✕ {e}", e=texte_erreur(err)))
            return
        pub = self.projet.d.setdefault("publications", [])
        pub.append({"reseau": "youtube", "url": url, "titre": self.titre.text().strip(), "date": __import__("time").strftime("%Y-%m-%d %H:%M")})
        self.projet.modifie = True
        texte = _("✓ Envoyée : <a href='{u}'>{u}</a> — vérifiez la visibilité dans YouTube Studio.", u=url)
        note = getattr(self, "_note_vignette", None)
        if (self.projet.d.get("vignette_image") or "") and note:
            texte += "<br>" + _("Vignette non envoyée : {r}.", r=note)
        elif self.projet.d.get("vignette_image"):
            texte += "<br>" + _("✓ Vignette envoyée.")
        self.etat.setText(texte)

    def done(self, r):
        for t in self.taches:
            if t.isRunning():
                t.stopper()
                t.wait(5000)
        super().done(r)
