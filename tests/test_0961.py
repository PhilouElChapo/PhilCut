"""0.9.61 : règle « prompt en anglais » — on écrit dans la langue du système, PhilCut traduit, on voit les deux et la
traduction reste modifiable ; une consigne rédigée en anglais (IA, « Rédiger ») est traduite dans l'autre sens.
Plan de liaison, séquence de personnages, tampons IA, musique IA (case bilingue) ; Fabrique (anglais en direct)."""
import os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
from app import consigne_bilingue as CB

TRAD = {"la caméra monte au-dessus du village": "the camera rises above the village",
        "un moulin": "a windmill"}


def faux_vers(t):
    return TRAD.get(t, ""), ([] if t in TRAD else [t.split()[0]])


def faux_depuis(t, langue=None):
    return {v: k for k, v in TRAD.items()}.get(t, "")


class TestCase_(unittest.TestCase):
    def setUp(self):
        self.anc = CB.vers_anglais, CB.depuis_anglais
        CB.vers_anglais, CB.depuis_anglais = faux_vers, faux_depuis

    def tearDown(self):
        CB.vers_anglais, CB.depuis_anglais = self.anc

    def test_ecrire_dans_sa_langue(self):
        c = CB.ConsigneBilingue()
        vus = []
        c.textChanged.connect(lambda: vus.append(c.toPlainText()))
        c.source.setPlainText("la caméra monte au-dessus du village")
        c.attendre()
        self.assertEqual(c.toPlainText(), "the camera rises above the village")
        self.assertIn("✓", c.etat.text())
        self.assertIn("the camera rises above the village", vus)
        # correction à la main : gardée, c'est elle qui part
        c.anglais.setPlainText("the drone camera rises above the old village")
        c.attendre()
        self.assertEqual(c.toPlainText(), "the drone camera rises above the old village")
        self.assertIn("main", c.etat.text())
        # mot introuvable : dit, sans bloquer
        c.source.setPlainText("zorglub tourne")
        c.attendre()
        self.assertIn("zorglub", c.etat.text())

    def test_consigne_de_l_ia_lue_dans_sa_langue(self):
        c = CB.ConsigneBilingue()
        c.setPlainText("a windmill")
        c.attendre()
        self.assertEqual(c.texte_source(), "un moulin")
        self.assertEqual(c.toPlainText(), "a windmill")              # rien n'est retraduit par-dessus
        c.setPlainText("anything", source="ce que je veux")
        self.assertEqual(c.texte_source(), "ce que je veux")

    def test_frappe_rapide_derniere_gagne(self):
        c = CB.ConsigneBilingue()
        c.source.setPlainText("un")
        c.source.setPlainText("un moulin")
        c.attendre()
        self.assertEqual(c.toPlainText(), "a windmill")

    def test_philcut_en_anglais(self):
        from app import langue as L
        anc = L.LANGUE
        L.LANGUE = "en"
        try:
            c = CB.ConsigneBilingue()
            self.assertTrue(c.source.isHidden())
            self.assertFalse(c.anglais.isHidden())
            c.setPlainText("a windmill")
            self.assertEqual(c.toPlainText(), "a windmill")
        finally:
            L.LANGUE = anc

    def test_fenetres(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        from app.dialogues_liaison import DialogueLiaison
        from app import moteur
        v = commun.video_test(os.environ["APPDATA"], "cb.mp4", duree=2)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        a, b = ed.projet.ajouter_clip(m["id"]), ed.projet.ajouter_clip(m["id"])
        d = DialogueLiaison(ed, a, b)
        self.assertIsInstance(d.consigne, CB.ConsigneBilingue)
        t0 = time.time()
        while time.time() - t0 < 60 and d.images is None and "✕" not in d.etat.text():
            app.processEvents()
            time.sleep(0.02)
        d.consigne.attendre()
        self.assertTrue(d.consigne.toPlainText())                    # la 1re proposition, en anglais…
        d.consigne.source.setPlainText("la caméra monte au-dessus du village")
        d.consigne.attendre()
        self.assertEqual(d.consigne.toPlainText().strip(), "the camera rises above the village")
        from verif_tronques import tronques
        self.assertEqual(tronques(d), [])
        d.close()
        # Fabrique : l'anglais en direct sous la phrase, corrigé à la main = envoyé
        from app.consigne_bilingue import AnglaisEnDirect
        from PySide6.QtWidgets import QPlainTextEdit
        champ = QPlainTextEdit()
        w = AnglaisEnDirect(champ, faux_vers)
        champ.setPlainText("un moulin")
        w.attendre()
        self.assertEqual(w.texte(), "a windmill")
        self.assertFalse(w.retouche())
        w.anglais.setPlainText("an old windmill at sunset")
        self.assertTrue(w.retouche())
        champ.setPlainText("la caméra monte au-dessus du village")      # nouvelle phrase : nouvelle traduction
        self.assertFalse(w.retouche())
        w.attendre()
        self.assertEqual(w.texte(), "the camera rises above the village")
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
