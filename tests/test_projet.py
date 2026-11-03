"""Le modele du projet : clips, coupes, deplacement, rognage, annuler, enregistrement."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
from app.projet import Projet, fin_clip, duree_clip


class TestProjet(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = Projet("Test", "16:9")
        self.m = self.p.ajouter_media(os.path.join(self.d, "x.mp4"), {"duree": 10.0, "video": {"largeur": 1920, "hauteur": 1080}})

    def test_clips_bout_a_bout(self):
        a = self.p.ajouter_clip(self.m["id"])
        b = self.p.ajouter_clip(self.m["id"])
        self.assertEqual(a["debut"], 0.0)
        self.assertEqual(b["debut"], 10.0)
        self.assertEqual(self.p.duree(), 20.0)

    def test_couper_et_refermer(self):
        a = self.p.ajouter_clip(self.m["id"])
        droite = self.p.couper(a["id"], 4.0)
        self.assertAlmostEqual(a["src_fin"], 4.0)
        self.assertAlmostEqual(droite["src_debut"], 4.0)
        self.assertAlmostEqual(droite["debut"], 4.0)
        self.p.retirer_clip(a["id"])
        self.assertAlmostEqual(self.p.clips[0]["debut"], 0.0)
        self.assertAlmostEqual(duree_clip(self.p.clips[0]), 6.0)

    def test_vitesse_et_duree(self):
        a = self.p.ajouter_clip(self.m["id"])
        self.p.vitesse(a["id"], 2.0)
        self.assertAlmostEqual(duree_clip(a), 5.0)
        b = self.p.ajouter_clip(self.m["id"])
        self.assertAlmostEqual(b["debut"], 5.0)

    def test_pas_de_chevauchement(self):
        a = self.p.ajouter_clip(self.m["id"], src_fin=5)
        b = self.p.ajouter_clip(self.m["id"], src_fin=5)
        self.p.deplacer(b["id"], 2.0)
        self.assertGreaterEqual(b["debut"], fin_clip(a) - 1e-6)

    def test_annuler(self):
        self.p.marquer()
        self.p.ajouter_clip(self.m["id"])
        self.assertEqual(len(self.p.clips), 1)
        self.assertTrue(self.p.annuler())
        self.assertEqual(len(self.p.clips), 0)
        self.assertTrue(self.p.refaire())
        self.assertEqual(len(self.p.clips), 1)

    def test_enregistrer_rouvrir(self):
        self.p.ajouter_clip(self.m["id"], src_fin=3)
        self.p.ajouter_titre("Bonjour", 0, 2, animation="neon")
        self.p.ajouter_goodie("altimetre", 0, 3, valeurs=[(0, 0), (3, 100)])
        chemin = self.p.enregistrer(os.path.join(self.d, "t"))
        self.assertTrue(chemin.endswith(".philcut"))
        q = Projet.ouvrir(chemin)
        self.assertEqual(q.nom, "Test")
        self.assertEqual(len(q.clips), 1)
        self.assertEqual(q.titres[0]["texte"], "Bonjour")
        self.assertEqual(q.goodies[0]["genre"], "altimetre")


if __name__ == "__main__":
    unittest.main(verbosity=2)
