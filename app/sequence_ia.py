"""Séquence IA (0.9.33) : une petite histoire en plusieurs plans, avec des personnages qui restent les mêmes d'un plan à
l'autre, des lieux, des répliques dites avec une manière de parler, et une musique.

Exemple : « deux pilotes arrivent sur un aérodrome, se préparent, vérifient l'avion, puis décollent ; l'un à la manière
d'Alain Delon, l'autre à la manière de Simon Templar ».

Principes retenus :
- « à la manière de » décrit un style (allure, jeu, manière de parler), jamais un visage, une voix clonée ni un personnage :
  le nom ne part jamais vers un moteur (styles_ia.transposer, diction.PAR_REFERENCE) ;
- la continuité vient de la description de chaque personnage, recopiée mot pour mot dans chaque plan, et des images de
  référence (personnes qui ont donné leur accord, lieux) : elles servent à composer l'image de départ de chaque plan ;
- trois moteurs vidéo : l'IA de ce poste (gratuite, courte et lente), un générateur cloud avec votre clef (Gemini Omni,
  Kling… prix annoncé et confirmé), ou Google Flow (votre abonnement, pas à pas) ;
- rien n'est posé sans avoir été regardé : chaque plan se regarde, se refait, puis la séquence se monte d'un coup.
"""
import copy
import json
import os
import re
import time

from .langue import _

VERSION = 1
DUREE_PLAN = 6


def nouvelle(format_="16:9"):
    return {"version": VERSION, "titre": "", "histoire": "", "format": format_, "moteur": "locale", "voix": "local",
            "musique": {"active": True, "phrase": ""}, "personnages": [], "lieux": [], "plans": [], "cree": time.time()}


def personnage(nom="", description="", style=""):
    return {"nom": nom, "description": description, "style": style, "maniere": "", "images": []}


def lieu(nom="", description=""):
    return {"nom": nom, "description": description, "images": []}


def plan(action="", personnages=None, lieu_="", duree=DUREE_PLAN, repliques=None, camera=""):
    return {"action": action, "personnages": list(personnages or []), "lieu": lieu_, "duree": int(duree), "camera": camera,
            "repliques": list(repliques or []), "consigne": "", "image": "", "fichier": "", "voix": []}


# ------------------------------------------------------------------ découpage de l'histoire en plans
_SEPARATEURS = r"(?:[.;!?\n]+|\bpuis\b|\bensuite\b|\bet enfin\b|\bthen\b)"


_ENCHAINEMENTS = re.compile(r"\s*(?:,\s*)?\b(?:puis|ensuite|avant de|après avoir|et enfin|pour s'|pour se|pour que|afin que|pendant que)\b\s*|"
                            r"\s+et\s+(?=(?:s'|se |l'|lui |y |en )?(?!(?:le|la|les|un|une|des|du|de|son|sa|ses|mon|ma|leur|leurs|ce|cette)\b)"
                            r"\w{3,}(?:e|ent|it|ait)\b)", re.I)


def actions_multiples(action):
    """L'action décrit-elle plusieurs actions enchaînées (« contourne le bureau et s'assoit ») ? Renvoie la position de la
    coupe (début, fin du lien) ou None. Les moteurs vidéo ne savent bien faire qu'UNE action simple par plan."""
    for m in _ENCHAINEMENTS.finditer(action or ""):
        if 3 < m.start() < len(action) - 4:
            return m.start(), m.end()
    return None


def couper_plan(seq, i):
    """Coupe le plan i en deux à l'enchaînement d'actions : deux plans d'une action chacun (durée partagée, mêmes
    personnages, lieu et caméra). Renvoie True si la coupe a eu lieu."""
    pl = seq["plans"][i]
    pos = actions_multiples(pl.get("action"))
    if not pos:
        return False
    a, b = pl["action"][:pos[0]].strip(" ,"), pl["action"][pos[1]:].strip(" ,")
    sujet = ""
    for n in pl.get("personnages") or []:
        if a.lower().startswith(n.lower()):
            sujet = n
    if sujet and not b.lower().startswith(sujet.lower()):
        b = f"{sujet} {b}"
    elif not sujet and pl.get("personnages") and len(pl["personnages"]) == 1 and not re.match(
            r"(?i)(?:le|la|les|l'|un|une|des|il|elle|ils|elles|on|the|a|an|he|she|they)\b", b):
        b = f"{pl['personnages'][0]} {b}"         # « s'assoit » → « Hélène s'assoit » ; pas devant un sujet déjà là
    elif not sujet and not re.match(r"(?i)(?:le|la|les|l'|un|une|des|il|elle|ils|elles|on|the|a|an|he|she|they)\b", b):
        g = re.match(r"(?i)((?:le|la|les|l'|un|une|des|the|a|an)\s*[^\s,]+)", a)     # 0.9.86 : « s'éloigne » → « La voiture s'éloigne »
        if g:
            b = f"{g.group(1)} {b}"
    d = max(3, int(round(float(pl.get("duree") or DUREE_PLAN) / 2 + 0.5)))
    p1 = dict(pl, action=a[0].upper() + a[1:], duree=d, consigne="", fichier="", image="")
    if "clef" in pl:                               # 0.9.87 : l'image clef reste à la fin de la seconde moitié
        p1.update(clef=False, sans_fin=True, image_fin="", fin_reelle=False)
    p2 = dict(pl, action=b[0].upper() + b[1:], duree=d, consigne="", fichier="", image="", repliques=[], voix=[])
    seq["plans"][i:i + 1] = [p1, p2]
    return True


def decouper_simple(histoire):
    """Sans IA : une phrase (ou un « puis ») = un plan."""
    morceaux = [m.strip(" ,") for m in re.split(_SEPARATEURS, histoire or "", flags=re.I)]
    return [plan(m[0].upper() + m[1:]) for m in morceaux if len(m) > 3][:12]


CONSIGNE_DECOUPER = """Tu es scénariste et réalisateur. Découpe cette petite histoire en plans de cinéma courts (4 à 6 secondes chacun,
12 au plus), en français. REGLE ESSENTIELLE : UNE SEULE action simple par plan (« elle s'assoit », « il ouvre la porte »),
jamais deux actions enchaînées (« elle contourne le bureau et s'assoit » = deux plans). Des gestes lents et physiquement possibles :
on contourne les meubles, on ne traverse jamais un objet. Réponds en JSON strict, sans texte autour :
{{"personnages": [{{"nom": "prénom court inventé", "description": "apparence physique et vêtements, précis et constants (âge, carrure,
cheveux, tenue)", "style": "nom de la personne ou du personnage dont il a le style, si l'histoire en cite un, sinon vide"}}],
"lieux": [{{"nom": "nom court", "description": "description visuelle précise (lumière, saison, détails)"}}],
"plans": [{{"action": "ce qu'on voit : une seule action simple", "personnages": ["noms présents"], "lieu": "nom du lieu", "duree": 6,
"camera": "cadrage et mouvement (plan large, travelling, gros plan…)", "repliques": [{{"qui": "nom", "texte": "réplique courte,
écrite dans la manière de parler de son style, sans jamais citer une réplique existante"}}]}}]}}
Garde les personnages et lieux déjà décrits par l'utilisateur. Histoire :
{histoire}
{deja}"""


def _json(texte):
    t = (texte if isinstance(texte, str) else json.dumps(texte)).strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    i, j = t.find("{"), t.rfind("}")
    return json.loads(t[i:j + 1]) if i >= 0 and j > i else {}


def _demander(params, systeme, demande, niveau, json_attendu=False, max_jetons=3000):
    if niveau == "locale":
        from . import ia_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise RuntimeError(_("Aucun modèle d'IA locale pour écrire : installez « Vision et texte » dans Préférences › IA locale, "
                                 "ou choisissez l'IA cloud."))
        return ia_locale.generer(modele, demande, [], systeme=systeme, json_attendu=json_attendu, params=params)
    from . import ia
    return ia.demander(params or {}, systeme, demande, json_attendu=json_attendu, max_jetons=max_jetons)


def decouper_ia(seq, params, niveau="locale"):
    """L'IA propose personnages, lieux et plans (avec répliques) ; ce que l'utilisateur a déjà décrit est gardé."""
    deja = ""
    if seq["personnages"] or seq["lieux"]:
        deja = "Déjà décrits : " + json.dumps({"personnages": [{k: p[k] for k in ("nom", "description", "style")} for p in seq["personnages"]],
                                               "lieux": [{k: l_[k] for k in ("nom", "description")} for l_ in seq["lieux"]]},
                                              ensure_ascii=False)
    r = _json(_demander(params, "Tu écris des découpages de films courts. JSON uniquement.",
                        CONSIGNE_DECOUPER.format(histoire=seq["histoire"].strip(), deja=deja), niveau, json_attendu=True))
    if not r.get("plans"):
        raise RuntimeError(_("L'IA n'a pas proposé de plans ; reformulez l'histoire ou découpez sans IA."))
    return fusionner(seq, r)


def fusionner(seq, r):
    """Ajoute à la séquence les personnages et lieux proposés (sans écraser ceux de l'utilisateur) et remplace les plans."""
    s = copy.deepcopy(seq)
    noms = {p["nom"].lower() for p in s["personnages"]}
    for p in r.get("personnages") or []:
        if p.get("nom") and p["nom"].lower() not in noms:
            s["personnages"].append(personnage(p["nom"], p.get("description", ""), p.get("style", "")))
            noms.add(p["nom"].lower())
    lieux = {l_["nom"].lower() for l_ in s["lieux"]}
    for l_ in r.get("lieux") or []:
        if l_.get("nom") and l_["nom"].lower() not in lieux:
            s["lieux"].append(lieu(l_["nom"], l_.get("description", "")))
            lieux.add(l_["nom"].lower())
    s["plans"] = []
    for p in (r.get("plans") or [])[:12]:
        rep = [{"qui": x.get("qui", ""), "texte": x.get("texte", "")} for x in p.get("repliques") or [] if x.get("texte")]
        s["plans"].append(plan(p.get("action", ""), p.get("personnages") or [], p.get("lieu", ""),
                               max(3, min(10, int(p.get("duree") or DUREE_PLAN))), rep, p.get("camera", "")))
    return s


# ------------------------------------------------------------------ consignes (anglais, sans aucun nom de célébrité)
def _anglais(texte, traduire):
    if not traduire or not texte:
        return texte
    try:
        from .traduction_recherche import phrase_en_anglais
        return phrase_en_anglais(texte)[0] or texte
    except Exception:
        return texte


def jeu_du_style(style, params=None):
    """« Alain Delon » → allure et jeu en anglais (jamais le nom, jamais le visage). Le décor du style n'est pas repris :
    c'est le lieu du plan qui décide."""
    if not (style or "").strip():
        return ""
    from . import styles_ia as S
    refs = S._toutes(params)
    net = S._net(style).strip()
    for cle, (nom, d) in refs.items():
        if cle == net or nom.lower() == net:
            return d.get("jeu") or d.get("image") or ""
    t = S.transposer(f"à la manière de {style}", "video", params)
    return t.get("ajout", "")


def maniere_de_parler(p, params=None):
    """Manière de parler du personnage : choisie, sinon déduite de son style (froid pour Delon, gentleman pour Templar…)."""
    if p.get("maniere"):
        return p["maniere"]
    from . import diction as D
    if p.get("style"):
        m = D.style_depuis(f"comme {p['style']}", "video", params)[0]
        if m != "naturel":
            return m
    return "naturel"


def fiche_personnage(p, params=None, traduire=True):
    """Description constante, recopiée telle quelle dans chaque plan : c'est elle qui garde le personnage identique."""
    desc = _anglais((p.get("description") or "").strip(), traduire)
    jeu = jeu_du_style(p.get("style", ""), params)
    lettre = chr(65 + max(0, int(p.get("_rang", 0))))
    tenue = p.get("tenue") or {}
    t_en = tenue.get("en") or _anglais(tenue.get("description", ""), traduire)
    bouts = [x for x in (desc, jeu, ("wearing " + t_en) if t_en else "") if x]     # 0.9.88 : la tenue de la scène
    return f"Character {lettre}: " + ("; ".join(bouts) if bouts else "a person")


def consigne(seq, pl, params=None, traduire=True):
    """Consigne détaillée du plan pour un générateur vidéo, en anglais, autonome (chaque plan est généré seul)."""
    rangs = {p["nom"].lower(): i for i, p in enumerate(seq["personnages"])}
    persos = []
    for n in pl.get("personnages") or []:
        p = next((x for x in seq["personnages"] if x["nom"].lower() == n.lower()), None)
        if p:
            persos.append(fiche_personnage(dict(p, _rang=rangs[p["nom"].lower()]), params, traduire))
    li = next((x for x in seq["lieux"] if x["nom"].lower() == (pl.get("lieu") or "").lower()), None)
    action = pl.get("action", "")
    for n, i in rangs.items():                       # les prénoms deviennent « Character A » : le moteur ne voit pas de nom
        action = re.sub(r"(?i)\b" + re.escape(n) + r"\b", f"Character {chr(65 + i)}", action)
    action = _anglais(action, traduire)
    f = "vertical 9:16" if seq.get("format") == "9:16" else "widescreen 16:9"
    morceaux = [f"Cinematic shot, {f}, about {int(pl.get('duree') or DUREE_PLAN)} seconds."]
    if li:
        morceaux.append("Setting: " + _anglais(li.get("description") or li["nom"], traduire) + ".")
    if persos:
        morceaux.append(" ".join(x.rstrip(".") + "." for x in persos))
    morceaux.append("Action: " + action.rstrip(".") + ".")
    vus = {n.lower() for n in visibles(seq, pl)}
    caches = [f"Character {chr(65 + i)}" for n, i in rangs.items() if n not in vus]
    if caches and seq["personnages"]:               # 0.9.86 : continuité, ceux qui sont sortis ne reviennent pas
        hors = _anglais(pl.get("hors_champ") or "", traduire).rstrip(".")
        morceaux.append("Not visible in this shot: " + ", ".join(caches) + (f" ({hors})" if hors else "") +
                        ". Nobody else appears.")
    if pl.get("camera"):
        morceaux.append("Camera: " + _anglais(pl["camera"], traduire).rstrip(".") + ".")
    if seq.get("voix") == "aucune":                  # 0.9.68 : histoire sans voix
        morceaux.append("Nobody speaks, no dialogue, closed mouths.")
    elif seq.get("voix") == "moteur" and pl.get("repliques"):     # le moteur fait parler : il reçoit les répliques telles quelles
        lignes = " ".join(f'Character {chr(65 + rangs[r["qui"].lower()])} says: "{r["texte"]}".' if (r.get("qui") or "").lower() in rangs else
                          f'Someone says: "{r["texte"]}".' for r in pl["repliques"])
        morceaux.append(lignes + " Natural lip sync, no subtitles.")
    elif pl.get("repliques"):
        morceaux.append("The characters talk briefly (lips moving), no subtitles.")
    morceaux.append("One single simple action, slow and natural, physically plausible: people walk around furniture and never "
                    "pass through objects or tables; steady camera unless stated.")
    if images_du_plan(seq, pl):
        morceaux.append("The people and the place look exactly like in the starting image.")
    morceaux.append("Same characters, same clothes and same light as the other shots of this sequence. Realistic, high detail, "
                    "natural motion, no text, no watermark, no logo, no famous person.")
    return " ".join(morceaux)


CONSIGNE_AMELIORER = """You improve a prompt for an AI video generator. Keep EXACTLY, word for word, every "Character X: ..." description
and the "Setting:" sentence (continuity between shots). Make the action, camera movement, lighting, lens and atmosphere more
precise and cinematic, in English, under 110 words. Keep ONE single simple, slow, physically plausible action (people walk around
furniture, never through objects); never add a second action. Never add a real person's name, a known character or a logo. Answer with the
prompt only.

Prompt:
{c}"""


def ameliorer(texte, params, niveau="locale"):
    r = _demander(params, "You are a cinematographer writing prompts for video generators.", CONSIGNE_AMELIORER.format(c=texte), niveau,
                  max_jetons=600)
    r = (r if isinstance(r, str) else str(r)).strip().strip('"')
    for p in re.findall(r"Character [A-Z]:[^.]*\.", texte):              # garde-fou : les fiches restent intactes
        if p not in r:
            r = p + " " + r
    return r or texte


# ------------------------------------------------------------------ fichiers et fabrication
def dossier(seq):
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "sequences", time.strftime("%Y%m%d_%H%M%S", time.localtime(seq.get("cree") or time.time())))
    os.makedirs(d, exist_ok=True)
    return d


def enregistrer(seq):
    chemin = os.path.join(dossier(seq), "sequence.json")
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(seq, f, ensure_ascii=False, indent=1)
    return chemin


def visibles(seq, pl):
    """Noms des personnages qu'on VOIT dans le plan. 0.9.86 : une fois la continuité établie (`visibles_fixes`), une liste
    vide veut dire « personne » (la voiture qui démarre, les passagères déjà dedans) ; avant, vide = tout le monde."""
    noms = [n for n in pl.get("personnages") or [] if n.strip()]
    if noms or pl.get("visibles_fixes"):
        return noms
    return [x["nom"] for x in seq["personnages"]]


def images_du_plan(seq, pl):
    """Images de référence utiles au plan : celles des personnages présents, puis celles du lieu (au plus 4)."""
    out = []
    noms = visibles(seq, pl)
    for n in noms:
        p = next((x for x in seq["personnages"] if x["nom"].lower() == n.lower()), None)
        out += [i for i in (p or {}).get("images") or [] if os.path.exists(i)]
    li = next((x for x in seq["lieux"] if x["nom"].lower() == (pl.get("lieu") or "").lower()), None)
    if li and li.get("planche") and os.path.exists(li["planche"]):
        out.append(li["planche"])                 # 0.9.88 : la planche du lieu (quatre vues) en premier
    out += [i for i in (li or {}).get("images") or [] if os.path.exists(i)]
    return out[:4]


def image_depart(seq, i, params, moteur_image="gemini", precision=""):
    """Image de départ du plan i, composée à partir des images de référence (Gemini : personnages et lieu réunis ;
    IA de ce poste : image du lieu retravaillée). Renvoie le chemin, ou "" s'il n'y a rien pour la composer."""
    pl = seq["plans"][i]
    planches = [im[0] for _n, im in references_du_plan(seq, pl) if "planche_" in os.path.basename(im[0])]
    refs = (planches + [x for x in images_du_plan(seq, pl) if x not in planches])[:4]
    texte = consigne(seq, pl, params) + ((" Precisely, at the start: " + _anglais(precision, True)) if precision else "")
    sortie = os.path.join(dossier(seq), f"plan{i + 1:02d}_depart_{int(time.time() * 1000) % 10 ** 9}.png")
    if moteur_image == "gemini":
        from . import ia
        if not refs:
            png = ia.generer_image(params, "First frame of this video shot, photorealistic still image: " + texte)
        else:
            png = ia.generer_image_refs(params, "Compose the first frame of this video shot as one photorealistic still image. "
                                                "Use the reference images for the people's appearance and the place. " + texte, refs)
        with open(sortie, "wb") as f:
            f.write(png)
        return sortie
    from . import creatif
    L, H = (512, 912) if seq.get("format") == "9:16" else (912, 512)
    init = next((r for r in refs if r in sum(((x.get("images") or []) for x in seq["lieux"]), [])), None)
    creatif.image(texte, sortie, params, largeur=L, hauteur=H, init=init, force=0.6)
    return sortie


# ------------------------------------------------------------------ 0.9.72 : personnage fidèle d'un plan à l'autre
CONSIGNE_PLANCHE = ("If the reference photo shows several people, draw ONLY the one person matching the description below, never "
                    "the others. Character model sheet of EXACTLY that same person as in the reference images: same face, same hairstyle, same "
                    "body, same outfit. Four views side by side on a plain light grey background: front view, three-quarter view, "
                    "side profile, full body standing. Even soft studio light, photorealistic, sharp, no text, no labels. {d}")


def planche_lieu(seq, li, params):
    """Planche d'un lieu (0.9.88) : quatre vues du même endroit, même lumière (large, côté, vers l'entrée, détail), d'après ses
    photos (réel, ou inspiré) ou sa description (inventé). Elle sert de décor aux images clefs."""
    from . import ia
    mode = li.get("mode") or ("reel" if li.get("images") else "invente")
    refs = [i for i in li.get("images") or [] if os.path.exists(i)] if mode != "invente" else []
    d = li.get("en") or _anglais((li.get("description") or "").strip(), True)
    if not refs and not d:
        raise ValueError(_("Ajoutez d'abord une photo ou une description du lieu « {n} ».", n=li.get("nom") or "?"))
    base = ("Location reference sheet: the SAME place shown in four views in a 2x2 grid: wide establishing view, view from "
            "the side, view toward the entrance or exit, close detail of materials. Same light and time of day in all four, "
            "photorealistic, no people, no text, no labels. ")
    if refs and mode == "reel":
        png = ia.generer_image_refs(params, base + "Exactly the place of the reference photos: same layout, furniture, materials, "
                                    "colours and light. " + d, refs[:4])
    elif refs:
        png = ia.generer_image_refs(params, base + "A place INSPIRED by the reference photos (same mood and style, new place) : " + d,
                                    refs[:4])
    else:
        png = ia.generer_image(params, base + "An invented place: " + d)
    sortie = os.path.join(dossier(seq), "lieu_" + re.sub(r"[^\w-]+", "_", li.get("nom") or "lieu")[:30] + ".png")
    with open(sortie, "wb") as f:
        f.write(png)
    li["planche"] = sortie
    return sortie


def planche_personnage(seq, p, params):
    """Fiche du personnage (0.9.72) : une planche face, trois quarts, profil, en pied, d'après ses images (Gemini). Une image
    se contrôle bien mieux qu'une vidéo : c'est elle que le moteur « Référence » garde ensuite à l'identique."""
    from . import ia
    mode = p.get("mode") or ("reel" if p.get("images") else "invente")
    refs = [i for i in p.get("images") or [] if os.path.exists(i)] if mode != "invente" else []
    d = p.get("en") or _anglais((p.get("description") or "").strip(), True)      # 0.9.89 : mots anglais du catalogue
    if not refs and not d:
        raise ValueError(_("Ajoutez d'abord une image ou une description du personnage « {n} ».", n=p.get("nom") or "?"))
    allure = jeu_du_style(p.get("style", ""), params)       # « à la manière de » : une allure, jamais un visage
    if allure and not refs:
        d = "; ".join(x for x in (d, allure) if x)
    tenue = p.get("tenue") or {}                            # 0.9.88 : la tenue choisie remplace celle des photos
    t_en = tenue.get("en") or _anglais(tenue.get("description", ""), True)
    t_img = tenue.get("image") if tenue.get("image") and os.path.exists(tenue.get("image")) else ""
    if t_en:
        d = "; ".join(x for x in (d, "OUTFIT to wear (replaces the clothes of the photos): " + t_en +
                                  (", exactly as in the last reference image" if t_img else "")) if x)
    if t_img:
        refs = refs[:3] + [t_img]
    if mode == "inspire" and refs and p.get("genre") != "objet":
        d = ("A person who LOOKS LIKE the person in the reference photos (same face and features, recognisable), adapted as "
             "described: " + d) if d else "A person who looks like the person in the reference photos"
    if p.get("genre") == "objet":                            # 0.9.79 : un objet qui revient (véhicule…) a aussi sa fiche
        consigne_objet = ("Reference sheet of ONE object: " + d + ". Four views side by side on a plain light grey background: "
                          "front, three-quarter, side, rear. Even soft studio light, photorealistic, sharp, no text, no logo, no "
                          "brand, no people.")
        png = ia.generer_image_refs(params, "Only the object described, as seen in the reference image. " + consigne_objet, refs) \
            if refs else ia.generer_image(params, consigne_objet)
    elif refs:
        png = ia.generer_image_refs(params, CONSIGNE_PLANCHE.format(d=("Description: " + d) if d else ""), refs)
    else:                                   # 0.9.77 : personnage inventé (le chauffeur) : sa fiche le fixe pour tous les plans
        png = ia.generer_image(params, "Character model sheet of an INVENTED person (not a real or famous person): " + d +
                               ". Four views side by side on a plain light grey background: front view, three-quarter view, side "
                               "profile, full body standing. Even soft studio light, photorealistic, sharp, no text, no labels.")
    sortie = os.path.join(dossier(seq), "planche_" + re.sub(r"[^\w-]+", "_", p.get("nom") or "perso")[:30] + ".png")
    with open(sortie, "wb") as f:
        f.write(png)
    p["planche"] = sortie
    p["planche_tenue"] = tenue.get("id", "")           # 0.9.88 : une autre tenue demandera une nouvelle fiche
    return sortie


_GROUPE = re.compile(r"(?i)\b(?:les deux|les trois|deux|trois|couple|groupe|elles|ils|both|two|three|group|everyone)\b")


def groupes_suspects(seq):
    """Personnages qui semblent être plusieurs personnes (« Les deux ») : un élément du moteur = une seule personne,
    sinon les visages se mélangent."""
    return [p["nom"] for p in seq["personnages"] if _GROUPE.search(p.get("nom") or "")]


def sans_planche(seq, indices):
    """Personnages présents dans ces plans, avec des images, mais sans planche encore."""
    noms = {n.lower() for i in indices for n in (seq["plans"][i].get("personnages") or [x["nom"] for x in seq["personnages"]])}
    return [p for p in seq["personnages"] if p["nom"].lower() in noms and not (p.get("planche") and os.path.exists(p["planche"])
                                                                             and _tenue_de_la_fiche(p))
            and ([x for x in p.get("images") or [] if os.path.exists(x)] or (p.get("description") or "").strip())]


def _tenue_de_la_fiche(p):
    """La fiche a-t-elle été faite avec la tenue demandée maintenant ? (une fiche sans tenue choisie reste bonne)"""
    voulue = (p.get("tenue") or {}).get("id", "")
    return not voulue or voulue == p.get("planche_tenue", "")


def planches_manquantes(seq, pl, params, moteur_video):
    """Avant un plan au moteur « Référence » : la planche des personnages qui n'en ont pas encore (si demandé, clef Gemini)."""
    if moteur_video in ("locale", "flow") or not (seq.get("image_fin_auto", True) and params.get("clef_gemini")):
        return
    from . import generateurs_video as GV
    if not (GV.modele(moteur_video, params) or {}).get("references"):
        return
    k = seq["plans"].index(pl)
    for p in sans_planche(seq, [k]):
        planche_personnage(seq, p, params)


def _photo_de_groupe(seq, chemin):
    """L'image est-elle partagée par plusieurs personnages (photo de groupe d'où sortent les découpes) ?"""
    return sum(1 for p in seq["personnages"] if chemin in (p.get("images") or [])) > 1


def references_du_plan(seq, pl):
    """[(« Character A », [planche, images…])] des personnages du plan, pour les moteurs « Référence »."""
    out = []
    noms = [n.lower() for n in visibles(seq, pl)]
    for k, p in enumerate(seq["personnages"]):
        if p["nom"].lower() not in noms:              # 0.9.86 : seulement ceux qu'on voit (continuité)
            continue
        autres = [i for i in p.get("images") or [] if os.path.exists(i)]
        if p.get("decoupe") and os.path.exists(p["decoupe"]):     # 0.9.86 : la découpe, pas la photo de groupe (visages mêlés)
            autres = [p["decoupe"]] + [i for i in autres if i != p["decoupe"] and i != p.get("image_source")
                                       and not _photo_de_groupe(seq, i)]
        imgs = ([p["planche"]] if p.get("planche") and os.path.exists(p["planche"]) else []) + autres
        if imgs:
            out.append((f"Character {chr(65 + k)}", imgs[:4]))
    return out


def derniere_image(video, sortie):
    """La dernière image exacte d'une vidéo : le plan suivant démarre dessus (raccord parfait)."""
    from . import moteur
    moteur.lancer(["-y", "-sseof", "-1", "-i", video, "-update", "1", "-q:v", "2", sortie])     # chaque image écrase la précédente : reste la dernière
    if not os.path.exists(sortie):
        moteur.lancer(["-y", "-i", video, "-update", "1", "-q:v", "2", sortie])
    return sortie if os.path.exists(sortie) else ""


def depart_enchaine(seq, i):
    """Image de départ du plan i prise à la fin du plan i-1 déjà fabriqué, si l'enchaînement est demandé (par défaut)."""
    if i <= 0 or not seq["plans"][i].get("enchainer", True):
        return ""
    av = seq["plans"][i - 1]
    if av.get("image_fin") and os.path.exists(av["image_fin"]) and not av.get("sans_fin") and seq.get("ancrer_visages", True):
        return av["image_fin"]            # 0.9.77 : image propre, visages d'après la fiche ; la vidéo y est arrivée
    f = av.get("fichier")
    if not (f and os.path.exists(f)):
        return ""
    return derniere_image(f, os.path.join(dossier(seq), f"plan{i + 1:02d}_depart_enchaine.png"))


def image_connue_avant(seq, i):
    """La dernière image réelle ou validée avant la fin du plan i : son départ, sinon l'image clef précédente, sinon la
    première image du plan 1 (0.9.87 : base d'une image clef quand le plan part de la vidéo d'avant, pas encore faite)."""
    for k in range(i, -1, -1):
        pl = seq["plans"][k]
        if k < i and pl.get("image_fin") and os.path.exists(pl["image_fin"]) and not pl.get("sans_fin"):
            return pl["image_fin"]
        if pl.get("image") and os.path.exists(pl["image"]):
            return pl["image"]
    return ""


def image_arrivee(seq, i, params, depart=None, precision=""):
    """Image d'arrivée du plan i (0.9.72) : la pose quand l'action est finie, composée d'après l'image de départ et les
    références. Le moteur doit la rejoindre : il ne peut plus faire traverser la table ni changer de visage en route."""
    from . import ia
    pl = seq["plans"][i]
    fiches = [x for _n, im in references_du_plan(seq, pl) for x in im[:1]]
    if not (depart and os.path.exists(depart)):
        depart = image_connue_avant(seq, i)          # 0.9.87 : image clef : la dernière image réelle connue sert de décor
    lieux = [x for x in images_du_plan(seq, pl) if x not in fiches and x != depart]
    fin = (seq.get("raccord") or {}).get("image_fin")
    refs = fiches[:3] + ([depart] if depart and os.path.exists(depart) else []) + lieux[:1]
    if fin and os.path.exists(fin) and fin not in refs and i < len(seq["plans"]) - 1:
        refs.append(fin)                             # relier deux rushes : tenues et lumière de l'image d'après
    action = consigne(seq, pl, params)
    png = (ia.generer_image_refs if refs else lambda prm, c, r=None: ia.generer_image(prm, c))(
        params, "KEY IMAGE of a video sequence: the exact state of the scene at the END of this shot, action completely finished "
                "(final pose, physically plausible). The first reference images are the character and object sheets: every face, "
                "hairstyle, outfit and object must match them exactly. The next reference images are REAL photos of the place: keep "
                "their decor, materials, light and lens exactly; the camera framing follows the Camera line (it may move, widen or "
                "come closer). People are where the story says at that moment: whoever got into a vehicle, left or is listed as not "
                "visible must NOT appear. One photorealistic still image, no text. " + action +
        ((" Precisely, at the end: " + _anglais(precision, True)) if precision else ""), refs[:5])
    sortie = os.path.join(dossier(seq), f"plan{i + 1:02d}_arrivee_{int(time.time() * 1000) % 10 ** 9}.png")
    with open(sortie, "wb") as f:
        f.write(png)
    pl["image_fin"] = sortie
    return sortie


def image_arrivee_locale(seq, i, params, depart=None, precision=""):
    """0.9.86 : arrivée faite sur ce poste (gratuite) : l'image de départ retravaillée d'après l'action ; les visages sont
    moins fidèles qu'avec Gemini."""
    from . import creatif
    pl = seq["plans"][i]
    texte = "Last frame of this shot, action finished. " + consigne(seq, pl, params) + \
        ((" Precisely, at the end: " + _anglais(precision, True)) if precision else "")
    L, H = (512, 912) if seq.get("format") == "9:16" else (912, 512)
    sortie = os.path.join(dossier(seq), f"plan{i + 1:02d}_arrivee_{int(time.time() * 1000) % 10 ** 9}.png")
    creatif.image(texte, sortie, params, largeur=L, hauteur=H, init=depart if depart and os.path.exists(depart) else None,
                  force=0.6)
    pl["image_fin"] = sortie
    return sortie


# ------------------------------------------------------------------ 0.9.73 : images vues et validées avant la vidéo
def depart_prevu(seq, i):
    """L'image par laquelle le plan i commencera : la sienne, sinon (enchaîné) l'arrivée du plan précédent, ou la vraie
    dernière image de sa vidéo si elle est faite."""
    pl = seq["plans"][i]
    if pl.get("image") and os.path.exists(pl["image"]):
        return pl["image"]
    if i > 0 and pl.get("enchainer", True):
        av = seq["plans"][i - 1]
        if av.get("image_fin") and os.path.exists(av["image_fin"]) and not av.get("sans_fin") and seq.get("ancrer_visages", True):
            return av["image_fin"]
        if av.get("fichier") and os.path.exists(av["fichier"]):
            return depart_enchaine(seq, i)
    return ""


def preparer_images(seq, i, params, quoi=("depart", "arrivee"), precision="", force=False):
    """Compose (Gemini) l'image de départ et/ou d'arrivée du plan i ; une image refaite n'est plus validée."""
    pl = seq["plans"][i]
    par = seq.get("images_par") or "gemini"
    if par == "gemini" and seq.get("image_fin_auto", True) and params.get("clef_gemini"):
        for p in sans_planche(seq, [i]):                  # la fiche du personnage d'abord : les deux images s'en servent
            planche_personnage(seq, p, params)
    if "depart" in quoi and (force or precision or not (i > 0 and pl.get("enchainer", True) and depart_prevu(seq, i))):
        pl["image"] = image_depart(seq, i, params, "gemini" if par == "gemini" else "locale",
                                   precision if quoi == ("depart",) else "")
    if "arrivee" in quoi:
        if par == "gemini":
            image_arrivee(seq, i, params, depart_prevu(seq, i) or None, precision if quoi == ("arrivee",) else "")
        else:
            image_arrivee_locale(seq, i, params, depart_prevu(seq, i) or None, precision if quoi == ("arrivee",) else "")
    pl["images_ok"] = False
    return pl


def images_a_verifier(seq, indices, params, moteur_video):
    """Plans dont les images doivent être vues avant la vidéo (moteur Référence avec image d'arrivée demandée)."""
    from . import generateurs_video as GV
    if moteur_video in ("locale", "flow") or not (GV.modele(moteur_video, params) or {}).get("references"):
        return []
    if not (seq.get("image_fin_auto", True) and params.get("clef_gemini")):
        return []
    return [i for i in indices if not seq["plans"][i].get("images_ok") and not seq["plans"][i].get("fichier")]


def fabriquer_plan(seq, i, params, moteur_video, progression=None, arret=lambda: False):
    """Plan i en vidéo. moteur_video : "locale" (IA de ce poste) ou l'identifiant d'un générateur cloud (votre clef).
    Flow se fait à la main (voir le dialogue). Renvoie le chemin du MP4."""
    pl = seq["plans"][i]
    texte = pl.get("consigne") or consigne(seq, pl, params)
    sortie = os.path.join(dossier(seq), f"plan{i + 1:02d}_{int(time.time())}.mp4")
    image = pl.get("image") if pl.get("image") and os.path.exists(pl["image"]) else None
    ref = False
    if moteur_video not in ("locale", "flow"):
        from . import generateurs_video as GV
        ref = bool((GV.modele(moteur_video, params) or {}).get("references"))
    if image is None and ref:
        image = depart_enchaine(seq, i) or None              # 0.9.72 : le plan démarre sur la dernière image du précédent
    if image is None and seq.get("image_auto", True) and moteur_video not in ("locale", "flow") and params.get("clef_gemini") \
            and images_du_plan(seq, pl):
        # 0.9.70 : sans image de départ, le moteur réinvente le personnage ; on compose d'abord l'image avec ses références
        progression and progression(0.02)
        image = image_depart(seq, i, params, "gemini")
        pl["image"] = image
    if moteur_video == "locale":
        from . import creatif
        L, H = (272, 480) if seq.get("format") == "9:16" else (480, 272)
        creatif.video(texte, sortie, params, init=image, secondes=min(5.0, float(pl.get("duree") or 5)), largeur=L, hauteur=H,
                      progression=progression, arret=arret)
    elif ref:
        fin = pl.get("image_fin") if pl.get("image_fin") and os.path.exists(pl["image_fin"]) else None
        if fin is None and seq.get("image_fin_auto", True) and params.get("clef_gemini") and not pl.get("sans_fin"):
            progression and progression(0.04)
            fin = image_arrivee(seq, i, params, image)
        GV.generer(params, moteur_video, texte, sortie, int(pl.get("duree") or DUREE_PLAN), seq.get("format", "16:9"), image,
                   progression, arret, son=seq.get("voix") == "moteur", references=references_du_plan(seq, pl), image_fin=fin)
    else:
        GV.generer(params, moteur_video, texte, sortie, int(pl.get("duree") or DUREE_PLAN), seq.get("format", "16:9"), image,
                   progression, arret, son=seq.get("voix") == "moteur")
    return sortie


def voix_du_plan(seq, i, params, moteur_voix="local"):
    """Répliques du plan i dites avec la manière de parler de chaque personnage : [(décalage s, wav)]."""
    from . import diction as D, moteur
    pl = seq["plans"][i]
    out, t = [], 0.4
    for k, r in enumerate(pl.get("repliques") or []):
        p = next((x for x in seq["personnages"] if x["nom"].lower() == (r.get("qui") or "").lower()), {})
        wav = os.path.join(dossier(seq), f"plan{i + 1:02d}_replique{k + 1}.wav")
        D.dire(r["texte"], wav, params, maniere_de_parler(p, params) if p else "naturel", moteur_voix, voix=p.get("voix") or None)
        out.append((round(t, 2), wav))
        t += float((moteur.sonder(wav) or {}).get("duree") or 2.0) + 0.35
    return out


def prix_total(seq, moteur_video, params):
    if moteur_video in ("locale", "flow"):
        return 0.0
    from . import generateurs_video as GV
    m = GV.modele(moteur_video, params)
    if not m:
        return 0.0
    son = seq.get("voix") == "moteur"
    from .recettes_ia import PRIX_GEMINI
    auto = seq.get("image_auto", True) and params.get("clef_gemini")
    fin = bool(m.get("references")) and seq.get("image_fin_auto", True) and params.get("clef_gemini")
    return round(sum(GV.prix(m, int(p.get("duree") or DUREE_PLAN), son) +
                     (PRIX_GEMINI["image"] if auto and not p.get("image") and images_du_plan(seq, p) else 0.0) +
                     (PRIX_GEMINI["image"] if fin and not p.get("image_fin") else 0.0)
                     for p in seq["plans"] if not p.get("fichier")), 2)


def monter(projet, seq, t):
    """Pose les plans fabriqués l'un après l'autre à l'instant t (la suite du film est décalée) et les répliques sur la
    piste Voix au bon moment. Renvoie (nombre de plans posés, durée totale)."""
    from . import moteur, prolonger
    from .projet import fin_clip
    debut, n = t, 0
    for pl in seq["plans"]:
        f = pl.get("fichier")
        if not (f and os.path.exists(f)):
            continue
        ci = prolonger.poser(projet, {"debut": t, "piste": "video"}, f, "debut", (pl.get("action") or "")[:40])
        if not ci:
            continue
        if seq.get("voix") != "moteur":
            ci["muet"] = True                        # 0.9.68 : seul « voix du moteur » garde le son fabriqué avec la vidéo
        for decal, wav in pl.get("voix") or []:
            if os.path.exists(wav):
                m = projet.ajouter_media(wav, moteur.sonder(wav))
                m["nom"] = _("Réplique")
                projet.ajouter_clip(m["id"], "voix", ci["debut"] + float(decal))
        t = fin_clip(ci)
        n += 1
    return n, t - debut
