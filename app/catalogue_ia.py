"""Catalogue unique des IA cloud (0.9.85) : adresse du service, prix indicatif, état (conseillé, ancien, retiré) et
remplaçant. Les valeurs livrées avec PhilCut servent toujours de secours ; le catalogue en ligne (catalogue/ia.json, relu
chaque jour sans bloquer) peut corriger un prix, changer d'adresse ou retirer un service devenu indisponible. Un service
retiré est remplacé tout seul par celui que le catalogue indique, et PhilCut le dit une fois dans la barre du bas.

Les IA locales (moteurs, modèles) restent décrites par le manifeste de packs_ia ; leurs mises à jour passent par maj_ia."""
import json, os

from .langue import _

FICHIER = "ia.json"
ETATS = ("conseille", "ancien", "retire")

# rôle -> service livré (prix en $, relevés en novembre 2026 sur fal.ai, indicatifs)
SERVICES = {
    "bruitages": {"nom": "MMAudio v2 (fal.ai)", "point": "fal-ai/mmaudio-v2", "prix": {"s": 0.001},
                  "usage": _("Bruitages calés sur l'image")},
    "detourage_video": {"nom": "Bria Video Background Removal v3 (fal.ai)", "point": "bria/video/background-removal/v3",
                        "prix": {"s": 0.05}, "usage": _("Fond retiré dans le cloud")},
    "levres_latentsync": {"nom": "LatentSync (fal.ai)", "point": "fal-ai/latentsync",
                          "prix": {"fixe": 0.20, "seuil": 40.0, "s": 0.005}, "usage": _("Lèvres calées sur la voix")},
    "levres_lipsync2": {"nom": "Sync lipsync-2 (fal.ai)", "point": "fal-ai/sync-lipsync/v2", "prix": {"s": 0.05},
                        "usage": _("Lèvres calées sur la voix")},
    "levres_omnihuman": {"nom": "OmniHuman 1.5 (fal.ai)", "point": "fal-ai/bytedance/omnihuman/v1.5", "prix": {"s": 0.16},
                         "usage": _("Image animée par la voix")},
    "suivi_video": {"nom": "SAM 3 vidéo (fal.ai)", "point": "fal-ai/sam-3/video", "prix": {"16": 0.005},
                    "usage": _("Suivi d'un élément dans le cloud")},
    "voix_transfo": {"nom": "ElevenLabs Voice Changer (fal.ai)", "point": "fal-ai/elevenlabs/voice-changer",
                     "prix": {"minute": 0.30}, "usage": _("Voix transformée")},
}

_en_ligne = None
_annonces = []          # services retirés remplacés pendant cette session : dits une fois


def _catalogue(recharger=False):
    global _en_ligne
    if _en_ligne is None or recharger:
        if os.environ.get("PHILCUT_IA_CATALOGUE"):
            try:
                with open(os.environ["PHILCUT_IA_CATALOGUE"], encoding="utf-8") as f:
                    _en_ligne = json.load(f)
            except (OSError, ValueError):
                _en_ligne = {}
        else:
            from . import catalogue_ligne
            _en_ligne = catalogue_ligne.charger(FICHIER, reseau=False)
    return _en_ligne if isinstance(_en_ligne, dict) else {}


def recharger():
    _catalogue(recharger=True)


def service(role):
    """Le service d'un rôle : livré, corrigé par le catalogue en ligne. Toujours un dict (vide pour un rôle inconnu)."""
    base = dict(SERVICES.get(role) or {})
    ligne = (_catalogue().get("services") or {}).get(role)
    if isinstance(ligne, dict):
        prix = dict(base.get("prix") or {})
        prix.update({k: float(v) for k, v in (ligne.get("prix") or {}).items() if isinstance(v, (int, float))})
        base.update({k: v for k, v in ligne.items() if k != "prix"})
        base["prix"] = prix
    base.setdefault("etat", "conseille")
    base["role"] = role
    return base


def _actif(role):
    """Le service réellement utilisé : un service retiré cède la place à son remplaçant (3 sauts au plus)."""
    s = service(role)
    vus = {role}
    for _i in range(3):
        rempl = s.get("remplace_par")
        if s.get("etat") != "retire" or not rempl:
            break
        if rempl in vus:
            break
        vus.add(rempl)
        if rempl in SERVICES or rempl in (_catalogue().get("services") or {}):
            neuf = service(rempl)
        else:                                   # remplaçant donné par son adresse seule
            neuf = dict(s, point=rempl, etat="conseille", remplace_par="", nom=s.get("nom_remplacant") or rempl)
        _annoncer(role, s, neuf)
        s = neuf
    return s


def _annoncer(role, ancien, neuf):
    texte = ancien.get("message") or _("« {a} » n'est plus proposé : PhilCut utilise maintenant « {n} ».",
                                        a=ancien.get("nom") or role, n=neuf.get("nom") or neuf.get("point", ""))
    if texte not in _annonces:
        _annonces.append(texte)


def annonces():
    """Messages à montrer (une fois) : services retirés et remplacés."""
    out = list(_annonces)
    _annonces.clear()
    return out


def point(role, defaut=""):
    return _actif(role).get("point") or defaut


def prix(role, champ, defaut=0.0):
    try:
        return float((_actif(role).get("prix") or {}).get(champ, defaut))
    except (TypeError, ValueError):
        return defaut


def retire(role):
    """Le service est retiré sans remplaçant : la fonction n'est plus disponible."""
    s = service(role)
    return s.get("etat") == "retire" and not s.get("remplace_par")


def nom(role):
    return _actif(role).get("nom") or role


def liste():
    """Tous les services cloud connus (livrés et ajoutés en ligne), par ordre alphabétique de nom."""
    import unicodedata
    roles = set(SERVICES) | set((_catalogue().get("services") or {}))
    net = lambda t: unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return sorted((service(r) for r in roles), key=lambda s: net(s.get("nom") or s["role"]))


def etat_texte(etat):
    return {"conseille": _("conseillé"), "ancien": _("ancienne version"), "retire": _("retiré")}.get(etat, etat)


def nombre(x):
    """0.05 → « 0,05 » (écriture française)."""
    try:
        return f"{float(x):g}".replace(".", ",")
    except (TypeError, ValueError):
        return str(x)


def prix_texte(s):
    p = {k: nombre(v) for k, v in (s.get("prix") or {}).items()}
    if "fixe" in p:
        return _("{f} $ jusqu'à {d} s, puis {s} $/s", f=p["fixe"], d=p.get("seuil", 0), s=p.get("s", 0))
    if "minute" in p:
        return _("{p} $/min", p=p["minute"])
    if "16" in p:
        return _("{p} $ les 16 images", p=p["16"])
    if "s" in p:
        return _("{p} $/s", p=p["s"])
    return ""
