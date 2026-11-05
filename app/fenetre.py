"""La fenetre principale de PhilCut : onglet Accueil + un onglet par projet, menus, barre personnalisable, session
partagee entre postes, mises a jour proposees, Fabrique, export, sous-titres, musique.

Memes regles que PhilPDF : rien de bloquant au demarrage, propositions laissees sur l'Accueil, encart de
progression non bloquant, journaux depuis l'Aide, mises a jour proposees jamais imposees."""
import datetime, os, subprocess, sys, webbrowser

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QKeySequence, QDesktopServices
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QMessageBox, QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QDialogButtonBox, QPlainTextEdit, QApplication, QInputDialog, QMenu, QWidget)

from . import mise_a_jour, moteur, outils as O, theme, fabrique as FAB
from .accueil import PageAccueil
from .config import Parametres, VERSION, est_portable, EXTENSION_PROJET, est_video, est_audio, est_image, dossier_donnees
from .editeur import Editeur, Encart
from .widgets import question_fr
from .icones import icone, logo
from .langue import _
from .projet import Projet
from .taches import Tache
from .widgets import boutons_fr


class Fenetre(QMainWindow):
    def __init__(self, fichiers=()):
        super().__init__()
        self.params = Parametres()
        self.setWindowTitle("PhilCut")
        self.setWindowIcon(logo(64))
        self.setAcceptDrops(True)
        self.resize(1480, 920)
        self.onglets = QTabWidget()
        self.onglets.setDocumentMode(True)
        self.onglets.setTabsClosable(True)
        self.onglets.setMovable(True)
        self.onglets.tabCloseRequested.connect(self.fermer_onglet)
        self.onglets.setStyleSheet("QTabBar::tab{padding:9px 18px;font-size:13px} QTabWidget::pane{border:none}")
        self.accueil = PageAccueil(self.params)
        self.accueil.nouveau.connect(self.nouveau_projet)
        self.accueil.ouvrir.connect(self.ouvrir)
        self.accueil.ouvrir_dialogue.connect(self.dialogue_ouvrir)
        self.accueil.importer_rushes.connect(self.rushes_vers_projet)
        self.accueil.action_fichier.connect(self.action_fichier)
        self.onglets.addTab(self.accueil, icone("ouvrir", theme.COULEURS["texte2"]), _("Accueil"))
        self.onglets.tabBar().setTabButton(0, self.onglets.tabBar().ButtonPosition.RightSide, None)
        self.setCentralWidget(self.onglets)
        self.taches = []
        self.encart_global = Encart(self)          # progression visible même sans projet ouvert (téléchargements…)
        self.statusBar().addPermanentWidget(self.encart_global, 1)
        from .telechargements import GestionTelechargements
        from . import activite
        self.telechargements = GestionTelechargements(self.params, self)
        self.fenetre_telech = None
        self.centre = activite.centre()
        self.centre.telechargements = self.telechargements
        # barre d'information : toujours là, dit ce qui se passe ; un clic ouvre le Centre d'activité
        self.b_activite = QPushButton(_("Prêt"))
        self.b_activite.setFlat(True)
        self.b_activite.setCursor(Qt.PointingHandCursor)
        self.b_activite.setToolTip(_("Ce que PhilCut fait en ce moment (imports, exports, IA, téléchargements). Clic : le détail."))
        self.b_activite.clicked.connect(self.voir_activite)
        self.statusBar().addPermanentWidget(self.b_activite)
        self.fenetre_activite = None
        self.centre.change.connect(self._etat_activite)
        self.telechargements.change.connect(self._etat_activite)
        self.telechargements.termine.connect(self._telech_termine)
        self._minut_activite = QTimer(self)
        self._minut_activite.timeout.connect(self._etat_activite)
        self._minut_activite.start(1000)
        self._menus()
        self.statusBar().showMessage(_("PhilCut {v}", v=VERSION) + (_(" · version portable") if est_portable() else "") +
                                     (_(" · FFmpeg {f}", f=moteur.version()) if moteur.disponible() else _(" · FFmpeg INTROUVABLE : import et export impossibles")))
        for f in fichiers:
            self.ouvrir(f)
        if not moteur.disponible():
            QTimer.singleShot(800, lambda: self.accueil.proposer(_("FFmpeg est introuvable : PhilCut en a besoin pour lire et fabriquer les vidéos. "
                                                                   "Le paquet tout-en-un l'embarque dans le dossier « bin » ; sinon installez-le et relancez."), _("Voir comment"),
                                                                 lambda: webbrowser.open("https://github.com/PhilouElChapo/PhilCut#ffmpeg")))
        if getattr(self.params, "nouveau", False) or not self.params.get("bienvenue_vue"):
            QTimer.singleShot(600, self.bienvenue)
        if self.params.get("maj_auto", True) and self.params.get("maj_derniere") != datetime.date.today().isoformat():
            self.params["maj_derniere"] = datetime.date.today().isoformat()
            self.params.enregistrer()
            QTimer.singleShot(3000, lambda: self.verifier_maj(silencieux=True))
        QTimer.singleShot(1500, self.verifier_session)
        self._minuterie = QTimer(self)
        self._minuterie.timeout.connect(self.ecrire_session)
        self._minuterie.start(60000)
        from .journal import noter_version
        noter_version(VERSION)

    # ---------------------------------------------------------------- menus
    def _menus(self):
        mb = self.menuBar()
        m = mb.addMenu(_("&Fichier"))
        m.addAction(icone("clap"), _("Nouveau projet 16:9"), lambda: self.nouveau_projet("16:9"), QKeySequence.New)
        m.addAction(icone("format"), _("Nouveau projet 9:16"), lambda: self.nouveau_projet("9:16"))
        m.addAction(icone("ouvrir"), _("Ouvrir un projet…"), self.dialogue_ouvrir, QKeySequence.Open)
        self.menu_recents = m.addMenu(_("Projets récents"))
        self.menu_recents.aboutToShow.connect(self._remplir_recents)
        m.addSeparator()
        m.addAction(icone("importer"), _("Importer des rushes…"), lambda: self._editeur_ou_nouveau().importer(), "Ctrl+I")
        m.addSeparator()
        m.addAction(icone("enregistrer"), _("Enregistrer"), self.enregistrer, QKeySequence.Save)
        m.addAction(_("Enregistrer sous…"), lambda: self.enregistrer(sous=True), "Ctrl+Shift+S")
        m.addSeparator()
        m.addAction(icone("exporter"), _("Exporter la vidéo…"), self.exporter, "Ctrl+E")
        m.addSeparator()
        m.addAction(_("Fermer le projet"), lambda: self.fermer_onglet(self.onglets.currentIndex()), "Ctrl+W")
        m.addAction(_("Quitter"), self.close, QKeySequence.Quit)
        e = mb.addMenu(_("&Edition"))
        e.addAction(icone("annuler"), _("Annuler|action"), lambda: self._ed(lambda ed: ed.annuler()), QKeySequence.Undo)
        e.addAction(icone("retablir"), _("Rétablir"), lambda: self._ed(lambda ed: ed.refaire()), "Ctrl+Y")
        e.addSeparator()
        e.addAction(icone("couper"), _("Couper au curseur"), lambda: self._ed(lambda ed: ed.timeline.couper_au_curseur()), "C")
        e.addAction(icone("supprimer"), _("Supprimer et refermer"), lambda: self._ed(lambda ed: ed.timeline.supprimer_selection(True)))
        e.addAction(_("Resserrer la piste vidéo (supprimer les trous)"), lambda: self._ed(lambda ed: (ed.projet.marquer(), ed.projet.resserrer("video"), ed.rafraichir())))
        e.addSeparator()
        e.addAction(icone("parametres"), _("Préférences…"), self.preferences, "Ctrl+,")
        a = mb.addMenu(_("&Affichage"))
        a.addAction(_("Lecture / pause"), lambda: self._ed(lambda ed: ed.apercu.basculer()), "Space")
        a.addAction(_("Tout voir dans la timeline"), lambda: self._ed(lambda ed: ed.timeline.ajuster()), "Ctrl+0")
        a.addAction(_("Zoom avant"), lambda: self._ed(lambda ed: ed.timeline.zoomer(1.3)), "Ctrl++")
        a.addAction(_("Zoom arrière"), lambda: self._ed(lambda ed: ed.timeline.zoomer(1 / 1.3)), "Ctrl+-")
        a.addAction(_("Lire avec les effets (▶✦ : 15 s préparées puis lues ici)"), lambda: self._ed(lambda ed: ed.lire_rendu()), "Shift+Space")
        af = a.addAction(_("Image fidèle à l'arrêt (effets, transitions, textes rendus)"))
        af.setCheckable(True)
        af.setChecked(bool(self.params.get("apercu_fidele", True)))
        af.toggled.connect(lambda on: self._ed(lambda ed: ed.b_fidele.setChecked(on)))
        a.addSeparator()
        a.addAction(_("Images de la timeline plus grandes (Alt + molette)"), lambda: self._ed(lambda ed: ed.timeline.hauteur_images(1.3)), "Alt++")
        a.addAction(_("Images de la timeline plus petites"), lambda: self._ed(lambda ed: ed.timeline.hauteur_images(1 / 1.3)), "Alt+-")
        a.addSeparator()
        a.addAction(_("Volet de droite : complet / icônes / masqué"), lambda: self._ed(lambda ed: ed.basculer_volet()), "F4")
        a.addAction(_("Personnaliser la barre d'outils…"), self.personnaliser_barre)
        mo = mb.addMenu(_("&Montage"))
        for oid in ("vitesse", "recadrer", "stabiliser", "texte", "effets", "goodies", "sous_titres", "musique", "voix"):
            o = O.outil(oid)
            mo.addAction(icone(o[2]), o[3], lambda _c=False, oid=oid: self._editeur_ou_nouveau().outil(oid))
        mo.addSeparator()
        mo.addAction(_("Ajouter une piste vidéo au-dessus (incrustation, image dans l'image)"), lambda: self._ed(lambda ed: ed.timeline._ajouter_piste("video")))
        mo.addAction(_("Ajouter une piste de musique ou de sons"), lambda: self._ed(lambda ed: ed.timeline._ajouter_piste("audio")))
        mo.addSeparator()
        mo.addAction(_("Début de la partie à sélectionner (au curseur)"), lambda: self._ed(lambda ed: ed.timeline.marquer_zone(0)), "I")
        mo.addAction(_("Fin de la partie à sélectionner (au curseur)"), lambda: self._ed(lambda ed: ed.timeline.marquer_zone(1)), "O")
        mo.addAction(_("Supprimer la partie sélectionnée (la suite se recolle)"), lambda: self._ed(lambda ed: ed.partie(False)))
        mo.addAction(_("Garder seulement la partie sélectionnée"), lambda: self._ed(lambda ed: ed.partie(True)))
        mo.addSeparator()
        mo.addAction(_("Caler les coupes sur les temps de la musique"), lambda: self._ed(lambda ed: ed.caler_rythme(False)))
        mo.addAction(_("Caler les coupes sur les débuts de mesure (plus posé)"), lambda: self._ed(lambda ed: ed.caler_rythme(True)))
        asst = mb.addMenu(_("A&ssistant"))
        asst.addAction(icone("assistant"), _("Analyser et proposer un montage"), lambda: self._editeur_ou_nouveau().outil("assistant"), "Ctrl+Shift+A")
        asst.addAction(icone("info"), _("Fiche vidéo du plan sélectionné"), lambda: self._ed(lambda ed: ed.outil("fiche")))
        asst.addAction(_("Changer le niveau (sans IA, locale, cloud)…"), lambda: self.preferences("Assistant"))
        asst.addAction(_("Connecter une IA (obtenir et tester ma clef)…"), self.connecter_ia)
        fb = mb.addMenu(_("Fa&brique"))
        fb.addAction(icone("fabrique"), _("Logo, intro, fin, plan IA…"), self.fabrique, "Ctrl+Shift+F")
        fb.addAction(_("Atelier de logo (créer, modifier, idées par l'IA)…"), self.atelier_logo)
        ou = mb.addMenu(_("&Outils"))
        ou.addAction(_("Publier (YouTube, Instagram, TikTok…)…"), self.publier)
        ou.addAction(icone("nuage"), _("Déposer l'export sur le Drive / NAS…"), self.partager)
        ou.addAction(_("Synchroniser maintenant"), self.ecrire_session)
        ou.addAction(_("Centre d'activité (tâches en cours, téléchargements)…"), self.voir_activite)
        ou.addAction(_("Journal des échanges (Drives, IA)…"), self.journal_echanges)
        ou.addAction(_("Ouvrir le dossier des données"), lambda: self.ouvrir_externe(dossier_donnees()))
        ai = mb.addMenu(_("&Aide"))
        ai.addAction(_("Raccourcis clavier"), self.raccourcis)
        ai.addAction(_("Guide de test de la première version"), lambda: webbrowser.open("https://github.com/PhilouElChapo/PhilCut/blob/main/docs/guideline-tests.md"))
        ai.addAction(_("Vérifier les mises à jour…"), lambda: self.verifier_maj(silencieux=False))
        ai.addAction(_("Site du projet (GitHub)"), lambda: webbrowser.open("https://github.com/PhilouElChapo/PhilCut"))
        ai.addSeparator()
        ai.addAction(_("A propos de PhilCut"), self.a_propos)

    def _remplir_recents(self):
        self.menu_recents.clear()
        for p in (self.params.get("recents") or [])[:15]:
            self.menu_recents.addAction(os.path.basename(p), lambda p=p: self.ouvrir(p))

    # ---------------------------------------------------------------- projets et onglets
    def editeur_courant(self):
        w = self.onglets.currentWidget()
        return w if isinstance(w, Editeur) else None

    def editeurs(self):
        return [self.onglets.widget(i) for i in range(self.onglets.count()) if isinstance(self.onglets.widget(i), Editeur)]

    def _ed(self, f):
        ed = self.editeur_courant()
        if ed:
            f(ed)

    def _editeur_ou_nouveau(self):
        ed = self.editeur_courant()
        if not ed:
            ed = self.nouveau_projet("16:9")
        return ed

    def nouveau_projet(self, format_="16:9", nom=None):
        n = nom or _("Projet {d}", d=datetime.datetime.now().strftime("%d-%m-%Y %Hh%M"))
        p = Projet(n, format_)
        return self.ajouter_onglet(p)

    def ajouter_onglet(self, projet):
        ed = Editeur(self, projet, self.params)
        ed.titre_change.connect(lambda ed=ed: self._maj_titre(ed))
        ed.demande_outil.connect(self.outil_global)
        i = self.onglets.addTab(ed, icone("projet", theme.COULEURS["accent"]), projet.nom)
        self.onglets.setCurrentIndex(i)
        ed.appliquer_volet()
        return ed

    def _maj_titre(self, ed):
        i = self.onglets.indexOf(ed)
        if i >= 0:
            self.onglets.setTabText(i, ed.projet.nom + (" •" if ed.projet.modifie else ""))

    def rushes_vers_projet(self):
        filtres = _("Vidéos, sons, images") + " (*.mp4 *.mov *.mkv *.m4v *.webm *.avi *.mts *.m2ts *.3gp *.mp3 *.wav *.m4a *.jpg *.jpeg *.png *.heic);;" + _("Tous") + " (*)"
        chemins, _f = QFileDialog.getOpenFileNames(self, _("Rushes du nouveau projet"), self.params.get("dernier_dossier") or "", filtres)
        if not chemins:
            return
        vert = sum(1 for c in chemins if c.lower().endswith(".mp4") and False)
        ed = self.nouveau_projet("16:9", os.path.splitext(os.path.basename(chemins[0]))[0])
        ed.importer(chemins)
        ed.outil("assistant")

    def dialogue_ouvrir(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Ouvrir"), self.params.get("dernier_dossier") or "",
                                            _("Projets PhilCut et vidéos") + " (*.philcut *.mp4 *.mov *.mkv *.m4v *.webm *.avi *.mts *.m2ts *.3gp)")
        if p:
            self.ouvrir(p)

    def ouvrir(self, chemin):
        if not os.path.exists(chemin):
            QMessageBox.warning(self, _("Ouvrir"), _("Introuvable : {p}", p=chemin))
            return None
        if chemin.lower().endswith(EXTENSION_PROJET):
            for ed in self.editeurs():
                if ed.projet.chemin and os.path.normcase(ed.projet.chemin) == os.path.normcase(chemin):
                    self.onglets.setCurrentWidget(ed)
                    return ed
            try:
                p = Projet.ouvrir(chemin)
            except Exception as e:    # noqa: BLE001
                QMessageBox.warning(self, _("Ouvrir"), _("Ce projet n'a pas pu être lu : {e}", e=e))
                return None
            self.params.ajouter_recent(chemin)
            self.params["dernier_dossier"] = os.path.dirname(chemin)
            ed = self.ajouter_onglet(p)
            manquants = p.manquants()
            if manquants:
                ed.encart.message(_("{n} rush(es) introuvable(s) : {l}", n=len(manquants), l=", ".join(m["nom"] for m in manquants[:4])), 15000)
            # proxys et vignettes manquants : refaits en arriere-plan
            for m in p.medias:
                if m.get("genre") == "video" and os.path.exists(m["chemin"]) and (not m.get("vignettes") or not os.path.exists(m.get("vignettes") or "")):
                    ed._file_import = getattr(ed, "_file_import", [])
            self._reconstruire_medias(ed)
            self.accueil.rafraichir()
            return ed
        if est_video(chemin) or est_audio(chemin) or est_image(chemin):
            ed = self.editeur_courant() or self.nouveau_projet("16:9", os.path.splitext(os.path.basename(chemin))[0])
            ed.importer([chemin])
            return ed
        QMessageBox.information(self, _("Ouvrir"), _("PhilCut ouvre des projets .philcut et des vidéos, sons ou images."))
        return None

    def _reconstruire_medias(self, ed):
        """Au chargement d'un projet : proxys, vignettes et ondes sont refaits si absents (ils ne sont pas dans le fichier projet)."""
        from .taches import importer_media
        a_faire = [m for m in ed.projet.medias if os.path.exists(m["chemin"]) and (not m.get("vignettes") or not os.path.exists(m["vignettes"]) or
                                                                                   (m.get("genre") == "video" and self.params.get("proxys", True) and not os.path.exists(m.get("proxy") or "")))]
        if not a_faire:
            return

        def travail(tache):
            for i, m in enumerate(a_faire):
                r = importer_media(tache, m["chemin"], self.params)
                m.update(fiche=r["fiche"], proxy=r.get("proxy", ""), vignettes=r.get("vignettes", ""), onde=r.get("onde") or [], niveaux=r.get("niveaux"))
                tache.avancer((i + 1) / len(a_faire), m["nom"])
                if tache.arret:
                    break
            return True
        t = Tache(travail, _("Préparation"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Préparation des rushes (proxys, vignettes)"))
        t.fini.connect(lambda r, e: (ed.biblio.remplir(ed.projet), ed.rafraichir()))
        t.start()

    def enregistrer(self, sous=False):
        ed = self.editeur_courant()
        if not ed:
            return False
        p = ed.projet
        chemin = p.chemin
        if sous or not chemin:
            depart = os.path.join(self.params.get("dernier_dossier") or os.path.expanduser("~"), p.nom.replace("/", "-") + EXTENSION_PROJET)
            chemin, _f = QFileDialog.getSaveFileName(self, _("Enregistrer le projet"), depart, "PhilCut (*" + EXTENSION_PROJET + ")")
            if not chemin:
                return False
            p.nom = os.path.splitext(os.path.basename(chemin))[0]
        try:
            p.enregistrer(chemin)
        except OSError as e:
            QMessageBox.warning(self, _("Enregistrer"), str(e))
            return False
        # vignette du projet pour l'Accueil
        try:
            png = ed.apercu.image_courante(320)
            if png:
                with open(chemin[:-len(EXTENSION_PROJET)] + "_vignette.png", "wb") as f:
                    f.write(png)
        except Exception:
            pass
        self.params.ajouter_recent(chemin)
        self.params["dernier_dossier"] = os.path.dirname(chemin)
        self.params.enregistrer()
        self._maj_titre(ed)
        self.accueil.rafraichir()
        self.ecrire_session()
        return True

    def fermer_onglet(self, i):
        w = self.onglets.widget(i)
        if not isinstance(w, Editeur):
            return
        if w.projet.modifie:
            r = question_fr(self, _("Fermer"), _("Enregistrer les modifications de « {n} » ?", n=w.projet.nom),
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Save:
                self.onglets.setCurrentIndex(i)
                if not self.enregistrer():
                    return
        w.apercu.arreter()
        w.preparation.fermer()
        self.onglets.removeTab(i)
        w.deleteLater()
        self.ecrire_session()

    def closeEvent(self, e):
        for ed in self.editeurs():
            if ed.projet.modifie:
                self.onglets.setCurrentWidget(ed)
                r = question_fr(self, _("Quitter"), _("Enregistrer les modifications de « {n} » ?", n=ed.projet.nom),
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if r == QMessageBox.Cancel:
                    e.ignore()
                    return
                if r == QMessageBox.Save and not self.enregistrer():
                    e.ignore()
                    return
        en_cours = [t for t in self.taches + sum((ed.taches for ed in self.editeurs()), []) if t.isRunning()]
        if self.telechargements.tache is not None:
            en_cours.append(self.telechargements.tache)
        if en_cours and QMessageBox.question(self, _("Quitter"), _("{n} opération(s) en cours (export, import…). Quitter quand même ?", n=len(en_cours))) != QMessageBox.Yes:
            e.ignore()
            return
        for t in en_cours:
            t.stopper()
        for ed in self.editeurs():
            ed.apercu.arreter()
            ed.preparation.fermer()
        self.ecrire_session()
        self.params.enregistrer()
        self.attendre_taches(8000)
        e.accept()

    def attendre_taches(self, ms=30000):
        """Attend la fin des taches de fond (Qt refuse qu'un fil soit detruit en cours de route)."""
        autres = [self.telechargements.tache] if getattr(self, "telechargements", None) and self.telechargements.tache else []
        for t in list(self.taches) + sum((list(ed.taches) for ed in self.editeurs()), []) + autres:
            try:
                if t.isRunning():
                    t.stopper()
                    t.wait(ms)
            except RuntimeError:
                pass

    # ---------------------------------------------------------------- glisser-deposer sur la fenetre
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        chemins = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        projets = [c for c in chemins if c.lower().endswith(EXTENSION_PROJET)]
        medias = [c for c in chemins if est_video(c) or est_audio(c) or est_image(c)]
        for p in projets:
            self.ouvrir(p)
        if medias:
            ed = self.editeur_courant() or self.nouveau_projet("16:9", os.path.splitext(os.path.basename(medias[0]))[0])
            ed.importer(medias)

    # ---------------------------------------------------------------- outils globaux
    def outil_global(self, oid):
        if oid == "exporter":
            self.exporter()
        elif oid == "fabrique":
            self.fabrique()
        elif oid == "musique":
            self.musique()
        elif oid == "sous_titres":
            self.sous_titres()
        elif oid == "voix":
            self.voix()
        elif oid == "partager":
            self.partager()

    def exporter(self):
        ed = self.editeur_courant()
        if not ed or not ed.projet.clips:
            QMessageBox.information(self, _("Exporter"), _("Rien à exporter : posez des plans dans la timeline."))
            return
        from .dialogues_video import DialogueExport
        from . import export, titres
        d = DialogueExport(self, ed.projet, self.params)
        if d.exec() != QDialog.Accepted:
            return
        sortie = d.chemin.text().strip()
        if not sortie:
            return
        os.makedirs(os.path.dirname(sortie) or ".", exist_ok=True)
        self.params["dernier_dossier_export"] = os.path.dirname(sortie)
        self.params["export_destination"] = d.dest.currentData()
        self.params.enregistrer()
        dest, enc, qual = d.dest.currentData(), d.enc.currentData(), d.qualite.currentData()
        st = list(ed.projet.d.get("sous_titres") or [])
        ed.projet.d["ducking"] = self.params.get("ducking", True)
        import copy
        projet_copie = copy.deepcopy(ed.projet)
        travaux = [(projet_copie, sortie, dest)]
        if d.double.isChecked() and d.dest2.currentData() != dest:
            dest2 = d.dest2.currentData()
            travaux.append((export.autre_format(ed.projet, dest2), export.nom_autre(sortie, dest2), dest2))

        def travail(tache):
            journal = []
            for k, (pj, sor, de) in enumerate(travaux):
                ex = export.Exportateur(pj, sor, de, qualite=qual, encodeur=enc, params=self.params)
                try:
                    ex.lancer(progression=lambda f, k=k: tache.avancer((k + f) / len(travaux), os.path.basename(sor)),
                              arret=lambda: tache.arret, sous_titres=st)
                    if d.srt.isChecked() and st:
                        with open(os.path.splitext(sor)[0] + ".srt", "w", encoding="utf-8") as f:
                            f.write(titres.srt(st))
                    journal += ex.journal
                finally:
                    ex.nettoyer()
            return journal
        t = Tache(travail, _("Export"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Export vers {f}", f=os.path.basename(sortie)), (_("Publier…"), lambda: self.publier(sortie)))
        t.fini.connect(lambda r, e: self._exporte(sortie, r, e, d.drive.isChecked()))
        t.start()

    def publier(self, fichier=""):
        ed = self._editeur_ou_nouveau()
        from .dialogues_publication import DialoguePublier
        DialoguePublier(self, ed.projet, self.params, fichier).exec()

    def _exporte(self, sortie, journal, erreur, deposer):
        from .journal import ecrire
        if erreur:
            ecrire("export", f"✕ {sortie} : {erreur}")
            return
        ed = self.editeur_courant()
        if ed:
            ed.projet.d["dernier_export"] = sortie
        ecrire("export", f"✓ {sortie}" + (f" ({'; '.join(journal)})" if journal else ""))
        if deposer:
            self.partager(sortie)

    def ouvrir_externe(self, chemin):
        if os.path.exists(chemin):
            QDesktopServices.openUrl(QUrl.fromLocalFile(chemin))

    def action_fichier(self, chemin, action):
        if action == "dossier":
            self.ouvrir_externe(os.path.dirname(chemin))
        elif action == "retirer":
            self.params["recents"] = [p for p in self.params.get("recents") or [] if p != chemin]
            self.params.enregistrer()
            self.accueil.rafraichir()

    def atelier_logo(self):
        """Atelier de logo ; « Enregistrer et animer » enchaîne sur la Fabrique avec ce logo."""
        from .dialogues_logo import DialogueLogo
        d = DialogueLogo(self, self.params)
        if d.exec() == QDialog.Accepted and d.png:
            self.fabrique(image=d.png, texte=d.logo.get("nom"))

    def fabrique(self, image=None, texte=None):
        ed = self._editeur_ou_nouveau()
        from .dialogues_video import DialogueFabrique
        d = DialogueFabrique(self, ed.projet, self.params)
        if image:
            d.image.setText(image)
            d.onglets.setCurrentIndex(0)
        if texte:
            d.texte.setText(texte)
        if d.exec() != QDialog.Accepted:
            return
        L, H = ed.projet.taille
        if d.onglets.currentIndex() == 0:
            texte = d.texte.text().strip() or "PhilCut"
            modele, duree, usage = d.modele.currentData(), d.duree.value(), d.usage.currentData()
            dossier = os.path.join(dossier_donnees(), "fabrique")
            os.makedirs(dossier, exist_ok=True)
            sortie = os.path.join(dossier, f"logo_{modele}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            image = d.image.text().strip() or None
            sous = d.sous.text().strip()

            def travail(tache):
                return FAB.fabriquer_logo(sortie, texte, modele, L, H, ed.projet.cadence, duree, progression=lambda f: tache.avancer(f), image_logo=image, sous_texte=sous)
            t = Tache(travail, _("Fabrique"))
            self.taches.append(t)
            ed.encart.suivre(t, _("Fabrication du logo « {t} »", t=texte))
            t.fini.connect(lambda r, e: self._logo_pret(ed, sortie, usage, e))
            t.start()
        else:
            consigne = d.consigne.toPlainText().strip() or FAB.consigne_plan("illustration", d.sujet.toPlainText().strip(), d.style.currentText().strip(), d.duree_ia.value(), ed.projet.format)
            self.params["fabrique_style"] = d.style.currentText().strip()
            self.params["dossier_flow"] = d.dossier.text().strip()
            self.params.enregistrer()
            if d.voie_veo.isChecked():
                from . import generateurs_video as GV
                modele = d.modele_veo.currentData()
                mo = GV.modele(modele, self.params)
                if not mo:
                    return
                prix = GV.prix(mo, d.duree_ia.value())
                fourn = GV.FOURNISSEURS[mo["fournisseur"]]["nom"]
                if QMessageBox.question(self, _("Plan IA"), _("Générer ce plan avec {m} pour au plus {p} $ environ (facturé sur votre clef {f}) ?",
                                                             m=mo["nom"], p=prix, f=fourn)) != QMessageBox.Yes:
                    return
                dossier = os.path.join(dossier_donnees(), "fabrique")
                os.makedirs(dossier, exist_ok=True)
                sortie = os.path.join(dossier, f"plan_ia_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
                t = Tache(lambda tache: GV.generer(self.params, modele, consigne, sortie, d.duree_ia.value(), ed.projet.format, progression=tache.avancer, arret=lambda: tache.arret), _("Plan IA"))
                self.taches.append(t)
                ed.encart.suivre(t, _("Génération du plan par IA (1 à 6 min)"))
                t.fini.connect(lambda r, e: ed.importer([sortie]) if not e else QMessageBox.warning(self, _("Plan IA"), str(e)))
                t.start()
            else:
                avant = FAB.preparer_flow(consigne, d.dossier.text().strip())
                ed.encart.message(_("Consigne copiée dans le presse-papiers, Flow ouvert dans le navigateur. Collez la consigne, générez, téléchargez : "
                                    "PhilCut surveille le dossier et importera le clip."), 30000)
                self._surveiller_flow(ed, d.dossier.text().strip(), avant)

    def _logo_pret(self, ed, sortie, usage, erreur):
        if erreur:
            return
        ed.importer([sortie])
        if usage in ("debut", "fin"):
            def placer():
                m = ed.projet.media(sortie) or next((x for x in ed.projet.medias if x["chemin"] == sortie), None)
                if not m:
                    QTimer.singleShot(1500, placer)
                    return
                ed.projet.marquer()
                if usage == "debut":
                    d = float((m.get("fiche") or {}).get("duree") or 2.5)
                    for c in ed.projet.clips_piste("video"):
                        c["debut"] += d
                    for x in ed.projet.titres + ed.projet.goodies:
                        x["debut"] += d
                        x["fin"] += d
                    ed.projet.ajouter_clip(m["id"], "video", 0.0)
                else:
                    ed.projet.ajouter_clip(m["id"], "video")
                ed.projet.ranger("video")
                ed.rafraichir()
            QTimer.singleShot(1500, placer)

    def _surveiller_flow(self, ed, dossier, avant, essais=0):
        nouveaux = FAB.nouveaux_clips(dossier, avant)
        if nouveaux:
            ed.importer(nouveaux)
            ed.encart.message(_("Clip Flow récupéré : {n}", n=", ".join(os.path.basename(x) for x in nouveaux)))
            return
        if essais < 600:
            QTimer.singleShot(3000, lambda: self._surveiller_flow(ed, dossier, avant, essais + 1))

    def musique(self):
        ed = self._editeur_ou_nouveau()
        m = QMenu(self)
        m.addAction(_("Importer une musique…"), lambda: ed.importer())
        d = self.params.get("musiques_dossier")
        if d and os.path.isdir(d):
            sm = m.addMenu(_("Mon dossier de musiques"))
            for f in sorted(os.listdir(d))[:40]:
                if est_audio(f):
                    sm.addAction(f, lambda f=f: self._poser_musique(ed, os.path.join(d, f)))
        m.addAction(_("Bibliothèque musicale libre (chercher, écouter, télécharger)…"), lambda: self.bibliotheque_musicale(ed))
        m.exec(self.cursor().pos())

    def bibliotheque_musicale(self, ed=None, ambiance=None):
        ed = ed or self._editeur_ou_nouveau()
        from .dialogues_musiques import DialogueMusiques
        amb = ambiance or ((ed.projet.d.get("recette") or {}).get("musique") or {}).get("ambiance")
        corresp = {"energique": "energique", "chaleureuse": "calme", "douce": "calme", "legere": "joyeuse"}
        d = DialogueMusiques(self, self.params, corresp.get(amb, amb))
        if d.exec() == QDialog.Accepted and d.chemin:
            self._poser_musique(ed, d.chemin)

    def _poser_musique(self, ed, chemin):
        ed._piste_depot = ("audio", 0.0)
        ed.importer([chemin])

    def sous_titres(self):
        ed = self.editeur_courant()
        if not ed:
            return
        m = QMenu(self)
        m.addAction(_("Sous-titres automatiques (voix transcrite sur ce poste)"), lambda: self._transcrire(ed))
        m.addAction(_("Sous-titres karaoké (chaque mot s'allume quand il est dit)"), lambda: self._transcrire(ed, karaoke=True))
        m.addAction(_("Importer un fichier .srt…"), lambda: self._importer_srt(ed))
        if ed.projet.d.get("sous_titres"):
            m.addAction(_("Retirer les sous-titres"), lambda: (ed.projet.marquer(), ed.projet.d.__setitem__("sous_titres", []), ed.rafraichir()))
        m.exec(self.cursor().pos())

    def _importer_srt(self, ed):
        from . import titres
        p, _f = QFileDialog.getOpenFileName(self, _("Sous-titres"), "", "SRT (*.srt)")
        if p:
            with open(p, encoding="utf-8", errors="replace") as f:
                ed.projet.marquer()
                ed.projet.d["sous_titres"] = titres.lire_srt(f.read())
            ed.encart.message(_("{n} sous-titres importés (rendus à l'export).", n=len(ed.projet.d["sous_titres"])))

    def _transcrire(self, ed, karaoke=False):
        from . import sous_titres as ST
        if not ST.disponible():
            QMessageBox.information(self, _("Sous-titres"), _("Cochez un modèle « Voix (sous-titres automatiques) » dans Edition › Préférences › IA locale : "
                                                             "il se range dans le dossier de PhilCut, rien n'est installé dans Windows."))
            return
        t = Tache(lambda tache: ST.transcrire_projet(ed.projet, self.params, progression=tache.avancer, karaoke=karaoke), _("Transcription"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Transcription de la voix (local)"))
        t.fini.connect(lambda r, e: (ed.projet.d.__setitem__("sous_titres", r), ed.encart.message(_("{n} sous-titres.", n=len(r)))) if r and not e else None)
        t.start()

    def voix(self):
        ed = self.editeur_courant()
        if not ed:
            return
        c = ed._clip_selectionne()
        m = QMenu(self)
        from .export import VOIX
        m.addAction(_("Enregistrer une voix off au micro…"), self.enregistrer_voix)
        m.addAction(_("Voix off lue par une voix de synthèse…"), self.voix_synthese)
        m.addAction(_("Doubler la vidéo dans une autre langue…"), self.doubler)
        if c:
            m.addAction(_("Autotune : corriger la justesse du chant de ce plan…"), lambda: ed.autotune(c))
            m.addAction(_("▶ Ecouter ce plan avec ses retouches"), lambda: (ed._ouvrir_volet(1), ed.timeline.selectionner(c["id"]),
                                                                          ed.inspecteur.montrer_clip(c["id"])))
        if not c:
            m.addSeparator()
            m.addAction(_("(choisissez un plan pour retoucher sa voix)")).setEnabled(False)
            m.exec(self.cursor().pos())
            return
        m.addSeparator()
        for eid, lib in VOIX:
            a = m.addAction(_(lib), lambda eid=eid: self._effet_audio(ed, c, eid))
            a.setCheckable(True)
            a.setChecked(eid in (c.get("effets_audio") or []))
        m.addSeparator()
        for lib, v in ((_("Volume 50 %"), 0.5), (_("Volume 100 %"), 1.0), (_("Volume 150 %"), 1.5)):
            m.addAction(lib, lambda v=v: (ed.projet.marquer(), c.__setitem__("volume", v), ed.rafraichir()))
        a = m.addAction(_("Muet"), lambda: (ed.projet.marquer(), c.__setitem__("muet", not c.get("muet")), ed.rafraichir()))
        a.setCheckable(True)
        a.setChecked(bool(c.get("muet")))
        m.exec(self.cursor().pos())

    # ---------------------------------------------------------------- voix off, synthèse, doublage
    def _poser_voix(self, ed, chemin, debut, effets=()):
        ed._piste_depot = ("voix", float(debut), {"effets_audio": list(effets)} if effets else {})
        ed.importer([chemin])

    def enregistrer_voix(self):
        ed = self.editeur_courant()
        if not ed:
            return
        from .dialogues_voix import DialogueEnregistrement
        debut = ed.timeline.position
        d = DialogueEnregistrement(self, self.params, debut, getattr(ed, "apercu", None))
        if d.exec() == QDialog.Accepted and d.chemin:
            self._poser_voix(ed, d.chemin, debut, d.effets)

    def voix_synthese(self):
        ed = self.editeur_courant()
        if not ed:
            return
        from .dialogues_voix import DialogueSynthese
        from . import voix as V
        debut = ed.timeline.position
        d = DialogueSynthese(self, self.params, debut)
        if d.exec() != QDialog.Accepted:
            return
        r = d.reglages
        if r["moteur"] == "gemini":
            if QMessageBox.question(self, _("Voix de synthèse"), _("Lecture par Gemini : environ {p} $ sur votre compte. Continuer ?",
                                    p=f"{V.prix_gemini(r['texte']):.3f}".replace(".", ","))) != QMessageBox.Yes:
                return
        sortie = V.nouveau_nom(self.params, "synthese")
        t = Tache(lambda tache: V.lire(r["texte"], sortie, self.params, r["moteur"], r["voix"], r["vitesse"]), _("Voix de synthèse"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Lecture du texte par la voix de synthèse"))
        t.fini.connect(lambda res, e: self._poser_voix(ed, res, debut, d.effets) if res and not e else
                       (e and QMessageBox.warning(self, _("Voix de synthèse"), str(e))))
        t.start()

    def doubler(self):
        ed = self.editeur_courant()
        if not ed:
            return
        from .dialogues_voix import DialogueDoublage
        from . import voix as V
        d = DialogueDoublage(self, self.params)
        if d.exec() != QDialog.Accepted:
            return
        r = d.reglages
        sortie = V.nouveau_nom(self.params, f"doublage_{r['langue']}")
        import copy
        projet = copy.deepcopy(ed.projet)
        t = Tache(lambda tache: V.doubler(projet, self.params, r["langue"], sortie, r["voix"], r["moteur"], r["en_ligne"],
                                          progression=tache.avancer, arret=lambda: tache.arret), _("Doublage"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Doublage en cours (écoute, traduction, lecture)"))

        def fini(res, e):
            if e or not res:
                if e:
                    QMessageBox.warning(self, _("Doublage"), str(e))
                return
            chemin, st = res
            ed.projet.marquer()
            V.baisser_originaux(ed.projet)
            if r["sous_titres"]:
                ed.projet.d["sous_titres"] = st
            self._poser_voix(ed, chemin, 0.0)
            ed.encart.message(_("Doublage posé sur la piste Voix ; la voix d'origine est baissée (Voix › Volume pour la régler)."))
        t.fini.connect(fini)
        t.start()

    def _effet_audio(self, ed, c, eid):
        ed.projet.marquer()
        l = list(c.get("effets_audio") or [])
        if eid in l:
            l.remove(eid)
        else:
            l.append(eid)
        c["effets_audio"] = l
        ed.rafraichir()

    def partager(self, chemin=None):
        if not chemin:
            chemin, _f = QFileDialog.getOpenFileName(self, _("Vidéo à déposer"), self.params.get("dernier_dossier_export") or __import__("app.session", fromlist=["x"]).dossier_systeme("videos"), "MP4 (*.mp4)")
            if not chemin:
                return
        try:
            from . import miroir, distant
            compte = miroir.compte_drive(self.params)
            if compte:
                e = distant.emplacement(compte)
                import posixpath
                dest = posixpath.join(miroir.racine_distante(compte), "Exports", os.path.basename(chemin))
                e.envoyer(chemin, dest) if hasattr(e, "envoyer") else e.televerser(chemin, dest)
                QMessageBox.information(self, _("Déposer"), _("Déposé sur {c} : {d}", c=miroir.libelle_compte(compte), d=dest))
                return
            dd = self.params.get("drive")
            if dd and os.path.isdir(dd):
                import shutil
                d = os.path.join(dd, "PhilCut", "Exports")
                os.makedirs(d, exist_ok=True)
                shutil.copy2(chemin, d)
                QMessageBox.information(self, _("Déposer"), _("Copié dans {d}", d=d))
                return
        except Exception as e:    # noqa: BLE001
            QMessageBox.warning(self, _("Déposer"), str(e))
            return
        QMessageBox.information(self, _("Déposer"), _("Aucun emplacement de synchronisation : choisissez-en un dans Edition › Préférences › Comptes et synchro."))

    # ---------------------------------------------------------------- barre, preferences, aide
    def personnaliser_barre(self):
        from PySide6.QtWidgets import QListWidget
        d = QDialog(self)
        d.setWindowTitle(_("Personnaliser la barre d'outils"))
        d.resize(720, 520)
        v = QVBoxLayout(d)
        lb = QLabel(_("Glissez pour changer l'ordre. La barre passe sur plusieurs lignes si la fenêtre est étroite. Elle est la même sur tous vos postes."))
        lb.setWordWrap(True)
        v.addWidget(lb)
        h = QHBoxLayout()
        dispo, barre = QListWidget(), QListWidget()
        barre.setDragDropMode(QListWidget.InternalMove)
        libelles = dict(O.ELEMENTS_BARRE)
        libelles.update({o[0]: o[3] for o in O.OUTILS})

        def item(cle):
            it = QListWidgetItem(libelles.get(cle, cle))
            it.setData(Qt.UserRole, cle)
            return it
        actuelle = list(self.params.get("barre") or O.BARRE_DEFAUT)
        for c in actuelle:
            barre.addItem(item(c))
        cles = [k for k, _l in O.ELEMENTS_BARRE] + [o[0] for o in O.OUTILS]

        def remplir():
            dispo.clear()
            presents = {barre.item(i).data(Qt.UserRole) for i in range(barre.count())}
            for c in cles:
                if c not in presents or c == "|":
                    dispo.addItem(item(c))
        remplir()
        vg = QVBoxLayout()
        vg.addWidget(QLabel(_("<b>Disponibles</b>")))
        vg.addWidget(dispo)
        h.addLayout(vg, 1)
        vb = QVBoxLayout()
        vb.addStretch(1)
        b_aj, b_ret = QPushButton(_("Ajouter →")), QPushButton(_("← Retirer"))
        vb.addWidget(b_aj)
        vb.addWidget(b_ret)
        vb.addStretch(1)
        h.addLayout(vb)
        vd = QVBoxLayout()
        vd.addWidget(QLabel(_("<b>Dans la barre</b> (de gauche à droite)")))
        vd.addWidget(barre)
        h.addLayout(vd, 1)
        v.addLayout(h, 1)

        def ajouter():
            for it in dispo.selectedItems():
                ligne = barre.currentRow() + 1 if barre.currentRow() >= 0 else barre.count()
                barre.insertItem(ligne, item(it.data(Qt.UserRole)))
            remplir()

        def retirer():
            for it in barre.selectedItems():
                barre.takeItem(barre.row(it))
            remplir()
        b_aj.clicked.connect(ajouter)
        b_ret.clicked.connect(retirer)
        dispo.itemDoubleClicked.connect(lambda _i: ajouter())
        barre.itemDoubleClicked.connect(lambda _i: retirer())
        hb = QHBoxLayout()
        b_def = QPushButton(_("Barre par défaut"))
        b_def.clicked.connect(lambda: (barre.clear(), [barre.addItem(item(c)) for c in O.BARRE_DEFAUT], remplir()))
        hb.addWidget(b_def)
        hb.addStretch(1)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel))
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        hb.addWidget(bb)
        v.addLayout(hb)
        if d.exec() != QDialog.Accepted:
            return
        self.params["barre"] = [barre.item(i).data(Qt.UserRole) for i in range(barre.count())]
        self.params.enregistrer()
        self.reconstruire_barres()

    def reconstruire_barres(self):
        for ed in self.editeurs():
            ed.construire_barre()
            ed.appliquer_volet()

    def preferences(self, onglet=None):
        from .preferences import DialoguePreferences
        avant = (self.params.get("theme"), self.params.get("langue"))
        d = DialoguePreferences(self, self.params, onglet)
        if d.exec() == QDialog.Accepted:
            self.reconstruire_barres()
            if avant != (self.params.get("theme"), self.params.get("langue")):
                if QMessageBox.question(self, _("Préférences"), _("Le thème ou la langue a changé : relancer PhilCut maintenant ?")) == QMessageBox.Yes:
                    self.redemarrer()

    def connecter_ia(self):
        from .dialogues_connexion_ia import DialogueConnexionIA
        DialogueConnexionIA(self, self.params).exec()

    def redemarrer(self):
        self.close()
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable])
        else:
            subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0])])
        QApplication.quit()

    def suivre_tache(self, t, texte, action=None):
        """Progression d'une tâche : dans l'encart du projet ouvert, sinon dans la barre du bas de la fenêtre."""
        ed = self.editeur_courant()
        (ed.encart if ed else self.encart_global).suivre(t, texte, action)      # l'encart inscrit aussi la tâche au Centre d'activité

    def voir_telechargements(self):
        self.voir_activite()

    def voir_activite(self):
        from .activite import FenetreActivite
        if self.fenetre_activite is None:
            self.fenetre_activite = FenetreActivite(self, self.centre)
        self.fenetre_activite.show()
        self.fenetre_activite.raise_()
        self.fenetre_activite.activateWindow()

    def _etat_activite(self):
        txt, actif = self.centre.resume()
        self.b_activite.setText(("● " if actif else "✓ ") + txt)
        self.b_activite.setStyleSheet("QPushButton{color:%s;font-weight:600}" % theme.COULEURS["accent"] if actif else "")

    def _telech_termine(self, cle, erreur):
        if erreur is not None and not isinstance(erreur, InterruptedError):
            self.encart_global.message(_("✕ Téléchargement de {c} : {e}", c=cle, e=str(erreur)[:160]), 15000)

    def installer_ia(self, cles):
        """Télécharge des modèles d'IA locale (et leur moteur) dans le dossier de PhilCut : file d'attente visible."""
        self.telechargements.ajouter(cles)
        self.voir_telechargements()

    def _installer_ia_ancien(self, cles):
        from . import packs_ia
        ed = self.editeur_courant()

        def travail(tache):
            for i, k in enumerate(cles):
                packs_ia.installer(k, lambda f, t="", i=i: tache.avancer((i + f) / len(cles), t), arret=lambda: tache.arret)
                genre = (packs_ia.modeles(avec_essai=True).get(k) or {}).get("genre")
                if genre:
                    choix = dict(self.params.get("ia_locale_modeles") or {})
                    choix[genre] = k
                    self.params["ia_locale_modeles"] = choix
            return True
        t = Tache(travail, _("IA locale"))
        self.taches.append(t)
        texte = _("Téléchargement de l'IA locale dans le dossier de PhilCut")
        self.suivre_tache(t, texte)
        t.fini.connect(lambda r, e: e and QMessageBox.warning(self, _("IA locale"), _("✕ {t} : {e}", t=texte, e=e)))
        t.fini.connect(lambda r, e: self.params.enregistrer())
        t.start()

    def telecharger_pack(self, cle):
        from . import effets as E
        p = E.PACKS.get(cle)
        if p and p.get("ia"):
            from . import packs_ia
            if not packs_ia.modele_actif(p["ia"]):
                self.installer_ia([packs_ia.DEFAUT[p["ia"]]])
            return
        if not p or not p.get("pip"):
            return
        if getattr(sys, "frozen", False):
            QMessageBox.information(self, _("Pack"), _("Dans la version tout-en-un, le pack « {n} » sera téléchargé sous forme de module séparé dans une prochaine version. "
                                                        "En attendant, lancez PhilCut depuis les sources (lancer.bat) et cochez-le : pip l'installe.", n=p["nom"]))
            return
        ed = self.editeur_courant()

        def travail(tache):
            tache.avancer(0.1, " ".join(p["pip"]))
            r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet"] + p["pip"], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(r.stderr[-400:])
            return True
        t = Tache(travail, _("Pack"))
        self.taches.append(t)
        self.suivre_tache(t, _("Téléchargement du pack « {n} »", n=p["nom"]))
        t.start()

    def bienvenue(self, seulement_synchro=False):
        try:
            from .bienvenue import DialogueBienvenue
            d = DialogueBienvenue(self, self.params, seulement_synchro)
            if d.exec() == QDialog.Accepted:
                if d.appliquer():
                    self.redemarrer()
        except Exception as e:    # noqa: BLE001 : l'assistant de bienvenue ne doit jamais bloquer
            self.params["bienvenue_vue"] = True
            self.params.enregistrer()
            from .journal import ecrire
            ecrire("bienvenue", f"non affiché : {e}")

    def exporter_reglages(self, parent=None):
        from . import reglages
        p, _f = QFileDialog.getSaveFileName(parent or self, _("Exporter les préférences"), "PhilCut_preferences.json", "JSON (*.json);;" + _("Chiffré") + " (*.philcutprefs)")
        if not p:
            return
        phrase = None
        if QMessageBox.question(self, _("Préférences"), _("Inclure les mots de passe et clefs (fichier chiffré par une phrase secrète) ?")) == QMessageBox.Yes:
            phrase, ok = QInputDialog.getText(self, _("Phrase secrète"), _("Phrase secrète (à retenir)"), echo=2)
            if not ok or not phrase:
                return
        d = reglages.instantane(self.params, avec_secrets=bool(phrase))
        d["philcut"] = 1
        reglages.exporter(p, d, phrase)
        QMessageBox.information(self, _("Préférences"), _("Préférences exportées."))

    def importer_reglages(self):
        from . import reglages
        p, _f = QFileDialog.getOpenFileName(self, _("Importer des préférences"), "", _("Préférences PhilCut") + " (*.json *.philcutprefs)")
        if not p:
            return
        phrase = None
        while True:
            try:
                d = reglages.importer(p, phrase)
                break
            except reglages.PhraseRequise:
                phrase, ok = QInputDialog.getText(self, _("Phrase secrète"), _("Ce fichier est chiffré : phrase secrète"), echo=2)
                if not ok:
                    return
            except Exception as e:     # noqa: BLE001
                QMessageBox.warning(self, _("Préférences"), str(e))
                return
        reglages.appliquer(self.params, d)
        self.reconstruire_barres()
        QMessageBox.information(self, _("Préférences"), _("Préférences importées."))

    def journal_echanges(self):
        from .journal import chemin
        d = QDialog(self)
        d.setWindowTitle(_("Journal des échanges"))
        d.resize(820, 520)
        v = QVBoxLayout(d)
        t = QPlainTextEdit()
        t.setReadOnly(True)
        try:
            with open(chemin(), encoding="utf-8", errors="replace") as f:
                t.setPlainText(f.read()[-200000:])
        except OSError:
            t.setPlainText(_("Aucun échange noté pour l'instant."))
        v.addWidget(t)
        bb = boutons_fr(QDialogButtonBox(QDialogButtonBox.Close))
        bb.rejected.connect(d.reject)
        bb.clicked.connect(d.reject)
        v.addWidget(bb)
        d.exec()

    def raccourcis(self):
        QMessageBox.information(self, _("Raccourcis"), _(
            "Espace : lecture / pause\nC : couper au curseur\nSuppr : supprimer et refermer (Maj+Suppr : laisser un trou)\n"
            "← → : image par image (Maj : seconde)\nOrigine / Fin : début / fin\nCtrl+molette : zoom de la timeline · Ctrl+0 : tout voir\n"
            "Ctrl+Z / Ctrl+Y : annuler / rétablir\nCtrl+I : importer · Ctrl+S : enregistrer · Ctrl+E : exporter\nF4 : volet de droite\n"
            "Double-clic sur un plan : effets et transition · clic droit : vitesse, cadrage, muet"))

    def a_propos(self):
        QMessageBox.about(self, _("A propos de PhilCut"), _(
            "<h3>PhilCut {v}</h3><p>Montage vidéo libre (GPL v3) : simple, efficace, effet wahou. Par Philippe Delaye, avec Claude.</p>"
            "<p>Moteurs : FFmpeg {f} (GPL), Qt / PySide6 (LGPL), OpenCV (Apache 2.0), police Nunito (SIL OFL).</p>"
            "<p>Vos rushes restent où ils sont ; rien n'est envoyé à une IA sans votre clic.</p>", v=VERSION, f=moteur.version() or "?"))

    # ---------------------------------------------------------------- mises a jour (proposees, jamais imposees)
    def verifier_maj(self, silencieux=True):
        t = Tache(lambda tache: mise_a_jour.chercher(self.params), _("Mise à jour"))
        self.taches.append(t)
        t.fini.connect(lambda r, e: self._maj_trouvee(r, e, silencieux))
        t.start()

    def _maj_trouvee(self, res, erreur, silencieux):
        if erreur or res is None or (isinstance(res, dict) and ("erreur" in res or "preparation" in res)):
            if not silencieux:
                if isinstance(res, dict) and res.get("preparation"):
                    QMessageBox.information(self, _("Mise à jour"), _("La version {v} est publiée ; son paquet est encore en fabrication. Réessayez dans quelques minutes.", v=res["preparation"]))
                elif isinstance(res, dict) and res.get("erreur"):
                    QMessageBox.information(self, _("Mise à jour"), _("Impossible de vérifier : {e}", e=res["erreur"]))
                elif erreur:
                    QMessageBox.information(self, _("Mise à jour"), str(erreur))
                else:
                    QMessageBox.information(self, _("Mise à jour"), _("PhilCut {v} est à jour.", v=VERSION))
            return
        version, paquet, notes = res
        texte = _("PhilCut {n} est disponible (vous avez {v}).", n=version, v=VERSION) + (f"<br><span style='color:#999'>{notes[:400]}</span>" if notes else "")
        self.accueil.proposer(texte, _("Télécharger et installer"), lambda: self._installer_maj(paquet))
        self.onglets.setCurrentIndex(0) if not silencieux else None

    def _installer_maj(self, paquet):
        t = Tache(lambda tache: mise_a_jour.recuperer(paquet, progression=lambda f: tache.avancer(f), arret=lambda: tache.arret), _("Mise à jour"))
        self.taches.append(t)
        ed = self.editeur_courant()
        if ed:
            ed.encart.suivre(t, _("Téléchargement de la mise à jour"))
        t.fini.connect(lambda r, e: self._maj_recue(r, e))
        t.start()

    def _maj_recue(self, fichier, erreur):
        if erreur or not fichier:
            QMessageBox.warning(self, _("Mise à jour"), str(erreur or _("téléchargement vide")))
            return
        if not mise_a_jour.fichier_valide(fichier):
            QMessageBox.warning(self, _("Mise à jour"), _("Le fichier téléchargé n'est pas valide : rien n'a été changé."))
            return
        if QMessageBox.question(self, _("Mise à jour"), _("Mise à jour téléchargée. Fermer PhilCut et l'installer maintenant ?")) == QMessageBox.Yes:
            mise_a_jour.appliquer(fichier)
            QApplication.quit()

    # ---------------------------------------------------------------- session partagee
    def ecrire_session(self):
        if not self.params.get("synchro", True):
            return
        try:
            from .session import session_de
            s = session_de(self.params)
            ouverts = [(ed.projet.chemin, 0, 1.0) for ed in self.editeurs() if ed.projet.chemin]
            s.ecrire(ouverts)
            from . import reglages
            reglages.ecrire_drive(self.params)
        except Exception as e:    # noqa: BLE001
            from .journal import ecrire
            ecrire("synchro", f"session non écrite : {e}")

    def verifier_session(self):
        try:
            from .session import session_de, date_fr, nb_fichiers
            s = session_de(self.params)
            autres = s.autres_machines()
            self.accueil.rafraichir(autres)
            d = s.discordance([ed.projet.chemin for ed in self.editeurs() if ed.projet.chemin])
            if d:
                machine, date, fichiers = d
                self.accueil.proposer(_("Sur « {m} » ({d}), {n} projet(s) étaient ouverts : {l}. Les rouvrir ici ?", m=machine, d=date_fr(date), n=len(fichiers),
                                        l=", ".join(f.get("nom", "") for f in fichiers[:4])), _("Reprendre"), lambda: self._reprendre(fichiers))
        except Exception as e:    # noqa: BLE001
            from .journal import ecrire
            ecrire("synchro", f"session non lue : {e}")

    def _reprendre(self, fichiers):
        for f in fichiers:
            p = f.get("chemin")
            if p and os.path.exists(p):
                self.ouvrir(p)
            else:
                self.statusBar().showMessage(_("Introuvable ici : {n}", n=f.get("nom", "")), 8000)
