"""0.9.86 : corrections du premier vrai essai de l'assistant (images trop petites pour fal, photo JPEG annoncée PNG,
continuité des personnages, cadrage, seul ce qui change est refait, retour en arrière sans rien perdre, images de
contrôle au choix, crédits) et la timeline image par image."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=40):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


def image(d, nom, l, h, couleur="#3060a0"):
    from PySide6.QtGui import QImage, QColor, QPainter
    img = QImage(l, h, QImage.Format_RGB32)
    img.fill(QColor("#e8e8e8"))
    p = QPainter(img)
    p.fillRect(int(l * 0.3), int(h * 0.1), int(l * 0.4), int(h * 0.85), QColor(couleur))
    p.end()
    ch = os.path.join(d, nom)
    img.save(ch)
    return ch


class TestImages(unittest.TestCase):
    def test_type_et_taille(self):
        from app import ia, generateurs_video as GV
        d = tempfile.mkdtemp()
        jpg = image(d, "photo.jpg", 200, 300)
        png = image(d, "dessin.png", 50, 50)
        self.assertEqual(ia.type_image(open(jpg, "rb").read()), "image/jpeg")
        self.assertEqual(ia.type_image(open(png, "rb").read()), "image/png")
        faux = os.path.join(d, "faux.png")                     # un JPEG nommé .png : c'est le contenu qui compte
        os.replace(jpg, faux)
        self.assertEqual(ia.type_image(open(faux, "rb").read()), "image/jpeg")
        self.assertTrue(GV._data_uri(faux).startswith("data:image/jpeg"))
        grande = GV.assez_grande(faux)
        from PySide6.QtGui import QImage
        q = QImage(grande)
        self.assertGreaterEqual(min(q.width(), q.height()), 512)
        gros = image(d, "gros.png", 800, 900)
        self.assertEqual(GV.assez_grande(gros), gros)

    def test_decoupe_detouree(self):
        from app import assistant_creation as A
        d = tempfile.mkdtemp()
        src = image(d, "groupe.png", 400, 300)
        dec = A.decouper(src, [0.25, 0.05, 0.75, 1.0], os.path.join(d, "dec.png"))
        self.assertTrue(os.path.exists(dec))
        import cv2
        im = cv2.imread(dec)
        self.assertGreater(im[2, 2].mean(), 200)               # le coin (fond) est blanc


class TestContinuite(unittest.TestCase):
    def seq(self):
        from app import sequence_ia as Q
        s = Q.nouvelle("16:9")
        s["personnages"] = [Q.personnage("Femme brune", "manteau noir"), Q.personnage("Chauffeur", "costume")]
        s["plans"] = [Q.plan("Elles montent dans la voiture", ["Femme brune", "Chauffeur"]),
                      Q.plan("Le chauffeur prend le volant", ["Chauffeur"]),
                      Q.plan("La voiture démarre", [])]
        return s

    def test_visibles_et_consigne(self):
        from app import sequence_ia as Q
        s = self.seq()
        self.assertEqual(len(Q.visibles(s, s["plans"][2])), 2)            # sans continuité : tout le monde (ancien comportement)
        for pl in s["plans"]:
            pl["visibles_fixes"] = True
        s["plans"][1]["hors_champ"] = "la femme est dans la voiture"
        self.assertEqual(Q.visibles(s, s["plans"][2]), [])
        c = Q.consigne(s, s["plans"][1], traduire=False)
        self.assertIn("Not visible in this shot: Character A", c)
        self.assertIn("Nobody else appears", c)
        self.assertEqual(Q.references_du_plan(s, s["plans"][2]), [])

    def test_scripte(self):
        from app import assistant_creation as A
        s = self.seq()
        anc = A.demander
        A.demander = lambda *a, **k: {"plans": [{"personnages": ["Femme brune", "Chauffeur"], "hors_champ": "", "camera": "plan large"},
                                                {"personnages": ["Chauffeur"], "hors_champ": "la femme est dans la voiture",
                                                 "camera": "plan moyen"},
                                                {"personnages": ["Inconnu"], "hors_champ": "tous dans la voiture",
                                                 "camera": "plan large, recule"}]}
        try:
            n = A.continuite({}, s, "claude")
        finally:
            A.demander = anc
        self.assertEqual(n, 3)
        self.assertEqual(s["plans"][2]["personnages"], [])                # nom inconnu ignoré : personne
        self.assertEqual(s["plans"][1]["camera"], "plan moyen")
        self.assertTrue(all(pl["visibles_fixes"] for pl in s["plans"]))

    def test_seul_ce_qui_change(self):
        from app import assistant_creation as A
        d = tempfile.mkdtemp()
        s = self.seq()
        for i, pl in enumerate(s["plans"]):
            pl["image_fin"] = image(d, f"fin{i}.png", 64, 64)
            pl["fichier"] = image(d, f"v{i}.png", 8, 8)
        etat = A.etat(s)
        etat["plans"][0]["action"] = "Elles montent vite dans la voiture"          # seul le plan 1 change
        A.appliquer(s, etat)
        self.assertFalse(s["plans"][0].get("image_fin"))
        self.assertFalse(s["plans"][1].get("image_fin"))                         # il part de l'arrivée refaite
        self.assertTrue(s["plans"][2].get("image_fin"))                          # intact
        self.assertTrue(s["plans"][2].get("fichier"))

    def test_images_par(self):
        from app import assistant_creation as A, sequence_ia as Q
        s = Q.nouvelle("16:9")
        self.assertEqual(A.images_par(s, {"clef_gemini": "k"}), "gemini")
        s["images_par"] = "aucune"
        self.assertEqual(A.a_preparer(s, {"clef_gemini": "k"}), (0, 0, 0))


class TestTimeline(unittest.TestCase):
    def test_image_par_image(self):
        from app.fenetre import Fenetre
        from app import moteur
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        v = os.path.join(d, "v.mp4")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30:duration=2", "-pix_fmt", "yuv420p", v])
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.projet.ajouter_clip(m["id"], "video", 0.0)
        ed.rafraichir()
        tl = ed.timeline
        tl.aller_a(0.0)
        for _i in range(10):
            tl.pas_image(1)
        self.assertAlmostEqual(tl.position, 10 / 30, places=3)
        tl.marquer_zone(0)
        tl.marquer_zone(1)                                   # une seule image
        self.assertEqual(tl.images_zone(), 1)
        tl.etendre_zone(1)
        tl.etendre_zone(1)
        self.assertEqual(tl.images_zone(), 3)
        self.assertTrue(ed.b_suppr_images.isEnabled())
        avant = ed.projet.duree()
        ed.partie(False)
        self.assertAlmostEqual(avant - ed.projet.duree(), 3 / 30, places=3)
        self.assertFalse(ed.b_suppr_images.isEnabled())


class TestFenetre(unittest.TestCase):
    def test_retour_sans_perte(self):
        from app.fenetre import Fenetre
        from app import moteur, assistant_creation as A
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_claude="k")
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        appels = []
        reponse = {"personnages": [{"nom": "Femme", "genre": "personne", "sur_image": False, "description": "manteau rouge"}],
                   "plans": [{"action": "Elle marche", "personnages": ["Femme"], "duree": 5, "camera": "plan large"},
                             {"action": "La rue est vide", "personnages": [], "hors_champ": "elle est partie", "duree": 4}]}

        def faux(params, consigne, texte, images=(), niveau="claude", max_jetons=3000):
            appels.append(consigne[:30])
            return reponse
        anc = A.demander
        A.demander = faux
        try:
            dl = ed.assistant_creation(c)
            dl._test_oui = True
            dl.histoire.setPlainText("Une femme en manteau rouge marche puis la rue reste vide")
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_QUI and not dl._en_calcul()))
            n = len(appels)
            dl.precedent()
            dl.suivant()                                      # rien n'a changé : pas de nouvelle lecture
            self.assertEqual(dl.pages.currentIndex(), D.P_QUI)
            self.assertEqual(len(appels), n)
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_PLANS)
            self.assertEqual(dl.t_plans.columnCount(), 4)
            self.assertEqual(dl.t_plans.item(0, 2).text(), "plan large")
            self.assertEqual(dl.t_plans.item(1, 1).text(), "")                # personne de visible
            self.assertIn("partie", dl.t_plans.item(1, 1).toolTip())
            dl._lire()
            self.assertTrue(dl.seq["plans"][1]["visibles_fixes"])
            self.assertEqual(dl.seq["plans"][1].get("hors_champ"), "elle est partie")
            self.assertIn("href='0'", dl.fil.text())                           # étapes déjà vues : cliquables
            dl.revenir_a(D.P_QUI)
            self.assertEqual(dl.pages.currentIndex(), D.P_QUI)
            self.assertEqual(dl.niveau_bas.currentData(), dl.niveau.currentData())
            self.assertTrue(any(x.fournisseur == "anthropic" for x in dl.credits))
            dl.revenir_a(D.P_PLANS)
            ed.assistant_creation_reprendre(dict(dl.seq, plans=dl.seq["plans"][:1]))     # retour du réglage manuel
            self.assertEqual(dl.t_plans.rowCount(), 1)
        finally:
            A.demander = anc


if __name__ == "__main__":
    unittest.main()
