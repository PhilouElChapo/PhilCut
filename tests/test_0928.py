"""0.9.28 : étalonnage simple — roues de couleur, curseurs, auto, accorder sur un autre plan, copie ; même chaîne à l'export."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur


class Test0928(unittest.TestCase):
    def test_calculs(self):
        from app import etalonnage as ET
        import numpy as np
        self.assertEqual(ET.filtre(ET.neutre()), "")
        for x, y in ((1, 0), (0, 1), (-0.5, -0.5)):
            o = ET.roue_vers_rvb(x, y)
            self.assertAlmostEqual(sum(o), 0, places=6)
            x2, y2 = ET.rvb_vers_roue(o)
            self.assertAlmostEqual(x, x2, places=5)
            self.assertAlmostEqual(y, y2, places=5)
        p = dict(ET.neutre(), exposition=0.3, temperature=0.5, moyens_x=1.0)
        ch = ET.filtre(p)
        self.assertIn("eq=", ch)
        self.assertIn("colortemperature", ch)
        self.assertIn("rm=0.25", ch)
        # image bleutée et terne : « auto » pousse les tons moyens vers le jaune (opposé du bleu) et ajoute du contraste
        img = np.zeros((90, 160, 3), np.uint8)
        img[..., 0], img[..., 1], img[..., 2] = 90, 100, 150
        img[:, :80] += 20
        a = ET.auto(img)
        o = ET.roue_vers_rvb(a["moyens_x"], a["moyens_y"])
        self.assertLess(o[2], 0)
        self.assertGreater(a["contraste"], 0)
        # accorder : une image plus sombre prend l'exposition de la référence
        ref = np.full((90, 160, 3), 180, np.uint8)
        sombre = np.full((90, 160, 3), 60, np.uint8)
        self.assertGreater(ET.accorder(sombre, ref)["exposition"], 0.3)

    def test_fenetre_et_export(self):
        from app import etalonnage as ET, effets as E
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        a = commun.video_test(d, "a.mp4", duree=2)
        b = commun.video_test(d, "b.mp4", duree=2)
        ma = ed.projet.ajouter_media(a, moteur.sonder(a))
        mb = ed.projet.ajouter_media(b, moteur.sonder(b))
        ca = ed.projet.ajouter_clip(ma["id"], "video", 0.0, 0.0, 2.0)
        cb = ed.projet.ajouter_clip(mb["id"], "video", 2.0, 0.0, 2.0)
        ca2 = ed.projet.ajouter_clip(ma["id"], "video", 4.0, 0.0, 1.0)
        from app.dialogues_etalonnage import DialogueEtalonnage
        dl = DialogueEtalonnage(ed, ca)
        self.assertFalse(dl.source.isNull())
        dl.curseurs["exposition"].setValue(40)
        dl.roues["moyens"].valeur(0.0, 1.0, True)
        dl._rendre()
        self.assertFalse(dl.vue.apres.isNull())
        self.assertNotEqual(dl.vue.apres.pixelColor(100, 60), dl.source.pixelColor(100, 60))        # l'aperçu change
        dl.auto()
        dl.accorder()
        dl.curseurs["saturation"].setValue(-100)                                               # noir et blanc
        dl.copier()                                                                              # même rush : ca2
        self.assertEqual(ET.reglages_de(ca2)["saturation"], -1.0)
        self.assertEqual(ET.reglages_de(cb)["saturation"], 0.0)
        dl.valider()
        e = next(x for x in ca["effets"] if x["id"] == "etalonnage")
        ch = E.filtre(e, {})
        self.assertIn("saturation=0.0000", ch)
        # export d'une image : le plan est bien en noir et blanc
        sortie = os.path.join(d, "x.mp4")
        from app import export
        export.exporter(ed.projet, sortie, "youtube", f.params)
        if os.path.exists(sortie):
            img = os.path.join(d, "x.png")
            moteur.lancer(["-y", "-ss", "1.0", "-i", sortie, "-frames:v", "1", img])
            from PySide6.QtGui import QImage
            q = QImage(img)
            c = q.pixelColor(q.width() // 3, q.height() // 2)
            self.assertLess(max(abs(c.red() - c.green()), abs(c.green() - c.blue())), 12)
        ed.projet.annuler()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
