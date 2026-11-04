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
        self.mode = None            # "deplacer" | "gauche" | "droite"
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
        base = QColor("#4b3a8a") if piste == "video" else QColor("#8a5a1f") if piste == "voix" else QColor("#1f6a6e")
        if self.media and self.media.get("genre") == "image":
            base = QColor("#7a4a1f")
        p.setPen(Qt.NoPen)
        p.setBrush(base)
        p.drawRoundedRect(r, 5, 5)
        if piste == "video" and self.vignette:
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
        elif piste in ("audio", "voix") and self.media and self.media.get("onde"):
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
        if self.clip.get("effets"):
            extra.append("✦" * min(3, len(self.clip["effets"])))
        if self.clip.get("transition"):
            extra.append("⇥")
        if self.clip.get("muet"):
            extra.append("🔇")
        texte = nom + ("  " + " ".join(extra) if extra else "")
        p.drawText(QRectF(r.x() + 6, r.y() + 1, r.width() - 10, 15), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(texte, Qt.ElideRight, int(r.width() - 12)))
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

    # ---- souris
    def _zone(self, pos):
        r = self.rect()
        if pos.x() <= r.x() + BORD:
            return "gauche"
        if pos.x() >= r.right() - BORD:
            return "droite"
        return "deplacer"

    def hoverMoveEvent(self, e):
        z = self._zone(e.pos())
        self.setCursor(Qt.SizeHorCursor if z != "deplacer" else Qt.OpenHandCursor)
        self.update()
        super().hoverMoveEvent(e)

    def hoverLeaveEvent(self, e):
        self.update()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        self.mode = self._zone(e.pos())
        self.tl.projet.marquer()
        self._origine = (e.scenePos().x(), self.clip["debut"], self.clip["src_debut"], self.clip["src_fin"])
        if self.mode != "deplacer":
            e.accept()
            self.setSelected(True)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
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
        self.tl.proprietes.emit(self.clip["id"])

    def contextMenuEvent(self, e):
        self.setSelected(True)
        self.tl.menu_clip(self.clip, e.screenPos())


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
        m.addAction(_("Modifier…"), lambda: self.tl.proprietes.emit(self.elem["id"]))
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
        y = H_REGLE
        out = {"video": (y, self.h_video)}
        y += self.h_video
        out["audio"] = (y, H_AUDIO)
        y += H_AUDIO
        out["voix"] = (y, H_VOIX)
        y += H_VOIX
        out["titre"] = (y, H_CALQUE)
        y += H_CALQUE
        out["goodie"] = (y, H_CALQUE)
        return out

    def hauteur_totale(self):
        return H_REGLE + self.h_video + H_AUDIO + H_VOIX + H_CALQUE * 2

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
                y, h = pistes[c["piste"] if c["piste"] in ("video", "audio", "voix") else "audio"]
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
            p.fillRect(QRectF(r.left(), y, r.width(), h), fond2 if nom in ("video", "titre") else _c("fond"))
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
        for nom, (y, h) in self._pistes().items():
            lib = {"video": _("Vidéo"), "audio": _("Musique"), "voix": _("Voix"), "titre": _("Titres"), "goodie": _("Goodies")}[nom]
            p.drawText(QRectF(x0 + 8, y, MARGE_G - 12, h), Qt.AlignLeft | Qt.AlignVCenter, lib)
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
    def mousePressEvent(self, e):
        sp = self.mapToScene(e.pos())
        if e.button() == Qt.LeftButton and (sp.y() < H_REGLE or self.itemAt(e.pos()) is None) and sp.x() >= MARGE_G:
            self._glisse_curseur = True
            self.aller_a((sp.x() - MARGE_G) / self.pps)
            if self.itemAt(e.pos()) is None:
                self._scene.clearSelection()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._glisse_curseur:
            sp = self.mapToScene(e.pos())
            self.aller_a(max(0.0, (sp.x() - MARGE_G) / self.pps))
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._glisse_curseur = False
        super().mouseReleaseEvent(e)

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
        for piste in ("video", "audio", "voix"):
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

    def menu_clip(self, clip, pos):
        m = QMenu()
        m.addAction(_("Couper ici (C)"), self.couper_au_curseur)
        m.addAction(_("Supprimer et refermer (Suppr)"), lambda: self.supprimer_selection(True))
        m.addAction(_("Supprimer en laissant un trou (Maj+Suppr)"), lambda: self.supprimer_selection(False))
        m.addSeparator()
        for lib, v in ((_("Vitesse ×0,25"), 0.25), (_("Vitesse ×0,5"), 0.5), (_("Vitesse normale"), 1.0), (_("Vitesse ×2"), 2.0), (_("Vitesse ×4"), 4.0), (_("Vitesse ×8"), 8.0)):
            m.addAction(lib, lambda v=v: self._vitesse(clip, v))
        m.addSeparator()
        if clip["piste"] == "video":
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
        m.addAction(_("Effets et transition…"), lambda: self.demande_menu.emit(clip["id"], "effets"))
        if self.zone_valide():
            m.addAction(_("Effets sur la partie sélectionnée seulement (en jaune)…"), lambda: self.demande_menu.emit(clip["id"], "effets_partie"))
        m.addAction(_("Propriétés…"), lambda: self.proprietes.emit(clip["id"]))
        m.exec(pos)

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
        pistes = self._pistes()
        piste = next((n for n in ("audio", "voix") if pistes[n][0] <= sp.y() < pistes[n][0] + pistes[n][1]), "video")
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
