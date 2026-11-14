"""Fenêtre « Clip de groupe d'après la chanson » (0.9.66), non bloquante. 1. PhilCut écoute le morceau ; 2. lieu, rendu et
musiciens inventés ; 3. plans calés sur les mesures, modifiables (idées par l'IA sur clic) ; 4. fabrication par le cloud,
prix total demandé avant ; 5. aperçu de chaque plan, puis pose sous la chanson (un seul Annuler)."""
import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QScrollArea, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from . import clip_groupe as CG
from .langue import _
from .taches import Tache, texte_erreur

COULEURS = {"intro": "#4b5d7a", "couplet": "#3f7f6a", "montee": "#b08a2e", "refrain": "#b5473a", "solo": "#7a4fa0", "fin": "#4b5d7a"}


def _tc(t):
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{int(t % 60):02d}"


class BandeParties(QWidget):
    """Les parties du morceau en couleurs, à l'échelle du temps."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.secs, self.duree = [], 1.0
        self.setMinimumHeight(30)
        self.setMaximumHeight(30)

    def poser(self, secs, duree):
        self.secs, self.duree = secs or [], max(0.1, duree)
        self.setToolTip("\n".join(f"{_tc(s['debut'])}–{_tc(s['fin'])} : {CG.PARTIES.get(s['type'], s['type'])}" for s in self.secs))
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        w, h = self.width(), self.height()
        for s in self.secs:
            x0, x1 = s["debut"] / self.duree * w, s["fin"] / self.duree * w
            r = QRectF(x0, 0, max(1.0, x1 - x0 - 1), h)
            c = QColor(COULEURS.get(s["type"], "#555"))
            c.setAlphaF(0.45 + 0.55 * float(s.get("energie") or 0))
            p.fillRect(r, c)
            if x1 - x0 > 46:
                p.setPen(QColor("white"))
                p.drawText(r.adjusted(3, 0, -2, 0), Qt.AlignVCenter | Qt.AlignLeft, CG.PARTIES.get(s["type"], s["type"]))
        p.end()


class DialogueClipGroupe(QDialog):
    def __init__(self, ed, clip_son=None, chemin=None, prefs=None):
        super().__init__(ed)
        from . import creations
        self.ed, self.params, self.clip_son = ed, ed.params, clip_son
        self.setModal(False)
        self.setWindowTitle(_("Clip de groupe d'après la chanson"))
        self.resize(900, 720)
        self.tache, self.clip = None, None
        prefs = dict(prefs or {})
        m = ed.projet.media(clip_son["media"]) if clip_son else None
        self.chemin = (m or {}).get("chemin") or chemin
        rec = creations.lire(self.chemin or "") or {}
        self.fiche = rec.get("fiche") if rec.get("famille") == "musique" else None
        if self.fiche and self.fiche.get("clip"):
            prefs = dict(self.fiche["clip"], **prefs)
        racine = QVBoxLayout(self)
        zone = QScrollArea()
        zone.setWidgetResizable(True)
        zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zone.setFrameShape(QFrame.NoFrame)
        racine.addWidget(zone, 1)
        corps = QWidget()
        zone.setWidget(corps)
        v = QVBoxLayout(corps)
        intro = QLabel(_("PhilCut écoute <b>{f}</b>, en déduit les parties (intro, couplets, refrains…), un groupe inventé et un "
                         "découpage plan par plan calé sur les mesures. Vous corrigez tout ; rien n'est payé avant « Fabriquer ».",
                         f=os.path.basename(self.chemin or "")))
        intro.setWordWrap(True)
        v.addWidget(intro)
        # 1. écoute
        g1 = QGroupBox(_("1. Le morceau"))
        l1 = QVBoxLayout(g1)
        h = QHBoxLayout()
        self.separer = QCheckBox(_("Séparer la voix (savoir quand on chante, lèvres du chanteur)"))
        from . import separation as S
        sep = S.manquant(self.params) is None
        self.separer.setChecked(sep)
        self.separer.setEnabled(sep)
        if not sep:
            self.separer.setToolTip(_("Installez « Séparer voix, musique et bruits » (Préférences › IA locale)"))
        h.addWidget(self.separer, 1)
        self.b_ecouter = QPushButton(_("Ecouter le morceau"))
        self.b_ecouter.clicked.connect(self.ecouter)
        h.addWidget(self.b_ecouter)
        l1.addLayout(h)
        self.bande = BandeParties()
        l1.addWidget(self.bande)
        self.resume = QLabel(_("Pas encore écouté."))
        self.resume.setWordWrap(True)
        self.resume.setStyleSheet("color:#9aa4b2")
        l1.addWidget(self.resume)
        v.addWidget(g1)
        # 2. scène et groupe
        g2 = QGroupBox(_("2. La scène et le groupe (musiciens inventés)"))
        l2 = QVBoxLayout(g2)
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Lieu")))
        self.lieu = QComboBox()
        for k in ("concert", "ailleurs"):
            self.lieu.addItem(CG.LIEUX[k], k)
        self.lieu.setCurrentIndex(max(0, self.lieu.findData(prefs.get("lieu", "concert"))))
        h.addWidget(self.lieu)
        self.lieu_texte = QLineEdit()
        self.lieu_texte.setPlaceholderText(_("où : une plage au coucher du soleil, un toit en ville la nuit…"))
        h.addWidget(self.lieu_texte, 1)
        self.anime = QCheckBox(_("Dessin animé"))
        self.anime.setChecked(bool(prefs.get("anime")))
        h.addWidget(self.anime)
        self.format = QComboBox()
        self.format.addItem(_("Paysage 16:9"), "16:9")
        self.format.addItem(_("Vertical 9:16"), "9:16")
        h.addWidget(self.format)
        l2.addLayout(h)
        self.table_groupe = QTableWidget(0, 3)
        self.table_groupe.setHorizontalHeaderLabels([_("Rôle"), _("Nom"), _("A quoi il ressemble (modifiable)")])
        self.table_groupe.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_groupe.verticalHeader().hide()
        self.table_groupe.setMaximumHeight(150)
        l2.addWidget(self.table_groupe)
        h = QHBoxLayout()
        b = QPushButton(_("Ajouter un musicien"))
        b.clicked.connect(self._ajouter_membre)
        h.addWidget(b)
        b = QPushButton(_("Retirer"))
        b.clicked.connect(self._retirer_membre)
        h.addWidget(b)
        h.addStretch(1)
        l2.addLayout(h)
        v.addWidget(g2)
        # 3. plans
        g3 = QGroupBox(_("3. Les plans, calés sur les mesures"))
        l3 = QVBoxLayout(g3)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([_("De"), _("Partie"), _("Plan (modifiable)"), _("Chant"), _("Etat")])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setWordWrap(True)                      # jamais de texte coupé : la ligne s'agrandit
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.horizontalHeader().sectionResized.connect(lambda *_a: self.table.resizeRowsToContents())
        self.table.setMinimumHeight(200)
        self.table.currentCellChanged.connect(lambda r, *_a: self._voir_plan(r))
        l3.addWidget(self.table)
        self.reutiliser = QCheckBox(_("Un refrain qui revient reprend les plans du premier (bien moins cher)"))
        self.reutiliser.setChecked(True)
        self.reutiliser.toggled.connect(self.redecouper)
        l3.addWidget(self.reutiliser)
        h = QHBoxLayout()
        b = QPushButton(_("Refaire le découpage"))
        b.clicked.connect(self.redecouper)
        h.addWidget(b)
        self.b_idees = QPushButton(_("Idées avec l'IA (ambiance, paroles)"))
        self.b_idees.clicked.connect(self.idees)
        h.addWidget(self.b_idees)
        self.niveau = self._choix_niveau()
        h.addWidget(self.niveau)
        h.addStretch(1)
        l3.addLayout(h)
        v.addWidget(g3)
        # 4. fabrication
        g4 = QGroupBox(_("4. Fabrication par le cloud"))
        l4 = QVBoxLayout(g4)
        h = QHBoxLayout()
        h.addWidget(QLabel(_("Moteur vidéo")))
        self.moteur = QComboBox()
        from . import generateurs_video as GV
        for mo in sorted(GV.disponibles(self.params), key=lambda x: CG._net(x["nom"])):
            self.moteur.addItem(mo["nom"], mo["id"])
        self.moteur.currentIndexChanged.connect(self._maj)
        h.addWidget(self.moteur, 1)
        l4.addLayout(h)
        self.images = QCheckBox(_("Mêmes visages dans tous les plans : portraits et images de départ par Gemini (conseillé)"))
        self.images.setChecked(bool(self.params.get("clef_gemini")))
        self.images.setEnabled(bool(self.params.get("clef_gemini")))
        self.images.toggled.connect(self._maj)
        l4.addWidget(self.images)
        self.accord = QCheckBox(_("Musiciens inventés : aucun vrai groupe, aucune personnalité"))
        self.accord.toggled.connect(self._maj)
        l4.addWidget(self.accord)
        self.cout = QLabel("")
        self.cout.setWordWrap(True)
        self.cout.setStyleSheet("font-weight:600")
        l4.addWidget(self.cout)
        v.addWidget(g4)
        from .dialogues_creatif import ApercuCreation
        self.apercu = ApercuCreation(self)
        self.apercu.hide()
        v.addWidget(self.apercu)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        racine.addWidget(self.barre)
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        racine.addWidget(self.etat)
        hb = QHBoxLayout()
        self.b_fabriquer = QPushButton(_("Fabriquer les plans"))
        self.b_fabriquer.setStyleSheet("font-weight:600")
        self.b_fabriquer.clicked.connect(self.fabriquer)
        hb.addWidget(self.b_fabriquer)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.clicked.connect(lambda: self.tache and self.tache.stopper())
        self.b_arreter.hide()
        hb.addWidget(self.b_arreter)
        self.b_poser = QPushButton(_("Poser le clip sous la chanson"))
        self.b_poser.clicked.connect(self.poser)
        hb.addWidget(self.b_poser)
        hb.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.close)
        hb.addWidget(b)
        racine.addLayout(hb)
        for w in (self.lieu, self.format):
            w.currentIndexChanged.connect(self._scene_changee)
        self.anime.toggled.connect(self._scene_changee)
        self.lieu_texte.editingFinished.connect(self._scene_changee)
        self._charger()
        self._maj()

    # ------------------------------------------------------------------ état
    def _charger(self):
        """Un clip déjà préparé pour ce morceau (clip.json dans son dossier) est repris."""
        import json
        m = self.ed.projet.media(self.clip_son["media"]) if self.clip_son else None
        d = (m or {}).get("clip_groupe")
        if d and os.path.exists(os.path.join(d, "clip.json")):
            try:
                with open(os.path.join(d, "clip.json"), encoding="utf-8") as f:
                    self.clip = json.load(f)
            except (OSError, ValueError):
                self.clip = None
        if self.clip:
            for w in (self.lieu, self.anime, self.lieu_texte, self.format):
                w.blockSignals(True)
            self.lieu.setCurrentIndex(max(0, self.lieu.findData(self.clip["lieu"])))
            self.anime.setChecked(bool(self.clip.get("anime")))
            self.lieu_texte.setText(self.clip.get("lieu_texte", ""))
            self.format.setCurrentIndex(max(0, self.format.findData(self.clip.get("format", "16:9"))))
            for w in (self.lieu, self.anime, self.lieu_texte, self.format):
                w.blockSignals(False)
            self.reutiliser.blockSignals(True)
            self.reutiliser.setChecked(self.clip.get("reutiliser", True))
            self.reutiliser.blockSignals(False)
            self._afficher()

    def _en_calcul(self):
        return self.tache is not None and self.tache.isRunning()

    def _choix_niveau(self):
        """Pour écrire les idées : Claude d'abord (le meilleur pour cela), Gemini ou l'IA de ce poste au choix."""
        from . import ia
        c = QComboBox()
        clefs = {m for m, _k in ia.moteurs(dict(self.params, ia_moteur="claude"))}
        if "claude" in clefs:
            c.addItem(_("Claude (cloud, le meilleur pour écrire)"), "claude")
        if "gemini" in clefs:
            c.addItem(_("Gemini (cloud)"), "gemini")
        c.addItem(_("IA locale (sur ce poste, gratuit)"), "locale")
        return c

    def _maj(self, *_a):
        pret = self.clip is not None
        for w in (self.b_idees,):
            w.setEnabled(pret and not self._en_calcul())
        self.lieu_texte.setVisible(self.lieu.currentData() == "ailleurs")
        manque = None
        if not pret:
            manque = _("Commencez par « Ecouter le morceau ».")
        elif not self.moteur.count():
            manque = _("Aucun moteur vidéo : ajoutez une clef Gemini ou fal.ai (Préférences › Assistant et IA).")
        if pret:
            self.clip["moteur"] = self.moteur.currentData() or ""
            v, l, im, t = CG.prix_detail(self.clip, self.params, self.images.isChecked())
            n = len(CG.a_fabriquer(self.clip))
            fait = sum(1 for i in range(len(self.clip["plans"])) if CG.fichier_du_plan(self.clip, i) and
                       os.path.exists(CG.fichier_du_plan(self.clip, i)))
            texte = _("{n} plans à fabriquer sur {t} (les autres reprennent un plan) : environ {p} $ — vidéo {v} $, lèvres {l} $, "
                      "images {i} $. Demandé avant de lancer.", n=n, t=len(self.clip["plans"]), p=_d(t), v=_d(v), l=_d(l), i=_d(im))
            if n == 0:
                texte = _("Tous les plans sont prêts : regardez-les (cliquez une ligne), puis « Poser le clip sous la chanson ».")
            self.cout.setText(manque or texte)
            self.b_poser.setEnabled(fait > 0 and not self._en_calcul())
        else:
            self.cout.setText(manque)
            self.b_poser.setEnabled(False)
        self.cout.setStyleSheet("font-weight:600;color:#c98a00" if manque else "font-weight:600")
        self.b_fabriquer.setEnabled(pret and not manque and self.accord.isChecked() and not self._en_calcul()
                                    and bool(CG.a_fabriquer(self.clip)))
        self.b_ecouter.setEnabled(not self._en_calcul())

    def _lire_tables(self):
        if not self.clip:
            return
        g = []
        for r in range(self.table_groupe.rowCount()):
            cb = self.table_groupe.cellWidget(r, 0)
            role = cb.currentData() if cb else "guitare"
            nom = (self.table_groupe.item(r, 1) or QTableWidgetItem("")).text().strip()
            desc = (self.table_groupe.item(r, 2) or QTableWidgetItem("")).text().strip()
            anc = self.clip["groupe"][r] if r < len(self.clip["groupe"]) else {}
            img = anc.get("image", "") if anc.get("description") == desc and anc.get("role") == role else ""
            g.append({"role": role, "nom": nom or CG.ROLES.get(role, role), "description": desc, "image": img})
        self.clip["groupe"] = g
        for r, p in enumerate(self.clip["plans"]):
            it = self.table.item(r, 2)
            if it and it.text().strip() and it.text().strip() != p["action"] and p.get("reprend") is None:
                p.update(action=it.text().strip(), action_en="", consigne="")
            ch = self.table.cellWidget(r, 3)
            if ch is not None and p.get("reprend") is None:
                p["chant"] = ch.isChecked()
        self.clip["lieu_texte"] = self.lieu_texte.text().strip() or self.clip.get("lieu_texte", "")

    def _afficher(self):
        c = self.clip
        an = c["analyse"]
        self.bande.poser(an["sections"], an["duree"])
        self.resume.setText(_("{b} battements par minute, {n} parties. {r}", b=int(an.get("bpm") or 0), n=len(an["sections"]),
                              r=an.get("resume", "")) + ((" " + _("Voix : {v}.", v=an["voix_fr"])) if an.get("voix_fr") else ""))
        if not self.lieu_texte.text():
            self.lieu_texte.setText(c.get("lieu_texte", ""))
        self.table_groupe.setRowCount(0)
        for m in c["groupe"]:
            self._ligne_membre(m)
        self.table.setRowCount(len(c["plans"]))
        for r, p in enumerate(c["plans"]):
            self.table.setItem(r, 0, _fixe(_tc(p["debut"])))
            self.table.setItem(r, 1, _fixe(CG.PARTIES.get(p["partie"], p["partie"])))
            it = QTableWidgetItem(p["action"])
            if p.get("reprend") is not None:
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                it.setForeground(QColor("#9aa4b2"))
                it.setToolTip(_("Reprend le plan {n}", n=p["reprend"] + 1))
            self.table.setItem(r, 2, it)
            if p.get("reprend") is None and c["analyse"].get("chante") and "chant" in p["qui"]:
                ch = QCheckBox()
                ch.setChecked(bool(p.get("chant")))
                ch.setToolTip(_("Lèvres calées sur la voix (LatentSync, fal.ai)"))
                ch.toggled.connect(lambda _c: (self._lire_tables(), self._maj()))
                self.table.setCellWidget(r, 3, ch)
            else:
                self.table.removeCellWidget(r, 3)
                self.table.setItem(r, 3, _fixe(""))
            self._etat_plan(r)
        self.table.resizeColumnToContents(0)
        self.table.resizeRowsToContents()
        self.table.resizeColumnToContents(1)
        self._maj()

    def _etat_plan(self, r):
        f = CG.fichier_du_plan(self.clip, r)
        p = self.clip["plans"][r]
        t = "✓" if f and os.path.exists(f) else (_("reprend {n}", n=p["reprend"] + 1) if p.get("reprend") is not None else "")
        self.table.setItem(r, 4, _fixe(t))

    def _ligne_membre(self, m):
        r = self.table_groupe.rowCount()
        self.table_groupe.insertRow(r)
        cb = QComboBox()
        for k, lib in sorted(CG.ROLES.items(), key=lambda kv: CG._net(kv[1])):
            cb.addItem(lib, k)
        cb.setCurrentIndex(max(0, cb.findData(m["role"])))
        self.table_groupe.setCellWidget(r, 0, cb)
        self.table_groupe.setItem(r, 1, QTableWidgetItem(m.get("nom", "")))
        self.table_groupe.setItem(r, 2, QTableWidgetItem(m.get("description", "")))

    def _ajouter_membre(self):
        if not self.clip:
            return
        self._lire_tables()
        self.clip["groupe"].append({"role": "claviers", "nom": CG.ROLES["claviers"],
                                    "description": CG.LOOKS[len(self.clip["groupe"]) % len(CG.LOOKS)], "image": ""})
        self._ligne_membre(self.clip["groupe"][-1])
        self._maj()

    def _retirer_membre(self):
        r = self.table_groupe.currentRow()
        if self.clip and 0 <= r < len(self.clip["groupe"]):
            self._lire_tables()
            del self.clip["groupe"][r]
            self.table_groupe.removeRow(r)
            self._maj()

    def _scene_changee(self, *_a):
        if not self.clip:
            self._maj()
            return
        self._lire_tables()
        self.clip.update(lieu=self.lieu.currentData(), anime=self.anime.isChecked(), format=self.format.currentData())
        for g in self.clip["groupe"]:
            g["image"] = ""                    # le rendu change : portraits à refaire
        self.redecouper()

    def redecouper(self, *_a):
        if not self.clip:
            return
        if any(p.get("fichier") for p in self.clip["plans"]) and QMessageBox.question(
                self, _("Refaire le découpage"), _("Des plans sont déjà fabriqués : les oublier et refaire le découpage ?")) != QMessageBox.Yes:
            return
        self._lire_tables()
        self.clip["reutiliser"] = self.reutiliser.isChecked()
        self.clip["plans"] = CG.decouper(self.clip)
        self._afficher()

    # ------------------------------------------------------------------ calculs
    def _lancer(self, travail, titre, fin):
        self.tache = Tache(travail, titre)
        self.tache.lier(self)
        from .widgets import suivre_en_fond
        suivre_en_fond(self, self.tache, titre)
        self.tache.progression.connect(lambda f, t: (self.barre.setValue(int(f * 1000)), t and self.etat.setText(t)), Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, e: self._fin(r, e, fin), Qt.QueuedConnection)
        self.barre.setValue(0)
        self.barre.show()
        self.b_arreter.show()
        self._maj()
        self.tache.start()

    def _fin(self, r, err, fin):
        self.barre.hide()
        self.b_arreter.hide()
        if err:
            self.etat.setText(_("Arrêté.") if isinstance(err, InterruptedError) else _("✕ {e}", e=texte_erreur(err)[:400]))
        fin(r, err)
        self._maj()

    def ecouter(self):
        if self._en_calcul() or not self.chemin:
            return
        chemin, params, separer = self.chemin, self.params, self.separer.isChecked()

        def fin(an, err):
            if err:
                return
            self.clip = CG.nouveau(chemin, an, self.fiche, self.lieu.currentData(), self.anime.isChecked(), self.format.currentData())
            if self.lieu_texte.text().strip():
                self.clip["lieu_texte"] = self.lieu_texte.text().strip()
            self.clip["reutiliser"] = self.reutiliser.isChecked()
            self.clip["plans"] = CG.decouper(self.clip)
            self._noter_dossier()
            self._afficher()
            self.etat.setText(_("✓ Morceau écouté : relisez le groupe et les plans, puis fabriquez."))
        self._lancer(lambda t: CG.analyser(chemin, params, separer, t.avancer, lambda: t.arret), _("Clip : écoute du morceau"), fin)

    def _noter_dossier(self):
        CG.enregistrer(self.clip)
        m = self.ed.projet.media(self.clip_son["media"]) if self.clip_son else None
        if m is not None:
            m["clip_groupe"] = CG.dossier(self.clip)

    def idees(self):
        if not self.clip or self._en_calcul():
            return
        self._lire_tables()
        from .dialogues_musique_ia import _avec_moteur
        niveau = self.niveau.currentData()
        clip, params = self.clip, self.params

        def fin(n, err):
            if not err:
                self._afficher()
                self.etat.setText(_("✓ {n} plans réécrits par l'IA : modifiez ce qui ne vous plaît pas.", n=n))
        self._lancer(lambda t: _avec_moteur(niveau, lambda: CG.idees_ia(clip, params, "locale" if niveau == "locale" else "cloud")),
                     _("Clip : idées de plans"), fin)

    def fabriquer(self):
        if not self.clip or self._en_calcul() or not self.accord.isChecked():
            return
        self._lire_tables()
        avec = self.images.isChecked()
        v, l, im, total = CG.prix_detail(self.clip, self.params, avec)
        a_faire = CG.a_fabriquer(self.clip)
        if QMessageBox.question(self, _("Fabriquer les plans"),
                                _("Fabriquer {n} plans pour environ {p} $ (vidéo {v} $, lèvres {l} $, images {i} $), facturés sur vos "
                                  "comptes ? Vous pourrez fermer la fenêtre : la barre du bas suit.", n=len(a_faire), p=_d(total),
                                  v=_d(v), l=_d(l), i=_d(im))) != QMessageBox.Yes:
            return
        clip, params = self.clip, self.params
        self._noter_dossier()

        def travail(t):
            n = len(a_faire) + (len(clip["groupe"]) if avec else 0)
            k = 0
            if avec:
                for j, g in enumerate(clip["groupe"]):
                    if not (g.get("image") and os.path.exists(g["image"])):
                        t.avancer(k / n, _("Portrait : {m}", m=g["nom"]))
                        CG.portrait(clip, j, params)
                    k += 1
                    if t.arret:
                        raise InterruptedError()
            faits, erreurs = 0, []
            for i in a_faire:
                if t.arret:
                    raise InterruptedError()
                try:
                    CG.fabriquer_plan(clip, i, params, avec, lambda f, x="", k=k: t.avancer((k + f) / n, x), lambda: t.arret)
                    faits += 1
                except InterruptedError:
                    raise
                except Exception as e:     # noqa: BLE001 : un plan raté n'arrête pas les autres
                    erreurs.append((i, texte_erreur(e)))
                k += 1
            CG.enregistrer(clip)
            return faits, erreurs

        def fin(r, err):
            for row in range(self.table.rowCount()):
                self._etat_plan(row)
            if err:
                return
            faits, erreurs = r
            msg = _("✓ {n} plans fabriqués. Cliquez une ligne pour regarder, puis « Poser le clip sous la chanson ».", n=faits)
            if erreurs:
                msg += " " + _("{n} plans ratés (relancez « Fabriquer » pour eux seuls) : {e}", n=len(erreurs), e=erreurs[0][1][:200])
            self.etat.setText(msg)
        self._lancer(travail, _("Clip : fabrication des plans"), fin)

    def _voir_plan(self, r):
        if not self.clip or not 0 <= r < len(self.clip["plans"]):
            return
        f = CG.fichier_du_plan(self.clip, r)
        if f and os.path.exists(f):
            self.apercu.show()
            self.apercu.charger(f, video=True)
            self.apercu.fondu_e.hide()
            self.apercu.fondu_s.hide()
        else:
            self.apercu.arreter()
            self.apercu.hide()

    def poser(self):
        if not self.clip:
            return
        ed, p = self.ed, self.ed.projet
        self.apercu.arreter()
        p.marquer()
        if self.clip_son and p.clip(self.clip_son["id"]) is not None:
            c = p.clip(self.clip_son["id"])
            t0 = c["debut"] - c["src_debut"]
            fen = (c["src_debut"], c["src_fin"])
        else:
            from . import moteur
            t0 = ed.timeline.position
            m = p.ajouter_media(self.chemin, moteur.sonder(self.chemin))
            c = p.ajouter_clip(m["id"], p.pistes_audio()[0], t0)
            self.clip_son = c
            fen = None
        n = CG.monter(p, self.clip, t0, fen)
        ed.rafraichir()
        self.etat.setText(_("✓ {n} plans posés sous la chanson, chaque coupe sur une mesure. Edition › Annuler pour revenir.", n=n))

    def closeEvent(self, ev):
        from .widgets import garder_calcul
        self.apercu.arreter()
        if garder_calcul(self, self._en_calcul()):
            ev.ignore()
            return
        if self.clip:
            self._lire_tables()
            CG.enregistrer(self.clip)
        super().closeEvent(ev)

    def done(self, r):
        from .widgets import garder_calcul
        if garder_calcul(self, self._en_calcul()):
            return
        super().done(r)


def _d(x):
    return f"{x:.2f}".replace(".", ",")


def _fixe(t):
    it = QTableWidgetItem(t)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it
