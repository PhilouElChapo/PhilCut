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


class TestRetoursDuSoir(unittest.TestCase):
    def test_musique_en_ligne(self):
        """Artiste et durée complétés ; « libre » jamais coché d'office ; licence d'archive.org signalée comme annoncée."""
        from app import musique_en_ligne as ML, videos_en_ligne as VL
        import json
        ancien = VL._lancer_ytdlp
        VL._lancer_ytdlp = lambda args, *a, **k: [json.dumps({"id": "abc", "artists": ["Orchestre"], "duration": 245, "album": "Concert",
                                                              "release_year": 1937})]
        try:
            r = ML.completer([{"id": "abc", "page": "https://music.youtube.com/watch?v=abc", "titre": "Valse", "artiste": "", "duree": 0}])
        finally:
            VL._lancer_ytdlp = ancien
        self.assertEqual((r[0]["artiste"], r[0]["duree"], r[0]["album"], r[0]["annee"]), ("Orchestre", 245.0, "Concert", "1937"))
        from app.dialogues_musique_ia import DialogueMusiqueEnLigne
        pa = {}
        d = DialogueMusiqueEnLigne(None, pa)
        d.resultats = [{"titre": "x", "source": "archive", "licence": "http://creativecommons.org/publicdomain/zero/1.0/", "licence_libre": True,
                        "libre": False, "page": "p"}]
        d.liste.addItem("x")
        d.libre.setChecked(True)
        d._choisi(0)
        self.assertFalse(d.libre.isChecked())
        self.assertFalse(d.avert.isHidden())
        d.source.setCurrentIndex(d.source.findData("ytmusic"))
        self.assertTrue(d.b_installer.isHidden() != d.b_maj.isHidden())
        d.done(0)

    def test_plan_ia_garde_ses_reglages(self):
        from app import fabrique as FAB, creations
        from app.dialogues_video import DialogueFabrique
        from app.projet import Projet
        d = DialogueFabrique(None, Projet(), {})
        d.sujet.setPlainText("un avion au roulage")
        d.duree_ia.setValue(6)
        rec = FAB.recette_plan(d, "a small plane taxiing", "cloud", "omni-360p")
        self.assertEqual((rec["outil"], rec["voie"], rec["modele"], rec["duree"], rec["consigne"]),
                         ("fabrique", "cloud", "omni-360p", 6, "a small plane taxiing"))
        dossier = FAB.dossier_plans()
        self.assertTrue(dossier.endswith(os.path.join("PhilCut", "Plans IA")))
        f = os.path.join(dossier, "essai_recette.mp4")
        open(f, "wb").write(b"x")
        creations.ecrire(f, rec)
        self.assertEqual(creations.lire(f)["consigne"], "a small plane taxiing")
        os.remove(f)


class TestEcran(unittest.TestCase):
    def test_fenetre_qui_grandit_reste_dans_l_ecran(self):
        """Une fenêtre qui grandit après coup (aperçu du résultat…) ne dépasse jamais l'écran : son contenu défile."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QApplication
        from app import ecran
        ecran.installer(QApplication.instance())
        d = QDialog()
        v = QVBoxLayout(d)
        v.addWidget(QLabel("petit"))
        d.show()
        app.processEvents()
        haut = ecran.place(d).height()
        grand = QLabel("grand")
        grand.setMinimumHeight(int(haut * 1.5))
        v.addWidget(grand)
        for _i in range(10):
            app.processEvents()
        self.assertLessEqual(d.height(), int(haut * 0.95))
        self.assertTrue(getattr(d, "_defilant", False))
        d.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
