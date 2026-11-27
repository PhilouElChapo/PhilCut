"""1.4.0 : registre des commandes (montage courant, pistes, son, repères) piloté par « Dites-le en clair »."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import commandes as K, commande_ia as C, moteur
from app.projet import fin_clip, duree_clip


class TestRegistre(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        self.ed = f.nouveau_projet("16:9")
        self.p = self.ed.projet
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        self.m = self.p.ajouter_media(v, moteur.sonder(v))
        for _ in range(3):
            self.p.ajouter_clip(self.m["id"], "video")
        cs = self.p.clips_piste("video")
        for i, c in enumerate(cs):
            c["nom"] = f"P{i + 1}"
        self.d = duree_clip(cs[0])

    def noms(self, piste="video"):
        return [c["nom"] for c in self.p.clips_piste(piste)]

    def test_declarations(self):
        for n, c in K.REGISTRE.items():
            self.assertIn(c.famille, K.FAMILLES, n)
            self.assertTrue(str(c.libelle) and c.aide.startswith("{"), n)
            self.assertTrue(c.decrire({"plan": 1, "piste": "video", "de": 1, "a": 2, "t": 3, "position": 1, "media": 1, "genre": "video",
                                       "quoi": "muette", "nom": "x", "debut": 1, "volume": 0.5}), n)
        self.assertEqual(set(C.FAMILLES_HISTORIQUES), set(C.ACTIONS))
        self.assertFalse(set(C.ACTIONS) & set(K.REGISTRE))              # déclarée une seule fois
        self.assertIn('"supprimer_plan"', C.consigne())
        self.assertIn("Piste video : 1: P1", K.etat(self.p))

    def test_montage_un_seul_annuler(self):
        avant = self.noms()
        n = C.appliquer([{"action": "changer_ordre", "plan": 3, "position": 1},
                         {"action": "supprimer_plan", "plans": [2]},
                         {"action": "dupliquer_plan", "plan": 1},
                         {"action": "raccourcir_plan", "plan": 3, "fin": self.d / 2}], self.ed)
        self.assertEqual(n, 4)
        self.assertEqual(self.noms(), ["P3", "P3", "P2"])
        cs = self.p.clips_piste("video")
        self.assertAlmostEqual(duree_clip(cs[2]), self.d / 2, places=2)
        self.assertTrue(all(abs(fin_clip(a) - b["debut"]) < 1e-6 for a, b in zip(cs, cs[1:])))   # tout reste collé
        self.p.annuler()
        self.assertEqual(self.noms(), avant)                             # un seul Annuler défait tout

    def test_poser_parties_trous(self):
        C.appliquer([{"action": "ajouter_piste", "genre": "video"},
                     {"action": "poser_media", "media": 1, "piste": "video2", "debut": 1.0}], self.ed)
        self.assertEqual(len(self.p.clips_piste("video2")), 1)
        C.appliquer([{"action": "supprimer_plan", "plans": [2], "refermer": False}], self.ed)
        self.assertGreater(self.p.clips_piste("video")[1]["debut"], self.d + 0.1)
        C.appliquer([{"action": "refermer_trous", "piste": "video"}], self.ed)
        self.assertAlmostEqual(self.p.clips_piste("video")[1]["debut"], self.d, places=3)
        total = self.p.duree()
        C.appliquer([{"action": "retirer_partie", "de": 0.2, "a": 0.6}], self.ed)
        self.assertAlmostEqual(self.p.duree(), total - 0.4, places=2)

    def test_pistes_son_verrou(self):
        C.appliquer([{"action": "regler_piste", "piste": "video", "quoi": "verrou", "etat": True},
                     {"action": "supprimer_plan", "plans": "tous"},
                     {"action": "son_plan", "plans": [1], "volume": 0.5}], self.ed)
        self.assertEqual(len(self.noms()), 3)                            # piste verrouillée : rien n'est touché
        self.assertEqual(C.appliquer.refuses, ["video"])
        C.appliquer([{"action": "regler_piste", "piste": "video", "quoi": "verrou", "etat": False},
                     {"action": "son_plan", "plans": [1], "volume": 0.5, "muet": True, "fondu_sortie": 2},
                     {"action": "renommer_piste", "piste": "musique", "nom": "Fond"},
                     {"action": "aller_a", "t": 0.5}], self.ed)
        c = self.p.clips_piste("video")[0]
        self.assertEqual((c["volume"], c["muet"], c["fondu_sortie"]), (0.5, True, 2.0))
        self.assertEqual(self.p.nom_piste("audio"), "Fond")

    def test_regles_sans_ia(self):
        r = lambda t: C.regles(t)
        self.assertEqual(r("supprime le plan 2"), [{"action": "supprimer_plan", "plans": [2]}])
        self.assertEqual(r("referme les trous")[0]["action"], "refermer_trous")
        self.assertEqual(r("duplique le plan 1"), [{"action": "dupliquer_plan", "plan": 1}])
        self.assertEqual(r("mets le plan 3 en premier"), [{"action": "changer_ordre", "plan": 3, "position": 1}])
        self.assertEqual(r("rends muette la piste musique"), [{"action": "regler_piste", "piste": "audio", "quoi": "muette", "etat": True}])
        self.assertFalse(any(a["action"] == "supprimer_plan" for a in r("supprime l'effet du plan 2")))

    def test_ia_cloud(self):
        from app import ia
        vus = []
        anc = ia.demander, ia.nom_moteur
        ia.demander = lambda params, sysm, texte, **k: (vus.append((sysm, texte)), {"actions": [
            {"action": "supprimer_plan", "plans": [1]}, {"action": "inventee"}]})[1]
        ia.nom_moteur = lambda p: "Claude"
        try:
            res = C.comprendre("enlève le premier plan", self.p, self.ed.params, "cloud", 0.4)
        finally:
            ia.demander, ia.nom_moteur = anc
        self.assertEqual(res["actions"], [{"action": "supprimer_plan", "plans": [1]}])
        self.assertIn("raccourcir_plan", vus[0][0])
        self.assertIn("Ligne rouge : 0.4 s", vus[0][1])
        self.assertIn("Médias : 1:", vus[0][1])


if __name__ == "__main__":
    unittest.main()
