"""0.9.94 : crédit épuisé (Gemini, Claude, fal.ai) dit en clair, avec l'endroit où recharger."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class TestCredit(unittest.TestCase):
    def test_gemini(self):
        from app.taches import texte_erreur
        e = RuntimeError("402 : Your prepayment credits are depleted. Please go to AI Studio at https://ai.studio/projects "
                         "to manage your project and billing.")
        t = texte_erreur(e)
        self.assertIn("Crédit Gemini épuisé", t)
        self.assertIn("aistudio.google.com", t)

    def test_autres(self):
        from app.taches import texte_erreur
        self.assertIn("Claude", texte_erreur(RuntimeError("Your credit balance is too low to access the Anthropic API")))
        self.assertIn("fal.ai", texte_erreur(RuntimeError("fal: User is locked. Reason: Exhausted balance.")))
        self.assertEqual(texte_erreur(RuntimeError("délai dépassé")), "délai dépassé")


if __name__ == "__main__":
    unittest.main()
