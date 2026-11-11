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


def decouper_simple(histoire):
    """Sans IA : une phrase (ou un « puis ») = un plan."""
    morceaux = [m.strip(" ,") for m in re.split(_SEPARATEURS, histoire or "", flags=re.I)]
    return [plan(m[0].upper() + m[1:]) for m in morceaux if len(m) > 3][:12]


CONSIGNE_DECOUPER = """Tu es scénariste et réalisateur. Découpe cette petite histoire en plans de cinéma courts (4 à 8 secondes chacun,
12 au plus), en français. Réponds en JSON strict, sans texte autour :
{{"personnages": [{{"nom": "prénom court inventé", "description": "apparence physique et vêtements, précis et constants (âge, carrure,
cheveux, tenue)", "style": "nom de la personne ou du personnage dont il a le style, si l'histoire en cite un, sinon vide"}}],
"lieux": [{{"nom": "nom court", "description": "description visuelle précise (lumière, saison, détails)"}}],
"plans": [{{"action": "ce qu'on voit, une phrase", "personnages": ["noms présents"], "lieu": "nom du lieu", "duree": 6,
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
    bouts = [x for x in (desc, jeu) if x]
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
    if pl.get("camera"):
        morceaux.append("Camera: " + _anglais(pl["camera"], traduire).rstrip(".") + ".")
    if pl.get("repliques"):
        morceaux.append("The characters talk briefly (lips moving), no subtitles.")
    morceaux.append("Same characters, same clothes and same light as the other shots of this sequence. Realistic, high detail, "
                    "natural motion, no text, no watermark, no logo, no famous person.")
    return " ".join(morceaux)


CONSIGNE_AMELIORER = """You improve a prompt for an AI video generator. Keep EXACTLY, word for word, every "Character X: ..." description
and the "Setting:" sentence (continuity between shots). Make the action, camera movement, lighting, lens and atmosphere more
precise and cinematic, in English, under 110 words. Never add a real person's name, a known character or a logo. Answer with the
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


def images_du_plan(seq, pl):
    """Images de référence utiles au plan : celles des personnages présents, puis celles du lieu (au plus 4)."""
    out = []
    for n in pl.get("personnages") or []:
        p = next((x for x in seq["personnages"] if x["nom"].lower() == n.lower()), None)
        out += [i for i in (p or {}).get("images") or [] if os.path.exists(i)]
    li = next((x for x in seq["lieux"] if x["nom"].lower() == (pl.get("lieu") or "").lower()), None)
    out += [i for i in (li or {}).get("images") or [] if os.path.exists(i)]
    return out[:4]


def image_depart(seq, i, params, moteur_image="gemini"):
    """Image de départ du plan i, composée à partir des images de référence (Gemini : personnages et lieu réunis ;
    IA de ce poste : image du lieu retravaillée). Renvoie le chemin, ou "" s'il n'y a rien pour la composer."""
    pl = seq["plans"][i]
    refs = images_du_plan(seq, pl)
    sortie = os.path.join(dossier(seq), f"plan{i + 1:02d}_depart.png")
    texte = consigne(seq, pl, params)
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


def fabriquer_plan(seq, i, params, moteur_video, progression=None, arret=lambda: False):
    """Plan i en vidéo. moteur_video : "locale" (IA de ce poste) ou l'identifiant d'un générateur cloud (votre clef).
    Flow se fait à la main (voir le dialogue). Renvoie le chemin du MP4."""
    pl = seq["plans"][i]
    texte = pl.get("consigne") or consigne(seq, pl, params)
    sortie = os.path.join(dossier(seq), f"plan{i + 1:02d}_{int(time.time())}.mp4")
    image = pl.get("image") if pl.get("image") and os.path.exists(pl["image"]) else None
    if moteur_video == "locale":
        from . import creatif
        L, H = (272, 480) if seq.get("format") == "9:16" else (480, 272)
        creatif.video(texte, sortie, params, init=image, secondes=min(5.0, float(pl.get("duree") or 5)), largeur=L, hauteur=H,
                      progression=progression, arret=arret)
    else:
        from . import generateurs_video as GV
        GV.generer(params, moteur_video, texte, sortie, int(pl.get("duree") or DUREE_PLAN), seq.get("format", "16:9"), image,
                   progression, arret)
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
    return round(sum(GV.prix(m, int(p.get("duree") or DUREE_PLAN)) for p in seq["plans"] if not p.get("fichier")), 2)


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
        for decal, wav in pl.get("voix") or []:
            if os.path.exists(wav):
                m = projet.ajouter_media(wav, moteur.sonder(wav))
                m["nom"] = _("Réplique")
                projet.ajouter_clip(m["id"], "voix", ci["debut"] + float(decal))
        t = fin_clip(ci)
        n += 1
    return n, t - debut
