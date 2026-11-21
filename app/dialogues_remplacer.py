"""1.0.5 : fenêtre « Remplacer un élément de l'image par un de ma bibliothèque » (non bloquante, une par plan)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QProgressBar, QPushButton, QRadioButton, QVBoxLayout, QWidget)

from . import remplacer_element as R
from .langue import _
from .taches import Tache, texte_erreur


class DialogueRemplacer(QDialog):
    def __init__(self, ed, clip):
        super().__init__(ed)
        from .cartes_assistant import ImageCadres
        from .credit_ia import LigneCredit
        self.ed, self.clip, self.params = ed, clip, ed.params
        self.zone, self.resultat, self.tache = None, "", None
        self.setWindowTitle(_("Remplacer un élément de l'image par un de ma bibliothèque"))
        self.source = self._image_source()
        v = QVBoxLayout(self)
        aide = QLabel(_("Dites ce qui doit disparaître et choisissez dans votre bibliothèque ce qui le remplace. Le reste de "
                        "l'image (personnes, décor, lumière) ne change pas. Une relecture par l'IA compare ensuite avant, après "
                        "et la fiche ; vous regardez le résultat avant de le poser."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        h = QHBoxLayout()
        gauche = QVBoxLayout()
        self.image = ImageCadres(self.source, 440)
        self.image.trace.connect(self._zone)
        gauche.addWidget(self.image)
        # le résultat prend la place de l'image (la fenêtre tient en 1024×768) ; clic = avant / après
        self.apres = QLabel()
        self.apres.setToolTip(_("Cliquez pour voir l'image d'avant, recliquez pour revenir au résultat"))
        self.apres.mousePressEvent = lambda _e: self._basculer()
        self.apres.hide()
        gauche.addWidget(self.apres)
        self.b_cadre = QPushButton(_("Retracer le cadre"))
        self.b_cadre.clicked.connect(self._retracer)
        self.b_cadre.hide()
        gauche.addWidget(self.b_cadre)
        self.l_zone = QLabel(_("Tracez le cadre de ce qui doit disparaître (prenez-le entier, avec un peu de marge)."))
        self.l_zone.setWordWrap(True)
        gauche.addWidget(self.l_zone)
        gauche.addStretch(1)
        h.addLayout(gauche)
        droite = QVBoxLayout()
        # 1.0.9 : les deux façons de faire (Philippe, 21/11)
        self.modes = QButtonGroup(self)
        for i, (cle, lib) in enumerate(R.MODES.items()):
            r = QRadioButton(lib + (_(" ★ conseillé") if cle == "auto" else ""))
            r.setProperty("mode", cle)
            r.setChecked(cle == "auto")
            self.modes.addButton(r, i)
            droite.addWidget(r)
        self.modes.buttonToggled.connect(lambda *_a: self._mode_change())
        f = QFormLayout()
        self.quoi = QLineEdit()
        self.quoi.setPlaceholderText(_("ex. : la voiture rouge, le panneau, l'avion blanc"))
        f.addRow(_("Ce qui disparaît"), self.quoi)
        self.choix = QComboBox()
        self.choix.setIconSize(QPixmap(48, 48).size())
        for e in R.entrees(self.params):
            from . import bibliotheque_creations as B
            self.choix.addItem(QIcon(B.apercu(e)), f"{e['nom']} ({B.GENRES.get(e['genre'], (e['genre'],))[0]})", e)
        f.addRow(_("Ce qui le remplace"), self.choix)
        self.orientation = QComboBox()
        for cle, (lib, _en) in R.ORIENTATIONS.items():
            self.orientation.addItem(lib, cle)
        f.addRow(_("Orientation"), self.orientation)
        self.f_form = f
        droite.addLayout(f)
        self.vignette = QLabel()
        self.vignette.setFixedHeight(90)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        droite.addWidget(self.vignette)
        droite.addWidget(self.desc)
        self.accord = QCheckBox(_("Les personnes de l'image sont d'accord pour qu'elle soit modifiée par l'IA (ou c'est moi)"))
        self.accord.setToolTip(_("L'image est envoyée à Gemini avec votre clef : seulement avec l'accord des personnes qu'on y voit"))
        droite.addWidget(self.accord)
        self.prix = QLabel(_("Gemini (votre clef) : environ {p} $ par essai, plus la relecture (environ {r} $).",
                             p=f"{R.PRIX:.2f}".replace(".", ","), r=f"{R.PRIX_RELECTURE:.2f}".replace(".", ",")))
        self.prix.setWordWrap(True)
        droite.addWidget(self.prix)
        self.credit = LigneCredit(self.params, "google", self, compact=True)
        droite.addWidget(self.credit)
        self.b_go = QPushButton(_("Remplacer (environ {p} $)", p=f"{R.PRIX:.2f}".replace(".", ",")))
        self.b_go.clicked.connect(self.lancer)
        droite.addWidget(self.b_go)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        droite.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        droite.addWidget(self.etat)
        self.verdict = QLabel("")
        self.verdict.setWordWrap(True)
        droite.addWidget(self.verdict)
        self._montre_avant = False
        droite.addStretch(1)
        h.addLayout(droite, 1)
        v.addLayout(h)
        hb = QHBoxLayout()
        image_plan = (self.ed.projet.media(clip.get("media")) or {}).get("genre") == "image"
        self.b_poser = QPushButton(_("Poser à la place de l'image") if image_plan else _("Insérer l'image à la ligne rouge"))
        self.b_poser.clicked.connect(self.poser)
        self.b_poser.setEnabled(False)
        self.b_garder = QPushButton(_("Garder dans les médias"))
        self.b_garder.clicked.connect(self.garder)
        self.b_garder.setEnabled(False)
        b_fermer = QPushButton(_("Fermer"))
        b_fermer.clicked.connect(self.close)
        hb.addWidget(self.b_poser)
        hb.addWidget(self.b_garder)
        hb.addStretch(1)
        hb.addWidget(b_fermer)
        v.addLayout(hb)
        self.image_plan = image_plan
        for w in (self.quoi.textChanged, self.accord.toggled):
            w.connect(self._maj)
        self.choix.currentIndexChanged.connect(self._entree)
        self._entree()
        self._mode_change()
        if not self.choix.count():
            self.etat.setText(_("Votre bibliothèque n'a encore aucun élément avec une image : Fabrique IA › « Ma bibliothèque de "
                                "créations… » pour en créer un."))

    def _image_source(self):
        p = self.ed.projet
        m = p.media(self.clip.get("media")) or {}
        if m.get("genre") == "image" and os.path.exists(m.get("chemin") or ""):
            return m["chemin"]
        from .cartes_assistant import image_ligne_rouge
        return image_ligne_rouge(self.ed)

    def mode(self):
        b = self.modes.checkedButton()
        return b.property("mode") if b else "auto"

    def _mode_change(self):
        auto = self.mode() == "auto"
        self.orientation.setEnabled(not auto)
        self.f_form.labelForField(self.orientation).setEnabled(not auto)
        if auto:
            self.l_zone.setText(_("Rien à tracer : Gemini trouve lui-même ce que vous avez nommé. Si vous tracez un cadre, il "
                                  "l'aide à le trouver."))
        elif not self.zone:
            self.l_zone.setText(_("Tracez le cadre de l'endroit où va le nouvel élément, à sa taille (il remplace ce qui s'y "
                                  "trouve)."))
        self._maj()

    def _basculer(self):
        if not self.resultat:
            return
        self._montre_avant = not self._montre_avant
        pm = QPixmap(self.source if self._montre_avant else self.resultat)
        self.apres.setPixmap(pm.scaled(440, 440, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.l_zone.setText(_("Image d'avant : cliquez pour revenir au résultat.") if self._montre_avant else
                            _("Résultat : cliquez l'image pour voir celle d'avant."))

    def _retracer(self):
        self.apres.hide()
        self.b_cadre.hide()
        self.image.show()
        self._mode_change()

    def _zone(self, b):
        self.zone = b
        self.image.cadres = [(1, "#E53935", b)]
        self.image.actif = 0
        self.image.update()
        self.l_zone.setText(_("Cadre tracé ; tracez-en un autre pour le corriger."))
        self._maj()

    def _entree(self):
        e = self.choix.currentData()
        if e:
            from . import bibliotheque_creations as B
            pm = QPixmap(B.apercu(e))
            if not pm.isNull():
                self.vignette.setPixmap(pm.scaledToHeight(84, Qt.SmoothTransformation))
            self.desc.setText(e.get("description") or "")
        self._maj()

    def _maj(self):
        pret = bool(self.source and (self.zone or self.mode() == "auto") and self.quoi.text().strip() and self.choix.currentData()
                    and self.accord.isChecked())
        self.b_go.setEnabled(pret and not (self.tache and self.tache.isRunning()))

    def lancer(self):
        if not getattr(self, "_test_oui", False) and QMessageBox.question(
                self, self.windowTitle(), _("Envoyer l'image à Gemini (votre clef) pour remplacer « {q} » par « {n} », puis la "
                                            "faire relire : environ {p} $ ?", q=self.quoi.text().strip(),
                                            n=self.choix.currentData()["nom"],
                                            p=f"{R.PRIX + R.PRIX_RELECTURE:.2f}".replace(".", ","))) != QMessageBox.Yes:
            return
        args = (self.params, self.source, list(self.zone) if self.zone else None, self.quoi.text(), self.choix.currentData())
        mode, orient = self.mode(), self.orientation.currentData()

        def travail(t):
            r = R.remplacer(*args, progression=t.avancer, mode=mode, orientation=orient)
            t.avancer(0.93, _("Relecture : avant, après et la fiche…"))
            try:
                v = R.verifier(args[0], args[1], r, args[3], args[4])
            except Exception as e:                    # la relecture n'empêche jamais de voir le résultat
                v = {"erreur": texte_erreur(e)}
            return r, v
        self.b_go.setEnabled(False)
        self.barre.setValue(0)
        self.barre.show()
        self.etat.setText(_("Gemini prépare l'image…"))
        self.verdict.setText("")
        self.tache = Tache(travail, _("Remplacer un élément de l'image"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("Remplacer un élément de l'image"))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self.tache.start()

    def _fini(self, r, err):
        try:
            self.barre.hide()
            self._maj()
            self.credit.montrer("google")
            if err:
                self.etat.setText(_("✕ Remplacement impossible : {e}", e=texte_erreur(err)[:300]))
                return
            r, v = r
            self.resultat = r
            self._montre_avant = False
            self.verdict.setText(self.texte_verdict(v))
            self._montre_avant = True
            self._basculer()
            self.image.hide()
            self.apres.show()
            self.b_cadre.show()
            self.b_poser.setEnabled(True)
            self.b_garder.setEnabled(True)
            self.b_go.setText(_("Refaire (environ {p} $)", p=f"{R.PRIX:.2f}".replace(".", ",")))
            self.etat.setText(_("Regardez le résultat : s'il convient, posez-le ; sinon corrigez le cadre ou le texte et refaites."))
        except RuntimeError:
            pass

    @staticmethod
    def texte_verdict(v):
        if v.get("erreur"):
            return _("Relecture impossible ({e}) : jugez à l'œil.", e=v["erreur"][:120])
        lignes = [("✓ " if v.get(k) else "⚠ ") + lib for k, lib in R.POINTS]
        if v.get("defauts"):
            lignes.append(_("Relecture : {d}", d=v["defauts"]))
        if all(v.get(k) for k, _l in R.POINTS):
            lignes.append(_("La relecture ne voit pas de défaut."))
        return "\n".join(lignes)

    def poser(self):
        if not self.resultat:
            return False
        if self.image_plan:
            ok = self.ed.remplacer_media_clip(self.clip["id"], self.resultat)
        else:
            ok = bool(self.ed.inserer_image(self.resultat, self.ed.timeline.position, nom=os.path.basename(self.resultat)))
        if ok:
            self.close()
        return ok

    def garder(self):
        if self.resultat:
            from . import moteur
            self.ed.projet.ajouter_media(self.resultat, moteur.sonder(self.resultat))
            self.ed.biblio.remplir(self.ed.projet)
            self.ed.encart.message(_("Image gardée dans les médias du projet."), 5000)

    def done(self, r):
        from .widgets import calcul_en_cours, garder_calcul
        if garder_calcul(self, calcul_en_cours(self)):
            return
        super().done(r)
