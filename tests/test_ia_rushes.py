"""0.4.3 : IA sur les rushes, sur ce poste — analyse par le modèle de vision local (simulé ici), recherche dans la
bibliothèque, étiquette depuis un texte lu, effets orbite et personne en code."""
import os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import analyse_locale as AL, moteur
from app.projet import Projet

REPONSE = '{"nom": "Décollage de Cannes", "resume": "Un petit avion décolle face à la mer.", "lieux_objets": ["avion", "mer", "piste"], "textes": ["F-GHIJ"]}'


class TestAnalyseLocale(unittest.TestCase):
    def test_analyse_et_recherche(self):
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=3)
        p = Projet()
        m = p.ajouter_media(v, moteur.sonder(v))
        with mock.patch("app.ia_locale.modele_actif", return_value="vision_leger"), \
                mock.patch("app.ia_locale.generer", return_value="Voici : " + REPONSE) as gen:
            out = AL.analyser(m, {})
        self.assertEqual(len(gen.call_args[0][2]), 4)                    # quatre images envoyées au modèle LOCAL
        self.assertEqual(out["textes"], ["F-GHIJ"])
        self.assertTrue(AL.correspond(m, "decollage"))                    # accents ignorés
        self.assertTrue(AL.correspond(m, "MER avion"))
        self.assertFalse(AL.correspond(m, "montagne"))
        with mock.patch("app.ia_locale.modele_actif", return_value=None):
            with self.assertRaises(AL.ErreurAnalyse):
                AL.analyser(m, {})

    def test_bibliotheque(self):
        from app.editeur import Bibliotheque
        p = Projet()
        p.d["medias"] = [{"id": "a", "nom": "GOPR001.mp4", "genre": "video", "chemin": "/x", "ia_locale": {"nom": "Vol", "resume": "La mer", "textes": []}},
                         {"id": "b", "nom": "GOPR002.mp4", "genre": "video", "chemin": "/y"}]
        b = Bibliotheque()
        b.remplir(p)
        self.assertEqual(b.count(), 2)
        b.filtrer("mer")
        self.assertEqual(b.count(), 1)
        b.filtrer("")
        self.assertEqual(b.count(), 2)


class TestEffetsMatrix(unittest.TestCase):
    def test_orbite_et_code(self):
        import numpy as np
        from app import export, generateurs as G
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=3)
        p = Projet()
        m = p.ajouter_media(v, moteur.sonder(v))
        c = p.ajouter_clip(m["id"])
        c["effets"] = [{"id": "orbite", "params": {}}]
        export.image_rendue(p, 1.0, os.path.join(d, "o.png"), largeur=320)

        def masques(i):
            mk = np.zeros((180, 320), np.uint8)
            mk[40:150, 120:200] = 255
            return mk
        motif, n = G.code_personne(tempfile.mkdtemp(), 320, 180, 10, 2.0, masques)
        import cv2
        img = cv2.imread(motif % 10, cv2.IMREAD_UNCHANGED)
        self.assertGreater(img[90, 160, 3], 100)                         # dans la silhouette : code
        self.assertEqual(img[10, 10, 3], 0)                              # hors silhouette : rien


if __name__ == "__main__":
    unittest.main()
