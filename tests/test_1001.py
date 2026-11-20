"""1.0.1 : neuf types d'animation de plus (camembert, jauge, comparaison, classement, chiffres clefs, chronologie, liste,
citation, appel à l'action) pour les trois moteurs, et « Recharger… » pour chaque modèle et chaque service."""
import json, os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

NOUVEAUX = ("camembert", "jauge", "comparaison", "classement", "chiffres_cles", "chronologie", "liste", "citation", "appel")


class TestTypes(unittest.TestCase):
    def test_horaire_et_elements(self):
        from app import motion as M
        for g in NOUVEAUX:
            a = M.preparer_genre(M.nouvelle(), g)
            h = M.horaire(a)
            self.assertIn(g, h["scenes"], g)
            self.assertIn(g, h)
            if "entrees" in h[g]:
                self.assertEqual(len(h[g]["entrees"]), len(M.elements(a)), g)
                self.assertEqual(h[g]["entrees"], sorted(h[g]["entrees"]))
        a = M.preparer_genre(M.nouvelle(), "classement")
        vals = [v for _l, v, _t in M.elements(a)]
        self.assertEqual(vals, sorted(vals, reverse=True))
        a = M.preparer_genre(M.nouvelle(), "chronologie")
        self.assertEqual(M.elements(a)[0][:1], ("1998",))
        self.assertTrue(M.preparer_genre(M.nouvelle(), "appel")["transparent"])
        self.assertEqual(len(M.palette({"couleurs": {"accent": "#8B7CFF", "accent2": "#3EE0F0", "texte": "#FFFFFF"}}, 6)), 6)

    def test_exemples_ne_touchent_pas_au_texte(self):
        from app import motion as M
        a = M.nouvelle()
        a["titre"] = "Mon chiffre d'affaires"
        a = M.preparer_genre(a, "citation")
        self.assertEqual(a["titre"], "Mon chiffre d'affaires")
        b = M.preparer_genre(M.preparer_genre(M.nouvelle(), "comparaison"), "barres")
        self.assertEqual(len(b["donnees"]), len(M.EXEMPLE))                 # l'exemple revient avec le type

    def test_voix(self):
        from app import motion as M
        a = M.preparer_genre(M.nouvelle(), "jauge")
        h, n = M.caler_voix(a, [[2.0, 2.6, "72"]])
        self.assertEqual(n, 1)
        self.assertAlmostEqual(h["jauge"]["fin"], 2.6, delta=0.8)
        b = M.preparer_genre(M.nouvelle(), "liste")
        h, n = M.caler_voix(b, [[1.0, 1.3, "Simple"], [3.0, 3.3, "Rapide,"]])
        self.assertGreaterEqual(n, 2)
        self.assertLess(h["liste"]["entrees"][0], h["liste"]["entrees"][1])

    def test_ia(self):
        from app import motion as M
        a = M.appliquer_ia(M.nouvelle(), {"genre": "liste", "lignes": ["Un", " ", "Deux"], "bouton": "Go"})
        self.assertEqual((a["genre"], a["lignes"], a["bouton"]), ("liste", ["Un", "Deux"], "Go"))
        self.assertIn("chronologie", M.CONSIGNE_IA)

    def test_maison(self):
        from app import motion as M, motion_maison as MM
        for g in NOUVEAUX:
            for taille in ((1920, 1080), (1080, 1920)):
                a = M.preparer_genre(M.nouvelle(taille=taille), g)
                im = MM.apercu_image(a, M.duree_conseillee(g) * 0.7, (320, 180) if taille[0] > taille[1] else (180, 320))
                self.assertFalse(im.isNull(), g)

    def test_html(self):
        from app import motion as M, motion_html as MH
        for g in NOUVEAUX:
            a = M.preparer_genre(M.nouvelle(), g)
            mp = MH.mise_en_page(a)
            self.assertIn(g, mp["horaire"]["scenes"])
            html = MH.composition(a)
            self.assertIn(f"function {g}(", html)
        self.assertEqual(len(MH.mise_en_page(M.preparer_genre(M.nouvelle(), "camembert"))["palette"]), 6)

    def test_remotion(self):
        with open(os.path.join(commun.RACINE, "motion", "philcut-remotion", "src", "PhilCut.tsx"), encoding="utf-8") as fic:
            src = fic.read()
        for nom in ("Camembert", "Jauge", "Comparaison", "Classement", "ChiffresCles", "Chronologie", "Liste", "Citation", "Appel"):
            self.assertIn(f"const {nom}: React.FC<SceneProps>", src)
        for g in NOUVEAUX:
            self.assertIn(f"{g}: ", src.split("const SCENES")[1].split("};")[0])


    def test_remotion_sources_a_jour(self):
        from app import motion_remotion as MR
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "src"))
        with open(os.path.join(d, "src", "PhilCut.tsx"), "w", encoding="utf-8") as f:
            f.write("ancien")
        anc = MR.dossier
        MR.dossier = lambda: d
        try:
            self.assertGreaterEqual(MR.mettre_a_jour_sources(), 1)
            with open(os.path.join(d, "src", "PhilCut.tsx"), encoding="utf-8") as f:
                self.assertIn("const Camembert", f.read())
            self.assertEqual(MR.mettre_a_jour_sources(), 0)
        finally:
            MR.dossier = anc


class Test1002(unittest.TestCase):
    def test_sous_titres_verticaux_plus_gros(self):
        from app import motion as M, motion_html as MH
        a = M.preparer_genre(M.nouvelle(taille=(1080, 1920)), "sous_titres")
        a["mots"] = [[0.3 * i, 0.3 * i + 0.28, w] for i, w in enumerate("un deux trois quatre cinq six sept huit neuf dix".split())]
        mp = MH.mise_en_page(a)
        self.assertGreater(mp["st_taille"], 1.0)
        self.assertTrue(all(len(" ".join(m[2] for m in l["mots"])) <= M.ST_VERTICAL_CAR for l in mp["lignes_st"]))
        self.assertEqual(MH.mise_en_page(M.preparer_genre(M.nouvelle(), "sous_titres"))["st_taille"], 1.0)

    def test_higgsfield_console(self):
        from app import credit_ia, generateurs_video as GV
        self.assertIn("open.higgsfield.ai", credit_ia.texte_credit("higgsfield", None))
        self.assertEqual(GV.PAGES_CREDIT["higgsfield"], "https://open.higgsfield.ai/api-keys")
        m = GV.modele("hf-seedance-25", {})
        self.assertEqual(m["modele"], "bytedance/seedance-2.5/text-to-video")
        envoye = {}

        def faux(url, cle, corps=None, delai=120):
            if corps is not None and "prompt" in corps:
                envoye.update(corps, url=url)
                return {"status_url": "https://api.higgsfield.ai/requests/x/status"}
            return {"status": "completed", "video": {"url": "https://x/v.mp4"}}
        anc_h, anc_t, anc_s = GV._http_hf, GV.telecharger, GV.time.sleep
        GV._http_hf, GV.telecharger, GV.time.sleep = faux, (lambda u, s: s), (lambda s: None)
        try:
            GV.generer_higgsfield("a:b", m, "A cinematic scene at sunset", "/tmp/v.mp4", 5, image="/tmp/x.png", format_="9:16")
        finally:
            GV._http_hf, GV.telecharger, GV.time.sleep = anc_h, anc_t, anc_s
        self.assertEqual((envoye["url"], envoye["duration"], envoye["aspect_ratio"], envoye["resolution"], envoye["generate_audio"]),
                         ("https://api.higgsfield.ai/bytedance/seedance-2.5/text-to-video", 5, "9:16", "720p", False))
        self.assertNotIn("image_url", envoye)


class Test1004(unittest.TestCase):
    def test_verifications_windows_une_a_la_fois(self):
        import gc, threading, time
        from app import reseau
        try:
            import truststore._api as api
        except ImportError:
            self.skipTest("truststore absent")
        anc = api._verify_peercerts_impl
        dedans, maxi, gc_actif = [0], [0], []

        def faux(*a, **k):
            dedans[0] += 1
            maxi[0] = max(maxi[0], dedans[0])
            gc_actif.append(gc.isenabled())
            time.sleep(0.02)
            dedans[0] -= 1
        api._verify_peercerts_impl = faux
        try:
            reseau._une_verification_a_la_fois()
            ts = [threading.Thread(target=api._verify_peercerts_impl) for _ in range(6)]
            [t.start() for t in ts]
            [t.join() for t in ts]
        finally:
            api._verify_peercerts_impl = anc
        self.assertEqual(maxi[0], 1)
        self.assertFalse(any(gc_actif))
        self.assertTrue(gc.isenabled())


class Test1005(unittest.TestCase):
    def test_remplacer_element(self):
        from PySide6.QtGui import QImage, QColor
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        from app.fenetre import Fenetre
        from app import bibliotheque_creations as B, ia, moteur, remplacer_element as R
        d = tempfile.mkdtemp()
        src, ref = os.path.join(d, "photo.png"), os.path.join(d, "fiche.png")
        q = QImage(640, 360, QImage.Format_RGB32)
        q.fill(QColor("#888888"))
        q.save(src)
        q.fill(QColor("#2255aa"))
        q.save(ref)
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        B.garder(f.params, "objet", "Avion d'essai", "Avion bleu", fichiers={"planche": ref})
        ed = f.nouveau_projet("16:9")
        m = ed.projet.ajouter_media(src, moteur.sonder(src))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0, 0.0, 5.0)
        dl = ed.remplacer_element(c)
        dl._test_oui = True
        self.assertFalse(dl.b_go.isEnabled())
        dl._zone([0.1, 0.1, 0.6, 0.5])
        dl.quoi.setText("la voiture")
        self.assertFalse(dl.b_go.isEnabled())              # l'accord manque
        dl.accord.setChecked(True)
        self.assertTrue(dl.b_go.isEnabled())
        recu = {}

        def faux(params, consigne, images, delai=240):
            recu.update(c=consigne, i=images)
            r = QImage(1024, 1024, QImage.Format_RGB32)
            r.fill(QColor("#aa3333"))
            ba = QByteArray()
            b = QBuffer(ba)
            b.open(QIODevice.WriteOnly)
            r.save(b, "PNG")
            return bytes(ba)
        anc = ia.generer_image_refs
        ia.generer_image_refs = faux
        try:
            dl.lancer()
            dl.tache.wait(20000)
            for _ in range(20):
                app.processEvents()
        finally:
            ia.generer_image_refs = anc
        self.assertTrue(dl.resultat)
        self.assertEqual((QImage(dl.resultat).width(), QImage(dl.resultat).height()), (640, 360))
        self.assertEqual(recu["i"][0], src)
        self.assertTrue(any(p.endswith("planche.png") for p in recu["i"][2:]))
        self.assertIn("« la voiture »", recu["c"])
        self.assertTrue(dl.poser())
        self.assertEqual(ed.projet.media(ed.projet.clip(c["id"])["media"])["chemin"], dl.resultat)
        ed.projet.modifie = False
        self.assertIn("red", R.CONSIGNE)


class TestRecharger(unittest.TestCase):
    def test_fabrique_suit_le_modele(self):
        from app.fenetre import Fenetre
        from app.dialogues_video import DialogueFabrique
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = DialogueFabrique(f, ed.projet, f.params)
        from app import generateurs_video as GV
        m = GV.modele(d.modele_veo.currentData() or "", f.params)
        self.assertEqual(d.credit.fournisseur, (m or {}).get("fournisseur"))
        i = next((k for k in range(d.modele_veo.count()) if (GV.modele(d.modele_veo.itemData(k), f.params) or {}).get("fournisseur") == "fal"), None)
        if i is not None:
            d.modele_veo.setCurrentIndex(i)
            self.assertEqual(d.credit.fournisseur, "fal")
        d.close()
        ed.projet.modifie = False

    def test_preferences(self):
        from app.config import Parametres
        from app.preferences import DialoguePreferences
        from PySide6.QtWidgets import QWidget
        pa = Parametres()
        pa["synchro_secrets"] = False

        class FauxFen(QWidget):
            def telecharger_pack(self, k): pass
        d = DialoguePreferences(FauxFen(), pa)
        self.assertEqual(sorted(d.boutons_recharge), sorted(["anthropic", "fal", "google", "heygen", "higgsfield"]))
        d._test_ouvert = []
        d.boutons_recharge["higgsfield"].click()
        self.assertEqual(d._test_ouvert, ["https://open.higgsfield.ai/api-keys"])
        d.close()

    def test_fenetre_credits(self):
        from app.dialogues_credits import DialogueCredits, usages
        from app.config import Parametres
        pa = Parametres()
        d = DialogueCredits(None, pa)
        self.assertEqual(list(d.lignes), ["anthropic", "google", "fal", "higgsfield", "heygen"])
        self.assertTrue(usages(pa, "fal")[1])                       # les modèles fal sont nommés
        d._test_oui = True
        d.connecter("google")
        self.assertIn("Gemini", d._test_connexion.onglets.tabText(d._test_connexion.onglets.currentIndex()))
        d.close()

    def test_menu(self):
        from app.fenetre import Fenetre
        from PySide6.QtWidgets import QMenu
        f = Fenetre()
        m = QMenu()
        f.remplir_fabrique(m)
        self.assertIn("Crédits et recharges des IA…", [a.text() for a in m.actions()])
        d = f.credits_ia()
        self.assertIs(f.credits_ia(), d)                             # une seule fenêtre
        d.close()


class TestFenetre(unittest.TestCase):
    def test_champs_selon_le_type(self):
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        dl = ed.animation(genre="chronologie")
        dl._test_oui = True
        self.assertTrue(dl.lignes.isVisible() and not dl.table.isVisible() and not dl.bouton.isVisible())
        dl.lignes.setPlainText("2001 : départ\n2024 : arrivée")
        self.assertEqual(len(dl.anim["lignes"]), 2)
        dl.genre.setCurrentIndex(dl.genre.findData("appel"))
        self.assertTrue(dl.bouton.isVisible() and not dl.lignes.isVisible())
        dl.genre.setCurrentIndex(dl.genre.findData("camembert"))
        self.assertTrue(dl.table.isVisible())
        self.assertTrue(dl.w_calage.isVisible())
        dl.close()
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
