"""0.9.83 : la bibliothèque de créations dans la Séquence IA (personnages, objets, lieux), le clip de groupe (musiciens) et la
Fabrique musique (voix, style, morceau créé)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def png(d, nom):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(80, 60, QImage.Format_RGB32)
    q.fill(QColor("gray"))
    q.save(ch)
    return ch


class TestBibliothequePartout(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre()
        self.f.bienvenue = lambda *a, **k: None
        self.ed = self.f.nouveau_projet("16:9")
        self.d = tempfile.mkdtemp()

    def test_sequence(self):
        from app import bibliotheque_creations as B
        B.garder(self.ed.params, "personnage", "Pilote Zoé", "combinaison bleue", {"planche": png(self.d, "pl.png"), "photo": png(self.d, "ph.png")},
                 {"accord": True})
        B.garder(self.ed.params, "lieu", "Hangar", "hangar d'aviation", [png(self.d, "h.png")])
        self.ed.sequence_ia()
        dl = self.ed._sequence
        dl._test_biblio = "Pilote Zoé"
        dl._depuis_biblio("perso")
        p = dl.seq["personnages"][-1]
        self.assertEqual((p["nom"], bool(p.get("planche")), p.get("accord")), ("Pilote Zoé", True, True))
        self.assertEqual(len(p["images"]), 1)
        dl._test_biblio = "Hangar"
        dl._depuis_biblio("lieu")
        self.assertEqual(dl.seq["lieux"][-1]["nom"], "Hangar")
        dl.t_persos.setCurrentCell(len(dl.seq["personnages"]) - 1, 0)
        dl._test_precision = "Pilote Zoé bis"
        dl._garder_biblio("perso")
        self.assertIn("Pilote Zoé bis", [e["nom"] for e in B.lister(self.ed.params, "personnage")])

    def test_clip_groupe(self):
        from app import bibliotheque_creations as B, clip_groupe as CG, moteur
        from app.dialogues_clip_groupe import DialogueClipGroupe
        B.garder(self.ed.params, "musicien", "Bassiste gris", "cheveux gris, veste noire", {"planche": png(self.d, "b.png")},
                 {"instrument": "basse"})
        son = os.path.join(self.d, "s.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=4", son])
        m = self.ed.projet.ajouter_media(son, moteur.sonder(son))
        c = self.ed.projet.ajouter_clip(m["id"], "audio", 0.0)
        dl = DialogueClipGroupe(self.ed, c)
        dl.clip = {"groupe": CG.groupe_propose({"caption_en": "rock"}), "plans": [], "lieu": "concert", "anime": False, "format": "16:9",
                   "chemin": son, "analyse": {}}
        for g in dl.clip["groupe"]:
            dl._ligne_membre(g)
        n = len(dl.clip["groupe"])
        dl._test_biblio = "Bassiste gris"
        dl._membre_biblio()
        # 1.3.11 : il prend la place du bassiste proposé (même instrument) au lieu de s'ajouter
        m2 = next(m for m in dl.clip["groupe"] if m["nom"] == "Bassiste gris")
        attendu = n if any(g["role"] == "basse" for g in CG.groupe_propose({"caption_en": "rock"})) else n + 1
        self.assertEqual((len(dl.clip["groupe"]), m2["role"]), (attendu, "basse"))
        self.assertEqual(dl.table_groupe.rowCount(), attendu)
        self.assertTrue(os.path.exists(m2["image"]))            # son visage suit : il n'est pas redessiné

    def test_fabrique_musique(self):
        from app import bibliotheque_creations as B
        from app.dialogues_musique_ia import DialogueFabriqueMusique
        B.garder(self.ed.params, "voix", "Chanteuse chaude", "voix chaude", None, {"voix_decrite": {"fr": "chaude, médium", "en": "warm"}})
        B.garder(self.ed.params, "style_musical", "Rock mélodique", "rock mélodique", None,
                 {"inspiration": {"resume": "rock, 140 bpm", "caption_en": "melodic rock", "bpm": 140}})
        dl = DialogueFabriqueMusique(self.ed, self.ed.params)
        dl._test_biblio = "Chanteuse chaude"
        dl._voix_biblio()
        self.assertEqual(dl.voix_decrite["en"], "warm")
        dl._test_biblio = "Rock mélodique"
        dl._style_biblio()
        self.assertEqual(dl.inspiration["bpm"], 140)
        self.assertFalse(dl.partir.isEnabled())                 # un style gardé inspire, il ne se réorchestre pas
        f = dl.fiche()
        self.assertEqual(f["voix_decrite"]["en"], "warm")
        dl.resultat = png(self.d, "faux.mp3")
        dl._test_precision = ""
        dl._garder_biblio(f)
        self.assertTrue(B.lister(self.ed.params, "musique"))


if __name__ == "__main__":
    unittest.main()
