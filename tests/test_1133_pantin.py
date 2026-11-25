"""1.3.0 : personnage animé (pantin). Découpe d'un dessin en pose en T, mouvements, expressions, bouches, rendu."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import pantin as P


def dessiner_t(dossier):
    """Un bonhomme simple en pose en T (500 x 600), et ses points."""
    from PySide6.QtGui import QImage, QPainter, QColor, QPen
    from PySide6.QtCore import Qt, QPointF
    img = QImage(500, 600, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    pts = {"tete": (250, 40), "cou": (250, 150), "epaule_g": (205, 170), "coude_g": (130, 170), "poignet_g": (60, 170),
           "epaule_d": (295, 170), "coude_d": (370, 170), "poignet_d": (440, 170), "bassin": (250, 330),
           "hanche_g": (225, 340), "genou_g": (205, 450), "cheville_g": (190, 560), "hanche_d": (275, 340),
           "genou_d": (295, 450), "cheville_d": (310, 560)}
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#3366cc"))
    p.drawRoundedRect(200, 150, 100, 200, 20, 20)
    p.setBrush(QColor("#f2c9a0"))
    p.drawEllipse(QPointF(250, 95), 55, 55)
    for a, b, c in (("epaule_g", "coude_g", "#3366cc"), ("coude_g", "poignet_g", "#f2c9a0"), ("epaule_d", "coude_d", "#3366cc"),
                    ("coude_d", "poignet_d", "#f2c9a0"), ("hanche_g", "genou_g", "#333333"), ("genou_g", "cheville_g", "#333333"),
                    ("hanche_d", "genou_d", "#333333"), ("genou_d", "cheville_d", "#333333")):
        p.setPen(QPen(QColor(c), 34, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(*pts[a]), QPointF(*pts[b]))
    p.end()
    chemin = os.path.join(dossier, "t.png")
    img.save(chemin)
    for nom, coul in (("bouche_X.png", "#aa3333"), ("bouche_A.png", "#661111"), ("yeux_ouverts.png", "#000000"),
                      ("yeux_fermes.png", "#555555"), ("yeux_joie.png", "#222222")):
        i = QImage(60, 20, QImage.Format_ARGB32)
        i.fill(QColor(coul))
        i.save(os.path.join(dossier, nom))
    return chemin, pts


def pantin_essai():
    """Un pantin complet, rangé dans « Mes personnages » (chemin de son pantin.json)."""
    d = P.nouveau_dossier("Essai")
    _img, pts = dessiner_t(d)
    p = P.nouveau("Personnage d'essai", d, "t.png", pts)
    P.decouper(p)
    p["bouches"] = {"X": "bouche_X.png", "A": "bouche_A.png"}
    p["yeux"] = {"ouverts": "yeux_ouverts.png", "fermes": "yeux_fermes.png", "joie": "yeux_joie.png"}
    return P.enregistrer(p)


class TestPantin(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        img, pts = dessiner_t(self.d)
        self.p = P.nouveau("Essai", self.d, "t.png", pts)
        P.decouper(self.p)
        self.p["bouches"] = {"X": "bouche_X.png", "A": "bouche_A.png"}
        self.p["yeux"] = {"ouverts": "yeux_ouverts.png", "fermes": "yeux_fermes.png", "joie": "yeux_joie.png"}
        self.chemin = P.enregistrer(self.p)

    def test_decoupe(self):
        self.assertEqual(set(self.p["pieces"]), set(P.PIECES))
        for n, d in self.p["pieces"].items():
            self.assertTrue(os.path.exists(os.path.join(self.d, d["png"])), n)
        # l'avant-bras gauche contient la main : il descend jusqu'au poignet
        self.assertLessEqual(self.p["pieces"]["bras_bas_g"]["origine"][0], 50)
        self.assertEqual(self.p["pieces"]["bras_bas_g"]["parent"], "bras_haut_g")
        relu = P.charger(self.chemin)
        self.assertEqual(relu["dossier"], self.d)

    def test_mouvements(self):
        noms = [n for _k, n in P.liste_mouvements()]
        self.assertEqual(noms, sorted(noms, key=lambda x: x.lower()))
        self.assertIn("saluer", dict(P.liste_mouvements()))
        for k in P.MOUVEMENTS:
            for u in (0, 0.3, 0.77, 1):
                p = P.pose_mouvement(k, u)
                self.assertIn("bras_haut_g", p)

    def test_piste(self):
        piste = P.piste_vide()
        piste["actions"] = [{"mouvement": "saluer", "debut": 1.0, "duree": 2.0},
                            {"mouvement": "sauter", "debut": 3.0, "duree": 1.0}]
        self.assertAlmostEqual(P.pose_a(piste, 0.2)["bras_haut_d"], P.REPOS["bras_haut_d"])
        self.assertLess(P.pose_a(piste, 1.6)["bras_haut_d"], 0)          # bras levé pour saluer
        self.assertLess(P.pose_a(piste, 3.5)["y"], -0.1)                  # en l'air
        self.assertEqual(P.expression_a(piste, 1.5), "joie")
        piste["expressions"] = [{"t": 1.2, "expression": "triste"}]
        self.assertEqual(P.expression_a(piste, 1.5), "triste")
        piste["bouches"] = [(0.0, "X"), (0.5, "A"), (0.9, "X")]
        self.assertEqual(P.bouche_a(piste, 0.6), "A")
        self.assertTrue(any(P.yeux_fermes(piste, k / 30) for k in range(30 * 8)))

    def test_rhubarb(self):
        self.assertEqual(P.lire_rhubarb("0.00\tX\n0.25\tB\n0.40\tG\nbruit\n0.6\tH\n"),
                         [(0.0, "X"), (0.25, "B"), (0.4, "F"), (0.6, "C")])

    def test_rendu(self):
        sc = P.scene_vide(320, 180)
        piste = P.piste_vide()
        piste["actions"] = [{"mouvement": "saluer", "debut": 0.0, "duree": 1.0}]
        sc["personnages"] = [{"pantin": self.chemin, "piste": piste}]
        sc["duree"] = 1.0
        img = P.image_scene(sc, 0.5)
        self.assertFalse(img.isNull())
        # le personnage est dessiné : des pixels bleus (le corps) au milieu de l'image
        from PySide6.QtGui import QColor
        bleus = sum(1 for x in range(0, 320, 4) for y in range(0, 180, 4) if QColor(img.pixel(x, y)).blue() > 150
                    and QColor(img.pixel(x, y)).red() < 120)
        self.assertGreater(bleus, 5)
        sortie = os.path.join(self.d, "o.mp4")
        P.fabriquer(sc, sortie)
        self.assertGreater(os.path.getsize(sortie), 1000)
        sc["fond"] = {"type": "transparent"}
        self.assertTrue(P.fabriquer(sc, sortie).endswith(".mov"))
        # une voix posée à 0,4 s : le film a du son, et sa durée reste celle de la scène
        from app import moteur
        import subprocess
        voix = os.path.join(self.d, "v.wav")
        subprocess.run([moteur.ffmpeg(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:d=0.4", voix], check=True)
        piste["voix"] = {"son": voix, "debut": 0.4}
        sc["fond"] = {"type": "couleur", "couleur": "#ffffff"}
        P.fabriquer(sc, sortie)
        info = moteur.sonder(sortie)
        self.assertAlmostEqual(float(info.get("duree") or 0), 1.0, delta=0.15)
        self.assertEqual(P.sons_scene(sc), [(voix, 0.4)])


class TestPantinIA(unittest.TestCase):
    def test_planche_visage(self):
        from PySide6.QtGui import QImage, QPainter, QColor
        from PySide6.QtCore import Qt, QPointF
        from app import pantin_ia as I
        img = QImage(1400, 500, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setBrush(QColor("#000000"))
        for k in range(6):                       # une paire d'yeux = deux taches proches
            cx = 110 + k * 230
            p.drawEllipse(QPointF(cx - 22, 120), 14, 14)
            p.drawEllipse(QPointF(cx + 22, 120), 14, 14)
        p.setBrush(QColor("#aa2222"))
        for k in range(7):
            p.drawEllipse(QPointF(100 + k * 195, 370), 40, 18 + k * 2)
        p.end()
        d = tempfile.mkdtemp()
        c = os.path.join(d, "v.png")
        img.save(c)
        rangees = I.separer_planche(c, [6, 7])
        self.assertEqual([len(r) for r in rangees], [6, 7])
        self.assertGreater(rangees[0][0].width(), 70)            # les deux yeux ensemble
        self.assertLess(rangees[1][0].height(), rangees[1][6].height())     # ordre de gauche à droite gardé
        v = I.enregistrer_visage(d, rangees)
        self.assertEqual(set(v["bouches"]), set(P.BOUCHES))
        with self.assertRaises(ValueError):
            I.separer_planche(c, [6, 6])

    def test_points(self):
        from app import pantin_ia as I
        r = {k: [500, 500] for k in P.POINTS}
        r["epaule_g"], r["epaule_d"] = [700, 200], [300, 200]
        pts = I.lire_points(r, 2000, 1000)
        self.assertEqual(pts["epaule_g"], [600.0, 200.0])
        del r["cou"]
        with self.assertRaises(ValueError):
            I.lire_points(r, 2000, 1000)

    def test_consignes(self):
        from app import pantin_ia as I
        c = I.consigne_corps("a cheerful baker", "plat")
        self.assertIn("T-POSE", c)
        self.assertIn("NO mouth", c)
        self.assertIn("reference photo", I.consigne_corps("", "bd", depuis_photo=True))
        self.assertIn("7 mouths", I.consigne_visage("plat"))
        self.assertEqual([n for _k, n in I.liste_styles()], sorted([n for _k, n in I.liste_styles()], key=str.lower))
        self.assertAlmostEqual(I.prix(), 0.085)


class TestFenetre(unittest.TestCase):
    def setUp(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()

    def test_scene(self):
        from app.dialogues_pantin import DialoguePantin
        from app import en_cours as EC
        d = DialoguePantin(self.ed)
        d._test_oui = True
        self.assertFalse(d.a_garder())
        d.ajouter_personnage(pantin_essai())
        self.assertEqual(d.liste.count(), 1)
        self.assertEqual(d.liste.item(0).text(), "Personnage d'essai")
        d.aller(1.0)
        d.mouvement.setCurrentIndex(d.mouvement.findData("saluer"))
        d.ajouter_mouvement()
        a = d.scene["personnages"][0]["piste"]["actions"]
        self.assertEqual((a[0]["mouvement"], a[0]["debut"]), ("saluer", 1.0))
        self.assertEqual(d.table.rowCount(), 1)
        d.table.cellWidget(0, 2).setValue(3.0)
        self.assertEqual(a[0]["duree"], 3.0)
        d.expression.setCurrentIndex(d.expression.findData("surprise"))
        d.poser_expression()
        self.assertEqual(d.scene["personnages"][0]["piste"]["expressions"][0]["expression"], "surprise")
        d.s_x.setValue(30)
        d.noter_place()
        d.aller(3.0)
        d.s_x.setValue(70)
        d.noter_place()
        self.assertEqual(len(d.scene["personnages"][0]["piste"]["deplacements"]), 2)
        # gardée sur le disque à chaque changement, et dans « Reprendre une création en cours »
        self.assertTrue(os.path.exists(d.chemin_scene))
        self.assertEqual(P.charger_scene(d.chemin_scene)["personnages"][0]["piste"]["actions"][0]["duree"], 3.0)
        self.assertEqual(d._etat_en_cours()["chemin"], d.chemin_scene)
        self.assertIn("pantin", EC.GENRES)
        # squelette : un point déplacé, puis appliqué (redécoupe)
        d.b_squelette.setChecked(True)
        self.assertIsNotNone(d.apercu.squelette)
        d.apercu._pantin = d._pantin_edite
        d._pantin_edite["points"]["coude_g"] = [140, 172]
        d.appliquer_squelette()
        self.assertIsNone(d.apercu.squelette)
        self.assertEqual(P.charger(d.scene["personnages"][0]["pantin"])["points"]["coude_g"], [140, 172])
        # voix posée à l'instant ; la fabrication fait une vidéo et sa recette (pour la rouvrir)
        from app import moteur, creations
        import subprocess
        voix = os.path.join(tempfile.mkdtemp(), "v.wav")
        subprocess.run([moteur.ffmpeg(), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=300:d=1", voix], check=True)
        d.aller(0.5)
        self.assertTrue(d.poser_voix(voix))
        self.assertEqual(d.scene["personnages"][0]["piste"]["voix"]["debut"], 0.5)
        d.scene["taille"] = [320, 180]
        d.fabriquer()
        d.tache.wait(120000)
        app.processEvents()
        for _i in range(50):
            app.processEvents()
            if getattr(d, "resultat", None):
                break
            import time as _t
            _t.sleep(0.05)
        self.assertTrue(os.path.exists(d.resultat))
        self.assertEqual(creations.lire(d.resultat)["outil"], "pantin")
        # fermer range la fenêtre (le travail est gardé)
        d.show()
        d.close()
        self.assertFalse(d.isVisible())
        self.assertTrue(d.a_garder())
        d._jeter = True
        d.done(0)

    def test_creer_sans_ia(self):
        """La création passe par l'IA ; ici les dessins et les points sont remplacés par ceux d'un bonhomme dessiné."""
        from app.dialogues_pantin import DialoguePantin, DialogueCreer
        from app import pantin_ia as I
        d = DialoguePantin(self.ed)
        d._test_oui = True
        d._test_creer = {"nom": "Test IA", "style": "bd", "description": "x", "photo": None}

        def corps(params, dossier, desc, style, photo=None):
            dessiner_t(dossier)
            import shutil
            shutil.copy(os.path.join(dossier, "t.png"), os.path.join(dossier, "corps.png"))
            return "corps.png"
        sauve = (I.fabriquer_corps, I.fabriquer_visage, I.trouver_points)
        try:
            I.fabriquer_corps = corps
            I.fabriquer_visage = lambda params, dossier, style: {"yeux": {"ouverts": "yeux_ouverts.png"},
                                                                 "bouches": {"X": "bouche_X.png"}}
            I.trouver_points = lambda params, dossier, image: dessiner_t(dossier)[1]
            d.creer()
            d.tache.wait(60000)
            for _i in range(50):
                app.processEvents()
                if d.liste.count():
                    break
        finally:
            I.fabriquer_corps, I.fabriquer_visage, I.trouver_points = sauve
        self.assertEqual(d.liste.count(), 1, d.etat.text())
        self.assertEqual(d.params.get("pantin_style"), "bd")
        self.assertTrue(d.b_squelette.isChecked())          # le squelette est montré pour vérification
        c = DialogueCreer(d, d.params, photo=True)
        self.assertFalse(c.ok.isEnabled())                  # photo et accord obligatoires
        c.chemin_photo.setText("x.png")
        self.assertFalse(c.ok.isEnabled())
        c.accord.setChecked(True)
        self.assertTrue(c.ok.isEnabled())
        self.assertIn("Traduction", c.consigne.text())
        d._jeter = True
        d.done(0)


if __name__ == "__main__":
    unittest.main()
