"""Fenêtre de l'assistant de création (0.9.79) : on est guidé, une question par écran, et l'on peut écrire librement à tout
moment. Voir assistant_creation.py pour ce que l'assistant sait faire ; le mode manuel (Séquence IA) reste à un clic."""
import copy
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QHeaderView, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton,
                               QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import assistant_creation as A
from . import sequence_ia as Q
from .langue import _
from .taches import Tache, texte_erreur
from .widgets import garder_calcul, suivre_en_fond

ETAPES = (_("1. Quoi"), _("2. L'histoire"), _("3. Qui et quoi"), _("4. Les plans"), _("5. Les images"), _("6. La vidéo"))
GENRES = (("personne_image", _("Personne de l'image")), ("personne", _("Personne inventée")),
          ("objet_image", _("Objet de l'image")), ("objet", _("Objet inventé")))


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


class DialogueAssistant(QDialog):
    def __init__(self, ed, clip=None):
        super().__init__(ed)
        self.ed, self.params, self.clip = ed, ed.params, clip
        self.seq = Q.nouvelle(ed.projet.format)
        self.image, self.tache, self.taches, self.file = "", None, [], []
        self.setWindowTitle(_("Assistant de création : guidé pas à pas"))
        self.resize(980, 700)
        v = QVBoxLayout(self)
        self.fil = QLabel("")
        self.fil.setWordWrap(True)
        v.addWidget(self.fil)
        self.pages = QStackedWidget()
        for fabrique in (self._page_quoi, self._page_histoire, self._page_qui, self._page_plans, self._page_images, self._page_video):
            self.pages.addWidget(fabrique())
        v.addWidget(self.pages, 1)
        # --- toujours là : écrire librement, budget, état, navigation
        hl = QHBoxLayout()
        self.libre = QLineEdit()
        self.libre.setPlaceholderText(_("Ou dites-le en clair : « le chauffeur plus âgé », « un plan de plus où elles saluent »…"))
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
        self.b_manuel.setToolTip(_("Ouvre cette histoire dans la Séquence IA (mode manuel) : tout y est réglable"))
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
        self.aller(0)

    # ------------------------------------------------------------------ pages
    def _titre(self, texte):
        lb = QLabel(texte)
        lb.setWordWrap(True)
        lb.setStyleSheet("font-size:15px;font-weight:600")
        return lb

    def _aide(self, texte):
        lb = QLabel(texte)
        lb.setWordWrap(True)
        lb.setStyleSheet("color:#9aa4b2")
        return lb

    def _page_quoi(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Que voulez-vous faire ?")))
        self.r_suite = QRadioButton(_("Continuer ce rush : la suite part de sa dernière image, avec les mêmes personnes"))
        self.r_scene = QRadioButton(_("Créer une nouvelle scène en plusieurs plans, à partir d'une histoire"))
        v.addWidget(self.r_suite)
        self.l_rush = self._aide("")
        v.addWidget(self.l_rush)
        v.addWidget(self.r_scene)
        v.addWidget(self._aide(_("Vous racontez, l'assistant pose les questions utiles, prépare les personnages et les plans, vous montre "
                                 "les images avant la vidéo, puis relit chaque plan fabriqué. Vous validez à chaque étape ; le budget "
                                 "prévu et dépensé reste affiché en bas.")))
        v.addSpacing(8)
        v.addWidget(self._titre(_("Qui vous assiste ?")))
        self.niveau = QComboBox()
        for k, lib in A.niveaux(self.params):
            self.niveau.addItem(lib, k)
        voulu = self.params.get("musique_ia_ecrire")
        self.niveau.setCurrentIndex(max(0, self.niveau.findData(voulu)) if voulu else 0)
        v.addWidget(self.niveau)
        self.l_manques = QLabel("")
        self.l_manques.setWordWrap(True)
        self.l_manques.setStyleSheet("color:#c98a00")
        v.addWidget(self.l_manques)
        v.addSpacing(8)
        v.addWidget(self._aide(_("Le mode assisté arrive ensuite pour l'intro, le logo, la musique et la chanson ; en attendant, ces "
                                 "boutons ouvrent leurs fenêtres habituelles :")))
        h = QHBoxLayout()
        for lib, fn in ((_("Intro ou logo animé…"), lambda: self.ed.window().fabrique(onglet=0)),
                        (_("Musique ou chanson…"), lambda: self.ed.fabrique_musique())):
            b = QPushButton(lib)
            b.clicked.connect(fn)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        v.addStretch(1)
        return w

    def _page_histoire(self):
        w = QWidget()
        h = QHBoxLayout(w)
        self.v_depart = QVBoxLayout()
        h.addLayout(self.v_depart)
        v = QVBoxLayout()
        self.t_histoire = self._titre("")
        v.addWidget(self.t_histoire)
        v.addWidget(self._aide(_("Ecrivez tout d'un trait, comme vous le raconteriez : qui fait quoi, où l'on va, qui apparaît. "
                                 "L'assistant découpera lui-même en plans.")))
        self.histoire = QPlainTextEdit()
        self.histoire.setPlaceholderText(_("ex. : Les deux femmes descendent les marches puis vont vers une limousine noire. Un chauffeur "
                                           "leur ouvre la portière, elles montent, et la limousine s'éloigne dans la rue éclairée."))
        v.addWidget(self.histoire, 1)
        h.addLayout(v, 1)
        return w

    def _page_qui(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Qui et quoi voit-on ? Vérifiez ce que l'assistant a compris")))
        v.addWidget(self._aide(_("Une ligne par personne (jamais deux personnes sur une ligne) et par objet important (véhicule…). Corrigez "
                                 "le nom et la description : c'est elle qui garde chacun identique d'un plan à l'autre. « Style » : une "
                                 "allure « à la manière de » (jamais un visage copié).")))
        self.t_qui = QTableWidget(0, 4)
        self.t_qui.setHorizontalHeaderLabels([_("Nom"), _("Qui ou quoi"), _("Description"), _("Style")])
        self._table(self.t_qui, (0, 1, 3), 2)
        v.addWidget(self.t_qui, 1)
        h = QHBoxLayout()
        for lib, fn in ((_("Ajouter"), self._ajouter_qui), (_("Retirer"), lambda: self._retirer(self.t_qui)),
                        (_("Style « à la manière de »…"), self._style)):
            b = QPushButton(lib)
            b.clicked.connect(fn)
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        self.accord = QCheckBox(_("Les personnes de l'image sont d'accord pour être animées par l'IA (ou c'est moi)"))
        v.addWidget(self.accord)
        return w

    def _page_plans(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(self._titre(_("Voici les plans : une seule action simple par plan")))
        v.addWidget(self._aide(_("Corrigez le texte, la durée, ou qui apparaît (noms séparés par une virgule ; vide = tout le monde). Un "
                                 "plan à deux actions est coupé en deux tout seul.")))
        self.t_plans = QTableWidget(0, 3)
        self.t_plans.setHorizontalHeaderLabels([_("Ce qu'on voit"), _("Qui"), _("Durée (s)")])
        self._table(self.t_plans, (1, 2), 0)
        v.addWidget(self.t_plans, 1)
        h = QHBoxLayout()
        for lib, fn in ((_("Ajouter un plan"), self._ajouter_plan), (_("Retirer"), lambda: self._retirer(self.t_plans))):
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

    # ------------------------------------------------------------------ départ
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
                            _("Pour continuer un rush : fermez, cliquez le plan dans la timeline, puis rouvrez l'assistant "
                              "(clic droit sur le plan › « Continuer ce plan avec l'assistant IA… »)."))
        self.l_manques.setText(" ".join(A.manques(self.params)))

    def _suite(self):
        return self.r_suite.isChecked() and bool(self.image)

    # ------------------------------------------------------------------ navigation
    def aller(self, k):
        self.pages.setCurrentIndex(k)
        self.fil.setText("   ›   ".join(f"<b>{e}</b>" if i == k else e for i, e in enumerate(ETAPES)))
        self.b_suiv.setText({0: _("Commencer ›"), 1: _("Analyser mon histoire ›"), 2: _("C'est bien eux ›"),
                             3: _("Préparer les images ›"), 4: _("Tout me convient : fabriquer la vidéo ›"),
                             5: _("Poser dans le film")}[k])
        if k == 1:
            suite = self._suite()
            self.t_histoire.setText(_("Que se passe-t-il ensuite ?") if suite else _("Racontez la scène"))
            while self.v_depart.count():
                x = self.v_depart.takeAt(0).widget()
                if x:
                    x.deleteLater()
            if suite:
                self.v_depart.addWidget(QLabel(_("La suite part de cette image :")))
                vg = Vignette(self.image, 260)
                vg.clic.connect(lambda ch: agrandir(self, ch))
                self.v_depart.addWidget(vg)
                self.v_depart.addStretch(1)
        self._maj()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _maj(self):
        calc = self._en_calcul()
        k = self.pages.currentIndex()
        self.b_prec.setEnabled(k > 0 and not calc)
        self.b_suiv.setEnabled(not calc and (k < 5 or any(pl.get("fichier") and os.path.exists(pl["fichier"]) for pl in self.seq["plans"])))
        self.b_dire.setEnabled(not calc)
        self.b_reduire.setVisible(calc)
        self.b_manuel.setEnabled(not calc and k >= 2)
        if k == 5:
            self.b_refaire.setEnabled(not calc and self.l_plans.currentRow() >= 0)
            self.b_reprendre.setVisible(not calc and any(not pl.get("fichier") for pl in self.seq["plans"]))
        b = A.budget(self.seq)
        if b.get("prevu") or b.get("depense"):
            rouge = A.depasse(self.seq)
            dep = A.argent(b.get("depense", 0))
            self.l_budget.setText(_("Budget prévu : <b>{p}</b>   ·   dépensé : {d}", p=A.argent(b.get("prevu", 0)),
                                    d=f"<b style='color:#e5484d'>{dep}</b> ⚠ " + _("dépassé") if rouge else f"<b>{dep}</b>"))
        else:
            self.l_budget.setText("")

    def precedent(self):
        k = self.pages.currentIndex()
        if k in (2, 3):
            self._lire_tables()
        self.aller(max(0, k - 1))

    def suivant(self):
        k = self.pages.currentIndex()
        if k == 0:
            self.params["musique_ia_ecrire"] = self.niveau.currentData()
            self.aller(1)
        elif k == 1:
            self.analyser()
        elif k == 2:
            self._lire_tables()
            if self._avec_personnes_reelles() and not self.accord.isChecked():
                self.etat.setText(_("Cochez la case : les personnes de l'image doivent être d'accord pour être animées par l'IA."))
                return
            for p in self.seq["personnages"]:
                if p.get("sur_image") and p.get("genre") != "objet":
                    p["accord"] = True
            self._remplir_plans()
            self.aller(3)
            self._maj_prix()
        elif k == 3:
            self.preparer()
        elif k == 4:
            for pl in self.seq["plans"]:
                pl["images_ok"] = True
            Q.enregistrer(self.seq)
            self._remplir_video()
            self.aller(5)
            self.fabriquer()
        else:
            self.poser()

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

    def _cloud(self):
        return self.niveau.currentData() != "locale"

    # ------------------------------------------------------------------ 2. analyse de l'histoire
    def analyser(self):
        histoire = self.histoire.toPlainText().strip()
        if len(histoire) < 8:
            self.etat.setText(_("Racontez d'abord ce qui doit se passer."))
            return
        self.seq["histoire"] = histoire
        image = self.image if self._suite() else None
        niveau = self.niveau.currentData()

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
            self._remplir_qui()
            self.aller(2)
            self.etat.setText(_("L'IA n'a pas répondu ({e}) : l'histoire est découpée simplement, ajoutez les personnages à la main.",
                                e=texte_erreur(souci)[:160]) if souci else
                              (analyse.get("remarques") or _("Vérifiez les personnages et les objets, puis continuez.")))
        self._lancer(travail, _("L'assistant lit votre histoire et regarde l'image") if image else _("L'assistant lit votre histoire"), fin)

    # ------------------------------------------------------------------ tables
    def _combo_genre(self, p):
        c = QComboBox()
        for k, lib in GENRES:
            c.addItem(lib, k)
        k = ("objet" if p.get("genre") == "objet" else "personne") + ("_image" if p.get("sur_image") else "")
        c.setCurrentIndex(max(0, c.findData(k)))
        c.model().item(0).setEnabled(bool(self._suite()))
        c.model().item(2).setEnabled(bool(self._suite()))
        c.currentIndexChanged.connect(lambda _i: self._maj_accord())
        return c

    def _remplir_qui(self):
        t = self.t_qui
        t.blockSignals(True)
        t.setRowCount(0)
        for p in self.seq["personnages"]:
            self._ligne_qui(p)
        t.blockSignals(False)
        t.resizeRowsToContents()
        self._maj_accord()

    def _ligne_qui(self, p):
        t = self.t_qui
        r = t.rowCount()
        t.insertRow(r)
        t.setItem(r, 0, QTableWidgetItem(p.get("nom", "")))
        t.setCellWidget(r, 1, self._combo_genre(p))
        t.setItem(r, 2, QTableWidgetItem(p.get("description", "")))
        t.setItem(r, 3, QTableWidgetItem(p.get("style", "")))

    def _ajouter_qui(self):
        self._ligne_qui({"nom": _("Personnage {n}", n=self.t_qui.rowCount() + 1), "genre": "personne"})
        self.t_qui.resizeRowsToContents()
        self.t_qui.setCurrentCell(self.t_qui.rowCount() - 1, 0)

    def _retirer(self, t):
        if t.currentRow() >= 0:
            t.removeRow(t.currentRow())
            self._maj_accord()
            self._maj_prix()

    def _style(self):
        r = self.t_qui.currentRow()
        if r < 0:
            self.etat.setText(_("Cliquez d'abord la ligne du personnage ou de l'objet."))
            return
        from .dialogues_creatif import choisir_style
        nom = choisir_style(self, self.params, "video")
        if nom:
            self.t_qui.item(r, 3).setText(nom)

    def _avec_personnes_reelles(self):
        return any(self.t_qui.cellWidget(r, 1).currentData() == "personne_image" for r in range(self.t_qui.rowCount()))

    def _maj_accord(self):
        self.accord.setVisible(self._avec_personnes_reelles())

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

    def _lire_tables(self):
        """Ce que montrent les tableaux devient la séquence (ce qui n'a pas changé garde ses fiches, images et vidéos)."""
        persos = []
        for r in range(self.t_qui.rowCount()):
            nom = (self.t_qui.item(r, 0).text() if self.t_qui.item(r, 0) else "").strip()
            if not nom:
                continue
            g = self.t_qui.cellWidget(r, 1).currentData()
            persos.append({"nom": nom, "genre": "objet" if g.startswith("objet") else "personne", "sur_image": g.endswith("_image"),
                           "position": "", "description": (self.t_qui.item(r, 2).text() if self.t_qui.item(r, 2) else "").strip(),
                           "style": (self.t_qui.item(r, 3).text() if self.t_qui.item(r, 3) else "").strip()})
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
        if self.pages.currentIndex() != 3:
            return
        self._lire_tables()
        e = A.estimer(self.seq, self.moteur.currentData(), self.params, self.niveau.currentData())
        f, d, a = A.a_preparer(self.seq, self.params)
        self.l_prix.setText(_("A prévoir : {n} image(s) de préparation {i} ; {p} plan(s) vidéo, {s} s, {v} ; relectures {l}. "
                              "Total : {t}, confirmé à l'étape suivante.", n=f + d + a, i=A.argent(e["images"]),
                              p=len(self.seq["plans"]), s=sum(int(pl.get("duree") or 0) for pl in self.seq["plans"]),
                              v=A.argent(e["videos"]), l=A.argent(e["lectures"]), t=A.argent(e["total"])))

    # ------------------------------------------------------------------ écrire librement
    def dire(self):
        texte = self.libre.text().strip()
        if not texte or self._en_calcul():
            return
        k = self.pages.currentIndex()
        if k <= 1:
            self.histoire.setPlainText((self.histoire.toPlainText().rstrip() + " " + texte).strip())
            self.libre.clear()
            self.aller(1)
            return
        if k in (2, 3):
            self._lire_tables()
        seq = copy.deepcopy(self.seq)
        niveau = self.niveau.currentData()
        image = self.image if self._suite() else None

        def fin(r, e):
            if e or not r:
                return
            self.seq, message = r
            if self._cloud():
                A.depenser(self.seq, _("Correction en clair"), A.PRIX_LECTURE)
            self.libre.clear()
            self._remplir_qui()
            self._remplir_plans()
            if k >= 4:
                self.aller(3)
            self._maj_prix()
            self.etat.setText("✓ " + (message or _("C'est modifié : vérifiez, puis continuez.")))
        self._lancer(lambda _t: A.modifier(self.params, seq, texte, niveau, image), _("L'assistant applique votre demande"), fin)

    # ------------------------------------------------------------------ 5. fiches et images
    def preparer(self):
        self._lire_tables()
        if not self.seq["plans"]:
            self.etat.setText(_("Il faut au moins un plan."))
            return
        self._remplir_plans()
        moteur_video = self.moteur.currentData()
        self.seq["moteur"] = moteur_video
        e = A.estimer(self.seq, moteur_video, self.params, self.niveau.currentData())
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
            self.aller(5)
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
            self.aller(4)
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
                self._remplir_qui()
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
        moteur_video, niveau = self.seq.get("moteur") or self.moteur.currentData(), self.niveau.currentData()

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
        """La même histoire dans la Séquence IA : tout y est réglable à la main."""
        if self.pages.currentIndex() in (2, 3):
            self._lire_tables()
        self._garder_dans_projet()
        self.ed._sequence = None
        self.ed.sequence_ia()
        self.hide()

    def done(self, r):
        if garder_calcul(self, self._en_calcul()):
            return
        try:
            self.apercu.arreter()
        except RuntimeError:
            pass
        super().done(r)
