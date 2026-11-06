"""Téléchargements de l'IA locale (moteurs, modèles, voix) : une file d'attente visible, un seul à la fois.

Fenêtre « Téléchargements » (Outils, ou bouton en bas de la fenêtre) : pour chacun, la taille, la progression, la
vitesse, le temps restant estimé, l'état (en attente, en cours, terminé, erreur) et un bouton pour l'arrêter. Elle se
ferme et se rouvre à volonté : les téléchargements continuent derrière.
"""
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QProgressBar, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .langue import _
from .taches import Tache

ATTENTE, EN_COURS, FINI, ERREUR, ARRETE, PAUSE = "attente", "en_cours", "fini", "erreur", "arrete", "pause"
ETATS = {ATTENTE: _("En attente"), EN_COURS: _("En cours"), FINI: _("Terminé"), ERREUR: _("Erreur"), ARRETE: _("Arrêté"),
         PAUSE: _("En pause")}
NON_FINIS = (ATTENTE, EN_COURS, PAUSE)


def duree_texte(s):
    if s is None or s < 0:
        return "—"
    s = int(s)
    if s < 60:
        return _("{s} s", s=s)
    if s < 3600:
        return _("{m} min {s:02d}", m=s // 60, s=s % 60)
    return _("{h} h {m:02d}", h=s // 3600, m=(s % 3600) // 60)


class GestionTelechargements(QObject):
    change = Signal()
    termine = Signal(str, object)        # clef, erreur (None si tout va bien)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.params = params
        self.travaux = []                # dicts : cle, nom, taille, etat, fraction, vitesse, reste, texte, erreur
        self.tache = None
        self._restaurer()

    # ---- d'une session à l'autre : ce qui n'était pas fini revient « en pause », prêt à reprendre où il s'était arrêté
    def _restaurer(self):
        from . import packs_ia
        try:
            cat = packs_ia.modeles(avec_essai=True)
        except Exception:        # noqa: BLE001
            return
        for k in list(self.params.get("telechargements_non_finis") or []):
            if k not in cat or any(t["cle"] == k for t in self.travaux):
                continue
            try:
                taille = packs_ia.a_telecharger(k)
            except Exception:    # noqa: BLE001
                taille = 0
            if not taille:
                continue
            self.travaux.append({"cle": k, "nom": cat[k].get("nom", k), "taille": taille, "etat": PAUSE, "fraction": self._deja(k, taille),
                                 "vitesse": 0.0, "reste": None, "texte": _("Commencé lors d'une session précédente"), "erreur": None})

    def _deja(self, cle, taille):
        """Part déjà téléchargée (fichiers .part laissés par l'arrêt), pour montrer où l'on reprendra."""
        from . import packs_ia
        try:
            n = packs_ia.octets_partiels(cle)
        except Exception:        # noqa: BLE001
            n = 0
        return max(0.0, min(0.99, n / taille)) if taille else 0.0

    def _sauver(self):
        cles = [t["cle"] for t in self.travaux if t["etat"] in NON_FINIS]
        if list(self.params.get("telechargements_non_finis") or []) != cles:
            self.params["telechargements_non_finis"] = cles
            try:
                self.params.enregistrer()
            except Exception:    # noqa: BLE001
                pass

    def non_finis(self):
        return [t for t in self.travaux if t["etat"] == PAUSE]

    # ---- file d'attente
    def ajouter(self, cles):
        from . import packs_ia
        cat = packs_ia.modeles(avec_essai=True)
        for k in cles:
            ex = next((t for t in self.travaux if t["cle"] == k and t["etat"] in NON_FINIS), None)
            if ex is not None:
                if ex["etat"] == PAUSE:
                    ex["etat"] = ATTENTE
                continue
            self.travaux.append({"cle": k, "nom": (cat.get(k) or {}).get("nom", k), "taille": packs_ia.a_telecharger(k),
                                 "etat": ATTENTE, "fraction": 0.0, "vitesse": 0.0, "reste": None, "texte": "", "erreur": None})
        self._sauver()
        self.change.emit()
        self._suivant()

    def actifs(self):
        return [t for t in self.travaux if t["etat"] in (ATTENTE, EN_COURS)]

    def en_file(self, cle):
        return any(t["cle"] == cle for t in self.actifs())

    def arreter(self, cle):
        for t in self.travaux:
            if t["cle"] == cle:
                if t["etat"] == ATTENTE:
                    t["etat"] = ARRETE
                elif t["etat"] == PAUSE:
                    t["etat"] = ARRETE
                elif t["etat"] == EN_COURS and self.tache is not None:
                    self.tache.stopper()
        self._sauver()
        self.change.emit()

    def pause(self, cle):
        """Mettre en pause : ce qui est téléchargé est gardé ; « Reprendre » repart de là, même après avoir fermé PhilCut."""
        for t in self.travaux:
            if t["cle"] == cle:
                if t["etat"] == ATTENTE:
                    t["etat"] = PAUSE
                elif t["etat"] == EN_COURS and self.tache is not None:
                    t["pause_demandee"] = True
                    self.tache.stopper()
        self._sauver()
        self.change.emit()

    def reprendre(self, cle=None):
        """Reprend un téléchargement en pause, en erreur ou arrêté : il repart de ce qui est déjà téléchargé."""
        for t in self.travaux:
            if t["etat"] in (PAUSE, ERREUR, ARRETE) and (cle is None or t["cle"] == cle):
                t["etat"], t["texte"], t["erreur"] = ATTENTE, "", None
        self._sauver()
        self.change.emit()
        self._suivant()

    def nettoyer(self):
        self.travaux = [t for t in self.travaux if t["etat"] in NON_FINIS]
        self.change.emit()

    # ---- exécution, un à la fois
    def _suivant(self):
        if self.tache is not None:
            return
        t = next((x for x in self.travaux if x["etat"] == ATTENTE), None)
        if t is None:
            return
        from . import packs_ia
        t["etat"] = EN_COURS
        t["debut"] = time.monotonic()
        mesures = []

        def avancer(f, texte=""):
            maintenant = time.monotonic()
            t["fraction"], t["texte"] = f, texte
            mesures.append((maintenant, f * (t["taille"] or 0)))
            while len(mesures) > 2 and maintenant - mesures[0][0] > 8:      # vitesse sur les 8 dernières secondes
                mesures.pop(0)
            if len(mesures) > 1 and mesures[-1][0] > mesures[0][0]:
                t["vitesse"] = max(0.0, (mesures[-1][1] - mesures[0][1]) / (mesures[-1][0] - mesures[0][0]))
                t["reste"] = (t["taille"] * (1 - f)) / t["vitesse"] if t["vitesse"] > 0 and t["taille"] else None

        def travail(tache):
            packs_ia.installer(t["cle"], lambda f, x="": tache.avancer(f, x), arret=lambda: tache.arret)
            return True
        self.tache = Tache(travail, _("Téléchargement"))
        self.tache.progression.connect(avancer)
        self.tache.fini.connect(lambda r, e, t=t: self._fini(t, e))
        self.tache.start()
        self.change.emit()

    def _fini(self, t, erreur):
        self.tache = None
        if erreur is None:
            t["etat"], t["fraction"], t["reste"] = FINI, 1.0, 0
            from . import packs_ia
            genre = (packs_ia.modeles(avec_essai=True).get(t["cle"]) or {}).get("genre")
            if genre:
                choix = dict(self.params.get("ia_locale_modeles") or {})
                choix[genre] = t["cle"]
                self.params["ia_locale_modeles"] = choix
                self.params.enregistrer()
        elif isinstance(erreur, InterruptedError):
            t["etat"] = PAUSE if t.pop("pause_demandee", False) else ARRETE
        else:
            t["etat"], t["erreur"] = ERREUR, str(erreur)
        self.termine.emit(t["cle"], None if erreur is None else erreur)
        self._sauver()
        self.change.emit()
        self._suivant()

    def attendre(self):
        while self.tache is not None and self.tache.isRunning():
            self.tache.wait(200)


class FenetreTelechargements(QDialog):
    """Ce qui se télécharge : taille, progression, vitesse, temps restant, file d'attente. Se ferme sans rien arrêter."""

    def __init__(self, parent, gestion):
        super().__init__(parent)
        self.setWindowTitle(_("Téléchargements"))
        self.setModal(False)
        self.resize(1000, 340)
        self.g = gestion
        v = QVBoxLayout(self)
        intro = QLabel(_("Modèles et moteurs de l'IA locale, rangés dans le dossier de PhilCut. Un à la fois ; vous pouvez fermer "
                         "cette fenêtre, les téléchargements continuent. Un téléchargement arrêté reprendra où il s'était arrêté."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([_("Elément"), _("Taille"), _("Progression"), _("Etat"), _("Vitesse"), _("Reste"), ""])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        colonnes_reglables(self.table, gestion.params, "colonnes_telechargements", [210, 80, 140, 125, 85, 80, 200])
        v.addWidget(self.table, 1)
        self.resume = QLabel("")
        v.addWidget(self.resume)
        bb = QDialogButtonBox()
        b_rep = bb.addButton(_("Tout reprendre"), QDialogButtonBox.ActionRole)
        b_rep.clicked.connect(lambda: self.g.reprendre())
        b_net = bb.addButton(_("Retirer les terminés"), QDialogButtonBox.ActionRole)
        b_net.clicked.connect(self.g.nettoyer)
        bb.addButton(_("Fermer"), QDialogButtonBox.RejectRole).clicked.connect(self.close)
        v.addWidget(bb)
        self.g.change.connect(self.remplir)
        self.minuteur = QTimer(self)
        self.minuteur.timeout.connect(self.actualiser)
        self.minuteur.start(500)
        self.remplir()

    def remplir(self):
        from . import packs_ia
        self.table.setRowCount(len(self.g.travaux))
        self._barres = []
        for i, t in enumerate(self.g.travaux):
            self.table.setItem(i, 0, QTableWidgetItem(t["nom"]))
            self.table.setItem(i, 1, QTableWidgetItem(packs_ia.taille_texte(t["taille"]) if t["taille"] else "—"))
            b = QProgressBar()
            b.setRange(0, 1000)
            self.table.setCellWidget(i, 2, b)
            self._barres.append(b)
            for c in (3, 4, 5):
                self.table.setItem(i, c, QTableWidgetItem(""))
            if t["etat"] in NON_FINIS:
                self.table.setCellWidget(i, 6, boutons_ligne(self.g, t))
            else:
                self.table.setCellWidget(i, 6, None)
                self.table.setItem(i, 6, QTableWidgetItem(""))
        self.actualiser()

    def actualiser(self):
        from . import packs_ia
        if len(getattr(self, "_barres", [])) != len(self.g.travaux):
            return self.remplir()
        for i, t in enumerate(self.g.travaux):
            b = self._barres[i]
            b.setValue(int(t["fraction"] * 1000))
            etat = ETATS[t["etat"]]
            if t["etat"] == EN_COURS:
                etat = f"{int(t['fraction'] * 100)} %"
                b.setToolTip(t["texte"] or "")
            elif t["etat"] == PAUSE:
                etat = _("En pause ({p} %)", p=int(t["fraction"] * 100))
                b.setToolTip(t["texte"] or "")
            elif t["etat"] == ERREUR:
                b.setToolTip(t["erreur"] or "")
                self.table.item(i, 3).setToolTip(t["erreur"] or "")
            self.table.item(i, 3).setText(etat)
            self.table.item(i, 4).setText(f"{packs_ia.taille_texte(t['vitesse'])}/s" if t["etat"] == EN_COURS and t["vitesse"] else "")
            self.table.item(i, 5).setText(duree_texte(t["reste"]) if t["etat"] == EN_COURS else ("" if t["etat"] != ERREUR else (t["erreur"] or "")[:60]))
        actifs = self.g.actifs()
        if actifs:
            reste = sum((t["taille"] or 0) * (1 - t["fraction"]) for t in actifs)
            vit = next((t["vitesse"] for t in actifs if t["etat"] == EN_COURS and t["vitesse"]), 0)
            self.resume.setText(_("{n} en cours ou en attente · reste {r} à télécharger{e}", n=len(actifs), r=packs_ia.taille_texte(reste),
                                  e=_(" · environ {d}", d=duree_texte(reste / vit)) if vit else ""))
        elif self.g.non_finis():
            self.resume.setText(_("{n} en pause : « Reprendre » repart de là où il s'était arrêté.", n=len(self.g.non_finis())))
        else:
            self.resume.setText(_("Rien en cours."))


def boutons_ligne(g, t):
    """Pause / Reprendre et Arrêter, pour une ligne de téléchargement non terminée."""
    w = QWidget()
    hl = QHBoxLayout(w)
    hl.setContentsMargins(2, 0, 2, 0)
    hl.setSpacing(4)
    if t["etat"] in (PAUSE, ERREUR, ARRETE):
        bp = QPushButton(_("▶ Reprendre"))
        bp.setToolTip(_("Repart de là où il s'était arrêté.") + (("\n" + t["erreur"]) if t.get("erreur") else ""))
        bp.clicked.connect(lambda _c=False, k=t["cle"]: g.reprendre(k))
        if t["etat"] != PAUSE:                    # erreur ou arrêt : seulement « Reprendre »
            hl.addWidget(bp)
            hl.addStretch(1)
            return w
    else:
        bp = QPushButton(_("⏸ Pause"))
        bp.setToolTip(_("Ce qui est déjà téléchargé est gardé, même si vous fermez PhilCut."))
        bp.clicked.connect(lambda _c=False, k=t["cle"]: g.pause(k))
    hl.addWidget(bp)
    bs = QPushButton(_("Arrêter"))
    bs.clicked.connect(lambda _c=False, k=t["cle"]: g.arreter(k))
    hl.addWidget(bs)
    hl.addStretch(1)
    return w


def colonnes_reglables(table, params, cle, largeurs):
    """Colonnes que l'on élargit à la souris ; les largeurs choisies sont retenues pour la prochaine fois."""
    h = table.horizontalHeader()
    h.setSectionResizeMode(QHeaderView.Interactive)
    h.setStretchLastSection(True)
    h.setMinimumSectionSize(40)
    gardees = list((params.get(cle) if params is not None else None) or [])
    for i, l in enumerate(largeurs):
        table.setColumnWidth(i, int(gardees[i]) if i < len(gardees) and gardees[i] else l)
    table.setWordWrap(True)
    h.setToolTip(_("Tirez le bord d'une colonne pour l'élargir ou la rétrécir."))

    def retenir(*_a):
        if params is not None:
            params[cle] = [table.columnWidth(i) for i in range(table.columnCount())]
    h.sectionResized.connect(retenir)
