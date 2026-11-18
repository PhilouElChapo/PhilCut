"""0.9.92 : lèvres calculées sur ce poste (LatentSync 1.5, carte NVIDIA de 8 Go). Le moteur (Python portable, publié en
parties de moins de 2 Go) est recollé à l'installation ; PhilCut lance son script et lit « PHILCUT <fraction> <texte> »."""
import os, shutil, sys, tempfile, time, unittest, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

FAUX = r'''
import shutil, sys, time
video, sortie, mode = sys.argv[1], sys.argv[2], sys.argv[3]
print("chargement de torch...", flush=True)
for k in range(4):
    print(f"PHILCUT {k / 4:.3f} Calcul des lèvres", flush=True)
if mode == "erreur":
    print("PHILCUT_ERREUR Mémoire de la carte graphique insuffisante", flush=True)
    sys.exit(4)
shutil.copy(video, sortie)
print("PHILCUT 1.000 Terminé", flush=True)
'''


class TestLevresLocales(unittest.TestCase):
    def test_moteur_dans_la_liste(self):
        from app import levres as LV
        noms = [k for k, _m in LV.moteurs("video")]
        self.assertIn("latentsync_local", noms)
        self.assertEqual(LV.prix("latentsync_local", 30), 0.0)
        self.assertLess(noms.index("latentsync"), noms.index("latentsync_local"))
        if sys.platform != "win32":
            self.assertIn("Windows", LV.local_manque())

    def test_lire_ligne(self):
        from app import levres as LV
        self.assertEqual(LV.lire_ligne("PHILCUT 0.250 Repérage du visage"), (0.25, "Repérage du visage"))
        self.assertEqual(LV.lire_ligne("PHILCUT_ERREUR Visage introuvable"), (None, "Visage introuvable"))
        self.assertIsNone(LV.lire_ligne("100%|████| 25/25"))

    def _faux(self, mode):
        d = tempfile.mkdtemp()
        script = os.path.join(d, "faux_levres.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(FAUX)
        return d, lambda son, video, brut: [sys.executable, script, video, brut, mode]

    def test_calcul(self):
        from app import levres as LV, moteur
        d, cmd = self._faux("ok")
        v = commun.video_test(d, "plan.mp4", 2)
        son = os.path.join(d, "voix.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=2", son])
        vu = []
        sortie = os.path.join(d, "sortie.mp4")
        LV.fabriquer_local({}, son, v, sortie, lambda f, t="": vu.append((round(f, 2), t)), commande=cmd)
        self.assertTrue(os.path.exists(sortie))
        info = moteur.sonder(sortie)
        self.assertAlmostEqual(float(info["duree"]), 2, delta=0.2)
        self.assertTrue(any(t == "Calcul des lèvres" for _f, t in vu))
        self.assertEqual(vu[-1][0], 1.0)

    def test_erreur_dite(self):
        from app import levres as LV, moteur
        d, cmd = self._faux("erreur")
        v = commun.video_test(d, "plan.mp4", 1)
        son = os.path.join(d, "voix.wav")
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=220:d=1", son])
        with self.assertRaises(RuntimeError) as e:
            LV.fabriquer_local({}, son, v, os.path.join(d, "s.mp4"), commande=cmd)
        self.assertIn("Mémoire de la carte", str(e.exception))

    def test_moteur_en_parties(self):
        from app import packs_ia as P
        d = tempfile.mkdtemp()
        racine = os.path.join(d, "moteur")
        exe = P.executable("levres")
        rel = os.path.relpath(exe, P.dossier_moteur("levres"))
        os.makedirs(os.path.join(racine, os.path.dirname(rel)), exist_ok=True)
        with open(os.path.join(racine, rel), "wb") as f:
            f.write(os.urandom(300_000))                 # incompressible : plusieurs parties
        with open(os.path.join(racine, "philcut_levres.py"), "w") as f:
            f.write("print('ok')\n")
        archive = os.path.join(d, "philcut-levres-test.zip")
        with zipfile.ZipFile(archive, "w") as z:
            for base, _dd, fs in os.walk(racine):
                for n in fs:
                    z.write(os.path.join(base, n), os.path.relpath(os.path.join(base, n), racine))
        octets = open(archive, "rb").read()
        parties = []
        for k in range(3):
            morceau = octets[k * len(octets) // 3:(k + 1) * len(octets) // 3]
            f = f"{archive}.{k + 1:03d}"
            open(f, "wb").write(morceau)
            parties.append({"fichier": os.path.basename(f), "url": "file://" + f, "taille": len(morceau),
                            "sha256": P.empreinte(f)})
        info = {"fichier": os.path.basename(archive), "taille": len(octets), "parties": parties}
        anc = P.moteur_info
        P.moteur_info = lambda g: info if g == "levres" else anc(g)
        vu = []
        try:
            P.installer_moteur("levres", vu.append)
        finally:
            P.moteur_info = anc
        self.assertTrue(os.path.exists(exe))
        self.assertTrue(os.path.exists(os.path.join(P.dossier_moteur("levres"), "philcut_levres.py")))
        self.assertTrue(P.moteur_installe("levres"))
        self.assertGreater(len(vu), 0)
        self.assertLessEqual(max(vu), 1.0)
        shutil.rmtree(P.dossier_moteur("levres"), ignore_errors=True)


class TestFenetre(unittest.TestCase):
    def test_gratuit_sur_ce_poste(self):
        from app.fenetre import Fenetre
        from app import levres as LV
        import test_0965 as T
        f = Fenetre([])
        f.bienvenue = lambda *a, **k: None
        ed = f._editeur_ou_nouveau()
        c = T._projet(ed)
        d = ed.faire_parler(c)
        d.moteur.setCurrentIndex(d.moteur.findData("latentsync_local"))
        d.accord.setChecked(True)
        if sys.platform != "win32":
            self.assertIn("Windows", d.cout.text())
            self.assertFalse(d.b_fabriquer.isEnabled())
        anc = LV.local_manque
        LV.local_manque = lambda: ""
        try:
            d._maj()
            self.assertIn("gratuit", d.cout.text())
            self.assertTrue(d.b_fabriquer.isEnabled())
        finally:
            LV.local_manque = anc
        ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
