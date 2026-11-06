"""IA créative locale (0.6 et 0.7) : tout tourne sur ce poste, rien n'est envoyé, rien n'est payé.

- images : stable-diffusion.cpp (sd-cli) — une phrase → une image, ou une image du film retouchée par une phrase ;
- vidéo : le même moteur avec Wan 2.2 (expérimental, long) ;
- musique : acestep.cpp (ace-lm puis ace-synth) — un style, une durée → un morceau ;
- agrandissement et ralenti : Real-ESRGAN et RIFE (ncnn, Vulkan) ;
- dessin animé et profondeur : modèles ONNX lus par onnxruntime (déjà dans PhilCut) ;
- sans modèle : un dessin animé « classique » par OpenCV, instantané, sur tous les postes.
La ligne de commande de chaque modèle vient du catalogue (« args ») : corrigeable sans nouvelle version de PhilCut.
"""
import json, os, random, re, shutil, subprocess, tempfile, time

from . import packs_ia as P
from .langue import _


class ErreurCreatif(Exception):
    pass


def modele_pour(genre, params=None):
    cle = P.modele_actif(genre, params)
    if not cle:
        raise ErreurCreatif(_("Aucun modèle « {g} » sur ce poste : cochez-en un dans Edition › Préférences › IA locale.",
                              g=P.GENRES.get(genre, genre)))
    return cle, (P.modeles(avec_essai=True).get(cle) or {}), P.etat().get(cle) or {}


def _fichier(cle, role):
    e = P.etat().get(cle) or {}
    nom = (e.get("roles") or {}).get(role)
    return os.path.join(P.dossier_modele(cle), nom) if nom else ""


def _moteur(genre_moteur, genre_gpu, params):
    if genre_gpu and P.moteur_installe(genre_gpu) and (params or {}).get("ia_gpu", True) is not False and P.carte_graphique():
        return genre_gpu
    if P.moteur_installe(genre_moteur):
        return genre_moteur
    if genre_gpu and P.moteur_installe(genre_gpu):
        return genre_gpu
    raise ErreurCreatif(_("Le moteur « {g} » n'est pas installé : cochez le modèle dans Préférences › IA locale.", g=genre_moteur))


def _remplir(gabarit, valeurs):
    out = []
    for a in gabarit:
        out.append(re.sub(r"\{(\w+)\}", lambda m: str(valeurs.get(m.group(1), m.group(0))), a))
    return out


def _lancer(genre, args, progression=None, arret=lambda: False, delai=3600, journal="creatif", exe=None):
    """Lance le programme du moteur ; suit « 3/20 » sur la sortie pour la progression."""
    exe = exe or P.executable(genre)
    cmd = [exe] + args
    proc = subprocess.Popen(cmd, cwd=P.dossier_moteur(genre), env=P._env(genre), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace", **P._options_processus())
    lignes = []
    t0 = time.time()
    try:
        for ligne in proc.stdout:
            lignes.append(ligne.rstrip())
            m = re.findall(r"(\d+)/(\d+)", ligne)
            if m and progression:
                a, b = map(int, m[-1])
                if 0 < b < 10000 and a <= b:
                    progression(a / b)
            if arret():
                proc.kill()
                raise InterruptedError()
            if time.time() - t0 > delai:
                proc.kill()
                raise ErreurCreatif(_("Trop long : arrêté après {m} min.", m=delai // 60))
        proc.wait()
    finally:
        try:
            with open(os.path.join(P.dossier(), f"journal_{journal}.txt"), "w", encoding="utf-8") as f:
                f.write(" ".join(cmd) + "\n\n" + "\n".join(lignes[-400:]))
        except OSError:
            pass
    if proc.returncode != 0:
        fin = "\n".join(l for l in lignes[-12:] if l.strip())
        raise ErreurCreatif(_("Le moteur s'est arrêté (code {c}) : {f}", c=proc.returncode, f=fin[-600:]))
    return lignes


# ------------------------------------------------------------------ images (stable-diffusion.cpp)
def image(prompt, sortie, params=None, negatif="", largeur=None, hauteur=None, init=None, force=0.55, graine=-1, cle=None,
          progression=None, arret=lambda: False):
    """Une image PNG : à partir d'une phrase, ou d'une image (init) retouchée par la phrase (force 0 = intacte, 1 = refaite)."""
    if cle:
        m, e = P.modeles(avec_essai=True).get(cle) or {}, P.etat().get(cle) or {}
    else:
        cle, m, e = modele_pour("image", params)
    genre = _moteur(m.get("moteur", "image"), m.get("moteur_gpu"), params)
    px = int(m.get("taille_px", 512))
    if init and (largeur is None or hauteur is None):
        from PySide6.QtGui import QImage
        q = QImage(init)
        if not q.isNull():
            k = px / max(q.width(), q.height())
            largeur, hauteur = q.width() * k, q.height() * k
    largeur = int(max(256, round((largeur or px) / 64) * 64))
    hauteur = int(max(256, round((hauteur or px) / 64) * 64))
    if init:                                         # le moteur veut une image à la taille demandée
        import cv2
        img = cv2.imread(init)
        if img is None:
            raise ErreurCreatif(_("Image illisible : {c}", c=init))
        tmp = os.path.join(tempfile.mkdtemp(prefix="philcut-sd-"), "init.png")
        cv2.imwrite(tmp, cv2.resize(img, (largeur, hauteur), interpolation=cv2.INTER_AREA))
        init = tmp
    valeurs = {"modele": _fichier(cle, "modele"), "vae": _fichier(cle, "vae"), "t5xxl": _fichier(cle, "t5xxl"), "prompt": prompt,
               "negatif": negatif or "blurry, low quality, deformed, watermark, text", "largeur": largeur, "hauteur": hauteur,
               "etapes": m.get("etapes", 4), "cfg": m.get("cfg", 1.0), "graine": graine if graine >= 0 else random.randint(1, 2 ** 31 - 1),
               "coeurs": P.coeurs(params), "sortie": sortie, "image": init or "", "force": f"{max(0.05, min(1.0, force)):.2f}"}
    args = _remplir(m.get("args") or [], valeurs) + (_remplir(m.get("args_init") or [], valeurs) if init else [])
    if not args:
        raise ErreurCreatif(_("Catalogue sans ligne de commande pour ce modèle : mettez à jour l'IA locale."))
    _lancer(genre, args, progression, arret, journal="image")
    if not os.path.exists(sortie):
        raise ErreurCreatif(_("Le moteur n'a pas produit d'image."))
    return sortie


def video(prompt, sortie, params=None, init=None, secondes=2.0, largeur=480, hauteur=272, progression=None, arret=lambda: False):
    """Quelques secondes de vidéo (Wan 2.2) à partir d'une image et d'une phrase ; MP4 en sortie."""
    from . import moteur
    cle, m, e = modele_pour("video", params)
    genre = _moteur(m.get("moteur", "image"), m.get("moteur_gpu"), params)
    images = int(max(9, min(81, round(secondes * 16) // 4 * 4 + 1)))
    brut = os.path.join(tempfile.mkdtemp(prefix="philcut-wan-"), "video.webm")
    init_redim = None
    if init:
        import cv2
        img = cv2.imread(init)
        init_redim = os.path.join(os.path.dirname(brut), "init.png")
        cv2.imwrite(init_redim, cv2.resize(img, (int(largeur) // 16 * 16, int(hauteur) // 16 * 16), interpolation=cv2.INTER_AREA))
    valeurs = {"modele": _fichier(cle, "modele"), "vae": _fichier(cle, "vae"), "t5xxl": _fichier(cle, "t5xxl"), "prompt": prompt,
               "negatif": "static, blurry, low quality, deformed, watermark, text", "largeur": int(largeur) // 16 * 16,
               "hauteur": int(hauteur) // 16 * 16, "images": images, "etapes": m.get("etapes", 20), "graine": random.randint(1, 2 ** 31 - 1),
               "coeurs": P.coeurs(params), "sortie": brut, "image": init_redim or ""}
    args = _remplir(m.get("args") or [], valeurs) + (_remplir(m.get("args_init") or [], valeurs) if init_redim else [])
    _lancer(genre, args, progression, arret, delai=4 * 3600, journal="video")
    if not os.path.exists(brut):
        raise ErreurCreatif(_("Le moteur n'a pas produit de vidéo."))
    moteur.lancer(["-y", "-i", brut, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24", sortie])
    return sortie


# ------------------------------------------------------------------ musique (acestep.cpp)
STYLES_MUSIQUE = [
    ("pop_aerienne", _("Pop aérienne"), "airy uplifting pop, bright synths, soft drums, positive, travel vlog"),
    ("cinema", _("Cinématique épique"), "epic cinematic orchestral, strings, big drums, inspiring, film trailer"),
    ("lofi", _("Lo-fi calme"), "lofi hip hop, chill, mellow piano, vinyl crackle, relaxed"),
    ("electro", _("Electro énergique"), "energetic electronic dance, punchy kick, synth bass, festival"),
    ("acoustique", _("Acoustique guitare"), "warm acoustic guitar, folk, light percussion, sunny"),
    ("piano", _("Piano doux"), "gentle solo piano, emotional, calm, ambient"),
    ("rock", _("Rock dynamique"), "driving rock, electric guitars, powerful drums, adventure"),
    ("ambient", _("Ambiance planante"), "ambient soundscape, pads, slow evolving, atmospheric"),
]


def musique(style, sortie, duree=60.0, params=None, instrumental=True, paroles="", langue="fr", bpm=0, progression=None, arret=lambda: False):
    """Un morceau (MP3) d'environ `duree` secondes dans le style donné (phrase libre ou clef de STYLES_MUSIQUE)."""
    cle, m, e = modele_pour("musique", params)
    genre = _moteur("musique", m.get("moteur_gpu", "musique_gpu"), params)
    caption = dict((k, c) for k, _n, c in STYLES_MUSIQUE).get(style, style)
    d = tempfile.mkdtemp(prefix="philcut-ace-")
    roles = e.get("roles") or {}
    req = {"caption": caption, "lyrics": "[Instrumental]" if instrumental or not paroles.strip() else paroles.strip(),
           "duration": float(max(10.0, min(240.0, duree))), "bpm": int(bpm or 0), "keyscale": "", "timesignature": "4",
           "vocal_language": "unknown" if instrumental else (langue or "fr"), "seed": random.randint(1, 2 ** 31 - 1),
           "inference_steps": 8, "lm_model": roles.get("lm", ""), "synth_model": roles.get("dit", ""), "output_format": "mp3"}
    if not req["bpm"]:
        req["bpm"] = {"lofi": 80, "piano": 72, "ambient": 70, "cinema": 90, "acoustique": 100, "pop_aerienne": 112, "rock": 128, "electro": 126}.get(style, 100)
    if not req["keyscale"]:
        req["keyscale"] = "C major"
    chemin = os.path.join(d, "demande.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(req, f, ensure_ascii=False)
    modeles_dir = P.dossier_modele(cle)
    exe_lm = os.path.join(P.dossier_moteur(genre), P._exe("ace-lm"))
    if not os.path.exists(exe_lm):
        raise ErreurCreatif(_("Moteur de musique incomplet (ace-lm manquant)."))
    p1 = (lambda f: progression(0.45 * f)) if progression else None
    p2 = (lambda f: progression(0.45 + 0.55 * f)) if progression else None
    _lancer(genre, ["--models", modeles_dir, "--request", chemin], p1, arret, journal="musique_lm", exe=exe_lm)
    suite = os.path.join(d, "demande0.json")
    if not os.path.exists(suite):
        raise ErreurCreatif(_("La première étape de la musique n'a rien produit."))
    _lancer(genre, ["--models", modeles_dir, "--request", suite], p2, arret, journal="musique")
    sons = [f for f in os.listdir(d) if f.lower().endswith((".mp3", ".wav"))]
    if not sons:
        raise ErreurCreatif(_("Le moteur n'a pas produit de son."))
    shutil.move(os.path.join(d, sorted(sons)[0]), sortie)
    return sortie


# ------------------------------------------------------------------ agrandissement et ralenti (ncnn)
def _images_video(video, dossier, debut=0.0, duree=None, ips=None):
    from . import moteur
    os.makedirs(dossier, exist_ok=True)
    args = ["-y", "-ss", f"{debut:.3f}", "-i", video]
    if duree:
        args += ["-t", f"{duree:.3f}"]
    if ips:
        args += ["-r", str(ips)]
    moteur.lancer(args + [os.path.join(dossier, "%06d.png")])
    return len([f for f in os.listdir(dossier) if f.endswith(".png")])


def agrandir(video, sortie, facteur=2, debut=0.0, duree=None, ips=30, params=None, progression=None, arret=lambda: False, anime=False):
    from . import moteur
    if not P.moteur_installe("upscale"):
        raise ErreurCreatif(_("Agrandissement IA non installé : cochez-le dans Préférences › IA locale."))
    d = tempfile.mkdtemp(prefix="philcut-up-")
    n = _images_video(video, os.path.join(d, "in"), debut, duree, ips)
    os.makedirs(os.path.join(d, "out"))
    nom = "realesr-animevideov3" if anime else "realesrgan-x4plus"
    args = ["-i", os.path.join(d, "in"), "-o", os.path.join(d, "out"), "-n", nom, "-s", str(int(facteur) if anime else 4), "-f", "png"]
    _lancer("upscale", args, progression, arret, journal="agrandissement")
    if not anime and facteur != 4:
        moteur.lancer(["-y", "-framerate", str(ips), "-i", os.path.join(d, "out", "%06d.png"), "-vf", f"scale=iw*{facteur}/4:ih*{facteur}/4:flags=lanczos",
                       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", sortie])
    else:
        moteur.lancer(["-y", "-framerate", str(ips), "-i", os.path.join(d, "out", "%06d.png"), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", sortie])
    shutil.rmtree(d, ignore_errors=True)
    return sortie, n


def ralentir(video, sortie, facteur=4, debut=0.0, duree=None, ips=30, params=None, progression=None, arret=lambda: False):
    """Ralenti fluide : RIFE invente les images intermédiaires (×2, ×4, ×8), sortie à la même cadence."""
    from . import moteur
    if not P.moteur_installe("interpolation"):
        raise ErreurCreatif(_("Ralenti fluide IA non installé : cochez-le dans Préférences › IA locale."))
    d = tempfile.mkdtemp(prefix="philcut-rife-")
    n = _images_video(video, os.path.join(d, "in"), debut, duree, ips)
    os.makedirs(os.path.join(d, "out"))
    _lancer("interpolation", ["-i", os.path.join(d, "in"), "-o", os.path.join(d, "out"), "-n", str(n * int(facteur)), "-m", "rife-v4.6", "-f", "%06d.png"],
            progression, arret, journal="ralenti")
    moteur.lancer(["-y", "-framerate", str(ips), "-i", os.path.join(d, "out", "%06d.png"), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", sortie])
    shutil.rmtree(d, ignore_errors=True)
    return sortie


# ------------------------------------------------------------------ ONNX : dessin animé, profondeur
_sessions = {}


def _session(cle, params=None):
    if cle in _sessions:
        return _sessions[cle]
    import onnxruntime as ort
    o = ort.SessionOptions()
    o.intra_op_num_threads = P.coeurs(params)
    fournisseurs = [x for x in ("DmlExecutionProvider", "CUDAExecutionProvider") if x in ort.get_available_providers()] + ["CPUExecutionProvider"]
    s = ort.InferenceSession(_fichier(cle, "modele"), o, providers=fournisseurs)
    _sessions[cle] = s
    return s


def anime_image(img_bgr, cle=None, params=None):
    """Une image (BGR) passée en dessin animé : modèle AnimeGANv3 s'il est là, sinon stylisation OpenCV."""
    import cv2
    import numpy as np
    if cle is None:
        cle = P.modele_actif("anime", params)
    if not cle or not P.installe(cle) or not P.onnx_present():
        return dessin_classique(img_bgr)
    s = _session(cle, params)
    H, L = img_bgr.shape[:2]
    k = 512 / max(H, L)
    h8, l8 = max(32, int(H * k) // 32 * 32), max(32, int(L * k) // 32 * 32)
    x = cv2.cvtColor(cv2.resize(img_bgr, (l8, h8), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 127.5 - 1.0
    entree = s.get_inputs()[0]
    if len(entree.shape) == 4 and entree.shape[1] == 3:        # NCHW
        y = s.run(None, {entree.name: x.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
    else:                                                        # NHWC
        y = s.run(None, {entree.name: x[None]})[0][0]
    y = ((np.clip(y, -1, 1) + 1) * 127.5).astype(np.uint8)
    return cv2.resize(cv2.cvtColor(y, cv2.COLOR_RGB2BGR), (L, H), interpolation=cv2.INTER_CUBIC)


def dessin_classique(img_bgr):
    """Dessin animé sans modèle : couleurs aplaties (filtre bilatéral, quantification) et contours encrés."""
    import cv2
    import numpy as np
    petit = cv2.resize(img_bgr, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    for _i in range(4):
        petit = cv2.bilateralFilter(petit, 9, 40, 9)
    couleur = cv2.resize(petit, (img_bgr.shape[1], img_bgr.shape[0]), interpolation=cv2.INTER_LINEAR)
    couleur = (couleur // 24 * 24 + 12).astype(np.uint8)
    gris = cv2.medianBlur(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY), 7)
    bords = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 4)
    return cv2.bitwise_and(couleur, couleur, mask=bords)


def profondeur(img_bgr, cle=None, params=None):
    """Carte de profondeur 0..1 (1 = proche) ; sans modèle, une estimation grossière (bas de l'image plus proche)."""
    import cv2
    import numpy as np
    H, L = img_bgr.shape[:2]
    cle = cle or P.modele_actif("profondeur", params)
    if not cle or not P.installe(cle) or not P.onnx_present():
        g = np.linspace(0.2, 1.0, H, dtype=np.float32)[:, None].repeat(L, 1)
        return cv2.GaussianBlur(g, (0, 0), 5)
    s = _session(cle, params)
    x = cv2.cvtColor(cv2.resize(img_bgr, (518, 518), interpolation=cv2.INTER_CUBIC), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = (x - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    y = s.run(None, {s.get_inputs()[0].name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0]
    y = np.squeeze(y).astype(np.float32)
    y = (y - y.min()) / max(1e-6, float(y.max() - y.min()))
    return cv2.resize(y, (L, H), interpolation=cv2.INTER_CUBIC)


def photo_3d(img_bgr, sortie, secondes=3.0, ips=30, mouvement="avance", amplitude=0.06, params=None, progression=None):
    """Photo 3D : la caméra avance (ou glisse) dans l'image grâce à la carte de profondeur ; MP4 en sortie."""
    import cv2
    import numpy as np
    from . import moteur
    H, L = img_bgr.shape[:2]
    if max(H, L) > 1280:
        k = 1280 / max(H, L)
        img_bgr = cv2.resize(img_bgr, (int(L * k) // 2 * 2, int(H * k) // 2 * 2), interpolation=cv2.INTER_AREA)
        H, L = img_bgr.shape[:2]
    prof = profondeur(img_bgr, params=params)
    prof = cv2.GaussianBlur(prof, (0, 0), 3)
    yy, xx = np.mgrid[0:H, 0:L].astype(np.float32)
    cx, cy = L / 2, H / 2
    d = tempfile.mkdtemp(prefix="philcut-3d-")
    n = max(2, int(secondes * ips))
    for i in range(n):
        t = i / (n - 1)
        e = t * t * (3 - 2 * t)
        if mouvement == "glisse":
            dx = (e - 0.5) * amplitude * L * prof
            mx, my = xx + dx, yy
            zoom = 1.06
        else:
            s = 1 + amplitude * 1.6 * e * (0.35 + prof)                 # le proche grossit plus vite que le lointain
            mx, my = cx + (xx - cx) / s, cy + (yy - cy) / s
            zoom = 1.02
        img = cv2.remap(img_bgr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img = cv2.resize(img, None, fx=zoom, fy=zoom)[int((H * zoom - H) / 2):int((H * zoom - H) / 2) + H, int((L * zoom - L) / 2):int((L * zoom - L) / 2) + L]
        cv2.imwrite(os.path.join(d, f"{i:05d}.png"), img)
        progression and progression(0.9 * (i + 1) / n)
    moteur.lancer(["-y", "-framerate", str(ips), "-i", os.path.join(d, "%05d.png"), "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
                   "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", sortie])
    shutil.rmtree(d, ignore_errors=True)
    return sortie


def transition_3d(img_a, img_b, sortie, duree=1.2, ips=30, params=None, progression=None):
    """Transition « IA » locale entre deux plans : la caméra plonge dans la dernière image du plan qui part (grâce à sa
    profondeur), un fondu rapide, puis elle recule hors de la première image du plan qui arrive."""
    from . import moteur
    import cv2
    H, L = img_a.shape[:2]
    img_b = cv2.resize(img_b, (L, H), interpolation=cv2.INTER_AREA)
    d = tempfile.mkdtemp(prefix="philcut-tr3d-")
    moitie = duree / 2 + 0.15
    a = photo_3d(img_a, os.path.join(d, "a.mp4"), moitie, ips, "avance", 0.28, params, (lambda f: progression(0.45 * f)) if progression else None)
    b = photo_3d(img_b, os.path.join(d, "b.mp4"), moitie, ips, "avance", 0.28, params, (lambda f: progression(0.45 + 0.45 * f)) if progression else None)
    moteur.lancer(["-y", "-i", a, "-i", b, "-filter_complex",
                   f"[1:v]reverse,setpts=PTS-STARTPTS[br];[0:v][br]xfade=transition=fade:duration=0.3:offset={moitie - 0.3:.3f},"
                   f"avgblur=sizeX=9:sizeY=9:enable='between(t,{moitie - 0.35:.3f},{moitie + 0.05:.3f})'[v]",
                   "-map", "[v]", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", sortie])
    shutil.rmtree(d, ignore_errors=True)
    return sortie


def traiter_video(video, sortie, fonction, debut=0.0, duree=None, ips=30, progression=None, arret=lambda: False):
    """Applique fonction(img_bgr) -> img_bgr à chaque image d'un passage ; garde le son d'origine."""
    from . import moteur
    import cv2
    d = tempfile.mkdtemp(prefix="philcut-fx-")
    n = _images_video(video, os.path.join(d, "in"), debut, duree, ips)
    os.makedirs(os.path.join(d, "out"))
    for i, f in enumerate(sorted(os.listdir(os.path.join(d, "in")))):
        if arret():
            raise InterruptedError()
        img = cv2.imread(os.path.join(d, "in", f))
        cv2.imwrite(os.path.join(d, "out", f), fonction(img))
        progression and progression(0.9 * (i + 1) / max(1, n))
    args = ["-y", "-framerate", str(ips), "-i", os.path.join(d, "out", "%06d.png"), "-ss", f"{debut:.3f}"]
    args += ["-t", f"{duree:.3f}"] if duree else []
    args += ["-i", video, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", sortie]
    moteur.lancer(args)
    shutil.rmtree(d, ignore_errors=True)
    return sortie


def flou_arriere_plan(img_bgr, force=12, params=None):
    """Arrière-plan flouté selon la profondeur (effet portrait), le proche reste net."""
    import cv2
    import numpy as np
    p = profondeur(img_bgr, params=params)
    flou = cv2.GaussianBlur(img_bgr, (0, 0), force)
    m = np.clip((p - 0.45) / 0.25, 0, 1)[..., None]
    return (img_bgr * m + flou * (1 - m)).astype(np.uint8)
