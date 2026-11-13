"""0.9.64 : fermer une fenêtre de création pendant le calcul ne perd rien. La fenêtre se range, le calcul continue,
la barre du bas le suit (« Afficher la fenêtre »), puis « Voir le résultat » la rouvre ; le Centre d'activité garde ces
deux boutons. Fabrique musique non bloquante et unique ; même règle pour liaison, voix, séparation, séquence."""
import os, sys, threading, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


def attendre(cond, s=10):
    t0 = time.time()
    while time.time() - t0 < s and not cond():
        app.processEvents()
        time.sleep(0.02)


class TestCalculEnFond(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()

    def tearDown(self):
        self.ed.projet.modifie = False

    def _tache_lente(self, ev):
        from app.taches import Tache
        return Tache(lambda t: (ev.wait(20), "fini")[1], "essai")

    def test_fabrique_musique(self):
        from app import activite
        d = self.ed.fabrique_musique()
        self.assertTrue(d.isVisible())
        self.assertFalse(d.isModal())
        ev = threading.Event()
        d.tache = self._tache_lente(ev)
        from app.widgets import suivre_en_fond
        suivre_en_fond(d, d.tache, "Fabrique musique : création du morceau")
        d.tache.start()
        d.reject()                                              # « Fermer » pendant la création
        app.processEvents()
        self.assertFalse(d.isVisible())
        self.assertTrue(d.tache.isRunning())                    # rien ne s'arrête
        self.assertEqual(self.ed.encart.bouton.text(), "Afficher la fenêtre")
        ligne = next(l for l in activite.centre().lignes if l["tache"] is d.tache)
        self.assertEqual(ligne["pendant"][0], "Afficher la fenêtre")
        self.assertIs(self.ed.fabrique_musique(), d)            # le menu rouvre la même fenêtre
        self.assertTrue(d.isVisible())
        d.hide()
        ev.set()
        attendre(lambda: not d.tache.isRunning() and "✓" in self.ed.encart.lbl.text())
        self.assertEqual(self.ed.encart.bouton.text(), "Voir le résultat")
        self.ed.encart.bouton.click()
        self.assertTrue(d.isVisible())
        self.assertEqual(ligne["ouvrir"][0], "Voir le résultat")
        d.reject()
        self.assertFalse(d.isVisible())

    def test_centre_activite_boutons(self):
        from PySide6.QtWidgets import QPushButton
        from app import activite
        from app.widgets import suivre_en_fond
        from PySide6.QtWidgets import QDialog
        dlg = QDialog(self.ed)
        ev = threading.Event()
        t = self._tache_lente(ev)
        suivre_en_fond(dlg, t, "Création d'essai")
        t.start()
        fa = activite.FenetreActivite(None, activite.centre())
        textes = [b.text() for b in fa.findChildren(QPushButton)]
        self.assertIn("Afficher la fenêtre", textes)
        ev.set()
        attendre(lambda: not t.isRunning())
        app.processEvents()
        fa.remplir()
        b = [b for b in fa.findChildren(QPushButton) if b.text() == "Voir le résultat" and b.isVisibleTo(fa)]
        self.assertTrue(b)
        b[0].click()
        self.assertTrue(dlg.isVisible())

    def test_autres_fenetres(self):
        from app.dialogues_liaison import DialogueLiaison
        from app.dialogues_voix_suite import DialogueVoixSuite
        from app.dialogues_separation import DialogueSeparation
        ev = threading.Event()
        for classe in (DialogueLiaison, DialogueVoixSuite, DialogueSeparation):
            d = classe.__new__(classe)
            from PySide6.QtWidgets import QDialog
            QDialog.__init__(d, self.ed)
            d.ed, d.lecteur, d.apercu = self.ed, None, type("A", (), {"arreter": lambda s: None})()
            d.tache = self._tache_lente(ev)
            d.tache.start()
            d.show()
            d.close()
            app.processEvents()
            self.assertFalse(d.isVisible(), classe.__name__)
            self.assertTrue(d.tache.isRunning(), classe.__name__)
        ev.set()


if __name__ == "__main__":
    unittest.main()
