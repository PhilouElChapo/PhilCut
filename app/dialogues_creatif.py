"""Atelier IA (0.6, 0.7) : effets IA locaux sur une image du film, sur la partie en jaune, pour un logo ou une musique.

A gauche, le catalogue (par famille, cherchable) ; à droite, la phrase modifiable, la force, l'image source et le résultat
côte à côte. Rien ne part sur Internet ; « Créer » lance le moteur du poste en tâche de fond (barre du bas).
"""
import os, time

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton, QSlider, QSplitter, QVBoxLayout, QWidget)

from . import creatif as C, effets_ia as EI, moteur
from .langue import _
from .projet import fin_clip
from .taches import Tache


def _dossier_sorties():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "ia_creations")
    os.makedirs(d, exist_ok=True)
    return d


class DialogueAtelierIA(QDialog):
    def __init__(self, ed, famille="image"):
        super().__init__(ed)
        self.ed = ed
        self.setWindowTitle(_("Atelier IA (sur ce poste)"))
        self.resize(1040, 680)
        self.tache, self.resultat, self.source = None, None, None
        v = QVBoxLayout(self)
        aide = QLabel(_("Effets IA qui tournent sur votre ordinateur : gratuits, rien n'est envoyé. Choisissez un effet, modifiez sa phrase "
                        "si vous voulez (vos changements sont gardés), puis « Créer ». Sans carte graphique, comptez plus longtemps."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        sp = QSplitter(Qt.Horizontal)
        gauche = QWidget()
        vg = QVBoxLayout(gauche)
        vg.setContentsMargins(0, 0, 0, 0)
        self.famille = QComboBox()
        for k, lib in EI.FAMILLES.items():
            self.famille.addItem(lib, k)
        self.famille.setCurrentIndex(max(0, self.famille.findData(famille)))
        self.famille.currentIndexChanged.connect(self._remplir)
        vg.addWidget(self.famille)
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(_("Chercher un effet…"))
        self.cherche.textChanged.connect(self._remplir)
        vg.addWidget(self.cherche)
        self.liste = QListWidget()
        self.liste.currentItemChanged.connect(self._choisi)
        vg.addWidget(self.liste, 1)
        sp.addWidget(gauche)
        droite = QWidget()
        vd = QVBoxLayout(droite)
        vd.setContentsMargins(6, 0, 0, 0)
        self.titre = QLabel("")
        self.titre.setStyleSheet("font-weight:600;font-size:15px")
        vd.addWidget(self.titre)
        self.etat_modele = QLabel("")
        self.etat_modele.setWordWrap(True)
        vd.addWidget(self.etat_modele)
        self.lbl_prompt = QLabel(_("Phrase pour l'IA (en anglais, c'est mieux compris)"))
        vd.addWidget(self.lbl_prompt)
        self.prompt = QPlainTextEdit()
        self.prompt.setMaximumHeight(70)
        vd.addWidget(self.prompt)
        hf = QHBoxLayout()
        self.lbl_force = QLabel(_("Force"))
        hf.addWidget(self.lbl_force)
        self.force = QSlider(Qt.Horizontal)
        self.force.setRange(5, 100)
        hf.addWidget(self.force, 1)
        self.val_force = QLabel("")
        self.val_force.setMinimumWidth(130)
        self.force.valueChanged.connect(self._texte_force)
        hf.addWidget(self.val_force)
        vd.addLayout(hf)
        # musique
        self.boite_musique = QWidget()
        hm = QHBoxLayout(self.boite_musique)
        hm.setContentsMargins(0, 0, 0, 0)
        hm.addWidget(QLabel(_("Durée")))
        self.duree = QDoubleSpinBox()
        self.duree.setRange(10, 240)
        self.duree.setSuffix(" s")
        self.duree.setValue(max(10.0, min(240.0, round(self.ed.projet.duree() or 60.0))))
        hm.addWidget(self.duree)
        self.instrumental = QCheckBox(_("Sans paroles"))
        self.instrumental.setChecked(True)
        hm.addWidget(self.instrumental)
        self.paroles = QLineEdit()
        self.paroles.setPlaceholderText(_("Paroles (facultatif ; décochez « Sans paroles »)"))
        self.paroles.setEnabled(False)
        self.instrumental.toggled.connect(lambda v: self.paroles.setEnabled(not v))
        hm.addWidget(self.paroles, 1)
        vd.addWidget(self.boite_musique)
        hi = QHBoxLayout()
        self.img_source = QLabel()
        self.img_resultat = QLabel()
        for lb, t in ((self.img_source, _("Image du film (tête de lecture)")), (self.img_resultat, _("Résultat"))):
            lb.setFixedSize(360, 203)
            lb.setAlignment(Qt.AlignCenter)
            lb.setStyleSheet("background:#000;border-radius:6px;color:#888")
            lb.setText(t)
            hi.addWidget(lb)
        hi.addStretch(1)
        vd.addLayout(hi)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        vd.addWidget(self.info)
        hb = QHBoxLayout()
        self.b_creer = QPushButton(_("Créer"))
        self.b_creer.setStyleSheet("font-weight:600;padding:6px 18px")
        self.b_creer.clicked.connect(self.creer)
        hb.addWidget(self.b_creer)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.hide()
        self.b_arreter.clicked.connect(self.arreter)
        hb.addWidget(self.b_arreter)
        self.b_garder = QPushButton(_("Garder ma phrase"))
        self.b_garder.setToolTip(_("La phrase et la force modifiées remplacent celles de l'effet (« Rétablir » revient à l'original)."))
        self.b_garder.clicked.connect(lambda: self._enregistrer(False))
        hb.addWidget(self.b_garder)
        self.b_nouveau = QPushButton(_("Enregistrer comme mon effet"))
        self.b_nouveau.clicked.connect(lambda: self._enregistrer(True))
        hb.addWidget(self.b_nouveau)
        self.b_retablir = QPushButton(_("Rétablir"))
        self.b_retablir.clicked.connect(self._retablir)
        hb.addWidget(self.b_retablir)
        hb.addStretch(1)
        vd.addLayout(hb)
        self.actions = QHBoxLayout()
        vd.addLayout(self.actions)
        vd.addStretch(1)
        b_pref = QPushButton(_("Modèles IA du poste (Préférences)…"))
        b_pref.setStyleSheet("text-align:left;padding:3px 8px")
        b_pref.clicked.connect(self._preferences)
        hp = QHBoxLayout()
        hp.addWidget(b_pref)
        hp.addStretch(1)
        vd.addLayout(hp)
        sp.addWidget(droite)
        sp.setSizes([290, 750])
        v.addWidget(sp, 1)
        self._remplir()
        self._charger_source()

    # ---- catalogue
    def _remplir(self, *_a):
        fam = self.famille.currentData()
        txt = self.cherche.text().strip().lower()
        self.liste.blockSignals(True)
        self.liste.clear()
        for e in EI.tous(self.ed.params):
            if e["famille"] != fam or (txt and txt not in e["nom"].lower() and txt not in e.get("prompt", "").lower()):
                continue
            ok, _m = EI.disponible(e, self.ed.params)
            it = QListWidgetItem(("★ " if e.get("perso") else "") + e["nom"] + ("" if ok else "  ⚠"))
            it.setData(Qt.UserRole, e)
            if not ok:
                it.setToolTip(_m)
            self.liste.addItem(it)
        self.liste.blockSignals(False)
        if self.liste.count():
            self.liste.setCurrentRow(0)
        self._choisi(self.liste.currentItem(), None)

    def effet(self):
        it = self.liste.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _choisi(self, it, _avant=None):
        e = it.data(Qt.UserRole) if it else None
        if not e:
            return
        self.titre.setText(e["nom"])
        ok, manque = EI.disponible(e, self.ed.params)
        self.etat_modele.setText(("✓ " + _("Prêt sur ce poste.")) if ok else ("⚠ " + manque))
        self.etat_modele.setStyleSheet("color:#7fd18b" if ok else "color:#ffb347")
        avec_phrase = e["moteur"] in ("image", "video", "musique")
        self.prompt.setVisible(avec_phrase)
        self.lbl_prompt.setVisible(avec_phrase)
        self.prompt.setPlainText(e.get("prompt", ""))
        self.boite_musique.setVisible(e["moteur"] == "musique")
        reglable = e["moteur"] in ("image", "profondeur", "photo3d", "upscale", "interpolation", "video", "transition3d")
        for w in (self.force, self.lbl_force, self.val_force):
            w.setVisible(reglable)
        f = float(e.get("force", 0.5))
        self.force.blockSignals(True)
        self.force.setValue(int({"profondeur": f / 30, "photo3d": f / 0.15, "upscale": f / 4, "interpolation": f / 8, "video": f / 5, "transition3d": f / 2}.get(e["moteur"], f) * 100))
        self.force.blockSignals(False)
        self._texte_force()
        self.img_source.setVisible(e["famille"] != "musique" and not e.get("sans_source"))
        self.img_resultat.setVisible(e["famille"] != "musique")
        self.b_garder.setEnabled(avec_phrase or reglable)
        self.b_retablir.setEnabled(bool(e.get("modifie")))
        self.info.setText(self._explication(e))

    def _valeur_force(self, e=None):
        e = e or self.effet() or {}
        x = self.force.value() / 100
        return {"profondeur": round(x * 30), "photo3d": round(x * 0.15, 3), "upscale": 4 if x > 0.75 else 2,
                "interpolation": 8 if x > 0.75 else (4 if x > 0.35 else 2), "video": round(1 + x * 4, 1),
                "transition3d": round(max(0.6, x * 2), 1)}.get(e.get("moteur"), round(x, 2))

    def _texte_force(self):
        e = self.effet() or {}
        v = self._valeur_force(e)
        self.val_force.setText({"image": _("{p} % de l'image refaite", p=int(v * 100)), "profondeur": _("flou {v}", v=v),
                                "photo3d": _("mouvement {p} %", p=int(v * 100)), "upscale": f"×{v}", "interpolation": _("ralenti ×{v}", v=v),
                                "video": _("{v} s", v=v), "transition3d": _("{v} s", v=v)}.get(e.get("moteur"), str(v)))

    def _explication(self, e):
        m = e["moteur"]
        if e["famille"] == "video":
            z = self._partie()
            ou = _("de {a} à {b}", a=_tc(z[0]), b=_tc(z[1])) if z else _("— placez la tête de lecture sur un plan ou choisissez une partie en jaune")
            if m == "transition3d":
                return _("La caméra plonge dans la dernière image du plan qui part et ressort de la première du suivant ; le clip est posé "
                         "au-dessus du raccord le plus proche de la tête de lecture.")
            if m in ("photo3d", "video"):
                return _("A partir de l'image à la tête de lecture ; le clip créé est posé au-dessus (piste Vidéo 2).")
            return _("Passage traité : {o}. Le résultat est posé au-dessus, sur la piste Vidéo 2 (supprimable, l'original reste).", o=ou)
        if e["famille"] == "musique":
            return _("Le morceau est posé sur la piste Musique, à la durée choisie, avec des fondus.")
        if e.get("sans_source"):
            return _("Image créée à partir de la phrase seule.")
        return _("L'image du film à la tête de lecture est redessinée selon la phrase ; « Force » règle combien elle change.")

    def _enregistrer(self, nouveau):
        e = self.effet()
        if not e:
            return
        nom = None
        if nouveau:
            from PySide6.QtWidgets import QInputDialog
            nom, ok = QInputDialog.getText(self, _("Mon effet"), _("Nom de l'effet"), text=e["nom"])
            if not ok or not nom.strip():
                return
        EI.enregistrer(self.ed.params, e, self.prompt.toPlainText().strip(), self._valeur_force(e), nom, nouveau)
        self._remplir()
        self.info.setText(_("Effet enregistré."))

    def _retablir(self):
        e = self.effet()
        if e:
            EI.retablir(self.ed.params, e["id"])
            self._remplir()

    def _preferences(self):
        f = self.ed.window()
        if hasattr(f, "preferences"):
            f.preferences("IA locale")
        self._remplir()

    # ---- source
    def _charger_source(self):
        from .dialogues_video import image_projet
        t = self.ed.timeline.position
        png = image_projet(self.ed.projet, t, 768)
        if png:
            chemin = os.path.join(_dossier_sorties(), "_source.png")
            with open(chemin, "wb") as f:
                f.write(png)
            self.source = chemin
            px = QPixmap(chemin)
            self.img_source.setPixmap(px.scaled(360, 203, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _raccord(self):
        """(dernière image du plan qui part, première du plan qui arrive, instant du raccord) le plus proche de la tête."""
        import cv2
        import numpy as np
        t = self.ed.timeline.position
        cs = sorted(self.ed.projet.clips_piste("video"), key=lambda c: c["debut"])
        paires = [(a, b) for a, b in zip(cs, cs[1:]) if abs(fin_clip(a) - b["debut"]) < 0.05]
        if not paires:
            return None
        a, b = min(paires, key=lambda p: abs(p[1]["debut"] - t))
        imgs = []
        for c, instant in ((a, float(a["src_fin"]) - 0.05), (b, float(b["src_debut"]) + 0.02)):
            med = self.ed.projet.media(c["media"])
            if not med:
                return None
            if med.get("genre") == "image":
                imgs.append(cv2.imread(med["chemin"]))
            else:
                png = moteur.image(med["chemin"], max(0.0, instant), 960)
                imgs.append(cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR))
        return imgs[0], imgs[1], b["debut"]

    def _partie(self):
        tl = self.ed.timeline
        z = tl.zone_valide() if hasattr(tl, "zone_valide") else None
        if z:
            return z
        c = self.ed.projet.clip_a(tl.position, "video")
        if c:
            return (c["debut"], min(fin_clip(c), c["debut"] + 10.0))
        return None

    # ---- création
    def creer(self):
        e = self.effet()
        if not e:
            return
        ok, manque = EI.disponible(e, self.ed.params)
        if not ok:
            self.info.setText("⚠ " + manque)
            return
        prompt, force, params = self.prompt.toPlainText().strip(), self._valeur_force(e), self.ed.params
        horo = time.strftime("%Y%m%d_%H%M%S")
        projet = self.ed.projet
        m = e["moteur"]
        if e["famille"] == "musique":
            sortie = os.path.join(_dossier_sorties(), f"musique_{horo}.mp3")
            duree, instr, paroles = self.duree.value(), self.instrumental.isChecked(), self.paroles.text()
            travail = lambda t: C.musique(prompt, sortie, duree, params, instr, paroles, progression=t.avancer, arret=t.arret_demande)
        elif e["famille"] in ("image", "logo"):
            if not e.get("sans_source") and not self.source:
                self.info.setText(_("Placez la tête de lecture sur une image du film."))
                return
            sortie = os.path.join(_dossier_sorties(), f"{e['id']}_{horo}.png")
            init = None if e.get("sans_source") else self.source
            travail = lambda t: C.image(prompt, sortie, params, init=init, force=force, progression=t.avancer, arret=t.arret_demande)
        else:
            sortie = os.path.join(_dossier_sorties(), f"{e['id']}_{horo}.mp4")
            if m == "transition3d":
                r = self._raccord()
                if not r:
                    self.info.setText(_("Placez la tête de lecture près d'un raccord entre deux plans de la piste Vidéo 1."))
                    return
                img_a, img_b, coupe = r
                travail = lambda t: C.transition_3d(img_a, img_b, sortie, force, projet.cadence, params, t.avancer)
                self._pose_tr = coupe - force / 2
            elif m in ("photo3d", "video"):
                if not self.source:
                    self.info.setText(_("Placez la tête de lecture sur une image du film."))
                    return
                src = self.source
                if m == "photo3d":
                    import cv2
                    travail = lambda t: C.photo_3d(cv2.imread(src), sortie, 3.0, projet.cadence, amplitude=force, params=params, progression=t.avancer)
                else:
                    travail = lambda t: C.video(prompt, sortie, params, init=src, secondes=force, progression=t.avancer, arret=t.arret_demande)
            else:
                z = self._partie()
                c = projet.clip_a(z[0] + 0.01, "video") if z else None
                med = projet.media(c["media"]) if c else None
                if not med or med.get("genre") != "video":
                    self.info.setText(_("Choisissez une partie en jaune (ou placez la tête de lecture) sur un plan vidéo."))
                    return
                v = float(c.get("vitesse", 1.0) or 1.0)
                debut = float(c["src_debut"]) + (z[0] - c["debut"]) * v
                duree = (min(z[1], fin_clip(c)) - z[0]) * v
                chemin, ips = med["chemin"], projet.cadence
                if m == "anime":
                    cle = None
                    travail = lambda t: C.traiter_video(chemin, sortie, lambda img: C.anime_image(img, cle, params), debut, duree, ips,
                                                        progression=t.avancer, arret=t.arret_demande)
                elif m == "profondeur":
                    travail = lambda t: C.traiter_video(chemin, sortie, lambda img: C.flou_arriere_plan(img, force, params), debut, duree, ips,
                                                        progression=t.avancer, arret=t.arret_demande)
                elif m == "upscale":
                    travail = lambda t: C.agrandir(chemin, sortie, int(force), debut, duree, ips, params, t.avancer, t.arret_demande)[0]
                else:
                    travail = lambda t: C.ralentir(chemin, sortie, int(force), debut, duree, ips, params, t.avancer, t.arret_demande)
                self._pose = z[0]
        if m == "transition3d":
            self._pose = self._pose_tr
        else:
            self._pose = getattr(self, "_pose", None) if e["famille"] == "video" and m not in ("photo3d", "video") else self.ed.timeline.position
        self.tache = Tache(travail, _("Atelier IA"))
        self.ed.taches.append(self.tache)
        self.ed.encart.suivre(self.tache, _("IA locale : {n}", n=e["nom"]))
        self.tache.fini.connect(lambda r, err, e=e: self._fini(e, r, err))
        self.b_creer.setEnabled(False)
        self.b_arreter.show()
        self.info.setText(_("Création en cours sur ce poste… vous pouvez continuer à travailler ; la barre du bas suit l'avancement."))
        self.tache.start()

    def arreter(self):
        if self.tache is not None:
            self.tache.stopper()

    def _vider_actions(self):
        while self.actions.count():
            it = self.actions.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def _action(self, texte, fonction):
        b = QPushButton(texte)
        b.clicked.connect(fonction)
        self.actions.addWidget(b)

    def _fini(self, e, r, err):
        self.b_creer.setEnabled(True)
        self.b_arreter.hide()
        self._vider_actions()
        if err:
            self.info.setText(_("✕ {e}", e=str(err)[:500]))
            return
        self.resultat = r if isinstance(r, str) else (r[0] if isinstance(r, (tuple, list)) else r)
        if e["famille"] in ("image", "logo"):
            px = QPixmap(self.resultat)
            self.img_resultat.setPixmap(px.scaled(360, 203, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.info.setText(_("Image créée. Choisissez ce que vous en faites :"))
            self._action(_("Insérer à la tête de lecture (3 s)"), lambda: self.ed.inserer_image(self.resultat, self._pose, 3.0, e["nom"]))
            self._action(_("Ajouter aux médias"), lambda: self.ed.importer([self.resultat]))
            self._action(_("Logo dans la Fabrique…"), lambda: self.ed.window().fabrique(image=self.resultat))
            self._action(_("Enregistrer en JPG (miniature)…"), self._enregistrer_jpg)
        elif e["famille"] == "musique":
            self.info.setText(_("Musique créée et posée sur la piste Musique."))
            self.ed._piste_depot = ("audio", 0.0, {"volume": 0.8, "fondu_entree": 1.5, "fondu_sortie": 3.0, "_couper_fin": True})
            self.ed.importer([self.resultat])
        else:
            png = moteur.image(self.resultat, 0.5, 360)
            px = QPixmap()
            px.loadFromData(png)
            self.img_resultat.setPixmap(px.scaled(360, 203, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.ed.poser_au_dessus(self.resultat, self._pose or 0.0, e["nom"])
            self.info.setText(_("Clip créé et posé au-dessus, sur la piste Vidéo 2 : supprimez-le pour revenir à l'original."))

    def _enregistrer_jpg(self):
        from .session import dossier_systeme
        p, _f = QFileDialog.getSaveFileName(self, _("Miniature"), os.path.join(self.ed.params.get("dossier_images") or dossier_systeme("images"),
                                                                                 "miniature.jpg"), "JPEG (*.jpg)")
        if p:
            moteur.lancer(["-y", "-i", self.resultat, "-q:v", "2", p if p.lower().endswith(".jpg") else p + ".jpg"])
            self.info.setText(_("Miniature enregistrée."))

    def done(self, r):
        if self.tache is not None and self.tache.isRunning():
            self.info.setText(_("La création continue en tâche de fond ; le résultat arrivera dans le projet."))
        super().done(r)


def _tc(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"
