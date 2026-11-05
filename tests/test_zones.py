"""0.3.3 : zones tracées dans l'image (flou, mosaïque, cache…) fixes ou suivies par analyse de l'image ; poignées de
redimensionnement dans l'aperçu ; catalogue des effets à vignettes animées et glisser-déposer sur la timeline."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import export, moteur, zones as Z
from app.projet import Projet


def _video_motif(d):
    """Un motif texturé (mandelbrot 70x70) qui traverse des barres de couleur fixes, de gauche à droite."""
    chemin = os.path.join(d, "motif.mp4")
    moteur.lancer(["-f", "lavfi", "-i", "smptehdbars=size=640x360:rate=25:duration=3", "-f", "lavfi", "-i", "mandelbrot=size=70x70:rate=25",
                   "-filter_complex", "[1]trim=duration=3[m];[0][m]overlay=x='40+t*120':y=140:shortest=1", "-c:v", "libx264",
                   "-pix_fmt", "yuv420p", chemin])
    return chemin


def _projet(chemin):
    p = Projet()
    m = p.ajouter_media(chemin, moteur.sonder(chemin))
    p.ajouter_clip(m["id"])
    return p


class TestZones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.video = _video_motif(cls.d)

    def test_suivi_par_motif(self):
        pts = Z.suivre_modele(self.video, 0, 2.5, (30 / 640, 130 / 360, 90 / 640, 90 / 360))
        self.assertGreater(len(pts), 20)
        for t, cx, cy, _l, _h in pts[::6]:
            self.assertAlmostEqual(cx * 640, 40 + t * 120 + 35, delta=12, msg=t)
            self.assertAlmostEqual(cy * 360, 175, delta=10, msg=t)

    def test_suivre_zone_et_export(self):
        p = _projet(self.video)
        L, H = p.taille
        z = Z.nouvelle(0, 3, 75 / 640, 175 / 360, 90 / 640, 90 / 360, "cache")
        z["couleur"] = "#ff0000"
        p.goodies.append(z)
        Z.suivre_zone(p, z)
        pos = z["suivi"]["positions"]
        self.assertAlmostEqual(Z.rect_a(z, 2.0)[0] * 640, 40 + 240 + 35, delta=14)
        # l'export cache le motif en rouge, là où il est
        png = os.path.join(self.d, "z.png")
        export.image_rendue(p, 2.0, png, largeur=640)
        from PIL import Image
        im = Image.open(png).convert("RGB")
        px = im.getpixel((int(315 * im.width / 640), int(175 * im.height / 360)))
        self.assertGreater(px[0], 200)
        self.assertLess(px[1] + px[2], 120)
        # figer : la zone reste où elle est à cet instant
        Z.figer(z, 2.0)
        self.assertIsNone(z.get("suivi"))
        self.assertAlmostEqual(z["x"] * 640, 315, delta=14)
        self.assertTrue(pos)

    def test_traitements_et_ovale(self):
        p = _projet(self.video)
        for i, (k, _lib) in enumerate(Z.TRAITEMENTS):
            z = Z.nouvelle(0, 3, 0.1 + 0.15 * i, 0.8, 0.12, 0.2, k)
            z["forme"] = "ovale" if i % 2 else "rect"
            p.goodies.append(z)
        ex = export.Exportateur(p, os.path.join(self.d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        f = " ".join(ex.filtres)
        for motif in ("boxblur", "flags=neighbor", "lutrgb", "hue=s=0", "geq=", "eq=brightness"):
            self.assertIn(motif, f)
        export.image_rendue(p, 1.0, os.path.join(self.d, "t.png"), largeur=640)       # le moteur accepte tout le graphe

    def test_deplacer_redimensionner_suivie(self):
        z = Z.nouvelle(0, 2, 0.5, 0.5, 0.2, 0.2)
        z["suivi"] = {"media": "m", "positions": [(0.0, 0.3, 0.5, 0.2, 0.2), (2.0, 0.7, 0.5, 0.2, 0.2)]}
        Z.deplacer(z, 0.6, 0.6, 1.0)                     # au milieu, la zone était en (0.5, 0.5) : tout est décalé
        self.assertAlmostEqual(z["suivi"]["positions"][0][1], 0.4, places=3)
        self.assertAlmostEqual(z["suivi"]["positions"][1][2], 0.6, places=3)
        Z.redimensionner(z, 0.6, 0.6, 0.4, 0.1, 1.0)
        self.assertAlmostEqual(z["suivi"]["positions"][0][3], 0.4, places=3)
        self.assertAlmostEqual(z["suivi"]["positions"][0][4], 0.1, places=3)

    def test_extrait_decale_les_trajectoires(self):
        p = _projet(self.video)
        z = Z.nouvelle(0.5, 3, 0.5, 0.5, 0.2, 0.2)
        z["suivi"] = {"media": "m", "positions": [(1.0, 0.3, 0.5, 0.2, 0.2), (2.0, 0.7, 0.5, 0.2, 0.2)]}
        p.goodies.append(z)
        q = export.extrait(p, 1.0, 3.0)
        self.assertEqual([x[0] for x in q.goodies[0]["suivi"]["positions"]], [0.0, 1.0])
        p.partie(0.0, 0.5, garder=False)
        self.assertEqual([x[0] for x in p.goodies[0]["suivi"]["positions"]], [0.5, 1.5])


class TestCatalogueEtPoignees(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.config import Parametres
        p = Parametres()
        p["bienvenue_vue"] = True
        p["maj_auto"] = False
        p["synchro"] = False
        p.enregistrer()
        from app.fenetre import Fenetre
        cls.d = tempfile.mkdtemp()
        cls.video = _video_motif(cls.d)
        cls.f = Fenetre()
        cls.f.resize(1400, 860)
        cls.f.show()
        cls.ed = cls.f.nouveau_projet("16:9")
        m = cls.ed.projet.ajouter_media(cls.video, moteur.sonder(cls.video))
        cls.ed.ajouter_a_la_timeline(m["id"])
        cls.ed.ajouter_a_la_timeline(m["id"])
        cls.ed.rafraichir()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ed.projet.modifie = False
        cls.ed.catalogue.fermer()
        cls.f.attendre_taches()
        cls.f.close()
        app.processEvents()

    def test_vignette_et_projet_essai(self):
        from app import catalogue_effets as C
        c = self.ed.projet.clips[1]
        p = C.projet_essai(self.ed.projet, c, "t_fondu_enchaine")
        self.assertEqual(len(p.clips), 2)
        self.assertEqual(p.clips[1]["transition"]["id"], "t_fondu_enchaine")
        self.assertEqual(len(C.projet_essai(self.ed.projet, c, "glow").clips), 1)
        imgs = C.vignette(self.ed.projet, c, "noir_blanc")
        self.assertGreaterEqual(len(imgs), 8)
        self.assertTrue(imgs[0].startswith(b"\xff\xd8"))

    def test_glisser_deposer_cibles(self):
        from PySide6.QtCore import QPointF
        from app.timeline import MARGE_G
        tl = self.ed.timeline
        c0, c1 = self.ed.projet.clips_piste("video")
        y = tl._pistes()["video"][0] + 10
        c, _r = tl.cible_effet(QPointF(MARGE_G + 1.0 * tl.pps, y), "glow")
        self.assertEqual(c["id"], c0["id"])
        c, _r = tl.cible_effet(QPointF(MARGE_G + (c1["debut"] + 0.1) * tl.pps, y), "t_glisse")
        self.assertEqual(c["id"], c1["id"])                         # raccord : le plan qui arrive
        c, raison = tl.cible_effet(QPointF(MARGE_G + 1.0 * tl.pps, y), "t_glisse")
        self.assertIsNone(c)                                         # premier plan : pas de transition
        self.assertIn("premier", raison)
        c, _r = tl.cible_effet(QPointF(MARGE_G + 1.0 * tl.pps, tl._pistes()["voix"][0] + 5), "glow")
        self.assertIsNone(c)
        self.ed.poser_effet(c0["id"], "glow")
        self.assertEqual(c0["effets"][-1]["id"], "glow")
        self.ed.poser_effet(c1["id"], "t_glisse")
        self.assertEqual(c1["transition"]["id"], "t_glisse")
        self.ed.projet.annuler()
        self.ed.projet.annuler()
        self.assertFalse(any(e["id"] == "glow" for e in self.ed.projet.clips_piste("video")[0].get("effets") or []))

    def test_tracer_zone_et_poignees(self):
        ed = self.ed
        ed.timeline.aller_a(0.5)
        ed.tracer_zone()
        self.assertTrue(ed.apercu._mode_trace)
        ed.apercu.tracer_zone(False)
        ed._zone_tracee(0.3, 0.4, 0.2, 0.25)
        z = [g for g in ed.projet.goodies if g.get("genre") == "zone"][-1]
        self.assertAlmostEqual(z["debut"], 0.5, places=2)
        self.assertEqual(ed.inspecteur._cible, ("zone", z["id"]))
        ed.apercu.aller_a(1.0, forcer=True)
        app.processEvents()
        from app.apercu import Poignee
        pg = [it for it in ed.apercu.poignees if isinstance(it, Poignee) and it.ident == z["id"]]
        self.assertTrue(pg and pg[0].zone)
        ed.apercu.calque_cadre.emit(z["id"], 0.5, 0.5, 0.4, 0.3)          # coin tiré dans l'image
        self.assertAlmostEqual(z["l"], 0.4, places=3)
        ed.apercu.calque_deplace.emit(z["id"], 0.6, 0.55)
        self.assertAlmostEqual(z["x"], 0.6, places=3)
        ed.apercu.calque_taille.emit(z["id"], 0.5)                         # molette
        self.assertAlmostEqual(z["l"], 0.2, places=3)
        ed._zone_tracee(-1, -1, 0, 0)                                      # tracé abandonné : rien de plus
        self.assertEqual(len([g for g in ed.projet.goodies if g.get("genre") == "zone"]), 1)
        # texte : un coin tiré l'agrandit (même facteur que la molette)
        t = ed.projet.ajouter_titre("Bonjour", 0, 3)
        ed.apercu.calque_taille.emit(t["id"], 1.5)
        self.assertAlmostEqual(t["taille"], 1.5, places=2)


if __name__ == "__main__":
    unittest.main()
