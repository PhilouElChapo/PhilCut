"""IA partagées entre les logiciels PhilFactory (0.9.46) : brique commune à PhilCut, PhilMusic, PhilPic…

Un modèle d'IA locale (plusieurs Go) n'est téléchargé qu'une fois pour tous les logiciels :
- un dossier commun « IA PhilFactory », choisi par l'utilisateur : modeles/<clef>/<fichiers> ; à sa racine,
  « philfactory-ia.json » (l'index : quels modèles, leurs empreintes, quels logiciels s'en servent) ;
- un fichier de rendez-vous FACULTATIF dans le profil (PhilFactory/ia.json) : il dit où est le dossier commun, pour qu'un
  logiciel installé plus tard le trouve tout de suite. Case « Partager mes IA avec les autres logiciels PhilFactory » :
  une version portable n'écrit rien dans le profil tant qu'elle n'est pas cochée ;
- sans rendez-vous, chaque logiciel regarde aussi à côté de lui (portables rangés côte à côte) et dans les dossiers de
  données des autres logiciels Phil… ;
- un fichier n'est repris que s'il est exactement celui attendu (taille, puis empreinte SHA-256 quand le catalogue la
  donne) ; une autre version se télécharge à part ;
- rien ne disparaît en silence : un modèle encore utilisé par un autre logiciel n'est jamais effacé.

Rien ici ne dépend de PhilCut : le nom du logiciel est passé en paramètre.
"""
import json
import os
import shutil
import sys
import time

INDEX = "philfactory-ia.json"
NOM_DOSSIER = "IA PhilFactory"


# ------------------------------------------------------------------ rendez-vous (profil, facultatif)
def fichier_rdv():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "PhilFactory", "ia.json")


def _lire(p):
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ecrire(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def lire_rdv():
    return _lire(fichier_rdv())


def annoncer(commun, logiciel, version="", programme=""):
    """Note dans le profil où est le dossier commun et quel logiciel s'en sert (seulement si l'utilisateur partage)."""
    d = lire_rdv()
    d["dossier"] = commun
    d.setdefault("logiciels", {})[logiciel] = {"version": version, "programme": programme, "vu": time.strftime("%Y-%m-%d")}
    _ecrire(fichier_rdv(), d)


def retirer_rdv(logiciel):
    d = lire_rdv()
    if logiciel in (d.get("logiciels") or {}):
        d["logiciels"].pop(logiciel)
        _ecrire(fichier_rdv(), d)


# ------------------------------------------------------------------ où chercher
def dossier_propose(programme, portable):
    """Portable : à côté des logiciels (C:\\Prog\\Windows\\IA PhilFactory) ; installé : le dossier de données commun."""
    if portable:
        return os.path.join(os.path.dirname(os.path.abspath(programme)), NOM_DOSSIER)
    if sys.platform == "win32":
        return os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "PhilFactory", "IA")
    return os.path.join(os.path.expanduser("~/.local/share"), "PhilFactory", "IA")


def communs_connus(programme=""):
    """Dossiers communs déjà créés par un logiciel PhilFactory : celui du rendez-vous, celui à côté des portables."""
    out = []
    d = lire_rdv().get("dossier")
    if d:
        out.append(d)
    if programme:
        out.append(os.path.join(os.path.dirname(os.path.abspath(programme)), NOM_DOSSIER))
    for p in (dossier_propose(programme or ".", False),):
        out.append(p)
    vus, res = set(), []
    for p in out:
        k = os.path.normcase(os.path.abspath(p))
        if k not in vus and os.path.isfile(os.path.join(p, INDEX)):
            vus.add(k)
            res.append(p)
    return res


def racines_modeles(programme="", commun=None, propre=None):
    """Tous les dossiers « modeles » où un logiciel PhilFactory a pu ranger des modèles : le dossier commun, ceux des
    autres logiciels Phil… à côté de celui-ci (portables) et dans les dossiers de données du profil."""
    cands = []
    if commun:
        cands.append(os.path.join(commun, "modeles"))
    for c in communs_connus(programme):
        cands.append(os.path.join(c, "modeles"))
    if programme:
        parent = os.path.dirname(os.path.abspath(programme))
        try:
            voisins = [os.path.join(parent, n) for n in os.listdir(parent) if n.lower().startswith("phil")]
        except OSError:
            voisins = []
        for v in voisins:
            cands += [os.path.join(v, "donnees", "ia", "modeles"), os.path.join(v, "ia", "modeles")]
    bases = [os.environ.get("APPDATA") or "", os.path.expanduser("~/.config")] if sys.platform == "win32" else \
        [os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")]
    for b in filter(None, bases):
        try:
            noms = [n for n in os.listdir(b) if n.lower().startswith("phil")]
        except OSError:
            noms = []
        cands += [os.path.join(b, n, "ia", "modeles") for n in noms]
    vus, res = set(), []
    exclu = os.path.normcase(os.path.abspath(propre)) if propre else None
    for p in cands:
        k = os.path.normcase(os.path.abspath(p))
        if k in vus or k == exclu or not os.path.isdir(p):
            continue
        vus.add(k)
        res.append(p)
    return res


def empreinte(chemin):
    import hashlib
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def chercher_fichier(nom, taille, sha256, racines, verifier=True):
    """Un fichier de modèle déjà présent ailleurs : même nom, même taille et, si le catalogue la donne, même empreinte."""
    for r in racines:
        try:
            cles = os.listdir(r)
        except OSError:
            continue
        for c in cles:
            p = os.path.join(r, c, nom)
            try:
                if not os.path.isfile(p) or (taille and os.path.getsize(p) != int(taille)):
                    continue
            except OSError:
                continue
            if verifier and sha256 and len(sha256) == 64 and empreinte(p) != sha256.lower():
                continue
            return p
    return None


def placer(src, cible, progression=None, arret=lambda: False):
    """Met le fichier à sa place dans le dossier commun : lien (instantané, sans doublon) sur le même disque, sinon copie."""
    os.makedirs(os.path.dirname(cible), exist_ok=True)
    if os.path.exists(cible):
        return cible
    try:
        os.link(src, cible)
        return cible
    except OSError:
        pass
    _copier(src, cible, progression, arret)
    return cible


def _copier(src, cible, progression=None, arret=lambda: False):
    total, fait = os.path.getsize(src), 0
    part = cible + ".part"
    with open(src, "rb") as a, open(part, "wb") as b:
        while True:
            if arret():
                b.close()
                os.remove(part)
                raise InterruptedError()
            bloc = a.read(8 << 20)
            if not bloc:
                break
            b.write(bloc)
            fait += len(bloc)
            if progression and total:
                progression(fait / total)
    if os.path.getsize(part) != total:
        os.remove(part)
        raise OSError("copie incomplète : " + os.path.basename(src))
    shutil.copystat(src, part)
    os.replace(part, cible)


# ------------------------------------------------------------------ index du dossier commun
def index(commun):
    return _lire(os.path.join(commun, INDEX))


def noter(commun, cle, logiciel, fichiers=None, utilise=True):
    """L'index du dossier commun : quels logiciels se servent de ce modèle (et ses fichiers, avec leur empreinte)."""
    d = index(commun)
    d.setdefault("format", 1)
    m = d.setdefault("modeles", {}).setdefault(cle, {"logiciels": []})
    if fichiers is not None:
        m["fichiers"] = fichiers
    ls = set(m.get("logiciels") or [])
    (ls.add if utilise else ls.discard)(logiciel)
    m["logiciels"] = sorted(ls)
    m["maj"] = time.strftime("%Y-%m-%d %H:%M")
    _ecrire(os.path.join(commun, INDEX), d)
    return m["logiciels"]


def autres_utilisateurs(commun, cle, logiciel):
    m = (index(commun).get("modeles") or {}).get(cle) or {}
    return [x for x in (m.get("logiciels") or []) if x != logiciel]


def preparer(commun, logiciel):
    """Crée le dossier commun et son index (s'il n'existe pas)."""
    os.makedirs(os.path.join(commun, "modeles"), exist_ok=True)
    d = index(commun)
    if not d:
        _ecrire(os.path.join(commun, INDEX), {"format": 1, "cree_par": logiciel, "cree_le": time.strftime("%Y-%m-%d"), "modeles": {}})


# ------------------------------------------------------------------ transition : ranger les modèles déjà téléchargés
def a_transferer(source):
    """(nombre de fichiers, octets) des modèles d'un logiciel encore rangés dans son propre dossier."""
    n, octets = 0, 0
    for base, _d, fichiers in os.walk(source):
        for f in fichiers:
            if f.endswith((".part", ".tmp")):
                continue
            n += 1
            try:
                octets += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
    return n, octets


def transferer(source, commun, logiciel, progression=None, arret=lambda: False):
    """Déplace les modèles d'un logiciel (source = son dossier « modeles ») dans le dossier commun.
    Même disque : déplacement instantané. Autre disque : copie vérifiée (taille), puis suppression de l'original.
    Un fichier déjà dans le dossier commun avec la même taille (téléchargé par un autre logiciel) n'est pas recopié :
    l'exemplaire en double est supprimé. Renvoie (fichiers rangés, octets libérés en double)."""
    preparer(commun, logiciel)
    dest = os.path.join(commun, "modeles")
    n_total, o_total = a_transferer(source)
    fait, ranges, doubles = 0, 0, 0
    try:
        cles = sorted(os.listdir(source))
    except OSError:
        cles = []
    for cle in cles:
        dsrc = os.path.join(source, cle)
        if not os.path.isdir(dsrc):
            continue
        noms = []
        for nom in sorted(os.listdir(dsrc)):
            src = os.path.join(dsrc, nom)
            if not os.path.isfile(src) or nom.endswith((".part", ".tmp")):
                continue
            if arret():
                raise InterruptedError()
            taille = os.path.getsize(src)
            cible = os.path.join(dest, cle, nom)
            os.makedirs(os.path.dirname(cible), exist_ok=True)
            if os.path.exists(cible) and os.path.getsize(cible) == taille:
                os.remove(src)                                 # déjà là (autre logiciel) : le double part
                doubles += taille
            else:
                try:
                    os.replace(src, cible)                     # même disque : instantané
                except OSError:
                    _copier(src, cible, (lambda f, base=fait, t=taille: progression and progression(
                        (base + f * t) / max(1, o_total), nom)), arret)
                    os.remove(src)
            fait += taille
            ranges += 1
            noms.append(nom)
            if progression:
                progression(fait / max(1, o_total), nom)
        if noms:
            noter(commun, cle, logiciel, [{"nom": x} for x in noms])
        try:
            os.rmdir(dsrc)
        except OSError:
            pass
    return ranges, doubles
