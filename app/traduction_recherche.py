"""Traduction automatique des mots de recherche vers l'anglais (banques de vidéos et de musiques libres, extraits de
films) : on tape dans sa langue, PhilCut cherche en anglais. Service gratuit sans clef (MyMemory) ; sans réseau, un
petit dictionnaire des mots les plus cherchés ; ce qui reste intraduisible est signalé (« tapez en anglais »).

Seuls les mots de la recherche sont envoyés, au moment du clic sur « Chercher » (comme la recherche elle-même)."""
import json, re, urllib.parse, urllib.request

API = "https://api.mymemory.translated.net/get"
_CACHE = {}

# mots fréquents des recherches de tampons et de musiques : fr, de, es, it → en
DICO = {
    "applaudissements": "applause", "applaudissement": "applause", "applaus": "applause", "aplausos": "applause", "applausi": "applause",
    "explosion": "explosion", "explosión": "explosion", "esplosione": "explosion",
    "foule": "crowd", "menge": "crowd", "multitud": "crowd", "folla": "crowd",
    "compte à rebours": "countdown", "countdown": "countdown", "cuenta atrás": "countdown", "conto alla rovescia": "countdown",
    "rire": "laugh", "rires": "laughter", "lachen": "laugh", "risa": "laugh", "risata": "laugh",
    "pluie": "rain", "regen": "rain", "lluvia": "rain", "pioggia": "rain",
    "neige": "snow", "schnee": "snow", "nieve": "snow", "neve": "snow",
    "mer": "sea", "meer": "sea", "mar": "sea", "mare": "sea", "plage": "beach", "strand": "beach", "playa": "beach", "spiaggia": "beach",
    "montagne": "mountain", "berg": "mountain", "montaña": "mountain", "montagna": "mountain",
    "ciel": "sky", "himmel": "sky", "cielo": "sky", "nuages": "clouds", "nuage": "cloud", "wolken": "clouds", "nubes": "clouds", "nuvole": "clouds",
    "coucher de soleil": "sunset", "sonnenuntergang": "sunset", "atardecer": "sunset", "tramonto": "sunset",
    "lever de soleil": "sunrise", "soleil": "sun", "sonne": "sun", "sol": "sun", "sole": "sun",
    "avion": "airplane", "flugzeug": "airplane", "avión": "airplane", "aereo": "airplane", "voiture": "car", "auto": "car", "coche": "car", "macchina": "car",
    "ville": "city", "stadt": "city", "ciudad": "city", "città": "city", "nuit": "night", "nacht": "night", "noche": "night", "notte": "night",
    "feu": "fire", "feuer": "fire", "fuego": "fire", "fuoco": "fire", "feu d'artifice": "fireworks", "feuerwerk": "fireworks", "fuegos artificiales": "fireworks",
    "fête": "party", "party": "party", "fiesta": "party", "festa": "party", "danse": "dance", "tanz": "dance", "baile": "dance", "ballo": "dance",
    "chien": "dog", "hund": "dog", "perro": "dog", "cane": "dog", "chat": "cat", "katze": "cat", "gato": "cat", "gatto": "cat",
    "oiseau": "bird", "vogel": "bird", "pájaro": "bird", "uccello": "bird",
    "calme": "calm", "ruhig": "calm", "tranquilo": "calm", "calmo": "calm", "joyeux": "happy", "joyeuse": "happy", "fröhlich": "happy", "alegre": "happy", "allegro": "happy",
    "triste": "sad", "traurig": "sad", "épique": "epic", "episch": "epic", "épico": "epic", "epico": "epic",
    "piano": "piano", "klavier": "piano", "guitare": "guitar", "gitarre": "guitar", "guitarra": "guitar", "chitarra": "guitar",
    "rembobinage": "rewind", "rembobiner": "rewind", "retour": "rewind", "zurückspulen": "rewind", "rebobinar": "rewind", "riavvolgere": "rewind",
    "ralenti": "slow motion", "zeitlupe": "slow motion", "cámara lenta": "slow motion", "rallentatore": "slow motion",
    "bravo": "bravo", "échec": "fail", "raté": "fail", "drôle": "funny", "lustig": "funny", "gracioso": "funny", "divertente": "funny",
    "incroyable": "amazing", "unglaublich": "amazing", "increíble": "amazing", "incredibile": "amazing",
    "génial": "awesome", "super": "awesome", "toll": "awesome", "genial": "awesome", "fantastico": "awesome",
    "non merci": "no thanks", "c'est parti": "let's go", "allons-y": "let's go", "attention": "watch out", "au secours": "help",
    "je t'aime": "i love you", "pourquoi": "why", "quoi": "what", "pas possible": "no way", "impossible": "impossible",
    "surprise": "surprise", "überraschung": "surprise", "sorpresa": "surprise", "peur": "scared", "angst": "fear", "miedo": "fear", "paura": "fear",
    "bonjour": "hello", "hallo": "hello", "hola": "hello", "ciao": "hello", "au revoir": "goodbye", "merci": "thank you", "danke": "thank you",
    "gracias": "thank you", "grazie": "thank you", "oui": "yes", "non": "no", "nein": "no", "sí": "yes",
    # petits mots et mots courants des phrases pour l'IA (images, musique), pour traduire un peu même sans réseau
    "le": "the", "la": "the", "les": "the", "un": "a", "une": "a", "de": "of", "du": "of the", "des": "of", "et": "and",
    "avec": "with", "dans": "in", "sur": "on", "pour": "for", "au": "at the", "aux": "at the", "en": "in", "très": "very",
    "der": "the", "das": "the", "ein": "a", "eine": "a", "und": "and", "mit": "with", "im": "in the", "auf": "on", "für": "for",
    "el": "the", "los": "the", "las": "the", "una": "a", "y": "and", "con": "with", "del": "of the", "para": "for", "muy": "very",
    "il": "the", "gli": "the", "e": "and", "nel": "in the", "di": "of", "per": "for", "molto": "very",
    "homme": "man", "mann": "man", "hombre": "man", "uomo": "man", "femme": "woman", "frau": "woman", "mujer": "woman", "donna": "woman",
    "enfant": "child", "kind": "child", "niño": "child", "bambino": "child", "fond": "background", "hintergrund": "background",
    "forêt": "forest", "wald": "forest", "bosque": "forest", "foresta": "forest", "fleurs": "flowers", "blumen": "flowers",
    "rouge": "red", "rot": "red", "rojo": "red", "rosso": "red", "bleu": "blue", "blau": "blue", "azul": "blue", "blu": "blue",
    "vert": "green", "grün": "green", "verde": "green", "jaune": "yellow", "gelb": "yellow", "amarillo": "yellow", "giallo": "yellow",
    "noir": "black", "schwarz": "black", "negro": "black", "nero": "black", "blanc": "white", "weiß": "white", "blanco": "white", "bianco": "white",
    "rapide": "fast", "schnell": "fast", "rápido": "fast", "veloce": "fast", "lent": "slow", "lente": "slow", "langsam": "slow", "lento": "slow",
    "douce": "soft", "doux": "soft", "sanft": "soft", "suave": "soft", "dolce": "soft", "musique": "music", "musik": "music", "música": "music", "musica": "music",
    "batterie": "drums", "violon": "violin", "geige": "violin", "violín": "violin", "violino": "violin", "voix": "voice", "stimme": "voice", "voz": "voice", "voce": "voice",
}


_ANGLAIS = {m for v in DICO.values() for m in v.split()} | {"the", "a", "of", "and", "in", "on", "with"}


def _agent():
    from .config import VERSION
    return {"User-Agent": f"PhilCut/{VERSION} (+https://github.com/PhilouElChapo/PhilCut)"}


def _dico(texte):
    """Traduction mot à mot (expressions de deux ou trois mots d'abord) ; renvoie (texte, mots non traduits)."""
    mots = re.findall(r"[\w'’-]+", texte.lower())
    out, manque, i = [], [], 0
    while i < len(mots):
        for n in (3, 2, 1):
            bloc = " ".join(mots[i:i + n])
            if len(mots[i:i + n]) == n and bloc in DICO:
                out.append(DICO[bloc])
                i += n
                break
        else:
            out.append(mots[i])
            if mots[i] not in _ANGLAIS:                   # déjà un mot anglais connu : rien à signaler
                manque.append(mots[i])
            i += 1
    return " ".join(out), manque


def en_anglais(texte, langue=None, reseau=True):
    """(texte en anglais, comment, mots restés intraduisibles). comment : "deja" (PhilCut en anglais), "service",
    "dictionnaire" ou "" (rien de traduit)."""
    from . import langue as L
    texte = (texte or "").strip()
    langue = langue or L.LANGUE or "fr"
    if not texte or langue == "en":
        return texte, "deja", []
    cle = (langue, texte.lower())
    if cle in _CACHE:
        return _CACHE[cle]
    res = None
    import os
    t_dico, manque_dico = _dico(texte)
    if not manque_dico:                          # tous les mots sont connus du dictionnaire : sûr et instantané
        res = (t_dico, "dictionnaire", [])
    elif reseau and not os.environ.get("PHILCUT_SANS_RESEAU"):
        try:
            url = API + "?" + urllib.parse.urlencode({"q": texte[:400], "langpair": f"{langue[:2]}|en", "mt": "1"})
            with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=6) as r:
                d = json.loads(r.read().decode("utf-8"))
            res = _meilleure(d, texte)
        except Exception:    # noqa: BLE001 : sans réseau, le dictionnaire prend le relais
            res = None
    if res is None:
        t, manque = _dico(texte)
        res = (t, "dictionnaire" if len(manque) < len(t.split()) else "", manque)
    _CACHE[cle] = res
    return res


def _meilleure(d, texte):
    """Traduction fiable de la réponse MyMemory : la traduction automatique (« MT ») ou une correspondance très proche ;
    les souvenirs approximatifs d'autres utilisateurs (ex. « incroyable » → « Business ») sont écartés."""
    if int(d.get("responseStatus") or 200) != 200:
        return None
    candidats = []
    rd = d.get("responseData") or {}
    if rd.get("translatedText"):
        candidats.append((float(rd.get("match") or 0), rd["translatedText"], False))
    for m in d.get("matches") or []:
        if m.get("translation"):
            mt = "MT" in str(m.get("created-by") or "").upper() or str(m.get("created-by") or "") == "MT!"
            proche = (m.get("segment") or "").strip().lower() == texte.strip().lower()
            candidats.append((1.0 if mt else (float(m.get("match") or 0) if proche else 0.0), m["translation"], mt))
    candidats = [c for c in candidats if c[0] >= 0.85 and "MYMEMORY WARNING" not in c[1].upper()]
    if not candidats:
        return None
    candidats.sort(key=lambda c: (c[2], c[0]), reverse=True)
    return (candidats[0][1].strip(), "service", [])


# petits mots qui trahissent la langue d'une phrase (prompts de l'Atelier IA)
_MOTS_LANGUE = {
    "en": {"the", "a", "an", "of", "with", "and", "in", "on", "at", "for", "to", "style", "by", "from", "very", "is", "into", "soft",
           "background", "light", "lighting", "detailed", "portrait", "photo", "illustration", "music", "beat", "cinematic"},
    "fr": {"le", "la", "les", "un", "une", "des", "du", "de", "et", "avec", "dans", "sur", "pour", "en", "au", "aux", "très", "qui",
           "est", "sous", "fond", "musique", "joyeuse", "douce", "façon", "comme"},
    "de": {"der", "die", "das", "ein", "eine", "und", "mit", "im", "auf", "für", "von", "sehr", "ist", "zu", "dem", "den", "musik"},
    "es": {"el", "los", "las", "una", "y", "con", "en", "del", "para", "muy", "es", "por", "estilo", "música", "fondo"},
    "it": {"il", "lo", "gli", "una", "e", "con", "nel", "della", "di", "per", "molto", "è", "stile", "musica", "sfondo"},
}
_ACCENTS = {"fr": "éèêàâçùûôîœ", "de": "äöüß", "es": "ñáíóú¿¡", "it": "àèìòù"}


def langue_probable(texte, defaut=None):
    """Langue la plus probable d'une phrase (en, fr, de, es, it), d'après ses petits mots et ses accents ; defaut si
    rien ne la trahit."""
    mots = re.findall(r"[\w'’]+", (texte or "").lower())
    scores = {k: sum(1 for m in mots if m in v) for k, v in _MOTS_LANGUE.items()}
    for k, lettres in _ACCENTS.items():
        scores[k] += sum(2 for c in (texte or "").lower() if c in lettres)
    meilleur = max(scores, key=lambda k: (scores[k], k == "en"))
    return meilleur if scores[meilleur] > 0 else defaut


def phrase_en_anglais(texte, langue=None, reseau=True):
    """Phrase pour un moteur d'IA (images, musique), qui ne comprend bien que l'anglais. Une phrase déjà en anglais
    est gardée telle quelle (rien n'est envoyé) ; sinon elle est traduite morceau par morceau (le service limite la
    longueur). Renvoie (texte en anglais, comment, mots restés intraduisibles) comme en_anglais."""
    from . import langue as L
    texte = (texte or "").strip()
    if not texte:
        return texte, "deja", []
    source = langue_probable(texte, None)
    if source is None:                         # rien ne trahit la langue : le dictionnaire tranche, sinon la langue de PhilCut
        t, manque = _dico(texte)
        mots = re.findall(r"[\w'’-]+", texte.lower())
        if not manque:
            return (texte, "deja", []) if t.split() == mots else (t, "dictionnaire", [])
        if t.split() == mots:                  # aucun mot reconnu d'une autre langue : sans doute de l'anglais (lofi, chill…)
            return texte, "deja", []
        source = L.LANGUE or "fr"
    if source == "en":
        return texte, "deja", []
    morceaux, cour = [], ""
    for bout in re.split(r"(?<=[.;,!?\n])\s*", texte):
        if cour and len(cour) + len(bout) + 1 > 380:
            morceaux.append(cour)
            cour = ""
        cour = (cour + " " + bout).strip()
    if cour:
        morceaux.append(cour)
    sortie, comments, manque = [], set(), []
    for m in morceaux:
        t, comment, mq = en_anglais(m[:400], source, reseau)
        sortie.append(t)
        comments.add(comment)
        manque += mq
    comment = "" if "" in comments else ("service" if "service" in comments else "dictionnaire")
    return " ".join(sortie).strip(), comment, manque


def message(origine, resultat):
    """Phrase pour la barre du bas : ce qui a vraiment été cherché, ou la demande de taper en anglais."""
    from .langue import _
    t, comment, manque = resultat
    if comment == "deja" or t.lower() == origine.strip().lower():
        return ""
    if manque:
        return _("Recherché en anglais : « {t} » ; pas de traduction pour « {m} » : tapez ces mots en anglais.", t=t, m=", ".join(manque))
    return _("Recherché en anglais : « {t} ».", t=t)
