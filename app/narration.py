"""Vidéo de narration déduite de ce qui est dit (0.9.67). La voix (piste Voix ou autre) est transcrite sur ce poste au mot
près, découpée en idées de 2 à 8 secondes ; pour chaque idée, une image proposée (règles, ou l'IA sur clic), que l'on
corrige ; un présentateur peut apparaître par moments et dire la voix (lèvres calées). Fabrication par le cloud, prix
total demandé avant ; les plans sont posés au-dessus du film, exactement sous les mots qu'ils illustrent, muets (la
voix reste celle de la timeline). Jamais une personnalité ni une marque."""
import json, math, os, re, time

from .langue import _

VERSION = 1
RENDUS = {"anime": (_("Dessin animé"), "2D animated cartoon, cel-shaded, vibrant colors"),
          "aquarelle": (_("Aquarelle animée"), "gently animated watercolor illustration, soft paper texture"),
          "cinema": (_("Cinéma réaliste"), "cinematic realistic b-roll footage, natural light, shallow depth of field"),
          "documentaire": (_("Documentaire"), "documentary footage, handheld camera, natural colors"),
          "3d": (_("Animation 3D"), "3D animated render, soft studio lighting, smooth camera move")}
FIN_PHRASE = re.compile(r"[.!?…:;]$")


def _net(t):
    import unicodedata
    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()


# ------------------------------------------------------------------ découpage de la voix en idées
def phrases(mots, pause=0.6):
    """Mots datés [{t0, t1, mot}] → phrases [(t0, t1, texte, [mots])] : fin de phrase sur la ponctuation ou un silence."""
    out, cour = [], []
    for k, m in enumerate(mots):
        cour.append(m)
        suivant = mots[k + 1] if k + 1 < len(mots) else None
        if suivant is None or FIN_PHRASE.search(m["mot"]) or suivant["t0"] - m["t1"] > pause:
            out.append((cour[0]["t0"], cour[-1]["t1"], " ".join(x["mot"] for x in cour), cour))
            cour = []
    return out


def _couper_long(ph, maxi):
    """Une phrase trop longue est coupée à une virgule ou au plus grand silence, sinon au milieu, jusqu'à tenir."""
    t0, t1, _t, ms = ph
    if t1 - t0 <= maxi or len(ms) < 2:
        return [ph]
    milieu = (t0 + t1) / 2
    cands = [k for k in range(1, len(ms)) if ms[k - 1]["mot"].endswith(",")]
    if not cands:
        cands = [max(range(1, len(ms)), key=lambda k: ms[k]["t0"] - ms[k - 1]["t1"])] if len(ms) > 2 else [1]
    k = min(cands, key=lambda k: abs(ms[k]["t0"] - milieu))
    a, b = ms[:k], ms[k:]
    return (_couper_long((a[0]["t0"], a[-1]["t1"], " ".join(x["mot"] for x in a), a), maxi) +
            _couper_long((b[0]["t0"], b[-1]["t1"], " ".join(x["mot"] for x in b), b), maxi))


def segments(mots, mini=2.5, maxi=8.0):
    """Idées de mini à maxi secondes, collées (chaque plan va du premier mot de son idée au premier mot de la suivante)."""
    ph = [p for x in phrases(mots) for p in _couper_long(x, maxi)]
    groupes, cour = [], []
    for p in ph:
        if cour and (p[1] - cour[0][0] > maxi or cour[-1][1] - cour[0][0] >= mini):
            groupes.append(cour)
            cour = []
        cour.append(p)
    if cour:
        if groupes and cour[-1][1] - cour[0][0] < mini and cour[-1][1] - groupes[-1][0][0] <= maxi:
            groupes[-1] += cour
        else:
            groupes.append(cour)
    segs = []
    for i, g in enumerate(groupes):
        debut = g[0][0]
        fin = groupes[i + 1][0][0] if i + 1 < len(groupes) else g[-1][1] + 0.4
        segs.append({"debut": round(debut, 3), "fin": round(fin, 3), "texte": " ".join(p[2] for p in g).strip()})
    return segs


# ------------------------------------------------------------------ narration et plans
def nouvelle(segs, rendu="cinema", format_="16:9", piste="voix"):
    n = {"version": VERSION, "rendu": rendu, "format": format_, "piste": piste, "moteur": "",
         "presentateur": {"actif": False, "image": "", "description": _("une femme d'une quarantaine d'années, souriante, veste bleue, "
                                                                      "dans un bureau lumineux")},
         "plans": [], "cree": time.time()}
    n["plans"] = [plan(s) for s in segs]
    return n


def plan(s):
    return {"debut": s["debut"], "fin": s["fin"], "texte": s["texte"], "action": s["texte"], "action_en": "",
            "presentateur": False, "consigne": "", "fichier": "", "reprend": None}


def proposer_presentateur(narr):
    """Présentateur au début et à la fin (accueil, conclusion), et à peu près un plan sur cinq ; le reste en images."""
    pl = narr["plans"]
    for k, p in enumerate(pl):
        p["presentateur"] = bool(narr["presentateur"]["actif"]) and (k == 0 or k == len(pl) - 1 or (len(pl) > 4 and k % 5 == 0))


def _en(texte):
    from .sequence_ia import _anglais
    return _anglais(texte, True)


def consigne(narr, i):
    p = narr["plans"][i]
    if p.get("consigne"):
        return p["consigne"]
    rendu = RENDUS.get(narr["rendu"], RENDUS["cinema"])[1]
    if p.get("presentateur"):
        return (f"{rendu}. The presenter speaks calmly to the camera, natural small gestures, friendly expression. "
                "No text, no subtitles, no logos.")
    idee = p.get("action_en") or _en(p.get("action") or p["texte"])
    return f"{rendu}. A shot that illustrates: {idee}. No text, no subtitles, no logos, no brand names, no real public figures."


def a_fabriquer(narr):
    return [i for i, p in enumerate(narr["plans"]) if not (p.get("fichier") and os.path.exists(p["fichier"]))]


def prix_detail(narr, params):
    """(images animées, présentateur, portrait, total) en $ pour les plans encore à fabriquer."""
    from . import generateurs_video as GV, levres as LV
    from .recettes_ia import PRIX_GEMINI
    m = GV.modele(narr.get("moteur") or "", params)
    v = pr = im = 0.0
    for i in a_fabriquer(narr):
        p = narr["plans"][i]
        d = p["fin"] - p["debut"]
        if p.get("presentateur"):
            pr += LV.prix("omnihuman", d)
        elif m:
            v += GV.prix(m, int(math.ceil(d)))
    pres = narr["presentateur"]
    if any(p.get("presentateur") for p in narr["plans"]) and not (pres.get("image") and os.path.exists(pres["image"])):
        im += PRIX_GEMINI["image"]
    return round(v, 2), round(pr, 2), round(im, 2), round(v + pr + im, 2)


# ------------------------------------------------------------------ idées par l'IA (sur clic)
CONSIGNE_IDEES = """Tu es réalisateur de vidéos explicatives. On te donne ce qui est dit, découpé en morceaux datés, et le rendu
voulu. Pour chaque morceau, propose UNE image animée qui illustre concrètement ce qui est dit à ce moment (un plan, pas un
texte à l'écran). Si un présentateur est disponible, mets "presentateur": true pour les morceaux où il vaut mieux voir la
personne qui parle (accueil, avis personnel, conclusion), au plus un tiers des morceaux. Règles : jamais de texte écrit dans
l'image, jamais une personnalité réelle, un logo ou une marque ; des plans variés qui se suivent bien.
Réponds en JSON seulement : {"plans": [{"i": numéro, "action": "idée d'image en français, une phrase", "action_en": "the same
shot in English, one sentence, for a video generator", "presentateur": false}]} avec un objet par morceau donné."""


def lire_idees(narr, texte):
    from .sequence_ia import _json
    d = _json(texte) or {}
    n = 0
    actif = bool(narr["presentateur"].get("actif"))
    for e in d.get("plans") or []:
        try:
            i = int(e.get("i"))
        except (TypeError, ValueError):
            continue
        if not 0 <= i < len(narr["plans"]):
            continue
        a = str(e.get("action") or "").strip()
        if not a:
            continue
        p = narr["plans"][i]
        p.update(action=a[:200], action_en=str(e.get("action_en") or "").strip()[:300], consigne="",
                 presentateur=actif and bool(e.get("presentateur")))
        n += 1
    return n


def idees_ia(narr, params, niveau="cloud"):
    from .sequence_ia import _demander
    demande = json.dumps({"rendu": RENDUS.get(narr["rendu"], RENDUS["cinema"])[0],
                          "presentateur_disponible": bool(narr["presentateur"].get("actif")),
                          "morceaux": [{"i": i, "de": p["debut"], "a": p["fin"], "dit": p["texte"]} for i, p in enumerate(narr["plans"])]},
                         ensure_ascii=False)
    return lire_idees(narr, _demander(params, CONSIGNE_IDEES, demande, niveau, json_attendu=True, max_jetons=6000))


# ------------------------------------------------------------------ fabrication
def dossier(narr):
    from .fabrique import dossier_plans
    d = narr.get("dossier")
    if not d:
        d = os.path.join(dossier_plans(), "Narration " + time.strftime("%Y-%m-%d %Hh%M"))
        narr["dossier"] = d
    os.makedirs(d, exist_ok=True)
    return d


def enregistrer(narr):
    with open(os.path.join(dossier(narr), "narration.json"), "w", encoding="utf-8") as f:
        json.dump(narr, f, ensure_ascii=False, indent=1)


def portrait_presentateur(narr, params):
    """Image du présentateur inventé (Gemini), de face, prête à parler."""
    from . import ia
    pres = narr["presentateur"]
    png = ia.generer_image(params, "Portrait of a fictional presenter facing the camera, upper body, mouth closed, eyes open, "
                                   f"well lit: {_en(pres.get('description', ''))}. Style: {RENDUS.get(narr['rendu'], RENDUS['cinema'])[1]}. "
                                   "No text, no logos.")
    ch = os.path.join(dossier(narr), f"presentateur_{int(time.time())}.png")
    with open(ch, "wb") as f:
        f.write(png)
    pres["image"] = ch
    return ch


def fabriquer_plan(narr, i, params, son=None, progression=None, arret=lambda: False):
    """Plan i : image animée par le moteur vidéo, ou le présentateur qui dit `son` (le passage de voix) par OmniHuman."""
    from . import generateurs_video as GV, levres as LV
    p = narr["plans"][i]
    d = p["fin"] - p["debut"]
    av = lambda f, t: progression and progression(f, t)
    sortie = os.path.join(dossier(narr), f"plan{i + 1:02d}_{int(time.time())}.mp4")
    if p.get("presentateur"):
        av(0.05, _("Plan {n} : le présentateur parle", n=i + 1))
        LV.fabriquer(params, "omnihuman", son, sortie, image=narr["presentateur"]["image"], consigne=consigne(narr, i),
                     progression=lambda f, t="": av(0.05 + 0.9 * f, t), arret=arret)
    else:
        GV.generer(params, narr["moteur"], consigne(narr, i), sortie, int(math.ceil(d)), narr.get("format", "16:9"), None,
                   lambda f: av(0.05 + 0.9 * f, _("Plan {n} : image animée", n=i + 1)), arret)
    p["fichier"] = sortie
    enregistrer(narr)
    av(1.0, _("Plan {n} prêt", n=i + 1))
    return sortie


def monter(projet, narr):
    """Pose les plans au-dessus du film, chacun exactement sous les mots qu'il illustre ; muets. Renvoie le nombre posé."""
    from . import moteur
    from .clip_groupe import piste_libre
    plans = [p for p in narr["plans"] if p.get("fichier") and os.path.exists(p["fichier"])]
    if not plans:
        return 0
    piste = piste_libre(projet, plans[0]["debut"], plans[-1]["fin"])
    n = 0
    for p in plans:
        m = projet.ajouter_media(p["fichier"], moteur.sonder(p["fichier"]))
        m["nom"] = _("Narration : {a}", a=p["action"][:40])
        besoin = p["fin"] - p["debut"]
        dispo = float(m.get("duree") or besoin)
        v = 1.0 if dispo >= besoin - 0.05 else max(0.5, dispo / besoin)
        c = projet.ajouter_clip(m["id"], piste, p["debut"], 0.0, min(dispo, besoin * v), v)
        c["muet"] = True
        c["narration"] = True
        n += 1
    return n
