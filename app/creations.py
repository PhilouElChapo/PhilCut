"""Ce qui a servi à créer un fichier par l'IA (0.9.19) : rangé à côté du fichier (« musique.mp3.ia.json »), pour pouvoir
rouvrir l'Atelier IA avec la même phrase, les mêmes paroles, la même durée, et refaire ou modifier la création."""
import json
import os


def chemin_recette(fichier):
    return f"{fichier}.ia.json"


def ecrire(fichier, recette):
    try:
        with open(chemin_recette(fichier), "w", encoding="utf-8") as f:
            json.dump(recette, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def lire(fichier):
    try:
        with open(chemin_recette(fichier), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return None


def copier(source, cible):
    """Copie le fichier (et sa recette) ; renvoie la cible."""
    import shutil
    shutil.copy2(source, cible)
    if os.path.exists(chemin_recette(source)):
        shutil.copy2(chemin_recette(source), chemin_recette(cible))
    return cible


# ------------------------------------------------------------------ dossier des créations et nettoyage (0.9.20)
DUREES = {0: "Jamais", 30: "30 jours", 90: "90 jours", 365: "1 an"}
DUREE_DEFAUT = 90


def dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "ia_creations")
    os.makedirs(d, exist_ok=True)
    return d


def _fichiers():
    d = dossier()
    for n in os.listdir(d):
        p = os.path.join(d, n)
        if os.path.isfile(p) and not n.endswith(".ia.json") and not n.startswith("_"):
            yield p


def taille():
    """(nombre de créations, octets, recettes comprises)."""
    n = o = 0
    for p in _fichiers():
        n += 1
        o += os.path.getsize(p) + (os.path.getsize(chemin_recette(p)) if os.path.exists(chemin_recette(p)) else 0)
    return n, o


def en_usage(params=None, projets=()):
    """Chemins de fichiers utilisés par les projets récents (enregistrés) et par les projets ouverts."""
    vus = set()
    chemins = list((params or {}).get("recents") or [])
    for c in chemins:
        if not str(c).lower().endswith(".philcut") or not os.path.exists(c):
            continue
        try:
            with open(c, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        for m in d.get("medias") or []:
            if m.get("chemin"):
                vus.add(os.path.normcase(os.path.abspath(m["chemin"])))
    for pr in projets:
        for m in getattr(pr, "medias", []) or []:
            if m.get("chemin"):
                vus.add(os.path.normcase(os.path.abspath(m["chemin"])))
    return vus


def nettoyer(jours, utilises=frozenset(), maintenant=None):
    """Supprime les créations plus vieilles que « jours » qu'aucun projet n'utilise ; renvoie (nombre, octets libérés)."""
    import time
    if not jours:
        return 0, 0
    limite = (maintenant or time.time()) - float(jours) * 86400
    n = o = 0
    for p in list(_fichiers()):
        if os.path.getmtime(p) >= limite or os.path.normcase(os.path.abspath(p)) in utilises:
            continue
        for q in (p, chemin_recette(p)):
            if os.path.exists(q):
                o += os.path.getsize(q)
                try:
                    os.remove(q)
                except OSError:
                    continue
        n += 1
    return n, o
