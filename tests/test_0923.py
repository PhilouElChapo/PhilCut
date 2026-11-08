"""0.9.23 : monter par le texte — transcription gardée par rush, couper une phrase dans le texte coupe la vidéo,
« euh » et silences retirés, la musique continue."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import moteur

MOTS = [[0.5, 0.9, "Bonjour"], [1.0, 1.4, "à"], [1.45, 1.9, "tous,"], [2.0, 2.3, "euh"], [2.4, 2.8, "aujourd'hui"],
        [2.9, 3.2, "on"], [3.25, 3.6, "vole."], [5.6, 6.0, "Ensuite"], [6.1, 6.6, "atterrissage."]]


class Test0923(unittest.TestCase):
    def _editeur(self):
        from app.config import Parametres
        pa = Parametres()
        pa.update(bienvenue_vue=True, maj_auto=False, synchro=False)
        pa.enregistrer()
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        d = tempfile.mkdtemp()
        v = commun.video_test(d, "vol.mp4", duree=8)
        m = ed.projet.ajouter_media(v, moteur.sonder(v))
        ed.ajouter_a_la_timeline(m["id"])
        mu = commun.video_test(d, "musique.mp4", duree=8)
        mm = ed.projet.ajouter_media(mu, moteur.sonder(mu))
        ed.projet.ajouter_clip(mm["id"], "audio", 0.0, 0.0, 8.0)
        return f, ed, m

    def test_transcription_gardee_par_rush(self):
        from app import montage_texte as MT, sous_titres as ST
        f, ed, m = self._editeur()
        self.assertEqual(MT.rushes_a_transcrire(ed.projet), [m["id"]])
        vus = []
        ST.transcrire_fichier = lambda chemin, **k: (vus.append(chemin), [(0.5, 3.6, "Bonjour à tous", [(0.5, 0.9, "Bonjour"), (1.0, 1.4, "à"),
                                                                                                   (1.45, 1.9, "tous")])])[1]
        self.assertEqual(MT.transcrire(ed.projet), 1)
        self.assertEqual([w for _d, _f, w in m["mots"]], ["Bonjour", "à", "tous"])
        self.assertEqual(MT.rushes_a_transcrire(ed.projet), [])                 # une seule fois
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()

    def test_couper_dans_le_texte(self):
        from app import montage_texte as MT
        from app.dialogues_texte import DialogueMontageTexte
        from PySide6.QtGui import QTextCursor
        f, ed, m = self._editeur()
        m["mots"] = [list(x) for x in MOTS]
        d = DialogueMontageTexte(ed)
        self.assertIn("Bonjour à tous, euh aujourd'hui on vole.", d.texte.toPlainText())
        self.assertIn("\n\nEnsuite", d.texte.toPlainText())                      # pause longue : nouveau paragraphe
        self.assertEqual(MT.hesitations(d.mots), [3])
        # sélectionner « aujourd'hui on » et couper
        a = d.positions[4][0]
        b = d.positions[5][1]
        cur = d.texte.textCursor()
        cur.setPosition(a)
        cur.setPosition(b, QTextCursor.KeepAnchor)
        d.texte.setTextCursor(cur)
        avant = ed.projet.duree()
        video_avant = sum(c["src_fin"] - c["src_debut"] for c in ed.projet.clips_piste("video"))
        enleve = d.couper_selection()
        self.assertAlmostEqual(enleve, 3.19 - 2.34, places=2)                   # de « aujourd'hui » au début de « vole »
        self.assertNotIn("aujourd'hui", d.texte.toPlainText())
        self.assertIn("euh vole.", d.texte.toPlainText())
        video_apres = sum(c["src_fin"] - c["src_debut"] for c in ed.projet.clips_piste("video"))
        self.assertAlmostEqual(video_avant - video_apres, enleve, places=2)
        musique = ed.projet.clips_piste("audio")
        self.assertEqual(len(musique), 1)                                        # la musique continue, pas coupée
        self.assertAlmostEqual(musique[0]["src_fin"], 8.0, places=2)
        # « euh » puis silences
        d.retirer_euh()
        self.assertNotIn("euh", d.texte.toPlainText())
        n = len(MT.silences(d.mots, ed.projet, 0.8))
        self.assertGreaterEqual(n, 1)
        d.retirer_silences()
        self.assertEqual(MT.silences(d.mots, ed.projet, 0.8), [])
        self.assertIn("Bonjour à tous, vole. Ensuite atterrissage.", d.texte.toPlainText().replace("\n\n", " "))
        # Annuler revient
        d.annuler()
        self.assertGreater(ed.projet.duree(), 0)
        d.reject()
        ed.projet.modifie = False
        f.hide()
        f.deleteLater()


if __name__ == "__main__":
    unittest.main()
