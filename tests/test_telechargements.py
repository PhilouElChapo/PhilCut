"""File des téléchargements de l'IA locale : un à la fois, vitesse et temps restant, arrêt, choix du modèle à la fin."""
import os, sys, time, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import packs_ia
from app.config import Parametres
from app.telechargements import GestionTelechargements, FenetreTelechargements, FINI, ARRETE


def faux_installer(cle, progression=None, arret=lambda: False):
    for i in range(1, 11):
        if arret():
            raise InterruptedError()
        time.sleep(0.03)
        progression and progression(i / 10, "morceau")
    return True


class TestTelechargements(unittest.TestCase):
    def test_file(self):
        cat = {"voix_a": {"nom": "Voix A", "genre": "voix"}, "voix_b": {"nom": "Voix B", "genre": "voix"}}
        p = Parametres()
        with mock.patch.object(packs_ia, "modeles", return_value=cat), mock.patch.object(packs_ia, "a_telecharger", return_value=10_000_000), \
                mock.patch.object(packs_ia, "installer", side_effect=faux_installer):
            g = GestionTelechargements(p)
            f = FenetreTelechargements(None, g)
            g.ajouter(["voix_a", "voix_b", "voix_a"])         # le doublon est ignoré
            self.assertEqual(len(g.travaux), 2)
            self.assertEqual(g.travaux[1]["etat"], "attente")
            g.arreter("voix_b")                                 # arrêté avant de commencer
            fin = time.time() + 10
            while g.actifs() and time.time() < fin:
                app.processEvents()
                time.sleep(0.02)
            self.assertEqual([t["etat"] for t in g.travaux], [FINI, ARRETE])
            self.assertGreater(g.travaux[0]["vitesse"], 0)
            self.assertEqual(p["ia_locale_modeles"]["voix"], "voix_a")
            f.actualiser()
            self.assertEqual(f.table.item(0, 3).text(), "Terminé")
            g.nettoyer()
            self.assertEqual(g.travaux, [])


if __name__ == "__main__":
    unittest.main()
