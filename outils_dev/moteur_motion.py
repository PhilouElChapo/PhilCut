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


def _png_essai(chemin, L=360, H=240):
    """Un PNG transparent avec un « canon » rouge et gris (écrit à la main : zlib)."""
    import struct, zlib
    lignes = []
    for y in range(H):
        ligne = bytearray([0])
        for x in range(L):
            if 40 <= x < 320 and 60 <= y < 180:
                ligne += bytes((192, 48, 32, 255))
            elif 140 <= x < 220 and 20 <= y < 80:
                ligne += bytes((48, 48, 48, 255))
            else:
                ligne += bytes((0, 0, 0, 0))
        lignes.append(bytes(ligne))
    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(chemin, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", L, H, 8, 6, 0, 0, 0)) +
                bloc(b"IDAT", zlib.compress(b"".join(lignes))) + bloc(b"IEND", b""))


def _essais_medias():
    """1.1.16 : une image (PNG transparent) et un plan vidéo de vérification, fabriqués par FFmpeg."""
    import subprocess, tempfile
    d = os.path.join(tempfile.gettempdir(), "philcut_essais_medias")
    os.makedirs(d, exist_ok=True)
    img, img2, vid = os.path.join(d, "img_canon.png"), os.path.join(d, "photo.jpg"), os.path.join(d, "vid_boom.mp4")
    if not os.path.exists(img):
        _png_essai(img)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=800x600", "-frames:v", "1", img2],
                       check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "mandelbrot=s=640x360:r=30", "-t", "4",
                        "-pix_fmt", "yuv420p", vid], check=True)
    return img, img2, vid


def _anim(genre="chiffres", L=1920, H=1080):
    from app import motion as M
    if genre == "libre_pro":                        # 1.1.16 : dessin (IMG) et plan vidéo posé en mode écran
        from app import motion_libre as ML
        img, _img2, vid = _essais_medias()
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(racine, "tests", "exemples", "libre_canons.txt"), encoding="utf-8") as f:
            s = ML.sections(f.read())
        s["js"] += ('\nconst dessin = $("img", {position: "absolute", left: 390 * u + "px", top: 260 * u + "px", width: 300 * u + "px"});'
                    '\ndessin.src = IMG.canon; dessin.style.opacity = "0";\ntl.fromTo(dessin, {opacity: 1}, {opacity: 1, duration: 0.3}, 0.8);')
        s["videos"] = "boom 5.3 1.6 540 960 1000"
        a = ML.fiche("essai", (int(L), int(H)))
        a["libre"] = {"ressources": {"images": {"canon": {"chemin": img, "largeur": 360, "hauteur": 240, "en": "cannon"}},
                                     "videos": {"boom": {"chemin": vid, "duree": 4.0, "en": "explosion"}}}}
        return ML.appliquer(a, s)
    if genre == "titre_images":                     # 1.1.16 : animation simple avec deux images
        img, img2, _vid = _essais_medias()
        a = M.nouvelle("titre", taille=(int(L), int(H)))
        a.update(titre="Une soirée au bord du lac", sous_titre="Chapitre 2",
                 images=[{"chemin": img2, "place": "haut"}, {"chemin": img, "place": "coin"}])
        return a
    if genre == "libre_3d":                         # 1.3.1 : 3D de PhilCut (Three.js, physique Rapier, lueur, grain)
        from app import motion_libre as ML
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(racine, "tests", "exemples", "libre_3d.txt"), encoding="utf-8") as f:
            return ML.appliquer(ML.fiche("essai", (int(L), int(H))), ML.sections(f.read()))
    if genre == "libre_pixel":                      # 1.3.1 : effets pixel art (pixelfx)
        from app import motion_libre as ML
        s = {"titre": "Pixel", "duree": "5", "plan": "0-5 s: feu de camp, feu d'artifice, papillon", "css": "", "html": "",
             "js": 'PFX.effect("fire/campfire", {x: W * 0.25, y: H * 0.8, scale: 6});\n'
                   'PFX.effect("explosions/firework-burst", {x: W * 0.55, y: H * 0.45, scale: 5, start: 0.5});\n'
                   'PFX.effect("critters/butterfly", {x: W * 0.75, y: H * 0.7, scale: 6});\n'
                   'const t = $("div", {position: "absolute", left: 0, right: 0, top: 80 * u, textAlign: "center", fontSize: 90 * u, '
                   'color: "#fff", fontFamily: F.titre}, null, "Pixel");\ntl.fromTo(t, {opacity: 0}, {opacity: 1, duration: 0.5}, 0.3);'}
        return ML.appliquer(ML.fiche("essai", (int(L), int(H))), s)
    if genre in ("libre", "libre_leger", "libre_canons"):   # 1.1.0 : une composition écrite comme l'IA l'écrirait (tests/exemples)
        from app import motion_libre as ML
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        nom = "libre_canons.txt" if genre == "libre_canons" else "libre_anniversaire.txt"     # 1.1.14 : vrai cas de Philippe
        with open(os.path.join(racine, "tests", "exemples", nom), encoding="utf-8") as f:
            a = ML.appliquer(ML.fiche("essai", (int(L), int(H))), ML.sections(f.read()))
        return ML.apercu_leger(a) if genre == "libre_leger" else a      # 1.1.9 : l'aperçu léger, taille logique gardée
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
    a = _anim(genre, L, H)
    os.makedirs("public", exist_ok=True)
    a = dict(a, _html_calques=MH._copier_calques(a, "public", ""))      # 1.1.16 : images de l'animation simple
    m = MH.mise_en_page(a)
    m["cadence"] = 30
    m["polices"] = []
    json.dump({"A": m}, open(fichier, "w", encoding="utf-8"), ensure_ascii=False)
    return 0


def libre_remotion(projet, fichier, L=1920, H=1080):
    """1.1.2 : l'exemple d'animation libre écrit pour Remotion (tests/exemples) : LibreCode.tsx + fiche de la composition « Libre »."""
    from app import motion_libre as ML, motion_remotion as MR
    with open(os.path.join(RACINE, "tests", "exemples", "libre_anniversaire_remotion.tsx"), encoding="utf-8") as f:
        tsx = f.read()
    a = ML.fiche("essai", (int(L), int(H)), 9.5, moteur="remotion")
    a = ML.appliquer(a, {"tsx": tsx, "duree": "9.5", "plan": "0-4 s: cadeau\n4.2-7 s: feu\n7-9.5 s: confettis"})
    img, _img2, vid = _essais_medias()                 # 1.1.16 : dessin et plan vidéo posé en mode écran
    a["libre"]["ressources"] = {"images": {"canon": {"chemin": img}}, "videos": {"boom": {"chemin": vid, "duree": 4.0}}}
    a["libre"]["videos_poses"] = [{"id": "boom", "debut": 4.2, "duree": 2.0, "cx": int(L) / 2, "cy": int(H) / 2,
                                   "largeur": int(L) * 0.8}]
    fiche = MR.preparer_libre(a, projet)
    fiche["A"]["polices"] = []
    json.dump(fiche, open(fichier, "w", encoding="utf-8"), ensure_ascii=False)
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
    sys.exit({"composition": composition, "props": props, "catalogue": catalogue,
              "libre_remotion": libre_remotion}[a[0]](*a[1:]))
