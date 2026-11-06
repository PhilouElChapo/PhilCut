"""0.5.0 : intros modernes (Punchy, Clean, Cinéma), titre d'ouverture posé sur le film, vignette du fichier,
exemples neutres (logiciel distribué : rien ne doit rappeler l'auteur)."""
import json, os, re, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Test050(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QFontDatabase
        for f in os.listdir(os.path.join(RACINE, "fonts")):
            if f.endswith(".ttf"):
                QFontDatabase.addApplicationFont(os.path.join(RACINE, "fonts", f))
        cls.d = tempfile.mkdtemp()

    def test_polices_modernes_livrees(self):
        from PySide6.QtGui import QFontDatabase
        familles = set(QFontDatabase.families())
        for f in ("Poppins", "Bebas Neue", "Anton"):
            self.assertIn(f, familles)

    def test_tous_les_modeles_dessinent_et_bougent(self):
        from app import intros as I
        for m in I.MODELES:
            for fond in ("degrade", "uni", "transparent"):
                ctx = I.contexte(m, "Notre week-end", "Au bord de la mer", 320, 180, 3.0, fond)
                a, b = I.image(ctx, 0.3), I.image(ctx, 1.6)
                self.assertFalse(a.isNull())
                self.assertNotEqual(a, b, f"{m} / {fond} : l'image ne bouge pas")
                # au milieu, le titre est là : des pixels clairs au centre
                zx, zy = (range(10, 220, 2), range(118, 160, 2)) if m.startswith("tiers") else (range(60, 260, 3), range(60, 120, 3))
                clairs = sum(1 for x in zx for y in zy if b.pixelColor(x, y).lightness() > 170)
                self.assertGreater(clairs, 3, f"{m} / {fond} : pas de titre visible")

    def test_fabriquer_clip(self):
        from app import intros as I
        sortie = os.path.join(self.d, "intro.mp4")
        I.fabriquer(sortie, "cinema", "Titre", "Sous-titre", 320, 180, 25, 1.2, fond="degrade")
        f = moteur.sonder(sortie)
        self.assertAlmostEqual(float(f["duree"]), 1.2, delta=0.15)

    def test_fond_film(self):
        from app import intros as I
        img = os.path.join(self.d, "film.png")
        subprocess.run([moteur.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180", "-frames:v", "1", img], check=True)
        ctx = I.contexte("verre", "Titre", "", 320, 180, 3.0, "film", image_film=img)
        self.assertIsNotNone(ctx.film)
        self.assertFalse(I.image(ctx, 1.5).isNull())

    def test_titre_ouverture_goodie(self):
        from app import goodies as GO
        g = {"genre": "intro_titre", "debut": 0.3, "fin": 3.8, "taille": 1.78, "options": {"texte": "Titre", "modele": "horizon"}}
        self.assertIn("intro_titre", GO.FLUIDES)
        a, b = GO.image(g, 0.5, 240), GO.image(g, 2.0, 240)
        self.assertNotEqual(a, b)

    def test_recette_pose_titre_moderne(self):
        from app.projet import Projet
        from app import recettes
        p = Projet()
        v = commun.video_test(self.d, "v.mp4", duree=3)
        m = p.ajouter_media(v, moteur.sonder(v))
        r = {"logo": {"modele": "trace", "texte": "Ma vidéo", "duree": 2.5}, "plans": [{"media": m["id"], "src_debut": 0, "src_fin": 3}]}
        recettes.appliquer(r, p, {}, {})
        g = [x for x in p.goodies if x["genre"] == "intro_titre"]
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["options"]["modele"], "masque")         # ancien nom de modèle → modèle moderne
        self.assertEqual(p.clips_piste("video")[0]["debut"], 0.0)      # plus de plan noir en tête

    def test_vignette_du_fichier(self):
        from app.export import poser_vignette
        v = commun.video_test(self.d, "vv.mp4", duree=3)
        jpg = poser_vignette(v, 1.5)
        self.assertTrue(os.path.getsize(jpg) > 500)
        r = subprocess.run([moteur.ffprobe(), "-v", "error", "-show_streams", "-of", "json", v], capture_output=True, text=True)
        flux = json.loads(r.stdout)["streams"]
        self.assertTrue(any((s.get("disposition") or {}).get("attached_pic") == 1 for s in flux))

    def test_dialogue_fabrique_vignettes(self):
        from app.projet import Projet
        from app.dialogues_video import DialogueFabrique
        p = Projet()
        d = DialogueFabrique(None, p, {})
        d.show()
        for _i in range(4):
            d._animer()
        app.processEvents()
        self.assertGreaterEqual(d.vignettes.count(), 10)
        self.assertFalse(d.vignettes.item(0).icon().isNull())
        self.assertIn(d.modele.currentData(), __import__("app.intros", fromlist=["MODELES"]).MODELES)
        d.famille.setCurrentIndex(d.famille.findData("anciens"))
        self.assertTrue(all(d.vignettes.item(i).data(0x0100) not in ("slam",) for i in range(d.vignettes.count())))
        d.reject()

    def test_051_transitions_modernes(self):
        from app import effets as E
        for k in ("t_zoom_avant", "t_lisse", "t_file_vertical", "t_radial", "t_vent", "t_tranches", "t_couverture", "t_gris"):
            self.assertIn(k, E.CATALOGUE)
            self.assertIn(k, E.XFADE)
        from app.projet import Projet
        from app.export import Exportateur
        p = Projet()
        v = commun.video_test(self.d, "t.mp4", duree=2)
        m = p.ajouter_media(v, moteur.sonder(v))
        p.ajouter_clip(m["id"], "video", 0, 0, 2)
        c2 = p.ajouter_clip(m["id"], "video", 2, 0, 2)
        for k in ("t_file_vertical", "t_zoom_avant"):
            c2["transition"] = {"id": k, "params": dict(E.defauts(k))}
            sortie = os.path.join(self.d, f"{k}.mp4")
            Exportateur(p, sortie, "whatsapp", qualite="allegee", encodeur="libx264", params={}).lancer()
            self.assertTrue(os.path.getsize(sortie) > 1000)

    def test_051_tiers_et_texte_moderne(self):
        from app import intros as I
        for m in ("tiers_clean", "tiers_punchy"):
            ctx = I.contexte(m, "Prénom Nom", "Fonction", 320, 180, 3.0, "transparent")
            self.assertGreater(ctx.y_texte, 180 * 0.7)
            img = I.image(ctx, 1.5)
            bas = sum(1 for x in range(0, 220, 2) for y in range(115, 170, 2) if img.pixelColor(x, y).alpha() > 150)
            self.assertGreater(bas, 5)
        from app.dialogues_video import DialogueTitre
        d = DialogueTitre(None)
        self.assertGreater(d.moderne.count(), 10)
        d.reject()
        from app import logo as LG
        g = LG.gabarits("Mon Studio")
        self.assertTrue(any(k.startswith("Moderne") for k in g))
        self.assertFalse(LG.rendre(next(v for k, v in g.items() if k.startswith("Moderne")), 200).isNull())

    def test_052_transitions_automatiques(self):
        from app.projet import Projet
        from app import transitions_auto as TA
        d = self.d
        pan = os.path.join(d, "pan.mp4")          # panoramique rapide vers la gauche
        subprocess.run([moteur.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x360:r=25:d=3",
                        "-vf", "crop=480:360:x='min(800,t*400)':y=0", pan], check=True)
        bleu = os.path.join(d, "bleu.mp4")
        subprocess.run([moteur.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x2050ff:s=480x360:r=25:d=3", bleu], check=True)
        fixe = os.path.join(d, "fixe.mp4")
        subprocess.run([moteur.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "smptebars=s=480x360:r=25:d=3", fixe], check=True)
        p = Projet()
        mp, mb, mf = (p.ajouter_media(x, moteur.sonder(x)) for x in (pan, bleu, fixe))
        p.ajouter_clip(mp["id"], "video", 0, 0, 2)
        c2 = p.ajouter_clip(mb["id"], "video", 2, 0, 2)
        c3 = p.ajouter_clip(mf["id"], "video", 4, 0, 2)
        c4 = p.ajouter_clip(mf["id"], "video", 6, 0.5, 2.5)
        props = {x["clip"]: x for x in TA.proposer(p, "clean")}
        self.assertEqual(props[c2["id"]]["eid"], "t_file", props[c2["id"]])          # le panoramique appelle un filé
        self.assertEqual(props[c3["id"]]["eid"], "t_fondu_enchaine")                  # autre scène : fondu
        self.assertIsNone(props[c4["id"]]["eid"])                                     # même scène : coupe franche
        n = TA.appliquer(p, list(props.values()))
        self.assertEqual(n, 3)
        self.assertEqual(p.clip(c2["id"])["transition"]["id"], "t_file")
        p.annuler()
        self.assertFalse(p.clip(c2["id"]).get("transition"))
        cine = {x["clip"]: x for x in TA.proposer(p, "cinema")}
        self.assertIn(cine[c3["id"]]["eid"], ("t_gris", "t_fondu_enchaine", "t_fondu_noir"))

    def test_exemples_neutres(self):
        """Logiciel distribué à la communauté : pas de lieux, commerces ou noms propres de l'auteur dans les textes."""
        interdits = re.compile(r"calvi|cannes|saint-vallier|samsung|prado|pharmacie du|delaye", re.I)
        fautes = []
        for f in os.listdir(os.path.join(RACINE, "app")):
            if not f.endswith(".py") or f == "aviation.py":          # aviation.py : liste publique des aérodromes
                continue
            for i, ligne in enumerate(open(os.path.join(RACINE, "app", f), encoding="utf-8"), 1):
                if interdits.search(ligne) and "Par Philippe Delaye" not in ligne:   # seule mention : l'auteur dans « A propos »
                    fautes.append(f"{f}:{i}: {ligne.strip()[:90]}")
        self.assertEqual(fautes, [])


if __name__ == "__main__":
    unittest.main()
