"""0.9.8 : fenêtre de mise à jour (voir test_095), fermeture qui dit quelles opérations tournent, fenêtre qui tient dans
l'écran après l'ouverture d'un projet, timeline qui peut rétrécir."""
import os, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test098(unittest.TestCase):
    def test_taches_decrites_et_hauteur(self):
        from app.config import Parametres
        pa = Parametres()
        pa["bienvenue_vue"] = True
        pa["maj_auto"] = False
        pa["synchro"] = False
        pa["synchro_secrets"] = False
        pa.enregistrer()
        from app.fenetre import Fenetre
        from app.taches import Tache
        f = Fenetre()
        f.resize(1280, 640)
        f.show()
        ed = f.nouveau_projet("16:9")
        for _i in range(10):
            app.processEvents()
        self.assertLess(f.minimumSizeHint().height(), 600)        # un portable en 1366 × 768 (ou 1920 × 1080 à 150 %) suffit
        t = Tache(lambda tache: (tache.avancer(0.42, "encodage des images"), time.sleep(0.3)), "Export")
        t.start()
        time.sleep(0.1)
        txt = Fenetre.description_taches([t])
        self.assertIn("Export : 42 %", txt)
        self.assertIn("encodage des images", txt)
        t.wait()
        # fermeture : une tâche coincée ne bloque pas la fenêtre plus que le délai donné (en tout, pas par tâche)
        bloque = Tache(lambda tache: time.sleep(5), "Coincée")
        bloque.start()
        f.taches.append(bloque)
        t0 = time.time()
        f.attendre_taches(400)
        self.assertLess(time.time() - t0, 1.5)
        Fenetre.arreter_sons()                                        # sans lecteur : ne plante pas
        bloque.wait()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
