"""0.9.43 : menu Fabrique rangé (Vidéo, Musique, Logo, intro et vignette), plan vidéo par l'IA de ce poste, Séquence IA
(ce poste d'abord, Flow en dernier, « Nouvelle histoire »), Atelier IA par ordre alphabétique, pCloud par WebDAV."""
import os, sys, unittest, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None          # pas de fenêtre d'accueil modale pendant les tests


class TestMenus(unittest.TestCase):
    def test_fabrique_et_aide(self):
        from app.fenetre import Fenetre
        f = Fenetre([])
        mb = f.menuBar()
        fb = [a.menu() for a in mb.actions() if a.menu() and "brique" in a.text()][0]
        sous = [a.text() for a in fb.actions() if a.menu()]
        self.assertEqual(sous, ["Image", "Logo, intro et vignette", "Musique", "Vidéo"])          # 0.9.46 : ordre alphabétique
        ai = [a.menu() for a in mb.actions() if a.menu() and "Aide" in a.text()][0]
        self.assertFalse(any("Guide de test" in a.text() for a in ai.actions()))
        tous = [a.text() for m in [a.menu() for a in fb.actions() if a.menu()] for a in m.actions()]
        self.assertFalse(any("Nouvelle séquence" in t for t in tous))       # une seule entrée pour la Séquence IA
        for ed in f.editeurs():
            ed.projet.modifie = False


class TestSequence(unittest.TestCase):
    def test_ordre_moteurs(self):
        from app.fenetre import Fenetre
        from app.dialogues_sequence import DialogueSequence
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        d = DialogueSequence(ed, None)
        donnees = [d.moteur.itemData(i) for i in range(d.moteur.count())]
        self.assertEqual(donnees[0], "locale")
        self.assertEqual(donnees[-1], "flow")
        self.assertEqual(d.moteur.currentData(), "locale")
        ed.projet.modifie = False


class TestPlanLocal(unittest.TestCase):
    def test_plan_par_ce_poste(self):
        from app import creatif, packs_ia
        from app.fenetre import Fenetre
        from app.dialogues_video import DialogueFabrique
        ancien = (packs_ia.modele_actif, packs_ia.installe, creatif.video)
        packs_ia.modele_actif = lambda genre, params=None: "wan" if genre == "video" else None
        packs_ia.installe = lambda cle: True
        vu = {}

        def video(prompt, sortie, params=None, **k):
            vu.update(prompt=prompt, **k)
            open(sortie, "wb").close()
            return sortie
        creatif.video = video
        try:
            f = Fenetre([])
            ed = f._editeur_ou_nouveau()
            d = DialogueFabrique(f, ed.projet, f.params)
            self.assertTrue(d.voie_locale.isChecked())                 # ce poste d'abord quand il est prêt
            d.sujet.setPlainText("survol de collines")
            d.consigne.setPlainText("aerial view of hills")
            import app.dialogues_video as DV
            montre = []

            class Apercu:
                def __init__(self, ed_, chemin, titre=""):
                    montre.append(chemin)

                def exec(self):
                    return 0
            ancien_dlg = DV.DialogueClipRecu
            DV.DialogueClipRecu = Apercu
            f._plan_local(ed, d, "aerial view of hills")
            t = f.taches[-1]
            t.wait(10000)
            app.processEvents()
            self.assertEqual(vu["prompt"], "aerial view of hills")
            self.assertLessEqual(vu["secondes"], 5.0)
            self.assertEqual(len(montre), 1)                            # on le regarde avant de l'intégrer
            DV.DialogueClipRecu = ancien_dlg
        finally:
            packs_ia.modele_actif, packs_ia.installe, creatif.video = ancien
        ed.projet.modifie = False


class TestPCloudDAV(unittest.TestCase):
    def test_envoi_en_flux(self):
        from app import distant
        c = distant.nouveau_compte("pcloud_dav")
        self.assertEqual(c["adresse"], "https://ewebdav.pcloud.com")
        c["utilisateur"] = "moi@exemple.org"
        requetes = []

        class Rep:
            status, reason, headers = 201, "Created", {}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self, n=-1):
                return b""

            def close(self):
                pass

        def faux(req, timeout=None, context=None):
            corps = req.data
            n = 0
            if corps is not None and hasattr(corps, "read"):
                while True:
                    b = corps.read(1 << 16)
                    if not b:
                        break
                    n += len(b)
            requetes.append((req.get_method(), req.full_url, n, req.get_header("Content-length")))
            return Rep()
        ancien = urllib.request.urlopen
        urllib.request.urlopen = faux
        try:
            tmp = os.path.join(os.environ["APPDATA"], "rush.mp4")
            with open(tmp, "wb") as g:
                g.write(b"r" * 200000)
            distant.emplacement(c, "secret").envoyer(tmp, "/Rushes/Medias/rush.mp4")
        finally:
            urllib.request.urlopen = ancien
        put = [r for r in requetes if r[0] == "PUT"][0]
        self.assertEqual(put[1], "https://ewebdav.pcloud.com/Rushes/Medias/rush.mp4")
        self.assertEqual((put[2], put[3]), (200000, "200000"))
        self.assertIn(("MKCOL", "https://ewebdav.pcloud.com/Rushes/Medias/", 0, None), requetes)


class TestAtelier(unittest.TestCase):
    def test_ordre_alphabetique(self):
        import unicodedata
        from app.fenetre import Fenetre
        from app.dialogues_creatif import DialogueAtelierIA
        f = Fenetre([])
        ed = f._editeur_ou_nouveau()
        d = DialogueAtelierIA(ed, "video")
        noms = [d.liste.item(i).text().replace("  ⚠", "") for i in range(d.liste.count())]
        norm = [unicodedata.normalize("NFD", n).encode("ascii", "ignore").decode().lower() for n in noms if not n.startswith("★")]
        self.assertEqual(norm, sorted(norm))
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
