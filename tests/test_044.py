"""0.4.4 : musique (début, fondus, couper à la fin de la vidéo), téléchargements en pause et repris à la session
suivante, dossier de musiques classé par dossier / album / artiste, « Dites-le en clair », flèches courbes et titres
tendance qui tournent avec les images clefs, voix studio (RNNoise), erreurs FFmpeg lisibles, partie jaune effaçable."""
import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur
from app.langue import _
from app.projet import fin_clip


class Test044(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["recents"] = []
        pa.enregistrer()
        from app.fenetre import Fenetre
        cls.d = tempfile.mkdtemp()
        v = commun.video_test(cls.d, "a.mp4", duree=4)
        cls.musique = commun.musique_test(cls.d, "m.mp3", duree=12)
        cls.f = Fenetre()
        cls.f.resize(1366, 768)
        cls.f.show()
        app.processEvents()
        cls.ed = cls.f.nouveau_projet("16:9")
        m = cls.ed.projet.ajouter_media(v, moteur.sonder(v))
        cls.ed.ajouter_a_la_timeline(m["id"])
        cls.ed.ajouter_a_la_timeline(m["id"])           # 8 s de vidéo
        mm = cls.ed.projet.ajouter_media(cls.musique, moteur.sonder(cls.musique))
        cls.mus = cls.ed.ajouter_a_la_timeline(mm["id"], "audio", 0.0)
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.ed.projet.modifie = False
        cls.ed.catalogue.fermer()
        cls.f.attendre_taches()
        cls.f.close()

    # ---------------------------------------------------------------- musique
    def test_couper_musique_fin_video(self):
        ed = self.ed
        c = ed.projet.clips_piste("audio")[0]                     # (l'annulation recrée les objets du projet)
        fin_v = max(fin_clip(x) for x in ed.projet.clips_piste("video"))
        self.assertGreater(fin_clip(c), fin_v + 1)
        ed.couper_son_fin(c["id"])
        self.assertAlmostEqual(fin_clip(c), fin_v, places=2)
        self.assertGreater(c.get("fondu_sortie", 0), 0)
        ed.projet.annuler()
        self.assertGreater(fin_clip(ed.projet.clip(c["id"])), fin_v + 1)                # annulable

    def test_fondus_et_debut(self):
        from app.export import fondus_audio
        c = {"fondus": True}
        self.assertIn("afade=t=in:st=0:d=0.800", fondus_audio(c, 10))
        c.update(fondu_entree=0.0, fondu_sortie=3.0)
        f = fondus_audio(c, 10)
        self.assertNotIn("t=in", f)
        self.assertIn("afade=t=out:st=7.000:d=3.000", f)
        self.assertEqual(fondus_audio({"fondus": False}, 10), "")
        # l'Inspecteur montre la rubrique son pour un plan de musique
        ed = self.ed
        cid = ed.projet.clips_piste("audio")[0]["id"]
        ed.timeline.selectionner(cid)
        ed.inspecteur.montrer_clip(cid)
        app.processEvents()
        from PySide6.QtWidgets import QGroupBox
        titres = [g.title() for g in ed.inspecteur.findChildren(QGroupBox)]
        self.assertTrue(any("fondus" in t for t in titres), titres)

    def test_export_avec_fondus(self):
        from app.export import Exportateur
        ed = self.ed
        c = ed.projet.clips_piste("audio")[0]
        c["fondu_entree"], c["fondu_sortie"] = 1.5, 2.5
        sortie = os.path.join(self.d, "sortie.mp4")
        ex = Exportateur(ed.projet, sortie, "whatsapp", qualite="allegee", encodeur="libx264", params={})
        ex.lancer()
        self.assertTrue(os.path.getsize(sortie) > 1000)

    # ---------------------------------------------------------------- téléchargements
    def test_pause_reprise_session_suivante(self):
        from unittest import mock
        from app import telechargements as T, packs_ia

        class P(dict):
            def enregistrer(self):
                pass
        pa = P()
        cat = {"m1": {"nom": "Modèle 1", "genre": "vision", "taille": 1000}}
        with mock.patch.object(packs_ia, "modeles", return_value=cat), mock.patch.object(packs_ia, "a_telecharger", return_value=1000), \
                mock.patch.object(packs_ia, "octets_partiels", return_value=400):
            g = T.GestionTelechargements(pa)
            g.travaux.append({"cle": "m1", "nom": "Modèle 1", "taille": 1000, "etat": T.ATTENTE, "fraction": 0.4, "vitesse": 0,
                              "reste": None, "texte": "", "erreur": None})
            g.pause("m1")
            self.assertEqual(g.travaux[0]["etat"], T.PAUSE)
            self.assertEqual(pa["telechargements_non_finis"], ["m1"])
            g2 = T.GestionTelechargements(pa)                 # PhilCut relancé : il revient en pause, à 40 %
            self.assertEqual(len(g2.non_finis()), 1)
            self.assertAlmostEqual(g2.travaux[0]["fraction"], 0.4)
            with mock.patch.object(g2, "_suivant"):
                g2.reprendre()
            self.assertEqual(g2.travaux[0]["etat"], T.ATTENTE)
            fen = T.FenetreTelechargements(None, g2)
            from PySide6.QtWidgets import QHeaderView
            self.assertEqual(fen.table.horizontalHeader().sectionResizeMode(0), QHeaderView.Interactive)
            self.assertEqual(fen.table.horizontalHeaderItem(1).text(), _("Taille"))
            fen.close()

    # ---------------------------------------------------------------- dossier de musiques
    def test_classement_musiques(self):
        from app import musiques as MU
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "Rock"))
        for chemin, titre, artiste, album in ((os.path.join(d, "Rock", "a.mp3"), "Alpha", "Zed", "Album Z"),
                                              (os.path.join(d, "b.mp3"), "Beta", "Amy", "Album A")):
            subprocess.run([moteur.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=d=1", "-metadata", f"title={titre}",
                            "-metadata", f"artist={artiste}", "-metadata", f"album={album}", chemin], check=True)
        liste = MU.morceaux([d])
        self.assertEqual({m["titre"] for m in liste}, {"Alpha", "Beta"})
        self.assertEqual([g for g, _m in MU.classer(liste, "artiste")], ["Amy", "Zed"])
        self.assertEqual(sorted(g for g, _m in MU.classer(liste, "dossier")), sorted([os.path.basename(d), "Rock"]))
        self.assertEqual(len(MU.classer(liste, "titre")[0][1]), 2)
        pa = {"musiques_telechargement": os.path.join(d, "libres")}
        self.assertTrue(MU.dossier(pa).endswith("libres") and os.path.isdir(MU.dossier(pa)))

    def test_recherche_arretable(self):
        from app.dialogues_musiques import DialogueMusiques
        from unittest import mock
        from app import musiques as MU
        import time
        with mock.patch.object(MU, "chercher", side_effect=lambda *a, **k: (time.sleep(0.5), [])[1]):
            dl = DialogueMusiques(None, {"musiques_telechargement": tempfile.mkdtemp()})
            dl.chercher()
            self.assertTrue(dl.b_arret.isVisibleTo(dl))
            dl.arreter_recherche()
            self.assertFalse(dl.b_arret.isVisibleTo(dl))
            self.assertIn("arrêtée", dl.etat.text())
            dl.reject()

    # ---------------------------------------------------------------- « Dites-le en clair »
    def test_commande_regles_et_appliquer(self):
        from app import commande_ia as C
        a = C.regles("ajoute du glow sur les plans 1 et 2, titre « Vol vers Calvi » au début, une flèche rouge courbe à 2 s")
        genres = [x["action"] for x in a]
        self.assertEqual(genres, ["effet", "texte", "fleche"])
        ed = self.ed
        n_t, n_g = len(ed.projet.titres), len(ed.projet.goodies)
        self.assertEqual(C.appliquer(a, ed), 3)
        ed.rafraichir()
        self.assertEqual(len(ed.projet.titres), n_t + 1)
        self.assertEqual(ed.projet.goodies[-1]["options"]["style"], "courbe")
        self.assertTrue(all(any(e["id"] == "glow" for e in c.get("effets") or []) for c in ed.projet.clips_piste("video")))
        ed.projet.annuler()                                       # une seule étape d'annulation
        self.assertEqual(len(ed.projet.titres), n_t)
        self.assertEqual(len(ed.projet.goodies), n_g)
        self.assertEqual([x["action"] for x in C.regles("mets une musique calme et coupe-la à la fin de la vidéo")], ["musique", "couper_musique"])

    def test_dialogue_commande(self):
        from app.dialogues_commande import DialogueCommande
        dl = DialogueCommande(self.ed)
        dl.phrase.setText("effet vintage sur tous les plans")
        dl.comprendre()
        dl.tache.wait(5000)
        app.processEvents()
        self.assertEqual(len(dl.cases), 1)
        self.assertTrue(dl.b_faire.isEnabled())
        dl.reject()

    # ---------------------------------------------------------------- flèches et titres tendance
    def test_fleche_tourne_avec_images_clefs(self):
        from app import cles as K, goodies as GO
        g = self.ed.projet.ajouter_goodie("fleche", 0, 4, options={"style": "courbe", "angle": 0})
        K.poser(g, 0.5, angle=0)
        K.poser(g, 3.5, angle=90, x=0.2)
        self.assertAlmostEqual(K.angle_goodie(g, 2.0), 45, places=0)
        a, b = GO.image(g, 1.0, 120), GO.image(g, 3.6, 120)
        self.assertNotEqual(a, b)
        for gr, st in (("bandeau_tendance", "incline"), ("bandeau_tendance", "deux"), ("bandeau_tendance", "contour"), ("surligne", "")):
            gg = {"genre": gr, "debut": 0, "fin": 3, "options": {"texte": "GRANDE HORLOGE SAMSUNG", "style": st}}
            img = GO.image(gg, 1.5, 160)
            opaques = sum(1 for x in range(0, 160, 4) for y in range(0, 160, 4) if img.pixelColor(x, y).alpha() > 0)
            self.assertGreater(opaques, 40, gr + st)
        self.ed.projet.goodies.remove(g)
        g2 = {"genre": "fleche", "debut": 0, "fin": 3, "options": {}}
        K.regler(g2, 0, angle=30)                           # sans image clef : l'angle va dans les options
        self.assertEqual(g2["options"]["angle"], 30)

    # ---------------------------------------------------------------- voix studio
    def test_voix_studio(self):
        from app import export
        f = export.filtre_audio("a_studio")
        self.assertIn("speechnorm", f)
        if moteur.filtre_disponible("arnndn"):
            self.assertIn("arnndn", f)
        entree = commun.musique_test(self.d, "voix.wav", duree=2)
        sortie = os.path.join(self.d, "voix_studio.wav")
        moteur.lancer(["-y", "-i", entree, "-af", f, sortie])
        self.assertTrue(os.path.getsize(sortie) > 1000)

    # ---------------------------------------------------------------- erreurs lisibles, partie jaune
    def test_message_erreur(self):
        lignes = ["[libx264 @ 0x1] frame I:1 Avg QP:20.00 size: 1234", "[libx264 @ 0x1] mb I  I16..4: 50.0% 20.0% 30.0%",
                  "[Parsed_overlay_3 @ 0x2] Error initializing filter", "Conversion failed!"]
        m = moteur.message_erreur(lignes, 1)
        self.assertIn("Error initializing filter", m)
        self.assertNotIn("I16..4", m)

    def test_partie_jaune_effacable(self):
        tl = self.ed.timeline
        tl.zone = [1.0, 3.0]
        self.assertTrue(tl.zone_valide())
        tl.effacer_zone()
        self.assertFalse(tl.zone_valide())


if __name__ == "__main__":
    unittest.main()
