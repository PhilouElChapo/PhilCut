"""Sauvegarde automatique et récupération après plantage (0.9.22).

Toutes les minutes (réglable), chaque projet modifié est copié dans le dossier « secours » des données de PhilCut,
sans toucher au fichier de l'utilisateur : le projet entier (plans, textes, Goodies, sous-titres, réglages), plus son
chemin d'origine et l'heure. Les dernières versions sont gardées (5 par défaut) : on peut revenir à l'une d'elles.

Fermeture normale (enregistré, ou « Ne pas enregistrer » choisi) : les copies de ce projet sont effacées. S'il en reste
au démarrage, c'est que PhilCut ne s'est pas fermé normalement (plantage, coupure de courant, Windows qui redémarre) :
une fenêtre propose de récupérer chaque projet.
"""
import copy
import glob
import json
import os
import time

from .langue import _

INTERVALLES = {1: "1 minute", 2: "2 minutes", 5: "5 minutes", 0: "Jamais"}
INTERVALLE_DEFAUT = 1
VERSIONS_DEFAUT = 5


def dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "secours")
    os.makedirs(d, exist_ok=True)
    return d


def cle(projet):
    """Identifiant stable du projet pour ses copies (créé une fois, gardé dans le projet)."""
    k = projet.d.get("secours_id")
    if not k:
        k = f"p{int(time.time() * 1000) % 10 ** 12}"
        projet.d["secours_id"] = k
    return k


def sauver(projet, versions=VERSIONS_DEFAUT, poste=""):
    """Écrit une copie de secours ; garde les « versions » dernières. Renvoie le chemin écrit."""
    k = cle(projet)
    horo = time.strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(dossier(), f"{k}_{horo}.philcut")
    d = copy.deepcopy(projet.d)
    d["_secours"] = {"origine": projet.chemin or "", "nom": projet.nom, "quand": time.strftime("%Y-%m-%dT%H:%M:%S"), "poste": poste}
    for m in d.get("medias") or []:
        m.pop("proxy", None)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, chemin)
    anciennes = sorted(glob.glob(os.path.join(dossier(), f"{k}_*.philcut")))
    for a in anciennes[:-max(1, int(versions))]:
        try:
            os.remove(a)
        except OSError:
            pass
    return chemin


def effacer(projet):
    """Fermeture normale : plus besoin des copies de ce projet."""
    k = projet.d.get("secours_id")
    if not k:
        return 0
    n = 0
    for a in glob.glob(os.path.join(dossier(), f"{k}_*.philcut")):
        try:
            os.remove(a)
            n += 1
        except OSError:
            pass
    return n


def _lire(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def versions(k):
    """Copies d'un projet, la plus récente d'abord : [{chemin, quand, nom, origine, plans}]."""
    out = []
    for a in sorted(glob.glob(os.path.join(dossier(), f"{k}_*.philcut")), reverse=True):
        d = _lire(a)
        if not d:
            continue
        s = d.get("_secours") or {}
        out.append({"chemin": a, "quand": s.get("quand", ""), "nom": s.get("nom") or d.get("nom", ""), "origine": s.get("origine", ""),
                    "plans": len(d.get("clips") or []), "cle": k})
    return out


def a_recuperer(ouverts=()):
    """Projets laissés par une fermeture anormale (hors projets ouverts en ce moment) : la dernière copie de chacun."""
    vus = {}
    for a in glob.glob(os.path.join(dossier(), "*_*.philcut")):
        k = os.path.basename(a).split("_", 1)[0]
        if k in ouverts:
            continue
        vus.setdefault(k, None)
    out = []
    for k in vus:
        v = versions(k)
        if v:
            r = dict(v[0], nb=len(v))
            # plus récente que le fichier enregistré ? sinon il n'y a rien à récupérer
            o = r["origine"]
            if o and os.path.exists(o):
                d0 = _lire(o) or {}
                r["plus_recent"] = (d0.get("modifie") or "") < r["quand"]
            else:
                r["plus_recent"] = True
            out.append(r)
    out.sort(key=lambda r: r["quand"], reverse=True)
    return out


def recuperer(chemin_copie):
    """Projet rouvert depuis une copie : il reprend son chemin d'origine (Enregistrer écrit là-bas) et reste « modifié »."""
    from .projet import Projet
    p = Projet.ouvrir(chemin_copie)
    s = p.d.pop("_secours", {}) or {}
    p.chemin = s.get("origine") or None
    if s.get("nom"):
        p.nom = s["nom"]
    p.modifie = True
    return p


def jeter(k):
    n = 0
    for a in glob.glob(os.path.join(dossier(), f"{k}_*.philcut")):
        try:
            os.remove(a)
            n += 1
        except OSError:
            pass
    return n


def depuis(quand):
    """« il y a 3 min », « hier à 14h05 »…"""
    import datetime
    try:
        t = datetime.datetime.fromisoformat(quand)
    except (TypeError, ValueError):
        return quand or ""
    s = (datetime.datetime.now() - t).total_seconds()
    if s < 90:
        return _("il y a une minute")
    if s < 3600:
        return _("il y a {n} min", n=int(s // 60))
    if t.date() == datetime.date.today():
        return _("aujourd'hui à {h}", h=t.strftime("%Hh%M"))
    if (datetime.date.today() - t.date()).days == 1:
        return _("hier à {h}", h=t.strftime("%Hh%M"))
    return t.strftime("%d/%m/%Y %Hh%M")
