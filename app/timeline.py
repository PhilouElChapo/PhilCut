"""La timeline : une bande video, une bande son, une bande titres et Goodies, un curseur de lecture.

Tout se fait a la souris : deposer un media depuis la bibliotheque, glisser un plan, tirer ses bords pour le
rogner, couper au curseur (C), supprimer (Suppr), zoomer (molette + Ctrl). Un aimant colle les plans entre eux
et au curseur. La timeline lit et ecrit directement le projet (app/projet.py) et previent la fenetre par signaux.
"""
import math
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QMimeData, QLineF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPixmap, QLinearGradient, QCursor, QFontMetrics, QPolygonF
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem, QMenu,
                               QApplication, QStyleOptionGraphicsItem, QFrame)

from . import theme
from .langue import _
from .projet import duree_clip, fin_clip

MIME_MEDIA = "application/x-philcut-media"
MIME_EFFET = "application/x-philcut-effet"     # effet ou transition glissé depuis le catalogue
H_REGLE = 36                    # règle : temps et repères en haut, boutons [ ] de la tête rouge en bas
H_VIDEO = 74
H_AUDIO = 48
H_VOIX = 40                     # voix off, doublage : sous la musique, qui baisse quand la voix parle
H_CALQUE = 22
MARGE_G = 86                    # colonne des noms de pistes
BORD = 7                        # largeur de la zone de rognage aux bords d'un plan


def _c(nom):
    return QColor(theme.COULEURS.get(nom, "#888"))


def _losanges(p, elem, x0, y, pps, h=9):
    """Images clefs ◆ d'un élément ; renvoie [(QRectF, t_rel)] pour les clics."""
    out = []
    for c in elem.get("cles") or []:
        x = x0 + c["t"] * pps
        rc = QRectF(x - h / 2, y - h / 2, h, h)
        poly = QPolygonF([QPointF(x, y - h / 2), QPointF(x + h / 2, y), QPointF(x, y + h / 2), QPointF(x - h / 2, y)])
        p.setPen(QPen(QColor(20, 20, 26), 1))
        p.setBrush(QColor("#ffd24a"))
        p.drawPolygon(poly)
        out.append((rc, c["t"]))
    return out


class ItemClip(QGraphicsRectItem):
    def __init__(self, timeline, clip, piste_y, hauteur):
        super().__init__()
        self.tl = timeline
        self.clip = clip
        self.piste_y = piste_y
        self.h = hauteur
        self.verrou = bool(timeline.projet and timeline.projet.piste_verrouillee(clip["piste"]))
        drapeaux = QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges
        if not self.verrou:
            drapeaux |= QGraphicsItem.ItemIsMovable
        self.setFlags(drapeaux)
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
        if piste.startswith("video") and self.vignette and r.height() > 30:
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
        if not piste.startswith("video") and r.width() > 12:
            # fondus d'entrée et de sortie dessinés : une rampe blanche à chaque bout (réglables dans l'Inspecteur)
            dft = (0.8, 1.2) if piste != "voix" else (0.0, 0.0)
            if not self.clip.get("fondus", True):
                dft = (0.0, 0.0)
            fe = float(self.clip.get("fondu_entree", dft[0])) * self.tl.pps
            fs = float(self.clip.get("fondu_sortie", dft[1])) * self.tl.pps
            p.setPen(QPen(QColor(255, 255, 255, 210), 1.5))
            p.setBrush(QColor(0, 0, 0, 70))
            haut, bas = r.y() + 15, r.bottom() - 1
            if fe >= 3:
                fe = min(fe, r.width() / 2)
                p.drawPolygon(QPolygonF([QPointF(r.x(), bas), QPointF(r.x(), haut), QPointF(r.x() + fe, haut)]))
            if fs >= 3:
                fs = min(fs, r.width() / 2)
                p.drawPolygon(QPolygonF([QPointF(r.right(), bas), QPointF(r.right(), haut), QPointF(r.right() - fs, haut)]))
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
        self.losanges = _losanges(p, self.clip, r.x(), r.y() + 22, self.tl.pps) if self.clip.get("cles") else []
        # contour (selection)
        if self.isSelected():
            p.setPen(QPen(QColor("#ffd36b"), 2))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 5, 5)
        if self.verrou:
            p.setPen(QColor(255, 255, 255, 200))
            p.drawText(QRectF(r.right() - 20, r.y() + 1, 16, 15), Qt.AlignCenter, "🔒")
        # poignees de rognage
        if (self.isSelected() or self.isUnderMouse()) and not self.verrou:
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
        # l'étiquette de la transition sur sa propre ligne, au milieu du bloc hachuré : le nom du plan (en haut) et les
        # effets (en bas) ne la chevauchent plus (0.9.31)
        y = r.y() + max(17.0, r.height() / 2 - 7)
        if r.height() < 34:
            y = r.y() + 2
        largeur = min(w - 6, QFontMetrics(f).horizontalAdvance(lib) + 8)
        p.fillRect(QRectF(r.x() + 3, y, largeur, 13), QColor(255, 210, 74, 230 if actif else 120))
        p.drawText(QRectF(r.x() + 7, y, w - 10, 13), Qt.AlignLeft | Qt.AlignVCenter, QFontMetrics(f).elidedText(lib, Qt.ElideRight, int(w - 12)))
        return 0 if r.height() >= 34 else min(w + 4, r.width() * 0.5)

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
        # effets posés sur une partie du plan : une bande à leur place, bords tirables
        from .projet import partiel
        partiels = [(g, i, n, a) for g, i, n, a in elements if g == "effet" and partiel(self.clip["effets"][i])]
        elements = [x_ for x_ in elements if x_ not in partiels]
        yp = y - h - 3 if elements and r.height() >= 50 else y
        for genre, i, nom, actif in partiels:
            de, a = partiel(self.clip["effets"][i])
            a = min(a, duree_clip(self.clip))
            rc = QRectF(r.x() + de * self.tl.pps, yp, max(10.0, (a - de) * self.tl.pps), h)
            p.setPen(QPen(QColor("#5ad1ff") if actif else QColor(90, 209, 255, 110), 1.5))
            p.setBrush(QColor(20, 40, 60, 225) if actif else QColor(20, 40, 60, 120))
            p.drawRoundedRect(rc, 4, 4)
            p.setBrush(QColor("#5ad1ff"))
            p.setPen(Qt.NoPen)
            p.drawRect(QRectF(rc.left(), rc.top(), 3, h))
            p.drawRect(QRectF(rc.right() - 3, rc.top(), 3, h))
            p.setPen(QColor("#e6f7ff") if actif else QColor(170, 170, 170))
            lib = "✦ " + nom + ("" if actif else _(" (off)"))
            p.drawText(rc.adjusted(6, 0, -5, 0), Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(lib, Qt.ElideRight, int(max(0, rc.width() - 11))))
            self.chips.append((rc, "effet_partiel", i))
        if yp == y and partiels:
            return
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
        for rc, t_rel in getattr(self, "losanges", []):
            if rc.adjusted(-3, -3, 3, 3).contains(pos):
                return ("cle", t_rel)
        for rc, genre, i in self.chips:
            if genre == "effet_partiel" and rc.adjusted(-3, 0, 3, 0).contains(pos):
                if abs(pos.x() - rc.left()) <= 5:
                    return ("bord_de", i)
                if abs(pos.x() - rc.right()) <= 5:
                    return ("bord_a", i)
                return ("effet", i)
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
        if isinstance(z, tuple) and z[0] == "cle":
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip(_("Image clef : clic pour y aller, clic droit pour la supprimer"))
        elif isinstance(z, tuple) and z[0] in ("bord_de", "bord_a"):
            self.setCursor(Qt.SizeHorCursor)
            self.setToolTip(_("Tirez pour changer où l'effet commence ou finit"))
        elif isinstance(z, tuple) or z == "transition":
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip(_("Clic : régler · clic droit : désactiver, supprimer") if isinstance(z, tuple) else
                            _("Transition : clic pour régler, tirez le bord droit pour la durée, clic droit pour changer ou supprimer"))
        elif self.verrou:
            self.setToolTip(_("Piste verrouillée : déverrouillez-la (🔒 sous le nom de la piste) pour modifier ce plan"))
            self.setCursor(Qt.ForbiddenCursor)
        else:
            self.setToolTip(_("Tirez un bord pour rogner · glissez pour déplacer · double-clic : effets") if z == "deplacer" else
                            _("Tirez pour rogner (raccourcir ou rallonger) le plan"))
            self.setCursor(Qt.SizeHorCursor if z != "deplacer" else Qt.OpenHandCursor)
        self.update()
        super().hoverMoveEvent(e)

    def hoverLeaveEvent(self, e):
        self.update()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        z = self._zone(e.pos())
        if isinstance(z, tuple) and z[0] == "cle":
            if e.button() == Qt.LeftButton:
                self.tl.aller_a(self.clip["debut"] + z[1])
                self.tl.element_clique.emit(self.clip["id"], "clip", 0)
            e.accept()
            self.mode = None
            return
        if e.button() == Qt.LeftButton and isinstance(z, tuple) and z[0] in ("bord_de", "bord_a") and not self.verrou:
            self.tl.projet.marquer()
            self.mode = z
            self.tl._scene.clearSelection()
            self.setSelected(True)
            e.accept()
            return
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
        if self.verrou and z in ("gauche", "droite", "transition_bord", "deplacer"):
            self.tl._scene.clearSelection()
            self.setSelected(True)
            self.mode = None
            e.accept()
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
        if isinstance(self.mode, tuple):           # bord d'un effet posé sur une partie du plan
            ef = self.clip["effets"][self.mode[1]]
            t = max(0.0, min(duree_clip(self.clip), (e.scenePos().x() - self.scenePos().x()) / self.tl.pps))
            if self.mode[0] == "bord_de":
                ef["de"] = round(min(t, float(ef.get("a") or duree_clip(self.clip)) - 0.1), 2)
            else:
                ef["a"] = round(max(t, float(ef.get("de") or 0.0) + 0.1), 2)
            self.tl._info_rognage = (self.clip["debut"] + t, _("Effet de {a} à {b}", a=_tc(self.clip["debut"] + float(ef.get("de") or 0)),
                                                                  b=_tc(self.clip["debut"] + float(ef.get("a") or duree_clip(self.clip)))))
            self.update()
            self.tl.viewport().update()
            return
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
            bord = self.clip["debut"] if self.mode == "gauche" else fin_clip(self.clip)
            src = self.clip["src_debut"] if self.mode == "gauche" else self.clip["src_fin"]
            self.tl._info_rognage = (bord, _("{q} dans le rush : {t} · durée {d:.1f} s", q=_("Début") if self.mode == "gauche" else _("Fin"),
                                                 t=_tc(src), d=duree_clip(self.clip)))
            self.tl.viewport().update()
            return
        super().mouseMoveEvent(e)
        # deplacement : instant aimante ; vers le haut ou le bas, le plan change de piste (même genre : vidéo ou son)
        t = max(0.0, (self.pos().x() - MARGE_G) / self.tl.pps)
        t = self.tl.aimanter(t, self.clip)
        self._piste_cible = self.tl.piste_compatible(self.clip, e.scenePos().y())
        y = self.tl._pistes()[self._piste_cible][0] if self._piste_cible else self.piste_y
        self.setPos(MARGE_G + t * self.tl.pps, y + 3)
        self.tl._info_rognage = (t, _("→ {p}", p=self.tl.libelle_piste(self._piste_cible))) if self._piste_cible else None

    def mouseReleaseEvent(self, e):
        self.tl._info_rognage = None
        self.tl._trait_aimant = None
        if isinstance(self.mode, tuple):
            self.mode = None
            self.tl.modifie.emit()
            self.tl.element_change.emit(self.clip["id"])
            self.tl.reconstruire()
            return
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
        cible = getattr(self, "_piste_cible", None)
        self._piste_cible = None
        if cible:
            self.clip["debut"] = t
            self.tl.changer_piste(self.clip, cible)
        elif abs(t - self.clip["debut"]) > 1e-3:
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
        if isinstance(z, tuple) and z[0] == "cle":
            self.tl.menu_cle(self.clip, z[1], e.screenPos())
            return
        if isinstance(z, tuple) and z[0] in ("bord_de", "bord_a"):
            z = ("effet", z[1])
        if isinstance(z, tuple):
            self.tl.menu_effet(self.clip, z[0], z[1], e.screenPos())
        elif z in ("transition", "transition_bord"):
            self.tl.menu_transition(self.clip, e.screenPos())
        else:
            self.tl.menu_clip(self.clip, e.screenPos(), max(0.0, (e.scenePos().x() - MARGE_G) / self.tl.pps))


def nb_lignes_multiples(item):
    return item.h < H_CALQUE - 4


class ItemCalque(QGraphicsRectItem):
    """Titre ou Goodie : une barre fine deplacable."""

    def __init__(self, timeline, elem, genre, y, rang=0, nb=1):
        super().__init__()
        self.tl, self.elem, self.genre = timeline, elem, genre
        hp = timeline._h_calque("titres" if genre == "titre" else "goodies")
        self.h = max(5.0, (hp - 4) / max(1, nb))              # éléments qui se chevauchent : rangés sur des sous-lignes
        self.y0 = y + rang * self.h
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setAcceptHoverEvents(True)
        self._bord = None                        # « g » ou « d » : on tire un bord pour changer la durée (0.9.31)
        self.placer()

    def _zone_bord(self, pos):
        r = self.rect()
        if r.width() < 3 * BORD:
            return "d" if pos.x() > r.width() / 2 else None
        if pos.x() <= BORD:
            return "g"
        if pos.x() >= r.width() - BORD:
            return "d"
        return None

    def hoverMoveEvent(self, e):
        b = self._zone_bord(e.pos())
        self.setCursor(Qt.SizeHorCursor if b else Qt.OpenHandCursor)
        self.setToolTip(_("Tirez ce bord pour changer la durée") if b else _("Glissez pour déplacer · tirez un bord pour la durée · "
                                                                              "double-clic : réglages"))
        super().hoverMoveEvent(e)

    def placer(self):
        self.setRect(0, 0, max(6.0, (self.elem["fin"] - self.elem["debut"]) * self.tl.pps), self.h - (1 if nb_lignes_multiples(self) else 0))
        self.setPos(MARGE_G + self.elem["debut"] * self.tl.pps, self.y0 + 2)

    def paint(self, p, opt, w=None):
        r = self.rect()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#ffd36b"), 2) if self.isSelected() else Qt.NoPen)
        zone = self.elem.get("genre") == "zone"
        p.setBrush(QColor("#b0186b") if self.genre == "titre" else QColor("#1f6f99") if zone else QColor("#a35c00"))
        p.drawRoundedRect(r, 4, 4)
        p.setPen(QColor("#fff"))
        f = QFont()
        f.setPointSizeF(8)
        p.setFont(f)
        if zone:
            from . import zones as Z
            texte = Z.libelle(self.elem)
        elif self.genre == "titre":
            texte = self.elem.get("texte")
        else:
            from . import goodies as GO
            texte = GO.GENRES.get(self.elem.get("genre"), (self.elem.get("genre", ""),))[0]
        if r.height() < 11:
            f.setPointSizeF(6.5)
            p.setFont(f)
        p.drawText(r.adjusted(5, 0, -4, 0), Qt.AlignLeft | Qt.AlignVCenter, QFontMetrics(f).elidedText(texte or "", Qt.ElideRight, int(r.width() - 9)))
        self.losanges = _losanges(p, self.elem, r.x(), r.center().y(), self.tl.pps, 8) if self.elem.get("cles") else []

    def _losange(self, pos):
        return next((t for rc, t in getattr(self, "losanges", []) if rc.adjusted(-3, -3, 3, 3).contains(pos)), None)

    def mousePressEvent(self, e):
        t = self._losange(e.pos())
        if t is not None and e.button() == Qt.LeftButton:
            self.tl.aller_a(self.elem["debut"] + t)
            self.tl.element_clique.emit(self.elem["id"], "calque", 0)
            e.accept()
            self._sur_cle = True
            return
        self._sur_cle = False
        self.tl.projet.marquer()
        self._bord = self._zone_bord(e.pos()) if e.button() == Qt.LeftButton else None
        if self._bord:
            self.setSelected(True)
            self.tl.element_clique.emit(self.elem["id"], "calque", 0)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._bord:
            t = max(0.0, (self.mapToScene(e.pos()).x() - MARGE_G) / self.tl.pps)
            if getattr(self.tl, "aimant", None) and hasattr(self.tl, "aimanter"):
                try:
                    t = self.tl.aimanter(t)
                except Exception:     # noqa: BLE001
                    pass
            if self._bord == "g":
                self.elem["debut"] = min(t, self.elem["fin"] - 0.2)
            else:
                self.elem["fin"] = max(t, self.elem["debut"] + 0.2)
            self.placer()
            self.tl._info_rognage = (t, _("Durée {d:.1f} s", d=self.elem["fin"] - self.elem["debut"]))
            self.tl.viewport().update()
            return
        super().mouseMoveEvent(e)
        t = max(0.0, (self.pos().x() - MARGE_G) / self.tl.pps)
        self.setPos(MARGE_G + t * self.tl.pps, self.y0 + 2)

    def mouseReleaseEvent(self, e):
        if getattr(self, "_sur_cle", False):
            self._sur_cle = False
            return
        if self._bord:
            self._bord = None
            self.tl._info_rognage = None
            self.tl.modifie.emit()
            self.tl.reconstruire()
            return
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
        t = self._losange(e.pos())
        if t is not None:
            self.tl.menu_cle(self.elem, t, e.screenPos())
            return
        m = QMenu()
        m.addAction(_("Régler dans l'Inspecteur"), lambda: self.tl.element_clique.emit(self.elem["id"], "calque", 0))
        if self.elem.get("genre") == "zone":
            suivie = bool((self.elem.get("suivi") or {}).get("positions"))
            m.addAction(_("Refaire le suivi depuis le début") if suivie else _("Suivre ce qu'elle couvre (analyse de l'image)"),
                        lambda: self.tl.demande_menu.emit(self.elem["id"], "zone_suivre"))
            if suivie:
                m.addAction(_("Corriger à la ligne rouge (retracer ici)"), lambda: self.tl.demande_menu.emit(self.elem["id"], "zone_retracer"))
                m.addAction(_("Figer (ne plus suivre)"), lambda: self.tl.demande_menu.emit(self.elem["id"], "zone_figer"))
            m.addSeparator()
            m.addAction(_("Supprimer"), lambda: self.tl.supprimer_element(self.elem["id"]))
            m.exec(e.screenPos())
            return
        m.addAction(_("Tous les réglages (fenêtre)…"), lambda: self.tl.proprietes.emit(self.elem["id"]))
        m.addAction(_("Accrocher à une personne (suit ses mouvements)…"), lambda: self.tl.demande_menu.emit(self.elem["id"], "accrocher"))
        if self.elem.get("suivi"):
            m.addAction(_("Corriger le suivi à la ligne rouge…"), lambda: self.tl.demande_menu.emit(self.elem["id"], "corriger"))
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
    effet_depose = Signal(str, str)         # clip_id, id de l'effet ou de la transition glissé depuis le catalogue
    message = Signal(str)                   # texte pour la barre d'information
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
        self.setMinimumHeight(H_REGLE + H_VIDEO + 24)       # la règle et la piste vidéo ; le reste défile (petits écrans)
        self.setFrameShape(QFrame.NoFrame)
        self.setBackgroundBrush(_c("fond"))
        self._glisse_curseur = False
        self._scene.selectionChanged.connect(self._selection)
        self.reconstruire()

    # ---- disposition des pistes
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if not hasattr(self, "_minut_taille"):
            from PySide6.QtCore import QTimer
            self._minut_taille = QTimer(self)
            self._minut_taille.setSingleShot(True)
            self._minut_taille.setInterval(120)
            self._minut_taille.timeout.connect(self._apres_redimension)
        if e.oldSize().height() != e.size().height():
            self._minut_taille.start()

    def _apres_redimension(self):
        """Hauteur visible changée : on ne reconstruit que si la disposition des pistes change, et jamais pendant un
        glissement (un élément ne doit pas disparaître sous la souris)."""
        if QApplication.mouseButtons() != Qt.NoButton:
            self._minut_taille.start()
            return
        sig = tuple(self._pistes().items())
        if sig != getattr(self, "_sig_pistes", None):
            self._sig_pistes = sig
            self.reconstruire()

    def _rangs_calques(self, cle):
        """Nombre de sous-lignes nécessaires pour que les textes (ou Goodies) qui se chevauchent restent tous visibles."""
        fins = []
        for e in sorted((self.projet.d.get(cle) or []) if self.projet else [], key=lambda x: x["debut"]):
            k = next((i for i, f in enumerate(fins) if f <= e["debut"] + 1e-3), None)
            if k is None:
                fins.append(e["fin"])
            else:
                fins[k] = e["fin"]
        return max(1, len(fins))

    def _h_calque(self, cle):
        return int(min(6 * 13 + 4, max(H_CALQUE, self._rangs_calques(cle) * 13 + 4)))

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
        rep = (lambda p_: self.projet.piste_repliee(p_)) if self.projet else (lambda p_: False)
        H_REPLIE = 18
        for p_ in reversed(pv[1:]):
            h = H_REPLIE if rep(p_) else h_sup
            out[p_] = (y, h)
            y += h
        h = H_REPLIE if rep("video") else self.h_video
        out["video"] = (y, h)
        y += h
        for i, p_ in enumerate(pa):
            h = H_REPLIE if rep(p_) else (H_AUDIO if i == 0 else int(max(32, H_AUDIO * tasse)))
            out[p_] = (y, h)
            y += h
        h = H_REPLIE if rep("voix") else H_VOIX
        out["voix"] = (y, h)
        y += h
        ht, hg = self._h_calque("titres"), self._h_calque("goodies")
        out["titre"] = (y, ht)
        y += ht
        out["goodie"] = (y, hg)
        # tout doit tenir dans la hauteur visible (petit écran) : les pistes se tassent jusqu'à 60 % ; au-delà, défilement
        dispo = self.viewport().height() - 8 if self.isVisible() else 0
        total = y + hg - H_REGLE
        if dispo > 0 and H_REGLE + total > dispo and self.h_video <= H_VIDEO:      # images agrandies à la main : on défile
            k = max(0.6, (dispo - H_REGLE) / max(1, total))
            y2, out2 = H_REGLE, {}
            for nom, (y0, h) in out.items():
                h2 = h if h <= 18 else max(14, int(h * k))
                out2[nom] = (y2, h2)
                y2 += h2
            out = out2
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
        perso = self.projet.nom_piste(nom) if self.projet else ""
        if perso:
            return perso
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
        self._sig_pistes = tuple(self._pistes().items())
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
            for liste, genre in ((self.projet.titres, "titre"), (self.projet.goodies, "goodie")):
                rangs, fins = {}, []
                for e in sorted(liste, key=lambda x: x["debut"]):       # rangement en sous-lignes sans chevauchement
                    k = next((i for i, f in enumerate(fins) if f <= e["debut"] + 1e-3), None)
                    if k is None:
                        fins.append(e["fin"])
                        k = len(fins) - 1
                    else:
                        fins[k] = e["fin"]
                    rangs[e["id"]] = k
                nb = min(6, max(1, len(fins)))
                for e in liste:
                    self._scene.addItem(ItemCalque(self, e, genre, pistes[genre][0], min(rangs[e["id"]], nb - 1), nb))
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
            p.drawText(QRectF(x + 3, 1, 80, 16), Qt.AlignLeft | Qt.AlignVCenter, _tc(t))
            for k in range(1, 5):
                xs = x + k * pas / 5 * self.pps
                p.drawLine(QLineF(xs, H_REGLE - 4, xs, H_REGLE))
            t += pas

    def drawForeground(self, p, r):
        dep = getattr(self, "_depot", None)
        if dep and self.projet:
            c = self.projet.clip(dep[0])
            it = self.items_clips.get(dep[0])
            if c and it:
                rc = it.sceneBoundingRect()
                if dep[1]:          # transition : le raccord s'allume
                    x = MARGE_G + c["debut"] * self.pps
                    p.fillRect(QRectF(x - 7, rc.top(), 14, rc.height()), QColor(255, 210, 74, 170))
                else:
                    p.setPen(QPen(QColor("#ffd24a"), 3))
                    p.setBrush(QColor(255, 210, 74, 50))
                    p.drawRoundedRect(rc.adjusted(1, 1, -1, -1), 5, 5)
        # barre de préparation : rouge = à préparer, orange = en cours, vert = prêt (lecture avec effets)
        etats = self.etats_preparation() if callable(getattr(self, "etats_preparation", None)) else []
        for a0, b0, etat in etats:
            couleur = {"pret": QColor("#4cd964"), "en_cours": QColor("#ffb347"), "a_preparer": QColor("#e05a5a")}[etat]
            p.fillRect(QRectF(MARGE_G + a0 * self.pps, H_REGLE - 5, max(2.0, (b0 - a0) * self.pps - 1), 4), couleur)
        # aimantation et rognage visibles pendant le glissement
        ta = getattr(self, "_trait_aimant", None)
        if ta is not None and QApplication.mouseButtons() & Qt.LeftButton:
            p.setPen(QPen(QColor("#5ad1ff"), 1.5, Qt.DashLine))
            x = MARGE_G + ta * self.pps
            p.drawLine(QLineF(x, H_REGLE, x, self.hauteur_totale()))
        info = getattr(self, "_info_rognage", None)
        if info:
            x = MARGE_G + info[0] * self.pps
            f = QFont()
            f.setPointSizeF(8)
            p.setFont(f)
            w = QFontMetrics(f).horizontalAdvance(info[1]) + 12
            rc = QRectF(x + 6, H_REGLE + 2, w, 16)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(20, 20, 26, 230))
            p.drawRoundedRect(rc, 4, 4)
            p.setPen(QColor("#ffd24a"))
            p.drawText(rc, Qt.AlignCenter, info[1])
            p.setPen(QPen(QColor("#ffd24a"), 1))
            p.drawLine(QLineF(x, H_REGLE, x, self.hauteur_totale()))
        vt = (self.projet.d.get("vignette_t") if self.projet else None)
        if vt is not None:                           # image choisie comme vignette du fichier : petit cadre sur la règle
            x = MARGE_G + float(vt) * self.pps
            rc = QRectF(x - 7, 3, 14, 10)
            p.setPen(QPen(QColor("#5ad1ff"), 1.4))
            p.setBrush(QColor(20, 30, 40, 220))
            p.drawRect(rc)
            p.drawLine(QLineF(rc.left() + 2, rc.bottom() - 2, rc.center().x(), rc.top() + 4))
            p.drawLine(QLineF(rc.center().x(), rc.top() + 4, rc.right() - 2, rc.bottom() - 2))
        a, b = self.zone
        if (a is None) != (b is None):              # seulement le début (ou la fin) : un fanion jaune l'indique
            t0 = a if a is not None else b
            x = MARGE_G + t0 * self.pps
            p.setPen(QPen(QColor("#ffd24a"), 2))
            p.drawLine(QLineF(x, 0, x, self.hauteur_totale()))
            f = QFont()
            f.setPointSizeF(7.5)
            f.setBold(True)
            p.setFont(f)
            lib = _("Début") if a is not None else _("Fin")
            w = QFontMetrics(f).horizontalAdvance(lib) + 10
            rcf = QRectF(x if a is not None else x - w, 2, w, 15)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ffd24a"))
            p.drawRoundedRect(rcf, 3, 3)
            p.setPen(QColor("#1a1a1a"))
            p.drawText(rcf, Qt.AlignCenter, lib)
        if a is not None and b is not None:          # partie sélectionnée : bande jaune sur la règle, voile sur les pistes
            xa = MARGE_G + (a if a is not None else b) * self.pps
            xb = MARGE_G + (b if b is not None else a) * self.pps
            p.fillRect(QRectF(xa, 0, max(2.0, xb - xa), H_REGLE), QColor(255, 210, 74, 150))
            p.fillRect(QRectF(xa, H_REGLE, max(2.0, xb - xa), self.hauteur_totale() - H_REGLE), QColor(255, 210, 74, 38))
            p.setPen(QPen(QColor("#ffd24a"), 1.5))
            for x in (xa, xb):
                p.drawLine(QLineF(x, 0, x, self.hauteur_totale()))
            # × pour enlever la sélection (aussi : simple clic sur la règle, Echap, clic droit)
            rc = QRectF(xb + 3, 1, 16, 16)
            self._croix_zone = rc
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(40, 40, 46, 230))
            p.drawRoundedRect(rc, 4, 4)
            p.setPen(QPen(QColor("#ffd24a"), 1.6))
            m = rc.width() * 0.3
            p.drawLine(QLineF(rc.left() + m, rc.top() + m, rc.right() - m, rc.bottom() - m))
            p.drawLine(QLineF(rc.right() - m, rc.top() + m, rc.left() + m, rc.bottom() - m))
        else:
            self._croix_zone = None
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
            compacte = h < 34 and nom not in ("titre", "goodie")        # piste tassée : boutons sur la ligne du nom
            larg_nom = MARGE_G - 12 if not compacte else 32
            lib = self.libelle_piste(nom)
            if compacte and not (self.projet and (self.projet.d.get("noms_pistes") or {}).get(nom)):
                lib = {"video": "V1", "voix": _("Voix")}.get(nom) or ("V" + nom[5:] if nom.startswith("video") else
                                                                     "M" + (nom[5:] or "1") if nom.startswith("audio") else lib)
            p.drawText(QRectF(x0 + 8, y + 2, larg_nom, min(h, 22)), Qt.AlignLeft | Qt.AlignVCenter,
                       QFontMetrics(f).elidedText(lib, Qt.ElideRight, int(larg_nom)))
            if nom in ("titre", "goodie") or not self.projet:
                continue
            # flèche pour replier / déplier la piste
            rf = QRectF(x0 + MARGE_G - 16, y + 3, 12, 12)
            p.setPen(_c("texte2"))
            p.drawText(rf, Qt.AlignCenter, "▸" if self.projet.piste_repliee(nom) else "▾")
            self._boutons_piste.setdefault(nom, []).append((rf, "repliee", _("Replier / déplier la piste"), self.projet.piste_repliee(nom)))
            if h < 16:
                continue
            # petits boutons : M = son coupé, S = solo, V = image masquée (vidéo 2+), 🔒 = verrou
            boutons = [("muette", "M", nom in (self.projet.d.get("pistes_muettes") or []), _("Son de la piste coupé (écoute et export)")),
                       ("solo", "S", self.projet.piste_solo(nom), _("Solo : on n'entend que cette piste (et les autres en solo)"))]
            if nom.startswith("video") and nom != "video":
                boutons.append(("masquee", "V", self.projet.piste_masquee(nom), _("Image de la piste masquée (écoute et export)")))
            boutons.append(("verrou", "🔒", self.projet.piste_verrouillee(nom), _("Piste verrouillée : ses plans ne bougent plus (ni déplacés, ni rognés, ni supprimés)")))
            if compacte:                                       # place pour M et S ; le reste par clic droit › Pistes
                boutons = boutons[:2]
            bx = x0 + 8 if not compacte else x0 + 42
            by = y + h - 20 if not compacte else y + max(1.0, (min(h, 22) - 14) / 2 + 1)
            fb = QFont()
            fb.setPointSizeF(7.5)
            fb.setBold(True)
            p.setFont(fb)
            for quoi, lettre, actif, aide in boutons:
                rc = QRectF(bx, by, 16 if not compacte else 12, 14)
                p.setPen(Qt.NoPen)
                p.setBrush({"muette": QColor("#e05a5a"), "solo": QColor("#e0b84a"), "masquee": QColor("#e05a5a"),
                            "verrou": QColor("#5a8ae0")}.get(quoi, QColor("#e05a5a")) if actif else QColor(255, 255, 255, 28))
                p.drawRoundedRect(rc, 3, 3)
                p.setPen(QColor("#ffffff") if actif else _c("texte2"))
                p.drawText(rc, Qt.AlignCenter, lettre)
                self._boutons_piste.setdefault(nom, []).append((rc, quoi, aide, actif))
                bx += 18 if not compacte else 13
        # curseur de lecture
        x = MARGE_G + self.position * self.pps
        p.setPen(QPen(QColor("#ff5c5c"), 2))
        p.drawLine(QLineF(x, 0, x, self.hauteur_totale()))
        p.setBrush(QColor("#ff5c5c"))
        p.setPen(Qt.NoPen)
        p.drawPolygon([QPointF(x - 6, 0), QPointF(x + 6, 0), QPointF(x, 9)])
        # [ ] à côté de la tête : la partie jaune commence / finit ici (à la souris, sans raccourci à retenir)
        f = QFont()
        f.setPointSizeF(9)
        f.setBold(True)
        p.setFont(f)
        self._boutons_tete = []
        for i, (dx, sym) in enumerate(((-21, "["), (5, "]"))):
            rcb = QRectF(x + dx, 19, 16, 15)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 92, 92, 215))
            p.drawRoundedRect(rcb, 3, 3)
            p.setPen(QColor("#ffffff"))
            p.drawText(rcb.adjusted(0, -1, 0, 0), Qt.AlignCenter, sym)
            self._boutons_tete.append(rcb)
        self._dessiner_rappel_zoom(p)

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
                self._trait_aimant = x          # montré par un trait pendant le glissement
                return x
        self._trait_aimant = None
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

    def mouseDoubleClickEvent(self, e):
        sp = self.mapToScene(e.pos())
        if e.button() == Qt.LeftButton and sp.y() < H_REGLE and sp.x() >= MARGE_G:
            self.double_clic_regle((sp.x() - MARGE_G) / self.pps)
            return
        if sp.x() < MARGE_G and self.projet:
            piste = self.piste_a(sp.y())
            if piste in self.projet.toutes_pistes():
                self._renommer_piste(piste)
                return
        super().mouseDoubleClickEvent(e)

    def _renommer_piste(self, piste):
        from PySide6.QtWidgets import QInputDialog
        nom, ok = QInputDialog.getText(self, _("Nom de la piste"), _("Nom affiché pour « {p} » (vide = nom d'origine) :", p=self.libelle_piste(piste)),
                                       text=self.projet.nom_piste(piste))
        if ok:
            self.projet.marquer()
            self.projet.renommer_piste(piste, nom)
            self.modifie.emit()
            self.viewport().update()

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
        cz = getattr(self, "_croix_zone", None)
        if e.button() == Qt.LeftButton and cz is not None and cz.adjusted(-2, -2, 2, 2).contains(sp):
            self.effacer_zone()
            return
        # coin en haut à gauche : rappel « molette = zoom » ; un clic montre tout le montage
        if e.button() == Qt.LeftButton and self._rect_zoom().contains(e.position()):
            self.ajuster()
            self._animer_zoom()
            return
        # petits boutons [ ] à côté de la tête rouge : début / fin de la partie jaune ici
        for i, rc in enumerate(getattr(self, "_boutons_tete", []) or []):
            if e.button() == Qt.LeftButton and rc.contains(sp):
                self.marquer_zone(i)
                return
        # bord de la partie jaune : on le tire pour l'ajuster
        bord = self._bord_zone_a(sp)
        if e.button() == Qt.LeftButton and bord is not None:
            self._tire_bord = bord
            self.balayage.emit(True)
            return
        if e.button() == Qt.LeftButton and (sp.y() < H_REGLE or self.itemAt(e.pos()) is None) and sp.x() >= MARGE_G:
            # un clic ou un glissement déplace toujours la ligne rouge rouge (jamais de sélection par erreur) ;
            # la partie jaune se fait par double-clic sur la règle (début puis fin), par [ ] ou Maj + glisser sur la règle
            self._glisse_curseur = True
            self.balayage.emit(True)
            maj = bool(e.modifiers() & Qt.ShiftModifier)
            self._depart_regle = (e.pos().x(), (sp.x() - MARGE_G) / self.pps) if sp.y() < H_REGLE and maj else None
            self.aller_a((sp.x() - MARGE_G) / self.pps)
            if self.itemAt(e.pos()) is None:
                self._scene.clearSelection()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        tb = getattr(self, "_tire_bord", None)
        if tb is not None:
            sp = self.mapToScene(e.pos())
            t = self.aimanter(max(0.0, (sp.x() - MARGE_G) / self.pps))
            self.zone[tb] = t
            self.aller_a(t)
            self.viewport().update()
            return
        if self._glisse_curseur:
            sp = self.mapToScene(e.pos())
            t = max(0.0, (sp.x() - MARGE_G) / self.pps)
            dep = getattr(self, "_depart_regle", None)
            if dep and abs(e.pos().x() - dep[0]) > 6:
                self.zone = sorted([dep[1], t])
                self.viewport().update()
            self.aller_a(t)
            return
        sp = self.mapToScene(e.pos())
        # le curseur dit ce que fera le clic : flèche double sur un bord jaune, main sur [ ] et le coin zoom
        if self._bord_zone_a(sp) is not None:
            self.viewport().setCursor(Qt.SizeHorCursor)
        elif self._rect_zoom().contains(e.position()) or any(rc.contains(sp) for rc in getattr(self, "_boutons_tete", []) or []):
            self.viewport().setCursor(Qt.PointingHandCursor)
        elif sp.y() < H_REGLE and sp.x() >= MARGE_G:
            self.viewport().setCursor(Qt.SplitHCursor if abs(sp.x() - (MARGE_G + self.position * self.pps)) <= 9 else Qt.ArrowCursor)
        else:
            self.viewport().unsetCursor()
        aide = None                                   # bulle d'aide selon l'endroit survolé
        if self._rect_zoom().contains(e.position()):
            aide = _("Molette : zoom sur la timeline (là où est la souris) · Maj + molette : défiler · clic ici : tout voir")
        elif any(rc.contains(sp) for rc in getattr(self, "_boutons_tete", []) or []):
            aide = _("[ : la partie jaune commence à la ligne rouge · ] : elle finit ici")
        elif self._bord_zone_a(sp) is not None:
            aide = _("Tirer ce bord pour ajuster la partie jaune")
        elif sp.y() < H_REGLE:
            aide = _("Clic ou glisser : déplacer la ligne rouge · double-clic : début, puis fin de la partie jaune · "
                     "molette : zoom")
        if aide != getattr(self, "_aide_regle", None):
            self._aide_regle = aide
            self.viewport().setToolTip(aide or "")
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if getattr(self, "_tire_bord", None) is not None:
            self._tire_bord = None
            a, b = self.zone
            if a is not None and b is not None and b < a:
                self.zone = [b, a]
            self.balayage.emit(False)
            self.zone_changee.emit()
            self.viewport().update()
            return
        dep = getattr(self, "_depart_regle", None)
        if self._glisse_curseur and dep and self.zone_valide():
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
        if clip["piste"].startswith("video"):
            m.addAction(_("Étalonnage (couleurs, avant / après)…"), lambda: self.demande_menu.emit(clip["id"], "etalonner"))
            m.addAction(_("Prolonger ce plan (image tenue, ralenti ou IA)…"), lambda: self.demande_menu.emit(clip["id"], "prolonger"))
        m.addAction(_("Couper ici"), lambda: (self.aller_a(t), self.couper_au_curseur()))
        self._menu_pistes(m, piste)
        m.addAction(_("Enregistrer l'image à cet endroit…"), lambda: (self.aller_a(t), self.demande_menu.emit("", "image")))
        m.addAction(_("Insérer un tampon vidéo ici…"), lambda: (self.aller_a(t), self.demande_menu.emit("", "tampon")))
        self._menu_partie(m, t)
        self._menu_zoom(m)
        m.exec(e.globalPos())

    def _menu_pistes(self, m, piste):
        """Ajouter ou retirer des pistes : une vidéo au-dessus (B-roll, image dans l'image), une musique de plus."""
        if not self.projet:
            return
        m.addSeparator()
        sm = m.addMenu(_("Pistes"))
        if piste and piste in self.projet.toutes_pistes():
            sm.addAction(_("Renommer « {p} »…", p=self.libelle_piste(piste)), lambda: self._renommer_piste(piste))
            for quoi, lib in (("muette", _("Son coupé")), ("solo", _("Solo")), ("verrou", _("Verrouillée")), ("repliee", _("Repliée"))):
                etat = {"muette": nom_in(self.projet, "pistes_muettes", piste), "solo": self.projet.piste_solo(piste),
                        "verrou": self.projet.piste_verrouillee(piste), "repliee": self.projet.piste_repliee(piste)}[quoi]
                a = sm.addAction(lib, lambda quoi=quoi: self._basculer(piste, quoi))
                a.setCheckable(True)
                a.setChecked(etat)
            sm.addSeparator()
        if len(self.projet.pistes_video()) < 4:
            sm.addAction(_("Ajouter une piste vidéo au-dessus (incrustation, image dans l'image)"), lambda: self._ajouter_piste("video"))
        if len(self.projet.pistes_audio()) < 4:
            sm.addAction(_("Ajouter une piste de musique ou de sons"), lambda: self._ajouter_piste("audio"))
        if piste and piste in self.projet.toutes_pistes() and piste not in ("video", "audio", "voix"):
            a = sm.addAction(_("Retirer la piste « {p} » (vide seulement)", p=self.libelle_piste(piste)), lambda: self._retirer_piste(piste))
            a.setEnabled(not self.projet.clips_piste(piste))

    def _basculer(self, piste, quoi):
        self.projet.marquer()
        self.projet.basculer_piste(piste, quoi)
        self.modifie.emit()
        self.reconstruire()

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
        if self.projet:
            m.addAction(_("Prendre cette image comme vignette du fichier"), lambda: (self.aller_a(t), self.demande_menu.emit("", "vignette")))
            m.addAction(_("Composer une vignette YouTube depuis cette image…"), lambda: (self.aller_a(t), self.demande_menu.emit("", "vignette_nouvelle")))
            if self.projet.d.get("vignette_t") is not None:
                m.addAction(_("Retirer la vignette choisie"), lambda: self.demande_menu.emit("", "vignette_retirer"))
        if self.zone != [None, None]:
            m.addAction(_("Enlever la partie jaune (sélection)"), self.effacer_zone)
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
        if (e.modifiers() & Qt.ControlModifier or e.position().x() < MARGE_G) and e.angleDelta().y():
            # Ctrl + molette, ou molette sur les noms des pistes : monter / descendre dans les pistes (0.9.31)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - e.angleDelta().y())
            return
        if e.modifiers() & Qt.AltModifier:
            d = e.angleDelta().y() or e.angleDelta().x()        # Alt fait parfois passer la molette en horizontal
            self.hauteur_images(1.15 if d > 0 else 1 / 1.15)
        elif e.modifiers() & Qt.ShiftModifier or (e.angleDelta().x() and not e.angleDelta().y()):
            d = e.angleDelta().y() or e.angleDelta().x()          # Maj + molette, ou molette horizontale : défiler
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d)
        elif e.angleDelta().y():
            self.zoomer(1.2 if e.angleDelta().y() > 0 else 1 / 1.2, e.position().x())     # molette : zoom là où est la souris
            self._animer_zoom(e.angleDelta().y() > 0)

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
            self.effacer_zone()
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

    def effacer_zone(self):
        self.zone = [None, None]
        self._croix_zone = None
        self.zone_changee.emit()
        self.viewport().update()

    def double_clic_regle(self, t):
        """Double-clic sur la règle : 1er = début de la partie jaune, 2e = fin ; un 3e recommence une nouvelle partie."""
        t = self.aimanter(max(0.0, t))
        self.aller_a(t)
        a, b = self.zone
        if a is not None and b is not None:
            self.zone = [t, None]
        elif a is None and b is None:
            self.zone = [t, None]
        else:
            debut = a if a is not None else b
            self.zone = sorted([debut, t])
        self.zone_changee.emit()
        self.viewport().update()

    def _bord_zone_a(self, sp):
        a, b = self.zone
        if a is None or b is None:
            return None
        for i, t in enumerate((a, b)):
            if abs(sp.x() - (MARGE_G + t * self.pps)) <= 5 and sp.y() < H_REGLE:
                return i
        return None

    def _rect_zoom(self):
        """Coin du rappel « molette = zoom », en coordonnées de la vue (fixe à gauche, sur la ligne de la règle)."""
        return QRectF(4, 6, MARGE_G - 8, H_REGLE - 12)

    def _animer_zoom(self, avant=True):
        from PySide6.QtCore import QVariantAnimation
        self._zoom_avant = avant
        a = getattr(self, "_anim_zoom", None)
        if a is None:
            a = QVariantAnimation(self)
            a.setDuration(700)
            a.setStartValue(0.0)
            a.setEndValue(1.0)
            a.valueChanged.connect(lambda v: (setattr(self, "_phase_zoom", float(v)), self.viewport().update()))
            a.finished.connect(lambda: (setattr(self, "_phase_zoom", None), self.viewport().update()))
            self._anim_zoom = a
        a.stop()
        a.start()

    def _dessiner_rappel_zoom(self, p):
        """Petite souris avec sa molette et une loupe ; s'anime quand on zoome. Dessiné en coordonnées de la vue."""
        p.save()
        p.resetTransform()
        rc = self._rect_zoom()
        phase = getattr(self, "_phase_zoom", None)
        actif = phase is not None
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 210, 74, 60) if actif else QColor(255, 255, 255, 18))
        p.drawRoundedRect(rc, 5, 5)
        coul = QColor("#ffd24a") if actif else _c("texte2")
        # souris
        sx, sy = rc.left() + 8, rc.top() + 3
        p.setPen(QPen(coul, 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(sx, sy, 10, rc.height() - 6), 5, 5)
        dy = (math.sin((phase or 0) * math.pi * 3) * 2.5) if actif else 0
        p.drawLine(QLineF(sx + 5, sy + 3 + dy, sx + 5, sy + 6 + dy))
        # loupe + / −
        lx, ly = sx + 17, rc.top() + 4
        k = 1 + (0.25 * math.sin((phase or 0) * math.pi)) if actif else 1
        r = 5 * k
        p.drawEllipse(QPointF(lx + 5, ly + 5), r, r)
        p.drawLine(QLineF(lx + 5 + r * 0.7, ly + 5 + r * 0.7, lx + 5 + r * 1.5, ly + 5 + r * 1.5))
        p.drawLine(QLineF(lx + 3, ly + 5, lx + 7, ly + 5))
        if not actif or getattr(self, "_zoom_avant", True):
            p.drawLine(QLineF(lx + 5, ly + 3, lx + 5, ly + 7))
        f = QFont()
        f.setPointSizeF(7.5)
        f.setBold(True)
        p.setFont(f)
        p.setPen(coul)
        p.drawText(QRectF(lx + 16, rc.top(), rc.right() - lx - 17, rc.height()), Qt.AlignVCenter | Qt.AlignLeft, _("Zoom"))
        p.restore()

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
            if self.projet.piste_verrouillee(piste):
                continue
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
        ids = [i for i in ids if not self.projet.piste_verrouillee((self.projet.clip(i) or {}).get("piste", ""))]
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
        if clip.get("vignette"):
            m.addAction(_("Modifier l'image composée…"), lambda: self.demande_menu.emit(clip["id"], "vignette_composee"))
        med = self.projet.media(clip["media"]) if self.projet else None
        if (med or {}).get("genre") == "image" and not clip.get("vignette"):
            m.addAction(_("Retirer le fond de l'image…"), lambda: self.demande_menu.emit(clip["id"], "fond_retirer"))
            m.addSeparator()
        if med and med.get("chemin"):
            from .creations import lire as _recette
            if _recette(med["chemin"]):
                m.addAction(_("Modifier la création IA (phrase, paroles, durée)…"), lambda: self.demande_menu.emit(clip["id"], "recreer_ia"))
            m.addAction(_("Enregistrer une copie du fichier sous…"), lambda: self.demande_menu.emit(clip["id"], "copie"))
            m.addSeparator()
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
                sm.addAction(_("Corriger le suivi à la ligne rouge…"), lambda: self.demande_menu.emit(clip["id"], "corriger"))
        a = m.addAction(_("Muet"), lambda: self._muet(clip))
        a.setCheckable(True)
        a.setChecked(bool(clip.get("muet")))
        m.addSeparator()
        m.addAction(_("Effets et transition sur tout le plan…"), lambda: self.demande_menu.emit(clip["id"], "effets"))
        if clip.get("effets"):
            m.addAction(_("Copier les effets de ce plan ({n})", n=len(clip["effets"])), lambda: self.copier_effets(clip))
        if getattr(self, "presse_effets", None):
            m.addAction(_("Coller les effets ({n})", n=len(self.presse_effets)), lambda: self.coller_effets(clip))
        soeurs = self._pistes_soeurs(clip)
        if soeurs:
            sp = m.addMenu(_("Déplacer vers la piste"))
            for p in soeurs:
                sp.addAction(self.libelle_piste(p), lambda p=p: (self.projet.marquer(), self.changer_piste(clip, p)))
        if self.zone_valide():
            m.addAction(_("Effets sur la partie en jaune seulement…"), lambda: self.demande_menu.emit(clip["id"], "effets_partie"))
        m.addAction(_("Enregistrer l'image à cet endroit…"), lambda: (self.aller_a(t), self.demande_menu.emit("", "image")))
        m.addAction(_("Insérer un tampon vidéo ici…"), lambda: (self.aller_a(t), self.demande_menu.emit("", "tampon")))
        if clip["piste"] == "video":
            m.addAction(_("Figer l'image à cet endroit (cadre photo, légende)…"), lambda: (self.aller_a(t), self.demande_menu.emit(clip["id"], "figer")))
        else:
            m.addAction(_("Couper ce son à la fin de la vidéo"), lambda: self.demande_menu.emit(clip["id"], "son_fin"))
        self._menu_partie(m, t)
        self._menu_zoom(m)
        m.addSeparator()
        m.addAction(_("Tous les effets et transitions (fenêtre)…"), lambda: self.proprietes.emit(clip["id"]))
        m.exec(pos)

    # ---- images clefs
    def menu_cle(self, elem, t_rel, pos):
        from . import cles as K
        m = QMenu()
        m.addAction(_("Aller à cette image clef ({t})", t=_tc(K.base(elem) + t_rel)), lambda: self.aller_a(K.base(elem) + t_rel))

        def suppr():
            self.projet.marquer()
            K.retirer(elem, t_rel)
            self.modifie.emit()
            self.reconstruire()
            self.element_change.emit(elem["id"])
        m.addAction(_("Supprimer cette image clef"), suppr)
        m.exec(pos)

    # ---- changer de piste
    @staticmethod
    def _famille_piste(nom):
        return "video" if (nom or "").startswith("video") else "son"

    def piste_compatible(self, clip, y):
        """Piste (autre que la sienne) où le plan peut aller s'il est lâché à la hauteur y, ou None."""
        if not self.projet:
            return None
        p = self.piste_a(y)
        if not p or p == clip["piste"] or p not in self.projet.toutes_pistes():
            return None
        if self._famille_piste(p) != self._famille_piste(clip["piste"]) or self.projet.piste_verrouillee(p):
            return None
        return p

    def changer_piste(self, clip, cible):
        """Le plan passe sur la piste `cible` (même genre), à son instant actuel ; une piste vidéo 2+ en fait une incrustation."""
        ancienne = clip["piste"]
        clip["piste"] = cible
        if cible.startswith("video") and cible != "video":
            clip.setdefault("incrust", {"echelle": 1.0, "x": 0.5, "y": 0.5, "opacite": 1.0})
        self.projet.ranger(cible)
        self.projet.ranger(ancienne)
        self.modifie.emit()
        self.reconstruire()

    def _pistes_soeurs(self, clip):
        return [p for p in self.projet.toutes_pistes() if p != clip["piste"] and self._famille_piste(p) == self._famille_piste(clip["piste"])
                and not self.projet.piste_verrouillee(p)]

    # ---- copier / coller des effets
    def copier_effets(self, clip, i=None):
        import copy as _copie
        effets = clip.get("effets") or []
        self.presse_effets = [_copie.deepcopy(effets[i])] if i is not None else _copie.deepcopy(effets)
        from . import effets as E
        noms = ", ".join((E.fiche(e["id"]) or {"nom": e["id"]})["nom"] for e in self.presse_effets)
        self.message.emit(_("Copié : {n}. Clic droit sur un autre plan › « Coller les effets ».", n=noms))

    def coller_effets(self, clip):
        import copy as _copie
        if not getattr(self, "presse_effets", None):
            return
        self.projet.marquer()
        clip.setdefault("effets", [])
        for e in self.presse_effets:
            clip["effets"].append(_copie.deepcopy(e))
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

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
            m.addAction(_("Copier cet effet"), lambda: self.copier_effets(clip, i))
            from .projet import partiel
            if partiel(e):
                m.addAction(_("Sur tout le plan"), lambda: self._partie_effet(clip, i, None))
            else:
                m.addAction(_("Sur une partie du plan (repères à tirer)"), lambda: self._partie_effet(clip, i, "milieu"))
            z = self.zone_valide()
            if z and z[1] > clip["debut"] and z[0] < fin_clip(clip):
                m.addAction(_("Seulement sur la partie en jaune"), lambda: self._partie_effet(clip, i, z))
        m.addSeparator()
        m.addAction(_("Supprimer « {n} »", n=nom), lambda: self._supprimer_effet(clip, genre, i))
        m.exec(pos)

    def _partie_effet(self, clip, i, partie):
        """partie : None = tout le plan ; "milieu" = le tiers du milieu ; (a, b) en temps du montage."""
        self.projet.marquer()
        e = clip["effets"][i]
        d = duree_clip(clip)
        if partie is None:
            e.pop("de", None)
            e.pop("a", None)
        elif partie == "milieu":
            e["de"], e["a"] = round(d / 3, 2), round(2 * d / 3, 2)
        else:
            e["de"], e["a"] = round(max(0.0, partie[0] - clip["debut"]), 2), round(min(d, partie[1] - clip["debut"]), 2)
        self.modifie.emit()
        self.reconstruire()
        self.element_change.emit(clip["id"])

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
        m.addSeparator()
        m.addAction(_("Ajouter un bruitage « whoosh » sur le raccord"), lambda: self.demande_menu.emit(clip["id"], "whoosh"))
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

    # ---- depot d'un effet ou d'une transition du catalogue
    def cible_effet(self, sp, eid):
        """Plan qui recevra l'effet (ou la transition) lâché au point sp de la scène, ou (None, raison)."""
        from . import effets as E
        if not self.projet:
            return None, ""
        fi = E.fiche(eid) or {}
        piste = self.piste_a(sp.y())
        if not (piste or "").startswith("video"):
            return None, _("Lâchez l'effet sur un plan d'une piste vidéo.")
        t = (sp.x() - MARGE_G) / self.pps
        clips = sorted(self.projet.clips_piste(piste), key=lambda c: c["debut"])
        if fi.get("famille") == "transition":
            # la transition va au plan qui ARRIVE : le raccord le plus proche du point lâché
            tol = max(0.4, 18 / self.pps)
            proches = [c for c in clips[1:] if abs(c["debut"] - t) <= tol]
            if proches:
                return min(proches, key=lambda c: abs(c["debut"] - t)), ""
            c = next((c for c in clips if c["debut"] <= t < fin_clip(c)), None)
            if c is None:
                return None, _("Lâchez la transition sur un raccord entre deux plans.")
            if c is clips[0]:
                return None, _("C'est le premier plan : une transition se pose sur un raccord, entre deux plans.")
            return c, ""
        c = next((c for c in clips if c["debut"] <= t < fin_clip(c)), None)
        return (c, "") if c else (None, _("Lâchez l'effet sur un plan."))

    def _effet_glisse(self, e):
        try:
            return bytes(e.mimeData().data(MIME_EFFET)).decode("utf-8")
        except Exception:       # noqa: BLE001
            return ""

    def dragLeaveEvent(self, e):
        self._depot = None
        self.viewport().update()
        super().dragLeaveEvent(e)

    # ---- depot depuis la bibliotheque
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME_EFFET):
            e.acceptProposedAction()
            return
        if e.mimeData().hasFormat(MIME_MEDIA) or e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(MIME_EFFET):
            sp = self.mapToScene(e.position().toPoint())
            eid = self._effet_glisse(e)
            c, raison = self.cible_effet(sp, eid)
            from . import effets as E
            trans = (E.fiche(eid) or {}).get("famille") == "transition"
            self._depot = (c["id"], trans) if c else None
            self._depot_raison = raison
            self.viewport().update()
            if c:
                e.acceptProposedAction()
            else:
                e.ignore()
            return
        if e.mimeData().hasFormat(MIME_MEDIA) or e.mimeData().hasUrls():
            sp = self.mapToScene(e.position().toPoint())
            self.aller_a(max(0.0, self.aimanter((sp.x() - MARGE_G) / self.pps)), emettre=False)
            e.acceptProposedAction()

    def dropEvent(self, e):
        sp = self.mapToScene(e.position().toPoint())
        if e.mimeData().hasFormat(MIME_EFFET):
            eid = self._effet_glisse(e)
            c, _r = self.cible_effet(sp, eid)
            self._depot = None
            self.viewport().update()
            if c:
                self.effet_depose.emit(c["id"], eid)
                e.acceptProposedAction()
            return
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


def nom_in(projet, cle, piste):
    return piste in (projet.d.get(cle) or [])
