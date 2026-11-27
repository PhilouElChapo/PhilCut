"""1.3.12 (choix de Philippe, 27/11) : concert en plans de 6 à 10 s, un plan sur quatre chante (lèvres), instruments en partie
cachés, lèvres sur ce poste d'abord, plans remis au format du projet avant d'être posés."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import clip_groupe as CG, moteur, levres as LV


def analyse(duree=200.0, mesure=2.0):
    mes = [round(k * mesure, 3) for k in range(int(duree / mesure) + 1)]
    parts = [("intro", 0, 20, 0.2, 0), ("couplet", 20, 60, 0.4, 1), ("refrain", 60, 90, 0.8, 2), ("couplet", 90, 130, 0.4, 1),
             ("refrain", 130, 160, 0.8, 2), ("solo", 160, 180, 0.6, 3), ("fin", 180, duree, 0.2, 4)]
    return {"duree": duree, "bpm": 120, "mesures": mes, "chante": True, "caption_en": "rock",
            "sections": [{"type": t, "debut": a, "fin": b, "energie": e, "groupe": g} for t, a, b, e, g in parts]}


class TestConcert(unittest.TestCase):
    def setUp(self):
        self.c = CG.nouveau("chanson.wav", analyse(), lieu="concert")

    def test_decoupage(self):
        pl = self.c["plans"]
        self.assertLessEqual(len(pl), 30)
        libres = [p for p in pl if p["reprend"] is None]
        self.assertTrue(all(p["fin"] - p["debut"] <= 10.51 for p in pl))
        self.assertLessEqual(len(pl), 24)                                     # environ 20 plans pour 3 min 20
        chantent = [p for p in libres if p["chant"]]
        self.assertTrue(chantent)
        self.assertLessEqual(len(chantent), len(libres) // 3 + 1)              # environ un sur quatre
        self.assertTrue(all("facing the camera" in p["action_en"] for p in chantent))
        self.assertTrue(all(not pl[p["reprend"]]["chant"] for p in pl if p["reprend"] is not None))
        self.assertFalse(any(p["chant"] for p in pl if p["partie"] in ("intro", "fin", "solo")))

    def test_consignes(self):
        pl = self.c["plans"]
        i = next(k for k, p in enumerate(pl) if p["chant"])
        j = next(k for k, p in enumerate(pl) if not p["chant"])
        self.assertIn("mouth", CG.consigne(self.c, i, traduire=False))
        cj = CG.consigne(self.c, j, traduire=False)
        self.assertIn("nobody sings toward the camera", cj)
        self.assertIn("no close-up on hands", cj)

    def test_levres_local_puis_cloud(self):
        anc = LV.local_manque, LV.clef
        try:
            LV.local_manque, LV.clef = (lambda: ""), (lambda p: "k")
            self.assertEqual(CG.ou_levres({}), "local")
            self.assertEqual(CG.ou_levres({}, {"levres_cloud": True}), "cloud")
            LV.local_manque = lambda: "pas installé"
            self.assertEqual(CG.ou_levres({}), "cloud")
            LV.clef = lambda p: ""
            self.assertEqual(CG.ou_levres({}), "")
        finally:
            LV.local_manque, LV.clef = anc

    def test_refaire_levres_et_pose(self):
        d = tempfile.mkdtemp()
        c = self.c
        c["dossier"] = d
        v = commun.video_test(d)
        son = os.path.join(d, "s.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=200", son])
        c["chemin"] = son
        i = next(k for k, p in enumerate(c["plans"]) if p["chant"])
        c["plans"][i]["fichier"] = v
        vus = []

        def faux_local(params, s, video, sortie, progression=None, arret=lambda: False):
            vus.append("local")
            moteur.lancer(["-y", "-i", video, "-c", "copy", sortie])
            return sortie
        anc = LV.local_manque, LV.fabriquer_local
        LV.local_manque, LV.fabriquer_local = (lambda: ""), faux_local
        try:
            lv = CG.refaire_levres(c, i, {})
            lv2 = CG.refaire_levres(c, i, {})
        finally:
            LV.local_manque, LV.fabriquer_local = anc
        self.assertEqual(vus, ["local", "local"])
        self.assertEqual(c["plans"][i]["fichier"], lv2)
        self.assertEqual(c["plans"][i]["video_brute"], v)                     # la vidéo payée est gardée
        self.assertIn(lv, c["plans"][i]["prises_levres"])
        n = CG.preparer_pose(c, (640, 360), 25)
        self.assertEqual(n, 1)
        info = moteur.sonder(c["plans"][i]["pose"])
        self.assertEqual((info["video"]["largeur"], info["video"]["hauteur"]), (640, 360))
        self.assertAlmostEqual(float(info["duree"]), c["plans"][i]["fin"] - c["plans"][i]["debut"], delta=0.1)


if __name__ == "__main__":
    unittest.main()
