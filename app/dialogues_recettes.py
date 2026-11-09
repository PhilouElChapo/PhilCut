"""« Créations à refaire ou à calculer » et comparaison avant / après (0.9.37). Rien n'est lancé sans votre clic ;
rien n'entre dans le film sans votre choix."""
import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QProgressBar, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout)

from . import recettes_ia as R
from .langue import _
from .taches import Tache


class DialogueCreations(QDialog):
    def __init__(self, ed):
        super().__init__(ed)
        self.ed, self.params = ed, ed.params
        self.tache = None
        self.setWindowTitle(_("Créations à refaire ou à calculer"))
        self.resize(980, 560)
        v = QVBoxLayout(self)
        t = QLabel(_("Les créations IA de ce projet qui restent à faire : demandées sur un autre appareil « à calculer sur le PC », ou "
                     "dont le fichier n'est ni ici ni sur le Drive. Cochez, choisissez comment les faire, puis « Lancer la sélection » : "
                     "rien ne part sans ce clic. Chaque résultat se compare avec l'ancien avant d'entrer dans le film. Une création déjà "
                     "faite ici ou déposée sur le Drive est reprise telle quelle : jamais payée deux fois."))
        t.setWordWrap(True)
        v.addWidget(t)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderLabels([_("Création"), _("Pourquoi"), _("Comment"), _("Coût, durée")])
        self.arbre.setRootIsDecorated(False)
        self.arbre.setWordWrap(True)
        h = self.arbre.header()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        v.addWidget(self.arbre, 1)
        self.etape = QLabel("")
        self.etape.setWordWrap(True)
        v.addWidget(self.etape)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.hide()
        v.addWidget(self.barre)
        hb = QHBoxLayout()
        self.b_lancer = QPushButton(_("Lancer la sélection"))
        self.b_lancer.setStyleSheet("font-weight:600;padding:5px 14px")
        self.b_lancer.clicked.connect(self.lancer)
        hb.addWidget(self.b_lancer)
        self.b_arreter = QPushButton(_("Arrêter"))
        self.b_arreter.hide()
        self.b_arreter.clicked.connect(lambda: self.tache and self.tache.stopper())
        hb.addWidget(self.b_arreter)
        b = QPushButton(_("Garder tel quel (retirer de la liste)"))
        b.setToolTip(_("La ligne disparaît ; le plan reste comme il est (gris s'il manque). La recette est gardée."))
        b.clicked.connect(self.garder_tel_quel)
        hb.addWidget(b)
        hb.addStretch(1)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.accept)
        hb.addWidget(b)
        v.addLayout(hb)
        self._horloge = QTimer(self)
        self._horloge.setInterval(1000)
        self._horloge.timeout.connect(self._tic)
        self.remplir()

    def remplir(self):
        self.arbre.clear()
        self.lignes = R.a_traiter(self.ed.projet, self.params)
        for i, l in enumerate(self.lignes):
            rec = l["recette"]
            titre = f"{R.INTENTIONS.get(l['intention'], l['intention'])} — {l['media'].get('nom', '')}"
            detail = (rec.get("prompt") or (rec.get("fiche") or {}).get("phrase") or rec.get("anglais") or "")[:120]
            it = QTreeWidgetItem([titre + ("\n" + detail if detail else ""), l["pourquoi"], "", ""])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(0, Qt.Checked)
            it.setData(0, Qt.UserRole, i)
            self.arbre.addTopLevelItem(it)
            c = QComboBox()
            if l["existant"]:
                c.addItem(_("Reprendre le résultat déjà fait (gratuit)"), "deja")
            for m, lib, prix, duree in R.moteurs_possibles(l, self.params):
                c.addItem(lib, m)
            c.currentIndexChanged.connect(lambda _x, it=it, c=c, l=l: self._cout(it, c, l))
            self.arbre.setItemWidget(it, 2, c)
            self._cout(it, c, l)
        if not self.lignes:
            self.arbre.addTopLevelItem(QTreeWidgetItem([_("Rien à refaire ni à calculer : toutes les créations sont là."), "", "", "✓"]))
            self.b_lancer.setEnabled(False)

    def _cout(self, it, c, l):
        m = c.currentData()
        if m == "deja":
            it.setText(3, _("0 € — déjà fait"))
            return
        for mm, _lib, prix, duree in R.moteurs_possibles(l, self.params):
            if mm == m:
                txt = (_("gratuit") if not prix else _("≈ {p} €", p=f"{prix:.2f}".replace(".", ","))) + \
                      (" · " + _("≈ {d} min", d=max(1, int(duree // 60))) if duree else "")
                if l["paye"] and prix:
                    txt += "\n" + _("⚠ déjà payée une fois")
                it.setText(3, txt)

    def garder_tel_quel(self):
        it = self.arbre.currentItem()
        if not it or it.data(0, Qt.UserRole) is None:
            return
        m = self.lignes[it.data(0, Qt.UserRole)]["media"]
        m.pop("a_calculer", None)
        m["recette_ignoree"] = True
        rec = m.pop("recette", None)
        if rec:
            m["recette_gardee"] = rec
        self.ed.projet.modifie = True
        self.remplir()

    def _choisis(self):
        out = []
        for k in range(self.arbre.topLevelItemCount()):
            it = self.arbre.topLevelItem(k)
            i = it.data(0, Qt.UserRole)
            if i is None or it.checkState(0) != Qt.Checked:
                continue
            c = self.arbre.itemWidget(it, 2)
            out.append((self.lignes[i], c.currentData() if c else "outil"))
        return out

    def lancer(self):
        choix = self._choisis()
        if not choix:
            return
        outils = [l for l, m in choix if m == "outil"]
        auto = [(l, m) for l, m in choix if m != "outil"]
        if outils and not auto:                       # une création à revoir dans son outil : on l'ouvre, recette remplie
            self.accept()
            for l in outils[:1]:
                self.ed.reprendre_creation(media_id=l["media"]["id"])
            return
        payants = [(l, m) for l, m in auto if m not in ("locale", "deja")]
        if payants:                                   # coût annoncé, confirmation ; « déjà payée » signalé
            total = 0.0
            lignes = []
            for l, m in payants:
                prix = next((p for mm, _lib, p, _d in R.moteurs_possibles(l, self.params) if mm == m), 0.0)
                total += prix
                lignes.append(f"• {l['media'].get('nom', '')} : ≈ {prix:.2f} €".replace(".", ",") + (" — " + _("déjà payée une fois") if l["paye"] else ""))
            r = QMessageBox.question(self, _("Créations payantes"),
                                     _("Ces créations seront refaites avec votre clef Gemini (payant) :") + "\n" + "\n".join(lignes) + "\n\n" +
                                     _("Total estimé : ≈ {t} €. Continuer ?", t=f"{total:.2f}".replace(".", ",")))
            if r != QMessageBox.Yes:
                return
        params = self.params

        def travail(t):
            res = []
            for k, (l, m) in enumerate(auto):
                if t.arret:
                    raise InterruptedError()
                base, part = k / len(auto), 1 / len(auto)
                t.avancer(base, _("{i}/{n} : {c}", i=k + 1, n=len(auto), c=l["media"].get("nom", "")))
                try:
                    chemin = l["existant"] if m == "deja" else R.calculer(l, m, params, lambda f, x="": t.avancer(base + part * f, x), lambda: t.arret)
                    res.append((l, chemin, None))
                except InterruptedError:
                    raise
                except Exception as e:      # noqa: BLE001 : une ligne ratée n'arrête pas les autres
                    res.append((l, None, e))
            return res
        self.tache = Tache(travail, _("Créations"))
        self.tache.progression.connect(self._progression, Qt.QueuedConnection)
        self.tache.fini.connect(self._fini, Qt.QueuedConnection)
        self._t0, self._f, self._txt = time.monotonic(), 0.0, _("Préparation…")
        self.b_lancer.setEnabled(False)
        self.b_arreter.show()
        self.barre.show()
        self._horloge.start()
        self.tache.start()
        self._outils = outils

    def _progression(self, f, txt):
        self._f = f
        if txt:
            self._txt = txt
        self.barre.setValue(int(f * 1000))
        self._tic()

    def _tic(self):
        e = time.monotonic() - self._t0
        s = f"{self._txt} — " + _("écoulé {e} s", e=int(e))
        if 0.05 < self._f < 0.995:
            s += " · " + _("reste environ {r} s", r=int(e / self._f - e))
        elif self._f >= 0.995:
            s += " · " + _("la barre est pleine : le dernier morceau s'enregistre")
        self.etape.setText(s)

    def _fini(self, res, err):
        self._horloge.stop()
        self.barre.hide()
        self.b_arreter.hide()
        self.b_lancer.setEnabled(True)
        if err:
            self.etape.setText(_("Arrêté.") if isinstance(err, InterruptedError) else _("✕ {e}", e=str(err)[:300]))
            return
        faits = 0
        for l, chemin, e in res or []:
            if e or not chemin:
                QMessageBox.warning(self, _("Créations"), _("« {n} » n'a pas pu être refaite : {e}", n=l["media"].get("nom", ""), e=str(e)[:300]))
                continue
            if DialogueAvantApres(self, l, chemin).exec() == QDialog.Accepted:
                faits += 1
        self.etape.setText(_("{n} création(s) intégrée(s).", n=faits))
        self.ed.biblio.remplir(self.ed.projet)
        self.ed.rafraichir()
        self.remplir()
        for l in getattr(self, "_outils", [])[:1]:
            self.ed.reprendre_creation(media_id=l["media"]["id"])


class DialogueAvantApres(QDialog):
    """L'ancien et le nouveau côte à côte : garder l'ancien, prendre le nouveau, ou garder les deux."""

    def __init__(self, parent, ligne, nouveau):
        super().__init__(parent)
        self.ligne, self.nouveau = ligne, nouveau
        self.ed = parent.ed
        m = ligne["media"]
        self.setWindowTitle(_("Avant / après : {n}", n=m.get("nom", "")))
        self.resize(980, 520)
        v = QVBoxLayout(self)
        ancien = m.get("chemin") if os.path.exists(m.get("chemin") or "") else None
        t = QLabel(_("A gauche ce que le film utilise, à droite le nouveau résultat. Ecoutez ou regardez, puis choisissez.") if ancien else
                   _("L'ancien fichier n'est pas sur ce poste : écoutez ou regardez le nouveau résultat, puis choisissez."))
        t.setWordWrap(True)
        v.addWidget(t)
        h = QHBoxLayout()
        from .dialogues_creatif import ApercuCreation
        video = os.path.splitext(nouveau)[1].lower() in (".mp4", ".mov", ".mkv", ".webm")
        image = os.path.splitext(nouveau)[1].lower() in (".png", ".jpg", ".jpeg", ".webp")
        self.apercus = []
        for titre, chemin in ((_("Avant"), ancien), (_("Après"), nouveau)):
            col = QVBoxLayout()
            lb = QLabel(f"<b>{titre}</b>")
            col.addWidget(lb)
            if not chemin:
                x = QLabel(_("(pas sur ce poste)"))
                x.setAlignment(Qt.AlignCenter)
                x.setMinimumHeight(200)
                col.addWidget(x)
            elif image:
                x = QLabel()
                x.setPixmap(QPixmap(chemin).scaled(440, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                col.addWidget(x)
            else:
                a = ApercuCreation(self)
                a.charger(chemin, video=video)
                self.apercus.append(a)
                col.addWidget(a)
            h.addLayout(col, 1)
        v.addLayout(h, 1)
        hb = QHBoxLayout()
        b = QPushButton(_("Prendre le nouveau"))
        b.setStyleSheet("font-weight:600")
        b.clicked.connect(self.prendre)
        hb.addWidget(b)
        b = QPushButton(_("Garder les deux (le nouveau dans les médias)"))
        b.clicked.connect(self.les_deux)
        hb.addWidget(b)
        b = QPushButton(_("Garder l'ancien"))
        b.clicked.connect(self.reject)
        hb.addWidget(b)
        hb.addStretch(1)
        v.addLayout(hb)

    def _stop(self):
        for a in self.apercus:
            a.arreter()

    def prendre(self):
        """Le média du projet pointe sur le nouveau fichier : tous les plans qui l'utilisent suivent (Annuler revient)."""
        self._stop()
        m = self.ligne["media"]
        self.ed.projet.marquer()
        if os.path.exists(m.get("chemin") or ""):
            m.setdefault("versions", []).append(m["chemin"])
        m["chemin"] = self.nouveau
        m.pop("a_calculer", None)
        m.pop("copie_legere", None)
        from .recettes_ia import noter_recette
        noter_recette(m, self.nouveau)
        self.ed.projet.modifie = True
        self.accept()

    def les_deux(self):
        self._stop()
        self.ed.importer([self.nouveau])
        self.ligne["media"].pop("a_calculer", None)
        self.accept()

    def done(self, r):
        self._stop()
        super().done(r)
