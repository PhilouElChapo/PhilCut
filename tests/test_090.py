"""0.9.0 : fenêtre « Mes musiques » (recherche, classement, pose), phrases de l'Atelier IA traduites en anglais, clip
plein cadre posé au-dessus (effet IA) visible à la lecture brute."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(tache, delai=60):
    t0 = time.time()
    while tache is not None and tache.isRunning() and time.time() - t0 < delai:
        app.processEvents()
        time.sleep(0.05)
    for _i in range(10):
        app.processEvents()


class Test090(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()

    def test_phrases_du_catalogue_restent_en_anglais(self):
        from app import effets_ia as EI, traduction_recherche as TR
        for e in EI.EFFETS:
            if e.get("prompt"):
                t, comment, manque = TR.phrase_en_anglais(e["prompt"])
                self.assertEqual(comment, "deja", f"{e['id']} : « {e['prompt']} » pris pour une autre langue")
        self.assertEqual(TR.langue_probable("une femme sur la plage"), "fr")
        self.assertEqual(TR.langue_probable("ein Hund mit der Katze"), "de")
        self.assertEqual(TR.langue_probable("una casa con el perro"), "es")
        self.assertEqual(TR.langue_probable("a dog in the snow"), "en")
        self.assertEqual(TR.phrase_en_anglais("une femme sur la plage au coucher de soleil")[0], "a woman on the beach at the sunset")

    def test_longue_phrase_traduite_par_morceaux(self):
        from app import traduction_recherche as TR
        vus = []
        vrai = TR.en_anglais
        TR.en_anglais = lambda t, l=None, r=True: (vus.append((t, l)) or ("X" * 10, "service", []))
        try:
            longue = ", ".join(["une maison rouge dans la forêt avec des fleurs"] * 20)
            t, comment, manque = TR.phrase_en_anglais(longue)
        finally:
            TR.en_anglais = vrai
        self.assertGreater(len(vus), 1)
        self.assertTrue(all(len(m) <= 400 and l == "fr" for m, l in vus))
        self.assertEqual(comment, "service")

    def test_clip_plein_cadre_au_dessus_se_voit_a_la_lecture(self):
        from app.projet import Projet
        from app import moteur
        p = Projet()
        v = commun.video_test(self.d, "base.mp4", duree=4)
        w = commun.video_test(self.d, "ia.mp4", duree=1)
        mb = p.ajouter_media(v, moteur.sonder(v))
        mi = p.ajouter_media(w, moteur.sonder(w))
        base = p.ajouter_clip(mb["id"], "video", 0.0, 0.0, 4.0)
        piste = p.ajouter_piste("video")
        ci = p.ajouter_clip(mi["id"], piste, 1.0, 0.0, 1.0)
        ci["incrust"] = {"echelle": 1.0, "x": 0.5, "y": 0.5, "opacite": 1.0}
        self.assertIs(p.plan_visible(1.5), ci)
        self.assertIs(p.plan_visible(3.0), base)
        ci["incrust"]["echelle"] = 0.4                # image dans l'image : la base reste la lecture brute
        self.assertIs(p.plan_visible(1.5), base)
        ci["incrust"]["echelle"] = 1.0
        p.d["pistes_masquees"] = [piste]
        self.assertIs(p.plan_visible(1.5), base)

    def test_fenetre_mes_musiques(self):
        from app.config import Parametres
        from app.dialogues_mes_musiques import DialogueMesMusiques
        racine = os.path.join(self.d, "Musiques")
        for i in range(40):
            dd = os.path.join(racine, f"Album {i:02d}")
            os.makedirs(dd, exist_ok=True)
            for j in range(12):
                open(os.path.join(dd, f"Artiste {i % 7} - Morceau {i:02d}-{j:02d}.mp3"), "w").close()
        commun.musique_test(os.path.join(racine, "Album 00"), "Balade du soir.mp3", duree=2)
        pa = Parametres()
        pa["musiques_dossier"] = racine
        pa["musiques_classement"] = "dossier"
        dl = DialogueMesMusiques(None, pa)
        dl.show()
        attendre(dl.tache)
        self.assertGreaterEqual(len(dl.liste), 481)
        self.assertGreaterEqual(dl.arbre.topLevelItemCount(), 40)          # un groupe par dossier, repliés
        dl.cherche.setText("balade soir")
        dl.remplir()
        from PySide6.QtWidgets import QTreeWidgetItemIterator
        trouves, it = [], QTreeWidgetItemIterator(dl.arbre)
        while it.value():
            if dl._chemin(it.value()):
                trouves.append(it.value())
            it += 1
        self.assertEqual(len(trouves), 1)
        self.assertIn("1 morceau", dl.etat.text())
        dl.classement.setCurrentIndex(dl.classement.findData("titre"))
        self.assertEqual(pa["musiques_classement"], "titre")
        self.assertEqual(dl.arbre.topLevelItemCount(), 1)                   # tout, par titre : liste à plat
        dl.arbre.setCurrentItem(dl.arbre.topLevelItem(0))
        dl.poser(dl.arbre.currentItem())
        self.assertTrue(dl.chemin.endswith("Balade du soir.mp3"))

    def test_image_ia_posee_au_dessus_et_volet_agrandi(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["synchro_secrets"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import moteur
        f = Fenetre()
        f.resize(1400, 900)
        f.show()
        ed = f.nouveau_projet("16:9")
        v = commun.video_test(self.d, "film.mp4", duree=4)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.ajouter_a_la_timeline(m["id"])
        img = os.path.join(self.d, "ia.png")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "color=c=red:s=320x180", "-frames:v", "1", img])
        c = ed.poser_au_dessus(img, 1.0, "Image IA", 3.0)
        self.assertNotEqual(c["piste"], "video")
        self.assertEqual(len(ed.projet.clips_piste("video")), 1)            # le film n'est pas coupé
        self.assertIs(ed.projet.plan_visible(2.0), c)
        # la timeline peut grandir : le volet de droite ne bloque plus la hauteur
        self.assertLess(ed.split_v.widget(0).minimumSizeHint().height(), 300)
        # volet ouvert dans une fenêtre : son contenu est visible (plus de fenêtre noire)
        ed.volet.setCurrentIndex(2)
        w = ed.volet.currentWidget()
        ed.agrandir_volet()
        app.processEvents()
        self.assertTrue(w.isVisible())
        # analyse et proposition : ce que fait la machine se voit dans le volet
        ed.proposition.niveau.setCurrentIndex(ed.proposition.niveau.findData("recettes"))
        ed.analyser()
        self.assertFalse(ed.proposition.suivi.isHidden())
        self.assertTrue(ed.proposition.suivi_lbl.text())
        t = ed.taches[-1]
        attendre(t, 120)
        self.assertTrue(ed.proposition.suivi.isHidden())
        self.assertTrue(ed.proposition.resume.text())
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
