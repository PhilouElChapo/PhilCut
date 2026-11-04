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


class TestFenetresVoix(unittest.TestCase):
    def test_fenetres(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        from app import dialogues_voix as DV
        with mock.patch.object(DV, "micros", return_value=([], None)):      # pas de micro (ni de son) sur le serveur de test
            e = DV.DialogueEnregistrement(None, {}, 12.5)
        self.assertFalse(e.b_rec.isEnabled())
        self.assertTrue(any(c.eid == "a_harmonieuse" and c.isChecked() for c in e.cases))
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
