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
    cmd = [chemin_ytdlp(), "--no-colors", "--ffmpeg-location", moteur.ffmpeg()] + args
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
        raise RuntimeError(_("yt-dlp n'a pas pu : {e}", e=err[-500:]))
    return lignes


def mettre_a_jour_ytdlp(progression=None):
    return "\n".join(_lancer_ytdlp(["-U"], progression))


def chercher_youtube(texte, n=10):
    """Résultats d'une recherche YouTube (sans rien télécharger) : titre, chaîne, durée, adresse."""
    lignes = _lancer_ytdlp(["--flat-playlist", "--dump-json", f"ytsearch{int(n)}:{texte}"])
    out = []
    for l in lignes:
        if not l.startswith("{"):
            continue
        try:
            d = json.loads(l)
        except ValueError:
            continue
        url = d.get("url") or d.get("webpage_url") or (f"https://www.youtube.com/watch?v={d['id']}" if d.get("id") else "")
        out.append({"titre": d.get("title") or "", "auteur": d.get("channel") or d.get("uploader") or "", "duree": d.get("duration") or 0,
                    "page": url, "source": "youtube", "licence": d.get("license") or ""})
    return out


def infos(url):
    """Titre, auteur, durée et licence d'une vidéo (sans la télécharger)."""
    lignes = _lancer_ytdlp(["--dump-json", "--no-playlist", url])
    for l in lignes:
        if l.startswith("{"):
            d = json.loads(l)
            return {"titre": d.get("title") or "", "auteur": d.get("channel") or d.get("uploader") or "", "duree": d.get("duration") or 0,
                    "page": d.get("webpage_url") or url, "licence": d.get("license") or "", "annee": (d.get("upload_date") or "")[:4]}
    return {"page": url}


def telecharger(url, dossier, audio_seul=False, debut=None, fin=None, progression=None, arret=lambda: False):
    """Télécharge la vidéo (MP4 jusqu'à 1080p) ou le son seul (M4A) ; debut/fin (secondes) : seulement ce morceau.
    Renvoie le chemin du fichier."""
    os.makedirs(dossier, exist_ok=True)
    modele = os.path.join(dossier, "%(title).80s [%(id)s].%(ext)s")
    args = ["--no-playlist", "--restrict-filenames", "-o", modele, "--print", "after_move:filepath", "--newline"]
    if audio_seul:
        args += ["-f", "bestaudio[ext=m4a]/bestaudio", "-x", "--audio-format", "m4a"]
    else:
        args += ["-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/b", "--merge-output-format", "mp4"]
    if debut is not None and fin is not None and fin > debut:
        args += ["--download-sections", f"*{float(debut):.2f}-{float(fin):.2f}", "--force-keyframes-at-cuts"]
    lignes = _lancer_ytdlp(args + [url], progression, arret)
    fichiers = [l.strip() for l in lignes if l.strip() and os.path.exists(l.strip())]
    if not fichiers:
        raise RuntimeError(_("Téléchargement terminé mais fichier introuvable."))
    return fichiers[-1]


# ------------------------------------------------------------------ Internet Archive (domaine public)
def chercher_archive(texte, n=12):
    """Films et extraits du domaine public ou sous licence libre sur archive.org."""
    q = f"({texte}) AND mediatype:(movies) AND (licenseurl:* OR collection:(prelinger OR feature_films OR publicdomainmovies))"
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
