"""Paroles de chanson écrites par l'IA (0.9.18), pour la musique IA (ACE-Step) : à partir du thème et, s'il y en a, du
début des paroles que l'utilisateur a tapé (l'IA le garde et continue). Structure lisible par le moteur de musique :
[verse], [chorus], [bridge], [outro]. IA locale (rien n'est envoyé) ou IA cloud (votre clef), au choix.
"""
from .langue import _

VOIX = {"auto": (_("Voix au choix du moteur"), ""), "femme": (_("Voix de femme"), "female vocals"),
        "homme": (_("Voix d'homme"), "male vocals"), "duo": (_("Duo homme et femme"), "male and female duet vocals"),
        "choeur": (_("Chœur"), "choir vocals"), "enfant": (_("Voix d'enfant"), "child vocals"),
        "rap": (_("Rap"), "rap vocals")}
LANGUES = {"fr": "Français", "en": "English", "es": "Español", "de": "Deutsch", "it": "Italiano"}

CONSIGNES = """Tu es parolier. Écris les paroles d'une chanson courte, chantable, avec des rimes simples.
Langue : {langue}. Thème et ambiance : {theme}. Voix : {voix}. Durée du morceau : environ {duree} secondes, donc {plan}.
Utilise exactement ces balises, chacune seule sur sa ligne : [verse], [chorus], [bridge], [outro].
Des vers courts (6 à 10 syllabes). Rien d'autre que les paroles : pas de titre, pas d'explication, pas de guillemets.
{debut}"""


def plan_pour(duree):
    d = float(duree or 60)
    if d <= 30:
        return "un couplet [verse] de 4 vers puis un refrain [chorus] de 4 vers"
    if d <= 75:
        return "[verse] 4 vers, [chorus] 4 vers, [verse] 4 vers, [chorus] 4 vers"
    return "[verse] 4 vers, [chorus] 4 vers, [verse] 4 vers, [chorus] 4 vers, [bridge] 2 à 4 vers, [chorus] 4 vers, [outro] 2 vers"


def demande(theme, debut="", langue="fr", voix="auto", duree=60):
    deb = (f"Commence EXACTEMENT par ces vers de l'utilisateur, sans les changer, puis continue dans le même esprit :\n{debut.strip()}"
           if debut.strip() else "")
    return CONSIGNES.format(langue=LANGUES.get(langue, langue), theme=theme.strip() or "libre", voix=VOIX.get(voix, VOIX["auto"])[1] or "au choix",
                            duree=int(duree), plan=plan_pour(duree), debut=deb)


def nettoyer(texte, debut=""):
    """Garde les balises et les vers ; remet le début de l'utilisateur s'il a été perdu."""
    lignes = []
    for l in str(texte or "").replace("\r", "").split("\n"):
        l = l.strip().strip('"«»').strip()
        if not l or l.startswith(("```", "Voici", "Here")):
            continue
        bas = l.lower().strip("[]() :")
        for b in ("verse", "chorus", "bridge", "outro", "intro", "couplet", "refrain", "pont"):
            if bas.startswith(b) and len(bas) < 14:
                l = "[" + {"couplet": "verse", "refrain": "chorus", "pont": "bridge"}.get(b, b) + "]"
                break
        lignes.append(l)
    out = "\n".join(lignes).strip()
    if debut.strip() and debut.strip().split("\n")[0][:20].lower() not in out.lower():
        out = debut.strip() + "\n" + out
    if not out.startswith("["):
        out = "[verse]\n" + out
    return out


def ecrire(theme, debut="", langue="fr", voix="auto", duree=60, params=None, niveau="locale"):
    """Paroles (texte) ; niveau « locale » (modèle de ce poste) ou « cloud » (Claude / Gemini, votre clef)."""
    texte = demande(theme, debut, langue, voix, duree)
    if niveau == "locale":
        from . import ia_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise RuntimeError(_("Aucun modèle d'IA locale pour écrire : installez « Vision et texte » dans Préférences › IA locale, "
                                 "ou choisissez l'IA cloud."))
        r = ia_locale.generer(modele, texte, [], systeme="Tu écris des paroles de chansons.", params=params)
    else:
        from . import ia
        r = ia.demander(params or {}, "Tu écris des paroles de chansons.", texte, max_jetons=1200)
    return nettoyer(r if isinstance(r, str) else str(r), debut)
