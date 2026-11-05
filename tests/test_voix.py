"""Voix : karaoké (balises ASS mot à mot), regroupement des mots de whisper.cpp, assemblage d'un doublage calé sur la
timeline (accélération si une phrase dépasse sa place), traduction locale simulée, fenêtres de la voix. Rien d'Internet."""
import os, sys, tempfile, unittest, wave
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun  # noqa: F401
from app import moteur, packs_ia, sous_titres as ST, titres as T, voix as V


def _bip(chemin, duree, freq=440):
    moteur.lancer(["-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duree}", "-ac", "1", "-ar", "22050", chemin])
    return chemin


class TestKaraoke(unittest.TestCase):
    def test_balises(self):
        k = T.karaoke(1.0, [(1.0, 1.4, "Bonjour"), (1.6, 1.8, "à"), (1.8, 2.5, "tous")])
        self.assertEqual(k, "{\\kf40}Bonjour {\\k20}{\\kf20}à {\\kf70}tous")
        a = T.ass([], 1920, 1080, 30, [(1, 3, "Bonjour à tous", [(1, 1.4, "Bonjour")]), (4, 5, "simple")])
        self.assertIn("\\kf40}Bonjour", a)
        self.assertIn("{\\fad(120,120)}simple", a)
        self.assertIn("2\n00:00:04,000", T.srt([(1, 3, "a", [(1, 2, "a")]), (4, 5, "b")]))

    def test_mots_whisper(self):
        j = [{"text": "[_BEG_]"}, {"text": " Bon", "offsets": {"from": 0, "to": 200}}, {"text": "jour", "offsets": {"from": 200, "to": 400}},
             {"text": " tous", "offsets": {"from": 600, "to": 900}}, {"text": ".", "offsets": {"from": 900, "to": 950}}]
        self.assertEqual(packs_ia.mots_segment(j, (0, 1, "x")), [(0.0, 0.4, "Bonjour"), (0.6, 0.95, "tous.")])
        self.assertEqual(len(packs_ia.mots_segment([], (0, 1, "a b"))), 2)

    def test_lignes_courtes(self):
        mots = [(i * 0.5, i * 0.5 + 0.5, w) for i, w in enumerate("Bonjour à tous et bienvenue dans cette vidéo".split())]
        l = ST.decouper_mots(0, 4, "", mots)
        self.assertEqual(len(l), 2)
        self.assertTrue(all(len(x[2]) <= 36 for x in l))
        self.assertEqual(l[0][0], 0)
        self.assertEqual(l[-1][1], 4)


class TestDoublage(unittest.TestCase):
    def test_assembler(self):
        d = tempfile.mkdtemp()
        a = _bip(os.path.join(d, "a.wav"), 1.0)
        b = _bip(os.path.join(d, "b.wav"), 2.0, 660)          # 2 s pour 1,5 s de place : accéléré
        sortie = V.assembler([(0.5, a, 3.0), (2.0, b, 1.5)], os.path.join(d, "dub.wav"), duree_totale=5.0)
        with wave.open(sortie) as w:
            self.assertEqual(w.getframerate(), V.TAUX)
            self.assertAlmostEqual(w.getnframes() / V.TAUX, 5.0, delta=0.05)
            import numpy as np
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        self.assertLess(abs(x[: int(0.4 * V.TAUX)]).max(), 50)            # silence avant la première phrase
        self.assertGreater(abs(x[int(0.7 * V.TAUX): int(1.2 * V.TAUX)]).max(), 1000)
        fin_b = 2.0 + 1.5                                    # 2 s accélérés ×1,33 pour tenir dans 1,5 s
        self.assertLess(abs(x[int((fin_b + 0.15) * V.TAUX):]).max(), 50)   # la seconde phrase a été raccourcie

    def test_traduire_local(self):
        with mock.patch("app.ia_locale.modele_actif", return_value="vision_leger"), \
                mock.patch("app.ia_locale.generer", return_value='{"t": ["Hello", "Welcome"]}'):
            self.assertEqual(V.traduire(["Bonjour", "Bienvenue"], "en", {}), ["Hello", "Welcome"])
        with mock.patch("app.ia_locale.modele_actif", return_value="vision_leger"), \
                mock.patch("app.ia_locale.generer", return_value='{"t": ["Hello"]}'):
            with self.assertRaises(V.ErreurVoix):
                V.traduire(["Bonjour", "Bienvenue"], "en", {})
        with mock.patch("app.ia_locale.modele_actif", return_value=None):
            with self.assertRaises(V.ErreurVoix):
                V.traduire(["Bonjour"], "en", {})

    def test_doubler(self):
        d = tempfile.mkdtemp()
        from app.projet import Projet
        pj = Projet()
        segs = [(0.0, 1.0, "Bonjour"), (2.0, 3.0, "Au revoir")]

        def lire(texte, sortie, params, m, v, vitesse=1.0):
            return _bip(sortie, 0.8)
        with mock.patch.object(V, "segments_parles", return_value=segs), \
                mock.patch.object(V, "traduire", return_value=["Hello", "Goodbye"]), \
                mock.patch.object(V, "voix_locale_langue", return_value="voix_en_femme"), \
                mock.patch.object(V, "lire", side_effect=lire):
            chemin, st = V.doubler(pj, {}, "en", os.path.join(d, "dub.wav"))
        self.assertTrue(os.path.exists(chemin))
        self.assertEqual(st, [(0.0, 1.0, "Hello"), (2.0, 3.0, "Goodbye")])
        self.assertAlmostEqual(V.duree_wav(chemin), 2.8, delta=0.1)

    def test_prix_gemini(self):
        p = V.prix_gemini("x" * 840)       # une minute de voix environ
        self.assertTrue(0.01 < p < 0.03, p)

    def test_synthese_sans_voix(self):
        with mock.patch.object(packs_ia, "modele_actif", return_value=None):
            with self.assertRaises(V.ErreurVoix):
                V.lire("Bonjour", os.path.join(tempfile.mkdtemp(), "x.wav"), {})


class TestNarrationEtAutotune(unittest.TestCase):
    def test_chaines_narration(self):
        from app.export import FILTRES_AUDIO, NARRATION
        d = tempfile.mkdtemp()
        src = _bip(os.path.join(d, "v.wav"), 2.0, 220)
        for eid, _lib in NARRATION[1:]:
            out = V.rendu_ecoute(src, [eid], os.path.join(d, eid + ".wav"))
            self.assertGreater(V.duree_wav(out), 1.5, eid)

    def test_couper_blancs(self):
        d = tempfile.mkdtemp()
        brut = os.path.join(d, "b.wav")
        moteur.lancer(["-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono:d=1", "-f", "lavfi", "-i", "sine=frequency=300:duration=1.5",
                       "-f", "lavfi", "-i", "anullsrc=r=22050:cl=mono:d=1", "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1", "-ar", "22050", brut])
        net = V.couper_blancs(brut, os.path.join(d, "n.wav"))
        self.assertAlmostEqual(V.duree_wav(net), 1.5, delta=0.45)
        self.assertLess(V.duree_wav(net), V.duree_wav(brut) - 1.0)

    def test_autotune(self):
        import numpy as np
        from app import autotune as A
        if not moteur.filtre_disponible("rubberband"):
            self.skipTest("rubberband absent")
        d = tempfile.mkdtemp()
        taux = 22050
        t = np.arange(int(taux * 2)) / taux
        f = np.where(t < 1, 225.0, 305.0)                          # chanté un peu faux
        ph = 2 * np.pi * np.cumsum(f) / taux
        x = 0.5 * np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
        src = os.path.join(d, "v.wav")
        with wave.open(src, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(taux)
            w.writeframes((x * 20000).astype("<i2").tobytes())
        tm, f0 = A.hauteurs(A.lire_mono(src))
        self.assertAlmostEqual(float(np.median(f0[(tm > 0.2) & (tm < 0.8)])), 225.0, delta=1.0)
        A.corriger(src, os.path.join(d, "o.wav"), force="robot")
        tm2, f2 = A.hauteurs(A.lire_mono(os.path.join(d, "o.wav")))
        self.assertAlmostEqual(float(np.median(f2[(tm2 > 0.3) & (tm2 < 0.8)])), 220.0, delta=2.0)        # La juste
        self.assertAlmostEqual(float(np.median(f2[(tm2 > 1.3) & (tm2 < 1.8)])), 311.1, delta=3.0)        # Ré# juste
        A.corriger(src, os.path.join(d, "maj.wav"), tonique=0, gamme="majeure", force="robot")
        tm3, f3 = A.hauteurs(A.lire_mono(os.path.join(d, "maj.wav")))
        self.assertAlmostEqual(float(np.median(f3[(tm3 > 1.3) & (tm3 < 1.8)])), 293.7, delta=3.0)        # Ré : Ré# n'est pas en Do majeur


class TestFenetresVoix(unittest.TestCase):
    def test_fenetres(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from app import dialogues_voix as DV
        with mock.patch.object(DV, "micros", return_value=([], None)):      # pas de micro (ni de son) sur le serveur de test
            e = DV.DialogueEnregistrement(None, {}, 12.5)
        self.assertFalse(e.b_rec.isEnabled())
        self.assertEqual(e.amelioration.currentData(), "a_studio")             # voix studio (RNNoise) par défaut
        self.assertTrue(e.blancs.isChecked())
        s = DV.DialogueSynthese(None, {"clef_gemini": "x"})
        self.assertTrue(any(s.choix.itemData(i)[0] == "gemini" for i in range(s.choix.count())))
        s.texte.setPlainText("Bonjour")
        s.choix.setCurrentIndex(s.choix.count() - 1)
        self.assertIn("$", s.prix.text())
        with mock.patch("app.ia_locale.modele_actif", return_value=None), mock.patch("app.ia.disponible", return_value=False):
            dd = DV.DialogueDoublage(None, {})
            self.assertFalse(dd.b_ok.isEnabled())
            self.assertIn("Il manque", dd.alerte.text())


if __name__ == "__main__":
    unittest.main()
