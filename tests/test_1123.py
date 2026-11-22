"""1.1.13 : un plan avec image clef est toujours fait seul (fal refuse « End Image Url » avec plusieurs consignes) ;
reprendre une création en cours après une erreur ou une fermeture."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test1123(unittest.TestCase):
    def test_clef_seule(self):
        from app import sequence_ia as Q
        seq = Q.nouvelle("9:16")
        seq["plans"] = [{"action": f"a{k}", "duree": 3, "personnages": []} for k in range(6)]
        seq["plans"][2]["clef"] = True
        seq["plans"][5]["clef"] = True
        orig = Q.continu_possible
        Q.continu_possible = lambda *a, **k: True
        try:
            g = Q.groupes_continus(seq, list(range(6)), "kling-o3-ref", {})
        finally:
            Q.continu_possible = orig
        self.assertEqual(g, [[0, 1], [2], [3, 4], [5]])

    def test_pas_de_fin_avec_multi(self):
        from app import generateurs_video as GV
        vu = {}
        anc = GV.televerser, GV.attendre_fal, GV.corps_reference
        GV.televerser = lambda cle, ch: "url:" + os.path.basename(ch)
        GV.corps_reference = lambda consigne, duree, f, depart, fin, el, m, son, multi: vu.update(fin=fin) or {}
        GV.attendre_fal = lambda *a, **k: "ok"
        d = tempfile.mkdtemp()
        from PySide6.QtGui import QImage
        im = QImage(600, 600, QImage.Format_RGB32)
        im.fill(0)
        p = os.path.join(d, "f.png")
        im.save(p)
        try:
            GV.generer_reference("k", GV.modele("kling-o3-ref", {}), "c", os.path.join(d, "o.mp4"), 6, "9:16", None, p, [],
                                 multi=[("a", 3), ("b", 3)])
            self.assertIsNone(vu["fin"])
            GV.generer_reference("k", GV.modele("kling-o3-ref", {}), "c", os.path.join(d, "o.mp4"), 3, "9:16", None, p, [],
                                 multi=None)
            self.assertTrue(vu["fin"])
        finally:
            GV.televerser, GV.attendre_fal, GV.corps_reference = anc

    def test_reprendre(self):
        from app.fenetre import Fenetre
        from app import sequence_ia as Q
        from app.dialogues_assistant_creation import DialogueAssistant, P_VIDEO
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("9:16")
        seq = Q.nouvelle("9:16")
        seq.update(assistant=True, histoire="Sur ce tarmac, deux personnes posent devant un avion")
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "p1.mp4", duree=2)
        seq["plans"] = [{"action": "pose", "duree": 3, "personnages": [], "fichier": v},
                        {"action": "décolle", "duree": 3, "personnages": []}]
        Q.enregistrer(seq)
        liste = Q.en_cours()
        self.assertTrue(liste and liste[0][1]["histoire"].startswith("Sur ce tarmac"))
        self.assertIn("2 plans, 1 faits", Q.resume_en_cours(liste[0][1]))
        dl = DialogueAssistant(ed, None)
        dl._test_reprendre = 0
        dl.reprendre_en_cours()
        self.assertEqual(dl.pages.currentIndex(), P_VIDEO)
        self.assertEqual(len(dl.seq["plans"]), 2)
        dl.hide()


if __name__ == "__main__":
    unittest.main()
