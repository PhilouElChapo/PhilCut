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
     "modele_image": "fal-ai/kling-video/v3/pro/image-to-video", "prix_s": 0.112, "prix_s_son": 0.168, "durees": [5, 10], "son_param": "generate_audio",
     "note": _("mouvements réalistes, personnes")},
    {"id": "kling-o3-ref", "fournisseur": "fal", "nom": "Kling O3 Référence : personnage fidèle (fal)",
     "modele": "fal-ai/kling-video/o3/standard/reference-to-video", "references": True, "image_fin": True,
     "prix_s": 0.084, "prix_s_son": 0.112, "durees": list(range(3, 16)), "son_param": "generate_audio",
     "note": _("garde le visage et la tenue d'après la fiche du personnage, image de départ et d'arrivée, jusqu'à 15 s")},
    {"id": "seedance-2", "fournisseur": "fal", "nom": "Seedance 2.0 (fal)", "modele": "bytedance/seedance-2.0/text-to-video",
     "modele_image": "bytedance/seedance-2.0/image-to-video", "prix_s": 0.30, "durees": list(range(4, 16)),
     "son_param": "generate_audio", "note": _("plans jusqu'à 15 s")},
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


def prix(m, duree, son=False):
    """Prix estimé maximal en $ : Omni choisit lui-même la durée (jusqu'à 10 s) ; son=True : le moteur fabrique aussi le son
    (voix comprises), plus cher chez certains."""
    if m.get("duree_auto"):
        duree = max(duree, 10)
    elif m.get("durees"):
        duree = min((d for d in m["durees"] if d >= duree), default=max(m["durees"]))
    return round(float((m.get("prix_s_son") if son else None) or m.get("prix_s", 0.2)) * duree, 2)


def duree_reelle(m, duree):
    if m.get("durees"):
        return min((d for d in m["durees"] if d >= duree), default=max(m["durees"]))
    return duree


# ------------------------------------------------------------------ génération
def generer(params, ident, consigne, sortie, duree=5, format_="16:9", image=None, progression=None, arret=lambda: False, son=False,
            references=None, image_fin=None):
    """son : le moteur fabrique aussi le son et fait parler (un seul réglage, « Répliques » de la Séquence IA) ; sinon, chez
    les moteurs qui le permettent, aucun son n'est fabriqué (PhilCut pose le sien ; Omni en fabrique toujours un, coupé au
    montage).
    references (0.9.72, moteurs « Référence ») : [(nom, [images])] — un « élément » par personnage, que le moteur garde
    identique ; image_fin : la dernière image imposée (le plan doit y arriver)."""
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
    if m.get("references"):
        return generer_reference(k, m, consigne, sortie, duree, format_, image, image_fin, references, progression, arret, son)
    return generer_fal(k, m, consigne, sortie, duree, format_, image, progression, arret, son)


def corps_reference(consigne, duree, format_, depart_url=None, fin_url=None, elements=None, m=None, son=False):
    """Demande « reference to video » (Kling O1/O3) : chaque personnage est un élément (@Element1…) avec une image de face et
    des images d'appui ; le texte commence par dire qui est qui, pour que le moteur relie les noms aux images."""
    elements = [e for e in (elements or []) if e.get("frontal_image_url")][:3]
    noms = [f"@Element{i + 1} is {e['nom']}" for i, e in enumerate(elements) if e.get("nom")]
    texte = ("; ".join(noms) + ". " if noms else "") + consigne
    if elements:
        texte += " Keep @" + ", @".join(f"Element{i + 1}" for i in range(len(elements))) + \
                 " exactly identical to the reference images: same face, hair, body and outfit."
    corps = {"prompt": texte, "duration": str(int(duree_reelle(m or {"durees": list(range(3, 16))}, duree))),
             "aspect_ratio": "9:16" if format_ == "9:16" else "16:9"}
    if elements:
        corps["elements"] = [{"frontal_image_url": e["frontal_image_url"],
                              "reference_image_urls": list(e.get("reference_image_urls") or [])[:3]} for e in elements]
    if depart_url:
        corps["start_image_url"] = depart_url
    if fin_url:
        corps["end_image_url"] = fin_url
    if (m or {}).get("son_param"):
        corps[m["son_param"]] = bool(son)
    return corps


def generer_reference(cle, m, consigne, sortie, duree=5, format_="16:9", image=None, image_fin=None, references=None,
                      progression=None, arret=lambda: False, son=False):
    """Moteur « Référence » : images envoyées sur le stockage fal, puis la demande ; la planche du personnage sert d'image de
    face, ses autres images d'appui."""
    av = progression or (lambda f: None)
    av(0.01)
    elements = []
    for nom, images in (references or [])[:3]:
        images = [i for i in images if i and os.path.exists(i)]
        if not images:
            continue
        urls = [televerser(cle, i) for i in images[:4]]
        elements.append({"nom": nom, "frontal_image_url": urls[0], "reference_image_urls": urls[1:]})
    depart = televerser(cle, image) if image and os.path.exists(image) else None
    fin = televerser(cle, image_fin) if image_fin and os.path.exists(image_fin) else None
    corps = corps_reference(consigne, duree, format_, depart, fin, elements, m, son)
    return attendre_fal(cle, m["modele"], corps, sortie, progression, arret)


# ------------------------------------------------------------------ crédit restant (0.9.72)
PAGES_CREDIT = {"fal": "https://fal.ai/dashboard/usage-billing/credits", "google": "https://aistudio.google.com/usage"}


def credit(params, fournisseur):
    """Crédit restant quand le fournisseur le dit : (montant, devise) ou None. fal.ai le donne (API Platform) ; Google ne
    publie pas le solde d'une clef Gemini (facturation Cloud) : None, et le bouton mène à la page de suivi."""
    k = clef(params, fournisseur)
    if not k or fournisseur != "fal":
        return None
    try:
        r = _http("https://api.fal.ai/v1/account/billing?expand=credits", k, delai=15)
    except Exception:          # noqa: BLE001 : clef sans droit de lecture du solde, hors ligne
        return None
    c = r.get("credits") or {}
    if c.get("current_balance") is None:
        return None
    return float(c["current_balance"]), c.get("currency") or "USD"


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


def generer_fal(cle, m, consigne, sortie, duree=5, format_="16:9", image=None, progression=None, arret=lambda: False, son=False):
    """File d'attente fal.ai : envoi, suivi de l'état, récupération de la vidéo (video.url)."""
    point = (m.get("modele_image") if image and m.get("modele_image") else m["modele"]).strip("/")
    corps = {"prompt": consigne, "duration": str(int(duree_reelle(m, duree))), "aspect_ratio": "9:16" if format_ == "9:16" else "16:9"}
    if image:
        corps["image_url"] = _data_uri(image)
    if m.get("son_param"):
        # 0.9.68 : pas de son fabriqué par le moteur (voix inventées, musique) sauf demande : PhilCut pose le sien, moins cher
        corps[m["son_param"]] = bool(son)
    return attendre_fal(cle, point, corps, sortie, progression, arret)


def attendre_fal(cle, point, corps, sortie, progression=None, arret=lambda: False, attente=300.0):
    """Une demande à la file d'attente de fal.ai, suivie jusqu'au bout ; la vidéo rendue est téléchargée dans `sortie`."""
    res = demande_fal(cle, point, corps, progression, arret, attente)
    url = ((res.get("video") or {}).get("url")) or next((v.get("url") for v in (res.get("videos") or []) if isinstance(v, dict)), None)
    if not url:
        raise ErreurGenerateur(_("fal.ai n'a renvoyé aucune vidéo : {r}", r=str(res)[:200]))
    telecharger(url, sortie)
    progression and progression(1.0)
    return sortie


def telecharger(url, sortie):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "PhilCut"}), timeout=600) as r2, open(sortie, "wb") as f:
        f.write(r2.read())
    return sortie


def demande_fal(cle, point, corps, progression=None, arret=lambda: False, attente=300.0):
    """Demande à la file d'attente de fal.ai suivie jusqu'au bout ; renvoie la réponse (JSON) du modèle."""
    point = point.strip("/")
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
        progression and progression(min(0.9, (time.time() - debut) / attente))
        if etat == "COMPLETED":
            break
        if etat in ("FAILED", "ERROR", "CANCELLED"):
            raise ErreurGenerateur(_("fal.ai : génération refusée ou en échec ({e}).", e=st.get("error") or etat))
        if time.time() - debut > 1500:
            raise ErreurGenerateur(_("La génération met trop de temps ; réessayez plus tard."))
    return _http(reponse_url, cle)


FAL_REST = "https://rest.fal.ai"
TYPES_FICHIERS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".wav": "audio/wav",
                  ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}


def televerser(cle, chemin):
    """Envoie un fichier sur le stockage de fal.ai (même méthode que la bibliothèque officielle fal-client) ; renvoie son
    adresse, que le modèle lit. Repli : le stockage « initiate » puis PUT."""
    ext = os.path.splitext(chemin)[1].lower()
    typ = TYPES_FICHIERS.get(ext, "application/octet-stream")
    with open(chemin, "rb") as f:
        donnees = f.read()
    nom = os.path.basename(chemin)
    try:
        jeton = _http(f"{FAL_REST}/storage/auth/token?storage_type=fal-cdn-v3", cle, {})
        req = urllib.request.Request(jeton["base_url"].rstrip("/") + "/files/upload", data=donnees, method="POST",
                                     headers={"Authorization": f"{jeton['token_type']} {jeton['token']}", "Content-Type": typ,
                                              "X-Fal-File-Name": nom, "User-Agent": "PhilCut"})
        with urllib.request.urlopen(req, timeout=600) as r:
            url = json.loads(r.read().decode("utf-8")).get("access_url")
        if url:
            return url
    except ErreurGenerateur as e:
        if "refusée" in str(e):
            raise
    except Exception:      # noqa: BLE001 : on essaie l'autre méthode
        pass
    init = _http(f"{FAL_REST}/storage/upload/initiate?storage_type=gcs", cle, {"file_name": nom, "content_type": typ})
    req = urllib.request.Request(init["upload_url"], data=donnees, method="PUT", headers={"Content-Type": typ})
    with urllib.request.urlopen(req, timeout=600):
        pass
    return init["file_url"]


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
