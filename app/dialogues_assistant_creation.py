"""Fenêtre de l'assistant de création : de l'idée au résultat (0.9.79, méthode commune en 0.9.80).

On dit en quelques mots ce que l'on veut ; l'assistant en déduit le genre (suite d'un plan, scène, musique ou chanson),
les éléments nécessaires et le déroulé, tout pré-rempli. Chaque élément est une carte où l'on choisit d'où il vient (dans
l'image, une photo, un morceau à moi, en ligne, le décrire, la liste, l'inventer…), chaque possibilité expliquée ; tout
texte peut être amélioré par l'IA (les deux versions sont montrées). Voir assistant_idee.py (la méthode, la musique) et
assistant_creation.py (la vidéo). Le mode manuel (Séquence IA, Fabrique musique) reste à un clic, pré-rempli."""
import copy
import os
import time

from PySide6.QtCore import Qt, QTimer, Signal
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

P_IDEE, P_QUI, P_PLANS, P_IMAGES, P_VIDEO, P_M_ELEM, P_M_DEROULE, P_M_PAROLES, P_M_CREER, P_I_ELEM, P_I_TEXTE, P_I_CREER = range(12)
ETAPES = {"video": ((P_IDEE, _("1. Votre idée")), (P_QUI, _("2. Qui et quoi")), (P_PLANS, _("3. Les plans")), (P_IMAGES, _("4. Les images")),
                    (P_VIDEO, _("5. La vidéo"))),
          "musique": ((P_IDEE, _("1. Votre idée")), (P_M_ELEM, _("2. Ce qu'il faut")), (P_M_DEROULE, _("3. Le déroulé")),
                      (P_M_PAROLES, _("4. Les paroles")), (P_M_CREER, _("5. La musique"))),
          "intro": ((P_IDEE, _("1. Votre idée")), (P_I_ELEM, _("2. Ce qu'il faut")), (P_I_TEXTE, _("3. Le texte et le rendu")),
                    (P_I_CREER, _("4. L'intro")))}
BOUTONS = {P_IDEE: _("Voir ce qu'il faut ›"), P_QUI: _("C'est bien eux ›"), P_PLANS: _("Préparer les images ›"),
           P_IMAGES: _("Tout me convient : fabriquer la vidéo ›"), P_VIDEO: _("Poser dans le film"), P_M_ELEM: _("Tout est prêt ›"),
           P_M_DEROULE: _("Les paroles ›"), P_M_PAROLES: _("Vers la création ›"), P_M_CREER: _("Poser sous la vidéo"),
           P_I_ELEM: _("Le texte et le rendu ›"), P_I_TEXTE: _("Fabriquer l'intro ›"), P_I_CREER: _("Poser l'intro")}
PLACEMENTS = (("debut", _("Au début du film (la suite est décalée)")), ("fin", _("A la fin du film")),
              ("ligne", _("A la ligne rouge")), ("medias", _("Seulement dans les médias")))
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
        self.fil.setTextFormat(Qt.RichText)
        self.fil.setToolTip(_("Cliquez une étape déjà vue pour y revenir : rien n'est perdu ni refait"))
        self.fil.linkActivated.connect(lambda lien: self.revenir_a(int(lien)))
        v.addWidget(self.fil)
        self.pages = QStackedWidget()
        for fabrique in (self._page_idee, self._page_qui, self._page_plans, self._page_images, self._page_video,
                         self._page_m_elements, self._page_m_deroule, self._page_m_paroles, self._page_m_creer,
                         self._page_i_elements, self._page_i_texte, self._page_i_creer):
            self.pages.addWidget(fabrique())
        v.addWidget(self.pages, 1)
        # --- toujours là : écrire librement, budget, état, navigation
        hl = QHBoxLayout()
        self.libre = QLineEdit()
        self.libre.setPlaceholderText(_("Ou dites-le en clair : « le plan 3 plus court », « ajoute un plan où il salue », « une voix plus grave »…"))
        self.libre.returnPressed.connect(self.dire)
        self.libre.setToolTip(_("Pour changer quelque chose sans chercher où : écrivez ce que vous voulez, l'assistant modifie lui-même "
                                "les cartes, les plans ou la musique, puis vous montre le résultat. A la page 1, la phrase "
                                "s'ajoute à votre idée."))
        aide_libre = QLabel("ⓘ")
        aide_libre.setToolTip(self.libre.toolTip())
        hl.addWidget(aide_libre)
        hl.addWidget(self.libre, 1)
        self.b_dire = QPushButton(_("Envoyer"))
        self.b_dire.clicked.connect(self.dire)
        hl.addWidget(self.b_dire)
        hl.addWidget(QLabel(_("Assistant :")))
        self.niveau_bas = QComboBox()                   # 0.9.86 : le cerveau se voit et se change à chaque étape
        self.niveau_bas.setModel(self.niveau.model())
        self.niveau_bas.setCurrentIndex(self.niveau.currentIndex())
        self.niveau_bas.setToolTip(_("Qui lit l'idée, découpe en plans, vérifie la continuité, relit et améliore les textes. Les "
                                     "images sont faites par Gemini, la vidéo par le moteur choisi."))
        self.niveau_bas.currentIndexChanged.connect(lambda i: self.niveau.setCurrentIndex(i))
        self.niveau.currentIndexChanged.connect(lambda i: (self.niveau_bas.setCurrentIndex(i), self._maj_credits()))
        hl.addWidget(self.niveau_bas)
        v.addLayout(hl)
        from .credit_ia import LigneCredit
        hc = QHBoxLayout()                              # 0.9.86 : crédit et « Recharger » de chaque IA utilisée
        self.credits = [LigneCredit(self.params, None, compact=True) for _i in range(3)]
        for c in self.credits:
            hc.addWidget(c, 1)
        v.addLayout(hc)
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

    def _maj_credits(self):
        """Les comptes réellement utilisés : le cerveau, Gemini pour les images (vidéo), le moteur vidéo."""
        if not hasattr(self, "credits"):
            return
        from .credit_ia import fournisseur_du_moteur
        f = {"claude": "anthropic", "gemini": "google"}.get(self._niveau())
        voulus = [f]
        if self.genre == "video":
            voulus.append("google" if A.images_par(self.seq, self.params) == "gemini" else None)
            m = self.moteur.currentData() if hasattr(self, "moteur") else None
            voulus.append(fournisseur_du_moteur(m, self.params))
        vus = []
        for x in voulus:
            if x and x not in vus:
                vus.append(x)
        for i, c in enumerate(self.credits):
            nouveau = vus[i] if i < len(vus) else None
            if nouveau != c.fournisseur:
                c.montrer(nouveau)

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
                                           _("Exemples :\n· la suite de ce plan : il pose sa tasse, se lève et sort par la porte du "
                                             "jardin\n· une scène : un enfant lâche un ballon rouge qui s'envole au-dessus des toits, sa mère "
                                             "le console\n· une chanson pop joyeuse de 2 minutes, voix d'homme, refrain qui monte\n· une "
                                             "intro de 4 s pour ma chaîne de cuisine, avec mon logo et un petit son"))
        self.histoire = self.c_histoire.t
        self.c_histoire.change.connect(self._deviner)
        v.addWidget(self.c_histoire, 1)
        v.addWidget(QLabel(_("L'assistant comprend :")))
        self.g_genre = QButtonGroup(self)
        self.r_suite = QRadioButton(_("La suite de ce plan (elle part de sa dernière image, avec les mêmes personnes)"))
        self.r_raccord = QRadioButton(_("Ce qui n'a pas été filmé entre ce plan et le suivant (relier deux rushes)"))
        self.r_raccord.setToolTip(_("La vidéo part de la dernière image de ce plan et arrive exactement sur la première image du "
                                    "plan suivant ; les images clefs entre les deux sont créées avec vos personnes, objets et "
                                    "lieux réels."))
        self.r_scene = QRadioButton(_("Une nouvelle scène vidéo, en plusieurs plans"))
        self.r_musique = QRadioButton(_("Une musique ou une chanson"))
        self.r_logo = QRadioButton(_("Une intro ou un logo animé"))
        for r in (self.r_suite, self.r_raccord, self.r_scene, self.r_musique, self.r_logo):
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
        self.image_b, self.image_ab, self.clip_b = "", "", None
        self.l_rush.setText(_("Plan choisi : « {n} ».", n=c.get("nom") or m.get("nom", "")) if ok else
                            _("Pour continuer un plan : clic droit sur le plan dans la timeline › « Continuer ce plan avec "
                              "l'assistant IA… »."))
        self.l_manques.setText(" ".join(A.manques(self.params)))
        if ok:
            self.v_depart.addWidget(QLabel(_("La suite part de cette image :")))
            vg = Vignette(self.image, 260)
            vg.clic.connect(lambda ch: agrandir(self, ch))
            self.v_depart.addWidget(vg)
            if m.get("genre") == "video":
                self._preparer_suivant(c)
            self.v_depart.addStretch(1)
        self.r_raccord.setEnabled(bool(self.image_b))

    def _preparer_suivant(self, c):
        """0.9.87 : le plan qui suit sur la même piste ; sa première image est l'arrivée d'un raccord."""
        from .projet import fin_clip
        p = self.ed.projet
        fin = fin_clip(c)
        suivants = sorted((x for x in p.clips_piste(c.get("piste", "video")) if x["id"] != c["id"] and x["debut"] >= fin - 0.05),
                          key=lambda x: x["debut"])
        if not suivants:
            return
        cb = suivants[0]
        mb = p.media(cb["media"])
        if not (mb and os.path.exists(mb.get("chemin") or "")):
            return
        if mb.get("genre") == "image":
            self.image_b = mb["chemin"]
        elif mb.get("genre") == "video":
            from . import prolonger
            self.image_b = prolonger._image(mb["chemin"], float(cb.get("src_debut") or 0.0) + 1.0 / max(1.0, float(p.cadence)),
                                            os.path.join(Q.dossier(self.seq), "arrivee_raccord.png"))
        if not (self.image_b and os.path.exists(self.image_b)):
            self.image_b = ""
            return
        self.clip_b = cb
        self.image_ab = A.image_raccord(self.image, self.image_b, os.path.join(Q.dossier(self.seq), "raccord_avant_apres.png"))
        self.v_depart.addWidget(QLabel(_("Début du plan suivant (pour relier) :")))
        vb = Vignette(self.image_b, 260)
        vb.clic.connect(lambda ch: agrandir(self, ch))
        self.v_depart.addWidget(vb)

    def _raccord(self):
        return self.genre == "video" and self.r_raccord.isChecked() and bool(getattr(self, "image_b", ""))

    def _image_cartes(self):
        """L'image où l'on encadre les personnes : avant | après pour un raccord, sinon la dernière image du plan."""
        return self.image_ab if self._raccord() and self.image_ab else self.image

    def _deviner(self):
        """Le genre se déduit des mots au fil de la frappe, tant que l'utilisateur n'a pas choisi lui-même."""
        if self._genre_choisi:
            return
        g = I.deviner_genre(self.c_histoire.texte(), bool(self.image))
        if g == "suite" and self.r_raccord.isChecked():
            return                                  # relier deux rushes reste choisi
        {"suite": self.r_suite, "scene": self.r_scene, "musique": self.r_musique, "logo": self.r_logo}[g].setChecked(True)

    def choisir_genre(self, genre):
        """Ouvert depuis le menu Musique : la musique est choisie d'office (on peut encore changer), si l'on est au début."""
        if self.pages.currentIndex() == P_IDEE:
            {"musique": self.r_musique, "scene": self.r_scene, "suite": self.r_suite, "intro": self.r_logo}[genre].setChecked(True)
            self._genre_choisi = True

    def _suite(self):
        """La vidéo part de la dernière image du plan choisi (continuer, ou relier au plan suivant)."""
        return self.genre == "video" and (self.r_suite.isChecked() or self._raccord()) and bool(self.image)

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
        if self.genre == "musique" and self.musique is not None:
            return self.musique
        if self.genre == "intro" and getattr(self, "intro", None) is not None:
            return self.intro
        return self.seq

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
        for lib, genre in ((_("+ Une personne"), "personne"), (_("+ Un objet"), "objet"), (_("+ Un lieu"), "lieu")):
            b = QPushButton(lib)
            b.clicked.connect(lambda _c=False, g=genre: self._ajouter_carte(g))
            hb.addWidget(b)
        hb.addStretch(1)
        v.addLayout(hb)
        self.accord = QCheckBox(_("Les personnes réelles (de l'image ou des photos) sont d'accord pour être animées par l'IA (ou c'est moi)"))
        v.addWidget(self.accord)
        h.addLayout(v, 1)
        return w

    def _element_de(self, p, lieu=False):
        if lieu:
            return I.element("lieu", p["nom"], p.get("description", ""), p.get("source") or "inventer", genre="lieu",
                             photo=p.get("photo", ""), images=list(p.get("images") or []), biblio=p.get("biblio", ""))
        return I.element(p.get("genre", "personne"), p["nom"], p.get("brut") or p.get("description", ""),
                         p.get("source") or ("image" if p.get("sur_image") else "inventer"), genre=p.get("genre", "personne"),
                         boite=p.get("boite"), photo=p.get("photo", ""), decoupe=p.get("decoupe", ""), style=p.get("style", ""),
                         position=p.get("position", ""), biblio=p.get("biblio", ""), planche=p.get("planche", ""),
                         images=list(p.get("images") or []) if p.get("source") == "bibliotheque" else [],
                         tenue=p.get("tenue") or None, mode=p.get("mode", ""))

    def _remplir_cartes(self):
        vider(self.v_cartes)
        self.cartes = []
        for p in self.seq["personnages"]:
            self._carte(self._element_de(p))
        for li in self.seq.get("lieux") or []:
            self._carte(self._element_de(li, lieu=True))
        self.v_cartes.addStretch(1)
        vider(self.v_image)
        self.image_cadres = None
        if self._suite():
            self.image_cadres = ImageCadres(self._image_cartes(), 320)
            self.image_cadres.trace.connect(self._cadre_trace)
            self.v_image.addWidget(QLabel(_("Avant | après (les deux rushes) :") if self._raccord() else _("Dernière image du plan :")))
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
                         {"personne": _("Personne"), "objet": _("Objet"), "lieu": _("Lieu")}[e["type"]], self.garder_carte)
        c.change.connect(self._maj_cadres)
        c.active.connect(self._activer)
        self.cartes.append(c)
        self.v_cartes.insertWidget(len(self.cartes) - 1, c)
        return c

    def _ajouter_carte(self, genre):
        n = sum(1 for c in self.cartes if c.e["type"] == genre) + 1
        nom = {"personne": _("Personne {n}", n=n), "objet": _("Objet {n}", n=n), "lieu": _("Lieu {n}", n=n)}[genre]
        e = I.element(genre, nom, "", "image" if self._suite() else "inventer", genre=genre)
        if self._suite() and genre != "lieu":
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
        self.image_cadres.cadres = [(k + 1, c._couleur, c.e.get("boite") if c.e.get("source") == "image" and c.e["type"] != "lieu" else None)
                                    for k, c in enumerate(self.cartes)]
        self.image_cadres.actif = self.cartes.index(actif) if actif in self.cartes else -1
        self.image_cadres.update()

    def _cadre_trace(self, boite):
        c = getattr(self, "_active", None)
        if c not in self.cartes:
            self.etat.setText(_("Cliquez d'abord la carte de la personne ou de l'objet."))
            return
        if c.e["type"] == "lieu":
            self.etat.setText(_("Un lieu pris dans l'image garde toute l'image : rien à encadrer."))
            return
        c.e["boite"] = [round(x, 4) for x in boite]
        c.e["decoupe"] = ""
        if c.e.get("source") != "image":
            c.radios["image"].setChecked(True)
        try:
            c.e["decoupe"] = A.decouper(self._image_cartes(), c.e["boite"], os.path.join(Q.dossier(self.seq), f"decoupe_carte_{id(c) % 10 ** 6}.png"))
        except Exception:      # noqa: BLE001
            c.e["decoupe"] = ""
        c.rafraichir()
        self._maj_cadres()

    def _options_personne(self, carte, source):
        e = carte.e
        if source == "bibliotheque":
            return self._options_bibliotheque(carte)
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 0, 0, 0)
        if source == "image" and e["type"] == "lieu":
            v.addWidget(self._aide(_("Le décor de la dernière image sert de référence au lieu.")))
        elif source == "image":
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
            br = QPushButton(_("Image d'un rush…"))
            br.setToolTip(_("Placez la ligne rouge sur un rush (ou une photo du montage) où on le voit, puis encadrez-le"))
            br.clicked.connect(lambda: self._photo_ligne_rouge(carte))
            h.addWidget(br)
            h.addWidget(QLabel(os.path.basename(e.get("photo") or "") or _("aucune")), 1)
            v.addLayout(h)
        if e["type"] == "lieu":
            return w
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
        if e.get("type") == "personne":
            from . import tenues as T
            ht = QHBoxLayout()
            ht.addWidget(QLabel(_("Tenue dans cette scène")))
            ct = QComboBox()
            ct.addItem(_("Celle de l'image ou de la description"), "")
            for x in T.toutes(self.params):
                ct.addItem(("★ " if x["source"] == "biblio" else "") + x["nom"], x["id"])
            ct.setCurrentIndex(max(0, ct.findData((e.get("tenue") or {}).get("id", ""))))
            ct.setToolTip(_("★ = votre bibliothèque. Sa fiche est dessinée avec cette tenue, et chaque plan la rappelle."))

            def tenue(_i, ct=ct, carte=carte):
                t = T.trouver(self.params, ct.currentData())
                carte.e["tenue"] = {"id": t["id"], "nom": t["nom"], "description": t["description"], "en": t.get("en", ""),
                                    "image": t.get("image", "")} if t else None
            ct.currentIndexChanged.connect(tenue)
            ht.addWidget(ct, 1)
            v.addLayout(ht)
        return w

    def _choisir_photo(self, carte):
        from .widgets import ouvrir_fichier
        ch = ouvrir_fichier(self, _("Photo de « {n} »", n=carte.e.get("nom", "")), _("Images") + " (*.png *.jpg *.jpeg *.webp)", "image",
                            self.params)
        if ch:
            carte.e["photo"] = ch
            carte.rafraichir()

    def _photo_ligne_rouge(self, carte):
        """0.9.88 : la personne, l'objet ou le lieu pris dans n'importe quel rush (ligne rouge), puis encadré."""
        from .cartes_assistant import encadrer, image_ligne_rouge
        t = self.ed.timeline.position
        image = image_ligne_rouge(self.ed)
        if not image:
            self.etat.setText(_("Placez la ligne rouge sur une image d'un rush ou d'une photo, puis recommencez."))
            return
        if carte.e.get("type") == "lieu":
            carte.e["photo"] = image
            carte.rafraichir()
            return
        boite = getattr(self, "_test_boite", None)
        if boite is None:
            boite = encadrer(self, image, _("Encadrez « {n} »", n=carte.e.get("nom", "")))
            if not boite:
                return
        dec = A.decouper(image, boite, os.path.join(Q.dossier(self.seq), f"rush_{id(carte) % 10 ** 6}_{int(t * 1000)}.png"))
        if dec:
            carte.e["photo"] = dec
            carte.rafraichir()
            self.etat.setText(_("✓ Pris dans le rush : sa fiche sera faite d'après cette image."))

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

    def _lire_lieux(self):
        return [{"nom": c.e["nom"].strip(), "description": (c.e.get("description") or "").strip(), "source": c.e.get("source") or "inventer",
                 "sur_image": c.e.get("source") == "image", "photo": c.e.get("photo", ""), "images": c.e.get("images") or [],
                 "biblio": c.e.get("biblio", "")} for c in self.cartes if c.e["type"] == "lieu" and (c.e.get("nom") or "").strip()]

    def _lire_cartes(self):
        persos = []
        for c in self.cartes:
            e = c.e
            if not (e.get("nom") or "").strip() or e["type"] == "lieu":
                continue
            persos.append({"nom": e["nom"].strip(), "genre": e.get("genre") or e["type"], "sur_image": e.get("source") == "image",
                           "position": e.get("position", ""), "description": (e.get("description") or "").strip(),
                           "style": e.get("style", ""), "source": e.get("source") or "inventer", "boite": e.get("boite"),
                           "photo": e.get("photo", ""), "decoupe": e.get("decoupe") or None, "biblio": e.get("biblio", ""),
                           "planche": e.get("planche", "") if e.get("source") == "bibliotheque" else None,
                           "images": e.get("images") if e.get("source") == "bibliotheque" else None,
                           "accord": (bool(self.accord.isChecked()) and e.get("source") in ("image", "photo")) or
                                     (e.get("source") == "bibliotheque" and bool(e.get("accord"))),
                           "tenue": e.get("tenue") or None, "mode": e.get("mode", "")})
        return persos

    def _avec_personnes_reelles(self):
        return any(c.e.get("type") == "personne" and c.e.get("source") in ("image", "photo") for c in self.cartes)

    # ------------------------------------------------------------------ bibliothèque (0.9.81)
    def _depuis_catalogue(self, carte):
        """0.9.89 : la bibliothèque toute faite, filtrée pour cette carte ; l'entrée prise remplit la carte."""
        from . import bibliotheque_creations as B
        from .dialogues_catalogue_prompts import DialogueCatalogue
        genres = {"personne": ("personnage",), "objet": ("objet",), "lieu": ("lieu",)}.get(carte.e.get("type"), None)
        d = getattr(self, "_test_catalogue", None) or DialogueCatalogue(self, self.params, genres)
        if not getattr(self, "_test_catalogue", None):
            d.exec()
        if d.ajoutees:
            x = d.ajoutees[-1]
            B.vers_carte(x, carte.e)
            carte.e["source"] = "bibliotheque"
            carte.nom.blockSignals(True)
            carte.nom.setText(carte.e["nom"])
            carte.nom.blockSignals(False)
            carte.mettre_description(carte.e.get("description", ""))
            carte.rafraichir()

    def _options_bibliotheque(self, carte):
        from . import bibliotheque_creations as B
        e = carte.e
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 0, 0, 0)
        entrees = B.lister(self.params, B.CARTES_POUR.get(e["type"], ()))
        h = QHBoxLayout()
        cb = QComboBox()
        cb.addItem(_("Choisir…") if entrees else _("Rien encore de ce genre dans votre bibliothèque"), "")
        for x in entrees:
            cb.addItem(x["nom"], x["id"])
        cb.setCurrentIndex(max(0, cb.findData(e.get("biblio") or "")))
        h.addWidget(cb, 1)
        b = QPushButton(_("Ma bibliothèque…"))
        b.setToolTip(_("Voir, créer, renommer ce qui est gardé"))
        b.clicked.connect(lambda: self.ed.bibliotheque_creations())
        h.addWidget(b)
        bt = QPushButton(_("Toute faite…"))
        bt.setToolTip(_("Prendre une description toute prête (lieu, véhicule, avion, personnage type) : elle rejoint votre "
                        "bibliothèque et cette carte"))
        bt.clicked.connect(lambda: self._depuis_catalogue(carte))
        h.addWidget(bt)
        v.addLayout(h)
        choisie = next((x for x in entrees if x["id"] == e.get("biblio")), None)
        if choisie:
            hh = QHBoxLayout()
            if B.apercu(choisie):
                hh.addWidget(Vignette(B.apercu(choisie), 110))
            hh.addWidget(self._aide(B.resume(choisie)), 1)
            v.addLayout(hh)

        def choisir(_i):
            x = next((y for y in entrees if y["id"] == cb.currentData()), None)
            if x is None:
                return
            B.vers_carte(x, e)
            carte.nom.blockSignals(True)
            carte.nom.setText(e["nom"])
            carte.nom.blockSignals(False)
            carte.mettre_description(e.get("description", ""))
            carte.rafraichir()
            self._maj_cadres()
        cb.currentIndexChanged.connect(choisir)
        return w

    def garder_carte(self, carte, planche=""):
        """« ☆ Garder » : la carte telle qu'elle est (fiche, découpe, voix, style) rangée dans la bibliothèque, sous un nom choisi."""
        from . import bibliotheque_creations as B
        e = carte.e if hasattr(carte, "e") else carte
        if not planche and e.get("type") in ("personne", "objet"):
            p = next((x for x in self.seq["personnages"] if x["nom"].lower() == (e.get("nom") or "").lower()), None)
            planche = (p or {}).get("planche", "")
        nom, ok = self._precision(_("Garder dans ma bibliothèque"), _("Nom sous lequel le retrouver (ex. : « Chanteuse rock chaude », "
                                                                     "« Vieux marin à la barbe blanche ») :"), e.get("nom", ""))
        if not ok or not nom.strip():
            return
        try:
            x = B.depuis_carte(self.params, e, nom.strip(), planche)
        except Exception as err:      # noqa: BLE001
            self.etat.setText("✕ " + texte_erreur(err))
            return
        self.etat.setText(_("✓ « {n} » est dans votre bibliothèque ({g}).", n=x["nom"], g=B.GENRES[x["genre"]][0]))

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
        v.addWidget(self._aide(_("Corrigez le texte, qui on voit (noms séparés par une virgule ; vide = personne, seulement le décor "
                                 "ou un objet), le cadrage ou la durée. Les personnes qui ne sont plus visibles (dans la voiture, "
                                 "sorties) ne reviennent pas : survolez « Qui » pour voir où elles sont. Un plan à deux actions est "
                                 "coupé en deux tout seul.")))
        self.t_plans = QTableWidget(0, 4)
        self.t_plans.setHorizontalHeaderLabels([_("Ce qu'on voit"), _("Qui"), _("Cadrage"), _("Durée (s)")])
        self._table(self.t_plans, (1, 3), 0)
        v.addWidget(self.t_plans, 1)
        h = QHBoxLayout()
        for lib, fn in ((_("Ajouter un plan"), self._ajouter_plan), (_("Retirer"), lambda: self._retirer(self.t_plans)),
                        (_("✨ Améliorer le plan choisi"), self._ameliorer_plan),
                        (_("✨ Vérifier la continuité"), self.verifier_continuite)):
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
        self.moteur.currentIndexChanged.connect(lambda _i: (self._maj_prix(), self._maj_credits()))
        hm.addWidget(self.moteur, 1)
        v.addLayout(hm)
        hi = QHBoxLayout()                              # 0.9.86 : qui fait les images de contrôle
        hi.addWidget(QLabel(_("Images de contrôle")))
        self.images_par = QComboBox()
        for k, lib in (("gemini", _("Gemini : visages fidèles, environ 0,04 $ l'image")),
                       ("locale", _("IA de ce poste : gratuite, visages approximatifs")),
                       ("aucune", _("Aucune : la vidéo part directement"))):
            self.images_par.addItem(lib, k)
        self.images_par.setToolTip(_("Avant la vidéo, une image de départ et une image d'arrivée par plan, à regarder et corriger. "
                                     "Gemini garde les visages des fiches ; l'IA de ce poste ne coûte rien mais les visages "
                                     "changent ; sans images, le moteur vidéo invente tout seul la fin de chaque plan."))
        self.images_par.setCurrentIndex(max(0, self.images_par.findData(A.images_par(self.seq, self.params))))
        self.images_par.currentIndexChanged.connect(self._images_par_change)
        hi.addWidget(self.images_par, 1)
        v.addLayout(hi)
        self.l_prix = QLabel("")
        self.l_prix.setWordWrap(True)
        v.addWidget(self.l_prix)
        return w

    def _images_par_change(self, _i=None):
        voulu = self.images_par.currentData()
        if voulu == "gemini" and not self.params.get("clef_gemini"):
            self.etat.setText(_("Il faut une clef Gemini (Préférences › IA › Connecter une IA)."))
        elif voulu == "locale" and not A.image_locale_possible(self.params):
            self.etat.setText(_("Aucun modèle d'image sur ce poste : Préférences › IA locale."))
        self.seq["images_par"] = voulu
        self.params["assistant_images_par"] = voulu
        self.images_par.blockSignals(True)
        self.images_par.setCurrentIndex(max(0, self.images_par.findData(A.images_par(self.seq, self.params))))
        self.images_par.blockSignals(False)
        self._maj_prix()
        self._maj_credits()

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
        it = QTableWidgetItem(pl.get("action", ""))
        it.setData(Qt.UserRole, {k: pl.get(k) for k in ("hors_champ", "visibles_fixes") if pl.get(k)})
        t.setItem(r, 0, it)
        qui = QTableWidgetItem(", ".join(pl.get("personnages") or []) if (pl.get("personnages") or pl.get("visibles_fixes"))
                               else ", ".join(p["nom"] for p in self.seq.get("personnages") or []))
        if pl.get("hors_champ"):
            qui.setToolTip(_("Pas visibles : {t}", t=pl["hors_champ"]))
        t.setItem(r, 1, qui)
        t.setItem(r, 2, QTableWidgetItem(pl.get("camera", "")))
        t.setItem(r, 3, QTableWidgetItem(str(int(pl.get("duree") or Q.DUREE_PLAN))))

    def verifier_continuite(self):
        """La scripte (0.9.86) : qui est visible plan par plan, où sont les autres, quel cadrage."""
        if self._en_calcul():
            return
        self._lire()
        seq, niveau = copy.deepcopy(self.seq), self._niveau()

        def fin(r, e):
            if e or r is None:
                return
            for a, b in zip(self.seq["plans"], seq["plans"]):
                for k in ("personnages", "hors_champ", "camera", "visibles_fixes"):
                    a[k] = b.get(k)
            if self._cloud():
                A.depenser(self.seq, _("Continuité"), A.PRIX_LECTURE)
            self._remplir_plans()
            self._maj_prix()
            self.etat.setText(_("✓ Continuité vérifiée : {n} plan(s) corrigé(s). Vérifiez « Qui » et « Cadrage ».", n=r))
        self._lancer(lambda _t: A.continuite(self.params, seq, niveau), _("L'assistant vérifie qui est visible dans chaque plan"), fin)

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
                    duree = int(float((self.t_plans.item(r, 3).text() or "").replace(",", ".")))
                except (ValueError, AttributeError):
                    duree = Q.DUREE_PLAN
                camera = (self.t_plans.item(r, 2).text() if self.t_plans.item(r, 2) else "").strip()
                pl = {"action": action, "personnages": qui, "duree": max(3, min(15, duree)), "camera": camera,
                      "visibles_fixes": True}                 # 0.9.86 : ce que montre « Qui » fait foi (vide = personne)
                pl.update({k: v for k, v in (self.t_plans.item(r, 0).data(Qt.UserRole) or {}).items() if k == "hors_champ"})
                plans.append(pl)
        else:
            plans = A.etat(self.seq)["plans"]
            for pl in plans:
                pl["personnages"] = [noms[n.lower()] for n in pl["personnages"] if n.lower() in noms]
        analyse = {"personnages": persos, "plans": plans}
        if self.cartes:
            analyse["lieux"] = self._lire_lieux()
        A.appliquer(self.seq, analyse, self.image if self._suite() else None, self._image_cartes() if self._suite() else None)

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
        v.addWidget(self._titre(_("Regardez avant la vidéo : les fiches et les images clefs")))
        v.addWidget(self._aide(_("Les fiches gardent chacun identique (personnes, objets, véhicules). Les images clefs fixent l'état "
                                 "de la scène là où il compte ; entre elles, les gestes s'enchaînent sur la vraie vidéo. Cliquez une "
                                 "image pour l'agrandir.")))
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
        etapes = ETAPES.get(self.genre, ETAPES["video"])
        self._vues = getattr(self, "_vues", set()) | {k}
        self.fil.setText("   ›   ".join(f"<b>{e}</b>" if p == k else (f"<a href='{p}'>{e}</a>" if p in self._vues else e)
                                        for p, e in etapes))
        self.b_suiv.setText(BOUTONS[k])
        self._maj()
        self._maj_credits()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _maj(self):
        calc = self._en_calcul()
        k = self.pages.currentIndex()
        self.b_prec.setEnabled(k > P_IDEE and (not calc or k in (P_IMAGES, P_VIDEO)))
        pret = True
        if k == P_VIDEO:
            pret = any(pl.get("fichier") and os.path.exists(pl["fichier"]) for pl in self.seq["plans"])
        elif k == P_M_CREER:
            pret = bool(getattr(self, "resultat", ""))
        elif k == P_I_CREER:
            pret = bool(getattr(self, "intro_fichier", ""))
        self.b_suiv.setEnabled(not calc and pret)
        self.b_dire.setEnabled(not calc)
        self.b_reduire.setVisible(calc)
        self.b_manuel.setEnabled(not calc and k != P_IDEE)
        if k == P_VIDEO:
            self.b_refaire.setEnabled(not calc and self.l_plans.currentRow() >= 0)
            self.b_reprendre.setVisible(not calc and any(not pl.get("fichier") for pl in self.seq["plans"]))
        if k == P_M_CREER:
            self._maj_creer()
        if k == P_I_CREER:
            self.b_fab_intro.setEnabled(not calc)
            self.b_garder_style.setEnabled(not calc)
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

    def revenir_a(self, cible):
        """Clic sur une étape du fil (0.9.86) : on y revient, ce qui est fait est gardé ; en avançant, seul ce qui a changé est
        refait."""
        k = self.pages.currentIndex()
        if cible == k:
            return
        if self._en_calcul() and k in (P_QUI, P_PLANS):
            self.etat.setText(_("L'assistant calcule : attendez la fin, ou « Réduire »."))
            return
        if k in (P_QUI, P_PLANS) and not self._en_calcul():
            self._lire()
        if k in (P_M_DEROULE, P_M_PAROLES):
            self._lire_musique()
        if cible == P_QUI:
            self._remplir_cartes()
        elif cible == P_PLANS:
            self._remplir_plans()
            self._maj_prix()
        elif cible == P_IMAGES:
            self._remplir_images()
        elif cible == P_VIDEO:
            self._remplir_video()
        self.aller(cible)

    def precedent(self):
        k = self.pages.currentIndex()
        if k in (P_QUI, P_PLANS):
            self._lire()
        if k in (P_M_DEROULE, P_M_PAROLES):
            self._lire_musique()
        if k == P_I_TEXTE:
            self._lire_intro()
        if self.genre == "intro":
            ordre = [p for p, _e in ETAPES["intro"]]
            self.aller(ordre[max(0, ordre.index(k) - 1)])
            return
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
                self.genre = "intro"
                self.analyser_intro()
                return
            if self.r_musique.isChecked():
                self.genre = "musique"
                self.analyser_musique()
            else:
                self.genre = "video"
                if self.seq.get("plans") and self.seq.get("histoire") == self.c_histoire.texte() and \
                        getattr(self, "_lue_avec", None) == (self._suite(), self._niveau(), self._raccord()):
                    self.aller(P_QUI)              # 0.9.86 : rien n'a changé : on retrouve tout tel quel
                    return
                if self.seq.get("plans") and getattr(self, "_lue_avec", None) and getattr(self, "_test_oui", None) is None \
                        and QMessageBox.question(
                        self, _("Assistant de création"),
                        _("Votre idée a changé. Relire l'idée ? Les cartes et les plans seront refaits ; les fiches, images et "
                          "vidéos des plans qui ne changent pas sont gardées.\n\n« Non » garde tout tel quel.")) != QMessageBox.Yes:
                    self.aller(P_QUI)
                    return
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
            if self.seq["personnages"] and not any(pl.get("visibles_fixes") for pl in self.seq["plans"]):
                self.verifier_continuite()        # 0.9.86 : découpage fait sans l'IA : la scripte passe d'office
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
        elif k == P_I_ELEM:
            manquent = [f"{c.e.get('nom')} : {I.manque(c.e)}" for c in self.icartes if I.manque(c.e)]
            if manquent:
                self.etat.setText(_("A compléter : {l}", l=" · ".join(manquent)))
                return
            self._remplir_texte_intro()
            self.aller(P_I_TEXTE)
        elif k == P_I_TEXTE:
            self._lire_intro()
            self.aller(P_I_CREER)
            self.fabriquer_intro()
        elif k == P_I_CREER:
            self.poser_intro()

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
        raccord = self._raccord()
        if raccord:
            self.seq["raccord"] = {"image_debut": self.image, "image_fin": self.image_b,
                                   "clip_b": (self.clip_b or {}).get("id", "")}
        else:
            self.seq.pop("raccord", None)
        vue = self._image_cartes() if image else None

        def travail(_t):
            try:
                return A.analyser(self.params, histoire, vue, niveau, image_fin=self.image_b if raccord else None), None
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
            A.appliquer(self.seq, analyse, image, vue)
            self._lue_avec = (bool(image), niveau, raccord) if not souci else None     # lecture ratée : « Suivant » réessaie
            self._remplir_cartes()
            self._remplir_plans()
            self.aller(P_QUI)
            if self.cartes:
                self._activer(self.cartes[0])
            self.etat.setText(_("⚠ L'assistant n'a pas pu lire votre idée ({e}). PhilCut l'a découpée sans IA, phrase par phrase : "
                                "ajoutez les personnes avec « + Une personne » ; à l'étape des plans, l'assistant vérifiera qui "
                                "est visible dans chaque plan. Ou « ‹ Précédent » pour réessayer, ou changer d'assistant.",
                                e=texte_erreur(souci)[:160]) if souci else
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
        if self.genre == "intro":
            self._dire_intro(texte)
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
        if A.images_par(self.seq, self.params) != "aucune" and sum(A.a_preparer(self.seq, self.params)) == 0:
            self._remplir_images()                 # 0.9.86 : tout est déjà fait : rien à repayer
            self.aller(P_IMAGES)
            self.etat.setText(_("Les fiches et images sont déjà faites : rien n'a été refait."))
            return
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
        if A.images_par(self.seq, self.params) == "aucune":     # pas d'images de contrôle : droit à la vidéo
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

    def _remplir_images(self, cible=None):
        """cible = (plan, "depart" / "arrivee") : l'image qu'on vient de refaire, montrée et entourée (0.9.86)."""
        self._vignettes_plans = {}
        w = QWidget()
        g = QGridLayout(w)
        ligne = 0
        g.addWidget(self._titre(_("Personnages et objets")), ligne, 0, 1, 3)
        ligne += 1
        for k, p in enumerate(self.seq["personnages"]):
            vg = Vignette(p.get("planche", ""), 170, _("Pas de fiche"))
            vg.clic.connect(lambda ch: agrandir(self, ch))
            g.addWidget(vg, ligne, 0)
            lb = QLabel(f"<b>{p['nom']}</b><br>{p.get('description', '')}")
            lb.setWordWrap(True)
            g.addWidget(lb, ligne, 1)
            bl = QVBoxLayout()
            b = QPushButton(_("Corriger…"))
            b.clicked.connect(lambda _c=False, k=k: self.corriger_fiche(k))
            bl.addWidget(b)
            bg = QPushButton(_("☆ Garder"))
            bg.setToolTip(_("Ranger cette fiche dans « Ma bibliothèque de créations »"))
            bg.clicked.connect(lambda _c=False, k=k: self._garder_fiche(k))
            bl.addWidget(bg)
            bl.addStretch(1)
            g.addLayout(bl, ligne, 2)
            ligne += 1
        g.addWidget(self._titre(_("Les images clefs")), ligne, 0, 1, 3)
        ligne += 1
        g.addWidget(self._aide(_("Chaque plan part de la vraie fin de la vidéo du plan d'avant : les gestes s'enchaînent sans image "
                                 "inventée. On n'impose une image de fin (image clef) que là où la scène doit être exactement "
                                 "respectée : un nouveau lieu, quelqu'un qui attend ou arrive, et la fin. Une image clef se crée "
                                 "avec vos fiches et les photos réelles du lieu, ou se prend dans un rush (ligne rouge).")), ligne, 0, 1, 3)
        ligne += 1
        n = len(self.seq["plans"])
        for i, pl in enumerate(self.seq["plans"]):
            lb = QLabel(_("<b>Plan {i}</b> ({d} s) : {a}", i=i + 1, d=pl.get("duree"), a=pl.get("action", "")))
            lb.setWordWrap(True)
            g.addWidget(lb, ligne, 0, 1, 3)
            ligne += 1
            # départ
            bloc = QVBoxLayout()
            depart = Q.depart_prevu(self.seq, i)
            enchaine = i > 0 and pl.get("enchainer", True) and not pl.get("image")
            vg = Vignette(depart, 200, _("Part de la fin de la vidéo du plan {k}", k=i) if enchaine else _("Pas d'image de départ"))
            vg.clic.connect(lambda ch: agrandir(self, ch))
            self._vignettes_plans[(i, "depart")] = vg
            if cible == (i, "depart"):
                vg.setStyleSheet("border: 3px solid #f5a524; border-radius: 6px;")
            bloc.addWidget(vg)
            if not enchaine and not (i == 0 and self._suite()):
                b = QPushButton(_("Corriger le départ…"))
                b.clicked.connect(lambda _c=False, i=i: self.corriger_image(i, "depart"))
                bloc.addWidget(b)
            elif i == 0 and self._suite():
                bloc.addWidget(self._aide(_("Image réelle : la fin du rush.")))
            g.addLayout(bloc, ligne, 0)
            # fin
            bloc = QVBoxLayout()
            if pl.get("fin_reelle"):
                vg = Vignette(pl.get("image_fin", ""), 200, "")
                bloc.addWidget(vg)
                bloc.addWidget(self._aide(_("Image réelle : le début du rush suivant. La vidéo y arrive exactement.")))
            else:
                case = QCheckBox(_("Image clef à la fin de ce plan"))
                case.setChecked(not pl.get("sans_fin"))
                case.setToolTip(_("Cochée : la vidéo doit arriver sur cette image (lieu, personnes, état de la scène). "
                                  "Décochée : le moteur enchaîne librement les gestes (souvent plus naturel)."))
                case.toggled.connect(lambda on, i=i: self._basculer_clef(i, on))
                bloc.addWidget(case)
                if pl.get("clef_pourquoi") and not pl.get("sans_fin"):
                    bloc.addWidget(self._aide(_("Pourquoi : {p}", p=pl["clef_pourquoi"])))
                if not pl.get("sans_fin"):
                    vg = Vignette(pl.get("image_fin", ""), 200, _("Image clef à créer"))
                    vg.clic.connect(lambda ch: agrandir(self, ch))
                    self._vignettes_plans[(i, "arrivee")] = vg
                    if cible == (i, "arrivee"):
                        vg.setStyleSheet("border: 3px solid #f5a524; border-radius: 6px;")
                        vg.setToolTip(_("L'image refaite"))
                    bloc.addWidget(vg)
                    hb = QHBoxLayout()
                    b = QPushButton(_("Créer…") if not pl.get("image_fin") else _("Corriger…"))
                    b.setToolTip(_("Avec vos fiches et les photos réelles du lieu ; dites ce qu'on doit voir et le cadrage"))
                    b.clicked.connect(lambda _c=False, i=i: self.corriger_image(i, "arrivee"))
                    hb.addWidget(b)
                    br = QPushButton(_("Image de la ligne rouge"))
                    br.setToolTip(_("Prend l'image affichée à la ligne rouge dans la timeline (un autre rush, une photo) comme "
                                    "image clef"))
                    br.clicked.connect(lambda _c=False, i=i: self.clef_ligne_rouge(i))
                    hb.addWidget(br)
                    bloc.addLayout(hb)
            g.addLayout(bloc, ligne, 1)
            ligne += 1
        g.setColumnStretch(1, 1)
        g.setRowStretch(ligne, 1)
        self.zone_images.setWidget(w)
        if cible in self._vignettes_plans:
            vg = self._vignettes_plans[cible]
            QTimer.singleShot(0, lambda: self.zone_images.ensureWidgetVisible(vg, 40, 120))

    def _basculer_clef(self, i, on):
        pl = self.seq["plans"][i]
        pl["clef"], pl["sans_fin"] = bool(on), not on
        pl["fichier"], pl["images_ok"] = "", False
        if not on:
            pl["image_fin"] = ""
        if i + 1 < len(self.seq["plans"]):
            self.seq["plans"][i + 1]["fichier"] = ""
        self._remplir_images((i, "arrivee"))

    def clef_ligne_rouge(self, i):
        """L'image affichée à la ligne rouge devient l'image clef du plan i (0.9.87 : des éléments du réel)."""
        p, t = self.ed.projet, self.ed.timeline.position
        c = p.plan_visible(t)
        m = p.media(c["media"]) if c else None
        if not (c and m and os.path.exists(m.get("chemin") or "")):
            self.etat.setText(_("Placez la ligne rouge sur une image d'un rush ou d'une photo, puis recommencez."))
            return
        if m.get("genre") == "image":
            chemin = m["chemin"]
        else:
            from . import images_plan
            src = float(c.get("src_debut") or 0.0) + (t - c["debut"]) * float(c.get("vitesse") or 1.0)
            r = images_plan.extraire(p, c, [src])
            chemin = r[0] if r else ""
        if not chemin:
            self.etat.setText(_("Image illisible à la ligne rouge."))
            return
        pl = self.seq["plans"][i]
        pl.update(image_fin=chemin, clef=True, sans_fin=False, fichier="", images_ok=False)
        if i + 1 < len(self.seq["plans"]):
            self.seq["plans"][i + 1]["fichier"] = ""
        self._remplir_images((i, "arrivee"))
        self.etat.setText(_("✓ Image clef prise à la ligne rouge (réelle, gratuite)."))

    def _precision(self, titre, question, defaut=""):
        if getattr(self, "_test_precision", None) is not None:
            return self._test_precision or defaut, True
        d = QInputDialog(self)                       # 0.9.90 : question à la ligne (jamais plus large que l'écran)
        d.setWindowTitle(titre)
        d.setLabelText(question)
        d.setTextValue(defaut)
        for l in d.findChildren(QLabel):
            l.setWordWrap(True)
        d.resize(560, d.sizeHint().height())
        ok = d.exec() == QDialog.Accepted
        return d.textValue(), ok

    def _garder_fiche(self, k):
        p = self.seq["personnages"][k]
        e = self._element_de(p)
        e["accord"] = bool(p.get("accord"))
        e["images"] = list(p.get("images") or [])
        self.garder_carte(e, p.get("planche", ""))

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

    def corriger_image(self, i, quoi, texte=None):
        if texte is None:
            texte, ok = self._precision(_("Corriger l'image"), _("Ce qui ne va pas, ou ce que vous voulez voir. Le cadrage compte : "
                                                                 "« plan large, on voit tout le véhicule », « plus près des mains », "
                                                                 "« elle n'est plus là ». Environ 0,04 $ :"))
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
                self._remplir_images((i, quoi))
                self.etat.setText(_("Image refaite : regardez-la (entourée en orange)."))
                suivant = i + 1
                if quoi == "arrivee" and suivant < len(self.seq["plans"]) and self.seq["plans"][suivant].get("enchainer", True) \
                        and not self.seq["plans"][suivant].get("fin_reelle") \
                        and not self.seq["plans"][suivant].get("image"):
                    nxt = self.seq["plans"][suivant]       # 0.9.86 : cette arrivée est le départ du plan suivant
                    nxt["fichier"], nxt["images_ok"] = "", False
                    if nxt.get("image_fin") and (getattr(self, "_test_oui", None) is not None or QMessageBox.question(
                            self, _("Assistant de création"),
                            _("Cette image est aussi le départ du plan {n}. Refaire son arrivée pour qu'elle suive (environ "
                              "0,04 $) ?", n=suivant + 1)) == QMessageBox.Yes):
                        QTimer.singleShot(0, lambda: self.corriger_image(suivant, "arrivee", ""))
        self._lancer(travail, _("Nouvelle image du plan {i}", i=i + 1), fin)

    # ------------------------------------------------------------------ 6. vidéo
    def _texte_plan(self, i):
        pl = self.seq["plans"][i]
        if pl.get("fichier") and os.path.exists(pl["fichier"]):
            etat = A.texte_verdict(pl.get("verdict"))
        elif pl.get("erreur"):
            etat = "✕ " + pl["erreur"]
        elif i in self.file or self._plan_en_cours == i or i in self._groupe_en_cours:
            etat = _("en fabrication…") if (self._plan_en_cours == i or i in self._groupe_en_cours) else _("en attente")
        else:
            etat = _("à fabriquer")
        lien = ""
        if pl.get("groupe") and i + 1 < len(self.seq["plans"]) and self.seq["plans"][i + 1].get("groupe") == pl["groupe"]:
            lien = "  ⛓ " + _("d'un seul tenant avec le plan suivant")
        return _("Plan {i} ({d} s) : {a}", i=i + 1, d=pl.get("duree"), a=pl.get("action", "")) + "\n      " + etat + lien

    _plan_en_cours = -1
    _groupe_en_cours = []

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
        moteur_video, niveau = self.seq.get("moteur") or self.moteur.currentData(), self._niveau()
        # 0.9.90 : les plans d'un même moment (jusqu'à la prochaine image clef) se font d'un seul calcul, gestes enchaînés
        groupe = Q.groupe_continu(self.seq, self.file[0], self.file, moteur_video, self.params)
        self.file = [x for x in self.file if x not in groupe]
        i = groupe[0]
        self._plan_en_cours = i
        self._groupe_en_cours = groupe
        self._remplir_video()
        seq = copy.deepcopy(self.seq)

        def travail(t):
            pl = seq["plans"][i]
            if not pl.get("image"):
                depart = Q.depart_prevu(seq, i)
                if depart:
                    pl["image"] = depart                 # tout moteur part de l'image validée
            nom = _("plans {a} à {b}", a=i + 1, b=groupe[-1] + 1) if len(groupe) > 1 else _("plan {i}", i=i + 1)
            fichiers = Q.fabriquer_groupe(seq, groupe, self.params, moteur_video, lambda x: t.avancer(0.85 * x, nom), t.arret_demande)
            out = []
            for k, (j, f) in enumerate(zip(groupe, fichiers)):
                seq["plans"][j]["fichier"] = f
                t.avancer(0.86 + 0.13 * k / len(groupe), _("relecture du plan {i}", i=j + 1))
                try:
                    verdict = A.verifier(self.params, seq, j, niveau)
                except Exception:      # noqa: BLE001 : la relecture est un plus, jamais un blocage
                    verdict = None
                out.append((j, f, verdict, seq["plans"][j].get("groupe", "")))
            return out

        def fin(r, e):
            self._plan_en_cours = -1
            self._groupe_en_cours = []
            if e or not r:
                self.seq["plans"][i]["erreur"] = texte_erreur(e)[:200] if e else _("rien n'a été fabriqué")
                self.file = []
                self._remplir_video()
                return
            for j, f, verdict, g in r:
                pl = self.seq["plans"][j]
                pl["fichier"], pl["verdict"] = f, verdict
                if g:
                    pl["groupe"] = g
                else:
                    pl.pop("groupe", None)
                A.depenser(self.seq, _("Plan {i}", i=j + 1), A.prix_plan(self.seq, j, moteur_video, self.params))
                if verdict is not None and self._cloud():
                    A.depenser(self.seq, _("Relecture"), A.PRIX_LECTURE)
            Q.enregistrer(self.seq)
            self._remplir_video()
            self.l_plans.setCurrentRow(i)
            self._suivant_de_la_file()
        titre = _("Fabrication des plans {a} à {b} d'un seul tenant", a=i + 1, b=groupe[-1] + 1) if len(groupe) > 1 else \
            _("Fabrication du plan {i} sur {n}", i=i + 1, n=len(self.seq["plans"]))
        self._lancer(travail, titre, fin)

    def refaire_plan(self):
        i = self.l_plans.currentRow()
        if i < 0 or self._en_calcul():
            return
        a_refaire = Q.plans_du_groupe_apres(self.seq, i)      # 0.9.90 : ceux du même calcul partent de sa fin
        prix = sum(A.prix_plan(self.seq, j, self.seq.get("moteur") or self.moteur.currentData(), self.params) for j in a_refaire)
        aussi = (" " + _("Les plans {l}, faits d'un seul tenant avec lui, sont refaits aussi (ils partent de sa fin).",
                         l=", ".join(str(j + 1) for j in a_refaire[1:]))) if len(a_refaire) > 1 else ""
        texte, ok = self._precision(_("Refaire le plan {i}", i=i + 1), _(
            "Environ {p}. Ce qu'il faut changer dans l'image d'arrivée (facultatif ; vide = même images, nouvel essai) :",
            p=A.argent(prix)) + aussi)
        if not ok:
            return
        self.apercu.arreter()
        for j in a_refaire:
            self.seq["plans"][j]["fichier"], self.seq["plans"][j]["verdict"] = "", None
            self.seq["plans"][j].pop("groupe", None)
        pl = self.seq["plans"][i]
        if texte.strip() and A.images_par(self.seq, self.params) != "aucune":
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
            c = CarteElement(e, I.sources(e["type"]), self._options_musique, I.manque, self.ameliorer, COULEURS[k], None, titres[e["type"]],
                             self.garder_carte if e["type"] in ("style", "voix") else None)
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
        if source == "bibliotheque":
            return self._options_bibliotheque(carte)
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
            from . import bibliotheque_creations as B
            hr = QHBoxLayout()
            hr.addWidget(QLabel(_("C'est une voix de")))
            cr = QComboBox()
            cr.addItem(_("Au choix"), "")
            for k, lib in B.ROLES_VOIX:
                cr.addItem(lib, k)
            cr.setCurrentIndex(max(0, cr.findData(e.get("role") or "")))
            cr.currentIndexChanged.connect(lambda _i: e.update(role=cr.currentData()))
            hr.addWidget(cr)
            hr.addStretch(1)
            v.addLayout(hr)
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
        self.b_garder_m = QPushButton(_("☆ Garder dans ma bibliothèque"))
        self.b_garder_m.clicked.connect(self._garder_musique)
        h.addWidget(self.b_garder_m)
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
        self.b_garder_m.setEnabled(not calc and fait)

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

    def _garder_musique(self):
        from . import bibliotheque_creations as B
        nom, ok = self._precision(_("Garder dans ma bibliothèque"), _("Nom du morceau :"), self.musique.get("titre") or _("Musique"))
        if not ok or not nom.strip():
            return
        x = B.garder(self.params, "musique", nom.strip(), I.resume(self.musique), {"morceau": self.resultat},
                     {"assistant": I.etat_musique(self.musique)})
        self.etat.setText(_("✓ « {n} » est dans votre bibliothèque ({g}).", n=x["nom"], g=B.GENRES["musique"][0]))

    def _enregistrer_musique(self):
        from .dialogues_creatif import enregistrer_copie
        c = enregistrer_copie(self, self.resultat, self.params)
        if c:
            self.etat.setText(_("✓ Copie enregistrée : {f}", f=c))

    # ================================================================== INTRO ET LOGO (0.9.82)
    def analyser_intro(self):
        from . import assistant_intro as AI
        texte = self.c_histoire.texte()
        if len(texte) < 4:
            self.etat.setText(_("Dites d'abord quelle intro vous voulez."))
            return
        niveau = self._niveau()

        def travail(_t):
            try:
                return AI.analyser_intro(self.params, texte, niveau), None
            except Exception as e:      # noqa: BLE001 : sans IA, des cartes pré-remplies par les mots
                return AI.analyse_intro_simple(texte), e

        def fin(r, e):
            if e or not r:
                return
            etat, souci = r
            etat["idee"] = texte
            if getattr(self, "intro", None) and self.intro.get("budget"):
                etat["budget"] = self.intro["budget"]
            self.intro, self.intro_fichier = etat, ""
            if self._cloud() and not souci:
                A.depenser(self.intro, _("Lecture de l'idée"), A.PRIX_LECTURE)
            if self._cloud() and not A.budget(self.intro).get("prevu"):
                A.prevoir(self.intro, 6 * A.PRIX_LECTURE + 2 * A.PRIX_IMAGE)
            self._remplir_icartes()
            self.aller(P_I_ELEM)
            self.etat.setText(_("L'IA n'a pas répondu ({e}) : les cartes sont pré-remplies d'après vos mots ; complétez-les.",
                                e=texte_erreur(souci)[:160]) if souci else
                              (etat.get("remarques") or _("Pour chaque carte, choisissez d'où elle vient, puis continuez.")))
        self._lancer(travail, _("L'assistant lit votre idée"), fin)

    def _dire_intro(self, texte):
        """Une demande en clair : relue avec l'idée de départ ; ce qui a été choisi (fichiers, logos, jingle) est gardé."""
        from . import assistant_intro as AI
        self._lire_intro()
        ancien, niveau = self.intro, self._niveau()
        idee = (ancien.get("idee", "") + ". " + _("Correction : {c}", c=texte)).strip()

        def fin(r, e):
            if e or not r:
                return
            neuf = r
            for vieux, el in zip(ancien["elements"], neuf["elements"]):
                if el.get("source") == vieux.get("source"):
                    for k in ("chemin", "biblio", "choix", "accent", "couleur"):
                        if vieux.get(k) and not el.get(k):
                            el[k] = vieux[k]
            for k in ("budget", "idee"):
                if ancien.get(k):
                    neuf[k] = ancien[k]
            self.intro, self.intro_fichier = neuf, ""
            if self._cloud():
                A.depenser(self.intro, _("Correction en clair"), A.PRIX_LECTURE)
            self.libre.clear()
            self._remplir_icartes()
            self._remplir_texte_intro()
            if self.pages.currentIndex() == P_I_CREER:
                self.aller(P_I_TEXTE)
            self.etat.setText("✓ " + (neuf.get("remarques") or _("C'est modifié : vérifiez, puis continuez.")))
        self._lancer(lambda _t: AI.analyser_intro(self.params, idee, niveau), _("L'assistant applique votre demande"), fin)

    # ------------------------------------------------------------------ 2. ce qu'il faut (logo, style, fond, son)
    def _page_i_elements(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Ce qu'il faut pour cette intro : vérifiez chaque carte")))
        v.addWidget(self._aide(_("Le logo, l'allure de l'animation, le fond et le son. Chaque carte dit d'où ils viennent, avec toutes les "
                                 "possibilités ; le texte et la durée se règlent à l'étape suivante, avec l'aperçu animé.")))
        self.w_icartes = QWidget()
        self.v_icartes = QVBoxLayout(self.w_icartes)
        v.addWidget(_defile(self.w_icartes), 1)
        self.icartes = []
        return w

    def _remplir_icartes(self):
        vider(self.v_icartes)
        self.icartes = []
        titres = {"logo": _("Logo"), "style_intro": _("Style"), "fond": _("Fond"), "son": _("Son")}
        for k, e in enumerate(self.intro["elements"]):
            e.setdefault("genre", {"style_intro": "style", "son": "partie", "logo": "logo", "fond": "fond"}.get(e["type"], "idee"))
            c = CarteElement(e, I.sources(e["type"]), self._options_intro, I.manque, self.ameliorer, COULEURS[k], None, titres[e["type"]],
                             self.garder_carte)
            c.change.connect(self._maj)
            self.icartes.append(c)
            self.v_icartes.addWidget(c)
        self.v_icartes.addStretch(1)

    def _options_intro(self, carte, source):
        from . import bruitages as BR
        from . import intros as IN
        e, t = carte.e, carte.e["type"]
        if source == "bibliotheque":
            return self._options_bibliotheque(carte)
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 0, 0, 0)
        h = QHBoxLayout()
        if t == "logo" and source == "atelier":
            from . import logo as LG
            logos = sorted(LG.liste(), key=lambda x: _alpha(x.get("nom", "")))
            cb = QComboBox()
            cb.addItem(_("Choisir…") if logos else _("Aucun logo encore : ouvrez l'Atelier de logo"), "")
            for x in logos:
                cb.addItem(x.get("nom", ""), x.get("nom", ""))

            def choisir(_i):
                x = next((y for y in logos if y.get("nom") == cb.currentData()), None)
                if x is not None:
                    e["chemin"] = LG.enregistrer(x)
                    carte.rafraichir()
            if e.get("chemin"):
                cb.setCurrentIndex(max(0, cb.findText(os.path.splitext(os.path.basename(e["chemin"]))[0])))
            cb.currentIndexChanged.connect(choisir)
            h.addWidget(cb, 1)
            b = QPushButton(_("Atelier de logo…"))
            b.clicked.connect(lambda: self.ed.window().atelier_logo())
            h.addWidget(b)
        elif source in ("fichier_image", "fichier"):
            b = QPushButton(_("Choisir le fichier…"))
            b.clicked.connect(lambda: self._fichier_intro(carte, source))
            h.addWidget(b)
            h.addWidget(QLabel(os.path.basename(e.get("chemin") or "") or _("aucun")), 1)
        elif source == "creer_ia":
            b = QPushButton(_("Le faire dessiner (environ 0,04 $)") if not e.get("chemin") else _("Le redessiner (environ 0,04 $)"))
            b.clicked.connect(lambda: self._dessiner_intro(carte))
            h.addWidget(b)
            h.addStretch(1)
        elif t == "style_intro" and source in ("liste", "decrire"):
            cb = QComboBox()
            for k, (fam, lib, expl) in sorted(IN.MODELES.items(), key=lambda x: _alpha(x[1][1])):
                cb.addItem(f"{lib} ({IN.FAMILLES[fam]})", k)
                cb.setItemData(cb.count() - 1, expl, Qt.ToolTipRole)
            cb.setCurrentIndex(max(0, cb.findData(e.get("choix") or "masque")))
            cb.currentIndexChanged.connect(lambda _i: (e.update(choix=cb.currentData()), carte.maj()))
            h.addWidget(cb, 1)
            if source == "decrire":
                b = QPushButton(_("Choisir d'après la description"))
                b.clicked.connect(lambda: self._style_d_apres_description(carte))
                h.addWidget(b)
            self._bouton_couleur(h, e, "accent", _("Couleur d'accent…"))
        elif t == "fond" and source == "uni":
            self._bouton_couleur(h, e, "couleur", _("Couleur du fond…"))
            h.addStretch(1)
        elif t == "son" and source == "bruitage":
            cb = QComboBox()
            for k, (lib, expl, *_r) in sorted(BR.SONS.items(), key=lambda x: _alpha(x[1][0])):
                cb.addItem(lib, k)
                cb.setItemData(cb.count() - 1, expl, Qt.ToolTipRole)
            cb.setCurrentIndex(max(0, cb.findData(e.get("choix") or "whoosh")))
            e["choix"] = cb.currentData()
            cb.currentIndexChanged.connect(lambda _i: (e.update(choix=cb.currentData()), carte.maj()))
            h.addWidget(cb, 1)
        elif t == "son" and source == "jingle":
            b = QPushButton(_("Créer le jingle (sur ce poste, gratuit)") if not e.get("chemin") else _("Recréer le jingle"))
            b.clicked.connect(lambda: self._creer_jingle(carte))
            h.addWidget(b)
            h.addStretch(1)
        else:
            return None
        v.addLayout(h)
        if t in ("logo", "fond") and e.get("chemin") and os.path.exists(e["chemin"]) and source in ("atelier", "fichier_image", "creer_ia"):
            v.addWidget(Vignette(e["chemin"], 160))
        return w

    def _bouton_couleur(self, h, e, cle, libelle):
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog
        b = QPushButton(libelle)
        if e.get(cle):
            b.setStyleSheet(f"border-left:14px solid {e[cle]}")

        def choisir():
            c = QColorDialog.getColor(QColor(e.get(cle) or "#3a7bd5"), self, libelle)
            if c.isValid():
                e[cle] = c.name()
                b.setStyleSheet(f"border-left:14px solid {e[cle]}")
        b.clicked.connect(choisir)
        h.addWidget(b)

    def _fichier_intro(self, carte, source):
        from .widgets import ouvrir_fichier
        if source == "fichier":
            ch = ouvrir_fichier(self, _("Son"), SONS, "musique", self.params)
        else:
            ch = ouvrir_fichier(self, _("Image"), _("Images") + " (*.png *.jpg *.jpeg *.webp)", "image", self.params)
        if ch:
            carte.e["chemin"] = ch
            carte.rafraichir()

    def _dessiner_intro(self, carte):
        from . import assistant_intro as AI
        e = carte.e
        if len((e.get("description") or "").strip()) < 4:
            self.etat.setText(_("Décrivez-le d'abord dans la carte."))
            return
        if getattr(self, "_test_oui", None) is None and QMessageBox.question(
                self, _("Le faire dessiner"), _("Gemini le dessine d'après la description, environ 0,04 $ sur votre clef. Continuer ?")) \
                != QMessageBox.Yes:
            return
        quoi = "logo" if e["type"] == "logo" else "fond"
        from .creations import dossier
        sortie = os.path.join(dossier(), f"intro_{quoi}_{int(time.time())}.png")
        etat, params = copy.deepcopy(self.intro), self.params

        def fin(r, err):
            if err or not r:
                return
            A.depenser(self.intro, _("Image dessinée"), A.PRIX_IMAGE)
            e["chemin"] = r
            carte.rafraichir()
        self._lancer(lambda _t: AI.image_ia(params, etat, quoi, sortie), _("Gemini dessine"), fin)

    def _style_d_apres_description(self, carte):
        from . import assistant_intro as AI
        e, niveau = carte.e, self._niveau()
        texte = (e.get("description") or "") + " — " + self.c_histoire.texte()

        def fin(r, err):
            if err or not r:
                return
            st = r["elements"][1]
            e["choix"] = st.get("choix") or e.get("choix")
            if st.get("accent"):
                e["accent"] = st["accent"]
            carte.rafraichir()
        self._lancer(lambda _t: AI.analyser_intro(self.params, texte, niveau), _("L'IA choisit le modèle"), fin)

    def _creer_jingle(self, carte):
        from . import assistant_intro as AI
        from . import traduction_recherche as TR
        e = carte.e
        self._lire_intro()
        etat, params = copy.deepcopy(self.intro), self.params
        from .creations import dossier
        sortie = os.path.join(dossier(), f"jingle_{int(time.time())}.mp3")

        def traduire(x):
            return TR.phrase_en_anglais(x)[0]

        def fin(r, err):
            if err or not r:
                return
            e["chemin"] = r
            carte.rafraichir()
            self.etat.setText(_("✓ Jingle créé : il s'entendra dans l'aperçu de l'intro."))
        self._lancer(lambda t: AI.creer_jingle(etat, sortie, params, t.avancer, t.arret_demande, traduire), _("Création du jingle sur ce poste"),
                     fin)

    # ------------------------------------------------------------------ 3. le texte et le rendu (aperçu animé)
    def _page_i_texte(self):
        from PySide6.QtCore import QTimer
        w = QWidget()
        h = QHBoxLayout(w)
        v = QVBoxLayout()
        v.addWidget(self._titre(_("Le texte et le rendu")))
        v.addWidget(QLabel(_("Titre")))
        self.c_titre = ChampAmeliorable("", "titre", 1, self.ameliorer, _("ex. : Cuisine du marché"))
        v.addWidget(self.c_titre)
        v.addWidget(QLabel(_("Sous-titre (facultatif)")))
        self.c_sous = ChampAmeliorable("", "titre", 1, self.ameliorer, _("ex. : épisode 3"))
        v.addWidget(self.c_sous)
        hd = QHBoxLayout()
        hd.addWidget(QLabel(_("Durée (s)")))
        self.i_duree = QDoubleSpinBox()
        self.i_duree.setRange(2, 8)
        self.i_duree.setSingleStep(0.5)
        self.i_duree.setDecimals(1)
        hd.addWidget(self.i_duree)
        hd.addStretch(1)
        v.addLayout(hd)
        v.addWidget(QLabel(_("Où la poser ?")))
        self.i_place = QComboBox()
        for k, lib in PLACEMENTS:
            self.i_place.addItem(lib, k)
        v.addWidget(self.i_place)
        v.addStretch(1)
        h.addLayout(v, 1)
        va = QVBoxLayout()
        va.addWidget(QLabel(_("Aperçu (sans le son) :")))
        self.i_apercu = QLabel()
        self.i_apercu.setFixedSize(400, 225)
        self.i_apercu.setStyleSheet("background:#000;border-radius:6px")
        va.addWidget(self.i_apercu)
        va.addStretch(1)
        h.addLayout(va)
        for c in (self.c_titre, self.c_sous):
            c.change.connect(self._apercu_change)
        self.i_duree.valueChanged.connect(lambda _x: self._apercu_change())
        self._minuterie_intro = QTimer(self)
        self._minuterie_intro.timeout.connect(self._image_suivante)
        self._ctx_intro, self._t_intro = None, 0.0
        return w

    def _remplir_texte_intro(self):
        m = self.intro
        self._remplissage = True                          # remplir les champs ne doit pas relire les autres, encore vides
        try:
            self.c_titre.mettre(m.get("titre", ""))
            self.c_sous.mettre(m.get("sous_titre", ""))
            self.i_duree.setValue(float(m.get("duree", 3.0)))
            voulu = m.get("placement") if m.get("placement") in ("debut", "fin", "ligne", "medias") else "debut"
            self.i_place.setCurrentIndex(max(0, self.i_place.findData(voulu)))
        finally:
            self._remplissage = False
        self._apercu_change()
        self._minuterie_intro.start(66)

    def _lire_intro(self):
        m = getattr(self, "intro", None)
        if m is None or not hasattr(self, "c_titre") or getattr(self, "_remplissage", False):
            return
        if self.c_titre.texte() or self.pages.currentIndex() == P_I_TEXTE:
            m["titre"] = self.c_titre.texte()
            m["sous_titre"] = self.c_sous.texte()
            m["duree"] = float(self.i_duree.value())
            m["placement"] = self.i_place.currentData()

    def _image_film(self):
        """La première image du film (pour le fond « images du film »), une fois."""
        if getattr(self, "_film_img", None) is not None:
            return self._film_img or None
        self._film_img = ""
        p = self.ed.projet
        c = next(iter(sorted(p.clips_piste("video"), key=lambda c: c["debut"])), None)
        m = p.media(c["media"]) if c else None
        if m and os.path.exists(m.get("chemin") or ""):
            if m.get("genre") == "image":
                self._film_img = m["chemin"]
            else:
                from . import prolonger
                sortie = os.path.join(Q.dossier(self.seq), "film_debut.png")
                try:
                    self._film_img = prolonger._image(m["chemin"], float(c.get("src_debut", 0)) + 0.5, sortie)
                except Exception:      # noqa: BLE001
                    self._film_img = ""
        return self._film_img or None

    def _apercu_change(self):
        from . import assistant_intro as AI
        if getattr(self, "intro", None) is None:
            return
        self._lire_intro()
        try:
            self._ctx_intro = AI.contexte(self.intro, 400, 225, self._image_film())
        except Exception:      # noqa: BLE001 : l'aperçu ne doit jamais bloquer
            self._ctx_intro = None
        self._t_intro = 0.0

    def _image_suivante(self):
        from PySide6.QtGui import QPixmap
        from . import intros as IN
        if self.pages.currentIndex() != P_I_TEXTE or not self.isVisible() or self._ctx_intro is None:
            return
        d = float(self.intro.get("duree", 3.0))
        self._t_intro = (self._t_intro + 1 / 15) % (d + 0.6)
        self.i_apercu.setPixmap(QPixmap.fromImage(IN.image(self._ctx_intro, min(self._t_intro, d))))

    # ------------------------------------------------------------------ 4. l'intro : fabrication, écoute, pose
    def _page_i_creer(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("L'intro : regardez-la, avec son son, avant de la poser")))
        self.l_resume_i = self._aide("")
        v.addWidget(self.l_resume_i)
        from .dialogues_creatif import ApercuCreation
        self.apercu_i = ApercuCreation(self)
        v.addWidget(self.apercu_i, 1)
        h = QHBoxLayout()
        self.b_fab_intro = QPushButton(_("Refabriquer"))
        self.b_fab_intro.clicked.connect(self.fabriquer_intro)
        h.addWidget(self.b_fab_intro)
        self.b_garder_style = QPushButton(_("☆ Garder ce style d'intro"))
        self.b_garder_style.setToolTip(_("Le modèle, les couleurs et le fond, nommés, pour refaire la même allure plus tard"))
        self.b_garder_style.clicked.connect(lambda: self.garder_carte(self.intro["elements"][1]))
        h.addWidget(self.b_garder_style)
        h.addStretch(1)
        v.addLayout(h)
        return w

    def fabriquer_intro(self):
        from . import assistant_intro as AI
        if self._en_calcul():
            return
        self._lire_intro()
        etat = copy.deepcopy(self.intro)
        L, H = self.ed.projet.taille
        cadence = self.ed.projet.cadence
        film = self._image_film()
        dossier = os.path.join(Q.dossier(self.seq), "intro")
        lieu = dict(PLACEMENTS).get(etat.get("placement"), "")
        self.l_resume_i.setText(_("« {t} » — {m}, {d:.1f} s ; pose : {p}.", t=etat.get("titre") or _("Votre titre"),
                                  m=etat["elements"][1].get("choix"), d=float(etat["duree"]), p=lieu))
        try:
            self.apercu_i.arreter()
        except RuntimeError:
            pass

        def fin(r, err):
            if err or not r:
                return
            self.intro_fichier = r
            self.apercu_i.charger(r, video=True)
            self.etat.setText(_("✓ Intro fabriquée : regardez-la, puis « Poser l'intro »."))
        self._lancer(lambda t: AI.fabriquer(etat, dossier, L, H, cadence, film, t.avancer), _("Fabrication de l'intro"), fin)

    def poser_intro(self):
        if not getattr(self, "intro_fichier", ""):
            return
        try:
            self.apercu_i.arreter()
        except RuntimeError:
            pass
        place = self.intro.get("placement", "debut")
        ed, f = self.ed, self.intro_fichier
        if place == "ligne":
            from . import prolonger
            ed.projet.marquer()
            prolonger.inserer(ed.projet, f, ed.timeline.position, nom=self.intro.get("titre") or _("Intro"))
            ed.biblio.remplir(ed.projet)
            ed.rafraichir()
        else:
            ed.window()._logo_pret(ed, f, place if place in ("debut", "fin") else "", None)
        self.etat.setText(_("✓ Intro posée ({p}) ; Ctrl+Z pour revenir.", p=dict(PLACEMENTS).get(place, "")))

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

    def reprendre_sequence(self, seq):
        """Retour du réglage manuel : la séquence réglée à la main reprend sa place dans l'assistant."""
        import copy as _c
        self.genre = "video"
        self.seq = _c.deepcopy(seq)
        self._lue_avec = (self._suite(), self._niveau(), self._raccord())
        if self.seq.get("histoire"):
            self.c_histoire.mettre(self.seq["histoire"])
        self._remplir_cartes()
        self._remplir_plans()
        self.aller(P_PLANS)
        self._maj_prix()
        self.show()
        self.raise_()
        self.etat.setText(_("De retour dans l'assistant, avec vos réglages."))

    def mode_manuel(self):
        """Ce qui est préparé, dans la fenêtre habituelle : la Séquence IA (vidéo), la Fabrique musique ou la Fabrique (intro),
        pré-remplie."""
        if self.genre == "intro" and getattr(self, "intro", None) is not None:
            self._lire_intro()
            from . import assistant_intro as AI
            self.hide()
            self.ed.window().fabrique(image=AI.logo_chemin(self.intro), texte=self.intro.get("titre") or None, onglet=0)
            return
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
        for a in ("apercu", "apercu_m", "apercu_i"):
            try:
                getattr(self, a).arreter()
            except (RuntimeError, AttributeError):
                pass
        try:
            self._minuterie_intro.stop()
        except (RuntimeError, AttributeError):
            pass
        super().done(r)
