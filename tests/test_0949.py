"""0.9.49 : tri des rushes sur ce poste (doublons, flou, tremblé, son raté, silences), pastilles sur les médias,
proposé à l'import, par clic droit, par le bouton IA."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
from app import moteur

D = os.path.join(os.environ["APPDATA"], "tri")
os.makedirs(D, exist_ok=True)


def _f(nom, *args):
    p = os.path.join(D, nom)
    if not os.path.exists(p):
        moteur.lancer(["-y"] + list(args) + [p])
    return p


def fichiers():
    net = _f("net.mp4", "-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=6", "-f", "lavfi", "-i", "sine=f=440:d=6",
             "-af", "volume=0.3", "-shortest", "-pix_fmt", "yuv420p")
    flou = _f("flou.mp4", "-i", net, "-vf", "boxblur=6:2", "-c:a", "copy")
    tremble = _f("tremble.mp4", "-f", "lavfi", "-i", "testsrc2=s=800x500:r=25:d=6", "-an",
                 "-vf", "crop=640:360:'80+40*sin(n*1.7)+30*sin(n*0.9)':'70+35*sin(n*2.3)'", "-pix_fmt", "yuv420p")
    pano = _f("pano.mp4", "-f", "lavfi", "-i", "testsrc2=s=1200x360:r=25:d=6", "-an", "-vf", "crop=640:360:'n*2':0", "-pix_fmt", "yuv420p")
    sature = _f("sature.wav", "-f", "lavfi", "-i", "sine=f=440:d=6", "-af", "volume=30")
    vent = _f("vent.wav", "-f", "lavfi", "-i", "anoisesrc=c=brown:a=0.5:d=6", "-af", "lowpass=f=100")
    sil = _f("silences.wav", "-f", "lavfi", "-i", "sine=f=440:d=10", "-af", "volume=enable='between(t,1,8)':volume=0")
    copie = os.path.join(D, "copie.mp4")
    if not os.path.exists(copie):
        moteur.lancer(["-y", "-i", net, "-c:v", "libx264", "-crf", "30", "-c:a", "aac", copie])
    return dict(net=net, flou=flou, tremble=tremble, pano=pano, sature=sature, vent=vent, silences=sil, copie=copie)


class TestMesures(unittest.TestCase):
    def test_pastilles(self):
        from app.projet import Projet
        from app import tri_rushes as TR
        f = fichiers()
        p = Projet()
        ids = {k: p.ajouter_media(v, moteur.sonder(v))["id"] for k, v in f.items()}
        vus = []
        r = TR.trier(p, progression=lambda x, n="": vus.append(x))
        self.assertEqual(vus[-1], 1.0)
        attendu = {"net": set(), "flou": {"flou"}, "tremble": {"tremble"}, "pano": set(), "sature": {"son"}, "vent": {"son"},
                   "silences": {"silences"}, "copie": {"doublon"}}
        for k, ident in ids.items():
            self.assertEqual(set(r[ident]), attendu[k], k)
        self.assertIn("vent", r[ids["vent"]]["son"])
        self.assertIn("net.mp4", r[ids["copie"]]["doublon"])
        self.assertEqual(TR.a_trier(p), [])                      # déjà fait : rien à refaire
        m = p.media(ids["flou"])
        from app import analyse_locale as AL
        self.assertTrue(AL.correspond(m, "à revoir"))
        self.assertTrue(AL.correspond(m, "flou"))
        self.assertFalse(AL.correspond(p.media(ids["net"]), "à revoir"))
        from PySide6.QtGui import QPixmap, QColor
        pm = QPixmap(112, 63)
        pm.fill(QColor("#000000"))
        self.assertNotEqual(TR.dessiner(pm, m).toImage().pixelColor(10, 10).name(), "#000000")


class TestEditeur(unittest.TestCase):
    def test_import_propose_et_regles(self):
        from app.fenetre import Fenetre
        from app import commande_ia as C
        f = fichiers()
        fe = Fenetre([])
        ed = fe._editeur_ou_nouveau()
        ed.params["tri_import"] = "proposer"
        ed.importer([f["net"], f["flou"]])
        import time
        t0 = time.time()
        while time.time() - t0 < 60 and len(ed.projet.medias) < 2:
            app.processEvents()
            time.sleep(0.05)
        app.processEvents()
        self.assertIn("Trier les rushes", ed.encart.bouton.text())                  # proposé, pas fait
        self.assertFalse(any(m.get("tri") for m in ed.projet.medias))
        ed.encart.bouton.click()
        t = ed.taches[-1]
        t.wait(60000)
        app.processEvents()
        self.assertTrue(all(m.get("tri") for m in ed.projet.medias))
        self.assertIn("à revoir", ed.encart.lbl.text())
        self.assertEqual(C.regles("trie les rushes"), [{"action": "trier_rushes"}])
        self.assertEqual(C.regles("range les rushes par date")[0]["action"], "ranger_rushes")
        self.assertNotEqual(C.regles("effet flou sur tous les plans")[:1], [{"action": "trier_rushes"}])
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
