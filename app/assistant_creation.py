"""Assistant de création (0.9.79) : le mode assisté de la vidéo par IA.

Philippe (17/11) : « tu as vu tout ce que l'on a été obligé de faire pour rallonger le rush… il faut être assisté ». Les
règles apprises à la main (un personnage par personne, une action par plan, fiches, images de départ et d'arrivée, plan
enchaîné sur une image validée, caméra jamais de dos) sont ici appliquées par le logiciel : on raconte la suite d'un
trait, une IA la lit avec l'image de départ et propose personnages, objets et plans ; on corrige en clair ; PhilCut
prépare fiches et images, fabrique, puis fait relire chaque plan par l'IA. Un budget (prévu, dépensé) suit tout.

Ce module ne dépend pas de l'interface ; il s'appuie sur sequence_ia (la séquence reste ouvrable en mode manuel).
"""
import copy
import os
import re

from . import sequence_ia as Q
from .langue import _

PRIX_IMAGE = 0.04
# 0.9.98 : le Réalisateur enchaîne tout par défaut ; les tests le coupent (PHILCUT_REALISATEUR=0), ainsi que la question de relecture
REALISATEUR_DEFAUT = os.environ.get("PHILCUT_REALISATEUR", "1") == "1"
PRIX_LECTURE = 0.01            # une lecture par l'IA cloud (analyse, correction, vérification) : ordre de grandeur


class ErreurAssistant(Exception):
    pass


CONSIGNE_ANALYSE = """Tu es réalisateur et tu prépares une courte séquence vidéo fabriquée par une IA vidéo, plan par plan.
{contexte}
A partir de l'histoire de l'utilisateur, rends un objet JSON :
{{"personnages": [{{"nom": "...", "genre": "personne" ou "objet", "sur_image": true ou false, "position": "gauche", "droite",
"centre" ou "", "boite": [x0, y0, x1, y1] en pourcentages de l'image (0 à 100) pour ce qui est sur l'image, sinon [],
"description": "..."}}],
 "lieux": [{{"nom": "...", "sur_image": true si c'est le décor de l'image de départ, "description": "lumière, matières, détails"}}],
 "plans": [{{"action": "...", "personnages": ["nom", ...], "hors_champ": "où sont ceux qu'on ne voit plus, ou vide",
 "lieu": "nom du lieu ou vide", "duree": 4 à 10, "camera": "cadrage et mouvement : plan large, plan moyen, gros plan ; fixe,
 recule, s'approche, accompagne…", "image_clef": true ou false, "pourquoi_clef": "si image_clef : en quelques mots, ce
 qu'elle doit fixer (« elles sont déjà dans la voiture »), sinon vide"}}],
 "remarques": "une phrase pour l'utilisateur, ou vide"}}
Règles impératives :
- Un personnage = UNE seule personne (jamais « les deux femmes » comme un seul personnage). Donne à chacun un nom court et
  neutre (« Femme brune », « Chauffeur »), jamais le nom d'une personne réelle ou célèbre.
- Les personnes visibles sur l'image de départ : sur_image = true, avec leur position sur l'image et une description qui
  les distingue (cheveux, vêtements, accessoires). Les personnes inventées par l'histoire : sur_image = false, avec une
  description physique complète (âge, allure, vêtements).
- Un objet important qui revient dans plusieurs plans (véhicule, accessoire) : genre = "objet", décrit précisément (couleur,
  forme), sans marque.
- UNE SEULE action simple par plan, physiquement possible, 4 à 10 secondes ; découpe « puis », « pour que », « pendant
  que » en plans séparés. Quand quelqu'un apparaît (un chauffeur), fais-le entrer dans un plan à lui avant qu'il agisse.
- Chaque plan liste seulement les personnages et objets qu'on y VOIT, par leur nom exact. Suis la continuité d'un plan à
  l'autre : quelqu'un qui monte dans un véhicule, entre dans un bâtiment ou sort du champ n'apparaît plus dans les plans
  suivants tant que l'histoire ne le fait pas ressortir ; dis où il est dans « hors_champ » (« les deux femmes sont dans la
  voiture »). Une liste vide = on ne voit aucun personnage (seulement le décor ou un objet).
- Images clefs : la vidéo de chaque plan part de la vraie dernière image du plan précédent ; on n'impose une image de fin
  (« image_clef »: true) qu'aux moments où la scène change vraiment (nouveau lieu, quelqu'un arrive ou s'en va, état très
  différent à respecter) et au dernier plan. Ailleurs false : le moteur enchaîne librement les gestes.
- Le cadrage suit l'action : plan large quand on se déplace d'un lieu à l'autre ou quand un véhicule doit tenir dans
  l'image, plus serré pour un geste ; dis-le dans « camera ».
- Caméra : simple et stable (recule, accompagne de côté, fixe) ; jamais de dos quand les visages doivent rester
  reconnaissables.
- Un lieu = un décor où se passent un ou plusieurs plans (l'escalier, la rue devant l'entrée…) ; au plus 4 lieux.
- Au plus 8 plans. Ecris nom, description, action et caméra en {langue}.
"""

CONSIGNE_MODIFIER = """Tu aides à préparer une séquence vidéo par IA. Voici son état (JSON) et une demande de l'utilisateur.
Rends l'état modifié, au même format : {{"personnages": [...], "plans": [...], "message": "ce que tu as changé, en une
phrase"}}. Ne change que ce qui est demandé ; garde mot pour mot les noms, descriptions et actions qui ne sont pas concernés.
Mêmes règles : un personnage = une personne, une seule action simple par plan (4 à 10 s), chaque plan liste ses
personnages, aucun nom de personne réelle. Ecris en {langue}."""

CONSIGNE_VERIFIER = """Tu contrôles un plan vidéo fabriqué par une IA. Les {n} premières images sont les fiches de référence
des personnages ({noms}). Les trois dernières sont le début, le milieu et la fin du plan fabriqué. Action demandée : « {action} ».
Rends un objet JSON : {{"visages": true si les personnes du plan ressemblent bien à leurs fiches du début à la fin (visage,
cheveux, vêtements), "action": true si l'action demandée est visible et plausible (personne ne traverse un objet, pas de
membre en trop), "probleme": "en une phrase courte, en {langue}, ce qui ne va pas ; vide si tout va bien"}}."""


def _langue():
    from . import langue
    return {"fr": "français", "en": "English", "de": "Deutsch", "es": "español", "it": "italiano"}.get(langue.LANGUE or "fr", "français")


def niveaux(params):
    """[(clef, libellé)] des IA qui peuvent mener l'assistance : cloud d'abord (le plus fiable), puis ce poste."""
    from . import ia
    clefs = {m for m, _k in ia.moteurs(dict(params, ia_moteur="claude"))}
    out = []
    if "claude" in clefs:
        out.append(("claude", _("Claude (cloud, le plus fiable)")))
    if "gemini" in clefs:
        out.append(("gemini", _("Gemini (cloud)")))
    out.append(("locale", _("IA locale (sur ce poste, gratuit)")))
    return out


def _jpeg(chemin, cote=1024):
    """L'image en JPEG réduit (octets) : assez pour être lue par une IA, légère à envoyer."""
    import tempfile
    from . import moteur
    sortie = os.path.join(tempfile.gettempdir(), f"philcut_assist_{os.getpid()}_{abs(hash(chemin)) % 10 ** 8}.jpg")
    moteur.lancer(["-y", "-i", chemin, "-vf", f"scale='min({cote},iw)':-2", "-frames:v", "1", "-q:v", "4", sortie])
    with open(sortie, "rb") as f:
        return f.read()


def demander(params, consigne, texte, images=(), niveau="claude", max_jetons=3000):
    """Objet JSON rendu par l'IA choisie ; les images sont des chemins de fichiers."""
    octets = [_jpeg(i) for i in images if i and os.path.exists(i)]
    if niveau == "locale":
        from . import ia_locale, analyse_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise ErreurAssistant(_("Aucune IA sur ce poste : Edition › Préférences › IA locale, ou choisissez Claude ou Gemini."))
        return analyse_locale.lire_json(ia_locale.generer(modele, consigne + "\n\n" + texte, octets, json_attendu=True, params=params))
    from . import ia
    ancien = ia.MOTEUR_FORCE
    ia.MOTEUR_FORCE = niveau if niveau in ("claude", "gemini") else ancien
    try:
        return ia.demander(params, consigne, texte, images=octets or None, json_attendu=True, max_jetons=max_jetons)
    finally:
        ia.MOTEUR_FORCE = ancien


# ------------------------------------------------------------------ lecture des réponses (tout est borné)
def _texte(v, n=400):
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def lire_analyse(d):
    """Réponse de l'IA rendue sûre : noms uniques, genres connus, durées bornées, plans qui citent des noms existants."""
    d = d if isinstance(d, dict) else {}
    persos, vus = [], set()
    for p in (d.get("personnages") or [])[:8]:
        if not isinstance(p, dict):
            continue
        nom = _texte(p.get("nom"), 40)
        if not nom or nom.lower() in vus:
            continue
        vus.add(nom.lower())
        persos.append({"nom": nom, "genre": "objet" if str(p.get("genre", "")).lower().startswith("obj") else "personne",
                       "sur_image": bool(p.get("sur_image")),
                       "position": _texte(p.get("position"), 12).lower() if _texte(p.get("position"), 12).lower() in
                       ("gauche", "droite", "centre", "left", "right", "center") else "",
                       "description": _texte(p.get("description")), "style": _texte(p.get("style"), 60),
                       "boite": lire_boite(p.get("boite")) if p.get("sur_image") else None})
    lieux, vus_l = [], set()
    for li in (d.get("lieux") or [])[:4]:
        if isinstance(li, dict) and _texte(li.get("nom"), 40) and _texte(li.get("nom"), 40).lower() not in vus_l:
            vus_l.add(_texte(li.get("nom"), 40).lower())
            lieux.append({"nom": _texte(li.get("nom"), 40), "sur_image": bool(li.get("sur_image")), "description": _texte(li.get("description")),
                          "image_n": 2 if str(li.get("image") or "") == "2" else 1})
    plans = []
    for pl in (d.get("plans") or [])[:10]:
        if not isinstance(pl, dict) or not _texte(pl.get("action")):
            continue
        try:
            duree = int(round(float(pl.get("duree") or Q.DUREE_PLAN)))
        except (TypeError, ValueError):
            duree = Q.DUREE_PLAN
        noms = [n for n in (_texte(x, 40) for x in (pl.get("personnages") or []) if x) if n.lower() in vus]
        lieu = _texte(pl.get("lieu"), 40)
        plans.append({"action": _texte(pl.get("action"), 300), "personnages": noms, "duree": max(3, min(15, duree)),
                      "camera": _texte(pl.get("camera"), 160), "lieu": lieu if lieu.lower() in vus_l else "",
                      "hors_champ": _texte(pl.get("hors_champ"), 200), "visibles_fixes": True,
                      "clef": bool(pl.get("image_clef")), "clef_pourquoi": _texte(pl.get("pourquoi_clef"), 160)})
    return {"personnages": persos, "lieux": lieux, "plans": plans, "remarques": _texte(d.get("remarques") or d.get("message"), 300)}


def lire_boite(b):
    """[x0, y0, x1, y1] en fractions (0..1), rangées et assez grandes ; None si la boîte n'est pas lisible."""
    try:
        x0, y0, x1, y1 = (float(v) for v in list(b)[:4])
    except (TypeError, ValueError):
        return None
    if max(x0, y0, x1, y1) > 1.5:                       # pourcentages (ou 0..1000 à la façon de Gemini)
        k = 1000.0 if max(x0, y0, x1, y1) > 100.5 else 100.0
        x0, y0, x1, y1 = x0 / k, y0 / k, x1 / k, y1 / k
    x0, x1 = sorted((max(0.0, min(1.0, x0)), max(0.0, min(1.0, x1))))
    y0, y1 = sorted((max(0.0, min(1.0, y0)), max(0.0, min(1.0, y1))))
    return [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)] if x1 - x0 > 0.03 and y1 - y0 > 0.03 else None


BOITES_POSITION = {"gauche": [0.04, 0.08, 0.46, 0.98], "left": [0.04, 0.08, 0.46, 0.98], "droite": [0.54, 0.08, 0.96, 0.98],
                   "right": [0.54, 0.08, 0.96, 0.98], "centre": [0.3, 0.08, 0.7, 0.98], "center": [0.3, 0.08, 0.7, 0.98]}


def boite_par_defaut(p):
    return BOITES_POSITION.get(p.get("position") or "", [0.3, 0.08, 0.7, 0.98])


def boite_autour(x, y, larg=0.3, haut=0.85):
    """Un clic sur l'image (fractions) : un cadre de personne debout centré sur le clic, gardé dans l'image."""
    x0 = max(0.0, min(1.0 - larg, x - larg / 2))
    y0 = max(0.0, min(1.0 - haut, y - haut / 2))
    return [round(x0, 4), round(y0, 4), round(x0 + larg, 4), round(y0 + haut, 4)]


def decouper(image, boite, sortie, marge=0.12, detourer=True, personne=True):
    """La personne ou l'objet découpé dans l'image (avec un peu de marge) : c'est cette découpe qui fait la fiche, et non
    plus toute la photo de groupe. 0.9.96 : détourée seulement pour une personne et avec le modèle « Détourage de personne »
    de ce poste ; sinon le cadre reste tel quel (le détourage approximatif mélangeait les voisins à l'objet)."""
    from . import moteur
    from PySide6.QtGui import QImage
    q = QImage(image)
    w, h = q.width(), q.height()
    if not (w and h):
        return ""
    x0, y0, x1, y1 = boite
    mx, my = (x1 - x0) * marge, (y1 - y0) * marge
    x0, y0, x1, y1 = max(0.0, x0 - mx), max(0.0, y0 - my), min(1.0, x1 + mx), min(1.0, y1 + my)
    cw, ch = max(16, int((x1 - x0) * w)) // 2 * 2, max(16, int((y1 - y0) * h)) // 2 * 2
    moteur.lancer(["-y", "-i", image, "-vf", f"crop={cw}:{ch}:{int(x0 * w)}:{int(y0 * h)}", "-frames:v", "1", sortie])
    if not os.path.exists(sortie):
        return ""
    if detourer and personne:
        detourer_decoupe(sortie, marge / (1 + 2 * marge))
    return sortie


def detourage_local_possible():
    """Le modèle « Détourage de personne » est-il installé ? (sans lui, pas de détourage sur ce poste)"""
    try:
        from . import segmentation
        return bool(segmentation._portable())
    except Exception:      # noqa: BLE001
        return False


def detourer_decoupe(chemin, marge=0.1):
    """Une personne détourée dans son cadre par le modèle « Détourage de personne » de ce poste, posée sur un fond blanc uni,
    ce que les IA lisent le mieux. 0.9.96 : plus de GrabCut (il gardait des morceaux de décor et de voisins). Renvoie True si
    le détourage a été fait (sinon la découpe reste telle quelle)."""
    try:
        import cv2
        import numpy as np
        from . import segmentation
        if not segmentation._portable():
            return False
        img = cv2.imread(chemin)
        if img is None:
            return False
        H, L = img.shape[:2]
        m = segmentation.masque_image(img)
        if m is None:
            return False
        part = (m > 127).mean()
        if not 0.12 < part < 0.97:            # rien ou tout : on garde la découpe
            return False
        a = cv2.GaussianBlur(m, (0, 0), 1.2).astype(np.float32)[..., None] / 255.0
        blanc = np.full_like(img, 255)
        cv2.imwrite(chemin, (img * a + blanc * (1 - a)).astype(np.uint8))
        return True
    except Exception:          # noqa: BLE001
        return False


CONSIGNE_ISOLER = ("Keep ONLY the main {quoi} in the centre of this image, exactly identical: same face, hair, body, clothes, "
                   "colours, shape, markings and proportions. Remove everything else (other people, other objects, background) "
                   "and place it whole, not cropped, on a plain pure white background, same angle. Do not change, beautify or "
                   "redraw it; no text.")
PRIX_ISOLER = 0.04


def isoler_gemini(chemin, quoi, params):
    """0.9.96 : Gemini garde seulement le sujet du cadre, entier, sur fond blanc (environ 0,04 $) ; remplace le fichier."""
    from . import ia
    with open(chemin, "rb") as f:
        octets = f.read()
    r = ia.retoucher_image(params, octets, CONSIGNE_ISOLER.format(quoi=quoi))
    if not r:
        raise ErreurAssistant(_("Gemini n'a pas rendu d'image."))
    with open(chemin, "wb") as f:
        f.write(r)
    return chemin


CONSIGNE_DECRIRE = """Tu aides à décrire {quoi} pour qu'une IA le dessine puis le garde identique d'un plan vidéo à l'autre. Voici ce
qu'en dit l'utilisateur et l'histoire. Rends un objet JSON {{"description": "description physique précise et complète en une ou
deux phrases ({details}), sans aucun nom de personne réelle ni marque"}}. Garde tout ce que l'utilisateur a écrit. Ecris en {langue}."""


def aider_a_decrire(params, p, histoire="", niveau="claude", image=None):
    """Complète la description d'un personnage ou d'un objet (inventé, ou vu sur l'image jointe)."""
    objet = p.get("genre") == "objet"
    r = demander(params, CONSIGNE_DECRIRE.format(quoi=_("un objet") if objet else _("une personne"), langue=_langue(),
                                                 details="couleur, forme, matière, état" if objet else
                                                 "âge, allure, visage, cheveux, vêtements, chaussures"),
                 f"Nom : {p.get('nom', '')}\nCe qu'en dit l'utilisateur : {p.get('description', '')}\nHistoire : {histoire}",
                 [image] if image else [], niveau, max_jetons=600)
    return _texte((r or {}).get("description"), 500) if isinstance(r, dict) else ""


CONTEXTE_RACCORD = ("L'image jointe montre DEUX images côte à côte : à gauche la DERNIERE image d'un rush filmé, à droite la "
                    "PREMIERE image du rush filmé ensuite. Entre les deux, rien n'a été filmé : la séquence reconstitue ce qui s'est "
                    "passé. Le premier plan part exactement de l'image de gauche, le dernier plan arrive exactement sur l'image de "
                    "droite (même cadrage, mêmes personnes, même lieu). Les boîtes sont en pourcentages de l'image entière (les deux "
                    "côte à côte). Pour chaque lieu, ajoute \"image\": 1 (décor de gauche) ou 2 (décor de droite). Prévois une "
                    "image clef partout où l'état doit être respecté pour arriver à droite (quelqu'un qui attend, qui arrive, un "
                    "changement de lieu).")


def image_raccord(gauche, droite, sortie):
    """Les deux images réelles côte à côte, même hauteur, séparées d'un trait blanc (0.9.87) : une seule image pour que
    l'assistant voie l'avant et l'après, et pour tracer les cadres des personnes de l'un ou l'autre côté."""
    from PySide6.QtGui import QImage, QPainter, QColor
    a, b = QImage(gauche), QImage(droite)
    if a.isNull() or b.isNull():
        return gauche
    H = min(720, max(a.height(), b.height()))
    a = a.scaledToHeight(H)
    b = b.scaledToHeight(H)
    sep = max(6, H // 90)
    img = QImage(a.width() + sep + b.width(), H, QImage.Format_RGB32)
    img.fill(QColor("#ffffff"))
    p = QPainter(img)
    p.drawImage(0, 0, a)
    p.drawImage(a.width() + sep, 0, b)
    p.end()
    img.save(sortie)
    return sortie


def analyser(params, histoire, image=None, niveau="claude", image_fin=None):
    """L'IA lit l'histoire (et regarde l'image de départ) : personnages, objets, plans d'une action. image_fin (0.9.87) : la
    première image du rush suivant ; `image` est alors l'image double (avant | après)."""
    contexte = (CONTEXTE_RACCORD if image and image_fin else
                "L'image jointe est la DERNIERE image d'un plan déjà tourné : la séquence en est la suite directe ; le premier plan "
                "part exactement de cette image." if image else
                "Il n'y a pas d'image de départ : tous les personnages sont inventés (sur_image = false).")
    try:
        r = lire_analyse(demander(params, CONSIGNE_ANALYSE.format(contexte=contexte, langue=_langue()),
                                  "Histoire : " + histoire.strip(), [image] if image else [], niveau))
    except Exception as e:      # noqa: BLE001 : 0.9.86 : image refusée → on redemande sans l'image avant d'abandonner
        if not image or "clef" in str(e).lower() or "refusée" in str(e).lower():
            raise
        contexte = ("L'image de départ n'a pas pu être lue : déduis les personnes de l'histoire (sur_image = true pour celles "
                    "qui y sont déjà au début, position et boîte vides).")
        r = lire_analyse(demander(params, CONSIGNE_ANALYSE.format(contexte=contexte, langue=_langue()),
                                  "Histoire : " + histoire.strip(), [], niveau))
    if not r["plans"]:
        raise ErreurAssistant(_("L'IA n'a pas proposé de plan utilisable : reformulez l'histoire, ou changez d'IA."))
    return r


CONSIGNE_CONTINUITE = """Tu es scripte (continuité) sur une séquence vidéo fabriquée par une IA, plan par plan. Voici les
personnages et objets (noms exacts) et les plans dans l'ordre. Pour CHAQUE plan, dis qui et quoi on VOIT réellement à l'image,
en suivant l'histoire : quelqu'un qui monte dans un véhicule, entre quelque part ou sort du champ n'est plus visible dans les
plans suivants tant qu'il n'en ressort pas. Dis où sont ceux qu'on ne voit pas. Propose le cadrage qui permet l'action (plan
large pour un déplacement ou un véhicule entier, plus serré pour un geste ; fixe, recule, s'approche, accompagne).
Rends un objet JSON {{"plans": [{{"personnages": ["nom", ...], "hors_champ": "...", "camera": "..."}}]}} avec exactement
{n} plans, dans le même ordre. Ecris en {langue}."""


def continuite(params, seq, niveau="claude"):
    """0.9.86 : la scripte. Remplit, plan par plan, qui est visible, où sont les autres, et le cadrage (texte seul, peu
    coûteux). Les plans gardent leur action. Renvoie le nombre de plans changés."""
    noms = [p["nom"] for p in seq["personnages"]]
    texte = ("Personnages et objets : " + "; ".join(f"{p['nom']} ({(p.get('description') or '')[:120]})" for p in seq["personnages"]) +
             "\nPlans :\n" + "\n".join(f"{i + 1}. {pl.get('action', '')}" for i, pl in enumerate(seq["plans"])))
    r = demander(params, CONSIGNE_CONTINUITE.format(n=len(seq["plans"]), langue=_langue()), texte, [], niveau, max_jetons=1500)
    lignes = (r or {}).get("plans") if isinstance(r, dict) else None
    if not isinstance(lignes, list) or len(lignes) != len(seq["plans"]):
        raise ErreurAssistant(_("La continuité n'a pas pu être établie : réessayez, ou remplissez la colonne « Qui »."))
    bas = {n.lower(): n for n in noms}
    change = 0
    for pl, l in zip(seq["plans"], lignes):
        if not isinstance(l, dict):
            continue
        vus = [bas[x.lower()] for x in (_texte(y, 40) for y in l.get("personnages") or [] if y) if x.lower() in bas]
        avant = (pl.get("personnages"), pl.get("hors_champ"), pl.get("camera"))
        pl["personnages"] = vus
        pl["hors_champ"] = _texte(l.get("hors_champ"), 200)
        if l.get("camera"):
            pl["camera"] = _texte(l.get("camera"), 160)
        pl["visibles_fixes"] = True
        if avant != (pl["personnages"], pl["hors_champ"], pl.get("camera")):
            change += 1
    return change


def analyse_simple(histoire):
    """Sans IA : une phrase ou un « puis » = un plan ; les personnages restent à ajouter à la main."""
    return {"personnages": [], "remarques": "",
            "plans": [{"action": pl["action"], "personnages": [], "duree": Q.DUREE_PLAN, "camera": ""} for pl in Q.decouper_simple(histoire)]}


# ------------------------------------------------------------------ de l'analyse à la séquence
_POSITIONS = {"gauche": _("à gauche sur l'image"), "left": _("à gauche sur l'image"), "droite": _("à droite sur l'image"),
              "right": _("à droite sur l'image"), "centre": _("au centre de l'image"), "center": _("au centre de l'image")}


def description_complete(p):
    """« à gauche sur l'image, cheveux longs bruns… » : la position sert à choisir la bonne personne d'une photo de groupe."""
    pos = _POSITIONS.get(p.get("position") or "", "") if p.get("sur_image") else ""
    d = (p.get("description") or "").strip()
    return ", ".join(x for x in (pos, d) if x and not (pos and d.lower().startswith(pos.lower())))


def _sans_accent(t):
    import unicodedata
    t = unicodedata.normalize("NFD", (t or "").lower())
    return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn" and (c.isalnum() or c == " ")).split())


def relier_noms(noms, connus):
    """1.0.6 : les noms cités par les plans, ramenés aux noms des cartes. Une carte renommée (prise dans la bibliothèque :
    « Maxime » devenu « Pilote Maxime ») gardait ses plans sous l'ancien nom : le pilote n'apparaissait plus nulle part et
    n'avait pas de fiche. Même nom sans accents, nom contenu dans l'autre, ou un mot de plus de 3 lettres en commun."""
    vus, sortie = set(), []
    nets = [(c, _sans_accent(c)) for c in connus]
    for n in noms or []:
        m = _sans_accent(n)
        trouve = next((c for c, x in nets if x == m), None) or \
            next((c for c, x in nets if len(m) > 3 and len(x) > 3 and (m in x or x in m)), None)
        if trouve is None:
            mots = {w for w in m.split() if len(w) > 3}
            cand = [c for c, x in nets if mots & {w for w in x.split() if len(w) > 3}]
            trouve = cand[0] if len(cand) == 1 else None
        nom = trouve or n
        if nom not in vus:
            vus.add(nom)
            sortie.append(nom)
    return sortie


def appliquer(seq, analyse, image=None, image_cartes=None):
    """Met l'analyse dans la séquence en gardant ce qui est déjà fait pour ce qui n'a pas changé (fiches, images, vidéos)."""
    anciens = {p["nom"].lower(): p for p in seq.get("personnages") or []}
    persos = []
    for a in analyse["personnages"]:
        p = Q.personnage(a["nom"], description_complete(a), a.get("style", ""))
        vieux = anciens.get(a["nom"].lower())
        for cle in ("source", "boite", "photo", "decoupe", "accord", "biblio", "planche", "images", "tenue", "mode"):     # ce que la carte a fixé suit
            if a.get(cle) is None and vieux and vieux.get(cle) is not None:
                if cle == "decoupe" and (a.get("boite") or vieux.get("boite")) != vieux.get("boite"):
                    continue                              # cadre changé : la découpe est refaite
                a[cle] = vieux[cle]
        source = a.get("source") or ("image" if a["sur_image"] and image else "inventer")
        for cle in ("tenue", "mode", "planche_tenue"):        # 0.9.88 : tenue de la scène, façon de créer
            val = a[cle] if cle in a and cle != "planche_tenue" else (vieux or {}).get(cle)
            if val:
                p[cle] = val
        p.update(genre=a["genre"], sur_image=source == "image", position=a.get("position", ""), brut=a.get("description", ""),
                 source=source, boite=a.get("boite") or (boite_par_defaut(a) if source == "image" else None))
        if source == "bibliotheque":                      # 0.9.81 : repris tel quel de la bibliothèque (fiche comprise)
            p["images"] = [x for x in a.get("images") or [] if x and os.path.exists(x)]
            if a.get("planche") and os.path.exists(a["planche"]):
                p["planche"] = a["planche"]
            p["biblio"] = a.get("biblio", "")
        elif source == "image" and (image_cartes or image):
            dec = a.get("decoupe") if a.get("decoupe") and os.path.exists(a["decoupe"]) else ""
            if not dec and p["boite"]:
                try:
                    dec = decouper(image_cartes or image, p["boite"], os.path.join(Q.dossier(seq), "decoupe_" + re.sub(r"[^\w-]+", "_", a["nom"])[:30] + ".png"), personne=a.get("genre") != "objet")
                except Exception:      # noqa: BLE001 : sans découpe, la photo entière et la position suffisent
                    dec = ""
            p["decoupe"] = dec
            p["images"] = [x for x in (dec, image_cartes or image) if x]
        elif source == "photo" and a.get("photo"):
            p["photo"] = a["photo"]
            p["images"] = [a["photo"]]
        if a.get("accord"):
            p["accord"] = True
        if vieux and vieux.get("description") == p["description"] and vieux.get("style", "") == p["style"] and \
                vieux.get("images") == p["images"]:
            for cle in ("planche", "accord"):
                if vieux.get(cle):
                    p[cle] = vieux[cle]
        persos.append(p)
    if "lieux" in analyse:                                  # 0.9.81 : les lieux (décor de l'image, photo, décrit, bibliothèque)
        anciens_l = {x["nom"].lower(): x for x in seq.get("lieux") or []}
        lieux = []
        for a in analyse["lieux"]:
            li = Q.lieu(a["nom"], a.get("description", ""))
            vieux = anciens_l.get(a["nom"].lower()) or {}
            source = a.get("source") or vieux.get("source") or ("image" if a.get("sur_image") and image else "inventer")
            li["source"] = source
            if source == "image" and image:
                rac = seq.get("raccord") or {}
                li["images"] = [rac["image_fin"] if a.get("image_n") == 2 and rac.get("image_fin") else image]
            elif source == "photo" and (a.get("photo") or vieux.get("photo")):
                li["photo"] = a.get("photo") or vieux.get("photo")
                li["images"] = [li["photo"]]
            elif source == "bibliotheque":
                li["images"] = [x for x in (a.get("images") or vieux.get("images") or []) if os.path.exists(x)]
                li["biblio"] = a.get("biblio") or vieux.get("biblio", "")
                if (a.get("planche") or vieux.get("planche")) and os.path.exists(a.get("planche") or vieux.get("planche")):
                    li["planche"] = a.get("planche") or vieux.get("planche")      # 0.9.88 : la planche du lieu suit
            lieux.append(li)
        seq["lieux"] = lieux
    cle_plan = lambda pl: (pl.get("action"), tuple(pl.get("personnages") or []), pl.get("camera") or "")
    vieux_plans = {cle_plan(pl): pl for pl in seq.get("plans") or []}
    plans = []
    precedent_change = False
    connus = [x["nom"] for x in persos]
    for a in analyse["plans"]:
        a["personnages"] = relier_noms(a.get("personnages"), connus)
        for cle in ("hors_champ", "visibles_fixes"):
            if isinstance(a.get(cle), list):
                a[cle] = relier_noms(a[cle], connus)
        pl = Q.plan(a["action"], a["personnages"], a.get("lieu", ""), a["duree"], camera=a.get("camera", ""))
        for cle in ("hors_champ", "visibles_fixes"):
            if a.get(cle):
                pl[cle] = a[cle]
        pl["clef"] = bool(a.get("clef"))            # 0.9.87 : image de fin imposée seulement aux images clefs
        pl["clef_pourquoi"] = a.get("clef_pourquoi", "")
        pl["sans_fin"] = not pl["clef"]
        vieux = vieux_plans.get(cle_plan(a))
        if vieux and precedent_change and vieux.get("enchainer", True):
            vieux = dict(vieux, image_fin="", images_ok=False, fichier="", verdict=None)    # son départ a changé : arrivée à refaire
        precedent_change = not vieux                # 0.9.86 : seul ce qui a changé (et le plan qui en part) est refait
        if vieux:
            for cle in ("image", "image_fin", "images_ok", "sans_fin", "clef", "clef_pourquoi", "fin_reelle", "fichier", "verdict", "precision", "precision_fin",
                        "consigne"):
                if cle in vieux:
                    pl[cle] = vieux[cle]
            if int(vieux.get("duree") or 0) != pl["duree"]:
                pl["fichier"], pl["verdict"] = "", None
        plans.append(pl)
    seq["personnages"], seq["plans"] = persos, plans
    uniformiser(seq, image)
    return seq


def uniformiser(seq, image=None):
    """Les règles que l'utilisateur n'a plus à connaître : actions doubles coupées, premier plan parti de l'image du rush,
    plans enchaînés."""
    i = 0
    while i < len(seq["plans"]) and len(seq["plans"]) < 12:
        if Q.actions_multiples(seq["plans"][i].get("action", "")) and not seq["plans"][i].get("fichier"):
            avant = len(seq["plans"])
            Q.couper_plan(seq, i)
            if len(seq["plans"]) == avant:
                i += 1
        else:
            i += 1
    for k, pl in enumerate(seq["plans"]):
        pl["enchainer"] = k > 0
        if pl.get("fin_reelle") and k < len(seq["plans"]) - 1:
            pl.pop("fin_reelle")
            pl["image_fin"], pl["clef"], pl["sans_fin"] = "", False, True
    if image and seq["plans"] and not seq["plans"][0].get("image"):
        seq["plans"][0]["image"] = image
    fin = (seq.get("raccord") or {}).get("image_fin")
    if fin and os.path.exists(fin) and seq["plans"]:     # 0.9.87 : relier deux rushes : le dernier plan arrive sur le rush suivant
        der = seq["plans"][-1]
        der.update(image_fin=fin, clef=True, sans_fin=False, fin_reelle=True)
    seq["image_auto"] = seq["image_fin_auto"] = True
    seq["voix"] = "aucune"
    seq["assistant"] = True
    return seq


def etat(seq):
    """L'état de la séquence tel qu'il est montré à l'IA pour une correction en clair."""
    return {"personnages": [{"nom": p["nom"], "genre": p.get("genre", "personne"), "sur_image": bool(p.get("sur_image")),
                             "source": p.get("source"), "boite": p.get("boite"),
                             "position": p.get("position", ""), "description": p.get("brut") or p.get("description", ""),
                             "style": p.get("style", "")} for p in seq["personnages"]],
            "lieux": [{"nom": x["nom"], "sur_image": x.get("source") == "image", "description": x.get("description", "")}
                      for x in seq.get("lieux") or []],
            "plans": [{"action": pl["action"], "personnages": pl.get("personnages") or [], "duree": pl.get("duree"),
                       "camera": pl.get("camera", ""), "lieu": pl.get("lieu", ""), "hors_champ": pl.get("hors_champ", ""),
                       "visibles_fixes": bool(pl.get("visibles_fixes"))} for pl in seq["plans"]]}


def modifier(params, seq, demande, niveau="claude", image=None):
    """« Le chauffeur plus âgé, et un plan de plus où elles saluent » : l'IA rend l'état corrigé ; renvoie (séquence, message)."""
    import json
    d = demander(params, CONSIGNE_MODIFIER.format(langue=_langue()),
                 "Etat :\n" + json.dumps(etat(seq), ensure_ascii=False) + "\n\nDemande : " + demande.strip(), [], niveau)
    r = lire_analyse(d)
    if not r["plans"]:
        raise ErreurAssistant(_("L'IA n'a pas su appliquer cette demande : dites-le autrement, ou corrigez dans le tableau."))
    nouveau = copy.deepcopy(seq)
    appliquer(nouveau, r, image)
    return nouveau, r["remarques"]


# ------------------------------------------------------------------ moteur vidéo, budget
def moteur_conseille(params):
    """Le moteur qui garde le mieux les personnages parmi ceux dont la clef est là ; sinon l'IA de ce poste."""
    from . import generateurs_video as GV
    dispo = [m["id"] for m in GV.disponibles(params)]
    for voulu in ("kling-o3-ref",):
        if voulu in dispo:
            return voulu
    return dispo[0] if dispo else "locale"


def manques(params):
    """Ce qui manque pour un bon résultat, en clair (liste vide = tout est là)."""
    from . import generateurs_video as GV
    out = []
    if not params.get("clef_gemini"):
        out.append(_("Sans clef Gemini, pas de fiches ni d'images de contrôle : les visages tiendront moins bien."))
    if not GV.clef(params, "fal"):
        out.append(_("Sans clef fal.ai, pas de moteur « Kling O3 Référence » (celui qui garde le mieux les personnages)."))
    return out


IMAGES_PAR = ("gemini", "locale", "aucune")


def images_par(seq, params):
    """Qui fait les images de préparation (0.9.86) : gemini (fidèle aux visages, 0,04 $ l'image), locale (IA de ce
    poste, gratuite, visages approximatifs, sans fiche) ou aucune (la vidéo part sans images de contrôle)."""
    voulu = seq.get("images_par") or params.get("assistant_images_par") or "gemini"
    if voulu == "gemini" and not params.get("clef_gemini"):
        voulu = "locale" if image_locale_possible(params) else "aucune"
    if voulu == "locale" and not image_locale_possible(params):
        voulu = "aucune"
    return voulu


def image_locale_possible(params):
    from . import packs_ia as P
    try:
        return bool(P.modele_actif("image", params))
    except Exception:          # noqa: BLE001
        return False


def a_preparer(seq, params):
    """(fiches à faire, images de départ à composer, images d'arrivée à composer)."""
    par = images_par(seq, params)
    if par == "aucune":
        return 0, 0, 0
    tous = list(range(len(seq["plans"])))
    fiches = len(Q.sans_planche(seq, tous)) if tous and par == "gemini" else 0
    depart = sum(1 for i in tous if not Q.depart_prevu(seq, i) and not (i > 0 and seq["plans"][i].get("enchainer", True)))
    # 0.9.87 : un plan enchaîné part de la vraie fin de la vidéo d'avant : pas d'image de départ inventée
    arrivee = sum(1 for pl in seq["plans"] if not (pl.get("image_fin") and os.path.exists(pl["image_fin"])) and not pl.get("sans_fin"))
    return fiches, depart, arrivee


def prix_plan(seq, i, moteur_video, params):
    if moteur_video in ("locale", "flow"):
        return 0.0
    from . import generateurs_video as GV
    m = GV.modele(moteur_video, params)
    return GV.prix(m, int(seq["plans"][i].get("duree") or Q.DUREE_PLAN)) if m else 0.0


def estimer(seq, moteur_video, params, niveau="claude"):
    """Budget prévu : {"images", "videos", "lectures", "reserve", "total"} pour ce qui reste à faire."""
    f, d, a = a_preparer(seq, params)
    restants = [i for i, pl in enumerate(seq["plans"]) if not (pl.get("fichier") and os.path.exists(pl["fichier"]))]
    videos = sum(prix_plan(seq, i, moteur_video, params) for i in restants)
    lectures = PRIX_LECTURE * len(restants) if niveau != "locale" else 0.0
    gemini = images_par(seq, params) == "gemini"
    images = PRIX_IMAGE * (f + d + a) if gemini else 0.0
    reserve = PRIX_IMAGE * 3 if (images or videos) and gemini else 0.0     # trois corrections d'images
    return {"images": round(images, 2), "videos": round(videos, 2), "lectures": round(lectures, 2), "reserve": round(reserve, 2),
            "total": round(images + videos + lectures + reserve, 2)}


def budget(seq):
    return seq.setdefault("budget", {"prevu": 0.0, "depense": 0.0, "lignes": []})


def prevoir(seq, montant):
    b = budget(seq)
    b["prevu"] = round(float(b.get("depense", 0.0)) + float(montant), 2)       # ce qui est déjà dépensé + ce qui reste à faire
    return b


def depenser(seq, libelle, montant):
    if montant <= 0:
        return budget(seq)
    b = budget(seq)
    b["depense"] = round(float(b.get("depense", 0.0)) + float(montant), 2)
    b["lignes"] = (b.get("lignes") or [])[-60:] + [[libelle, round(float(montant), 2)]]
    return b


def depasse(seq):
    b = budget(seq)
    if float(b.get("prevu", 0.0)) <= 0:                   # rien de prévu encore (lecture de l'idée) : pas de dépassement
        return False
    return float(b.get("depense", 0.0)) > float(b.get("prevu", 0.0)) + 0.004


def argent(x):
    return f"{float(x):.2f}".replace(".", ",") + " $"


# ------------------------------------------------------------------ préparation (fiches, images) et vérification
def _images_faites(seq):
    return (sum(1 for p in seq["personnages"] if p.get("planche") and os.path.exists(p["planche"])),
            {(i, c): pl.get(c) for i, pl in enumerate(seq["plans"]) for c in ("image", "image_fin")})


def _deux_fois(f):
    """0.9.96 : un délai dépassé (réseau lent, serveur chargé) : on réessaie une fois avant d'abandonner."""
    from . import ia
    try:
        return f()
    except ia.ErreurIA as e:
        if not (getattr(e, "delai", False) or "injoignable" in str(e) or "timed out" in str(e)):
            raise
        from .journal import ecrire
        ecrire("assistant", f"délai dépassé, nouvel essai : {e}")
        return f()


def preparer(seq, params, progression=None, arret=lambda: False):
    """Fiches des personnages et objets, puis image de départ et d'arrivée de chaque plan à fabriquer. Renvoie le nombre
    d'images composées (pour le budget)."""
    av = progression or (lambda f, t="": None)
    n_avant, images_avant = _images_faites(seq)
    tous = list(range(len(seq["plans"])))
    seq["images_par"] = images_par(seq, params)
    a_ficher = Q.sans_planche(seq, tous) if seq["images_par"] == "gemini" else []
    etapes = len(a_ficher) + len(tous)
    k = 0
    for p in a_ficher:
        if arret():
            raise InterruptedError()
        av(k / max(1, etapes), _("Fiche de « {n} »", n=p["nom"]))
        _deux_fois(lambda: Q.planche_personnage(seq, p, params))
        k += 1
    for i in tous:
        if arret():
            raise InterruptedError()
        pl = seq["plans"][i]
        k += 1
        if pl.get("fichier") and os.path.exists(pl["fichier"]):
            continue
        av((k - 1) / max(1, etapes), _("Images du plan {i}", i=i + 1))
        quoi = []
        if not Q.depart_prevu(seq, i) and not (i > 0 and pl.get("enchainer", True)):
            quoi.append("depart")
        if not (pl.get("image_fin") and os.path.exists(pl["image_fin"])) and not pl.get("sans_fin") and not pl.get("fin_reelle"):
            quoi.append("arrivee")
        if quoi:
            _deux_fois(lambda: Q.preparer_images(seq, i, params, tuple(quoi)))
    n_apres, images_apres = _images_faites(seq)
    return (n_apres - n_avant) + sum(1 for c, v in images_apres.items() if v and v != images_avant.get(c))


def images_du_film(video, dossier, prefixe):
    """Trois images du plan fabriqué : début, milieu, fin."""
    from . import moteur
    duree = float((moteur.sonder(video) or {}).get("duree") or 0.0)
    out = []
    for k, t in enumerate((0.1, duree / 2, max(0.0, duree - 0.15))):
        f = os.path.join(dossier, f"{prefixe}_v{k}.jpg")
        moteur.lancer(["-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-q:v", "3", f])
        if os.path.exists(f):
            out.append(f)
    return out


def verifier(params, seq, i, niveau="claude"):
    """L'IA relit le plan fabriqué (fiches + trois images du plan) : {"visages", "action", "probleme", "ok"} ; None si la
    vérification n'est pas possible (pas de fichier, pas d'IA)."""
    pl = seq["plans"][i]
    if not (pl.get("fichier") and os.path.exists(pl["fichier"])):
        return None
    refs = Q.references_du_plan(seq, pl)
    fiches = [im[0] for _n, im in refs][:3]
    noms = ", ".join(p["nom"] for p in seq["personnages"]
                     if not pl.get("personnages") or p["nom"] in pl["personnages"])[:200]
    vues = images_du_film(pl["fichier"], Q.dossier(seq), f"plan{i + 1:02d}")
    if len(vues) < 2:
        return None
    d = demander(params, CONSIGNE_VERIFIER.format(n=len(fiches), noms=noms or "-", action=pl.get("action", ""), langue=_langue()),
                 "Contrôle ce plan.", fiches + vues, niveau, max_jetons=600)
    d = d if isinstance(d, dict) else {}
    v = {"visages": bool(d.get("visages", True)), "action": bool(d.get("action", True)), "probleme": _texte(d.get("probleme"), 240)}
    v["ok"] = v["visages"] and v["action"]
    return v


def texte_verdict(v):
    if v is None:
        return _("non vérifié")
    if v.get("ok"):
        return _("✓ vérifié par l'IA")
    quoi = [x for x, bon in ((_("visages"), v.get("visages")), (_("action"), v.get("action"))) if not bon]
    return "⚠ " + ", ".join(quoi) + ((" : " + v["probleme"]) if v.get("probleme") else "")
