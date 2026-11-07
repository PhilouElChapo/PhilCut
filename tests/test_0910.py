"""0.9.10 : la DLL qui manque à un moteur est trouvée (une seule solution proposée) ; Drive en direct, NAS, FTP : les
réglages partent vraiment vers le lieu de synchronisation et ceux d'un autre poste sont repris au démarrage."""
import json, os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


def attendre(t, delai=30):
    t0 = time.time()
    while t is not None and t.isRunning() and time.time() - t0 < delai:
        app.processEvents()
        time.sleep(0.05)
    for _i in range(10):
        app.processEvents()


class Test0910(unittest.TestCase):
    def test_famille_des_dll(self):
        from app import diagnostic_ia as D
        self.assertEqual(D.famille_dll("VCRUNTIME140_1.dll"), "vcredist")
        self.assertEqual(D.famille_dll("MSVCP140.dll"), "vcredist")
        self.assertEqual(D.famille_dll("nvcuda.dll"), "pilote_nvidia")
        self.assertEqual(D.famille_dll("cudart64_12.dll"), "moteur")
        d = D.diagnostiquer("code 3221225781", None, {"VCRUNTIME140_1.dll": ["ace-synth.exe"]})
        self.assertEqual([a for a, _l in d["actions"]], ["vcredist"])          # une seule solution, la bonne
        self.assertIn("VCRUNTIME140_1.dll", d["titre"])
        d = D.diagnostiquer("code 3221225781", None, {"cudart64_12.dll": ["ggml-cuda.dll"]})
        self.assertEqual(d["actions"][0][0], "reinstaller")
        self.assertNotIn("pilote_nvidia", [a for a, _l in d["actions"]])
        d = D.diagnostiquer("code 3221225781", None, {"nvcuda.dll": ["ggml-cuda.dll"]})
        self.assertEqual(d["actions"][0][0], "pilote_nvidia")
        d = D.diagnostiquer("code 3221225781", None, {})                       # cause inconnue : pas de pilote Nvidia
        self.assertNotIn("pilote_nvidia", [a for a, _l in d["actions"]])

    def test_imports_d_un_programme_windows(self):
        """Petit programme Windows fabriqué à la main : sa table des imports est lue."""
        from app import diagnostic_ia as D
        import struct
        d = tempfile.mkdtemp()
        b = bytearray(0x400)
        b[0:2] = b"MZ"
        struct.pack_into("<I", b, 0x3C, 0x40)
        b[0x40:0x44] = b"PE\0\0"
        struct.pack_into("<H", b, 0x46, 1)                  # 1 section
        struct.pack_into("<H", b, 0x54, 240)                # taille de l'en-tête optionnel (PE32+)
        opt = 0x58
        struct.pack_into("<H", b, opt, 0x20B)
        struct.pack_into("<II", b, opt + 112 + 8, 0x1000, 40)     # répertoire des imports
        sec = opt + 240
        struct.pack_into("<IIII", b, sec + 8, 0x200, 0x1000, 0x200, 0x200)
        struct.pack_into("<I", b, 0x200 + 12, 0x1080)      # descripteur : nom à l'adresse 0x1080
        b[0x280:0x280 + 20] = b"VCRUNTIME140_1.dll\0\0"
        exe = os.path.join(d, "moteur.exe")
        with open(exe, "wb") as f:
            f.write(bytes(b))
        self.assertEqual(D.imports_pe(exe), ["VCRUNTIME140_1.dll"])
        sys32 = tempfile.mkdtemp()
        self.assertEqual(D.dll_manquantes(d, chemins=[sys32]), {"VCRUNTIME140_1.dll": ["moteur.exe"]})
        open(os.path.join(sys32, "VCRUNTIME140_1.dll"), "w").close()
        self.assertEqual(D.dll_manquantes(d, chemins=[sys32]), {})

    def test_synchro_vers_le_lieu_choisi(self):
        from app.config import Parametres
        from app.fenetre import Fenetre
        distant = tempfile.mkdtemp()
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=True, synchro_secrets=False)
        pa["comptes"] = [{"id": "nas1", "type": "reseau", "nom": "NAS", "adresse": distant}]
        pa["drive_compte"] = "nas1"
        pa.enregistrer()
        # un autre poste a laissé ses réglages communs plus récents
        os.makedirs(os.path.join(distant, "PhilCut"), exist_ok=True)
        with open(os.path.join(distant, "PhilCut", "preferences.json"), "w", encoding="utf-8") as g:
            json.dump({"philcut": 1, "communs": {"chaine_nom": "Ma chaîne", "maj": "2099-01-01T00:00:00", "par": "Autre PC"}}, g)
        f = Fenetre()
        compte = f._compte_synchro()
        self.assertIsNotNone(compte)
        t = f._synchroniser(compte)
        attendre(t)
        self.assertEqual(f.params.get("chaine_nom"), "Ma chaîne")              # repris de l'autre poste
        self.assertIn("Autre PC", f.statusBar().currentMessage())
        # ce poste envoie : la session part vers le lieu de synchronisation
        f.ecrire_session()
        attendre(f._tache_synchro)
        self.assertTrue(os.path.exists(os.path.join(distant, "PhilCut", "preferences.json")))
        with open(os.path.join(distant, "PhilCut", "preferences.json"), encoding="utf-8") as g:
            self.assertIn(f.params.get("machine"), json.load(g).get("postes", {}))
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
