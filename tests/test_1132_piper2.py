"""1.2.3 : nouveau moteur de voix (piper1-gpl). Il n'a plus --sentence_silence : la pause entre les phrases est faite par
PhilCut (une phrase par ligne, --output_dir, recollage avec le silence demandé). Essai avec un faux moteur."""
import os, sys, tempfile, unittest, wave, stat
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import packs_ia as P

FAUX = r'''#!/usr/bin/env python3
import os, sys, time, wave
a = sys.argv[1:]
assert "--sentence_silence" not in a, "option disparue"
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "args.txt"), "w").write(" ".join(a))
def ecrire(chemin, n):
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(1000); w.writeframes(b"\x01\x00" * n)
lignes = [l for l in sys.stdin.read().splitlines() if l.strip()]
if "--output_dir" in a:
    d = a[a.index("--output_dir") + 1]
    for l in lignes:
        p = os.path.join(d, f"{time.time_ns()}.wav"); ecrire(p, 100 * len(l)); print(p)
else:
    p = a[a.index("--output_file") + 1]; ecrire(p, 100 * len(" ".join(lignes))); print(p)
'''


class TestPiper2(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.exe = os.path.join(self.d, "piper")
        open(self.exe, "w").write(FAUX)
        os.chmod(self.exe, os.stat(self.exe).st_mode | stat.S_IEXEC)
        open(os.path.join(self.d, "v.onnx"), "w").write("x")
        self.sauve = (P.modele_actif, P.installe, P.moteur_installe, P.etat, P.dossier_modele, P.executable, P.dossier_moteur)
        P.installe = lambda c: True
        P.moteur_installe = lambda g: True
        P.etat = lambda: {"v": {"roles": {"modele": "v.onnx"}}}
        P.dossier_modele = lambda c: self.d
        P.executable = lambda g: self.exe
        P.dossier_moteur = lambda g: self.d

    def tearDown(self):
        (P.modele_actif, P.installe, P.moteur_installe, P.etat, P.dossier_modele, P.executable, P.dossier_moteur) = self.sauve

    def duree(self, f):
        with wave.open(f) as w:
            return w.getnframes()

    @unittest.skipIf(sys.platform == "win32", "faux moteur en script")
    def test_pause_entre_phrases(self):
        out = os.path.join(self.d, "o.wav")
        P.synthese("Une phrase. Une autre !", out, "v", silence=0.5)
        # 11 + 11 caractères × 100 trames, plus 0,5 s à 1000 Hz
        self.assertEqual(self.duree(out), 1100 + 1100 + 500)
        self.assertFalse(os.path.exists(out + ".phrases"))
        self.assertIn("--output_dir", open(os.path.join(self.d, "args.txt")).read())

    @unittest.skipIf(sys.platform == "win32", "faux moteur en script")
    def test_sans_pause_un_seul_appel(self):
        out = os.path.join(self.d, "o.wav")
        P.synthese("Une phrase. Une autre !", out, "v", vitesse=1.25, expressivite=0.5)
        a = open(os.path.join(self.d, "args.txt")).read()
        self.assertIn("--output_file", a)
        self.assertIn("--length_scale 0.800", a)
        self.assertIn("--noise_w", a)

    def test_wav_flottant_remis_en_entiers(self):
        import struct
        x = struct.pack("<4f", 0.0, 0.5, -1.0, 2.0)
        fmt = struct.pack("<HHIIHH", 3, 1, 22050, 22050 * 4, 4, 32)
        f = os.path.join(self.d, "f.wav")
        with open(f, "wb") as o:
            o.write(b"RIFF" + struct.pack("<I", 36 + len(x)) + b"WAVE" + b"fmt " + struct.pack("<I", 16) + fmt
                    + b"data" + struct.pack("<I", 0x7FFFFFFF) + x)        # taille « en flux », comme le nouveau Piper
        P.en_pcm16(f)
        with wave.open(f) as w:
            self.assertEqual((w.getsampwidth(), w.getframerate(), w.getnframes()), (2, 22050, 4))
            self.assertEqual(struct.unpack("<4h", w.readframes(4)), (0, 16384, -32767, 32767))
        avant = open(f, "rb").read()
        P.en_pcm16(f)                       # déjà en entiers : rien ne change
        self.assertEqual(open(f, "rb").read(), avant)

    def test_decoupage(self):
        self.assertEqual(P.decouper_phrases("Bonjour. Ça va ?\nOui… Merci!"), ["Bonjour.", "Ça va ?", "Oui…", "Merci!"])
        self.assertEqual(P.decouper_phrases("  "), [])


if __name__ == "__main__":
    unittest.main()
