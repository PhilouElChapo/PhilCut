"""Espace PhilCut sur le Drive (0.9.35) : copies légères des médias, créations IA déposées, analyse et nettoyage.

Rangement dans le dossier PhilCut du lieu de synchronisation (dossier du Drive de bureau, ou copie locale du Drive
« en direct », NAS, FTP, que le miroir envoie et reçoit) :
  Medias/<empreinte>_720p.mp4      copies légères (proposées, jamais faites d'office)
  Creations/<empreinte>.<ext>      créations IA déposées (si l'utilisateur l'a permis), avec leur recette .ia.json
  Medias/index.json                {nom: {media, projet, depose, utilise}} : dernière utilisation de chaque fichier

L'analyse classe tout ce qui est dans le dossier PhilCut, propose (cases pré-cochées) ce qui est trop ancien ou
n'est plus utilisé ; rien n'est supprimé sans clic. Les réglages, la session, la bibliothèque et les clefs ne sont
jamais proposés.
"""
import json
import os
import subprocess
import time

from .langue import _

LARGEUR_LEGERE = 1280          # 720p en 16:9 ; la hauteur suit
JOURS_DEFAUT = 90               # au-delà, une copie ou une création non utilisée est proposée à la suppression
GARDES = ("preferences.json", "session.json", "correspondances.json", "secrets", "tampons", "apprentissage",
          "mes_points.json", "effets_perso.json", "bibliotheque")


def racine(params):
    from .bibliotheque import dossier_philcut_drive
    return dossier_philcut_drive(params or {})


def disponible(params):
    return bool(racine(params))


def _index_chemin(params):
    r = racine(params)
    return os.path.join(r, "Medias", "index.json") if r else None


def lire_index(params):
    p = _index_chemin(params)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return {}


def _ecrire_index(params, idx):
    p = _index_chemin(params)
    if not p:
        return
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def noter_utilisation(params, projet):
    """A l'enregistrement d'un projet : ses copies et créations sur le Drive sont « utilisées » aujourd'hui."""
    noms = [m.get("copie_drive") for m in projet.medias if m.get("copie_drive")]
    if not noms or not disponible(params):
        return
    idx = lire_index(params)
    jour = time.strftime("%Y-%m-%d")
    for n in noms:
        e = idx.setdefault(n, {"depose": jour})
        e["utilise"] = jour
        e["projet"] = projet.nom
    _ecrire_index(params, idx)


# ------------------------------------------------------------------ copies légères
def a_copier(projet):
    """Vidéos du projet présentes ici et sans copie légère."""
    return [m for m in projet.medias if m.get("genre") == "video" and os.path.exists(m.get("chemin") or "")
            and not m.get("copie_drive") and not m.get("copie_legere")]


def estimer(medias):
    """Taille approximative des copies légères (environ 2,5 Mbit/s vidéo + son)."""
    duree = sum(float((m.get("fiche") or {}).get("duree") or 0) for m in medias)
    return int(duree * 2_700_000 / 8)


def copier_leger(params, m, progression=None, arret=lambda: False):
    """Fabrique la copie légère 720p d'un média dans PhilCut/Medias ; renvoie son nom (rangé dans m["copie_drive"])."""
    from .moteur import ffmpeg as ffmpeg_bin, _sans_console
    r = racine(params)
    if not r:
        raise RuntimeError(_("Aucun lieu de synchronisation : Préférences › Comptes et synchro."))
    d = os.path.join(r, "Medias")
    os.makedirs(d, exist_ok=True)
    nom = f"{(m.get('empreinte') or m['id'])[:24]}_720p.mp4"
    sortie = os.path.join(d, nom)
    if not os.path.exists(sortie):
        tmp = sortie + ".part.mp4"
        cmd = [ffmpeg_bin(), "-y", "-v", "error", "-i", m["chemin"], "-vf",
               f"scale='if(gt(iw,ih),min({LARGEUR_LEGERE},iw),-2)':'if(gt(iw,ih),-2,min({LARGEUR_LEGERE},ih))'",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
               "-progress", "pipe:1", "-nostats", tmp]
        duree = float((m.get("fiche") or {}).get("duree") or 0) or 1.0
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, **_sans_console())
        for ligne in p.stdout:
            if arret():
                p.kill()
                break
            if ligne.startswith("out_time_us=") and progression:
                try:
                    progression(min(1.0, int(ligne.split("=")[1]) / 1e6 / duree))
                except ValueError:
                    pass
        p.wait()
        if arret() or p.returncode != 0:
            try:
                os.remove(tmp)
            except OSError:
                pass
            if arret():
                return None
            raise RuntimeError(_("Copie légère impossible pour {n}.", n=m.get("nom", "")))
        os.replace(tmp, sortie)
    m["copie_drive"] = nom
    idx = lire_index(params)
    jour = time.strftime("%Y-%m-%d")
    idx[nom] = {"media": m.get("nom", ""), "depose": idx.get(nom, {}).get("depose", jour), "utilise": jour}
    _ecrire_index(params, idx)
    return nom


# ------------------------------------------------------------------ créations IA déposées
def deposer_creation(params, chemin, m=None):
    """Dépose une création IA (et sa recette) dans PhilCut/Creations, pour la reprendre sur un autre appareil sans
    la refaire ni la repayer. Renvoie le nom déposé."""
    import shutil
    from .projet import _empreinte
    r = racine(params)
    if not r or not os.path.exists(chemin):
        return None
    d = os.path.join(r, "Creations")
    os.makedirs(d, exist_ok=True)
    nom = f"{_empreinte(chemin)[:24]}{os.path.splitext(chemin)[1].lower()}"
    cible = os.path.join(d, nom)
    if not os.path.exists(cible):
        shutil.copy2(chemin, cible + ".tmp")
        os.replace(cible + ".tmp", cible)
    recette = chemin + ".ia.json"
    if os.path.exists(recette):
        shutil.copy2(recette, cible + ".ia.json")
    if m is not None:
        m["copie_drive"] = nom
    idx = lire_index(params)
    jour = time.strftime("%Y-%m-%d")
    idx[nom] = {"media": os.path.basename(chemin), "depose": idx.get(nom, {}).get("depose", jour), "utilise": jour, "creation": True}
    _ecrire_index(params, idx)
    return nom


# ------------------------------------------------------------------ analyse et nettoyage
CATEGORIES = {"medias": _("Copies légères des vidéos"), "creations": _("Créations IA déposées"),
              "projets": _("Projets et sauvegardes"), "reglages": _("Réglages, session, bibliothèque, clefs (gardés)"),
              "temporaires": _("Restes de transferts interrompus"), "autres": _("Autres fichiers")}


def _age_jours(date_iso, mtime):
    try:
        t = time.mktime(time.strptime(date_iso[:10], "%Y-%m-%d")) if date_iso else mtime
    except (ValueError, OverflowError):
        t = mtime
    return max(0, int((time.time() - t) / 86400))


def analyser(params, utilises=frozenset(), jours=None):
    """Tout ce qu'il y a dans le dossier PhilCut du lieu de synchronisation :
    [{rel, chemin, taille, categorie, age, raison, proposer}] ; « proposer » = case pré-cochée.
    utilises : noms de copies / créations utilisées par les projets ouverts (jamais proposées)."""
    r = racine(params)
    if not r:
        return []
    jours = int(jours if jours is not None else (params or {}).get("drive_purge_jours", JOURS_DEFAUT) or JOURS_DEFAUT)
    idx = lire_index(params)
    out = []
    for dossier, _sous, fichiers in os.walk(r):
        for f in fichiers:
            chemin = os.path.join(dossier, f)
            rel = os.path.relpath(chemin, r).replace("\\", "/")
            try:
                st = os.stat(chemin)
            except OSError:
                continue
            tete = rel.split("/")[0]
            e = {"rel": rel, "chemin": chemin, "taille": st.st_size, "categorie": "autres", "age": 0, "raison": "", "proposer": False}
            if f.endswith((".tmp", ".part", ".distant", ".part.mp4")):
                e.update(categorie="temporaires", proposer=True, raison=_("transfert interrompu"))
            elif tete in GARDES or rel in GARDES or f in ("index.json",):
                e.update(categorie="reglages", raison=_("indispensable à la synchronisation"))
            elif tete in ("Medias", "Creations"):
                nom = f[:-len(".ia.json")] if f.endswith(".ia.json") else f
                info = idx.get(nom, {})
                e["categorie"] = "medias" if tete == "Medias" else "creations"
                e["age"] = _age_jours(info.get("utilise") or info.get("depose"), st.st_mtime)
                if nom in utilises:
                    e["raison"] = _("utilisé par un projet ouvert")
                elif not info:
                    e.update(proposer=True, raison=_("plus référencé par aucun projet"))
                elif e["age"] >= jours:
                    e.update(proposer=True, raison=_("pas utilisé depuis {n} jours", n=e["age"]))
                else:
                    e["raison"] = _("utilisé il y a {n} jour(s)", n=e["age"]) if e["age"] else _("utilisé aujourd'hui")
                if info.get("projet"):
                    e["raison"] += " — " + info["projet"]
            elif f.endswith(".philcut") or tete in ("Projets", "secours"):
                e["categorie"] = "projets"
                e["age"] = _age_jours("", st.st_mtime)
                e["raison"] = _("modifié il y a {n} jour(s)", n=e["age"])
            else:
                e["age"] = _age_jours("", st.st_mtime)
            out.append(e)
    return sorted(out, key=lambda e: (list(CATEGORIES).index(e["categorie"]), -e["taille"]))


def supprimer(params, rels, progression=None):
    """Supprime ces fichiers du dossier PhilCut, ici ET sur le Drive (Drive en direct, NAS, FTP : à la corbeille quand
    le service en a une). Renvoie (supprimés, octets, erreurs)."""
    r = racine(params)
    if not r:
        return 0, 0, []
    from . import miroir
    compte = miroir.compte_drive(params or {})
    emplacement = None
    if compte:
        from . import distant
        emplacement = distant.emplacement(compte)
    n, octets, erreurs = 0, 0, []
    idx = lire_index(params)
    for i, rel in enumerate(rels):
        local = os.path.join(r, *rel.split("/"))
        try:
            taille = os.path.getsize(local) if os.path.exists(local) else 0
            if emplacement is not None:
                emplacement.supprimer(miroir.racine_distante(compte).rstrip("/") + "/" + rel)
            if os.path.exists(local):
                os.remove(local)
            idx.pop(os.path.basename(rel), None)
            n += 1
            octets += taille
        except Exception as e:      # noqa: BLE001
            erreurs.append((rel, str(e)))
        if progression:
            progression((i + 1) / max(1, len(rels)))
    _ecrire_index(params, idx)
    if compte:                                       # le miroir oublie ces fichiers : ni renvoyés, ni redemandés
        etat_p = os.path.join(miroir.dossier_miroir(compte), "etat.json")
        try:
            with open(etat_p, encoding="utf-8") as f:
                etat = json.load(f)
            for rel in rels:
                if not os.path.exists(os.path.join(r, *rel.split("/"))):
                    etat.pop(rel, None)
            with open(etat_p, "w", encoding="utf-8") as f:
                json.dump(etat, f, indent=1)
        except (OSError, ValueError):
            pass
    return n, octets, erreurs


def taille_lisible(o):
    for u in ("o", "Ko", "Mo", "Go"):
        if o < 1024 or u == "Go":
            return f"{o:.0f} {u}" if u == "o" else f"{o:.1f} {u}".replace(".", ",")
        o /= 1024
    return f"{o:.1f} Go"
