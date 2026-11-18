"""Tenues (0.9.88) : des vêtements décrits une fois et mis à n'importe quel personnage, dans la bibliothèque (genre « tenue »)
ou parmi les tenues toutes faites ci-dessous. Une tenue est une description (et, si l'on veut, une image) : la fiche du
personnage est dessinée avec elle, et la consigne des plans la rappelle."""
import unicodedata

from .langue import _

FAMILLES = (("bureau", _("Bureau et ville")), ("soiree", _("Soirée")), ("decontracte", _("Décontracté et sport")),
            ("metiers", _("Uniformes et métiers")))

# (identifiant, famille, nom affiché, description française, description anglaise envoyée aux IA)
PRETES = (
    ("tailleur_sombre", "bureau", _("Tailleur sombre"), _("tailleur veste et pantalon bleu marine, chemisier blanc, escarpins noirs"),
     "navy blue trouser suit, white blouse, black pumps"),
    ("tailleur_jupe", "bureau", _("Tailleur jupe"), _("veste cintrée grise, jupe droite au genou, chemisier crème, escarpins"),
     "fitted grey blazer, knee-length pencil skirt, cream blouse, pumps"),
    ("costume_cravate", "bureau", _("Costume cravate"), _("costume gris anthracite, chemise blanche, cravate unie, chaussures noires"),
     "charcoal grey suit, white shirt, plain tie, black shoes"),
    ("chemise_chino", "bureau", _("Chemise et chino"), _("chemise bleu clair, pantalon chino beige, mocassins"),
     "light blue shirt, beige chino trousers, loafers"),
    ("manteau_ville", "bureau", _("Manteau de ville"), _("long manteau camel, écharpe, tenue de ville dessous"),
     "long camel coat, scarf, city clothes underneath"),
    ("robe_soiree", "soiree", _("Robe de soirée"), _("longue robe de soirée noire, bijoux discrets, chaussures à talons"),
     "long black evening gown, discreet jewellery, high heels"),
    ("robe_cocktail", "soiree", _("Robe de cocktail"), _("robe de cocktail au genou bleu nuit, pochette, talons"),
     "midnight blue knee-length cocktail dress, clutch bag, heels"),
    ("smoking", "soiree", _("Smoking"), _("smoking noir, chemise blanche, nœud papillon noir"),
     "black tuxedo, white shirt, black bow tie"),
    ("costume_soiree", "soiree", _("Costume de soirée"), _("costume bleu nuit ajusté, chemise blanche ouverte, chaussures vernies"),
     "slim midnight blue suit, open white shirt, patent shoes"),
    ("jean_tshirt", "decontracte", _("Jean et tee-shirt"), _("jean bleu, tee-shirt blanc, baskets blanches"),
     "blue jeans, white t-shirt, white sneakers"),
    ("pull_hiver", "decontracte", _("Pull d'hiver"), _("gros pull en laine, jean, bottines, bonnet"),
     "chunky wool sweater, jeans, ankle boots, beanie"),
    ("tenue_sport", "decontracte", _("Tenue de sport"), _("legging ou short de sport, tee-shirt technique, chaussures de course"),
     "sports leggings or shorts, technical t-shirt, running shoes"),
    ("vacances", "decontracte", _("Vacances d'été"), _("chemise de lin légère, short, sandales, lunettes de soleil"),
     "light linen shirt, shorts, sandals, sunglasses"),
    ("pilote_ligne", "metiers", _("Pilote de ligne"), _("uniforme de pilote : veste bleu marine à galons dorés, chemise blanche, "
                                                         "cravate, casquette"),
     "airline pilot uniform: navy jacket with gold stripes, white shirt, tie, pilot cap"),
    ("pilote_prive", "metiers", _("Pilote privé"), _("blouson d'aviateur en cuir, chemise, pantalon, lunettes de soleil, "
                                                      "casque audio autour du cou"),
     "leather flight jacket, shirt, trousers, sunglasses, aviation headset around the neck"),
    ("medecin", "metiers", _("Médecin"), _("blouse blanche, stéthoscope autour du cou, tenue de ville dessous"),
     "white lab coat, stethoscope around the neck, city clothes underneath"),
    ("pharmacien", "metiers", _("Pharmacien"), _("blouse blanche de pharmacie, badge, chemise dessous"),
     "white pharmacy coat, name badge, shirt underneath"),
    ("serveur", "metiers", _("Serveur"), _("chemise blanche, gilet noir, long tablier noir, nœud papillon"),
     "white shirt, black waistcoat, long black apron, bow tie"),
    ("chauffeur", "metiers", _("Chauffeur"), _("costume noir, chemise blanche, cravate noire, casquette de chauffeur, gants"),
     "black suit, white shirt, black tie, chauffeur cap, gloves"),
    ("cuisinier", "metiers", _("Cuisinier"), _("veste de cuisinier blanche, tablier, toque"),
     "white chef jacket, apron, chef hat"),
)


def _net(t):
    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()


def pretes(famille=None):
    """Tenues toutes faites, par ordre alphabétique de nom : [{"id", "famille", "nom", "description", "en"}]."""
    out = [{"id": "pret:" + i, "famille": f, "nom": n, "description": d, "en": en}
           for i, f, n, d, en in PRETES if not famille or f == famille]
    return sorted(out, key=lambda x: _net(x["nom"]))


def pret(ident):
    ident = (ident or "").replace("pret:", "")
    return next((x for x in pretes() if x["id"] == "pret:" + ident), None)


def toutes(params):
    """Tenues de la bibliothèque puis tenues toutes faites : [{"id", "nom", "description", "image", "source"}]."""
    from . import bibliotheque_creations as B
    out = []
    try:
        for e in B.lister(params, ["tenue"]):
            out.append({"id": "biblio:" + e["id"], "nom": e["nom"], "description": e.get("description", ""),
                        "en": (e.get("donnees") or {}).get("en", ""), "image": (e.get("fichiers") or {}).get("image_tenue", ""),
                        "source": "biblio"})
    except Exception:          # noqa: BLE001 : sans bibliothèque, les tenues toutes faites restent
        pass
    for x in pretes():
        out.append(dict(x, image="", source="pret"))
    try:                                           # 0.9.89 : les tenues complètes de la bibliothèque toute faite
        from . import catalogue_prompts as CP
        vus = {_net(x["nom"]) for x in out}
        for e in CP.entrees("tenue"):
            if _net(e["nom_affiche"]) not in vus:
                out.append({"id": "cat:" + e["id"], "nom": e["nom_affiche"], "description": e["description_affichee"], "en": e["en"],
                            "image": CP.image(e), "source": "pret", "famille": "tenue"})
    except Exception:          # noqa: BLE001
        pass
    return out


def trouver(params, ident):
    return next((x for x in toutes(params) if x["id"] == ident), None)


def texte_anglais(t):
    """La description envoyée aux IA (anglais connu pour les tenues toutes faites)."""
    if not t:
        return ""
    return t.get("en") or t.get("description", "")
