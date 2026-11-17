"""Intro et logo animé, de l'idée au résultat (0.9.82) : même méthode que l'assistant vidéo et musique (assistant_idee).

Une phrase (« une intro de 4 s pour ma chaîne aviation, style cinéma, avec mon logo et un whoosh ») → cartes pré-remplies :
Logo, Style, Fond, Son ; puis le texte (titre, sous-titre, améliorables) et la durée ; un aperçu animé ; la fabrication
(intros.fabriquer + le son mêlé) ; la pose au début, à la fin, à la ligne rouge ou dans les médias. Ce module ne dépend pas
de l'interface."""
import os
import re
import time

from .langue import _

CONSIGNE_INTRO = """Tu es motion designer. L'utilisateur décrit en quelques mots l'intro (ou le logo animé) qu'il veut pour sa
vidéo. Déduis ce qu'il faut et rends un objet JSON :
{{"titre": "le texte principal (nom de la chaîne, titre)", "sous_titre": "ou vide", "duree": secondes (2 à 8),
 "style": {{"modele": un identifiant parmi [{modeles}], "accent": "#rrggbb", "description": "l'allure voulue, en mots"}},
 "logo": {{"source": "atelier", "fichier_image", "creer_ia" ou "aucune", "description": "le logo voulu, ou vide"}},
 "fond": {{"source": "degrade", "uni", "film", "transparent", "fichier_image" ou "creer_ia", "couleur": "#rrggbb ou vide",
           "description": "le fond voulu, ou vide"}},
 "son": {{"source": "aucune", "bruitage", "jingle" ou "fichier", "bruitage": un identifiant parmi [{bruitages}] ou vide,
          "description": "le son voulu, en mots, ou vide"}},
 "placement": "debut" ou "fin", "remarques": "une phrase pour l'utilisateur, ou vide"}}
Règles : « mon logo » = source "atelier" (ses logos déjà faits) ; un logo à inventer = "creer_ia" ; « sur le film » ou
« par-dessus la vidéo » = fond "transparent" ; « les images du film » = "film" ; un petit son court (whoosh, impact, ding) =
"bruitage" ; une petite musique, un jingle, un logo sonore = "jingle" ; rien de dit sur le son = "aucune". Aucun nom de
marque ou de personne réelle dans les descriptions. Ecris en {langue}.
"""


def _langue():
    from . import assistant_idee as I
    return I._langue()


def _txt(v, n=200):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _couleur(v):
    v = _txt(v, 9)
    return v if re.fullmatch(r"#[0-9a-fA-F]{6}", v) else ""


def lire_intro(d):
    """Réponse de l'IA rendue sûre : cartes Logo, Style, Fond, Son et réglages bornés."""
    from . import assistant_idee as I
    from . import bruitages as BR
    from . import intros as IN
    d = d if isinstance(d, dict) else {}
    st, lg, fd, sn = (d.get(k) if isinstance(d.get(k), dict) else {} for k in ("style", "logo", "fond", "son"))
    modele = _txt(st.get("modele"), 20)
    style = I.element("style_intro", _("Style"), _txt(st.get("description")), "liste",
                      choix=modele if modele in IN.MODELES else "masque", accent=_couleur(st.get("accent")))
    logo = I.element("logo", _("Logo"), _txt(lg.get("description")), _txt(lg.get("source"), 15) or "aucune", chemin="")
    fond = I.element("fond", _("Fond"), _txt(fd.get("description")), _txt(fd.get("source"), 15) or "degrade",
                     couleur=_couleur(fd.get("couleur")), chemin="")
    br = _txt(sn.get("bruitage"), 20)
    son = I.element("son", _("Son"), _txt(sn.get("description")), _txt(sn.get("source"), 15) or "aucune",
                    choix=br if br in BR.SONS else "", chemin="")
    if son["source"] == "bruitage" and not son["choix"]:
        son["choix"] = "whoosh"
    try:
        duree = max(2.0, min(8.0, float(d.get("duree") or 3.0)))
    except (TypeError, ValueError):
        duree = 3.0
    return {"genre": "intro", "titre": _txt(d.get("titre"), 60), "sous_titre": _txt(d.get("sous_titre"), 80), "duree": duree,
            "placement": "fin" if _txt(d.get("placement"), 6) == "fin" else "debut",
            "elements": [logo, style, fond, son], "remarques": _txt(d.get("remarques"), 300)}


_STYLES_MOTS = (("cinema", r"cin[ée]ma|film|g[ée]n[ée]rique|[ée]pique"), ("lumiere", r"lumi[èe]re|chaleur|dor[ée]"),
                ("slam", r"punchy|dynamique|[ée]nergique|r[ée]seaux|tiktok|short"), ("glitch_net", r"glitch|tech|num[ée]rique"),
                ("verre", r"verre|moderne|[ée]l[ée]gant"), ("tiers_clean", r"bas de l'[ée]cran|nom et fonction|interview"))


def analyse_intro_simple(texte):
    """Sans IA : le titre entre guillemets (ou les premiers mots), un style d'après les mots, la durée dite."""
    t = texte or ""
    m = re.search(r"[«\"“]\s*([^»\"”]{1,60})\s*[»\"”]", t)
    titre = m.group(1).strip() if m else ""
    modele = next((k for k, motif in _STYLES_MOTS if re.search(motif, t, re.I)), "masque")
    son = "bruitage" if re.search(r"whoosh|impact|ding|bruitage", t, re.I) else ("jingle" if re.search(r"jingle|musique|logo sonore", t, re.I)
                                                                                  else "aucune")
    br = next((k for k in ("whoosh", "impact", "ding") if k in t.lower()), "whoosh")
    md = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:s|sec|secondes?)\b", t)
    d = {"titre": titre, "duree": float(md.group(1).replace(",", ".")) if md else 3.0,
         "style": {"modele": modele}, "logo": {"source": "atelier" if re.search(r"mon logo", t, re.I) else "aucune"},
         "fond": {"source": "transparent" if re.search(r"sur le film|par-dessus", t, re.I) else "degrade"},
         "son": {"source": son, "bruitage": br}, "placement": "fin" if re.search(r"\bfin\b|outro", t, re.I) else "debut"}
    return lire_intro(d)


def analyser_intro(params, texte, niveau="claude"):
    from . import assistant_creation as A
    from . import bruitages as BR
    from . import intros as IN
    r = A.demander(params, CONSIGNE_INTRO.format(modeles=", ".join(IN.MODELES), bruitages=", ".join(BR.SONS), langue=_langue()),
                   "Demande : " + texte.strip(), (), niveau, max_jetons=1200)
    return lire_intro(r)


# ------------------------------------------------------------------ ce qu'il faut pour fabriquer
def manque(e):
    """Ce qui manque à une carte de l'intro (les autres types passent par assistant_idee.manque)."""
    t, s = e.get("type"), e.get("source")
    if not s:
        return _("Choisissez d'où vient cet élément.")
    if s == "bibliotheque":
        return "" if e.get("chemin") or e.get("choix") else _("Choisissez dans votre bibliothèque.")
    if t == "style_intro":
        if s == "decrire" and not e.get("choix"):
            return _("Décrivez l'allure, puis « Choisir d'après la description ».")
        return "" if e.get("choix") else _("Choisissez un modèle.")
    if s in ("atelier", "fichier_image", "fichier") and not (e.get("chemin") and os.path.exists(e["chemin"])):
        return _("Choisissez le fichier.") if s != "atelier" else _("Choisissez un de vos logos.")
    if s == "creer_ia" and not (e.get("chemin") and os.path.exists(e["chemin"])):
        return _("Décrivez-le, puis « Le faire dessiner » (environ 0,04 $).")
    if s == "jingle" and not (e.get("chemin") and os.path.exists(e["chemin"])):
        return _("Décrivez le jingle, puis « Créer le jingle (sur ce poste) ».")
    if s == "bruitage" and not e.get("choix"):
        return _("Choisissez le bruitage.")
    return ""


def fond_pour_intros(fond):
    """(fond d'intros.py, image) : une image (à moi, dessinée, de la bibliothèque) passe en fond « film »."""
    s = fond.get("source")
    if s in ("fichier_image", "creer_ia", "bibliotheque") and fond.get("chemin"):
        return "film", fond["chemin"]
    return (s if s in ("degrade", "uni", "film", "transparent") else "degrade"), None


def couleurs(etat):
    logo, style, fond, son = etat["elements"]
    c = {}
    if style.get("accent"):
        c["accent"] = style["accent"]
    if fond.get("source") == "uni" and fond.get("couleur"):
        c["fond"] = fond["couleur"]
    return c or None


def logo_chemin(etat):
    lg = etat["elements"][0]
    return lg["chemin"] if lg.get("source") != "aucune" and lg.get("chemin") and os.path.exists(lg["chemin"]) else None


def son_chemin(etat):
    from . import bruitages as BR
    sn = etat["elements"][3]
    s = sn.get("source")
    if s == "bruitage" and sn.get("choix") in BR.SONS:
        return BR.chemin(sn["choix"])
    if s in ("jingle", "fichier", "bibliotheque") and sn.get("chemin") and os.path.exists(sn["chemin"]):
        return sn["chemin"]
    return None


def contexte(etat, L=640, H=360, image_film=None):
    from . import intros as IN
    fond, image = fond_pour_intros(etat["elements"][2])
    return IN.contexte(etat["elements"][1].get("choix") or "masque", etat.get("titre") or _("Votre titre"), etat.get("sous_titre", ""),
                       L, H, float(etat["duree"]), fond, couleurs(etat), image or image_film, logo_chemin(etat))


def fabriquer(etat, dossier, L, H, cadence, image_film=None, progression=None):
    """Le clip de l'intro : l'animation (intros.py) puis, s'il y en a un, le son mêlé (bruitage au moment où le titre
    arrive, jingle ou morceau depuis le début), fondu à la fin. Renvoie le MP4."""
    from . import intros as IN
    from . import moteur
    os.makedirs(dossier, exist_ok=True)
    pile = time.strftime("%Y%m%d_%H%M%S")
    video = os.path.join(dossier, f"intro_{pile}_image.mp4")
    fond, image = fond_pour_intros(etat["elements"][2])
    duree = float(etat["duree"])
    IN.fabriquer(video, etat["elements"][1].get("choix") or "masque", etat.get("titre") or _("Votre titre"), etat.get("sous_titre", ""),
                 L, H, cadence, duree, fond=fond, couleurs=couleurs(etat), image_film=image or image_film, logo=logo_chemin(etat),
                 progression=(lambda f: progression(0.9 * f, _("animation"))) if progression else None)
    son = son_chemin(etat)
    sortie = os.path.join(dossier, f"intro_{pile}.mp4")
    if not son:
        os.replace(video, sortie)
        return sortie
    progression and progression(0.92, _("son"))
    retard = 250 if etat["elements"][3].get("source") == "bruitage" else 0
    filtre = (f"[1:a]adelay={retard}|{retard},apad,atrim=0:{duree:.3f},afade=t=out:st={max(0.0, duree - 0.6):.3f}:d=0.6,"
              f"aformat=sample_rates=48000:channel_layouts=stereo[a]")
    moteur.lancer(["-y", "-i", video, "-i", son, "-filter_complex", filtre, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                   "-c:a", "aac", "-b:a", "192k", "-shortest", sortie])
    try:
        os.remove(video)
    except OSError:
        pass
    return sortie


def creer_jingle(etat, sortie, params=None, progression=None, arret=lambda: False, traduire=None):
    """Un logo sonore court (sur ce poste) : la durée de l'intro, d'après la description de la carte Son."""
    from . import musique_ia as MI
    sn = etat["elements"][3]
    f = MI.fiche_vide()
    f["duree"] = max(3.0, float(etat["duree"]) + 0.5)
    f["instrumental"] = True
    f["utiliser_ia"] = False
    f["phrase"] = ", ".join(x for x in ((traduire(sn["description"]) if traduire and sn.get("description") else sn.get("description", "")),
                                        "short sound logo jingle, intro sting, ending on a clear final hit") if x)
    r, _c = MI.creer(f, sortie, params, progression, arret, traduire)
    return r


def image_ia(params, etat, quoi, sortie):
    """Logo ou fond dessiné par Gemini d'après la description de la carte (environ 0,04 $)."""
    from . import ia
    from . import logo as LG
    if quoi == "logo":
        e = etat["elements"][0]
        return LG.image_ia(params, (e.get("description") or "") + (" — " + etat["titre"] if etat.get("titre") else ""), sortie)
    e = etat["elements"][2]
    png = ia.generer_image(params, _("Image de fond pour une intro vidéo, format paysage 16:9 : {d}. Aucun texte, aucun logo, aucune "
                                     "personne reconnaissable ; laisser de la place au centre pour un titre.", d=e.get("description") or ""))
    with open(sortie, "wb") as f:
        f.write(png)
    return sortie
