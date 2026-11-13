"""« Continuer avec ma voix » (0.9.57) : une phrase dite avec la voix d'un extrait de 5 à 15 secondes, sur ce poste.

Modèle : Chatterbox Multilingual de Resemble AI (licence MIT, 23 langues dont le français), export ONNX de onnx-community :
- speech_encoder : l'extrait de voix (24 kHz) -> empreinte de la voix (cond_emb, jetons de l'extrait, timbre, traits) ;
- embed_tokens   : jetons (texte puis parole) -> vecteurs, avec l'« expressivité » (exaggeration) ;
- language_model : un Llama de 0,5 milliard de paramètres (variante q4, 354 Mo) qui écrit la parole jeton par jeton ;
- conditional_decoder : jetons de parole + timbre -> son à 24 kHz.

La suite des opérations reprend le code d'exemple de la carte du modèle (onnx-community/chatterbox-multilingual-ONNX) :
langue en tête du texte (« [fr]… »), positions -1, 0, 1… pour le texte et 0 pour les jetons de parole, empreinte de la
voix devant le texte au premier pas, pénalité de répétition 1,2, choix du jeton le plus probable, arrêt au jeton 6562,
puis jetons de l'extrait + jetons produits envoyés au décodeur.

Règles de PhilCut : uniquement la voix de l'utilisateur ou d'une personne qui a donné son accord (case à cocher qui engage
l'auteur), jamais la voix d'une personne connue ; rien ne sort du poste ; le fichier produit dit qu'il est fait par IA.
"""
import os, re, unicodedata, wave

from .langue import _

CLE = "voix_clone"
TAUX = 24000
DEBUT_PAROLE, FIN_PAROLE = 6561, 6562
COUCHES, TETES, DIM_TETE = 30, 16, 64
PENALITE = 1.2
REF_MIN, REF_MAX = 3.0, 15.0             # secondes d'extrait de voix
LANGUES = ("ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi", "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv",
           "sw", "tr", "zh")
LANGUES_SIMPLES = ("da", "de", "el", "en", "es", "fi", "fr", "it", "ms", "nl", "no", "pl", "pt", "ru", "sv", "sw", "tr")
ROLES = ("encodeur", "encodeur_donnees", "jetons", "jetons_donnees", "langage", "langage_donnees", "decodeur", "decodeur_donnees",
         "tokenizer")


class ErreurVoix(Exception):
    pass


# ---------------------------------------------------------------- installation
def manquant(params=None):
    """Le texte à montrer si la voix ne peut pas être fabriquée sur ce poste, sinon None."""
    from . import packs_ia as P
    if not P.onnx_present():
        return _("Le moteur ONNX de PhilCut est absent : réinstallez PhilCut.")
    try:
        import tokenizers  # noqa: F401
    except ImportError:
        return _("Le découpeur de texte de PhilCut est absent : réinstallez PhilCut.")
    if not P.installe(CLE):
        return _("Installez le modèle « Continuer avec ma voix » : Edition › Préférences › IA locale (environ 1,6 Go, gratuit, "
                 "licence MIT, tout reste sur ce poste).")
    return None


def _chemins():
    from . import packs_ia as P
    roles = (P.etat().get(CLE) or {}).get("roles") or {}
    d = P.dossier_modele(CLE)
    return {r: os.path.join(d, n) for r, n in roles.items()}


_SESSIONS = {}


def sessions(params=None, chemins=None):
    """Les quatre modèles ONNX et le découpeur de texte, chargés une fois."""
    chemins = chemins or _chemins()
    cle = tuple(sorted(chemins.items()))
    if _SESSIONS.get("cle") == cle:
        return _SESSIONS["s"]
    import onnxruntime as ort
    from tokenizers import Tokenizer
    from . import packs_ia as P
    o = ort.SessionOptions()
    try:
        o.intra_op_num_threads = P.coeurs(params)
    except Exception:      # noqa: BLE001
        pass
    cpu = ["CPUExecutionProvider"]
    s = {nom: ort.InferenceSession(chemins[role], o, providers=cpu)
         for nom, role in (("encodeur", "encodeur"), ("jetons", "jetons"), ("langage", "langage"), ("decodeur", "decodeur"))}
    s["tokenizer"] = Tokenizer.from_file(chemins["tokenizer"])
    _SESSIONS.clear()
    _SESSIONS.update({"cle": cle, "s": s})
    return s


# ---------------------------------------------------------------- texte
def normaliser(texte):
    """Ponctuation propre (la reprise du modèle d'origine) : espaces, guillemets et tirets typographiques, une majuscule au
    début, un point à la fin."""
    t = " ".join((texte or "").split())
    for a, b in (("« ", '"'), (" »", '"'), ("“", '"'), ("”", '"'), ("«", '"'), ("»", '"'), ("‘", "'"), ("’", "'"), ("—", "-"), ("–", "-"), ("…", "..."),
                 (" ,", ","), (" .", "."), (" ", " ")):
        t = t.replace(a, b)
    t = re.sub(r'\s+([?!:;])', r'\1', t).strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    if t[-1] not in ".!?-,":
        t += "."
    return t


def phrases(texte, maxi=220):
    """Découpe un long texte en morceaux d'une à quelques phrases (le modèle tient environ 20 s par morceau)."""
    morceaux, cour = [], ""
    for p in re.split(r'(?<=[.!?])\s+', normaliser(texte)):
        if not p:
            continue
        while len(p) > maxi:                                     # phrase très longue : coupée à une virgule ou un espace
            i = max(p.rfind(", ", 0, maxi), p.rfind(" ", 0, maxi))
            i = i if i > maxi // 3 else maxi
            morceaux.append(p[:i + 1].strip())
            p = p[i + 1:].strip()
        if cour and len(cour) + 1 + len(p) > maxi:
            morceaux.append(cour)
            cour = p
        else:
            cour = (cour + " " + p).strip()
    if cour:
        morceaux.append(cour)
    return [normaliser(m) for m in morceaux if m.strip(" .")]


def jetons_texte(tokenizer, texte, langue):
    """Identifiants des jetons du texte, langue en tête ([fr]…), comme le code d'exemple du modèle."""
    import numpy as np
    langue = (langue or "fr").lower()
    if langue not in LANGUES:
        raise ErreurVoix(_("Langue non prise en charge : {l}.", l=langue))
    t = f"[{langue}]{texte}"
    ids = tokenizer.encode(t).ids
    return np.array([ids], dtype=np.int64)


def jetons_attendus(texte):
    """Nombre maximal de jetons de parole pour un morceau (25 jetons par seconde, environ 14 caractères par seconde, marge)."""
    return int(min(1000, 60 + len(texte) * 25 / 11))


# ---------------------------------------------------------------- son
def lire_reference(source, debut=0.0, duree=None):
    """L'extrait de voix : mono 24 kHz float32, 3 à 15 s (au-delà : les 15 premières secondes)."""
    import numpy as np
    from . import moteur
    duree = min(REF_MAX, duree) if duree else REF_MAX
    brut = moteur.sortie(["-ss", f"{max(0.0, debut):.3f}", "-t", f"{duree:.3f}", "-i", source, "-vn", "-ac", "1", "-ar", str(TAUX),
                          "-f", "f32le", "pipe:1"], delai=600)
    a = np.frombuffer(brut[: len(brut) - len(brut) % 4], dtype=np.float32).copy()
    if a.size < REF_MIN * TAUX:
        raise ErreurVoix(_("L'extrait de voix est trop court : il faut au moins {n} secondes de parole.", n=int(REF_MIN)))
    if float(np.sqrt(np.mean(a ** 2))) < 0.003:
        raise ErreurVoix(_("L'extrait choisi est silencieux : choisissez un passage où l'on entend la voix."))
    return a


def niveau(a):
    import numpy as np
    a = np.asarray(a, dtype=np.float32)
    parle = a[np.abs(a) > 0.02]
    return float(np.sqrt(np.mean(parle ** 2))) if parle.size > TAUX // 10 else float(np.sqrt(np.mean(a ** 2)) + 1e-9)


def ecrire(chemin, son, taux=TAUX):
    """WAV 16 bits mono, avec la mention qu'il est fait par IA (bloc LIST/INFO : ICMT et ISFT)."""
    import numpy as np
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    pcm = (np.clip(son, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taux)
        w.writeframes(pcm.tobytes())
    _mention_ia(chemin)
    return chemin


def _mention_ia(chemin):
    """Ajoute au WAV un bloc LIST/INFO : commentaire « voix fabriquée par IA » et logiciel."""
    import struct

    def champ(cle, texte):
        b = texte.encode("utf-8") + b"\0"
        if len(b) % 2:
            b += b"\0"
        return cle + struct.pack("<I", len(b)) + b
    info = b"INFO" + champ(b"ICMT", "Voix fabriquee par IA (Chatterbox, PhilCut) a partir d'un extrait consenti") + \
        champ(b"ISFT", "PhilCut")
    bloc = b"LIST" + struct.pack("<I", len(info)) + info
    with open(chemin, "r+b") as f:
        f.seek(0, 2)
        f.write(bloc)
        taille = f.tell()
        f.seek(4)
        f.write(struct.pack("<I", taille - 8))


def lire_mention(chemin):
    with open(chemin, "rb") as f:
        return b"Voix fabriquee par IA" in f.read()


# ---------------------------------------------------------------- génération
def empreinte(s, reference):
    """Empreinte de la voix : (cond_emb, jetons de l'extrait, timbre, traits)."""
    import numpy as np
    sortie = s["encodeur"].run(None, {"audio_values": reference[np.newaxis, :].astype(np.float32)})
    return tuple(sortie[:4])


def _penaliser(deja, logits, penalite=PENALITE):
    import numpy as np
    sc = np.take_along_axis(logits, deja, axis=1)
    sc = np.where(sc < 0, sc * penalite, sc / penalite)
    out = logits.copy()
    np.put_along_axis(out, deja, sc, axis=1)
    return out


def parole(s, ids, emp, expressivite=0.5, maxi=400, progression=None, arret=lambda: False):
    """Jetons de parole d'un morceau de texte (sans les jetons de début et de fin)."""
    import numpy as np
    cond, _jt, _timbre, _traits = emp
    pos = np.where(ids >= DEBUT_PAROLE, 0, np.arange(ids.shape[1])[np.newaxis, :] - 1).astype(np.int64)
    entrees = {"input_ids": ids, "position_ids": pos, "exaggeration": np.array([expressivite], dtype=np.float32)}
    produits = np.array([[DEBUT_PAROLE]], dtype=np.int64)
    noms_kv = [f"past_key_values.{c}.{kv}" for c in range(COUCHES) for kv in ("key", "value")]
    types = {i.name: i.type for i in s["langage"].get_inputs()}
    dt = np.float16 if "float16" in types.get(noms_kv[0], "") else np.float32
    passe, masque = None, None
    for i in range(maxi):
        if arret():
            raise InterruptedError(_("Arrêté"))
        emb = s["jetons"].run(None, entrees)[0]
        if i == 0:
            emb = np.concatenate((cond, emb), axis=1)
            passe = {n: np.zeros((1, TETES, 0, DIM_TETE), dtype=dt) for n in noms_kv}
            masque = np.ones((1, emb.shape[1]), dtype=np.int64)
        logits, *present = s["langage"].run(None, dict(inputs_embeds=emb.astype(np.float32), attention_mask=masque, **passe))
        dernier = _penaliser(produits, logits[:, -1, :])
        suivant = np.argmax(dernier, axis=-1, keepdims=True).astype(np.int64)
        produits = np.concatenate((produits, suivant), axis=-1)
        if int(suivant[0, 0]) == FIN_PAROLE:
            break
        entrees["input_ids"] = suivant
        entrees["position_ids"] = np.full((1, 1), i + 1, dtype=np.int64)
        masque = np.concatenate([masque, np.ones((1, 1), dtype=np.int64)], axis=1)
        passe = dict(zip(noms_kv, present))
        if progression and i % 5 == 0:
            progression(min(0.99, (i + 1) / maxi))
    j = produits[:, 1:]
    if j.shape[1] and int(j[0, -1]) == FIN_PAROLE:
        j = j[:, :-1]
    return j[(j < DEBUT_PAROLE)].reshape(1, -1)               # jamais un jeton spécial au décodeur


def decoder(s, jetons, emp):
    import numpy as np
    _cond, jt_ref, timbre, traits = emp
    tous = np.concatenate([jt_ref, jetons], axis=1).astype(np.int64)
    son = s["decodeur"].run(None, {"speech_tokens": tous, "speaker_embeddings": timbre, "speaker_features": traits})[0]
    # le décodeur ne rend que la suite (l'extrait sert de modèle, comme dans S3Gen d'origine) : vérifié par l'essai réel du
    # 13/11/2026, 60 jetons -> 2,44 s (2,40 attendus)
    return np.squeeze(son, axis=0)


def dire(texte, reference, sortie, langue="fr", expressivite=0.5, params=None, progression=None, arret=lambda: False,
         chemins=None, s=None):
    """Dit le texte avec la voix de l'extrait (tableau mono 24 kHz) ; écrit un WAV 24 kHz et renvoie (chemin, durée)."""
    import numpy as np
    morceaux = phrases(texte)
    if not morceaux:
        raise ErreurVoix(_("Ecrivez le texte à dire."))
    if progression:
        progression(0.01, _("Chargement du modèle de voix…"))
    s = s or sessions(params, chemins)
    emp = empreinte(s, reference)
    blanc = np.zeros(int(0.22 * TAUX), dtype=np.float32)
    sons, n = [], len(morceaux)
    for k, m in enumerate(morceaux):
        def prog(f, k=k):
            if progression:
                progression(0.03 + 0.92 * (k + f) / n, _("Voix : phrase {i} sur {n}", i=k + 1, n=n))
        ids = jetons_texte(s["tokenizer"], m, langue)
        j = parole(s, ids, emp, expressivite, jetons_attendus(m), prog, arret)
        if j.shape[1] == 0:
            continue
        if progression:                                   # la mise en son est l'étape la plus longue (≈ 4 s par seconde de voix)
            progression(0.03 + 0.92 * (k + 0.6) / n, _("Voix : phrase {i} sur {n}, mise en son…", i=k + 1, n=n))
        sons += [decoder(s, j, emp), blanc]
    if not sons:
        raise ErreurVoix(_("Le modèle n'a rien prononcé : reformulez le texte."))
    son = np.concatenate(sons[:-1]).astype(np.float32)
    # même niveau que la voix de l'extrait, pour que la suite ne saute pas à l'oreille
    cible, actuel = niveau(reference), niveau(son)
    if actuel > 1e-6:
        son = son * min(4.0, cible / actuel)
    pic = float(np.max(np.abs(son))) if son.size else 0.0
    if pic > 0.98:
        son = son * (0.98 / pic)
    ecrire(sortie, son)
    if progression:
        progression(1.0, _("Terminé"))
    return sortie, son.size / TAUX


def dossier_sorties():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "voix_continuees")
    os.makedirs(d, exist_ok=True)
    return d


def langue_defaut(params=None):
    """La langue de l'interface si le modèle la parle, sinon le français."""
    from .langue import LANGUE
    l = (LANGUE or "fr")[:2]
    return l if l in LANGUES_SIMPLES else "fr"


# ---------------------------------------------------------------- pose dans le film
def poser(projet, chemin, debut, fiche=None, sur_liaison=None):
    """Pose la voix fabriquée à `debut` : sur la piste Voix si elle est libre à cet endroit, sinon sur une piste de sons
    libre (ajoutée s'il le faut). Un seul Annuler. Renvoie le plan posé."""
    from . import moteur
    from .dialogues_separation import _libre
    fiche = fiche or moteur.sonder(chemin)
    duree = float(fiche.get("duree") or 0)
    if duree <= 0:
        raise ErreurVoix(_("La voix fabriquée est vide."))
    projet.marquer()
    m = projet.ajouter_media(chemin, fiche)
    m["nom"] = _("Voix continuée — {d}", d=os.path.splitext(os.path.basename(chemin))[0][-8:])
    a, b = float(debut), float(debut) + duree
    piste = next((x for x in ["voix"] + projet.pistes_audio() if _libre(projet, x, a, b)), None)
    if piste is None:
        piste = projet.ajouter_piste("audio")
    c = projet.ajouter_clip(m["id"], piste=piste, debut=a, src_debut=0.0, src_fin=duree)
    c["voix_ia"] = True                                   # fabriquée par IA : le montage le sait
    if sur_liaison:
        c["sur_liaison"] = sur_liaison
    projet.modifie = True
    return c


def extrait_par_defaut(clip, position=None):
    """(début dans la source, durée) : les dernières secondes de voix du plan avant la ligne rouge (12 s au plus), sinon la
    fin du plan : c'est la voix qui doit continuer."""
    v = float(clip.get("vitesse") or 1.0)
    s0, s1 = float(clip["src_debut"]), float(clip["src_fin"])
    fin = s1
    if position is not None and clip["debut"] < position < clip["debut"] + (s1 - s0) / v:
        fin = s0 + (position - clip["debut"]) * v
    if fin - s0 < REF_MIN + 0.5:
        fin = s1
    debut = max(s0, fin - 12.0)
    return round(debut, 2), round(fin - debut, 2)
