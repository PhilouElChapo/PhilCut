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


    def test_lignes_et_bouton_mis_en_avant(self):
        from PySide6.QtWidgets import QLabel, QWidget
        from app.credit_ia import LignesCredit, fournisseur_epuise
        self.assertEqual(fournisseur_epuise("402 : Your prepayment credits are depleted"), "google")
        self.assertEqual(fournisseur_epuise("rien"), "")
        w = QWidget()
        etat = QLabel(w)
        lc = LignesCredit({}, ["google", "anthropic"], w).surveiller(etat)
        self.assertEqual(set(lc.lignes), {"google", "anthropic"})
        etat.setText("✕ 402 : Your prepayment credits are depleted. Go to AI Studio billing")
        self.assertIn("c62828", lc.lignes["google"].b.styleSheet())
        self.assertEqual(lc.lignes["anthropic"].b.styleSheet(), "")

    def test_bibliotheque_a_ses_credits(self):
        from app.dialogues_bibliotheque_creations import DialogueBibliothequeCreations
        from PySide6.QtWidgets import QWidget
        ed = QWidget()
        ed.params = {}
        d = DialogueBibliothequeCreations(ed)
        self.assertEqual(set(d.credits.lignes), {"google", "anthropic"})
        d.etat.setText("✕ " + "402 : Your prepayment credits are depleted.")
        self.assertIn("c62828", d.credits.lignes["google"].b.styleSheet())


if __name__ == "__main__":
    unittest.main()
