"""Générateurs vidéo par IA : catalogue (intégré, en ligne, ajouts de l'utilisateur), prix, et file d'attente fal.ai
simulée par un petit serveur local (aucun appel payant)."""
import json, os, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun  # noqa: F401
from app import generateurs_video as GV

ETAT = {"appels": 0, "corps": None}


class FauxFal(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, d, code=200):
        b = json.dumps(d).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        if self.headers.get("Authorization") != "Key bon:secret":
            return self._json({"detail": "Unauthorized"}, 401)
        ETAT["corps"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ETAT["chemin"] = self.path
        base = f"http://127.0.0.1:{self.server.server_port}{self.path}/requests/abc"
        self._json({"request_id": "abc", "status_url": base + "/status", "response_url": base})

    def do_GET(self):
        if self.path.endswith("/status"):
            ETAT["appels"] += 1
            return self._json({"status": "COMPLETED" if ETAT["appels"] >= 2 else "IN_PROGRESS"})
        if self.path.endswith("/requests/abc"):
            return self._json({"video": {"url": f"http://127.0.0.1:{self.server.server_port}/video.mp4"}})
        if self.path == "/video.mp4":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"\x00\x00\x00\x18ftypmp42video")
            return
        self._json({}, 404)


class TestGenerateurs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), FauxFal)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.ancien = GV.FAL_FILE
        GV.FAL_FILE = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        GV.FAL_FILE = cls.ancien
        cls.srv.shutdown()

    def test_catalogue_et_prix(self):
        params = {"clef_gemini": "g", "modeles_video_perso": [{"modele": "fal-ai/autre/v1/text-to-video", "prix_s": 0.05}]}
        ids = [m["id"] for m in GV.modeles(params, en_ligne=False)]
        self.assertIn("omni-720p", ids)
        self.assertIn("kling-3-pro", ids)
        self.assertIn("perso:fal-ai/autre/v1/text-to-video", ids)
        dispo = {m["fournisseur"] for m in GV.disponibles(dict(params, clef_fal=""))}
        self.assertEqual(dispo, {"google"})
        self.assertEqual(GV.prix(GV.modele("omni-360p"), 4), 0.35)          # Omni : jusqu'à 10 s comptées
        self.assertEqual(GV.prix(GV.modele("kling-3-pro"), 6), 1.4)         # Kling : 5 ou 10 s -> 10 s
        self.assertEqual(GV.duree_reelle(GV.modele("seedance-2"), 7), 7)

    def test_file_d_attente_fal(self):
        d = tempfile.mkdtemp()
        img = os.path.join(d, "depart.png")
        with open(img, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\nimage")
        sortie = os.path.join(d, "plan.mp4")
        params = {"clef_fal": "bon:secret"}
        etapes = []
        GV.time.sleep = lambda s: None                      # pas d'attente réelle pendant l'essai
        GV.generer(params, "kling-3-pro", "Un avion décolle", sortie, duree=6, format_="9:16", image=img, progression=etapes.append)
        self.assertTrue(open(sortie, "rb").read().startswith(b"\x00\x00\x00\x18ftyp"))
        self.assertIn("image-to-video", ETAT["chemin"])
        c = ETAT["corps"]
        self.assertEqual((c["duration"], c["aspect_ratio"]), ("10", "9:16"))
        self.assertTrue(c["image_url"].startswith("data:image/png;base64,"))
        self.assertEqual(etapes[-1], 1.0)
        with self.assertRaises(GV.ErreurGenerateur):
            GV.generer({"clef_fal": "mauvais"}, "kling-3-pro", "x", sortie)
        with self.assertRaises(GV.ErreurGenerateur):
            GV.generer({}, "kling-3-pro", "x", sortie)


if __name__ == "__main__":
    unittest.main()
