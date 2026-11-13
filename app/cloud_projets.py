"""Projets et rushes dans vos clouds (0.9.58), sur le modèle de PhilPDF.

Trois rôles de comptes (Préférences › Comptes et synchro › Rôle de chaque compte) :
- réglages et session : le lieu de synchronisation (miroir.py), inchangé ;
- projets : le compte « préféré » (params["compte_prefere"], comme PhilPDF) et son dossier (params["projets_dossier"]) :
  Fichier › Ouvrir un projet depuis un emplacement / Enregistrer le projet vers un emplacement ; un projet ouvert depuis
  un compte y retourne à chaque Enregistrer (copie de travail sur ce poste) ;
- rushes : params["rushs_compte"] et son dossier d'échange (drive_philcut.py) : copies légères (Medias/) et originaux
  (Originaux/) déposés au choix ; sur un autre poste, chaque rush absent se télécharge au choix en copie légère ou en
  original. Ce compte n'est plus reçu d'office (envoi seulement) : rien de lourd n'arrive sans clic.

Aucune suppression sur un compte. Les échanges passent par distant.Emplacement (NAS, FTP, WebDAV, Drives en direct).
"""
import os, posixpath, threading, time

from . import distant
from .langue import _

EXT_PROJET = (".philcut",)
EXT_RUSHES = (".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi", ".mts", ".m2ts", ".3gp", ".mp3", ".wav", ".m4a", ".flac", ".ogg",
              ".aac", ".jpg", ".jpeg", ".png", ".webp", ".heic")


class ConflitDistant(distant.ErreurDistant):
    """Le fichier du compte a changé depuis qu'on l'a ouvert (modifié sur un autre poste)."""

    def __init__(self, date):
        super().__init__(_("Ce projet a été modifié ailleurs depuis son ouverture."))
        self.date = date


# ---------------------------------------------------------------- comptes et dossiers
def compte(params, cid):
    return next((c for c in params.get("comptes", []) if c.get("id") == cid), None) if cid else None


def compte_par_cle(params, cle):
    """Même compte sur un autre poste : même type, même adresse, même utilisateur (distant.cle_compte)."""
    return next((c for c in params.get("comptes", []) if distant.cle_compte(c) == cle), None) if cle else None


def compte_projets(params):
    return distant.prefere(params)


def dossier_projets(params):
    d = "/" + "/".join(p for p in str(params.get("projets_dossier") or "/PhilCut/Projets").split("/") if p)
    return d if d != "/" else "/PhilCut/Projets"


def compte_rushs(params):
    """Le compte des rushes s'il est choisi (même s'il est aussi le lieu de synchronisation), sinon None."""
    return compte(params, params.get("rushs_compte"))


def dossier_rushs(params):
    from .drive_philcut import dossier_rushs as d
    return d(params)


def dossier_cache():
    from .config import dossier_donnees
    return dossier_donnees()


def info_distante(c, chemin, date=""):
    """Ce qu'on retient d'un fichier ouvert depuis un compte : de quoi y renvoyer, et le rouvrir sur un autre poste."""
    return {"compte": c["id"], "cle": distant.cle_compte(c), "chemin": chemin, "lieu": distant.libelle(c), "date": date or ""}


def _date_distante(e, chemin):
    """Repère de version du fichier sur le compte (date|taille), '' s'il n'existe pas ou si on ne peut pas lister."""
    try:
        for x in e.lister(posixpath.dirname(chemin) or "/"):
            if not x.dossier and x.nom == posixpath.basename(chemin):
                return f"{x.date}|{x.taille}"
    except distant.ErreurDistant:
        return ""
    return ""


# ---------------------------------------------------------------- transferts avec progression
def _avec_progression(fonction, local, taille, progression, arret, sens="recu"):
    """Lance fonction() dans un fil et suit la taille du fichier local (téléchargement) : la barre avance vraiment.
    Pour un envoi, la progression vient de l'emplacement s'il la donne, sinon elle reste indéterminée."""
    erreur, fini = [], threading.Event()

    def lancer():
        try:
            fonction()
        except BaseException as e:      # noqa: BLE001
            erreur.append(e)
        finally:
            fini.set()
    threading.Thread(target=lancer, daemon=True).start()
    while not fini.wait(0.25):
        if arret():
            raise InterruptedError(_("Arrêté"))
        if progression and taille and sens == "recu":
            try:
                progression(min(0.99, os.path.getsize(local) / taille))
            except OSError:
                pass
    if erreur:
        raise erreur[0]
    if progression:
        progression(1.0)


def telecharger(e, chemin, local, taille=0, progression=None, arret=lambda: False):
    """Télécharge en passant par un fichier .part (jamais un fichier à moitié à sa place)."""
    os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
    part = local + ".part"
    try:
        _avec_progression(lambda: e.telecharger(chemin, part), part, taille, progression, arret)
    except BaseException:
        try:
            os.remove(part)
        except OSError:
            pass
        raise
    os.replace(part, local)
    return local


def envoyer(e, local, chemin, progression=None, arret=lambda: False):
    """Envoie un fichier (dossiers créés au besoin) ; progression réelle si l'emplacement la donne."""
    # chaque type d'emplacement crée lui-même les dossiers du fichier à l'envoi (0.9.62 : plus d'appel ici, qui créait sur
    # pCloud un DOSSIER du nom du fichier)
    import inspect
    try:
        avec = "progression" in inspect.signature(e.envoyer).parameters
    except (TypeError, ValueError):
        avec = False
    if avec and progression:
        _avec_progression(lambda: e.envoyer(local, chemin, progression=progression), local, 0, None, arret, "envoi")
    else:
        _avec_progression(lambda: e.envoyer(local, chemin), local, 0, None, arret, "envoi")
    if progression:
        progression(1.0)


# ---------------------------------------------------------------- projets
def cache_projet(c, chemin):
    return distant.cache(dossier_cache(), c, chemin)


def ouvrir_projet(params, c, chemin, e=None, progression=None, arret=lambda: False):
    """Télécharge le projet du compte dans sa copie de travail ; renvoie (chemin local, info distante)."""
    e = e or distant.emplacement(c)
    local = cache_projet(c, chemin)
    date = _date_distante(e, chemin)
    try:
        taille = int(date.split("|")[1]) if "|" in date else 0
    except ValueError:
        taille = 0
    telecharger(e, chemin, local, taille, progression, arret)
    info = info_distante(c, chemin, date)
    retenir(params, local, info)
    return local, info


def envoyer_projet(params, local, info, e=None, forcer=False, progression=None, arret=lambda: False):
    """Renvoie la copie de travail à son compte. Si le fichier du compte a changé depuis l'ouverture (autre poste),
    ConflitDistant, sauf forcer=True. Met à jour la date retenue. Renvoie info."""
    c = compte(params, info.get("compte")) or compte_par_cle(params, info.get("cle"))
    if c is None:
        raise distant.ErreurDistant(_("Le compte « {l} » n'existe plus sur ce poste : le projet reste enregistré ici.",
                                      l=info.get("lieu", "")))
    e = e or distant.emplacement(c)
    if not forcer:
        avant = _date_distante(e, info["chemin"])
        if avant and info.get("date") and avant != info["date"]:
            raise ConflitDistant(avant)
    envoyer(e, local, info["chemin"], progression, arret)
    info = dict(info, compte=c["id"], cle=distant.cle_compte(c), date=_date_distante(e, info["chemin"]) or info.get("date", ""),
                envoye=time.strftime("%Y-%m-%dT%H:%M"))
    retenir(params, local, info)
    return info


def retenir(params, local, info):
    """La copie de travail garde son origine (récents, Accueil, session pour les autres postes)."""
    m = dict(params.get("recents_distants") or {})
    m[local] = {k: info.get(k) for k in ("compte", "cle", "chemin", "lieu", "date", "envoye") if info.get(k) is not None}
    garder = set(params.get("recents") or []) | {local}
    params["recents_distants"] = {k: v for k, v in m.items() if k in garder}


def origine(params, local):
    """L'origine distante d'une copie de travail, sinon None."""
    if not local:
        return None
    m = params.get("recents_distants") or {}
    return m.get(local) or next((v for k, v in m.items() if os.path.normcase(k) == os.path.normcase(local)), None)


def chemin_suggere(params, nom):
    return posixpath.join(dossier_projets(params), nom if nom.lower().endswith(".philcut") else nom + ".philcut")


# ---------------------------------------------------------------- rushes
def dossier_originaux(params):
    """Dossier des originaux sur le compte des rushes. Si ce compte est aussi le lieu de synchronisation, ils vont à côté
    du dossier PhilCut synchronisé (« /PhilCut Originaux ») : sinon chaque poste les recevrait d'office."""
    from . import drive_philcut as DP
    if DP.compte_rushs(params) is not None:                # compte à part : envoi seulement, rien n'arrive sans clic
        return posixpath.join(dossier_rushs(params), "Originaux")
    return "/PhilCut Originaux"


def nom_original(m):
    base = os.path.basename(m.get("original") or m.get("chemin") or m.get("nom") or "rush")
    return f"{(m.get('empreinte') or m['id'])[:24]}_{base}"


def a_envoyer_original(projet):
    """Vidéos du projet présentes ici dont l'original n'est pas encore sur le compte des rushes."""
    return [m for m in projet.medias if m.get("genre") in ("video", "audio", "image") and os.path.exists(m.get("chemin") or "")
            and not m.get("copie_legere") and not m.get("original_drive")]


def envoyer_original(params, m, progression=None, arret=lambda: False, e=None):
    """Dépose l'original d'un rush dans « Originaux » du compte des rushes (au choix de l'utilisateur)."""
    c = compte_rushs(params)
    if c is None:
        raise distant.ErreurDistant(_("Choisissez d'abord un compte pour les rushes : Préférences › Comptes et synchro › Rôle de "
                                      "chaque compte."))
    e = e or distant.emplacement(c)
    nom = nom_original(m)
    envoyer(e, m["chemin"], posixpath.join(dossier_originaux(params), nom), progression, arret)
    m["original_drive"] = nom
    return nom


def dispo_rushs(params, e=None):
    """Ce que le compte des rushes propose : {"leger": {nom: taille}, "original": {nom: taille}}."""
    out = {"leger": {}, "original": {}}
    c = compte_rushs(params)
    if c is None:
        return out
    e = e or distant.emplacement(c)
    for genre, dossier in (("leger", posixpath.join(dossier_rushs(params), "Medias")), ("original", dossier_originaux(params))):
        try:
            for x in e.lister(dossier):
                if not x.dossier:
                    out[genre][x.nom] = x.taille
        except distant.ErreurDistant:
            pass
    return out


def choix_possibles(m, dispo):
    """Pour un média absent : [("leger", taille), ("original", taille)] selon ce que le compte des rushes a."""
    out = []
    if m.get("copie_drive") and m["copie_drive"] in dispo.get("leger", {}):
        out.append(("leger", dispo["leger"][m["copie_drive"]]))
    if m.get("original_drive") and m["original_drive"] in dispo.get("original", {}):
        out.append(("original", dispo["original"][m["original_drive"]]))
    return out


def dossier_local_rushs(params):
    """Où arrivent les rushes téléchargés : la copie locale du compte des rushes (Rushes/Medias, Rushes/Originaux)."""
    from . import drive_philcut as DP, miroir
    c = DP.compte_rushs(params)
    if c is not None:
        return os.path.join(miroir.dossier_miroir(c), "Rushes")
    c = compte_rushs(params)
    if c is not None:                                  # compte des rushes = lieu de synchronisation
        return os.path.join(miroir.dossier_miroir(c), "Rushes")
    return os.path.join(dossier_cache(), "rushes_recus")


def telecharger_rush(params, projet, m, genre, progression=None, arret=lambda: False, e=None, taille=0):
    """Télécharge la copie légère ou l'original d'un rush absent, puis le rattache au projet.
    Copie légère : le média garde son original noté (« copie_legere ») ; original : rattaché comme le vrai fichier."""
    c = compte_rushs(params)
    if c is None:
        raise distant.ErreurDistant(_("Aucun compte pour les rushes sur ce poste : Préférences › Comptes et synchro."))
    e = e or distant.emplacement(c)
    if genre == "leger":
        sous, nom, dist = "Medias", m["copie_drive"], posixpath.join(dossier_rushs(params), "Medias")
    else:
        sous, nom, dist = "Originaux", m["original_drive"], dossier_originaux(params)
    local = os.path.join(dossier_local_rushs(params), sous, nom)
    if not os.path.exists(local):
        telecharger(e, posixpath.join(dist, nom), local, taille, progression, arret)
    if genre == "leger":
        m.setdefault("original", m.get("chemin"))
        m["chemin"] = local
        m["copie_legere"] = True
    else:
        from . import liens
        ok, msg = liens.rattacher(projet, m, local, params)
        if not ok:
            liens.rattacher(projet, m, local, params, verifier=False)
        m.pop("copie_legere", None)
    projet.modifie = True
    return local


def importer(params, c, chemins, dossier_local, progression=None, arret=lambda: False, e=None, tailles=None):
    """Télécharge des rushes choisis sur un compte dans dossier_local ; renvoie les chemins locaux."""
    e = e or distant.emplacement(c)
    os.makedirs(dossier_local, exist_ok=True)
    out, n = [], len(chemins)
    for k, ch in enumerate(chemins):
        local = os.path.join(dossier_local, posixpath.basename(ch))
        if not os.path.exists(local):
            telecharger(e, ch, local, (tailles or {}).get(ch, 0),
                        (lambda f, k=k: progression((k + f) / n, posixpath.basename(ch))) if progression else None, arret)
        out.append(local)
    return out


def preparer_dossiers(params):
    """Après les Préférences (0.9.62) : le dossier des projets et celui des rushes existent sur leurs comptes. Renvoie
    [(lieu, dossier, erreur ou None)]."""
    out = []
    for c, d in ((compte_projets(params), dossier_projets(params)), (compte_rushs(params), dossier_rushs(params))):
        if c is None or any(x[0] == distant.libelle(c) and x[1] == d for x in out):
            continue
        try:
            distant.emplacement(c).creer_dossier(d)
            out.append((distant.libelle(c), d, None))
        except Exception as ex:      # noqa: BLE001
            out.append((distant.libelle(c), d, ex))
    return out


def dossier_import(params, c):
    """Dossier local des rushes importés d'un compte : Vidéos/PhilCut — <compte>."""
    from .session import dossier_systeme
    nom = "".join(x for x in distant.libelle(c) if x not in '\\/:*?"<>|').strip() or "cloud"
    return os.path.join(dossier_systeme("videos"), f"PhilCut — {nom}")
