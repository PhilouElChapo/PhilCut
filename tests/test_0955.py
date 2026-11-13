"""0.9.55 : guides livrés par le catalogue en ligne (comme les Goodies), barre de lecture qui passe à la ligne
(fenêtre utilisable dès 1024 de large), explication du choix du moteur dans la Séquence IA. Les garde-fous sont dans
test_garde_fous.py."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


class TestGuidesCatalogue(unittest.TestCase):
    def test_livre_et_fusion(self):
        from app import guides as G
        ids = {g["id"]: g for g in G.guides()}
        self.assertIn("rushes_pcloud", ids)                      # livré avec PhilCut (copie du catalogue)
        self.assertTrue(ids["rushes_pcloud"]["catalogue"])
        self.assertIn("suivi", ids)                              # les guides intégrés restent

    def test_remplace_filtre_et_tolere(self):
        from app import guides as G, catalogue_ligne as CL
        anc = CL.charger
        CL.charger = lambda nom, reseau=False, delai=8: {"guides": [
            {"id": "suivi", "titre": {"fr": "Suivre (corrigé en ligne)"}, "intro": "x", "etapes": [{"texte": "a"}]},
            {"id": "futur", "philcut_min": "9.0.0", "titre": "Plus tard", "intro": "", "etapes": [{"texte": "b"}]},
            {"id": "casse", "titre": "Sans étapes"},
            "pas un guide"]}
        try:
            ids = {g["id"]: g for g in G.guides()}
        finally:
            CL.charger = anc
        self.assertEqual(ids["suivi"]["titre"], "Suivre (corrigé en ligne)")    # corrigé sans nouvelle version
        self.assertNotIn("futur", ids)                                         # demande une version plus récente
        self.assertNotIn("casse", ids)

    def test_nouveau_puis_vu(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        f.params["guides_vus"] = []
        d = f.guides()
        from app.dialogues_guide import CaseGuide
        textes = [c.libelle.text() for c in d.zone.widget().findChildren(CaseGuide)]
        self.assertTrue(any("Nouveau" in t for t in textes))
        d.ouvrir("rushes_pcloud")
        self.assertIn("rushes_pcloud", f.params["guides_vus"])
        d.close()
        for ed in f.editeurs():
            ed.projet.modifie = False


class TestInterface(unittest.TestCase):
    def test_fenetre_1024(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        f._editeur_ou_nouveau()
        f.show()
        app.processEvents()
        self.assertLessEqual(f.minimumSizeHint().width(), 1024)
        for ed in f.editeurs():
            ed.projet.modifie = False

    def test_explication_moteur(self):
        from app.fenetre import Fenetre
        from app.dialogues_sequence import DialogueSequence
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        d = DialogueSequence(ed, None)
        d.moteur.setCurrentIndex(d.moteur.findData("locale"))
        d._maj_moteur()
        self.assertIn("visage dérive", d.explication_moteur.text())
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
