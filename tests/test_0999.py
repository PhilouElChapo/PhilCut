"""0.9.99 : animations (motion design) : charte, moteur maison, composition HyperFrames, fiche Remotion, conseil du moteur,
fenêtre ; Higgsfield et HeyGen (clefs, crédit, rendu cloud simulé)."""
import json, os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=120):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestCharte(unittest.TestCase):
    def test_contraste_et_correction(self):
        from app import charte as C
        self.assertAlmostEqual(C.contraste("#FFFFFF", "#000000"), 21.0, places=1)
        ch = C.complete({"couleurs": {"fond": "#0B1020", "texte": "#202020", "accent": "#101010"}})
        self.assertTrue(C.avertissements(ch))
        ok = C.corriger(ch)
        self.assertFalse(C.avertissements(ok))

    def test_depuis_image(self):
        import numpy as np, cv2
        from app import charte as C
        d = tempfile.mkdtemp()
        img = np.zeros((100, 200, 3), np.uint8)
        img[:, :140] = (40, 30, 20)
        img[:, 140:] = (0, 140, 255)             # orange (BGR)
        f = os.path.join(d, "logo.png")
        cv2.imwrite(f, img)
        ch = C.depuis_image(f)
        r, g, b = C.hex_rvb(ch["couleurs"]["accent"])
        self.assertGreater(r, 200)
        self.assertEqual(ch["logo"], f)

    def test_site(self):
        from app import charte as C
        page = ('<html><head><title>Exemple</title><meta name="theme-color" content="#00a651">'
                '<link rel="icon" href="/logo.png"></head><body style="font-family:Montserrat,sans-serif"></body>')
        a = C.analyser_site("https://exemple.fr/", page, "a{color:#00a651} body{background:#ffffff}")
        self.assertEqual(a["couleurs"][0][0], "#00A651")
        self.assertEqual(a["polices"][0], "Montserrat")
        self.assertEqual(a["logo"], "https://exemple.fr/logo.png")

    def test_garder(self):
        from app import charte as C
        p = {}
        ch = C.garder(p, C.depuis_couleurs([("#ff0000", 0.5), ("#111111", 0.5)], "Rouge"))
        self.assertEqual(C.active(p)["id"], ch["id"])
        C.retirer(p, ch["id"])
        self.assertEqual(C.active(p)["id"], "defaut")


class TestMotion(unittest.TestCase):
    def test_donnees(self):
        from app import motion as M
        self.assertEqual(M.lire_donnees("Mois\tVisites\nJanv.\t3 120\nFévr.\t4.380,5"), [["Janv.", 3120.0], ["Févr.", 4380.5]])
        self.assertEqual(M.lire_donnees("Lundi : 12 €\nMardi 15"), [["Lundi", 12.0], ["Mardi", 15.0]])
        self.assertEqual(M.nombre(34390, langue="fr"), "34 390")
        d = tempfile.mkdtemp()
        f = os.path.join(d, "t.csv")
        open(f, "w", encoding="utf-8").write("Trimestre;CA\nT1;120\nT2;150\n")
        self.assertEqual(M.lire_fichier(f), [["T1", 120.0], ["T2", 150.0]])

    def test_ia(self):
        from app import motion as M, assistant_creation as A
        a = M.nouvelle("compteur")
        anc = A.demander
        A.demander = lambda *x, **k: {"genre": "barres", "titre": "Ventes", "donnees": [["T1", 10], ["T2", 20]], "suffixe": " €",
                                      "reglages": {"rebond": 5}, "message": "compris"}
        try:
            b, msg = M.preparer_ia({}, "les ventes", a)
        finally:
            A.demander = anc
        self.assertEqual((b["genre"], b["valeur"], b["suffixe"], msg), ("barres", 30.0, " €", "compris"))
        self.assertEqual(b["reglages"]["rebond"], 1.0)

    def test_conseil_et_prix(self):
        from app import motion as M
        a = M.nouvelle()
        self.assertEqual(M.conseiller(a, {})[0], "maison")
        self.assertEqual(M.prix(a, "maison"), 0.0)
        self.assertEqual(M.prix(a, "hyperframes_cloud"), 0.10)
        self.assertFalse(M.etat("hyperframes_cloud", {})[0])
        self.assertTrue(M.etat("hyperframes_cloud", {"clef_heygen": "k"})[0])
        self.assertFalse(M.etat("remotion", {})[0])

    def test_maison(self):
        from app import motion as M, motion_maison as MM, moteur
        d = tempfile.mkdtemp()
        for genre, taille in (("chiffres", (320, 180)), ("titre", (180, 320))):
            a = M.nouvelle(genre, taille=taille)
            a["duree"] = 1.2
            f = MM.fabriquer(a, os.path.join(d, genre + ".mp4"))
            info = moteur.sonder(f)
            self.assertAlmostEqual(float(info["duree"]), 1.2, delta=0.15)
        a = M.nouvelle("barres", taille=(320, 180))
        a.update(duree=1.0, transparent=True)
        f = MM.fabriquer(a, os.path.join(d, "t.mp4"))
        self.assertTrue(f.endswith(".mov") and os.path.getsize(f) > 1000)
        img = MM.apercu_image(M.nouvelle("courbe"), 3.0, (320, 180))
        self.assertEqual((img.width(), img.height()), (320, 180))

    def test_composition_html(self):
        from app import motion as M, motion_html as MH
        a = M.nouvelle("chiffres", taille=(1080, 1920))
        d = MH.preparer_projet(a, tempfile.mkdtemp())
        h = open(os.path.join(d, "index.html"), encoding="utf-8").read()
        self.assertIn('data-composition-id="philcut"', h)
        self.assertIn('window.__timelines["philcut"]', h)
        self.assertIn("modifiers", h)
        self.assertTrue(os.path.exists(os.path.join(d, "assets", "Poppins-Bold.ttf")))
        A = json.loads(h.split("const A = ")[1].split(";\nconst tl")[0])
        self.assertTrue(A["vertical"])
        self.assertEqual(A["zh"], int(1920 * 0.62))

    def test_progressions(self):
        from app import motion_html as MH, motion_remotion as MR
        self.assertAlmostEqual(MH.lire_progression("Rendering 45%"), 0.45)
        self.assertAlmostEqual(MR.lire_progression("Rendered 30/120"), 0.25)

    def test_heygen_simule(self):
        from app import motion as M, motion_html as MH
        appels = []

        def faux(methode, chemin, cle, corps=None, delai=60):
            appels.append((methode, chemin))
            if chemin == "/v3/assets/direct-uploads":
                return {"data": {"asset_id": "A1", "upload_url": "http://x", "upload_headers": {}}}
            if chemin == "/v3/hyperframes/renders":
                return {"data": {"render_id": "R1"}}
            if chemin.startswith("/v3/hyperframes/renders/"):
                return {"data": {"status": "completed", "video_url": "http://v"}}
            return {"data": {}}
        import urllib.request
        anc = (MH._heygen, urllib.request.urlopen, MH.time.sleep)
        d = tempfile.mkdtemp()

        class Rep:
            def __init__(s, *a, **k):
                pass

            def __enter__(s):
                return s

            def __exit__(s, *a):
                return False

            def read(s, *a):
                return b""
        MH._heygen = faux
        urllib.request.urlopen = lambda *a, **k: Rep()
        MH.time.sleep = lambda s: None
        try:
            a = M.nouvelle("titre", taille=(320, 180))
            r = MH.rendre_cloud({"clef_heygen": "k"}, a, os.path.join(d, "x.mp4"))
        finally:
            MH._heygen, urllib.request.urlopen, MH.time.sleep = anc
        self.assertTrue(r.endswith("x.mp4"))
        self.assertEqual([c[1] for c in appels][:4], ["/v3/assets/direct-uploads", "/v3/assets/A1/complete", "/v3/hyperframes/renders",
                                                       "/v3/hyperframes/renders/R1"])

    def test_remotion_fiche(self):
        from app import motion as M, motion_remotion as MR
        d = tempfile.mkdtemp()
        anc = MR.dossier
        MR.dossier = lambda: d
        try:
            props = MR.preparer(M.nouvelle("barres"))
        finally:
            MR.dossier = anc
        self.assertEqual(props["A"]["cadence"], 30)
        self.assertTrue(any(p[1] == "Poppins-Bold.ttf" for p in props["A"]["polices"]))
        self.assertTrue(os.path.exists(os.path.join(d, "public", "Poppins-Bold.ttf")))


class TestFournisseurs(unittest.TestCase):
    def test_higgsfield(self):
        from app import generateurs_video as GV
        envoyes = []

        def faux(url, cle, corps=None, delai=120):
            envoyes.append((url, corps))
            if corps is not None and "status" not in url:
                return {"request_id": "r1", "status_url": "https://api.higgsfield.ai/requests/r1/status"}
            return {"status": "completed", "video": {"url": "https://cdn/v.mp4"}}
        anc = (GV._http_hf, GV.telecharger, GV.time.sleep)
        GV._http_hf, GV.telecharger, GV.time.sleep = faux, (lambda u, s: s), (lambda s: None)
        try:
            r = GV.generer({"clef_higgsfield": "id:secret"}, "hf-kling-25-pro", "a plane", "/tmp/x.mp4", duree=7)
        finally:
            GV._http_hf, GV.telecharger, GV.time.sleep = anc
        self.assertEqual(r, "/tmp/x.mp4")
        self.assertTrue(envoyes[0][0].endswith("/kling-video/v2.5-turbo/pro/text-to-video"))
        self.assertEqual(envoyes[0][1]["duration"], 10)

    def test_credit_et_messages(self):
        from app import credit_ia as CI, taches
        self.assertIn("Higgsfield", taches.credit_epuise("Solde Higgsfield épuisé (rien n'a été fabriqué)"))
        self.assertEqual(CI.fournisseur_epuise("Crédit HeyGen épuisé (rien n'a été rendu)"), "heygen")
        self.assertIn("HeyGen", CI.texte_credit("heygen", None))
        from app import motion_html as MH
        anc = MH._heygen
        MH._heygen = lambda *a, **k: {"data": {"wallet": {"currency": "usd", "remaining_balance": 42.5}}}
        try:
            self.assertEqual(MH.credit_heygen("k"), (42.5, "USD"))
        finally:
            MH._heygen = anc


class TestFenetre(unittest.TestCase):
    def test_animation(self):
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        dl = ed.animation()
        dl._test_oui = True
        self.assertTrue(dl.isVisible())
        dl.genre.setCurrentIndex(dl.genre.findData("compteur"))
        dl.duree.setValue(2.0)
        dl.format.setCurrentIndex(dl.format.findData([1080, 1080]))
        app.clipboard().setText("A\t10\nB\t20\nC\t5")
        dl.coller()
        self.assertEqual(dl.anim["valeur"], 35.0)
        dl.choisir_variante(2)
        self.assertEqual(dl.anim["reglages"]["lueur"], 0.0)
        dl.r_moteurs["maison"].setChecked(True)
        dl.anim["taille"] = [240, 240]
        dl.format.setItemData(0, [240, 240])
        dl.format.setCurrentIndex(0)
        dl.fabriquer()
        self.assertTrue(attendre(lambda: dl.resultat is not None and dl.tache is None))
        self.assertTrue(os.path.exists(dl.resultat) and os.path.exists(dl.resultat + ".motion.json"))
        from app.dialogues_motion import ResultatAnimation
        r = ResultatAnimation(ed, dl.resultat, dl.anim)
        n = len(ed.projet.clips_piste("video"))
        r.inserer()
        self.assertEqual(len(ed.projet.clips_piste("video")), n + 1)
        d = dl.projet_html()
        self.assertTrue(os.path.exists(os.path.join(d, "index.html")))
        dl.r_moteurs["remotion"].setChecked(True)
        self.assertTrue(dl.licence.isVisible())
        dl.close()
        ed.projet.modifie = False

    def test_charte_fenetre(self):
        from app.dialogues_motion import DialogueCharte
        from app import charte as C
        p = {}

        class P(dict):
            def enregistrer(self):
                pass
        pp = P()
        d = DialogueCharte(None, pp)
        d.nouvelle()
        d.nom.setText("Bleu")
        d.ch["couleurs"]["texte"] = "#0B1020"
        d._maj()
        self.assertTrue(d.avert.text())
        d._lisible()
        self.assertFalse(d.avert.text())
        d.valider()
        self.assertEqual(C.active(pp)["nom"], "Bleu")


if __name__ == "__main__":
    unittest.main()
