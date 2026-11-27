"""1.4.1 : volume du film (EBU R128) : mesure, cibles, indicateur de la barre du bas, export ramené à la cible ou tel quel."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import niveau_sonore as NS, moteur, export


def attendre(cond, s=120):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestVolume(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre()
        self.f.bienvenue = lambda *a, **k: None
        self.ed = self.f.nouveau_projet("16:9")
        self.p = self.ed.projet
        self.d = tempfile.mkdtemp()
        v = os.path.join(self.d, "v.mp4")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=25:duration=6", "-f", "lavfi", "-i",
                       "sine=f=440:d=6", "-filter:a", "volume=0.05", "-shortest", "-pix_fmt", "yuv420p", "-c:a", "aac", v])
        m = self.p.ajouter_media(v, moteur.sonder(v))
        self.p.ajouter_clip(m["id"], "video")

    def test_lecture_ebur128(self):
        txt = ("[Parsed_ebur128_0 @ 0x1] t: 0.1  TARGET:-23 LUFS    M: -30.0 S:-120.7     I: -30.0 LUFS       LRA:   0.0 LU  "
               "SPK: -10.0 dBFS FTPK: -10 dBFS TPK: -10 dBFS\n"
               "  Integrated loudness:\n    I:         -31.2 LUFS\n  Loudness range:\n    LRA:         2.3 LU\n"
               "  True peak:\n    Peak:        -9.8 dBFS\nSummary:\n\n  Integrated loudness:\n    I:         -31.2 LUFS\n"
               "    Threshold: -41.2 LUFS\n\n  Loudness range:\n    LRA:         2.3 LU\n\n  True peak:\n    Peak:        -9.8 dBFS\n")
        r = NS.lire_ebur128(txt)
        self.assertEqual((r["integre"], r["lra"], r["crete"]), (-31.2, 2.3, -9.8))
        self.assertEqual(r["court"][0], (0.1, -70.0))
        self.assertEqual(NS.verdict(r, -14)[0], "faible")
        self.assertEqual(NS.verdict({"integre": -14.3, "crete": -1.6, "lra": 3}, -14)[0], "ok")
        self.assertEqual(NS.verdict({"integre": -10, "crete": -0.1, "lra": 3}, -14)[0], "fort")

    def test_cibles(self):
        self.assertEqual(NS.cible(self.p, {}, "whatsapp")[1], -16.0)
        self.assertEqual(NS.cible(self.p, {"son_cible": "television"})[1], -23.0)
        self.p.d["son_cible"] = "podcast"
        self.assertEqual(NS.cible(self.p, {"son_cible": "television"})[:2], ("podcast", -16.0))
        libs = [str(l) for k, l in NS.choix_cibles()[1:]]
        self.assertEqual(libs, sorted(libs, key=str.lower))          # ordre alphabétique

    def test_mesure_projet_et_indicateur(self):
        self.p.d.pop("son_cible", None)
        t = self.f.mesurer_son(self.ed)
        self.assertTrue(attendre(lambda: bool(self.p.d.get("son_mesure"))))
        mes = NS.a_jour(self.p)
        self.assertIsNotNone(mes)
        self.assertLess(mes["integre"], -30)                         # sinus à 5 % : bien trop faible
        self.assertGreater(len(mes["court"]), 5)
        self.f.maj_son(self.ed, 3.0)
        self.assertIn("LUFS", self.f.b_son.text())
        self.ed.inspecteur.vide()
        self.p.clips_piste("video")[0]["volume"] = 0.5               # le son change : la mesure est à refaire
        self.assertIsNone(NS.a_jour(self.p))
        self.f.maj_son(self.ed)
        self.assertIn("mesurer", self.f.b_son.text())

    def test_export_cible_ou_tel_quel(self):
        sortie = os.path.join(self.d, "o.mp4")
        self.p.d["son_lufs"] = -16.0
        export.exporter(self.p, sortie, "youtube")
        i = NS.mesurer(sortie)["integre"]
        self.assertAlmostEqual(i, -16.0, delta=1.5)                  # ramené à la cible demandée
        self.p.d["son_tel_quel"] = True
        export.exporter(self.p, sortie, "youtube")
        self.assertLess(NS.mesurer(sortie)["integre"], -30)          # laissé tel quel

    def test_registre(self):
        from app import commande_ia as C
        C.appliquer([{"action": "cible_son", "cible": "television"}], self.ed)
        self.assertEqual(self.p.d["son_cible"], "television")
        self.p.annuler()
        self.assertNotIn("son_cible", self.p.d)


if __name__ == "__main__":
    unittest.main()
