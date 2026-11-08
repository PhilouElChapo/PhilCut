"""Phrasé « à la manière de » (0.9.21) : la réplique d'un clip IA est dite par un moteur de voix séparé, avec la manière
de parler d'un style (débit, pauses, hauteur, grain, énergie), puis mêlée à la vidéo. Deux moteurs :
  - local (Piper, sur ce poste, gratuit) : débit, pauses entre les phrases, expressivité, puis hauteur, grain et
    présence par des filtres audio ;
  - cloud (Gemini, votre clef, payant, prix affiché) : la consigne de jeu est donnée en clair au moteur de voix
    (« laconic slow drawl, long pauses… »), qui sait vraiment jouer la phrase.
Comme pour l'image, c'est une manière de dire, jamais la voix d'une personne : aucun clonage, aucun extrait.
L'IA peut aussi récrire la réplique « à sa manière » (tournures, gouaille, laconisme) sans citer de réplique célèbre.
"""
import os
import re
import unicodedata

from .langue import _

# débit (1 = normal), silence entre phrases (s), expressivité (0-1), hauteur (demi-tons), grain (0-1), voix Gemini, consigne Gemini
STYLES = {
    "naturel": (_("Naturel"), dict(vitesse=1.0, silence=0.3, expr=0.5, hauteur=0, grain=0.0, gemini="Kore",
                                   consigne="")),
    "trainant": (_("Lent et traînant, laconique (cow-boy)"), dict(vitesse=0.8, silence=0.9, expr=0.35, hauteur=-2, grain=0.3, gemini="Charon",
                 consigne="Speak as a laconic cowboy: slow, low drawl, long pauses between short sentences, calm authority")),
    "froid": (_("Froid, impassible, peu de mots"), dict(vitesse=0.9, silence=0.8, expr=0.15, hauteur=-1, grain=0.1, gemini="Orus",
              consigne="Speak coldly and impassively, flat even tone, very few words, icy silences, never raise the voice")),
    "gouailleur": (_("Gouailleur, rapide, charmeur"), dict(vitesse=1.15, silence=0.2, expr=0.9, hauteur=0, grain=0.2, gemini="Puck",
                   consigne="Speak like a cheeky charming rogue from Paris: quick, playful, street-smart banter, a grin in the voice")),
    "bourru": (_("Bourru, grave, posé"), dict(vitesse=0.9, silence=0.6, expr=0.3, hauteur=-3, grain=0.5, gemini="Charon",
               consigne="Speak gruffly in a deep, heavy, unhurried working-class voice, few words, weight on each one")),
    "nerveux": (_("Nerveux, explosif, comique"), dict(vitesse=1.3, silence=0.1, expr=1.0, hauteur=2, grain=0.0, gemini="Puck",
                consigne="Speak frantically and irascibly, fast, explosive outbursts, comic exasperation, sudden shouts")),
    "naif": (_("Naïf, doux, bonhomme"), dict(vitesse=0.9, silence=0.5, expr=0.6, hauteur=1, grain=0.0, gemini="Puck",
             consigne="Speak gently and naively, good-natured, a little hesitant, kind and befuddled")),
    "detective": (_("Détective désabusé (film noir)"), dict(vitesse=0.95, silence=0.6, expr=0.3, hauteur=-2, grain=0.4, gemini="Charon",
                  consigne="Speak like a world-weary film noir detective narrating: low, tired, sardonic, measured")),
    "crooner": (_("Crooner suave"), dict(vitesse=0.9, silence=0.5, expr=0.5, hauteur=-2, grain=0.1, gemini="Charon",
                consigne="Speak like a suave crooner: smooth, warm, relaxed, confident, a smile in the voice")),
    "glamour": (_("Glamour, souffle léger"), dict(vitesse=0.9, silence=0.5, expr=0.6, hauteur=1, grain=0.0, gemini="Aoede",
                consigne="Speak breathily and playfully, soft glamorous voice, innocent charm")),
    "heros": (_("Héros d'action, phrases courtes"), dict(vitesse=0.95, silence=0.7, expr=0.2, hauteur=-3, grain=0.3, gemini="Orus",
              consigne="Speak like a stoic action hero: deep, short punchy lines, deadpan, menacing calm")),
    "theatral": (_("Théâtral, grandiloquent"), dict(vitesse=0.95, silence=0.6, expr=1.0, hauteur=0, grain=0.0, gemini="Orus",
                 consigne="Speak theatrically: grand, dramatic crescendos, impassioned, rolling delivery")),
    "chuchote": (_("Chuchoté, sensuel"), dict(vitesse=0.85, silence=0.6, expr=0.4, hauteur=-1, grain=0.2, gemini="Charon",
                 consigne="Speak in a low half-whisper, ironic and sensual, unhurried")),
    "conteur": (_("Conteur, chaleureux"), dict(vitesse=0.95, silence=0.5, expr=0.7, hauteur=-1, grain=0.0, gemini="Charon",
                consigne="Speak like a warm storyteller, engaging, with gentle emphasis and pauses")),
    "gentleman": (_("Gentleman britannique, ironie légère"), dict(vitesse=1.0, silence=0.4, expr=0.6, hauteur=-1, grain=0.0, gemini="Charon",
                  consigne="Speak like a suave British gentleman adventurer: polished, light, wry understatement, amused confidence")),
    "annonceur": (_("Bande-annonce de film"), dict(vitesse=0.85, silence=0.8, expr=0.4, hauteur=-4, grain=0.3, gemini="Charon",
                  consigne="Speak like an epic movie trailer narrator: very deep, slow, dramatic pauses")),
}

# référence (nom canonique de styles_ia) → manière de parler
PAR_REFERENCE = {
    "john wayne": "trainant", "clint eastwood": "heros", "alain delon": "froid", "belmondo": "gouailleur", "jean gabin": "bourru",
    "louis de funes": "nerveux", "bourvil": "naif", "lino ventura": "bourru", "humphrey bogart": "detective", "frank sinatra": "crooner",
    "sinatra": "crooner", "marilyn monroe": "glamour", "audrey hepburn": "glamour", "schwarzenegger": "heros", "bruce lee": "heros",
    "jacques brel": "theatral", "serge gainsbourg": "chuchote", "gainsbourg": "chuchote", "james dean": "chuchote",
    "johnny hallyday": "bourru", "elvis": "crooner", "james bond": "froid", "star wars": "annonceur", "tontons flingueurs": "gouailleur",
    "film noir": "detective", "sergio leone": "trainant", "indiana jones": "heros",
    "simon templar": "gentleman", "roger moore": "gentleman", "cary grant": "gentleman", "david niven": "gentleman",
}


def _net(t):
    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()


def style_depuis(prompt, famille="video", params=None):
    """La manière de parler qui va avec la phrase de l'Atelier (« joué comme Alain Delon » → froid) ; « naturel » sinon."""
    from . import styles_ia as S
    tr = S.transposer(prompt or "", famille, params)
    for nom, _d in tr["styles"]:
        k = PAR_REFERENCE.get(_net(nom))
        if k:
            return k, nom
    return "naturel", ""


def filtres(reg):
    """Filtres FFmpeg : hauteur (sans changer le débit), grain (saturation douce + médiums), présence."""
    f = []
    h = float(reg.get("hauteur", 0) or 0)
    if abs(h) >= 0.5:
        k = 2 ** (h / 12.0)
        f.append(f"asetrate=48000*{k:.4f},aresample=48000,atempo={1 / k:.4f}")
    g = float(reg.get("grain", 0) or 0)
    if g > 0.05:
        f.append(f"equalizer=f=180:t=q:w=1:g={2 + 4 * g:.1f},equalizer=f=3000:t=q:w=1.5:g={1.5 * g:.1f},"
                 f"asoftclip=type=tanh:threshold={1 - 0.4 * g:.2f}")
    f.append("highpass=f=70,acompressor=threshold=-18dB:ratio=3:attack=10:release=200,loudnorm=I=-16:TP=-1.5")
    return ",".join(f)


def dire(texte, sortie, params, style="naturel", moteur_voix="local", voix=None, dossier=None):
    """Dit la réplique avec la manière choisie ; écrit un WAV 48 kHz prêt à mêler. Renvoie le chemin."""
    from . import moteur, voix as V
    texte = (texte or "").strip()
    if not texte:
        raise V.ErreurVoix(_("Aucune réplique à dire."))
    reg = STYLES.get(style, STYLES["naturel"])[1]
    brut = os.path.join(dossier or os.path.dirname(sortie), "_replique_brute.wav")
    if moteur_voix == "gemini":
        consigne = reg.get("consigne")
        V.lire_gemini((consigne + ": " + texte) if consigne else texte, brut, params, voix or reg.get("gemini") or "Kore")
        f = "highpass=f=70,loudnorm=I=-16:TP=-1.5"          # Gemini joue déjà la phrase : on ne déforme pas sa voix
    else:
        from . import packs_ia
        try:
            packs_ia.synthese(texte, brut, cle=voix, params=params, vitesse=reg["vitesse"], silence=reg["silence"], expressivite=reg["expr"])
        except packs_ia.ErreurIA as e:
            raise V.ErreurVoix(str(e)) from e
        f = filtres(reg)
    moteur.lancer(["-y", "-i", brut, "-af", f"aresample=48000,{f}", "-ac", "1", "-ar", "48000", sortie])
    try:
        os.remove(brut)
    except OSError:
        pass
    return sortie


def prix(texte, moteur_voix):
    from . import voix as V
    return V.prix_gemini(texte + " " * 80) if moteur_voix == "gemini" else 0.0


def mixer(video, voix_wav, sortie, debut=0.3, volume_voix=1.0, volume_film=0.35):
    """La vidéo et la réplique dans un seul fichier : la voix commence à « debut » ; le son du clip (s'il en a) passe
    dessous ; si la réplique est plus longue que la vidéo, la dernière image est tenue jusqu'à la fin de la phrase."""
    from . import moteur
    fv = moteur.sonder(video) or {}
    dv = float(fv.get("duree") or 0)
    dw = float((moteur.sonder(voix_wav) or {}).get("duree") or 0)
    total = max(dv, debut + dw + 0.4)
    tenir = max(0.0, total - dv)
    vf = f"tpad=stop_mode=clone:stop_duration={tenir:.2f}" if tenir > 0.05 else "null"
    ms = int(debut * 1000)
    a_son = bool(fv.get("audio"))
    if a_son:
        fa = (f"[0:a]volume={volume_film},apad=whole_dur={total:.2f}[f];[1:a]adelay={ms}|{ms},volume={volume_voix}[v];"
              f"[f][v]amix=inputs=2:normalize=0:duration=longest[a]")
    else:
        fa = f"[1:a]adelay={ms}|{ms},volume={volume_voix},apad=whole_dur={total:.2f}[a]"
    moteur.lancer(["-y", "-i", video, "-i", voix_wav, "-filter_complex", f"[0:v]{vf}[vv];{fa}", "-map", "[vv]", "-map", "[a]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                   "-t", f"{total:.2f}", "-movflags", "+faststart", sortie])
    return sortie


CONSIGNE_REECRIRE = """Récris cette réplique de film en français, à la manière de parler suivante : {maniere}.
Garde le sens, la longueur à peu près ({n} mots). Invente : ne cite aucune réplique célèbre existante, aucun nom.
Réponds seulement par la réplique, sans guillemets.
Réplique : {texte}"""


def reecrire(texte, style, params=None, niveau="locale", reference=""):
    """L'IA récrit la réplique avec les tournures de cette manière de parler (sans citer de réplique célèbre)."""
    reg = STYLES.get(style, STYLES["naturel"])
    maniere = reg[1].get("consigne") or reg[0]
    if reference:
        from . import styles_ia as S
        jeu = S.transposer(f"comme {reference}", "video", params)["ajout"]
        maniere = f"{maniere}; {jeu}" if jeu else maniere
    demande = CONSIGNE_REECRIRE.format(maniere=maniere, n=len(texte.split()), texte=texte.strip())
    systeme = "Tu es dialoguiste de cinéma."
    if niveau == "locale":
        from . import ia_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise RuntimeError(_("Aucun modèle d'IA locale pour écrire : installez « Vision et texte » dans Préférences › IA locale, "
                                 "ou choisissez l'IA cloud."))
        r = ia_locale.generer(modele, demande, [], systeme=systeme, params=params)
    else:
        from . import ia
        r = ia.demander(params or {}, systeme, demande, max_jetons=300)
    r = (r if isinstance(r, str) else str(r)).strip()
    r = re.sub(r"^(réplique\s*:\s*)", "", r, flags=re.I).strip().strip("«»\"' ")
    return r.splitlines()[0].strip() if r else texte
