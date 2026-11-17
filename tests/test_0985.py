"""0.9.85 : suivi précis par le cloud (SAM 3 sur fal.ai) pour les zones et les Goodies accrochés ; la boîte du sujet est
retrouvée en comparant la vidéo rendue à l'origine, que SAM colore le sujet ou efface le reste."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def carre_mobile(d, duree=2.0):
    """Fond gris, carré blanc qui va de gauche à droite."""
    from app import moteur
    ch = os.path.join(d, "carre.mp4")
    moteur.lancer(["-y", "-f", "lavfi", "-i", f"color=c=gray:s=640x360:r=30:d={duree}", "-f", "lavfi", "-i", f"color=c=white:s=80x80:r=30:d={duree}",
                   "-filter_complex", "[0][1]overlay=x='40+t*200':y=140", "-c:v", "libx264", "-pix_fmt", "yuv420p", ch])
    return ch


class TestSuiviCloud(unittest.TestCase):
    def test_boites_deux_modes(self):
        import numpy as np
        from app import suivi_cloud as SC
        orig = np.full((3, 40, 80, 3), 120, np.int16)
        for i in range(3):
            orig[i, 10:20, 10 + i * 20:20 + i * 20] = 250
        efface = np.where(orig > 200, orig, 0)                      # SAM efface le reste
        colore = orig.copy()
        colore[orig > 200] = 0                                     # SAM colore le sujet
        for rendu in (efface, colore):
            b = SC.boites(orig, rendu, (15 / 80, 15 / 40))
            self.assertEqual(len(b), 3)
            self.assertLess(b[0][0], b[2][0])                       # le sujet va vers la droite
            self.assertAlmostEqual(b[2][0], 55 / 80, delta=0.06)
        self.assertEqual(SC.prix(10), 0.05)

    def test_zone_suivie_par_le_cloud(self):
        from app import generateurs_video as GV, moteur, zones as Z
        from app.fenetre import Fenetre
        d = tempfile.mkdtemp()
        v = carre_mobile(d)
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_fal="id:secret")
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.projet.ajouter_clip(m["id"], "video", 0.0)
        z = Z.nouvelle(0.0, 2.0, 0.125, 0.5, 0.15, 0.25) if hasattr(Z, "nouvelle") else None
        if z is None:
            self.skipTest("zones.nouvelle absente")
        ed.projet.goodies.append(z)
        envoye = {}

        def faux_televerser(cle, chemin):
            envoye.setdefault("fichiers", []).append(chemin)
            return "http://faux/" + os.path.basename(chemin)

        def faux_demande(cle, point, corps, progression=None, arret=None, attente=0):
            envoye["corps"] = corps
            return {"video": {"url": "http://faux/rendu.mp4"}}

        def faux_telecharger(url, sortie):              # « SAM » : seul le carré blanc reste, le fond devient noir
            src = envoye["fichiers"][-1]
            moteur.lancer(["-y", "-i", src, "-vf", "geq=r='if(gt(r(X,Y),200),r(X,Y),0)':g='if(gt(g(X,Y),200),g(X,Y),0)':"
                           "b='if(gt(b(X,Y),200),b(X,Y),0)'", "-c:v", "libx264", "-pix_fmt", "yuv420p", sortie])
            return sortie
        anc = (GV.televerser, GV.demande_fal, GV.telecharger)
        GV.televerser, GV.demande_fal, GV.telecharger = faux_televerser, faux_demande, faux_telecharger
        try:
            Z.suivre_zone(ed.projet, z, methode="cloud", params=ed.params)
        finally:
            GV.televerser, GV.demande_fal, GV.telecharger = anc
        self.assertEqual(envoye["corps"]["point_prompts"][0]["label"], 1)
        pos = z["suivi"]["positions"]
        self.assertGreater(len(pos), 5)
        self.assertEqual(z["suivi"]["methode"], "cloud")
        self.assertLess(pos[0][1], pos[-1][1] - 0.3)                 # la zone a suivi le carré vers la droite


if __name__ == "__main__":
    unittest.main()
