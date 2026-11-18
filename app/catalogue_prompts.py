"""Bibliothèque toute faite de l'atelier de création (0.9.89) : catalogue/prompts.json (livré, mis à jour en ligne comme les
autres catalogues). Pièces de vêtements et matières (pour composer une tenue), tenues complètes, lieux, véhicules, aéronefs
et autres transports, personnages types inventés. Chaque entrée garde sa description anglaise, envoyée telle quelle aux IA.
Les images d'exemple (catalogue/exemples/<id>.jpg) sont facultatives : livrées, sinon lues en ligne une fois, sinon rien."""
import os
import unicodedata
import urllib.request

from . import catalogue_ligne as CL
from .langue import _

FICHIER = "prompts.json"
POUR = (("", _("Tous")), ("f", _("Femme")), ("h", _("Homme")))
PIECES = ("haut", "bas", "robe", "veste", "chaussures", "chapeau", "accessoire")


def _net(t):
    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()


def catalogue():
    return CL.charger(FICHIER) or {}


def rubriques(genre=None):
    """[(clef, nom affiché, genre)] dans l'ordre du catalogue ; `genre` filtre (« tenue », « lieu », « objet », « personnage », « piece »)."""
    r = catalogue().get("rubriques") or {}
    return [(k, CL.localise(v.get("nom")), v.get("genre", "")) for k, v in r.items() if not genre or v.get("genre") in
            ((genre,) if isinstance(genre, str) else genre)]


def entrees(rubrique=None, pour="", texte=""):
    """Entrées d'une rubrique (ou toutes), filtrées par femme / homme (les mixtes restent) et par mots, par ordre alphabétique."""
    t = _net(texte)
    out = []
    for e in catalogue().get("entrees") or []:
        if rubrique and e.get("rubrique") not in ((rubrique,) if isinstance(rubrique, str) else rubrique):
            continue
        if pour and e.get("pour") not in (pour, "m"):
            continue
        nom, desc = CL.localise(e.get("nom")), CL.localise(e.get("description"))
        if t and t not in _net(nom + " " + desc):
            continue
        out.append(dict(e, nom_affiche=nom, description_affichee=desc))
    return sorted(out, key=lambda x: _net(x["nom_affiche"]))


def entree(ident):
    return next((e for e in entrees() if e["id"] == ident), None)


def genre_de(e):
    return ((catalogue().get("rubriques") or {}).get(e.get("rubrique")) or {}).get("genre", "")


def image(e, reseau=False):
    """Image d'exemple : livrée, en copie locale, ou (reseau=True) lue une fois en ligne ; "" si aucune."""
    nom = f"exemples/{e['id']}.jpg"
    for ch in (CL._livre(nom), CL._cache(nom.replace("/", "_"))):
        if os.path.exists(ch):
            return ch
    if not reseau or os.environ.get("PHILCUT_SANS_RESEAU"):
        return ""
    try:
        from .config import VERSION
        req = urllib.request.Request(CL.BASE + nom, headers={"User-Agent": f"PhilCut/{VERSION}"})
        with urllib.request.urlopen(req, timeout=6) as r:
            octets = r.read()
        cible = CL._cache(nom.replace("/", "_"))
        with open(cible, "wb") as f:
            f.write(octets)
        return cible
    except Exception:    # noqa: BLE001 : pas d'exemple, pas grave
        return ""


def composer(pieces, matiere=None):
    """Une tenue d'après des pièces choisies (+ une matière) : (description française, description anglaise)."""
    choisies = [entree(i) for i in pieces if i]
    choisies = [x for x in choisies if x]
    m = entree(matiere) if matiere else None
    fr = ", ".join(CL.localise(x["description"]) if isinstance(x["description"], dict) else x["description"] for x in choisies)
    en = ", ".join(x["en"] for x in choisies)
    if m:
        fr += (", " if fr else "") + (m["description"].get("fr") if isinstance(m["description"], dict) else m["description"])
        en += (", " if en else "") + m["en"]
    return fr, en


def vers_bibliotheque(params, e):
    """Range l'entrée du catalogue dans « Ma bibliothèque de créations » (modifiable ensuite). Renvoie l'entrée créée."""
    from . import bibliotheque_creations as B
    genre = genre_de(e)
    if genre not in B.GENRES:
        raise ValueError(_("Cette entrée sert à composer une tenue, pas à être rangée seule."))
    fr = e["description"].get("fr") if isinstance(e["description"], dict) else e["description"]
    donnees = {"en": e["en"], "fr_origine": fr, "catalogue": e["id"], "mode": "invente"}
    if genre == "tenue":
        donnees["famille"] = e.get("rubrique", "")
    return B.garder(params, genre, CL.localise(e["nom"]), fr, None, donnees)
