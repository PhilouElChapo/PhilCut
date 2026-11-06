"""L'assistant de montage : analyse en local, decide avec peu de mots, applique en local.

Trois niveaux (Preferences > Assistant) : recettes sans IA (regles), IA locale (portable, sur ce poste), IA cloud (Claude ou
Gemini avec la clef). Dans tous les cas la sortie est la meme recette JSON (recettes.py), que le volet
Proposition montre element par element avec une case a cocher et un bouton « autre idée ».
"""
import json

from . import fiche as F, ia, ia_locale, recettes
from .langue import _

CONSIGNES = """Tu es l'assistant de montage de PhilCut, un logiciel de montage vidéo simple et « effet wahou ».
On te donne la fiche technique de chaque rush (durée, format, cadence, lumière, son, coupes, visages, couleurs, date, lieu)
et quelques vignettes. Tu ne vois pas la vidéo entière. Propose un montage complet, concret et sobre, en français.

Réponds UNIQUEMENT par un objet JSON avec ces clefs :
- "type": un de vol, visite, portrait, clip_ia, annonce, generique
- "titre": titre court de la vidéo
- "resume": une phrase sur l'idée du montage
- "format": "16:9" ou "9:16"
- "logo": {"modele": slam|decoupe|contour|glitch_net|masque|verre|espacement|cinema|horizon|lumiere, "texte": "...", "duree": secondes, "pourquoi": "..."}
- "musique": {"ambiance": energique|douce|cinema|chaleureuse|mysterieuse|legere, "bpm": nombre, "energie": 0..1, "pourquoi": "..."}
- "look": un effet de look parmi ciel_altitude, nuit_chaude, cinema, cosy, epure, vintage, noir_blanc, y2k ou ""
- "plans": liste ordonnée de {"media": id, "src_debut": s, "src_fin": s, "vitesse": 0.25..8, "effets": [ids], "transition": id ou null, "cadrage": remplir|contenir_noir|contenir_flou, "pourquoi": "..."}
   Effets possibles : glow, glitch, flou_mouvement, ralenti_fluide, stabiliser, debruiter, eclaircir, nettete, pluie_code, matrix_vert, feu_artifice, eclairs, fuite_lumiere, separation_rvb, hyperlapse, bullet_time
   Transitions possibles : t_fondu_enchaine, t_fondu_noir, t_fondu_blanc, t_dissolution, t_glisse, t_cercle, t_pixels, t_flou_fondu, t_diagonale, t_puzzle, t_explosion, t_glitch, t_zoom, t_balayage, t_code
- "textes": liste de {"texte": "...", "debut": s (dans le montage), "fin": s, "animation": fondu|zoom|glisse|machine|neon|feu|tournoyant|cinetique, "style": titre|etiquette, "x": 0..1, "y": 0..1, "taille": 0.5..2, "suivre_visage": bool, "media": id si étiquette, "pourquoi": "..."}
- "goodies": liste de {"genre": altimetre|anemometre|compas|horizon|variometre|chrono|immatriculation|horloge|boussole|altitude|distance|compte_a_rebours|date|bandeau, "debut": s, "fin": s, "x": 0..1, "y": 0..1, "taille": 0.1..0.4, "pourquoi": "..."}
- "publication": {"titre": "...", "description": "...", "mots_clefs": [...]}
- "plans_a_generer": liste de {"usage": intro|transition|illustration|fin, "duree": s, "consigne": "consigne prête pour un générateur vidéo (Flow, Veo)"}
- "a_jeter": liste de {"media": id, "de": s, "a": s, "pourquoi": "..."}

Règles : respecte la durée cible ; chaque plan dure 2 à 10 s (plus pour un vol) ; évite les passages noirs et les silences inutiles ;
les effets doivent être cohérents avec le sujet (pas de Matrix sur un jardin illuminé sans raison) ; une étiquette accrochée à une
personne seulement si un visage est signalé ; pas plus de 3 Goodies ; explique chaque choix en quelques mots dans "pourquoi"."""


def niveau(params):
    return (params or {}).get("assistant_niveau") or "recettes"


def preparer(projet, params, progression=None):
    """Analyse locale de chaque media qui n'a pas encore sa fiche. Renvoie la liste des fiches (avec vignettes)."""
    fiches = []
    medias = [m for m in projet.medias]
    for i, m in enumerate(medias):
        if progression:
            progression(i / max(1, len(medias)), m["nom"])
        if m.get("analyse") and m.get("genre") != "video":
            fiches.append(dict(m["analyse"], media=m["id"], nom=m["nom"], genre=m["genre"], vignettes=[]))
            continue
        f = F.analyser(m["chemin"], params, progression=(lambda fr, t, i=i, n=len(medias): progression((i + fr) / n, t)) if progression else None)
        m["analyse"] = {k: v for k, v in f.items() if k != "vignettes"}
        f.update(media=m["id"], nom=m["nom"], genre=m["genre"])
        fiches.append(f)
    if progression:
        progression(1.0, "")
    return fiches


def proposer(projet, params, fiches=None, indices="", format_=None, duree_cible=None, niveau_force=None, rapporter=None):
    """La recette, selon le niveau choisi. Toujours une recette sans IA d'abord : elle sert de secours et d'exemple."""
    niv = niveau_force or niveau(params)
    base = recettes.proposer(projet.medias, params, indices=indices, format_=format_, duree_cible=duree_cible)
    base["source"] = "recettes"
    if niv == "recettes":
        return base
    fiches = fiches or [dict(m.get("analyse") or {}, media=m["id"], nom=m["nom"], genre=m["genre"]) for m in projet.medias]
    texte = _texte_demande(projet, fiches, base, indices, format_, duree_cible)
    images = []
    for f in fiches:
        for v in (f.get("vignettes") or [])[:4]:
            images.append(v)
    images = images[:12]
    try:
        if niv == "locale":
            rapporter and rapporter(_("IA locale : envoi de la fiche au modèle…"))
            modele = ia_locale.modele_actif(params)
            if not modele:
                raise RuntimeError(_("Aucun modèle local : cochez-en un dans Préférences › IA locale."))
            r = ia_locale.generer(modele, texte, images, systeme=CONSIGNES, json_attendu=True, params=params)
            d = ia.lire_json(r)
            source = "locale:" + modele
        else:
            rapporter and rapporter(_("IA cloud ({m}) : envoi de la fiche et de {n} vignettes…", m=ia.nom_moteur(params), n=len(images)))
            d = ia.demander(params, CONSIGNES, texte, images=images, json_attendu=True, max_jetons=6000)
            source = "cloud:" + ia.nom_moteur(params)
    except Exception as e:        # noqa: BLE001 : on garde la recette sans IA, avec le message
        base["avertissement"] = _("L'IA n'a pas répondu ({e}) : voici la recette sans IA.", e=str(e)[:200])
        return base
    r = _fusionner(base, d, projet)
    r["source"] = source
    return r


def _texte_demande(projet, fiches, base, indices, format_, duree_cible):
    lignes = [_("Projet : {n}", n=projet.nom)]
    if indices:
        lignes.append(_("Indications de l'utilisateur : {i}", i=indices))
    lignes.append(_("Format souhaité : {f}", f=format_ or base.get("format")))
    lignes.append(_("Durée cible : environ {d} s", d=duree_cible or base.get("duree_cible")))
    lignes.append("")
    lignes.append(_("Fiches des rushes (JSON, une par ligne ; « media » est l'identifiant à réutiliser) :"))
    for f in fiches:
        lignes.append(F.pour_ia({k: v for k, v in f.items() if k not in ("vignettes", "chemin", "instants_vignettes")}))
    lignes.append("")
    lignes.append(_("Les vignettes jointes sont, dans l'ordre, des images de chaque rush (jusqu'à 4 par rush)."))
    lignes.append(_("Recette de référence produite sans IA (à améliorer, pas à recopier) :"))
    lignes.append(json.dumps({k: v for k, v in base.items() if k in ("type", "plans", "textes", "goodies", "musique", "logo", "look")}, ensure_ascii=False)[:6000])
    return "\n".join(lignes)


def _fusionner(base, d, projet):
    """Verifie la reponse de l'IA : identifiants de medias valides, bornes dans la duree, champs obligatoires ; complete avec la base."""
    r = dict(base)
    if not isinstance(d, dict):
        return r
    ids = {m["id"] for m in projet.medias}
    durees = {m["id"]: float((m.get("fiche") or {}).get("duree") or 0) for m in projet.medias}
    for k in ("type", "titre", "resume", "format", "logo", "musique", "look", "publication", "plans_a_generer", "a_jeter"):
        if d.get(k) is not None:
            r[k] = d[k]
    if r.get("musique") and base.get("musique", {}).get("media") and not r["musique"].get("media"):
        r["musique"]["media"] = base["musique"]["media"]
    plans = []
    t = 0.0
    for p in d.get("plans") or []:
        if not isinstance(p, dict) or p.get("media") not in ids:
            continue
        dm = durees.get(p["media"]) or 1e9
        a = max(0.0, float(p.get("src_debut", 0) or 0))
        b = min(dm, float(p.get("src_fin", a + 4) or a + 4))
        if b - a < 0.3:
            continue
        v = max(0.1, min(16.0, float(p.get("vitesse", 1.0) or 1.0)))
        eff = [{"id": e, "params": {}} if isinstance(e, str) else e for e in (p.get("effets") or []) if (e if isinstance(e, str) else e.get("id")) in _IDS_EFFETS]
        tr = p.get("transition")
        tr = {"id": tr, "params": {}} if isinstance(tr, str) and tr in _IDS_EFFETS else (tr if isinstance(tr, dict) and tr.get("id") in _IDS_EFFETS else None)
        plans.append({"media": p["media"], "nom": next((m["nom"] for m in projet.medias if m["id"] == p["media"]), ""), "src_debut": round(a, 2), "src_fin": round(b, 2),
                      "vitesse": v, "effets": eff, "transition": tr if plans else None, "cadrage": p.get("cadrage") if p.get("cadrage") in ("remplir", "contenir_noir", "contenir_flou") else "remplir",
                      "pourquoi": str(p.get("pourquoi", ""))[:200], "debut": round(t, 2)})
        t += (b - a) / v
    if plans:
        r["plans"] = plans
        r["duree"] = round(t, 1)
    duree = r.get("duree") or base.get("duree") or 60
    textes = []
    for x in d.get("textes") or []:
        if not isinstance(x, dict) or not x.get("texte"):
            continue
        d0 = max(0.0, float(x.get("debut", 0) or 0))
        f0 = min(duree, float(x.get("fin", d0 + 3) or d0 + 3))
        if f0 - d0 < 0.3:
            continue
        tx = {"texte": str(x["texte"])[:120], "debut": round(d0, 2), "fin": round(f0, 2), "animation": x.get("animation") if x.get("animation") in _ANIMS else "fondu",
              "style": "etiquette" if x.get("style") == "etiquette" else "titre", "x": _b(x.get("x", 0.5)), "y": _b(x.get("y", 0.85)),
              "taille": max(0.4, min(2.5, float(x.get("taille", 1.0) or 1.0))), "pourquoi": str(x.get("pourquoi", ""))[:200]}
        if x.get("suivre_visage") and x.get("media") in ids:
            boite = None
            for m in projet.medias:
                if m["id"] == x["media"]:
                    inst = ((m.get("analyse") or {}).get("visages") or {}).get("instants") or []
                    boite = inst[0]["boite"] if inst else None
            if boite:
                tx.update(suivre_visage=True, media=x["media"], boite=boite)
        textes.append(tx)
    if textes:
        r["textes"] = textes
    goodies = []
    for g in (d.get("goodies") or [])[:3]:
        if isinstance(g, dict) and g.get("genre") in _IDS_GOODIES:
            goodies.append({"genre": g["genre"], "debut": round(max(0.0, float(g.get("debut", 0) or 0)), 2), "fin": round(min(duree, float(g.get("fin", duree) or duree)), 2),
                            "x": _b(g.get("x", 0.88)), "y": _b(g.get("y", 0.85)), "taille": max(0.08, min(0.5, float(g.get("taille", 0.2) or 0.2))), "style": "cadran",
                            "pourquoi": str(g.get("pourquoi", ""))[:200]})
    r["goodies"] = goodies if (d.get("goodies") is not None) else r.get("goodies", [])
    r["resume"] = r.get("resume") or base.get("resume")
    return r


def _b(v):
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.5


from . import effets as _E, goodies as _G       # noqa: E402
_IDS_EFFETS = set(_E.CATALOGUE)
_IDS_GOODIES = set(_G.GENRES)
_ANIMS = {"fondu", "zoom", "glisse", "machine", "neon", "feu", "tournoyant", "cinetique", "aucune"}


def autre_idee(projet, params, recette, element, rapporter=None):
    """Une autre proposition pour un seul element (ex. "logo", "musique", "texte:0", "plan:2")."""
    niv = niveau(params)
    if niv == "recettes":
        import random
        r = dict(recette)
        if element == "logo":
            modeles = ["slam", "decoupe", "contour", "glitch_net", "masque", "verre", "espacement", "cinema", "horizon", "lumiere"]
            r["logo"] = dict(recette["logo"], modele=random.choice([m for m in modeles if m != recette["logo"].get("modele")]))
        elif element == "musique":
            amb = ["energique", "douce", "cinema", "chaleureuse", "mysterieuse", "legere"]
            r["musique"] = dict(recette["musique"], ambiance=random.choice([a for a in amb if a != recette["musique"].get("ambiance")]))
        elif element.startswith("texte:"):
            i = int(element.split(":")[1])
            anims = ["fondu", "zoom", "glisse", "machine", "neon", "feu", "tournoyant", "cinetique"]
            r["textes"] = list(recette["textes"])
            r["textes"][i] = dict(r["textes"][i], animation=random.choice([a for a in anims if a != r["textes"][i].get("animation")]))
        elif element.startswith("plan:"):
            i = int(element.split(":")[1])
            trs = ["t_fondu_enchaine", "t_fondu_noir", "t_fondu_blanc", "t_cercle", "t_glisse", "t_puzzle", "t_glitch", "t_zoom", "t_balayage", "t_code"]
            r["plans"] = list(recette["plans"])
            cur = (r["plans"][i].get("transition") or {}).get("id")
            r["plans"][i] = dict(r["plans"][i], transition={"id": random.choice([t for t in trs if t != cur]), "params": {}})
        return r
    texte = _("Voici la recette actuelle (JSON). Propose une AUTRE idée seulement pour l'élément « {e} », en gardant tout le reste identique. "
              "Réponds par la recette complète en JSON.\n\n{r}", e=element, r=json.dumps(recette, ensure_ascii=False)[:12000])
    try:
        if niv == "locale":
            d = ia.lire_json(ia_locale.generer(ia_locale.modele_actif(params), texte, systeme=CONSIGNES, json_attendu=True, params=params))
        else:
            d = ia.demander(params, CONSIGNES, texte, json_attendu=True, max_jetons=6000)
    except Exception as e:        # noqa: BLE001
        r = dict(recette)
        r["avertissement"] = str(e)[:200]
        return r
    return _fusionner(recette, d, projet)
