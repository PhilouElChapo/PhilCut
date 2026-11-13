"""0.9.52 : guides pas à pas (« Comment faire… ») : chaque chemin de menu cité existe vraiment, « Montrez-moi » ouvre
le bon menu, les étapes se cochent seules ; accord certifié pour les images d'un personnage (Séquence IA)."""
import os, sys, time, unittest, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


def _fenetre_avec_plan():
    from app.fenetre import Fenetre
    f = Fenetre([])
    ed = f._editeur_ou_nouveau()
    v = commun.video_test(os.environ["APPDATA"], "guide.mp4", duree=3)
    m = ed.projet.ajouter_media(v, {"duree": 3.0})
    ed.projet.ajouter_clip(m["id"])
    ed.rafraichir()
    f.show()
    app.processEvents()
    return f, ed


class TestGuides(unittest.TestCase):
    def test_ordre_et_recherche(self):
        from app import guides as G
        gs = G.guides()
        n = [unicodedata.normalize("NFD", g["titre"]).encode("ascii", "ignore").decode().lower() for g in gs]
        self.assertEqual(n, sorted(n))
        self.assertGreaterEqual(len(gs), 8)
        self.assertEqual(G.chercher("comment retirer la voix de la musique ?")[0]["id"], "voix_musique")
        self.assertEqual(G.chercher("suivre une personne")[0]["id"], "suivi")
        self.assertEqual(G.chercher("changer le fond")[0]["id"], "fond")
        for g in gs:
            self.assertIn(g["etat"], G.ETATS)
            self.assertTrue(g["etapes"])

    def test_chemins_de_menu_existent(self):
        """Chaque « Montrez-moi » qui ouvre un menu de la barre trouve toutes les lignes de son chemin."""
        from app import guides as G
        f, ed = _fenetre_avec_plan()
        mb = f.menuBar()
        for g in G.guides():
            for e in g["etapes"]:
                ch = (e.get("montrer") or {}).get("menu")
                if not ch:
                    continue
                a = G._trouver(mb.actions(), ch[0])
                self.assertIsNotNone(a, (g["id"], ch[0]))
                menu = a.menu()
                for seg in ch[1:]:
                    menu.aboutToShow.emit()                     # menus remplis à l'ouverture
                    a = G._trouver(menu.actions(), seg)
                    self.assertIsNotNone(a, (g["id"], seg, [x.text() for x in menu.actions()]))
                    menu = a.menu() or menu
        ed.projet.modifie = False

    def test_clic_droit_existe(self):
        """Chaque « Montrez-moi » du clic droit trouve sa ligne dans le menu du plan."""
        from app import guides as G
        f, ed = _fenetre_avec_plan()
        vus = []
        ed.timeline._exec_menu = lambda m, pos: vus.append(m)
        for g in G.guides():
            for e in g["etapes"]:
                ch = (e.get("montrer") or {}).get("clic_droit")
                if not ch:
                    continue
                if "corriger" in _norm(ch[-1]):
                    ed.projet.clips_piste("video")[0]["ajustement"] = "suivi"      # cette ligne n'existe qu'avec un suivi
                vus.clear()
                self.assertTrue(G.montrer_clic_droit(ed, ch))
                m = vus[-1]
                a = None
                for seg in ch:
                    a = G._trouver(m.actions(), seg)
                    self.assertIsNotNone(a, (g["id"], seg, [x.text() for x in m.actions()]))
                    m = a.menu() or m
        ed.projet.modifie = False

    def test_volet_et_etapes_faites(self):
        from app import guides as G
        f, ed = _fenetre_avec_plan()
        self.assertTrue(G.montrer_volet(ed, "effets", "Fond vert"))
        self.assertEqual(ed.catalogue.recherche.text(), "Fond vert")
        c = ed.projet.clips_piste("video")[0]
        self.assertFalse(G.est_fait("effet:chroma_key", ed))
        c.setdefault("effets", []).append({"id": "chroma_key", "params": {}})
        self.assertTrue(G.est_fait("effet:chroma_key", ed))
        c["ajustement"] = "suivi"
        self.assertTrue(G.est_fait("suivi", ed))
        ed.timeline.selectionner(c["id"])
        self.assertTrue(G.est_fait("plan_choisi", ed))
        ed.projet.modifie = False

    def test_fenetre_guides(self):
        from app.dialogues_guide import DialogueGuides
        f, ed = _fenetre_avec_plan()
        d = f.guides()
        self.assertIsInstance(d, DialogueGuides)
        self.assertFalse(d.isModal())
        d.cherche.setText("voix")
        app.processEvents()
        d.ouvrir("suivi")
        self.assertEqual(len(d.cases), 3)
        c = ed.projet.clips_piste("video")[0]
        ed.timeline.selectionner(c["id"])
        d._verifier()
        self.assertTrue(d.cases[0][0].isChecked())                     # cochée toute seule
        self.assertIs(f.guides("fond"), d)                             # une seule fenêtre de guides
        self.assertEqual(d.guide["id"], "fond")
        textes = [a.text() for m in [a.menu() for a in f.menuBar().actions() if a.menu()] for a in m.actions()]
        self.assertIn("Comment faire… (guides pas à pas)", textes)
        d.close()
        ed.projet.modifie = False

    def test_dites_le_ouvre_le_guide(self):
        from app.dialogues_commande import DialogueCommande
        f, ed = _fenetre_avec_plan()
        d = DialogueCommande(ed)
        d.phrase.setText("comment retirer la voix d'une musique ?")
        d.comprendre()
        self.assertEqual(f._guides.guide["id"], "voix_musique")
        f._guides.close()
        ed.projet.modifie = False


class TestAccordPersonnage(unittest.TestCase):
    def test_images_sans_accord_refusees(self):
        from app.fenetre import Fenetre
        from app.dialogues_sequence import DialogueSequence
        import app.widgets as W
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        d = DialogueSequence(ed, None)
        d.seq["personnages"] = [{"nom": "Alex", "description": "", "style": "", "images": []}]
        d._remplir_tables()
        d.t_persos.setCurrentCell(0, 0)
        anc = W.ouvrir_fichiers
        W.ouvrir_fichiers = lambda *a, **k: ["/tmp/x.png"]
        try:
            d._accord_personne = lambda nom: False
            d._images("perso")
            self.assertEqual(d.seq["personnages"][0]["images"], [])
            d._accord_personne = lambda nom: True
            d._images("perso")
            self.assertEqual(d.seq["personnages"][0]["images"], ["/tmp/x.png"])
            self.assertTrue(d.seq["personnages"][0]["accord"])
        finally:
            W.ouvrir_fichiers = anc
        ed.projet.modifie = False


def _norm(t):
    from app.guides import _norm as n
    return n(t)


if __name__ == "__main__":
    unittest.main()
