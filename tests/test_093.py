"""0.9.3 : vignettes et images fixes composées (zones de couleur, kits), vérification des modèles d'IA."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

import cv2
import numpy as np


def attendre(tache, delai=60):
    t0 = time.time()
    while tache is not None and tache.isRunning() and time.time() - t0 < delai:
        app.processEvents()
        time.sleep(0.03)
    for _i in range(10):
        app.processEvents()


def composee(dl, delai=60):
    """Attend la fin de la composition en cours (délai de saisie puis calcul en tâche de fond)."""
    t0 = time.time()
    while time.time() - t0 < delai:
        app.processEvents()
        if not dl._delai.isActive() and not (dl.tache is not None and dl.tache.isRunning()):
            for _i in range(5):
                app.processEvents()
            if not dl._delai.isActive():
                return
        time.sleep(0.03)


def scene():
    """Fond bleu-gris, un objet rouge net au centre droit."""
    img = np.full((720, 1280, 3), (120, 100, 80), np.uint8)
    cv2.circle(img, (760, 360), 150, (40, 40, 220), -1)
    return img


class Test093(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()

    def zones(self):
        return [{"couleur": "rouge", "points": [[0.44, 0.22], [0.75, 0.22], [0.75, 0.78], [0.44, 0.78]]},
                {"couleur": "bleu", "points": [[0.03, 0.05], [0.40, 0.05], [0.40, 0.40], [0.03, 0.40]]},
                {"couleur": "jaune", "points": [[0.80, 0.10], [0.86, 0.10], [0.86, 0.18], [0.80, 0.18]]},
                {"couleur": "vert", "points": [[0.05, 0.82], [0.95, 0.82], [0.95, 0.96], [0.05, 0.96]]}]

    def test_detourage_suit_l_objet(self):
        from app import vignette as V
        img = scene()
        m = V.masque_sujet(img, self.zones()[0], 1280, 720)
        dans = m[360, 760] > 127
        hors = m[200, 600] > 127                     # coin de la zone tracée, hors de l'objet
        self.assertTrue(dans)
        self.assertFalse(hors)

    def test_composition_tous_kits(self):
        from app import vignette as V
        r = V.nouvelle_recette()
        r.update(zones=self.zones(), titre="Le moteur qui change tout", accent_mots="change", elements="Pistons ✓\nSoupapes ✗\nArbre à cames")
        for kit in V.KITS:
            r["kit"] = kit
            q, infos = V.composer(r, scene(), None, 1280, 720)
            self.assertEqual((q.width(), q.height()), (1280, 720))
            self.assertGreater(infos["taille_titre"], 40, kit)
            self.assertEqual(infos["avertissements"], [], kit)
        # le titre est dessiné dans la zone bleue : des pixels clairs y apparaissent
        a = V._depuis_qimage(q)
        self.assertGreater(int(a[36:288, 38:512].max()), 200)

    def test_elements_lisibilite_variantes(self):
        from app import vignette as V
        self.assertEqual(V._elements("Pistons ✓, soupapes ✗\narbre à cames"), [("Pistons", "ok"), ("soupapes", "non"), ("arbre à cames", "")])
        r = V.nouvelle_recette()
        r.update(titre="Un titre beaucoup trop long pour une vignette lisible", zones=[])
        av = V.lisibilite(r, 0, 1280, 720)
        self.assertTrue(any("bleu" in a for a in av))
        self.assertTrue(any("mots" in a for a in av))
        vs = V.variantes(dict(r, kit="punchy"))
        self.assertEqual(len(vs), 3)
        self.assertEqual(vs[0]["kit"], "punchy")
        self.assertNotEqual(vs[1]["kit"], "punchy")
        self.assertEqual(len({v["graine"] for v in vs}), 3)

    def test_proposition_ia(self):
        from app import ia, vignette as V
        vrai = ia.demander
        vus = {}
        ia.demander = lambda params, consignes, texte, images=None, json_attendu=False, max_jetons=0: (
            vus.update(texte=texte, images=images) or {"titre": "Trois pièces changent tout", "accent_mots": "tout",
                                                      "elements": ["Pistons ✓", "Soupapes ✓"], "kit": "documentaire", "fleche": "cercle", "pourquoi": "ok"})
        try:
            r = V.nouvelle_recette()
            r["zones"] = self.zones()
            r["prompt"] = "moteur : pistons, soupapes"
            out = V.proposer_ia(r, b"png", {}, "cloud")
        finally:
            ia.demander = vrai
        self.assertIn("pistons, soupapes", vus["texte"])
        self.assertEqual(vus["images"], [b"png"])
        self.assertEqual(out["kit"], "documentaire")
        self.assertEqual(out["elements"], "Pistons ✓\nSoupapes ✓")
        self.assertEqual(out["fleche"], "cercle")

    def test_avant_apres(self):
        from app import vignette as V
        r = V.nouvelle_recette()
        r["avant_apres"] = True
        img2 = np.full((720, 1280, 3), (20, 200, 20), np.uint8)
        q, _i = V.composer(r, scene(), img2, 1280, 720)
        a = V._depuis_qimage(q)
        self.assertGreater(int(a[360, 1200, 1]), 150)                     # à droite : l'image « après » (verte)
        self.assertLess(int(a[360, 60, 1]), 150)

    def test_fenetre_pose_et_rouvre(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["synchro_secrets"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import moteur, vignette as V
        from app.dialogues_vignette import DialogueVignette
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        v = commun.video_test(self.d, "film.mp4", duree=4)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.ajouter_a_la_timeline(m["id"])
        ed.aller_a(1.0)
        dl = DialogueVignette(ed)
        dl.show()
        composee(dl)
        self.assertIsNotNone(dl.resultat)
        dl.recette["zones"] = self.zones()
        dl.titre.setText("Essai de vignette")
        composee(dl)
        self.assertGreater(dl.infos.get("taille_titre", 0), 20)
        self.assertIn("Zone verte sans éléments", dl.lisib.text())         # la zone verte attend ses éléments
        dl.elements.setPlainText("Pistons ✓")
        composee(dl)
        self.assertIn("✓", dl.lisib.text())
        dl.miniature()
        self.assertTrue(os.path.exists(ed.projet.d["vignette_image"]))
        dl.poser()
        c = next(c for c in ed.projet.clips if c.get("vignette"))
        self.assertNotEqual(c["piste"], "video")
        self.assertEqual(len(ed.projet.clips_piste("video")), 1)
        dl.reject()
        rec = ed.projet.d["vignettes"][0]
        self.assertEqual(rec["titre"], "Essai de vignette")
        # rouverte depuis le plan : même recette, et « Poser » remplace l'ancien plan
        d2 = DialogueVignette(ed, rec)
        d2.clip_a_remplacer = c["id"]
        self.assertEqual(d2.titre.text(), "Essai de vignette")
        composee(d2)
        d2.poser()
        self.assertEqual(len([x for x in ed.projet.clips if x.get("vignette")]), 1)
        d2.reject()
        # export : la miniature composée devient la vignette du fichier
        from app.export import poser_vignette
        sortie = os.path.join(self.d, "export.mp4")
        import shutil
        shutil.copy(v, sortie)
        jpg = poser_vignette(sortie, 0.0, ed.projet.d["vignette_image"])
        self.assertTrue(os.path.getsize(jpg) > 1000)
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
