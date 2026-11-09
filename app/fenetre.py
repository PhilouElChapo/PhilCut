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


def resume_notes(notes, n=4):
    """Les quelques nouveautés de la dernière version (puces « - » du premier « ### ») au lieu des notes brutes."""
    import html as H
    lignes, dans = [], False
    for l in (notes or "").splitlines():
        l = l.strip()
        if l.startswith("### "):
            if dans:
                break
            dans = True
            continue
        if dans and l.startswith("- "):
            lignes.append("• " + H.escape(l[2:]))
    return "<br>".join(lignes[:n])


def progression_maj(tache):
    """Progression du téléchargement de la mise à jour : mise_a_jour.recuperer donne (octets reçus, taille totale)."""
    def suivre(fait, total=0):
        tache.avancer(fait / total if total else 0.0, f"{fait / 1e6:.0f} / {total / 1e6:.0f} Mo" if total else f"{fait / 1e6:.0f} Mo")
    return suivre


class Fenetre(QMainWindow):
    def __init__(self, fichiers=()):
        super().__init__()
        self.params = Parametres()
        from . import projet as _projet_mod
        _projet_mod.PARAMS = self.params          # appareil et Drive pour les liens virtuels (0.9.35)
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
        self.accueil.reprendre.connect(lambda machine, fichiers: self._reprendre(fichiers, machine))
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
        if self.telechargements.non_finis():
            n = len(self.telechargements.non_finis())
            self.encart_global.suivre_message(_("⏸ {n} téléchargement(s) non terminé(s) la dernière fois ; ils reprendront où ils "
                                                "s'étaient arrêtés.", n=n), (_("▶ Reprendre"), lambda: (self.telechargements.reprendre(),
                                                                                                   self.voir_telechargements())), 30000)
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
        QTimer.singleShot(1500, self.synchro_demarrage)
        if self.params.get("creations_purge_derniere") != datetime.date.today().isoformat():
            QTimer.singleShot(20000, self.nettoyer_creations)
        self._catalogues()
        self._minuterie = QTimer(self)
        self._minuterie.timeout.connect(self.ecrire_session)
        self._minuterie.start(60000)
        self._minuterie_secours = QTimer(self)                  # sauvegarde automatique (0.9.22)
        self._minuterie_secours.timeout.connect(self.sauvegarde_auto)
        self.regler_sauvegarde_auto()
        QTimer.singleShot(1200, self.proposer_recuperation)
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
        m.addAction(_("Revenir à une sauvegarde automatique…"), self.revenir_sauvegarde)
        m.addSeparator()
        m.addAction(_("Médias introuvables sur ce poste…"), lambda: self.medias_introuvables())
        m.addAction(_("Retrouver ce projet sur mes autres appareils (Drive)…"), self.preparer_appareils)
        m.addAction(_("Espace PhilCut sur le Drive…"), self.espace_drive)
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
        a.addAction(_("Lecture / pause"), lambda: self._ed(lambda ed: ed.lecture_auto()), "Space")
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
        a.addAction(_("Colonne des médias : complète / repliée"), lambda: self._ed(lambda ed: ed.replier_gauche()), "F3")
        a.addAction(_("Volet de droite : complet / icônes / masqué"), lambda: self._ed(lambda ed: ed.basculer_volet()), "F4")
        a.addAction(_("Personnaliser la barre d'outils…"), self.personnaliser_barre)
        mo = mb.addMenu(_("&Montage"))
        mo.setToolTipsVisible(True)

        def act(ic, lib, aide, fonction, raccourci=None):
            """Libellé court ; l'explication en bulle au survol et dans la barre d'information du bas."""
            a_ = mo.addAction(ic, lib, fonction) if ic is not None else mo.addAction(lib, fonction)
            if raccourci:
                a_.setShortcut(raccourci)
            a_.setToolTip(aide)
            a_.setStatusTip(aide)
            return a_
        for oid in ("vitesse", "recadrer", "stabiliser", "texte", "effets", "goodies", "zone", "sous_titres", "musique", "voix"):
            o = O.outil(oid)
            mo.addAction(icone(o[2]), o[3], lambda _c=False, oid=oid: self._editeur_ou_nouveau().outil(oid))
            # outils voisins, rangés avec leur famille (plus de menu à part)
        act(None, _("Figer l'image…"), _("Le film s'arrête sur l'image de la ligne rouge, avec un cadre photo et une légende, puis reprend"),
            lambda: self._ed(lambda ed: ed.figer_image()))
        sm_ia = mo.addMenu(icone("assistant"), _("Atelier IA (sur ce poste)"))
        for fam, lib in (("image", _("Retoucher l'image du film (cartoon, 3D, peinture…)…")),
                         ("video", _("Vidéo IA sur la partie en jaune (animer l'image, dessin animé, ralenti…)…")),
                         ("logo", _("Logo, intro ou miniature par IA…")), ("musique", _("Créer une musique par IA…"))):
            sm_ia.addAction(lib, lambda fam=fam: self._ed(lambda ed: ed.atelier_ia(fam)))
        sm_ia.addSeparator()
        sm_ia.addAction(_("Séquence IA : une histoire en plusieurs plans (personnages, répliques, musique)…"),
                        lambda: self._ed(lambda ed: ed.sequence_ia()))
        act(icone("effets"), _("Étalonnage du plan…"), _("Couleurs et lumière du plan à la ligne rouge : roues de couleur, avant / après, "
                                                          "auto, accorder sur un autre plan"), lambda: self._ed(lambda ed: ed.etalonner()), "Ctrl+Shift+E")
        act(icone("image"), _("Présentation de photos animée…"), _("Lancer de cartes, explosion en particules, puzzle, mur de photos, "
                                                                     "carrousel 3D, éventail, polaroïds sur une corde"),
            lambda: self._editeur_ou_nouveau().presentation_photos())
        act(icone("clap"), _("Modèles de montage…"), _("Vlog voyage 30 s, Short dynamique, Vol en avion, Souvenirs de famille… : vos rushes "
                                                         "montés à la façon du modèle"), lambda: self._editeur_ou_nouveau().modeles_montage())
        act(icone("sous_titres"), _("Monter par le texte…"), _("Le texte de ce qui est dit : effacer une phrase coupe la vidéo ; « euh » et "
                                                                 "silences enlevés d'un clic"), lambda: self._ed(lambda ed: ed.monter_par_texte()), "Ctrl+T")
        act(icone("assistant"), _("Dites-le en clair…"), _("Une phrase (« coupe les silences et mets une musique calme ») devient des actions"),
            lambda: self._ed(lambda ed: ed.dites_le()))
        act(icone("effets"), _("Transitions automatiques…"), _("A chaque coupe, la transition qui va avec les images et la musique"),
            lambda: self._ed(lambda ed: ed.transitions_auto()))
        act(icone("musique"), _("Bruitages…"), _("Whoosh, impact, déclic, bip… fabriqués sur ce poste, libres de droits"), lambda: self._ed(lambda ed: ed.bruitage()))
        act(icone("clap"), _("Tampons vidéo…"), _("Petites séquences toutes faites (rembobinage, « tadaa », bip…), vos clips, extraits YouTube "
                                                 "et Internet Archive"), lambda: self._ed(lambda ed: ed.tampons()))
        mo.addSeparator()
        act(None, _("Ajouter une piste vidéo"), _("Une piste au-dessus du film : incrustation, image dans l'image, logo"),
            lambda: self._ed(lambda ed: ed.timeline._ajouter_piste("video")))
        act(None, _("Ajouter une piste de sons"), _("Une piste de plus pour une musique, une voix ou des bruitages"),
            lambda: self._ed(lambda ed: ed.timeline._ajouter_piste("audio")))
        mo.addSeparator()
        act(None, _("Début de la partie jaune ici"), _("La partie jaune commence à la ligne rouge (ou double-clic sur la règle des temps)"),
            lambda: self._ed(lambda ed: ed.timeline.marquer_zone(0)), "I")
        act(None, _("Fin de la partie jaune ici"), _("La partie jaune finit à la ligne rouge (ou second double-clic sur la règle)"),
            lambda: self._ed(lambda ed: ed.timeline.marquer_zone(1)), "O")
        act(None, _("Supprimer la partie jaune"), _("Elle est retirée et la suite se recolle"), lambda: self._ed(lambda ed: ed.partie(False)))
        act(None, _("Garder seulement la partie jaune"), _("Tout le reste est retiré"), lambda: self._ed(lambda ed: ed.partie(True)))
        mo.addSeparator()
        act(None, _("Caler les coupes sur le rythme"), _("Chaque coupe tombe sur un temps de la musique"), lambda: self._ed(lambda ed: ed.caler_rythme(False)))
        act(None, _("Caler les coupes sur les mesures"), _("Coupes sur les débuts de mesure : plus posé"), lambda: self._ed(lambda ed: ed.caler_rythme(True)))
        asst = mb.addMenu(_("A&ssistant"))
        asst.addAction(icone("assistant"), _("Analyser et proposer un montage"), lambda: self._editeur_ou_nouveau().outil("assistant"), "Ctrl+Shift+A")
        asst.addAction(icone("info"), _("Fiche vidéo du plan sélectionné"), lambda: self._ed(lambda ed: ed.outil("fiche")))
        asst.addAction(_("Changer le niveau (sans IA, locale, cloud)…"), lambda: self.preferences("Assistant"))
        asst.addAction(_("Connecter une IA (obtenir et tester ma clef)…"), self.connecter_ia)
        fb = mb.addMenu(_("Fa&brique"))
        fb.setToolTipsVisible(True)

        def actf(ic, lib, aide, fonction, raccourci=None):
            a_ = fb.addAction(ic, lib, fonction) if ic is not None else fb.addAction(lib, fonction)
            if raccourci:
                a_.setShortcut(raccourci)
            a_.setToolTip(aide)
            a_.setStatusTip(aide)
            return a_
        actf(icone("fabrique"), _("Logo animé, intro, fin (sur ce poste) · plan vidéo (IA cloud)…"),
             _("Logos, intros et fins animés : dessinés sur ce poste, gratuits. Les plans vidéo générés passent par Flow ou Veo "
               "(IA cloud, votre compte, prix affiché avant)."), self.fabrique, "Ctrl+Shift+F")
        actf(icone("ia"), _("Séquence IA : une histoire en plusieurs plans (personnages, répliques, musique)…"),
             _("Plusieurs plans qui se suivent avec les mêmes personnages (style « à la manière de », images de référence), "
               "leurs répliques et une musique ; vidéo par l'IA de ce poste, un générateur cloud ou Google Flow."),
             lambda: self._ed(lambda ed: ed.sequence_ia()))
        actf(None, _("Nouvelle séquence IA…"), _("Repartir d'une histoire vide (les séquences précédentes restent dans le projet)."),
             lambda: self._ed(lambda ed: ed.sequence_ia(nouvelle=True)))
        actf(icone("musique"), _("Fabrique musique : créer une musique par IA (sur ce poste)…"),
             _("Une fiche musicale (style, ambiance, tempo, tonalité, instruments, voix) devient une consigne solide, améliorable par "
               "l'IA ; s'inspirer d'un morceau ; créé sur ce poste, gratuitement."), lambda: self._ed(lambda ed: ed.fabrique_musique()))
        actf(None, _("Musique en ligne (YouTube Music, YouTube, archives libres)…"),
             _("Chercher, écouter et télécharger le son d'un titre, avec ce qui est permis expliqué."), lambda: self.musique_en_ligne())
        actf(None, _("Créations à refaire ou à calculer…"),
             _("Les créations IA demandées sur un autre appareil, ou dont le fichier manque : les calculer ici gratuitement ou les "
               "refaire, comparer avant / après, sans jamais payer deux fois."), lambda: self._ed(lambda ed: self.creations_a_traiter(ed)))
        actf(None, _("Mes plans IA déjà fabriqués (dossier)…"),
             _("Les plans vidéo générés (Gemini, Kling…) et les logos fabriqués sont gardés dans ce dossier, même s'ils ne sont "
               "plus dans un projet : on les ouvre ou on les glisse dans les médias."),
             self._dossier_fabrique)
        actf(None, _("Atelier de logo (sur ce poste) · idées par l'IA cloud…"),
             _("Créer et modifier un logo sur ce poste ; le bouton « Idées par l'IA » demande des propositions à l'IA cloud (votre clef)."),
             self.atelier_logo)
        fb.addSeparator()
        actf(icone("assistant"), _("Logo, intro ou miniature par IA locale (sur ce poste, gratuit)…"),
             _("Une image dessinée par l'IA de ce poste à partir d'une phrase : rien n'est envoyé, rien n'est payé ; plus lent sans carte graphique."),
             lambda: self._ed(lambda ed: ed.atelier_ia("logo")))
        actf(None, _("Effet vidéo ou image animée par IA locale, à partir du film (sur ce poste)…"),
             _("A partir d'une image ou d'une partie du film : dessin animé, ralenti fluide, agrandir, photo 3D, animer l'image. "
               "L'IA de ce poste ne crée pas encore un plan à partir d'une phrase seule : pour cela, Flow ou le plan vidéo IA cloud."),
             lambda: self._ed(lambda ed: ed.atelier_ia("video")))
        fb.addSeparator()
        actf(icone("image"), _("Vignette YouTube composée (sur ce poste)…"),
             _("Zones de couleur, titre, flèche, pastilles, composées sur ce poste ; propositions par l'IA locale ou cloud, au choix."),
             lambda: self._ed(lambda ed: ed.vignette_composee("vignette")))
        actf(None, _("Image fixe composée à poser dans le film (sur ce poste)…"),
             _("Même fenêtre que la vignette, au format du film, posée au-dessus à la ligne rouge."),
             lambda: self._ed(lambda ed: ed.vignette_composee("image")))
        ou = mb.addMenu(_("&Outils"))
        ou.addAction(_("Publier (YouTube, Instagram, TikTok…)…"), self.publier)
        ou.addAction(icone("nuage"), _("Déposer l'export sur le Drive / NAS…"), self.partager)
        ou.addAction(_("Synchroniser maintenant"), self.synchro_demarrage)
        ou.addAction(_("Centre d'activité (tâches en cours, téléchargements)…"), self.voir_activite)
        ou.addAction(_("Journal des échanges (Drives, IA)…"), self.journal_echanges)
        ou.addAction(_("Ouvrir le dossier des données"), lambda: self.ouvrir_externe(dossier_donnees()))
        ai = mb.addMenu(_("&Aide"))
        ai.addAction(_("Raccourcis clavier"), self.raccourcis)
        ai.addAction(_("Guide de test de la première version"), lambda: webbrowser.open("https://github.com/PhilouElChapo/PhilCut/blob/main/docs/guideline-tests.md"))
        ai.addAction(_("Vérifier les mises à jour…"), lambda: self.verifier_maj(silencieux=False))
        ai.addAction(_("Nouveautés du catalogue (Goodies, modèles, styles)…"), self.voir_nouveautes)
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
        QTimer.singleShot(0, self.tenir_dans_ecran)
        return ed

    def tenir_dans_ecran(self):
        """La fenêtre ne dépasse jamais l'écran (ouvrir un projet ne doit pas l'agrandir sous la barre des tâches)."""
        if self.isMaximized() or self.isFullScreen():
            return
        ecr = self.screen() or QApplication.primaryScreen()
        if not ecr:
            return
        dispo = ecr.availableGeometry()
        g = self.frameGeometry()
        if dispo.contains(g):
            return
        marge_h = g.height() - self.height()
        marge_l = g.width() - self.width()
        w = min(self.width(), dispo.width() - marge_l)
        h = min(self.height(), dispo.height() - marge_h)
        self.resize(max(640, w), max(400, h))
        g = self.frameGeometry()
        self.move(max(dispo.left(), min(g.left(), dispo.right() - g.width())), max(dispo.top(), min(g.top(), dispo.bottom() - g.height())))

    def _maj_titre(self, ed):
        i = self.onglets.indexOf(ed)
        if i >= 0:
            self.onglets.setTabText(i, ed.projet.nom + (" •" if ed.projet.modifie else ""))

    def rushes_vers_projet(self):
        filtres = _("Vidéos, sons, images") + " (*.mp4 *.mov *.mkv *.m4v *.webm *.avi *.mts *.m2ts *.3gp *.mp3 *.wav *.m4a *.jpg *.jpeg *.png *.heic);;" + _("Tous") + " (*)"
        from .session import dossier_systeme
        depart = self.params.get("dossier_rushes") or dossier_systeme("videos")      # Vidéos du système, puis le dernier dossier
        chemins, _f = QFileDialog.getOpenFileNames(self, _("Rushes du nouveau projet"), depart, filtres)
        if not chemins:
            return
        self.params["dossier_rushes"] = os.path.dirname(chemins[0])
        vert = sum(1 for c in chemins if c.lower().endswith(".mp4") and False)
        ed = self.nouveau_projet("16:9", os.path.splitext(os.path.basename(chemins[0]))[0])
        ed.importer(chemins)
        ed.outil("assistant")

    def dialogue_ouvrir(self):
        from .session import dossier_systeme
        p, _f = QFileDialog.getOpenFileName(self, _("Ouvrir"), self.params.get("dernier_dossier") or dossier_systeme("videos"),
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
            try:                                   # liens virtuels : même fichier ailleurs sur ce poste, ou copie légère du Drive
                r = p.retrouver_medias()
            except Exception:    # noqa: BLE001
                r = {"trouves": [], "copies": [], "manquants": p.manquants()}
            ed = self.ajouter_onglet(p)
            if r["trouves"] or r["copies"]:
                p.modifie = True
            if r["manquants"] or r["copies"]:
                n = len(r["manquants"])
                texte = (_("{n} média(s) introuvable(s) sur ce poste ; ils restent dans le projet, grisés.", n=n) if n else "")
                if r["copies"]:
                    texte += (" " if texte else "") + _("{c} vidéo(s) montée(s) sur leur copie légère du Drive.", c=len(r["copies"]))
                ed.encart.suivre_message(texte, (_("Où sont-ils ?…"), lambda: self.medias_introuvables(ed)), 30000)
            elif r["trouves"]:
                ed.encart.message(_("{n} média(s) retrouvé(s) à un autre emplacement sur ce poste.", n=len(r["trouves"])), 6000)
            try:                                       # créations IA à calculer ou à refaire : proposées, jamais lancées seules
                from . import recettes_ia
                n_rec = len(recettes_ia.a_traiter(p, self.params))
            except Exception:      # noqa: BLE001
                n_rec = 0
            if n_rec:
                QTimer.singleShot(1500, lambda: ed.encart.suivre_message(
                    _("{n} création(s) IA à refaire ou à calculer sur ce poste.", n=n_rec),
                    (_("Voir la liste…"), lambda: self.creations_a_traiter(ed)), 30000))
            if getattr(p, "plus_recent", False):
                QMessageBox.information(self, _("Ouvrir"), _("Ce projet a été enregistré par une version plus récente de PhilCut (un autre "
                                                              "appareil à jour). Il s'ouvre ; ce que cette version ne connaît pas est "
                                                              "gardé tel quel et sera réécrit à l'identique. Pensez à mettre PhilCut à jour."))
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
        if getattr(p, "conflit", None):
            c = p.conflit
            ed.encart.suivre_message(_("Ce projet avait aussi été modifié sur {a} ({q}). Votre version, la plus récente, est enregistrée ; "
                                       "l'autre est gardée dans Fichier › Revenir à une sauvegarde automatique.", a=c["appareil"], q=c["quand"].replace("T", " ")),
                                     (_("Voir les versions"), self.revenir_sauvegarde), 30000)
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
        from . import secours
        secours.effacer(p)                        # enregistré : les copies de secours ne servent plus
        ed._secours_empreinte = None
        self._maj_titre(ed)
        self.accueil.rafraichir()
        self.ecrire_session()
        if not getattr(self, "_sans_proposition_drive", False):
            try:
                from .dialogues_drive import proposer_apres_enregistrement
                proposer_apres_enregistrement(ed)
            except Exception as e:    # noqa: BLE001
                ed.encart.message(_("Dépôt sur le Drive non proposé : {e}", e=e), 6000)
        return True

    def medias_introuvables(self, ed=None):
        ed = ed or self.editeur_courant()
        if ed:
            from .dialogues_drive import DialogueManquants
            DialogueManquants(ed).exec()

    def espace_drive(self):
        from .dialogues_drive import DialogueEspaceDrive
        utilises = {m.get("copie_drive") for ed in self.editeurs() for m in ed.projet.medias if m.get("copie_drive")}
        DialogueEspaceDrive(self, self.params, frozenset(utilises)).exec()

    def preparer_appareils(self):
        ed = self.editeur_courant()
        if not ed:
            return
        ed.projet.d.pop("appareils_preparer", None)
        from .dialogues_drive import proposer_apres_enregistrement
        from . import drive_philcut as DP
        if not DP.disponible(self.params):
            QMessageBox.information(self, _("Drive"), _("Choisissez d'abord un lieu de synchronisation : Préférences › Comptes et synchro."))
            return
        avant = (DP.a_copier(ed.projet), [m for m in ed.projet.medias if os.path.exists((m.get("chemin") or "") + ".ia.json") and not m.get("copie_drive")])
        if not avant[0] and not avant[1]:
            ed.encart.message(_("Tout est déjà prêt : les vidéos ont leur copie légère et les créations sont déposées."), 6000)
            return
        proposer_apres_enregistrement(ed)

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
        from . import secours
        secours.effacer(w.projet)                  # fermeture voulue : enregistré, ou « Ne pas enregistrer »
        w.apercu.arreter()
        w.preparation.fermer()
        w.catalogue.fermer()
        self.onglets.removeTab(i)
        w.deleteLater()
        self.ecrire_session()

    def afficher(self):
        """Première ouverture : plein écran (maximisée), la barre d'état du bas toujours visible au-dessus de la barre des
        tâches ; ensuite la taille et la place de la dernière fois, si elles tiennent dans l'écran actuel."""
        from PySide6.QtCore import QByteArray, QRect
        g = self.params.get("fenetre_geometrie")
        ok = False
        if g and not self.params.get("fenetre_maximisee", True):
            try:
                self.restoreGeometry(QByteArray.fromBase64(g.encode()))
                ecr = self.screen() or QApplication.primaryScreen()
                dispo = ecr.availableGeometry() if ecr else QRect()
                ok = dispo.isNull() or dispo.contains(self.frameGeometry())
            except Exception:    # noqa: BLE001
                ok = False
        if ok:
            self.show()
        else:
            self.showMaximized()

    @staticmethod
    def description_taches(taches):
        """« • Export : 42 % — encodage… » : une ligne par opération en cours."""
        lignes = []
        for t in taches:
            f, texte = getattr(t, "dernier", (0.0, ""))
            titre = getattr(t, "titre", "") or _("Opération")
            if "|" in (texte or ""):             # progression brute (octets) : on ne la montre pas
                texte = ""
            lignes.append(f"• {titre} : {int(f * 100)} %" + (f" — {texte[:80]}" if texte else ""))
        return "\n".join(lignes)

    def _quitter_malgre(self, en_cours):
        """Dire quelles opérations tournent (comme PhilPDF), les montrer d'un clic, ou quitter quand même."""
        m = QMessageBox(self)
        m.setIcon(QMessageBox.Question)
        m.setWindowTitle(_("Quitter"))
        m.setText(_("{n} opération(s) encore en cours :", n=len(en_cours)))
        m.setInformativeText(self.description_taches(en_cours) + "\n\n" + _("Les quitter maintenant les arrête."))
        voir = m.addButton(_("Voir les opérations"), QMessageBox.ActionRole)
        quitter = m.addButton(_("Quitter quand même"), QMessageBox.DestructiveRole)
        m.addButton(_("Rester"), QMessageBox.RejectRole)
        m.exec()
        if m.clickedButton() is voir:
            self.voir_activite()
            return False
        return m.clickedButton() is quitter

    def _retenir_geometrie(self):
        try:
            self.params["fenetre_maximisee"] = self.isMaximized()
            if not self.isMaximized():
                self.params["fenetre_geometrie"] = bytes(self.saveGeometry().toBase64()).decode()
        except Exception:    # noqa: BLE001
            pass

    def closeEvent(self, e):
        self._retenir_geometrie()
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
        if en_cours and not self._quitter_malgre(en_cours):
            e.ignore()
            return
        for t in en_cours:
            t.stopper()
        self.statusBar().showMessage(_("Fermeture : arrêt des opérations en cours et du son…"))
        self.arreter_sons()
        for ed in self.editeurs():
            try:
                ed.apercu.arreter()
                ed.preparation.fermer()
                ed.catalogue.fermer()
            except Exception:    # noqa: BLE001 : on ferme quand même
                pass
        self.ecrire_session()
        self.params.enregistrer()
        from . import secours
        for ed in self.editeurs():                 # fermeture normale : rien à récupérer au prochain démarrage
            secours.effacer(ed.projet)
        self.attendre_taches(3000)
        e.accept()

    @staticmethod
    def arreter_sons():
        """Tous les lecteurs audio et vidéo arrêtés et vidés avant de quitter : le service audio de Windows n'est pas
        laissé avec un flux ouvert au moment où le programme s'arrête."""
        try:
            from PySide6.QtMultimedia import QMediaPlayer
            from PySide6.QtCore import QUrl
        except ImportError:
            return
        for w in QApplication.topLevelWidgets():
            for lp in w.findChildren(QMediaPlayer):
                try:
                    lp.stop()
                    lp.setSource(QUrl())
                except RuntimeError:
                    pass
        QApplication.processEvents()

    def attendre_taches(self, ms=30000):
        """Demande l'arrêt de toutes les tâches de fond puis attend, au plus ms en tout (pas par tâche), en laissant la
        fenêtre répondre : Windows ne la croit jamais « bloquée ». Ce qui ne s'arrête pas à temps (un téléchargement
        coincé sur le réseau) est abandonné proprement par la sortie directe du programme."""
        import time as _t
        autres = [self.telechargements.tache] if getattr(self, "telechargements", None) and self.telechargements.tache else []
        taches = list(self.taches) + sum((list(ed.taches) for ed in self.editeurs()), []) + autres
        for t in taches:
            try:
                if t.isRunning():
                    t.stopper()
            except RuntimeError:
                pass
        fin = _t.monotonic() + ms / 1000
        while _t.monotonic() < fin:
            try:
                vivantes = [t for t in taches if t.isRunning()]
            except RuntimeError:
                vivantes = []
            if not vivantes:
                return
            QApplication.processEvents()
            vivantes[0].wait(50)

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
        utilises = {c["media"] for c in ed.projet.clips}
        absents = [m for m in ed.projet.medias if m["id"] in utilises and not os.path.exists(m.get("chemin") or "")]
        legeres = [m for m in ed.projet.medias if m["id"] in utilises and m.get("copie_legere")]
        if absents:
            b = QMessageBox.question(self, _("Exporter"), _("{n} média(s) utilisé(s) dans le film sont introuvables sur ce poste : {l}.\n\n"
                                                            "Les rattacher d'abord (recommandé) ?", n=len(absents),
                                                            l=", ".join(m.get("nom", "") for m in absents[:5])),
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if b == QMessageBox.Cancel:
                return
            if b == QMessageBox.Yes:
                self.medias_introuvables(ed)
                return
        if legeres:
            QMessageBox.information(self, _("Exporter"), _("{n} vidéo(s) seront exportées depuis leur copie légère 720p (l'original n'est "
                                                           "pas sur ce poste) : la qualité de ces passages sera réduite.", n=len(legeres)))
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
        noms = {sortie}
        for dest2 in d.autres_formats():                    # exports en série (0.9.25) : un fichier par format coché
            if dest2 == dest:
                continue
            nom = export.nom_autre(sortie, dest2)
            if nom in noms:
                b, x = os.path.splitext(nom)
                nom = f"{b}_{dest2}{x}"
            noms.add(nom)
            travaux.append((export.autre_format(ed.projet, dest2), nom, dest2))

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

    def fabrique(self, image=None, texte=None, recette=None):
        ed = self._editeur_ou_nouveau()
        from .dialogues_video import DialogueFabrique
        d = DialogueFabrique(self, ed.projet, self.params)
        if recette:                                    # 0.9.40 : reprendre un plan IA avec ses réglages d'origine
            d.onglets.setCurrentIndex(1)
            d.sujet.setPlainText(recette.get("sujet") or "")
            if recette.get("style"):
                d.style.setCurrentText(recette["style"])
            d.duree_ia.setValue(int(recette.get("duree") or 8))
            d.consigne.setPlainText(recette.get("consigne") or "")
            if recette.get("voie") == "cloud" and d.voie_veo.isEnabled():
                d.voie_veo.setChecked(True)
                i = d.modele_veo.findData(recette.get("modele"))
                if i >= 0:
                    d.modele_veo.setCurrentIndex(i)
            else:
                d.voie_flow.setChecked(True)
        if image:
            d.image.setText(image)
            d.onglets.setCurrentIndex(0)
        if texte:
            d.texte.setText(texte)
        if d.exec() != QDialog.Accepted:
            if getattr(d, "vers_sequence", False):
                ed.sequence_ia()
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

            from . import intros as IN
            oi = d.options_intro()

            def travail(tache):
                if modele in IN.MODELES:
                    return IN.fabriquer(sortie, modele, texte, sous, L, H, ed.projet.cadence, duree, fond=oi["fond"], couleurs=oi["couleurs"],
                                        image_film=oi["image_film"], logo=image, progression=lambda f: tache.avancer(f))
                return FAB.fabriquer_logo(sortie, texte, modele, L, H, ed.projet.cadence, duree, progression=lambda f: tache.avancer(f), image_logo=image, sous_texte=sous)
            t = Tache(travail, _("Fabrique"))
            self.taches.append(t)
            ed.encart.suivre(t, _("Fabrication du logo « {t} »", t=texte))
            t.fini.connect(lambda r, e: self._logo_pret(ed, sortie, usage, e))
            t.start()
        else:
            consigne = d.consigne.toPlainText().strip() or FAB.consigne_plan("illustration", d.sujet.toPlainText().strip(), d.style.currentText().strip(), d.duree_ia.value(), ed.projet.format, params=self.params, traduire=True)
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
                dossier = FAB.dossier_plans()
                sortie = os.path.join(dossier, f"plan_ia_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
                rec = FAB.recette_plan(d, consigne, "cloud", modele, ed.projet.format)
                rec.update(paye=True, cout_max=prix)
                params, duree_ia, fmt = self.params, d.duree_ia.value(), ed.projet.format

                def travail(tache):
                    # Google ne dit pas où il en est : PhilCut montre le temps écoulé et une barre estimée (pas un faux « 2 % »)
                    import threading
                    import time as _t
                    fin = threading.Event()
                    t0 = _t.monotonic()

                    def battement():
                        while not fin.wait(1.0):
                            e = int(_t.monotonic() - t0)
                            tache.avancer(min(0.95, e / 150.0), _("{m} calcule le plan : {e} s écoulées. D'habitude 1 à 3 min ; la barre est une "
                                                                  "estimation, le service ne donne pas son avancement.", m=fourn, e=e))
                    threading.Thread(target=battement, daemon=True).start()
                    try:
                        return GV.generer(params, modele, consigne, sortie, duree_ia, fmt, progression=None, arret=lambda: tache.arret)
                    finally:
                        fin.set()

                def fini(r, e):
                    if e:
                        QMessageBox.warning(self, _("Plan IA"), str(e))
                        return
                    from . import creations
                    creations.ecrire(sortie, rec)
                    ed.importer([sortie])
                    ed.encart.suivre_message(_("Plan IA rangé dans {d} ; il est dans les médias du projet.", d=dossier),
                                             (_("Ouvrir le dossier"), lambda: self._ouvrir_dans_systeme(dossier)), 30000)
                t = Tache(travail, _("Plan IA"))
                self.taches.append(t)
                ed.encart.suivre(t, _("Génération du plan par IA"))
                t.fini.connect(fini, Qt.QueuedConnection)
                t.start()
            else:
                avant = FAB.preparer_flow(consigne, d.dossier.text().strip())
                self._surveiller_flow(ed, d.dossier.text().strip(), avant, FAB.recette_plan(d, consigne, "flow", "", ed.projet.format))

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
                    from .projet import decaler_suivi
                    for x in ed.projet.titres + ed.projet.goodies:
                        x["debut"] += d
                        x["fin"] += d
                        decaler_suivi(x, lambda t: t + d)
                    ed.projet.ajouter_clip(m["id"], "video", 0.0)
                else:
                    ed.projet.ajouter_clip(m["id"], "video")
                ed.projet.ranger("video")
                ed.rafraichir()
            QTimer.singleShot(1500, placer)

    def _surveiller_flow(self, ed, dossier, avant, recette=None):
        """Attente du clip téléchargé depuis Flow : tâche suivie dans la barre du bas (étape, temps écoulé, Arrêter),
        puis aperçu avant intégration."""
        def travail(tache):
            return FAB.attendre_clip(dossier, avant, tache)
        t = Tache(travail, _("Clip Flow"))
        self.taches.append(t)
        ed.encart.suivre(t, _("Consigne copiée, Flow ouvert : PhilCut attend le clip dans « {d} »", d=os.path.basename(dossier) or dossier))

        def fini(r, e):
            if e or not r:
                return
            from .dialogues_video import DialogueClipRecu
            from . import creations
            for chemin in r:
                if recette:                            # la recette suit le clip : « Reprendre la création » rouvre la Fabrique remplie
                    creations.ecrire(chemin, recette)
                DialogueClipRecu(ed, chemin, _("Clip reçu de Flow")).exec()
        t.fini.connect(fini, Qt.QueuedConnection)
        t.start()

    def musique(self):
        ed = self._editeur_ou_nouveau()
        m = QMenu(self)
        ac = "#9b7bff"                                     # mêmes petites icônes, couleur PhilCut, pour toutes les lignes
        m.addAction(icone("importer", ac), _("Importer une musique…"), lambda: ed.importer())
        m.addAction(icone("musique", ac), _("Mes musiques (chercher, écouter, poser)…"), lambda: self.mes_musiques(ed))
        m.addAction(icone("telecharger", ac), _("Bibliothèque musicale libre (chercher, écouter, télécharger)…"), lambda: self.bibliotheque_musicale(ed))
        m.addAction(icone("telecharger", ac), _("Musique en ligne (YouTube Music, YouTube, archives libres)…"), lambda: self.musique_en_ligne(ed))
        m.addAction(icone("ia", ac), _("Fabrique musique : créer une musique par IA (sur ce poste)…"), lambda: ed.fabrique_musique())
        from .widgets import fenetre_choix
        fenetre_choix(self, m, _("Musique"), _("D'où vient la musique ? Elle est posée sur la piste Musique, sous la vidéo."))

    def creations_a_traiter(self, ed=None):
        ed = ed or self.editeur_courant()
        if ed:
            from .dialogues_recettes import DialogueCreations
            DialogueCreations(ed).exec()

    def musique_en_ligne(self, ed=None):
        """Chercher, écouter, télécharger un son (YouTube Music, YouTube, archives libres) ; le poser dans le film."""
        ed = ed or self._editeur_ou_nouveau()
        from .dialogues_musique_ia import DialogueMusiqueEnLigne
        DialogueMusiqueEnLigne(self, self.params, poser=lambda chemin: self._poser_musique(ed, chemin)).exec()

    def mes_musiques(self, ed=None):
        """Mon dossier de musiques et les musiques libres téléchargées, dans une fenêtre (recherche, classement, écoute)."""
        ed = ed or self._editeur_ou_nouveau()
        from .dialogues_mes_musiques import DialogueMesMusiques
        d = DialogueMesMusiques(self, self.params)
        if d.exec() == QDialog.Accepted and d.chemin:
            self._poser_musique(ed, d.chemin)
            self.statusBar().showMessage(_("Musique posée sur la piste Musique : {n}", n=os.path.basename(d.chemin)), 6000)

    def _choisir_dossier_musiques(self):
        from .session import dossier_systeme
        d = QFileDialog.getExistingDirectory(self, _("Mon dossier de musiques"), self.params.get("musiques_dossier") or dossier_systeme("musique"))
        if d:
            self.params["musiques_dossier"] = d
            self.params.enregistrer()
            self.statusBar().showMessage(_("Dossier de musiques : {d}", d=d), 6000)

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
        m.addSeparator()
        a = m.addAction(_("Seulement les échanges radio (pilote, tour de contrôle)…"), ed.radio)
        a.setToolTip(_("Pour un film d'avion : PhilCut écoute le son, garde seulement les phrases dites à la radio et les écrit en haut "
                       "de l'image, style radio. Les autres paroles ne sont pas sous-titrées."))
        m.setToolTipsVisible(True)
        if ed.projet.d.get("sous_titres"):
            m.addAction(_("Retirer les sous-titres"), lambda: (ed.projet.marquer(), ed.projet.d.__setitem__("sous_titres", []), ed.rafraichir()))
        from .widgets import fenetre_choix
        fenetre_choix(self, m, _("Sous-titres"), _("Les paroles du film écrites à l'image, sur ce poste (rien n'est envoyé)."))

    def _importer_srt(self, ed):
        from . import titres
        from .widgets import ouvrir_fichier
        p = ouvrir_fichier(self, _("Sous-titres"), "SRT (*.srt)", "documents", self.params)
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
            from .widgets import fenetre_choix
            fenetre_choix(self, m, _("Voix"), _("Voix off, voix de synthèse, doublage ; cliquez d'abord un plan pour retoucher sa voix."))
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
        from .widgets import fenetre_choix
        fenetre_choix(self, m, _("Voix de « {n} »", n=c.get("nom", "")), _("Voix off, synthèse, doublage, ou une retouche de la voix de ce "
                                                                        "plan (✓ : déjà appliquée ; la choisir à nouveau la retire)."))

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
        from .widgets import ouvrir_fichier
        p = ouvrir_fichier(self, _("Importer des préférences"), _("Préférences PhilCut") + " (*.json *.philcutprefs)", "documents", self.params)
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
        t.moveCursor(t.textCursor().MoveOperation.End)
        v.addWidget(t)
        h = QHBoxLayout()
        b_cp = QPushButton(_("Copier"))
        b_cp.setToolTip(_("Copie la sélection, ou tout le journal si rien n'est sélectionné (pour le coller dans un message)"))

        def copier():
            txt = t.textCursor().selectedText().replace("\u2029", "\n") or t.toPlainText()
            QApplication.clipboard().setText(txt)
            b_cp.setText(_("✓ Copié"))
            QTimer.singleShot(1800, lambda: b_cp.setText(_("Copier")))
        b_cp.clicked.connect(copier)
        h.addWidget(b_cp)
        b_ou = QPushButton(_("Ouvrir le fichier"))
        b_ou.clicked.connect(lambda: self._ouvrir_dans_systeme(chemin()))
        h.addWidget(b_ou)
        h.addStretch(1)
        b_f = QPushButton(_("Fermer"))
        b_f.clicked.connect(d.reject)
        h.addWidget(b_f)
        v.addLayout(h)
        d.exec()

    def _dossier_fabrique(self):
        """Vidéos › PhilCut › Plans IA ; les plans et logos d'avant 0.9.40 restent dans l'ancien dossier, ouvert aussi s'il en a."""
        d = FAB.dossier_plans()
        self._ouvrir_dans_systeme(d)
        ancien = os.path.join(dossier_donnees(), "fabrique")
        if os.path.isdir(ancien) and os.listdir(ancien):
            self._ouvrir_dans_systeme(ancien)

    def _ouvrir_dans_systeme(self, chemin):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        if chemin and os.path.exists(chemin):
            QDesktopServices.openUrl(QUrl.fromLocalFile(chemin))

    def raccourcis(self):
        QMessageBox.information(self, _("Raccourcis"), _(
            "Espace : lecture / pause\nC : couper au curseur\nSuppr : supprimer et refermer (Maj+Suppr : laisser un trou)\n"
            "← → : image par image (Maj : seconde)\nOrigine / Fin : début / fin\nMolette : zoom de la timeline (Maj + molette : défiler) · Ctrl+0 : tout voir\nDouble-clic sur la règle : début puis fin de la partie jaune\n"
            "Ctrl+Z / Ctrl+Y : annuler / rétablir\nCtrl+I : importer · Ctrl+S : enregistrer · Ctrl+E : exporter\nF4 : volet de droite\n"
            "Ctrl+T : monter par le texte · Ctrl+Maj+E : étalonnage du plan\nCtrl + molette, ou molette sur les noms des pistes : monter / descendre dans les pistes\n"
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
        texte = _("PhilCut {n} est disponible (vous avez {v}).", n=version, v=VERSION) + \
            (f"<br><span style='color:#999'>{resume_notes(notes)}</span>" if resume_notes(notes) else "")
        self.accueil.proposer(texte, _("Télécharger et installer"), lambda: self._installer_maj(paquet, version))
        self.onglets.setCurrentIndex(0) if not silencieux else None

    def _installer_maj(self, paquet, version=""):
        """Fenêtre de mise à jour : progression visible tout de suite (Mo, vitesse, temps restant), arrêt possible,
        puis « Installer et redémarrer ». Suivie aussi dans la barre du bas et le Centre d'activité."""
        from .dialogues_maj import DialogueMaj
        d = getattr(self, "_dialogue_maj", None)
        if d is not None and d.tache.isRunning():
            d.show()
            d.raise_()
            return
        d = DialogueMaj(self, version or _("nouvelle version"), paquet)
        self._dialogue_maj = d
        t = d.demarrer()
        self.taches.append(t)
        try:
            self.encart_global.suivre(t, _("Téléchargement de la mise à jour"), action=(_("Installer et redémarrer"), d.installer),
                                      pendant=(_("Afficher"), lambda: (d.showNormal(), d.raise_())))
            self.centre.suivre(t, _("Mise à jour de PhilCut"))
        except Exception:      # noqa: BLE001 : la fenêtre suffit
            pass

    def _catalogues(self):
        """Catalogues d'effets : copie locale tout de suite, mise à jour depuis GitHub en arrière-plan (sans bloquer)."""
        import threading
        from . import effets as E, catalogue_ligne
        from . import nouveautes as NV
        E.catalogue_en_ligne(reseau=False)
        NV.integrer(reseau=False)
        if os.environ.get("PHILCUT_SANS_RESEAU") or not self.params.get("effets_en_ligne", True):
            return
        fil = threading.Thread(target=lambda: [catalogue_ligne.telecharger(n, 8) for n in ("effets.json", "effets_gl.json", "effets_ia.json", NV.FICHIER, "elements.json")],
                               daemon=True)
        fil.start()

        def fusion():
            if fil.is_alive():
                QTimer.singleShot(2000, fusion)
            else:
                E.catalogue_en_ligne(reseau=False)
                NV.integrer(reseau=False)
                self.params["nouveautes_verifie"] = datetime.datetime.now().strftime("%d/%m/%Y %Hh%M")
                n = NV.nombre_nouveaux(self.params)
                if n:                                  # discret : la barre du bas, avec le chemin pour les voir
                    self.statusBar().showMessage(_("✦ {n} nouveauté(s) dans le catalogue : Aide › Nouveautés du catalogue.", n=n), 15000)
        QTimer.singleShot(2000, fusion)

    # ---------------------------------------------------------------- session partagee
    # ---------------------------------------------------------------- Drive en direct, NAS, FTP (0.9.10)
    def _compte_synchro(self):
        if not self.params.get("synchro", True):
            return None
        try:
            from . import miroir
            return miroir.compte_drive(self.params)
        except Exception:      # noqa: BLE001
            return None

    # ---------------------------------------------------------------- sauvegarde automatique (0.9.22)
    def _maj_bouton_synchro(self, recus, envoyes):
        """Bouton discret dans la barre du bas : la dernière synchronisation ; un clic montre ce qui a été échangé (0.9.31)."""
        from PySide6.QtWidgets import QToolButton
        b = getattr(self, "_b_synchro", None)
        if b is None:
            b = QToolButton()
            b.setAutoRaise(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(self.voir_synchro)
            self.statusBar().addPermanentWidget(b)
            self._b_synchro = b
        b.setText(_("⇅ {h} : {r} reçu(s), {e} envoyé(s)", h=datetime.datetime.now().strftime("%Hh%M"), r=recus, e=envoyes))
        b.setToolTip(_("Cliquez pour voir ce qui a été reçu et envoyé"))

    def voir_synchro(self):
        from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
        from . import miroir
        d = QDialog(self)
        d.setWindowTitle(_("Ce qu'échange la synchronisation"))
        d.resize(720, 460)
        v = QVBoxLayout(d)
        t = QLabel(_("Chaque minute, PhilCut échange avec votre Drive les fichiers qui ont vraiment changé : réglages communs, projets "
                     "ouverts, bibliothèque… Jamais vos vidéos. Voici les dernières synchronisations qui ont échangé quelque chose."))
        t.setWordWrap(True)
        v.addWidget(t)
        arbre = QTreeWidget()
        arbre.setHeaderLabels([_("Quand"), _("Fichier"), _("Ce que c'est")])
        arbre.setColumnWidth(0, 150)
        arbre.setColumnWidth(1, 200)
        arbre.setWordWrap(True)
        for h in miroir.HISTORIQUE:
            tete = QTreeWidgetItem([f"{h['quand']}", h["lieu"], ""])
            for sens, rel in h["fichiers"]:
                QTreeWidgetItem(tete, ["↑ " + _("envoyé") if sens == "envoye" else "↓ " + _("reçu"), rel, miroir.expliquer(rel)])
            arbre.addTopLevelItem(tete)
            tete.setExpanded(True)
        if not miroir.HISTORIQUE:
            arbre.addTopLevelItem(QTreeWidgetItem(["", _("Rien d'échangé depuis le démarrage."), ""]))
        v.addWidget(arbre, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(d.reject)
        v.addWidget(bb)
        d.exec()

    def voir_nouveautes(self):
        from .dialogues_nouveautes import DialogueNouveautes
        d = DialogueNouveautes(self, self.params)
        d.exec()
        return d

    def regler_sauvegarde_auto(self):
        from . import secours
        m = int(self.params.get("secours_minutes", secours.INTERVALLE_DEFAUT) or 0)
        if m:
            self._minuterie_secours.start(m * 60000)
        else:
            self._minuterie_secours.stop()

    def sauvegarde_auto(self):
        """Copie de secours de chaque projet modifié depuis la dernière copie ; le fichier de l'utilisateur n'est pas touché."""
        import hashlib, json
        from . import secours
        n = 0
        for ed in self.editeurs():
            if not ed.projet.modifie:
                continue
            secours.cle(ed.projet)
            emp = hashlib.md5(json.dumps(ed.projet.d, sort_keys=True, default=str).encode()).hexdigest()
            if emp == getattr(ed, "_secours_empreinte", None):
                continue
            try:
                secours.sauver(ed.projet, int(self.params.get("secours_versions", secours.VERSIONS_DEFAUT) or 5), self.params.get("machine", ""))
                ed._secours_empreinte = emp
                n += 1
            except OSError:
                pass
        if n:
            self.statusBar().showMessage(_("Sauvegarde automatique : {h}", h=datetime.datetime.now().strftime("%Hh%M")), 4000)
        return n

    def proposer_recuperation(self):
        """Au démarrage : des copies de secours restent, PhilCut ne s'est pas fermé normalement. On propose de reprendre."""
        from . import secours
        ouverts = {ed.projet.d.get("secours_id") for ed in self.editeurs()}
        liste = [r for r in secours.a_recuperer(ouverts) if r["plus_recent"]]
        if not liste:
            for r in secours.a_recuperer(ouverts):              # rien de plus récent que le fichier enregistré : inutile
                secours.jeter(r["cle"])
            return None
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and not getattr(self, "_recuperation_test", False):
            return None
        d = DialogueRecuperation(self, liste)
        d.exec()
        return d

    def revenir_sauvegarde(self):
        ed = self.editeur_courant()
        if not ed:
            return
        from . import secours
        v = secours.versions(secours.cle(ed.projet))
        if not v:
            QMessageBox.information(self, _("Sauvegardes automatiques"), _("Pas encore de sauvegarde automatique pour ce projet "
                                                                            "(une copie est faite chaque minute dès qu'il est modifié)."))
            return
        d = DialogueVersions(self, ed, v)
        d.exec()

    def nettoyer_creations(self, silencieux=True):
        """Une fois par jour, en tâche de fond : les créations IA plus vieilles que la durée choisie (Préférences › Assistant
        et IA) et qu'aucun projet récent ou ouvert n'utilise sont supprimées. La barre du bas le dit."""
        from . import creations as CR
        from .taches import Tache
        jours = int(self.params.get("creations_purge_jours", CR.DUREE_DEFAUT) or 0)
        self.params["creations_purge_derniere"] = datetime.date.today().isoformat()
        self.params.enregistrer()
        if not jours:
            return None
        projets = [ed.projet for ed in self.editeurs()]
        t = Tache(lambda tache: CR.nettoyer(jours, CR.en_usage(self.params, projets)), _("Créations IA"))

        def fin(r, err):
            if not err and r and r[0]:
                self.statusBar().showMessage(_("Créations IA de plus de {j} jours, utilisées par aucun projet : {n} fichier(s) supprimé(s), "
                                               "{m} Mo libérés.", j=jours, n=r[0], m=round(r[1] / 1e6, 1)), 12000)
        t.fini.connect(fin, Qt.QueuedConnection)
        self.taches.append(t)
        t.start()
        return t

    def synchro_demarrage(self):
        """Au démarrage, comme PhilPDF : ce qui arrive de vos autres postes (réglages, tampons, session…) est montré
        dans la fenêtre « Synchronisation avec … » ; sinon, l'échange se fait sans rien demander. La barre du bas dit
        ce qui se passe. Ensuite seulement, la session des autres postes est lue (projets ouverts ailleurs)."""
        compte = self._compte_synchro()
        if compte is None:
            self.verifier_session()
            return
        from . import miroir, synchro_plan
        lieu = miroir.libelle_compte(compte)
        self.statusBar().showMessage(_("Synchronisation avec {l} : recherche de ce qui a changé…", l=lieu))

        def plan(t):
            t.avancer(0.1, _("Synchronisation avec {l} : recherche de ce qui a changé…", l=lieu))
            return synchro_plan.decrire(miroir.planifier(self.params, compte), self.params, compte)
        t = Tache(plan, _("Synchronisation"))
        self.taches.append(t)
        try:
            self.centre.suivre(t, _("Synchronisation avec {l}", l=lieu))
        except Exception:      # noqa: BLE001
            pass

        def vu(lignes, err):
            if err:
                self.statusBar().showMessage(_("✕ Synchronisation avec {l} impossible : {e}. Nouvel essai dans une minute.", l=lieu,
                                               e=str(err)[:160]), 15000)
                self.verifier_session()
                return
            lignes = lignes or []
            choix = None
            if synchro_plan.merite_fenetre(lignes):
                d = synchro_plan.DialoguePlan(self, lignes, lieu)
                if d.exec() != QDialog.Accepted:
                    self.statusBar().showMessage(_("Synchronisation remise à plus tard : rien n'a été reçu ni envoyé."), 8000)
                    self.verifier_session()
                    return
                choix = d.choisis()
            self._synchroniser(compte, choix=choix, apres=self.verifier_session)
        t.fini.connect(vu, Qt.QueuedConnection)
        t.start()

    def _synchroniser(self, compte, choix=None, sens=None, apres=None, silencieux=False):
        """Echange avec le lieu de synchronisation en tâche de fond ; puis les réglages venus d'un autre poste sont repris."""
        from . import miroir
        if getattr(self, "_tache_synchro", None) is not None and self._tache_synchro.isRunning():
            return self._tache_synchro
        lieu = miroir.libelle_compte(compte)

        def travail(t):
            t.avancer(0.2, _("Synchronisation avec {l} : envoi et réception…", l=lieu))
            return miroir.synchroniser(self.params, compte, choix=choix, sens=sens)
        t = Tache(travail, _("Synchronisation"))
        self._tache_synchro = t
        self.taches.append(t)
        if not silencieux:
            self.statusBar().showMessage(_("Synchronisation avec {l} : envoi et réception…", l=lieu))

        def fin(r, err):
            if err:
                if not silencieux:
                    self.statusBar().showMessage(_("✕ Synchronisation avec {l} impossible : {e}. Nouvel essai dans une minute.", l=lieu,
                                                   e=str(err)[:160]), 15000)
            else:
                recus, envoyes = r or (0, 0)
                repris = None
                if recus:
                    try:
                        from . import reglages
                        repris = reglages.reprendre_communs_drive(self.params)
                    except Exception:      # noqa: BLE001
                        repris = None
                self._maj_bouton_synchro(recus, envoyes)
                if recus or envoyes or not silencieux:
                    msg = _("✓ Synchronisation avec {l} : {r} reçu(s), {e} envoyé(s).", l=lieu, r=recus, e=envoyes)
                    if repris:
                        msg += " " + _("Réglages repris de « {p} ».", p=repris[0])
                    self.statusBar().showMessage(msg, 10000)
            if apres:
                apres()
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()
        return t

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
            n = reglages.synchro_secrets_auto(self.params)        # clefs et mots de passe (chiffrés) entre les postes
            if n:
                self.statusBar().showMessage(_("{n} mot(s) de passe ou clef(s) repris de vos autres postes.", n=n), 8000)
            compte = self._compte_synchro()
            if compte is not None:                                 # Drive en direct, NAS, FTP : les changements de ce poste partent
                from . import miroir
                self._synchroniser(compte, sens=set(miroir.ENVOIS), silencieux=True)
        except Exception as e:    # noqa: BLE001
            from .journal import ecrire
            ecrire("synchro", f"session non écrite : {e}")

    def verifier_session(self):
        try:
            from .session import session_de, date_fr, nb_fichiers
            s = session_de(self.params)
            self._secrets_au_demarrage()
            autres = s.autres_machines()
            donnees = s.lire()
            self.accueil.rafraichir(autres, [(m, dte, donnees.get(m, {}).get("fichiers", [])) for m, dte, _n in autres])
            d = s.discordance([ed.projet.chemin for ed in self.editeurs() if ed.projet.chemin])
            if d:
                machine, date, fichiers = d
                self.accueil.proposer(_("Sur « {m} » ({d}), {n} projet(s) étaient ouverts : {l}. Les rouvrir ici ?", m=machine, d=date_fr(date), n=len(fichiers),
                                        l=", ".join(f.get("nom", "") for f in fichiers[:4])), _("Reprendre"), lambda: self._reprendre(fichiers, machine))
        except Exception as e:    # noqa: BLE001
            from .journal import ecrire
            ecrire("synchro", f"session non lue : {e}")

    def _secrets_au_demarrage(self):
        """Clefs partagées par les autres postes : reprises tout de suite si la phrase est connue ici, sinon proposées."""
        from . import coffre, reglages
        if not self.params.get("synchro_secrets"):
            return
        chemin = reglages.chemin_secrets(self.params)
        if coffre.lire(reglages.PHRASE):
            n = reglages.synchro_secrets_auto(self.params)
            if n:
                self.statusBar().showMessage(_("{n} mot(s) de passe ou clef(s) repris de vos autres postes.", n=n), 8000)
        elif chemin and os.path.exists(chemin):
            from .dialogues_phrase import demander_phrase
            self.accueil.proposer(_("Vos autres postes partagent des mots de passe et clefs (IA, Pixabay, Pexels…). Donnez votre "
                                    "phrase secrète une fois pour les reprendre ici."), _("Donner la phrase…"),
                                  lambda: demander_phrase(self, self.params, nouvelle=False))

    def _reprendre(self, fichiers, machine=None):
        s = None
        for f in fichiers:
            p = f.get("chemin")
            if machine and not (p and os.path.exists(p)):
                try:                                   # même dossier par défaut, Drive, NAS, dossier déjà appris…
                    from .session import session_de
                    s = s or session_de(self.params)
                    p = s.retrouver_direct(machine, f)[0] or p
                except Exception:    # noqa: BLE001
                    pass
            if p and os.path.exists(p):
                self.ouvrir(p)
            else:
                self.statusBar().showMessage(_("Introuvable ici : {n}", n=f.get("nom", "")), 8000)


class DialogueRecuperation(QDialog):
    """PhilCut ne s'est pas fermé normalement : les projets non enregistrés, cochés, à récupérer (0.9.22)."""

    def __init__(self, fenetre, liste):
        super().__init__(fenetre)
        from PySide6.QtWidgets import QListWidgetItem, QPushButton
        from . import secours
        self.fenetre, self.liste_r = fenetre, liste
        self.setWindowTitle(_("Récupérer le travail"))
        self.resize(640, 360)
        v = QVBoxLayout(self)
        t = QLabel(_("PhilCut ne s'est pas fermé normalement la dernière fois (plantage, coupure de courant, redémarrage de Windows). "
                     "Ces projets ont des modifications qui n'étaient pas enregistrées ; la sauvegarde automatique les a gardées."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.liste = QListWidget()
        for r in liste:
            ou = r["origine"] or _("jamais enregistré")
            it = QListWidgetItem(_("« {n} » — {q}, {p} plan(s)\n{o}", n=r["nom"], q=secours.depuis(r["quand"]), p=r["plans"], o=ou))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            it.setData(Qt.UserRole, r)
            self.liste.addItem(it)
        v.addWidget(self.liste, 1)
        h = QHBoxLayout()
        b1 = QPushButton(_("Récupérer les projets cochés"))
        b1.setDefault(True)
        b1.clicked.connect(self.recuperer)
        b2 = QPushButton(_("Jeter les projets cochés"))
        b2.clicked.connect(self.jeter)
        b3 = QPushButton(_("Plus tard"))
        b3.setToolTip(_("Les copies sont gardées : la question reviendra au prochain démarrage."))
        b3.clicked.connect(self.reject)
        for b in (b1, b2, b3):
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        self.ouverts = []

    def _coches(self):
        return [self.liste.item(i).data(Qt.UserRole) for i in range(self.liste.count()) if self.liste.item(i).checkState() == Qt.Checked]

    def recuperer(self):
        from . import secours
        for r in self._coches():
            try:
                p = secours.recuperer(r["chemin"])
            except Exception as e:    # noqa: BLE001
                QMessageBox.warning(self, _("Récupérer"), _("Copie illisible : {e}", e=e))
                continue
            ed = self.fenetre.ajouter_onglet(p)
            self.fenetre._reconstruire_medias(ed)
            self.fenetre._maj_titre(ed)
            ed.encart.message(_("Projet récupéré ({q}). Enregistrez-le pour le garder.", q=secours.depuis(r["quand"])), 10000)
            self.ouverts.append(ed)
        self.accept()

    def jeter(self):
        from . import secours
        coches = self._coches()
        if coches and question_fr(self, _("Jeter"), _("Jeter les modifications non enregistrées de {n} projet(s) ?", n=len(coches)),
                                  QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        for r in coches:
            secours.jeter(r["cle"])
        self.accept()


class DialogueVersions(QDialog):
    """Fichier › Revenir à une sauvegarde automatique : les dernières copies du projet ; Annuler revient en arrière."""

    def __init__(self, fenetre, ed, versions):
        super().__init__(fenetre)
        from PySide6.QtWidgets import QListWidgetItem, QPushButton
        from . import secours
        self.ed = ed
        self.setWindowTitle(_("Sauvegardes automatiques"))
        self.resize(520, 320)
        v = QVBoxLayout(self)
        t = QLabel(_("Choisissez une version : le projet revient à cet état (Annuler, Ctrl+Z, ramène l'état actuel)."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.liste = QListWidget()
        for r in versions:
            it = QListWidgetItem(_("{q} — {p} plan(s) — version enregistrée sur {a}", q=secours.depuis(r["quand"]), p=r["plans"], a=r["poste"] or "?")
                                 if r.get("autre") else _("{q} — {p} plan(s)", q=secours.depuis(r["quand"]), p=r["plans"]))
            it.setData(Qt.UserRole, r)
            self.liste.addItem(it)
        self.liste.setCurrentRow(0)
        self.liste.itemDoubleClicked.connect(lambda _i: self.revenir())
        v.addWidget(self.liste, 1)
        h = QHBoxLayout()
        b = QPushButton(_("Revenir à cette version"))
        b.clicked.connect(self.revenir)
        h.addWidget(b)
        b2 = QPushButton(_("Fermer"))
        b2.clicked.connect(self.reject)
        h.addWidget(b2)
        h.addStretch(1)
        v.addLayout(h)

    def revenir(self):
        it = self.liste.currentItem()
        if not it:
            return
        import json
        with open(it.data(Qt.UserRole)["chemin"], encoding="utf-8") as f:
            d = json.load(f)
        d.pop("_secours", None)
        p = self.ed.projet
        p.marquer()
        for m in d.get("medias") or []:                       # proxys et vignettes de la version actuelle, s'ils existent
            ancien = p.media(m.get("id"))
            if ancien:
                for k in ("proxy", "vignettes", "onde"):
                    if ancien.get(k) and not m.get(k):
                        m[k] = ancien[k]
        d["secours_id"] = p.d.get("secours_id")
        p.d.clear()
        p.d.update(d)
        self.ed.biblio.remplir(p)
        self.ed.rafraichir()
        self.ed.encart.message(_("Projet revenu à la sauvegarde de {q} (Ctrl+Z pour annuler).", q=it.text().split(" — ")[0]), 8000)
        self.accept()
