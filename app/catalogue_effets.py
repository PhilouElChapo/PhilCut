"""Catalogue des effets dans le volet de droite (0.3.3) : vignettes animées et glisser-déposer.

Chaque effet et chaque transition a sa vignette qui bouge : un petit film d'une seconde et demie, fabriqué en
arrière-plan sur VOTRE plan (celui sous la ligne rouge), en tout petit, effet par effet. On voit ainsi ce que fait
chaque effet avant de le poser. On le pose en le glissant sur un plan de la timeline (une transition : sur un raccord
entre deux plans), par double-clic (plan sélectionné) ou par clic droit.
"""
import copy, os, subprocess, tempfile, threading

from PySide6.QtCore import QMimeData, QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMenu,
                               QVBoxLayout, QWidget)

from . import effets as E, theme
from .icones import icone
from .langue import _
from .timeline import MIME_EFFET

L_VIGNETTE, H_VIGNETTE = 128, 72
IPS = 8                     # images par seconde des vignettes


def _paysage(larg=2560, haut=720):
    """Un paysage dessiné par PhilCut (ciel, soleil, montagnes, mer) : neutre et libre, pour montrer les effets avant
    qu'un plan soit dans la timeline. Aucune image d'autrui."""
    import numpy as np
    y = np.linspace(0, 1, haut)[:, None]
    x = np.linspace(0, 1, larg)[None, :]
    img = np.zeros((haut, larg, 3), np.float32)
    ciel = np.array([[70, 140, 225]], np.float32) * (1 - y) + np.array([[250, 190, 140]], np.float32) * y      # bleu → orangé
    img[:] = ciel[:, None, :] if ciel.ndim == 2 else ciel
    img[:] = (np.array([70, 140, 225], np.float32) * (1 - y[..., None]) + np.array([250, 190, 140], np.float32) * y[..., None])
    # soleil et halo
    sx, sy, r = 0.32 * larg, 0.42 * haut, 0.06 * haut
    yy, xx = np.mgrid[0:haut, 0:larg]
    d = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
    halo = np.clip(1 - d / (r * 5), 0, 1)[..., None] ** 2
    img = img * (1 - 0.5 * halo) + np.array([255, 230, 170], np.float32) * 0.5 * halo
    img[d < r] = (255, 245, 210)
    # nuages
    for cx, cy, w in ((0.15, 0.18, 0.09), (0.55, 0.12, 0.12), (0.8, 0.22, 0.08), (0.95, 0.15, 0.1)):
        dn = ((xx - cx * larg) / (w * larg)) ** 2 + ((yy - cy * haut) / (0.035 * haut)) ** 2
        a = np.clip(1 - dn, 0, 1)[..., None] ** 0.7 * 0.85
        img = img * (1 - a) + 255 * a
    # trois chaînes de montagnes, de plus en plus sombres
    rng = np.random.default_rng(7)
    for k, (base, amp, coul) in enumerate(((0.55, 0.16, (120, 125, 160)), (0.63, 0.13, (75, 95, 110)), (0.70, 0.10, (40, 70, 55)))):
        crete = base + sum(amp / (i + 1) * np.sin(2 * np.pi * (x[0] * (i + 1) * (2 + k) + rng.random())) for i in range(5)) * 0.5
        masque = (y >= crete[None, :]) & (y < 0.74)
        img[masque] = np.array(coul, np.float32) * (0.85 + 0.3 * y.repeat(larg, 1)[masque, None] - 0.15)
    # mer avec reflets
    mer = (y >= 0.74).repeat(larg, 1)
    vague = (np.sin(xx * 0.05 + yy * 0.9) * 0.5 + 0.5)
    img[mer] = (np.array([30, 80, 130], np.float32) * (0.8 + 0.25 * vague[mer, None]))
    refl = mer & (np.abs(xx - sx) < 60 * (0.5 + y.repeat(larg, 1))) & (vague > 0.6)
    img[refl] = (250, 210, 150)
    return np.clip(img, 0, 255).astype(np.uint8)


def exemple_video():
    """La vidéo d'exemple des vignettes d'effets (6 s, lent travelling sur le paysage), fabriquée une fois sur ce poste."""
    import cv2
    from . import moteur
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "cache")
    sortie = os.path.join(d, "exemple_effets_v1.mp4")
    if os.path.exists(sortie):
        return sortie
    os.makedirs(d, exist_ok=True)
    png = os.path.join(d, "exemple_effets_v1.png")
    cv2.imwrite(png, cv2.cvtColor(_paysage(), cv2.COLOR_RGB2BGR))
    tmp = sortie + ".part.mp4"
    moteur.lancer(["-y", "-loop", "1", "-i", png, "-t", "6", "-r", "25",
                   "-vf", "crop=1280:720:'(iw-1280)*t/6':0,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", tmp])
    os.replace(tmp, sortie)
    return sortie


def projet_exemple():
    """Un projet d'un plan (la vidéo d'exemple) pour les vignettes quand la timeline est vide."""
    from . import moteur
    from .projet import Projet
    v = exemple_video()
    p = Projet()
    m = p.ajouter_media(v, moteur.sonder(v))
    m["nom"] = _("Exemple")
    c = p.ajouter_clip(m["id"])
    return p, c


def projet_essai(projet, clip, eid):
    """Mini-projet d'une seconde et demie (deux plans pour une transition) qui montre l'effet sur ce plan."""
    from .projet import Projet
    m = projet.media(clip["media"])
    p = Projet()
    p.d["format"] = projet.d.get("format", "16:9")
    if projet.d.get("cadence"):
        p.d["cadence"] = projet.d["cadence"]
    p.d["medias"] = [copy.deepcopy(m)]
    p.d["musique"] = None
    fi = E.fiche(eid) or {}
    duree_src = float((m.get("fiche") or {}).get("duree") or (clip["src_fin"] - clip["src_debut"]))
    base = {k: copy.deepcopy(v) for k, v in clip.items() if k not in ("effets", "transition", "effets_audio")}
    base.update(piste="video", vitesse=1.0, muet=True, effets=[], transition=None)
    milieu = (clip["src_debut"] + clip["src_fin"]) / 2
    if fi.get("famille") == "transition":
        d = float(E.defauts(eid).get("duree", 0.8) or 0.8)
        a0 = max(0.0, min(duree_src - 2.6, clip["src_debut"]))
        b0 = max(0.0, min(duree_src - 1.4, a0 + max(2.0, (clip["src_fin"] - clip["src_debut"]) / 2)))
        c1 = dict(base, id="essai1", debut=0.0, src_debut=a0, src_fin=a0 + 0.6 + d)
        c2 = dict(base, id="essai2", debut=0.6 + d, src_debut=b0, src_fin=b0 + 1.4,
                  transition={"id": eid, "params": dict(E.defauts(eid))})
        p.d["clips"] = [c1, c2]
    else:
        a0 = max(0.0, min(duree_src - 1.5, milieu - 0.75))
        p.d["clips"] = [dict(base, id="essai1", debut=0.0, src_debut=a0, src_fin=a0 + 1.5, effets=[{"id": eid, "params": dict(E.defauts(eid))}])]
    return p


def images_film(chemin, largeur=L_VIGNETTE):
    """Les images d'un petit film, en JPEG (une commande FFmpeg)."""
    from . import moteur
    r = subprocess.run([moteur.ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", chemin, "-vf", f"fps={IPS},scale={largeur}:-2",
                        "-q:v", "5", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"], capture_output=True, timeout=120, **moteur._sans_console())
    data, out, i = r.stdout, [], 0
    while True:
        d = data.find(b"\xff\xd8", i)
        if d < 0:
            break
        f = data.find(b"\xff\xd9", d)
        if f < 0:
            break
        out.append(data[d:f + 2])
        i = f + 2
    return out


def vignette(projet, clip, eid, params=None, arret=lambda: False):
    """Images (JPEG) de la vignette animée de l'effet `eid` sur ce plan."""
    from . import export
    p = projet_essai(projet, clip, eid)
    tmp = tempfile.mkdtemp(prefix="philcut-vignette-")
    sortie = os.path.join(tmp, "v.mp4")
    ex = export.Exportateur(p, sortie, "whatsapp", qualite="allegee", encodeur="libx264", params=params or {})
    L, H = p.taille
    ex.L, ex.H = (L_VIGNETTE * 2, H_VIGNETTE * 2) if L >= H else (H_VIGNETTE * 2, L_VIGNETTE * 2)
    ex.sans_son = True
    try:
        ex.lancer(arret=arret)
        return images_film(sortie)
    finally:
        ex.nettoyer()
        try:
            os.remove(sortie)
            os.rmdir(tmp)
        except OSError:
            pass


class Fabrique(QObject):
    """Fabrique les vignettes une par une, en arrière-plan, dans l'ordre demandé (les visibles d'abord)."""
    prete = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = {}            # eid -> [octets jpeg]
        self.cle = None             # (media, instant) : le plan qui sert d'exemple
        self._file = []
        self._fil = None
        self._arret = False
        self._verrou = threading.Lock()

    def changer_exemple(self, cle):
        if cle != self.cle:
            with self._verrou:
                self.cle = cle
                self.images = {}
                self._file = []

    def demander(self, projet, clip, eids, params):
        with self._verrou:
            for e in eids:
                if e not in self.images and e not in self._file:
                    self._file.append(e)
            self._contexte = (copy.deepcopy(projet), copy.deepcopy(clip), params, self.cle)
        if self._fil is None or not self._fil.is_alive():
            self._fil = threading.Thread(target=self._travail, daemon=True)
            self._fil.start()

    def arreter(self):
        self._arret = True

    def _travail(self):
        while not self._arret:
            with self._verrou:
                if not self._file:
                    return
                eid = self._file.pop(0)
                projet, clip, params, cle = self._contexte
            try:
                imgs = vignette(projet, clip, eid, params, arret=lambda: self._arret)
            except Exception:       # noqa: BLE001 : un effet qui ne se rend pas garde son icône
                imgs = []
            with self._verrou:
                if cle != self.cle:
                    continue
                self.images[eid] = imgs
            self.prete.emit(eid)


class ListeEffets(QListWidget):
    """Grille de vignettes ; on glisse une vignette sur la timeline."""

    def mimeTypes(self):
        return [MIME_EFFET]

    def mimeData(self, items):
        md = QMimeData()
        if items:
            md.setData(MIME_EFFET, (items[0].data(Qt.UserRole) or "").encode("utf-8"))
        return md

    def startDrag(self, actions):
        it = self.currentItem()
        if it is None:
            return
        from PySide6.QtGui import QDrag
        dr = QDrag(self)
        dr.setMimeData(self.mimeData([it]))
        px = it.icon().pixmap(QSize(L_VIGNETTE, H_VIGNETTE))
        if not px.isNull():
            dr.setPixmap(px.scaled(L_VIGNETTE * 3 // 4, H_VIGNETTE * 3 // 4, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        dr.exec(Qt.CopyAction)


class CatalogueEffets(QWidget):
    """Onglet « Catalogue » du volet de droite."""

    def __init__(self, editeur):
        super().__init__()
        self.ed = editeur
        self.params = editeur.params
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        aide = QLabel(_("Glissez une vignette sur un plan de la timeline (une transition : sur le raccord entre deux plans). "
                        "Double-clic : sur le plan sélectionné. Les vignettes montrent l'effet sur le plan sous la ligne rouge."))
        aide.setWordWrap(True)
        aide.setStyleSheet(f"color:{theme.COULEURS['texte2']}")
        v.addWidget(aide)
        h = QHBoxLayout()
        self.famille = QComboBox()
        self.famille.addItem(_("Toutes les familles"), "")
        self.famille.addItem(_("★ Favoris"), "favoris")
        for fam, nom in E.FAMILLES:
            self.famille.addItem(nom, fam)
        i = self.famille.findData(self.params.get("catalogue_famille", ""))
        self.famille.setCurrentIndex(max(0, i))
        h.addWidget(self.famille, 1)
        v.addLayout(h)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(_("Rechercher un effet…"))
        self.recherche.setClearButtonEnabled(True)
        v.addWidget(self.recherche)
        self.liste = ListeEffets()
        self.liste.setViewMode(QListView.IconMode)
        self.liste.setIconSize(QSize(L_VIGNETTE, H_VIGNETTE))
        self.liste.setGridSize(QSize(L_VIGNETTE + 12, H_VIGNETTE + 38))
        self.liste.setResizeMode(QListView.Adjust)
        self.liste.setMovement(QListView.Static)
        self.liste.setWordWrap(True)
        self.liste.setUniformItemSizes(True)
        self.liste.setDragEnabled(True)
        self.liste.setSelectionMode(QListWidget.SingleSelection)
        self.liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._menu)
        self.liste.itemDoubleClicked.connect(lambda it: self.ed.poser_effet(None, it.data(Qt.UserRole)))
        self.liste.currentItemChanged.connect(self._decrire)
        v.addWidget(self.liste, 1)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setStyleSheet(f"color:{theme.COULEURS['texte2']}")
        v.addWidget(self.info)
        self.fabrique = Fabrique(self)
        self.fabrique.prete.connect(self._prete)
        self._pixmaps = {}          # eid -> [QPixmap]
        self._tic = 0
        self.minuteur = QTimer(self)
        self.minuteur.setInterval(1000 // IPS)
        self.minuteur.timeout.connect(self._animer)
        self.famille.currentIndexChanged.connect(self._remplir)
        self.recherche.textChanged.connect(self._remplir)
        self._remplir()

    # ---- contenu
    def _cles(self):
        fam = self.famille.currentData() or ""
        self.params["catalogue_famille"] = fam
        favoris = list(self.params.get("effets_favoris") or [])
        if fam == "favoris":
            cles = [k for k in favoris if E.fiche(k)]
        elif fam:
            cles = E.par_famille().get(fam, [])
        else:
            cles = [k for f, _n in E.FAMILLES for k in E.par_famille().get(f, [])]
        filtre = self.recherche.text().strip().lower()
        if filtre:
            cles = [k for k in cles if filtre in E.fiche(k)["nom"].lower() or filtre in E.fiche(k)["description"].lower()]
        return cles

    def _icone_fixe(self, k):
        fi = E.fiche(k)
        px = QPixmap(L_VIGNETTE, H_VIGNETTE)
        px.fill(QColor(theme.COULEURS["surface"]))
        pt = QPainter(px)
        ic = icone({"transition": "fractionner", "look": "lumiere", "personne": "oeil"}.get(fi["famille"], "effets"), theme.COULEURS["texte2"])
        ic.paint(pt, (L_VIGNETTE - 32) // 2, (H_VIGNETTE - 32) // 2, 32, 32)
        pt.end()
        return QIcon(px)

    def _remplir(self):
        self.liste.clear()
        favoris = set(self.params.get("effets_favoris") or [])
        for k in self._cles():
            fi = E.fiche(k)
            it = QListWidgetItem(("★ " if k in favoris else "") + fi["nom"])
            it.setData(Qt.UserRole, k)
            tip = fi["description"]
            if fi["pack"] and not E.pack_pret(fi["pack"], self.params):
                tip += "\n" + _("Demande le pack « {p} » (Préférences).", p=E.PACKS.get(fi["pack"], {}).get("nom", fi["pack"]))
            it.setToolTip(tip)
            px = self._pixmaps.get(k)
            it.setIcon(QIcon(px[0]) if px else self._icone_fixe(k))
            it.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            self.liste.addItem(it)
        self.actualiser()

    def actualiser(self):
        """A appeler quand le volet devient visible ou que la ligne rouge change de plan : vignettes à fabriquer."""
        if not self.isVisible():
            return
        projet = self.ed.projet
        c = projet.clip_a(self.ed.timeline.position, "video") or next(iter(projet.clips_piste("video")), None)
        m = projet.media(c["media"]) if c else None
        exemple = not c or not m or m.get("genre") != "video"
        if exemple:                                    # 0.9.50 : timeline vide → les effets sur un paysage d'exemple
            if getattr(self, "_exemple", None) is None:
                if getattr(self, "_tache_exemple", None) is None:  # fabriquée une fois, hors de l'interface
                    from .taches import Tache
                    self._tache_exemple = Tache(lambda t: projet_exemple(), _("Exemple des effets"))
                    self._tache_exemple.fini.connect(self._exemple_pret)
                    self._tache_exemple.start()
                self.info.setText(_("Préparation d'une image d'exemple pour montrer les effets…"))
                return
            projet, c = self._exemple
        cle = ("exemple",) if exemple else (c["media"], round(c["src_debut"], 1), round(c["src_fin"], 1))
        if cle != self.fabrique.cle:
            self.fabrique.changer_exemple(cle)
            self._pixmaps = {}
            for i in range(self.liste.count()):
                it = self.liste.item(i)
                it.setIcon(self._icone_fixe(it.data(Qt.UserRole)))
        a_faire = [k for k in self._cles() if not (E.fiche(k)["pack"] and not E.pack_pret(E.fiche(k)["pack"], self.params))]
        manquent = [k for k in a_faire if k not in self.fabrique.images]
        self._sur_exemple = exemple
        if manquent:
            self.info.setText(_("Vignettes en préparation sur une image d'exemple : {k} sur {t}…", k=len(a_faire) - len(manquent), t=len(a_faire))
                              if exemple else
                              _("Vignettes en préparation sur « {n} » : {k} sur {t}…", n=c.get("nom", ""), k=len(a_faire) - len(manquent), t=len(a_faire)))
            self.fabrique.demander(projet, c, manquent, self.params)
        elif exemple:
            self.info.setText(self._texte_exemple())
        self.minuteur.start()

    def _prete(self, eid):
        imgs = self.fabrique.images.get(eid) or []
        pxs = []
        for b in imgs:
            px = QPixmap()
            if px.loadFromData(b):
                pxs.append(px)
        if pxs:
            self._pixmaps[eid] = pxs
        a_faire = [k for k in self._cles() if not (E.fiche(k)["pack"] and not E.pack_pret(E.fiche(k)["pack"], self.params))]
        prets = len([k for k in a_faire if k in self.fabrique.images])
        self.info.setText(_("Vignettes prêtes : {k} sur {t}.", k=prets, t=len(a_faire)) if prets < len(a_faire) else
                          self._texte_exemple() if getattr(self, "_sur_exemple", False) else
                          _("Survolez une vignette pour lire sa description ; glissez-la sur un plan pour la poser."))

    def _exemple_pret(self, r, err):
        if err or not r:
            self.info.setText(_("Mettez un plan vidéo dans la timeline : les vignettes montreront les effets sur lui."))
            return
        self._exemple = r
        self.actualiser()

    def _texte_exemple(self):
        return _("Effets montrés sur une image d'exemple. Mettez un plan vidéo dans la timeline : les vignettes les montreront sur vos images.")

    def _animer(self):
        if not self.isVisible():
            self.minuteur.stop()
            return
        self._tic += 1
        vue = self.liste.viewport().rect()
        for i in range(self.liste.count()):
            it = self.liste.item(i)
            pxs = self._pixmaps.get(it.data(Qt.UserRole))
            if not pxs or not self.liste.visualItemRect(it).intersects(vue):
                continue
            it.setIcon(QIcon(pxs[self._tic % len(pxs)]))

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self.actualiser)

    def _decrire(self, it, _p=None):
        if it is None:
            return
        fi = E.fiche(it.data(Qt.UserRole))
        if fi:
            self.info.setText(f"<b>{fi['nom']}</b> — {fi['description']}")

    def _menu(self, pos):
        it = self.liste.itemAt(pos)
        if it is None:
            return
        k = it.data(Qt.UserRole)
        favoris = list(self.params.get("effets_favoris") or [])
        m = QMenu(self)
        m.addAction(_("Poser sur le plan sélectionné"), lambda: self.ed.poser_effet(None, k))
        if k in favoris:
            m.addAction(icone("etoile", "#ffd24a"), _("Retirer des favoris"), lambda: self._favori(k, False))
        else:
            m.addAction(icone("etoile", "#ffd24a"), _("Ajouter aux favoris"), lambda: self._favori(k, True))
        m.addAction(_("Fenêtre Effets (aperçu en grand, réglages)…"), lambda: self.ed.outil("effets"))
        m.exec(self.liste.viewport().mapToGlobal(pos))

    def _favori(self, k, oui):
        f = [x for x in (self.params.get("effets_favoris") or []) if x != k]
        if oui:
            f.insert(0, k)
        self.params["effets_favoris"] = f
        self._remplir()

    def fermer(self):
        self.fabrique.arreter()
