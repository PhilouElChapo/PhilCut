"""Prolonger un plan trop court (0.9.24), comme « Generative Extend » de Premiere, mais sur ce poste :
  - « image tenue » : la dernière image (ou la première) reste à l'écran avec un lent zoom, instantané ;
  - « ralenti » : la dernière seconde est ralentie en douceur (images fondues entre elles) jusqu'à la durée voulue ;
  - « IA » : quelques secondes de vidéo inventées à partir de la dernière image par le modèle vidéo local (Wan), qui
    continue la scène.
Le son : l'ambiance de la fin du plan est prolongée (aller-retour, fondu), ou du silence. Le résultat est un nouveau
fichier, posé juste après le plan (ou avant), la suite décalée ; Ctrl+Z l'enlève.
"""
import os
import re
import tempfile

from . import moteur
from .langue import _

METHODES = {"tenue": _("Image tenue, léger zoom (instantané)"), "ralenti": _("Ralenti de la fin, images fondues (quelques secondes)"),
            "ia": _("Prolongé par l'IA sur ce poste (la scène continue ; une à plusieurs minutes)"),
            "cloud": _("Prolongé par l'IA cloud, fidèle (Kling O3 Référence, votre clef fal)")}
MODELE_CLOUD = "kling-o3-ref"


def prix_cloud(duree, params=None):
    from . import generateurs_video as GV
    m = GV.modele(MODELE_CLOUD, params) or {"prix_s": 0.084, "durees": list(range(3, 16))}
    return GV.prix(m, max(3, int(-(-float(duree) // 1))))


_COUPURES_EN = re.compile(r"\s*(?:;|\.\s+|,?\s+(?:and\s+)?then\s+|,?\s+after that,?\s+|,?\s+finally,?\s+)\s*", re.I)
_COUPURES_FR = re.compile(r"\s*(?:;|\.\s+|,?\s+(?:et\s+)?puis\s+|,?\s+ensuite,?\s+|,?\s+enfin,?\s+)\s*", re.I)


def etapes_suite(texte_en, duree_totale, source=""):
    """0.9.76 : une suite décrite d'un coup (« elles descendent l'escalier puis… puis… ») devient des étapes d'une seule action,
    fabriquées à la chaîne, chacune partant de la dernière image de la précédente. Renvoie [(anglais, durée, français)]."""
    morceaux = _fusionner([m.strip(" .,;") for m in _COUPURES_EN.split(texte_en or "") if m and len(m.strip(" .,;")) > 3])
    fr = _fusionner([m.strip(" .,;") for m in _COUPURES_FR.split(source or "") if m and len(m.strip(" .,;")) > 3])
    if not morceaux:
        morceaux = [(texte_en or "").strip() or "The same scene continues naturally"]
    if len(fr) != len(morceaux):
        fr = morceaux
    n = len(morceaux)
    duree_totale = max(3.0 * n, float(duree_totale))
    d = min(15.0, duree_totale / n)
    return [(m, round(d, 1), f) for m, f in zip(morceaux, fr)]


_CAMERA = re.compile(r"(?i)^(?:the\s+)?(?:camera|shot|la\s+cam[ée]ra|le\s+plan|cam[ée]ra)\b")
_LIAISON = re.compile(r"(?i)^(?:then|and then|after that|finally|puis|ensuite|enfin|et puis)\s*,?\s+")


def _fusionner(morceaux):
    """Une indication de caméra (« la caméra recule… ») reste avec l'action qui précède ; les mots de liaison de tête partent."""
    out = []
    for m in morceaux:
        m = _LIAISON.sub("", m).strip()
        if not m:
            continue
        if out and _CAMERA.match(m):
            out[-1] = out[-1] + "; " + m
        else:
            out.append(m[:1].upper() + m[1:])
    return out


def prix_etapes(etapes, params=None):
    return round(sum(prix_cloud(d, params) for _t, d, _f in etapes), 2)


def images_reperes(chemin, debut, fin, dossier, n=3):
    """Quelques images du plan (début, milieu, fin) : le moteur « Référence » s'en sert pour garder les personnes et les
    objets identiques dans la suite."""
    out = []
    for k in range(n):
        t = debut + (fin - debut) * (k / max(1, n - 1)) - (0.05 if k == n - 1 else 0.0)
        f = _image(chemin, max(debut, t), os.path.join(dossier, f"repere{k}.png"))
        if os.path.exists(f):
            out.append(f)
    return out
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
              sortie=None, progression=None, arret=lambda: False, suite="", etapes=None):
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
    if methode == "tenue" or (media.get("genre") == "image" and methode not in ("cloud", "ia")):
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
    elif methode == "cloud":
        # 0.9.72 : la suite démarre sur la dernière image exacte (ou arrive sur la première), les personnes et objets du plan
        # servent de référence : même visage, même tenue, même lieu
        from . import generateurs_video as GV
        av(0.05, _("Envoi des images du plan…"))
        reperes = images_reperes(chemin, float(clip["src_debut"]), float(clip["src_fin"]), d) if media.get("genre") != "image" else [image]
        L0, H0 = taille
        fmt = "9:16" if H0 > L0 else "16:9"
        etapes = etapes or [((suite or "").strip() or "The same scene continues naturally", duree, "")]
        if cote != "fin":
            etapes = etapes[-1:]
        bruts, depart = [], image
        for k, (texte, dk, _fr) in enumerate(etapes):
            texte = texte.rstrip(". ") + (". Exactly the same people, faces, clothes, objects, place, light and camera style as in the "
                                          "reference images. One simple natural action, physically plausible, no text.")
            brut = os.path.join(d, f"cloud{k}.mp4")
            a, b = 0.05 + 0.85 * k / len(etapes), 0.05 + 0.85 * (k + 1) / len(etapes)
            GV.generer(params, MODELE_CLOUD, texte, brut, max(3, int(-(-dk // 1))), fmt,
                       depart if cote == "fin" else None,
                       lambda f, a=a, b=b, k=k: av(a + (b - a) * f, _("L'IA cloud fabrique l'étape {k} sur {n}…", k=k + 1, n=len(etapes))),
                       arret, references=[("the main subject", reperes)], image_fin=image if cote == "debut" else None)
            bruts.append((brut, dk))
            if k < len(etapes) - 1:                         # l'étape suivante part de la dernière image exacte de celle-ci
                depart = os.path.join(d, f"fin{k}.png")
                moteur.lancer(["-y", "-sseof", "-1", "-i", brut, "-update", "1", "-q:v", "2", depart])
        av(0.92, _("Mise au format du film…"))
        listes = []
        for k, (brut, dk) in enumerate(bruts):
            part = os.path.join(d, f"part{k}.mp4")
            deb = 0.0 if cote == "fin" else max(0.0, float((moteur.sonder(brut) or {}).get("duree") or dk) - dk)
            moteur.lancer(["-y", "-ss", f"{deb:.3f}", "-i", brut, "-an", "-vf", f"{cadre},fps={cadence}", "-t", f"{dk:.3f}",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", part])
            listes.append(part)
        liste = os.path.join(d, "liste.txt")
        with open(liste, "w", encoding="utf-8") as f:
            f.write("".join(f"file '{x}'\n" for x in listes))
        total = sum(dk for _b, dk in bruts)
        if total > duree + 0.05:                            # plusieurs étapes : le son suit la durée totale
            wav = _son(chemin, float(clip["src_fin"]) if cote == "fin" else t_ref, total, os.path.join(d, "son_total.wav"), cote, son, a_son)
        moteur.lancer(["-y", "-f", "concat", "-safe", "0", "-i", liste, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                       "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", sortie])
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
