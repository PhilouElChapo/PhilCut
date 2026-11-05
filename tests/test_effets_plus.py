"""0.4.1 : effets manquants — tremblement, LUT, cadre photo, zoom lent, avant / après, transitions choc / rotation /
filé, image figée, bruitages, autocollants ; fondu au noir / flash blanc de nouveau exportables."""
import os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import bruitages as B, effets as E, export, goodies as GO, moteur
from app.projet import Projet, fin_clip


class TestEffetsPlus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.v = commun.video_test(cls.d, "a.mp4", duree=4)
        cls.v2 = commun.video_test(cls.d, "b.mp4", duree=4, taille="320x180")
        cls.lut = os.path.join(cls.d, "chaud.cube")
        with open(cls.lut, "w") as f:
            f.write("LUT_3D_SIZE 2\n")
            for b in (0, 1):
                for g in (0, 1):
                    for r in (0, 1):
                        f.write(f"{min(1, r + 0.2)} {g * 0.9} {b * 0.5}\n")

    def _projet(self):
        p = Projet()
        m = p.ajouter_media(self.v, moteur.sonder(self.v))
        m2 = p.ajouter_media(self.v2, moteur.sonder(self.v2))
        return p, m, m2

    def test_effets_rendus(self):
        cas = [("tremblement", {"amorti": True}), ("lut", {"fichier": self.lut, "force": 0.7}), ("cadre_photo", {}), ("zoom_lent", {}),
               ("avant_apres", {"mode": "rideau"}), ("avant_apres", {"mode": "moitie"})]
        for eid, pa in cas:
            p, m, m2 = self._projet()
            c = p.ajouter_clip(m["id"])
            if eid == "avant_apres":
                pa = dict(pa, media=m2["id"])
            c["effets"] = [{"id": eid, "params": pa}]
            export.image_rendue(p, 1.5, os.path.join(self.d, f"{eid}.png"), largeur=320)

    def test_transitions(self):
        for tr in ("t_choc", "t_rotation", "t_file", "t_fondu_noir", "t_fondu_blanc"):
            p, m, m2 = self._projet()
            p.ajouter_clip(m["id"])
            c2 = p.ajouter_clip(m2["id"])
            c2["transition"] = {"id": tr, "params": {}}
            export.image_rendue(p, c2["debut"] + 0.1, os.path.join(self.d, f"{tr}.png"), largeur=320)
        ex = export.Exportateur(p, os.path.join(self.d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        self.assertNotIn("max(0", " ".join(ex.filtres))           # « st » de fade : un nombre, pas une expression

    def test_bruitages(self):
        p, m, _m2 = self._projet()
        p.ajouter_clip(m["id"])
        p.ajouter_clip(m["id"], "audio", 0.0)                       # piste Musique occupée
        c = B.poser(p, "whoosh", 1.0)
        self.assertEqual(c["piste"], "audio2")                      # une piste de son libre est ajoutée
        self.assertAlmostEqual(fin_clip(c) - c["debut"], 0.8, delta=0.05)
        c2 = B.poser(p, "impact", 3.0)
        self.assertEqual(c2["piste"], "audio2")
        self.assertTrue(all(os.path.getsize(B.chemin(k)) > 1000 for k in B.SONS))

    def test_autocollants(self):
        for genre, o in (("polaroid", {"texte": "Calvi"}), ("post_it", {"texte": "QNH 1013"}), ("fleche", {"angle": 45})):
            g = {"genre": genre, "debut": 0, "fin": 3, "options": o}
            for t in (0.05, 1.0):
                self.assertFalse(GO.image(g, t, 160).isNull())
        self.assertIn("polaroid", GO.PACKS["autocollants"]["goodies"])


class TestImageFigee(unittest.TestCase):
    def test_figer(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import dialogues_effets_plus as DP
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=4)
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.ajouter_a_la_timeline(m["id"])
        t = ed.projet.ajouter_titre("Plus tard", 3.0, 4.0)
        ed.timeline.aller_a(2.0)
        with mock.patch.object(DP.DialogueFiger, "exec", lambda self: (self.legende.setText("Calvi"), self.duree.setValue(2.5), 1)[2]):
            ed.figer_image()
        video = sorted(ed.projet.clips_piste("video"), key=lambda c: c["debut"])
        self.assertEqual([round(c["debut"], 2) for c in video], [0.0, 2.0, 4.5])
        self.assertEqual(ed.projet.media(video[1]["media"])["genre"], "image")
        self.assertEqual([e["id"] for e in video[1]["effets"]], ["zoom_lent", "cadre_photo"])
        self.assertEqual(video[1]["transition"]["id"], "t_fondu_blanc")
        self.assertAlmostEqual(t["debut"], 5.5)                      # la suite est décalée
        self.assertTrue(any(x["texte"] == "Calvi" for x in ed.projet.titres))
        self.assertTrue(any("Déclic" in c["nom"] or "clic" in c["nom"] for c in ed.projet.clips if c["piste"].startswith("audio")))
        export.image_rendue(ed.projet, 3.0, os.path.join(d, "fig.png"), largeur=320)
        ed.projet.modifie = False
        f.attendre_taches()
        f.close()


if __name__ == "__main__":
    unittest.main()
