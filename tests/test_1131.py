"""1.2.1 : variantes propres à chaque voix du catalogue ; « Mon groupe… » dans la Fabrique musique (style et voix du groupe,
repris par le clip de groupe) ; « Reprendre une création en cours » (Fabrique musique, assistant musique, clip de groupe,
motion design IA), gardé à chaque changement."""
import os, sys, tempfile, unittest, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import voix_familles as VF, en_cours as EC


def vider(params):
    from app import bibliotheque_creations as B
    for g in ("voix", "groupe", "musicien", "style_musical"):
        shutil.rmtree(os.path.join(B.dossier(params), g), ignore_errors=True)
    shutil.rmtree(EC.dossier(), ignore_errors=True)


class TestCatalogue(unittest.TestCase):
    def test_variantes_propres(self):
        from app.langue import _
        cat = {x["nom"]: x for x in VF.catalogue()}
        self.assertIn(_("Crooner"), [v["nom"] for v in cat["sinatra"]["variantes"]])
        self.assertIn("swing", [v["id"] for v in cat["sinatra"]["variantes"]])
        self.assertTrue(all(len(x["variantes"]) >= 3 for x in cat.values()))
        rap = next(x for x in cat.values() if x["genre"] == "rap")
        self.assertIn("flow_rapide", [v["id"] for v in rap["variantes"]] + ["flow_rapide"] * ("rapid" in rap["en"]))
        # une voix déjà rauque n'a pas de variante « rauque »
        for x in cat.values():
            if "raspy" in x["en"].lower():
                self.assertNotIn("rauque", [v["id"] for v in x["variantes"]], x["nom"])
        import json
        sty = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue", "styles.json"),
                             encoding="utf-8"))["styles"]
        self.assertTrue(all(e.get("variantes") for e in sty if e.get("voix")))       # écrites dans le catalogue en ligne
        for e in sty:
            for v in e.get("variantes") or []:
                self.assertEqual(set(v["noms"]), {"fr", "en", "de", "es", "it"})


class TestGroupeEtReprise(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre()
        self.f.bienvenue = lambda *a, **k: None
        self.ed = self.f.nouveau_projet("16:9")
        vider(self.ed.params)

    def test_groupe_fabrique(self):
        from app import bibliotheque_creations as B
        from app.dialogues_musique_ia import DialogueFabriqueMusique
        v = VF.garder_principal(self.ed.params, "Archangel", VF.NEUTRES)
        v = VF.ajouter_variante(self.ed.params, v, "Chaude (solo)", VF.appliquer(VF.NEUTRES, {"chaleur": 30}), ["chaude"])
        st = B.garder(self.ed.params, "style_musical", "Rock mélodique", "rock mélodique", None,
                      {"inspiration": {"resume": "rock, 140 bpm", "caption_en": "melodic rock", "bpm": 140}})
        g = B.garder_groupe(self.ed.params, "Archangel", [{"role": "chant", "nom": "Chanteuse"}], None, "rock mélodique",
                            {"nom": "Archangel › Chaude", "entree": v["id"], "variante": VF.variantes(v)[0]["id"]})
        B.garder(self.ed.params, "groupe", g["nom"], g["description"], None, {"style_biblio": st["id"]}, g["id"])
        dl = DialogueFabriqueMusique(self.ed, self.ed.params)
        dl._test_biblio = "Archangel"
        dl.choisir_groupe()
        self.assertEqual(dl.inspiration["bpm"], 140)
        self.assertIn("warm", dl.voix_decrite["en"])
        dl.clip_lieu.setCurrentIndex(1)
        f = dl.fiche()
        self.assertEqual((f["groupe"]["id"], f["clip"]["groupe"]), (g["id"], g["id"]))
        dl._sans_voix_decrite()                                  # tout reste modifiable
        self.assertIsNone(dl.voix_decrite)

    def test_suivi(self):
        from PySide6.QtWidgets import QWidget
        w = QWidget()
        etat = {"a": 1}
        s = EC.Suivi(w, "fabrique_musique", lambda: etat, lambda: "Essai")
        p = s.maintenant()
        self.assertTrue(p and os.path.exists(p))
        self.assertIsNone(s.maintenant())                        # rien n'a changé : rien n'est réécrit
        etat["a"] = 2
        self.assertTrue(s.maintenant())
        self.assertEqual(EC.lire("fabrique_musique", s.ident)["etat"], {"a": 2})
        self.assertEqual([x["id"] for x in EC.lister()], [s.ident])
        s.oublier()
        self.assertEqual(EC.lister(), [])

    def test_reprendre_fabrique(self):
        d = self.ed.fabrique_musique()
        d.phrase.setPlainText("une valse lente au piano")
        d._suivi_en_cours.maintenant()
        d.hide()
        self.ed._fab_musique = None
        liste = EC.lister()
        self.assertEqual(liste[0]["genre"], "fabrique_musique")
        d2 = self.ed.reprendre_en_cours(0)
        self.assertIn("valse lente", d2.phrase.toPlainText())
        self.assertEqual(d2._suivi_en_cours.ident, liste[0]["id"])      # la même entrée continue
        d2.hide()

    def test_reprendre_motion_et_assistant(self):
        d = self.ed.animation_libre()
        d.description.setPlainText("un cadeau qui grandit")
        d._suivi_en_cours.maintenant()
        d.hide()
        self.ed._fenetres_non_bloquantes = {} if hasattr(self.ed, "_fenetres_non_bloquantes") else None
        x = next(i for i, e in enumerate(EC.lister()) if e["genre"] == "motion_ia")
        from app import editeur
        d2 = self.ed.reprendre_en_cours(x)
        self.assertEqual(d2.description.toPlainText(), "un cadeau qui grandit")
        d2.hide()
        from app import assistant_idee as I
        a = self.ed.assistant_creation(musique=True)
        a.genre = "musique"
        a.musique = I.analyse_musique_simple("une ballade rock de 3 minutes")
        if a.musique is None:
            self.skipTest("pas d'analyse simple")
        a._suivi_en_cours.maintenant()
        a.hide()
        k = next(i for i, e in enumerate(EC.lister()) if e["genre"] == "assistant_musique")
        e = EC.lister()[k]["etat"]
        a2 = self.ed.assistant_creation(musique=True)
        a2.reprendre_musique(e)
        self.assertEqual(a2.genre, "musique")
        self.assertEqual(len(a2.musique["elements"]), len(e["musique"]["elements"]))
        a2.hide()


if __name__ == "__main__":
    unittest.main()
