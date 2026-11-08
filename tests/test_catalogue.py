"""Catalogue en ligne (0.9.26) : ce que la veille mensuelle dépose dans catalogue/nouveautes.json doit être sûr et
utilisable. Ce test est passé AVANT chaque envoi de la veille : s'il échoue, rien n'est publié."""
import json, os, re, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lire(nom):
    with open(os.path.join(RACINE, "catalogue", nom), encoding="utf-8") as f:
        return json.load(f)


class TestCatalogue(unittest.TestCase):
    def test_nouveautes_valides(self):
        from app import effets as E, goodies_svg as GS, recettes as R, tampons_ia as TI, bruitages as B, titres
        d = lire("nouveautes.json")
        self.assertEqual(d.get("format"), 1)
        for gid, g in (d.get("goodies") or {}).items():
            self.assertRegex(gid, r"^[a-z0-9_]+$")
            svg = g["svg"]
            self.assertTrue(GS.valide(svg), gid)
            self.assertNotRegex(svg.lower(), r"<script|javascript:|href\s*=\s*[\"'](?!#)|<image|<foreignobject|@import|url\(\s*[\"']?http", gid)
            self.assertLess(len(svg), 20000, gid)
            self.assertIn(g.get("animation", "pop"), GS.ANIMATIONS, gid)
            self.assertIn("fr", g["nom"], gid)
            self.assertIn(g.get("pack"), d.get("packs_goodies") or {}, gid)
        for m in d.get("modeles_montage") or []:
            self.assertIn(m["type"], R.TYPES, m["id"])
            self.assertIn(m["format"], ("16:9", "9:16", "1:1"), m["id"])
            self.assertTrue(5 <= m["duree"] <= 600, m["id"])
            for t in (m.get("reglages") or {}).get("transitions") or []:
                self.assertIn(t, E.CATALOGUE, (m["id"], t))
            look = (m.get("reglages") or {}).get("look")
            if look:
                self.assertIn(look, E.CATALOGUE, m["id"])
            self.assertIn("fr", m["nom"])
        for nom, s in (d.get("styles") or {}).items():
            self.assertTrue(any(isinstance(s.get(k), str) and s[k] for k in ("voix", "musique", "image", "jeu")), nom)
            for k in ("voix", "musique", "image", "jeu"):
                if s.get(k):
                    self.assertNotIn(nom.split()[0].lower(), s[k].lower(), (nom, "le nom ne doit pas être dans la description"))
                    self.assertNotRegex(s[k].lower(), r"\b(face of|looks like|lookalike|clone|voice of)\b", nom)
        for m in d.get("tampons_ia") or []:
            self.assertIn(m.get("mouvement", "zoom"), TI.MOUVEMENTS, m["id"])
            self.assertIn(m.get("voix", "normale"), TI.STYLES_VOIX, m["id"])
            for b in m.get("bruitages") or []:
                self.assertIn(b, B.SONS, (m["id"], b))
            self.assertTrue(1.0 <= float(m.get("duree", 3)) <= 6.0, m["id"])

    def test_effets_valides(self):
        d = lire("effets.json")
        for k, e in (d.get("effets") or {}).items():
            self.assertTrue(e.get("ffmpeg"), k)
            self.assertNotRegex(e["ffmpeg"], r"movie=|amovie=|sendcmd|zmq|\bfile\b", k)

    def test_integration_et_fenetres(self):
        from app import nouveautes as NV, goodies as GO, modeles_montage as MM, styles_ia as S, tampons_ia as TI
        arrives = NV.integrer()
        self.assertTrue(arrives)
        gs = [a for a in arrives if a["cat"] == "goodies"]
        if gs:
            img = GO.image({"genre": gs[0]["id"], "debut": 0, "fin": 5, "x": 0.5, "y": 0.5, "taille": 0.3, "options": {}}, 1.0, 96)
            self.assertGreater(sum(1 for x in range(0, 96, 8) for y in range(0, 96, 8) if img.pixelColor(x, y).alpha() > 0), 5)
        params = {}
        self.assertEqual(NV.nombre_nouveaux(params), len(arrives))
        NV.marquer_vus(params, "goodies")
        self.assertEqual(NV.nombre_nouveaux(params), len(arrives) - len(gs))
        for a in arrives:
            if a["cat"] == "modeles_montage":
                self.assertIn(a["id"], MM.tous(params))
            if a["cat"] == "tampons_ia":
                self.assertIn(a["id"], TI.MODELES)
        if any(a["cat"] == "styles" and a["id"] == "top gun" for a in arrives):
            self.assertIn("fighter pilot", S.transposer("un pilote à la Top Gun", "video")["ajout"])
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False, nouveautes_vues=[])
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        from app.dialogues_nouveautes import DialogueNouveautes
        d = DialogueNouveautes(f, f.params)
        self.assertEqual(d.liste.count(), len(arrives))
        self.assertTrue(d.liste.item(0).text().startswith("✦"))
        d.reject()
        from app.dialogues_effets_plus import GalerieGoodies
        g = GalerieGoodies(f, f.params)
        textes = [g.liste.item(i).text() for i in range(g.liste.count())]
        self.assertTrue(any(t.startswith("✦") for t in textes))
        g.reject()
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
