"""De l'idée au résultat (0.9.80) : la méthode commune des assistants PhilFactory.

Règle de Philippe (17/11) : « en quelques mots on décrit ce que l'on veut, tu guides pas à pas avec les possibilités ; soit
création pure, soit fichier, image, partie de vidéo, partie de son… ; à partir d'une idée tu guides en laissant et en
expliquant toutes les options ». Elle vaut pour la vidéo, la musique, et ensuite pour les autres parties de PhilCut et
les autres logiciels.

1. Une phrase : ce que l'on veut (le contexte connu, plan ou morceau choisi, est pris d'office).
2. L'assistant en déduit le genre de création, les ÉLÉMENTS nécessaires (personnes, objets, style, voix, paroles…) et le
   DÉROULÉ (plans, parties) : tout arrive pré-rempli.
3. Chaque élément est une carte : ce qui a été compris, et d'où il vient, avec TOUTES les sources possibles expliquées
   (dans l'image, un fichier à moi, un passage du film ou d'un morceau, en ligne, le décrire, le créer par l'IA…) ; la
   conseillée est cochée, sauf quand le choix appartient à l'utilisateur. Une carte complète est verte ; sinon elle dit
   exactement ce qui manque.
4. On valide ou on corrige carte par carte, ou en clair dans la zone libre ; « Régler moi-même » ouvre le mode manuel
   pré-rempli (rien n'est perdu).
5. Aperçu avant toute dépense, budget prévu et dépensé (rouge au-delà), fabrication relue, pose.

Ce module ne dépend pas de l'interface. La partie musique (déduction, fiches par partie, enchaînement) est ici ; la partie
vidéo reste dans assistant_creation.
"""
import copy
import os
import re

from .langue import _

# ------------------------------------------------------------------ les sources possibles d'un élément
# clef -> (libellé, explication). L'ordre des listes par type est l'ordre d'affichage.
SOURCES = {
    "image": (_("Dans l'image du plan"), _("La personne ou l'objet tel qu'on le voit sur la dernière image : PhilCut le découpe et en tire sa fiche. Corrigez le cadre sur l'image si ce n'est pas le bon.")),
    "photo": (_("Une photo à moi"), _("Une image de votre ordinateur (une personne qui est d'accord, ou vous-même) : la fiche est faite d'après elle.")),
    "inventer": (_("Inventé d'après la description"), _("Personne ne l'a encore filmé : l'IA le dessine d'après la description, puis le garde identique d'un plan à l'autre.")),
    "fichier": (_("Un morceau à moi"), _("Un fichier de votre ordinateur (MP3, WAV, vidéo…). Vous choisissez le passage ; il est lu sur ce poste, rien n'est envoyé.")),
    "en_ligne": (_("Le chercher en ligne"), _("YouTube, YouTube Music ou les archives libres : vous écoutez, téléchargez, puis PhilCut s'en sert comme d'un fichier.")),
    "decrire": (_("Le décrire"), _("Vous écrivez comment il doit être ; l'IA peut compléter la description.")),
    "liste": (_("Choisir dans la liste"), _("Les styles ou les voix tout faits de PhilCut.")),
    "j_ecris": (_("Je les écris"), _("Vous écrivez le texte ; l'IA peut ensuite l'améliorer.")),
    "ia": (_("L'IA les écrit"), _("D'après votre idée ; vous relisez et corrigez avant la création.")),
    "aucune": (_("Aucune"), _("Morceau instrumental, sans voix ni paroles.")),
}
TYPES = {
    "personne": ("image", "photo", "inventer"),
    "objet": ("image", "photo", "inventer"),
    "style": ("fichier", "en_ligne", "decrire", "liste"),
    "voix": ("fichier", "en_ligne", "decrire", "liste", "aucune"),
    "paroles": ("j_ecris", "ia", "aucune"),
}
# Ce que l'on fait d'un morceau donné en source (style ou voix) : deux usages, toujours expliqués.
USAGES = {
    "style": (("inspirer", _("S'en inspirer"), _("PhilCut mesure tempo, tonalité, instruments et ambiance, et les écrit dans la consigne : le morceau n'est jamais repris.")),
              ("reprendre", _("Repartir du morceau (réorchestrer)"), _("Le moteur part de l'enregistrement lui-même et le rejoue autrement : seulement pour un morceau à vous ou libre de droits (déclaré)."))),
    "voix": (("decrire", _("Décrire sa manière de chanter"), _("La voix est isolée sur ce poste puis décrite (registre, étendue, vibrato, timbre) : le moteur chante dans cette manière, avec une autre voix.")),
             ("timbre", _("Garder son timbre"), _("La voix isolée sert de référence de timbre : seulement votre voix ou celle d'une personne qui est d'accord. « Plus féminine », « plus grave » se règlent ensuite aussi par Transformer la voix."))),
}


def element(type_, nom="", description="", source="", **autres):
    """Une carte : {type, nom, description, source, ...} ; `source` vide = à choisir par l'utilisateur."""
    e = {"type": type_, "nom": nom, "description": description, "source": source if source in TYPES.get(type_, ()) else ""}
    e.update(autres)
    return e


def sources(type_):
    return [(k, SOURCES[k][0], SOURCES[k][1]) for k in TYPES.get(type_, ())]


def manque(e):
    """Ce qui manque pour que la carte soit complète (texte pour l'utilisateur), ou "" si elle l'est."""
    t, s = e.get("type"), e.get("source")
    if not s:
        return _("Choisissez d'où vient cet élément.")
    if t in ("personne", "objet"):
        if s == "image" and not e.get("boite"):
            return _("Tracez son cadre sur l'image.")
        if s == "photo" and not (e.get("photo") and os.path.exists(e["photo"])):
            return _("Choisissez la photo.")
        if s == "inventer" and len((e.get("description") or "").strip()) < 8:
            return _("Décrivez-le (âge, allure, vêtements ; couleur et forme pour un objet).")
        return ""
    if s in ("fichier", "en_ligne"):
        if not e.get("chemin"):
            return _("Choisissez le morceau.") if s == "fichier" else _("Cherchez puis choisissez le morceau.")
        if not e.get("usage"):
            return _("Dites ce que PhilCut doit en faire.")
        if e["usage"] in ("reprendre",) and not e.get("droits_ok"):
            return _("Déclarez que ce morceau est à vous ou libre de droits.")
        if e["usage"] == "timbre" and not e.get("accord"):
            return _("Cochez l'accord de la personne qui chante (ou c'est vous).")
        if e["usage"] == "timbre" and not e.get("voix_seule"):
            return _("Isolez la voix (sur ce poste).")
        if e["usage"] in ("inspirer", "decrire") and not e.get("pret"):
            return _("Analyse à faire : « Ecouter et décrire ».")
        return ""
    if s == "decrire" and len((e.get("description") or "").strip()) < 4:
        return _("Ecrivez la description.")
    if s == "liste" and not e.get("choix"):
        return _("Choisissez dans la liste.")
    return ""


def complet(elements):
    return all(not manque(e) for e in elements)


# ------------------------------------------------------------------ deviner ce que l'on veut faire
_MOTS_MUSIQUE = re.compile(r"\b(musique|chanson|ballade|morceau|mélodie|melodie|refrain|couplet|rock|pop|jazz|blues|électro|electro|rap|"
                           r"hip-hop|métal|metal|symphon\w*|orchestr\w*|chant\w*|chanteu\w*|instrumental|tempo|guitare|piano|batterie|"
                           r"song|music|ballad|tune)\b", re.I)
_MOTS_LOGO = re.compile(r"\b(logo|intro|générique|generique|titre animé|jingle visuel)\b", re.I)


def deviner_genre(texte, avec_plan=False):
    """« musique », « logo » ou « video » (suite du plan s'il y en a un) d'après les mots ; l'utilisateur peut changer."""
    t = texte or ""
    if _MOTS_LOGO.search(t) and not _MOTS_MUSIQUE.search(t):
        return "logo"
    if len(_MOTS_MUSIQUE.findall(t)) >= 1 and not re.search(r"\b(descend\w*|monte\w*|marche\w*|limousine|voiture|caméra|plan)\b", t, re.I):
        return "musique"
    return "suite" if avec_plan else "scene"


def duree_dite(texte, defaut=60.0):
    """« 3 minutes », « 2 min 30 », « 90 s » → secondes (bornées 10 à 600)."""
    t = (texte or "").lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:min|minutes?|mn)\b(?:\s*(\d+)\s*(?:s|sec|secondes?)?)?", t)
    if m:
        return max(10.0, min(600.0, float(m.group(1)) * 60 + float(m.group(2) or 0)))
    m = re.search(r"(\d+)\s*(?:s|sec|secondes?)\b", t)
    if m:
        return max(10.0, min(600.0, float(m.group(1))))
    return defaut


# ------------------------------------------------------------------ musique : déduire les cartes et le déroulé
CONSIGNE_MUSIQUE = """Tu es directeur artistique. L'utilisateur décrit en quelques mots la musique qu'il veut. Déduis ce qu'il faut
pour la fabriquer avec une IA musicale qui crée partie par partie. Rends un objet JSON :
{{"titre": "titre court", "duree": secondes au total,
 "style": {{"reference": "nom du groupe ou de l'artiste cité, ou vide", "description": "le style en mots, sans aucun nom propre",
            "style_id": un identifiant parmi [{ids}] ou vide, "source": "fichier", "en_ligne", "decrire" ou "liste"}},
 "voix": {{"chantee": true ou false, "reference": "de qui est la voix citée, ou vide", "description": "la voix voulue en mots, sans nom",
           "retouche": "ce qu'il faut changer à cette voix (ex. plus féminine et chaude) ou vide",
           "source": "fichier", "en_ligne", "decrire", "liste" ou "aucune"}},
 "paroles": {{"theme": "de quoi parle la chanson, ou vide", "source": "j_ecris", "ia" ou "aucune", "langue": "fr", "en"…}},
 "parties": [{{"nom": "Intro", "duree": secondes, "tempo": battements par minute, "energie": "calme", "moyenne" ou "forte",
              "chant": true ou false, "description": "ce qu'on entend, en mots"}}],
 "tonalite": "ex. E minor, ou vide", "remarques": "une phrase pour l'utilisateur, ou vide"}}
Règles : la somme des durées des parties = la durée voulue (par défaut 60 s) ; 3 à 8 parties ; respecte exactement le
déroulé demandé (un passage lent au milieu = une ou deux parties lentes au milieu, avec un tempo nettement plus bas) ;
même tonalité pour tout le morceau. Quand un groupe ou un artiste est cité, la source conseillée du style et de la voix est
« fichier » (un morceau à lui) ; sinon « decrire ». Les descriptions ne contiennent jamais de nom propre. Ecris en {langue}.
"""


def _langue():
    from . import langue
    return {"fr": "français", "en": "English", "de": "Deutsch", "es": "español", "it": "italiano"}.get(langue.LANGUE or "fr", "français")


def _txt(v, n=300):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _num(v, defaut, bas, haut):
    try:
        return max(bas, min(haut, float(v)))
    except (TypeError, ValueError):
        return defaut


def lire_musique(d, duree_voulue=None):
    """Réponse de l'IA rendue sûre : cartes style, voix, paroles ; parties bornées dont la durée totale est respectée."""
    from . import musique_ia as MI
    d = d if isinstance(d, dict) else {}
    ids = {s[0] for s in MI.STYLES}
    st, vx, pa = d.get("style") or {}, d.get("voix") or {}, d.get("paroles") or {}
    duree = float(duree_voulue or _num(d.get("duree"), 60.0, 10.0, 600.0))
    ref = _txt(st.get("reference"), 60)
    style = element("style", ref or _("Style"), _txt(st.get("description")), _txt(st.get("source"), 10) or ("fichier" if ref else "decrire"),
                    reference=ref, choix=_txt(st.get("style_id"), 30) if _txt(st.get("style_id"), 30) in ids else "")
    chantee = bool(vx.get("chantee", True)) and _txt(vx.get("source"), 10) != "aucune"
    vref = _txt(vx.get("reference"), 60)
    voix = element("voix", vref or _("Voix"), _txt(vx.get("description")),
                   (_txt(vx.get("source"), 10) or ("fichier" if vref else "decrire")) if chantee else "aucune",
                   reference=vref, retouche=_txt(vx.get("retouche"), 120))
    langue = _txt(pa.get("langue"), 5).lower() or "fr"
    paroles = element("paroles", _("Paroles"), _txt(pa.get("theme")), (_txt(pa.get("source"), 10) or "ia") if chantee else "aucune",
                      langue=langue if langue in ("fr", "en", "de", "es", "it", "pt", "ja") else "fr", texte="")
    parties = []
    for p in (d.get("parties") or [])[:8]:
        if not isinstance(p, dict):
            continue
        parties.append({"nom": _txt(p.get("nom"), 30) or _("Partie {n}", n=len(parties) + 1), "duree": _num(p.get("duree"), 20.0, 5.0, 240.0),
                        "tempo": int(_num(p.get("tempo"), 100, 40, 220)),
                        "energie": _txt(p.get("energie"), 10).lower() if _txt(p.get("energie"), 10).lower() in ("calme", "moyenne", "forte") else "moyenne",
                        "chant": bool(p.get("chant")) and chantee, "description": _txt(p.get("description"), 200)})
    if not parties:
        parties = parties_simples(duree)
    caler(parties, duree)
    return {"titre": _txt(d.get("titre"), 60), "duree": duree, "elements": [style, voix, paroles], "parties": parties,
            "tonalite": _txt(d.get("tonalite"), 20), "remarques": _txt(d.get("remarques"), 300)}


def parties_simples(duree, tempo=110, lent_au_milieu=False):
    """Sans IA : intro, couplet, refrain, (pont lent), refrain, fin."""
    gabarit = [(_("Intro"), 0.1, 1.0, "moyenne", False), (_("Couplet"), 0.2, 1.0, "moyenne", True), (_("Refrain"), 0.2, 1.0, "forte", True)]
    gabarit += [(_("Passage lent"), 0.25, 0.6, "calme", True)] if lent_au_milieu else [(_("Couplet"), 0.2, 1.0, "moyenne", True)]
    gabarit += [(_("Refrain"), 0.15, 1.0, "forte", True), (_("Fin"), 0.1, 1.0, "calme", False)]
    tot = sum(g[1] for g in gabarit)
    return [{"nom": n, "duree": duree * f / tot, "tempo": int(tempo * k), "energie": e, "chant": c, "description": ""} for n, f, k, e, c in gabarit]


def caler(parties, duree):
    """Les durées des parties ramenées à la durée voulue (proportions gardées), arrondies à la seconde."""
    tot = sum(p["duree"] for p in parties) or 1.0
    reste = float(duree)
    for i, p in enumerate(parties):
        p["duree"] = float(round(reste if i == len(parties) - 1 else p["duree"] * duree / tot))
        reste -= p["duree"]
    return parties


def analyse_musique_simple(texte):
    """Sans IA : la durée dite, un style deviné par les mots, un passage lent si on le demande ; cartes pré-remplies."""
    from . import musique_ia as MI
    t = (texte or "").lower()
    duree = duree_dite(texte, 60.0)
    choix = next((s[0] for s in MI.STYLES if s[0] in t or s[1].lower() in t), "rock" if "rock" in t else "")
    tempo = next((s[4] for s in MI.STYLES if s[0] == choix and s[4]), 110)
    lent = bool(re.search(r"\b(lent\w*|ballade|calme|doux|douce)\b", t)) and bool(re.search(r"\b(rapide\w*|milieu|puis|ensuite)\b", t))
    chantee = bool(re.search(r"\b(voix|chant\w*|chanson|paroles|chanteu\w*)\b", t))
    return {"titre": "", "duree": duree, "tonalite": "", "remarques": "",
            "elements": [element("style", _("Style"), texte.strip()[:200], "liste" if choix else "decrire", choix=choix),
                         element("voix", _("Voix"), "", "decrire" if chantee else "aucune", retouche=""),
                         element("paroles", _("Paroles"), texte.strip()[:200], "ia" if chantee else "aucune", langue="fr", texte="")],
            "parties": caler(parties_simples(duree, tempo, lent), duree)}


def analyser_musique(params, texte, niveau="claude"):
    from . import assistant_creation as A
    from . import musique_ia as MI
    ids = ", ".join(s[0] for s in MI.STYLES)
    r = A.demander(params, CONSIGNE_MUSIQUE.format(ids=ids, langue=_langue()), "Demande : " + texte.strip(), (), niveau)
    dite = duree_dite(texte, 0.0) or None
    return lire_musique(r, dite)


# ------------------------------------------------------------------ musique : de la carte à la fiche du moteur
ENERGIES_EN = {"calme": "soft, calm, gentle, sparse", "moyenne": "steady groove, medium energy", "forte": "powerful, energetic, full band, driving"}


def fiche_base(etat):
    """Fiche musique_ia commune à toutes les parties (style, voix, tonalité) d'après les cartes."""
    from . import musique_ia as MI
    style, voix, paroles = etat["elements"]
    f = MI.fiche_vide()
    f["duree"] = float(etat["duree"])
    f["tonalite"] = etat.get("tonalite") or ""
    if style["source"] == "liste" and style.get("choix"):
        f["style"] = style["choix"]
    elif style.get("choix"):
        f["style"] = style["choix"]
    phrase = []
    if style["source"] == "decrire" or (style.get("description") and style["source"] in ("fichier", "en_ligne") and not style.get("inspiration")):
        phrase.append(style.get("description") or "")
    if style.get("inspiration"):
        f["inspiration"] = style["inspiration"]
        if not f["tonalite"]:
            f["tonalite"] = style["inspiration"].get("tonalite") or ""
    if style["source"] != "liste" and not style.get("choix"):
        f["utiliser_ia"], f["consigne_ia"] = False, ""
    f["instrumental"] = voix["source"] == "aucune"
    if not f["instrumental"]:
        if voix["source"] == "liste" and voix.get("choix"):
            f["voix"] = voix["choix"]
        if voix.get("voix_decrite"):
            f["voix_decrite"] = dict(voix["voix_decrite"])
        elif voix["source"] == "decrire" and voix.get("description"):
            f["voix_decrite"] = {"fr": voix["description"], "en": "", "a_traduire": voix["description"]}
        if voix.get("usage") == "timbre" and voix.get("voix_seule"):
            f["voix_reference"] = {"chemin": voix["voix_seule"]}
        if voix.get("retouche"):
            f["retouche_voix"] = voix["retouche"]
        f["langue"] = paroles.get("langue") or "fr"
    f["phrase"] = ", ".join(x for x in phrase if x)
    if style.get("usage") == "reprendre" and style.get("chemin") and style.get("droits_ok"):
        f["source"] = {"chemin": style["chemin"], "force": float(style.get("force", 0.5))}
    return f


def paroles_par_partie(texte, parties):
    """Les paroles balisées ([verse], [chorus], [bridge]…) réparties sur les parties chantées, dans l'ordre ; une partie
    sans chant reçoit [Instrumental]. Sans balises, les vers sont partagés au prorata des durées chantées."""
    blocs = [b.strip() for b in re.split(r"(?m)^(?=\[)", texte or "") if b.strip()]
    chantees = [i for i, p in enumerate(parties) if p.get("chant")]
    out = ["" for _p in parties]
    if not chantees or not (texte or "").strip():
        return out
    if len(blocs) <= 1:                                   # sans balises : partage des vers
        vers = [l for l in (texte or "").split("\n") if l.strip() and not l.strip().startswith("[")]
        tot = sum(parties[i]["duree"] for i in chantees) or 1.0
        k = 0
        for n, i in enumerate(chantees):
            nb = len(vers) - k if n == len(chantees) - 1 else max(1, round(len(vers) * parties[i]["duree"] / tot))
            out[i] = "\n".join(vers[k:k + nb])
            k += nb
        return out
    for n, i in enumerate(chantees):                      # un bloc par partie chantée ; les blocs en trop vont à la dernière
        if n < len(blocs):
            out[i] = blocs[n] if n < len(chantees) - 1 else "\n".join(blocs[n:])
    return out


def fiche_partie(base, etat, k, paroles_k, traduire=None):
    """La fiche d'une partie : même style, même voix, même tonalité ; durée, tempo, énergie et paroles de la partie."""
    p = etat["parties"][k]
    f = copy.deepcopy(base)
    f["duree"] = float(p["duree"])
    f["tempo"] = int(p["tempo"])
    desc = p.get("description") or ""
    en = ENERGIES_EN.get(p.get("energie"), "")
    if desc:
        desc = traduire(desc) if traduire else desc
    morceaux = [x for x in (f.get("phrase") or "",) if x]
    f["phrase"] = ", ".join(morceaux)
    f["partie_en"] = ", ".join(x for x in (en, desc, "slow ballad tempo" if p["tempo"] < 85 else "") if x)
    f["instrumental"] = base.get("instrumental") or not p.get("chant") or not (paroles_k or "").strip()
    f["paroles"] = "" if f["instrumental"] else paroles_k
    src = base.get("source")
    if src and etat.get("debuts"):
        f["source"] = dict(src, debut=etat["debuts"][k])
    return f


def debuts(parties):
    t, out = 0.0, []
    for p in parties:
        out.append(t)
        t += float(p["duree"])
    return out


def mesure_s(tempo, temps=4):
    return 60.0 / max(40, int(tempo or 100)) * temps


def enchainer(fichiers, parties, sortie):
    """Les parties bout à bout, chaque raccord en fondu d'une mesure (au tempo de la partie qui finit) : un seul fichier."""
    from . import moteur
    if len(fichiers) == 1:
        moteur.lancer(["-y", "-i", fichiers[0], "-c:a", "libmp3lame", "-q:a", "2", sortie])
        return sortie
    args = ["-y"]
    for f in fichiers:
        args += ["-i", f]
    chaine, prec = [], "[0:a]"
    for i in range(1, len(fichiers)):
        d = max(0.5, min(3.0, mesure_s(parties[i - 1]["tempo"]), float(parties[i - 1]["duree"]) / 3, float(parties[i]["duree"]) / 3))
        lab = f"[a{i}]" if i < len(fichiers) - 1 else "[out]"
        chaine.append(f"{prec}[{i}:a]acrossfade=d={d:.2f}:c1=tri:c2=tri{lab}")
        prec = lab
    args += ["-filter_complex", ";".join(chaine), "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "2", sortie]
    moteur.lancer(args)
    if not os.path.exists(sortie):
        raise RuntimeError(_("Les parties n'ont pas pu être enchaînées."))
    return sortie


def creer_parties(etat, dossier, params=None, progression=None, arret=lambda: False, traduire=None, deja=None):
    """Fabrique chaque partie à son tempo (même style, voix, tonalité), puis les enchaîne. `deja` : {k: fichier} gardés
    (une partie refaite ne refait pas les autres). Renvoie (fichier final, {k: fichier}, fiche de base)."""
    from . import musique_ia as MI
    base = fiche_base(etat)
    if (base.get("voix_decrite") or {}).get("a_traduire") and traduire:
        base["voix_decrite"]["en"] = traduire(base["voix_decrite"].pop("a_traduire"))
    if base.get("retouche_voix"):
        base["retouche_en"] = traduire(base["retouche_voix"]) if traduire else base["retouche_voix"]
        if (base.get("voix_decrite") or {}).get("en"):          # la retouche va avec la voix, jamais sur une partie instrumentale
            base["voix_decrite"]["en"] = base["voix_decrite"]["en"].rstrip(" ,.") + ", " + base.pop("retouche_en")
    textes = paroles_par_partie((etat["elements"][2].get("texte") or "") if etat["elements"][2]["source"] != "aucune" else "", etat["parties"])
    etat["debuts"] = debuts(etat["parties"])
    faits = dict(deja or {})
    n = len(etat["parties"])
    for k in range(n):
        if arret():
            raise InterruptedError()
        if faits.get(k) and os.path.exists(faits[k]):
            continue
        f = fiche_partie(base, etat, k, textes[k], traduire)
        if f.get("source"):                               # réorchestrer : le passage du morceau qui correspond à la partie
            src = f.pop("source")
            from . import moteur
            total = float((moteur.sonder(src["chemin"]) or {}).get("duree") or 0)
            deb = src["debut"] % total if total > f["duree"] else 0.0       # morceau plus court que le nouveau : on reprend au début
            try:
                f["source"] = {"chemin": MI.extraire_passage(src["chemin"], deb, min(deb + f["duree"], total or deb + f["duree"])),
                               "force": src.get("force", 0.5)}
            except RuntimeError:                          # passage impossible (trop court) : cette partie s'en inspire seulement
                pass
        f["phrase"] = ", ".join(x for x in (f.get("phrase"), f.pop("partie_en", ""),
                                            "" if f.get("instrumental") else base.get("retouche_en", "")) if x)
        sortie = os.path.join(dossier, f"partie_{k + 1:02d}.mp3")
        prog = (lambda x, t="", k=k: progression((k + x) / (n + 0.3), _("partie {i} sur {n}", i=k + 1, n=n) + (" — " + t if t else ""))) \
            if progression else None
        r, _c = MI.creer(f, sortie, params, prog, arret, traduire)
        faits[k] = r
    if progression:
        progression(n / (n + 0.3), _("Enchaînement des parties…"))
    final = enchainer([faits[k] for k in range(n)], etat["parties"], os.path.join(dossier, "morceau.mp3"))
    return final, faits, base


def resume(etat):
    """La musique telle qu'elle sera fabriquée, en une ou deux phrases, pour la dernière étape."""
    st, vx, pa = etat["elements"]
    parts = " · ".join(f"{p['nom']} {int(p['duree'])} s, {p['tempo']} bpm" for p in etat["parties"])
    voix = _("instrumental") if vx["source"] == "aucune" else (vx.get("description") or (vx.get("voix_decrite") or {}).get("fr") or vx.get("nom"))
    if vx.get("retouche") and vx["source"] != "aucune":
        voix += " (" + vx["retouche"] + ")"
    return _("{d} : style {s} ; voix : {v} ; {p}.", d=f"{int(etat['duree']) // 60}:{int(etat['duree']) % 60:02d}",
             s=st.get("description") or st.get("choix") or st.get("nom"), v=voix, p=parts)


# ------------------------------------------------------------------ améliorer un texte (Philippe, 17/11 : « ce qui est
# proposé peut être amélioré en phrasé par l'IA aussi ; l'IA crée parfois mieux les choses par le sens donné »)
QUOI = {"idee": "l'idée de départ d'une création (vidéo ou musique)", "personne": "la description physique d'une personne à dessiner",
        "objet": "la description d'un objet à dessiner", "plan": "l'action d'un plan vidéo (une seule action simple, physiquement possible)",
        "style": "la description d'un style musical", "voix": "la description d'une voix chantée", "partie": "ce qu'on entend dans une partie d'un morceau",
        "paroles": "les paroles d'une chanson (garde les balises [verse], [chorus], [bridge])", "theme": "le thème d'une chanson"}

CONSIGNE_AMELIORER = """Tu améliores le phrasé de {quoi}, pour qu'une IA de création comprenne mieux ce qui est voulu. Garde
exactement le sens, les noms, les chiffres et tout ce que l'utilisateur a demandé ; précise ce qui est flou, rends les images
concrètes (gestes, lumière, matières, ambiance), enlève les répétitions. Jamais de nom de personne réelle ou célèbre, ni de
marque. {contexte}Rends un objet JSON {{"texte": "le texte amélioré", "pourquoi": "en une phrase courte, ce que tu as changé"}}.
Ecris en {langue}."""


def ameliorer_texte(params, texte, quoi="idee", contexte="", niveau="claude"):
    """(texte amélioré, pourquoi) ; le texte de l'utilisateur reste affiché à côté pour qu'il choisisse."""
    from . import assistant_creation as A
    if len((texte or "").strip()) < 3:
        raise A.ErreurAssistant(_("Ecrivez d'abord quelques mots."))
    r = A.demander(params, CONSIGNE_AMELIORER.format(quoi=QUOI.get(quoi, quoi), langue=_langue(),
                                                     contexte=("Contexte : " + contexte.strip()[:800] + "\n") if contexte.strip() else ""),
                   texte.strip(), (), niveau, max_jetons=1500 if quoi == "paroles" else 700)
    r = r if isinstance(r, dict) else {}
    neuf = str(r.get("texte") or "").strip()
    if quoi != "paroles":
        neuf = re.sub(r"\s+", " ", neuf)
    if not neuf:
        raise A.ErreurAssistant(_("L'IA n'a rien proposé : réessayez, ou changez d'IA."))
    return neuf[:4000], _txt(r.get("pourquoi"), 200)


CONSIGNE_MODIFIER_MUSIQUE = """Tu aides à préparer une musique fabriquée par IA. Voici son état (JSON) et une demande de l'utilisateur.
Rends l'état modifié au même format que l'état reçu, plus "remarques": "ce que tu as changé, en une phrase". Ne change que ce qui
est demandé ; garde mot pour mot le reste. La somme des durées des parties = "duree". Aucun nom propre dans les descriptions.
Ecris en {langue}."""

_GARDER = ("chemin", "passage", "usage", "inspiration", "pret", "voix_decrite", "voix_seule", "accord", "droits_ok", "texte", "choix", "force")


def etat_musique(etat):
    st, vx, pa = etat["elements"]
    return {"titre": etat.get("titre", ""), "duree": etat["duree"], "tonalite": etat.get("tonalite", ""),
            "style": {"reference": st.get("reference", ""), "description": st.get("description", ""), "style_id": st.get("choix", ""),
                      "source": st.get("source", "")},
            "voix": {"chantee": vx.get("source") != "aucune", "reference": vx.get("reference", ""), "description": vx.get("description", ""),
                     "retouche": vx.get("retouche", ""), "source": vx.get("source", "")},
            "paroles": {"theme": pa.get("description", ""), "source": pa.get("source", ""), "langue": pa.get("langue", "fr")},
            "parties": [dict(p) for p in etat["parties"]]}


def modifier_musique(params, etat, demande, niveau="claude"):
    """« Le passage lent plus long, une voix plus grave » : l'état corrigé, ce qui a été choisi (fichiers, analyses, paroles)
    gardé. Renvoie (état, message)."""
    import json
    from . import assistant_creation as A
    r = A.demander(params, CONSIGNE_MODIFIER_MUSIQUE.format(langue=_langue()),
                   "Etat :\n" + json.dumps(etat_musique(etat), ensure_ascii=False) + "\n\nDemande : " + demande.strip(), (), niveau)
    neuf = lire_musique(r, (r or {}).get("duree") if isinstance(r, dict) else etat["duree"])
    for vieux, e in zip(etat["elements"], neuf["elements"]):
        if e.get("source") == vieux.get("source") or not e.get("source"):
            e["source"] = vieux.get("source")
            for k in _GARDER:
                if k in vieux and k not in ("choix",) or (k == "choix" and not e.get("choix") and vieux.get("choix")):
                    e[k] = vieux[k]
    return neuf, neuf.get("remarques", "")
