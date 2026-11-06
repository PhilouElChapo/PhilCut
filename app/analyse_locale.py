"""IA sur les rushes, uniquement sur ce poste (0.4.3) : rien n'est envoyé, rien n'est payé.

Le modèle de vision local (Préférences › IA locale, llama.cpp portable) regarde quelques images de chaque rush et
rend, en une fois : une phrase qui décrit le rush, les lieux et objets vus, les textes lisibles (immatriculations,
panneaux, enseignes) et un nom court. Le résultat est gardé dans le projet (media["ia_locale"]) : la recherche des
médias porte dessus, la fiche vidéo l'affiche, un texte lu peut devenir une étiquette.
"""
import json, re, time, unicodedata

from .langue import _

CONSIGNE = (
    "Voici {n} images tirées, dans l'ordre, d'une même vidéo. Réponds en français, uniquement en JSON, avec les clefs : "
    "\"nom\" (3 à 5 mots qui nomment la vidéo, ex. « Balade en bord de mer »), \"resume\" (une phrase), "
    "\"lieux_objets\" (liste de mots : lieux, objets, personnes, animaux, météo), "
    "\"textes\" (liste des textes réellement lisibles : immatriculations d'avion comme F-GABC, panneaux, enseignes, "
    "écrans ; liste vide si rien n'est lisible ; n'invente rien).")


class ErreurAnalyse(Exception):
    pass


def disponible(params):
    from . import ia_locale
    return ia_locale.modele_actif(params) is not None


def analyser(media, params, progression=None, n_images=4):
    """Analyse un rush (vidéo ou image) avec le modèle de vision local ; renvoie le dictionnaire gardé dans le média."""
    from . import ia_locale, moteur
    modele = ia_locale.modele_actif(params)
    if not modele:
        raise ErreurAnalyse(_("Aucun modèle de vision sur ce poste : cochez-en un dans Edition › Préférences › IA locale."))
    p = progression or (lambda f: None)
    duree = float((media.get("fiche") or {}).get("duree") or 0)
    if media.get("genre") == "image":
        images = [open(media["chemin"], "rb").read()]
    else:
        instants = [duree * (k + 0.5) / n_images for k in range(n_images)] if duree > 0 else [0.0]
        images = moteur.images_clefs(media["chemin"], instants, 448)
    p(0.3)
    brut = ia_locale.generer(modele, CONSIGNE.format(n=len(images)), images, json_attendu=True, params=params)
    p(0.95)
    d = lire_json(brut)
    out = {"nom": str(d.get("nom") or "").strip()[:60], "resume": str(d.get("resume") or "").strip()[:400],
           "lieux_objets": [str(x).strip() for x in (d.get("lieux_objets") or []) if str(x).strip()][:20],
           "textes": [str(x).strip() for x in (d.get("textes") or []) if str(x).strip()][:20],
           "modele": modele, "date": time.strftime("%Y-%m-%d %H:%M")}
    media["ia_locale"] = out
    return out


def lire_json(texte):
    """Le premier objet JSON de la réponse (les petits modèles ajoutent parfois du texte autour)."""
    try:
        return json.loads(texte)
    except (TypeError, ValueError):
        pass
    m = re.search(r"\{.*\}", texte or "", re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except ValueError:
            pass
    return {"resume": (texte or "").strip()[:400]}


def _sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def texte_cherchable(media):
    a = media.get("ia_locale") or {}
    morceaux = [media.get("nom", ""), a.get("nom", ""), a.get("resume", "")] + list(a.get("lieux_objets") or []) + list(a.get("textes") or [])
    morceaux.append(((media.get("analyse") or {}).get("resume")) or "")
    return _sans_accents(" ".join(morceaux))


def correspond(media, recherche):
    """Tous les mots de la recherche se trouvent dans le nom ou dans ce que l'IA locale a vu (accents ignorés)."""
    mots = _sans_accents(recherche).split()
    t = texte_cherchable(media)
    return all(m in t for m in mots)
