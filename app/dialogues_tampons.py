"""Fenêtre « Tampons vidéo » : ma bibliothèque (aperçus animés, recherche, insertion à la ligne rouge), tampons
maison fabriqués sur ce poste, et recherche de clips libres en ligne (Wikimedia Commons, Pixabay, Pexels)."""
import os, tempfile, time, urllib.request

from PySide6.QtCore import Qt, QSize, QTimer, QUrl
from PySide6.QtGui import QIcon, QPixmap, QImage, QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QListWidget, QListWidgetItem, QLabel, QLineEdit,
                               QPushButton, QComboBox, QMessageBox, QFileDialog, QInputDialog, QDialogButtonBox, QFormLayout, QCheckBox)

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
                         "Double-clic ou « Mettre dans le film… » : PhilCut demande où (début, ligne rouge, partie en jaune, fin) et "
                         "comment (insérer ou par-dessus). Réglages par défaut, ordre et emplacement de la bibliothèque : Edition › "
                         "Préférences › Tampons et extraits."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.onglets = QTabWidget()
        v.addWidget(self.onglets, 1)
        self._page_biblio()
        self._page_maison()
        self._page_en_ligne()
        self._page_ia()
        self.onglets.setCurrentIndex(onglet)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:%s" % theme.COULEURS["texte2"])
        v.addWidget(self.etat)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.button(QDialogButtonBox.Close).setText(_("Fermer"))
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
        h.addWidget(QLabel(_("Classer")))
        self.classement = QComboBox()
        for k, lib in T.CLASSEMENTS.items():
            self.classement.addItem(lib, k)
        self.classement.setCurrentIndex(max(0, self.classement.findData(self.params.get("tampons_classement", "perso"))))
        self.classement.currentIndexChanged.connect(self._classement_change)
        h.addWidget(self.classement)
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
        self.liste.model().rowsMoved.connect(lambda *_a: QTimer.singleShot(0, self._ordre_glisse))
        self.liste.currentItemChanged.connect(lambda *_a: self._choisi())
        self.liste.itemDoubleClicked.connect(lambda _i: self.inserer())
        # comme une table de sons : un clic sur un son, on l'entend
        self.liste.itemClicked.connect(lambda it: self.ecouter() if (it.data(Qt.UserRole) or {}).get("genre") == "son" else None)
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
        self.b_inserer = QPushButton(_("Mettre dans le film…"))
        self.b_inserer.setToolTip(_("Choisir où (début, ligne rouge, partie en jaune, fin) et comment (insérer ou par-dessus)"))
        self.b_inserer.setProperty("primaire", True)
        self.b_inserer.clicked.connect(self.inserer)
        droite.addWidget(self.b_inserer)
        he = QHBoxLayout()
        b = QPushButton("▶ " + _("Écouter"))
        b.setToolTip(_("Un clic sur un son l'écoute aussi"))
        b.clicked.connect(self.ecouter)
        he.addWidget(b)
        b = QPushButton(_("Raccourcir…"))
        b.clicked.connect(self.raccourcir)
        he.addWidget(b)
        droite.addLayout(he)
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
        b = QPushButton(_("Réglages des tampons et extraits…"))
        b.setToolTip(_("Edition › Préférences › Tampons et extraits : où poser par défaut, classement, clefs, YouTube"))
        b.clicked.connect(self._reglages)
        droite.addWidget(b)
        droite.addStretch(1)
        corps.addLayout(droite, 0)
        v.addLayout(corps, 1)
        self.onglets.addTab(w, _("Ma bibliothèque"))

    def remplir_biblio(self, *_a, choisir=None):
        self.liste.clear()
        tout = T.charger(self.params)
        mode = self.classement.currentData() or "perso"
        perso = mode == "perso" and not self.recherche.text().strip()
        self.liste.setMovement(QListWidget.Snap if perso else QListWidget.Static)
        self.liste.setDragDropMode(QListWidget.InternalMove if perso else QListWidget.NoDragDrop)
        for e in T.trier(T.chercher_local(tout, self.recherche.text()), mode):
            it = QListWidgetItem(("★ " if e.get("favori") else "") + f"{e['nom']}\n{e.get('duree', 0):.1f} s · {T.SOURCES.get(e.get('source'), _('maison') if e.get('source') == 'maison' else _('à moi'))}")
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

    # ---- ordre de la bibliothèque (rangé dans la bibliothèque : suit sur vos autres postes)
    def _reglages(self):
        f = self.ed.window()
        if hasattr(f, "preferences"):
            f.preferences("Tampons")
            self.classement.blockSignals(True)
            self.classement.setCurrentIndex(max(0, self.classement.findData(self.params.get("tampons_classement", "perso"))))
            self.classement.blockSignals(False)
            self.remplir_biblio()

    def _classement_change(self):
        self.params["tampons_classement"] = self.classement.currentData()
        self.params.enregistrer()
        self.remplir_biblio()

    def _ids_affiches(self):
        return [self.liste.item(i).data(Qt.UserRole)["id"] for i in range(self.liste.count()) if self.liste.item(i).data(Qt.UserRole)]

    def _ordre_glisse(self):
        if self.classement.currentData() != "perso":
            return
        T.ranger(self.params, self._ids_affiches())
        self.etat.setText(_("Ordre enregistré (il suit sur vos autres postes avec la bibliothèque)."))

    def _passer_en_perso(self):
        """Monter, descendre : on passe à « Mon ordre » en partant de l'ordre affiché."""
        ids = self._ids_affiches()
        if self.classement.currentData() != "perso":
            T.ranger(self.params, ids)
            self.classement.blockSignals(True)
            self.classement.setCurrentIndex(self.classement.findData("perso"))
            self.classement.blockSignals(False)
            self.params["tampons_classement"] = "perso"
        return ids

    def deplacer(self, sens):
        e = self._entree()
        if not e:
            return
        ids = self._passer_en_perso()
        i = ids.index(e["id"])
        j = 0 if sens == "haut" else len(ids) - 1 if sens == "bas" else max(0, min(len(ids) - 1, i + sens))
        ids.insert(j, ids.pop(i))
        T.ranger(self.params, ids)
        self.remplir_biblio(choisir=e["id"])

    def basculer_favori(self):
        e = self._entree()
        if e:
            T.modifier(self.params, e["id"], favori=not e.get("favori"))
            self.remplir_biblio(choisir=e["id"])

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
        if e.get("genre") == "son":                       # comme une table de sons : un clic, on entend
            self._frames = []
            from .icones import icone
            self.apercu.setPixmap(icone("musique", theme.COULEURS["accent"], 96).pixmap(96, 96))
            return
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
        if e:
            self.poser_entree(e)

    def poser_entree(self, e):
        """Demande où et comment (début, ligne rouge, partie en jaune, fin ; insérer, par-dessus), puis pose le tampon."""
        if not e:
            return False
        choix = DialoguePlacement(self, self.ed, e).demander()
        if not choix:
            return False
        if e.get("genre") == "son":
            self.ed.poser_son(T.chemin(self.params, e), choix["t"], e["nom"])
        else:
            self.ed.placer_tampon(T.chemin(self.params, e), e["nom"], choix)
        T.noter_usage(self.params, e["id"])
        self.accept()
        return True

    def importer(self):
        from .widgets import ouvrir_fichier
        f = ouvrir_fichier(self, _("Importer mon clip"), _("Vidéos et sons") + " (*.mp4 *.mov *.m4v *.mkv *.webm *.avi *.mp3 *.wav *.ogg *.m4a *.aac *.flac)",
                           "videos", self.params)
        if not f:
            return
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
            QMessageBox.information(self, _("Tampons vidéo"), _("Choisissez d'abord une partie de la vidéo : double-clic sur la règle des temps "
                                                               "(au-dessus des pistes) au début, puis à la fin ; elle apparaît en jaune."))
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
        e = it.data(Qt.UserRole)
        m.addAction(_("Mettre dans le film…"), self.inserer)
        m.addAction("▶ " + _("Écouter"), self.ecouter)
        m.addSeparator()
        m.addAction(_("Retirer des favoris") if e.get("favori") else _("★ Favori (toujours en tête)"), self.basculer_favori)
        m.addAction(_("Monter"), lambda: self.deplacer(-1))
        m.addAction(_("Descendre"), lambda: self.deplacer(1))
        m.addAction(_("Tout en haut"), lambda: self.deplacer("haut"))
        m.addAction(_("Tout en bas"), lambda: self.deplacer("bas"))
        m.addSeparator()
        m.addAction(_("Raccourcir…"), self.raccourcir)
        m.addAction(_("Renommer, mots-clefs…"), self.renommer)
        m.addAction(_("Enregistrer une copie sous…"), lambda: self._copie(e))
        m.addAction(_("Retirer"), self.retirer)
        m.exec(self.liste.mapToGlobal(pos))

    def _copie(self, e):
        from .dialogues_creatif import enregistrer_copie
        enregistrer_copie(self, os.path.join(T.dossier_tampons(self.params), e.get("fichier", "")), self.params)

    # ------------------------------------------------------------------ tampons maison
    # ------------------------------------------------------------------ tampons créés par l'IA (0.9.18)
    def _page_ia(self):
        from . import bruitages as B, tampons_ia as TI
        w = QWidget()
        h = QHBoxLayout(w)
        g = QVBoxLayout()
        aide = QLabel(_("Petites animations créées par l'IA : une image dessinée, du mouvement, un texte qui claque, des bruitages et "
                        "une phrase dite avec un style de voix. Choisissez un modèle, modifiez-le, puis « Créer » : il rejoint votre "
                        "bibliothèque."))
        aide.setWordWrap(True)
        g.addWidget(aide)
        self.liste_ia = QListWidget()
        for k, m in TI.MODELES.items():
            it = QListWidgetItem(m[0])
            it.setData(Qt.UserRole, k)
            self.liste_ia.addItem(it)
        self.liste_ia.currentItemChanged.connect(lambda *_a: self._modele_ia())
        g.addWidget(self.liste_ia, 1)
        h.addLayout(g, 1)
        f = QFormLayout()
        self.ia_nom = QLineEdit()
        f.addRow(_("Nom"), self.ia_nom)
        from PySide6.QtWidgets import QPlainTextEdit, QDoubleSpinBox
        self.ia_consigne = QPlainTextEdit()
        self.ia_consigne.setMaximumHeight(80)
        self.ia_consigne.setToolTip(_("Ce que l'IA dessine (en anglais, la langue que les moteurs comprennent ; le français est traduit)"))
        f.addRow(_("Image (phrase pour l'IA)"), self.ia_consigne)
        self.ia_mouvement = QComboBox()
        for k, lib in TI.MOUVEMENTS.items():
            self.ia_mouvement.addItem(lib, k)
        f.addRow(_("Mouvement"), self.ia_mouvement)
        self.ia_texte = QLineEdit()
        self.ia_texte.setPlaceholderText(_("Facultatif : BOUM !, VICTOIRE !…"))
        f.addRow(_("Texte à l'image"), self.ia_texte)
        self.ia_phrase = QLineEdit()
        self.ia_phrase.setPlaceholderText(_("Facultatif : la phrase dite (voix de synthèse de ce poste)"))
        f.addRow(_("Phrase dite"), self.ia_phrase)
        self.ia_voix = QComboBox()
        for k, lib in TI.STYLES_VOIX.items():
            self.ia_voix.addItem(lib, k)
        f.addRow(_("Style de voix"), self.ia_voix)
        hb = QHBoxLayout()
        self.ia_b1, self.ia_b2 = QComboBox(), QComboBox()
        for cb in (self.ia_b1, self.ia_b2):
            cb.addItem(_("(aucun)"), "")
            for k, (nom, *_r) in B.SONS.items():
                cb.addItem(nom, k)
            hb.addWidget(cb)
        f.addRow(_("Bruitages"), hb)
        self.ia_duree = QDoubleSpinBox()
        self.ia_duree.setRange(1.5, 8.0)
        self.ia_duree.setSuffix(" s")
        f.addRow(_("Durée"), self.ia_duree)
        self.ia_niveau = QComboBox()
        self.ia_niveau.addItem(_("Image par l'IA locale (sur ce poste, gratuit)"), "locale")
        self.ia_niveau.addItem(_("Image par l'IA cloud (Gemini, votre clef, payant)"), "cloud")
        f.addRow(_("Dessin"), self.ia_niveau)
        b = QPushButton(_("Créer ce tampon"))
        b.setProperty("primaire", True)
        b.clicked.connect(self.creer_ia)
        f.addRow(b)
        d = QWidget()
        d.setLayout(f)
        h.addWidget(d, 2)
        self.onglets.addTab(w, _("Tampons IA"))
        self.liste_ia.setCurrentRow(0)

    def _modele_ia(self):
        from . import tampons_ia as TI
        it = self.liste_ia.currentItem()
        if not it:
            return
        nom, consigne, mouv, bruits, phrase, texte, voix, duree = TI.MODELES[it.data(Qt.UserRole)]
        self.ia_nom.setText(nom)
        self.ia_consigne.setPlainText(consigne)
        self.ia_mouvement.setCurrentIndex(max(0, self.ia_mouvement.findData(mouv)))
        self.ia_texte.setText(texte)
        self.ia_phrase.setText(phrase)
        self.ia_voix.setCurrentIndex(max(0, self.ia_voix.findData(voix)))
        for cb, b in zip((self.ia_b1, self.ia_b2), list(bruits) + ["", ""]):
            cb.setCurrentIndex(max(0, cb.findData(b)))
        self.ia_duree.setValue(duree)

    def reglages_ia(self):
        return {"nom": self.ia_nom.text().strip() or _("Tampon IA"), "consigne": self.ia_consigne.toPlainText().strip(),
                "mouvement": self.ia_mouvement.currentData(), "texte": self.ia_texte.text().strip(), "phrase": self.ia_phrase.text().strip(),
                "voix": self.ia_voix.currentData(), "bruitages": [b for b in (self.ia_b1.currentData(), self.ia_b2.currentData()) if b],
                "duree": self.ia_duree.value()}

    def creer_ia(self):
        from . import tampons_ia as TI, traduction_recherche as TR
        r = self.reglages_ia()
        niveau = self.ia_niveau.currentData()
        if niveau == "cloud":
            from . import ia
            if not ia.confirmer_cout(self, self.params, 200, 1, _("Image du tampon « {n} »", n=r["nom"])):
                return
        L, H = self.format

        def travail(t):
            from . import styles_ia as S
            st = S.transposer(r["consigne"], "image", self.params)       # « façon Tim Burton » → description du style
            ph = TR.phrase_en_anglais(st["texte"]) if st["texte"] else ("", "deja", [])
            en = ", ".join(x for x in (ph[0] or st["texte"], st["ajout"]) if x)
            r2 = dict(r, consigne=en or r["consigne"])
            return TI.creer(self.params, r2, L=L // 2 * 2 if L <= 1280 else 1280, H=(H * (1280 / L) if L > 1280 else H) // 2 * 2,
                            niveau=niveau, progression=t.avancer, arret=t.arret_demande)
        self._lancer(travail, _("Création du tampon « {n} » par l'IA…", n=r["nom"]),
                     fin=lambda e, err: (self.etat.setText("✕ " + str(err)[:300]) if err else
                                         (self.remplir_biblio(choisir=e["id"]), self.onglets.setCurrentIndex(0),
                                          self.etat.setText(_("✓ « {n} » créé et rangé dans votre bibliothèque : double-clic pour le "
                                                              "mettre dans le film.", n=e["nom"])))))

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
        self.source.addItem(_("Films du domaine public : Internet Archive"), "archive")
        self.source.addItem(_("Vidéos en ligne : YouTube et autres, par yt-dlp (à vos risques)"), "ytdlp")
        for k, (nom, _d) in T.SONS_FILMS.items():
            self.source.addItem(_("Répliques et sons de films : {s} (navigateur)", s=nom), "extrait:" + k)
        for k, (nom, _u) in T.EXTRAITS.items():
            self.source.addItem(_("Extraits de films et séries : {s} (navigateur)", s=nom), "extrait:" + k)
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
        bl = QPushButton(_("Coller un lien"))
        bl.setToolTip(_("Un lien de vidéo copié (YouTube, Vimeo, Dailymotion, lien direct vers un fichier .mp4…) : PhilCut la lit, vous "
                        "la regardez ici, choisissez le morceau, et seul ce morceau est téléchargé, avec la progression."))
        bl.clicked.connect(self.coller_lien)
        h.addWidget(bl)
        self.b_importer_web = QPushButton(_("Importer le clip téléchargé…"))
        self.b_importer_web.setToolTip(_("Le clip téléchargé depuis le site (dossier Téléchargements) rejoint votre bibliothèque."))
        self.b_importer_web.clicked.connect(self.importer_telecharge)
        h2 = QHBoxLayout()                       # 2e ligne : le champ de recherche garde toute sa largeur
        h2.addWidget(self.b_importer_web)
        # morceau à garder (vidéos longues : on ne télécharge que lui)
        self.ligne_morceau = QWidget()
        hm = QHBoxLayout(self.ligne_morceau)
        hm.setContentsMargins(0, 0, 0, 0)
        hm.addWidget(QLabel(_("Morceau à garder : de")))
        self.morceau_de = QLineEdit()
        self.morceau_de.setPlaceholderText("0:00")
        self.morceau_de.setMaximumWidth(80)
        hm.addWidget(self.morceau_de)
        hm.addWidget(QLabel(_("à")))
        self.morceau_a = QLineEdit()
        self.morceau_a.setPlaceholderText("0:10")
        self.morceau_a.setMaximumWidth(80)
        hm.addWidget(self.morceau_a)
        self.audio_seul = QCheckBox(_("Le son seulement"))
        self.audio_seul.setChecked(bool(self.params.get("ytdlp_son_seul")))
        hm.addWidget(self.audio_seul)
        self.b_maj_ytdlp = QPushButton(_("Mettre à jour yt-dlp"))
        self.b_maj_ytdlp.setToolTip(_("Les sites changent souvent : si un téléchargement échoue, mettez yt-dlp à jour"))
        self.b_maj_ytdlp.clicked.connect(self.maj_ytdlp)
        hm.addWidget(self.b_maj_ytdlp)
        h2.addWidget(self.ligne_morceau)
        self.genre_yt = QComboBox()
        self.genre_yt.addItem(_("Vidéos et Shorts"), "tout")
        self.genre_yt.addItem(_("Shorts seulement"), "shorts")
        self.genre_yt.addItem(_("Vidéos (sans les Shorts)"), "videos")
        from .videos_en_ligne import pays
        self.genre_yt.setToolTip(_("Recherche sur le YouTube de votre pays ({p}), avec vos mots tels que tapés", p=pays()))
        h2.addWidget(self.genre_yt)
        self.langue_rech = QComboBox()
        self.langue_rech.addItem(_("Mots tapés et en anglais"), "deux")
        self.langue_rech.addItem(_("Mots tels que tapés"), "tel")
        self.langue_rech.addItem(_("Traduits en anglais"), "anglais")
        self.langue_rech.setToolTip(_("Ces sites sont surtout en anglais : chercher aussi la traduction anglaise donne plus de résultats. "
                                      "Choisissez « tels que tapés » pour un nom propre ou un titre de film."))
        self.langue_rech.setCurrentIndex(max(0, self.langue_rech.findData(self.params.get("tampons_langue_recherche", "deux"))))
        self.langue_rech.currentIndexChanged.connect(lambda: self.params.__setitem__("tampons_langue_recherche", self.langue_rech.currentData()))
        h2.addWidget(self.langue_rech)
        self.guette = QCheckBox(_("Ajouter tout seul ce que je télécharge"))
        self.guette.setChecked(self.params.get("tampons_guetter", True) is not False)
        self.guette.setToolTip(_("Pendant 15 minutes après l'ouverture du site, les sons et clips qui arrivent dans votre dossier "
                                 "Téléchargements rejoignent votre bibliothèque"))
        self.guette.toggled.connect(lambda on: self.params.__setitem__("tampons_guetter", on))
        h2.addWidget(self.guette)
        h2.addStretch(1)
        self.b_clef = QPushButton(_("Ma clef…"))
        self.b_clef.clicked.connect(self.ma_clef)
        h.addWidget(self.b_clef)
        v.addLayout(h)
        v.addLayout(h2)
        self.suggestion = QLabel("")
        self.suggestion.setTextFormat(Qt.RichText)
        self.suggestion.linkActivated.connect(self._prendre_suggestion)
        self.suggestion.hide()
        v.addWidget(self.suggestion)
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
        self.b_voir = QPushButton("▶ " + _("Regarder et choisir le morceau…"))
        self.b_voir.setToolTip(_("Regarder la vidéo ici, dans PhilCut, et marquer le début et la fin du morceau à importer"))
        self.b_voir.clicked.connect(self.regarder)
        h.addWidget(self.b_voir)
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
        site = s.split(":", 1)[-1]
        self.question.setPlaceholderText(_("Une réplique ou des mots, en français : c'est pas faux, la voiture, on se calme…")
                                         if site in T.SANS_TRADUCTION else
                                         _("Mots à chercher sur YouTube, ou un lien collé : YouTube, Vimeo, Dailymotion, fichier .mp4…") if s == "ytdlp" else
                                         _("Dans votre langue : applaudissements, explosion, foule, rembobinage…"))
        self.b_clef.setVisible(s != "wikimedia" and not extrait)
        self.b_importer_web.setVisible(extrait)
        self.guette.setVisible(extrait)
        en_ligne = s in ("ytdlp", "archive")
        self.ligne_morceau.setVisible(en_ligne)
        self.b_maj_ytdlp.setVisible(s == "ytdlp")
        self.audio_seul.setVisible(s == "ytdlp")
        self.genre_yt.setVisible(s == "ytdlp")
        self.langue_rech.setVisible(not extrait and s != "ytdlp")
        self.b_voir.setVisible(en_ligne)
        self.suggestion.hide()
        self.b_ajouter.setVisible(not extrait)
        self.b_ajouter_ins.setVisible(not extrait)
        self.resultats.clear()
        if extrait:
            for ligne in ((_("1. Tapez une réplique ou des mots en français, puis « Chercher » : PhilCut ouvre le site dans votre navigateur.")
                           if site in T.SANS_TRADUCTION else
                           _("1. Tapez une réplique ou des mots dans votre langue, puis « Chercher » : PhilCut traduit en anglais et "
                             "ouvre le site dans votre navigateur.")),
                          _("2. Sur le site, écoutez et téléchargez l'extrait choisi (bouton de téléchargement du site, quand il existe)."),
                          _("3. PhilCut guette votre dossier Téléchargements : l'extrait rejoint tout seul votre bibliothèque, prêt à "
                            "écouter, raccourcir et insérer (sinon « Importer le clip téléchargé… »).")):
                it = QListWidgetItem(ligne)
                it.setFlags(Qt.ItemIsEnabled)
                it.setSizeHint(QSize(900, 34))
                self.resultats.addItem(it)
        self.resultats.setViewMode(QListWidget.ListMode if extrait else QListWidget.IconMode)
        self.resultats.setGridSize(QSize() if extrait else QSize(212, 150))
        self.resultats.setIconSize(QSize(192, 108))
        self.info_res.setText(_("<b>Extraits protégés par le droit d'auteur.</b> PhilCut ouvre la recherche du site dans votre navigateur ; "
                                "vous y écoutez et téléchargez l'extrait vous-même (quand le site le permet), il rejoint votre bibliothèque. "
                                "Une courte citation peut être tolérée, mais une vidéo publiée, surtout monétisée, peut être bloquée "
                                "ou démonétisée par YouTube : à vos risques.") if extrait else
                              _("Seuls les clips dont la licence autorise une vidéo publiée sont proposés. Les extraits de films ou "
                                "d'émissions connus ne sont pas libres : ils ne se trouvent pas ici."))
        if s in ("ytdlp", "archive"):
            from . import videos_en_ligne as VL
            self.b_clef.hide()
            self.resultats.setViewMode(QListWidget.ListMode)
            self.resultats.setGridSize(QSize())
            self.info_res.setText(VL.LEGAL)
            return
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
        if texte.startswith(("http://", "https://")) and s != "ytdlp":
            # un lien collé (YouTube, Vimeo, Dailymotion, fichier .mp4…) : il se lit par yt-dlp, quelle que soit la source choisie
            self.source.setCurrentIndex(self.source.findData("ytdlp"))
            self.question.setText(texte)
            s = "ytdlp"
        if s.startswith("extrait:"):
            site = s.split(":", 1)[1]
            self.etat.setText(_("Ouverture de {s}…", s=T.EXTRAITS[site][0]))

            if site in T.SANS_RECHERCHE:
                from PySide6.QtWidgets import QApplication
                QApplication.clipboard().setText(texte)

            def ouvrir(r, err):
                if err or not r:
                    return
                url, note = r
                import webbrowser                # navigateur par défaut du système (fiable depuis toute version de PhilCut)
                if not webbrowser.open(url):
                    QDesktopServices.openUrl(QUrl(url))
                self.guetter(site)
                if note:
                    self.etat.setText(self.etat.text() + "  " + note if self.guette.isChecked() else
                                      _("Recherche ouverte dans le navigateur.") + "  " + note)
                elif not self.guette.isChecked():
                    self.etat.setText(_("Recherche ouverte dans le navigateur."))
            self._lancer(lambda t: self._traduire_extrait(site, texte), None, fin=ouvrir)
            return
        if s == "ytdlp":
            if not self._ytdlp_pret():
                return
            from . import videos_en_ligne as VL
            self.resultats.clear()
            url = texte.startswith(("http://", "https://"))
            self.etat.setText(_("Lecture de la vidéo…") if url else _("Recherche sur YouTube…"))
            n, genre = int(self.params.get("ytdlp_resultats") or 30), self.genre_yt.currentData()
            dv = os.path.join(tempfile.gettempdir(), "philcut-tampons", "youtube")
            self._lancer(lambda t: [dict(VL.infos(texte), source="youtube")] if url else
                         VL.vignettes(VL.chercher_youtube(texte, n, genre), dv, t.arret_demande), None, fin=self._resultats_recus)
            if not url:
                self._verifier_orthographe(texte)
            return
        if s == "archive":
            from . import videos_en_ligne as VL
            from . import traduction_recherche as TR
            self.resultats.clear()
            self.etat.setText(_("Recherche sur Internet Archive…"))
            mode = self.langue_rech.currentData()
            self._lancer(lambda t: VL.chercher_archive(texte if mode != "anglais" else TR.en_anglais(texte)[0], 30,
                                                       TR.en_anglais(texte)[0] if mode == "deux" else ""), None, fin=self._resultats_recus)
            return
        self.resultats.clear()
        self.etat.setText(_("Recherche sur {s}…", s=T.SOURCES[s]))
        mode = self.langue_rech.currentData()
        self._lancer(lambda t: self._chercher_et_vignettes(s, texte, mode), None, apres=None, fin=self._resultats_recus)

    @staticmethod
    def _traduire_extrait(site, texte):
        from . import traduction_recherche as TR
        if site in T.SANS_TRADUCTION:                   # site en français : on cherche tel quel
            note = _("« {t} » copié : collez-le dans la recherche du site (Ctrl+V).", t=texte) if site in T.SANS_RECHERCHE else ""
            return T.url_extrait(site, texte), note
        tr = TR.en_anglais(texte)
        return T.url_extrait(site, tr[0]), TR.message(texte, tr)

    # ---- téléchargements faits dans le navigateur : ils rejoignent la bibliothèque tout seuls
    def guetter(self, site):
        if not self.guette.isChecked():
            return
        from .session import dossier_systeme
        self._guet_dossier = dossier_systeme("telechargements")
        self._guet_site = site
        self._guet_mots = [m for m in self.question.text().split() if len(m) > 2]
        if not getattr(self, "_guet_timer", None):
            self._guet_timer = QTimer(self)
            self._guet_timer.setInterval(1500)
            self._guet_timer.timeout.connect(self._guet_tic)
        if not self._guet_timer.isActive():
            self._guet_avant = T.etat_dossier(self._guet_dossier)
            self._guet_prec = dict(self._guet_avant)
        self._guet_fin = time.monotonic() + 15 * 60
        self._guet_timer.start()
        self.etat.setText(_("Recherche ouverte dans le navigateur. PhilCut guette votre dossier Téléchargements pendant 15 minutes : "
                            "ce que vous téléchargez arrive dans votre bibliothèque."))

    def _guet_tic(self):
        if time.monotonic() > self._guet_fin:
            self._guet_timer.stop()
            return
        prets, self._guet_prec = T.nouveaux_telecharges(self._guet_dossier, self._guet_avant, self._guet_prec)
        for p in prets:
            self._guet_avant[p] = self._guet_prec.get(p)
            nom = T.nom_depuis_fichier(p)
            site = (T.EXTRAITS.get(self._guet_site) or T.SONS_FILMS.get(self._guet_site) or (self._guet_site,))[0]
            self.etat.setText(_("Téléchargement repéré : « {n} »… copie dans la bibliothèque.", n=os.path.basename(p)))

            def fin(e, err, nom=nom):
                if err:
                    self.etat.setText("✕ " + str(err))
                    return
                self.remplir_biblio(choisir=e["id"])
                self.etat.setText(_("✓ « {n} » ajouté à votre bibliothèque. Onglet « Ma bibliothèque » : écouter, raccourcir, renommer, insérer.",
                                    n=nom))
            self._lancer(lambda t, p=p, nom=nom, site=site: T.ajouter_fichier(self.params, p, nom, self._guet_mots + [site]), None, fin=fin)

    def ecouter(self):
        e = self._entree()
        if not e:
            return
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":     # tests automatiques : pas de carte son
            self.etat.setText(_("▶ Écoute : {n}", n=e["nom"]))
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            self.etat.setText(_("Ecoute impossible sur ce poste."))
            return
        if getattr(self, "lecteur", None) is None:
            self.lecteur = QMediaPlayer(self)
            self._sortie_son = QAudioOutput(self)
            self.lecteur.setAudioOutput(self._sortie_son)
        self.lecteur.setSource(QUrl.fromLocalFile(T.chemin(self.params, e)))
        self.lecteur.play()
        self.etat.setText(_("▶ Écoute : {n}", n=e["nom"]))

    def raccourcir(self):
        e = self._entree()
        if not e:
            return
        from PySide6.QtWidgets import QDoubleSpinBox
        d = QDialog(self)
        d.setWindowTitle(_("Raccourcir « {n} »", n=e["nom"]))
        f = QFormLayout(d)
        duree = float(e.get("duree") or 0) or 10.0
        aide = QLabel(_("Gardez seulement le morceau utile (de … à …). Écoutez avant de garder."))
        aide.setWordWrap(True)
        f.addRow(aide)
        a, b = QDoubleSpinBox(), QDoubleSpinBox()
        for w, v in ((a, 0.0), (b, duree)):
            w.setRange(0.0, duree)
            w.setDecimals(2)
            w.setSingleStep(0.1)
            w.setSuffix(" s")
            w.setValue(v)
        f.addRow(_("Début"), a)
        f.addRow(_("Fin"), b)
        be = QPushButton("▶ " + _("Écouter ce morceau"))

        def ecouter_morceau():
            self.ecouter()
            if getattr(self, "lecteur", None) is not None:
                self.lecteur.setPosition(int(a.value() * 1000))
                QTimer.singleShot(int(max(0.1, b.value() - a.value()) * 1000), self.lecteur.pause)
        be.clicked.connect(ecouter_morceau)
        f.addRow(be)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        f.addRow(bb)
        if d.exec() and b.value() > a.value():
            if getattr(self, "lecteur", None) is not None:
                self.lecteur.stop()
                self.lecteur.setSource(QUrl())
            self._lancer(lambda t: T.raccourcir(self.params, e["id"], a.value(), b.value()), _("Raccourci en cours…"),
                         fin=lambda r, err: (self.etat.setText("✕ " + str(err)) if err else
                                             (self.remplir_biblio(choisir=e["id"]), self.etat.setText(_("✓ « {n} » raccourci.", n=e["nom"])))))

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
    def _chercher_et_vignettes(source, texte, mode="deux"):
        from . import traduction_recherche as TR
        tr = TR.en_anglais(texte) if mode != "tel" else (texte, "tel", [])
        res = T.chercher(source, tr[0]) if mode != "tel" else []
        if mode in ("tel", "deux") and tr[0].lower() != texte.lower():          # aussi les mots tels que tapés
            vus = {r.get("url") for r in res}
            res += [r for r in T.chercher(source, texte) if r.get("url") not in vus]
        note = TR.message(texte, tr) if mode != "tel" else ""
        res = [dict(r, _note=note) for r in res] or [{"_vide": True, "_note": note}]
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
        en_ligne = self.source.currentData() in ("ytdlp", "archive")
        if en_ligne:
            grille = any(r.get("_vignette") for r in res)
            self.resultats.setViewMode(QListWidget.IconMode if grille else QListWidget.ListMode)
            self.resultats.setIconSize(QSize(240, 135))
            self.resultats.setGridSize(QSize(260, 200) if grille else QSize())
        for r in res:
            if en_ligne and grille:                       # YouTube : vignettes comme sur le site (titre, chaîne, durée), toutes pareilles
                d = float(r.get("duree") or 0)
                it = QListWidgetItem(("▮ Short · " if r.get("short") else "") + (r.get("titre") or "")[:70] + "\n" +
                                     "  ·  ".join(b for b in (r.get("auteur") or "", f"{int(d // 60)}:{int(d % 60):02d}" if d else "") if b))
                img = QImage(r["_vignette"]) if r.get("_vignette") else QImage()
                if img.isNull():                          # image non reçue : une case grise, le résultat reste visible
                    px = QPixmap(240, 135)
                    px.fill(Qt.darkGray)
                else:
                    px = QPixmap.fromImage(img.scaled(240, 135, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                it.setIcon(QIcon(px))
                it.setSizeHint(QSize(250, 195))
                it.setData(Qt.UserRole, r)
                it.setToolTip(f"{r.get('titre')}\n{r.get('page') or ''}")
                self.resultats.addItem(it)
                continue
            if en_ligne:                      # liste : titre entier, chaîne, durée, année, licence (Creative Commons mise en avant)
                d = float(r.get("duree") or 0)
                bouts = [("▮ Short  " if r.get("short") else "") + (r.get("titre") or ""), r.get("auteur") or "", f"{int(d // 60)}:{int(d % 60):02d}" if d else "", r.get("annee") or "",
                         ("✓ " + r["licence"]) if r.get("licence") else ""]
                it = QListWidgetItem("  ·  ".join(b for b in bouts if b))
                it.setData(Qt.UserRole, r)
                it.setToolTip(r.get("page") or "")
                self.resultats.addItem(it)
                continue
            it = QListWidgetItem(f"{r['titre'][:40]}\n{r.get('duree') or 0:.0f} s · {r.get('auteur', '')[:24]}")
            if r.get("_vignette"):
                img = QImage(r["_vignette"])
                if not img.isNull():
                    it.setIcon(QIcon(QPixmap.fromImage(img.scaled(192, 108, Qt.KeepAspectRatio, Qt.SmoothTransformation))))
            it.setData(Qt.UserRole, r)
            it.setToolTip(f"{r['titre']}\n{r.get('licence', '')}")
            self.resultats.addItem(it)
        self.resultats.doItemsLayout()
        self.resultats.scrollToTop()
        shorts = sum(1 for r in res if r.get("short"))
        detail = _("{v} vidéo(s) et {s} Short(s), les Shorts à la fin. ", v=len(res) - shorts, s=shorts) if shorts and en_ligne else ""
        self.etat.setText((_("{n} clip(s) trouvé(s). Double-clic : ajouter à la bibliothèque et insérer.", n=len(res)) + " " + detail if res else
                           _("Rien trouvé : essayez d'autres mots, ou une autre langue de recherche.")) + ("  " + note if note else ""))

    def coller_lien(self):
        from PySide6.QtWidgets import QApplication
        lien = QApplication.clipboard().text().strip()
        if not lien.startswith(("http://", "https://")):
            self.etat.setText(_("Copiez d'abord le lien de la vidéo (clic droit sur la vidéo › Copier l'adresse), puis « Coller un lien »."))
            return
        self.question.setText(lien)
        self.chercher()

    # ---- orthographe : « Vouliez-vous dire … ? » (comme la recherche de YouTube)
    def _verifier_orthographe(self, texte):
        from . import videos_en_ligne as VL
        self.suggestion.hide()
        t = Tache(lambda tache: VL.correction(texte, VL.suggestions(texte)), _("Orthographe"))
        self.taches.append(t)

        def fin(r, err):
            try:
                if r and not err and self.question.text().strip() == texte:
                    self.suggestion.setText(_("Vouliez-vous dire <a href='{c}'><b>{c}</b></a> ? Cliquez pour chercher ainsi.", c=r))
                    self.suggestion.show()
            except RuntimeError:
                pass
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _prendre_suggestion(self, texte):
        self.question.setText(texte)
        self.suggestion.hide()
        self.chercher()

    # ---- regarder dans PhilCut et choisir le morceau
    def regarder(self):
        it = self.resultats.currentItem()
        r = it.data(Qt.UserRole) if it else None
        if not r or r.get("source") not in ("youtube", "archive"):
            self.etat.setText(_("Choisissez d'abord une vidéo dans la liste."))
            return
        from . import videos_en_ligne as VL
        if r.get("source") == "youtube" and not self._ytdlp_pret():
            return
        self.etat.setText(_("Préparation de la lecture de « {t} »…", t=(r.get("titre") or "")[:60]))

        def adresse(t):
            if r["source"] == "archive":
                return VL.fichier_archive(r["ident"])[0]
            return VL.flux_lecture(r["page"])

        def fin(url, err):
            if err or not url:
                self.etat.setText(_("✕ Lecture impossible ici : {e}. « page » ouvre la vidéo dans le navigateur.", e=str(err)[:200]))
                return
            self.etat.setText("")
            d = DialogueVisionner(self, url, r, _lire_temps_txt(self.morceau_de.text()), _lire_temps_txt(self.morceau_a.text()))
            if d.exec() == QDialog.Accepted:
                self.morceau_de.setText(_tc_court(d.debut))
                self.morceau_a.setText(_tc_court(d.fin))
                self.etat.setText(_("Morceau choisi : de {a} à {b} ({d:.1f} s). « Ajouter à ma bibliothèque » ne télécharge que lui.",
                                    a=_tc_court(d.debut), b=_tc_court(d.fin), d=d.fin - d.debut))
        self._lancer(adresse, None, fin=fin)

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
        if r.get("source") in ("youtube", "archive"):
            self._ajouter_en_ligne(r, inserer)
            return

        def apres(e=None):
            if inserer and e:
                self.poser_entree(e)
        self._lancer(lambda t: T.telecharger(self.params, r, progression=lambda f: t.avancer(f), arret=t.arret_demande),
                     _("Téléchargement de « {t} »…", t=r["titre"]), fin_entree=apres)

    # ------------------------------------------------------------------ yt-dlp et Internet Archive
    def _ytdlp_pret(self):
        """Accord sur ce qui est permis (une fois), puis installation de yt-dlp si besoin."""
        from . import videos_en_ligne as VL
        if not self.params.get("ytdlp_accord"):
            d = QDialog(self)
            d.setWindowTitle(_("Vidéos en ligne : ce qui est permis"))
            v = QVBoxLayout(d)
            l = QLabel(VL.LEGAL)
            l.setWordWrap(True)
            l.setTextFormat(Qt.RichText)
            l.setMinimumWidth(560)
            v.addWidget(l)
            c = QCheckBox(VL.CONFIRMATION)
            c.setStyleSheet("font-weight:600")
            v.addWidget(c)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            bb.button(QDialogButtonBox.Ok).setEnabled(False)
            c.toggled.connect(bb.button(QDialogButtonBox.Ok).setEnabled)
            bb.accepted.connect(d.accept)
            bb.rejected.connect(d.reject)
            v.addWidget(bb)
            if not d.exec():
                return False
            self.params["ytdlp_accord"] = True
            self.params.enregistrer()
        if not VL.ytdlp_installe():
            if QMessageBox.question(self, _("Installer yt-dlp"), _("yt-dlp, le programme libre qui lit les vidéos en ligne, n'est pas encore sur "
                                                                  "ce poste. Le télécharger depuis son dépôt officiel (github.com/yt-dlp, "
                                                                  "environ 18 Mo) ?")) != QMessageBox.Yes:
                return False
            def les_deux(t):                       # yt-dlp, puis Deno qu'il lui faut maintenant pour YouTube
                VL.installer_ytdlp(progression=lambda f: t.avancer(f * 0.3, _("Installation de yt-dlp…")), arret=t.arret_demande)
                if not VL.deno_installe():
                    VL.installer_deno(progression=lambda f: t.avancer(0.3 + f * 0.7, _("Installation de Deno (lecteur de YouTube)…")),
                                      arret=t.arret_demande)
            self._lancer(les_deux, _("Installation de yt-dlp…"),
                         fin=lambda r, err: self.etat.setText("✕ " + str(err) if err else _("✓ yt-dlp installé : relancez la recherche.")))
            return False
        if not VL.deno_installe():
            if QMessageBox.question(self, _("Installer Deno"), _("Pour lire et télécharger les vidéos YouTube, yt-dlp a maintenant besoin de "
                                                                "Deno, un petit programme libre (dépôt officiel github.com/denoland, "
                                                                "environ 45 Mo), rangé dans le dossier de PhilCut. L'installer ?")) != QMessageBox.Yes:
                return True                          # la recherche marche sans lui ; la lecture dira ce qu'il faut
            self._lancer(lambda t: VL.installer_deno(progression=lambda f: t.avancer(f, _("Installation de Deno (lecteur de YouTube)…")),
                                                     arret=t.arret_demande), _("Installation de Deno…"),
                         fin=lambda r, err: self.etat.setText("✕ " + str(err) if err else _("✓ Deno installé : vous pouvez regarder et "
                                                                                           "télécharger les vidéos YouTube.")))
            return False
        return True

    def maj_ytdlp(self):
        from . import videos_en_ligne as VL
        if not VL.ytdlp_installe():
            self._ytdlp_pret()
            return
        def travail(t):
            r = VL.mettre_a_jour_ytdlp()
            if not VL.deno_installe():
                VL.installer_deno(progression=lambda f: t.avancer(f, _("Installation de Deno (lecteur de YouTube)…")), arret=t.arret_demande)
            return r
        self._lancer(travail, _("Mise à jour de yt-dlp…"),
                     fin=lambda r, err: self.etat.setText("✕ " + str(err) if err else _("✓ yt-dlp à jour.")))

    def _ajouter_en_ligne(self, r, inserer):
        from . import videos_en_ligne as VL
        a, b = T.lire_temps(self.morceau_de.text()), T.lire_temps(self.morceau_a.text())
        if b is not None and a is None:
            a = 0.0
        duree = float(r.get("duree") or 0)
        sans_morceau = a is None or b is None
        if sans_morceau and (duree > 300 or (r.get("source") == "archive" and duree == 0)):
            self.etat.setText(_("Vidéo longue ({m} min) : indiquez le morceau à garder (de … à …), seul ce morceau est téléchargé.",
                                m=int(duree // 60) or "?"))
            self.morceau_de.setFocus()
            return
        if a is not None and b is not None and b <= a:
            self.etat.setText(_("Le morceau doit finir après son début."))
            return
        audio = self.audio_seul.isChecked() and r.get("source") == "youtube"
        params = self.params
        mots = [m for m in self.question.text().split() if len(m) > 2 and not m.startswith("http")]

        def travail(t):
            d = tempfile.mkdtemp(prefix="philcut-en-ligne-")
            if r["source"] == "youtube":
                f = VL.telecharger(r["page"], d, audio, a, b, progression=t.avancer, arret=t.arret_demande,
                                  hauteur=int(self.params.get("ytdlp_hauteur") or 1080))
            elif a is not None:
                from . import moteur
                url, _taille = VL.fichier_archive(r["ident"])
                f = os.path.join(d, "extrait.mp4")
                t.avancer(0.1, _("Lecture du morceau sur archive.org…"))
                moteur.lancer(["-y", "-ss", f"{a:.2f}", "-i", url, "-t", f"{b - a:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", f])
            else:
                f = VL.telecharger_archive(r["ident"], d, progression=lambda x: t.avancer(x), arret=t.arret_demande)
            e = T.ajouter_fichier(params, f, (r.get("titre") or "")[:60], mots + [r["source"]])
            T.modifier(params, e["id"], auteur=r.get("auteur") or "", licence=r.get("licence") or "", page=r.get("page") or "", source=r["source"])
            import shutil
            shutil.rmtree(d, ignore_errors=True)
            e.update(auteur=r.get("auteur") or "", licence=r.get("licence") or "", page=r.get("page") or "")
            return e

        def apres(e=None):
            if inserer and e:
                self.poser_entree(e)
        self._lancer(travail, _("Téléchargement de « {t} »…", t=(r.get("titre") or "")[:50]), fin_entree=apres)

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
        t.fini.connect(termine, Qt.QueuedConnection)        # toujours exécuté dans le fil de l'interface
        t.start()

    def reject(self):
        self._fermer()
        super().reject()

    def accept(self):
        self._fermer()
        super().accept()

    def _fermer(self):
        self.minuterie.stop()                       # une création en cours continue en tâche de fond (barre du bas)


# ---------------------------------------------------------------------- où et comment poser un tampon (0.9.9)
QUAND = {"ligne": _("À la ligne rouge (l'instant affiché)"), "debut": _("Au tout début du film"), "zone": _("À la place de la partie en jaune"),
         "fin": _("À la fin du film")}
COMMENT = {"inserer": _("Insérer : le film s'écarte, la suite est décalée"), "dessus": _("Par-dessus : il recouvre le film, rien n'est décalé")}
AJUSTER = {"garder": _("Garder sa durée"), "vitesse": _("L'accélérer ou le ralentir pour remplir la partie"),
           "couper": _("Le couper à la durée de la partie")}


CADRAGES = {"contenir_flou": _("Entier, sur un fond flou de lui-même (conseillé)"), "contenir_noir": _("Entier, avec des bandes noires"),
            "remplir": _("Remplir l'image en recadrant, partie gardée au centre"), "remplir_g": _("Remplir en recadrant, partie gardée à gauche"),
            "remplir_d": _("Remplir en recadrant, partie gardée à droite"), "suivi": _("Remplir en suivant la personne (recadrage automatique)")}


def _format(l, h):
    if not l or not h:
        return ""
    r = l / h
    for nom, v in (("16:9", 16 / 9), ("9:16", 9 / 16), ("1:1", 1.0), ("4:3", 4 / 3), ("3:4", 3 / 4), ("21:9", 21 / 9)):
        if abs(r - v) < 0.04:
            return nom
    return f"{l}×{h}"


def placement_defaut(params):
    d = dict(params.get("tampons_placement") or {})
    return {"quand": d.get("quand", "ligne"), "comment": d.get("comment", "inserer"), "ajuster": d.get("ajuster", "garder"),
            "son": d.get("son", True) is not False, "demander": d.get("demander", True) is not False,
            "cadrage": d.get("cadrage", "contenir_flou")}


class DialoguePlacement(QDialog):
    """« Où mettre ce tampon ? » : quand (début, ligne rouge, partie en jaune, fin), comment (insérer ou par-dessus), et
    si la durée ne correspond pas à la partie en jaune : garder, accélérer/ralentir, couper. Le choix est retenu."""

    def __init__(self, parent, ed, e):
        super().__init__(parent)
        from PySide6.QtWidgets import QButtonGroup, QGroupBox, QRadioButton
        self.ed, self.e = ed, e
        self.params = ed.params
        self.duree = float(e.get("duree") or 0) or 2.0
        self.son = e.get("genre") == "son"
        tl = ed.timeline
        self.zone = tl.zone_valide() if hasattr(tl, "zone_valide") else None
        self.position = float(tl.position or 0.0)
        self.fin_film = float(ed.projet.duree() or 0.0)
        d = placement_defaut(self.params)
        self.setWindowTitle(_("Où mettre « {n} » ?", n=e["nom"]))
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        tete = QLabel(_("<b>{n}</b> · {d:.1f} s", n=e["nom"], d=self.duree))
        v.addWidget(tete)
        g1 = QGroupBox(_("Quand"))
        v1 = QVBoxLayout(g1)
        self.g_quand = QButtonGroup(self)
        libs = {"ligne": f"{QUAND['ligne']} — {_tc(self.position)}", "debut": f"{QUAND['debut']} — 0:00.0",
                "zone": (f"{QUAND['zone']} — {_tc(self.zone[0])} → {_tc(self.zone[1])} ({self.zone[1] - self.zone[0]:.1f} s)" if self.zone else
                         QUAND["zone"] + " — " + _("pas encore choisie")),
                "fin": f"{QUAND['fin']} — {_tc(self.fin_film)}"}
        self.r_quand = {}
        for k in ("ligne", "debut", "zone", "fin"):
            r = QRadioButton(libs[k])
            r.setEnabled(k != "zone" or bool(self.zone))
            if k == "zone" and not self.zone:
                r.setToolTip(_("Choisir une partie : double-clic sur la règle des temps au début, puis à la fin ; elle devient jaune"))
            self.g_quand.addButton(r)
            self.r_quand[k] = r
            v1.addWidget(r)
        quand = d["quand"] if (d["quand"] != "zone" or self.zone) else "ligne"
        if self.zone:
            quand = "zone"                      # une partie en jaune est choisie : c'est sûrement là qu'on veut le tampon
        self.r_quand[quand].setChecked(True)
        v.addWidget(g1)
        self.g2 = QGroupBox(_("Comment"))
        v2 = QVBoxLayout(self.g2)
        self.g_comment = QButtonGroup(self)
        self.r_comment = {}
        for k, lib in COMMENT.items():
            r = QRadioButton(lib)
            self.g_comment.addButton(r)
            self.r_comment[k] = r
            v2.addWidget(r)
        self.r_comment.get(d["comment"], self.r_comment["inserer"]).setChecked(True)
        self.c_son = QCheckBox(_("Garder le son du tampon (sinon on entend le film)"))
        self.c_son.setChecked(d["son"])
        v2.addWidget(self.c_son)
        v.addWidget(self.g2)
        self.g2.setVisible(not self.son)
        self.g3 = QGroupBox(_("Le tampon et la partie en jaune n'ont pas la même durée"))
        v3 = QVBoxLayout(self.g3)
        self.g_ajuster = QButtonGroup(self)
        self.r_ajuster = {}
        for k, lib in AJUSTER.items():
            r = QRadioButton(lib)
            self.g_ajuster.addButton(r)
            self.r_ajuster[k] = r
            v3.addWidget(r)
        self.r_ajuster.get(d["ajuster"], self.r_ajuster["garder"]).setChecked(True)
        v.addWidget(self.g3)
        # format différent du projet (clip 16:9 dans un projet 9:16…) : comment le faire entrer
        self.fmt_tampon, self.fmt_projet = "", ""
        try:
            from . import moteur
            vi = (moteur.sonder(T.chemin(self.params, e)).get("video") or {}) if not self.son else {}
            lt, ht = vi.get("largeur") or 0, vi.get("hauteur") or 0
            if vi.get("rotation") in (90, 270, -90):
                lt, ht = ht, lt
            lp, hp = ed.projet.taille
            self.fmt_tampon, self.fmt_projet = _format(lt, ht), _format(lp, hp)
            differents = bool(lt and ht) and abs(lt / ht - lp / hp) > 0.04
        except Exception:      # noqa: BLE001
            differents = False
        self.g4 = QGroupBox(_("Le tampon est en {a}, le projet en {b} : comment le faire entrer ?", a=self.fmt_tampon, b=self.fmt_projet))
        v4 = QVBoxLayout(self.g4)
        self.g_cadrage = QButtonGroup(self)
        self.r_cadrage = {}
        for k, lib in CADRAGES.items():
            r = QRadioButton(lib)
            self.g_cadrage.addButton(r)
            self.r_cadrage[k] = r
            v4.addWidget(r)
        self.r_cadrage.get(d["cadrage"], self.r_cadrage["contenir_flou"]).setChecked(True)
        n4 = QLabel(_("Modifiable ensuite : clic sur le plan › Inspecteur › Cadrage."))
        n4.setStyleSheet("color:#9aa4b2")
        v4.addWidget(n4)
        v.addWidget(self.g4)
        self.g4.setVisible(differents)
        self.differents = differents
        self.resume = QLabel("")
        self.resume.setWordWrap(True)
        self.resume.setStyleSheet("background:#22262d;color:#e6e6e6;border-radius:6px;padding:8px")
        v.addWidget(self.resume)
        self.c_demander = QCheckBox(_("Toujours me demander (sinon : ce choix, directement, au double-clic)"))
        self.c_demander.setChecked(d["demander"])
        v.addWidget(self.c_demander)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Mettre dans le film"))
        bb.button(QDialogButtonBox.Cancel).setText(_("Annuler"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        for g in (self.g_quand, self.g_comment, self.g_ajuster, self.g_cadrage):
            g.buttonClicked.connect(lambda *_a: self._maj())
        self.c_son.toggled.connect(lambda *_a: self._maj())
        self._maj()

    def _cle(self, dico):
        for k, r in dico.items():
            if r.isChecked():
                return k
        return next(iter(dico))

    def choix(self):
        quand, comment, ajuster = self._cle(self.r_quand), self._cle(self.r_comment), self._cle(self.r_ajuster)
        t = {"ligne": self.position, "debut": 0.0, "zone": self.zone[0] if self.zone else self.position, "fin": self.fin_film}[quand]
        c = {"t": t, "quand": quand, "comment": comment, "ajuster": ajuster, "son": self.c_son.isChecked(), "src_fin": None, "vitesse": 1.0,
             "cadrage": self._cle(self.r_cadrage) if getattr(self, "differents", False) else "contenir_flou"}
        if quand == "zone" and self.zone:
            place = self.zone[1] - self.zone[0]
            if comment == "inserer":
                c["comment"] = "remplacer"
                c["zone"] = tuple(self.zone)
            if abs(place - self.duree) > 0.05:
                if ajuster == "vitesse":
                    c["vitesse"] = round(self.duree / place, 3)
                elif ajuster == "couper" and self.duree > place:
                    c["src_fin"] = place
        return c

    def _maj(self):
        c = self.choix()
        ecart = bool(self.zone) and c["quand"] == "zone" and abs((self.zone[1] - self.zone[0]) - self.duree) > 0.05
        self.g3.setVisible(ecart and not self.son)
        self.c_son.setVisible(c["comment"] == "dessus")
        if hasattr(self, "g4"):
            self.g4.setVisible(self.differents and c["comment"] != "dessus")
        if ecart:
            self.g3.setTitle(_("Le tampon dure {d:.1f} s, la partie en jaune {p:.1f} s", d=self.duree, p=self.zone[1] - self.zone[0]))
            self.r_ajuster["couper"].setEnabled(self.duree > self.zone[1] - self.zone[0])
        duree = (c["src_fin"] or self.duree) / c["vitesse"]
        if self.son:
            txt = _("Le son est posé à {t} sur une piste de sons libre, sans rien décaler.", t=_tc(c["t"]))
        elif c["comment"] == "remplacer":
            txt = _("La partie en jaune ({a} → {b}) est retirée et le tampon prend sa place ({d:.1f} s).", a=_tc(self.zone[0]), b=_tc(self.zone[1]),
                    d=duree)
            ecart_fin = duree - (self.zone[1] - self.zone[0])
            if abs(ecart_fin) > 0.05:
                txt += " " + (_("La suite du film est repoussée de {s:.1f} s.", s=ecart_fin) if ecart_fin > 0 else
                              _("La suite du film est avancée de {s:.1f} s.", s=-ecart_fin))
        elif c["comment"] == "dessus":
            txt = _("Le tampon recouvre le film de {a} à {b} ({d:.1f} s) ; le film continue dessous, rien n'est décalé.",
                    a=_tc(c["t"]), b=_tc(c["t"] + duree), d=duree)
        else:
            txt = _("Le tampon est inséré à {t} ({d:.1f} s) : tout ce qui suit est décalé de {d:.1f} s.", t=_tc(c["t"]), d=duree)
        if c["vitesse"] != 1.0:
            txt += " " + (_("Il est accéléré (×{v:.2f}).", v=c["vitesse"]) if c["vitesse"] > 1 else _("Il est ralenti (×{v:.2f}).", v=c["vitesse"]))
        if c["src_fin"]:
            txt += " " + _("Il est coupé à {s:.1f} s.", s=c["src_fin"])
        self.resume.setText(txt)

    def demander(self):
        """Renvoie le choix (dict) ou None ; sans demander si l'utilisateur l'a réglé ainsi."""
        if not placement_defaut(self.params)["demander"]:
            return self.choix()
        if self.exec() != QDialog.Accepted:
            return None
        c = self.choix()
        self.params["tampons_placement"] = {"quand": c["quand"], "comment": self._cle(self.r_comment), "ajuster": c["ajuster"], "son": c["son"],
                                            "demander": self.c_demander.isChecked(),
                                            "cadrage": c["cadrage"] if self.differents else placement_defaut(self.params)["cadrage"]}
        try:
            self.params.enregistrer()
        except AttributeError:
            pass
        return c


def _tc_court(t):
    t = max(0.0, float(t or 0))
    m, s_ = divmod(t, 60)
    return f"{int(m)}:{s_:04.1f}" if s_ % 1 else f"{int(m)}:{int(s_):02d}"


def _lire_temps_txt(texte):
    try:
        return T.lire_temps(texte)
    except Exception:      # noqa: BLE001
        return None


class DialogueVisionner(QDialog):
    """Regarder une vidéo en ligne dans PhilCut (version légère) et marquer le début et la fin du morceau à importer."""

    def __init__(self, parent, url, r, debut=None, fin=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QSlider
        self.url = url
        self.duree = float(r.get("duree") or 0)
        self.debut = float(debut or 0.0)
        self.fin = float(fin) if fin else min(self.duree or 10.0, self.debut + 10.0)
        self.lecteur = None
        self.setWindowTitle(_("Regarder : {t}", t=(r.get("titre") or "")[:80]))
        self.resize(900, 620)
        v = QVBoxLayout(self)
        self.vue = QWidget()
        self.vue.setMinimumHeight(360)
        self.vue.setStyleSheet("background:#000")
        v.addWidget(self.vue, 1)
        self.curseur = QSlider(Qt.Horizontal)
        self.curseur.setRange(0, int((self.duree or 600) * 10))
        self.curseur.sliderMoved.connect(lambda x: self.lecteur and self.lecteur.setPosition(x * 100))
        v.addWidget(self.curseur)
        h = QHBoxLayout()
        self.b_lire = QPushButton("▶ " + _("Lecture"))
        self.b_lire.clicked.connect(self.basculer)
        h.addWidget(self.b_lire)
        self.temps = QLabel("0:00")
        h.addWidget(self.temps)
        h.addStretch(1)
        b = QPushButton("[ " + _("Début du morceau ici"))
        b.clicked.connect(lambda: self._marquer(True))
        h.addWidget(b)
        b = QPushButton(_("Fin du morceau ici") + " ]")
        b.clicked.connect(lambda: self._marquer(False))
        h.addWidget(b)
        v.addLayout(h)
        self.morceau = QLabel("")
        self.morceau.setStyleSheet("background:#22262d;color:#e6e6e6;border-radius:6px;padding:8px")
        v.addWidget(self.morceau)
        aide = QLabel(_("Lisez, mettez en pause au bon endroit, puis « Début du morceau ici » et « Fin du morceau ici ». Seul ce morceau "
                        "sera téléchargé."))
        aide.setWordWrap(True)
        aide.setStyleSheet("color:#9aa4b2")
        v.addWidget(aide)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText(_("Garder ce morceau"))
        bb.button(QDialogButtonBox.Cancel).setText(_("Annuler"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self._maj_morceau()
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":      # tests automatiques : pas de lecture réelle
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtMultimediaWidgets import QVideoWidget
        except ImportError:
            self.morceau.setText(_("Lecture impossible sur ce poste."))
            return
        lay = QVBoxLayout(self.vue)
        lay.setContentsMargins(0, 0, 0, 0)
        self.video = QVideoWidget()
        lay.addWidget(self.video)
        self.lecteur = QMediaPlayer(self)
        self.sortie = QAudioOutput(self)
        self.lecteur.setAudioOutput(self.sortie)
        self.lecteur.setVideoOutput(self.video)
        self.lecteur.positionChanged.connect(self._position)
        self.lecteur.durationChanged.connect(lambda d: d > 0 and self.curseur.setRange(0, int(d / 100)))
        self.lecteur.setSource(QUrl(url))
        self.lecteur.setPosition(int(self.debut * 1000))
        self.lecteur.play()
        self.b_lire.setText("❚❚ " + _("Pause"))

    def position(self):
        return (self.lecteur.position() / 1000.0) if self.lecteur is not None else self.curseur.value() / 10.0

    def _position(self, ms):
        if not self.curseur.isSliderDown():
            self.curseur.setValue(int(ms / 100))
        self.temps.setText(_tc_court(ms / 1000.0))

    def basculer(self):
        if self.lecteur is None:
            return
        from PySide6.QtMultimedia import QMediaPlayer
        if self.lecteur.playbackState() == QMediaPlayer.PlayingState:
            self.lecteur.pause()
            self.b_lire.setText("▶ " + _("Lecture"))
        else:
            self.lecteur.play()
            self.b_lire.setText("❚❚ " + _("Pause"))

    def _marquer(self, debut):
        t = self.position()
        if debut:
            self.debut = t
            if self.fin <= t:
                self.fin = t + 10.0
        else:
            self.fin = max(t, self.debut + 0.5)
        self._maj_morceau()

    def _maj_morceau(self):
        self.morceau.setText(_("Morceau à importer : de <b>{a}</b> à <b>{b}</b> ({d:.1f} s)", a=_tc_court(self.debut), b=_tc_court(self.fin),
                               d=self.fin - self.debut))

    def done(self, r):
        if self.lecteur is not None:
            self.lecteur.stop()
            self.lecteur.setSource(QUrl())
        super().done(r)
