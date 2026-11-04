"""Voix : voix off enregistrée au micro, voix de synthèse, doublage dans une autre langue (cahier des charges 10.9).

Toujours le local d'abord, l'IA en ligne seulement si l'utilisateur la choisit :
  - voix de synthèse : Piper, portable, dans le dossier de PhilCut (Préférences › IA locale) ; Gemini en option,
    avec le prix affiché avant ;
  - doublage : transcription locale (whisper.cpp), traduction par le modèle local s'il est là, sinon par Claude ou
    Gemini après confirmation, puis lecture par la voix choisie, chaque phrase calée sur son moment dans la vidéo.
Les retouches (voix harmonieuse, anti-souffle, radio…) sont des effets audio non destructifs posés sur le plan : on
peut les changer à tout moment, le fichier enregistré reste intact.
"""
import base64, json, os, re, tempfile, time, urllib.error, urllib.request, wave

from . import moteur
from .langue import _

TAUX = 24000                      # fréquence commune des morceaux de voix assemblés
VOIX_GEMINI = [("Kore", _("Femme, posée")), ("Aoede", _("Femme, légère")), ("Leda", _("Femme, jeune")),
               ("Charon", _("Homme, grave")), ("Puck", _("Homme, enjoué")), ("Orus", _("Homme, ferme"))]
LANGUES = [("fr", _("Français")), ("en", _("Anglais")), ("es", _("Espagnol")), ("de", _("Allemand")), ("it", _("Italien")),
           ("pt", _("Portugais")), ("nl", _("Néerlandais"))]
NOMS_LANGUES = {"fr": "French", "en": "English", "es": "Spanish", "de": "German", "it": "Italian", "pt": "Portuguese", "nl": "Dutch"}
# Gemini TTS (Flash) : 0,50 $ le million de jetons de texte, 10 $ le million de jetons audio (25 jetons par seconde)
PRIX_TTS = (0.5, 10.0)


class ErreurVoix(Exception):
    pass


def dossier(params=None):
    from .config import dossier_donnees
    d = (params or {}).get("voix_dossier") or os.path.join(dossier_donnees(), "voix")
    os.makedirs(d, exist_ok=True)
    return d


def nouveau_nom(params, prefixe="voix"):
    return os.path.join(dossier(params), f"{prefixe}_{time.strftime('%Y%m%d_%H%M%S')}.wav")


def duree_wav(chemin):
    with wave.open(chemin, "rb") as w:
        return w.getnframes() / float(w.getframerate() or 1)


def ecrire_wav(chemin, pcm, taux=TAUX):
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taux)
        w.writeframes(pcm)
    return chemin


# ------------------------------------------------------------------ voix de synthèse
def voix_locales():
    """Voix Piper installées sur ce poste : [(clef, nom)]."""
    from . import packs_ia
    m = packs_ia.modeles()
    return [(c, (m.get(c) or {}).get("nom") or c) for c in packs_ia.installes("voix")]


def voix_locale_langue(langue):
    from . import packs_ia
    m = packs_ia.modeles()
    for c, _n in voix_locales():
        if (m.get(c) or {}).get("langue") == langue:
            return c
    return None


def lire(texte, sortie, params, moteur_voix="local", voix=None, vitesse=1.0):
    """Lit le texte avec la voix choisie et écrit un WAV. moteur_voix : local (Piper) | gemini."""
    texte = (texte or "").strip()
    if not texte:
        raise ErreurVoix(_("Aucun texte à lire."))
    if moteur_voix == "gemini":
        return lire_gemini(texte, sortie, params, voix or VOIX_GEMINI[0][0], vitesse)
    from . import packs_ia
    try:
        return packs_ia.synthese(texte, sortie, cle=voix, params=params, vitesse=vitesse)
    except packs_ia.ErreurIA as e:
        raise ErreurVoix(str(e)) from e


def prix_gemini(texte):
    """Prix indicatif en dollars d'une lecture par Gemini (environ 14 caractères par seconde de voix)."""
    secondes = len(texte) / 14.0
    return round((len(texte) / 4 * PRIX_TTS[0] + secondes * 25 * PRIX_TTS[1]) / 1e6, 4)


def _modele_tts(clef):
    from .ia import _http
    r = _http("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", entetes={"x-goog-api-key": clef})
    noms = [m["name"].split("/")[-1] for m in (r.get("models") or []) if "tts" in m["name"]]

    def rang(n):
        v = [int(x) for x in re.findall(r"\d+", n)[:2]]
        return ("flash" in n, "preview" not in n, v)
    noms.sort(key=rang, reverse=True)
    if not noms:
        raise ErreurVoix(_("Aucun modèle de voix Gemini ouvert à cette clef."))
    return noms[0]


def lire_gemini(texte, sortie, params, voix="Kore", vitesse=1.0):
    clef = (params or {}).get("clef_gemini") or ""
    if not clef:
        raise ErreurVoix(_("Pas de clef Gemini : Outils › Connecter une IA."))
    from .ia import _http, ErreurIA
    modele = _modele_tts(clef)
    consigne = texte if abs(vitesse - 1.0) < 0.05 else \
        (_("Lis à un rythme un peu rapide : ") if vitesse > 1 else _("Lis lentement et calmement : ")) + texte
    corps = {"contents": [{"parts": [{"text": consigne}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voix}}}}}
    try:
        r = _http(f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent", corps,
                  {"x-goog-api-key": clef, "Content-Type": "application/json"}, delai=180)
    except ErreurIA as e:
        raise ErreurVoix(str(e)) from e
    for p in ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []:
        d = p.get("inlineData") or p.get("inline_data")
        if d and d.get("data"):
            taux = int((re.search(r"rate=(\d+)", d.get("mimeType", "")) or [0, TAUX])[1])
            return ecrire_wav(sortie, base64.b64decode(d["data"]), taux)
    raise ErreurVoix(_("Gemini n'a pas renvoyé de voix."))


# ------------------------------------------------------------------ doublage
def traduire(textes, langue, params, en_ligne=False):
    """Traduit une liste de phrases. Local (modèle de vision portable ou Ollama) d'abord ; Claude ou Gemini si
    en_ligne (la confirmation du coût a été demandée avant). Renvoie une liste de même longueur."""
    if not textes:
        return []
    cible = NOMS_LANGUES.get(langue, langue)
    consignes = (f"Translate each sentence of the JSON list into {cible}, for a video voice-over: natural spoken "
                 f"{cible}, same meaning, about the same length. Answer with a JSON object {{\"t\": [...]}} with exactly "
                 f"{len(textes)} strings, in the same order.")
    texte = json.dumps(textes, ensure_ascii=False)
    if en_ligne:
        from . import ia
        r = ia.demander(params, consignes, texte, json_attendu=True, max_jetons=min(8000, 400 + len(texte)))
    else:
        from . import ia_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise ErreurVoix(_("Pas de modèle local pour traduire : cochez-en un dans Préférences › IA locale, ou choisissez Claude ou Gemini."))
        brut = ia_locale.generer(modele, consignes + "\n\n" + texte, json_attendu=True, params=params)
        from .ia import lire_json
        r = lire_json(brut)
    t = (r.get("t") if isinstance(r, dict) else r) or []
    t = [str(x) for x in t]
    if len(t) != len(textes):
        raise ErreurVoix(_("La traduction n'a pas le bon nombre de phrases ({a} au lieu de {b}).", a=len(t), b=len(textes)))
    return t


def segments_parles(projet, params, progression=None, langue=None):
    """Phrases prononcées dans les plans vidéo, placées sur la timeline : [(debut, fin, texte)]."""
    from . import sous_titres as ST
    segs = ST.transcrire_projet(projet, params, progression=progression, langue=langue or "auto", decouper=False)
    return [(a, b, t) for a, b, t, *_r in segs]


def assembler(morceaux, sortie, duree_totale=None):
    """morceaux : [(debut_s, chemin_wav, place_s)] ; chaque morceau est accéléré (jusqu'à 1,6×) s'il dépasse sa place,
    ramené à 24 kHz mono, puis posé à son moment dans une seule piste WAV."""
    import numpy as np
    tmp = tempfile.mkdtemp(prefix="philcut_voix_")
    pistes = []
    for i, (debut, chemin, place) in enumerate(morceaux):
        d = duree_wav(chemin)
        facteur = min(1.6, d / place) if place and d > place * 1.02 else 1.0
        f = os.path.join(tmp, f"m{i}.raw")
        filtres = [f"atempo={facteur:.3f}"] if facteur > 1.0 else []
        moteur.lancer(["-i", chemin] + (["-af", ",".join(filtres)] if filtres else []) + ["-ac", "1", "-ar", str(TAUX), "-f", "s16le", f])
        pistes.append((debut, np.fromfile(f, dtype="<i2")))
    fin = max([d + len(a) / TAUX for d, a in pistes] + [duree_totale or 0])
    total = np.zeros(int(fin * TAUX) + 1, dtype=np.int32)
    for d, a in pistes:
        i = int(d * TAUX)
        total[i:i + len(a)] += a
    ecrire_wav(sortie, np.clip(total, -32768, 32767).astype("<i2").tobytes())
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    return sortie


def doubler(projet, params, langue, sortie, voix=None, moteur_voix="local", traduction_en_ligne=False,
            langue_source=None, progression=None, arret=lambda: False):
    """Doublage complet ; renvoie (chemin du WAV, [(debut, fin, texte traduit)]) pour des sous-titres éventuels."""
    p = progression or (lambda f, t="": None)
    segs = segments_parles(projet, params, lambda f, t="": p(0.4 * f, _("Ecoute de la voix")), langue_source)
    if not segs:
        raise ErreurVoix(_("Aucune parole trouvée dans les plans vidéo."))
    p(0.42, _("Traduction"))
    trad = traduire([t for _a, _b, t in segs], langue, params, traduction_en_ligne)
    if moteur_voix == "local" and not voix:
        voix = voix_locale_langue(langue)
        if not voix:
            raise ErreurVoix(_("Pas de voix de synthèse dans cette langue sur ce poste : cochez-en une dans Préférences › IA locale."))
    tmp = tempfile.mkdtemp(prefix="philcut_doublage_")
    morceaux = []
    for i, ((a, b, _t), texte) in enumerate(zip(segs, trad)):
        if arret():
            raise InterruptedError()
        p(0.45 + 0.5 * i / len(segs), _("Lecture {i}/{n}", i=i + 1, n=len(segs)))
        suivant = segs[i + 1][0] if i + 1 < len(segs) else b + 1.0
        w = lire(texte, os.path.join(tmp, f"p{i}.wav"), params, moteur_voix, voix)
        morceaux.append((a, w, max(0.3, suivant - a - 0.05)))
    assembler(morceaux, sortie, projet.duree())
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    p(1.0, "")
    return sortie, [(a, b, t) for (a, b, _o), t in zip(segs, trad)]


def baisser_originaux(projet, niveau=0.15):
    """Garde un fond de la voix d'origine (ambiance), comme un doublage de documentaire."""
    for c in projet.clips_piste("video"):
        c["volume"] = min(c.get("volume", 1.0), niveau)
