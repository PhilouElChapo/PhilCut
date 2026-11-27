"""1.4.2 : multicaméra : calage par le son (corrélation), par l'heure, à la main ; plan multicaméra, coupe sur un angle,
changer d'angle, mosaïque, proposition de l'assistant ; un seul Annuler."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import multicam as MC, moteur
from app.projet import fin_clip


def attendre(cond, s=120):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestMulticam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Un « événement » sonore commun (bruit) de 30 s ; trois caméras qui le captent à des moments différents."""
        cls.d = tempfile.mkdtemp()
        src = os.path.join(cls.d, "evenement.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "anoisesrc=d=30:c=pink:r=48000:a=0.3:s=7", "-ac", "1", src])
        cls.cams = []
        for k, (debut, duree, couleur, son) in enumerate(((0.0, 20.0, "red", True), (3.5, 18.0, "green", True),
                                                          (7.25, 15.0, "blue", True), (2.0, 10.0, "yellow", False))):
            v = os.path.join(cls.d, f"cam{k + 1}.mp4")
            args = ["-y", "-f", "lavfi", "-i", f"color=c={couleur}:s=320x180:r=25:d={duree}"]
            if son:
                args += ["-ss", str(debut), "-t", str(duree), "-i", src, "-c:a", "aac", "-shortest"]
            moteur.lancer(args + ["-vf", "drawbox=x='mod(t*80,300)':y=60:w=20:h=20:c=white:t=fill" if k == 1 else "null",
                                  "-pix_fmt", "yuv420p", v])
            cls.cams.append((v, debut))

    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre()
        self.f.bienvenue = lambda *a, **k: None
        self.ed = self.f.nouveau_projet("16:9")
        self.p = self.ed.projet
        self.ms = [self.p.ajouter_media(v, moteur.sonder(v)) for v, _d in self.cams]

    def test_calage_son_heure_main(self):
        r = MC.synchroniser(self.ms[:3])
        self.assertTrue(all(a["methode"] == "son" for a in r))
        for a, (_v, debut) in zip(r, self.cams[:3]):
            self.assertAlmostEqual(a["decalage"], debut, delta=0.01)        # au centième près
        self.ms[3]["fiche"]["date"] = ""
        r = MC.synchroniser([self.ms[0], self.ms[3]])
        self.assertEqual(r[1]["methode"], "main")                          # sans son ni heure : à la main
        self.ms[0]["fiche"]["date"] = "2026-11-27T10:00:00.000000Z"
        self.ms[3]["fiche"]["date"] = "2026-11-27T10:00:02.000000Z"
        r = MC.synchroniser([self.ms[0], self.ms[3]])
        self.assertEqual((r[1]["methode"], r[1]["decalage"]), ("heure", 2.0))
        with self.assertRaises(ValueError):
            MC.synchroniser(self.ms[:1])

    def test_plan_coupes_angles_annuler(self):
        angles = MC.synchroniser(self.ms[:3])
        self.p.marquer()
        mc = MC.creer(self.p, angles, son=self.ms[1]["id"])
        v = self.p.clips_piste("video")
        self.assertEqual(len(v), 1)
        self.assertTrue(v[0]["muet"])
        son = [c for p in self.p.pistes_audio() for c in self.p.clips_piste(p) if c.get("son_multicam")]
        self.assertEqual(len(son), 1)
        self.assertAlmostEqual(son[0]["debut"], 3.5, delta=0.02)           # la source son est calée sur le même axe
        o = v[0]["origine_mc"]
        self.p.marquer()
        c2 = MC.couper_angle(self.p, o + 8.0, 1)                           # à 8 s : angle 2
        self.assertIsNotNone(c2)
        self.assertEqual(c2["media"], self.ms[1]["id"])
        self.assertAlmostEqual(c2["src_debut"], 8.0 - 3.5, delta=0.02)     # le même instant, vu par l'angle 2
        c3 = MC.couper_angle(self.p, o + 12.0, 2)
        self.assertAlmostEqual(c3["src_debut"], 12.0 - 7.25, delta=0.02)
        self.assertIsNone(MC.couper_angle(self.p, o + 1.0, 2))             # l'angle 3 ne filme pas encore à 1 s
        self.p.marquer()
        mc_d = self.p.d["multicams"][mc]
        mc_d["angles"][1]["decalage"] = 0.5                                  # pour l'essai : l'angle 2 s'arrête à 18,5 s
        c4 = MC.couper_angle(self.p, o + 15.0, 1)                           # la fin du plan (18,5 à 20 s) reste à l'angle 3
        mc_d["angles"][1]["decalage"] = 3.5
        self.assertIsNotNone(c4)
        self.assertEqual([c.get("angle") for c in self.p.clips_piste("video")], [0, 1, 2, 1, 2])
        self.p.annuler()
        v = self.p.clips_piste("video")
        self.assertEqual([c.get("angle") for c in v], [0, 1, 2])
        self.assertTrue(all(abs(fin_clip(a) - b["debut"]) < 1e-3 for a, b in zip(v, v[1:])))
        self.assertTrue(MC.changer_angle(self.p, v[1], 0))                 # clic droit › Changer d'angle
        self.assertEqual(v[1]["media"], self.ms[0]["id"])
        self.p.annuler()
        self.p.annuler()
        self.assertEqual(len(self.p.clips_piste("video")), 0)              # tout revient

    def test_mosaique_proposition_registre(self):
        from app.dialogues_multicam import DialogueMulticam, DialogueMosaique
        dl = DialogueMulticam(self.ed, [m["id"] for m in self.ms[:3]])
        self.assertEqual(dl.angles[0]["media"], self.ms[0]["id"])           # le plus long d'abord
        dl.caler()
        self.assertTrue(attendre(lambda: not dl.tache.isRunning() and dl.angles[1]["methode"] == "son"))
        dl._test_sans_mosaique = True
        dl.creer()
        mc_id = dl.mc_id
        mo = DialogueMosaique(self.ed, mc_id)
        mo.show()
        self.assertTrue(attendre(lambda: not mo.tache.isRunning()))
        o = self.p.clips_piste("video")[0]["origine_mc"]
        self.ed.timeline.aller_a(o + 9.0)
        mo.afficher(o + 9.0)
        self.assertIsNotNone(mo.cases[1].pixmap())
        self.assertTrue(mo.couper(1, o + 9.0))
        self.assertEqual(self.p.clips_piste("video")[-1]["angle"], 1)
        mo._test_oui = True
        mo.proposer()
        v = self.p.clips_piste("video")
        self.assertGreaterEqual(len(v), 2)
        self.assertTrue(all(c.get("multicam") == mc_id for c in v))
        self.assertTrue(all(fin_clip(c) - c["debut"] <= 10.6 or c is v[-1] for c in v))
        mo.close()
        from app import commande_ia as C
        n = C.appliquer([{"action": "changer_angle", "plan": 1, "angle": 1}], self.ed)
        self.assertEqual(self.p.clips_piste("video")[0]["angle"], 0)
        from app import commandes as K
        self.assertIn("multicaméra angle", K.etat(self.p))


if __name__ == "__main__":
    unittest.main()
