"""« Mises à jour des IA » (0.9.85) : ce qui peut changer sur ce poste (moteurs, modèles de l'IA locale) et l'état des IA
cloud (adresse, prix, version conseillée). Rien ne s'installe sans un clic ; chaque mise à jour est essayée, l'ancienne
version revient si l'essai rate, et reste gardée pour un retour arrière."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QProgressBar, QPushButton, QTabWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import catalogue_ia as CI, maj_ia as MI, packs_ia as P
from .langue import _
from .taches import Tache, texte_erreur


def _texte_taille(o):
    return P.taille_texte(o) if o else "—"


class DialogueMajIA(QDialog):
    def __init__(self, parent, params):
        super().__init__(parent)
        self.params = params
        self.setWindowTitle(_("Mises à jour des IA"))
        self.resize(900, 600)
        self.tache = None
        self.taches = []
        self.majs = []
        v = QVBoxLayout(self)
        intro = QLabel(_("Rien ne change sans vous : cochez ce que vous voulez mettre à jour. Chaque mise à jour se télécharge en "
                         "fond, puis l'IA est essayée ; si l'essai rate, l'ancienne version revient toute seule. L'ancienne reste "
                         "gardée pour revenir en arrière tant que vous ne libérez pas la place. Les modèles du dossier commun "
                         "PhilFactory profitent aux autres logiciels."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.onglets = QTabWidget()
        v.addWidget(self.onglets, 1)

        # --- sur ce poste
        p = QWidget()
        pv = QVBoxLayout(p)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([_("IA"), _("Ce qui change"), _("Pourquoi"), _("Taille")])
        self._etirer(self.table, 1)
        pv.addWidget(self.table, 1)
        self.lbl_vide = QLabel(_("Tout est à jour sur ce poste."))
        self.lbl_vide.setWordWrap(True)
        pv.addWidget(self.lbl_vide)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        pv.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        pv.addWidget(self.etat)
        h = QHBoxLayout()
        self.b_maj = QPushButton(_("Mettre à jour la sélection"))
        self.b_maj.setProperty("primaire", True)
        self.b_maj.clicked.connect(self.mettre_a_jour)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.clicked.connect(self.arreter)
        self.b_arreter.hide()
        self.b_reduire = QPushButton(_("Réduire"))
        self.b_reduire.setToolTip(_("Range la fenêtre : la mise à jour continue, suivie dans la barre du bas"))
        self.b_reduire.clicked.connect(self.hide)
        self.b_reduire.hide()
        h.addWidget(self.b_maj)
        h.addWidget(self.b_arreter)
        h.addWidget(self.b_reduire)
        h.addStretch(1)
        pv.addLayout(h)
        t = QLabel(_("<b>Anciennes versions gardées</b> (pour revenir en arrière)"))
        pv.addWidget(t)
        self.table_gardes = QTableWidget(0, 3)
        self.table_gardes.setHorizontalHeaderLabels([_("IA"), _("Place"), ""])
        self._etirer(self.table_gardes, 0)
        self.table_gardes.setMaximumHeight(130)
        pv.addWidget(self.table_gardes)
        h = QHBoxLayout()
        self.b_liberer = QPushButton(_("Libérer la place"))
        self.b_liberer.clicked.connect(self.liberer)
        h.addWidget(self.b_liberer)
        h.addStretch(1)
        pv.addLayout(h)
        self.onglets.addTab(p, _("Sur ce poste"))

        # --- dans le cloud
        c = QWidget()
        cv = QVBoxLayout(c)
        lc = QLabel(_("Les IA cloud se mettent à jour chez leur fournisseur. PhilCut relit chaque jour leur adresse et leur prix "
                      "indicatif ; un service retiré est remplacé par celui indiqué, et PhilCut vous le dit. Le prix est "
                      "toujours affiché et demandé avant de payer."))
        lc.setWordWrap(True)
        cv.addWidget(lc)
        self.table_cloud = QTableWidget(0, 4)
        self.table_cloud.setHorizontalHeaderLabels([_("IA"), _("Pour"), _("Prix indicatif"), _("État")])
        self._etirer(self.table_cloud, 0)
        cv.addWidget(self.table_cloud, 1)
        self.onglets.addTab(c, _("Dans le cloud"))

        h = QHBoxLayout()
        self.b_verifier = QPushButton(_("Vérifier maintenant"))
        self.b_verifier.setToolTip(_("Relit les catalogues en ligne (moteurs, modèles, services cloud)"))
        self.b_verifier.clicked.connect(self.verifier)
        self.lbl_verif = QLabel(_("Dernière vérification : {d}", d=params.get("ia_maj_derniere") or _("jamais")))
        b_fermer = QPushButton(_("Fermer"))
        b_fermer.clicked.connect(self.close)
        h.addWidget(self.b_verifier)
        h.addWidget(self.lbl_verif, 1)
        h.addWidget(b_fermer)
        v.addLayout(h)
        self.remplir()

    @staticmethod
    def _etirer(table, colonne):
        table.verticalHeader().hide()
        table.setWordWrap(True)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        hh = table.horizontalHeader()
        for i in range(table.columnCount()):
            hh.setSectionResizeMode(i, QHeaderView.Stretch if i == colonne else QHeaderView.ResizeToContents)

    # ------------------------------------------------------------ remplissage
    def remplir(self, majs=None):
        self.majs = MI.a_mettre_a_jour() if majs is None else majs
        self.table.setRowCount(len(self.majs))
        for i, m in enumerate(self.majs):
            it = QTableWidgetItem(m["nom"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            self.table.setItem(i, 0, it)
            change = (_("remplacé par « {n} »", n=m["apres"]) if m["type"] == "remplacement"
                      else _("{a} → {b}", a=m["avant"], b=m["apres"]))
            self.table.setItem(i, 1, QTableWidgetItem(change))
            self.table.setItem(i, 2, QTableWidgetItem(m["raison"]))
            self.table.setItem(i, 3, QTableWidgetItem(_texte_taille(m.get("taille"))))
        self.table.resizeRowsToContents()
        self.lbl_vide.setVisible(not self.majs)
        self.table.setVisible(bool(self.majs))
        self.b_maj.setEnabled(bool(self.majs) and not self._en_calcul())
        self.params["ia_maj_nombre"] = len(self.majs)
        f = self.parent()
        if f is not None and hasattr(f, "_signaler_maj_ia"):
            f._signaler_maj_ia(len(self.majs))
        self._remplir_gardes()
        self._remplir_cloud()

    def _remplir_gardes(self):
        gardes = MI.gardes()
        self.table_gardes.setRowCount(len(gardes))
        for i, (cle, genre_maj, nom, octets) in enumerate(gardes):
            self.table_gardes.setItem(i, 0, QTableWidgetItem(nom))
            self.table_gardes.setItem(i, 1, QTableWidgetItem(_texte_taille(octets)))
            b = QPushButton(_("Revenir"))
            b.setToolTip(_("Remet la version d'avant la mise à jour"))
            b.clicked.connect(lambda _c=False, k=cle, g=genre_maj, n=nom: self.revenir(k, g, n))
            self.table_gardes.setCellWidget(i, 2, b)
        total = sum(g[3] for g in gardes)
        self.b_liberer.setEnabled(bool(gardes))
        self.b_liberer.setText(_("Libérer la place ({t})", t=_texte_taille(total)) if gardes else _("Libérer la place"))

    def _remplir_cloud(self):
        lignes = [(s.get("nom") or s["role"], s.get("usage", ""), CI.prix_texte(s), s.get("etat", "conseille"), s.get("message", ""))
                  for s in CI.liste()]
        try:
            from . import generateurs_video as GV
            for m in GV.modeles(self.params):
                if m.get("prix_s") is not None and not str(m.get("id", "")).startswith("perso:"):
                    lignes.append((m.get("nom", m["id"]), _("Vidéo IA"), _("{p} $/s", p=CI.nombre(m["prix_s"])), m.get("etat", "conseille"),
                                   m.get("note", "")))
        except Exception:      # noqa: BLE001 : le tableau reste utile sans eux
            pass
        import unicodedata
        net = lambda t: unicodedata.normalize("NFKD", str(t).lower()).encode("ascii", "ignore").decode()
        lignes.sort(key=lambda l: net(l[0]))
        self.table_cloud.setRowCount(len(lignes))
        for i, (nom, usage, prix, etat, note) in enumerate(lignes):
            self.table_cloud.setItem(i, 0, QTableWidgetItem(nom))
            self.table_cloud.setItem(i, 1, QTableWidgetItem(usage))
            self.table_cloud.setItem(i, 2, QTableWidgetItem(prix))
            it = QTableWidgetItem(CI.etat_texte(etat))
            if note:
                it.setToolTip(note)
            self.table_cloud.setItem(i, 3, it)

    # ------------------------------------------------------------ actions
    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def choisies(self):
        return [m for i, m in enumerate(self.majs) if self.table.item(i, 0) and self.table.item(i, 0).checkState() == Qt.Checked]

    def mettre_a_jour(self):
        majs = self.choisies()
        if not majs or self._en_calcul():
            return
        params = self.params

        def travail(t):
            comptes = []
            for n, m in enumerate(majs):
                if t.arret:
                    break
                a, b = n / len(majs), (n + 1) / len(majs)
                try:
                    comptes.append((True, MI.appliquer(m, params, lambda f, x="", a=a, b=b: t.avancer(a + (b - a) * f, x),
                                                       lambda: t.arret)))
                except InterruptedError:
                    raise
                except Exception as e:      # noqa: BLE001 : une IA ratée n'empêche pas les autres
                    comptes.append((False, texte_erreur(e)))
            return comptes
        self.tache = Tache(travail, _("Mises à jour des IA"))
        self.taches.append(self.tache)
        self.tache.lier(self)
        from .widgets import suivre_en_fond
        suivre_en_fond(self, self.tache, _("Mises à jour des IA ({n})", n=len(majs)))
        self.tache.progression.connect(lambda f, txt: (self.barre.setValue(int(f * 1000)), txt and self.etat.setText(txt)),
                                       Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self.barre.setValue(0)
        for w in (self.barre, self.b_arreter, self.b_reduire):
            w.show()
        self.b_maj.setEnabled(False)
        self.tache.start()

    def _fini(self, comptes, err):
        for w in (self.barre, self.b_arreter, self.b_reduire):
            w.hide()
        if err is not None:
            self.etat.setText(_("Arrêté : {e}", e=texte_erreur(err)) if not isinstance(err, InterruptedError) else _("Arrêté."))
        else:
            self.etat.setText("<br>".join(("✓ " if ok else "✗ ") + t for ok, t in (comptes or [])))
        try:
            self.params.enregistrer()
        except Exception:      # noqa: BLE001
            pass
        self.remplir()

    def arreter(self):
        if self._en_calcul():
            self.tache.stopper()

    def revenir(self, cle, genre_maj, nom):
        if self._en_calcul():
            return
        if QMessageBox.question(self, _("Revenir en arrière"), _("Remettre la version d'avant pour « {n} » ?", n=nom)) != QMessageBox.Yes:
            return
        ok = MI.revenir(cle, genre_maj)
        self.etat.setText(_("✓ « {n} » : version d'avant remise.", n=nom) if ok else _("Rien à remettre pour « {n} ».", n=nom))
        self.remplir()

    def liberer(self):
        if self._en_calcul():
            return
        o = MI.liberer()
        self.etat.setText(_("✓ {t} libérés. Le retour arrière n'est plus possible pour ces IA.", t=_texte_taille(o)))
        self.remplir()

    def verifier(self):
        if self._en_calcul():
            return
        params = self.params

        def travail(t):
            t.avancer(0.1, _("Lecture des catalogues en ligne…"))
            P.manifeste(rafraichir=True)
            from . import catalogue_ligne
            catalogue_ligne.telecharger(CI.FICHIER)
            CI.recharger()
            return MI.a_mettre_a_jour()
        self.tache = Tache(travail, _("Vérification des IA"))
        self.taches.append(self.tache)
        self.tache.lier(self)
        self.b_verifier.setEnabled(False)
        self.etat.setText(_("Lecture des catalogues en ligne…"))
        self.tache.fini.connect(lambda r, e: self._verifie(r, e, params), Qt.QueuedConnection)
        self.tache.start()

    def _verifie(self, majs, err, params):
        import datetime
        self.b_verifier.setEnabled(True)
        if err is not None:
            self.etat.setText(_("Vérification impossible : {e}", e=texte_erreur(err)))
            return
        params["ia_maj_derniere"] = datetime.date.today().isoformat()
        self.lbl_verif.setText(_("Dernière vérification : {d}", d=params["ia_maj_derniere"]))
        self.etat.setText(_("{n} mise(s) à jour proposée(s).", n=len(majs)) if majs else _("Tout est à jour sur ce poste."))
        self.remplir(majs)

    def closeEvent(self, ev):
        from .widgets import garder_calcul
        if garder_calcul(self, self._en_calcul()):
            ev.ignore()
            return
        super().closeEvent(ev)
