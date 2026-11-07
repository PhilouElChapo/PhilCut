"""Aérodromes du monde (0.9.18) : la liste libre d'OurAirports (domaine public, ourairports.com), téléchargée une fois
à la demande (environ 12 Mo, gardée en version réduite, environ 2 Mo), et vos propres points enregistrés. Recherche par
code OACI, nom ou ville, sans accents ni majuscules. Sans téléchargement, la petite liste intégrée (aviation.AERODROMES)
reste utilisable."""
import csv
import io
import json
import os
import unicodedata

from .langue import _

URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
TYPES = {"large_airport", "medium_airport", "small_airport", "seaplane_base", "heliport"}
_LISTE = None


def _fichier():
    from .config import dossier_donnees
    return os.path.join(dossier_donnees(), "aerodromes.json")


def _points_fichier(params=None):
    """Mes points : dans le dossier synchronisé s'il existe (ils suivent sur vos autres postes), sinon local."""
    try:
        from .bibliotheque import dossier_philcut_drive
        d = dossier_philcut_drive(params or {})
    except Exception:      # noqa: BLE001
        d = None
    if not d:
        from .config import dossier_donnees
        d = dossier_donnees()
    return os.path.join(d, "mes_points.json")


def installe():
    return os.path.exists(_fichier())


def telecharger(progression=None, arret=lambda: False):
    """Télécharge la liste d'OurAirports et en garde l'essentiel : code, nom, ville, pays, latitude, longitude, type."""
    global _LISTE
    import urllib.request
    from .config import VERSION
    req = urllib.request.Request(URL, headers={"User-Agent": f"PhilCut/{VERSION} (+https://github.com/PhilouElChapo/PhilCut)"})
    morceaux, fait = [], 0
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get("Content-Length") or 0)
        while True:
            if arret():
                raise InterruptedError()
            b = r.read(1 << 16)
            if not b:
                break
            morceaux.append(b)
            fait += len(b)
            if progression:
                progression(fait / total if total else 0.0)
    out = lire_csv(b"".join(morceaux).decode("utf-8", "replace"))
    with open(_fichier() + ".part", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(_fichier() + ".part", _fichier())
    _LISTE = out
    return len(out)


def lire_csv(texte):
    out = []
    for l in csv.DictReader(io.StringIO(texte)):
        if l.get("type") not in TYPES:
            continue
        try:
            la, lo = float(l["latitude_deg"]), float(l["longitude_deg"])
        except (TypeError, ValueError):
            continue
        code = l.get("icao_code") or l.get("gps_code") or l.get("ident") or ""
        out.append([code, l.get("name") or "", l.get("municipality") or "", l.get("iso_country") or "", round(la, 5), round(lo, 5),
                    l.get("type")[0]])
    return out


def liste():
    global _LISTE
    if _LISTE is None:
        try:
            with open(_fichier(), encoding="utf-8") as f:
                _LISTE = json.load(f)
        except (OSError, ValueError):
            from .aviation import AERODROMES
            _LISTE = [[c, n, "", "", la, lo, "s"] for c, n, la, lo in AERODROMES]
    return _LISTE


def _net(t):
    return unicodedata.normalize("NFKD", str(t).lower()).encode("ascii", "ignore").decode()


def chercher(texte, n=40, pays=None):
    """Aérodromes dont le code, le nom ou la ville contiennent les mots ; le code exact d'abord."""
    mots = _net(texte).split()
    if not mots:
        return []
    exact, autres = [], []
    for a in liste():
        if a[0].lower() == mots[0] and len(mots) == 1:
            exact.append(a)
            continue
        cle = _net(f"{a[0]} {a[1]} {a[2]}")
        if all(m in cle for m in mots):
            autres.append(a)
    autres.sort(key=lambda a: (pays is not None and a[3] != pays, a[6] not in "lms", a[1]))
    return (exact + autres)[:n]


def etape(a):
    """Entrée de la liste → étape du trajet."""
    nom = f"{a[0]} {a[1]}".strip()
    return {"nom": nom, "code": a[0], "lat": float(a[4]), "lon": float(a[5])}


def libelle(a):
    lieu = ", ".join(x for x in (a[2], a[3]) if x)
    return f"{a[0]}  {a[1]}" + (f"  ({lieu})" if lieu else "")


# ------------------------------------------------------------------ mes points
def mes_points(params=None):
    try:
        with open(_points_fichier(params), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def enregistrer_point(params, nom, lat, lon):
    pts = [p for p in mes_points(params) if p.get("nom") != nom]
    pts.append({"nom": nom, "lat": round(float(lat), 5), "lon": round(float(lon), 5)})
    with open(_points_fichier(params), "w", encoding="utf-8") as f:
        json.dump(pts, f, ensure_ascii=False, indent=1)
    return pts


def retirer_point(params, nom):
    pts = [p for p in mes_points(params) if p.get("nom") != nom]
    with open(_points_fichier(params), "w", encoding="utf-8") as f:
        json.dump(pts, f, ensure_ascii=False, indent=1)
    return pts
