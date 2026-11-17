"""0.9.79 : assistant de création (mode assisté de la vidéo par IA) : analyse de l'histoire, règles appliquées seules,
correction en clair, fiches et images, fabrication relue, budget prévu et dépensé."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

ANALYSE = {"personnages": [
    {"nom": "Femme brune", "genre": "personne", "sur_image": True, "position": "gauche", "description": "cheveux longs bruns, manteau noir"},
    {"nom": "Femme blonde", "genre": "personne", "sur_image": True, "position": "droite", "description": "cheveux courts, combinaison noire"},
    {"nom": "Chauffeur", "genre": "personne", "sur_image": False, "description": "homme de 50 ans, costume noir, casquette"},
    {"nom": "Limousine", "genre": "objet", "sur_image": False, "description": "limousine noire longue"},
    {"nom": "femme brune", "description": "doublon"}],
    "plans": [{"action": "Elles descendent les marches", "personnages": ["Femme brune", "Femme blonde"], "duree": 6},
              {"action": "Le chauffeur ouvre la portière pour que les deux femmes montent", "personnages": ["Chauffeur", "Inconnu"], "duree": 40},
              {"action": "La limousine s'éloigne", "personnages": ["Limousine"], "duree": 5}],
    "remarques": "Trois temps."}


def attendre(cond, s=40):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


def _png(d, nom="a.png"):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(64, 36, QImage.Format_RGB32)
    q.fill(QColor("gray"))
    q.save(ch)
    return ch


class TestLogique(unittest.TestCase):
    def test_regles(self):
        from app import assistant_creation as A, sequence_ia as Q
        d = tempfile.mkdtemp()
        img = _png(d)
        r = A.lire_analyse(ANALYSE)
        self.assertEqual(len(r["personnages"]), 4)                       # doublon de nom écarté
        self.assertEqual(r["plans"][1]["personnages"], ["Chauffeur"])    # nom inconnu écarté
        self.assertEqual(r["plans"][1]["duree"], 15)                     # durée bornée
        s = A.appliquer(Q.nouvelle("9:16"), r, img)
        self.assertEqual(len(s["plans"]), 4)                             # « pour que » : coupé en deux tout seul
        self.assertEqual(s["plans"][0]["image"], img)                    # le premier plan part de l'image du rush
        self.assertTrue(all(pl["enchainer"] for pl in s["plans"][1:]))
        self.assertTrue(s["personnages"][0]["description"].startswith("à gauche sur l'image"))
        self.assertEqual(s["personnages"][0]["images"][-1], img)          # 0.9.80 : la découpe d'abord, puis l'image
        self.assertTrue(os.path.exists(s["personnages"][0]["images"][0]))
        self.assertEqual(s["personnages"][2]["images"], [])
        self.assertEqual(s["personnages"][3]["genre"], "objet")
        s["personnages"][0]["planche"] = img
        A.appliquer(s, A.etat(s), img)                                   # rien n'a changé : la fiche est gardée
        self.assertEqual(s["personnages"][0].get("planche"), img)
        e = A.estimer(s, "kling-o3-ref", {"clef_gemini": "x", "clef_fal": "a:b"})
        self.assertGreater(e["videos"], 1.0)
        self.assertAlmostEqual(e["images"], 0.04 * (3 + 4), places=2)    # 3 fiches manquantes, 4 arrivées
        A.prevoir(s, 2.0)
        A.depenser(s, "plan", 1.5)
        self.assertFalse(A.depasse(s))
        A.depenser(s, "plan refait", 0.8)
        self.assertTrue(A.depasse(s))
        self.assertEqual(A.argent(2.3), "2,30 $")
        self.assertIn("⚠", A.texte_verdict({"ok": False, "visages": False, "action": True, "probleme": "visage différent"}))

    def test_objet_fiche(self):
        from app import sequence_ia as Q, ia
        vus = []
        anc = ia.generer_image
        ia.generer_image = lambda p, c, *a, **k: (vus.append(c), open(_png(tempfile.mkdtemp()), "rb").read())[1]
        try:
            s = Q.nouvelle()
            o = Q.personnage("Limousine", "limousine noire")
            o["genre"] = "objet"
            s["personnages"] = [o]
            Q.planche_personnage(s, o, {"clef_gemini": "x"})
        finally:
            ia.generer_image = anc
        self.assertIn("ONE object", vus[0])


class TestFenetre(unittest.TestCase):
    def test_parcours(self):
        from app.fenetre import Fenetre
        from app import moteur, assistant_creation as A, sequence_ia as Q, generateurs_video as GV, ia
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None                 # pas de fenêtre d'accueil pendant l'essai
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_gemini="x", clef_fal="a:b", clef_claude="k")
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        png = open(_png(d), "rb").read()
        demandes = []

        def faux_demander(params, consigne, texte, images=(), niveau="claude", max_jetons=3000):
            demandes.append((consigne[:30], len(list(images))))
            if "contrôles un plan" in consigne:
                return {"visages": len(demandes) % 2 == 0, "action": True, "probleme": "visage différent"}
            if "Demande :" in texte:
                e = eval(texte.split("Etat :\n")[1].split("\n\nDemande")[0].replace("true", "True").replace("false", "False").replace("null", "None"))
                e["personnages"][2]["description"] += ", plus âgé"
                e["message"] = "Chauffeur vieilli."
                return e
            return ANALYSE
        anc = (A.demander, ia.generer_image, ia.generer_image_refs, GV.generer)
        A.demander = faux_demander
        ia.generer_image = lambda p, cns, *a, **k: png
        ia.generer_image_refs = lambda p, cns, refs, delai=240: png

        def faux_generer(params, ident, texte, sortie, duree, fmt, image, *a, **k):
            moteur.lancer(["-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10:duration=1", "-pix_fmt", "yuv420p", sortie])
            return sortie
        GV.generer = faux_generer
        try:
            dl = ed.assistant_creation(c)
            dl._test_oui, dl._test_precision = True, "plus souriant"
            dl.apercu.charger = lambda *a, **k: None
            dl.apercu.arreter = lambda: None
            self.assertTrue(dl.r_suite.isChecked() and os.path.exists(dl.image))
            dl.histoire.setPlainText("Elles descendent, un chauffeur ouvre, la limousine part.")
            self.assertTrue(dl.r_suite.isChecked())                       # 0.9.80 : une idée vidéo reste la suite du plan
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_QUI and not dl._en_calcul()))
            self.assertEqual(demandes[0][1], 1)                           # l'image de départ a été montrée à l'IA
            self.assertEqual(len(dl.cartes), 4)                           # une carte par personne et par objet
            self.assertEqual([c.e["source"] for c in dl.cartes], ["image", "image", "inventer", "inventer"])
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_QUI)            # accord des personnes obligatoire
            dl.accord.setChecked(True)
            dl.libre.setText("le chauffeur plus âgé")
            dl.dire()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and "plus âgé" in dl.seq["personnages"][2]["description"]))
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_PLANS)
            self.assertEqual(dl.t_plans.rowCount(), 4)
            self.assertEqual(dl.moteur.currentData(), "kling-o3-ref")
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_IMAGES and not dl._en_calcul()))
            self.assertTrue(all(p.get("planche") for p in dl.seq["personnages"]))
            self.assertTrue(all(pl.get("image_fin") for pl in dl.seq["plans"]))
            prevu = A.budget(dl.seq)["prevu"]
            self.assertGreater(prevu, 1.0)
            dl.corriger_image(1, "arrivee")
            self.assertTrue(attendre(lambda: not dl._en_calcul()))
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_VIDEO and not dl._en_calcul() and not dl.file
                                     and all(pl.get("fichier") for pl in dl.seq["plans"]), 90))
            self.assertTrue(any(pl["verdict"] and not pl["verdict"]["ok"] for pl in dl.seq["plans"]))
            self.assertIn("⚠", dl.l_plans.item(0).text() + dl.l_plans.item(1).text())
            self.assertFalse(A.depasse(dl.seq))
            dl.l_plans.setCurrentRow(0)
            dl._test_precision = ""
            for _k in range(3):                                           # trois nouveaux essais : le budget est dépassé
                dl.refaire_plan()
                self.assertTrue(attendre(lambda: not dl._en_calcul() and dl.seq["plans"][0].get("fichier"), 60))
            self.assertTrue(A.depasse(dl.seq))
            self.assertIn("#e5484d", dl.l_budget.text())
            n = len(ed.projet.clips)
            dl.suivant()
            self.assertEqual(len(ed.projet.clips), n + 4)
            from app.projet import fin_clip
            self.assertAlmostEqual(min(x["debut"] for x in ed.projet.clips if x["id"] != c["id"]), fin_clip(c), places=2)
        finally:
            A.demander, ia.generer_image, ia.generer_image_refs, GV.generer = anc


if __name__ == "__main__":
    unittest.main()
