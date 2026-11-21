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
    # 0.9.99 : Higgsfield, paiement à l'usage en dollars (recharge de 5 $ au moins), sans abonnement : l'API est un produit
    # séparé de l'abonnement du site (les crédits de l'un ne paient pas l'autre)
    "higgsfield": {"nom": "Higgsfield (Kling, Hailuo et autres)", "clef": "clef_higgsfield", "page": "https://open.higgsfield.ai/api-keys",
                   "etapes": [_("Ouvrez la console développeur de l'API, open.higgsfield.ai (pas le site higgsfield.ai : ses crédits et son abonnement ne "
                                "servent pas à l'API), créez le compte et rechargez le solde en dollars (5 $ au moins, sans abonnement)."),
                              _("Menu « API keys » › créez une clef nommée PhilCut : elle a un identifiant et un secret."),
                              _("Collez « identifiant:secret » ici (les deux, séparés par deux-points).")]},
    # 0.9.99 : HeyGen, pour le rendu cloud des animations HyperFrames (pas de plans vidéo ici)
    "heygen": {"nom": "HeyGen (rendu des animations HyperFrames)", "clef": "clef_heygen", "page": "https://platform.heygen.com/api-keys",
               "etapes": [_("Créez un compte HeyGen, puis ouvrez Paramètres › API."),
                          _("Achetez du crédit API (paiement à l'usage, sans abonnement) et créez une clef API."),
                          _("Copiez la clef et collez-la ici : le crédit restant s'affichera dans PhilCut.")]},
}
POUR_VIDEO = ("google", "fal", "higgsfield")        # fournisseurs qui fabriquent des plans vidéo

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
     "modele": "fal-ai/kling-video/o3/standard/reference-to-video", "references": True, "image_fin": True, "multi": True,
     "prix_s": 0.084, "prix_s_son": 0.112, "durees": list(range(3, 16)), "son_param": "generate_audio",
     "note": _("garde le visage et la tenue d'après la fiche du personnage, image de départ et d'arrivée, jusqu'à 15 s")},
    {"id": "seedance-2", "fournisseur": "fal", "nom": "Seedance 2.0 (fal)", "modele": "bytedance/seedance-2.0/text-to-video",
     "modele_image": "bytedance/seedance-2.0/image-to-video", "prix_s": 0.30, "durees": list(range(4, 16)),
     "son_param": "generate_audio", "note": _("plans jusqu'à 15 s")},
    # 0.9.99 : Higgsfield (API à l'usage) ; chemins de leur spécification OpenAPI ; prix indicatifs relevés le 20/11/2026,
    # corrigés par le catalogue en ligne s'ils changent
    {"id": "hf-kling-25-pro", "fournisseur": "higgsfield", "nom": "Kling 2.5 Turbo Pro (Higgsfield)",
     "modele": "kling-video/v2.5-turbo/pro/text-to-video", "modele_image": "kling-video/v2.5-turbo/pro/image-to-video",
     "prix_s": 0.07, "durees": [5, 10], "note": _("prix indicatif ; vérifiez-le dans la console Higgsfield")},
    # 1.0.2 : Seedance 2.5 (texte → vidéo seulement ; page de la console relevée le 20/11/2026 : 4 à 30 s, 480p ou 720p,
    # formats 16:9, 4:3, 1:1, 3:4, 9:16, 21:9, son par generate_audio, « from 0.144 / s »)
    {"id": "hf-seedance-25", "fournisseur": "higgsfield", "nom": "Seedance 2.5 (Higgsfield)",
     "modele": "bytedance/seedance-2.5/text-to-video", "prix_s": 0.144, "durees": list(range(4, 31)), "resolution": "720p",
     "formats": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9"], "son_param": "generate_audio",
     "note": _("texte seulement (pas d'image de départ), jusqu'à 30 s ; prix indicatif")},
    {"id": "hf-hailuo-23", "fournisseur": "higgsfield", "nom": "Hailuo 2.3 (Higgsfield)",
     "modele": "minimax/hailuo-2.3/standard/text-to-video", "modele_image": "minimax/hailuo-2.3/standard/image-to-video",
     "prix_s": 0.05, "durees": [6, 10], "note": _("mouvements vifs ; prix indicatif")},
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
            references=None, image_fin=None, multi=None):
    """son : le moteur fabrique aussi le son et fait parler (un seul réglage, « Répliques » de la Séquence IA) ; sinon, chez
    les moteurs qui le permettent, aucun son n'est fabriqué (PhilCut pose le sien ; Omni en fabrique toujours un, coupé au
    montage).
    references (0.9.72, moteurs « Référence ») : [(nom, [images])] — un « élément » par personnage, que le moteur garde
    identique ; image_fin : la dernière image imposée (le plan doit y arriver).
    multi (0.9.90, moteurs « multi ») : [(consigne, durée)] — plusieurs plans d'un même moment faits d'un seul calcul ; la
    durée totale est leur somme (15 s au plus)."""
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
    if m["fournisseur"] == "higgsfield":
        return generer_higgsfield(k, m, consigne, sortie, duree, image, progression, arret, format_=format_, son=son)
    if m.get("references"):
        return generer_reference(k, m, consigne, sortie, duree, format_, image, image_fin, references, progression, arret, son,
                                 multi if m.get("multi") else None)
    return generer_fal(k, m, consigne, sortie, duree, format_, image, progression, arret, son)


MAX_PROMPT_PLAN = 500      # Kling O3, chaque plan d'un multi_prompt : 512 caractères au plus (marge gardée)


def raccourcir(texte, n):
    """Le texte en n caractères au plus, coupé à la fin d'une phrase entière si possible, sinon à un mot."""
    t = " ".join(str(texte or "").split())
    if len(t) <= n:
        return t
    coupe = t[:n]
    fin = max(coupe.rfind(". "), coupe.rfind("! "), coupe.rfind("? "))
    if fin > n * 0.5:
        return coupe[:fin + 1]
    return coupe[:coupe.rfind(" ")].rstrip(",;:") if " " in coupe else coupe


def corps_reference(consigne, duree, format_, depart_url=None, fin_url=None, elements=None, m=None, son=False, multi=None):
    """Demande « reference to video » (Kling O1/O3) : chaque personnage est un élément (@Element1…) avec une image de face et
    des images d'appui ; le texte commence par dire qui est qui, pour que le moteur relie les noms aux images."""
    elements = [e for e in (elements or []) if e.get("frontal_image_url")][:4]
    noms = [f"@Element{i + 1} is {e['nom']}" for i, e in enumerate(elements) if e.get("nom")]
    avant = "; ".join(noms) + ". " if noms else ""
    apres = (" Keep @" + ", @".join(f"Element{i + 1}" for i in range(len(elements))) +
             " exactly identical to the reference images: same face, hair, body and outfit.") if elements else ""
    corps = {"prompt": avant + consigne + apres, "duration": str(int(duree_reelle(m or {"durees": list(range(3, 16))}, duree))),
             "aspect_ratio": "9:16" if format_ == "9:16" else "16:9"}
    if multi:
        # 0.9.90 : un plan par élément, durées entières de 1 à 15 s, somme ≤ 15 ; le moteur les enchaîne en gardant gestes,
        # lumière et visages d'un plan à l'autre (« prompt » et « multi_prompt » s'excluent)
        plans = [(t, max(1, int(round(float(d))))) for t, d in multi][:6]
        corps.pop("prompt")
        # 0.9.96 : Kling refuse un plan de plus de 512 caractères (erreur 422) : noms des éléments en abrégé, rappel court,
        # consigne raccourcie à la dernière phrase entière qui tient
        avant_c = "; ".join(f"@Element{i + 1}={n}" for i, n in enumerate(x.get("nom", "") for x in (elements or []))) \
            if elements else ""
        avant_c = (avant_c + ". ") if avant_c else ""
        apres_c = " Keep elements identical to references." if elements else ""
        corps["multi_prompt"] = [{"prompt": avant_c + raccourcir(t, MAX_PROMPT_PLAN - len(avant_c) - len(apres_c)) + apres_c,
                                  "duration": str(d)} for t, d in plans]
        corps["duration"] = str(min(15, max(3, sum(d for _t, d in plans))))
        corps["shot_type"] = "customize"
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


MINI_FAL = 512        # fal refuse une image de référence de moins de 300 px de côté : marge prise


RAPPORT_MIN, RAPPORT_MAX = 0.4, 2.5        # rapport largeur / hauteur accepté par fal pour les images de référence


def assez_grande(chemin, mini=MINI_FAL):
    """L'image si ses deux côtés font au moins `mini` px, sinon une copie agrandie (côté court = mini, bords nets,
    PNG à côté). 0.9.86 : les découpes de personnes partaient trop petites (« image_too_small »)."""
    from PySide6.QtGui import QImage, QPainter, QColor
    from PySide6.QtCore import Qt
    img = QImage(chemin)
    if img.isNull():
        return chemin
    # 1.1.11 (Philippe, 22/11 00h26 : 422 « aspect ratio should be between 0.4 and 2.5 ») : une image trop allongée (planche en
    # bandeau, découpe très étroite) est complétée par des bords gris clair jusqu'à un rapport accepté, sans rien couper
    r = img.width() / max(1, img.height())
    if r > RAPPORT_MAX or r < RAPPORT_MIN:
        if r > RAPPORT_MAX:
            L, H = img.width(), round(img.width() / (RAPPORT_MAX - 0.1))
        else:
            L, H = round(img.height() * (RAPPORT_MIN + 0.02)), img.height()
        fond = QImage(L, H, QImage.Format_RGB32)
        fond.fill(QColor(205, 205, 205))
        pe = QPainter(fond)
        pe.drawImage((L - img.width()) // 2, (H - img.height()) // 2, img)
        pe.end()
        img = fond
        chemin = os.path.splitext(chemin)[0] + "_cadre.png"
        img.save(chemin)
    if min(img.width(), img.height()) >= mini:
        return chemin
    k = mini / max(1, min(img.width(), img.height()))
    grande = img.scaled(round(img.width() * k), round(img.height() * k), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    sortie = os.path.splitext(chemin)[0] + f"_{mini}.png"
    grande.save(sortie)
    return sortie


def generer_reference(cle, m, consigne, sortie, duree=5, format_="16:9", image=None, image_fin=None, references=None,
                      progression=None, arret=lambda: False, son=False, multi=None):
    """Moteur « Référence » : images envoyées sur le stockage fal, puis la demande ; la planche du personnage sert d'image de
    face, ses autres images d'appui."""
    av = progression or (lambda f: None)
    av(0.01)
    elements = []
    for nom, images in (references or [])[:4]:
        images = [i for i in images if i and os.path.exists(i)]
        if not images:
            continue
        urls = [televerser(cle, assez_grande(i)) for i in images[:4]]
        elements.append({"nom": nom, "frontal_image_url": urls[0], "reference_image_urls": urls[1:]})
    depart = televerser(cle, assez_grande(image)) if image and os.path.exists(image) else None
    fin = televerser(cle, assez_grande(image_fin)) if image_fin and os.path.exists(image_fin) else None
    corps = corps_reference(consigne, duree, format_, depart, fin, elements, m, son, multi)
    return attendre_fal(cle, m["modele"], corps, sortie, progression, arret)


# ------------------------------------------------------------------ crédit restant (0.9.72)
PAGES_CREDIT = {"anthropic": "https://console.anthropic.com/settings/billing", "fal": "https://fal.ai/dashboard/usage-billing/credits",
                "google": "https://aistudio.google.com/usage", "heygen": "https://platform.heygen.com/billing",
                "higgsfield": "https://open.higgsfield.ai/api-keys"}


def credit(params, fournisseur):
    """Crédit restant quand le fournisseur le dit : (montant, devise) ou None. fal.ai le donne (API Platform) ; Google ne
    publie pas le solde d'une clef Gemini (facturation Cloud) : None, et le bouton mène à la page de suivi."""
    k = clef(params, fournisseur)
    if k and fournisseur == "heygen":
        from .motion_html import credit_heygen
        return credit_heygen(k)
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


# ------------------------------------------------------------------ Higgsfield (0.9.99)
HIGGSFIELD = "https://api.higgsfield.ai"


def _http_hf(url, cle, corps=None, delai=120):
    import uuid
    entetes = {"Authorization": f"Key {cle}", "Content-Type": "application/json", "User-Agent": "PhilCut", "Accept": "application/json"}
    if corps is not None:
        entetes["Idempotency-Key"] = str(uuid.uuid4())
    req = urllib.request.Request(url, data=json.dumps(corps).encode("utf-8") if corps is not None else None, headers=entetes,
                                 method="POST" if corps is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code in (401, 403):
            raise ErreurGenerateur(_("Clef Higgsfield refusée (forme « identifiant:secret ») : {d}", d=detail)) from e
        if e.code == 402 or "balance" in detail.lower() or "insufficient" in detail.lower():
            raise ErreurGenerateur(_("Solde Higgsfield épuisé (rien n'a été fabriqué ni payé) : rechargez-le dans la console. {d}",
                                     d=detail)) from e
        raise ErreurGenerateur(f"Higgsfield HTTP {e.code} : {detail}") from e


def generer_higgsfield(cle, m, consigne, sortie, duree=5, image=None, progression=None, arret=lambda: False, attente=600.0,
                       format_="16:9", son=False):
    """File d'attente Higgsfield : envoi, suivi (status_url), vidéo téléchargée (video.url)."""
    point = (m.get("modele_image") if image and m.get("modele_image") else m["modele"]).strip("/")
    corps = {"prompt": consigne, "duration": int(duree_reelle(m, duree))}
    if image and m.get("modele_image"):
        corps["image_url"] = _data_uri(image)
    if m.get("formats"):                          # 1.0.2 : Seedance 2.5 (page de la console) : format, définition, son
        corps["aspect_ratio"] = format_ if format_ in m["formats"] else "16:9"
    if m.get("resolution"):
        corps["resolution"] = m["resolution"]
    if m.get("son_param"):
        corps[m["son_param"]] = bool(son)
    r = _http_hf(f"{HIGGSFIELD}/{point}", cle, corps)
    url_etat = r.get("status_url") or f"{HIGGSFIELD}/requests/{r.get('request_id')}/status"
    debut = time.time()
    while True:
        if arret():
            try:
                _http_hf(r.get("cancel_url") or url_etat.replace("/status", "/cancel"), cle, {})
            except Exception:      # noqa: BLE001
                pass
            raise InterruptedError()
        time.sleep(3)
        e = _http_hf(url_etat, cle)
        st = e.get("status")
        if progression:
            progression(min(0.95, (time.time() - debut) / 150), _("Higgsfield : {s}", s={"queued": _("en file d'attente"),
                                                                                        "in_progress": _("fabrication")}.get(st, st or "…")))
        if st == "completed":
            break
        if st in ("failed", "nsfw", "canceled"):
            raise ErreurGenerateur(_("Higgsfield : plan refusé ou en échec ({s}) ; rien n'est facturé pour un échec.", s=st))
        if time.time() - debut > attente:
            raise ErreurGenerateur(_("Higgsfield n'a pas fini à temps."))
    url = (e.get("video") or {}).get("url") or next((v.get("url") for v in (e.get("videos") or []) if isinstance(v, dict)), None)
    if not url:
        raise ErreurGenerateur(_("Higgsfield n'a pas rendu de vidéo : {r}", r=str(e)[:200]))
    return telecharger(url, sortie)


def _data_uri(chemin):
    from .ia import type_image
    with open(chemin, "rb") as f:
        o = f.read()
    return f"data:{type_image(o)};base64," + base64.b64encode(o).decode()


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
    if typ.startswith("image/"):
        from .ia import type_image
        typ = type_image(donnees)
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
        if fournisseur == "heygen":
            from .motion_html import tester_heygen
            return tester_heygen(cle)
        if fournisseur == "higgsfield":
            req = urllib.request.Request(f"{HIGGSFIELD}/requests/00000000-0000-0000-0000-000000000000/status",
                                         headers={"Authorization": f"Key {cle}", "User-Agent": "PhilCut"})
            try:
                urllib.request.urlopen(req, timeout=20)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    return False, _("Clef Higgsfield refusée (forme « identifiant:secret »).")
            return True, _("Clef Higgsfield acceptée (le solde se voit dans la console Higgsfield).")
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


# 0.9.96 : chaque vidéo payante réussie est notée (« dépensé ce mois par PhilCut »), les soldes n'étant pas toujours donnés
_generer_sans_compte = generer


def generer(params, ident, consigne, sortie, duree=5, format_="16:9", image=None, progression=None, arret=lambda: False,
            son=False, references=None, image_fin=None, multi=None):
    r = _generer_sans_compte(params, ident, consigne, sortie, duree, format_, image, progression, arret, son=son,
                             references=references, image_fin=image_fin, multi=multi)
    try:
        m = modele(ident, params)
        if m and m.get("fournisseur") in POUR_VIDEO:
            from .credit_ia import noter_depense
            noter_depense(m["fournisseur"], prix(m, duree, son) + (0.0 if not image_fin else 0.0))
    except Exception:      # noqa: BLE001 : le compte est un plus
        pass
    return r
