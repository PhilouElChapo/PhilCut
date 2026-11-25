"""1.3.1 : motion design « look pro » : 3D (Three.js, Rapier, effets), effets pixel (pixelfx), plans (Video ShotCraft),
planche de contrôle des relectures, grille des temps de la musique."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import motion_libre as ML, motion_pro as MP, motion_html as MH


class TestCatalogues(unittest.TestCase):
    def test_pixel(self):
        c = MP.catalogue_pixel()
        self.assertEqual(len(c), 244)
        e = next(x for x in c if x["id"] == "fire/campfire")
        self.assertTrue(e["boucle"])
        self.assertEqual(e["taille"], [128, 128])

    def test_plans(self):
        c = MP.catalogue_plans()
        self.assertGreaterEqual(len(c), 120)
        self.assertTrue(all(p["carte"].startswith("references/shots/") and p["demo"].startswith("demos/") for p in c))
        self.assertTrue(all(len(p["commit"]) == 40 for p in c))

    def test_source_plan_cache(self):
        p = MP.catalogue_plans()[0]
        appels = []
        anc = MP._lire_url
        MP._lire_url = lambda url, delai=40: appels.append(url) or "# carte " + url
        try:
            t1 = MP.source_plan(p["nom"], avec_demo=True)
            t2 = MP.source_plan(p["nom"], avec_demo=True)
        finally:
            MP._lire_url = anc
        self.assertEqual(len(appels), 2)                      # carte et démo, une seule fois
        self.assertEqual(t1, t2)
        self.assertIn(p["commit"], appels[0])
        with self.assertRaises(ValueError):
            MP.source_plan("n-existe-pas")


class TestPreparation(unittest.TestCase):
    def test_lire(self):
        d = {"complexite": 3, "blocs": [], "effets_pixel": ["fire/campfire", "inconnu", "fire/campfire", "a/b", "c/d", "e/f"],
             "plans": ["spotlight-hero-card", "x", "crane-rise-reveal", "basic-3d-scene"]}
        r = MP.lire_preparation(d, set(), noms_pixel={"fire/campfire", "a/b", "c/d", "e/f", "g/h"},
                                noms_plans={"spotlight-hero-card", "crane-rise-reveal", "basic-3d-scene"})
        self.assertEqual(r["pixel"], ["fire/campfire", "a/b", "c/d", "e/f"])
        self.assertEqual(r["plans"], ["spotlight-hero-card", "crane-rise-reveal"])
        self.assertEqual(MP.lire_preparation({}, set())["pixel"], [])

    def test_consigne_de_preparation(self):
        from app import ia
        recu = {}

        def faux(params, consignes, texte, images=None, **k):
            recu["c"] = consignes
            return {"complexite": 2, "effets_pixel": ["fire/campfire"], "plans": ["spotlight-hero-card"]}
        anc, anc_px = ia.demander, MP.pixel_dispo
        ia.demander, MP.pixel_dispo = faux, lambda: True
        try:
            r = MP.preparer({}, {"description": "un feu de camp en pixel art", "moteur_libre": "hyperframes"})
        finally:
            ia.demander, MP.pixel_dispo = anc, anc_px
        self.assertIn("fire/campfire (Campfire)", recu["c"])
        self.assertIn("spotlight-hero-card [opening]", recu["c"])
        self.assertEqual((r["pixel"], r["plans"]), (["fire/campfire"], ["spotlight-hero-card"]))

    def test_ressources(self):
        lib = {"ressources": {"pixel": {"fire/campfire": MP.catalogue_pixel()[12]}, "plans": {"spotlight-hero-card": "# carte"}}}
        t = MP.consigne_ressources(lib, "hyperframes")
        self.assertIn("PFX.effect(id", t)
        self.assertIn("--- spotlight-hero-card ---", t)
        r = MP.consigne_ressources(lib, "remotion")
        self.assertNotIn("PFX.effect", r)                       # pas d'effets pixel en Remotion
        self.assertIn("allowed imports only", r)
        self.assertGreater(MP.prix({"plans": ["a", "b"]}, "claude-sonnet-5-5")["ecrire"],
                           MP.prix({}, "claude-sonnet-5-5")["ecrire"])


class TestComposition(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        for nom, var in (("three-philcut.js", "PHILCUT_THREE_JS"), ("pixelfx-philcut.js", "PHILCUT_PIXELFX_JS")):
            f = os.path.join(self.d, nom)
            open(f, "w").write("/* " + nom + " */")
            os.environ[var] = f

    def tearDown(self):
        os.environ.pop("PHILCUT_THREE_JS", None)
        os.environ.pop("PHILCUT_PIXELFX_JS", None)

    def test_3d_et_pixel(self):
        with open(os.path.join(os.path.dirname(__file__), "exemples", "libre_3d.txt"), encoding="utf-8") as f:
            a = ML.appliquer(ML.fiche("x", (640, 360)), ML.sections(f.read()))
        self.assertTrue(ML.utilise_3d(a))
        self.assertFalse(ML.utilise_pixel(a))
        a["libre"]["js"] += '\nPFX.effect("fire/campfire", {x: 100, y: 300});'
        self.assertTrue(ML.utilise_pixel(a))
        sortie = MH.preparer_projet(a, os.path.join(self.d, "projet"), gsap_en_ligne=True)
        page = open(os.path.join(sortie, "index.html"), encoding="utf-8").read()
        self.assertIn('<script src="assets/three-philcut.js"></script>', page)
        self.assertIn('<script src="assets/pixelfx-philcut.js"></script>', page)
        self.assertLess(page.index("three-philcut.js"), page.index("P3.scene"))
        for f in ("three-philcut.js", "pixelfx-philcut.js"):
            self.assertTrue(os.path.exists(os.path.join(sortie, "assets", f)))
        # sans 3D : rien de chargé
        b = ML.appliquer(ML.fiche("x", (640, 360)), {"js": "tl.to('#scenes', {opacity: 1}, 0)", "duree": "3"})
        page = open(os.path.join(MH.preparer_projet(b, os.path.join(self.d, "p2"), gsap_en_ligne=True), "index.html"),
                    encoding="utf-8").read()
        self.assertNotIn("three-philcut", page)
        # moteur absent : message clair
        os.environ["PHILCUT_THREE_JS"] = os.path.join(self.d, "absent.js")
        with self.assertRaises(MH.ErreurMotion):
            MH.preparer_projet(a, os.path.join(self.d, "p3"), gsap_en_ligne=True)

    def test_consigne_3d(self):
        a = ML.fiche("des cubes qui tombent", (1920, 1080))
        self.assertIn("P3.scene(", ML.consigne(a))
        self.assertNotIn("P3.scene(", ML.consigne(dict(a, avec_3d=False)))
        self.assertNotIn("P3.scene(", ML.consigne(ML.fiche("x", moteur="remotion")))
        os.environ["PHILCUT_THREE_JS"] = os.path.join(self.d, "absent.js")
        self.assertNotIn("P3.scene(", ML.consigne(a))            # pas de 3D tant que le moteur ne l'a pas


class TestPlancheEtMusique(unittest.TestCase):
    def test_planche(self):
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        ims = []
        for k in range(5):
            q = QImage(200, 100, QImage.Format_RGB32)
            q.fill(QColor(40 * k, 80, 120))
            ims.append(os.path.join(d, f"{k}.jpg"))
            q.save(ims[-1])
        plan = [(k, k + 1, "étape") for k in range(5)]
        q = QImage(ML.planche_controle(ims, plan, os.path.join(d, "p.jpg")))
        self.assertEqual((q.width(), q.height()), (3 * 206 + 6, 2 * 106 + 6))     # 3 colonnes, 2 lignes

    def test_grille_des_temps(self):
        a = ML.fiche("x")
        a["musique"] = {"forts": [0.5, 2.5, 4.5], "temps": [0.5, 1.0, 1.5, 2.0, 2.5], "bpm": 120}
        t = ML.musique_consigne(a)
        self.assertIn("Every beat of the grid: 0.5, 1, 1.5, 2, 2.5", t)
        a["musique"] = {"forts": [0.5, 2.5], "bpm": 120}
        self.assertNotIn("Every beat", ML.musique_consigne(a))


if __name__ == "__main__":
    unittest.main()
