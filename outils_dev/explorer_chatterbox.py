"""Exploration (0.9.57) du dépôt onnx-community/chatterbox-multilingual-ONNX : fichiers et tailles, entrées/sorties des
modèles ONNX, carte du modèle (README) et fichiers du tokenizer, pour écrire « Continuer avec ma voix »."""
import json, os, sys
from huggingface_hub import HfApi, hf_hub_download

DEPOT = "onnx-community/chatterbox-multilingual-ONNX"
d = sys.argv[1]
os.makedirs(d, exist_ok=True)
info = HfApi().model_info(DEPOT, files_metadata=True)
print("licence :", (info.card_data or {}).get("license") if info.card_data else None)
for s in info.siblings:
    print(f"{s.rfilename:70s} {(s.size or 0) / 1e6:10.1f} Mo")
for f in ("README.md", "tokenizer.json", "tokenizer_config.json", "config.json", "generation_config.json",
          "special_tokens_map.json", "preprocessor_config.json"):
    try:
        p = hf_hub_download(DEPOT, f, local_dir=d)
        print("téléchargé", f, os.path.getsize(p))
    except Exception as e:
        print("absent", f, e.__class__.__name__)
import onnxruntime as ort
petits = [s.rfilename for s in info.siblings if s.rfilename.endswith(".onnx") and "/" in s.rfilename]
for f in sorted(petits):
    # on ne charge que les variantes « q4 » ou les fichiers de base sans gros poids externes, pour lire les entrées/sorties
    try:
        p = hf_hub_download(DEPOT, f, local_dir=d)
        donnees = f + "_data"
        if any(s.rfilename == donnees for s in info.siblings):
            hf_hub_download(DEPOT, donnees, local_dir=d)
        se = ort.InferenceSession(p, providers=["CPUExecutionProvider"])
        print("\n==", f)
        for i in se.get_inputs()[:8]:
            print("  entrée", i.name, i.shape, i.type)
        if len(se.get_inputs()) > 8:
            print("  …", len(se.get_inputs()), "entrées")
        for o in se.get_outputs()[:8]:
            print("  sortie", o.name, o.shape, o.type)
        if len(se.get_outputs()) > 8:
            print("  …", len(se.get_outputs()), "sorties")
        del se
        os.remove(p)
        if os.path.exists(os.path.join(d, donnees)):
            os.remove(os.path.join(d, donnees))
    except Exception as e:
        print("!!", f, e)
