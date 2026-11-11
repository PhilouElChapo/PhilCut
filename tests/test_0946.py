"""0.9.46 : menus Montage et Fabrique IA rangés (ordre alphabétique, un seul menu Fabrique IA, aussi au clic droit) ;
IA locale partagée entre les logiciels PhilFactory (dossier commun, transfert, reprise sans retéléchargement, rien
d'effacé sous les pieds d'un autre logiciel)."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F, alpha
_F.bienvenue = lambda self, *a, **k: None


class TestMenus(unittest.TestCase):
    def test_ordre_alphabetique(self):
        f = _F([])
        mb = f.menuBar()
        for nom in ("Montage", "Fabrique IA"):
            m = [a.menu() for a in mb.actions() if a.menu() and a.text().replace("&", "") == nom][0]
            titres = [a.text() for a in m.actions() if a.menu()]
            self.assertEqual(titres, sorted(titres, key=alpha), nom)
            for a in m.actions():
                if a.menu():
                    libs = [x.text() for x in a.menu().actions() if x.text() and not x.menu()]
                    self.assertEqual(libs, sorted(libs, key=alpha), a.text())
        montage = [a.menu() for a in mb.actions() if a.menu() and a.text().replace("&", "") == "Montage"][0]
        self.assertEqual(len([a for a in montage.actions() if a.menu()]), 5)
        tout = " ".join(x.text() for a in montage.actions() if a.menu() for x in a.menu().actions())
        self.assertNotIn("Atelier IA", tout)
        self.assertNotIn("Monter par le texte", tout)
        for ed in f.editeurs():
            ed.projet.modifie = False

    def test_clic_droit_meme_menu(self):
        from PySide6.QtWidgets import QMenu
        f = _F([])
        ed = f._editeur_ou_nouveau()
        m = f.remplir_fabrique(QMenu(), ed)
        self.assertEqual([a.text() for a in m.actions() if a.menu()], ["Image", "Logo, intro et vignette", "Musique", "Vidéo"])
        ed.projet.modifie = False


class TestIAPartagee(unittest.TestCase):
    def setUp(self):
        from app import packs_ia as P
        self.P = P
        self.racine = tempfile.mkdtemp()
        os.environ["PHILCUT_IA_DOSSIER"] = os.path.join(self.racine, "philcut_ia")
        P.regler_commun(None)

    def tearDown(self):
        self.P.regler_commun(None)
        os.environ.pop("PHILCUT_IA_DOSSIER", None)

    def test_transfert_et_partage(self):
        from app import ia_partagee as IP
        P = self.P
        propre = P.dossier_modeles_propre()
        os.makedirs(os.path.join(propre, "musique_rapide"))
        with open(os.path.join(propre, "musique_rapide", "vae.gguf"), "wb") as f:
            f.write(b"v" * 1000)
        commun = os.path.join(self.racine, "IA PhilFactory")
        # un autre logiciel a déjà le même fichier : pas recopié, le double est libéré
        os.makedirs(os.path.join(commun, "modeles", "musique_rapide"))
        with open(os.path.join(commun, "modeles", "musique_rapide", "vae.gguf"), "wb") as f:
            f.write(b"v" * 1000)
        IP.noter(commun, "musique_rapide", "PhilMusic")
        n, doubles = IP.transferer(propre, commun, "PhilCut")
        self.assertEqual((n, doubles), (1, 1000))
        self.assertFalse(os.path.exists(os.path.join(propre, "musique_rapide")))
        self.assertEqual(IP.autres_utilisateurs(commun, "musique_rapide", "PhilCut"), ["PhilMusic"])
        P.regler_commun(commun)
        self.assertEqual(P.dossier_modele("x"), os.path.join(commun, "modeles", "x"))
        # supprimer côté PhilCut ne retire pas le fichier encore utilisé par PhilMusic
        P._noter("musique_rapide", {"genre": "musique", "fichiers": ["vae.gguf"]})
        P.supprimer("musique_rapide")
        self.assertTrue(os.path.exists(os.path.join(commun, "modeles", "musique_rapide", "vae.gguf")))

    def test_reprise_sans_retelecharger(self):
        from app import ia_partagee as IP
        P = self.P
        # PhilPic portable rangé à côté : son modèle est trouvé (même taille, même empreinte)
        voisin = os.path.join(self.racine, "PhilPic", "donnees", "ia", "modeles", "image_rapide")
        os.makedirs(voisin)
        with open(os.path.join(voisin, "sd.gguf"), "wb") as f:
            f.write(b"s" * 4096)
        sha = IP.empreinte(os.path.join(voisin, "sd.gguf"))
        racines = IP.racines_modeles(os.path.join(self.racine, "PhilCut"), None)
        self.assertEqual(IP.chercher_fichier("sd.gguf", 4096, sha, racines), os.path.join(voisin, "sd.gguf"))
        self.assertIsNone(IP.chercher_fichier("sd.gguf", 4096, "0" * 64, racines))          # autre version : non reprise
        cible = os.path.join(self.racine, "commun", "modeles", "image_rapide", "sd.gguf")
        IP.placer(os.path.join(voisin, "sd.gguf"), cible)
        self.assertEqual(os.path.getsize(cible), 4096)

    def test_rendez_vous(self):
        from app import ia_partagee as IP
        commun = os.path.join(self.racine, "IA PhilFactory")
        IP.preparer(commun, "PhilPic")
        IP.annoncer(commun, "PhilPic", "1.0")
        self.assertEqual(IP.lire_rdv()["dossier"], commun)
        self.assertIn(commun, IP.communs_connus(""))
        IP.retirer_rdv("PhilPic")
        self.assertNotIn("PhilPic", IP.lire_rdv().get("logiciels", {}))


if __name__ == "__main__":
    unittest.main()
