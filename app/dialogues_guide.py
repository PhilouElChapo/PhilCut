"""Volet « Comment faire… » (0.9.52) : guides pas à pas, à côté du film, non bloquant.

La liste des cas (ordre alphabétique, recherche), puis le guide choisi : ses étapes, chacune avec « Montrez-moi »
(PhilCut ouvre lui-même le bon menu en surlignant la bonne ligne, ou le menu du clic droit sur le plan, ou l'onglet du
volet) ; l'étape se coche toute seule quand PhilCut voit qu'elle est faite, sinon « C'est fait »."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from . import guides as G
from .langue import _


class CaseGuide(QFrame):
    """Une ligne de la liste des guides, cliquable, dont le texte passe à la ligne (un QPushButton ne le fait pas)."""

    def __init__(self, texte, action):
        super().__init__()
        self.setObjectName("caseguide")
        self.action = action
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QFrame#caseguide{border:1px solid #3a3f4b;border-radius:6px}"
                           "QFrame#caseguide:hover{border:1px solid #8b7cf6}")
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 8, 10, 8)
        self.libelle = QLabel(texte)
        self.libelle.setWordWrap(True)
        h.addWidget(self.libelle, 1)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.action()
        super().mouseReleaseEvent(e)


class DialogueGuides(QDialog):
    def __init__(self, fenetre, guide=None):
        super().__init__(fenetre)
        self.fenetre = fenetre
        self.setWindowTitle(_("Comment faire…"))
        self.setWindowFlags(Qt.Tool | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setModal(False)
        self.setMinimumWidth(360)
        self.guide, self.cases = None, []
        v = QVBoxLayout(self)
        self.haut = QHBoxLayout()
        self.b_retour = QPushButton(_("‹ Tous les guides"))
        self.b_retour.clicked.connect(self.liste)
        self.haut.addWidget(self.b_retour)
        self.haut.addStretch(1)
        v.addLayout(self.haut)
        self.cherche = QLineEdit()
        self.cherche.setPlaceholderText(_("Que voulez-vous faire ? (ex. : retirer la voix, suivre une personne)"))
        self.cherche.setClearButtonEnabled(True)
        self.cherche.textChanged.connect(self._filtrer)
        v.addWidget(self.cherche)
        self.zone = QScrollArea()
        self.zone.setWidgetResizable(True)
        self.zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.zone.setFrameShape(QFrame.NoFrame)
        v.addWidget(self.zone, 1)
        self.minuteur = QTimer(self)
        self.minuteur.setInterval(600)
        self.minuteur.timeout.connect(self._verifier)
        self._placer()
        if guide:
            self.ouvrir(guide)
        else:
            self.liste()
        self._mise_a_jour_catalogue()

    def _placer(self):
        """A droite de la fenêtre de PhilCut, sur toute sa hauteur utile."""
        f = self.fenetre
        if f is None:
            self.resize(420, 640)
            return
        g = f.frameGeometry()
        larg = 420
        h = max(480, min(g.height() - 80, 900))
        self.resize(larg, h)
        self.move(max(0, g.right() - larg - 24), g.top() + 60)

    def _editeur(self):
        f = self.fenetre
        try:
            return f.editeur_courant() if f is not None else None
        except RuntimeError:
            return None

    # ------------------------------------------------------------------ liste
    def liste(self):
        self.guide = None
        self.minuteur.stop()
        self.b_retour.hide()
        self.cherche.show()
        self._filtrer(self.cherche.text())

    def _filtrer(self, texte):
        if self.guide is not None:
            return
        gs = G.chercher(texte) if texte.strip() else G.guides()
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 4, 0)
        intro = QLabel(_("Choisissez ce que vous voulez faire : le guide vous montre chaque étape dans PhilCut, et ouvre "
                         "lui-même les bons menus."))
        intro.setWordWrap(True)
        v.addWidget(intro)
        for g in gs:
            sym, coul = G.ETATS.get(g["etat"], ("", ""))
            nouveau = g.get("catalogue") and g["id"] not in (self._vus() or [])
            badge = f"&nbsp; <span style='color:#8b7cf6;font-weight:600'>{_('Nouveau')}</span>" if nouveau else ""
            b = CaseGuide(f"<span style='color:{coul}'>{sym}</span>&nbsp; {g['titre']}{badge}",
                          lambda g_=g: self.ouvrir(g_))           # le titre passe à la ligne : jamais coupé
            b.setToolTip(G.libelle_etat(g["etat"]) + "\n\n" + g["intro"])
            v.addWidget(b)
        if not gs:
            rien = QLabel(_("Aucun guide pour « {t} » pour l'instant. Essayez d'autres mots, ou écrivez votre demande dans le "
                            "bouton IA (Dites-le en clair).", t=texte))
            rien.setWordWrap(True)
            v.addWidget(rien)
        leg = QLabel("  ".join(f"{G.ETATS[k][0]} {G.libelle_etat(k)}" for k in ("ok", "partiel", "a_venir")))
        leg.setWordWrap(True)
        leg.setStyleSheet("color:#9aa4b2")
        v.addWidget(leg)
        v.addStretch(1)
        self.zone.setWidget(w)

    def _params(self):
        return getattr(self.fenetre, "params", None)

    def _vus(self):
        p = self._params()
        return list(p.get("guides_vus") or []) if p is not None else []

    def _mise_a_jour_catalogue(self):
        """Les guides du catalogue en ligne, relus en arrière-plan (jamais bloquant) ; la liste se refait s'ils ont changé."""
        import os, threading
        p = self._params()
        if os.environ.get("PHILCUT_SANS_RESEAU") or (p is not None and not p.get("effets_en_ligne", True)):
            return
        from . import catalogue_ligne as CL
        avant = [g["id"] for g in G.guides()]
        fil = threading.Thread(target=lambda: CL.telecharger("guides.json", 8), daemon=True)
        fil.start()

        def apres():
            if fil.is_alive():
                QTimer.singleShot(800, apres)
            elif self.guide is None and [g["id"] for g in G.guides()] != avant:
                self._filtrer(self.cherche.text())
        QTimer.singleShot(800, apres)

    # ------------------------------------------------------------------ un guide
    def ouvrir(self, g):
        if isinstance(g, str):
            g = next((x for x in G.guides() if x["id"] == g), None)
            if g is None:
                return self.liste()
        self.guide = g
        p = self._params()
        if g.get("catalogue") and p is not None and g["id"] not in self._vus():
            p["guides_vus"] = self._vus() + [g["id"]]
        self.b_retour.show()
        self.cherche.hide()
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 4, 0)
        t = QLabel(f"<b>{g['titre']}</b>")
        t.setWordWrap(True)
        t.setStyleSheet("font-size:15px")
        v.addWidget(t)
        sym, coul = G.ETATS.get(g["etat"], ("", "#9aa4b2"))
        et = QLabel(f"{sym} {G.libelle_etat(g['etat'])}")
        et.setStyleSheet(f"color:{coul};font-weight:600")
        v.addWidget(et)
        intro = QLabel(g["intro"])
        intro.setWordWrap(True)
        v.addWidget(intro)
        self.cases = []
        for i, e in enumerate(g["etapes"], 1):
            cadre = QFrame()
            cadre.setObjectName("etape")
            vc = QVBoxLayout(cadre)
            case = QCheckBox(_("Etape {n}", n=i))
            case.setStyleSheet("font-weight:600")
            vc.addWidget(case)
            lb = QLabel(e["texte"])
            lb.setWordWrap(True)
            lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
            vc.addWidget(lb)
            hb = QHBoxLayout()
            if e.get("montrer"):
                bm = QPushButton(_("Montrez-moi"))
                bm.setToolTip(_("PhilCut ouvre lui-même le bon menu et surligne la ligne : il ne reste qu'à cliquer"))
                bm.setStyleSheet("font-weight:600")
                bm.clicked.connect(lambda _c=False, e_=e: self._montrer(e_))
                hb.addWidget(bm)
            if not e.get("fait"):
                case.setToolTip(_("Cochez quand c'est fait"))
            else:
                case.setToolTip(_("Se coche toute seule quand PhilCut voit que c'est fait"))
            hb.addStretch(1)
            vc.addLayout(hb)
            v.addWidget(cadre)
            self.cases.append((case, e, cadre))
            case.toggled.connect(self._suivante)
        self.fin = QLabel("")
        self.fin.setWordWrap(True)
        v.addWidget(self.fin)
        v.addStretch(1)
        self.zone.setWidget(w)
        self._suivante()
        self.minuteur.start()
        self.show()
        self.raise_()

    def _montrer(self, e):
        ed = self._editeur()
        ok = G.montrer(self.fenetre, ed, e.get("montrer"))
        if not ok:
            if e.get("montrer", {}).get("clic_droit") is not None:
                self.fin.setText(_("Mettez d'abord un plan vidéo dans la timeline : le menu du clic droit s'ouvre sur lui."))
            else:
                self.fin.setText(_("Je n'ai pas trouvé ce menu : ouvrez-le à la main en suivant le texte de l'étape."))

    def _verifier(self):
        if self.guide is None or not self.isVisible():
            return
        ed = self._editeur()
        for case, e, _c in self.cases:
            if e.get("fait") and not case.isChecked() and G.est_fait(e["fait"], ed):
                case.setChecked(True)

    def _suivante(self, *_a):
        """L'étape à faire est encadrée ; les étapes faites s'estompent."""
        courante = None
        for case, e, cadre in self.cases:
            if case.isChecked():
                cadre.setStyleSheet("QFrame#etape{border:1px solid #3a3f4b;border-radius:6px} QLabel{color:#8a94a6}")
            elif courante is None:
                courante = cadre
                cadre.setStyleSheet("QFrame#etape{border:2px solid #8b7cf6;border-radius:6px}")
            else:
                cadre.setStyleSheet("QFrame#etape{border:1px solid #3a3f4b;border-radius:6px}")
        if self.cases and courante is None:
            self.fin.setText(_("✓ Toutes les étapes sont faites."))
        elif hasattr(self, "fin"):
            self.fin.setText("")

    def closeEvent(self, ev):
        self.minuteur.stop()
        super().closeEvent(ev)


def ouvrir_guides(fenetre, guide=None):
    """Une seule fenêtre de guides par fenêtre de PhilCut."""
    d = getattr(fenetre, "_guides", None)
    try:
        if d is not None and d.isVisible() is not None:
            if guide:
                d.ouvrir(guide)
            d.show()
            d.raise_()
            d.activateWindow()
            return d
    except RuntimeError:
        pass
    d = DialogueGuides(fenetre, guide)
    fenetre._guides = d
    d.show()
    return d
