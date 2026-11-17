"""Mises à jour des IA locales (0.9.85) : moteurs et modèles installés comparés au catalogue (packs_ia.manifeste).

Jamais en silence : la liste est proposée (barre du bas, Préférences › IA locale), l'utilisateur coche ce qu'il veut.
Chaque mise à jour se fait à côté de l'ancienne (« .neuf »), l'ancienne est mise de côté (« .ancien ») au moment de
basculer, puis l'essai du genre (essai_ia) est lancé : s'il échoue, l'ancienne version revient toute seule. Après
réussite l'ancienne reste gardée pour un retour arrière, jusqu'à la mise à jour suivante ou « Libérer la place ».

Un modèle « retiré » du catalogue avec un remplaçant est proposé en remplacement : le nouveau s'installe, l'ancien
reste tant qu'on ne le supprime pas."""
import os
import shutil
import time

from . import packs_ia as P
from .langue import _


def _modele_a_jour(cle, e, m):
    """Raison de mettre à jour un modèle installé, ou "" s'il est à jour."""
    d = P.dossier_modele(cle)
    connus = e.get("empreintes") or {}
    noms_catalogue = [f["nom"] for f in m.get("fichiers") or []]
    if sorted(noms_catalogue) != sorted(e.get("fichiers") or []):
        return _("fichiers du modèle changés")
    for f in m.get("fichiers") or []:
        p = os.path.join(d, f["nom"])
        if not os.path.exists(p):
            return _("fichier manquant")
        if f.get("sha256") and connus.get(f["nom"]):
            if connus[f["nom"]] != f["sha256"]:
                return _("nouvelle version")
        elif f.get("taille") and os.path.getsize(p) != f["taille"]:
            return _("nouvelle version")
    if m.get("version") and e.get("version") and m["version"] != e["version"]:
        return _("nouvelle version")
    return ""


def a_mettre_a_jour():
    """Mises à jour disponibles : [{"cle", "type" (moteur, modele, remplacement), "nom", "genre", "avant", "apres",
    "taille", "raison"}], triées par nom."""
    import unicodedata
    out = []
    try:
        man = P.manifeste()
    except Exception:          # noqa: BLE001 : hors ligne et sans copie : rien à proposer
        return []
    etat = P.etat()
    moteurs = man.get("moteurs") or {}
    for k, e in etat.items():
        if not k.startswith("moteur_"):
            continue
        g = k[len("moteur_"):]
        info = (moteurs.get(g) or {})
        neuf = info.get("version", "")
        if neuf and neuf != e.get("version") and info.get(P.systeme()):
            out.append({"cle": g, "type": "moteur", "nom": _("Moteur « {g} »", g=g), "genre": g, "avant": e.get("version") or "?",
                        "apres": neuf, "taille": info[P.systeme()].get("taille", 0), "raison": _("nouvelle version")})
    modeles = P.modeles(avec_essai=True)
    for cle, e in etat.items():
        if cle.startswith("moteur_") or not isinstance(e, dict):
            continue
        m = modeles.get(cle)
        if not m:
            continue
        if m.get("etat") == "retire":
            rempl = m.get("remplace_par")
            if rempl and rempl in modeles and not P.installe(rempl):
                n = modeles[rempl]
                out.append({"cle": cle, "type": "remplacement", "nom": m.get("nom", cle), "genre": m.get("genre", ""),
                            "avant": m.get("nom", cle), "apres": n.get("nom", rempl), "remplace_par": rempl,
                            "taille": sum(f.get("taille", 0) for f in n.get("fichiers") or []),
                            "raison": m.get("message") or _("retiré du catalogue, remplacé")})
            continue
        raison = _modele_a_jour(cle, e, m)
        if raison:
            out.append({"cle": cle, "type": "modele", "nom": m.get("nom", cle), "genre": m.get("genre", ""),
                        "avant": e.get("version") or e.get("date", "?"), "apres": m.get("version") or _("catalogue du jour"),
                        "taille": sum(f.get("taille", 0) for f in m.get("fichiers") or []), "raison": raison})
    net = lambda t: unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()
    return sorted(out, key=lambda x: net(x["nom"]))


# ------------------------------------------------------------------ essai après mise à jour
def _genres_a_essayer(maj):
    from . import essai_ia as EI
    if maj["type"] == "moteur":
        modeles = P.modeles(avec_essai=True)
        gs = []
        for c in P.installes():
            m = modeles.get(c) or {"genre": P.etat().get(c, {}).get("genre")}
            if maj["cle"] in (P.moteur_du_modele(m), P.moteur_gpu_du_modele(m)) and m.get("genre") in EI.ESSAIS:
                gs.append(m["genre"])
        return sorted(set(gs))
    g = maj.get("genre")
    return [g] if g in EI.ESSAIS else []


def essayer(maj, params=None, progression=None, arret=lambda: False):
    """Essai réel du genre touché. Renvoie (ok, message) ; sans essai prévu pour ce genre : (True, "")."""
    from . import essai_ia as EI
    for g in _genres_a_essayer(maj):
        r = EI.tester(g, params, progression, arret)
        if not r.get("ok"):
            return False, r.get("message") or _("essai raté")
    return True, ""


# ------------------------------------------------------------------ moteurs
def _maj_moteur(g, progression, arret):
    info = P.moteur_info(g)
    if not info:
        raise P.ErreurIA(_("Pas de moteur « {g} » pour ce système dans le catalogue.", g=g))
    tmp = os.path.join(P.dossier(), "tmp")
    archive = os.path.join(tmp, info["fichier"])
    source = os.environ.get("PHILCUT_IA_ARCHIVES")
    url = os.path.join(source, info["fichier"]) if source else info["url"]
    P._telecharger(url, archive, info.get("taille", 0), info.get("sha256", ""), progression, arret)
    cible = P.dossier_moteur(g)
    neuf, ancien = cible + ".neuf", cible + ".ancien"
    shutil.rmtree(neuf, ignore_errors=True)
    os.makedirs(neuf, exist_ok=True)
    P.extraire(archive, neuf)
    os.remove(archive)
    exe = os.path.join(neuf, os.path.basename(P.executable(g)))
    if not os.path.exists(exe):
        shutil.rmtree(neuf, ignore_errors=True)
        raise P.ErreurIA(_("Archive du moteur « {g} » incomplète : rien n'a été changé.", g=g))
    if os.name != "nt":
        for f in os.listdir(neuf):
            p = os.path.join(neuf, f)
            if os.path.isfile(p) and not os.path.islink(p):
                os.chmod(p, 0o755)
    shutil.rmtree(ancien, ignore_errors=True)
    if os.path.isdir(cible):
        os.replace(cible, ancien)
    os.replace(neuf, cible)
    avant = P.etat().get(f"moteur_{g}") or {}
    P._noter(f"moteur_{g}", {"genre": g, "version": (P.manifeste().get("moteurs", {}).get(g) or {}).get("version", ""),
                             "date": time.strftime("%Y-%m-%d"), "precedent": {k: v for k, v in avant.items() if k != "precedent"}})


# ------------------------------------------------------------------ modèles
def _maj_modele(cle, progression, arret):
    m = P.modeles(avec_essai=True).get(cle)
    if not m:
        raise P.ErreurIA(_("Modèle inconnu : {c}", c=cle))
    d = P.dossier_modele(cle)
    neuf, ancien = os.path.join(d, ".neuf"), os.path.join(d, ".ancien")
    os.makedirs(neuf, exist_ok=True)
    total = max(1, sum(f.get("taille", 0) for f in m["fichiers"]))
    fait = 0
    for f in m["fichiers"]:
        t = f.get("taille", 0)
        p = (lambda x, t=t, fait=fait: progression and progression(min(0.99, (fait + x * t) / total), m["nom"]))
        _telecharger_ou_garder(f, os.path.join(d, f["nom"]), os.path.join(neuf, f["nom"]), p, arret)
        fait += t
    shutil.rmtree(ancien, ignore_errors=True)
    os.makedirs(ancien, exist_ok=True)
    avant = P.etat().get(cle) or {}
    for nom in avant.get("fichiers") or []:
        p = os.path.join(d, nom)
        if os.path.exists(p):
            os.replace(p, os.path.join(ancien, nom))
    for f in m["fichiers"]:
        os.replace(os.path.join(neuf, f["nom"]), os.path.join(d, f["nom"]))
    shutil.rmtree(neuf, ignore_errors=True)
    P._noter(cle, dict(avant, fichiers=[f["nom"] for f in m["fichiers"]], roles={f["role"]: f["nom"] for f in m["fichiers"]},
                       taille=m.get("taille", 0), date=time.strftime("%Y-%m-%d"), version=m.get("version", ""),
                       empreintes={f["nom"]: f.get("sha256", "") for f in m["fichiers"]},
                       precedent={k: v for k, v in avant.items() if k != "precedent"}))
    if P.dossier_commun():
        from . import ia_partagee as IP
        IP.noter(P.dossier_commun(), cle, P.LOGICIEL,
                 [{"nom": f["nom"], "taille": f.get("taille", 0), "sha256": f.get("sha256", "")} for f in m["fichiers"]])


def _telecharger_ou_garder(f, actuel, cible, progression, arret):
    """Un fichier déjà bon (même empreinte) est recopié tel quel ; sinon il est téléchargé."""
    if os.path.exists(actuel) and f.get("sha256") and P.empreinte(actuel) == f["sha256"]:
        shutil.copy2(actuel, cible)
        return
    src = P.deja_ailleurs(f, verifier=True)
    if src and os.path.realpath(src) != os.path.realpath(actuel):
        shutil.copy2(src, cible)
        return
    P._telecharger(f["url"], cible, f.get("taille", 0), f.get("sha256", ""), progression, arret)


# ------------------------------------------------------------------ appliquer, revenir en arrière
def appliquer(maj, params=None, progression=None, arret=lambda: False):
    """Applique une mise à jour, l'essaie, revient en arrière si l'essai rate. Renvoie un texte de compte rendu ;
    lève ErreurIA si l'essai a raté (l'ancienne version est alors remise)."""
    prog = (lambda part, a, b: (lambda f, t="": progression and progression(a + (b - a) * f, t or part)))
    if maj["type"] == "remplacement":
        P.installer(maj["remplace_par"], prog(maj["apres"], 0.0, 0.85), arret)
        ok, msg = essayer(dict(maj, cle=maj["remplace_par"]), params, prog(_("essai"), 0.85, 1.0), arret)
        if not ok:
            P.supprimer(maj["remplace_par"])
            raise P.ErreurIA(_("Le remplaçant « {n} » a raté son essai ({m}) : l'ancien modèle reste utilisé.", n=maj["apres"], m=msg))
        if params is not None and maj.get("genre"):
            choix = dict(params.get("ia_locale_modeles") or {})
            if choix.get(maj["genre"]) in (None, maj["cle"]):
                choix[maj["genre"]] = maj["remplace_par"]
                params["ia_locale_modeles"] = choix
        return _("« {a} » remplacé par « {n} ». L'ancien reste installé : supprimez-le quand vous voulez.", a=maj["avant"], n=maj["apres"])
    if maj["type"] == "moteur":
        _maj_moteur(maj["cle"], prog(maj["nom"], 0.0, 0.85), arret)
    else:
        _maj_modele(maj["cle"], prog(maj["nom"], 0.0, 0.85), arret)
    ok, msg = essayer(maj, params, prog(_("essai"), 0.85, 1.0), arret)
    if not ok:
        revenir(maj["cle"], maj["type"])
        raise P.ErreurIA(_("« {n} » a raté son essai après la mise à jour ({m}) : l'ancienne version a été remise.", n=maj["nom"], m=msg))
    return _("« {n} » mis à jour et essayé. L'ancienne version est gardée : « Revenir » la remet.", n=maj["nom"])


def revenir(cle, genre_maj):
    """Remet la version d'avant (moteur ou modèle). Renvoie True si c'était possible."""
    if genre_maj == "moteur":
        cible = P.dossier_moteur(cle)
        ancien = cible + ".ancien"
        if not os.path.isdir(ancien):
            return False
        neuf = cible + ".retire"
        shutil.rmtree(neuf, ignore_errors=True)
        if os.path.isdir(cible):
            os.replace(cible, neuf)
        os.replace(ancien, cible)
        shutil.rmtree(neuf, ignore_errors=True)
        e = P.etat().get(f"moteur_{cle}") or {}
        P._noter(f"moteur_{cle}", e.get("precedent") or dict(e, version=""))
        return True
    d = P.dossier_modele(cle)
    ancien = os.path.join(d, ".ancien")
    e = P.etat().get(cle) or {}
    prec = e.get("precedent")
    if not os.path.isdir(ancien) or not prec:
        return False
    for nom in e.get("fichiers") or []:
        p = os.path.join(d, nom)
        if os.path.exists(p) and nom not in (prec.get("fichiers") or []):
            os.remove(p)
    for nom in os.listdir(ancien):
        os.replace(os.path.join(ancien, nom), os.path.join(d, nom))
    shutil.rmtree(ancien, ignore_errors=True)
    P._noter(cle, prec)
    return True


def gardes():
    """Anciennes versions gardées pour un retour arrière : [(cle, type, nom, octets)]."""
    out = []
    for k, e in P.etat().items():
        if k.startswith("moteur_"):
            g = k[len("moteur_"):]
            a = P.dossier_moteur(g) + ".ancien"
            if os.path.isdir(a):
                out.append((g, "moteur", _("Moteur « {g} »", g=g), P.taille_dossier(a)))
        elif isinstance(e, dict):
            a = os.path.join(P.dossier_modele(k), ".ancien")
            if os.path.isdir(a) and e.get("precedent"):
                out.append((k, "modele", e.get("nom", k), P.taille_dossier(a)))
    return out


def liberer():
    """Efface les anciennes versions gardées. Renvoie les octets libérés."""
    total = 0
    for cle, genre_maj, _n, octets in gardes():
        a = P.dossier_moteur(cle) + ".ancien" if genre_maj == "moteur" else os.path.join(P.dossier_modele(cle), ".ancien")
        shutil.rmtree(a, ignore_errors=True)
        total += octets
        k = f"moteur_{cle}" if genre_maj == "moteur" else cle
        e = P.etat().get(k)
        if e and "precedent" in e:
            e.pop("precedent")
            P._noter(k, e)
    return total
