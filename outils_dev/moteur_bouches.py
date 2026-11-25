"""Moteur « bouches » (1.3.0) : Rhubarb Lip Sync (Daniel S. Wolf, licence MIT), qui lit une voix et donne la forme de
bouche à chaque instant, pour les personnages animés (pantins). Les archives officielles sont reprises telles quelles.

  python outils_dev/moteur_bouches.py catalogue dist version   -> moteur « bouches » et modèle « bouches_rhubarb »
                                                                  ajoutés à dist/moteurs-creatifs.json
  python outils_dev/moteur_bouches.py essai rhubarb voix.wav    -> la synchro donne bien plusieurs formes de bouche
"""
import json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RELEASE = "https://github.com/PhilouElChapo/PhilCut/releases/download/moteurs-ia/"
NOMS = {"windows": "philcut-rhubarb-windows-x64.zip", "linux": "philcut-rhubarb-linux-x64.zip"}


def catalogue(dossier, version):
    from moteurs_ia import empreinte
    p = os.path.join(dossier, "moteurs-creatifs.json")
    man = json.load(open(p, encoding="utf-8"))
    m = man["moteurs"].setdefault("bouches", {})
    m.update({"nom": "Rhubarb Lip Sync (bouches des personnages animés)", "version": version, "licence": "MIT",
              "source": "https://github.com/DanielSWolf/rhubarb-lip-sync"})
    for systeme, nom in NOMS.items():
        f = os.path.join(dossier, nom)
        if not os.path.exists(f):
            print(f"::error::archive {nom} absente")
            return 1
        m[systeme] = {"fichier": nom, "url": RELEASE + nom, "taille": os.path.getsize(f), "sha256": empreinte(f)}
    man.setdefault("modeles", {})["bouches_rhubarb"] = {
        "genre": "bouches", "nom": "Bouches des personnages animés (Rhubarb Lip Sync)", "moteur": "bouches", "qualite": 4,
        "memoire_go": 1, "essai": False, "fichiers": [], "taille": 0, "version": version,
        "source": "DanielSWolf/rhubarb-lip-sync (MIT)",
        "note": "Lit la voix off et donne la forme de la bouche à chaque instant ; reconnaissance phonétique, toutes langues."}
    man["date"] = time.strftime("%Y-%m-%d")
    json.dump(man, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(m, ensure_ascii=False, indent=1))
    return 0


def essai(exe, wav):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("PHILCUT_LANGUE", "fr")
    from app.pantin import lire_rhubarb
    r = subprocess.run([exe, "-r", "phonetic", "-f", "tsv", "--extendedShapes", "GHX", wav], capture_output=True)
    formes = lire_rhubarb(r.stdout.decode("utf-8", "replace"))
    print("formes :", formes[:30])
    if r.returncode != 0 or len({f for _t, f in formes}) < 3:
        print(f"::error title=Essai Rhubarb::{r.stderr.decode('utf-8', 'replace')[-400:]}")
        return 1
    print(f"::notice title=Essai Rhubarb::{len(formes)} changements de bouche, {len({f for _t, f in formes})} formes")
    return 0


if __name__ == "__main__":
    if sys.argv[1] == "catalogue":
        sys.exit(catalogue(sys.argv[2], sys.argv[3]))
    if sys.argv[1] == "essai":
        sys.exit(essai(sys.argv[2], sys.argv[3]))
    print(__doc__)
    sys.exit(2)
