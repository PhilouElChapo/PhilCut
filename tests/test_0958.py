"""0.9.58 : comptes à rôles distincts (comme PhilPDF). Réglages / projets / rushes ; ouvrir et enregistrer un projet
sur un compte (copie de travail, renvoi à chaque Enregistrer, conflit avec un autre poste détecté) ; rushes absents
téléchargés au choix en copie légère ou en original ; import de rushes ; envoi d'une vidéo ; récents du cloud
(Accueil, session des autres postes) ; « Nouveau dossier » ; le compte des rushes n'est plus reçu d'office.
Le « cloud » des tests est un dossier réseau (même chemin de code que pCloud, Drive, NAS pour PhilCut)."""
import json, os, posixpath, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
from app import cloud_projets as CP, distant
from PySide6.QtWidgets import QDialog


def compte_reseau(nom="Cloud d'essai"):
    c = distant.nouveau_compte("reseau")
    c["adresse"] = tempfile.mkdtemp(prefix="cloud-")
    c["nom"] = nom
    return c


def attendre(cond, s=60):
    t0 = time.time()
    while time.time() - t0 < s and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestComptes(unittest.TestCase):
    def test_prefere_et_nouveau_dossier(self):
        a, b = compte_reseau("A"), compte_reseau("B")
        params = {"comptes": [a, b], "compte_prefere": b["id"]}
        self.assertEqual([c["id"] for c in distant.comptes_ordonnes(params)], [b["id"], a["id"]])
        self.assertIs(CP.compte_projets(params), b)
        params["compte_prefere"] = "disparu"
        self.assertIsNone(CP.compte_projets(params))
        e = distant.emplacement(a)
        e.nouveau_dossier("/Projets/2026")
        self.assertTrue(os.path.isdir(os.path.join(a["adresse"], "Projets", "2026")))
        with self.assertRaises(distant.ErreurDistant):
            e.nouveau_dossier("/Projets/2026")
        self.assertEqual(CP.dossier_projets({}), "/PhilCut/Projets")
        self.assertEqual(CP.dossier_projets({"projets_dossier": "Mes projets/"}), "/Mes projets")


class TestProjets(unittest.TestCase):
    def setUp(self):
        self.c = compte_reseau()
        self.params = {"comptes": [self.c], "compte_prefere": self.c["id"], "recents": []}
        d = os.path.join(self.c["adresse"], "PhilCut", "Projets")
        os.makedirs(d)
        self.distant = os.path.join(d, "Balade.philcut")
        with open(self.distant, "w", encoding="utf-8") as f:
            f.write('{"essai": 1}')

    def test_aller_retour_et_conflit(self):
        local, info = CP.ouvrir_projet(self.params, self.c, "/PhilCut/Projets/Balade.philcut")
        self.assertTrue(local.startswith(CP.dossier_cache()))
        self.assertEqual(open(local, encoding="utf-8").read(), '{"essai": 1}')
        self.assertEqual(CP.origine(self.params, local)["chemin"], "/PhilCut/Projets/Balade.philcut")
        self.assertTrue(info["date"])
        with open(local, "w", encoding="utf-8") as f:
            f.write('{"essai": 2}')
        info = CP.envoyer_projet(self.params, local, info)
        self.assertEqual(open(self.distant, encoding="utf-8").read(), '{"essai": 2}')
        # un autre poste le modifie : notre envoi s'arrête (rien n'est écrasé sans le demander)
        time.sleep(1.1)
        with open(self.distant, "w", encoding="utf-8") as f:
            f.write('{"essai": "autre poste", "plus": "long"}')
        with self.assertRaises(CP.ConflitDistant):
            CP.envoyer_projet(self.params, local, info)
        self.assertIn("autre poste", open(self.distant, encoding="utf-8").read())
        CP.envoyer_projet(self.params, local, info, forcer=True)
        self.assertEqual(open(self.distant, encoding="utf-8").read(), '{"essai": 2}')

    def test_compte_disparu(self):
        local, info = CP.ouvrir_projet(self.params, self.c, "/PhilCut/Projets/Balade.philcut")
        self.params["comptes"] = []
        with self.assertRaises(distant.ErreurDistant):
            CP.envoyer_projet(self.params, local, info)

    def test_meme_compte_sur_un_autre_poste(self):
        autre = dict(self.c, id="autre-id")                # même type, même adresse : même compte
        self.assertIs(CP.compte_par_cle({"comptes": [autre]}, distant.cle_compte(self.c)), autre)


class TestRushes(unittest.TestCase):
    def setUp(self):
        from app import moteur
        self.sync, self.r = compte_reseau("Synchro"), compte_reseau("Rushes")
        self.params = {"comptes": [self.sync, self.r], "drive_compte": self.sync["id"], "rushs_compte": self.r["id"],
                       "rushs_dossier": "/Rushes PhilCut", "machine": "poste-essai"}
        self.video = commun.video_test(os.environ["APPDATA"], "rush_cloud.mp4", duree=2)
        self.fiche = moteur.sonder(self.video)

    def _projet(self):
        from app.projet import Projet
        p = Projet("essai")
        m = p.ajouter_media(self.video, self.fiche)
        return p, m

    def test_original_puis_choix_sur_un_autre_poste(self):
        p, m = self._projet()
        self.assertEqual(CP.a_envoyer_original(p), [m])
        nom = CP.envoyer_original(self.params, m)
        self.assertTrue(os.path.exists(os.path.join(self.r["adresse"], "Rushes PhilCut", "Originaux", nom)))
        self.assertEqual(CP.a_envoyer_original(p), [])
        # une copie légère déposée aussi (à la main ici)
        m["copie_drive"] = "abc_720p.mp4"
        dl = os.path.join(self.r["adresse"], "Rushes PhilCut", "Medias")
        os.makedirs(dl)
        with open(os.path.join(dl, "abc_720p.mp4"), "wb") as f:
            f.write(b"x" * 1000)
        dispo = CP.dispo_rushs(self.params)
        self.assertEqual(dict(CP.choix_possibles(m, dispo)), {"leger": 1000, "original": os.path.getsize(self.video)})
        # sur l'autre poste : le rush est absent ; l'original est choisi
        m["chemin"] = "/introuvable/rush_cloud.mp4"
        local = CP.telecharger_rush(self.params, p, m, "original")
        self.assertTrue(os.path.exists(local))
        self.assertEqual(m["chemin"], local)
        self.assertFalse(m.get("copie_legere"))
        # ou la copie légère : l'original reste noté
        m["chemin"] = "/introuvable/rush_cloud.mp4"
        m.pop("original", None)
        local2 = CP.telecharger_rush(self.params, p, m, "leger")
        self.assertTrue(m["copie_legere"])
        self.assertEqual(m["original"], "/introuvable/rush_cloud.mp4")
        self.assertEqual(os.path.getsize(local2), 1000)

    def test_originaux_hors_du_dossier_synchronise(self):
        """Compte des rushes = lieu de synchronisation : les originaux ne vont pas dans /PhilCut (reçu d'office partout)."""
        self.params["rushs_compte"] = self.sync["id"]
        self.assertEqual(CP.dossier_originaux(self.params), "/PhilCut Originaux")
        self.params["rushs_compte"] = self.r["id"]
        self.assertEqual(CP.dossier_originaux(self.params), "/Rushes PhilCut/Originaux")

    def test_rushes_plus_recus_d_office(self):
        from app import drive_philcut as DP, miroir
        d = os.path.join(self.r["adresse"], "Rushes PhilCut", "Medias")
        os.makedirs(d)
        with open(os.path.join(d, "lourd_720p.mp4"), "wb") as f:
            f.write(b"z" * 100)
        with open(os.path.join(d, "index.json"), "w", encoding="utf-8") as f:
            json.dump({"lourd_720p.mp4": {"depose": "2026-11-13"}}, f)
        miroir.synchroniser(self.params, DP.compte_rushs(self.params),
                            sens={"envoyer", "recevoir:Medias/index.json", "fusionner:Medias/index.json"})
        self.assertFalse(os.path.exists(os.path.join(DP.dossier_medias(self.params), "lourd_720p.mp4")))
        self.assertTrue(os.path.exists(os.path.join(DP.dossier_medias(self.params), "index.json")))
        self.assertTrue(os.path.exists(os.path.join(d, "lourd_720p.mp4")))          # rien n'est supprimé là-bas

    def test_importer(self):
        d = os.path.join(self.r["adresse"], "Tournage")
        os.makedirs(d)
        for n in ("a.mp4", "b.mp4"):
            with open(os.path.join(d, n), "wb") as f:
                f.write(b"v" * 300)
        dest = tempfile.mkdtemp()
        etapes = []
        out = CP.importer(self.params, self.r, ["/Tournage/a.mp4", "/Tournage/b.mp4"], dest, lambda f, t="": etapes.append(f),
                          tailles={"/Tournage/a.mp4": 300, "/Tournage/b.mp4": 300})
        self.assertEqual([os.path.basename(x) for x in out], ["a.mp4", "b.mp4"])
        self.assertTrue(all(os.path.getsize(x) == 300 for x in out))
        self.assertTrue(etapes and etapes == sorted(etapes))
        self.assertFalse([f for f in os.listdir(dest) if f.endswith(".part")])
        self.assertIn("Rushes", CP.dossier_import(self.params, self.r))


class TestFenetre(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.c = compte_reseau("Cloud d'essai")
        self.f.params["comptes"] = [self.c]
        self.f.params["compte_prefere"] = self.c["id"]
        self.f.params["synchro"] = False

    def tearDown(self):
        for ed in self.f.editeurs():
            ed.projet.modifie = False

    def _faux_parcourir(self, compte, choisi, choisis=None):
        from app import dialogues_distant as DD
        anc = DD.DialogueParcourir.exec

        def faux(d):
            d.comptes.setCurrentIndex(d.comptes.findData(compte["id"]))
            d.choisi, d.choisis = choisi, choisis or [choisi]
            return QDialog.Accepted
        DD.DialogueParcourir.exec = faux
        return lambda: setattr(DD.DialogueParcourir, "exec", anc)

    def test_enregistrer_vers_puis_rouvrir(self):
        ed = self.f.nouveau_projet("16:9", "Sortie")
        self.f._sans_proposition_drive = True
        remettre = self._faux_parcourir(self.c, "/PhilCut/Projets/Sortie.philcut")
        try:
            self.assertTrue(self.f.enregistrer_distant())
        finally:
            remettre()
        fichier = os.path.join(self.c["adresse"], "PhilCut", "Projets", "Sortie.philcut")
        self.assertTrue(attendre(lambda: os.path.exists(fichier)))
        self.assertTrue(ed.projet.distant)
        self.assertTrue(self.f.onglets.tabText(self.f.onglets.indexOf(ed)).startswith("☁"))
        local = ed.projet.chemin
        self.assertEqual(CP.origine(self.f.params, local)["lieu"], "Cloud d'essai")
        # récents : Accueil et menu montrent le cloud ; la session le donne aux autres postes
        self.f.accueil.rafraichir()
        textes = [self.f.accueil.liste.item(i).text() for i in range(self.f.accueil.liste.count())]
        self.assertTrue(any("☁ Cloud d'essai : /PhilCut/Projets" in t for t in textes), textes)
        from app.session import session_de
        s = session_de(self.f.params)
        s.chemin = os.path.join(tempfile.mkdtemp(), "session.json")
        s.ecrire([(local, 0, 1.0, ed.projet.distant)])
        moi = json.load(open(s.chemin, encoding="utf-8"))[self.f.params["machine"]]
        self.assertEqual(moi["recents"][0]["distant"]["chemin"], "/PhilCut/Projets/Sortie.philcut")
        self.assertEqual(moi["fichiers"][0]["distant"]["lieu"], "Cloud d'essai")
        # modifier et enregistrer : renvoyé au cloud
        avant = os.path.getmtime(fichier)
        time.sleep(1.1)
        ed.projet.nom = "Sortie"
        ed.projet.modifie = True
        self.f.enregistrer()
        self.assertTrue(attendre(lambda: os.path.getmtime(fichier) > avant))
        # copie de travail effacée : le récent se rouvre depuis le cloud
        self.f.fermer_onglet(self.f.onglets.indexOf(ed))
        os.remove(local)
        self.f.ouvrir(local)
        self.assertTrue(attendre(lambda: any(e.projet.nom == "Sortie" for e in self.f.editeurs())))
        ed2 = next(e for e in self.f.editeurs() if e.projet.nom == "Sortie")
        self.assertEqual(ed2.projet.distant["chemin"], "/PhilCut/Projets/Sortie.philcut")

    def test_reprendre_depuis_un_autre_poste(self):
        d = os.path.join(self.c["adresse"], "PhilCut", "Projets")
        os.makedirs(d)
        from app.projet import Projet
        Projet("Ailleurs").enregistrer(os.path.join(d, "Ailleurs.philcut"))
        f = {"chemin": "C:/Users/x/AppData/distant/abc/Ailleurs.philcut", "nom": "Ailleurs.philcut",
             "distant": {"cle": distant.cle_compte(self.c), "chemin": "/PhilCut/Projets/Ailleurs.philcut", "lieu": "Cloud d'essai"}}
        self.f._reprendre([f], "autre-poste")
        self.assertTrue(attendre(lambda: any(e.projet.nom == "Ailleurs" for e in self.f.editeurs())))

    def test_importer_et_envoyer(self):
        d = os.path.join(self.c["adresse"], "Tournage")
        os.makedirs(d)
        v = commun.video_test(d, "plage.mp4", duree=2)
        ed = self.f.nouveau_projet("16:9", "Import")
        remettre = self._faux_parcourir(self.c, "/Tournage/plage.mp4")
        from app import session
        anc = session.dossier_systeme
        session.dossier_systeme = lambda genre: tempfile.mkdtemp()
        try:
            self.f.importer_distant()
            self.assertTrue(attendre(lambda: any(m["nom"].startswith("plage") for m in ed.projet.medias)))
        finally:
            remettre()
            session.dossier_systeme = anc
        remettre = self._faux_parcourir(self.c, "/PhilCut/Exports/plage_finale.mp4")
        try:
            self.f.partager(v)
            dest = os.path.join(self.c["adresse"], "PhilCut", "Exports", "plage_finale.mp4")
            self.assertTrue(attendre(lambda: os.path.exists(dest)))
        finally:
            remettre()

    def test_parcourir(self):
        from app.dialogues_distant import DialogueParcourir
        from PySide6.QtWidgets import QInputDialog
        d0 = os.path.join(self.c["adresse"], "PhilCut", "Projets")
        os.makedirs(d0)
        for n in ("a.philcut", "b.mp4", "c.txt"):
            open(os.path.join(d0, n), "w").close()
        d = DialogueParcourir(self.f, self.f.params, "ouvrir", dossier="/PhilCut/Projets", extensions=CP.EXT_PROJET)
        self.assertEqual(d.dossier, "/PhilCut/Projets")
        noms = [d.liste.item(i).text().split("   ")[0] for i in range(d.liste.count())]
        self.assertIn("a.philcut", noms)
        self.assertNotIn("b.mp4", noms)
        self.assertTrue(d.comptes.itemText(0).startswith("★"))
        anc = QInputDialog.getText
        QInputDialog.getText = lambda *a, **k: ("Saison 2", True)
        try:
            d.nouveau_dossier()
        finally:
            QInputDialog.getText = anc
        self.assertEqual(d.dossier, "/PhilCut/Projets/Saison 2")
        self.assertTrue(os.path.isdir(os.path.join(d0, "Saison 2")))
        d2 = DialogueParcourir(self.f, self.f.params, "ouvrir", dossier="/n/existe/pas")       # dossier absent : la racine
        self.assertEqual(d2.dossier, "/")
        d3 = DialogueParcourir(self.f, self.f.params, "ouvrir", dossier="/PhilCut/Projets", extensions=CP.EXT_RUSHES, multiple=True)
        for i in range(d3.liste.count()):
            if d3.liste.item(i).text().startswith("b.mp4"):
                d3.liste.item(i).setSelected(True)
        d3._valider()
        self.assertEqual(d3.choisis, ["/PhilCut/Projets/b.mp4"])

    def test_preferences_roles(self):
        from app.preferences import DialoguePreferences
        r = compte_reseau("Rushes")
        self.f.params["comptes"].append(r)
        d = DialoguePreferences(self.f, self.f.params, "Comptes et synchro")
        self.assertEqual(d.projets_compte.currentData(), self.c["id"])
        self.assertGreaterEqual(d.rushs_compte.findData(r["id"]), 0)
        d.projets_compte.setCurrentIndex(d.projets_compte.findData(r["id"]))
        d.projets_dossier.setText("/Mes projets")
        d.rushs_compte.setCurrentIndex(d.rushs_compte.findData(self.c["id"]))
        d.valider()
        self.assertEqual(self.f.params["compte_prefere"], r["id"])
        self.assertEqual(self.f.params["projets_dossier"], "/Mes projets")
        self.assertEqual(self.f.params["rushs_compte"], self.c["id"])
        from verif_tronques import tronques
        d2 = DialoguePreferences(self.f, self.f.params, "Comptes et synchro")
        d2.resize(1000, 700)
        d2.show()
        app.processEvents()
        self.assertEqual([x for x in tronques(d2) if "Rôle" in str(x) or "Projets" in str(x)], [])
        d2.close()


class TestManquants(unittest.TestCase):
    def test_choix_copie_ou_original(self):
        from app.fenetre import Fenetre
        from app.dialogues_drive import DialogueManquants
        from app import moteur
        f = Fenetre([])
        sync, r = compte_reseau("Synchro"), compte_reseau("Rushes")
        f.params.update(comptes=[sync, r], drive_compte=sync["id"], rushs_compte=r["id"], rushs_dossier="/Rushes PhilCut")
        ed = f.nouveau_projet("16:9", "Manque")
        v = commun.video_test(os.environ["APPDATA"], "manque.mp4", duree=2)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        CP.envoyer_original(f.params, m)
        m["chemin"] = "/introuvable/manque.mp4"
        d = DialogueManquants(ed)
        self.assertTrue(attendre(lambda: d.dispo["original"]))
        self.assertTrue(d.b_original.isEnabled())
        self.assertFalse(d.b_leger.isEnabled())                       # pas de copie légère déposée
        self.assertIn("original", d.arbre.topLevelItem(0).text(2))
        d.telecharger("original")
        self.assertTrue(attendre(lambda: os.path.exists(m["chemin"])))
        d.done(0)
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
