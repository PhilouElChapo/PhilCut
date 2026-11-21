"""Ma bibliothèque de créations (0.9.81) : personnages, musiciens, objets, lieux, voix (chanteur, chanteuse, narration),
styles musicaux et visuels nommés, musiques, images — gardés pour être réutilisés tels quels.

Philippe (17/11) : « les créations voix, image, musique, style… il faudra les sauvegarder comme une bibliothèque pour les
réutiliser ; pour les personnages idem, pouvoir en créer en bibliothèque ; prévoir des endroits et des lieux aussi ;
musicien pareil ; un style, le nommer ; voix chanteur, chanteuse idem ». Réponses : synchronisée entre les postes et
partagée avec les autres logiciels PhilFactory ; on y range seulement quand on clique.

Rangement : <dossier PhilCut du lieu de synchronisation>/creations_partagees/<genre>/<id>/ avec fiche.json et les fichiers
(planche, photos, voix, morceau…). Sans lieu de synchronisation : le dossier de données de PhilCut. Les autres logiciels
PhilFactory lisent le même dossier (même format, champ « logiciel » pour savoir qui l'a créé). Rien n'est effacé : une
entrée retirée va dans _corbeille.
"""
import json
import os
import re
import shutil
import time
import unicodedata
import uuid

from .langue import _

FORMAT = 1
GENRES = {
    "personnage": (_("Personnage"), _("Une personne, avec sa fiche (face, profil, en pied) : elle reste identique d'une vidéo à l'autre.")),
    "musicien": (_("Musicien"), _("Un musicien inventé, avec son instrument : pour les clips de groupe.")),
    "objet": (_("Objet"), _("Un véhicule, un accessoire qui revient : sa fiche le garde identique.")),
    "lieu": (_("Lieu"), _("Un endroit, un décor : ses images et sa description.")),
    "voix": (_("Voix"), _("Chanteur, chanteuse, narration : une voix décrite, ou un timbre gardé (avec l'accord de la personne).")),
    "style_musical": (_("Style musical"), _("Un style nommé : ce que PhilCut a entendu d'un morceau, ou une description.")),
    "tenue": (_("Tenue"), _("Des vêtements décrits une fois (et une image si vous voulez), à mettre à n'importe quel personnage.")),
    "style_visuel": (_("Style visuel"), _("Une allure, un rendu « à la manière de » : décrit, jamais un visage copié.")),
    "logo": (_("Logo"), _("Un logo prêt à poser (image), fait dans l'Atelier, dessiné par l'IA ou à vous.")),
    "style_intro": (_("Style d'intro"), _("Une intro nommée : son modèle d'animation, ses couleurs, son fond.")),
    "musique": (_("Musique"), _("Un morceau créé, avec ce qui a servi à le créer.")),
    "image": (_("Image"), _("Une image créée ou gardée pour resservir.")),
    # 1.1.3 (Philippe, 21/11 20h56 : « quand on crée des modèles de musique ou autres, les enregistrer pour les retrouver »)
    "modele_musique": (_("Modèle de musique"), _("Une fiche de la Fabrique musique (style, paroles, voix, inspiration, durée), "
                                                 "à reprendre telle quelle pour un autre morceau.")),
    "modele_animation": (_("Modèle d'animation"), _("Une animation libre : sa description, son moteur et son code, à reprendre "
                                                    "et à changer.")),
}
MODES = (("reel", _("Réel"), _("D'après vos photos (plusieurs : face, profil, en pied, ou plusieurs angles) : c'est lui, tel quel.")),
         ("inspire", _("Inspiré de photos"), _("L'IA crée une version nouvelle qui garde la ressemblance des photos, adaptée par la "
                                                 "description (âge, coiffure, allure).")),
         ("invente", _("Inventé"), _("Seulement d'après la description, aucune personne réelle. « ✨ Améliorer » aide "
                                      "à la préciser.")))
ROLES_VOIX = (("chanteuse", _("Chanteuse")), ("chanteur", _("Chanteur")), ("narration", _("Narration")), ("autre", _("Autre")))


def _alpha(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def dossier(params):
    """Le dossier de la bibliothèque : sur le lieu de synchronisation (suit l'utilisateur sur tous ses postes), sinon local."""
    d = None
    try:
        from .bibliotheque import dossier_philcut_drive
        racine = dossier_philcut_drive(params)
        if racine:
            d = os.path.join(racine, "creations_partagees")
    except Exception:    # noqa: BLE001
        d = None
    if not d:
        from .config import dossier_donnees
        d = os.path.join(dossier_donnees(), "creations_partagees")
    os.makedirs(d, exist_ok=True)
    return d


def _dossier_entree(params, genre, ident):
    return os.path.join(dossier(params), genre, ident)


def _ecrire(e, d):
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "fiche.json.part")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(e, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(d, "fiche.json"))


def _nom_fichier(chemin, deja):
    base = re.sub(r"[^\w.\-]+", "_", os.path.basename(chemin))[:80] or "fichier"
    nom, ext = os.path.splitext(base)
    k, out = 1, base
    while out in deja:
        k += 1
        out = f"{nom}_{k}{ext}"
    return out


def garder(params, genre, nom, description="", fichiers=None, donnees=None, ident=None):
    """Range (ou met à jour, si `ident` est donné) une entrée ; les fichiers sont COPIÉS dans la bibliothèque. Renvoie l'entrée,
    avec « fichiers » = {rôle: chemin absolu}. `fichiers` : {rôle: chemin} (planche, photo, decoupe, voix, morceau…) ou liste."""
    if genre not in GENRES:
        raise ValueError(genre)
    nom = re.sub(r"\s+", " ", nom or "").strip()[:80]
    if not nom:
        raise ValueError(_("Donnez un nom."))
    ident = ident or time.strftime("%Y%m%d") + "_" + uuid.uuid4().hex[:8]
    d = _dossier_entree(params, genre, ident)
    ancienne = lire(params, genre, ident) or {}
    if isinstance(fichiers, (list, tuple)):
        fichiers = {f"image{k + 1}": f for k, f in enumerate(fichiers)}
    gardes = dict(ancienne.get("_fichiers") or {})
    os.makedirs(d, exist_ok=True)
    for role, src in (fichiers or {}).items():
        if not src or not os.path.exists(src):
            continue
        if os.path.abspath(os.path.dirname(src)) == os.path.abspath(d):      # déjà dans la bibliothèque
            gardes[role] = os.path.basename(src)
            continue
        cible = _nom_fichier(f"{role}{os.path.splitext(src)[1].lower()}", set(os.listdir(d)) - {gardes.get(role, "")})
        shutil.copy2(src, os.path.join(d, cible))
        for droits in (src + ".droits.json",):            # la déclaration (à moi, accord) suit le fichier
            if os.path.exists(droits):
                shutil.copy2(droits, os.path.join(d, cible + ".droits.json"))
        gardes[role] = cible
    e = {"format": FORMAT, "id": ident, "genre": genre, "nom": nom, "description": (description or "").strip()[:2000],
         "cree": ancienne.get("cree") or time.strftime("%Y-%m-%d %H:%M"), "modifie": time.strftime("%Y-%m-%d %H:%M"),
         "logiciel": ancienne.get("logiciel") or "PhilCut", "_fichiers": gardes,
         "donnees": dict(ancienne.get("donnees") or {}, **(donnees or {}))}
    _ecrire(e, d)
    return _complet(e, d)


def _complet(e, d):
    e = dict(e)
    e["dossier"] = d
    e["fichiers"] = {r: os.path.join(d, n) for r, n in (e.get("_fichiers") or {}).items() if os.path.exists(os.path.join(d, n))}
    return e


def lire(params, genre, ident):
    d = _dossier_entree(params, genre, ident)
    try:
        with open(os.path.join(d, "fiche.json"), encoding="utf-8") as f:
            e = json.load(f)
    except (OSError, ValueError):
        return None
    return _complet(e, d) if isinstance(e, dict) else None


def lister(params, genres=None):
    """Les entrées (d'un ou plusieurs genres), par ordre alphabétique du nom (accents ignorés)."""
    racine = dossier(params)
    if isinstance(genres, str):
        genres = (genres,)
    out = []
    for g in genres or GENRES:
        dg = os.path.join(racine, g)
        if not os.path.isdir(dg):
            continue
        for ident in os.listdir(dg):
            e = lire(params, g, ident)
            if e:
                out.append(e)
    return sorted(out, key=lambda e: (_alpha(e["nom"]), e["id"]))


def renommer(params, e, nom):
    return garder(params, e["genre"], nom, e.get("description", ""), None, None, e["id"])


def retirer(params, e):
    """Rien n'est effacé : l'entrée part dans _corbeille (elle se remet à la main si besoin)."""
    src = _dossier_entree(params, e["genre"], e["id"])
    if not os.path.isdir(src):
        return False
    dst = os.path.join(dossier(params), "_corbeille", e["genre"], e["id"])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        shutil.rmtree(dst, ignore_errors=True)
    shutil.move(src, dst)
    return True


def apercu(e):
    """Le fichier à montrer en vignette : planche, découpe, photo, image ; sinon rien."""
    f = e.get("fichiers") or {}
    choisie = (e.get("donnees") or {}).get("vignette")         # 1.1.7 : la photo choisie comme vignette passe avant tout
    if choisie and f.get(choisie):
        return f[choisie]
    for role in ("planche", "decoupe", "photo", "image1", "image", "vignette", "image_tenue"):
        if f.get(role):
            return f[role]
    return next((c for c in f.values() if c.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))), "")


def resume(e):
    """Une ligne lisible : genre, rôle de la voix ou instrument, description courte."""
    d = e.get("donnees") or {}
    bouts = [GENRES.get(e["genre"], ("?",))[0]]
    if e["genre"] == "voix":
        bouts.append(dict(ROLES_VOIX).get(d.get("role"), ""))
        if d.get("voix_seule") or (e.get("fichiers") or {}).get("voix_seule"):
            bouts.append(_("timbre gardé"))
    if e["genre"] == "musicien" and d.get("instrument"):
        bouts.append(d["instrument"])
    texte = e.get("description") or (d.get("voix_decrite") or {}).get("fr") or (d.get("inspiration") or {}).get("resume") or ""
    return " · ".join(x for x in bouts if x) + (" — " + texte[:140] if texte else "")


# ------------------------------------------------------------------ des cartes de l'assistant à la bibliothèque, et retour
GENRE_DE_CARTE = {"personne": "personnage", "objet": "objet", "lieu": "lieu", "voix": "voix", "style": "style_musical",
                  "logo": "logo", "style_intro": "style_intro", "fond": "image", "son": "musique"}
CARTES_POUR = {"personne": ("personnage", "musicien"), "objet": ("objet",), "lieu": ("lieu",), "voix": ("voix",),
               "style": ("style_musical",), "logo": ("logo", "image"), "style_intro": ("style_intro",), "fond": ("image", "lieu"),
               "son": ("musique",)}


def depuis_carte(params, e, nom=None, planche=""):
    """Range ce que montre une carte de l'assistant (fiche, découpe ou photo, voix décrite ou isolée, style entendu)."""
    t = e.get("type")
    genre = GENRE_DE_CARTE.get(t)
    if not genre:
        raise ValueError(t)
    fichiers, donnees = {}, {}
    if t in ("personne", "objet", "lieu"):
        for role in ("decoupe", "photo"):
            if e.get(role) and os.path.exists(e[role]):
                fichiers[role] = e[role]
        if planche and os.path.exists(planche):
            fichiers["planche"] = planche
        for k, v in enumerate(e.get("images") or []):
            if v and os.path.exists(v) and v not in fichiers.values():
                fichiers[f"image{k + 1}"] = v
        donnees.update(style=e.get("style", ""), accord=bool(e.get("accord")), mode=e.get("mode", ""),
                       tenue=e.get("tenue") or None)
    elif t == "voix":
        donnees.update(voix_decrite=e.get("voix_decrite") or None, retouche=e.get("retouche", ""), choix=e.get("choix", ""),
                       role=e.get("role") or "", accord=bool(e.get("accord")))
        if e.get("voix_seule") and os.path.exists(e["voix_seule"]):
            fichiers["voix_seule"] = e["voix_seule"]
    elif t in ("logo", "fond", "son"):
        if e.get("chemin") and os.path.exists(e["chemin"]):
            fichiers[{"logo": "image", "fond": "image", "son": "morceau"}[t]] = e["chemin"]
    elif t == "style_intro":
        donnees.update(modele=e.get("choix", ""), accent=e.get("accent", ""))
    elif t == "style":
        insp = e.get("inspiration") or {}
        donnees.update(choix=e.get("choix", ""), inspiration={k: insp[k] for k in ("caption_en", "resume", "bpm", "tonalite", "mesure")
                                                             if k in insp} or None)
    return garder(params, genre, nom or e.get("nom") or GENRES[genre][0], e.get("description", ""), fichiers, donnees)


def vers_carte(entree, e):
    """Remplit la carte `e` d'après l'entrée de la bibliothèque (rien n'est refait : fiche, voix, style sont repris)."""
    d, f = entree.get("donnees") or {}, entree.get("fichiers") or {}
    e.update(biblio=entree["id"], biblio_genre=entree["genre"], nom=entree["nom"], description=entree.get("description", ""))
    if e.get("type") in ("personne", "objet", "lieu"):
        e["planche"] = f.get("planche", "")
        e["images"] = [p for r, p in sorted(f.items()) if r not in ("planche", "image_tenue")
                       and p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
        e["style"] = d.get("style", "")
        e["accord"] = bool(d.get("accord"))
        e["mode"] = d.get("mode", "")
        if d.get("tenue"):
            e["tenue"] = d["tenue"]
    elif e.get("type") == "voix":
        e["voix_decrite"] = d.get("voix_decrite") or None
        e["retouche"] = d.get("retouche", e.get("retouche", ""))
        e["choix"] = d.get("choix", "")
        e["voix_seule"] = f.get("voix_seule", "")
        e["accord"] = bool(d.get("accord"))
    elif e.get("type") == "style":
        e["inspiration"] = d.get("inspiration") or None
        e["choix"] = d.get("choix", "")
    elif e.get("type") in ("logo", "fond"):
        e["chemin"] = apercu(entree)
    elif e.get("type") == "son":
        e["chemin"] = f.get("morceau") or next((p for p in f.values() if not p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))), "")
    elif e.get("type") == "style_intro":
        e["choix"] = d.get("modele", "") or "masque"
        e["accent"] = d.get("accent", "")
    return e
