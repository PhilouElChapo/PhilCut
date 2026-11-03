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


def transcrire_fichier(chemin, langue=None, modele="small", progression=None, params=None):
    """chemin : WAV 16 kHz mono. Renvoie [(debut, fin, texte)]."""
    from . import packs_ia
    if packs_ia.modele_actif("whisper", params):
        return packs_ia.transcrire(chemin, langue=langue or "fr", params=params, progression=progression)
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        from .langue import _
        raise RuntimeError(_("Aucun modèle de voix sur ce poste : cochez-en un dans Préférences › IA locale.")) from e
    import ctranslate2
    appareil = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    m = WhisperModel(modele, device=appareil, compute_type="float16" if appareil == "cuda" else "int8")
    segments, info = m.transcribe(chemin, language=langue, vad_filter=True, word_timestamps=False)
    out = []
    for s in segments:
        out.append((float(s.start), float(s.end), s.text.strip()))
        if progression:
            progression(min(0.95, float(s.end) / max(1.0, info.duration or 1.0)))
    return out


def _dossier_tmp():
    from . import packs_ia
    d = os.path.join(packs_ia.dossier(), "tmp")
    os.makedirs(d, exist_ok=True)
    return d


def transcrire_projet(projet, params=None, progression=None, modele="small"):
    """Transcrit chaque plan video (avec son) et replace les sous-titres sur la timeline du montage."""
    out = []
    clips = [c for c in projet.clips_piste("video") if not c.get("muet")]
    for i, c in enumerate(clips):
        m = projet.media(c["media"])
        if not m or not (m.get("fiche") or {}).get("audio"):
            continue
        tmp = os.path.join(_dossier_tmp(), f"philcut_voix_{c['id']}.wav")
        try:
            moteur.lancer(["-ss", f"{c['src_debut']:.3f}", "-t", f"{c['src_fin'] - c['src_debut']:.3f}", "-i", m["chemin"], "-vn", "-ac", "1", "-ar", "16000", tmp])
            segs = transcrire_fichier(tmp, modele=modele, params=params,
                                      progression=lambda f: progression and progression((i + f) / len(clips), m["nom"]))
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        v = c.get("vitesse", 1.0)
        for a, b, texte in segs:
            d0 = c["debut"] + a / v
            f0 = min(fin_clip(c), c["debut"] + b / v)
            if f0 - d0 > 0.2 and texte:
                out.extend(_decouper(d0, f0, texte))
    return out


def _decouper(d, f, texte, max_car=42):
    mots = texte.split()
    if len(texte) <= max_car or len(mots) < 4:
        return [(d, f, texte)]
    moitie = len(mots) // 2
    t = (d + f) / 2
    return _decouper(d, t, " ".join(mots[:moitie]), max_car) + _decouper(t, f, " ".join(mots[moitie:]), max_car)
