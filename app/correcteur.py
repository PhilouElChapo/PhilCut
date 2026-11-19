"""0.9.98 : le correcteur du Réalisateur.

Chaque défaut, trouvé par l'IA (relecture d'un plan fabriqué, proposée avant la fabrication) ou écrit par l'utilisateur
(à la ligne rouge de l'aperçu, ou avec l'instant dans le texte : « à 0:12 le pilote n'a plus sa barbe »), devient une
proposition de correction : la cause probable, ce qui est refait (une fiche, une image clef, un plan et ceux qui en
partent) et le prix. Rien n'est payé sans le clic. Deux remarques sur le même élément : PhilCut propose de l'écrire dans
sa fiche, pour que ça ne revienne plus.

Un défaut : {"id", "plan", "t" (secondes dans le plan), "t_seq" (dans toute la séquence), "quoi" (visage, objet, geste,
continuite, autre), "element", "texte", "source" (ia / moi), "fait"}."""
import os, re, time

from .langue import _
from . import sequence_ia as Q

QUOI = ("visage", "objet", "geste", "continuite", "autre")
ACTIONS = ("refaire_plan", "preciser_fiche", "refaire_fiche", "refaire_image_clef")

CONSIGNE_RELIRE = """Tu relis un plan vidéo fabriqué par une IA, comme une scripte. Les {n} premières images sont les fiches de
référence ({noms}). Les images suivantes sont des vues du plan, à {instants} secondes. Action demandée : « {action} ».
Cherche les défauts : visage, barbe, cheveux ou tenue qui ne correspondent plus à la fiche ; objet (véhicule, avion…) qui
change de forme ou de couleur ; geste impossible (traverser un objet, membre en trop) ; personne qui apparaît ou disparaît
sans raison ; raccord faux avec l'action. Rends un objet JSON : {{"defauts": [{{"t": instant en secondes (une des valeurs
données), "quoi": "visage|objet|geste|continuite|autre", "element": "nom de la fiche concernée ou vide", "texte": "en une
phrase courte, en {langue}"}}]}} ; liste vide si tout va bien. Ne signale que ce qui se voit vraiment."""

CONSIGNE_PROPOSER = """Tu es le correcteur d'une séquence vidéo fabriquée par IA, plan par plan, à partir de fiches (une image de
référence par personne ou objet). Voici la séquence : {plans}. Fiches : {fiches}. Défaut signalé ({source}) au plan {plan},
à {t} s : « {texte} ».
Choisis UNE correction : "refaire_plan" (refaire ce plan avec une précision ajoutée à sa consigne), "preciser_fiche" (ajouter
un détail à la description d'une fiche, puis refaire la fiche et les plans où on la voit), "refaire_fiche" (refaire l'image
de la fiche telle quelle, puis les plans où on la voit), "refaire_image_clef" (refaire l'image clef de fin de ce plan avec une
précision). Rends un objet JSON : {{"action": "...", "element": "nom de la fiche concernée ou vide", "precision": "en anglais,
courte, ce qu'il faut imposer", "cause": "en une phrase courte, en {langue}, la cause probable"}}."""


# ------------------------------------------------------------------ temps
def debuts(seq):
    """Début de chaque plan dans la séquence (secondes)."""
    out, t = [], 0.0
    for pl in seq["plans"]:
        out.append(t)
        t += float(pl.get("duree") or Q.DUREE_PLAN)
    return out


def plan_a(seq, t_seq):
    """(plan, instant dans le plan) pour un instant de toute la séquence."""
    d = debuts(seq)
    for i in range(len(d) - 1, -1, -1):
        if t_seq >= d[i] - 1e-6:
            return i, max(0.0, t_seq - d[i])
    return 0, 0.0


def instant_dans(texte):
    """L'instant écrit dans une remarque (« à 0:12 », « 1:05 », « 12 s », « à 12,5 s ») en secondes, sinon None."""
    t = texte or ""
    m = re.search(r"\b(\d{1,2}):(\d{2})(?:[.,](\d))?\b", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2)) + (int(m.group(3)) / 10 if m.group(3) else 0)
    m = re.search(r"\b(\d{1,3}(?:[.,]\d)?)\s*(?:s\b|sec|seconde)", t)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _id():
    return f"d{int(time.time() * 1000) % 10 ** 9}"


def defaut(seq, plan, t, texte, source="moi", quoi="autre", element=""):
    d = {"id": _id(), "plan": int(plan), "t": round(float(t), 2), "t_seq": round(debuts(seq)[int(plan)] + float(t), 2),
         "quoi": quoi if quoi in QUOI else "autre", "element": element or "", "texte": (texte or "").strip()[:300],
         "source": source, "fait": False}
    seq.setdefault("defauts", []).append(d)
    return d


def remarque(seq, texte, t_seq=None):
    """Une remarque écrite : l'instant est pris dans le texte s'il y est, sinon à la ligne rouge (t_seq). L'élément visé est
    deviné par son nom (fiches de la séquence)."""
    t = instant_dans(texte)
    t = t if t is not None else (t_seq or 0.0)
    i, dans = plan_a(seq, t)
    element = next((p["nom"] for p in seq.get("personnages") or [] if p["nom"].lower() in (texte or "").lower()), "")
    return defaut(seq, i, dans, texte, "moi", "autre", element)


# ------------------------------------------------------------------ relecture par l'IA
def vues(video, dossier, prefixe, n=4):
    """n vues réparties dans le plan : [(instant, image)]."""
    from . import moteur
    duree = float((moteur.sonder(video) or {}).get("duree") or 0.0)
    if duree <= 0:
        return []
    out = []
    for k in range(n):
        t = round(min(duree - 0.1, 0.1 + k * (duree - 0.2) / max(1, n - 1)), 2)
        f = os.path.join(dossier, f"{prefixe}_r{k}.jpg")
        moteur.lancer(["-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1", "-q:v", "3", f])
        if os.path.exists(f):
            out.append((max(0.0, t), f))
    return out


def relire(params, seq, i, niveau="claude"):
    """L'IA relit le plan i fabriqué ; ses défauts sont ajoutés à seq["defauts"] (les anciens défauts IA du plan sont
    remplacés). Renvoie la liste ; None si la relecture n'est pas possible."""
    from . import assistant_creation as A
    pl = seq["plans"][i]
    if not (pl.get("fichier") and os.path.exists(pl["fichier"])):
        return None
    refs = Q.references_du_plan(seq, pl)
    fiches = [im[0] for _n, im in refs][:4]
    noms = ", ".join(n for n, _im in refs)[:240] or "-"
    v = vues(pl["fichier"], Q.dossier(seq), f"plan{i + 1:02d}")
    if len(v) < 2:
        return None
    d = A.demander(params, CONSIGNE_RELIRE.format(n=len(fiches), noms=noms, instants=", ".join(f"{t:g}" for t, _f in v),
                                                  action=pl.get("action", ""), langue=A._langue()),
                   "Relis ce plan.", fiches + [f for _t, f in v], niveau, max_jetons=900)
    trouves = (d or {}).get("defauts") if isinstance(d, dict) else None
    seq["defauts"] = [x for x in seq.get("defauts") or [] if not (x["plan"] == i and x["source"] == "ia")]
    out = []
    for x in trouves or []:
        if not isinstance(x, dict) or not str(x.get("texte") or "").strip():
            continue
        try:
            t = float(x.get("t") or 0)
        except (TypeError, ValueError):
            t = 0.0
        out.append(defaut(seq, i, min(t, float(pl.get("duree") or Q.DUREE_PLAN)), str(x["texte"]), "ia",
                          str(x.get("quoi") or "autre"), str(x.get("element") or "")))
    pl["verdict"] = {"ok": not out, "visages": not any(x["quoi"] == "visage" for x in out),
                     "action": not any(x["quoi"] in ("geste", "continuite") for x in out),
                     "probleme": out[0]["texte"] if out else ""}
    return out


# ------------------------------------------------------------------ propositions
def plans_ou_on_voit(seq, element):
    return [i for i, pl in enumerate(seq["plans"]) if element in Q.visibles(seq, pl)] if element else []


def a_refaire(seq, action, plan, element=""):
    """Les plans à refabriquer pour une correction : le plan (et ceux de son calcul continu qui en partent), ou tous ceux où
    l'élément est visible pour une fiche refaite."""
    if action in ("preciser_fiche", "refaire_fiche") and element:
        plans = plans_ou_on_voit(seq, element) or [plan]
    else:
        plans = [plan]
    out = set()
    for i in plans:
        out.update(Q.plans_du_groupe_apres(seq, i))
    return sorted(out)


def prix(seq, proposition, params):
    from . import assistant_creation as A
    plans = proposition["plans"]
    p = sum(A.prix_plan(seq, i, seq.get("moteur") or "kling-o3-ref", params) for i in plans)
    if proposition["action"] in ("preciser_fiche", "refaire_fiche", "refaire_image_clef"):
        p += A.PRIX_IMAGE
    return round(p, 2)


def proposer(params, seq, d, niveau="claude"):
    """La correction proposée pour un défaut : {"defaut", "action", "element", "precision", "cause", "plans", "prix"}. Sans IA :
    refaire le plan avec la remarque comme précision."""
    from . import assistant_creation as A
    choix = {}
    try:
        plans = " | ".join(f"{k + 1}. {pl.get('action', '')} ({pl.get('duree')} s)" for k, pl in enumerate(seq["plans"]))[:2500]
        fiches = ", ".join(p["nom"] for p in seq.get("personnages") or [])[:400] or "-"
        r = A.demander(params, CONSIGNE_PROPOSER.format(plans=plans, fiches=fiches, plan=d["plan"] + 1, t=d["t"], texte=d["texte"],
                                                        source=_("par l'IA") if d["source"] == "ia" else _("par vous"),
                                                        langue=A._langue()),
                       "Propose la correction.", None, niveau, max_jetons=500)
        choix = r if isinstance(r, dict) else {}
    except Exception:      # noqa: BLE001 : sans IA, la correction simple
        choix = {}
    action = choix.get("action") if choix.get("action") in ACTIONS else "refaire_plan"
    noms = {p["nom"].lower(): p["nom"] for p in seq.get("personnages") or []}
    element = noms.get(str(choix.get("element") or d.get("element") or "").lower(), "")
    if action in ("preciser_fiche", "refaire_fiche") and not element:
        action = "refaire_plan"
    precision = str(choix.get("precision") or "").strip()[:300] or d["texte"]
    cause = str(choix.get("cause") or "").strip()[:240] or _("plan à refaire avec votre remarque comme consigne")
    p = {"defaut": d["id"], "action": action, "element": element, "precision": precision, "cause": cause,
         "plan": d["plan"], "plans": a_refaire(seq, action, d["plan"], element)}
    p["prix"] = prix(seq, p, params)
    return p


def texte_proposition(p):
    quoi = {"refaire_plan": _("refaire le plan {i} avec cette précision : « {x} »", i=p["plan"] + 1, x=p["precision"]),
            "preciser_fiche": _("ajouter à la fiche de {e} : « {x} », refaire sa fiche", e=p["element"], x=p["precision"]),
            "refaire_fiche": _("refaire la fiche de {e}", e=p["element"]),
            "refaire_image_clef": _("refaire l'image clef du plan {i} : « {x} »", i=p["plan"] + 1, x=p["precision"])}[p["action"]]
    plans = ", ".join(str(i + 1) for i in p["plans"])
    return _("Cause probable : {c}.\nCorrection : {q} ; puis refaire le(s) plan(s) {l}.\nPrix : environ {p} $.", c=p["cause"],
             q=quoi, l=plans, p=f"{p['prix']:.2f}".replace(".", ","))


def appliquer(seq, p):
    """Prépare la séquence pour la correction (rien n'est encore fabriqué) : précisions posées, fiche ou image clef remise à
    faire, fichiers des plans concernés retirés. Le défaut est noté « fait »."""
    pl = seq["plans"][p["plan"]]
    if p["action"] == "refaire_plan":
        pl["precision"] = ((pl.get("precision") or "") + " " + p["precision"]).strip()[:600]
    elif p["action"] in ("preciser_fiche", "refaire_fiche"):
        perso = next((x for x in seq["personnages"] if x["nom"] == p["element"]), None)
        if perso is not None:
            if p["action"] == "preciser_fiche":
                perso["description"] = ((perso.get("description") or "") + " " + p["precision"]).strip()
            perso["planche"] = ""                       # la fiche sera refaite à la préparation
    elif p["action"] == "refaire_image_clef":
        pl["image_fin"] = ""
        pl["precision_fin"] = p["precision"]
    for i in p["plans"]:
        x = seq["plans"][i]
        x["fichier"], x["verdict"] = "", None
        x.pop("groupe", None)
    for d in seq.get("defauts") or []:
        if d["id"] == p["defaut"]:
            d["fait"] = True
    seq.setdefault("corrections", []).append({k: p[k] for k in ("action", "element", "precision", "plans", "prix")})
    return p["plans"]


# ------------------------------------------------------------------ apprendre
def a_retenir(seq):
    """Deux remarques (ou plus) de l'utilisateur sur le même élément : [(element, [textes])] à proposer dans sa fiche."""
    par = {}
    for d in seq.get("defauts") or []:
        if d["source"] == "moi" and d.get("element"):
            par.setdefault(d["element"], []).append(d["texte"])
    deja = set(seq.get("retenus") or [])
    return [(e, t) for e, t in par.items() if len(t) >= 2 and e not in deja]
