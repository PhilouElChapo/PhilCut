"""Variantes des voix du catalogue « à la manière de » (1.2.1, choix de Philippe du 25/11 : propres à chaque voix).

Pour chaque style de catalogue/styles.json qui décrit une voix, 3 ou 4 variantes justes, choisies d'après sa famille musicale
et les mots de sa description (une voix déjà rauque n'a pas de variante « rauque », un crooner a « swing », un rappeur
« flow serré »…). Chaque variante : id, noms (fr, en, de, es, it), en (description anglaise complète pour le moteur), mots
(pour la retrouver dans une phrase). Jamais un nom de personne dans les descriptions. Relancé par la veille quand le catalogue
change ; écrit catalogue/styles.json.

    python outils_dev/variantes_voix.py
"""
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, RACINE)
from app.voix_familles import variantes_pour as variantes   # noqa: E402  (la règle vit dans PhilCut : même résultat sans catalogue)


def main():
    p = os.path.join(RACINE, "catalogue", "styles.json")
    with open(p, encoding="utf-8") as f:
        cat = json.load(f)
    nb = 0
    for e in cat.get("styles") or []:
        if e.get("voix"):
            e["variantes"] = variantes(e.get("genre", "chant"), e["voix"])
            nb += 1
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{nb} voix avec leurs variantes")


if __name__ == "__main__":
    sys.exit(main())
