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
    "surprise": "surprise", "überraschung": "surprise", "sorpresa": "surprise", "peur": "scared", "angst": "fear", "miedo": "fear", "paura": "fear",
    "bonjour": "hello", "hallo": "hello", "hola": "hello", "ciao": "hello", "au revoir": "goodbye", "merci": "thank you", "danke": "thank you",
    "gracias": "thank you", "grazie": "thank you", "oui": "yes", "non": "no", "nein": "no", "sí": "yes",
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
    if reseau and not os.environ.get("PHILCUT_SANS_RESEAU"):
        try:
            url = API + "?" + urllib.parse.urlencode({"q": texte[:400], "langpair": f"{langue}|en"})
            with urllib.request.urlopen(urllib.request.Request(url, headers=_agent()), timeout=6) as r:
                d = json.loads(r.read().decode("utf-8"))
            t = ((d.get("responseData") or {}).get("translatedText") or "").strip()
            if t and int(d.get("responseStatus") or 200) == 200 and "MYMEMORY WARNING" not in t.upper():
                res = (t, "service", [])
        except Exception:    # noqa: BLE001 : sans réseau, le dictionnaire prend le relais
            res = None
    if res is None:
        t, manque = _dico(texte)
        res = (t, "dictionnaire" if len(manque) < len(t.split()) else "", manque)
    _CACHE[cle] = res
    return res


def message(origine, resultat):
    """Phrase pour la barre du bas : ce qui a vraiment été cherché, ou la demande de taper en anglais."""
    from .langue import _
    t, comment, manque = resultat
    if comment == "deja" or t.lower() == origine.strip().lower():
        return ""
    if manque:
        return _("Recherché en anglais : « {t} » ; pas de traduction pour « {m} » : tapez ces mots en anglais.", t=t, m=", ".join(manque))
    return _("Recherché en anglais : « {t} ».", t=t)
