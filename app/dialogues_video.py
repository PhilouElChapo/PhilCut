"""Fenetres de PhilCut : titre, effets d'un plan, Goodie, vitesse, export, Fabrique, fiche video."""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTreeWidget, QTreeWidgetItem, QMenu,
                               QCheckBox, QPushButton, QDialogButtonBox, QListWidget, QListWidgetItem, QColorDialog, QSlider, QGroupBox,
                               QPlainTextEdit, QFileDialog, QTabWidget, QWidget, QMessageBox, QProgressBar, QTextBrowser, QRadioButton)

from . import effets as E, goodies as GO, moteur, fabrique
from .icones import icone
from .langue import _
from .widgets import boutons_fr

ANIMATIONS = [("fondu", _("Fondu")), ("zoom", _("Zoom")), ("glisse", _("Glissé")), ("machine", _("Machine à écrire")), ("neon", _("Néon")),
              ("feu", _("Feu")), ("tournoyant", _("Tournoyant")), ("cinetique", _("Mots au rythme")), ("aucune", _("Aucune"))]


class DialogueTitre(QDialog):
    def __init__(self, parent, titre=None, position=0.0, duree_projet=10.0, medias_visages=()):
        super().__init__(parent)
        self.setWindowTitle(_("Texte") if titre is None else _("Modifier le texte"))
        self.setMinimumWidth(460)
        t = titre or {"texte": "", "debut": position, "fin": position + 3.0, "style": "titre", "animation": "fondu", "x": 0.5, "y": 0.85, "taille": 1.0, "couleur": "#ffffff"}
        self.t = t
        f = QFormLayout(self)
        self.texte = QPlainTextEdit(t.get("texte", ""))
        self.texte.setMaximumHeight(70)
        f.addRow(_("Texte"), self.texte)
        self.style = QComboBox()
        self.style.addItem(_("Titre"), "titre")
        self.style.addItem(_("Etiquette (accrochée)"), "etiquette")
        self.style.setCurrentIndex(1 if t.get("style") == "etiquette" else 0)
        f.addRow(_("Style"), self.style)
        self.anim = QComboBox()
        for k, lib in ANIMATIONS:
            self.anim.addItem(lib, k)
        self.anim.setCurrentIndex(max(0, [k for k, _l in ANIMATIONS].index(t.get("animation", "fondu")) if t.get("animation", "fondu") in [k for k, _l in ANIMATIONS] else 0))
        f.addRow(_("Animation"), self.anim)
        h = QHBoxLayout()
        self.debut = QDoubleSpinBox()
        self.debut.setRange(0, 36000)
        self.debut.setDecimals(2)
        self.debut.setSuffix(" s")
        self.debut.setValue(float(t.get("debut", 0)))
        self.fin = QDoubleSpinBox()
        self.fin.setRange(0, 36000)
        self.fin.setDecimals(2)
        self.fin.setSuffix(" s")
        self.fin.setValue(float(t.get("fin", 3)))
        h.addWidget(QLabel(_("de")))
        h.addWidget(self.debut)
        h.addWidget(QLabel(_("à")))
        h.addWidget(self.fin)
        f.addRow(_("Moment"), h)
        h2 = QHBoxLayout()
        self.x = QSlider(Qt.Horizontal)
        self.x.setRange(0, 100)
        self.x.setValue(int(float(t.get("x", 0.5)) * 100))
        self.y = QSlider(Qt.Horizontal)
        self.y.setRange(0, 100)
        self.y.setValue(int(float(t.get("y", 0.85)) * 100))
        h2.addWidget(QLabel("←→"))
        h2.addWidget(self.x)
        h2.addWidget(QLabel("↑↓"))
        h2.addWidget(self.y)
        f.addRow(_("Position"), h2)
        self.taille = QDoubleSpinBox()
        self.taille.setRange(0.3, 3.0)
        self.taille.setSingleStep(0.1)
        self.taille.setValue(float(t.get("taille", 1.0)))
        f.addRow(_("Taille"), self.taille)
        hc = QHBoxLayout()
        self.couleur = t.get("couleur", "#ffffff")
        self.b_coul = QPushButton()
        self._coul()
        self.b_coul.clicked.connect(self._choisir)
        hc.addWidget(self.b_coul)
        hc.addStretch(1)
        f.addRow(_("Couleur"), hc)
        from .titres import EFFETS_TEXTE
        from PySide6.QtWidgets import QFontComboBox
        from PySide6.QtGui import QFont
        he = QHBoxLayout()
        self.effet = QComboBox()
        for k, lib in EFFETS_TEXTE:
            self.effet.addItem(_(lib), k)
        self.effet.setCurrentIndex(max(0, self.effet.findData(t.get("effet_texte") or "aucun")))
        self.couleur2 = t.get("couleur2") or ""
        self.b_coul2 = QPushButton(_("Couleur de l'effet"))
        self.b_coul2.clicked.connect(self._choisir2)
        self._coul2()
        he.addWidget(self.effet, 1)
        he.addWidget(self.b_coul2)
        f.addRow(_("Effet du texte"), he)
        self.police = QFontComboBox()
        self.police.setCurrentFont(QFont(t.get("police") or "Nunito"))
        f.addRow(_("Police"), self.police)
        self.suivre = QComboBox()
        self.suivre.addItem(_("Non"), None)
        for m, boite in medias_visages:
            self.suivre.addItem(_("Suivre le visage dans « {n} »", n=m["nom"]), (m["id"], boite))
        if t.get("suivi"):
            self.suivre.setCurrentIndex(max(0, self.suivre.count() - 1))
        f.addRow(_("Suivre une personne"), self.suivre)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _coul(self):
        self.b_coul.setText(self.couleur)
        self.b_coul.setStyleSheet(f"background:{self.couleur};color:{'#000' if QColor(self.couleur).lightness() > 128 else '#fff'};padding:4px 14px")

    def _choisir(self):
        c = QColorDialog.getColor(QColor(self.couleur), self, _("Couleur du texte"))
        if c.isValid():
            self.couleur = c.name()
            self._coul()

    def _coul2(self):
        if self.couleur2:
            self.b_coul2.setStyleSheet(f"background:{self.couleur2};color:{'#000' if QColor(self.couleur2).lightness() > 128 else '#fff'};padding:4px 10px")

    def _choisir2(self):
        c = QColorDialog.getColor(QColor(self.couleur2 or "#000000"), self, _("Couleur du contour, de l'ombre ou de la lueur"))
        if c.isValid():
            self.couleur2 = c.name()
            self._coul2()

    def resultat(self):
        t = dict(self.t)
        t.update(texte=self.texte.toPlainText().strip(), style=self.style.currentData(), animation=self.anim.currentData(),
                 debut=self.debut.value(), fin=max(self.debut.value() + 0.3, self.fin.value()), x=self.x.value() / 100, y=self.y.value() / 100,
                 taille=self.taille.value(), couleur=self.couleur, effet_texte=self.effet.currentData(), couleur2=self.couleur2,
                 police=self.police.currentFont().family())
        s = self.suivre.currentData()
        if s:
            t["suivi"] = {"media": s[0], "boite": s[1], "positions": []}
            t["style"] = "etiquette"
        elif t.get("suivi") and self.suivre.currentIndex() == 0:
            t["suivi"] = None
        return t


class DialogueEffets(QDialog):
    """Effets et transition d'un plan : catalogue a gauche, poses a droite, parametres en bas."""

    def __init__(self, parent, clip, params, medias=()):
        super().__init__(parent)
        self.setWindowTitle(_("Effets et transition — {n}", n=clip.get("nom", "")))
        self.resize(820, 560)
        self.clip = clip
        self.params = params
        self.medias = medias
        self.effets = [dict(e) for e in clip.get("effets") or []]
        self.transition = dict(clip["transition"]) if clip.get("transition") else None
        v = QVBoxLayout(self)
        h = QHBoxLayout()
        gauche = QVBoxLayout()
        mode = QLabel(_("<b>1.</b> Cliquez un effet du catalogue : son aperçu se fabrique sur votre plan (à droite). "
                        "<b>2.</b> « Poser sur ce plan » (ou double-clic). <b>3.</b> Réglez-le, puis <b>OK</b>."))
        mode.setWordWrap(True)
        v.addWidget(mode)
        gauche.addWidget(QLabel(_("<b>Catalogue</b>")))
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(_("Rechercher un effet…"))
        self.recherche.setClearButtonEnabled(True)
        gauche.addWidget(self.recherche)
        self.cat = QTreeWidget()
        self.cat.setHeaderHidden(True)
        self.cat.setIndentation(14)
        self.cat.setAnimated(True)
        self.cat.setContextMenuPolicy(Qt.CustomContextMenu)
        self.cat.customContextMenuRequested.connect(self._menu_catalogue)
        self._remplir_catalogue()
        self.recherche.textChanged.connect(self._filtrer_catalogue)
        self.cat.itemDoubleClicked.connect(self._poser)
        self.cat.currentItemChanged.connect(lambda it, _p: self._choisi(it))
        gauche.addWidget(self.cat, 1)
        self.b_poser = QPushButton(_("Poser sur ce plan →"))
        self.b_poser.setEnabled(False)
        self.b_poser.clicked.connect(lambda: self.cat.currentItem() and self._poser(self.cat.currentItem()))
        hp = QHBoxLayout()
        hp.addWidget(self.b_poser)
        hp.addStretch(1)
        gauche.addLayout(hp)
        h.addLayout(gauche, 1)
        droite = QVBoxLayout()
        droite.addWidget(QLabel(_("<b>Sur ce plan</b>")))
        self.poses = QListWidget()
        self.poses.currentRowChanged.connect(self._parametres)
        droite.addWidget(self.poses, 1)
        hb = QHBoxLayout()
        b_ret = QPushButton(_("Retirer"))
        b_ret.clicked.connect(self._retirer)
        hb.addWidget(b_ret)
        b_haut = QPushButton("↑")
        b_haut.clicked.connect(lambda: self._bouger(-1))
        hb.addWidget(b_haut)
        b_bas = QPushButton("↓")
        b_bas.clicked.connect(lambda: self._bouger(1))
        hb.addWidget(b_bas)
        hb.addStretch(1)
        droite.addLayout(hb)
        self.grp = QGroupBox(_("Réglages"))
        self.form = QFormLayout(self.grp)
        droite.addWidget(self.grp)
        h.addLayout(droite, 1)
        # ---- aperçu : quelques secondes du plan, rendues avec les effets
        apercu = QVBoxLayout()
        apercu.addWidget(QLabel(_("<b>Aperçu sur votre plan</b>")))
        self.ecran = None
        self.lecteur = None
        try:
            from PySide6.QtMultimedia import QMediaPlayer
            from PySide6.QtMultimediaWidgets import QVideoWidget
            if not params.get("apercu_images"):
                self.ecran = QVideoWidget()
                self.ecran.setMinimumSize(320, 200)
                self.lecteur = QMediaPlayer(self)
                self.lecteur.setVideoOutput(self.ecran)
                self.lecteur.setLoops(QMediaPlayer.Infinite)
                apercu.addWidget(self.ecran, 1)
        except Exception:       # noqa: BLE001
            self.ecran = None
        if self.ecran is None:
            self.ecran_image = QLabel()
            self.ecran_image.setMinimumSize(320, 200)
            self.ecran_image.setAlignment(Qt.AlignCenter)
            apercu.addWidget(self.ecran_image, 1)
        self.etat_apercu = QLabel(_("Choisissez un effet pour le voir."))
        self.etat_apercu.setWordWrap(True)
        self.etat_apercu.setStyleSheet("color:#999")
        apercu.addWidget(self.etat_apercu)
        hb2 = QHBoxLayout()
        self.b_apercu = QPushButton(_("↻ Revoir avec les réglages"))
        self.b_apercu.clicked.connect(lambda: self._apercu())
        hb2.addWidget(self.b_apercu)
        hb2.addStretch(1)
        apercu.addLayout(hb2)
        h.addLayout(apercu, 1)
        self._tache_apercu = None
        self._minuteur_apercu = QTimer(self)
        self._minuteur_apercu.setSingleShot(True)
        self._minuteur_apercu.timeout.connect(self._apercu)
        self.resize(1180, 620)
        v.addLayout(h, 1)
        self.aide = QLabel("")
        self.aide.setWordWrap(True)
        self.aide.setStyleSheet("color:#999")
        v.addWidget(self.aide)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._remplir()

    # ---- catalogue : familles dépliables, favoris, récents, recherche
    COULEURS_FAMILLES = {"look": "#d9a441", "wahou": "#b36cf2", "mouvement": "#5bb3ff", "transition": "#ffd24a", "personne": "#ff7ab3",
                         "matrix": "#43d17a", "correction": "#8fd3d8"}

    def _remplir_catalogue(self, filtre=""):
        from PySide6.QtGui import QBrush, QFont
        self.cat.clear()
        favoris = list(self.params.get("effets_favoris") or [])
        recents = list(self.params.get("effets_recents") or [])
        filtre = (filtre or "").strip().lower()

        def feuille(parent, k):
            fi = E.fiche(k)
            if not fi:
                return None
            lib = fi["nom"]
            if fi["pack"] and not E.pack_pret(fi["pack"], self.params):
                lib += _("  (pack « {p} » à télécharger)", p=E.PACKS.get(fi["pack"], {}).get("nom", fi["pack"]))
            if filtre and filtre not in lib.lower() and filtre not in fi["description"].lower():
                return None
            it = QTreeWidgetItem(parent, [("★ " if k in favoris else "") + lib])
            it.setData(0, Qt.UserRole, k)
            it.setToolTip(0, fi["description"])
            it.setIcon(0, icone("etoile" if k in favoris else {"transition": "fractionner", "look": "lumiere", "personne": "oeil"}.get(fi["famille"], "effets"),
                                self.COULEURS_FAMILLES.get(fi["famille"], "#ccc")))
            return it

        def famille(nom, cles, couleur, ouvert):
            if not cles:
                return
            racine = QTreeWidgetItem(self.cat, [nom])
            racine.setFlags(Qt.ItemIsEnabled)
            f = QFont()
            f.setBold(True)
            racine.setFont(0, f)
            racine.setForeground(0, QBrush(QColor(couleur)))
            n = 0
            for k in cles:
                if feuille(racine, k) is not None:
                    n += 1
            if n == 0:
                self.cat.invisibleRootItem().removeChild(racine)
                return
            racine.setText(0, f"{nom}  ({n})")
            racine.setExpanded(ouvert or bool(filtre))
        famille(_("★ Favoris"), favoris, "#ffd24a", True)
        famille(_("Récents"), [k for k in recents if k not in favoris][:8], "#aaa", True)
        deplies = set(self.params.get("effets_familles_ouvertes") or ["wahou", "transition"])
        for fam, nom in E.FAMILLES:
            famille(nom, E.par_famille().get(fam, []), self.COULEURS_FAMILLES.get(fam, "#ccc"), fam in deplies)
        self.cat.itemExpanded.connect(self._memoriser_familles)
        self.cat.itemCollapsed.connect(self._memoriser_familles)

    def _memoriser_familles(self, _it=None):
        noms = {nom: fam for fam, nom in E.FAMILLES}
        ouvertes = []
        for i in range(self.cat.topLevelItemCount()):
            r = self.cat.topLevelItem(i)
            base = r.text(0).rsplit("  (", 1)[0]
            if base in noms and r.isExpanded():
                ouvertes.append(noms[base])
        self.params["effets_familles_ouvertes"] = ouvertes

    def _filtrer_catalogue(self, texte):
        self._remplir_catalogue(texte)

    def _menu_catalogue(self, pos):
        it = self.cat.itemAt(pos)
        k = it.data(0, Qt.UserRole) if it else None
        if not k:
            return
        favoris = list(self.params.get("effets_favoris") or [])
        m = QMenu(self)
        m.addAction(_("Poser sur ce plan"), lambda: self._poser(it))
        m.addAction(_("Retirer des favoris") if k in favoris else _("★ Ajouter aux favoris"), lambda: self._favori(k))
        m.exec(self.cat.viewport().mapToGlobal(pos))

    def _favori(self, k):
        favoris = list(self.params.get("effets_favoris") or [])
        if k in favoris:
            favoris.remove(k)
        else:
            favoris.insert(0, k)
        self.params["effets_favoris"] = favoris
        self.params.enregistrer()
        self._remplir_catalogue(self.recherche.text())

    def _noter_recent(self, k):
        recents = [x for x in (self.params.get("effets_recents") or []) if x != k]
        recents.insert(0, k)
        self.params["effets_recents"] = recents[:12]
        self.params.enregistrer()

    def _choisi(self, it):
        k = it.data(0, Qt.UserRole) if it else None
        self.b_poser.setEnabled(bool(k))
        if not k:
            return
        fi = E.fiche(k)
        self.aide.setText(f"<b>{fi['nom']}</b> — {fi['description']}")
        self._essai = k
        self._minuteur_apercu.start(500)

    def _apercu(self):
        """Fabrique 2 à 3 s du plan avec les effets posés et l'effet choisi dans le catalogue, puis le joue en boucle."""
        ed = self.parent()
        projet = getattr(ed, "projet", None)
        if projet is None or not projet.clip(self.clip.get("id", "")):
            self.etat_apercu.setText(_("Aperçu indisponible ici."))
            return
        import tempfile
        from .taches import Tache
        from . import export
        effets = [dict(e) for e in self.effets]
        transition = self.transition
        k = getattr(self, "_essai", None)
        fi = E.fiche(k) if k else None
        if fi and not (fi["pack"] and not E.pack_pret(fi["pack"], self.params)):
            if fi["famille"] == "transition":
                transition = {"id": k, "params": dict(E.defauts(k))} if not (transition and transition["id"] == k) else transition
            elif not any(e["id"] == k for e in effets):
                effets.append({"id": k, "params": dict(E.defauts(k))})
        if self._tache_apercu is not None:
            self._tache_apercu.stopper()
        self._n_apercu = getattr(self, "_n_apercu", 0) + 1
        sortie = os.path.join(tempfile.gettempdir(), f"philcut_effet_{os.getpid()}_{self._n_apercu % 3}.mp4")
        t = getattr(getattr(ed, "timeline", None), "position", self.clip["debut"])
        nom = (fi or {}).get("nom") or _("vos effets")
        self.etat_apercu.setText(_("Fabrication de l'aperçu : {n}…", n=nom))
        tache = Tache(lambda tc: export.apercu_effet(projet, self.clip["id"], effets, transition, t, sortie, self.params,
                                                     arret=lambda: tc.arret), _("Aperçu d'effet"))
        self._tache_apercu = tache
        if hasattr(ed, "taches"):
            ed.taches.append(tache)
        from . import activite
        activite.centre().suivre(tache, _("Aperçu de l'effet « {n} »", n=nom))

        def fini(r, e, tache=tache):
            if tache is not self._tache_apercu:
                return
            self._tache_apercu = None
            try:
                if e:
                    self.etat_apercu.setText(_("Aperçu impossible : {e}", e=str(e)[:160]))
                    return
                pose = fi is None or any(x["id"] == k for x in self.effets) or (self.transition or {}).get("id") == k
                self.etat_apercu.setText(_("Aperçu : {n} (en boucle).", n=nom) + ("" if pose else _(" Pas encore posé : « Poser sur ce plan ».")))
                if self.lecteur is not None:
                    from PySide6.QtCore import QUrl
                    self.lecteur.setSource(QUrl.fromLocalFile(sortie))
                    self.lecteur.play()
                else:
                    from PySide6.QtGui import QPixmap
                    png = moteur.image(sortie, 1.0, 480)
                    pm = QPixmap()
                    pm.loadFromData(png)
                    self.ecran_image.setPixmap(pm.scaled(self.ecran_image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except RuntimeError:        # fenêtre déjà fermée
                pass
        tache.fini.connect(fini)
        tache.start()

    def done(self, r):
        if self._tache_apercu is not None:
            self._tache_apercu.stopper()
        if self.lecteur is not None:
            self.lecteur.stop()
        super().done(r)

    def _remplir(self):
        self.poses.clear()
        if self.transition:
            it = QListWidgetItem(_("Transition : {n}", n=E.fiche(self.transition["id"])["nom"]))
            it.setData(Qt.UserRole, ("transition", 0))
            self.poses.addItem(it)
        for i, e in enumerate(self.effets):
            fi = E.fiche(e["id"]) or {"nom": e["id"]}
            it = QListWidgetItem(fi["nom"])
            it.setData(Qt.UserRole, ("effet", i))
            self.poses.addItem(it)

    def _poser(self, it):
        k = it.data(0, Qt.UserRole) if it is not None else None
        if not k:
            return
        self._noter_recent(k)
        fi = E.fiche(k)
        if fi["pack"] and not E.pack_pret(fi["pack"], self.params):
            ou = _("Edition › Préférences › IA locale") if (E.PACKS.get(fi["pack"]) or {}).get("ia") else _("Edition › Préférences › Effets")
            QMessageBox.information(self, _("Pack à télécharger"), _("Cet effet a besoin du pack « {p} ». Cochez-le dans {o} ; "
                                                                      "il se télécharge alors dans le dossier de PhilCut.", p=E.PACKS.get(fi["pack"], {}).get("nom", fi["pack"]), o=ou))
            return
        if fi["famille"] == "transition":
            ed = self.parent()
            projet = getattr(ed, "projet", None)
            premier = projet is not None and not any(c["debut"] < self.clip["debut"] - 0.01 for c in projet.clips_piste(self.clip.get("piste", "video")))
            if premier:
                QMessageBox.information(self, _("Transition"), _("Une transition se pose sur le plan qui ARRIVE : elle fait le passage entre le plan "
                                                                 "d'avant et celui-ci. Ce plan est le premier de la timeline : choisissez plutôt le "
                                                                 "plan suivant (ou un effet « Fondu au noir » pour le début)."))
                return
            self.transition = {"id": k, "params": dict(E.defauts(k))}
            ligne = 0
        else:
            if not any(e["id"] == k for e in self.effets):
                self.effets.append({"id": k, "params": dict(E.defauts(k))})
            ligne = next(i for i, e in enumerate(self.effets) if e["id"] == k) + (1 if self.transition else 0)
        self._remplir()
        self.poses.setCurrentRow(ligne)
        self.aide.setText(_("✓ « {n} » est posé sur ce plan. Réglez-le ci-dessous, puis OK. Pour l'enlever : « Retirer ».", n=fi["nom"]))
        self._essai = None
        self._minuteur_apercu.start(300)

    def _courant(self):
        it = self.poses.currentItem()
        if not it:
            return None
        genre, i = it.data(Qt.UserRole)
        return self.transition if genre == "transition" else self.effets[i]

    def _retirer(self):
        it = self.poses.currentItem()
        if not it:
            return
        genre, i = it.data(Qt.UserRole)
        if genre == "transition":
            self.transition = None
        else:
            del self.effets[i]
        self._remplir()

    def _bouger(self, sens):
        it = self.poses.currentItem()
        if not it or it.data(Qt.UserRole)[0] != "effet":
            return
        i = it.data(Qt.UserRole)[1]
        j = i + sens
        if 0 <= j < len(self.effets):
            self.effets[i], self.effets[j] = self.effets[j], self.effets[i]
            self._remplir()
            self.poses.setCurrentRow(j + (1 if self.transition else 0))

    def _parametres(self, _row):
        while self.form.rowCount():
            self.form.removeRow(0)
        e = self._courant()
        if not e:
            self.aide.setText("")
            return
        fi = E.fiche(e["id"])
        self.aide.setText(fi["description"] if fi else "")
        for (cle, lib, genre, defaut, mini, maxi) in (fi["parametres"] if fi else []):
            val = (e.get("params") or {}).get(cle, defaut)
            if genre == "float":
                w = QDoubleSpinBox()
                w.setRange(float(mini), float(maxi))
                w.setSingleStep((float(maxi) - float(mini)) / 20 or 0.1)
                w.setValue(float(val))
                w.valueChanged.connect(lambda v, c=cle, e=e: e.setdefault("params", {}).__setitem__(c, v))
            elif genre == "int":
                w = QSpinBox()
                w.setRange(int(mini), int(maxi))
                w.setValue(int(val))
                w.valueChanged.connect(lambda v, c=cle, e=e: e.setdefault("params", {}).__setitem__(c, v))
            elif genre == "bool":
                w = QCheckBox()
                w.setChecked(bool(val))
                w.toggled.connect(lambda v, c=cle, e=e: e.setdefault("params", {}).__setitem__(c, v))
            elif genre == "choix":       # mini = liste (valeur, libellé)
                w = QComboBox()
                for v, l in mini:
                    w.addItem(l, v)
                    if v == val:
                        w.setCurrentIndex(w.count() - 1)
                w.currentIndexChanged.connect(lambda _i, w=w, c=cle, e=e: e.setdefault("params", {}).__setitem__(c, w.currentData()))
            elif genre == "media":
                w = QComboBox()
                w.addItem(_("(choisir)"), "")
                for m in self.medias:
                    w.addItem(m["nom"], m["id"])
                    if m["id"] == val:
                        w.setCurrentIndex(w.count() - 1)
                w.currentIndexChanged.connect(lambda _i, w=w, c=cle, e=e: e.setdefault("params", {}).__setitem__(c, w.currentData()))
            else:   # couleur
                w = QLineEdit(str(val))
                w.textChanged.connect(lambda v, c=cle, e=e: e.setdefault("params", {}).__setitem__(c, v))
            self.form.addRow(lib, w)

    def resultat(self):
        return self.effets, self.transition


class DialogueGoodie(QDialog):
    def __init__(self, parent, goodie=None, position=0.0, duree=10.0, params=None):
        super().__init__(parent)
        self.setWindowTitle(_("Goodie"))
        g = goodie or {"genre": "altimetre", "debut": position, "fin": min(duree, position + 10), "x": 0.88, "y": 0.85, "taille": 0.22, "style": "cadran", "valeurs": [], "options": {}}
        self.g = g
        f = QFormLayout(self)
        self.genre = QComboBox()
        coches = set((params or {}).get("goodies_coches") or ["aviation", "maison"])
        for pk, p in GO.PACKS.items():
            for gid in p["goodies"]:
                lib = f"{p['nom']} · {GO.GENRES.get(gid, (gid,))[0]}"
                self.genre.addItem(lib, gid)
                if gid == g.get("genre"):
                    self.genre.setCurrentIndex(self.genre.count() - 1)
        f.addRow(_("Goodie"), self.genre)
        self.style = QComboBox()
        self.style.addItem(_("Cadran (tableau de bord)"), "cadran")
        self.style.addItem(_("HUD épuré"), "hud")
        self.style.setCurrentIndex(1 if g.get("style") == "hud" else 0)
        f.addRow(_("Style"), self.style)
        h = QHBoxLayout()
        self.debut = QDoubleSpinBox()
        self.debut.setRange(0, 36000)
        self.debut.setSuffix(" s")
        self.debut.setValue(float(g["debut"]))
        self.fin = QDoubleSpinBox()
        self.fin.setRange(0, 36000)
        self.fin.setSuffix(" s")
        self.fin.setValue(float(g["fin"]))
        h.addWidget(self.debut)
        h.addWidget(QLabel("→"))
        h.addWidget(self.fin)
        f.addRow(_("Moment"), h)
        h2 = QHBoxLayout()
        self.x = QSlider(Qt.Horizontal)
        self.x.setRange(0, 100)
        self.x.setValue(int(float(g.get("x", 0.88)) * 100))
        self.y = QSlider(Qt.Horizontal)
        self.y.setRange(0, 100)
        self.y.setValue(int(float(g.get("y", 0.85)) * 100))
        h2.addWidget(self.x)
        h2.addWidget(self.y)
        f.addRow(_("Position"), h2)
        self.taille = QDoubleSpinBox()
        self.taille.setRange(0.06, 0.6)
        self.taille.setSingleStep(0.02)
        self.taille.setValue(float(g.get("taille", 0.22)))
        f.addRow(_("Taille (part de la hauteur)"), self.taille)
        self.texte = QLineEdit((g.get("options") or {}).get("texte", ""))
        f.addRow(_("Texte (badge, immatriculation…)"), self.texte)
        hi = QHBoxLayout()
        self.chemin_image = QLineEdit((g.get("options") or {}).get("chemin", ""))
        self.chemin_image.setPlaceholderText(_("Pour « Image ou logo » : un PNG transparent de préférence"))
        b_img = QPushButton(_("Image…"))
        b_img.clicked.connect(self._choisir_image)
        hi.addWidget(self.chemin_image, 1)
        hi.addWidget(b_img)
        f.addRow(_("Image"), hi)
        self.valeurs = QPlainTextEdit("\n".join(f"{t}\t{v}" for t, v in (g.get("valeurs") or [])))
        self.valeurs.setPlaceholderText(_("Valeurs saisies : une par ligne « seconde  valeur » (ex. 0  0 puis 60  2500). Vide = décor animé."))
        self.valeurs.setMaximumHeight(90)
        f.addRow(_("Valeurs"), self.valeurs)
        hg = QHBoxLayout()
        b_gpx = QPushButton(_("Depuis une trace GPX…"))
        b_gpx.clicked.connect(self._gpx)
        hg.addWidget(b_gpx)
        hg.addStretch(1)
        f.addRow(hg)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _choisir_image(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Image ou logo"), "", "Images (*.png *.jpg *.jpeg *.webp *.svg)")
        if p:
            self.chemin_image.setText(p)
            self.genre.setCurrentIndex(max(0, self.genre.findData("image")))

    def _gpx(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Trace GPX"), "", "GPX (*.gpx)")
        if not p:
            return
        pts = GO.depuis_gpx(p)
        if not pts:
            QMessageBox.warning(self, _("Trace GPX"), _("Aucun point horodaté dans ce fichier."))
            return
        genre = self.genre.currentData()
        idx = {"altimetre": 1, "altitude": 1, "anemometre": 2, "compteur": 2, "compas": 3, "boussole": 3}.get(genre, 1)
        d0 = self.debut.value()
        pas = max(1, len(pts) // 60)
        lignes = []
        for t, ele, v, cap, _la, _lo in pts[::pas]:
            val = [None, ele * (3.281 if genre == "altimetre" else 1), v * (0.54 if genre == "anemometre" else 1), cap][idx]
            lignes.append(f"{d0 + t:.1f}\t{val:.0f}")
        self.valeurs.setPlainText("\n".join(lignes))

    def resultat(self):
        g = dict(self.g)
        vals = []
        for l in self.valeurs.toPlainText().splitlines():
            parts = l.replace(",", ".").split()
            if len(parts) >= 2:
                try:
                    vals.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    pass
        opts = dict(g.get("options") or {})
        opts["texte"] = self.texte.text().strip()
        if self.chemin_image.text().strip():
            opts["chemin"] = self.chemin_image.text().strip()
        g.update(genre=self.genre.currentData(), style=self.style.currentData(), debut=self.debut.value(), fin=max(self.debut.value() + 0.5, self.fin.value()),
                 x=self.x.value() / 100, y=self.y.value() / 100, taille=self.taille.value(), valeurs=sorted(vals), options=opts)
        return g


class DialogueVitesse(QDialog):
    def __init__(self, parent, clip):
        super().__init__(parent)
        self.setWindowTitle(_("Vitesse — {n}", n=clip.get("nom", "")))
        f = QFormLayout(self)
        self.v = QDoubleSpinBox()
        self.v.setRange(0.1, 16.0)
        self.v.setSingleStep(0.25)
        self.v.setValue(float(clip.get("vitesse", 1.0)))
        f.addRow(_("Vitesse (×)"), self.v)
        h = QHBoxLayout()
        for lib, val in ((_("¼"), 0.25), (_("½"), 0.5), ("1", 1.0), ("2", 2.0), ("4", 4.0), ("8", 8.0)):
            b = QPushButton(lib)
            b.clicked.connect(lambda _c, val=val: self.v.setValue(val))
            h.addWidget(b)
        f.addRow(h)
        self.fluide = QCheckBox(_("Ralenti fluide (images intermédiaires calculées, export plus lent)"))
        self.fluide.setChecked(any(e["id"] == "ralenti_fluide" for e in clip.get("effets") or []))
        f.addRow(self.fluide)
        self.ramp = QCheckBox(_("Speed ramp : couper le plan en trois (lent · rapide · lent)"))
        f.addRow(self.ramp)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


class DialogueExport(QDialog):
    def __init__(self, parent, projet, params):
        super().__init__(parent)
        self.setWindowTitle(_("Exporter"))
        self.setMinimumWidth(520)
        self.projet, self.params = projet, params
        f = QFormLayout(self)
        self.dest = QComboBox()
        for k, d in moteur.DESTINATIONS.items():
            self.dest.addItem(d[0], k)
            if k == params.get("export_destination"):
                self.dest.setCurrentIndex(self.dest.count() - 1)
        f.addRow(_("Destination"), self.dest)
        self.enc = QComboBox()
        for e in moteur.encodeurs():
            self.enc.addItem(moteur.nom_encodeur(e), e)
        f.addRow(_("Encodeur"), self.enc)
        self.qualite = QComboBox()
        for k, lib in (("allegee", _("Allégée (petit fichier)")), ("normale", _("Normale")), ("haute", _("Haute"))):
            self.qualite.addItem(lib, k)
        self.qualite.setCurrentIndex(1)
        f.addRow(_("Qualité"), self.qualite)
        h = QHBoxLayout()
        nom = (projet.nom or "video").replace("/", "-") + ".mp4"
        from .session import dossier_systeme
        dossier = params.get("dernier_dossier_export") or dossier_systeme("videos")
        self.chemin = QLineEdit(os.path.join(dossier, nom))
        b = QPushButton(_("Parcourir…"))
        b.clicked.connect(self._parcourir)
        h.addWidget(self.chemin, 1)
        h.addWidget(b)
        f.addRow(_("Fichier"), h)
        self.srt = QCheckBox(_("Ecrire aussi les sous-titres en .srt (pour YouTube)"))
        f.addRow(self.srt)
        hd = QHBoxLayout()
        self.double = QCheckBox(_("Exporter aussi en"))
        self.dest2 = QComboBox()
        for k, d in moteur.DESTINATIONS.items():
            if k != "original":
                self.dest2.addItem(d[0], k)
        self.dest2.setCurrentIndex(max(0, self.dest2.findData("insta" if projet.taille[0] >= projet.taille[1] else "youtube")))
        self.double.setToolTip(_("Deux fichiers d'un coup : par exemple horizontal pour YouTube et vertical pour Instagram. "
                                 "Les plans qui suivent une personne la suivent dans les deux formats ; les autres passent en fond flou."))
        hd.addWidget(self.double)
        hd.addWidget(self.dest2, 1)
        f.addRow(hd)
        self.drive = QCheckBox(_("Déposer ensuite sur le Drive / NAS de synchronisation"))
        f.addRow(self.drive)
        self.info = QLabel(_("Durée : {d} · {n} plans", d=moteur.duree_texte(projet.duree()), n=len(projet.clips_piste("video"))))
        f.addRow(self.info)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Exporter"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _parcourir(self):
        p, _f = QFileDialog.getSaveFileName(self, _("Exporter la vidéo"), self.chemin.text(), "MP4 (*.mp4)")
        if p:
            self.chemin.setText(p if p.lower().endswith(".mp4") else p + ".mp4")


class DialogueFabrique(QDialog):
    """Logo / intro / fin anime, ou plan genere par IA."""

    def __init__(self, parent, projet, params, recette=None):
        super().__init__(parent)
        self.setWindowTitle(_("Fabrique"))
        self.resize(640, 520)
        self.projet, self.params, self.recette = projet, params, recette or projet.d.get("recette") or {}
        v = QVBoxLayout(self)
        intro = QLabel(_("<b>La Fabrique</b> crée ce que vos rushes n'ont pas : un <b>logo animé</b> ou une <b>intro</b> / <b>fin</b> de vidéo "
                         "(onglet 1), ou un <b>plan généré par IA</b> à partir d'une phrase, par exemple « survol des collines de Provence au "
                         "lever du soleil » (onglet 2). Le résultat arrive dans les médias du projet, prêt à poser sur la timeline. "
                         "Pour dessiner votre logo lui-même : Fabrique › Atelier de logo."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.onglets = QTabWidget()
        v.addWidget(self.onglets, 1)
        # ---- logo / intro
        w = QWidget()
        f = QFormLayout(w)
        self.texte = QLineEdit((self.recette.get("logo") or {}).get("texte") or params.get("chaine_nom") or "")
        f.addRow(_("Texte"), self.texte)
        self.sous = QLineEdit("")
        f.addRow(_("Sous-titre (facultatif)"), self.sous)
        self.modele = QComboBox()
        for k, lib in fabrique.MODELES_LOGO.items():
            self.modele.addItem(lib, k)
            if k == (self.recette.get("logo") or {}).get("modele"):
                self.modele.setCurrentIndex(self.modele.count() - 1)
        f.addRow(_("Animation"), self.modele)
        self.duree = QDoubleSpinBox()
        self.duree.setRange(1.0, 10.0)
        self.duree.setValue(float((self.recette.get("logo") or {}).get("duree") or 2.5))
        self.duree.setSuffix(" s")
        f.addRow(_("Durée"), self.duree)
        h = QHBoxLayout()
        self.image = QLineEdit("")
        self.image.setPlaceholderText(_("PNG ou SVG de votre logo (facultatif)"))
        b = QPushButton(_("Parcourir…"))
        b.clicked.connect(self._image)
        b_at = QPushButton(_("Créer dans l'atelier…"))
        b_at.setToolTip(_("Atelier de logo : gabarits, textes, formes, idées par Claude ou Gemini."))
        b_at.clicked.connect(self._atelier)
        h.addWidget(self.image, 1)
        h.addWidget(b)
        h.addWidget(b_at)
        f.addRow(_("Image du logo"), h)
        self.usage = QComboBox()
        self.usage.addItem(_("Au début (intro)"), "debut")
        self.usage.addItem(_("A la fin"), "fin")
        self.usage.addItem(_("Seulement dans la bibliothèque"), "biblio")
        f.addRow(_("Placer"), self.usage)
        self.onglets.addTab(w, _("Logo et intro"))
        # ---- plan IA
        w2 = QWidget()
        f2 = QFormLayout(w2)
        self.sujet = QPlainTextEdit("")
        self.sujet.setMaximumHeight(80)
        plans = self.recette.get("plans_a_generer") or []
        if plans:
            self.sujet.setPlainText(plans[0].get("consigne", ""))
        self.sujet.setPlaceholderText(_("Décrivez le plan : « plan aérien au-dessus de la baie de Cannes au lever du soleil »"))
        f2.addRow(_("Sujet"), self.sujet)
        self.style = QComboBox()
        self.style.setEditable(True)
        for s in fabrique.STYLES:
            self.style.addItem(s)
        self.style.setCurrentText(params.get("fabrique_style") or "")
        f2.addRow(_("Style"), self.style)
        self.duree_ia = QSpinBox()
        self.duree_ia.setRange(4, 8)
        self.duree_ia.setValue(8)
        self.duree_ia.setSuffix(" s")
        f2.addRow(_("Durée"), self.duree_ia)
        self.consigne = QPlainTextEdit("")
        self.consigne.setMaximumHeight(90)
        f2.addRow(_("Consigne prête"), self.consigne)
        b_c = QPushButton(_("Rédiger la consigne"))
        b_c.clicked.connect(self._consigne)
        f2.addRow(b_c)
        self.voie_flow = QRadioButton(_("Flow (votre abonnement) : PhilCut copie la consigne, ouvre Flow, puis récupère le clip dans le dossier surveillé"))
        self.voie_flow.setChecked(True)
        self.voie_veo = QRadioButton(_("Générateur IA payant avec votre clef (Google, fal.ai : Kling, Seedance…)"))
        from . import generateurs_video as GV
        dispo = {m["id"] for m in GV.disponibles(params)}
        self.voie_veo.setEnabled(bool(params.get("veo_actif")) and bool(dispo))
        f2.addRow(self.voie_flow)
        f2.addRow(self.voie_veo)
        self.modele_veo = QComboBox()
        for m in GV.modeles(params):
            lib = f"{m['nom']} — {m.get('prix_s', 0):.2f} $/s ({m.get('note', '')})"
            if m["id"] not in dispo:
                lib += "  — " + _("clef {f} à saisir", f=GV.FOURNISSEURS[m["fournisseur"]]["nom"].split(" (")[0])
            self.modele_veo.addItem(lib, m["id"])
            if m["id"] not in dispo:
                self.modele_veo.model().item(self.modele_veo.count() - 1).setEnabled(False)
        prems = next((i for i in range(self.modele_veo.count()) if self.modele_veo.itemData(i) in dispo), 0)
        self.modele_veo.setCurrentIndex(max(prems, self.modele_veo.findData("omni-720p") if "omni-720p" in dispo else prems))
        hm = QHBoxLayout()
        hm.addWidget(self.modele_veo, 1)
        b_conn = QPushButton(_("Connecter une IA…"))
        b_conn.clicked.connect(self._connecter)
        hm.addWidget(b_conn)
        f2.addRow(_("Modèle"), hm)
        self.prix = QLabel("")
        f2.addRow(self.prix)
        self.modele_veo.currentIndexChanged.connect(self._prix)
        self.duree_ia.valueChanged.connect(self._prix)
        self._prix()
        h3 = QHBoxLayout()
        self.dossier = QLineEdit(params.get("dossier_flow") or os.path.join(os.path.expanduser("~"), "Downloads"))
        b3 = QPushButton(_("Dossier…"))
        b3.clicked.connect(self._dossier)
        h3.addWidget(self.dossier, 1)
        h3.addWidget(b3)
        f2.addRow(_("Dossier surveillé"), h3)
        self.onglets.addTab(w2, _("Plan généré par IA"))
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Fabriquer"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def _image(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Image du logo"), "", "Images (*.png *.svg *.jpg *.jpeg)")
        if p:
            self.image.setText(p)

    def _atelier(self):
        from .dialogues_logo import DialogueLogo
        d = DialogueLogo(self, self.params, nom=self.texte.text().strip())
        if d.exec() == QDialog.Accepted and d.png:
            self.image.setText(d.png)

    def _dossier(self):
        p = QFileDialog.getExistingDirectory(self, _("Dossier où Flow dépose les clips"), self.dossier.text())
        if p:
            self.dossier.setText(p)

    def _consigne(self):
        self.consigne.setPlainText(fabrique.consigne_plan("illustration", self.sujet.toPlainText().strip(), self.style.currentText().strip(),
                                                          self.duree_ia.value(), self.projet.format))

    def _prix(self):
        from . import generateurs_video as GV
        m = GV.modele(self.modele_veo.currentData() or "", self.params)
        if not m:
            self.prix.setText("")
            return
        precision = _(" (le modèle choisit la durée, 3 à 10 s)") if m.get("duree_auto") else ""
        self.prix.setText(_("Prix estimé : jusqu'à {p} ${d} ; confirmation avant l'envoi.", p=GV.prix(m, self.duree_ia.value()), d=precision))

    def _connecter(self):
        from .dialogues_connexion_ia import DialogueConnexionIA
        if DialogueConnexionIA(self, self.params).exec() == QDialog.Accepted:
            self.reject()
            QMessageBox.information(self.parent(), _("Connecter une IA"), _("Clefs enregistrées : rouvrez la Fabrique pour choisir le modèle."))


class DialogueFiche(QDialog):
    def __init__(self, parent, media):
        super().__init__(parent)
        self.setWindowTitle(_("Fiche vidéo — {n}", n=media["nom"]))
        self.resize(640, 560)
        v = QVBoxLayout(self)
        t = QTextBrowser()
        a = media.get("analyse") or {}
        f = media.get("fiche") or {}
        lignes = [f"<h3>{media['nom']}</h3>", f"<p>{a.get('resume') or moteur.resume_fiche(f)}</p>"]
        vid = f.get("video") or {}
        if vid:
            lignes.append("<ul>" + "".join(f"<li>{k} : {val}</li>" for k, val in (
                (_("Définition"), f"{vid.get('largeur')}×{vid.get('hauteur')} ({a.get('format', '')})"), (_("Codec"), f"{vid.get('codec')} {vid.get('bits')} bits{' HDR' if vid.get('hdr') else ''}"),
                (_("Cadence réelle"), f"{vid.get('cadence')} i/s" + (_(" (variable — convertie en cadence fixe à l'import)") if vid.get('cadence_variable') else "")),
                (_("Rotation du téléphone"), f"{vid.get('rotation')}°"), (_("Appareil"), f.get("appareil") or "?"), (_("Date"), f"{a.get('date', '')} {a.get('heure', '')}"),
                (_("Son"), _("aucun / muet") if (a.get('son') or {}).get('muet', not f.get('audio')) else f"{(a.get('son') or {}).get('moyen_db', '?')} dB moyen, max {(a.get('son') or {}).get('max_db', '?')} dB"),
                (_("Lumière"), _("nuit") if (a.get('lumiere') or {}).get('nuit') else _("jour")), (_("Plans détectés"), a.get("plans", "?")),
                (_("Visages"), (a.get("visages") or {}).get("nb_max", 0)), (_("Couleurs dominantes"), ", ".join(f"{c} {int(p * 100)} %" for c, p in (a.get("couleurs") or []))),
            )) + "</ul>")
        if a.get("moments"):
            lignes.append("<p><b>" + _("Moments forts") + "</b> : " + ", ".join(f"{m['t']} s ({m['pourquoi']})" for m in a["moments"][:12]) + "</p>")
        if (a.get("lumiere") or {}).get("passages_noirs"):
            lignes.append("<p><b>" + _("Passages noirs à couper") + "</b> : " + ", ".join(f"{x}–{y} s" for x, y in a["lumiere"]["passages_noirs"]) + "</p>")
        if media.get("proxy"):
            lignes.append(f"<p style='color:#999'>{_('Proxy')} : {media['proxy']}</p>")
        t.setHtml("".join(lignes))
        v.addWidget(t)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Close))
        bb.rejected.connect(self.reject)
        bb.clicked.connect(self.reject)
        v.addWidget(bb)
