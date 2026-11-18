"""Moteur « lèvres sur ce poste » (0.9.92) : LatentSync 1.5 dans un Python portable (workflow « Moteur levres »).

  python outils_dev/moteur_levres.py decouper archive.zip [taille_Mo]   -> archive.zip.001, .002… (assets GitHub < 2 Go)
  python outils_dev/moteur_levres.py catalogue dist                    -> moteur « levres » et modèle « levres_local »
                                                                          ajoutés à dist/moteurs-creatifs.json

Modèles (téléchargés par PhilCut, jamais pendant le calcul) :
- ByteDance/LatentSync-1.5 : latentsync_unet.pt, whisper/tiny.pt (Apache 2.0) ;
- stabilityai/sd-vae-ft-mse : config.json, diffusion_pytorch_model.safetensors (MIT) ;
- InsightFace buffalo_l (repérage du visage ; modèles réservés à un usage non commercial, voir leur licence).
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moteurs_ia import _hf_fichiers, empreinte   # noqa: E402

COMMIT = "7b380d6"            # dernier commit de LatentSync avant 1.6 (256 px, 8 Go de carte graphique)
VERSION = f"LatentSync 1.5 ({COMMIT})"
BUFFALO = "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
RELEASE = "https://github.com/PhilouElChapo/PhilCut/releases/download/moteurs-ia/"
FICHIERS = [("unet", "ByteDance/LatentSync-1.5", "latentsync_unet.pt"),
            ("whisper", "ByteDance/LatentSync-1.5", "whisper/tiny.pt"),
            ("vae_config", "stabilityai/sd-vae-ft-mse", "config.json"),
            ("vae", "stabilityai/sd-vae-ft-mse", "diffusion_pytorch_model.safetensors")]


def decouper(archive, taille_mo=1900):
    t = int(taille_mo) * 1024 * 1024
    n = 0
    with open(archive, "rb") as f:
        while True:
            bloc = f.read(t)
            if not bloc:
                break
            n += 1
            with open(f"{archive}.{n:03d}", "wb") as o:
                o.write(bloc)
    print(f"::notice::{archive} : {n} partie(s)")
    return 0


def catalogue(dossier, buffalo=None):
    p = os.path.join(dossier, "moteurs-creatifs.json")
    man = json.load(open(p, encoding="utf-8"))
    nom = "philcut-levres-windows-x64.zip"
    parties = sorted(f for f in os.listdir(dossier) if f.startswith(nom + "."))
    if not parties:
        print("::error::aucune partie du moteur")
        return 1
    m = man["moteurs"].setdefault("levres", {})
    m.update({"nom": "LatentSync 1.5 (Python portable, PyTorch CUDA)", "version": VERSION, "licence": "Apache 2.0"})
    m["windows"] = {"fichier": nom, "taille": sum(os.path.getsize(os.path.join(dossier, f)) for f in parties),
                    "parties": [{"fichier": f, "url": RELEASE + f, "taille": os.path.getsize(os.path.join(dossier, f)),
                                 "sha256": empreinte(os.path.join(dossier, f))} for f in parties]}
    liste = []
    caches = {}
    for role, depot, f in FICHIERS:
        fichiers = caches.get(depot) or _hf_fichiers(depot)
        caches[depot] = fichiers
        if f not in fichiers:
            print(f"::error::{depot} : {f} absent")
            return 1
        liste.append({"nom": os.path.basename(f), "role": role, "url": f"https://huggingface.co/{depot}/resolve/main/{f}",
                      "taille": fichiers[f]["taille"], "sha256": fichiers[f]["sha256"]})
    if buffalo and os.path.exists(buffalo):
        liste.append({"nom": "buffalo_l.zip", "role": "visages", "url": BUFFALO, "taille": os.path.getsize(buffalo),
                      "sha256": empreinte(buffalo)})
    else:
        print("::error::buffalo_l.zip absent")
        return 1
    man.setdefault("modeles", {})["levres_local"] = {
        "genre": "levres", "nom": "Lèvres sur ce poste (LatentSync 1.5, carte NVIDIA de 8 Go)", "moteur": "levres",
        "source": "ByteDance/LatentSync-1.5, stabilityai/sd-vae-ft-mse, InsightFace buffalo_l", "qualite": 4, "memoire_go": 8,
        "carte": "nvidia", "essai": False, "fichiers": liste, "taille": sum(x["taille"] for x in liste),
        "note": "Refait la bouche d'un plan sur votre son, gratuitement, sur une carte NVIDIA de 8 Go (Apache 2.0 ; le repérage "
                "du visage, InsightFace, est réservé à un usage non commercial). Windows seulement pour l'instant."}
    man["date"] = time.strftime("%Y-%m-%d")
    json.dump(man, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(man["moteurs"]["levres"], ensure_ascii=False, indent=1))
    print(json.dumps(man["modeles"]["levres_local"], ensure_ascii=False, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "decouper":
        sys.exit(decouper(sys.argv[2], *(sys.argv[3:4])))
    if cmd == "catalogue":
        sys.exit(catalogue(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    print(__doc__)
    sys.exit(2)
