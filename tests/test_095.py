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
        u = T.url_extrait("zonesons", "c'est pas faux")
        self.assertIn("site%3Azonesons.com", u)
        self.assertIn("pas+faux", u)                                    # recherche en français, sans traduction
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
        i = dl.source.findData("extrait:zonesons")
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
            dl.guetter("zonesons")
            m = commun.musique_test(d, "pas_faux.mp3", duree=1)
            t0 = time.time()
            while time.time() - t0 < 15 and not any(e["nom"] == "Pas faux" for e in T.charger(pa)):
                app.processEvents()
                time.sleep(0.05)
        finally:
            S.dossier_systeme = vrai
        e = next(e for e in T.charger(pa) if e["nom"] == "Pas faux")
        self.assertEqual(e["genre"], "son")
        self.assertIn("ZoneSons (films français)", e["mots"])
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


if __name__ == "__main__":
    unittest.main()
