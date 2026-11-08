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


VERSION_TAGS = 3          # 0.9.9 : numéro de piste, disque, artiste de l'album ; étiquettes des flux (FLAC, OGG, M4A)
_NUM = re.compile(r"^\s*(?:(?:cd|disc|disque)\s*\d+\s*[-_. ]\s*|\d-(?=\d{2}))?(\d{1,3})(?:\s*[-_.)]\s*|\s+)(?=\S)", re.I)


def _sans_numero(texte):
    """« 01 - Hells Bells », « 1-03. Shake A Leg », « 07 Shoot To Thrill » → (« Hells Bells », 1)."""
    m = _NUM.match(texte or "")
    if m and not texte[m.start(1):m.end()].strip(" ").replace(m.group(1), "", 1) and not m.group(1).startswith("0"):
        m = None                       # « 99 Luftballons » : un nombre suivi d'une espace seule n'est un n° de piste que s'il est « 07 »
    if m and len(texte) > m.end():
        return texte[m.end():].strip(), int(m.group(1))
    return (texte or "").strip(), 0


# artistes dont le nom commence vraiment par un nombre (ils ne perdent pas leur nombre)
ARTISTES_NOMBRE = {"3 doors down", "50 cent", "10 years", "30 seconds to mars", "4 non blondes", "2 unlimited", "5 seconds of summer",
                   "98 degrees", "112", "311", "702", "3t", "2pac", "10cc", "4him", "38 special", "the 1975", "21 savage", "6lack"}
_NUM_DEVANT = re.compile(r"^\s*(\d{1,3})(?:\s*[-_.)]\s*|\s+)(?=\S)")


_RACINES = set()           # dossiers de musiques choisis : un fichier rangé dessous, dans un sous-dossier, est dans un album


def nettoyer_artiste(a):
    """« 17 Queen » (n° de piste collé au nom, dans l'étiquette ou le nom du fichier) → « Queen » (0.9.31)."""
    a = re.sub(r"\s+", " ", (a or "").replace("_", " ")).strip()
    m = _NUM_DEVANT.match(a)
    if m and a.lower() not in ARTISTES_NOMBRE and int(m.group(1)) <= 40 and len(a) > m.end():
        return a[m.end():].strip()
    return a


def _depuis_nom(chemin):
    """Faute d'étiquettes : rangement habituel « Artiste/Album/01 - Titre », ou « Artiste - Titre » ; le numéro de piste
    n'est jamais pris pour un artiste."""
    nom = re.sub(r"\s+", " ", os.path.splitext(os.path.basename(chemin))[0].replace("_", " ")).strip()
    titre, piste = _sans_numero(nom)
    m0 = _NUM_DEVANT.match(nom)
    dans_sous_dossier = _RACINES and os.path.normcase(os.path.dirname(os.path.abspath(chemin))) not in _RACINES
    if not piste and m0 and dans_sous_dossier and int(m0.group(1)) <= 40 and " - " not in nom:
        titre, piste = nom[m0.end():].strip(), int(m0.group(1))      # « 10 Living On My Own » rangé dans un album
    artiste = ""
    if " - " in titre:
        g, d = [x.strip() for x in titre.split(" - ", 1)]
        d2, p2 = _sans_numero(d)
        m = _NUM_DEVANT.match(g)
        if m and g.lower() not in ARTISTES_NOMBRE and int(m.group(1)) <= 40:
            # « 17 Queen - Who Wants… » : n° de piste + artiste ; « 14 Another One Bites The Dust - Free » : n° + titre long
            reste = g[m.end():].strip()
            piste = piste or int(m.group(1))
            if len(reste.split()) <= 3:
                artiste, titre = reste, d2
            else:
                titre = f"{reste} - {d}"
        elif not g.isdigit():
            artiste, titre, piste = g, d2, piste or p2
    parent = os.path.basename(os.path.dirname(chemin))
    grand = os.path.basename(os.path.dirname(os.path.dirname(chemin)))
    album = ""
    if piste and parent and not artiste and dans_sous_dossier is not False:   # « 01 - Titre » dans un dossier : c'est un album
        album = parent
        if not artiste and grand:
            artiste = grand
    return {"titre": titre, "artiste": artiste, "album": album, "duree": 0, "piste": piste, "disque": 0, "artiste_album": ""}


def _entier(v):
    m = re.match(r"\s*(\d+)", str(v or ""))
    return int(m.group(1)) if m else 0


def etiquettes(chemin, lire=True):
    """Titre, artiste, album, n° de piste d'un morceau (lus une fois par ffprobe, puis gardés) ; à défaut tirés du nom
    de fichier et des dossiers. lire=False : jamais de ffprobe ; ce qui n'est pas encore lu vient de l'ancien cache ou du
    nom du fichier, avec a_lire=True."""
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
    connu = _TAGS.get(cle)
    if connu and connu.get("v") == VERSION_TAGS:
        return connu
    if not lire:
        base = dict(_depuis_nom(chemin))
        if connu:                                   # lu par une version précédente : on le montre en attendant
            base.update({k: v for k, v in connu.items() if v})
        return dict(base, a_lire=True)
    tags = {}
    try:
        import subprocess
        from . import moteur
        r = subprocess.run([moteur.ffprobe(), "-v", "error", "-print_format", "json", "-show_entries",
                            "format_tags:stream_tags:format=duration", "-select_streams", "a:0", chemin],
                           capture_output=True, timeout=15, **moteur._sans_console())
        d = json.loads(r.stdout.decode("utf-8", "replace") or "{}")
        fmt = d.get("format") or {}
        t = {}
        for flux in d.get("streams") or []:        # FLAC, OGG, Opus : étiquettes rangées sur le flux
            t.update({k.lower(): v for k, v in (flux.get("tags") or {}).items()})
        t.update({k.lower(): v for k, v in (fmt.get("tags") or {}).items()})       # MP3 (ID3), M4A : sur le fichier
        tags = {"titre": (t.get("title") or "").strip(), "artiste": (t.get("artist") or t.get("album_artist") or t.get("albumartist") or "").strip(),
                "artiste_album": (t.get("album_artist") or t.get("albumartist") or t.get("album artist") or "").strip(),
                "album": (t.get("album") or "").strip(), "duree": float(fmt.get("duration") or 0),
                "piste": _entier(t.get("track") or t.get("tracknumber")), "disque": _entier(t.get("disc") or t.get("discnumber"))}
    except Exception:            # noqa: BLE001
        pass
    devine = _depuis_nom(chemin)
    for k, v in devine.items():
        if not tags.get(k):
            tags[k] = v
    for k in ("artiste", "artiste_album"):
        tags[k] = nettoyer_artiste(tags.get(k))
    tags["v"] = VERSION_TAGS
    _TAGS[cle] = tags
    return tags


def _garder_tags():
    import json
    if _TAGS:
        try:
            with open(_fichier_tags(), "w", encoding="utf-8") as f:
                json.dump(dict(_TAGS), f, ensure_ascii=False)
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
        _RACINES.add(os.path.normcase(os.path.abspath(racine)))
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
        from concurrent.futures import ThreadPoolExecutor
        _LECTURE["faits"], _LECTURE["total"] = 0, len(a_lire)

        def un(p):
            try:
                etiquettes(p)
            finally:
                _LECTURE["faits"] += 1
        with ThreadPoolExecutor(max_workers=max(2, min(6, (os.cpu_count() or 4) // 2))) as ex:      # 4 à 6 fois plus vite
            for k, _r in enumerate(ex.map(un, a_lire)):
                if k % 100 == 99:
                    _garder_tags()
        _garder_tags()
    _LECTURE["fil"] = threading.Thread(target=travail, daemon=True)
    _LECTURE["fil"].start()
    return len(a_lire)


def _ordre_album(m):
    return (int(m.get("disque") or 0), int(m.get("piste") or 0) or 999, (m.get("titre") or "").lower())


def _artiste_groupe(m):
    """Comme les lecteurs de musique : l'artiste de l'album d'abord (une compilation reste ensemble), sinon l'artiste."""
    return (m.get("artiste_album") or m.get("artiste") or "").strip()


def classer(liste, mode):
    """[(groupe, [morceaux])] triés ; « titre » donne un seul groupe. Dans un album, l'ordre des pistes (disque, n°)."""
    if mode == "titre":
        return [("", sorted(liste, key=lambda m: (m.get("titre") or "").lower()))]
    if mode == "artiste":
        cle_g, inconnu = _artiste_groupe, _("Artiste inconnu")
        ordre = lambda m: ((m.get("album") or "").lower(),) + _ordre_album(m)
    elif mode == "album":
        cle_g, inconnu = (lambda m: (m.get("album") or "").strip()), _("Album inconnu")
        ordre = _ordre_album
    else:
        cle_g, inconnu = (lambda m: (m.get("dossier") or "").strip()), "?"
        ordre = _ordre_album
    groupes = {}
    for m in liste:
        groupes.setdefault(cle_g(m) or inconnu, []).append(m)
    return [(g, sorted(v, key=ordre)) for g, v in sorted(groupes.items(), key=lambda kv: (kv[0] in (inconnu, "?"), kv[0].lower()))]


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
