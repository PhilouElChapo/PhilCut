"""0.9.59 : modèle « Continuer avec ma voix » absent de la liste. Le catalogue des modèles n'était relu qu'une fois par
jour : une nouvelle version de PhilCut le relit tout de suite, et un modèle inconnu le fait relire une fois. Le bouton
« Installer le modèle » des fenêtres lance le téléchargement (file de PhilCut) au lieu d'ouvrir seulement les Préférences."""
import json, os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
from app import packs_ia as P


class TestCatalogue(unittest.TestCase):
    def test_copie_perimee_apres_mise_a_jour(self):
        from app.config import VERSION
        copie = os.path.join(os.environ["APPDATA"], "cat_essai.json")
        with open(copie, "w") as f:
            f.write("{}")
        self.assertTrue(P._perime(copie))                    # jamais lue par cette version
        P._noter_version(copie)
        self.assertFalse(P._perime(copie))
        with open(copie + ".version", "w") as f:
            f.write("0.9.57")
        self.assertTrue(P._perime(copie))                    # lue par l'ancienne version : relue
        P._noter_version(copie)
        os.utime(copie, (time.time() - 90000, time.time() - 90000))
        self.assertTrue(P._perime(copie))                    # plus d'un jour

    def test_modele_inconnu_relit_une_fois(self):
        appels = []
        anc_m, anc_man = P.modeles, P.manifeste
        cat = {}
        P.modeles = lambda genre=None, avec_essai=False: dict(cat)
        P.manifeste = lambda rafraichir=False, delai=8: (appels.append(rafraichir), cat.update(voix_clone={"genre": "voix_clone"}))
        P._RELUS.clear()
        try:
            self.assertTrue(P.modele_connu("voix_clone"))
            self.assertEqual(appels, [True])
            cat.clear()
            P.manifeste = lambda rafraichir=False, delai=8: appels.append(rafraichir)
            self.assertFalse(P.modele_connu("inexistant"))
            self.assertFalse(P.modele_connu("inexistant"))     # pas de relecture à chaque appel
            self.assertEqual(appels, [True, True])
        finally:
            P.modeles, P.manifeste = anc_m, anc_man
            P._RELUS.clear()


class TestBouton(unittest.TestCase):
    def test_installer_depuis_la_fenetre(self):
        from app.fenetre import Fenetre
        from app import voix_clone as V
        from app.dialogues_voix_suite import DialogueVoixSuite
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        anc_c, anc_a = P.modele_connu, f.telechargements.ajouter
        file = []
        P.modele_connu = lambda cle: True
        f.telechargements.ajouter = lambda cles: file.extend(cles)
        anc_e = f.telechargements.en_file
        f.telechargements.en_file = lambda cle: cle in file
        try:
            d = DialogueVoixSuite(ed)
            self.assertTrue(d.b_installer.isVisibleTo(d))
            d._installer()
            self.assertEqual(file, [V.CLE])
            self.assertFalse(d.b_installer.isEnabled())
            self.assertIn("barre du bas", d.manque.text())
            d.close()
        finally:
            P.modele_connu, f.telechargements.ajouter, f.telechargements.en_file = anc_c, anc_a, anc_e
            ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
