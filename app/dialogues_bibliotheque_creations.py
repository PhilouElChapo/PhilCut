"""Fenêtre « Ma bibliothèque de créations » (0.9.81) : voir, créer, nommer, compléter et retirer ce qui est gardé
(personnages, musiciens, objets, lieux, voix, styles, musiques, images). Voir bibliotheque_creations.py."""
import copy
import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QMessageBox, QPushButton, QScrollArea, QSplitter, QToolButton, QVBoxLayout, QWidget)

from . import bibliotheque_creations as B
from .cartes_assistant import ChampAmeliorable, aide, choisir_proposition, vider
from .langue import _
from .taches import Tache, texte_erreur
from .widgets import garder_calcul, suivre_en_fond

IMAGES = _("Images") + " (*.png *.jpg *.jpeg *.webp)"
SONS = _("Sons") + " (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.mp4 *.mkv *.webm *.mov)"


class DialogueBibliothequeCreations(QDialog):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed, self.params = ed, ed.params
        self.courante, self.tache = None, None
        self.setWindowTitle(_("Ma bibliothèque de créations"))
        self.resize(960, 640)
        v = QVBoxLayout(self)
        v.addWidget(aide(_("Ce que vous gardez ici se réutilise tel quel dans l'assistant de création (« Dans ma bibliothèque ») : la "
                           "fiche d'un personnage, une voix, un style, un lieu… Rangée avec vos réglages, elle vous suit sur vos autres "
                           "postes.")))
        sp = QSplitter()
        g = QWidget()
        gv = QVBoxLayout(g)
        gv.setContentsMargins(0, 0, 0, 0)
        h = QHBoxLayout()
        self.filtre = QComboBox()
        self.filtre.addItem(_("Tout"), "")
        for k, (lib, _x) in sorted(B.GENRES.items(), key=lambda x: B._alpha(x[1][0])):
            self.filtre.addItem(lib, k)
        self.filtre.currentIndexChanged.connect(lambda _i: self.remplir())
        h.addWidget(self.filtre)
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(_("Chercher…"))
        self.cherche.textChanged.connect(lambda _t: self.remplir())
        h.addWidget(self.cherche, 1)
        gv.addLayout(h)
        self.liste = QListWidget()
        self.liste.setIconSize(QSize(64, 48))
        self.liste.setWordWrap(True)
        self.liste.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.liste.currentRowChanged.connect(self._choisie)
        gv.addWidget(self.liste, 1)
        hb = QHBoxLayout()
        b = QPushButton(_("Nouveau…"))
        m = QMenu(b)
        for k, (lib, expl) in sorted(B.GENRES.items(), key=lambda x: B._alpha(x[1][0])):
            a = m.addAction(lib, lambda k=k: self.nouveau(k))
            a.setToolTip(expl)
        m.setToolTipsVisible(True)
        b.setMenu(m)
        hb.addWidget(b)
        bt = QPushButton(_("Tenues toutes faites…"))
        mt = QMenu(bt)
        from . import tenues as T
        for k, lib in T.FAMILLES:
            sm = mt.addMenu(lib)
            for x in T.pretes(k):
                a = sm.addAction(x["nom"], lambda x=x: self.ajouter_tenue_prete(x))
                a.setToolTip(x["description"])
            sm.setToolTipsVisible(True)
        bt.setMenu(mt)
        bt.setToolTip(_("Ajoute une tenue toute faite à la bibliothèque, pour la modifier ou la mettre à vos personnages"))
        hb.addWidget(bt)
        self.b_retirer = QPushButton(_("Retirer"))
        self.b_retirer.setToolTip(_("L'entrée va dans la corbeille de la bibliothèque : rien n'est effacé"))
        self.b_retirer.clicked.connect(self.retirer)
        hb.addWidget(self.b_retirer)
        hb.addStretch(1)
        gv.addLayout(hb)
        sp.addWidget(g)
        self.droite = QWidget()
        self.v_detail = QVBoxLayout(self.droite)
        zone = QScrollArea()                           # 0.9.88 : le détail grandit (photos, mode, tenue) : il défile
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zone.setWidget(self.droite)
        sp.addWidget(zone)
        sp.setSizes([360, 600])
        v.addWidget(sp, 1)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hn = QHBoxLayout()
        hn.addStretch(1)
        self.b_reduire = QPushButton(_("Réduire"))
        self.b_reduire.clicked.connect(self.hide)
        self.b_reduire.hide()
        hn.addWidget(self.b_reduire)
        bf = QPushButton(_("Fermer"))
        bf.clicked.connect(self.close)
        hn.addWidget(bf)
        v.addLayout(hn)
        self.remplir()

    # ------------------------------------------------------------------ liste
    def remplir(self, choisir=None):
        ident = choisir or (self.courante or {}).get("id")
        texte = B._alpha(self.cherche.text().strip())
        g = self.filtre.currentData()
        self.entrees = [e for e in B.lister(self.params, g or None)
                        if not texte or texte in B._alpha(e["nom"] + " " + e.get("description", "") + " " + B.resume(e))]
        self.liste.blockSignals(True)
        self.liste.clear()
        for e in self.entrees:
            it = QListWidgetItem(f"{e['nom']}\n{B.resume(e)[:90]}")
            ap = B.apercu(e)
            if ap:
                it.setIcon(QIcon(QPixmap(ap).scaled(64, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            self.liste.addItem(it)
        self.liste.blockSignals(False)
        k = next((i for i, e in enumerate(self.entrees) if e["id"] == ident), 0 if self.entrees else -1)
        if k >= 0:
            self.liste.setCurrentRow(k)
        self._choisie(k)

    def _choisie(self, r):
        self.courante = self.entrees[r] if 0 <= r < len(self.entrees) else None
        self.b_retirer.setEnabled(self.courante is not None)
        self._detail()

    # ------------------------------------------------------------------ détail d'une entrée
    def _detail(self):
        vider(self.v_detail)
        e = self.courante
        if e is None:
            self.v_detail.addWidget(aide(_("Votre bibliothèque est vide pour l'instant : « Nouveau… », ou « ☆ Garder » sur une carte de "
                                           "l'assistant de création.")))
            self.v_detail.addStretch(1)
            return
        d = e.get("donnees") or {}
        lb = QLabel(f"<b>{B.GENRES[e['genre']][0]}</b> — " + _("créé le {c}", c=e.get("cree", "")))
        self.v_detail.addWidget(lb)
        ap = B.apercu(e)
        if ap:
            im = QLabel()
            im.setPixmap(QPixmap(ap).scaled(420, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.v_detail.addWidget(im)
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Nom")))
        self.nom = QLineEdit(e["nom"])
        h.addWidget(self.nom, 1)
        self.v_detail.addLayout(h)
        self.desc = ChampAmeliorable(e.get("description", ""), {"personnage": "personne", "musicien": "personne", "objet": "objet",
                                                               "voix": "voix", "style_musical": "style"}.get(e["genre"], "idee"),
                                     3, self._ameliorer, _("Description"))
        self.v_detail.addWidget(self.desc)
        self.extra = {}
        if e["genre"] in ("personnage", "objet", "lieu"):
            h = QHBoxLayout()
            h.addWidget(QLabel(_("Création")))
            cm = QComboBox()
            for k, lib, expl in B.MODES:
                cm.addItem(lib, k)
                cm.setItemData(cm.count() - 1, expl, Qt.ToolTipRole)
            mode = d.get("mode") or ("reel" if self._photos(e) else "invente")
            cm.setCurrentIndex(max(0, cm.findData(mode)))
            self.extra["mode"] = cm
            h.addWidget(cm, 1)
            self.v_detail.addLayout(h)
            self.l_mode = aide(dict((k, x) for k, _l, x in B.MODES).get(mode, ""))
            cm.currentIndexChanged.connect(lambda _i: self.l_mode.setText(dict((k, x) for k, _l, x in B.MODES)
                                                                         .get(cm.currentData(), "")))
            self.v_detail.addWidget(self.l_mode)
            self._bande_photos(e)
        if e["genre"] == "personnage":
            from . import tenues as T
            h = QHBoxLayout()
            h.addWidget(QLabel(_("Tenue")))
            ct = QComboBox()
            ct.addItem(_("Celle des photos (ou de la description)"), "")
            for x in T.toutes(self.params):
                ct.addItem(("★ " if x["source"] == "biblio" else "") + x["nom"], x["id"])
            actuelle = (d.get("tenue") or {}).get("id", "")
            ct.setCurrentIndex(max(0, ct.findData(actuelle)))
            ct.setToolTip(_("La fiche est dessinée avec cette tenue ; dans l'assistant, chaque scène peut en choisir une autre"))
            self.extra["tenue"] = ct
            h.addWidget(ct, 1)
            self.v_detail.addLayout(h)
        if e["genre"] == "tenue":
            from . import tenues as T
            h = QHBoxLayout()
            h.addWidget(QLabel(_("Famille")))
            cf = QComboBox()
            cf.addItem(_("Autre"), "")
            for k, lib in T.FAMILLES:
                cf.addItem(lib, k)
            cf.setCurrentIndex(max(0, cf.findData(d.get("famille", ""))))
            self.extra["famille"] = cf
            h.addWidget(cf, 1)
            self.v_detail.addLayout(h)
        if e["genre"] == "musicien":
            h = QHBoxLayout()
            h.addWidget(QLabel(_("Instrument")))
            self.extra["instrument"] = QLineEdit(d.get("instrument", ""))
            h.addWidget(self.extra["instrument"], 1)
            self.v_detail.addLayout(h)
        if e["genre"] == "voix":
            h = QHBoxLayout()
            h.addWidget(QLabel(_("C'est une voix de")))
            cr = QComboBox()
            for k, lib in B.ROLES_VOIX:
                cr.addItem(lib, k)
            cr.setCurrentIndex(max(0, cr.findData(d.get("role") or "")))
            self.extra["role"] = cr
            h.addWidget(cr)
            h.addStretch(1)
            self.v_detail.addLayout(h)
            if (d.get("voix_decrite") or {}).get("fr"):
                self.v_detail.addWidget(aide(_("Voix décrite : {d}", d=d["voix_decrite"]["fr"])))
        if e["genre"] in ("personnage", "musicien", "voix"):
            self.extra["accord"] = QCheckBox(_("Accord de la personne des photos (ou c'est moi)"))
            self.extra["accord"].setToolTip(_("Obligatoire pour « Réel » et « Inspiré de photos » : la ressemblance est gardée."))
            self.extra["accord"].setChecked(bool(d.get("accord")))
            self.v_detail.addWidget(self.extra["accord"])
        if e["genre"] == "style_musical" and (d.get("inspiration") or {}).get("resume"):
            self.v_detail.addWidget(aide(_("Entendu : {r}", r=d["inspiration"]["resume"])))
        fich = e.get("fichiers") or {}
        if fich:
            self.v_detail.addWidget(aide(_("Fichiers : {l}", l=", ".join(sorted(os.path.basename(x) for x in fich.values())))))
        h = QHBoxLayout()
        b = QPushButton(_("Enregistrer"))
        b.setStyleSheet("font-weight:600")
        b.clicked.connect(self.enregistrer)
        h.addWidget(b)
        b = QPushButton(_("Ajouter un fichier…"))
        b.clicked.connect(self.ajouter_fichier)
        h.addWidget(b)
        if e["genre"] in ("personnage", "musicien", "objet"):
            b = QPushButton(_("Faire sa fiche (Gemini)…"))
            b.setToolTip(_("Face, trois quarts, profil, en pied, d'après ses photos (selon « Création »), sa description et sa "
                           "tenue ; environ 0,04 $"))
            b.clicked.connect(self.faire_fiche)
            h.addWidget(b)
        if e["genre"] == "lieu":
            b = QPushButton(_("Faire sa planche (Gemini)…"))
            b.setToolTip(_("Quatre vues du même lieu, même lumière, d'après ses photos ou sa description ; environ 0,04 $. Elle sert "
                           "de décor aux images clefs."))
            b.clicked.connect(self.faire_planche_lieu)
            h.addWidget(b)
        if e["genre"] == "tenue":
            b = QPushButton(_("Faire son image (Gemini)…"))
            b.setToolTip(_("La tenue seule, sur fond neutre, d'après sa description ; environ 0,04 $"))
            b.clicked.connect(self.faire_image_tenue)
            h.addWidget(b)
        if e["genre"] == "voix":
            b = QPushButton(_("Décrire d'après un morceau…"))
            b.setToolTip(_("La voix est isolée sur ce poste puis décrite ; rien n'est envoyé"))
            b.clicked.connect(lambda: self.voix_depuis_morceau(False))
            h.addWidget(b)
            b = QPushButton(_("Garder son timbre…"))
            b.setToolTip(_("Seulement votre voix ou celle d'une personne d'accord (case ci-dessus)"))
            b.clicked.connect(lambda: self.voix_depuis_morceau(True))
            h.addWidget(b)
        if e["genre"] == "style_musical":
            b = QPushButton(_("Ecouter un morceau (sur ce poste)…"))
            b.clicked.connect(self.style_depuis_morceau)
            h.addWidget(b)
        h.addStretch(1)
        self.v_detail.addLayout(h)
        self.v_detail.addStretch(1)

    def _donnees(self):
        e = self.courante
        d = dict(e.get("donnees") or {})
        if "instrument" in self.extra:
            d["instrument"] = self.extra["instrument"].text().strip()
        if "role" in self.extra:
            d["role"] = self.extra["role"].currentData()
        if "accord" in self.extra:
            d["accord"] = self.extra["accord"].isChecked()
        if "mode" in self.extra:
            d["mode"] = self.extra["mode"].currentData()
        if "famille" in self.extra:
            d["famille"] = self.extra["famille"].currentData()
        if "tenue" in self.extra:
            from . import tenues as T
            t = T.trouver(self.params, self.extra["tenue"].currentData())
            d["tenue"] = {"id": t["id"], "nom": t["nom"], "description": t["description"], "en": t.get("en", ""),
                          "image": t.get("image", "")} if t else None
        return d

    def enregistrer(self, fichiers=None, donnees=None):
        e = self.courante
        if e is None:
            return
        d = self._donnees()
        if d.get("mode") in ("reel", "inspire") and e["genre"] in ("personnage", "musicien") and self._photos(e) \
                and not d.get("accord"):
            self.etat.setText(_("✕ « Réel » et « Inspiré de photos » gardent la ressemblance : cochez d'abord l'accord de la "
                                "personne (ou que c'est vous)."))
            return
        d.update(donnees or {})
        try:
            x = B.garder(self.params, e["genre"], self.nom.text(), self.desc.texte(), fichiers, d, e["id"])
        except ValueError as err:
            self.etat.setText("✕ " + texte_erreur(err))
            return
        self.etat.setText(_("✓ « {n} » enregistré.", n=x["nom"]))
        self.remplir(x["id"])

    def nouveau(self, genre):
        x = B.garder(self.params, genre, _("Nouveau : {g}", g=B.GENRES[genre][0].lower()))
        self.filtre.setCurrentIndex(0)
        self.cherche.clear()
        self.remplir(x["id"])
        self.nom.setFocus()
        self.nom.selectAll()
        self.etat.setText(B.GENRES[genre][1])

    def retirer(self):
        e = self.courante
        if e is None:
            return
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Retirer"), _("Retirer « {n} » de la bibliothèque ? Il reste dans la corbeille de la bibliothèque.", n=e["nom"])) \
                != QMessageBox.Yes:
            return
        B.retirer(self.params, e)
        self.courante = None
        self.remplir()

    # ------------------------------------------------------------------ photos, tenues, planches (0.9.88)
    @staticmethod
    def _photos(e):
        return [(r, p) for r, p in sorted((e.get("fichiers") or {}).items())
                if r not in ("planche", "image_tenue") and p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

    def _bande_photos(self, e):
        photos = self._photos(e)
        self.v_detail.addWidget(QLabel(_("Photos ({n}) : plusieurs angles donnent un meilleur résultat", n=len(photos))))
        h = QHBoxLayout()
        for role, p in photos[:8]:
            col = QVBoxLayout()
            im = QLabel()
            im.setPixmap(QPixmap(p).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            im.setToolTip(os.path.basename(p))
            col.addWidget(im)
            bx = QToolButton()
            bx.setText("✕")
            bx.setToolTip(_("Retirer cette photo"))
            bx.clicked.connect(lambda _c=False, r=role: self.retirer_photo(r))
            col.addWidget(bx, 0, Qt.AlignHCenter)
            h.addLayout(col)
        b = QPushButton(_("Ajouter des photos…"))
        b.clicked.connect(self.ajouter_photos)
        h.addWidget(b)
        br = QPushButton(_("Image d'un rush…"))
        br.setToolTip(_("Placez la ligne rouge sur un rush (ou une photo du montage) où on le voit : PhilCut prend l'image, vous "
                        "l'encadrez. Recommencez avec d'autres rushes pour d'autres angles."))
        br.clicked.connect(self.photo_ligne_rouge)
        h.addWidget(br)
        h.addStretch(1)
        self.v_detail.addLayout(h)

    @staticmethod
    def _prochain(e):
        """Numéro libre pour une nouvelle photo (jamais une photo écrasée)."""
        import re as _re
        nums = [int(m.group(1)) for r in (e.get("_fichiers") or e.get("fichiers") or {}) for m in [_re.match(r"image(\d+)$", r)] if m]
        return max(nums, default=0) + 1

    def _mode_reel(self):
        """Des photos arrivent sur une entrée « Inventé » : elle devient « Réel » (on peut rechanger)."""
        cm = self.extra.get("mode")
        if cm is not None and cm.currentData() == "invente":
            cm.setCurrentIndex(max(0, cm.findData("reel")))

    def ajouter_photos(self):
        from .widgets import ouvrir_fichiers
        e = self.courante
        if e is None:
            return
        chemins = ouvrir_fichiers(self, _("Photos"), IMAGES, "image", self.params)
        if chemins:
            self._mode_reel()
            n = self._prochain(e)
            self.enregistrer({f"image{n + k}": c for k, c in enumerate(chemins)})

    def photo_ligne_rouge(self):
        """0.9.88 : une photo prise dans n'importe quel rush (ligne rouge) ; une personne ou un objet est encadré."""
        from . import assistant_creation as A
        from .cartes_assistant import encadrer, image_ligne_rouge
        e = self.courante
        if e is None:
            return
        image = image_ligne_rouge(self.ed)
        if not image:
            self.etat.setText(_("Placez la ligne rouge sur une image d'un rush ou d'une photo, puis recommencez."))
            return
        if e["genre"] in ("personnage", "musicien", "objet", "tenue"):
            boite = getattr(self, "_test_boite", None) or encadrer(self, image, _("Encadrez « {n} »", n=e["nom"]))
            if not boite:
                return
            import tempfile
            image = A.decouper(image, boite, os.path.join(tempfile.mkdtemp(), "rush.png"), detourer=e["genre"] != "tenue")
        if image:
            self._mode_reel()
            self.enregistrer({f"image{self._prochain(e)}": image})

    def retirer_photo(self, role):
        e = self.courante
        if e is None:
            return
        d = e["dossier"]
        ent = B.lire(self.params, e["genre"], e["id"]) or e
        f = dict(ent.get("_fichiers") or {})
        nom = f.pop(role, None)
        ent["_fichiers"] = f
        B._ecrire({k: v for k, v in ent.items() if k not in ("dossier", "fichiers")}, d)
        if nom and os.path.exists(os.path.join(d, nom)):
            os.replace(os.path.join(d, nom), os.path.join(d, "." + nom + ".retire"))
        self.remplir(e["id"])

    def ajouter_tenue_prete(self, x):
        t = B.garder(self.params, "tenue", x["nom"], x["description"], None, {"famille": x["famille"], "en": x["en"]})
        self.filtre.setCurrentIndex(0)
        self.remplir(t["id"])
        self.etat.setText(_("✓ Tenue « {n} » ajoutée : modifiez-la si vous voulez, puis mettez-la à vos personnages.", n=x["nom"]))

    def faire_planche_lieu(self):
        from . import sequence_ia as Q
        e = copy.deepcopy(self.courante)
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Faire sa planche"), _("La planche est dessinée par Gemini (votre clef), environ 0,04 $. Continuer ?")) != QMessageBox.Yes:
            return
        li = {"nom": self.nom.text(), "description": self.desc.texte(), "images": [p for _r, p in self._photos(e)],
              "mode": self.extra["mode"].currentData() if "mode" in self.extra else ""}
        seq, params = Q.nouvelle(), self.params

        def travail(t):
            t.avancer(0.1, _("dessin du lieu"))
            return Q.planche_lieu(seq, li, params)
        self._lancer(travail, _("Planche de « {n} »", n=li["nom"]), lambda r: r and self.enregistrer({"planche": r}))

    def faire_image_tenue(self):
        from . import ia, sequence_ia as Q
        e = self.courante
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Faire son image"), _("L'image est dessinée par Gemini (votre clef), environ 0,04 $. Continuer ?")) != QMessageBox.Yes:
            return
        texte = (e.get("donnees") or {}).get("en") or Q._anglais(self.desc.texte(), True)
        params, dossier = self.params, e["dossier"]

        def travail(t):
            t.avancer(0.1, _("dessin de la tenue"))
            png = ia.generer_image(params, "Fashion reference image of ONE outfit, on an invisible mannequin, plain light grey "
                                           "background, front view, even studio light, photorealistic, no person, no face, no text, no "
                                           "logo: " + texte)
            sortie = os.path.join(dossier, "_tenue_tmp.png")
            with open(sortie, "wb") as f:
                f.write(png)
            return sortie
        self._lancer(travail, _("Image de « {n} »", n=self.nom.text()), lambda r: r and self.enregistrer({"image_tenue": r}))

    def ajouter_fichier(self):
        from .widgets import ouvrir_fichier
        e = self.courante
        if e is None:
            return
        son = e["genre"] in ("voix", "musique", "style_musical")
        ch = ouvrir_fichier(self, _("Fichier"), SONS if son else IMAGES, "musique" if son else "image", self.params)
        if ch:
            n = len(e.get("fichiers") or {}) + 1
            self.enregistrer({("son" if son else "image") + str(n): ch})

    # ------------------------------------------------------------------ travaux (suivis, non bloquants)
    def _lancer(self, travail, texte, fin):
        t = Tache(travail, _("Ma bibliothèque de créations"))
        self.tache = t
        suivre_en_fond(self, t, texte)
        self.etat.setText(texte + "…")
        self.b_reduire.show()
        t.progression.connect(lambda f, tx="": self.etat.setText(f"{texte} : {tx or ''} {int(f * 100)} %"), Qt.QueuedConnection)

        def fini(r, err):
            try:
                self.b_reduire.hide()
                if err:
                    self.etat.setText("✕ " + texte_erreur(err)[:300])
                    return
                fin(r)
            except RuntimeError:
                pass
        t.fini.connect(fini, Qt.QueuedConnection)
        t.start()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _ameliorer(self, champ):
        from . import assistant_idee as I
        texte, quoi = champ.texte(), champ.quoi
        niveau = self.params.get("musique_ia_ecrire") or "claude"

        def fin(r):
            choisi = choisir_proposition(self, texte, r[0], r[1])
            if choisi is not None:
                champ.mettre(choisi)
        self._lancer(lambda _t: I.ameliorer_texte(self.params, texte, quoi, "", niveau), _("L'IA améliore le texte"), fin)

    def faire_fiche(self):
        from . import sequence_ia as Q
        e = copy.deepcopy(self.courante)
        images = [p for _r, p in self._photos(e)]
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Faire sa fiche"), _("La fiche est dessinée par Gemini (votre clef), environ 0,04 $. Continuer ?")) != QMessageBox.Yes:
            return
        p = Q.personnage(self.nom.text(), self.desc.texte(), (e.get("donnees") or {}).get("style", ""))
        p["genre"] = "objet" if e["genre"] == "objet" else "personne"
        p["images"] = images
        d = self._donnees()
        p["mode"] = d.get("mode") or ""
        if d.get("tenue"):
            p["tenue"] = d["tenue"]
        if p["mode"] in ("reel", "inspire") and images and e["genre"] != "objet" and not d.get("accord"):
            self.etat.setText(_("✕ Cochez d'abord l'accord de la personne des photos (ou que c'est vous)."))
            return
        seq = Q.nouvelle()
        params = self.params
        def travail(t):
            t.avancer(0.1, _("dessin de la fiche"))
            r = Q.planche_personnage(seq, p, params)
            return p.get("planche") or (r if isinstance(r, str) else "")
        self._lancer(travail, _("Fiche de « {n} »", n=p["nom"]), lambda r: r and self.enregistrer({"planche": r}))

    def voix_depuis_morceau(self, timbre):
        from . import creatif
        from . import musique_ia as MI
        from .dialogues_musique_ia import choisir_passage
        from .widgets import ouvrir_fichier
        if timbre and not self.extra["accord"].isChecked():
            self.etat.setText(_("Cochez d'abord l'accord de la personne (ou c'est vous)."))
            return
        manque = creatif.separation_manquante(self.params)
        if manque:
            QMessageBox.information(self, _("Voix"), manque)
            return
        ch = ouvrir_fichier(self, _("Morceau"), SONS, "musique", self.params)
        if not ch:
            return
        passage = choisir_passage(self, ch, _("Passage où la voix chante"), _("15 à 40 secondes où l'on entend bien la voix."))
        if not passage:
            return
        from .creations import dossier
        params, nom = self.params, os.path.splitext(os.path.basename(ch))[0][:50]

        def travail(t):
            p = MI.extraire_passage(ch, *passage)
            voix = creatif.extraire_voix(p, os.path.join(dossier(), nom + "_voix.wav"), params, lambda f, x="": t.avancer(0.8 * f, x), t.arret_demande)
            if timbre:
                MI.declarer(voix, voix_accord=True)
                return {"fichiers": {"voix_seule": voix}}
            r = MI.decrire_voix(voix, lambda f, x="": t.avancer(0.8 + 0.2 * f, x), t.arret_demande)
            return {"donnees": {"voix_decrite": {k: r[k] for k in ("en", "fr") if k in r}}}
        self._lancer(travail, _("La voix est isolée sur ce poste"),
                     lambda r: self.enregistrer(r.get("fichiers"), r.get("donnees")))

    def style_depuis_morceau(self):
        from . import musique_ia as MI
        from .dialogues_musique_ia import choisir_passage
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Morceau"), SONS, "musique", self.params)
        if not ch:
            return
        passage = choisir_passage(self, ch, _("Passage à écouter"), _("Tout le morceau, ou le passage qui donne le style."))
        if not passage:
            return
        params = self.params

        def travail(t):
            r = MI.analyser(MI.extraire_passage(ch, *passage), params, t.avancer, t.arret_demande)
            return {k: r[k] for k in ("caption_en", "resume", "bpm", "tonalite", "mesure") if k in r}

        def fin(r):
            if not self.desc.texte():
                self.desc.mettre(r.get("resume", ""))
            self.enregistrer(None, {"inspiration": r})
        self._lancer(travail, _("Ecoute du morceau sur ce poste"), fin)

    def done(self, r):
        if garder_calcul(self, self._en_calcul()):
            return
        super().done(r)


# ------------------------------------------------------------------ pour les autres fenêtres (Séquence IA, clip, Fabrique musique)
def choisir_entree(parent, params, genres, titre=None):
    """Petite fenêtre « Depuis ma bibliothèque » : la liste des entrées des genres voulus (vignette, nom, résumé) ; renvoie
    l'entrée choisie ou None. Essais : parent._test_biblio = nom de l'entrée à prendre."""
    entrees = B.lister(params, genres)
    essai = getattr(parent, "_test_biblio", None)
    if essai is not None:
        return next((e for e in entrees if e["nom"] == essai), None)
    if not entrees:
        QMessageBox.information(parent, titre or _("Ma bibliothèque de créations"),
                                _("Rien encore de ce genre dans votre bibliothèque : « ☆ Garder » sur une création, ou Fabrique IA › "
                                  "« Ma bibliothèque de créations… » › « Nouveau… »."))
        return None
    d = QDialog(parent)
    d.setWindowTitle(titre or _("Depuis ma bibliothèque"))
    v = QVBoxLayout(d)
    lst = QListWidget()
    lst.setIconSize(QSize(64, 48))
    lst.setWordWrap(True)
    lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    for e in entrees:
        it = QListWidgetItem(f"{e['nom']}\n{B.resume(e)[:110]}")
        ap = B.apercu(e)
        if ap:
            it.setIcon(QIcon(QPixmap(ap).scaled(64, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        lst.addItem(it)
    lst.setCurrentRow(0)
    lst.itemDoubleClicked.connect(lambda _i: d.accept())
    v.addWidget(lst, 1)
    h = QHBoxLayout()
    h.addStretch(1)
    for lib, fn in ((_("Annuler"), d.reject), (_("Prendre"), d.accept)):
        b = QPushButton(lib)
        b.clicked.connect(fn)
        h.addWidget(b)
    v.addLayout(h)
    d.resize(560, 420)
    if d.exec() != QDialog.Accepted or lst.currentRow() < 0:
        return None
    return entrees[lst.currentRow()]


def garder_rapide(parent, params, genre, nom, description="", fichiers=None, donnees=None):
    """« ☆ Garder » depuis une autre fenêtre : le nom est demandé (proposé), puis l'entrée est rangée. Renvoie l'entrée ou None."""
    from PySide6.QtWidgets import QInputDialog
    essai = getattr(parent, "_test_precision", None)
    if essai is not None:
        choisi, ok = (essai or nom), True
    else:
        choisi, ok = QInputDialog.getText(parent, _("Garder dans ma bibliothèque"), _("Nom sous lequel le retrouver :"), QLineEdit.Normal, nom)
    if not ok or not (choisi or "").strip():
        return None
    return B.garder(params, genre, choisi.strip(), description, fichiers, donnees)
