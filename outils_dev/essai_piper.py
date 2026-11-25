"""Essai réel du moteur de voix (Piper, piper1-gpl) fabriqué par moteur_piper.yml (1.2.3).

Usage : python outils_dev/essai_piper.py <dossier du moteur> <dossier de travail>
        python outils_dev/essai_piper.py philcut <moteurs-ia.json> <dossier des archives>   (avec le code de PhilCut)

Vérifie, avec le moteur tel qu'il sera livré (exécutable, bibliothèques, espeak-ng-data à côté) :
- que « piper --version » répond ;
- qu'une voix au nouveau format (rhasspy/piper-voices, main) parle ;
- qu'une voix à l'ancien format (révision épinglée en 1.1.24) parle toujours ;
- que la lecture phrase par phrase (--output_dir, une ligne = un fichier) marche, pour les pauses entre les phrases."""
import os
import subprocess
import sys
import urllib.request

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
    """Durée d'un WAV, entiers ou virgule flottante (le nouveau Piper écrit du float 32 bits)."""
    import struct
    d = open(wav, "rb").read()
    i, octets_s, n = 12, 0, 0
    while i + 8 <= len(d):
        nom, t = d[i:i + 4], struct.unpack("<I", d[i + 4:i + 8])[0]
        if nom == b"fmt ":
            _c, _ca, _taux, octets_s = struct.unpack("<HHII", d[i + 8:i + 20])
        elif nom == b"data":
            n = min(t, len(d) - i - 8)     # le nouveau Piper laisse la taille « en flux » (0x7FFFFFFF) dans l'en-tête
        i += 8 + t + (t & 1)
    return n / float(octets_s or 1)


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


def essai_philcut(manifeste, archives):
    """Installation et lecture par le code de PhilCut : moteur « voix » et voix française du catalogue mis à jour, une
    phrase seule puis deux phrases avec une pause (découpage, recollage, remise en 16 bits)."""
    import tempfile
    os.environ["PHILCUT_IA_MANIFESTE"] = manifeste
    os.environ["PHILCUT_IA_ARCHIVES"] = archives
    os.environ["PHILCUT_IA_DOSSIER"] = tempfile.mkdtemp()
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import packs_ia as P
    import wave
    P.installer_moteur("voix")
    P.installer("voix_fr_femme")
    erreurs = []
    for nom, silence in (("seule", None), ("pause", 0.6)):
        wav = os.path.join(P.dossier(), f"{nom}.wav")
        P.synthese(PHRASE, wav, "voix_fr_femme", {}, silence=silence, expressivite=0.5)
        with wave.open(wav) as w:
            d = w.getnframes() / float(w.getframerate())
        print(f"PhilCut {nom} : {d:.2f} s")
        if not 2.0 < d < 30.0:
            erreurs.append(f"PhilCut {nom} : durée {d:.2f} s")
    for e in erreurs:
        print(f"::error title=Essai Piper PhilCut::{e}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    if sys.argv[1] == "philcut":
        sys.exit(essai_philcut(os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])))
    sys.exit(main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])))
