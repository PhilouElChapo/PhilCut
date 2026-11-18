"""Images d'exemple de la bibliothèque toute faite (0.9.89) : une image par entrée qui n'en a pas encore, dessinée par Gemini
(clef du secret GEMINI_API_KEY, payant : environ 0,04 $ l'image), réduite en JPEG 512 px dans catalogue/exemples/<id>.jpg.
Lancé seulement à la main (workflow « Images d'exemple du catalogue »), après accord sur le prix.

    python outils_dev/exemples_prompts.py [rubriques séparées par des virgules] [--compter]
"""
import base64, io, json, os, sys, time, urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELE = "gemini-2.5-flash-image"
CADRE = {
    "tenue": "Fashion catalogue photo of ONE outfit worn by an invented model, full body, plain light grey studio background, "
             "even light, photorealistic, no text, no logo: ",
    "piece": "Product photo of ONE clothing item or accessory, on a plain light grey background, even studio light, photorealistic, "
             "no person, no text, no logo: ",
    "lieu": "Photorealistic wide view of a place, natural light, no people, no text, no logo: ",
    "objet": "Photorealistic three-quarter view of ONE vehicle, clean setting, no people, no text, no logo, no brand: ",
    "personnage": "Photorealistic portrait, waist up, of an INVENTED person (not a real or famous person), neutral background, soft "
                  "light, no text: ",
}


def dessiner(cle, consigne):
    corps = {"contents": [{"parts": [{"text": consigne}]}], "generationConfig": {"responseModalities": ["IMAGE"]}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODELE}:generateContent",
                                 data=json.dumps(corps).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": cle})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    for p in d["candidates"][0]["content"]["parts"]:
        if p.get("inlineData", {}).get("data"):
            return base64.b64decode(p["inlineData"]["data"])
    raise RuntimeError("pas d'image")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    voulues = set(args[0].split(",")) if args and args[0] else None
    cat = json.load(open(os.path.join(RACINE, "catalogue", "prompts.json"), encoding="utf-8"))
    genres = {k: v["genre"] for k, v in cat["rubriques"].items()}
    d = os.path.join(RACINE, "catalogue", "exemples")
    os.makedirs(d, exist_ok=True)
    a_faire = [e for e in cat["entrees"] if (not voulues or e["rubrique"] in voulues) and e["rubrique"] != "matiere"
               and not os.path.exists(os.path.join(d, e["id"] + ".jpg"))]
    print(f"{len(a_faire)} image(s) à faire, environ {len(a_faire) * 0.04:.2f} $")
    if "--compter" in sys.argv:
        return
    cle = os.environ.get("GEMINI_API_KEY", "")
    if not cle:
        sys.exit("GEMINI_API_KEY manquant")
    from PIL import Image
    ratees = 0
    for e in a_faire:
        try:
            png = dessiner(cle, CADRE[genres[e["rubrique"]]] + e["en"])
            im = Image.open(io.BytesIO(png)).convert("RGB")
            im.thumbnail((512, 512))
            im.save(os.path.join(d, e["id"] + ".jpg"), quality=82)
            print("ok", e["id"], flush=True)
        except Exception as err:      # noqa: BLE001
            ratees += 1
            print("::warning::" + e["id"] + " : " + str(err)[:200], flush=True)
        time.sleep(1)
    print(f"faites : {len(a_faire) - ratees}, ratées : {ratees}")


if __name__ == "__main__":
    main()
