"""Fenetres de PhilCut : titre, effets d'un plan, Goodie, vitesse, export, Fabrique, fiche video."""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QTreeWidget, QTreeWidgetItem, QMenu,
                               QCheckBox, QPushButton, QDialogButtonBox, QListWidget, QListWidgetItem, QColorDialog, QSlider, QGroupBox,
                               QPlainTextEdit, QFileDialog, QTabWidget, QWidget, QMessageBox, QProgressBar, QTextBrowser, QRadioButton)

from . import effets as E, goodies as GO, moteur, fabrique, theme
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
        # style moderne animé (0.5.1) : même moteur que les intros, polices et courbes actuelles
        from . import intros as IN
        self.moderne = QComboBox()
        self.moderne.addItem(_("Aucun : texte classique (réglages ci-dessous)"), "")
        for k, (fam, lib, _d) in IN.MODELES.items():
            self.moderne.addItem(f"{IN.FAMILLES[fam]} — {lib}", k)
        self.moderne.setToolTip(_("Un style moderne animé remplace l'animation, la police et l'effet classiques ; le texte se règle ensuite "
                                  "dans l'Inspecteur (piste Goodies)."))
        self.sous_moderne = QLineEdit("")
        self.sous_moderne.setPlaceholderText(_("Sous-titre du style moderne (facultatif)"))
        self.sous_moderne.setEnabled(False)
        self.moderne.currentIndexChanged.connect(lambda _i: self.sous_moderne.setEnabled(bool(self.moderne.currentData())))
        if titre is None:
            f.addRow(_("Style moderne"), self.moderne)
            f.addRow("", self.sous_moderne)
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
        if self.poses.count():                           # effets déjà posés : le premier est choisi, ses réglages s'affichent
            self.poses.setCurrentRow(0)
        else:
            self._parametres(-1)

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
        # nom unique : sous Windows, le lecteur garde ouvert le fichier de l'aperçu précédent
        dossier_ap = os.path.join(tempfile.gettempdir(), f"philcut_apercus_{os.getpid()}")
        os.makedirs(dossier_ap, exist_ok=True)
        for vieux in sorted(os.listdir(dossier_ap))[:-4]:
            try:
                os.remove(os.path.join(dossier_ap, vieux))
            except OSError:
                pass
        sortie = os.path.join(dossier_ap, f"effet_{self._n_apercu:05d}.mp4")
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
                    self.etat_apercu.setText(_("Aperçu impossible : {e}", e=str(e)[:400]))
                    self.etat_apercu.setWordWrap(True)
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
            vide = QLabel(_("Posez d'abord l'effet (« Poser sur ce plan → » ou double-clic), puis cliquez-le dans « Sur ce plan » : "
                            "ses réglages apparaissent ici, et l'aperçu se refait à chaque changement."))
            vide.setWordWrap(True)
            vide.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
            self.form.addRow(vide)
            return
        fi = E.fiche(e["id"])
        self.aide.setText(fi["description"] if fi else "")
        if not (fi and fi["parametres"]):
            sans = QLabel(_("Cet effet n'a pas de réglage."))
            sans.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
            self.form.addRow(sans)
        from .inspecteur import widget_parametre
        for spec in (fi["parametres"] if fi else []):
            cle, lib = spec[0], spec[1]
            val = (e.get("params") or {}).get(cle, spec[3])

            def changer(v, c=cle, e=e):
                e.setdefault("params", {})[c] = v
                self._minuteur_apercu.start(600)          # l'aperçu se refait avec le nouveau réglage
            w = widget_parametre(spec, val, changer, self.medias)
            self.form.addRow(lib, w)

    def resultat(self):
        return self.effets, self.transition


class DialogueGoodie(QDialog):
    def __init__(self, parent, goodie=None, position=0.0, duree=10.0, params=None):
        super().__init__(parent)
        self.setWindowTitle(_("Goodie"))
        g = goodie or {"genre": "altimetre", "debut": position, "fin": min(duree, position + 10), "x": 0.88, "y": 0.85, "taille": 0.22, "style": "cadran", "valeurs": [], "options": {}}
        self.g = g
        self.ed = parent
        racine = QHBoxLayout(self)
        f = QFormLayout()
        racine.addLayout(f, 1)
        self._apercu_construire(racine)
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
        self.style.addItem(_("Cadran (tableau de bord) ou illustré animé"), "cadran")
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
        self.chemin_image.setPlaceholderText(_("PNG transparent de préférence"))
        b_img = QPushButton(_("Image…"))
        b_img.clicked.connect(self._choisir_image)
        hi.addWidget(self.chemin_image, 1)
        hi.addWidget(b_img)
        self.b_fond = QPushButton(_("Retirer le fond…"))
        self.b_fond.setToolTip(_("Un JPG (logo sur fond blanc, photo) devient une copie PNG transparente, sur ce poste"))
        self.b_fond.clicked.connect(self._retirer_fond)
        hi.addWidget(self.b_fond)
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
        # tout réglage se voit tout de suite dans l'aperçu animé
        for w, sig in ((self.genre, "currentIndexChanged"), (self.style, "currentIndexChanged"), (self.debut, "valueChanged"),
                       (self.fin, "valueChanged"), (self.x, "valueChanged"), (self.y, "valueChanged"), (self.taille, "valueChanged"),
                       (self.texte, "textChanged"), (self.chemin_image, "textChanged"), (self.valeurs, "textChanged")):
            getattr(w, sig).connect(lambda *_a: self._apercu_regle())
        self._apercu_regle()
        self._horloge.start()

    # ---- aperçu animé : le Goodie sur l'image du film, joué en boucle de son début à sa fin
    def _apercu_construire(self, racine):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QVBoxLayout
        va = QVBoxLayout()
        projet = getattr(self.ed, "projet", None)
        L, H = (projet.taille if projet is not None else (1920, 1080))
        self._ech = 420 / max(L, H)
        self._L, self._H = int(L * self._ech), int(H * self._ech)
        self.vue = QLabel()
        self.vue.setFixedSize(self._L, self._H)
        self.vue.setStyleSheet("background:#000;border-radius:6px")
        va.addWidget(QLabel(_("Aperçu (joué en boucle, comme dans le film)")))
        va.addWidget(self.vue)
        self.vue_temps = QLabel("")
        self.vue_temps.setStyleSheet("color:#9aa4b2")
        va.addWidget(self.vue_temps)
        va.addStretch(1)
        racine.addLayout(va)
        self._fond = None
        try:
            png = self.ed.apercu.image_courante(max(self._L, 320)) if hasattr(self.ed, "apercu") else None
            if png:
                px = QPixmap()
                px.loadFromData(png)
                if not px.isNull():
                    self._fond = px.scaled(self._L, self._H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:      # noqa: BLE001 : sans image du film, fond noir
            self._fond = None
        self._cache, self._t_vue = {}, 0.0
        self._horloge = QTimer(self)
        self._horloge.setInterval(66)
        self._horloge.timeout.connect(self._apercu_tic)

    def _apercu_regle(self):
        self._cache = {}
        self._g_vue = self.resultat()

    def _apercu_tic(self):
        g = self._g_vue
        d, fin = float(g["debut"]), float(g["fin"])
        self._t_vue = self._t_vue + 0.066 if d <= self._t_vue < fin else d
        self._dessiner(self._t_vue)

    def _dessiner(self, t):
        from PySide6.QtGui import QPainter, QColor
        g = self._g_vue
        img = QPixmap(self._L, self._H)
        img.fill(QColor("#000"))
        p = QPainter(img)
        if self._fond is not None:
            p.drawPixmap((self._L - self._fond.width()) // 2, (self._H - self._fond.height()) // 2, self._fond)
        taille = max(24, int(self._H * float(g.get("taille", 0.22))))
        x = float(g.get("x", 0.88)) * self._L - taille / 2
        y = float(g.get("y", 0.85)) * self._H - taille / 2
        try:
            if g["genre"] == "image" and (g.get("options") or {}).get("chemin"):
                src = QPixmap(g["options"]["chemin"]).scaled(taille, taille, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                p.drawPixmap(int(x + (taille - src.width()) / 2), int(y + (taille - src.height()) / 2), src)
            else:
                chaine = (getattr(self.ed, "projet", None).d.get("chaine") if getattr(self.ed, "projet", None) is not None else None)
                p.drawImage(int(x), int(y), GO.image(g, t, taille, chaine, self._cache))
        except Exception as e:     # noqa: BLE001 : on montre pourquoi plutôt que rien
            p.setPen(QColor("#ff8a80"))
            p.drawText(10, 20, str(e)[:80])
        p.end()
        self.vue.setPixmap(img)
        self.vue_temps.setText(_("Instant : {t} s (de {a} à {b} s)", t=f"{t:.1f}", a=f"{float(g['debut']):.1f}", b=f"{float(g['fin']):.1f}"))

    def done(self, r):
        self._horloge.stop()
        super().done(r)

    def _choisir_image(self):
        from .widgets import ouvrir_fichier
        p = ouvrir_fichier(self, _("Image ou logo"), "Images (*.png *.jpg *.jpeg *.webp *.svg)", "images")
        if p:
            self.chemin_image.setText(p)
            self.genre.setCurrentIndex(max(0, self.genre.findData("image")))
            from . import fond as F
            try:
                if not p.lower().endswith(".svg") and not F.a_deja_transparence(F.lire(p)):
                    if QMessageBox.question(self, _("Image sans transparence"),
                                            _("Cette image n'a pas de fond transparent : son fond (blanc ou autre) se verra sur le film. "
                                              "Retirer le fond maintenant ?")) == QMessageBox.Yes:
                        self._retirer_fond()
            except Exception:       # noqa: BLE001 : image illisible par OpenCV, on la garde telle quelle
                pass

    def _retirer_fond(self):
        p = self.chemin_image.text().strip()
        if not p or not os.path.exists(p):
            self._choisir_image()
            p = self.chemin_image.text().strip()
            if not p:
                return
        from .dialogues_fond import retirer_fond
        r = retirer_fond(self, p)
        if r:
            self.chemin_image.setText(r)

    def _gpx(self):
        from .widgets import ouvrir_fichier
        p = ouvrir_fichier(self, _("Trace GPX"), "GPX (*.gpx)", "documents")
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


def image_projet(projet, t, largeur=320):
    """Image du montage à l'instant t (plan de la piste Vidéo 1, sans les effets), en PNG ; None si rien."""
    from .projet import fin_clip
    for c in projet.clips_piste("video"):
        if c["debut"] <= t < fin_clip(c):
            m = projet.media(c["media"])
            if not m:
                return None
            if m.get("genre") == "image":
                with open(m["chemin"], "rb") as fh:
                    return fh.read()
            try:
                return moteur.image(m["chemin"], float(c["src_debut"]) + (t - c["debut"]) * float(c.get("vitesse", 1.0) or 1.0), largeur)
            except moteur.ErreurMoteur:
                return None
    return None


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
        # exports en série (0.9.25) : la même vidéo dans plusieurs formats d'un coup, un fichier par format
        from PySide6.QtWidgets import QGridLayout, QGroupBox
        g = QGroupBox(_("Exporter aussi en (un fichier par format coché)"))
        g.setToolTip(_("Par exemple horizontal pour YouTube, vertical pour les Reels et carré : les plans qui suivent une personne la "
                       "suivent dans chaque format ; les autres passent en fond flou (rien n'est coupé)."))
        gl = QGridLayout(g)
        self.autres = {}
        deja = set(params.get("export_autres") or [])
        for i, (k, d) in enumerate((k, d) for k, d in moteur.DESTINATIONS.items() if k != "original"):
            cb = QCheckBox(d[0])
            cb.setChecked(k in deja)
            self.autres[k] = cb
            gl.addWidget(cb, i // 2, i % 2)
        self.dest.currentIndexChanged.connect(self._maj_autres)
        self._maj_autres()
        f.addRow(g)
        self.drive = QCheckBox(_("Déposer ensuite sur le Drive / NAS de synchronisation"))
        f.addRow(self.drive)
        # ---- vignette du fichier : l'image du film qui représente la vidéo
        hv = QHBoxLayout()
        self.vignette_cb = QCheckBox(_("Vignette à"))
        self.vignette_cb.setToolTip(_("L'image choisie est intégrée au fichier (explorateur, lecteurs) et enregistrée à côté en JPG "
                                      "pour la miniature YouTube. Aussi : clic droit sur la règle › Prendre cette image comme vignette."))
        self.vignette_t = QDoubleSpinBox()
        self.vignette_t.setRange(0.0, max(0.0, projet.duree() - 0.05))
        self.vignette_t.setDecimals(1)
        self.vignette_t.setSuffix(" s")
        vt = projet.d.get("vignette_t")
        self.vignette_cb.setChecked(vt is not None)
        self.vignette_t.setValue(float(vt) if vt is not None else min(1.0, projet.duree() / 2))
        self.apercu_vignette = QLabel()
        self.apercu_vignette.setFixedSize(128, 72)
        self.apercu_vignette.setStyleSheet("background:#000;border-radius:4px")
        hv.addWidget(self.vignette_cb)
        hv.addWidget(self.vignette_t)
        hv.addWidget(self.apercu_vignette)
        hv.addStretch(1)
        f.addRow(_("Image du fichier"), hv)
        self.vignette_t.valueChanged.connect(lambda _v: (self.vignette_cb.setChecked(True), self._vignette()))
        self.vignette_cb.toggled.connect(lambda _v: self._vignette())
        QTimer.singleShot(0, self._vignette)
        self.info = QLabel(_("Durée : {d} · {n} plans", d=moteur.duree_texte(projet.duree()), n=len(projet.clips_piste("video"))))
        f.addRow(self.info)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.button(QDialogButtonBox.Ok).setText(_("Exporter"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _vignette(self):
        """Montre l'image choisie et la garde dans le projet (annulable comme le reste)."""
        from PySide6.QtGui import QPixmap
        if not self.vignette_cb.isChecked():
            self.projet.d.pop("vignette_t", None)
            self.apercu_vignette.clear()
            return
        t = self.vignette_t.value()
        self.projet.d["vignette_t"] = round(t, 2)
        png = image_projet(self.projet, t, 256)
        px = QPixmap()
        if png and px.loadFromData(png):
            self.apercu_vignette.setPixmap(px.scaled(128, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _maj_autres(self, *_a):
        for k, cb in self.autres.items():
            cb.setEnabled(k != self.dest.currentData())

    def autres_formats(self):
        l = [k for k, cb in self.autres.items() if cb.isChecked() and cb.isEnabled()]
        self.params["export_autres"] = l
        return l

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
                         "(onglet 1), ou un <b>plan généré par IA</b> à partir d'une phrase, par exemple « survol de collines au "
                         "lever du soleil » (onglet 2). Le résultat arrive dans les médias du projet, prêt à poser sur la timeline. "
                         "Pour dessiner votre logo lui-même : Fabrique IA › Logo, intro et vignette › Mon logo."))
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
        # ---- modèles en vignettes animées (calculées avec votre texte), grand aperçu du modèle choisi
        from . import intros as IN
        self._IN = IN
        self.modele = QComboBox()                # liste de référence (modernes puis anciens), synchronisée avec les vignettes
        for k, (fam, lib, _d) in IN.MODELES.items():
            self.modele.addItem(f"{IN.FAMILLES[fam]} — {lib}", k)
        for k, lib in fabrique.MODELES_LOGO.items():
            self.modele.addItem(_("Ancien modèle — {n}", n=lib), k)
        voulu = (self.recette.get("logo") or {}).get("modele")
        self.modele.setCurrentIndex(max(0, self.modele.findData(voulu if voulu in IN.MODELES else "masque")))
        self.famille = QComboBox()
        self.famille.addItem(_("Tous les styles modernes"), "")
        for k, lib in IN.FAMILLES.items():
            self.famille.addItem(lib, k)
        self.famille.addItem(_("Anciens modèles"), "anciens")
        self.famille.currentIndexChanged.connect(self._remplir_modeles)
        f.addRow(_("Style"), self.famille)
        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QListView, QListWidget
        hv = QHBoxLayout()
        self.vignettes = QListWidget()
        self.vignettes.setViewMode(QListView.IconMode)
        self.vignettes.setIconSize(QSize(176, 99))
        self.vignettes.setGridSize(QSize(188, 130))
        self.vignettes.setResizeMode(QListView.Adjust)
        self.vignettes.setMovement(QListView.Static)
        self.vignettes.setWordWrap(True)
        self.vignettes.setMinimumHeight(140)
        self.vignettes.currentItemChanged.connect(self._modele_choisi)
        hv.addWidget(self.vignettes, 3)
        va = QVBoxLayout()
        self.grand = QLabel()
        self.grand.setFixedSize(320, 180)
        self.grand.setStyleSheet("background:#000;border-radius:6px")
        va.addWidget(self.grand)
        self.desc_modele = QLabel("")
        self.desc_modele.setWordWrap(True)
        self.desc_modele.setFixedWidth(320)
        va.addWidget(self.desc_modele)
        va.addStretch(1)
        hv.addLayout(va, 0)
        f.addRow(hv)
        self.fond = QComboBox()
        for k, lib in IN.FONDS.items():
            self.fond.addItem(lib, k)
        self.fond.setCurrentIndex(max(0, self.fond.findData(params.get("intro_fond") or "degrade")))
        self.fond.currentIndexChanged.connect(self._raz_apercus)
        self.accent = QPushButton(_("Couleur d'accent : celle du style"))
        self.accent.setStyleSheet("text-align:left;padding:3px 8px")
        self._accent = ""
        self.accent.clicked.connect(self._choisir_accent)
        hf = QHBoxLayout()
        hf.addWidget(self.fond, 1)
        hf.addWidget(self.accent)
        f.addRow(_("Fond"), hf)
        self.duree = QDoubleSpinBox()
        self.duree.setRange(1.0, 10.0)
        self.duree.setValue(float((self.recette.get("logo") or {}).get("duree") or 3.0))
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
        self._apercus, self._image_film, self._pos = {}, None, 0
        self.texte.textChanged.connect(self._raz_apercus)
        self.sous.textChanged.connect(self._raz_apercus)
        self.minuterie = QTimer(self)
        self.minuterie.timeout.connect(self._animer)
        self.minuterie.start(110)
        self._remplir_modeles()
        # ---- plan IA
        w2 = QWidget()
        f2 = QFormLayout(w2)
        self.sujet = QPlainTextEdit("")
        self.sujet.setMaximumHeight(80)
        plans = self.recette.get("plans_a_generer") or []
        if plans:
            self.sujet.setPlainText(plans[0].get("consigne", ""))
        self.sujet.setPlaceholderText(_("Décrivez le plan : « plan aérien au-dessus d'une baie au lever du soleil »"))
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
        hc = QHBoxLayout()
        b_c = QPushButton(_("Rédiger la consigne"))
        b_c.setToolTip(_("« à la manière de Alain Delon », « comme John Wayne »… dans le sujet : le nom est remplacé par la "
                         "description du style (allure, jeu, image), jamais un visage"))
        b_c.clicked.connect(self._consigne)
        hc.addWidget(b_c, 1)
        b_st = QPushButton(_("Style « à la manière de »…"))
        b_st.clicked.connect(self._style)
        hc.addWidget(b_st)
        f2.addRow(hc)
        b_seq = QPushButton(_("Plusieurs plans avec personnages et répliques : Séquence IA…"))
        b_seq.setToolTip(_("Une histoire découpée en plans, les mêmes personnages d'un plan à l'autre, leurs répliques et une musique"))
        b_seq.clicked.connect(self._vers_sequence)
        f2.addRow(b_seq)
        from . import packs_ia as _P
        cle_v = _P.modele_actif("video", params)
        local_pret = bool(cle_v and _P.installe(cle_v))
        self.voie_locale = QRadioButton(_("IA de ce poste (gratuite, rien n'est envoyé) : 5 s au plus, plus lent sans carte graphique")
                                        if local_pret else
                                        _("IA de ce poste (gratuite) : modèle vidéo à installer dans Edition › Préférences › IA locale"))
        self.voie_locale.setEnabled(local_pret)
        self.voie_flow = QRadioButton(_("Google Flow, avec votre abonnement Google (sans clef, sans frais en plus)"))
        self.aide_flow = QLabel(_(
            "<b>Comment ça marche ?</b> Flow est le site de Google qui fabrique des vidéos par IA ; PhilCut ne peut pas "
            "s'y connecter à votre place, il vous mâche le travail (essai du 9 novembre 2026) :<br>"
            "1. « Fabriquer » : PhilCut met la consigne (en anglais) dans le presse-papiers et ouvre Flow dans votre navigateur.<br>"
            "2. Dans Flow : « + Nouveau projet ». La première fois, l'icône des réglages (à gauche de la flèche, en bas à droite) : "
            "laissez « Confirmer avant de générer : Toujours », vidéo 16:9, <b>x1</b> (x2 coûte le double), modèle "
            "<b>Veo 3.1 – Lite</b> (le moins cher), puis « Enregistrer ».<br>"
            "3. Dans « Que voulez-vous créer ? » : <b>Ctrl+V</b> pour coller, puis la flèche. Flow annonce le prix en crédits "
            "(Veo 3.1 Lite : 10 crédits pour 8 s, sa seule durée) : « Approuver » (jamais « Toujours approuver »). Selon "
            "l'affluence, le plan attend dans une file d'attente quelques minutes.<br>"
            "4. Crédits : cliquez sur votre photo en haut à droite ; Flow en offre <b>50 par jour</b> (environ 5 plans Lite), "
            "remis à zéro chaque soir.<br>"
            "5. Sur la vidéo : bouton <b>Télécharger</b> (MP4 720p). Le fichier arrive dans le dossier surveillé ci-dessous "
            "(vos Téléchargements en général).<br>"
            "6. PhilCut attend ce fichier (barre du bas, avec le temps écoulé et « Arrêter »), puis vous le montre : vous le "
            "regardez, et vous choisissez de l'insérer à la ligne rouge, de le garder dans les médias ou de le jeter. Ses réglages "
            "sont gardés : clic droit sur le plan › « Reprendre la création »."))
        self.aide_flow.setWordWrap(True)
        self.aide_flow.setTextFormat(Qt.RichText)
        self.aide_flow.setStyleSheet("padding:6px 8px;border:1px solid palette(mid);border-radius:6px")
        self.voie_flow.toggled.connect(self.aide_flow.setVisible)
        self.voie_veo = QRadioButton(_("Gemini ou un autre générateur payant avec votre clef (fal.ai : Kling, Seedance…)"))
        from . import generateurs_video as GV
        dispo = {m["id"] for m in GV.disponibles(params)}
        self.voie_veo.setEnabled(bool(params.get("veo_actif")) and bool(dispo))
        # ordre : ce poste d'abord (gratuit), puis Gemini (votre clef, prix annoncé), Flow en dernier (pas à pas)
        (self.voie_locale if local_pret else self.voie_veo if self.voie_veo.isEnabled() else self.voie_flow).setChecked(True)
        self.aide_flow.setVisible(self.voie_flow.isChecked())
        f2.addRow(self.voie_locale)
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
        f2.addRow(self.voie_veo)
        f2.addRow(_("Modèle"), hm)
        self.prix = QLabel("")
        f2.addRow(self.prix)
        f2.addRow(self.voie_flow)
        f2.addRow(self.aide_flow)
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

    # ---- vignettes animées des intros
    N_IMAGES = 18

    def _remplir_modeles(self):
        from PySide6.QtWidgets import QListWidgetItem
        IN = self._IN
        fam = self.famille.currentData() or ""
        actuel = self.modele.currentData()
        self.vignettes.blockSignals(True)
        self.vignettes.clear()
        for i in range(self.modele.count()):
            k = self.modele.itemData(i)
            moderne = k in IN.MODELES
            if (fam == "anciens" and moderne) or (fam not in ("", "anciens") and (not moderne or IN.MODELES[k][0] != fam)) or (fam == "" and not moderne):
                continue
            it = QListWidgetItem(IN.MODELES[k][1] if moderne else fabrique.MODELES_LOGO[k])
            it.setData(Qt.UserRole, k)
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            self.vignettes.addItem(it)
            if k == actuel:
                self.vignettes.setCurrentItem(it)
        self.vignettes.blockSignals(False)
        if self.vignettes.currentItem() is None and self.vignettes.count():
            self.vignettes.setCurrentRow(0)
        else:
            self._modele_choisi(self.vignettes.currentItem(), None)

    def _modele_choisi(self, it, _avant=None):
        if it is None:
            return
        k = it.data(Qt.UserRole)
        self.modele.setCurrentIndex(max(0, self.modele.findData(k)))
        IN = self._IN
        self.desc_modele.setText(IN.MODELES[k][2] if k in IN.MODELES else _("Ancien modèle, gardé pour les projets existants."))

    def _raz_apercus(self, *_a):
        self._apercus = {}
        self.params["intro_fond"] = self.fond.currentData()

    def _choisir_accent(self):
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(self._accent or "#ff3b30"), self, _("Couleur d'accent"))
        if c.isValid():
            self._accent = c.name()
            self.accent.setText(_("Couleur d'accent : {c}", c=c.name()))
            self.accent.setStyleSheet(f"text-align:left;padding:3px 8px;background:{c.name()};color:{'#000' if c.lightness() > 140 else '#fff'}")
            self._raz_apercus()

    def image_film(self):
        """Une image du premier plan vidéo du projet (fond « premières images du film »)."""
        if self._image_film is None:
            self._image_film = ""
            try:
                cs = sorted(self.projet.clips_piste("video"), key=lambda c: c["debut"])
                if cs:
                    m = self.projet.media(cs[0]["media"])
                    if m and m.get("genre") != "image":
                        import tempfile
                        png = moteur.image(m["chemin"], float(cs[0]["src_debut"]) + 0.5, 960)
                        chemin = os.path.join(tempfile.gettempdir(), f"philcut_film_{os.getpid()}.png")
                        with open(chemin, "wb") as fh:
                            fh.write(png)
                        self._image_film = chemin
                    elif m:
                        self._image_film = m["chemin"]
            except Exception:            # noqa: BLE001
                self._image_film = ""
        return self._image_film or None

    def options_intro(self):
        return {"fond": self.fond.currentData(), "couleurs": {"accent": self._accent} if self._accent else None,
                "image_film": self.image_film() if self.fond.currentData() == "film" else None}

    def _animer(self):
        """Une image de plus par tick pour les vignettes visibles ; le grand aperçu joue le modèle choisi."""
        from PySide6.QtGui import QIcon, QPixmap
        IN = self._IN
        if self.onglets.currentIndex() != 0 or not self.isVisible():
            return
        self._pos = (self._pos + 1) % self.N_IMAGES
        o = self.options_intro()
        budget = 4
        duree = 3.0
        for i in range(self.vignettes.count()):
            it = self.vignettes.item(i)
            k = it.data(Qt.UserRole)
            if k not in IN.MODELES:
                continue
            imgs = self._apercus.setdefault(k, [None] * self.N_IMAGES)
            j = self._pos
            if imgs[j] is None and budget > 0:
                budget -= 1
                ctx = getattr(self, "_ctx_" + k, None)
                cle = (self.texte.text(), self.sous.text(), o["fond"], self._accent)
                if ctx is None or getattr(self, "_cle_" + k, None) != cle:
                    ctx = IN.contexte(k, self.texte.text() or _("Votre titre"), self.sous.text(), 320, 180, duree, o["fond"], o["couleurs"],
                                      o["image_film"], self.image.text().strip() or None)
                    setattr(self, "_ctx_" + k, ctx)
                    setattr(self, "_cle_" + k, cle)
                imgs[j] = QPixmap.fromImage(IN.image(ctx, 0.2 + (duree - 0.2) * j / self.N_IMAGES))
            if imgs[j] is not None:
                it.setIcon(QIcon(imgs[j].scaled(176, 99, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                if it is self.vignettes.currentItem():
                    self.grand.setPixmap(imgs[j])

    def _image(self):
        from .widgets import ouvrir_fichier
        p = ouvrir_fichier(self, _("Image du logo"), "Images (*.png *.svg *.jpg *.jpeg)", "images")
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

    def _style(self):
        from .dialogues_creatif import choisir_style
        nom = choisir_style(self, self.params, "video")
        if nom:
            t = self.sujet.toPlainText().rstrip(" ,")
            self.sujet.setPlainText((t + ", " if t else "") + _("à la manière de") + " " + nom)
            self._consigne()

    def _vers_sequence(self):
        self.vers_sequence = True
        self.reject()

    def _consigne(self):
        self.consigne.setPlainText(fabrique.consigne_plan("illustration", self.sujet.toPlainText().strip(), self.style.currentText().strip(),
                                                          self.duree_ia.value(), self.projet.format, params=self.params, traduire=True))

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
        il = media.get("ia_locale") or {}
        if il:
            lignes.append("<p><b>" + _("Vu par l'IA locale") + f"</b> ({il.get('date', '')}) : {il.get('nom', '')} — {il.get('resume', '')}</p>")
            if il.get("lieux_objets"):
                lignes.append("<p>" + _("Lieux et objets : {l}", l=", ".join(il["lieux_objets"])) + "</p>")
            if il.get("textes"):
                lignes.append("<p>" + _("Textes lus : {t}", t=", ".join(il["textes"])) + "</p>")
        else:
            lignes.append("<p><i>" + _("Clic droit sur le média › « Analyser avec l'IA locale » : description, lieux, textes lus (sur ce poste).") + "</i></p>")
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


class DialogueClipRecu(QDialog):
    """Clip reçu (Flow ou autre générateur) : on le regarde AVANT de l'intégrer, puis insérer / garder / jeter."""

    def __init__(self, ed, chemin, titre=""):
        super().__init__(ed)
        from .dialogues_creatif import ApercuCreation
        self.ed, self.chemin = ed, chemin
        self.setWindowTitle(titre or _("Clip reçu"))
        v = QVBoxLayout(self)
        lb = QLabel(_("« {n} » est arrivé. Regardez-le, gardez le morceau voulu, puis choisissez.", n=os.path.basename(chemin)))
        lb.setWordWrap(True)
        v.addWidget(lb)
        self.apercu = ApercuCreation(self)
        self.apercu.charger(chemin, video=True)
        self.apercu.show()
        v.addWidget(self.apercu)
        h = QHBoxLayout()
        b1 = QPushButton(_("Insérer à la ligne rouge"))
        b1.setToolTip(_("Le clip se place après le plan sous la ligne rouge ; la suite du film est décalée (Ctrl+Z revient)."))
        b1.clicked.connect(self.inserer)
        b2 = QPushButton(_("Garder dans les médias (sans poser)"))
        b2.setToolTip(_("Le fichier rejoint les médias du projet, à gauche : vous le glisserez où vous voulez."))
        b2.clicked.connect(self.garder)
        b3 = QPushButton(_("Jeter"))
        b3.setToolTip(_("Rien n'est ajouté au projet ; le fichier téléchargé reste dans votre dossier."))
        b3.clicked.connect(self.reject)
        for b in (b1, b2, b3):
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        self.resize(720, 460)

    def inserer(self):
        from . import prolonger
        r = self.apercu.reglages()
        self.apercu.arreter()
        p = self.ed.projet
        p.marquer()
        ci = prolonger.inserer(p, self.chemin, self.ed.timeline.position, "video", os.path.splitext(os.path.basename(self.chemin))[0])
        if ci:
            ci["src_debut"], ci["src_fin"] = r["src_debut"], r["src_fin"]
        self.ed.biblio.remplir(p)
        self.ed.rafraichir()
        self.ed.encart.message(_("Clip inséré à la ligne rouge ; la suite est décalée (Ctrl+Z pour revenir)."), 6000)
        self.accept()

    def garder(self):
        self.apercu.arreter()
        self.ed.importer([self.chemin])
        self.accept()

    def done(self, r):
        self.apercu.arreter()
        super().done(r)
