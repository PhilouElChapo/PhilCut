"""Sous-titres automatiques : transcription de la voix sur ce poste, puis decoupage en lignes courtes calees sur la
timeline du projet. Moteur portable whisper.cpp (Preferences > IA locale, range dans le dossier de PhilCut) ;
faster-whisper en secours s'il est installe (lancement depuis les sources)."""
import os

from . import moteur
from .projet import fin_clip


def disponible():
    from . import packs_ia
    if packs_ia.modele_actif("whisper"):
        return True
    try:
        import faster_whisper     # noqa: F401
        return True
    except ImportError:
        return False


def transcrire_fichier(chemin, langue=None, modele="small", progression=None, params=None, mots=False):
    """chemin : WAV 16 kHz mono. Renvoie [(debut, fin, texte)] ; mots=True : [(debut, fin, texte, [(d, f, mot)])]."""
    from . import packs_ia
    if packs_ia.modele_actif("whisper", params):
        return packs_ia.transcrire(chemin, langue=langue or "fr", params=params, progression=progression, mots=mots)
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        from .langue import _
        raise RuntimeError(_("Aucun modèle de voix sur ce poste : cochez-en un dans Préférences › IA locale.")) from e
    import ctranslate2
    appareil = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    m = WhisperModel(modele, device=appareil, compute_type="float16" if appareil == "cuda" else "int8")
    segments, info = m.transcribe(chemin, language=langue, vad_filter=True, word_timestamps=mots)
    out = []
    for s in segments:
        seg = (float(s.start), float(s.end), s.text.strip())
        if mots:
            seg += ([(float(w.start), float(w.end), w.word.strip()) for w in (s.words or [])],)
        out.append(seg)
        if progression:
            progression(min(0.95, float(s.end) / max(1.0, info.duration or 1.0)))
    return out


def _dossier_tmp():
    from . import packs_ia
    d = os.path.join(packs_ia.dossier(), "tmp")
    os.makedirs(d, exist_ok=True)
    return d


def transcrire_projet(projet, params=None, progression=None, modele="small", karaoke=False, langue=None, pistes=("video",), decouper=True, filtre=None):
    """Transcrit chaque plan vidéo (avec son) et replace les sous-titres sur la timeline du montage.
    karaoke=True : chaque sous-titre garde ses mots datés (ils se colorent quand ils sont prononcés)."""
    out = []
    clips = [c for p in pistes for c in projet.clips_piste(p) if not c.get("muet")]
    for i, c in enumerate(clips):
        m = projet.media(c["media"])
        if not m or not (m.get("fiche") or {}).get("audio"):
            continue
        tmp = os.path.join(_dossier_tmp(), f"philcut_voix_{c['id']}.wav")
        try:
            moteur.lancer(["-ss", f"{c['src_debut']:.3f}", "-t", f"{c['src_fin'] - c['src_debut']:.3f}", "-i", m["chemin"], "-vn"]
                          + (["-af", filtre] if filtre else []) + ["-ac", "1", "-ar", "16000", tmp])
            segs = transcrire_fichier(tmp, langue=langue, modele=modele, params=params, mots=karaoke,
                                      progression=lambda f: progression and progression((i + f) / len(clips), m["nom"]))
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        v = c.get("vitesse", 1.0)
        for seg in segs:
            a, b, texte = seg[0], seg[1], seg[2]
            d0 = c["debut"] + a / v
            f0 = min(fin_clip(c), c["debut"] + b / v)
            if f0 - d0 > 0.2 and texte:
                if karaoke:
                    ms = [(c["debut"] + x / v, min(f0, c["debut"] + y / v), w) for x, y, w in (seg[3] if len(seg) > 3 else [])]
                    out.extend(decouper_mots(d0, f0, texte, ms))
                elif decouper:
                    out.extend(_decouper(d0, f0, texte))
                else:
                    out.append((d0, f0, texte))
    return out


def decouper_mots(d, f, texte, mots, max_car=36):
    """Lignes de karaoké courtes : on coupe entre deux mots, la ligne dure du premier au dernier mot."""
    if not mots:
        mots = [(d + i * (f - d) / max(1, len(texte.split())), d + (i + 1) * (f - d) / max(1, len(texte.split())), w)
                for i, w in enumerate(texte.split())]
    out, ligne = [], []
    for m in mots:
        if ligne and len(" ".join(w for _a, _b, w in ligne + [m])) > max_car:
            out.append(ligne)
            ligne = []
        ligne.append(m)
    if ligne:
        out.append(ligne)
    res = []
    for k, l in enumerate(out):
        debut = d if k == 0 else l[0][0]
        fin = f if k == len(out) - 1 else max(l[-1][1], out[k + 1][0][0] - 0.01)
        res.append((debut, fin, " ".join(w for _a, _b, w in l), l))
    return res


def _decouper(d, f, texte, max_car=42):
    mots = texte.split()
    if len(texte) <= max_car or len(mots) < 4:
        return [(d, f, texte)]
    moitie = len(mots) // 2
    t = (d + f) / 2
    return _decouper(d, t, " ".join(mots[:moitie]), max_car) + _decouper(t, f, " ".join(mots[moitie:]), max_car)
