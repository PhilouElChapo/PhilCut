"""1.3.3 : au-delà de deux personnes, leurs fiches tiennent sur une seule image de référence (l'hôtesse n'est plus perdue)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import sequence_ia as Q


class TestCasting(unittest.TestCase):
    def test_casting_et_image_clef(self):
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        rp = []
        for k, c in enumerate(("#aa0000", "#00aa00", "#0000aa", "#aaaa00")):
            f = os.path.join(d, f"planche_{k}.png")
            q = QImage(300, 200, QImage.Format_RGB32)
            q.fill(QColor(c))
            q.save(f)
            rp.append((f"Character {chr(65 + k)}", [f]))
        sortie = Q.casting(rp, os.path.join(d, "c.png"), hauteur=200)
        q = QImage(sortie)
        self.assertEqual(q.width(), 4 * 300 + 5 * 12)
        self.assertEqual(QColor(q.pixel(12 + 3 * 312 + 150, 100)).name(), "#aaaa00")      # la 4e fiche est là
        # l'image clef reçoit la planche commune au lieu de 3 fiches sur 4
        recu = {}
        from app import ia
        anc = (Q.references_du_plan, Q.images_du_plan, Q.image_connue_avant, Q.consigne, Q.dossier, ia.generer_image_refs)
        try:
            Q.references_du_plan = lambda seq, pl: rp
            Q.images_du_plan = lambda seq, pl: []
            Q.image_connue_avant = lambda seq, i: ""
            Q.consigne = lambda seq, pl, params: "Action."
            Q.dossier = lambda seq: d
            ia.generer_image_refs = lambda params, c, refs: recu.update(c=c, refs=refs) or b"png"
            Q.image_arrivee({"plans": [{}]}, 0, {})
        finally:
            Q.references_du_plan, Q.images_du_plan, Q.image_connue_avant, Q.consigne, Q.dossier, ia.generer_image_refs = anc
        self.assertEqual(len(recu["refs"]), 1)
        self.assertTrue(recu["refs"][0].endswith("plan01_casting.png"))
        self.assertIn("cast sheet", recu["c"])
        self.assertIn("NOT characters", recu["c"])


if __name__ == "__main__":
    unittest.main()
