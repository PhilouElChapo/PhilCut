"""0.9.9 : moteur d'IA en panne → cause et solution (Visual C++, carte dédiée, processeur), résultat des tests lisible,
tampons posés où et comme on veut (début, ligne rouge, partie en jaune, fin ; insérer, par-dessus, remplacer),
bibliothèque rangée à son idée, page de Préférences des tampons, zones des vignettes avec leur texte, menus clarifiés."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def params():
    from app.config import Parametres
    pa = Parametres()
    pa["bienvenue_vue"] = True
    pa["maj_auto"] = False
    pa["synchro"] = False
    pa["synchro_secrets"] = False
    pa.enregistrer()
    return pa


class Test099(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()

    def test_diagnostic_des_codes(self):
        from app import diagnostic_ia as D
        d = D.diagnostiquer("Le moteur s'est arrêté (code 3221225781) : ", "musique_gpu")
        self.assertEqual(d["code"], D.DLL_MANQUANTE)
        self.assertIn("vcredist", [a for a, _l in d["actions"]])
        self.assertIn("processeur", [a for a, _l in d["actions"]])
        self.assertEqual(D.code_arret("code -1073741515"), D.DLL_MANQUANTE)          # forme signée
        sortie = ("[0 Intel(R) UHD Graphics]  queueC=0[1]  queueG=0[1]\n[1 NVIDIA GeForce RTX 3070 Laptop GPU]  queueC=2[8]\n"
                  "Le moteur s'est arrêté (code 3221226505)")
        self.assertEqual(D.cartes_vulkan(sortie), [(0, "Intel(R) UHD Graphics"), (1, "NVIDIA GeForce RTX 3070 Laptop GPU")])
        self.assertEqual(D.carte_dediee(sortie), 1)
        d = D.diagnostiquer(sortie, "upscale")
        self.assertIn("carte_dediee", [a for a, _l in d["actions"]])
        self.assertEqual(D.diagnostiquer("bla", None)["actions"][0][0], "reessayer")
        p = {}
        D.appliquer("processeur", "musique_gpu", p)
        self.assertEqual(p["moteurs_evites"], ["musique_gpu"])

    def test_ncnn_reessaie_sur_la_carte_dediee(self):
        from app import creatif as C
        appels = []
        vrai = C._lancer

        def faux(genre, args, *a, **k):
            appels.append(list(args))
            if "-g" not in args:
                e = C.ErreurCreatif("Le moteur s'est arrêté (code 3221226505)")
                e.code, e.genre = 0xC0000409, genre
                e.lignes = ["[0 Intel(R) UHD Graphics]  queueC=0[1]", "[1 NVIDIA GeForce RTX 3070 Laptop GPU]  queueC=2[8]"]
                raise e
            return ["ok"]
        C._lancer = faux
        try:
            p = {}
            C._lancer_ncnn("upscale", ["-i", "x"], p, None, lambda: False, "agrandissement", "Agrandissement")
            self.assertEqual(appels[-1][-2:], ["-g", "1"])
            self.assertEqual(p["vulkan_carte"], {"upscale": 1})
            appels.clear()
            C._lancer_ncnn("upscale", ["-i", "x"], p, None, lambda: False, "agrandissement", "Agrandissement")
            self.assertEqual(len(appels), 1)                                    # la carte retenue est prise d'emblée
        finally:
            C._lancer = vrai

    def test_repli_processeur(self):
        from app import creatif as C, diagnostic_ia as D, packs_ia as P
        e = C.ErreurCreatif("code 3221225781")
        e.code, e.genre = D.DLL_MANQUANTE, "musique_gpu"
        vrai = P.moteur_installe
        P.moteur_installe = lambda g: True
        try:
            p = {}
            self.assertTrue(C._repli_processeur(e, "musique", "musique_gpu", p))
            self.assertIn("musique_gpu", p["moteurs_evites"])
            self.assertEqual(C._moteur("musique", "musique_gpu", p), "musique")
            e.genre = "musique"                                                 # déjà sur le processeur : pas de boucle
            self.assertFalse(C._repli_processeur(e, "musique", "musique_gpu", p))
        finally:
            P.moteur_installe = vrai

    def test_resultat_des_essais_lisible(self):
        from app import essai_ia
        from app.preferences import ResultatEssai
        pa = params()
        r = {"genre": "musique", "ok": False, "message": "Ne fonctionne pas : Le moteur s'est arrêté (code 3221225781) : ", "date": "2026-11-07 21:00",
             "peripherique": "carte graphique (RTX)"}
        self.assertNotIn("3221225781", essai_ia.resume(r))                    # ancien résultat : raccourci
        w = ResultatEssai(pa, "musique", lambda: None)
        w.resize(520, 400)
        w.montrer(r)
        w.show()
        app.processEvents()
        self.assertFalse(w.panneau.isHidden())
        self.assertIn("Visual C++", " ".join(w.panneau.ligne_actions.itemAt(i).widget().text()
                                             for i in range(w.panneau.ligne_actions.count()) if w.panneau.ligne_actions.itemAt(i).widget()))
        w.montrer({"ok": True, "message": "Fonctionne : 5 secondes de musique en 12 s.", "date": "x", "peripherique": "y"})
        self.assertTrue(w.panneau.isHidden())
        self.assertIn("#5bd27a", w.ligne.styleSheet())
        w.hide()
        w.deleteLater()

    def test_bibliotheque_rangee(self):
        from app import tampons as T
        liste = [{"id": "a", "nom": "Zèbre", "duree": 3, "ajoute": "2026-01-01"}, {"id": "b", "nom": "Alpha", "duree": 1, "ajoute": "2026-03-01"},
                 {"id": "c", "nom": "Milieu", "duree": 2, "ajoute": "2026-02-01", "favori": True, "usages": 1},
                 {"id": "d", "nom": "Son", "duree": 0.5, "genre": "son", "ajoute": "2026-04-01", "usages": 9}]
        self.assertEqual([e["id"] for e in T.trier(liste, "nom")], ["c", "b", "d", "a"])          # favori en tête
        self.assertEqual([e["id"] for e in T.trier(liste, "recent")], ["c", "d", "b", "a"])
        self.assertEqual([e["id"] for e in T.trier(liste, "utilise")], ["c", "d", "b", "a"])
        self.assertEqual([e["id"] for e in T.trier(liste, "genre")][-1], "d")
        for i, e in enumerate(liste):
            e["ordre"] = [3, 2, 1, 0][i]
        self.assertEqual([e["id"] for e in T.trier(liste, "perso")], ["c", "d", "b", "a"])

    def test_tampon_ou_et_comment(self):
        from app.fenetre import Fenetre
        from app import tampons as T
        from app.dialogues_tampons import DialoguePlacement, DialogueTampons
        params()
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        v = commun.video_test(self.d, "film.mp4", duree=6)
        ed.importer([v])
        t0 = time.time()
        while not ed.projet.clips and time.time() - t0 < 30:
            app.processEvents()
            time.sleep(0.05)
        tampon = commun.video_test(self.d, "tampon.mp4", duree=2)
        e = {"id": "x", "nom": "Tadaa", "duree": 2.0}
        ed.timeline.aller_a(1.0)
        ed.timeline.zone = [2.0, 3.0]
        d = DialoguePlacement(None, ed, e)
        self.assertTrue(d.r_quand["zone"].isChecked())                          # une partie en jaune : proposée d'office
        self.assertFalse(d.g3.isHidden() and False)
        d.r_ajuster["vitesse"].setChecked(True)
        d._maj()
        c = d.choix()
        self.assertEqual(c["comment"], "remplacer")
        self.assertAlmostEqual(c["vitesse"], 2.0)
        self.assertIn("remplacée" if False else "retirée", d.resume.text())
        n = len(ed.projet.clips)
        ci = ed.placer_tampon(tampon, "Tadaa", c)
        self.assertAlmostEqual(ci["debut"], 2.0, places=2)
        from app.projet import duree_clip
        self.assertAlmostEqual(duree_clip(ci), 1.0, places=2)
        self.assertAlmostEqual(ed.projet.duree(), 6.0, places=1)                # 1 s retirée, 1 s mise : même durée
        # par-dessus : rien ne bouge
        d.r_quand["debut"].setChecked(True)
        d.r_comment["dessus"].setChecked(True)
        c = d.choix()
        ci = ed.placer_tampon(tampon, "Tadaa", c)
        self.assertNotEqual(ci["piste"], "video")
        self.assertAlmostEqual(ed.projet.duree(), 6.0, places=1)
        self.assertGreater(len(ed.projet.clips), n)
        d.deleteLater()
        # format différent du projet : recadré à gauche
        ci = ed._cadrer_tampon(ci, {"cadrage": "remplir_g"})
        self.assertEqual((ci["ajustement"], ci["cadre_x"]), ("remplir", 0.0))
        from app.dialogues_tampons import _format
        self.assertEqual((_format(1920, 1080), _format(1080, 1920)), ("16:9", "9:16"))
        # fenêtre des tampons : classement et réglages
        dt = DialogueTampons(ed)
        self.assertGreaterEqual(dt.classement.count(), 5)
        dt.hide()
        dt.deleteLater()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_preferences_tampons_et_menus(self):
        from app.fenetre import Fenetre
        from app.preferences import DialoguePreferences
        pa = params()
        f = Fenetre()
        d = DialoguePreferences(f, pa, "Tampons")
        noms = [d.onglets.tabText(i) for i in range(d.onglets.count())]
        self.assertIn("Tampons et extraits", noms)
        self.assertEqual(d.onglets.tabText(d.onglets.currentIndex()), "Tampons et extraits")
        d.pl_quand.setCurrentIndex(d.pl_quand.findData("fin"))
        d.ytdlp_hauteur.setCurrentIndex(d.ytdlp_hauteur.findData(720))
        d.valider()
        self.assertEqual(pa["tampons_placement"]["quand"], "fin")
        self.assertEqual(pa["ytdlp_hauteur"], 720)
        from app import reglages
        self.assertIn("tampons_placement", reglages.COMMUNS)                 # suit sur les autres postes
        textes = []
        for a in f.menuBar().actions():
            if a.menu():
                textes += [x.text() for x in a.menu().actions()]
        self.assertFalse(any("radio" in t.lower() for t in textes))           # rangé dans Sous-titres
        self.assertFalse(any("plus tard" in t for t in textes))
        self.assertFalse(any("tête de lecture" in t for t in textes))
        d.deleteLater()
        f.hide()
        f.deleteLater()

    def test_zones_de_vignette_avec_texte(self):
        from app import vignette as V
        import numpy as np
        r = V.nouvelle_recette("youtube")
        r["zones"] = [{"couleur": "vert", "points": [[0.6, 0.1], [0.95, 0.1], [0.95, 0.6], [0.6, 0.6]], "texte": "Isolation ✓, Fenêtre ✗"},
                      {"couleur": "bleu", "points": [[0.05, 0.6], [0.55, 0.6], [0.55, 0.95], [0.05, 0.95]], "texte": "Trois erreurs"},
                      {"couleur": "jaune", "points": [[0.3, 0.3], [0.35, 0.3], [0.35, 0.35], [0.3, 0.35]], "texte": "la fissure"}]
        img = np.full((720, 1280, 3), 90, np.uint8)
        q, infos = V.composer(r, img, L=1280, H=720)
        self.assertFalse(q.isNull())
        self.assertEqual(infos["avertissements"], [])                          # titre et éléments donnés par les zones
        self.assertGreater(infos["taille_titre"], 0)
        dem = V.demande_ia(r)
        self.assertIn("Isolation ✓", dem)
        self.assertIn("la fissure", dem)
        self.assertIn("place du titre", dem)

    def test_musiques_sans_numeros_et_dans_l_ordre(self):
        from app import musiques as MU
        d = MU._depuis_nom(os.path.join("Musique", "AC-DC", "Back In Black", "01 - Hells Bells.mp3"))
        self.assertEqual((d["titre"], d["artiste"], d["album"], d["piste"]), ("Hells Bells", "AC-DC", "Back In Black", 1))
        d = MU._depuis_nom(os.path.join("x", "1-03. Shake A Leg.flac"))
        self.assertEqual((d["titre"], d["piste"]), ("Shake A Leg", 3))
        d = MU._depuis_nom(os.path.join("x", "Avril Lavigne - Complicated.mp3"))
        self.assertEqual((d["artiste"], d["titre"]), ("Avril Lavigne", "Complicated"))
        d = MU._depuis_nom(os.path.join("x", "03 - Avril Lavigne - Complicated.mp3"))
        self.assertEqual((d["artiste"], d["titre"], d["piste"]), ("Avril Lavigne", "Complicated", 3))
        liste = [{"titre": "You Shook Me", "artiste": "AC/DC", "album": "Back In Black", "piste": 10, "chemin": "a"},
                 {"titre": "Hells Bells", "artiste": "AC/DC", "album": "Back In Black", "piste": 1, "chemin": "b"},
                 {"titre": "Thunderstruck", "artiste": "AC/DC", "album": "The Razors Edge", "piste": 1, "chemin": "c"},
                 {"titre": "Duo", "artiste": "Invité", "artiste_album": "AC/DC", "album": "Live", "piste": 2, "chemin": "d"},
                 {"titre": "Sans rien", "chemin": "e"}]
        g = MU.classer(liste, "artiste")
        self.assertEqual([x for x, _m in g], ["AC/DC", "Artiste inconnu"])         # un groupe par artiste, inconnus à la fin
        self.assertEqual([m["titre"] for m in g[0][1]], ["Hells Bells", "You Shook Me", "Duo", "Thunderstruck"])
        g = dict(MU.classer(liste, "album"))
        self.assertEqual([m["titre"] for m in g["Back In Black"]], ["Hells Bells", "You Shook Me"])

    def test_recherche_youtube(self):
        from app import videos_en_ligne as VL
        self.assertEqual(VL.correction("planette interdite", ["planète interdite", "planète interdite film"]), "planète interdite")
        self.assertIsNone(VL.correction("planète interdite", ["planète interdite film", "planète interdite 1956"]))
        self.assertIsNone(VL.correction("tout autre chose", ["chat", "chien"]))
        import json
        vu = {}
        lignes = [json.dumps({"id": "a", "title": "Court", "duration": 30, "url": "https://www.youtube.com/shorts/a"}),
                  json.dumps({"id": "b", "title": "Long", "duration": 600, "url": "https://www.youtube.com/watch?v=b"})]
        vrai = VL._lancer_ytdlp
        VL._lancer_ytdlp = lambda args, *a, **k: (vu.setdefault("args", args), lignes)[1]
        try:
            self.assertEqual([r["titre"] for r in VL.chercher_youtube("planète interdite", 10, "shorts")], ["Court"])
            import urllib.parse
            self.assertIn("planète interdite #shorts", urllib.parse.unquote_plus(vu["args"][-1]))      # 0.9.44 : mots exacts
            self.assertIn("--xff", vu["args"])                                 # le YouTube du pays
            self.assertEqual([r["titre"] for r in VL.chercher_youtube("x", 10, "videos")], ["Long"])
            self.assertEqual(len(VL.chercher_youtube("x", 10)), 2)
        finally:
            VL._lancer_ytdlp = vrai
        from app.dialogues_tampons import DialogueVisionner
        d = DialogueVisionner(None, "https://exemple.invalid/v.mp4", {"titre": "Essai", "duree": 120}, 5.0, None)
        d.curseur.setValue(300)
        d._marquer(False)
        self.assertAlmostEqual(d.debut, 5.0)
        self.assertAlmostEqual(d.fin, 30.0)
        self.assertIn("25.0 s", d.morceau.text())
        d.deleteLater()


if __name__ == "__main__":
    unittest.main()
