"""0.9.72 : personnage fidèle d'un plan à l'autre (fiche personnage, images de départ et d'arrivée, moteur Kling O3
Référence, enchaînement sur la dernière image), « Prolonger ce plan » par le cloud, crédit restant, fenêtres de travail
avec « Réduire », rangement des tampons à la souris, case du visage visible dans « Faire parler »."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def _image(d, nom="perso.png", couleur="gray"):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(64, 36, QImage.Format_RGB32)
    q.fill(QColor(couleur))
    q.save(ch)
    return ch


def _video(d, nom="plan.mp4", duree=1.0):
    from app import moteur
    ch = os.path.join(d, nom)
    moteur.lancer(["-y", "-f", "lavfi", "-i", f"testsrc=size=160x90:rate=10:duration={duree}", "-pix_fmt", "yuv420p", ch])
    return ch


class TestMoteurReference(unittest.TestCase):
    def test_corps(self):
        from app import generateurs_video as GV
        m = GV.modele("kling-o3-ref", en_ligne=False) if "en_ligne" in GV.modele.__code__.co_varnames else \
            next(x for x in GV.MODELES if x["id"] == "kling-o3-ref")
        c = GV.corps_reference("Character A sits down.", 12, "16:9", "https://d", "https://f",
                               [{"nom": "Character A", "frontal_image_url": "https://p", "reference_image_urls": ["https://i1"]}], m)
        self.assertEqual(c["duration"], "12")
        self.assertEqual(c["start_image_url"], "https://d")
        self.assertEqual(c["end_image_url"], "https://f")
        self.assertEqual(c["elements"][0]["frontal_image_url"], "https://p")
        self.assertTrue(c["prompt"].startswith("@Element1 is Character A"))
        self.assertIn("exactly identical", c["prompt"])
        self.assertIs(c["generate_audio"], False)
        self.assertEqual(GV.prix(m, 5), 0.42)

    def test_envoi(self):
        from app import generateurs_video as GV
        d = tempfile.mkdtemp()
        img = _image(d)
        envoyes, demandes = [], []
        anc = (GV.televerser, GV.attendre_fal)
        GV.televerser = lambda cle, ch: (envoyes.append(ch), "https://cdn/" + os.path.basename(ch))[1]
        GV.attendre_fal = lambda cle, point, corps, sortie, *a, **k: (demandes.append((point, corps)), sortie)[1]
        try:
            GV.generer({"clef_fal": "a:b"}, "kling-o3-ref", "x", os.path.join(d, "o.mp4"), 6, "16:9", img,
                       references=[("Character A", [img, img])], image_fin=img)
        finally:
            GV.televerser, GV.attendre_fal = anc
        point, corps = demandes[0]
        self.assertIn("reference-to-video", point)
        self.assertEqual(len(envoyes), 4)                         # 2 images du personnage, départ, arrivée
        self.assertEqual(corps["elements"][0]["reference_image_urls"], ["https://cdn/perso.png"])


class TestSequenceFidele(unittest.TestCase):
    def test_chaine(self):
        from app import sequence_ia as Q, generateurs_video as GV, ia
        d = tempfile.mkdtemp()
        img = _image(d)
        s = Q.nouvelle()
        s["personnages"] = [Q.personnage("Hélène", "femme")]
        s["personnages"][0]["images"] = [img]
        s["plans"] = [Q.plan("Hélène entre", ["Hélène"], "", 5), Q.plan("Hélène s'assoit", ["Hélène"], "", 5)]
        params = {"clef_gemini": "x", "clef_fal": "a:b"}
        with open(img, "rb") as f:
            png = f.read()
        appels, images_ia = [], []
        anc = (GV.generer, ia.generer_image_refs)
        ia.generer_image_refs = lambda p, c, refs, delai=240: (images_ia.append(c[:30]), png)[1]

        def faux(params, ident, texte, sortie, duree, fmt, image, *a, **k):
            appels.append((image, k.get("references"), k.get("image_fin")))
            return _video(os.path.dirname(sortie), os.path.basename(sortie))
        GV.generer = faux
        try:
            self.assertEqual(len(Q.sans_planche(s, [0, 1])), 1)
            Q.planches_manquantes(s, s["plans"][0], params, "kling-o3-ref")
            self.assertTrue(os.path.exists(s["personnages"][0]["planche"]))
            f0 = Q.fabriquer_plan(s, 0, params, "kling-o3-ref")
            s["plans"][0]["fichier"] = f0
            Q.fabriquer_plan(s, 1, params, "kling-o3-ref")
        finally:
            GV.generer, ia.generer_image_refs = anc
        refs = appels[0][1]
        self.assertEqual(refs[0][0], "Character A")
        self.assertEqual(refs[0][1][0], s["personnages"][0]["planche"])      # la planche passe en image de face
        self.assertTrue(appels[0][2])                                        # image d'arrivée composée
        self.assertIn("plan01_arrivee", appels[1][0])                        # 0.9.77 : plan 2 part de l'arrivée du plan 1
        self.assertTrue(any(c.startswith("If the reference photo") for c in images_ia))
        s2 = Q.nouvelle()
        s2["plans"] = [Q.plan("a", [], "", 5)]
        self.assertGreater(Q.prix_total(s2, "kling-o3-ref", params), Q.prix_total(dict(s2, image_fin_auto=False), "kling-o3-ref", params))

    def test_sans_enchainement(self):
        from app import sequence_ia as Q
        s = Q.nouvelle()
        s["plans"] = [Q.plan("a"), Q.plan("b")]
        s["plans"][0]["fichier"] = _video(tempfile.mkdtemp())
        s["plans"][1]["enchainer"] = False
        self.assertEqual(Q.depart_enchaine(s, 1), "")
        s["plans"][1]["enchainer"] = True
        self.assertTrue(os.path.exists(Q.depart_enchaine(s, 1)))

    def test_fenetre(self):
        from app import dialogues_sequence as DS
        from app.fenetre import Fenetre
        f = Fenetre([])
        ed = f.nouveau_projet("16:9")
        d = DS.DialogueSequence(ed, None)
        self.assertTrue(hasattr(d, "image_fin") and hasattr(d, "p_enchainer") and hasattr(d, "credit"))
        self.assertEqual(d.p_duree.maximum(), 15)


class TestProlongerCloud(unittest.TestCase):
    def test_cloud(self):
        from app import prolonger as PR, generateurs_video as GV, moteur
        d = tempfile.mkdtemp()
        v = _video(d, "rush.mp4", 2.0)
        media = {"chemin": v, "genre": "video", "fiche": moteur.sonder(v)}
        clip = {"id": "c1", "src_debut": 0.0, "src_fin": 2.0}
        vus = []
        anc = GV.generer

        def faux(params, ident, texte, sortie, duree, fmt, image, *a, **k):
            vus.append((ident, duree, image, len(k["references"][0][1]), texte))
            return _video(d, "brut.mp4", 3.0) and os.replace(os.path.join(d, "brut.mp4"), sortie) or sortie
        GV.generer = faux
        try:
            out = PR.fabriquer(media, clip, 2.5, "cloud", "fin", "silence", (320, 180), 25, {"clef_fal": "a:b"},
                               sortie=os.path.join(d, "suite.mp4"), suite="She smiles")
        finally:
            GV.generer = anc
        self.assertTrue(os.path.exists(out))
        ident, duree, image, n, texte = vus[0]
        self.assertEqual((ident, duree, n), ("kling-o3-ref", 3, 3))
        self.assertTrue(image)
        self.assertTrue(texte.startswith("She smiles"))
        self.assertAlmostEqual(float(moteur.sonder(out)["duree"]), 2.5, delta=0.2)
        self.assertEqual(PR.prix_cloud(2.5), 0.25)


class TestCreditEtFenetres(unittest.TestCase):
    def test_credit(self):
        from app import credit_ia as C
        self.assertIn("12,40", C.texte_credit("fal", (12.4, "USD")))
        self.assertIn("presque", C.texte_credit("fal", (1.0, "USD")))
        self.assertIn("Google", C.texte_credit("google", None))
        self.assertEqual(C.fournisseur_du_moteur("kling-o3-ref"), "fal")
        self.assertIsNone(C.fournisseur_du_moteur("locale"))
        w = C.LigneCredit({}, "fal")
        w._test_ouvert = []
        w.recharger()
        self.assertIn("fal.ai", w._test_ouvert[0])

    def test_reduire(self):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QWidget
        from app.widgets import non_bloquante
        hote = QWidget()
        d0 = QDialog(hote)
        QVBoxLayout(d0).addWidget(QDialogButtonBox(QDialogButtonBox.Close))
        d = non_bloquante(hote, "essai", lambda: d0)
        self.assertIsNotNone(d.b_reduire)
        self.assertFalse(d.isModal())

    def test_grille_rangeable(self):
        from PySide6.QtWidgets import QListWidgetItem
        from app.dialogues_tampons import GrilleRangeable
        ordre = []
        g = GrilleRangeable()
        for t in "ABCD":
            g.addItem(QListWidgetItem(t))
        g.permettre(True)
        g.apres_rangement = lambda: ordre.append([g.item(i).text() for i in range(g.count())])
        g.deplacer(0, 2)
        self.assertEqual(ordre[-1], ["B", "C", "A", "D"])
        g.permettre(False)
        self.assertFalse(g.dragEnabled())


if __name__ == "__main__":
    unittest.main()
