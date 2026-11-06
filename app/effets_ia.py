"""Catalogue des effets IA locaux (0.6) : prompts préprogrammés, modifiables et enregistrables par l'utilisateur.

Chaque effet : famille (image, video, logo, musique), moteur, phrase (prompt) et réglages. L'utilisateur peut changer la
phrase et la force d'un effet (ses changements sont gardés dans les préférences) ou en créer un à lui. Le catalogue
s'enrichit avec la veille (nouveaux effets publiés dans le catalogue en ligne, catalogue/effets_ia.json).
"""
import copy, json, os

from .langue import _

FAMILLES = {"image": _("Image du film retouchée"), "logo": _("Logo, intro, miniature"), "video": _("Effet sur la partie en jaune"),
            "musique": _("Musique")}

# moteur : image (stable-diffusion.cpp), anime (ONNX ou OpenCV), profondeur, photo3d, upscale, interpolation, video (Wan), musique
EFFETS = [
    {"id": "cartoon_3d", "famille": "image", "moteur": "image", "nom": _("Personnage 3D façon film d'animation"),
     "prompt": "3d animated movie style, pixar style character, soft lighting, vibrant colors, highly detailed", "force": 0.55},
    {"id": "anime", "famille": "image", "moteur": "image", "nom": _("Anime japonais"),
     "prompt": "anime style, studio ghibli, cel shading, beautiful clouds, vivid colors", "force": 0.55},
    {"id": "bd", "famille": "image", "moteur": "image", "nom": _("Bande dessinée"),
     "prompt": "comic book style, bold ink outlines, halftone dots, flat colors", "force": 0.6},
    {"id": "aquarelle", "famille": "image", "moteur": "image", "nom": _("Aquarelle"),
     "prompt": "watercolor painting, soft washes, paper texture, delicate", "force": 0.55},
    {"id": "huile", "famille": "image", "moteur": "image", "nom": _("Peinture à l'huile"),
     "prompt": "oil painting, thick brush strokes, impressionist, rich colors", "force": 0.55},
    {"id": "croquis", "famille": "image", "moteur": "image", "nom": _("Croquis au crayon"),
     "prompt": "pencil sketch, graphite drawing, cross hatching, white paper", "force": 0.6},
    {"id": "cyberpunk", "famille": "image", "moteur": "image", "nom": _("Néon cyberpunk"),
     "prompt": "cyberpunk city style, neon lights, pink and cyan glow, night, cinematic", "force": 0.5},
    {"id": "jouet", "famille": "image", "moteur": "image", "nom": _("Figurine en plastique"),
     "prompt": "toy figurine, plastic action figure, miniature diorama, tilt shift", "force": 0.6},
    {"id": "poster", "famille": "image", "moteur": "image", "nom": _("Affiche vintage de voyage"),
     "prompt": "retro travel poster, flat vector illustration, limited palette, bold shapes", "force": 0.65},
    {"id": "logo_mascotte", "famille": "logo", "moteur": "image", "nom": _("Mascotte cartoon à partir de l'image"),
     "prompt": "cute cartoon mascot, sticker style, thick white outline, simple flat colors, centered, plain background", "force": 0.7,
     "action": "logo"},
    {"id": "logo_embleme", "famille": "logo", "moteur": "image", "nom": _("Emblème rond (sans image)"),
     "prompt": "minimalist round emblem logo, flat vector, two colors, centered, plain white background", "force": 1.0, "action": "logo",
     "sans_source": True},
    {"id": "miniature", "famille": "logo", "moteur": "image", "nom": _("Miniature YouTube éclatante"),
     "prompt": "youtube thumbnail style, dramatic lighting, high contrast, saturated colors, sharp details", "force": 0.35,
     "action": "miniature"},
    {"id": "fond_intro", "famille": "logo", "moteur": "image", "nom": _("Fond d'intro (à partir d'une phrase)"),
     "prompt": "abstract gradient background, soft light, bokeh, modern, clean", "force": 1.0, "sans_source": True, "action": "fond"},
    {"id": "v_anime", "famille": "video", "moteur": "anime", "nom": _("Dessin animé (vidéo)"), "prompt": "", "force": 1.0},
    {"id": "v_flou_fond", "famille": "video", "moteur": "profondeur", "nom": _("Flou d'arrière-plan (effet portrait)"), "prompt": "", "force": 12},
    {"id": "v_photo3d", "famille": "video", "moteur": "photo3d", "nom": _("Photo 3D à partir de l'image (3 s)"), "prompt": "", "force": 0.06},
    {"id": "v_agrandir", "famille": "video", "moteur": "upscale", "nom": _("Agrandir ×2 (netteté IA)"), "prompt": "", "force": 2},
    {"id": "v_ralenti", "famille": "video", "moteur": "interpolation", "nom": _("Ralenti fluide ×4"), "prompt": "", "force": 4},
    {"id": "v_transition", "famille": "video", "moteur": "transition3d", "nom": _("Transition 3D entre deux plans (raccord le plus proche)"),
     "prompt": "", "force": 1.2},
    {"id": "v_animer", "famille": "video", "moteur": "video", "nom": _("Animer l'image (Wan, expérimental)"),
     "prompt": "slow cinematic camera push in, gentle natural motion", "force": 2.5},
]
for _k, _n, _c in __import__("app.creatif", fromlist=["STYLES_MUSIQUE"]).STYLES_MUSIQUE:
    EFFETS.append({"id": "m_" + _k, "famille": "musique", "moteur": "musique", "nom": _n, "prompt": _c, "force": 1.0})


def tous(params=None):
    """Effets du catalogue, avec les changements de l'utilisateur et ses effets à lui (params « effets_ia_perso »)."""
    perso = (params or {}).get("effets_ia_perso") or {}
    out = []
    vus = set()
    for e in EFFETS + _en_ligne():
        if e["id"] in vus:
            continue
        vus.add(e["id"])
        x = copy.deepcopy(e)
        x.update({k: v for k, v in (perso.get(e["id"]) or {}).items() if k in ("prompt", "force", "nom")})
        x["modifie"] = e["id"] in perso
        out.append(x)
    for k, v in perso.items():
        if k not in vus and v.get("famille"):
            x = dict(v, id=k, perso=True)
            out.append(x)
    return out


def enregistrer(params, effet, prompt, force, nom=None, nouveau=False):
    """Garde la phrase et la force (ou crée « mon effet »)."""
    perso = dict(params.get("effets_ia_perso") or {})
    if nouveau:
        i = 1
        while f"perso_{i}" in perso:
            i += 1
        cle = f"perso_{i}"
        perso[cle] = {"famille": effet["famille"], "moteur": effet["moteur"], "nom": nom or _("Mon effet {n}", n=i), "prompt": prompt,
                      "force": force, "action": effet.get("action"), "sans_source": effet.get("sans_source", False)}
    else:
        cle = effet["id"]
        perso[cle] = dict(perso.get(cle) or {}, prompt=prompt, force=force, **({"nom": nom} if nom else {}))
        if effet.get("perso"):
            perso[cle].update(famille=effet["famille"], moteur=effet["moteur"])
    params["effets_ia_perso"] = perso
    try:
        params.enregistrer()
    except AttributeError:
        pass
    return cle


def retablir(params, effet_id):
    perso = dict(params.get("effets_ia_perso") or {})
    perso.pop(effet_id, None)
    params["effets_ia_perso"] = perso


def _en_ligne():
    """Effets ajoutés par la veille dans catalogue/effets_ia.json (livré avec PhilCut, mis à jour avec les versions)."""
    import sys
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(base, "catalogue", "effets_ia.json"), encoding="utf-8") as f:
            return [e for e in json.load(f).get("effets", []) if e.get("id") and e.get("famille") in FAMILLES]
    except (OSError, ValueError):
        return []


def disponible(effet, params=None):
    """(True, "") si l'effet peut tourner sur ce poste, sinon (False, ce qu'il manque)."""
    from . import packs_ia as P
    m = effet["moteur"]
    if m in ("anime", "photo3d", "profondeur", "transition3d"):
        return True, ""                                   # repli OpenCV / estimation sans modèle
    genre = {"image": "image", "video": "video", "musique": "musique", "upscale": "upscale", "interpolation": "interpolation"}[m]
    if P.modele_actif(genre, params):
        return True, ""
    return False, _("Il faut le modèle « {g} » : Edition › Préférences › IA locale.", g=P.GENRES.get(genre, genre))
