"""Suivi précis par le cloud (0.9.85) : SAM 3 (Meta, sur fal.ai) suit EXACTEMENT ce qu'on a désigné, même s'il se tourne,
se cache un instant ou change de taille. Annoncé le 15/11 (« suivi précis / recadrage, flèche qui suit une personne »).

Même entrée et même sortie que les suivis de ce poste (zones.suivre_modele, suivi.suivre) : une boîte de départ (le cadre
tracé, ou le centre du clic), et [(t_source, centre x, centre y, largeur, hauteur)] normalisés. On peut donc l'utiliser pour
une zone (flou, cache), un Goodie ou un texte accroché, le recadrage qui suit.

Méthode : le passage est envoyé réduit (640 px, 15 images/s) avec un point posé sur le sujet ; SAM 3 rend la vidéo masquée.
Sur ce poste, on compare chaque image rendue à l'image d'origine : le sujet est la région qui contient le point désigné
(rendue différente si SAM la colore, identique si SAM efface le reste) ; sa boîte englobante donne la trajectoire. Vers
l'arrière (zone tracée au milieu), le passage est envoyé à l'envers. Prix : environ 0,005 $ pour 16 images (montré avant)."""
import os
import tempfile

from .langue import _

POINT = "fal-ai/sam-3/video"
PRIX_16 = 0.005
IPS = 15
LARGEUR = 640


def prix(duree):
    return round(max(1, int(duree * IPS / 16) + 1) * PRIX_16, 3)


class ErreurSuiviCloud(Exception):
    pass


def _extraire(chemin, a, b, sortie, envers=False):
    """Passage [a, b] de la source, 640 px, 15 i/s, sans son (à l'envers pour remonter le temps)."""
    from . import moteur
    vf = f"fps={IPS},scale={LARGEUR}:-2" + (",reverse" if envers else "")
    moteur.lancer(["-y", "-ss", f"{min(a, b):.3f}", "-t", f"{abs(b - a):.3f}", "-i", chemin, "-an", "-vf", vf,
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", sortie])
    if not os.path.exists(sortie):
        raise ErreurSuiviCloud(_("Le passage n'a pas pu être extrait."))
    return sortie


def _images(chemin, largeur=160):
    """Toutes les images d'une vidéo, en petit (gris), pour comparer l'origine et le rendu de SAM."""
    import subprocess
    import numpy as np
    from . import moteur
    v = (moteur.sonder(chemin) or {}).get("video") or {}
    w, h = int(v.get("largeur") or 0), int(v.get("hauteur") or 0)
    if not (w and h):
        raise ErreurSuiviCloud(_("Vidéo illisible pour le suivi."))
    hh = max(2, int(round(largeur * h / w / 2)) * 2)
    p = subprocess.run([moteur.ffmpeg(), "-v", "error", "-i", chemin, "-vf", f"scale={largeur}:{hh}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=False, **moteur._sans_console())
    a = np.frombuffer(p.stdout, dtype=np.uint8)
    n = a.size // (largeur * hh * 3)
    return a[: n * largeur * hh * 3].reshape(n, hh, largeur, 3).astype(np.int16)


def boites(origine, rendu, point):
    """Boîte du sujet image par image : (cx, cy, l, h) normalisés, ou None si l'image ne montre rien. `point` = (x, y) normalisés
    du sujet sur la première image."""
    import numpy as np
    n = min(len(origine), len(rendu))
    if n == 0:
        return []
    H, L = origine.shape[1:3]
    px, py = min(L - 1, max(0, int(point[0] * L))), min(H - 1, max(0, int(point[1] * H)))
    diff = [np.abs(origine[i] - rendu[i]).sum(axis=2) > 60 for i in range(n)]
    autour = diff[0][max(0, py - 2):py + 3, max(0, px - 2):px + 3]
    sujet_change = autour.mean() >= 0.5            # SAM colore le sujet ; sinon il a effacé le reste
    out = []
    for i in range(n):
        m = diff[i] if sujet_change else ~diff[i]
        ys, xs = np.nonzero(m)
        if len(xs) < max(6, L * H // 2000):
            out.append(None)
            continue
        x0, x1 = np.percentile(xs, (2, 98))
        y0, y1 = np.percentile(ys, (2, 98))
        out.append(((x0 + x1) / 2 / L, (y0 + y1) / 2 / H, max(1, x1 - x0) / L, max(1, y1 - y0) / H))
    return out


def _sam(params, video, point, progression=None, arret=lambda: False):
    from . import generateurs_video as GV
    k = GV.clef(params, "fal")
    if not k:
        raise ErreurSuiviCloud(_("Il faut une clef fal.ai (Préférences › Assistant et IA) pour le suivi précis par le cloud."))
    from . import moteur
    v = (moteur.sonder(video) or {}).get("video") or {}
    w, h = int(v.get("largeur") or LARGEUR), int(v.get("hauteur") or 360)
    url = GV.televerser(k, video)
    corps = {"video_url": url, "point_prompts": [{"x": int(point[0] * w), "y": int(point[1] * h), "label": 1, "object_id": 1}],
             "apply_mask": True, "video_output_type": "X264 (.mp4)"}
    res = GV.demande_fal(k, POINT, corps, progression, arret, attente=900.0)
    url_rendu = ((res or {}).get("video") or {}).get("url")
    if not url_rendu:
        raise ErreurSuiviCloud(_("fal.ai n'a renvoyé aucune vidéo : {r}", r=str(res)[:200]))
    sortie = video[:-4] + "_sam.mp4"
    GV.telecharger(url_rendu, sortie)
    return sortie


def suivre(params, chemin, t0, t1, boite, progression=None, arret=lambda: False):
    """Comme zones.suivre_modele : `boite` = (coin x, coin y, largeur, hauteur) normalisés de la source à t0 ; t1 < t0 = vers
    l'arrière. Renvoie [(t_source, cx, cy, l, h)] dans l'ordre du temps ; une image où le sujet est caché garde la boîte
    précédente."""
    envers = t1 < t0
    d = tempfile.mkdtemp(prefix="philcut-sam-")
    video = _extraire(chemin, t0, t1, os.path.join(d, "passage.mp4"), envers)
    centre = (boite[0] + boite[2] / 2, boite[1] + boite[3] / 2)
    rendu = _sam(params, video, centre, (lambda f, t="": progression(0.1 + 0.8 * f)) if progression else None, arret)
    progression and progression(0.92)
    bx = boites(_images(video), _images(rendu), centre)
    pts, dernier = [], (centre[0], centre[1], boite[2], boite[3])
    for i, b in enumerate(bx):
        dernier = b or dernier
        t = t0 - i / IPS if envers else t0 + i / IPS
        pts.append((round(t, 3),) + tuple(round(v, 4) for v in dernier))
    progression and progression(1.0)
    return list(reversed(pts)) if envers else pts
