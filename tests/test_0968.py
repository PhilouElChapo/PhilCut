"""0.9.68 : les fenêtres de travail ne bloquent plus PhilCut (remarque de Philippe : Séquence IA qui fabrique, impossible
de réduire). Séquence IA non modale et unique, « Réduire » pendant un calcul, « Nouvelle histoire » refusée pendant un
calcul ; présentation, modèles, prolonger, tampons, logo, publication : non modales ; fermer pendant un calcul range la
fenêtre et la barre du bas (ou le Centre d'activité) suit le calcul."""
import os, sys, threading, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None


def attendre(cond, s=10):
    t0 = time.time()
    while time.time() - t0 < s and not cond():
        app.processEvents()
        time.sleep(0.02)


def tache_lente(ev):
    from app.taches import Tache
    return Tache(lambda t: (ev.wait(20), "fini")[1], "essai")


class TestNonBloquantes(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()

    def tearDown(self):
        self.ed.projet.modifie = False

    def test_sequence(self):
        from PySide6.QtWidgets import QMessageBox
        from app import activite
        d = self.ed.sequence_ia()
        self.assertTrue(d.isVisible())
        self.assertFalse(d.isModal())
        ev = threading.Event()
        t = tache_lente(ev)
        d.taches.append(t)
        t.start()
        attendre(lambda: d.b_reduire.isVisibleTo(d))
        self.assertTrue(d.b_reduire.isVisibleTo(d))                    # « Réduire » pendant le calcul
        vu = []
        anc = QMessageBox.information
        QMessageBox.information = lambda *a, **k: vu.append(a)
        try:
            d._nouvelle()
        finally:
            QMessageBox.information = anc
        self.assertTrue(vu)                                          # pas de nouvelle histoire pendant un calcul
        self.assertFalse(getattr(d, "nouvelle_demandee", False))
        d.b_reduire.click()
        self.assertFalse(d.isVisible())
        self.assertIs(self.ed.sequence_ia(), d)                      # le menu la rouvre
        self.assertTrue(d.isVisible())
        d.close()                                                    # fermer pendant le calcul : rangée
        self.assertFalse(d.isVisible())
        self.assertTrue(t.isRunning())
        self.assertTrue(any(l["tache"] is t for l in activite.centre().lignes))
        ev.set()
        attendre(lambda: not t.isRunning())
        attendre(lambda: not d.b_reduire.isVisibleTo(d), 2)
        self.assertFalse(d.b_reduire.isVisibleTo(d))

    def test_autres_fenetres(self):
        from app import activite
        for ouvrir in (lambda: self.ed.tampons(1), lambda: self.ed.modeles_montage(), lambda: self.f.atelier_logo(),
                       lambda: self.f.publier()):
            d = ouvrir()
            self.assertFalse(d.isModal(), type(d).__name__)
            self.assertTrue(d.isVisible(), type(d).__name__)
            self.assertIs(ouvrir(), d, type(d).__name__)              # une seule fenêtre
            ev = threading.Event()
            t = tache_lente(ev)
            if not hasattr(d, "taches"):
                d.taches = []
            d.taches.append(t)
            t.start()
            debut = time.time()
            d.close()
            self.assertLess(time.time() - debut, 2, type(d).__name__)  # ne fige plus PhilCut
            self.assertFalse(d.isVisible(), type(d).__name__)
            self.assertTrue(t.isRunning(), type(d).__name__)         # le calcul continue
            self.assertTrue(any(l["tache"] is t for l in activite.centre().lignes), type(d).__name__)
            ev.set()
            attendre(lambda: not t.isRunning())
            d.taches.remove(t)
            d.close()



class TestSansVoixEtCertificats(unittest.TestCase):
    def test_kling_sans_son_et_sequence_sans_voix(self):
        from app import generateurs_video as GV, sequence_ia as Q
        recu = {}
        anc = GV.attendre_fal
        GV.attendre_fal = lambda cle, point, corps, sortie, *a, **k: recu.update(corps)
        try:
            GV.generer_fal("k", GV.modele("kling-3-pro", {}), "a shot", "x.mp4", 5)
        finally:
            GV.attendre_fal = anc
        self.assertIs(recu["generate_audio"], False)                  # pas de voix inventée par le moteur
        s = Q.nouvelle()
        s["plans"] = Q.decouper_simple("Un avion décolle au lever du jour.")
        s["plans"][0]["repliques"] = [{"qui": "A", "texte": "On y va."}]
        s["voix"] = "aucune"
        self.assertIn("Nobody speaks", Q.consigne(s, s["plans"][0], traduire=False))
        s["voix"] = "local"
        self.assertIn("talk briefly", Q.consigne(s, s["plans"][0], traduire=False))
        # un seul réglage : la voix du moteur reçoit les répliques, le son est demandé et gardé, le prix suit
        s["personnages"] = [Q.personnage("Léa", "femme de 30 ans")]
        s["plans"][0]["repliques"] = [{"qui": "Léa", "texte": "On y va."}]
        s["voix"] = "moteur"
        c = Q.consigne(s, s["plans"][0], traduire=False)
        self.assertIn('Character A says: "On y va."', c)
        self.assertNotIn("Léa", c)
        m = GV.modele("kling-3-pro", {})
        self.assertGreater(GV.prix(m, 5, son=True), GV.prix(m, 5))
        recu.clear()
        GV.attendre_fal = lambda cle, point, corps, sortie, *a, **k: recu.update(corps)
        try:
            GV.generer_fal("k", m, "a shot", "x.mp4", 5, son=True)
        finally:
            GV.attendre_fal = anc
        self.assertIs(recu["generate_audio"], True)
        # au montage, le son du plan (voix inventée par Gemini) est coupé
        import tempfile
        from app.projet import Projet
        d = tempfile.mkdtemp()
        s["plans"][0]["fichier"] = commun.video_test(d, "p.mp4", duree=2)
        s["voix"] = "aucune"
        p = Projet()
        Q.monter(p, s, 0.0)
        self.assertTrue(p.clips_piste("video")[0]["muet"])
        s["voix"] = "moteur"
        p2 = Projet()
        Q.monter(p2, s, 0.0)
        self.assertFalse(p2.clips_piste("video")[0].get("muet"))           # la voix du moteur est gardée

    def test_certificats_par_windows(self):
        import ssl
        from app import reseau
        self.assertIn(reseau.activer(), ("windows", "python"))
        import philcut
        self.assertIn("reseau.activer()", open(philcut.__file__, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
