"""Publication (cahier des charges 18.4).

- YouTube : envoi direct par l'API officielle (YouTube Data API v3, envoi « reprenable » par morceaux), avec le compte
  de l'utilisateur relié une fois (OAuth, même application PhilCut que le Drive). Titre, description, mots-clefs et
  visibilité préparés par l'assistant. Tant que l'application PhilCut n'a pas passé l'audit de Google pour YouTube,
  Google range les vidéos envoyées par API en « privé » : on les passe ensuite en public d'un clic dans YouTube Studio.
- Instagram, TikTok, Facebook : leurs API de publication demandent un compte professionnel et une validation de
  l'application par chaque réseau. En attendant : publication assistée — le bon fichier (format du réseau) est prêt,
  la légende est copiée, la page d'envoi du réseau s'ouvre, il reste à glisser le fichier.
"""
import json, os, time, urllib.error, urllib.parse, urllib.request

from .langue import _

RESEAUX = {
    "youtube": {"nom": "YouTube", "direct": True, "format": "16:9", "page": "https://studio.youtube.com/"},
    "shorts": {"nom": "YouTube Shorts", "direct": True, "format": "9:16", "page": "https://studio.youtube.com/"},
    "instagram": {"nom": "Instagram (Reels)", "direct": False, "format": "9:16", "page": "https://www.instagram.com/"},
    "tiktok": {"nom": "TikTok", "direct": False, "format": "9:16", "page": "https://www.tiktok.com/upload"},
    "facebook": {"nom": "Facebook", "direct": False, "format": "16:9", "page": "https://www.facebook.com/"},
}
VISIBILITES = [("private", _("Privée")), ("unlisted", _("Non répertoriée")), ("public", _("Publique"))]
CATEGORIES = {"voyage": "19", "personnes": "22", "auto": "2", "divertissement": "24", "science": "28"}


class ErreurPublication(Exception):
    pass


# ------------------------------------------------------------------ comptes YouTube (0.9.50 : plusieurs chaînes)
# Dans le coffre du système, sous « publication:youtube » : {"comptes": {id_chaine: {refresh_token, access_token, expire,
# nom}}, "actif": id_chaine}. L'ancien format (un seul jeu de jetons) est repris tel quel comme premier compte.
def _magasin():
    from . import coffre
    try:
        d = json.loads(coffre.lire("publication:youtube") or "{}")
    except ValueError:
        d = {}
    if d.get("refresh_token"):                                   # ancien format : un seul compte
        d = {"comptes": {"ancien": dict(d, nom=_("Ma chaîne"))}, "actif": "ancien"}
    d.setdefault("comptes", {})
    if d.get("actif") not in d["comptes"]:
        d["actif"] = next(iter(sorted(d["comptes"])), None)
    return d


def _ranger(d):
    from . import coffre
    if d.get("comptes"):
        coffre.enregistrer("publication:youtube", json.dumps(d))
    else:
        coffre.supprimer("publication:youtube")


def comptes_youtube():
    """[(id, nom de la chaîne)], par ordre alphabétique (accents ignorés)."""
    import unicodedata
    d = _magasin()
    return sorted(((k, v.get("nom") or k) for k, v in d["comptes"].items()),
                  key=lambda x: unicodedata.normalize("NFD", x[1]).encode("ascii", "ignore").decode().lower())


def compte_actif():
    return _magasin().get("actif")


def choisir_compte(ident):
    d = _magasin()
    if ident in d["comptes"]:
        d["actif"] = ident
        _ranger(d)


def youtube_relie(compte=None):
    d = _magasin()
    return bool((d["comptes"].get(compte) if compte else d["comptes"]) )


def _chaine(jeton):
    """(id, nom) de la chaîne YouTube du compte qui vient d'être relié."""
    req = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                                 headers={"Authorization": f"Bearer {jeton}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            items = json.loads(r.read().decode("utf-8")).get("items") or []
    except (urllib.error.URLError, OSError, ValueError):
        items = []
    if not items:
        return None, None
    return items[0].get("id"), (items[0].get("snippet") or {}).get("title")


def relier_youtube(journal=None, arret=lambda: False):
    """Relie une chaîne de plus (ou met à jour celle qui l'est déjà) ; elle devient la chaîne choisie. Renvoie son nom."""
    from . import oauth
    j = oauth.autoriser("youtube", journal=journal, arret=arret)
    ident, nom = _chaine(j.get("access_token", ""))
    d = _magasin()
    trouve = bool(nom)
    ident = ident or f"compte{len(d['comptes']) + 1}"
    nom = nom or _("Chaîne {n}", n=len(d["comptes"]) + 1)
    d["comptes"][ident] = dict(j, nom=nom)
    d["actif"] = ident
    _ranger(d)
    return {"id": ident, "nom": nom, "nom_trouve": trouve}


def renommer_compte(ident, nom):
    d = _magasin()
    if ident in d["comptes"] and nom.strip():
        d["comptes"][ident]["nom"] = nom.strip()
        _ranger(d)


def delier_youtube(compte=None):
    """Délie une chaîne (la chaîne choisie par défaut) ; les autres restent reliées."""
    d = _magasin()
    d["comptes"].pop(compte or d.get("actif"), None)
    d["actif"] = None
    _ranger(_magasin_apres(d))


def _magasin_apres(d):
    if d.get("actif") not in d["comptes"]:
        d["actif"] = next(iter(sorted(d["comptes"])), None)
    return d


def _acces(journal=None, compte=None):
    from . import oauth
    d = _magasin()
    cle = compte or d.get("actif")
    j = d["comptes"].get(cle) or {}
    if not j.get("refresh_token"):
        raise ErreurPublication(_("Compte YouTube non relié : bouton « Relier mon compte YouTube »."))
    if j.get("access_token") and j.get("expire", 0) > time.time():
        return j["access_token"]
    n = oauth.rafraichir("youtube", j["refresh_token"], journal)
    j.update(access_token=n["access_token"], expire=n["expire"])
    d["comptes"][cle] = j
    _ranger(d)
    return j["access_token"]


# ------------------------------------------------------------------ envoi YouTube
URL_ENVOI = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"


URL_VIGNETTE = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"


def envoyer_vignette(id_video, image, compte=None):
    """La vignette de la vidéo (JPG ou PNG, moins de 2 Mo) ; YouTube peut la refuser tant que la chaîne n'est pas validée
    par téléphone : on le dit, la vidéo reste envoyée. Renvoie None si c'est fait, sinon la raison."""
    if not (id_video and image and os.path.exists(image)):
        return _("pas de vignette choisie")
    with open(image, "rb") as f:
        donnees = f.read()
    type_ = "image/png" if image.lower().endswith(".png") else "image/jpeg"
    req = urllib.request.Request(URL_VIGNETTE + "?" + urllib.parse.urlencode({"videoId": id_video}), data=donnees, method="POST",
                                 headers={"Authorization": f"Bearer {_acces(compte=compte)}", "Content-Type": type_, "Content-Length": str(len(donnees))})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            r.read()
        return None
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return _("YouTube n'accepte les vignettes personnalisées qu'après validation de la chaîne par téléphone "
                     "(youtube.com/verify) : posez-la dans YouTube Studio")
        return _expliquer(e)
    except (urllib.error.URLError, OSError) as e:
        return str(getattr(e, "reason", e))


def envoyer_youtube(chemin, titre, description="", mots_clefs=(), visibilite="private", categorie="19", enfants=False,
                    progression=None, arret=lambda: False, morceau=8 * 1024 * 1024, compte=None):
    """Envoie la vidéo ; renvoie l'adresse de la vidéo sur YouTube. Reprend un morceau qui a échoué (réseau instable)."""
    taille = os.path.getsize(chemin)
    meta = {"snippet": {"title": (titre or os.path.splitext(os.path.basename(chemin))[0])[:100], "description": (description or "")[:4900],
                        "tags": [m for m in mots_clefs if m][:30], "categoryId": str(categorie)},
            "status": {"privacyStatus": visibilite, "selfDeclaredMadeForKids": bool(enfants)}}
    jeton = _acces(compte=compte)
    req = urllib.request.Request(URL_ENVOI, data=json.dumps(meta).encode("utf-8"), method="POST",
                                 headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(taille)})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            session = r.headers.get("Location")
    except urllib.error.HTTPError as e:
        raise ErreurPublication(_expliquer(e)) from e
    if not session:
        raise ErreurPublication(_("YouTube n'a pas ouvert l'envoi."))
    fait = 0
    essais = 0
    with open(chemin, "rb") as f:
        while fait < taille:
            if arret():
                raise InterruptedError()
            f.seek(fait)
            bloc = f.read(morceau)
            fin = fait + len(bloc) - 1
            req = urllib.request.Request(session, data=bloc, method="PUT",
                                         headers={"Content-Length": str(len(bloc)), "Content-Range": f"bytes {fait}-{fin}/{taille}"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    rep = json.loads(r.read().decode("utf-8") or "{}")
                    progression and progression(1.0)
                    return f"https://youtu.be/{rep.get('id')}" if rep.get("id") else ""
            except urllib.error.HTTPError as e:
                if e.code == 308:                                   # morceau reçu, on continue
                    plage = e.headers.get("Range")                  # « bytes=0-12345 »
                    fait = int(plage.split("-")[-1]) + 1 if plage else fin + 1
                    essais = 0
                    progression and progression(fait / taille)
                    continue
                if e.code >= 500 and essais < 5:
                    essais += 1
                    time.sleep(2 ** essais)
                    fait = _reprise(session, taille, fait)
                    continue
                raise ErreurPublication(_expliquer(e)) from e
            except (urllib.error.URLError, OSError):
                if essais >= 5:
                    raise
                essais += 1
                time.sleep(2 ** essais)
                fait = _reprise(session, taille, fait)
    raise ErreurPublication(_("Envoi interrompu."))


def _reprise(session, taille, defaut):
    """Demande à YouTube où il en est (après une coupure)."""
    req = urllib.request.Request(session, data=b"", method="PUT", headers={"Content-Length": "0", "Content-Range": f"bytes */{taille}"})
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        if e.code == 308:
            plage = e.headers.get("Range")
            return int(plage.split("-")[-1]) + 1 if plage else 0
    except Exception:       # noqa: BLE001
        pass
    return defaut


def _expliquer(e):
    try:
        d = json.loads(e.read().decode("utf-8"))
        raison = ((d.get("error") or {}).get("errors") or [{}])[0].get("reason", "")
        msg = (d.get("error") or {}).get("message", "")
    except Exception:       # noqa: BLE001
        raison, msg = "", ""
    if raison in ("quotaExceeded", "uploadLimitExceeded"):
        return _("YouTube refuse pour aujourd'hui (quota d'envois atteint) : réessayez demain.")
    if e.code in (401, 403) and "accessNotConfigured" in (raison + msg):
        return _("L'API YouTube n'est pas activée dans le projet Google de PhilCut.")
    if e.code == 401:
        return _("Accès YouTube expiré : reliez à nouveau votre compte.")
    return f"YouTube : HTTP {e.code} {raison} {msg}".strip()


# ------------------------------------------------------------------ publication assistée
def legende(titre, description, mots_clefs):
    tags = " ".join("#" + "".join(m.split()) for m in mots_clefs if m)[:500]
    return "\n\n".join(x for x in (titre, description, tags) if x)


def preparer_assistee(reseau, chemin, titre, description, mots_clefs):
    """Copie la légende, ouvre la page du réseau et le dossier du fichier. Renvoie le texte copié."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices, QGuiApplication
    texte = legende(titre, description, mots_clefs)
    QGuiApplication.clipboard().setText(texte)
    QDesktopServices.openUrl(QUrl(RESEAUX[reseau]["page"]))
    QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(chemin)))
    return texte
