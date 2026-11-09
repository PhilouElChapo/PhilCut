"""0.9.35 : étape 0 vers Android — format de projet 2 (liens virtuels, révision, inconnu gardé), espace PhilCut sur le
Drive, moteur d'effets GL commun PC / Android (shaders, parité avec les images de référence)."""
import json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur

REFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "references_gl")


def image_reference():
    """Image d'essai déterministe (dégradés, aplats, bords nets) : la même partout, sans dépendre de FFmpeg."""
    import numpy as np
    h, w = 90, 160
    y, x = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3), np.float32)
    img[..., 0] = x / (w - 1)
    img[..., 1] = y / (h - 1)
    img[..., 2] = 0.5 + 0.5 * np.sin(x / 9.0) * np.cos(y / 7.0)
    img[20:60, 50:110] = (1.0, 1.0, 1.0)
    img[35:45, 10:40] = (0.0, 0.0, 0.0)
    return (img * 255).astype(np.uint8)


def fenetre():
    from app.config import Parametres
    pa = Parametres()
    pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
    pa.enregistrer()
    from app.fenetre import Fenetre
    return Fenetre()


class TestProjet2(unittest.TestCase):
    def test_inconnu_garde_revision_emplacements(self):
        from app.projet import Projet
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=1)
        p = Projet()
        m = p.ajouter_media(v, moteur.sonder(v))
        p.ajouter_clip(m["id"])
        p.d["pistes_android"] = {"x": [1, 2]}
        m["futur"] = "garde"
        f = os.path.join(d, "p.philcut")
        p.enregistrer(f)
        dd = json.load(open(f, encoding="utf-8"))
        self.assertEqual(dd["version"], 2)
        self.assertEqual(dd["revision"], 1)
        self.assertEqual(dd["pistes_android"], {"x": [1, 2]})
        self.assertEqual(dd["medias"][0]["futur"], "garde")
        self.assertTrue(dd["medias"][0]["emplacements"])
        # projet d'une version plus récente : ouvert quand même, et réécrit avec ce qu'on ne connaît pas
        dd["version"] = 9
        dd["inconnu"] = {"a": 1}
        json.dump(dd, open(f, "w", encoding="utf-8"))
        q = Projet.ouvrir(f)
        self.assertTrue(q.plus_recent)
        q.enregistrer(f)
        dd = json.load(open(f, encoding="utf-8"))
        self.assertEqual((dd["version"], dd["inconnu"]), (9, {"a": 1}))

    def test_conflit_garde_l_autre_version(self):
        from app.projet import Projet
        from app import secours
        d = tempfile.mkdtemp()
        p = Projet("conflit")
        f = os.path.join(d, "c.philcut")
        p.enregistrer(f)
        q = Projet.ouvrir(f)
        dd = json.load(open(f, encoding="utf-8"))
        dd.update(revision=dd["revision"] + 3, appareil="Galaxy S24", nom="version du téléphone")
        json.dump(dd, open(f, "w", encoding="utf-8"))
        q.enregistrer(f)
        self.assertEqual(q.conflit["appareil"], "Galaxy S24")
        self.assertTrue(os.path.exists(q.conflit["copie"]))
        v = secours.versions(secours.cle(q))
        self.assertTrue(any(x["autre"] and x["poste"] == "Galaxy S24" for x in v))
        secours.effacer(q)                         # la fermeture normale ne jette pas la version de l'autre appareil
        self.assertTrue(os.path.exists(q.conflit["copie"]))

    def test_liens_virtuels(self):
        from app.projet import Projet
        from app import liens, projet as P
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=1)
        w = commun.video_test(d, "b.mp4", duree=1)
        p = Projet()
        for x in (v, w):
            p.ajouter_clip(p.ajouter_media(x, moteur.sonder(x))["id"])
        f = os.path.join(d, "p.philcut")
        p.enregistrer(f)
        # les deux fichiers partent ailleurs : « Où est ce fichier ? » sur l'un retrouve l'autre (même dossier)
        d2 = tempfile.mkdtemp()
        shutil.move(v, os.path.join(d2, "a.mp4"))
        shutil.move(w, os.path.join(d2, "b.mp4"))
        q = Projet.ouvrir(f)
        r = q.retrouver_medias()
        self.assertEqual(len(r["manquants"]), 2)
        ok, msg = liens.rattacher(q, q.medias[0], os.path.join(d2, "a.mp4"))
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(q.medias[1]["chemin"]))
        # un autre fichier que l'original : refusé sans confirmation
        autre = commun.video_test(d2, "c.mp4", duree=2)
        ok, _m = liens.rattacher(q, q.medias[0], autre)
        self.assertFalse(ok)
        # copie légère sur le Drive : le média manquant est monté sur elle, l'original reste dans le fichier
        drive = tempfile.mkdtemp()
        os.makedirs(os.path.join(drive, "PhilCut", "Medias"))
        ancien = P.PARAMS
        P.PARAMS = {"drive": drive, "machine": "pc-essai"}
        try:
            q.medias[0]["copie_drive"] = "x_720p.mp4"
            shutil.copy(os.path.join(d2, "a.mp4"), os.path.join(drive, "PhilCut", "Medias", "x_720p.mp4"))
            os.remove(os.path.join(d2, "a.mp4"))
            q.medias[0]["chemin"] = os.path.join(d2, "a.mp4")
            r = q.retrouver_medias()
            self.assertEqual(len(r["copies"]), 1)
            self.assertTrue(q.medias[0]["copie_legere"])
            q.enregistrer(f)
            dd = json.load(open(f, encoding="utf-8"))
            self.assertEqual(dd["medias"][0]["chemin"], os.path.join(d2, "a.mp4"))
            self.assertNotIn("copie_legere", dd["medias"][0])
        finally:
            P.PARAMS = ancien

    def test_export_sans_media_ne_plante_pas(self):
        from app.projet import Projet
        from app import export
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=1)
        w = commun.video_test(d, "b.mp4", duree=1)
        p = Projet()
        for x in (v, w):
            p.ajouter_clip(p.ajouter_media(x, moteur.sonder(x))["id"])
        os.remove(w)
        out, _j = export.exporter(p, os.path.join(d, "o.mp4"), "whatsapp")
        self.assertTrue(os.path.exists(out))


class TestDrive(unittest.TestCase):
    def test_copie_legere_analyse_suppression(self):
        from app import drive_philcut as DP
        from app.projet import Projet
        d = tempfile.mkdtemp()
        drive = tempfile.mkdtemp()
        params = {"drive": drive, "drive_purge_jours": 90}
        v = commun.video_test(d, "a.mp4", duree=2, taille="1920x1080")
        p = Projet("essai")
        m = p.ajouter_media(v, moteur.sonder(v))
        nom = DP.copier_leger(params, m)
        copie = os.path.join(drive, "PhilCut", "Medias", nom)
        self.assertTrue(os.path.exists(copie))
        self.assertLessEqual(moteur.sonder(copie)["video"]["largeur"], 1280)
        # une création IA déposée, un vieux fichier oublié, un reste de transfert, les réglages
        cr = os.path.join(d, "musique.wav")
        moteur.lancer(["-f", "lavfi", "-i", "sine=f=330:d=1", cr])
        json.dump({"phrase": "jazz"}, open(cr + ".ia.json", "w"))
        DP.deposer_creation(params, cr)
        oubli = os.path.join(drive, "PhilCut", "Medias", "vieux_720p.mp4")
        shutil.copy(copie, oubli)
        open(os.path.join(drive, "PhilCut", "Medias", "x.part"), "w").write("x")
        json.dump({}, open(os.path.join(drive, "PhilCut", "preferences.json"), "w"))
        el = {e["rel"]: e for e in DP.analyser(params)}
        self.assertTrue(el["Medias/vieux_720p.mp4"]["proposer"])        # plus référencé
        self.assertTrue(el["Medias/x.part"]["proposer"])
        self.assertFalse(el[f"Medias/{nom}"]["proposer"])                 # utilisé aujourd'hui
        self.assertEqual(el["preferences.json"]["categorie"], "reglages")
        self.assertFalse(el["preferences.json"]["proposer"])
        self.assertTrue(any(r.startswith("Creations/") for r in el))
        # vieux de 200 jours : proposé
        idx = DP.lire_index(params)
        idx[nom]["utilise"] = "2026-01-01"
        DP._ecrire_index(params, idx)
        self.assertTrue({e["rel"]: e for e in DP.analyser(params)}[f"Medias/{nom}"]["proposer"])
        n, octets, err = DP.supprimer(params, ["Medias/vieux_720p.mp4", "Medias/x.part"])
        self.assertEqual((n, err), (2, []))
        self.assertFalse(os.path.exists(oubli))

    def test_fenetres(self):
        f = fenetre()
        ed = f.nouveau_projet("16:9")
        from app.dialogues_drive import DialogueManquants, DialogueEspaceDrive
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=1)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        m["chemin"] = os.path.join(d, "parti.mp4")
        dm = DialogueManquants(ed)
        self.assertEqual(dm.arbre.topLevelItemCount(), 1)
        dm.reject()
        de = DialogueEspaceDrive(f, {"drive": tempfile.mkdtemp()})
        de.reject()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


class TestMoteurGL(unittest.TestCase):
    def test_shaders_pc_et_android(self):
        from app import moteur_gl as G
        if not G.disponible():
            self.skipTest("OpenGL indisponible : " + G.raison())
        cat = G.charger()
        self.assertGreaterEqual(len(cat["effets"]), 50)

        def compiler():
            ctx = G._CTX["ctx"]
            for nom in cat["shaders"]:
                ctx.program(vertex_shader=G.ENTETE_PC + G.SOMMETS, fragment_shader=G.source(nom))
                ctx.program(vertex_shader=G.ENTETE_ES + G.SOMMETS, fragment_shader=G.source(nom, "es"))   # OpenGL ES 3.0 (Android)
        G.executer(compiler)
        # chaque effet a un nom dans les 5 langues et ses réglages dans les bornes
        for ident, e in cat["effets"].items():
            self.assertEqual(set(e["nom"]), {"fr", "en", "de", "es", "it"}, ident)
            sh = cat["shaders"][e["shader"]]
            for p in sh["parametres"]:
                v = G.valeurs(ident)[p["cle"]]
                if p.get("type") == "choix":
                    self.assertLess(int(v), len(p["choix"]), ident)
                elif p.get("type") != "bool":
                    self.assertTrue(p["min"] <= float(v) <= p["max"], (ident, p["cle"], v))

    def test_parite_images_de_reference(self):
        """Chaque effet, sur l'image d'essai à t = 0,45 s, doit redonner l'image de référence (celle que l'appli Android
        doit aussi produire). PHILCUT_REFS=1 refait les références."""
        import numpy as np
        from PIL import Image
        from app import moteur_gl as G
        if not G.disponible():
            self.skipTest("OpenGL indisponible : " + G.raison())
        img = image_reference()
        os.makedirs(REFS, exist_ok=True)
        ecarts = {}
        for ident in G.charger()["effets"]:
            out = G.appliquer_image([{"id": ident}], img, temps=0.45, duree=3.0)
            ref = os.path.join(REFS, ident + ".png")
            if os.environ.get("PHILCUT_REFS") or not os.path.exists(ref):
                Image.fromarray(out).save(ref)
                continue
            attendu = np.array(Image.open(ref).convert("RGB")).astype(np.float32)

            def blocs(a):            # moyenne par blocs de 4×4 : le grain (bruit pseudo-aléatoire) diffère d'une carte
                return a.reshape(a.shape[0] // 2, 2, a.shape[1] // 4, 4, 3)[:44].mean(axis=(1, 3))    # graphique à l'autre
            ecarts[ident] = float(np.abs(blocs(out.astype(np.float32)) - blocs(attendu)).mean())
        mauvais = {k: round(v, 2) for k, v in ecarts.items() if v > 4.0}
        self.assertEqual(mauvais, {})

    def test_export_avec_effets_gl_et_glow(self):
        from app.projet import Projet
        from app import export, moteur_gl as G
        import numpy as np
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=1)
        p = Projet()
        c = p.ajouter_clip(p.ajouter_media(v, moteur.sonder(v))["id"])
        c["effets"] = [{"id": "gl_ouvrir_cercle", "params": {"duree": 2.0}}, {"id": "glow"}]
        out, journal = export.exporter(p, os.path.join(d, "o.mp4"), "whatsapp")
        self.assertTrue(os.path.exists(out))
        brut = moteur.lancer(["-ss", "0.2", "-i", out, "-frames:v", "1", "-vf", "scale=64:36", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]) \
            if hasattr(moteur, "lancer_brut") else None
        import subprocess
        px = subprocess.run([moteur.ffmpeg(), "-v", "error", "-ss", "0.2", "-i", out, "-frames:v", "1", "-vf", "scale=64:36", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        a = np.frombuffer(px, np.uint8).reshape(36, 64, 3)
        if G.disponible():
            coin = a[:4, :4].astype(int)
            self.assertLess(coin.max(), 30)          # hors du cercle : noir, pas violet (glow en RVB)
        self.assertEqual(brut, None)

    def test_secours_sans_carte_graphique(self):
        from app import moteur_gl as G
        self.assertIn("vintage", G.filtre_secours("gl_retro_8mm"))
        self.assertIn("scale=iw/24", G.filtre_secours("gl_pixels"))
        self.assertIsNone(G.filtre_secours("gl_etoiles"))


if __name__ == "__main__":
    unittest.main()
