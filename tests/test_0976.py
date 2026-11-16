"""0.9.76 : « Prolonger ce plan » par l'IA cloud : une photo n'est plus figée ; une suite décrite d'un coup devient des
étapes d'une action, fabriquées à la chaîne (chacune part de la dernière image de la précédente)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestSuiteAutomatique(unittest.TestCase):
    def test_etapes(self):
        from app.prolonger import etapes_suite as E, prix_etapes
        et = E("The women walk down the steps, then they walk to a limousine; a driver helps them in. Then it drives away.", 24,
               "Elles descendent les marches, puis vont vers une limousine ; un chauffeur les aide. Puis elle démarre.")
        self.assertEqual([x[2] for x in et], ["Elles descendent les marches", "Vont vers une limousine", "Un chauffeur les aide",
                                              "Elle démarre"])
        self.assertEqual([x[1] for x in et], [6.0] * 4)
        un = E("They descend the steps; the camera moves back.", 6)
        self.assertEqual(len(un), 1)
        self.assertAlmostEqual(prix_etapes(et), 2.0, delta=0.05)

    def test_photo_en_plusieurs_etapes(self):
        from app import prolonger as PR, generateurs_video as GV, moteur
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        photo = os.path.join(d, "photo.png")
        q = QImage(180, 320, QImage.Format_RGB32)
        q.fill(QColor("gray"))
        q.save(photo)
        media = {"chemin": photo, "genre": "image", "fiche": moteur.sonder(photo)}
        clip = {"id": "c1", "src_debut": 0.0, "src_fin": 3.0}
        vus = []
        anc = GV.generer

        def faux(params, ident, texte, sortie, duree, fmt, image, *a, **k):
            vus.append((duree, fmt, image, texte))
            moteur.lancer(["-y", "-f", "lavfi", "-i", f"testsrc=size=180x320:rate=10:duration={duree}", "-pix_fmt", "yuv420p", sortie])
            return sortie
        GV.generer = faux
        try:
            et = PR.etapes_suite("They walk down the steps, then they get into a car.", 8)
            out = PR.fabriquer(media, clip, 8, "cloud", "fin", "silence", (180, 320), 25, {"clef_fal": "a:b"},
                               sortie=os.path.join(d, "suite.mp4"), etapes=et)
        finally:
            GV.generer = anc
        self.assertEqual(len(vus), 2)
        self.assertEqual(vus[0][2], photo)                       # la photo est le point de départ (plus d'image figée)
        self.assertIn("fin0.png", vus[1][2])                     # l'étape 2 part de la fin de l'étape 1
        self.assertEqual(vus[0][1], "9:16")
        self.assertAlmostEqual(float(moteur.sonder(out)["duree"]), 8.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
