"""1.0.0 : sous-titres animés, habillage (bandeau, barre de progression, capture qui défile) et animations calées sur la voix
ou la musique, pour les trois moteurs (horaire commun)."""
import json, os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

MOTS = [[0.2, 0.5, "Aujourd'hui"], [0.5, 0.7, "on"], [0.7, 1.0, "parle"], [1.0, 1.2, "de"], [1.2, 1.7, "motion"],
        [1.7, 2.1, "design."], [3.2, 3.5, "Ensuite"], [3.5, 3.9, "les"], [3.9, 4.4, "chiffres"]]


def attendre(cond, s=120):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestHoraire(unittest.TestCase):
    def test_defaut(self):
        from app import motion as M
        h = M.horaire(M.nouvelle("chiffres"))
        self.assertEqual(h["scenes"]["barres"], [4.0, 9.4])
        self.assertAlmostEqual(h["compteur"]["fin"], 2.6)
        a = M.nouvelle("chiffres")
        a["reglages"]["vitesse"] = 2.0
        self.assertAlmostEqual(M.horaire(a)["compteur"]["fin"], 1.3)

    def test_voix(self):
        from app import motion as M
        a = M.nouvelle("chiffres")
        mots = [[3.0, 3.6, "34"], [3.6, 4.0, "390"], [3.0, 3.8, "34390"], [5.0, 5.4, "janvier"], [6.0, 6.4, "février"],
                [11, 11.5, "record"]]
        h, n = M.caler_voix(a, mots)
        self.assertGreaterEqual(n, 4)
        self.assertAlmostEqual(h["compteur"]["fin"], 3.25)
        self.assertEqual(h["barres"]["entrees"][:2], [5.0, 6.0])
        self.assertGreater(h["barres"]["entrees"][2], 6.0)          # « mars » pas dit : juste après février
        self.assertGreaterEqual(h["courbe"]["record"], h["courbe"]["debut"])
        self.assertTrue(M._nombre_dit("34 000", 34390))
        self.assertFalse(M._nombre_dit("12", 34390))

    def test_musique(self):
        from app import motion as M
        a = M.nouvelle("barres")
        h, n = M.caler_musique(a, [i * 0.5 for i in range(20)], [i * 2.0 for i in range(5)])
        self.assertGreater(n, 3)
        e = h["barres"]["entrees"]
        self.assertTrue(all(abs((x / 0.5) - round(x / 0.5)) < 1e-6 for x in e))
        self.assertEqual(len(e), len(a["donnees"]))

    def test_lignes_et_mots(self):
        from app import motion as M
        l = M.lignes_st(MOTS)
        self.assertEqual(len(l), 3)                                    # longueur, puis le point et la pause
        self.assertEqual(l[-1]["mots"][0][2], "Ensuite")
        self.assertTrue(all(len(" ".join(m[2] for m in x["mots"])) <= 28 for x in l))
        mm = [{"t0": 10 + a, "t1": 10 + b, "mot": w} for a, b, w in MOTS]
        r = M.mots_dans(mm, 10.0, 2.0)
        self.assertEqual(r[0], [0.2, 0.5, "Aujourd'hui"])
        self.assertTrue(all(x[1] <= 2.0 for x in r))


class TestRendus(unittest.TestCase):
    def test_maison(self):
        from app import motion as M, motion_maison as MM
        d = tempfile.mkdtemp()
        for g in ("sous_titres", "bandeau", "progression", "defilement"):
            a = M.preparer_genre(M.nouvelle("compteur", taille=(320, 180)), g)
            a.update(duree=1.5, mots=MOTS, chapitres=[[0, "Intro"], [1, "Suite"]], image="")
            for st in (["surligne", "saute", "un_mot", "karaoke"] if g == "sous_titres" else [None]):
                if st:
                    a["style_st"] = st
                img = MM.apercu_image(a, 1.3, (320, 180))
                self.assertEqual(img.width(), 320)
            f = MM.fabriquer(a, os.path.join(d, g + ".mp4"))
            self.assertTrue(f.endswith(".mov" if a["transparent"] else ".mp4"), g)

    def test_html_et_remotion(self):
        from app import motion as M, motion_html as MH, motion_remotion as MR
        a = M.preparer_genre(M.nouvelle("compteur"), "sous_titres")
        a["mots"] = MOTS
        h = MH.composition(a)
        A = json.loads(h.split("const A = ")[1].split(";\nconst tl")[0])
        self.assertEqual(len(A["lignes_st"]), 3)                       # en 16:9, lignes de 32 caractères au plus
        self.assertIn("function sous_titres", h)
        self.assertEqual(A["horaire"]["scenes"], {"sous_titres": [0, 10.0]})
        b = M.nouvelle("chiffres")
        b["horaire"], _n = M.caler_voix(b, [[3.0, 3.8, "34390"]])
        A = json.loads(MH.composition(b).split("const A = ")[1].split(";\nconst tl")[0])
        self.assertAlmostEqual(A["horaire"]["compteur"]["fin"], 3.25)
        d = tempfile.mkdtemp()
        anc = MR.dossier
        MR.dossier = lambda: d
        try:
            c = M.preparer_genre(M.nouvelle("compteur"), "defilement")
            import numpy as np, cv2
            f = os.path.join(d, "cap.png")
            cv2.imwrite(f, np.full((800, 200, 3), 200, np.uint8))
            c["image"] = f
            props = MR.preparer(c)
        finally:
            MR.dossier = anc
        self.assertEqual(props["A"]["image"], "capture.png")
        self.assertAlmostEqual(props["A"]["image_ratio"], 4.0)


class TestFenetre(unittest.TestCase):
    def test_sous_titres_et_calage(self):
        from app.fenetre import Fenetre
        from app import motion as M
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        dl = ed.animation(genre="sous_titres")
        dl._test_oui = True
        self.assertEqual(dl.anim["genre"], "sous_titres")
        self.assertTrue(dl.anim["transparent"])
        self.assertTrue(dl.style_st.isVisible() and not dl.table.isVisible())
        anc = (M.mots_montage, M.a_transcrire)
        M.mots_montage = lambda projet: [{"t0": 5 + a, "t1": 5 + b, "mot": w} for a, b, w in MOTS]
        M.a_transcrire = lambda projet: 0
        try:
            ed.timeline.position = 5.0
            dl.prendre_mots()
            self.assertEqual(len(dl.anim["mots"]), len(MOTS))
            self.assertAlmostEqual(dl.anim["pose"], 5.0)
            dl.genre.setCurrentIndex(dl.genre.findData("chiffres"))
            dl.anim["valeur"] = 34390
            M.mots_montage = lambda projet: [{"t0": 8.0, "t1": 8.8, "mot": "34390"}]
            dl.calage.setCurrentIndex(dl.calage.findData("voix"))
            dl.caler()
            self.assertTrue(attendre(lambda: dl.anim.get("cale") == "voix"))
        finally:
            M.mots_montage, M.a_transcrire = anc
        self.assertAlmostEqual(dl.anim["horaire"]["compteur"]["fin"], 8.8 - dl.anim["pose"] + 0.25 - 0.8, delta=1.0)
        dl.genre.setCurrentIndex(dl.genre.findData("progression"))
        self.assertTrue(dl.b_toute.isVisible())
        dl.close()
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
