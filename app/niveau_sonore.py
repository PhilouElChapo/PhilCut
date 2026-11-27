"""Volume sonore du film (1.4.1, choix de Philippe le 27/11 après la comparaison avec FilmCraft).

Mesure à la norme EBU R128 / ITU BS.1770 par le filtre ebur128 de FFmpeg : volume intégré (LUFS, sur tout le film),
court terme (3 s, suivi pendant la lecture), plage de volume (LRA) et crête vraie (dBTP). Le son du film est d'abord
mélangé comme à l'export, mais sans être ramené à la cible : on voit le volume tel qu'il est. Des cibles toutes
prêtes (YouTube, Instagram, écran LED, télévision, podcast) ; l'export ramène le film à la cible, sauf si l'on choisit
de le laisser tel quel, et l'on est alors prévenu s'il en est loin, avec « Corriger ».
"""
import hashlib, json, os, re, tempfile

from .langue import _

# cible : (libellé, LUFS intégré, crête vraie maximale)
CIBLES = {
    "ecran_led": (_("Ecran LED (-14 LUFS)"), -14.0, -1.0),
    "instagram": (_("Instagram, TikTok (-14 LUFS)"), -14.0, -1.0),
    "podcast": (_("Podcast, voix (-16 LUFS)"), -16.0, -1.0),
    "television": (_("Télévision EBU R128 (-23 LUFS)"), -23.0, -1.0),
    "youtube": (_("YouTube (-14 LUFS)"), -14.0, -1.0),
}
ECART_TOLERE = 1.5          # LU : au-delà, le film est « hors cible »


def libelle_auto():
    return _("Selon la destination de l'export")


def choix_cibles():
    """[(clef, libellé)] : « selon la destination » d'abord, puis les cibles par ordre alphabétique du libellé traduit."""
    return [("auto", libelle_auto())] + sorted(((k, v[0]) for k, v in CIBLES.items()), key=lambda x: str(x[1]).lower())


def cible(projet, params=None, destination=None):
    """(clef, LUFS, crête) visés pour ce film : le choix du projet, sinon celui des Préférences, sinon la destination."""
    from .export import LUFS
    k = (projet.d.get("son_cible") if projet is not None else None) or (params or {}).get("son_cible") or "auto"
    if k in CIBLES:
        return k, CIBLES[k][1], CIBLES[k][2]
    dest = destination or (params or {}).get("export_destination") or "youtube"
    return "auto", float(LUFS.get(dest, -14)), -1.0


def empreinte(projet):
    """Ce qui change le son du film : si l'empreinte change, la mesure est à refaire."""
    cles = ("media", "piste", "debut", "src_debut", "src_fin", "vitesse", "volume", "muet", "fondu_entree", "fondu_sortie",
            "fondus", "effets_son", "retouches_voix")
    d = {"c": [{k: c.get(k) for k in cles} for c in sorted(projet.clips, key=lambda c: (c["piste"], c["debut"]))],
         "m": sorted(projet.d.get("pistes_muettes") or []), "s": sorted(projet.d.get("pistes_solo") or []),
         "d": projet.d.get("ducking", True)}
    return hashlib.sha1(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:16]


_LIGNE = re.compile(r"t:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.]+|-inf|nan)\s+S:\s*(-?[\d.]+|-inf|nan)")


def _nombre(x, defaut=-70.0):
    try:
        v = float(x)
        return v if v == v and v > -70 else defaut          # sous -70 LUFS : silence
    except (TypeError, ValueError):
        return defaut


def lire_ebur128(texte):
    """Lit la sortie du filtre ebur128 : {"integre", "lra", "crete", "court": [(t, S)]}."""
    court = [(round(float(m.group(1)), 2), _nombre(m.group(3))) for m in _LIGNE.finditer(texte)]
    resume = texte[texte.rfind("Summary:"):] if "Summary:" in texte else texte
    i = re.search(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", resume)
    l = re.search(r"LRA:\s*(-?[\d.]+)\s*LU", resume)
    p = re.search(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", resume)
    return {"integre": _nombre(i.group(1) if i else None), "lra": _nombre(l.group(1) if l else None, 0.0),
            "crete": _nombre(p.group(1) if p else None), "court": court[::3]}       # un point toutes les 0,3 s


def mesurer(chemin, progression=None, arret=lambda: False, duree=None):
    """Mesure EBU R128 d'un fichier (son ou vidéo)."""
    from . import moteur
    if duree is None:
        duree = float((moteur.sonder(chemin) or {}).get("duree") or 0)
    if progression and duree:
        # la progression passe par -progress ; ebur128 écrit dans le journal : niveau « info » gardé
        args = ["-nostats", "-loglevel", "info", "-i", chemin, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]
        txt = moteur.lancer(args, progression=progression, duree=duree, arret=arret)
    else:
        txt = moteur.lancer(["-nostats", "-i", chemin, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], delai=3600)
    return lire_ebur128(txt)


def melanger(projet, sortie, params=None, progression=None, arret=lambda: False):
    """Le son du film mélangé comme à l'export, sans le ramener à la cible (WAV). Renvoie la durée."""
    from . import export, moteur
    from .projet import fin_clip
    ex = export.Exportateur(projet, sortie, "youtube", params=params)
    ex.normaliser = False
    fins = [fin_clip(c) for c in ex.p.clips_piste("video")] + [x.get("fin", 0) for x in ex.p.titres + ex.p.goodies]
    ex.duree = max(fins + [0.0]) or max([fin_clip(c) for c in ex.p.clips] + [1.0])
    try:
        a = ex._son()
        script = os.path.join(ex.tmp, "filtres_son.txt")
        with open(script, "w", encoding="utf-8") as f:
            f.write(";\n".join(ex.filtres))
        args = [x for e in ex.entrees for x in e] + moteur.args_script_filtres(script) + \
            ["-map", f"[{a}]", "-t", f"{ex.duree:.3f}", "-c:a", "pcm_s16le", "-ar", "48000", sortie]
        moteur.lancer(args, progression=progression, duree=ex.duree, arret=arret)
    finally:
        ex.nettoyer()
    return ex.duree


def mesurer_projet(projet, params=None, progression=None, arret=lambda: False):
    """Mesure le film entier ; le résultat est gardé dans le projet (projet.d["son_mesure"]) avec son empreinte."""
    av = lambda f, t="": progression and progression(f, t)
    tmp = tempfile.mkdtemp(prefix="philcut-son-")
    wav = os.path.join(tmp, "film.wav")
    try:
        av(0.0, _("Mélange du son du film"))
        duree = melanger(projet, wav, params, lambda f: av(0.6 * f, _("Mélange du son du film")), arret)
        r = mesurer(wav, lambda f: av(0.6 + 0.4 * f, _("Mesure du volume")), arret, duree)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    r["empreinte"] = empreinte(projet)
    return r


def a_jour(projet):
    """La mesure gardée, si le son du film n'a pas changé depuis ; sinon None."""
    m = projet.d.get("son_mesure")
    return m if m and m.get("empreinte") == empreinte(projet) else None


def court_terme(mesure, t):
    """Le volume court terme (3 s) mesuré autour de l'instant t."""
    pts = (mesure or {}).get("court") or []
    if not pts:
        return None
    import bisect
    k = bisect.bisect_left([p[0] for p in pts], t)
    return pts[min(k, len(pts) - 1)][1]


def verdict(mesure, lufs, crete=-1.0):
    """("ok" | "fort" | "faible" | "sature", phrase) pour un résultat de mesure et une cible."""
    i, p = mesure.get("integre", -70.0), mesure.get("crete", -70.0)
    if i <= -69:
        return "faible", _("Le film est muet ou presque.")
    if i > lufs + ECART_TOLERE:
        etat = "fort"
    elif i < lufs - ECART_TOLERE:
        etat = "faible"
    elif p > crete + 0.5:
        etat = "sature"
    else:
        etat = "ok"
    txt = _("Volume du film : {i} LUFS (cible {c}), crête {p} dBTP, plage {l} LU.", i=f"{i:.1f}", c=f"{lufs:.0f}", p=f"{p:.1f}",
            l=f"{mesure.get('lra', 0.0):.1f}")
    return etat, txt + " " + {"ok": _("✓ Au bon niveau."), "fort": _("Trop fort pour la cible."),
                              "faible": _("Trop faible pour la cible."), "sature": _("Crêtes trop hautes : risque de son saturé.")}[etat]
