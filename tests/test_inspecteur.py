"""0.3.0 : tout ce qui est posé se voit et se reprend. Effets désactivables (ignorés à l'export), étiquettes et
transition dessinées et cliquables sur la timeline, Inspecteur pour plan / texte / Goodie, Centre d'activité."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import effets as E, export
from app.projet import Projet


class TestEffetsActifs(unittest.TestCase):
    def test_actif(self):
        c = {"effets": [{"id": "glow", "params": {}}, {"id": "vintage", "params": {}, "actif": False}], "transition": {"id": "t_fondu_enchaine", "params": {"duree": 1}, "actif": False}}
        self.assertEqual([e["id"] for e in E.actifs(c)], ["glow"])
        self.assertIsNone(E.transition_active(c))
        c["transition"]["actif"] = True
        self.assertIsNotNone(E.transition_active(c))

    def test_export_ignore_desactive(self):
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=2)
        p = Projet()
        from app import taches

        class T:
            arret = False

            @staticmethod
            def avancer(fr, t=""):
                pass
        r = taches.importer_media(T, v, {}, avec_proxy=False)
        m = p.ajouter_media(v, r["fiche"])
        c = p.ajouter_clip(m["id"])
        c["effets"] = [{"id": "noir_blanc", "params": {}, "actif": False}]
        ex = export.Exportateur(p, os.path.join(d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        self.assertNotIn("hue=s=0", " ".join(ex.filtres))
        c["effets"][0]["actif"] = True
        ex = export.Exportateur(p, os.path.join(d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        self.assertIn("hue=s=0", " ".join(ex.filtres))


class TestInterface030(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.config import Parametres
        p = Parametres()
        p["bienvenue_vue"] = True
        p["maj_auto"] = False
        p["synchro"] = False
        p.enregistrer()
        from app.fenetre import Fenetre
        from app import taches
        cls.d = tempfile.mkdtemp()
        v = commun.video_test(cls.d, "a.mp4", duree=6)
        cls.f = Fenetre()
        cls.f.resize(1400, 860)
        cls.f.show()
        cls.ed = cls.f.nouveau_projet("16:9")

        class T:
            arret = False

            @staticmethod
            def avancer(fr, t=""):
                pass
        r = taches.importer_media(T, v, cls.f.params, avec_proxy=False)
        m = cls.ed.projet.ajouter_media(v, r["fiche"])
        m.update(vignettes=r["vignettes"], onde=r["onde"])
        cls.ed.ajouter_a_la_timeline(m["id"])
        cls.ed.ajouter_a_la_timeline(m["id"])
        c0, c1 = cls.ed.projet.clips
        c0["effets"] = [{"id": "glow", "params": {"rayon": 12.0, "intensite": 0.6}}, {"id": "vintage", "params": {}}]
        c1["transition"] = {"id": "t_fondu_enchaine", "params": {"duree": 1.0}}
        cls.ed.projet.ajouter_titre("Bienvenue", 1, 4)
        cls.ed.projet.ajouter_goodie("horloge", 0, 3)
        cls.ed.rafraichir()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ed.projet.modifie = False
        cls.f.attendre_taches()
        cls.f.close()
        app.processEvents()

    def test_etiquettes_et_transition_dessinees(self):
        tl = self.ed.timeline
        it0 = tl.items_clips[self.ed.projet.clips[0]["id"]]
        it1 = tl.items_clips[self.ed.projet.clips[1]["id"]]
        app.processEvents()
        self.f.grab()                                   # force le dessin
        self.assertEqual([g for _r, g, _i in it0.chips], ["effet", "effet"])
        self.assertIsNotNone(it1.rect_transition)
        # zones : le clic sur une étiquette ouvre l'Inspecteur dessus
        rc = it0.chips[1][0]
        self.assertEqual(it0._zone(rc.center()), ("effet", 1))
        self.assertEqual(it1._zone(it1.rect_transition.center()), "transition")

    def test_inspecteur_plan_effet_transition(self):
        ed = self.ed
        c0, c1 = ed.projet.clips
        ed._element_clique(c0["id"], "effet", 1)
        app.processEvents()
        self.assertEqual(ed.inspecteur._cible, ("clip", c0["id"]))
        self.assertEqual(ed.inspecteur._ouvrir, ("effet", 1))
        self.assertEqual(ed.volet.currentIndex(), 1)
        # désactiver puis supprimer depuis la timeline (menus) : reflété dans le modèle
        ed.timeline._basculer_effet(c0, 0)
        self.assertFalse(c0["effets"][0].get("actif", True))
        ed.timeline._supprimer_effet(c0, "effet", 0)
        self.assertEqual([e["id"] for e in c0["effets"]], ["vintage"])
        ed.timeline._duree_transition(c1, 1.5)
        self.assertEqual(c1["transition"]["params"]["duree"], 1.5)
        ed.timeline._changer_transition(c1, "t_cercle")
        self.assertEqual(c1["transition"]["id"], "t_cercle")
        self.assertEqual(c1["transition"]["params"]["duree"], 1.5)
        ed.timeline._supprimer_transition(c1)
        self.assertIsNone(c1["transition"])
        # chaque suppression est annulable
        n = len(ed.projet._pile)
        self.assertGreaterEqual(n, 4)

    def test_inspecteur_texte_goodie_et_coalescence(self):
        ed = self.ed
        t = ed.projet.titres[0]
        ed.inspecteur.montrer_texte(t)
        app.processEvents()
        avant = len(ed.projet._pile)
        ed.inspecteur._changer(lambda: t.__setitem__("taille", 1.2), reconstruire=False)
        ed.inspecteur._changer(lambda: t.__setitem__("taille", 1.3), reconstruire=False)
        self.assertEqual(len(ed.projet._pile), avant + 1)       # une rafale = un seul Annuler
        self.assertEqual(t["taille"], 1.3)
        g = ed.projet.goodies[0]
        ed.inspecteur.montrer_goodie(g)
        app.processEvents()
        self.assertEqual(ed.inspecteur._cible, ("goodie", g["id"]))
        ed.inspecteur.montrer_selection([])
        self.assertIsNone(ed.inspecteur._cible)

    def test_agrandir_volet(self):
        ed = self.ed
        ed.volet.setCurrentIndex(1)
        n = ed.volet.count()
        ed.agrandir_volet()
        app.processEvents()
        self.assertEqual(ed.volet.count(), n - 1)
        from PySide6.QtWidgets import QDialog
        dlg = next(x for x in self.f.findChildren(QDialog) if ed.inspecteur in x.findChildren(type(ed.inspecteur)))
        dlg.close()
        app.processEvents()
        self.assertEqual(ed.volet.count(), n)

    def test_centre_activite(self):
        from app.taches import Tache
        from app import activite
        c = activite.centre()
        t = Tache(lambda tache: (time.sleep(0.2), tache.avancer(0.5, "milieu"), time.sleep(0.2), True)[-1], "Essai")
        self.ed.taches.append(t)
        self.ed.encart.suivre(t, "Tâche d'essai")
        t.start()
        time.sleep(0.25)
        app.processEvents()
        txt, actif = c.resume()
        self.assertTrue(actif)
        self.assertIn("Tâche d'essai", txt)
        self.assertIn("Tâche d'essai", self.f.b_activite.text())
        t.wait(3000)
        app.processEvents()
        self.assertEqual(next(l for l in c.lignes if l["tache"] is t)["etat"], "fini")
        self.f.voir_activite()
        app.processEvents()
        self.assertGreaterEqual(self.f.fenetre_activite.table.rowCount(), 1)
        self.f.fenetre_activite.close()


if __name__ == "__main__":
    unittest.main()
