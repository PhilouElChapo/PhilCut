"""Traductions : chaque texte de l'interface passé à _() existe en anglais, allemand, espagnol et italien,
avec les mêmes {variables} que le français (sinon le texte s'afficherait en français ou planterait)."""
import ast, json, os, re, unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGUES = ("en", "de", "es", "it")


def textes_interface():
    cles = {}
    dossier = os.path.join(RACINE, "app")
    fichiers = [os.path.join(dossier, f) for f in sorted(os.listdir(dossier)) if f.endswith(".py")] + [os.path.join(RACINE, "philcut.py")]
    for chemin in fichiers:
        f = os.path.basename(chemin)
        with open(chemin, encoding="utf-8") as g:
            arbre = ast.parse(g.read())
        for n in ast.walk(arbre):
            if (isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_" and n.args
                    and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                cles.setdefault(n.args[0].value, f)
    return cles


class Traductions(unittest.TestCase):
    def test_tout_est_traduit(self):
        cles = textes_interface()
        self.assertGreater(len(cles), 1500)
        for l in LANGUES:
            with open(os.path.join(RACINE, "langues", l + ".json"), encoding="utf-8") as fl:
                d = json.load(fl)
            manque = [f"{f} : {k[:70]}" for k, f in cles.items() if not d.get(k)]
            self.assertEqual(manque, [], f"{l} : {len(manque)} texte(s) sans traduction")

    def test_variables_identiques(self):
        cles = textes_interface()
        for l in LANGUES:
            with open(os.path.join(RACINE, "langues", l + ".json"), encoding="utf-8") as fl:
                d = json.load(fl)
            for k in cles:
                t = d.get(k)
                if t:
                    self.assertEqual(sorted(re.findall(r"\{[^}]*\}", k)), sorted(re.findall(r"\{[^}]*\}", t)),
                                     f"{l} : variables différentes pour « {k[:60]} »")


if __name__ == "__main__":
    unittest.main()
