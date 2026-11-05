"""Vrai autotune : correction de la justesse du chant, sur ce poste.

1. La voix est lue en mono 22 050 Hz ; sa hauteur est mesurée toutes les 11,6 ms (méthode YIN, numpy).
2. Pour chaque instant chanté, on calcule l'écart à la note juste la plus proche (gamme chromatique, ou une tonalité
   majeure / mineure choisie). La force règle la correction : « naturel » ne corrige qu'une partie de l'écart et
   lisse les transitions ; « robot » colle instantanément à la note (l'effet des tubes des années 2000).
3. La correction est appliquée par FFmpeg (filtre rubberband, timbre préservé), piloté instant par instant par un
   fichier de commandes. Le résultat est un nouveau fichier WAV : l'enregistrement d'origine n'est jamais modifié.
"""
import os, subprocess, tempfile, wave

import numpy as np

from .langue import _

NOTES = ["Do", "Do#", "Ré", "Ré#", "Mi", "Fa", "Fa#", "Sol", "Sol#", "La", "La#", "Si"]
GAMMES = {"chromatique": list(range(12)), "majeure": [0, 2, 4, 5, 7, 9, 11], "mineure": [0, 2, 3, 5, 7, 8, 10]}
FORCES = {"naturel": (0.6, 0.12), "net": (0.9, 0.05), "robot": (1.0, 0.0)}      # (part de l'écart corrigée, lissage en s)
TAUX = 22050
TRAME = 1024
PAS = 256


class ErreurAutotune(Exception):
    pass


def lire_mono(chemin, taux=TAUX):
    from . import moteur
    r = subprocess.run([moteur.ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", chemin, "-ac", "1", "-ar", str(taux),
                        "-f", "s16le", "pipe:1"], capture_output=True, timeout=600, **moteur._sans_console())
    if r.returncode != 0:
        raise ErreurAutotune(r.stderr.decode("utf-8", "replace")[-300:])
    return np.frombuffer(r.stdout, dtype="<i2").astype(np.float32) / 32768.0


def hauteurs(x, taux=TAUX, fmin=70.0, fmax=1000.0, seuil=0.15):
    """Fréquence fondamentale par trame (Hz, 0 = pas de note : silence ou souffle), méthode YIN vectorisée."""
    if len(x) < TRAME:
        return np.zeros(0), np.zeros(0)
    n = 1 + (len(x) - TRAME) // PAS
    idx = np.arange(TRAME)[None, :] + PAS * np.arange(n)[:, None]
    tr = x[idx]
    energie = np.sqrt((tr ** 2).mean(axis=1))
    w = TRAME // 2
    tau_max = min(w, int(taux / fmin))
    tau_min = max(2, int(taux / fmax))
    # fonction de différence par FFT : d(tau) = r(0) + r_tau(0) - 2 r(tau)
    Fa = np.fft.rfft(tr[:, :w], n=2 * TRAME, axis=1)       # r(tau) = somme sur j < w de x[j] x[j + tau]
    Fb = np.fft.rfft(tr, n=2 * TRAME, axis=1)
    acf = np.fft.irfft(np.conj(Fa) * Fb, axis=1)[:, :w]
    cs = np.cumsum(tr ** 2, axis=1)
    e0 = cs[:, w - 1][:, None]
    taus = np.arange(w)
    fin = np.clip(taus + w - 1, 0, TRAME - 1)
    debut = taus - 1
    ew = cs[:, fin] - np.where(debut >= 0, cs[:, np.clip(debut, 0, None)], 0)
    d = e0 + ew - 2 * acf
    d[:, 0] = 0
    cumul = np.cumsum(d[:, 1:], axis=1) / np.arange(1, w)[None, :]
    dn = np.ones_like(d)
    dn[:, 1:] = d[:, 1:] / np.maximum(cumul, 1e-12)
    f0 = np.zeros(n)
    for i in range(n):
        if energie[i] < 0.01:
            continue
        ligne = dn[i, tau_min:tau_max]
        sous = np.where(ligne < seuil)[0]
        if len(sous) == 0:
            continue
        k = sous[0]
        while k + 1 < len(ligne) and ligne[k + 1] < ligne[k]:     # creux local
            k += 1
        t = k + tau_min
        if 1 <= t < w - 1:                                          # interpolation parabolique
            a, b, c = dn[i, t - 1], dn[i, t], dn[i, t + 1]
            den = a - 2 * b + c
            t = t + 0.5 * (a - c) / den if abs(den) > 1e-12 else t
        f0[i] = taux / t
    temps = (np.arange(n) * PAS + TRAME / 2) / taux
    return temps, f0


def note_juste(f, tonique=0, gamme="chromatique"):
    """Fréquence de la note de la gamme la plus proche de f."""
    m = 69 + 12 * np.log2(f / 440.0)
    degres = GAMMES.get(gamme, GAMMES["chromatique"])
    base = np.floor(m)
    candidats = []
    for octave in (-12, 0, 12):
        for dgr in degres:
            n = (base // 12) * 12 + tonique + dgr + octave
            candidats.append(n)
    candidats = np.array(candidats)
    cible = candidats[np.argmin(np.abs(candidats - m))]
    return 440.0 * 2 ** ((cible - 69) / 12)


def rapports(temps, f0, tonique=0, gamme="chromatique", force="naturel"):
    """Rapport de hauteur à appliquer par trame (1 = rien), lissé selon la force."""
    part, lissage = FORCES.get(force, FORCES["naturel"])
    r = np.ones(len(f0))
    for i, f in enumerate(f0):
        if f > 0:
            cible = note_juste(f, tonique, gamme)
            r[i] = (cible / f) ** part
    if lissage > 0 and len(r) > 2:
        k = max(1, int(lissage * TAUX / PAS))
        noyau = np.ones(k) / k
        voisees = f0 > 0
        lisse = np.convolve(np.log(r), noyau, mode="same")
        r = np.where(voisees, np.exp(lisse), 1.0)
    return np.clip(r, 0.5, 2.0)


def corriger(entree, sortie, tonique=0, gamme="chromatique", force="naturel", progression=None):
    """Ecrit dans `sortie` (WAV) la voix corrigée. Renvoie un petit bilan (écart moyen avant, en cents)."""
    from . import moteur
    if not moteur.filtre_disponible("rubberband"):
        raise ErreurAutotune(_("Le moteur vidéo de ce poste n'a pas le filtre « rubberband » : l'autotune n'est pas disponible ici."))
    p = progression or (lambda f: None)
    x = lire_mono(entree)
    p(0.15)
    temps, f0 = hauteurs(x)
    p(0.45)
    r = rapports(temps, f0, tonique, gamme, force)
    voisees = f0 > 0
    ecart = float(np.mean(np.abs(1200 * np.log2(np.maximum(r[voisees], 1e-6))))) if voisees.any() else 0.0
    # fichier de commandes : une consigne de hauteur quand elle change de plus de 3 cents
    lignes, dernier = [], None
    for t, k in zip(temps, r):
        if dernier is None or abs(1200 * np.log2(k / dernier)) > 3:
            lignes.append(f"{t:.4f} rubberband pitch {k:.5f};")
            dernier = k
    tmp = tempfile.mkdtemp(prefix="philcut_autotune_")
    cmd_f = os.path.join(tmp, "hauteurs.txt")
    with open(cmd_f, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    chemin_cmd = cmd_f.replace("\\", "/").replace(":", "\\:")
    filtre = f"asendcmd=f='{chemin_cmd}',rubberband=pitch=1:formant=preserved:pitchq=quality"
    moteur.lancer(["-i", entree, "-af", filtre, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", sortie])
    p(1.0)
    for n in os.listdir(tmp):
        os.remove(os.path.join(tmp, n))
    os.rmdir(tmp)
    return {"ecart_cents": round(ecart, 1), "notes": int(voisees.sum())}
