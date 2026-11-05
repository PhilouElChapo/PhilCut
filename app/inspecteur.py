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
    """Un réglage d'effet (float, int, bool, choix, media, couleur) → widget relié à on_change(valeur)."""
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
                sl.setValue(int(float(inc.get(cle, defaut / 100)) * 100))
                lv = QLabel(f"{sl.value()} %")
                lv.setMinimumWidth(42)
                sl.valueChanged.connect(lambda v, cle=cle, lv=lv: (lv.setText(f"{v} %"), self._changer(lambda: inc.__setitem__(cle, v / 100), reconstruire=False)))
                hs.addWidget(sl, 1)
                hs.addWidget(lv)
                fi_.addRow(lib, hs)
            hb = QHBoxLayout()
            for lib, vals in ((_("Plein cadre"), (1.0, 0.5, 0.5)), (_("Petit, en bas à droite"), (0.3, 0.96, 0.95)), (_("Petit, en haut à gauche"), (0.3, 0.04, 0.05))):
                b = QPushButton(lib)
                b.clicked.connect(lambda _x=False, vals=vals: (self._changer(lambda: inc.update(echelle=vals[0], x=vals[1], y=vals[2]), reconstruire=False), self.montrer_clip(ident)))
                hb.addWidget(b)
            fi_.addRow(hb)
            n = QLabel(f"<span style='color:{theme.COULEURS['texte2']}'>" + _("Le résultat se voit dans l'aperçu à l'arrêt et à l'export.") + "</span>")
            n.setWordWrap(True)
            fi_.addRow(n)
            lay.addWidget(gi)
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
        bn = QToolButton()
        bn.setText(("▾ " if ouvert else "▸ ") + fi["nom"] + ("" if E.actif(e) else _(" (off)")))
        bn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        bn.setAutoRaise(True)
        bn.setStyleSheet("QToolButton{font-weight:600;text-align:left;border:none}")
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
        if ouvert:
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
        ta.setValue(float(t.get("taille", 1.0)))
        ta.valueChanged.connect(lambda v: self._changer(lambda: t.__setitem__("taille", v), reconstruire=False))
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
            sl.setValue(int(float(t.get(cle, 0.5)) * 100))
            sl.valueChanged.connect(lambda v, cle=cle: self._changer(lambda: t.__setitem__(cle, v / 100), reconstruire=False))
            f.addRow(lib, sl)
        lay.addWidget(g)
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
        from . import goodies as GO
        self._cible = ("goodie", g["id"])
        lay = self._nouveau()
        nom = GO.GENRES.get(g.get("genre"), (g.get("genre"),))[0]
        self._titre(lay, "goodies", _("Goodie : {n}", n=nom), _("{a} → {b}", a=_tc(g["debut"]), b=_tc(g["fin"])))
        gr = QGroupBox(_("Réglages"))
        f = QFormLayout(gr)
        f.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        st = QComboBox()
        for lib, k in ((_("Cadran (tableau de bord)"), "cadran"), (_("HUD épuré"), "hud")):
            st.addItem(lib, k)
            if k == g.get("style", "cadran"):
                st.setCurrentIndex(st.count() - 1)
        st.currentIndexChanged.connect(lambda _i: self._changer(lambda: g.__setitem__("style", st.currentData()), reconstruire=False))
        f.addRow(_("Style"), st)
        for cle, lib, mini, maxi in (("taille", _("Taille"), 5, 60), ("x", _("Position horizontale"), 0, 100), ("y", _("Position verticale"), 0, 100)):
            sl = QSlider(Qt.Horizontal)
            sl.setRange(mini, maxi)
            sl.setValue(int(float(g.get(cle, 0.5)) * 100))
            sl.valueChanged.connect(lambda v, cle=cle: self._changer(lambda: g.__setitem__(cle, v / 100), reconstruire=False))
            f.addRow(lib, sl)
        for cle, lib in (("debut", _("Début (s)")), ("fin", _("Fin (s)"))):
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 36000.0)
            sp.setDecimals(2)
            sp.setValue(float(g[cle]))
            sp.valueChanged.connect(lambda v, cle=cle: self._changer(lambda: g.__setitem__(cle, v)))
            f.addRow(lib, sp)
        lay.addWidget(gr)
        lay.addWidget(QLabel(_("{n} valeur(s) saisies ou issues d'une trace GPS.", n=len(g.get("valeurs") or []))))
        bm = QPushButton(_("Tous les réglages (valeurs, trace GPS, genre)…"))
        bm.clicked.connect(lambda: self.demande_edition.emit(g["id"]))
        lay.addWidget(bm)
        lay.addWidget(self._bouton_supprimer(_("Supprimer ce Goodie"), lambda: (self._changer(lambda: self.projet.retirer_element(g["id"])), self.vide())))
        lay.addStretch(1)
        self._poser()


def _tc(t):
    m, s = divmod(max(0.0, float(t)), 60)
    return f"{int(m)}:{s:04.1f}"
