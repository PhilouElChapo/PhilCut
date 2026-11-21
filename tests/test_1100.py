"""1.1.0 : animation libre : décrite en phrases, écrite par l'IA en composition HyperFrames, vérifiée, aperçue, corrigée."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

REPONSE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "exemples", "libre_anniversaire.txt"), encoding="utf-8").read()


class TestLogique(unittest.TestCase):
    def test_sections_et_regles(self):
        from app import motion_libre as ML
        s = ML.sections(REPONSE)
        self.assertEqual(s["titre"], "40 ans")
        self.assertIn("tl.to", s["js"])
        self.assertEqual(ML.verifier_code(s["js"], s["html"]), [])
        self.assertTrue(ML.verifier_code("const x = Math.random(); setTimeout(f, 3); tl.to(a, {repeat: -1}, 0)"))
        with self.assertRaises(ValueError):
            ML.sections("pas de sections")
        self.assertEqual(ML.sections("```\n===JS===\ntl.set({}, {}, 1);\n```")["js"], "tl.set({}, {}, 1);")

    def test_composition(self):
        from app import motion_libre as ML, motion_html as MH
        a = ML.appliquer(ML.fiche("un cadeau", (1080, 1920), transparent=True), ML.sections(REPONSE))
        self.assertEqual(a["duree"], 9.0)
        h = MH.composition(a, "gsap.min.js", (), "")
        for x in ('data-composition-id="philcut"', 'data-duration="9"', "const W = 1080, H = 1920", "TRANSPARENT = true",
                  'window.__timelines["philcut"] = tl', "tl.set({}, {}, D)", "const alea"):
            self.assertIn(x, h)
        self.assertIn("background: transparent", h)
        b = ML.apercu_leger(a)
        self.assertEqual((b["taille"], b["cadence"]), ([540, 960], 15))
        d = tempfile.mkdtemp()
        MH.preparer_projet(a, d)
        self.assertTrue(os.path.exists(os.path.join(d, "index.html")))

    def test_corriger_garde_l_historique(self):
        from app import ia, motion_libre as ML
        a = ML.appliquer(ML.fiche("x"), ML.sections(REPONSE))
        recu = {}

        def faux(params, consignes, texte, images=None, json_attendu=False, max_jetons=4000):
            recu["t"] = texte
            return REPONSE.replace("40 ans", "40 ans bis")
        anc = ia.demander
        ia.demander = faux
        try:
            b = ML.corriger({}, a, remarque="le cadeau plus grand")
        finally:
            ia.demander = anc
        self.assertIn("le cadeau plus grand", recu["t"])
        self.assertIn("===JS===", recu["t"])
        self.assertEqual(b["titre"], "40 ans bis")
        self.assertEqual(len(b["libre"]["historique"]), 1)
        self.assertEqual(ML.revenir(b)["libre"]["js"], a["libre"]["js"])
        a2 = dict(a, duree=5, duree_imposee=True)
        self.assertEqual(ML.appliquer(a2, ML.sections(REPONSE))["duree"], 5)


class TestSynchro(unittest.TestCase):
    def test_fichier_supprime_ici_n_est_plus_propose(self):
        """1.1.1 : un fichier supprimé sur ce poste (déjà envoyé) ne revient plus à chaque ouverture en « à recevoir »."""
        from app import distant, miroir
        r = distant.nouveau_compte("reseau")
        r["adresse"] = tempfile.mkdtemp()
        params = {"comptes": [r], "drive_compte": r["id"]}
        local = os.path.join(miroir.dossier_miroir(r), "PhilCut", "creations_partagees", "personnage", "x")
        os.makedirs(local, exist_ok=True)
        f = os.path.join(local, "image1.png")
        with open(f, "wb") as fic:
            fic.write(b"png")
        miroir.synchroniser(params, r)
        os.remove(f)
        for _i in range(2):
            plan = []
            miroir.synchroniser(params, r, plan=plan)
            self.assertFalse([x for x in plan if x["rel"].endswith("image1.png")], plan)
            miroir.synchroniser(params, r)
        self.assertFalse(os.path.exists(f))


class TestFenetre(unittest.TestCase):
    def test_creer_sans_moteur_local(self):
        from app import ia, motion_html as MH
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("9:16")
        dl = ed.animation_libre()
        dl._test_oui = True
        self.assertEqual(dl.format.currentData(), (1080, 1920))
        self.assertFalse(dl.b_corriger.isEnabled())
        dl.description.setPlainText("un cadeau qui grandit jusqu'à 40")
        anc, anc_l = ia.demander, MH.local_pret
        ia.demander = lambda *a, **k: REPONSE
        MH.local_pret = lambda: False
        try:
            dl.creer()
            dl.tache.wait(20000)
            for _ in range(30):
                app.processEvents()
        finally:
            ia.demander, MH.local_pret = anc, anc_l
        self.assertEqual(dl.anim["titre"], "40 ans")
        self.assertIn("40 ans", dl.message.text())
        self.assertTrue(dl.b_corriger.isEnabled())
        self.assertTrue(dl.b_installer.isVisible() or not dl.isVisible())
        d = dl.ouvrir_projet()
        self.assertTrue(os.path.exists(os.path.join(d, "index.html")))
        ed.projet.modifie = False

    def test_menu(self):
        from app.fenetre import Fenetre
        from PySide6.QtWidgets import QMenu
        f = Fenetre()
        m = QMenu()
        f.remplir_fabrique(m)
        textes = []
        for a in m.actions():
            if a.menu():
                textes += [b.text() for b in a.menu().actions()]
        self.assertIn("Animation libre : décrivez-la, l'IA la construit…", textes)


if __name__ == "__main__":
    unittest.main()
