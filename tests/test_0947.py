"""0.9.47 : Audionautix (musiques libres de Jason Shaw, CC BY 4.0) : recherche dans le catalogue lu sur le site,
téléchargement direct sans yt-dlp, crédit gardé avec le fichier et repris dans la description à la publication."""
import os, sys, unittest, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

ACCUEIL = b'''<html><a href="/free-music/jazz">Jazz</a> <a href="https://audionautix.com/free-music/acoustic">Acoustic</a>
<a href="/free-music/jazz">Jazz</a></html>'''
JAZZ = b'''<div data-src="https://audionautix.com/Music/JasonShaw-AUDIONAUTIX-COM_Smooth-Night.mp3"></div>
<audio src="/Music/Cool-Cat.mp3"></audio>'''
ACOU = b'''<a href='//audionautix.com/Music/MorningWalk.mp3'>dl</a> <a href="/Music/Cool-Cat.mp3">x</a>'''


class Rep:
    def __init__(self, corps):
        self.corps, self.headers = corps, {"Content-Length": str(len(corps))}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def read(self, n=-1):
        c, self.corps = (self.corps, b"") if n < 0 else (self.corps[:n], self.corps[n:])
        return c


class TestAudionautix(unittest.TestCase):
    def setUp(self):
        from app import musique_en_ligne as ML
        self.ML = ML
        self.vus = []

        def faux(req, timeout=None):
            u = req.full_url
            self.vus.append((u, req.get_header("User-agent")))
            if u.endswith("/free-music/jazz"):
                return Rep(JAZZ)
            if u.endswith("/free-music/acoustic"):
                return Rep(ACOU)
            if u.endswith(".mp3"):
                return Rep(b"ID3" + b"0" * 1000)
            return Rep(ACCUEIL)
        self.ancien = urllib.request.urlopen
        urllib.request.urlopen = faux

    def tearDown(self):
        urllib.request.urlopen = self.ancien

    def test_catalogue_et_recherche(self):
        cat = self.ML.catalogue_audionautix(rafraichir=True)
        titres = sorted(p["titre"] for p in cat)
        self.assertEqual(titres, ["Cool Cat", "Morning Walk", "Smooth Night"])           # sans doublon
        self.assertTrue(all("PhilCut" in (a or "") for _u, a in self.vus))                  # agent déclaré, jamais déguisé
        r = self.ML.chercher("jazz", "audionautix", 30)
        self.assertEqual(sorted(x["titre"] for x in r), ["Cool Cat", "Smooth Night"])
        self.assertTrue(all(x["libre"] and "CC BY 4.0" in x["licence"] and "audionautix.com" in x["credit"] for x in r))
        self.assertEqual([x["titre"] for x in self.ML.chercher("matin", "audionautix", 30)], [])
        self.assertEqual([x["titre"] for x in self.ML.chercher("morning", "audionautix", 30)], ["Morning Walk"])

    def test_telechargement_et_credit(self):
        from app import musique_ia as MI, musiques
        self.ML.catalogue_audionautix(rafraichir=True)
        r = self.ML.chercher("smooth", "audionautix", 5)[0]
        d = os.path.join(os.environ["APPDATA"], "musiques_audionautix")
        from app import moteur
        ancien = moteur.lancer
        moteur.lancer = lambda args, *a, **k: open(args[-1], "wb").write(b"ID3")
        try:
            f = self.ML.telecharger(r, d)
        finally:
            moteur.lancer = ancien
        self.assertTrue(os.path.exists(f))
        self.assertTrue(MI.droits(f)["libre"])
        credit = open(os.path.splitext(f)[0] + ".credit.txt", encoding="utf-8").read()
        self.assertIn("Music by audionautix.com", credit)

    def test_fenetre(self):
        from app.dialogues_musique_ia import DialogueMusiqueEnLigne
        m = DialogueMusiqueEnLigne(None, {})
        noms = [m.source.itemText(i) for i in range(m.source.count())]
        self.assertTrue(any("Audionautix" in n for n in noms))
        self.assertEqual([n.lower() for n in noms], sorted(n.lower() for n in noms))
        m.source.setCurrentIndex(m.source.findData("audionautix"))
        m._maj()
        self.assertTrue(m.b_installer.isHidden())                         # pas besoin de yt-dlp


if __name__ == "__main__":
    unittest.main()
