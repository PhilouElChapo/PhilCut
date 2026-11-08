"""Styles « à la manière de » (0.9.20). On écrit dans l'Atelier IA « chanté à la manière de Sinatra, orchestre façon
Liza Minnelli » ou « un cow-boy à la John Wayne, look Star Wars » ; les moteurs ne connaissent pas les noms (et ne
doivent pas copier une personne ou une œuvre), alors PhilCut remplace chaque nom par la DESCRIPTION de son style :
pour la musique, le grain et la manière de chanter, l'orchestre, l'époque ; pour l'image et la vidéo, la lumière, la
pellicule, les décors, les costumes et le jeu d'acteur (attitude, démarche, manière de parler). Un style, une époque,
un genre ne sont à personne ; le visage, la voix exacte d'une personne et les personnages, logos et noms d'une œuvre,
si : la description n'en reprend aucun.

Les références connues sont ci-dessous (hors ligne, rien n'est envoyé). Un nom inconnu peut être transposé par l'IA,
locale ou cloud, sur votre clic ; la réponse est gardée dans « Mes styles » (Préférences › Assistant et IA), modifiable.
"""
import json
import re
import unicodedata

from .langue import _

# (noms reconnus, {voix, musique, image, jeu}) — descriptions en anglais, la langue des moteurs ; aucune ne décrit un visage.
_R = [
    # ---- chanteurs et chanteuses
    (["sinatra", "frank sinatra"], {
        "voix": "smooth baritone crooner vocals, relaxed behind-the-beat phrasing, warm legato, confident swing delivery",
        "musique": "1950s swing big band, lush strings, brass stabs, walking upright bass, brushed drums",
        "jeu": "suave 1950s crooner archetype, sharp tailored suit and fedora, relaxed confident swagger, wry charm"}),
    (["liza minnelli", "minnelli"], {
        "voix": "powerful theatrical belting female vocals, dramatic vibrato, Broadway showstopper energy",
        "musique": "Broadway cabaret show tune, brassy pit orchestra, vamping piano, big dramatic finale, 1970s showbiz",
        "jeu": "cabaret performer archetype, sequins, bowler hat, jazz hands, dazzling stage presence"}),
    (["edith piaf", "piaf*"], {
        "voix": "intense French chanson female vocals, rolling r's, fierce vibrato, heartbreaking emotion",
        "musique": "1940s Parisian chanson, accordion, waltz rhythm, small café orchestra",
        "jeu": "small fragile singer in a simple black dress, intense emotional gestures"}),
    (["jacques brel", "brel*"], {
        "voix": "impassioned French chanson male vocals, theatrical crescendos, intense spoken-sung delivery",
        "musique": "1960s French chanson, accordion, swelling orchestra, building waltz", "jeu": "sweating, intense, theatrical singer with expansive gestures"}),
    (["aznavour", "charles aznavour"], {
        "voix": "tender nasal French crooner male vocals, intimate and melancholic", "musique": "1960s French ballad, strings, piano, soft orchestra"}),
    (["gainsbourg", "serge gainsbourg"], {
        "voix": "low whispered half-spoken male vocals, ironic and sensual, cigarette-smoky",
        "musique": "late 1960s French pop, funky bass, orchestral strings, cool and sultry",
        "jeu": "nonchalant provocative dandy, unshaven, crumpled jacket, half-smile"}),
    (["johnny hallyday", "johnny*", "hallyday"], {
        "voix": "raspy powerful French rock male vocals, roaring stadium delivery",
        "musique": "French stadium rock, big electric guitars, harmonica, anthemic chorus",
        "jeu": "leather-clad rock idol, biker attitude, arms raised to the crowd"}),
    (["elvis", "elvis presley"], {
        "voix": "deep rockabilly male vocals, hiccuping, velvet baritone", "musique": "1950s rock and roll, slapback echo, twangy guitar, upright bass",
        "jeu": "1950s rock and roll idol archetype, quiff, swiveling hips, high-collared jumpsuit"}),
    (["louis armstrong", "armstrong*"], {
        "voix": "gravelly warm jazz male vocals, joyful scat", "musique": "New Orleans jazz, trumpet solos, clarinet, banjo, swing"}),
    (["ella fitzgerald", "ella*"], {"voix": "clear agile jazz female vocals, playful scat, perfect diction", "musique": "swing jazz, big band, piano trio"}),
    (["ray charles"], {"voix": "soulful raspy male vocals, gospel shouts", "musique": "1960s soul and R&B, electric piano, gospel backing singers"}),
    (["johnny cash", "cash*"], {"voix": "deep resonant country male baritone, plain storytelling", "musique": "boom-chicka-boom country, train beat, acoustic guitar",
                                "jeu": "man in black archetype, black clothes, guitar slung low, stern gaze"}),
    (["michael jackson"], {"voix": "high energetic pop male vocals, hiccups and yelps", "musique": "1980s funk pop, tight drum machine, slap bass, synth stabs",
                           "jeu": "sharp pop dancer, sequined glove, moonwalk-like glides, crisp spins"}),
    (["madonna*"], {"voix": "bright confident pop female vocals", "musique": "1980s dance pop, synth bass, drum machine, catchy hooks"}),
    (["whitney houston", "whitney"], {"voix": "soaring powerful female R&B vocals, gospel melisma", "musique": "1990s power ballad, piano, strings, key change"}),
    (["adele*"], {"voix": "rich soulful female vocals, powerful chest voice, emotional", "musique": "piano soul ballad, strings, big drums"}),
    (["amy winehouse", "winehouse"], {"voix": "smoky retro soul female vocals, jazzy phrasing", "musique": "1960s retro soul, horn section, Motown drums"}),
    (["david bowie", "bowie"], {"voix": "theatrical androgynous male vocals, wide range", "musique": "glam rock, art rock, saxophone, synths",
                                "jeu": "glam rock star archetype, glitter, bold makeup, alien elegance"}),
    (["freddie mercury", "mercury*"], {"voix": "operatic powerful male rock vocals, huge range, theatrical", "musique": "arena rock with operatic choirs and piano"}),
    (["queen*"], {"voix": "operatic multitracked rock harmonies", "musique": "1970s arena rock, layered vocal harmonies, piano, stacked guitar orchestra, stomping beat"}),
    (["beatles", "les beatles", "the beatles"], {"voix": "bright male vocal harmonies, Liverpool pop", "musique": "1960s British pop rock, jangly guitars, bass, catchy melodies"}),
    (["abba"], {"voix": "bright female pop harmonies", "musique": "1970s Europop, disco piano, glossy strings, catchy chorus"}),
    (["bob marley", "marley*"], {"voix": "relaxed soulful Jamaican male vocals", "musique": "roots reggae, offbeat skank guitar, deep bass, one-drop drums"}),
    (["ac/dc", "acdc", "ac dc"], {"voix": "high screeching hard rock male vocals", "musique": "hard rock, crunchy power chords, driving 4/4 beat"}),
    (["pink floyd"], {"voix": "dreamy detached male vocals", "musique": "psychedelic progressive rock, long guitar solos, synth pads, spacey"}),
    (["nirvana", "kurt cobain"], {"voix": "raw raspy grunge male vocals, quiet-loud", "musique": "1990s grunge, distorted guitars, heavy drums"}),
    (["daft punk"], {"voix": "vocoder robot vocals", "musique": "French house, filtered disco samples, four-on-the-floor, funky bass",
                     "jeu": "two robot-helmeted performers archetype, chrome, glowing visors"}),
    (["jean-michel jarre", "jarre*"], {"musique": "1970s electronic synth symphony, analog arpeggios, spacey pads, laser show grandeur"}),
    (["vangelis"], {"musique": "lush analog synth score, Yamaha CS-80 brass, melancholic and epic"}),
    (["hans zimmer", "zimmer*"], {"musique": "epic modern film score, huge braams, pounding percussion, ostinato strings"}),
    (["john williams"], {"musique": "grand symphonic adventure film score, heroic brass fanfares, soaring strings"}),
    (["ennio morricone", "morricone"], {"musique": "spaghetti western score, whistling, twangy guitar, choir, trumpet, whip cracks"}),
    (["mozart"], {"musique": "classical era orchestra, elegant and bright, harpsichord, string quartet"}),
    (["vivaldi"], {"musique": "baroque strings, harpsichord continuo, energetic violin concerto"}),
    # ---- acteurs, actrices : le jeu, jamais le visage
    (["john wayne", "wayne*"], {
        "jeu": "classic Hollywood cowboy archetype, slow rolling walk, laconic drawl, wide-brimmed hat, leather vest, steady unflinching gaze",
        "image": "1950s Technicolor western, Monument Valley-like desert buttes, warm saturated colors"}),
    (["clint eastwood", "eastwood*"], {
        "jeu": "taciturn gunslinger archetype, squinting eyes, poncho, cigarillo, few words, menacing calm",
        "image": "spaghetti western, extreme close-ups, dusty sun-bleached tones, wide desert vistas"}),
    (["alain delon", "delon"], {
        "jeu": "cool impassive 1960s French gangster archetype, trench coat and fedora, minimal gestures, icy silence, elegant poise",
        "image": "1960s French policier, cold blue-grey palette, rain-wet Paris streets, neon at night"}),
    (["simon templar", "le saint*", "templar*"], {
        "jeu": "suave 1960s British gentleman-adventurer archetype, tailored light suit, raised eyebrow, wry half-smile, unhurried elegance, "
               "witty and charming under pressure",
        "image": "1960s British TV adventure series look, glossy colors, Riviera sunshine, vintage white sports car"}),
    (["roger moore"], {
        "jeu": "debonair British gentleman archetype, polished manners, ironic raised eyebrow, light humor, impeccable suit",
        "image": "1970s glamorous spy-adventure look, jet-set locations, warm sunny tones"}),
    (["cary grant"], {"jeu": "urbane charming leading man archetype, effortless poise, playful wit, sharp tailoring",
                      "image": "1950s Hollywood romantic thriller, Technicolor, elegant Riviera"}),
    (["belmondo", "jean-paul belmondo", "bebel*"], {
        "jeu": "charming roguish French adventurer archetype, cheeky grin, nonchalant swagger, does his own stunts, quick banter",
        "image": "1970s French action comedy, rooftop chases, sunny Riviera, vintage cars"}),
    (["jean gabin", "gabin*"], {"jeu": "gruff working-class patriarch, heavy calm presence, sparing words", "image": "1950s French black and white film, Parisian bistro"}),
    (["louis de funes", "de funes", "funes"], {"jeu": "hyperactive irascible comic, frantic grimaces, explosive tantrums, fast gestures",
                                               "image": "1960s French comedy, bright colors, slapstick"}),
    (["bourvil"], {"jeu": "naive good-natured simpleton, gentle befuddled smile, clumsy kindness"}),
    (["lino ventura", "ventura*"], {"jeu": "tough taciturn hard man, contained anger, stocky stillness"}),
    (["charlie chaplin", "chaplin", "charlot*"], {"jeu": "silent film tramp archetype, bowler hat, cane, baggy trousers, waddling walk, pantomime",
                                                 "image": "1920s silent film, black and white, film scratches, iris transitions, intertitles"}),
    (["humphrey bogart", "bogart"], {"jeu": "hard-boiled detective archetype, trench coat, fedora, cigarette, world-weary lisp",
                                     "image": "1940s film noir, high-contrast black and white, venetian blind shadows"}),
    (["marilyn monroe", "marilyn*"], {"jeu": "1950s Hollywood glamour archetype, breathy voice, playful innocence, white halter dress",
                                     "image": "1950s Technicolor glamour, soft focus, studio lighting"}),
    (["audrey hepburn", "hepburn*"], {"jeu": "elegant gamine archetype, little black dress, pearls, graceful poise"}),
    (["james dean"], {"jeu": "rebellious 1950s youth archetype, red jacket, slouch, brooding"}),
    (["bruce lee"], {"jeu": "martial arts master archetype, lightning-fast strikes, intense focus, battle cries", "image": "1970s kung fu film, crash zooms"}),
    (["schwarzenegger", "arnold*"], {"jeu": "muscular action hero archetype, stoic one-liners, heavy machine gun", "image": "1980s action movie, explosions, neon and smoke"}),
    # ---- films, sagas, réalisateurs : le look, jamais les personnages ni les logos
    (["star wars", "la guerre des etoiles"], {
        "image": "1970s space opera look, anamorphic widescreen, film grain, used and weathered spaceships, twin-sun desert planets, "
                 "glowing energy blades, practical models, sweeping starfields",
        "jeu": "space opera heroes and villains archetypes, flowing robes, armored helmets, laser blasters", "musique": "grand symphonic space adventure score"}),
    (["indiana jones"], {"image": "1930s pulp adventure look, golden desert light, ancient temples, jungle ruins",
                         "jeu": "rugged adventurer archetype, fedora, leather jacket, bullwhip"}),
    (["james bond", "007"], {"image": "1960s spy thriller look, glamorous casinos, exotic locations, gadgets",
                             "jeu": "suave secret agent archetype, tuxedo, raised eyebrow, cool under fire", "musique": "1960s spy jazz, brass, surf guitar"}),
    (["matrix*"], {"image": "green-tinted cyberpunk, rain, black leather coats, slow-motion bullet time, digital rain code"}),
    (["mad max"], {"image": "post-apocalyptic desert, rusted spiked vehicles, orange and teal, dust storms"}),
    (["blade runner"], {"image": "neon noir cyberpunk city, rain, smoke, towering billboards, night", "musique": "melancholic analog synth score"}),
    (["harry potter"], {"image": "gothic magical school look, candlelit stone halls, floating candles, misty castle"}),
    (["seigneur des anneaux", "lord of the rings"], {"image": "epic high fantasy, misty mountains, medieval villages, golden hour, sweeping aerial shots"}),
    (["wes anderson"], {"image": "symmetrical pastel compositions, centered framing, whimsical dollhouse sets, flat lay"}),
    (["tarantino"], {"image": "1970s grindhouse look, saturated colors, trunk shots, bold title cards", "jeu": "witty violent banter, cool characters in black suits"}),
    (["tim burton", "burton*"], {"image": "gothic whimsical, twisted curly shapes, pale faces, striped patterns, moonlit"}),
    (["kubrick"], {"image": "cold symmetrical one-point perspective, wide-angle, clinical lighting"}),
    (["spielberg"], {"image": "1980s family adventure look, lens flares, suburban streets, bikes, warm wonder"}),
    (["sergio leone", "leone*"], {"image": "spaghetti western, extreme close-ups of eyes, wide desert, long tense standoffs"}),
    (["hitchcock"], {"image": "1950s suspense thriller, dramatic shadows, vertigo zoom, saturated Technicolor"}),
    (["miyazaki", "ghibli"], {"image": "hand-painted anime look, soft watercolor skies, lush countryside, gentle whimsical creatures"}),
    (["pixar"], {"image": "polished 3D animated family film look, soft global illumination, expressive cartoon characters"}),
    (["disney"], {"image": "classic hand-drawn animated fairy tale look, vibrant colors, storybook castles"}),
    (["amelie poulain", "amelie*"], {"image": "whimsical Montmartre, saturated green and red, warm golden glow, quirky close-ups"}),
    (["tontons flingueurs"], {"image": "1960s French black and white crime comedy, smoky kitchens", "jeu": "gangsters in suits trading sharp witty insults"}),
    (["grande vadrouille"], {"image": "1960s French wartime comedy, countryside chases, bright colors"}),
    (["film noir"], {"image": "1940s film noir, high contrast black and white, rain, venetian blind shadows"}),
]

REFERENCES = {}
AVEC_LIEN = set()          # noms courants ailleurs (« une jarre », « queen », « cash ») : reconnus seulement après « comme », « à la manière de »…
for noms, d in _R:
    for n in noms:
        if n.endswith("*"):
            n = n[:-1]
            AVEC_LIEN.add(n)
        REFERENCES[n] = (noms[0].rstrip("*"), d)

# mots qui annoncent un style : ils partent avec le nom
LIENS = (r"(?:(?:dans\s+le\s+)?style\s+(?:de\s+|d'|du\s+)?|à\s+la\s+manière\s+(?:de\s+|d'|du\s+|des\s+)|façon\s+|comme\s+(?:dans\s+)?|"
         r"à\s+la\s+|(?:(?:dans|avec)\s+(?:un|le)\s+)?look\s+(?:de\s+|d'|du\s+)?|genre\s+|inspiré\s+(?:de\s+|d'|du\s+|par\s+))")
_ASPECTS = {"musique": ("voix", "musique"), "image": ("image", "jeu"), "logo": ("image", "jeu"), "video": ("image", "jeu")}
_VOIX = re.compile(r"chant|voix|vocal|sing|interpr", re.I)
_ORCH = re.compile(r"musique|orchestr|arrange|instrument|style\s+musical|accompagn", re.I)


def _net(t):
    return unicodedata.normalize("NFKD", t.lower()).encode("ascii", "ignore").decode()


def _toutes(params=None):
    refs = dict(REFERENCES)
    for k, v in ((params or {}).get("styles_perso") or {}).items():
        refs[_net(k).strip()] = (k, {"perso": v})
    return refs


def _description(d, famille, avant=""):
    if "perso" in d:
        return d["perso"]
    aspects = _ASPECTS.get(famille, ("image", "jeu"))
    if famille == "musique" and _VOIX.search(avant) and not _ORCH.search(avant) and d.get("voix"):
        aspects = ("voix",)                       # « chanté à la manière de … » : la voix seulement
    elif famille == "musique" and _ORCH.search(avant) and d.get("musique"):
        aspects = ("musique",)                    # « musique façon … » : l'orchestre seulement
    morceaux = [d[a] for a in aspects if d.get(a)]
    if not morceaux:                              # rien pour cette famille : ce qui existe (ex. un chanteur dans une vidéo)
        morceaux = [v for v in d.values() if v][:1]
    return ", ".join(morceaux)


def transposer(texte, famille="musique", params=None):
    """{"texte": la phrase sans les noms, "styles": [(nom, description anglaise)], "inconnus": [noms annoncés par
    « à la manière de », « comme »… mais pas connus], "ajout": descriptions jointes}. Hors ligne."""
    refs = _toutes(params)
    net = _net(texte)
    trouves, a_retirer = [], []
    for cle in sorted(refs, key=len, reverse=True):
        for m in re.finditer(r"(?<![\w])" + re.escape(cle) + r"(?![\w])", net):
            if any(a <= m.start() < b for a, b in a_retirer):
                continue
            debut = m.start()
            lien = re.search(_net(LIENS) + r"$", net[max(0, debut - 40):debut])
            if lien:
                debut = max(0, debut - 40) + lien.start()
            elif cle in AVEC_LIEN:
                continue
            a_retirer.append((debut, m.end()))
            nom, d = refs[cle]
            desc = _description(d, famille, net[max(0, debut - 50):debut])
            if desc and all(desc != x[2] for x in trouves):
                trouves.append((debut, nom, desc))
    trouves = [(n, d) for _p, n, d in sorted(trouves)]           # dans l'ordre de la phrase
    # le texte d'origine garde ses accents : on retire les mêmes positions (la normalisation garde la longueur sauf
    # lettres combinées, rares en français tapé au clavier)
    reste = texte
    if len(net) == len(texte):
        for a, b in sorted(a_retirer, reverse=True):
            reste = reste[:a] + reste[b:]
    else:
        reste = net
        for a, b in sorted(a_retirer, reverse=True):
            reste = reste[:a] + reste[b:]
    inconnus = []
    for m in re.finditer(LIENS + r"((?:[A-ZÉÈ][\w\-']+(?:\s+|$)){1,3})", reste):
        nom = m.group(1).strip()
        if nom and _net(nom) not in refs:
            inconnus.append(nom)
    reste = re.sub(r"\s+([,.;])", r"\1", re.sub(r"\s{2,}", " ", reste)).strip(" ,;")
    reste = re.sub(r"(,\s*){2,}", ", ", reste)
    return {"texte": reste, "styles": trouves, "inconnus": list(dict.fromkeys(inconnus)), "ajout": ", ".join(d for _n, d in trouves)}


CONSIGNE_IA = """Transpose each name into a STYLE DESCRIPTION in English, for an AI {quoi} generator that does not know names.
Describe only style: {aspects}. Never describe the face or exact physical likeness of a real person, never mention names,
characters, logos or trademarks. 10 to 25 words each.
Answer only with JSON: {{"name": "description", ...}}
Names: {noms}
Context of the request: {contexte}"""


def demande_ia(noms, famille, contexte=""):
    if famille == "musique":
        quoi, aspects = "music", "vocal timbre and phrasing, genre, era, instrumentation, tempo, production"
    else:
        quoi, aspects = "image and video", ("visual look (era, film stock, lighting, colors, sets, costumes) and, for an actor, the acting "
                                            "archetype (attitude, walk, way of speaking, gestures)")
    return CONSIGNE_IA.format(quoi=quoi, aspects=aspects, noms=", ".join(noms), contexte=contexte[:300])


def lire_reponse(r, noms):
    """JSON de l'IA → {nom: description} ; les noms restés dans une description sont retirés."""
    m = re.search(r"\{.*\}", r or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        d = {}
    out = {}
    for k, v in d.items():
        if not isinstance(v, str):
            continue
        for n in noms:
            for mot in n.split():
                if len(mot) > 2:
                    v = re.sub(re.escape(mot), "", v, flags=re.I)
        v = re.sub(r"\s{2,}", " ", v).strip(" ,.")
        nom = next((n for n in noms if _net(n) == _net(k)), k)
        if v:
            out[nom] = v
    return out


def transposer_ia(noms, famille, contexte="", params=None, niveau="locale"):
    """Demande à l'IA (locale : rien ne sort ; cloud : votre clef) la description des noms inconnus ; renvoie {nom: description}."""
    texte = demande_ia(noms, famille, contexte)
    systeme = "You describe artistic styles without naming or copying anyone."
    if niveau == "locale":
        from . import ia_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise RuntimeError(_("Aucun modèle d'IA locale pour écrire : installez « Vision et texte » dans Préférences › IA locale, "
                                 "ou choisissez l'IA cloud."))
        r = ia_locale.generer(modele, texte, [], systeme=systeme, params=params)
    else:
        from . import ia
        r = ia.demander(params or {}, systeme, texte, max_jetons=600)
    return lire_reponse(r if isinstance(r, str) else str(r), noms)


def retenir(params, styles):
    """Garde les transpositions dans « Mes styles » (suivent sur vos autres postes)."""
    perso = dict(params.get("styles_perso") or {})
    perso.update(styles)
    params["styles_perso"] = perso
    try:
        params.enregistrer()
    except AttributeError:
        pass
