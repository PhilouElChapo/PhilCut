"""0.9.98 : le Réalisateur (enchaîne tout, s'arrête sur le brouillon et le prix) et son correcteur (défauts relus par l'IA
ou écrits à l'instant, correction proposée avec son prix, deux remarques sur un même élément retenues dans sa fiche)."""
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


def sequence():
    from app import sequence_ia as Q
    seq = Q.nouvelle("16:9")
    seq["personnages"] = [Q.personnage("Pilote", "barbu, lunettes"), Q.personnage("Hôtesse", "uniforme bleu")]
    seq["plans"] = [Q.plan("Le pilote accueille", ["Pilote"], "", 4), Q.plan("L'hôtesse fait monter", ["Hôtesse"], "", 3),
                    Q.plan("Le pilote monte", ["Pilote"], "", 3)]
    return seq


class TestCorrecteur(unittest.TestCase):
    def test_instants(self):
        from app import correcteur as C
        self.assertEqual(C.instant_dans("à 0:12 le pilote n'a plus sa barbe"), 12)
        self.assertEqual(C.instant_dans("vers 1:05,5"), 65.5)
        self.assertEqual(C.instant_dans("à 8 s l'avion change"), 8.0)
        self.assertIsNone(C.instant_dans("le pilote n'a plus sa barbe"))
        seq = sequence()
        self.assertEqual(C.plan_a(seq, 5.0), (1, 1.0))
        self.assertEqual(C.plan_a(seq, 0.0), (0, 0.0))

    def test_remarque_et_element(self):
        from app import correcteur as C
        seq = sequence()
        d = C.remarque(seq, "à 0:08 le pilote n'a plus sa barbe")
        self.assertEqual((d["plan"], d["t"], d["element"], d["source"]), (2, 1.0, "Pilote", "moi"))
        d2 = C.remarque(seq, "l'hôtesse n'a plus son foulard", t_seq=4.5)
        self.assertEqual((d2["plan"], d2["element"]), (1, "Hôtesse"))

    def test_proposer_sans_ia_et_appliquer(self):
        from app import correcteur as C, assistant_creation as A
        seq = sequence()
        for k, pl in enumerate(seq["plans"]):
            pl["fichier"] = f"/tmp/plan{k}.mp4"
        d = C.remarque(seq, "à 0:02 il sourit trop")
        seq["moteur"] = "kling-o3-ref"
        anc = A.demander
        A.demander = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("pas d'IA"))
        try:
            p = C.proposer({"clef_fal": "k"}, seq, d)
        finally:
            A.demander = anc
        self.assertEqual(p["action"], "refaire_plan")
        self.assertEqual(p["plans"], [0])
        self.assertGreater(p["prix"], 0)
        self.assertIn("Prix", C.texte_proposition(p))
        C.appliquer(seq, p)
        self.assertEqual(seq["plans"][0]["fichier"], "")
        self.assertEqual(seq["plans"][1]["fichier"], "/tmp/plan1.mp4")
        self.assertIn("il sourit trop", seq["plans"][0]["precision"])
        self.assertTrue(seq["defauts"][0]["fait"])

    def test_preciser_fiche_refait_les_plans_ou_on_la_voit(self):
        from app import correcteur as C, assistant_creation as A
        seq = sequence()
        seq["personnages"][0]["planche"] = "/tmp/planche.png"
        d = C.remarque(seq, "à 0:01 le pilote n'a plus sa barbe")
        anc = A.demander
        A.demander = lambda *a, **k: {"action": "preciser_fiche", "element": "Pilote", "precision": "full grey beard",
                                      "cause": "la fiche ne montre pas assez la barbe"}
        try:
            p = C.proposer({}, seq, d)
        finally:
            A.demander = anc
        self.assertEqual((p["action"], p["element"], p["plans"]), ("preciser_fiche", "Pilote", [0, 2]))
        C.appliquer(seq, p)
        self.assertIn("full grey beard", seq["personnages"][0]["description"])
        self.assertEqual(seq["personnages"][0]["planche"], "")

    def test_consignes_avec_precision(self):
        from app import sequence_ia as Q
        seq = sequence()
        seq["plans"][0]["precision"] = "keep his grey beard"
        self.assertIn("Important: keep his grey beard", Q.consigne_courte(seq, seq["plans"][0], {}, traduire=False))
        self.assertIn("Important: keep his grey beard", Q.consigne(seq, seq["plans"][0], {}, traduire=False))

    def test_relire(self):
        from app import correcteur as C, assistant_creation as A
        d = tempfile.mkdtemp()
        seq = sequence()
        anc_d = __import__("app.sequence_ia", fromlist=["x"]).dossier
        import app.sequence_ia as Q
        Q.dossier = lambda s: d
        seq["plans"][0]["fichier"] = commun.video_test(d, "p0.mp4", 4)
        anc = A.demander
        A.demander = lambda *a, **k: {"defauts": [{"t": 2.5, "quoi": "visage", "element": "Pilote", "texte": "barbe disparue"}]}
        try:
            r = C.relire({}, seq, 0)
        finally:
            A.demander, Q.dossier = anc, anc_d
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["t_seq"], r[0]["source"]), (2.5, "ia"))
        self.assertFalse(seq["plans"][0]["verdict"]["ok"])

    def test_apprendre(self):
        from app import correcteur as C
        seq = sequence()
        C.remarque(seq, "l'hôtesse n'a plus son foulard", 4.0)
        self.assertEqual(C.a_retenir(seq), [])
        C.remarque(seq, "l'hôtesse a perdu son foulard rouge", 5.0)
        self.assertEqual(C.a_retenir(seq)[0][0], "Hôtesse")


class TestDialogue(unittest.TestCase):
    def _dialogue(self):
        from app.fenetre import Fenetre
        from app import moteur
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        va = commun.video_test(d, "a.mp4", 2)
        ma = ed.projet.ajouter_media(va, moteur.sonder(va))
        ca = ed.projet.ajouter_clip(ma["id"], "video", 0.0)
        return ed, ed.assistant_creation(ca), d

    def test_bibliotheque_prise_par_le_nom(self):
        from app import bibliotheque_creations as B
        from app.cartes_assistant import CarteElement
        ed, dl, _d = self._dialogue()
        B.garder(ed.params, "personnage", "Pilote Maxime", "pilote barbu")
        e = {"type": "personne", "nom": "pilote maxime", "source": "inventer", "description": ""}

        class Carte:
            def __init__(s):
                s.e = e
        dl.cartes = [Carte()]
        self.assertEqual(dl._bibliotheque_auto(), ["Pilote Maxime"])
        self.assertEqual(e["source"], "bibliotheque")

    def test_remarques_et_correction(self):
        from app import correcteur as C
        import app.sequence_ia as Q
        ed, dl, d = self._dialogue()
        anc_d = Q.dossier
        Q.dossier = lambda s: d
        try:
            dl.seq = sequence()
            for k, pl in enumerate(dl.seq["plans"]):
                pl["fichier"] = commun.video_test(d, f"p{k}.mp4", 1)
            dl._remplir_video()
            dl._test_oui = True
            dl.e_remarque.setText("à 0:01 le pilote n'a plus sa barbe")
            dl.ajouter_remarque()
            self.assertEqual(dl.l_defauts.count(), 1)
            dl.e_remarque.setText("à 0:08 le pilote a perdu sa barbe")
            dl.ajouter_remarque()
            self.assertIn("Pilote", dl.seq.get("retenus"))          # deux fois : retenu dans la fiche
            self.assertIn("barbe", dl.seq["personnages"][0]["description"])
            vu = []
            anc_p, anc_f = C.proposer, dl.fabriquer
            C.proposer = lambda params, seq, df, niveau="claude": {"defaut": df["id"], "action": "refaire_plan", "element": "",
                                                                 "precision": "keep the beard", "cause": "c", "plan": df["plan"],
                                                                 "plans": [df["plan"]], "prix": 0.42}
            dl.fabriquer = lambda: vu.append(True)
            try:
                dl.l_defauts.setCurrentRow(0)
                dl.proposer_correction()
                self.assertTrue(attendre(lambda: vu))
            finally:
                C.proposer, dl.fabriquer = anc_p, anc_f
            self.assertEqual(dl.seq["plans"][0]["fichier"], "")
            self.assertIn("keep the beard", dl.seq["plans"][0]["precision"])
        finally:
            Q.dossier = anc_d
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
