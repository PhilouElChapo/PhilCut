"""0.4.2 : confort — timeline qui tient dans la hauteur visible (pistes tassées, en-têtes compacts), colonne des médias
repliable et mémorisée, onglets du volet lisibles, galerie des Goodies, accueil sans cadre vide, badges dont le texte tient."""
import os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import goodies as GO, moteur


class TestConfort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["colonne_gauche"] = "complet"
        pa["recents"] = []
        pa.enregistrer()
        from app.fenetre import Fenetre
        cls.d = tempfile.mkdtemp()
        v = commun.video_test(cls.d, "a.mp4", duree=4)
        cls.f = Fenetre()
        cls.f.resize(1366, 768)
        cls.f.show()
        app.processEvents()
        cls.ed = cls.f.nouveau_projet("16:9")
        m = cls.ed.projet.ajouter_media(v, moteur.sonder(v))
        cls.ed.ajouter_a_la_timeline(m["id"])
        for _ in range(2):
            cls.ed.timeline._ajouter_piste("video")
            cls.ed.timeline._ajouter_piste("audio")
        cls.ed.projet.ajouter_titre("Bonjour", 0, 3)
        cls.ed.rafraichir()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ed.projet.modifie = False
        cls.ed.catalogue.fermer()
        cls.f.attendre_taches()
        cls.f.close()

    def test_timeline_tient(self):
        tl = self.ed.timeline
        tl.resize(tl.width(), 260)
        app.processEvents()
        self.assertLessEqual(tl.hauteur_totale(), tl.viewport().height())          # toutes les pistes visibles
        tl.hauteur_images(1.6)                                                       # agrandies à la main : on défile
        self.assertGreater(tl.hauteur_totale(), tl.viewport().height())
        tl.h_video = 74
        tl.reconstruire()

    def test_colonne_gauche(self):
        ed = self.ed
        ed.replier_gauche(True)
        app.processEvents()
        self.assertFalse(ed.gauche_complet.isVisible())
        self.assertTrue(ed.gauche_icones.isVisible())
        self.assertEqual(ed.params["colonne_gauche"], "icones")
        self.assertLessEqual(ed.split_h.sizes()[0], 72)
        ed.replier_gauche(False)
        app.processEvents()
        self.assertTrue(ed.gauche_complet.isVisible())

    def test_onglets_lisibles(self):
        tb = self.ed.volet.tabBar()
        self.assertFalse(self.ed.volet.usesScrollButtons())
        self.assertEqual(tb.count(), 3)

    def test_galerie_goodies(self):
        from app import dialogues_effets_plus as DP
        gal = DP.GalerieGoodies(None, {})
        self.assertGreater(gal.liste.count(), 20)
        gal.famille.setCurrentIndex(gal.famille.findData("autocollants"))
        self.assertEqual(gal.liste.count(), 3)
        n = len(self.ed.projet.goodies)
        with mock.patch.object(DP.GalerieGoodies, "exec", lambda self: (self.famille.setCurrentIndex(self.famille.findData("pharmacie")), 1)[1]):
            self.ed.nouveau_goodie()
        self.assertEqual(len(self.ed.projet.goodies), n + 1)
        self.assertEqual(self.ed.inspecteur._cible[0], "goodie")

    def test_accueil_vide(self):
        acc = self.f.onglets.widget(0)
        acc.rafraichir()
        self.assertEqual(acc.liste.count(), 1)
        self.assertIn("Nouveau projet", acc.liste.item(0).text())

    def test_badges(self):
        for genre in ("croix", "confettis", "lune", "immatriculation"):
            g = {"genre": genre, "debut": 0, "fin": 5, "options": {"texte": "F-GHIJ très long texte"}}
            self.assertFalse(GO.image(g, 1.0, 120).isNull())


if __name__ == "__main__":
    unittest.main()
