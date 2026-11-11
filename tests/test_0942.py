"""0.9.42 : pCloud (autorisation dans le navigateur, API) et kDrive (API Infomaniak) ; compte choisi pour les rushes."""
import io, json, os, sys, threading, unittest, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

from app import distant, coffre


class Rep(io.BytesIO):
    status, reason = 200, "OK"

    def __init__(self, data):
        super().__init__(json.dumps(data).encode() if not isinstance(data, bytes) else data)
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class FauxServeur:
    """Remplace urlopen : chaque requête est notée, la réponse vient de `repondre(methode, url, corps)`."""

    def __init__(self, repondre):
        self.repondre, self.requetes = repondre, []

    def __call__(self, req, timeout=None, context=None):
        corps = req.data
        if corps is not None and hasattr(corps, "read"):
            morceaux = []
            while True:
                b = corps.read(1 << 16)
                if not b:
                    break
                morceaux.append(b)
            corps = b"".join(morceaux)
        self.requetes.append((req.get_method(), req.full_url, corps, dict(req.header_items())))
        return Rep(self.repondre(req.get_method(), req.full_url, corps))


def q(url):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))


class TestPCloud(unittest.TestCase):
    def setUp(self):
        self.c = distant.nouveau_compte("pcloud")
        coffre.enregistrer(self.c["id"] + ".jeton", "JETON-PCLOUD")
        self.ancien = urllib.request.urlopen

    def tearDown(self):
        urllib.request.urlopen = self.ancien

    def test_region_liste_envoi(self):
        def rep(m, url, corps):
            u = urllib.parse.urlsplit(url)
            if u.hostname == "eapi.pcloud.com":
                return {"result": 2000, "error": "Log in failed."}         # compte américain
            meth = u.path.strip("/")
            if meth == "listfolder":
                return {"result": 0, "metadata": {"contents": [
                    {"name": "Medias", "isfolder": True}, {"name": "a.mp4", "isfolder": False, "size": 12, "modified": "Wed, 11 Nov 2026 10:00:00 +0000"}]}}
            if meth == "userinfo":
                return {"result": 0, "email": "moi@exemple.org", "quota": 100, "usedquota": 40}
            return {"result": 0}
        f = urllib.request.urlopen = FauxServeur(rep)
        e = distant.emplacement(self.c)
        el = e.lister("/PhilCut")
        self.assertEqual([x.nom for x in el], ["Medias", "a.mp4"])
        self.assertEqual(self.c["hote"], "api.pcloud.com")              # retenu pour la suite
        self.assertEqual(q(f.requetes[-1][1])["access_token"], "JETON-PCLOUD")
        self.assertIn("access_token=****", distant.masquer(f.requetes[-1][1]))
        self.assertIn("a.mp4", e.modifies("/PhilCut"))
        tmp = os.path.join(os.environ["APPDATA"], "rush.mp4")
        with open(tmp, "wb") as g:
            g.write(b"x" * 300000)
        vus = []
        e.envoyer(tmp, "/PhilCut/Medias/rush.mp4", progression=lambda a, b: vus.append((a, b)))
        m, url, corps, ent = f.requetes[-1]
        self.assertEqual((m, urllib.parse.urlsplit(url).path), ("PUT", "/uploadfile"))
        self.assertEqual(q(url)["filename"], "rush.mp4")
        self.assertEqual(q(url)["path"], "/PhilCut/Medias")
        self.assertEqual(len(corps), 300000)
        self.assertEqual(vus[-1], (300000, 300000))
        crees = [q(u)["path"] for _m, u, *_r in f.requetes if "createfolderifnotexists" in u]
        self.assertEqual(crees, ["/PhilCut", "/PhilCut/Medias"])
        self.assertEqual(e.qui(), "moi@exemple.org")

    def test_introuvable(self):
        urllib.request.urlopen = FauxServeur(lambda m, u, c: {"result": 2005, "error": "Directory does not exist."})
        self.c["hote"], self.c["hote_verifie"] = "eapi.pcloud.com", True
        self.assertEqual(distant.emplacement(self.c).modifies("/PhilCut"), {})


class TestKDrive(unittest.TestCase):
    def setUp(self):
        self.c = distant.nouveau_compte("kdrive")
        self.c["adresse"] = "https://ksuite.infomaniak.com/kdrive/app/drive/424242/files"
        self.ancien = urllib.request.urlopen

    def tearDown(self):
        urllib.request.urlopen = self.ancien

    def test_dossiers_et_envois(self):
        arbre = {1: [{"id": 5, "name": "Private", "type": "dir"}, {"id": 6, "name": "Common documents", "type": "dir"}], 5: []}
        sessions = []

        def rep(m, url, corps):
            p = urllib.parse.urlsplit(url).path
            self.assertIn("/drive/424242/", p)
            if m == "GET" and p.endswith("/files") and "/files/" in p:
                ident = int(p.split("/files/")[1].split("/")[0])
                return {"result": "success", "data": arbre.get(ident, []), "has_more": False}
            if p.endswith("/directory"):
                parent = int(p.split("/files/")[1].split("/")[0])
                nouveau = {"id": 100 + len(arbre), "name": json.loads(corps)["name"], "type": "dir"}
                arbre.setdefault(parent, []).append(nouveau)
                arbre[nouveau["id"]] = []
                return {"result": "success", "data": nouveau}
            if p.endswith("/upload/session/start"):
                sessions.append(json.loads(corps))
                return {"result": "success", "data": {"token": "T1", "upload_url": "https://envoi.exemple.org"}}
            if "/chunk" in p:
                return {"result": "success", "data": {}}
            if p.endswith("/finish"):
                return {"result": "success", "data": {"file": {"id": 900}}}
            if p.endswith("/upload"):
                return {"result": "success", "data": {"id": 901}}
            return {"result": "success", "data": {}}
        f = urllib.request.urlopen = FauxServeur(rep)
        e = distant.emplacement(self.c, "JETON-KDRIVE")
        tmp = os.path.join(os.environ["APPDATA"], "petit.mp4")
        with open(tmp, "wb") as g:
            g.write(b"y" * 1000)
        e.envoyer(tmp, "/PhilCut/Medias/petit.mp4")
        m, url, corps, ent = f.requetes[-1]
        self.assertTrue(url.split("?")[0].endswith("/3/drive/424242/upload"))
        self.assertEqual(q(url)["conflict"], "version")
        self.assertEqual(len(corps), 1000)
        self.assertEqual(ent.get("Authorization"), "Bearer JETON-KDRIVE")
        noms = [x["name"] for x in arbre[5]]
        self.assertEqual(noms, ["PhilCut"])                           # dans « Private », pas à la racine commune
        e.MORCEAU, e.PETIT = 400, 500                                  # gros fichier : envoi par morceaux
        with open(tmp, "wb") as g:
            g.write(b"z" * 1000)
        e.envoyer(tmp, "/PhilCut/Medias/gros.mp4")
        morceaux = [u for _m, u, *_r in f.requetes if "/chunk" in u]
        self.assertEqual(len(morceaux), 3)
        self.assertTrue(morceaux[0].startswith("https://envoi.exemple.org/3/drive/424242/upload/session/T1/chunk"))
        self.assertEqual(sessions[0]["total_chunks"], 3)
        self.assertEqual([x.nom for x in e.lister("/PhilCut")], ["Medias"])

    def test_sans_jeton(self):
        with self.assertRaises(distant.ErreurDistant):
            distant.emplacement(self.c, "").lister("/")


class TestAutorisationPCloud(unittest.TestCase):
    def test_jeton_par_le_fragment(self):
        from app import oauth
        os.environ["PHILCUT_PCLOUD_ID"] = "id-essai"
        os.environ.pop("PHILCUT_PCLOUD_SECRET", None)
        vu = {}

        def navigateur(url):
            vu["url"] = url
            p = q(url)

            def aller():
                retour = p["redirect_uri"]
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(retour, timeout=5) as r:
                    vu["relais"] = r.read().decode()             # la page qui renvoie le fragment
                frag = urllib.parse.urlencode({"access_token": "TOK", "state": p["state"], "hostname": "eapi.pcloud.com",
                                               "locationid": "2"})
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(retour + "?" + frag, timeout=5) as r:
                    vu["fin"] = r.read().decode()
            threading.Thread(target=aller, daemon=True).start()
            return True
        j = oauth.autoriser("pcloud", ouvrir=navigateur, delai=20)
        self.assertEqual(q(vu["url"])["response_type"], "token")
        self.assertIn("location.hash", vu["relais"])
        self.assertEqual((j["refresh_token"], j["hote"]), ("TOK", "eapi.pcloud.com"))


class TestRushes(unittest.TestCase):
    def test_compte_des_rushes(self):
        from app import drive_philcut as DP, miroir
        g = distant.nouveau_compte("gdrive")
        p = distant.nouveau_compte("pcloud")
        params = {"comptes": [g, p], "drive_compte": g["id"], "rushs_compte": ""}
        self.assertIsNone(DP.compte_rushs(params))
        self.assertEqual(DP.dossier_medias(params), os.path.join(miroir.dossier_miroir(g), "PhilCut", "Medias"))
        params["rushs_compte"] = p["id"]
        self.assertEqual(DP.compte_rushs(params)["id"], p["id"])
        dm = DP.dossier_medias(params)
        self.assertEqual(dm, os.path.join(miroir.dossier_miroir(p), "Rushes", "Medias"))
        self.assertEqual(miroir.racine_distante(DP.compte_rushs(params)), "/PhilCut")
        params["rushs_dossier"] = "Rushes PhilCut/"
        self.assertEqual(miroir.racine_distante(DP.compte_rushs(params)), "/Rushes PhilCut")
        os.makedirs(dm, exist_ok=True)
        with open(os.path.join(dm, "abc_720p.mp4"), "wb") as f:
            f.write(b"v" * 10)
        with open(os.path.join(DP.racine(params), "session.json"), "w") as f:
            f.write("{}")
        el = DP.analyser(params)
        rush = [e for e in el if e["rel"] == "Medias/abc_720p.mp4"][0]
        self.assertEqual(rush["lieu"], distant.libelle(p))
        self.assertTrue(any(e["rel"] == "session.json" and not e.get("lieu") for e in el))
        self.assertEqual(DP.lieu_de(params, rush["chemin"])[0]["id"], p["id"])
        params["drive_compte"] = p["id"]                                  # même compte : pas de lieu à part
        self.assertIsNone(DP.compte_rushs(params))

    def test_synchro_vers_le_dossier_designe(self):
        import tempfile
        from app import drive_philcut as DP, miroir
        g = distant.nouveau_compte("gdrive")
        r = distant.nouveau_compte("reseau")
        r["adresse"] = tempfile.mkdtemp()
        params = {"comptes": [g, r], "drive_compte": g["id"], "rushs_compte": r["id"], "rushs_dossier": "/Echange rushes"}
        dm = DP.dossier_medias(params)
        os.makedirs(dm, exist_ok=True)
        with open(os.path.join(dm, "r1_720p.mp4"), "wb") as f:
            f.write(b"w" * 50)
        recus, envoyes = miroir.synchroniser(params, DP.compte_rushs(params))
        self.assertEqual(envoyes, 1)
        self.assertTrue(os.path.exists(os.path.join(r["adresse"], "Echange rushes", "Medias", "r1_720p.mp4")))
        self.assertFalse(os.path.exists(os.path.join(r["adresse"], "PhilCut")))

    def test_preferences(self):
        from app.fenetre import Fenetre
        from app.preferences import DialoguePreferences
        f = Fenetre([])
        p = distant.nouveau_compte("pcloud")
        f.params["comptes"] = [p]
        d = DialoguePreferences(f, f.params)
        i = d.findChildren(type(d), "")  # noqa: F841
        cb = [w for w in d.findChildren(__import__("PySide6.QtWidgets", fromlist=["QComboBox"]).QComboBox)
              if w.findData(p["id"]) >= 0 and w.itemData(0) == ""][0]
        cb.setCurrentIndex(cb.findData(p["id"]))
        d.valider()
        self.assertEqual(f.params.get("rushs_compte"), p["id"])
        for ed in f.editeurs():
            ed.projet.modifie = False


if __name__ == "__main__":
    unittest.main()
