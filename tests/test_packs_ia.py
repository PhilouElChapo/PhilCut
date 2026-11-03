"""IA locale portable : catalogue, téléchargement avec reprise et empreinte, moteurs lancés à la demande puis arrêtés,
désinstallation complète. Les moteurs sont ici de faux programmes (scripts Python) qui parlent comme les vrais ;
l'essai avec les vrais moteurs et de vrais modèles se fait dans la fabrication « Moteurs IA locaux »."""
import hashlib, io, json, os, shutil, sys, tarfile, tempfile, unittest

from commun import RACINE  # noqa: F401

FAUX_SERVEUR = r'''#!PYTHON
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
a = sys.argv
if "--list-devices" in a:
    print("Available devices:")
    print("  Vulkan0: Intel(R) UHD Graphics (128 MiB, 100 MiB free)")
    print("  Vulkan1: NVIDIA GeForce RTX 3070 Laptop GPU (8192 MiB, 7900 MiB free)")
    sys.exit(0)
if "--device" in a:
    assert a[a.index("--device") + 1] == "Vulkan1", a
port = int(a[a.index("--port") + 1])
assert "-m" in a and "--mmproj" in a and "-t" in a
class G(BaseHTTPRequestHandler):
    def log_message(self, *x): pass
    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404); self.end_headers(); self.wfile.write(b"{}")
    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        n = sum(1 for c in d["messages"][-1]["content"] if c["type"] == "image_url")
        rep = json.dumps({"images": n, "json": "response_format" in d}) if "response_format" in d else f"{n} image(s) vue(s)"
        b = json.dumps({"choices": [{"message": {"content": rep}}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
HTTPServer(("127.0.0.1", port), G).serve_forever()
'''
FAUX_WHISPER = r'''#!PYTHON
import json, sys
a = sys.argv
base = a[a.index("-of") + 1]
for p in (25, 50, 100):
    print(f"whisper_print_progress_callback: progress = {p}%", file=sys.stderr)
json.dump({"transcription": [{"offsets": {"from": 0, "to": 1500}, "text": " Bonjour PhilCut"},
                             {"offsets": {"from": 1500, "to": 2000}, "text": " [Music]"},
                             {"offsets": {"from": 2000, "to": 3200}, "text": " deuxieme phrase"}]}, open(base + ".json", "w"))
'''


def _sha(b):
    return hashlib.sha256(b).hexdigest()


class TestPacksIA(unittest.TestCase):
    def setUp(self):
        if sys.platform == "win32":
            self.skipTest("faux moteurs en scripts : essai sous Linux")
        self.tmp = tempfile.mkdtemp(prefix="philcut-ia-")
        src = os.path.join(self.tmp, "src")
        os.makedirs(src)
        archives = {}
        for genre, nom, code in (("vision", "llama-server", FAUX_SERVEUR), ("vision_gpu", "llama-server", FAUX_SERVEUR.replace(
                'assert "-m" in a', 'assert a[a.index("-ngl") + 1] == "99"; assert "-m" in a')), ("whisper", "whisper-cli", FAUX_WHISPER)):
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as t:
                data = code.replace("PYTHON", sys.executable).encode()
                ti = tarfile.TarInfo(f"{genre}/{nom}")
                ti.size = len(data)
                ti.mode = 0o644
                t.addfile(ti, io.BytesIO(data))
                lib = b"bibliotheque"
                ti = tarfile.TarInfo(f"{genre}/libggml.so.1")
                ti.size = len(lib)
                t.addfile(ti, io.BytesIO(lib))
                ti = tarfile.TarInfo(f"{genre}/libggml.so")
                ti.type = tarfile.SYMTYPE
                ti.linkname = "libggml.so.1"
                t.addfile(ti)
            fichier = f"philcut-{ {'vision': 'llama', 'vision_gpu': 'llama-vulkan', 'whisper': 'whisper'}[genre]}-linux-x64.tar.gz"
            with open(os.path.join(src, fichier), "wb") as f:
                f.write(buf.getvalue())
            archives[genre] = {"linux": {"fichier": fichier, "taille": len(buf.getvalue()), "sha256": _sha(buf.getvalue()), "url": "http://inutile/" + fichier},
                               "version": "essai"}

        def modele(cle, genre, fichiers):
            liste = []
            for nom, role, contenu in fichiers:
                p = os.path.join(src, nom)
                with open(p, "wb") as f:
                    f.write(contenu)
                liste.append({"nom": nom, "role": role, "url": "file://" + p, "taille": len(contenu), "sha256": _sha(contenu)})
            return {"genre": genre, "nom": cle, "fichiers": liste, "taille": sum(x["taille"] for x in liste), "essai": False}
        man = {"format": 1, "moteurs": archives, "modeles": {
            "vision_leger": modele("vision_leger", "vision", [("m.gguf", "modele", b"poids" * 100), ("p.gguf", "mmproj", b"proj" * 50)]),
            "whisper_leger": modele("whisper_leger", "whisper", [("ggml-base.bin", "modele", b"voix" * 80)])}}
        self.man = os.path.join(self.tmp, "moteurs-ia.json")
        json.dump(man, open(self.man, "w"))
        os.environ.update(PHILCUT_IA_MANIFESTE=self.man, PHILCUT_IA_ARCHIVES=src, PHILCUT_IA_DOSSIER=os.path.join(self.tmp, "ia"))
        from app import packs_ia
        packs_ia._manifeste = None
        packs_ia._carte = ""            # pas de carte graphique, sauf dans test_carte_graphique
        packs_ia._peripherique = None
        self.P = packs_ia

    def tearDown(self):
        for k in ("PHILCUT_IA_MANIFESTE", "PHILCUT_IA_ARCHIVES", "PHILCUT_IA_DOSSIER"):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_installer_utiliser_supprimer(self):
        P = self.P
        self.assertFalse(P.installe("vision_leger"))
        self.assertGreater(P.a_telecharger("vision_leger"), 700)          # modèle + moteur
        etapes = []
        P.installer("vision_leger", lambda f, t="": etapes.append(f))
        self.assertTrue(P.installe("vision_leger") and P.moteur_installe("vision"))
        self.assertEqual(etapes[-1], 1.0)
        self.assertTrue(os.access(P.executable("vision"), os.X_OK))
        self.assertTrue(os.path.islink(os.path.join(P.dossier_moteur("vision"), "libggml.so")))
        self.assertEqual(P.a_telecharger("vision_leger"), 0)
        self.assertEqual(P.modele_actif("vision"), "vision_leger")
        # serveur lancé à la demande, arrêté à la sortie
        with P.ServeurVision(params={"ia_poste_leger": True}) as s:
            self.assertEqual(s.generer("Décris", [b"\x89PNG....", b"\xff\xd8jpeg"]), "2 image(s) vue(s)")
            self.assertEqual(json.loads(s.generer("JSON", [], json_attendu=True)), {"images": 0, "json": True})
            proc = s.proc
        self.assertIsNotNone(proc.poll())
        # voix
        P.installer("whisper_leger")
        wav = os.path.join(self.tmp, "v.wav")
        open(wav, "wb").write(b"RIFF")
        prog = []
        segs = P.transcrire(wav, params={}, progression=prog.append)
        self.assertEqual(segs, [(0.0, 1.5, "Bonjour PhilCut"), (2.0, 3.2, "deuxieme phrase")])
        self.assertEqual(prog, [0.25, 0.5, 1.0])
        self.assertEqual(os.listdir(os.path.join(P.dossier(), "tmp")), [])
        # tout retirer : modèles, puis moteurs devenus inutiles
        P.supprimer("vision_leger")
        self.assertFalse(P.moteur_installe("vision"))
        self.assertTrue(P.moteur_installe("whisper"))
        P.supprimer("whisper_leger")
        self.assertEqual(P.etat(), {})
        self.assertFalse(os.path.exists(P.dossier_moteur("whisper")))

    def test_carte_graphique(self):
        """Carte dédiée : moteur Vulkan installé en plus et utilisé ; s'il échoue, le processeur prend le relais."""
        P = self.P
        P._carte = "NVIDIA GeForce RTX 3060"
        P.installer("vision_leger")
        self.assertTrue(P.moteur_installe("vision_gpu") and P.moteur_installe("vision"))
        with P.ServeurVision(params={}) as s:
            self.assertEqual(s.mode, "gpu")
            self.assertEqual(s.peripherique, ("Vulkan1", "NVIDIA GeForce RTX 3070 Laptop GPU (8192 MiB, 7900 MiB free)"))
            self.assertEqual(s.generer("x", [b"\x89PNG"]), "1 image(s) vue(s)")
        with P.ServeurVision(params={"ia_gpu": False}) as s:
            self.assertEqual(s.mode, "cpu")
        with open(P.executable("vision_gpu"), "w") as f:          # pilote absent ou carte en panne
            f.write("#!/bin/sh\nexit 3\n")
        with P.ServeurVision(params={}) as s:
            self.assertEqual(s.mode, "cpu")
            self.assertEqual(s.generer("x"), "0 image(s) vue(s)")
        P.supprimer("vision_leger")
        self.assertFalse(P.moteur_installe("vision_gpu"))
        self.assertEqual(P.etat(), {})

    def test_empreinte_et_reprise(self):
        P = self.P
        src = os.path.join(self.tmp, "gros.bin")
        contenu = os.urandom(3 << 20)
        open(src, "wb").write(contenu)
        cible = os.path.join(self.tmp, "dl", "gros.bin")
        with self.assertRaises(P.ErreurIA):
            P._telecharger("file://" + src, cible, len(contenu), "0" * 64)
        self.assertFalse(os.path.exists(cible))
        P._telecharger("file://" + src, cible, len(contenu), _sha(contenu))
        self.assertEqual(open(cible, "rb").read(), contenu)

    def test_archive_suspecte_refusee(self):
        P = self.P
        a = os.path.join(self.tmp, "mal.tar.gz")
        with tarfile.open(a, "w:gz") as t:
            d = b"x"
            ti = tarfile.TarInfo("../../evade.txt")
            ti.size = 1
            t.addfile(ti, io.BytesIO(d))
        with self.assertRaises(P.ErreurIA):
            P.extraire(a, os.path.join(self.tmp, "cible"))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "..", "evade.txt")))

    def test_poste_leger(self):
        P = self.P
        n = os.cpu_count() or 2
        self.assertEqual(P.coeurs({"ia_poste_leger": True}), max(1, n // 2))
        self.assertEqual(P.coeurs({"ia_poste_leger": False}), max(1, n - 1))
        self.assertIn("preexec_fn", P._options_processus())


if __name__ == "__main__":
    unittest.main()
