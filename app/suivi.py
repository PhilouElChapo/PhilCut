"""Suivi d'une personne ou d'un objet (cahier des charges, section 14) : un seul moteur, réutilisé partout.

- detecter(image)            : personnes et visages trouvés sur une image (pour proposer qui suivre)
- suivre(...)                : trajectoire d'une boîte de départ dans un média (OpenCV, sur le proxy), avec reprise
                               par détection quand le suivi décroche
- lisser(...)                : trajectoire sans à-coups (cadre qui suit en douceur)
- recadrer(projet, clip, …)  : le plan suit la personne (zoom, passage 9:16 <-> 16:9) ; rendu à l'export par FFmpeg
- accrocher(projet, element) : un texte, un Goodie ou une image suit la personne
- expr(points)               : trajectoire en expression FFmpeg (fonction du temps, morceaux linéaires)

Tout se fait sur ce poste, sans IA payante. Positions normalisées 0..1 (centre x, centre y, largeur, hauteur).
"""
import math

try:
    import cv2
    import numpy as np
except ImportError:          # pragma: no cover
    cv2 = None
    np = None

LISSAGES = {"doux": 1.2, "normal": 0.6, "reactif": 0.25}     # fenêtre de lissage, en secondes


class ErreurSuivi(Exception):
    pass


# ------------------------------------------------------------------ détection
_hog = None
_visages = None


def detecter(img):
    """Boîtes normalisées (x, y, l, h, genre, score) des personnes puis des visages, les plus grandes d'abord."""
    global _hog, _visages
    if cv2 is None:
        return []
    H, L = img.shape[:2]
    echelle = min(1.0, 640.0 / max(L, H))
    petit = cv2.resize(img, (int(L * echelle), int(H * echelle))) if echelle < 1 else img
    out = []
    try:
        if _hog is None:
            _hog = cv2.HOGDescriptor()
            _hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        boites, scores = _hog.detectMultiScale(petit, winStride=(8, 8), padding=(8, 8), scale=1.05)
        for (x, y, w, h), s in zip(boites, list(np.array(scores).ravel()) or [1.0] * len(boites)):
            if float(s) > 0.3:
                out.append((x / echelle / L, y / echelle / H, w / echelle / L, h / echelle / H, "personne", float(s)))
    except Exception:       # noqa: BLE001
        pass
    try:
        import os
        if _visages is None:
            _visages = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
        gris = cv2.cvtColor(petit, cv2.COLOR_BGR2GRAY)
        mini = max(20, int(min(petit.shape[:2]) / 18))
        for (x, y, w, h) in _visages.detectMultiScale(gris, 1.15, 5, minSize=(mini, mini)):
            out.append((x / echelle / L, y / echelle / H, w / echelle / L, h / echelle / H, "visage", 1.0))
    except Exception:       # noqa: BLE001
        pass
    out = _sans_doublons(out)
    out.sort(key=lambda b: (b[4] != "personne", -b[2] * b[3]))
    return out


def _sans_doublons(boites, seuil=0.5):
    garde = []
    for b in sorted(boites, key=lambda b: -b[2] * b[3]):
        if all(_iou(b, g) < seuil or b[4] != g[4] for g in garde):
            garde.append(b)
    return garde


def _iou(a, b):
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    ix = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    iy = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = ix * iy
    return inter / max(1e-9, a[2] * a[3] + b[2] * b[3] - inter)


def image_a(chemin, t, largeur=None):
    """Image (BGR) d'un média à l'instant t (secondes de la source)."""
    if cv2 is None:
        raise ErreurSuivi("OpenCV absent")
    cap = cv2.VideoCapture(chemin)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
    ok, img = cap.read()
    cap.release()
    if not ok:
        raise ErreurSuivi("image illisible")
    if largeur and img.shape[1] > largeur:
        img = cv2.resize(img, (largeur, int(img.shape[0] * largeur / img.shape[1])))
    return img


# ------------------------------------------------------------------ suivi
def _nouveau_traqueur():
    for nom in ("TrackerCSRT_create", "TrackerKCF_create", "TrackerMIL_create"):
        for mod in (cv2, getattr(cv2, "legacy", None)):
            if mod is not None and hasattr(mod, nom):
                return getattr(mod, nom)()
    raise ErreurSuivi("aucun traqueur OpenCV disponible")


def suivre(chemin, t0, t1, boite, pas=0.1, progression=None, arret=lambda: False, largeur_max=640):
    """Suit `boite` (x, y, l, h normalisés, à l'instant t0 de la source) jusqu'à t1.
    Renvoie [(t_source, cx, cy, l, h)]. Si le suivi décroche, on cherche la personne par détection près de la dernière
    position ; à défaut, la dernière position est gardée (le cadre ne saute pas)."""
    if cv2 is None:
        raise ErreurSuivi("OpenCV absent")
    cap = cv2.VideoCapture(chemin)
    if not cap.isOpened():
        raise ErreurSuivi("vidéo illisible")
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t0) * 1000)
    ok, img = cap.read()
    if not ok:
        cap.release()
        raise ErreurSuivi("image de départ illisible")
    H0, L0 = img.shape[:2]
    ech = min(1.0, largeur_max / float(L0))
    if ech < 1:
        img = cv2.resize(img, (int(L0 * ech), int(H0 * ech)))
    H, L = img.shape[:2]
    bx, by, bw, bh = (float(v) for v in boite[:4])

    def pixels(b):
        return (int(b[0] * L), int(b[1] * H), max(8, int(b[2] * L)), max(8, int(b[3] * H)))
    traqueur = _nouveau_traqueur()
    traqueur.init(img, pixels((bx, by, bw, bh)))
    cad = cap.get(cv2.CAP_PROP_FPS) or 30
    saut = max(1, int(round(pas * cad)))
    t = float(t0)
    derniere = (bx + bw / 2, by + bh / 2, bw, bh)
    points = [(round(t, 3),) + tuple(round(v, 4) for v in derniere)]
    perdus = 0
    total = max(1e-6, t1 - t0)
    while t < t1:
        if arret():
            break
        for _k in range(saut):
            ok, img = cap.read()
            if not ok:
                break
        if not ok:
            break
        if ech < 1:
            img = cv2.resize(img, (L, H))
        t += saut / cad
        ok2, b = traqueur.update(img)
        if ok2 and b[2] > 2 and b[3] > 2:
            x, y, w, h = b
            derniere = ((x + w / 2) / L, (y + h / 2) / H, w / L, h / H)
            perdus = 0
        else:
            perdus += 1
            if perdus % 5 == 1:          # reprise : la personne la plus proche de la dernière position
                cand = [c for c in detecter(img) if c[4] == ("personne" if boite[2] * boite[3] > 0.02 else "visage")] or detecter(img)
                if cand:
                    cx, cy = derniere[0], derniere[1]
                    c = min(cand, key=lambda c: math.hypot(c[0] + c[2] / 2 - cx, c[1] + c[3] / 2 - cy))
                    if math.hypot(c[0] + c[2] / 2 - cx, c[1] + c[3] / 2 - cy) < 0.35:
                        traqueur = _nouveau_traqueur()
                        traqueur.init(img, pixels(c))
                        derniere = (c[0] + c[2] / 2, c[1] + c[3] / 2, c[2], c[3])
                        perdus = 0
        points.append((round(t, 3),) + tuple(round(v, 4) for v in derniere))
        if progression:
            progression(min(1.0, (t - t0) / total))
    cap.release()
    return points


def lisser(points, fenetre_s=0.6):
    """Moyenne glissante centrée (sur le temps) : le cadre suit sans trembler. Garde le format des points."""
    if len(points) < 3 or fenetre_s <= 0:
        return list(points)
    out = []
    n = len(points[0])
    j0 = 0
    for i, p in enumerate(points):
        while points[j0][0] < p[0] - fenetre_s / 2:
            j0 += 1
        voisins = []
        j = j0
        while j < len(points) and points[j][0] <= p[0] + fenetre_s / 2:
            voisins.append(points[j])
            j += 1
        poids = [1.0 - abs(v[0] - p[0]) / (fenetre_s / 2 + 1e-9) * 0.5 for v in voisins]
        tot = sum(poids)
        out.append((p[0],) + tuple(round(sum(w * v[k] for w, v in zip(poids, voisins)) / tot, 4) for k in range(1, n)))
    return out


def alleger(points, pas=0.2):
    """Garde un point tous les `pas` secondes (et le dernier) : expressions FFmpeg courtes."""
    if not points:
        return []
    out = [points[0]]
    for p in points[1:-1]:
        if p[0] - out[-1][0] >= pas - 1e-6:
            out.append(p)
    if len(points) > 1:
        out.append(points[-1])
    return out


# ------------------------------------------------------------------ expressions FFmpeg
def expr(points, var="t"):
    """Valeur linéaire par morceaux de `var` : points [(t, v)], constante avant le premier et après le dernier.
    Somme de termes gte()*lt() (pas d'imbrication : FFmpeg l'évalue vite, même avec des centaines de points)."""
    if not points:
        return "0"
    if len(points) == 1:
        return f"{points[0][1]:.4f}"
    termes = [f"lt({var},{points[0][0]:.3f})*{points[0][1]:.4f}"]
    for (ta, va), (tb, vb) in zip(points, points[1:]):
        if tb - ta < 1e-4:
            continue
        pente = (vb - va) / (tb - ta)
        termes.append(f"gte({var},{ta:.3f})*lt({var},{tb:.3f})*({va:.4f}+{pente:.5f}*({var}-{ta:.3f}))")
    termes.append(f"gte({var},{points[-1][0]:.3f})*{points[-1][1]:.4f}")
    return "+".join(termes)


def valeur(points, t, k=1):
    """Valeur interpolée (colonne k) d'une trajectoire [(t, ...)] à l'instant t (même règle que expr())."""
    if not points:
        return None
    if t <= points[0][0]:
        return points[0][k]
    for a, b in zip(points, points[1:]):
        if a[0] <= t < b[0]:
            return a[k] + (b[k] - a[k]) * (t - a[0]) / max(1e-9, b[0] - a[0])
    return points[-1][k]


def fenetre_source(cadre, t_source, lw, lh, L, H):
    """Fenêtre (x, y, largeur, hauteur) en pixels de la source montrée à t_source : la même que filtre_recadrage()."""
    pts = cadre.get("positions") or []
    zoom = max(1.0, float(cadre.get("zoom", 1.0)))
    cw = min(lw, lh * L / H) / zoom
    ch = cw * H / L
    cx, cy = valeur(pts, t_source, 1), valeur(pts, t_source, 2)
    if cx is None:
        cx, cy = 0.5, 0.5
    x = min(max(cx * lw - cw / 2, 0), lw - cw)
    y = min(max(cy * lh - ch / 2, 0), lh - ch)
    return x, y, cw, ch


def filtre_recadrage(cadre, clip, L, H):
    """crop+scale FFmpeg qui suit la trajectoire `cadre` (positions en temps source) sur un plan du montage.
    Le temps du filtre est celui du plan (0 au début du plan, vitesse appliquée)."""
    v = float(clip.get("vitesse", 1.0) or 1.0)
    d0 = float(clip.get("src_debut", 0.0))
    pts = [((p[0] - d0) / v, p[1], p[2]) for p in cadre.get("positions") or []]
    zoom = max(1.0, float(cadre.get("zoom", 1.0)))
    ex = expr([(t, x) for t, x, _y in pts])
    ey = expr([(t, y) for t, _x, y in pts])
    largeur = f"2*trunc(min(iw\\,ih*{L}/{H})/{zoom:.3f}/2)"
    hauteur = f"2*trunc(ow*{H}/{L}/2)"
    return (f"crop=w='{largeur}':h='{hauteur}':x='clip(({ex})*iw-ow/2\\,0\\,iw-ow)':y='clip(({ey})*ih-oh/2\\,0\\,ih-oh)',"
            f"scale={L}:{H}")


# ------------------------------------------------------------------ usages dans le projet
def _source(projet, media):
    return media.get("proxy") or media["chemin"]


def recadrer(projet, clip, boite, zoom=1.0, lissage="normal", progression=None, arret=lambda: False):
    """Le plan suit la personne : clip["ajustement"] = "suivi", trajectoire gardée dans clip["suivi_cadre"]."""
    m = projet.media(clip["media"])
    if not m or m.get("genre") != "video":
        raise ErreurSuivi("le recadrage par suivi demande une vidéo")
    pts = suivre(_source(projet, m), clip["src_debut"], clip["src_fin"], boite, progression=progression, arret=arret)
    pts = alleger(lisser(pts, LISSAGES.get(lissage, 0.6)), 0.2)
    clip["suivi_cadre"] = {"boite": list(boite[:4]), "zoom": float(zoom), "lissage": lissage,
                           "positions": [(p[0], p[1], p[2]) for p in pts]}
    clip["ajustement"] = "suivi"
    return clip


def accrocher(projet, element, media, boite, decalage=(0.0, -0.6), lissage="normal", progression=None, arret=lambda: False):
    """Texte, Goodie ou image qui suit la personne. element["suivi"]["positions"] = [(t_montage, x, y)] où (x, y) est le
    point d'accroche : centre de la boîte décalé de `decalage` (en hauteurs de boîte ; -0.6 = au-dessus de la tête)."""
    clip = next((c for c in projet.clips_piste("video") if c["media"] == media["id"]
                 and c["debut"] - 0.05 <= element["debut"] < c["debut"] + (c["src_fin"] - c["src_debut"]) / c.get("vitesse", 1.0)), None)
    if clip is None:
        clip = next((c for c in projet.clips_piste("video") if c["media"] == media["id"]), None)
    if clip is None:
        raise ErreurSuivi("le média suivi n'est pas sur la timeline")
    v = float(clip.get("vitesse", 1.0) or 1.0)
    t0 = clip["src_debut"] + max(0.0, element["debut"] - clip["debut"]) * v
    t1 = min(clip["src_fin"], clip["src_debut"] + (element["fin"] - clip["debut"]) * v)
    pts = lisser(suivre(_source(projet, media), t0, t1, boite, progression=progression, arret=arret), LISSAGES.get(lissage, 0.6))
    dx, dy = decalage
    pos = [(round(clip["debut"] + (p[0] - clip["src_debut"]) / v, 3), round(p[1] + dx * p[3], 4), round(p[2] + dy * p[4], 4)) for p in pts]
    element["suivi"] = {"media": media["id"], "boite": list(boite[:4]), "decalage": list(decalage), "lissage": lissage,
                        "positions": alleger(pos, 0.1)}
    return element


def position_pixels(element, L, H, largeur_px, hauteur_px):
    """Expressions overlay x, y (en pixels, coin haut-gauche) d'un élément accroché : centré horizontalement sur le
    point d'accroche, posé au-dessus. Temps = temps du montage."""
    pts = (element.get("suivi") or {}).get("positions") or []
    ex = expr([(t, x) for t, x, _y in pts])
    ey = expr([(t, y) for t, _x, y in pts])
    return (f"'clip(({ex})*{L}-{largeur_px}/2\\,0\\,{L}-{largeur_px})'",
            f"'clip(({ey})*{H}-{hauteur_px}\\,0\\,{H}-{hauteur_px})'")
