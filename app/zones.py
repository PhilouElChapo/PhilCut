"""Zones tracées dans l'image (0.3.3) : flou, mosaïque, cache de couleur, assombrir, éclaircir, noir et blanc.

Une zone se trace à la souris dans l'aperçu ; elle se range avec les Goodies (genre « zone ») : elle a sa barre dans la
timeline (déplaçable, rognable, clic droit), se règle dans l'Inspecteur, se déplace et se redimensionne dans l'image
et se supprime comme tout le reste.

Elle peut suivre ce qu'elle couvre (un visage, une plaque, un logo) : le moteur de suivi d'OpenCV analyse le rush image
par image depuis l'instant où on l'a tracée et garde sa trajectoire (centre et taille) en temps du montage. On peut la
corriger à n'importe quel instant (on la retrace là, le suivi est refait à partir de cet instant) ou la figer.

Coordonnées : centre x, centre y, largeur, hauteur, normalisés (0..1) sur l'image du montage.
"""
import os

from .langue import _
from .projet import _id

TRAITEMENTS = [("flou", "Flou (visage, plaque, écran)"), ("mosaique", "Mosaïque (gros pixels)"), ("cache", "Cache de couleur unie"),
               ("assombrir", "Assombrir"), ("eclaircir", "Eclaircir"), ("noir_blanc", "Noir et blanc")]
FORMES = [("rect", "Rectangle"), ("ovale", "Ovale")]


def nouvelle(debut, fin, x, y, l, h, traitement="flou"):
    return {"id": _id(), "genre": "zone", "debut": float(debut), "fin": float(fin), "x": round(x, 4), "y": round(y, 4),
            "l": round(max(0.01, l), 4), "h": round(max(0.01, h), 4), "traitement": traitement, "force": 0.6,
            "forme": "rect", "couleur": "#000000", "options": {}, "valeurs": []}


def libelle(z):
    t = dict(TRAITEMENTS).get(z.get("traitement", "flou"), "?").split(" (")[0]
    return _("Zone : {t}", t=_(t)) + (" · " + _("suivie") if (z.get("suivi") or {}).get("positions") else "")


def rect_a(z, t):
    """(centre x, centre y, largeur, hauteur) de la zone à l'instant t du montage (trajectoire si elle est suivie)."""
    pos = (z.get("suivi") or {}).get("positions") or []
    if pos:
        from . import suivi
        return tuple(float(suivi.valeur(pos, t, k)) for k in (1, 2, 3, 4))
    return float(z.get("x", 0.5)), float(z.get("y", 0.5)), float(z.get("l", 0.2)), float(z.get("h", 0.2))


def deplacer(z, x, y, t):
    """Nouvelle position du centre ; une zone suivie est décalée en bloc (toute sa trajectoire)."""
    pos = (z.get("suivi") or {}).get("positions") or []
    if pos:
        cx, cy = rect_a(z, t)[:2]
        dx, dy = x - cx, y - cy
        z["suivi"]["positions"] = [(p[0], round(p[1] + dx, 4), round(p[2] + dy, 4), p[3], p[4]) for p in pos]
    z["x"], z["y"] = round(x, 4), round(y, 4)


def redimensionner(z, x, y, l, h, t):
    pos = (z.get("suivi") or {}).get("positions") or []
    if pos:
        cx, cy, l0, h0 = rect_a(z, t)
        fx, fy = l / max(1e-4, l0), h / max(1e-4, h0)
        dx, dy = x - cx, y - cy
        z["suivi"]["positions"] = [(p[0], round(p[1] + dx, 4), round(p[2] + dy, 4), round(p[3] * fx, 4), round(p[4] * fy, 4)) for p in pos]
    z["x"], z["y"], z["l"], z["h"] = round(x, 4), round(y, 4), round(max(0.01, l), 4), round(max(0.01, h), 4)


# ------------------------------------------------------------------ rendu FFmpeg
def _pair(v):
    return max(4, int(round(v / 2)) * 2)


def traitement_ffmpeg(z, w, h):
    """Filtres appliqués au morceau d'image découpé (w × h pixels)."""
    f = max(0.0, min(1.0, float(z.get("force", 0.6))))
    tr = z.get("traitement", "flou")
    if tr == "mosaique":
        bloc = max(4, int(min(w, h) * (0.05 + 0.2 * f)))
        return f"scale={max(1, w // bloc)}:{max(1, h // bloc)}:flags=area,scale={w}:{h}:flags=neighbor"
    if tr == "cache":
        c = (z.get("couleur") or "#000000").lstrip("#")
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4)) if len(c) == 6 else (0, 0, 0)
        return f"format=rgb24,lutrgb=r={r}:g={g}:b={b}"
    if tr == "assombrir":
        return f"eq=brightness={-0.08 - 0.35 * f:.3f}"
    if tr == "eclaircir":
        return f"eq=brightness={0.06 + 0.3 * f:.3f}"
    if tr == "noir_blanc":
        return "hue=s=0"
    rayon = int(4 + 36 * f)
    return (f"boxblur=luma_radius='min(min(w,h)/2-1,{rayon})':luma_power=2:"
            f"chroma_radius='min(min(cw,ch)/2-1,{max(1, rayon // 2)})':chroma_power=2")


def filtres(z, base, L, H, nom):
    """Chaîne de filtres qui applique la zone `z` sur le flux `base` ; renvoie (lignes, étiquette de sortie).
    `nom(prefixe)` fournit des étiquettes uniques."""
    from . import suivi
    d, fin = float(z["debut"]), float(z["fin"])
    pos = (z.get("suivi") or {}).get("positions") or []
    if pos:
        w = _pair(max(p[3] for p in pos) * L)
        h = _pair(max(p[4] for p in pos) * H)
        ex = suivi.expr([(p[0], p[1]) for p in pos])
        ey = suivi.expr([(p[0], p[2]) for p in pos])
        x = f"'clip(({ex})*{L}-{w}/2,0,{L}-{w})'"
        y = f"'clip(({ey})*{H}-{h}/2,0,{H}-{h})'"
    else:
        w = _pair(float(z.get("l", 0.2)) * L)
        h = _pair(float(z.get("h", 0.2)) * H)
        w, h = min(w, L - L % 2), min(h, H - H % 2)
        x = str(int(max(0, min(L - w, float(z.get("x", 0.5)) * L - w / 2))))
        y = str(int(max(0, min(H - h, float(z.get("y", 0.5)) * H - h / 2))))
    a, b, mz, out = nom("za"), nom("zb"), nom("zm"), nom("zo")
    chaine = f"[{b}]crop={w}:{h}:{x}:{y},{traitement_ffmpeg(z, w, h)}"
    if z.get("forme") == "ovale":
        chaine += (",format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':"
                   "a='255*clip((1-(pow(2*X/W-1,2)+pow(2*Y/H-1,2)))*6,0,1)'")
    lignes = [f"[{base}]split[{a}][{b}]", chaine + f"[{mz}]",
              f"[{a}][{mz}]overlay=x={x}:y={y}:format=auto:enable='between(t,{d:.3f},{fin:.3f})'[{out}]"]
    return lignes, out


# ------------------------------------------------------------------ suivi par analyse de l'image
def _clip_sous(projet, t):
    c = projet.clip_a(t, "video")
    if c is None:
        return None, None
    m = projet.media(c["media"])
    if not m or m.get("genre") != "video":
        return None, None
    return c, m


def _dims(m):
    v = (m.get("fiche") or {}).get("video") or {}
    return float(v.get("largeur") or 1920), float(v.get("hauteur") or 1080)


def _transfo(clip, m, L, H, t_src):
    """(échelle, décalage x, décalage y, largeur source, hauteur source) : pixel image = source × échelle + décalage."""
    lw, lh = _dims(m)
    mode = clip.get("ajustement", "remplir")
    if mode == "suivi" and (clip.get("suivi_cadre") or {}).get("positions"):
        from . import suivi
        wx, wy, cw, ch = suivi.fenetre_source(clip["suivi_cadre"], t_src, lw, lh, L, H)
        s = L / cw
        return s, -wx * s, -wy * s, lw, lh
    s = max(L / lw, H / lh) if mode == "remplir" else min(L / lw, H / lh)
    return s, (L - lw * s) / 2, (H - lh * s) / 2, lw, lh


def vers_source(clip, m, L, H, t_src, x, y, l, h):
    """Zone (image du montage, centre/taille normalisés) -> boîte (coin x, coin y, largeur, hauteur) normalisée de la source."""
    s, ox, oy, lw, lh = _transfo(clip, m, L, H, t_src)
    cx, cy = (x * L - ox) / s / lw, (y * H - oy) / s / lh
    bl, bh = l * L / s / lw, h * H / s / lh
    return (max(0.0, cx - bl / 2), max(0.0, cy - bh / 2), min(1.0, bl), min(1.0, bh))


def vers_image(clip, m, L, H, t_src, cx, cy, bl, bh):
    s, ox, oy, lw, lh = _transfo(clip, m, L, H, t_src)
    return ((cx * lw * s + ox) / L, (cy * lh * s + oy) / H, bl * lw * s / L, bh * lh * s / H)


class ErreurZone(Exception):
    pass


def suivre_modele(chemin, t0, t1, boite, pas=1.0 / 15, progression=None, arret=lambda: False, largeur_max=640):
    """Suit le contenu de `boite` (coin x, coin y, largeur, hauteur normalisés, source à t0) jusqu'à t1 par
    correspondance de motif : à chaque pas, le morceau d'image est recherché autour de sa dernière place, à trois
    tailles (il peut s'approcher ou s'éloigner) ; le motif se met à jour doucement (le visage tourne, la lumière change).
    Renvoie [(t_source, centre x, centre y, largeur, hauteur)] normalisés. S'il est perdu, la zone reste en place."""
    try:
        import cv2
        import numpy as np
    except ImportError as e:          # pragma: no cover
        raise ErreurZone("OpenCV absent") from e
    cap = cv2.VideoCapture(chemin)
    if not cap.isOpened():
        raise ErreurZone(_("Vidéo illisible pour le suivi."))
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t0) * 1000)
    ok, img = cap.read()
    if not ok:
        cap.release()
        raise ErreurZone(_("Image de départ illisible pour le suivi."))
    H0, L0 = img.shape[:2]
    ech = min(1.0, largeur_max / float(L0))

    def prep(im):
        if ech < 1:
            im = cv2.resize(im, (int(L0 * ech), int(H0 * ech)), interpolation=cv2.INTER_AREA)
        return cv2.GaussianBlur(im, (3, 3), 0).astype(np.float32)        # en couleur : le blanc se distingue du jaune
    g = prep(img)
    H, L = g.shape[:2]
    bw, bh = max(8.0, boite[2] * L), max(8.0, boite[3] * H)
    cx, cy = boite[0] * L + bw / 2, boite[1] * H + bh / 2

    def morceau(im, cx, cy, w, h):
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        x0, y0 = max(0, min(L - int(w), x0)), max(0, min(H - int(h), y0))
        return im[y0:y0 + int(h), x0:x0 + int(w)]
    bw0, bh0 = bw, bh
    noyau = 0.6                     # on suit le cœur de la zone : le bord tracé contient surtout du décor
    modele = morceau(g, cx, cy, bw * noyau, bh * noyau).copy()
    origine = modele.copy()
    cad = cap.get(cv2.CAP_PROP_FPS) or 30
    saut = max(1, int(round(pas * cad)))
    t = float(t0)
    points = [(round(t, 3), cx / L, cy / H, bw / L, bh / H)]
    total = max(1e-6, t1 - t0)
    vx = vy = 0.0                   # vitesse (pixels par pas) : on cherche d'abord là où il devrait être
    perdus = 0
    while t < t1 - 1e-6:
        if arret():
            break
        for _k in range(saut):
            ok, img = cap.read()
            if not ok:
                break
        if not ok:
            break
        t += saut / cad
        g = prep(img)
        px, py = cx + vx, cy + vy
        cw, ch = bw * noyau, bh * noyau
        marge = max(cw, ch) * (0.8 + 0.5 * min(perdus, 6)) + abs(vx) + abs(vy) + 8
        x0, y0 = int(max(0, px - cw / 2 - marge)), int(max(0, py - ch / 2 - marge))
        x1, y1 = int(min(L, px + cw / 2 + marge)), int(min(H, py + ch / 2 + marge))
        zone = g[y0:y1, x0:x1]
        meilleur = None
        for f in (0.95, 1.0, 1.05):
            w, h = int(round(cw * f)), int(round(ch * f))
            if w < 4 or h < 4 or w >= zone.shape[1] or h >= zone.shape[0]:
                continue
            r = cv2.matchTemplate(zone, cv2.resize(modele, (w, h)), cv2.TM_CCOEFF_NORMED)
            _mn, score, _pmn, pmax = cv2.minMaxLoc(r)
            score -= 0.01 * abs(f - 1) / 0.05                   # léger avantage à la même taille
            if meilleur is None or score > meilleur[0]:
                meilleur = (score, x0 + pmax[0] + w / 2, y0 + pmax[1] + h / 2, f)
        if meilleur and meilleur[0] > 0.5:
            score, nx, ny, f = meilleur
            vx, vy = 0.6 * vx + 0.4 * (nx - cx), 0.6 * vy + 0.4 * (ny - cy)
            cx, cy = nx, ny
            bw, bh = min(2 * bw0, max(0.5 * bw0, bw * f)), min(2 * bh0, max(0.5 * bh0, bh * f))
            perdus = 0
            if score > 0.75:
                neuf = cv2.resize(morceau(g, cx, cy, bw * noyau, bh * noyau), (modele.shape[1], modele.shape[0]))
                modele = 0.8 * modele + 0.15 * neuf + 0.05 * origine
        else:
            perdus += 1
            vx, vy = vx * 0.5, vy * 0.5
        points.append((round(t, 3), round(cx / L, 4), round(cy / H, 4), round(bw / L, 4), round(bh / H, 4)))
        if progression:
            progression(min(1.0, (t - t0) / total))
    cap.release()
    return points


def suivre_zone(projet, z, t_depart=None, progression=None, arret=lambda: False):
    """La zone suit ce qu'elle couvre à partir de t_depart (par défaut son début) jusqu'à sa fin ou la fin du plan.
    Avant t_depart, la trajectoire existante est gardée (correction en cours de route)."""
    from . import suivi
    L, H = projet.taille
    t0 = float(z["debut"] if t_depart is None else max(z["debut"], t_depart))
    c, m = _clip_sous(projet, t0 + 0.01)
    if c is None:
        raise ErreurZone(_("Il n'y a pas de plan vidéo sous la zone à cet instant : rien à suivre."))
    v = float(c.get("vitesse", 1.0) or 1.0)
    from .projet import fin_clip
    t1 = min(float(z["fin"]), fin_clip(c))
    s0 = c["src_debut"] + (t0 - c["debut"]) * v
    s1 = c["src_debut"] + (t1 - c["debut"]) * v
    x, y, l, h = rect_a(z, t0)
    boite = vers_source(c, m, L, H, s0, x, y, l, h)
    src = m.get("proxy") or m["chemin"]
    pts = suivi.lisser(suivre_modele(src, s0, s1, boite, progression=progression, arret=arret), 0.2)
    nouv = []
    for p in pts:
        tm = c["debut"] + (p[0] - c["src_debut"]) / v
        ix, iy, il, ih = vers_image(c, m, L, H, p[0], p[1], p[2], p[3], p[4])
        nouv.append((round(tm, 3), round(ix, 4), round(iy, 4), round(il, 4), round(ih, 4)))
    nouv = suivi.alleger(nouv, 1.0 / 15)
    avant = [p for p in (z.get("suivi") or {}).get("positions") or [] if p[0] < t0 - 0.02]
    z["suivi"] = {"media": m["id"], "positions": avant + nouv}
    return z


def figer(z, t):
    """La zone ne suit plus : elle reste à la place qu'elle a à l'instant t."""
    x, y, l, h = rect_a(z, t)
    z.pop("suivi", None)
    z["x"], z["y"], z["l"], z["h"] = round(x, 4), round(y, 4), round(l, 4), round(h, 4)
