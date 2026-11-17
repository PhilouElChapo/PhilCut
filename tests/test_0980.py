"""0.9.80 : de l'idée au résultat. Une phrase → genre deviné, cartes pré-remplies (sources expliquées), tout texte amélioré
par l'IA (deux versions montrées), personnes de l'image encadrées et corrigées au clic ; musique partie par partie (tempo
de chaque partie, même style, voix, tonalité), enchaînée en fondu d'une mesure."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

REPONSE = {"titre": "Ballade", "duree": 180,
           "style": {"reference": "Archangel", "description": "rock mélodique, guitares saturées, batterie ample", "style_id": "rock",
                     "source": "fichier"},
           "voix": {"chantee": True, "reference": "chanteur d'Archangel", "description": "voix rock puissante",
                    "retouche": "plus féminine et chaude", "source": "fichier"},
           "paroles": {"theme": "la route de nuit", "source": "ia", "langue": "fr"},
           "parties": [{"nom": "Intro", "duree": 20, "tempo": 140, "energie": "forte", "chant": False},
                       {"nom": "Couplet", "duree": 40, "tempo": 140, "energie": "forte", "chant": True},
                       {"nom": "Ballade", "duree": 80, "tempo": 70, "energie": "calme", "chant": True, "description": "longue ballade lente"},
                       {"nom": "Final", "duree": 50, "tempo": 140, "energie": "forte", "chant": True}],
           "tonalite": "E minor"}


def attendre(cond, s=40):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


def son(d, nom, duree=3.0, f=440):
    from app import moteur
    ch = os.path.join(d, nom)
    moteur.lancer(["-y", "-f", "lavfi", "-i", f"sine=frequency={f}:duration={duree}", "-ac", "2", ch])
    return ch


class TestMethode(unittest.TestCase):
    def test_genre_duree_manque(self):
        from app import assistant_idee as I
        self.assertEqual(I.deviner_genre("crée une ballade rock de 3 minutes avec une voix chaude"), "musique")
        self.assertEqual(I.deviner_genre("Les deux femmes descendent les marches", True), "suite")
        self.assertEqual(I.deviner_genre("Une femme ouvre son ordinateur"), "scene")
        self.assertEqual(I.deviner_genre("un logo animé pour la chaîne"), "logo")
        self.assertEqual(I.duree_dite("ballade de 3 minutes"), 180)
        self.assertEqual(I.duree_dite("2 min 30"), 150)
        self.assertEqual(I.duree_dite("rien"), 60)
        e = I.element("voix", "Voix", "", "fichier")
        self.assertIn("morceau", I.manque(e))
        e.update(chemin="/x.wav")
        self.assertIn("faire", I.manque(e))                  # l'usage n'est jamais choisi d'office pour la voix
        e.update(usage="timbre")
        self.assertIn("accord", I.manque(e))
        e.update(accord=True, voix_seule="/v.wav")
        self.assertEqual(I.manque(e), "")
        s = I.element("style", "S", "", "fichier", chemin="/a.mp3", usage="reprendre")
        self.assertIn("Déclarez", I.manque(s))
        p = I.element("personne", "Chauffeur", "", "inventer")
        self.assertIn("Décrivez", I.manque(p))

    def test_lecture_et_parties(self):
        from app import assistant_idee as I
        r = I.lire_musique(REPONSE, 180.0)
        self.assertEqual(sum(p["duree"] for p in r["parties"]), 180)       # durée voulue respectée
        st, vx, pa = r["elements"]
        self.assertEqual((st["source"], st["choix"], vx["retouche"], pa["source"]), ("fichier", "rock", "plus féminine et chaude", "ia"))
        self.assertEqual(r["parties"][2]["tempo"], 70)
        txt = "[verse]\na\nb\n[chorus]\nc\n[bridge]\nd\n[outro]\ne"
        par = I.paroles_par_partie(txt, r["parties"])
        self.assertEqual(par[0], "")                                       # l'intro reste instrumentale
        self.assertTrue(par[1].startswith("[verse]") and par[2].startswith("[chorus]") and "[outro]" in par[3])
        base = I.fiche_base(r)
        f = I.fiche_partie(base, r, 2, par[2])
        self.assertEqual((f["tempo"], f["duree"], f["instrumental"]), (70, r["parties"][2]["duree"], False))
        self.assertIn("slow", f["partie_en"])
        self.assertTrue(I.fiche_partie(base, r, 0, par[0])["instrumental"])
        simple = I.analyse_musique_simple("une ballade rock de 3 minutes, rapide puis lente au milieu, avec voix")
        self.assertEqual(simple["duree"], 180)
        self.assertTrue(any(p["tempo"] < 90 for p in simple["parties"]))   # le passage lent est là sans IA

    def test_enchainer_et_creer(self):
        from app import assistant_idee as I, musique_ia as MI, moteur
        d = tempfile.mkdtemp()
        etat = I.lire_musique(dict(REPONSE, parties=[{"nom": "A", "duree": 4, "tempo": 120}, {"nom": "B", "duree": 4, "tempo": 60},
                                                     {"nom": "C", "duree": 4, "tempo": 120}]), 12.0)
        etat["elements"][1]["source"] = "aucune"
        vus = []

        def faux_creer(fiche, sortie, params=None, progression=None, arret=lambda: False, traduire=None):
            vus.append((fiche["tempo"], fiche["duree"], fiche["tonalite"]))
            return son(d, os.path.basename(sortie).replace(".mp3", ".wav"), fiche["duree"], 200 + fiche["tempo"]), {}
        anc = MI.creer
        MI.creer = faux_creer
        try:
            final, faits, _b = I.creer_parties(etat, d, {})
            self.assertEqual([v[0] for v in vus], [120, 60, 120])
            self.assertTrue(all(v[2] == "E minor" for v in vus))            # même tonalité partout
            duree = moteur.sonder(final)["duree"]
            self.assertTrue(9.0 < duree < 12.0, duree)                     # 3 × 4 s moins deux fondus
            vus.clear()
            faits.pop(1)
            I.creer_parties(etat, d, {}, deja=faits)                       # une partie refaite seule
            self.assertEqual(len(vus), 1)
        finally:
            MI.creer = anc

    def test_ameliorer_et_cadres(self):
        from app import assistant_idee as I, assistant_creation as A
        anc = A.demander
        A.demander = lambda p, c, t, images=(), niveau="claude", max_jetons=3000: {"texte": "Elles descendent lentement les marches.",
                                                                                   "pourquoi": "gestes précisés"}
        try:
            self.assertEqual(I.ameliorer_texte({}, "elles descendent", "plan"), ("Elles descendent lentement les marches.", "gestes précisés"))
        finally:
            A.demander = anc
        self.assertEqual(A.lire_boite([10, 20, 40, 90]), [0.1, 0.2, 0.4, 0.9])
        self.assertEqual(A.lire_boite([100, 200, 400, 900]), [0.1, 0.2, 0.4, 0.9])
        self.assertIsNone(A.lire_boite("rien"))
        b = A.boite_autour(0.95, 0.5)
        self.assertLessEqual(b[2], 1.0)
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        img = os.path.join(d, "i.png")
        q = QImage(200, 100, QImage.Format_RGB32)
        q.fill(QColor("gray"))
        q.save(img)
        dec = A.decouper(img, [0.1, 0.1, 0.4, 0.9], os.path.join(d, "dec.png"))
        self.assertLess(QImage(dec).width(), 200)


class TestFenetre(unittest.TestCase):
    def test_cartes_video(self):
        from app.fenetre import Fenetre
        from app import moteur, assistant_creation as A
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_claude="k")
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        reponse = {"personnages": [{"nom": "Femme brune", "genre": "personne", "sur_image": True, "position": "gauche",
                                    "boite": [5, 10, 45, 95], "description": "manteau noir"},
                                   {"nom": "Chauffeur", "genre": "personne", "sur_image": False, "description": "costume"}],
                   "plans": [{"action": "Elle descend", "personnages": ["Femme brune"], "duree": 5}]}

        def faux(params, consigne, texte, images=(), niveau="claude", max_jetons=3000):
            if "améliores le phrasé" in consigne:
                return {"texte": texte + " (mieux)", "pourquoi": "ok"}
            if "aides à décrire" in consigne:
                return {"description": "homme de 50 ans, costume noir, casquette"}
            return reponse
        anc = A.demander
        A.demander = faux
        try:
            dl = ed.assistant_creation(c)
            dl._test_prendre = True
            dl.histoire.setPlainText("Elle descend les marches vers la voiture")
            dl.ameliorer(dl.c_histoire)
            self.assertTrue(attendre(lambda: not dl._en_calcul() and "(mieux)" in dl.c_histoire.texte()))
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_QUI and not dl._en_calcul()))
            brune, chauffeur = dl.cartes
            self.assertEqual(brune.e["boite"], [0.05, 0.1, 0.45, 0.95])      # cadre proposé par l'IA
            self.assertTrue(dl.image_cadres is not None and dl.image_cadres.cadres[0][2])
            dl._activer(brune)
            dl._cadre_trace([0.5, 0.1, 0.9, 0.9])                           # corrigé à la souris
            self.assertEqual(brune.e["boite"], [0.5, 0.1, 0.9, 0.9])
            self.assertTrue(os.path.exists(brune.e["decoupe"]))
            dl._aider_description(chauffeur)
            self.assertTrue(attendre(lambda: not dl._en_calcul() and "casquette" in chauffeur.e["description"]))
            dl.accord.setChecked(True)
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_PLANS)
            p0 = dl.seq["personnages"][0]
            self.assertEqual(p0["boite"], [0.5, 0.1, 0.9, 0.9])
            self.assertEqual(p0["images"][0], brune.e["decoupe"])            # la fiche partira de la bonne personne
            self.assertIn("casquette", dl.seq["personnages"][1]["description"])
            dl.t_plans.setCurrentCell(0, 0)
            dl._ameliorer_plan()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and "(mieux)" in dl.t_plans.item(0, 0).text()))
            self.assertFalse(A.depasse(dl.seq))                               # rien de prévu encore : jamais rouge
        finally:
            A.demander = anc

    def test_parcours_musique(self):
        from app.fenetre import Fenetre
        from app import assistant_creation as A, musique_ia as MI, paroles as PA, creatif, traduction_recherche as TR
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_claude="k")
        d = tempfile.mkdtemp()
        morceau = son(d, "archangel.wav", 8.0)
        petit = dict(REPONSE, duree=12, parties=[{"nom": "Intro", "duree": 4, "tempo": 140, "chant": False},
                                                  {"nom": "Ballade", "duree": 4, "tempo": 70, "chant": True},
                                                  {"nom": "Final", "duree": 4, "tempo": 140, "chant": True}])
        anc = (A.demander, MI.analyser, MI.creer, PA.ecrire, creatif.extraire_voix, MI.decrire_voix, creatif.separation_manquante)
        A.demander = lambda *a, **k: petit
        MI.analyser = lambda ch, params=None, progression=None, arret=None, ecouter=True: {"resume": "rock, 140 bpm", "caption_en": "rock",
                                                                                         "bpm": 140, "tonalite": "E minor", "mesure": "4/4"}
        MI.creer = lambda fiche, sortie, *a, **k: (son(d, os.path.basename(sortie)[:-4] + ".wav", fiche["duree"], 300), {})
        PA.ecrire = lambda *a, **k: "[verse]\nla route\n[chorus]\nde nuit"
        creatif.extraire_voix = lambda src, sortie, *a, **k: son(d, "voix.wav", 3.0)
        MI.decrire_voix = lambda *a, **k: {"fr": "voix grave, vibrato léger", "en": "deep voice, light vibrato"}
        creatif.separation_manquante = lambda params=None: None
        anc_tr = TR.phrase_en_anglais
        TR.phrase_en_anglais = lambda x: ("EN " + x, "service", [])       # pas de réseau pendant les essais
        try:
            dl = ed.assistant_creation(None)
            dl._test_oui = True
            dl._test_passage = lambda dlg: dlg._b_tout.click()
            dl.histoire.setPlainText("crée une ballade rock de 3 minutes avec le style d'Archangel et la voix de ce groupe, plus féminine")
            self.assertTrue(dl.r_musique.isChecked())                        # deviné d'après les mots
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_M_ELEM and not dl._en_calcul()))
            self.assertIn("Ce qu'il faut", dl.fil.text())
            style, voix, paroles = dl.mcartes
            self.assertEqual(style.e["source"], "fichier")
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_M_ELEM)            # cartes incomplètes : on reste
            dl._fichier_choisi(style, morceau)
            dl._usage(style, "reprendre")
            dl._declarer(style)
            self.assertTrue(style.e["droits_ok"])
            dl._analyser_style(style)
            self.assertTrue(attendre(lambda: not dl._en_calcul() and style.e.get("pret")))
            dl._fichier_choisi(voix, morceau, passage=False)
            self.assertEqual(voix.e.get("usage"), "")                         # deux voies, aucune cochée d'office
            dl._usage(voix, "decrire")
            dl._voix(voix, "decrire")
            self.assertTrue(attendre(lambda: not dl._en_calcul() and voix.e.get("voix_decrite")))
            self.assertEqual(voix.e["retouche"], "plus féminine et chaude")
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_M_DEROULE)
            self.assertEqual(dl.t_parties.rowCount(), 3)
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_M_PAROLES)
            dl._ecrire_paroles()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and "[chorus]" in dl.c_paroles.texte()))
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_M_CREER)
            dl.apercu_m.charger = lambda *a, **k: None
            dl.apercu_m.reglages = lambda: {"src_debut": 0.0, "src_fin": 10.0}
            dl.creer_musique()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and dl.resultat, 60), dl.etat.text())
            self.assertEqual(len(dl.parties_faites), 3)
            self.assertTrue(os.path.exists(dl.resultat))
            self.assertFalse(A.depasse(dl.musique))
            n = len(ed.projet.medias)
            dl.suivant()                                                      # poser sous la vidéo
            self.assertTrue(attendre(lambda: len(ed.projet.medias) > n, 20))
        finally:
            (A.demander, MI.analyser, MI.creer, PA.ecrire, creatif.extraire_voix, MI.decrire_voix, creatif.separation_manquante) = anc
            TR.phrase_en_anglais = anc_tr


if __name__ == "__main__":
    unittest.main()
