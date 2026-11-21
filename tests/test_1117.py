"""1.1.7 : bibliothèque : vignette choisie parmi les photos, description écrite d'après les photos, raison claire quand Gemini
ne rend pas d'image, second essai après une coupure TLS."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def image(d, nom, couleur=(200, 120, 60)):
    from PIL import Image
    p = os.path.join(d, nom)
    Image.new("RGB", (64, 64), couleur).save(p)
    return p


class TestGemini(unittest.TestCase):
    def test_raison_claire(self):
        from app import ia
        m = ia.pas_d_image({"candidates": [{"finishReason": "IMAGE_SAFETY", "content": {"parts": [{"text": "I can't create that."}]}}]})
        self.assertIn("IMAGE_SAFETY", m)
        self.assertIn("personne réelle", m)
        self.assertIn("I can't create that.", m)
        self.assertIn("Inventé", ia.pas_d_image({}))
        self.assertIn("PROHIBITED_CONTENT", ia.pas_d_image({"promptFeedback": {"blockReason": "PROHIBITED_CONTENT"}}))

    def test_second_essai_tls(self):
        import urllib.error, urllib.request
        from app import ia
        appels = []

        class Rep:
            status = 200

            def read(self):
                return b'{"ok": 1}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def faux(r, timeout=None):
            appels.append(1)
            if len(appels) == 1:
                raise urllib.error.URLError("[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol")
            return Rep()
        anc, anc_s = urllib.request.urlopen, ia.time.sleep
        urllib.request.urlopen, ia.time.sleep = faux, lambda s: None
        try:
            self.assertEqual(ia._http("https://exemple.invalid/x", {"a": 1}), {"ok": 1})
        finally:
            urllib.request.urlopen, ia.time.sleep = anc, anc_s
        self.assertEqual(len(appels), 2)


class TestBibliotheque(unittest.TestCase):
    def test_vignette_et_description(self):
        from app.fenetre import Fenetre
        from app import bibliotheque_creations as B, ia, widgets
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        ed.params["sync_dossier"] = d
        dl = ed.bibliotheque_creations()
        dl._test_oui = True
        dl.nouveau("personnage")
        anc = widgets.ouvrir_fichiers
        widgets.ouvrir_fichiers = lambda *a, **k: [image(d, "f1.png"), image(d, "f2.png", (20, 40, 200))]
        try:
            dl.ajouter_photos()
        finally:
            widgets.ouvrir_fichiers = anc
        dl._ameliorer(dl.desc)                                    # description vide : dit tout de suite
        self.assertIn("Décrire d'après les photos", dl.etat.text())
        role = dl._photos(dl.courante)[1][0]
        dl.choisir_vignette(role)
        self.assertEqual(B.apercu(dl.courante), dl.courante["fichiers"][role])
        recu = {}

        def faux(params, consignes, texte, images=None, **k):
            recu["c"], recu["i"] = consignes, images
            return "Femme d'une trentaine d'années, longs cheveux blonds, allure élégante, tailleur clair."
        anc = ia.demander
        ia.demander = faux
        try:
            dl.decrire_photos()
            dl.tache.wait(10000) if getattr(dl, "tache", None) else None
            for _ in range(20):
                app.processEvents()
        finally:
            ia.demander = anc
        self.assertEqual(len(recu["i"]), 2)
        self.assertTrue(all(isinstance(x, bytes) and x[:2] == b"\xff\xd8" for x in recu["i"]))    # des octets JPEG
        self.assertIn("Ne nomme jamais", recu["c"])
        self.assertIn("cheveux blonds", dl.desc.texte())
        self.assertIn("Inventé", dl.etat.text())
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
