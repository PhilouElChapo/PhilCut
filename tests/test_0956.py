"""0.9.56 : plan de liaison intelligent. Images du raccord (dernière de A, première de B), mesures, propositions bornées,
Gemini Omni avec première et dernière images (images d'abord, puis la phrase de Google), pose dans un vide ou avec
décalage de la suite (plans, marqueurs, titres) en une seule annulation, fenêtre non bloquante, menus et guide."""
import base64, io, json, os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


def _projet_deux_plans(ed, vide=0.0):
    from app import moteur
    d = os.environ["APPDATA"]
    va = commun.video_test(d, "liaison_a.mp4", duree=3)
    vb = os.path.join(d, "liaison_b.mp4")
    moteur.lancer(["-y", "-f", "lavfi", "-i", "color=c=navy:s=640x360:r=30:d=3", "-c:v", "libx264", "-preset", "ultrafast",
                   "-pix_fmt", "yuv420p", vb])
    ma, mb = ed.projet.ajouter_media(va, moteur.sonder(va)), ed.projet.ajouter_media(vb, moteur.sonder(vb))
    a = ed.projet.ajouter_clip(ma["id"], debut=0.0, src_debut=0.5, src_fin=2.5)
    b = ed.projet.ajouter_clip(mb["id"], debut=2.0 + vide, src_debut=0.0, src_fin=3.0)
    ed.rafraichir()
    return a, b


class TestMoteur(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()

    def tearDown(self):
        self.ed.projet.modifie = False

    def test_images_mesures_propositions(self):
        from app import liaison as L
        import cv2
        a, b = _projet_deux_plans(self.ed)
        self.assertIs(L.plans_voisins(self.ed.projet, a)[1], b)
        self.assertIsNone(L.plans_voisins(self.ed.projet, b)[1])
        d = os.path.join(os.environ["APPDATA"], "raccord")
        ia, ib = L.images_raccord(self.ed.projet, a, b, d, largeur=320)
        img_b = cv2.imread(ib)
        self.assertGreater(int(img_b[:, :, 0].mean()), int(img_b[:, :, 2].mean()) + 40)     # B est bleu marine
        mes = L.mesurer(self.ed.projet, a, b, ia, ib)
        self.assertLess(mes["lumiere_b"], mes["lumiere_a"])
        props = L.propositions_regles(mes)
        self.assertGreaterEqual(len(props), 3)
        for p in props:
            self.assertTrue(p["titre"] and p["idee"] and p["consigne"])
            self.assertTrue(3 <= p["duree"] <= 10)

    def test_reponse_ia_bornee(self):
        from app import liaison as L
        r = L.lire_propositions({"propositions": [{"titre": "Envol", "idee": "x", "consigne": "fly", "duree": 40},
                                                  {"titre": "", "idee": "", "consigne": ""}, "n'importe quoi",
                                                  {"titre": "Court", "idee": "y", "consigne": "short", "duree": 1}]})
        self.assertEqual([p["duree"] for p in r], [10, 3])
        self.assertEqual(L.lire_propositions(None), [])

    def test_omni_premiere_et_derniere_image(self):
        """Méthode Google pour Omni 1.2 : image de départ, image d'arrivée, PUIS le texte avec la phrase des rôles."""
        from app import fabrique, liaison as L
        envoyes = []

        class Rep(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def faux(req, timeout=0):
            envoyes.append(json.loads(req.data.decode()))
            return Rep(json.dumps({"id": "x", "status": "completed",
                                   "outputs": [{"type": "video", "data": base64.b64encode(b"MP4").decode()}]}).encode())
        d = os.environ["APPDATA"]
        ia, ib = os.path.join(d, "oa.png"), os.path.join(d, "ob.png")
        open(ia, "wb").write(b"AAA")
        open(ib, "wb").write(b"BBB")
        anc = fabrique.urllib.request.urlopen
        fabrique.urllib.request.urlopen = faux
        try:
            s = L.omni_premiere_derniere("clef-essai", ia, ib, "The camera rises.", os.path.join(d, "o.mp4"), duree=14)
        finally:
            fabrique.urllib.request.urlopen = anc
        self.assertEqual(open(s, "rb").read(), b"MP4")
        entree = envoyes[0]["input"]
        self.assertEqual([x["type"] for x in entree], ["image", "image", "text"])
        self.assertEqual(base64.b64decode(entree[0]["data"]), b"AAA")
        self.assertEqual(base64.b64decode(entree[1]["data"]), b"BBB")
        self.assertIn("first image as the starting frame and the second image as the final frame", entree[2]["text"])
        self.assertIn("about 10 seconds", entree[2]["text"])                        # bornée à 10 s
        self.assertEqual(envoyes[0]["model"], "gemini-omni-1.2-flash")
        self.assertNotIn("<FIRST_FRAME>", entree[2]["text"])                       # plus de balises
        self.assertAlmostEqual(L.prix_omni(5), 1.0)                                # Omni peut aller à 10 s : compté au plus haut

    def test_pose_dans_un_vide(self):
        from app import liaison as L, moteur
        a, b = _projet_deux_plans(self.ed, vide=4.0)
        v = commun.video_test(os.environ["APPDATA"], "liaison_c.mp4", duree=3)
        debut_b = b["debut"]
        c = L.poser(self.ed.projet, a, b, v, moteur.sonder(v))
        self.assertAlmostEqual(c["debut"], 2.0, places=3)
        self.assertAlmostEqual(b["debut"], debut_b)                                 # il tenait dans le vide : rien ne bouge
        self.assertEqual(c["liaison"], {"a": a["id"], "b": b["id"]})

    def test_pose_decale_la_suite_et_s_annule_d_un_coup(self):
        from app import liaison as L, moteur
        a, b = _projet_deux_plans(self.ed)
        p = self.ed.projet
        p.ajouter_marqueur(3.0, "après")
        p.ajouter_titre("Titre B", 2.5, 4.0)
        p.ajouter_titre("Titre A", 0.5, 1.5)
        avant = json.dumps(p.d, sort_keys=True)
        v = commun.video_test(os.environ["APPDATA"], "liaison_d.mp4", duree=3)
        c = L.poser(p, a, b, v, moteur.sonder(v), src=(0.5, 2.5))
        self.assertAlmostEqual(c["src_fin"] - c["src_debut"], 2.0, places=2)
        self.assertAlmostEqual(p.clip(b["id"])["debut"], 4.0, places=3)             # B recule de 2 s
        self.assertAlmostEqual(p.marqueurs[0]["t"], 5.0, places=3)
        titres = {t["texte"]: t for t in p.titres}
        self.assertAlmostEqual(titres["Titre B"]["debut"], 4.5, places=3)
        self.assertAlmostEqual(titres["Titre A"]["debut"], 0.5, places=3)            # avant le raccord : ne bouge pas
        p.annuler()
        self.assertEqual(json.dumps(p.d, sort_keys=True), avant)


class TestFenetre(unittest.TestCase):
    def test_fenetre_complete(self):
        from app import liaison as L
        from app.fenetre import Fenetre
        from app.dialogues_liaison import DialogueLiaison
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        a, b = _projet_deux_plans(ed)
        d = ed.plan_liaison(a)
        self.assertIsInstance(d, DialogueLiaison)
        self.assertFalse(d.isModal())
        t0 = time.time()
        while time.time() - t0 < 60 and d.images is None and d.etat.text()[:1] != "✕":
            app.processEvents()
            time.sleep(0.02)
        self.assertIsNotNone(d.images, d.etat.text())
        self.assertGreaterEqual(len(d.props), 3)
        self.assertTrue(d.consigne.toPlainText())                                  # la 1re proposition est choisie
        d.props[1][0].setChecked(True)
        self.assertEqual(d.consigne.toPlainText(), d.props[1][2]["consigne"])
        # les IA demandent l'accord des personnes visibles
        d.mode.setCurrentIndex(list(d.mode.itemData(i) for i in range(d.mode.count())).index("omni"))
        self.assertTrue(d.accord.isVisibleTo(d))
        self.assertFalse(d.b_fabriquer.isEnabled())
        d.mode.setCurrentIndex(0)                                                   # transition 3D : gratuite
        self.assertEqual(d.mode.currentData(), "3d")
        self.assertTrue(d.b_fabriquer.isEnabled())
        anc = L.fabriquer

        def faux(mode, ia, ib, consigne, sortie, duree, params, fmt, progression=None, arret=None):
            progression(0.5, "…")
            return commun.video_test(os.path.dirname(sortie), os.path.basename(sortie), duree=2)
        L.fabriquer = faux
        try:
            d.fabriquer()
            t0 = time.time()
            while time.time() - t0 < 60 and d.resultat is None and d.etat.text()[:1] != "✕":
                app.processEvents()
                time.sleep(0.02)
        finally:
            L.fabriquer = anc
        self.assertIsNotNone(d.resultat, d.etat.text())
        self.assertTrue(d.b_poser.isEnabled())
        n = len(ed.projet.clips)
        d.poser()
        self.assertEqual(len(ed.projet.clips), n + 1)
        from app import guides as G
        self.assertTrue(G.est_fait("liaison", ed))
        ed.projet.annuler()
        self.assertEqual(len(ed.projet.clips), n)
        d.close()
        ed.projet.modifie = False

    def test_menus_et_guide(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        a, b = _projet_deux_plans(ed)
        vus = []
        ed.timeline._exec_menu = lambda mm, pos: vus.append([x.text() for x in mm.actions()])
        ed.timeline.menu_clip(a, None, 0.5)
        self.assertIn("Plan de liaison avec le plan suivant…", vus[-1])
        ed.timeline.menu_clip(b, None, 2.5)                                         # dernier plan : pas de suivant
        self.assertNotIn("Plan de liaison avec le plan suivant…", vus[-1])
        fb = f.menu_fabrique_ia if hasattr(f, "menu_fabrique_ia") else None
        from app import guides as G
        g = next(x for x in G.guides() if x["id"] == "liaison")
        self.assertEqual(g["etat"], "ok")
        # sans plan suivant : un message, pas de fenêtre
        ed.timeline.selectionner(b["id"])
        self.assertIsNone(ed.plan_liaison(b))
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
