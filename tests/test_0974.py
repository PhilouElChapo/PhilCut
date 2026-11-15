"""0.9.74 : son des tampons IA par le cloud (bruitages fabriqués d'après la vidéo par fal.ai, phrase dite par Gemini) ; le
son décrit dans la phrase d'image en est retiré (l'image ne fait aucun son)."""
import os, sys, shutil, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestSonTampons(unittest.TestCase):
    def test_separer(self):
        from app.tampons_ia import separer_son as S
        self.assertEqual(S("Trophée doré, ambiance festive.  en son une voix de commentateur"),
                         ("Trophée doré, ambiance festive", "une voix de commentateur"))
        self.assertEqual(S("Golden trophy, festive mood. and the sound of drumrolls and a few cymbals.")[1],
                         "drumrolls and a few cymbals")
        self.assertEqual(S("fusée qui décolle, on entend le grondement")[0], "fusée qui décolle")
        self.assertEqual(S("Carte météo dessinée"), ("Carte météo dessinée", ""))

    def test_creer_cloud(self):
        from app import tampons_ia as TI, generateurs_video as GV, voix, moteur
        d = tempfile.mkdtemp()
        sfx = os.path.join(d, "sfx.wav")
        moteur.lancer(["-f", "lavfi", "-i", "sine=frequency=300:duration=3", sfx])
        parle = os.path.join(d, "parle.wav")
        moteur.lancer(["-f", "lavfi", "-i", "sine=frequency=600:duration=1", parle])
        demandes, dits = [], []
        anc = (GV.televerser, GV.demande_fal, GV.telecharger, voix.lire_gemini, TI.image)
        GV.televerser = lambda cle, ch: "https://cdn/muet.mp4"
        GV.demande_fal = lambda cle, point, corps, *a, **k: (demandes.append((point, corps)), {"audio": {"url": "https://x/sfx.wav"}})[1]
        GV.telecharger = lambda url, sortie: shutil.copyfile(sfx, sortie) and sortie
        voix.lire_gemini = lambda texte, sortie, params, *a, **k: (dits.append(texte), shutil.copyfile(parle, sortie))[1]

        def image(consigne, chemin, L, H, params, niveau="locale", **k):
            from PySide6.QtGui import QImage, QColor
            q = QImage(L, H, QImage.Format_RGB32)
            q.fill(QColor("orange"))
            q.save(chemin)
            return chemin
        TI.image = image
        params = {"clef_fal": "a:b", "clef_gemini": "x", "tampons_dossier": d}
        try:
            e = TI.creer(params, {"nom": "Victoire", "consigne": "golden trophy", "mouvement": "zoom", "texte": "VICTOIRE !",
                                  "phrase": "Victoire !", "voix": "grave", "bruitages": ["impact"], "duree": 3.0, "son": "cloud",
                                  "son_texte": "drumrolls and cymbals"}, L=320, H=180)
        finally:
            GV.televerser, GV.demande_fal, GV.telecharger, voix.lire_gemini, TI.image = anc
        point, corps = demandes[0]
        self.assertEqual(point, "fal-ai/mmaudio-v2")
        self.assertIn("drumrolls", corps["prompt"])
        self.assertEqual(corps["duration"], 3)
        self.assertTrue(dits[0].startswith("Say in a big, deep, booming voice: Victoire"))
        from app import tampons as T
        f = os.path.join(T.dossier_tampons(params), e["fichier"])
        info = moteur.sonder(f)
        self.assertTrue(info.get("audio"))
        self.assertGreaterEqual(TI.prix_son_cloud("Victoire !", 3), 0.003)


if __name__ == "__main__":
    unittest.main()
