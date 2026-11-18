"""0.9.87 : images clefs. Chaque plan part de la vraie fin de la vidéo d'avant ; une image de fin n'est imposée qu'aux images
clefs (nouveau lieu, quelqu'un qui attend, la fin) ; relier deux rushes : départ réel, arrivée réelle, images clefs entre les
deux créées avec les fiches et les photos réelles, ou prises dans un rush."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=40):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


REPONSE = {"personnages": [{"nom": "Lui", "genre": "personne", "sur_image": True, "boite": [10, 10, 40, 95], "description": "veste"},
                           {"nom": "Elle", "genre": "personne", "sur_image": True, "boite": [60, 10, 90, 95], "description": "robe"},
                           {"nom": "Taxi", "genre": "objet", "sur_image": True, "boite": [55, 40, 99, 90], "description": "taxi jaune"}],
           "lieux": [{"nom": "Salle", "sur_image": True, "image": 1, "description": "salle de restaurant"},
                     {"nom": "Parvis", "sur_image": True, "image": 2, "description": "parvis de nuit"}],
           "plans": [{"action": "Il quitte la table et va vers la sortie", "personnages": ["Lui"], "duree": 6, "camera": "plan moyen",
                      "image_clef": False},
                     {"action": "Elle l'attend près de la porte", "personnages": ["Lui", "Elle"], "duree": 5, "camera": "plan large",
                      "image_clef": True},
                     {"action": "Ils sortent sur le parvis", "personnages": ["Lui", "Elle"], "duree": 6, "camera": "plan large",
                      "image_clef": False}]}


class TestLogique(unittest.TestCase):
    def test_clefs_et_raccord(self):
        from app import assistant_creation as A, sequence_ia as Q
        d = tempfile.mkdtemp()
        a = commun.image_test(d, "a.png") if hasattr(commun, "image_test") else None
        if a is None:
            from PySide6.QtGui import QImage, QColor
            for nom, c in (("a.png", "#803030"), ("b.png", "#303080")):
                im = QImage(320, 240, QImage.Format_RGB32)
                im.fill(QColor(c))
                im.save(os.path.join(d, nom))
            a, b = os.path.join(d, "a.png"), os.path.join(d, "b.png")
        ab = A.image_raccord(a, b, os.path.join(d, "ab.png"))
        from PySide6.QtGui import QImage
        self.assertGreater(QImage(ab).width(), 600)
        seq = Q.nouvelle("16:9")
        seq["raccord"] = {"image_debut": a, "image_fin": b}
        analyse = A.lire_analyse(REPONSE)
        self.assertEqual([p["clef"] for p in analyse["plans"]], [False, True, False])
        A.appliquer(seq, analyse, a, ab)
        pls = seq["plans"]
        self.assertEqual(pls[0]["image"], a)                          # départ réel
        self.assertTrue(pls[-1]["fin_reelle"] and pls[-1]["image_fin"] == b)     # arrivée réelle
        self.assertTrue(all(p["sans_fin"] for p in pls[:-1] if not p["clef"]))
        lieux = {x["nom"]: x for x in seq["lieux"]}
        self.assertEqual(lieux["Parvis"]["images"], [b])
        self.assertTrue(any(p["genre"] == "objet" for p in seq["personnages"]))
        params = {"clef_gemini": "k"}
        f, dep, arr = A.a_preparer(seq, params)
        self.assertEqual(dep, 0)                                       # rien d'inventé au départ des plans enchaînés
        self.assertEqual(arr, sum(1 for p in pls if p["clef"] and not p.get("fin_reelle")))
        faits = []
        anc = (Q.planche_personnage, Q.image_arrivee)
        Q.planche_personnage = lambda s, p, prm: None
        Q.image_arrivee = lambda s, i, prm, dep=None, prec="": (faits.append(i), s["plans"][i].__setitem__("image_fin", b))
        try:
            A.preparer(seq, params)
        finally:
            Q.planche_personnage, Q.image_arrivee = anc
        self.assertEqual(faits, [i for i, p in enumerate(pls) if p["clef"] and not p.get("fin_reelle")])
        self.assertEqual(Q.image_connue_avant(seq, 0), a)

    def test_coupe_garde_la_clef_a_la_fin(self):
        from app import sequence_ia as Q
        s = Q.nouvelle("16:9")
        pl = Q.plan("Elle se lève puis sort", [])
        pl.update(clef=True, sans_fin=False, image_fin="x.png")
        s["plans"] = [pl]
        Q.couper_plan(s, 0)
        self.assertEqual([p.get("clef") for p in s["plans"]], [False, True])
        self.assertEqual(s["plans"][0]["image_fin"], "")


class TestFenetre(unittest.TestCase):
    def test_relier_deux_rushes(self):
        from app.fenetre import Fenetre
        from app import moteur, assistant_creation as A
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_claude="k", clef_gemini="g")
        d = tempfile.mkdtemp()
        va, vb = commun.video_test(d, "a.mp4", 2), commun.video_test(d, "b.mp4", 2)
        ma, mb = ed.projet.ajouter_media(va, moteur.sonder(va)), ed.projet.ajouter_media(vb, moteur.sonder(vb))
        ca = ed.projet.ajouter_clip(ma["id"], "video", 0.0)
        ed.projet.ajouter_clip(mb["id"], "video", 2.0)
        vus = {}

        def faux(params, consigne, texte, images=(), niveau="claude", max_jetons=3000):
            vus["consigne"] = consigne
            return REPONSE
        anc = A.demander
        A.demander = faux
        try:
            dl = ed.assistant_creation(ca)
            dl._test_oui = True
            self.assertTrue(dl.r_raccord.isEnabled())
            dl.r_raccord.setChecked(True)
            dl._genre_choisi = True
            dl.histoire.setPlainText("Je quitte la table, elle m'attend à la porte, on sort attendre le taxi")
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_QUI and not dl._en_calcul()))
            self.assertIn("DEUX images", vus["consigne"])
            self.assertTrue(dl.seq["plans"][-1].get("fin_reelle"))
            self.assertIn("Avant", "".join(w.text() for w in dl.findChildren(D.QLabel) if w.isVisible() or True))
            dl.accord.setChecked(True)
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_PLANS)
            dl._remplir_images()
            cases = [c for c in dl.zone_images.widget().findChildren(D.QCheckBox)]
            self.assertEqual(len(cases), len(dl.seq["plans"]) - 1)     # la fin réelle n'a pas de case
            ed.timeline.aller_a(2.5)                                   # une image du rush suivant
            k = next(i for i, p in enumerate(dl.seq["plans"]) if p.get("clef") and not p.get("fin_reelle"))
            dl.clef_ligne_rouge(k)
            self.assertTrue(os.path.exists(dl.seq["plans"][k]["image_fin"]))
            dl._basculer_clef(k, False)
            self.assertTrue(dl.seq["plans"][k]["sans_fin"])
        finally:
            A.demander = anc


if __name__ == "__main__":
    unittest.main()
