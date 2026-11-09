"""Fenêtres des projets entre appareils (0.9.35) : médias introuvables, préparer pour les autres appareils (copies
légères, créations IA déposées), analyse de l'espace PhilCut sur le Drive."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from . import drive_philcut as DP
from . import liens
from .langue import _
from .taches import Tache
from .widgets import SuiviAttente


# ------------------------------------------------------------------ médias introuvables
class DialogueManquants(QDialog):
    """Les médias que ce poste ne trouve pas : ils restent dans le projet, intacts, jusqu'à ce qu'on les rattache."""

    def __init__(self, ed, media=None):
        super().__init__(ed)
        self.ed, self.params = ed, ed.params
        self.taches = []
        self.media_choisi = media
        self.setWindowTitle(_("Médias introuvables sur ce poste"))
        self.resize(900, 520)
        v = QVBoxLayout(self)
        t = QLabel(_("Ces fichiers ne sont pas à l'endroit noté sur vos autres appareils. Ils restent dans le projet, à leur place, "
                     "grisés : rien n'est supprimé ni remplacé. Indiquez où ils sont (« Où est ce fichier ? ») : les autres fichiers "
                     "du même dossier sont alors retrouvés tout seuls, et ce dossier est retenu pour la suite."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderLabels([_("Média"), _("Où il était"), _("État")])
        self.arbre.setRootIsDecorated(False)
        self.arbre.setWordWrap(True)
        self.arbre.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.arbre.itemDoubleClicked.connect(lambda it, _c: self.ou())
        v.addWidget(self.arbre, 1)
        self.suivi = SuiviAttente()
        v.addWidget(self.suivi)
        h = QHBoxLayout()
        b = QPushButton(_("Où est ce fichier ?…"))
        b.setToolTip(_("Choisir le fichier sur ce poste ; PhilCut vérifie que c'est bien le même (empreinte)"))
        b.clicked.connect(self.ou)
        h.addWidget(b)
        b = QPushButton(_("Chercher sur ce poste"))
        b.setToolTip(_("Parcourt vos dossiers habituels (Vidéos, Images, Téléchargements, Drive…) par nom, taille et empreinte"))
        b.clicked.connect(self.chercher)
        h.addWidget(b)
        h.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.accept)
        h.addWidget(b)
        v.addLayout(h)
        self.remplir()

    def _manquants(self):
        return [m for m in self.ed.projet.medias if not os.path.exists(m.get("chemin") or "") or m.get("copie_legere")]

    def remplir(self):
        self.arbre.clear()
        for m in self._manquants():
            emp = m.get("emplacements") or {}
            ou = "\n".join(f"{k} : {e.get('chemin', '')}" for k, e in emp.items()) or (m.get("original") or m.get("chemin") or "")
            etat = _("copie légère du Drive en attendant l'original") if m.get("copie_legere") else _("introuvable")
            it = QTreeWidgetItem([m.get("nom", ""), ou, etat])
            it.setData(0, Qt.UserRole, m["id"])
            it.setToolTip(1, ou)
            self.arbre.addTopLevelItem(it)
            if m["id"] == self.media_choisi:
                self.arbre.setCurrentItem(it)
        self.arbre.resizeColumnToContents(0)
        if not self.arbre.topLevelItemCount():
            it = QTreeWidgetItem([_("Tous les médias sont retrouvés."), "", "✓"])
            self.arbre.addTopLevelItem(it)

    def _courant(self):
        it = self.arbre.currentItem() or self.arbre.topLevelItem(0)
        mid = it.data(0, Qt.UserRole) if it else None
        return self.ed.projet.media(mid) if mid else None

    def ou(self):
        m = self._courant()
        if not m:
            return
        from .session import dossier_systeme
        depart = self.params.get("dernier_dossier_rattacher") or dossier_systeme("videos" if m.get("genre") == "video" else "images")
        ch, _f = QFileDialog.getOpenFileName(self, _("Où est « {n} » ?", n=m.get("nom", "")), os.path.join(depart, m.get("nom", "")))
        if not ch:
            return
        self.params["dernier_dossier_rattacher"] = os.path.dirname(ch)
        ok, msg = liens.rattacher(self.ed.projet, m, ch, self.params)
        if not ok:
            if QMessageBox.question(self, _("Rattacher"), msg) != QMessageBox.Yes:
                return
            ok, msg = liens.rattacher(self.ed.projet, m, ch, self.params, verifier=False)
        self._apres(msg)

    def chercher(self):
        p = self.ed.projet
        t = Tache(lambda tache: p.retrouver_medias(chercher_disque=True, arret=lambda: tache.arret), _("Recherche"))
        self.taches.append(t)
        self.suivi.demarrer(_("Recherche des médias dans vos dossiers"), t, _("Au plus 20 secondes ; le disque n'est parcouru qu'une fois."))

        def fin(r, e):
            self.suivi.finir()
            if e:
                self._apres(_("✕ {e}", e=str(e)[:200]))
                return
            self._apres(_("{n} média(s) retrouvé(s), {c} sur copie légère, {m} encore introuvable(s).", n=len(r["trouves"]),
                          c=len(r["copies"]), m=len(r["manquants"])))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def _apres(self, msg):
        self.ed.projet.modifie = True
        self.ed.biblio.remplir(self.ed.projet)
        self.ed.rafraichir()
        self.ed.encart.message(msg, 7000)
        self.remplir()

    def done(self, r):
        for t in self.taches:
            if t.isRunning():
                t.stopper()
        super().done(r)


# ------------------------------------------------------------------ préparer pour vos autres appareils
class DialoguePreparer(QDialog):
    """Après l'enregistrement : proposer la copie légère des vidéos et le dépôt des créations IA sur le Drive."""

    def __init__(self, ed, videos, creations):
        super().__init__(ed)
        self.ed, self.params = ed, ed.params
        self.videos, self.creations = videos, creations
        self.setWindowTitle(_("Retrouver ce projet sur vos autres appareils"))
        v = QVBoxLayout(self)
        t = QLabel(_("Le projet est enregistré. Il contient des liens vers vos fichiers : sur un autre appareil, PhilCut les cherche "
                     "tout seul. Pour monter ailleurs même sans l'original (téléphone, autre PC), il peut aussi déposer sur le Drive :"))
        t.setWordWrap(True)
        v.addWidget(t)
        self.c_videos = QCheckBox(_("Une copie légère 720p de {n} vidéo(s) — environ {t}", n=len(videos), t=DP.taille_lisible(DP.estimer(videos))))
        self.c_videos.setChecked(bool(videos))
        self.c_videos.setVisible(bool(videos))
        v.addWidget(self.c_videos)
        taille = sum(os.path.getsize(m["chemin"]) for m in creations if os.path.exists(m["chemin"]))
        self.c_creations = QCheckBox(_("Les {n} création(s) IA du projet — {t} (reprises ailleurs sans être refaites ni payées deux fois)",
                                       n=len(creations), t=DP.taille_lisible(taille)))
        self.c_creations.setChecked(bool(creations))
        self.c_creations.setVisible(bool(creations))
        v.addWidget(self.c_creations)
        self.c_plus = QCheckBox(_("Ne plus me le demander pour ce projet"))
        v.addWidget(self.c_plus)
        note = QLabel(_("<span style='color:#999'>Ces fichiers prennent de la place sur votre Drive ; « Espace PhilCut sur le Drive » "
                        "(menu Fichier) propose de supprimer ce qui ne sert plus. Réglages : Préférences › Comptes et synchro.</span>"))
        note.setWordWrap(True)
        v.addWidget(note)
        h = QHBoxLayout()
        h.addStretch(1)
        b = QPushButton(_("Déposer"))
        b.setDefault(True)
        b.clicked.connect(self.accept)
        h.addWidget(b)
        b = QPushButton(_("Pas maintenant"))
        b.clicked.connect(self.reject)
        h.addWidget(b)
        v.addLayout(h)


def proposer_apres_enregistrement(ed):
    """Appelé après chaque enregistrement réussi : rien si aucun lieu de synchronisation, ou si l'utilisateur a refusé."""
    params, p = ed.params, ed.projet
    if not DP.disponible(params) or p.d.get("appareils_preparer") == "non":
        return
    try:
        DP.noter_utilisation(params, p)
    except OSError:
        pass
    videos = DP.a_copier(p) if params.get("proposer_copie_legere", True) else []
    mode = params.get("creations_drive", "demander")
    creations = [m for m in p.medias if os.path.exists((m.get("chemin") or "") + ".ia.json") and not m.get("copie_drive")]
    if mode == "toujours":
        for m in creations:
            try:
                DP.deposer_creation(params, m["chemin"], m)
            except OSError:
                pass
        creations = []
    elif mode == "jamais":
        creations = []
    if not videos and not creations:
        return
    d = DialoguePreparer(ed, videos, creations)
    ok = d.exec() == QDialog.Accepted
    if d.c_plus.isChecked():
        p.d["appareils_preparer"] = "non"
        p.modifie = True
    if not ok:
        return
    a_copier = videos if d.c_videos.isChecked() else []
    a_deposer = creations if d.c_creations.isChecked() else []

    def travail(tache):
        n = len(a_copier) + len(a_deposer)
        for k, m in enumerate(a_deposer):
            tache.avancer(k / n, _("création {k} sur {n}", k=k + 1, n=len(a_deposer)))
            DP.deposer_creation(params, m["chemin"], m)
        for k, m in enumerate(a_copier):
            if tache.arret:
                break
            base = len(a_deposer) + k
            tache.avancer(base / n, _("copie légère de {nom}", nom=m.get("nom", "")))
            DP.copier_leger(params, m, progression=lambda f, base=base: tache.avancer((base + f) / n), arret=lambda: tache.arret)
        return True
    t = Tache(travail, _("Drive"))
    ed._taches_drive = getattr(ed, "_taches_drive", []) + [t]
    ed.encart.suivre(t, _("Dépôt sur le Drive pour vos autres appareils"))

    def fin(r, e):
        if not e:
            p.modifie = True                       # les noms des copies vont dans le projet au prochain enregistrement
    t.fini.connect(fin, Qt.QueuedConnection)
    t.start()


# ------------------------------------------------------------------ espace PhilCut sur le Drive
class DialogueEspaceDrive(QDialog):
    def __init__(self, fenetre, params, utilises=frozenset()):
        super().__init__(fenetre)
        self.params, self.utilises = params, utilises
        self.taches = []
        self.setWindowTitle(_("Espace PhilCut sur le Drive"))
        self.resize(940, 620)
        v = QVBoxLayout(self)
        self.intro = QLabel("")
        self.intro.setWordWrap(True)
        v.addWidget(self.intro)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderLabels([_("Fichier"), _("Taille"), _("Pourquoi")])
        self.arbre.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.arbre.setWordWrap(True)
        self.arbre.itemChanged.connect(self._total)
        v.addWidget(self.arbre, 1)
        self.total = QLabel("")
        v.addWidget(self.total)
        self.suivi = SuiviAttente()
        v.addWidget(self.suivi)
        h = QHBoxLayout()
        b = QPushButton(_("Ouvrir le dossier"))
        b.clicked.connect(self._ouvrir)
        h.addWidget(b)
        b = QPushButton(_("Tout décocher"))
        b.clicked.connect(lambda: self._cocher(False))
        h.addWidget(b)
        h.addStretch(1)
        self.b_suppr = QPushButton(_("Supprimer la sélection"))
        self.b_suppr.clicked.connect(self.supprimer)
        h.addWidget(self.b_suppr)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.reject)
        h.addWidget(b)
        v.addLayout(h)
        self.remplir()

    def remplir(self):
        self.arbre.blockSignals(True)
        self.arbre.clear()
        if not DP.disponible(self.params):
            self.intro.setText(_("Aucun lieu de synchronisation n'est choisi : Préférences › Comptes et synchro."))
            self.b_suppr.setEnabled(False)
            self.arbre.blockSignals(False)
            return
        elements = DP.analyser(self.params, self.utilises)
        jours = int(self.params.get("drive_purge_jours", DP.JOURS_DEFAUT) or DP.JOURS_DEFAUT)
        tot = sum(e["taille"] for e in elements)
        self.intro.setText(_("Le dossier PhilCut de votre lieu de synchronisation occupe {t} ({n} fichiers). Les cases cochées sont "
                             "proposées à la suppression : copies et créations qui n'ont pas servi depuis {j} jours ou qui ne sont plus "
                             "utilisées par aucun projet, restes de transferts. Vérifiez, décochez ce que vous voulez garder : rien n'est "
                             "supprimé sans votre clic. Sur les Drives, les fichiers vont à la corbeille.",
                             t=DP.taille_lisible(tot), n=len(elements), j=jours))
        par_cat = {}
        for e in elements:
            par_cat.setdefault(e["categorie"], []).append(e)
        for cat, lib in DP.CATEGORIES.items():
            es = par_cat.get(cat) or []
            if not es:
                continue
            racine = QTreeWidgetItem([f"{lib} ({len(es)})", DP.taille_lisible(sum(e["taille"] for e in es)), ""])
            racine.setFirstColumnSpanned(False)
            self.arbre.addTopLevelItem(racine)
            for e in es:
                it = QTreeWidgetItem([e["rel"], DP.taille_lisible(e["taille"]), e["raison"]])
                it.setData(0, Qt.UserRole, e["rel"])
                it.setData(1, Qt.UserRole, e["taille"])
                if cat != "reglages":
                    it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                    it.setCheckState(0, Qt.Checked if e["proposer"] else Qt.Unchecked)
                else:
                    it.setDisabled(True)
                racine.addChild(it)
            racine.setExpanded(cat != "reglages")
        self.arbre.resizeColumnToContents(0)
        self.arbre.blockSignals(False)
        self._total()

    def _coches(self):
        out = []
        for i in range(self.arbre.topLevelItemCount()):
            r = self.arbre.topLevelItem(i)
            for j in range(r.childCount()):
                it = r.child(j)
                if it.flags() & Qt.ItemIsUserCheckable and it.checkState(0) == Qt.Checked:
                    out.append((it.data(0, Qt.UserRole), int(it.data(1, Qt.UserRole) or 0)))
        return out

    def _cocher(self, oui):
        self.arbre.blockSignals(True)
        for i in range(self.arbre.topLevelItemCount()):
            r = self.arbre.topLevelItem(i)
            for j in range(r.childCount()):
                it = r.child(j)
                if it.flags() & Qt.ItemIsUserCheckable:
                    it.setCheckState(0, Qt.Checked if oui else Qt.Unchecked)
        self.arbre.blockSignals(False)
        self._total()

    def _total(self, *_a):
        c = self._coches()
        self.total.setText(_("Sélection : {n} fichier(s), {t} libérés.", n=len(c), t=DP.taille_lisible(sum(t for _r, t in c))))
        self.b_suppr.setEnabled(bool(c))

    def _ouvrir(self):
        r = DP.racine(self.params)
        f = getattr(self.parent(), "_ouvrir_dans_systeme", None)
        if r and f:
            f(r)

    def supprimer(self):
        c = self._coches()
        if not c or QMessageBox.question(self, _("Supprimer"), _("Supprimer {n} fichier(s) ({t}) ici et sur le Drive ?", n=len(c),
                                                                  t=DP.taille_lisible(sum(t for _r, t in c)))) != QMessageBox.Yes:
            return
        rels = [r for r, _t in c]
        t = Tache(lambda tache: DP.supprimer(self.params, rels, progression=lambda f: tache.avancer(f)), _("Nettoyage"))
        self.taches.append(t)
        self.suivi.demarrer(_("Suppression de {n} fichier(s)", n=len(rels)), t)

        def fin(r, e):
            self.suivi.finir()
            if e:
                QMessageBox.warning(self, _("Supprimer"), str(e))
            else:
                n, octets, erreurs = r
                msg = _("{n} fichier(s) supprimé(s), {t} libérés.", n=n, t=DP.taille_lisible(octets))
                if erreurs:
                    msg += "\n\n" + _("Non supprimés :") + "\n" + "\n".join(f"{a} : {b[:120]}" for a, b in erreurs[:8])
                QMessageBox.information(self, _("Supprimer"), msg)
            self.remplir()
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    def done(self, r):
        for t in self.taches:
            if t.isRunning():
                t.stopper()
        super().done(r)
