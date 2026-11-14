"""0.9.70 : retours de Philippe sur la Séquence IA avec Gemini (gestes incohérents : le personnage traverse la table pour
s'asseoir ; personnage qui ne ressemble pas à son image). Une action par plan (détection, coupe en deux, découpage IA et
consigne), image de départ composée d'office avec les images du personnage (Gemini) et comptée dans le prix."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestUneAction(unittest.TestCase):
    def test_detection(self):
        from app import sequence_ia as Q
        for t in ("Hélène contourne le bureau et s'assoit dans son fauteuil", "Il ouvre la porte et entre dans la pièce",
                  "Il se lève puis sort", "Elle range ses papiers avant de partir"):
            self.assertIsNotNone(Q.actions_multiples(t), t)
        for t in ("Elle s'avance vers le bureau en verre et bois, esquissant un sourire", "Le chat et le chien dorment",
                  "Une table et une chaise", "Ses mains ouvrent délicatement l'écran"):
            self.assertIsNone(Q.actions_multiples(t), t)

    def test_coupe_et_consigne(self):
        from app import sequence_ia as Q
        s = Q.nouvelle()
        s["personnages"] = [Q.personnage("Hélène", "femme de 35 ans, chemisier blanc")]
        s["plans"] = [Q.plan("Hélène contourne le bureau et s'assoit dans son fauteuil", ["Hélène"], "", 6)]
        self.assertTrue(Q.couper_plan(s, 0))
        self.assertEqual([p["action"] for p in s["plans"]], ["Hélène contourne le bureau", "Hélène s'assoit dans son fauteuil"])
        self.assertEqual([p["duree"] for p in s["plans"]], [4, 4])
        self.assertFalse(Q.couper_plan(s, 0))
        c = Q.consigne(s, s["plans"][1], traduire=False)
        self.assertIn("One single simple action", c)
        self.assertIn("never pass through objects", c)
        self.assertIn("UNE SEULE action", Q.CONSIGNE_DECOUPER)

    def test_image_de_depart_automatique(self):
        from app import sequence_ia as Q, generateurs_video as GV
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        img = os.path.join(d, "helene.png")
        q = QImage(32, 32, QImage.Format_RGB32)
        q.fill(QColor("gray"))
        q.save(img)
        s = Q.nouvelle()
        s["dossier"] = d
        s["personnages"] = [Q.personnage("Hélène", "femme")]
        s["personnages"][0]["images"] = [img]
        s["plans"] = [Q.plan("Hélène s'assoit", ["Hélène"], "", 5)]
        params = {"clef_gemini": "x"}
        composees, envoyees = [], []
        anc = (Q.image_depart, GV.generer)
        Q.image_depart = lambda seq, i, p, m="gemini": (composees.append(i), img)[1]
        GV.generer = lambda params, ident, texte, sortie, duree, fmt, image, *a, **k: envoyees.append(image)
        try:
            Q.fabriquer_plan(s, 0, params, "omni-720p")
        finally:
            Q.image_depart, GV.generer = anc
        self.assertEqual(composees, [0])
        self.assertEqual(envoyees, [img])                       # le moteur part de l'image composée
        self.assertEqual(s["plans"][0]["image"], img)
        s["plans"][0]["image"] = ""
        sans = Q.prix_total(dict(s, image_auto=False), "omni-720p", params)
        self.assertAlmostEqual(Q.prix_total(s, "omni-720p", params) - sans, 0.04, places=2)   # compté dans le prix


if __name__ == "__main__":
    unittest.main()
