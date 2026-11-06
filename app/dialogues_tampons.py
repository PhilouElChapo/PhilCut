"""Fenêtre « Tampons vidéo » : ma bibliothèque (aperçus animés, recherche, insertion à la tête de lecture), tampons
maison fabriqués sur ce poste, et recherche de clips libres en ligne (Wikimedia Commons, Pixabay, Pexels)."""
import os, tempfile, urllib.request

from PySide6.QtCore import Qt, QSize, QTimer, QUrl
from PySide6.QtGui import QIcon, QPixmap, QImage, QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QListWidget, QListWidgetItem, QLabel, QLineEdit,
                               QPushButton, QComboBox, QMessageBox, QFileDialog, QInputDialog, QDialogButtonBox, QFormLayout)

from . import tampons as T, theme
from .langue import _
from .taches import Tache


def _tc(t):
    m, s = divmod(max(0.0, float(t)), 60)
    return f"{int(m)}:{s:04.1f}"


class DialogueTampons(QDialog):
    def __init__(self, ed, onglet=0):
        super().__init__(ed)
        self.ed = ed
        self.params = ed.params
        self.setWindowTitle(_("Tampons vidéo"))
        self.resize(1000, 680)
        L, H = ed.projet.taille
        self.format = (1920, 1080) if L >= H else (1080, 1920)
        v = QVBoxLayout(self)
        intro = QLabel(_("Des petites séquences toutes faites, avec leur son, à glisser dans le montage pour ponctuer ou faire rire. "
                         "Double-clic ou « Insérer » : le tampon arrive à la tête de lecture ({t}) et la suite du montage se décale ; "
                         "c'est un plan comme un autre (supprimer, rogner, effets).", t=_tc(ed.timeline.position)))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.onglets = QTabWidget()
        v.addWidget(self.onglets, 1)
        self._page_biblio()
        self._page_maison()
        self._page_en_ligne()
        self.onglets.setCurrentIndex(onglet)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
        v.addWidget(self.etat)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.taches = []
        self._frames, self._image_n = [], 0
        self.minuterie = QTimer(self)
        self.minuterie.timeout.connect(self._animer)
        self.minuterie.start(100)
        self.remplir_biblio()

    # ------------------------------------------------------------------ ma bibliothèque
    def _liste_icones(self):
        li = QListWidget()
        li.setViewMode(QListWidget.IconMode)
        li.setIconSize(QSize(192, 108))
        li.setGridSize(QSize(212, 150))
        li.setResizeMode(QListWidget.Adjust)
        li.setMovement(QListWidget.Static)
        li.setWordWrap(True)
        li.setSpacing(4)
        return li

    def _page_biblio(self):
        w = QWidget()
        v = QVBoxLayout(w)
        h = QHBoxLayout()
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(_("Chercher : nom ou mot-clef (humour, fin, retour…)"))
        self.recherche.textChanged.connect(self.remplir_biblio)
        h.addWidget(self.recherche, 1)
        b = QPushButton(_("Importer mon clip…"))
        b.setToolTip(_("Un de vos clips (réaction, gag, logo animé…) : une copie est rangée dans la bibliothèque, avec un nom et des mots-clefs."))
        b.clicked.connect(self.importer)
        h.addWidget(b)
        b = QPushButton(_("Partie en jaune → tampon"))
        b.setToolTip(_("La partie choisie sur la règle des temps (en jaune) devient un tampon de votre bibliothèque."))
        b.clicked.connect(self.depuis_partie)
        h.addWidget(b)
        v.addLayout(h)
        corps = QHBoxLayout()
        self.liste = self._liste_icones()
        self.liste.currentItemChanged.connect(lambda *_a: self._choisi())
        self.liste.itemDoubleClicked.connect(lambda _i: self.inserer())
        self.liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._menu)
        corps.addWidget(self.liste, 3)
        droite = QVBoxLayout()
        self.apercu = QLabel()
        self.apercu.setFixedSize(320, 180)
        self.apercu.setAlignment(Qt.AlignCenter)
        self.apercu.setStyleSheet("background:#000;border-radius:6px")
        droite.addWidget(self.apercu)
        self.infos = QLabel(_("Choisissez un tampon pour le voir."))
        self.infos.setWordWrap(True)
        self.infos.setTextFormat(Qt.RichText)
        self.infos.setOpenExternalLinks(True)
        self.infos.setMaximumWidth(320)
        droite.addWidget(self.infos)
        self.b_inserer = QPushButton(_("Insérer à la tête de lecture"))
        self.b_inserer.setProperty("primaire", True)
        self.b_inserer.clicked.connect(self.inserer)
        droite.addWidget(self.b_inserer)
        hb = QHBoxLayout()
        b = QPushButton(_("Renommer, mots-clefs…"))
        b.clicked.connect(self.renommer)
        hb.addWidget(b)
        b = QPushButton(_("Retirer"))
        b.clicked.connect(self.retirer)
        hb.addWidget(b)
        droite.addLayout(hb)
        b = QPushButton(_("Ouvrir le dossier des tampons"))
        b.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(T.dossier_tampons(self.params))))
        droite.addWidget(b)
        droite.addStretch(1)
        corps.addLayout(droite, 0)
        v.addLayout(corps, 1)
        self.onglets.addTab(w, _("Ma bibliothèque"))

    def remplir_biblio(self, *_a, choisir=None):
        self.liste.clear()
        tout = T.charger(self.params)
        for e in sorted(T.chercher_local(tout, self.recherche.text()), key=lambda x: x.get("ajoute", ""), reverse=True):
            it = QListWidgetItem(f"{e['nom']}\n{e.get('duree', 0):.1f} s · {T.SOURCES.get(e.get('source'), _('maison') if e.get('source') == 'maison' else _('à moi'))}")
            vg = None if e.get("genre") == "son" else T.vignette(self.params, e)
            if vg:
                it.setIcon(QIcon(vg))
            elif e.get("genre") == "son":
                from .icones import icone
                it.setIcon(icone("musique", theme.COULEURS["accent"], 96))
            it.setData(Qt.UserRole, e)
            it.setToolTip(", ".join(e.get("mots") or []))
            self.liste.addItem(it)
            if choisir and e["id"] == choisir:
                self.liste.setCurrentItem(it)
        if not tout:
            it = QListWidgetItem(_("Bibliothèque vide : créez les tampons maison (onglet 2), importez vos clips, ou cherchez des clips libres (onglet 3)."))
            it.setFlags(Qt.NoItemFlags)
            self.liste.addItem(it)
        self.b_inserer.setEnabled(bool(self._entree()))

    def _entree(self):
        it = self.liste.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _choisi(self):
        e = self._entree()
        self.b_inserer.setEnabled(bool(e))
        if not e:
            return
        lignes = [f"<b>{e['nom']}</b>", _("Durée : {d:.1f} s", d=e.get("duree", 0))]
        if e.get("mots"):
            lignes.append(_("Mots-clefs : {m}", m=", ".join(e["mots"])))
        if e.get("auteur") or e.get("licence"):
            lignes.append(_("Auteur : {a} · {l}", a=e.get("auteur") or "?", l=e.get("licence") or ""))
            lignes.append("<span style='color:#999'>" + _("Le crédit est ajouté tout seul à la description lors de la publication.") + "</span>")
        if e.get("page"):
            lignes.append(f"<a href='{e['page']}'>{_('Page d’origine')}</a>")
        self.infos.setText("<br>".join(lignes))
        self._preparer_images(T.chemin(self.params, e), e.get("duree") or 2)

    def _preparer_images(self, video, duree):
        """Une dizaine d'images du clip, jouées en boucle dans l'aperçu (sans lecteur multimédia)."""
        from . import moteur
        d = os.path.join(tempfile.gettempdir(), "philcut-tampons", str(abs(hash(video))))
        if not os.path.isdir(d) or not os.listdir(d):
            os.makedirs(d, exist_ok=True)
            try:
                moteur.lancer(["-i", video, "-vf", f"fps={min(12.0, 24 / max(0.5, float(duree))):.3f},scale=320:180:force_original_aspect_ratio=decrease",
                               "-frames:v", "24", os.path.join(d, "%03d.jpg")])
            except Exception:    # noqa: BLE001
                pass
        self._frames = [QPixmap(os.path.join(d, f)) for f in sorted(os.listdir(d))] if os.path.isdir(d) else []
        self._image_n = 0

    def _animer(self):
        if self.onglets.currentIndex() == 1:
            self._animer_maison()
            return
        if self._frames:
            self._image_n = (self._image_n + 1) % len(self._frames)
            self.apercu.setPixmap(self._frames[self._image_n])

    def inserer(self):
        e = self._entree()
        if not e:
            return
        if e.get("genre") == "son":
            self.ed.poser_son(T.chemin(self.params, e), self.ed.timeline.position, e["nom"])
        else:
            self.ed.inserer_tampon(T.chemin(self.params, e), self.ed.timeline.position, e["nom"])
        self.accept()

    def importer(self):
        f, _f = QFileDialog.getOpenFileName(self, _("Importer mon clip"), self.params.get("dossier_tampons_import") or "",
                                            _("Vidéos et sons") + " (*.mp4 *.mov *.m4v *.mkv *.webm *.avi *.mp3 *.wav *.ogg *.m4a *.aac *.flac)")
        if not f:
            return
        self.params["dossier_tampons_import"] = os.path.dirname(f)
        nom, ok = QInputDialog.getText(self, _("Importer mon clip"), _("Nom du tampon :"), text=os.path.splitext(os.path.basename(f))[0])
        if not ok:
            return
        mots, ok = QInputDialog.getText(self, _("Importer mon clip"), _("Mots-clefs, séparés par des virgules (facultatif) :"))
        self._lancer(lambda t: T.ajouter_fichier(self.params, f, nom.strip(), [m.strip() for m in mots.split(",") if m.strip()]),
                     _("Copie dans la bibliothèque…"))

    def depuis_partie(self):
        tl = self.ed.timeline
        z = tl.zone_valide() if hasattr(tl, "zone_valide") else None
        c = self.ed.projet.clip_a((z[0] + z[1]) / 2, "video") if z else None
        if not z or not c:
            QMessageBox.information(self, _("Tampons vidéo"), _("Choisissez d'abord une partie de la vidéo : glissez sur la règle des temps "
                                                               "(au-dessus des pistes), elle apparaît en jaune."))
            return
        med = self.ed.projet.media(c["media"]) or {}
        a = max(z[0], c["debut"])
        from .projet import fin_clip
        b = min(z[1], fin_clip(c))
        debut = c["src_debut"] + (a - c["debut"]) * c.get("vitesse", 1.0)
        nom, ok = QInputDialog.getText(self, _("Tampons vidéo"), _("Nom du tampon :"), text=med.get("nom") or "")
        if not ok:
            return
        self._lancer(lambda t: T.ajouter_fichier(self.params, med["chemin"], nom.strip(), [], debut, (b - a) * c.get("vitesse", 1.0)),
                     _("Extraction de la partie en jaune…"))

    def renommer(self):
        e = self._entree()
        if not e:
            return
        nom, ok = QInputDialog.getText(self, _("Renommer"), _("Nom du tampon :"), text=e["nom"])
        if not ok:
            return
        mots, ok = QInputDialog.getText(self, _("Mots-clefs"), _("Mots-clefs, séparés par des virgules :"), text=", ".join(e.get("mots") or []))
        if ok:
            T.modifier(self.params, e["id"], nom=nom.strip() or e["nom"], mots=[m.strip() for m in mots.split(",") if m.strip()])
            self.remplir_biblio(choisir=e["id"])

    def retirer(self):
        e = self._entree()
        if e and QMessageBox.question(self, _("Retirer"), _("Retirer « {n} » de la bibliothèque (le fichier est supprimé) ? "
                                                          "Les montages qui l'utilisent déjà le gardent tant que le fichier existe ailleurs.",
                                                          n=e["nom"])) == QMessageBox.Yes:
            T.retirer(self.params, e["id"])
            self.remplir_biblio()

    def _menu(self, pos):
        from PySide6.QtWidgets import QMenu
        it = self.liste.itemAt(pos)
        if not it or not it.data(Qt.UserRole):
            return
        self.liste.setCurrentItem(it)
        m = QMenu(self)
        m.addAction(_("Insérer à la tête de lecture"), self.inserer)
        m.addAction(_("Renommer, mots-clefs…"), self.renommer)
        m.addAction(_("Retirer"), self.retirer)
        m.exec(self.liste.mapToGlobal(pos))

    # ------------------------------------------------------------------ tampons maison
    def _page_maison(self):
        w = QWidget()
        v = QVBoxLayout(w)
        aide = QLabel(_("Tampons dessinés et sonorisés par PhilCut sur ce poste : aucun droit à payer, textes dans la langue de PhilCut, "
                        "au format du projet. Ils rejoignent votre bibliothèque."))
        aide.setWordWrap(True)
        v.addWidget(aide)
        self.liste_maison = self._liste_icones()
        for k, (nom, desc, mots, d) in T.MAISON.items():
            it = QListWidgetItem(nom)
            it.setToolTip(desc)
            it.setData(Qt.UserRole, k)
            it.setIcon(QIcon(QPixmap.fromImage(T.image_maison(k, d * 0.7, 192, 108))))
            self.liste_maison.addItem(it)
        self.liste_maison.itemDoubleClicked.connect(lambda _i: self.creer_maison(False))
        v.addWidget(self.liste_maison, 1)
        h = QHBoxLayout()
        self.info_maison = QLabel("")
        self.info_maison.setWordWrap(True)
        h.addWidget(self.info_maison, 1)
        b = QPushButton(_("Créer celui-ci"))
        b.clicked.connect(lambda: self.creer_maison(False))
        h.addWidget(b)
        self.b_tous = QPushButton(_("Créer tous les tampons maison"))
        self.b_tous.setProperty("primaire", True)
        self.b_tous.clicked.connect(lambda: self.creer_maison(True))
        h.addWidget(self.b_tous)
        v.addLayout(h)
        self.liste_maison.currentItemChanged.connect(lambda *_a: self._info_maison())
        self.onglets.addTab(w, _("Tampons maison"))
        self._t_maison = 0.0
        self._info_maison()

    def _info_maison(self):
        it = self.liste_maison.currentItem()
        manque = T.maison_manquants(self.params, *self.format)
        self.b_tous.setText(_("Créer les {n} tampons maison manquants", n=len(manque)) if manque else _("Tous les tampons maison sont prêts"))
        self.b_tous.setEnabled(bool(manque))
        if it:
            k = it.data(Qt.UserRole)
            self.info_maison.setText(f"<b>{T.MAISON[k][0]}</b> — {T.MAISON[k][1]} ({T.MAISON[k][3]:.1f} s)"
                                     + ("" if k in manque else "  ✓ " + _("dans votre bibliothèque")))

    def _animer_maison(self):
        it = self.liste_maison.currentItem()
        if not it:
            return
        k = it.data(Qt.UserRole)
        d = T.MAISON[k][3]
        self._t_maison = (self._t_maison + 0.1) % d
        it.setIcon(QIcon(QPixmap.fromImage(T.image_maison(k, self._t_maison, 192, 108))))

    def creer_maison(self, tous):
        it = self.liste_maison.currentItem()
        ids = T.maison_manquants(self.params, *self.format) if tous else ([it.data(Qt.UserRole)] if it else [])
        if not ids:
            return
        L, H = self.format

        def travail(t):
            dernier = None
            for i, k in enumerate(ids):
                if t.arret_demande():
                    break
                dernier = T.fabriquer_maison(self.params, k, L, H, progression=lambda f, i=i: t.avancer((i + f) / len(ids), T.MAISON[k][0]))
            return dernier
        self._lancer(travail, _("Fabrication des tampons maison ({n})…", n=len(ids)), apres=self._info_maison)

    # ------------------------------------------------------------------ en ligne
    def _page_en_ligne(self):
        w = QWidget()
        v = QVBoxLayout(w)
        h = QHBoxLayout()
        self.source = QComboBox()
        self.source.addItem(_("Wikimedia Commons (libre, sans clef)"), "wikimedia")
        self.source.addItem(_("Pixabay (clef gratuite)"), "pixabay")
        self.source.addItem(_("Pexels (clef gratuite)"), "pexels")
        for k, (nom, _u) in T.EXTRAITS.items():
            self.source.addItem(_("Extraits de films : {s} (navigateur)", s=nom), "extrait:" + k)
        for k, (nom, _d) in T.SONS_FILMS.items():
            self.source.addItem(_("Répliques et sons de films : {s} (navigateur)", s=nom), "extrait:" + k)
        self.source.currentIndexChanged.connect(self._source_changee)
        h.addWidget(self.source)
        self.question = QLineEdit()
        self.question.setPlaceholderText(_("Dans votre langue, PhilCut traduit en anglais : applaudissements, explosion, foule, rembobinage…"))
        self.question.returnPressed.connect(self.chercher)
        h.addWidget(self.question, 1)
        b = QPushButton(_("Chercher"))
        b.setProperty("primaire", True)
        b.clicked.connect(self.chercher)
        h.addWidget(b)
        self.b_importer_web = QPushButton(_("Importer le clip téléchargé…"))
        self.b_importer_web.setToolTip(_("Le clip téléchargé depuis le site (dossier Téléchargements) rejoint votre bibliothèque."))
        self.b_importer_web.clicked.connect(self.importer_telecharge)
        h.addWidget(self.b_importer_web)
        self.b_clef = QPushButton(_("Ma clef…"))
        self.b_clef.clicked.connect(self.ma_clef)
        h.addWidget(self.b_clef)
        v.addLayout(h)
        self.resultats = self._liste_icones()
        self.resultats.currentItemChanged.connect(lambda *_a: self._resultat_choisi())
        self.resultats.itemDoubleClicked.connect(lambda _i: self.ajouter_resultat(True))
        v.addWidget(self.resultats, 1)
        h = QHBoxLayout()
        self.info_res = QLabel(_("Seuls les clips dont la licence autorise une vidéo publiée sont proposés. Les extraits de films ou "
                                 "d'émissions connus ne sont pas libres : ils ne se trouvent pas ici."))
        self.info_res.setWordWrap(True)
        self.info_res.setTextFormat(Qt.RichText)
        self.info_res.setOpenExternalLinks(True)
        h.addWidget(self.info_res, 1)
        self.b_ajouter = QPushButton(_("Ajouter à ma bibliothèque"))
        self.b_ajouter.clicked.connect(lambda: self.ajouter_resultat(False))
        h.addWidget(self.b_ajouter)
        self.b_ajouter_ins = QPushButton(_("Ajouter et insérer"))
        self.b_ajouter_ins.setProperty("primaire", True)
        self.b_ajouter_ins.clicked.connect(lambda: self.ajouter_resultat(True))
        h.addWidget(self.b_ajouter_ins)
        v.addLayout(h)
        self.onglets.addTab(w, _("Chercher en ligne"))
        self._source_changee()

    def _source_changee(self):
        s = self.source.currentData()
        extrait = s.startswith("extrait:")
        self.b_clef.setVisible(s != "wikimedia" and not extrait)
        self.b_importer_web.setVisible(extrait)
        self.b_ajouter.setVisible(not extrait)
        self.b_ajouter_ins.setVisible(not extrait)
        self.resultats.clear()
        if extrait:
            for ligne in (_("1. Tapez une réplique ou des mots dans votre langue, puis « Chercher » : PhilCut traduit en anglais et "
                            "ouvre le site dans votre navigateur."),
                          _("2. Sur le site, téléchargez l'extrait choisi (bouton de téléchargement du site, quand il existe)."),
                          _("3. « Importer le clip téléchargé… » : l'extrait rejoint votre bibliothèque, prêt à insérer.")):
                it = QListWidgetItem(ligne)
                it.setFlags(Qt.ItemIsEnabled)
                it.setSizeHint(QSize(900, 34))
                self.resultats.addItem(it)
        self.resultats.setViewMode(QListWidget.ListMode if extrait else QListWidget.IconMode)
        self.resultats.setGridSize(QSize() if extrait else QSize(212, 150))
        self.resultats.setIconSize(QSize(192, 108))
        self.info_res.setText(_("<b>Extraits protégés par le droit d'auteur.</b> PhilCut ouvre la recherche du site dans votre navigateur ; "
                                "vous y téléchargez l'extrait vous-même (quand le site le permet), puis « Importer le clip téléchargé ». "
                                "Une courte citation peut être tolérée, mais une vidéo publiée, surtout monétisée, peut être bloquée "
                                "ou démonétisée par YouTube : à vos risques.") if extrait else
                              _("Seuls les clips dont la licence autorise une vidéo publiée sont proposés. Les extraits de films ou "
                                "d'émissions connus ne sont pas libres : ils ne se trouvent pas ici."))
        if extrait:
            return
        if s != "wikimedia":
            from . import coffre
            self.b_clef.setText(_("Ma clef {s} ✓", s=T.SOURCES[s]) if coffre.lire(T.CLEFS[s]) else _("Ma clef {s}…", s=T.SOURCES[s]))

    def ma_clef(self):
        from . import coffre
        s = self.source.currentData()
        d = QDialog(self)
        d.setWindowTitle(_("Ma clef {s}", s=T.SOURCES[s]))
        f = QFormLayout(d)
        aide = QLabel(_("La clef {s} est gratuite : créez un compte sur le site, puis copiez la clef de l'API et collez-la ici. "
                        "Elle reste sur ce poste, dans le coffre du système ; PhilCut n'en contient aucune.", s=T.SOURCES[s]))
        aide.setWordWrap(True)
        f.addRow(aide)
        b = QPushButton(_("Ouvrir la page pour créer ma clef"))
        b.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(T.PAGES_CLEF[s])))
        f.addRow(b)
        champ = QLineEdit()
        from .widgets import oeil
        oeil(champ)
        champ.setPlaceholderText(_("Collez votre clef ici"))
        f.addRow(_("Clef"), champ)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        if d.exec() and champ.text().strip():
            coffre.enregistrer(T.CLEFS[s], champ.text().strip())
            self._source_changee()
            try:                                        # vers les autres postes si la synchro des clefs est cochée
                from . import reglages
                reglages.synchro_secrets_auto(self.params)
            except Exception:    # noqa: BLE001
                pass
            from . import reglages
            self.etat.setText(_("Clef enregistrée dans le coffre du système ; elle suivra sur vos autres postes.")
                              if self.params.get("synchro_secrets") else
                              _("Clef enregistrée dans le coffre du système. Pour la retrouver sur vos autres postes : Préférences › "
                                "Comptes et synchro › « Synchroniser aussi les mots de passe et clefs »."))

    def chercher(self):
        texte = self.question.text().strip()
        if not texte:
            self.question.setFocus()
            return
        s = self.source.currentData()
        if s.startswith("extrait:"):
            site = s.split(":", 1)[1]
            self.etat.setText(_("Ouverture de {s}…", s=T.EXTRAITS[site][0]))

            def ouvrir(r, err):
                if err or not r:
                    return
                url, note = r
                QDesktopServices.openUrl(QUrl(url))
                self.etat.setText(_("Recherche ouverte dans le navigateur.") + ("  " + note if note else ""))
            self._lancer(lambda t: self._traduire_extrait(site, texte), None, fin=ouvrir)
            return
        self.resultats.clear()
        self.etat.setText(_("Recherche sur {s}…", s=T.SOURCES[s]))
        self._lancer(lambda t: self._chercher_et_vignettes(s, texte), None, apres=None, fin=self._resultats_recus)

    @staticmethod
    def _traduire_extrait(site, texte):
        from . import traduction_recherche as TR
        tr = TR.en_anglais(texte)
        return T.url_extrait(site, tr[0]), TR.message(texte, tr)

    def importer_telecharge(self):
        from .session import dossier_systeme
        f, _f = QFileDialog.getOpenFileName(self, _("Importer le clip téléchargé"), self.params.get("dossier_tampons_web") or dossier_systeme("telechargements"),
                                            _("Vidéos et sons") + " (*.mp4 *.mov *.m4v *.mkv *.webm *.gif *.mp3 *.wav *.ogg *.m4a *.aac *.flac)")
        if not f:
            return
        self.params["dossier_tampons_web"] = os.path.dirname(f)
        site = self.source.currentData().split(":", 1)[-1]
        nom, ok = QInputDialog.getText(self, _("Importer le clip téléchargé"), _("Nom du tampon :"), text=os.path.splitext(os.path.basename(f))[0])
        if not ok:
            return
        mots = [m for m in self.question.text().split() if len(m) > 2] + [(T.EXTRAITS.get(site) or T.SONS_FILMS.get(site) or (site,))[0]]
        self._lancer(lambda t: T.ajouter_fichier(self.params, f, nom.strip(), mots), _("Copie dans la bibliothèque…"))

    @staticmethod
    def _chercher_et_vignettes(source, texte):
        from . import traduction_recherche as TR
        tr = TR.en_anglais(texte)
        res = T.chercher(source, tr[0])
        res = [dict(r, _note=TR.message(texte, tr)) for r in res] or [{"_vide": True, "_note": TR.message(texte, tr)}]
        d = os.path.join(tempfile.gettempdir(), "philcut-tampons", "web")
        os.makedirs(d, exist_ok=True)
        for k, r in enumerate(res):                                     # petites images des résultats
            if r.get("vignette"):
                f = os.path.join(d, f"{abs(hash(r['vignette']))}.jpg")
                if not os.path.exists(f):
                    try:
                        req = urllib.request.Request(r["vignette"], headers=T._agent())
                        with urllib.request.urlopen(req, timeout=15) as rep, open(f, "wb") as g:
                            g.write(rep.read())
                    except Exception:    # noqa: BLE001
                        continue
                r["_vignette"] = f
        return res

    def _resultats_recus(self, res, err):
        if err:
            self.etat.setText("✕ " + str(err))
            return
        self.resultats.clear()
        note = (res[0].get("_note") if res else "") or ""
        res = [r for r in res if not r.get("_vide")]
        for r in res:
            it = QListWidgetItem(f"{r['titre'][:40]}\n{r.get('duree', 0):.0f} s · {r.get('auteur', '')[:24]}")
            if r.get("_vignette"):
                img = QImage(r["_vignette"])
                if not img.isNull():
                    it.setIcon(QIcon(QPixmap.fromImage(img.scaled(192, 108, Qt.KeepAspectRatio, Qt.SmoothTransformation))))
            it.setData(Qt.UserRole, r)
            it.setToolTip(f"{r['titre']}\n{r.get('licence', '')}")
            self.resultats.addItem(it)
        self.etat.setText((_("{n} clip(s) trouvé(s). Double-clic : ajouter à la bibliothèque et insérer.", n=len(res)) if res else
                           _("Rien trouvé : essayez d'autres mots (en anglais).")) + ("  " + note if note else ""))

    def _resultat_choisi(self):
        it = self.resultats.currentItem()
        r = it.data(Qt.UserRole) if it else None
        if r:
            self.info_res.setText(f"<b>{r['titre']}</b> — {r.get('auteur', '?')} · {r.get('licence', '')} · {r.get('duree', 0):.0f} s"
                                  + (f" · <a href='{r['page']}'>{_('page')}</a>" if r.get("page") else ""))

    def ajouter_resultat(self, inserer):
        it = self.resultats.currentItem()
        r = it.data(Qt.UserRole) if it else None
        if not r:
            return

        def apres(e=None):
            if inserer and e:
                self.ed.inserer_tampon(T.chemin(self.params, e), self.ed.timeline.position, e["nom"])
                self.accept()
        self._lancer(lambda t: T.telecharger(self.params, r, progression=lambda f: t.avancer(f), arret=t.arret_demande),
                     _("Téléchargement de « {t} »…", t=r["titre"]), fin_entree=apres)

    # ------------------------------------------------------------------ tâches de fond
    def _lancer(self, travail, message, apres=None, fin=None, fin_entree=None):
        t = Tache(travail, _("Tampons vidéo"))
        self.taches.append(t)
        try:
            self.ed.taches.append(t)
        except Exception:    # noqa: BLE001
            pass
        if message:
            self.etat.setText(message)
            try:
                self.ed.encart.suivre(t, message)
            except Exception:    # noqa: BLE001
                pass
        t.progression.connect(lambda f, txt: self.etat.setText(f"{message or ''} {int(f * 100)} %  {txt}"))

        def termine(r, err):
            if fin:
                fin(r, err)
                return
            if err:
                self.etat.setText("✕ " + str(err))
                return
            self.etat.setText(_("✓ Ajouté à votre bibliothèque."))
            self.remplir_biblio(choisir=r.get("id") if isinstance(r, dict) else None)
            if apres:
                apres()
            if fin_entree:
                fin_entree(r)
            elif isinstance(r, dict) and self.onglets.currentIndex() != 1:
                self.onglets.setCurrentIndex(0)
        t.fini.connect(termine)
        t.start()

    def reject(self):
        self._fermer()
        super().reject()

    def accept(self):
        self._fermer()
        super().accept()

    def _fermer(self):
        self.minuterie.stop()                       # une création en cours continue en tâche de fond (barre du bas)
