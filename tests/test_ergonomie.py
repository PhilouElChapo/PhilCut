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


class TestEffetSurUnePartie(unittest.TestCase):
    def test_morceau(self):
        import tempfile
        from app.config import Parametres
        p = Parametres()
        p["bienvenue_vue"] = True
        p["maj_auto"] = False
        p["synchro"] = False
        p.enregistrer()
        from app.fenetre import Fenetre
        from app import taches
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "long.mp4", duree=12)
        f = Fenetre()
        ed = f.nouveau_projet("16:9")

        class T:
            arret = False

            @staticmethod
            def avancer(fr, t=""):
                pass
        r = taches.importer_media(T, v, f.params, avec_proxy=False)
        m = ed.projet.ajouter_media(v, r["fiche"])
        ed.ajouter_a_la_timeline(m["id"])
        ed.timeline.aller_a(3.0)
        ed.timeline.marquer_zone(0)
        ed.timeline.aller_a(5.0)
        ed.timeline.marquer_zone(1)
        # à la souris (0.9.4) : double-clic sur la règle des temps au début, puis à la fin de la partie
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt, QPoint
        from app.timeline import MARGE_G
        tl = ed.timeline
        tl.effacer_zone()
        f.show()
        app.processEvents()
        x = lambda t: tl.mapFromScene(MARGE_G + t * tl.pps, 5).x()
        QTest.mouseDClick(tl.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(x(3.0), 5))
        QTest.mouseDClick(tl.viewport(), Qt.LeftButton, Qt.NoModifier, QPoint(x(5.0), 5))
        z = tl.zone_valide()
        self.assertIsNotNone(z)
        self.assertAlmostEqual(z[0], 3.0, delta=0.15)
        self.assertAlmostEqual(z[1], 5.0, delta=0.15)
        tl.zone = [3.0, 5.0]
        c = ed.morceau_de_partie(*ed.timeline.zone_valide())
        self.assertAlmostEqual(c["debut"], 3.0)
        self.assertAlmostEqual(fin_clip(c), 5.0)
        self.assertEqual(len(ed.projet.clips), 3)
        self.assertEqual(ed.timeline.selection(), [c["id"]])
        ed.projet.modifie = False
        f.attendre_taches()
        f.close()
        app.processEvents()


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
