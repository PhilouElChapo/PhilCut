"""Fenêtre « Vidéo de narration d'après ce qui est dit » (0.9.67), non bloquante. 1. la voix est transcrite et découpée en
idées ; 2. rendu, format, présentateur éventuel ; 3. une image proposée par idée (modifiable, idées par l'IA sur clic) ;
4. fabrication par le cloud, prix total demandé ; 5. aperçu puis pose sous les mots (un seul Annuler)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from . import narration as NA
from .langue import _
from .taches import Tache, texte_erreur


def _tc(t):
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{t % 60:04.1f}"


def _d(x):
    return f"{x:.2f}".replace(".", ",")


def _fixe(t):
    it = QTableWidgetItem(t)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    it.setToolTip(t)
    return it


def piste_de_voix(projet, clip=None):
    """La piste qui porte la voix : celle du plan choisi, sinon Voix, sinon la première piste de son non vide, sinon la vidéo."""
    if clip is not None:
        return clip["piste"]
    for p in ["voix"] + projet.pistes_audio() + ["video"]:
        if projet.clips_piste(p):
            return p
    return "voix"


class DialogueNarration(QDialog):
    def __init__(self, ed, clip=None):
        super().__init__(ed)
        self.ed, self.params = ed, ed.params
        self.setModal(False)
        self.setWindowTitle(_("Vidéo de narration d'après ce qui est dit"))
        self.resize(900, 720)
        self.tache, self.narr = None, None
        self.piste = piste_de_voix(ed.projet, clip)
        racine = QVBoxLayout(self)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zone.setFrameShape(QFrame.NoFrame)
        racine.addWidget(zone, 1)
        corps = QWidget()
        zone.setWidget(corps)
        v = QVBoxLayout(corps)
        intro = QLabel(_("PhilCut écoute <b>ce qui est dit</b>, le découpe en idées et propose une image animée pour chacune, posée "
                         "exactement sous les mots. Vous corrigez tout ; rien n'est payé avant « Fabriquer »."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        # 1. la voix
        g1 = QGroupBox(_("1. Ce qui est dit"))
        l1 = QVBoxLayout(g1)
        self.lbl_voix = QLabel("")
        self.lbl_voix.setWordWrap(True)
        self.lbl_voix.setStyleSheet("color:#9ad0ff")
        l1.addWidget(self.lbl_voix)
        h = QHBoxLayout()
        self.b_fichier = QPushButton(_("Choisir un fichier de voix…"))
        self.b_fichier.clicked.connect(self._fichier_voix)
        h.addWidget(self.b_fichier)
        h.addStretch(1)
        self.b_transcrire = QPushButton(_("Ecouter et découper"))
        self.b_transcrire.clicked.connect(self.transcrire)
        h.addWidget(self.b_transcrire)
        l1.addLayout(h)
        v.addWidget(g1)
        # 2. rendu et présentateur
        g2 = QGroupBox(_("2. Le rendu et le présentateur"))
        l2 = QVBoxLayout(g2)
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Rendu")))
        self.rendu = QComboBox()
        for k, (lib, _en) in sorted(NA.RENDUS.items(), key=lambda kv: NA._net(kv[1][0])):
            self.rendu.addItem(lib, k)
        self.rendu.setCurrentIndex(self.rendu.findData("cinema"))
        h.addWidget(self.rendu, 1)
        self.format = QComboBox()
        self.format.addItem(_("Paysage 16:9"), "16:9")
        self.format.addItem(_("Vertical 9:16"), "9:16")
        h.addWidget(self.format)
        l2.addLayout(h)
        self.pres_actif = QCheckBox(_("Un présentateur apparaît par moments et dit la voix (lèvres calées, OmniHuman)"))
        self.pres_actif.toggled.connect(self._presentateur_change)
        l2.addWidget(self.pres_actif)
        self.boite_pres = QWidget()
        hp = QHBoxLayout(self.boite_pres)
        hp.setContentsMargins(0, 0, 0, 0)
        self.vignette = QLabel()
        self.vignette.setFixedSize(96, 96)
        self.vignette.setStyleSheet("background:#000;border-radius:4px")
        self.vignette.setAlignment(Qt.AlignCenter)
        hp.addWidget(self.vignette)
        vp = QVBoxLayout()
        self.pres_desc = QLineEdit()
        self.pres_desc.setPlaceholderText(_("A quoi il ressemble : âge, tenue, lieu…"))
        vp.addWidget(self.pres_desc)
        hb = QHBoxLayout()
        b = QPushButton(_("Une image…"))
        b.clicked.connect(self._image_presentateur)
        hb.addWidget(b)
        self.b_creer_pres = QPushButton(_("Le créer avec Gemini"))
        self.b_creer_pres.clicked.connect(self._creer_presentateur)
        self.b_creer_pres.setEnabled(bool(self.params.get("clef_gemini")))
        hb.addWidget(self.b_creer_pres)
        hb.addStretch(1)
        vp.addLayout(hb)
        self.pres_accord = QCheckBox(_("Visage d'un personnage inventé, le mien, ou d'une personne d'accord"))
        self.pres_accord.toggled.connect(self._maj)
        vp.addWidget(self.pres_accord)
        hp.addLayout(vp, 1)
        self.boite_pres.hide()
        l2.addWidget(self.boite_pres)
        v.addWidget(g2)
        # 3. plans
        g3 = QGroupBox(_("3. Une image par idée, sous les mots"))
        l3 = QVBoxLayout(g3)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([_("De"), _("Ce qui est dit"), _("Image proposée (modifiable)"), _("Présentateur")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setWordWrap(True)                      # jamais de texte coupé : la ligne s'agrandit
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.horizontalHeader().sectionResized.connect(lambda *_a: self.table.resizeRowsToContents())
        self.table.setMinimumHeight(220)
        self.table.currentCellChanged.connect(lambda r, *_a: self._voir_plan(r))
        l3.addWidget(self.table)
        h = QHBoxLayout()
        self.b_idees = QPushButton(_("Idées d'images avec l'IA"))
        self.b_idees.clicked.connect(self.idees)
        h.addWidget(self.b_idees)
        self.niveau = self._choix_niveau()
        h.addWidget(self.niveau)
        h.addStretch(1)
        l3.addLayout(h)
        v.addWidget(g3)
        # 4. fabrication
        g4 = QGroupBox(_("4. Fabrication par le cloud"))
        l4 = QVBoxLayout(g4)
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Moteur vidéo")))
        self.moteur = QComboBox()
        from . import generateurs_video as GV
        for mo in sorted(GV.disponibles(self.params), key=lambda x: NA._net(x["nom"])):
            self.moteur.addItem(mo["nom"], mo["id"])
        self.moteur.currentIndexChanged.connect(self._maj)
        h.addWidget(self.moteur, 1)
        l4.addLayout(h)
        self.cout = QLabel("")
        self.cout.setWordWrap(True)
        l4.addWidget(self.cout)
        v.addWidget(g4)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        self.apercu.hide()
        v.addWidget(self.apercu)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        racine.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        racine.addWidget(self.etat)
        hb = QHBoxLayout()
        self.b_fabriquer = QPushButton(_("Fabriquer les plans"))
        self.b_fabriquer.setStyleSheet("font-weight:600")
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hb.addWidget(self.b_fabriquer)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.clicked.connect(lambda: self.tache and self.tache.stopper())
        self.b_arreter.hide()
        hb.addWidget(self.b_arreter)
        self.b_poser = QPushButton(_("Poser sous les mots"))
        self.b_poser.clicked.connect(self.poser)
        hb.addWidget(self.b_poser)
        hb.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        hb.addWidget(b)
        racine.addLayout(hb)
        self.rendu.currentIndexChanged.connect(self._rendu_change)
        self.format.currentIndexChanged.connect(self._rendu_change)
        self._charger()
        self._maj()

    # ------------------------------------------------------------------ état
    def _choix_niveau(self):
        from . import ia
        c = QComboBox()
        clefs = {m for m, _k in ia.moteurs(dict(self.params, ia_moteur="claude"))}
        if "claude" in clefs:
            c.addItem(_("Claude (cloud, le meilleur pour écrire)"), "claude")
        if "gemini" in clefs:
            c.addItem(_("Gemini (cloud)"), "gemini")
        c.addItem(_("IA locale (sur ce poste, gratuit)"), "locale")
        return c

    def _media_voix(self):
        clips = self.ed.projet.clips_piste(self.piste)
        return self.ed.projet.media(clips[0]["media"]) if clips else None

    def _charger(self):
        m = self._media_voix()
        d = (m or {}).get("narration")
        if d and os.path.exists(os.path.join(d, "narration.json")):
            import json
            try:
                with open(os.path.join(d, "narration.json"), encoding="utf-8") as f:
                    self.narr = json.load(f)
            except (OSError, ValueError):
                self.narr = None
        if self.narr:
            for w in (self.rendu, self.format, self.pres_actif):
                w.blockSignals(True)
            self.rendu.setCurrentIndex(max(0, self.rendu.findData(self.narr["rendu"])))
            self.format.setCurrentIndex(max(0, self.format.findData(self.narr.get("format", "16:9"))))
            self.pres_actif.setChecked(bool(self.narr["presentateur"].get("actif")))
            for w in (self.rendu, self.format, self.pres_actif):
                w.blockSignals(False)
            self.boite_pres.setVisible(self.pres_actif.isChecked())
            self.pres_desc.setText(self.narr["presentateur"].get("description", ""))
            self._vignette()
            self._afficher()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _maj(self, *_a):
        from .projet import fin_clip
        clips = self.ed.projet.clips_piste(self.piste)
        noms = {"voix": _("Voix"), "video": _("Vidéo 1")}
        if clips:
            a, b = clips[0]["debut"], max(fin_clip(c) for c in clips)
            self.lbl_voix.setText(_("Piste « {p} » : {n} plan(s), de {a} à {b}.", p=noms.get(self.piste, self.piste), n=len(clips),
                                    a=_tc(a), b=_tc(b)))
        else:
            self.lbl_voix.setText(_("⚠ Rien sur la piste Voix : enregistrez la voix, posez une voix IA, ou choisissez un fichier."))
        self.b_transcrire.setEnabled(bool(clips) and not self._en_calcul())
        pret = self.narr is not None
        self.b_idees.setEnabled(pret and not self._en_calcul())
        manque = None
        if not pret:
            manque = _("Commencez par « Ecouter et découper ».")
        elif not self.moteur.count():
            manque = _("Aucun moteur vidéo : ajoutez une clef Gemini ou fal.ai (Préférences › Assistant et IA).")
        elif self.pres_actif.isChecked() and any(p.get("presentateur") for p in self.narr["plans"]):
            from . import levres as LV
            if not LV.clef(self.params):
                manque = _("Le présentateur passe par fal.ai : ajoutez la clef fal.ai, ou décochez « Présentateur » dans les plans.")
            elif not (self.narr["presentateur"].get("image") or self.params.get("clef_gemini")):
                manque = _("Choisissez l'image du présentateur (ou ajoutez une clef Gemini pour le créer).")
            elif not self.pres_accord.isChecked():
                manque = _("Cochez la case du visage du présentateur.")
        if pret:
            self._lire_table()
            self.narr["moteur"] = self.moteur.currentData() or ""
            vi, pr, im, t = NA.prix_detail(self.narr, self.params)
            n = len(NA.a_fabriquer(self.narr))
            texte = (_("{n} plans à fabriquer : environ {p} $ — images animées {v} $, présentateur {r} $, portrait {i} $. Demandé avant "
                       "de lancer.", n=n, p=_d(t), v=_d(vi), r=_d(pr), i=_d(im)) if n else
                     _("Tous les plans sont prêts : regardez-les (cliquez une ligne), puis « Poser sous les mots »."))
            fait = len(self.narr["plans"]) - n
            self.b_poser.setEnabled(fait > 0 and not self._en_calcul())
        else:
            texte = ""
            self.b_poser.setEnabled(False)
        self.cout.setText(manque or texte)
        self.cout.setStyleSheet("font-weight:600;color:#c98a00" if manque else "font-weight:600")
        self.b_fabriquer.setEnabled(pret and not manque and not self._en_calcul() and bool(NA.a_fabriquer(self.narr)))

    def _lire_table(self):
        if not self.narr:
            return
        for r, p in enumerate(self.narr["plans"]):
            it = self.table.item(r, 2)
            if it and it.text().strip() and it.text().strip() != p["action"]:
                p.update(action=it.text().strip(), action_en="", consigne="")
            ch = self.table.cellWidget(r, 3)
            if ch is not None:
                p["presentateur"] = ch.isChecked() and self.pres_actif.isChecked()
        pres = self.narr["presentateur"]
        if self.pres_desc.text().strip() and self.pres_desc.text().strip() != pres.get("description"):
            pres["description"] = self.pres_desc.text().strip()
        pres["actif"] = self.pres_actif.isChecked()

    def _afficher(self):
        n = self.narr
        self.table.blockSignals(True)
        self.table.setRowCount(len(n["plans"]))
        for r, p in enumerate(n["plans"]):
            self.table.setItem(r, 0, _fixe(_tc(p["debut"])))
            self.table.setItem(r, 1, _fixe(p["texte"]))
            self.table.setItem(r, 2, QTableWidgetItem(p["action"]))
            if self.pres_actif.isChecked():
                ch = QCheckBox("✓" if p.get("fichier") and os.path.exists(p["fichier"]) else "")
                ch.setChecked(bool(p.get("presentateur")))
                ch.toggled.connect(lambda _c: self._maj())
                self.table.setCellWidget(r, 3, ch)
            else:
                self.table.removeCellWidget(r, 3)
                self.table.setItem(r, 3, _fixe("✓" if p.get("fichier") and os.path.exists(p["fichier"]) else ""))
        self.table.blockSignals(False)
        self.table.resizeColumnToContents(0)
        self.table.resizeRowsToContents()
        self._maj()

    def _vignette(self):
        img = (self.narr or {}).get("presentateur", {}).get("image")
        pm = QPixmap(img) if img and os.path.exists(img) else QPixmap()
        self.vignette.setPixmap(pm.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pm.isNull() else QPixmap())

    def _presentateur_change(self, oui):
        self.boite_pres.setVisible(oui)
        if self.narr:
            self._lire_table()
            self.narr["presentateur"]["actif"] = oui
            NA.proposer_presentateur(self.narr)
            self._afficher()
        self._maj()

    def _rendu_change(self, *_a):
        if self.narr:
            self._lire_table()
            self.narr.update(rendu=self.rendu.currentData(), format=self.format.currentData())
        self._maj()

    def _fichier_voix(self):
        from . import moteur
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Voix à illustrer"), _("Sons") + " (*.wav *.mp3 *.m4a *.flac *.ogg *.aac)", "musique", self.params)
        if not ch:
            return
        p = self.ed.projet
        p.marquer()
        m = p.ajouter_media(ch, moteur.sonder(ch))
        p.ajouter_clip(m["id"], "voix", self.ed.timeline.position)
        self.piste = "voix"
        self.ed.rafraichir()
        self._maj()

    def _image_presentateur(self):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Image du présentateur"), "Images (*.png *.jpg *.jpeg *.webp)", "images", self.params)
        if ch and self.narr:
            self.narr["presentateur"]["image"] = ch
            self._vignette()
            self._maj()

    # ------------------------------------------------------------------ calculs
    def _lancer(self, travail, titre, fin):
        self.tache = Tache(travail, titre)
        self.tache.lier(self)
        from .widgets import suivre_en_fond
        suivre_en_fond(self, self.tache, titre)
        self.tache.progression.connect(lambda f, t: (self.barre.setValue(int(f * 1000)), t and self.etat.setText(t)), Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, e: self._fin(r, e, fin), Qt.QueuedConnection)
        self.barre.setValue(0)
        self.barre.show()
        self.b_arreter.show()
        self._maj()
        self.tache.start()

    def _fin(self, r, err, fin):
        self.barre.hide()
        self.b_arreter.hide()
        if err:
            self.etat.setText(_("Arrêté.") if isinstance(err, InterruptedError) else _("✕ {e}", e=texte_erreur(err)[:400]))
        fin(r, err)
        self._maj()

    def transcrire(self):
        if self._en_calcul():
            return
        from . import montage_texte as MT
        projet, params, piste = self.ed.projet, self.params, self.piste

        def travail(t):
            t.avancer(0.01, _("Transcription de la voix sur ce poste…"))
            MT.transcrire(projet, params, progression=lambda f, x="": t.avancer(0.02 + 0.95 * f, _("Transcription : {x}", x=x)),
                          arret=lambda: t.arret, piste=piste)
            mots = MT.mots_du_montage(projet, piste)
            if not mots:
                raise RuntimeError(_("Aucun mot entendu sur cette piste."))
            return NA.segments(mots)

        def fin(segs, err):
            if err:
                return
            self.narr = NA.nouvelle(segs, self.rendu.currentData(), self.format.currentData(), piste)
            self.narr["presentateur"]["actif"] = self.pres_actif.isChecked()
            if self.pres_desc.text().strip():
                self.narr["presentateur"]["description"] = self.pres_desc.text().strip()
            else:
                self.pres_desc.setText(self.narr["presentateur"]["description"])
            NA.proposer_presentateur(self.narr)
            self._noter()
            self._afficher()
            self.etat.setText(_("✓ {n} idées : relisez les images proposées, ou « Idées d'images avec l'IA ».", n=len(segs)))
        self._lancer(travail, _("Narration : écoute de la voix"), fin)

    def _noter(self):
        NA.enregistrer(self.narr)
        m = self._media_voix()
        if m is not None:
            m["narration"] = NA.dossier(self.narr)

    def idees(self):
        if not self.narr or self._en_calcul():
            return
        self._lire_table()
        from .dialogues_musique_ia import _avec_moteur
        niveau, narr, params = self.niveau.currentData(), self.narr, self.params

        def fin(n, err):
            if not err:
                self._afficher()
                self.etat.setText(_("✓ {n} images proposées par l'IA : modifiez ce qui ne vous plaît pas.", n=n))
        self._lancer(lambda t: _avec_moteur(niveau, lambda: NA.idees_ia(narr, params, "locale" if niveau == "locale" else "cloud")),
                     _("Narration : idées d'images"), fin)

    def _creer_presentateur(self):
        if not self.narr or self._en_calcul():
            return
        self._lire_table()
        narr, params = self.narr, self.params

        def fin(_r, err):
            if not err:
                self._vignette()
                self.etat.setText(_("✓ Présentateur créé : regardez-le, recréez-le si besoin."))
        self._lancer(lambda t: NA.portrait_presentateur(narr, params), _("Narration : présentateur"), fin)

    def fabriquer(self):
        if not self.narr or self._en_calcul():
            return
        self._lire_table()
        vi, pr, im, total = NA.prix_detail(self.narr, self.params)
        a_faire = NA.a_fabriquer(self.narr)
        if QMessageBox.question(self, _("Fabriquer les plans"),
                                _("Fabriquer {n} plans pour environ {p} $ (images animées {v} $, présentateur {r} $, portrait {i} $), "
                                  "facturés sur vos comptes ? Vous pourrez fermer la fenêtre : la barre du bas suit.", n=len(a_faire),
                                  p=_d(total), v=_d(vi), r=_d(pr), i=_d(im))) != QMessageBox.Yes:
            return
        from . import levres as LV
        narr, params, projet = self.narr, self.params, self.ed.projet
        self._noter()
        sons = {}
        for i in a_faire:                                  # le passage de voix de chaque plan du présentateur, préparé ici
            p = narr["plans"][i]
            if p.get("presentateur"):
                sons[i] = (p["debut"], p["fin"])

        def travail(t):
            n = len(a_faire) + 1
            if sons and not (narr["presentateur"].get("image") and os.path.exists(narr["presentateur"]["image"])):
                t.avancer(0.0, _("Portrait du présentateur"))
                NA.portrait_presentateur(narr, params)
            faits, erreurs = 0, []
            for k, i in enumerate(a_faire):
                if t.arret:
                    raise InterruptedError()
                try:
                    son = None
                    if i in sons:
                        son = LV.extraire_son(projet, *sons[i], os.path.join(NA.dossier(narr), f"plan{i + 1:02d}_voix.wav"),
                                              pistes=[narr["piste"]])
                    NA.fabriquer_plan(narr, i, params, son, lambda f, x="", k=k: t.avancer((k + 1 + f) / n, x), lambda: t.arret)
                    faits += 1
                except InterruptedError:
                    raise
                except Exception as e:     # noqa: BLE001 : un plan raté n'arrête pas les autres
                    erreurs.append((i, texte_erreur(e)))
            NA.enregistrer(narr)
            return faits, erreurs

        def fin(r, err):
            self._afficher()
            if err:
                return
            faits, erreurs = r
            msg = _("✓ {n} plans fabriqués. Cliquez une ligne pour regarder, puis « Poser sous les mots ».", n=faits)
            if erreurs:
                msg += " " + _("{n} plans ratés (relancez « Fabriquer » pour eux seuls) : {e}", n=len(erreurs), e=erreurs[0][1][:200])
            self.etat.setText(msg)
        self._lancer(travail, _("Narration : fabrication des plans"), fin)

    def _voir_plan(self, r):
        if not self.narr or not 0 <= r < len(self.narr["plans"]):
            return
        f = self.narr["plans"][r].get("fichier")
        if f and os.path.exists(f):
            self.apercu.show()
            self.apercu.charger(f, video=True)
            self.apercu.fondu_e.hide()
            self.apercu.fondu_s.hide()
        else:
            self.apercu.arreter()
            self.apercu.hide()

    def poser(self):
        if not self.narr:
            return
        self.apercu.arreter()
        p = self.ed.projet
        p.marquer()
        n = NA.monter(p, self.narr)
        self.ed.rafraichir()
        self.etat.setText(_("✓ {n} plans posés au-dessus du film, chacun sous ses mots. Edition › Annuler pour revenir.", n=n))

    def closeEvent(self, ev):
        from .widgets import garder_calcul
        self.apercu.arreter()
        if garder_calcul(self, self._en_calcul()):
            ev.ignore()
            return
        if self.narr:
            self._lire_table()
            NA.enregistrer(self.narr)
        super().closeEvent(ev)

    def done(self, r):
        from .widgets import garder_calcul
        if garder_calcul(self, self._en_calcul()):
            return
        super().done(r)
