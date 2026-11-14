"""0.9.65 : faire parler un personnage sur le son. Le son sous un passage (voix + musique, à leur place et à leur volume),
le plan extrait, l'envoi à fal.ai (stockage puis file d'attente), la fenêtre (coût, case du visage, aperçu, pose à la
place du plan muet / au-dessus du film), le menu et le guide."""
import json, os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


def attendre(cond, s=15):
    t0 = time.time()
    while time.time() - t0 < s and not cond():
        app.processEvents()
        time.sleep(0.02)


def _projet(ed):
    from app import moteur
    d = os.environ["APPDATA"]
    v = commun.video_test(d, "parle.mp4", duree=4)
    voix = os.path.join(d, "voix_parle.wav")
    moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=3", voix])
    mus = os.path.join(d, "musique_parle.wav")
    moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=660:d=10", mus])
    p = ed.projet
    mv, mvo, mm = p.ajouter_media(v, moteur.sonder(v)), p.ajouter_media(voix, moteur.sonder(voix)), p.ajouter_media(mus, moteur.sonder(mus))
    c = p.ajouter_clip(mv["id"], "video", 0.0, 0.0, 4.0)
    p.ajouter_clip(mvo["id"], "voix", 0.5, 0.0, 3.0)
    p.ajouter_clip(mm["id"], "audio", 0.0, 2.0, 8.0)
    ed.rafraichir()
    return c


class TestLevres(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()

    def tearDown(self):
        self.ed.projet.modifie = False

    def test_son_et_plan(self):
        from app import levres as LV, moteur
        import numpy as np
        c = _projet(self.ed)
        sons = LV.sons_sous(self.ed.projet, 0.0, 4.0)
        self.assertEqual(len(sons), 2)
        s = LV.extraire_son(self.ed.projet, 0.0, 4.0, os.path.join(os.environ["APPDATA"], "sous.wav"))
        self.assertAlmostEqual(float(moteur.sonder(s)["duree"]), 4.0, delta=0.1)
        r = __import__("subprocess").run([moteur.ffmpeg(), "-v", "error", "-i", s, "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                                         capture_output=True)
        x = np.frombuffer(r.stdout, np.float32)
        spec = lambda a, b: np.abs(np.fft.rfft(x[int(a * 8000):int(b * 8000)]))
        f = np.fft.rfftfreq(int(0.4 * 8000), 1 / 8000)
        sp = spec(0.05, 0.45)
        self.assertGreater(sp[np.argmin(abs(f - 660))], 10 * sp[np.argmin(abs(f - 220))])   # avant la voix : la musique seule
        sp = spec(1.0, 1.4)
        self.assertGreater(sp[np.argmin(abs(f - 220))], 0.3 * sp[np.argmin(abs(f - 660))])   # puis la voix, à sa place
        with self.assertRaises(RuntimeError):
            LV.extraire_son(self.ed.projet, 20.0, 22.0, os.path.join(os.environ["APPDATA"], "vide.wav"))
        pl = LV.extraire_plan(self.ed.projet, c, os.path.join(os.environ["APPDATA"], "plan_parle.mp4"))
        self.assertAlmostEqual(float(moteur.sonder(pl)["duree"]), 4.0, delta=0.15)
        self.assertEqual(LV.prix("latentsync", 30), 0.20)
        self.assertEqual(LV.prix("latentsync", 60), 0.30)
        self.assertEqual(LV.prix("omnihuman", 10), 1.6)
        self.assertEqual([k for k, _m in LV.moteurs("video")], ["latentsync", "lipsync2"])

    def test_fal_envoi_et_file(self):
        from app import generateurs_video as GV
        appels = []

        def http(url, cle, corps=None, methode=None, delai=120):
            appels.append((url, corps))
            if "auth/token" in url:
                return {"token": "t", "token_type": "Bearer", "base_url": "https://v3.fal.media", "expires_at": "2099-01-01T00:00:00+00:00"}
            if url.endswith("/status"):
                return {"status": "COMPLETED"}
            if "/requests/" in url:
                return {"video": {"url": "https://exemple.invalid/v.mp4"}}
            return {"request_id": "r1"}

        class Rep:
            def __init__(self, data):
                self.data = data

            def read(self):
                return self.data

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        envois = []

        def urlopen(req, timeout=0):
            envois.append((getattr(req, "full_url", req), getattr(req, "headers", {})))
            if "files/upload" in getattr(req, "full_url", ""):
                return Rep(json.dumps({"access_url": "https://v3.fal.media/files/x/son.wav"}).encode())
            return Rep(b"MP4")
        anc = (GV._http, GV.urllib.request.urlopen, GV.time.sleep)
        GV._http, GV.urllib.request.urlopen, GV.time.sleep = http, urlopen, lambda s: None
        try:
            son = os.path.join(os.environ["APPDATA"], "envoi.wav")
            open(son, "wb").write(b"RIFF")
            self.assertEqual(GV.televerser("k", son), "https://v3.fal.media/files/x/son.wav")
            self.assertEqual(envois[0][1].get("Authorization"), "Bearer t")
            self.assertEqual(envois[0][1].get("Content-type"), "audio/wav")
            sortie = os.path.join(os.environ["APPDATA"], "rendu.mp4")
            GV.attendre_fal("k", "fal-ai/latentsync", {"audio_url": "a", "video_url": "v"}, sortie)
            self.assertEqual(open(sortie, "rb").read(), b"MP4")
            self.assertTrue(any(u.endswith("queue.fal.run/fal-ai/latentsync") for u, _c in appels))
        finally:
            GV._http, GV.urllib.request.urlopen, GV.time.sleep = anc

    def test_fenetre_video(self):
        from app import levres as LV, moteur
        c = _projet(self.ed)
        self.ed.params["clef_fal"] = "essai"
        d = self.ed.faire_parler(c)
        self.assertIn("voix_parle.wav", d.lbl_son.text())
        self.assertFalse(d.b_fabriquer.isEnabled())                  # case du visage pas cochée
        d.accord.setChecked(True)
        self.assertTrue(d.b_fabriquer.isEnabled())
        self.assertIn("0,20", d.cout.text())
        recu = {}
        rendu = commun.video_test(os.environ["APPDATA"], "rendu_parle.mp4", duree=4)

        def faux(params, k, son, sortie, image=None, video=None, **kw):
            recu.update(k=k, son=son, video=video)
            import shutil
            shutil.copy(rendu, sortie)
            return sortie
        anc = (LV.fabriquer, __import__("PySide6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.question)
        from PySide6.QtWidgets import QMessageBox
        LV.fabriquer, QMessageBox.question = faux, lambda *a, **k: QMessageBox.Yes
        try:
            d.fabriquer()
            attendre(lambda: d.b_poser.isEnabled())
        finally:
            LV.fabriquer, QMessageBox.question = anc
        self.assertEqual(recu["k"], "latentsync")
        self.assertAlmostEqual(float(moteur.sonder(recu["son"])["duree"]), 4.0, delta=0.1)
        d.poser()
        c2 = self.ed.projet.clip(c["id"])
        self.assertTrue(c2["muet"])
        self.assertEqual(self.ed.projet.media(c2["media"])["chemin"], d.resultat)
        self.ed.annuler()
        self.assertNotEqual(self.ed.projet.media(self.ed.projet.clip(c["id"])["media"])["chemin"], d.resultat)
        self.ed.params.pop("clef_fal", None)

    def test_fenetre_image_et_menus(self):
        _projet(self.ed)
        self.ed.params.pop("clef_fal", None)
        d = self.ed.faire_parler(genre="image")
        self.assertIn("clef fal.ai", d.cout.text())                  # sans clef : on dit où la mettre
        self.ed.params["clef_fal"] = "essai"
        d.accord.setChecked(True)
        d._maj()
        self.assertFalse(d.b_fabriquer.isEnabled())                   # pas encore d'image
        img = os.path.join(os.environ["APPDATA"], "perso.png")
        from PySide6.QtGui import QImage, QColor
        q = QImage(64, 64, QImage.Format_RGB32)
        q.fill(QColor("gray"))
        q.save(img)
        d._poser_image(img)
        self.assertTrue(d.b_fabriquer.isEnabled())
        self.assertIn("OmniHuman", d.moteur.currentText())
        self.ed.params.pop("clef_fal", None)
        from app import guides
        self.assertTrue(any(g["id"] == "levres" for g in guides.guides()))


if __name__ == "__main__":
    unittest.main()
