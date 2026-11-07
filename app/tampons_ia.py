"""Tampons créés par l'IA (0.9.18) : de petites animations de 2 à 4 secondes, avec image dessinée par l'IA, mouvement,
texte qui claque, bruitages et une phrase dite avec un style de voix. Modèles préremplis (cartoon, science-fiction,
bande dessinée…), tout est modifiable ; le résultat rejoint la bibliothèque des tampons.

Image : IA locale (stable-diffusion.cpp, rien n'est envoyé) ou IA cloud (Gemini, votre clef, coût affiché avant).
Mouvement et texte : dessinés ici (QPainter). Sons : bruitages fabriqués ici, voix de synthèse Piper (locale).
"""
import math
import os
import random
import shutil
import tempfile

from .langue import _

# id : nom, consigne image (anglais), mouvement, bruitages, phrase dite, texte affiché, style de voix, durée
MODELES = {
    "decollage": (_("Décollage de fusée (cartoon)"), "cartoon rocket launching from a launch pad, flames and smoke, bright flat colors, blue sky",
                  "monte", ["montee", "boom"], _("Trois, deux, un… décollage !"), _("DÉCOLLAGE !"), "normale", 3.5),
    "boum_bd": (_("BOUM ! façon bande dessinée"), "comic book explosion burst, pop art, halftone dots, yellow red orange, no text",
                "choc", ["boom"], "", _("BOUM !"), "normale", 2.0),
    "ovni": (_("Soucoupe volante (science-fiction)"), "retro sci-fi flying saucer with a beam of light over a field at night, 1950s movie poster style",
             "flotte", ["laser", "montee"], _("Nous venons en paix."), "", "robot", 3.5),
    "robot": (_("Robot qui dit bonjour"), "cute retro tin robot waving hello, studio light, colorful background",
              "zoom", ["bip", "bip"], _("Bonjour, humain."), "", "robot", 3.0),
    "chat_surpris": (_("Chat surpris (cartoon)"), "cartoon cat with a very surprised face, huge eyes, simple background, flat illustration",
                     "choc", ["boing"], _("Quoi ?!"), "", "aigue", 2.0),
    "trophee": (_("Victoire, trophée"), "golden trophy with confetti and spotlights, celebration, vibrant",
                "zoom", ["tambour", "cymbale"], _("Bravo !"), _("VICTOIRE !"), "normale", 3.5),
    "jackpot": (_("Jackpot !"), "cartoon pile of gold coins and banknotes raining, casino lights, fun",
                "choc", ["caisse"], _("Jackpot !"), _("JACKPOT !"), "normale", 2.5),
    "eureka": (_("Eurêka, idée !"), "glowing light bulb idea above a cartoon head, bright background, flat illustration",
               "zoom", ["ding"], _("J'ai une idée !"), _("EURÊKA !"), "normale", 2.5),
    "hyperespace": (_("Saut dans l'hyperespace"), "stars stretching into light streaks, hyperspace jump, deep blue and white, cinematic",
                    "zoom", ["whoosh_inverse", "boom"], "", "", "normale", 2.5),
    "dodo": (_("Ennui, dodo"), "cartoon sleeping moon with nightcap among stars, soft pastel colors",
             "flotte", ["tic_tac"], _("Zzz… on s'ennuie…"), _("Zzz…"), "grave", 3.5),
    "plus_tard": (_("Quelques heures plus tard…"), "cartoon clock spinning fast, motion lines, warm colors",
                  "tourne", ["tic_tac", "whoosh"], _("Quelques heures plus tard…"), _("QUELQUES HEURES PLUS TARD…"), "grave", 3.0),
    "alerte": (_("Alerte !"), "red emergency siren light flashing, comic style, dramatic",
               "choc", ["buzzer", "buzzer"], _("Alerte, alerte !"), _("ALERTE !"), "robot", 2.5),
}

STYLES_VOIX = {"normale": _("Normale"), "robot": _("Robot"), "aigue": _("Petite voix aiguë (cartoon)"), "grave": _("Grosse voix grave"),
               "radio": _("Radio / talkie-walkie"), "echo": _("Écho (grande salle)")}
MOUVEMENTS = {"zoom": _("Zoom avant doux"), "choc": _("Choc (secousse et zoom rapide)"), "monte": _("Monte vers le haut"),
              "flotte": _("Flotte (léger balancement)"), "tourne": _("Tourne")}

_FILTRES_VOIX = {"normale": "", "robot": "afreqshift=shift=-120,aecho=0.8:0.6:12:0.5,aphaser=type=t:speed=2",
                 "aigue": "asetrate=22050*1.35,aresample=48000,atempo=0.75", "grave": "asetrate=22050*0.78,aresample=48000,atempo=1.28",
                 "radio": "highpass=f=500,lowpass=f=3000,acrusher=bits=8:mix=0.25", "echo": "aecho=0.8:0.7:60|120:0.4|0.25"}


def image(consigne, chemin, L, H, params, niveau="locale", progression=None, arret=lambda: False):
    """Image de l'animation, dessinée par l'IA (locale ou cloud)."""
    if niveau == "cloud":
        from . import ia
        donnees = ia.generer_image(params, consigne + ", no text, no watermark")
        with open(chemin, "wb") as f:
            f.write(donnees)
        return chemin
    from . import creatif as C
    k = 512 / max(L, H)
    return C.image(consigne + ", no text, no watermark", chemin, params=params, largeur=int(L * k), hauteur=int(H * k),
                   progression=progression, arret=arret)


def _images(img_chemin, texte, mouvement, duree, L, H, dossier, cadence=30, graine=0):
    """Images PNG de l'animation : l'image qui bouge, puis le texte qui claque."""
    from PySide6.QtCore import QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen
    src = QImage(img_chemin)
    if src.isNull():
        raise RuntimeError(_("Image illisible"))
    n = max(2, int(duree * cadence))
    rng = random.Random(graine)
    for i in range(n):
        t = i / (n - 1)
        q = QImage(L, H, QImage.Format_RGB32)
        q.fill(QColor("#000000"))
        p = QPainter(q)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setRenderHint(QPainter.Antialiasing)
        echelle, dx, dy, angle = 1.0, 0.0, 0.0, 0.0
        if mouvement == "zoom":
            echelle = 1.0 + 0.18 * t
        elif mouvement == "choc":
            echelle = 1.0 + 0.25 * (1 - math.exp(-8 * t))
            if t < 0.35:
                dx, dy = (rng.random() - 0.5) * 30 * (1 - t / 0.35), (rng.random() - 0.5) * 30 * (1 - t / 0.35)
        elif mouvement == "monte":
            echelle, dy = 1.25, H * 0.12 * (1 - t) - H * 0.12 * t
        elif mouvement == "flotte":
            echelle, dy, angle = 1.12, math.sin(t * math.pi * 2) * H * 0.02, math.sin(t * math.pi * 2) * 2
        elif mouvement == "tourne":
            echelle, angle = 1.45, t * 25
        cible_l = L * echelle
        cible_h = cible_l * src.height() / max(1, src.width())
        if cible_h < H * echelle:
            cible_h = H * echelle
            cible_l = cible_h * src.width() / max(1, src.height())
        p.translate(L / 2 + dx, H / 2 + dy)
        p.rotate(angle)
        p.drawImage(QRectF(-cible_l / 2, -cible_h / 2, cible_l, cible_h), src)
        p.resetTransform()
        if texte and t > 0.25:
            u = min(1.0, (t - 0.25) / 0.12)
            pop = 1.0 + 0.35 * math.sin(u * math.pi) if u < 1 else 1.0
            f = QFont("Anton")
            f.setPixelSize(int(H * 0.16))
            f.setBold(True)
            fm = QFontMetricsF(f)
            while fm.horizontalAdvance(texte) > L * 0.9 and f.pixelSize() > 20:
                f.setPixelSize(int(f.pixelSize() * 0.9))
                fm = QFontMetricsF(f)
            chemin = QPainterPath()
            chemin.addText(QPointF(-fm.horizontalAdvance(texte) / 2, fm.ascent() / 2 - fm.descent() / 2), f, texte)
            p.translate(L / 2, H * 0.78)
            p.scale(pop, pop)
            p.rotate(-4)
            p.setPen(QPen(QColor("#111111"), max(4, f.pixelSize() * 0.12), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(chemin)
            p.fillPath(chemin, QColor("#ffd60a"))
        p.end()
        q.save(os.path.join(dossier, f"{i:05d}.png"))
    return os.path.join(dossier, "%05d.png"), n


def _son(bruitages, phrase, style, duree, dossier, params):
    """Bande son : bruitages l'un après l'autre (le dernier au moment du texte), puis la phrase dite avec son style."""
    from . import bruitages as B, moteur
    entrees, filtres, k = [], [], 0
    moments = [0.0] + [duree * 0.25] * max(0, len(bruitages) - 1)
    for i, b in enumerate(bruitages):
        if b not in B.SONS:
            continue
        entrees += ["-i", B.chemin(b)]
        filtres.append(f"[{k}:a]adelay={int(moments[min(i, len(moments) - 1)] * 1000)}|{int(moments[min(i, len(moments) - 1)] * 1000)}[a{k}]")
        k += 1
    if phrase.strip():
        try:
            from . import voix
            w = os.path.join(dossier, "voix.wav")
            voix.lire(phrase, w, params)
            fv = _FILTRES_VOIX.get(style, "")
            entrees += ["-i", w]
            filtres.append(f"[{k}:a]{fv + ',' if fv else ''}aresample=48000,adelay=350|350,volume=1.6[a{k}]")
            k += 1
        except Exception:      # noqa: BLE001 : sans voix de synthèse installée, l'animation garde ses bruitages
            pass
    sortie = os.path.join(dossier, "son.wav")
    if not k:
        moteur.lancer(["-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={duree}", sortie])
        return sortie
    mix = ";".join(filtres) + ";" + "".join(f"[a{i}]" for i in range(k)) + f"amix=inputs={k}:normalize=0,atrim=0:{duree},apad=whole_dur={duree}"
    moteur.lancer(entrees + ["-filter_complex", mix, "-ac", "2", "-ar", "48000", sortie])
    return sortie


def creer(params, reglages, L=1280, H=720, niveau="locale", progression=None, arret=lambda: False):
    """reglages : {nom, consigne, mouvement, bruitages, phrase, texte, voix, duree}. Renvoie l'entrée de la bibliothèque."""
    from . import moteur, tampons as T

    def av(f, txt):
        if progression:
            progression(f, txt)
    d = tempfile.mkdtemp(prefix="philcut-tampon-ia-")
    try:
        duree = float(reglages.get("duree") or 3.0)
        av(0.02, _("Dessin de l'image par l'IA ({n})…", n=_("sur ce poste") if niveau == "locale" else _("IA cloud")))
        img = image(reglages["consigne"], os.path.join(d, "image.png"), L, H, params, niveau,
                    progression=lambda f, *_a: av(0.02 + 0.6 * f, _("Dessin de l'image par l'IA : {p} %", p=int(f * 100))), arret=arret)
        av(0.65, _("Animation et texte…"))
        motif, _n = _images(img, reglages.get("texte") or "", reglages.get("mouvement") or "zoom", duree, L, H, d)
        av(0.8, _("Bruitages et voix…"))
        son = _son(reglages.get("bruitages") or [], reglages.get("phrase") or "", reglages.get("voix") or "normale", duree, d, params)
        av(0.9, _("Assemblage du clip…"))
        clip = os.path.join(d, "tampon.mp4")
        moteur.lancer(["-framerate", "30", "-i", motif, "-i", son, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "160k", "-shortest", clip])
        e = T.ajouter_fichier(params, clip, reglages.get("nom") or _("Tampon IA"), [_("IA"), _("animation")])
        av(1.0, _("Tampon prêt."))
        return e
    finally:
        shutil.rmtree(d, ignore_errors=True)
