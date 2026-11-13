"""Exploration (0.9.57) du dépôt onnx-community/chatterbox-multilingual-ONNX : carte du modèle (code d'exemple) et
configuration du tokenizer, imprimées dans le journal (les artefacts ne sont pas lisibles depuis l'atelier)."""
import os, sys
from huggingface_hub import hf_hub_download

DEPOT = "onnx-community/chatterbox-multilingual-ONNX"
d = sys.argv[1]
os.makedirs(d, exist_ok=True)
for f in ("README.md", "tokenizer_config.json", "generation_config.json"):
    p = hf_hub_download(DEPOT, f, local_dir=d)
    print(f"\n######## {f}")
    for i, ligne in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
        print(f"{i:4d}| {ligne}")
import json
tok = json.load(open(hf_hub_download(DEPOT, "tokenizer.json", local_dir=d), encoding="utf-8"))
print("\n######## tokenizer.json")
print("modèle :", tok["model"]["type"], "normalizer :", json.dumps(tok.get("normalizer"))[:300])
print("pre_tokenizer :", json.dumps(tok.get("pre_tokenizer"))[:300])
print("added_tokens :", [(a["id"], a["content"]) for a in tok.get("added_tokens", [])][:60])
voc = tok["model"]["vocab"]
print("taille vocab :", len(voc), "exemples :", list(voc.items())[:40])
print("[fr] :", voc.get("[fr]"), "[START] :", voc.get("[START]"), "[STOP] :", voc.get("[STOP]"), "[SPACE] :", voc.get("[SPACE]"))
print("fusions :", len(tok["model"].get("merges", [])))
