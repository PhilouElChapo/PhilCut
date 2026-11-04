"""Bibliothèque musicale libre : seules les licences compatibles avec une vidéo publiée sont gardées ; téléchargement
avec le crédit à côté ; crédits repris pour la description de la publication. Faux serveur local, rien d'Internet."""
import json, os, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun  # noqa: F401
from app import moteur, musiques as MU, projet


class FauxOpenverse(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        port = self.server.server_port
        if self.path.startswith("/audio/"):
            self.server.requete = self.path
            res = [{"id": "1", "title": "Envol", "creator": "Ana", "url": f"http://127.0.0.1:{port}/f/envol.mp3", "duration": 125000,
                    "license": "by", "license_version": "4.0", "attribution": "« Envol » par Ana, CC BY 4.0", "foreign_landing_url": "https://jamendo/1",
                    "source": "jamendo", "filetype": "mp3", "tags": [{"name": "cinematic"}]},
                   {"id": "2", "title": "Interdit", "creator": "Bob", "url": f"http://127.0.0.1:{port}/f/x.mp3", "license": "by-nc"}]
            b = json.dumps({"results": res}).encode()
        else:
            b = self.server.musique
        self.send_response(200)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class TestMusiques(unittest.TestCase):
    def test_chercher_telecharger_crediter(self):
        d = tempfile.mkdtemp()
        mp3 = commun.musique_test(d, "m.mp3", 3)
        srv = HTTPServer(("127.0.0.1", 0), FauxOpenverse)
        srv.musique = open(mp3, "rb").read()
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with mock.patch.object(MU, "API", f"http://127.0.0.1:{srv.server_port}/audio/"):
            res = MU.chercher("drone", "cinema", "medium")
        self.assertIn("license=cc0%2Cpdm%2Cby%2Cby-sa", srv.requete)
        self.assertIn("length=medium", srv.requete)
        self.assertEqual([r["titre"] for r in res], ["Envol"])            # la musique « NC » est écartée
        params = {"musiques_dossier": os.path.join(d, "mes musiques")}
        chemin = MU.telecharger(res[0], params)
        srv.shutdown()
        self.assertTrue(os.path.exists(chemin))
        self.assertEqual(moteur.sonder(chemin)["genre"], "audio")
        p = projet.Projet("C", "16:9")
        m = p.ajouter_media(chemin, moteur.sonder(chemin))
        p.ajouter_clip(m["id"], "audio", 0.0)
        cr = MU.credits_projet(p)
        self.assertEqual(len(cr), 1)
        self.assertIn("Envol", cr[0])
        self.assertIn("https://jamendo/1", cr[0])


if __name__ == "__main__":
    unittest.main()
