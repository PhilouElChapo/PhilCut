"""Préparation automatique de la lecture (0.3.1) et pellicule de balayage.

Préparation : la timeline est découpée en tranches de quelques secondes. Une tranche où il se passe quelque chose que
la lecture brute ne montre pas (effet, transition, incrustation, texte, Goodie, sous-titre) est « à préparer » : elle
est rendue en arrière-plan (720p), une à la fois, la plus proche du curseur d'abord. Au-dessus de la timeline, une
barre la montre en rouge (pas prête) puis en vert (prête). La lecture simple (▶) joue les tranches vertes à la place
des rushes : on voit les effets en lisant, sans bouton spécial.

Chaque tranche est identifiée par l'empreinte de son contenu : modifier un plan ne fait repréparer que les tranches
qu'il touche ; revenir en arrière (Annuler) retrouve les tranches déjà prêtes.

Pellicule : pour balayer la vidéo à la souris, les images d'un rush sont extraites une fois en petit (une seule
commande FFmpeg) et gardées en mémoire ; le curseur qu'on tire les affiche instantanément."""
import copy, hashlib, json, os, subprocess, tempfile, threading

from PySide6.QtCore import QObject, QTimer, Signal

from . import effets as E
from .langue import _
from .projet import fin_clip

TRANCHE = 4.0                   # secondes
MAX_CACHE = 60                  # tranches gardées sur le disque


def a_preparer(projet, a, b):
    """La tranche [a, b] contient-elle quelque chose que la lecture brute ne montre pas ?"""
    for c in projet.clips_piste("video"):
        if fin_clip(c) <= a or c["debut"] >= b:
            continue
        if E.actifs(c):
            return True
        t = E.transition_active(c)
        if t and c["debut"] < b and c["debut"] + float((t.get("params") or {}).get("duree", 0.8) or 0.8) > a:
            return True
        if c.get("ajustement") == "suivi":
            return True
    for x in projet.titres + projet.goodies:
        if x["fin"] > a and x["debut"] < b:
            return True
    for c in projet.incrustations():
        if fin_clip(c) > a and c["debut"] < b and not projet.piste_masquee(c["piste"]):
            return True
    return any(x[1] > a and x[0] < b for x in (projet.d.get("sous_titres") or []))


def empreinte(projet, a, b):
    """Empreinte du contenu de la tranche : ce qui la touche, ramené à son début (indépendant du reste du montage)."""
    from .export import extrait
    p = extrait(projet, a, b)
    d = {k: p.d.get(k) for k in ("clips", "titres", "goodies", "format", "cadence", "pistes_muettes", "pistes_masquees",
                                  "nb_video", "nb_audio", "ducking")}
    d["medias"] = sorted({c["media"] for c in p.clips})
    d["chemins"] = [((p.media(m) or {}).get("chemin"), ((p.media(m) or {}).get("fiche") or {}).get("duree")) for m in d["medias"]]
    d["st"] = [list(x) for x in (projet.d.get("sous_titres") or []) if x[1] > a and x[0] < b]
    d["ab"] = (round(a, 3), round(b, 3))
    return hashlib.sha1(json.dumps(d, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:20]


class Preparation(QObject):
    change = Signal()               # les états des tranches ont changé (la timeline redessine sa barre)

    def __init__(self, editeur):
        super().__init__(editeur)
        self.ed = editeur
        self.actif = bool(editeur.params.get("preparation_auto", True)) and os.environ.get("PHILCUT_PREPARATION") != "0"
        self.dossier = tempfile.mkdtemp(prefix="philcut-preparation-")
        self.prets = {}             # empreinte -> chemin du fichier rendu
        self.tranches = []          # [(a, b, empreinte | None)] : None = rien à préparer
        self.tache = None
        self._en_cours = None       # empreinte en préparation
        self._ferme = False
        self.minuteur = QTimer(self)
        self.minuteur.setSingleShot(True)
        self.minuteur.setInterval(600)
        self.minuteur.timeout.connect(self._recalculer)

    # ---- état
    def revoir(self):
        """A appeler après chaque modification : recalcul différé des tranches."""
        if not self._ferme:
            self.minuteur.start()

    def regler(self, on):
        self.actif = bool(on)
        self.ed.params["preparation_auto"] = self.actif
        if on:
            self.revoir()
        else:
            self.arreter_tache()
            self.change.emit()

    def _recalculer(self):
        p = self.ed.projet
        duree = p.duree()
        out = []
        a = 0.0
        while a < duree - 0.05:
            b = min(duree, a + TRANCHE)
            try:
                out.append((a, b, empreinte(p, a, b) if a_preparer(p, a, b) else None))
            except Exception:       # noqa: BLE001 : une tranche impossible à décrire reste brute
                out.append((a, b, None))
            a = b
        self.tranches = out
        self.change.emit()
        self._suivante()

    def etats(self):
        """[(a, b, 'pret' | 'a_preparer' | 'en_cours')] pour la barre de la timeline (tranches à préparer seulement)."""
        if not self.actif:
            return []
        out = []
        for a, b, e in self.tranches:
            if e is None:
                continue
            if e in self.prets and os.path.exists(self.prets[e]):
                out.append((a, b, "pret"))
            elif e == self._en_cours:
                out.append((a, b, "en_cours"))
            else:
                out.append((a, b, "a_preparer"))
        return out

    def tranche_prete(self, t):
        """(a, b, fichier) si la tranche qui contient t est prête pour l'état actuel du montage."""
        if not self.actif:
            return None
        for a, b, e in self.tranches:
            if a - 1e-3 <= t < b - 0.02:
                if e and e in self.prets and os.path.exists(self.prets[e]):
                    return a, b, self.prets[e]
                return None
        return None

    def resume(self):
        et = self.etats()
        n = len(et)
        prets = len([x for x in et if x[2] == "pret"])
        return prets, n

    # ---- préparation, une tranche à la fois, la plus proche du curseur d'abord
    def _suivante(self):
        if not self.actif or self._ferme or (self.tache is not None and self.tache.isRunning()):
            return
        t0 = self.ed.timeline.position
        attente = [(a, b, e) for a, b, e in self.tranches if e and not (e in self.prets and os.path.exists(self.prets[e]))]
        if not attente:
            return
        attente.sort(key=lambda x: (x[0] + 1e-3 < t0 - TRANCHE, abs(x[0] - t0)))      # devant le curseur d'abord
        a, b, e = attente[0]
        self._lancer(a, b, e)

    def _lancer(self, a, b, e):
        from . import export
        from .taches import Tache
        projet = copy.deepcopy(self.ed.projet)
        sortie = os.path.join(self.dossier, f"{e}.mp4")
        st = list(self.ed.projet.d.get("sous_titres") or [])
        params = self.ed.params

        def travail(tache):
            p = export.extrait(projet, a, b)
            ex = export.Exportateur(p, sortie + ".part.mp4", "whatsapp", qualite="allegee", encodeur="libx264", params=params)
            try:
                ex.lancer(progression=lambda f: tache.avancer(f), arret=lambda: tache.arret,
                          sous_titres=[(x[0] - a, x[1] - a) + tuple(x[2:]) for x in st if x[1] > a and x[0] < b])
            finally:
                ex.nettoyer()
            os.replace(sortie + ".part.mp4", sortie)
            return sortie
        t = Tache(travail, _("Préparation de la lecture"))
        self.tache = t
        self._en_cours = e
        self.ed.taches.append(t)
        from . import activite
        activite.centre().suivre(t, _("Préparation de la lecture ({a} → {b})", a=_tc(a), b=_tc(b)))
        self.change.emit()

        def fini(r, err, t=t, e=e):
            if t in self.ed.taches:
                self.ed.taches.remove(t)
            self.tache = None
            self._en_cours = None
            if not err and r:
                self.prets[e] = r
                self._nettoyer_cache()
            self.change.emit()
            if not self._ferme:
                QTimer.singleShot(50, self._suivante)
        t.fini.connect(fini)
        t.start()

    def _nettoyer_cache(self):
        if len(self.prets) <= MAX_CACHE:
            return
        utiles = {e for _a, _b, e in self.tranches if e}
        for e in [k for k in self.prets if k not in utiles][: len(self.prets) - MAX_CACHE]:
            try:
                os.remove(self.prets.pop(e))
            except OSError:
                pass

    def arreter_tache(self):
        t = self.tache
        if t is not None and t.isRunning():
            t.stopper()
            t.wait(5000)

    def fermer(self):
        self._ferme = True
        self.minuteur.stop()
        self.arreter_tache()
        import shutil
        shutil.rmtree(self.dossier, ignore_errors=True)


# ------------------------------------------------------------------ pellicule de balayage
class Pellicules:
    """Images d'un rush en petit, extraites une fois en arrière-plan, pour balayer sans attendre."""

    def __init__(self, largeur=480):
        self.largeur = largeur
        self.images = {}            # media_id -> (pas, [octets jpeg])
        self._en_cours = set()
        self._verrou = threading.Lock()

    def image(self, m, t_src):
        """Octets JPEG de l'image la plus proche de t_src, ou None si la pellicule n'est pas encore prête (elle se lance)."""
        e = self.images.get(m["id"])
        if e is None:
            self._lancer(m)
            return None
        pas, imgs = e
        if not imgs:
            return None
        i = max(0, min(len(imgs) - 1, int(round(t_src / pas))))
        return imgs[i]

    def _lancer(self, m):
        with self._verrou:
            if m["id"] in self._en_cours or m.get("genre") != "video":
                return
            self._en_cours.add(m["id"])
        threading.Thread(target=self._extraire, args=(m,), daemon=True).start()

    def _extraire(self, m):
        from . import moteur
        duree = float((m.get("fiche") or {}).get("duree") or 0)
        ips = 8 if duree <= 300 else 4 if duree <= 900 else 2
        src = m.get("proxy") or m["chemin"]
        cmd = [moteur.ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", src, "-an", "-vf", f"fps={ips},scale={self.largeur}:-2",
               "-q:v", "6", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1"]
        imgs = []
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=600, **moteur._sans_console())
            data = r.stdout
            i = 0
            while True:
                d = data.find(b"\xff\xd8", i)
                if d < 0:
                    break
                f = data.find(b"\xff\xd9", d)
                if f < 0:
                    break
                imgs.append(data[d:f + 2])
                i = f + 2
        except Exception:       # noqa: BLE001 : pas de pellicule, le balayage passe par FFmpeg image par image
            imgs = []
        self.images[m["id"]] = (1.0 / ips, imgs)
        with self._verrou:
            self._en_cours.discard(m["id"])


def _tc(t):
    m, s = divmod(max(0.0, float(t)), 60)
    return f"{int(m)}:{s:04.1f}"
