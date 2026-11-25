"""1.2.0 : voix par familles (modèle principal, variantes, voix réelle), « Mes voix… » (arbre, curseurs, pré-écoute gardée),
voix trouvée dans la phrase, branchements (Fabrique musique, assistant musique, clip de groupe, bibliothèque)."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app import voix_familles as VF


def vider(params):
    import shutil
    from app import bibliotheque_creations as B
    for g in ("voix", "groupe", "musicien"):
        shutil.rmtree(os.path.join(B.dossier(params), g), ignore_errors=True)


def wav(d, nom, f=220, s=2):
    from app import moteur
    ch = os.path.join(d, nom)
    moteur.lancer(["-y", "-f", "lavfi", "-i", f"sine=f={f}:d={s}", ch])
    return ch


class TestDonnees(unittest.TestCase):
    def setUp(self):
        self.params = {}
        vider(self.params)
        self.d = tempfile.mkdtemp()

    def test_reglages_et_description(self):
        r = VF.reglages_depuis_mesures({"f0": 110, "etendue": 18, "vibrato": 35, "brillance": 1200, "souffle": 0.2, "nettete": 0.5})
        self.assertLess(r["hauteur"], 30)
        self.assertGreater(r["etendue"], 65)
        self.assertGreater(r["chaleur"], 65)
        en, fr = VF.decrire(r)
        self.assertIn("warm", en)
        self.assertIn("pronounced vibrato", en)
        self.assertIn(_fr("timbre chaud"), fr)
        chaude = VF.variante_type("chaude", VF.NEUTRES)
        self.assertGreater(chaude["reglages"]["chaleur"], 50)
        self.assertIn("chaude", chaude["mots"])

    def test_famille_et_phrase(self):
        e = VF.garder_principal(self.params, "Archangel", dict(VF.NEUTRES, hauteur=70), role="chanteuse")
        e = VF.ajouter_variante(self.params, e, "Chaude (solo)", VF.appliquer(VF.reglages_de(e), {"chaleur": 25}), ["chaude", "solo"])
        e = VF.ajouter_variante(self.params, e, "Rapide", VF.appliquer(VF.reglages_de(e), {"debit": 30}), ["rapide"])
        self.assertEqual([v["nom"] for v in VF.variantes(e)], ["Chaude (solo)", "Rapide"])
        t = VF.trouver("une ballade à la manière d'Archangel, voix chaude, piano", self.params)
        self.assertEqual((t["entree"]["id"], t["variante"]["nom"]), (e["id"], "Chaude (solo)"))
        t = VF.trouver("rock à la manière d'Archangel", self.params)
        self.assertIsNone(t["variante"])
        self.assertEqual(t["mot_inconnu"], "")
        t = VF.trouver("à la manière d'Archangel douce", self.params)
        self.assertEqual((t["mot_inconnu"], t["type"]), ("douce", "douce"))
        self.assertIsNone(VF.trouver("une valse lente", self.params))
        c = VF.choix(e, VF.variantes(e)[1])
        self.assertIn("fast", c["voix_decrite"]["en"])
        self.assertNotIn("reference", c)                        # pas une voix réelle : jamais de timbre

    def test_voix_reelle(self):
        with self.assertRaises(ValueError):
            VF.garder_principal(self.params, "Ma voix", VF.NEUTRES, reel=True, accord=False)
        v = wav(self.d, "v.wav")
        e = VF.garder_principal(self.params, "Ma voix", VF.NEUTRES, reel=True, accord=True, voix_seule=v, extrait=v)
        self.assertEqual(VF.nom_affiche(e), "Ma voix " + _fr("(réel)"))
        self.assertTrue(os.path.exists(VF.choix(e)["reference"]))
        self.assertTrue(os.path.exists(VF.extrait_de(e)))

    def test_extrait_garde(self):
        e = VF.garder_principal(self.params, "Voix test", VF.NEUTRES)
        e = VF.ajouter_variante(self.params, e, "Aiguë", VF.NEUTRES)
        va = VF.variantes(e)[0]
        e = VF.garder_extrait(self.params, e, wav(self.d, "x.wav"), va)
        self.assertTrue(os.path.exists(VF.extrait_de(e, VF.variantes(e)[0])))
        self.assertEqual(VF.extrait_de(e), "")

    def test_catalogue(self):
        cat = VF.catalogue()
        self.assertTrue(cat)
        self.assertEqual([x["nom"] for x in cat], sorted([x["nom"] for x in cat], key=VF._net))
        self.assertTrue(all(len(x["variantes"]) >= 3 for x in cat))
        c = VF.choix_catalogue(cat[0], cat[0]["variantes"][0])
        self.assertTrue(c["voix_decrite"]["en"])
        self.assertNotIn("reference", c)

    def test_preecoute_cloud(self):
        from app import generateurs_video as GV
        vu = {}
        v = GV.demande_fal
        GV.demande_fal = lambda cle, point, corps, *a, **k: vu.update(point=point, corps=corps) or {"audio": {}}
        try:
            with self.assertRaises(ValueError):
                VF.preecoute("warm vocals", "[verse]\nLa nuit tombe sur le port\n", os.path.join(self.d, "p.wav"), {"clef_fal": "a:b"},
                             ou="cloud")
        finally:
            GV.demande_fal = v
        self.assertEqual(vu["point"], "fal-ai/ace-step")
        self.assertIn("La nuit tombe sur le port", vu["corps"]["lyrics"])
        self.assertEqual(VF.ligne_paroles(""), VF.PHRASE_NEUTRE["fr"])


def _fr(t):
    from app.langue import _
    return _(t)


class TestFenetres(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre()
        self.f.bienvenue = lambda *a, **k: None
        self.ed = self.f.nouveau_projet("16:9")
        self.d = tempfile.mkdtemp()
        vider(self.ed.params)
        self.e = VF.garder_principal(self.ed.params, "Archangel", dict(VF.NEUTRES, hauteur=70))
        self.e = VF.ajouter_variante(self.ed.params, self.e, "Chaude (solo)", VF.appliquer(VF.NEUTRES, {"chaleur": 25}), ["chaude"])

    def test_arbre_et_variante(self):
        from app.dialogues_mes_voix import DialogueMesVoix
        d = DialogueMesVoix(self.ed, self.ed.params, "[verse]\nJe marche seul\n")
        top = d.arbre.topLevelItem(0)
        self.assertEqual(top.text(0), "Archangel")
        self.assertEqual([top.child(k).text(0) for k in range(top.childCount())][1:], ["Chaude (solo)"])
        cat = d.arbre.topLevelItem(d.arbre.topLevelItemCount() - 1)
        self.assertGreater(cat.childCount(), 10)
        self.assertFalse(cat.isExpanded())
        d.arbre.setCurrentItem(top.child(1))
        self.assertTrue(d.boite_reglages.isVisible() or not d.isVisible())
        self.assertGreater(d.curseurs["chaleur"].value(), 50)
        d.curseurs["debit"].setValue(90)                         # changé pour ce morceau : le modèle ne bouge pas
        d.utiliser()
        self.assertTrue(d.choisi["modifiee"])
        self.assertIn("fast", d.choisi["voix_decrite"]["en"])
        self.assertEqual(VF.reglages_de(VF.mes_voix(self.ed.params)[0])["debit"], 50)
        d2 = DialogueMesVoix(self.ed, self.ed.params)
        d2.arbre.setCurrentItem(d2.arbre.topLevelItem(0).child(0))
        d2.curseurs["souffle"].setValue(85)
        d2._test_nom = "Murmure"
        d2.garder_variante()
        self.assertIn("Murmure", [v["nom"] for v in VF.variantes(VF.mes_voix(self.ed.params)[0])])
        d2.ajouter_type("aigue")
        self.assertIn(_fr("Aiguë"), [v["nom"] for v in VF.variantes(VF.mes_voix(self.ed.params)[0])])
        d2.recherche.setText("rock")
        self.assertTrue(d2.arbre.topLevelItem(d2.arbre.topLevelItemCount() - 1).isExpanded())

    def test_ecoute_sans_calcul_au_clic(self):
        from app.dialogues_mes_voix import DialogueMesVoix
        d = DialogueMesVoix(self.ed, self.ed.params)
        d.arbre.setCurrentItem(d.arbre.topLevelItem(0).child(1))
        d._ecouter(automatique=True)
        self.assertFalse(d._taches)                              # un clic ne lance jamais de calcul
        joue = []
        d._jouer = joue.append
        ex = wav(self.d, "ex.wav")
        VF.garder_extrait(self.ed.params, VF.mes_voix(self.ed.params)[0], ex, VF.variantes(self.e)[0])
        d.remplir()
        d.arbre.setCurrentItem(d.arbre.topLevelItem(0).child(1))
        d._ecouter(automatique=True)
        self.assertEqual(len(joue), 1)
        self.assertFalse(d._taches)

    def test_fabrique(self):
        from app.dialogues_musique_ia import DialogueFabriqueMusique
        dl = DialogueFabriqueMusique(self.ed, self.ed.params)
        self.assertEqual(dl.b_voix_style.text(), _fr("Mes voix…"))
        self.assertIsNone(dl.b_voix_style.menu())                # un seul bouton
        dl._test_mes_voix = lambda d: (d.arbre.setCurrentItem(d.arbre.topLevelItem(0).child(1)), d.utiliser(), d.choisi)[-1]
        dl.mes_voix()
        self.assertIn("warm", dl.voix_decrite["en"])
        self.assertEqual(dl.fiche()["voix_choisie"]["variante"], VF.variantes(self.e)[0]["id"])
        dl._sans_voix_decrite()
        dl.phrase.setPlainText("une ballade rock, à la manière d'Archangel, voix chaude")
        dl.voix_de_la_phrase()
        self.assertIn("Chaude", dl.fiche()["voix_choisie"]["nom"])
        self.assertNotIn("Archangel", dl.phrase.toPlainText())
        dl._sans_voix_decrite()
        dl._test_variante = lambda e, t: None                    # « Archangel douce » : on demande ; ici, le modèle principal
        dl.phrase.setPlainText("à la manière d'Archangel douce")
        dl.voix_de_la_phrase()
        self.assertEqual(dl.fiche()["voix_choisie"].get("variante"), None)
        self.assertTrue(dl.voix_decrite)

    def test_clip_et_bibliotheque(self):
        from app import bibliotheque_creations as B, clip_groupe as CG, moteur
        from app.dialogues_clip_groupe import DialogueClipGroupe
        son = wav(self.d, "s.wav", s=4)
        m = self.ed.projet.ajouter_media(son, moteur.sonder(son))
        c = self.ed.projet.ajouter_clip(m["id"], "audio", 0.0)
        dl = DialogueClipGroupe(self.ed, c)
        dl.clip = {"groupe": CG.groupe_propose({"caption_en": "rock"}), "plans": [], "lieu": "concert", "anime": False, "format": "16:9",
                   "chemin": son, "analyse": {}}
        for g in dl.clip["groupe"]:
            dl._ligne_membre(g)
        dl._test_mes_voix = lambda d: (d.arbre.setCurrentItem(d.arbre.topLevelItem(0).child(0)), d.utiliser(), d.choisi)[-1]
        dl._voix_chant()
        dl._test_precision = "Archangel groupe"
        dl._garder_groupe()
        g = B.lister(self.ed.params, "groupe")[0]
        self.assertEqual(g["donnees"]["voix"]["entree"], self.e["id"])
        from app.dialogues_bibliotheque_creations import DialogueBibliothequeCreations
        bd = DialogueBibliothequeCreations(self.ed)
        bd._test_variantes = lambda d: d
        d = bd.variantes_voix(VF.mes_voix(self.ed.params)[0])
        self.assertEqual(d.arbre.currentItem().text(0), _fr("Normale (modèle principal)"))


if __name__ == "__main__":
    unittest.main()
