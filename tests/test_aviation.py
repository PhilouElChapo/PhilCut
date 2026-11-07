"""0.4.0 : lot Aviation réglé par l'utilisateur — profil de vol -> instruments, trajet (carte animée, mini-carte),
manche à air, sous-titres radio ; les Goodies gardent leur déroulé dans les extraits (aperçu, préparation)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import aviation as A, export, goodies as GO, moteur, titres as T
from app.projet import Projet


class TestAviation(unittest.TestCase):
    def test_profil_coherent(self):
        c = A.profil(700, {"terrain_ft": 0, "croisiere_ft": 3000, "montee_s": 300, "roulage_s": 0, "descente_s": 300, "atterrissage_s": 0})
        g = {"genre": "altimetre", "valeurs": c["altimetre"], "debut": 0, "fin": 600}
        self.assertAlmostEqual(GO.valeur(g, 320), 3000, delta=15)
        self.assertAlmostEqual(GO.valeur(g, 0), 0, delta=1)
        vario = {"genre": "variometre", "valeurs": c["variometre"], "debut": 0, "fin": 600}
        self.assertAlmostEqual(GO.valeur(vario, 150), 3000 / 295 * 60, delta=2)     # 3000 ft en 300 s (rampes comprises)
        court = A.profil(20)                                                   # vidéo plus courte que les phases : resserrées
        self.assertLessEqual(max(t for t, _v in court["altimetre"]), 20)

    def test_trajet(self):
        et = [A.aerodrome("LFMD"), A.aerodrome("LFTZ")]
        self.assertAlmostEqual(A.distance_nm(*et), 32, delta=4)
        self.assertAlmostEqual(A.cap(*et), 225, delta=8)
        lat, lon, cp, i = A.position(et, 0.5)
        self.assertAlmostEqual(lat, (et[0]["lat"] + et[1]["lat"]) / 2, places=3)
        g = {"genre": "carte_trajet", "debut": 10, "fin": 20, "options": {"etapes": et, "lisse": False}}
        self.assertAlmostEqual(A.avancement(g, 15), 0.5, places=3)
        c = A.profil(100, None, et + [A.aerodrome("LFKC")])                   # le cap suit les tronçons
        self.assertAlmostEqual(c["compas"][1][1] % 360, 225, delta=8)

    def test_tableau_groupe(self):
        p = Projet()
        gs = A.poser_tableau(p, 0, 60, ["altimetre", "anemometre", "horizon"], {"croisiere_ft": 2000})
        self.assertEqual(len(p.goodies), 3)
        grp = gs[0]["options"]["groupe"]
        self.assertTrue(gs[2]["options"]["roulis_valeurs"])
        A.poser_tableau(p, 0, 60, ["altimetre", "compas"], {"croisiere_ft": 5000}, groupe=grp)       # régler à nouveau
        self.assertEqual(sorted(g["genre"] for g in p.goodies), ["altimetre", "compas"])
        alt = next(g for g in p.goodies if g["genre"] == "altimetre")
        self.assertAlmostEqual(max(v for _t, v in alt["valeurs"]), 5000, delta=1)

    def test_radio(self):
        self.assertGreaterEqual(A.score_radio("Cannes tour, Fox Golf Hotel India, verticale pour vent arrière piste 17"), 4)
        self.assertGreaterEqual(A.score_radio("F-GHIJ contactez Nice sur 118.700"), 3)
        self.assertLess(A.score_radio("regarde la mer c'est magnifique"), 2)
        a = T.ass([], 1920, 1080, radio=[(1, 3, "Cannes tour, F-GHIJ")])
        self.assertIn("Style: Radio", a)
        self.assertIn("RADIO › Cannes tour", a)

    def test_rendu_et_extrait(self):
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=6)
        p = Projet()
        m = p.ajouter_media(v, moteur.sonder(v))
        p.ajouter_clip(m["id"])
        et = [A.aerodrome("LFMD"), A.aerodrome("LFTZ"), A.aerodrome("LFKC")]
        p.ajouter_goodie("carte_trajet", 0, 6, taille=0.4, options={"etapes": et})
        p.ajouter_goodie("mini_carte", 0, 6, taille=0.2, options={"etapes": et})
        p.ajouter_goodie("manche_air", 0, 6, taille=0.2, options={"vent_kt": 12, "rafales_kt": 18})
        A.poser_tableau(p, 0, 6, ["altimetre"], {"roulage_s": 0, "montee_s": 3, "descente_s": 2, "atterrissage_s": 0, "croisiere_ft": 3000})
        p.d["sous_titres_radio"] = [(1.0, 4.0, "Cannes tour, F-GHIJ")]
        for g in p.goodies:
            img = GO.image(g, 3.0, 200)
            self.assertFalse(img.isNull())
        # extrait (aperçu à 3 s) : la carte et l'altimètre gardent le déroulé de la vidéo entière
        q = export.extrait(p, 2.5, 4.0)
        cq = next(g for g in q.goodies if g["genre"] == "carte_trajet")
        self.assertAlmostEqual(A.avancement(cq, 0.5), A.avancement(next(g for g in p.goodies if g["genre"] == "carte_trajet"), 3.0), places=3)
        aq = next(g for g in q.goodies if g["genre"] == "altimetre")
        a0 = next(g for g in p.goodies if g["genre"] == "altimetre")
        self.assertAlmostEqual(GO.valeur(aq, 0.5), GO.valeur(a0, 3.0), places=1)
        self.assertEqual(q.d["sous_titres_radio"][0][:2], (0.0, 1.5))
        export.image_rendue(p, 3.0, os.path.join(d, "av.png"), largeur=640)
        # supprimer une partie avant : les valeurs suivent
        p.partie(0.0, 1.0, garder=False)
        a1 = next(g for g in p.goodies if g["genre"] == "altimetre")
        self.assertAlmostEqual(GO.valeur(a1, 2.0), GO.valeur(a0, 3.0), places=0)


class TestFenetresAviation(unittest.TestCase):
    def test_fenetres(self):
        from app.dialogues_aviation import DialogueManche, DialogueRadio, DialogueTableau, DialogueTrajet
        et = [A.aerodrome("LFMD"), A.aerodrome("LFTZ")]
        d = DialogueTableau(None, 0, 120, None, None, et)
        self.assertTrue(d.suivre.isChecked())
        d.champs["croisiere_ft"].setValue(6000)
        self.assertEqual(d.reglages()["croisiere_ft"], 6000)
        t = DialogueTrajet(None, 0, 60, {"etapes": et})
        self.assertEqual(len(t.etapes()), 2)
        t.cherche_ad.setText("LFKC")                                   # 0.9.18 : recherche par code, nom ou ville
        self.assertGreaterEqual(t.resultats_ad.count(), 1)
        t._ajouter_ad()
        self.assertEqual(t.etapes()[-1]["code"], "LFKC")
        self.assertIn("NM", t.resume.text())
        self.assertEqual(len(t.carte.etapes), 3)                       # les étapes sont sur la carte
        from app import carte_osm as K
        x, y = K.vers_pixels(43.548, 6.954, 9)
        la, lo = K.vers_degres(x, y, 9)
        self.assertAlmostEqual(la, 43.548, places=4)
        self.assertAlmostEqual(lo, 6.954, places=4)
        from app import aerodromes as AD
        self.assertEqual(AD.chercher("cannes")[0][0], "LFMD")
        csv_ = ('"id","ident","type","name","latitude_deg","longitude_deg","elevation_ft","continent","iso_country","iso_region",'
                '"municipality","scheduled_service","icao_code","iata_code","gps_code","local_code"\n'
                '1,"LFMF","small_airport","Fayence-Tourrettes",43.6106,6.7028,750,"EU","FR","FR-U","Fayence","no","LFMF","","LFMF",""\n'
                '2,"FR-0001","closed","Ancien terrain",44,5,0,"EU","FR","FR-U","","no","","","",""\n')
        lus = AD.lire_csv(csv_)
        self.assertEqual(len(lus), 1)
        self.assertEqual(lus[0][:4], ["LFMF", "Fayence-Tourrettes", "Fayence", "FR"])
        m = DialogueManche(None, 0, 60, {"vent_kt": 8})
        self.assertEqual(m.options()["vent_kt"], 8)
        m.minut.stop()
        r = DialogueRadio(None, [(1, 2, "Cannes tour F-GHIJ", 4), (3, 4, "bonjour", 0)])
        self.assertEqual([x[2] for x in r.resultat()], ["Cannes tour F-GHIJ"])


if __name__ == "__main__":
    unittest.main()
