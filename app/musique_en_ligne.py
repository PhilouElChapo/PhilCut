"""Musique en ligne (0.9.37) : chercher, écouter et télécharger le son d'une vidéo YouTube, d'un titre YouTube Music,
ou d'un enregistrement libre des archives (archive.org, licence indiquée). Brique commune à PhilCut et PhilMusic.

Le choix est laissé à l'utilisateur, avec ce qui est permis clairement expliqué (LEGAL_MUSIQUE) et une confirmation la
première fois : une œuvre et son enregistrement ont des droits distincts. yt-dlp est le programme officiel, installé et
mis à jour comme pour les vidéos (videos_en_ligne). Le fichier téléchargé garde sa source (étiquette « commentaire » et
fichier « .droits.json ») : PhilCut sait ensuite s'il peut seulement s'en inspirer, ou aussi le réorchestrer.
"""
import json
import os
import re
import urllib.parse
import urllib.request

from .langue import _

SOURCES = [("ytmusic", _("YouTube Music (titres)")), ("youtube", _("YouTube (vidéos)")), ("archive", _("Archives libres (archive.org)")),
           ("audionautix", _("Audionautix : musiques libres de Jason Shaw (crédit à citer)"))]
SANS_YTDLP = ("archive", "audionautix")          # sources lues directement, sans yt-dlp

# 0.9.47 : Audionautix (audionautix.com) : toute la musique de Jason Shaw est sous licence Creative Commons Attribution 4.0,
# utilisable même commercialement, à condition de citer « music by audionautix.com » (ou un lien vers le site) ; pas de
# revente telle quelle, seulement dans une œuvre (vidéo, podcast…). Le site n'a pas d'API : PhilCut lit ses pages de genres
# (agent PhilCut déclaré, jamais déguisé), garde le catalogue une semaine et cherche dedans.
AUDIONAUTIX = "https://audionautix.com"
AUDIONAUTIX_LICENCE = "CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/"
AUDIONAUTIX_CREDIT = "Music by audionautix.com (Jason Shaw), CC BY 4.0"

LEGAL_MUSIQUE = _(
    "<b>Une musique a deux sortes de droits.</b> <b>L'œuvre</b> (la composition, les paroles) est libre 70 ans après la mort de son "
    "dernier auteur : le Dies irae, Mozart, Beethoven, Bizet le sont. <b>L'enregistrement</b> (une interprétation précise) a ses propres "
    "droits, ceux du producteur et des interprètes : en France et dans l'Union européenne, en règle générale, 70 ans après sa "
    "publication ; un enregistrement des années 30 est donc en principe libre ici, mais pas forcément aux Etats-Unis (là-bas, ceux de "
    "1925 ne le sont que depuis 2026). Une Symphonie de Beethoven enregistrée en 2015 reste protégée par son enregistrement. "
    "<b>Libres d'usage :</b> les enregistrements anciens dans ces conditions, ceux sous licence libre (Creative Commons, indiquée par la "
    "source) et ce dont vous avez l'accord. <b>Pour un morceau protégé</b>, PhilCut peut seulement s'inspirer de son style (tempo, "
    "instruments, ambiance) : la mélodie n'est jamais recopiée. Les conditions de YouTube n'autorisent le téléchargement que par ses "
    "propres moyens : en utilisant yt-dlp, vous en prenez la responsabilité. En cas de doute, ne publiez pas.")

CONFIRMATION = _("Je télécharge seulement ce que j'ai le droit d'utiliser, ou pour m'en inspirer sans le publier : domaine public, "
                 "licence libre, accord de l'auteur.")


def _agent():
    from .config import VERSION
    return {"User-Agent": f"PhilCut/{VERSION} (+https://github.com/PhilouElChapo/PhilCut)"}


def _net_artiste(a):
    a = re.sub(r"\s*-\s*Topic$", "", a or "").strip()
    a = re.sub(r"VEVO$", "", a).strip()
    return a


def _lignes_json(lignes):
    for l in lignes:
        if l.startswith("{"):
            try:
                yield json.loads(l)
            except ValueError:
                continue


def chercher(texte, source="ytmusic", n=30):
    """Résultats : titre, artiste, durée, page, source, licence, libre (licence libre annoncée par la source)."""
    texte = (texte or "").strip()
    if not texte:
        return []
    if source == "archive":
        return chercher_archive(texte, n)
    if source == "audionautix":
        return chercher_audionautix(texte, n)
    from . import videos_en_ligne as VL
    if source == "youtube":
        out = VL._recherche_brute(texte, n)
        for r in out:
            r["artiste"] = _net_artiste(r.get("auteur"))
            r["libre"] = "creative commons" in (r.get("licence") or "").lower()
        return [r for r in out if not r.get("short")]
    url = "https://music.youtube.com/search?" + urllib.parse.urlencode({"q": texte}) + "#songs"
    lignes = VL._lancer_ytdlp(["--flat-playlist", "--dump-json", "--playlist-end", str(int(n)), "--xff", VL.pays(), url])
    out = []
    for d in _lignes_json(lignes):
        ident = d.get("id") or ""
        if not ident:
            continue
        artistes = d.get("artists") or ([d["artist"]] if d.get("artist") else [])
        out.append({"titre": d.get("title") or "", "artiste": ", ".join(artistes) if artistes else _net_artiste(d.get("channel") or d.get("uploader")),
                    "duree": float(d.get("duration") or 0), "page": f"https://music.youtube.com/watch?v={ident}", "id": ident,
                    "source": "ytmusic", "licence": d.get("license") or "", "album": d.get("album") or "",
                    "vignette": f"https://i.ytimg.com/vi/{ident}/mqdefault.jpg", "libre": False})
    completer(out[:12])
    return out


def completer(resultats):
    """La recherche rapide de YouTube Music ne donne souvent que le titre : on demande la fiche des premiers titres
    (artiste, album, année, durée) en une fois. Sans réseau ou en cas d'échec, les résultats restent tels quels."""
    manquants = [r for r in resultats if not r.get("artiste") or not r.get("duree")]
    if not manquants:
        return resultats
    from . import videos_en_ligne as VL
    try:
        lignes = VL._lancer_ytdlp(["--skip-download", "--dump-json", "--no-warnings", "--ignore-errors", "--xff", VL.pays()]
                                  + [r["page"] for r in manquants])
    except Exception:      # noqa: BLE001
        return resultats
    fiches = {d.get("id"): d for d in _lignes_json(lignes)}
    for r in manquants:
        d = fiches.get(r.get("id"))
        if not d:
            continue
        artistes = d.get("artists") or ([d["artist"]] if d.get("artist") else [])
        r["artiste"] = r.get("artiste") or (", ".join(artistes) if artistes else _net_artiste(d.get("channel") or d.get("uploader")))
        r["duree"] = r.get("duree") or float(d.get("duration") or 0)
        r["album"] = r.get("album") or d.get("album") or ""
        r["annee"] = r.get("annee") or str(d.get("release_year") or (d.get("upload_date") or "")[:4] or "")
        r["licence"] = r.get("licence") or d.get("license") or ""
    return resultats


ARCHIVE_API = "https://archive.org/advancedsearch.php"


def chercher_archive(texte, n=25):
    """Enregistrements des archives d'Internet Archive dont la licence est indiquée (Creative Commons, domaine public)."""
    q = f"({texte}) AND mediatype:(audio) AND licenseurl:*"
    url = ARCHIVE_API + "?" + urllib.parse.urlencode({"q": q, "fl[]": ["identifier", "title", "year", "creator", "licenseurl", "date"],
                                                       "rows": int(n), "output": "json", "sort[]": "downloads desc"}, doseq=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for doc in (d.get("response") or {}).get("docs") or []:
        ident = doc.get("identifier")
        if not ident:
            continue
        c = doc.get("creator") or ""
        lic = doc.get("licenseurl") or ""
        out.append({"titre": doc.get("title") or ident, "artiste": c if isinstance(c, str) else ", ".join(c), "duree": 0.0,
                    "annee": str(doc.get("year") or doc.get("date") or "")[:4], "page": f"https://archive.org/details/{ident}", "id": ident,
                    "source": "archive", "licence": lic, "licence_libre": bool(re.search(r"publicdomain|creativecommons\.org/(licenses/by|publicdomain)", lic)
                                                                                   and "-nc" not in lic.lower() and "-nd" not in lic.lower()),
                    "libre": False})        # licence ANNONCÉE par la personne qui a déposé le fichier : à vérifier, jamais cochée d'office
    return out


def _page(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def _titre_fichier(url):
    """« JasonShaw-AUDIONAUTIX-COM_Morning-Walk.mp3 » → « Morning Walk »."""
    n = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    n = re.sub(r"\.mp3$", "", n, flags=re.I)
    n = re.sub(r"(?i)^(jason[ _-]*shaw[ _-]*)?(audionautix[ _.-]*(com)?[ _-]*)?", "", n)
    n = re.sub(r"[_-]+", " ", n)
    n = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", n)
    return re.sub(r"\s+", " ", n).strip().title() or "?"


def catalogue_audionautix(rafraichir=False):
    """Toutes les musiques d'Audionautix (titre, genre, adresse du MP3), gardées une semaine sur ce poste."""
    import time
    from .config import dossier_donnees
    cache = os.path.join(dossier_donnees(), "cache", "audionautix.json")
    try:
        if not rafraichir and time.time() - os.path.getmtime(cache) < 7 * 86400:
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    accueil = _page(AUDIONAUTIX + "/")
    genres = []
    for m in re.finditer(r'href=["\'](?:https?://(?:www\.)?audionautix\.com)?(/free-music/[^"\'#?]+)["\']', accueil, re.I):
        g = m.group(1).rstrip("/")
        if g not in genres:
            genres.append(g)
    pistes, vues = [], set()
    for g in [""] + genres:
        try:
            html = accueil if not g else _page(AUDIONAUTIX + g)
        except Exception:      # noqa: BLE001 : une page de genre absente n'empêche pas les autres
            continue
        nom_genre = urllib.parse.unquote(g.rsplit("/", 1)[-1]).replace("-", " ").title() if g else ""
        for m in re.finditer(r'["\'(]((?:https?:)?//[^"\'()\s]+?\.mp3|/[^"\'()\s]+?\.mp3)["\')]', html, re.I):
            u = m.group(1)
            u = ("https:" + u) if u.startswith("//") else (AUDIONAUTIX + u if u.startswith("/") else u)
            if u in vues:
                continue
            vues.add(u)
            pistes.append({"titre": _titre_fichier(u), "genre": nom_genre, "url": u})
    if not pistes:
        raise RuntimeError(_("Audionautix n'a renvoyé aucune musique : le site a peut-être changé. Essayez les archives libres."))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(pistes, f, ensure_ascii=False)
    return pistes


def _sans_accents(t):
    import unicodedata
    return unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()


def chercher_audionautix(texte, n=30):
    """Les musiques d'Audionautix dont le titre ou le genre contient vos mots (ex. « jazz », « calm », « piano »)."""
    mots = [m for m in _sans_accents(texte).split() if m]
    out = []
    for p in catalogue_audionautix():
        cible = _sans_accents(p["titre"] + " " + p.get("genre", ""))
        if all(m in cible for m in mots):
            out.append({"titre": p["titre"], "artiste": "Jason Shaw (Audionautix)", "album": p.get("genre", ""), "duree": 0.0,
                        "page": p["url"], "id": p["url"], "source": "audionautix", "licence": AUDIONAUTIX_LICENCE,
                        "credit": AUDIONAUTIX_CREDIT, "libre": True})
        if len(out) >= n:
            break
    return out


def _fichier_archive(ident):
    """Le meilleur fichier son d'un enregistrement d'archive.org (MP3 de préférence)."""
    url = f"https://archive.org/metadata/{urllib.parse.quote(ident)}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    fichiers = d.get("files") or []
    for fmt in ("VBR MP3", "MP3", "128Kbps MP3", "64Kbps MP3", "Ogg Vorbis", "Flac"):
        for f in fichiers:
            if f.get("format") == fmt:
                return f"https://archive.org/download/{urllib.parse.quote(ident)}/{urllib.parse.quote(f['name'])}", f["name"]
    raise RuntimeError(_("Pas de fichier son dans cet enregistrement."))


def nom_propre(r):
    """« Artiste - Titre » sans les « (Official Video) », « [HD] », « Lyrics »… ni caractères interdits."""
    titre = re.sub(r"\s*[\(\[][^)\]]*(official|officiel|video|vidéo|clip|lyrics|paroles|audio|hd|4k|remaster)[^)\]]*[\)\]]", "", r.get("titre") or "",
                   flags=re.I).strip()
    artiste = (r.get("artiste") or "").strip()
    if artiste and titre.lower().startswith(artiste.lower() + " - "):
        titre = titre[len(artiste) + 3:]
    nom = f"{artiste} - {titre}" if artiste else titre
    return re.sub(r'[\\/:*?"<>|]+', "_", nom).strip(" ._")[:110] or "musique", titre, artiste


def telecharger(r, dossier, libre=None, progression=None, arret=lambda: False):
    """Télécharge le son (MP3) dans `dossier`, avec titre, artiste, album, année et la source en commentaire ; écrit
    « .droits.json » (source, licence, libre). Renvoie le chemin."""
    from . import moteur, musique_ia as MI
    os.makedirs(dossier, exist_ok=True)
    nom, titre, artiste = nom_propre(r)
    cible = os.path.join(dossier, nom + ".mp3")
    brut = None
    if r.get("source") in SANS_YTDLP:
        url, _f = _fichier_archive(r["id"]) if r.get("source") == "archive" else (r["id"], r["id"].rsplit("/", 1)[-1])
        brut = os.path.join(dossier, nom + ".telechargement" + os.path.splitext(_f)[1])
        with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=120) as rep, open(brut + ".part", "wb") as f:
            total, fait = int(rep.headers.get("Content-Length") or 0), 0
            while True:
                if arret():
                    raise InterruptedError()
                b = rep.read(1 << 16)
                if not b:
                    break
                f.write(b)
                fait += len(b)
                if progression and total:
                    progression(0.9 * fait / total, _("Téléchargement : {p} %", p=int(100 * fait / total)))
        os.replace(brut + ".part", brut)
    else:
        from . import videos_en_ligne as VL
        modele = os.path.join(dossier, nom + ".telechargement.%(ext)s")
        lignes = VL._lancer_ytdlp(["--no-playlist", "-f", "bestaudio/best", "-x", "--audio-format", "mp3", "--audio-quality", "0", "-o", modele,
                                   "--print", "after_move:filepath", "--newline", r["page"]],
                                  (lambda f, t="": progression(0.9 * f, t)) if progression else None, arret)
        fichiers = [l.strip() for l in lignes if l.strip() and os.path.exists(l.strip())]
        if not fichiers:
            raise RuntimeError(_("Téléchargement terminé mais fichier introuvable."))
        brut = fichiers[-1]
    if progression:
        progression(0.95, _("Etiquettes (titre, artiste, source)…"))
    commentaire = _("Source : {p}", p=r.get("page", "")) + (f" — {r['licence']}" if r.get("licence") else "") + \
        (f" — {r['credit']}" if r.get("credit") else "")
    meta = ["-metadata", f"title={titre}", "-metadata", f"artist={artiste}", "-metadata", f"comment={commentaire}"]
    if r.get("album"):
        meta += ["-metadata", f"album={r['album']}"]
    if r.get("annee"):
        meta += ["-metadata", f"date={r['annee']}"]
    copie = brut.lower().endswith(".mp3")
    moteur.lancer(["-i", brut, "-map", "0:a:0", "-map_metadata", "-1"] + (["-c:a", "copy"] if copie else ["-c:a", "libmp3lame", "-q:a", "0"])
                  + meta + ["-id3v2_version", "3", cible])
    try:
        os.remove(brut)
    except OSError:
        pass
    infos = {"credit": r["credit"]} if r.get("credit") else {}
    MI.declarer(cible, origine=r.get("page", ""), source=r.get("source", ""), licence=r.get("licence", ""),
                libre=bool(r.get("libre") if libre is None else libre), titre=titre, artiste=artiste, **infos)
    if r.get("credit"):                                # crédit CC BY repris dans la description à la publication
        try:
            with open(os.path.splitext(cible)[0] + ".credit.txt", "w", encoding="utf-8") as f:
                f.write(f"{titre} — {r['credit']}")
        except OSError:
            pass
    if progression:
        progression(1.0, _("Téléchargé."))
    return cible
