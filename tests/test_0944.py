"""0.9.44 : fenêtre de mise à jour comme PhilPDF, recherche YouTube avec vos mots exacts et un compte juste, Fabrique
musique (morceau et voix cherchés en ligne, voix seule d'un morceau), logo dans la vignette, vignette de la vidéo envoyée."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


class TestMaj(unittest.TestCase):
    def test_comme_philpdf(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QWidget
        from app.dialogues_maj import DialogueMaj
        w = QWidget()
        d = DialogueMaj(w, "v9", {})
        self.assertFalse(d.windowFlags() & Qt.WindowMinimizeButtonHint)
        self.assertEqual(d.b_reduire.text(), "Réduire")

        class EnCours:
            def isRunning(self):
                return True
        vraie = d.tache
        d.tache = EnCours()
        d.show()
        d.close()                                   # la croix range la fenêtre, rien ne s'arrête
        self.assertFalse(d.isVisible())
        d.show()
        d.reject()
        self.assertFalse(d.isVisible())
        d.tache = vraie


class TestRechercheYouTube(unittest.TestCase):
    def test_mots_exacts_et_compte(self):
        from app import videos_en_ligne as VL
        vus = []

        def faux(args, *a, **k):
            vus.append(args)
            url = args[-1]
            shorts = "%23shorts" in url or "#shorts" in url
            return [json.dumps({"id": f"{'s' if shorts else 'v'}{i}", "title": "x", "duration": 30 if shorts else 300,
                                "url": f"https://www.youtube.com/{'shorts/' if shorts else 'watch?v='}{i}"}) for i in range(60)]
        ancien = VL._lancer_ytdlp
        VL._lancer_ytdlp = faux
        try:
            res = VL.chercher_youtube("tonton flingur", 30, "tout")
            self.assertEqual(len(res), 30)
            self.assertEqual(sum(1 for r in res if r["short"]), 10)
            self.assertIn("sp=QgIIAQ%3D%3D", vus[0][-1])                    # orthographe exacte : pas de correction
            self.assertIn("search_query=tonton+flingur", vus[0][-1])
            self.assertEqual(len(VL.chercher_youtube("x", 30, "videos")), 30)
            self.assertEqual(len(VL.chercher_youtube("x", 30, "shorts")), 30)
        finally:
            VL._lancer_ytdlp = ancien

    def test_repli_si_page_refusee(self):
        from app import videos_en_ligne as VL
        appels = []

        def faux(args, *a, **k):
            appels.append(args[-1])
            if args[-1].startswith("https://www.youtube.com/results"):
                return []
            return [json.dumps({"id": "a", "title": "t", "url": "https://www.youtube.com/watch?v=a"})]
        ancien = VL._lancer_ytdlp
        VL._lancer_ytdlp = faux
        try:
            self.assertEqual(len(VL._recherche_brute("abc", 5)), 1)
            self.assertTrue(appels[-1].startswith("ytsearch5:"))
        finally:
            VL._lancer_ytdlp = ancien


class TestFabriqueMusique(unittest.TestCase):
    def test_menus_et_utiliser(self):
        from PySide6.QtWidgets import QPushButton
        from app.dialogues_musique_ia import DialogueFabriqueMusique, DialogueMusiqueEnLigne
        d = DialogueFabriqueMusique(None, {})
        b = [x for x in d.findChildren(QPushButton) if x.text() == "Choisir un morceau…"][0]
        self.assertTrue(any("Chercher en ligne" in a.text() for a in b.menu().actions()))
        r = [x for x in d.findChildren(QPushButton) if x.text() == "Choisir l'enregistrement…"][0]
        self.assertEqual(len(r.menu().actions()), 3)
        recu = []
        m = DialogueMusiqueEnLigne(None, {}, utiliser=recu.append, libelle_utiliser="S'inspirer de ce morceau")
        self.assertFalse(m.b_utiliser.isHidden())
        m.dernier = "/tmp/morceau.mp3"
        m._utiliser()
        self.assertEqual(recu, ["/tmp/morceau.mp3"])

    def test_extraire_voix(self):
        from app import creatif, packs_ia as P
        self.assertIsNotNone(creatif.separation_manquante({}))           # rien d'installé : on dit quoi faire
        anc = (P.modele_actif, P.installe, P.modeles, P.etat, creatif._moteur, creatif._lancer, creatif._extrait_wav)
        vu = {}
        P.modele_actif = lambda g, p=None: "voix_seule" if g == "separation" else None
        P.installe = lambda c: True
        P.modeles = lambda *a, **k: {"voix_seule": {"moteur_gpu": "musique_gpu"}}
        P.etat = lambda: {"voix_seule": {"roles": {"dit": "acestep-v15-base-Q4_K_M.gguf"}}}
        creatif._moteur = lambda *a, **k: "musique"
        creatif._extrait_wav = lambda src, duree, d: os.path.join(d, "source.wav")

        def lancer(genre, args, *a, **k):
            req = json.load(open(args[args.index("--request") + 1], encoding="utf-8"))
            vu.update(req)
            d = os.path.dirname(args[args.index("--request") + 1])
            from app import moteur
            moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=300:d=1", os.path.join(d, "voix0.wav")])
        creatif._lancer = lancer
        try:
            sortie = os.path.join(os.environ["APPDATA"], "voix.wav")
            creatif.extraire_voix("/tmp/x.mp3", sortie, {})
            self.assertTrue(os.path.exists(sortie))
            self.assertEqual((vu["task_type"], vu["track"]), ("extract", "vocals"))
            self.assertIn("base", vu["synth_model"])
        finally:
            P.modele_actif, P.installe, P.modeles, P.etat, creatif._moteur, creatif._lancer, creatif._extrait_wav = anc

    def test_catalogue_choix_gguf(self):
        sys.path.insert(0, os.path.join(commun.RACINE, "outils_dev"))
        import moteurs_creatifs as MC
        voeu = MC.MODELES["voix_seule"][2][2][2]
        self.assertEqual(MC._choisir({"acestep-v15-base-Q8_0.gguf": {}}, voeu), "acestep-v15-base-Q8_0.gguf")
        self.assertEqual(MC._choisir({"acestep-v15-base-Q5_K_M.gguf": {}}, voeu), None)
        self.assertEqual(MC._choisir({"acestep-v15-base-Q4_0.gguf": {}}, voeu), "acestep-v15-base-Q4_0.gguf")


class TestVignette(unittest.TestCase):
    def test_logo_dans_la_vignette(self):
        from PySide6.QtGui import QImage, QColor
        import numpy as np
        from app import vignette as V
        logo = os.path.join(os.environ["APPDATA"], "logo.png")
        q = QImage(100, 50, QImage.Format_ARGB32)
        q.fill(QColor(255, 0, 0))
        q.save(logo)
        rec = V.nouvelle_recette()
        img = np.zeros((360, 640, 3), np.uint8)
        sans, _i = V.composer(rec, img, None, 640, 360)
        rec.update(logo=logo, logo_coin="haut_droite")
        avec, _i = V.composer(rec, img, None, 640, 360)
        c = avec.pixelColor(640 - 30, 30)
        self.assertGreater(c.red(), 200)
        self.assertLess(sans.pixelColor(640 - 30, 30).red(), 100)

    def test_fenetre_vignette(self):
        from PySide6.QtWidgets import QPushButton
        from app.fenetre import Fenetre
        from app.dialogues_vignette import DialogueVignette
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        d = DialogueVignette(ed, None, "vignette")
        self.assertIn("miniature YouTube", d.windowTitle())
        textes = {b.text(): b for b in d.findChildren(QPushButton)}
        self.assertFalse(textes["Utiliser comme vignette de la vidéo"].isHidden())
        self.assertTrue(textes["Poser dans le film (au-dessus, à la ligne rouge)"].isHidden())
        self.assertIn("Atelier de logo…", textes)
        ed.projet.modifie = False


class TestPublication(unittest.TestCase):
    def test_vignette_envoyee(self):
        import urllib.request
        from app import publication as P
        vu = {}

        class Rep:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                return b"{}"
        anc = (urllib.request.urlopen, P._acces)
        P._acces = lambda journal=None, compte=None: "jeton"
        urllib.request.urlopen = lambda req, timeout=None: (vu.update(url=req.full_url, n=len(req.data)), Rep())[1]
        try:
            img = os.path.join(os.environ["APPDATA"], "v.jpg")
            open(img, "wb").write(b"\xff\xd8" + b"0" * 100)
            self.assertIsNone(P.envoyer_vignette("abc123", img))
            self.assertIn("thumbnails/set?videoId=abc123", vu["url"])
        finally:
            urllib.request.urlopen, P._acces = anc


if __name__ == "__main__":
    unittest.main()
