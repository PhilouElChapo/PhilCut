"""Essai de la clef Gemini et de Veo, lance par GitHub Actions (onglet Actions › « Tester la clef Gemini et Veo »).

La clef vient du secret GEMINI_API_KEY du depot : elle n'est jamais affichee.
  essai=cle    : gratuit. Verifie la clef, liste les modeles Veo ouverts a ce compte, fait repondre Gemini en une phrase.
  essai=video  : PAYANT. Genere un plan court avec le code de PhilCut (app/fabrique.generer_veo) ; la video est
                 jointe au resultat de l'action (rubrique « Artifacts »).
"""
import json, os, sys, time, urllib.error, urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
BASE = "https://generativelanguage.googleapis.com/v1beta"


def lire(url, clef, corps=None):
    req = urllib.request.Request(url, data=json.dumps(corps).encode() if corps is not None else None,
                                 headers={"x-goog-api-key": clef, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def erreur_google(e):
    try:
        return json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")[:300]
    except Exception:  # noqa: BLE001
        return str(e)


def main():
    clef = "".join(os.environ.get("GEMINI_API_KEY", "").split())
    essai = os.environ.get("ESSAI", "cle")
    if not clef:
        print("::error title=Clef absente::Ajoutez le secret GEMINI_API_KEY dans Settings › Secrets and variables › Actions.")
        return 1
    print(f"Clef lue : {len(clef)} caracteres, commence par {clef[:3]}…")

    # 1. la clef ouvre-t-elle l'API ?
    try:
        modeles, page = [], ""
        while True:
            r = lire(f"{BASE}/models?pageSize=200" + (f"&pageToken={page}" if page else ""), clef)
            modeles += r.get("models", [])
            page = r.get("nextPageToken")
            if not page:
                break
    except urllib.error.HTTPError as e:
        print(f"::error title=Clef refusee::HTTP {e.code} : {erreur_google(e)}")
        return 1
    noms = [m["name"].split("/")[-1] for m in modeles]
    veo = sorted(n for n in noms if n.startswith("veo"))
    gem = [n for n in noms if n.startswith("gemini")]
    print(f"::notice title=Clef valide::{len(noms)} modeles ouverts, dont {len(gem)} Gemini et {len(veo)} Veo")
    print("Modeles Veo : " + (", ".join(veo) or "aucun"))

    # 2. Gemini repond-il ? (quelques centimes de centime au plus)
    texte_ok = False
    for m in ("gemini-2.5-flash", "gemini-flash-latest") + tuple(gem[:3]):
        if m not in noms:
            continue
        try:
            r = lire(f"{BASE}/models/{m}:generateContent", clef,
                     {"contents": [{"parts": [{"text": "Réponds en une phrase courte, en français : quel est ton nom de modèle ?"}]}]})
            rep = r["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"::notice title=Gemini repond ({m})::{rep[:200]}")
            texte_ok = True
            break
        except urllib.error.HTTPError as e:
            print(f"{m} : HTTP {e.code} : {erreur_google(e)}")
    if not texte_ok:
        print("::warning title=Gemini::aucune reponse texte")

    if essai != "video":
        print("Essai gratuit termine. Pour un vrai plan Veo, relancez avec essai = video (payant).")
        return 0 if texte_ok else 1

    # 3. Veo, avec le code de PhilCut
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from app import fabrique
    modele = os.environ.get("MODELE_VEO") or "veo-3.1-lite-generate-preview"
    if veo and modele not in veo:
        lite = [n for n in veo if "lite" in n] or [n for n in veo if "fast" in n] or veo
        print(f"{modele} n'est pas ouvert a ce compte : essai avec {lite[0]}")
        modele = lite[0]
    duree = int(os.environ.get("DUREE", "4"))
    print(f"Veo : {modele}, {duree} s, 16:9 — prix indicatif {fabrique.prix_veo(modele, duree)} $")
    consigne = ("Cinematic aerial shot: a small single-engine plane takes off at sunrise above the green hills "
                "of Provence, warm golden light, gentle camera follow, no text.")
    os.makedirs("essai_veo", exist_ok=True)
    sortie = os.path.join("essai_veo", "essai_veo.mp4")
    debut = time.time()
    try:
        fabrique.generer_veo({"clef_gemini": clef}, consigne, sortie, modele=modele, duree=duree, format_="16:9",
                             progression=lambda f: print(f"  … {int(f * 100)} %", flush=True))
    except urllib.error.HTTPError as e:
        print(f"::error title=Veo refuse::HTTP {e.code} : {erreur_google(e)}")
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"::error title=Veo::{str(e)[:300]}")
        return 1
    taille = os.path.getsize(sortie) / 1e6
    print(f"::notice title=Veo OK::{modele} : {taille:.1f} Mo en {int(time.time() - debut)} s (video jointe : Artifacts › essai-veo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
