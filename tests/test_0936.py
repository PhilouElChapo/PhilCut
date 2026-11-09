"""0.9.36 : éléments animés (Lottie, PC et Android), galerie avec aperçu animé, recherche, favoris et récents ;
aller-retour d'un projet entre deux appareils quand un média manque (rien n'est perdu ni deviné)."""
import json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur

CATALOGUE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue", "elements.json")


def _parcourir(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from _parcourir(v)
    elif isinstance(x, list):
        for v in x:
            yield from _parcourir(v)


class TestCatalogueElements(unittest.TestCase):
    def test_fichier_sur_et_complet(self):
        """Que des données : pas d'image incorporée, de texte, d'expression ni de lien ; 5 langues ; couleurs valides."""
        d = json.load(open(CATALOGUE, encoding="utf-8"))
        self.assertGreaterEqual(len(d["elements"]), 40)
        for k, pk in d["packs"].items():
            self.assertEqual(set(pk["nom"]), {"fr", "en", "de", "es", "it"}, k)
        for eid, e in d["elements"].items():
            self.assertEqual(set(e["nom"]), {"fr", "en", "de", "es", "it"}, eid)
            self.assertIn(e["pack"], d["packs"], eid)
            self.assertIn(e["fin"], ("boucle", "tenir", "une_fois"), eid)
            self.assertTrue(e["couleurs"], eid)
            lt = e["lottie"]
            self.assertEqual(lt["assets"], [], eid)
            for n in _parcourir(lt):
                self.assertNotIn("x", {k for k in n if k == "x" and isinstance(n[k], str)}, eid)       # expressions
                self.assertNotIn(n.get("ty"), (2, 5), eid)                                             # image, texte
            texte = json.dumps(lt)
            for interdit in ("http", "data:", "<script", "javascript"):
                self.assertNotIn(interdit, texte, eid)

    def test_chaque_element_se_dessine(self):
        """Rendu au début, au milieu et à la fin : jamais vide (sauf l'entrée), couleurs remplaçables."""
        import numpy as np
        from app import elements as EL, goodies as GO
        EL.integrer(False)
        self.assertTrue(EL.disponible(), EL.raison())
        vides = []
        for eid, e in EL.ELEMENTS.items():
            g = {"genre": EL.genre(eid), "debut": 0, "fin": 30, "options": {}}
            d = EL.duree(eid)
            pleins = 0
            for u in (d * 0.5, d * 0.97):
                img = GO.image(g, u, 96)
                a = np.frombuffer(img.constBits(), np.uint8).reshape(96, 96, 4)[..., 3]
                pleins += int((a > 30).sum() > 60)
            if not pleins:
                vides.append(eid)
            self.assertIn(EL.genre(eid), GO.GENRES)
            self.assertIn(EL.genre(eid), GO.FLUIDES)
        self.assertEqual(vides, [])
        # couleur : le cœur rouge devient bleu
        g = {"genre": "lottie:coeur_bat", "debut": 0, "fin": 5, "options": {"couleurs": ["#1e90ff"]}}
        img = GO.image(g, 0.2, 120)
        c = img.pixelColor(60, 66)
        self.assertGreater(c.blue(), 200)
        self.assertLess(c.red(), 80)
        # fin : « une fois » disparaît, « tenir » reste
        g = {"genre": "lottie:coche", "debut": 0, "fin": 9, "options": {"fin": "une_fois"}}
        self.assertIsNone(EL.image(g, 5.0, 64))
        g["options"]["fin"] = "tenir"
        self.assertIsNotNone(EL.image(g, 5.0, 64))

    def test_export_avec_element(self):
        from app.projet import Projet
        from app import export, elements as EL
        EL.integrer(False)
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=2)
        p = Projet()
        p.ajouter_clip(p.ajouter_media(v, moteur.sonder(v))["id"])
        g = p.ajouter_goodie("lottie:soleil", 0.0, 1.5)
        g.update(x=0.5, y=0.5, taille=0.5)
        out, _j = export.exporter(p, os.path.join(d, "f.mp4"), "web")
        img = os.path.join(d, "i.png")
        import subprocess
        subprocess.run([moteur.ffmpeg(), "-y", "-v", "error", "-ss", "0.8", "-i", out, "-frames:v", "1", img], check=True)
        from PySide6.QtGui import QImage
        q = QImage(img)
        c = q.pixelColor(q.width() // 2, q.height() // 2)          # cœur du soleil : jaune
        self.assertGreater(c.red(), 180)
        self.assertGreater(c.green(), 150)
        self.assertLess(c.blue(), 120)

    def test_galerie(self):
        from app import nouveautes as NV
        from app.dialogues_effets_plus import GalerieGoodies
        NV.integrer(False)
        pa = {}
        d = GalerieGoodies(None, pa)
        d.recherche.setText("flèche")
        self.assertGreater(d.liste.count(), 2)
        d.recherche.setText("")
        d.famille.setCurrentIndex(d.famille.findData("el_meteo"))
        self.assertEqual(d.liste.count(), 6)
        d.liste.setCurrentRow(0)
        d._basculer_favori()
        self.assertEqual(pa["goodies_favoris"], ["lottie:soleil"])
        d.famille.setCurrentIndex(d.famille.findData("@favoris"))
        self.assertEqual(d.liste.count(), 1)
        d._animer()
        self.assertFalse(d.apercu.pixmap().isNull())
        d.done(0)


class TestEditeur(unittest.TestCase):
    def test_poser_et_regler_un_element(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app import elements as EL
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=6)
        f = Fenetre()
        f.resize(1400, 860)
        f.show()
        ed = f.nouveau_projet("16:9")
        from app import taches

        class T:
            arret = False

            @staticmethod
            def avancer(fr, t=""):
                pass
        r = taches.importer_media(T, v, f.params, avec_proxy=False)
        m = ed.projet.ajouter_media(v, r["fiche"])
        m.update(vignettes=r["vignettes"], onde=r["onde"])
        ed.ajouter_a_la_timeline(m["id"])
        ed.rafraichir()
        app.processEvents()
        from app.dialogues_effets_plus import GalerieGoodies
        GalerieGoodies.exec = lambda self: (self.famille.setCurrentIndex(self.famille.findData("el_reperes")), self.liste.setCurrentRow(0), 1)[-1]
        ed.nouveau_goodie()
        g = ed.projet.goodies[-1]
        self.assertTrue(EL.est_element(g))
        self.assertEqual(f.params["goodies_recents"][0], g["genre"])
        ed.inspecteur.montrer_goodie(g)
        app.processEvents()
        ed.inspecteur._changer(lambda: g["options"].__setitem__("couleurs", ["#2ecc40"]), reconstruire=False)
        self.assertEqual(EL.couleurs_de(g), ["#2ecc40"])
        if os.environ.get("PHILCUT_CAPTURE"):
            ed.timeline.aller_a(g["debut"] + 1.0)
            app.processEvents()
            f.grab().save(os.environ["PHILCUT_CAPTURE"])
        ed.projet.modifie = False
        f.close()


class TestAllerRetour(unittest.TestCase):
    def test_media_absent_sur_l_autre_poste(self):
        """Poste A → poste B (fichier absent : il reste gris, intact) → retour sur A : tout est comme au début.
        Puis B rattache un autre emplacement : A retrouve quand même le sien."""
        from app.projet import Projet
        from app import projet as P, liens
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=2)
        ancien = P.PARAMS
        try:
            P.PARAMS = {"machine": "poste-A"}
            p = Projet()
            p.ajouter_clip(p.ajouter_media(v, moteur.sonder(v))["id"], src_debut=0.5, src_fin=1.5)
            f = os.path.join(d, "p.philcut")
            p.enregistrer(f)
            # sur B, le fichier n'est pas là
            cache = v + ".ailleurs"
            os.rename(v, cache)
            P.PARAMS = {"machine": "tel-B"}
            q = Projet.ouvrir(f)
            r = q.retrouver_medias()
            self.assertEqual(len(r["manquants"]), 1)
            q.clips[0]["debut"] = 0.0                          # on monte autour, sans toucher au plan gris
            q.enregistrer(f)
            dd = json.load(open(f, encoding="utf-8"))
            self.assertEqual(dd["medias"][0]["chemin"], v)       # rien n'a été deviné ni effacé
            self.assertNotIn("tel-B", dd["medias"][0].get("emplacements", {}))
            self.assertEqual((dd["clips"][0]["src_debut"], dd["clips"][0]["src_fin"]), (0.5, 1.5))
            # retour sur A
            os.rename(cache, v)
            P.PARAMS = {"machine": "poste-A"}
            a = Projet.ouvrir(f)
            self.assertEqual(a.retrouver_medias()["manquants"], [])
            self.assertEqual(a.medias[0]["chemin"], v)
            # B rattache une copie à un autre endroit : chacun garde le sien
            autre = tempfile.mkdtemp()
            copie = os.path.join(autre, "a.mp4")
            shutil.copy(v, copie)
            os.rename(v, cache)
            P.PARAMS = {"machine": "tel-B"}
            b = Projet.ouvrir(f)
            b.retrouver_medias()
            ok, _m = liens.rattacher(b, b.medias[0], copie, P.PARAMS)
            self.assertTrue(ok)
            b.enregistrer(f)
            shutil.rmtree(autre)
            os.rename(cache, v)
            P.PARAMS = {"machine": "poste-A"}
            a = Projet.ouvrir(f)
            r = a.retrouver_medias()
            self.assertEqual(r["manquants"], [])
            self.assertEqual(a.medias[0]["chemin"], v)
        finally:
            P.PARAMS = ancien

    def test_plan_gris_double_clic(self):
        """Un plan dont le fichier manque : double-clic ou clic droit → « Où est ce fichier ? » sur ce média."""
        from app.timeline import ItemClip
        from app.projet import Projet
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "a.mp4", duree=1)
        p = Projet()
        c = p.ajouter_clip(p.ajouter_media(v, moteur.sonder(v))["id"])
        os.remove(v)
        recus = []

        class TL:
            pass
        tl = TL()
        tl.projet = p
        tl.demande_menu = type("S", (), {"emit": lambda *a: recus.append(a[1:])})()
        it = ItemClip.__new__(ItemClip)
        it.clip, it.tl, it.absent = c, tl, True
        it._zone = lambda pos: None
        ItemClip.mouseDoubleClickEvent(it, type("E", (), {"pos": lambda self: None})())
        self.assertEqual(recus, [(c["id"], "ou_media")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
