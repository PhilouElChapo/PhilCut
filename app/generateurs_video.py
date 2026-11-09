"""Générateurs de plans vidéo par IA, en paiement à l'usage, avec la clef de chaque utilisateur.

Plusieurs fournisseurs, une seule façon de faire : consigne (et image de départ facultative) -> clip ramené dans la
timeline, prix estimé affiché et confirmation avant chaque envoi.
- google : Gemini Omni Flash, avec la clef Gemini (Google AI Studio)
- fal    : agrégateur fal.ai, une clef pour des dizaines de modèles (Kling, Seedance…), paiement à l'usage ;
           l'API officielle de Kling, elle, se vend par paquets (plusieurs centaines de dollars) : fal évite cet achat.
La liste des modèles s'enrichit sans réinstaller (catalogue en ligne catalogue/generateurs.json), et chacun peut ajouter
l'identifiant d'un modèle fal qu'il connaît (Préférences › IA). Prix relevés le 4 novembre 2026, indicatifs.
"""
import base64, json, os, time, urllib.error, urllib.request

from .langue import _

FOURNISSEURS = {
    "google": {"nom": "Google (Gemini Omni Flash)", "clef": "clef_gemini", "page": "https://aistudio.google.com/apikey",
               "etapes": [_("Ouvrez Google AI Studio avec votre compte Google, menu « Get API key » (Clefs API)."),
                          _("« Créer une clef API », dans un projet à votre nom ; activez la facturation du projet pour la vidéo."),
                          _("Copiez la clef et collez-la ici. Conseil : fixez un budget dans la console Google Cloud.")]},
    "fal": {"nom": "fal.ai (Kling, Seedance et autres)", "clef": "clef_fal", "page": "https://fal.ai/dashboard/keys",
            "etapes": [_("Créez un compte sur fal.ai (Google ou e-mail) et ajoutez du crédit (paiement à l'usage, sans abonnement)."),
                       _("Menu « Keys » › « Add key » : donnez-lui le nom PhilCut."),
                       _("Copiez la clef (forme « identifiant:secret ») et collez-la ici.")]},
}

MODELES = [
    {"id": "omni-360p", "fournisseur": "google", "nom": "Gemini Omni Flash 360p (brouillon)", "modele": "gemini-omni-1.1-flash",
     "resolution": "360p", "prix_s": 0.035, "duree_auto": True, "note": _("le moins cher, pour essayer une idée")},
    {"id": "omni-720p", "fournisseur": "google", "nom": "Gemini Omni Flash 720p", "modele": "gemini-omni-1.1-flash",
     "resolution": "720p", "prix_s": 0.10, "duree_auto": True, "note": _("bon compromis")},
    {"id": "omni12-720p", "fournisseur": "google", "nom": "Gemini Omni 1.2 Flash 720p (nouveau)", "modele": "gemini-omni-1.2-flash",
     "repli": "gemini-omni-1.1-flash", "resolution": "720p", "prix_s": 0.10, "duree_auto": True,
     "note": _("version de novembre 2026 : personnages plus stables ; prix indicatif à confirmer au premier essai")},
    {"id": "omni-1080p", "fournisseur": "google", "nom": "Gemini Omni Flash 1080p", "modele": "gemini-omni-1.1-flash",
     "resolution": "1080p", "prix_s": 0.10, "duree_auto": True, "note": _("720p agrandi par Google")},
    {"id": "kling-3-pro", "fournisseur": "fal", "nom": "Kling 3.0 Pro (fal)", "modele": "fal-ai/kling-video/v3/pro/text-to-video",
     "modele_image": "fal-ai/kling-video/v3/pro/image-to-video", "prix_s": 0.14, "durees": [5, 10],
     "note": _("mouvements réalistes, personnes")},
    {"id": "seedance-2", "fournisseur": "fal", "nom": "Seedance 2.0 (fal)", "modele": "bytedance/seedance-2.0/text-to-video",
     "modele_image": "bytedance/seedance-2.0/image-to-video", "prix_s": 0.30, "durees": list(range(4, 16)),
     "note": _("son généré, plans jusqu'à 15 s")},
]


class ErreurGenerateur(Exception):
    pass


# ------------------------------------------------------------------ catalogue
def _catalogue_en_ligne():
    from .config import dossier_donnees
    copie = os.path.join(dossier_donnees(), "generateurs.json")
    url = "https://raw.githubusercontent.com/PhilouElChapo/PhilCut/main/catalogue/generateurs.json"
    if not os.path.exists(copie) or time.time() - os.path.getmtime(copie) > 86400:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "PhilCut"}), timeout=6) as r:
                donnees = r.read()
            json.loads(donnees.decode("utf-8"))
            with open(copie, "wb") as f:
                f.write(donnees)
        except Exception:       # noqa: BLE001 : hors ligne, on garde ce qu'on a
            pass
    try:
        with open(copie, encoding="utf-8") as f:
            return json.load(f).get("modeles", [])
    except Exception:           # noqa: BLE001
        return []


def modeles(params=None, en_ligne=True):
    """Modèles connus : intégrés, puis catalogue en ligne (qui peut en corriger le prix), puis ceux ajoutés par l'utilisateur."""
    par_id = {m["id"]: dict(m) for m in MODELES}
    for m in (_catalogue_en_ligne() if en_ligne else []):
        if m.get("id") and m.get("fournisseur") in FOURNISSEURS and m.get("modele"):
            par_id[m["id"]] = dict(par_id.get(m["id"], {}), **m)
    for m in (params or {}).get("modeles_video_perso") or []:
        if m.get("modele"):
            mid = "perso:" + m["modele"]
            par_id[mid] = {"id": mid, "fournisseur": "fal", "nom": m.get("nom") or m["modele"], "modele": m["modele"],
                           "modele_image": m.get("modele_image") or "", "prix_s": float(m.get("prix_s") or 0.2),
                           "note": _("ajouté par vous")}
    return list(par_id.values())


def modele(ident, params=None):
    return next((m for m in modeles(params) if m["id"] == ident), None)


def clef(params, fournisseur):
    from .ia import nettoyer_clef
    return nettoyer_clef((params or {}).get(FOURNISSEURS[fournisseur]["clef"], ""))


def disponibles(params):
    """Modèles utilisables avec les clefs saisies sur ce poste."""
    return [m for m in modeles(params) if clef(params, m["fournisseur"])]


def prix(m, duree):
    """Prix estimé maximal en $ : Omni choisit lui-même la durée (jusqu'à 10 s)."""
    if m.get("duree_auto"):
        duree = max(duree, 10)
    elif m.get("durees"):
        duree = min((d for d in m["durees"] if d >= duree), default=max(m["durees"]))
    return round(float(m.get("prix_s", 0.2)) * duree, 2)


def duree_reelle(m, duree):
    if m.get("durees"):
        return min((d for d in m["durees"] if d >= duree), default=max(m["durees"]))
    return duree


# ------------------------------------------------------------------ génération
def generer(params, ident, consigne, sortie, duree=5, format_="16:9", image=None, progression=None, arret=lambda: False):
    m = modele(ident, params)
    if not m:
        raise ErreurGenerateur(_("Modèle inconnu : {m}", m=ident))
    k = clef(params, m["fournisseur"])
    if not k:
        raise ErreurGenerateur(_("Clef {f} absente : Préférences › IA › Connecter une IA.", f=FOURNISSEURS[m["fournisseur"]]["nom"]))
    if m["fournisseur"] == "google":
        from .fabrique import generer_omni
        try:
            return generer_omni(k, consigne, sortie, m["modele"], duree, format_, image, m.get("resolution", "720p"), progression, arret)
        except InterruptedError:
            raise
        except Exception as e:                    # noqa: BLE001 : modèle pas encore ouvert à cette clef : la version précédente, éprouvée
            if m.get("repli") and (getattr(e, "code", None) == 404 or any(x in str(e) for x in ("404", "NOT_FOUND", "not found", "not supported"))):
                return generer_omni(k, consigne, sortie, m["repli"], duree, format_, image, m.get("resolution", "720p"), progression, arret)
            raise
    return generer_fal(k, m, consigne, sortie, duree, format_, image, progression, arret)


FAL_FILE = "https://queue.fal.run"


def _http(url, cle, corps=None, methode=None, delai=120):
    entetes = {"Authorization": f"Key {cle}", "Content-Type": "application/json", "User-Agent": "PhilCut"}
    req = urllib.request.Request(url, data=json.dumps(corps).encode("utf-8") if corps is not None else None, headers=entetes,
                                 method=methode or ("POST" if corps is not None else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code in (401, 403):
            raise ErreurGenerateur(_("Clef fal.ai refusée (vérifiez-la, et le crédit du compte) : {d}", d=detail)) from e
        raise ErreurGenerateur(f"HTTP {e.code} : {detail}") from e


def _data_uri(chemin):
    mime = "image/png" if chemin.lower().endswith(".png") else "image/jpeg"
    with open(chemin, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def generer_fal(cle, m, consigne, sortie, duree=5, format_="16:9", image=None, progression=None, arret=lambda: False):
    """File d'attente fal.ai : envoi, suivi de l'état, récupération de la vidéo (video.url)."""
    point = (m.get("modele_image") if image and m.get("modele_image") else m["modele"]).strip("/")
    corps = {"prompt": consigne, "duration": str(int(duree_reelle(m, duree))), "aspect_ratio": "9:16" if format_ == "9:16" else "16:9"}
    if image:
        corps["image_url"] = _data_uri(image)
    r = _http(f"{FAL_FILE}/{point}", cle, corps)
    statut_url = r.get("status_url") or f"{FAL_FILE}/{point}/requests/{r.get('request_id')}/status"
    reponse_url = r.get("response_url") or f"{FAL_FILE}/{point}/requests/{r.get('request_id')}"
    if not r.get("request_id") and not r.get("status_url"):
        raise ErreurGenerateur(_("Réponse inattendue de fal.ai : {r}", r=str(r)[:200]))
    debut = time.time()
    while True:
        if arret():
            try:
                _http(f"{FAL_FILE}/{point}/requests/{r.get('request_id')}/cancel", cle, methode="PUT", corps={})
            except Exception:       # noqa: BLE001
                pass
            raise InterruptedError()
        time.sleep(5)
        st = _http(statut_url, cle)
        etat = (st.get("status") or "").upper()
        progression and progression(min(0.9, (time.time() - debut) / 300))
        if etat == "COMPLETED":
            break
        if etat in ("FAILED", "ERROR", "CANCELLED"):
            raise ErreurGenerateur(_("fal.ai : génération refusée ou en échec ({e}).", e=st.get("error") or etat))
        if time.time() - debut > 1500:
            raise ErreurGenerateur(_("La génération met trop de temps ; réessayez plus tard."))
    res = _http(reponse_url, cle)
    url = ((res.get("video") or {}).get("url")) or next((v.get("url") for v in (res.get("videos") or []) if isinstance(v, dict)), None)
    if not url:
        raise ErreurGenerateur(_("fal.ai n'a renvoyé aucune vidéo : {r}", r=str(res)[:200]))
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "PhilCut"}), timeout=600) as r2, open(sortie, "wb") as f:
        f.write(r2.read())
    progression and progression(1.0)
    return sortie


# ------------------------------------------------------------------ test des clefs (gratuit)
def tester_clef(fournisseur, cle):
    """(ok, message) sans rien générer ni payer."""
    if not cle:
        return False, _("Aucune clef saisie.")
    try:
        if fournisseur == "google":
            req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": cle})
            with urllib.request.urlopen(req, timeout=20) as r:
                n = len(json.loads(r.read().decode("utf-8")).get("models", []))
            return True, _("Clef Google valide : {n} modèles ouverts.", n=n)
        if fournisseur == "fal":
            # état d'une demande inexistante : 401/403 = clef refusée ; 404/400/422 = clef acceptée
            req = urllib.request.Request(f"{FAL_FILE}/fal-ai/fast-sdxl/requests/00000000-0000-0000-0000-000000000000/status",
                                         headers={"Authorization": f"Key {cle}", "User-Agent": "PhilCut"})
            try:
                urllib.request.urlopen(req, timeout=20)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    return False, _("Clef fal.ai refusée.")
            return True, _("Clef fal.ai acceptée (le crédit du compte se vérifie sur fal.ai).")
    except urllib.error.HTTPError as e:
        return False, _("Clef refusée (HTTP {c}).", c=e.code)
    except Exception as e:      # noqa: BLE001
        return False, _("Test impossible : {e}", e=e)
    return False, "?"
