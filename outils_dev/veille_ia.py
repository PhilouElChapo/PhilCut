"""Veille hebdomadaire des IA (0.9.85), lancée par .github/workflows/veille_ia.yml.

  python outils_dev/veille_ia.py modeles dist      relit Hugging Face pour chaque modèle des catalogues (dist/moteurs-ia.json,
                                                  dist/moteurs-creatifs.json) ; un fichier changé (empreinte, taille) met
                                                  à jour l'entrée (champ « version » = date du relevé) ; dist/changes.json
                                                  liste les clefs changées
  python outils_dev/veille_ia.py essai dist       essai réel des modèles changés (installés avec le code de PhilCut, puis
                                                  essai_ia) ; sortie non nulle si l'un rate : rien n'est alors publié
  python outils_dev/veille_ia.py cloud            relit la page de chaque service cloud (catalogue_ia) : adresse
                                                  disparue → signalée ; prix relu → corrigé dans catalogue/ia.json

Rien n'est retiré automatiquement : un service introuvable est signalé (« a_verifier ») ; le retrait et le remplaçant se
décident à la main dans catalogue/ia.json."""
import json, os, re, sys, time, urllib.error, urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
UA = {"User-Agent": "PhilCut-veille"}
HF = re.compile(r"^https://huggingface\.co/([^/]+/[^/]+)/resolve/([^/]+)/(.+)$")


def note(titre, texte):
    print(f"::notice title={titre}::{texte}", flush=True)


def alerte(texte):
    print(f"::warning::{texte}", flush=True)


def lire(url, delai=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=delai) as r:
        return r.read().decode("utf-8", "replace")


def _hf(depot, cache):
    if depot not in cache:
        d = json.loads(lire(f"https://huggingface.co/api/models/{depot}?blobs=true"))
        out = {}
        for s in d.get("siblings") or []:
            lfs = s.get("lfs") or {}
            out[s["rfilename"]] = {"taille": int(s.get("size") or lfs.get("size") or 0), "sha256": lfs.get("sha256") or ""}
        cache[depot] = out
    return cache[depot]


def relever(man, cache, jour):
    """Met à jour en place les fichiers Hugging Face des modèles du catalogue. Renvoie les clefs changées."""
    changes = []
    for cle, m in (man.get("modeles") or {}).items():
        change = False
        for f in m.get("fichiers") or []:
            r = HF.match(f.get("url", ""))
            if not r:
                continue
            depot, _branche, chemin = r.groups()
            try:
                infos = _hf(depot, cache).get(chemin)
            except Exception as e:      # noqa: BLE001
                alerte(f"{cle} : {depot} illisible ({e})")
                continue
            if infos is None:
                alerte(f"{cle} : {chemin} n'est plus sur {depot} (à remplacer à la main)")
                continue
            if infos["sha256"] and f.get("sha256") and infos["sha256"] != f["sha256"] or \
                    infos["taille"] and f.get("taille") and infos["taille"] != f["taille"]:
                note("Modele change", f"{cle} : {chemin}")
                f["sha256"], f["taille"] = infos["sha256"] or f.get("sha256", ""), infos["taille"] or f.get("taille", 0)
                change = True
        if change:
            m["taille"] = sum(f.get("taille", 0) for f in m.get("fichiers") or [])
            m["version"] = jour
            changes.append(cle)
    return changes


def cmd_modeles(dist):
    cache, jour, changes = {}, time.strftime("%Y-%m-%d"), {}
    for nom in ("moteurs-ia.json", "moteurs-creatifs.json"):
        p = os.path.join(dist, nom)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            man = json.load(f)
        c = relever(man, cache, jour)
        if c:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(man, f, ensure_ascii=False, indent=1)
            changes[nom] = c
    with open(os.path.join(dist, "changes.json"), "w", encoding="utf-8") as f:
        json.dump(changes, f)
    if not changes:
        note("Veille IA", "modeles a jour")
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write("change=" + ("oui" if changes else "non") + "\n")


def cmd_essai(dist, limite=3e9):
    os.environ["PHILCUT_IA_MANIFESTE"] = os.path.join(dist, "moteurs-ia.json")
    if os.path.exists(os.path.join(dist, "moteurs-creatifs.json")):
        os.environ["PHILCUT_IA_MANIFESTE2"] = os.path.join(dist, "moteurs-creatifs.json")
    os.environ.setdefault("PHILCUT_IA_DOSSIER", os.path.join(dist, "essai"))
    from app import essai_ia as EI, packs_ia as P
    with open(os.path.join(dist, "changes.json"), encoding="utf-8") as f:
        changes = [c for liste in json.load(f).values() for c in liste]
    rates = []
    for cle in changes:
        m = P.modeles(avec_essai=True).get(cle) or {}
        if m.get("taille", 0) > limite:
            note("Essai IA", f"{cle} : trop gros pour l'essai ({m['taille'] / 1e9:.1f} Go), empreintes verifiees au telechargement")
            continue
        try:
            P.installer(cle)        # vérifie taille et empreinte de chaque fichier
            if m.get("genre") in EI.ESSAIS:
                r = EI.tester(m["genre"], {"ia_locale_modeles": {m["genre"]: cle}, "ia_poste_leger": False})
                if not r.get("ok"):
                    raise RuntimeError(r.get("message") or "essai rate")
            note("Essai IA", f"{cle} : ok")
        except Exception as e:      # noqa: BLE001
            alerte(f"{cle} : essai rate ({e})")
            rates.append(cle)
        finally:
            try:
                P.supprimer(cle)
            except Exception:       # noqa: BLE001
                pass
    if rates:
        sys.exit(1)


_N = r"\$\s*\**\s*([0-9]+(?:\.[0-9]+)?)\s*\**\s*"
PRIX = (("minute", re.compile(_N + r"(?:per|/|a)\s*minute", re.I)),
        ("16", re.compile(_N + r"(?:per|/|for every)\s*16\s*frames", re.I)),
        ("s", re.compile(_N + r"(?:per|/|a)\s*(?:second|sec)\b", re.I)))


def section_prix(page):
    """Le passage « ## Pricing » de la page llms.txt de fal.ai (toute la page s'il manque)."""
    r = re.search(r"^##\s*Pricing\s*$(.*?)(?=^##\s|\Z)", page, re.M | re.S)
    return r.group(1) if r else page


def cmd_cloud():
    from app import catalogue_ia as CI
    chemin = os.path.join(RACINE, "catalogue", "ia.json")
    with open(chemin, encoding="utf-8") as f:
        cat = json.load(f)
    services = cat.setdefault("services", {})
    change = False
    for role in sorted(CI.SERVICES):
        s = CI.service(role)
        try:
            page = section_prix(lire(f"https://fal.ai/models/{s['point']}/llms.txt", 30))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                alerte(f"{role} : {s['point']} introuvable sur fal.ai (a remplacer a la main dans catalogue/ia.json)")
                if not services.get(role, {}).get("a_verifier"):
                    services.setdefault(role, {})["a_verifier"] = time.strftime("%Y-%m-%d")
                    change = True
            continue
        except Exception as e:      # noqa: BLE001
            alerte(f"{role} : page illisible ({e})")
            continue
        if services.get(role, {}).pop("a_verifier", None):
            change = True
        prix = s.get("prix") or {}
        if "fixe" in prix:          # prix en deux parties : relu à la main
            continue
        for champ, motif in PRIX:
            if champ in prix:
                vus = {float(x) for x in motif.findall(page)}
                if len(vus) > 1:            # plusieurs prix (résolutions, options) : relu à la main
                    note("Prix a relire", f"{role} : {sorted(vus)} $ ({champ})")
                elif vus and abs(vus.pop() - float(prix[champ])) > 1e-9:
                    neuf = float(motif.search(page).group(1))
                    note("Prix change", f"{role} : {prix[champ]} -> {neuf} $ ({champ})")
                    services.setdefault(role, {}).setdefault("prix", {})[champ] = neuf
                    change = True
                break
    for role in [r for r, v in services.items() if v == {}]:
        services.pop(role)
    if change:
        cat["maj"] = time.strftime("%Y-%m-%d")
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(cat, f, ensure_ascii=False, indent=1)
            f.write("\n")
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write("cloud=" + ("oui" if change else "non") + "\n")


if __name__ == "__main__":
    quoi = sys.argv[1] if len(sys.argv) > 1 else ""
    if quoi == "modeles":
        cmd_modeles(sys.argv[2])
    elif quoi == "essai":
        cmd_essai(sys.argv[2])
    elif quoi == "cloud":
        cmd_cloud()
    else:
        print(__doc__)
        sys.exit(2)
