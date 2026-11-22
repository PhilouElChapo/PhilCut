"""1.1.12 : groupe entier dans la bibliothèque (clip de groupe) ; aide par discussion (manuel tiré des vrais menus, chemins
vérifiés, « Montrez-moi », « Le faire pour moi »)."""
import copy, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def png(d, nom):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(80, 60, QImage.Format_RGB32)
    q.fill(QColor("gray"))
    q.save(ch)
    return ch


class TestGroupe(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre()
        self.f.bienvenue = lambda *a, **k: None
        self.ed = self.f.nouveau_projet("16:9")
        self.d = tempfile.mkdtemp()

    def test_garder_et_reprendre(self):
        from app import bibliotheque_creations as B, clip_groupe as CG, moteur
        from app.dialogues_clip_groupe import DialogueClipGroupe
        B.garder(self.ed.params, "musicien", "Batteur roux", "cheveux roux", {"planche": png(self.d, "b.png")}, {"instrument": "batterie"})
        son = os.path.join(self.d, "s.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=4", son])
        m = self.ed.projet.ajouter_media(son, moteur.sonder(son))
        c = self.ed.projet.ajouter_clip(m["id"], "audio", 0.0)
        dl = DialogueClipGroupe(self.ed, c)
        dl.clip = {"groupe": CG.groupe_propose({"caption_en": "rock"}), "plans": [], "lieu": "concert", "anime": False,
                   "format": "16:9", "chemin": son, "analyse": {}}
        for g in dl.clip["groupe"]:
            dl._ligne_membre(g)
        dl._test_biblio = "Batteur roux"
        dl._membre_biblio()
        n = len(dl.clip["groupe"])
        dl._test_precision = "Les Essais"
        dl._garder_groupe()
        grp = B.lister(self.ed.params, "groupe")
        self.assertEqual([g["nom"] for g in grp], ["Les Essais"])
        self.assertEqual(len(grp[0]["donnees"]["membres"]), n)
        self.assertTrue(all(x.get("biblio") for x in grp[0]["donnees"]["membres"]))   # chaque musicien a sa fiche
        self.assertIn("Batteur roux", [x["nom"] for x in grp[0]["donnees"]["membres"]])
        # nouveau clip : le groupe revient, avec le visage du batteur
        dl2 = DialogueClipGroupe(self.ed, c)
        dl2.clip = {"groupe": CG.groupe_propose({"caption_en": "jazz"}), "plans": [], "lieu": "concert", "anime": False,
                    "format": "16:9", "chemin": son, "analyse": {}}
        dl2._test_biblio = "Les Essais"
        dl2._groupe_biblio()
        self.assertEqual(len(dl2.clip["groupe"]), n)
        b = next(x for x in dl2.clip["groupe"] if x["nom"] == "Batteur roux")
        self.assertTrue(os.path.exists(b["image"]))
        self.assertEqual(dl2.table_groupe.rowCount(), n)
        self.assertIn("musiciens", B.resume(grp[0]))


def fenetre_avec_plans():
    from app.fenetre import Fenetre
    f = Fenetre([])
    f.bienvenue = lambda *a, **k: None
    ed = f._editeur_ou_nouveau()
    v = commun.video_test(os.environ["APPDATA"], "aide.mp4", duree=3)
    m = ed.projet.ajouter_media(v, {"duree": 3.0})
    ed.projet.ajouter_clip(m["id"])
    ed.projet.ajouter_clip(m["id"])
    ed.rafraichir()
    f.show()
    app.processEvents()
    return f, ed


class TestAide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f, cls.ed = fenetre_avec_plans()

    def test_manuel(self):
        from app import aide_ia as AI
        barre = [" › ".join(c) for c, _b in AI.menus_barre(self.f)]
        self.assertIn("Aide › Demander à l'aide (discussion avec l'IA)…", barre)
        self.assertTrue(any(x.startswith("Fabrique IA › Vidéo › Clip de groupe") for x in barre))
        clic = AI.menus_clic_droit(self.ed)
        self.assertIn(("Prolonger ce plan (image tenue, ralenti ou IA)…",), [c for c, _b in clic[AI.PLAN_VIDEO]])
        consignes, texte = AI.preparer(self.f, self.ed, self.ed.params, "comment rallonger un plan ?", [], "claude")
        self.assertIn("Prolonger ce plan", consignes)
        self.assertIn("Fiche : Rallonger un plan", consignes)       # fiches du catalogue
        self.assertIn("Guide :", consignes)
        self.assertIn("Ligne rouge", texte)
        self.assertNotIn("sk-ant", consignes + texte)
        c2, _t = AI.preparer(self.f, self.ed, self.ed.params, "comment rallonger un plan ?", [], "locale")
        self.assertLess(len(c2), len(consignes))
        self.assertIn("Fiche : Rallonger un plan", c2)              # la plus proche reste pour l'IA de ce poste

    def test_chemins_verifies(self):
        from app import aide_ia as AI
        self.assertTrue(AI.chemin_valide(self.f, self.ed, {"menu": ["Fabrique IA", "Vidéo", "Clip de groupe d'après une chanson…"]}))
        self.assertFalse(AI.chemin_valide(self.f, self.ed, {"menu": ["Fabrique IA", "Vidéo", "Téléporter l'avion"]}))
        self.assertFalse(AI.chemin_valide(self.f, self.ed, {"menu": ["Fabrique IA", "Vidéo"]}))        # un sous-menu, pas une ligne
        r = AI.lire_reponse({"reponse": "Faites ceci.", "etapes": [
            {"texte": "Clic droit sur le plan", "montrer": {"clic_droit": ["Prolonger ce plan (image tenue, ralenti ou IA)…"]}},
            {"texte": "Inventé", "montrer": {"menu": ["Montage", "Baguette magique"]}}, "Une étape en texte"],
            "faire": {"menu": ["Rien", "Du tout"]}, "dites_le": "", "manque": ""})
        self.assertEqual(AI.verifier(r, self.f, self.ed), 2)
        self.assertIsNotNone(r["etapes"][0]["montrer"])
        self.assertIsNone(r["etapes"][1]["montrer"])
        self.assertEqual(r["etapes"][2]["texte"], "Une étape en texte")
        self.assertIsNone(r["faire"])

    def test_faire_pour_moi(self):
        from app import aide_ia as AI
        c = AI._un_plan(self.ed, "video")
        avant = bool(c.get("muet"))
        self.assertTrue(AI.faire(self.f, self.ed, {"clic_droit": ["Muet"], "plan": "video"}))
        self.assertEqual(bool(c.get("muet")), not avant)
        self.assertFalse(AI.faire(self.f, self.ed, {"clic_droit": ["N'existe pas"], "plan": "video"}))

    def test_fenetre(self):
        from app.dialogues_aide_ia import DialogueAideIA
        d = DialogueAideIA(self.f, "Comment rallonger ce plan ?")
        d.capture.setChecked(False)
        recu = {}

        def faux(consignes, texte, images, niveau):
            recu.update(c=consignes, t=texte, i=images)
            return {"reponse": "Clic droit sur le plan.", "etapes": [
                {"texte": "Ouvrez Prolonger", "montrer": {"clic_droit": ["Prolonger ce plan (image tenue, ralenti ou IA)…"],
                                                         "plan": "video"}}],
                    "faire": {"clic_droit": ["Prolonger ce plan (image tenue, ralenti ou IA)…"], "plan": "video"},
                    "dites_le": "baisse la musique", "manque": ""}
        d._test_envoi = faux
        d.envoyer()
        d.tache.wait(10000)
        app.processEvents()
        self.assertIn("Comment rallonger", recu["t"])
        self.assertEqual(recu["i"], [])
        self.assertEqual(len(d.historique), 1)
        textes = [d.flux.itemAt(i).widget().text() for i in range(d.flux.count())]
        self.assertTrue(any("Montrez-moi" in t for t in textes))
        self.assertTrue(any("Le faire pour moi" in t for t in textes))
        self.assertTrue(any("Dites-le en clair" in t for t in textes))
        self.assertIn("Clic droit sur le plan.", d.fil.toPlainText())
        d.question.setPlainText("Et ensuite ?")
        d.envoyer()
        d.tache.wait(10000)
        app.processEvents()
        self.assertIn("DISCUSSION JUSQU'ICI", recu["t"])          # la suite garde la discussion
        d.hide()

    def test_capture(self):
        from app import aide_ia as AI
        imgs = AI.capture(self.f)
        self.assertTrue(imgs and os.path.exists(imgs[0]))

    def test_cache_claude(self):
        from app import ia
        corps = {}
        anc = ia._http, ia._modele_claude
        ia._http = lambda url, c=None, e=None, *a, **k: (corps.update(c=c), {"content": [{"type": "text", "text": "ok"}]})[1]
        ia._modele_claude = lambda *a, **k: "claude-test"
        try:
            ia._claude("x", {}, "m" * 9000, "q", [], 100)
            self.assertEqual(corps["c"]["system"][0]["cache_control"], {"type": "ephemeral"})
            ia._claude("x", {}, "court", "q", [], 100)
            self.assertEqual(corps["c"]["system"], "court")
        finally:
            ia._http, ia._modele_claude = anc


if __name__ == "__main__":
    unittest.main()
