"""Suivi (section 14) : trajectoire d'un objet qui bouge, recadrage 9:16 -> 16:9 qui le garde au centre, Goodie accroché,
expressions FFmpeg identiques à l'interpolation de l'aperçu."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
commun.application()
import cv2
import numpy as np
from app import export, moteur, projet, suivi

L_SRC, H_SRC, CAD, DUREE = 360, 640, 25, 4.0


def objet_x(t):
    """L'objet (carré clair) va de la gauche vers la droite puis remonte un peu."""
    return 0.2 + 0.6 * t / DUREE


def video_mobile(chemin):
    w = cv2.VideoWriter(chemin, cv2.VideoWriter_fourcc(*"mp4v"), CAD, (L_SRC, H_SRC))
    for i in range(int(DUREE * CAD)):
        t = i / CAD
        img = np.full((H_SRC, L_SRC, 3), (40, 30, 25), np.uint8)
        for k in range(0, L_SRC, 40):           # décor : des bandes, pour que le recadrage se voie
            cv2.line(img, (k, 0), (k, H_SRC), (70, 60, 50), 2)
        cx, cy = int(objet_x(t) * L_SRC), int((0.5 - 0.1 * t / DUREE) * H_SRC)
        cv2.rectangle(img, (cx - 28, cy - 40), (cx + 28, cy + 40), (230, 240, 250), -1)
        cv2.circle(img, (cx, cy - 15), 9, (30, 30, 200), -1)
        w.write(img)
    w.release()
    return chemin


def centre_objet(img):
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ys, xs = np.where(gris > 180)
    return (xs.mean() / img.shape[1], ys.mean() / img.shape[0]) if len(xs) else (None, None)


class TestSuivi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        brut = video_mobile(os.path.join(cls.d, "brut.mp4"))
        cls.v = os.path.join(cls.d, "mobile.mp4")
        moteur.lancer(["-i", brut, "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", cls.v])
        cls.boite = (objet_x(0) - 28 / L_SRC, 0.5 - 40 / H_SRC, 56 / L_SRC, 80 / H_SRC)

    def test_expression_egale_interpolation(self):
        pts = [(0.0, 0.2), (1.0, 0.6), (2.5, 0.4)]
        e = suivi.expr(pts)
        env = {"lt": lambda a, b: float(a < b), "gte": lambda a, b: float(a >= b)}
        for t in (-1, 0, 0.5, 1, 1.7, 2.5, 9):
            self.assertAlmostEqual(eval(e, env, {"t": t}), suivi.valeur([(a, b) for a, b in pts], t), places=3)

    def test_trajectoire(self):
        pts = suivi.suivre(self.v, 0.0, DUREE, self.boite, pas=0.2)
        self.assertGreater(len(pts), 10)
        for t, cx, cy, _w, _h in pts[::4]:
            self.assertAlmostEqual(cx, objet_x(t), delta=0.06, msg=f"t={t}")
        lisse = suivi.lisser(pts, 0.6)
        self.assertEqual(len(lisse), len(pts))
        self.assertLess(max(abs(a[1] - b[1]) for a, b in zip(lisse, lisse[1:])), 0.06)

    def test_recadrage_vertical_vers_horizontal(self):
        """Rush vertical dans un projet 16:9 : le cadre suit l'objet, qui reste au centre de l'image exportée."""
        p = projet.Projet("Suivi", "16:9")
        m = p.ajouter_media(self.v, moteur.sonder(self.v))
        c = p.ajouter_clip(m["id"])
        suivi.recadrer(p, c, self.boite, zoom=1.0, lissage="reactif")
        self.assertEqual(c["ajustement"], "suivi")
        g = p.ajouter_goodie("horloge", 0.5, 3.5)
        suivi.accrocher(p, g, m, self.boite)
        self.assertGreater(len(g["suivi"]["positions"]), 5)
        out, _j = export.exporter(p, os.path.join(self.d, "suivi.mp4"), "whatsapp", progression=lambda x: None)
        f = moteur.sonder(out)
        self.assertGreater(f["video"]["largeur"], f["video"]["hauteur"])
        cap = cv2.VideoCapture(out)
        ecarts = []
        for t in (0.3, 1.5, 2.8):
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, img = cap.read()
            self.assertTrue(ok)
            cx, cy = centre_objet(img)
            self.assertIsNotNone(cx)
            ecarts.append(abs(cy - 0.5))
        cap.release()
        # sans suivi, l'objet serait coupé ou au bord ; avec suivi il reste près du centre vertical du cadre 16:9
        self.assertLess(max(ecarts), 0.2, ecarts)

    def test_fenetre_source_dans_l_image(self):
        cadre = {"positions": [(0, 0.02, 0.98), (1, 0.99, 0.01)], "zoom": 1.5}
        for t in (0, 0.5, 1):
            x, y, cw, ch = suivi.fenetre_source(cadre, t, 360, 640, 1920, 1080)
            self.assertTrue(0 <= x <= 360 - cw + 1e-6 and 0 <= y <= 640 - ch + 1e-6)
            self.assertAlmostEqual(cw / ch, 1920 / 1080, places=3)


if __name__ == "__main__":
    unittest.main()
