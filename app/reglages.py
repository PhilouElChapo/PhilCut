"""Sauvegarde, export et import des preferences.

Deux familles de reglages :
  - COMMUNS a tous vos postes : votre nom, la langue, les comptes (NAS, FTP, WebDAV, Drives), l'ordre des
    outils et des favoris, l'etat des volets et des barres, le zoom, les filigranes personnels, l'IA,
    les mises a jour, les effets et Goodies coches, la destination d'export, le niveau de l'assistant ;
  - PROPRES A UN POSTE : son nom (alias), ses dossiers et chemins (NAS, emplacements, dernier dossier),
    le choix du Drive sur ce PC, l'association des projets .philcut, les proxys, le test de l'IA locale.

Automatiquement : a chaque validation des Preferences et a la fermeture, <Drive>/PhilCut/preferences.json
recoit les reglages communs et ceux de ce poste (sans aucun mot de passe). Une nouvelle installation qui
trouve ce fichier propose de les reprendre.

A la main (Preferences > General) : export dans un fichier, avec ou sans les mots de passe et clefs ;
s'ils sont inclus, le fichier est chiffre en AES-256 par une phrase secrete.
"""
import datetime, json, os
from . import coffre
from .langue import _

COMMUNS = ["auteur", "langue", "outils_epingles", "barre_rapide", "volet", "ia_moteur", "maj_source", "maj_auto",
           "synchro", "comptes", "comptes_icone", "theme", "synchro_secrets", "barre", "barre_style", "ordre_outils",
           "export_destination", "assistant_niveau", "ia_consignes_recette", "effets_coches", "goodies_coches", "effets_favoris", "effets_recents", "effets_familles_ouvertes",
           "musiques_dossier", "chaine_nom", "fabrique_style", "veo_actif", "ia_confirmer_cout", "modeles_video_perso",
           "tampons_guetter", "tampons_classement", "tampons_placement", "ytdlp_accord", "ytdlp_hauteur", "ytdlp_son_seul", "ytdlp_resultats", "tampons_langue_recherche",
           "musiques_classement", "styles_perso", "creations_purge_jours", "secours_minutes", "secours_versions", "export_autres", "nouveautes_vues", "lecture_effets",
           "proposer_copie_legere", "creations_drive", "drive_purge_jours", "superpositions_alpha"]
POSTE = ["secrets_refuses", "disposition_vue", "volet_largeur", "biblio_replies", "sessions_vues", "synchro_etat",
         "machine", "zoom", "racines", "nas", "dernier_dossier", "drive", "drive_compte", "association_video",
         "recherche_racines", "proxys", "ia_locale", "ia_poste_leger", "ia_gpu", "ia_locale_modeles", "ia_dossier_commun", "ia_partage", "ia_commun_propose", "dossier_flow", "dossier_proxys", "encodeur", "apercu_images", "ajout_auto", "dernier_dossier_export", "barre_taille", "dossier_images", "tailles_vue", "apercu_fidele", "preparation_auto", "secrets_empreinte", "dossier_rushes", "fenetre_geometrie", "fenetre_maximisee", "dossier_musique_import", "dossier_telechargements", "dossier_documents",
         "vulkan_carte", "moteurs_evites", "essais_ia"]
CLEFS_IA = ["clef_claude", "clef_gemini", "clef_fal"]
COFFRE_PARTAGES = {"pixabay_cle": "Pixabay", "pexels_cle": "Pexels"}      # clefs rangées directement dans le coffre
FICHIER_DRIVE = "preferences.json"


def maintenant():
    return datetime.datetime.now().isoformat(timespec="minutes")


def instantane(params, avec_secrets=False):
    d = {"philcut": 1, "date": maintenant(), "machine": params.get("machine", ""),
         "communs": {k: params[k] for k in COMMUNS if k in params},
         "poste": {k: params[k] for k in POSTE if k in params}}
    if avec_secrets:
        s = {k: params.get(k, "") for k in CLEFS_IA}
        for c in params.get("comptes", []):
            for suffixe in ("", ".jeton", ".appareil"):
                v = coffre.lire(c["id"] + suffixe)
                if v:
                    s["coffre:" + c["id"] + suffixe] = v
        for ident in COFFRE_PARTAGES:                      # clefs des banques de vidéos libres (tampons)
            v = coffre.lire(ident)
            if v:
                s["coffre:" + ident] = v
        for c in params.get("comptes_mail", []):           # mots de passe des adresses d'envoi d'e-mails
            v = coffre.lire("mail_" + c["id"])
            if v:
                s["coffre:mail_" + c["id"]] = v
        try:
            from . import identites
            s.update(identites.secrets(params))
        except Exception:                                 # noqa: BLE001
            pass
        d["secrets"] = s
    return d


def appliquer(params, d, communs=True, poste=False, secrets=True):
    if communs:
        for k, v in d.get("communs", {}).items():
            if k in COMMUNS:
                params[k] = v
    if poste:
        for k, v in d.get("poste", {}).items():
            if k in POSTE:
                params[k] = v
    if secrets:
        for k, v in (d.get("secrets") or {}).items():
            if k.startswith("coffre:"):
                coffre.enregistrer(k[7:], v)
            elif k.startswith("identite:") and v:
                from . import identites
                identites.reprendre_secret(params, k, v, ecraser=True)
            elif k in CLEFS_IA and v:
                params[k] = v
    params.enregistrer()


# ------------------------------------------------------------------ fichier (export / import)
MAGIE = b"PHILCUT-PREFS-AES\n"


def _clef(phrase, sel):
    import base64, hashlib
    return base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", phrase.encode("utf-8"), sel, 390000))


def exporter(chemin, d, phrase=None):
    """JSON lisible sans phrase ; avec une phrase : fichier chiffre (AES-128-CBC + HMAC, clef PBKDF2) contenant le JSON."""
    contenu = json.dumps(d, ensure_ascii=False, indent=1).encode("utf-8")
    if not phrase:
        with open(chemin, "wb") as f:
            f.write(contenu)
        return
    from cryptography.fernet import Fernet
    sel = os.urandom(16)
    with open(chemin, "wb") as f:
        f.write(MAGIE + sel + Fernet(_clef(phrase, sel)).encrypt(contenu))


class PhraseRequise(Exception):
    pass


def importer(chemin, phrase=None):
    with open(chemin, "rb") as f:
        brut = f.read()
    if not brut.startswith(MAGIE):
        d = json.loads(brut.decode("utf-8"))
    else:
        from cryptography.fernet import Fernet, InvalidToken
        if not phrase:
            raise PhraseRequise()
        sel = brut[len(MAGIE):len(MAGIE) + 16]
        try:
            d = json.loads(Fernet(_clef(phrase, sel)).decrypt(brut[len(MAGIE) + 16:]).decode("utf-8"))
        except InvalidToken:
            raise PhraseRequise()
    if d.get("philcut") != 1:
        raise ValueError("format")
    return d


# ------------------------------------------------------------------ Drive (automatique, sans secrets)
def chemin_drive(params):
    from .bibliotheque import dossier_philcut_drive
    d = dossier_philcut_drive(params)
    return os.path.join(d, FICHIER_DRIVE) if d else None


def lire_drive(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, TypeError):
        return {}


def ecrire_drive(params):
    p = chemin_drive(params)
    if not p:
        return False
    d = lire_drive(p)
    i = instantane(params)
    d["philcut"] = 1
    local = params.get("communs_maj") or ""
    dc = d.get("communs") or {}
    sur_drive = dc.get("maj") or ""
    # ceux d'un autre poste que vous n'avez pas encore vus (fenetre de choix) ne sont jamais remplaces en silence
    pas_vus = bool(dc) and dc.get("par") not in ("", None, i["machine"]) and sur_drive != (params.get("communs_drive_vu") or "")
    # sinon, les reglages communs de ce poste remplacent ceux du Drive s'ils ont ete changes plus recemment
    if local and local > sur_drive and not pas_vus:
        d["communs"] = dict(i["communs"], maj=local, par=i["machine"])
    d.setdefault("postes", {})[i["machine"]] = dict(i["poste"], maj=i["date"])
    try:
        return ecrire_si_change(p, d)
    except OSError:
        return False


def trouver_sur_drives():
    """Preferences laissees sur un Drive de ce PC (dossier de l'application de bureau) : [(nom, chemin, contenu)]."""
    from .bibliotheque import detecter_clouds
    out = []
    for nom, racine in detecter_clouds():
        p = os.path.join(racine, "PhilCut", FICHIER_DRIVE)
        d = lire_drive(p)
        if d.get("communs"):
            out.append((nom, racine, d))
    return out


# ------------------------------------------------------------------ mots de passe sur le Drive (chiffres)
FICHIER_SECRETS = "secrets.philcut"
PHRASE = "phrase_synchro"            # cle du coffre local qui garde la phrase de ce poste


def chemin_secrets(params):
    from .bibliotheque import dossier_philcut_drive
    d = dossier_philcut_drive(params)
    return os.path.join(d, FICHIER_SECRETS) if d else None


FICHIER_INDICE = "indice_phrase.json"


def ecrire_indice(params, indice):
    """Indice (en clair, facultatif) de la phrase secrete, a cote du fichier chiffre : vu sur les autres postes."""
    p = chemin_secrets(params)
    if not p:
        return
    f = os.path.join(os.path.dirname(p), FICHIER_INDICE)
    try:
        if indice:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump({"indice": indice, "maj": maintenant(), "par": params.get("machine", "")}, fh, ensure_ascii=False)
        elif os.path.exists(f):
            os.remove(f)
    except OSError:
        pass


def lire_indice(params):
    p = chemin_secrets(params)
    try:
        with open(os.path.join(os.path.dirname(p), FICHIER_INDICE), encoding="utf-8") as fh:
            return json.load(fh).get("indice", "")
    except (OSError, ValueError, TypeError):
        return ""


def _secrets_partageables(params):
    s = instantane(params, avec_secrets=True).get("secrets", {})
    # Box change de jeton durable a chaque usage : partage entre postes impossible, chacun autorise le sien
    box = {c["id"] for c in params.get("comptes", []) if c.get("type") == "box"}
    return {k: v for k, v in s.items() if v and not any(k == f"coffre:{b}.jeton" for b in box)}


def lire_secrets_drive(params, phrase):
    """Secrets du Drive ({cle: valeur}) ; leve PhraseRequise si la phrase est fausse, {} s'il n'y a rien."""
    p = chemin_secrets(params)
    if not p or not os.path.exists(p):
        return {}
    return importer(p, phrase).get("secrets", {})


def ecrire_secrets_drive(params, phrase=None):
    """Met les mots de passe, autorisations et clefs de ce poste sur le Drive, chiffres (AES-256) par la phrase.
    Ceux des autres postes deja presents sont gardes. Renvoie False si rien n'a ete ecrit."""
    phrase = phrase or coffre.lire(PHRASE)
    p = chemin_secrets(params)
    if not phrase or not p or not params.get("synchro_secrets"):
        return False
    try:
        anciens = lire_secrets_drive(params, phrase)
    except (PhraseRequise, OSError, ValueError, KeyError):
        anciens = {}
    tous = dict(anciens, **_secrets_partageables(params))
    tmp = p + ".tmp"
    exporter(tmp, {"philcut": 1, "date": maintenant(), "machine": params.get("machine", ""), "communs": {}, "poste": {},
                   "secrets": tous}, phrase)
    os.replace(tmp, p)
    return True


def synchro_secrets_auto(params):
    """Synchronisation automatique des clefs et mots de passe (case « Synchroniser aussi les mots de passe et clefs ») :
    envoie ceux de ce poste quand ils ont changé, reprend ceux des autres postes absents ici. Renvoie le nombre repris ;
    rien sans phrase secrète sur ce poste, ou si la phrase ne correspond pas."""
    import hashlib
    phrase = coffre.lire(PHRASE)
    if not params.get("synchro_secrets") or not phrase or not chemin_secrets(params):
        return 0
    try:
        n = reprendre_secrets_drive(params, phrase) if os.path.exists(chemin_secrets(params)) else 0
        empreinte = hashlib.sha256(json.dumps(_secrets_partageables(params), sort_keys=True).encode()).hexdigest()[:24]
        if empreinte != params.get("secrets_empreinte") or not os.path.exists(chemin_secrets(params)):
            if ecrire_secrets_drive(params, phrase):
                params["secrets_empreinte"] = empreinte
                params.enregistrer()
        return n
    except (PhraseRequise, OSError, ValueError, KeyError):
        return 0


def nom_secret(params, k):
    """Le nom lisible d'un secret partagé (jamais sa valeur) : « Clef Claude », « pCloud — autorisation »…"""
    noms_ia = {"clef_claude": _("Clef Claude"), "clef_gemini": _("Clef Gemini"), "clef_fal": _("Clef fal.ai")}
    if k in noms_ia:
        return noms_ia[k]
    if k.startswith("coffre:"):
        c = k[7:]
        if c in COFFRE_PARTAGES:
            return _("Clef {s}", s=COFFRE_PARTAGES[c])
        base, _p, quoi = c.partition(".")
        compte = next((x for x in params.get("comptes", []) if x.get("id") == base), None)
        if compte is not None:
            from . import distant
            return distant.libelle(compte) + " — " + (_("autorisation") if quoi == "jeton" else _("mot de passe"))
        return _("Mot de passe d'un compte")
    if k.startswith("identite:"):
        return _("Adresse d'envoi d'e-mails")
    return k


def etat_secrets(params):
    """Pour les Préférences (0.9.62) : où en est la synchronisation des mots de passe et clefs sur ce poste.
    {phrase_ici, fichier, lisible, indice, date, machine, noms}"""
    phrase = coffre.lire(PHRASE)
    p = chemin_secrets(params)
    out = {"phrase_ici": bool(phrase), "fichier": bool(p and os.path.exists(p)), "lisible": False, "indice": lire_indice(params),
           "date": "", "machine": "", "noms": []}
    if out["fichier"] and phrase:
        try:
            d = importer(p, phrase)
            out.update(lisible=True, date=d.get("date", ""), machine=d.get("machine", ""),
                       noms=sorted({nom_secret(params, k) for k, v in (d.get("secrets") or {}).items() if v}, key=str.lower))
        except (PhraseRequise, OSError, ValueError, KeyError):
            pass
    return out


def changer_phrase(params, ancienne, nouvelle, indice=None):
    """Rechiffre les secrets partagés avec une nouvelle phrase (les autres postes la redemanderont une fois)."""
    if coffre.lire(PHRASE) and ancienne != coffre.lire(PHRASE):
        raise PhraseRequise()
    anciens = lire_secrets_drive(params, ancienne) if chemin_secrets(params) and os.path.exists(chemin_secrets(params)) else {}
    coffre.enregistrer(PHRASE, nouvelle)
    p = chemin_secrets(params)
    if p:
        tous = dict(anciens, **_secrets_partageables(params))
        tmp = p + ".tmp"
        exporter(tmp, {"philcut": 1, "date": maintenant(), "machine": params.get("machine", ""), "communs": {}, "poste": {},
                       "secrets": tous}, nouvelle)
        os.replace(tmp, p)
    if indice is not None:
        ecrire_indice(params, indice)
    params["secrets_empreinte"] = ""
    return True


def reprendre_secrets_drive(params, phrase, ecraser=False):
    """Copie dans le coffre de ce poste les secrets du Drive (sans ecraser ceux deja presents, sauf demande).
    Renvoie le nombre de secrets repris."""
    n = 0
    for k, v in lire_secrets_drive(params, phrase).items():
        if k.startswith("coffre:"):
            if ecraser or not coffre.lire(k[7:]):
                coffre.enregistrer(k[7:], v)
                n += 1
        elif k in CLEFS_IA and v and (ecraser or not params.get(k)):
            params[k] = v
            n += 1
        elif k.startswith("identite:") and v:
            from . import identites
            if identites.reprendre_secret(params, k, v, ecraser=ecraser):
                n += 1
    params.enregistrer()
    return n


def copie_avant_reprise(params):
    """Filet de securite : copie des preferences de ce poste juste avant d'y reprendre celles d'un autre poste
    (comptes e-mail, carnet...). Gardee dans « donnees/copies_avant_reprise », les 10 dernieres."""
    try:
        import shutil
        from .config import dossier_donnees
        d = os.path.join(dossier_donnees(), "copies_avant_reprise")
        os.makedirs(d, exist_ok=True)
        shutil.copy2(params.chemin, os.path.join(d, "preferences-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json"))
        for vieux in sorted(os.listdir(d))[:-10]:
            os.remove(os.path.join(d, vieux))
    except Exception:                                # noqa: BLE001
        pass


def reprendre_communs_drive(params):
    """Au demarrage : si un autre poste a change des reglages communs plus recemment (favoris, outils, barres,
    comptes, langue...), on les reprend ici. Renvoie le nom de ce poste, ou None."""
    p = chemin_drive(params)
    if not p:
        return None
    c = (lire_drive(p).get("communs") or {})
    maj, par = c.get("maj") or "", c.get("par") or ""
    if not maj or maj <= (params.get("communs_maj") or "") or par == params.get("machine"):
        return None
    copie_avant_reprise(params)
    comptes_ici = {x["id"] for x in params.get("comptes", [])}
    a_renvoyer = False
    for k, v in c.items():
        if k in COMMUNS:
            params[k] = _valeur_reprise(params, c, k, v)
            if not _meme(params[k], v):               # ce poste en a plus (identites) : le Drive doit les recevoir
                a_renvoyer = True
    params["communs_maj"] = maj
    params["communs_drive_vu"] = maj
    params._communs_vus = params._empreinte_communs() if hasattr(params, "_empreinte_communs") else ""
    if a_renvoyer:                                    # date plus recente : la liste reunie part sur le Drive
        params["communs_maj"] = datetime.datetime.now().isoformat(timespec="seconds")
    params.enregistrer()
    if a_renvoyer:
        ecrire_drive(params)
    nouveaux = [x for x in params.get("comptes", []) if x["id"] not in comptes_ici]
    return par, nouveaux


# ------------------------------------------------------------------ mise a jour choisie (jamais en silence)
def _(t, **k):
    from .langue import _ as tr
    return tr(t, **k)


def libelle_commun(k):
    return {"auteur": _("Votre nom (écran de fin, crédits)"), "langue": _("Langue de PhilCut"),
            "outils_epingles": _("Outils favoris"), "barre_rapide": _("Barre rapide"),
            "volet": _("Volet de droite"), "ia_moteur": _("IA utilisée"),
            "maj_source": _("Source des mises à jour"), "maj_auto": _("Mises à jour automatiques"),
            "synchro": _("Synchronisation des projets"), "comptes": _("Comptes (NAS, FTP, Drives)"),
            "comptes_icone": _("Style des icônes des comptes"), "theme": _("Thème"),
            "synchro_secrets": _("Synchroniser les mots de passe"), "barre": _("Barre d'outils"),
            "barre_style": _("Boutons de la barre (icône, nom)"), "ordre_outils": _("Ordre des outils"),
            "export_destination": _("Destination d'export par défaut"), "assistant_niveau": _("Niveau de l'assistant de montage"),
            "ia_consignes_recette": _("Consignes personnelles pour l'assistant"), "effets_coches": _("Effets téléchargés"),
            "goodies_coches": _("Goodies téléchargés"), "musiques_dossier": _("Dossier de musiques personnel"),
            "chaine_nom": _("Nom de la chaîne / signature des vidéos"), "fabrique_style": _("Style de la Fabrique"),
            "veo_actif": _("Génération Veo par l'API (payante)"),
            "proposer_copie_legere": _("Proposer la copie légère sur le Drive"), "creations_drive": _("Créations IA déposées sur le Drive"),
            "drive_purge_jours": _("Nettoyage de l'espace PhilCut sur le Drive"), "superpositions_alpha": _("Superpositions avec transparence")}.get(k, k)


# valeur utilisee quand le reglage n'a jamais ete touche sur un poste (absent = cette valeur)
DEFAUTS_COMMUNS = {"comptes_icone": "photo", "barre_style": "auto", "ia_consignes_recette": "",
                   "export_destination": "youtube", "assistant_niveau": "recettes", "effets_coches": [], "goodies_coches": [],
                   "musiques_dossier": "", "chaine_nom": "", "fabrique_style": "", "veo_actif": False,
                   "proposer_copie_legere": True, "creations_drive": "demander", "drive_purge_jours": 90, "superpositions_alpha": True}


def _effectif(params, k):
    v = params.get(k)
    if v in (None, "") and k in DEFAUTS_COMMUNS:
        return DEFAUTS_COMMUNS[k]
    return v


def _meme(a, b):
    vide = (None, "", [], {})
    return a == b or (a in vide and b in vide)


def _court(v):
    if isinstance(v, bool):
        return _("oui") if v else _("non")
    if v in (None, "", [], {}):
        return _("(vide)")
    t = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return t if len(t) <= 40 else t[:37] + "..."


def _nom_element(x):
    if isinstance(x, dict):
        return str(x.get("nom") or x.get("id") or x.get("texte") or "?")
    return str(x)


def decrire_changement(k, avant, apres):
    """Phrase lisible : ce qui va changer sur ce poste si on reprend ce reglage."""
    if k == "comptes":
        a = {c.get("id"): c for c in avant or []}
        b = {c.get("id"): c for c in apres or []}
        morceaux = []
        aj = [_nom_element(b[i]) for i in b if i not in a]
        rt = [_nom_element(a[i]) for i in a if i not in b]
        md = [_nom_element(b[i]) for i in b if i in a and a[i] != b[i]]
        if aj:
            morceaux.append(_("ajoute : {x}", x=", ".join(aj)))
        if rt:
            morceaux.append(_("retire : {x}", x=", ".join(rt)))
        if md:
            morceaux.append(_("modifie : {x}", x=", ".join(md)))
        return " ; ".join(morceaux) or _("ordre modifié")
    if isinstance(avant, list) and isinstance(apres, list):
        ka = [_nom_element(x) for x in avant]
        kb = [_nom_element(x) for x in apres]
        aj = [x for x in kb if x not in ka]
        rt = [x for x in ka if x not in kb]
        morceaux = []
        if aj:
            morceaux.append(_("ajoute : {x}", x=", ".join(aj[:8]) + ("..." if len(aj) > 8 else "")))
        if rt:
            morceaux.append(_("retire : {x}", x=", ".join(rt[:8]) + ("..." if len(rt) > 8 else "")))
        return " ; ".join(morceaux) or _("ordre modifié")
    if isinstance(avant, dict) and isinstance(apres, dict):
        cles = [c for c in set(avant) | set(apres) if avant.get(c) != apres.get(c)]
        return _("modifie : {x}", x=", ".join(sorted(map(str, cles))[:8]))
    return f"{_court(avant)}  →  {_court(apres)}"


def _valeur_reprise(params, communs, k, v):
    """Valeur d'un reglage commun repris d'un autre poste : les identites et certificats sont reunis (ceux d'ici
    restent), jamais remplaces par une liste plus courte."""
    from .miroir import UNIONS, unir
    if k in UNIONS and isinstance(v, list):
        ret = set(params.get(UNIONS[k][1]) or []) | set(communs.get(UNIONS[k][1]) or [])
        return unir(k, params.get(k) or [], v, ret)
    from .miroir import RETRAITS
    if k in RETRAITS and isinstance(v, list):
        return sorted(set(v) | set(params.get(k) or []))
    return v


def comptes_mail_ailleurs(params):
    """Adresses d'envoi d'e-mails enregistrees par un autre poste et absentes ici (sauf celles retirees expres),
    que la fenetre de choix ait deja ete vue ou non."""
    p = chemin_drive(params)
    if not p:
        return []
    c = lire_drive(p).get("communs") or {}
    retires = set(params.get("comptes_mail_retires") or []) | set(c.get("comptes_mail_retires") or [])
    ici = {x.get("id") for x in params.get("comptes_mail") or [] if isinstance(x, dict)}
    return [x for x in c.get("comptes_mail") or [] if isinstance(x, dict) and x.get("id") and x.get("adresse")
            and x["id"] not in ici and x["id"] not in retires]


UNIONS_CLES = ("identites", "certificats_approuves", "comptes_mail", "carnet")


def changements_communs(params):
    """None si rien de plus recent sur le Drive ; sinon {"par", "maj", "items": [{cle, libelle, detail, valeur}]}."""
    p = chemin_drive(params)
    if not p:
        return None
    c = (lire_drive(p).get("communs") or {})
    maj, par = c.get("maj") or "", c.get("par") or ""
    # proposes des qu'un autre poste les a ecrits et que vous ne les avez pas encore vus, quelle que soit la date :
    # la case est cochee d'avance seulement si l'autre poste est le plus recent
    if not maj or par == params.get("machine") or maj == (params.get("communs_drive_vu") or ""):
        return None
    local = params.get("communs_maj") or ""
    plus_recent_ailleurs = maj > local
    items = []
    for k in COMMUNS:
        # « (vide) -> google » n'est pas un changement : jamais regle ici = valeur par defaut, la meme
        if k not in c:
            continue
        val = _valeur_reprise(params, c, k, c[k])
        if not _meme(val, _effectif(params, k)) and not _meme(_effectif({k: val}, k), _effectif(params, k)):
            from .miroir import UNIONS
            items.append({"cle": k, "libelle": libelle_commun(k), "detail": decrire_changement(k, _effectif(params, k), val),
                          "valeur": val, "coche": plus_recent_ailleurs or k in UNIONS,
                          "renvoyer": k in UNIONS and not _meme(val, c[k])})
        elif k in UNIONS_CLES and not _meme(val, c[k]):
            items.append({"cle": k, "libelle": libelle_commun(k), "detail": "", "valeur": val, "coche": True,
                          "cache": True, "renvoyer": True})    # rien de nouveau ici, mais le Drive doit recevoir les notres
    return {"par": par, "maj": maj, "local": local, "items": items, "plus_recent_ailleurs": plus_recent_ailleurs}


DISPOSITION = ("volet_largeur", "vignettes_largeur", "biblio_replies")


def disposition_autre(params):
    """Disposition (largeur des volets, categories ouvertes) changee sur un autre poste : proposee ici, une fois.
    Chaque poste garde la sienne ; refusee, la question ne revient que si l'autre poste la change encore.
    Renvoie {"poste", "sig", "items": [{cle, libelle, detail, valeur}]} ou None."""
    p = chemin_drive(params)
    if not p:
        return None
    postes = lire_drive(p).get("postes") or {}
    moi = params.get("machine")
    autres = sorted(((v.get("maj") or "", m, v) for m, v in postes.items() if m != moi and isinstance(v, dict)
                     and any(k in v for k in DISPOSITION)), reverse=True)
    if not autres:
        return None
    _d, m, v = autres[0]
    sig = m + "|" + json.dumps({k: v.get(k) for k in DISPOSITION}, sort_keys=True)
    if sig == params.get("disposition_vue"):
        return None
    libs = {"volet_largeur": _("Largeur du volet de droite"), "vignettes_largeur": _("Largeur des vignettes"),
            "biblio_replies": _("Groupes ouverts ou fermés dans le volet des tampons")}
    items = []
    for k in DISPOSITION:
        if k in v and v[k] != params.get(k):
            if k == "biblio_replies":
                det = _("comme sur « {poste} »", poste=m)
            else:
                det = f"{params.get(k) or '-'} px  →  {v[k]} px"
            items.append({"cle": k, "libelle": libs[k], "detail": det, "valeur": v[k]})
    if not items:
        params["disposition_vue"] = sig
        params.enregistrer()
        return None
    return {"poste": m, "sig": sig, "items": items}


def appliquer_disposition(params, dispo, cles):
    """Reprend ce qui est coche ; dans tous les cas, cette disposition n'est plus proposee."""
    for it in dispo["items"]:
        if it["cle"] in cles:
            params[it["cle"]] = it["valeur"]
    params["disposition_vue"] = dispo["sig"]
    params.enregistrer()


def appliquer_communs(params, changements, cles):
    """Reprend seulement les reglages choisis ; les autres restent ceux de ce poste. On ne redemande pas ensuite."""
    copie_avant_reprise(params)
    garde_ici = False
    for it in changements["items"]:
        if it["cle"] in cles or it.get("cache"):
            params[it["cle"]] = it["valeur"]
            if it.get("renvoyer"):
                garde_ici = True                          # la liste reunie doit repartir vers le Drive
        else:
            garde_ici = True
    params["communs_drive_vu"] = changements["maj"]
    # tout repris : ce poste est a egalite avec le Drive ; sinon ses valeurs gardees deviennent la reference (envoyees)
    params["communs_maj"] = datetime.datetime.now().isoformat(timespec="seconds") if garde_ici else changements["maj"]
    params._communs_vus = params._empreinte_communs() if hasattr(params, "_empreinte_communs") else ""
    params.enregistrer()


def secrets_nouveaux(params, phrase, secrets=None):
    """Secrets du Drive (ou ceux donnes) absents de ce poste : [{cle, libelle}] (jamais les valeurs)."""
    noms = {c["id"]: c.get("nom") or c["id"] for c in params.get("comptes", [])}
    noms.update({"mail_" + c["id"]: c.get("adresse") or c["id"] for c in params.get("comptes_mail", [])})
    out = []
    import hashlib
    refuses = params.get("secrets_refuses") or {}
    supprimees = set(params.get("identites_supprimees") or [])
    for k, v in (lire_secrets_drive(params, phrase) if secrets is None else secrets).items():
        if v and refuses.get(k) == hashlib.sha1(str(v).encode()).hexdigest()[:16]:
            continue                                 # deja refuse sur ce poste (meme valeur) : plus propose
        if k.startswith("coffre:") and k[7:] in COFFRE_PARTAGES:
            if v and not coffre.lire(k[7:]):
                out.append({"cle": k, "libelle": _("clef {x}", x=COFFRE_PARTAGES[k[7:]])})
        elif k.startswith("coffre:"):
            if v and not coffre.lire(k[7:]):
                cid, _p, suffixe = k[7:].partition(".")
                quoi = _("autorisation") if suffixe in ("jeton", "appareil") else _("mot de passe")
                out.append({"cle": k, "libelle": f"{quoi} : {noms.get(cid, cid)}"})
        elif k in CLEFS_IA and v and not params.get(k):
            out.append({"cle": k, "libelle": _("clef IA : {x}", x="Claude" if "claude" in k else "Gemini")})
        elif k.startswith("identite:") and v:
            from . import identites
            ident = k.split(":", 1)[1]
            if ident in supprimees:                  # supprimee sur un poste : jamais reproposee
                continue
            deja = any(ident in (e.get("alias") or []) and (e.get("ici") or os.path.exists(identites._fichier(e["id"])))
                       for e in identites.liste(params))
            if not deja and not os.path.exists(identites._fichier(ident)):
                out.append({"cle": k, "libelle": _("identité numérique : {x}", x=identites.nom_identite(params, k))})
    return out


def refuser_secrets(params, phrase, cles):
    """Secrets decoches dans la fenetre : retenus (avec leur valeur) pour ne plus les proposer sur ce poste,
    sauf s'ils changent un jour sur l'autre poste."""
    import hashlib
    if not cles:
        return
    tous = lire_secrets_drive(params, phrase)
    r = dict(params.get("secrets_refuses") or {})
    for k in cles:
        if tous.get(k):
            r[k] = hashlib.sha1(str(tous[k]).encode()).hexdigest()[:16]
    params["secrets_refuses"] = r
    params.enregistrer()


def reprendre_secrets_choisis(params, phrase, cles):
    n = 0
    for k, v in lire_secrets_drive(params, phrase).items():
        if k not in cles:
            continue
        if k.startswith("coffre:"):
            coffre.enregistrer(k[7:], v)
        elif k.startswith("identite:"):
            from . import identites
            identites.reprendre_secret(params, k, v, ecraser=True)
        else:
            params[k] = v
        n += 1
    params.enregistrer()
    return n


def _sans_horodatage(o):
    if isinstance(o, dict):
        return {k: _sans_horodatage(v) for k, v in o.items() if k not in ("maj", "date")}
    if isinstance(o, list):
        return [_sans_horodatage(v) for v in o]
    return o


def ecrire_si_change(chemin, d, rafraichir_minutes=30):
    """N'écrit le fichier synchronisé que si son contenu change vraiment (pas seulement l'heure) ou si l'heure du poste
    date de plus de 30 minutes : sinon la synchronisation renverrait le même fichier chaque minute (0.9.31)."""
    import datetime
    try:
        with open(chemin, encoding="utf-8") as f:
            avant = json.load(f)
    except (OSError, ValueError):
        avant = None
    if avant is not None and _sans_horodatage(avant) == _sans_horodatage(d):
        def plus_recent(o):
            if isinstance(o, dict):
                vals = [o.get("maj"), o.get("date")] + [plus_recent(v) for v in o.values()]
                return max([v for v in vals if isinstance(v, str)] or [""])
            return ""
        m = plus_recent(avant)
        limite = (datetime.datetime.now() - datetime.timedelta(minutes=rafraichir_minutes)).isoformat(timespec="minutes")
        if m and m[:16] >= limite[:16]:
            return False
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    return True
