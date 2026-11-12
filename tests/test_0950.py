"""0.9.50 : plusieurs chaînes YouTube reliées (choix de la chaîne à la publication), effets montrés sur un paysage
d'exemple quand la timeline est vide."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


class FauxCoffre:
    def __init__(self):
        self.d = {}

    def lire(self, k):
        return self.d.get(k)

    def enregistrer(self, k, v):
        self.d[k] = v

    def supprimer(self, k):
        self.d.pop(k, None)


class TestComptes(unittest.TestCase):
    def setUp(self):
        from app import coffre, oauth, publication as P
        self.P = P
        self.fc = FauxCoffre()
        self.anc = (coffre.lire, coffre.enregistrer, coffre.supprimer, oauth.autoriser, P._chaine)
        coffre.lire, coffre.enregistrer, coffre.supprimer = self.fc.lire, self.fc.enregistrer, self.fc.supprimer
        self.chaines = iter([("UC_b", "Vols du dimanche"), ("UC_a", "Atelier"), (None, None)])
        oauth.autoriser = lambda f, journal=None, arret=None: {"refresh_token": "r", "access_token": "a", "expire": 9e12}
        P._chaine = lambda jeton: next(self.chaines)

    def tearDown(self):
        from app import coffre, oauth
        coffre.lire, coffre.enregistrer, coffre.supprimer, oauth.autoriser, self.P._chaine = self.anc

    def test_plusieurs_chaines(self):
        P = self.P
        self.fc.d["publication:youtube"] = json.dumps({"refresh_token": "vieux"})       # ancien format repris
        self.assertEqual([n for _k, n in P.comptes_youtube()], ["Ma chaîne"])
        P.relier_youtube()
        P.relier_youtube()
        r = P.relier_youtube()
        self.assertFalse(r["nom_trouve"])
        P.renommer_compte(r["id"], "Pharmacie")
        self.assertEqual([n for _k, n in P.comptes_youtube()], ["Atelier", "Ma chaîne", "Pharmacie", "Vols du dimanche"])
        self.assertEqual(P.compte_actif(), r["id"])
        P.choisir_compte("UC_b")
        self.assertEqual(P._acces(), "a")
        P.delier_youtube("UC_b")
        self.assertNotIn("UC_b", dict(P.comptes_youtube()))
        self.assertIn(P.compte_actif(), dict(P.comptes_youtube()))

    def test_fenetre(self):
        P = self.P
        P.relier_youtube()
        P.relier_youtube()
        from app.fenetre import Fenetre
        from app.dialogues_publication import DialoguePublier
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        d = DialoguePublier(f, ed.projet, f.params)
        self.assertEqual(d.chaine.count(), 2)
        self.assertEqual(d.b_relier.text(), "Ajouter une chaîne…")
        self.assertEqual(d.chaine.currentData(), "UC_a")          # la dernière reliée est choisie
        ed.projet.modifie = False


class TestExempleEffets(unittest.TestCase):
    def test_paysage_et_vignettes(self):
        from app import catalogue_effets as C
        img = C._paysage(640, 360)
        self.assertEqual(img.shape, (360, 640, 3))
        self.assertGreater(float(img.std()), 20)
        p, c = C.projet_exemple()
        self.assertGreater(float(p.media(c["media"])["fiche"]["duree"]), 5)
        import time
        from app.fenetre import Fenetre
        f = Fenetre([])
        f.show()
        ed = f._editeur_ou_nouveau()
        cat = ed.catalogue
        cat.show()
        cat.actualiser()
        t0 = time.time()
        while time.time() - t0 < 120 and not cat.fabrique.images:
            app.processEvents()
            time.sleep(0.05)
        self.assertTrue(cat.fabrique.images)                      # les vignettes se font sur l'exemple
        self.assertEqual(cat.fabrique.cle, ("exemple",))
        cat.fabrique.arreter()
        ed.projet.modifie = False


class TestJournalPlantages(unittest.TestCase):
    def test_erreurs_notees(self):
        import sys, threading
        from app import journal as J
        anc = (sys.excepthook, threading.excepthook)
        try:
            J.surveiller_plantages("9.9.9")
            try:
                raise ValueError("essai de plantage")
            except ValueError:
                sys.excepthook(*sys.exc_info())
            t = threading.Thread(target=lambda: 1 / 0)
            t.start()
            t.join()
            J.fin_normale()
            txt = open(J.chemin_plantages(), encoding="utf-8").read()
            self.assertIn("PhilCut 9.9.9", txt)
            self.assertIn("ValueError: essai de plantage", txt)
            self.assertIn("ZeroDivisionError", txt)
            self.assertIn("fermeture normale", txt)
        finally:
            import faulthandler
            faulthandler.disable()
            sys.excepthook, threading.excepthook = anc

    def test_menu(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        textes = [a.text() for m in [a.menu() for a in f.menuBar().actions() if a.menu()] for a in m.actions()]
        self.assertIn("Journal des plantages et erreurs…", textes)
        for ed in f.editeurs():
            ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
