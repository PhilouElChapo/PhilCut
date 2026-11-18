"""0.9.89 : bibliothèque toute faite (catalogue/prompts.json) : pièces et matières pour composer une tenue, tenues complètes,
lieux, véhicules, avions, personnages types ; rangement dans « Ma bibliothèque » ; mots anglais gardés pour les IA."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCatalogue(unittest.TestCase):
    def test_contenu(self):
        from app import catalogue_prompts as CP
        cat = json.load(open(os.path.join(RACINE, "catalogue", "prompts.json"), encoding="utf-8"))
        ids = [e["id"] for e in cat["entrees"]]
        self.assertEqual(len(ids), len(set(ids)))
        for e in cat["entrees"]:
            self.assertTrue(e["en"] and e["nom"]["fr"] and e["description"]["fr"], e["id"])
            self.assertIn(e["rubrique"], cat["rubriques"])
            self.assertIn(e["pour"], ("f", "h", "m"))
        noms = {e["id"] for e in CP.entrees("chaussures")}
        for x in ("baskets_blanches", "mocassins", "bottines", "escarpins_hauts", "escarpins_moyens", "talons_bas"):
            self.assertIn(x, noms)
        self.assertTrue({"borsalino", "texan", "bonnet", "casquette"} <= {e["id"] for e in CP.entrees("chapeau")})
        self.assertTrue({"cachemire", "cuir", "luxe"} <= {e["id"] for e in CP.entrees("matiere")})
        self.assertTrue({"piscine", "bord_mer", "jardin", "cathedrale"} <= {e["id"] for e in CP.entrees("lieu")})
        self.assertTrue({"limousine", "sportive", "citadine", "berline", "suv"} <= {e["id"] for e in CP.entrees("vehicule")})
        self.assertTrue({"helicoptere", "avion_leger"} <= {e["id"] for e in CP.entrees("air")})
        self.assertNotIn("escarpins_hauts", {e["id"] for e in CP.entrees("chaussures", "h")})     # femme / homme
        self.assertIn("mocassins", {e["id"] for e in CP.entrees("chaussures", "h")})                # mixte reste
        self.assertEqual([e["id"] for e in CP.entrees(texte="helico")], ["helicoptere"])
        fr, en = CP.composer(["chemisier_soie", "jupe_crayon", "escarpins_moyens", "capeline"], "soie")
        self.assertIn("escarpins", fr)
        self.assertIn("silk", en)

    def test_vers_bibliotheque(self):
        from app import catalogue_prompts as CP, bibliotheque_creations as B, tenues as T
        params = {}
        x = CP.vers_bibliotheque(params, CP.entree("suv"))
        self.assertEqual(x["genre"], "objet")
        self.assertEqual(x["donnees"]["en"], "tall rugged SUV")
        self.assertEqual(CP.vers_bibliotheque(params, CP.entree("piscine"))["genre"], "lieu")
        self.assertEqual(CP.vers_bibliotheque(params, CP.entree("directrice"))["genre"], "personnage")
        with self.assertRaises(ValueError):
            CP.vers_bibliotheque(params, CP.entree("borsalino"))                   # une pièce se compose, ne se range pas seule
        self.assertTrue(any(t["id"] == "cat:t_western" for t in T.toutes(params)))

    def test_fenetres(self):
        from app.dialogues_catalogue_prompts import DialogueCatalogue, ComposerTenue
        d = DialogueCatalogue(None, {}, ("lieu",))
        self.assertTrue(all(e["rubrique"] == "lieu" for e in d.items))
        d.cherche.setText("piscine")
        d.ajouter()
        self.assertEqual(d.ajoutees[0]["nom"], "Piscine")
        self.assertLessEqual(d.minimumSizeHint().width(), 1024)
        c = ComposerTenue(None)
        c.pour.setCurrentIndex(c.pour.findData("f"))
        c.combos["chaussures"].setCurrentIndex(c.combos["chaussures"].findData("bottes_hautes"))
        c.combos["matiere"].setCurrentIndex(c.combos["matiere"].findData("cuir"))
        self.assertIn("bottes", c.resultat[0])
        self.assertIn("leather", c.resultat[1])


if __name__ == "__main__":
    unittest.main()
