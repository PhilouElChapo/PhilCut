"""« Dites-le en clair » (0.4.4) : une phrase devient des actions de montage, montrées avant d'être faites.

« mets une musique calme et coupe-la à la fin de la vidéo », « titre Notre week-end au début », « effet vintage sur tous
les plans », « ralenti sur le plan 2 », « une flèche rouge à 5 s »… Trois façons de comprendre, comme l'assistant :
- sans IA : des règles reconnaissent les demandes courantes (gratuit, instantané, rien ne sort du poste) ;
- IA locale : le modèle du poste traduit la phrase en actions (rien n'est envoyé) ;
- IA cloud : Claude ou Gemini, avec votre clef, le coût affiché et confirmé avant l'envoi.
Dans tous les cas la sortie est la même liste d'actions JSON ; la fenêtre les montre, chacune cochable, et tout est
fait en une seule étape d'annulation (Ctrl+Z défait tout).
"""
import json, re, unicodedata

from .langue import _

ACTIONS = {
    "musique": _("Musique"), "couper_musique": _("Couper la musique à la fin de la vidéo"), "fondus_musique": _("Fondus de la musique"),
    "volume": _("Volume"), "effet": _("Effet"), "transition": _("Transition"), "vitesse": _("Vitesse"), "texte": _("Texte"),
    "fleche": _("Flèche"), "goodie": _("Goodie"), "couper": _("Couper"), "look": _("Look"),
}

CONSIGNE = """Tu traduis une demande de montage vidéo en actions pour le logiciel PhilCut. Réponds UNIQUEMENT en JSON :
{"actions": [ ... ]} avec, pour chaque action, "action" parmi :
- "musique" {"ambiance": energique|calme|cinema|joyeuse|acoustique|piano|electro|aventure}
- "couper_musique" {} (la musique s'arrête à la fin de la vidéo, avec un fondu)
- "fondus_musique" {"entree": s, "sortie": s}
- "volume" {"piste": "musique"|"video"|"voix", "valeur": 0..2}
- "effet" {"id": identifiant, "plans": "tous"|"selection"|[numéros de plans à partir de 1]}
- "transition" {"id": identifiant, "plans": "tous"|[numéros]}
- "vitesse" {"valeur": 0.25..8, "plans": "selection"|[numéros]}
- "texte" {"texte": "...", "debut": s, "fin": s, "style": "titre"|"simple"|"encadre", "y": 0..1}
- "fleche" {"debut": s, "fin": s, "x": 0..1, "y": 0..1, "angle": degrés, "couleur": "#rrggbb", "style": "droite"|"courbe"}
- "goodie" {"genre": identifiant, "debut": s, "fin": s}
- "couper" {"t": s}
- "look" {"id": identifiant d'effet de look}
Utilise seulement les identifiants listés plus bas. N'invente pas d'action. Si un temps n'est pas dit, laisse-le absent."""


def _sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def _temps(txt):
    """« 5 s », « 1 min 20 », « 1:20 », « au début », « à la fin » → secondes (ou mot clef)."""
    t = _sans_accents(txt)
    m = re.search(r"(\d+):(\d{1,2})", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"(\d+)\s*min(?:utes?)?\s*(\d+)?", t)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2) or 0)
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:s\b|sec|seconde)", t)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _plans(t):
    if re.search(r"tous les plans|toute la video|partout|chaque plan", t):
        return "tous"
    m = re.findall(r"plans?\s+(\d+(?:\s*(?:,|et)\s*\d+)*)", t)
    if m:
        return [int(x) for x in re.findall(r"\d+", m[0])]
    return "selection"


_COULEURS = {"rouge": "#ff3030", "blanc": "#ffffff", "blanche": "#ffffff", "jaune": "#ffd21f", "vert": "#2ecc40", "verte": "#2ecc40",
             "bleu": "#1e90ff", "bleue": "#1e90ff", "orange": "#ff8c1a", "noir": "#000000", "noire": "#000000", "rose": "#ff4fa3"}


def regles(phrase):
    """Ce que l'on comprend sans IA. Renvoie une liste d'actions (éventuellement vide)."""
    from . import effets as E
    out = []
    morceaux = re.split(r"\s*(?:,|;|\bpuis\b|\bet ensuite\b|\bensuite\b|\bet\b(?=\s+(?:mets|met|ajoute|coupe|fais|place|pose|enleve|baisse|monte)))\s*",
                        phrase.strip(), flags=re.I)
    noms_effets = {}
    for k, e in E.CATALOGUE.items():
        noms_effets[_sans_accents(e[1])] = k
        noms_effets[_sans_accents(k.replace("_", " "))] = k
    for brut in [m for m in morceaux if m and m.strip()]:
        t = _sans_accents(brut)
        tm = _temps(t)
        if re.search(r"\b(musique|son de fond|bande son|morceau)\b", t):
            if re.search(r"coupe|arrete|termine|finir|fin de la video|raccourci", t):
                out.append({"action": "couper_musique"})
            elif re.search(r"fondu|fade", t):
                n = [float(x.replace(",", ".")) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*s", t)]
                out.append({"action": "fondus_musique", "entree": n[0] if n else 2.0, "sortie": n[1] if len(n) > 1 else (n[0] if n else 3.0)})
            elif re.search(r"baisse|moins fort|plus bas|doucement", t):
                out.append({"action": "volume", "piste": "musique", "valeur": 0.4})
            elif re.search(r"monte|plus fort", t):
                out.append({"action": "volume", "piste": "musique", "valeur": 1.2})
            else:
                amb = next((a for mots, a in (("calme|douce|doux|zen|relax", "calme"), ("energ|dynamique|rythm|punchy|rock", "energique"),
                                              ("cinema|epique|film", "cinema"), ("joyeu|gai|happy", "joyeuse"), ("piano", "piano"),
                                              ("guitare|acoustique", "acoustique"), ("electro", "electro"), ("aventure|vol|avion", "aventure"))
                            if re.search(mots, t)), "")
                out.append({"action": "musique", "ambiance": amb})
                if re.search(r"fin de la video|coupe", t):
                    out.append({"action": "couper_musique"})
            continue
        if re.search(r"coupe|arrete|termine", t) and re.search(r"fin de la video|fin du montage|a la fin", t):
            out.append({"action": "couper_musique"})
            continue
        if re.search(r"\bfleche", t):
            couleur = next((v for k, v in _COULEURS.items() if re.search(rf"\b{k}\b", t)), "#ff3030")
            d = tm if tm is not None else None
            a = {"action": "fleche", "couleur": couleur, "style": "courbe" if re.search(r"courbe|dessinee|main", t) else "droite"}
            if d is not None:
                a["debut"] = d
            if "gauche" in t:
                a["angle"] = 180
            elif "haut" in t:
                a["angle"] = -90
            elif "bas" in t:
                a["angle"] = 90
            out.append(a)
            continue
        m = re.search(r"(?:titre|texte|[ée]cris|[ée]crire|l[ée]gende)\s*[:«\"']?\s*(.+?)\s*[»\"']?\s*(?:au debut|a la fin|a \d|$)", brut, re.I)
        if m and re.search(r"titre|texte|ecri|legende", t):
            q = re.search(r"[«\"“]\s*(.+?)\s*[»\"”]", brut)
            txt = q.group(1) if q else re.sub(r"^(?:titre|texte)\s*", "", m.group(1), flags=re.I).strip(" «»\"'")
            # le texte d'origine (accents compris) entre les mots repérés
            a = {"action": "texte", "texte": txt, "style": "titre" if "titre" in t else "simple"}
            if "au debut" in t:
                a["debut"] = 0.0
            elif "a la fin" in t:
                a["debut"] = "fin"
            elif tm is not None:
                a["debut"] = tm
            if txt:
                out.append(a)
            continue
        if re.search(r"ralenti|ralentis|au ralenti", t):
            out.append({"action": "vitesse", "valeur": 0.5, "plans": _plans(t)})
            continue
        if re.search(r"accelere|plus vite|timelapse|x2\b|x4\b", t):
            v = 4.0 if re.search(r"x4|timelapse", t) else 2.0
            out.append({"action": "vitesse", "valeur": v, "plans": _plans(t)})
            continue
        if re.search(r"\bcoupe\b|\bcouper\b", t) and tm is not None:
            out.append({"action": "couper", "t": tm})
            continue
        eid = next((k for nom, k in sorted(noms_effets.items(), key=lambda kv: -len(kv[0])) if len(nom) > 3 and nom in t), None)
        if eid:
            fam = E.CATALOGUE[eid][0]
            out.append({"action": "transition" if fam == "transition" else ("look" if fam == "look" and "tous" in _plans(t) else "effet"),
                        "id": eid, "plans": _plans(t)})
    return out


def comprendre(phrase, projet, params, niveau="recettes"):
    """Les actions pour cette phrase, selon le niveau. Revient aux règles si l'IA ne répond pas."""
    base = regles(phrase)
    if niveau == "recettes":
        return {"actions": base, "source": "regles"}
    from . import effets as E
    ids = ", ".join(sorted(E.CATALOGUE))
    plans = [f"plan {i + 1} : {c.get('nom', '')} ({c['debut']:.1f} s)" for i, c in enumerate(projet.clips_piste("video"))]
    texte = _("Demande : {p}\nDurée du montage : {d:.1f} s\nPlans : {l}\nIdentifiants d'effets : {i}\nGoodies : {g}",
              p=phrase, d=projet.duree(), l="; ".join(plans) or "aucun", i=ids, g=", ".join(_genres_goodies()))
    try:
        if niveau == "locale":
            from . import ia_locale
            modele = ia_locale.modele_actif(params)
            if not modele:
                raise RuntimeError(_("Aucun modèle local : cochez-en un dans Préférences › IA locale."))
            brut = ia_locale.generer(modele, texte, [], systeme=CONSIGNE, json_attendu=True, params=params)
            src = "locale:" + modele
        else:
            from . import ia
            brut = ia.demander(params, CONSIGNE, texte, json_attendu=True, max_jetons=1500)
            src = "cloud:" + ia.nom_moteur(params)
        d = brut if isinstance(brut, dict) else lire_json(brut)
        acts = [a for a in (d.get("actions") or []) if isinstance(a, dict) and a.get("action") in ACTIONS]
        acts = [a for a in acts if a["action"] not in ("effet", "transition", "look") or a.get("id") in E.CATALOGUE]
        return {"actions": acts or base, "source": src if acts else "regles"}
    except Exception as e:       # noqa: BLE001
        return {"actions": base, "source": "regles", "avertissement": _("L'IA n'a pas répondu ({e}) : compris sans IA.", e=str(e)[:160])}


def _genres_goodies():
    try:
        from . import goodies as GO
        return sorted(GO.GENRES)[:60]
    except Exception:            # noqa: BLE001
        return []


def lire_json(texte):
    try:
        return json.loads(texte)
    except (TypeError, ValueError):
        m = re.search(r"\{.*\}", texte or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                pass
    return {}


def decrire(a):
    """Une ligne lisible pour la fenêtre de confirmation."""
    from . import effets as E
    k = a.get("action")
    nom_eff = (E.CATALOGUE.get(a.get("id") or "") or (None, a.get("id", "")))[1]
    plans = a.get("plans")
    qui = _("tous les plans") if plans == "tous" else (_("le plan sélectionné") if plans in (None, "selection") else
                                                         _("plan(s) {l}", l=", ".join(str(x) for x in plans)))
    if k == "musique":
        return _("Poser une musique{a} sous la vidéo (vos dossiers d'abord, sinon une musique libre gratuite), coupée à la fin",
                 a=_(" « {a} »", a=a["ambiance"]) if a.get("ambiance") else "")
    if k == "couper_musique":
        return _("Couper la musique à la fin de la vidéo, avec un fondu de sortie")
    if k == "fondus_musique":
        return _("Fondu d'entrée {e} s, fondu de sortie {s} s sur la musique", e=a.get("entree", 2), s=a.get("sortie", 3))
    if k == "volume":
        return _("Volume de la piste {p} à {v} %", p=a.get("piste", "musique"), v=int(float(a.get("valeur", 1)) * 100))
    if k in ("effet", "look"):
        return _("Effet « {n} » sur {q}", n=nom_eff, q=qui)
    if k == "transition":
        return _("Transition « {n} » sur {q}", n=nom_eff, q=qui)
    if k == "vitesse":
        return _("Vitesse ×{v} sur {q}", v=a.get("valeur"), q=qui)
    if k == "texte":
        return _("Texte « {t} »{d}", t=a.get("texte", ""), d=_(" à la fin") if a.get("debut") == "fin" else
                 (_(" à {s} s", s=a["debut"]) if a.get("debut") not in (None, "") else _(" à la ligne rouge")))
    if k == "fleche":
        return _("Flèche {s} ({c}){d}, que vous déplacez ensuite dans l'image", s=_("courbe") if a.get("style") == "courbe" else _("droite"),
                 c=a.get("couleur", "#ff3030"), d=_(" à {s} s", s=a["debut"]) if a.get("debut") is not None else _(" à la ligne rouge"))
    if k == "goodie":
        return _("Goodie « {g} »", g=a.get("genre", ""))
    if k == "couper":
        return _("Couper la vidéo à {t} s", t=a.get("t"))
    return k


def appliquer(actions, ed):
    """Fait les actions dans l'éditeur ; une seule étape d'annulation. Renvoie le nombre d'actions faites."""
    from . import effets as E
    from .projet import fin_clip
    projet = ed.projet
    projet.marquer()
    videos = sorted(projet.clips_piste("video"), key=lambda c: c["debut"])
    sel = ed._clip_selectionne() if hasattr(ed, "_clip_selectionne") else None
    t0 = ed.timeline.position
    fin_v = max([fin_clip(c) for c in videos] or [projet.duree()])

    def cibles(plans):
        if plans == "tous":
            return videos
        if isinstance(plans, list):
            return [videos[i - 1] for i in plans if isinstance(i, int) and 1 <= i <= len(videos)]
        c = sel if sel and sel["piste"].startswith("video") else (projet.clip_a(t0) or (videos[0] if videos else None))
        return [c] if c else []
    faits = 0
    musique_posee = False
    for a in actions:
        k = a.get("action")
        try:
            if k == "musique":
                if not projet.clips_piste("audio"):
                    ed.musique_auto(a.get("ambiance") or None)
                    musique_posee = True
                faits += 1
            elif k == "couper_musique":
                if not musique_posee:
                    for c in list(projet.clips_piste("audio")):
                        if fin_clip(c) > fin_v + 0.05 and c["debut"] < fin_v:
                            v = float(c.get("vitesse", 1.0) or 1.0)
                            c["src_fin"] = round(c["src_debut"] + (fin_v - c["debut"]) * v, 3)
                            c.setdefault("fondu_sortie", 2.0)
                faits += 1
            elif k == "fondus_musique":
                for c in projet.clips_piste("audio"):
                    c["fondu_entree"], c["fondu_sortie"] = float(a.get("entree", 2)), float(a.get("sortie", 3))
                faits += 1
            elif k == "volume":
                piste = {"musique": "audio", "video": "video", "voix": "voix"}.get(a.get("piste", "musique"), "audio")
                for c in projet.clips_piste(piste):
                    c["volume"] = max(0.0, min(2.0, float(a.get("valeur", 1))))
                faits += 1
            elif k in ("effet", "look") and a.get("id") in E.CATALOGUE:
                for c in cibles(a.get("plans") if k == "effet" else "tous"):
                    c.setdefault("effets", []).append({"id": a["id"], "params": dict(E.defauts(a["id"]))})
                faits += 1
            elif k == "transition" and a.get("id") in E.CATALOGUE:
                for c in cibles(a.get("plans") or "tous"):
                    if c is not videos[0]:
                        c["transition"] = {"id": a["id"], "params": dict(E.defauts(a["id"]))}
                faits += 1
            elif k == "vitesse":
                for c in cibles(a.get("plans")):
                    projet.vitesse(c["id"], max(0.1, min(16.0, float(a.get("valeur", 1)))))
                projet.ranger("video")
                faits += 1
            elif k == "texte" and a.get("texte"):
                d = a.get("debut")
                d = max(0.0, fin_v - 4) if d == "fin" else (float(d) if d not in (None, "") else t0)
                f = float(a.get("fin") or d + 4)
                style = {"titre": "titre", "encadre": "encadre"}.get(a.get("style"), "simple")
                projet.ajouter_titre(a["texte"], d, max(d + 0.5, f), style=style, y=float(a.get("y", 0.5 if style == "titre" else 0.85)),
                                     animation="zoom" if style == "titre" else "fondu")
                faits += 1
            elif k == "fleche":
                d = float(a["debut"]) if a.get("debut") is not None else t0
                f = float(a.get("fin") or d + 3)
                projet.ajouter_goodie("fleche", d, f, x=float(a.get("x", 0.5)), y=float(a.get("y", 0.45)), taille=0.25,
                                      options={"angle": float(a.get("angle", 0)), "couleur": a.get("couleur", "#ff3030"),
                                               "style": "courbe" if a.get("style") == "courbe" else "droite", "dessin": True})
                faits += 1
            elif k == "goodie" and a.get("genre"):
                d = float(a.get("debut") if a.get("debut") is not None else t0)
                projet.ajouter_goodie(a["genre"], d, float(a.get("fin") or d + 4))
                faits += 1
            elif k == "couper" and a.get("t") is not None:
                projet.couper_a(float(a["t"]))
                faits += 1
        except Exception as e:       # noqa: BLE001 : une action ratée n'empêche pas les autres
            from .journal import ecrire
            ecrire("commande", f"{k} : {e}")
    projet.modifie = True
    return faits
