"""Essai réel de l'IA locale portable, avec le code de PhilCut (app/packs_ia.py) et de petits modèles.

Variables : PHILCUT_IA_MANIFESTE (catalogue), PHILCUT_IA_ARCHIVES (archives des moteurs fabriquées),
PHILCUT_IA_DOSSIER (dossier d'essai). Sortie non nulle si un moteur ne répond pas.
"""
import os, shutil, subprocess, sys, time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from app import packs_ia as P   # noqa: E402


def note(titre, texte):
    print(f"::notice title={titre}::{texte}", flush=True)


def image_essai():
    import cv2, numpy as np
    img = np.full((240, 320, 3), (235, 206, 135), np.uint8)          # ciel bleu (BGR)
    cv2.rectangle(img, (0, 170), (320, 240), (60, 140, 60), -1)       # herbe
    cv2.circle(img, (160, 95), 28, (40, 80, 200), -1)                 # tête
    cv2.rectangle(img, (130, 120), (190, 200), (40, 40, 160), -1)     # corps
    ok, png = cv2.imencode(".png", img)
    return img, png.tobytes()


def main():
    params = {"ia_poste_leger": True}
    erreurs = []
    img, png = image_essai()
    print("Catalogue :", ", ".join(sorted(P.modeles(avec_essai=True))))

    # 1. vision
    try:
        if P.moteur_info("vision_gpu"):   # la machine d'essai n'a pas de carte : on vérifie que le moteur Vulkan démarre ou cède la place
            P._carte = "carte d'essai (machine sans carte graphique)"
        t0 = time.time()
        P.installer("vision_test", lambda f, t="": None)
        note("Vision installée", f"{P.taille_texte(P.taille_dossier())} en {time.time() - t0:.0f} s")
        t0 = time.time()
        with P.ServeurVision("vision_test", params) as s:
            demarrage = time.time() - t0
            t1 = time.time()
            r = s.generer("Describe this picture in one short sentence.", [png])
            note("Vision répond", f"{r.strip()[:150]!r} (moteur {s.mode}, Vulkan installé : {P.moteur_installe('vision_gpu')}, "
                                  f"démarrage {demarrage:.1f} s, réponse {time.time() - t1:.1f} s)")
            j = s.generer('Reply with a JSON object {"colour": "<main colour of the sky>"}', [png], json_attendu=True)
            note("Vision JSON", j.strip()[:150])
        assert P.ServeurVision  # serveur arrêté à la sortie du bloc
    except Exception as e:      # noqa: BLE001
        erreurs.append(f"vision : {e}")
        print(f"::error title=Vision::{e}")
        try:
            print(open(os.path.join(P.dossier(), "journal_vision.txt"), encoding="utf-8", errors="replace").read()[-3000:])
        except OSError:
            pass

    # 2. voix
    try:
        P.installer("whisper_test")
        wav = os.path.join(P.dossier(), "voix.wav")
        brut = wav + ".brut.wav"
        phrase = "Bonjour, ceci est un essai de sous-titres pour PhilCut."
        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        piper = False
        if P.moteur_info("voix") and "voix_fr_femme" in P.modeles():      # voix de synthèse portable (Piper)
            try:
                t0 = time.time()
                P.installer("voix_fr_femme")
                P.synthese(phrase, brut, "voix_fr_femme", params)
                note("Voix de synthèse", f"Piper : {os.path.getsize(brut) // 1024} Ko en {time.time() - t0:.1f} s (installation comprise)")
                piper = True
            except Exception as e:      # noqa: BLE001
                print(f"::warning title=Voix de synthèse::{e}")
        if piper and shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-y", "-i", brut, "-ac", "1", "-ar", "16000", wav], check=True, capture_output=True)
            espeak = "piper"
        elif espeak and shutil.which("ffmpeg"):
            subprocess.run([espeak, "-v", "fr", "-s", "140", "-w", brut, phrase], check=True)
            subprocess.run(["ffmpeg", "-y", "-i", brut, "-ac", "1", "-ar", "16000", wav], check=True, capture_output=True)
        else:   # pas de synthèse vocale sur ce poste : un son simple, pour vérifier que le moteur tourne
            import math, struct, wave
            espeak = None
            with wave.open(wav, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(16000 * 3)))
        t0 = time.time()
        segs = P.transcrire(wav, "whisper_test", "fr", params)
        texte = " ".join(s[2] for s in segs)
        note("Voix transcrite", f"{texte[:150]!r} ({len(segs)} segment(s), {time.time() - t0:.1f} s)")
        mots = P.transcrire(wav, "whisper_test", "fr", params, mots=True)
        note("Mots datés (karaoké)", " ".join(f"{w}@{d:.1f}" for seg in mots for d, _f, w in seg[3])[:200])
        if espeak and "essai" not in texte.lower():
            print("::warning title=Voix::le mot « essai » n'a pas été reconnu (modèle d'essai minuscule)")
    except Exception as e:      # noqa: BLE001
        erreurs.append(f"voix : {e}")
        print(f"::error title=Voix::{e}")

    # 3. détourage
    try:
        if not P.onnx_present():
            raise RuntimeError("onnxruntime absent")
        P.installer("detourage_leger")
        t0 = time.time()
        m = P.masque_personne(img, "detourage_leger", params)
        assert m is not None and m.shape == img.shape[:2], m
        centre, coin = int(m[150, 160]), int(m[10, 10])
        note("Détourage", f"masque {m.shape[1]}×{m.shape[0]} en {time.time() - t0:.2f} s ; centre {centre}, coin {coin}")
    except Exception as e:      # noqa: BLE001
        erreurs.append(f"détourage : {e}")
        print(f"::error title=Détourage::{e}")

    # 4. tout retirer
    avant = P.taille_dossier()
    for cle in list(P.installes()):
        P.supprimer(cle)
    reste = [c for c in P.etat()]
    note("Désinstallation", f"{P.taille_texte(avant)} libérés ; reste : {reste or 'rien'} ; dossier {P.taille_texte(P.taille_dossier())}")
    if reste:
        erreurs.append("désinstallation incomplète : " + ", ".join(reste))
    if erreurs:
        print("ECHEC : " + " ; ".join(erreurs))
        return 1
    print("ESSAI IA LOCALE : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
