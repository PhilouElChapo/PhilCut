"""Clip de groupe déduit d'une chanson (0.9.66). PhilCut écoute le morceau (temps, mesures, parties, énergie, voix), en
déduit un groupe inventé (qui chante, qui joue quoi) et un découpage plan par plan calé sur les mesures, que l'on corrige
avant de rien payer ; puis il fait fabriquer les plans par le cloud (prix total annoncé), cale les lèvres du chanteur sur
la voix séparée et monte le tout sous la chanson, chaque coupe sur un début de mesure.

Lieu : concert sur scène, ou clip tourné ailleurs ; rendu : réaliste ou dessin animé. Un refrain qui revient peut
reprendre les plans du premier (bien moins cher). Les doigts ne jouent pas les vraies notes : le découpage préfère les
plans où cela ne se juge pas (larges, contre-jour, ralentis, visages, public). Jamais un vrai groupe ni une personnalité :
des musiciens inventés, sans logo ni nom de marque."""
import json, math, os, time

from .langue import _

VERSION = 1
LIEUX = {"concert": _("Concert sur scène"), "ailleurs": _("Clip tourné ailleurs")}
PARTIES = {"intro": _("Intro"), "couplet": _("Couplet"), "montee": _("Montée"), "refrain": _("Refrain"), "solo": _("Solo, instrumental"),
           "fin": _("Fin")}
ROLES = {"chant": _("Chant"), "guitare": _("Guitare"), "basse": _("Basse"), "batterie": _("Batterie"), "claviers": _("Claviers"),
         "machines": _("Machines, DJ"), "cordes": _("Cordes"), "cuivres": _("Cuivres, saxophone")}
ROLES_EN = {"chant": "lead singer at the microphone", "guitare": "guitarist playing an electric guitar", "basse": "bass player",
            "batterie": "drummer behind a drum kit", "claviers": "keyboard player", "machines": "DJ at the decks and synthesizers",
            "cordes": "violinist", "cuivres": "saxophone player"}
# looks variés pour inventer les musiciens (modifiables ensuite)
LOOKS = [_("la trentaine, cheveux courts noirs, veste en cuir noire"), _("cheveux longs bouclés roux, chemise à fleurs ouverte"),
         _("crâne rasé, barbe courte, débardeur gris, tatouages sur les bras"), _("cheveux blonds au carré, pull rayé, lunettes rondes"),
         _("dreadlocks attachées, t-shirt blanc, chaîne argentée"), _("cheveux bruns mi-longs, veste en jean, bandana rouge"),
         _("cheveux gris courts, costume sombre sans cravate")]


def _net(t):
    import unicodedata
    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()


# ------------------------------------------------------------------ écoute de la chanson
def _chroma_par_temps(x, sr, bornes):
    """Pour chaque intervalle [bornes[i], bornes[i+1]] : (niveau dB, brillance, chroma 12 normalisé)."""
    import numpy as np
    n, pas = 4096, 2048
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    nb = 1 + (len(x) - n) // pas
    idx = np.arange(n)[None, :] + pas * np.arange(nb)[:, None]
    S = np.abs(np.fft.rfft(x[idx] * np.hanning(n).astype(np.float32), axis=1))
    f = np.fft.rfftfreq(n, 1.0 / sr)
    ok = (f > 55) & (f < 5000)
    pc = (np.round(12 * np.log2(f[ok] / 440.0)).astype(int) + 9) % 12
    M = np.zeros((ok.sum(), 12), np.float32)
    M[np.arange(ok.sum()), pc] = 1
    chroma = (S[:, ok] ** 2) @ M
    energie = (S ** 2).sum(axis=1) + 1e-12
    brill = (S ** 2) @ f / energie
    t = (np.arange(nb) * pas + n / 2) / sr
    out = []
    for a, b in zip(bornes[:-1], bornes[1:]):
        sel = (t >= a) & (t < b)
        if not sel.any():
            sel = np.argmin(abs(t - a)) == np.arange(nb)
        c = chroma[sel].mean(axis=0)
        out.append((float(10 * np.log10(energie[sel].mean())), float(brill[sel].mean()), c / (np.linalg.norm(c) + 1e-9)))
    return out


def _niveaux(x, sr, bornes):
    import numpy as np
    out = []
    for a, b in zip(bornes[:-1], bornes[1:]):
        s = x[int(a * sr):max(int(a * sr) + 1, int(b * sr))]
        out.append(float(np.sqrt((s ** 2).mean())) if len(s) else 0.0)
    return out


def mesures_du_morceau(duree, temps, forts):
    """Débuts de mesure (secondes) qui couvrent tout le morceau ; grille de 2 s si le rythme n'est pas net."""
    if len(forts) >= 4:
        mes = (forts[-1] - forts[0]) / max(1, len(forts) - 1)
        b = [0.0] + [t for t in forts if t > 0.5 * mes]
        if duree - b[-1] > 0.3:
            b.append(duree)
        else:
            b[-1] = duree
        return b
    pas = 2.0
    return [min(duree, i * pas) for i in range(int(math.ceil(duree / pas)) + 1)]


def sections(x, sr, mesures, voix=None):
    """Parties du morceau : phrases de 4 mesures comparées (harmonie, timbre, niveau) ; une phrase qui ressemble à une
    précédente en reprend l'étiquette ; les plus fortes qui reviennent sont le refrain."""
    import numpy as np
    phr = mesures[::4]
    if phr[-1] < mesures[-1]:
        if mesures[-1] - phr[-1] < 2 * (mesures[1] - mesures[0]) and len(phr) > 1:
            phr[-1] = mesures[-1]
        else:
            phr.append(mesures[-1])
    feats = _chroma_par_temps(x, sr, phr)
    db = np.array([f[0] for f in feats])
    lo, hi = np.percentile(db, 10), np.percentile(db, 95)
    en = np.clip((db - lo) / max(1e-6, hi - lo), 0, 1)
    vrat = None
    if voix is not None:
        nv, nm = _niveaux(voix, sr, phr), _niveaux(x, sr, phr)
        vrat = [v / (m + 1e-9) for v, m in zip(nv, nm)]
    etiq, protos = [], []
    for i, (d, b, c) in enumerate(feats):
        lab = None
        for k, (pc, pd, pb) in enumerate(protos):
            if float(c @ pc) > 0.92 and abs(d - pd) < 5 and abs(b - pb) / max(pb, 1) < 0.35:
                lab = k
                break
        if lab is None:
            protos.append((c, d, b))
            lab = len(protos) - 1
        etiq.append(lab)
    # regroupement des phrases voisines de même étiquette
    secs = []
    for i, lab in enumerate(etiq):
        if secs and secs[-1]["groupe"] == lab:
            secs[-1]["fin"] = phr[i + 1]
            secs[-1]["_i"].append(i)
        else:
            secs.append({"debut": phr[i], "fin": phr[i + 1], "groupe": lab, "_i": [i]})
    for s in secs:
        s["_phrase"] = (s["fin"] - s["debut"]) / max(1, len(s["_i"]))
        s["energie"] = round(float(np.mean([en[i] for i in s["_i"]])), 2)
        s["voix"] = round(float(np.mean([vrat[i] for i in s["_i"]])), 2) if vrat else None
        s["montee"] = bool(len(s["_i"]) and en[s["_i"][-1]] - en[s["_i"][0]] > 0.25)
    # noms
    compte = {}
    for s in secs:
        compte[s["groupe"]] = compte.get(s["groupe"], 0) + 1
    repetes = [g for g, n in compte.items() if n >= 2]
    refrain = max(repetes, key=lambda g: np.mean([s["energie"] for s in secs if s["groupe"] == g]), default=None)
    if refrain is None and secs:
        refrain = max(secs, key=lambda s: s["energie"])["groupe"]
    for k, s in enumerate(secs):
        if s["groupe"] == refrain and s["energie"] >= 0.45:
            s["type"] = "refrain"
        elif k == 0 and s["energie"] < 0.5:
            s["type"] = "intro"
        elif k == len(secs) - 1 and s["energie"] < 0.55:
            s["type"] = "fin"
        elif s["voix"] is not None and s["voix"] < 0.12 and s["energie"] >= 0.35:
            s["type"] = "solo"
        elif k + 1 < len(secs) and secs[k + 1]["groupe"] == refrain and secs[k + 1]["energie"] >= 0.45 and \
                (s["montee"] or (s["fin"] - s["debut"] <= s["_phrase"] * 1.05 and s["energie"] < secs[k + 1]["energie"])):
            s["type"] = "montee"
        else:
            s["type"] = "couplet"
        s.pop("_i", None)
        s.pop("_phrase", None)
        s["debut"], s["fin"] = round(s["debut"], 3), round(s["fin"], 3)
    return secs


def analyser(chemin, params=None, separer=True, progression=None, arret=lambda: False):
    """Ecoute la chanson sur ce poste (rien n'est envoyé) : tempo, mesures, parties, énergie, voix séparée et décrite."""
    from . import musique_ia as MI, rythme
    av = lambda f, t: progression and progression(f, t)
    av(0.02, _("Ecoute du tempo et des mesures…"))
    ry = rythme.analyser(chemin)
    x, sr = MI._lire_audio(chemin, sr=22050, max_s=900)
    if arret():
        raise InterruptedError()
    duree = round(len(x) / sr, 3)
    me = MI.mesurer(x, sr) if hasattr(MI, "mesurer") else {}
    voix_chemin, voix_x, voix_desc = None, None, None
    from . import separation as S
    if separer and S.manquant(params) is None:
        av(0.1, _("Séparation de la voix (pour savoir quand on chante, et pour les lèvres)…"))
        r = S.separer(chemin, os.path.join(S.dossier_sorties(), "clip_groupe"), 0.0, duree, params,
                      progression=lambda f, t="": av(0.1 + 0.75 * f, _("Séparation de la voix")), arret=arret)
        voix_chemin = r["voix"]
        voix_x, _sr = MI._lire_audio(voix_chemin, sr=sr, max_s=900)
        try:
            voix_desc = MI.decrire_voix_mesures(MI.mesurer_voix(*MI._lire_audio(voix_chemin, sr=16000, max_s=120)))
        except Exception:      # noqa: BLE001 : morceau sans chant
            voix_desc = None
    av(0.9, _("Découpage en parties…"))
    mes = mesures_du_morceau(duree, ry.get("temps") or [], ry.get("forts") or [])
    secs = sections(x, sr, mes, voix_x)
    en, fr = (MI.decrire(me) if me else ("", ""))
    fr = " ; ".join(x for x in fr.split(" ; ") if not x.startswith(_("tempo {b} battements par minute", b="").split("{")[0].strip()[:5]))
    chante = bool(voix_x is not None and any((s["voix"] or 0) > 0.2 for s in secs))
    av(1.0, _("Morceau écouté."))
    return {"duree": duree, "bpm": ry.get("bpm") or me.get("bpm") or 0, "mesures": mes, "sections": secs, "caption_en": en,
            "resume": fr, "voix": voix_chemin, "chante": chante, "voix_en": voix_desc[0] if voix_desc else "",
            "voix_fr": voix_desc[1] if voix_desc else "", "basses": me.get("basses", 0), "percussif": me.get("percussif", 0),
            "brillance": me.get("brillance", 0)}


# ------------------------------------------------------------------ le groupe
def _roles_depuis_texte(t):
    t = _net(t)
    r = []
    for mots, role in ((("guitar", "guitare"), "guitare"), (("bass", "basse", "slap"), "basse"),
                       (("drum", "batter", "kick", "percussion"), "batterie"), (("piano", "keys", "organ", "clavier", "rhodes"), "claviers"),
                       (("synth", "electro", "dj", "machine"), "machines"), (("violin", "string", "cello", "violon", "cordes"), "cordes"),
                       (("brass", "sax", "trumpet", "cuivre", "trompette"), "cuivres")):
        if any(m in t for m in mots) and role not in r:
            r.append(role)
    return r


def groupe_propose(analyse, fiche=None):
    """Musiciens inventés déduits du morceau (et de la fiche de la Fabrique musique s'il en vient)."""
    roles = []
    if fiche:
        from . import musique_ia as MI
        st = next((s for s in MI.STYLES if s[0] == fiche.get("style")), None)
        roles = _roles_depuis_texte(" ".join(x for x in ((st[7] if st else ""), fiche.get("instruments", ""), fiche.get("phrase", "")) if x))
    if not roles:
        roles = _roles_depuis_texte(analyse.get("caption_en", ""))
    if len(roles) < 2:                                  # un groupe : au moins trois musiciens, d'après le son
        electro = analyse.get("brillance", 0) > 2600 and analyse.get("percussif", 0) > 1.2
        for r in (["machines", "claviers"] if electro else ["guitare", "basse", "batterie"]):
            if r not in roles:
                roles.append(r)
    chante = analyse.get("chante") or (fiche is not None and not fiche.get("instrumental", True))
    if chante:
        roles.insert(0, "chant")
    roles = roles[:5]
    vf = _net(analyse.get("voix_fr", ""))
    membres = []
    for i, r in enumerate(roles):
        qui = _("Chanteuse") if r == "chant" and "femme" in vf else ROLES[r]
        membres.append({"role": r, "nom": qui, "description": LOOKS[i % len(LOOKS)], "image": ""})
    return membres


def nouveau(chemin, analyse, fiche=None, lieu="concert", anime=False, format_="16:9"):
    clip = {"version": VERSION, "chemin": chemin, "analyse": analyse, "lieu": lieu, "anime": bool(anime),
            "lieu_texte": lieu_par_defaut(analyse), "format": format_, "groupe": groupe_propose(analyse, fiche), "reutiliser": True,
            "plans": [], "moteur": "", "paroles": (fiche or {}).get("paroles", ""), "cree": time.time()}
    clip["plans"] = decouper(clip)
    return clip


def lieu_par_defaut(analyse):
    e = max([s["energie"] for s in analyse.get("sections") or []] or [0.5])
    if analyse.get("bpm", 0) >= 120 and e > 0.6:
        return _("une rue de grande ville la nuit, néons et reflets sur le sol mouillé")
    if analyse.get("bpm", 0) < 90:
        return _("une plage au coucher du soleil, lumière dorée")
    return _("un grand entrepôt désaffecté, rayons de lumière à travers les vitres")


# ------------------------------------------------------------------ découpage plan par plan
# (partie, lieu) -> idées de plans : (action FR, action EN, qui, caméra EN, chant)
_IDEES = {
    ("intro", "concert"): [(_("La scène dans la pénombre et la fumée, les projecteurs s'allument un à un"),
                            "dark stage filled with haze, spotlights turning on one by one", [], "slow push-in, wide shot", False),
                           (_("Le public attend en contre-jour, mains levées"), "crowd waiting in silhouette, hands raised", [],
                            "wide shot from behind the crowd", False)],
    ("intro", "ailleurs"): [(_("Le lieu au calme, la lumière qui change"), "the empty location, light slowly changing", [],
                             "slow aerial establishing shot", False),
                            (_("Les musiciens arrivent et s'installent"), "the band members arrive and get ready", ["*"],
                             "wide tracking shot", False)],
    ("couplet", "*"): [(_("Le chanteur au micro, gros plan"), "close-up of the singer singing into the microphone", ["chant"],
                        "close-up, slight handheld", True),
                       (_("Le guitariste en contre-jour, le manche de la guitare"), "guitarist in backlight, guitar neck in focus", ["guitare"],
                        "medium shot, backlight", False),
                       (_("Le bassiste, plan taille, qui hoche la tête en rythme"), "bass player nodding to the beat", ["basse"],
                        "medium shot", False),
                       (_("Le batteur vu de derrière la batterie"), "drummer seen from behind the drum kit", ["batterie"],
                        "wide shot from behind the drums", False),
                       (_("Le claviériste, mains floues, visage concentré"), "keyboard player, focused face, hands out of focus",
                        ["claviers"], "medium close-up", False),
                       (_("Le groupe entier, lumière douce"), "the whole band playing, soft light", ["*"], "wide shot", False)],
    ("montee", "*"): [(_("Les lumières montent, travelling vers le groupe"), "lights building up, camera moving toward the band",
                       ["*"], "fast dolly-in", False),
                      (_("Le batteur frappe les cymbales, ralenti"), "drummer hitting the cymbals in slow motion", ["batterie"],
                       "slow motion close-up", False),
                      (_("Le chanteur ferme les yeux, l'émotion monte"), "singer with eyes closed, emotion rising", ["chant"],
                       "close-up", True)],
    ("refrain", "concert"): [(_("Toute la scène en pleine lumière, flashs"), "full stage lit up, strobes and flashes, energetic",
                              ["*"], "wide shot", False),
                             (_("Le chanteur face au public, bras tendu"), "singer facing the crowd, arm stretched out", ["chant"],
                              "medium shot from the side of the stage", True),
                             (_("Le public saute, mains levées"), "crowd jumping, hands in the air, confetti", [],
                              "wide shot over the crowd", False),
                             (_("Vue d'en haut au-dessus de la foule"), "overhead shot above the crowd and the stage", [],
                              "high angle crane shot", False),
                             (_("Le guitariste s'avance au bord de la scène"), "guitarist stepping to the edge of the stage", ["guitare"],
                              "low angle shot", False)],
    ("refrain", "ailleurs"): [(_("Le groupe joue à fond dans le lieu"), "the band playing at full energy on location", ["*"],
                               "wide shot, dynamic camera", False),
                              (_("Le chanteur marche vers la caméra en chantant"), "singer walking toward the camera, singing", ["chant"],
                               "tracking shot", True),
                              (_("Plan d'ambiance du lieu, mouvement rapide"), "atmospheric shot of the location, fast movement", [],
                               "fast drone shot", False)],
    ("solo", "*"): [(_("Le soliste seul sous un projecteur, fumée"), "the soloist alone under a single spotlight, haze", ["guitare"],
                     "low angle, backlight", False),
                    (_("Le groupe vu de loin pendant le solo"), "the band seen from afar during the solo", ["*"], "wide shot", False)],
    ("fin", "concert"): [(_("Le groupe salue, les lumières s'éteignent"), "the band bowing, lights fading out", ["*"],
                          "wide shot", False),
                         (_("Le public applaudit en contre-jour"), "crowd applauding in silhouette", [], "wide shot", False)],
    ("fin", "ailleurs"): [(_("Le groupe s'éloigne, le lieu redevient calme"), "the band walking away, the place becomes calm", ["*"],
                           "slow pull-back", False)],
}


def _idees(partie, lieu):
    return _IDEES.get((partie, lieu)) or _IDEES.get((partie, "*")) or _IDEES[("couplet", "*")]


def longueur_plan(partie, mesure_s):
    """Nombre de mesures par plan selon la partie : plans longs au calme, courts au refrain (2 à 8 s)."""
    cible = {"intro": 6.0, "fin": 6.0, "couplet": 4.0, "solo": 4.0, "montee": 3.0, "refrain": 3.0}.get(partie, 4.0)
    n = max(1, int(round(cible / max(0.5, mesure_s))))
    while n > 1 and n * mesure_s > 8.0:
        n -= 1
    while n * mesure_s < 2.0:
        n += 1
    return n


def decouper(clip):
    """Plans calés sur les mesures, idées tirées de la partie et du groupe ; un refrain qui revient reprend les plans du
    premier (« reprend »), si « reutiliser »."""
    an = clip["analyse"]
    mes = an["mesures"]
    roles = {m["role"] for m in clip["groupe"]}
    plans, premiers = [], {}
    for s in an["sections"]:
        bornes = [t for t in mes if s["debut"] - 1e-3 <= t <= s["fin"] + 1e-3]
        if len(bornes) < 2:
            bornes = [s["debut"], s["fin"]]
        mesure_s = (bornes[-1] - bornes[0]) / max(1, len(bornes) - 1)
        n = longueur_plan(s["type"], mesure_s)
        coupes = bornes[::n]
        if coupes[-1] < bornes[-1]:
            if bornes[-1] - coupes[-1] < n * mesure_s / 2 and len(coupes) > 1:
                coupes[-1] = bornes[-1]
            else:
                coupes.append(bornes[-1])
        idees = [i for i in _idees(s["type"], clip["lieu"])
                 if not i[2] or "*" in i[2] or set(i[2]) <= roles] or _idees("couplet", "*")[-1:]
        if not an.get("chante"):
            idees = [i for i in idees if not i[4]] or idees
        deja = premiers.get(s["groupe"]) if clip.get("reutiliser", True) else None
        for k, (a, b) in enumerate(zip(coupes[:-1], coupes[1:])):
            fr, en, qui, cam, chant = idees[k % len(idees)]
            pl = {"debut": round(a, 3), "fin": round(b, 3), "partie": s["type"], "groupe": s["groupe"], "energie": s["energie"],
                  "action": fr, "action_en": en, "qui": sorted(roles) if "*" in qui else list(qui), "camera": cam,
                  "chant": bool(chant and an.get("chante")), "reprend": None, "consigne": "", "image": "", "fichier": "", "levres": ""}
            if deja:
                src = deja[(k + 1) % len(deja)]                 # même plans, autre ordre
                if plans[src]["fin"] - plans[src]["debut"] >= b - a - 0.05:
                    pl.update(reprend=src, action=plans[src]["action"], action_en=plans[src]["action_en"], qui=plans[src]["qui"],
                              camera=plans[src]["camera"], chant=False)
            plans.append(pl)
        if s["groupe"] not in premiers:
            premiers[s["groupe"]] = [i for i, p in enumerate(plans) if p["groupe"] == s["groupe"] and p["reprend"] is None]
    return plans


# ------------------------------------------------------------------ consignes et prix
def _en(texte, traduire=True):
    from .sequence_ia import _anglais
    return _anglais(texte, traduire)


def rendu_en(clip, traduire=True):
    if clip["lieu"] == "concert":
        base = "live concert music video, professional stage lighting, haze, cinematic, shallow depth of field"
    else:
        base = f"cinematic music video shot on location: {_en(clip.get('lieu_texte', ''), traduire)}, film grain"
    if clip.get("anime"):
        base = "2D animated cartoon music video, cel-shaded, vibrant colors, " + base.replace("film grain", "").strip(", ")
    return base


def fiche_membre(m, traduire=True):
    return f"{ROLES_EN.get(m['role'], m['role'])}: {_en(m.get('description', ''), traduire)}"


def consigne(clip, i, traduire=True):
    """Consigne anglaise du plan i (celle écrite à la main dans le tableau passe avant)."""
    pl = clip["plans"][i]
    if pl.get("consigne"):
        return pl["consigne"]
    humeur = "calm, intimate" if pl["energie"] < 0.35 else "explosive, high energy" if pl["energie"] > 0.7 else "building energy"
    qui = [m for m in clip["groupe"] if m["role"] in pl["qui"]]
    morceaux = [rendu_en(clip, traduire), pl.get("action_en") or _en(pl["action"], traduire), pl.get("camera", ""), humeur]
    if qui:
        morceaux.append("Band members in this shot: " + "; ".join(fiche_membre(m, traduire) for m in qui))
    morceaux.append("fictional musicians, no text, no logos, no brand names")
    return ". ".join(x for x in morceaux if x)


def a_fabriquer(clip):
    return [i for i, p in enumerate(clip["plans"]) if p.get("reprend") is None and not (p.get("fichier") and os.path.exists(p["fichier"]))]


def prix_detail(clip, params, avec_images=True):
    """(vidéo, lèvres, images, total) en $ pour les plans encore à fabriquer."""
    from . import generateurs_video as GV, levres as LV
    from .recettes_ia import PRIX_GEMINI
    m = GV.modele(clip.get("moteur") or "", params)
    v = l = im = 0.0
    for i in a_fabriquer(clip):
        p = clip["plans"][i]
        d = int(math.ceil(p["fin"] - p["debut"]))
        if m:
            v += GV.prix(m, d)
        if p.get("chant"):
            l += LV.prix("latentsync", d)
        if avec_images:
            im += PRIX_GEMINI["image"]
    if avec_images:
        im += PRIX_GEMINI["image"] * sum(1 for g in clip["groupe"] if not (g.get("image") and os.path.exists(g["image"])))
    return round(v, 2), round(l, 2), round(im, 2), round(v + l + im, 2)


# ------------------------------------------------------------------ fabrication
def dossier(clip):
    from .fabrique import dossier_plans
    d = clip.get("dossier")
    if not d:
        d = os.path.join(dossier_plans(), "Clip " + time.strftime("%Y-%m-%d %Hh%M"))
        clip["dossier"] = d
    os.makedirs(d, exist_ok=True)
    return d


def enregistrer(clip):
    with open(os.path.join(dossier(clip), "clip.json"), "w", encoding="utf-8") as f:
        json.dump(clip, f, ensure_ascii=False, indent=1)


def portrait(clip, k, params):
    """Image de référence d'un musicien (Gemini) : le même visage dans tous les plans."""
    from . import ia
    m = clip["groupe"][k]
    png = ia.generer_image(params, "Reference portrait of a fictional musician for a music video, full body and clear face, "
                                   f"plain studio background. {fiche_membre(m)}. Style: {rendu_en(clip)}. No text, no logos.")
    ch = os.path.join(dossier(clip), f"membre{k + 1}_{m['role']}.png")
    with open(ch, "wb") as f:
        f.write(png)
    m["image"] = ch
    return ch


def image_depart(clip, i, params):
    from . import ia
    pl = clip["plans"][i]
    refs = [m["image"] for m in clip["groupe"] if m["role"] in pl["qui"] and m.get("image") and os.path.exists(m["image"])][:3]
    texte = consigne(clip, i)
    png = (ia.generer_image_refs(params, "First frame of this music video shot, one still image. Keep the people's appearance from "
                                         "the reference images. " + texte, refs) if refs else
           ia.generer_image(params, "First frame of this music video shot, one still image. " + texte))
    ch = os.path.join(dossier(clip), f"plan{i + 1:02d}_depart.png")
    with open(ch, "wb") as f:
        f.write(png)
    pl["image"] = ch
    return ch


def _extrait(src, debut, duree, sortie, video=True):
    from . import moteur
    args = ["-y", "-v", "error", "-ss", f"{debut:.3f}", "-t", f"{duree:.3f}", "-i", src]
    args += (["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"] if video else ["-vn", "-ac", "2", "-ar", "48000"])
    moteur.lancer(args + [sortie])
    return sortie


def fabriquer_plan(clip, i, params, avec_images=True, progression=None, arret=lambda: False):
    """Plan i : image de départ (avec les visages du groupe), vidéo par le cloud, puis lèvres calées sur la voix si le plan
    chante. Renvoie le fichier final."""
    from . import generateurs_video as GV, levres as LV, moteur
    pl = clip["plans"][i]
    av = lambda f, t: progression and progression(f, t)
    d = pl["fin"] - pl["debut"]
    if avec_images and not (pl.get("image") and os.path.exists(pl["image"])):
        av(0.02, _("Image de départ du plan {n}", n=i + 1))
        image_depart(clip, i, params)
    sortie = os.path.join(dossier(clip), f"plan{i + 1:02d}_{int(time.time())}.mp4")
    GV.generer(params, clip["moteur"], consigne(clip, i), sortie, int(math.ceil(d)), clip.get("format", "16:9"),
               pl.get("image") if avec_images else None, lambda f: av(0.1 + 0.7 * f, _("Plan {n} : vidéo", n=i + 1)), arret)
    pl["fichier"] = sortie
    if pl.get("chant") and LV.clef(params):
        av(0.82, _("Plan {n} : lèvres sur la voix", n=i + 1))
        dv = float((moteur.sonder(sortie) or {}).get("duree") or d)
        video = _extrait(sortie, 0.0, min(d, dv), os.path.join(dossier(clip), f"plan{i + 1:02d}_court.mp4"))
        son = _extrait(clip["analyse"].get("voix") or clip["chemin"], pl["debut"], min(d, dv),
                       os.path.join(dossier(clip), f"plan{i + 1:02d}_voix.wav"), video=False)
        lv = os.path.join(dossier(clip), f"plan{i + 1:02d}_levres.mp4")
        LV.fabriquer(params, "latentsync", son, lv, video=video, arret=arret)
        pl["levres"] = lv
        pl["fichier"] = lv
    av(1.0, _("Plan {n} prêt", n=i + 1))
    enregistrer(clip)
    return pl["fichier"]


def fichier_du_plan(clip, i):
    p = clip["plans"][i]
    if p.get("reprend") is not None:
        return clip["plans"][p["reprend"]].get("fichier")
    return p.get("fichier")


# ------------------------------------------------------------------ montage
def piste_libre(projet, debut, fin):
    """Piste vidéo sans rien entre debut et fin (la Vidéo 1 si elle est vide là ; sinon une piste au-dessus)."""
    from .projet import fin_clip
    for p in projet.pistes_video():
        if not any(c["debut"] < fin and fin_clip(c) > debut for c in projet.clips_piste(p)):
            return p
    return projet.ajouter_piste("video")


def monter(projet, clip, t0, fenetre=None):
    """Pose les plans fabriqués sous la chanson (le début de la chanson tombe à t0 sur la timeline), coupes sur les mesures,
    plans muets (la musique reste celle de la piste). fenetre : (de, à) dans la chanson, le passage réellement posé (un
    morceau rogné) ; les plans hors de ce passage sont laissés. Renvoie le nombre de plans posés."""
    from . import moteur
    a, b = fenetre or (0.0, 1e9)
    plans = [(i, p) for i, p in enumerate(clip["plans"]) if fichier_du_plan(clip, i) and os.path.exists(fichier_du_plan(clip, i))
             and p["debut"] >= a - 0.05 and p["fin"] <= b + 0.05]
    if not plans:
        return 0
    piste = piste_libre(projet, t0 + plans[0][1]["debut"], t0 + plans[-1][1]["fin"])
    medias, n = {}, 0
    for i, p in plans:
        f = fichier_du_plan(clip, i)
        if f not in medias:
            m = projet.ajouter_media(f, moteur.sonder(f))
            m["nom"] = _("Clip : {a}", a=p["action"][:40])
            medias[f] = m
        m = medias[f]
        besoin = p["fin"] - p["debut"]
        dispo = float(m.get("duree") or besoin)
        v = 1.0 if dispo >= besoin - 0.05 else max(0.5, dispo / besoin)       # plan un peu court : légèrement ralenti
        c = projet.ajouter_clip(m["id"], piste, t0 + p["debut"], 0.0, min(dispo, besoin * v), v)
        c["muet"] = True
        c["clip_groupe"] = i
        n += 1
    return n


# ------------------------------------------------------------------ idées de plans par l'IA (sur clic)
CONSIGNE_IDEES = """Tu es réalisateur de clips musicaux. On te donne une chanson analysée (parties, énergie, paroles éventuelles),
le lieu, le rendu et les musiciens INVENTÉS du groupe, puis la liste des plans déjà calés sur les mesures.
Pour chaque plan, propose une idée de plan plus inspirée, qui suit l'ambiance de la partie et, s'il y en a, le sens des paroles
à ce moment. Règles : jamais un vrai groupe, une personnalité, un logo ou une marque ; préférer des plans où l'on ne juge pas
les doigts sur les instruments (larges, contre-jour, ralentis, visages, public, ambiance) ; garder « qui » parmi les rôles donnés.
Réponds en JSON seulement : {"plans": [{"i": numéro, "action": "idée en français, une phrase", "action_en": "the same idea in
English, one sentence, for a video generator", "qui": ["rôle", …]}]} avec un objet par plan donné."""


def lire_idees(clip, texte):
    """Applique la réponse de l'IA aux plans (bornée : numéros connus, rôles du groupe) ; renvoie le nombre de plans changés."""
    from .sequence_ia import _json
    d = _json(texte) or {}
    roles = {m["role"] for m in clip["groupe"]}
    n = 0
    for e in d.get("plans") or []:
        try:
            i = int(e.get("i"))
        except (TypeError, ValueError):
            continue
        if not 0 <= i < len(clip["plans"]) or clip["plans"][i].get("reprend") is not None:
            continue
        a, ae = str(e.get("action") or "").strip(), str(e.get("action_en") or "").strip()
        if not a:
            continue
        p = clip["plans"][i]
        p.update(action=a[:200], action_en=ae[:300], consigne="")
        q = [r for r in e.get("qui") or [] if r in roles]
        if isinstance(e.get("qui"), list):
            p["qui"] = q
            p["chant"] = p["chant"] and "chant" in q
        n += 1
    for i, p in enumerate(clip["plans"]):                       # les reprises suivent leur modèle
        if p.get("reprend") is not None:
            m = clip["plans"][p["reprend"]]
            p.update(action=m["action"], action_en=m["action_en"], qui=m["qui"])
    return n


def idees_ia(clip, params, niveau="cloud"):
    from .sequence_ia import _demander
    an = clip["analyse"]
    demande = json.dumps({
        "chanson": {"tempo": an.get("bpm"), "ambiance": an.get("resume"), "voix": an.get("voix_fr"),
                    "parties": [{"de": s["debut"], "a": s["fin"], "partie": s["type"], "energie": s["energie"]} for s in an["sections"]]},
        "paroles": (clip.get("paroles") or "")[:3000],
        "lieu": LIEUX[clip["lieu"]] + (" : " + clip.get("lieu_texte", "") if clip["lieu"] == "ailleurs" else ""),
        "rendu": "dessin animé" if clip.get("anime") else "réaliste",
        "groupe": [{"role": m["role"], "description": m["description"]} for m in clip["groupe"]],
        "plans": [{"i": i, "de": p["debut"], "a": p["fin"], "partie": p["partie"], "idee": p["action"], "qui": p["qui"]}
                  for i, p in enumerate(clip["plans"]) if p.get("reprend") is None]}, ensure_ascii=False)
    return lire_idees(clip, _demander(params, CONSIGNE_IDEES, demande, niveau, json_attendu=True, max_jetons=6000))
