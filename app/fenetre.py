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
from .editeur import Editeur
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
        e = mb.addMenu(_("&Édition"))
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
        a.addSeparator()
        a.addAction(_("Volet de droite : complet / icônes / masqué"), lambda: self._ed(lambda ed: ed.basculer_volet()), "F4")
        a.addAction(_("Personnaliser la barre d'outils…"), self.personnaliser_barre)
        mo = mb.addMenu(_("&Montage"))
        for oid in ("vitesse", "recadrer", "stabiliser", "texte", "effets", "goodies", "sous_titres", "musique", "voix"):
            o = O.outil(oid)
            mo.addAction(icone(o[2]), o[3], lambda _c=False, oid=oid: self._editeur_ou_nouveau().outil(oid))
        asst = mb.addMenu(_("A&ssistant"))
        asst.addAction(icone("assistant"), _("Analyser et proposer un montage"), lambda: self._editeur_ou_nouveau().outil("assistant"), "Ctrl+Shift+A")
        asst.addAction(icone("liste_fichiers"), _("Fiche vidéo du plan sélectionné"), lambda: self._ed(lambda ed: ed.outil("fiche")))
        asst.addAction(_("Changer le niveau (sans IA, locale, cloud)…"), lambda: self.preferences("Assistant"))
        fb = mb.addMenu(_("Fa&brique"))
        fb.addAction(icone("fabrique"), _("Logo, intro, fin, plan IA…"), self.fabrique, "Ctrl+Shift+F")
        ou = mb.addMenu(_("&Outils"))
        ou.addAction(icone("nuage"), _("Déposer l'export sur le Drive / NAS…"), self.partager)
        ou.addAction(_("Synchroniser maintenant"), self.ecrire_session)
        ou.addAction(_("Journal des échanges (Drives, IA)…"), self.journal_echanges)
        ou.addAction(_("Ouvrir le dossier des données"), lambda: self.ouvrir_externe(dossier_donnees()))
        ai = mb.addMenu(_("&Aide"))
        ai.addAction(_("Raccourcis clavier"), self.raccourcis)
        ai.addAction(_("Guide de test de la première version"), lambda: webbrowser.open("https://github.com/PhilouElChapo/PhilCut/blob/main/docs/guideline-tests.md"))
        ai.addAction(_("Vérifier les mises à jour…"), lambda: self.verifier_maj(silencieux=False))
        ai.addAction(_("Site du projet (GitHub)"), lambda: webbrowser.open("https://github.com/PhilouElChapo/PhilCut"))
        ai.addSeparator()
        ai.addAction(_("À propos de PhilCut"), self.a_propos)

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
            r = QMessageBox.question(self, _("Fermer"), _("Enregistrer les modifications de « {n} » ?", n=w.projet.nom),
                                     QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Save:
                self.onglets.setCurrentIndex(i)
                if not self.enregistrer():
                    return
        w.apercu.arreter()
        self.onglets.removeTab(i)
        w.deleteLater()
        self.ecrire_session()

    def closeEvent(self, e):
        for ed in self.editeurs():
            if ed.projet.modifie:
                self.onglets.setCurrentWidget(ed)
                r = QMessageBox.question(self, _("Quitter"), _("Enregistrer les modifications de « {n} » ?", n=ed.projet.nom),
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if r == QMessageBox.Cancel:
                    e.ignore()
                    return
                if r == QMessageBox.Save and not self.enregistrer():
                    e.ignore()
                    return
        en_cours = [t for t in self.taches + sum((ed.taches for ed in self.editeurs()), []) if t.isRunning()]
        if en_cours and QMessageBox.question(self, _("Quitter"), _("{n} opération(s) en cours (export, import…). Quitter quand même ?", n=len(en_cours))) != QMessageBox.Yes:
            e.ignore()
            return
        for t in en_cours:
            t.stopper()
        for ed in self.editeurs():
            ed.apercu.arreter()
        self.ecrire_session()
        self.params.enregistrer()
        e.accept()

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

        def travail(tache):
            ex = export.Exportateur(projet_copie, sortie, dest, qualite=qual, encodeur=enc, params=self.params)
            try:
                ex.lancer(progression=lambda f: tache.avancer(f), arret=lambda: tache.arret, sous_titres=st)
                if d.srt.isChecked() and st:
                    with open(os.path.splitext(sortie)[0] + ".srt", "w", encoding="utf-8") as f:
                        f.write(titres.srt(st))
                return ex.journal
            finally:
                ex.nettoyer()
        t = Tache(travail, _("Export"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Export vers {f}", f=os.path.basename(sortie)), (_("Ouvrir"), lambda: self.ouvrir_externe(sortie)))
        t.fini.connect(lambda r, e: self._exporte(sortie, r, e, d.drive.isChecked()))
        t.start()

    def _exporte(self, sortie, journal, erreur, deposer):
        from .journal import ecrire
        if erreur:
            ecrire("export", f"✕ {sortie} : {erreur}")
            return
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

    def fabrique(self):
        ed = self._editeur_ou_nouveau()
        from .dialogues_video import DialogueFabrique
        d = DialogueFabrique(self, ed.projet, self.params)
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
                modele = d.modele_veo.currentData()
                prix = FAB.prix_veo(modele, d.duree_ia.value())
                if QMessageBox.question(self, _("Veo"), _("Générer ce plan avec {m} pour environ {p} $ (facturé sur votre clef Gemini) ?", m=FAB.MODELES_VEO[modele][0], p=prix)) != QMessageBox.Yes:
                    return
                dossier = os.path.join(dossier_donnees(), "fabrique")
                os.makedirs(dossier, exist_ok=True)
                sortie = os.path.join(dossier, f"veo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
                t = Tache(lambda tache: FAB.generer_veo(self.params, consigne, sortie, modele, d.duree_ia.value(), ed.projet.format, progression=tache.avancer, arret=lambda: tache.arret), _("Veo"))
                self.taches.append(t)
                ed.encart.suivre(t, _("Génération Veo (1 à 6 min)"))
                t.fini.connect(lambda r, e: ed.importer([sortie]) if not e else QMessageBox.warning(self, _("Veo"), str(e)))
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
        m.addAction(_("Bibliothèque libre en ligne (bientôt : catalogue téléchargeable)"), lambda: webbrowser.open("https://freemusicarchive.org/"))
        m.exec(self.cursor().pos())

    def _poser_musique(self, ed, chemin):
        ed._piste_depot = ("audio", 0.0)
        ed.importer([chemin])

    def sous_titres(self):
        ed = self.editeur_courant()
        if not ed:
            return
        m = QMenu(self)
        m.addAction(_("Transcrire la voix (Whisper local, pack à cocher)"), lambda: self._transcrire(ed))
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

    def _transcrire(self, ed):
        try:
            from faster_whisper import WhisperModel      # noqa: F401
        except ImportError:
            QMessageBox.information(self, _("Sous-titres"), _("Cochez le pack « Sous-titres automatiques (Whisper local) » dans Édition › Préférences › Effets et Goodies : il se télécharge sur ce poste."))
            return
        from . import sous_titres as ST
        t = Tache(lambda tache: ST.transcrire_projet(ed.projet, self.params, progression=tache.avancer), _("Transcription"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Transcription de la voix (local)"))
        t.fini.connect(lambda r, e: (ed.projet.d.__setitem__("sous_titres", r), ed.encart.message(_("{n} sous-titres.", n=len(r)))) if r and not e else None)
        t.start()

    def voix(self):
        ed = self.editeur_courant()
        if not ed:
            return
        c = ed._clip_selectionne()
        if not c:
            return
        m = QMenu(self)
        for lib, eid in ((_("Débruiter le son (vent, moteur)"), "a_debruit"), (_("Voix embellie (narration)"), "a_voix"), (_("Autotune (chant)"), "a_autotune"), (_("Réverbération"), "a_reverb"), (_("Écho"), "a_echo")):
            a = m.addAction(lib, lambda eid=eid: self._effet_audio(ed, c, eid))
            a.setCheckable(True)
            a.setChecked(eid in (c.get("effets_audio") or []))
        m.addSeparator()
        for lib, v in ((_("Volume 50 %"), 0.5), (_("Volume 100 %"), 1.0), (_("Volume 150 %"), 1.5)):
            m.addAction(lib, lambda v=v: (ed.projet.marquer(), c.__setitem__("volume", v), ed.rafraichir()))
        a = m.addAction(_("Muet"), lambda: (ed.projet.marquer(), c.__setitem__("muet", not c.get("muet")), ed.rafraichir()))
        a.setCheckable(True)
        a.setChecked(bool(c.get("muet")))
        m.exec(self.cursor().pos())

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
            chemin, _f = QFileDialog.getOpenFileName(self, _("Vidéo à déposer"), self.params.get("dernier_dossier_export") or "", "MP4 (*.mp4)")
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
        QMessageBox.information(self, _("Déposer"), _("Aucun emplacement de synchronisation : choisissez-en un dans Édition › Préférences › Comptes et synchro."))

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

    def redemarrer(self):
        self.close()
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable])
        else:
            subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0])])
        QApplication.quit()

    def telecharger_pack(self, cle):
        from . import effets as E
        p = E.PACKS.get(cle)
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
        if ed:
            ed.encart.suivre(t, _("Téléchargement du pack « {n} »", n=p["nom"]))
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
        QMessageBox.about(self, _("À propos de PhilCut"), _(
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
