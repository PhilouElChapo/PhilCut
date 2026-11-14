"""0.9.67 : vidéo de narration déduite de ce qui est dit. Découpage de la voix en idées (ponctuation, silences, 2 à 8 s,
collées), présentateur proposé au début et à la fin, idées de l'IA bornées, prix, fabrication (faux cloud ; le
présentateur reçoit exactement son passage de voix), pose sous les mots (muets, un Annuler), reprise de la fenêtre."""
import json, os, shutil, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None

TEXTE = ("Bonjour à tous. Aujourd'hui nous partons en vol vers une île, au départ de la côte. Le moteur démarre, la radio grésille, "
         "et nous roulons vers la piste. Décollage ! En montée, la côte apparaît sous nos ailes, avec ses criques et ses villages "
         "perchés, puis la mer à perte de vue jusqu'à l'horizon où se dessine enfin l'île. Merci.")


def mots(t=0.5):
    out = []
    for w in TEXTE.split():
        out.append({"t0": round(t, 2), "t1": round(t + 0.32, 2), "mot": w})
        t += 0.38 + (0.7 if w.endswith(".") else 0)
    return out


def attendre(cond, s=30):
    t0 = time.time()
    while time.time() - t0 < s and not cond():
        app.processEvents()
        time.sleep(0.02)


class TestDecoupage(unittest.TestCase):
    def test_segments(self):
        from app import narration as NA
        m = mots()
        s = NA.segments(m)
        self.assertGreaterEqual(len(s), 3)
        self.assertAlmostEqual(s[0]["debut"], m[0]["t0"])
        for a, b in zip(s, s[1:]):
            self.assertAlmostEqual(a["fin"], b["debut"])                       # collés
        for x in s:
            self.assertLessEqual(x["fin"] - x["debut"], 8.5)
            self.assertGreaterEqual(x["fin"] - x["debut"], 2.0)
        self.assertEqual(" ".join(x["texte"] for x in s).split(), TEXTE.split())   # rien de perdu
        self.assertTrue(s[0]["texte"].startswith("Bonjour"))

    def test_presentateur_et_idees(self):
        from app import narration as NA
        n = NA.nouvelle(NA.segments(mots()))
        n["presentateur"]["actif"] = True
        NA.proposer_presentateur(n)
        self.assertTrue(n["plans"][0]["presentateur"] and n["plans"][-1]["presentateur"])
        self.assertIn("presenter", NA.consigne(n, 0))
        self.assertIn("illustrates", NA.consigne(n, 1))
        k = NA.lire_idees(n, json.dumps({"plans": [{"i": 1, "action": "Une hélice qui se met à tourner", "action_en": "a propeller starts",
                                                     "presentateur": True}, {"i": 99, "action": "x"}, {"i": 2, "action": ""}]}))
        self.assertEqual(k, 1)
        self.assertEqual(n["plans"][1]["action_en"], "a propeller starts")
        self.assertTrue(n["plans"][1]["presentateur"])
        n["presentateur"]["actif"] = False
        NA.lire_idees(n, json.dumps({"plans": [{"i": 1, "action": "y", "presentateur": True}]}))
        self.assertFalse(n["plans"][1]["presentateur"])                     # pas de présentateur : jamais coché


class TestFenetre(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()

    def tearDown(self):
        self.ed.projet.modifie = False
        for k in ("clef_fal",):
            self.ed.params.pop(k, None)

    def test_de_bout_en_bout(self):
        from app import generateurs_video as GV, levres as LV, montage_texte as MT, moteur
        from PySide6.QtWidgets import QMessageBox
        p = self.ed.projet
        voix = os.path.join(os.environ["APPDATA"], "voix_narration.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=200:d=30", voix])
        m = p.ajouter_media(voix, moteur.sonder(voix))
        cv = p.ajouter_clip(m["id"], "voix", 3.0)
        m["mots"] = [[x["t0"], x["t1"], x["mot"]] for x in mots(0.5)]      # transcription déjà faite
        self.ed.rafraichir()
        self.ed.params["clef_fal"] = "essai"
        d = self.ed.narration(cv)
        self.assertIs(self.ed.narration(cv), d)
        anc_tr = MT.transcrire
        MT.transcrire = lambda *a, **k: 0
        try:
            d.transcrire()
            attendre(lambda: d.narr is not None and not d._en_calcul())
        finally:
            MT.transcrire = anc_tr
        plans = d.narr["plans"]
        self.assertAlmostEqual(plans[0]["debut"], 3.5, delta=0.01)          # en temps de la timeline
        d.pres_actif.setChecked(True)
        self.assertTrue(plans[0]["presentateur"])
        img = os.path.join(os.environ["APPDATA"], "pres.png")
        from PySide6.QtGui import QImage, QColor
        q = QImage(64, 64, QImage.Format_RGB32)
        q.fill(QColor("gray"))
        q.save(img)
        d.narr["presentateur"]["image"] = img
        d._maj()
        self.assertFalse(d.b_fabriquer.isEnabled())                          # case du visage
        d.pres_accord.setChecked(True)
        self.assertTrue(d.b_fabriquer.isEnabled())
        rendu = commun.video_test(os.environ["APPDATA"], "plan_narr.mp4", duree=8)
        vus, sons = [], []

        def faux_gen(params, ident, consigne, sortie, *a, **k):
            vus.append(consigne)
            shutil.copy(rendu, sortie)
            return sortie

        def faux_lv(params, k, son, sortie, image=None, **kw):
            sons.append((k, float(moteur.sonder(son)["duree"]), image))
            shutil.copy(rendu, sortie)
            return sortie
        anc = (GV.generer, LV.fabriquer, QMessageBox.question)
        GV.generer, LV.fabriquer, QMessageBox.question = faux_gen, faux_lv, lambda *a, **k: QMessageBox.Yes
        try:
            d.fabriquer()
            attendre(lambda: not d._en_calcul() and d.b_poser.isEnabled(), 60)
        finally:
            GV.generer, LV.fabriquer, QMessageBox.question = anc
        npres = sum(1 for x in plans if x["presentateur"])
        self.assertEqual(len(sons), npres)
        self.assertEqual(len(vus), len(plans) - npres)
        self.assertEqual(sons[0][0], "omnihuman")
        self.assertAlmostEqual(sons[0][1], plans[0]["fin"] - plans[0]["debut"], delta=0.1)   # exactement son passage
        self.assertEqual(sons[0][2], img)
        n_avant = len(p.clips)
        d.poser()
        poses = [c for c in p.clips if c.get("narration")]
        self.assertEqual(len(poses), len(plans))
        self.assertTrue(all(c["muet"] for c in poses))
        self.assertAlmostEqual(min(c["debut"] for c in poses), 3.5, delta=0.01)
        self.ed.annuler()
        self.assertEqual(len(p.clips), n_avant)
        d.close()
        self.ed._narrations.clear()
        d2 = self.ed.narration(p.clip(cv["id"]))
        self.assertIsNotNone(d2.narr)
        self.assertEqual(len(d2.narr["plans"]), len(plans))


if __name__ == "__main__":
    unittest.main()
