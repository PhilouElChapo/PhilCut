"""Images de départ et d'arrivée des plans, vues et validées avant la vidéo (0.9.73).

Philippe : « une image d'arrivée, mais elle est générée comment ? c'est ça le problème ». Gemini compose ces images ; s'il
se trompe, la vidéo (chère) est forcée vers l'erreur. Ici, chaque plan se regarde : départ et arrivée côte à côte ; on
garde, on refait avec une précision, on met sa propre image ou une image du film, ou on laisse le plan finir librement.
Seuls les plans validés partent en vidéo.
"""
import copy
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QVBoxLayout)

from . import sequence_ia as Q
from .langue import _
from .taches import Tache, texte_erreur
from .widgets import suivre_en_fond

PRIX_IMAGE = 0.04


class CadreImage(QLabel):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 170)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border:1px solid #555;border-radius:6px")
        self.setWordWrap(True)

    def montrer(self, chemin, vide):
        if chemin and os.path.exists(chemin):
            self.setPixmap(QPixmap(chemin).scaled(420, 236, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.setPixmap(QPixmap())
            self.setText(vide)


class DialogueImagesPlans(QDialog):
    """Revue plan par plan ; `seq` est la séquence de la fenêtre Séquence IA (modifiée sur place)."""

    def __init__(self, parent, seq, params, indices, ed=None):
        super().__init__(parent)
        self.seq, self.params, self.indices, self.ed = seq, params, list(indices), ed
        self.k, self.tache, self.taches = 0, None, []
        self.setWindowTitle(_("Images des plans, avant la vidéo"))
        self.resize(940, 560)
        v = QVBoxLayout(self)
        intro = QLabel(_("Le moteur vidéo part de l'image de <b>départ</b> et doit arriver sur l'image d'<b>arrivée</b>. Regardez-les "
                         "ici, avant de payer la vidéo : même visage, même tenue, pose possible ? Refaites ou remplacez celles qui ne "
                         "vont pas. Seuls les plans validés partent en vidéo."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.titre = QLabel("")
        self.titre.setWordWrap(True)
        self.titre.setStyleSheet("font-weight:600")
        v.addWidget(self.titre)
        h = QHBoxLayout()
        self.colonnes = {}
        for quoi, lib in (("depart", _("Départ")), ("arrivee", _("Arrivée"))):
            col = QVBoxLayout()
            col.addWidget(QLabel("<b>" + lib + "</b>"))
            cadre = CadreImage()
            col.addWidget(cadre, 1)
            hb = QHBoxLayout()
            boutons = []
            for blib, fn, aide in ((_("Refaire…"), lambda q=quoi: self.refaire(q), _("Gemini la recompose ; vous pouvez préciser ce qui ne va pas")),
                                   (_("Mon image…"), lambda q=quoi: self.mon_image(q), _("Une image à vous (fichier)")),
                                   (_("Image du film"), lambda q=quoi: self.image_du_film(q), _("L'image du film à la ligne rouge"))):
                b = QPushButton(blib)
                b.setToolTip(aide)
                b.clicked.connect(fn)
                hb.addWidget(b)
                boutons.append(b)
            if quoi == "arrivee":
                b = QPushButton(_("Sans arrivée"))
                b.setToolTip(_("Le moteur finit le plan librement (moins de contrôle sur la pose finale)"))
                b.clicked.connect(self.sans_arrivee)
                hb.addWidget(b)
                boutons.append(b)
            col.addLayout(hb)
            self.colonnes[quoi] = (cadre, boutons)
            h.addLayout(col, 1)
        v.addLayout(h, 1)
        self.note = QLabel("")
        self.note.setWordWrap(True)
        self.note.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.note)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hn = QHBoxLayout()
        self.b_prec = QPushButton(_("‹ Plan précédent"))
        self.b_prec.clicked.connect(lambda: self.aller(self.k - 1))
        hn.addWidget(self.b_prec)
        self.b_ok = QPushButton(_("Valider ce plan ›"))
        self.b_ok.setStyleSheet("font-weight:600")
        self.b_ok.clicked.connect(self.valider)
        hn.addWidget(self.b_ok)
        hn.addStretch(1)
        self.b_reduire = QPushButton(_("Réduire (suivi dans la barre du bas)"))
        self.b_reduire.clicked.connect(self.hide)
        self.b_reduire.hide()
        hn.addWidget(self.b_reduire)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        hn.addWidget(b)
        v.addLayout(hn)
        self.aller(0)

    # ------------------------------------------------------------------ affichage
    def _pl(self):
        return self.seq["plans"][self.indices[self.k]] if 0 <= self.k < len(self.indices) else None

    def aller(self, k):
        if not self.indices:
            return
        self.k = max(0, min(len(self.indices) - 1, k))
        self.montrer()

    def montrer(self):
        i = self.indices[self.k]
        pl = self._pl()
        ok = sum(1 for j in self.indices if self.seq["plans"][j].get("images_ok"))
        self.titre.setText(_("Plan {i} ({k} sur {n}, {ok} validé(s)) : {a}", i=i + 1, k=self.k + 1, n=len(self.indices), ok=ok,
                             a=pl.get("action", "")) + ("  ✓" if pl.get("images_ok") else ""))
        depart = Q.depart_prevu(self.seq, i)
        enchaine = i > 0 and pl.get("enchainer", True) and not (pl.get("image") and os.path.exists(pl["image"]))
        self.colonnes["depart"][0].montrer(depart, _("Pas encore d'image de départ : « Refaire… » la compose."))
        self.colonnes["arrivee"][0].montrer(
            "" if pl.get("sans_fin") else pl.get("image_fin"),
            _("Sans image d'arrivée : le moteur finit librement.") if pl.get("sans_fin") else _("Pas encore d'image d'arrivée : « Refaire… » la compose."))
        self.note.setText(_("Départ enchaîné : la vidéo partira de la vraie dernière image du plan précédent (ici, son arrivée "
                            "prévue). « Refaire… » ou « Mon image… » le détachent.") if enchaine else "")
        self.b_prec.setEnabled(self.k > 0)
        manque = not depart or not (pl.get("image_fin") or pl.get("sans_fin"))
        self.b_ok.setEnabled(not manque and not self._en_calcul())
        self.b_ok.setText(_("Valider ce plan ›") if self.k < len(self.indices) - 1 else _("Valider ce plan ✓"))
        for _c, boutons in self.colonnes.values():
            for b in boutons:
                b.setEnabled(not self._en_calcul())

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    # ------------------------------------------------------------------ actions
    def preparer_manquantes(self):
        """Compose d'un coup ce qui manque (prix demandé), plan après plan (l'arrivée d'un plan sert de départ au suivant)."""
        a_faire = []
        for i in self.indices:
            pl = self.seq["plans"][i]
            q = []
            if not Q.depart_prevu(self.seq, i) and not (i > 0 and pl.get("enchainer", True)):
                q.append("depart")
            if not pl.get("image_fin") and not pl.get("sans_fin"):
                q.append("arrivee")
            if q:
                a_faire.append((i, tuple(q)))
        if not a_faire:
            return
        n = sum(len(q) for _i, q in a_faire) + (len(Q.sans_planche(self.seq, self.indices)) if self.seq.get("image_fin_auto", True) else 0)
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Images des plans"), _("Composer {n} image(s) avec Gemini pour environ {p} $ (votre clef) ? Vous les "
                                               "verrez toutes avant la vidéo.", n=n, p=f"{n * PRIX_IMAGE:.2f}".replace(".", ","))) != QMessageBox.Yes:
            return
        self._lancer(lambda seq, t: [(t.avancer(k / len(a_faire), _("plan {i}", i=i + 1)), Q.preparer_images(seq, i, self.params, q))
                                     for k, (i, q) in enumerate(a_faire)], _("Images des plans : {n} à composer", n=n))

    def refaire(self, quoi):
        i = self.indices[self.k]
        if getattr(self, "_test_precision", None) is not None:
            precision, ok = self._test_precision, True
        else:
            precision, ok = QInputDialog.getText(self, _("Refaire l'image"), _(
                "Ce qui ne va pas, ou ce que vous voulez voir (facultatif, dans votre langue) ; environ 0,04 $ :\n"
                "ex. : assise, l'ordinateur ouvert devant elle, face caméra"))
        if not ok:
            return
        if quoi == "depart":
            self.seq["plans"][i]["image"] = ""
        self._lancer(lambda seq, t: Q.preparer_images(seq, i, self.params, (quoi,), precision.strip(), force=True),
                     _("Plan {i} : nouvelle image", i=i + 1))

    def _poser(self, quoi, chemin):
        pl = self._pl()
        if quoi == "depart":
            pl["image"] = chemin
        else:
            pl["image_fin"], pl["sans_fin"] = chemin, False
        pl["images_ok"] = False
        self.montrer()

    def mon_image(self, quoi):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Image du plan"), _("Images") + " (*.png *.jpg *.jpeg *.webp)", "images", self.params)
        if ch:
            self._poser(quoi, ch)

    def image_du_film(self, quoi):
        ed = self.ed
        if ed is None:
            return
        from . import moteur
        p, t = ed.projet, ed.timeline.position
        c = p.plan_visible(t) if hasattr(p, "plan_visible") else None
        m = p.media(c["media"]) if c else None
        if not (c and m):
            self.etat.setText(_("Mettez la ligne rouge sur un plan du film."))
            return
        temps = c["src_debut"] + (t - c["debut"]) * float(c.get("vitesse", 1.0) or 1.0)
        sortie = os.path.join(Q.dossier(self.seq), f"film_{int(t * 1000)}.png")
        moteur.lancer(["-y", "-ss", f"{max(0.0, temps):.3f}", "-i", m["chemin"], "-frames:v", "1", sortie])
        if os.path.exists(sortie):
            self._poser(quoi, sortie)

    def sans_arrivee(self):
        pl = self._pl()
        pl["image_fin"], pl["sans_fin"], pl["images_ok"] = "", True, False
        self.montrer()

    def valider(self):
        self._pl()["images_ok"] = True
        Q.enregistrer(self.seq)
        if self.k < len(self.indices) - 1:
            self.aller(self.k + 1)
        else:
            self.montrer()
            reste = [j + 1 for j in self.indices if not self.seq["plans"][j].get("images_ok")]
            self.etat.setText(_("✓ Tous les plans sont validés : fermez, puis « Fabriquer les plans manquants ».") if not reste else
                              _("Plans encore à valider : {l}.", l=", ".join(map(str, reste))))
            if not reste:
                self.accept()

    def _lancer(self, travail, texte):
        seq = copy.deepcopy(self.seq)
        t = Tache(lambda tache: (travail(seq, tache), seq)[1], _("Images des plans"))
        self.tache = t
        self.taches.append(t)
        suivre_en_fond(self, t, texte)
        self.etat.setText(texte + " — " + _("Gemini : 10 à 60 s par image."))
        self.b_reduire.show()
        self.montrer()

        def fin(r, e):
            self.b_reduire.hide()
            if e:
                self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:300]))
            elif r:
                for a, b in zip(self.seq["plans"], r["plans"]):
                    for cle in ("image", "image_fin", "images_ok", "sans_fin"):
                        if cle in b:
                            a[cle] = b[cle]
                for a, b in zip(self.seq["personnages"], r["personnages"]):
                    if b.get("planche"):
                        a["planche"] = b["planche"]
                Q.enregistrer(self.seq)
                self.etat.setText(_("Regardez, puis « Valider ce plan »."))
            self.montrer()
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def done(self, r):
        from .widgets import garder_calcul
        if garder_calcul(self, self._en_calcul()):
            return
        super().done(r)


def ouvrir(parent, seq, params, indices, ed=None, preparer=True):
    d = DialogueImagesPlans(parent, seq, params, indices, ed)
    d.setModal(False)
    d.show()
    if preparer:
        QTimer.singleShot(0, d.preparer_manquantes)
    return d
