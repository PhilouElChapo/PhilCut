"""0.9.62 : dossier des projets « /PhilCut/Projets » absent du cloud (remarque de Philippe). La fenêtre de choix le dit
et propose de le créer ; valider les Préférences crée les dossiers des rôles. Correction : creer_dossiers() n'a pas le
même sens partout (fichier pour WebDAV, dossier pour pCloud / kDrive) : l'envoi d'un projet ne crée plus sur pCloud un
dossier du nom du fichier ; « Nouveau dossier » sur kDrive ne crée plus de dossier « _ »."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
from app import cloud_projets as CP, distant


def compte_reseau():
    c = distant.nouveau_compte("reseau")
    c["adresse"] = tempfile.mkdtemp(prefix="cloud-")
    return c


class TestSens(unittest.TestCase):
    def test_pcloud_pas_de_dossier_du_nom_du_fichier(self):
        c = distant.nouveau_compte("pcloud")                                # pCloud en direct (autorisation)
        self.assertIs(distant.CLASSES["pcloud"], distant.PCloud)
        e = distant.emplacement(c, mot_de_passe="x")
        appels = []

        def faux_api(methode, http="GET", donnees=None, entetes=None, brut=False, **params):
            appels.append((methode, params.get("path") or params.get("folderid") or params.get("filename")))
            if donnees is not None and hasattr(donnees, "read"):
                while donnees.read(65536):
                    pass
            return {"metadata": {"name": "x"}, "result": 0}
        e._api = faux_api
        local = os.path.join(tempfile.mkdtemp(), "Sortie.philcut")
        open(local, "w").write("{}")
        CP.envoyer(e, local, "/PhilCut/Projets/Sortie.philcut")
        dossiers = [p for m, p in appels if m.startswith("createfolder")]
        self.assertEqual(dossiers, ["/PhilCut", "/PhilCut/Projets"])
        self.assertFalse([p for p in dossiers if p and p.endswith(".philcut")])
        appels.clear()
        e.creer_dossier("/PhilCut/Projets")
        self.assertEqual([p for m, p in appels if m.startswith("createfolder")], ["/PhilCut", "/PhilCut/Projets"])

    def test_kdrive_nouveau_dossier(self):
        c = distant.nouveau_compte("kdrive")
        e = distant.emplacement(c, mot_de_passe="x")
        crees = []
        e._id = lambda chemin, creer=False, **k: (crees.append(chemin) if creer else None)
        e.nouveau_dossier("/Saison 2")
        self.assertEqual(crees, ["/Saison 2"])
        crees.clear()
        e.creer_dossier("/PhilCut/Projets")
        self.assertEqual(crees, ["/PhilCut/Projets"])

    def test_reseau_creer_dossier(self):
        c = compte_reseau()
        e = distant.emplacement(c)
        e.creer_dossier("/PhilCut/Projets")
        e.creer_dossier("/PhilCut/Projets")                             # déjà là : rien à redire
        self.assertTrue(os.path.isdir(os.path.join(c["adresse"], "PhilCut", "Projets")))


class TestFenetres(unittest.TestCase):
    def test_dossier_absent_annonce_et_cree(self):
        from app.fenetre import Fenetre
        from app.dialogues_distant import DialogueParcourir
        f = Fenetre([])
        c = compte_reseau()
        os.makedirs(os.path.join(c["adresse"], "PhilCut", "Test"))
        f.params["comptes"] = [c]
        d = DialogueParcourir(f, f.params, "dossier", compte_id=c["id"], dossier="/PhilCut/Projets")
        self.assertEqual(d.dossier, "/PhilCut")                         # le parent qui existe
        self.assertFalse(d.manquant.isHidden())
        self.assertIn("/PhilCut/Projets", d.manquant.text())
        d.creer_depart()
        self.assertEqual(d.dossier, "/PhilCut/Projets")
        self.assertTrue(d.manquant.isHidden())
        self.assertTrue(os.path.isdir(os.path.join(c["adresse"], "PhilCut", "Projets")))
        d.show()
        app.processEvents()
        ecran = d.screen().availableGeometry()
        self.assertTrue(ecran.contains(d.frameGeometry().topLeft()) and d.frameGeometry().right() <= ecran.right() + 1)
        d.close()

    def test_preferences_preparent_les_dossiers(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        p, r = compte_reseau(), compte_reseau()
        f.params.update(comptes=[p, r], compte_prefere=p["id"], projets_dossier="/PhilCut/Projets", rushs_compte=r["id"],
                        rushs_dossier="/Rushes PhilCut")
        t = f._preparer_dossiers_cloud()
        t0 = time.time()
        while time.time() - t0 < 30 and t.isRunning():
            app.processEvents()
            time.sleep(0.02)
        app.processEvents()
        self.assertTrue(os.path.isdir(os.path.join(p["adresse"], "PhilCut", "Projets")))
        self.assertTrue(os.path.isdir(os.path.join(r["adresse"], "Rushes PhilCut")))
        self.assertIn("✓", f.statusBar().currentMessage())


class TestPhraseSecrete(unittest.TestCase):
    """Remarque de Philippe : « dans PhilPDF il y avait une phrase avec un indice, je ne vois rien ». La phrase secrète, son
    indice et ce qui est partagé se voient et se règlent dans Comptes et synchro."""

    def setUp(self):
        from app import coffre, reglages
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.p = self.f.params
        self.p["drive"] = tempfile.mkdtemp()
        self.p["drive_compte"] = ""
        self.p["clef_claude"] = "sk-ant-essai-0123456789"
        self.p["synchro_secrets"] = False
        coffre.supprimer(reglages.PHRASE)

    def tearDown(self):
        from app import coffre, reglages
        coffre.supprimer(reglages.PHRASE)
        self.p["clef_claude"] = ""
        self.p["synchro_secrets"] = False

    def test_etat_et_changement_de_phrase(self):
        from app import coffre, reglages
        e = reglages.etat_secrets(self.p)
        self.assertFalse(e["phrase_ici"])
        self.p["synchro_secrets"] = True
        coffre.enregistrer(reglages.PHRASE, "phrase numero un")
        reglages.ecrire_indice(self.p, "le carnet bleu")
        reglages.synchro_secrets_auto(self.p)
        e = reglages.etat_secrets(self.p)
        self.assertTrue(e["phrase_ici"] and e["lisible"])
        self.assertEqual(e["indice"], "le carnet bleu")
        self.assertIn("Clef Claude", e["noms"])
        self.assertTrue(e["date"])
        with self.assertRaises(reglages.PhraseRequise):
            reglages.changer_phrase(self.p, "pas la bonne", "phrase numero deux")
        reglages.changer_phrase(self.p, "phrase numero un", "phrase numero deux", "titre + année")
        self.assertEqual(coffre.lire(reglages.PHRASE), "phrase numero deux")
        self.assertEqual(reglages.lire_secrets_drive(self.p, "phrase numero deux").get("clef_claude"), "sk-ant-essai-0123456789")
        with self.assertRaises(reglages.PhraseRequise):
            reglages.lire_secrets_drive(self.p, "phrase numero un")
        self.assertEqual(reglages.lire_indice(self.p), "titre + année")

    def test_preferences_montrent_et_demandent(self):
        from app import coffre, reglages, dialogues_phrase as DPH
        from app.preferences import DialoguePreferences
        d = DialoguePreferences(self.f, self.p, "Comptes et synchro")
        self.assertIn("Pas encore de phrase secrète", d.etat_secrets.text())
        self.assertFalse(d.b_changer_phrase.isEnabled())
        appels = []
        anc = DPH.demander_phrase
        DPH.demander_phrase = lambda parent, params, nouvelle=True: (appels.append(nouvelle), False)[1]     # annulé
        try:
            d.synchro_secrets.setChecked(True)                      # cocher demande la phrase tout de suite
            self.assertEqual(appels, [True])
            self.assertFalse(d.synchro_secrets.isChecked())          # annulé : décoché
            DPH.demander_phrase = lambda parent, params, nouvelle=True: (coffre.enregistrer(reglages.PHRASE, "phrase essai"),
                                                                         reglages.ecrire_indice(params, "indice essai"),
                                                                         reglages.synchro_secrets_auto(params), True)[3]
            d.synchro_secrets.setChecked(True)
            self.assertTrue(d.synchro_secrets.isChecked())
        finally:
            DPH.demander_phrase = anc
        self.assertIn("✓", d.etat_secrets.text())
        self.assertIn("indice essai", d.etat_secrets.text())
        self.assertIn("Clef Claude", d.etat_secrets.text())
        self.assertTrue(d.b_changer_phrase.isEnabled())
        from verif_tronques import tronques
        d.resize(1000, 700)
        d.show()
        app.processEvents()
        self.assertFalse([x for x in tronques(d) if "phrase" in str(x).lower()])
        d.close()


if __name__ == "__main__":
    unittest.main()
