"""Bibliothèque musicale libre (cahier des charges 10.8) : recherche dans Openverse (musiques sous licence Creative
Commons de Jamendo, ccMixter, Freesound…), seulement les licences compatibles avec une vidéo publiée, y compris
monétisée : CC0, domaine public, CC BY, CC BY-SA. Téléchargement à la demande dans votre dossier de musiques, avec la
mention de crédit à recopier (PhilCut l'ajoute à la description YouTube). Sans clef ni compte."""
import json, os, re, time, urllib.parse, urllib.request

from .langue import _

API = "https://api.openverse.org/v1/audio/"


def _agent():
    """Identité HTTP sobre (ASCII, version, adresse du projet) : le pare-feu d'Openverse refuse les autres."""
    from .config import VERSION
    return {"User-Agent": f"PhilCut/{VERSION} (+https://github.com/PhilouElChapo/PhilCut)"}
LICENCES = "cc0,pdm,by,by-sa"          # NC (pas d'usage commercial) et ND (pas de modification) exclues
AMBIANCES = [("energique", _("Energique"), "upbeat energetic"), ("cinema", _("Cinéma"), "cinematic epic"),
             ("calme", _("Calme"), "calm ambient relaxing"), ("joyeuse", _("Joyeuse"), "happy cheerful"),
             ("electro", _("Electro"), "electronic"), ("acoustique", _("Acoustique"), "acoustic guitar"),
             ("piano", _("Piano"), "piano"), ("aventure", _("Aventure, vol"), "adventure inspiring")]


class ErreurMusique(Exception):
    pass


def chercher(texte="", ambiance=None, longueur=None, page=1, taille=20):
    """Morceaux trouvés : [{"id", "titre", "auteur", "url", "duree", "licence", "attribution", "page", "source", "tags"}].
    longueur : short (< 30 s) | medium (30 s - 2 min) | long (> 2 min)."""
    q = " ".join(x for x in (texte.strip(), dict((k, m) for k, _l, m in AMBIANCES).get(ambiance, "")) if x) or "music"
    params = {"q": q, "license": LICENCES, "category": "music", "page_size": taille, "page": page, "mature": "false"}
    if longueur:
        params["length"] = longueur
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=_agent())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise ErreurMusique(_("Trop de recherches d'un coup : réessayez dans une minute.")) from e
        raise ErreurMusique(_("Bibliothèque injoignable (HTTP {c}).", c=e.code)) from e
    except Exception as e:      # noqa: BLE001
        raise ErreurMusique(_("Bibliothèque injoignable : {e}", e=e)) from e
    out = []
    for x in d.get("results") or []:
        if not x.get("url"):
            continue
        lic = (x.get("license") or "").lower()
        if lic not in LICENCES.split(","):
            continue
        version = x.get("license_version") or ""
        out.append({"id": x.get("id"), "titre": x.get("title") or _("Sans titre"), "auteur": x.get("creator") or "?",
                    "url": x["url"], "duree": (x.get("duration") or 0) / 1000.0, "licence": f"CC {lic.upper()} {version}".replace("CC CC0", "CC0").replace("CC PDM", _("Domaine public")).strip(),
                    "attribution": x.get("attribution") or credit_texte(x), "page": x.get("foreign_landing_url") or "",
                    "source": x.get("source") or x.get("provider") or "", "type": (x.get("filetype") or "mp3").lower(),
                    "tags": [t.get("name") for t in (x.get("tags") or []) if isinstance(t, dict) and t.get("name")][:8]})
    return out


def credit_texte(x):
    titre = x.get("title") or x.get("titre") or ""
    auteur = x.get("creator") or x.get("auteur") or ""
    lic = (x.get("license") or "").upper()
    return f"« {titre} » par {auteur}, licence CC {lic} {x.get('license_version') or ''}".strip()


def dossier(params, creer=True):
    """Dossier où arrivent les musiques libres téléchargées : celui choisi (retenu), sinon Musique › PhilCut - musiques libres.
    creer=False : seulement le nom, sans toucher au disque (affichage ; un disque réseau absent ne gèle rien)."""
    d = (params or {}).get("musiques_telechargement") or ""
    if not d:
        from .session import dossier_systeme
        d = os.path.join(dossier_systeme("musique"), "PhilCut - musiques libres")
    if not creer:
        return d
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        from .config import dossier_donnees
        d = os.path.join(dossier_donnees(), "musiques")
        os.makedirs(d, exist_ok=True)
    return d


# ------------------------------------------------------------------ mon dossier de musiques : par dossier, album, artiste
CLASSEMENTS = (("dossier", _("Par dossier")), ("album", _("Par album")), ("artiste", _("Par artiste")), ("titre", _("Tout, par titre")))
_TAGS = None


def _fichier_tags():
    from .config import dossier_donnees
    return os.path.join(dossier_donnees(), "musiques_etiquettes.json")


def _depuis_nom(chemin):
    nom = os.path.splitext(os.path.basename(chemin))[0]
    if " - " in nom:
        a, t = [x.strip() for x in nom.split(" - ", 1)]
        return {"titre": t, "artiste": a, "album": "", "duree": 0}
    return {"titre": nom, "artiste": "", "album": "", "duree": 0}


def etiquettes(chemin, lire=True):
    """Titre, artiste, album d'un morceau (lus une fois par ffprobe, puis gardés) ; à défaut tirés du nom de fichier.
    lire=False : jamais de ffprobe (menu instantané) ; ce qui n'est pas encore connu vient du nom du fichier."""
    global _TAGS
    import json
    if _TAGS is None:
        try:
            with open(_fichier_tags(), encoding="utf-8") as f:
                _TAGS = json.load(f)
        except (OSError, ValueError):
            _TAGS = {}
    try:
        st = os.stat(chemin)
    except OSError:
        return {}
    cle = f"{chemin}|{int(st.st_mtime)}|{st.st_size}"
    if cle in _TAGS:
        return _TAGS[cle]
    if not lire:
        return dict(_depuis_nom(chemin), a_lire=True)
    tags = {}
    try:
        import subprocess
        from . import moteur
        r = subprocess.run([moteur.ffprobe(), "-v", "error", "-print_format", "json", "-show_entries", "format_tags=title,artist,album,album_artist:format=duration", chemin],
                           capture_output=True, timeout=15, **moteur._sans_console())
        fmt = (json.loads(r.stdout.decode("utf-8", "replace") or "{}").get("format") or {})
        t = {k.lower(): v for k, v in (fmt.get("tags") or {}).items()}
        tags = {"titre": t.get("title", ""), "artiste": t.get("artist") or t.get("album_artist") or "", "album": t.get("album", ""),
                "duree": float(fmt.get("duration") or 0)}
    except Exception:            # noqa: BLE001
        pass
    nom = os.path.splitext(os.path.basename(chemin))[0]
    if not tags.get("titre"):
        if " - " in nom and not tags.get("artiste"):
            tags["artiste"], tags["titre"] = [x.strip() for x in nom.split(" - ", 1)]
        else:
            tags["titre"] = nom
    _TAGS[cle] = tags
    return tags


def _garder_tags():
    import json
    if _TAGS:
        try:
            with open(_fichier_tags(), "w", encoding="utf-8") as f:
                json.dump(_TAGS, f, ensure_ascii=False)
        except OSError:
            pass


def morceaux(dossiers, limite=2000, rapide=False, delai=None):
    """Tous les morceaux des dossiers donnés (sous-dossiers compris) avec leurs étiquettes.
    rapide=True : sans lire les étiquettes encore inconnues (elles se lisent en arrière-plan, voir lire_en_fond) ;
    delai : temps maximal de parcours en secondes (dossier énorme ou disque réseau lent)."""
    import time
    from .config import est_audio
    out, vus = [], set()
    t0 = time.monotonic()
    for racine in dossiers:
        if not racine or not os.path.isdir(racine):
            continue
        for base, sous, fichiers in os.walk(racine):
            if delai and time.monotonic() - t0 > delai:
                break
            sous.sort()
            for f in sorted(fichiers):
                p = os.path.join(base, f)
                if not est_audio(f) or p in vus or f.endswith(".part"):
                    continue
                vus.add(p)
                e = dict(etiquettes(p, lire=not rapide))
                e["chemin"] = p
                e["dossier"] = os.path.relpath(base, racine) if base != racine else os.path.basename(racine.rstrip("/\\")) or racine
                out.append(e)
                if len(out) >= limite:
                    _garder_tags()
                    return out
    _garder_tags()
    return out


_LECTURE = {"fil": None}


def lire_en_fond(liste):
    """Lit en arrière-plan les étiquettes des morceaux encore inconnus (titre, artiste, album, durée) : la prochaine
    ouverture du menu les montre, sans jamais bloquer PhilCut."""
    import threading
    a_lire = [m["chemin"] for m in liste if m.get("a_lire")]
    if not a_lire or (_LECTURE["fil"] and _LECTURE["fil"].is_alive()):
        return 0

    def travail():
        for k, p in enumerate(a_lire):
            etiquettes(p)
            if k % 50 == 49:
                _garder_tags()
        _garder_tags()
    _LECTURE["fil"] = threading.Thread(target=travail, daemon=True)
    _LECTURE["fil"].start()
    return len(a_lire)


def classer(liste, mode):
    """[(groupe, [morceaux])] triés ; « titre » donne un seul groupe."""
    if mode == "titre":
        return [("", sorted(liste, key=lambda m: (m.get("titre") or "").lower()))]
    cle = {"dossier": "dossier", "album": "album", "artiste": "artiste"}.get(mode, "dossier")
    inconnu = {"album": _("Album inconnu"), "artiste": _("Artiste inconnu"), "dossier": "?"}[cle]
    groupes = {}
    for m in liste:
        groupes.setdefault((m.get(cle) or "").strip() or inconnu, []).append(m)
    return [(g, sorted(v, key=lambda m: (m.get("titre") or "").lower())) for g, v in sorted(groupes.items(), key=lambda kv: kv[0].lower())]


def libelle(m):
    d = m.get("duree") or 0
    return (m.get("titre") or os.path.basename(m["chemin"])) + (f" — {m['artiste']}" if m.get("artiste") else "") + \
        (f"  ({int(d // 60)}:{int(d % 60):02d})" if d else "")


def telecharger(morceau, params, progression=None):
    """Télécharge le morceau dans le dossier de musiques ; écrit à côté un .txt avec le crédit. Renvoie le chemin."""
    nom = re.sub(r"[^\w\- ]+", "_", f"{morceau['auteur']} - {morceau['titre']}").strip()[:90] or "musique"
    ext = morceau.get("type") if morceau.get("type") in ("mp3", "ogg", "wav", "flac", "m4a") else "mp3"
    chemin = os.path.join(dossier(params), f"{nom}.{ext}")
    if not os.path.exists(chemin):
        req = urllib.request.Request(morceau["url"], headers=_agent())
        with urllib.request.urlopen(req, timeout=120) as r, open(chemin + ".part", "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            fait = 0
            while True:
                bloc = r.read(1 << 16)
                if not bloc:
                    break
                f.write(bloc)
                fait += len(bloc)
                if progression and total:
                    progression(fait / total)
        os.replace(chemin + ".part", chemin)
    with open(os.path.splitext(chemin)[0] + ".credit.txt", "w", encoding="utf-8") as f:
        f.write(credit(morceau) + "\n")
    return chemin


def credit(morceau):
    """Mention à mettre dans la description de la vidéo (obligatoire pour CC BY et CC BY-SA)."""
    lien = f" — {morceau['page']}" if morceau.get("page") else ""
    return _("Musique : {a}{l}", a=morceau.get("attribution") or credit_texte(morceau), l=lien)


def credits_projet(projet):
    """Crédits des musiques et des tampons vidéo du projet (fichiers .credit.txt à côté des médias utilisés)."""
    out = []
    for c in list(projet.clips):
        m = projet.media(c["media"]) or {}
        f = os.path.splitext(m.get("chemin", ""))[0] + ".credit.txt"
        if os.path.exists(f):
            with open(f, encoding="utf-8") as g:
                t = g.read().strip()
            if t and t not in out:
                out.append(t)
    return out
