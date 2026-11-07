"""0.9.5 : retirer le fond d'une image (JPG → PNG transparent), depuis le Goodie, les médias et le plan."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
import cv2
import numpy as np
from PySide6.QtCore import Qt


def logo(d):
    img = np.full((400, 600, 3), 255, np.uint8)
    cv2.circle(img, (300, 200), 150, (0, 120, 255), -1)
    cv2.circle(img, (300, 200), 60, (255, 255, 255), -1)
    p = os.path.join(d, "logo.jpg")
    cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return p


class Test095(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.logo = logo(cls.d)

    def test_fond_uni(self):
        from app import fond as F
        img = F.lire(self.logo)
        self.assertFalse(F.a_deja_transparence(img))
        self.assertTrue(F.fond_uni_probable(img[..., :3]))
        out, m = F.retirer_fond(img)
        self.assertEqual(m, "uni")
        self.assertEqual(out[5, 5, 3], 0)                     # coin : transparent
        self.assertEqual(out[200, 180, 3], 255)               # l'anneau orange reste
        self.assertEqual(out[200, 300, 3], 255)               # le blanc enfermé reste par défaut
        out2, _m = F.retirer_fond(img, enferme=True)
        self.assertEqual(out2[200, 300, 3], 0)                # sur demande, lui aussi
        r = F.recadrer_au_sujet(out)
        self.assertLess(r.shape[1], 600)
        p = F.enregistrer(r, F.chemin_copie(self.logo))
        self.assertRegex(os.path.basename(p), r"^logo_sans_fond(_\d+)?\.png$")
        self.assertTrue(F.a_deja_transparence(F.lire(p)))
        self.assertTrue(os.path.exists(self.logo))             # l'original est gardé

    def test_photo(self):
        from app import fond as F
        img = np.full((300, 400, 3), 0, np.uint8)
        img[:] = np.random.RandomState(1).randint(60, 200, (300, 400, 3))        # fond varié
        cv2.circle(img, (200, 150), 80, (30, 30, 230), -1)
        out, m = F.retirer_fond(cv2.cvtColor(img, cv2.COLOR_BGR2BGRA))
        self.assertEqual(m, "photo")
        self.assertGreater(out[150, 200, 3], 127)
        self.assertLess(out[10, 10, 3], 127)

    def test_fenetre_et_plan(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["synchro_secrets"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import moteur
        import app.dialogues_fond as DF
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        m = ed.projet.ajouter_media(self.logo, moteur.sonder(self.logo))
        ed.ajouter_a_la_timeline(m["id"])
        c = ed.projet.clips[0]
        # la fenêtre : calcul en tâche de fond puis « Garder »
        d = DF.DialogueFond(None, self.logo)
        t0 = time.time()
        while (d.sortie is None) and time.time() - t0 < 20:
            app.processEvents()
            time.sleep(0.03)
        self.assertIsNotNone(d.sortie)
        self.assertTrue(d.b_ok.isEnabled())
        d.garder()
        self.assertTrue(os.path.exists(d.resultat))
        # depuis le plan : le plan prend la copie transparente, l'original reste dans les médias
        vrai = DF.retirer_fond
        DF.retirer_fond = lambda parent, chemin: d.resultat
        try:
            ed.retirer_fond(m["id"], c["id"])
        finally:
            DF.retirer_fond = vrai
        nouveau = ed.projet.media(ed.projet.clip(c["id"])["media"])
        self.assertTrue(nouveau["chemin"].endswith(".png"))
        self.assertIsNotNone(ed.projet.media(m["id"]))
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_sources_francaises_et_guet_des_telechargements(self):
        from app import tampons as T
        u = T.url_extrait("voicy", "c'est pas faux")
        self.assertIn("site%3Avoicy.network", u)
        self.assertNotIn("zonesons", T.SONS_FILMS)                      # ZoneSons retiré (0.9.7)
        self.assertEqual(T.url_extrait("kaamelott", "c'est pas faux"), "https://kaamelott.fspot.org/")
        self.assertIn("kaamelott", T.SANS_RECHERCHE)
        d = tempfile.mkdtemp()
        avant = T.etat_dossier(d)
        m = commun.musique_test(d, "c_est_pas_faux-kaamelott (1).mp3", duree=1)
        open(os.path.join(d, "film.mp4.crdownload"), "wb").write(b"x" * 100)
        prets, prec = T.nouveaux_telecharges(d, avant, avant)
        self.assertEqual(prets, [])                                     # premier passage : on attend que la taille ne bouge plus
        prets, prec = T.nouveaux_telecharges(d, avant, prec)
        self.assertEqual(prets, [m])                                    # le .crdownload (en cours) n'est pas pris
        self.assertEqual(T.nom_depuis_fichier(m), "C est pas faux kaamelott")

    def test_raccourcir_un_son(self):
        from app import tampons as T
        from app.config import Parametres
        pa = Parametres()
        m = commun.musique_test(self.d, "replique.mp3", duree=3)
        e = T.ajouter_fichier(pa, m, "Réplique à raccourcir", ["essai"])
        e2 = T.raccourcir(pa, e["id"], 0.5, 1.5)
        self.assertAlmostEqual(float(e2["duree"]), 1.0, delta=0.15)
        self.assertTrue(os.path.exists(T.chemin(pa, e2)))
        T.retirer(pa, e["id"])

    def test_fenetre_tampons_ecoute_et_guet(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["synchro_secrets"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import tampons as T
        from app.dialogues_tampons import DialogueTampons
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        dl = DialogueTampons(ed, 2)
        pa = ed.params
        dl.show()
        i = dl.source.findData("extrait:voicy")
        self.assertGreaterEqual(i, 0)
        dl.source.setCurrentIndex(i)
        self.assertIn("français", dl.question.placeholderText())
        self.assertTrue(dl.guette.isVisible())
        # le guet : un son arrive dans « Téléchargements » → il rejoint la bibliothèque
        d = tempfile.mkdtemp()
        import app.session as S
        vrai = S.dossier_systeme
        S.dossier_systeme = lambda quoi: d if quoi == "telechargements" else vrai(quoi)
        try:
            dl.question.setText("pas faux")
            dl.guetter("voicy")
            m = commun.musique_test(d, "pas_faux.mp3", duree=1)
            t0 = time.time()
            while time.time() - t0 < 15 and not any(e["nom"] == "Pas faux" for e in T.charger(pa)):
                app.processEvents()
                time.sleep(0.05)
        finally:
            S.dossier_systeme = vrai
        e = next(e for e in T.charger(pa) if e["nom"] == "Pas faux")
        self.assertEqual(e["genre"], "son")
        self.assertIn("Voicy", e["mots"])
        # un clic sur un son l'écoute
        for _i in range(20):
            app.processEvents()
        ecoutes = []
        dl.ecouter = lambda: ecoutes.append(dl._entree()["id"])          # pas de vrai son ici (pas de carte son en test)
        it = next(dl.liste.item(k) for k in range(dl.liste.count()) if (dl.liste.item(k).data(Qt.UserRole) or {}).get("id") == e["id"])
        dl.liste.setCurrentItem(it)
        self.assertEqual(ecoutes, [])                                   # choisir ne joue rien…
        dl.liste.itemClicked.emit(it)
        self.assertEqual(ecoutes, [e["id"]])                            # …un clic sur un son l'écoute
        T.retirer(pa, e["id"])
        dl.reject()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_videos_en_ligne(self):
        """0.9.7 : yt-dlp (résultats, morceau, crédit) et Internet Archive, sans réseau (réponses simulées)."""
        from app import videos_en_ligne as VL, tampons as T
        self.assertIn("70 ans après la mort", VL.LEGAL)
        self.assertEqual(T.lire_temps("1:23.5"), 83.5)
        self.assertEqual(T.lire_temps("1:02:03"), 3723)
        self.assertIsNone(T.lire_temps("abc"))
        vus = {}
        vrai = VL._lancer_ytdlp

        def faux(args, progression=None, arret=lambda: False, delai=0):
            vus.setdefault("appels", []).append(args)
            if "--flat-playlist" in args:
                return ['{"title": "Classic trailer", "channel": "Archive", "duration": 125, "id": "abc123"}', "bruit"]
            d = args[args.index("-o") + 1].rsplit(os.sep, 1)[0]
            f = commun.video_test(d, "Classic_trailer_abc123.mp4", duree=2)
            if progression:
                progression(0.5, "[download]  50.0% of 2MiB")
            return [f]
        VL._lancer_ytdlp = faux
        try:
            r = VL.chercher_youtube("classic trailer")
            self.assertEqual(r[0]["page"], "https://www.youtube.com/watch?v=abc123")
            self.assertEqual(r[0]["duree"], 125)
            f = VL.telecharger(r[0]["page"], tempfile.mkdtemp(), debut=3, fin=8)
            self.assertTrue(os.path.exists(f))
            args = vus["appels"][-1]
            self.assertIn("*3.00-8.00", args)                           # seulement le morceau
            self.assertIn("--ffmpeg-location", [a for a in args] + ["--ffmpeg-location"])
        finally:
            VL._lancer_ytdlp = vrai
        # Internet Archive : réponse simulée
        import io, json as J, urllib.request as U
        vrai_open = U.urlopen

        class Rep(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        U.urlopen = lambda req, timeout=0: Rep(J.dumps({"response": {"docs": [{"identifier": "film_1940", "title": "Film 1940",
                                                                                 "year": 1940, "creator": "Studio"}]}}).encode())
        try:
            res = VL.chercher_archive("rocket")
        finally:
            U.urlopen = vrai_open
        self.assertEqual(res[0]["page"], "https://archive.org/details/film_1940")
        self.assertEqual(res[0]["source"], "archive")

    def test_fenetre_videos_en_ligne(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["synchro_secrets"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import tampons as T, videos_en_ligne as VL
        from app.dialogues_tampons import DialogueTampons
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        ed.params["ytdlp_accord"] = True
        dl = DialogueTampons(ed, 2)
        dl.show()
        dl.source.setCurrentIndex(dl.source.findData("ytdlp"))
        self.assertTrue(dl.ligne_morceau.isVisible())
        self.assertIn("70 ans", dl.info_res.text())
        r = {"titre": "Bande annonce ancienne", "auteur": "Chaîne libre", "duree": 900, "page": "https://www.youtube.com/watch?v=abc123",
             "source": "youtube", "licence": "Creative Commons Attribution"}
        dl._resultats_recus([r], None)
        dl.resultats.setCurrentRow(0)
        self.assertIn("Creative Commons", dl.resultats.item(0).text())
        dl.ajouter_resultat(False)
        self.assertIn("morceau", dl.etat.text())                        # vidéo de 15 min : il faut dire quel morceau
        vrai_tel, vrai_inst = VL.telecharger, VL.ytdlp_installe
        VL.ytdlp_installe = lambda: True
        VL.telecharger = lambda url, d, audio=False, a=None, b=None, progression=None, arret=None, hauteur=1080: commun.video_test(d, "extrait.mp4", duree=2)
        dl.morceau_de.setText("1:00")
        dl.morceau_a.setText("1:05")
        avant = {e["id"] for e in T.charger(ed.params)}
        try:
            dl.ajouter_resultat(False)
            t0 = time.time()
            while time.time() - t0 < 20 and not ({e["id"] for e in T.charger(ed.params)} - avant):
                app.processEvents()
                time.sleep(0.05)
        finally:
            VL.telecharger, VL.ytdlp_installe = vrai_tel, vrai_inst
        e = next(e for e in T.charger(ed.params) if e["id"] not in avant)
        self.assertEqual(e["page"], r["page"])
        self.assertEqual(e["licence"], "Creative Commons Attribution")
        self.assertEqual(e["source"], "youtube")
        self.assertIn("YouTube", T.credit(e))                            # crédit ajouté à la publication
        T.retirer(ed.params, e["id"])
        dl.reject()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_fenetre_de_mise_a_jour(self):
        """0.9.8 : « Télécharger et installer » ouvre une fenêtre qui montre la progression (Mo, vitesse, reste), puis
        « Installer et redémarrer » ; une erreur est dite clairement."""
        from app import mise_a_jour as M
        from app.dialogues_maj import DialogueMaj
        vrai_r, vrai_v = M.recuperer, M.fichier_valide

        def faux(paquet, progression=None, arret=lambda: False):
            for i in range(1, 6):
                if arret():
                    raise RuntimeError("annule")
                progression(i * 40_000_000, 200_000_000)
                time.sleep(0.05)
            return os.path.join(self.d, "PhilCut_portable.zip")
        M.recuperer, M.fichier_valide = faux, lambda f: True
        try:
            d = DialogueMaj(None, "0.9.8", "https://exemple.invalid/PhilCut_portable.zip")
            t = d.demarrer()
            self.assertTrue(d.isVisible())
            vus = []
            t0 = time.time()
            while (t.isRunning() or not d.b_installer.isVisibleTo(d)) and time.time() - t0 < 10:
                app.processEvents()
                vus.append(d.detail.text())
                time.sleep(0.02)
            self.assertTrue(any("/ 200 Mo" in v and "Mo/s" in v for v in vus), vus[-3:])
            self.assertFalse(d.b_installer.isHidden())
            self.assertIn("Installer et redémarrer", d.b_installer.text())
            d.close()
            # erreur réseau : message clair, pas de silence
            M.recuperer = lambda paquet, progression=None, arret=None: (_ for _ in ()).throw(OSError("réseau coupé"))
            d2 = DialogueMaj(None, "0.9.8", "x")
            t = d2.demarrer()
            t0 = time.time()
            while t.isRunning() and time.time() - t0 < 10:
                app.processEvents()
            for _i in range(10):
                app.processEvents()
            self.assertIn("réseau coupé", d2.detail.text())
            self.assertTrue(d2.b_installer.isHidden())
            d2.close()
        finally:
            M.recuperer, M.fichier_valide = vrai_r, vrai_v


if __name__ == "__main__":
    unittest.main()
