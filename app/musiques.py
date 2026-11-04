"""Bibliothèque musicale libre (cahier des charges 10.8) : recherche dans Openverse (musiques sous licence Creative
Commons de Jamendo, ccMixter, Freesound…), seulement les licences compatibles avec une vidéo publiée, y compris
monétisée : CC0, domaine public, CC BY, CC BY-SA. Téléchargement à la demande dans votre dossier de musiques, avec la
mention de crédit à recopier (PhilCut l'ajoute à la description YouTube). Sans clef ni compte."""
import json, os, re, time, urllib.parse, urllib.request

from .langue import _

API = "https://api.openverse.org/v1/audio/"
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
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "PhilCut (montage vidéo libre)"})
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


def dossier(params):
    d = (params or {}).get("musiques_dossier") or ""
    if not d:
        from .config import dossier_donnees
        d = os.path.join(dossier_donnees(), "musiques")
    os.makedirs(d, exist_ok=True)
    return d


def telecharger(morceau, params, progression=None):
    """Télécharge le morceau dans le dossier de musiques ; écrit à côté un .txt avec le crédit. Renvoie le chemin."""
    nom = re.sub(r"[^\w\- ]+", "_", f"{morceau['auteur']} - {morceau['titre']}").strip()[:90] or "musique"
    ext = morceau.get("type") if morceau.get("type") in ("mp3", "ogg", "wav", "flac", "m4a") else "mp3"
    chemin = os.path.join(dossier(params), f"{nom}.{ext}")
    if not os.path.exists(chemin):
        req = urllib.request.Request(morceau["url"], headers={"User-Agent": "PhilCut (montage vidéo libre)"})
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
    """Crédits des musiques du projet (fichiers .credit.txt à côté des musiques utilisées)."""
    out = []
    for c in projet.clips_piste("audio"):
        m = projet.media(c["media"]) or {}
        f = os.path.splitext(m.get("chemin", ""))[0] + ".credit.txt"
        if os.path.exists(f):
            with open(f, encoding="utf-8") as g:
                t = g.read().strip()
            if t and t not in out:
                out.append(t)
    return out
