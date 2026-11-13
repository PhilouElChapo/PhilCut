"""Séparer voix, musique et bruits (0.9.53) — sur ce poste, gratuit, rien n'est envoyé.

Modèle : HT-Demucs (Meta, licence MIT) au format ONNX (« adowu/htdemucs-onnx »), lu par onnxruntime (déjà dans PhilCut).
Il rend quatre pistes : batterie, basse, autres, voix. PhilCut en fait trois, qui s'additionnent exactement au son
d'origine (rien ne se perd) :
- Voix : la piste voix, moins son fond de bruit continu ;
- Musique : batterie + basse + autres, moins leur fond de bruit continu ;
- Bruits : le fond continu (vent, rumeur, ventilation, circulation) retiré des deux.
Le fond de bruit est estimé fréquence par fréquence (niveau bas et stable dans le temps) ; c'est une estimation, on
écoute avant de poser.

Découpage : morceaux de 7,8 s (taille fixe du modèle) qui se chevauchent d'un quart, raccordés par des fondus
triangulaires — la méthode de Demucs lui-même (apply_model). Normalisation moyenne / écart-type comme Demucs.
"""
import os
import wave

from .langue import _

CLE = "separation_sons"
TAUX = 44100
SEGMENT = 343980                     # 7,8 s : taille d'entrée fixe du modèle exporté
CHEVAUCHEMENT = 0.25
ORDRE = ("batterie", "basse", "autres", "voix")
PISTES = ("voix", "musique", "bruits")


class ErreurSeparation(Exception):
    pass


def manquant(params=None):
    """Le texte à montrer si la séparation n'est pas possible sur ce poste, sinon None."""
    from . import packs_ia as P
    if not P.onnx_present():
        return _("Le moteur ONNX de PhilCut est absent : réinstallez PhilCut.")
    if not P.installe(CLE):
        return _("Installez le modèle « Séparer voix, musique et bruits » : Edition › Préférences › IA locale (environ 170 Mo, "
                 "gratuit, licence MIT, tout reste sur ce poste).")
    return None


def _chemin_modele():
    from . import packs_ia as P
    e = P.etat().get(CLE) or {}
    nom = (e.get("roles") or {}).get("modele")
    return os.path.join(P.dossier_modele(CLE), nom) if nom else ""


_session = None


def session(chemin=None, params=None):
    global _session
    chemin = chemin or _chemin_modele()
    if _session is not None and _session[0] == chemin:
        return _session[1]
    import onnxruntime as ort
    from . import packs_ia as P
    o = ort.SessionOptions()
    try:
        o.intra_op_num_threads = P.coeurs(params)
    except Exception:      # noqa: BLE001
        pass
    fournisseurs = [x for x in ("DmlExecutionProvider", "CUDAExecutionProvider") if x in ort.get_available_providers()] + ["CPUExecutionProvider"]
    s = ort.InferenceSession(chemin, o, providers=fournisseurs)
    entrees = s.get_inputs()
    if len(entrees) != 1:
        raise ErreurSeparation(_("Ce modèle de séparation n'est pas du bon type (il attend {n} entrées).", n=len(entrees)))
    _session = (chemin, s)
    return s


# ---------------------------------------------------------------- son
def lire(source, debut=0.0, duree=None):
    """Le son (stéréo, 44,1 kHz, float32, forme (2, n)) d'un fichier, d'un instant à un autre."""
    import numpy as np
    from . import moteur
    args = ["-ss", f"{max(0.0, debut):.3f}"]
    if duree:
        args += ["-t", f"{duree:.3f}"]
    brut = moteur.sortie(args + ["-i", source, "-vn", "-ac", "2", "-ar", str(TAUX), "-f", "f32le", "pipe:1"], delai=1800)
    a = np.frombuffer(brut[: len(brut) - len(brut) % 8], dtype=np.float32)
    if a.size < 2 * TAUX // 10:
        raise ErreurSeparation(_("Pas de son dans ce plan."))
    return a.reshape(-1, 2).T.copy()


def ecrire(chemin, son):
    """WAV 16 bits stéréo 44,1 kHz."""
    import numpy as np
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    x = np.clip(son, -1.0, 1.0)
    pcm = (x.T * 32767.0).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(TAUX)
        w.writeframes(pcm.tobytes())
    return chemin


# ---------------------------------------------------------------- HT-Demucs
def poids_fondu(n):
    """Fondu triangulaire de Demucs (sommet au milieu), jamais nul."""
    import numpy as np
    w = np.concatenate([np.arange(1, n // 2 + 1), np.arange(n - n // 2, 0, -1)]).astype(np.float32)
    return w / w.max()


def morceaux(n, segment=SEGMENT, chevauchement=CHEVAUCHEMENT):
    """Débuts des morceaux : pas de segment × (1 − chevauchement), le dernier se termine au bout du son."""
    pas = int((1 - chevauchement) * segment)
    debuts = list(range(0, max(1, n - segment) + 1, pas)) if n > segment else [0]
    if n > segment and debuts[-1] + segment < n:
        debuts.append(n - segment)
    return debuts


def demucs(son, s=None, progression=None, arret=lambda: False, executer=None):
    """Les quatre pistes de Demucs (batterie, basse, autres, voix), forme (4, 2, n). `executer` : pour les essais."""
    import numpy as np
    n = son.shape[1]
    ref = son.mean(0)
    moy, ecart = float(ref.mean()), float(ref.std()) or 1.0
    x = (son - moy) / (ecart + 1e-8)
    if executer is None:
        s = s or session()
        nom = s.get_inputs()[0].name
        executer = lambda bloc: s.run(None, {nom: bloc})[0]
    sortie = np.zeros((4, 2, n), np.float32)
    somme = np.zeros(n, np.float32)
    w = poids_fondu(SEGMENT)
    debuts = morceaux(n)
    for i, d in enumerate(debuts):
        if arret():
            raise InterruptedError()
        bloc = np.zeros((1, 2, SEGMENT), np.float32)
        fin = min(n, d + SEGMENT)
        bloc[0, :, : fin - d] = x[:, d:fin]
        y = np.asarray(executer(bloc), dtype=np.float32)[0]           # (4, 2, SEGMENT)
        sortie[:, :, d:fin] += y[:, :, : fin - d] * w[: fin - d]
        somme[d:fin] += w[: fin - d]
        if progression:
            progression((i + 1) / len(debuts) * 0.9, _("Séparation : morceau {i} sur {n}", i=i + 1, n=len(debuts)))
    sortie /= np.maximum(somme, 1e-8)
    return sortie * ecart + moy / 4.0


# ---------------------------------------------------------------- fond de bruit continu
def _stft(x, n=2048, pas=512):
    """Transformée par fenêtres centrées (marge d'une demi-fenêtre de chaque côté : les bords sont exacts)."""
    import numpy as np
    fen = np.hanning(n + 1)[:-1].astype(np.float32)
    lx = x.shape[-1]
    xp = np.pad(x, (n // 2, n // 2))
    nb = 1 + max(0, xp.shape[-1] - n + pas - 1) // pas
    xp = np.pad(xp, (0, max(0, (nb - 1) * pas + n - xp.shape[-1])))
    idx = np.arange(n)[None, :] + pas * np.arange(nb)[:, None]
    return np.fft.rfft(xp[idx] * fen, axis=1), fen, lx


def _istft(S, fen, lx, n=2048, pas=512):
    import numpy as np
    trames = np.fft.irfft(S, n=n, axis=1) * fen
    nb = S.shape[0]
    out = np.zeros((nb - 1) * pas + n, np.float64)
    norme = np.zeros_like(out)
    for i in range(nb):
        out[i * pas:i * pas + n] += trames[i]
        norme[i * pas:i * pas + n] += fen ** 2
    out /= np.maximum(norme, 1e-8)
    return out[n // 2:n // 2 + lx].astype(np.float32)


def fond_continu(x, quantile=0.15, marge=1.6):
    """La part « fond continu » d'un son mono : niveau bas et stable de chaque fréquence (quantile sur le temps), retiré
    par un masque doux. Renvoie (fond, reste) avec fond + reste = x."""
    import numpy as np
    S, fen, lx = _stft(x)
    mag = np.abs(S)
    if mag.shape[0] < 4:
        return np.zeros_like(x), x.copy()
    plancher = np.quantile(mag, quantile, axis=0)[None, :] * marge
    masque = np.clip(plancher / np.maximum(mag, 1e-9), 0.0, 1.0) ** 2         # là où le son ne dépasse pas le fond
    fond = _istft(S * masque, fen, lx)
    return fond, x - fond


def trois_pistes(stems):
    """Voix, musique, bruits à partir des quatre pistes de Demucs (somme exacte conservée)."""
    import numpy as np
    voix4 = stems[3]
    musique4 = stems[0] + stems[1] + stems[2]
    voix, musique, bruits = np.zeros_like(voix4), np.zeros_like(voix4), np.zeros_like(voix4)
    for c in range(voix4.shape[0]):
        fv, rv = fond_continu(voix4[c])
        fm, rm = fond_continu(stems[2][c], quantile=0.08, marge=1.2)        # « autres » : prudent, une nappe tenue reste musique
        voix[c], bruits[c] = rv, fv + fm
        musique[c] = musique4[c] - fm
    return {"voix": voix, "musique": musique, "bruits": bruits}


def separer(source, dossier, debut=0.0, duree=None, params=None, progression=None, arret=lambda: False, executer=None):
    """Sépare le son d'un fichier (de debut à debut + duree) en voix, musique et bruits : trois WAV dans `dossier`.
    Renvoie {"voix": chemin, "musique": chemin, "bruits": chemin}."""
    if executer is None:
        m = manquant(params)
        if m:
            raise ErreurSeparation(m)
    if progression:
        progression(0.0, _("Lecture du son"))
    son = lire(source, debut, duree)
    stems = demucs(son, progression=progression, arret=arret, executer=executer)
    if progression:
        progression(0.92, _("Voix, musique et bruits"))
    pistes = trois_pistes(stems)
    os.makedirs(dossier, exist_ok=True)
    base = os.path.splitext(os.path.basename(source))[0]
    out = {}
    for k in PISTES:
        out[k] = ecrire(os.path.join(dossier, f"{base}_{int(debut * 1000)}_{k}.wav"), pistes[k])
    if progression:
        progression(1.0, _("Terminé"))
    return out


def dossier_sorties():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "sons_separes")
    os.makedirs(d, exist_ok=True)
    return d
