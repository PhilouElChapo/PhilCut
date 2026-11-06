"""Catalogues en ligne (effets FFmpeg, effets IA) : lus sur GitHub sans bloquer, gardés en copie locale pour les jours
sans réseau, et à défaut ceux livrés avec PhilCut. Un texte peut être donné par langue : {"fr": "...", "en": "..."}."""
import json, os, sys, urllib.request

BASE = "https://raw.githubusercontent.com/PhilouElChapo/PhilCut/main/catalogue/"


def _cache(nom):
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "catalogue")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, nom)


def _livre(nom):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "catalogue", nom)


def _lire(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def telecharger(nom, delai=8):
    """Copie à jour depuis GitHub (rangée en local) ; None si pas de réseau."""
    from .config import VERSION
    try:
        req = urllib.request.Request(BASE + nom, headers={"User-Agent": f"PhilCut/{VERSION}"})
        with urllib.request.urlopen(req, timeout=delai) as r:
            d = json.loads(r.read().decode("utf-8"))
        if not isinstance(d, dict):
            return None
        with open(_cache(nom) + ".part", "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(_cache(nom) + ".part", _cache(nom))
        return d
    except Exception:    # noqa: BLE001 : jamais bloquant
        return None


def charger(nom, reseau=False, delai=8):
    """Le catalogue le plus récent disponible : en ligne (si reseau), sinon la copie locale, sinon celui livré."""
    return (telecharger(nom, delai) if reseau else None) or _lire(_cache(nom)) or _lire(_livre(nom)) or {}


def localise(v):
    """Texte dans la langue de PhilCut quand le catalogue en donne plusieurs (repli : français, puis anglais)."""
    if isinstance(v, dict):
        from . import langue
        return v.get(langue.LANGUE or "fr") or v.get("fr") or v.get("en") or next(iter(v.values()), "")
    return v or ""
