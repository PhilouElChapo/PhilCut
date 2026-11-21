"""1.1.2 : animation libre au choix HyperFrames ou Remotion ; plan de l'IA vérifié contre la durée ; fenêtre gardée (Réduire)."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

ICI = os.path.dirname(os.path.abspath(__file__))
REPONSE_HF = open(os.path.join(ICI, "exemples", "libre_anniversaire.txt"), encoding="utf-8").read()
TSX = open(os.path.join(ICI, "exemples", "libre_anniversaire_remotion.tsx"), encoding="utf-8").read()
REPONSE_R = ("===TITRE===\n40 ans\n===DUREE===\n9.5\n===PLAN===\n0-4 s: le cadeau grandit, compteur et barres\n"
             "4.2-7 s: feu d'artifice\n7-9.5 s: tout part en confettis\n===TSX===\n" + TSX + "\n===MESSAGE===\nVoilà.")


class TestLogique(unittest.TestCase):
    def test_consignes(self):
        from app import motion_libre as ML
        a = ML.fiche("x", (1080, 1920), moteur="remotion")
        c = ML.consigne(a)
        self.assertIn("export const Animation", c)
        self.assertIn("===TSX===", c)
        self.assertIn("===PLAN===", c)
        self.assertIn("1080×1920", c)
        self.assertIn("===PLAN===", ML.consigne(ML.fiche("x")))
        self.assertIn("===JS===", ML.consigne(ML.fiche("x")))

    def test_remotion_lu_et_verifie(self):
        from app import motion_libre as ML
        a = ML.appliquer(ML.fiche("x", moteur="remotion"), ML.sections(REPONSE_R))
        self.assertEqual(ML.code_de(a), "remotion")
        self.assertTrue(ML.a_jour(a))
        self.assertEqual(ML.fautes(a), [])
        self.assertEqual(len(a["libre"]["plan"]), 3)
        self.assertIn("feu d'artifice", ML.plan_texte(a))
        self.assertEqual(a["duree"], 9.5)
        self.assertTrue(ML.verifier_tsx('import _ from "lodash";\nexport const Animation = () => { setTimeout(f); }'))

    def test_plan_qui_depasse(self):
        """Philippe, 21/11 20h13 : feu d'artifice et confettis absents : la fin ne doit jamais être coupée sans le dire."""
        from app import motion_libre as ML
        libre = ML.appliquer(ML.fiche("x"), {"js": "tl.to(a, {x: 1}, 0)", "duree": "6",
                                             "plan": "0-4 s: cadeau\n4-8 s: feu\n8-10 s: confettis"})
        self.assertEqual(libre["duree"], 10)                     # durée au choix de l'IA : jamais plus courte que son plan
        impose = dict(ML.fiche("x", duree=6), duree_imposee=True)
        b = ML.appliquer(impose, {"js": "tl.to(a, {x: 1}, 0)", "duree": "6", "plan": "0-4 s: cadeau\n4-8 s: feu"})
        self.assertTrue(any("feu" in f for f in ML.fautes(b)))
        self.assertEqual(ML.lire_plan("2 à 5,5 s : compteur"), [(2.0, 5.5, "compteur")])

    def test_transposer_et_revenir(self):
        from app import ia, motion_libre as ML
        a = ML.appliquer(ML.fiche("x"), ML.sections(REPONSE_HF))
        a["moteur_libre"] = "remotion"
        self.assertFalse(ML.a_jour(a))
        recu = {}

        def faux(params, consignes, texte, **k):
            recu["c"], recu["t"] = consignes, texte
            return REPONSE_R
        anc = ia.demander
        ia.demander = faux
        try:
            b = ML.corriger({}, a)
        finally:
            ia.demander = anc
        self.assertIn("translate it into a Remotion", recu["t"])
        self.assertIn("===JS===", recu["t"])                     # l'ancien code HyperFrames est montré
        self.assertIn("===TSX===", recu["c"])                    # la réponse attendue est au format Remotion
        self.assertEqual(ML.code_de(b), "remotion")
        c = ML.revenir(b)
        self.assertEqual((ML.code_de(c), c["moteur_libre"]), ("hyperframes", "hyperframes"))

    def test_remotion_fiche_et_projet(self):
        from app import motion_libre as ML, motion_remotion as MR
        a = ML.appliquer(ML.fiche("x", (1080, 1920), moteur="remotion"), ML.sections(REPONSE_R))
        d = MR.projet_libre(a, tempfile.mkdtemp())
        with open(os.path.join(d, "src", "LibreCode.tsx"), encoding="utf-8") as f:
            self.assertIn("feu d'artifice", f.read())
        for x in ("Libre.tsx", "LibreTypes.ts", "Root.tsx", "index.ts", "PhilCut.tsx"):
            self.assertTrue(os.path.exists(os.path.join(d, "src", x)), x)
        A = json.load(open(os.path.join(d, "props.json"), encoding="utf-8"))["A"]
        self.assertEqual((A["W"], A["H"], A["D"], A["fps"]), (1080, 1920, 9.5, 30))
        self.assertEqual(MR.commande("p.json", "s.mp4", a)[4], "Libre")
        self.assertEqual(MR.commande("p.json", "s.mp4", {"genre": "compteur"})[4], "PhilCut")
        with self.assertRaises(MR.ErreurRemotion):
            MR.preparer_libre(ML.fiche("x", moteur="remotion"), tempfile.mkdtemp())

    def test_mise_a_jour_garde_le_code_de_l_ia(self):
        from app import motion_remotion as MR
        d = tempfile.mkdtemp()
        anc = MR.dossier
        MR.dossier = lambda: d
        try:
            os.makedirs(os.path.join(d, "src"))
            with open(os.path.join(d, "src", "LibreCode.tsx"), "w") as f:
                f.write("// code de l'IA")
            MR.mettre_a_jour_sources()
            with open(os.path.join(d, "src", "LibreCode.tsx")) as f:
                self.assertEqual(f.read(), "// code de l'IA")
            self.assertTrue(os.path.exists(os.path.join(d, "src", "Libre.tsx")))
        finally:
            MR.dossier = anc


class TestMusique(unittest.TestCase):
    def test_seventeen_trouve_17(self):
        """Philippe, 21/11 20h25 : « avril lavigne seventeen » : le titre s'appelle « 17 »."""
        from app import musique_en_ligne as ML, videos_en_ligne as VL
        demandes = []

        def faux(args, *a, **k):
            demandes.append(args)
            url = args[-1]
            if "search" in url:
                titres = [("a1", "Im a mess (Open Verse Challenge)"), ("a2", "Complicated (Country Version)")]
                if "q=avril+lavigne+17" in url:
                    titres = [("b1", "17"), ("a1", "Im a mess (Open Verse Challenge)")]
                return [json.dumps({"id": i, "title": t}) for i, t in titres]
            return [json.dumps({"id": u.split("v=")[1], "artists": ["Avril Lavigne"], "duration": 200})
                    for u in args if "watch?v=" in u]
        anc = VL._lancer_ytdlp
        VL._lancer_ytdlp = faux
        try:
            r = ML.chercher("avril lavigne seventeen", "ytmusic", 30)
        finally:
            VL._lancer_ytdlp = anc
        self.assertEqual(r[0]["titre"], "17")
        self.assertEqual(len(r), 3)                               # sans doublon
        self.assertEqual(r[0]["artiste"], "Avril Lavigne")
        self.assertEqual(ML.variante_nombres("dix-sept ans"), "17 ans")
        self.assertEqual(ML.variante_nombres("un jour"), "")      # « un » n'est pas pris pour un nombre


class TestFenetre(unittest.TestCase):
    def test_choix_du_moteur_et_reduire(self):
        from app import ia, motion_html as MH, motion_remotion as MR
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params["remotion_licence"] = False
        dl = ed.animation_libre()
        dl._test_oui = True
        i = dl.moteur_libre.findData("remotion")
        dl.moteur_libre.setCurrentIndex(i)
        self.assertEqual(dl.moteur.currentData(), "remotion")
        self.assertFalse(dl.b_creer.isEnabled())                 # licence pas confirmée
        dl.licence.setChecked(True)
        self.assertTrue(dl.b_creer.isEnabled())
        dl.description.setPlainText("un cadeau qui grandit jusqu'à 40, feu d'artifice, confettis")
        anc = ia.demander, MH.local_pret, MR.pret
        ia.demander = lambda *a, **k: REPONSE_R
        MH.local_pret = lambda: False
        MR.pret = lambda: False
        try:
            dl.creer()
            dl.tache.wait(20000)
            for _ in range(30):
                app.processEvents()
        finally:
            ia.demander, MH.local_pret, MR.pret = anc
        self.assertEqual(dl.anim["moteur_libre"], "remotion")
        self.assertIn("feu d'artifice", dl.message.text())       # le plan est montré
        self.assertTrue(dl.b_fabriquer.isEnabled())
        d = dl.ouvrir_projet()
        self.assertTrue(os.path.exists(os.path.join(d, "src", "LibreCode.tsx")))
        # changer de moteur : le code est à réécrire, la fabrication attend
        dl.moteur_libre.setCurrentIndex(dl.moteur_libre.findData("hyperframes"))
        self.assertFalse(dl.b_fabriquer.isEnabled())
        self.assertTrue(dl.b_corriger.isEnabled())
        self.assertIn("réécrire", dl.etat.text())
        # fermer ne perd rien : la même fenêtre revient, telle quelle (Philippe, 21/11 20h15)
        dl.close()
        app.processEvents()
        self.assertFalse(dl.isVisible())
        self.assertIs(ed.animation_libre(), dl)
        self.assertEqual(dl.anim["titre"], "40 ans")
        dl.reduire()
        self.assertFalse(dl.isVisible())
        self.assertIs(ed.animation_libre(), dl)
        dl.nouvelle()
        self.assertIsNone(dl.anim)
        dl.close()
        app.processEvents()
        self.assertIsNot(ed.animation_libre(), dl)               # rien à garder : une fenêtre neuve
        ed.projet.modifie = False


    def test_fabrique_musique_gardee(self):
        """Philippe, 21/11 20h35 : Fabrique musique : « on ne peut pas réduire ; si je fais fermer on perd tout »."""
        from PySide6.QtWidgets import QLineEdit, QPlainTextEdit
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = ed.fabrique_musique()
        for _ in range(5):
            app.processEvents()
        self.assertTrue(d.b_reduire.isVisibleTo(d))
        champ = next(w for w in d.findChildren(QPlainTextEdit) if not w.isReadOnly())
        champ.setPlainText("40 ans 40 ans, et bien voilà c'est arrivé")
        d.close()
        app.processEvents()
        self.assertFalse(d.isVisible())
        self.assertIs(ed.fabrique_musique(), d)
        self.assertIn("40 ans", champ.toPlainText())
        d.b_reduire.click()
        self.assertFalse(d.isVisible())
        self.assertIs(ed.fabrique_musique(), d)
        d._test_oui = True
        d.b_repartir.click()
        app.processEvents()
        self.assertIsNot(ed._fab_musique, d)
        ed._fab_musique.close()
        ed.projet.modifie = False

    def test_modeles(self):
        """Philippe, 21/11 20h56 : garder les modèles de musique (et d'animation) pour les retrouver."""
        from app.fenetre import Fenetre
        from app import motion_libre as ML
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = ed.fabrique_musique()
        d.phrase.setPlainText("ballade pour un anniversaire")
        d.paroles.setPlainText("[verse]\n40 ans 40 ans")
        d._test_precision = "Anniversaire 40 ans"
        self.assertTrue(d.garder_modele())
        d.phrase.setPlainText("")
        d.paroles.setPlainText("")
        d._test_biblio = "Anniversaire 40 ans"
        self.assertTrue(d.reprendre_modele())
        self.assertEqual(d.phrase.toPlainText(), "ballade pour un anniversaire")
        self.assertIn("40 ans 40 ans", d.paroles.toPlainText())
        d._test_oui = True
        d._jeter = True
        d.close()
        dl = ed.animation_libre()
        dl._test_oui = True
        dl.anim = ML.appliquer(ML.fiche("cadeau", (1080, 1920), moteur="remotion"), ML.sections(REPONSE_R))
        dl.description.setPlainText("cadeau")
        dl.format.setCurrentIndex(1)                              # 9:16
        dl.moteur_libre.setCurrentIndex(dl.moteur_libre.findData("remotion"))
        dl._test_precision = "Cadeau 40"
        self.assertTrue(dl.garder_modele())
        dl.nouvelle()
        dl._test_biblio = "Cadeau 40"
        from app import motion_remotion as MR, motion_html as MH
        anc = MR.pret, MH.local_pret
        MR.pret = MH.local_pret = lambda: False
        try:
            self.assertTrue(dl.reprendre_modele())
            if dl.tache:
                dl.tache.wait(10000)
            for _ in range(20):
                app.processEvents()
        finally:
            MR.pret, MH.local_pret = anc
        self.assertEqual(ML.code_de(dl.anim), "remotion")
        self.assertEqual(dl.format.currentData(), (1080, 1920))
        self.assertEqual(dl.moteur_choisi(), "remotion")
        ed.projet.modifie = False

    def test_autres_fenetres_ont_reduire(self):
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        for ouvrir in (ed.sequence_ia, lambda: ed.atelier_ia("image")):
            d = ouvrir()
            d = d or ed._atelier
            self.assertTrue(getattr(d, "b_reduire", None) is not None, d)
            d.close()
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
