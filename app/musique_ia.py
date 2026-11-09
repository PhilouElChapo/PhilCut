"""Fabrique musique (0.9.37) : le cœur de la création musicale, sans dépendre du montage vidéo, pour PhilCut et
PhilMusic.

- Une **fiche musicale** (style, ambiance, tempo, tonalité, mesure, instruments, structure, voix, époque, durée,
  paroles) devient une **consigne solide** en anglais pour le moteur (ACE-Step, sur ce poste) ; l'IA peut l'améliorer
  (locale, rien ne sort ; ou cloud avec votre clef, coût annoncé).
- **S'inspirer d'un morceau** : analyse sur ce poste (tempo, tonalité, mesure, énergie, brillance, basses, percussions,
  déroulé ; et, si le moteur le permet, genre, instruments et voix décrits par « ace-understand »). Rien n'est envoyé ;
  seul le **style** est gardé (jamais la mélodie, les paroles ni le nom de l'artiste).
- **Partir d'un morceau** (le réorchestrer) et **voix de référence** : seulement pour un fichier libre de droits ou à
  vous, et une voix qui est la vôtre ou celle d'une personne d'accord ; déclaré et gardé à côté du fichier
  (« <fichier>.droits.json »). Jamais la voix d'un chanteur ou d'une personne connue : son style se décrit.
"""
import json
import os
import re
import subprocess
import tempfile

from .langue import _

# ------------------------------------------------------------------ styles
# (clef, nom, famille, consigne anglaise, tempo, tonalité, mesure, instruments proposés)
FAMILLES = {"pop": _("Pop, rock, électro"), "calme": _("Calme, ambiance"), "cinema": _("Cinéma"), "classique": _("Classique, opéra, sacré"),
            "jazz": _("Jazz, blues, swing"), "monde": _("Musiques du monde"), "retro": _("Rétro, époques"), "chanson": _("Chanson, voix")}
STYLES = [
    ("pop_aerienne", _("Pop aérienne"), "pop", "airy uplifting pop, bright synths, soft drums, positive, travel vlog", 112, "", "4/4", "synths, soft drums, bass"),
    ("rock", _("Rock dynamique"), "pop", "driving rock, electric guitars, powerful drums, adventure", 128, "E minor", "4/4", "electric guitars, bass, drums"),
    ("electro", _("Electro énergique"), "pop", "energetic electronic dance, punchy kick, synth bass, festival", 126, "", "4/4", "synth bass, kick, leads"),
    ("hiphop", _("Hip-hop"), "pop", "boom bap hip hop beat, dusty drums, deep bass, sampled keys", 90, "", "4/4", "drums, bass, keys"),
    ("funk", _("Funk"), "pop", "tight funk groove, slap bass, wah guitar, brass stabs", 108, "", "4/4", "slap bass, guitar, brass"),
    ("metal", _("Métal"), "pop", "heavy metal, distorted guitars, double kick drums, aggressive", 150, "E minor", "4/4", "distorted guitars, drums"),
    ("synthwave", _("Synthwave années 80"), "retro", "80s synthwave, analog synths, gated reverb drums, neon night drive", 100, "A minor", "4/4", "analog synths, drum machine"),
    ("lofi", _("Lo-fi calme"), "calme", "lofi hip hop, chill, mellow piano, vinyl crackle, relaxed", 80, "", "4/4", "piano, soft drums"),
    ("piano", _("Piano doux"), "calme", "gentle solo piano, emotional, calm, ambient", 72, "", "4/4", "piano"),
    ("ambient", _("Ambiance planante"), "calme", "ambient soundscape, pads, slow evolving, atmospheric", 70, "", "4/4", "pads, textures"),
    ("acoustique", _("Acoustique guitare"), "calme", "warm acoustic guitar, folk, light percussion, sunny", 100, "G major", "4/4", "acoustic guitar, percussion"),
    ("cinema", _("Cinématique épique"), "cinema", "epic cinematic orchestral, strings, big drums, inspiring, film trailer", 90, "D minor", "4/4",
     "strings, brass, taiko drums, choir"),
    ("suspense", _("Suspense"), "cinema", "dark suspense underscore, low strings, pulsing synth, tension", 85, "C minor", "4/4", "low strings, synth pulse"),
    ("aventure", _("Aventure"), "cinema", "adventurous orchestral score, heroic brass, soaring strings", 110, "D major", "4/4", "brass, strings, percussion"),
    ("symphonie", _("Symphonie (grand orchestre)"), "classique", "romantic era symphony, full symphony orchestra, lush strings, horns, "
     "woodwinds, timpani, dramatic dynamics, concert hall", 96, "C minor", "4/4", "strings, horns, woodwinds, timpani"),
    ("classique", _("Classique (musique de chambre)"), "classique", "classical chamber music, string quartet, elegant, refined, "
     "Classical period", 104, "G major", "4/4", "violins, viola, cello"),
    ("baroque", _("Baroque"), "classique", "baroque music, harpsichord, strings, counterpoint, ornamented, Baroque period", 100, "D major", "4/4",
     "harpsichord, strings, continuo"),
    ("opera", _("Opéra (air)"), "classique", "operatic aria, orchestra accompaniment, dramatic lyrical vocals, bel canto, opera house",
     72, "A minor", "4/4", "orchestra, voice"),
    ("piano_romantique", _("Piano romantique"), "classique", "romantic piano solo, expressive rubato, virtuosic, nocturne", 66, "C# minor", "4/4",
     "grand piano"),
    ("valse", _("Valse"), "classique", "Viennese waltz, orchestra, elegant ballroom", 168, "D major", "3/4", "strings, woodwinds"),
    ("sacre", _("Chœur sacré"), "classique", "sacred choral music, large mixed choir, cathedral reverb, solemn, requiem", 60, "D minor", "4/4",
     "choir, organ"),
    ("gregorien", _("Chant grégorien"), "classique", "gregorian chant, male monks choir in unison, monophonic plainchant, abbey reverb",
     60, "D dorian", "4/4", "male choir"),
    ("marche", _("Marche, fanfare"), "classique", "military march, brass band, snare drums, proud", 116, "B♭ major", "2/4", "brass, snare drums"),
    ("jazz", _("Jazz piano bar"), "jazz", "smooth jazz trio, piano, upright bass, brushed drums, late night bar", 92, "", "4/4",
     "piano, double bass, brushes"),
    ("swing", _("Swing big band"), "jazz", "1940s big band swing, brass section, walking bass, swing drums", 160, "", "4/4", "trumpets, saxophones, trombones"),
    ("blues", _("Blues"), "jazz", "slow electric blues, expressive guitar bends, shuffle", 70, "E major", "12/8", "electric guitar, harmonica"),
    ("bossa", _("Bossa nova"), "jazz", "bossa nova, nylon guitar, soft percussion, relaxed Brazilian", 128, "", "4/4", "nylon guitar, shaker"),
    ("flamenco", _("Flamenco"), "monde", "flamenco, Spanish guitar, palmas hand claps, passionate", 120, "A phrygian", "3/4", "Spanish guitar, claps"),
    ("celtique", _("Celtique"), "monde", "celtic folk, tin whistle, fiddle, bodhran, joyful", 112, "D major", "6/8", "fiddle, tin whistle, bodhran"),
    ("reggae", _("Reggae"), "monde", "roots reggae, offbeat guitar skank, deep bass, one drop drums", 76, "", "4/4", "guitar, bass, drums"),
    ("afrique", _("Afro"), "monde", "afrobeat, polyrhythmic percussion, highlife guitar, horns", 110, "", "4/4", "percussion, guitar, horns"),
    ("orient", _("Orientale"), "monde", "middle eastern music, oud, darbuka, qanun, maqam scales", 96, "D phrygian", "4/4", "oud, darbuka"),
    ("tango", _("Tango"), "monde", "Argentine tango, bandoneon, violin, piano, dramatic", 116, "A minor", "4/4", "bandoneon, violin, piano"),
    ("annees30", _("Années 30 (swing, musette)"), "retro", "1930s vintage dance band, old gramophone sound, clarinet, muted trumpet",
     132, "", "4/4", "clarinet, trumpet, banjo"),
    ("musette", _("Musette (accordéon)"), "retro", "French bal musette, accordion waltz, Parisian guinguette", 160, "", "3/4", "accordion"),
    ("rocknroll", _("Rock'n'roll années 50"), "retro", "1950s rock and roll, slapback echo, upright bass, boogie piano", 168, "", "4/4",
     "electric guitar, upright bass, piano"),
    ("disco", _("Disco années 70"), "retro", "1970s disco, four on the floor, strings, funky bass", 120, "", "4/4", "strings, bass, guitar"),
    ("chiptune", _("Chiptune 8 bits"), "retro", "8-bit chiptune, video game, square waves, arpeggios", 140, "", "4/4", "square waves"),
    ("chanson", _("Chanson française"), "chanson", "French chanson, accordion, piano, intimate storytelling", 100, "", "4/4", "accordion, piano"),
    ("ballade", _("Ballade"), "chanson", "heartfelt pop ballad, piano and strings, emotional build", 72, "", "4/4", "piano, strings"),
    ("country", _("Country"), "chanson", "country song, acoustic guitar, pedal steel, fiddle", 104, "G major", "4/4", "acoustic guitar, pedal steel"),
    ("gospel", _("Gospel"), "chanson", "gospel, choir, Hammond organ, clapping, uplifting", 96, "", "4/4", "choir, organ"),
]
_STYLE = {s[0]: s for s in STYLES}

AMBIANCES = [("", _("Ambiance au choix")), ("joyeuse", _("Joyeuse")), ("energique", _("Energique")), ("calme", _("Calme")),
             ("romantique", _("Romantique")), ("melancolique", _("Mélancolique")), ("epique", _("Epique")), ("tendue", _("Tendue")),
             ("mysterieuse", _("Mystérieuse")), ("solennelle", _("Solennelle")), ("festive", _("Festive")), ("nostalgique", _("Nostalgique"))]
AMBIANCES_EN = {"joyeuse": "joyful, happy", "energique": "energetic", "calme": "calm, peaceful", "romantique": "romantic, tender",
                "melancolique": "melancholic, bittersweet", "epique": "epic, triumphant", "tendue": "tense, suspenseful",
                "mysterieuse": "mysterious", "solennelle": "solemn, majestic", "festive": "festive, celebratory", "nostalgique": "nostalgic"}
STRUCTURES = [("", _("Déroulé au choix du moteur")), ("chanson", _("Intro, couplet, refrain, couplet, refrain, final")),
              ("montee", _("Montée progressive jusqu'au final")), ("calme_final", _("Calme puis grand final")),
              ("fond", _("Régulier (fond sous une voix)")), ("court", _("Court et percutant (jingle)"))]
STRUCTURES_EN = {"chanson": "song structure: intro, verse, chorus, verse, chorus, outro", "montee": "gradual build-up to a powerful climax",
                 "calme_final": "quiet beginning, grand finale", "fond": "steady and even, background music under narration",
                 "court": "short punchy jingle"}
TONALITES = ["", "C major", "G major", "D major", "A major", "E major", "F major", "B♭ major", "E♭ major",
             "A minor", "E minor", "B minor", "D minor", "G minor", "C minor", "F minor", "C# minor", "D dorian", "A phrygian"]
MESURES = ["", "4/4", "3/4", "6/8", "2/4", "12/8"]
VOIX_EN_PLUS = {"tenor": (_("Ténor lyrique"), "operatic tenor male vocals, bel canto"),
                "mezzo": (_("Mezzo-soprano"), "mezzo-soprano female vocals, warm classical"),
                "gregorien": (_("Chœur de moines (grégorien)"), "male monks choir singing in unison")}


def voix_disponibles():
    from . import paroles as PA
    d = dict(PA.VOIX)
    d.update(VOIX_EN_PLUS)
    return d


def fiche_vide():
    return {"style": "pop_aerienne", "ambiance": "", "phrase": "", "tempo": 0, "tonalite": "", "mesure": "", "instruments": "",
            "structure": "", "voix": "auto", "epoque": "", "duree": 60.0, "instrumental": True, "paroles": "", "langue": "fr",
            "inspiration": None, "consigne_ia": "", "utiliser_ia": False, "source": None, "voix_reference": None}


# ------------------------------------------------------------------ consigne
def _propre(t):
    t = re.sub(r"\s+", " ", t or "").strip(" ,;")
    return re.sub(r"(,\s*){2,}", ", ", t)


def consigne(fiche, params=None, traduire=None):
    """La consigne pour le moteur : {"caption", "bpm", "keyscale", "timesignature", "noms": [styles transposés], "inconnus": [...]}.
    traduire(texte) -> anglais (None : le texte est gardé tel quel, pour l'aperçu sans réseau)."""
    f = dict(fiche_vide(), **(fiche or {}))
    st = _STYLE.get(f["style"]) or _STYLE["pop_aerienne"]
    parties = []
    from . import styles_ia as S
    tr = S.transposer(f.get("phrase") or "", "musique", params)
    if f.get("utiliser_ia") and f.get("consigne_ia"):
        parties.append(f["consigne_ia"])
    else:
        parties.append(st[3])
        if f.get("ambiance"):
            parties.append(AMBIANCES_EN.get(f["ambiance"], f["ambiance"]))
        if f.get("structure"):
            parties.append(STRUCTURES_EN.get(f["structure"], f["structure"]))
        insp = f.get("inspiration") or {}
        if insp.get("caption_en"):
            parties.append(insp["caption_en"])
    reste = re.sub(r"(?i)\b(chant[ée]e?s?|jou[ée]e?s?|interpr[ée]t[ée]e?s?|sung|played|performed)\b", "", tr["texte"] or "")
    libres = [x for x in (reste, f.get("instruments"), f.get("epoque")) if len(re.sub(r"[\W_]+", "", x or "")) > 1]
    for x in libres:
        parties.append(traduire(x) if traduire else x)
    if tr["ajout"]:
        parties.append(tr["ajout"])
    if not f.get("instrumental"):
        v = voix_disponibles().get(f.get("voix") or "auto", ("", ""))[1]
        if v:
            parties.append(v)
    else:
        parties.append("instrumental")
    insp = f.get("inspiration") or {}
    bpm = int(f.get("tempo") or insp.get("bpm") or st[4] or 0)
    key = f.get("tonalite") or insp.get("tonalite") or st[5] or ""
    mesure = f.get("mesure") or insp.get("mesure") or st[6] or "4/4"
    return {"caption": _propre(", ".join(p for p in parties if p)), "bpm": bpm, "keyscale": key.replace("♭", "b"),
            "timesignature": mesure.split("/")[0], "mesure": mesure, "styles": tr["styles"], "inconnus": tr["inconnus"]}


# ------------------------------------------------------------------ amélioration par l'IA
CONSIGNE_AMELIORER = """You are a music producer writing the prompt for an AI music generator (ACE-Step) that only understands English
and does not know any artist, band, song or composer names.
Improve this music brief into ONE rich prompt of 40 to 90 words: genre and sub-genre, era, instrumentation with the role of each
instrument, rhythm and groove, harmony and mode, mood and its evolution, structure, production and mix, vocal type if any.
Keep every intention of the user. Never write a name of a person, band, song, work or brand.
Answer only with JSON: {{"caption": "...", "bpm": number, "keyscale": "C major", "time_signature": "4/4"}}
Brief: {brief}"""


def ameliorer(fiche, params=None, niveau="locale", traduire=None):
    """L'IA réécrit la consigne en un prompt de producteur ; renvoie {"caption", "bpm", "keyscale", "mesure"} (sans aucun nom)."""
    c = consigne(dict(fiche, utiliser_ia=False), params, traduire)
    brief = json.dumps({"prompt": c["caption"], "bpm": c["bpm"], "key": c["keyscale"], "time_signature": c["mesure"],
                        "duration_seconds": (fiche or {}).get("duree", 60)}, ensure_ascii=False)
    texte = CONSIGNE_AMELIORER.format(brief=brief)
    systeme = "You write precise prompts for music generation, without naming or copying anyone."
    if niveau == "locale":
        from . import ia_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise RuntimeError(_("Aucun modèle d'IA locale pour écrire : installez « Vision et texte » dans Préférences › IA locale, "
                                 "ou choisissez l'IA cloud."))
        r = ia_locale.generer(modele, texte, [], systeme=systeme, params=params)
    else:
        from . import ia
        r = ia.demander(params or {}, systeme, texte, max_jetons=700)
    return lire_amelioration(r if isinstance(r, str) else str(r), [n for n, _d in c["styles"]] + c["inconnus"])


def lire_amelioration(r, noms=()):
    m = re.search(r"\{.*\}", r or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    cap = d.get("caption") if isinstance(d.get("caption"), str) else (r or "").strip()
    for n in noms:
        for mot in str(n).split():
            if len(mot) > 2:
                cap = re.sub(r"\b" + re.escape(mot) + r"\b", "", cap, flags=re.I)
    try:
        bpm = int(float(d.get("bpm") or 0))
    except (TypeError, ValueError):
        bpm = 0
    return {"caption": _propre(cap)[:900], "bpm": bpm if 40 <= bpm <= 220 else 0, "keyscale": str(d.get("keyscale") or "")[:20],
            "mesure": str(d.get("time_signature") or "")[:5]}


# ------------------------------------------------------------------ droits d'un fichier (libre, à moi, voix d'accord)
def chemin_droits(fichier):
    return f"{fichier}.droits.json"


def droits(fichier):
    try:
        with open(chemin_droits(fichier), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def declarer(fichier, **infos):
    """Garde à côté du fichier ce que l'utilisateur a déclaré (libre de droits, à lui, voix d'une personne d'accord)."""
    import time
    d = droits(fichier)
    d.update(infos)
    d["declare_le"] = time.strftime("%Y-%m-%d %H:%M")
    try:
        with open(chemin_droits(fichier), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return d


def peut_partir_de(fichier):
    d = droits(fichier)
    return bool(d.get("libre") or d.get("a_moi"))


# ------------------------------------------------------------------ analyse d'un morceau (sur ce poste)
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_MAJ = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MIN = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def _lire_audio(chemin, sr=22050, max_s=360):
    import numpy as np
    from . import moteur
    cmd = [moteur.ffmpeg(), "-v", "error", "-i", chemin, "-t", str(max_s), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    try:
        from .packs_ia import _options_processus
        opts = {k: v for k, v in _options_processus().items() if k != "preexec_fn"}
    except Exception:      # noqa: BLE001
        opts = {}
    r = subprocess.run(cmd, capture_output=True, timeout=300, **opts)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(_("Ce fichier ne se lit pas comme un son : {e}", e=r.stderr.decode("utf-8", "replace")[-200:]))
    return np.frombuffer(r.stdout, np.float32).copy(), sr


def mesurer(x, sr):
    """Mesures objectives d'un son : tempo, tonalité, mesure, énergie, brillance, basses, percussions, déroulé."""
    import numpy as np
    n_fft, hop = 2048, 512
    if len(x) < n_fft * 4:
        raise RuntimeError(_("Morceau trop court pour être analysé."))
    fen = np.hanning(n_fft).astype(np.float32)
    nb = 1 + (len(x) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(nb)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * fen, axis=1)).astype(np.float32)          # trames × fréquences
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    # --- tempo : flux spectral (attaques), autocorrélation entre 50 et 210 battements par minute
    logS = np.log1p(S * 10)
    flux = np.maximum(0, np.diff(logS, axis=0)).sum(axis=1)
    flux = flux - np.convolve(flux, np.ones(16) / 16, mode="same")
    flux = np.maximum(flux, 0)
    ips = sr / hop
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    lags = np.arange(len(ac))
    bpm_l = 60.0 * ips / np.maximum(lags, 1)
    ok = (bpm_l >= 50) & (bpm_l <= 210)
    poids = np.exp(-0.5 * (np.log2(np.maximum(bpm_l, 1) / 115.0) / 0.9) ** 2)        # préférence douce autour de 115
    score = np.where(ok, ac * poids, 0)
    lag = int(np.argmax(score)) or 1
    if 2 < lag < len(ac) - 2:                                            # précision au-delà de la trame
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]
        d = (a - c) / (2 * (a - 2 * b + c)) if (a - 2 * b + c) else 0
        lag_f = lag + max(-0.5, min(0.5, d))
    else:
        lag_f = lag
    bpm = 60.0 * ips / lag_f
    # mesure : 3 ou 4 temps, d'après les temps forts. L'énergie des graves de chaque battement, mesurée à l'endroit
    # des attaques, est regroupée par 3 et par 4 : le regroupement qui fait ressortir un temps fort l'emporte.
    grave = (S[:, freqs < 250] ** 2).sum(axis=1)
    seuil = np.percentile(flux, 90)
    pics = [i for i in range(1, len(flux) - 1) if flux[i] >= seuil and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    mesure = "4/4"
    if len(pics) >= 12:
        t0 = pics[0]
        forces = {}
        for i in pics:
            k = int(round((i - t0) / lag_f))
            forces[k] = max(forces.get(k, 0.0), float(grave[min(len(grave) - 1, i + 1)]))
        if len(forces) >= 12:
            ks = np.array(sorted(forces))
            vs = np.array([forces[k] for k in ks])

            def contraste(n):
                g = [vs[ks % n == o].mean() for o in range(n) if (ks % n == o).any()]
                return float(max(g) / (np.mean(g) + 1e-9)) if len(g) == n else 0.0
            if contraste(3) > 1.25 and contraste(3) > 1.05 * contraste(4):
                mesure = "3/4"
    regularite = float(score[lag] / (ac[0] + 1e-9))
    # --- tonalité : chroma (60 Hz à 5 kHz), profils de Krumhansl
    sel = (freqs >= 60) & (freqs <= 5000)
    midi = 69 + 12 * np.log2(freqs[sel] / 440.0)
    classes = np.mod(np.round(midi).astype(int), 12)
    energie_bins = (S[:, sel] ** 2).mean(axis=0)
    chroma = np.bincount(classes, weights=energie_bins, minlength=12)
    chroma = chroma / (chroma.max() + 1e-12)
    meilleur = (-2.0, 0, "major")
    for k in range(12):
        for mode, prof in (("major", _MAJ), ("minor", _MIN)):
            r = float(np.corrcoef(chroma, np.roll(prof, k))[0, 1])
            if r > meilleur[0]:
                meilleur = (r, k, mode)
    tonalite = f"{NOTES[meilleur[1]]} {meilleur[2]}"
    # --- timbre, énergie, déroulé
    p = (S ** 2).sum(axis=1) + 1e-12
    centroide = float(((S ** 2) @ freqs / p).mean())
    basses = float((S[:, freqs < 150] ** 2).sum() / p.sum())
    rms = np.sqrt((x[: len(x) // sr * sr].reshape(-1, sr) ** 2).mean(axis=1)) if len(x) >= sr else np.array([np.sqrt((x ** 2).mean())])
    db = 20 * np.log10(rms + 1e-6)
    percussif = float(np.mean(flux) / (np.mean(logS.sum(axis=1)) + 1e-9) * 100)
    morceaux = np.array_split(db, min(6, len(db))) if len(db) >= 6 else [db]
    deroule = [round(float(m.mean()), 1) for m in morceaux]
    return {"duree": round(len(x) / sr, 1), "bpm": int(round(bpm)), "regularite": round(regularite, 3), "mesure": mesure,
            "tonalite": tonalite, "certitude_tonalite": round(meilleur[0], 2), "brillance": int(centroide), "basses": round(basses, 3),
            "percussif": round(percussif, 2), "volume_db": round(float(np.median(db)), 1), "dynamique_db": round(float(np.percentile(db, 95) - np.percentile(db, 10)), 1),
            "deroule_db": deroule}


NOTES_FR = {"C": "do", "D": "ré", "E": "mi", "F": "fa", "G": "sol", "A": "la", "B": "si"}


def tonalite_fr(t):
    """« A minor » → « la mineur », « C# minor » → « do dièse mineur », « B♭ major » → « si bémol majeur »."""
    m = re.match(r"^\s*([A-G])\s*([#♯b♭]?)\s*(\w*)", t or "")
    if not m:
        return t or ""
    from . import langue as L
    lg = (L.LANGUE or "fr")[:2]
    base = NOTES_FR[m.group(1)] if lg in ("fr", "es", "it") else ("H" if lg == "de" and m.group(1) == "B" else m.group(1))
    if lg == "es":
        base = {"ré": "re"}.get(base, base)
    note = base + {"#": _(" dièse"), "♯": _(" dièse"), "b": _(" bémol"), "♭": _(" bémol")}.get(m.group(2), "")
    mode = {"major": _("majeur"), "minor": _("mineur"), "dorian": _("dorien"), "phrygian": _("phrygien")}.get(m.group(3).lower(), m.group(3))
    return f"{note} {mode}".strip()


def decrire(m):
    """Mesures → description anglaise (pour le moteur) et résumé français (pour l'utilisateur)."""
    en, fr = [], []
    tempo = m["bpm"]
    en.append({True: "slow tempo", False: "moderate tempo"}[tempo < 80] if tempo < 110 else "fast tempo" if tempo > 135 else "upbeat tempo")
    fr.append(_("tempo {b} battements par minute", b=tempo))
    fr.append(_("tonalité {t}", t=tonalite_fr(m["tonalite"])))
    fr.append(_("mesure {m}", m=m["mesure"]))
    if m["mesure"] == "3/4":
        en.append("waltz feel in 3/4")
    en.append("minor key, emotional" if "minor" in m["tonalite"] else "major key, bright harmony")
    if m["brillance"] < 1400:
        en.append("warm dark timbre"); fr.append(_("son chaud et sombre"))
    elif m["brillance"] > 2800:
        en.append("bright crisp sound"); fr.append(_("son brillant"))
    if m["basses"] > 0.35:
        en.append("heavy deep bass"); fr.append(_("basses très présentes"))
    if m["percussif"] > 1.8 and m["regularite"] > 0.25:
        en.append("strong steady beat, prominent drums"); fr.append(_("rythme marqué, percussions présentes"))
    elif m["percussif"] < 0.8:
        en.append("no drums, flowing, rubato"); fr.append(_("peu ou pas de percussions"))
    d = m["deroule_db"]
    if len(d) >= 3:
        if d[-1] - d[0] > 6 and max(d) == d[-1] or d[-2] - d[0] > 6:
            en.append("gradual build-up to a powerful climax"); fr.append(_("monte en puissance"))
        elif d[0] - d[-1] > 6:
            en.append("starts strong, fades into calm"); fr.append(_("finit plus calme"))
        elif max(d) - min(d) < 3:
            en.append("steady even dynamics"); fr.append(_("régulier du début à la fin"))
    if m["dynamique_db"] > 18:
        en.append("wide dynamic range, orchestral contrasts"); fr.append(_("grands contrastes de volume"))
    return ", ".join(en), " ; ".join(fr)


def _ace_understand(chemin, params=None, progression=None, arret=lambda: False):
    """Genre, instruments, voix décrits par ace-understand (moteur de musique de ce poste), si sa version le permet."""
    from . import creatif as C, packs_ia as P
    try:
        cle, m, e = C.modele_pour("musique", params)
    except Exception:      # noqa: BLE001
        return None
    for genre in ("musique_gpu", "musique"):
        exe = os.path.join(P.dossier_moteur(genre), P._exe("ace-understand"))
        if os.path.exists(exe):
            break
    else:
        return None
    sortie = os.path.join(tempfile.mkdtemp(prefix="philcut-comprendre-"), "compris.json")
    roles = (e or {}).get("roles") or {}
    req = os.path.join(os.path.dirname(sortie), "demande.json")
    with open(req, "w", encoding="utf-8") as f:
        json.dump({"lm_model": roles.get("lm", ""), "synth_model": roles.get("dit", "")}, f)
    C._lancer(genre, ["--models", P.dossier_modele(cle), "--src-audio", chemin, "--request", req, "-o", sortie], progression, arret,
              journal="musique_comprendre", exe=exe, etape=_("Le moteur de musique écoute le morceau (genre, instruments, voix)"))
    try:
        with open(sortie, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def analyser(chemin, params=None, progression=None, arret=lambda: False, ecouter=True):
    """Analyse sur ce poste ; rien n'est envoyé. Renvoie {"mesures", "caption_en", "resume", "bpm", "tonalite", "mesure",
    "compris": bool}. Les paroles et les noms éventuels ne sont jamais gardés : seulement le style."""
    if progression:
        progression(0.05, _("Lecture du morceau…"))
    x, sr = _lire_audio(chemin)
    if arret():
        raise InterruptedError()
    if progression:
        progression(0.2, _("Mesure du tempo, de la tonalité et du déroulé…"))
    m = mesurer(x, sr)
    en, fr = decrire(m)
    res = {"mesures": m, "caption_en": en, "resume": fr, "bpm": m["bpm"], "tonalite": m["tonalite"], "mesure": m["mesure"], "compris": False,
           "fichier": os.path.basename(chemin)}
    if ecouter:
        try:
            u = _ace_understand(chemin, params, (lambda f, t="": progression(0.3 + 0.65 * f, t)) if progression else None, arret)
        except InterruptedError:
            raise
        except Exception:      # noqa: BLE001 : l'écoute fine est un plus, jamais un blocage
            u = None
        if u:
            cap = str(u.get("caption") or "")
            cap = re.sub(r"\b(by|from|like|inspired by)\s+[A-Z][\w'\-]+(\s+[A-Z][\w'\-]+)*", "", cap)      # pas de nom
            if cap:
                res["caption_en"] = _propre(f"{cap}, {en}")
                res["compris"] = True
            try:
                b = int(float(u.get("bpm") or 0))
                if 40 <= b <= 220:
                    res["bpm"] = b
            except (TypeError, ValueError):
                pass
            if u.get("keyscale"):
                res["tonalite"] = str(u["keyscale"])[:20]
    if progression:
        progression(1.0, _("Analyse terminée."))
    return res


# ------------------------------------------------------------------ création
def creer(fiche, sortie, params=None, progression=None, arret=lambda: False, traduire=None):
    """Fabrique le morceau (MP3) d'après la fiche ; renvoie (chemin, consigne envoyée)."""
    from . import creatif as C
    f = dict(fiche_vide(), **(fiche or {}))
    c = consigne(f, params, traduire)
    options = {"keyscale": c["keyscale"], "timesignature": c["timesignature"]}
    src = f.get("source") or {}
    if src.get("chemin"):
        if not peut_partir_de(src["chemin"]):
            raise RuntimeError(_("Ce morceau n'est pas déclaré libre de droits ou à vous : PhilCut peut seulement s'inspirer de son style."))
        options.update(source=src["chemin"], force_source=float(src.get("force", 0.5)), fidele=bool(src.get("fidele")))
    ref = f.get("voix_reference") or {}
    if ref.get("chemin"):
        d = droits(ref["chemin"])
        if not (d.get("voix_a_moi") or d.get("voix_accord")):
            raise RuntimeError(_("La voix de référence doit être la vôtre ou celle d'une personne qui a donné son accord (à déclarer)."))
        options["reference"] = ref["chemin"]
    r = C.musique(c["caption"], sortie, float(f["duree"]), params, bool(f["instrumental"]), f.get("paroles") or "", langue=f.get("langue") or "fr",
                  bpm=c["bpm"], progression=progression, arret=arret, voix="", options=options)
    return r, c


def recette(fiche, c):
    """Ce qui est gardé à côté du morceau (« .ia.json ») pour le refaire ou le modifier, ici ou sur un autre appareil."""
    f = dict(fiche)
    insp = f.get("inspiration") or {}
    if insp:                                                 # le style du morceau d'inspiration, jamais le morceau
        f["inspiration"] = {k: insp[k] for k in ("caption_en", "resume", "bpm", "tonalite", "mesure", "fichier") if k in insp}
    r = {"famille": "musique", "intention": "musique", "fiche": f, "anglais": c.get("caption", ""),
         "prompt": f.get("phrase", ""), "duree": f.get("duree"), "instrumental": f.get("instrumental"), "paroles": f.get("paroles", ""),
         "voix": f.get("voix"), "langue": f.get("langue")}
    from .recettes_ia import empreinte
    import time
    r.update(empreinte=empreinte(r), moteur="locale:ace-step", date=time.strftime("%Y-%m-%d %H:%M"))
    return r
