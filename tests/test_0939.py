"""0.9.39 : la fenêtre de mise à jour se réduit ; le téléchargement se suit dans la barre du bas (« Afficher »)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestMaj(unittest.TestCase):
    def test_reduire_et_suivre_en_bas(self):
        from PySide6.QtCore import Qt
        from app.dialogues_maj import DialogueMaj
        from app.editeur import Encart
        from app.taches import Tache
        from PySide6.QtWidgets import QWidget
        w = QWidget()
        d = DialogueMaj(w, "v9", {})
        self.assertTrue(d.windowFlags() & Qt.WindowMinimizeButtonHint)
        d.show()
        d.b_reduire.click()
        self.assertFalse(d.isVisible())
        # pas d'estimation fantaisiste au départ
        d._fait, d._total = 1_000_000, 288_000_000
        d._progression(0.003, "")
        self.assertNotIn("min", d.detail.text())
        e = Encart(w)
        t = Tache(lambda t: None, "x")
        vus = []
        e.suivre(t, "Téléchargement", pendant=("Afficher", lambda: vus.append(1)))
        self.assertTrue(e.bouton.isVisibleTo(w) or not e.bouton.isHidden())
        e.bouton.click()
        self.assertEqual(vus, [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
