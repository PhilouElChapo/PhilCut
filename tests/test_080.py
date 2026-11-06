"""0.8 : Goodies dessinés des packs Balade, Route, Fête, Maison et Commerce ; projets des autres postes en gris sur
l'Accueil ; tampons vidéo (maison, vos clips, clips libres en ligne) avec crédit à la publication."""
import json, os, subprocess, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def attendre(tache, delai=180):
    t0 = time.time()
    while tache.isRunning() and time.time() - t0 < delai:
        app.processEvents()
        time.sleep(0.05)
    for _i in range(10):
        app.processEvents()


class Test080(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QFontDatabase
        for f in os.listdir(os.path.join(RACINE, "fonts")):
            if f.endswith(".ttf"):
                QFontDatabase.addApplicationFont(os.path.join(RACINE, "fonts", f))
        cls.d = tempfile.mkdtemp()
        from app.config import Parametres
        cls.params = Parametres()

    # ---------------------------------------------------------------- Goodies dessinés
    def test_goodies_dessines_bougent_et_se_voient(self):
        from app import goodies as G, goodies_dessins as GD
        for genre in GD.GENRES:
            g = {"genre": genre, "debut": 0, "fin": 6, "taille": 0.3, "options": {"ciel": "pluie", "texte": "2026-05-01"} if genre in ("meteo", "date") else {}}
            a, b = G.image(g, 0.6, 160), G.image(g, 3.2, 160)
            visibles = sum(1 for x in range(0, 160, 4) for y in range(0, 160, 4) if b.pixelColor(x, y).alpha() > 120)
            self.assertGreater(visibles, 60, f"{genre} : presque rien de dessiné")
            if genre not in ("date",):
                self.assertNotEqual(a, b, f"{genre} : l'image ne bouge pas")
        # le style HUD garde le badge sobre
        h = G.image({"genre": "altitude", "debut": 0, "fin": 4, "style": "hud"}, 1.0, 160)
        self.assertFalse(h.isNull())

    def test_tous_les_genres_des_packs_dessines(self):
        from app import goodies as G, goodies_dessins as GD
        badges = {"immatriculation", "chrono"}          # restent des badges de texte, par choix
        for pack in ("balade", "route", "fete", "maison", "pharmacie"):
            for genre in G.PACKS[pack]["goodies"]:
                if genre in ("croix", "confettis", "lune", "horloge", "boussole", "mini_carte") or genre in badges:
                    continue
                self.assertIn(genre, GD.GENRES, f"{pack} : {genre} n'est pas dessiné")

    # ---------------------------------------------------------------- catalogues en ligne
    def test_catalogue_effets_en_ligne(self):
        from app import effets as E, catalogue_ligne as CL
        with open(os.path.join(RACINE, "catalogue", "effets.json"), encoding="utf-8") as f:
            d = json.load(f)
        self.assertGreaterEqual(len(d["effets"]), 20)
        v = commun.video_test(self.d, "cat.mp4", duree=1, taille="320x180")
        for k, e in d["effets"].items():
            for l in ("fr", "en", "de", "es", "it"):
                self.assertTrue(e["nom"].get(l) and e["description"].get(l), f"{k} : {l} manquant")
            r = subprocess.run([moteur.ffmpeg(), "-v", "error", "-i", v, "-vf", e["ffmpeg"].replace("{largeur}", "320").replace("{hauteur}", "180"), "-f", "null", "-"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{k} : {r.stderr[-200:]}")
        E.catalogue_en_ligne(reseau=False)
        self.assertIn("web_vhs", E.CATALOGUE)
        self.assertEqual(E.filtre_en_ligne("web_negatif"), "negate")
        self.assertEqual(CL.localise({"fr": "Bonjour", "en": "Hello"}) in ("Bonjour", "Hello"), True)

    def test_catalogue_effets_ia_en_ligne(self):
        from app import effets_ia as EI
        en_ligne = [e for e in EI.tous() if e.get("en_ligne")]
        self.assertGreaterEqual(len(en_ligne), 10)
        for e in en_ligne:
            self.assertTrue(isinstance(e["nom"], str) and e["nom"])
            self.assertIn(e["famille"], EI.FAMILLES)
            self.assertTrue(e["prompt"])

    # ---------------------------------------------------------------- Accueil
    def test_accueil_projets_des_autres_postes_en_gris(self):
        from PySide6.QtCore import Qt
        from app.accueil import PageAccueil
        p = {"recents": [], "recents_dates": {}}
        a = PageAccueil(p)
        recu = []
        a.reprendre.connect(lambda m, f: recu.append((m, f)))
        fichier = {"chemin": "/ailleurs/Vacances.philcut", "nom": "Vacances.philcut"}
        a.rafraichir([("Portable", "2026-11-05T20:10", 1)], [("Portable", "2026-11-05T20:10", [fichier, {"chemin": "/x/a.mp4", "nom": "a.mp4"}])])
        textes = [a.liste.item(i).text() for i in range(a.liste.count())]
        self.assertEqual(len(textes), 1, textes)                     # seul le projet .philcut, pas la vidéo
        it = a.liste.item(0)
        self.assertIn("Vacances", it.text())
        self.assertIn("Portable", it.text())
        self.assertEqual(it.foreground().color().name(), "#a0a0a4")    # gris
        a._activer(it)
        self.assertEqual(recu, [("Portable", [fichier])])
        a.rafraichir()                                               # un rafraîchissement simple garde la liste des autres postes
        self.assertEqual(a.liste.count(), 1)

    # ---------------------------------------------------------------- tampons
    def test_tampons_maison_images(self):
        from app import tampons as T
        self.assertGreaterEqual(len(T.MAISON), 10)
        for k, (nom, desc, mots, d) in T.MAISON.items():
            a, b = T.image_maison(k, d * 0.3, 320, 180), T.image_maison(k, d * 0.8, 320, 180)
            self.assertNotEqual(a, b, f"{k} : le tampon ne bouge pas")
            self.assertIn(k, T._SONS)

    def test_tampon_maison_fabrique_avec_son(self):
        from app import tampons as T
        e = T.fabriquer_maison(self.params, "idee", 320, 180)
        f = T.chemin(self.params, e)
        r = subprocess.run([moteur.ffprobe(), "-v", "error", "-show_streams", "-of", "json", f], capture_output=True, text=True)
        genres = {s["codec_type"] for s in json.loads(r.stdout)["streams"]}
        self.assertEqual(genres, {"video", "audio"})
        self.assertAlmostEqual(float(moteur.sonder(f)["duree"]), 2.0, delta=0.25)
        self.assertEqual(e["source"], "maison")
        self.assertIn(e["id"], [x["id"] for x in T.charger(self.params)])
        self.assertTrue(T.vignette(self.params, e))
        e2 = T.fabriquer_maison(self.params, "idee", 320, 180)      # déjà fabriqué : même entrée, pas de doublon
        self.assertEqual(e2["id"], e["id"])
        self.assertNotIn("idee", T.maison_manquants(self.params, 320, 180))

    def test_mes_clips_extrait_recherche_retrait(self):
        from app import tampons as T
        v = commun.video_test(self.d, "reaction.mp4", duree=4)
        e = T.ajouter_fichier(self.params, v, "Ma réaction", ["humour", "surprise"], debut=1.0, duree=1.5)
        self.assertAlmostEqual(float(e["duree"]), 1.5, delta=0.2)
        self.assertEqual([x["id"] for x in T.chercher_local(T.charger(self.params), "SURPRISE")], [e["id"]])
        self.assertEqual(T.chercher_local(T.charger(self.params), "reaction")[0]["id"], e["id"])      # sans accents
        T.modifier(self.params, e["id"], nom="Réaction", mots=["gag"])
        self.assertEqual([x["nom"] for x in T.charger(self.params) if x["id"] == e["id"]], ["Réaction"])
        T.retirer(self.params, e["id"])
        self.assertNotIn(e["id"], [x["id"] for x in T.charger(self.params)])

    def test_recherche_wikimedia_filtre_les_licences(self):
        from app import tampons as T
        rep = {"query": {"pages": {
            "1": {"index": 1, "title": "File:Applause crowd.webm", "imageinfo": [{"mime": "video/webm", "url": "https://upload.example/a.webm",
                  "descriptionurl": "https://commons.example/a", "thumburl": "", "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"},
                                                                                              "Artist": {"value": "<a href='x'>Jane Doe</a>"}}}]},
            "2": {"index": 2, "title": "File:Pas libre.webm", "imageinfo": [{"mime": "video/webm", "url": "https://upload.example/b.webm",
                  "extmetadata": {"LicenseShortName": {"value": "CC BY-NC 2.0"}}}]},
            "3": {"index": 3, "title": "File:Image.jpg", "imageinfo": [{"mime": "image/jpeg", "url": "https://upload.example/c.jpg",
                  "extmetadata": {"LicenseShortName": {"value": "CC0"}}}]}}}}
        ancien = T._json
        T._json = lambda url, entetes=None, timeout=20: rep
        try:
            res = T.chercher_wikimedia("applause")
        finally:
            T._json = ancien
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["auteur"], "Jane Doe")
        self.assertEqual(res[0]["titre"], "Applause crowd")
        self.assertIn("CC BY-SA", T.credit(res[0]))

    def test_clefs_pixabay_pexels_suivent_sur_les_autres_postes(self):
        from app.config import Parametres
        from app import coffre, reglages
        pa = Parametres()
        drive = tempfile.mkdtemp()
        pa["drive"] = drive
        pa["drive_compte"] = ""
        pa["synchro_secrets"] = True
        coffre.enregistrer(reglages.PHRASE, "une phrase de test")
        coffre.enregistrer("pixabay_cle", "cle-pixabay-essai")
        coffre.enregistrer("pexels_cle", "cle-pexels-essai")
        reglages.synchro_secrets_auto(pa)
        self.assertTrue(os.path.exists(reglages.chemin_secrets(pa)))
        with open(reglages.chemin_secrets(pa), "rb") as f:
            self.assertNotIn(b"cle-pixabay-essai", f.read())          # chiffré, jamais en clair sur le Drive
        # « autre poste » : la clef n'y est pas encore, elle est reprise
        coffre.supprimer("pixabay_cle")
        coffre.supprimer("pexels_cle")
        libelles = [x["libelle"] for x in reglages.secrets_nouveaux(pa, "une phrase de test")]
        self.assertTrue(any("Pixabay" in l for l in libelles), libelles)
        self.assertGreaterEqual(reglages.synchro_secrets_auto(pa), 2)
        self.assertEqual(coffre.lire("pixabay_cle"), "cle-pixabay-essai")
        self.assertEqual(coffre.lire("pexels_cle"), "cle-pexels-essai")
        coffre.enregistrer(reglages.PHRASE, "mauvaise phrase")           # mauvaise phrase : rien, sans erreur
        self.assertEqual(reglages.synchro_secrets_auto(pa), 0)
        coffre.supprimer(reglages.PHRASE)
        coffre.supprimer("pixabay_cle")
        coffre.supprimer("pexels_cle")

    def test_traduction_des_recherches(self):
        from app import traduction_recherche as TR
        t, comment, manque = TR.en_anglais("Applaudissements de la foule", "fr", reseau=False)
        self.assertIn("applause", t)
        self.assertIn("crowd", t)
        t, comment, manque = TR.en_anglais("coucher de soleil sur la mer", "fr", reseau=False)
        self.assertIn("sunset", t)
        self.assertIn("sea", t)
        self.assertTrue(manque)                                      # « sur », « la » : signalés
        self.assertIn("anglais", TR.message("coucher de soleil sur la mer", (t, comment, manque)))
        self.assertEqual(TR.en_anglais("explosion crowd", "fr", reseau=False)[2], [])   # déjà de l'anglais : rien à signaler
        self.assertEqual(TR.en_anglais("anything", "en")[1], "deja")
        self.assertEqual(TR.en_anglais("Zeitlupe", "de", reseau=False)[0], "slow motion")
        self.assertEqual(TR.en_anglais("incroyable", "fr", reseau=False)[0], "amazing")
        # réponse du service : les souvenirs approximatifs (« Business ») sont écartés, la traduction automatique gardée
        rep = {"responseStatus": 200, "responseData": {"translatedText": "Business", "match": 0.3},
               "matches": [{"segment": "incroyable", "translation": "Business", "match": 0.3, "created-by": "x"},
                           {"segment": "incroyable", "translation": "incredible", "match": 0.85, "created-by": "MT!"}]}
        self.assertEqual(TR._meilleure(rep, "incroyable")[0], "incredible")
        self.assertIsNone(TR._meilleure({"responseStatus": 200, "responseData": {"translatedText": "Business", "match": 0.3}}, "incroyable"))

    def test_extraits_de_films_dans_le_navigateur(self):
        from app import tampons as T
        self.assertEqual(T.url_extrait("clipcafe", "my precious"), "https://clip.cafe/s/my+precious/")
        self.assertEqual(T.url_extrait("yarn", "thank you"), "https://yarn.co/yarn-find?text=thank%20you")
        self.assertIn("playphrase.me/#/search?q=hello", T.url_extrait("playphrase", "hello"))

    def test_sons_de_films_et_tampon_sonore(self):
        from app import tampons as T
        u = T.url_extrait("voicy", "thank you")
        self.assertTrue(u.startswith("https://duckduckgo.com/?q="))
        self.assertIn("site%3Avoicy.network", u)
        m = commun.musique_test(self.d, "replique.mp3", duree=2)
        e = T.ajouter_fichier(self.params, m, "Réplique", ["film"])
        self.assertEqual(e["genre"], "son")
        self.assertTrue(e["fichier"].endswith(".mp3"))
        e2 = T.ajouter_fichier(self.params, m, "Réplique courte", [], debut=0.5, duree=1.0)
        self.assertTrue(e2["fichier"].endswith(".m4a"))
        self.assertAlmostEqual(float(e2["duree"]), 1.0, delta=0.15)
        T.retirer(self.params, e["id"])
        T.retirer(self.params, e2["id"])

    def test_ecran_de_lancement(self):
        from app.demarrage import EcranDemarrage
        e = EcranDemarrage("9.9.9")
        e.etape("Chargement des effets…", 0.4)
        e.etape("Retour en arrière", 0.2)                            # la barre ne recule jamais
        self.assertAlmostEqual(e.fraction, 0.4)
        img = e.grab().toImage()
        self.assertGreater(img.width(), 400)
        e.close()

    def test_progression_de_la_mise_a_jour(self):
        from app.fenetre import progression_maj
        recu = []

        class Faux:
            def avancer(self, f, t=""):
                recu.append((f, t))
        suivre = progression_maj(Faux())
        suivre(5_000_000, 20_000_000)                                 # mise_a_jour.recuperer donne (fait, total)
        suivre(3_000_000)
        self.assertAlmostEqual(recu[0][0], 0.25)
        self.assertIn("20", recu[0][1])
        self.assertEqual(recu[1][0], 0.0)

    def test_tout_mot_de_passe_a_son_oeil(self):
        """Règle : chaque champ de mot de passe, phrase ou clef se visualise (œil à droite du champ)."""
        import re
        manque = []
        for f in os.listdir(os.path.join(RACINE, "app")):
            if not f.endswith(".py") or f == "widgets.py":
                continue
            with open(os.path.join(RACINE, "app", f), encoding="utf-8") as g:
                lignes = g.read().splitlines()
            for i, l in enumerate(lignes):
                m = re.search(r"(\S+)\.setEchoMode\(QLineEdit\.Password\)", l)
                if m:
                    suite = "\n".join(lignes[i:i + 4])
                    if f"oeil({m.group(1)})" not in suite and "addAction(icone(\"oeil\"" not in suite:
                        manque.append(f"{f}:{i + 1}")
        self.assertEqual(manque, [])

    def test_preferences_clefs_pixabay_pexels(self):
        from app.config import Parametres
        from app import coffre, tampons as T
        from app.preferences import DialoguePreferences
        from PySide6.QtWidgets import QLineEdit, QWidget
        pa = Parametres()
        pa["synchro_secrets"] = False                     # pas de fenêtre de phrase secrète pendant ce test

        class FauxFen(QWidget):
            def telecharger_pack(self, k): pass
        fen = FauxFen()
        d = DialoguePreferences(fen, pa)
        self.assertIn("pixabay", d.clefs_banques)
        self.assertEqual(d.clefs_banques["pexels"].echoMode(), QLineEdit.Password)
        self.assertTrue(d.clefs_banques["pexels"].actions())               # l'œil
        d.clefs_banques["pexels"].setText("cle-pexels-pref")
        d.valider()
        self.assertEqual(coffre.lire(T.CLEFS["pexels"]), "cle-pexels-pref")
        coffre.supprimer(T.CLEFS["pexels"])

    def test_menu_musiques_sans_gel(self):
        """Gros dossier de musiques : le menu se construit sans lire les étiquettes (lues ensuite en arrière-plan)."""
        import shutil
        from app import musiques as MU
        d = tempfile.mkdtemp()
        m = commun.musique_test(d, "base.mp3", duree=1)
        for i in range(300):
            shutil.copy(m, os.path.join(d, f"Artiste - Titre {i}.mp3"))
        t0 = time.time()
        liste = MU.morceaux([d], rapide=True, delai=3)
        self.assertLess(time.time() - t0, 2.0)
        self.assertEqual(len(liste), 301)
        self.assertEqual(liste[5]["artiste"], "Artiste")               # tiré du nom en attendant
        self.assertGreater(MU.lire_en_fond(liste), 0)
        MU._LECTURE["fil"].join(120)
        self.assertFalse(any(x.get("a_lire") for x in MU.morceaux([d], rapide=True)))

    def test_pixabay_sans_clef_explique(self):
        from app import tampons as T, coffre
        coffre.supprimer(T.CLEFS["pixabay"])
        with self.assertRaises(T.ErreurTampon):
            T.chercher("pixabay", "applause")

    def test_inserer_tampon_et_credit(self):
        from app.config import Parametres
        from app import tampons as T, musiques
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        v = commun.video_test(self.d, "film.mp4", duree=4)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.ajouter_a_la_timeline(m["id"])
        ed.aller_a(2.0)
        app.processEvents()
        # un clip « téléchargé » : copie locale avec son crédit, comme le ferait telecharger()
        e = T.ajouter_fichier(ed.params, commun.video_test(self.d, "libre.mp4", duree=2), "Applaudissements")
        with open(os.path.splitext(T.chemin(ed.params, e))[0] + ".credit.txt", "w", encoding="utf-8") as g:
            g.write(T.credit({"titre": "Applause", "auteur": "Jane Doe", "licence": "CC BY 4.0", "source": "wikimedia", "page": "https://x"}) + "\n")
        from app.dialogues_tampons import DialogueTampons
        dl = DialogueTampons(ed)
        self.assertEqual(dl.onglets.count(), 3)
        items = [dl.liste.item(i) for i in range(dl.liste.count()) if dl.liste.item(i).data(0x0100)]
        dl.liste.setCurrentItem([i for i in items if i.data(0x0100)["id"] == e["id"]][0])
        app.processEvents()
        self.assertIn("Jane Doe", T.credit({"titre": "Applause", "auteur": "Jane Doe", "licence": "CC BY 4.0", "source": "wikimedia"}))
        dl.inserer()
        vids = sorted(ed.projet.clips_piste("video"), key=lambda c: c["debut"])
        self.assertEqual(len(vids), 3)                               # plan coupé à 2 s, tampon au milieu
        self.assertAlmostEqual(vids[1]["debut"], 2.0, delta=0.05)
        self.assertAlmostEqual(vids[2]["debut"], 4.0, delta=0.15)
        self.assertTrue(any("Jane Doe" in c for c in musiques.credits_projet(ed.projet)))
        # onglet maison : bouton « créer les manquants » à jour
        dl2 = DialogueTampons(ed, 1)
        self.assertIn(str(len(T.maison_manquants(ed.params, 1920, 1080))), dl2.b_tous.text())
        dl2.reject()
        son = commun.musique_test(self.d, "ah.mp3", duree=2)
        c = ed.poser_son(son, 1.0, "Réplique")
        self.assertNotEqual(c["piste"], "video")
        self.assertEqual(len(ed.projet.clips_piste("video")), 3)       # le film n'est pas décalé
        ed.projet.annuler()
        ed.projet.annuler()
        self.assertEqual(len(ed.projet.clips_piste("video")), 1)       # annulable


if __name__ == "__main__":
    unittest.main()
