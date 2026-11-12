"""0.9.48 : bouton IA toujours visible, « Dites-le en clair » élargi (étalonnage de toute la séquence, rushes rangés,
marqueurs), plan montré avant d'agir ; marqueurs sur la règle."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


def _editeur(n=3):
    from app.fenetre import Fenetre
    f = Fenetre([])
    ed = f._editeur_ou_nouveau()
    d = os.environ["APPDATA"]
    for i in range(n):
        v = commun.video_test(d, f"plan{i}.mp4", duree=2)
        m = ed.projet.ajouter_media(v, {"duree": 2.0, "date": f"2026-0{3 - i}-01T10:00:00"})
        ed.projet.ajouter_clip(m["id"])
    ed.rafraichir()
    return f, ed


class TestRegles(unittest.TestCase):
    def test_phrases(self):
        from app import commande_ia as C
        self.assertEqual(C.regles("étalonnage auto sur toute la séquence"), [{"action": "etalonnage", "mode": "auto", "plans": "tous"}])
        r = C.regles("rends toute la vidéo un peu plus chaude")[0]
        self.assertEqual((r["mode"], r["plans"], r["temperature"]), ("reglages", "tous", 0.35))
        self.assertEqual(C.regles("mêmes couleurs partout comme le plan 2")[0]["reference"], 2)
        self.assertEqual(C.regles("range les rushes par date"), [{"action": "ranger_rushes", "par": "date"}])
        self.assertEqual(C.regles("un marqueur à chaque plan")[0]["t"], "plans")
        self.assertEqual(C.regles("marqueurs sur les temps forts de la musique")[0]["t"], "musique")
        self.assertEqual(C.regles("marqueur « discours » à 12 s")[0], {"action": "marqueur", "texte": "discours", "t": 12.0})
        for a in C.regles("étalonnage auto sur toute la séquence, range les rushes par nom, un marqueur à chaque plan"):
            self.assertTrue(C.decrire(a))


class TestActions(unittest.TestCase):
    def test_sequence_rushes_marqueurs(self):
        from app import commande_ia as C, etalonnage as ET
        f, ed = _editeur()
        p = ed.projet
        acts = C.regles("toute la séquence plus lumineuse") + C.regles("range les rushes par date") + C.regles("un marqueur à chaque plan")
        n = C.appliquer(acts, ed)
        self.assertEqual(n, 3)
        self.assertTrue(all(ET.reglages_de(c)["exposition"] > 0 for c in p.clips_piste("video")))
        self.assertEqual([m["nom"] for m in p.medias], ["plan2.mp4", "plan1.mp4", "plan0.mp4"])          # par date de prise de vue
        self.assertEqual([m["t"] for m in p.marqueurs], [0.0, 2.0, 4.0])
        p.annuler()                                                    # une seule étape d'annulation
        self.assertEqual(p.marqueurs, [])
        self.assertEqual(p.medias[0]["nom"], "plan0.mp4")
        p.modifie = False

    def test_etalonnage_auto_prepare(self):
        from app import commande_ia as C, etalonnage as ET
        f, ed = _editeur(2)
        acts = C.regles("étalonnage auto sur toute la séquence")
        self.assertEqual(len(C.a_preparer(acts)), 1)
        vu = []
        C.preparer(acts, ed.projet, progression=lambda fr, nom="": vu.append(fr))
        self.assertEqual(vu[-1], 1.0)
        self.assertEqual(len(acts[0]["_par_plan"]), 2)
        C.appliquer(acts, ed)
        self.assertTrue(all(any(e["id"] == "etalonnage" for e in c.get("effets") or []) or not ET.filtre(ET.reglages_de(c))
                            for c in ed.projet.clips_piste("video")))
        ed.projet.modifie = False


class TestInterface(unittest.TestCase):
    def test_bouton_ia_et_fenetre(self):
        from PySide6.QtWidgets import QToolButton, QPushButton
        from app.dialogues_commande import DialogueCommande
        f, ed = _editeur(1)
        ed.params["barre"] = ["importer", "couper"]                    # même sans le bouton Volet, le bouton IA reste
        ed.construire_barre()
        b = [x for x in ed.findChildren(QToolButton) if x.objectName() == "bouton_ia" and x.parent() is not None]
        self.assertTrue(b)
        d = DialogueCommande(ed)
        libs = [x.text() for x in d.rapides.findChildren(QPushButton)]
        self.assertIn("Un marqueur à chaque plan", libs)
        import unicodedata
        n = [unicodedata.normalize("NFD", x).encode("ascii", "ignore").decode().lower() for x in libs]
        self.assertEqual(n, sorted(n))
        [x for x in d.rapides.findChildren(QPushButton) if x.text() == "Un marqueur à chaque plan"][0].click()
        d.tache.wait(5000)
        app.processEvents()
        self.assertTrue(d.b_faire.isEnabled())                         # le plan est montré, rien n'est fait
        self.assertEqual(ed.projet.marqueurs, [])
        d.faire()
        self.assertEqual(len(ed.projet.marqueurs), 1)
        ed.params["barre"] = None
        ed.projet.modifie = False

    def test_marqueurs_timeline(self):
        f, ed = _editeur(2)
        tl = ed.timeline
        tl.aller_a(1.5)
        m = tl.poser_marqueur(texte="ici")
        self.assertEqual(m["t"], 1.5)
        tl.poser_marqueur(1.5)                                         # pas de doublon
        self.assertEqual(len(ed.projet.marqueurs), 1)
        from PySide6.QtCore import QPointF
        from app.timeline import MARGE_G, H_REGLE
        self.assertIs(tl.marqueur_a(QPointF(MARGE_G + 1.5 * tl.pps + 3, H_REGLE - 6)), m)
        self.assertIsNone(tl.marqueur_a(QPointF(MARGE_G + 1.5 * tl.pps + 3, H_REGLE + 10)))
        tl._retirer_marqueur(None)
        self.assertEqual(ed.projet.marqueurs, [])
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
