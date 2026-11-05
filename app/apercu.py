"""L'apercu : lecture de la timeline en temps reel, avec les titres et les Goodies dessines par-dessus.

La lecture utilise le lecteur multimedia de Qt sur les proxys (copies legeres H.264), plan apres plan, a la
vitesse du plan. Les effets lourds (glow, puzzle, Matrix...) ne sont pas calcules en direct : un bouton
« Aperçu rendu » exporte en petit le passage choisi pour le juger ; l'export final, lui, est fidele.
"""
from PySide6.QtCore import Qt, QTimer, QUrl, QRectF, QPointF, Signal, QSizeF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap, QImage
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsPixmapItem, QWidget, QVBoxLayout, QFrame

from . import goodies as GO
from .langue import _
from .projet import fin_clip, duree_clip

import os as _os
try:
    if _os.environ.get("PHILCUT_SANS_MULTIMEDIA"):
        raise ImportError()
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
    MULTIMEDIA = True
except ImportError:                                     # sans module multimedia : apercu par images fixes
    MULTIMEDIA = False


PISTES_SON = ("audio", "voix")


class Apercu(QGraphicsView):
    position_changee = Signal(float)
    etat_lecture = Signal(bool)
    calque_deplace = Signal(str, float, float)      # id d'un texte ou Goodie déplacé à la souris dans l'image : x, y (0..1)
    calque_clique = Signal(str)                     # id : ouvrir dans l'Inspecteur
    calque_taille = Signal(str, float)              # id, facteur : molette sur l'élément dans l'image
    segment_fini = Signal(float)                    # la lecture avec effets arrive au bout du passage rendu (instant)
    pas_image = Signal(int)                         # molette sur l'image : ±1 image

    def __init__(self, projet=None, params=None, parent=None):
        super().__init__(parent)
        self.projet = projet
        self.params = params or {}
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setBackgroundBrush(QColor("#000"))
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cadre = QGraphicsRectItem(0, 0, 1920, 1080)
        self.cadre.setBrush(QColor("#111"))
        self.cadre.setPen(Qt.NoPen)
        self._scene.addItem(self.cadre)
        self.image_fixe = QGraphicsPixmapItem()
        self._scene.addItem(self.image_fixe)
        self.video = None
        self.lecteur = self.son = None
        self.lecteur_audio = self.son_audio = None
        self.sons = {}
        self.pistes_muettes = set()          # pistes coupées à l'écoute (bouton haut-parleur de chaque piste)
        self.muet_general = False
        if MULTIMEDIA and not self.params.get("apercu_images") and not _os.environ.get("PHILCUT_APERCU_IMAGES"):
            self.video = QGraphicsVideoItem()
            self._scene.addItem(self.video)
            self.lecteur = QMediaPlayer(self)
            self.son = QAudioOutput(self)
            self.lecteur.setAudioOutput(self.son)
            self.lecteur.setVideoOutput(self.video)
            for piste in PISTES_SON:            # un lecteur par piste de son : musique et voix off
                lp, so = QMediaPlayer(self), QAudioOutput(self)
                lp.setAudioOutput(so)
                self.sons[piste] = {"lecteur": lp, "sortie": so, "clip": None, "source": None}
            self.lecteur_audio, self.son_audio = self.sons["audio"]["lecteur"], self.sons["audio"]["sortie"]
            self.lecteur.errorOccurred.connect(self._erreur)
        self.calques = []                   # items des titres / goodies
        self.t = 0.0
        self.clip = None                    # clip video en cours
        self.clip_audio = None
        self.en_lecture = False
        self.boucle = False
        self._source = None
        self._source_audio = None
        self.sans_video = self.lecteur is None            # apercu par images FFmpeg (secours ou choix dans les Preferences)
        self._cache_images = {}
        self._derniere_image = None
        self.horloge = QTimer(self)
        self.horloge.setInterval(33)
        self.horloge.timeout.connect(self._tic)
        # image fidèle à l'arrêt : le montage rendu avec effets, transitions, textes et Goodies (0.3.0)
        self.item_rendu = QGraphicsPixmapItem()
        self.item_rendu.setZValue(50)
        self.item_rendu.hide()
        self._scene.addItem(self.item_rendu)
        self.badge_rendu = self._scene.addSimpleText("")
        self.badge_rendu.setZValue(51)
        self.badge_rendu.setBrush(QColor("#ffd24a"))
        self.badge_rendu.hide()
        self.fidele = bool(self.params.get("apercu_fidele", True))
        self._minut_rendu = QTimer(self)
        self._minut_rendu.setSingleShot(True)
        self._minut_rendu.setInterval(450)
        self._minut_rendu.timeout.connect(self._lancer_rendu)
        self._tache_rendu = None
        self.segment = None                 # (debut, fin, fichier) : passage rendu avec effets, lu à la place des rushes
        self.taches_hote = None             # liste de tâches de l'éditeur : la fenêtre les attend avant de se fermer
        self._rendu_pour = None             # (t, numéro d'état du projet) de l'image affichée
        self._t_depart = None
        self.changer_projet(projet)

    # ---------------------------------------------------------------- projet et format
    def changer_projet(self, projet):
        self.projet = projet
        self.arreter()
        L, H = projet.taille if projet else (1920, 1080)
        self.cadre.setRect(0, 0, L, H)
        if self.video:
            self.video.setSize(QSizeF(L, H))
            self.video.setPos(0, 0)
        self._scene.setSceneRect(0, 0, L, H)
        self._source = None
        self.clip = None
        self.aller_a(0.0)
        self.ajuster()

    def ajuster(self):
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.ajuster()

    # ---------------------------------------------------------------- navigation
    def aller_a(self, t, forcer=False):
        self.t = max(0.0, float(t))
        self._placer_video(forcer)
        self._placer_audio()
        self._dessiner_calques()
        self._cacher_rendu()
        if not self.en_lecture:
            self._minut_rendu.start()
        self.position_changee.emit(self.t)

    # ---- image fidèle à l'arrêt
    def _cacher_rendu(self):
        self.item_rendu.hide()
        self.badge_rendu.hide()

    def regler_fidele(self, on):
        self.fidele = bool(on)
        self.params["apercu_fidele"] = self.fidele
        if on:
            self._minut_rendu.start()
        else:
            self._cacher_rendu()

    def _a_rendre(self, t):
        """Y a-t-il à l'instant t quelque chose que la lecture brute ne montre pas (effet, transition, incrustation,
        texte, Goodie, sous-titre) ?"""
        from . import effets as E
        p = self.projet
        c = p.clip_a(t, "video")
        if c and (E.actifs(c) or (E.transition_active(c) and t < c["debut"] + float((c["transition"].get("params") or {}).get("duree", 0.8) or 0.8) + 0.05)):
            return True
        if any(x["debut"] <= t <= x["fin"] for x in p.titres + p.goodies):
            return True
        if any(x["debut"] <= t < fin_clip(x) for x in p.incrustations()):
            return True
        return any(x[0] <= t < x[1] for x in (p.d.get("sous_titres") or []))

    def _etat_projet(self):
        return (len(getattr(self.projet, "_pile", [])), len(getattr(self.projet, "_refaire", [])))

    def _lancer_rendu(self):
        if not self.fidele or self.en_lecture or not self.projet or self.projet.duree() <= 0 or self.t > self.projet.duree():
            return
        if self.segment and self.segment[0] - 0.02 <= self.t < self.segment[1] - 0.02:
            return                          # le passage rendu est déjà l'image fidèle
        if not self._a_rendre(self.t):
            return                          # rien à rendre ici : l'image brute est déjà la bonne
        if self._rendu_pour == (round(self.t, 3), self._etat_projet()) and not self.item_rendu.isVisible():
            self.item_rendu.show()
            self.badge_rendu.show()
            return
        if self._tache_rendu is not None and self._tache_rendu.isRunning():
            self._tache_rendu.stopper()
        import copy, tempfile
        from . import export
        from .taches import Tache
        projet = copy.deepcopy(self.projet)
        t, etat = self.t, self._etat_projet()
        sortie = _os.path.join(tempfile.gettempdir(), f"philcut_rendu_{_os.getpid()}_{id(self) % 1000}.png")
        st = list(self.projet.d.get("sous_titres") or [])
        tache = Tache(lambda tc: export.image_rendue(projet, t, sortie, self.params, 1280, st), _("Image fidèle"))
        self._tache_rendu = tache
        if self.taches_hote is not None:
            self.taches_hote.append(tache)

        def fini(r, e, tache=tache):
            if self.taches_hote is not None and tache in self.taches_hote:
                self.taches_hote.remove(tache)
            if tache is not self._tache_rendu or e or self.en_lecture or abs(self.t - t) > 1e-3:
                return
            px = QPixmap(sortie)
            if px.isNull():
                return
            L, H = self.projet.taille
            self.item_rendu.setPixmap(px)
            self.item_rendu.setScale(L / max(1, px.width()))
            self.item_rendu.setPos(0, 0)
            self.item_rendu.show()
            f = self.badge_rendu.font()
            f.setPixelSize(max(14, int(H * 0.028)))
            self.badge_rendu.setFont(f)
            self.badge_rendu.setText(_("✦ image avec effets"))
            self.badge_rendu.setPos(H * 0.015, H * 0.012)
            self.badge_rendu.show()
            for it in self.calques:             # les calques approchés laissent la place au vrai rendu
                try:
                    it.hide()
                except RuntimeError:
                    pass
            self._rendu_pour = (round(t, 3), etat)
        tache.fini.connect(fini)
        tache.start()

    def _url(self, m):
        chemin = m.get("proxy") or m["chemin"]
        return QUrl.fromLocalFile(chemin)

    def jouer_segment(self, debut, fin, chemin):
        """Lecture avec effets : le passage [debut, fin] a été rendu dans un fichier, on le joue à la place des rushes."""
        self.pause()
        self.segment = (float(debut), float(fin), chemin)
        self.clip = None
        self._source = None
        self.aller_a(debut, forcer=True)
        self.lire()

    def _source_video(self):
        """(plan, média) à montrer à l'instant t : le passage rendu s'il couvre t, sinon le plan de la piste vidéo."""
        seg = self.segment
        if seg:
            if seg[0] - 0.02 <= self.t < seg[1] - 0.02:
                L, H = self.projet.taille
                c = {"id": "__rendu__", "media": "__rendu__", "debut": seg[0], "src_debut": 0.0, "src_fin": seg[1] - seg[0],
                     "vitesse": 1.0, "ajustement": "remplir", "volume": 1.0}
                m = {"id": "__rendu__", "chemin": seg[2], "genre": "video", "fiche": {"video": {"largeur": L, "hauteur": H}}}
                return c, m
            fin = seg[1]
            self.segment = None             # on en sort : retour aux rushes, sauf si la suite est déjà prête
            self._source = None
            if self.en_lecture:
                self.segment_fini.emit(fin)
                if self.segment:            # l'éditeur vient d'enchaîner sur le passage suivant
                    return self._source_video()
        c = self.projet.clip_a(self.t, "video")
        return c, (self.projet.media(c["media"]) if c else None)

    def _media_de(self, c):
        if c and c.get("id") == "__rendu__" and self.segment:
            return {"genre": "video", "chemin": self.segment[2]}
        return self.projet.media(c["media"]) if c else None

    def _placer_video(self, forcer=False):
        if not self.projet:
            return
        c, m = self._source_video()
        if c is None:
            self.clip = None
            if self.lecteur:
                self.lecteur.pause()
                if self.video:
                    self.video.setVisible(False)
            self.image_fixe.setVisible(False)
            return
        if m is None:
            return
        if m.get("genre") == "image":
            if self.video:
                self.video.setVisible(False)
                self.lecteur.pause()
            self._montrer_image(m)
            self.clip = c
            return
        if self.sans_video or not self.lecteur:
            self.clip = c
            if self.lecteur:
                self.lecteur.pause()
            self._image_ffmpeg(c, m)
            return
        self.image_fixe.setVisible(False)
        self.video.setVisible(True)
        src = self._url(m)
        pos_ms = int((c["src_debut"] + (self.t - c["debut"]) * c.get("vitesse", 1.0)) * 1000)
        if self.clip is None or c["id"] != self.clip["id"] or src != self._source or forcer:
            if src != self._source:
                self.lecteur.setSource(src)
                self._source = src
            self.clip = c
            self.lecteur.setPlaybackRate(float(c.get("vitesse", 1.0)))
            self._cadrer(c, m)
        self.son.setVolume(0.0 if (c.get("muet") or self.muet_general or "video" in self.pistes_muettes or self.projet.piste_muette("video")) else float(c.get("volume", 1.0)))
        if c.get("ajustement") == "suivi":           # le cadre bouge avec la personne
            self._cadrer(c, m)
        if abs(self.lecteur.position() - pos_ms) > 80 or not self.en_lecture:
            self.lecteur.setPosition(pos_ms)
        if self.en_lecture and self.lecteur.playbackState() != QMediaPlayer.PlayingState:
            self.lecteur.play()
        elif not self.en_lecture:
            self.lecteur.pause()

    def _montrer_image(self, m):
        px = QPixmap(m["chemin"])
        if px.isNull():
            return
        L, H = self.projet.taille
        px = px.scaled(L, H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.image_fixe.setPixmap(px)
        self.image_fixe.setPos((L - px.width()) / 2, (H - px.height()) / 2)
        self.image_fixe.setVisible(True)

    def _cadrer(self, c, m):
        """Meme regle que l'export : remplir (recadre), ou contenir (bandes)."""
        if not self.video:
            return
        L, H = self.projet.taille
        v = (m.get("fiche") or {}).get("video") or {}
        lw, lh = v.get("largeur") or L, v.get("hauteur") or H
        mode = c.get("ajustement", "remplir")
        r_src, r_dst = lw / lh, L / H
        if mode == "suivi" and (c.get("suivi_cadre") or {}).get("positions"):
            from . import suivi
            t_src = c["src_debut"] + (self.t - c["debut"]) * c.get("vitesse", 1.0)
            x, y, cw, _ch = suivi.fenetre_source(c["suivi_cadre"], t_src, lw, lh, L, H)
            e = L / cw
            self.video.setAspectRatioMode(Qt.IgnoreAspectRatio)
            self.video.setSize(QSizeF(lw * e, lh * e))
            self.video.setPos(-x * e, -y * e)
            return
        if mode == "remplir":
            if r_src > r_dst:
                h = H
                w = H * r_src
            else:
                w = L
                h = L / r_src
        else:
            if r_src > r_dst:
                w = L
                h = L / r_src
            else:
                h = H
                w = H * r_src
        self.video.setAspectRatioMode(Qt.IgnoreAspectRatio)
        self.video.setSize(QSizeF(w, h))
        self.video.setPos((L - w) / 2, (H - h) / 2)

    def _placer_audio(self):
        if not self.projet or not self.sons:
            return
        if self.segment and self.clip and self.clip.get("id") == "__rendu__":
            for sp in self.sons.values():
                sp["lecteur"].pause()
            return
        for piste, sp in self.sons.items():
            lp, so = sp["lecteur"], sp["sortie"]
            c = self.projet.clip_a(self.t, piste)
            m = self.projet.media(c["media"]) if c else None
            if c is None or not m:
                sp["clip"] = None
                lp.pause()
                continue
            src = QUrl.fromLocalFile(m["chemin"])
            pos_ms = int((c["src_debut"] + (self.t - c["debut"]) * c.get("vitesse", 1.0)) * 1000)
            if sp["clip"] is None or c["id"] != sp["clip"]["id"] or src != sp["source"]:
                if src != sp["source"]:
                    lp.setSource(src)
                    sp["source"] = src
                sp["clip"] = c
                lp.setPlaybackRate(float(c.get("vitesse", 1.0)))
            coupe = c.get("muet") or self.muet_general or piste in self.pistes_muettes or self.projet.piste_muette(piste)
            so.setVolume(0.0 if coupe else min(1.0, float(c.get("volume", 1.0)) * (0.8 if piste == "audio" else 1.0)))
            if abs(lp.position() - pos_ms) > 120 or not self.en_lecture:
                lp.setPosition(pos_ms)
            if self.en_lecture:
                if lp.playbackState() != QMediaPlayer.PlayingState:
                    lp.play()
            else:
                lp.pause()
        self.clip_audio = self.sons["audio"]["clip"]

    def couper_son(self, piste=None, coupe=None):
        """Couper / remettre le son : de tout l'aperçu (piste=None) ou d'une piste (video, audio, voix)."""
        if piste is None:
            self.muet_general = (not self.muet_general) if coupe is None else bool(coupe)
        else:
            if coupe is None:
                coupe = piste not in self.pistes_muettes
            (self.pistes_muettes.add if coupe else self.pistes_muettes.discard)(piste)
        self._placer_video(False)
        self._placer_audio()

    # ---------------------------------------------------------------- lecture
    def lire(self):
        if not self.projet or self.projet.duree() <= 0:
            return
        if self.t >= self.projet.duree() - 0.02:
            self.t = 0.0
        self.en_lecture = True
        self._minut_rendu.stop()
        self._cacher_rendu()
        if self.segment:
            H = self.projet.taille[1]
            f = self.badge_rendu.font()
            f.setPixelSize(max(14, int(H * 0.028)))
            self.badge_rendu.setFont(f)
            self.badge_rendu.setText(_("✦ lecture avec effets"))
            self.badge_rendu.setPos(H * 0.015, H * 0.012)
            self.badge_rendu.show()
        import time
        self._t_depart = (time.monotonic(), self.t)
        self._placer_video(forcer=True)
        self._placer_audio()
        self.horloge.start()
        self.etat_lecture.emit(True)

    def pause(self):
        self.en_lecture = False
        self.horloge.stop()
        self._minut_rendu.start()
        if self.lecteur:
            self.lecteur.pause()
        for sp in self.sons.values():
            sp["lecteur"].pause()
        self.etat_lecture.emit(False)

    def arreter(self):
        self.pause()
        self._minut_rendu.stop()
        t = self._tache_rendu
        if t is not None and t.isRunning():
            t.stopper()
            t.wait(4000)

    def basculer(self):
        if self.en_lecture:
            self.pause()
        else:
            self.lire()

    def _tic(self):
        import time
        if not self.projet:
            return
        if self.clip and self.lecteur and not self.sans_video and self.lecteur.playbackState() == QMediaPlayer.PlayingState and (self._media_de(self.clip) or {}).get("genre") != "image":
            pos = self.lecteur.position() / 1000.0
            t = self.clip["debut"] + (pos - self.clip["src_debut"]) / self.clip.get("vitesse", 1.0)
            # le lecteur peut trainer au demarrage : on garde l'horloge comme garde-fou
            t_h = self._t_depart[1] + (time.monotonic() - self._t_depart[0])
            if abs(t - t_h) > 0.6:
                t = t_h
        else:
            t = self._t_depart[1] + (time.monotonic() - self._t_depart[0])
        if self.clip and t >= fin_clip(self.clip) - 0.02:
            t = fin_clip(self.clip)
        self.t = t
        if self.t >= self.projet.duree() - 0.01:
            if self.boucle:
                self.t = 0.0
                self._t_depart = (time.monotonic(), 0.0)
            else:
                self.t = self.projet.duree()
                self.pause()
                self._dessiner_calques()
                self.position_changee.emit(self.t)
                return
        c, _m = self._source_video()
        if (c is None) != (self.clip is None) or (c and self.clip and c["id"] != self.clip["id"]):
            self._t_depart = (time.monotonic(), self.t)
            self._placer_video(forcer=True)
        elif self.sans_video and c is not None:
            self._compte = getattr(self, "_compte", 0) + 1
            if self._compte % 6 == 0:
                m = self.projet.media(c["media"])
                if m and m.get("genre") != "image":
                    self._image_ffmpeg(c, m)
        for piste, sp in self.sons.items():
            ca = self.projet.clip_a(self.t, piste)
            if (ca is None) != (sp["clip"] is None) or (ca and sp["clip"] and ca["id"] != sp["clip"]["id"]):
                self._placer_audio()
                break
        self._dessiner_calques()
        self.position_changee.emit(self.t)

    def _erreur(self, err, texte=""):
        """Le lecteur multimedia n'y arrive pas (codec, carte, pilote) : on passe a l'apercu par images, sans rien casser."""
        if not self.sans_video:
            self.sans_video = True
            if self.video:
                self.video.setVisible(False)
            self._placer_video(forcer=True)

    def _image_ffmpeg(self, c, m):
        """Image du plan a l'instant courant, rendue par FFmpeg (proxy de preference), avec un petit cache."""
        from . import moteur
        t_src = c["src_debut"] + (self.t - c["debut"]) * c.get("vitesse", 1.0)
        cle = (m["id"], round(t_src, 1), c.get("ajustement"))
        if cle in self._cache_images:
            px = self._cache_images[cle]
        else:
            try:
                png = moteur.image(m.get("proxy") or m["chemin"], t_src, 960)
                px = QPixmap()
                px.loadFromData(png)
            except Exception:
                px = QPixmap()
            if len(self._cache_images) > 60:
                self._cache_images.pop(next(iter(self._cache_images)))
            self._cache_images[cle] = px
        if px.isNull():
            return
        L, H = self.projet.taille
        mode = c.get("ajustement", "remplir")
        if mode == "suivi" and (c.get("suivi_cadre") or {}).get("positions"):
            from . import suivi
            x, y, cw, ch = suivi.fenetre_source(c["suivi_cadre"], t_src, px.width(), px.height(), L, H)
            px = px.copy(int(x), int(y), max(1, int(cw)), max(1, int(ch)))
            mode = "remplir"
        px2 = px.scaled(L, H, Qt.KeepAspectRatioByExpanding if mode == "remplir" else Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_fixe.setPixmap(px2)
        self.image_fixe.setPos((L - px2.width()) / 2, (H - px2.height()) / 2)
        self.image_fixe.setVisible(True)

    # ---------------------------------------------------------------- calques : titres et goodies
    def _dessiner_calques(self):
        for it in self.calques + getattr(self, "poignees", []):
            self._scene.removeItem(it)
        self.calques = []
        self.poignees = []
        if not self.projet:
            return
        if self.segment and self.clip and self.clip.get("id") == "__rendu__":
            return
        L, H = self.projet.taille
        for t in self.projet.titres:
            if t["debut"] <= self.t <= t["fin"]:
                avant = len(self.calques)
                self._titre(t, L, H)
                if not t.get("suivi"):
                    self._poignee(t, self.calques[avant:], L, H)
        for g in self.projet.goodies:
            if g["debut"] <= self.t <= g["fin"]:
                avant = len(self.calques)
                self._goodie(g, L, H)
                if not (g.get("suivi") or {}).get("positions"):
                    self._poignee(g, self.calques[avant:], L, H)

    def _poignee(self, elem, items, L, H):
        """Cadre invisible par-dessus un texte ou un Goodie : on le déplace à la souris directement dans l'image."""
        if not items:
            return
        r = items[0].sceneBoundingRect()
        for it in items[1:]:
            r = r.united(it.sceneBoundingRect())
        pg = Poignee(self, elem["id"], r.adjusted(-6, -6, 6, 6), L, H)
        self._scene.addItem(pg)
        self.poignees.append(pg)

    def wheelEvent(self, e):
        it = self.itemAt(e.position().toPoint())
        if isinstance(it, Poignee):                 # molette sur un texte ou un Goodie : sa taille
            super().wheelEvent(e)
            return
        d = e.angleDelta().y()
        if d:
            self.pas_image.emit(-1 if d > 0 else 1)
        e.accept()

    def _titre(self, t, L, H):
        taille = H * 0.055 * float(t.get("taille") or 1.0)
        f = QFont(t.get("police") or "Nunito")
        f.setPixelSize(int(taille))
        f.setBold(True)
        it = QGraphicsSimpleTextItem(t.get("texte", ""))
        it.setFont(f)
        it.setBrush(QColor(t.get("couleur") or "#ffffff"))
        it.setPen(QPen(QColor(0, 0, 0, 160), max(1.0, taille / 18)))
        x, y = float(t.get("x", 0.5)) * L, float(t.get("y", 0.85)) * H
        if t.get("suivi") and t["suivi"].get("positions"):
            pos = t["suivi"]["positions"]
            p = min(pos, key=lambda z: abs(z[0] - self.t))
            x, y = float(p[1]) * L, float(p[2]) * H - taille * 1.4
        r = it.boundingRect()
        if t.get("style") == "etiquette":
            fond = QGraphicsRectItem(r.adjusted(-10, -5, 10, 5))
            fond.setBrush(QColor(0, 0, 0, 160))
            fond.setPen(Qt.NoPen)
            fond.setPos(x - r.width() / 2, y - r.height() / 2)
            fond.setZValue(5)
            self._scene.addItem(fond)
            self.calques.append(fond)
        anim = t.get("animation") or "fondu"
        age = self.t - t["debut"]
        if anim == "machine":
            n = len(t.get("texte", ""))
            k = min(n, int(age / max(0.02, min(0.09, (t["fin"] - t["debut"]) * 0.5 / max(1, n)))))
            it.setText(t.get("texte", "")[:k])
        elif anim == "cinetique":
            mots = t.get("texte", "").split()
            pas = (t["fin"] - t["debut"]) / (len(mots) + 1) if mots else 1
            i = min(len(mots) - 1, int(age / pas)) if mots else 0
            it.setText(mots[i] if mots else "")
            r = it.boundingRect()
        elif anim == "feu":
            it.setBrush(QColor("#ffa700"))
            it.setPen(QPen(QColor("#ff2800"), max(1.0, taille / 14)))
        elif anim == "neon":
            it.setPen(QPen(QColor(t.get("couleur") or "#ffffff"), max(1.0, taille / 10)))
        it.setPos(x - r.width() / 2, y - r.height() / 2)
        it.setZValue(6)
        if anim in ("fondu", "zoom", "glisse") and age < 0.3:
            it.setOpacity(max(0.0, age / 0.3))
        self._scene.addItem(it)
        self.calques.append(it)

    def _goodie(self, g, L, H):
        taille = max(48, int(H * float(g.get("taille", 0.22))))
        nom = GO.GENRES.get(g["genre"], (g["genre"], "", (0, 0)))
        v = GO.valeur(g, self.t)
        x = float(g.get("x", 0.88)) * L - taille / 2
        y = float(g.get("y", 0.85)) * H - taille / 2
        pos = (g.get("suivi") or {}).get("positions")
        if pos:                       # accroché : centré sur le point d'accroche, posé au-dessus
            from . import suivi
            x = min(max(suivi.valeur(pos, self.t, 1) * L - taille / 2, 0), L - taille)
            y = min(max(suivi.valeur(pos, self.t, 2) * H - taille, 0), H - taille)
        if g.get("genre") == "image":
            px = QPixmap((g.get("options") or {}).get("chemin") or "")
            if not px.isNull():
                px = px.scaled(taille, taille, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                it = self._scene.addPixmap(px)
                it.setPos(x + (taille - px.width()) / 2, y + (taille - px.height()) / 2)
                it.setZValue(6)
                self.calques.append(it)
                return
        cadre = QGraphicsRectItem(0, 0, taille, taille)
        cadre.setBrush(QColor(10, 10, 14, 170))
        cadre.setPen(QPen(QColor(255, 255, 255, 140), 2))
        cadre.setPos(x, y)
        cadre.setZValue(5)
        self._scene.addItem(cadre)
        texte = QGraphicsSimpleTextItem(f"{nom[0]}\n{v:,.0f} {nom[1]}".replace(",", " ") if nom[1] else nom[0])
        f = QFont("Nunito")
        f.setPixelSize(max(10, taille // 8))
        f.setBold(True)
        texte.setFont(f)
        texte.setBrush(QColor("#ffffff"))
        r = texte.boundingRect()
        texte.setPos(x + (taille - r.width()) / 2, y + (taille - r.height()) / 2)
        texte.setZValue(6)
        self._scene.addItem(texte)
        self.calques += [cadre, texte]

    # ---------------------------------------------------------------- image fixe a l'instant (sans multimedia ou pour la miniature)
    def image_courante(self, largeur=640):
        """PNG de l'image a l'instant courant, rendu par FFmpeg (miniature, fiche, IA)."""
        from . import moteur
        c = self.projet.clip_a(self.t, "video") if self.projet else None
        if not c:
            return None
        m = self.projet.media(c["media"])
        if m.get("genre") == "image":
            with open(m["chemin"], "rb") as f:
                return f.read()
        return moteur.image(m.get("proxy") or m["chemin"], c["src_debut"] + (self.t - c["debut"]) * c.get("vitesse", 1.0), largeur)


class Poignee(QGraphicsRectItem):
    """Cadre déplaçable posé sur un texte ou un Goodie dans l'aperçu : glisser le déplace, double-clic ouvre l'Inspecteur."""

    def __init__(self, apercu, ident, rect, L, H):
        super().__init__(rect)
        self.apercu, self.ident, self.L, self.H = apercu, ident, L, H
        self.setZValue(60)
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemIsSelectable)
        self.setPen(QPen(QColor(255, 210, 74, 0), 2, Qt.DashLine))
        self.setBrush(Qt.NoBrush)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip(_("Glissez pour déplacer · molette : plus grand ou plus petit · double-clic : réglages"))

    def hoverEnterEvent(self, e):
        self.setPen(QPen(QColor(255, 210, 74, 220), 2, Qt.DashLine))
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        self.setPen(QPen(QColor(255, 210, 74, 0), 2, Qt.DashLine))
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self.setCursor(Qt.OpenHandCursor)
        c = self.sceneBoundingRect().center()
        x = min(1.0, max(0.0, c.x() / self.L))
        y = min(1.0, max(0.0, c.y() / self.H))
        self.apercu.calque_deplace.emit(self.ident, x, y)

    def mouseDoubleClickEvent(self, e):
        self.apercu.calque_clique.emit(self.ident)

    def wheelEvent(self, e):
        d = e.delta()
        if d:
            self.apercu.calque_taille.emit(self.ident, 1.1 if d > 0 else 1 / 1.1)
        e.accept()
