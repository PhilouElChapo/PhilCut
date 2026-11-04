"""Montage au rythme : tempo et temps d'une musique de synthèse à 120 BPM, puis coupes calées sur les temps."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
from app import moteur, projet, rythme
from app.projet import fin_clip


class TestRythme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.m = os.path.join(cls.d, "clics.wav")
        expr = ("0.15*sin(2*PI*110*t)+if(lt(mod(t-0.25\\,0.5)\\,0.03)\\,(0.5+0.4*lt(mod(t-0.25\\,2)\\,0.03))"
                "*sin(2*PI*1800*t)\\,0)")
        moteur.lancer(["-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d=20", cls.m])
        cls.v = commun.video_test(cls.d, duree=8, son=False)

    def test_tempo_et_temps(self):
        a = rythme.analyser(self.m)
        self.assertAlmostEqual(a["bpm"], 120, delta=1.5)
        self.assertLess(min(abs(t - 0.25) for t in a["temps"][:3]), 0.05)
        for t in a["forts"][:4]:          # débuts de mesure : 0,25 + 2 k
            self.assertLess(abs(((t - 0.25) % 2.0 + 1.0) % 2.0 - 1.0), 0.06, a["forts"][:4])

    def test_caler_les_coupes(self):
        p = projet.Projet("R", "16:9")
        mv = p.ajouter_media(self.v, moteur.sonder(self.v))
        mm = p.ajouter_media(self.m, moteur.sonder(self.m))
        for d0, f0 in ((0.0, 1.9), (2.0, 3.37), (4.0, 6.1)):      # coupes à 1,9 s, 3,27 s… hors rythme
            p.ajouter_clip(mv["id"], src_debut=d0, src_fin=f0)
        mus = p.ajouter_clip(mm["id"], "audio", 0.0, 0.0, 10.0)
        a = rythme.analyser(self.m)
        n = rythme.caler(p, mus, a)
        self.assertEqual(n, 2)
        grille = rythme.temps_montage(mus, a)
        clips = p.clips_piste("video")
        for c in clips[:-1]:
            self.assertLess(min(abs(fin_clip(c) - g) for g in grille), 0.01)
        for a_, b_ in zip(clips, clips[1:]):               # pas de trou ni de chevauchement
            self.assertAlmostEqual(fin_clip(a_), b_["debut"], places=3)


if __name__ == "__main__":
    unittest.main()
