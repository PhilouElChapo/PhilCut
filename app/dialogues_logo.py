"""Atelier de logo (Fabrique › Créer un logo) : gabarits, textes et formes déplaçables à la souris, propriétés à droite,
idées proposées par Claude ou Gemini (logos éditables), image dessinée par Gemini, puis enregistrement (PNG transparent
+ fichier modifiable) et animation par la Fabrique."""
import os

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QImage
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel, QLineEdit, QComboBox,
                               QDoubleSpinBox, QSpinBox, QFormLayout, QWidget, QColorDialog, QFileDialog, QMenu, QMessageBox, QPlainTextEdit,
                               QCheckBox, QFontComboBox, QSizePolicy, QInputDialog)

from . import logo as LG
from .langue import _
from .taches import Tache


class _Toile(QWidget):
    """Le logo, centré sur un damier (transparence) ; clic = sélection, glisser = déplacer, molette = taille."""
    selection = Signal(int)
    modifie = Signal()

    def __init__(self, editeur):
        super().__init__()
        self.ed = editeur
        self.setMinimumSize(420, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._prise = None

    def _zone(self):
        lg = self.ed.logo
        L, H = lg["largeur"], lg["hauteur"]
        e = min((self.width() - 20) / L, (self.height() - 20) / H)
        return (self.width() - L * e) / 2, (self.height() - H * e) / 2, e

    def _vers_logo(self, p):
        x0, y0, e = self._zone()
        return (p.x() - x0) / e, (p.y() - y0) / e

    def paintEvent(self, ev):
        p = QPainter(self)
        x0, y0, e = self._zone()
        L, H = self.ed.logo["largeur"], self.ed.logo["hauteur"]
        cote = 14
        for i in range(int(L * e / cote) + 1):              # damier : la transparence se voit
            for j in range(int(H * e / cote) + 1):
                p.fillRect(QRectF(x0 + i * cote, y0 + j * cote, cote, cote), QColor("#3a3a44") if (i + j) % 2 else QColor("#4a4a55"))
        img = LG.rendre(self.ed.logo, int(L * e), selection=self.ed.courant)
        p.drawImage(QPointF(x0, y0), img)
        p.end()

    def mousePressEvent(self, ev):
        x, y = self._vers_logo(ev.position())
        i = LG.element_sous(self.ed.logo, x, y)
        self.selection.emit(-1 if i is None else i)
        if i is not None:
            el = self.ed.logo["elements"][i]
            self._prise = (x - float(el.get("x", 0)), y - float(el.get("y", 0)))

    def mouseMoveEvent(self, ev):
        if self._prise is None or self.ed.courant is None:
            return
        x, y = self._vers_logo(ev.position())
        el = self.ed.logo["elements"][self.ed.courant]
        el["x"], el["y"] = round(x - self._prise[0]), round(y - self._prise[1])
        self.update()

    def mouseReleaseEvent(self, ev):
        if self._prise is not None:
            self._prise = None
            self.modifie.emit()

    def wheelEvent(self, ev):
        if self.ed.courant is None:
            return
        el = self.ed.logo["elements"][self.ed.courant]
        k = 1.06 if ev.angleDelta().y() > 0 else 1 / 1.06
        if el["type"] == "texte":
            el["taille"] = max(8, round(float(el.get("taille", 100)) * k))
        else:
            el["l"], el["h"] = max(8, round(float(el.get("l", 100)) * k)), max(8, round(float(el.get("h", 100)) * k))
        self.update()
        self.modifie.emit()


class DialogueLogo(QDialog):
    def __init__(self, parent, params, logo=None, nom=""):
        super().__init__(parent)
        self.setWindowTitle(_("Atelier de logo"))
        self.resize(1080, 680)
        self.params = params
        self.logo = LG.copie(logo) if logo else LG.copie(next(iter(LG.gabarits(nom or params.get("chaine_nom") or "PhilCut").values())))
        if nom and not logo:
            self.logo["nom"] = nom
        self.courant = None
        self.png = None
        self.taches = []
        v = QVBoxLayout(self)
        # ---- barre du haut
        h = QHBoxLayout()
        self.nom = QLineEdit(self.logo.get("nom", ""))
        self.nom.setPlaceholderText(_("Nom du logo"))
        self.nom.textChanged.connect(lambda t: self.logo.__setitem__("nom", t))
        h.addWidget(QLabel(_("Nom")))
        h.addWidget(self.nom, 1)
        b_gab = QPushButton(_("Gabarits ▾"))
        b_gab.clicked.connect(self._gabarits)
        h.addWidget(b_gab)
        b_ouvrir = QPushButton(_("Mes logos ▾"))
        b_ouvrir.clicked.connect(self._mes_logos)
        h.addWidget(b_ouvrir)
        b_ia = QPushButton(_("Idées par l'IA…"))
        b_ia.setToolTip(_("Claude ou Gemini proposent trois logos que vous pouvez ensuite modifier ici (quelques centimes, prix affiché)."))
        b_ia.clicked.connect(self._idees_ia)
        h.addWidget(b_ia)
        b_img = QPushButton(_("Image dessinée par Gemini…"))
        b_img.clicked.connect(self._image_ia)
        h.addWidget(b_img)
        v.addLayout(h)
        # ---- centre : éléments | toile | propriétés
        c = QHBoxLayout()
        g = QVBoxLayout()
        self.liste = QListWidget()
        self.liste.setMaximumWidth(200)
        self.liste.currentRowChanged.connect(lambda r: self._choisir(r if r >= 0 else None, depuis_liste=True))
        g.addWidget(self.liste, 1)
        for lib, f in ((_("+ Texte"), self._ajouter_texte), (_("+ Forme ▾"), self._ajouter_forme), (_("+ Image…"), self._ajouter_image)):
            b = QPushButton(lib)
            b.clicked.connect(f)
            g.addWidget(b)
        hb = QHBoxLayout()
        for lib, aide, f in (("▲", _("Devant"), lambda: self._ordre(1)), ("▼", _("Derrière"), lambda: self._ordre(-1)),
                             ("⧉", _("Dupliquer"), self._dupliquer), ("✕", _("Supprimer"), self._supprimer)):
            b = QPushButton(lib)
            b.setToolTip(aide)
            b.setFixedWidth(40)
            b.clicked.connect(f)
            hb.addWidget(b)
        g.addLayout(hb)
        c.addLayout(g)
        self.toile = _Toile(self)
        self.toile.selection.connect(lambda i: self._choisir(None if i < 0 else i))
        self.toile.modifie.connect(self._rafraichir_props)
        c.addWidget(self.toile, 1)
        self.panneau = QWidget()
        self.panneau.setFixedWidth(280)
        self.form = QFormLayout(self.panneau)
        c.addWidget(self.panneau)
        v.addLayout(c, 1)
        # ---- bas
        hb2 = QHBoxLayout()
        self.fond = QCheckBox(_("Fond plein"))
        self.fond.setChecked(bool(self.logo.get("fond")))
        self.fond.toggled.connect(self._fond)
        hb2.addWidget(self.fond)
        self.taille = QComboBox()
        for lib, (L, H) in ((_("Carré 1024 × 1024"), (1024, 1024)), (_("Large 1600 × 600"), (1600, 600)), (_("Large 1600 × 800"), (1600, 800))):
            self.taille.addItem(lib, (L, H))
            if (L, H) == (self.logo["largeur"], self.logo["hauteur"]):
                self.taille.setCurrentIndex(self.taille.count() - 1)
        self.taille.currentIndexChanged.connect(self._format)
        hb2.addWidget(self.taille)
        hb2.addStretch(1)
        self.etat = QLabel("")
        hb2.addWidget(self.etat)
        for lib, f in ((_("Exporter en PNG…"), self._exporter), (_("Enregistrer"), self._enregistrer), (_("Enregistrer et animer…"), self._animer)):
            b = QPushButton(lib)
            b.clicked.connect(f)
            hb2.addWidget(b)
        b = QPushButton(_("Fermer"))
        b.clicked.connect(self.reject)
        hb2.addWidget(b)
        v.addLayout(hb2)
        self._remplir_liste()

    # ------------------------------------------------------------ liste et sélection
    def _libelle(self, el):
        if el["type"] == "texte":
            return "T  " + el.get("texte", "").replace("\n", " ")[:24]
        if el["type"] == "forme":
            return "◆  " + dict(LG.FORMES).get(el.get("forme"), el.get("forme"))
        return "▣  " + os.path.basename(el.get("chemin", ""))

    def _remplir_liste(self):
        self.liste.blockSignals(True)
        self.liste.clear()
        for el in self.logo["elements"]:
            self.liste.addItem(self._libelle(el))
        if self.courant is not None and self.courant < self.liste.count():
            self.liste.setCurrentRow(self.courant)
        self.liste.blockSignals(False)
        self._rafraichir_props()
        self.toile.update()

    def _choisir(self, i, depuis_liste=False):
        self.courant = i
        if not depuis_liste:
            self.liste.blockSignals(True)
            self.liste.setCurrentRow(-1 if i is None else i)
            self.liste.blockSignals(False)
        self._rafraichir_props()
        self.toile.update()

    def _maj(self, cle, valeur):
        if self.courant is None:
            return
        self.logo["elements"][self.courant][cle] = valeur
        self.liste.item(self.courant).setText(self._libelle(self.logo["elements"][self.courant]))
        self.toile.update()

    def _couleur(self, cle, titre):
        el = self.logo["elements"][self.courant]
        c = QColorDialog.getColor(QColor(str(el.get(cle) or "#ffffff")[:7]), self, titre, QColorDialog.ShowAlphaChannel)
        if c.isValid():
            self._maj(cle, c.name() if c.alpha() == 255 else c.name() + f"{c.alpha():02x}")
            self._rafraichir_props()

    def _rafraichir_props(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        if self.courant is None or self.courant >= len(self.logo["elements"]):
            lab = QLabel(_("Cliquez sur un élément pour le modifier. Glisser pour le déplacer, molette pour l'agrandir."))
            lab.setWordWrap(True)
            self.form.addRow(lab)
            return
        el = self.logo["elements"][self.courant]

        def spin(cle, mini, maxi, pas=1.0, dec=0):
            w = QDoubleSpinBox()
            w.setRange(mini, maxi)
            w.setDecimals(dec)
            w.setSingleStep(pas)
            w.setValue(float(el.get(cle, 0) or 0))
            w.valueChanged.connect(lambda val, c=cle: self._maj(c, val))
            return w

        def bouton_couleur(cle, titre):
            b = QPushButton(str(el.get(cle) or _("aucune")))
            col = str(el.get(cle) or "")[:7]
            if col.startswith("#"):
                b.setStyleSheet(f"background:{col};color:{'#000' if QColor(col).lightness() > 128 else '#fff'}")
            b.clicked.connect(lambda: self._couleur(cle, titre))
            return b
        if el["type"] == "texte":
            t = QPlainTextEdit(el.get("texte", ""))
            t.setMaximumHeight(60)
            t.textChanged.connect(lambda: self._maj("texte", t.toPlainText()))
            self.form.addRow(_("Texte"), t)
            pol = QFontComboBox()
            pol.setCurrentFont(QFont(el.get("police") or "Nunito"))
            pol.currentFontChanged.connect(lambda f: self._maj("police", f.family()))
            self.form.addRow(_("Police"), pol)
            self.form.addRow(_("Taille"), spin("taille", 8, 1200, 4))
            hg = QHBoxLayout()
            for cle, lib in (("gras", _("Gras")), ("italique", _("Italique"))):
                cb = QCheckBox(lib)
                cb.setChecked(bool(el.get(cle)))
                cb.toggled.connect(lambda v_, c=cle: self._maj(c, v_))
                hg.addWidget(cb)
            self.form.addRow(hg)
            self.form.addRow(_("Couleur"), bouton_couleur("couleur", _("Couleur du texte")))
            eff = QComboBox()
            for k, lib in LG.EFFETS:
                eff.addItem(lib, k)
            eff.setCurrentIndex(max(0, eff.findData(el.get("effet") or "aucun")))
            eff.currentIndexChanged.connect(lambda _i: self._maj("effet", eff.currentData()))
            self.form.addRow(_("Effet"), eff)
            self.form.addRow(_("Couleur de l'effet"), bouton_couleur("couleur2", _("Couleur du contour, de la lueur ou du dégradé")))
            self.form.addRow(_("Epaisseur de l'effet"), spin("epaisseur", 0, 80))
            self.form.addRow(_("Espacement (%)"), spin("espacement", -20, 80))
        elif el["type"] == "forme":
            fo = QComboBox()
            for k, lib in LG.FORMES:
                fo.addItem(lib, k)
            fo.setCurrentIndex(max(0, fo.findData(el.get("forme"))))
            fo.currentIndexChanged.connect(lambda _i: (self._maj("forme", fo.currentData())))
            self.form.addRow(_("Forme"), fo)
            self.form.addRow(_("Largeur"), spin("l", 4, 4000, 10))
            self.form.addRow(_("Hauteur"), spin("h", 4, 4000, 10))
            self.form.addRow(_("Couleur"), bouton_couleur("couleur", _("Couleur de la forme")))
            self.form.addRow(_("Contour"), bouton_couleur("contour", _("Couleur du contour")))
            self.form.addRow(_("Epaisseur du contour"), spin("epaisseur", 0, 200))
        else:
            self.form.addRow(_("Largeur"), spin("l", 4, 4000, 10))
            self.form.addRow(_("Hauteur"), spin("h", 4, 4000, 10))
        self.form.addRow(_("Rotation (°)"), spin("rotation", -180, 180, 5))
        el.setdefault("opacite", 1.0)
        self.form.addRow(_("Opacité"), spin("opacite", 0, 1, 0.05, 2))
        hp = QHBoxLayout()
        hp.addWidget(spin("x", -2000, 6000, 5))
        hp.addWidget(spin("y", -2000, 6000, 5))
        self.form.addRow(_("Position x, y"), hp)

    # ------------------------------------------------------------ actions
    def _ajouter(self, el):
        self.logo["elements"].append(el)
        self.courant = len(self.logo["elements"]) - 1
        self._remplir_liste()

    def _ajouter_texte(self):
        self._ajouter(LG.texte(self.logo.get("nom") or _("Texte"), self.logo["largeur"] / 2, self.logo["hauteur"] / 2,
                               taille=int(self.logo["hauteur"] * 0.14)))

    def _ajouter_forme(self):
        m = QMenu(self)
        for k, lib in LG.FORMES:
            m.addAction(lib, lambda k=k: self._ajouter(LG.forme(k, self.logo["largeur"] / 2, self.logo["hauteur"] / 2,
                                                                min(self.logo["largeur"], self.logo["hauteur"]) * 0.6,
                                                                min(self.logo["largeur"], self.logo["hauteur"]) * 0.6)))
        m.exec(self.cursor().pos())

    def _ajouter_image(self):
        p, _f = QFileDialog.getOpenFileName(self, _("Image"), "", "Images (*.png *.jpg *.jpeg *.webp *.svg)")
        if p:
            q = QImage(p)
            e = min(self.logo["largeur"] * 0.6 / max(1, q.width()), self.logo["hauteur"] * 0.6 / max(1, q.height()))
            self._ajouter({"type": "image", "chemin": p, "x": self.logo["largeur"] / 2, "y": self.logo["hauteur"] / 2,
                           "l": round(q.width() * e), "h": round(q.height() * e), "rotation": 0, "opacite": 1.0})

    def _ordre(self, sens):
        i = self.courant
        if i is None:
            return
        j = i + sens
        if 0 <= j < len(self.logo["elements"]):
            els = self.logo["elements"]
            els[i], els[j] = els[j], els[i]
            self.courant = j
            self._remplir_liste()

    def _dupliquer(self):
        if self.courant is not None:
            el = LG.copie(self.logo["elements"][self.courant])
            el["x"], el["y"] = el.get("x", 0) + 30, el.get("y", 0) + 30
            self._ajouter(el)

    def _supprimer(self):
        if self.courant is not None:
            del self.logo["elements"][self.courant]
            self.courant = None
            self._remplir_liste()

    def _fond(self, oui):
        if oui:
            c = QColorDialog.getColor(QColor(self.logo.get("fond") or "#0b0b12"), self, _("Couleur du fond"))
            self.logo["fond"] = c.name() if c.isValid() else "#0b0b12"
        else:
            self.logo["fond"] = None
        self.toile.update()

    def _format(self):
        L, H = self.taille.currentData()
        ex, ey = L / self.logo["largeur"], H / self.logo["hauteur"]
        for el in self.logo["elements"]:
            el["x"], el["y"] = el.get("x", 0) * ex, el.get("y", 0) * ey
        self.logo["largeur"], self.logo["hauteur"] = L, H
        self.toile.update()

    def _charger(self, lg):
        self.logo = LG.copie(lg)
        self.nom.setText(self.logo.get("nom", ""))
        self.fond.blockSignals(True)
        self.fond.setChecked(bool(self.logo.get("fond")))
        self.fond.blockSignals(False)
        self.courant = None
        self._remplir_liste()

    def _gabarits(self):
        m = QMenu(self)
        for n, lg in LG.gabarits(self.logo.get("nom") or "PhilCut").items():
            px = QPixmap.fromImage(LG.rendre(lg, 96))
            m.addAction(px, n, lambda lg=lg: self._charger(dict(lg, nom=self.logo.get("nom") or lg["nom"])))
        m.exec(self.cursor().pos())

    def _mes_logos(self):
        m = QMenu(self)
        mes = LG.liste()
        if not mes:
            m.addAction(_("Aucun logo enregistré pour l'instant")).setEnabled(False)
        for lg in mes:
            m.addAction(QPixmap.fromImage(LG.rendre(lg, 96)), lg.get("nom", "?"), lambda lg=lg: self._charger(lg))
        m.exec(self.cursor().pos())

    def _idees_ia(self):
        from . import ia, dialogues_ia
        if not dialogues_ia.verifier_cle(self, self.params):
            return
        style, ok = QInputDialog.getText(self, _("Idées par l'IA"), _("Style souhaité (ex. « aviation rétro », « pharmacie moderne et rassurante », "
                                                                       "« néon festif ») — laisser vide pour laisser l'IA choisir :"))
        if not ok:
            return
        if not ia.confirmer_cout(self.parent() or self, self.params, 2500, 0, _("Trois logos proposés pour « {n} »", n=self.logo.get("nom"))):
            return
        base = self.logo if self.logo["elements"] else None
        t = Tache(lambda tache: LG.proposer_ia(self.params, self.logo.get("nom") or "PhilCut", style, base=base), _("Logo"))
        self.taches.append(t)
        self.etat.setText(_("L'IA dessine trois propositions…"))
        t.fini.connect(self._idees_pretes)
        t.start()

    def _idees_pretes(self, props, err):
        self.etat.setText("")
        if err:
            QMessageBox.warning(self, _("Idées par l'IA"), str(err))
            return
        m = QMenu(self)
        m.addAction(_("Choisissez une proposition (modifiable ensuite) :")).setEnabled(False)
        for lg in props:
            m.addAction(QPixmap.fromImage(LG.rendre(dict(lg, fond=lg.get("fond") or "#3a3a44"), 140)), lg.get("nom", ""), lambda lg=lg: self._charger(lg))
        m.exec(self.mapToGlobal(self.rect().center()))

    def _image_ia(self):
        from . import ia
        if not (self.params.get("clef_gemini") or "").strip():
            QMessageBox.information(self, _("Image dessinée par Gemini"), _("Il faut une clef Gemini : Assistant › Connecter une IA."))
            return
        consigne, ok = QInputDialog.getText(self, _("Image dessinée par Gemini"), _("Décrivez le logo (le nom « {n} » y sera écrit) :",
                                                                                       n=self.logo.get("nom")))
        if not ok:
            return
        if not ia.confirmer_cout(self, self.params, 600, 0, _("Une image de logo dessinée par Gemini (environ 0,04 $ l'image).")):
            return
        sortie = os.path.join(LG.dossier(), f"ia_{len(os.listdir(LG.dossier()))}.png")
        texte = _("« {n} », {c}", n=self.logo.get("nom"), c=consigne)
        t = Tache(lambda tache: LG.image_ia(self.params, texte, sortie), _("Logo"))
        self.taches.append(t)
        self.etat.setText(_("Gemini dessine…"))
        t.fini.connect(lambda r, e: (self.etat.setText(""), QMessageBox.warning(self, _("Gemini"), str(e)) if e else self._image_prete(r)))
        t.start()

    def _image_prete(self, chemin):
        q = QImage(chemin)
        e = min(self.logo["largeur"] * 0.9 / max(1, q.width()), self.logo["hauteur"] * 0.9 / max(1, q.height()))
        self._ajouter({"type": "image", "chemin": chemin, "x": self.logo["largeur"] / 2, "y": self.logo["hauteur"] / 2,
                       "l": round(q.width() * e), "h": round(q.height() * e), "rotation": 0, "opacite": 1.0})

    def _enregistrer(self):
        self.png = LG.enregistrer(self.logo)
        self.etat.setText(_("✓ Enregistré dans Mes logos"))
        return self.png

    def _exporter(self):
        p, _f = QFileDialog.getSaveFileName(self, _("Exporter le logo"), (self.logo.get("nom") or "logo") + ".png", "PNG (*.png)")
        if p:
            LG.rendre(self.logo, max(2048, self.logo["largeur"])).save(p)
            self.etat.setText(_("✓ Exporté"))

    def _animer(self):
        self._enregistrer()
        self.accept()

    def done(self, r):
        for t in self.taches:
            t.wait(30000)
        super().done(r)
