"""0.9.51 : une tâche relancée avant la fin de la précédente ne fait plus planter PhilCut (QThread détruit en plein
travail → arrêt de Qt, 0xc0000409) ; Dites-le en clair : un clic à la fois, seule la dernière demande compte."""
import gc, os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


class TestTaches(unittest.TestCase):
    def test_tache_abandonnee_survit(self):
        from app.taches import Tache, _EN_COURS
        fini = []

        def lente(t):
            time.sleep(0.6)
            return 42
        t = Tache(lente)
        t.fini.connect(lambda r, e: fini.append(r))
        t.start()
        t = None                                   # la fenêtre « oublie » la tâche, comme un second clic
        gc.collect()
        self.assertEqual(len(_EN_COURS), 1)
        t0 = time.time()
        while time.time() - t0 < 5 and (not fini or _EN_COURS):
            app.processEvents()
            time.sleep(0.02)
        self.assertEqual(fini, [42])
        self.assertEqual(len(_EN_COURS), 0)       # libérée après sa vraie fin


class TestDitesLe(unittest.TestCase):
    def test_un_clic_a_la_fois(self):
        from app import commande_ia as C
        from app.fenetre import Fenetre
        from app.dialogues_commande import DialogueCommande
        from PySide6.QtWidgets import QPushButton
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        ancien = C.comprendre

        def lent(phrase, projet, params, niv):
            time.sleep(0.4)
            return {"actions": C.regles(phrase), "source": "regles"}
        C.comprendre = lent
        try:
            d = DialogueCommande(ed)
            bs = d.rapides.findChildren(QPushButton)
            bs[0].click()
            self.assertFalse(d.rapides.isEnabled())                 # les autres attendent
            d.phrase.setText("un marqueur à chaque plan")
            d.comprendre()                                           # relance pendant que la première tourne
            gc.collect()
            t0 = time.time()
            while time.time() - t0 < 5 and not d.rapides.isEnabled():
                app.processEvents()
                time.sleep(0.02)
            for _ in range(30):
                app.processEvents()
                time.sleep(0.02)
            self.assertTrue(d.rapides.isEnabled())
            self.assertEqual([a["action"] for a in d.actions], ["marqueur"])   # seule la dernière demande compte
        finally:
            C.comprendre = ancien
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
