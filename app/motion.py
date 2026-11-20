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
}
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


def nouvelle(genre="chiffres", charte=None, taille=(1920, 1080)):
    from . import charte as CH
    d = sum(v for _l, v in EXEMPLE)
    return {"format": FORMAT, "genre": genre if genre in GENRES else "chiffres", "titre": _("Visiteurs, premier semestre"),
            "sous_titre": _("Visiteurs par mois"), "valeur": d, "prefixe": "", "suffixe": "", "badge": _("▲ +23 % sur un an"),
            "titre_barres": _("Mois après mois"), "titre_courbe": _("La tendance"), "sous_titre_courbe": _("Juin bat le record du semestre"),
            "donnees": [list(x) for x in EXEMPLE], "source": "", "duree": duree_conseillee(genre), "taille": list(taille),
            "cadence": 30, "transparent": False, "charte": copy.deepcopy(charte or CH.DEFAUT),
            "reglages": {k: d_ for k, _l, _a, _b, d_ in REGLAGES}, "variante": 0, "zones_sures": taille[1] > taille[0]}


def duree_conseillee(genre):
    return {"compteur": 4.5, "barres": 5.5, "courbe": 5.0, "titre": 4.0, "chiffres": 14.0}.get(genre, 6.0)


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
    if anim.get("genre") in GENRES and not anim.get("html"):
        if etat("hyperframes_local", params)[0] and float(reglage(anim, "lueur")) > 0.7:
            return "hyperframes_local", _("installé ici, gratuit, et le plus fin pour les lueurs et les dégradés")
        return "maison", _("vos chiffres et titres se font très bien ici : gratuit, rien à installer, aperçu immédiat")
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
{{"genre": "compteur|barres|courbe|titre|chiffres", "titre": "...", "sous_titre": "...", "valeur": nombre ou null,
"prefixe": "", "suffixe": " €" ou " %" ou "", "badge": "texte court ou vide", "titre_barres": "...", "titre_courbe": "...",
"sous_titre_courbe": "...", "donnees": [["libellé", nombre], ...], "source": "source des chiffres si donnée, sinon vide",
"duree": secondes, "reglages": {{"vitesse": 0.5..2, "rebond": 0..1, "decalage": 0..1, "epaisseur": 0.2..1, "lueur": 0..1,
"taille_texte": 0.6..1.4}}, "message": "ce que tu as compris, en une phrase"}}
Règles : n'invente jamais de chiffres ; si l'utilisateur n'en donne pas, garde ceux de la fiche actuelle. Textes courts (un
titre tient sur une ligne), dans la langue de l'utilisateur ({langue}). Chiffres arrondis comme il les a écrits.
Fiche actuelle : {fiche}"""


def _fiche_ia(anim):
    return json.dumps({k: anim.get(k) for k in ("genre", "titre", "sous_titre", "valeur", "prefixe", "suffixe", "badge",
                                                 "titre_barres", "titre_courbe", "sous_titre_courbe", "donnees", "source", "duree",
                                                 "reglages")}, ensure_ascii=False)


def appliquer_ia(anim, r):
    a = copy.deepcopy(anim)
    if not isinstance(r, dict):
        return a
    if r.get("genre") in GENRES:
        a["genre"] = r["genre"]
    for k in ("titre", "sous_titre", "prefixe", "suffixe", "badge", "titre_barres", "titre_courbe", "sous_titre_courbe", "source"):
        if isinstance(r.get(k), str):
            a[k] = r[k][:120]
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
