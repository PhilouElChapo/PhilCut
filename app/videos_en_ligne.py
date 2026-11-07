"""Extraits de vidéos en ligne (0.9.7) : YouTube et autres sites, avec yt-dlp, et films du domaine public d'Internet
Archive (archive.org).

Le choix est laissé à l'utilisateur, avec ce qui est légal clairement indiqué (LEGAL) et une confirmation la première
fois. yt-dlp n'est pas livré avec PhilCut : son programme officiel est téléchargé au premier usage depuis son dépôt
GitHub (yt-dlp/yt-dlp) dans le dossier des données, et mis à jour d'un clic (les sites changent souvent).
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

from .langue import _

LEGAL = _("<b>Ce qui est permis.</b> En France et dans l'Union européenne, un film reste protégé jusqu'à <b>70 ans après la mort du "
          "dernier de ses auteurs</b> (réalisateur, scénariste, dialoguiste, compositeur de la musique), et non 60 ans après sa sortie : "
          "un film de 1956 est presque toujours encore protégé. Libres : les œuvres dont tous les auteurs sont morts depuis plus de 70 ans, "
          "les vidéos sous licence Creative Commons (indiquée sous la vidéo), les vidéos dont vous avez l'accord de l'auteur. Les films "
          "américains publiés avant 1931 sont du domaine public aux Etats-Unis, pas forcément en France. Une courte citation est "
          "admise pour la critique, l'analyse ou l'information, avec la source citée. Les conditions de YouTube n'autorisent le "
          "téléchargement que par ses propres moyens : en utilisant yt-dlp, vous en prenez la responsabilité.")

CONFIRMATION = _("Je télécharge seulement des vidéos que j'ai le droit d'utiliser : domaine public, licence libre, accord de l'auteur, ou "
                 "courte citation dans les règles.")

ARCHIVE_API = "https://archive.org/advancedsearch.php"


def _agent():
    from .config import VERSION
    return {"User-Agent": f"PhilCut/{VERSION} (+https://github.com/PhilouElChapo/PhilCut)"}


# ------------------------------------------------------------------ yt-dlp
def _nom_ytdlp():
    if sys.platform.startswith("win"):
        return "yt-dlp.exe"
    if sys.platform == "darwin":
        return "yt-dlp_macos"
    return "yt-dlp_linux"


def chemin_ytdlp():
    from .config import dossier_donnees
    return os.path.join(dossier_donnees(), "outils", _nom_ytdlp())


def ytdlp_installe():
    return os.path.exists(chemin_ytdlp())


def installer_ytdlp(progression=None, arret=lambda: False):
    """Télécharge le programme officiel yt-dlp (dernière version, dépôt GitHub yt-dlp/yt-dlp)."""
    from . import packs_ia
    url = f"https://github.com/yt-dlp/yt-dlp/releases/latest/download/{_nom_ytdlp()}"
    cible = chemin_ytdlp()
    packs_ia._telecharger(url, cible, progression=progression, arret=arret)
    if not sys.platform.startswith("win"):
        os.chmod(cible, 0o755)
    return cible


# ------------------------------------------------------------------ Deno (0.9.14)
# YouTube oblige désormais yt-dlp à exécuter un petit programme JavaScript pour lire les vidéos (« No supported
# JavaScript runtime could be found ») : sans lui, la recherche marche mais pas la lecture ni le téléchargement.
# yt-dlp recommande Deno : son programme officiel (dépôt GitHub denoland/deno) est rangé à côté de yt-dlp.
def _nom_deno():
    if sys.platform.startswith("win"):
        return "deno-x86_64-pc-windows-msvc.zip", "deno.exe"
    if sys.platform == "darwin":
        import platform
        return ("deno-aarch64-apple-darwin.zip" if platform.machine() == "arm64" else "deno-x86_64-apple-darwin.zip"), "deno"
    return "deno-x86_64-unknown-linux-gnu.zip", "deno"


def chemin_deno():
    from .config import dossier_donnees
    return os.path.join(dossier_donnees(), "outils", _nom_deno()[1])


def deno_installe():
    return os.path.exists(chemin_deno())


def installer_deno(progression=None, arret=lambda: False):
    """Télécharge le programme officiel Deno (environ 45 Mo) et le range à côté de yt-dlp."""
    import zipfile
    from . import packs_ia
    archive, exe = _nom_deno()
    cible = chemin_deno()
    zp = cible + ".zip"
    packs_ia._telecharger(f"https://github.com/denoland/deno/releases/latest/download/{archive}", zp, progression=progression, arret=arret)
    with zipfile.ZipFile(zp) as z:
        nom = next(n for n in z.namelist() if os.path.basename(n) == exe)
        with z.open(nom) as src, open(cible, "wb") as dst:
            dst.write(src.read())
    os.remove(zp)
    if not sys.platform.startswith("win"):
        os.chmod(cible, 0o755)
    return cible


def _options():
    try:
        from .packs_ia import _options_processus
        return _options_processus()
    except Exception:      # noqa: BLE001
        return {}


def _lancer_ytdlp(args, progression=None, arret=lambda: False, delai=3600):
    """Lance yt-dlp ; suit « 42.3% » pour la progression. Renvoie la sortie (lignes)."""
    if not ytdlp_installe():
        raise RuntimeError(_("yt-dlp n'est pas encore installé."))
    from . import moteur
    cmd = [chemin_ytdlp(), "--no-colors", "--ffmpeg-location", moteur.ffmpeg()]
    if deno_installe():
        cmd += ["--js-runtimes", f"deno:{chemin_deno()}"]
    cmd += args
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", **_options())
    lignes = []
    for ligne in proc.stdout:
        lignes.append(ligne.rstrip())
        m = re.search(r"(\d+(?:\.\d+)?)%", ligne)
        if m and progression:
            progression(min(1.0, float(m.group(1)) / 100), re.sub(r"\s+", " ", ligne.strip())[:90])
        if arret():
            proc.kill()
            raise InterruptedError()
    proc.wait()
    if proc.returncode != 0:
        err = "\n".join(l for l in lignes[-6:] if l.strip())
        if "JavaScript runtime" in err and not deno_installe():
            raise RuntimeError(_("YouTube demande maintenant un petit programme complémentaire (Deno) pour lire ses vidéos : "
                                 "cliquez « Mettre à jour yt-dlp », qui l'installe aussi (programme officiel, environ 45 Mo), puis réessayez."))
        raise RuntimeError(_("yt-dlp n'a pas pu : {e}", e=err[-500:]))
    return lignes


def mettre_a_jour_ytdlp(progression=None):
    return "\n".join(_lancer_ytdlp(["-U"], progression))


def pays():
    """Pays de l'utilisateur (« FR ») d'après la langue du système : la recherche se fait sur le YouTube de son pays."""
    try:
        from PySide6.QtCore import QLocale
        nom = QLocale.system().name()           # fr_FR, de_CH…
        if "_" in nom:
            return nom.split("_", 1)[1][:2].upper()
    except Exception:      # noqa: BLE001
        pass
    return "FR"


def _langue():
    try:
        from .langue import LANGUE
        return (LANGUE or "fr")[:2]
    except Exception:      # noqa: BLE001
        return "fr"


def _recherche_brute(requete, n):
    lignes = _lancer_ytdlp(["--flat-playlist", "--dump-json", "--xff", pays(), "--extractor-args", f"youtube:lang={_langue()}",
                            f"ytsearch{int(n)}:{requete}"])
    out = []
    for l in lignes:
        if not l.startswith("{"):
            continue
        try:
            d = json.loads(l)
        except ValueError:
            continue
        url = d.get("url") or d.get("webpage_url") or (f"https://www.youtube.com/watch?v={d['id']}" if d.get("id") else "")
        duree = float(d.get("duration") or 0)
        out.append({"titre": d.get("title") or "", "auteur": d.get("channel") or d.get("uploader") or "", "duree": duree,
                    "page": url, "source": "youtube", "licence": d.get("license") or "", "short": "/shorts/" in url,
                    "vues": d.get("view_count") or 0, "id": d.get("id") or url,
                    "vignette": f"https://i.ytimg.com/vi/{d['id']}/mqdefault.jpg" if d.get("id") else ""})
    return out


def chercher_youtube(texte, n=30, genre="tout"):
    """Résultats d'une recherche YouTube (sans rien télécharger) : titre, chaîne, durée, adresse, Short ou non. La
    recherche se fait dans la langue et le pays de l'utilisateur, avec les mots tels qu'il les a tapés (pas de
    traduction). genre : « tout » (vidéos, puis les Shorts, comme la page de YouTube), « shorts » ou « videos ».
    La recherche simple de YouTube ne renvoie presque que des vidéos : les Shorts sont cherchés à part."""
    n = int(n)
    vus, out = set(), []

    def ajouter(liste, garder, maximum):
        k = 0
        for r in liste:
            if k >= maximum:
                break
            if r["id"] in vus or not garder(r):
                continue
            vus.add(r["id"])
            out.append(r)
            k += 1
    if genre in ("tout", "videos"):
        ajouter(_recherche_brute(texte, n * (2 if genre == "videos" else 1)), (lambda r: not r["short"]) if genre == "videos" else
                (lambda r: True), n)
    if genre in ("tout", "shorts"):
        quota = n if genre == "shorts" else max(10, n // 2)
        brut = _recherche_brute(f"{texte} #shorts", quota * 2)
        for r in brut:                                    # une vidéo très courte trouvée par « #shorts » est un Short
            r["short"] = r["short"] or 0 < r["duree"] <= 180
        ajouter(brut, lambda r: r["short"], quota)
    return out


def vignettes(resultats, dossier, arret=lambda: False):
    """Télécharge les petites images des résultats (en parallèle) ; ajoute « _vignette » (chemin local)."""
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(dossier, exist_ok=True)

    def une(r):
        if not r.get("vignette") or arret():
            return
        f = os.path.join(dossier, re.sub(r"[^\w]", "_", r["vignette"])[-90:] + ".jpg")
        if not os.path.exists(f):
            try:
                with urllib.request.urlopen(urllib.request.Request(r["vignette"], headers=_agent()), timeout=10) as rep, open(f, "wb") as g:
                    g.write(rep.read())
            except Exception:      # noqa: BLE001 : sans image, le résultat reste listé
                return
        r["_vignette"] = f
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(une, resultats))
    return resultats


def suggestions(texte):
    """Orthographe proposée par YouTube pour une recherche mal tapée (« planette interdite » → « planète interdite »)."""
    url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "ds": "yt", "hl": _langue(), "gl": pays(), "q": texte})
    with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=8) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return [x for x in (d[1] if isinstance(d, list) and len(d) > 1 else []) if isinstance(x, str)]


def correction(texte, propositions):
    """La bonne orthographe si la recherche semble mal tapée, sinon None."""
    import difflib
    import unicodedata

    def net(t):
        return " ".join(unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode().split())
    q = net(texte)
    if not q or any(net(p).startswith(q) for p in propositions):
        return None                                    # la recherche est bien tapée (les suggestions la prolongent)
    meilleure, score = None, 0.0
    for p in propositions:
        debut = " ".join(p.split()[:len(texte.split())])        # même nombre de mots que la recherche
        r = difflib.SequenceMatcher(None, q, net(debut)).ratio()
        if r > score:
            meilleure, score = debut, r
    return meilleure if meilleure and score >= 0.7 and net(meilleure) != q else None


def flux_lecture(url):
    """Adresse directe d'une version légère (son et image, 360p à 480p) pour regarder la vidéo dans PhilCut."""
    lignes = _lancer_ytdlp(["-g", "--no-playlist", "-f", "18/b[ext=mp4][vcodec!=none][acodec!=none][height<=480]/b[height<=480]/b", url])
    for l in lignes:
        if l.startswith("http"):
            return l.strip()
    raise RuntimeError(_("Pas de version lisible de cette vidéo."))


def infos(url):
    """Titre, auteur, durée et licence d'une vidéo (sans la télécharger)."""
    lignes = _lancer_ytdlp(["--dump-json", "--no-playlist", url])
    for l in lignes:
        if l.startswith("{"):
            d = json.loads(l)
            return {"titre": d.get("title") or "", "auteur": d.get("channel") or d.get("uploader") or "", "duree": d.get("duration") or 0,
                    "page": d.get("webpage_url") or url, "licence": d.get("license") or "", "annee": (d.get("upload_date") or "")[:4]}
    return {"page": url}


HAUTEURS = {720: _("720p (fichier léger)"), 1080: _("1080p (conseillé)"), 2160: _("4K si disponible (gros fichier)")}


def telecharger(url, dossier, audio_seul=False, debut=None, fin=None, progression=None, arret=lambda: False, hauteur=1080):
    """Télécharge la vidéo (MP4 jusqu'à `hauteur`, 1080p par défaut) ou le son seul (M4A) ; debut/fin (secondes) :
    seulement ce morceau. Renvoie le chemin du fichier."""
    h = int(hauteur or 1080)
    os.makedirs(dossier, exist_ok=True)
    modele = os.path.join(dossier, "%(title).80s [%(id)s].%(ext)s")
    args = ["--no-playlist", "--restrict-filenames", "-o", modele, "--print", "after_move:filepath", "--newline"]
    if audio_seul:
        args += ["-f", "bestaudio[ext=m4a]/bestaudio", "-x", "--audio-format", "m4a"]
    else:
        args += ["-f", f"bv*[height<={h}][ext=mp4]+ba[ext=m4a]/b[height<={h}][ext=mp4]/bv*[height<={h}]+ba/b", "--merge-output-format", "mp4"]
    if debut is not None and fin is not None and fin > debut:
        args += ["--download-sections", f"*{float(debut):.2f}-{float(fin):.2f}", "--force-keyframes-at-cuts"]
    lignes = _lancer_ytdlp(args + [url], progression, arret)
    fichiers = [l.strip() for l in lignes if l.strip() and os.path.exists(l.strip())]
    if not fichiers:
        raise RuntimeError(_("Téléchargement terminé mais fichier introuvable."))
    return fichiers[-1]


# ------------------------------------------------------------------ Internet Archive (domaine public)
def chercher_archive(texte, n=30, anglais=""):
    """Films et extraits du domaine public ou sous licence libre sur archive.org ; avec les mots tapés ET leur
    traduction anglaise si elle est différente (la plupart des fiches sont en anglais)."""
    mots = f"({texte}) OR ({anglais})" if anglais and anglais.lower() != texte.lower() else f"({texte})"
    q = f"({mots}) AND mediatype:(movies) AND (licenseurl:* OR collection:(prelinger OR feature_films OR publicdomainmovies))"
    url = ARCHIVE_API + "?" + urllib.parse.urlencode({"q": q, "fl[]": ["identifier", "title", "year", "creator", "licenseurl"], "rows": n,
                                                       "output": "json"}, doseq=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for doc in (d.get("response") or {}).get("docs") or []:
        ident = doc.get("identifier")
        if not ident:
            continue
        createur = doc.get("creator") or ""
        out.append({"titre": doc.get("title") or ident, "auteur": createur if isinstance(createur, str) else ", ".join(createur),
                    "annee": str(doc.get("year") or ""), "licence": doc.get("licenseurl") or _("domaine public (selon archive.org)"),
                    "page": f"https://archive.org/details/{ident}", "ident": ident, "source": "archive"})
    return out


def fichier_archive(ident):
    """Adresse du meilleur fichier vidéo MP4 d'un élément archive.org."""
    with urllib.request.urlopen(urllib.request.Request(f"https://archive.org/metadata/{ident}", headers=_agent()), timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    fichiers = [f for f in d.get("files") or [] if str(f.get("name", "")).lower().endswith(".mp4")]
    if not fichiers:
        raise RuntimeError(_("Pas de fichier MP4 dans cet élément d'archive.org."))
    fichiers.sort(key=lambda f: int(f.get("size") or 0))
    meilleur = next((f for f in fichiers if int(f.get("size") or 0) < 1_500_000_000), fichiers[0])     # pas d'énorme copie d'archive
    return f"https://archive.org/download/{ident}/{urllib.parse.quote(meilleur['name'])}", int(meilleur.get("size") or 0)


def telecharger_archive(ident, dossier, progression=None, arret=lambda: False):
    from . import packs_ia
    url, taille = fichier_archive(ident)
    cible = os.path.join(dossier, re.sub(r"[^\w\-.]+", "_", f"{ident}.mp4"))
    packs_ia._telecharger(url, cible, taille=taille, progression=progression, arret=arret)
    return cible
