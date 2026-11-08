"""Monter par le texte (0.9.23), comme Descript ou Premiere : les rushes sont transcrits sur ce poste (whisper.cpp,
mots datés), le texte du montage s'affiche dans l'ordre de la timeline ; effacer une phrase dans le texte coupe la
vidéo (la suite se recolle), les « euh » et les silences trop longs s'enlèvent d'un clic.

La transcription est gardée dans le projet (par rush, en temps du rush) : elle n'est faite qu'une fois, et le texte
suit toutes les coupes, d'où qu'elles viennent.
"""
import os
import re

from . import moteur
from .langue import _
from .projet import fin_clip

HESITATIONS = {"euh", "heu", "euhh", "euuh", "hum", "hmm", "mmh", "mh", "bah", "ben", "beh", "bref", "um", "uh", "uhm", "erm", "eh",
               "hein"}
MARGE = 0.06            # on garde un souffle avant et après la coupe


def _net(m):
    return re.sub(r"[^\w']", "", (m or "").lower())


def rushes_a_transcrire(projet, piste="video"):
    ids = []
    for c in projet.clips_piste(piste):
        m = projet.media(c["media"])
        if m and m["id"] not in ids and (m.get("fiche") or {}).get("audio") and m.get("mots") is None and os.path.exists(m.get("chemin", "")):
            ids.append(m["id"])
    return ids


def transcrire(projet, params=None, langue=None, progression=None, arret=lambda: False, piste="video"):
    """Transcrit chaque rush de la piste (une fois) : media["mots"] = [[debut, fin, mot], ...] en temps du rush."""
    from . import sous_titres as ST
    ids = rushes_a_transcrire(projet, piste)
    for i, ident in enumerate(ids):
        if arret():
            raise InterruptedError()
        m = projet.media(ident)
        tmp = os.path.join(ST._dossier_tmp(), f"philcut_texte_{ident}.wav")
        try:
            moteur.lancer(["-y", "-i", m["chemin"], "-vn", "-ac", "1", "-ar", "16000", tmp])
            segs = ST.transcrire_fichier(tmp, langue=langue, params=params, mots=True,
                                         progression=lambda f, i=i: progression and progression((i + f) / len(ids), m["nom"]))
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        mots = []
        for seg in segs:
            liste = seg[3] if len(seg) > 3 and seg[3] else [(seg[0], seg[1], seg[2])]
            for d, f, w in liste:
                w = (w or "").strip()
                if w:
                    mots.append([round(float(d), 3), round(float(max(f, d + 0.05)), 3), w])
        m["mots"] = mots
        m["mots_langue"] = langue or "auto"
    projet.modifie = projet.modifie or bool(ids)
    return len(ids)


def mots_du_montage(projet, piste="video"):
    """Les mots entendus dans le montage, dans l'ordre : [{t0, t1, mot, clip, rang}] en temps de la timeline."""
    out = []
    for c in projet.clips_piste(piste):
        m = projet.media(c["media"]) or {}
        if c.get("muet") or not m.get("mots"):
            continue
        v = float(c.get("vitesse", 1.0) or 1.0)
        a, b = float(c["src_debut"]), float(c["src_fin"])
        for d, f, w in m["mots"]:
            if d >= a - 0.02 and d < b - 0.03:
                t0 = c["debut"] + (max(d, a) - a) / v
                t1 = min(fin_clip(c), c["debut"] + (min(f, b) - a) / v)
                out.append({"t0": round(t0, 3), "t1": round(t1, 3), "mot": w, "clip": c["id"], "media": c["media"],
                            "debut_plan": c["debut"], "fin_plan": fin_clip(c)})
    for i, x in enumerate(out):
        x["rang"] = i
    return out


def plage(mots, i, j):
    """Passage des mots i à j (inclus) → [a, b] à couper : du début du premier au début du mot qui suit (même plan)."""
    i, j = sorted((i, j))
    a = max(mots[i]["t0"] - MARGE, mots[i].get("debut_plan", 0.0))
    if i > 0 and mots[i - 1]["clip"] == mots[i]["clip"]:
        a = max(a, mots[i - 1]["t1"])
    if j + 1 < len(mots) and mots[j + 1]["clip"] == mots[j]["clip"]:
        b = mots[j + 1]["t0"] - MARGE
    else:                                         # dernier mot du plan : jamais au-delà, le plan suivant est intact
        b = min(mots[j]["t1"] + 0.15, mots[j].get("fin_plan", 1e9))
    return max(0.0, a), max(a + 0.05, b)


def hesitations(mots):
    """Rangs des « euh », « hum »… (les mots seuls, pas « ben » au milieu d'une phrase : on n'en garde que les isolés)."""
    out = []
    for i, x in enumerate(mots):
        n = _net(x["mot"])
        if n in HESITATIONS:
            if n in ("ben", "bah", "bref", "hein", "eh"):            # mots qui ont aussi un sens : seulement suivis d'une virgule ou d'une pause
                suivant = mots[i + 1] if i + 1 < len(mots) else None
                if not (x["mot"].rstrip().endswith((",", "…", "...")) or (suivant and suivant["t0"] - x["t1"] > 0.35)):
                    continue
            out.append(i)
    return out


def silences(mots, projet, seuil=0.8, piste="video"):
    """Pauses de plus de « seuil » secondes à l'intérieur des plans (entre deux mots, ou avant le premier, après le
    dernier) : [(a, b)] à couper, en gardant un petit souffle de chaque côté."""
    garde = 0.25
    out = []
    par_clip = {}
    for x in mots:
        par_clip.setdefault(x["clip"], []).append(x)
    for c in projet.clips_piste(piste):
        ms = par_clip.get(c["id"])
        if not ms:
            continue
        bornes = [(c["debut"], c["debut"])] + [(x["t0"], x["t1"]) for x in ms] + [(fin_clip(c), fin_clip(c))]
        for (_a0, a1), (b0, _b1) in zip(bornes, bornes[1:]):
            if b0 - a1 > seuil:
                out.append((a1 + garde, b0 - garde))
    return [(a, b) for a, b in out if b - a > 0.1]


def fusionner(plages):
    out = []
    for a, b in sorted(plages):
        if out and a <= out[-1][1] + 0.02:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def couper(projet, plages, sauf=()):
    """Coupe les passages (de la fin vers le début, pour que les temps restent justes) ; renvoie la durée enlevée."""
    total = 0.0
    for a, b in reversed(fusionner(plages)):
        if projet.partie(a, b, False, sauf=sauf):
            total += b - a
    return total


def paragraphes(mots, pause=1.2):
    """Rangs où commence un nouveau paragraphe : autre rush, ou pause longue (une coupe dans le texte n'en crée pas)."""
    out = set()
    for i in range(1, len(mots)):
        if mots[i].get("media") != mots[i - 1].get("media") or mots[i]["t0"] - mots[i - 1]["t1"] > pause:
            out.add(i)
    return out
