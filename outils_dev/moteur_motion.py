"""Moteur « motion » (0.9.99) : Node portable + HyperFrames + GSAP + Chrome sans fenêtre, et le projet Remotion de PhilCut
sans ses bibliothèques (Remotion s'installe depuis npm chez l'utilisateur, après sa confirmation de licence).

  python outils_dev/moteur_motion.py composition sortie_dossier [genre] [L] [H]   -> projet HyperFrames d'essai (vérification)
  python outils_dev/moteur_motion.py props fichier.json [genre]                     -> fiche d'essai pour Remotion
  python outils_dev/moteur_motion.py catalogue dist                                 -> moteur « motion » et modèle « motion_html »
                                                                                       ajoutés à dist/moteurs-creatifs.json
"""
import json, os, sys, time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("PHILCUT_LANGUE", "fr")
RELEASE = "https://github.com/PhilouElChapo/PhilCut/releases/download/moteurs-ia/"
NOMS = {"windows": "philcut-motion-windows-x64.zip", "linux": "philcut-motion-linux-x64.tar.gz"}


def _anim(genre="chiffres", L=1920, H=1080):
    from app import motion as M
    if genre == "libre":                          # 1.1.0 : une composition écrite comme l'IA l'écrirait (tests/donnees)
        from app import motion_libre as ML
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(racine, "tests", "donnees", "libre_anniversaire.txt"), encoding="utf-8") as f:
            return ML.appliquer(ML.fiche("essai", (int(L), int(H))), ML.sections(f.read()))
    a = M.nouvelle(genre, taille=(int(L), int(H)))
    a["source"] = "Exemple neutre"
    if genre == "titre":
        a.update(titre="Une soirée au bord du lac", sous_titre="Chapitre 2")
    if genre in M.HABILLAGE or genre == "defilement" or genre not in ("chiffres", "compteur", "barres", "courbe", "titre"):
        M.preparer_genre(a, genre)
        a["transparent"] = False                 # vérification : sur le fond, pour voir
    if genre == "sous_titres":
        mots = "Aujourd'hui on parle de motion design pour vos vidéos et de la façon de caler chaque mot sur la voix".split()
        a["mots"] = [[round(0.3 + k * 0.32, 2), round(0.3 + k * 0.32 + 0.28, 2), w] for k, w in enumerate(mots)]
        a["duree"], a["style_st"] = 7.0, "surligne"
    if genre == "progression":
        a.update(duree=8.0, chapitres=[[0, "Intro"], [3, "Les chiffres"], [6, "La suite"]])
    return a


def composition(dossier, genre="chiffres", L=1920, H=1080):
    from app import motion_html as MH
    MH.preparer_projet(_anim(genre, L, H), dossier, gsap_en_ligne=True)
    print("::notice::projet", dossier)
    return 0


def props(fichier, genre="chiffres", L=1920, H=1080):
    from app import motion_html as MH
    m = MH.mise_en_page(_anim(genre, L, H))
    m["cadence"] = 30
    m["polices"] = []
    json.dump({"A": m}, open(fichier, "w", encoding="utf-8"), ensure_ascii=False)
    return 0


def catalogue(dossier):
    from moteurs_ia import empreinte
    p = os.path.join(dossier, "moteurs-creatifs.json")
    man = json.load(open(p, encoding="utf-8"))
    m = man["moteurs"].setdefault("motion", {})
    version = open(os.path.join(dossier, "version-motion.txt"), encoding="utf-8").read().strip() \
        if os.path.exists(os.path.join(dossier, "version-motion.txt")) else time.strftime("%Y-%m-%d")
    m.update({"nom": "Animations HTML (Node, HyperFrames, GSAP, Chrome sans fenêtre)", "version": version,
              "licence": "HyperFrames Apache 2.0 ; GSAP licence standard gratuite ; Chrome for Testing (Google) ; Node.js MIT"})
    trouve = False
    for systeme, nom in NOMS.items():
        f = os.path.join(dossier, nom)
        if os.path.exists(f):
            trouve = True
            m[systeme] = {"fichier": nom, "url": RELEASE + nom, "taille": os.path.getsize(f), "sha256": empreinte(f)}
    if not trouve:
        print("::error::aucune archive du moteur motion")
        return 1
    man.setdefault("modeles", {})["motion_html"] = {
        "genre": "motion", "nom": "Animations HyperFrames et Remotion sur ce poste", "moteur": "motion", "qualite": 4,
        "memoire_go": 2, "essai": False, "fichiers": [], "taille": 0, "version": version,
        "source": "heygen-com/hyperframes, gsap, chrome-headless-shell ; Remotion installé à part depuis npm",
        "note": "Rend les animations (chiffres, graphiques, titres, sous-titres animés) en HTML : HyperFrames (gratuit, libre) ; "
                "Remotion s'installe à part, après confirmation de votre droit à sa licence gratuite."}
    man["date"] = time.strftime("%Y-%m-%d")
    json.dump(man, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(man["moteurs"]["motion"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(1)
    sys.exit({"composition": composition, "props": props, "catalogue": catalogue}[a[0]](*a[1:]))
