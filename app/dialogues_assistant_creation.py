"""Fenêtre de l'assistant de création : de l'idée au résultat (0.9.79, méthode commune en 0.9.80).

On dit en quelques mots ce que l'on veut ; l'assistant en déduit le genre (suite d'un plan, scène, musique ou chanson),
les éléments nécessaires et le déroulé, tout pré-rempli. Chaque élément est une carte où l'on choisit d'où il vient (dans
l'image, une photo, un morceau à moi, en ligne, le décrire, la liste, l'inventer…), chaque possibilité expliquée ; tout
texte peut être amélioré par l'IA (les deux versions sont montrées). Voir assistant_idee.py (la méthode, la musique) et
assistant_creation.py (la vidéo). Le mode manuel (Séquence IA, Fabrique musique) reste à un clic, pré-rempli."""
import copy
import os
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPushButton, QRadioButton, QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import assistant_creation as A
from . import assistant_idee as I
from . import sequence_ia as Q
from .cartes_assistant import COULEURS, CarteElement, ChampAmeliorable, ImageCadres, aide, choisir_proposition, vider
from .langue import _
from .taches import Tache, texte_erreur
from .widgets import garder_calcul, suivre_en_fond

P_IDEE, P_QUI, P_PLANS, P_IMAGES, P_VIDEO, P_M_ELEM, P_M_DEROULE, P_M_PAROLES, P_M_CREER = range(9)
ETAPES = {"video": ((P_IDEE, _("1. Votre idée")), (P_QUI, _("2. Qui et quoi")), (P_PLANS, _("3. Les plans")), (P_IMAGES, _("4. Les images")),
                    (P_VIDEO, _("5. La vidéo"))),
          "musique": ((P_IDEE, _("1. Votre idée")), (P_M_ELEM, _("2. Ce qu'il faut")), (P_M_DEROULE, _("3. Le déroulé")),
                      (P_M_PAROLES, _("4. Les paroles")), (P_M_CREER, _("5. La musique")))}
BOUTONS = {P_IDEE: _("Voir ce qu'il faut ›"), P_QUI: _("C'est bien eux ›"), P_PLANS: _("Préparer les images ›"),
           P_IMAGES: _("Tout me convient : fabriquer la vidéo ›"), P_VIDEO: _("Poser dans le film"), P_M_ELEM: _("Tout est prêt ›"),
           P_M_DEROULE: _("Les paroles ›"), P_M_PAROLES: _("Vers la création ›"), P_M_CREER: _("Poser sous la vidéo")}
SONS = _("Sons") + " (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.mp4 *.mkv *.webm *.mov)"
ENERGIES = (("calme", _("Calme")), ("moyenne", _("Moyenne")), ("forte", _("Forte")))


def _alpha(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


class Vignette(QLabel):
    """Image réduite ; un clic l'agrandit (pour juger un visage)."""
    clic = Signal(str)

    def __init__(self, chemin="", largeur=230, vide=""):
        super().__init__()
        self.chemin = chemin
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(largeur, int(largeur * 0.56))
        self.setStyleSheet("border:1px solid #555;border-radius:6px")
        self.setWordWrap(True)
        if chemin and os.path.exists(chemin):
            self.setPixmap(QPixmap(chemin).scaled(largeur, int(largeur * 0.8), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip(_("Cliquez pour agrandir"))
        else:
            self.setText(vide)

    def mouseReleaseEvent(self, e):
        if self.chemin and os.path.exists(self.chemin):
            self.clic.emit(self.chemin)


def agrandir(parent, chemin):
    d = QDialog(parent)
    d.setWindowTitle(_("Image"))
    v = QVBoxLayout(d)
    lb = QLabel()
    lb.setPixmap(QPixmap(chemin).scaled(960, 620, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    v.addWidget(lb)
    b = QPushButton(_("Fermer"))
    b.clicked.connect(d.accept)
    v.addWidget(b, 0, Qt.AlignRight)
    d.exec()


def _defile(widget):
    z = QScrollArea()
    z.setWidgetResizable(True)
    z.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    z.setWidget(widget)
    return z


class DialogueAssistant(QDialog):
    def __init__(self, ed, clip=None):
        super().__init__(ed)
        self.ed, self.params, self.clip = ed, ed.params, clip
        self.seq = Q.nouvelle(ed.projet.format)
        self.musique = None                          # état de la musique (assistant_idee) quand c'en est une
        self.genre = "video"
        self._genre_choisi = False
        self.image, self.tache, self.taches, self.file = "", None, [], []
        self.cartes = []
        self.setWindowTitle(_("Assistant de création : de l'idée au résultat"))
        self.resize(1000, 720)
        v = QVBoxLayout(self)
        self.fil = QLabel("")
        self.fil.setWordWrap(True)
        v.addWidget(self.fil)
        self.pages = QStackedWidget()
        for fabrique in (self._page_idee, self._page_qui, self._page_plans, self._page_images, self._page_video,
                         self._page_m_elements, self._page_m_deroule, self._page_m_paroles, self._page_m_creer):
            self.pages.addWidget(fabrique())
        v.addWidget(self.pages, 1)
        # --- toujours là : écrire librement, budget, état, navigation
        hl = QHBoxLayout()
        self.libre = QLineEdit()
        self.libre.setPlaceholderText(_("Ou dites-le en clair : « le chauffeur plus âgé », « le passage lent plus long »…"))
        self.libre.returnPressed.connect(self.dire)
        hl.addWidget(self.libre, 1)
        self.b_dire = QPushButton(_("Envoyer"))
        self.b_dire.clicked.connect(self.dire)
        hl.addWidget(self.b_dire)
        v.addLayout(hl)
        self.l_budget = QLabel("")
        self.l_budget.setTextFormat(Qt.RichText)
        self.l_budget.setWordWrap(True)
        v.addWidget(self.l_budget)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        v.addWidget(self.etat)
        hn = QHBoxLayout()
        self.b_prec = QPushButton(_("‹ Précédent"))
        self.b_prec.clicked.connect(self.precedent)
        hn.addWidget(self.b_prec)
        self.b_suiv = QPushButton(_("Suivant ›"))
        self.b_suiv.setProperty("primaire", True)
        self.b_suiv.setStyleSheet("font-weight:600")
        self.b_suiv.clicked.connect(self.suivant)
        hn.addWidget(self.b_suiv)
        hn.addStretch(1)
        self.b_manuel = QPushButton(_("Régler moi-même…"))
        self.b_manuel.setToolTip(_("Ouvre ce qui est préparé dans la fenêtre habituelle (Séquence IA, Fabrique musique) : tout y est "
                                   "réglable, rien n'est perdu"))
        self.b_manuel.clicked.connect(self.mode_manuel)
        hn.addWidget(self.b_manuel)
        self.b_reduire = QPushButton(_("Réduire"))
        self.b_reduire.setToolTip(_("Le calcul continue ; « Afficher la fenêtre » dans la barre du bas la rouvre"))
        self.b_reduire.clicked.connect(self.hide)
        self.b_reduire.hide()
        hn.addWidget(self.b_reduire)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        hn.addWidget(b)
        v.addLayout(hn)
        self._preparer_depart()
        self.aller(P_IDEE)

    # ------------------------------------------------------------------ outils de page
    def _titre(self, texte):
        lb = QLabel(texte)
        lb.setWordWrap(True)
        lb.setStyleSheet("font-size:15px;font-weight:600")
        return lb

    def _aide(self, texte):
        return aide(texte)

    def _table(self, t, etroites, large):
        t.verticalHeader().setVisible(False)
        t.setWordWrap(True)
        t.setTextElideMode(Qt.ElideNone)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for c in etroites:
            t.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(large, QHeaderView.Stretch)
        t.itemChanged.connect(lambda _i: t.resizeRowsToContents())

    def _niveau(self):
        return self.niveau.currentData()

    def _cloud(self):
        return self._niveau() != "locale"

    # ------------------------------------------------------------------ 1. l'idée
    def _page_idee(self):
        w = QWidget()
        h = QHBoxLayout(w)
        self.v_depart = QVBoxLayout()
        h.addLayout(self.v_depart)
        v = QVBoxLayout()
        v.addWidget(self._titre(_("Que voulez-vous faire ?")))
        v.addWidget(self._aide(_("Dites-le en quelques mots, comme vous le raconteriez. L'assistant en déduit ce qu'il faut (personnes, "
                                 "objets, style, voix, paroles…) et le déroulé ; vous n'aurez plus qu'à valider ou corriger, carte par "
                                 "carte.")))
        self.c_histoire = ChampAmeliorable("", "idee", 0, self.ameliorer,
                                           _("ex. : Les deux femmes descendent les marches puis vont vers une limousine noire ; un chauffeur "
                                             "leur ouvre la portière et la limousine s'éloigne.\nou : une ballade rock de 3 minutes, rapide au "
                                             "début, avec au milieu un long passage lent et entraînant, voix chaude."))
        self.histoire = self.c_histoire.t
        self.c_histoire.change.connect(self._deviner)
        v.addWidget(self.c_histoire, 1)
        v.addWidget(QLabel(_("L'assistant comprend :")))
        self.g_genre = QButtonGroup(self)
        self.r_suite = QRadioButton(_("La suite de ce plan (elle part de sa dernière image, avec les mêmes personnes)"))
        self.r_scene = QRadioButton(_("Une nouvelle scène vidéo, en plusieurs plans"))
        self.r_musique = QRadioButton(_("Une musique ou une chanson"))
        self.r_logo = QRadioButton(_("Une intro ou un logo animé (fenêtre habituelle pour l'instant)"))
        for r in (self.r_suite, self.r_scene, self.r_musique, self.r_logo):
            self.g_genre.addButton(r)
            r.clicked.connect(lambda _c=False: setattr(self, "_genre_choisi", True))
            v.addWidget(r)
        self.l_rush = self._aide("")
        v.addWidget(self.l_rush)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel(_("Qui vous assiste ?")))
        self.niveau = QComboBox()
        for k, lib in A.niveaux(self.params):
            self.niveau.addItem(lib, k)
        voulu = self.params.get("musique_ia_ecrire")
        self.niveau.setCurrentIndex(max(0, self.niveau.findData(voulu)) if voulu else 0)
        h2.addWidget(self.niveau, 1)
        v.addLayout(h2)
        self.l_manques = QLabel("")
        self.l_manques.setWordWrap(True)
        self.l_manques.setStyleSheet("color:#c98a00")
        v.addWidget(self.l_manques)
        h.addLayout(v, 1)
        return w

    def _preparer_depart(self):
        """L'image d'où part la suite : la dernière image du plan choisi (ou la photo)."""
        p, c = self.ed.projet, self.clip
        m = p.media(c["media"]) if c else None
        ok = bool(c and m and m.get("genre") in ("video", "image") and os.path.exists(m.get("chemin") or ""))
        if ok:
            if m.get("genre") == "image":
                self.image = m["chemin"]
            else:
                from . import prolonger
                self.image = prolonger._image(m["chemin"], float(c["src_fin"]) - 1.5 / max(1.0, float(p.cadence)),
                                              os.path.join(Q.dossier(self.seq), "depart.png"))
                ok = os.path.exists(self.image)
        self.r_suite.setEnabled(ok)
        (self.r_suite if ok else self.r_scene).setChecked(True)
        self.l_rush.setText(_("Plan choisi : « {n} ».", n=c.get("nom") or m.get("nom", "")) if ok else
                            _("Pour continuer un plan : clic droit sur le plan dans la timeline › « Continuer ce plan avec "
                              "l'assistant IA… »."))
        self.l_manques.setText(" ".join(A.manques(self.params)))
        if ok:
            self.v_depart.addWidget(QLabel(_("La suite part de cette image :")))
            vg = Vignette(self.image, 260)
            vg.clic.connect(lambda ch: agrandir(self, ch))
            self.v_depart.addWidget(vg)
            self.v_depart.addStretch(1)

    def _deviner(self):
        """Le genre se déduit des mots au fil de la frappe, tant que l'utilisateur n'a pas choisi lui-même."""
        if self._genre_choisi:
            return
        g = I.deviner_genre(self.c_histoire.texte(), bool(self.image))
        {"suite": self.r_suite, "scene": self.r_scene, "musique": self.r_musique, "logo": self.r_logo}[g].setChecked(True)

    def choisir_genre(self, genre):
        """Ouvert depuis le menu Musique : la musique est choisie d'office (on peut encore changer), si l'on est au début."""
        if self.pages.currentIndex() == P_IDEE:
            {"musique": self.r_musique, "scene": self.r_scene, "suite": self.r_suite}[genre].setChecked(True)
            self._genre_choisi = True

    def _suite(self):
        return self.genre == "video" and self.r_suite.isChecked() and bool(self.image)

    # ------------------------------------------------------------------ améliorer un texte (tout champ)
    def ameliorer(self, champ, contexte=""):
        if self._en_calcul():
            return
        texte, quoi, niveau = champ.texte(), champ.quoi, self._niveau()
        ctx = contexte or (self.c_histoire.texte() if champ is not self.c_histoire else "")

        def fin(r, e):
            if e or not r:
                return
            if self._cloud():
                A.depenser(self._etat_budget(), _("Texte amélioré"), A.PRIX_LECTURE)
            neuf, pourquoi = r
            choisi = choisir_proposition(self, texte, neuf, pourquoi)
            if choisi is not None:
                champ.mettre(choisi)
                self.etat.setText("✓ " + _("Texte amélioré."))
            else:
                self.etat.setText(_("Votre texte est gardé."))
        self._lancer(lambda _t: I.ameliorer_texte(self.params, texte, quoi, ctx, niveau), _("L'IA améliore le texte"), fin)

    def _etat_budget(self):
        return self.musique if self.genre == "musique" and self.musique is not None else self.seq

    # ------------------------------------------------------------------ 2. qui et quoi (vidéo) : les cartes
    def _page_qui(self):
        w = QWidget()
        h = QHBoxLayout(w)
        self.v_image = QVBoxLayout()
        h.addLayout(self.v_image)
        v = QVBoxLayout()
        v.addWidget(self._titre(_("Qui et quoi voit-on ? Une carte par personne et par objet important")))
        v.addWidget(self._aide(_("L'assistant a déduit une fiche par personne (jamais deux personnes sur une fiche) et par objet qui revient. "
                                 "Pour chacune, dites d'où elle vient : dans l'image (le cadre de même couleur ; cliquez ou tracez pour le "
                                 "corriger), une photo à vous, ou inventée d'après sa description. « ✨ Améliorer » reformule la "
                                 "description.")))
        self.w_cartes = QWidget()
        self.v_cartes = QVBoxLayout(self.w_cartes)
        v.addWidget(_defile(self.w_cartes), 1)
        hb = QHBoxLayout()
        for lib, genre in ((_("+ Une personne"), "personne"), (_("+ Un objet"), "objet")):
            b = QPushButton(lib)
            b.clicked.connect(lambda _c=False, g=genre: self._ajouter_carte(g))
            hb.addWidget(b)
        hb.addStretch(1)
        v.addLayout(hb)
        self.accord = QCheckBox(_("Les personnes réelles (de l'image ou des photos) sont d'accord pour être animées par l'IA (ou c'est moi)"))
        v.addWidget(self.accord)
        h.addLayout(v, 1)
        return w

    def _element_de(self, p):
        return I.element(p.get("genre", "personne"), p["nom"], p.get("brut") or p.get("description", ""),
                         p.get("source") or ("image" if p.get("sur_image") else "inventer"), genre=p.get("genre", "personne"),
                         boite=p.get("boite"), photo=p.get("photo", ""), decoupe=p.get("decoupe", ""), style=p.get("style", ""),
                         position=p.get("position", ""))

    def _remplir_cartes(self):
        vider(self.v_cartes)
        self.cartes = []
        for p in self.seq["personnages"]:
            self._carte(self._element_de(p))
        self.v_cartes.addStretch(1)
        vider(self.v_image)
        self.image_cadres = None
        if self._suite():
            self.image_cadres = ImageCadres(self.image, 320)
            self.image_cadres.trace.connect(self._cadre_trace)
            self.v_image.addWidget(QLabel(_("Dernière image du plan :")))
            self.v_image.addWidget(self.image_cadres)
            self.v_image.addWidget(self._aide(_("Cliquez une carte, puis cliquez ou tracez ici la personne ou l'objet.")))
            self.v_image.addStretch(1)
        self.accord.setChecked(any(p.get("accord") for p in self.seq["personnages"]))
        self._maj_cadres()

    def _carte(self, e):
        k = len(self.cartes)
        sources = I.sources(e["type"])
        if not self._suite():
            sources = [s for s in sources if s[0] != "image"]
            if e.get("source") == "image":
                e["source"] = "inventer"
        c = CarteElement(e, sources, self._options_personne, I.manque, self.ameliorer, COULEURS[k % len(COULEURS)], self._retirer_carte,
                         _("Personne") if e["type"] == "personne" else _("Objet"))
        c.change.connect(self._maj_cadres)
        c.active.connect(self._activer)
        self.cartes.append(c)
        self.v_cartes.insertWidget(len(self.cartes) - 1, c)
        return c

    def _ajouter_carte(self, genre):
        n = sum(1 for c in self.cartes if c.e["type"] == genre) + 1
        nom = _("Personne {n}", n=n) if genre == "personne" else _("Objet {n}", n=n)
        e = I.element(genre, nom, "", "image" if self._suite() else "inventer", genre=genre)
        if self._suite():
            e["boite"] = A.boite_par_defaut({})
        c = self._carte(e)
        self._activer(c)
        self._maj_cadres()

    def _retirer_carte(self, c):
        if c in self.cartes:
            self.cartes.remove(c)
            c.hide()
            c.setParent(None)
            c.deleteLater()
            self._maj_cadres()

    def _activer(self, c):
        self._active = c
        for x in self.cartes:
            x.setStyleSheet(f"CarteElement{{border:{3 if x is c else 2}px solid {x._couleur};border-radius:8px}}")
        self._maj_cadres()

    def _maj_cadres(self):
        if getattr(self, "image_cadres", None) is None:
            return
        actif = getattr(self, "_active", None)
        self.image_cadres.cadres = [(k + 1, c._couleur, c.e.get("boite") if c.e.get("source") == "image" else None)
                                    for k, c in enumerate(self.cartes)]
        self.image_cadres.actif = self.cartes.index(actif) if actif in self.cartes else -1
        self.image_cadres.update()

    def _cadre_trace(self, boite):
        c = getattr(self, "_active", None)
        if c not in self.cartes:
            self.etat.setText(_("Cliquez d'abord la carte de la personne ou de l'objet."))
            return
        c.e["boite"] = [round(x, 4) for x in boite]
        c.e["decoupe"] = ""
        if c.e.get("source") != "image":
            c.radios["image"].setChecked(True)
        try:
            c.e["decoupe"] = A.decouper(self.image, c.e["boite"], os.path.join(Q.dossier(self.seq), f"decoupe_carte_{id(c) % 10 ** 6}.png"))
        except Exception:      # noqa: BLE001
            c.e["decoupe"] = ""
        c.rafraichir()
        self._maj_cadres()

    def _options_personne(self, carte, source):
        e = carte.e
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 0, 0, 0)
        if source == "image":
            if e.get("decoupe") and os.path.exists(e["decoupe"]):
                h = QHBoxLayout()
                h.addWidget(Vignette(e["decoupe"], 110))
                h.addWidget(self._aide(_("Ce qui servira à faire sa fiche. Pas la bonne personne ? Cliquez-la ou tracez son cadre sur "
                                         "l'image.")), 1)
                v.addLayout(h)
            else:
                v.addWidget(self._aide(_("Cadre {n} sur l'image : cliquez cette carte, puis la personne ou l'objet sur l'image.",
                                         n=self.cartes.index(carte) + 1 if carte in self.cartes else len(self.cartes) + 1)))
        elif source == "photo":
            h = QHBoxLayout()
            b = QPushButton(_("Choisir la photo…"))
            b.clicked.connect(lambda: self._choisir_photo(carte))
            h.addWidget(b)
            h.addWidget(QLabel(os.path.basename(e.get("photo") or "") or _("aucune")), 1)
            v.addLayout(h)
        h = QHBoxLayout()
        b = QPushButton(_("✨ Compléter la description"))
        b.setToolTip(_("L'IA écrit une description complète (âge, allure, vêtements ; couleur, forme) en gardant la vôtre"))
        b.clicked.connect(lambda: self._aider_description(carte))
        h.addWidget(b)
        b2 = QPushButton(_("Style « à la manière de »…"))
        b2.setToolTip(_("Une allure, jamais un visage copié"))
        b2.clicked.connect(lambda: self._style_carte(carte))
        h.addWidget(b2)
        if e.get("style"):
            h.addWidget(QLabel(_("Style : {s}", s=e["style"])), 1)
        h.addStretch(1)
        v.addLayout(h)
        return w

    def _choisir_photo(self, carte):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Photo de « {n} »", n=carte.e.get("nom", "")), _("Images") + " (*.png *.jpg *.jpeg *.webp)", "image",
                            self.params)
        if ch:
            carte.e["photo"] = ch
            carte.rafraichir()

    def _style_carte(self, carte):
        from .dialogues_creatif import choisir_style
        nom = choisir_style(self, self.params, "video")
        if nom:
            carte.e["style"] = nom
            carte.rafraichir()

    def _aider_description(self, carte):
        if self._en_calcul():
            return
        e = dict(carte.e)
        image = e.get("decoupe") if e.get("source") == "image" and e.get("decoupe") else (e.get("photo") if e.get("source") == "photo" else None)
        histoire, niveau = self.seq.get("histoire", ""), self._niveau()

        def fin(r, err):
            if err or not r:
                return
            if self._cloud():
                A.depenser(self.seq, _("Description complétée"), A.PRIX_LECTURE)
            choisi = choisir_proposition(self, e.get("description", ""), r)
            if choisi is not None:
                carte.mettre_description(choisi)
        self._lancer(lambda _t: A.aider_a_decrire(self.params, e, histoire, niveau, image), _("L'IA complète la description"), fin)

    def _lire_cartes(self):
        persos = []
        for c in self.cartes:
            e = c.e
            if not (e.get("nom") or "").strip():
                continue
            persos.append({"nom": e["nom"].strip(), "genre": e.get("genre") or e["type"], "sur_image": e.get("source") == "image",
                           "position": e.get("position", ""), "description": (e.get("description") or "").strip(),
                           "style": e.get("style", ""), "source": e.get("source") or "inventer", "boite": e.get("boite"),
                           "photo": e.get("photo", ""), "decoupe": e.get("decoupe") or None,
                           "accord": bool(self.accord.isChecked()) and e.get("source") in ("image", "photo")})
        return persos

    def _avec_personnes_reelles(self):
        return any(c.e.get("type") == "personne" and c.e.get("source") in ("image", "photo") for c in self.cartes)

    def _cartes_completes(self):
        manquent = [f"{k + 1}. {c.e.get('nom')} : {I.manque(c.e)}" for k, c in enumerate(self.cartes) if I.manque(c.e)]
        if manquent:
            self.etat.setText(_("A compléter : {l}", l=" · ".join(manquent)))
        return not manquent

    # ------------------------------------------------------------------ 3. plans (vidéo)
    def _page_plans(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Voici les plans : une seule action simple par plan")))
        v.addWidget(self._aide(_("Corrigez le texte, la durée, ou qui apparaît (noms séparés par une virgule ; vide = tout le monde). Un "
                                 "plan à deux actions est coupé en deux tout seul. « ✨ Améliorer le plan choisi » reformule son action.")))
        self.t_plans = QTableWidget(0, 3)
        self.t_plans.setHorizontalHeaderLabels([_("Ce qu'on voit"), _("Qui"), _("Durée (s)")])
        self._table(self.t_plans, (1, 2), 0)
        v.addWidget(self.t_plans, 1)
        h = QHBoxLayout()
        for lib, fn in ((_("Ajouter un plan"), self._ajouter_plan), (_("Retirer"), lambda: self._retirer(self.t_plans)),
                        (_("✨ Améliorer le plan choisi"), self._ameliorer_plan)):
            b = QPushButton(lib)
            b.clicked.connect(fn)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        hm = QHBoxLayout()
        hm.addWidget(QLabel(_("Moteur vidéo")))
        self.moteur = QComboBox()
        from . import generateurs_video as GV
        conseil = A.moteur_conseille(self.params)
        self.moteur.addItem(_("IA de ce poste (gratuite ; plans courts, personnages peu fidèles)"), "locale")
        for m in sorted(GV.disponibles(self.params), key=lambda m: m["nom"].lower()):
            self.moteur.addItem(m["nom"] + ("  ★ " + _("conseillé") if m["id"] == conseil else ""), m["id"])
        self.moteur.setCurrentIndex(max(0, self.moteur.findData(conseil)))
        self.moteur.currentIndexChanged.connect(lambda _i: self._maj_prix())
        hm.addWidget(self.moteur, 1)
        v.addLayout(hm)
        self.l_prix = QLabel("")
        self.l_prix.setWordWrap(True)
        v.addWidget(self.l_prix)
        return w

    def _ameliorer_plan(self):
        r = self.t_plans.currentRow()
        if r < 0 or not self.t_plans.item(r, 0):
            self.etat.setText(_("Cliquez d'abord la ligne du plan."))
            return
        item = self.t_plans.item(r, 0)

        class _Champ:                                   # le texte de la cellule, vu comme un champ améliorable
            quoi = "plan"

            def texte(_s):
                return item.text()

            def mettre(_s, t):
                item.setText(t)
        self.ameliorer(_Champ(), self.c_histoire.texte())

    def _remplir_plans(self):
        t = self.t_plans
        t.blockSignals(True)
        t.setRowCount(0)
        for pl in self.seq["plans"]:
            self._ligne_plan(pl)
        t.blockSignals(False)
        t.resizeRowsToContents()

    def _ligne_plan(self, pl):
        t = self.t_plans
        r = t.rowCount()
        t.insertRow(r)
        t.setItem(r, 0, QTableWidgetItem(pl.get("action", "")))
        t.setItem(r, 1, QTableWidgetItem(", ".join(pl.get("personnages") or [])))
        t.setItem(r, 2, QTableWidgetItem(str(int(pl.get("duree") or Q.DUREE_PLAN))))

    def _ajouter_plan(self):
        self._ligne_plan({"action": "", "duree": Q.DUREE_PLAN})
        self.t_plans.setCurrentCell(self.t_plans.rowCount() - 1, 0)
        self.t_plans.editItem(self.t_plans.item(self.t_plans.rowCount() - 1, 0))

    def _retirer(self, t):
        if t.currentRow() >= 0:
            t.removeRow(t.currentRow())
            self._maj_prix()

    def _lire(self):
        """Ce que montrent les cartes et le tableau devient la séquence (ce qui n'a pas changé garde ses fiches, images, vidéos)."""
        if self.genre != "video":
            return
        persos = self._lire_cartes() if self.cartes or not self.seq["personnages"] else A.etat(self.seq)["personnages"]
        noms = {p["nom"].lower(): p["nom"] for p in persos}
        if len(persos) == len(self.seq["personnages"]):       # un nom corrigé suit dans les plans
            for vieux, neuf in zip(self.seq["personnages"], persos):
                noms.setdefault(vieux["nom"].lower(), neuf["nom"])
        if self.t_plans.rowCount() or not self.seq["plans"]:
            plans = []
            for r in range(self.t_plans.rowCount()):
                action = (self.t_plans.item(r, 0).text() if self.t_plans.item(r, 0) else "").strip()
                if not action:
                    continue
                qui = [noms[n.strip().lower()] for n in (self.t_plans.item(r, 1).text() if self.t_plans.item(r, 1) else "").split(",")
                       if n.strip().lower() in noms]
                try:
                    duree = int(float((self.t_plans.item(r, 2).text() or "").replace(",", ".")))
                except (ValueError, AttributeError):
                    duree = Q.DUREE_PLAN
                plans.append({"action": action, "personnages": qui, "duree": max(3, min(15, duree)), "camera": ""})
            cameras = {pl["action"]: pl.get("camera", "") for pl in self.seq["plans"]}
            for pl in plans:
                pl["camera"] = cameras.get(pl["action"], "")
        else:
            plans = A.etat(self.seq)["plans"]
            for pl in plans:
                pl["personnages"] = [noms[n.lower()] for n in pl["personnages"] if n.lower() in noms]
        A.appliquer(self.seq, {"personnages": persos, "plans": plans}, self.image if self._suite() else None)

    def _maj_prix(self):
        if self.pages.currentIndex() != P_PLANS:
            return
        self._lire()
        e = A.estimer(self.seq, self.moteur.currentData(), self.params, self._niveau())
        f, d, a = A.a_preparer(self.seq, self.params)
        self.l_prix.setText(_("A prévoir : {n} image(s) de préparation {i} ; {p} plan(s) vidéo, {s} s, {v} ; relectures {l}. "
                              "Total : {t}, confirmé à l'étape suivante.", n=f + d + a, i=A.argent(e["images"]),
                              p=len(self.seq["plans"]), s=sum(int(pl.get("duree") or 0) for pl in self.seq["plans"]),
                              v=A.argent(e["videos"]), l=A.argent(e["lectures"]), t=A.argent(e["total"])))

    def _page_images(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Regardez avant la vidéo : mêmes visages, mêmes tenues, poses possibles ?")))
        v.addWidget(self._aide(_("Les fiches gardent chacun identique ; chaque plan part de son image de départ et doit arriver sur son "
                                 "image d'arrivée. Cliquez une image pour l'agrandir ; « Corriger… » la refait d'après ce que vous "
                                 "écrivez (0,04 $).")))
        self.zone_images = QScrollArea()
        self.zone_images.setWidgetResizable(True)
        self.zone_images.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(self.zone_images, 1)
        return w

    def _page_video(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Fabrication : chaque plan est relu par l'assistant")))
        self.l_plans = QListWidget()
        self.l_plans.setWordWrap(True)
        self.l_plans.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.l_plans.currentRowChanged.connect(self._voir_plan)
        v.addWidget(self.l_plans, 1)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        self.apercu.hide()
        v.addWidget(self.apercu, 2)
        h = QHBoxLayout()
        self.b_refaire = QPushButton(_("Refaire ce plan…"))
        self.b_refaire.clicked.connect(self.refaire_plan)
        h.addWidget(self.b_refaire)
        self.b_reprendre = QPushButton(_("Fabriquer les plans qui manquent"))
        self.b_reprendre.clicked.connect(self.fabriquer)
        h.addWidget(self.b_reprendre)
        h.addStretch(1)
        v.addLayout(h)
        return w

    # ------------------------------------------------------------------ navigation
    def aller(self, k):
        self.pages.setCurrentIndex(k)
        etapes = ETAPES["musique" if self.genre == "musique" else "video"]
        self.fil.setText("   ›   ".join(f"<b>{e}</b>" if p == k else e for p, e in etapes))
        self.b_suiv.setText(BOUTONS[k])
        self._maj()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _maj(self):
        calc = self._en_calcul()
        k = self.pages.currentIndex()
        self.b_prec.setEnabled(k > P_IDEE and not calc)
        pret = True
        if k == P_VIDEO:
            pret = any(pl.get("fichier") and os.path.exists(pl["fichier"]) for pl in self.seq["plans"])
        elif k == P_M_CREER:
            pret = bool(getattr(self, "resultat", ""))
        self.b_suiv.setEnabled(not calc and pret)
        self.b_dire.setEnabled(not calc)
        self.b_reduire.setVisible(calc)
        self.b_manuel.setEnabled(not calc and k != P_IDEE)
        if k == P_VIDEO:
            self.b_refaire.setEnabled(not calc and self.l_plans.currentRow() >= 0)
            self.b_reprendre.setVisible(not calc and any(not pl.get("fichier") for pl in self.seq["plans"]))
        if k == P_M_CREER:
            self._maj_creer()
        b = A.budget(self._etat_budget())
        if not b.get("prevu") and b.get("depense"):
            self.l_budget.setText(_("Dépensé jusqu'ici : <b>{d}</b> (le budget prévu est annoncé avant la première fabrication payante)",
                                    d=A.argent(b["depense"])))
        elif b.get("prevu") or b.get("depense"):
            rouge = A.depasse(self._etat_budget())
            dep = A.argent(b.get("depense", 0))
            self.l_budget.setText(_("Budget prévu : <b>{p}</b>   ·   dépensé : {d}", p=A.argent(b.get("prevu", 0)),
                                    d=f"<b style='color:#e5484d'>{dep}</b> ⚠ " + _("dépassé") if rouge else f"<b>{dep}</b>"))
        else:
            self.l_budget.setText("")

    def precedent(self):
        k = self.pages.currentIndex()
        if k in (P_QUI, P_PLANS):
            self._lire()
        if k in (P_M_DEROULE, P_M_PAROLES):
            self._lire_musique()
        if self.genre == "musique":
            ordre = [p for p, _e in ETAPES["musique"]]
            cible = ordre[max(0, ordre.index(k) - 1)]
            if cible == P_M_PAROLES and self.musique["elements"][2]["source"] == "aucune":
                cible = P_M_DEROULE
            self.aller(cible)
        else:
            self.aller(max(P_IDEE, k - 1))

    def suivant(self):
        k = self.pages.currentIndex()
        if k == P_IDEE:
            self.params["musique_ia_ecrire"] = self._niveau()
            if self.r_logo.isChecked():
                self.ed.window().fabrique(onglet=0)
                return
            if self.r_musique.isChecked():
                self.genre = "musique"
                self.analyser_musique()
            else:
                self.genre = "video"
                self.analyser()
        elif k == P_QUI:
            if not self._cartes_completes():
                return
            if self._avec_personnes_reelles() and not self.accord.isChecked():
                self.etat.setText(_("Cochez la case : les personnes réelles doivent être d'accord pour être animées par l'IA."))
                return
            self._lire()
            self._remplir_plans()
            self.aller(P_PLANS)
            self._maj_prix()
        elif k == P_PLANS:
            self.preparer()
        elif k == P_IMAGES:
            for pl in self.seq["plans"]:
                pl["images_ok"] = True
            Q.enregistrer(self.seq)
            self._remplir_video()
            self.aller(P_VIDEO)
            self.fabriquer()
        elif k == P_VIDEO:
            self.poser()
        elif k == P_M_ELEM:
            if not self._cartes_musique_completes():
                return
            self._remplir_deroule()
            self.aller(P_M_DEROULE)
        elif k == P_M_DEROULE:
            self._lire_musique()
            if self.musique["elements"][2]["source"] == "aucune":
                self._preparer_creer()
                self.aller(P_M_CREER)
            else:
                self._remplir_paroles()
                self.aller(P_M_PAROLES)
        elif k == P_M_PAROLES:
            self._lire_musique()
            if not self.musique["elements"][2].get("texte", "").strip():
                self.etat.setText(_("Ecrivez les paroles, ou « Ecrire avec l'IA ».") )
                return
            self._preparer_creer()
            self.aller(P_M_CREER)
        elif k == P_M_CREER:
            self.poser_musique(False)

    def _lancer(self, travail, texte, fin):
        """Un calcul suivi (barre du bas, Réduire) ; `travail(tache)` hors de l'interface, `fin(resultat, erreur)` dedans."""
        t = Tache(travail, _("Assistant de création"))
        self.tache = t
        self.taches.append(t)
        suivre_en_fond(self, t, texte)
        self.etat.setText(texte + "…")
        t.progression.connect(lambda f, tx="": self.etat.setText(f"{texte} : {tx or ''} {int(f * 100)} %"), Qt.QueuedConnection)

        def fini(r, e):
            try:
                if e:
                    self.etat.setText(_("✕ {e}", e=texte_erreur(e)[:400]))
                fin(r, e)
                self._maj()
            except RuntimeError:
                pass
        t.fini.connect(fini, Qt.QueuedConnection)
        t.start()
        self._maj()


    # ------------------------------------------------------------------ analyse de l'idée (vidéo)
    def analyser(self):
        histoire = self.c_histoire.texte()
        if len(histoire) < 8:
            self.etat.setText(_("Racontez d'abord ce qui doit se passer."))
            return
        self.seq["histoire"] = histoire
        image = self.image if self._suite() else None
        niveau = self._niveau()

        def travail(_t):
            try:
                return A.analyser(self.params, histoire, image, niveau), None
            except Exception as e:      # noqa: BLE001 : sans IA, on découpe simplement et on le dit
                return A.analyse_simple(histoire), e

        def fin(r, e):
            if e or not r:
                return
            analyse, souci = r
            if not analyse["plans"]:
                self.etat.setText(_("✕ {e}", e=texte_erreur(souci)[:300]) if souci else _("Rien à découper : détaillez l'histoire."))
                return
            if self._cloud() and not souci:
                A.depenser(self.seq, _("Lecture de l'histoire"), A.PRIX_LECTURE)
            A.appliquer(self.seq, analyse, image)
            self._remplir_cartes()
            self._remplir_plans()
            self.aller(P_QUI)
            if self.cartes:
                self._activer(self.cartes[0])
            self.etat.setText(_("L'IA n'a pas répondu ({e}) : l'histoire est découpée simplement, ajoutez les personnes avec « + Une "
                                "personne ».", e=texte_erreur(souci)[:160]) if souci else
                              (analyse.get("remarques") or _("Vérifiez chaque carte, corrigez ce qui ne va pas, puis continuez.")))
        self._lancer(travail, _("L'assistant lit votre idée et regarde l'image") if image else _("L'assistant lit votre idée"), fin)

    # ------------------------------------------------------------------ écrire librement
    def dire(self):
        texte = self.libre.text().strip()
        if not texte or self._en_calcul():
            return
        k = self.pages.currentIndex()
        if k == P_IDEE:
            self.c_histoire.mettre((self.c_histoire.texte() + " " + texte).strip())
            self.libre.clear()
            return
        if self.genre == "musique":
            self._dire_musique(texte)
            return
        if k in (P_QUI, P_PLANS):
            self._lire()
        seq = copy.deepcopy(self.seq)
        niveau = self._niveau()
        image = self.image if self._suite() else None

        def fin(r, e):
            if e or not r:
                return
            self.seq, message = r
            if self._cloud():
                A.depenser(self.seq, _("Correction en clair"), A.PRIX_LECTURE)
            self.libre.clear()
            self._remplir_cartes()
            self._remplir_plans()
            if k >= P_IMAGES:
                self.aller(P_PLANS)
            self._maj_prix()
            self.etat.setText("✓ " + (message or _("C'est modifié : vérifiez, puis continuez.")))
        self._lancer(lambda _t: A.modifier(self.params, seq, texte, niveau, image), _("L'assistant applique votre demande"), fin)

    # ------------------------------------------------------------------ 5. fiches et images
    def preparer(self):
        self._lire()
        if not self.seq["plans"]:
            self.etat.setText(_("Il faut au moins un plan."))
            return
        self._remplir_plans()
        moteur_video = self.moteur.currentData()
        self.seq["moteur"] = moteur_video
        e = A.estimer(self.seq, moteur_video, self.params, self._niveau())
        if e["total"] > 0 and getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Assistant de création"),
                _("Budget prévu pour cette création : {t} sur vos comptes ({i} d'images de préparation, {v} de vidéo, {l} de "
                  "relectures, {r} de réserve pour trois corrections d'images).\n\nD'abord les fiches et les images ({i}) : vous "
                  "les verrez avant que la vidéo parte. Un plan refait s'ajoute : le dépensé passe en rouge s'il dépasse le prévu. "
                  "Continuer ?", t=A.argent(e["total"]), i=A.argent(e["images"]), v=A.argent(e["videos"]), l=A.argent(e["lectures"]),
                  r=A.argent(e["reserve"]))) != QMessageBox.Yes:
            return
        A.prevoir(self.seq, e["total"])
        if not self.params.get("clef_gemini"):               # pas d'images de contrôle possibles : droit à la vidéo
            self._remplir_video()
            self.aller(P_VIDEO)
            self.fabriquer()
            return
        seq = copy.deepcopy(self.seq)

        def travail(t):
            n = A.preparer(seq, self.params, t.avancer, t.arret_demande)
            return seq, n

        def fin(r, err):
            if r:
                self._reprendre_images(r[0])
                A.depenser(self.seq, _("Fiches et images"), A.PRIX_IMAGE * r[1])
            if err and not r:
                return
            Q.enregistrer(self.seq)
            self._remplir_images()
            self.aller(P_IMAGES)
            self.etat.setText(_("Regardez chaque image ; corrigez celles qui ne vont pas, puis lancez la vidéo."))
        self._lancer(travail, _("L'assistant prépare les fiches et les images"), fin)

    def _reprendre_images(self, autre):
        for a, b in zip(self.seq["personnages"], autre["personnages"]):
            if b.get("planche"):
                a["planche"] = b["planche"]
            a["description"] = b.get("description", a.get("description"))
        for a, b in zip(self.seq["plans"], autre["plans"]):
            for cle in ("image", "image_fin", "sans_fin"):
                if cle in b:
                    a[cle] = b[cle]

    def _remplir_images(self):
        w = QWidget()
        g = QGridLayout(w)
        ligne = 0
        g.addWidget(self._titre(_("Personnages et objets")), ligne, 0, 1, 3)
        ligne += 1
        for k, p in enumerate(self.seq["personnages"]):
            vg = Vignette(p.get("planche", ""), 300, _("Pas de fiche"))
            vg.clic.connect(lambda ch: agrandir(self, ch))
            g.addWidget(vg, ligne, 0)
            lb = QLabel(f"<b>{p['nom']}</b><br>{p.get('description', '')}")
            lb.setWordWrap(True)
            g.addWidget(lb, ligne, 1)
            b = QPushButton(_("Corriger…"))
            b.clicked.connect(lambda _c=False, k=k: self.corriger_fiche(k))
            g.addWidget(b, ligne, 2, Qt.AlignTop)
            ligne += 1
        g.addWidget(self._titre(_("Plans : départ, puis arrivée")), ligne, 0, 1, 3)
        ligne += 1
        for i, pl in enumerate(self.seq["plans"]):
            lb = QLabel(_("<b>Plan {i}</b> ({d} s) : {a}", i=i + 1, d=pl.get("duree"), a=pl.get("action", "")))
            lb.setWordWrap(True)
            g.addWidget(lb, ligne, 0, 1, 3)
            ligne += 1
            for col, (chemin, quoi, vide) in enumerate(((Q.depart_prevu(self.seq, i), "depart", _("Pas d'image de départ")),
                                                        (pl.get("image_fin", ""), "arrivee", _("Pas d'image d'arrivée")))):
                bloc = QVBoxLayout()
                vg = Vignette(chemin, 230, vide)
                vg.clic.connect(lambda ch: agrandir(self, ch))
                bloc.addWidget(vg)
                enchaine = quoi == "depart" and i > 0 and not pl.get("image")
                b = QPushButton(_("Corriger l'arrivée…") if quoi == "arrivee" else _("Corriger le départ…"))
                b.setEnabled(not enchaine and not (quoi == "depart" and i == 0 and self._suite()))
                b.setToolTip(_("Ce départ est l'arrivée du plan précédent : corrigez-la là-bas") if enchaine else "")
                b.clicked.connect(lambda _c=False, i=i, quoi=quoi: self.corriger_image(i, quoi))
                bloc.addWidget(b)
                g.addLayout(bloc, ligne, col)
            ligne += 1
        g.setColumnStretch(1, 1)
        g.setRowStretch(ligne, 1)
        self.zone_images.setWidget(w)

    def _precision(self, titre, question):
        if getattr(self, "_test_precision", None) is not None:
            return self._test_precision, True
        return QInputDialog.getText(self, titre, question)

    def corriger_fiche(self, k):
        p = self.seq["personnages"][k]
        texte, ok = self._precision(_("Corriger « {n} »", n=p["nom"]), _("Ce qu'il faut changer (ex. : plus âgé, cheveux gris, casquette) ; "
                                                                        "environ 0,04 $ :"))
        if not ok or not texte.strip():
            return
        seq = copy.deepcopy(self.seq)

        def travail(_t):
            q = seq["personnages"][k]
            q["description"] = (q.get("description", "").rstrip(" .;") + " ; " + texte.strip()).strip(" ;")
            q["brut"] = q["description"]
            q["planche"] = ""
            Q.planche_personnage(seq, q, self.params)
            return seq

        def fin(r, e):
            if r:
                self._reprendre_images(r)
                self.seq["personnages"][k]["brut"] = self.seq["personnages"][k]["description"]
                A.depenser(self.seq, _("Fiche refaite"), A.PRIX_IMAGE)
                self._remplir_images()
                self._remplir_cartes()
                self.etat.setText(_("Fiche refaite. Si elle change beaucoup, corrigez aussi les images des plans où on le voit."))
        self._lancer(travail, _("Nouvelle fiche de « {n} »", n=p["nom"]), fin)

    def corriger_image(self, i, quoi):
        texte, ok = self._precision(_("Corriger l'image"), _("Ce qui ne va pas, ou ce que vous voulez voir (ex. : assise, l'ordinateur "
                                                             "ouvert, face caméra) ; environ 0,04 $ :"))
        if not ok:
            return
        seq = copy.deepcopy(self.seq)

        def travail(_t):
            if quoi == "depart":
                seq["plans"][i]["image"] = ""
            Q.preparer_images(seq, i, self.params, (quoi,), texte.strip(), force=True)
            return seq

        def fin(r, e):
            if r:
                self._reprendre_images(r)
                self.seq["plans"][i]["fichier"] = ""
                A.depenser(self.seq, _("Image refaite"), A.PRIX_IMAGE)
                self._remplir_images()
                self.etat.setText(_("Image refaite : regardez-la."))
        self._lancer(travail, _("Nouvelle image du plan {i}", i=i + 1), fin)

    # ------------------------------------------------------------------ 6. vidéo
    def _texte_plan(self, i):
        pl = self.seq["plans"][i]
        if pl.get("fichier") and os.path.exists(pl["fichier"]):
            etat = A.texte_verdict(pl.get("verdict"))
        elif pl.get("erreur"):
            etat = "✕ " + pl["erreur"]
        elif i in self.file or self._plan_en_cours == i:
            etat = _("en fabrication…") if self._plan_en_cours == i else _("en attente")
        else:
            etat = _("à fabriquer")
        return _("Plan {i} ({d} s) : {a}", i=i + 1, d=pl.get("duree"), a=pl.get("action", "")) + "\n      " + etat

    _plan_en_cours = -1

    def _remplir_video(self):
        r = self.l_plans.currentRow()
        self.l_plans.blockSignals(True)
        self.l_plans.clear()
        for i in range(len(self.seq["plans"])):
            self.l_plans.addItem(QListWidgetItem(self._texte_plan(i)))
        self.l_plans.blockSignals(False)
        if 0 <= r < self.l_plans.count():
            self.l_plans.setCurrentRow(r)

    def _voir_plan(self, r):
        if 0 <= r < len(self.seq["plans"]):
            f = self.seq["plans"][r].get("fichier")
            if f and os.path.exists(f):
                self.apercu.charger(f, video=True)
                self.apercu.show()
        self._maj()

    def fabriquer(self):
        self.file = [i for i, pl in enumerate(self.seq["plans"]) if not (pl.get("fichier") and os.path.exists(pl["fichier"]))]
        for i in self.file:
            self.seq["plans"][i].pop("erreur", None)
        self._suivant_de_la_file()

    def _suivant_de_la_file(self):
        if not self.file:
            self._plan_en_cours = -1
            self._remplir_video()
            rates = [i + 1 for i, pl in enumerate(self.seq["plans"]) if pl.get("verdict") and not pl["verdict"].get("ok")]
            self.etat.setText(_("Terminé. L'assistant conseille de revoir le(s) plan(s) {l} : cliquez-le, regardez, puis « Refaire ce "
                                "plan… » ou gardez-le.", l=", ".join(map(str, rates))) if rates else
                              _("Terminé : regardez les plans, puis « Poser dans le film »."))
            self._maj()
            return
        i = self.file.pop(0)
        self._plan_en_cours = i
        self._remplir_video()
        seq = copy.deepcopy(self.seq)
        moteur_video, niveau = self.seq.get("moteur") or self.moteur.currentData(), self._niveau()

        def travail(t):
            pl = seq["plans"][i]
            if not pl.get("image"):
                depart = Q.depart_prevu(seq, i)
                if depart:
                    pl["image"] = depart                 # tout moteur part de l'image validée
            f = Q.fabriquer_plan(seq, i, self.params, moteur_video, lambda x: t.avancer(0.9 * x, _("plan {i}", i=i + 1)), t.arret_demande)
            pl["fichier"] = f
            t.avancer(0.92, _("relecture du plan {i}", i=i + 1))
            try:
                verdict = A.verifier(self.params, seq, i, niveau)
            except Exception:      # noqa: BLE001 : la relecture est un plus, jamais un blocage
                verdict = None
            return f, verdict

        def fin(r, e):
            pl = self.seq["plans"][i]
            self._plan_en_cours = -1
            if e or not r:
                pl["erreur"] = texte_erreur(e)[:200] if e else _("rien n'a été fabriqué")
                self.file = []
                self._remplir_video()
                return
            pl["fichier"], pl["verdict"] = r
            A.depenser(self.seq, _("Plan {i}", i=i + 1), A.prix_plan(self.seq, i, moteur_video, self.params))
            if r[1] is not None and self._cloud():
                A.depenser(self.seq, _("Relecture"), A.PRIX_LECTURE)
            Q.enregistrer(self.seq)
            self._remplir_video()
            self.l_plans.setCurrentRow(i)
            self._suivant_de_la_file()
        self._lancer(travail, _("Fabrication du plan {i} sur {n}", i=i + 1, n=len(self.seq["plans"])), fin)

    def refaire_plan(self):
        i = self.l_plans.currentRow()
        if i < 0 or self._en_calcul():
            return
        prix = A.prix_plan(self.seq, i, self.seq.get("moteur") or self.moteur.currentData(), self.params)
        texte, ok = self._precision(_("Refaire le plan {i}", i=i + 1), _(
            "Environ {p}. Ce qu'il faut changer dans l'image d'arrivée (facultatif ; vide = même images, nouvel essai) :", p=A.argent(prix)))
        if not ok:
            return
        self.apercu.arreter()
        pl = self.seq["plans"][i]
        pl["fichier"], pl["verdict"] = "", None
        if texte.strip() and self.params.get("clef_gemini"):
            seq = copy.deepcopy(self.seq)

            def fin(r, e):
                if r:
                    self._reprendre_images(r)
                    A.depenser(self.seq, _("Image refaite"), A.PRIX_IMAGE)
                    self.fabriquer()
            self._lancer(lambda _t: (Q.preparer_images(seq, i, self.params, ("arrivee",), texte.strip(), force=True), seq)[1],
                         _("Nouvelle image d'arrivée du plan {i}", i=i + 1), fin)
        else:
            self.fabriquer()

    # ================================================================== MUSIQUE (0.9.80)
    def analyser_musique(self):
        texte = self.c_histoire.texte()
        if len(texte) < 4:
            self.etat.setText(_("Dites d'abord quelle musique vous voulez."))
            return
        niveau = self._niveau()

        def travail(_t):
            try:
                return I.analyser_musique(self.params, texte, niveau), None
            except Exception as e:      # noqa: BLE001 : sans IA, des cartes pré-remplies par les mots
                return I.analyse_musique_simple(texte), e

        def fin(r, e):
            if e or not r:
                return
            etat, souci = r
            etat["idee"] = texte
            if self.musique and self.musique.get("budget"):
                etat["budget"] = self.musique["budget"]
            self.musique = etat
            if self._cloud() and not souci:
                A.depenser(self.musique, _("Lecture de l'idée"), A.PRIX_LECTURE)
            if self._cloud() and not A.budget(self.musique).get("prevu"):
                A.prevoir(self.musique, 8 * A.PRIX_LECTURE)      # quelques lectures (améliorations, paroles) ; la création est gratuite ici
            self.resultat, self.parties_faites = "", {}
            self._remplir_mcartes()
            self.aller(P_M_ELEM)
            self.etat.setText(_("L'IA n'a pas répondu ({e}) : les cartes sont pré-remplies d'après vos mots ; complétez-les.",
                                e=texte_erreur(souci)[:160]) if souci else
                              (etat.get("remarques") or _("Pour chaque carte, choisissez d'où elle vient, puis continuez.")))
        self._lancer(travail, _("L'assistant lit votre idée"), fin)

    def _dire_musique(self, texte):
        if self.pages.currentIndex() in (P_M_DEROULE, P_M_PAROLES):
            self._lire_musique()
        etat, niveau = copy.deepcopy(self.musique), self._niveau()

        def fin(r, e):
            if e or not r:
                return
            neuf, message = r
            for k in ("budget", "idee"):
                if self.musique.get(k):
                    neuf[k] = self.musique[k]
            self.musique = neuf
            if self._cloud():
                A.depenser(self.musique, _("Correction en clair"), A.PRIX_LECTURE)
            self.libre.clear()
            self.parties_faites = {}
            self._remplir_mcartes()
            self._remplir_deroule()
            self._remplir_paroles()
            if self.pages.currentIndex() == P_M_CREER:
                self.aller(P_M_DEROULE)
            self.etat.setText("✓ " + (message or _("C'est modifié : vérifiez, puis continuez.")))
        self._lancer(lambda _t: I.modifier_musique(self.params, etat, texte, niveau), _("L'assistant applique votre demande"), fin)

    # ------------------------------------------------------------------ 2. ce qu'il faut (cartes style, voix, paroles)
    def _page_m_elements(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Ce qu'il faut pour cette musique : vérifiez chaque carte")))
        v.addWidget(self._aide(_("Pour le style et la voix : un morceau à vous (votre groupe…), un morceau trouvé en ligne, une "
                                 "description, ou la liste de PhilCut. Un morceau donné peut servir de deux façons, expliquées sur la "
                                 "carte ; c'est vous qui choisissez. Tout reste sur ce poste.")))
        self.w_mcartes = QWidget()
        self.v_mcartes = QVBoxLayout(self.w_mcartes)
        v.addWidget(_defile(self.w_mcartes), 1)
        return w

    def _remplir_mcartes(self):
        vider(self.v_mcartes)
        self.mcartes = []
        titres = {"style": _("Style"), "voix": _("Voix"), "paroles": _("Paroles")}
        for k, e in enumerate(self.musique["elements"]):
            e.setdefault("genre", {"paroles": "theme"}.get(e["type"], e["type"]))
            c = CarteElement(e, I.sources(e["type"]), self._options_musique, I.manque, self.ameliorer, COULEURS[k], None, titres[e["type"]])
            c.change.connect(self._maj)
            self.mcartes.append(c)
            self.v_mcartes.addWidget(c)
        self.v_mcartes.addStretch(1)

    def _cartes_musique_completes(self):
        manquent = [f"{c.e.get('nom')} : {I.manque(c.e)}" for c in self.mcartes if I.manque(c.e)]
        if manquent:
            self.etat.setText(_("A compléter : {l}", l=" · ".join(manquent)))
        return not manquent

    def _options_musique(self, carte, source):
        e = carte.e
        t = e["type"]
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 0, 0, 0)
        if t in ("style", "voix") and source in ("fichier", "en_ligne"):
            h = QHBoxLayout()
            b = QPushButton(_("Choisir le morceau…") if source == "fichier" else _("Chercher en ligne…"))
            b.clicked.connect(lambda: self._morceau(carte, source))
            h.addWidget(b)
            autre = self.musique["elements"][0] if t == "voix" else None
            if autre is not None and autre.get("chemin") and autre.get("chemin") != e.get("chemin"):
                b2 = QPushButton(_("Le même que pour le style"))
                b2.clicked.connect(lambda: self._fichier_choisi(carte, autre["chemin"], autre.get("nom_fichier"), passage=False))
                h.addWidget(b2)
            h.addWidget(QLabel(e.get("nom_fichier") or _("aucun")), 1)
            v.addLayout(h)
            if e.get("chemin"):
                g = QButtonGroup(w)
                for cle, lib, expl in I.USAGES[t]:
                    r = QRadioButton(lib)
                    r.setChecked(e.get("usage") == cle)
                    g.addButton(r)
                    v.addWidget(r)
                    lb = aide(expl)
                    lb.setContentsMargins(24, 0, 0, 0)
                    v.addWidget(lb)
                    r.toggled.connect(lambda on, cle=cle: on and self._usage(carte, cle))
                self._options_usage(carte, v)
        elif source == "liste" and t in ("style", "voix"):
            cb = QComboBox()
            if t == "style":
                from . import musique_ia as MI
                items = sorted(((s[1], s[0]) for s in MI.STYLES), key=lambda x: _alpha(x[0]))
            else:
                from . import musique_ia as MI
                items = sorted(((lib, k) for k, (lib, _en) in MI.voix_disponibles().items() if k != "auto"), key=lambda x: _alpha(x[0]))
            cb.addItem(_("Choisir…"), "")
            for lib, k in items:
                cb.addItem(lib, k)
            cb.setCurrentIndex(max(0, cb.findData(e.get("choix") or "")))
            cb.currentIndexChanged.connect(lambda _i: (e.update(choix=cb.currentData()), carte.maj()))
            v.addWidget(cb)
        if t == "voix" and source != "aucune":
            h = QHBoxLayout()
            h.addWidget(QLabel(_("A changer dans cette voix :")))
            rt = ChampAmeliorable(e.get("retouche", ""), "voix", 1, None, _("ex. : plus féminine et chaude, plus grave…"))
            rt.change.connect(lambda: e.update(retouche=rt.texte()))
            h.addWidget(rt, 1)
            v.addLayout(h)
        if t == "paroles" and source in ("j_ecris", "ia"):
            from . import paroles as PA
            h = QHBoxLayout()
            h.addWidget(QLabel(_("Langue")))
            cb = QComboBox()
            for k, lib in sorted(PA.LANGUES.items(), key=lambda x: _alpha(x[1])):
                cb.addItem(lib, k)
            cb.setCurrentIndex(max(0, cb.findData(e.get("langue") or "fr")))
            cb.currentIndexChanged.connect(lambda _i: e.update(langue=cb.currentData()))
            h.addWidget(cb)
            h.addStretch(1)
            v.addLayout(h)
            v.addWidget(self._aide(_("Le texte s'écrit à l'étape « Paroles » ; la description ci-dessus sert de thème.")))
        return w

    def _options_usage(self, carte, v):
        e, t, u = carte.e, carte.e["type"], carte.e.get("usage")
        if not u:
            return
        h = QHBoxLayout()
        if t == "style" and u == "reprendre":
            if not e.get("droits_ok"):
                b = QPushButton(_("Ce morceau est à moi, ou libre de droits…"))
                b.clicked.connect(lambda: self._declarer(carte))
                h.addWidget(b)
            else:
                h.addWidget(QLabel(_("✓ Déclaré à vous ou libre de droits")))
                h.addWidget(QLabel(_("Proche")))
                f = QDoubleSpinBox()
                f.setRange(0.1, 0.9)
                f.setSingleStep(0.1)
                f.setValue(float(e.get("force", 0.5)))
                f.setToolTip(_("Proche : le morceau reste reconnaissable ; libre : le moteur s'en éloigne"))
                f.valueChanged.connect(lambda x: e.update(force=x))
                h.addWidget(f)
                h.addWidget(QLabel(_("Libre")))
        if t == "style":
            b = QPushButton(_("Ecouter et décrire (sur ce poste, gratuit)") if not e.get("pret") else _("Réécouter"))
            b.clicked.connect(lambda: self._analyser_style(carte))
            h.addWidget(b)
        elif u == "decrire":
            b = QPushButton(_("Isoler et décrire la voix (sur ce poste)") if not e.get("pret") else _("Redécrire"))
            b.clicked.connect(lambda: self._voix(carte, "decrire"))
            h.addWidget(b)
        elif u == "timbre":
            acc = QCheckBox(_("La personne qui chante est d'accord (ou c'est moi)"))
            acc.setChecked(bool(e.get("accord")))
            acc.toggled.connect(lambda on: (e.update(accord=on), carte.maj()))
            h.addWidget(acc)
            b = QPushButton(_("Isoler la voix (sur ce poste)") if not e.get("voix_seule") else _("Isoler à nouveau"))
            b.clicked.connect(lambda: self._voix(carte, "timbre"))
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        if t == "style" and e.get("inspiration"):
            v.addWidget(self._aide(_("Entendu : {r}", r=e["inspiration"].get("resume", ""))))
        if t == "voix" and e.get("voix_decrite"):
            v.addWidget(self._aide(_("Voix décrite : {d}", d=e["voix_decrite"].get("fr", ""))))
        if t == "voix" and e.get("voix_seule"):
            v.addWidget(self._aide(_("Voix isolée : {f}", f=os.path.basename(e["voix_seule"]))))

    def _usage(self, carte, cle):
        carte.e["usage"] = cle
        carte.rafraichir()

    def _morceau(self, carte, source):
        if source == "fichier":
            from .widgets import ouvrir_fichier
            ch = ouvrir_fichier(self, _("Morceau"), SONS, "musique", self.params)
            if ch:
                self._fichier_choisi(carte, ch)
            return
        from .dialogues_musique_ia import DialogueMusiqueEnLigne
        DialogueMusiqueEnLigne(self, self.params, utiliser=lambda ch: self._fichier_choisi(carte, ch), libelle_utiliser=_("Utiliser ce morceau"),
                               aide=_("<b>Cherchez le morceau</b> : écoutez, téléchargez, puis « Utiliser ce morceau ». Il reviendra sur "
                                      "la carte, où vous choisirez ce que PhilCut en fait.")).exec()

    def _fichier_choisi(self, carte, ch, nom=None, passage=True):
        from . import musique_ia as MI
        from .dialogues_musique_ia import choisir_passage
        e = carte.e
        if passage:
            p = choisir_passage(self, ch, _("Passage à utiliser"),
                                _("Gardez tout le morceau, ou le passage qui compte (pour une voix : 15 à 40 s où elle chante bien)."))
            if not p:
                return
            try:
                ch2 = MI.extraire_passage(ch, *p)
            except RuntimeError as err:
                self.etat.setText("✕ " + texte_erreur(err))
                return
        else:
            ch2 = ch
        e.update(chemin=ch2, nom_fichier=nom or os.path.basename(ch), pret=False, inspiration=None, voix_decrite=None, voix_seule="",
                 droits_ok=MI.peut_partir_de(ch2))
        if e["type"] == "voix":
            e["usage"] = e.get("usage") if e.get("usage") in ("decrire", "timbre") else ""
        carte.rafraichir()

    def _declarer(self, carte):
        from . import musique_ia as MI
        from .musique_en_ligne import LEGAL_MUSIQUE
        ch = carte.e.get("chemin")
        if not ch:
            return
        d = QMessageBox(self)
        d.setWindowTitle(_("Morceau à vous ou libre de droits"))
        d.setTextFormat(Qt.RichText)
        d.setText(LEGAL_MUSIQUE + "<br><br>" + _("Ce morceau (l'œuvre <b>et</b> cet enregistrement) est-il à vous, ou libre de droits ?"))
        b_moi = d.addButton(_("C'est le mien"), QMessageBox.AcceptRole)
        b_libre = d.addButton(_("Libre de droits"), QMessageBox.AcceptRole)
        d.addButton(_("Non, m'en inspirer seulement"), QMessageBox.RejectRole)
        if getattr(self, "_test_oui", None) is not None:
            MI.declarer(ch, a_moi=True)
        else:
            d.exec()
            if d.clickedButton() is b_moi:
                MI.declarer(ch, a_moi=True)
            elif d.clickedButton() is b_libre:
                MI.declarer(ch, libre=True)
            else:
                carte.e["usage"] = "inspirer"
                carte.rafraichir()
                return
        carte.e["droits_ok"] = MI.peut_partir_de(ch)
        carte.rafraichir()

    def _analyser_style(self, carte):
        from . import musique_ia as MI
        e, params = carte.e, self.params

        def fin(r, err):
            if err or not r:
                return
            e["inspiration"], e["pret"] = r, True
            if not self.musique.get("tonalite") and r.get("tonalite"):
                self.musique["tonalite"] = r["tonalite"]
            carte.rafraichir()
            self.etat.setText(_("✓ Style entendu : {r}", r=r.get("resume", "")))
        self._lancer(lambda t: MI.analyser(e["chemin"], params, t.avancer, t.arret_demande), _("Ecoute du morceau sur ce poste"), fin)

    def _voix(self, carte, usage):
        from . import creatif
        from . import musique_ia as MI
        manque = creatif.separation_manquante(self.params)
        if manque:
            QMessageBox.information(self, _("Voix"), manque)
            return
        e, params = carte.e, self.params
        if usage == "timbre" and not e.get("accord"):
            self.etat.setText(_("Cochez d'abord l'accord de la personne qui chante (ou c'est vous)."))
            return
        from .creations import dossier
        sortie = os.path.join(dossier(), os.path.splitext(os.path.basename(e["chemin"]))[0][:50] + f"_voix_{int(time.time())}.wav")

        def travail(t):
            voix = creatif.extraire_voix(e["chemin"], sortie, params, lambda f, x="": t.avancer(0.8 * f, x), t.arret_demande)
            if usage == "timbre":
                MI.declarer(voix, voix_accord=True)
                return {"voix_seule": voix}
            r = MI.decrire_voix(voix, lambda f, x="": t.avancer(0.8 + 0.2 * f, x), t.arret_demande)
            return {"voix_decrite": {k: r[k] for k in ("en", "fr") if k in r}}

        def fin(r, err):
            if err or not r:
                return
            e.update(r)
            e["pret"] = True
            carte.rafraichir()
            self.etat.setText(_("✓ Voix prête."))
        self._lancer(travail, _("La voix est isolée sur ce poste"), fin)

    # ------------------------------------------------------------------ 3. le déroulé
    def _page_m_deroule(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Le déroulé : chaque partie à son tempo")))
        v.addWidget(self._aide(_("Chaque partie est fabriquée à son tempo, avec le même style, la même voix et la même tonalité, puis les "
                                 "parties sont enchaînées en fondu d'une mesure. Ecoutez les raccords : une partie se refait seule.")))
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Durée totale (s)")))
        self.m_duree = QDoubleSpinBox()
        self.m_duree.setRange(10, 600)
        self.m_duree.setDecimals(0)
        h.addWidget(self.m_duree)
        b = QPushButton(_("Recaler les parties"))
        b.setToolTip(_("Les durées des parties sont ramenées à la durée totale, proportions gardées"))
        b.clicked.connect(self._recaler)
        h.addWidget(b)
        h.addWidget(QLabel(_("Tonalité")))
        self.m_ton = QLineEdit()
        self.m_ton.setPlaceholderText(_("ex. E minor ; vide = au choix"))
        h.addWidget(self.m_ton)
        h.addStretch(1)
        v.addLayout(h)
        self.t_parties = QTableWidget(0, 6)
        self.t_parties.setHorizontalHeaderLabels([_("Partie"), _("Durée (s)"), _("Tempo"), _("Energie"), _("Chantée"), _("Ce qu'on entend")])
        self._table(self.t_parties, (0, 1, 2, 3, 4), 5)
        v.addWidget(self.t_parties, 1)
        h = QHBoxLayout()
        for lib, fn in ((_("Ajouter une partie"), self._ajouter_partie), (_("Retirer"), lambda: self._retirer(self.t_parties)),
                        (_("✨ Améliorer la partie choisie"), self._ameliorer_partie)):
            b = QPushButton(lib)
            b.clicked.connect(fn)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        return w

    def _remplir_deroule(self):
        m = self.musique
        self.m_duree.setValue(float(m["duree"]))
        self.m_ton.setText(m.get("tonalite") or "")
        t = self.t_parties
        t.blockSignals(True)
        t.setRowCount(0)
        for p in m["parties"]:
            self._ligne_partie(p)
        t.blockSignals(False)
        t.resizeRowsToContents()

    def _ligne_partie(self, p):
        t = self.t_parties
        r = t.rowCount()
        t.insertRow(r)
        t.setItem(r, 0, QTableWidgetItem(p.get("nom", "")))
        t.setItem(r, 1, QTableWidgetItem(str(int(p.get("duree") or 20))))
        t.setItem(r, 2, QTableWidgetItem(str(int(p.get("tempo") or 100))))
        cb = QComboBox()
        for k, lib in ENERGIES:
            cb.addItem(lib, k)
        cb.setCurrentIndex(max(0, cb.findData(p.get("energie") or "moyenne")))
        t.setCellWidget(r, 3, cb)
        it = QTableWidgetItem("")
        it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        it.setCheckState(Qt.Checked if p.get("chant") else Qt.Unchecked)
        t.setItem(r, 4, it)
        t.setItem(r, 5, QTableWidgetItem(p.get("description", "")))

    def _ajouter_partie(self):
        self._ligne_partie({"nom": _("Partie {n}", n=self.t_parties.rowCount() + 1), "duree": 20, "tempo": 100, "energie": "moyenne"})

    def _ameliorer_partie(self):
        r = self.t_parties.currentRow()
        if r < 0:
            self.etat.setText(_("Cliquez d'abord la ligne de la partie."))
            return
        item = self.t_parties.item(r, 5) or QTableWidgetItem("")
        if self.t_parties.item(r, 5) is None:
            self.t_parties.setItem(r, 5, item)

        class _Champ:
            quoi = "partie"

            def texte(_s):
                return item.text() or (self.t_parties.item(r, 0).text() if self.t_parties.item(r, 0) else "")

            def mettre(_s, t):
                item.setText(t)
        self.ameliorer(_Champ(), self.c_histoire.texte())

    def _recaler(self):
        self._lire_musique(recaler=True)
        self._remplir_deroule()

    def _lire_musique(self, recaler=False):
        m = self.musique
        if m is None:
            return
        if self.t_parties.rowCount():
            parties = []
            for r in range(self.t_parties.rowCount()):
                def txt(c):
                    return (self.t_parties.item(r, c).text() if self.t_parties.item(r, c) else "").strip()
                parties.append({"nom": txt(0) or _("Partie {n}", n=r + 1), "duree": I._num(txt(1).replace(",", "."), 20.0, 5.0, 240.0),
                                "tempo": int(I._num(txt(2), 100, 40, 220)), "energie": self.t_parties.cellWidget(r, 3).currentData(),
                                "chant": self.t_parties.item(r, 4).checkState() == Qt.Checked if self.t_parties.item(r, 4) else False,
                                "description": txt(5)})
            vieilles = m["parties"]
            if [(p["duree"], p["tempo"], p["energie"], p["chant"], p["description"]) for p in parties] != \
                    [(p["duree"], p["tempo"], p["energie"], p["chant"], p["description"]) for p in vieilles]:
                self.parties_faites = {k: f for k, f in (getattr(self, "parties_faites", {}) or {}).items()
                                       if k < len(parties) and k < len(vieilles) and parties[k] == vieilles[k]}
            m["parties"] = parties
            m["duree"] = float(self.m_duree.value()) if recaler else float(sum(p["duree"] for p in parties))
            if recaler:
                I.caler(m["parties"], m["duree"])
            m["tonalite"] = self.m_ton.text().strip()
        if hasattr(self, "c_paroles") and self.pages.currentIndex() == P_M_PAROLES:
            m["elements"][2]["texte"] = self.c_paroles.texte()

    # ------------------------------------------------------------------ 4. les paroles
    def _page_m_paroles(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Les paroles")))
        self.l_balises = self._aide("")
        v.addWidget(self.l_balises)
        self.c_paroles = ChampAmeliorable("", "paroles", 0, self.ameliorer, _("[verse]\n…\n[chorus]\n…"))
        v.addWidget(self.c_paroles, 1)
        h = QHBoxLayout()
        b = QPushButton(_("Ecrire avec l'IA"))
        b.setToolTip(_("D'après le thème de la carte Paroles et le déroulé ; ce que vous avez déjà écrit est gardé en tête"))
        b.clicked.connect(self._ecrire_paroles)
        h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        return w

    def _remplir_paroles(self):
        if self.musique is None:
            return
        chantees = [p["nom"] for p in self.musique["parties"] if p.get("chant")]
        self.l_balises.setText(_("Un bloc par partie chantée, dans l'ordre, chacun commencé par une balise ([verse] couplet, [chorus] "
                                 "refrain, [bridge] passage lent) : {l}. Les parties sans chant restent instrumentales.",
                                 l=" › ".join(chantees) or _("aucune partie chantée : cochez « Chantée » dans le déroulé")))
        self.c_paroles.mettre(self.musique["elements"][2].get("texte", ""))

    def _ecrire_paroles(self):
        from . import paroles as PA
        from .dialogues_musique_ia import _avec_moteur
        pa = self.musique["elements"][2]
        niveau = self._niveau()
        plan = ", ".join(f"{p['nom']} ({int(p['duree'])} s, {'chantée' if p.get('chant') else 'instrumentale'})" for p in self.musique["parties"])
        theme = (pa.get("description") or self.c_histoire.texte()) + ". " + _("Déroulé : {p}.", p=plan)
        args = (theme, self.c_paroles.texte(), pa.get("langue") or "fr", "auto", self.musique["duree"], self.params)

        def fin(r, err):
            if err or not r:
                return
            if self._cloud():
                A.depenser(self.musique, _("Paroles écrites"), A.PRIX_LECTURE)
            choisi = choisir_proposition(self, self.c_paroles.texte(), r) if self.c_paroles.texte() else r
            if choisi is not None:
                self.c_paroles.mettre(choisi)
                pa["texte"] = choisi
        self._lancer(lambda _t: _avec_moteur(niveau, lambda: PA.ecrire(*args, "locale" if niveau == "locale" else "cloud")),
                     _("L'IA écrit les paroles"), fin)

    # ------------------------------------------------------------------ 5. la création
    def _page_m_creer(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("La musique : partie par partie, puis enchaînée")))
        self.l_resume = self._aide("")
        v.addWidget(self.l_resume)
        self.l_parties = QListWidget()
        self.l_parties.setWordWrap(True)
        self.l_parties.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.l_parties.currentRowChanged.connect(self._voir_partie)
        v.addWidget(self.l_parties, 1)
        from .dialogues_creatif import ApercuCreation
        self.apercu_m = ApercuCreation(self)
        self.apercu_m.hide()
        v.addWidget(self.apercu_m, 1)
        h = QHBoxLayout()
        self.b_creer = QPushButton(_("Créer la musique (sur ce poste, gratuit)"))
        self.b_creer.setStyleSheet("font-weight:600")
        self.b_creer.clicked.connect(self.creer_musique)
        h.addWidget(self.b_creer)
        self.b_refaire_partie = QPushButton(_("Refaire la partie choisie"))
        self.b_refaire_partie.clicked.connect(self.refaire_partie)
        h.addWidget(self.b_refaire_partie)
        self.b_ligne = QPushButton(_("Poser à la ligne rouge"))
        self.b_ligne.clicked.connect(lambda: self.poser_musique(True))
        h.addWidget(self.b_ligne)
        self.b_sous = QPushButton(_("Enregistrer sous…"))
        self.b_sous.clicked.connect(self._enregistrer_musique)
        h.addWidget(self.b_sous)
        h.addStretch(1)
        v.addLayout(h)
        return w

    def _preparer_creer(self):
        self.l_resume.setText(I.resume(self.musique))
        self._remplir_lparties()
        if getattr(self, "resultat", ""):
            self.apercu_m.charger(self.resultat, video=False)
            self.apercu_m.show()

    def _remplir_lparties(self):
        r = self.l_parties.currentRow()
        self.l_parties.blockSignals(True)
        self.l_parties.clear()
        faits = getattr(self, "parties_faites", {}) or {}
        for k, p in enumerate(self.musique["parties"]):
            ok = faits.get(k) and os.path.exists(faits[k])
            self.l_parties.addItem(QListWidgetItem(f"{'✓' if ok else '○'}  {p['nom']} — {int(p['duree'])} s, {p['tempo']} bpm, "
                                                   f"{dict(ENERGIES).get(p.get('energie'), '')}" + (" ♪" if p.get("chant") else "")))
        self.l_parties.blockSignals(False)
        if 0 <= r < self.l_parties.count():
            self.l_parties.setCurrentRow(r)

    def _voir_partie(self, r):
        f = (getattr(self, "parties_faites", {}) or {}).get(r)
        if f and os.path.exists(f) and not self._en_calcul():
            self.apercu_m.charger(f, video=False)
            self.apercu_m.show()
        self._maj()

    def _maj_creer(self):
        calc = self._en_calcul()
        fait = bool(getattr(self, "resultat", ""))
        self.b_creer.setEnabled(not calc)
        self.b_creer.setText(_("Créer les parties qui manquent") if fait or getattr(self, "parties_faites", None) else
                             _("Créer la musique (sur ce poste, gratuit)"))
        self.b_refaire_partie.setEnabled(not calc and self.l_parties.currentRow() >= 0 and bool(getattr(self, "parties_faites", None)))
        self.b_ligne.setEnabled(not calc and fait)
        self.b_sous.setEnabled(not calc and fait)

    def creer_musique(self):
        if self._en_calcul():
            return
        from . import traduction_recherche as TR
        etat, params = copy.deepcopy(self.musique), self.params
        deja = dict(getattr(self, "parties_faites", {}) or {})
        dossier = os.path.join(Q.dossier(self.seq), "musique")
        os.makedirs(dossier, exist_ok=True)
        try:
            self.apercu_m.arreter()
        except RuntimeError:
            pass

        def traduire(x):
            en, comment, manque = TR.phrase_en_anglais(x)
            if manque and comment != "service":
                raise RuntimeError(_("Pas de traduction pour « {m} » (pas de réseau ?) : écrivez ces mots en anglais.",
                                     m=", ".join(dict.fromkeys(manque))))
            return en

        def travail(t):
            return I.creer_parties(etat, dossier, params, t.avancer, t.arret_demande, traduire, deja)

        def fin(r, err):
            if err or not r:
                self._remplir_lparties()
                return
            final, faits, base = r
            self.parties_faites, self.resultat = faits, final
            from . import creations
            from . import musique_ia as MI
            try:
                creations.ecrire(final, dict(MI.recette(base, {"caption": ""}), assistant=I.etat_musique(self.musique)))
            except Exception:      # noqa: BLE001 : la recette est un plus
                pass
            self._remplir_lparties()
            self.apercu_m.charger(final, video=False)
            self.apercu_m.show()
            self.etat.setText(_("✓ Musique créée ({n} parties enchaînées). Ecoutez les raccords ; une partie se refait seule, puis "
                                "« Poser sous la vidéo ».", n=len(faits)))
        self._lancer(travail, _("Création de la musique sur ce poste"), fin)

    def refaire_partie(self):
        k = self.l_parties.currentRow()
        if k < 0 or self._en_calcul():
            return
        (self.parties_faites or {}).pop(k, None)
        self.resultat = ""
        self.creer_musique()

    def poser_musique(self, a_la_ligne):
        if not getattr(self, "resultat", ""):
            return
        r = self.apercu_m.reglages()
        self.apercu_m.arreter()
        ed = self.ed
        ed._piste_depot = ("audio", float(ed.timeline.position if a_la_ligne else 0.0), dict(r, volume=0.8, _couper_fin=True))
        ed.importer([self.resultat])
        self.etat.setText(_("✓ Morceau posé ({d:.0f} s) sur la piste Musique ; Ctrl+Z pour revenir.", d=r["src_fin"] - r["src_debut"]))

    def _enregistrer_musique(self):
        from .dialogues_creatif import enregistrer_copie
        c = enregistrer_copie(self, self.resultat, self.params)
        if c:
            self.etat.setText(_("✓ Copie enregistrée : {f}", f=c))

    # ------------------------------------------------------------------ poser (vidéo), mode manuel, fermeture
    def poser(self):
        p = self.ed.projet
        from .projet import fin_clip
        c = p.clip(self.clip["id"]) if self.clip and self._suite() else None
        t = fin_clip(c) if c else self.ed.timeline.position
        self.apercu.arreter()
        p.marquer()
        n, duree = Q.monter(p, self.seq, t)
        self._garder_dans_projet()
        self.ed.biblio.remplir(p)
        self.ed.rafraichir()
        self.etat.setText(_("✓ {n} plan(s) posés ({d} s) {ou} ; Ctrl+Z pour revenir.", n=n, d=int(duree),
                            ou=_("à la suite du rush") if c else _("à la ligne rouge")))

    def _garder_dans_projet(self):
        p = self.ed.projet
        p.d["sequences_ia"] = [s for s in p.d.get("sequences_ia") or [] if s.get("cree") != self.seq.get("cree")] + [copy.deepcopy(self.seq)]
        Q.enregistrer(self.seq)

    def mode_manuel(self):
        """Ce qui est préparé, dans la fenêtre habituelle : la Séquence IA (vidéo) ou la Fabrique musique, pré-remplie."""
        if self.genre == "musique" and self.musique is not None:
            self._lire_musique()
            f = I.fiche_base(self.musique)
            f["paroles"] = self.musique["elements"][2].get("texte", "") if not f.get("instrumental") else ""
            f["structure"] = ""
            f["phrase"] = ", ".join(x for x in (f.get("phrase"), " ; ".join(f"{p['nom']} {int(p['duree'])} s {p['tempo']} bpm" +
                                                                          (f" ({p['description']})" if p.get("description") else "")
                                                                          for p in self.musique["parties"])) if x)
            self.ed.fabrique_musique(fiche=f)
            self.hide()
            return
        if self.pages.currentIndex() in (P_QUI, P_PLANS):
            self._lire()
        self._garder_dans_projet()
        self.ed._sequence = None
        self.ed.sequence_ia()
        self.hide()

    def done(self, r):
        if garder_calcul(self, self._en_calcul()):
            return
        for a in ("apercu", "apercu_m"):
            try:
                getattr(self, a).arreter()
            except (RuntimeError, AttributeError):
                pass
        super().done(r)
