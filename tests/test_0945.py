"""0.9.45 : recherche YouTube des tampons vidéo : 30 résultats, puis 30 de plus en descendant (comme la page de YouTube)."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


class TestPlus(unittest.TestCase):
    def test_trente_de_plus(self):
        from app import videos_en_ligne as VL
        from app.dialogues_tampons import DialogueTampons
        demandes = []

        def faux(texte, n=30, genre="tout"):
            demandes.append(n)
            return [{"titre": f"v{i}", "id": f"v{i}", "page": f"https://y/{i}", "duree": 60, "short": False} for i in range(min(n, 75))]
        anc = (VL.chercher_youtube, VL.vignettes)
        VL.chercher_youtube, VL.vignettes = faux, (lambda res, d, arret=None: res)
        f = _F([])
        ed = f._editeur_ou_nouveau()
        d = DialogueTampons(ed, 2)
        d._ytdlp_pret = lambda: True
        d._verifier_orthographe = lambda t: None

        def attendre():
            for _i in range(200):
                app.processEvents()
                if not any(t.isRunning() for t in getattr(d, "taches", [])) and not d._plus_en_cours:
                    break
                import time
                time.sleep(0.02)
            app.processEvents()
        try:
            d.source.setCurrentIndex(d.source.findData("ytdlp"))
            d.question.setText("tonton flingur")
            d.chercher()
            attendre()
            self.assertEqual(d.resultats.count(), 30)
            self.assertFalse(d.b_plus.isHidden())
            d.plus_de_resultats()
            attendre()
            self.assertEqual(d.resultats.count(), 60)
            self.assertEqual(demandes[-1], 60)
            d.plus_de_resultats()
            attendre()
            self.assertEqual(d.resultats.count(), 75)
            d.plus_de_resultats()                                     # YouTube n'a rien de plus : on s'arrête
            attendre()
            self.assertTrue(d.b_plus.isHidden() or d._yt is None)
        finally:
            VL.chercher_youtube, VL.vignettes = anc
            ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
