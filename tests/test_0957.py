"""0.9.57 : « Continuer avec ma voix ». Chaîne Chatterbox reproduite avec de faux modèles (positions, empreinte devant le
texte au premier pas, pénalité de répétition, arrêt au jeton de fin, jetons spéciaux jamais décodés), découpe du texte,
extrait de voix (trop court, silencieux), niveau accordé à l'extrait, mention « fabriquée par IA » dans le WAV, pose sur
la piste Voix en un Annuler, fenêtre (accord obligatoire), menus, guide, bouton du plan de liaison.
L'essai avec le vrai modèle tourne sur GitHub (outils_dev/essai_voix.py)."""
import os, sys, time, unittest, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None
from app import voix_clone as V

D = 8                      # largeur des vecteurs des faux modèles (1024 dans le vrai)


class _E:
    def __init__(self, name, type_="tensor(float)"):
        self.name, self.type = name, type_


class FauxEncodeur:
    def run(self, _s, e):
        n = e["audio_values"].shape[1]
        return [np.ones((1, 3, D), np.float32), np.arange(5, dtype=np.int64)[None] + 100, np.full((1, 192), n / V.TAUX, np.float32),
                np.zeros((1, 10, 80), np.float32)]


class FauxJetons:
    def __init__(self):
        self.appels = []

    def run(self, _s, e):
        self.appels.append({k: np.array(v) for k, v in e.items()})
        return [np.zeros((1, e["input_ids"].shape[1], D), np.float32)]


class FauxLangage:
    """Rend, dans l'ordre, les jetons voulus ; le jeton 50 est toujours un peu favori (la pénalité de répétition doit
    l'empêcher de revenir sans fin)."""

    def __init__(self, suite):
        self.suite, self.k, self.vus = list(suite), 0, []

    def get_inputs(self):
        return [_E("inputs_embeds"), _E("attention_mask", "tensor(int64)")] + \
            [_E(f"past_key_values.{c}.{kv}") for c in range(V.COUCHES) for kv in ("key", "value")]

    def run(self, _s, e):
        self.vus.append((e["inputs_embeds"].shape[1], e["attention_mask"].shape[1], e["past_key_values.0.key"].shape[2]))
        lg = np.zeros((1, e["inputs_embeds"].shape[1], 8194), np.float32)
        t = self.suite[min(self.k, len(self.suite) - 1)]
        lg[0, -1, t] = 10.0
        self.k += 1
        tot = e["attention_mask"].shape[1]
        return [lg] + [np.zeros((1, V.TETES, tot, V.DIM_TETE), np.float32) for _ in range(2 * V.COUCHES)]


class FauxDecodeur:
    def __init__(self):
        self.recus = None

    def run(self, _s, e):
        self.recus = e["speech_tokens"].copy()
        n = e["speech_tokens"].shape[1] - 5                       # l'extrait (5 jetons) n'est pas rendu
        t = np.arange(n * 960) / V.TAUX
        return [(0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)[None]]


class FauxDecoupeur:
    class _R:
        def __init__(self, ids):
            self.ids = ids

    def encode(self, texte):
        return self._R([6563, 255, 634] + [ord(c) % 200 + 3 for c in texte[4:]] + [0, 6561, 6561])


def fausses_sessions(suite=(10, 11, 12, V.FIN_PAROLE)):
    return {"encodeur": FauxEncodeur(), "jetons": FauxJetons(), "langage": FauxLangage(suite), "decodeur": FauxDecodeur(),
            "tokenizer": FauxDecoupeur()}


def reference(secondes=6.0, niveau=0.1):
    t = np.arange(int(secondes * V.TAUX)) / V.TAUX
    return (niveau * np.sqrt(2) * np.sin(2 * np.pi * 150 * t)).astype(np.float32)


class TestChaine(unittest.TestCase):
    def test_texte(self):
        self.assertEqual(V.normaliser("  et   maintenant ,passons à « autre » chose  "), 'Et maintenant,passons à "autre" chose.')
        self.assertEqual(V.normaliser("Vraiment ?"), "Vraiment?")
        self.assertEqual(V.phrases(""), [])
        p = V.phrases("Une phrase. " * 40)
        self.assertGreater(len(p), 1)
        self.assertTrue(all(len(x) <= 230 for x in p))
        self.assertEqual(" ".join(p).count("Une phrase."), 40)                     # rien de perdu

    def test_suite_des_operations(self):
        s = fausses_sessions()
        emp = V.empreinte(s, reference())
        ids = V.jetons_texte(s["tokenizer"], "Bonjour.", "fr")
        j = V.parole(s, ids, emp, 0.7, maxi=50)
        self.assertEqual(j.tolist(), [[10, 11, 12]])
        ap = s["jetons"].appels
        # premier pas : 0 pour le jeton d'expressivité (spécial), puis 0, 1, 2… pour le texte, 0 pour les jetons de parole
        p0 = ap[0]["position_ids"][0].tolist()
        self.assertEqual(p0[:4], [0, 0, 1, 2])
        self.assertEqual(p0[-2:], [0, 0])
        self.assertAlmostEqual(float(ap[0]["exaggeration"][0]), 0.7, places=5)
        self.assertEqual([int(a["position_ids"][0, 0]) for a in ap[1:]], [1, 2, 3])
        # empreinte de la voix (3 vecteurs) devant le texte au premier pas, puis un jeton à la fois avec le cache
        vus = s["langage"].vus
        self.assertEqual(vus[0], (3 + ids.shape[1], 3 + ids.shape[1], 0))
        self.assertEqual(vus[1][0], 1)
        self.assertEqual(vus[1][2], vus[0][1])
        son = V.decoder(s, j, emp)
        self.assertEqual(s["decodeur"].recus.tolist()[0][:5], [100, 101, 102, 103, 104])      # extrait d'abord
        self.assertEqual(son.size, 3 * 960)

    def test_repetition_penalisee_et_jetons_speciaux(self):
        """Un jeton favori qui revient est freiné ; un jeton spécial n'arrive jamais au décodeur ; arrêt à maxi."""
        lg = np.zeros((1, 8194), np.float32)
        lg[0, 50], lg[0, 60] = 2.0, 1.9
        deja = np.array([[V.DEBUT_PAROLE, 50]])
        self.assertEqual(int(np.argmax(V._penaliser(deja, lg))), 60)
        s = fausses_sessions((10, V.DEBUT_PAROLE, 11))                             # jamais de fin
        j = V.parole(s, V.jetons_texte(s["tokenizer"], "x", "fr"), V.empreinte(s, reference()), maxi=6)
        self.assertNotIn(V.DEBUT_PAROLE, j.tolist()[0])
        self.assertLessEqual(j.shape[1], 6)

    def test_dire_niveau_mention_arret(self):
        d = os.environ["APPDATA"]
        s = fausses_sessions()
        ref = reference(niveau=0.05)
        sortie = os.path.join(d, "suite.wav")
        etapes = []
        chem, duree = V.dire("Et maintenant, passons à autre chose. Voici la suite.", ref, sortie, "fr", s=s,
                             progression=lambda f, t="": etapes.append(f))
        self.assertTrue(V.lire_mention(chem))
        with wave.open(chem) as w:
            self.assertEqual((w.getframerate(), w.getnchannels()), (V.TAUX, 1))
            a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
        self.assertAlmostEqual(duree, a.size / V.TAUX, places=3)
        self.assertAlmostEqual(V.niveau(a), V.niveau(ref), delta=0.01)             # même niveau que l'extrait
        self.assertEqual(etapes[-1], 1.0)
        self.assertEqual(etapes, sorted(etapes))
        with self.assertRaises(InterruptedError):
            V.dire("Une phrase.", ref, sortie, "fr", s=fausses_sessions(), arret=lambda: True)
        with self.assertRaises(V.ErreurVoix):
            V.dire("   ", ref, sortie, "fr", s=fausses_sessions())
        with self.assertRaises(V.ErreurVoix):
            V.jetons_texte(FauxDecoupeur(), "x", "xx")

    def test_extrait(self):
        from app import moteur
        d = os.environ["APPDATA"]
        court, muet, bon = (os.path.join(d, n) for n in ("court.wav", "muet.wav", "bon.wav"))
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=200:d=2", court])
        moteur.lancer(["-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "6", muet])
        moteur.lancer(["-y", "-f", "lavfi", "-i", "sine=f=200:d=30", bon])
        with self.assertRaises(V.ErreurVoix):
            V.lire_reference(court)
        with self.assertRaises(V.ErreurVoix):
            V.lire_reference(muet)
        a = V.lire_reference(bon, 2.0, 40)
        self.assertAlmostEqual(a.size / V.TAUX, V.REF_MAX, delta=0.05)              # 15 s au plus
        clip = {"debut": 10.0, "src_debut": 5.0, "src_fin": 35.0, "vitesse": 1.0}
        self.assertEqual(V.extrait_par_defaut(clip, 30.0), (13.0, 12.0))           # les 12 s avant la ligne rouge
        self.assertEqual(V.extrait_par_defaut(clip, None), (23.0, 12.0))           # sinon la fin du plan
        self.assertEqual(V.extrait_par_defaut(clip, 11.0), (23.0, 12.0))           # trop peu avant la ligne : la fin du plan

    def test_manquant(self):
        from app import packs_ia as P
        anc = P.installe
        P.installe = lambda cle: False
        try:
            self.assertIn("Continuer avec ma voix", V.manquant())
        finally:
            P.installe = anc


class TestFilm(unittest.TestCase):
    def setUp(self):
        from app.fenetre import Fenetre
        self.f = Fenetre([])
        self.ed = self.f._editeur_ou_nouveau()
        d = os.environ["APPDATA"]
        self.wav = os.path.join(d, "voix_essai.wav")
        V.ecrire(self.wav, reference(3.0))

    def tearDown(self):
        self.ed.projet.modifie = False

    def test_pose_piste_voix_un_annuler(self):
        p = self.ed.projet
        n = len(p.clips)
        c = V.poser(p, self.wav, 4.0)
        self.assertEqual(c["piste"], "voix")
        self.assertTrue(c["voix_ia"])
        self.assertAlmostEqual(c["debut"], 4.0)
        c2 = V.poser(p, self.wav, 5.0)                                              # la piste Voix est prise à cet endroit
        self.assertNotEqual(c2["piste"], "voix")
        p.annuler()
        p.annuler()
        self.assertEqual(len(p.clips), n)

    def test_fenetre(self):
        from app import moteur
        from app.dialogues_voix_suite import DialogueVoixSuite
        from app import packs_ia as P
        v = commun.video_test(os.environ["APPDATA"], "voix_plan.mp4", duree=20)
        m = self.ed.projet.ajouter_media(v, moteur.sonder(v))
        clip = self.ed.projet.ajouter_clip(m["id"])
        self.ed.rafraichir()
        self.ed.timeline.position = 15.0
        anc_m, anc_d = V.manquant, V.dire
        V.manquant = lambda params=None: None
        V.dire = lambda texte, ref, sortie, langue="fr", expr=0.5, params=None, progression=None, arret=None: \
            (progression(0.5, "…"), V.ecrire(sortie, ref[: V.TAUX * 2]), (sortie, 2.0))[2]
        try:
            d = self.ed.continuer_voix(clip)
            self.assertIsInstance(d, DialogueVoixSuite)
            self.assertFalse(d.isModal())
            self.assertEqual((d.ref_debut.value(), d.ref_duree.value()), (3.0, 12.0))
            self.assertIn("15,0", d.ou.text())
            d.texte.setPlainText("Et maintenant, passons à autre chose.")
            self.assertFalse(d.b_fabriquer.isEnabled())                             # l'accord d'abord
            d.accord.setChecked(True)
            self.assertTrue(d.b_fabriquer.isEnabled())
            self.assertEqual(d.langue.currentData(), "fr")
            d.fabriquer()
            t0 = time.time()
            while time.time() - t0 < 30 and d.resultat is None and "✕" not in d.etat.text():
                app.processEvents()
                time.sleep(0.02)
            self.assertIsNotNone(d.resultat, d.etat.text())
            self.assertTrue(d.b_poser.isEnabled())
            d.poser()
            from app import guides as G
            self.assertTrue(G.est_fait("voix_ia", self.ed))
            c = next(c for c in self.ed.projet.clips if c.get("voix_ia"))
            self.assertAlmostEqual(c["debut"], 15.0)
            from verif_tronques import tronques
            self.assertEqual(tronques(d), [])
            d.close()
        finally:
            V.manquant, V.dire = anc_m, anc_d

    def test_menus_guide_liaison(self):
        from app import moteur, guides as G
        v = commun.video_test(os.environ["APPDATA"], "voix_plan2.mp4", duree=3)
        m = self.ed.projet.ajouter_media(v, moteur.sonder(v))
        a = self.ed.projet.ajouter_clip(m["id"])
        b = self.ed.projet.ajouter_clip(m["id"])
        self.ed.rafraichir()
        vus = []
        self.ed.timeline._exec_menu = lambda mm, pos: vus.append([x.text() for x in mm.actions()])
        self.ed.timeline.menu_clip(a, None, 0.5)
        self.assertIn("Continuer avec cette voix…", vus[-1])
        g = next(x for x in G.guides() if x["id"] == "suite_voix")
        self.assertEqual(g["etat"], "ok")
        # depuis la fenêtre du plan de liaison : la voix va au début du plan de liaison, avec la voix du premier plan
        from app.dialogues_liaison import DialogueLiaison
        dl = DialogueLiaison(self.ed, a, b)
        self.assertTrue(dl.b_voix.isHidden())
        from app import liaison as L
        dl.pose = L.poser(self.ed.projet, a, b, v)
        dv = dl.voix_sur_liaison()
        self.assertIs(dv.clip, a)
        self.assertAlmostEqual(dv.debut, dl.pose["debut"])
        self.assertEqual(dv.sur_liaison, dl.pose["id"])
        self.assertIn("plan de liaison", dv.ou.text())
        dv.close()
        dl.close()


if __name__ == "__main__":
    unittest.main()
