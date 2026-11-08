"""0.9.25 : modèles de montage tout faits (vos rushes montés à la façon du modèle) ; exports en série."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur


def attendre(t, delai=120):
    t0 = time.time()
    while t is not None and t.isRunning() and time.time() - t0 < delai:
        app.processEvents()
        time.sleep(0.05)
    for _i in range(20):
        app.processEvents()


class Test0925(unittest.TestCase):
    def _fenetre(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        return Fenetre()

    def test_modele_de_montage(self):
        from app import modeles_montage as MM
        from app.projet import fin_clip
        self.assertGreaterEqual(len(MM.MODELES), 10)
        f = self._fenetre()
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        for i in range(3):
            v = commun.video_test(d, f"r{i}.mp4", duree=6)
            ed.projet.ajouter_media(v, moteur.sonder(v))
        from app.dialogues_modeles import DialogueModeles
        dl = DialogueModeles(ed)
        k = [dl.liste.item(i).data(0x0100) for i in range(dl.liste.count())].index("short_15")
        dl.liste.setCurrentRow(k)
        self.assertEqual(dl.duree.value(), 15)
        self.assertEqual(dl.format.currentData(), "9:16")
        dl.monter()
        attendre(dl.tache or getattr(dl, "_t", None))
        attendre(None)
        p = ed.projet
        self.assertEqual(p.d["format"], "9:16")
        plans = p.clips_piste("video")
        self.assertGreaterEqual(len(plans), 4, dl.etat.text())
        self.assertTrue(all(fin_clip(c) - c["debut"] <= 1.8 + 0.05 for c in plans[:-1]))         # coupes rapides du modèle
        self.assertEqual(p.d["recette"]["modele"], "short_15")
        self.assertTrue(any(c.get("transition") for c in plans))
        self.assertEqual(p.titres[0]["animation"], "cinetique")
        p.annuler()
        self.assertEqual(p.clips_piste("video"), [])                                              # Ctrl+Z revient
        p.modifie = False
        f.hide()
        f.deleteLater()

    def test_exports_en_serie(self):
        f = self._fenetre()
        ed = f.nouveau_projet("16:9")
        from app.dialogues_video import DialogueExport
        dl = DialogueExport(f, ed.projet, f.params)
        dl.dest.setCurrentIndex(dl.dest.findData("youtube"))
        self.assertFalse(dl.autres["youtube"].isEnabled())
        for k in ("insta", "insta_carre", "ecran_led"):
            dl.autres[k].setChecked(True)
        self.assertEqual(sorted(dl.autres_formats()), ["ecran_led", "insta", "insta_carre"])
        self.assertEqual(sorted(f.params["export_autres"]), ["ecran_led", "insta", "insta_carre"])
        dl.reject()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
