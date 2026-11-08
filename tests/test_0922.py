"""0.9.22 : sauvegarde automatique et récupération après plantage ; revenir à une version précédente."""
import os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test0922(unittest.TestCase):
    def setUp(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()

    def test_copie_puis_recuperation(self):
        from app import secours
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9", "Mon vol")
        ed.projet.marquer()
        ed.projet.ajouter_titre("Bonjour", 0.0, 2.0)
        self.assertEqual(f.sauvegarde_auto(), 1)
        self.assertEqual(f.sauvegarde_auto(), 0)                    # rien n'a bougé : pas de nouvelle copie
        k = ed.projet.d["secours_id"]
        self.assertEqual(len(secours.versions(k)), 1)
        # « plantage » : la fenêtre disparaît sans fermeture normale
        f.hide()
        f.deleteLater()
        app.processEvents()
        liste = [r for r in secours.a_recuperer() if r["cle"] == k]
        self.assertEqual(len(liste), 1)
        self.assertTrue(liste[0]["plus_recent"])
        f2 = Fenetre()
        f2._recuperation_test = True
        from app.fenetre import DialogueRecuperation
        d = DialogueRecuperation(f2, liste)
        d.recuperer()
        ed2 = d.ouverts[0]
        self.assertEqual(ed2.projet.nom, "Mon vol")
        self.assertEqual(ed2.projet.titres[0]["texte"], "Bonjour")
        self.assertTrue(ed2.projet.modifie)
        self.assertIsNone(ed2.projet.chemin)
        # enregistrer efface les copies
        import tempfile
        from PySide6.QtWidgets import QFileDialog
        cible = os.path.join(tempfile.mkdtemp(), "vol.philcut")
        QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (cible, ""))
        self.assertTrue(f2.enregistrer())
        self.assertEqual(secours.versions(k), [])
        ed2.projet.modifie = False
        f2.hide()
        f2.deleteLater()

    def test_revenir_a_une_version(self):
        from app import secours
        from app.fenetre import Fenetre, DialogueVersions
        f = Fenetre()
        ed = f.nouveau_projet("16:9", "Essai")
        ed.projet.marquer()
        ed.projet.ajouter_titre("Un", 0.0, 1.0)
        f.sauvegarde_auto()
        time.sleep(1.1)
        ed.projet.marquer()
        ed.projet.ajouter_titre("Deux", 1.0, 2.0)
        f.sauvegarde_auto()
        v = secours.versions(secours.cle(ed.projet))
        self.assertEqual(len(v), 2)
        d = DialogueVersions(f, ed, v)
        d.liste.setCurrentRow(1)                                   # la plus ancienne : un seul titre
        d.revenir()
        self.assertEqual([t["texte"] for t in ed.projet.titres], ["Un"])
        ed.projet.annuler()
        self.assertEqual(len(ed.projet.titres), 2)
        # fermeture normale : plus rien à récupérer
        ed.projet.modifie = False
        f.fermer_onglet(f.onglets.indexOf(ed))
        self.assertEqual(secours.versions(ed.projet.d["secours_id"]), [])
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
