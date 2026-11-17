"""0.9.84 : lever le fond de n'importe quel sujet par le cloud (Bria VRMBG 3.0 sur fal.ai) ; l'export se sert de la
transparence rendue comme masque du plan."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestDetourageCloud(unittest.TestCase):
    def test_fabriquer_et_exporter(self):
        from app import detourage_cloud as DC, generateurs_video as GV, moteur, effets as E
        from app.fenetre import Fenetre
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_fal="id:secret")
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        c["src_fin"] = min(c["src_fin"], 1.5)
        envoi = {}

        def faux_demande(cle, point, corps, progression=None, arret=None, attente=0):
            envoi.update(point=point, corps=corps)
            return {"video": {"url": "http://faux/sortie.mov"}}

        def faux_telecharger(url, sortie):        # une vidéo transparente : un carré opaque au centre, le reste transparent
            moteur.lancer(["-y", "-f", "lavfi", "-i", "color=c=black@0.0:s=320x180:d=1.5,format=yuva444p",
                           "-vf", "drawbox=x=110:y=50:w=100:h=80:color=white@1:t=fill:replace=1", "-c:v", "prores_ks", "-profile:v", "4444",
                           "-pix_fmt", "yuva444p10le", sortie])
            return sortie
        anc = (GV.televerser, GV.demande_fal, GV.telecharger)
        GV.televerser = lambda cle, ch: "http://faux/entree.mp4"
        GV.demande_fal, GV.telecharger = faux_demande, faux_telecharger
        try:
            r = DC.fabriquer(ed.params, c, m)
            self.assertTrue(os.path.exists(r))
            self.assertEqual(envoi["point"], DC.POINT)
            self.assertEqual((envoi["corps"]["background_color"], envoi["corps"]["output_container_and_codec"]), ("Transparent", "mov_proresks"))
            envoi.clear()
            self.assertEqual(DC.fabriquer(ed.params, c, m), r)
            self.assertEqual(envoi, {})                                   # jamais repayé pour le même passage
        finally:
            GV.televerser, GV.demande_fal, GV.telecharger = anc
        self.assertEqual(DC.prix(10), 0.5)
        c["effets"] = [{"id": "detourage", "params": dict(E.defauts("detourage"), fond="couleur", couleur="#ff0000", methode="cloud",
                                                          adoucir=0.0)}]
        sortie = os.path.join(d, "export.mp4")
        from app import export
        export.exporter(ed.projet, sortie, "youtube", ed.params)
        self.assertTrue(os.path.exists(sortie))
        if True:
            from PySide6.QtGui import QImage
            img = os.path.join(d, "i.png")
            moteur.lancer(["-y", "-ss", "0.5", "-i", sortie, "-frames:v", "1", img])
            q = QImage(img)
            coin = q.pixelColor(5, 5)
            self.assertGreater(coin.red(), 180)                          # hors du sujet : le nouveau fond rouge
            self.assertLess(coin.green(), 80)
            centre = q.pixelColor(q.width() // 2, q.height() // 2)
            self.assertFalse(centre.red() > 180 and centre.green() < 80 and centre.blue() < 80, centre.name())   # le sujet reste


if __name__ == "__main__":
    unittest.main()
