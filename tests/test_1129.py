"""1.1.23 : fiche d'une vraie personne obligatoire (face, profil, en pied, tenue complétée) ; Seedream (fal.ai) en secours quand
Gemini refuse ; la vidéo ne part pas sans les fiches des personnes."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import sequence_ia as Q, ia


def _png(d, nom):
    from PySide6.QtGui import QImage, QColor
    im = QImage(400, 500, QImage.Format_RGB32)
    im.fill(QColor("#aa8866"))
    ch = os.path.join(d, nom)
    im.save(ch)
    return ch


class Test1129(unittest.TestCase):
    def seq(self):
        d = tempfile.mkdtemp()
        s = Q.nouvelle("9:16")
        s["personnages"] = [{"nom": "Femme brune", "images": [_png(d, "a.png")], "mode": "reel", "accord": True},
                            {"nom": "Avion", "genre": "objet", "images": [_png(d, "b.png")]}]
        s["plans"] = [{"action": "marche", "duree": 4, "personnages": ["Femme brune", "Avion"]}]
        return s

    def test_sans_fiche(self):
        s = self.seq()
        self.assertEqual(Q.personnes_sans_fiche(s), ["Femme brune"])     # l'objet n'est pas exigé
        self.assertIn("complete the rest of the outfit", Q.CONSIGNE_PLANCHE)

    def test_secours_seedream(self):
        s = self.seq()
        appels = []

        def refuse(params, consigne, images, delai=240):
            raise ia.ErreurIA("Gemini n'a pas renvoyé d'image (IMAGE_OTHER).")

        def secours(params, consigne, refs):
            appels.append((consigne, refs))
            return b"\x89PNG\r\n\x1a\nfiche"
        v1, v2 = ia.generer_image_refs, Q.planche_secours
        ia.generer_image_refs, Q.planche_secours = refuse, secours
        try:
            Q.planche_personnage(s, s["personnages"][0], {"clef_gemini": "g", "clef_fal": "f"})
            self.assertEqual(len(appels), 1)
            self.assertTrue(os.path.exists(s["personnages"][0]["planche"]))
            self.assertEqual(Q.personnes_sans_fiche(s), [])
            # sans clef fal.ai : l'erreur de Gemini remonte telle quelle
            s["personnages"][0].pop("planche")
            with self.assertRaises(ia.ErreurIA):
                Q.planche_personnage(s, s["personnages"][0], {"clef_gemini": "g"})
        finally:
            ia.generer_image_refs, Q.planche_secours = v1, v2

    def test_planche_secours_appel(self):
        from app import generateurs_video as GV
        vu = {}
        v = (GV.televerser, GV.demande_fal)
        GV.televerser = lambda cle, ch: "https://x/" + os.path.basename(ch)
        GV.demande_fal = lambda cle, point, corps, *a, **k: vu.update(point=point, corps=corps) or {"images": []}
        try:
            with self.assertRaises(ValueError):
                Q.planche_secours({"clef_fal": "a:b"}, "sheet", [self.seq()["personnages"][0]["images"][0]])
        finally:
            GV.televerser, GV.demande_fal = v
        self.assertEqual(vu["point"], "fal-ai/bytedance/seedream/v4.5/edit")
        self.assertEqual(len(vu["corps"]["image_urls"]), 1)
        self.assertGreaterEqual(vu["corps"]["image_size"]["width"], 1920)


if __name__ == "__main__":
    unittest.main()
