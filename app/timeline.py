"""La timeline : une bande video, une bande son, une bande titres et Goodies, un curseur de lecture.

Tout se fait a la souris : deposer un media depuis la bibliotheque, glisser un plan, tirer ses bords pour le
rogner, couper au curseur (C), supprimer (Suppr), zoomer (molette + Ctrl). Un aimant colle les plans entre eux
et au curseur. La timeline lit et ecrit directement le projet (app/projet.py) et previent la fenetre par signaux.
"""
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QMimeData, QLineF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QLinearGradient, QCursor, QFontMetrics
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem, QMenu,
                               QApplication, QStyleOptionGraphicsItem, QFrame)

from . import theme
from .langue import _
from .projet import duree_clip, fin_clip

MIME_MEDIA = "application/x-philcut-media"
H_REGLE = 26
H_VIDEO = 74
H_AUDIO = 48
H_VOIX = 40                     # voix off, doublage : sous la musique, qui baisse quand la voix parle
H_CALQUE = 22
MARGE_G = 86                    # colonne des noms de pistes
BORD = 7                        # largeur de la zone de rognage aux bords d'un plan


def _c(nom):
    return QColor(theme.COULEURS.get(nom, "#888"))


class ItemClip(QGraphicsRectItem):
    def __init__(self, timeline, clip, piste_y, hauteur):
        super().__init__()
        self.tl = timeline
        self.clip = clip
        self.piste_y = piste_y
        self.h = hauteur
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.mode = None            # "deplacer" | "gauche" | "droite" | "transition_bord"
        self.chips = []             # [(QRectF, genre, index)] : étiquettes d'effets cliquables, calculées au dessin
        self.rect_transition = None
        self.vignette = None
        m = timeline.projet.media(clip["media"]) if timeline.projet else None
        self.media = m
        if m and m.get("vignettes"):
            px = QPixmap(m["vignettes"])
            if not px.isNull():
                self.vignette = px
        self.placer()

    def placer(self):
        x = MARGE_G + self.clip["debut"] * self.tl.pps
        w = max(4.0, duree_clip(self.clip) * self.tl.pps)
        self.setRect(0, 0, w, self.h - 6)
        self.setPos(x, self.piste_y + 3)

    # ---- dessin
    def paint(self, p, opt, w=None):
        r = self.rect()
        p.setRenderHint(QPainter.Antialiasing)
        piste = self.clip["piste"]
        base = (QColor("#4b3a8a") if piste == "video" else QColor("#6a4fb3") if piste.startswith("video") else
                QColor("#8a5a1f") if piste == "voix" else QColor("#1f6a6e"))
        if self.media and self.media.get("genre") == "image":
            base = QColor("#7a4a1f")
        p.setPen(Qt.NoPen)
        p.setBrush(base)
        p.drawRoundedRect(r, 5, 5)
        if self.tl.projet and (self.tl.projet.piste_masquee(piste) or (self.tl.projet.piste_muette(piste) and not piste.startswith("video"))):
            self.setOpacity(0.45)
        else:
            self.setOpacity(1.0)
        if piste.startswith("video") and self.vignette:
            p.save()
            p.setClipRect(r.adjusted(1, 1, -1, -1))
            vh = r.height() - 18
            # la bande contient 24 vignettes du média entier : chacune est posée à ses vraies proportions (pas
            # écrasée), en prenant pour chaque case l'image du moment qu'elle couvre
            d_med = float((self.media.get("fiche") or {}).get("duree") or 1)
            n = 24
            tw, th = self.vignette.width() / n, self.vignette.height()
            case = max(8.0, vh * tw / max(1, th))
            v = self.clip.get("vitesse", 1.0)
            x = 0.0
            while x < r.width():
                t = self.clip["src_debut"] + (x + case / 2) / self.tl.pps * v
                i = max(0, min(n - 1, int(t / d_med * n)))
                p.drawPixmap(QRectF(r.x() + 1 + x, r.y() + 16, case, vh), self.vignette, QRectF(i * tw, 0, tw, th))
                x += case
            p.restore()
        elif not piste.startswith("video") and self.media and self.media.get("onde"):
            onde = self.media["onde"]
            p.setPen(QPen(QColor(120, 230, 230, 200), 1))
            n = len(onde)
            d_med = float((self.media.get("fiche") or {}).get("duree") or 1)
            i0 = int(self.clip["src_debut"] / d_med * n)
            i1 = max(i0 + 1, int(self.clip["src_fin"] / d_med * n))
            cy = r.y() + r.height() * 0.62
            amp = r.height() * 0.3
            for k in range(int(r.width())):
                i = i0 + int((i1 - i0) * k / max(1, r.width()))
                v = onde[min(n - 1, i)] * amp
                p.drawLine(QPointF(r.x() + k, cy - v), QPointF(r.x() + k, cy + v))
        # bandeau du nom
        p.setPen(QColor(255, 255, 255, 230))
        f = QFont()
        f.setPointSizeF(8.5)
        f.setBold(True)
        p.setFont(f)
        nom = self.clip.get("nom") or ""
        extra = []
        if abs(self.clip.get("vitesse", 1.0) - 1.0) > 1e-3:
            extra.append(f"×{self.clip['vitesse']:g}")
        if self.clip.get("muet"):
            extra.append("🔇")
        texte = nom + ("  " + " ".join(extra) if extra else "")
        decal = self._dessiner_transition(p, r)
        p.setPen(QColor(255, 255, 255, 230))
        p.setFont(f)
        p.drawText(QRectF(r.x() + 6 + decal, r.y() + 1, r.width() - 10 - decal, 15), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(texte, Qt.ElideRight, int(r.width() - 12 - decal)))
        self._dessiner_chips(p, r)
        # contour (selection)
        if self.isSelected():
            p.setPen(QPen(QColor("#ffd36b"), 2))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 5, 5)
        # poignees de rognage
        if self.isSelected() or self.isUnderMouse():
            p.setBrush(QColor(255, 255, 255, 90))
            p.setPen(Qt.NoPen)
            p.drawRect(QRectF(r.x(), r.y() + 4, BORD - 2, r.height() - 8))
            p.drawRect(QRectF(r.right() - BORD + 2, r.y() + 4, BORD - 2, r.height() - 8))

    def _dessiner_transition(self, p, r):
        """La transition d'entrée du plan : un bloc hachuré sur la jonction, large comme sa durée, avec son nom.
        Renvoie la largeur occupée (le nom du plan se décale)."""
        from . import effets as E
        t = self.clip.get("transition")
        self.rect_transition = None
        if not t:
            return 0
        fi = E.fiche(t["id"]) or {"nom": t["id"]}
        d = float((t.get("params") or {}).get("duree", 0.8) or 0.8)
        w = max(14.0, min(r.width(), d * self.tl.pps))
        actif = E.actif(t)
        rt = QRectF(r.x(), r.y(), w, r.height())
        self.rect_transition = rt
        p.save()
        p.setClipRect(rt)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 210, 74, 70 if actif else 30))
        p.drawRect(rt)
        p.setPen(QPen(QColor(255, 210, 74, 150 if actif else 60), 1))
        k = -r.height()
        while k < w:                        # hachures
            p.drawLine(QPointF(r.x() + k, r.bottom()), QPointF(r.x() + k + r.height(), r.y()))
            k += 9
        p.restore()
        p.setPen(QPen(QColor("#ffd24a") if actif else QColor(255, 210, 74, 120), 2))
        p.drawLine(QPointF(rt.right(), r.y()), QPointF(rt.right(), r.bottom()))      # bord tirable : durée
        p.setPen(QPen(QColor("#ffd24a"), 2))
        p.drawLine(QPointF(r.x() + 1, r.y()), QPointF(r.x() + 1, r.bottom()))        # jonction
        f = QFont()
        f.setPointSizeF(7.5)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#1a1a1a") if actif else QColor(60, 60, 60))
        lib = ("⇆ " if actif else "⇆ (off) ") + fi["nom"] + f" {d:g} s"
        p.fillRect(QRectF(r.x() + 3, r.y() + 2, min(w - 6, QFontMetrics(f).horizontalAdvance(lib) + 8), 13), QColor(255, 210, 74, 230 if actif else 120))
        p.drawText(QRectF(r.x() + 7, r.y() + 2, w - 10, 13), Qt.AlignLeft | Qt.AlignVCenter, QFontMetrics(f).elidedText(lib, Qt.ElideRight, int(w - 12)))
        return min(w + 4, r.width() * 0.5)

    def _dessiner_chips(self, p, r):
        """Une étiquette par effet posé, en bas du plan : clic = régler, clic droit = désactiver / supprimer."""
        from . import effets as E
        from .export import VOIX
        self.chips = []
        elements = [("effet", i, (E.fiche(e["id"]) or {"nom": e["id"]})["nom"], E.actif(e)) for i, e in enumerate(self.clip.get("effets") or [])]
        noms_voix = dict(VOIX)
        elements += [("effet_audio", i, _(noms_voix.get(eid, eid)), True) for i, eid in enumerate(self.clip.get("effets_audio") or [])]
        if not elements or r.height() < 28:
            return
        f = QFont()
        f.setPointSizeF(7.5)
        p.setFont(f)
        fm = QFontMetrics(f)
        h = 14
        x = r.x() + 4
        y = r.bottom() - h - 3
        for genre, i, nom, actif in elements:
            lib = ("✦ " if genre == "effet" else "♪ ") + nom
            w = min(fm.horizontalAdvance(lib) + 12, max(30.0, r.right() - 4 - x))
            if w < 24:
                break
            rc = QRectF(x, y, w, h)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(20, 20, 26, 215) if actif else QColor(20, 20, 26, 120))
            p.drawRoundedRect(rc, 6, 6)
            p.setPen(QColor("#f2e6ff") if actif else QColor(170, 170, 170))
            p.drawText(rc.adjusted(6, 0, -4, 0), Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(lib if actif else lib + _(" (off)"), Qt.ElideRight, int(w - 8)))
            self.chips.append((rc, genre, i))
            x += w + 3
            if x > r.right() - 30:
                break

    # ---- souris
    def _zone(self, pos):
        r = self.rect()
        for rc, genre, i in self.chips:
            if rc.contains(pos):
                return (genre, i)
        rt = self.rect_transition
        if rt is not None and rt.contains(pos):
            if abs(pos.x() - rt.right()) <= 4:
                return "transition_bord"
            if pos.x() > r.x() + BORD:
                return "transition"
        if pos.x() <= r.x() + BORD:
            return "gauche"
        if pos.x() >= r.right() - BORD:
            return "droite"
        return "deplacer"

    def hoverMoveEvent(self, e):
        z = self._zone(e.pos())
        if isinstance(z, tuple) or z == "transition":
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip(_("Clic : régler · clic droit : désactiver, supprimer") if isinstance(z, tuple) else
                            _("Transition : clic pour régler, tirez le bord droit pour la durée, clic droit pour changer ou supprimer"))
        else:
            self.setToolTip("")
            self.setCursor(Qt.SizeHorCursor if z != "deplacer" else Qt.OpenHandCursor)
        self.update()
        super().hoverMoveEvent(e)

    def hoverLeaveEvent(self, e):
        self.update()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        z = self._zone(e.pos())
        if e.button() == Qt.LeftButton and (isinstance(z, tuple) or z == "transition"):
            self.tl._scene.clearSelection()
            self.setSelected(True)
            e.accept()
            self.mode = None
            if isinstance(z, tuple):
                self.tl.element_clique.emit(self.clip["id"], z[0], z[1])
            else:
                self.tl.element_clique.emit(self.clip["id"], "transition", 0)
            return
        self.mode = z
        self.tl.projet.marquer()
        self._origine = (e.scenePos().x(), self.clip["debut"], self.clip["src_debut"], self.clip["src_fin"],
                         float(((self.clip.get("transition") or {}).get("params") or {}).get("duree", 0.8) or 0.8))
        if self.mode != "deplacer":
            e.accept()
            self.setSelected(True)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.mode == "transition_bord":
            dx = (e.scenePos().x() - self._origine[0]) / self.tl.pps
            d = max(0.2, min(5.0, duree_clip(self.clip) * 0.9, self._origine[4] + dx))
            self.clip["transition"].setdefault("params", {})["duree"] = round(d, 2)
            self.update()
            self.tl.element_change.emit(self.clip["id"])
            return
        if self.mode in ("gauche", "droite"):
            dx = (e.scenePos().x() - self._origine[0]) / self.tl.pps
            v = self.clip.get("vitesse", 1.0)
            d_med = float((self.media.get("fiche") or {}).get("duree") or 1e9) if self.media else 1e9
            if self.media and self.media.get("genre") == "image":
                d_med = 1e9
            if self.mode == "gauche":
                nd = self._origine[2] + dx * v
                nd = max(0.0, min(nd, self.clip["src_fin"] - 0.1))
                t_time = self._origine[1] + (nd - self._origine[2]) / v
                self.clip["src_debut"], self.clip["debut"] = nd, max(0.0, self.tl.aimanter(t_time, self.clip))
            else:
                nf = self._origine[3] + dx * v
                nf = max(self.clip["src_debut"] + 0.1, min(nf, d_med))
                fin_t = self.tl.aimanter(self.clip["debut"] + (nf - self.clip["src_debut"]) / v, self.clip)
                self.clip["src_fin"] = max(self.clip["src_debut"] + 0.1, self.clip["src_debut"] + (fin_t - self.clip["debut"]) * v)
            self.placer()
            self.tl.apercu_rognage(self.clip, self.mode)
            return
        super().mouseMoveEvent(e)
        # deplacement : rester sur sa piste, instant aimante
        t = max(0.0, (self.pos().x() - MARGE_G) / self.tl.pps)
        t = self.tl.aimanter(t, self.clip)
        self.setPos(MARGE_G + t * self.tl.pps, self.piste_y + 3)

    def mouseReleaseEvent(self, e):
        if self.mode == "transition_bord":
            self.mode = None
            self.tl.modifie.emit()
            self.tl.element_change.emit(self.clip["id"])
            return
        if self.mode in ("gauche", "droite"):
            self.mode = None
            self.tl.projet.ranger(self.clip["piste"])
            self.tl.modifie.emit()
            self.tl.reconstruire()
            return
        super().mouseReleaseEvent(e)
        self.mode = None
        t = max(0.0, (self.pos().x() - MARGE_G) / self.tl.pps)
        if abs(t - self.clip["debut"]) > 1e-3:
            self.clip["debut"] = t
            self.tl.projet.ranger(self.clip["piste"])
            self.tl.modifie.emit()
        self.tl.reconstruire()

    def mouseDoubleClickEvent(self, e):
        z = self._zone(e.pos())
        if isinstance(z, tuple) or z == "transition":
            return
        self.tl.proprietes.emit(self.clip["id"])

    def contextMenuEvent(self, e):
        self.setSelected(True)
        z = self._zone(e.pos())
        if isinstance(z, tuple):
            self.tl.menu_effet(self.clip, z[0], z[1], e.screenPos())
        elif z in ("transition", "transition_bord"):
            self.tl.menu_transition(self.clip, e.screenPos())
        else:
            self.tl.menu_clip(self.clip, e.screenPos(), max(0.0, (e.scenePos().x() - MARGE_G) / self.tl.pps))


class ItemCalque(QGraphicsRectItem):
    """Titre ou Goodie : une barre fine deplacable."""

    def __init__(self, timeline, elem, genre, y):
        super().__init__()
        self.tl, self.elem, self.genre = timeline, elem, genre
        self.y0 = y
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.placer()

    def placer(self):
        self.setRect(0, 0, max(6.0, (self.elem["fin"] - self.elem["debut"]) * self.tl.pps), H_CALQUE - 4)
        self.setPos(MARGE_G + self.elem["debut"] * self.tl.pps, self.y0 + 2)

    def paint(self, p, opt, w=None):
        r = self.rect()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#ffd36b"), 2) if self.isSelected() else Qt.NoPen)
        p.setBrush(QColor("#b0186b") if self.genre == "titre" else QColor("#a35c00"))
        p.drawRoundedRect(r, 4, 4)
        p.setPen(QColor("#fff"))
        f = QFont()
        f.setPointSizeF(8)
        p.setFont(f)
        texte = self.elem.get("texte") if self.genre == "titre" else self.elem.get("genre", "")
        p.drawText(r.adjusted(5, 0, -4, 0), Qt.AlignLeft | Qt.AlignVCenter, QFontMetrics(f).elidedText(texte or "", Qt.ElideRight, int(r.width() - 9)))

    def mousePressEvent(self, e):
        self.tl.projet.marquer()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        t = max(0.0, (self.pos().x() - MARGE_G) / self.tl.pps)
        self.setPos(MARGE_G + t * self.tl.pps, self.y0 + 2)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        t = max(0.0, (self.pos().x() - MARGE_G) / self.tl.pps)
        d = self.elem["fin"] - self.elem["debut"]
        self.elem["debut"], self.elem["fin"] = t, t + d
        self.tl.modifie.emit()
        self.tl.reconstruire()

    def mouseDoubleClickEvent(self, e):
        self.tl.proprietes.emit(self.elem["id"])

    def contextMenuEvent(self, e):
        self.setSelected(True)
        m = QMenu()
        m.addAction(_("Régler dans l'Inspecteur"), lambda: self.tl.element_clique.emit(self.elem["id"], "calque", 0))
        m.addAction(_("Tous les réglages (fenêtre)…"), lambda: self.tl.proprietes.emit(self.elem["id"]))
        m.addAction(_("Accrocher à une personne (suit ses mouvements)…"), lambda: self.tl.demande_menu.emit(self.elem["id"], "accrocher"))
        if self.elem.get("suivi"):
            m.addAction(_("Corriger le suivi à la tête de lecture…"), lambda: self.tl.demande_menu.emit(self.elem["id"], "corriger"))
            m.addAction(_("Décrocher (position fixe)"), lambda: self.tl.demande_menu.emit(self.elem["id"], "decrocher"))
        m.addAction(_("Supprimer"), lambda: self.tl.supprimer_element(self.elem["id"]))
        m.exec(e.screenPos())


class Timeline(QGraphicsView):
    position_changee = Signal(float)
    selection_changee = Signal(list)        # identifiants selectionnes
    modifie = Signal()
    zone_changee = Signal()                 # partie sélectionnée (I / O) modifiée
    element_clique = Signal(str, str, int)  # clip_id, "effet" | "effet_audio" | "transition", index : ouvrir dans l'Inspecteur
    element_change = Signal(str)
    balayage = Signal(bool)                 # le curseur est tiré à la souris (aperçu : images de la pellicule)            # clip_id : un réglage a changé depuis la timeline (durée de transition…)
    proprietes = Signal(str)                # double clic : identifiant
    media_depose = Signal(str, str, float)  # media_id, piste, instant
    demande_menu = Signal(str, object)      # (clip_id, position ecran) pour la fenetre (effets, etc.)

    def __init__(self, projet=None, parent=None):
        super().__init__(parent)
        self.projet = projet
        self.pps = 40.0                       # pixels par seconde
        self.position = 0.0
        self.aimant = True
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.zone = [None, None]        # partie sélectionnée : début (I) et fin (O)
        self.h_video = H_VIDEO          # hauteur de la piste vidéo : Alt + molette ou Affichage › Images de la timeline
        self.setMinimumHeight(H_REGLE + H_VIDEO + H_AUDIO + H_VOIX + H_CALQUE * 2 + 14)
        self.setFrameShape(QFrame.NoFrame)
        self.setBackgroundBrush(_c("fond"))
        self._glisse_curseur = False
        self._scene.selectionChanged.connect(self._selection)
        self.reconstruire()

    # ---- disposition des pistes
    def _pistes(self):
        """Disposition : pistes vidéo (la 3 au-dessus de la 2, au-dessus de la base), puis musiques, voix, titres, Goodies.
        Les pistes ajoutées sont plus basses que la base, et tout se tasse quand il y en a beaucoup."""
        y = H_REGLE
        out = {}
        pv = self.projet.pistes_video() if self.projet else ["video"]
        pa = self.projet.pistes_audio() if self.projet else ["audio"]
        n_sup = len(pv) + len(pa) - 2
        tasse = 1.0 if n_sup <= 1 else max(0.6, 1.0 - 0.12 * (n_sup - 1))
        h_sup = int(max(36, min(self.h_video, 56) * tasse))
        for p_ in reversed(pv[1:]):
            out[p_] = (y, h_sup)
            y += h_sup
        out["video"] = (y, self.h_video)
        y += self.h_video
        for i, p_ in enumerate(pa):
            h = H_AUDIO if i == 0 else int(max(32, H_AUDIO * tasse))
            out[p_] = (y, h)
            y += h
        out["voix"] = (y, H_VOIX)
        y += H_VOIX
        out["titre"] = (y, H_CALQUE)
        y += H_CALQUE
        out["goodie"] = (y, H_CALQUE)
        return out

    def hauteur_totale(self):
        p = self._pistes()
        y, h = p["goodie"]
        return y + h

    def piste_a(self, y):
        """Piste sous l'ordonnée y de la scène (None sur la règle ou en dessous)."""
        for nom, (y0, h) in self._pistes().items():
            if y0 <= y < y0 + h:
                return nom
        return None

    def libelle_piste(self, nom):
        if nom == "video":
            return _("Vidéo") if not self.projet or len(self.projet.pistes_video()) == 1 else _("Vidéo 1")
        if nom.startswith("video"):
            return _("Vidéo {n}", n=nom[5:])
        if nom == "audio":
            return _("Musique") if not self.projet or len(self.projet.pistes_audio()) == 1 else _("Musique 1")
        if nom.startswith("audio"):
            return _("Musique {n}", n=nom[5:])
        return {"voix": _("Voix"), "titre": _("Titres"), "goodie": _("Goodies")}.get(nom, nom)

    def hauteur_images(self, facteur):
        """Agrandit ou réduit les images de la piste vidéo (de 50 à 220 pixels de haut)."""
        self.h_video = int(max(50, min(220, self.h_video * facteur)))
        self.reconstruire()

    def reconstruire(self):
        sel = {it.clip["id"] for it in self._scene.items() if isinstance(it, ItemClip) and it.isSelected()}
        self._scene.blockSignals(True)
        self._scene.clear()
        self.items_clips = {}
        if self.projet:
            pistes = self._pistes()
            for c in self.projet.clips:
                y, h = pistes.get(c["piste"], pistes["audio"])
                it = ItemClip(self, c, y, h)
                self._scene.addItem(it)
                self.items_clips[c["id"]] = it
                if c["id"] in sel:
                    it.setSelected(True)
            for t in self.projet.titres:
                self._scene.addItem(ItemCalque(self, t, "titre", pistes["titre"][0]))
            for g in self.projet.goodies:
                self._scene.addItem(ItemCalque(self, g, "goodie", pistes["goodie"][0]))
        duree = max(60.0, (self.projet.duree() if self.projet else 0) + 30.0)
        self._scene.setSceneRect(0, 0, MARGE_G + duree * self.pps + 40, self.hauteur_totale())
        self._scene.blockSignals(False)
        self.viewport().update()

    def changer_projet(self, projet):
        self.projet = projet
        self.position = 0.0
        self.reconstruire()

    # ---- fond : regle, pistes, curseur
    def drawBackground(self, p, r):
        super().drawBackground(p, r)
        pistes = self._pistes()
        fond2 = _c("surface")
        for nom, (y, h) in pistes.items():
            p.fillRect(QRectF(r.left(), y, r.width(), h), fond2 if nom.startswith("video") or nom == "titre" else _c("fond"))
            p.setPen(QPen(_c("bord_leger"), 1))
            p.drawLine(QLineF(r.left(), y + h - 0.5, r.right(), y + h - 0.5))
        # regle
        p.fillRect(QRectF(r.left(), 0, r.width(), H_REGLE), _c("surface"))
        p.setPen(QPen(_c("texte2"), 1))
        pas = self._pas_regle()
        f = QFont()
        f.setPointSizeF(8)
        p.setFont(f)
        t = max(0.0, (r.left() - MARGE_G) / self.pps)
        t = int(t / pas) * pas
        while MARGE_G + t * self.pps < r.right():
            x = MARGE_G + t * self.pps
            p.drawLine(QLineF(x, H_REGLE - 8, x, H_REGLE))
            p.drawText(QRectF(x + 3, 2, 80, H_REGLE - 4), Qt.AlignLeft | Qt.AlignVCenter, _tc(t))
            for k in range(1, 5):
                xs = x + k * pas / 5 * self.pps
                p.drawLine(QLineF(xs, H_REGLE - 4, xs, H_REGLE))
            t += pas

    def drawForeground(self, p, r):
        # barre de préparation : rouge = à préparer, orange = en cours, vert = prêt (lecture avec effets)
        etats = self.etats_preparation() if callable(getattr(self, "etats_preparation", None)) else []
        for a0, b0, etat in etats:
            couleur = {"pret": QColor("#4cd964"), "en_cours": QColor("#ffb347"), "a_preparer": QColor("#e05a5a")}[etat]
            p.fillRect(QRectF(MARGE_G + a0 * self.pps, H_REGLE - 5, max(2.0, (b0 - a0) * self.pps - 1), 4), couleur)
        a, b = self.zone
        if a is not None or b is not None:          # partie sélectionnée : bande jaune sur la règle, voile sur les pistes
            xa = MARGE_G + (a if a is not None else b) * self.pps
            xb = MARGE_G + (b if b is not None else a) * self.pps
            p.fillRect(QRectF(xa, 0, max(2.0, xb - xa), H_REGLE), QColor(255, 210, 74, 150))
            p.fillRect(QRectF(xa, H_REGLE, max(2.0, xb - xa), self.hauteur_totale() - H_REGLE), QColor(255, 210, 74, 38))
            p.setPen(QPen(QColor("#ffd24a"), 1.5))
            for x in (xa, xb):
                p.drawLine(QLineF(x, 0, x, self.hauteur_totale()))
        # colonne des noms de pistes (fixe a gauche de la vue)
        x0 = self.mapToScene(0, 0).x()
        p.fillRect(QRectF(x0, 0, MARGE_G, self.hauteur_totale()), _c("fond"))
        p.setPen(QPen(_c("bord"), 1))
        p.drawLine(QLineF(x0 + MARGE_G - 0.5, 0, x0 + MARGE_G - 0.5, self.hauteur_totale()))
        f = QFont()
        f.setPointSizeF(8.5)
        f.setBold(True)
        p.setFont(f)
        p.setPen(_c("texte2"))
        self._boutons_piste = {}
        for nom, (y, h) in self._pistes().items():
            p.setPen(_c("texte2"))
            p.setFont(f)
            p.drawText(QRectF(x0 + 8, y + 2, MARGE_G - 12, min(h, 22)), Qt.AlignLeft | Qt.AlignVCenter, self.libelle_piste(nom))
            if nom in ("titre", "goodie") or h < 34 or not self.projet:
                continue
            # petits boutons : M = son coupé (toutes les pistes à son), V = image masquée (pistes vidéo 2 et plus)
            boutons = [("muette", "M", self.projet.piste_muette(nom), _("Son de la piste coupé (écoute et export)"))]
            if nom.startswith("video") and nom != "video":
                boutons.append(("masquee", "V", self.projet.piste_masquee(nom), _("Image de la piste masquée (écoute et export)")))
            bx = x0 + 8
            by = y + h - 20
            fb = QFont()
            fb.setPointSizeF(7.5)
            fb.setBold(True)
            p.setFont(fb)
            for quoi, lettre, actif, aide in boutons:
                rc = QRectF(bx, by, 16, 14)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#e05a5a") if actif else QColor(255, 255, 255, 28))
                p.drawRoundedRect(rc, 3, 3)
                p.setPen(QColor("#ffffff") if actif else _c("texte2"))
                p.drawText(rc, Qt.AlignCenter, lettre)
                self._boutons_piste.setdefault(nom, []).append((rc, quoi, aide, actif))
                bx += 20
        # curseur de lecture
        x = MARGE_G + self.position * self.pps
        p.setPen(QPen(QColor("#ff5c5c"), 2))
        p.drawLine(QLineF(x, 0, x, self.hauteur_totale()))
        p.setBrush(QColor("#ff5c5c"))
        p.setPen(Qt.NoPen)
        p.drawPolygon([QPointF(x - 6, 0), QPointF(x + 6, 0), QPointF(x, 9)])

    def _pas_regle(self):
        for pas in (0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600):
            if pas * self.pps >= 70:
                return pas
        return 600

    # ---- curseur
    def aller_a(self, t, emettre=True):
        self.position = max(0.0, float(t))
        self.viewport().update()
        if emettre:
            self.position_changee.emit(self.position)
        x = MARGE_G + self.position * self.pps
        vue = self.mapToScene(self.viewport().rect()).boundingRect()
        if x > vue.right() - 40 or x < vue.left() + MARGE_G:
            self.horizontalScrollBar().setValue(int(x - MARGE_G - 20))

    def aimanter(self, t, clip=None):
        if not self.aimant or not self.projet:
            return t
        tol = 8.0 / self.pps
        cibles = [0.0, self.position]
        for c in self.projet.clips:
            if clip is None or c["id"] != clip["id"]:
                cibles += [c["debut"], fin_clip(c)]
        for x in cibles:
            if abs(x - t) <= tol:
                return x
        return t

    def apercu_rognage(self, clip, mode):
        """Pendant le rognage, le curseur suit le bord tire : l'apercu montre l'image exacte."""
        self.aller_a(clip["debut"] if mode == "gauche" else fin_clip(clip) - 0.001)

    # ---- souris et clavier
    def _bouton_piste_a(self, sp):
        x0 = self.mapToScene(0, 0).x()
        for nom, boutons in getattr(self, "_boutons_piste", {}).items():
            for rc, quoi, aide, actif in boutons:
                if rc.contains(sp):
                    return nom, quoi, aide, actif
        return None

    def event(self, e):
        from PySide6.QtCore import QEvent
        if e.type() == QEvent.ToolTip:
            b = self._bouton_piste_a(self.mapToScene(e.pos()))
            from PySide6.QtWidgets import QToolTip
            if b:
                QToolTip.showText(e.globalPos(), b[2] + (_(" — actif") if b[3] else _(" — clic pour activer")), self)
                return True
        return super().event(e)

    def mousePressEvent(self, e):
        sp = self.mapToScene(e.pos())
        if e.button() == Qt.LeftButton and sp.x() < MARGE_G and self.projet:
            b = self._bouton_piste_a(sp)
            if b:
                self.projet.marquer()
                self.projet.basculer_piste(b[0], b[1])
                self.modifie.emit()
                self.reconstruire()
                return
        if e.button() == Qt.LeftButton and (sp.y() < H_REGLE or self.itemAt(e.pos()) is None) and sp.x() >= MARGE_G:
            self._glisse_curseur = True
            self.balayage.emit(True)
            # glisser sur la règle des temps choisit une partie (en jaune) ; un simple clic place le curseur
            self._depart_regle = (e.pos().x(), (sp.x() - MARGE_G) / self.pps) if sp.y() < H_REGLE else None
            self.aller_a((sp.x() - MARGE_G) / self.pps)
            if self.itemAt(e.pos()) is None:
                self._scene.clearSelection()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._glisse_curseur:
            sp = self.mapToScene(e.pos())
            t = max(0.0, (sp.x() - MARGE_G) / self.pps)
            dep = getattr(self, "_depart_regle", None)
            if dep and abs(e.pos().x() - dep[0]) > 6:
                self.zone = sorted([dep[1], t])
                self.viewport().update()
            self.aller_a(t)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._glisse_curseur and getattr(self, "_depart_regle", None) and self.zone_valide():
            self.zone_changee.emit()
        self._depart_regle = None
        if self._glisse_curseur:
            self._glisse_curseur = False
            self.balayage.emit(False)
        super().mouseReleaseEvent(e)

    def contextMenuEvent(self, e):
        """Clic droit : sur un plan, son menu ; ailleurs (règle, piste vide), couper et choisir une partie à cet endroit."""
        it = self.itemAt(e.pos())
        if it is not None and isinstance(it, (ItemClip, ItemCalque)):
            super().contextMenuEvent(e)
            return
        sp = self.mapToScene(e.pos())
        piste = self.piste_a(sp.y())
        if sp.x() < MARGE_G:
            m = QMenu()
            self._menu_pistes(m, piste)
            m.exec(e.globalPos())
            return
        t = max(0.0, (sp.x() - MARGE_G) / self.pps)
        m = QMenu()
        m.addAction(_("Couper ici"), lambda: (self.aller_a(t), self.couper_au_curseur()))
        self._menu_pistes(m, piste)
        m.addAction(_("Enregistrer l'image à cet endroit…"), lambda: (self.aller_a(t), self.demande_menu.emit("", "image")))
        self._menu_partie(m, t)
        self._menu_zoom(m)
        m.exec(e.globalPos())

    def _menu_pistes(self, m, piste):
        """Ajouter ou retirer des pistes : une vidéo au-dessus (B-roll, image dans l'image), une musique de plus."""
        if not self.projet:
            return
        m.addSeparator()
        sm = m.addMenu(_("Pistes"))
        if len(self.projet.pistes_video()) < 4:
            sm.addAction(_("Ajouter une piste vidéo au-dessus (incrustation, image dans l'image)"), lambda: self._ajouter_piste("video"))
        if len(self.projet.pistes_audio()) < 4:
            sm.addAction(_("Ajouter une piste de musique ou de sons"), lambda: self._ajouter_piste("audio"))
        if piste and piste in self.projet.toutes_pistes() and piste not in ("video", "audio", "voix"):
            a = sm.addAction(_("Retirer la piste « {p} » (vide seulement)", p=self.libelle_piste(piste)), lambda: self._retirer_piste(piste))
            a.setEnabled(not self.projet.clips_piste(piste))

    def _ajouter_piste(self, genre):
        self.projet.marquer()
        self.projet.ajouter_piste(genre)
        self.modifie.emit()
        self.reconstruire()

    def _retirer_piste(self, piste):
        self.projet.marquer()
        if self.projet.retirer_piste(piste):
            self.modifie.emit()
            self.reconstruire()
        else:
            self.projet.annuler()

    def _menu_zoom(self, m):
        m.addSeparator()
        sm = m.addMenu(_("Zoom de la timeline"))
        sm.addAction(_("Tout voir (le montage remplit la largeur)"), self.ajuster)
        sm.addAction(_("Agrandir (voir plus de détail)"), lambda: self.zoomer(1.6))
        sm.addAction(_("Réduire"), lambda: self.zoomer(1 / 1.6))
        sm.addSeparator()
        sm.addAction(_("Images plus grandes"), lambda: self.hauteur_images(1.3))
        sm.addAction(_("Images plus petites"), lambda: self.hauteur_images(1 / 1.3))

    def _menu_partie(self, m, t):
        """Choisir une partie de la vidéo à la souris : début ici, fin ici, puis effets, suppression ou garder."""
        m.addSeparator()
        sm = m.addMenu(_("Partie de la vidéo (pour un effet, supprimer, garder)"))
        sm.addAction(_("La partie commence ici"), lambda: (self.aller_a(t), self.marquer_zone(0)))
        sm.addAction(_("La partie finit ici"), lambda: (self.aller_a(t), self.marquer_zone(1)))
        z = self.zone_valide()
        if z:
            sm.addSeparator()
            sm.addAction(_("Effets sur cette partie seulement…"), lambda: self.demande_menu.emit("", "effets_partie"))
            sm.addAction(_("Supprimer cette partie (la suite se recolle)"), lambda: self.demande_menu.emit("", "partie_supprimer"))
            sm.addAction(_("Garder seulement cette partie"), lambda: self.demande_menu.emit("", "partie_garder"))
            sm.addAction(_("Annuler la sélection"), lambda: (self.zone.__setitem__(0, None), self.zone.__setitem__(1, None),
                                                            self.zone_changee.emit(), self.viewport().update()))
        sm.addSeparator()
        a = sm.addAction(_("Astuce : glissez sur la règle des temps pour choisir une partie"))
        a.setEnabled(False)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.AltModifier:
            d = e.angleDelta().y() or e.angleDelta().x()        # Alt fait parfois passer la molette en horizontal
            self.hauteur_images(1.15 if d > 0 else 1 / 1.15)
        elif e.modifiers() & Qt.ControlModifier:
            self.zoomer(1.2 if e.angleDelta().y() > 0 else 1 / 1.2, e.position().x())
        else:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - e.angleDelta().y())

    def zoomer(self, facteur, x_souris=None):
        ancien = self.pps
        self.pps = max(4.0, min(600.0, self.pps * facteur))
        t = (self.mapToScene(int(x_souris or 0), 0).x() - MARGE_G) / ancien if x_souris is not None else self.position
        self.reconstruire()
        x = MARGE_G + t * self.pps
        self.horizontalScrollBar().setValue(int(x - (x_souris or 0)))

    def ajuster(self):
        """Toute la duree du projet visible."""
        if not self.projet or self.projet.duree() <= 0:
            return
        largeur = max(200, self.viewport().width() - MARGE_G - 40)
        self.pps = max(4.0, min(600.0, largeur / self.projet.duree()))
        self.reconstruire()

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Delete or k == Qt.Key_Backspace:
            self.supprimer_selection(refermer=not (e.modifiers() & Qt.ShiftModifier))
        elif k == Qt.Key_C and not e.modifiers():
            self.couper_au_curseur()
        elif k == Qt.Key_I and not e.modifiers():
            self.marquer_zone(0)
        elif k == Qt.Key_O and not e.modifiers():
            self.marquer_zone(1)
        elif k == Qt.Key_Escape:
            self.zone = [None, None]
            self.zone_changee.emit()
            self.viewport().update()
        elif k == Qt.Key_Home:
            self.aller_a(0)
        elif k == Qt.Key_End:
            self.aller_a(self.projet.duree() if self.projet else 0)
        elif k == Qt.Key_Left:
            self.aller_a(self.position - (1.0 if e.modifiers() & Qt.ShiftModifier else 1.0 / (self.projet.cadence if self.projet else 30)))
        elif k == Qt.Key_Right:
            self.aller_a(self.position + (1.0 if e.modifiers() & Qt.ShiftModifier else 1.0 / (self.projet.cadence if self.projet else 30)))
        else:
            super().keyPressEvent(e)

    # ---- partie sélectionnée (entrée / sortie)
    def marquer_zone(self, i):
        self.zone[i] = self.position
        a, b = self.zone
        if a is not None and b is not None and b < a:
            self.zone = [b, a]
        self.zone_changee.emit()
        self.viewport().update()

    def zone_valide(self):
        a, b = self.zone
        return (a, b) if a is not None and b is not None and b - a > 0.04 else None

    # ---- actions
    def selection(self):
        return [it.clip["id"] for it in self._scene.selectedItems() if isinstance(it, ItemClip)]

    def selection_calques(self):
        return [it.elem["id"] for it in self._scene.selectedItems() if isinstance(it, ItemCalque)]

    def _selection(self):
        self.selection_changee.emit(self.selection() + self.selection_calques())

    def selectionner(self, ident):
        self._scene.clearSelection()
        it = self.items_clips.get(ident)
        if it:
            it.setSelected(True)

    def couper_au_curseur(self):
        if not self.projet:
            return
        self.projet.marquer()
        fait = False
        sel = self.selection()
        for piste in self.projet.toutes_pistes():
            for c in self.projet.clips_piste(piste):
                if (not sel or c["id"] in sel) and c["debut"] < self.position < fin_clip(c):
                    if self.projet.couper(c["id"], self.position):
                        fait = True
        if fait:
            self.modifie.emit()
            self.reconstruire()
        else:
            self.projet.annuler()

    def supprimer_selection(self, refermer=True):
        if not self.projet:
            return
        ids, calques = self.selection(), self.selection_calques()
        if not ids and not calques:
            return
        self.projet.marquer()
        for i in ids:
            self.projet.retirer_clip(i, refermer=refermer)
        for i in calques:
            self.projet.retirer_element(i)
        self.modifie.emit()
        self.reconstruire()

    def supprimer_element(self, ident):
        self.projet.marquer()
        self.projet.retirer_element(ident)
        self.modifie.emit()
        self.reconstruire()

    def menu_clip(self, clip, pos, t=None):
        m = QMenu()
        t = self.position if t is None else t
        m.addAction(_("Couper ici"), lambda: (self.aller_a(t), self.couper_au_curseur()))
        m.addAction(_("Supprimer ce plan (la suite se recolle)"), lambda: self.supprimer_selection(True))
        m.addAction(_("Supprimer ce plan en laissant un trou"), lambda: self.supprimer_selection(False))
        m.addSeparator()
        for lib, v in ((_("Vitesse ×0,25"), 0.25), (_("Vitesse ×0,5"), 0.5), (_("Vitesse normale"), 1.0), (_("Vitesse ×2"), 2.0), (_("Vitesse ×4"), 4.0), (_("Vitesse ×8"), 8.0)):
            m.addAction(lib, lambda v=v: self._vitesse(clip, v))
        m.addSeparator()
        if clip["piste"].startswith("video"):
            sm = m.addMenu(_("Cadrage"))
            for lib, mode in ((_("Remplir (recadrer)"), "remplir"), (_("Contenir, bandes noires"), "contenir_noir"), (_("Contenir, fond flou"), "contenir_flou")):
                a = sm.addAction(lib, lambda mode=mode: self._cadrage(clip, mode))
                a.setCheckable(True)
                a.setChecked(clip.get("ajustement", "remplir") == mode)
            sm.addSeparator()
            a = sm.addAction(_("Suivre la personne (recadrage automatique)…"), lambda: self.demande_menu.emit(clip["id"], "suivi"))
            a.setCheckable(True)
            a.setChecked(clip.get("ajustement") == "suivi")
            if clip.get("ajustement") == "suivi":
                sm.addAction(_("Corriger le suivi à la tête de lecture…"), lambda: self.demande_menu.emit(clip["id"], "corriger"))
        a = m.addAction(_("Muet"), lambda: self._muet(clip))
        a.setCheckable(True)
        a.setChecked(bool(clip.get("muet")))
        m.addSeparator()
        m.addAction(_("Effets et transition sur tout le plan…"), lambda: self.demande_menu.emit(clip["id"], "effets"))
        if self.zone_valide():
            m.addAction(_("Effets sur la partie en jaune seulement…"), lambda: self.demande_menu.emit(clip["id"], "effets_partie"))
        m.addAction(_("Enregistrer l'image à cet endroit…"), lambda: (self.aller_a(t), self.demande_menu.emit("", "image")))
        self._menu_partie(m, t)
        self._menu_zoom(m)
        m.addSeparator()
        m.addAction(_("Tous les effets et transitions (fenêtre)…"), lambda: self.proprietes.emit(clip["id"]))
        m.exec(pos)

    def menu_effet(self, clip, genre, i, pos):
        from . import effets as E
        from .export import VOIX
        if genre == "effet":
            e = (clip.get("effets") or [])[i]
            nom = (E.fiche(e["id"]) or {"nom": e["id"]})["nom"]
        else:
            e = None
            nom = _(dict(VOIX).get(clip["effets_audio"][i], clip["effets_audio"][i]))
        m = QMenu()
        m.addAction(_("Régler « {n} »…", n=nom), lambda: self.element_clique.emit(clip["id"], genre, i))
        if e is not None:
            a = m.addAction(_("Actif"), lambda: self._basculer_effet(clip, i))
            a.setCheckable(True)
            a.setChecked(E.actif(e))
            if i > 0:
                m.addAction(_("Appliquer avant le précédent"), lambda: self._bouger_effet(clip, i, -1))
            if i < len(clip["effets"]) - 1:
                m.addAction(_("Appliquer après le suivant"), lambda: self._bouger_effet(clip, i, 1))
        m.addSeparator()
        m.addAction(_("Supprimer « {n} »", n=nom), lambda: self._supprimer_effet(clip, genre, i))
        m.exec(pos)

    def _basculer_effet(self, clip, i):
        self.projet.marquer()
        e = clip["effets"][i]
        e["actif"] = not e.get("actif", True)
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

    def _bouger_effet(self, clip, i, sens):
        j = i + sens
        if 0 <= j < len(clip["effets"]):
            self.projet.marquer()
            clip["effets"][i], clip["effets"][j] = clip["effets"][j], clip["effets"][i]
            self.modifie.emit()
            self.reconstruire()
            self.element_change.emit(clip["id"])

    def _supprimer_effet(self, clip, genre, i):
        self.projet.marquer()
        if genre == "effet":
            del clip["effets"][i]
        else:
            del clip["effets_audio"][i]
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

    def menu_transition(self, clip, pos):
        from . import effets as E
        t = clip.get("transition") or {}
        fi = E.fiche(t.get("id", "")) or {"nom": t.get("id", "")}
        m = QMenu()
        m.addAction(_("Régler la transition « {n} »…", n=fi["nom"]), lambda: self.element_clique.emit(clip["id"], "transition", 0))
        sm = m.addMenu(_("Durée"))
        for d in (0.3, 0.5, 0.8, 1.0, 1.5, 2.0):
            a = sm.addAction(_("{d:g} s", d=d), lambda d=d: self._duree_transition(clip, d))
            a.setCheckable(True)
            a.setChecked(abs(float((t.get("params") or {}).get("duree", 0.8)) - d) < 0.01)
        sm2 = m.addMenu(_("Changer pour…"))
        for k in E.par_famille().get("transition", []):
            a = sm2.addAction(E.fiche(k)["nom"], lambda k=k: self._changer_transition(clip, k))
            a.setCheckable(True)
            a.setChecked(k == t.get("id"))
        a = m.addAction(_("Active"), lambda: self._basculer_transition(clip))
        a.setCheckable(True)
        a.setChecked(E.actif(t))
        m.addSeparator()
        m.addAction(_("Supprimer la transition"), lambda: self._supprimer_transition(clip))
        m.exec(pos)

    def _duree_transition(self, clip, d):
        self.projet.marquer()
        clip["transition"].setdefault("params", {})["duree"] = d
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

    def _changer_transition(self, clip, k):
        from . import effets as E
        self.projet.marquer()
        d = float(((clip.get("transition") or {}).get("params") or {}).get("duree", 0.8))
        params = dict(E.defauts(k))
        if "duree" in params:
            params["duree"] = d
        clip["transition"] = {"id": k, "params": params}
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

    def _basculer_transition(self, clip):
        self.projet.marquer()
        t = clip["transition"]
        t["actif"] = not t.get("actif", True)
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

    def _supprimer_transition(self, clip):
        self.projet.marquer()
        clip["transition"] = None
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

    def _vitesse(self, clip, v):
        self.projet.marquer()
        self.projet.vitesse(clip["id"], v)
        self.modifie.emit()
        self.reconstruire()

    def _cadrage(self, clip, mode):
        self.projet.marquer()
        clip["ajustement"] = mode
        self.modifie.emit()
        self.reconstruire()

    def _muet(self, clip):
        self.projet.marquer()
        clip["muet"] = not clip.get("muet")
        self.modifie.emit()
        self.reconstruire()

    # ---- depot depuis la bibliotheque
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_MEDIA) or e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_MEDIA) or e.mimeData().hasUrls():
            sp = self.mapToScene(e.position().toPoint())
            self.aller_a(max(0.0, self.aimanter((sp.x() - MARGE_G) / self.pps)), emettre=False)
            e.acceptProposedAction()

    def dropEvent(self, e):
        sp = self.mapToScene(e.position().toPoint())
        t = max(0.0, self.aimanter((sp.x() - MARGE_G) / self.pps))
        piste = self.piste_a(sp.y())
        if piste not in (self.projet.toutes_pistes() if self.projet else ["video", "audio", "voix"]):
            piste = "video"
        if e.mimeData().hasFormat(MIME_MEDIA):
            for ident in bytes(e.mimeData().data(MIME_MEDIA)).decode("utf-8").split(";"):
                if ident:
                    self.media_depose.emit(ident, piste, t)
                    t = self.projet.fin_piste(piste) if self.projet else t
            e.acceptProposedAction()
        elif e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if u.isLocalFile():
                    self.media_depose.emit("fichier:" + u.toLocalFile(), piste, t)
            e.acceptProposedAction()


def _tc(t):
    t = max(0.0, float(t))
    m, s = divmod(t, 60)
    h, m = divmod(int(m), 60)
    if h:
        return f"{h}:{m:02d}:{s:04.1f}"
    if t < 10 and t != int(t):
        return f"{m}:{s:04.1f}"
    return f"{m}:{int(s):02d}"
