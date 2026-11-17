"""0.9.81 : ma bibliothèque de créations (personnages, musiciens, objets, lieux, voix, styles, musiques, images), rangée sur
clic, réutilisée telle quelle par l'assistant ; lieux dans l'assistant vidéo."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=40):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


def png(d, nom, couleur="gray"):
    from PySide6.QtGui import QImage, QColor
    ch = os.path.join(d, nom)
    q = QImage(120, 80, QImage.Format_RGB32)
    q.fill(QColor(couleur))
    q.save(ch)
    return ch


class TestBibliotheque(unittest.TestCase):
    def test_garder_lister_retirer(self):
        from app import bibliotheque_creations as B
        d = tempfile.mkdtemp()
        params = {}
        a = B.garder(params, "personnage", "Zoé pilote", "cheveux courts", {"planche": png(d, "p.png"), "photo": png(d, "f.png")},
                     {"accord": True})
        b = B.garder(params, "voix", "Écho chanteuse", "voix chaude", None, {"role": "chanteuse", "voix_decrite": {"fr": "chaude", "en": "warm"}})
        B.garder(params, "lieu", "Abbaye", "cloître de pierre", [png(d, "l.png")])
        self.assertTrue(os.path.exists(a["fichiers"]["planche"]))
        self.assertNotEqual(os.path.dirname(a["fichiers"]["planche"]), d)            # copié dans la bibliothèque
        noms = [e["nom"] for e in B.lister(params)]
        self.assertEqual(noms[:3], sorted(noms[:3], key=B._alpha))                  # ordre alphabétique, accents ignorés
        self.assertIn("Écho chanteuse", [e["nom"] for e in B.lister(params, "voix")])
        self.assertIn("Chanteuse", B.resume(b))
        a2 = B.renommer(params, a, "Zoé, pilote d'essai")
        self.assertEqual(a2["id"], a["id"])
        self.assertTrue(a2["fichiers"]["planche"])
        self.assertTrue(B.retirer(params, a2))
        self.assertIsNone(B.lire(params, "personnage", a["id"]))
        self.assertTrue(os.path.isdir(os.path.join(B.dossier(params), "_corbeille", "personnage", a["id"])))   # rien n'est effacé

    def test_carte_aller_retour(self):
        from app import bibliotheque_creations as B, assistant_idee as I
        d = tempfile.mkdtemp()
        e = I.element("personne", "Chauffeur", "homme de 50 ans, casquette", "inventer", genre="personne")
        x = B.depuis_carte({}, e, "Chauffeur de limousine", png(d, "planche.png"))
        neuve = I.element("personne", "?", "", "bibliotheque", genre="personne")
        self.assertIn("bibliothèque", I.manque(neuve))
        B.vers_carte(x, neuve)
        self.assertEqual((neuve["nom"], I.manque(neuve)), ("Chauffeur de limousine", ""))
        self.assertTrue(os.path.exists(neuve["planche"]))
        v = I.element("voix", "Voix", "", "fichier", voix_decrite={"fr": "grave", "en": "deep voice"}, retouche="plus chaude",
                      role="chanteur")
        xv = B.depuis_carte({}, v, "Chanteur grave")
        etat = I.lire_musique({"duree": 20, "voix": {"chantee": True, "source": "bibliotheque"}}, 20)
        B.vers_carte(xv, etat["elements"][1])
        base = I.fiche_base(etat)
        self.assertEqual(base["voix_decrite"]["en"], "deep voice")                   # la voix gardée sert telle quelle

    def test_assistant_reprend_la_fiche(self):
        from app import assistant_creation as A, sequence_ia as Q, bibliotheque_creations as B
        d = tempfile.mkdtemp()
        x = B.garder({}, "personnage", "Chauffeur", "costume noir", {"planche": png(d, "pl.png")})
        img = png(d, "depart.png")
        analyse = {"personnages": [{"nom": "Chauffeur", "genre": "personne", "sur_image": False, "description": "costume noir",
                                    "source": "bibliotheque", "biblio": x["id"], "planche": x["fichiers"]["planche"], "images": []}],
                   "lieux": [{"nom": "Rue", "sur_image": True, "description": "rue éclairée"}],
                   "plans": [{"action": "Il ouvre la portière", "personnages": ["Chauffeur"], "duree": 5, "lieu": "Rue"}]}
        s = A.appliquer(Q.nouvelle(), analyse, img)
        self.assertEqual(s["personnages"][0]["planche"], x["fichiers"]["planche"])  # pas de nouvelle fiche à payer
        self.assertEqual(s["lieux"][0]["images"], [img])
        self.assertEqual(s["plans"][0]["lieu"], "Rue")
        e = A.estimer(s, "kling-o3-ref", {"clef_gemini": "x", "clef_fal": "a:b"})
        self.assertAlmostEqual(e["images"], 0.04 * 1, places=2)                     # seulement l'image d'arrivée
        r = A.lire_analyse({"personnages": [], "lieux": [{"nom": "Escalier", "description": "marbre"}],
                            "plans": [{"action": "Elle descend", "lieu": "Escalier"}, {"action": "Elle sort", "lieu": "Inconnu"}]})
        self.assertEqual([p["lieu"] for p in r["plans"]], ["Escalier", ""])


class TestFenetres(unittest.TestCase):
    def test_fenetre_bibliotheque(self):
        from app.fenetre import Fenetre
        from app import bibliotheque_creations as B
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        dl = ed.bibliotheque_creations()
        dl._test_oui = True
        avant = len(B.lister(ed.params))
        dl.nouveau("musicien")
        self.assertEqual(len(B.lister(ed.params)), avant + 1)
        dl.nom.setText("Bassiste aux cheveux gris")
        dl.extra["instrument"].setText("basse")
        dl.enregistrer()
        x = dl.courante
        self.assertEqual((x["nom"], x["donnees"]["instrument"]), ("Bassiste aux cheveux gris", "basse"))
        dl.cherche.setText("bassiste")
        self.assertEqual(dl.liste.count(), 1)
        dl.retirer()
        self.assertEqual(len(B.lister(ed.params)), avant)

    def test_garder_depuis_l_assistant(self):
        from app.fenetre import Fenetre
        from app import moteur, assistant_creation as A, bibliotheque_creations as B
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_claude="k")
        d = tempfile.mkdtemp()
        img = png(d, "photo.png")
        m = ed.projet.ajouter_media(img, moteur.sonder(img))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        rep = {"personnages": [{"nom": "Chauffeur", "genre": "personne", "sur_image": False, "description": "costume noir, casquette"}],
               "lieux": [{"nom": "Rue", "sur_image": True, "description": "rue de nuit"}],
               "plans": [{"action": "Il ouvre la portière", "personnages": ["Chauffeur"], "duree": 5, "lieu": "Rue"}]}
        anc = A.demander
        A.demander = lambda *a, **k: rep
        try:
            dl = ed.assistant_creation(c)
            dl._test_precision = ""
            dl.histoire.setPlainText("Un chauffeur ouvre la portière dans la rue")
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_QUI and not dl._en_calcul()))
            self.assertEqual([c_.e["type"] for c_ in dl.cartes], ["personne", "lieu"])      # le lieu a sa carte
            dl._test_precision = "Chauffeur de limousine"
            dl.garder_carte(dl.cartes[0])
            self.assertIn("Chauffeur de limousine", [e["nom"] for e in B.lister(ed.params, "personnage")])
            chauffeur = dl.cartes[0]
            chauffeur.radios["bibliotheque"].setChecked(True)
            x = next(e for e in B.lister(ed.params, "personnage") if e["nom"] == "Chauffeur de limousine")
            B.vers_carte(x, chauffeur.e)
            chauffeur.rafraichir()
            self.assertTrue(chauffeur.maj())
            dl.suivant()
            self.assertEqual(dl.pages.currentIndex(), D.P_PLANS, dl.etat.text())
            self.assertEqual(dl.seq["personnages"][0].get("biblio"), x["id"])
            self.assertEqual(dl.seq["lieux"][0]["nom"], "Rue")
        finally:
            A.demander = anc


if __name__ == "__main__":
    unittest.main()
