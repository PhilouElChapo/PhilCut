"""Le Centre d'activité : tout ce que PhilCut fait en arrière-plan, au même endroit.

Import des rushes, proxys, analyse, export, aperçus, IA, suivi, téléchargements de l'IA locale : chaque tâche est
inscrite ici avec son état, sa progression, sa durée, et un bouton pour l'arrêter. La barre du bas de la fenêtre
résume en permanence ce qui se passe (« Export — 43 % · 2 en attente ») ; un clic ouvre la fenêtre.
Règle commune à tous les logiciels : on sait toujours ce qui se passe."""
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QProgressBar, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .langue import _

EN_COURS, FINI, ERREUR, ARRETE, ATTENTE = "en_cours", "fini", "erreur", "arrete", "attente"
ETATS = {ATTENTE: _("En attente"), EN_COURS: _("En cours"), FINI: _("Terminé"), ERREUR: _("Erreur"), ARRETE: _("Arrêté"),
         "pause": _("En pause")}
_centre = None


def centre():
    global _centre
    if _centre is None:
        _centre = Centre()
    return _centre


def duree_texte(s):
    if s is None or s < 0:
        return "—"
    s = int(s)
    if s < 60:
        return _("{s} s", s=s)
    if s < 3600:
        return _("{m} min {s:02d}", m=s // 60, s=s % 60)
    return _("{h} h {m:02d}", h=s // 3600, m=(s % 3600) // 60)


class Centre(QObject):
    change = Signal()

    def __init__(self):
        super().__init__()
        self.lignes = []            # dicts : titre, texte, fraction, etat, debut, fin, erreur, tache, cle
        self.telechargements = None  # GestionTelechargements, branché par la fenêtre

    def suivre(self, tache, titre):
        """Inscrit une tâche de fond (Tache) : progression et fin suivies automatiquement."""
        if any(l.get("tache") is tache for l in self.lignes):
            return
        l = {"titre": titre, "texte": "", "fraction": 0.0, "etat": EN_COURS, "debut": time.monotonic(), "fin": None, "erreur": None,
             "tache": tache, "cle": None}
        self.lignes.append(l)
        del self.lignes[:-60]

        def prog(f, t):
            l["fraction"], l["texte"] = f, t
            self.change.emit()

        def fini(r, e):
            l["fin"] = time.monotonic()
            l["fraction"] = 1.0 if e is None else l["fraction"]
            if e is None:
                l["etat"] = FINI
            elif isinstance(e, InterruptedError) or getattr(tache, "arret", False):
                l["etat"] = ARRETE
            else:
                l["etat"], l["erreur"] = ERREUR, str(e)
            self.change.emit()
        tache.progression.connect(prog)
        tache.fini.connect(fini)
        self.change.emit()

    def arreter(self, l):
        t = l.get("tache")
        if t is not None and l["etat"] == EN_COURS:
            t.stopper()

    def actives(self):
        return [l for l in self.lignes if l["etat"] == EN_COURS]

    def nettoyer(self):
        self.lignes = [l for l in self.lignes if l["etat"] == EN_COURS]
        if self.telechargements is not None:
            self.telechargements.nettoyer()
        self.change.emit()

    def resume(self):
        """Une ligne pour la barre du bas : ce qui tourne, et combien attendent."""
        actives = self.actives()
        attente = 0
        if self.telechargements is not None:
            tl = self.telechargements.actifs()
            attente += len([t for t in tl if t["etat"] == "attente"])
            actives = actives + [{"titre": _("Téléchargement : {n}", n=t["nom"]), "fraction": t["fraction"], "texte": ""} for t in tl if t["etat"] == "en_cours"]
        if not actives:
            pz = [t for t in (self.telechargements.travaux if self.telechargements is not None else []) if t["etat"] == "pause"]
            if pz:
                return _("Prêt · {n} téléchargement(s) en pause", n=len(pz)), False
            return _("Prêt"), False
        a = actives[0]
        txt = a["titre"] + (f" — {int(a['fraction'] * 100)} %" if a["fraction"] > 0 else "…")
        if a.get("texte"):
            txt += f" ({a['texte'][:40]})"
        reste = len(actives) - 1 + attente
        if reste:
            txt += _(" · {n} autre(s)", n=reste)
        return txt, True


class FenetreActivite(QDialog):
    """Toutes les tâches : état, progression, détail, durée, arrêt ; téléchargements compris."""

    def __init__(self, parent, centre):
        super().__init__(parent)
        self.setWindowTitle(_("Centre d'activité"))
        self.setModal(False)
        self.resize(1060, 400)
        self.c = centre
        v = QVBoxLayout(self)
        intro = QLabel(_("Tout ce que PhilCut fait en arrière-plan : imports, exports, aperçus, IA, téléchargements de l'IA locale. "
                         "Fermer cette fenêtre n'arrête rien."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([_("Tâche"), _("Progression"), _("Etat"), _("Détail"), _("Durée / reste"), ""])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        from .telechargements import colonnes_reglables
        colonnes_reglables(self.table, getattr(centre.telechargements, "params", None), "colonnes_activite", [300, 140, 100, 170, 110, 200])
        v.addWidget(self.table, 1)
        self.resume = QLabel("")
        v.addWidget(self.resume)
        bb = QDialogButtonBox()
        bb.addButton(_("Retirer les terminés"), QDialogButtonBox.ActionRole).clicked.connect(self.c.nettoyer)
        bb.addButton(_("Fermer"), QDialogButtonBox.RejectRole).clicked.connect(self.close)
        v.addWidget(bb)
        self.c.change.connect(self.remplir)
        if self.c.telechargements is not None:
            self.c.telechargements.change.connect(self.remplir)
        self.minuteur = QTimer(self)
        self.minuteur.timeout.connect(self.actualiser)
        self.minuteur.start(500)
        self.remplir()

    def _lignes(self):
        """Tâches et téléchargements fondus en une liste, les plus récents en haut."""
        out = []
        for l in self.c.lignes:
            out.append(dict(l, genre="tache"))
        if self.c.telechargements is not None:
            from . import packs_ia
            for t in self.c.telechargements.travaux:
                detail = ""
                if t["etat"] == "en_cours" and t.get("vitesse"):
                    detail = f"{packs_ia.taille_texte(t['vitesse'])}/s"
                reste = duree_texte(t.get("reste")) if t["etat"] == "en_cours" else ""
                if t["etat"] == "pause":
                    detail = _("{f} sur {t} déjà là", f=packs_ia.taille_texte(int(t["fraction"] * (t["taille"] or 0))),
                               t=packs_ia.taille_texte(t["taille"]) if t["taille"] else "?")
                out.append({"titre": _("Téléchargement : {n} ({t})", n=t["nom"], t=packs_ia.taille_texte(t["taille"]) if t["taille"] else "?"),
                            "texte": detail, "fraction": t["fraction"], "etat": t["etat"], "erreur": t.get("erreur"), "genre": "telech",
                            "cle": t["cle"], "reste": reste, "debut": t.get("debut"), "fin": None})
        return out[::-1]

    def remplir(self):
        lignes = self._lignes()
        self.table.setRowCount(len(lignes))
        self._barres = []
        for i, l in enumerate(lignes):
            self.table.setItem(i, 0, QTableWidgetItem(l["titre"]))
            b = QProgressBar()
            b.setRange(0, 1000)
            self.table.setCellWidget(i, 1, b)
            self._barres.append(b)
            for col in (2, 3, 4):
                self.table.setItem(i, col, QTableWidgetItem(""))
            if l["genre"] == "telech" and l["etat"] in (EN_COURS, ATTENTE, "pause"):
                from .telechargements import boutons_ligne
                self.table.setCellWidget(i, 5, boutons_ligne(self.c.telechargements, l))
            elif l["etat"] in (EN_COURS, ATTENTE):
                w = QWidget()
                hl = QHBoxLayout(w)
                hl.setContentsMargins(2, 0, 2, 0)
                bs = QPushButton(_("Arrêter"))
                bs.clicked.connect(lambda _c=False, l=l: self.c.arreter(l))
                hl.addWidget(bs)
                self.table.setCellWidget(i, 5, w)
            else:
                self.table.setCellWidget(i, 5, None)
                self.table.setItem(i, 5, QTableWidgetItem(""))
        self._courantes = lignes
        self.actualiser()

    def actualiser(self):
        lignes = getattr(self, "_courantes", [])
        if len(getattr(self, "_barres", [])) != len(lignes):
            return self.remplir()
        for i, l in enumerate(lignes):
            src = l
            if l["genre"] == "tache":           # données vivantes
                src = next((x for x in self.c.lignes if x.get("tache") is l.get("tache")), l)
            elif self.c.telechargements is not None:
                src = next((dict(x, texte=(f"{__import__('app.packs_ia', fromlist=['x']).taille_texte(x['vitesse'])}/s" if x.get("vitesse") and x["etat"] == "en_cours" else ""),
                                 reste=duree_texte(x.get("reste")) if x["etat"] == "en_cours" else "")
                            for x in self.c.telechargements.travaux if x["cle"] == l["cle"]), l)
            self._barres[i].setValue(int(src["fraction"] * 1000))
            etat = ETATS.get(src["etat"], src["etat"])
            if src["etat"] == EN_COURS:
                etat = f"{int(src['fraction'] * 100)} %" if src["fraction"] > 0 else _("En cours")
            self.table.item(i, 2).setText(etat)
            self.table.item(i, 3).setText((src.get("erreur") or "")[:80] if src["etat"] == ERREUR else (src.get("texte") or ""))
            if l["genre"] == "telech":
                self.table.item(i, 4).setText(src.get("reste") or "")
            else:
                d = (src.get("fin") or time.monotonic()) - (src.get("debut") or time.monotonic())
                f = src["fraction"]
                reste = _(" · reste ~{r}", r=duree_texte(d * (1 - f) / f)) if src["etat"] == EN_COURS and 0.05 < f < 1 else ""
                self.table.item(i, 4).setText(duree_texte(d) + reste)
        txt, actif = self.c.resume()
        self.resume.setText(txt)
