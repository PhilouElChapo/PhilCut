"""Liens virtuels (0.9.35) : un média du projet est reconnu sur chaque appareil, même renommé ou déplacé.

Chaque média garde :
  - son empreinte (taille + début et fin du fichier, voir projet._empreinte) ;
  - ses emplacements connus par appareil : {machine: {chemin, nom, taille, modifie, relatif_maison, connu, relatif_connu}} ;
  - en option, une copie légère 720p sur le Drive (« copie_drive » : nom du fichier dans PhilCut/Medias).

A l'ouverture, un média absent est cherché : emplacement connu ici → même fichier ailleurs (dossiers par défaut,
dossier utilisateur, dossiers déjà appris : session.retrouver_direct) → copie légère du Drive → sinon il reste
« manquant », intact, et « Où est ce fichier ? » permet de le rattacher. Rien n'est deviné ni supprimé.
"""
import os
import time

from .langue import _


def machine(params=None):
    import platform
    return (params or {}).get("machine") or platform.node() or "Ce PC"


def decrire(chemin, empreinte="", params=None):
    """Ce qu'il faut pour retrouver ce fichier sur un autre appareil (jamais le fichier lui-même)."""
    from .session import _relatif, dossiers_connus, empreinte as empreinte_session
    try:
        st = os.stat(chemin)
    except OSError:
        return None
    e = {"chemin": chemin, "nom": os.path.basename(chemin), "taille": st.st_size, "modifie": int(st.st_mtime),
         "empreinte": empreinte_session(chemin), "relatif_maison": _relatif(chemin, os.path.expanduser("~")) or ""}
    try:
        for clef, base in sorted(dossiers_connus(params).items(), key=lambda kv: -len(kv[1])):
            rel = _relatif(chemin, base)
            if rel:
                e["connu"], e["relatif_connu"] = clef, rel
                break
    except Exception:      # noqa: BLE001
        pass
    return e


def noter(d, params=None):
    """Avant l'écriture du projet : révision, appareil, et emplacement de chaque média présent ici."""
    ici = machine(params)
    d["revision"] = int(d.get("revision") or 0) + 1
    d["appareil"] = ici
    d.setdefault("appareils", {})[ici] = time.strftime("%Y-%m-%dT%H:%M:%S")
    for m in d.get("medias") or []:
        ch = m.get("chemin") or ""
        if ch and os.path.exists(ch) and not m.get("copie_legere"):
            if not m.get("recette") and os.path.exists(ch + ".ia.json"):     # la recette voyage avec le projet (0.9.37)
                try:
                    from .recettes_ia import noter_recette
                    noter_recette(m, ch)
                except Exception:      # noqa: BLE001
                    pass
            ancien = (m.get("emplacements") or {}).get(ici)
            try:
                st = os.stat(ch)
            except OSError:
                continue
            if ancien and ancien.get("chemin") == ch and ancien.get("taille") == st.st_size and ancien.get("modifie") == int(st.st_mtime):
                continue                                  # rien n'a changé : pas de relecture
            e = decrire(ch, m.get("empreinte", ""), params)
            if e:
                m.setdefault("emplacements", {})[ici] = e


def copie_drive(params, m):
    """Chemin local de la copie légère de ce média sur le Drive, si elle est là."""
    nom = m.get("copie_drive")
    if not nom:
        return None
    from .bibliotheque import dossier_philcut_drive
    base = dossier_philcut_drive(params or {})
    if not base:
        return None
    for sous in ("Medias", "Creations"):
        p = os.path.join(base, sous, nom)
        if os.path.isfile(p):
            return p
    return None


def retrouver(projet, params=None, chercher_disque=False, arret=lambda: False):
    """Rattache les médias absents. Renvoie {"trouves": [(m, comment)], "copies": [m], "manquants": [m]}.
    Un média retrouvé par sa copie légère garde son original dans « original » et est marqué « copie_legere »."""
    res = {"trouves": [], "copies": [], "manquants": []}
    absents = [m for m in projet.medias if not os.path.exists(m.get("chemin") or "")]
    if not absents:
        return res
    ici = machine(params)
    try:
        from .session import session_de
        s = session_de(params) if params is not None else None
    except Exception:      # noqa: BLE001
        s = None
    restants = []
    for m in absents:
        trouve = None
        emp = m.get("emplacements") or {}
        if ici in emp and os.path.exists(emp[ici].get("chemin") or ""):
            trouve = (emp[ici]["chemin"], _("emplacement connu sur ce poste"))
        if not trouve and s is not None:
            for autre, e in emp.items():
                if autre == ici:
                    continue
                e = dict(e)
                try:
                    ch, comment = s.retrouver_direct(autre, e)
                except Exception:      # noqa: BLE001
                    ch, comment = None, None
                if ch and os.path.exists(ch):
                    trouve = (ch, comment)
                    break
        if trouve:
            m["chemin"] = trouve[0]
            m.pop("copie_legere", None)
            res["trouves"].append((m, trouve[1]))
        else:
            restants.append(m)
    if chercher_disque and restants and s is not None:
        par_machine = {}
        for m in restants:
            emp = m.get("emplacements") or {}
            autre = next((k for k in emp if k != ici), None)
            if autre:
                par_machine.setdefault(autre, []).append(m)
        for autre, ms in par_machine.items():
            fichiers = [dict(m["emplacements"][autre]) for m in ms]
            try:
                trouves = s.retrouver_tous(autre, fichiers, arret=arret, delai=20)
            except Exception:      # noqa: BLE001
                trouves = [(None, None)] * len(ms)
            for m, (ch, comment) in zip(ms, trouves):
                if ch and os.path.exists(ch):
                    m["chemin"] = ch
                    res["trouves"].append((m, comment))
        restants = [m for m in restants if not os.path.exists(m.get("chemin") or "")]
    for m in restants:
        c = copie_drive(params, m)
        if c:
            m.setdefault("original", m.get("chemin"))
            m["chemin"] = c
            m["copie_legere"] = True
            res["copies"].append(m)
        else:
            res["manquants"].append(m)
    return res


def rattacher(projet, m, chemin, params=None, verifier=True):
    """« Où est ce fichier ? » : rattache le média à ce fichier. Renvoie (ok, message). Si l'empreinte ne correspond
    pas, ok=False et le message le dit (l'utilisateur peut forcer avec verifier=False)."""
    from .projet import _empreinte
    if verifier and m.get("empreinte"):
        e = _empreinte(chemin)
        if e and e != m["empreinte"]:
            return False, _("Ce fichier n'est pas le même que l'original (contenu différent). Le rattacher quand même ?")
    ancien = m.get("chemin")
    m["chemin"] = chemin
    m.pop("copie_legere", None)
    m["nom"] = m.get("nom") or os.path.basename(chemin)
    # le dossier est appris : les autres médias du même dossier d'origine seront retrouvés tout seuls
    try:
        from .session import session_de
        s = session_de(params)
        emp = m.get("emplacements") or {}
        autre = next((k for k in emp if k != machine(params)), None)
        if autre:
            s.apprendre(autre, os.path.dirname(emp[autre]["chemin"]).replace("\\", "/"), os.path.dirname(chemin))
    except Exception:      # noqa: BLE001
        pass
    autres = 0
    if ancien:
        base_ancienne, base_nouvelle = os.path.dirname(ancien), os.path.dirname(chemin)
        for x in projet.medias:
            if x is m or os.path.exists(x.get("chemin") or ""):
                continue
            if os.path.dirname(x.get("chemin") or "") == base_ancienne:
                cand = os.path.join(base_nouvelle, os.path.basename(x["chemin"]))
                if os.path.isfile(cand) and (not x.get("empreinte") or _empreinte(cand) == x["empreinte"]):
                    x["chemin"] = cand
                    autres += 1
    return True, (_("Rattaché ; {n} autre(s) média(s) du même dossier retrouvé(s) aussi.", n=autres) if autres else _("Rattaché."))
