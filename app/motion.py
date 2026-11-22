"""Animations (motion design) dans PhilCut (0.9.99) : chiffres qui montent, barres qui poussent, courbe qui se trace, titres
animés… décrits une fois (une « animation » : des données, un texte, la charte), puis fabriqués par le moteur choisi.

Les moteurs (l'utilisateur choisit, PhilCut conseille et dit pourquoi) :
- maison             : dessiné par PhilCut, rien à installer, aperçu immédiat ;
- hyperframes_local  : HyperFrames (HeyGen, Apache 2.0) sur ce poste : HTML + GSAP rendu par un Chrome invisible, gratuit ;
- hyperframes_cloud  : la même composition rendue chez HeyGen, payée à la minute (clef HeyGen, crédit affiché) ;
- remotion           : Remotion sur ce poste (gratuit pour un particulier ou une structure de 3 personnes au plus ;
                       licence entreprise au-delà : la question est posée une fois).
Le même texte, les mêmes données et la même charte donnent le même film, quel que soit le moteur.

Une animation : {"format": 1, "genre", "titre", "sous_titre", "valeur", "prefixe", "suffixe", "badge", "donnees":
[[libellé, valeur]], "source", "duree", "taille": [L, H], "cadence", "transparent", "charte", "reglages", "variante",
"zones_sures"}
"""
import copy, csv, io, json, os, re, time

from .langue import _


def _langue_ui():
    from . import langue
    return langue.LANGUE or "fr"

FORMAT = 1
GENRES = {
    "compteur": {"nom": _("Chiffre qui monte"), "aide": _("Un grand chiffre qui défile jusqu'à sa valeur, son titre, une pastille "
                                                         "(« ▲ +23 % sur un an »).")},
    "barres": {"nom": _("Barres qui poussent"), "aide": _("Une barre par ligne de vos données, chacune avec son chiffre ; la plus "
                                                         "haute est mise en avant.")},
    "courbe": {"nom": _("Courbe qui se trace"), "aide": _("La courbe se dessine point par point, la zone dessous se remplit, le "
                                                         "record s'affiche.")},
    "titre": {"nom": _("Titre animé"), "aide": _("Un titre qui arrive mot par mot, son sous-titre et un trait d'accent : chapitre, "
                                                "annonce, citation.")},
    "chiffres": {"nom": _("Les trois à la suite (chiffre, barres, courbe)"),
                 "aide": _("Le chiffre total, puis les barres, puis la courbe : une petite séquence complète sur vos données.")},
    # 1.0.0 : sous-titres animés et habillage
    "sous_titres": {"nom": _("Sous-titres animés"), "aide": _("Les mots dits dans le montage, animés au rythme de la voix : mot "
                                                             "surligné, mots qui sautent, un mot à la fois ou karaoké.")},
    "bandeau": {"nom": _("Bandeau nom et fonction"), "aide": _("Le nom et la fonction de la personne qui parle, en bas de "
                                                              "l'image : il arrive, reste, puis s'en va.")},
    "progression": {"nom": _("Barre de progression"), "aide": _("Une barre fine qui avance sur toute la vidéo, avec les "
                                                               "chapitres (vos repères) : on sait où l'on en est.")},
    "defilement": {"nom": _("Capture qui défile"), "aide": _("Une capture (page web, document, conversation) dans un cadre, qui "
                                                            "défile doucement de haut en bas.")},
    # 1.0.1 : plus de types (Philippe, 20/11 13h09 « il en faut plus »)
    "camembert": {"nom": _("Camembert (parts d'un total)"), "aide": _("Un anneau qui se remplit part par part, avec la légende et "
                                                                      "les pourcentages : la répartition d'un budget, d'un public…")},
    "jauge": {"nom": _("Jauge en pourcentage"), "aide": _("Un anneau qui se remplit jusqu'au pourcentage pendant que le chiffre "
                                                          "monte : un taux, un objectif atteint.")},
    "comparaison": {"nom": _("Comparaison avant / après"), "aide": _("Deux chiffres face à face (les deux premières lignes de vos "
                                                                     "données), leurs barres, et l'évolution en pourcentage.")},
    "classement": {"nom": _("Classement (barres horizontales)"), "aide": _("Vos lignes rangées de la plus grande à la plus petite, "
                                                                          "avec leur rang : un palmarès, un top 5.")},
    "chiffres_cles": {"nom": _("Chiffres clefs (2 à 4 tuiles)"), "aide": _("Deux à quatre chiffres dans des tuiles, qui montent "
                                                                         "l'un après l'autre : le résumé d'une année.")},
    "chronologie": {"nom": _("Chronologie (frise)"), "aide": _("Une frise qui se trace, une date et un texte par ligne : « 1998 : "
                                                              "ouverture »…")},
    "liste": {"nom": _("Liste à points"), "aide": _("Les points arrivent un par un avec une coche : étapes, conseils, avantages.")},
    "citation": {"nom": _("Citation"), "aide": _("Une phrase en grand avec ses guillemets, mot par mot, puis son auteur.")},
    "appel": {"nom": _("Appel à l'action (s'abonner…)"), "aide": _("Un bouton que la souris vient cliquer : « S'abonner », « Lien en "
                                                                  "description », « Réserver »…")},
}
A_LIGNES = ("chronologie", "liste")                        # genres qui prennent des lignes de texte (anim["lignes"])
A_DONNEES = ("compteur", "barres", "courbe", "chiffres", "camembert", "comparaison", "classement", "chiffres_cles")
STYLES_ST = {"surligne": _("Mot surligné (le mot dit dans une boîte de couleur)"), "saute": _("Mots qui sautent, un à un"),
             "un_mot": _("Un grand mot à la fois, au centre"), "karaoke": _("Karaoké (la ligne se colore au fil des mots)")}
CALAGES = {"": _("Rien (horaire par défaut)"), "voix": _("La voix : quand le chiffre, le mois, le mot est dit"),
           "musique": _("La musique : sur les temps")}
VARIANTES = {0: _("Dans le style de la charte"), 1: _("Plus vif"), 2: _("Plus sobre")}
REGLAGES = [  # (clef, libellé, minimum, maximum, défaut) : les curseurs de la fenêtre, communs à tous les moteurs
    ("vitesse", _("Vitesse"), 0.5, 2.0, 1.0),
    ("rebond", _("Rebond"), 0.0, 1.0, 0.35),
    ("decalage", _("Décalage entre éléments"), 0.0, 1.0, 0.5),
    ("epaisseur", _("Epaisseur des barres et du trait"), 0.2, 1.0, 0.7),
    ("lueur", _("Lueur"), 0.0, 1.0, 0.6),
    ("taille_texte", _("Taille du texte"), 0.6, 1.4, 1.0),
]
EXEMPLE = [["Janv.", 3120], ["Févr.", 4380], ["Mars", 3960], ["Avr.", 5870], ["Mai", 7240], ["Juin", 9820]]   # neutre


def TITRES_EXEMPLE():
    """Les titres d'exemple : on les remplace en changeant de type, jamais le texte de l'utilisateur."""
    return (_("Visiteurs, premier semestre"), _("Camille Martin"), _("S'abonner pour la suite"), _("La simplicité est la sophistication suprême."),
            _("Objectif atteint"), _("Avant / après"), _("Le semestre en chiffres"), _("Notre histoire"), _("Pourquoi l'essayer"))


def nouvelle(genre="chiffres", charte=None, taille=(1920, 1080)):
    from . import charte as CH
    d = sum(v for _l, v in EXEMPLE)
    return {"format": FORMAT, "genre": genre if genre in GENRES else "chiffres", "titre": _("Visiteurs, premier semestre"),
            "sous_titre": _("Visiteurs par mois"), "valeur": d, "prefixe": "", "suffixe": "", "badge": _("▲ +23 % sur un an"),
            "titre_barres": _("Mois après mois"), "titre_courbe": _("La tendance"), "sous_titre_courbe": _("Juin bat le record du semestre"),
            "donnees": [list(x) for x in EXEMPLE], "source": "", "duree": duree_conseillee(genre), "taille": list(taille),
            "cadence": 30, "transparent": False, "charte": copy.deepcopy(charte or CH.DEFAUT),
            "reglages": {k: d_ for k, _l, _a, _b, d_ in REGLAGES}, "variante": 0, "zones_sures": taille[1] > taille[0]}


def instant_vignette(anim):
    """L'instant le plus parlant pour les vignettes des propositions."""
    g, D = anim.get("genre"), float(anim.get("duree") or 6)
    if g == "sous_titres" and anim.get("mots"):
        m = anim["mots"][min(len(anim["mots"]) - 1, 3)]
        return float(m[0]) + 0.05
    return {"bandeau": min(D * 0.5, 2.0), "progression": D * 0.4, "defilement": D * 0.4, "titre": D * 0.55}.get(
        g, D * (0.5 if g == "chiffres" else 0.55))


def elements(anim):
    """Les éléments qui arrivent un à un : [(libellé, valeur ou None, texte)] selon le genre."""
    g = anim.get("genre")
    d = [x for x in anim.get("donnees") or [] if len(x) >= 2] or [list(x) for x in EXEMPLE]
    if g in A_LIGNES:
        out = []
        for l in anim.get("lignes") or []:
            l = str(l).strip()
            if not l:
                continue
            m = re.match(r"^(.{1,24}?)\s*(?:[:—–]|\s-\s)\s*(.+)$", l) if g == "chronologie" else None
            out.append((m.group(1), None, m.group(2)) if m else (l if g == "liste" else "", None, l if g == "liste" else l))
        return out[:12]
    if g == "classement":
        return [(l, float(v), "") for l, v in sorted(d, key=lambda x: -float(x[1]))][:10]
    if g == "chiffres_cles":
        return [(l, float(v), "") for l, v in d][:4]
    if g == "comparaison":
        return [(l, float(v), "") for l, v in d][:2]
    if g == "camembert":
        return [(l, float(v), "") for l, v in d if float(v) > 0][:8]
    return [(l, float(v), "") for l, v in d]


def palette(charte, n):
    """n couleurs de la charte pour les parts d'un camembert : de l'accent au second accent, puis plus claires."""
    from . import charte as CH
    c = CH.complete(charte)["couleurs"]
    out = []
    for i in range(max(1, n)):
        x = i / max(1, n - 1)
        coul = CH.melanger(c["accent"], c["accent2"], x)
        if i % 2 and n > 3:
            coul = CH.melanger(coul, c["texte"], 0.25)
        out.append(coul)
    return out


HABILLAGE = ("sous_titres", "bandeau", "progression", "appel")   # posés sur le film : transparents d'office


def preparer_genre(anim, genre):
    """Ce qui change avec le genre : durée conseillée, transparence de l'habillage, textes d'exemple neutres."""
    anim["genre"] = genre
    anim["duree"] = duree_conseillee(genre)
    anim["horaire"] = None
    if genre in HABILLAGE:
        anim["transparent"] = True
    exemple = anim.get("titre") in TITRES_EXEMPLE()
    exemple_donnees = anim.get("donnees") in ([list(x) for x in EXEMPLE], [[_("2025"), 120.0], [_("2026"), 150.0]])
    if exemple and genre not in ("bandeau", "citation", "appel", "jauge", "comparaison", "chronologie", "liste"):
        anim["titre"], anim["sous_titre"] = _("Visiteurs, premier semestre"), _("Visiteurs par mois")
        if exemple_donnees:
            anim["donnees"] = [list(x) for x in EXEMPLE]
            anim["valeur"], anim["suffixe"] = sum(v for _l, v in EXEMPLE), ""
    if genre == "chiffres_cles" and exemple:
        anim["titre"], anim["sous_titre"] = _("Le semestre en chiffres"), ""
    elif genre == "chronologie" and exemple:
        anim["titre"], anim["sous_titre"] = _("Notre histoire"), ""
    elif genre == "liste" and exemple:
        anim["titre"], anim["sous_titre"] = _("Pourquoi l'essayer"), ""
    elif genre == "bandeau" and exemple:
        anim["titre"], anim["sous_titre"] = _("Camille Martin"), _("Responsable de l'atelier")
    elif genre == "citation" and exemple:
        anim["titre"], anim["sous_titre"] = _("La simplicité est la sophistication suprême."), _("proverbe")
    elif genre == "appel" and exemple:
        anim["titre"], anim["sous_titre"], anim["bouton"] = _("S'abonner pour la suite"), _("une vidéo chaque semaine"), _("S'abonner")
    elif genre == "jauge" and exemple:
        anim.update(titre=_("Objectif atteint"), sous_titre=_("sur l'année"))
        if exemple_donnees:
            anim.update(valeur=72, suffixe=" %")
    elif genre == "comparaison" and exemple:
        anim.update(titre=_("Avant / après"), sous_titre="")
        if exemple_donnees:
            anim["donnees"] = [[_("2025"), 120.0], [_("2026"), 150.0]]
    if genre in A_LIGNES and not anim.get("lignes"):
        anim["lignes"] = ([_("1998 : ouverture de l'atelier"), _("2010 : deuxième atelier"), _("2020 : boutique en ligne"),
                           _("2026 : 10 000 clients")] if genre == "chronologie" else
                          [_("Simple à prendre en main"), _("Rapide, même sur un portable"), _("Vos couleurs partout"),
                           _("Rien n'est payé sans votre accord")])
    return anim


def duree_conseillee(genre):
    return {"compteur": 4.5, "barres": 5.5, "courbe": 5.0, "titre": 4.0, "chiffres": 14.0, "bandeau": 5.0, "progression": 30.0,
            "defilement": 8.0, "sous_titres": 10.0, "camembert": 6.0, "jauge": 4.5, "comparaison": 5.0, "classement": 6.0,
            "chiffres_cles": 5.5, "chronologie": 7.0, "liste": 6.0, "citation": 6.0, "appel": 4.5}.get(genre, 6.0)


# ------------------------------------------------------------------ l'horaire : quand chaque élément arrive (1.0.0)
def horaire(anim):
    """Les instants (en secondes de l'animation) de chaque élément, communs aux trois moteurs. Par défaut ils suivent la
    vitesse et le décalage ; « Caler sur la voix ou la musique » les remplace (anim["horaire"], figé)."""
    if isinstance(anim.get("horaire"), dict) and anim["horaire"].get("genre") == anim.get("genre"):
        return anim["horaire"]
    D = float(anim.get("duree") or duree_conseillee(anim.get("genre")))
    V = max(0.1, reglage(anim, "vitesse"))
    dec = 0.06 + 0.22 * reglage(anim, "decalage")
    g = anim.get("genre") or "chiffres"
    n = len(anim.get("donnees") or EXEMPLE)
    h = {"genre": g, "duree": D, "scenes": {}}

    def compteur(a, b):
        h["scenes"]["compteur"] = [a, b]
        h["compteur"] = {"debut": a + 0.3 / V, "fin": a + 2.6 / V, "badge": a + 2.4 / V}

    def barres(a, b):
        h["scenes"]["barres"] = [a, b]
        h["barres"] = {"grille": a + 0.2 / V, "entrees": [a + (0.6 + i * dec) / V for i in range(n)], "halo": a + 2.6 / V}

    def courbe(a, b):
        h["scenes"]["courbe"] = [a, b]
        h["courbe"] = {"debut": a + 0.4 / V, "fin": a + 2.8 / V, "record": a + 2.8 / V}

    if g == "compteur":
        compteur(0, D)
    elif g == "barres":
        barres(0, D)
    elif g == "courbe":
        courbe(0, D)
    elif g == "titre":
        mots = (anim.get("titre") or "").split()
        h["scenes"]["titre"] = [0, D]
        h["titre"] = {"mots": [(0.15 + k * dec) / V for k in range(len(mots))], "trait": (0.4 + len(mots) * dec * 0.5) / V,
                      "sous_titre": 0.8 / V}
    elif g == "bandeau":
        h["scenes"]["bandeau"] = [0, D]
        h["bandeau"] = {"entree": 0.1 / V, "texte": 0.35 / V, "sortie": max(0.8, D - 0.7 / V)}
    elif g in ("progression", "defilement", "sous_titres"):
        h["scenes"][g] = [0, D]
    elif g == "jauge":
        h["scenes"][g] = [0, D]
        h[g] = {"debut": 0.4 / V, "fin": 2.6 / V}
    elif g == "citation":
        mots = (anim.get("titre") or "").split()
        h["scenes"][g] = [0, D]
        h[g] = {"mots": [(0.4 + k * dec * 0.6) / V for k in range(len(mots))], "auteur": (0.8 + len(mots) * dec * 0.6) / V}
    elif g == "appel":
        h["scenes"][g] = [0, D]
        h[g] = {"entree": 0.2 / V, "curseur": 0.9 / V, "clic": 1.9 / V}
    elif g in ("camembert", "comparaison", "classement", "chiffres_cles", "chronologie", "liste"):
        k = len(elements(anim))
        h["scenes"][g] = [0, D]
        h[g] = {"entrees": [(0.5 + i * dec * 2.2) / V for i in range(k)], "fin": (0.5 + k * dec * 2.2 + 0.6) / V}
    else:
        compteur(0, D * 4.3 / 14)
        barres(D * 4.0 / 14, D * 9.4 / 14)
        courbe(D * 9.2 / 14, D)
    return h


def _norm(t):
    import unicodedata
    t = "".join(x for x in unicodedata.normalize("NFD", str(t)) if unicodedata.category(x) != "Mn").lower()
    return re.sub(r"[^a-z0-9]", "", t)


def _nombre_dit(mot, valeur):
    """Le mot dit est-il ce chiffre (« 34 390 », « 34390 », « 34 000 » pour 34 390 arrondi, « 1,2 » million…) ?"""
    t = re.sub(r"[^\d,.]", "", str(mot))
    if not t or not any(c.isdigit() for c in t):
        return False
    try:
        v = _valeur(t)
    except ValueError:
        return False
    if not valeur:
        return False
    for k in (1, 1000, 1_000_000):
        if abs(v * k - valeur) <= max(1.0, abs(valeur) * 0.05):
            return True
    return False


def mots_dans(mots_montage, debut, duree):
    """Les mots du montage entendus pendant l'animation (posée à `debut`), en temps de l'animation : [[t0, t1, mot]]."""
    out = []
    for m in mots_montage or []:
        t0, t1 = float(m["t0"]) - debut, float(m["t1"]) - debut
        if t1 > 0 and t0 < duree:
            out.append([round(max(0.0, t0), 3), round(min(duree, t1), 3), m["mot"]])
    return out


def caler_voix(anim, mots):
    """Horaire calé sur la voix (mots en temps de l'animation) : le compteur finit quand le chiffre est dit, chaque barre
    arrive quand son libellé est dit, le record quand il est dit ; les scènes s'ouvrent juste avant. (horaire, trouvés)"""
    h = json.loads(json.dumps(horaire(dict(anim, horaire=None))))
    V = max(0.1, reglage(anim, "vitesse"))
    trouves = 0
    mots = [(float(a), float(b), w) for a, b, w in mots or []]

    def chercher(cond, apres=-1.0):
        return next((a for a, _b, w in mots if a >= apres and cond(w)), None)
    if "compteur" in h:
        v = anim.get("valeur")
        t = chercher(lambda w: _nombre_dit(w, v)) if v is not None else None
        if t is not None:
            fin = t + 0.25
            h["compteur"].update(fin=fin, debut=max(h["scenes"]["compteur"][0] + 0.1, fin - 2.3 / V), badge=fin - 0.1)
            trouves += 1
    if "barres" in h:
        apres = h["scenes"]["barres"][0] - 1.0
        e = h["barres"]["entrees"]
        for i, (lib, _v) in enumerate(anim.get("donnees") or []):
            cle = _norm(lib)[:4]
            t = chercher(lambda w, c=cle: len(c) >= 3 and _norm(w).startswith(c), apres) if cle else None
            if t is not None:
                e[i] = t
                apres = t
                trouves += 1
            elif i:
                e[i] = max(e[i], e[i - 1] + 0.35)          # pas dit : juste après la précédente
    if "courbe" in h:
        d = anim.get("donnees") or []
        rec = max(range(len(d)), key=lambda i: d[i][1]) if d else 0
        cle = _norm(d[rec][0])[:4] if d else ""
        t = chercher(lambda w: _norm(w).startswith("record") or (len(cle) >= 3 and _norm(w).startswith(cle)),
                     h["scenes"]["courbe"][0] - 0.5)
        if t is not None:
            c = h["courbe"]
            c["record"] = max(t, c["debut"] + 0.8)
            c["fin"] = max(c["debut"] + 0.8, min(c["fin"], c["record"]))
            trouves += 1
    g = anim.get("genre")
    if g in ("camembert", "comparaison", "classement", "chiffres_cles", "chronologie", "liste") and g in h:
        apres = -1.0
        e = h[g]["entrees"]
        for i, (lib, _v, txt) in enumerate(elements(anim)):
            mot = (str(lib or txt).split() or [""])[0]
            cle = _norm(mot)[:4]
            t = chercher(lambda w, c=cle: len(c) >= 2 and _norm(w).startswith(c), apres) if cle else None
            if t is not None and i < len(e):
                e[i] = t
                apres = t
                trouves += 1
            elif 0 < i < len(e):
                e[i] = max(e[i], e[i - 1] + 0.35)
        h[g]["fin"] = max(h[g]["fin"], (e[-1] + 0.6) if e else 0)
    if g == "jauge":
        v = anim.get("valeur")
        t = chercher(lambda w: _nombre_dit(w, v)) if v is not None else None
        if t is not None:
            h[g].update(fin=t + 0.25, debut=max(0.1, t + 0.25 - 2.2))
            trouves += 1
    if g == "citation":
        cit = [_norm(w) for w in (anim.get("titre") or "").split()]
        apres = 0.0
        for k, m in enumerate(cit):
            t = chercher(lambda w, m=m: m and _norm(w) == m, apres)
            if t is not None:
                h[g]["mots"][k] = t
                apres = t
                trouves += 1
    if "titre" in h:
        titre = [_norm(w) for w in (anim.get("titre") or "").split()]
        apres = 0.0
        for k, m in enumerate(titre):
            t = chercher(lambda w, m=m: m and _norm(w) == m, apres)
            if t is not None:
                h["titre"]["mots"][k] = t
                apres = t
                trouves += 1
    _ouvrir_scenes(h)
    return h, trouves


def _ouvrir_scenes(h):
    """Chaque scène s'ouvre au plus tard 0,6 s avant son premier élément, et la précédente se ferme en fondu juste après."""
    ordre = [k for k in ("compteur", "barres", "courbe") if k in h.get("scenes", {})]
    premiers = {"compteur": lambda: h["compteur"]["debut"] - 0.3, "barres": lambda: min(h["barres"]["entrees"] or [0]) - 0.6,
                "courbe": lambda: h["courbe"]["debut"] - 0.4}
    for i, k in enumerate(ordre):
        a, b = h["scenes"][k]
        a = max(0.0, min(a, premiers[k]()))
        if i:
            prec = ordre[i - 1]
            a = max(a, h["scenes"][prec][0] + 1.0)
            h["scenes"][prec][1] = min(h["scenes"][prec][1], a + 0.4)
        h["scenes"][k] = [round(a, 3), round(b, 3)]


def caler_musique(anim, temps, forts=()):
    """Horaire calé sur la musique (temps et temps forts, en temps de l'animation) : scènes et fin du compteur sur les temps
    forts, barres une par temps, mots du titre un par temps. (horaire, nombre de calages)"""
    h = json.loads(json.dumps(horaire(dict(anim, horaire=None))))
    temps = sorted(float(t) for t in temps or [] if 0 <= float(t) <= h["duree"])
    forts = sorted(float(t) for t in forts or [] if 0 <= float(t) <= h["duree"]) or temps
    if len(temps) < 2:
        return h, 0
    ecart = (temps[-1] - temps[0]) / max(1, len(temps) - 1)
    pas = 2 if ecart < 0.3 else 1                      # tempo rapide : un élément tous les deux temps

    def proche(t, grille):
        return min(grille, key=lambda x: abs(x - t))

    def suivants(t, k):
        g = [x for x in temps if x >= t - 0.02][::pas]
        return (g + [g[-1] + ecart * pas * (j + 1) for j in range(k)])[:k] if g else []
    n = 0
    if "compteur" in h:
        fin = proche(h["compteur"]["fin"], forts)
        h["compteur"].update(fin=fin, debut=max(0.1, fin - 2.3), badge=proche(fin + 0.1, temps))
        n += 1
    if "barres" in h:
        e = suivants(h["barres"]["entrees"][0], len(h["barres"]["entrees"]))
        if e:
            h["barres"]["entrees"] = e
            h["barres"]["halo"] = proche(e[-1] + ecart, temps)
            n += len(e)
    if "courbe" in h:
        h["courbe"]["record"] = proche(h["courbe"]["record"], forts)
        n += 1
    if "titre" in h:
        e = suivants(h["titre"]["mots"][0] if h["titre"]["mots"] else 0.15, len(h["titre"]["mots"]))
        if e:
            h["titre"]["mots"] = e
            n += len(e)
    if "bandeau" in h:
        h["bandeau"]["entree"] = proche(h["bandeau"]["entree"], forts)
        n += 1
    for g in ("camembert", "comparaison", "classement", "chiffres_cles", "chronologie", "liste"):
        if g in h and h[g]["entrees"]:
            e = suivants(h[g]["entrees"][0], len(h[g]["entrees"]))
            if e:
                h[g]["entrees"] = e
                h[g]["fin"] = e[-1] + ecart
                n += len(e)
    if "jauge" in h:
        h["jauge"]["fin"] = proche(h["jauge"]["fin"], forts)
        h["jauge"]["debut"] = max(0.1, h["jauge"]["fin"] - 2.2)
        n += 1
    if "citation" in h and h["citation"]["mots"]:
        e = suivants(h["citation"]["mots"][0], len(h["citation"]["mots"]))
        if e:
            h["citation"]["mots"] = e
            h["citation"]["auteur"] = e[-1] + ecart
            n += len(e)
    if "appel" in h:
        h["appel"]["clic"] = proche(h["appel"]["clic"], forts)
        n += 1
    for k in list(h["scenes"]):
        a, b = h["scenes"][k]
        if a > 0:
            h["scenes"][k][0] = proche(a, forts)
    _ouvrir_scenes(h)
    return h, n


# ------------------------------------------------------------------ ce que le montage fournit (1.0.0)
def mots_montage(projet):
    """Tous les mots transcrits du montage (piste vidéo et piste Voix), dans l'ordre : [{t0, t1, mot}]."""
    from . import montage_texte as MT
    out = []
    for piste in ("video", "voix"):
        try:
            out += MT.mots_du_montage(projet, piste)
        except Exception:      # noqa: BLE001 : une piste sans transcription
            pass
    return sorted(out, key=lambda m: m["t0"])


def a_transcrire(projet):
    from . import montage_texte as MT
    return sum(len(MT.rushes_a_transcrire(projet, p)) for p in ("video", "voix"))


def transcrire(projet, params, progression=None, arret=lambda: False):
    from . import montage_texte as MT
    n = 0
    for p in ("video", "voix"):
        n += MT.transcrire(projet, params, progression=progression, arret=arret, piste=p)
    return n


def mots_pour_sous_titres(projet, debut, fin=None, pause_fin=3.0, maxi=90.0):
    """Les mots à sous-titrer à partir de `debut` (jusqu'à `fin`, sinon jusqu'à une pause de 3 s) : (mots en temps de
    l'animation, durée)."""
    tous = [m for m in mots_montage(projet) if m["t1"] > debut]
    choisis = []
    for m in tous:
        if fin is not None and m["t0"] >= fin:
            break
        if fin is None and choisis and (m["t0"] - choisis[-1]["t1"] > pause_fin or m["t1"] - debut > maxi):
            break
        choisis.append(m)
    if not choisis:
        return [], 0.0
    duree = (fin - debut) if fin is not None else (choisis[-1]["t1"] - debut + 0.4)
    return mots_dans(choisis, debut, duree), round(max(1.0, duree), 2)


def temps_musique(projet):
    """Temps et temps forts de la première musique du montage, en temps de la timeline : (temps, forts)."""
    from . import rythme
    for c in sorted(projet.clips_piste("audio"), key=lambda x: x["debut"]):
        m = projet.media(c["media"])
        if not m:
            continue
        an = m.get("rythme")
        if not an:
            an = rythme.analyser(m["chemin"])
            m["rythme"] = an
        return rythme.temps_montage(c, an, False), rythme.temps_montage(c, an, True)
    return [], []


def chapitres(projet, debut=0.0, duree=None):
    """Les repères du montage comme chapitres de la barre de progression : [[t, nom]] en temps de l'animation."""
    out = []
    for m in sorted(getattr(projet, "marqueurs", []) or [], key=lambda x: x.get("t", 0)):
        t = float(m.get("t", 0)) - debut
        if 0 <= t < (duree if duree else 1e9):
            out.append([round(t, 2), m.get("texte") or _("Chapitre")])
    return out


# ------------------------------------------------------------------ sous-titres : les lignes
# 1.0.2 : sous-titres en 9:16 plus gros d'office (Philippe, 20/11 16h15) : texte ×1,3, lignes plus courtes pour tenir
ST_VERTICAL_TAILLE, ST_VERTICAL_CAR, ST_HORIZONTAL_CAR = 1.3, 16, 32


def lignes_st(mots, max_car=28, max_mots=6, pause=0.7):
    """Les mots regroupés en courtes lignes (au plus max_car caractères, coupées aux pauses) : [{t0, t1, mots: [[t0, t1, mot]]}]."""
    out, cour = [], []
    for m in mots or []:
        txt = " ".join(x[2] for x in cour + [m])
        if cour and (len(txt) > max_car or len(cour) >= max_mots or m[0] - cour[-1][1] > pause
                     or cour[-1][2].rstrip()[-1:] in ".!?"):
            out.append(cour)
            cour = []
        cour.append(list(m))
    if cour:
        out.append(cour)
    return [{"t0": l[0][0], "t1": max(l[-1][1], l[0][0] + 0.5), "mots": l} for l in out]


def reglage(anim, cle):
    d = next((x[4] for x in REGLAGES if x[0] == cle), 1.0)
    try:
        return float((anim.get("reglages") or {}).get(cle, d))
    except (TypeError, ValueError):
        return d


def avec_variante(anim, v):
    """Les trois propositions : la même animation, trois façons de bouger."""
    a = copy.deepcopy(anim)
    a["variante"] = v
    r = a.setdefault("reglages", {})
    if v == 1:
        r.update(vitesse=min(2.0, reglage(anim, "vitesse") * 1.35), rebond=max(0.6, reglage(anim, "rebond")),
                 lueur=max(0.8, reglage(anim, "lueur")), decalage=0.35)
    elif v == 2:
        r.update(vitesse=reglage(anim, "vitesse") * 0.85, rebond=0.0, lueur=0.0, decalage=0.7)
    return a


# ------------------------------------------------------------------ nombres et données
def nombre(v, decimales=None, langue=None):
    """1 234,5 en français (espace fine insécable), 1,234.5 en anglais ; entier si la valeur l'est."""
    langue = (langue or _langue_ui() or "fr")[:2]
    try:
        v = float(v)
    except (TypeError, ValueError):
        return str(v)
    if decimales is None:
        decimales = 0 if abs(v - round(v)) < 1e-9 or abs(v) >= 1000 else (1 if abs(v * 10 - round(v * 10)) < 1e-9 else 2)
    t = f"{v:,.{decimales}f}"
    if langue in ("fr", "es", "it", "de"):
        mil = "\u202f" if langue == "fr" else "."
        t = t.replace(",", "§").replace(".", ",").replace("§", mil)
        if langue == "es" and abs(v) < 10000:          # en espagnol, pas de séparateur sous 10 000
            t = t.replace(".", "")
    return t


def nombre_texte(anim, v):
    return f"{anim.get('prefixe') or ''}{nombre(v, anim.get('decimales'))}{anim.get('suffixe') or ''}"


def _valeur(t):
    t = str(t).strip().replace(" ", "").replace("\xa0", "").replace(" ", "")
    t = re.sub(r"[€$%£]", "", t)
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):        # 1.234,5
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", t):      # 1,234.5
        t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    return float(t)


def lire_donnees(texte):
    """Un tableau collé (Excel, Sheets, CSV, ou « Janvier 3120 » ligne par ligne) → [[libellé, valeur]]. Une ligne d'en-tête
    ou sans nombre est ignorée."""
    lignes = [l for l in (texte or "").replace("\r", "").split("\n") if l.strip()]
    if not lignes:
        return []
    sep = "\t" if any("\t" in l for l in lignes) else (";" if any(";" in l for l in lignes) else None)
    out = []
    for l in lignes:
        if sep:
            cases = [c.strip() for c in l.split(sep)]
        else:
            m = re.match(r"^(.*?)[\s:=,]+(-?[\d\s., \xa0]+\s*[€$%£]?)\s*$", l.strip())
            cases = [m.group(1), m.group(2)] if m else [l.strip()]
        if len(cases) < 2:
            continue
        lib = cases[0]
        for c in cases[1:]:
            try:
                out.append([lib, _valeur(c)])
                break
            except ValueError:
                continue
    return out[:24]


def lire_fichier(chemin):
    """Les deux premières colonnes d'un fichier Excel (.xlsx) ou CSV : [[libellé, valeur]]."""
    ext = os.path.splitext(chemin)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
        ws = wb.worksheets[0]
        lignes = []
        for row in ws.iter_rows(values_only=True):
            cases = [c for c in row if c is not None and str(c).strip() != ""]
            if len(cases) >= 2:
                lignes.append("\t".join(str(c) for c in cases[:2]))
            if len(lignes) > 60:
                break
        wb.close()
        return lire_donnees("\n".join(lignes))
    with open(chemin, encoding="utf-8-sig", errors="replace") as f:
        brut = f.read(200_000)
    try:
        dialecte = csv.Sniffer().sniff(brut[:4000], delimiters=";,\t")
        lignes = ["\t".join(r[:2]) for r in csv.reader(io.StringIO(brut), dialecte) if len(r) >= 2]
        return lire_donnees("\n".join(lignes))
    except csv.Error:
        return lire_donnees(brut)


# ------------------------------------------------------------------ zones sûres (Reels, Shorts, TikTok)
# ------------------------------------------------------------------ 1.1.16 : une ou deux images dans l'animation simple
PLACES_IMAGE = {"droite": _("à droite"), "gauche": _("à gauche"), "haut": _("en haut"), "coin": _("petite, dans un coin"),
                "fond": _("en fond, discrète")}
MAX_IMAGES = 2


def _taille_image(chemin):
    """(largeur, hauteur) d'une image : par Qt, sinon en lisant l'en-tête PNG ou JPEG (outils sans Qt)."""
    try:
        from PySide6.QtGui import QImageReader
        s = QImageReader(chemin).size()
        if s.isValid() and s.width() > 0:
            return s.width(), s.height()
    except ImportError:
        pass
    import struct
    try:
        with open(chemin, "rb") as f:
            d = f.read(65536)
        if d[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", d[16:24])
        i = 2
        while d[:2] == b"\xff\xd8" and i + 9 < len(d):
            if d[i] != 0xFF:
                break
            m, n = d[i + 1], struct.unpack(">H", d[i + 2:i + 4])[0]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", d[i + 5:i + 9])
                return w, h
            i += 2 + n
    except (OSError, struct.error):
        pass
    return 1, 1


def calques_images(anim):
    """Les images de l'animation simple (Philippe, 22/11 22h06 : « intégrer 1 ou 2 images si nécessaire ») : rectangle en pixels
    de l'image, opacité, apparition et départ, mêmes pour les trois moteurs. [{chemin, x, y, w, h, op, cover, t0, t1}]"""
    L, H = [int(x) // 2 * 2 for x in (anim.get("taille") or (1920, 1080))]
    zx, zy, zw, zh = zone_sure(dict(anim, taille=[L, H]))
    D = float(anim.get("duree") or duree_conseillee(anim.get("genre")))
    out = []
    for k, im in enumerate((anim.get("images") or [])[:MAX_IMAGES]):
        ch = (im or {}).get("chemin") or ""
        if not os.path.exists(ch):
            continue
        iw, ih = _taille_image(ch)
        r = ih / iw
        place = im.get("place") if im.get("place") in PLACES_IMAGE else "droite"
        op, cover = 1.0, False
        if place == "fond":
            x, y, w, h, op, cover = 0, 0, L, H, 0.3, True
        elif place in ("gauche", "droite"):
            w = zw * (0.42 if H > L else 0.3)
            h = min(w * r, zh * 0.62)
            w = h / r
            x = zx if place == "gauche" else zx + zw - w
            y = zy + (zh - h) / 2
        elif place == "haut":
            h = zh * 0.28
            w = min(h / r, zw * 0.7)
            h = w * r
            x, y = zx + (zw - w) / 2, zy
        else:
            w = min(L, H) * 0.18
            h = w * r
            x, y = zx, zy + zh - h
        if k == 1 and out and out[0]["x"] == x and out[0]["y"] == y and not cover:      # même place : à côté de la première
            x = max(zx, x - w * 1.08) if x > zx + zw / 2 else min(zx + zw - w, x + w * 1.08)
        t0 = 0.15 + 0.3 * k
        out.append({"n": k, "chemin": ch, "x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1), "op": op,
                    "cover": cover, "t0": t0, "t1": max(t0 + 0.6, D - 0.45)})
    return out


def zone_sure(anim):
    """Le rectangle (x, y, l, h) où poser textes et chiffres : en vertical, les boutons et la légende des réseaux couvrent le
    haut, le bas et la droite (zones mortes) ; en horizontal, une marge de 7 %."""
    L, H = anim.get("taille") or (1920, 1080)
    if H > L and anim.get("zones_sures", True):
        return (int(L * 0.07), int(H * 0.13), int(L * 0.80), int(H * 0.62))
    return (int(L * 0.08), int(H * 0.09), int(L * 0.84), int(H * 0.82))


# ------------------------------------------------------------------ moteurs : état, prix, conseil
MOTEURS = {
    "maison": {"nom": _("PhilCut (moteur maison)"), "aide": _("Dessiné par PhilCut : rien à installer, aperçu immédiat, gratuit.")},
    "hyperframes_local": {"nom": _("HyperFrames sur ce poste"),
                          "aide": _("HTML et GSAP rendus par un Chrome invisible (HeyGen, libre, Apache 2.0) ; gratuit, environ "
                                    "300 Mo à installer une fois ; le plus riche pour les effets et les sous-titres animés.")},
    "hyperframes_cloud": {"nom": _("HyperFrames chez HeyGen (cloud)"),
                          "aide": _("La même composition rendue sur les serveurs de HeyGen : rien à installer, rapide ; payé à la "
                                    "minute de vidéo avec votre clef HeyGen (environ 0,10 $ la minute en 1080p 30 i/s).")},
    "remotion": {"nom": _("Remotion sur ce poste"),
                 "aide": _("Le moteur de l'étalon « Chiffres » ; gratuit pour un particulier, une structure de 3 personnes au plus "
                           "ou une association ; au-delà, une licence entreprise Remotion est obligatoire.")},
}
PRIX_HEYGEN_MIN = {(1080, 30): 0.10, (1080, 60): 0.20, (2160, 30): 0.15, (2160, 60): 0.30}   # $/min (HeyGen, nov. 2026)


def prix(anim, moteur):
    if moteur != "hyperframes_cloud":
        return 0.0
    L, H = anim.get("taille") or (1920, 1080)
    grand = 2160 if max(L, H) > 1920 else 1080
    fps = 60 if int(anim.get("cadence") or 30) > 30 else 30
    minutes = max(1.0, float(anim.get("duree") or 6) / 60.0)        # au moins une minute comptée (prudence)
    return round(PRIX_HEYGEN_MIN[(grand, fps)] * minutes, 2)


def etat(moteur, params=None):
    """(possible, texte) : ce qui manque pour ce moteur, dit en clair."""
    if moteur == "maison":
        return True, _("prêt")
    if moteur == "hyperframes_local":
        from . import motion_html as MH
        return (True, _("installé")) if MH.local_pret() else (False, _("à installer (environ 300 Mo, une fois)"))
    if moteur == "hyperframes_cloud":
        from . import generateurs_video as GV
        return (True, _("clef HeyGen présente")) if GV.clef(params, "heygen") else (False, _("clef HeyGen à saisir"))
    if moteur == "remotion":
        from . import motion_remotion as MR
        if not (params or {}).get("remotion_licence"):
            return False, _("licence à confirmer (une fois)")
        return (True, _("installé")) if MR.pret() else (False, _("à installer (une fois)"))
    return False, "?"


def conseiller(anim, params=None):
    """(moteur, raison) : le moteur conseillé pour cette animation sur ce poste."""
    if anim.get("genre") in ("sous_titres", "bandeau", "progression", "defilement"):
        if etat("hyperframes_local", params)[0]:
            return "hyperframes_local", _("installé ici, gratuit : le plus fin pour le texte animé et l'habillage")
        return "maison", _("l'habillage se fait bien ici : gratuit, rien à installer, aperçu immédiat")
    if anim.get("genre") in GENRES and not anim.get("html"):
        if etat("hyperframes_local", params)[0] and float(reglage(anim, "lueur")) > 0.7:
            return "hyperframes_local", _("installé ici, gratuit, et le plus fin pour les lueurs et les dégradés")
        return "maison", _("vos chiffres et titres se font très bien ici : gratuit, rien à installer, aperçu immédiat")
    if anim.get("genre") == "libre" and anim.get("moteur_libre") == "remotion":
        return "remotion", _("animation libre écrite pour Remotion : Remotion la rend ici, gratuitement")
    if etat("hyperframes_local", params)[0]:
        return "hyperframes_local", _("animation libre écrite par l'IA : HyperFrames la rend ici, gratuitement")
    return "hyperframes_cloud", _("animation libre écrite par l'IA : sans HyperFrames installé, HeyGen la rend pour quelques centimes")


# ------------------------------------------------------------------ fabriquer
def dossier():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "animations")
    os.makedirs(d, exist_ok=True)
    return d


def sortie_pour(anim, nom=""):
    base = re.sub(r"[^\w-]+", "_", (nom or anim.get("titre") or "animation"))[:40].strip("_") or "animation"
    ext = ".mov" if anim.get("transparent") else ".mp4"
    return os.path.join(dossier(), f"{time.strftime('%Y%m%d_%H%M%S')}_{base}{ext}")


def fabriquer(params, anim, sortie, moteur="maison", progression=None, arret=lambda: False):
    """Fabrique l'animation avec le moteur choisi ; la recette est gardée à côté (« .motion.json ») pour la reprendre."""
    if moteur == "maison":
        from . import motion_maison as MM
        r = MM.fabriquer(anim, sortie, progression, arret)
    elif moteur in ("hyperframes_local", "hyperframes_cloud"):
        from . import motion_html as MH
        r = (MH.rendre_local if moteur == "hyperframes_local" else MH.rendre_cloud)(params, anim, sortie, progression, arret)
    elif moteur == "remotion":
        from . import motion_remotion as MR
        r = MR.rendre(params, anim, sortie, progression, arret)
    else:
        raise ValueError(moteur)
    try:
        json.dump(dict(anim, moteur=moteur), open(r + ".motion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except OSError:
        pass
    if moteur == "hyperframes_cloud":
        from .credit_ia import noter_depense
        noter_depense("heygen", prix(anim, moteur))
    return r


def recette(chemin):
    try:
        with open(chemin + ".motion.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ l'IA prépare, l'IA corrige
CONSIGNE_IA = """Tu prépares une animation de motion design pour une vidéo (chiffres, graphiques, titres). L'utilisateur décrit ce
qu'il veut ; tu remplis la fiche. Réponds en JSON seul :
{{"genre": "compteur|barres|courbe|titre|chiffres|camembert|jauge|comparaison|classement|chiffres_cles|chronologie|liste|citation|appel",
"titre": "...", "sous_titre": "...", "valeur": nombre ou null, "lignes": ["...", ...], "bouton": "texte du bouton",
"prefixe": "", "suffixe": " €" ou " %" ou "", "badge": "texte court ou vide", "titre_barres": "...", "titre_courbe": "...",
"sous_titre_courbe": "...", "donnees": [["libellé", nombre], ...], "source": "source des chiffres si donnée, sinon vide",
"duree": secondes, "reglages": {{"vitesse": 0.5..2, "rebond": 0..1, "decalage": 0..1, "epaisseur": 0.2..1, "lueur": 0..1,
"taille_texte": 0.6..1.4}}, "message": "ce que tu as compris, en une phrase"}}
Genres : camembert (parts d'un tout), jauge (un pourcentage, valeur de 0 à 100), comparaison (deux valeurs, avant/après),
classement (du plus grand au plus petit), chiffres_cles (2 à 4 chiffres en cartes), chronologie (lignes « 2020 : fait »),
liste (lignes de points clefs), citation (titre = la citation, sous_titre = l'auteur), appel (titre, sous_titre, bouton).
Règles : n'invente jamais de chiffres ; si l'utilisateur n'en donne pas, garde ceux de la fiche actuelle. Textes courts (un
titre tient sur une ligne), dans la langue de l'utilisateur ({langue}). Chiffres arrondis comme il les a écrits.
Fiche actuelle : {fiche}"""


def _fiche_ia(anim):
    return json.dumps({k: anim.get(k) for k in ("genre", "titre", "sous_titre", "valeur", "prefixe", "suffixe", "badge", "lignes", "bouton",
                                                 "titre_barres", "titre_courbe", "sous_titre_courbe", "donnees", "source", "duree",
                                                 "reglages")}, ensure_ascii=False)


def appliquer_ia(anim, r):
    a = copy.deepcopy(anim)
    if not isinstance(r, dict):
        return a
    if r.get("genre") in GENRES:
        a["genre"] = r["genre"]
    for k in ("titre", "sous_titre", "prefixe", "suffixe", "badge", "titre_barres", "titre_courbe", "sous_titre_courbe", "source", "bouton"):
        if isinstance(r.get(k), str):
            a[k] = r[k][:120]
    if isinstance(r.get("lignes"), list):
        lg = [str(x).strip()[:90] for x in r["lignes"] if str(x).strip()]
        if lg:
            a["lignes"] = lg[:8]
    if isinstance(r.get("valeur"), (int, float)):
        a["valeur"] = float(r["valeur"])
    d = []
    for x in r.get("donnees") or []:
        if isinstance(x, (list, tuple)) and len(x) >= 2:
            try:
                d.append([str(x[0])[:24], float(x[1])])
            except (TypeError, ValueError):
                pass
    if d:
        a["donnees"] = d[:24]
        if not isinstance(r.get("valeur"), (int, float)):
            a["valeur"] = sum(v for _l, v in d)
    try:
        a["duree"] = max(2.0, min(60.0, float(r.get("duree") or a["duree"])))
    except (TypeError, ValueError):
        pass
    for k, _l, lo, hi, _d in REGLAGES:
        v = (r.get("reglages") or {}).get(k)
        if isinstance(v, (int, float)):
            a.setdefault("reglages", {})[k] = max(lo, min(hi, float(v)))
    return a


def preparer_ia(params, description, anim, niveau="claude"):
    """La description de l'utilisateur → la fiche de l'animation ; (fiche, message)."""
    from . import assistant_creation as A
    r = A.demander(params, CONSIGNE_IA.format(langue=A._langue(), fiche=_fiche_ia(anim)), description, (), niveau, max_jetons=1500)
    return appliquer_ia(anim, r), (r or {}).get("message", "") if isinstance(r, dict) else ""


def corriger_ia(params, anim, remarque, instant=None, niveau="claude"):
    """Une remarque (« à 0:03 la barre de juin est trop rouge ») → la fiche corrigée."""
    texte = (f"A {instant:.1f} s : " if instant is not None else "") + remarque
    return preparer_ia(params, _("Corrige la fiche selon cette remarque : {r}", r=texte), anim, niveau)
