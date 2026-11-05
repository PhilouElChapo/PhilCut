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
    calque_cadre = Signal(str, float, float, float, float)   # id d'une zone redimensionnée : centre x, y, largeur, hauteur (0..1)
    zone_tracee = Signal(float, float, float, float)         # rectangle tracé à la souris (mode « tracer une zone ») : x, y, l, h
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
        self.fidele = bool(self.params.get("apercu_fidele", True)) and _os.environ.get("PHILCUT_APERCU_FIDELE") != "0"
        self._minut_rendu = QTimer(self)
        self._minut_rendu.setSingleShot(True)
        self._minut_rendu.setInterval(450)
        self._minut_rendu.timeout.connect(self._lancer_rendu)
        self._tache_rendu = None
        self.segment = None                 # (debut, fin, fichier) : passage rendu avec effets, lu à la place des rushes
        self.fournisseur = None             # t -> (debut, fin, fichier) | None : tranches préparées automatiquement (0.3.1)
        self.balayage = False               # le curseur est tiré à la souris : images de la pellicule
        from .preparation import Pellicules
        self.pellicules = Pellicules()
        self.taches_hote = None             # liste de tâches de l'éditeur : la fenêtre les attend avant de se fermer
        self._rendu_pour = None             # (t, numéro d'état du projet) de l'image affichée
        self._t_depart = None
        self.changer_projet(projet)

    # ---------------------------------------------------------------- projet et format
    def changer_projet(self, projet):
        self.projet = projet
        self.arreter()
        self._ferme = False
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
    def _badge(self, texte):
        H = self.projet.taille[1] if self.projet else 1080
        f = self.badge_rendu.font()
        f.setPixelSize(max(14, int(H * 0.028)))
        self.badge_rendu.setFont(f)
        self.badge_rendu.setText(texte)
        self.badge_rendu.setPos(H * 0.015, H * 0.012)
        self.badge_rendu.show()

    def regler_balayage(self, on):
        """Pendant qu'on tire le curseur : images de la pellicule (instantanées) ; au lâcher : l'image exacte."""
        self.balayage = bool(on)
        if not on:
            self.aller_a(self.t, forcer=True)

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
        if c and (E.actifs_entre(c, t - 0.01, t + 0.01) or (E.transition_active(c) and t < c["debut"] + float((c["transition"].get("params") or {}).get("duree", 0.8) or 0.8) + 0.05)):
            return True
        if any(x["debut"] <= t <= x["fin"] for x in p.titres + p.goodies):
            return True
        if any(x["debut"] <= t < fin_clip(x) for x in p.incrustations()):
            return True
        return any(x[0] <= t < x[1] for x in (p.d.get("sous_titres") or []))

    def _etat_projet(self):
        return (len(getattr(self.projet, "_pile", [])), len(getattr(self.projet, "_refaire", [])))

    def _lancer_rendu(self):
        if getattr(self, "_ferme", False) or not self.fidele or self.en_lecture or not self.projet or self.projet.duree() <= 0 or self.t > self.projet.duree():
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
            self.badge_rendu.hide()
            QTimer.singleShot(0, self._placer_audio)
        if self.en_lecture and self.fournisseur is not None:
            tr = self.fournisseur(self.t)
            if tr:                          # tranche préparée : on la lit à la place des rushes
                self.segment = tr
                self._source = None
                self._badge(_("✦ lecture avec effets"))
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
        if self.balayage and not self.en_lecture and c.get("id") != "__rendu__":
            t_src = c["src_debut"] + (self.t - c["debut"]) * c.get("vitesse", 1.0)
            jpg = self.pellicules.image(m, t_src)
            if jpg is not None:
                px = QPixmap()
                px.loadFromData(jpg)
                if not px.isNull():
                    if self.video:
                        self.video.setVisible(False)
                    self.clip = c
                    self._afficher_px(c, px, t_src)
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
                sp["clip"] = None           # au retour aux rushes, chaque piste se replace
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
            self._badge(_("✦ lecture avec effets"))
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
        self._ferme = True
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
        self._afficher_px(c, px, t_src)

    def _afficher_px(self, c, px, t_src):
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
                if g.get("genre") == "zone":
                    self._zone(g, L, H)
                    self._poignee(g, self.calques[avant:avant + 1], L, H, zone=True)
                    continue
                self._goodie(g, L, H)
                if not (g.get("suivi") or {}).get("positions"):
                    self._poignee(g, self.calques[avant:], L, H)

    def _poignee(self, elem, items, L, H, zone=False):
        """Cadre par-dessus un texte, un Goodie ou une zone : on le déplace et le redimensionne directement dans l'image."""
        if not items:
            return
        r = items[0].sceneBoundingRect()
        for it in items[1:]:
            r = r.united(it.sceneBoundingRect())
        pg = Poignee(self, elem["id"], r if zone else r.adjusted(-6, -6, 6, 6), L, H, zone=zone)
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
        if t.get("cles"):                       # images clefs : valeurs de cet instant
            from . import cles as K
            v = K.valeurs_a(t, self.t)
            t = dict(t, x=v["x"], y=v["y"], taille=v["taille"], _opacite=v["opacite"])
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
        if t.get("_opacite") is not None:
            it.setOpacity(max(0.0, min(1.0, float(t["_opacite"]))))
        self._scene.addItem(it)
        self.calques.append(it)

    def _zone(self, g, L, H):
        """Zone tracée (flou, mosaïque, cache…) : son contour et un aperçu de son traitement. A l'arrêt, l'image fidèle
        (rendue par le moteur d'export) la montre exactement, par-dessus."""
        from . import zones as Z
        x, y, l, h = Z.rect_a(g, self.t)
        r = QRectF((x - l / 2) * L, (y - h / 2) * H, l * L, h * H)
        tr = g.get("traitement", "flou")
        if g.get("forme") == "ovale":
            from PySide6.QtWidgets import QGraphicsEllipseItem
            it = QGraphicsEllipseItem(r)
        else:
            it = QGraphicsRectItem(r)
        if tr == "cache":
            it.setBrush(QColor(g.get("couleur") or "#000000"))
        else:
            c = {"flou": QColor(200, 200, 210, 120), "mosaique": QColor(160, 160, 170, 140), "eclaircir": QColor(255, 255, 255, 70),
                 "assombrir": QColor(0, 0, 0, 110), "noir_blanc": QColor(128, 128, 128, 120)}.get(tr, QColor(200, 200, 210, 110))
            it.setBrush(QBrush(c, Qt.Dense4Pattern if tr == "mosaique" else Qt.SolidPattern))
        it.setPen(QPen(QColor("#5ad1ff"), 2, Qt.DashLine))
        it.setZValue(7)
        self._scene.addItem(it)
        lib = QGraphicsSimpleTextItem(Z.libelle(g))
        f = QFont()
        f.setPixelSize(max(12, int(H * 0.022)))
        f.setBold(True)
        lib.setFont(f)
        lib.setBrush(QColor("#5ad1ff"))
        lib.setPos(r.left() + 4, max(0.0, r.top() - f.pixelSize() * 1.4))
        lib.setZValue(7)
        self._scene.addItem(lib)
        self.calques += [it, lib]

    # ---------------------------------------------------------------- tracer une zone à la souris
    def tracer_zone(self, on=True):
        """Mode « tracer » : le prochain glisser dans l'image dessine un rectangle (signal zone_tracee)."""
        self._mode_trace = bool(on)
        self._trace = None
        self.viewport().setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)

    def keyPressEvent(self, e):
        if getattr(self, "_mode_trace", False) and e.key() == Qt.Key_Escape:
            if getattr(self, "_trace", None):
                self._scene.removeItem(self._trace[1])
            self.tracer_zone(False)
            self.zone_tracee.emit(-1.0, -1.0, 0.0, 0.0)
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        if getattr(self, "_mode_trace", False) and e.button() == Qt.LeftButton:
            p = self.mapToScene(e.position().toPoint())
            self._trace = (p, QGraphicsRectItem(QRectF(p, p)))
            self._trace[1].setPen(QPen(QColor("#5ad1ff"), 2, Qt.DashLine))
            self._trace[1].setBrush(QColor(90, 209, 255, 50))
            self._trace[1].setZValue(70)
            self._scene.addItem(self._trace[1])
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if getattr(self, "_trace", None):
            p = self.mapToScene(e.position().toPoint())
            self._trace[1].setRect(QRectF(self._trace[0], p).normalized())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if getattr(self, "_trace", None):
            r = self._trace[1].rect().intersected(self._scene.sceneRect())
            self._scene.removeItem(self._trace[1])
            self._trace = None
            self.tracer_zone(False)
            L, H = self.projet.taille if self.projet else (1920, 1080)
            if r.width() > 6 and r.height() > 6:
                self.zone_tracee.emit(r.center().x() / L, r.center().y() / H, r.width() / L, r.height() / H)
            else:
                self.zone_tracee.emit(-1.0, -1.0, 0.0, 0.0)          # simple clic : tracé abandonné
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def _goodie(self, g, L, H):
        if g.get("cles"):
            from . import cles as K
            v = K.valeurs_a(g, self.t)
            g = dict(g, x=v["x"], y=v["y"])
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
    """Cadre posé sur un texte, un Goodie ou une zone dans l'aperçu : glisser le déplace, les quatre coins carrés
    l'agrandissent ou le rétrécissent, la molette aussi, double-clic ouvre l'Inspecteur."""

    COIN = 9            # demi-côté des coins, en pixels d'écran

    def __init__(self, apercu, ident, rect, L, H, zone=False):
        super().__init__(rect)
        self.apercu, self.ident, self.L, self.H, self.zone = apercu, ident, L, H, zone
        self.setZValue(60)
        self.setAcceptHoverEvents(True)
        self.setFlags(QGraphicsRectItem.ItemIsSelectable)
        self.setBrush(Qt.NoBrush)
        self.setCursor(Qt.OpenHandCursor)
        self._survol = zone
        self._prise = None          # (genre, point de départ, rect de départ) pendant un glissement
        self._maj_stylo()
        self.setToolTip(_("Glissez pour déplacer · tirez un coin pour agrandir ou rétrécir · molette : taille · double-clic : réglages"))

    def _maj_stylo(self):
        a = 230 if self._survol or self._prise else 0
        self.setPen(QPen(QColor(90, 209, 255, a) if self.zone else QColor(255, 210, 74, a), 2, Qt.DashLine))

    def _ech(self):
        m = self.apercu.transform().m11() or 1.0
        return self.COIN / m

    def _coins(self):
        r = self.rect()
        return {"hg": r.topLeft(), "hd": r.topRight(), "bg": r.bottomLeft(), "bd": r.bottomRight()}

    def _coin_sous(self, pos):
        k = self._ech() * 1.6
        for nom, c in self._coins().items():
            if abs(pos.x() - c.x()) <= k and abs(pos.y() - c.y()) <= k:
                return nom
        return None

    def boundingRect(self):
        k = self._ech() + 2
        return self.rect().adjusted(-k, -k, k, k)

    def shape(self):
        from PySide6.QtGui import QPainterPath
        pp = QPainterPath()
        pp.addRect(self.boundingRect())
        return pp

    def paint(self, p, opt, w=None):
        p.setPen(self.pen())
        p.setBrush(Qt.NoBrush)
        p.drawRect(self.rect())
        if self._survol or self._prise:
            k = self._ech()
            p.setPen(QPen(QColor(20, 20, 26), 1))
            p.setBrush(QColor("#5ad1ff") if self.zone else QColor("#ffd24a"))
            for c in self._coins().values():
                p.drawRect(QRectF(c.x() - k, c.y() - k, 2 * k, 2 * k))

    def hoverEnterEvent(self, e):
        self._survol = True
        self._maj_stylo()
        self.update()
        super().hoverEnterEvent(e)

    def hoverMoveEvent(self, e):
        coin = self._coin_sous(e.pos())
        self.setCursor(Qt.SizeFDiagCursor if coin in ("hg", "bd") else Qt.SizeBDiagCursor if coin else Qt.OpenHandCursor)
        super().hoverMoveEvent(e)

    def hoverLeaveEvent(self, e):
        self._survol = self.zone
        self._maj_stylo()
        self.update()
        super().hoverLeaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            e.ignore()
            return
        coin = self._coin_sous(e.pos())
        self._prise = (coin or "deplacer", e.scenePos(), QRectF(self.sceneBoundingRect().adjusted(0, 0, 0, 0)), QRectF(self.rect()))
        if not coin:
            self.setCursor(Qt.ClosedHandCursor)
        e.accept()

    def mouseMoveEvent(self, e):
        if not self._prise:
            return
        genre, p0, _sb, r0 = self._prise
        d = e.scenePos() - p0
        self.prepareGeometryChange()
        if genre == "deplacer":
            self.setRect(r0.translated(d))
        else:
            r = QRectF(r0)
            if self.zone:                       # une zone se déforme librement
                if "g" in genre:
                    r.setLeft(min(r0.right() - 8, r0.left() + d.x()))
                if "d" in genre:
                    r.setRight(max(r0.left() + 8, r0.right() + d.x()))
                if "h" in genre:
                    r.setTop(min(r0.bottom() - 8, r0.top() + d.y()))
                if "b" in genre:
                    r.setBottom(max(r0.top() + 8, r0.bottom() + d.y()))
            else:                               # un texte ou un Goodie garde ses proportions, centre fixe
                c = r0.center()
                coin = {"hg": r0.topLeft(), "hd": r0.topRight(), "bg": r0.bottomLeft(), "bd": r0.bottomRight()}[genre]
                v0 = coin - c
                v1 = coin + d - c
                n0 = max(1.0, (v0.x() ** 2 + v0.y() ** 2) ** 0.5)
                f = max(0.15, min(8.0, (v1.x() ** 2 + v1.y() ** 2) ** 0.5 / n0))
                r = QRectF(c.x() - r0.width() * f / 2, c.y() - r0.height() * f / 2, r0.width() * f, r0.height() * f)
            self.setRect(r)
        self.update()
        e.accept()

    def mouseReleaseEvent(self, e):
        if not self._prise:
            return
        genre, _p0, _sb, r0 = self._prise
        self._prise = None
        self.setCursor(Qt.OpenHandCursor)
        self._maj_stylo()
        r = self.rect()
        if genre == "deplacer":
            c = r.center()
            if (c - r0.center()).manhattanLength() < 1:
                return
            self.apercu.calque_deplace.emit(self.ident, min(1.0, max(0.0, c.x() / self.L)), min(1.0, max(0.0, c.y() / self.H)))
        elif self.zone:
            self.apercu.calque_cadre.emit(self.ident, r.center().x() / self.L, r.center().y() / self.H, r.width() / self.L, r.height() / self.H)
        else:
            f = r.width() / max(1.0, r0.width())
            if abs(f - 1) > 0.01:
                self.apercu.calque_taille.emit(self.ident, f)

    def mouseDoubleClickEvent(self, e):
        self.apercu.calque_clique.emit(self.ident)

    def wheelEvent(self, e):
        d = e.delta()
        if d:
            self.apercu.calque_taille.emit(self.ident, 1.1 if d > 0 else 1 / 1.1)
        e.accept()
