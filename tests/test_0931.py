"""0.9.31 : retours du 8 novembre au soir — durée des titres et Goodies à la souris, numéros de piste hors des artistes,
modèles après import, lecture avec effets, synchro sans renvois inutiles, tampons maison personnalisés, voix, styles."""
import json, os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur


def fenetre():
    from app.config import Parametres
    pa = Parametres()
    pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
    pa.enregistrer()
    from app.fenetre import Fenetre
    return Fenetre()


class Test0931(unittest.TestCase):
    def test_artistes_sans_numero(self):
        from app import musiques as M
        M._RACINES.add(os.path.normcase(os.path.abspath("/m")))
        self.assertEqual(M._depuis_nom("/m/17_Queen_-_Who_wants_to_live_forever.mp3")["artiste"], "Queen")
        r = M._depuis_nom("/m/Queen/Greatest Hits III/14 Another One Bites The Dust - Free (R&B).mp3")
        self.assertEqual((r["artiste"], r["titre"]), ("Queen", "Another One Bites The Dust - Free (R&B)"))
        self.assertEqual(M._depuis_nom("/m/50 Cent - In Da Club.mp3")["artiste"], "50 Cent")
        self.assertEqual(M._depuis_nom("/m/Nena/99 Luftballons.mp3")["titre"], "99 Luftballons")
        self.assertEqual(M.nettoyer_artiste("17 Queen"), "Queen")
        self.assertEqual(M.nettoyer_artiste("3 Doors Down"), "3 Doors Down")

    def test_duree_des_titres_a_la_souris(self):
        from PySide6.QtCore import QPointF
        from app.timeline import ItemCalque
        f = fenetre()
        ed = f.nouveau_projet("16:9")
        ed.projet.ajouter_titre("Bonjour", 1.0, 4.0)
        ed.rafraichir()
        app.processEvents()
        it = next(i for i in ed.timeline.scene().items() if isinstance(i, ItemCalque))
        r = it.rect()
        self.assertEqual(it._zone_bord(QPointF(r.width() - 2, 3)), "d")
        self.assertEqual(it._zone_bord(QPointF(2, 3)), "g")
        self.assertIsNone(it._zone_bord(QPointF(r.width() / 2, 3)))

        class Ev:                       # faux évènements souris
            def __init__(s, x):
                s._p = QPointF(x, 3)

            def pos(s):
                return s._p

            def button(s):
                from PySide6.QtCore import Qt
                return Qt.LeftButton

            def accept(s):
                pass
        it.mousePressEvent(Ev(r.width() - 2))
        x_scene_2s = ed.timeline.mapToScene(0, 0).x() * 0 + __import__("app.timeline", fromlist=["MARGE_G"]).MARGE_G + 2.0 * ed.timeline.pps
        it.mouseMoveEvent(Ev(x_scene_2s - it.scenePos().x()))
        it.mouseReleaseEvent(Ev(0))
        self.assertAlmostEqual(ed.projet.titres[0]["fin"], 2.0, delta=0.05)
        self.assertAlmostEqual(ed.projet.titres[0]["debut"], 1.0)
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_lecture_avec_effets(self):
        f = fenetre()
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=2)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0, 0.0, 2.0)
        self.assertFalse(ed._a_des_effets(0, 15))                          # rien : lecture directe
        ed.projet.ajouter_titre("T", 0.0, 1.0)
        self.assertFalse(ed._a_des_effets(0, 15))                          # les titres sont dessinés en direct
        c["effets"] = [{"id": "noir_blanc", "params": {}}]
        self.assertTrue(ed._a_des_effets(0, 15))
        appels = []
        ed.lire_rendu = lambda *a: appels.append("rendu")
        ed.lecture_auto()
        self.assertEqual(appels, ["rendu"])
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_synchro_sans_renvoi(self):
        from app.reglages import ecrire_si_change
        p = os.path.join(tempfile.mkdtemp(), "session.json")
        import datetime
        maintenant = datetime.datetime.now().isoformat(timespec="minutes")
        self.assertTrue(ecrire_si_change(p, {"poste": {"maj": maintenant, "fichiers": [1]}}))
        self.assertFalse(ecrire_si_change(p, {"poste": {"maj": "2099-01-01T00:00", "fichiers": [1]}}))   # seule l'heure change
        self.assertTrue(ecrire_si_change(p, {"poste": {"maj": maintenant, "fichiers": [1, 2]}}))
        from app import miroir
        self.assertIn("réglages", miroir.expliquer("preferences.json"))

    def test_tampon_personnalise_et_voix(self):
        from app import tampons as T, paroles as PA
        a = T.image_maison("bravo", 2.0, 320, 180)
        b = T.image_maison("bravo", 2.0, 320, 180, "BIEN JOUÉ !", 3.5)
        self.assertNotEqual(bytes(a.constBits()), bytes(b.constBits()))
        self.assertIn("crooner", PA.VOIX)
        self.assertIn("baritone", PA.VOIX["crooner"][1])

    def test_fenetres(self):
        f = fenetre()
        ed = f.nouveau_projet("16:9")
        from app.dialogues_modeles import DialogueModeles
        dm = DialogueModeles(ed)
        self.assertFalse(dm.b_monter.isEnabled())
        c = commun.video_test(tempfile.mkdtemp(), "r.mp4", duree=2)
        ed.projet.ajouter_media(c, moteur.sonder(c))                     # import fini en tâche de fond
        dm._suivre_projet()
        self.assertTrue(dm.b_monter.isEnabled())
        dm.reject()
        from app.dialogues_creatif import DialogueAtelierIA
        dl = DialogueAtelierIA(ed, "musique")
        dl.show()
        self.assertTrue(dl.b_styles.isVisible())
        self.assertTrue(hasattr(dl, "b_essai_voix"))
        dl.suivi.demarrer("Essai")
        self.assertIn("en cours depuis", dl.suivi.texte.text())
        dl.suivi.finir()
        dl.reject()
        f._maj_bouton_synchro(0, 2)
        self.assertIn("2", f._b_synchro.text())
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
