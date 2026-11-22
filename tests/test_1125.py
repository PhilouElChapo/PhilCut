"""1.1.16 : motion design IA « look pro » (préproduction : blocs HyperFrames, dessins Gemini détourés, effets en vidéo IA,
modèle selon la complexité ; l'IA regarde son rendu et se corrige) ; animation simple avec une ou deux images."""
import copy, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def png_vert(d):
    from PySide6.QtGui import QImage, QColor, QPainter
    im = QImage(400, 300, QImage.Format_RGB32)
    im.fill(QColor("#00FF00"))
    p = QPainter(im)
    p.fillRect(120, 80, 160, 140, QColor("#c03020"))
    p.end()
    ch = os.path.join(d, "brut.png")
    im.save(ch)
    return ch


def anim_canons(d):
    from app import motion_libre as ML, moteur
    img = os.path.join(d, "img_canon.png")
    from app import motion_pro as MP
    MP.retirer_vert(png_vert(d), img)
    vid = os.path.join(d, "vid_boom.mp4")
    moteur.lancer(["-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:d=3", "-pix_fmt", "yuv420p", vid])
    with open(os.path.join(RACINE, "tests", "exemples", "libre_canons.txt"), encoding="utf-8") as f:
        s = ML.sections(f.read())
    s["videos"] = "boom 5.3 1.5 540 900 900\ninconnu 1 1 0 0 100"
    a = ML.fiche("essai", (1080, 1920))
    a["libre"] = {"ressources": {"images": {"canon": {"chemin": img, "largeur": 160, "hauteur": 140, "en": "a cannon"}},
                                 "videos": {"boom": {"chemin": vid, "duree": 3.0, "en": "explosion"}},
                                 "blocs": {"confetti": "<div class='x'>bloc</div>"}}}
    return ML.appliquer(a, s)


class TestPro(unittest.TestCase):
    def test_preparation_bornee(self):
        from app import motion_pro as MP
        r = MP.lire_preparation({"complexite": 9, "blocs": ["confetti", "inexistant", "count-up", "blur-in", "badge-pop"],
                                 "images": [{"id": "Canon Gauche!", "en": "a bronze cannon", "forme": "large"},
                                            {"id": "canon_gauche", "en": "doublon"}, {"en": ""}],
                                 "videos": [{"id": "feu", "en": "fire burst", "duree": 12}]},
                                {"confetti", "count-up", "blur-in", "badge-pop"})
        self.assertEqual(r["complexite"], 3)
        self.assertEqual(r["blocs"], ["confetti", "count-up", "blur-in"])
        self.assertEqual([x["id"] for x in r["images"]], ["canon_gauche"])
        self.assertEqual(r["videos"][0]["duree"], 5)
        self.assertEqual(MP.lire_preparation("n'importe quoi", set())["complexite"], 2)
        self.assertEqual(MP.lire_preparation({"images": [{"en": "x"}]}, set(), avec_images=False)["images"], [])

    def test_catalogue_et_modele(self):
        from app import motion_pro as MP
        cat = MP.catalogue()
        self.assertGreater(len(cat), 150)
        self.assertIn("confetti", {b["nom"] for b in cat})
        p = {"clef_claude": "sk-x", "clef_gemini": ""}
        self.assertEqual(MP.modele(p, 3), ("claude", "claude-opus-5-5"))
        self.assertEqual(MP.modele(p, 3, "rapide"), ("claude", "claude-sonnet-5-5"))
        self.assertEqual(MP.modele({"clef_gemini": "g"}, 1, "meilleur"), ("gemini", "gemini-2.5-pro"))
        pm = MP.params_modele(p, "claude", "claude-opus-5-5")
        self.assertEqual(pm["ia_modele_claude"], "claude-opus-5-5")
        self.assertNotIn("ia_modele_claude", p)
        prix = MP.prix({"images": [{}, {}], "videos": [], "blocs": ["a"]}, "claude-opus-5-5", {}, 2)
        self.assertAlmostEqual(prix["dessins"], 0.08)
        self.assertGreater(prix["total"], prix["ecrire"])

    def test_vert_retire(self):
        from PySide6.QtGui import QImage
        from app import motion_pro as MP
        d = tempfile.mkdtemp()
        w, h = MP.retirer_vert(png_vert(d), os.path.join(d, "o.png"))
        self.assertLess(w, 200)                                          # recadré sur l'objet
        q = QImage(os.path.join(d, "o.png"))
        self.assertEqual(q.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(q.pixelColor(w // 2, h // 2).alpha(), 255)

    def test_composition_et_consigne(self):
        from app import motion_libre as ML, motion_html as MH
        d = tempfile.mkdtemp()
        a = anim_canons(d)
        self.assertEqual([v["id"] for v in a["libre"]["videos_poses"]], ["boom"])
        c = ML.consigne(a)
        self.assertIn("ILLUSTRATIONS ALREADY DRAWN", c)
        self.assertIn("===VIDEOS===", c)
        self.assertIn("BUILDING BLOCKS", c)
        self.assertIn("===VIDEOS===", ML._code(a))                     # gardé quand l'IA corrige
        p = os.path.join(d, "projet")
        MH.preparer_projet(a, p)
        page = open(os.path.join(p, "index.html"), encoding="utf-8").read()
        self.assertIn('src="assets/vid_boom.mp4"', page)
        self.assertIn("mix-blend-mode:screen", page)
        self.assertIn('"canon": "assets/img_canon.png"', page)
        self.assertTrue(os.path.exists(os.path.join(p, "assets", "img_canon.png")))
        leger = ML.composition(ML.apercu_leger(MH._ressources_libres(a, p)), "g.js", (), "")
        self.assertIn("width:450.0px", leger)                          # le clip suit l'échelle de l'aperçu léger
        from app import motion_remotion as MR
        r = os.path.join(d, "remotion")
        a2 = copy.deepcopy(a)
        a2["libre"]["tsx"], a2["libre"]["moteur"] = "export const Animation = () => null;", "remotion"
        fiche = MR.preparer_libre(a2, r)["A"]
        self.assertEqual(fiche["IMG"], {"canon": "img_canon.png"})
        self.assertEqual(fiche["VID"][0]["fichier"], "vid_boom.mp4")
        self.assertTrue(os.path.exists(os.path.join(r, "public", "vid_boom.mp4")))
        c2 = ML.consigne(dict(a2, moteur_libre="remotion"))
        self.assertIn("A.IMG.<id>", c2)
        self.assertNotIn("BUILDING BLOCKS", c2)                         # les blocs sont du HTML : HyperFrames seulement

    def test_fenetre_relit_et_corrige(self):
        from app import motion_pro as MP, motion_libre as ML
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("9:16")
        ed.params.update(clef_claude="sk-essai", clef_gemini="g-essai")
        dl = ed.animation_libre()
        dl._test_oui = True
        dl.pro_tours.setValue(2)
        dl.description.setPlainText("des mots tombent, deux canons tirent, tout explose")
        d = tempfile.mkdtemp()
        appels = {"creer": None, "corriger": [], "dessins": 0}
        base = anim_canons(d)
        anc = (MP.preparer, MP.dessiner, MP.source_bloc, MP.modele_video, ML.creer, ML.corriger, ML.verifier_etapes,
               type(dl)._verifier_et_apercu)
        MP.preparer = lambda p, a, i, v: {"complexite": 3, "blocs": ["confetti"], "images": [{"id": "canon", "en": "cannon"}],
                                          "videos": [], "pourquoi": "essai"}

        def dessiner(p, img, dossier, style=""):
            appels["dessins"] += 1
            return {"chemin": base["libre"]["ressources"]["images"]["canon"]["chemin"], "largeur": 160, "hauteur": 140}
        MP.dessiner = dessiner
        MP.source_bloc = lambda nom: "<div>bloc</div>"
        MP.modele_video = lambda p: None

        def creer(p, a):
            appels["creer"] = p.get("ia_modele_claude")
            appels["ressources"] = sorted((a.get("libre") or {}).get("ressources", {}).get("images", {}))
            return dict(base, pro=a.get("pro"))
        ML.creer = creer

        def corriger(p, a, remarque="", erreur=""):
            appels["corriger"].append(remarque)
            return a
        ML.corriger = corriger
        vus = iter([[{"n": 1, "a": 0, "b": 1, "texte": "mots", "vue": False, "remarque": "absents"}],
                    [{"n": 1, "a": 0, "b": 1, "texte": "mots", "vue": True}]])
        ML.verifier_etapes = lambda p, a, v: next(vus)
        type(dl)._verifier_et_apercu = lambda self, t, a: (a, os.path.join(d, "vid_boom.mp4"), [])
        try:
            dl.creer()
            for _ in range(400):
                app.processEvents()
                if appels["creer"] and dl.tache is None and dl.anim and (dl.anim.get("pro") or {}).get("relectures"):
                    break
                import time
                time.sleep(0.02)
        finally:
            (MP.preparer, MP.dessiner, MP.source_bloc, MP.modele_video, ML.creer, ML.corriger, ML.verifier_etapes,
             type(dl)._verifier_et_apercu) = anc
        self.assertEqual(appels["creer"], "claude-opus-5-5")             # complexité 3 : le meilleur modèle
        self.assertEqual(appels["ressources"], ["canon"])
        self.assertEqual(appels["dessins"], 1)
        self.assertEqual(len(appels["corriger"]), 1)                      # un tour a corrigé, le second a tout vu
        self.assertIn("step 1", appels["corriger"][0])
        self.assertIn("Claude Opus", dl.message.text())
        self.assertIn("tout se voit", dl.message.text())
        ed.projet.modifie = False


class TestSimpleImages(unittest.TestCase):
    def test_calques_trois_moteurs(self):
        from PySide6.QtGui import QImage, QColor
        from app import motion as M, motion_html as MH, motion_maison as MM
        d = tempfile.mkdtemp()
        im = QImage(300, 200, QImage.Format_RGB32)
        im.fill(QColor("#ff0000"))
        ch = os.path.join(d, "rouge.png")
        im.save(ch)
        a = M.nouvelle("titre", taille=(1920, 1080))
        a.update(titre="Essai", images=[{"chemin": ch, "place": "coin"}, {"chemin": ch, "place": "fond"},
                                        {"chemin": ch, "place": "haut"}])
        c = M.calques_images(a)
        self.assertEqual(len(c), 2)                                         # deux au plus
        self.assertTrue(c[1]["cover"])
        x, y = int(c[0]["x"] + c[0]["w"] / 2), int(c[0]["y"] + c[0]["h"] / 2)
        img = MM.apercu_image(a, 2.0, (1920, 1080))
        self.assertGreater(img.pixelColor(x, y).red(), 200)               # moteur maison : l'image se voit
        p = os.path.join(d, "projet")
        MH.preparer_projet(a, p)
        page = open(os.path.join(p, "index.html"), encoding="utf-8").read()
        self.assertIn('"src": "assets/image1.png"', page)
        self.assertIn("A.calques", page)
        from app import motion_remotion as MR
        anc = MR.dossier
        MR.dossier = lambda: os.path.join(d, "rem")
        try:
            os.makedirs(os.path.join(d, "rem"), exist_ok=True)
            orig = MR.mettre_a_jour_sources
            MR.mettre_a_jour_sources = lambda: None
            fiche = MR.preparer(a)["A"]
            MR.mettre_a_jour_sources = orig
        finally:
            MR.dossier = anc
        self.assertEqual(fiche["calques"][0]["src"], "image1.png")
        self.assertTrue(os.path.exists(os.path.join(d, "rem", "public", "image1.png")))

    def test_fenetre(self):
        from PySide6.QtGui import QImage, QColor
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        dl = ed.animation()
        d = tempfile.mkdtemp()
        im = QImage(100, 100, QImage.Format_RGB32)
        im.fill(QColor("#00ff00"))
        ch = os.path.join(d, "v.png")
        im.save(ch)
        dl._test_image = ch
        dl._ajouter_image()
        dl._ajouter_image()
        self.assertEqual([x["place"] for x in dl.anim["images"]], ["droite", "gauche"])
        dl._place_image(1, "fond")
        self.assertEqual(dl.lire_fiche()["images"][1]["place"], "fond")
        dl._retirer_image(0)
        self.assertEqual(len(dl.anim["images"]), 1)
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
