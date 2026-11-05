"""Pistes multiples (0.3.0) : vidéo 2 et 3 incrustées par-dessus la base (plein cadre ou image dans l'image), musiques
supplémentaires ; ajout et retrait de pistes ; disposition de la timeline ; export avec overlay et audio mélangé."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import export, taches
from app.projet import Projet


class T:
    arret = False

    @staticmethod
    def avancer(fr, t=""):
        pass


def projet_deux_pistes(d):
    v = commun.video_test(d, "a.mp4", duree=4)
    w = commun.video_test(d, "b.mp4", duree=3, taille="320x240")
    p = Projet()
    ma = p.ajouter_media(v, taches.importer_media(T, v, {}, avec_proxy=False)["fiche"])
    mb = p.ajouter_media(w, taches.importer_media(T, w, {}, avec_proxy=False)["fiche"])
    p.ajouter_clip(ma["id"])
    p.ajouter_piste("video")
    c = p.ajouter_clip(mb["id"], "video2", 1.0)
    c["incrust"] = {"echelle": 0.4, "x": 0.9, "y": 0.1, "opacite": 0.8}
    return p, c


class TestPistes(unittest.TestCase):
    def test_modele(self):
        p = Projet()
        self.assertEqual(p.pistes_video(), ["video"])
        self.assertEqual(p.ajouter_piste("video"), "video2")
        self.assertEqual(p.ajouter_piste("audio"), "audio2")
        self.assertEqual(p.toutes_pistes(), ["video", "video2", "audio", "audio2", "voix"])
        self.assertTrue(p.retirer_piste("audio2"))
        self.assertFalse(p.retirer_piste("video"))          # la base reste
        self.assertEqual(p.toutes_pistes(), ["video", "video2", "audio", "voix"])

    def test_export_incrustation(self):
        d = tempfile.mkdtemp()
        p, c = projet_deux_pistes(d)
        ex = export.Exportateur(p, os.path.join(d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        f = "\n".join(ex.filtres)
        self.assertIn("overlay=(W-w)*0.900:(H-h)*0.100", f)
        self.assertIn("scale=trunc(iw*0.400/2)*2", f)
        self.assertIn("colorchannelmixer=aa=0.800", f)
        self.assertIn("between(t,1.000,4.000)", f)
        # le son du plan incrusté est mélangé (il a une piste audio)
        self.assertIn("voixmix", f)
        # et l'export tourne pour de vrai
        ex = export.Exportateur(p, os.path.join(d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        out = ex.lancer()
        self.assertGreater(os.path.getsize(out), 10000)
        # image fidèle : le rendu à 2 s contient l'incrustation (pas d'erreur)
        png = export.image_rendue(p, 2.0, os.path.join(d, "i.png"), {}, 320)
        self.assertGreater(os.path.getsize(png), 1000)

    def test_muet_et_masque_par_piste(self):
        d = tempfile.mkdtemp()
        p, c = projet_deux_pistes(d)
        p.basculer_piste("video2", "masquee")
        ex = export.Exportateur(p, os.path.join(d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        self.assertNotIn("overlay=", "\n".join(ex.filtres))          # image masquée : pas d'incrustation
        p.basculer_piste("video2", "masquee")
        p.basculer_piste("video", "muette")
        ex = export.Exportateur(p, os.path.join(d, "o.mp4"), "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.commande()
        f = "\n".join(ex.filtres)
        self.assertIn("overlay=", f)
        self.assertIn("[sil", f)                                         # le son de la vidéo 1 est remplacé par du silence
        self.assertTrue(p.piste_muette("video"))
        from app.timeline import Timeline
        tl = Timeline(p)
        tl.resize(900, 400)
        tl.show()
        app.processEvents()
        tl.grab()
        self.assertIn("video", tl._boutons_piste)
        self.assertEqual([q for _r, q, _a, _x in tl._boutons_piste["video2"]], ["repliee", "muette", "solo", "masquee", "verrou"])

    def test_solo_verrou_nom_repli(self):
        d = tempfile.mkdtemp()
        p, c = projet_deux_pistes(d)
        p.basculer_piste("video2", "solo")
        self.assertTrue(p.piste_muette("video"))           # une autre piste en solo : la base se tait
        self.assertFalse(p.piste_muette("video2"))
        p.basculer_piste("video2", "solo")
        self.assertFalse(p.piste_muette("video"))
        p.renommer_piste("video2", "Avion")
        from app.timeline import Timeline
        tl = Timeline(p)
        self.assertEqual(tl.libelle_piste("video2"), "Avion")
        h_avant = tl._pistes()["video"][1]
        p.basculer_piste("video", "repliee")
        self.assertLess(tl._pistes()["video"][1], h_avant)
        # verrou : ni coupe ni suppression sur la piste
        p.basculer_piste("video", "verrou")
        base = p.clips_piste("video")[0]
        tl.reconstruire()
        tl.aller_a(2.0)
        tl.couper_au_curseur()
        self.assertEqual(len(p.clips_piste("video")), 1)
        tl.selectionner(base["id"])
        tl.supprimer_selection(True)
        self.assertEqual(len(p.clips_piste("video")), 1)
        self.assertTrue(tl.items_clips[base["id"]].verrou)
        p.basculer_piste("video", "verrou")
        tl.reconstruire()
        tl.couper_au_curseur()
        self.assertEqual(len(p.clips_piste("video")), 2)

    def test_piste_vide_retiree_seulement(self):
        d = tempfile.mkdtemp()
        p, c = projet_deux_pistes(d)
        self.assertFalse(p.retirer_piste("video2"))
        p.retirer_clip(c["id"])
        self.assertTrue(p.retirer_piste("video2"))

    def test_timeline_disposition(self):
        from app.timeline import Timeline, H_REGLE
        d = tempfile.mkdtemp()
        p, c = projet_deux_pistes(d)
        p.ajouter_piste("audio")
        tl = Timeline(p)
        pistes = tl._pistes()
        self.assertLess(pistes["video2"][0], pistes["video"][0])             # la vidéo 2 est au-dessus de la base
        self.assertLess(pistes["audio"][0], pistes["audio2"][0])
        self.assertEqual(tl.piste_a(pistes["audio2"][0] + 3), "audio2")
        self.assertEqual(tl.piste_a(H_REGLE - 2), None)
        self.assertIn("Vidéo 2", tl.libelle_piste("video2"))
        self.assertIn(c["id"], tl.items_clips)
        tl._retirer_piste("audio2")
        self.assertEqual(p.pistes_audio(), ["audio"])


if __name__ == "__main__":
    unittest.main()
