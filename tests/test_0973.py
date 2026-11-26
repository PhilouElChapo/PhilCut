"""0.9.73 : images de départ et d'arrivée vues et validées avant la vidéo ; retouches de voix (traitements qui se
remplacent, écoute qui marche, recopie sur d'autres plans) ; voix créée qui ne s'arrête plus sur un mot."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def _image(d, nom="perso.png"):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(64, 36, QImage.Format_RGB32)
    q.fill(QColor("gray"))
    q.save(ch)
    return ch


def attendre(cond, s=20):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestRetouches(unittest.TestCase):
    def test_exclusifs(self):
        from app.export import basculer_retouche as B
        l = B([], "a_studio")
        l = B(l, "a_narration_chaude")
        self.assertEqual(l, ["a_narration_chaude"])                 # un traitement complet remplace l'autre
        l = B(l, "a_desser")
        l = B(l, "a_grave")
        l = B(l, "a_aigu")
        self.assertEqual(l, ["a_narration_chaude", "a_desser", "a_aigu"])
        self.assertEqual(B(l, "a_aigu"), ["a_narration_chaude", "a_desser"])
        self.assertEqual(B(l, "a_desser", False), ["a_narration_chaude", "a_aigu"])

    def test_ecoute_et_recopie(self):
        from app.fenetre import Fenetre
        from app import moteur
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c1 = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        c2 = ed.projet.ajouter_clip(m["id"], "video", 10.0)
        c1["effets_audio"] = ["a_chaude"]
        ed.inspecteur.montrer_clip(c1["id"])
        joue = []

        class FauxLecteur:                      # pas de vraie sortie son sur le serveur de test
            class _S:
                def connect(self, f):
                    pass
            playbackStateChanged = _S()

            def playbackState(self):
                return 0

            def setSource(self, u):
                if u.toLocalFile():
                    joue.append(u.toLocalFile())

            def play(self):
                pass
        ed.inspecteur._lecteur = FauxLecteur()
        ed.inspecteur._ecouter(c1)
        self.assertTrue(attendre(lambda: bool(joue)))
        self.assertTrue(os.path.exists(joue[0]))
        ed.inspecteur._poser_retouches(c1, [c2])
        self.assertEqual(c2["effets_audio"], ["a_chaude"])
        f._effet_audio(ed, c1, "a_studio")
        self.assertEqual(c1["effets_audio"], ["a_chaude", "a_studio"])
        f._effet_audio(ed, c1, "a_studio_doux")
        self.assertEqual(c1["effets_audio"], ["a_chaude", "a_studio_doux"])


class TestVoixClone(unittest.TestCase):
    def test_reprise_sans_accents(self):
        from app import voix_clone as VC
        import numpy as np
        vus = []
        anc = (VC.jetons_texte, VC.parole, VC.decoder)
        VC.jetons_texte = lambda tok, t, l: (vus.append(t), np.array([[1, 2]]))[1]

        def parole(s, ids, emp, ex, maxi, prog, arret, infos):
            infos["fini"] = "é" not in vus[-1]                    # le modèle se perd sur l'accent
            return np.array([[5, 6, 7]])
        VC.parole = parole
        VC.decoder = lambda s, j, emp: np.ones(10, dtype=np.float32)
        try:
            r = VC._morceau({"tokenizer": None}, "Une vidéo.", "fr", None, 0.5, lambda f: None, lambda: False)
        finally:
            VC.jetons_texte, VC.parole, VC.decoder = anc
        self.assertEqual(vus, ["Une vidéo.", "Une video."])
        self.assertEqual(len(r), 10)
        self.assertEqual(VC.sans_accents("Vidéo à l'été"), "Video a l'ete")


class TestImagesAvantVideo(unittest.TestCase):
    def test_revue(self):
        from app import sequence_ia as Q, ia
        from app.dialogues_images_plans import DialogueImagesPlans
        d = tempfile.mkdtemp()
        img = _image(d)
        with open(img, "rb") as f:
            png = f.read()
        s = Q.nouvelle()
        s["personnages"] = [Q.personnage("Hélène", "femme")]
        s["personnages"][0]["images"] = [img]
        s["plans"] = [Q.plan("Hélène entre", ["Hélène"], "", 5), Q.plan("Hélène s'assoit", ["Hélène"], "", 5)]
        params = {"clef_gemini": "x", "clef_fal": "a:b"}
        self.assertEqual(Q.images_a_verifier(s, [0, 1], params, "kling-o3-ref"), [0, 1])
        self.assertEqual(Q.images_a_verifier(s, [0, 1], params, "omni-720p"), [])
        consignes = []
        anc = ia.generer_image_refs
        ia.generer_image_refs = lambda p, c, refs, *a, **k: (consignes.append(c), png)[1]
        try:
            dl = DialogueImagesPlans(None, s, params, [0, 1])
            dl._test_oui = True
            dl.preparer_manquantes()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and s["plans"][1].get("image_fin")))
            self.assertTrue(s["personnages"][0].get("planche"))
            self.assertTrue(s["plans"][0]["image"] and s["plans"][0]["image_fin"])
            self.assertEqual(Q.depart_prevu(s, 1), s["plans"][0]["image_fin"])     # plan 2 enchaîné sur l'arrivée du 1
            self.assertTrue(dl.b_ok.isEnabled())
            dl._test_precision = "assise, l'ordinateur ouvert"
            ancienne = s["plans"][0]["image_fin"]
            dl.refaire("arrivee")
            self.assertTrue(attendre(lambda: not dl._en_calcul() and s["plans"][0]["image_fin"] != ancienne))
            self.assertIn("Precisely, at the end", consignes[-1])
            dl.valider()
            self.assertTrue(s["plans"][0]["images_ok"])
            dl.sans_arrivee()
            self.assertTrue(s["plans"][1]["sans_fin"])
            dl.valider()
        finally:
            ia.generer_image_refs = anc
        self.assertEqual(Q.images_a_verifier(s, [0, 1], params, "kling-o3-ref"), [])


if __name__ == "__main__":
    unittest.main()
