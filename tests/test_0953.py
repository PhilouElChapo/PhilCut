"""0.9.53 : séparer voix, musique et bruits (HT-Demucs ONNX) : découpage et raccord des morceaux exacts, trois pistes
qui redonnent le son d'origine, fenêtre (calcul, écoute, pose sous le plan, son d'origine coupé, une seule annulation)."""
import os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
import numpy as np


class FausseSession:
    """Un « modèle » qui rend des parts fixes du mélange : la voix = 40 %, etc."""
    class _E:
        name = "mix"
        shape = [1, 2, 343980]

    def get_inputs(self):
        return [self._E()]

    def run(self, _sorties, entrees):
        b = entrees["mix"]
        return [np.stack([b * 0.1, b * 0.2, b * 0.3, b * 0.4], axis=1)]


class TestCalcul(unittest.TestCase):
    def test_raccords_exacts(self):
        from app import separation as S
        rng = np.random.default_rng(3)
        for n in (1000, S.SEGMENT, S.SEGMENT * 2 + 777):
            son = (rng.standard_normal((2, n)) * 0.1).astype(np.float32)
            st = S.demucs(son, s=FausseSession())
            self.assertEqual(st.shape, (4, 2, n))
            self.assertLess(float(np.abs(st.sum(0) - son).max()), 1e-5)
            self.assertLess(float(np.abs(st[3] - 0.4 * son).max()), 2e-3)      # à la composante continue près

    def test_trois_pistes_sans_perte(self):
        from app import separation as S
        t = np.arange(S.TAUX * 6) / S.TAUX
        voix = (np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 0.7 * t) > 0)).astype(np.float32) * 0.3   # avec des pauses
        bruit = (np.random.default_rng(1).standard_normal(t.size) * 0.02).astype(np.float32)
        stems = np.zeros((4, 2, t.size), np.float32)
        stems[3] = voix + bruit
        stems[2] = bruit
        tr = S.trois_pistes(stems)
        self.assertLess(float(np.abs(tr["voix"] + tr["musique"] + tr["bruits"] - stems.sum(0)).max()), 1e-4)
        self.assertGreater(float(np.abs(tr["bruits"]).mean()), 0.005)            # le souffle continu va aux bruits
        self.assertGreater(float(np.corrcoef(tr["voix"][0], voix)[0, 1]), 0.9)   # la voix reste la voix

    def test_manquant_sans_modele(self):
        from app import separation as S
        self.assertIn("IA locale", S.manquant({}) or "")


class TestFenetre(unittest.TestCase):
    def test_separer_et_poser(self):
        from app import separation as S
        from app.fenetre import Fenetre
        from app.dialogues_separation import DialogueSeparation
        anc = (S.manquant, S.session)
        S.manquant = lambda params=None: None
        S.session = lambda chemin=None, params=None: FausseSession()
        try:
            f = Fenetre([])
            ed = f._editeur_ou_nouveau()
            v = commun.video_test(os.environ["APPDATA"], "sep.mp4", duree=4)
            m = ed.projet.ajouter_media(v, {"duree": 4.0})
            c = ed.projet.ajouter_clip(m["id"])
            c["src_debut"], c["src_fin"] = 1.0, 3.5
            ed.rafraichir()
            d = DialogueSeparation(ed, c)
            self.assertFalse(d.isModal())
            self.assertTrue(d.b_separer.isEnabled())
            d._garder(("musique", "bruits"))                       # « Retirer la voix »
            self.assertEqual(d.gardees(), [])                      # rien tant que ce n'est pas séparé
            d.separer()
            t0 = time.time()
            while time.time() - t0 < 60 and d.resultat is None and d.etat.text()[:1] != "✕":
                app.processEvents()
                time.sleep(0.02)
            self.assertIsNotNone(d.resultat, d.etat.text())
            for k in S.PISTES:
                self.assertTrue(os.path.exists(d.resultat[k]))
            self.assertEqual(d.gardees(), ["musique", "bruits"])
            n_avant = len(ed.projet.clips)
            d.poser()
            nouveaux = [x for x in ed.projet.clips if x.get("separe_de") == c["id"]]
            self.assertEqual(len(nouveaux), 2)
            self.assertTrue(all(abs(x["debut"] - c["debut"]) < 1e-6 for x in nouveaux))
            self.assertTrue(all(abs((x["src_fin"] - x["src_debut"]) - 2.5) < 0.05 for x in nouveaux))
            self.assertEqual(len({x["piste"] for x in nouveaux}), 2)                  # chacune sur sa piste
            self.assertTrue(c["muet"])
            ed.projet.annuler()                                                     # une seule annulation
            self.assertEqual(len(ed.projet.clips), n_avant)
            self.assertFalse(ed.projet.clip(c["id"])["muet"])
            d.close()
            ed.projet.modifie = False
        finally:
            S.manquant, S.session = anc

    def test_menus(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        v = commun.video_test(os.environ["APPDATA"], "sep2.mp4", duree=2)
        m = ed.projet.ajouter_media(v, {"duree": 2.0})
        c = ed.projet.ajouter_clip(m["id"])
        ed.rafraichir()
        vus = []
        ed.timeline._exec_menu = lambda mm, pos: vus.append([a.text() for a in mm.actions()])
        ed.timeline.menu_clip(c, None, 0.5)
        self.assertIn("Séparer voix, musique et bruits…", vus[-1])
        from app import guides as G
        self.assertEqual(next(g for g in G.guides() if g["id"] == "voix_musique")["etat"], "ok")
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
