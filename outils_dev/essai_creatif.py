"""Essai réel des moteurs créatifs avec le code de PhilCut (app/creatif.py) sur la machine de fabrication (Linux, sans
carte graphique : Vulkan logiciel « lavapipe » pour Real-ESRGAN et RIFE). Sortie non nulle si le moteur d'images,
l'agrandissement ou la profondeur ne marchent pas ; la musique et la vidéo (très lentes sans carte) ne bloquent pas.
"""
import os, subprocess, sys, time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from app import packs_ia as P, creatif as C   # noqa: E402


def note(titre, texte):
    print(f"::notice title={titre}::{texte}", flush=True)


def essai(titre, fonction, bloquant=True):
    t0 = time.time()
    try:
        r = fonction()
        note(titre, f"OK en {time.time() - t0:.0f} s : {r}")
        return True
    except Exception as e:      # noqa: BLE001
        print(f"::{'error' if bloquant else 'warning'} title={titre}::{e}", flush=True)
        for j in ("image", "musique", "musique_lm", "agrandissement", "ralenti", "video"):
            p = os.path.join(P.dossier(), f"journal_{j}.txt")
            if os.path.exists(p) and os.path.getmtime(p) > t0:
                print(open(p, encoding="utf-8", errors="replace").read()[-2500:])
        return not bloquant


def main():
    import cv2, numpy as np
    params = {"ia_poste_leger": False, "ia_gpu": False}
    cat = P.modeles(avec_essai=True)
    print("Catalogue créatif :", ", ".join(sorted(k for k, v in cat.items() if v.get("genre") in ("image", "video", "musique", "anime", "profondeur", "upscale", "interpolation"))))
    d = os.path.abspath("essai_sorties")
    os.makedirs(d, exist_ok=True)
    img = np.full((240, 320, 3), (235, 206, 135), np.uint8)
    cv2.rectangle(img, (0, 170), (320, 240), (60, 140, 60), -1)
    cv2.circle(img, (160, 95), 28, (40, 80, 200), -1)
    src = os.path.join(d, "source.png")
    cv2.imwrite(src, img)
    ok = True

    def image_rapide():
        P.installer("image_rapide", lambda f, t="": None)
        out = C.image("a red sports car on a coastal road, sunny", os.path.join(d, "voiture.png"), params, largeur=256, hauteur=256)
        out2 = C.image("cartoon style, colorful", os.path.join(d, "cartoon.png"), params, init=src, force=0.6, largeur=256, hauteur=256)
        return f"{os.path.getsize(out)} + {os.path.getsize(out2)} octets"
    ok &= essai("Images (SD-Turbo)", image_rapide)

    def profondeur():
        P.installer("profondeur", lambda f, t="": None)
        p = C.profondeur(img, params=params)
        out = C.photo_3d(img, os.path.join(d, "photo3d.mp4"), secondes=1.0, ips=12, params=params)
        return f"profondeur {p.shape} min {p.min():.2f} max {p.max():.2f}, photo 3D {os.path.getsize(out)} octets"
    ok &= essai("Profondeur et photo 3D", profondeur)

    vid = os.path.join(d, "court.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=10:d=1", "-pix_fmt", "yuv420p", vid], check=True)

    def agrandir():
        P.installer("upscale_video", lambda f, t="": None)
        out, n = C.agrandir(vid, os.path.join(d, "grand.mp4"), facteur=2, ips=10, params=params, anime=True)
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", out], capture_output=True, text=True)
        return f"{n} images, {r.stdout.strip()}"
    ok &= essai("Agrandissement (Real-ESRGAN)", agrandir, bloquant=False)

    def ralentir():
        P.installer("ralenti_ia", lambda f, t="": None)
        out = C.ralentir(vid, os.path.join(d, "ralenti.mp4"), facteur=2, ips=10, params=params)
        return f"{os.path.getsize(out)} octets"
    essai("Ralenti (RIFE)", ralentir, bloquant=False)

    for cle in [k for k, v in cat.items() if v.get("genre") == "anime"][:1]:
        def anime(cle=cle):
            P.installer(cle, lambda f, t="": None)
            y = C.anime_image(img, cle, params)
            return f"{cle} : {y.shape}, moyenne {y.mean():.0f}"
        essai("Dessin animé (AnimeGANv3)", anime, bloquant=False)
    essai("Dessin classique (OpenCV)", lambda: str(C.dessin_classique(img).shape))

    def musique():
        P.installer("musique_rapide", lambda f, t="": None)
        out = C.musique("lofi", os.path.join(d, "musique.mp3"), duree=10, params=params)
        return f"{os.path.getsize(out)} octets"
    essai("Musique (ACE-Step)", musique, bloquant=False)

    def comprendre():                     # 0.9.37 : la fabrique musique écoute un morceau (ace-understand)
        from app import musique_ia as MI
        r = MI.analyser(os.path.join(d, "musique.mp3"), params)
        return f"compris={r['compris']} bpm={r['bpm']} {r['tonalite']} : {r['caption_en'][:120]}"
    essai("Musique : écoute d'un morceau (ace-understand)", comprendre, bloquant=False)

    def reorchestrer():                   # morceau « à moi » réorchestré (cover)
        from app import musique_ia as MI
        src = os.path.join(d, "musique.mp3")
        MI.declarer(src, a_moi=True)
        f = dict(MI.fiche_vide(), style="symphonie", duree=10, source={"chemin": src, "force": 0.5})
        out, _c = MI.creer(f, os.path.join(d, "reorchestre.mp3"), params)
        return f"{os.path.getsize(out)} octets"
    essai("Musique : réorchestrer un morceau (cover)", reorchestrer, bloquant=False)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
