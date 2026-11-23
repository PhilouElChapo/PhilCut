"""1.1.19 : Centre d'activité : boutons d'une tâche en cours entiers et visibles (« Arrêter » était coupé à droite) ; fiche
d'une personne réelle : la découpe de la photo se voit à la place de « Pas de fiche »."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test1127(unittest.TestCase):
    def test_boutons_visibles(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QPushButton
        from app import activite as A
        c = A.Centre()
        c.lignes.append({"id": 1, "titre": "L'assistant prépare les fiches et les images", "texte": "Fiche de « Femme brune souriante »",
                         "fraction": 0.3, "etat": A.EN_COURS, "debut": 0, "fin": None, "erreur": None,
                         "pendant": ("Afficher la fenêtre", lambda: None), "tache": None})
        from PySide6.QtCore import QObject, Signal

        class Telech(QObject):
            change = Signal()

            def __init__(self):
                super().__init__()
                self.travaux = []
                self.actifs = lambda: []
                self.nettoyer = lambda: None
                self.params = {"colonnes_activite": [450, 230, 160, 450, 170, 380]}     # largeurs tirées à la souris
        c.telechargements = Telech()
        f = A.FenetreActivite(None, c)
        f.resize(1060, 400)
        f.show()
        app.processEvents()
        f.remplir()
        app.processEvents()
        w = f.table.cellWidget(0, 5)
        boutons = w.findChildren(QPushButton)
        self.assertEqual(sorted(b.text() for b in boutons), ["Afficher la fenêtre", "Arrêter"])
        vp = f.table.viewport()
        for b in boutons:
            self.assertGreaterEqual(b.width(), b.fontMetrics().horizontalAdvance(b.text()))     # texte entier
            droite = b.mapTo(vp, QPoint(b.width(), 0)).x()
            self.assertLessEqual(droite, vp.width() + 1, b.text())                              # pas coupé à droite
        self.assertFalse(f.table.horizontalScrollBar().isVisible())
        f.close()


    def test_decoupe_montree(self):
        import tempfile
        from PySide6.QtGui import QImage, QColor
        from app.fenetre import Fenetre
        from app import sequence_ia as Q
        from app.dialogues_assistant_creation import DialogueAssistant
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("9:16")
        d = tempfile.mkdtemp()
        im = QImage(120, 200, QImage.Format_RGB32)
        im.fill(QColor("#884422"))
        dec = os.path.join(d, "decoupe.png")
        im.save(dec)
        dl = DialogueAssistant(ed, None)
        dl.seq = Q.nouvelle("9:16")
        dl.seq["personnages"] = [{"nom": "Femme brune", "description": "manteau", "decoupe": dec},
                                 {"nom": "Inconnu", "description": "x"}]
        dl.seq["plans"] = [{"action": "pose", "duree": 3, "personnages": []}]
        dl._remplir_images()
        app.processEvents()
        from PySide6.QtWidgets import QLabel
        textes = " ".join(l.text() for l in dl.findChildren(QLabel))
        self.assertIn("Découpe de votre photo", textes)
        self.assertEqual(textes.count("Pas de fiche"), 1)                 # seul « Inconnu » n'a rien
        dl.hide()
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
