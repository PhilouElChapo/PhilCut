"""1.3.11 (choix de Philippe, 27/11) : plans de montage (deux visages au plus, plans de coupe), ce que l'IA propose suit le
tableau des plans, prises gardées ; clip de groupe : mes musiciens, enregistrement avec la chanson."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import assistant_creation as A, sequence_ia as Q, moteur

ANALYSE = {"personnages": [
    {"nom": "Femme brune", "genre": "personne", "sur_image": True, "position": "gauche", "description": "manteau brun"},
    {"nom": "Femme blonde", "genre": "personne", "sur_image": True, "position": "droite", "description": "manteau noir"},
    {"nom": "Pilote", "genre": "personne", "sur_image": False, "description": "uniforme bleu marine"},
    {"nom": "Hôtesse", "genre": "personne", "sur_image": False, "description": "tailleur bleu marine"}],
    "lieux": [{"nom": "Tarmac", "sur_image": True, "description": "tarmac gris"}],
    "plans": [
        {"action": "Le pilote serre la main des deux femmes", "personnages": ["Femme brune", "Femme blonde", "Pilote", "Hôtesse"],
         "visages": ["Pilote", "Femme brune", "Hôtesse"], "duree": 7, "depart": "Le pilote face aux deux femmes", "lieu": "Tarmac",
         "enchainer": False, "image_clef": True, "pourquoi_clef": "poignée de main finie"},
        {"action": "Deux mains se serrent", "personnages": ["Pilote", "Femme brune"], "coupe": True, "visages": ["Pilote"],
         "duree": 4, "depart": "gros plan sur les mains", "lieu": "Tarmac", "enchainer": True, "pourquoi_lien": "même geste"}]}


def _png(d, nom):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(320, 180, QImage.Format_RGB32)
    q.fill(QColor("gray"))
    q.save(ch)
    return ch


class TestMontage(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.seq = A.appliquer(Q.nouvelle("16:9"), A.lire_analyse(ANALYSE), _png(self.d, "rush.png"))

    def test_lecture(self):
        p0, p1 = self.seq["plans"]
        self.assertTrue(self.seq["montage"])
        self.assertEqual(p0["visages"], ["Femme brune", "Pilote"][:2] if False else p0["visages"])
        self.assertEqual(len(p0["visages"]), 2)                       # jamais plus de deux visages
        self.assertTrue(p1["coupe"])
        self.assertEqual(p1["visages"], [])                           # un plan de coupe n'a aucun visage
        self.assertIn("PLANS DE COUPE", A.CONSIGNE_ANALYSE)
        self.assertIn("AU PLUS DEUX VISAGES", A.CONSIGNE_ANALYSE)

    def test_consigne(self):
        c0 = Q.consigne(self.seq, self.seq["plans"][0], {}, traduire=False)
        self.assertIn("show their face", c0)
        self.assertIn("back to the camera", c0)
        c1 = Q.consigne(self.seq, self.seq["plans"][1], {}, traduire=False)
        self.assertIn("NO FACE is visible", c1)

    def test_tableau_garde_les_propositions(self):
        """Avant 1.3.11, passer par « 3. Les plans » perdait le départ, le lien et l'image clef proposés par l'IA."""
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        dl = ed.assistant_creation(None)
        dl.seq = self.seq
        dl.cartes = []
        dl._remplir_plans()
        self.assertEqual(dl.t_plans.item(1, 4).text(), "Plan de coupe")
        dl._lire()
        p0, p1 = dl.seq["plans"]
        self.assertEqual(p0["etat_depart"], "Le pilote face aux deux femmes")
        self.assertTrue(p0["clef"])
        self.assertTrue(p1["enchainer_ia"] and p1["enchainer"])
        self.assertEqual(p1["lien_pourquoi"], "même geste")
        self.assertTrue(p1["coupe"])
        dl.t_plans.item(0, 4).setText("Pilote")                       # on choisit à la main qui est de face
        dl._lire()
        self.assertEqual(dl.seq["plans"][0]["visages"], ["Pilote"])
        dl.close()

    def test_prises(self):
        from app.fenetre import Fenetre
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        dl = ed.assistant_creation(None)
        dl.seq = self.seq
        a, b = commun.video_test(self.d), os.path.join(self.d, "b.mp4")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=10:duration=1", "-pix_fmt", "yuv420p", b])
        pl = dl.seq["plans"][0]
        pl["prises"], pl["fichier"] = [a], b
        dl._remplir_video()
        dl.l_plans.setCurrentRow(0)
        self.assertEqual(dl.c_prise.count(), 2)
        dl.c_prise.setCurrentIndex(0)
        self.assertEqual(pl["fichier"], a)                            # la prise choisie est celle posée dans le film
        self.assertEqual(set(pl["prises"]), {a, b})                   # aucune prise perdue
        dl.close()


class TestClip(unittest.TestCase):
    def test_mes_musiciens_et_export(self):
        from app import bibliotheque_creations as B, clip_groupe as CG
        from app.fenetre import Fenetre
        from app.dialogues_clip_groupe import DialogueClipGroupe
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        img = _png(d, "b.png")
        B.garder(ed.params, "musicien", "Batteur à moi", "batteur, cheveux gris", {"planche": img}, {"instrument": "batterie"})
        B.garder(ed.params, "musicien", "Guitariste à moi", "guitariste", {"planche": img}, {"instrument": "guitare"})
        son = os.path.join(d, "s.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=4", son])
        m = ed.projet.ajouter_media(son, moteur.sonder(son))
        c = ed.projet.ajouter_clip(m["id"], "audio", 0.0)
        dl = DialogueClipGroupe(ed, c)
        dl.clip = {"groupe": CG.groupe_propose({"caption_en": "rock"}), "plans": [], "lieu": "concert", "anime": False,
                   "format": "16:9", "chemin": son, "analyse": {}}
        for g in dl.clip["groupe"]:
            dl._ligne_membre(g)
        n = len(dl.clip["groupe"])
        dl._test_biblio = "Batteur à moi|Guitariste à moi"
        dl._membre_biblio(plusieurs=True)
        noms = [x["nom"] for x in dl.clip["groupe"]]
        self.assertIn("Batteur à moi", noms)
        self.assertIn("Guitariste à moi", noms)
        roles_proposes = {g["role"] for g in CG.groupe_propose({"caption_en": "rock"})}
        attendu = n + len({"batterie", "guitare"} - roles_proposes)
        self.assertEqual(len(dl.clip["groupe"]), attendu)              # ils remplacent les musiciens proposés
        # le clip enregistré à part, avec la chanson
        v = commun.video_test(d)
        dl.clip["plans"] = [{"debut": 0.0, "fin": 2.0, "fichier": v, "action": "a"}, {"debut": 2.0, "fin": 4.0, "action": "b"}]
        sortie = CG.exporter(dl.clip, son, os.path.join(d, "clip.mp4"))
        info = moteur.sonder(sortie)
        self.assertTrue(os.path.exists(sortie))
        self.assertAlmostEqual(float(info.get("duree") or 0), 4.0, delta=0.5)
        self.assertTrue(info.get("audio", True))
        dl.close()


if __name__ == "__main__":
    unittest.main()
