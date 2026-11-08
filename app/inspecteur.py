"""L'Inspecteur : le volet de droite qui montre l'élément sélectionné (plan, effet, transition, texte, Goodie) avec
de vrais réglages modifiables en direct, et pour chacun un bouton Supprimer et une case Actif.

Règle : tout ce qui est posé reste visible, re-modifiable et supprimable. Chaque réglage se répercute tout de suite
sur la timeline et l'aperçu ; les changements rapprochés (un curseur qu'on tire) ne font qu'un seul « Annuler »."""
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QSlider, QSpinBox, QToolButton,
                               QVBoxLayout, QWidget)

from . import effets as E, theme
from .icones import icone
from .langue import _
from .projet import duree_clip, fin_clip


def widget_parametre(spec, val, on_change, medias=()):
    """Un réglage d'effet (float, int, bool, choix, media, fichier, couleur) → widget relié à on_change(valeur)."""
    cle, lib, genre, defaut, mini, maxi = spec
    if genre == "float":
        w = QDoubleSpinBox()
        w.setRange(float(mini), float(maxi))
        w.setSingleStep((float(maxi) - float(mini)) / 20 or 0.1)
        w.setDecimals(2)
        w.setValue(float(val))
        w.valueChanged.connect(on_change)
    elif genre == "int":
        w = QSpinBox()
        w.setRange(int(mini), int(maxi))
        w.setValue(int(val))
        w.valueChanged.connect(on_change)
    elif genre == "bool":
        w = QCheckBox()
        w.setChecked(bool(val))
        w.toggled.connect(on_change)
    elif genre == "choix":
        w = QComboBox()
        for v, l in mini:
            w.addItem(l, v)
            if v == val:
                w.setCurrentIndex(w.count() - 1)
        w.currentIndexChanged.connect(lambda _i, w=w: on_change(w.currentData()))
    elif genre == "media":
        w = QComboBox()
        w.addItem(_("(choisir)"), "")
        for m in medias:
            w.addItem(m["nom"], m["id"])
            if m["id"] == val:
                w.setCurrentIndex(w.count() - 1)
        w.currentIndexChanged.connect(lambda _i, w=w: on_change(w.currentData()))
    elif genre == "fichier":                # mini = filtre de la fenêtre d'ouverture (ex. « LUT (*.cube *.3dl) »)
        import os
        w = QPushButton(os.path.basename(str(val)) if val else _("Choisir un fichier…"))
        w.setToolTip(str(val) or "")
        w.setStyleSheet("text-align:left;padding:3px 8px")

        def choisir_fichier():
            from PySide6.QtWidgets import QFileDialog
            filtre = str(mini or "*")
            genre = "images" if any(x in filtre.lower() for x in ("png", "jpg", "image")) else \
                "musique" if any(x in filtre.lower() for x in ("mp3", "wav")) else "videos" if "mp4" in filtre.lower() else "documents"
            if val and os.path.isdir(os.path.dirname(str(val))):
                ch, _f = QFileDialog.getOpenFileName(w, lib, os.path.dirname(str(val)), filtre)
            else:
                from .widgets import ouvrir_fichier
                ch = ouvrir_fichier(w, lib, filtre, genre)
            if ch:
                w.setText(os.path.basename(ch))
                w.setToolTip(ch)
                on_change(ch)
        w.clicked.connect(choisir_fichier)
    else:                                   # couleur
        w = QPushButton(str(val))
        w.setStyleSheet(f"background:{val};color:#000" if str(val).startswith("#") else "")

        def choisir():
            c = QColorDialog.getColor(QColor(w.text()), w, lib)
            if c.isValid():
                w.setText(c.name())
                w.setStyleSheet(f"background:{c.name()};color:#000")
                on_change(c.name())
        w.clicked.connect(choisir)
    return w


class Inspecteur(QWidget):
    demande_effets = Signal(str)            # clip_id : ouvrir la fenêtre « Effets et transition »
    demande_edition = Signal(str)           # id d'un texte ou Goodie : fenêtre complète

    def __init__(self, editeur):
        super().__init__()
        self.ed = editeur
        self.projet = editeur.projet
        self._dernier_marquage = 0.0
        self._cible = None                  # (genre, id) de ce qui est montré
        self._ouvrir = None                 # ("effet", i) | ("transition", 0) : réglages dépliés
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        self.zone = QScrollArea()
        self.zone.setWidgetResizable(True)
        self.zone.setFrameShape(QFrame.NoFrame)
        self.zone.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        v.addWidget(self.zone)
        self.contenu = None
        self.vide()

    # ------------------------------------------------------------ mécanique
    def _nouveau(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)
        self._en_cours = w
        return lay

    def _poser(self, defil=0):
        """Le contenu est posé dans la zone une fois construit (sinon la zone ne connaît pas sa hauteur)."""
        self.zone.setWidget(self._en_cours)
        self.contenu = self._en_cours
        self.contenu.adjustSize()
        self.zone.verticalScrollBar().setValue(defil)
        self.zone.horizontalScrollBar().setValue(0)         # jamais de décalage horizontal (contenu plus large qu'attendu)

    def _marquer(self, cle=None):
        """Un seul « Annuler » pour une rafale de changements du même réglage (curseur qu'on tire) ; un autre réglage
        ou une pause de plus d'une seconde et demie ouvrent un nouvel « Annuler »."""
        t = time.monotonic()
        if t - self._dernier_marquage > 1.5 or cle != getattr(self, "_derniere_cle", None):
            self.projet.marquer()
        self._dernier_marquage = t
        self._derniere_cle = cle

    def _changer(self, f, reconstruire=True):
        self._marquer(getattr(f, "__code__", None))
        f()
        self.ed._modifie()
        if reconstruire:
            self.ed.timeline.reconstruire()

    # ------------------------------------------------------------ autocollants et badges : texte, couleur, angle, photo
    def _options_autocollant(self, g):
        import os
        gr = QGroupBox(_("Contenu"))
        f = QFormLayout(gr)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        opts = g.setdefault("options", {})
        genre = g["genre"]
        from . import autocollants as AC
        if genre != "fleche" and genre != "image":
            te = QLineEdit(str(opts.get("texte") or ""))
            te.setPlaceholderText(_("Texte") if genre != "bandeau_tendance" else _("Texte ; « | » pour passer à la ligne"))
            te.textChanged.connect(lambda v: self._changer(lambda: opts.__setitem__("texte", v), reconstruire=False))
            f.addRow(_("Texte"), te)
        if genre == "intro_titre":
            from . import intros as IN
            ts = QLineEdit(str(opts.get("sous_texte") or ""))
            ts.setPlaceholderText(_("Sous-titre (facultatif)"))
            ts.textChanged.connect(lambda v: self._changer(lambda: opts.__setitem__("sous_texte", v), reconstruire=False))
            f.addRow(_("Sous-titre"), ts)
            cm = QComboBox()
            for k, (fam, lib, _d) in IN.MODELES.items():
                cm.addItem(f"{IN.FAMILLES[fam]} — {lib}", k)
            cm.setCurrentIndex(max(0, cm.findData(opts.get("modele") or "masque")))
            cm.currentIndexChanged.connect(lambda _i: self._changer(lambda: opts.__setitem__("modele", cm.currentData()), reconstruire=False))
            f.addRow(_("Animation"), cm)
        if genre in ("fleche", "bandeau_tendance"):
            cs = QComboBox()
            for k, lib in (AC.STYLES_FLECHE if genre == "fleche" else AC.STYLES_BANDEAU):
                cs.addItem(lib, k)
            cs.setCurrentIndex(max(0, cs.findData(opts.get("style") or ("droite" if genre == "fleche" else "incline"))))
            cs.currentIndexChanged.connect(lambda _i: self._changer(lambda: opts.__setitem__("style", cs.currentData()), reconstruire=False))
            f.addRow(_("Style"), cs)
        if genre in ("polaroid", "image"):
            bi = QPushButton(os.path.basename(opts.get("chemin") or "") or _("Choisir une photo…"))
            bi.setStyleSheet("text-align:left;padding:3px 8px")

            def photo():
                from PySide6.QtWidgets import QFileDialog
                from .session import dossier_systeme
                from .widgets import ouvrir_fichier
                ch = ouvrir_fichier(self, _("Photo"), "Images (*.png *.jpg *.jpeg *.webp)", "images", self.ed.params)
                if ch:
                    self._changer(lambda: opts.__setitem__("chemin", ch), reconstruire=False)
                    self.montrer_goodie(g)
            bi.clicked.connect(photo)
            f.addRow(_("Photo"), bi)

        def bouton_couleur(cle, defaut, titre):
            bc = QPushButton(opts.get(cle) or defaut)
            bc.setStyleSheet(f"background:{opts.get(cle) or defaut};color:{'#000' if QColor(opts.get(cle) or defaut).lightness() > 128 else '#fff'};"
                             "text-align:left;padding:3px 8px")

            def choisir():
                c = QColorDialog.getColor(QColor(opts.get(cle) or defaut), self, titre)
                if c.isValid():
                    self._changer(lambda: opts.__setitem__(cle, c.name()), reconstruire=False)
                    self.montrer_goodie(g)
            bc.clicked.connect(choisir)
            # nuancier rapide : les couleurs à la mode en un clic
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(3)
            hl.addWidget(bc, 1)
            for coul in AC.COULEURS_TENDANCE[:6]:
                pb = QToolButton()
                pb.setFixedSize(18, 18)
                pb.setStyleSheet(f"background:{coul};border:1px solid #777;border-radius:3px")
                pb.setToolTip(coul)
                pb.clicked.connect(lambda _c=False, coul=coul: (self._changer(lambda: opts.__setitem__(cle, coul), reconstruire=False),
                                                                self.montrer_goodie(g)))
                hl.addWidget(pb)
            f.addRow(titre, w)
        if genre in ("post_it", "fleche", "bandeau_tendance", "surligne"):
            bouton_couleur("couleur", {"post_it": "#ffe066", "fleche": "#ff3b30", "bandeau_tendance": "#ff8c1a", "surligne": "#ffe14d"}[genre],
                           _("Couleur") if genre != "bandeau_tendance" else _("Couleur de la boîte"))
        if genre == "fleche":
            bouton_couleur("contour", "#ffffff", _("Contour"))
            ep = QSlider(Qt.Horizontal)
            ep.setRange(2, 12)
            ep.setValue(int(float(opts.get("epaisseur", 0.055)) * 100))
            ep.valueChanged.connect(lambda v: self._changer(lambda: opts.__setitem__("epaisseur", v / 100), reconstruire=False))
            f.addRow(_("Epaisseur"), ep)
            mi = QCheckBox(_("Courbée de l'autre côté"))
            mi.setChecked(bool(opts.get("miroir")))
            mi.toggled.connect(lambda v: self._changer(lambda: opts.__setitem__("miroir", v), reconstruire=False))
            f.addRow(mi)
        if genre == "bandeau_tendance":
            bouton_couleur("couleur2", "#ffd21f", _("2e couleur"))
            bouton_couleur("couleur_texte", "#ffffff", _("Couleur du texte"))
        if genre in ("polaroid", "post_it", "fleche", "bandeau_tendance", "surligne"):
            sl = QSlider(Qt.Horizontal)
            sl.setRange(-180, 180) if genre == "fleche" else sl.setRange(-30, 30)
            defaut = {"fleche": 0, "polaroid": -6, "post_it": 4, "bandeau_tendance": -4, "surligne": -2}[genre]
            sl.setValue(int(self._valeur(g, "angle", float(opts.get("angle", defaut)))))
            sl.setToolTip(_("Avec des images clefs, la flèche tourne d'une image clef à l'autre."))
            sl.valueChanged.connect(lambda v: self._regler(g, "angle", float(v)))
            f.addRow(_("Direction (°)") if genre == "fleche" else _("Inclinaison (°)"), sl)
        return gr

    # ------------------------------------------------------------ valeurs d'un instrument
    def _table_valeurs(self, g):
        """Les points (instant depuis le début du Goodie, valeur) de l'instrument : modifiables, ajoutables, supprimables."""
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        from . import goodies as GO
        unite = GO.GENRES[g["genre"]][1]
        gr = QGroupBox(_("Valeurs dans le temps ({u})", u=unite))
        v = QVBoxLayout(gr)
        pts = sorted(g.get("valeurs") or [])
        tb = QTableWidget(len(pts), 2)
        tb.setHorizontalHeaderLabels([_("Instant (s)"), _("Valeur")])
        tb.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tb.verticalHeader().setVisible(False)
        tb.setMaximumHeight(170)
        for i, (t, val) in enumerate(pts):
            tb.setItem(i, 0, QTableWidgetItem(f"{t - g['debut']:.1f}"))
            tb.setItem(i, 1, QTableWidgetItem(f"{val:g}"))

        def relire(*_a):
            out = []
            for i in range(tb.rowCount()):
                try:
                    out.append((round(g["debut"] + float(tb.item(i, 0).text().replace(",", ".")), 2), float(tb.item(i, 1).text().replace(",", "."))))
                except (AttributeError, ValueError):
                    continue
            self._changer(lambda: g.__setitem__("valeurs", sorted(out)), reconstruire=False)
        tb.itemChanged.connect(relire)
        v.addWidget(tb)
        h = QHBoxLayout()
        ba = QPushButton(_("+ Point à la ligne rouge"))

        def ajouter():
            from . import goodies as GO_
            t = self.ed.timeline.position
            val = GO_.valeur(g, t) if g.get("valeurs") else 0.0
            self._changer(lambda: g.__setitem__("valeurs", sorted((g.get("valeurs") or []) + [(round(t, 2), round(val, 1))])), reconstruire=False)
            self.montrer_goodie(g)
        ba.clicked.connect(ajouter)
        h.addWidget(ba)
        bs = QPushButton(_("Retirer la ligne"))

        def retirer():
            r = tb.currentRow()
            if r >= 0:
                tb.removeRow(r)
                relire()
                self.montrer_goodie(g)
        bs.clicked.connect(retirer)
        h.addWidget(bs)
        h.addStretch(1)
        v.addLayout(h)
        aide = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>" + _("Entre deux points, l'aiguille passe en douceur. Vide : décor animé.") + "</span>")
        aide.setWordWrap(True)
        v.addWidget(aide)
        return gr

    # ------------------------------------------------------------ images clefs
    def _valeur(self, elem, cle, defaut):
        """Valeur affichée d'un réglage : celle de la ligne rouge si l'élément est animé."""
        from . import cles as K
        if elem.get("cles") and cle in dict(K.PROPRIETES[K.genre(elem)]):
            return float(K.valeurs_a(elem, self.ed.timeline.position)[cle])
        return defaut

    def _regler(self, elem, cle, v):
        """Un réglage : image clef à la ligne rouge si l'élément est animé (et que ce réglage s'anime), sinon fixe."""
        from . import cles as K
        if elem.get("cles") and cle in dict(K.PROPRIETES[K.genre(elem)]):
            self._changer(lambda: K.regler(elem, self.ed.timeline.position, **{cle: v}))
        elif K.genre(elem) == "incrustation":
            self._changer(lambda: elem.setdefault("incrust", {}).__setitem__(cle, v), reconstruire=False)
        elif K.genre(elem) == "goodie" and cle == "angle":
            self._changer(lambda: elem.setdefault("options", {}).__setitem__("angle", v), reconstruire=False)
        else:
            self._changer(lambda: elem.__setitem__(cle, v), reconstruire=False)

    def _groupe_cles(self, elem, rafraichir):
        """Rubrique « Animation (images clefs) » : poser, aller à la précédente / suivante, supprimer."""
        from . import cles as K
        gr = QGroupBox(_("Animation (images clefs)"))
        v = QVBoxLayout(gr)
        t_rel = self.ed.timeline.position - K.base(elem)
        cl = K.liste(elem)
        dedans = -0.01 <= t_rel <= K.duree(elem) + 0.01
        if cl:
            ici = K.a_cle(elem, t_rel)
            txt = _("{n} image(s) clef(s) ◆ (losanges sur la timeline). A la ligne rouge, chaque réglage (curseurs ci-dessus, "
                    "glisser dans l'image) pose ou modifie l'image clef de cet instant ; entre deux, le mouvement est progressif.", n=len(cl))
            if ici:
                txt += " " + _("La ligne rouge est sur une image clef.")
        else:
            txt = _("Pour qu'il bouge, tourne, grossisse ou s'efface : placez la ligne rouge au début du mouvement, « ◆ Image clef ici », "
                    "puis à la fin, réglez-le (curseurs ou souris dans l'image) : une seconde image clef se pose toute seule.")
        l = QLabel(txt)
        l.setWordWrap(True)
        v.addWidget(l)
        h = QHBoxLayout()
        b = QPushButton(_("◆ Image clef ici"))
        b.setEnabled(dedans)
        b.setToolTip(_("Fige les réglages actuels à la ligne rouge"))
        b.clicked.connect(lambda: (self._changer(lambda: K.poser(elem, t_rel)), rafraichir()))
        h.addWidget(b)
        for lib, sens in (("◀", -1), ("▶", 1)):
            bb = QToolButton()
            bb.setText(lib)
            bb.setToolTip(_("Aller à l'image clef précédente") if sens < 0 else _("Aller à l'image clef suivante"))
            cible = K.voisine(elem, t_rel, sens)
            bb.setEnabled(cible is not None)
            bb.clicked.connect(lambda _x=False, cible=cible: (self.ed.aller_a(K.base(elem) + cible), rafraichir()))
            h.addWidget(bb)
        h.addStretch(1)
        v.addLayout(h)
        if cl:
            h2 = QHBoxLayout()
            if K.a_cle(elem, t_rel):
                bs = QPushButton(_("Supprimer celle-ci"))
                bs.clicked.connect(lambda: (self._changer(lambda: K.retirer(elem, t_rel)), rafraichir()))
                h2.addWidget(bs)
            bt = QPushButton(_("Tout effacer (réglages fixes)"))

            def effacer():
                vals = K.valeurs(elem, t_rel)
                def f():
                    elem.pop("cles", None)
                    K.regler(elem, 0, **vals)
                self._changer(f)
                rafraichir()
            bt.clicked.connect(effacer)
            h2.addWidget(bt)
            h2.addStretch(1)
            v.addLayout(h2)
        return gr

    def _titre(self, lay, ic, texte, sous=""):
        h = QHBoxLayout()
        l = QLabel()
        l.setPixmap(icone(ic, theme.COULEURS["accent"]).pixmap(22, 22))
        h.addWidget(l)
        t = QLabel(f"<b>{texte}</b>" + (f"<br><span style='color:{theme.COULEURS['texte2']}'>{sous}</span>" if sous else ""))
        t.setWordWrap(True)
        h.addWidget(t, 1)
        lay.addLayout(h)

    def _bouton_supprimer(self, texte, f):
        b = QPushButton(icone("supprimer", "#e06060"), texte)
        b.setStyleSheet("QPushButton{color:#e06060}")
        b.clicked.connect(f)
        return b

    # ------------------------------------------------------------ affichages
    def vide(self):
        self._cible = None
        lay = self._nouveau()
        self._titre(lay, "info", _("Inspecteur"), _("Cliquez sur un plan, une étiquette d'effet, une transition, un texte ou un Goodie : "
                                                      "ses réglages apparaissent ici et se modifient en direct."))
        tl = getattr(self.ed, "timeline", None)
        c = self.projet.clip_a(tl.position, "video") if self.projet and tl is not None else None
        if c:
            b = QPushButton(_("Plan sous le curseur : « {n} »", n=c.get("nom", "")))
            b.clicked.connect(lambda: self.ed.timeline.selectionner(c["id"]) or self.montrer_clip(c["id"]))
            lay.addWidget(b)
        lay.addStretch(1)
        self._poser()

    def montrer_selection(self, ids):
        if not ids:
            self.vide()
            return
        ident = ids[0]
        if self.projet.clip(ident):
            if self._cible != ("clip", ident):
                self._ouvrir = None
            self.montrer_clip(ident)
            return
        for t in self.projet.titres:
            if t["id"] == ident:
                self.montrer_texte(t)
                return
        for g in self.projet.goodies:
            if g["id"] == ident:
                if g.get("genre") == "zone":
                    self.montrer_zone(g)
                else:
                    self.montrer_goodie(g)
                return
        self.vide()

    def montrer_element(self, clip_id, genre, i):
        """Un clic sur une étiquette d'effet ou sur la transition dans la timeline : on déplie ses réglages."""
        self._ouvrir = (genre, i)
        self.montrer_clip(clip_id)

    def rafraichir(self, clip_id=None):
        if self._cible and (clip_id is None or self._cible == ("clip", clip_id)):
            genre, ident = self._cible
            if genre == "clip":
                self.montrer_clip(ident)

    # ------------------------------------------------------------ plan
    def montrer_clip(self, ident):
        c = self.projet.clip(ident)
        if not c:
            self.vide()
            return
        self._cible = ("clip", ident)
        defil = self.zone.verticalScrollBar().value()
        self._cadre_ouvert = None
        lay = self._nouveau()
        m = self.projet.media(c["media"]) or {}
        piste = {"video": _("Vidéo"), "audio": _("Musique"), "voix": _("Voix")}.get(c["piste"], c["piste"])
        self._titre(lay, "piste_video" if c["piste"] == "video" else "piste_audio", c.get("nom", ""),
                    _("Piste {p} · {a} → {b} ({d:.1f} s)", p=piste, a=_tc(c["debut"]), b=_tc(fin_clip(c)), d=duree_clip(c)))
        # ---- réglages du plan
        g = QGroupBox(_("Plan"))
        f = QFormLayout(g)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        if m.get("genre") != "image":
            hv = QHBoxLayout()
            sv = QDoubleSpinBox()
            sv.setRange(0.1, 16.0)
            sv.setSingleStep(0.25)
            sv.setDecimals(2)
            sv.setValue(float(c.get("vitesse", 1.0)))
            sv.setSuffix(" ×")
            sv.valueChanged.connect(lambda v: self._changer(lambda: self.projet.vitesse(c["id"], v)))
            hv.addWidget(sv, 1)
            for lib, val in (("½", 0.5), ("1", 1.0), ("2", 2.0)):
                b = QToolButton()
                b.setText(lib)
                b.clicked.connect(lambda _x=False, val=val, sv=sv: sv.setValue(val))
                hv.addWidget(b)
            f.addRow(_("Vitesse"), hv)
        if c["piste"].startswith("video"):
            cb = QComboBox()
            for lib, mode in ((_("Remplir (recadrer)"), "remplir"), (_("Contenir, bandes noires"), "contenir_noir"),
                              (_("Contenir, fond flou"), "contenir_flou"), (_("Suivre la personne"), "suivi")):
                cb.addItem(lib, mode)
                if c.get("ajustement", "remplir") == mode:
                    cb.setCurrentIndex(cb.count() - 1)

            def cadrage(_i, cb=cb):
                mode = cb.currentData()
                if mode == "suivi":
                    self.ed.recadrer_suivi(c)
                else:
                    self._changer(lambda: c.__setitem__("ajustement", mode))
            cb.currentIndexChanged.connect(cadrage)
            f.addRow(_("Cadrage"), cb)
        if (m.get("fiche") or {}).get("audio") or c["piste"] != "video":
            hs = QHBoxLayout()
            sl = QSlider(Qt.Horizontal)
            sl.setRange(0, 200)
            sl.setValue(int(float(c.get("volume", 1.0)) * 100))
            lv = QLabel(f"{sl.value()} %")
            lv.setMinimumWidth(42)
            sl.valueChanged.connect(lambda v: (lv.setText(f"{v} %"), self._changer(lambda: c.__setitem__("volume", v / 100), reconstruire=False)))
            hs.addWidget(sl, 1)
            hs.addWidget(lv)
            f.addRow(_("Volume"), hs)
            mu = QCheckBox(_("Muet"))
            mu.setChecked(bool(c.get("muet")))
            mu.toggled.connect(lambda on: self._changer(lambda: c.__setitem__("muet", on)))
            f.addRow("", mu)
        lay.addWidget(g)
        # ---- musique, sons, voix : où commencer dans le morceau, fondus, couper
        if not c["piste"].startswith("video"):
            gm = QGroupBox(_("Son : début, fondus, longueur"))
            fm = QFormLayout(gm)
            fm.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            dmax = float((m.get("fiche") or {}).get("duree") or c["src_fin"])
            sd = QDoubleSpinBox()
            sd.setRange(0.0, max(0.0, dmax - 0.5))
            sd.setDecimals(1)
            sd.setSuffix(" s")
            sd.setValue(float(c["src_debut"]))
            sd.setToolTip(_("Le morceau commence plus loin (ex. 32 s : on saute l'introduction) ; le plan garde sa place et sa durée."))

            def debut_morceau(v):
                def f_():
                    d = c["src_fin"] - c["src_debut"]
                    c["src_debut"] = round(v, 2)
                    c["src_fin"] = round(min(dmax, v + d), 2)
                self._changer(f_)
            sd.valueChanged.connect(debut_morceau)
            fm.addRow(_("Commencer le morceau à"), sd)
            for cle, lib, defaut in (("fondu_entree", _("Fondu d'entrée"), 0.8), ("fondu_sortie", _("Fondu de sortie"), 1.2)):
                fs = QDoubleSpinBox()
                fs.setRange(0.0, 20.0)
                fs.setDecimals(1)
                fs.setSingleStep(0.5)
                fs.setSuffix(" s")
                fs.setValue(float(c.get(cle, defaut if c.get("fondus", True) else 0.0)))
                fs.valueChanged.connect(lambda v, cle=cle: self._changer(lambda: c.__setitem__(cle, round(v, 2))))
                fm.addRow(lib, fs)
            h = QHBoxLayout()
            b1 = QPushButton(_("Couper à la fin de la vidéo"))
            b1.setToolTip(_("Le son s'arrête avec le dernier plan vidéo (fondu de sortie compris)."))
            b1.clicked.connect(lambda: (self.ed.couper_son_fin(c["id"]), self.montrer_clip(c["id"])))
            b2 = QPushButton(_("Couper à la ligne rouge"))
            b2.clicked.connect(lambda: (self.ed.couper_son_a(c["id"], self.ed.timeline.position), self.montrer_clip(c["id"])))
            for b_ in (b1, b2):
                b_.setStyleSheet("text-align:left;padding:4px 8px")
            fm.addRow(b1)
            fm.addRow(b2)
            lay.addWidget(gm)
        # ---- incrustation (pistes vidéo au-dessus de la base)
        if c["piste"].startswith("video") and c["piste"] != "video":
            gi = QGroupBox(_("Incrustation (par-dessus la vidéo 1)"))
            fi_ = QFormLayout(gi)
            fi_.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            inc = c.setdefault("incrust", {"echelle": 1.0, "x": 0.5, "y": 0.5, "opacite": 1.0})
            for cle, lib, mini, maxi, defaut in (("echelle", _("Taille (% de l'image)"), 10, 100, 100), ("x", _("Position horizontale"), 0, 100, 50),
                                                 ("y", _("Position verticale"), 0, 100, 50), ("opacite", _("Opacité"), 0, 100, 100)):
                hs = QHBoxLayout()
                sl = QSlider(Qt.Horizontal)
                sl.setRange(mini, maxi)
                sl.setValue(int(self._valeur(c, cle, float(inc.get(cle, defaut / 100))) * 100))
                lv = QLabel(f"{sl.value()} %")
                lv.setMinimumWidth(42)
                sl.valueChanged.connect(lambda v, cle=cle, lv=lv: (lv.setText(f"{v} %"), self._regler(c, cle, v / 100)))
                hs.addWidget(sl, 1)
                hs.addWidget(lv)
                fi_.addRow(lib, hs)
            from .widgets import FluxLayout
            zb = QWidget()
            hb = FluxLayout(zb, marge=0, espace=4)          # les boutons passent à la ligne si le volet est étroit
            for lib, vals in ((_("Plein cadre"), (1.0, 0.5, 0.5)), (_("Petit, en bas à droite"), (0.3, 0.96, 0.95)), (_("Petit, en haut à gauche"), (0.3, 0.04, 0.05))):
                b = QPushButton(lib)
                b.clicked.connect(lambda _x=False, vals=vals: (self._changer(lambda: K_regler(c, self.ed.timeline.position, echelle=vals[0], x=vals[1], y=vals[2])), self.montrer_clip(ident)))
                hb.addWidget(b)
            fi_.addRow(zb)
            n = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>" + _("Le résultat se voit dans l'aperçu à l'arrêt et à l'export.") + "</span>")
            n.setWordWrap(True)
            fi_.addRow(n)
            lay.addWidget(gi)
            lay.addWidget(self._groupe_cles(c, lambda: self.montrer_clip(ident)))
        # ---- transition
        t = c.get("transition")
        gt = QGroupBox(_("Transition d'entrée"))
        ft = QFormLayout(gt)
        ft.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        if t:
            fi = E.fiche(t["id"]) or {"nom": t["id"], "parametres": [], "description": ""}
            h = QHBoxLayout()
            ca = QCheckBox(fi["nom"])
            ca.setChecked(E.actif(t))
            ca.setToolTip(_("Décochée : la transition reste posée mais ne s'applique pas"))
            ca.toggled.connect(lambda on: self._changer(lambda: t.__setitem__("actif", on)))
            h.addWidget(ca, 1)
            bx = QToolButton()
            bx.setIcon(icone("supprimer", "#e06060"))
            bx.setToolTip(_("Supprimer la transition"))
            bx.clicked.connect(lambda: (self._changer(lambda: c.__setitem__("transition", None)), self.montrer_clip(ident)))
            h.addWidget(bx)
            ft.addRow(h)
            cb = QComboBox()
            for k in E.par_famille().get("transition", []):
                cb.addItem(E.fiche(k)["nom"], k)
                if k == t["id"]:
                    cb.setCurrentIndex(cb.count() - 1)
            cb.currentIndexChanged.connect(lambda _i, cb=cb: (self.ed.timeline._changer_transition(c, cb.currentData()), self.montrer_clip(ident)))
            ft.addRow(_("Type"), cb)
            for spec in fi["parametres"]:
                val = (t.get("params") or {}).get(spec[0], spec[3])
                w = widget_parametre(spec, val, lambda v, k=spec[0]: self._changer(lambda: t.setdefault("params", {}).__setitem__(k, v)), self.projet.medias)
                ft.addRow(spec[1], w)
            d = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>{fi['description']} " + _("Elle fait le passage entre le plan d'avant et celui-ci.") + "</span>")
            d.setWordWrap(True)
            ft.addRow(d)
        else:
            b = QPushButton(_("Ajouter une transition d'entrée…"))
            b.clicked.connect(lambda: self.demande_effets.emit(ident))
            ft.addRow(b)
            n = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>" + _("Une transition se pose sur le plan qui arrive : elle fait le passage depuis le plan d'avant.") + "</span>")
            n.setWordWrap(True)
            ft.addRow(n)
        lay.addWidget(gt)
        # ---- effets
        ge = QGroupBox(_("Effets ({n})", n=len(c.get("effets") or [])))
        ve = QVBoxLayout(ge)
        effets = c.get("effets") or []
        if not effets:
            ne = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>" + _("Aucun effet sur ce plan.") + "</span>")
            ve.addWidget(ne)
        for i, e in enumerate(effets):
            ve.addWidget(self._ligne_effet(c, i, e))
        be = QPushButton(icone("effets", theme.COULEURS["texte"]), _("Ajouter un effet…"))
        be.clicked.connect(lambda: self.demande_effets.emit(ident))
        ve.addWidget(be)
        lay.addWidget(ge)
        # ---- voix (effets audio)
        if (m.get("fiche") or {}).get("audio") or c["piste"] != "video":
            from .export import VOIX
            gv = QGroupBox(_("Voix et son"))
            vv = QVBoxLayout(gv)
            poses = list(c.get("effets_audio") or [])
            hb = QHBoxLayout()
            be = QPushButton(_("▶ Ecouter avec ces retouches"))
            be.setToolTip(_("Ecoute les 15 premières secondes du plan avec les retouches cochées, comme dans la vidéo exportée"))
            be.clicked.connect(lambda: self._ecouter(c, be))
            hb.addWidget(be)
            ba = QPushButton(_("Autotune…"))
            ba.setToolTip(_("Vraie correction de justesse d'un chant (tonalité, force), écoute avant / après, nouveau fichier"))
            ba.clicked.connect(lambda: self.ed.autotune(c))
            hb.addWidget(ba)
            vv.addLayout(hb)
            if c.get("media_origine"):
                bo = QPushButton(_("Revenir à l'enregistrement d'origine (sans autotune)"))
                bo.clicked.connect(lambda: self.ed.annuler_autotune(c))
                vv.addWidget(bo)
            for eid, lib in VOIX:
                cv = QCheckBox(_(lib))
                cv.setChecked(eid in poses)
                cv.toggled.connect(lambda on, eid=eid: self._changer(lambda: self._effet_audio(c, eid, on)))
                vv.addWidget(cv)
            lay.addWidget(gv)
        # ---- résumé du rush
        r = (m.get("analyse") or {}).get("resume")
        if r:
            lr = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>{r}</span>")
            lr.setWordWrap(True)
            lay.addWidget(lr)
        bs = self._bouton_supprimer(_("Supprimer ce plan (la suite se recolle)"), lambda: (self.ed.timeline.selectionner(ident), self.ed.timeline.supprimer_selection(True)))
        lay.addWidget(bs)
        lay.addStretch(1)
        self._poser(defil)
        if self._ouvrir:
            from PySide6.QtCore import QTimer
            cible = self._cadre_ouvert if self._ouvrir[0] == "effet" and getattr(self, "_cadre_ouvert", None) else gt
            def voir(cible=cible):
                try:
                    if cible.parent() is not None and self.contenu is cible.window() or self.contenu.isAncestorOf(cible):
                        self.zone.ensureWidgetVisible(cible, 0, 40)
                        self.zone.horizontalScrollBar().setValue(0)
                except RuntimeError:        # contenu déjà remplacé
                    pass
            QTimer.singleShot(0, voir)

    def _ecouter(self, c, bouton):
        """Rend 15 s du plan avec ses retouches audio et les joue ; second clic : arrêt."""
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtCore import QUrl
        import tempfile, os
        from . import voix as V
        from .taches import Tache
        if getattr(self, "_lecteur", None) is None:
            self._lecteur = QMediaPlayer(self)
            self._sortie = QAudioOutput(self)
            self._lecteur.setAudioOutput(self._sortie)
        if self._lecteur.playbackState() == QMediaPlayer.PlayingState:
            self._lecteur.stop()
            return
        m = self.projet.media(c["media"]) or {}
        if not m.get("chemin"):
            return
        sortie = os.path.join(tempfile.gettempdir(), f"philcut_ecoute_{os.getpid()}.wav")
        effets, vol = list(c.get("effets_audio") or []), float(c.get("volume", 1.0))
        debut, duree = c["src_debut"], min(15.0, c["src_fin"] - c["src_debut"])
        bouton.setText(_("Préparation…"))
        t = Tache(lambda tc: V.rendu_ecoute(m["chemin"], effets, sortie, debut, duree, vol), _("Ecoute"))
        self._tache_ecoute = t

        def fini(r, e):
            try:
                bouton.setText(_("▶ Ecouter avec ces retouches"))
            except RuntimeError:
                pass
            if e or not r:
                return
            self._lecteur.setSource(QUrl())
            self._lecteur.setSource(QUrl.fromLocalFile(r))
            self._lecteur.play()
        t.fini.connect(fini)
        t.start()

    def _effet_audio(self, c, eid, on):
        l = [x for x in (c.get("effets_audio") or []) if x != eid]
        if on:
            l.append(eid)
        c["effets_audio"] = l

    def _ligne_effet(self, c, i, e):
        """Une ligne par effet : case Actif, nom, monter / descendre, supprimer ; réglages dépliables dessous."""
        fi = E.fiche(e["id"]) or {"nom": e["id"], "parametres": [], "description": ""}
        w = QFrame()
        w.setObjectName("ligne_effet")
        ouvert = self._ouvrir == ("effet", i)
        if ouvert:
            self._cadre_ouvert = w
        w.setStyleSheet("QFrame#ligne_effet{border:1px solid %s;border-radius:6px;background:%s}" % (theme.COULEURS["accent"] if ouvert else theme.COULEURS["bord_leger"], theme.COULEURS["surface"]))
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 4, 6, 4)
        h = QHBoxLayout()
        ca = QCheckBox()
        ca.setChecked(E.actif(e))
        ca.setToolTip(_("Actif : décochez pour garder l'effet sans l'appliquer"))
        ca.toggled.connect(lambda on: self._changer(lambda: e.__setitem__("actif", on)))
        h.addWidget(ca)
        bn = QPushButton(("▾ " if ouvert else "▸ ") + fi["nom"] + ("" if E.actif(e) else _(" (off)")))
        bn.setFlat(True)
        bn.setStyleSheet("QPushButton{font-weight:600;text-align:left;border:none;padding:2px 4px}")      # nom calé à gauche
        bn.setToolTip(fi["description"])
        bn.clicked.connect(lambda: self._deplier(c["id"], i, not ouvert))
        h.addWidget(bn, 1)
        for ic, aide, sens in (("premiere", _("Appliquer avant"), -1), ("derniere", _("Appliquer après"), 1)):
            if 0 <= i + sens < len(c["effets"]):
                b = QToolButton()
                b.setText("↑" if sens < 0 else "↓")
                b.setAutoRaise(True)
                b.setToolTip(aide)
                b.clicked.connect(lambda _x=False, sens=sens: (self.ed.timeline._bouger_effet(c, i, sens), self._deplier(c["id"], i + sens, ouvert)))
                h.addWidget(b)
        bx = QToolButton()
        bx.setIcon(icone("supprimer", "#e06060"))
        bx.setAutoRaise(True)
        bx.setToolTip(_("Supprimer cet effet"))
        bx.clicked.connect(lambda: (self.ed.timeline._supprimer_effet(c, "effet", i), self.montrer_clip(c["id"])))
        h.addWidget(bx)
        v.addLayout(h)
        if ouvert and e["id"] == "etalonnage":                 # réglages dans leur fenêtre (roues, avant / après)
            bo = QPushButton(_("Ouvrir l'étalonnage (roues de couleur, avant / après)…"))
            bo.clicked.connect(lambda: self.ed.etalonner(c))
            v.addWidget(bo)
        elif ouvert:
            if fi["parametres"]:
                f = QFormLayout()
                f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
                for spec in fi["parametres"]:
                    val = (e.get("params") or {}).get(spec[0], spec[3])
                    wp = widget_parametre(spec, val, lambda v, k=spec[0]: self._changer(lambda: e.setdefault("params", {}).__setitem__(k, v), reconstruire=False),
                                          self.projet.medias)
                    f.addRow(spec[1], wp)
                v.addLayout(f)
            else:
                v.addWidget(QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>" + _("Cet effet n'a pas de réglage.") + "</span>"))
            # étendue : tout le plan, ou une partie (de … à …, en secondes depuis le début du plan)
            from .projet import partiel
            pa = partiel(e)
            fp = QFormLayout()
            fp.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            ct = QComboBox()
            ct.addItem(_("Tout le plan"), False)
            ct.addItem(_("Une partie du plan"), True)
            ct.setCurrentIndex(1 if pa else 0)
            dc = duree_clip(c)

            def etendue(_i):
                if ct.currentData():
                    self._changer(lambda: e.update(de=round(dc / 3, 2), a=round(2 * dc / 3, 2)))
                else:
                    self._changer(lambda: (e.pop("de", None), e.pop("a", None)))
                self.montrer_clip(c["id"])
            ct.currentIndexChanged.connect(etendue)
            fp.addRow(_("S'applique à"), ct)
            if pa:
                for cle, lib, val in (("de", _("De (s)"), pa[0]), ("a", _("A (s)"), min(pa[1], dc))):
                    sp = QDoubleSpinBox()
                    sp.setRange(0.0, dc)
                    sp.setDecimals(2)
                    sp.setSingleStep(0.1)
                    sp.setValue(val)
                    sp.valueChanged.connect(lambda v_, cle=cle: self._changer(lambda: e.__setitem__(cle, round(v_, 2))))
                    fp.addRow(lib, sp)
                aide = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>" + _("Secondes comptées depuis le début du plan. Sur la timeline : bande bleue, bords à tirer.") + "</span>")
                aide.setWordWrap(True)
                fp.addRow(aide)
            v.addLayout(fp)
            d = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>{fi['description']}</span>")
            d.setWordWrap(True)
            v.addWidget(d)
        return w

    def _deplier(self, clip_id, i, ouvrir):
        self._ouvrir = ("effet", i) if ouvrir else None
        self.montrer_clip(clip_id)

    # ------------------------------------------------------------ texte
    def montrer_texte(self, t):
        from .dialogues_video import ANIMATIONS
        from .titres import EFFETS_TEXTE
        self._cible = ("texte", t["id"])
        lay = self._nouveau()
        self._titre(lay, "texte", _("Texte"), _("{a} → {b}", a=_tc(t["debut"]), b=_tc(t["fin"])))
        g = QGroupBox(_("Réglages"))
        f = QFormLayout(g)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        te = QPlainTextEdit(t.get("texte", ""))
        te.setMaximumHeight(64)
        te.textChanged.connect(lambda: self._changer(lambda: t.__setitem__("texte", te.toPlainText())))
        f.addRow(_("Texte"), te)
        an = QComboBox()
        for k, lib in ANIMATIONS:
            an.addItem(lib, k)
            if k == t.get("animation", "fondu"):
                an.setCurrentIndex(an.count() - 1)
        an.currentIndexChanged.connect(lambda _i: self._changer(lambda: t.__setitem__("animation", an.currentData()), reconstruire=False))
        f.addRow(_("Animation"), an)
        ef = QComboBox()
        for k, lib in EFFETS_TEXTE:
            ef.addItem(_(lib), k)
            if k == t.get("effet_texte", "aucun"):
                ef.setCurrentIndex(ef.count() - 1)
        ef.currentIndexChanged.connect(lambda _i: self._changer(lambda: t.__setitem__("effet_texte", ef.currentData()), reconstruire=False))
        f.addRow(_("Effet du texte"), ef)
        ta = QDoubleSpinBox()
        ta.setRange(0.3, 4.0)
        ta.setSingleStep(0.1)
        ta.setValue(self._valeur(t, "taille", float(t.get("taille", 1.0))))
        ta.valueChanged.connect(lambda v: self._regler(t, "taille", v))
        f.addRow(_("Taille"), ta)
        bc = widget_parametre(("couleur", _("Couleur"), "couleur", "#ffffff", 0, 0), t.get("couleur", "#ffffff"),
                              lambda v: self._changer(lambda: t.__setitem__("couleur", v), reconstruire=False))
        f.addRow(_("Couleur"), bc)
        for cle, lib in (("debut", _("Début (s)")), ("fin", _("Fin (s)"))):
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 36000.0)
            sp.setDecimals(2)
            sp.setValue(float(t[cle]))
            sp.valueChanged.connect(lambda v, cle=cle: self._changer(lambda: t.__setitem__(cle, v)))
            f.addRow(lib, sp)
        for cle, lib in (("x", _("Position horizontale")), ("y", _("Position verticale"))):
            sl = QSlider(Qt.Horizontal)
            sl.setRange(0, 100)
            sl.setValue(int(self._valeur(t, cle, float(t.get(cle, 0.5))) * 100))
            sl.valueChanged.connect(lambda v, cle=cle: self._regler(t, cle, v / 100))
            f.addRow(lib, sl)
        lay.addWidget(g)
        lay.addWidget(self._groupe_cles(t, lambda: self.montrer_texte(t)))
        if t.get("suivi"):
            lay.addWidget(QLabel(_("Accroché à une personne : clic droit sur le texte dans la timeline pour corriger ou décrocher.")))
        bm = QPushButton(_("Tous les réglages (police, accrocher à une personne)…"))
        bm.clicked.connect(lambda: self.demande_edition.emit(t["id"]))
        lay.addWidget(bm)
        lay.addWidget(self._bouton_supprimer(_("Supprimer ce texte"), lambda: (self._changer(lambda: self.projet.retirer_element(t["id"])), self.vide())))
        lay.addStretch(1)
        self._poser()

    # ------------------------------------------------------------ goodie
    def montrer_goodie(self, g):
        from . import goodies as GO  # noqa: F811
        self._cible = ("goodie", g["id"])
        lay = self._nouveau()
        nom = GO.GENRES.get(g.get("genre"), (g.get("genre"),))[0]
        self._titre(lay, "goodies", _("Goodie : {n}", n=nom), _("{a} → {b}", a=_tc(g["debut"]), b=_tc(g["fin"])))
        gr = QGroupBox(_("Réglages"))
        f = QFormLayout(gr)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        st = QComboBox()
        from . import goodies_dessins as GD
        illustre = g.get("genre") in GD.GENRES
        for lib, k in (((_("Illustré (animé)") if illustre else _("Cadran (tableau de bord)")), "cadran"), (_("HUD épuré"), "hud")):
            st.addItem(lib, k)
            if k == g.get("style", "cadran"):
                st.setCurrentIndex(st.count() - 1)
        st.currentIndexChanged.connect(lambda _i: self._changer(lambda: g.__setitem__("style", st.currentData()), reconstruire=False))
        contenu = g.get("genre") in ("polaroid", "post_it", "fleche", "image", "immatriculation", "bandeau", "pastille", "prix", "horaires",
                                     "date", "bandeau_tendance", "surligne", "intro_titre")
        if g.get("genre") in GO.GENRES and GO.GENRES[g["genre"]][1] or illustre:      # instruments : cadran ou HUD
            f.addRow(_("Style d'instrument"), st)
        else:
            st.deleteLater()
        if g.get("genre") == "meteo":                    # ciel de l'icône météo
            ciel = QComboBox()
            for k, lib in GD.CIELS.items():
                ciel.addItem(lib, k)
                if k == (g.get("options") or {}).get("ciel", "soleil"):
                    ciel.setCurrentIndex(ciel.count() - 1)
            ciel.currentIndexChanged.connect(lambda _i: self._changer(lambda: g.setdefault("options", {}).__setitem__("ciel", ciel.currentData()),
                                                                      reconstruire=False))
            f.addRow(_("Ciel"), ciel)
        if g.get("genre") == "compte_a_rebours":
            dep = QDoubleSpinBox()
            dep.setRange(1, 3600)
            dep.setDecimals(0)
            dep.setSuffix(" s")
            dep.setValue(float((g.get("options") or {}).get("depuis", 10)))
            dep.valueChanged.connect(lambda v: self._changer(lambda: g.setdefault("options", {}).__setitem__("depuis", v), reconstruire=False))
            f.addRow(_("Compter à partir de"), dep)
        for cle, lib, mini, maxi in (("taille", _("Taille"), 5, 60), ("x", _("Position horizontale"), 0, 100), ("y", _("Position verticale"), 0, 100)):
            sl = QSlider(Qt.Horizontal)
            sl.setRange(mini, maxi)
            sl.setValue(int(self._valeur(g, cle, float(g.get(cle, 0.5))) * 100))
            sl.valueChanged.connect(lambda v, cle=cle: self._regler(g, cle, v / 100))
            f.addRow(lib, sl)
        for cle, lib in (("debut", _("Début (s)")), ("fin", _("Fin (s)"))):
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 36000.0)
            sp.setDecimals(2)
            sp.setValue(float(g[cle]))
            sp.valueChanged.connect(lambda v, cle=cle: self._changer(lambda: g.__setitem__(cle, v)))
            f.addRow(lib, sp)
        lay.addWidget(gr)
        if contenu:                     # style, couleur, direction : juste sous les réglages, avant l'animation
            lay.addWidget(self._options_autocollant(g))
        lay.addWidget(self._groupe_cles(g, lambda: self.montrer_goodie(g)))
        opts = g.get("options") or {}
        if opts.get("groupe"):
            ba = QPushButton(icone("goodies", theme.COULEURS["texte"]), _("Profil de vol… (tous les instruments)"))
            ba.clicked.connect(lambda: self.ed.tableau_de_bord(opts["groupe"]))
            lay.addWidget(ba)
        if g.get("genre") in ("carte_trajet", "mini_carte"):
            ba = QPushButton(_("Etapes du trajet… ({n})", n=len(opts.get("etapes") or [])))
            ba.clicked.connect(lambda: self.ed.trajet(g))
            lay.addWidget(ba)
        if g.get("genre") == "manche_air":
            ba = QPushButton(_("Vent… ({d:.0f}° / {f:.0f} kt)", d=float(opts.get("vent_dir", 270)), f=float(opts.get("vent_kt", 10))))
            ba.clicked.connect(lambda: self.ed.manche_air(g))
            lay.addWidget(ba)
        if g.get("genre") in GO.GENRES and GO.GENRES[g["genre"]][1] and g.get("genre") not in ("manche_air",):
            lay.addWidget(self._table_valeurs(g))
        lay.addWidget(QLabel(_("{n} valeur(s) saisies ou issues d'une trace GPS.", n=len(g.get("valeurs") or []))))
        bm = QPushButton(_("Tous les réglages (valeurs, trace GPS, genre)…"))
        bm.clicked.connect(lambda: self.demande_edition.emit(g["id"]))
        lay.addWidget(bm)
        lay.addWidget(self._bouton_supprimer(_("Supprimer ce Goodie"), lambda: (self._changer(lambda: self.projet.retirer_element(g["id"])), self.vide())))
        lay.addStretch(1)
        self._poser()

    # ------------------------------------------------------------ zone tracée
    def montrer_zone(self, z):
        from . import zones as Z
        self._cible = ("zone", z["id"])
        defil = self.zone.verticalScrollBar().value()
        lay = self._nouveau()
        self._titre(lay, "recadrer", Z.libelle(z), _("{a} → {b}", a=_tc(z["debut"]), b=_tc(z["fin"])))
        aide = QLabel(_("Dans l'image : glissez la zone pour la déplacer, tirez un coin pour la redimensionner."))
        aide.setWordWrap(True)
        lay.addWidget(aide)
        gr = QGroupBox(_("Traitement"))
        f = QFormLayout(gr)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        tr = QComboBox()
        for k, lib in Z.TRAITEMENTS:
            tr.addItem(_(lib), k)
            if k == z.get("traitement", "flou"):
                tr.setCurrentIndex(tr.count() - 1)
        tr.currentIndexChanged.connect(lambda _i: (self._changer(lambda: z.__setitem__("traitement", tr.currentData())), self.montrer_zone(z)))
        f.addRow(_("Effet"), tr)
        if z.get("traitement") not in ("cache", "noir_blanc"):
            sl = QSlider(Qt.Horizontal)
            sl.setRange(5, 100)
            sl.setValue(int(float(z.get("force", 0.6)) * 100))
            sl.valueChanged.connect(lambda v: self._changer(lambda: z.__setitem__("force", v / 100), reconstruire=False))
            f.addRow(_("Force"), sl)
        if z.get("traitement") == "cache":
            bc = QPushButton(z.get("couleur") or "#000000")
            bc.setStyleSheet(f"QPushButton{{background:{z.get('couleur') or '#000000'};color:#fff}}")

            def couleur():
                c = QColorDialog.getColor(QColor(z.get("couleur") or "#000000"), self, _("Couleur du cache"))
                if c.isValid():
                    self._changer(lambda: z.__setitem__("couleur", c.name()), reconstruire=False)
                    self.montrer_zone(z)
            bc.clicked.connect(couleur)
            f.addRow(_("Couleur"), bc)
        fo = QComboBox()
        for k, lib in Z.FORMES:
            fo.addItem(_(lib), k)
            if k == z.get("forme", "rect"):
                fo.setCurrentIndex(fo.count() - 1)
        fo.currentIndexChanged.connect(lambda _i: self._changer(lambda: z.__setitem__("forme", fo.currentData()), reconstruire=False))
        f.addRow(_("Forme"), fo)
        for cle, lib in (("debut", _("Début (s)")), ("fin", _("Fin (s)"))):
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 36000.0)
            sp.setDecimals(2)
            sp.setValue(float(z[cle]))
            sp.valueChanged.connect(lambda v, cle=cle: self._changer(lambda: z.__setitem__(cle, v)))
            f.addRow(lib, sp)
        lay.addWidget(gr)
        gs = QGroupBox(_("Suivre ce qu'elle couvre"))
        v = QVBoxLayout(gs)
        pos = (z.get("suivi") or {}).get("positions") or []
        etat = QLabel(_("La zone suit l'objet : {n} positions trouvées par analyse de l'image.", n=len(pos)) if pos else
                      _("La zone est fixe. PhilCut peut analyser le rush image par image pour qu'elle suive le visage, la plaque "
                        "ou l'objet qu'elle couvre."))
        etat.setWordWrap(True)
        v.addWidget(etat)
        b1 = QPushButton(icone("synchro", theme.COULEURS["texte"]), _("Refaire le suivi depuis le début") if pos else _("Suivre ce qu'elle couvre"))
        b1.clicked.connect(lambda: self.ed.suivre_zone(z))
        v.addWidget(b1)
        if pos:
            b2 = QPushButton(_("Corriger à la ligne rouge (retracer ici)"))
            b2.setToolTip(_("Le suivi s'est trompé ? Placez la ligne rouge à cet instant, retracez la zone : la suite est refaite."))
            b2.clicked.connect(lambda: self.ed.retracer_zone(z))
            v.addWidget(b2)
            b3 = QPushButton(_("Figer (ne plus suivre)"))
            b3.clicked.connect(lambda: self.ed.figer_zone(z))
            v.addWidget(b3)
        for b in gs.findChildren(QPushButton):
            b.setStyleSheet("text-align:left;padding:4px 8px")
        lay.addWidget(gs)
        lay.addWidget(self._bouton_supprimer(_("Supprimer cette zone"), lambda: (self._changer(lambda: self.projet.retirer_element(z["id"])), self.vide())))
        lay.addStretch(1)
        self._poser(defil)


def K_regler(elem, t, **v):
    from . import cles as K
    return K.regler(elem, t, **v)


def _tc(t):
    m, s = divmod(max(0.0, float(t)), 60)
    return f"{int(m)}:{s:04.1f}"
