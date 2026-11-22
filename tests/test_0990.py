"""0.9.90 : séquences continues. Les plans d'un même moment (jusqu'à la prochaine image clef, 15 s au plus) se font d'un
seul calcul Kling O3 (multi_prompt) : les gestes s'enchaînent, puis la vidéo est coupée en ses plans."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=60):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


def sequence(durees, clefs=()):
    from app import sequence_ia as Q
    seq = Q.nouvelle("16:9")
    seq["plans"] = [Q.plan(f"action {i + 1}", [], "", d) for i, d in enumerate(durees)]
    for i in clefs:
        seq["plans"][i]["clef"] = True
    return seq


class TestCorps(unittest.TestCase):
    def test_multi_prompt(self):
        from app import generateurs_video as GV
        m = GV.modele("kling-o3-ref", {})
        self.assertTrue(m.get("multi"))
        el = [{"nom": "Character A", "frontal_image_url": "u1"}]
        c = GV.corps_reference("x", 9, "16:9", "dep", "fin", el, m, False, multi=[("walks", 4), ("sits", 5)])
        self.assertNotIn("prompt", c)
        self.assertEqual([x["duration"] for x in c["multi_prompt"]], ["4", "5"])
        self.assertEqual(c["duration"], "9")
        self.assertEqual(c["shot_type"], "customize")
        self.assertTrue(all("@Element1=Character A" in x["prompt"] and "identical" in x["prompt"] for x in c["multi_prompt"]))
        self.assertEqual((c["start_image_url"], c["end_image_url"]), ("dep", "fin"))
        c1 = GV.corps_reference("x", 5, "16:9", m=m)
        self.assertIn("prompt", c1)
        self.assertNotIn("multi_prompt", c1)


class TestGroupes(unittest.TestCase):
    def test_jusqu_a_l_image_clef(self):
        from app import sequence_ia as Q
        seq = sequence([4, 4, 4, 4, 4], clefs=[2])
        g = Q.groupes_continus(seq, range(5), "kling-o3-ref", {})
        self.assertEqual(g, [[0, 1], [2], [3, 4]])          # 1.1.13 : le plan clef est fait seul (fal 422)

    def test_quinze_secondes_au_plus(self):
        from app import sequence_ia as Q
        seq = sequence([6, 6, 6, 3])
        self.assertEqual(Q.groupes_continus(seq, range(4), "kling-o3-ref", {}), [[0, 1], [2, 3]])

    def test_plan_par_plan(self):
        from app import sequence_ia as Q
        seq = sequence([4, 4, 4])
        self.assertEqual(Q.groupes_continus(seq, range(3), "kling-o3-ref", {"sequence_continue": False}), [[0], [1], [2]])
        self.assertEqual(Q.groupes_continus(seq, range(3), "locale", {}), [[0], [1], [2]])
        seq["plans"][1]["enchainer"] = False
        self.assertEqual(Q.groupes_continus(seq, range(3), "kling-o3-ref", {}), [[0], [1, 2]])

    def test_image_de_depart_a_lui_coupe(self):
        from app import sequence_ia as Q
        d = tempfile.mkdtemp()
        img = os.path.join(d, "i.png")
        with open(img, "wb") as o:
            o.write(b"x")
        seq = sequence([4, 4, 4])
        seq["plans"][2]["image"] = img
        self.assertEqual(Q.groupes_continus(seq, range(3), "kling-o3-ref", {}), [[0, 1], [2]])
        self.assertEqual(Q.groupes_continus(seq, [0, 2], "kling-o3-ref", {}), [[0], [2]])     # le plan 2 déjà fait

    def test_fabriquer_et_couper(self):
        from app import sequence_ia as Q, generateurs_video as GV, moteur
        d = tempfile.mkdtemp()
        seq = sequence([2, 3, 2], clefs=[2])
        anc_dossier = Q.dossier
        Q.dossier = lambda s: d
        vu = {}
        fin = os.path.join(d, "clef.png")
        with open(fin, "wb") as o:
            o.write(b"x")

        def faux_generer(params, ident, consigne, sortie, duree=5, format_="16:9", image=None, progression=None,
                         arret=lambda: False, son=False, references=None, image_fin=None, multi=None):
            vu.update(duree=duree, multi=multi, fin=image_fin)
            v = commun.video_test(d, "groupe.mp4", duree)
            os.replace(v, sortie)
            return sortie
        anc, anc_arr = GV.generer, Q.image_arrivee
        GV.generer = faux_generer
        Q.image_arrivee = lambda s, i, prm, dep=None, prec="": (s["plans"][i].__setitem__("image_fin", fin), fin)[1]
        try:
            fichiers = Q.fabriquer_groupe(seq, [0, 1, 2], {"clef_gemini": "g"}, "kling-o3-ref")
        finally:
            GV.generer, Q.image_arrivee, Q.dossier = anc, anc_arr, anc_dossier
        self.assertEqual(vu["duree"], 7)
        self.assertEqual([x[1] for x in vu["multi"]], [2, 3, 2])
        self.assertEqual(vu["fin"], fin)                          # l'image clef du dernier plan est l'arrivée
        self.assertEqual(len(fichiers), 3)
        durees = [float(moteur.sonder(f)["duree"]) for f in fichiers]
        for vrai, voulu in zip(durees, [2, 3, 2]):
            self.assertAlmostEqual(vrai, voulu, delta=0.35)
        g = {p.get("groupe") for p in seq["plans"]}
        self.assertEqual(len(g), 1)
        self.assertEqual(Q.plans_du_groupe_apres(seq, 1), [1, 2])


class TestAssistant(unittest.TestCase):
    def test_fabrication_par_moment(self):
        from app.fenetre import Fenetre
        from app import moteur, assistant_creation as A, sequence_ia as Q
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_fal="k")
        d = tempfile.mkdtemp()
        va = commun.video_test(d, "a.mp4", 2)
        ma = ed.projet.ajouter_media(va, moteur.sonder(va))
        ca = ed.projet.ajouter_clip(ma["id"], "video", 0.0)
        dl = ed.assistant_creation(ca)
        dl.seq = sequence([4, 4, 4, 4], clefs=[1])
        dl.seq["moteur"] = "kling-o3-ref"
        appels = []

        def faux(seq, groupe, params, moteur_video, progression=None, arret=lambda: False):
            appels.append(list(groupe))
            out = []
            for j in groupe:
                v = commun.video_test(d, f"p{j}_{len(appels)}.mp4", 1)
                seq["plans"][j]["fichier"] = v
                if len(groupe) > 1:
                    seq["plans"][j]["groupe"] = "g" + str(len(appels))
                out.append(v)
            return out
        anc, anc_v = Q.fabriquer_groupe, A.verifier
        Q.fabriquer_groupe, A.verifier = faux, lambda *a, **k: {"ok": True}
        try:
            dl.fabriquer()
            self.assertTrue(attendre(lambda: not dl.file and not dl._en_calcul() and dl._plan_en_cours == -1
                                     and all(p.get("fichier") for p in dl.seq["plans"])))
            self.assertEqual(appels, [[0], [1], [2, 3]])        # 1.1.13 : le plan clef est fait seul
            self.assertIn("⛓", dl._texte_plan(2))
            self.assertNotIn("⛓", dl._texte_plan(1))
            dl.l_plans.setCurrentRow(2)
            dl._test_precision = ""
            dl.refaire_plan()                                 # le plan 3 et le 4, du même calcul
            self.assertTrue(attendre(lambda: len(appels) == 4 and not dl._en_calcul()))
            self.assertEqual(appels[-1], [2, 3])
        finally:
            Q.fabriquer_groupe, A.verifier = anc, anc_v


if __name__ == "__main__":
    unittest.main()
