"""0.9.77 : visages gardés sur toute une histoire (départ enchaîné sur l'arrivée validée, fiches en tête des références,
une personne par fiche même d'après une photo de groupe), personnage inventé (le chauffeur) avec sa fiche."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestVisages(unittest.TestCase):
    def test_tout(self):
        from app import sequence_ia as Q, ia
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        img = os.path.join(d, "a.png")
        q = QImage(64, 36, QImage.Format_RGB32)
        q.fill(QColor("gray"))
        q.save(img)
        with open(img, "rb") as f:
            png = f.read()
        s = Q.nouvelle()
        s["personnages"] = [Q.personnage("Les deux", ""), Q.personnage("Chauffeur", "homme en costume sombre, casquette")]
        self.assertEqual(Q.groupes_suspects(s), ["Les deux"])
        s["plans"] = [Q.plan("Le chauffeur ouvre la portière", ["Chauffeur"], "", 5),
                      Q.plan("Le chauffeur vient ouvrir la portière pour que les deux femmes montent", ["Chauffeur"], "", 5)]
        self.assertTrue(Q.actions_multiples(s["plans"][1]["action"]))
        vus = []
        anc = (ia.generer_image, ia.generer_image_refs)
        ia.generer_image = lambda p, c, *a, **k: (vus.append(("texte", c)), png)[1]
        ia.generer_image_refs = lambda p, c, refs, delai=240: (vus.append(("refs", c, list(refs))), png)[1]
        try:
            self.assertEqual([p["nom"] for p in Q.sans_planche(s, [0])], ["Chauffeur"])
            Q.planche_personnage(s, s["personnages"][1], {"clef_gemini": "x"})
            self.assertEqual(vus[0][0], "texte")
            self.assertIn("INVENTED", vus[0][1])
            s["plans"][0]["image_fin"] = img
            self.assertEqual(Q.depart_enchaine(s, 1), img)            # départ = arrivée validée, pas la dernière image dérivée
            s["plans"][0]["image"] = img
            Q.image_arrivee(s, 0, {"clef_gemini": "x"}, img)
            self.assertEqual(vus[-1][2][0], s["personnages"][1]["planche"])   # la fiche passe avant l'image de départ
        finally:
            ia.generer_image, ia.generer_image_refs = anc
        self.assertIn("ONLY the one person", Q.CONSIGNE_PLANCHE)


if __name__ == "__main__":
    unittest.main()
