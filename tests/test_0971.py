"""0.9.71 : journal des plantages de Philippe (14/11). « access violation » notée à tort à « Installer et redémarrer »
(sortie voulue pendant une synchro) ; « Windows fatal exception 0x80040155 » notée à tort pendant la fenêtre de fichiers
de Windows (exception COM rattrapée par Windows lui-même) ; réseau lent annoncé comme « autorisation expirée »."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestJournal(unittest.TestCase):
    def test_sortie_voulue_et_fenetres_de_fichiers(self):
        import faulthandler
        from app import journal
        anc = journal._fichier_plantage
        journal._fichier_plantage = open(tempfile.mktemp(), "w", encoding="utf-8")
        try:
            faulthandler.enable(file=journal._fichier_plantage, all_threads=True)
            with journal._SansSurveillance():
                self.assertFalse(faulthandler.is_enabled())       # pendant la fenêtre de fichiers de Windows
            self.assertTrue(faulthandler.is_enabled())
            journal.fin_normale()
            self.assertFalse(faulthandler.is_enabled())           # sortie voulue : plus de faux plantage
        finally:
            journal._fichier_plantage = anc
        plat = sys.platform
        sys.platform = "win32"
        try:
            journal._calmer_dialogues_windows()
        finally:
            sys.platform = plat
        from PySide6.QtWidgets import QFileDialog
        self.assertTrue(getattr(QFileDialog.getOpenFileName, "_philcut", False))

    def test_reseau_lent_n_est_pas_une_autorisation_expiree(self):
        from app import distant, oauth, coffre
        c = distant.nouveau_compte("gdrive")
        c["id"] = "essai_lent"
        anc_r, anc_l = oauth.rafraichir, coffre.lire

        def lent(*a, **k):
            e = oauth.ErreurAutorisation("Serveur injoignable : The read operation timed out")
            e.reseau = True
            raise e
        oauth.rafraichir, coffre.lire = lent, lambda *a, **k: "jeton-durable"
        try:
            d = distant.GoogleDrive(c)
            with self.assertRaises(distant.ErreurDistant) as ctx:
                d._acces()
        finally:
            oauth.rafraichir, coffre.lire = anc_r, anc_l
        self.assertIn("réessaiera seule", str(ctx.exception))
        self.assertNotIn("autorisez à nouveau", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
