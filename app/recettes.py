"""Recettes de montage : ce que l'assistant propose a partir des fiches des rushes.

Une recette est un dictionnaire (JSON) : type de video, logo d'ouverture, musique, plans (ordre, bornes, vitesse,
effets, transition), textes, Goodies, look, publication, plans a generer. Elle est produite :
  - sans IA, par les regles de ce module (gratuit, immediat) ;
  - par une IA locale ou cloud (assistant.py) qui remplit le meme schema.
`appliquer()` la pose dans le projet ; chaque element est accepte ou refuse dans le volet Proposition.
"""
import copy

from .langue import _

TYPES = {
    "vol": {"nom": _("Vol"), "logo": "code", "musique": {"ambiance": "energique", "bpm": 120, "energie": 0.75}, "look": "ciel_altitude",
            "goodies": ["altimetre", "anemometre"], "transitions": ["t_puzzle", "t_zoom", "t_fondu_noir"], "plan_s": (4, 9)},
    "visite": {"nom": _("Visite / ambiance d'un lieu"), "logo": "lucioles", "musique": {"ambiance": "chaleureuse", "bpm": 85, "energie": 0.4},
               "look": "nuit_chaude", "goodies": ["horloge"], "transitions": ["t_fondu_noir", "t_balayage"], "plan_s": (3, 7)},
    "portrait": {"nom": _("Portrait / personne"), "logo": "eclat", "musique": {"ambiance": "douce", "bpm": 95, "energie": 0.5}, "look": "cosy",
                 "goodies": [], "transitions": ["t_fondu_blanc", "t_zoom"], "plan_s": (2.5, 6)},
    "clip_ia": {"nom": _("Clip de photos animées"), "logo": "particules", "musique": {"ambiance": "energique", "bpm": 110, "energie": 0.7},
                "look": "glow", "goodies": [], "transitions": ["t_glitch", "t_zoom", "t_balayage"], "plan_s": (2, 5)},
    "annonce": {"nom": _("Annonce / pharmacie"), "logo": "trace", "musique": {"ambiance": "legere", "bpm": 100, "energie": 0.5}, "look": "epure",
                "goodies": ["croix", "horaires"], "transitions": ["t_balayage"], "plan_s": (3, 6)},
    "generique": {"nom": _("Montage"), "logo": "trace", "musique": {"ambiance": "douce", "bpm": 100, "energie": 0.5}, "look": "cinema",
                  "goodies": [], "transitions": ["t_fondu_noir", "t_zoom"], "plan_s": (3, 8)},
}


def classer(fiches, indices=None):
    """Type de video deduit des fiches (et des indices : noms de fichiers, texte lu, mots de l'utilisateur)."""
    indices = (indices or "").lower()
    if any(m in indices for m in ("avion", "vol ", "pilote", "f-g", "aero", "decoll", "atterr", "cockpit")):
        return "vol"
    if any(m in indices for m in ("pharma", "promo", "offre", "ordonnance")):
        return "annonce"
    if not fiches:
        return "generique"
    videos = [f for f in fiches if f.get("genre") == "video"]
    if not videos:
        return "generique"
    courts = [f for f in videos if f["duree"] <= 7]
    muets = [f for f in videos if (f.get("son") or {}).get("muet")]
    petits = [f for f in videos if (f.get("video") or {}).get("largeur", 1920) < 900 or (f.get("video") or {}).get("largeur", 0) in (1952,)]
    if len(courts) >= max(2, 0.7 * len(videos)) and (len(muets) >= 0.5 * len(videos) or len(petits) >= 0.5 * len(videos)):
        return "clip_ia"
    nuits = [f for f in videos if (f.get("lumiere") or {}).get("nuit")]
    visages = sum((f.get("visages") or {}).get("nb_max", 0) for f in videos)
    bleu = sum(dict(f.get("couleurs") or {}).get("bleu", 0) + dict(f.get("couleurs") or {}).get("cyan", 0) for f in videos) / len(videos)
    mouvement = sum((sum(f.get("mouvement") or [0]) / max(1, len(f.get("mouvement") or [1]))) for f in videos) / len(videos)
    if len(nuits) >= 0.6 * len(videos) and visages <= 1:
        return "visite"
    if bleu > 0.45 and mouvement > 12:
        return "vol"
    if visages >= 2 or (visages >= 1 and sum(f["duree"] for f in videos) < 90):
        return "portrait"
    return "generique"


def proposer(medias, params=None, indices="", format_=None, duree_cible=None, type_force=None):
    """Recette sans IA, a partir des medias du projet (chacun avec m["analyse"] = fiche)."""
    params = params or {}
    fiches = [dict(m.get("analyse") or {}, media=m["id"], nom=m["nom"], genre=m.get("genre")) for m in medias]
    videos = sorted([f for f in fiches if f.get("genre") == "video" and f.get("duree")], key=lambda f: ((f.get("date") or ""), (f.get("heure") or ""), f["nom"]))
    images = [f for f in fiches if f.get("genre") == "image"]
    musiques = [f for f in fiches if f.get("genre") == "audio"]
    type_ = type_force or classer(fiches, indices + " " + " ".join(f["nom"] for f in fiches))
    T = TYPES[type_]
    vertical = format_ == "9:16" if format_ else (sum(1 for f in videos if f.get("vertical")) > len(videos) / 2 if videos else False)
    fmt = format_ or ("9:16" if vertical else "16:9")
    cible = duree_cible or (55 if fmt == "9:16" else min(240, max(45, sum(f["duree"] for f in videos) * 0.45)))
    pmin, pmax = T["plan_s"]
    if fmt == "9:16":
        pmin, pmax = pmin * 0.7, pmax * 0.7
    chaine = params.get("chaine_nom") or ""
    recette = {"type": type_, "type_nom": T["nom"], "format": fmt, "duree_cible": round(cible), "resume": "",
               "logo": {"modele": T["logo"], "texte": chaine or _("Ma vidéo"), "duree": 2.5, "pourquoi": _("ouverture courte, dans l'esprit du sujet")},
               "musique": dict(T["musique"], media=(musiques[0]["media"] if musiques else None), pourquoi=_("ambiance adaptée au type de vidéo")),
               "look": T["look"], "plans": [], "textes": [], "goodies": [], "publication": {}, "plans_a_generer": [], "a_jeter": []}
    # ---- plans : decoupage utile de chaque rush
    budget = cible
    t = 0.0
    for i, f in enumerate(videos):
        segments = _segments_utiles(f, pmin, pmax)
        part = budget * (f["duree"] / max(1, sum(x["duree"] for x in videos)))
        pris = 0.0
        for k, (a, b, pourquoi) in enumerate(segments):
            if pris >= part and len(recette["plans"]) > 2:
                break
            d = b - a
            vitesse = 1.0
            if f.get("deja_monte"):
                vitesse = 1.0
            elif d > pmax * 1.5 and "mouvement" in pourquoi:
                vitesse = 2.0 if type_ != "vol" else 1.0
            effets = []
            if k == 0 and i == 0 and type_ == "vol":
                effets.append({"id": "ciel_altitude", "params": {}})
            if type_ == "visite" and (f.get("lumiere") or {}).get("nuit"):
                effets.append({"id": "nuit_chaude", "params": {}})
                if "lumière" in pourquoi:
                    effets.append({"id": "glow", "params": {"rayon": 10, "intensite": 0.5}})
            if type_ == "clip_ia":
                effets.append({"id": "nettete", "params": {}})
            transition = None
            if recette["plans"]:
                transition = {"id": T["transitions"][len(recette["plans"]) % len(T["transitions"])], "params": {}}
            recette["plans"].append({"media": f["media"], "nom": f["nom"], "src_debut": round(a, 2), "src_fin": round(b, 2), "vitesse": vitesse,
                                     "effets": effets, "transition": transition, "cadrage": "remplir" if fmt == "9:16" or not f.get("vertical") else "contenir_flou",
                                     "pourquoi": pourquoi, "debut": round(t, 2)})
            t += d / vitesse
            pris += d / vitesse
        for (a, b) in ((f.get("lumiere") or {}).get("passages_noirs") or [])[:5]:
            recette["a_jeter"].append({"media": f["media"], "de": a, "a": b, "pourquoi": _("passage noir")})
    for f in images[:4]:
        recette["plans"].append({"media": f["media"], "nom": f["nom"], "src_debut": 0, "src_fin": 4, "vitesse": 1.0, "effets": [{"id": "glow", "params": {}}],
                                 "transition": {"id": "t_zoom", "params": {}}, "cadrage": "remplir", "pourquoi": _("photo importée"), "debut": round(t, 2)})
        t += 4
    duree = t
    # ---- textes
    titre = _titre(type_, fiches, chaine)
    recette["textes"].append({"texte": titre, "debut": 0.6, "fin": min(4.2, max(2.5, duree * 0.08)), "animation": "neon" if type_ in ("vol", "clip_ia") else "fondu",
                              "style": "titre", "x": 0.5, "y": 0.5 if fmt == "9:16" else 0.78, "pourquoi": _("titre d'ouverture")})
    dates = sorted({f.get("date") for f in videos if f.get("date")})
    if dates:
        recette["textes"].append({"texte": _date_fr(dates[0]) + (" → " + _date_fr(dates[-1]) if len(dates) > 1 else ""), "debut": 0.8, "fin": 3.8,
                                  "animation": "fondu", "style": "titre", "taille": 0.55, "x": 0.5, "y": 0.9, "pourquoi": _("date des prises")})
    for f in videos:
        for v in ((f.get("visages") or {}).get("instants") or [])[:1]:
            plan = next((p for p in recette["plans"] if p["media"] == f["media"] and p["src_debut"] <= v["t"] <= p["src_fin"]), None)
            if plan:
                d0 = plan["debut"] + (v["t"] - plan["src_debut"]) / plan["vitesse"]
                recette["textes"].append({"texte": _("le Pilote") if type_ == "vol" else _("Moi"), "debut": round(max(0, d0 - 0.5), 2), "fin": round(min(duree, d0 + 3), 2),
                                          "animation": "fondu", "style": "etiquette", "suivre_visage": True, "media": f["media"], "boite": v["boite"],
                                          "pourquoi": _("étiquette accrochée à la personne")})
                break
    recette["textes"].append({"texte": chaine or _("Merci d'avoir regardé"), "debut": round(max(0, duree - 2.5), 2), "fin": round(duree, 2), "animation": "zoom",
                              "style": "titre", "x": 0.5, "y": 0.5, "pourquoi": _("écran de fin")})
    # ---- goodies
    for k, g in enumerate(T["goodies"]):
        recette["goodies"].append({"genre": g, "debut": round(min(duree, 4.0), 2), "fin": round(max(5.0, duree - 3), 2), "x": 0.12 + 0.76 * (k % 2), "y": 0.85 if fmt != "9:16" else 0.78 - 0.14 * k,
                                   "taille": 0.2 if fmt != "9:16" else 0.16, "style": "cadran", "pourquoi": _("instrument dans l'esprit de la vidéo (valeurs à saisir ou trace GPS)")})
    # ---- publication
    recette["publication"] = {"titre": titre, "description": _("Montage réalisé avec PhilCut.") + (f" {chaine}" if chaine else ""),
                              "mots_clefs": [T["nom"].lower()] + ([_("aviation"), _("vol")] if type_ == "vol" else [])}
    if type_ == "vol":
        recette["plans_a_generer"].append({"usage": "intro", "duree": 5, "consigne": _("Plan aérien cinématographique au-dessus de la Côte d'Azur au petit matin, avion léger de tourisme, lumière dorée, mouvement de caméra lent.")})
    recette["duree"] = round(duree, 1)
    recette["resume"] = _("{type} · {n} plans · {d} · format {f}", type=T["nom"], n=len(recette["plans"]), d=_duree_txt(duree), f=fmt)
    return recette


def _segments_utiles(f, pmin, pmax):
    """[(debut, fin, pourquoi)] dans le rush : evite les passages noirs et les silences inutiles, suit les coupes."""
    d = f["duree"]
    noirs = ((f.get("lumiere") or {}).get("passages_noirs") or [])
    bornes = [0.0] + [c for c in (f.get("coupes") or []) if 0.5 < c < d - 0.5] + [d]
    out = []
    for a, b in zip(bornes, bornes[1:]):
        # retire les passages noirs
        morceaux = [(a, b)]
        for (na, nb) in noirs:
            nouveaux = []
            for (x, y) in morceaux:
                if nb <= x or na >= y:
                    nouveaux.append((x, y))
                else:
                    if na - x >= 1.0:
                        nouveaux.append((x, na))
                    if y - nb >= 1.0:
                        nouveaux.append((nb, y))
            morceaux = nouveaux
        for (x, y) in morceaux:
            if y - x < 1.0:
                continue
            if y - x <= pmax:
                out.append((x, y, _("plan entier") if f.get("deja_monte") else _("passage retenu")))
            else:
                # long plan : on garde le debut et un milieu, a la longueur maximale
                out.append((x, min(y, x + pmax), _("début du plan")))
                milieu = (x + y) / 2
                if y - x > 3 * pmax:
                    out.append((milieu, min(y, milieu + pmax * 0.8), _("milieu du plan (mouvement)")))
                if y - x > 2 * pmax:
                    out.append((max(x, y - pmax * 0.7), y, _("fin du plan")))
    return out or [(0.0, min(d, pmax), _("début"))]


def _titre(type_, fiches, chaine):
    noms = " ".join(f.get("nom", "") for f in fiches).lower()
    if type_ == "vol":
        return _("Survol")
    if type_ == "visite":
        return _("Quand la nuit tombe")
    if type_ == "portrait":
        return _("Portrait")
    if type_ == "clip_ia":
        return _("Instants")
    if type_ == "annonce":
        return chaine or _("Cette semaine")
    return chaine or _("Souvenirs")


def _date_fr(iso):
    try:
        a, m, j = iso.split("-")
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
        return f"{int(j)} {mois[int(m) - 1]} {a}"
    except (ValueError, IndexError):
        return iso


def _duree_txt(s):
    from .moteur import duree_texte
    return duree_texte(s)


# ------------------------------------------------------------------ application au projet
def appliquer(recette, projet, params=None, choix=None, remplacer=True):
    """Pose la recette dans le projet. choix : {"logo": bool, "musique": bool, "plans": bool, "textes": bool, "goodies": bool, "look": bool,
    "plan:<i>": bool, "texte:<i>": bool, "goodie:<i>": bool} ; absent = accepte."""
    choix = choix or {}
    ok = lambda k: choix.get(k, True)
    projet.marquer()
    if remplacer:
        projet.d["clips"], projet.d["titres"], projet.d["goodies"] = [], [], []
    if recette.get("format") and recette["format"] in ("16:9", "9:16", "1:1", "4:5") and remplacer:
        projet.d["format"] = recette["format"]
    t = 0.0
    decalage = 0.0
    if ok("logo") and recette.get("logo"):
        g = projet.ajouter_goodie("logo_intro", 0.0, float(recette["logo"].get("duree", 2.5)), x=0.5, y=0.5, taille=0.5, style="hud",
                                  options={"texte": recette["logo"].get("texte", ""), "modele": recette["logo"].get("modele", "trace")})
        g["genre"] = "bandeau"           # rendu comme bandeau texte tant que la Fabrique n'a pas genere le logo anime
        decalage = float(recette["logo"].get("duree", 2.5))
        t = decalage
    if ok("plans"):
        for i, p in enumerate(recette.get("plans") or []):
            if not ok(f"plan:{i}") or not projet.media(p["media"]):
                continue
            c = projet.ajouter_clip(p["media"], "video", t, p.get("src_debut", 0), p.get("src_fin"), p.get("vitesse", 1.0))
            c["effets"] = copy.deepcopy(p.get("effets") or [])
            if ok("look") and recette.get("look") and not any(e["id"] == recette["look"] for e in c["effets"]) and recette["look"] in ("ciel_altitude", "nuit_chaude", "cinema", "cosy", "epure", "vintage"):
                c["effets"].append({"id": recette["look"], "params": {}})
            c["transition"] = copy.deepcopy(p.get("transition")) if p.get("transition") else None
            c["ajustement"] = p.get("cadrage", "remplir")
            from .projet import fin_clip
            t = fin_clip(c)
    duree = max(t, projet.duree())
    if ok("textes"):
        for i, x in enumerate(recette.get("textes") or []):
            if not ok(f"texte:{i}"):
                continue
            d0, f0 = float(x["debut"]) + decalage, float(x["fin"]) + decalage
            if x.get("style") == "titre" and "fin" in x and recette.get("duree") and abs(float(x["fin"]) - float(recette["duree"])) < 0.05:
                d0, f0 = max(0, duree - 2.5), duree       # ecran de fin : cale sur la vraie fin
            titre = projet.ajouter_titre(x["texte"], d0, f0, style=x.get("style", "titre"), animation=x.get("animation", "fondu"),
                                         x=float(x.get("x", 0.5)), y=float(x.get("y", 0.85)), taille=float(x.get("taille", 1.0)))
            if x.get("suivre_visage") and x.get("boite"):
                bx, by, bw, bh = x["boite"]
                titre["suivi"] = {"media": x.get("media"), "boite": x["boite"], "positions": [(d0, bx + bw / 2, by), (f0, bx + bw / 2, by)]}
    if ok("goodies"):
        for i, g in enumerate(recette.get("goodies") or []):
            if not ok(f"goodie:{i}"):
                continue
            projet.ajouter_goodie(g["genre"], float(g["debut"]) + decalage, min(duree, float(g["fin"]) + decalage), x=float(g.get("x", 0.88)), y=float(g.get("y", 0.85)),
                                  taille=float(g.get("taille", 0.2)), style=g.get("style", "cadran"), valeurs=g.get("valeurs") or [])
    if ok("musique") and (recette.get("musique") or {}).get("media") and projet.media(recette["musique"]["media"]):
        m = projet.media(recette["musique"]["media"])
        dm = float((m.get("fiche") or {}).get("duree") or duree)
        c = projet.ajouter_clip(m["id"], "audio", 0.0, 0.0, min(dm, duree))
        c["volume"] = 0.8
    projet.d["recette"] = copy.deepcopy(recette)
    projet.d["ducking"] = True
    projet.modifie = True
    return projet


def suivre_visage(projet, titre, params=None, pas=0.2):
    """Etiquette accrochée : la personne de titre["suivi"]["boite"] est suivie (moteur commun app/suivi.py)."""
    from . import suivi
    s = titre.get("suivi") or {}
    m = projet.media(s.get("media")) if s.get("media") else None
    if not m or not s.get("boite"):
        return False
    try:
        suivi.accrocher(projet, titre, m, s["boite"], decalage=(0.0, -0.5))
    except suivi.ErreurSuivi:
        return False
    return len(titre["suivi"].get("positions") or []) > 1
