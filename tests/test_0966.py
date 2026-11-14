"""0.9.66 : clip de groupe déduit d'une chanson. Ecoute (mesures, parties, refrain qui revient), groupe inventé,
découpage calé sur les mesures avec reprise des plans du premier refrain, prix, fabrication (faux cloud : vidéo puis
lèvres sur la voix), montage sous la chanson (coupes sur les mesures, plans muets, un Annuler), idées de l'IA bornées,
fenêtre, menus et lien avec la Fabrique musique."""
import json, os, shutil, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
import numpy as np


def attendre(cond, s=30):
    t0 = time.time()
    while time.time() - t0 < s and not cond():
        app.processEvents()
        time.sleep(0.02)


def chanson(chemin):
    """Intro calme, couplet, refrain fort, couplet, refrain, fin : 120 battements par minute, mesures de 2 s."""
    import wave
    sr, beat = 22050, 0.5
    bar = 4 * beat

    def accord(notes, d, vol):
        t = np.arange(int(d * sr)) / sr
        return vol * sum(np.sin(2 * np.pi * 440 * 2 ** ((n - 9) / 12) * t) for n in notes) / len(notes)

    def batterie(d, vol):
        out = np.zeros(int(d * sr))
        rng = np.random.default_rng(1)
        for k in range(int(d / beat)):
            i, L = int(k * beat * sr), int(0.12 * sr)
            env = np.exp(-np.arange(L) / (0.02 * sr))
            sig = (np.sin(2 * np.pi * 60 * np.arange(L) / sr) if k % 2 == 0 else rng.standard_normal(L) * 0.5) * env
            out[i:i + L] += vol * sig[:len(out) - i]
        return out

    def partie(n, notes, vol, dr):
        x = accord(notes, n * bar, vol)
        return x + batterie(n * bar, dr) if dr else x
    A, B = [0, 4, 7], [5, 9, 12]
    x = np.concatenate([partie(8, [0, 7], 0.08, 0), partie(8, A, 0.2, 0.3), partie(8, B, 0.45, 0.6), partie(8, A, 0.2, 0.3),
                        partie(8, B, 0.45, 0.6), partie(4, [0, 7], 0.06, 0)])
    x = x / np.abs(x).max() * 0.8
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return chemin


CHANSON = None


def _chanson():
    global CHANSON
    if CHANSON is None:
        CHANSON = chanson(os.path.join(os.environ["APPDATA"], "chanson_clip.wav"))
    return CHANSON


class TestEcoute(unittest.TestCase):
    def test_parties_et_plans(self):
        from app import clip_groupe as CG
        a = CG.analyser(_chanson(), {}, separer=False)
        types = [s["type"] for s in a["sections"]]
        self.assertEqual(types, ["intro", "couplet", "refrain", "couplet", "refrain", "fin"])
        self.assertAlmostEqual(a["bpm"], 120, delta=2)
        c = CG.nouveau(_chanson(), a, lieu="concert")
        self.assertGreaterEqual(len(c["groupe"]), 3)                          # un groupe : au moins trois musiciens
        pl = c["plans"]
        self.assertAlmostEqual(pl[0]["debut"], 0.0)
        self.assertAlmostEqual(pl[-1]["fin"], a["duree"], delta=0.01)
        for p, q in zip(pl, pl[1:]):
            self.assertAlmostEqual(p["fin"], q["debut"])                      # sans trou
            self.assertTrue(any(abs(p["fin"] - m) < 0.01 for m in a["mesures"]))   # coupe sur une mesure
            self.assertLessEqual(p["fin"] - p["debut"], 8.01)
        repris = [p for p in pl if p["reprend"] is not None]
        self.assertTrue(repris)                                              # le 2e refrain reprend le premier
        self.assertTrue(all(pl[p["reprend"]]["reprend"] is None for p in repris))
        n_avec = len(CG.a_fabriquer(c))
        c["reutiliser"] = False
        c["plans"] = CG.decouper(c)
        self.assertGreater(len(CG.a_fabriquer(c)), n_avec)
        # consigne : anglais, sans nom propre ni marque, rendu dessin animé
        c["anime"] = True
        t = CG.consigne(c, 3, traduire=False)
        self.assertIn("2D animated", t)
        self.assertIn("no logos", t)

    def test_groupe_depuis_fiche(self):
        from app import clip_groupe as CG
        a = {"caption_en": "", "chante": False, "voix_fr": "", "percussif": 0, "basses": 0, "brillance": 0}
        g = CG.groupe_propose(a, {"style": "funk", "instruments": "", "phrase": "", "instrumental": False})
        roles = [m["role"] for m in g]
        self.assertEqual(roles[0], "chant")
        self.assertIn("basse", roles)
        self.assertIn("cuivres", roles)

    def test_idees_bornees(self):
        from app import clip_groupe as CG
        a = CG.analyser(_chanson(), {}, separer=False)
        c = CG.nouveau(_chanson(), a)
        i_rep = next(i for i, p in enumerate(c["plans"]) if p["reprend"] is not None)
        n = CG.lire_idees(c, json.dumps({"plans": [{"i": 0, "action": "Un phare dans la brume", "action_en": "a lighthouse in fog",
                                                     "qui": ["batterie", "inconnu"]},
                                                    {"i": 999, "action": "x"}, {"i": i_rep, "action": "ignoré"}]}))
        self.assertEqual(n, 1)
        self.assertEqual(c["plans"][0]["qui"], ["batterie"])
        self.assertNotEqual(c["plans"][i_rep]["action"], "ignoré")


class TestFenetre(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()

    def tearDown(self):
        self.ed.projet.modifie = False
        self.ed.params.pop("clef_fal", None)

    def test_de_bout_en_bout(self):
        from app import clip_groupe as CG, generateurs_video as GV, levres as LV, moteur
        from PySide6.QtWidgets import QMessageBox
        p = self.ed.projet
        m = p.ajouter_media(_chanson(), moteur.sonder(_chanson()))
        cs = p.ajouter_clip(m["id"], "audio", 2.0)
        self.ed.rafraichir()
        self.ed.params["clef_fal"] = "essai"
        d = self.ed.clip_groupe(cs, {"lieu": "ailleurs", "anime": True})
        self.assertIs(self.ed.clip_groupe(cs), d)                         # une seule fenêtre par morceau
        self.assertEqual(d.lieu.currentData(), "ailleurs")
        d.separer.setChecked(False)
        d.ecouter()
        attendre(lambda: d.clip is not None and not d._en_calcul())
        self.assertTrue(d.anime.isChecked())
        self.assertEqual(d.table.rowCount(), len(d.clip["plans"]))
        self.assertFalse(d.b_fabriquer.isEnabled())                        # case « musiciens inventés »
        d.accord.setChecked(True)
        d.images.setChecked(False)
        self.assertTrue(d.b_fabriquer.isEnabled())
        self.assertIn("$", d.cout.text())
        d.table.item(0, 2).setText("Le lieu au lever du jour")
        rendu = commun.video_test(os.environ["APPDATA"], "plan_clip.mp4", duree=8)
        vus = []

        def faux_gen(params, ident, consigne, sortie, duree=5, format_="16:9", image=None, progression=None, arret=lambda: False):
            vus.append(consigne)
            shutil.copy(rendu, sortie)
            return sortie
        anc = (GV.generer, QMessageBox.question)
        GV.generer, QMessageBox.question = faux_gen, lambda *a, **k: QMessageBox.Yes
        try:
            d.fabriquer()
            attendre(lambda: not d._en_calcul() and d.b_poser.isEnabled(), 60)
        finally:
            GV.generer, QMessageBox.question = anc
        self.assertEqual(len(vus), len([x for x in d.clip["plans"] if x["reprend"] is None]))
        self.assertTrue(any("2D animated" in v for v in vus))
        self.assertIn("lever du jour", d.clip["plans"][0]["action"])
        self.assertTrue(os.path.exists(os.path.join(d.clip["dossier"], "clip.json")))
        n_avant = len(p.clips)
        d.poser()
        poses = [c for c in p.clips if "clip_groupe" in c]
        self.assertEqual(len(poses), len(d.clip["plans"]))
        self.assertTrue(all(c["muet"] for c in poses))
        self.assertAlmostEqual(min(c["debut"] for c in poses), 2.0, delta=0.01)   # sous la chanson
        self.ed.annuler()
        self.assertEqual(len(p.clips), n_avant)
        # la fenêtre se rouvre avec ce clip (clip.json rattaché au morceau)
        d.close()
        self.ed._clips_groupe.clear()
        d2 = self.ed.clip_groupe(p.clip(cs["id"]))
        self.assertIsNotNone(d2.clip)
        self.assertEqual(len(d2.clip["plans"]), len(d.clip["plans"]))

    def test_menus_et_fabrique(self):
        from app.dialogues_musique_ia import DialogueFabriqueMusique, Hote
        h = Hote()
        h.clip = True
        d = DialogueFabriqueMusique(None, {}, h)
        d.clip_lieu.setCurrentIndex(d.clip_lieu.findData("concert"))
        d.clip_anime.setChecked(True)
        self.assertEqual(d.fiche()["clip"], {"lieu": "concert", "anime": True})
        d2 = DialogueFabriqueMusique(None, {}, Hote())
        self.assertTrue(d2.ligne_clip.isHidden())                         # PhilMusic : pas de clip vidéo
        self.assertNotIn("clip", d2.fiche())


if __name__ == "__main__":
    unittest.main()
