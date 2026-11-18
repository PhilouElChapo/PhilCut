"""0.9.88 : atelier de création dans la bibliothèque (personnages et lieux réels, inspirés de photos ou inventés, plusieurs
photos, planche de lieu), tenues (toutes faites et à soi, mises à n'importe quel personnage), image d'un rush prise à la ligne
rouge sur une carte, raison des images clefs."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(cond, s=30):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


def image(d, nom, couleur="#305080"):
    from PySide6.QtGui import QImage, QColor
    im = QImage(400, 300, QImage.Format_RGB32)
    im.fill(QColor(couleur))
    ch = os.path.join(d, nom)
    im.save(ch)
    return ch


PNG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "icones", "philcut.png"), "rb").read() \
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "icones", "philcut.png")) else b"\x89PNG"


class TestTenues(unittest.TestCase):
    def test_pretes_et_fiche(self):
        from app import tenues as T, sequence_ia as Q, ia
        fam = {x["famille"] for x in T.pretes()}
        self.assertEqual(fam, {"bureau", "soiree", "decontracte", "metiers"})
        noms = [x["nom"] for x in T.pretes()]
        self.assertEqual(noms, sorted(noms, key=lambda n: T._net(n)))
        t = T.pret("pilote_ligne")
        self.assertIn("pilot", t["en"])
        vus = {}
        anc = (ia.generer_image, ia.generer_image_refs)
        ia.generer_image = lambda prm, c: (vus.__setitem__("c", c), PNG)[1]
        ia.generer_image_refs = lambda prm, c, refs, delai=240: (vus.__setitem__("c", c), vus.__setitem__("r", refs), PNG)[-1]
        try:
            d = tempfile.mkdtemp()
            seq = Q.nouvelle()
            p = Q.personnage("Directrice", "femme de cinquante ans, cheveux gris courts")
            p.update(mode="invente", tenue={"id": t["id"], "en": t["en"]})
            Q.planche_personnage(seq, p, {})
            self.assertIn("OUTFIT", vus["c"])
            self.assertEqual(p["planche_tenue"], t["id"])
            p2 = Q.personnage("Secrétaire", "plus jeune, chignon")
            p2.update(mode="inspire", images=[image(d, "photo.png")])
            Q.planche_personnage(seq, p2, {})
            self.assertIn("LOOKS LIKE", vus["c"])
            p2["tenue"] = {"id": "pret:serveur", "en": "white shirt"}            # autre tenue : la fiche est à refaire
            seq["personnages"], seq["plans"] = [p2], [Q.plan("Elle arrive", [p2["nom"]])]
            self.assertEqual(Q.sans_planche(seq, [0]), [p2])
            li = {"nom": "Bureau", "description": "", "images": [image(d, "b1.png"), image(d, "b2.png")], "mode": "reel"}
            Q.planche_lieu(seq, li, {})
            self.assertTrue(os.path.exists(li["planche"]) and len(vus["r"]) == 2)
            self.assertIn("Character A", Q.fiche_personnage(dict(p, _rang=0), traduire=False))
            self.assertIn("wearing", Q.fiche_personnage(dict(p, _rang=0), traduire=False))
        finally:
            ia.generer_image, ia.generer_image_refs = anc


class TestBibliotheque(unittest.TestCase):
    def test_atelier(self):
        from app.fenetre import Fenetre
        from app import bibliotheque_creations as B, widgets
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        ed.params["sync_dossier"] = d
        dl = ed.bibliotheque_creations()
        dl._test_oui = True
        dl.nouveau("personnage")
        e = dl.courante
        anc = widgets.ouvrir_fichiers
        widgets.ouvrir_fichiers = lambda *a, **k: [image(d, "f1.png"), image(d, "f2.png")]
        try:
            dl.ajouter_photos()
        finally:
            widgets.ouvrir_fichiers = anc
        self.assertEqual(len(dl._photos(dl.courante)), 2)
        dl.extra["mode"].setCurrentIndex(dl.extra["mode"].findData("inspire"))
        dl.extra["accord"].setChecked(False)
        dl.enregistrer()
        self.assertIn("accord", dl.etat.text())                          # ressemblance gardée : accord obligatoire
        dl.extra["accord"].setChecked(True)
        dl.enregistrer()
        self.assertEqual((dl.courante.get("donnees") or {}).get("mode"), "inspire")
        role = dl._photos(dl.courante)[0][0]
        dl.retirer_photo(role)
        self.assertEqual(len(dl._photos(dl.courante)), 1)
        from app import moteur
        v = commun.video_test(d, "r.mp4", 2)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.projet.ajouter_clip(m["id"], "video", 0.0)
        ed.timeline.aller_a(1.0)
        dl._test_boite = [0.1, 0.1, 0.6, 0.9]
        dl.photo_ligne_rouge()                                            # une image prise dans un rush
        self.assertEqual(len(dl._photos(dl.courante)), 2)
        from app import tenues as T
        dl.ajouter_tenue_prete(T.pret("tailleur_sombre"))
        self.assertEqual(dl.courante["genre"], "tenue")
        self.assertTrue(any(x["source"] == "biblio" for x in T.toutes(ed.params)))
        x = B.lister(ed.params, ["personnage"])[0]
        dl.remplir(x["id"])
        k = dl.extra["tenue"].findData("biblio:" + B.lister(ed.params, ["tenue"])[0]["id"])
        self.assertGreater(k, 0)
        dl.extra["tenue"].setCurrentIndex(k)
        dl.enregistrer()
        self.assertEqual(dl.courante["donnees"]["tenue"]["nom"], "Tailleur sombre")
        dl.close()


class TestCarte(unittest.TestCase):
    def test_image_du_rush_et_tenue(self):
        from app.fenetre import Fenetre
        from app import moteur, assistant_creation as A
        from app import dialogues_assistant_creation as D
        f = Fenetre()
        f.bienvenue = lambda *a, **k: None
        ed = f.nouveau_projet("16:9")
        ed.params.update(clef_claude="k")
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", 2)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        c = ed.projet.ajouter_clip(m["id"], "video", 0.0)
        rep = {"personnages": [{"nom": "Elle", "genre": "personne", "sur_image": False, "description": "manteau"}],
               "plans": [{"action": "Elle attend", "personnages": ["Elle"], "duree": 5, "image_clef": True,
                          "pourquoi_clef": "elle attend devant la porte"}]}
        anc = A.demander
        A.demander = lambda *a, **k: rep
        try:
            dl = ed.assistant_creation(c)
            dl._test_oui = True
            dl.r_scene.setChecked(True)
            dl._genre_choisi = True
            dl.histoire.setPlainText("Une femme attend devant la porte")
            dl.suivant()
            self.assertTrue(attendre(lambda: dl.pages.currentIndex() == D.P_QUI and not dl._en_calcul()))
            carte = dl.cartes[0]
            carte.radios["photo"].setChecked(True)
            ed.timeline.aller_a(1.0)
            dl._test_boite = [0.2, 0.1, 0.8, 0.9]
            dl._photo_ligne_rouge(carte)
            self.assertTrue(os.path.exists(carte.e["photo"]))
            carte.e["tenue"] = {"id": "pret:robe_soiree", "nom": "Robe de soirée", "description": "robe", "en": "evening gown", "image": ""}
            dl.accord.setChecked(True)
            dl.suivant()
            p = dl.seq["personnages"][0]
            self.assertEqual(p["tenue"]["id"], "pret:robe_soiree")
            self.assertEqual(dl.seq["plans"][0]["clef_pourquoi"], "elle attend devant la porte")
        finally:
            A.demander = anc


if __name__ == "__main__":
    unittest.main()
