"""Calques generes par PhilCut lui-meme (numpy + OpenCV) : feu d'artifice, eclairs, fuites de lumiere, pluie de
code Matrix, transitions puzzle / explosion / glitch / dissolution en code, halo autour d'une personne.

Chaque generateur ecrit une suite d'images PNG avec transparence (RGBA) dans un dossier temporaire et renvoie
le motif « dossier/%05d.png » ; l'export les superpose au bon moment. Tout est fait maison : aucune image
tierce, donc rien a redistribuer.
"""
import math, os, random

import numpy as np

try:
    import cv2
except ImportError:                 # OpenCV absent : les effets generes sont desactives proprement
    cv2 = None

_CHARS = "0123456789ABCDEFZXYQW<>+-=*/|#$%&@アイウエオカキクケコサシスセソ"


def _rng(graine):
    return random.Random(graine)


def _ecrire(dossier, i, img):
    cv2.imwrite(os.path.join(dossier, f"{i:05d}.png"), img)


def _vide(L, H):
    return np.zeros((H, L, 4), dtype=np.uint8)


def _glyphes(taille):
    """Petites images de caracteres (Hershey), vert Matrix, pour la pluie de code."""
    out = []
    for ch in _CHARS:
        g = np.zeros((taille, taille, 4), dtype=np.uint8)
        cv2.putText(g, ch if ord(ch) < 128 else random.choice("0123456789"), (1, taille - 3), cv2.FONT_HERSHEY_SIMPLEX,
                    taille / 28.0, (80, 255, 120, 255), max(1, taille // 12), cv2.LINE_AA)
        out.append(g)
    return out


def _poser(img, g, x, y, alpha=1.0):
    h, w = g.shape[:2]
    H, L = img.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(L, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    src = g[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    dst = img[y0:y1, x0:x1].astype(np.float32)
    a = (src[..., 3:4] / 255.0) * alpha
    dst[..., :3] = src[..., :3] * a + dst[..., :3] * (1 - a)
    dst[..., 3:4] = np.maximum(dst[..., 3:4], src[..., 3:4] * alpha)
    img[y0:y1, x0:x1] = dst.astype(np.uint8)


# ------------------------------------------------------------------ pluie de code
def pluie_code(dossier, L, H, cadence, duree, densite=1.0, opacite=0.7, graine=1, couverture=None):
    """couverture(fraction du temps) -> 0..1 : part de l'image occupee (pour la dissolution en code)."""
    rng = _rng(graine)
    taille = max(10, int(H / 40))
    gl = _glyphes(taille)
    cols = int(L / taille)
    n = int(duree * cadence)
    chutes = [{"y": rng.uniform(-H, 0), "v": rng.uniform(H / 2.5, H / 1.2), "l": rng.randint(6, 22), "actif": rng.random() < 0.55 * densite}
              for _ in range(cols)]
    for i in range(n):
        img = _vide(L, H)
        t = i / max(1, n - 1)
        for c, ch in enumerate(chutes):
            if not ch["actif"]:
                if rng.random() < 0.02 * densite:
                    ch.update(actif=True, y=-taille * ch["l"])
                continue
            ch["y"] += ch["v"] / cadence
            tete = int(ch["y"] / taille)
            for k in range(ch["l"]):
                ligne = tete - k
                if 0 <= ligne * taille < H:
                    g = gl[(ligne * 7 + c * 13 + (i // 3)) % len(gl)]
                    a = opacite * (1.0 if k == 0 else max(0.08, 1 - k / ch["l"]))
                    if couverture is not None and (ligne / max(1, H / taille)) > couverture(t):
                        continue
                    _poser(img, g, c * taille, ligne * taille, a)
            if (tete - ch["l"]) * taille > H:
                ch.update(y=-taille * rng.randint(2, 20), v=rng.uniform(H / 2.5, H / 1.2), l=rng.randint(6, 22), actif=rng.random() < 0.7 * densite)
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


# ------------------------------------------------------------------ particules : feu d'artifice, eclairs, flashs
def feu_artifice(dossier, L, H, cadence, duree, quantite=6, graine=2):
    rng = _rng(graine)
    n = int(duree * cadence)
    gerbes = []
    for q in range(int(quantite)):
        t0 = rng.uniform(0.05, max(0.06, duree - 1.6))
        coul = rng.choice([(90, 160, 255), (255, 200, 90), (120, 255, 160), (255, 120, 200), (255, 255, 255), (80, 220, 255)])
        cx, cy = rng.uniform(0.15, 0.85) * L, rng.uniform(0.12, 0.55) * H
        parts = []
        for _ in range(rng.randint(60, 120)):
            ang, v = rng.uniform(0, 2 * math.pi), rng.uniform(0.25, 1.0) * H / 3
            parts.append([cx, cy, math.cos(ang) * v, math.sin(ang) * v])
        gerbes.append({"t0": t0, "coul": coul, "parts": parts, "vie": rng.uniform(1.2, 1.8)})
    traine = _vide(L, H).astype(np.float32)
    for i in range(n):
        t = i / cadence
        traine *= 0.86
        img = traine.copy()
        for g in gerbes:
            age = t - g["t0"]
            if age < 0 or age > g["vie"]:
                continue
            a = max(0.0, 1 - age / g["vie"])
            if age < 0.08:
                cv2.circle(img, (int(g["parts"][0][0]), int(g["parts"][0][1])), int(H * 0.03), (255, 255, 255, 255), -1)
            for p in g["parts"]:
                x = p[0] + p[2] * age
                y = p[1] + p[3] * age + 0.5 * (H * 0.35) * age * age
                r = max(1, int(H * 0.004 * (1.2 - age / g["vie"])))
                b, gg, rr = g["coul"]
                cv2.circle(img, (int(x), int(y)), r, (b, gg, rr, int(255 * a)), -1)
        traine = np.maximum(traine, img * 0.9)
        _ecrire(dossier, i, np.clip(img, 0, 255).astype(np.uint8))
    return os.path.join(dossier, "%05d.png"), n


def eclairs(dossier, L, H, cadence, duree, quantite=4, graine=3):
    rng = _rng(graine)
    n = int(duree * cadence)
    instants = sorted(rng.uniform(0.1, max(0.2, duree - 0.3)) for _ in range(int(quantite)))
    for i in range(n):
        t = i / cadence
        img = _vide(L, H)
        for t0 in instants:
            age = t - t0
            if 0 <= age < 0.25:
                a = int(255 * max(0, 1 - age / 0.25))
                x = int(rng.uniform(0.2, 0.8) * L) if age < 1 / cadence else None
                pts = []
                xx, yy = int(L * (0.3 + 0.4 * ((t0 * 97) % 1))), 0
                while yy < H:
                    pts.append((xx, yy))
                    yy += rng.randint(H // 30, H // 12)
                    xx += rng.randint(-L // 20, L // 20)
                for p, q in zip(pts, pts[1:]):
                    cv2.line(img, p, q, (255, 240, 200, a), max(2, H // 240), cv2.LINE_AA)
                    cv2.line(img, p, q, (255, 255, 255, a), max(1, H // 600), cv2.LINE_AA)
                if age < 0.07:
                    img[..., :3] = np.maximum(img[..., :3], 255)
                    img[..., 3] = np.maximum(img[..., 3], int(90 * (1 - age / 0.07)))
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


def fuite_lumiere(dossier, L, H, cadence, duree, force=0.6, graine=4):
    rng = _rng(graine)
    n = int(duree * cadence)
    yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)
    for i in range(n):
        t = i / max(1, n - 1)
        img = _vide(L, H)
        cx = L * (-0.2 + 1.4 * t)
        cy = H * (0.2 + 0.5 * math.sin(t * 3.1))
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (0.55 * H)
        a = np.clip(1 - d, 0, 1) ** 2 * 255 * force * math.sin(math.pi * t)
        img[..., 0] = 60
        img[..., 1] = 140
        img[..., 2] = 255
        img[..., 3] = a.astype(np.uint8)
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


# ------------------------------------------------------------------ transitions a partir des images des plans
def puzzle(dossier, L, H, cadence, duree, images_entrantes, pieces=4):
    """Le plan qui arrive est decoupe en `pieces` x `pieces` morceaux inclines qui glissent en place, puis l'image
    zoome jusqu'au plein cadre. images_entrantes(i) -> image BGR (L x H) du plan entrant a l'image i."""
    n = int(duree * cadence)
    k = max(2, int(pieces ** 0.5)) if pieces > 3 else 2
    rng = _rng(5)
    offs = [(rng.uniform(-0.5, 0.5) * L, rng.uniform(-0.5, 0.5) * H, rng.uniform(-28, 28)) for _ in range(k * k)]
    for i in range(n):
        t = i / max(1, n - 1)
        src = images_entrantes(i)
        img = _vide(L, H)
        if t < 0.7:
            e = _ease(t / 0.7)
            pw, ph = L / k, H / k
            for r in range(k):
                for c in range(k):
                    ox, oy, ang = offs[r * k + c]
                    piece = src[int(r * ph):int((r + 1) * ph), int(c * pw):int((c + 1) * pw)]
                    rgba = cv2.cvtColor(piece, cv2.COLOR_BGR2BGRA)
                    cv2.rectangle(rgba, (0, 0), (rgba.shape[1] - 1, rgba.shape[0] - 1), (255, 255, 255, 255), max(1, H // 300))
                    cx, cy = c * pw + pw / 2 + ox * (1 - e), r * ph + ph / 2 + oy * (1 - e)
                    M = cv2.getRotationMatrix2D((pw / 2, ph / 2), ang * (1 - e), 0.92 + 0.08 * e)
                    M[0, 2] += cx - pw / 2
                    M[1, 2] += cy - ph / 2
                    warp = cv2.warpAffine(rgba, M, (L, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
                    _poser(img, warp, 0, 0, 1.0)
        else:
            e = _ease((t - 0.7) / 0.3)
            z = 0.92 + 0.08 * e
            M = cv2.getRotationMatrix2D((L / 2, H / 2), 0, z)
            img = cv2.warpAffine(cv2.cvtColor(src, cv2.COLOR_BGR2BGRA), M, (L, H), borderValue=(0, 0, 0, 255))
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


def explosion(dossier, L, H, cadence, duree, image_sortante, pieces=16):
    """Le plan precedent (une image figee) eclate en fragments qui s'envolent."""
    n = int(duree * cadence)
    k = max(2, int(round(pieces ** 0.5)))
    rng = _rng(6)
    src = cv2.cvtColor(image_sortante, cv2.COLOR_BGR2BGRA)
    vits = [(rng.uniform(-1.2, 1.2) * L, rng.uniform(-1.4, 0.4) * H, rng.uniform(-240, 240)) for _ in range(k * k)]
    pw, ph = L / k, H / k
    for i in range(n):
        t = i / max(1, n - 1)
        img = _vide(L, H)
        for r in range(k):
            for c in range(k):
                vx, vy, va = vits[r * k + c]
                piece = src[int(r * ph):int((r + 1) * ph), int(c * pw):int((c + 1) * pw)].copy()
                piece[..., 3] = int(255 * max(0, 1 - t * 1.1))
                cx, cy = c * pw + pw / 2 + vx * t, r * ph + ph / 2 + vy * t + 0.9 * H * t * t
                M = cv2.getRotationMatrix2D((pw / 2, ph / 2), va * t, 1 - 0.3 * t)
                M[0, 2] += cx - pw / 2
                M[1, 2] += cy - ph / 2
                warp = cv2.warpAffine(piece, M, (L, H), borderValue=(0, 0, 0, 0))
                _poser(img, warp, 0, 0, 1.0)
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


def glitch_transition(dossier, L, H, cadence, duree, graine=7):
    rng = _rng(graine)
    n = max(2, int(duree * cadence))
    for i in range(n):
        t = i / max(1, n - 1)
        img = _vide(L, H)
        force = math.sin(math.pi * t)
        for _ in range(int(14 * force) + 1):
            y = rng.randint(0, H - 1)
            h = rng.randint(2, max(3, H // 30))
            coul = rng.choice([(255, 80, 80), (80, 255, 80), (80, 80, 255), (255, 255, 255)])
            img[y:y + h, :, :3] = coul
            img[y:y + h, :, 3] = rng.randint(60, 200)
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


def balayage(dossier, L, H, cadence, duree, couleur=(20, 20, 20)):
    n = max(2, int(duree * cadence))
    for i in range(n):
        t = i / max(1, n - 1)
        img = _vide(L, H)
        larg = int(L * 0.18)
        x = int(-larg + (L + larg) * _ease(t))
        img[:, max(0, x):min(L, x + larg), :3] = couleur
        img[:, max(0, x):min(L, x + larg), 3] = 235
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


def dissolution_code(dossier, L, H, cadence, duree, graine=8):
    """Pluie de code qui recouvre tout puis se retire : transition Matrix."""
    return pluie_code(dossier, L, H, cadence, duree, densite=2.2, opacite=0.95, graine=graine,
                      couverture=lambda t: 1.0 if t < 0.5 else max(0.0, 1 - (t - 0.5) * 2) * 1.0 + (1 if t < 0.5 else 0))


def halo(dossier, L, H, cadence, duree, masques, couleur="#ffd36b", force=1.0):
    """Aura lumineuse autour d'un masque de personne. masques(i) -> masque 0..255 (H x L) ou None."""
    n = int(duree * cadence)
    hexa = couleur.lstrip("#")
    r, g, b = int(hexa[0:2], 16), int(hexa[2:4], 16), int(hexa[4:6], 16)
    for i in range(n):
        img = _vide(L, H)
        m = masques(i)
        if m is not None:
            k = max(9, int(H * 0.05 * force)) | 1
            dil = cv2.dilate(m, np.ones((k // 3 | 1, k // 3 | 1), np.uint8))
            fl = cv2.GaussianBlur(dil, (k, k), 0).astype(np.float32)
            fl = np.clip(fl - m.astype(np.float32) * 0.9, 0, 255)
            puls = 0.75 + 0.25 * math.sin(i / cadence * 4)
            img[..., 0], img[..., 1], img[..., 2] = b, g, r
            img[..., 3] = (fl * puls).astype(np.uint8)
        _ecrire(dossier, i, img)
    return os.path.join(dossier, "%05d.png"), n


def _ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


# ------------------------------------------------------------------ images d'un media pour les transitions
def lecteur_images(chemin, debut, L, H, cadence):
    """images(i) -> image BGR LxH du media a partir de `debut` (lecture OpenCV, redimensionnee)."""
    cap = cv2.VideoCapture(chemin)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, debut) * 1000)
    cache = {}
    derniere = [None]

    def images(i):
        if i in cache:
            return cache[i]
        ok, fr = cap.read()
        if not ok:
            fr = derniere[0] if derniere[0] is not None else np.zeros((H, L, 3), dtype=np.uint8)
        else:
            fr = cv2.resize(fr, (L, H), interpolation=cv2.INTER_AREA)
            derniere[0] = fr
        cache[i] = fr
        if len(cache) > 4:
            cache.pop(min(cache))
        return fr
    images.fermer = cap.release
    return images


def image_fixe(chemin, t, L, H):
    cap = cv2.VideoCapture(chemin)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        return np.zeros((H, L, 3), dtype=np.uint8)
    return cv2.resize(fr, (L, H), interpolation=cv2.INTER_AREA)
