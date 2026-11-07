"""Fenêtre « Vignette et image fixe » (0.9.3) : on entoure des zones de couleur sur une image du film, PhilCut
compose une vignette propre (kit de style cohérent), l'IA peut proposer titre, éléments et style.

Résultat : miniature YouTube de l'export, image enregistrée, ou image fixe posée dans le film (piste du dessus), que l'on
rouvre et modifie (clic droit sur le plan › « Modifier l'image composée… »)."""
import copy
import os
import time

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSlider, QVBoxLayout,
                               QWidget, QToolButton)

from . import vignette as V
from .langue import _
from .taches import Tache


def _dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "vignettes")
    os.makedirs(d, exist_ok=True)
    return d


class Toile(QWidget):
    """L'image composée, avec les zones tracées par-dessus ; on trace à la souris (lasso ou rectangle)."""
    zones_changees = Signal()

    def __init__(self, recette):
        super().__init__()
        self.recette = recette
        self.image = None
        self.couleur = "rouge"
        self.mode = "lasso"
        self.montrer = True
        self._trace = []
        self.setMinimumSize(480, 270)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    def cadre(self):
        """Rectangle où l'image est dessinée (proportions gardées)."""
        if self.image is None or self.image.isNull():
            return QRectF(0, 0, self.width(), self.height())
        k = min(self.width() / self.image.width(), self.height() / self.image.height())
        w, h = self.image.width() * k, self.image.height() * k
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def _norm(self, pos):
        r = self.cadre()
        return [min(1.0, max(0.0, (pos.x() - r.left()) / r.width())), min(1.0, max(0.0, (pos.y() - r.top()) / r.height()))]

    def _ecran(self, pt):
        r = self.cadre()
        return QPointF(r.left() + pt[0] * r.width(), r.top() + pt[1] * r.height())

    def zone_sous(self, pos):
        x, y = self._norm(pos)
        for i in range(len(self.recette["zones"]) - 1, -1, -1):
            poly = QPolygonF([QPointF(*p) for p in self.recette["zones"][i]["points"]])
            if poly.containsPoint(QPointF(x, y), Qt.OddEvenFill):
                return i
        return None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._trace = [self._norm(e.position())]
            self.update()

    def mouseMoveEvent(self, e):
        if self._trace:
            pt = self._norm(e.position())
            if self.mode == "rectangle":
                self._trace = [self._trace[0], pt]
            elif abs(pt[0] - self._trace[-1][0]) + abs(pt[1] - self._trace[-1][1]) > 0.004:
                self._trace.append(pt)
            self.update()
        else:
            i = self.zone_sous(e.position())
            self.setToolTip(_("Zone {c} : clic droit pour la supprimer ou changer sa couleur", c=self.recette["zones"][i]["couleur"]) if i is not None
                            else _("Tracez à la souris : la couleur choisie à gauche dit le rôle de la zone"))

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or not self._trace:
            return
        t = self._trace
        self._trace = []
        if self.mode == "rectangle" and len(t) == 2:
            (x0, y0), (x1, y1) = t
            t = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
        xs, ys = [p[0] for p in t], [p[1] for p in t]
        if len(t) >= 3 and max(xs) - min(xs) > 0.015 and max(ys) - min(ys) > 0.015:
            if len(t) > 80:                                  # tracé allégé
                pas = len(t) / 80
                t = [t[int(i * pas)] for i in range(80)]
            self.recette["zones"].append({"couleur": self.couleur, "points": [[round(x, 4), round(y, 4)] for x, y in t]})
            self.zones_changees.emit()
        self.update()

    def _menu(self, pos):
        i = self.zone_sous(pos)
        if i is None:
            return
        m = QMenu(self)
        m.addAction(_("Supprimer cette zone"), lambda: self._supprimer(i))
        sm = m.addMenu(_("Changer sa couleur"))
        for c, (_h, lib, _a) in V.COULEURS_ZONES.items():
            sm.addAction(lib, lambda c=c: self._recolorer(i, c))
        m.exec(self.mapToGlobal(pos))

    def _supprimer(self, i):
        del self.recette["zones"][i]
        self.zones_changees.emit()
        self.update()

    def _recolorer(self, i, c):
        self.recette["zones"][i]["couleur"] = c
        self.zones_changees.emit()
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#101010"))
        r = self.cadre()
        if self.image is not None and not self.image.isNull():
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawImage(r, self.image)
        else:
            p.setPen(QColor("#9aa4b2"))
            p.drawText(self.rect(), Qt.AlignCenter, _("Préparation de l'image du film…"))
        p.setRenderHint(QPainter.Antialiasing)
        zs = list(self.recette["zones"]) if self.montrer else []
        if self._trace:
            t = self._trace
            if self.mode == "rectangle" and len(t) == 2:
                (x0, y0), (x1, y1) = t
                t = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
            zs.append({"couleur": self.couleur, "points": t, "en_cours": True})
        for z in zs:
            col = QColor(V.COULEURS_ZONES.get(z["couleur"], ("#ffffff", ""))[0])
            chemin = QPainterPath()
            for j, pt in enumerate(z["points"]):
                (chemin.moveTo if j == 0 else chemin.lineTo)(self._ecran(pt))
            if not z.get("en_cours"):
                chemin.closeSubpath()
            remp = QColor(col)
            remp.setAlpha(40)
            p.fillPath(chemin, remp)
            p.setPen(QPen(col, 2, Qt.DashLine if not z.get("en_cours") else Qt.SolidLine))
            p.drawPath(chemin)


class DialogueVignette(QDialog):
    def __init__(self, ed, recette=None, usage="vignette"):
        super().__init__(ed)
        self.ed = ed
        self.params = getattr(ed, "params", None) or {}
        self.usage = usage
        self.recette = copy.deepcopy(recette) if recette else V.nouvelle_recette("youtube" if usage == "vignette" else "projet")
        if not recette:
            self.recette["source_t"] = round(getattr(getattr(ed, "timeline", None), "position", 0.0) or 0.0, 3)
            if usage == "image":
                self.recette["nom"] = _("Image fixe")
        self.resultat = None          # QImage composée
        self.infos = {}
        self._images = {}              # instant -> image BGR du film
        self._gen = 0
        self.tache = None
        self.setWindowTitle(_("Vignette et image fixe composées"))
        self.resize(1360, 860)
        racine = QVBoxLayout(self)
        corps = QHBoxLayout()
        racine.addLayout(corps, 1)
        # ---- colonne de gauche : réglages (défile)
        zg = QScrollArea()
        zg.setWidgetResizable(True)
        zg.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        zg.setMinimumWidth(420)
        gauche = QWidget()
        vg = QVBoxLayout(gauche)
        zg.setWidget(gauche)
        corps.addWidget(zg)
        projet = getattr(ed, "projet", None)
        duree = max(0.1, float(projet.duree() if projet is not None else 0.1))
        g1 = QGroupBox(_("Image du film"))
        f1 = QFormLayout(g1)
        self.format = QComboBox()
        for k, (lib, _l, _h) in V.FORMATS.items():
            self.format.addItem(lib, k)
        self.format.setCurrentIndex(max(0, self.format.findData(self.recette.get("format"))))
        self.format.currentIndexChanged.connect(lambda: self._regle("format", self.format.currentData()))
        f1.addRow(_("Format"), self.format)
        self.temps, self.lbl_t = self._curseur_temps(duree, self.recette.get("source_t") or 0.0, "source_t")
        bt = QPushButton(_("Prendre la tête de lecture"))
        bt.setToolTip(_("Prendre l'image à la tête de lecture de la timeline"))
        bt.clicked.connect(lambda: self.temps.setValue(int(round(getattr(ed.timeline, "position", 0.0) * 10))))
        h = QHBoxLayout()
        h.addWidget(self.temps, 1)
        h.addWidget(self.lbl_t)
        f1.addRow(_("Instant"), h)
        f1.addRow("", bt)
        self.cadrage = QSlider(Qt.Horizontal)
        self.cadrage.setRange(0, 100)
        self.cadrage.setValue(int(self.recette.get("cadrage", 0.5) * 100))
        self.cadrage.setToolTip(_("Quelle partie de l'image garder quand le format ne correspond pas (gauche, centre, droite)"))
        self.cadrage.valueChanged.connect(lambda v: self._regle("cadrage", v / 100))
        f1.addRow(_("Cadrage"), self.cadrage)
        self.avant_apres = QCheckBox(_("Avant / après (image coupée en diagonale)"))
        self.avant_apres.setChecked(bool(self.recette.get("avant_apres")))
        self.avant_apres.toggled.connect(self._avant_apres)
        f1.addRow(self.avant_apres)
        t2 = self.recette.get("source2_t")
        self.temps2, self.lbl_t2 = self._curseur_temps(duree, duree * 0.9 if t2 is None else t2, "source2_t")
        h2 = QHBoxLayout()
        h2.addWidget(self.temps2, 1)
        h2.addWidget(self.lbl_t2)
        self.lig_apres = QWidget()
        self.lig_apres.setLayout(h2)
        f1.addRow(_("Image « après »"), self.lig_apres)
        self._f1 = f1
        f1.setRowVisible(self.lig_apres, self.avant_apres.isChecked())
        vg.addWidget(g1)
        g2 = QGroupBox(_("Zones : entourez à la souris sur l'image"))
        v2 = QVBoxLayout(g2)
        self.groupe_couleurs = QButtonGroup(self)
        grille = QHBoxLayout()
        col1, col2 = QVBoxLayout(), QVBoxLayout()
        grille.addLayout(col1)
        grille.addLayout(col2)
        for i, (c, (hexa, lib, aide)) in enumerate(V.COULEURS_ZONES.items()):
            b = QToolButton()
            b.setCheckable(True)
            b.setText(lib)
            b.setToolTip(aide)
            pm = QPixmap(14, 14)
            pm.fill(QColor(hexa))
            from PySide6.QtGui import QIcon
            b.setIcon(QIcon(pm))
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            b.setStyleSheet("QToolButton{padding:4px 8px;text-align:left} QToolButton:checked{font-weight:600}")
            from PySide6.QtWidgets import QSizePolicy
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.clicked.connect(lambda _c=False, c=c: setattr(self.toile, "couleur", c))
            self.groupe_couleurs.addButton(b)
            (col1 if i % 2 == 0 else col2).addWidget(b)
            if c == "rouge":
                b.setChecked(True)
        col2.addStretch(1)
        v2.addLayout(grille)
        self.aide_zone = QLabel(V.COULEURS_ZONES["rouge"][2])
        self.aide_zone.setWordWrap(True)
        self.aide_zone.setStyleSheet("color:#9aa4b2")
        self.groupe_couleurs.buttonClicked.connect(lambda b: self.aide_zone.setText(b.toolTip()))
        v2.addWidget(self.aide_zone)
        hm = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem(_("Tracer à main levée"), "lasso")
        self.mode.addItem(_("Tracer un rectangle"), "rectangle")
        self.mode.currentIndexChanged.connect(lambda: setattr(self.toile, "mode", self.mode.currentData()))
        hm.addWidget(self.mode, 1)
        be = QPushButton(_("Effacer les zones"))
        be.clicked.connect(self._effacer_zones)
        hm.addWidget(be)
        v2.addLayout(hm)
        self.voir_zones = QCheckBox(_("Montrer les zones sur l'image"))
        self.voir_zones.setChecked(True)
        self.voir_zones.toggled.connect(lambda on: (setattr(self.toile, "montrer", on), self.toile.update()))
        v2.addWidget(self.voir_zones)
        vg.addWidget(g2)
        g3 = QGroupBox(_("Phrase pour l'IA (facultatif)"))
        v3 = QVBoxLayout(g3)
        self.prompt_id = QComboBox()
        for k, (lib, _t) in V.PROMPTS.items():
            self.prompt_id.addItem(lib, k)
        self.prompt_id.setCurrentIndex(max(0, self.prompt_id.findData(self.recette.get("prompt_id"))))
        self.prompt_id.currentIndexChanged.connect(self._prompt_choisi)
        v3.addWidget(self.prompt_id)
        self.prompt = QPlainTextEdit(self.recette.get("prompt") or "")
        self.prompt.setMaximumHeight(90)
        self.prompt.setToolTip(_("Modifiable : précisez le sujet et ce que la zone verte doit montrer (ex. « pistons, soupapes, arbre à cames »)."))
        self.prompt.textChanged.connect(lambda: self.recette.__setitem__("prompt", self.prompt.toPlainText()))
        v3.addWidget(self.prompt)
        hi = QVBoxLayout()
        self.niveau = QComboBox()
        self.niveau.addItem(_("IA locale (sur ce poste, gratuite)"), "locale")
        self.niveau.addItem(_("IA cloud (Claude / Gemini, votre clef)"), "cloud")
        self.niveau.setCurrentIndex(0 if (self.params.get("assistant_niveau") or "") == "locale" else 1)
        hi.addWidget(self.niveau)
        self.b_ia = QPushButton(_("Proposer par l'IA"))
        self.b_ia.setToolTip(_("L'IA regarde l'image et vos zones, puis propose le titre, les éléments et le style. Rien n'est envoyé sans ce clic."))
        self.b_ia.clicked.connect(self.proposer_ia)
        hi.addWidget(self.b_ia)
        v3.addLayout(hi)
        vg.addWidget(g3)
        g4 = QGroupBox(_("Contenu"))
        f4 = QFormLayout(g4)
        self.titre = QLineEdit(self.recette.get("titre") or "")
        self.titre.setPlaceholderText(_("Titre court (3 à 5 mots)"))
        self.titre.textChanged.connect(lambda t: self._regle("titre", t))
        f4.addRow(_("Titre (zone bleue)"), self.titre)
        self.accent = QLineEdit(self.recette.get("accent_mots") or "")
        self.accent.setPlaceholderText(_("Mot(s) du titre en couleur"))
        self.accent.textChanged.connect(lambda t: self._regle("accent_mots", t))
        f4.addRow(_("Mots en couleur"), self.accent)
        self.elements = QPlainTextEdit(self.recette.get("elements") or "")
        self.elements.setPlaceholderText(_("Un élément par ligne, suivi de ✓ (validé), ✗ (non) ou rien. Ex. : Pistons ✓"))
        self.elements.setMaximumHeight(96)
        self.elements.textChanged.connect(lambda: self._regle("elements", self.elements.toPlainText()))
        f4.addRow(_("Éléments (zone verte)"), self.elements)
        vg.addWidget(g4)
        g5 = QGroupBox(_("Style"))
        f5 = QFormLayout(g5)
        self.kit = self._combo(V.KITS, "kit", lambda k: k["nom"])
        f5.addRow(_("Kit"), self.kit)
        self.effet = self._combo(V.EFFETS_ROUGE, "effet_rouge")
        f5.addRow(_("Zone rouge"), self.effet)
        self.fleche = self._combo(V.FLECHES, "fleche")
        f5.addRow(_("Zone jaune"), self.fleche)
        vg.addWidget(g5)
        vg.addStretch(1)
        # ---- centre : l'image, puis les variantes
        vc = QVBoxLayout()
        self.toile = Toile(self.recette)
        self.toile.zones_changees.connect(self.recomposer)
        vc.addWidget(self.toile, 1)
        hv = QHBoxLayout()
        bv = QPushButton(_("Proposer 3 variantes"))
        bv.setToolTip(_("Autre couleur d'accent et côté de la flèche, puis deux autres kits : cliquez celle qui vous plaît"))
        bv.clicked.connect(self.variantes)
        hv.addWidget(bv)
        self.vues_var = []
        for i in range(3):
            lb = QPushButton()
            lb.setFixedSize(192, 108)
            lb.setIconSize(lb.size())
            lb.setFlat(True)
            lb.setToolTip(_("Choisir cette variante"))
            lb.clicked.connect(lambda _c=False, i=i: self._prendre_variante(i))
            lb.hide()
            self.vues_var.append(lb)
            hv.addWidget(lb)
        hv.addStretch(1)
        vc.addLayout(hv)
        corps.addLayout(vc, 1)
        # ---- droite : taille téléphone et lisibilité
        vd = QVBoxLayout()
        vd.addWidget(QLabel(_("En taille téléphone")))
        self.petite = QLabel()
        self.petite.setFixedSize(176, 176)
        self.petite.setAlignment(Qt.AlignCenter)
        self.petite.setStyleSheet("background:#0f0f0f;border-radius:6px")
        vd.addWidget(self.petite)
        self.lisib = QLabel("")
        self.lisib.setWordWrap(True)
        self.lisib.setFixedWidth(176)
        vd.addWidget(self.lisib)
        vd.addStretch(1)
        corps.addLayout(vd)
        # ---- bas : ce qui se passe, et les actions
        self.etat = QLabel("")
        self.etat.setWordWrap(True)
        self.etat.setStyleSheet("color:#9aa4b2")
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        self.barre.setMaximumHeight(14)
        self.barre.setTextVisible(False)
        self.barre.hide()
        racine.addWidget(self.barre)
        racine.addWidget(self.etat)
        hb = QHBoxLayout()
        b1 = QPushButton(_("Enregistrer l'image…"))
        b1.clicked.connect(self.enregistrer_sous)
        hb.addWidget(b1)
        b2 = QPushButton(_("Miniature YouTube de l'export"))
        b2.setToolTip(_("A l'export, cette image est intégrée au MP4 et enregistrée à côté en JPG pour YouTube"))
        b2.clicked.connect(self.miniature)
        hb.addWidget(b2)
        hb.addStretch(1)
        hb.addWidget(QLabel(_("Durée dans le film")))
        self.duree_pose = QDoubleSpinBox()
        self.duree_pose.setRange(0.5, 60)
        self.duree_pose.setValue(float(self.recette.get("duree_pose", 6.0)))
        self.duree_pose.setSuffix(" s")
        hb.addWidget(self.duree_pose)
        self.b_poser = QPushButton(_("Poser dans le film (au-dessus, à la tête de lecture)"))
        self.b_poser.setStyleSheet("font-weight:600;padding:6px 14px")
        self.b_poser.clicked.connect(self.poser)
        hb.addWidget(self.b_poser)
        bf = QPushButton(_("Fermer"))
        bf.clicked.connect(self.reject)
        hb.addWidget(bf)
        racine.addLayout(hb)
        self._delai = QTimer(self)
        self._delai.setSingleShot(True)
        self._delai.setInterval(250)
        self._delai.timeout.connect(self._lancer)
        self._t0 = 0.0
        self.recomposer()
        if not self.recette["zones"]:
            self.etat.setText(_("Entourez sur l'image : en rouge ce qu'il faut montrer, en bleu la place du titre, en jaune ce qu'il faut "
                                "désigner, en vert les éléments à lister. Clic droit sur une zone pour la supprimer."))

    # ---- petits constructeurs
    def _curseur_temps(self, duree, valeur, cle):
        s = QSlider(Qt.Horizontal)
        s.setRange(0, int(duree * 10))
        s.setValue(int(round(valeur * 10)))
        lb = QLabel(f"{valeur:.1f} s")
        lb.setMinimumWidth(54)

        def change(v):
            lb.setText(f"{v / 10:.1f} s")
            self._regle(cle, v / 10)
        s.valueChanged.connect(change)
        return s, lb

    def _combo(self, dico, cle, libelle=lambda v: v):
        c = QComboBox()
        for k, v in dico.items():
            c.addItem(libelle(v), k)
        c.setCurrentIndex(max(0, c.findData(self.recette.get(cle))))
        c.currentIndexChanged.connect(lambda: self._regle(cle, c.currentData()))
        return c

    def _regle(self, cle, valeur):
        self.recette[cle] = valeur
        self.recomposer()

    def _avant_apres(self, on):
        self._f1.setRowVisible(self.lig_apres, on)
        self._regle("avant_apres", on)

    def _prompt_choisi(self):
        k = self.prompt_id.currentData()
        self.recette["prompt_id"] = k
        self.prompt.setPlainText(V.PROMPTS[k][1])
        if k == "avant_apres" and not self.avant_apres.isChecked():
            self.avant_apres.setChecked(True)

    def _effacer_zones(self):
        self.recette["zones"].clear()
        self.toile.update()
        self.recomposer()

    # ---- composition en tâche de fond
    def recomposer(self):
        self._delai.start()

    def _image(self, t):
        cle = round(float(t or 0), 1)
        if cle not in self._images:
            img = V.image_du_film(self.ed.projet, cle, 1920)
            if img is None:
                raise RuntimeError(_("Pas d'image du film à {t} s : placez l'instant sur un plan vidéo.", t=cle))
            self._images[cle] = img
        return self._images[cle]

    def _lancer(self):
        if self.tache is not None and self.tache.isRunning():
            self._delai.start()                   # on recompose dès que le calcul en cours est fini
            return
        self._gen += 1
        gen = self._gen
        rec = copy.deepcopy(self.recette)
        L, H = V.taille_sortie(rec, getattr(self.ed, "projet", None))

        def travail(t):
            t.avancer(0.0, _("Image du film à {s} s…", s=round(rec.get("source_t") or 0, 1)))
            img = self._image(rec.get("source_t"))
            img2 = self._image(rec.get("source2_t") or 0) if rec.get("avant_apres") else None
            return V.composer(rec, img, img2, L, H, progression=t.avancer)
        self.tache = Tache(travail, _("Vignette"))
        self.tache.progression.connect(self._progression, Qt.QueuedConnection)
        self.tache.fini.connect(lambda r, e, gen=gen: self._compose(gen, r, e), Qt.QueuedConnection)
        self._t0 = time.monotonic()
        self.tache.start()

    def _progression(self, f, texte):
        if time.monotonic() - self._t0 > 0.4:          # rien ne clignote pour un calcul instantané
            self.barre.show()
        self.barre.setValue(int(f * 1000))
        if texte:
            self.etat.setText(texte)

    def _compose(self, gen, r, err):
        self.barre.hide()
        if err:
            self.etat.setText(_("✕ {e}", e=str(err)[:300]))
            return
        if gen != self._gen:
            return
        self.resultat, self.infos = r
        self.toile.image = self.resultat
        self.toile.update()
        pm = QPixmap.fromImage(self.resultat).scaled(168, 168, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.petite.setPixmap(pm)
        av = self.infos.get("avertissements") or []
        self.lisib.setText("<br>".join("⚠ " + a for a in av) if av else _("✓ Lisible en petit."))
        self.lisib.setStyleSheet("color:#e0a040" if av else "color:#30d158")
        if self.recette["zones"]:
            self.etat.setText(_("Vignette à jour ({s:.1f} s de calcul). Tout reste modifiable : zones, texte, style.", s=time.monotonic() - self._t0))

    # ---- IA
    def proposer_ia(self):
        if self.resultat is None:
            return
        from PySide6.QtCore import QBuffer, QIODevice
        img = self._images.get(round(float(self.recette.get("source_t") or 0), 1))
        if img is None:
            return
        import cv2
        ok, png = cv2.imencode(".png", cv2.resize(img, (768, int(768 * img.shape[0] / img.shape[1]))))
        rec = copy.deepcopy(self.recette)
        niveau = self.niveau.currentData()
        params = self.params
        t = Tache(lambda tache: V.proposer_ia(rec, png.tobytes(), params, niveau, rapporter=lambda x: tache.avancer(0.5, x)), _("Vignette : IA"))
        self.tache_ia = t
        if hasattr(self.ed, "taches"):
            self.ed.taches.append(t)
        if hasattr(self.ed, "encart"):
            self.ed.encart.suivre(t, _("Vignette : propositions de l'IA"))
        self.b_ia.setEnabled(False)
        self.barre.show()
        self.barre.setRange(0, 0)                      # durée inconnue : barre animée, et le temps écoulé
        t0 = time.monotonic()
        horloge = QTimer(self)
        horloge.setInterval(1000)
        texte = {"v": _("Envoi à l'IA…")}

        def tic():
            e = int(time.monotonic() - t0)
            self.etat.setText(f"{texte['v']}  ({e // 60}:{e % 60:02d})")
        horloge.timeout.connect(tic)
        horloge.start()
        t.progression.connect(lambda f, x: (texte.__setitem__("v", x or texte["v"]), tic()), Qt.QueuedConnection)

        def fin(r, err):
            horloge.stop()
            self.barre.setRange(0, 1000)
            self.barre.hide()
            self.b_ia.setEnabled(True)
            if err:
                self.etat.setText(_("✕ L'IA n'a pas répondu : {e}", e=str(err)[:300]))
                return
            for cle, champ in (("titre", self.titre), ("accent_mots", self.accent)):
                if r.get(cle):
                    champ.setText(r[cle])
            if r.get("elements"):
                self.elements.setPlainText(r["elements"])
            for cle, combo in (("kit", self.kit), ("effet_rouge", self.effet), ("fleche", self.fleche)):
                if r.get(cle):
                    combo.setCurrentIndex(max(0, combo.findData(r[cle])))
            self.etat.setText(_("Proposition de l'IA appliquée : {p}", p=r.get("pourquoi") or _("modifiez ce que vous voulez.")))
        t.fini.connect(fin, Qt.QueuedConnection)
        t.start()

    # ---- variantes
    def variantes(self):
        if self.resultat is None:
            return
        self._vars = V.variantes(self.recette)
        L, H = V.taille_sortie(self.recette, getattr(self.ed, "projet", None))
        rec = copy.deepcopy(self._vars)
        img = self._image(self.recette.get("source_t"))
        img2 = self._image(self.recette.get("source2_t") or 0) if self.recette.get("avant_apres") else None
        k = 640 / max(L, H)

        def travail(t):
            out = []
            for i, r in enumerate(rec):
                t.avancer(i / len(rec), _("Variante {i}/{n} : kit « {k} »…", i=i + 1, n=len(rec), k=V.KITS[r["kit"]]["nom"]))
                out.append(V.composer(r, img, img2, int(L * k), int(H * k))[0])
            return out
        t = Tache(travail, _("Variantes"))
        t.progression.connect(self._progression, Qt.QueuedConnection)
        t.fini.connect(self._variantes_pretes, Qt.QueuedConnection)
        self.tache_var = t
        self._t0 = time.monotonic()
        t.start()

    def _variantes_pretes(self, images, err):
        self.barre.hide()
        if err:
            self.etat.setText(_("✕ {e}", e=str(err)[:300]))
            return
        for lb, q in zip(self.vues_var, images):
            pm = QPixmap.fromImage(q).scaled(lb.width(), lb.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            from PySide6.QtGui import QIcon
            lb.setIcon(QIcon(pm))
            lb.show()
        self.etat.setText(_("Trois variantes : cliquez celle qui vous plaît, elle devient la vignette (toujours modifiable)."))

    def _prendre_variante(self, i):
        r = self._vars[i]
        self.recette["graine"] = r["graine"]
        self.kit.setCurrentIndex(max(0, self.kit.findData(r["kit"])))
        self.recomposer()

    # ---- résultats
    def _garder_recette(self):
        """La recette est gardée dans le projet : la vignette se rouvre et se modifie."""
        p = getattr(self.ed, "projet", None)
        if p is None:
            return
        self.recette["duree_pose"] = self.duree_pose.value()
        liste = p.d.setdefault("vignettes", [])
        for i, r in enumerate(liste):
            if r.get("id") == self.recette["id"]:
                liste[i] = copy.deepcopy(self.recette)
                break
        else:
            liste.append(copy.deepcopy(self.recette))
        p.modifie = True

    def _fichier(self, ext="png"):
        return os.path.join(_dossier(), f"{self.recette['id']}_{time.strftime('%Y%m%d_%H%M%S')}.{ext}")

    def enregistrer_sous(self):
        if self.resultat is None:
            return
        from .session import dossier_systeme
        d = self.params.get("dossier_images") or dossier_systeme("images")
        chemin, _f = QFileDialog.getSaveFileName(self, _("Enregistrer l'image"), os.path.join(d, "vignette.jpg"), "JPEG (*.jpg);;PNG (*.png)")
        if not chemin:
            return
        if hasattr(self.params, "enregistrer"):
            self.params["dossier_images"] = os.path.dirname(chemin)
            self.params.enregistrer()
        V.enregistrer(self.resultat, chemin)
        self._garder_recette()
        self.etat.setText(_("Image enregistrée : {c}", c=chemin))

    def miniature(self):
        if self.resultat is None:
            return
        chemin = self._fichier("jpg")
        V.enregistrer(self.resultat, chemin)
        self.ed.projet.marquer()
        self.ed.projet.d["vignette_image"] = chemin
        self._garder_recette()
        self.etat.setText(_("Miniature choisie : à l'export, elle est intégrée au MP4 et enregistrée à côté en JPG pour YouTube."))

    def poser(self):
        if self.resultat is None:
            return
        chemin = self._fichier("png")
        V.enregistrer(self.resultat, chemin)
        self._garder_recette()
        ed = self.ed
        ancien = getattr(self, "clip_a_remplacer", None)
        if ancien is not None and ed.projet.clip(ancien):
            c0 = ed.projet.clip(ancien)
            t, duree = c0["debut"], self.duree_pose.value()
            ed.projet.marquer()
            ed.projet.retirer_clip(ancien, refermer=False)
        else:
            t, duree = ed.timeline.position, self.duree_pose.value()
        c = ed.poser_au_dessus(chemin, t, self.recette.get("nom") or _("Image composée"), duree)
        if c:
            c["vignette"] = self.recette["id"]
            self.clip_a_remplacer = c["id"]
        ed.rafraichir()
        self.etat.setText(_("Image posée dans le film à {t} s pour {d} s, au-dessus du film (piste Vidéo 2). Clic droit sur le plan › « Modifier "
                            "l'image composée… » pour la retoucher.", t=round(t, 1), d=duree))

    def done(self, r):
        if self.recette.get("zones") or self.recette.get("titre"):
            self._garder_recette()
        super().done(r)
