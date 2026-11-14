"""Fenêtre « Faire parler » (0.9.65), non bloquante. Le son d'abord : celui qui passe sous le plan (ou sous la partie en
jaune, ou un fichier). Puis le visage : le plan lui-même (seule la bouche est refaite) ou une image du personnage (le
moteur fabrique toute la vidéo). Coût annoncé et confirmé, aperçu avant de poser, un seul Annuler."""
import os, tempfile, time

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from . import levres as LV
from .langue import _
from .taches import Tache, texte_erreur


def _tc(t):
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{t % 60:04.1f}"


class DialogueLevres(QDialog):
    def __init__(self, ed, clip=None, genre="video"):
        super().__init__(ed)
        from .projet import fin_clip
        self.ed, self.clip, self.genre = ed, clip, genre
        self.setModal(False)
        self.setWindowTitle(_("Faire parler un personnage sur le son"))
        self.setMinimumWidth(620)
        self.tache, self.resultat, self.fichier_son, self.image = None, None, None, None
        self.dossier = tempfile.mkdtemp(prefix="philcut-levres-")
        if clip is not None:
            self.debut, self.fin = clip["debut"], fin_clip(clip)
        else:
            z = ed.timeline.zone_valide()
            self.debut, self.fin = z if z else (ed.timeline.position, ed.timeline.position + 8.0)
        racine = QVBoxLayout(self)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zone.setFrameShape(QFrame.NoFrame)
        racine.addWidget(zone, 1)
        corps = QWidget()
        zone.setWidget(corps)
        v = QVBoxLayout(corps)
        if genre == "video":
            intro = _("Les lèvres du plan « {n} » sont refaites pour dire <b>le son qui passe sous lui</b> ({a} à {b}) : la voix "
                      "posée sur la piste Voix, une musique chantée… Le reste du plan ne change pas.", n=clip.get("nom", ""),
                      a=_tc(self.debut), b=_tc(self.fin))
        else:
            intro = _("Une <b>image du personnage</b> devient une vidéo qui dit <b>votre son</b> : lèvres, tête, regard. Le son est "
                      "celui qui passe sous la partie en jaune (ou à partir de la ligne rouge), ou un fichier. Le plan est posé "
                      "au-dessus du film, au même instant que le son.")
        lb = QLabel(intro)
        lb.setWordWrap(True)
        v.addWidget(lb)
        # --- le son
        self.lbl_son = QLabel("")
        self.lbl_son.setWordWrap(True)
        self.lbl_son.setStyleSheet("color:#9ad0ff")
        v.addWidget(self.lbl_son)
        hs = QHBoxLayout()
        if genre == "image":
            hs.addWidget(QLabel(_("De")))
            self.s_debut = QDoubleSpinBox()
            self.s_fin = QDoubleSpinBox()
            for w, val in ((self.s_debut, self.debut), (self.s_fin, self.fin)):
                w.setRange(0.0, 36000.0)
                w.setDecimals(1)
                w.setSuffix(" s")
                w.setValue(val)
                w.valueChanged.connect(self._maj)
            hs.addWidget(self.s_debut)
            hs.addWidget(QLabel(_("à")))
            hs.addWidget(self.s_fin)
            hs.addStretch(1)
            v.addLayout(hs)
            hs = QHBoxLayout()
        b = QPushButton(_("Un fichier son à la place…"))
        b.clicked.connect(self._choisir_son)
        hs.addWidget(b)
        self.b_sans_fichier = QPushButton(_("Le son de la timeline"))
        self.b_sans_fichier.clicked.connect(lambda: (setattr(self, "fichier_son", None), self._maj()))
        self.b_sans_fichier.hide()
        hs.addWidget(self.b_sans_fichier)
        hs.addStretch(1)
        v.addLayout(hs)
        self.isoler = QCheckBox(_("Isoler d'abord la voix (musique derrière, chanson) : les lèvres suivent mieux"))
        v.addWidget(self.isoler)
        # --- le visage (image)
        if genre == "image":
            hi = QHBoxLayout()
            self.vignette = QLabel()
            self.vignette.setFixedSize(160, 90)
            self.vignette.setStyleSheet("background:#000;border-radius:4px")
            self.vignette.setAlignment(Qt.AlignCenter)
            hi.addWidget(self.vignette)
            vi = QVBoxLayout()
            b = QPushButton(_("Image du personnage…"))
            b.clicked.connect(self._choisir_image)
            vi.addWidget(b)
            b = QPushButton(_("L'image du film à la ligne rouge"))
            b.clicked.connect(self._image_du_film)
            vi.addWidget(b)
            conseil = QLabel(_("Conseil : un personnage de face, yeux ouverts, bouche fermée, bien éclairé. Fabrique IA › Image peut le "
                               "créer."))
            conseil.setWordWrap(True)
            conseil.setStyleSheet("color:#9aa4b2")
            vi.addWidget(conseil)
            hi.addLayout(vi, 1)
            v.addLayout(hi)
        # --- moteur
        hm = QHBoxLayout()
        hm.addWidget(QLabel(_("Moteur")))
        self.moteur = QComboBox()
        for k, m in LV.moteurs(genre):
            self.moteur.addItem(m["nom"], k)
        self.moteur.currentIndexChanged.connect(self._maj)
        hm.addWidget(self.moteur, 1)
        self.resolution = QComboBox()
        self.resolution.addItem("720p", "720p")
        self.resolution.addItem("1080p", "1080p")
        self.resolution.setVisible(genre == "image")
        self.resolution.currentIndexChanged.connect(self._maj)
        hm.addWidget(self.resolution)
        v.addLayout(hm)
        self.expl = QLabel("")
        self.expl.setWordWrap(True)
        self.expl.setStyleSheet("color:#9aa4b2")
        v.addWidget(self.expl)
        if genre == "image":
            from .consigne_bilingue import ConsigneBilingue
            v.addWidget(QLabel(_("Attitude, gestes (facultatif) :")))
            self.consigne = ConsigneBilingue(48, _("ex. : parle calmement en souriant, petits gestes des mains"))
            v.addWidget(self.consigne)
        else:
            self.consigne = None
        self.accord = QCheckBox(_("Visage d'un personnage inventé, le mien, ou d'une personne d'accord"))
        self.accord.toggled.connect(self._maj)
        v.addWidget(self.accord)
        eng = QLabel(_("Jamais une personnalité ni une personne qui n'est pas d'accord : faire dire à un vrai visage ce qu'il n'a "
                       "pas dit, c'est fabriquer un faux. En cochant, vous vous en portez garant."))
        eng.setWordWrap(True)
        eng.setStyleSheet("color:#c98a00")
        v.addWidget(eng)
        self.cout = QLabel("")
        self.cout.setWordWrap(True)
        self.cout.setStyleSheet("font-weight:600")
        v.addWidget(self.cout)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        v.addWidget(self.apercu)
        v.addStretch(1)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        racine.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        racine.addWidget(self.etat)
        hb = QHBoxLayout()
        self.b_fabriquer = QPushButton(_("Faire parler"))
        self.b_fabriquer.setStyleSheet("font-weight:600")
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hb.addWidget(self.b_fabriquer)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.clicked.connect(lambda: self.tache and self.tache.stopper())
        self.b_arreter.hide()
        hb.addWidget(self.b_arreter)
        self.b_poser = QPushButton(_("Poser à la place du plan") if genre == "video" else _("Poser au-dessus du film"))
        self.b_poser.clicked.connect(self.poser)
        self.b_poser.setEnabled(False)
        hb.addWidget(self.b_poser)
        hb.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        hb.addWidget(b)
        racine.addLayout(hb)
        self._maj()

    # ------------------------------------------------------------------ état
    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _plage(self):
        if self.genre == "image":
            return self.s_debut.value(), max(self.s_debut.value() + 1.0, self.s_fin.value())
        return self.debut, self.fin

    def duree(self):
        if self.fichier_son:
            from . import moteur
            return float((moteur.sonder(self.fichier_son) or {}).get("duree") or 0)
        a, b = self._plage()
        return b - a

    def _maj(self, *_a):
        from . import separation as S
        a, b = self._plage()
        if self.fichier_son:
            self.lbl_son.setText(_("Son : le fichier « {f} » ({d} s).", f=os.path.basename(self.fichier_son), d=int(self.duree())))
        else:
            sons = LV.sons_sous(self.ed.projet, a, b)
            noms = ", ".join(dict.fromkeys(c.get("nom") or m.get("nom") or "" for c, m in sons))
            self.lbl_son.setText(_("Son : ce qui passe de {a} à {b} — {n}.", a=_tc(a), b=_tc(b), n=noms) if sons else
                                 _("⚠ Aucun son de {a} à {b} : posez d'abord la voix sous ce passage, ou choisissez un fichier son.",
                                   a=_tc(a), b=_tc(b)))
        self.b_sans_fichier.setVisible(bool(self.fichier_son))
        sep = S.manquant(self.ed.params) is None
        self.isoler.setEnabled(sep)
        if not sep:
            self.isoler.setChecked(False)
            self.isoler.setToolTip(_("Installez « Séparer voix, musique et bruits » (Préférences › IA locale) pour isoler la voix"))
        k = self.moteur.currentData()
        m = LV.MOTEURS[k]
        d = self.duree()
        self.expl.setText(m["explication"])
        manque = None
        if not LV.clef(self.ed.params):
            manque = _("Il faut une clef fal.ai : Préférences › Assistant et IA, « Clef fal.ai » (ou « Connecter une IA ») ; paiement "
                       "à l'usage, sans abonnement.")
        elif d > m["max_s"]:
            manque = _("Son trop long pour ce moteur ({d} s au plus) : prenez un passage plus court.", d=int(m["max_s"]))
        elif self.genre == "image" and not self.image:
            manque = _("Choisissez l'image du personnage.")
        elif not self.fichier_son and not LV.sons_sous(self.ed.projet, a, b):
            manque = _("Pas de son à faire dire.")
        self.cout.setText(manque or _("Coût annoncé par fal.ai : environ {p} $ pour {d} s (demandé avant de lancer).",
                                      p=f"{LV.prix(k, d):.2f}".replace(".", ","), d=int(round(d))))
        self.cout.setStyleSheet("font-weight:600;color:#c98a00" if manque else "font-weight:600")
        self.b_fabriquer.setEnabled(not manque and self.accord.isChecked() and not self._en_calcul())
        self.b_fabriquer.setToolTip("" if self.accord.isChecked() else _("Cochez d'abord la case du visage"))

    # ------------------------------------------------------------------ choix
    def _choisir_son(self):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Son à faire dire"), _("Sons") + " (*.wav *.mp3 *.m4a *.flac *.ogg *.aac)", "musique",
                            self.ed.params)
        if ch:
            self.fichier_son = ch
            self._maj()

    def _poser_image(self, ch):
        self.image = ch
        pm = QPixmap(ch)
        if not pm.isNull():
            self.vignette.setPixmap(pm.scaled(160, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._maj()

    def _choisir_image(self):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Image du personnage"), "Images (*.png *.jpg *.jpeg *.webp)", "images", self.ed.params)
        if ch:
            self._poser_image(ch)

    def _image_du_film(self):
        from . import moteur
        p, t = self.ed.projet, self.ed.timeline.position
        c = p.plan_visible(t) if hasattr(p, "plan_visible") else None
        c = c or next((x for x in p.clips_piste("video") if x["debut"] <= t < x["debut"] + (x["src_fin"] - x["src_debut"])), None)
        if not c:
            self.etat.setText(_("Pas de plan vidéo à la ligne rouge."))
            return
        m = p.media(c["media"])
        sortie = os.path.join(self.dossier, f"image_{int(time.time())}.png")
        moteur.lancer(["-y", "-v", "error", "-ss", f"{c['src_debut'] + (t - c['debut']) * float(c.get('vitesse') or 1.0):.3f}",
                       "-i", m["chemin"], "-frames:v", "1", sortie])
        if os.path.exists(sortie):
            self._poser_image(sortie)

    # ------------------------------------------------------------------ fabrication
    def fabriquer(self):
        if self._en_calcul() or not self.accord.isChecked():
            return
        k, d = self.moteur.currentData(), self.duree()
        p = LV.prix(k, d)
        if QMessageBox.question(self, _("Faire parler"), _("Faire calculer les lèvres par {m} pour environ {p} $ ({d} s), facturés sur "
                                                         "votre compte fal.ai ?", m=LV.MOTEURS[k]["nom"],
                                                         p=f"{p:.2f}".replace(".", ","), d=int(round(d)))) != QMessageBox.Yes:
            return
        projet, params, clip, (a, b) = self.ed.projet, self.ed.params, self.clip, self._plage()
        fichier, isoler, image, genre = self.fichier_son, self.isoler.isChecked(), self.image, self.genre
        consigne = self.consigne.toPlainText().strip() if self.consigne is not None else ""
        resolution, dossier = self.resolution.currentData(), self.dossier
        sortie = os.path.join(LV.dossier_sorties(), f"parle_{time.strftime('%Y%m%d_%H%M%S')}.mp4")

        def travail(t):
            son = fichier
            if not son:
                t.avancer(0.01, _("Préparation du son du passage…"))
                son = LV.extraire_son(projet, a, b, os.path.join(dossier, "son.wav"))
            if isoler:
                son = LV.isoler_voix(son, params, lambda f, x="": t.avancer(0.01 + 0.09 * f, _("Isolement de la voix")),
                                     lambda: t.arret)
            video = LV.extraire_plan(projet, clip, os.path.join(dossier, "plan.mp4")) if genre == "video" else None
            return LV.fabriquer(params, k, son, sortie, image=image, video=video, consigne=consigne, resolution=resolution,
                                progression=lambda f, x="": t.avancer(0.1 + 0.9 * f, x), arret=lambda: t.arret)
        self.tache = Tache(travail, _("Faire parler"))
        self.tache.lier(self)
        from .widgets import suivre_en_fond
        suivre_en_fond(self, self.tache, _("Lèvres sur le son ({m})", m=LV.MOTEURS[k]["nom"]))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, e: self._fini(r, e, k, p, a, b), Qt.QueuedConnection)
        self.barre.setValue(0)
        self.barre.show()
        self.b_arreter.show()
        self.b_poser.setEnabled(False)
        self.apercu.arreter()
        self.apercu.hide()
        self._maj()
        self.tache.start()

    def _fini(self, r, err, k, p, a, b):
        self.barre.hide()
        self.b_arreter.hide()
        self._maj()
        if err:
            self.etat.setText(_("Arrêté.") if isinstance(err, InterruptedError) else _("✕ {e}", e=texte_erreur(err)[:400]))
            return
        from . import creations
        creations.ecrire(r, LV.recette(k, self.genre, self.image, self.consigne.toPlainText().strip() if self.consigne else "",
                                       a, b, p))
        self.resultat = r
        self.apercu.charger(r, video=True)
        self.apercu.fondu_e.hide()
        self.apercu.fondu_s.hide()
        self.b_poser.setEnabled(True)
        self.etat.setText(_("Regardez : les lèvres suivent-elles le son ? Puis « {b} ».", b=self.b_poser.text()))

    def poser(self):
        if not self.resultat:
            return
        self.apercu.arreter()
        ed, p = self.ed, self.ed.projet
        if self.genre == "video" and p.clip(self.clip["id"]) is not None:
            ed.remplacer_media_clip(self.clip["id"], self.resultat, {"src_debut": 0.0, "src_fin": self.fin - self.debut})
            c = p.clip(self.clip["id"])
            c["vitesse"] = 1.0
            c["muet"] = True                       # le son reste celui de la timeline, dessous
            ed.rafraichir()
            self.etat.setText(_("✓ Le plan parle sur le son. Edition › Annuler pour revenir."))
        else:
            a, _b = self._plage()
            ci = ed.poser_au_dessus(self.resultat, a, _("Personnage qui parle"))
            ci["muet"] = not self.fichier_son      # son du fichier : il vient avec le plan
            self.etat.setText(_("✓ Posé au-dessus du film à {t}. Edition › Annuler pour revenir.", t=_tc(a)))
        self.b_poser.setEnabled(False)

    def closeEvent(self, ev):
        from .widgets import garder_calcul
        self.apercu.arreter()
        if garder_calcul(self, self._en_calcul()):
            ev.ignore()
            return
        super().closeEvent(ev)

    def done(self, r):
        from .widgets import garder_calcul
        if garder_calcul(self, self._en_calcul()):
            return
        super().done(r)
