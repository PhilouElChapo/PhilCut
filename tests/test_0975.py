"""0.9.75 : transformer une voix (sur ce poste : hauteur et timbre ; IA cloud : voix toute faite) ; guides fond, élément qui
suit, voix."""
import os, shutil, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=30):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestTransfo(unittest.TestCase):
    def test_filtres(self):
        from app import export, moteur
        self.assertEqual(export.filtre_transfo(0, 1.0), "")
        f = export.filtre_transfo(4, 1.13)
        self.assertIn("asetrate=48000*1.1300", f)
        if moteur.filtre_disponible("rubberband"):
            self.assertIn("rubberband=pitch=", f)
        c = {"voix_transfo": {"hauteur": -3, "timbre": 0.88}, "effets_audio": ["a_chaude"]}
        fs = export.filtres_voix(c)
        self.assertEqual(len(fs), 2)
        d = tempfile.mkdtemp()
        src = os.path.join(d, "v.wav")
        moteur.lancer(["-f", "lavfi", "-i", "sine=frequency=220:duration=2", "-ar", "48000", src])
        from app import voix
        out = voix.rendu_ecoute(src, ["a_chaude"], os.path.join(d, "o.wav"), 0, 2, 1.0, {"hauteur": -3, "timbre": 0.88})
        self.assertAlmostEqual(float(moteur.sonder(out)["duree"]), 2.0, delta=0.15)     # même durée : seule la voix change

    def test_cloud_et_fenetre(self):
        from app.fenetre import Fenetre
        from app import moteur, generateurs_video as GV, voix_transfo as VT
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params["clef_fal"] = "a:b"
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        dl = ed.transformer_voix(c)
        dl.preset.setCurrentIndex(dl.preset.findData("feminine"))
        dl.appliquer()
        self.assertEqual(c["voix_transfo"], {"hauteur": 4.0, "timbre": 1.13})
        dl.retirer()
        self.assertNotIn("voix_transfo", c)
        rendu = os.path.join(d, "rendu.wav")
        moteur.lancer(["-f", "lavfi", "-i", "sine=frequency=330:duration=3", rendu])
        demandes = []
        anc = (GV.televerser, GV.demande_fal, GV.telecharger)
        GV.televerser = lambda cle, ch: "https://cdn/x.wav"
        GV.demande_fal = lambda cle, point, corps, *a, **k: (demandes.append((point, corps)), {"audio": {"url": "https://x/y.mp3"}})[1]
        GV.telecharger = lambda url, sortie: shutil.copyfile(rendu, sortie) and sortie
        try:
            self.assertFalse(dl.b_cloud.isEnabled())                 # pas d'accord coché
            dl.accord.setChecked(True)
            self.assertTrue(dl.b_cloud.isEnabled())
            dl._test_oui = True
            dl.apercu.charger = lambda *a, **k: None
            dl.cloud()
            self.assertTrue(attendre(lambda: dl.resultat is not None))
        finally:
            GV.televerser, GV.demande_fal, GV.telecharger = anc
        self.assertEqual(demandes[0][0], "fal-ai/elevenlabs/voice-changer")
        self.assertEqual(demandes[0][1]["voice"], "Sarah")
        dl.apercu.arreter = lambda: None
        dl.poser()
        self.assertTrue(c["muet"])
        self.assertEqual(len(ed.projet.clips_piste("voix")), 1)
        self.assertEqual(VT.prix_cloud(60), 0.3)


if __name__ == "__main__":
    unittest.main()
