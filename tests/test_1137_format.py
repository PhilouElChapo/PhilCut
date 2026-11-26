"""1.3.9 : format du projet imposé aux images de départ ; création « scènes » encore en gestes à redécouper."""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from app import ia


class TestFormat(unittest.TestCase):
    def test_config(self):
        self.assertEqual(ia._config_image("16:9")["imageConfig"], {"aspectRatio": "16:9"})
        self.assertEqual(ia._config_image("9:16")["imageConfig"], {"aspectRatio": "9:16"})
        self.assertNotIn("imageConfig", ia._config_image(None))

    def test_envoye(self):
        vus = []
        anc = ia._http, ia.modeles_image_gemini, ia.nettoyer_clef
        ia._http = lambda url, corps, delai=0: (vus.append(dict(corps["generationConfig"])),
                                                {"candidates": [{"content": {"parts": [{"inlineData": {"data": "cG5n"}}]}}]})[1]
        ia.modeles_image_gemini = lambda c: ["m"]
        ia.nettoyer_clef = lambda c: "k"
        try:
            ia.generer_image({"clef_gemini": "k"}, "x", format_="16:9")
        finally:
            ia._http, ia.modeles_image_gemini, ia.nettoyer_clef = anc
        self.assertEqual(vus[0]["imageConfig"]["aspectRatio"], "16:9")

    def test_gestes(self):
        from app.dialogues_assistant_creation import DialogueAssistant as D
        class F:
            seq = {"mode": "scenes", "plans": [{"duree": 3}] * 11}
        self.assertTrue(D._gestes(F()))
        F.seq = {"mode": "scenes", "plans": [{"duree": 12}, {"duree": 12}, {"duree": 10}, {"duree": 15}]}
        self.assertFalse(D._gestes(F()))
        F.seq = {"mode": "", "plans": [{"duree": 12}]}
        self.assertTrue(D._gestes(F()))


if __name__ == "__main__":
    unittest.main()
