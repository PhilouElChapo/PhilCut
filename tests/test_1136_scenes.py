"""1.3.5 (choix de Philippe, 25/11 22h50) : des scènes, pas des gestes ; références propres ; une image de départ par scène ;
brouillon relu par l'IA avant de payer."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import assistant_creation as A, sequence_ia as Q, brouillon as B

ANALYSE = {"personnages": [
    {"nom": "Femme brune", "genre": "personne", "sur_image": True, "position": "gauche", "description": "manteau brun"},
    {"nom": "Pilote", "genre": "personne", "sur_image": False, "description": "uniforme bleu marine, barbe"},
    {"nom": "Hôtesse", "genre": "personne", "sur_image": False, "description": "tailleur bleu marine"},
    {"nom": "Jet", "genre": "objet", "sur_image": True, "position": "centre", "description": "petit jet blanc et bleu"}],
    "lieux": [{"nom": "Tarmac", "sur_image": True, "description": "tarmac gris, ciel nuageux"}],
    "plans": [
        {"action": "La femme sourit face caméra puis se tourne vers le jet", "personnages": ["Femme brune", "Jet"], "duree": 8,
         "depart": "La femme debout devant le jet", "lieu": "Tarmac", "image_clef": True},
        {"action": "Le pilote et l'hôtesse arrivent côte à côte. Le pilote serre la main de la femme pendant que l'hôtesse sourit à côté",
         "personnages": ["Femme brune", "Pilote", "Hôtesse", "Jet"], "duree": 12, "lieu": "Tarmac",
         "depart": "La femme devant le jet, le pilote et l'hôtesse à droite, à dix mètres"},
        {"action": "Le jet roule puis décolle", "personnages": ["Jet"], "duree": 10, "depart": "Le jet porte fermée, personne dehors",
         "lieu": "Tarmac"}]}


def _png(d, nom, coul="gray"):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(400, 300, QImage.Format_RGB32)
    q.fill(QColor(coul))
    q.save(ch)
    return ch


class TestScenes(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.img = _png(self.d, "rush.png")
        self.seq = A.appliquer(Q.nouvelle("9:16"), A.lire_analyse(ANALYSE), self.img)

    def test_decoupage(self):
        s = self.seq
        self.assertEqual(s["mode"], "scenes")
        self.assertEqual(len(s["plans"]), 3)                         # « et », « puis », « pendant que » : rien n'est coupé
        self.assertIn("côte à côte", s["plans"][1]["action"])
        self.assertTrue(all(not pl["enchainer"] for pl in s["plans"]))        # chaque scène part de son image
        self.assertTrue(all(pl["sans_fin"] and not pl["clef"] for pl in s["plans"]))    # aucune image d'arrivée imposée
        self.assertEqual(s["plans"][1]["etat_depart"], "La femme devant le jet, le pilote et l'hôtesse à droite, à dix mètres")
        self.assertEqual(A.etat(s)["plans"][1]["depart"], s["plans"][1]["etat_depart"])
        f, dep, arr = A.a_preparer(s, {"clef_gemini": "x"})
        self.assertEqual((dep, arr), (2, 0))                         # une image de départ par scène (la 1re est le rush)
        self.assertIn("SCENE entière de 8 à 15 secondes", A.CONSIGNE_ANALYSE)
        self.assertIn("sans aucun personnage visible", A.CONSIGNE_ANALYSE)

    def test_references_propres(self):
        s = self.seq
        for p in s["personnages"]:
            p["planche"] = _png(self.d, "planche_" + p["nom"] + ".png")
        pl = s["plans"][1]
        self.assertEqual(len(Q.references_du_plan(s, pl)), 4)
        self.assertEqual(len(Q.references_du_plan(s, pl, sans_objets=True)), 3)        # le jet vient de l'image de départ
        recu = {}
        from app import generateurs_video as GV
        anc = GV.generer, GV.modele
        GV.modele = lambda i, p=None: {"references": True}
        GV.generer = lambda *a, **k: recu.update(k, texte=a[2], image=a[6])
        try:
            pl["image"] = self.img
            Q.fabriquer_plan(s, 1, {}, "kling-o3-ref")
        finally:
            GV.generer, GV.modele = anc
        self.assertEqual(len(recu["references"]), 3)
        self.assertIsNone(recu["image_fin"])
        self.assertIn("One continuous take", recu["texte"])

    def test_image_de_depart(self):
        s = self.seq
        from app import ia
        recu = {}
        anc, ancd = ia.generer_image_refs, Q.dossier
        ia.generer_image_refs = lambda params, c, refs: recu.update(c=c, refs=refs) or b"png"
        Q.dossier = lambda seq: self.d
        try:
            Q.image_depart(s, 1, {}, "gemini")
        finally:
            ia.generer_image_refs, Q.dossier = anc, ancd
        self.assertIn("VERY FIRST INSTANT", recu["c"])
        self.assertIn(self.img, recu["refs"])                        # le décor de la scène d'avant

    def test_brouillon_relu(self):
        s = self.seq
        from app import correcteur as C
        anc, ancd = C.relire, Q.dossier
        Q.dossier = lambda seq: self.d
        os.makedirs(os.path.join(self.d, "brouillon"))
        for i in (0, 1):
            open(os.path.join(self.d, "brouillon", f"plan{i + 1:02d}_omni-360p.mp4"), "w").write("x")
        C.relire = lambda params, seq, i, niveau: C.defaut(seq, i, 2.0, f"défaut {i}", "ia", "action")
        try:
            d = B.relire(s, "omni-360p", {}, "claude")
        finally:
            C.relire, Q.dossier = anc, ancd
        self.assertEqual([(x["plan"], x["texte"]) for x in d], [(0, "défaut 0"), (1, "défaut 1")])
        self.assertEqual(B.texte_corrections(d), "Scène 1 : défaut 0\nScène 2 : défaut 1")
        self.assertFalse(s.get("defauts"))                           # la séquence elle-même n'est pas touchée

    def test_image_clef_cochee_gardee(self):
        s = self.seq
        s["plans"][1].update(clef=True, sans_fin=False, clef_main=True, image_fin=self.img)
        n = A.appliquer(s, A.lire_analyse(ANALYSE), self.img)
        self.assertTrue(n["plans"][1]["clef"] and not n["plans"][1]["sans_fin"])
        self.assertFalse(n["plans"][0]["clef"])

    def test_modifier_garde_les_lieux(self):
        s = self.seq
        anc = A.demander
        A.demander = lambda *a, **k: {"personnages": ANALYSE["personnages"], "plans": ANALYSE["plans"][:2]}
        try:
            n, _m = A.modifier({}, s, "plus court")
        finally:
            A.demander = anc
        self.assertEqual([x["nom"] for x in n["lieux"]], ["Tarmac"])
        self.assertEqual(len(n["plans"]), 2)


class TestFenetre(unittest.TestCase):
    def test_brouillon_avant_de_payer(self):
        import time
        from app.fenetre import Fenetre
        from app import moteur, generateurs_video as GV, ia
        from app import dialogues_assistant_creation as D
        from app.dialogues_creatif import ApercuCreation

        def attendre(cond, s=60):
            fin = time.time() + s
            while time.time() < fin and not cond():
                app.processEvents()
                time.sleep(0.02)
            return cond()
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_gemini="x", clef_fal="a:b", clef_claude="k")
        d = tempfile.mkdtemp()
        v = commun.video_test(d)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        png = open(_png(d, "p.png"), "rb").read()
        demandes = []

        def faux_demander(params, consigne, texte, images=(), niveau="claude", max_jetons=3000):
            demandes.append(texte)
            if "comme une scripte" in consigne:
                return {"defauts": [{"t": 1, "quoi": "action", "texte": "le pilote n'arrive pas"}]}
            return ANALYSE

        def faux_generer(params, ident, texte, sortie, duree, fmt, image, *a, **k):
            moteur.lancer(["-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10:duration=1", "-pix_fmt", "yuv420p", sortie])
            return sortie
        anc = (A.demander, ia.generer_image, ia.generer_image_refs, GV.generer, ApercuCreation.charger)
        A.demander, GV.generer = faux_demander, faux_generer
        ia.generer_image = lambda p, cns, *a, **k: png
        ia.generer_image_refs = lambda p, cns, refs, delai=240: png
        ApercuCreation.charger = lambda *a, **k: None
        try:
            dl = ed.assistant_creation(c)
            dl._test_oui, dl._test_precision, dl._test_relire = True, "", False
            dl.c_realisateur.setChecked(False) if hasattr(dl, "c_realisateur") else None
            dl.histoire.setPlainText("Une femme sur le tarmac, le pilote et l'hôtesse arrivent, le jet décolle.")
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_QUI and not dl._en_calcul()))
            dl.accord.setChecked(True)
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_PLANS)
            self.assertEqual(dl.t_plans.rowCount(), 3)                        # trois scènes, rien de coupé
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_IMAGES and not dl._en_calcul()))
            self.assertTrue(all(pl.get("image") for pl in dl.seq["plans"]))   # une image de départ par scène
            self.assertFalse(any(pl.get("image_fin") for pl in dl.seq["plans"]))
            dl._test_brouillon = "brouillon"
            dl.suivant()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and (dl.seq.get("brouillon") or {}).get("defauts") is not None))
            self.assertEqual(dl.pages.currentIndex(), D.P_IMAGES)             # la vraie fabrication attend
            self.assertFalse(any(pl.get("fichier") for pl in dl.seq["plans"]))
            self.assertEqual(len(dl.seq["brouillon"]["defauts"]), 3)
            b = dl._dlg_brouillon
            b._br.click()
            self.assertIn("Scène 2 : le pilote n'arrive pas", b.corrections.toPlainText())
            b.corrections.setPlainText(b.corrections.toPlainText() + "\net l'hôtesse en tailleur")     # modifiable
            b._ba.click()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and dl.pages.currentIndex() == D.P_PLANS))
            self.assertIn("l'hôtesse en tailleur", demandes[-1])
            self.assertFalse(dl.seq["brouillon_vu"])
            dl._test_brouillon = "direct"
            self.assertFalse(dl._brouillon_d_abord())
            # une ancienne création (geste par geste) : « 1. Votre idée » puis Suivant propose de la redécouper en scènes
            dl.seq["mode"] = ""
            fiches = [p.get("planche") for p in dl.seq["personnages"]]
            dl._test_redecouper = True
            dl.aller(D.P_IDEE)
            dl.suivant()
            self.assertTrue(attendre(lambda: not dl._en_calcul() and dl.seq.get("mode") == "scenes"))
            self.assertEqual(dl.pages.currentIndex(), D.P_PLANS)
            self.assertIn("Redécoupe toute l'histoire en scènes", demandes[-1])
            self.assertEqual([p.get("planche") for p in dl.seq["personnages"]], fiches)      # les fiches payées sont gardées
        finally:
            A.demander, ia.generer_image, ia.generer_image_refs, GV.generer, ApercuCreation.charger = anc


if __name__ == "__main__":
    unittest.main()
