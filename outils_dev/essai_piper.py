"""Essai réel du moteur de voix (Piper, piper1-gpl) fabriqué par moteur_piper.yml (1.2.3).

Usage : python outils_dev/essai_piper.py <dossier du moteur> <dossier de travail>

Vérifie, avec le moteur tel qu'il sera livré (exécutable, bibliothèques, espeak-ng-data à côté) :
- que « piper --version » répond ;
- qu'une voix au nouveau format (rhasspy/piper-voices, main) parle ;
- qu'une voix à l'ancien format (révision épinglée en 1.1.24) parle toujours ;
- que la lecture phrase par phrase (--output_dir, une ligne = un fichier) marche, pour les pauses entre les phrases."""
import os
import subprocess
import sys
import urllib.request
import wave

VOIX = {
    "nouvelle": "main",
    "ancienne": "e7229f7d33a10e145e109b886d661984201ac3c4",
}
CHEMIN = "fr/fr_FR/siwis/medium/fr_FR-siwis-medium"
PHRASE = "Bonjour, ceci est un essai de la voix de synthèse. Tout fonctionne bien."


def telecharger(url, dest):
    if not os.path.exists(dest):
        with urllib.request.urlopen(url, timeout=120) as r, open(dest + ".part", "wb") as f:
            f.write(r.read())
        os.replace(dest + ".part", dest)


def duree(wav):
    with wave.open(wav) as w:
        return w.getnframes() / float(w.getframerate())


def main(moteur, travail):
    os.makedirs(travail, exist_ok=True)
    exe = os.path.join(moteur, "piper.exe" if os.name == "nt" else "piper")
    env = dict(os.environ)
    cle = "PATH" if os.name == "nt" else "LD_LIBRARY_PATH"
    env[cle] = moteur + (os.pathsep + env[cle] if env.get(cle) else "")
    erreurs = []
    r = subprocess.run([exe, "--version"], capture_output=True, env=env, cwd=moteur)
    print("version :", r.stdout.decode().strip(), r.stderr.decode().strip()[-300:])
    if r.returncode != 0:
        erreurs.append("--version a échoué")
    for nom, rev in VOIX.items():
        base = os.path.join(travail, f"{nom}-{os.path.basename(CHEMIN)}")
        for ext in (".onnx", ".onnx.json"):
            telecharger(f"https://huggingface.co/rhasspy/piper-voices/resolve/{rev}/{CHEMIN}{ext}", base + ext)
        wav = os.path.join(travail, f"{nom}.wav")
        r = subprocess.run([exe, "--model", base + ".onnx", "--config", base + ".onnx.json", "--output_file", wav,
                            "--length_scale", "1.000", "--noise_scale", "0.667", "--noise_w", "0.800"],
                           input=PHRASE.encode("utf-8"), capture_output=True, env=env, cwd=moteur, timeout=300)
        if r.returncode != 0 or not os.path.exists(wav):
            erreurs.append(f"voix {nom} : {r.stderr.decode('utf-8', 'replace')[-400:]}")
            continue
        d = duree(wav)
        print(f"voix {nom} : {d:.2f} s")
        if d < 2.0:
            erreurs.append(f"voix {nom} : son trop court ({d:.2f} s)")
        # phrase par phrase : une ligne = un fichier, dans l'ordre
        sortie = os.path.join(travail, f"phrases-{nom}")
        os.makedirs(sortie, exist_ok=True)
        r = subprocess.run([exe, "--model", base + ".onnx", "--config", base + ".onnx.json", "--output_dir", sortie],
                           input="Première phrase.\nDeuxième phrase.\n".encode("utf-8"), capture_output=True, env=env,
                           cwd=moteur, timeout=300)
        lignes = [x.strip() for x in r.stdout.decode("utf-8", "replace").splitlines() if x.strip().endswith(".wav")]
        print(f"phrases {nom} :", lignes)
        if r.returncode != 0 or len(lignes) != 2 or not all(os.path.exists(x) and duree(x) > 0.3 for x in lignes):
            erreurs.append(f"phrases {nom} : {r.stderr.decode('utf-8', 'replace')[-400:]}")
    for e in erreurs:
        print(f"::error title=Essai Piper::{e}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])))
