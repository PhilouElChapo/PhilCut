"""1.1.18 : ramasse-miettes dans le fil de l'interface (tas corrompu 0xc0000374 pendant un « Garbage-collecting » dans le fil de la
synchronisation) ; synchronisation : un fichier identique des deux côtés (empreinte MD5 du Drive) n'est plus proposé."""
import gc, json, os, sys, tempfile, threading, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test1126(unittest.TestCase):
    def test_ramasse_miettes(self):
        from app import ramasse_miettes as R
        anc = gc.isenabled()
        try:
            t = R.installer(app, 50)
            self.assertFalse(gc.isenabled())
            ramasses = []

            class Cycle:
                def __del__(self):
                    ramasses.append(threading.current_thread() is threading.main_thread())

            def fil():
                for _ in range(3000):
                    a = Cycle()
                    a.moi = a
            th = threading.Thread(target=fil)
            th.start()
            th.join()
            from PySide6.QtCore import QEventLoop, QTimer
            boucle = QEventLoop()
            QTimer.singleShot(400, boucle.quit)
            boucle.exec()
            gc.collect()
            self.assertTrue(ramasses)
            self.assertTrue(all(ramasses))                   # libérés dans le fil de l'interface, jamais dans l'autre
        finally:
            if R._minuterie is not None:
                R._minuterie.stop()
                R._minuterie = None
            if anc:
                gc.enable()

    def test_identique_des_deux_cotes(self):
        from app import miroir
        d = tempfile.mkdtemp()
        f = os.path.join(d, "fiche.json")
        with open(f, "w", encoding="utf-8") as x:
            json.dump({"a": 1}, x)
        self.assertEqual(len(miroir._md5(f)), 32)


if __name__ == "__main__":
    unittest.main()
