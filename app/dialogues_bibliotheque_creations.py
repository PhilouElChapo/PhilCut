"""Fenêtre « Ma bibliothèque de créations » (0.9.81) : voir, créer, nommer, compléter et retirer ce qui est gardé
(personnages, musiciens, objets, lieux, voix, styles, musiques, images). Voir bibliotheque_creations.py."""
import copy
import os

from PySide6.QtCore import QSize, Qt, QTimer
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



CONSIGNE_DECRIRE = {
    "personnage": ("Tu écris la description d'un personnage pour une fiche de création vidéo, d'après des photos. Décris seulement "
                   "ce qu'on voit : allure générale, âge apparent, cheveux (couleur, longueur, coiffure), carrure, traits du visage "
                   "en termes généraux, tenue et style, attitude. Ne nomme jamais la personne, ne devine jamais qui elle est, ne "
                   "parle pas des photos elles-mêmes (défilé, magazine). Réponds en français, en 2 à 4 phrases, sans liste ni titre."),
    "objet": ("Tu écris la description d'un objet ou d'un véhicule pour une fiche de création vidéo, d'après des photos : forme, "
              "couleurs, matières, détails reconnaissables, état. Pas de marque ni d'immatriculation. Réponds en français, en 2 à "
              "3 phrases, sans liste."),
    "lieu": ("Tu écris la description d'un lieu pour une fiche de création vidéo, d'après des photos : type d'endroit, ambiance, "
             "lumière, matériaux, couleurs, éléments marquants. Pas de nom de lieu réel ni d'enseigne. Réponds en français, en 2 à "
             "3 phrases, sans liste."),
}

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
        bt = QPushButton(_("Toute faite…"))
        bt.setToolTip(_("La bibliothèque toute faite : tenues, lieux, véhicules, avions, personnages types ; prenez-en une, "
                        "puis modifiez-la"))
        bt.clicked.connect(self.depuis_catalogue)
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
        from .credit_ia import LignesCredit           # 0.9.95 : fiches et images par Gemini, textes par Claude ou Gemini
        self.credits = LignesCredit(self.params, ["google", "anthropic"], self).surveiller(self.etat)
        v.addWidget(self.credits)
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
        planche = (e.get("fichiers") or {}).get("planche")
        ap = planche or B.apercu(e)              # 1.1.10 : la fiche reste en grand ; la vignette ne sert qu'à la liste
        if ap:
            im = QLabel()
            im.setPixmap(QPixmap(ap).scaled(420, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.v_detail.addWidget(im)
        if e["genre"] in ("personnage", "musicien", "objet"):
            self.v_detail.addWidget(aide(_("✓ Fiche faite : c'est elle que les moteurs vidéo reçoivent pour garder le même visage (ou "
                                           "le même objet) d'un plan à l'autre.") if planche else
                                         _("Pas encore de fiche : « Faire sa fiche (Gemini)… » en bas (face, trois quarts, profil, "
                                           "en pied).")))
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
        if e["genre"] == "groupe":                         # 1.1.12 : les musiciens du groupe, chacun par sa fiche
            self.v_detail.addWidget(QLabel(_("Musiciens du groupe")))
            lm = QListWidget()
            lm.setIconSize(QSize(48, 36))
            lm.setWordWrap(True)
            lm.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            lm.setMaximumHeight(170)
            for m in B.membres(self.params, e):
                self._ligne_groupe(lm, m)
            self.extra["membres"] = lm
            self.v_detail.addWidget(lm)
            h = QHBoxLayout()
            b = QPushButton(_("Ajouter un musicien…"))
            b.setToolTip(_("Un musicien ou un personnage de votre bibliothèque"))
            b.clicked.connect(self._ajouter_au_groupe)
            h.addWidget(b)
            b = QPushButton(_("Retirer du groupe"))
            b.clicked.connect(lambda: lm.takeItem(lm.currentRow()) if lm.currentRow() >= 0 else None)
            h.addWidget(b)
            h.addStretch(1)
            self.v_detail.addLayout(h)
            self.v_detail.addWidget(aide(_("Clip de groupe › « Prendre un groupe de ma bibliothèque… » : ces musiciens jouent avec "
                                           "leurs visages. « Enregistrer » garde la liste.")))
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
            # 1.2.0 : variantes (chaude, aiguë…) et les 7 réglages, dans « Mes voix… »
            vs = d.get("variantes") or []
            hv = QHBoxLayout()
            hv.addWidget(QLabel(_("Variantes : {v}", v=", ".join(v["nom"] for v in vs) if vs else _("aucune"))))
            bv = QPushButton(_("Variantes et réglages…"))
            bv.setToolTip(_("Ouvre « Mes voix… » sur cette voix : curseurs, pré-écoute, « + Ajouter une variante »"))
            bv.clicked.connect(lambda: self.variantes_voix(e))
            hv.addWidget(bv)
            hv.addStretch(1)
            self.v_detail.addLayout(hv)
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
            bc = QPushButton(_("Composer…"))
            bc.setToolTip(_("Pièce par pièce : haut, bas ou robe, veste, chaussures, chapeau, accessoire, matière"))
            bc.clicked.connect(self.composer_tenue)
            h.addWidget(bc)
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

    @staticmethod
    def _ligne_groupe(lm, m):
        it = QListWidgetItem(f"{m.get('nom', '')} — {m.get('role', '')}")
        if m.get("image") and os.path.exists(m["image"]):
            it.setIcon(QIcon(QPixmap(m["image"]).scaled(48, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
        it.setData(Qt.UserRole, {k: m.get(k, "") for k in ("role", "nom", "description", "biblio", "genre")})
        lm.addItem(it)

    def _ajouter_au_groupe(self):
        x = choisir_entree(self, self.params, ("musicien", "personnage"))
        if x is None or "membres" not in self.extra:
            return
        d = x.get("donnees") or {}
        self._ligne_groupe(self.extra["membres"], {"role": d.get("instrument", ""), "nom": x["nom"], "genre": x["genre"],
                                                   "description": x.get("description", ""), "biblio": x["id"],
                                                   "image": (x.get("fichiers") or {}).get("planche") or B.apercu(x)})

    def _donnees(self):
        e = self.courante
        d = dict(e.get("donnees") or {})
        if "membres" in self.extra:
            lm = self.extra["membres"]
            d["membres"] = [lm.item(i).data(Qt.UserRole) for i in range(lm.count())]
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
        self.etat.setText(B.GENRES[genre][1])

        def ecrire_tout_de_suite():               # 0.9.96 : après la fermeture du menu « Nouveau… », qui reprenait le focus
            if hasattr(self, "nom"):
                self.activateWindow()
                self.nom.setFocus(Qt.OtherFocusReason)
                self.nom.selectAll()
        ecrire_tout_de_suite()
        QTimer.singleShot(120, ecrire_tout_de_suite)

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
        choisie = (e.get("donnees") or {}).get("vignette")
        for role, p in photos[:8]:
            col = QVBoxLayout()
            im = QLabel()
            im.setPixmap(QPixmap(p).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            im.setToolTip(os.path.basename(p) + "\n" + _("Clic : en faire la vignette de « {n} »", n=e.get("nom", "")))
            im.setCursor(Qt.PointingHandCursor)
            if role == choisie:
                im.setStyleSheet("border: 3px solid #8b7cff;")
            im.mousePressEvent = lambda _ev, r=role: self.choisir_vignette(r)
            col.addWidget(im)
            bx = QToolButton()
            bx.setText("✕")
            bx.setToolTip(_("Retirer cette photo"))
            bx.clicked.connect(lambda _c=False, r=role: self.retirer_photo(r))
            col.addWidget(bx, 0, Qt.AlignHCenter)
            h.addLayout(col)
        h.addStretch(1)
        self.v_detail.addLayout(h)
        h = QHBoxLayout()                      # 1.1.9 : les boutons sur leur propre rangée (ils sortaient de la fenêtre)
        b = QPushButton(_("Ajouter des photos…"))
        b.clicked.connect(self.ajouter_photos)
        h.addWidget(b)
        if photos:
            bd = QPushButton(_("Décrire d'après les photos…"))
            bd.setToolTip(_("L'IA écrit la description de ce qu'on voit (allure, cheveux, âge apparent, tenue, style), sans jamais "
                            "dire qui c'est ; avec « Inventé », on crée alors quelqu'un de nouveau qui en garde l'esprit"))
            bd.clicked.connect(self.decrire_photos)
            h.addWidget(bd)
        br = QPushButton(_("Image d'un rush…"))
        br.setToolTip(_("Placez la ligne rouge sur un rush (ou une photo du montage) où on le voit : PhilCut prend l'image, vous "
                        "l'encadrez. Recommencez avec d'autres rushes pour d'autres angles."))
        br.clicked.connect(self.photo_ligne_rouge)
        h.addWidget(br)
        h.addStretch(1)
        self.v_detail.addLayout(h)

    def choisir_vignette(self, role):
        """1.1.7 : la photo cliquée devient la vignette de l'entrée (liste, choix depuis les autres fenêtres)."""
        e = self.courante
        if e is None:
            return
        d = dict(e.get("donnees") or {}, vignette=role)   # seulement la vignette : rien d'autre du formulaire n'est enregistré
        nom, desc = self.nom.text(), self.desc.texte()       # ce qui est tapé et pas encore enregistré reste à l'écran
        x = B.garder(self.params, e["genre"], e["nom"], e.get("description", ""), None, d, e["id"])
        self.remplir(x["id"])
        self.nom.setText(nom)
        self.desc.mettre(desc)
        self.etat.setText(_("✓ Vignette choisie."))

    PRIX_DECRIRE = 0.01

    def decrire_photos(self):
        """1.1.7 (Philippe, 21/11 22h36 : « une description en fonction des photos ; ça permet de créer du non réel sur du
        réel ») : l'IA décrit ce qu'elle voit, sans identifier personne ; la description se relit et se modifie."""
        from . import ia
        e = self.courante
        images = [p for _r, p in self._photos(e)][:4] if e else []
        if not images:
            return
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Décrire d'après les photos"), _("Les photos sont envoyées à votre IA (Claude ou Gemini, votre clef) pour "
                                                        "écrire la description : environ {p} $. Continuer ?",
                                                        p=f"{self.PRIX_DECRIRE:.2f}".replace(".", ","))) != QMessageBox.Yes:
            return
        genre, params = e["genre"], self.params
        consigne = CONSIGNE_DECRIRE.get(genre, CONSIGNE_DECRIRE["personnage"])
        texte = self.desc.texte()

        def travail(_t):
            from .assistant_creation import _jpeg
            octets = [_jpeg(p) for p in images]           # l'IA reçoit des octets (JPEG réduit), jamais des chemins
            return ia.demander(params, consigne, _("Décrivez ce que montrent ces photos."), images=octets, max_jetons=600).strip()

        def fin(r):
            if not r:
                return
            choisi = choisir_proposition(self, texte, r, _("D'après les photos")) if texte.strip() else r
            if choisi is not None:
                self.desc.mettre(choisi)
                self.etat.setText(_("Description écrite d'après les photos : relisez-la. Pour quelqu'un de nouveau qui n'est pas la "
                                    "personne des photos, choisissez « Inventé » : les photos ne sont plus envoyées, seule cette "
                                    "description compte."))
        self._lancer(travail, _("L'IA décrit les photos"), fin)

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
            image = A.decouper(image, boite, os.path.join(tempfile.mkdtemp(), "rush.png"), detourer=False)
            if not image:
                return
            methode = getattr(self, "_test_isoler", None) or self.choisir_isolement(e, image)
            if not methode:
                return
            if methode == "local":
                A.detourer_decoupe(image)
            elif methode == "gemini":
                quoi = {"objet": "object", "tenue": "outfit"}.get(e["genre"], "person")
                cle = f"image{self._prochain(e)}"

                def fin(chemin):
                    self._mode_reel()
                    self.enregistrer({cle: chemin})
                self._lancer(lambda t: A.isoler_gemini(image, quoi, self.params), _("Gemini isole « {n} »", n=e["nom"]), fin)
                return
        if image:
            self._mode_reel()
            self.enregistrer({f"image{self._prochain(e)}": image})

    def choisir_isolement(self, e, image):
        """0.9.96 : comment garder ce qui est encadré : le cadre tel quel, détouré sur ce poste (personnes, avec le modèle de
        détourage), ou isolé par Gemini sur fond blanc (le plus propre, environ 0,04 $). "" = annulé."""
        from PySide6.QtGui import QPixmap
        from . import assistant_creation as A
        m = QMessageBox(self)
        m.setWindowTitle(_("Garder ce qui est encadré"))
        m.setText(_("Comment garder « {n} » ?", n=e["nom"]))
        m.setInformativeText(_("Le plus propre : Gemini garde seulement le sujet du cadre, entier, sur fond blanc (les voisins et "
                               "le décor disparaissent), sans le changer. Le cadre tel quel convient aussi : les IA s'y "
                               "retrouvent si le sujet le remplit bien."))
        px = QPixmap(image)
        if not px.isNull():
            m.setIconPixmap(px.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        boutons = {}
        if self.params.get("clef_gemini"):
            boutons["gemini"] = m.addButton(_("Isoler par Gemini (environ {p})", p="0,04 $"), QMessageBox.AcceptRole)
        if e["genre"] in ("personnage", "musicien") and A.detourage_local_possible():
            boutons["local"] = m.addButton(_("Détourer sur ce poste (gratuit)"), QMessageBox.AcceptRole)
        boutons["cadre"] = m.addButton(_("Garder le cadre tel quel"), QMessageBox.AcceptRole)
        annuler = m.addButton(_("Annuler"), QMessageBox.RejectRole)
        m.setDefaultButton(boutons.get("gemini") or boutons["cadre"])
        m.exec()
        clique = m.clickedButton()
        if clique is annuler:
            return ""
        return next((k for k, b in boutons.items() if b is clique), "")

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

    def depuis_catalogue(self):
        from .dialogues_catalogue_prompts import DialogueCatalogue
        d = DialogueCatalogue(self, self.params)
        d.exec()
        if d.ajoutees:
            self.filtre.setCurrentIndex(0)
            self.remplir(d.ajoutees[-1]["id"])

    def composer_tenue(self):
        from .dialogues_catalogue_prompts import ComposerTenue
        d = ComposerTenue(self)
        if d.exec() == QDialog.Accepted and d.resultat and d.resultat[0]:
            fr, en = d.resultat
            self.desc.mettre(fr)
            self.enregistrer(donnees={"en": en, "fr_origine": fr})

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
        li = {"nom": self.nom.text(), "description": self.desc.texte(), "en": self._anglais_pret(e), "images": [p for _r, p in self._photos(e)],
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
        texte = self._anglais_pret(e) or Q._anglais(self.desc.texte(), True)
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

    def _anglais_pret(self, e):
        """Les mots anglais du catalogue, tant que la description n'a pas été changée."""
        d = e.get("donnees") or {}
        return d.get("en", "") if d.get("en") and self.desc.texte().strip() == (d.get("fr_origine") or e.get("description", "")).strip() \
            else ""

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
        if not texte.strip():                  # 1.1.7 : dit tout de suite, sans lancer de calcul (ni écrire au journal)
            self.etat.setText(_("Ecrivez d'abord quelques mots, ou « Décrire d'après les photos… »."))
            return
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
        p["en"] = self._anglais_pret(e)
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

    def variantes_voix(self, e):
        from .dialogues_mes_voix import DialogueMesVoix
        d = DialogueMesVoix(self, self.params)
        d.recherche.setText(e["nom"])
        for i in range(d.arbre.topLevelItemCount()):
            it = d.arbre.topLevelItem(i)
            x = it.data(0, Qt.UserRole) or (None, None, None)
            if x[0] == "mienne" and x[1]["id"] == e["id"]:
                d.arbre.setCurrentItem(it.child(0))
        if getattr(self, "_test_variantes", None):
            return self._test_variantes(d)
        d.b_ok.hide()
        d.exec()
        self.remplir() if hasattr(self, "remplir") else None
        return d

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
def choisir_entree(parent, params, genres, titre=None, plusieurs=False, vide=None):
    """Petite fenêtre « Depuis ma bibliothèque » : la liste des entrées des genres voulus (vignette, nom, résumé) ; renvoie
    l'entrée choisie ou None. Essais : parent._test_biblio = nom de l'entrée à prendre."""
    entrees = B.lister(params, genres)
    essai = getattr(parent, "_test_biblio", None)
    if essai is not None:
        if plusieurs:                                # 1.3.11 : plusieurs à la fois (noms séparés par « | »)
            return [e for n in str(essai).split("|") for e in entrees if e["nom"] == n]
        return next((e for e in entrees if e["nom"] == essai), None)
    if not entrees:
        QMessageBox.information(parent, titre or _("Ma bibliothèque de créations"),
                                vide or _("Rien encore de ce genre dans votre bibliothèque : « ☆ Garder » sur une création, ou "
                                          "Fabrique IA › « Ma bibliothèque de créations… » › « Nouveau… »."))
        return [] if plusieurs else None
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
    if plusieurs:                                    # 1.3.11 : Ctrl-clic ou Maj-clic pour en prendre plusieurs
        from PySide6.QtWidgets import QAbstractItemView
        lst.setSelectionMode(QAbstractItemView.ExtendedSelection)
        lb = QLabel(_("Ctrl-clic pour en prendre plusieurs."))
        lb.setWordWrap(True)
        v.addWidget(lb)
    else:
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
        return [] if plusieurs else None
    if plusieurs:
        return [entrees[lst.row(it)] for it in sorted(lst.selectedItems(), key=lst.row)]
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
