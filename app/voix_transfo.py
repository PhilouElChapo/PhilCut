"""Transformer une voix (0.9.75) : plus grave, plus aiguë, plus masculine ou féminine, enfant…

- Sur ce poste (gratuit) : hauteur et timbre réglés par filtres (export.filtre_transfo), posés sur le plan comme une
  retouche : rien n'est recalculé, tout se règle et s'écoute.
- IA cloud (plus naturel) : la voix du plan est redite par une voix toute faite (voix inventées d'ElevenLabs, par
  fal.ai), avec le même débit, les mêmes intonations ; le résultat est un nouveau fichier posé sur la piste Voix, le son
  d'origine du plan coupé. Jamais la voix d'une personne réelle : seulement des voix de synthèse du catalogue.
"""
import os
import time

from . import catalogue_ia as CI
from .langue import _

PRESETS = {"neutre": (_("Sans transformation"), 0.0, 1.0), "masculine": (_("Plus masculine"), -3.0, 0.88),
           "feminine": (_("Plus féminine"), 4.0, 1.13), "enfant": (_("Voix d'enfant"), 7.0, 1.22),
           "narrateur": (_("Narrateur posé (plus grave)"), -2.0, 0.95), "grosse": (_("Grosse voix"), -6.0, 0.82),
           "petite": (_("Petite voix (dessin animé)"), 6.0, 1.18)}

MODELE_CLOUD = "fal-ai/elevenlabs/voice-changer"
PRIX_MINUTE = 0.30
# voix toutes faites du catalogue ElevenLabs (inventées) : nom affiché, nom demandé
VOIX_CLOUD = [(_("Femme : douce (Sarah)"), "Sarah"), (_("Femme : posée (Laura)"), "Laura"), (_("Femme : claire (Charlotte)"), "Charlotte"),
              (_("Femme : chaleureuse (Alice)"), "Alice"), (_("Homme : grave (George)"), "George"), (_("Homme : narrateur (Brian)"), "Brian"),
              (_("Homme : posé (Daniel)"), "Daniel"), (_("Homme : décontracté (Roger)"), "Roger")]


def prix_cloud(duree_s):
    return round(max(0.01, CI.prix("voix_transfo", "minute", PRIX_MINUTE) * float(duree_s) / 60.0), 2)


def extraire(projet, clip, sortie):
    """Le son du plan (sa partie utilisée) en WAV 44,1 kHz mono."""
    from . import moteur
    m = projet.media(clip["media"])
    d = float(clip["src_fin"]) - float(clip["src_debut"])
    moteur.lancer(["-ss", f"{float(clip['src_debut']):.3f}", "-t", f"{d:.3f}", "-i", m["chemin"], "-vn", "-ac", "1", "-ar", "44100", sortie])
    return sortie


def dossier_sorties():
    from .creations import dossier
    d = os.path.join(dossier(), "voix_transformees")
    os.makedirs(d, exist_ok=True)
    return d


def transformer_cloud(params, projet, clip, voix, debruiter=True, progression=None, arret=lambda: False):
    """Voix du plan redite par une voix du catalogue (fal.ai) ; renvoie le WAV obtenu."""
    from . import generateurs_video as GV, moteur
    k = GV.clef(params, "fal")
    if not k:
        raise GV.ErreurGenerateur(_("Il faut une clef fal.ai : Préférences › IA › Connecter une IA."))
    av = progression or (lambda f: None)
    base = os.path.join(dossier_sorties(), f"voix_{clip['id']}_{time.strftime('%Y%m%d_%H%M%S')}")
    src = extraire(projet, clip, base + "_source.wav")
    av(0.1)
    url = GV.televerser(k, src)
    res = GV.demande_fal(k, CI.point("voix_transfo", MODELE_CLOUD), {"audio_url": url, "voice": voix, "remove_background_noise": bool(debruiter)},
                         lambda f: av(0.15 + 0.75 * f), arret)
    lien = ((res.get("audio") or {}).get("url")) or res.get("audio_url") or ((res.get("output") or {}).get("url"))
    if not lien:
        raise GV.ErreurGenerateur(_("fal.ai n'a renvoyé aucun son : {r}", r=str(res)[:200]))
    brut = GV.telecharger(lien, base + "_brut")
    sortie = base + ".wav"
    moteur.lancer(["-i", brut, "-ac", "2", "-ar", "48000", sortie])
    try:
        os.remove(brut)
    except OSError:
        pass
    av(1.0)
    return sortie


def poser_cloud(projet, clip, chemin, nom):
    """Pose la voix transformée sur la piste Voix, au même instant, et coupe le son d'origine du plan (un Annuler)."""
    from . import moteur
    projet.marquer()
    m = projet.ajouter_media(chemin, moteur.sonder(chemin))
    m["nom"] = nom
    c = projet.ajouter_clip(m["id"], "voix", float(clip["debut"]))
    clip["muet"] = True
    return c
