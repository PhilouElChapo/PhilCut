"""Moteurs créatifs de l'IA locale de PhilCut (workflow « Moteurs créatifs ») : images et vidéo (stable-diffusion.cpp),
musique (acestep.cpp), agrandissement (Real-ESRGAN ncnn), ralenti (RIFE ncnn), modèles ONNX (dessin animé, profondeur).

  python outils_dev/moteurs_creatifs.py versions [sortie.json]   -> versions et archives officielles à reprendre
  python outils_dev/moteurs_creatifs.py modeles sortie.json       -> catalogue des modèles (Hugging Face, GitHub)
  python outils_dev/moteurs_creatifs.py assembler dossier         -> moteurs-creatifs.json (fusionné par PhilCut au catalogue principal)

Chaque modèle porte la ligne de commande à lancer (« args », gabarits {modele}, {prompt}…) : on corrige une option en
republiant le catalogue, sans nouvelle version de PhilCut.
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moteurs_ia import UA, _derniere, _hf_fichiers, empreinte, gh, taille_distante   # noqa: E402,F401

NEGATIF = "blurry, low quality, deformed, watermark, text, signature, extra fingers"
ARGS_IMAGE = ["-m", "{modele}", "-p", "{prompt}", "-n", "{negatif}", "-W", "{largeur}", "-H", "{hauteur}", "--steps", "{etapes}",
              "--cfg-scale", "{cfg}", "--sampling-method", "euler_a", "-s", "{graine}", "-t", "{coeurs}", "-o", "{sortie}"]
ARGS_INIT = ["-i", "{image}", "--strength", "{force}"]

# emplacement : (nom, genre, [(rôle, dépôt, [fichiers préférés…] ou motif)], options)
MODELES = {
    "image_rapide": ("Images rapides (SD-Turbo)", "image", [("modele", "stabilityai/sd-turbo", ["sd_turbo.safetensors"])],
                     {"qualite": 3, "memoire_go": 4, "note": "Une image en quelques secondes avec une carte graphique, une minute sans.",
                      "args": ARGS_IMAGE, "args_init": ARGS_INIT, "etapes": 4, "cfg": 1.0, "taille_px": 512}),
    "image_qualite": ("Images de qualité (SDXL-Turbo)", "image", [("modele", "stabilityai/sdxl-turbo", ["sd_xl_turbo_1.0_fp16.safetensors"]),
                                                                    ("vae", "madebyollin/sdxl-vae-fp16-fix", ["sdxl_vae.safetensors"])],
                      {"qualite": 5, "memoire_go": 8, "note": "Plus fin et plus fidèle à la phrase ; carte graphique de 8 Go conseillée.",
                       "args": ARGS_IMAGE[:2] + ["--vae", "{vae}"] + ARGS_IMAGE[2:], "args_init": ARGS_INIT, "etapes": 4, "cfg": 1.0, "taille_px": 768}),
    "video_wan": ("Vidéo IA (Wan 2.2 TI2V 5B, expérimental)", "video",
                  [("modele", "QuantStack/Wan2.2-TI2V-5B-GGUF", "gguf:Q4_K_M,Q4_K_S,Q5_K_M,Q8_0"),
                   ("vae", "Comfy-Org/Wan_2.2_ComfyUI_Repackaged", ["split_files/vae/wan2.2_vae.safetensors"]),
                   ("t5xxl", "city96/umt5-xxl-encoder-gguf", "gguf:Q4_K_M,Q5_K_M,Q8_0")],
                  {"qualite": 4, "memoire_go": 8, "note": "Anime 2 à 3 secondes à partir d'une image ; plusieurs minutes même avec une carte graphique.",
                   "args": ["-M", "vid_gen", "--diffusion-model", "{modele}", "--vae", "{vae}", "--t5xxl", "{t5xxl}", "-p", "{prompt}",
                            "-n", "{negatif}", "--cfg-scale", "5.0", "--sampling-method", "euler", "--flow-shift", "3.0", "-W", "{largeur}",
                            "-H", "{hauteur}", "--video-frames", "{images}", "--steps", "{etapes}", "--offload-to-cpu", "--vae-tiling",
                            "-s", "{graine}", "-t", "{coeurs}", "-o", "{sortie}"],
                   "args_init": ["-i", "{image}"], "etapes": 20, "taille_px": 480}),
    "musique_rapide": ("Musique rapide (ACE-Step 1.5, LM 0.6B)", "musique",
                       [("vae", "Serveurperso/ACE-Step-1.5-GGUF", ["vae-BF16.gguf"]),
                        ("texte", "Serveurperso/ACE-Step-1.5-GGUF", ["Qwen3-Embedding-0.6B-Q8_0.gguf"]),
                        ("lm", "Serveurperso/ACE-Step-1.5-GGUF", ["acestep-5Hz-lm-0.6B-Q8_0.gguf"]),
                        ("dit", "Serveurperso/ACE-Step-1.5-GGUF", ["acestep-v15-turbo-Q4_K_M.gguf", "acestep-v15-turbo-Q8_0.gguf"])],
                       {"qualite": 3, "memoire_go": 4, "note": "Un morceau d'une minute en une à deux minutes avec une carte graphique (licence MIT)."}),
    "musique_qualite": ("Musique de qualité (ACE-Step 1.5, LM 1.7B)", "musique",
                        [("vae", "Serveurperso/ACE-Step-1.5-GGUF", ["vae-BF16.gguf"]),
                         ("texte", "Serveurperso/ACE-Step-1.5-GGUF", ["Qwen3-Embedding-0.6B-Q8_0.gguf"]),
                         ("lm", "Serveurperso/ACE-Step-1.5-GGUF", ["acestep-5Hz-lm-1.7B-Q8_0.gguf"]),
                         ("dit", "Serveurperso/ACE-Step-1.5-GGUF", ["acestep-v15-turbo-Q8_0.gguf"])],
                        {"qualite": 5, "memoire_go": 8, "note": "Meilleure musique et meilleures paroles ; carte graphique de 8 Go conseillée."}),
    "profondeur": ("Profondeur (Depth Anything V2 small)", "profondeur",
                   [("modele", "onnx-community/depth-anything-v2-small", ["onnx/model.onnx", "onnx/model_fp16.onnx"])],
                   {"qualite": 4, "memoire_go": 2, "note": "Photo 3D, flou d'arrière-plan, brume : sur le processeur, rapide (Apache 2.0)."}),
}
ANIMEGAN = {"anime_hayao": ("Dessin animé, style Hayao", "Hayao"), "anime_shinkai": ("Dessin animé, style Shinkai (ciels lumineux)", "Shinkai"),
            "anime_croquis": ("Croquis au crayon", "Sketch")}
MOTEURS_SEULS = {"upscale_video": ("Agrandissement IA (Real-ESRGAN)", "upscale", "upscale"),
                 "ralenti_ia": ("Ralenti fluide IA (RIFE)", "interpolation", "interpolation")}


def versions():
    out = {}
    tag, n = _derniere("leejet/stable-diffusion.cpp", {"sd_win": lambda x: "bin-win-cpu-x64" in x or ("win" in x and "avx2" in x and x.endswith(".zip")),
                                                        "sd_win_vulkan": lambda x: "bin-win-vulkan-x64" in x})
    out["sd_tag"], out["sd_win"], out["sd_win_vulkan"] = tag, n["sd_win"], n["sd_win_vulkan"]
    tag, n = _derniere("xinntao/Real-ESRGAN-ncnn-vulkan", {"esrgan_win": lambda x: x.endswith("windows.zip"), "esrgan_linux": lambda x: x.endswith("ubuntu.zip")})
    out["esrgan_tag"], out["esrgan_win"], out["esrgan_linux"] = tag, n["esrgan_win"], n["esrgan_linux"]
    tag, n = _derniere("nihui/rife-ncnn-vulkan", {"rife_win": lambda x: x.endswith("windows.zip"), "rife_linux": lambda x: x.endswith("ubuntu.zip")})
    out["rife_tag"], out["rife_win"], out["rife_linux"] = tag, n["rife_win"], n["rife_linux"]
    try:
        out["ace_ref"] = gh("repos/ServeurpersoCom/acestep.cpp/commits?per_page=1")[0]["sha"][:12]
    except Exception as e:      # noqa: BLE001
        print(f"::warning::acestep.cpp : {e}")
        out["ace_ref"] = "master"
    for k, v in out.items():
        print(f"{k}={v}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            for k, v in out.items():
                f.write(f"{k}={v}\n")
    return out


def _choisir(fichiers, voeu):
    if isinstance(voeu, list):
        return next((f for f in voeu if f in fichiers), None)
    if voeu.startswith("gguf:"):
        ggufs = [f for f in fichiers if f.endswith(".gguf")]
        for q in voeu[5:].split(","):
            for f in ggufs:
                if q in f:
                    return f
        return ggufs[0] if ggufs else None
    return None


def modeles(sortie):
    cat = {}
    caches = {}
    for cle, (nom, genre, parts, opts) in MODELES.items():
        liste, ok = [], True
        for role, depot, voeu in parts:
            try:
                fichiers = caches.get(depot) or _hf_fichiers(depot)
                caches[depot] = fichiers
            except Exception as e:      # noqa: BLE001
                print(f"::warning title={cle}::{depot} indisponible ({e})")
                ok = False
                break
            f = _choisir(fichiers, voeu)
            if not f:
                print(f"::warning title={cle}::{depot} : aucun fichier parmi {voeu} ; vus : {', '.join(list(fichiers)[:15])}")
                ok = False
                break
            liste.append({"nom": os.path.basename(f), "role": role, "url": f"https://huggingface.co/{depot}/resolve/main/{f}",
                          "taille": fichiers[f]["taille"], "sha256": fichiers[f]["sha256"]})
        if not ok:
            continue
        e = {"genre": genre, "nom": nom, "source": ", ".join(sorted({d for _r, d, _v in parts})), "fichiers": liste,
             "taille": sum(x["taille"] for x in liste), "essai": False}
        e.update({k: v for k, v in opts.items()})
        if genre in ("image", "video"):
            e["moteur"], e["moteur_gpu"] = "image", "image_gpu"
        elif genre == "musique":
            e["moteur"], e["moteur_gpu"] = "musique", "musique_gpu"
        cat[cle] = e
        print(f"::notice title={cle}::{', '.join(x['nom'] for x in liste)} ({e['taille'] / 1e9:.2f} Go)")
    # dessin animé : modèles ONNX publiés par l'auteur d'AnimeGANv3 (usage non commercial, voir sa licence)
    try:
        assets = []
        for r in gh("repos/TachibanaYoshino/AnimeGANv3/releases?per_page=30"):
            assets += [(a["name"], a["browser_download_url"], a["size"]) for a in r.get("assets", []) if a["name"].lower().endswith(".onnx")]
        for cle, (nom, motif) in ANIMEGAN.items():
            a = next((x for x in assets if motif.lower() in x[0].lower()), None)
            if not a:
                print(f"::warning title={cle}::aucun ONNX « {motif} » ; vus : {', '.join(x[0] for x in assets[:12])}")
                continue
            cat[cle] = {"genre": "anime", "nom": nom, "source": "AnimeGANv3 (usage non commercial)", "qualite": 4, "essai": False,
                        "note": "Image par image, sur la carte graphique ou le processeur ; réservé à un usage non commercial.",
                        "fichiers": [{"nom": a[0], "role": "modele", "url": a[1], "taille": a[2], "sha256": ""}], "taille": a[2]}
            print(f"::notice title={cle}::{a[0]} ({a[2] / 1e6:.0f} Mo)")
    except Exception as e:      # noqa: BLE001
        print(f"::warning title=AnimeGANv3::{e}")
    for cle, (nom, genre, moteur) in MOTEURS_SEULS.items():
        cat[cle] = {"genre": genre, "nom": nom, "source": "ncnn (MIT)", "qualite": 4, "essai": False, "moteur": moteur,
                    "note": "Le programme contient ses modèles ; utilise la carte graphique (Vulkan), y compris une carte intégrée.",
                    "fichiers": [], "taille": 0}
    with open(sortie, "w", encoding="utf-8") as fo:
        json.dump(cat, fo, ensure_ascii=False, indent=1)
    return 0


def assembler(dossier):
    v = json.load(open(os.path.join(dossier, "versions-creatifs.json")))
    man = {"format": 1, "date": time.strftime("%Y-%m-%d"), "depot": "PhilouElChapo/PhilCut", "tag": "moteurs-ia",
           "moteurs": {"image": {"nom": "stable-diffusion.cpp (processeur)", "version": v.get("sd_tag", ""), "licence": "MIT"},
                       "image_gpu": {"nom": "stable-diffusion.cpp Vulkan (carte graphique)", "version": v.get("sd_tag", ""), "licence": "MIT"},
                       "musique": {"nom": "acestep.cpp (processeur)", "version": v.get("ace_ref", ""), "licence": "MIT"},
                       "musique_gpu": {"nom": "acestep.cpp Vulkan (carte graphique)", "version": v.get("ace_ref", ""), "licence": "MIT"},
                       "upscale": {"nom": "Real-ESRGAN ncnn Vulkan", "version": v.get("esrgan_tag", ""), "licence": "MIT"},
                       "interpolation": {"nom": "RIFE ncnn Vulkan", "version": v.get("rife_tag", ""), "licence": "MIT"}},
           "modeles": json.load(open(os.path.join(dossier, "modeles-creatifs.json"), encoding="utf-8"))}
    prefixes = (("image_gpu", "philcut-sd-vulkan"), ("image", "philcut-sd"), ("musique_gpu", "philcut-ace-vulkan"), ("musique", "philcut-ace"),
                ("upscale", "philcut-esrgan"), ("interpolation", "philcut-rife"))
    vus = set()
    for genre, prefixe in prefixes:
        for systeme in ("windows", "linux"):
            for f in sorted(os.listdir(dossier)):
                if f.startswith(f"{prefixe}-{systeme}") and f not in vus:
                    vus.add(f)
                    p = os.path.join(dossier, f)
                    man["moteurs"][genre][systeme] = {"fichier": f, "taille": os.path.getsize(p), "sha256": empreinte(p),
                                                      "url": f"https://github.com/PhilouElChapo/PhilCut/releases/download/moteurs-ia/{f}"}
    with open(os.path.join(dossier, "moteurs-creatifs.json"), "w", encoding="utf-8") as fo:
        json.dump(man, fo, ensure_ascii=False, indent=1)
    for g, m in man["moteurs"].items():
        for s in ("windows", "linux"):
            print(f"::notice title={g} {s}::{m[s]['fichier']} ({m[s]['taille'] / 1e6:.0f} Mo)" if s in m else f"::warning::{g} {s} absent")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "versions":
        r = versions()
        if len(sys.argv) > 2:
            json.dump(r, open(sys.argv[2], "w"))
        sys.exit(0)
    if cmd == "modeles":
        sys.exit(modeles(sys.argv[2]))
    if cmd == "assembler":
        sys.exit(assembler(sys.argv[2]))
    print(__doc__)
    sys.exit(2)
