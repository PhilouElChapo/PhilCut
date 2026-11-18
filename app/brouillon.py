"""0.9.91 : brouillon de toute une séquence, pour la voir en entier avant de payer la vraie qualité.

Trois façons :
- « animatique » : gratuit et immédiat ; chaque plan montre ce qu'on sait déjà de lui (image de départ connue, image clef
  d'arrivée en fondu, sinon la fiche du lieu ou d'une personne), avec son numéro, son action et sa durée exacte ;
- « locale » : l'IA vidéo de ce poste (gratuite, quelques minutes par plan, 5 s au plus, 480p) ;
- un modèle cloud bon marché (Gemini Omni 360p) : prix demandé avant.
Rien n'est posé dans le film : le brouillon se regarde, puis on corrige les plans ou on lance la vraie fabrication."""
import copy, os, shutil, tempfile, time

from .langue import _
from . import moteur, sequence_ia as Q

MODES = ("animatique", "locale", "omni-360p")
FPS = 25


def taille(seq):
    return (720, 1280) if seq.get("format") == "9:16" else (1280, 720)


def image_du_plan(seq, i):
    """La meilleure image connue pour le début du plan i (sans rien calculer), sinon ""."""
    d = Q.depart_prevu(seq, i)
    if d:
        return d
    pl = seq["plans"][i]
    for k in range(i - 1, -1, -1):                       # la dernière image clef avant lui
        av = seq["plans"][k]
        if av.get("image_fin") and os.path.exists(av["image_fin"]) and not av.get("sans_fin"):
            return av["image_fin"]
        if av.get("image") and os.path.exists(av["image"]):
            return av["image"]
    for li in seq.get("lieux") or []:
        if li.get("nom") == pl.get("lieu") or not pl.get("lieu"):
            for im in [li.get("planche")] + list(li.get("images") or []):
                if im and os.path.exists(im):
                    return im
    for p in seq.get("personnages") or []:
        if p.get("nom") in (pl.get("personnages") or []):
            for im in [p.get("planche")] + list(p.get("images") or []):
                if im and os.path.exists(im):
                    return im
    return ""


def image_fin_du_plan(seq, i):
    pl = seq["plans"][i]
    if pl.get("image_fin") and os.path.exists(pl["image_fin"]) and not pl.get("sans_fin"):
        return pl["image_fin"]
    return ""


def prix(seq, mode, params):
    """Prix estimé du brouillon en $ (0 pour l'animatique et l'IA de ce poste)."""
    if mode in ("animatique", "locale"):
        return 0.0
    from . import generateurs_video as GV
    m = GV.modele(mode, params) or {}
    return round(sum(GV.prix(m, int(p.get("duree") or Q.DUREE_PLAN)) for p in seq["plans"]), 2)


def _carte(seq, i, image, chemin):
    """Image du plan au format de la séquence, avec un bandeau : numéro, action, durée."""
    from PySide6.QtGui import QImage, QPainter, QColor, QFont
    from PySide6.QtCore import Qt, QRectF
    W, H = taille(seq)
    out = QImage(W, H, QImage.Format_RGB32)
    out.fill(QColor("#202428"))
    p = QPainter(out)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    src = QImage(image) if image else QImage()
    if not src.isNull():
        s = src.scaled(W, H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p.drawImage((W - s.width()) // 2, (H - s.height()) // 2, s)
    pl = seq["plans"][i]
    texte = _("Plan {i} · {d} s — {a}", i=i + 1, d=int(pl.get("duree") or Q.DUREE_PLAN), a=pl.get("action", ""))
    f = QFont()
    f.setPixelSize(max(18, H // 26))
    f.setBold(True)
    p.setFont(f)
    marge = H // 30
    zone = QRectF(marge, 0, W - 2 * marge, H)
    r = p.boundingRect(zone, Qt.TextWordWrap | Qt.AlignLeft, texte)
    bande = QRectF(0, H - r.height() - 2 * marge, W, r.height() + 2 * marge)
    p.fillRect(bande, QColor(0, 0, 0, 170))
    p.setPen(QColor("white"))
    p.drawText(QRectF(marge, bande.top() + marge, W - 2 * marge, r.height()), Qt.TextWordWrap | Qt.AlignLeft, texte)
    if not image:
        p.setPen(QColor("#9aa0a6"))
        f.setPixelSize(max(16, H // 30))
        f.setBold(False)
        p.setFont(f)
        p.drawText(QRectF(0, 0, W, H * 0.7), Qt.AlignCenter, _("(pas encore d'image pour ce plan)"))
    p.end()
    out.save(chemin)
    return chemin


def _encoder(args, sortie):
    moteur.lancer(["-y"] + args + ["-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-an", sortie])
    return sortie


def animatique(seq, sortie, progression=None, arret=lambda: False):
    """Le brouillon gratuit : une carte par plan, en fondu vers son image clef s'il en a une."""
    tmp = tempfile.mkdtemp(prefix="philcut-brouillon-")
    W, H = taille(seq)
    morceaux = []
    n = len(seq["plans"])
    for i, pl in enumerate(seq["plans"]):
        if arret():
            raise InterruptedError
        progression and progression(i / max(1, n))
        d = float(pl.get("duree") or Q.DUREE_PLAN)
        a = _carte(seq, i, image_du_plan(seq, i), os.path.join(tmp, f"a{i}.png"))
        fin = image_fin_du_plan(seq, i)
        f = os.path.join(tmp, f"p{i:02d}.mp4")
        zoom = f"scale={W * 2}:{H * 2},zoompan=z='min(zoom+0.0004,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(d * FPS)}:s={W}x{H}:fps={FPS}"
        if fin:
            b = _carte(seq, i, fin, os.path.join(tmp, f"b{i}.png"))
            fondu = max(0.6, d * 0.4)
            _encoder(["-loop", "1", "-t", f"{d:.2f}", "-i", a, "-loop", "1", "-t", f"{d:.2f}", "-i", b, "-filter_complex",
                      f"[0]scale={W}:{H},fps={FPS}[x];[1]scale={W}:{H},fps={FPS}[y];"
                      f"[x][y]xfade=transition=fade:duration={fondu:.2f}:offset={d - fondu:.2f}", "-t", f"{d:.2f}"], f)
        else:
            _encoder(["-loop", "1", "-i", a, "-vf", zoom, "-t", f"{d:.2f}"], f)
        morceaux.append(f)
    return assembler(morceaux, sortie, seq)


def assembler(morceaux, sortie, seq, durees=None):
    """Met bout à bout des vidéos de tailles et cadences différentes (même taille, 25 i/s, sans son) ; durees : chaque
    morceau coupé à la durée de son plan (un moteur qui choisit lui-même sa durée)."""
    W, H = taille(seq)
    args = []
    for f in morceaux:
        args += ["-i", f]
    chaines = "".join(f"[{k}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,"
                      f"setsar=1,fps={FPS}" + (f",trim=duration={float(durees[k]):.2f},setpts=PTS-STARTPTS" if durees else "") +
                      f"[v{k}];" for k in range(len(morceaux)))
    chaines += "".join(f"[v{k}]" for k in range(len(morceaux))) + f"concat=n={len(morceaux)}:v=1:a=0[out]"
    return _encoder(args + ["-filter_complex", chaines, "-map", "[out]"], sortie)


def fabriquer(seq, mode, params, progression=None, arret=lambda: False):
    """Le brouillon de toute la séquence dans le dossier de la séquence ; seq["brouillon"] le retient. Renvoie le chemin."""
    if mode not in MODES and not mode.startswith("omni"):
        raise ValueError(mode)
    dossier = os.path.join(Q.dossier(seq), "brouillon")
    os.makedirs(dossier, exist_ok=True)
    sortie = os.path.join(dossier, f"brouillon_{mode}_{int(time.time())}.mp4")
    if mode == "animatique":
        animatique(seq, sortie, progression, arret)
    else:
        # chaque plan avec le moteur bon marché, à partir de ce qu'on sait déjà (images connues), sans rien payer d'autre
        copie = copy.deepcopy(seq)
        copie["image_auto"] = False
        copie["image_fin_auto"] = False
        copie["voix"] = "aucune"
        morceaux, n = [], len(copie["plans"])
        for i, pl in enumerate(copie["plans"]):
            if arret():
                raise InterruptedError
            pl["image"] = image_du_plan(seq, i) or ""
            f = Q.fabriquer_plan(copie, i, params, mode, lambda x, i=i: progression and progression((i + x) / n), arret)
            dest = os.path.join(dossier, f"plan{i + 1:02d}_{mode}.mp4")
            shutil.move(f, dest)
            morceaux.append(dest)
        assembler(morceaux, sortie, seq, [float(p.get("duree") or Q.DUREE_PLAN) for p in seq["plans"]])
    seq["brouillon"] = {"mode": mode, "fichier": sortie, "quand": time.strftime("%Y-%m-%d %H:%M")}
    progression and progression(1.0)
    return sortie
