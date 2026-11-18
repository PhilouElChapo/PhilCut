"""0.9.91 : brouillon de toute la séquence (animatique gratuite, IA de ce poste, Gemini Omni 360p) avant la vraie
fabrication ; rien n'est posé dans le film."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=90):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


def images(d):
    from PySide6.QtGui import QImage, QColor
    out = []
    for nom, c in (("a.png", "#803030"), ("b.png", "#303080")):
        im = QImage(320, 240, QImage.Format_RGB32)
        im.fill(QColor(c))
        im.save(os.path.join(d, nom))
        out.append(os.path.join(d, nom))
    return out


def sequence(d):
    from app import sequence_ia as Q
    a, b = images(d)
    seq = Q.nouvelle("16:9")
    seq["plans"] = [Q.plan("Il quitte la table", [], "", 2), Q.plan("Elle l'attend près de la porte", [], "", 3),
                    Q.plan("Ils sortent", [], "", 2)]
    seq["plans"][0]["image"] = a
    seq["plans"][1].update(clef=True, image_fin=b, sans_fin=False)
    seq["plans"][2]["sans_fin"] = True
    return seq, a, b


class TestBrouillon(unittest.TestCase):
    def setUp(self):
        from app import sequence_ia as Q
        self.d = tempfile.mkdtemp()
        self.anc = Q.dossier
        Q.dossier = lambda s: self.d

    def tearDown(self):
        from app import sequence_ia as Q
        Q.dossier = self.anc

    def test_images_connues(self):
        from app import brouillon as B
        seq, a, b = sequence(self.d)
        self.assertEqual(B.image_du_plan(seq, 0), a)
        self.assertEqual(B.image_fin_du_plan(seq, 1), b)
        self.assertEqual(B.image_du_plan(seq, 2), b)          # part de l'image clef du plan d'avant
        self.assertEqual(B.prix(seq, "animatique", {}), 0)
        self.assertGreater(B.prix(seq, "omni-360p", {}), 0)

    def test_animatique(self):
        from app import brouillon as B, moteur
        seq, a, b = sequence(self.d)
        f = B.fabriquer(seq, "animatique", {})
        info = moteur.sonder(f)
        self.assertAlmostEqual(float(info["duree"]), 7, delta=0.3)
        self.assertEqual(seq["brouillon"]["fichier"], f)
        self.assertEqual(seq["brouillon"]["mode"], "animatique")

    def test_cloud_coupe_a_la_duree_des_plans(self):
        from app import brouillon as B, generateurs_video as GV, moteur
        seq, a, b = sequence(self.d)
        vus = []

        def faux(params, ident, consigne, sortie, duree=5, format_="16:9", image=None, progression=None,
                 arret=lambda: False, son=False, references=None, image_fin=None, multi=None):
            vus.append((ident, image, son))
            v = commun.video_test(self.d, f"o{len(vus)}.mp4", 4, taille="640x360")
            os.replace(v, sortie)
            return sortie
        anc = GV.generer
        GV.generer = faux
        try:
            f = B.fabriquer(seq, "omni-360p", {"clef_gemini": "g"})
        finally:
            GV.generer = anc
        self.assertEqual([v[0] for v in vus], ["omni-360p"] * 3)
        self.assertEqual(vus[0][1], a)
        self.assertFalse(any(v[2] for v in vus))
        self.assertAlmostEqual(float(moteur.sonder(f)["duree"]), 7, delta=0.3)
        self.assertFalse(seq["plans"][0].get("fichier"))        # le brouillon ne touche pas aux vrais plans


class TestAssistant(unittest.TestCase):
    def test_bouton(self):
        from app.fenetre import Fenetre
        from app import moteur, sequence_ia as Q
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        anc = Q.dossier
        Q.dossier = lambda s: d
        try:
            va = commun.video_test(d, "a.mp4", 2)
            ma = ed.projet.ajouter_media(va, moteur.sonder(va))
            ca = ed.projet.ajouter_clip(ma["id"], "video", 0.0)
            dl = ed.assistant_creation(ca)
            dl.seq, _a, _b = sequence(d)
            modes = dl.modes_brouillon()
            self.assertEqual([m[0] for m in modes], ["animatique", "locale", "omni-360p"])
            self.assertTrue(modes[0][3])
            self.assertFalse(modes[2][3])                         # sans clef Gemini
            dl._remplir_images()
            self.assertFalse(dl.b_voir_brouillon.isVisibleTo(dl))
            dl.faire_brouillon("animatique")
            self.assertTrue(attendre(lambda: getattr(dl, "_dlg_brouillon", None) is not None))
            self.assertTrue(dl._dlg_brouillon.isVisible())
            self.assertTrue(os.path.exists(dl.seq["brouillon"]["fichier"]))
            dl._dlg_brouillon.close()
        finally:
            Q.dossier = anc


if __name__ == "__main__":
    unittest.main()
