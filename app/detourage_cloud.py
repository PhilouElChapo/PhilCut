"""Lever le fond de N'IMPORTE QUEL sujet par le cloud (0.9.84) : personne, animal, objet, avion… sans fond vert.

Annoncé le 15/11 (« comment enlever un fond qui n'est pas vert »). L'effet « Changer le fond (détourage) » gagne une méthode :
« IA de ce poste » (U²-Net, personnes, gratuit) ou « IA cloud, tout sujet » (Bria VRMBG 3.0 sur fal.ai, environ 0,05 $ la
seconde, prix montré et confirmé). Le passage du plan est envoyé une fois ; Bria rend une vidéo AVEC TRANSPARENCE (ProRes
4444) gardée sur ce poste ; à l'export, sa transparence sert de masque au plan (les effets et le cadrage du plan restent).
Un plan déjà préparé n'est jamais repayé (même passage du même fichier = même résultat)."""
import hashlib
import os

from . import catalogue_ia as CI
from .langue import _

POINT = "bria/video/background-removal/v3"
PRIX_S = 0.05


def prix(duree):
    return round(CI.prix("detourage_video", "s", PRIX_S) * max(1.0, float(duree)), 2)


def dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "detourages_cloud")
    os.makedirs(d, exist_ok=True)
    return d


def cle(clip, media):
    """Même fichier, même passage → même clef : rien n'est payé deux fois."""
    t = f"{os.path.abspath(media['chemin'])}|{os.path.getsize(media['chemin']) if os.path.exists(media['chemin']) else 0}|" \
        f"{float(clip.get('src_debut', 0)):.3f}|{float(clip.get('src_fin', 0)):.3f}"
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:16]


def fichier(clip, media):
    return os.path.join(dossier(), cle(clip, media) + ".mov")


def pret(clip, media):
    f = fichier(clip, media)
    return f if os.path.exists(f) and os.path.getsize(f) > 1000 else ""


def extraire(media, debut, duree, sortie):
    """Le passage du plan, sans le son, en 1080p au plus (ce que Bria lit le mieux, et moins lourd à envoyer)."""
    from . import moteur
    moteur.lancer(["-y", "-ss", f"{debut:.3f}", "-t", f"{duree:.3f}", "-i", media["chemin"], "-an",
                   "-vf", "scale='min(1920,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", sortie])
    if not os.path.exists(sortie):
        raise RuntimeError(_("Le passage du plan n'a pas pu être extrait."))
    return sortie


def fabriquer(params, clip, media, progression=None, arret=lambda: False):
    """Envoie le passage à Bria (fal.ai) et garde la vidéo transparente. Renvoie son chemin."""
    from . import generateurs_video as GV
    deja = pret(clip, media)
    if deja:
        return deja
    k = GV.clef(params, "fal")
    if not k:
        raise GV.ErreurGenerateur(_("Il faut une clef fal.ai (Préférences › Assistant et IA) pour lever le fond par le cloud."))
    debut = float(clip.get("src_debut", 0.0))
    duree = max(0.2, float(clip.get("src_fin", debut + 1)) - debut)
    sortie = fichier(clip, media)
    passage = sortie[:-4] + "_source.mp4"
    progression and progression(0.03, _("extraction du passage"))
    extraire(media, debut, duree, passage)
    progression and progression(0.1, _("envoi à fal.ai"))
    url = GV.televerser(k, passage)
    corps = {"video_url": url, "background_color": "Transparent", "output_container_and_codec": "mov_proresks", "preserve_audio": False}
    res = GV.demande_fal(k, CI.point("detourage_video", POINT), corps, (lambda f, t="": progression(0.15 + 0.75 * f, t or _("le cloud lève le fond"))) if progression
                         else None, arret, attente=900.0)
    video = (res or {}).get("video") or {}
    if not video.get("url"):
        raise GV.ErreurGenerateur(_("fal.ai n'a renvoyé aucune vidéo : {r}", r=str(res)[:200]))
    progression and progression(0.93, _("réception"))
    tmp = sortie[:-4] + ".part.mov"
    GV.telecharger(video["url"], tmp)
    os.replace(tmp, sortie)
    try:
        os.remove(passage)
    except OSError:
        pass
    return sortie


def filtre_masque(cadrage):
    """Le cadrage du plan appliqué à la vidéo transparente (bandes transparentes, jamais noires), puis la transparence en gris :
    c'est le masque que l'export pose sur le plan."""
    c = (cadrage or "").replace("color=black", "color=black@0")
    if "split[" in c:                        # « contenir, fond flou » : le sujet seul, contenu, le reste transparent
        c = ""
    return c
