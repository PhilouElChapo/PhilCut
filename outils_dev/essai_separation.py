"""Essai réel de la séparation (0.9.53, modèle « separation_sons »), lancé par GitHub Actions (essai_separation.yml) : télécharge HT-Demucs ONNX,
mélange une voix de synthèse (espeak-ng) et une musique synthétique, sépare, et vérifie :
- les quatre pistes ont la bonne forme et s'additionnent au mélange ;
- la piste voix ressemble à la voix (corrélation) bien plus qu'à la musique ;
- voix + musique + bruits redonnent le mélange.
Usage : python outils_dev/essai_separation.py <dossier de travail>"""
import os, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from app import separation as S

URL = "https://huggingface.co/adowu/htdemucs-onnx/resolve/main/htdemucs_fp16weights.onnx"


def ff(*a):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *a], check=True)


def corr(a, b):
    a, b = a.ravel() - a.mean(), b.ravel() - b.mean()
    return float((a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def main(d):
    os.makedirs(d, exist_ok=True)
    mod = os.path.join(d, "htdemucs.onnx")
    if not os.path.exists(mod):
        t = time.time()
        urllib.request.urlretrieve(URL, mod)
        print(f"modèle : {os.path.getsize(mod) / 1e6:.0f} Mo en {time.time() - t:.0f} s")
    texte = ("Bonjour, ceci est un essai de séparation de la voix et de la musique. Nous partons en promenade au bord de la mer, "
             "puis nous passons à autre chose. Le vent souffle un peu, mais la voix doit rester claire et nette.")
    subprocess.run(["espeak-ng", "-v", "fr", "-s", "150", "-w", os.path.join(d, "voix0.wav"), texte], check=True)
    ff("-i", os.path.join(d, "voix0.wav"), "-ac", "2", "-ar", "44100", "-t", "16", os.path.join(d, "voix.wav"))
    # musique : accords + basse + battement, 16 s
    ff("-f", "lavfi", "-i", "sine=f=220:d=16", "-f", "lavfi", "-i", "sine=f=277:d=16", "-f", "lavfi", "-i", "sine=f=330:d=16",
       "-f", "lavfi", "-i", "sine=f=55:d=16", "-f", "lavfi", "-i", "anoisesrc=c=white:a=0.6:d=16",
       "-filter_complex", "[4]volume='if(lt(mod(t,0.5),0.04),1,0)':eval=frame,highpass=f=2000[hat];"
                          "[0][1][2][3][hat]amix=inputs=5:normalize=0,volume=0.12,aformat=channel_layouts=stereo",
       "-ar", "44100", os.path.join(d, "musique.wav"))
    ff("-i", os.path.join(d, "voix.wav"), "-i", os.path.join(d, "musique.wav"), "-filter_complex", "[0][1]amix=inputs=2:normalize=0",
       "-ar", "44100", "-ac", "2", os.path.join(d, "melange.wav"))
    voix = S.lire(os.path.join(d, "voix.wav"))
    musique = S.lire(os.path.join(d, "musique.wav"))
    mix = S.lire(os.path.join(d, "melange.wav"))
    n = min(voix.shape[1], musique.shape[1], mix.shape[1])
    voix, musique, mix = voix[:, :n], musique[:, :n], mix[:, :n]
    s = S.session(mod)
    print("entrée :", [(i.name, i.shape) for i in s.get_inputs()], "sortie :", [(o.name, o.shape) for o in s.get_outputs()])
    t = time.time()
    stems = S.demucs(mix, s=s, progression=lambda f, txt="": None)
    duree = time.time() - t
    print(f"séparation de {n / S.TAUX:.1f} s en {duree:.1f} s (processeur)")
    assert stems.shape == (4, 2, n), stems.shape
    assert np.isfinite(stems).all()
    somme = stems.sum(0)
    c_somme = corr(somme, mix)
    c_vv, c_vm = corr(stems[3], voix), corr(stems[3], musique)
    c_mm = corr(stems[0] + stems[1] + stems[2], musique)
    print(f"somme/mélange {c_somme:.3f} · voix/voix {c_vv:.3f} · voix/musique {c_vm:.3f} · musique/musique {c_mm:.3f}")
    trois = S.trois_pistes(stems)
    reste = trois["voix"] + trois["musique"] + trois["bruits"] - somme
    print(f"écart voix+musique+bruits / somme des pistes : {np.abs(reste).max():.2e}")
    print(f"après le fond continu : voix/voix {corr(trois['voix'], voix):.3f} · musique/musique {corr(trois['musique'], musique):.3f} · "
          f"part des bruits {np.abs(trois['bruits']).mean() / (np.abs(mix).mean() + 1e-9):.3f}")
    ok = c_somme > 0.95 and c_vv > 0.8 and c_vv > c_vm + 0.4 and c_mm > 0.6 and np.abs(reste).max() < 1e-3
    for k, v in trois.items():
        S.ecrire(os.path.join(d, f"sortie_{k}.wav"), v)
    print("RESULTAT", "OK" if ok else "ECHEC")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "essai_sep"))
