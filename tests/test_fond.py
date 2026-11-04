"""Changer le fond (section 15) : la personne détourée reste, le fond devient une couleur, le fond flouté ou un autre
média ; le masque suit le cadrage du plan (rush vertical dans un projet horizontal).

Le masque vient ici d'un détourage « idéal » (le sujet clair de l'image de synthèse) pour vérifier sans ambiguïté le
cadrage et le mélange ; le vrai modèle U²-Net est essayé à part (fabrication « Moteurs IA locaux »)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
commun.application()
import cv2
import numpy as np
from app import export, moteur, projet


def video_sujet(chemin, L=360, H=640, duree=2.0, cad=25):
    w = cv2.VideoWriter(chemin, cv2.VideoWriter_fourcc(*"mp4v"), cad, (L, H))
    for i in range(int(duree * cad)):
        img = np.zeros((H, L, 3), np.uint8)
        img[:] = (40, 120, 40)                                        # décor vert
        cv2.ellipse(img, (L // 2, H // 2), (70, 160), 0, 0, 360, (200, 200, 230), -1)   # sujet clair au centre
        cv2.circle(img, (L // 2, H // 2 - 120), 40, (180, 190, 220), -1)
        w.write(img)
    w.release()
    return chemin


def masque_ideal(img):
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return np.where(gris > 160, 255, 0).astype(np.uint8)


class TestFond(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import segmentation
        cls._ancien = segmentation.masque_image
        segmentation.masque_image = masque_ideal
        cls.d = tempfile.mkdtemp()
        brut = video_sujet(os.path.join(cls.d, "brut.mp4"))
        cls.v = os.path.join(cls.d, "sujet.mp4")
        moteur.lancer(["-i", brut, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", cls.v])

    @classmethod
    def tearDownClass(cls):
        from app import segmentation
        segmentation.masque_image = cls._ancien

    def _export(self, fond, ajustement="contenir_noir", **params):
        p = projet.Projet("Fond", "16:9")
        m = p.ajouter_media(self.v, moteur.sonder(self.v))
        c = p.ajouter_clip(m["id"])
        c["ajustement"] = ajustement
        c["effets"] = [{"id": "detourage", "params": dict(fond=fond, adoucir=0.5, **params)}]
        out, _j = export.exporter(p, os.path.join(self.d, f"f_{fond}_{ajustement}.mp4"), "whatsapp", progression=lambda x: None)
        cap = cv2.VideoCapture(out)
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
        ok, img = cap.read()
        cap.release()
        self.assertTrue(ok)
        return img

    def test_fond_couleur_et_cadrage(self):
        img = self._export("couleur", couleur="#d02020")          # rouge
        H, L = img.shape[:2]
        centre = img[H // 2, L // 2].astype(int)                  # le sujet (clair) est gardé
        bord = img[H // 2, L // 2 + int(L * 0.12)].astype(int)    # à côté du sujet, dans l'image : plus vert, rouge
        self.assertGreater(centre.min(), 150, centre)
        self.assertGreater(bord[2], 150, bord)
        self.assertLess(bord[1], 90, bord)

    def test_fond_flou(self):
        img = self._export("flou", ajustement="remplir")
        H, L = img.shape[:2]
        self.assertGreater(img[H // 2, L // 2].astype(int).min(), 150)

    def test_sans_media_garde_l_original(self):
        img = self._export("media")
        H, L = img.shape[:2]
        self.assertGreater(img[H // 2, L // 2 + int(L * 0.12)].astype(int)[1], 90)    # décor vert d'origine


if __name__ == "__main__":
    unittest.main()
