"""0.9.85 : catalogue unique des IA (cloud : adresse, prix, état, remplaçant) et « Mises à jour des IA » locales (moteurs,
modèles) avec essai et retour arrière."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
import test_packs_ia as TP        # noqa: E402  (même faux catalogue, mêmes faux moteurs)
_sha = TP._sha


class TestMajIA(TP.TestPacksIA):
    test_installer_utiliser_supprimer = test_carte_graphique = test_empreinte_et_reprise = None    # déjà dans test_packs_ia
    test_archive_suspecte_refusee = test_poste_leger = None

    def _catalogue(self, changer):
        man = json.load(open(self.man))
        changer(man)
        json.dump(man, open(self.man, "w"))
        self.P._manifeste = None

    def _nouveau_fichier(self, man, cle, nom, contenu):
        p = os.path.join(self.tmp, "src", "v2_" + nom)
        open(p, "wb").write(contenu)
        for f in man["modeles"][cle]["fichiers"]:
            if f["nom"] == nom:
                f.update(url="file://" + p, taille=len(contenu), sha256=_sha(contenu))

    def test_mises_a_jour_essai_retour(self):
        from app import maj_ia as MI
        P = self.P
        P.installer("vision_leger")
        self.assertEqual(MI.a_mettre_a_jour(), [])
        self.assertTrue(P.etat()["vision_leger"]["empreintes"]["m.gguf"])
        self._catalogue(lambda man: (self._nouveau_fichier(man, "vision_leger", "m.gguf", b"poids neufs" * 90),
                                     man["moteurs"]["vision"].update(version="essai2")))
        majs = MI.a_mettre_a_jour()
        self.assertEqual(sorted((m["type"], m["cle"]) for m in majs), [("modele", "vision_leger"), ("moteur", "vision")])
        anc = MI.essayer
        try:
            MI.essayer = lambda maj, params=None, progression=None, arret=None: (True, "")
            for m in majs:
                MI.appliquer(m, {})
            self.assertEqual(MI.a_mettre_a_jour(), [])
            chemin = os.path.join(P.dossier_modele("vision_leger"), "m.gguf")
            self.assertEqual(open(chemin, "rb").read(), b"poids neufs" * 90)
            self.assertTrue(os.path.exists(P.executable("vision")))
            self.assertEqual(len(MI.gardes()), 2)
            self.assertTrue(MI.revenir("vision_leger", "modele"))          # retour arrière
            self.assertEqual(open(chemin, "rb").read(), b"poids" * 100)
            self.assertTrue(P.installe("vision_leger"))
            self.assertEqual([m["cle"] for m in MI.a_mettre_a_jour() if m["type"] == "modele"], ["vision_leger"])
            MI.liberer()
            self.assertEqual(MI.gardes(), [])
            # essai raté : l'ancienne version revient toute seule
            MI.essayer = lambda maj, params=None, progression=None, arret=None: (False, "faux échec")
            m = next(x for x in MI.a_mettre_a_jour() if x["type"] == "modele")
            with self.assertRaises(P.ErreurIA):
                MI.appliquer(m, {})
            self.assertEqual(open(chemin, "rb").read(), b"poids" * 100)
            self.assertTrue(P.installe("vision_leger"))
        finally:
            MI.essayer = anc

    def test_remplacement(self):
        from app import maj_ia as MI
        P = self.P
        P.installer("whisper_leger")

        def changer(man):
            src = os.path.join(self.tmp, "src", "neuf.bin")
            open(src, "wb").write(b"neuf" * 30)
            man["modeles"]["whisper_neuf"] = {"genre": "whisper", "nom": "Whisper neuf", "taille": 120, "fichiers": [
                {"nom": "neuf.bin", "role": "modele", "url": "file://" + src, "taille": 120, "sha256": _sha(b"neuf" * 30)}]}
            man["modeles"]["whisper_leger"].update(etat="retire", remplace_par="whisper_neuf")
        self._catalogue(changer)
        majs = MI.a_mettre_a_jour()
        self.assertEqual([(m["type"], m["remplace_par"]) for m in majs], [("remplacement", "whisper_neuf")])
        params = {}
        anc = MI.essayer
        try:
            MI.essayer = lambda maj, params=None, progression=None, arret=None: (True, "")
            MI.appliquer(majs[0], params)
        finally:
            MI.essayer = anc
        self.assertTrue(P.installe("whisper_neuf") and P.installe("whisper_leger"))   # l'ancien reste
        self.assertEqual(params["ia_locale_modeles"]["whisper"], "whisper_neuf")
        self.assertEqual(MI.a_mettre_a_jour(), [])

    def test_fenetre(self):
        from app.dialogues_maj_ia import DialogueMajIA
        self.P.installer("vision_leger")
        self._catalogue(lambda man: man["moteurs"]["vision"].update(version="essai3"))
        d = DialogueMajIA(None, {})
        self.assertEqual(d.table.rowCount(), 1)
        self.assertEqual(len(d.choisies()), 1)
        self.assertGreater(d.table_cloud.rowCount(), 5)
        self.assertLessEqual(d.minimumSizeHint().width(), 1024)
        d.close()


class TestCatalogueCloud(unittest.TestCase):
    def setUp(self):
        self.f = os.path.join(tempfile.mkdtemp(), "ia.json")
        os.environ["PHILCUT_IA_CATALOGUE"] = self.f

    def tearDown(self):
        os.environ.pop("PHILCUT_IA_CATALOGUE", None)
        from app import catalogue_ia as CI
        CI.recharger()

    def _ecrire(self, services):
        from app import catalogue_ia as CI
        json.dump({"format": 1, "services": services}, open(self.f, "w"))
        CI.recharger()
        CI.annonces()

    def test_defauts_prix_et_remplacement(self):
        from app import catalogue_ia as CI, detourage_cloud as DC, suivi_cloud as SC, levres as LV, voix_transfo as VT
        self._ecrire({})
        self.assertEqual(CI.point("detourage_video"), DC.POINT)
        self.assertEqual(DC.prix(10), 0.5)
        self.assertEqual(LV.prix("latentsync", 60), 0.30)
        self._ecrire({"detourage_video": {"prix": {"s": 0.07}}, "levres_latentsync": {"prix": {"fixe": 0.25}},
                      "voix_transfo": {"etat": "retire", "remplace_par": "fal-ai/autre/voice-changer"},
                      "suivi_video": {"etat": "retire", "remplace_par": "detourage_video"}})
        self.assertEqual(DC.prix(10), 0.7)
        self.assertEqual(LV.prix("latentsync", 30), 0.25)
        self.assertEqual(LV.moteur_ia("latentsync")["modele"], "fal-ai/latentsync")
        self.assertEqual(CI.point("voix_transfo"), "fal-ai/autre/voice-changer")
        self.assertEqual(CI.point("suivi_video"), DC.POINT)
        self.assertEqual(len(CI.annonces()), 2)
        self.assertEqual(CI.annonces(), [])                     # dites une seule fois
        self.assertGreater(VT.prix_cloud(60), 0)
        self.assertGreater(SC.prix(2), 0)
        self.assertEqual(CI.etat_texte(CI.service("voix_transfo")["etat"]), "retiré")
        noms = [s["nom"] for s in CI.liste()]
        self.assertEqual(noms, sorted(noms, key=str.lower))

    def test_veille_prix(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outils_dev"))
        import veille_ia as V
        page = "# x\n## Pricing\nYour request will cost **$0.05** per second.\nH100 is $4.50/h\n## Autre\n$9 per second"
        self.assertEqual(dict((c, m.findall(V.section_prix(page))) for c, m in V.PRIX)["s"], ["0.05"])
        self.assertEqual(V.PRIX[1][1].findall("cost **$0.005** per 16 frames of video input"), ["0.005"])


if __name__ == "__main__":
    unittest.main()
