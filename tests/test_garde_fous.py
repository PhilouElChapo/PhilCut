"""Garde-fous automatiques (0.9.55) : chaque règle des guidelines de Philippe, et chaque incident, vérifié à chaque version.

Une règle écrite s'oublie ; une règle vérifiée à chaque version, non. Quand un garde-fou échoue, son message dit la règle
et quoi faire. Le point de départ (ce qui n'était pas encore conforme le 13/11/2026) est dans garde_fous_dette.json :
ces listes ne peuvent que rétrécir.

Règles issues des guidelines
- G6  Listes par ordre alphabétique (accents ignorés), sauf un ordre qui a un sens, annoncé.
- G7  Aucun texte tronqué, aucune fenêtre plus grande qu'un écran de 1024×768, pas de défilement horizontal.
- G8  Tout réglage est aussi dans les Préférences (sinon : mémoire interne, classée comme telle).
- G9  Toute tâche longue montre sa progression.
- G10 Les fenêtres de fichiers passent par PhilCut (dossier du système d'abord, puis le dernier utilisé).
- G11 Exemples neutres : rien de personnel dans PhilCut (test_050).
- G12 Sécurité : aucune clef ni aucun secret dans le code ; jamais de navigateur imité (User-Agent déguisé).
- G13 Les fenêtres de progression n'ont pas le bouton « réduire » de Windows (bouton « Réduire » de PhilCut).
- G14 Aucun texte sans traduction (test_traductions).

Règles issues des incidents (12-13/11/2026)
- G1  Jamais une erreur vide : tout « ✕ … » passe par texte_erreur (« Agrandir ×2 : » vide).
- G2  Jamais un fil détruit en plein travail : tout QThread hérite de FilProtege (plantage 0xc0000409 de « Dites-le »).
- G3  Une aide ne cite jamais un menu qui n'existe pas (guides « Comment faire… »).
- G4  Une IA est essayée en vrai avant d'être livrée (un essai outils_dev/essai_*.py qui la nomme).
- G5  Rien ne se perd : ce qui est fait se défait d'un seul Annuler, à l'identique.
"""
import copy, glob, json, os, re, sys, unicodedata, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()
from app.fenetre import Fenetre as _F
_F.bienvenue = lambda self, *a, **k: None

RACINE = commun.RACINE
DETTE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "garde_fous_dette.json"), encoding="utf-8"))


def _sources():
    for p in sorted(glob.glob(os.path.join(RACINE, "app", "*.py"))):
        yield os.path.relpath(p, RACINE).replace("\\", "/"), open(p, encoding="utf-8").read()


def _norm(t):
    t = (t or "").replace("&", "").replace("…", "").strip()
    return unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()


def _fenetre():
    from app.fenetre import Fenetre
    f = Fenetre([])
    ed = f._editeur_ou_nouveau()
    v = commun.video_test(os.environ["APPDATA"], "garde.mp4", duree=3)
    m = ed.projet.ajouter_media(v, {"duree": 3.0})
    ed.projet.ajouter_clip(m["id"])
    ed.projet.ajouter_clip(m["id"])                    # deux plans : les menus « avec le plan suivant » existent
    ed.rafraichir()
    return f, ed


class G1ErreursJamaisVides(unittest.TestCase):
    def test_texte_erreur(self):
        """Tout message « ✕ » qui montre une erreur passe par texte_erreur (jamais vide)."""
        fautes = []
        for p, s in _sources():
            for i, l in enumerate(s.split("\n"), 1):
                if "✕" in l and (re.search(r"\bstr\((e|err|erreur|exc)\)", l) or re.search(r"\{e\}\"[^)]*, e=(e|err|erreur)\)", l)):
                    fautes.append(f"{p}:{i}")
        self.assertEqual(fautes, [], "G1 : une erreur peut s'afficher vide — utilisez texte_erreur(e) : " + ", ".join(fautes))
        from app.taches import texte_erreur
        self.assertTrue(texte_erreur(RuntimeError()))


class G2FilsProteges(unittest.TestCase):
    def test_qthread(self):
        fautes = [p for p, s in _sources() if re.search(r"class \w+\(QThread\)", s) and p != "app/taches.py"]
        self.assertEqual(fautes, [], "G2 : un fil (QThread) doit hériter de taches.FilProtege : " + ", ".join(fautes))


class G3GuidesMenusExistants(unittest.TestCase):
    def test_chemins(self):
        from app import guides as G
        f, ed = _fenetre()
        mb = f.menuBar()
        vus = []
        ed.timeline._exec_menu = lambda m, pos: vus.append(m)
        fautes = []
        for g in G.guides():
            for e in g["etapes"]:
                mo = e.get("montrer") or {}
                if "menu" in mo:
                    a = G._trouver(mb.actions(), mo["menu"][0])
                    menu = a.menu() if a else None
                    for seg in mo["menu"][1:]:
                        if menu is None:
                            break
                        menu.aboutToShow.emit()
                        a = G._trouver(menu.actions(), seg)
                        menu = (a.menu() or menu) if a else None
                    if a is None or menu is None:
                        fautes.append(f"{g['id']} : {' › '.join(mo['menu'])}")
                if "clic_droit" in mo:
                    if any("corriger" in _norm(x) for x in mo["clic_droit"]):
                        ed.projet.clips_piste("video")[0]["ajustement"] = "suivi"
                    vus.clear()
                    G.montrer_clic_droit(ed, mo["clic_droit"])
                    m = vus[-1] if vus else None
                    for seg in mo["clic_droit"]:
                        a = G._trouver(m.actions(), seg) if m else None
                        if a is None:
                            fautes.append(f"{g['id']} : clic droit › {' › '.join(mo['clic_droit'])}")
                            break
                        m = a.menu() or m
        self.assertEqual(fautes, [], "G3 : un guide cite un menu qui n'existe pas : " + " ; ".join(fautes))
        ed.projet.modifie = False


class G4IAEssayeesEnVrai(unittest.TestCase):
    def test_essais(self):
        sys.path.insert(0, os.path.join(RACINE, "outils_dev"))
        import moteurs_creatifs as M
        essais = " ".join(open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(RACINE, "outils_dev", "essai_*.py")))
        anciens = set(DETTE["G4_modeles_essayes_par_philippe"])
        fautes = [k for k in M.MODELES if k not in anciens and k not in essais]
        self.assertEqual(fautes, [], "G4 : modèle d'IA livré sans essai réel (outils_dev/essai_*.py qui le nomme) : " + ", ".join(fautes))


class G5RienNeSePerd(unittest.TestCase):
    def test_annuler_a_l_identique(self):
        """Chaque action de « Dites-le » (et la pose des sons séparés) se défait d'un seul Annuler, à l'identique."""
        from app import commande_ia as C
        f, ed = _fenetre()
        p = ed.projet
        for phrase in ("un marqueur à chaque plan", "range les rushes par nom", "toute la séquence plus chaude",
                       "effet vintage sur tous les plans", "titre « Essai » au début"):
            avant = copy.deepcopy(p.d)
            acts = C.regles(phrase)
            if not acts:
                continue
            C.appliquer(acts, ed)
            p.annuler()
            self.assertEqual(p.d, avant, f"G5 : « {phrase} » ne se défait pas à l'identique d'un seul Annuler")
        p.modifie = False


class G6OrdreAlphabetique(unittest.TestCase):
    def test_listes(self):
        f, ed = _fenetre()
        mb = f.menuBar()
        fautes = []

        def trie(noms, ou):
            n = [_norm(x) for x in noms if x.strip()]
            if n != sorted(n):
                fautes.append(f"{ou} : {noms}")
        for top in ("Fabrique IA", "Montage"):
            a = next((x for x in mb.actions() if _norm(x.text()) == _norm(top)), None)
            if a is None:
                continue
            a.menu().aboutToShow.emit()
            sous = [x for x in a.menu().actions() if x.menu()]
            if top == "Montage":
                sous = [x for x in sous if _norm(x.text()) != "assistant"]
            trie([x.text() for x in sous], top)
            for x in sous:
                x.menu().aboutToShow.emit()
                trie([y.text() for y in x.menu().actions() if not y.isSeparator() and y.isEnabled() and not y.menu()
                      and "refaire" not in _norm(y.text())], f"{top} › {x.text()}")
        from app import guides as G
        trie([g["titre"] for g in G.guides()], "Guides")
        from app.dialogues_commande import RAPIDES
        trie([x[0] for x in RAPIDES], "Dites-le en clair › actions")
        self.assertEqual(fautes, [], "G6 : liste pas par ordre alphabétique : " + " | ".join(fautes))
        ed.projet.modifie = False


class G7RienDeTronque(unittest.TestCase):
    def test_fenetres(self):
        from verif_tronques import tronques
        f, ed = _fenetre()
        f.resize(1024, 740)
        f.show()
        c = ed.projet.clips_piste("video")[0]
        from app.preferences import DialoguePreferences
        from app.dialogues_commande import DialogueCommande
        from app.dialogues_guide import DialogueGuides
        from app.dialogues_separation import DialogueSeparation
        from app.dialogues_publication import DialoguePublier
        from app.dialogues_creatif import DialogueAtelierIA
        from app.dialogues_musique_ia import DialogueFabriqueMusique
        from app.dialogues_sequence import DialogueSequence
        from app.dialogues_vignette import DialogueVignette
        from app.dialogues_liaison import DialogueLiaison
        from app.dialogues_voix_suite import DialogueVoixSuite
        from app.dialogues_levres import DialogueLevres
        from app.dialogues_clip_groupe import DialogueClipGroupe
        from app.dialogues_narration import DialogueNarration
        c2 = ed.projet.clips_piste("video")[1]
        fen = [("PhilCut", f), ("Préférences", DialoguePreferences(f, f.params)), ("Dites-le", DialogueCommande(ed)),
               ("Guides", DialogueGuides(f)), ("Séparation", DialogueSeparation(ed, c)),
               ("Publier", DialoguePublier(f, ed.projet, f.params)), ("Atelier IA", DialogueAtelierIA(ed, "video")),
               ("Fabrique musique", DialogueFabriqueMusique(ed, f.params)), ("Séquence IA", DialogueSequence(ed, None)),
               ("Vignette", DialogueVignette(ed, None, "vignette")), ("Plan de liaison", DialogueLiaison(ed, c, c2)),
               ("Continuer avec ma voix", DialogueVoixSuite(ed, c)), ("Faire parler un plan", DialogueLevres(ed, c, "video")),
               ("Personnage qui parle", DialogueLevres(ed, None, "image")),
               ("Clip de groupe", DialogueClipGroupe(ed, None, os.path.join(os.environ["APPDATA"], "x.wav"))),
               ("Narration", DialogueNarration(ed))]
        fautes = []
        for nom, d in fen:
            d.show()
            for pb in tronques(d):
                fautes.append(f"{nom} : {pb[0]} « {pb[1][:50]} » {pb[2]}")
            if d is not f:
                d.close()
        self.assertEqual(fautes, [], "G7 : texte tronqué ou fenêtre trop grande : " + " | ".join(fautes))
        ed.projet.modifie = False


class G8ReglagesDansPreferences(unittest.TestCase):
    def test_cles(self):
        cles = set()
        for _p, s in _sources():
            cles.update(re.findall(r'params(?:\.get|\.setdefault)?[\[\(]\s*"([a-z_0-9]+)"', s))
        prefs = open(os.path.join(RACINE, "app", "preferences.py"), encoding="utf-8").read()
        connues = set(DETTE["G8_etat_interne"]["cles"]) | set(DETTE["G8_reglages_a_mettre_dans_preferences"])
        nouvelles = sorted(k for k in cles if f'"{k}"' not in prefs and k not in connues)
        self.assertEqual(nouvelles, [], "G8 : réglage absent des Préférences — ajoutez-le aux Préférences, ou, si c'est de la "
                                        "mémoire interne, classez-le dans garde_fous_dette.json (G8_etat_interne) : " + ", ".join(nouvelles))
        reglees = [k for k in DETTE["G8_reglages_a_mettre_dans_preferences"] if f'"{k}"' in prefs]
        self.assertEqual(reglees, [], "G8 : bravo, ces réglages sont maintenant dans les Préférences : retirez-les de la dette : "
                         + ", ".join(reglees))


class G9Progression(unittest.TestCase):
    def test_taches(self):
        fautes = []
        for p, s in _sources():
            if p == "app/taches.py" or not re.search(r"\bTache\(", s):
                continue
            ok = any(x in s for x in ("suivre(", "progression.connect", ".avancer(", "barre.setValue"))
            if not ok and p not in DETTE["G9_taches_sans_progression"]:
                fautes.append(p)
        self.assertEqual(fautes, [], "G9 : tâche de fond sans progression visible (encart.suivre, ou progression.connect) : "
                         + ", ".join(fautes))


class G10DossiersSysteme(unittest.TestCase):
    def test_fenetres_fichiers(self):
        dette = DETTE["G10_fenetres_fichiers_directes"]
        fautes = []
        for p, s in _sources():
            n = len(re.findall(r"QFileDialog\.get(?:Open|Save|Existing)", s))
            if n > dette.get(p, 0):
                fautes.append(f"{p} ({n} au lieu de {dette.get(p, 0)})")
        self.assertEqual(fautes, [], "G10 : fenêtre de fichiers directe — passez par widgets.ouvrir_fichier / enregistrer_fichier "
                                     "(dossier du système d'abord, puis le dernier utilisé) : " + ", ".join(fautes))


class G12Securite(unittest.TestCase):
    MOTIFS = [(r"AIza[0-9A-Za-z_\-]{30,}", "clef Google"), (r"sk-[A-Za-z0-9_\-]{24,}", "clef d'IA"),
              (r"sk-ant-[A-Za-z0-9_\-]{20,}", "clef Anthropic"), (r"gh[pousr]_[A-Za-z0-9]{30,}", "jeton GitHub"),
              (r"GOCSPX-[A-Za-z0-9_\-]{20,}", "secret Google OAuth"), (r"xox[baprs]-[A-Za-z0-9\-]{10,}", "jeton Slack")]

    def test_aucun_secret(self):
        fautes = []
        for d in ("app", "outils_dev", "docs", "tests", ".github"):
            for p in glob.glob(os.path.join(RACINE, d, "**", "*"), recursive=True):
                if not os.path.isfile(p) or os.path.getsize(p) > 2_000_000 or p.endswith((".png", ".jpg", ".ico", ".mp4", ".wav", ".gguf")):
                    continue
                try:
                    s = open(p, encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                for motif, nom in self.MOTIFS:
                    for m in re.finditer(motif, s):
                        if re.search(r"essai|exemple|faux|fausse|0123456789", m.group(0), re.I):
                            continue                                  # fausse clef des essais, annoncée comme telle
                        fautes.append(f"{os.path.relpath(p, RACINE)} ({nom})")
        self.assertEqual(fautes, [], "G12 : secret dans le dépôt — il doit aller dans le coffre du système ou les secrets GitHub : "
                         + ", ".join(fautes))

    def test_pas_de_navigateur_imite(self):
        fautes = [p for p, s in _sources() if re.search(r"Mozilla/5\.0|Chrome/\d+|Safari/\d+", s)]
        self.assertEqual(fautes, [], "G12 : User-Agent déguisé en navigateur (interdit) : " + ", ".join(fautes))


class G13FenetresDeProgression(unittest.TestCase):
    def test_pas_de_bouton_reduire_windows(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QWidget
        from app.dialogues_maj import DialogueMaj
        self.parent_ = QWidget()
        d = DialogueMaj(self.parent_, "v9", {})
        self.assertFalse(d.windowFlags() & Qt.WindowMinimizeButtonHint, "G13 : la fenêtre de mise à jour a le bouton réduire")
        self.assertTrue(hasattr(d, "b_reduire"), "G13 : la fenêtre de mise à jour n'a pas son bouton « Réduire »")


if __name__ == "__main__":
    unittest.main()
