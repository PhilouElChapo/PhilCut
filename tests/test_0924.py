"""0.9.24 : prolonger un plan trop court (image tenue, ralenti), regardé avant d'être posé ; la suite est décalée."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur


class Test0924(unittest.TestCase):
    def test_prolonger(self):
        from app import prolonger as PR
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        a = commun.video_test(d, "a.mp4", duree=3)
        b = commun.video_test(d, "b.mp4", duree=2)
        ma = ed.projet.ajouter_media(a, moteur.sonder(a))
        mb = ed.projet.ajouter_media(b, moteur.sonder(b))
        ca = ed.projet.ajouter_clip(ma["id"], "video", 0.0, 0.0, 3.0)
        cb = ed.projet.ajouter_clip(mb["id"], "video", 3.0, 0.0, 2.0)
        ed.projet.ajouter_titre("Titre", 3.5, 4.5)
        w = os.path.join(d, "x")
        for methode in ("tenue", "ralenti"):
            r = PR.fabriquer(ma, ca, 1.5, methode, "fin", "ambiance", taille=(640, 360), cadence=30, sortie=f"{w}_{methode}.mp4")
            info = moteur.sonder(r)
            self.assertAlmostEqual(info["duree"], 1.5, delta=0.15, msg=methode)
            self.assertTrue(info["audio"], methode)
            self.assertEqual((info["video"]["largeur"], info["video"]["hauteur"]), (640, 360))
        r = PR.fabriquer(ma, ca, 1.0, "tenue", "debut", "silence", taille=(640, 360), sortie=f"{w}_debut.mp4")
        self.assertAlmostEqual(moteur.sonder(r)["duree"], 1.0, delta=0.15)
        # dans la fenêtre : on fabrique, on regarde, on pose
        from app.dialogues_prolonger import DialogueProlonger
        dl = DialogueProlonger(ed, ca)
        dl.duree.setValue(2.0)
        dl.fabriquer()
        import time
        t0 = time.time()
        while dl.tache.isRunning() and time.time() - t0 < 60:
            app.processEvents()
            time.sleep(0.05)
        for _i in range(20):
            app.processEvents()
        self.assertTrue(dl.b_poser.isEnabled(), dl.etat.text())
        self.assertEqual(len(ed.projet.clips_piste("video")), 2)                 # rien n'est posé avant d'avoir regardé
        ci = dl.poser()
        self.assertAlmostEqual(ci["debut"], 3.0, places=2)
        self.assertAlmostEqual(cb["debut"], 5.0, delta=0.1)                       # la suite est décalée
        self.assertAlmostEqual(ed.projet.titres[0]["debut"], 5.5, delta=0.1)
        ed.projet.annuler()
        self.assertEqual(len(ed.projet.clips_piste("video")), 2)
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
