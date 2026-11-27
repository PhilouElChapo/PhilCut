"""Voix par familles (1.2.0, plan musique validé par Philippe les 23, 24 et 25/11/2026).

Une voix gardée dans la bibliothèque (genre « voix ») devient un MODÈLE PRINCIPAL (« Archangel ») avec des VARIANTES
(chaude, aiguë, rapide…) ; une voix enregistrée, avec l'accord de la personne, est « réelle » (« Archangel (réel) ») et sert
aussi de timbre. Chaque voix et chaque variante a 7 réglages (0 à 100) : hauteur, étendue, chaleur, brillance, souffle,
vibrato, débit ; ils donnent la description anglaise envoyée au moteur. Les voix du catalogue « à la manière de » ont leurs
propres variantes (catalogue/styles.json, « variantes »), sinon un jeu déduit de leur famille musicale. Jamais un clone d'une
voix du catalogue : seulement une manière de chanter décrite.

Données d'une entrée « voix » de la bibliothèque (donnees) :
  reglages {clef: 0-100}, voix_decrite {en, fr}, reel bool, accord bool, role, variantes [{id, nom, mots[], reglages,
  voix_decrite, extrait}], extrait (nom de fichier gardé dans la bibliothèque)
"""
import os
import re
import time
import unicodedata
import uuid

from .langue import _

REGLAGES = (("hauteur", _("Hauteur")), ("etendue", _("Etendue")), ("chaleur", _("Chaleur")), ("brillance", _("Brillance")),
            ("souffle", _("Souffle")), ("vibrato", _("Vibrato")), ("debit", _("Débit")))
NEUTRES = {k: 50 for k, _l in REGLAGES}

# variantes types : ce qui change par rapport au modèle, et les mots qui les appellent dans une phrase
TYPES = {
    "chaude": (_("Chaude"), {"chaleur": +25, "brillance": -15, "souffle": +10}, ("chaude", "chaud", "warm", "solo")),
    "aigue": (_("Aiguë"), {"hauteur": +22, "brillance": +10}, ("aigue", "aigu", "haute", "high")),
    "grave": (_("Grave"), {"hauteur": -22, "chaleur": +10}, ("grave", "basse", "low", "deep")),
    "rapide": (_("Rapide"), {"debit": +30, "vibrato": -15}, ("rapide", "effrene", "vite", "fast")),
    "lente": (_("Lente"), {"debit": -25, "vibrato": +10}, ("lente", "lent", "slow")),
    "douce": (_("Douce"), {"souffle": +20, "brillance": -10, "chaleur": +10}, ("douce", "doux", "soft", "tendre")),
    "puissante": (_("Puissante"), {"etendue": +15, "brillance": +15, "souffle": -15}, ("puissante", "puissant", "forte", "powerful")),
    "rauque": (_("Rauque"), {"souffle": +15, "brillance": -5, "chaleur": +5}, ("rauque", "rocailleuse", "raspy", "gritty")),
    "soufflee": (_("Soufflée"), {"souffle": +30, "brillance": -10}, ("soufflee", "souffle", "airy", "breathy", "murmuree")),
}

# ------------------------------------------------------------------ variantes des voix du catalogue (1.2.1)
# Propres à chaque voix (choix de Philippe, 25/11) : d'après sa famille musicale et les mots de sa description ; écrites dans
# catalogue/styles.json par outils_dev/variantes_voix.py (le catalogue en ligne peut les corriger), sinon calculées ici.
# id : (noms fr/en/de/es/it, ajout anglais, mots qui l'appellent, mots de la description qui la rendent inutile)
V = {
    "douce": (("Douce (ballade)", "Soft (ballad)", "Sanft (Ballade)", "Suave (balada)", "Dolce (ballata)"),
              "softer gentle ballad delivery, intimate", ("douce", "doux", "ballade", "soft", "tendre"), ("soft", "gentle", "whisper")),
    "puissante": (("Puissante (refrain)", "Powerful (chorus)", "Kraftvoll (Refrain)", "Potente (estribillo)", "Potente (ritornello)"),
                  "full powerful chest voice, big chorus energy", ("puissante", "puissant", "refrain", "fort"), ("powerful", "soaring", "belting")),
    "rauque": (("Rauque", "Raspy", "Rau", "Ronca", "Roca"), "raspier gritty edge, rough texture", ("rauque", "raspy", "rocailleuse"),
               ("raspy", "gritty", "gravelly", "rough")),
    "criee": (("Criée", "Screamed", "Geschrien", "Gritada", "Urlata"), "screamed aggressive delivery, intense shouts", ("criee", "cri", "hurlee"),
              ("scream", "growl", "shout")),
    "intime": (("Soufflée (intime)", "Breathy (intimate)", "Gehaucht (intim)", "Susurrada (íntima)", "Sussurrata (intima)"),
               "breathy whispered close-mic delivery", ("soufflee", "intime", "murmuree", "breathy"), ("whisper", "breathy", "airy")),
    "parlee": (("Parlée-chantée", "Spoken-sung", "Gesprochen-gesungen", "Hablada-cantada", "Parlata-cantata"),
               "half-spoken storytelling delivery", ("parlee", "parle", "spoken"), ("spoken", "half-spoken", "talk")),
    "lyrique": (("Lyrique", "Lyrical", "Lyrisch", "Lírica", "Lirica"), "lyrical sustained legato lines, rich vibrato",
                ("lyrique", "legato"), ("operatic", "legato")),
    "crooner": (("Crooner", "Crooner", "Crooner", "Crooner", "Crooner"), "velvety relaxed crooning, close to the mic, warm legato",
                ("crooner", "croon", "velours"), ()),
    "swing": (("Swing", "Swing", "Swing", "Swing", "Swing"), "upbeat swinging phrasing, playful timing", ("swing", "swinguee"), ("swing",)),
    "feutree": (("Feutrée", "Hushed", "Gedämpft", "Aterciopelada", "Vellutata"), "hushed velvety late-night delivery",
                ("feutree", "velours", "nuit"), ("smoky", "velvet", "silky")),
    "gospel": (("Gospel", "Gospel", "Gospel", "Gospel", "Gospel"), "gospel-inflected powerful runs and melisma", ("gospel",),
               ("gospel",)),
    "scat": (("Scat", "Scat", "Scat", "Scat", "Scat"), "playful jazz scat improvisation", ("scat",), ("scat",)),
    "flow_rapide": (("Flow serré", "Rapid flow", "Schneller Flow", "Flow rápido", "Flow veloce"), "rapid-fire tight rap flow",
                    ("rapide", "serre", "flow", "fast"), ("rapid", "fast")),
    "posee": (("Posée", "Laid-back", "Entspannt", "Relajada", "Rilassata"), "laid-back relaxed rap delivery, behind the beat",
              ("posee", "calme", "laid"), ("laid-back", "relaxed", "drawling")),
    "chantee": (("Chantée (mélodique)", "Sung (melodic)", "Gesungen (melodisch)", "Cantada (melódica)", "Cantata (melodica)"),
                "melodic sung hook, autotuned", ("chantee", "melodique", "melodic"), ("melodic", "autotune", "sung")),
    "acoustique": (("Acoustique", "Acoustic", "Akustisch", "Acústica", "Acustica"), "plain acoustic campfire delivery, warm and close",
                   ("acoustique", "guitare", "feu"), ("acoustic",)),
    "harmonies": (("Harmonies", "Harmonies", "Harmonien", "Armonías", "Armonie"), "stacked close vocal harmonies", ("harmonies", "choeur"),
                  ("harmon",)),
    "robotique": (("Robotique (vocoder)", "Robotic (vocoder)", "Robotisch (Vocoder)", "Robótica (vocoder)", "Robotica (vocoder)"),
                  "robotic vocoder-processed vocals", ("robot", "robotique", "vocoder"), ("vocoder", "robot")),
    "planante": (("Planante", "Dreamy", "Verträumt", "Etérea", "Sognante"), "dreamy reverb-drenched floating vocals",
                 ("planante", "reve", "dreamy"), ("dreamy", "reverb", "floating")),
    "chaude": (("Chaude", "Warm", "Warm", "Cálida", "Calda"), "warmer richer tone", ("chaude", "chaud", "warm"), ("warm",)),
    "aigue": (("Aiguë", "High", "Hoch", "Aguda", "Acuta"), "higher register, head voice", ("aigue", "haute", "high"), ("high", "falsetto")),
    "grave": (("Grave", "Low", "Tief", "Grave", "Grave"), "lower register, deep tone", ("grave", "basse", "low"), ("deep", "low", "baritone")),
}

PAR_GENRE = {
    "rock_metal": ("rauque", "criee", "puissante", "douce"),
    "pop": ("douce", "puissante", "intime", "aigue"),
    "chanson": ("douce", "parlee", "lyrique", "puissante"),
    "rap": ("flow_rapide", "posee", "chantee", "grave"),
    "jazz_soul": ("feutree", "swing", "gospel", "douce"),
    "folk_country": ("acoustique", "harmonies", "rauque", "douce"),
    "electro": ("robotique", "planante", "intime", "aigue"),
    "monde": ("chaude", "douce", "puissante", "harmonies"),
    "classique": ("lyrique", "douce", "puissante", "aigue"),
    "film": ("douce", "puissante", "lyrique", "intime"),
    "chant": ("chaude", "douce", "puissante", "lyrique"),
}
# quelques voix où la famille ne suffit pas (mots de la description → variantes en tête)
INDICES = ((r"croon", ("crooner", "swing", "douce", "feutree")), (r"scat", ("scat", "swing", "douce")), (r"metal|growl|scream", ("criee", "rauque", "douce")),
           (r"punk", ("criee", "rauque", "puissante")), (r"opera|operatic", ("lyrique", "puissante", "douce")),
           (r"whisper|breathy", ("intime", "douce", "puissante")), (r"vocoder|robot", ("robotique", "planante", "intime")),
           (r"rap", ("flow_rapide", "posee", "chantee")), (r"country|folk", ("acoustique", "harmonies", "douce")),
           (r"gospel|soul", ("gospel", "feutree", "douce")))


def variantes_pour(genre, voix_en, n=4):
    texte = voix_en.lower()
    ordre = []
    for motif, ids in INDICES:
        if re.search(motif, texte):
            ordre += ids
    ordre += PAR_GENRE.get(genre, PAR_GENRE["chant"])
    ordre += ["chaude", "puissante", "aigue", "grave", "douce", "rauque"]     # de quoi en avoir au moins 3
    out = []
    for i in dict.fromkeys(ordre):
        noms, ajout, mots, inutile = V[i]
        if any(m in texte for m in inutile) and i not in ("crooner", "swing", "scat", "gospel", "lyrique"):
            continue                                   # déjà dans la voix : pas une variante
        out.append({"id": i, "noms": dict(zip(("fr", "en", "de", "es", "it"), noms)), "en": f"{voix_en}, {ajout}",
                    "mots": list(mots)})
        if len(out) >= n:
            break
    return out


PHRASE_NEUTRE = {"fr": "La lumière se lève sur la ville, je chante pour toi ce soir",
                 "en": "The light is rising on the city, I sing for you tonight"}
PRIX_CLOUD_S = 0.0002                      # fal-ai/ace-step, par seconde produite (relevé le 25/11/2026)


def _net(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def _borne(v):
    return int(max(0, min(100, round(v))))


# ------------------------------------------------------------------ réglages ↔ mesures ↔ description
def reglages_depuis_mesures(m):
    """Mesures de musique_ia.mesurer_voix (f0 Hz, etendue demi-tons, vibrato cents, brillance Hz, souffle, nettete) → 0-100."""
    import math
    m = m or {}
    r = dict(NEUTRES)
    if m.get("f0"):
        r["hauteur"] = _borne(100 * (math.log2(float(m["f0"])) - math.log2(80)) / (math.log2(420) - math.log2(80)))
    if m.get("etendue") is not None:
        r["etendue"] = _borne(float(m["etendue"]) * 100 / 24)
    if m.get("vibrato") is not None:
        r["vibrato"] = _borne(float(m["vibrato"]) * 100 / 50)
    if m.get("brillance"):
        r["brillance"] = _borne((float(m["brillance"]) - 900) * 100 / 2600)
        r["chaleur"] = _borne(100 - r["brillance"] * 0.8 - (10 if (m.get("nettete") or 1) > 0.85 else 0))
    if m.get("souffle") is not None:
        r["souffle"] = _borne(float(m["souffle"]) * 100 / 0.25)
    if m.get("debit") is not None:
        r["debit"] = _borne(m["debit"])
    return r


def decrire(reglages):
    """7 réglages → (description anglaise pour le moteur, résumé dans la langue de PhilCut)."""
    g = dict(NEUTRES, **(reglages or {}))
    en, fr = [], []
    h = g["hauteur"]
    if h < 20:
        en.append("deep low vocals"); fr.append(_("voix grave"))
    elif h < 40:
        en.append("low-mid baritone range vocals"); fr.append(_("voix médium grave"))
    elif h < 60:
        en.append("mid-range vocals"); fr.append(_("voix médium"))
    elif h < 80:
        en.append("high vocals, alto to tenor range"); fr.append(_("voix haute"))
    else:
        en.append("very high soprano vocals"); fr.append(_("voix très aiguë"))
    if g["etendue"] >= 65:
        en.append("wide range with big leaps"); fr.append(_("grande étendue"))
    elif g["etendue"] <= 25:
        en.append("narrow melody close to speech"); fr.append(_("mélodie resserrée"))
    if g["chaleur"] >= 65:
        en.append("warm rich timbre"); fr.append(_("timbre chaud"))
    if g["brillance"] >= 65:
        en.append("bright clear timbre"); fr.append(_("timbre brillant"))
    elif g["brillance"] <= 25 and g["chaleur"] < 65:
        en.append("dark mellow timbre"); fr.append(_("timbre sombre"))
    if g["souffle"] >= 70:
        en.append("airy breathy delivery"); fr.append(_("voix soufflée"))
    elif g["souffle"] >= 55:
        en.append("slightly husky"); fr.append(_("un peu voilée"))
    elif g["souffle"] <= 20:
        en.append("full clean tone"); fr.append(_("son plein et net"))
    if g["vibrato"] >= 60:
        en.append("pronounced vibrato"); fr.append(_("vibrato marqué"))
    elif g["vibrato"] >= 30:
        en.append("light vibrato"); fr.append(_("léger vibrato"))
    else:
        en.append("straight tone"); fr.append(_("voix droite"))
    if g["debit"] >= 70:
        en.append("fast rapid-fire phrasing"); fr.append(_("débit rapide"))
    elif g["debit"] <= 30:
        en.append("slow sustained phrasing"); fr.append(_("phrasé lent et tenu"))
    return ", ".join(en), ", ".join(fr)


def appliquer(base, ecarts):
    """Réglages d'une variante type à partir du modèle principal."""
    r = dict(NEUTRES, **(base or {}))
    for k, d in (ecarts or {}).items():
        r[k] = _borne(r.get(k, 50) + d)
    return r


def variante_type(cle, base):
    nom, ecarts, mots = TYPES[cle]
    reg = appliquer(base, ecarts)
    en, fr = decrire(reg)
    return {"id": cle, "nom": nom, "mots": list(mots), "reglages": reg, "voix_decrite": {"en": en, "fr": fr}}


# ------------------------------------------------------------------ mes voix (bibliothèque)
def nom_affiche(e):
    d = e.get("donnees") or {}
    return e["nom"] + (" " + _("(réel)") if d.get("reel") else "")


def mes_voix(params):
    """Les voix gardées, par ordre alphabétique (bibliotheque_creations.lister trie déjà)."""
    from . import bibliotheque_creations as B
    return B.lister(params, "voix")


def reglages_de(e):
    d = e.get("donnees") or {}
    if d.get("reglages"):
        return dict(NEUTRES, **d["reglages"])
    m = (d.get("voix_decrite") or {}).get("mesures") or d.get("mesures")
    return reglages_depuis_mesures(m) if m else dict(NEUTRES)


def variantes(e):
    """Variantes de l'entrée, triées par nom ; la première ligne de l'arbre est « Normale » (le modèle lui-même)."""
    return sorted((e.get("donnees") or {}).get("variantes") or [], key=lambda v: _net(v.get("nom")))


def garder_principal(params, nom, reglages, voix_decrite=None, extrait=None, reel=False, voix_seule=None, accord=False,
                     role="", source="", ident=None):
    """« ☆ Garder comme modèle principal » : range la voix dans la bibliothèque (genre voix)."""
    from . import bibliotheque_creations as B
    if reel and not accord:
        raise ValueError(_("Une voix réelle se garde seulement avec l'accord de la personne (case à cocher)."))
    en, fr = decrire(reglages)
    vd = dict(voix_decrite or {}) or {"en": en, "fr": fr}
    fichiers = {}
    if extrait:
        fichiers["extrait"] = extrait
    if reel and voix_seule:
        fichiers["voix_seule"] = voix_seule
    donnees = {"reglages": dict(NEUTRES, **(reglages or {})), "voix_decrite": vd, "reel": bool(reel), "accord": bool(accord),
               "role": role, "source": source}
    return B.garder(params, "voix", nom, vd.get("fr", ""), fichiers, donnees, ident)


def ajouter_variante(params, e, nom, reglages, mots=None, extrait=None, ident=None):
    """« + Ajouter une variante » (ou « Garder comme variante… ») : sous-famille du modèle principal."""
    from . import bibliotheque_creations as B
    nom = re.sub(r"\s+", " ", nom or "").strip()[:60]
    if not nom:
        raise ValueError(_("Donnez un nom à la variante."))
    vs = [v for v in (e.get("donnees") or {}).get("variantes") or [] if v.get("id") != ident]
    ident = ident or uuid.uuid4().hex[:8]
    en, fr = decrire(reglages)
    v = {"id": ident, "nom": nom, "mots": [m for m in dict.fromkeys([_net(nom)] + [_net(x) for x in (mots or [])]) if m],
         "reglages": dict(NEUTRES, **(reglages or {})), "voix_decrite": {"en": en, "fr": fr}, "cree": time.strftime("%Y-%m-%d %H:%M")}
    fichiers = {}
    if extrait:
        fichiers["extrait_" + ident] = extrait
        v["extrait"] = "extrait_" + ident
    ancienne = next((x for x in (e.get("donnees") or {}).get("variantes") or [] if x.get("id") == ident), None)
    if ancienne and ancienne.get("extrait") and not extrait:
        v["extrait"] = ancienne["extrait"]
    vs.append(v)
    return B.garder(params, "voix", e["nom"], e.get("description", ""), fichiers, {"variantes": vs}, e["id"])


def retirer_variante(params, e, ident):
    from . import bibliotheque_creations as B
    vs = [v for v in (e.get("donnees") or {}).get("variantes") or [] if v.get("id") != ident]
    return B.garder(params, "voix", e["nom"], e.get("description", ""), None, {"variantes": vs}, e["id"])


# ------------------------------------------------------------------ 1.3.13 : ma voix parlée (Continuer avec ma voix, Voix off)
def voix_parlees(params):
    """Les voix parlées gardées (5 à 15 s de la personne qui parle), modèle et variantes : [{nom, chemin, entree, variante}],
    par ordre alphabétique. Elles disent n'importe quel texte sur ce poste (« Continuer avec ma voix », Voix off)."""
    out = []
    for e in mes_voix(params):
        f = e.get("fichiers") or {}
        if f.get("parole") and os.path.exists(f["parole"]):
            out.append({"nom": e["nom"], "chemin": f["parole"], "entree": e["id"], "variante": ""})
        for v in variantes(e):
            k = v.get("parole")
            if k and f.get(k) and os.path.exists(f[k]):
                out.append({"nom": f"{e['nom']} — {v['nom']}", "chemin": f[k], "entree": e["id"], "variante": v["id"]})
    return sorted(out, key=lambda x: _net(x["nom"]))


def garder_parole(params, nom, chemin, accord, variante=""):
    """Garde l'extrait de voix parlée `chemin` (WAV) sous « nom » (sa voix, avec l'accord) ; `variante` (« calme »,
    « enjouée »…) en fait une sous-famille de la même voix. Renvoie l'entrée."""
    from . import bibliotheque_creations as B
    if not accord:
        raise ValueError(_("Une voix réelle se garde seulement avec l'accord de la personne (case à cocher)."))
    nom = re.sub(r"\s+", " ", nom or "").strip()[:60]
    if not nom:
        raise ValueError(_("Donnez un nom à la voix."))
    e = next((x for x in mes_voix(params) if _net(x["nom"]) == _net(nom)), None)
    if e is None:
        e = garder_principal(params, nom, {}, reel=True, accord=True, role="narration", source="parole")
    variante = re.sub(r"\s+", " ", variante or "").strip()[:60]
    if not variante:
        return B.garder(params, "voix", e["nom"], e.get("description", ""), {"parole": chemin},
                        {"parole": True, "reel": True, "accord": True}, e["id"])
    vs = list((e.get("donnees") or {}).get("variantes") or [])
    v = next((x for x in vs if _net(x.get("nom")) == _net(variante)), None)
    if v is None:
        v = {"id": uuid.uuid4().hex[:8], "nom": variante, "mots": [_net(variante)], "reglages": dict(reglages_de(e)),
             "voix_decrite": dict((e.get("donnees") or {}).get("voix_decrite") or {}), "cree": time.strftime("%Y-%m-%d %H:%M")}
        vs.append(v)
    v["parole"] = "parole_" + v["id"]
    return B.garder(params, "voix", e["nom"], e.get("description", ""), {v["parole"]: chemin},
                    {"variantes": vs, "reel": True, "accord": True}, e["id"])


def extrait_de(e, variante=None):
    """L'extrait de pré-écoute déjà gardé (rien n'est recalculé), ou ''."""
    f = e.get("fichiers") or {}
    if variante:
        return f.get(variante.get("extrait") or "", "")
    return f.get("extrait", "")


def garder_extrait(params, e, chemin, variante=None):
    from . import bibliotheque_creations as B
    if variante:
        vs = [dict(v, extrait="extrait_" + v["id"]) if v.get("id") == variante.get("id") else v
              for v in (e.get("donnees") or {}).get("variantes") or []]
        return B.garder(params, "voix", e["nom"], e.get("description", ""), {"extrait_" + variante["id"]: chemin},
                        {"variantes": vs}, e["id"])
    return B.garder(params, "voix", e["nom"], e.get("description", ""), {"extrait": chemin}, None, e["id"])


# ------------------------------------------------------------------ catalogue « à la manière de »
def catalogue(params=None):
    """[(nom, genre, description anglaise de la voix, [variantes])] des styles du catalogue qui décrivent une voix,
    par ordre alphabétique. Variantes : celles du catalogue en ligne, sinon déduites de la famille musicale."""
    from . import styles_ia as S
    S._catalogue()
    vus, out = set(), []
    for cle, (nom, d) in S._toutes(params).items():
        if nom in vus or not d.get("voix"):
            continue
        vus.add(nom)
        g = S.genre(nom)
        vs = S._CATALOGUE.get("variantes", {}).get(_net(nom)) or variantes_pour(g, d["voix"])
        from .langue import LANGUE
        vs = [dict(v, nom=(v.get("noms") or {}).get(LANGUE) or (v.get("noms") or {}).get("fr") or v.get("nom") or v["id"]) for v in vs]
        out.append({"nom": nom, "genre": g, "en": d["voix"], "variantes": vs})
    return sorted(out, key=lambda x: _net(x["nom"]))


# ------------------------------------------------------------------ dans une phrase (« à la manière d'Archangel, voix chaude »)
def trouver(texte, params):
    """Une voix gardée nommée dans la phrase : {"entree", "variante" (ou None = modèle principal), "mot_inconnu",
    "debut", "fin"} ; None si aucune. Les voix gardées passent avant le catalogue."""
    net = _net(texte)
    meilleure = None
    for e in mes_voix(params):
        for m in re.finditer(r"(?<![\w])" + re.escape(_net(e["nom"])) + r"(?![\w])", net):
            if meilleure is None or len(e["nom"]) > len(meilleure[0]["nom"]):
                meilleure = (e, m)
    if not meilleure:
        return None
    e, m = meilleure
    debut, fin = m.start(), m.end()
    lien = re.search(r"(?:a\s+la\s+maniere\s+(?:de\s+|d'|du\s+)|facon\s+|comme\s+|style\s+(?:de\s+|d')?|(?:chante|voix)\s+(?:de\s+|d')?)$",
                     net[max(0, debut - 40):debut])
    if lien:
        debut = max(0, debut - 40) + lien.start()
    apres = net[fin:fin + 40]
    mots = re.findall(r"[a-z]+", apres)[:4]
    stop = {"voix", "avec", "une", "un", "la", "le", "en", "et", "de", "d", "plus", "tres", "mode"}
    mots = [w for w in mots if w not in stop]
    vs = variantes(e)
    for w in mots[:2]:
        for v in vs:
            if w in (v.get("mots") or []) or w == _net(v.get("nom")) or _net(v.get("nom")).startswith(w):
                return {"entree": e, "variante": v, "mot_inconnu": "", "debut": debut, "fin": fin + apres.find(w) + len(w)}
    # un mot de variante type absent de cette voix : on demande (choix de Philippe, 25/11)
    for w in mots[:1]:
        for cle, (_n, _e, m2) in TYPES.items():
            if w in m2:
                return {"entree": e, "variante": None, "mot_inconnu": w, "type": cle, "debut": debut, "fin": fin + apres.find(w) + len(w)}
    return {"entree": e, "variante": None, "mot_inconnu": "", "debut": debut, "fin": fin}


def choix(e, variante=None):
    """Ce que la Fabrique pose pour cette voix : {"nom", "voix_decrite": {en, fr}, "reference" (timbre, voix réelle), …}."""
    d = e.get("donnees") or {}
    reg = (variante or {}).get("reglages") or reglages_de(e)
    vd = (variante or {}).get("voix_decrite") or d.get("voix_decrite") or dict(zip(("en", "fr"), decrire(reg)))
    nom = nom_affiche(e) + (" › " + variante["nom"] if variante else "")
    r = {"nom": nom, "entree": e["id"], "variante": (variante or {}).get("id", ""), "reglages": reg,
         "voix_decrite": {"en": vd.get("en", ""), "fr": vd.get("fr", ""), "fichier": nom}}
    f = e.get("fichiers") or {}
    if d.get("reel") and d.get("accord") and f.get("voix_seule"):
        r["reference"] = f["voix_seule"]
    return r


def choix_catalogue(entree, variante=None):
    en = (variante or {}).get("en") or entree["en"]
    nom = entree["nom"] + " " + _("(à la manière de)") + (" › " + variante["nom"] if variante else "")
    return {"nom": nom, "catalogue": entree["nom"], "variante": (variante or {}).get("id", ""), "reglages": None,
            "voix_decrite": {"en": en, "fr": _("à la manière de {n}", n=entree["nom"]) + (f" ({variante['nom']})" if variante else ""),
                             "fichier": nom}}


# ------------------------------------------------------------------ pré-écoute
def ligne_paroles(paroles, langue="fr"):
    """Une ligne chantée des paroles en cours (environ 10 s), sinon une phrase neutre."""
    for ligne in (paroles or "").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("[") and len(ligne) >= 8:
            return ligne[:90]
    return PHRASE_NEUTRE.get(langue, PHRASE_NEUTRE["en"])


def prix_cloud(secondes=10):
    return round(PRIX_CLOUD_S * secondes, 4)


def preecoute(voix_en, paroles, sortie, params, langue="fr", ou="local", reference=None, secondes=10, progression=None,
              arret=lambda: False):
    """Environ 10 s chantées avec cette manière : sur ce poste (moteur de musique, gratuit) ou par fal.ai (ACE-Step, prix
    demandé avant). Renvoie le chemin du fichier."""
    ligne = ligne_paroles(paroles, langue)
    caption = "short a cappella-like vocal demo with soft piano, " + (voix_en or "clear vocals")
    if ou == "cloud":
        from . import generateurs_video as GV
        cle = GV.clef(params, "fal")
        if not cle:
            raise ValueError(_("Pas de clef fal.ai : choisissez « sur ce poste » ou connectez fal.ai (Préférences › IA)."))
        if progression:
            progression(0.1, _("Envoi à fal.ai (ACE-Step)…"))
        res = GV.demande_fal(cle, "fal-ai/ace-step", {"tags": caption, "lyrics": "[verse]\n" + ligne, "duration": secondes})
        url = (res.get("audio") or {}).get("url")
        if not url:
            raise ValueError(_("fal.ai n'a pas rendu d'extrait : {r}", r=str(res)[:200]))
        import urllib.request
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "PhilCut"}), timeout=120) as r, \
                open(sortie, "wb") as f:
            f.write(r.read())
        try:
            from .credit_ia import noter_depense
            noter_depense("fal", prix_cloud(secondes))
        except Exception:      # noqa: BLE001
            pass
        return sortie
    from . import creatif as C
    options = {"reference": reference} if reference else {}
    return C.musique(caption, sortie, float(secondes), params, False, "[verse]\n" + ligne, langue=langue, progression=progression,
                     arret=arret, voix="", options=options)


def dossier_extraits():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "voix_extraits")
    os.makedirs(d, exist_ok=True)
    return d
