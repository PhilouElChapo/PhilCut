"""1.1.11 : images de référence trop allongées (fal 422), chemins d'images pour l'IA (relecture du remplacement),
plans jusqu'au dernier événement, Pilote Maxime repris par son nom."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def image(d, nom, l, h):
    from PySide6.QtGui import QImage, QColor
    im = QImage(l, h, QImage.Format_RGB32)
    im.fill(QColor("#305080"))
    p = os.path.join(d, nom)
    im.save(p)
    return p


class Test1121(unittest.TestCase):
    def test_rapport_accepte_par_fal(self):
        from PySide6.QtGui import QImage
        from app import generateurs_video as GV
        d = tempfile.mkdtemp()
        for l, h in ((1600, 400), (200, 900), (800, 600)):
            q = QImage(GV.assez_grande(image(d, f"{l}x{h}.png", l, h)))
            self.assertTrue(GV.RAPPORT_MIN <= q.width() / q.height() <= GV.RAPPORT_MAX, (l, h, q.width(), q.height()))
            self.assertGreaterEqual(min(q.width(), q.height()), GV.MINI_FAL)

    def test_chemins_d_images_pour_l_ia(self):
        from app import ia
        d = tempfile.mkdtemp()
        p = image(d, "a.png", 64, 64)
        recu = {}
        anc = ia.moteurs, ia._claude
        ia.moteurs = lambda params: [("claude", "x")]

        def faux(clef, params, consignes, texte, images, max_jetons):
            recu["i"] = images
            return "ok"
        ia._claude = faux
        try:
            self.assertEqual(ia.demander({}, "c", "t", images=[p, b"\xff\xd8octets"]), "ok")
        finally:
            ia.moteurs, ia._claude = anc
        self.assertTrue(all(isinstance(x, bytes) for x in recu["i"]))
        self.assertEqual(recu["i"][0][:2], b"\xff\xd8")

    def test_tous_les_plans(self):
        from app import assistant_creation as A
        self.assertIn("jusqu'au DERNIER", A.CONSIGNE_ANALYSE)
        d = {"personnages": [{"nom": "Pilote Maxime", "genre": "personne"}],
             "plans": [{"action": f"action {k}", "personnages": [], "duree": 4} for k in range(13)]}
        self.assertEqual(len(A.lire_analyse(d)["plans"]), 13)


if __name__ == "__main__":
    unittest.main()
