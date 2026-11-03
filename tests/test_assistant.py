"""L'assistant : fiche locale, classement, recette sans IA, application au projet, fusion d'une reponse IA."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
commun.application()
from app import moteur, projet, fiche, recettes, assistant


class TestAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.v = commun.video_test(cls.d, duree=6)
        cls.m = commun.musique_test(cls.d)

    def test_fiche(self):
        f = fiche.analyser(self.v, vignettes=4)
        self.assertEqual(f["genre"], "video")
        self.assertIn("resume", f)
        self.assertEqual(len(f["instants_vignettes"]), 4)
        self.assertIn("son", f)
        self.assertFalse(f["son"]["muet"])
        self.assertIn("lumiere", f)

    def test_classer(self):
        self.assertEqual(recettes.classer([], "vol avion F-GDLJ"), "vol")
        courts = [{"genre": "video", "duree": 5, "son": {"muet": True}, "video": {"largeur": 480}} for _ in range(3)]
        self.assertEqual(recettes.classer(courts), "clip_ia")
        nuit = [{"genre": "video", "duree": 80, "lumiere": {"nuit": True}, "visages": {"nb_max": 0}, "couleurs": [], "mouvement": [5]} for _ in range(2)]
        self.assertEqual(recettes.classer(nuit), "visite")

    def test_recette_et_application(self):
        p = projet.Projet("R", "16:9")
        m = p.ajouter_media(self.v, moteur.sonder(self.v))
        mu = p.ajouter_media(self.m, moteur.sonder(self.m))
        fiches = assistant.preparer(p, {}, progression=lambda f, t: None)
        self.assertTrue(m.get("analyse"))
        r = assistant.proposer(p, {"chaine_nom": "Chaine"}, fiches, indices="vol", niveau_force="recettes")
        self.assertEqual(r["type"], "vol")
        self.assertTrue(r["plans"])
        self.assertTrue(r["textes"])
        self.assertEqual(r["musique"]["media"], mu["id"])
        recettes.appliquer(r, p, {}, choix={"goodie:0": False})
        self.assertTrue(p.clips_piste("video"))
        self.assertTrue(p.clips_piste("audio"))
        self.assertEqual(len(p.goodies), len(r["goodies"]) - 1 + 1)   # un goodie refuse, mais le logo (bandeau) ajoute
        self.assertIsNotNone(p.d["recette"])

    def test_fusion_reponse_ia(self):
        p = projet.Projet("F", "16:9")
        m = p.ajouter_media(self.v, moteur.sonder(self.v))
        base = recettes.proposer(p.medias, {}, indices="vol")
        d = {"type": "vol", "titre": "Mon vol", "plans": [{"media": m["id"], "src_debut": 0, "src_fin": 99, "vitesse": 2, "effets": ["glow", "inconnu"], "transition": "t_puzzle"},
                                                          {"media": "faux", "src_debut": 0, "src_fin": 2}],
             "textes": [{"texte": "Titre", "debut": 0, "fin": 2, "animation": "neon", "x": 2, "y": -1}], "goodies": [{"genre": "altimetre", "debut": 0, "fin": 3}, {"genre": "inconnu"}]}
        r = assistant._fusionner(base, d, p)
        self.assertEqual(len(r["plans"]), 1)
        self.assertLessEqual(r["plans"][0]["src_fin"], 6.5)
        self.assertEqual([e["id"] for e in r["plans"][0]["effets"]], ["glow"])
        self.assertIsNone(r["plans"][0]["transition"])     # pas de transition sur le premier plan
        self.assertEqual(r["textes"][0]["x"], 1.0)
        self.assertEqual(len(r["goodies"]), 1)

    def test_autre_idee_sans_ia(self):
        p = projet.Projet("A", "16:9")
        p.ajouter_media(self.v, moteur.sonder(self.v))
        r = recettes.proposer(p.medias, {}, indices="vol")
        r2 = assistant.autre_idee(p, {"assistant_niveau": "recettes"}, r, "logo")
        self.assertNotEqual(r["logo"]["modele"], r2["logo"]["modele"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
