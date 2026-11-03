"""FFmpeg : fiche, vignettes, proxys, export complet avec effets, transitions generees, titres ASS, Goodies, musique."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
commun.application()
from app import moteur, projet, export, titres, effets, generateurs


class TestMoteur(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.v = commun.video_test(cls.d)
        cls.m = commun.musique_test(cls.d)

    def test_sonder(self):
        f = moteur.sonder(self.v)
        self.assertEqual(f["genre"], "video")
        self.assertAlmostEqual(f["duree"], 4.0, delta=0.2)
        self.assertEqual(f["video"]["largeur"], 640)
        self.assertEqual(len(f["audio"]), 1)
        self.assertIn("i/s", moteur.resume_fiche(f))

    def test_vignettes_onde_niveaux(self):
        png = moteur.vignettes(self.v, n=6, hauteur=40)
        self.assertTrue(png.startswith(b"\x89PNG"))
        onde = moteur.forme_onde(self.v, 50)
        self.assertEqual(len(onde), 50)
        self.assertGreater(max(onde), 0.1)
        n = moteur.niveaux(self.v)
        self.assertFalse(n["muet"])

    def test_proxy(self):
        p = moteur.proxy(self.v, {"dossier_proxys": self.d})
        self.assertTrue(os.path.exists(p))
        f = moteur.sonder(p)
        self.assertEqual(f["video"]["codec"], "h264")
        self.assertFalse(f["video"]["cadence_variable"])

    def test_export_complet(self):
        p = projet.Projet("Export", "16:9")
        m = p.ajouter_media(self.v, moteur.sonder(self.v))
        mu = p.ajouter_media(self.m, moteur.sonder(self.m))
        c1 = p.ajouter_clip(m["id"])
        p.couper(c1["id"], 2.0)
        c2 = p.clips[1]
        c2["vitesse"] = 0.5
        c1["effets"] = [{"id": "glow", "params": {}}, {"id": "feu_artifice", "params": {"quantite": 2}}, {"id": "ciel_altitude", "params": {}}]
        c2["transition"] = {"id": "t_puzzle", "params": {"duree": 0.8}}
        c2["effets"] = [{"id": "glitch", "params": {}}]
        c2["effets_audio"] = ["a_voix"]
        p.ajouter_clip(mu["id"], "audio", 0.0, 0, 6)
        p.ajouter_titre("Survol", 0.5, 3.0, animation="neon")
        p.ajouter_titre("le Pilote", 1, 4, style="etiquette", suivi={"positions": [(1, 0.3, 0.4), (2, 0.5, 0.5)]})
        p.ajouter_goodie("altimetre", 0, 5, valeurs=[(0, 0), (5, 2500)])
        out, journal = export.exporter(p, os.path.join(self.d, "out.mp4"), "whatsapp", progression=lambda x: None,
                                       sous_titres=[(0.5, 2.0, "Bonjour")])
        f = moteur.sonder(out)
        self.assertAlmostEqual(f["duree"], 6.0, delta=0.3)
        self.assertEqual(f["video"]["largeur"], 1280)
        self.assertEqual(len(f["audio"]), 1)
        self.assertEqual(journal, [])

    def test_export_vertical_fond_flou(self):
        p = projet.Projet("V", "9:16")
        m = p.ajouter_media(self.v, moteur.sonder(self.v))
        c = p.ajouter_clip(m["id"], src_fin=2)
        c["ajustement"] = "contenir_flou"
        c["transition"] = {"id": "t_zoom", "params": {}}
        out, _j = export.exporter(p, os.path.join(self.d, "v.mp4"), "insta")
        f = moteur.sonder(out)
        self.assertEqual((f["video"]["largeur"], f["video"]["hauteur"]), (1080, 1920))

    def test_filtres_effets(self):
        ctx = {"cadence": 30, "largeur": 1920, "hauteur": 1080, "duree": 3}
        for k in effets.CATALOGUE:
            e = {"id": k, "params": effets.defauts(k)}
            f = effets.filtre(e, ctx)
            if k in effets.GENERES:
                self.assertIsNone(f, k)
            elif k not in ("double_exposition", "chroma_key", "detourage"):
                self.assertTrue(f, k)

    def test_ass(self):
        t = titres.ass([{"texte": "Test", "debut": 0, "fin": 2, "animation": "machine", "x": 0.5, "y": 0.5}], 1920, 1080, 30, [(0, 1, "st")])
        self.assertIn("[Events]", t)
        self.assertIn("SousTitre", t)
        self.assertIn("\\alpha", t)
        srt = titres.srt([(0, 1.5, "a"), (2, 3, "b")])
        self.assertEqual(len(titres.lire_srt(srt)), 2)

    def test_generateurs(self):
        if generateurs.cv2 is None:
            self.skipTest("OpenCV absent")
        d = tempfile.mkdtemp()
        motif, n = generateurs.pluie_code(d, 320, 180, 10, 1.0)
        self.assertEqual(n, 10)
        self.assertTrue(os.path.exists(motif % 0))
        motif, n = generateurs.feu_artifice(d, 320, 180, 10, 1.0, 2)
        self.assertEqual(n, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
