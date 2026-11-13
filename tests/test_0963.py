"""0.9.63 : Fabrique musique — « à la manière de » enrichi par le catalogue en ligne (familles, recherche tolérante),
voix « à la manière de » et voix décrite d'un morceau (isolée puis mesurée, jamais copiée), passage choisi pour
s'inspirer, « Plus de résultats » et « S'inspirer » actif dès qu'un morceau est choisi."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
import numpy as np


def attendre(cond, s=10):
    import time
    t0 = time.time()
    while time.time() - t0 < s and not cond():
        app.processEvents()
        time.sleep(0.02)


class TestStyles(unittest.TestCase):
    def test_catalogue_et_recherche(self):
        from app import styles_ia as S
        S.recharger_catalogue()
        refs = S._toutes()
        noms = {v[0] for v in refs.values()}
        self.assertGreater(len(noms), 200)
        self.assertIn("metallica", noms)
        self.assertEqual(S.genre("metallica"), "rock_metal")
        self.assertEqual(S.genre("ludovico einaudi"), "film")
        self.assertEqual(S.genre("john wayne"), "cinema")
        texte = lambda n: n + " " + S.mots_cles(n) + " " + " ".join(refs[S._net(n)][1].values())
        self.assertTrue(S.correspond("metallic", texte("metallica")))       # la recherche de Philippe
        self.assertTrue(S.correspond("zimer", texte("hans zimmer")))         # une lettre près
        self.assertFalse(S.correspond("valse", texte("metallica")))
        r = S.transposer("chanté à la manière de Metallica", "musique")
        self.assertEqual(r["styles"][0][0], "metallica")
        self.assertNotIn("metallica", r["ajout"].lower())

    def test_catalogue_sans_nom_ni_visage(self):
        d = json.load(open(os.path.join(commun.RACINE, "catalogue", "styles.json"), encoding="utf-8"))
        from app import styles_ia as S
        for e in d["styles"]:
            self.assertIn(e["genre"], S.GENRES, e)
            if e.get("nature") == "genre":                 # un genre (synthwave, k-pop) n'est à personne
                continue
            for k in ("voix", "musique", "image", "jeu"):
                for n in e["noms"]:
                    n = n.rstrip("*")
                    if len(n) > 3:
                        self.assertNotIn(n, (e.get(k) or "").lower(), e)

    def test_fenetre_styles(self):
        from PySide6.QtWidgets import QWidget
        from app.dialogues_creatif import choisir_style
        vus = {}

        class Hote(QWidget):
            def _test_style(self, d):
                d._cherche.setText("metallic")
                vis = [d._arbre.topLevelItem(i).text(0) for i in range(d._arbre.topLevelItemCount()) if not d._arbre.topLevelItem(i).isHidden()]
                vus["metal"] = vis
                d._cherche.setText("Groupe Inventé")
                vus["absent"] = d._b_nom.isVisible() or not d._b_nom.isHidden()
                d._b_nom.click()
        h = Hote()
        self.assertEqual(choisir_style(h, {}, "voix"), "Groupe Inventé")
        self.assertIn("Metallica", vus["metal"])
        self.assertTrue(vus["absent"])
        noms = []

        class Hote2(QWidget):
            def _test_style(self, d):
                g = d._genre.findData("film")
                d._genre.setCurrentIndex(g)
                noms.extend(d._arbre.topLevelItem(i).text(0) for i in range(d._arbre.topLevelItemCount()) if not d._arbre.topLevelItem(i).isHidden())
        choisir_style(Hote2(), {}, "musique")
        self.assertIn("Hans Zimmer", noms)
        self.assertNotIn("Metallica", noms)
        from app import styles_ia as S
        self.assertEqual(noms, sorted(noms, key=S._net))                    # ordre alphabétique sans accents


class TestVoix(unittest.TestCase):
    def _voix(self, base, vib, sr=16000):
        t = np.arange(sr * 8) / sr
        f = base * 2 ** ((vib / 1200) * np.sin(2 * np.pi * 5.5 * t)) * np.where((t % 2) < 1, 1, 2 ** (5 / 12))
        ph = 2 * np.pi * np.cumsum(f) / sr
        return (sum(np.sin(k * ph) / k for k in range(1, 8)) * 0.3).astype(np.float32), sr

    def test_mesures(self):
        from app import musique_ia as MI
        en, fr = MI.decrire_voix_mesures(MI.mesurer_voix(*self._voix(110, 0)))
        self.assertIn("male", en)
        self.assertIn("straight tone", en)
        en, fr = MI.decrire_voix_mesures(MI.mesurer_voix(*self._voix(330, 45)))
        self.assertIn("female", en)
        self.assertIn("vibrato", en)
        with self.assertRaises(RuntimeError):
            MI.mesurer_voix(np.zeros(16000 * 4, np.float32), 16000)

    def test_consigne_et_fenetre(self):
        from app import musique_ia as MI
        f = MI.fiche_vide()
        f.update(instrumental=False, voix_decrite={"en": "deep low male vocals, light vibrato", "fr": "x"})
        self.assertIn("deep low male vocals", MI.consigne(f)["caption"])
        from PySide6.QtWidgets import QPushButton
        from app.dialogues_musique_ia import DialogueFabriqueMusique
        d = DialogueFabriqueMusique(None, {})
        self.assertEqual(len(d.b_voix_style.menu().actions()), 3)
        d._poser_voix_decrite({"en": "high female vocals, soprano range", "fr": "voix de femme aiguë", "fichier": "chanson.mp3"})
        self.assertFalse(d.instrumental.isChecked())
        self.assertFalse(d.voix.isEnabled())
        self.assertIn("soprano", d.fiche()["voix_decrite"]["en"])
        self.assertIn("chanson.mp3", d.voix_decrite_info.text())
        d._sans_voix_decrite()
        self.assertIsNone(d.fiche()["voix_decrite"])
        self.assertTrue(d.voix.isEnabled())


class TestPassage(unittest.TestCase):
    def test_extraire_et_choisir(self):
        from app import moteur, musique_ia as MI
        src = os.path.join(os.environ["APPDATA"], "morceau.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=440:d=20", src])
        MI.declarer(src, libre=True)
        self.assertEqual(MI.extraire_passage(src, 0, 20), src)               # tout le morceau : pas de copie
        p = MI.extraire_passage(src, 5, 12)
        self.assertNotEqual(p, src)
        self.assertAlmostEqual(float(moteur.sonder(p)["duree"]), 7, delta=0.3)
        self.assertTrue(MI.peut_partir_de(p))                                # la déclaration suit le passage
        with self.assertRaises(RuntimeError):
            MI.extraire_passage(src, 5, 6)
        from PySide6.QtWidgets import QWidget
        from app.dialogues_musique_ia import choisir_passage

        class Hote(QWidget):
            def _test_passage(self, d):
                d._apercu.debut.setValue(3)
                d._apercu.fin.setValue(9)
                d._b_ok.click()
        self.assertEqual(choisir_passage(Hote(), src, "t", "c"), (3.0, 9.0))


class TestEnLigne(unittest.TestCase):
    def test_plus_et_inspirer_des_le_choix(self):
        from app import musique_en_ligne as ML
        from app.dialogues_musique_ia import DialogueMusiqueEnLigne, PAR_PAGE
        demandes = []
        anc_ch, anc_tel = ML.chercher, ML.telecharger

        def faux(texte, source="ytmusic", n=30):
            demandes.append(n)
            return [{"titre": f"t{i}", "page": f"p{i}", "source": "audionautix"} for i in range(n)]
        dl = os.path.join(os.environ["APPDATA"], "dl.mp3")
        open(dl, "wb").write(b"x")
        ML.chercher, ML.telecharger = faux, lambda x, *a, **k: dl
        recu = []
        try:
            m = DialogueMusiqueEnLigne(None, {"musique_en_ligne_ok": True, "musique_en_ligne_source": "audionautix"},
                                       utiliser=recu.append, libelle_utiliser="S'inspirer de ce morceau")
            m.texte.setText("calm")
            m.chercher()
            attendre(lambda: m.liste.count() == PAR_PAGE)
            self.assertFalse(m.b_plus.isHidden())
            m.plus()
            attendre(lambda: m.liste.count() == 2 * PAR_PAGE)
            self.assertEqual(demandes, [PAR_PAGE, 2 * PAR_PAGE])
            self.assertFalse(m.b_utiliser.isEnabled())
            m.liste.setCurrentRow(3)
            self.assertTrue(m.b_utiliser.isEnabled())                       # actif dès le choix
            m.b_utiliser.click()                                            # télécharge, puis s'inspire
            attendre(lambda: recu)
            self.assertEqual(recu, [dl])
        finally:
            ML.chercher, ML.telecharger = anc_ch, anc_tel


if __name__ == "__main__":
    unittest.main()
