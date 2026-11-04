"""Montage au rythme de la musique (cahier des charges 8.4.6 et 13.3.2).

- analyser(chemin)   : tempo (BPM), temps (grille régulière calée sur les attaques) et temps forts (début de mesure)
- caler(projet, …)   : chaque coupe entre deux plans tombe sur un temps (ou un début de mesure) de la musique ;
                       les plans se raccourcissent ou s'allongent un peu, dans la limite du rush disponible
Tout est local et rapide (numpy), sans IA.
"""
from . import moteur

try:
    import numpy as np
except ImportError:          # pragma: no cover
    np = None

TAUX = 11025
SAUT = 256                   # ~23 ms par trame


def _signal(chemin):
    brut = moteur.sortie(["-i", chemin, "-vn", "-ac", "1", "-ar", str(TAUX), "-f", "s16le", "pipe:1"], delai=600)
    return np.frombuffer(brut[: len(brut) - len(brut) % 2], dtype=np.int16).astype(np.float32) / 32768.0


def enveloppe(x):
    """Enveloppe des attaques (flux spectral positif), une valeur par trame de SAUT échantillons."""
    n = 1024
    if len(x) < n * 4:
        return np.zeros(0, np.float32)
    trames = np.lib.stride_tricks.sliding_window_view(x, n)[::SAUT] * np.hanning(n).astype(np.float32)
    spectre = np.log1p(np.abs(np.fft.rfft(trames, axis=1)) * 10)
    flux = np.maximum(0.0, np.diff(spectre, axis=0)).sum(axis=1)
    flux = np.concatenate([[0.0], flux])
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")          # retire la tendance lente
    return np.maximum(flux, 0.0)


def analyser(chemin, bpm_min=60, bpm_max=180):
    """{"bpm", "temps": [s], "forts": [s], "duree"}. Vide si la musique est trop courte ou sans rythme net."""
    vide = {"bpm": 0, "temps": [], "forts": [], "duree": 0.0}
    if np is None:
        return vide
    try:
        x = _signal(chemin)
    except moteur.ErreurMoteur:
        return vide
    env = enveloppe(x)
    if len(env) < 200 or env.max() <= 0:
        return vide
    fps = TAUX / SAUT
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    lag_min, lag_max = int(fps * 60 / bpm_max), int(fps * 60 / bpm_min)
    lags = np.arange(lag_min, min(lag_max, len(ac) - 1))
    if not len(lags):
        return vide
    poids = np.exp(-0.5 * (np.log2((60 * fps / lags) / 120.0) / 0.9) ** 2)   # préfère les tempos autour de 120
    lag = int(lags[np.argmax(ac[lags] * poids)])
    # affinage : période fractionnaire et phase qui font tomber le plus d'attaques sur la grille (sur tout le morceau)
    lisse = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    meilleur = (-1.0, float(lag), 0.0)
    for periode_t in np.linspace(lag - 1.5, lag + 1.5, 121):
        k = np.arange(int(len(env) / periode_t))
        for phase in np.arange(0.0, periode_t, 0.25):
            idx = np.round(phase + k * periode_t).astype(int)
            idx = idx[idx < len(env)]
            sc = lisse[idx].sum() / max(1, len(idx))
            if sc > meilleur[0]:
                meilleur = (sc, float(periode_t), float(phase))
    _sc, periode_t, phase = meilleur
    periode = periode_t / fps
    decalage = 512 / TAUX                # l'attaque est au milieu de la fenêtre d'analyse
    temps = [round((phase + k * periode_t) / fps + decalage, 3) for k in range(int((len(env) - phase) / periode_t) + 1)]
    # début de mesure : parmi les 4 positions possibles, celle dont les temps sont les plus forts
    forces = [sum(lisse[min(len(env) - 1, int(round((t - decalage) * fps)))] for t in temps[k::4]) for k in range(min(4, len(temps)))]
    k = int(np.argmax(forces)) if forces else 0
    return {"bpm": round(60 / periode, 1), "temps": temps, "forts": temps[k::4], "duree": round(len(x) / TAUX, 3)}


def temps_montage(clip_musique, analyse, forts=False):
    """Instants des temps (ou des temps forts) sur la timeline du montage, pour une musique posée sur la piste audio."""
    v = float(clip_musique.get("vitesse", 1.0) or 1.0)
    d0, f0 = clip_musique["src_debut"], clip_musique["src_fin"]
    return [clip_musique["debut"] + (t - d0) / v for t in analyse["forts" if forts else "temps"] if d0 <= t <= f0]


def caler(projet, clip_musique, analyse, forts=False, plan_mini=0.6):
    """Chaque coupe vidéo est déplacée sur le temps de musique le plus proche : on rogne ou on allonge la fin du plan
    (sans dépasser le rush), puis les plans suivants se recollent. Renvoie le nombre de coupes calées."""
    grille = temps_montage(clip_musique, analyse, forts)
    if len(grille) < 2:
        return 0
    from .projet import fin_clip
    clips = projet.clips_piste("video")
    n = 0
    t = clips[0]["debut"] if clips else 0.0
    for i, c in enumerate(clips):
        c["debut"] = t
        if i == len(clips) - 1:
            break
        v = float(c.get("vitesse", 1.0) or 1.0)
        m = projet.media(c["media"]) or {}
        dispo = (m.get("fiche") or {}).get("duree") or 1e9
        if m.get("genre") == "image":
            dispo = 1e9
        fin = fin_clip(c)
        mini = c["debut"] + plan_mini
        maxi = c["debut"] + (dispo - c["src_debut"]) / v
        candidats = [g for g in grille if mini <= g <= maxi]
        if candidats:
            cible = min(candidats, key=lambda g: abs(g - fin))
            if abs(cible - fin) <= max(0.6, 60.0 / max(analyse.get("bpm") or 120, 1) * (4 if forts else 1)):
                c["src_fin"] = c["src_debut"] + (cible - c["debut"]) * v
                n += 1
        t = fin_clip(c)
    return n
