"""Motion design IA « look pro » (1.1.16) : ce que fait l'animation libre, avec la méthode des outils en ligne.

Demande de Philippe (22/11 22h06) : « l'IA regarde le rendu, vrais dessins, modèle pour le code choisi suivant la complexité,
bibliothèques (où les trouver, haute qualité), mélange vidéo IA ».

Etapes, chacune facultative et chiffrée avant de payer :
1. Préproduction (un appel court) : l'IA lit la description et choisit dans la bibliothèque de blocs HyperFrames (le registre
   officiel de HeyGen, Apache 2.0 : 236 composants éprouvés : textes, particules, transitions, compteurs…) ceux qui aident,
   liste les dessins à faire (objets, personnages, décors) et les plans vidéo réalistes (feu, fumée, explosion, eau…),
   et note la complexité, qui choisit le modèle qui écrit le code.
2. Dessins : Gemini dessine chaque objet sur un fond vert uni ; PhilCut retire le vert (PNG transparent).
3. Plans vidéo : un générateur vidéo (votre clef) fabrique chaque effet réaliste sur fond noir ; PhilCut le pose au bon
   instant, en mode « écran » (le noir disparaît).
4. Ecriture : le modèle choisi écrit la composition avec ces blocs, dessins et plans.
5. Relecture : l'IA regarde une image par étape de l'aperçu, et fait corriger ce qui ne se voit pas, quelques tours au plus.
"""
import json
import os
import re
import urllib.request

from .langue import _

REGISTRE = "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry"
MAX_BLOCS, MAX_IMAGES, MAX_VIDEOS = 3, 4, 2
MAX_SOURCE_BLOC = 14000                      # caractères d'un bloc donnés à l'IA (les plus longs sont coupés)
PRIX_PREPARER = 0.03
PRIX_IMAGE = 0.04
DUREE_VIDEO = 5
# Modèles d'écriture : la complexité notée à la préproduction choisit (Opus 5.5 : 4 $ / 20 $ le million de jetons, Sonnet 5.5 :
# 2 $ / 10 $ ; Gemini Pro et Flash de même)
MODELES = {"claude": {1: "claude-sonnet-5-5", 2: "claude-sonnet-5-5", 3: "claude-opus-5-5"},
           "gemini": {1: "gemini-2.5-flash", 2: "gemini-2.5-pro", 3: "gemini-2.5-pro"}}
PRIX_ECRIRE = {"claude-sonnet-5-5": 0.12, "claude-opus-5-5": 0.24, "gemini-2.5-flash": 0.04, "gemini-2.5-pro": 0.15}
CHOIX_MODELE = ("auto", "rapide", "meilleur")


def nom_modele(m):
    return {"claude-sonnet-5-5": "Claude Sonnet", "claude-opus-5-5": "Claude Opus", "gemini-2.5-flash": "Gemini Flash",
            "gemini-2.5-pro": "Gemini Pro"}.get(m, m)


# ------------------------------------------------------------------ la bibliothèque de blocs
def catalogue():
    """Les composants du registre HyperFrames (catalogue/blocs_hyperframes.json, livré et mis à jour en ligne)."""
    from . import catalogue_ligne as CL
    return [b for b in (CL.charger("blocs_hyperframes.json").get("blocs") or []) if isinstance(b, dict) and b.get("nom")]


def catalogue_texte(blocs=None):
    return "\n".join(f"{b['nom']}: {b.get('description', '')[:120]} [{', '.join((b.get('tags') or [])[:4])}]"
                     for b in (blocs if blocs is not None else catalogue()))


def _dossier_blocs():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "blocs_hyperframes")
    os.makedirs(d, exist_ok=True)
    return d


def _lire_url(url, delai=40):
    from . import reseau
    with reseau.ouvrir(urllib.request.Request(url, headers={"User-Agent": "PhilCut"}), timeout=delai) as r:
        return r.read().decode("utf-8", "replace")


def source_bloc(nom):
    """Le code d'un composant (gardé sur ce poste après le premier téléchargement)."""
    if not re.fullmatch(r"[a-z0-9-]{2,60}", nom or ""):
        raise ValueError(_("Nom de bloc invalide : {n}", n=nom))
    cache = os.path.join(_dossier_blocs(), nom + ".html")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            return f.read()
    fiche = json.loads(_lire_url(f"{REGISTRE}/components/{nom}/registry-item.json"))
    morceaux = []
    for f in fiche.get("files") or []:
        p = f.get("path") or ""
        if p.endswith((".html", ".css", ".js")) and re.fullmatch(r"[A-Za-z0-9_./-]{1,120}", p) and ".." not in p:
            morceaux.append(_lire_url(f"{REGISTRE}/components/{nom}/{p}"))
    texte = "\n".join(morceaux)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(texte)
    return texte


# ------------------------------------------------------------------ préproduction
CONSIGNE_PREPARER = """You are the art director of a motion design studio. Read the user's description of an animation and prepare
the production. Answer in JSON only:
{"complexite": 1, 2 or 3 (1 = a few texts and shapes; 2 = several scenes or effects; 3 = many objects, choreography, particles,
  physics or illustration),
 "blocs": [names of at most 3 components from the LIBRARY below that would really help (proven, high-quality building blocks:
   text reveals, particles, transitions, counters…); [] if none fits],
 "images": [at most 4 objects, characters or props that must LOOK REAL or detailed (a cannon, an airplane, a gift, a product…),
   drawn once as illustrations: {"id": "short_id", "en": "precise English description of the object alone, its view angle and
   style", "forme": "carre" | "large" | "haut"}; do not list texts, simple shapes, particles or backgrounds],
 "videos": [at most 2 realistic effects that code cannot draw well (fire, smoke, explosion, water, sparks, lightning…), filmed
   on a pure black background: {"id": "short_id", "en": "precise English description, black background, centered", "duree": 3 to 5}],
 "pourquoi": "one sentence in {langue}: what you chose and why"}
Images allowed: {images}. Videos allowed: {videos}.

LIBRARY (name: description [tags]):
{catalogue}"""


def _slug(t, defaut):
    s = re.sub(r"[^a-z0-9_]", "_", (t or "").lower())[:24].strip("_")
    return s or defaut


def lire_preparation(d, noms_blocs, avec_images=True, avec_videos=True):
    """La préproduction bornée : complexité 1-3, blocs connus, images et vidéos limitées (ids uniques)."""
    d = d if isinstance(d, dict) else {}
    try:
        cx = max(1, min(3, int(d.get("complexite") or 2)))
    except (TypeError, ValueError):
        cx = 2
    blocs = [b for b in (d.get("blocs") or []) if isinstance(b, str) and b in noms_blocs][:MAX_BLOCS]
    images, vus = [], set()
    for k, x in enumerate((d.get("images") or []) if avec_images else []):
        if not isinstance(x, dict) or not str(x.get("en", "")).strip():
            continue
        i = _slug(x.get("id"), f"image{k + 1}")
        if i in vus:
            continue
        vus.add(i)
        images.append({"id": i, "en": str(x["en"]).strip()[:400],
                       "forme": x.get("forme") if x.get("forme") in ("carre", "large", "haut") else "carre"})
    videos = []
    for k, x in enumerate((d.get("videos") or []) if avec_videos else []):
        if not isinstance(x, dict) or not str(x.get("en", "")).strip():
            continue
        i = _slug(x.get("id"), f"video{k + 1}")
        if i in vus:
            continue
        vus.add(i)
        try:
            duree = max(3, min(5, int(round(float(x.get("duree") or 4)))))
        except (TypeError, ValueError):
            duree = 4
        videos.append({"id": i, "en": str(x["en"]).strip()[:400], "duree": duree})
    return {"complexite": cx, "blocs": blocs, "images": images[:MAX_IMAGES], "videos": videos[:MAX_VIDEOS],
            "pourquoi": str(d.get("pourquoi") or "").strip()[:400]}


def preparer(params, anim, avec_images=True, avec_videos=True):
    from . import ia
    from .motion import _langue_ui
    blocs = catalogue() if anim.get("moteur_libre", "hyperframes") != "remotion" else []
    consigne = (CONSIGNE_PREPARER.replace("{langue}", _langue_ui()).replace("{catalogue}", catalogue_texte(blocs) or "(none)")
                .replace("{images}", "yes" if avec_images else "no").replace("{videos}", "yes" if avec_videos else "no"))
    r = ia.demander(params, consigne, anim.get("description", ""), json_attendu=True, max_jetons=1500)
    return lire_preparation(r, {b["nom"] for b in blocs}, avec_images, avec_videos)


def modele(params, complexite, choix="auto"):
    """Le modèle qui écrit le code (Claude ou Gemini selon le réglage « Assistant »), d'après la complexité ou le choix."""
    from . import ia
    fam = "gemini" if (params.get("ia_moteur") == "gemini" or not ia.nettoyer_clef(params.get("clef_claude", ""))) \
        and ia.nettoyer_clef(params.get("clef_gemini", "")) else "claude"
    niveau = {"rapide": 1, "meilleur": 3}.get(choix, complexite)
    return fam, MODELES[fam][niveau]


def params_modele(params, fam, m):
    """Les réglages pour forcer ce modèle le temps d'un appel."""
    return dict(params, ia_moteur=fam, **({"ia_modele_claude": m} if fam == "claude" else {"ia_modele_gemini": m}))


def prix(prep, modele_id, params=None, tours=2):
    """Coût indicatif en $ : {dessins, videos, ecrire, relecture, total}."""
    from . import generateurs_video as GV
    m = modele_video(params or {})
    pv = sum(GV.prix(m, v["duree"], False) for v in prep.get("videos") or []) if m else 0.0
    ecrire = PRIX_ECRIRE.get(modele_id, 0.12) + 0.02 * len(prep.get("blocs") or [])
    relecture = tours * (0.03 + PRIX_ECRIRE.get(modele_id, 0.12) * 0.8)
    out = {"dessins": PRIX_IMAGE * len(prep.get("images") or []), "videos": pv, "ecrire": ecrire, "relecture": relecture}
    out["total"] = sum(out.values())
    return out


# ------------------------------------------------------------------ dessins (Gemini, fond vert retiré)
FORMES = {"carre": "square 1:1", "large": "wide 16:9", "haut": "tall 9:16"}


def consigne_dessin(img, style=""):
    return (f"{img['en']}. {style or 'High-quality detailed illustration, soft studio lighting, crisp edges'}. The object ALONE, "
            f"whole and centered, {FORMES.get(img.get('forme'), 'square 1:1')} framing, on a perfectly uniform pure green "
            "(#00FF00) background with no shadow, no floor, no gradient, no text, no logo, no other object.")


def retirer_vert(source, sortie):
    """Fond vert uni → transparent (avec un adoucissement des bords et le vert des contours retiré). Renvoie la taille."""
    import numpy as np
    from PySide6.QtGui import QImage
    q = QImage(source).convertToFormat(QImage.Format_RGBA8888)
    if q.isNull():
        raise ValueError(_("Image illisible : {f}", f=source))
    w, h = q.width(), q.height()
    a = np.frombuffer(q.constBits(), np.uint8, count=q.bytesPerLine() * h).reshape(h, q.bytesPerLine())[:, :w * 4]
    a = a.reshape(h, w, 4).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    vert = g - np.maximum(r, b)                          # combien le pixel est « plus vert » que le reste
    alpha = np.clip(1.0 - (vert - 40.0) / 80.0, 0.0, 1.0)
    g2 = np.where(vert > 0, np.minimum(g, np.maximum(r, b) + 10), g)    # liseré vert des contours retiré
    out = np.dstack([r, g2, b, alpha * 255]).clip(0, 255).astype(np.uint8)
    ys, xs = np.nonzero(alpha > 0.05)                    # recadré au plus près de l'objet
    if len(xs):
        m = 4
        x0, x1, y0, y1 = max(0, xs.min() - m), min(w, xs.max() + m + 1), max(0, ys.min() - m), min(h, ys.max() + m + 1)
        out = np.ascontiguousarray(out[y0:y1, x0:x1])
    hh, ww = out.shape[:2]
    QImage(out.data, ww, hh, ww * 4, QImage.Format_RGBA8888).copy().save(sortie, "PNG")
    return ww, hh


def dessiner(params, img, dossier, style=""):
    """Un dessin de la préproduction : PNG transparent dans `dossier`. Renvoie {chemin, largeur, hauteur}."""
    from . import ia
    brut = os.path.join(dossier, f"dessin_{img['id']}_brut.png")
    with open(brut, "wb") as f:
        f.write(ia.generer_image(params, consigne_dessin(img, style)))
    sortie = os.path.join(dossier, f"img_{img['id']}.png")
    w, h = retirer_vert(brut, sortie)
    return {"chemin": sortie, "largeur": w, "hauteur": h}


# ------------------------------------------------------------------ plans vidéo réalistes
def modele_video(params):
    """Le générateur vidéo qui fera les effets : celui choisi dans les réglages, sinon le premier disponible qui part d'un texte."""
    from . import generateurs_video as GV
    voulu = params.get("motion_pro_video")
    dispo = [m for m in GV.disponibles(params) if not m.get("references") and not m.get("image_seule")
             and "360p" not in m.get("id", "")]
    for m in dispo:
        if m.get("id") == voulu:
            return m
    return dispo[0] if dispo else None


def filmer(params, vid, dossier, format_="16:9", progression=None, arret=None):
    """Un effet réaliste sur fond noir (votre clef du générateur). Renvoie {chemin, duree}."""
    from . import generateurs_video as GV
    m = modele_video(params)
    if m is None:
        raise ValueError(_("Aucun générateur vidéo n'est connecté : Fabrique IA › Connecter une IA (fal ou Google)."))
    sortie = os.path.join(dossier, f"vid_{vid['id']}.mp4")
    consigne = (f"{vid['en']}. Pure black background, static camera, the effect only, no text, no people, no logo, "
                "high detail, cinematic.")
    GV.generer(params, m["id"], consigne, sortie, vid["duree"], format_, None, progression=progression, arret=arret)
    return {"chemin": sortie, "duree": float(vid["duree"])}


# ------------------------------------------------------------------ ce que l'écriture reçoit
def consigne_ressources(lib, moteur="hyperframes"):
    """Le paragraphe ajouté à la consigne d'écriture : blocs (code à adapter), dessins (IMG.id), plans vidéo (===VIDEOS===)."""
    morceaux = []
    res = lib.get("ressources") or {}
    imgs = res.get("images") or {}
    if imgs:
        acces = "A.IMG.<id>" if moteur == "remotion" else "IMG.<id>"
        balise = "<Img src={A.IMG.id} />" if moteur == "remotion" else "$('img', {...}).src = IMG.id (or an <img> in HTML)"
        morceaux.append(
            "ILLUSTRATIONS ALREADY DRAWN FOR YOU (transparent PNG, use them instead of drawing these objects in SVG; give each a "
            f"width in u and keep its proportions; animate them like any element). Access: {acces}, e.g. {balise}.\n" +
            "\n".join(f"- {k}: {v['en']} ({v.get('largeur', '?')}×{v.get('hauteur', '?')} px)" for k, v in imgs.items()))
    vids = res.get("videos") or {}
    if vids:
        morceaux.append(
            "REALISTIC VIDEO EFFECTS ALREADY FILMED (black background; PhilCut lays them over your animation in screen mode, the "
            "black disappears). Do not draw these effects yourself: place each one with an extra section ===VIDEOS===, one line "
            "per use: \"id start_seconds duration_seconds center_x center_y width\" in pixels of the frame (e.g. \"boom 5.3 1.5 "
            "540 900 900\"). An effect may be used several times.\n" +
            "\n".join(f"- {k}: {v['en']} ({v['duree']:g} s)" for k, v in vids.items()))
    blocs = res.get("blocs") or {}
    if blocs and moteur != "remotion":
        morceaux.append(
            "PROVEN HIGH-QUALITY BUILDING BLOCKS from the HyperFrames registry (Apache-2.0). Reuse their technique, CSS and "
            "timing (adapt them into your single composition: your elements in #scenes, every tween on `tl` at absolute times, "
            "colours from C, sizes in u; drop their demo card, titles and sample texts):\n" +
            "\n\n".join(f"--- {k} ---\n{v[:MAX_SOURCE_BLOC]}" for k, v in blocs.items()))
    return ("\n\n" + "\n\n".join(morceaux)) if morceaux else ""


def lire_videos(texte, connues, D=None):
    """Lignes « id début durée cx cy largeur » → [{id, debut, duree, cx, cy, largeur}] (ids connus seulement)."""
    out = []
    for ligne in (texte or "").splitlines():
        p = ligne.replace(",", " ").split()
        if len(p) < 3 or p[0] not in connues:
            continue
        try:
            v = [float(x) for x in p[1:6]]
        except ValueError:
            continue
        debut, duree = max(0.0, v[0]), max(0.2, v[1])
        if D:
            debut = min(debut, max(0.0, D - 0.2))
            duree = min(duree, D - debut)
        out.append({"id": p[0], "debut": round(debut, 3), "duree": round(duree, 3),
                    "cx": v[2] if len(v) > 2 else None, "cy": v[3] if len(v) > 3 else None,
                    "largeur": v[4] if len(v) > 4 else None})
    return out[:12]
