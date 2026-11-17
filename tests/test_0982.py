"""0.9.82 : intro et logo animé, de l'idée au résultat (cartes Logo, Style, Fond, Son ; texte améliorable ; aperçu animé ;
fabrication avec le son mêlé ; pose au début, à la fin, à la ligne rouge)."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

REPONSE = {"titre": "Mes vols du dimanche", "sous_titre": "épisode 3", "duree": 2.5,
           "style": {"modele": "cinema", "accent": "#e8c27a", "description": "doré, cinéma"},
           "logo": {"source": "atelier", "description": "mon logo"},
           "fond": {"source": "uni", "couleur": "#101820"},
           "son": {"source": "bruitage", "bruitage": "impact"}, "placement": "debut"}


def attendre(cond, s=60):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestLogique(unittest.TestCase):
    def test_lecture(self):
        from app import assistant_intro as AI, assistant_idee as I
        r = AI.lire_intro(REPONSE)
        logo, style, fond, son = r["elements"]
        self.assertEqual((style["choix"], style["accent"], fond["couleur"], son["choix"]), ("cinema", "#e8c27a", "#101820", "impact"))
        self.assertIn("logos", I.manque(logo))                         # un de mes logos : encore à choisir
        self.assertEqual(I.manque(son), "")
        r2 = AI.lire_intro({"duree": 99, "style": {"modele": "inconnu"}, "son": {"source": "bruitage", "bruitage": "rien"}})
        self.assertEqual((r2["duree"], r2["elements"][1]["choix"], r2["elements"][3]["choix"]), (8.0, "masque", "whoosh"))
        s = AI.analyse_intro_simple("une intro cinéma « Ciel ouvert » avec mon logo et un whoosh, 4 s")
        self.assertEqual((s["titre"], s["elements"][1]["choix"], s["elements"][0]["source"], s["elements"][3]["choix"]),
                         ("Ciel ouvert", "cinema", "atelier", "whoosh"))
        self.assertEqual(s["duree"], 4.0)

    def test_fabriquer_avec_son(self):
        from app import assistant_intro as AI, moteur
        r = AI.lire_intro(REPONSE)
        r["elements"][0]["source"] = "aucune"
        r["titre"] = "Ciel ouvert"
        d = tempfile.mkdtemp()
        f = AI.fabriquer(r, d, 320, 180, 15)
        info = moteur.sonder(f)
        self.assertTrue(2.0 < float(info["duree"]) < 3.2, info)
        self.assertTrue(info.get("audio"), info)                          # le son est mêlé
        r["elements"][3]["source"] = "aucune"
        self.assertTrue(os.path.exists(AI.fabriquer(r, d, 320, 180, 15)))


class TestFenetre(unittest.TestCase):
    def test_parcours(self):
        from app.fenetre import Fenetre
        from app import assistant_creation as A, logo as LG
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_claude="k")
        LG.enregistrer(dict(next(iter(LG.gabarits("Ciel").values())), nom="Logo essai"), 256)
        anc = A.demander
        A.demander = lambda *a, **k: {"texte": "Mes vols du dimanche !", "pourquoi": "plus vivant"} if "améliores" in a[1] else REPONSE
        try:
            dl = ed.assistant_creation(intro=True)
            dl._test_prendre = True
            self.assertTrue(dl.r_logo.isChecked())
            dl.histoire.setPlainText("une intro de 2 s style cinéma avec mon logo et un impact")
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_I_ELEM and not dl._en_calcul()))
            self.assertIn("Ce qu'il faut", dl.fil.text())
            logo = dl.icartes[0]
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_I_ELEM)          # logo pas encore choisi
            logo.e["chemin"] = LG.enregistrer(next(x for x in LG.liste() if x.get("nom") == "Logo essai"))
            logo.rafraichir()
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_I_TEXTE)
            self.assertEqual(dl.c_titre.texte(), "Mes vols du dimanche")
            dl.ameliorer(dl.c_titre)
            self.assertTrue(attendre(lambda: not dl._en_calcul() and dl.c_titre.texte().endswith("!")))
            self.assertTrue(attendre(lambda: dl.i_apercu.pixmap() is not None and not dl.i_apercu.pixmap().isNull(), 5))
            dl.i_duree.setValue(2.0)
            dl.apercu_i.charger = lambda *a, **k: None
            dl.suivant()                                                     # fabrication
            self.assertTrue(attendre(lambda: not dl._en_calcul() and dl.intro_fichier, 120), dl.etat.text())
            self.assertEqual(dl.pages.currentIndex(), D.P_I_CREER)
            n = len(ed.projet.medias)
            dl.suivant()                                                     # poser au début
            self.assertTrue(attendre(lambda: len(ed.projet.medias) > n, 10))
            dl._test_precision = "Cinéma doré"
            dl.garder_carte(dl.intro["elements"][1])
            from app import bibliotheque_creations as B
            x = next(e for e in B.lister(ed.params, "style_intro") if e["nom"] == "Cinéma doré")
            self.assertEqual(x["donnees"]["modele"], "cinema")
        finally:
            A.demander = anc


if __name__ == "__main__":
    unittest.main()
