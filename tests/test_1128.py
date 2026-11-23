"""1.1.21 : Kling O3 refuse plus de 3 éléments avec une image de départ ou d'arrivée (422 du tarmac, 23/11 22h43) ; tout
refus 422 connu est corrigé et renvoyé ; Kling 3.0 reçoit « start_image_url » ; images ramenées aux règles de fal."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import generateurs_video as GV

MSG = ('HTTP 422 : {"detail":[{"loc":["body"],"msg":"The number of elements exceeds the limit for first/tail image input, '
       'max number is 3.","type":"input_value_error"}]}')


class Test1128(unittest.TestCase):
    def elements(self, n):
        return [{"nom": f"Character {chr(65 + i)}", "frontal_image_url": f"u{i}", "reference_image_urls": []} for i in range(n)]

    def test_trois_avec_image(self):
        m = GV.modele("kling-o3-ref")
        c = GV.corps_reference("walk", 6, "9:16", "dep", None, self.elements(4), m,
                               multi=[("a", 3), ("b", 3)])
        self.assertEqual(len(c["elements"]), 3)
        self.assertNotIn("Element4", c["multi_prompt"][0]["prompt"])
        c = GV.corps_reference("walk", 6, "9:16", None, None, self.elements(4), m)
        self.assertEqual(len(c["elements"]), 4)
        c = GV.corps_reference("walk", 6, "9:16", None, "fin", self.elements(4), m)
        self.assertEqual(len(c["elements"]), 3)

    def test_ajuster(self):
        c = {"multi_prompt": [{"prompt": "x"}], "elements": self.elements(4), "start_image_url": "d"}
        n = GV.ajuster_corps(c, MSG)
        self.assertEqual(len(n["elements"]), 3)
        self.assertEqual(len(c["elements"]), 4)              # l'original n'est pas touché
        n = GV.ajuster_corps({"multi_prompt": [{"prompt": "x"}], "end_image_url": "f"},
                             'HTTP 422 : {"msg":"Value error, End Image Url is not supported with Multi Prompt"}')
        self.assertNotIn("end_image_url", n)
        n = GV.ajuster_corps({"prompt": "mot " * 300}, 'HTTP 422 : {"msg":"Prompt must not exceed 512 characters."}')
        self.assertLessEqual(len(n["prompt"]), 512)
        n = GV.ajuster_corps({"image_url": "x"}, 'HTTP 422 : {"loc":["body","start_image_url"],"msg":"Field required"}')
        self.assertEqual(n, {"start_image_url": "x"})
        self.assertIsNone(GV.ajuster_corps({"prompt": "x"}, "HTTP 500 : erreur"))
        self.assertIsNone(GV.ajuster_corps({"prompt": "x"}, 'HTTP 422 : {"msg":"autre chose"}'))

    def test_renvoi_automatique(self):
        envois = []

        def faux_http(url, cle, corps=None, methode=None, delai=120):
            if url.endswith("reference-to-video"):
                envois.append(corps)
                if len(corps.get("elements") or []) > 3:
                    raise GV.ErreurGenerateur(MSG)
                return {"request_id": "r", "status_url": "s", "response_url": "rep"}
            if url == "s":
                return {"status": "COMPLETED"}
            return {"video": {"url": "v"}}
        vieux, GV._http = GV._http, faux_http
        vieux_sleep = GV.time.sleep
        GV.time.sleep = lambda s: None
        try:
            r = GV.demande_fal("k", "fal-ai/kling-video/o3/standard/reference-to-video",
                               {"prompt": "x", "elements": self.elements(4), "start_image_url": "d"})
        finally:
            GV._http, GV.time.sleep = vieux, vieux_sleep
        self.assertEqual(len(envois), 2)
        self.assertEqual(len(envois[1]["elements"]), 3)
        self.assertEqual(r, {"video": {"url": "v"}})

    def test_kling3_start_image(self):
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        im = QImage(1000, 150, QImage.Format_RGB32)          # trop allongée et trop basse
        im.fill(QColor("#336699"))
        ch = os.path.join(d, "i.png")
        im.save(ch)
        vu = {}
        vieux = GV.attendre_fal
        GV.attendre_fal = lambda cle, point, corps, *a, **k: vu.update(point=point, corps=corps)
        try:
            GV.generer_fal("k", GV.modele("kling-3-pro"), "a plane", os.path.join(d, "o.mp4"), 5, "16:9", ch)
            self.assertIn("start_image_url", vu["corps"])
            self.assertNotIn("image_url", vu["corps"])
            self.assertTrue(vu["point"].endswith("image-to-video"))
            GV.generer_fal("k", GV.modele("seedance-2"), "a plane", os.path.join(d, "o.mp4"), 5, "16:9", ch)
            self.assertIn("image_url", vu["corps"])
        finally:
            GV.attendre_fal = vieux
        g = QImage(GV.assez_grande(ch))
        self.assertGreaterEqual(min(g.width(), g.height()), 300)
        self.assertLessEqual(g.width() / g.height(), 2.5)

    def test_personnes_d_abord(self):
        from app import sequence_ia as Q
        d = tempfile.mkdtemp()
        imgs = []
        for i in range(2):
            p = os.path.join(d, f"{i}.png")
            open(p, "wb").close()
            imgs.append(p)
        seq = Q.nouvelle("9:16")
        seq["personnages"] = [{"nom": "Avion", "genre": "objet", "images": [imgs[0]]},
                              {"nom": "Pilote", "images": [imgs[1]]}]
        pl = {"action": "x", "personnages": ["Avion", "Pilote"], "duree": 4}
        refs = Q.references_du_plan(seq, pl)
        self.assertEqual([n for n, _i in refs], ["Character B", "Character A"])


if __name__ == "__main__":
    unittest.main()
