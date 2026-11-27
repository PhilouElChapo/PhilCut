"""1.3.13 (Philippe, 27/11) : ma voix parlée gardée dans la bibliothèque (variantes), choisie dans « Continuer avec ma voix »
et dans la Voix off ; voix du groupe reliée d'office ; croche sur les entrées qui ont un son."""
import os, sys, tempfile, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import voix_familles as VF, bibliotheque_creations as B, moteur


def _son(d, nom="moi.wav", secondes=8):
    ch = os.path.join(d, nom)
    moteur.lancer(["-y", "-f", "lavfi", "-i", f"sine=f=180:d={secondes}", "-ar", "24000", "-ac", "1", ch])
    return ch


def attendre(cond, s=60):
    fin = time.time() + s
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    return cond()


class TestMaVoix(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre()
        self.f.bienvenue = lambda *a, **k: None
        self.ed = self.f.nouveau_projet("16:9")
        self.p = self.ed.params
        self.d = tempfile.mkdtemp()

    def test_garder_et_variantes(self):
        with self.assertRaises(ValueError):
            VF.garder_parole(self.p, "Ma voix", _son(self.d), False)
        VF.garder_parole(self.p, "Ma voix test", _son(self.d), True)
        VF.garder_parole(self.p, "ma voix test", _son(self.d, "b.wav"), True, "calme")
        noms = [x["nom"] for x in VF.voix_parlees(self.p) if x["nom"].startswith("Ma voix test")]
        self.assertEqual(noms, ["Ma voix test", "Ma voix test — calme"])
        e = next(v for v in VF.mes_voix(self.p) if v["nom"] == "Ma voix test")
        self.assertTrue(B.son_genere(e))
        self.assertIn("voix parlée gardée", B.resume(e))
        from app.dialogues_bibliotheque_creations import icone_entree
        self.assertIsNotNone(icone_entree(e))                        # une croche, même sans image

    def test_voix_off_et_continuer(self):
        from app import voix as V, voix_clone as VC
        from app.dialogues_voix import _ChoixVoix
        from app.dialogues_voix_suite import DialogueVoixSuite
        VF.garder_parole(self.p, "Ma voix off", _son(self.d), True)
        anc = VC.manquant, VC.dire
        vus = []

        def faux_dire(texte, ref, sortie, langue="fr", expr=0.5, params=None, **k):
            vus.append((texte, len(ref)))
            VC.ecrire(sortie, ref)
            return sortie, len(ref) / VC.TAUX
        VC.manquant, VC.dire = (lambda p=None: None), faux_dire
        try:
            c = _ChoixVoix(self.p, "fr", ma_voix=True)
            self.assertEqual(c.choix()[0], "ma_voix")                 # ma voix en tête
            sortie = os.path.join(self.d, "off.wav")
            V.lire("Bonjour à tous.", sortie, self.p, *c.choix())
            self.assertTrue(os.path.exists(sortie))
            self.assertEqual(vus[-1][0], "Bonjour à tous.")
            dl = DialogueVoixSuite(self.ed)
            k = dl.gardees.findText("Ma voix off")
            self.assertGreater(k, 0)
            dl.gardees.setCurrentIndex(k)
            self.assertTrue(dl.accord.isChecked())
            self.assertEqual(dl._media(), dl.gardees.itemData(k))
            # garder une variante depuis un fichier
            dl.gardees.setCurrentIndex(0)
            dl.fichier = _son(self.d, "c.wav", 12)
            dl.ref_debut.setValue(0.0)
            dl.ref_duree.setValue(10.0)
            dl.accord.setChecked(True)
            dl.garder_voix("Ma voix off", "enjouée")
            self.assertTrue(attendre(lambda: not dl._en_calcul() and dl.gardees.findText("Ma voix off — enjouée") > 0))
            self.assertEqual(dl.gardees.currentText(), "Ma voix off — enjouée")
            dl.close()
        finally:
            VC.manquant, VC.dire = anc

    def test_voix_du_groupe_d_office(self):
        from app import clip_groupe as CG
        from app.dialogues_clip_groupe import DialogueClipGroupe
        VF.garder_principal(self.p, "Groupe Essai", {}, role="chanteur")
        son = _son(self.d, "s.wav", 4)
        m = self.ed.projet.ajouter_media(son, moteur.sonder(son))
        c = self.ed.projet.ajouter_clip(m["id"], "audio", 0.0)
        dl = DialogueClipGroupe(self.ed, c)
        dl.clip = {"groupe": CG.groupe_propose({"caption_en": "rock"}), "plans": [], "lieu": "concert", "anime": False,
                   "format": "16:9", "chemin": son, "analyse": {}}
        for g in dl.clip["groupe"]:
            dl._ligne_membre(g)
        dl._test_precision = "Groupe essai"
        dl._garder_groupe()
        self.assertEqual(dl.clip["voix_chant"]["nom"], "Groupe Essai")
        dl.close()


if __name__ == "__main__":
    unittest.main()
