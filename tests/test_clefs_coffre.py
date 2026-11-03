"""Clefs IA (11.6) : rangées dans le coffre du système, jamais en clair dans parametres.json ; une clef laissée en
clair par la 0.1 est déplacée dans le coffre au démarrage."""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun  # noqa: F401  (dossier de données jetable)
from app import coffre
from app.config import Parametres

CLAUDE = "sk-ant-api03-essai-0123456789abcdefghijklmnop"
GEMINI = "AQ.Ab8RN6essai0123456789abcdefghijklmnop"


class TestClefsCoffre(unittest.TestCase):
    def tearDown(self):
        for k in ("clef_claude", "clef_gemini"):
            coffre.supprimer("ia:" + k)

    def _fichier(self, p):
        with open(p.chemin, encoding="utf-8") as f:
            return f.read()

    def test_jamais_en_clair(self):
        p = Parametres()
        p["clef_claude"] = CLAUDE
        p["clef_gemini"] = GEMINI
        p.enregistrer()
        brut = self._fichier(p)
        self.assertNotIn(CLAUDE, brut)
        self.assertNotIn(GEMINI, brut)
        self.assertEqual(coffre.lire("ia:clef_gemini"), GEMINI)
        p2 = Parametres()
        self.assertEqual(p2["clef_claude"], CLAUDE)
        self.assertEqual(p2.get("clef_gemini"), GEMINI)
        # effacer la clef la retire aussi du coffre
        p2["clef_claude"] = ""
        p2.enregistrer()
        self.assertFalse(coffre.lire("ia:clef_claude"))
        self.assertEqual(Parametres()["clef_claude"], "")

    def test_migration_depuis_0_1(self):
        p = Parametres()
        d = json.loads(self._fichier(p)) if os.path.exists(p.chemin) else {}
        d["clef_gemini"] = GEMINI                       # comme la 0.1 : en clair dans le fichier
        with open(p.chemin, "w", encoding="utf-8") as f:
            json.dump(d, f)
        p2 = Parametres()
        self.assertEqual(p2["clef_gemini"], GEMINI)
        self.assertNotIn(GEMINI, self._fichier(p2))
        self.assertEqual(coffre.lire("ia:clef_gemini"), GEMINI)


if __name__ == "__main__":
    unittest.main()
