"""Prolonger un plan trop court (0.9.24), comme « Generative Extend » de Premiere, mais sur ce poste :
  - « image tenue » : la dernière image (ou la première) reste à l'écran avec un lent zoom, instantané ;
  - « ralenti » : la dernière seconde est ralentie en douceur (images fondues entre elles) jusqu'à la durée voulue ;
  - « IA » : quelques secondes de vidéo inventées à partir de la dernière image par le modèle vidéo local (Wan), qui
    continue la scène.
Le son : l'ambiance de la fin du plan est prolongée (aller-retour, fondu), ou du silence. Le résultat est un nouveau
fichier, posé juste après le plan (ou avant), la suite décalée ; Ctrl+Z l'enlève.
"""
import os
import tempfile

from . import moteur
from .langue import _

METHODES = {"tenue": _("Image tenue, léger zoom (instantané)"), "ralenti": _("Ralenti de la fin, images fondues (quelques secondes)"),
            "ia": _("Prolongé par l'IA sur ce poste (la scène continue ; une à plusieurs minutes)")}
SONS = {"ambiance": _("Ambiance du plan prolongée (fondu)"), "silence": _("Silence")}


def _image(chemin, t, sortie):
    moteur.lancer(["-y", "-ss", f"{max(0.0, t):.3f}", "-i", chemin, "-frames:v", "1", "-q:v", "2", sortie])
    if not os.path.exists(sortie):                       # tout au bout du fichier : une image un peu avant
        moteur.lancer(["-y", "-sseof", "-0.2", "-i", chemin, "-frames:v", "1", "-q:v", "2", sortie])
    return sortie


def _son(chemin, t_ref, duree, sortie, cote="fin", genre="ambiance", a_son=True):
    """Son du morceau ajouté : la dernière (ou première) seconde jouée en aller-retour, puis fondu ; ou du silence."""
    if genre == "silence" or not a_son:
        moteur.lancer(["-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={duree:.3f}", sortie])
        return sortie
    deb = max(0.0, t_ref - 1.0) if cote == "fin" else t_ref
    morceau = os.path.join(os.path.dirname(sortie), "_morceau.wav")
    moteur.lancer(["-y", "-ss", f"{deb:.3f}", "-t", "1.0", "-i", chemin, "-vn", "-ac", "2", "-ar", "48000", morceau])
    filtre = (f"[0:a]asplit=2[a][b];[b]areverse[r];[a][r]concat=n=2:v=0:a=1,aloop=loop=-1:size=96000,atrim=0:{duree:.3f},"
              f"afade=t={'out' if cote == 'fin' else 'in'}:st={0 if cote == 'debut' else max(0.0, duree - min(duree, 1.5)):.3f}:d={min(duree, 1.5):.3f},"
              f"volume=0.8")
    moteur.lancer(["-y", "-i", morceau, "-filter_complex", filtre, "-ac", "2", "-ar", "48000", sortie])
    try:
        os.remove(morceau)
    except OSError:
        pass
    return sortie


def fabriquer(media, clip, duree, methode="tenue", cote="fin", son="ambiance", taille=(1920, 1080), cadence=30, params=None,
              sortie=None, progression=None, arret=lambda: False):
    """Fabrique le morceau ajouté (MP4 avec son) ; renvoie son chemin."""
    chemin = media["chemin"]
    fiche = media.get("fiche") or moteur.sonder(chemin)
    a_son = bool(fiche.get("audio"))
    L, H = (int(taille[0]) // 2 * 2, int(taille[1]) // 2 * 2)
    duree = max(0.3, float(duree))
    t_ref = float(clip["src_fin"]) - 0.05 if cote == "fin" else float(clip["src_debut"])
    d = tempfile.mkdtemp(prefix="philcut-prolonger-")
    if not sortie:
        import time
        from .creations import dossier
        sortie = os.path.join(dossier(), f"prolonge_{clip['id']}_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
    av = progression or (lambda f, t="": None)
    av(0.05, _("Son prolongé…"))
    wav = _son(chemin, float(clip["src_fin"]) if cote == "fin" else t_ref, duree, os.path.join(d, "son.wav"), cote, son, a_son)
    image = os.path.join(d, "image.png")
    if media.get("genre") == "image":
        image = chemin
    else:
        _image(chemin, t_ref, image)
    cadre = f"scale={L}:{H}:force_original_aspect_ratio=increase,crop={L}:{H},setsar=1"
    n = max(2, int(round(duree * cadence)))
    if methode == "tenue" or media.get("genre") == "image":
        av(0.3, _("Image tenue…"))
        z = "1+0.04*on/{n}".format(n=n) if cote == "fin" else "1.04-0.04*on/{n}".format(n=n)
        vf = (f"scale={L * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={L * 2}:{H * 2},"
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={L}x{H}:fps={cadence},setsar=1")
        moteur.lancer(["-y", "-loop", "1", "-i", image, "-i", wav, "-vf", vf, "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast",
                       "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", sortie])
    elif methode == "ralenti":
        av(0.3, _("Ralenti de la fin…"))
        base = 1.0 if cote == "fin" else 1.0
        deb = max(float(clip["src_debut"]), float(clip["src_fin"]) - base) if cote == "fin" else float(clip["src_debut"])
        facteur = duree / base
        vf = f"{cadre},setpts={facteur:.4f}*PTS,framerate=fps={cadence}:interp_start=0:interp_end=255:scene=100"
        moteur.lancer(["-y", "-ss", f"{deb:.3f}", "-t", f"{base:.3f}", "-i", chemin, "-i", wav, "-map", "0:v", "-map", "1:a", "-vf", vf,
                       "-t", f"{duree:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", sortie], arret=arret)
    else:
        from . import creatif as C
        av(0.1, _("L'IA invente la suite de la scène…"))
        brut = os.path.join(d, "ia.mp4")
        C.video("the same scene continues naturally, same camera movement, same lighting, realistic, smooth motion", brut, params,
                init=image, secondes=duree, progression=lambda f, t="": av(0.1 + 0.8 * f, t or _("L'IA invente la suite de la scène…")),
                arret=arret)
        if cote == "debut":                               # pour le début, on passe la vidéo inventée à l'envers : elle arrive sur la première image
            inv = os.path.join(d, "ia_inv.mp4")
            moteur.lancer(["-y", "-i", brut, "-vf", "reverse", "-an", inv])
            brut = inv
        av(0.92, _("Mise au format du film…"))
        moteur.lancer(["-y", "-i", brut, "-i", wav, "-map", "0:v", "-map", "1:a", "-vf", f"{cadre},fps={cadence}", "-t", f"{duree:.3f}",
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                       "-movflags", "+faststart", sortie])
    if not os.path.exists(sortie):
        raise RuntimeError(_("Le plan n'a pas pu être prolongé."))
    av(1.0, _("Plan prolongé."))
    return sortie


def poser(projet, clip, chemin, cote="fin", nom=""):
    """Pose le morceau juste après le plan (ou juste avant) sur la même piste ; tout ce qui suit est décalé d'autant."""
    from .projet import fin_clip
    duree = float((moteur.sonder(chemin) or {}).get("duree") or 0)
    if duree <= 0.05:
        return None
    t = fin_clip(clip) if cote == "fin" else clip["debut"]
    for x in projet.clips:
        if x["debut"] >= t - 1e-3:
            x["debut"] += duree
    for x in projet.titres + projet.goodies:
        if x["debut"] >= t - 1e-3:
            x["debut"] += duree
            x["fin"] += duree
    st = []
    for e in projet.d.get("sous_titres") or []:
        st.append([e[0] + duree, e[1] + duree] + list(e[2:]) if e[0] >= t - 1e-3 else e)
    projet.d["sous_titres"] = st
    mi = projet.ajouter_media(chemin, moteur.sonder(chemin))
    mi["nom"] = nom or _("Prolongement")
    ci = projet.ajouter_clip(mi["id"], clip["piste"], t, 0.0, duree)
    ci["nom"] = mi["nom"]
    for k in ("ajustement", "incrust"):
        if clip.get(k) is not None:
            ci[k] = copy_(clip[k])
    projet.modifie = True
    return ci


def copy_(v):
    import copy
    return copy.deepcopy(v)


def inserer(projet, chemin, t, piste="video", nom=""):
    """Insère un fichier dans la piste à l'instant t (après le plan qui s'y trouve) ; la suite est décalée."""
    from .projet import fin_clip
    sous = next((c for c in projet.clips_piste(piste) if c["debut"] - 1e-3 <= t < fin_clip(c) - 1e-3), None)
    if sous:
        t = fin_clip(sous)
    repere = {"debut": t, "piste": piste}                  # poser() avant ce repère = insérer à t
    return poser(projet, repere, chemin, "debut", nom)
