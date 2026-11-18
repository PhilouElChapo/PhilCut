"""0.9.96 : retours du premier vrai essai (18/11 au soir) : plans Kling de plus de 512 caractères (422), « Réponse de l'IA
illisible » (réflexion de Gemini qui mangeait la réponse), images préparées perdues après une erreur, détourage
approximatif, nom pas tout de suite modifiable, dépenses du mois."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestKling(unittest.TestCase):
    def test_plans_de_512_au_plus(self):
        from app import generateurs_video as GV
        m = GV.modele("kling-o3-ref", {})
        el = [{"nom": f"Character {c}", "frontal_image_url": "u"} for c in "ACDE"]
        long = "Cinematic shot, vertical 9:16, about 6 seconds. " + "Character A wears a navy uniform with gold stripes. " * 20
        c = GV.corps_reference("x", 9, "9:16", None, None, el, m, False, multi=[(long, 4), ("Action: they walk.", 5)])
        for p in c["multi_prompt"]:
            self.assertLessEqual(len(p["prompt"]), 512)
            self.assertIn("@Element1=Character A", p["prompt"])
        self.assertTrue(c["multi_prompt"][0]["prompt"].rstrip().endswith("references."))

    def test_consigne_courte_commence_par_l_action(self):
        from app import sequence_ia as Q
        seq = Q.nouvelle("9:16")
        seq["personnages"] = [Q.personnage("Pilote", "très longue description " * 30)]
        pl = Q.plan("Pilote accueille les passagères", ["Pilote"], "", 4)
        seq["plans"] = [pl]
        t = Q.consigne_courte(seq, pl, {}, traduire=False)
        self.assertTrue(t.startswith("Action: Character A accueille"))
        self.assertLess(len(t), 400)


class TestJson(unittest.TestCase):
    def test_reparer(self):
        from app.ia import lire_json, reparer_json
        self.assertEqual(lire_json('{"a": [1, 2,],}'), {"a": [1, 2]})
        self.assertEqual(reparer_json('{"cartes": [{"nom": "x"}, {"nom": "y", "de'), {"cartes": [{"nom": "x"}, {"nom": "y"}]})
        self.assertIsNone(reparer_json("pas de json"))

    def test_gemini_laisse_la_place_a_la_reflexion(self):
        from app import ia
        vu = {}

        def faux(url, corps, *a, **k):
            vu.update(corps)
            return {"candidates": [{"content": {"parts": [{"text": "je réfléchis", "thought": True}, {"text": '{"texte": "ok"}'}]},
                                    "finishReason": "STOP"}]}
        anc, anc_m = ia._http, ia._modele_gemini
        ia._http, ia._modele_gemini = faux, lambda *a: "gemini-test"
        try:
            r = ia._gemini("k", {}, "c", "t", None, 700, True)
        finally:
            ia._http, ia._modele_gemini = anc, anc_m
        self.assertGreaterEqual(vu["generationConfig"]["maxOutputTokens"], 700 + 8000)
        self.assertEqual(r, '{"texte": "ok"}')                 # la réflexion n'est pas mêlée à la réponse


class TestDecoupe(unittest.TestCase):
    def test_objet_jamais_detoure(self):
        from app import assistant_creation as A
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        im = QImage(400, 300, QImage.Format_RGB32)
        im.fill(QColor("#336699"))
        src = os.path.join(d, "a.png")
        im.save(src)
        vu = []
        anc = A.detourer_decoupe
        A.detourer_decoupe = lambda *a, **k: vu.append(a) or True
        try:
            A.decouper(src, (0.2, 0.2, 0.6, 0.6), os.path.join(d, "o.png"), personne=False)
            self.assertEqual(vu, [])
            A.decouper(src, (0.2, 0.2, 0.6, 0.6), os.path.join(d, "p.png"))
            self.assertEqual(len(vu), 1)
        finally:
            A.detourer_decoupe = anc

    def test_sans_modele_pas_de_detourage(self):
        from app import assistant_creation as A
        d = tempfile.mkdtemp()
        f = os.path.join(d, "x.png")
        from PySide6.QtGui import QImage
        QImage(64, 64, QImage.Format_RGB32).save(f)
        if not A.detourage_local_possible():
            self.assertFalse(A.detourer_decoupe(f))

    def test_isoler_par_gemini(self):
        from app import assistant_creation as A, ia
        d = tempfile.mkdtemp()
        f = os.path.join(d, "x.png")
        open(f, "wb").write(b"avant")
        vu = []
        anc = ia.retoucher_image
        ia.retoucher_image = lambda p, o, c, *a, **k: vu.append(c) or b"apres"
        try:
            A.isoler_gemini(f, "object", {"clef_gemini": "g"})
        finally:
            ia.retoucher_image = anc
        self.assertEqual(open(f, "rb").read(), b"apres")
        self.assertIn("plain pure white background", vu[0])


class TestDepenses(unittest.TestCase):
    def test_compte_du_mois(self):
        from app import credit_ia as C
        avant = C.depense_du_mois("fal")
        C.noter_depense("fal", 1.25)
        self.assertAlmostEqual(C.depense_du_mois("fal"), avant + 1.25, places=3)
        self.assertIn("dépensé ce mois", C.texte_court("fal", None))
        self.assertIn("ADMIN", C.texte_credit("fal", None))


class TestNouveau(unittest.TestCase):
    def test_nom_pret_a_ecrire(self):
        from PySide6.QtWidgets import QWidget
        from app.dialogues_bibliotheque_creations import DialogueBibliothequeCreations
        import time
        ed = QWidget()
        ed.params = {}
        d = DialogueBibliothequeCreations(ed)
        d.show()
        d.nouveau("objet")
        fin = time.time() + 1
        while time.time() < fin:
            app.processEvents()
        self.assertEqual(d.nom.selectedText(), d.nom.text())


if __name__ == "__main__":
    unittest.main()
