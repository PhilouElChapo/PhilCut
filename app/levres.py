"""Faire parler (ou chanter) un personnage sur un son déjà fait (0.9.65). Le son passe d'abord : le moteur reçoit VOTRE
son et fabrique les lèvres dessus. Deux façons :
- « image » : une image fixe du personnage + le son → une vidéo complète (lèvres, tête, expressions) ;
- « video » : un plan déjà fait (plan IA, vidéo) dont seule la bouche est refaite pour coller au son.

Le son est celui qui passe SOUS le plan dans la timeline (voix, musiques, aux mêmes instants), ou un fichier ; il peut
être isolé d'abord (voix seule) pour que les lèvres suivent mieux. Calcul : fal.ai (payant, coût annoncé et confirmé) ou,
depuis 0.9.92, sur ce poste (LatentSync 1.5, gratuit, carte NVIDIA de 8 Go, à installer dans Préférences › IA locale). Jamais une personnalité : un personnage fictif, son propre visage, ou celui
d'une personne d'accord (case qui engage l'auteur)."""
import os
import tempfile

from .langue import _

# moteurs : prix relevés le 14 novembre 2026 sur fal.ai, indicatifs
MOTEURS = {
    "latentsync": {"nom": "LatentSync (fal.ai)", "genre": "video", "modele": "fal-ai/latentsync",
                   "prix_fixe": 0.20, "seuil": 40.0, "prix_s": 0.005, "max_s": 600.0,
                   "explication": _("Refait seulement la bouche du plan. Le moins cher : 0,20 $ jusqu'à 40 s.")},
    "lipsync2": {"nom": "Sync lipsync-2 (fal.ai)", "genre": "video", "modele": "fal-ai/sync-lipsync/v2", "prix_s": 0.05, "max_s": 300.0,
                 "explication": _("Refait seulement la bouche du plan. Le plus précis : 3 $ la minute.")},
    # 0.9.92 : sur ce poste, gratuit (LatentSync 1.5 dans un Python portable, carte NVIDIA de 8 Go)
    "latentsync_local": {"nom": "LatentSync 1.5 sur ce poste (gratuit)", "genre": "video", "local": True, "prix_s": 0.0,
                         "max_s": 120.0,
                         "explication": _("Refait seulement la bouche du plan, sur votre carte NVIDIA (8 Go) : gratuit, environ "
                                          "une à deux minutes de calcul pour 10 s de vidéo. A installer une fois dans "
                                          "Préférences › IA locale (environ 6 Go).")},
    "omnihuman": {"nom": "OmniHuman 1.5 (fal.ai)", "genre": "image", "modele": "fal-ai/bytedance/omnihuman/v1.5", "prix_s": 0.16,
                  "max_s": 60.0, "max_1080": 30.0,
                  "explication": _("Anime une image : lèvres, tête, regard, gestes. 0,16 $ la seconde ; 30 s au plus en 1080p, "
                                   "60 s en 720p.")},
}


def moteur_ia(ident):
    """Le moteur, corrigé par le catalogue des IA (adresse, prix, remplaçant d'un service retiré)."""
    from . import catalogue_ia as CI
    m = dict(MOTEURS[ident])
    if m.get("local"):
        return m
    role = "levres_" + ident
    m["modele"] = CI.point(role, m["modele"])
    if "prix_fixe" in m:
        m["prix_fixe"] = CI.prix(role, "fixe", m["prix_fixe"])
        m["seuil"] = CI.prix(role, "seuil", m["seuil"])
    m["prix_s"] = CI.prix(role, "s", m["prix_s"])
    return m


def moteurs(genre):
    """Moteurs d'un genre (« image » ou « video »), par ordre alphabétique."""
    import unicodedata
    net = lambda t: unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return sorted(((k, m) for k, m in MOTEURS.items() if m["genre"] == genre), key=lambda km: net(km[1]["nom"]))


def prix(ident, duree):
    """Prix estimé en $ pour `duree` secondes."""
    m = moteur_ia(ident)
    if m.get("local"):
        return 0.0
    if "prix_fixe" in m:
        return round(m["prix_fixe"] + max(0.0, duree - m["seuil"]) * m["prix_s"], 2)
    return round(duree * m["prix_s"], 2)


def clef(params):
    from . import generateurs_video as GV
    return GV.clef(params, "fal")


# ------------------------------------------------------------------ le son sous un passage de la timeline
def sons_sous(projet, debut, fin, pistes=None):
    """Plans de son (et plans vidéo qui ont du son) qui passent entre debut et fin, non muets : [(clip, media)]."""
    from .projet import fin_clip
    pistes = pistes or (["voix"] + projet.pistes_audio())
    out = []
    for p in pistes:
        if projet.piste_muette(p):
            continue
        for c in projet.clips_piste(p):
            if c.get("muet") or c["debut"] >= fin or fin_clip(c) <= debut:
                continue
            m = projet.media(c["media"])
            if m and os.path.exists(m.get("chemin") or ""):
                out.append((c, m))
    return out


def extraire_son(projet, debut, fin, sortie, pistes=None):
    """Le son qui passe entre debut et fin (voix et musiques, à leur place et à leur volume), en WAV de la durée exacte du
    passage : ce que l'on entendra sous le plan. Lève une erreur s'il n'y a aucun son."""
    from . import moteur
    from .projet import fin_clip
    sons = sons_sous(projet, debut, fin, pistes)
    if not sons:
        raise RuntimeError(_("Aucun son sous ce passage : posez d'abord la voix (piste Voix) ou la musique dessous, ou choisissez un "
                             "fichier son."))
    duree = fin - debut
    args, filtres = ["-y", "-v", "error"], []
    for i, (c, m) in enumerate(sons):
        v = float(c.get("vitesse") or 1.0)
        a = max(debut, c["debut"])
        b = min(fin, fin_clip(c))
        src = c["src_debut"] + (a - c["debut"]) * v
        args += ["-ss", f"{src:.3f}", "-t", f"{(b - a) * v:.3f}", "-i", m["chemin"]]
        f = f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo"
        if abs(v - 1.0) > 0.01 and 0.5 <= v <= 2.0:
            f += f",atempo={v:.4f}"
        f += f",volume={float(c.get('volume', 1.0)):.3f},adelay={int((a - debut) * 1000)}|{int((a - debut) * 1000)}[s{i}]"
        filtres.append(f)
    n = len(sons)
    mix = "".join(f"[s{i}]" for i in range(n)) + (f"amix=inputs={n}:normalize=0" if n > 1 else "anull")
    filtres.append(f"{mix},apad,atrim=0:{duree:.3f}[out]")
    args += ["-filter_complex", ";".join(filtres), "-map", "[out]", "-ac", "2", "-ar", "48000", sortie]
    moteur.lancer(args)
    if not os.path.exists(sortie):
        raise RuntimeError(_("Le son du passage n'a pas pu être préparé."))
    return sortie


def extraire_plan(projet, clip, sortie):
    """La vidéo du plan (le passage utilisé, sans son), pour en refaire la bouche."""
    from . import moteur
    m = projet.media(clip["media"])
    v = float(clip.get("vitesse") or 1.0)
    d = (clip["src_fin"] - clip["src_debut"])
    args = ["-y", "-v", "error", "-ss", f"{clip['src_debut']:.3f}", "-t", f"{d:.3f}", "-i", m["chemin"], "-an"]
    if abs(v - 1.0) > 0.01:
        args += ["-vf", f"setpts=PTS/{v:.4f}"]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", sortie]
    moteur.lancer(args)
    return sortie


def isoler_voix(son, params, progression=None, arret=lambda: False):
    """Voix seule du son (séparation sur ce poste) : les lèvres suivent la voix, pas la batterie."""
    from . import moteur, separation as S
    d = float((moteur.sonder(son) or {}).get("duree") or 0)
    r = S.separer(son, tempfile.mkdtemp(prefix="philcut-levres-"), 0.0, d, params, progression=progression, arret=arret)
    return r["voix"]


# ------------------------------------------------------------------ fabrication (fal.ai)
def fabriquer(params, moteur_id, son, sortie, image=None, video=None, consigne="", resolution="720p", progression=None,
              arret=lambda: False):
    """Envoie le son et l'image (ou la vidéo) à fal.ai, attend, télécharge la vidéo ; renvoie le chemin."""
    from . import generateurs_video as GV, moteur
    m = moteur_ia(moteur_id)
    if m.get("local"):
        return fabriquer_local(params, son, video, sortie, progression, arret)
    cle = clef(params)
    if not cle:
        raise GV.ErreurGenerateur(_("Pas de clef fal.ai : Préférences › Assistant et IA, « Clef fal.ai » (ou « Connecter une IA »)."))
    duree = float((moteur.sonder(son) or {}).get("duree") or 0)
    if duree > m["max_s"]:
        raise GV.ErreurGenerateur(_("Son trop long pour {m} : {d} s au plus. Coupez le passage en plusieurs plans.", m=m["nom"],
                                    d=int(m["max_s"])))
    av = lambda f, t="": progression and progression(f, t)
    av(0.02, _("Envoi du son à fal.ai…"))
    corps = {"audio_url": GV.televerser(cle, son)}
    if m["genre"] == "image":
        av(0.06, _("Envoi de l'image…"))
        corps["image_url"] = GV.televerser(cle, image)
        if consigne:
            corps["prompt"] = consigne
        corps["resolution"] = "1080p" if resolution == "1080p" and duree <= m.get("max_1080", 30) else "720p"
    else:
        av(0.06, _("Envoi du plan…"))
        corps["video_url"] = GV.televerser(cle, video)
        if moteur_id == "lipsync2":
            corps["sync_mode"] = "cut_off"
        if moteur_id == "latentsync":
            corps["loop_mode"] = "loop"
    av(0.1, _("fal.ai calcule les lèvres…"))
    return GV.attendre_fal(cle, m["modele"], corps, sortie,
                           progression=lambda f: av(0.1 + 0.88 * f, _("fal.ai calcule les lèvres…")), arret=arret,
                           attente=max(120.0, duree * 20))


# ------------------------------------------------------------------ 0.9.92 : sur ce poste (LatentSync 1.5)
MODELE_LOCAL = "levres_local"


def local_pret():
    """Le moteur et ses modèles sont-ils installés ?"""
    from . import packs_ia as P
    return P.installe(MODELE_LOCAL) and P.moteur_installe("levres")


def local_manque():
    """Phrase qui dit ce qui manque pour calculer sur ce poste, ou "" (Windows et carte NVIDIA)."""
    from . import packs_ia as P
    import sys
    if sys.platform != "win32":
        return _("Les lèvres sur ce poste existent pour l'instant sous Windows seulement.")
    if not local_pret():
        return _("A installer une fois : Préférences › IA locale, « Lèvres synchronisées sur ce poste » (environ 6 Go).")
    carte = (P.carte_graphique() or "").lower() if hasattr(P, "carte_graphique") else ""
    if carte and "nvidia" not in carte and "geforce" not in carte and "rtx" not in carte:
        return _("Il faut une carte NVIDIA (8 Go) : celle de ce poste ne convient pas.")
    return ""


def commande_locale(params, son, video, sortie, etapes=20, guidance=1.5):
    """La ligne de commande du moteur (chemins des modèles installés)."""
    from . import packs_ia as P
    roles = (P.etat().get(MODELE_LOCAL) or {}).get("roles") or {}
    d = P.dossier_modele(MODELE_LOCAL)
    f = lambda r: os.path.join(d, roles.get(r, ""))
    exe = P.executable("levres")
    script = os.path.join(P.dossier_moteur("levres"), "philcut_levres.py")
    return [exe, script, "--video", video, "--audio", son, "--sortie", sortie, "--unet", f("unet"), "--whisper", f("whisper"),
            "--vae", d, "--visages", f("visages"), "--etapes", str(int(etapes)),
            "--guidance", f"{float(guidance):.2f}", "--deepcache"]


def lire_ligne(ligne):
    """« PHILCUT 0.250 texte » → (0.25, "texte") ; « PHILCUT_ERREUR texte » → (None, "texte") ; sinon None."""
    ligne = ligne.strip()
    if ligne.startswith("PHILCUT_ERREUR "):
        return None, ligne[len("PHILCUT_ERREUR "):]
    if ligne.startswith("PHILCUT "):
        morceaux = ligne.split(" ", 2)
        try:
            return float(morceaux[1]), (morceaux[2] if len(morceaux) > 2 else "")
        except ValueError:
            return None
    return None


def fabriquer_local(params, son, video, sortie, progression=None, arret=lambda: False, commande=None):
    """Refait la bouche de `video` sur `son` avec LatentSync 1.5 sur ce poste ; renvoie `sortie`. Le son est remis tel quel
    (le moteur le rééchantillonne) ; la vidéo est d'abord ramenée à 25 images/s, comme le moteur l'attend."""
    import subprocess
    from . import moteur
    from .journal import ecrire
    manque = local_manque() if commande is None else ""
    if manque:
        raise RuntimeError(manque)
    av = lambda f, t="": progression and progression(f, t)
    tmp = tempfile.mkdtemp(prefix="philcut-levres-")
    v25 = os.path.join(tmp, "plan25.mp4")
    moteur.lancer(["-y", "-v", "error", "-i", video, "-an", "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                   "-pix_fmt", "yuv420p", v25])
    s16 = os.path.join(tmp, "son.wav")
    moteur.lancer(["-y", "-v", "error", "-i", son, "-ac", "1", "-ar", "16000", s16])
    brut = os.path.join(tmp, "levres.mp4")
    cmd = commande(s16, v25, brut) if commande else commande_locale(params, s16, v25, brut)
    env = dict(os.environ)
    ff = os.path.dirname(moteur.ffmpeg()) if hasattr(moteur, "ffmpeg") else ""
    if ff:
        env["PATH"] = ff + os.pathsep + env.get("PATH", "")      # LatentSync appelle « ffmpeg » lui-même
    env["PYTHONUNBUFFERED"] = "1"
    av(0.01, _("Démarrage du calcul des lèvres sur ce poste…"))
    options = {}
    if os.name == "nt":
        options["creationflags"] = 0x08000000                  # pas de fenêtre noire
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                         env=env, cwd=os.path.dirname(cmd[1]) if len(cmd) > 1 else None, **options)
    message, fin = "", []
    try:
        for ligne in p.stdout:
            fin = (fin + [ligne.rstrip()])[-40:]
            if arret():
                p.kill()
                raise InterruptedError
            lu = lire_ligne(ligne)
            if lu is None:
                continue
            f, texte = lu
            if f is None:
                message = texte
            else:
                av(0.02 + 0.93 * f, texte)
        code = p.wait()
    finally:
        if p.poll() is None:
            p.kill()
    if code != 0 or not os.path.exists(brut):
        ecrire("levres", "LatentSync sur ce poste : " + " | ".join(fin[-12:]))
        raise RuntimeError(message or _("Le calcul des lèvres sur ce poste a échoué (voir le journal des plantages et "
                                        "erreurs)."))
    av(0.96, _("Finition…"))
    moteur.lancer(["-y", "-v", "error", "-i", brut, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
                   "-pix_fmt", "yuv420p", sortie])
    av(1.0, _("Terminé"))
    return sortie


def dossier_sorties():
    from .fabrique import dossier_plans
    return dossier_plans()


def recette(moteur_id, genre, image=None, consigne="", debut=None, fin=None, cout=None):
    return {"famille": "video", "intention": "levres", "outil": "levres", "moteur": moteur_id, "genre": genre,
            "image": image or "", "consigne": consigne, "debut": debut, "fin": fin, "paye": True, "cout_max": cout,
            "mention": "Video fabriquee par IA (levres synchronisees sur le son)"}

