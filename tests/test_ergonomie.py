"""Ergonomie (retours du premier test) : partie sélectionnée gardée ou supprimée, liste d'Annuler / Rétablir, dossiers
du système, cases dont le texte passe à la ligne, Préférences sans défilement horizontal, son par piste dans l'aperçu."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.projet import Projet, fin_clip


def projet():
    p = Projet()
    p.d["medias"] = [{"id": "m1", "nom": "a.mp4", "genre": "video", "fiche": {"duree": 10}, "chemin": "/x/a.mp4"}]
    p.ajouter_clip("m1")
    p.ajouter_titre("Titre", 2, 8)
    return p


class TestPartie(unittest.TestCase):
    def test_supprimer(self):
        p = projet()
        self.assertTrue(p.partie(3, 5, False))
        self.assertEqual([(c["debut"], round(fin_clip(c), 3)) for c in p.clips], [(0.0, 3.0), (3, 8.0)])
        self.assertEqual((p.titres[0]["debut"], p.titres[0]["fin"]), (2.0, 6.0))
        self.assertAlmostEqual(p.duree(), 8.0)

    def test_garder(self):
        p = projet()
        self.assertTrue(p.partie(5, 3, True))           # ordre indifférent
        self.assertEqual(len(p.clips), 1)
        self.assertAlmostEqual(fin_clip(p.clips[0]), 2.0)
        self.assertAlmostEqual(p.clips[0]["src_debut"], 3.0)
        self.assertFalse(p.partie(1, 1.01, True))


class TestHistorique(unittest.TestCase):
    def test_libelles(self):
        p = projet()
        c = p.clips[0]
        p.marquer()
        c["vitesse"] = 2
        p.marquer()
        c["effets"] = [{"id": "glow"}]
        p.marquer()
        p.couper(c["id"], 2.0)
        annul, retab = p.historique()
        self.assertEqual(annul[:3], ["Coupe de « a.mp4 »", "Effets de « a.mp4 »", "Vitesse de « a.mp4 »"])
        p.annuler()
        self.assertEqual(p.historique()[1], ["Coupe de « a.mp4 »"])


class TestInterfaceErgonomie(unittest.TestCase):
    def test_dossier_systeme(self):
        from app.session import dossier_systeme
        self.assertTrue(os.path.isdir(dossier_systeme("videos")))

    def test_case_longue(self):
        from app.widgets import CaseLongue
        c = CaseLongue("un texte très long " * 20)
        vu = []
        c.toggled.connect(vu.append)
        c.setChecked(True)
        self.assertTrue(c.isChecked())
        self.assertEqual(vu, [True])
        c.resize(300, 100)
        self.assertLess(c.minimumSizeHint().width(), 300)

    def test_preferences_sans_defilement_horizontal(self):
        from app.config import Parametres
        from app.preferences import DialoguePreferences
        from PySide6.QtCore import Qt
        d = DialoguePreferences(None, Parametres())
        d.resize(760, 600)
        d.show()
        for i in range(d.onglets.count()):
            d.onglets.setCurrentIndex(i)
            app.processEvents()
            z = d.onglets.widget(i)
            self.assertEqual(z.horizontalScrollBarPolicy(), Qt.ScrollBarAlwaysOff)
            self.assertLessEqual(z.widget().minimumSizeHint().width(), z.viewport().width() + 2, d.onglets.tabText(i))
        d.close()


if __name__ == "__main__":
    unittest.main()
