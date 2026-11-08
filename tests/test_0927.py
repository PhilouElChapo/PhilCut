"""0.9.27 : présentation de photos animée (8 animations), modèles à photos, mise à jour des modèles par le catalogue."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur


def photos(d, n=4):
    out = []
    for i in range(n):
        c = os.path.join(d, f"p{i}.jpg")
        moteur.lancer(["-y", "-f", "lavfi", "-i", f"testsrc2=s=640x{400 + 40 * i}:d=1,hue=h={i * 70}", "-frames:v", "1", c])
        out.append(c)
    return out


def attendre(t, delai=180):
    t0 = time.time()
    while t is not None and t.isRunning() and time.time() - t0 < delai:
        app.processEvents()
        time.sleep(0.05)
    for _i in range(20):
        app.processEvents()


class Test0927(unittest.TestCase):
    def test_toutes_les_animations(self):
        from app import presentation as PR
        d = tempfile.mkdtemp()
        ph = photos(d)
        for st in PR.STYLES:
            T = PR.duree_totale(len(ph), st, 1.0)
            vus = set()
            for k in range(6):
                img = PR.apercu_image(ph, st, T * k / 6, (160, 90), "sombre", 1.0)
                vus.add(bytes(img.constBits())[:160 * 90 * 4:997])
            self.assertGreater(len(vus), 2, st)                         # l'image change : ça bouge
        sortie = os.path.join(d, "cartes.mp4")
        PR.fabriquer(ph, sortie, "cartes", 1.0, (320, 180), 15, "table")
        info = moteur.sonder(sortie)
        self.assertAlmostEqual(info["duree"], PR.duree_totale(4, "cartes", 1.0), delta=0.3)
        self.assertEqual((info["video"]["largeur"], info["video"]["hauteur"]), (320, 180))

    def test_fenetre_et_modele(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9", "Vacances")
        d = tempfile.mkdtemp()
        for c in photos(d, 3):
            ed.projet.ajouter_media(c, moteur.sonder(c))
        from app.dialogues_presentation import DialoguePresentation
        dl = DialoguePresentation(ed)
        self.assertEqual(len(dl.photos), 3)
        self.assertGreaterEqual(dl.styles.count(), 8)
        dl.styles.setCurrentRow(list(__import__("app.presentation", fromlist=["STYLES"]).STYLES).index("pile"))
        dl.duree.setValue(1.0)
        dl.fabriquer()
        attendre(dl.tache)
        self.assertTrue(dl.b_poser.isEnabled(), dl.etat.text())
        self.assertEqual(ed.projet.clips_piste("video"), [])                   # rien n'est posé avant d'avoir regardé
        dl.poser()
        self.assertEqual(len(ed.projet.clips_piste("video")), 1)
        # 0.9.29 : la dernière image du plan et des images choisies dans une vidéo du montage
        v = commun.video_test(d, "vol.mp4", duree=3)
        mv = ed.projet.ajouter_media(v, moteur.sonder(v))
        cv = ed.projet.ajouter_clip(mv["id"], "video", 0.0, 0.5, 3.0)
        ed.aller_a(1.0)
        dl2 = DialoguePresentation(ed)
        n0 = len(dl2.photos)
        dl2._derniere_image()
        self.assertEqual(len(dl2.photos), n0 + 1)
        self.assertEqual(dl2.bande.count(), n0 + 1)
        from app.images_plan import DialogueImagesPlan
        di = DialogueImagesPlan(dl2, ed.projet, cv, n=8)
        self.assertGreaterEqual(di.liste.count(), 6)
        di.nombre.setValue(3)
        di.repartir()
        di.valider()
        self.assertEqual(len(di.choisies), 3)
        dl2._ajouter(di.choisies)
        self.assertEqual(len(dl2.photos), n0 + 4)
        dl2.reject()
        # modèle à photos
        from app.dialogues_modeles import DialogueModeles
        dm = DialogueModeles(ed)
        k = [dm.liste.item(i).data(0x0100) for i in range(dm.liste.count())].index("photos_explosion")
        dm.liste.setCurrentRow(k)
        dm.duree.setValue(6)
        dm.monter()
        attendre(dm.tache)
        attendre(None)
        p = ed.projet
        self.assertEqual(p.d["recette"]["presentation"], "explosion")
        self.assertEqual(p.d["format"], "9:16")
        self.assertEqual(len(p.clips_piste("video")), 1)
        self.assertEqual(p.titres[0]["animation"], "cinetique")
        p.modifie = False
        f.hide()
        f.deleteLater()

    def test_modeles_mis_a_jour_par_le_catalogue(self):
        from app import modeles_montage as MM, nouveautes as NV, presentation as PR
        avant = list(MM.MODELES["vlog_30"]["reglages"]["transitions"])
        MM.mettre_a_jour({"vlog_30": {"reglages": {"transitions": ["t_balayage", avant[0]]}}, "inconnu": {"x": 1}})
        apres = MM.MODELES["vlog_30"]["reglages"]["transitions"]
        self.assertEqual(apres.count(avant[0]), 1)
        self.assertIn("t_balayage", apres)
        NV.integrer()
        self.assertIn("confettis", PR.VARIANTES)
        self.assertEqual(MM.MODELES["diaporama"].get("presentation"), "pile")


if __name__ == "__main__":
    unittest.main()
