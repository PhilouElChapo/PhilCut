"""0.9.20 : styles « à la manière de » (le nom devient la description du style, jamais envoyé au moteur) ; dossier des
créations IA nettoyé selon la durée choisie, sans toucher à ce qu'un projet utilise."""
import json, os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test0920(unittest.TestCase):
    def test_transposer_les_noms(self):
        from app import styles_ia as S
        r = S.transposer("une chanson d'amour chantée à la manière de Sinatra, musique façon Liza Minnelli", "musique")
        self.assertEqual([n for n, _d in r["styles"]], ["sinatra", "liza minnelli"])
        self.assertIn("crooner", r["styles"][0][1])
        self.assertIn("Broadway", r["styles"][1][1])
        self.assertNotIn("Sinatra", r["texte"])
        self.assertNotIn("Minnelli", r["texte"])
        v = S.transposer("un cow-boy à la John Wayne dans un look Star Wars", "video")
        self.assertEqual(v["texte"], "un cow-boy")
        self.assertIn("cowboy archetype", v["ajout"])
        self.assertIn("space opera", v["ajout"])
        for nom in ("wayne", "star wars", "sinatra"):
            self.assertNotIn(nom, (v["ajout"] + r["ajout"]).lower())
        self.assertEqual(S.transposer("une jarre en terre cuite", "image")["styles"], [])   # mot courant : pas sans « comme »
        self.assertEqual(S.transposer("portrait à la manière de Gérard Dupont", "image")["inconnus"], ["Gérard Dupont"])
        # réponse de l'IA : JSON lu, le nom retiré s'il s'y glisse
        d = S.lire_reponse('Voilà : {"Gérard Dupont": "Dupont style, warm 1970s portrait lighting, soft grain"}', ["Gérard Dupont"])
        self.assertEqual(d, {"Gérard Dupont": "style, warm 1970s portrait lighting, soft grain"})
        pa = {"styles_perso": d}
        self.assertEqual(S.transposer("portrait à la manière de Gérard Dupont", "image", pa)["inconnus"], [])

    def test_nettoyage_des_creations(self):
        from app import creations as CR
        d = CR.dossier()
        vieux, utilise, recent = (os.path.join(d, f"test_{k}.mp3") for k in ("vieux", "utilise", "recent"))
        for p in (vieux, utilise, recent):
            with open(p, "wb") as f:
                f.write(b"x" * 1000)
            CR.ecrire(p, {"prompt": "x"})
        il_y_a_100_jours = time.time() - 100 * 86400
        for p in (vieux, utilise):
            os.utime(p, (il_y_a_100_jours, il_y_a_100_jours))
        projet = os.path.join(tempfile.mkdtemp(), "p.philcut")
        with open(projet, "w", encoding="utf-8") as f:
            json.dump({"medias": [{"chemin": utilise}]}, f)
        n, o = CR.nettoyer(90, CR.en_usage({"recents": [projet]}))
        self.assertEqual(n, 1)
        self.assertFalse(os.path.exists(vieux) or os.path.exists(CR.chemin_recette(vieux)))
        self.assertTrue(os.path.exists(utilise) and os.path.exists(recent))
        self.assertEqual(CR.nettoyer(0)[0], 0)                                # « Ne jamais supprimer »
        for p in (utilise, recent):
            os.remove(p)
            os.remove(CR.chemin_recette(p))

    def test_atelier_montre_le_style(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        from app.dialogues_creatif import DialogueAtelierIA
        dl = DialogueAtelierIA(ed, "musique")
        dl.show()
        dl.liste.setCurrentRow(0)
        dl.prompt.setPlainText("ballade chantée à la manière de Sinatra")
        self.assertIn("crooner", dl.style_info.text())
        self.assertFalse(dl.style_info.isHidden())
        self.assertTrue(dl.boite_style.isHidden())
        dl.prompt.setPlainText("ballade à la manière de Gérard Dupont")
        self.assertFalse(dl.boite_style.isHidden())                            # bouton « Transposer avec l'IA »
        from app.preferences import DialoguePreferences
        p = DialoguePreferences(f, f.params, "Assistant")
        self.assertEqual(p.purge.currentData(), 90)
        p.styles_perso.setPlainText("Gérard Dupont = warm 1970s ballad, soft male vocals")
        p.valider()
        self.assertEqual(f.params["styles_perso"]["Gérard Dupont"], "warm 1970s ballad, soft male vocals")
        dl._maj_style()
        self.assertTrue(dl.boite_style.isHidden())
        dl.reject()
        p.hide()
        p.deleteLater()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_replique_dite_et_melee(self):
        """0.9.21 : la réplique est dite par un moteur de voix à part avec le phrasé du style, puis mêlée au clip ;
        une réplique plus longue que le clip tient la dernière image."""
        from app import diction as DI, moteur
        self.assertEqual(DI.style_depuis("un gangster joué comme Alain Delon")[0], "froid")
        self.assertEqual(DI.style_depuis("un cow-boy à la John Wayne")[0], "trainant")
        self.assertEqual(DI.style_depuis("un chat sur un toit")[0], "naturel")
        self.assertIn("asetrate", DI.filtres(DI.STYLES["bourru"][1]))
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "plan.mp4", duree=2)

        def faux_dire(texte, sortie, params, style="naturel", moteur_voix="local", voix=None, dossier=None):
            vus.append((texte, style, moteur_voix))
            moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=3", "-ar", "48000", sortie])
            return sortie
        vus = []
        DI.dire = faux_dire
        w = os.path.join(d, "r.wav")
        DI.dire("Salut", w, {})
        sortie = DI.mixer(v, w, os.path.join(d, "m.mp4"), debut=0.3)
        info = moteur.sonder(sortie)
        self.assertTrue(info["audio"])
        self.assertGreater(info["duree"], 3.4)                              # 0,3 + 3 s de voix + 0,4
        # dans l'Atelier : effet vidéo (dessin animé OpenCV, hors ligne) + réplique
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.ajouter_a_la_timeline(m["id"])
        ed.aller_a(1.0)
        app.processEvents()
        from app.dialogues_creatif import DialogueAtelierIA
        dl = DialogueAtelierIA(ed, "video")
        dl.show()
        dl.liste.setCurrentRow([dl.liste.item(i).data(0x0100)["id"] for i in range(dl.liste.count())].index("v_anime"))
        self.assertFalse(dl.boite_replique.isHidden())
        dl.replique.setPlainText("Ici, c'est moi qui décide.")
        dl.diction.setCurrentIndex(dl.diction.findData("gouailleur"))
        dl.creer()
        t0 = time.time()
        while dl.tache.isRunning() and time.time() - t0 < 120:
            app.processEvents()
            time.sleep(0.05)
        for _i in range(20):
            app.processEvents()
        self.assertTrue(dl.resultat and moteur.sonder(dl.resultat)["audio"], dl.info.text())
        self.assertEqual(vus[-1], ("Ici, c'est moi qui décide.", "gouailleur", "local"))
        self.assertTrue(os.path.exists(dl._clip_brut))
        from app import creations
        self.assertEqual(creations.lire(dl.resultat)["replique"], "Ici, c'est moi qui décide.")
        textes = [dl.actions.itemAt(i).widget().text() for i in range(dl.actions.count()) if dl.actions.itemAt(i).widget()]
        self.assertIn("Refaire seulement la voix", textes)
        dl.reject()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
