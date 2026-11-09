"""0.9.37 : fabrique musique (fiche, styles classiques, consigne, amélioration, analyse d'un morceau, réorchestration d'un
morceau libre, voix de référence d'accord), musique en ligne (YouTube Music, YouTube, archives libres), recettes IA et
« Créations à refaire ou à calculer » avec avant / après."""
import io, json, os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
import numpy as np
from app import moteur

SR = 22050


def piste(bpm, notes, dur=30, mes=4):
    t = np.arange(int(SR * dur)) / SR
    x = np.zeros_like(t)
    for f in notes:
        x += 0.15 * np.sin(2 * np.pi * f * t)
    beat = 60 / bpm
    rnd = np.random.RandomState(1)
    for k in range(int(dur / beat)):
        i, n = int(k * beat * SR), int(0.08 * SR)
        x[i:i + n] += (1.0 if k % mes == 0 else 0.5) * np.sin(2 * np.pi * 60 * t[:n]) * np.exp(-t[:n] * 40)
        x[i:i + 200] += 0.3 * rnd.randn(200)
    return x.astype(np.float32)


def ecrire_mp3(chemin, x):
    subprocess.run([moteur.ffmpeg(), "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", chemin], input=x.tobytes(), check=True)
    return chemin


class TestFiche(unittest.TestCase):
    def test_styles_et_consigne(self):
        from app import musique_ia as MI
        ids = [s[0] for s in MI.STYLES]
        self.assertEqual(len(ids), len(set(ids)))
        for k in ("symphonie", "opera", "classique", "baroque", "sacre", "gregorien", "valse"):
            self.assertIn(k, ids)
        for s in MI.STYLES:
            self.assertEqual(len(s), 8, s[0])
            self.assertIn(s[2], MI.FAMILLES, s[0])
        f = dict(MI.fiche_vide(), style="opera", ambiance="solennelle", phrase="chanté à la manière de Frank Sinatra", instrumental=False,
                 voix="tenor", tempo=0, mesure="")
        c = MI.consigne(f)
        self.assertNotIn("sinatra", c["caption"].lower())
        self.assertNotIn("chanté", c["caption"])
        self.assertIn("operatic", c["caption"])
        self.assertIn("tenor", c["caption"])
        self.assertEqual(c["bpm"], 72)
        self.assertEqual(c["keyscale"], "A minor")
        # la consigne améliorée remplace la fiche quand on la choisit
        f.update(consigne_ia="lush orchestral aria", utiliser_ia=True)
        self.assertTrue(MI.consigne(f)["caption"].startswith("lush orchestral aria"))
        self.assertEqual(MI.tonalite_fr("C# minor"), "do dièse mineur")
        self.assertEqual(MI.tonalite_fr("B♭ major"), "si bémol majeur")

    def test_amelioration_sans_nom(self):
        from app import musique_ia as MI
        r = MI.lire_amelioration('Voici : {"caption": "smooth crooner like Sinatra, big band", "bpm": 98, "keyscale": "F major", '
                                 '"time_signature": "4/4"}', ["Frank Sinatra"])
        self.assertNotIn("sinatra", r["caption"].lower())
        self.assertEqual((r["bpm"], r["keyscale"], r["mesure"]), (98, "F major", "4/4"))
        self.assertEqual(MI.lire_amelioration('{"caption": "x", "bpm": 999}')["bpm"], 0)


class TestAnalyse(unittest.TestCase):
    def test_tempo_tonalite_mesure(self):
        from app import musique_ia as MI
        for bpm, notes, mes, ton in ((120, [220, 261.6, 329.6], 4, "A minor"), (96, [261.6, 329.6, 392], 4, "C major"),
                                     (150, [293.7, 370, 440], 3, "D major")):
            m = MI.mesurer(piste(bpm, notes, mes=mes), SR)
            self.assertLessEqual(abs(m["bpm"] - bpm), 2, (bpm, m))
            self.assertEqual(m["tonalite"], ton)
            self.assertEqual(m["mesure"], f"{mes}/4")

    def test_analyser_un_fichier(self):
        from app import musique_ia as MI
        d = tempfile.mkdtemp()
        f = ecrire_mp3(os.path.join(d, "morceau.mp3"), piste(120, [220, 261.6, 329.6], dur=20))
        r = MI.analyser(f, {}, ecouter=False)
        self.assertEqual(r["bpm"], 120)
        self.assertIn("minor", r["caption_en"])
        self.assertFalse(r["compris"])
        self.assertNotIn("paroles", r)


class TestCreation(unittest.TestCase):
    def test_droits_et_options_du_moteur(self):
        from app import musique_ia as MI, creatif as C
        d = tempfile.mkdtemp()
        src = ecrire_mp3(os.path.join(d, "theme.mp3"), piste(100, [261.6], dur=12))
        recu = {}
        ancien = C.musique

        def faux(style, sortie, duree=60, params=None, instrumental=True, paroles="", langue="fr", bpm=0, progression=None, arret=None,
                 voix="", options=None):
            recu.update(style=style, options=options, bpm=bpm)
            open(sortie, "wb").write(b"x")
            return sortie
        C.musique = faux
        try:
            f = dict(MI.fiche_vide(), style="symphonie", source={"chemin": src, "force": 0.4})
            with self.assertRaises(RuntimeError):                       # pas déclaré libre : seulement s'en inspirer
                MI.creer(f, os.path.join(d, "o.mp3"))
            MI.declarer(src, a_moi=True)
            out, c = MI.creer(f, os.path.join(d, "o.mp3"))
            self.assertEqual(recu["options"]["source"], src)
            self.assertAlmostEqual(recu["options"]["force_source"], 0.4)
            self.assertEqual(recu["options"]["keyscale"], "C minor")
            self.assertEqual(recu["bpm"], 96)
            voix = ecrire_mp3(os.path.join(d, "ma_voix.mp3"), piste(90, [220], dur=8))
            f2 = dict(MI.fiche_vide(), voix_reference={"chemin": voix})
            with self.assertRaises(RuntimeError):                       # voix non déclarée : refusée
                MI.creer(f2, os.path.join(d, "o2.mp3"))
            MI.declarer(voix, voix_a_moi=True)
            MI.creer(f2, os.path.join(d, "o2.mp3"))
            self.assertEqual(recu["options"]["reference"], voix)
            rec = MI.recette(dict(f, inspiration={"caption_en": "x", "chemin": "/secret", "mesures": {}}), c)
            self.assertNotIn("chemin", rec["fiche"]["inspiration"])
            self.assertTrue(rec["empreinte"])
        finally:
            C.musique = ancien

    def test_reorchestration_demande_au_moteur(self):
        """Le moteur reçoit « cover » et le morceau source, sans l'étape de composition."""
        from app import creatif as C, packs_ia as P
        d = tempfile.mkdtemp()
        src = ecrire_mp3(os.path.join(d, "s.mp3"), piste(100, [261.6], dur=12))
        appels = []
        ancien = C._lancer, P.dossier_modele

        def lancer(genre, args, *a, **k):
            appels.append(args)
            req = args[args.index("--request") + 1]
            json.load(open(req))
            open(os.path.join(os.path.dirname(req), "demande.mp3"), "wb").write(b"son")
        C._lancer, P.dossier_modele = lancer, (lambda cle: d)
        try:
            out = C._musique("epic", os.path.join(d, "out.mp3"), 10, {}, True, "", "fr", 100, None, lambda: False, "m", {}, {}, "musique",
                             options={"source": src, "force_source": 0.3, "keyscale": "D minor", "timesignature": "3"})
            self.assertTrue(os.path.exists(out))
            args = appels[0]
            self.assertIn("--src-audio", args)
            req = json.load(open(args[args.index("--request") + 1]))
            self.assertEqual(req["task_type"], "cover")
            self.assertAlmostEqual(req["audio_cover_strength"], 0.3)
            self.assertEqual((req["keyscale"], req["timesignature"]), ("D minor", "3"))
        finally:
            C._lancer, P.dossier_modele = ancien


class TestEnLigne(unittest.TestCase):
    def test_nom_propre(self):
        from app import musique_en_ligne as ML
        nom, titre, artiste = ML.nom_propre({"titre": "Orchestre X - Valse (Official Video) [HD]", "artiste": "Orchestre X"})
        self.assertEqual((nom, titre), ("Orchestre X - Valse", "Valse"))
        self.assertEqual(ML._net_artiste("Quelqu'un - Topic"), "Quelqu'un")

    def test_archives_libres_et_telechargement(self):
        from app import musique_en_ligne as ML, musique_ia as MI
        import urllib.request
        d = tempfile.mkdtemp()
        son = open(ecrire_mp3(os.path.join(d, "src.mp3"), piste(100, [261.6], dur=5)), "rb").read()
        reponses = {
            "advancedsearch": json.dumps({"response": {"docs": [
                {"identifier": "requiem1937", "title": "Requiem", "creator": "Orchestre", "year": "1937",
                 "licenseurl": "http://creativecommons.org/publicdomain/mark/1.0/"},
                {"identifier": "nc", "title": "Autre", "licenseurl": "https://creativecommons.org/licenses/by-nc/4.0/"}]}}).encode(),
            "metadata": json.dumps({"files": [{"name": "requiem.mp3", "format": "VBR MP3"}]}).encode(),
            "download": son}

        class Rep(io.BytesIO):
            headers = {}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def ouvrir(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else req
            for k, v in reponses.items():
                if k in url:
                    r = Rep(v)
                    r.headers = {"Content-Length": str(len(v))}
                    return r
            raise AssertionError(url)
        ancien = urllib.request.urlopen
        urllib.request.urlopen = ouvrir
        try:
            res = ML.chercher("requiem", "archive")
            self.assertEqual([r["licence_libre"] for r in res], [True, False])
            self.assertEqual([r["libre"] for r in res], [False, False])     # jamais déclaré libre d'office
            f = ML.telecharger(res[0], d, libre=True)
        finally:
            urllib.request.urlopen = ancien
        self.assertTrue(f.endswith("Orchestre - Requiem.mp3"))
        self.assertTrue(MI.peut_partir_de(f))
        tags = moteur.sonder(f)
        self.assertGreater(tags.get("duree", 0), 4)
        sortie = subprocess.run([moteur.ffprobe(), "-v", "error", "-show_entries", "format_tags", "-of", "json", f],
                                capture_output=True, text=True).stdout
        t = {k.lower(): v for k, v in json.loads(sortie)["format"]["tags"].items()}
        self.assertEqual(t["title"], "Requiem")
        self.assertIn("archive.org", t["comment"])


class TestRecettes(unittest.TestCase):
    def test_liste_deja_fait_et_avant_apres(self):
        from app import recettes_ia as R, creations
        from app.projet import Projet
        rec = {"famille": "musique", "intention": "musique", "fiche": {"style": "valse", "duree": 20}, "anglais": "viennese waltz"}
        self.assertEqual(R.empreinte(rec), R.empreinte(dict(rec, moteur="autre", date="hier")))
        d = tempfile.mkdtemp()
        p = Projet()
        f = ecrire_mp3(os.path.join(d, "valse.mp3"), piste(168, [293.7], dur=6, mes=3))
        creations.ecrire(f, rec)
        m = p.ajouter_media(f, moteur.sonder(f))
        R.noter_recette(m)
        self.assertEqual(m["recette"]["empreinte"], R.empreinte(rec))
        self.assertEqual(R.a_traiter(p), [])
        os.remove(f)                                    # le fichier manque : à refaire
        lignes = R.a_traiter(p)
        self.assertEqual(lignes[0]["etat"], "a_refaire")
        self.assertIsNone(lignes[0]["existant"])
        self.assertEqual(R.moteurs_possibles(lignes[0])[0][0], "locale")
        # la même demande déjà faite sur ce poste : reprise, jamais recalculée
        fait = ecrire_mp3(os.path.join(creations.dossier(), "musique_deja.mp3"), piste(168, [293.7], dur=6, mes=3))
        creations.ecrire(fait, dict(rec, empreinte=R.empreinte(rec)))
        lignes = R.a_traiter(p)
        self.assertEqual(lignes[0]["existant"], fait)
        self.assertEqual(R.calculer(lignes[0], "locale"), fait)
        # demandée sur le téléphone, à calculer sur le PC
        m2 = p.ajouter_media(os.path.join(d, "plus_tard.mp3"), {"duree": 10})
        m2.update(recette=dict(rec, fiche={"style": "opera"}), a_calculer={"appareil": "téléphone"})
        etats = sorted(l["etat"] for l in R.a_traiter(p))
        self.assertEqual(etats, ["a_calculer", "a_refaire"])

    def test_images_et_voix_refaites(self):
        """Tableau des recettes : image sur ce poste ou avec Gemini (coût annoncé, marquée payée), voix ; l'image de départ suit."""
        from app import recettes_ia as R, creations, ia, creatif as C, diction
        from PySide6.QtGui import QImage, QColor
        d = tempfile.mkdtemp()
        res = os.path.join(d, "aquarelle.png")
        q = QImage(64, 64, QImage.Format_RGB32)
        q.fill(QColor("#336699"))
        q.save(res)
        q.save(res + ".source.png")
        rec = {"famille": "image", "effet": "aquarelle", "prompt": "aquarelle", "anglais": "watercolor painting", "force": 0.5,
               "source_image": "aquarelle.png.source.png"}
        m = {"id": "m1", "nom": "aquarelle.png", "chemin": os.path.join(d, "absent.png"), "recette": rec}
        ligne = {"media": m, "recette": rec, "intention": R.intention(rec), "etat": "a_refaire", "existant": None, "paye": False}
        m["chemin"] = res + ".absent"
        os.rename(res + ".source.png", os.path.join(creations.dossier(), "aquarelle.png.source.png"))
        self.assertTrue(R.source_image(ligne))
        anciens = ia.retoucher_image, C.image, diction.dire, R._a_clef
        recu = {}
        try:
            R._a_clef = lambda params: True

            def retoucher(params, png, consigne, *a, **k):
                recu["gemini"] = consigne
                return open(res, "rb").read()
            ia.retoucher_image = retoucher

            def image(prompt, sortie, params=None, init=None, force=0.55, **k):
                recu["locale"] = (prompt, init, force)
                q.save(sortie)
            C.image = image
            self.assertEqual([x[0] for x in R.moteurs_possibles(ligne, {})], ["locale", "gemini", "outil"])
            out = R.calculer(ligne, "gemini", {})
            self.assertEqual(recu["gemini"], "watercolor painting")
            nouv = creations.lire(out)
            self.assertTrue(nouv["paye"])
            self.assertTrue(os.path.exists(out + ".source.png"))
            self.assertEqual(R.calculer(ligne, "locale", {}), out)     # déjà fait (et payé) : repris, rien n'est recalculé
            self.assertNotIn("locale", recu)
            os.remove(out)
            out2 = R.calculer(ligne, "locale", {})
            self.assertEqual(recu["locale"], ("watercolor painting", R.source_image(ligne), 0.5))
            self.assertTrue(os.path.exists(out2))
            rv = {"famille": "image", "replique": "Bonjour à tous", "diction": "naturel"}
            lv = {"media": {"id": "v"}, "recette": rv, "intention": R.intention(rv), "existant": None, "paye": False}
            self.assertEqual(lv["intention"], "voix")
            diction.dire = lambda texte, sortie, params, style="naturel", moteur_voix="local", **k: (recu.__setitem__("voix", (texte, moteur_voix)),
                                                                                                   open(sortie, "wb").write(b"RIFF"))
            R.calculer(lv, "gemini", {})
            self.assertEqual(recu["voix"], ("Bonjour à tous", "gemini"))
        finally:
            ia.retoucher_image, C.image, diction.dire, R._a_clef = anciens

    def test_fenetres(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app.dialogues_recettes import DialogueCreations, DialogueAvantApres
        from app.dialogues_musique_ia import DialogueFabriqueMusique, DialogueMusiqueEnLigne, Hote
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        a = ecrire_mp3(os.path.join(d, "a.mp3"), piste(120, [220], dur=4))
        b = ecrire_mp3(os.path.join(d, "b.mp3"), piste(120, [261.6], dur=4))
        m = ed.projet.ajouter_media(a, moteur.sonder(a))
        m.update(recette={"intention": "musique", "fiche": {"style": "valse"}}, a_calculer={"appareil": "téléphone"})
        dc = DialogueCreations(ed)
        self.assertEqual(dc.arbre.topLevelItemCount(), 1)
        av = DialogueAvantApres(dc, dc.lignes[0], b)
        av.prendre()
        self.assertEqual(m["chemin"], b)
        self.assertNotIn("a_calculer", m)
        self.assertIn(a, m["versions"])
        h = Hote()
        poses = []
        h.poser = lambda c, r, ligne: poses.append(c)
        fm = DialogueFabriqueMusique(f, f.params, h, {"style": "gregorien", "duree": 30, "instrumental": False, "voix": "gregorien"}, 30)
        self.assertEqual(fm.style.currentData(), "gregorien")
        self.assertIn("monks", fm.apercu_consigne.text())
        fm._fini(fm.fiche(), (b, {"caption": "x"}), None)
        self.assertTrue(any(fm.actions.itemAt(i).widget().text() == "Poser sous la vidéo" for i in range(fm.actions.count())))
        fm.done(0)
        ml = DialogueMusiqueEnLigne(f, f.params, poser=lambda c: None)
        self.assertEqual(ml.source.count(), 3)
        ml.done(0)
        ed.projet.modifie = False
        f.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
