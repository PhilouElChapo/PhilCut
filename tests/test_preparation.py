"""0.3.1 : préparation automatique de la lecture (tranches rouges puis vertes, lues à la place des rushes) et pellicule
de balayage (images extraites une fois, affichées pendant qu'on tire le curseur)."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import preparation as PR, taches
from app.projet import Projet


class T:
    arret = False

    @staticmethod
    def avancer(fr, t=""):
        pass


def projet(d):
    v = commun.video_test(d, "a.mp4", duree=6)
    p = Projet()
    m = p.ajouter_media(v, taches.importer_media(T, v, {}, avec_proxy=False)["fiche"])
    p.ajouter_clip(m["id"])
    p.ajouter_clip(m["id"])
    return p, m


class TestTranches(unittest.TestCase):
    def test_a_preparer_et_empreinte(self):
        d = tempfile.mkdtemp()
        p, m = projet(d)
        c0, c1 = p.clips
        self.assertFalse(PR.a_preparer(p, 0, 4))
        c0["effets"] = [{"id": "noir_blanc", "params": {}}]
        self.assertTrue(PR.a_preparer(p, 0, 4))
        self.assertFalse(PR.a_preparer(p, 8, 12))
        c0["effets"][0]["actif"] = False
        self.assertFalse(PR.a_preparer(p, 0, 4))
        c0["effets"][0]["actif"] = True
        e1 = PR.empreinte(p, 0, 4)
        e_loin = PR.empreinte(p, 8, 12)
        c1["effets"] = [{"id": "vintage", "params": {}}]          # changer le plan 2 ne touche pas la tranche 0-4
        self.assertEqual(PR.empreinte(p, 0, 4), e1)
        self.assertNotEqual(PR.empreinte(p, 8, 12), e_loin)
        p.ajouter_titre("Bonjour", 4.5, 5.5)
        self.assertTrue(PR.a_preparer(p, 4, 8))

    def test_pellicule(self):
        d = tempfile.mkdtemp()
        p, m = projet(d)
        pel = PR.Pellicules(largeur=160)
        self.assertIsNone(pel.image(m, 1.0))                    # première demande : extraction lancée
        fin = time.time() + 30
        while time.time() < fin and m["id"] not in pel.images:
            time.sleep(0.05)
        jpg = pel.image(m, 1.0)
        self.assertTrue(jpg and jpg[:2] == b"\xff\xd8")
        self.assertGreaterEqual(len(pel.images[m["id"]][1]), 40)      # 6 s à 8 images par seconde


class TestPreparationEditeur(unittest.TestCase):
    def test_tranches_preparees_puis_lues(self):
        os.environ["PHILCUT_PREPARATION"] = "1"
        try:
            from app.config import Parametres
            pp = Parametres()
            pp["bienvenue_vue"] = True
            pp["maj_auto"] = False
            pp["synchro"] = False
            pp["preparation_auto"] = True
            pp.enregistrer()
            from app.fenetre import Fenetre
            d = tempfile.mkdtemp()
            v = commun.video_test(d, "a.mp4", duree=6)
            f = Fenetre()
            f.show()
            ed = f.nouveau_projet("16:9")
            r = taches.importer_media(T, v, f.params, avec_proxy=False)
            m = ed.projet.ajouter_media(v, r["fiche"])
            ed.ajouter_a_la_timeline(m["id"])
            ed.ajouter_a_la_timeline(m["id"])
            ed.projet.marquer()
            ed.projet.clips[1]["effets"] = [{"id": "noir_blanc", "params": {}}]
            ed._modifie()
            fin = time.time() + 60
            while time.time() < fin and not (ed.preparation.etats() and all(x[2] == "pret" for x in ed.preparation.etats())):
                app.processEvents()
                time.sleep(0.05)
            et = ed.preparation.etats()
            self.assertTrue(et)
            self.assertTrue(all(x[2] == "pret" for x in et), et)
            self.assertEqual(et[0][0], 4.0)                     # seule la partie du plan 2 est à préparer (tranches de 4 s)
            # en lecture, la tranche prête remplace les rushes
            ed.timeline.aller_a(6.5)
            ed.apercu.lire()
            app.processEvents()
            c, _m = ed.apercu._source_video()
            self.assertEqual(c["id"], "__rendu__")
            ed.apercu.pause()
            ed.timeline.aller_a(1.0)
            c, _m = ed.apercu._source_video()
            self.assertNotEqual(c["id"], "__rendu__")
            # Annuler : les tranches de l'état précédent restent prêtes (empreinte) — pas de recalcul inutile
            ed.annuler()
            ed.preparation._recalculer()
            self.assertEqual(ed.preparation.etats(), [])
            ed.projet.modifie = False
            f.attendre_taches()
            f.close()
            app.processEvents()
        finally:
            os.environ["PHILCUT_PREPARATION"] = "0"


if __name__ == "__main__":
    unittest.main()
