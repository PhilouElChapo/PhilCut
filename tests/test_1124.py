"""1.1.14 : animation libre : $() accepte un objet de styles (l'IA de Philippe l'écrivait ainsi : tous les styles perdus,
« [object Object] » : mots sans couleur, canons mal placés, flammes visibles en étoiles)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test1124(unittest.TestCase):
    def test_style_objet(self):
        from app import motion_libre as ML
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(racine, "tests", "exemples", "libre_canons.txt"), encoding="utf-8") as f:
            s = ML.sections(f.read())
        self.assertIn("backgroundImage", s["js"])                 # le vrai cas : styles donnés en objet
        a = ML.appliquer(ML.fiche("essai", (1080, 1920)), s)
        from app import motion_html as MH
        page = MH.composition(a) if hasattr(MH, "composition") else ""
        self.assertIn("__style", page)
        self.assertIn('typeof style === "string"', page)
        self.assertIn("camelCase", ML.CONSIGNE)


if __name__ == "__main__":
    unittest.main()
