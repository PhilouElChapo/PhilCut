"""Atelier de logo : gabarits, rendu transparent, sélection par clic, propositions de l'IA nettoyées, enregistrement
(PNG + JSON) puis animation par la Fabrique avec ce logo."""
import json, os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
commun.application()
from app import logo as LG


class TestLogo(unittest.TestCase):
    def test_gabarits_et_rendu(self):
        for nom, lg in LG.gabarits("Phil Aviation").items():
            img = LG.rendre(lg, 256)
            self.assertEqual(img.width(), 256, nom)
            coin = img.pixelColor(1, 1)
            if not lg.get("fond"):
                self.assertEqual(coin.alpha(), 0, nom)          # fond transparent
            visibles = sum(img.pixelColor(x, y).alpha() > 0 for x in range(0, img.width(), 8) for y in range(0, img.height(), 8))
            self.assertGreater(visibles, 20, nom)

    def test_selection_au_clic(self):
        lg = LG.gabarits("Test")["Badge rond"]
        self.assertEqual(LG.element_sous(lg, 512, 530), 1)       # le texte, au-dessus du cercle
        self.assertEqual(LG.element_sous(lg, 200, 512), 0)       # le cercle seul
        self.assertIsNone(LG.element_sous(lg, 5, 5))

    def test_proposition_ia_nettoyee(self):
        rep = json.dumps({"propositions": [
            {"nom": "A", "largeur": 1024, "hauteur": 1024, "fond": "pas une couleur",
             "elements": [{"type": "forme", "forme": "inconnue", "x": 512, "y": 512, "l": 800, "h": 800, "couleur": "#112233"},
                          {"type": "texte", "texte": "Phil", "taille": "180", "effet": "lueur", "couleur2": "#ff00ff"},
                          {"type": "script", "code": "rm -rf"}]},
            {"nom": "vide", "elements": []}]})
        with mock.patch("app.ia.demander", return_value=rep):
            props = LG.proposer_ia({"clef_claude": "x"}, "Phil")
        self.assertEqual(len(props), 1)
        p = props[0]
        self.assertIsNone(p["fond"])
        self.assertEqual([e["type"] for e in p["elements"]], ["forme", "texte"])
        self.assertEqual(p["elements"][0]["forme"], "cercle")
        self.assertEqual(p["elements"][1]["taille"], 180.0)
        self.assertFalse(LG.rendre(p, 128).isNull())

    def test_enregistrer_et_animer(self):
        lg = dict(LG.gabarits("Phil Aviation")["Aviation (ailes)"], nom="Phil Aviation")
        png = LG.enregistrer(lg)
        self.assertTrue(os.path.exists(png) and os.path.exists(png[:-4] + ".json"))
        self.assertIn("Phil Aviation", [x["nom"] for x in LG.liste()])
        from app import fabrique, moteur
        sortie = os.path.join(tempfile.mkdtemp(), "intro.mp4")
        fabrique.fabriquer_logo(sortie, "Phil Aviation", "eclat", 640, 360, 25, 1.2, image_logo=png)
        self.assertAlmostEqual(moteur.sonder(sortie)["duree"], 1.2, delta=0.2)


if __name__ == "__main__":
    unittest.main()
