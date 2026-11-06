"""0.6 et 0.7 : IA créative locale (images, vidéo, musique, agrandissement, ralenti, dessin animé, profondeur, photo 3D),
catalogue d'effets IA modifiable, Atelier IA. Les moteurs sont remplacés ici par de faux programmes qui imitent leur
sortie ; l'essai avec les vrais moteurs et modèles est fait par le workflow « Moteurs creatifs »."""
import json, os, stat, subprocess, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur

FAUX_SD = r'''#!/usr/bin/env python3
import sys, subprocess
a = sys.argv[1:]
out = a[a.index("-o") + 1]
w, h = a[a.index("-W") + 1], a[a.index("-H") + 1]
print("chargement", flush=True)
for i in range(1, 5):
    print(f"  |=====| {i}/4 - 0.10s/it", flush=True)
couleur = "red" if "-i" in a else "blue"
if "vid_gen" in a:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={couleur}:s={w}x{h}:d=1:r=16", "-c:v", "libvpx-vp9", out], check=True)
else:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={couleur}:s={w}x{h}", "-frames:v", "1", out], check=True)
'''
FAUX_LM = r'''#!/usr/bin/env python3
import sys, json, os
a = sys.argv[1:]
req = a[a.index("--request") + 1]
d = json.load(open(req))
assert d["lyrics"] and d["duration"] > 0 and d["lm_model"]
d["audio_codes"] = "1,2,3"
base = os.path.splitext(req)[0]
json.dump(d, open(base + "0.json", "w"))
print("1/2", flush=True); print("2/2", flush=True)
'''
FAUX_SYNTH = r'''#!/usr/bin/env python3
import sys, json, os, subprocess
a = sys.argv[1:]
req = a[a.index("--request") + 1]
d = json.load(open(req))
assert d.get("audio_codes")
base = os.path.splitext(req)[0]
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=f=440:d={min(3, d['duration'])}", base + "0.mp3"], check=True)
print("8/8", flush=True)
'''


def ecrire_exe(chemin, texte):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w") as f:
        f.write(texte)
    os.chmod(chemin, os.stat(chemin).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class Test060(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        os.environ["PHILCUT_IA_DOSSIER"] = os.path.join(cls.d, "ia")
        man1 = {"format": 1, "moteurs": {}, "modeles": {}}
        man2 = {"format": 1, "moteurs": {"image": {"linux": {"fichier": "x"}}, "musique": {"linux": {"fichier": "y"}}},
                "modeles": {"image_rapide": {"genre": "image", "nom": "Images rapides", "moteur": "image", "moteur_gpu": "image_gpu",
                                             "fichiers": [{"nom": "m.safetensors", "role": "modele"}], "taille": 1, "etapes": 4, "cfg": 1.0,
                                             "taille_px": 256, "args": ["-m", "{modele}", "-p", "{prompt}", "-W", "{largeur}", "-H", "{hauteur}",
                                                                        "--steps", "{etapes}", "-o", "{sortie}"],
                                             "args_init": ["-i", "{image}", "--strength", "{force}"]},
                            "musique_rapide": {"genre": "musique", "nom": "Musique", "moteur": "musique", "taille": 1,
                                               "fichiers": [{"nom": f, "role": r} for r, f in (("lm", "lm.gguf"), ("dit", "dit.gguf"),
                                                                                               ("vae", "vae.gguf"), ("texte", "t.gguf"))]},
                            "video_wan": {"genre": "video", "nom": "Vidéo", "moteur": "image", "taille": 1, "taille_px": 256,
                                          "fichiers": [{"nom": "w.gguf", "role": "modele"}],
                                          "args": ["-M", "vid_gen", "-p", "{prompt}", "-W", "{largeur}", "-H", "{hauteur}", "-o", "{sortie}"],
                                          "args_init": ["-i", "{image}"]}}}
        for nom, m in (("m1.json", man1), ("m2.json", man2)):
            with open(os.path.join(cls.d, nom), "w") as f:
                json.dump(m, f)
        os.environ["PHILCUT_IA_MANIFESTE"] = os.path.join(cls.d, "m1.json")
        os.environ["PHILCUT_IA_MANIFESTE2"] = os.path.join(cls.d, "m2.json")
        from app import packs_ia as P
        P._manifeste = None
        P._carte = ""
        # faux moteurs et modèles « installés »
        ecrire_exe(os.path.join(P.dossier_moteur("image"), "sd-cli"), FAUX_SD)
        ecrire_exe(os.path.join(P.dossier_moteur("musique"), "ace-lm"), FAUX_LM)
        ecrire_exe(os.path.join(P.dossier_moteur("musique"), "ace-synth"), FAUX_SYNTH)
        for g in ("image", "musique"):
            P._noter(f"moteur_{g}", {"genre": g})
        for cle, m in P.modeles(avec_essai=True).items():
            os.makedirs(P.dossier_modele(cle), exist_ok=True)
            for f in m["fichiers"]:
                open(os.path.join(P.dossier_modele(cle), f["nom"]), "w").close()
            P._noter(cle, {"genre": m["genre"], "nom": m["nom"], "fichiers": [f["nom"] for f in m["fichiers"]],
                           "roles": {f["role"]: f["nom"] for f in m["fichiers"]}})
        cls.P = P
        cls.img = os.path.join(cls.d, "src.png")
        subprocess.run([moteur.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180", "-frames:v", "1", cls.img], check=True)

    @classmethod
    def tearDownClass(cls):
        for k in ("PHILCUT_IA_DOSSIER", "PHILCUT_IA_MANIFESTE", "PHILCUT_IA_MANIFESTE2"):
            os.environ.pop(k, None)
        cls.P._manifeste = None

    def test_catalogue_fusionne_et_moteurs(self):
        P = self.P
        m = P.modeles(avec_essai=True)
        self.assertIn("image_rapide", m)
        self.assertEqual(P.moteur_du_modele(m["image_rapide"]), "image")
        self.assertEqual(P.moteur_gpu_du_modele(m["image_rapide"]), "image_gpu")
        self.assertTrue(P.moteur_installe("image"))
        self.assertEqual(P.modele_actif("image"), "image_rapide")
        self.assertTrue(P.executable("upscale").endswith("realesrgan-ncnn-vulkan"))

    def test_image_phrase_et_retouche(self):
        from app import creatif as C
        etapes = []
        out = C.image("a red car", os.path.join(self.d, "a.png"), {}, progression=etapes.append)
        self.assertTrue(os.path.getsize(out) > 50)
        self.assertEqual(etapes[-1], 1.0)
        out2 = C.image("cartoon", os.path.join(self.d, "b.png"), {}, init=self.img, force=0.6)
        from PySide6.QtGui import QImage
        q = QImage(out2)
        self.assertEqual(q.width() % 64, 0)
        self.assertGreater(q.pixelColor(10, 10).red(), 200)          # le faux moteur a vu l'image d'origine (-i)

    def test_video_wan(self):
        from app import creatif as C
        out = C.video("slow push in", os.path.join(self.d, "v.mp4"), {}, init=self.img, secondes=1.0)
        self.assertGreater(float(moteur.sonder(out)["duree"]), 0.5)

    def test_musique(self):
        from app import creatif as C
        out = C.musique("lofi", os.path.join(self.d, "m.mp3"), duree=12, params={})
        self.assertTrue(os.path.getsize(out) > 500)
        self.assertGreater(len(C.STYLES_MUSIQUE), 5)

    def test_dessin_profondeur_photo3d_video(self):
        import cv2
        from app import creatif as C
        img = cv2.imread(self.img)
        self.assertEqual(C.dessin_classique(img).shape, img.shape)
        self.assertEqual(C.anime_image(img).shape, img.shape)        # sans modèle : repli OpenCV
        p = C.profondeur(img)
        self.assertGreater(p[-1].mean(), p[0].mean())                 # estimation sans modèle : le bas est plus proche
        out = C.photo_3d(img, os.path.join(self.d, "p3d.mp4"), secondes=1.0, ips=10)
        self.assertAlmostEqual(float(moteur.sonder(out)["duree"]), 1.0, delta=0.2)
        v = commun.video_test(self.d, "court.mp4", duree=2)
        out = C.traiter_video(v, os.path.join(self.d, "anime.mp4"), C.dessin_classique, 0.5, 1.0, 10)
        self.assertAlmostEqual(float(moteur.sonder(out)["duree"]), 1.0, delta=0.25)
        self.assertEqual(C.flou_arriere_plan(img).shape, img.shape)
        out = C.transition_3d(img, img[:, ::-1].copy(), os.path.join(self.d, "tr.mp4"), 1.2, 20)
        self.assertAlmostEqual(float(moteur.sonder(out)["duree"]), 1.2, delta=0.2)

    def test_catalogue_effets_modifiable(self):
        from app import effets_ia as EI
        pa = {}
        tous = EI.tous(pa)
        self.assertTrue({"image", "logo", "video", "musique"} <= {e["famille"] for e in tous})
        e = next(x for x in tous if x["id"] == "anime")
        EI.enregistrer(pa, e, "my own prompt", 0.4)
        e2 = next(x for x in EI.tous(pa) if x["id"] == "anime")
        self.assertEqual((e2["prompt"], e2["force"], e2["modifie"]), ("my own prompt", 0.4, True))
        cle = EI.enregistrer(pa, e, "another", 0.7, "Mon style", nouveau=True)
        self.assertTrue(any(x["id"] == cle and x.get("perso") for x in EI.tous(pa)))
        EI.retablir(pa, "anime")
        self.assertNotEqual(next(x for x in EI.tous(pa) if x["id"] == "anime")["prompt"], "my own prompt")
        self.assertTrue(EI.disponible(next(x for x in tous if x["id"] == "v_anime"))[0])

    def test_atelier_ia_dans_l_editeur(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        v = commun.video_test(self.d, "plan.mp4", duree=3)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.ajouter_a_la_timeline(m["id"])
        ed.aller_a(1.0)
        app.processEvents()
        from app.dialogues_creatif import DialogueAtelierIA
        dl = DialogueAtelierIA(ed, "video")
        self.assertIsNotNone(dl.source)
        dl.liste.setCurrentRow([dl.liste.item(i).data(0x0100)["id"] for i in range(dl.liste.count())].index("v_anime"))
        dl.creer()
        t0 = time.time()
        while dl.tache.isRunning() and time.time() - t0 < 120:
            app.processEvents()
            time.sleep(0.05)
        for _i in range(20):
            app.processEvents()
        au_dessus = [c for c in ed.projet.clips if c["piste"] != "video"]
        self.assertEqual(len(au_dessus), 1, dl.info.text())
        self.assertEqual(au_dessus[0]["incrust"]["echelle"], 1.0)
        # image retouchée par la phrase (faux moteur), puis insérée à la tête de lecture
        dl.famille.setCurrentIndex(dl.famille.findData("image"))
        dl.creer()
        while dl.tache.isRunning():
            app.processEvents()
            time.sleep(0.05)
        for _i in range(20):
            app.processEvents()
        self.assertTrue(dl.resultat and dl.resultat.endswith(".png"), dl.info.text())
        n = len(ed.projet.clips_piste("video"))
        ed.inserer_image(dl.resultat, 1.0, 2.0, "essai")
        self.assertEqual(len(ed.projet.clips_piste("video")), n + 2)       # coupé + image insérée
        dl.reject()
        ed.projet.modifie = False
        f.close()

    def test_atelier_musique_traduit_et_montre_l_avancement(self):
        """0.9.0 : la phrase tapée en français part en anglais au moteur, l'avancement se voit dans la fenêtre, une phrase
        intraduisible (sans réseau) est refusée avec la demande d'écrire en anglais."""
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        f.show()
        ed = f.nouveau_projet("16:9")
        from app.dialogues_creatif import DialogueAtelierIA
        dl = DialogueAtelierIA(ed, "musique")
        dl.show()
        dl.liste.setCurrentRow(0)
        dl.duree.setValue(10)
        dl.prompt.setPlainText("musique douce au piano")
        dl.creer()
        self.assertFalse(dl.barre.isHidden())
        vus = []
        dl.tache.progression.connect(lambda fr, t: vus.append(t))
        t0 = time.time()
        while dl.tache.isRunning() and time.time() - t0 < 120:
            app.processEvents()
            time.sleep(0.05)
        for _i in range(20):
            app.processEvents()
        self.assertEqual(dl._ph["en"], "music soft at the piano")
        self.assertIn("music soft at the piano", dl.envoye.text())
        self.assertTrue(any("2/2" in t for t in vus), vus)                  # étapes nommées
        self.assertTrue(dl.barre.isHidden())
        self.assertIn(_txt("Musique créée"), dl.info.text())
        # intraduisible sans réseau : rien n'est lancé, on demande l'anglais
        dl.prompt.setPlainText("chanson rigolote pour mon anniversaire")
        dl.creer()
        while dl.tache.isRunning():
            app.processEvents()
            time.sleep(0.05)
        for _i in range(20):
            app.processEvents()
        self.assertIn("anglais", dl.info.text())
        self.assertIn("rigolote", dl.info.text())
        self.assertGreaterEqual(dl.actions.count(), 1)                      # « Réessayer »
        dl.reject()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()



def _txt(t):
    return t


if __name__ == "__main__":
    unittest.main()
