"""0.3.4 : plan déplacé d'une piste à l'autre, effets copiés / collés, effet sur une partie du plan (bornes tirables),
images clefs (incrustation, texte, Goodie) à l'aperçu et à l'export."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import cles as K, export, moteur
from app.projet import Projet, decouper_effets_partiels, fin_clip


def _projet(d):
    v = commun.video_test(d, "a.mp4", duree=6)
    p = Projet()
    m = p.ajouter_media(v, moteur.sonder(v))
    return p, m


class TestModele(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()

    def test_effet_partiel_decoupe_et_coupe(self):
        p, m = _projet(self.d)
        c = p.ajouter_clip(m["id"])
        c["effets"] = [{"id": "glow", "params": {}}, {"id": "noir_blanc", "params": {}, "de": 2.0, "a": 4.0}]
        q = decouper_effets_partiels(p)
        self.assertEqual([[e["id"] for e in x["effets"]] for x in q.clips], [["glow"], ["glow", "noir_blanc"], ["glow"]])
        self.assertEqual(len(p.clips), 1)                                    # le projet lui-même n'est pas coupé
        ex = export.Exportateur(p, os.path.join(self.d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        self.assertEqual(" ".join(ex.filtres).count("hue=s=0"), 1)           # noir et blanc sur un seul morceau
        p.couper(c["id"], 3.0)                                               # coupe au milieu de la partie
        a, b = p.clips
        self.assertEqual((a["effets"][1]["de"], a["effets"][1]["a"]), (2.0, 3.0))
        self.assertEqual((b["effets"][1]["de"], b["effets"][1]["a"]), (0.0, 1.0))
        q = export.extrait(p, 4.5, 6.0)                                      # extrait : la partie sort du plan
        self.assertEqual([e["id"] for e in q.clips[0]["effets"]], ["glow"])

    def test_images_clefs(self):
        p, m = _projet(self.d)
        t = p.ajouter_titre("Envol", 1.0, 5.0)
        self.assertFalse(K.regler(t, 2.0, x=0.3))                             # sans image clef : réglage fixe
        self.assertEqual(t["x"], 0.3)
        K.poser(t, 0.0)
        K.poser(t, 4.0, x=0.9, taille=2.0)
        self.assertAlmostEqual(K.valeurs_a(t, 3.0)["x"], 0.6, places=3)      # milieu
        self.assertAlmostEqual(K.valeurs_a(t, 3.0)["taille"], 1.5, places=3)
        self.assertTrue(K.regler(t, 3.0, y=0.2))                              # animé : image clef à la tête de lecture
        self.assertEqual(len(t["cles"]), 3)
        self.assertEqual(K.voisine(t, 2.0, 1), 4.0)
        # ASS : un événement par intervalle, avec \move
        from app import titres as T
        a = T.ass([t], 1920, 1080)
        self.assertEqual(a.count("\\move("), 2)
        self.assertTrue(K.retirer(t, 2.0))
        # incrustation animée : commandes sendcmd et image rendue
        p.ajouter_clip(m["id"])
        c2 = p.ajouter_clip(m["id"], "video2", 0.0)
        c2["incrust"] = {"echelle": 0.2, "x": 0.0, "y": 0.0, "opacite": 1.0}
        K.poser(c2, 0.0)
        K.poser(c2, 5.0, echelle=0.6, x=1.0, y=1.0, opacite=0.5)
        lignes = K.commandes_echelle_opacite(c2, 1920, 1080, "scale@a", "colorchannelmixer@b", 25)
        self.assertIn("scale@a w 384", lignes[0])
        export.image_rendue(p, 4.0, os.path.join(self.d, "k.png"), largeur=640)
        # extrait : les clefs suivent
        q = export.extrait(p, 2.5, 6.0)
        c2q = q.clips_piste("video2")[0]
        self.assertAlmostEqual(K.valeurs(c2q, 0.0)["echelle"], 0.4, places=2)


class TestInterface034(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        cls.d = tempfile.mkdtemp()
        v = commun.video_test(cls.d, "a.mp4", duree=4)
        cls.f = Fenetre()
        cls.f.resize(1400, 860)
        cls.f.show()
        cls.ed = cls.f.nouveau_projet("16:9")
        m = cls.ed.projet.ajouter_media(v, moteur.sonder(v))
        cls.ed.ajouter_a_la_timeline(m["id"])
        cls.ed.ajouter_a_la_timeline(m["id"])
        cls.ed.timeline._ajouter_piste("video")
        cls.ed.rafraichir()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ed.projet.modifie = False
        cls.ed.catalogue.fermer()
        cls.f.attendre_taches()
        cls.f.close()
        app.processEvents()

    def test_changer_de_piste(self):
        tl = self.ed.timeline
        c = self.ed.projet.clips_piste("video")[1]
        y2 = tl._pistes()["video2"][0] + 10
        self.assertEqual(tl.piste_compatible(c, y2), "video2")
        self.assertIsNone(tl.piste_compatible(c, tl._pistes()["voix"][0] + 5))        # pas vers une piste de son
        self.ed.projet.marquer()
        tl.changer_piste(c, "video2")
        self.assertEqual(c["piste"], "video2")
        self.assertIn("incrust", c)
        self.ed.projet.annuler()
        self.assertEqual(len(self.ed.projet.clips_piste("video")), 2)

    def test_copier_coller_effets(self):
        tl = self.ed.timeline
        a, b = self.ed.projet.clips_piste("video")
        a["effets"] = [{"id": "vintage", "params": {}}]
        tl.copier_effets(a)
        tl.coller_effets(b)
        self.assertEqual([e["id"] for e in b["effets"]], ["vintage"])
        self.assertIsNot(b["effets"][0], a["effets"][0])
        self.ed.projet.annuler()
        self.assertFalse(self.ed.projet.clips_piste("video")[1].get("effets"))

    def test_partie_et_inspecteur(self):
        tl = self.ed.timeline
        a = self.ed.projet.clips_piste("video")[0]
        a["effets"] = [{"id": "noir_blanc", "params": {}}]
        tl._partie_effet(a, 0, "milieu")
        self.assertIn("de", self.ed.projet.clips_piste("video")[0]["effets"][0])
        tl.reconstruire()
        app.processEvents()
        self.ed.inspecteur.montrer_element(a["id"], "effet", 0)
        a = self.ed.projet.clips_piste("video")[0]
        tl._partie_effet(a, 0, None)
        self.assertNotIn("de", self.ed.projet.clips_piste("video")[0]["effets"][0])

    def test_cles_dans_l_interface(self):
        t = self.ed.projet.ajouter_titre("Bonjour", 0, 4)
        self.ed.timeline.aller_a(0.0)
        self.ed.inspecteur.montrer_texte(t)
        K.poser(t, 0.0)
        self.ed.timeline.aller_a(3.0)
        self.ed.apercu.calque_deplace.emit(t["id"], 0.8, 0.3)     # glisser dans l'image à 3 s : seconde image clef
        self.assertEqual(len(t["cles"]), 2)
        self.assertAlmostEqual(K.valeurs_a(t, 3.0)["x"], 0.8, places=3)
        self.ed.timeline.reconstruire()
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
