"""L'interface hors ecran : fenetre, projet, import, timeline, dialogues, preferences, enregistrement, reouverture."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import theme
theme.appliquer("sombre")
from app.config import dossier_donnees, Parametres
app.setStyleSheet(theme.feuille(dossier_donnees(), "sombre"))


class TestInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.v = commun.video_test(cls.d)
        p = Parametres()
        p["bienvenue_vue"] = True
        p["maj_auto"] = False
        p["synchro"] = False
        p.enregistrer()
        from app.fenetre import Fenetre
        cls.f = Fenetre()
        cls.f.show()
        app.processEvents()

    def test_01_nouveau_projet_et_import(self):
        from app import taches
        ed = self.f.nouveau_projet("16:9")
        self.assertIsNotNone(ed)

        class T:
            arret = False

            @staticmethod
            def avancer(fr, t=""):
                pass
        r = taches.importer_media(T, self.v, self.f.params, avec_proxy=False)
        m = ed.projet.ajouter_media(self.v, r["fiche"])
        m.update(vignettes=r["vignettes"], onde=r["onde"])
        ed.biblio.remplir(ed.projet)
        ed.ajouter_a_la_timeline(m["id"])
        self.assertEqual(len(ed.projet.clips), 1)
        ed.timeline.aller_a(2.0)
        ed.timeline.couper_au_curseur()
        self.assertEqual(len(ed.projet.clips), 2)
        ed.timeline.selectionner(ed.projet.clips[1]["id"])
        ed.timeline.supprimer_selection(True)
        self.assertEqual(len(ed.projet.clips), 1)
        ed.annuler()
        self.assertEqual(len(ed.projet.clips), 2)
        ed.projet.ajouter_titre("T", 0, 2)
        ed.projet.ajouter_goodie("horloge", 0, 3)
        ed.rafraichir()
        app.processEvents()
        self.assertFalse(self.f.grab().isNull())

    def test_02_dialogues(self):
        from app.dialogues_video import DialogueEffets, DialogueTitre, DialogueGoodie, DialogueExport, DialogueFabrique, DialogueFiche
        from app.preferences import DialoguePreferences
        ed = self.f.editeur_courant()
        for dlg in (DialogueEffets(self.f, ed.projet.clips[0], self.f.params, ed.projet.medias), DialogueTitre(self.f), DialogueGoodie(self.f),
                    DialogueExport(self.f, ed.projet, self.f.params), DialogueFabrique(self.f, ed.projet, self.f.params),
                    DialogueFiche(self.f, ed.projet.medias[0]), DialoguePreferences(self.f, self.f.params)):
            dlg.show()
            app.processEvents()
            self.assertFalse(dlg.grab().isNull())
            dlg.close()

    def test_03_barre_personnalisee(self):
        self.f.params["barre"] = ["importer", "|", "couper", "exporter"]
        self.f.reconstruire_barres()
        ed = self.f.editeur_courant()
        self.assertEqual(ed.flux.count(), 4)
        self.f.params["barre"] = None

    def test_04_enregistrer_rouvrir(self):
        ed = self.f.editeur_courant()
        chemin = os.path.join(self.d, "p.philcut")
        ed.projet.enregistrer(chemin)
        n = self.f.onglets.count()
        self.f.onglets.removeTab(self.f.onglets.indexOf(ed))
        ed2 = self.f.ouvrir(chemin)
        self.assertIsNotNone(ed2)
        self.assertEqual(len(ed2.projet.clips), 2)
        self.assertIn(chemin, self.f.params["recents"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
