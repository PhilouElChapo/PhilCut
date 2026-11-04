"""Préparation des moteurs d'IA locale de PhilCut (lancé par GitHub Actions, workflow « Moteurs IA locaux »).

  python outils_dev/moteurs_ia.py versions            -> dernières versions de llama.cpp et whisper.cpp + noms des archives officielles
  python outils_dev/moteurs_ia.py modeles sortie.json -> catalogue des modèles (adresse, taille, empreinte) lu sur Hugging Face
  python outils_dev/moteurs_ia.py assembler dossier   -> moteurs-ia.json : moteurs fabriqués + modèles, publié avec les archives

Les moteurs sont les programmes officiels (llama.cpp pour la vision, whisper.cpp pour la voix), repris tels quels
dans une archive PhilCut qui ne garde que le nécessaire. Les modèles restent chez leurs auteurs (Hugging Face,
GitHub) : PhilCut les télécharge directement quand l'utilisateur coche la case.
"""
import hashlib, json, os, sys, time, urllib.request

UA = {"User-Agent": "PhilCut-moteurs-ia"}

# Modèles proposés. Pour chaque emplacement, une liste de candidats : le premier qui existe est retenu.
VISION = {
    "vision_leger": {"nom": "Vision légère", "memoire_go": 4, "qualite": 3,
                     "note": "Pour un mini PC ou un portable : plus lent à réfléchir, idées correctes.",
                     "candidats": ["ggml-org/Qwen3-VL-2B-Instruct-GGUF", "ggml-org/Qwen2.5-VL-3B-Instruct-GGUF", "ggml-org/SmolVLM2-2.2B-Instruct-GGUF"]},
    "vision_standard": {"nom": "Vision standard", "memoire_go": 8, "qualite": 4,
                        "note": "Pour un PC avec 16 Go de mémoire ou une carte graphique : meilleures idées.",
                        "candidats": ["ggml-org/Qwen3-VL-4B-Instruct-GGUF", "ggml-org/gemma-3-4b-it-GGUF", "ggml-org/Qwen2.5-VL-7B-Instruct-GGUF"]},
    "vision_avance": {"nom": "Vision avancée (carte graphique)", "memoire_go": 8, "qualite": 5,
                      "note": "Pour une carte graphique de 8 Go (RTX 3070, 4060…) : le modèle le plus fin, tout tient dans la carte.",
                      "candidats": ["ggml-org/Qwen3-VL-8B-Instruct-GGUF", "ggml-org/Qwen2.5-VL-7B-Instruct-GGUF", "ggml-org/gemma-3-12b-it-GGUF"]},
    "vision_test": {"nom": "Vision (essai)", "memoire_go": 1, "qualite": 1, "cache": True,
                    "note": "Minuscule, seulement pour vérifier que le moteur marche.",
                    "candidats": ["ggml-org/SmolVLM-256M-Instruct-GGUF", "ggml-org/SmolVLM-500M-Instruct-GGUF"]},
}
WHISPER = {
    "whisper_leger": ("Voix légère (base)", "ggml-base.bin", 3),
    "whisper_standard": ("Voix standard (small)", "ggml-small.bin", 4),
    "whisper_precis": ("Voix précise (large v3 turbo)", "ggml-large-v3-turbo-q5_0.bin", 5),
    "whisper_test": ("Voix (essai, tiny)", "ggml-tiny.bin", 1),
}
WHISPER_DEPOTS = ["ggerganov/whisper.cpp", "ggml-org/whisper.cpp"]
PIPER_TAG = "2023.11.14-2"            # dernière version autonome (exécutable) de Piper
VOIX_SYNTHESE = {                       # clef : (nom, chemin dans rhasspy/piper-voices, qualité)
    "voix_fr_femme": ("Voix française, femme (Siwis)", "fr/fr_FR/siwis/medium/fr_FR-siwis-medium", 3),
    "voix_fr_homme": ("Voix française, homme (Tom)", "fr/fr_FR/tom/medium/fr_FR-tom-medium", 3),
    "voix_en_femme": ("English voice, female (Lessac)", "en/en_US/lessac/medium/en_US-lessac-medium", 4),
    "voix_en_homme": ("English voice, male (Alan, UK)", "en/en_GB/alan/medium/en_GB-alan-medium", 3),
    "voix_es": ("Voz española (Davefx)", "es/es_ES/davefx/medium/es_ES-davefx-medium", 3),
    "voix_de": ("Deutsche Stimme (Thorsten)", "de/de_DE/thorsten/medium/de_DE-thorsten-medium", 4),
    "voix_it": ("Voce italiana (Paola)", "it/it_IT/paola/medium/it_IT-paola-medium", 3),
}
DETOURAGE = {
    "detourage_leger": ("Détourage léger (u2netp)", "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx", 2),
    "detourage_precis": ("Détourage précis, spécial personnes (u2net human seg)", "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx", 4),
}


def lire_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def taille_distante(url):
    req = urllib.request.Request(url, headers=UA, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers.get("Content-Length") or 0)


def gh(chemin):
    jeton = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    req = urllib.request.Request("https://api.github.com/" + chemin, headers=dict(UA, **({"Authorization": "Bearer " + jeton} if jeton else {})))
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _derniere(depot, motifs):
    """Release la plus récente (parmi les 30 dernières, préversions comprises) qui contient une archive pour chaque motif.
    motifs : {cle: fonction(nom) -> bool}. Renvoie (tag, {cle: nom})."""
    vus = []
    for r in gh(f"repos/{depot}/releases?per_page=30"):
        if r.get("draft"):
            continue
        noms = [a["name"] for a in r.get("assets", [])]
        vus.append(f"{r['tag_name']}: {', '.join(noms[:12])}")
        trouve = {k: next((n for n in noms if f(n)), "") for k, f in motifs.items()}
        if all(trouve.values()):
            return r["tag_name"], trouve
    print(f"::warning title={depot}::aucune release avec toutes les archives ; vues : " + " | ".join(vus[:6])[:1500])
    return "", {k: "" for k in motifs}


def versions():
    out = {}
    tag, n = _derniere("ggml-org/llama.cpp", {"llama_win": lambda x: "bin-win-cpu-x64" in x and x.endswith(".zip"),
                                              "llama_win_vulkan": lambda x: "bin-win-vulkan-x64" in x and x.endswith(".zip"),
                                              "llama_linux_vulkan": lambda x: "bin-ubuntu-vulkan-x64" in x})
    out["llama_tag"], out["llama_win"] = tag, n["llama_win"]
    out["llama_win_vulkan"], out["llama_linux_vulkan"] = n["llama_win_vulkan"], n["llama_linux_vulkan"]
    tag, n = _derniere("ggml-org/whisper.cpp", {"whisper_win": lambda x: x.endswith(".zip") and "x64" in x and "bin" in x
                                                 and not any(m in x.lower() for m in ("blas", "cublas", "cuda", "vulkan", "arm", "xcframework"))})
    out["whisper_tag"], out["whisper_win"] = tag, n["whisper_win"]
    for k, v in out.items():
        print(f"{k}={v}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            for k, v in out.items():
                f.write(f"{k}={v}\n")
    if not all(out.values()):
        print("::error::archives officielles introuvables")
        sys.exit(1)
    return out


def _hf_fichiers(depot):
    d = lire_json(f"https://huggingface.co/api/models/{depot}?blobs=true")
    out = {}
    for s in d.get("siblings", []):
        lfs = s.get("lfs") or {}
        out[s["rfilename"]] = {"taille": int(s.get("size") or lfs.get("size") or 0), "sha256": lfs.get("sha256") or lfs.get("oid") or ""}
    return out


def _choisir(fichiers, mmproj):
    ggufs = [f for f in fichiers if f.endswith(".gguf") and (("mmproj" in f.lower()) == mmproj)]
    prefs = ["Q8_0", "F16", "f16", "bf16"] if mmproj else ["Q4_K_M", "q4_k_m", "Q4_0", "Q8_0"]
    for p in prefs:
        for f in ggufs:
            if p in f:
                return f
    return ggufs[0] if ggufs else None


def modeles(sortie):
    cat = {}
    for cle, v in VISION.items():
        for depot in v["candidats"]:
            try:
                fichiers = _hf_fichiers(depot)
            except Exception as e:      # noqa: BLE001
                print(f"{cle} : {depot} indisponible ({e})")
                continue
            m, p = _choisir(fichiers, False), _choisir(fichiers, True)
            if not (m and p):
                print(f"{cle} : {depot} sans modèle ou sans projecteur d'image")
                continue
            liste = [{"nom": f, "role": r, "url": f"https://huggingface.co/{depot}/resolve/main/{f}",
                      "taille": fichiers[f]["taille"], "sha256": fichiers[f]["sha256"]} for f, r in ((m, "modele"), (p, "mmproj"))]
            cat[cle] = {"genre": "vision", "nom": v["nom"], "source": depot, "fichiers": liste, "taille": sum(x["taille"] for x in liste),
                        "memoire_go": v["memoire_go"], "qualite": v["qualite"], "note": v["note"], "essai": bool(v.get("cache"))}
            print(f"::notice title={cle}::{depot} — {m} + {p} ({cat[cle]['taille'] / 1e9:.2f} Go)")
            break
        else:
            print(f"::warning title={cle}::aucun candidat disponible")
    for depot in WHISPER_DEPOTS:
        try:
            fichiers = _hf_fichiers(depot)
            break
        except Exception as e:          # noqa: BLE001
            print(f"whisper : {depot} indisponible ({e})")
            fichiers = {}
    for cle, (nom, f, q) in WHISPER.items():
        if f in fichiers:
            cat[cle] = {"genre": "whisper", "nom": nom, "source": depot, "qualite": q, "essai": cle.endswith("_test"),
                        "fichiers": [{"nom": f, "role": "modele", "url": f"https://huggingface.co/{depot}/resolve/main/{f}",
                                      "taille": fichiers[f]["taille"], "sha256": fichiers[f]["sha256"]}], "taille": fichiers[f]["taille"]}
            print(f"::notice title={cle}::{f} ({fichiers[f]['taille'] / 1e6:.0f} Mo)")
        else:
            print(f"::warning title={cle}::{f} introuvable")
    try:
        voix_hf = _hf_fichiers("rhasspy/piper-voices")
    except Exception as e:              # noqa: BLE001
        print(f"::warning title=Voix de synthèse::piper-voices indisponible ({e})")
        voix_hf = {}
    for cle, (nom, chemin, q) in VOIX_SYNTHESE.items():
        f1, f2 = chemin + ".onnx", chemin + ".onnx.json"
        if f1 in voix_hf and f2 in voix_hf:
            fichiers = [{"nom": os.path.basename(f), "role": r, "url": f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{f}",
                         "taille": voix_hf[f]["taille"], "sha256": voix_hf[f]["sha256"]} for f, r in ((f1, "modele"), (f2, "config"))]
            cat[cle] = {"genre": "voix", "nom": nom, "source": "rhasspy/piper-voices", "qualite": q, "essai": False, "langue": chemin[:2],
                        "fichiers": fichiers, "taille": sum(x["taille"] for x in fichiers)}
            print(f"::notice title={cle}::{os.path.basename(f1)} ({cat[cle]['taille'] / 1e6:.0f} Mo)")
        else:
            print(f"::warning title={cle}::{chemin} introuvable")
    for cle, (nom, url, q) in DETOURAGE.items():
        try:
            t = taille_distante(url)
        except Exception as e:          # noqa: BLE001
            print(f"::warning title={cle}::{url} : {e}")
            continue
        cat[cle] = {"genre": "detourage", "nom": nom, "source": "rembg (Apache 2.0)", "qualite": q, "essai": False,
                    "fichiers": [{"nom": os.path.basename(url), "role": "modele", "url": url, "taille": t, "sha256": ""}], "taille": t}
        print(f"::notice title={cle}::{os.path.basename(url)} ({t / 1e6:.0f} Mo)")
    with open(sortie, "w", encoding="utf-8") as fo:
        json.dump(cat, fo, ensure_ascii=False, indent=1)
    if not any(v["genre"] == "vision" and not v["essai"] for v in cat.values()):
        print("::error::aucun modèle de vision disponible")
        return 1
    return 0


def empreinte(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def assembler(dossier):
    """dossier contient les archives fabriquées, modeles.json et versions.json."""
    v = json.load(open(os.path.join(dossier, "versions.json")))
    man = {"format": 1, "date": time.strftime("%Y-%m-%d"), "depot": "PhilouElChapo/PhilCut", "tag": "moteurs-ia",
           "moteurs": {"vision": {"nom": "llama.cpp (llama-server)", "version": v["llama_tag"], "licence": "MIT"},
                       "vision_gpu": {"nom": "llama.cpp Vulkan (carte graphique)", "version": v["llama_tag"], "licence": "MIT"},
                       "whisper": {"nom": "whisper.cpp (whisper-cli)", "version": v["whisper_tag"], "licence": "MIT"},
                       "voix": {"nom": "Piper (voix de synthèse)", "version": PIPER_TAG, "licence": "MIT"}},
           "modeles": json.load(open(os.path.join(dossier, "modeles.json"), encoding="utf-8"))}
    vus = set()
    for genre, prefixe in (("vision_gpu", "philcut-llama-vulkan"), ("vision", "philcut-llama"), ("whisper", "philcut-whisper"), ("voix", "philcut-piper")):
        for systeme in ("windows", "linux"):
            for f in os.listdir(dossier):
                if f.startswith(f"{prefixe}-{systeme}") and f not in vus:
                    vus.add(f)
                    p = os.path.join(dossier, f)
                    man["moteurs"][genre][systeme] = {"fichier": f, "taille": os.path.getsize(p), "sha256": empreinte(p),
                                                      "url": f"https://github.com/PhilouElChapo/PhilCut/releases/download/moteurs-ia/{f}"}
    with open(os.path.join(dossier, "moteurs-ia.json"), "w", encoding="utf-8") as fo:
        json.dump(man, fo, ensure_ascii=False, indent=1)
    for g, m in man["moteurs"].items():
        for s in ("windows", "linux"):
            if s not in m:
                if os.environ.get("PARTIEL") or g in ("vision_gpu", "voix"):     # facultatifs : leur absence ne bloque pas
                    print(f"::warning::moteur {g} {s} absent")
                    continue
                print(f"::error::moteur {g} {s} absent")
                return 1
            print(f"::notice title=Moteur {g} {s}::{m[s]['fichier']} ({m[s]['taille'] / 1e6:.0f} Mo)")
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
