"""0.9.4 : timeline plus simple — clic = tête de lecture, double-clic sur la règle = début puis fin de la partie jaune,
[ ] à côté de la tête, bords jaunes à tirer, molette = zoom (avec rappel animé)."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtTest import QTest


class Test094(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["synchro_secrets"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import moteur
        cls.f = Fenetre()
        cls.f.resize(1400, 860)
        cls.f.show()
        cls.ed = cls.f.nouveau_projet("16:9")
        v = commun.video_test(tempfile.mkdtemp(), "film.mp4", duree=12)
        m = cls.ed.projet.ajouter_media(v, moteur.sonder(v))
        cls.ed.ajouter_a_la_timeline(m["id"])
        for _i in range(10):
            app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ed.projet.modifie = False
        cls.f.hide()
        cls.f.deleteLater()

    def setUp(self):
        self.tl = self.ed.timeline
        self.tl.ajuster()
        self.tl.effacer_zone()
        for _i in range(5):
            app.processEvents()
        self.vp = self.tl.viewport()

    def x(self, t):
        from app.timeline import MARGE_G
        return int(self.tl.mapFromScene(MARGE_G + t * self.tl.pps, 0).x())

    def test_clic_deplace_sans_selectionner(self):
        QTest.mousePress(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(2.0), 12))
        ev = QMouseEvent(QEvent.MouseMove, QPointF(self.x(6.0), 12), self.vp.mapToGlobal(QPointF(self.x(6.0), 12)), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        app.sendEvent(self.vp, ev)
        QTest.mouseRelease(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(6.0), 12))
        self.assertAlmostEqual(self.tl.position, 6.0, delta=0.1)
        self.assertEqual(self.tl.zone, [None, None])                     # glisser déplace seulement la tête rouge

    def test_double_clic_debut_puis_fin(self):
        QTest.mouseDClick(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(3.0), 12))
        self.assertAlmostEqual(self.tl.zone[0], 3.0, delta=0.1)
        self.assertIsNone(self.tl.zone[1])
        QTest.mouseClick(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(5.0), 12))
        self.assertIsNone(self.tl.zone[1])                               # un clic entre les deux ne défait rien
        QTest.mouseDClick(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(7.0), 12))
        a, b = self.tl.zone_valide()
        self.assertAlmostEqual(a, 3.0, delta=0.1)
        self.assertAlmostEqual(b, 7.0, delta=0.1)
        QTest.mouseDClick(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(9.0), 12))
        self.assertAlmostEqual(self.tl.zone[0], 9.0, delta=0.1)          # un 3e double-clic recommence
        self.assertIsNone(self.tl.zone[1])

    def test_boutons_crochets_et_bord(self):
        self.tl.aller_a(2.0)
        app.processEvents()
        self.vp.repaint()
        rc_debut, rc_fin = self.tl._boutons_tete
        p = self.tl.mapFromScene(rc_debut.center())
        QTest.mouseClick(self.vp, Qt.LeftButton, Qt.NoModifier, p)
        self.tl.aller_a(5.0)
        self.vp.repaint()
        p = self.tl.mapFromScene(self.tl._boutons_tete[1].center())
        QTest.mouseClick(self.vp, Qt.LeftButton, Qt.NoModifier, p)
        self.assertEqual([round(z, 1) for z in self.tl.zone], [2.0, 5.0])
        # tirer le bord de fin sur la règle
        QTest.mousePress(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(5.0), 12))
        ev = QMouseEvent(QEvent.MouseMove, QPointF(self.x(8.0), 12), self.vp.mapToGlobal(QPointF(self.x(8.0), 12)), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        app.sendEvent(self.vp, ev)
        QTest.mouseRelease(self.vp, Qt.LeftButton, Qt.NoModifier, QPoint(self.x(8.0), 12))
        self.assertAlmostEqual(self.tl.zone[1], 8.0, delta=0.15)

    def test_molette_zoom_et_rappel(self):
        pps = self.tl.pps
        pos = QPointF(self.x(5.0), 60)
        we = QWheelEvent(pos, self.vp.mapToGlobal(pos), QPoint(0, 0), QPoint(0, 120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        app.sendEvent(self.vp, we)
        self.assertGreater(self.tl.pps, pps)
        from PySide6.QtCore import QAbstractAnimation
        self.assertEqual(self.tl._anim_zoom.state(), QAbstractAnimation.Running)   # le rappel « Zoom » s'anime
        barre = self.tl.horizontalScrollBar().value()
        we = QWheelEvent(pos, self.vp.mapToGlobal(pos), QPoint(0, 0), QPoint(0, -120), Qt.NoButton, Qt.ShiftModifier, Qt.NoScrollPhase, False)
        pps2 = self.tl.pps
        app.sendEvent(self.vp, we)
        self.assertEqual(self.tl.pps, pps2)                              # Maj + molette : défiler, pas zoomer
        self.assertNotEqual(self.tl.horizontalScrollBar().value(), barre)
        # clic sur le rappel : tout voir
        self.tl.zoomer(4)
        c = self.tl._rect_zoom().center().toPoint()
        QTest.mouseClick(self.vp, Qt.LeftButton, Qt.NoModifier, c)
        self.assertLess(self.tl.pps, pps2 * 4)


if __name__ == "__main__":
    unittest.main()
