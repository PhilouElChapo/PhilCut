"""Publication YouTube : envoi reprenable par morceaux contre un faux serveur (aucun envoi réel), reprise après une
erreur, légende des réseaux en publication assistée."""
import json, os, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun  # noqa: F401
from app import publication as P

RECU = {"octets": bytearray(), "meta": None, "erreurs": 1}


class FauxYouTube(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        RECU["meta"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(200)
        self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/session")
        self.end_headers()

    def do_PUT(self):
        n = int(self.headers.get("Content-Length") or 0)
        bloc = self.rfile.read(n)
        plage = self.headers["Content-Range"]
        if plage.startswith("bytes */"):                       # où en est-on ?
            self.send_response(308)
            if RECU["octets"]:
                self.send_header("Range", f"bytes=0-{len(RECU['octets']) - 1}")
            self.end_headers()
            return
        if RECU["erreurs"] and len(RECU["octets"]) > 0:       # une panne passagère au deuxième morceau
            RECU["erreurs"] -= 1
            self.send_response(503)
            self.end_headers()
            return
        debut, fin_total = plage[6:].split("-")
        fin, total = fin_total.split("/")
        RECU["octets"][int(debut):] = bloc
        if int(fin) + 1 >= int(total):
            b = json.dumps({"id": "abc123"}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b)
        else:
            self.send_response(308)
            self.send_header("Range", f"bytes=0-{fin}")
            self.end_headers()


class TestPublication(unittest.TestCase):
    def test_envoi_youtube_reprenable(self):
        srv = HTTPServer(("127.0.0.1", 0), FauxYouTube)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        d = tempfile.mkdtemp()
        chemin = os.path.join(d, "v.mp4")
        contenu = os.urandom(300_000)
        open(chemin, "wb").write(contenu)
        etapes = []
        with mock.patch.object(P, "URL_ENVOI", f"http://127.0.0.1:{srv.server_port}/upload"), \
                mock.patch.object(P, "_acces", return_value="jeton"), mock.patch.object(P.time, "sleep", lambda s: None):
            url = P.envoyer_youtube(chemin, "Survol de Cannes", "Vol du dimanche", ["aviation", "Cannes"], "unlisted",
                                    progression=etapes.append, morceau=100_000)
        srv.shutdown()
        self.assertEqual(url, "https://youtu.be/abc123")
        self.assertEqual(bytes(RECU["octets"]), contenu)
        self.assertEqual(RECU["meta"]["status"]["privacyStatus"], "unlisted")
        self.assertEqual(RECU["meta"]["snippet"]["tags"], ["aviation", "Cannes"])
        self.assertEqual(etapes[-1], 1.0)

    def test_legende(self):
        self.assertEqual(P.legende("Titre", "Desc", ["vol libre", "Cannes"]), "Titre\n\nDesc\n\n#vollibre #Cannes")

    def test_youtube_utilise_l_application_google(self):
        from app import oauth
        with mock.patch.dict(os.environ, {"PHILCUT_GOOGLE_ID": "id-google", "PHILCUT_GOOGLE_SECRET": "s"}):
            self.assertEqual(oauth.identifiants("youtube"), ("id-google", "s"))
        self.assertIn("youtube.upload", oauth.FOURNISSEURS["youtube"]["portee"])


if __name__ == "__main__":
    unittest.main()
