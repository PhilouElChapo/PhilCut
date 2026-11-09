"""Moteur d'effets GL (0.9.35) : les effets du catalogue « effets_gl.json » sont des shaders GLSL, exécutés par la carte
graphique, les MÊMES sur PC (ici, via moderngl) et sur Android (Media3, OpenGL ES 3.0) : même image des deux côtés.

Conventions d'un shader (corps seulement ; l'entête est ajoutée ici selon la plate-forme) :
  uniform sampler2D image;   l'image du plan (déjà cadrée à la taille du projet)
  uniform vec2 taille;       largeur, hauteur en pixels
  uniform float temps;       secondes depuis le début du plan (horloge du montage)
  uniform float duree;       durée du plan
  uniform float progres;     temps / duree (0 → 1)
  uniform float p_<cle>;     un réglage de l'effet (booléen = 0 ou 1, choix = rang)
  in vec2 uv;                (0,0) = coin HAUT-gauche, (1,1) = bas-droit (Android retourne l'axe vertical pour suivre)
  out vec4 couleur;
Fonctions fournies : hash(vec2), bruit(vec2), lum(vec3), lire(vec2) (lecture bornée de l'image).

Sans carte graphique utilisable (machine virtuelle, pilote trop ancien), chaque effet a une approximation FFmpeg
(« ffmpeg » dans le catalogue) ou, à défaut, est ignoré à l'export avec un message.
"""
import hashlib
import json
import os
import subprocess
import threading

ENTETE_PC = "#version 330\n"
ENTETE_ES = "#version 300 es\nprecision highp float;\n"
COMMUN = """
uniform sampler2D image;
uniform vec2 taille;
uniform float temps;
uniform float duree;
uniform float progres;
in vec2 uv;
out vec4 couleur;
float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float bruit(vec2 p) {
    vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
float lum(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
vec4 lire(vec2 p) { return texture(image, clamp(p, vec2(0.0), vec2(1.0))); }
"""
SOMMETS = """
in vec2 pos;
out vec2 uv;
void main() { uv = vec2(pos.x * 0.5 + 0.5, pos.y * 0.5 + 0.5); gl_Position = vec4(pos, 0.0, 1.0); }
"""

_VERROU = threading.RLock()
_CTX = {"possible": None, "raison": "", "ctx": None, "programmes": {}}
_FIL = {"fil": None, "file": None}


def _boucle(file):
    """Fil GL unique : le contexte OpenGL y est créé et n'en sort jamais (un contexte GL est lié à son fil)."""
    while True:
        fn, res = file.get()
        try:
            res["valeur"] = fn()
        except BaseException as e:      # noqa: BLE001
            res["erreur"] = e
        res["fait"].set()


def executer(fn):
    """Exécute fn() dans le fil GL et renvoie son résultat (ou relève son erreur)."""
    import queue
    with _VERROU:
        if _FIL["fil"] is None:
            _FIL["file"] = queue.Queue()
            _FIL["fil"] = threading.Thread(target=_boucle, args=(_FIL["file"],), daemon=True, name="PhilCut-GL")
            _FIL["fil"].start()
    if threading.current_thread() is _FIL["fil"]:
        return fn()
    res = {"fait": threading.Event()}
    _FIL["file"].put((fn, res))
    res["fait"].wait()
    if "erreur" in res:
        raise res["erreur"]
    return res.get("valeur")
_CATALOGUE = {"effets": {}, "shaders": {}, "charge": False}


# ------------------------------------------------------------------ catalogue
def charger(reseau=False):
    """Lit catalogue/effets_gl.json (en ligne si demandé, sinon copie locale ou fichier livré)."""
    from .catalogue_ligne import charger as ch
    d = ch("effets_gl.json", reseau)
    _CATALOGUE["shaders"] = dict(d.get("shaders") or {})
    _CATALOGUE["effets"] = {e["id"]: e for e in d.get("effets") or [] if e.get("id") and e.get("shader") in _CATALOGUE["shaders"]}
    _CATALOGUE["familles"] = d.get("familles") or []
    _CATALOGUE["version"] = d.get("version", 0)
    _CATALOGUE["charge"] = True
    return _CATALOGUE


def catalogue():
    if not _CATALOGUE["charge"]:
        charger()
    return _CATALOGUE


def est_gl(ident):
    return ident in catalogue()["effets"]


def effet(ident):
    return catalogue()["effets"].get(ident)


def parametres(ident):
    """[(cle, nom, type, defaut, min, max)] au format du catalogue d'effets de PhilCut."""
    from .catalogue_ligne import localise
    e = effet(ident) or {}
    sh = catalogue()["shaders"].get(e.get("shader"), {})
    out = []
    for p in sh.get("parametres") or []:
        d = (e.get("reglages") or {}).get(p["cle"], p.get("defaut", 0.0))
        if p.get("type") == "choix":
            out.append((p["cle"], localise(p.get("nom")) or p["cle"], "choix", d,
                        [(i, localise(n)) for i, n in enumerate(p.get("choix") or [])], 0))
        else:
            out.append((p["cle"], localise(p.get("nom")) or p["cle"], p.get("type", "float"), d, p.get("min", 0.0), p.get("max", 1.0)))
    return out


def valeurs(ident, params=None):
    """Réglages complets d'un effet posé : ceux du shader, puis ceux de la variante, puis ceux de l'utilisateur."""
    e = effet(ident) or {}
    sh = catalogue()["shaders"].get(e.get("shader"), {})
    v = {p["cle"]: p.get("defaut", 0.0) for p in sh.get("parametres") or []}
    v.update(e.get("reglages") or {})
    v.update(params or {})
    return v


# ------------------------------------------------------------------ contexte GL
def _creer():
    import sys
    import moderngl
    essais = ([dict(backend="egl"), {}] if not os.environ.get("DISPLAY") else [{}, dict(backend="egl")]) if sys.platform.startswith("linux") else [{}]
    derniere = ""
    for k in essais:
        try:
            return moderngl.create_standalone_context(require=330, **k), ""
        except Exception as e:      # noqa: BLE001
            derniere = str(e)[:200]
    return None, derniere


def contexte():
    """Contexte OpenGL hors écran (moderngl), dans le fil GL ; None si OpenGL est indisponible (voir raison())."""
    if _CTX["possible"] is False:
        return None
    if _CTX["ctx"] is not None:
        return _CTX["ctx"]

    def creer():
        if _CTX["ctx"] is not None or _CTX["possible"] is False:
            return _CTX["ctx"]
        if os.environ.get("PHILCUT_SANS_GL"):
            _CTX.update(possible=False, raison="désactivé (PHILCUT_SANS_GL)")
            return None
        try:
            import moderngl  # noqa: F401
        except ImportError as e:
            _CTX.update(possible=False, raison=f"moderngl absent ({e})")
            return None
        ctx, err = _creer()
        if ctx is None:
            _CTX.update(possible=False, raison=err)
            return None
        _CTX.update(possible=True, raison=ctx.info.get("GL_RENDERER", ""), ctx=ctx)
        return ctx
    return executer(creer)


def disponible():
    return contexte() is not None


def raison():
    contexte()
    return _CTX["raison"]


def source(nom_shader, plateforme="pc"):
    """Texte complet du shader de fragments (pour les tests et pour l'appli Android)."""
    sh = catalogue()["shaders"][nom_shader]
    params = "".join(f"uniform float p_{p['cle']};\n" for p in sh.get("parametres") or [])
    return (ENTETE_ES if plateforme == "es" else ENTETE_PC) + COMMUN + params + sh["glsl"]


def _programme(nom_shader):
    """Programme compilé (dans le fil GL)."""
    progs = _CTX["programmes"]
    if nom_shader in progs:
        return progs[nom_shader]
    ctx = _CTX["ctx"]
    prog = ctx.program(vertex_shader=ENTETE_PC + SOMMETS, fragment_shader=source(nom_shader))
    import numpy as np
    quad = ctx.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype="f4").tobytes())
    vao = ctx.simple_vertex_array(prog, quad, "pos")
    progs[nom_shader] = (prog, vao)
    return prog, vao


class Chaine:
    """Applique une suite d'effets GL à des images L×H (RVB 8 bits) : textures et tampons gardés d'une image à l'autre.
    Tout le travail OpenGL se fait dans le fil GL (executer)."""

    def __init__(self, effets, largeur, hauteur, duree):
        if contexte() is None:
            raise RuntimeError("OpenGL indisponible : " + raison())
        self.L, self.H, self.duree = int(largeur), int(hauteur), max(0.01, float(duree))
        self.effets = [(e["id"], valeurs(e["id"], e.get("params"))) for e in effets if est_gl(e["id"])]
        executer(self._preparer)

    def _preparer(self):
        ctx = _CTX["ctx"]
        self.tex = [ctx.texture((self.L, self.H), 3) for _i in range(2)]
        self.fbo = [ctx.framebuffer(color_attachments=[t]) for t in self.tex]
        self.entree = ctx.texture((self.L, self.H), 3)
        for t in self.tex + [self.entree]:
            t.repeat_x = t.repeat_y = False
        for ident, _v in self.effets:
            _programme(effet(ident)["shader"])

    def appliquer(self, octets, temps):
        """octets : image RVB L×H, ligne du haut en premier ; renvoie l'image traitée au même format."""
        if not self.effets:
            return octets
        return executer(lambda: self._appliquer(octets, temps))

    def _appliquer(self, octets, temps):
        ctx = _CTX["ctx"]
        self.entree.write(octets)
        src = self.entree
        for k, (ident, v) in enumerate(self.effets):
            prog, vao = _programme(effet(ident)["shader"])
            for nom, val in (("taille", (float(self.L), float(self.H))), ("temps", float(temps)), ("duree", self.duree),
                             ("progres", max(0.0, min(1.0, float(temps) / self.duree)))):
                if nom in prog:
                    prog[nom].value = val
            for cle, val in v.items():
                u = "p_" + cle
                if u in prog:
                    prog[u].value = float(val) if not isinstance(val, bool) else (1.0 if val else 0.0)
            if "image" in prog:
                prog["image"].value = 0
            src.use(0)
            self.fbo[k % 2].use()
            ctx.viewport = (0, 0, self.L, self.H)
            vao.render(mode=ctx.TRIANGLE_STRIP)
            src = self.tex[k % 2]
        return self.fbo[(len(self.effets) - 1) % 2].read(components=3)

    def liberer(self):
        def lib():
            for o in getattr(self, "tex", []) + getattr(self, "fbo", []) + ([self.entree] if hasattr(self, "entree") else []):
                try:
                    o.release()
                except Exception:      # noqa: BLE001
                    pass
        executer(lib)


def appliquer_image(effets, image_rvb, temps=0.0, duree=5.0):
    """Une image numpy (H, L, 3) uint8 → image traitée (pour l'aperçu et les tests)."""
    import numpy as np
    h, w = image_rvb.shape[:2]
    ch = Chaine(effets, w, h, duree)
    try:
        out = ch.appliquer(np.ascontiguousarray(image_rvb, dtype=np.uint8).tobytes(), temps)
    finally:
        ch.liberer()
    return np.frombuffer(out, dtype=np.uint8).reshape(h, w, 3)


# ------------------------------------------------------------------ rendu d'un plan
def cle_cache(*morceaux):
    return hashlib.sha1(json.dumps(morceaux, sort_keys=True, default=str).encode()).hexdigest()[:20]


def dossier_cache():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "cache_gl")
    os.makedirs(d, exist_ok=True)
    return d


def rendre(entree, filtres_tete, effets, largeur, hauteur, cadence, duree, sortie, avance=0.0, progression=None, arret=lambda: False,
           duree_plan=None):
    """Décode « entree » (arguments FFmpeg avant -i compris), applique filtres_tete (cadrage, vitesse…) puis les effets
    GL image par image, et écrit un MP4 intermédiaire de très bonne qualité. Renvoie sortie."""
    from .moteur import ffmpeg, _sans_console
    L, H = int(largeur), int(hauteur)
    graphe = "[0:v]" + ",".join(filtres_tete + [f"scale={L}:{H}", "format=rgb24"]) + "[o]"
    dec = subprocess.Popen([ffmpeg(), "-v", "error", *entree, "-filter_complex", graphe, "-map", "[o]", "-t", f"{duree:.3f}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, **_sans_console())
    tmp = sortie + ".part.mp4"
    enc = subprocess.Popen([ffmpeg(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L}x{H}", "-r", str(cadence),
                            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", tmp],
                           stdin=subprocess.PIPE, stderr=subprocess.PIPE, **_sans_console())
    ch = Chaine(effets, L, H, duree_plan or duree)
    taille = L * H * 3
    total = max(1, int(round(duree * cadence)))
    i = 0
    try:
        while True:
            if arret():
                break
            octets = dec.stdout.read(taille)
            if not octets or len(octets) < taille:
                break
            enc.stdin.write(ch.appliquer(octets, avance + i / float(cadence)))
            i += 1
            if progression and i % 5 == 0:
                progression(min(1.0, i / total))
    finally:
        ch.liberer()
        try:
            enc.stdin.close()
        except OSError:
            pass
        enc.wait()
        dec.stdout.close()
        dec.wait()
    if arret() or i == 0 or enc.returncode != 0:
        try:
            os.remove(tmp)
        except OSError:
            pass
        if arret():
            return None
        raise RuntimeError("rendu GL impossible : " + (dec.stderr.read().decode("utf-8", "replace")[-300:] if dec.stderr else ""))
    os.replace(tmp, sortie)
    return sortie


def filtre_secours(ident, params=None):
    """Approximation FFmpeg d'un effet GL quand la carte graphique n'est pas utilisable ; None s'il n'y en a pas."""
    e = effet(ident) or {}
    sh = catalogue()["shaders"].get(e.get("shader"), {})
    f = e.get("ffmpeg") or sh.get("ffmpeg")
    if not f:
        return None
    v = valeurs(ident, params)
    try:
        return f.format(**{k: (float(x) if not isinstance(x, bool) else int(x)) for k, x in v.items()})
    except (KeyError, ValueError, IndexError):
        return None
