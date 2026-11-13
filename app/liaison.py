"""Plan de liaison intelligent (0.9.56) : un plan qui part de la dernière image du rush A et arrive à la première image
du rush B, pour passer d'un lieu à l'autre sans coupe sèche.

1. Les deux images sont prises au raccord (dernière image utilisée de A, première de B).
2. Mesures calculées sur ce poste (gratuites, immédiates) : lumière, couleurs, mouvement de la caméra à la fin de A et
   au début de B.
3. Propositions de passage : par règles à partir des mesures, ou par une IA qui regarde les deux images (l'IA de vision
   de ce poste, gratuite ; ou Claude / Gemini, coût affiché avant). Chaque proposition a une idée en français et une
   consigne en anglais pour le générateur vidéo.
4. Fabrication, au choix :
   - « 3d »     : transition 3D calculée sur ce poste (gratuite, immédiate) ;
   - « locale » : l'IA vidéo de ce poste part de l'image A et suit la consigne, puis rejoint l'image B par un fondu ;
   - « omni »   : Gemini Omni (votre clef, coût affiché avant) part exactement de l'image A et arrive exactement sur
                  l'image B (première et dernière images imposées, 3 à 10 s).
5. Le plan se regarde, puis se pose entre les deux rushes (la suite du film se décale d'autant, un seul Annuler).
"""
import json, os, tempfile

from .langue import _

MODELE_OMNI = "omni12-720p"     # generateurs_video : Omni 1.2 Flash 720p, repli 1.1 si la clef n'y a pas encore accès


class ErreurLiaison(Exception):
    pass


# ---------------------------------------------------------------- les deux plans et leurs images
def plans_voisins(projet, clip):
    """(A, B) : le plan donné et le plan vidéo qui le suit sur la même piste ; B est None s'il n'y en a pas."""
    from .projet import fin_clip
    cs = sorted(projet.clips_piste(clip["piste"]), key=lambda c: c["debut"])
    suivants = [c for c in cs if c["debut"] >= fin_clip(clip) - 0.05 and c["id"] != clip["id"]]
    return clip, (suivants[0] if suivants else None)


def plans_autour(projet, t, piste="video"):
    """(A, B) autour d'un instant : dans un vide, le plan d'avant et celui d'après ; sur un plan, lui et le suivant."""
    from .projet import fin_clip
    c = projet.clip_a(t, piste)
    if c:
        return plans_voisins(projet, c)
    cs = sorted(projet.clips_piste(piste), key=lambda c: c["debut"])
    avant = [c for c in cs if fin_clip(c) <= t + 1e-6]
    apres = [c for c in cs if c["debut"] >= t - 1e-6]
    return (avant[-1] if avant else None), (apres[0] if apres else None)


def images_raccord(projet, a, b, dossier, largeur=1280):
    """Dernière image utilisée de A et première de B, en PNG dans `dossier` : (chemin_a, chemin_b)."""
    from . import moteur
    os.makedirs(dossier, exist_ok=True)
    out = []
    for c, quand, nom in ((a, "fin", "image_a.png"), (b, "debut", "image_b.png")):
        m = projet.media(c["media"]) or {}
        if m.get("genre") == "image":
            import shutil
            p = os.path.join(dossier, nom)
            shutil.copy(m["chemin"], p)
            out.append(p)
            continue
        cad = float((m.get("fiche") or {}).get("cadence") or 25) or 25
        t = float(c["src_fin"]) - 1.5 / cad if quand == "fin" else float(c["src_debut"]) + 0.5 / cad
        p = os.path.join(dossier, nom)
        with open(p, "wb") as f:
            f.write(moteur.image(m["chemin"], max(0.0, t), largeur, m.get("fiche")))
        out.append(p)
    return tuple(out)


# ---------------------------------------------------------------- mesures (gratuites)
def _mouvement(projet, c, quand):
    """Direction du mouvement de la caméra à la fin (ou au début) d'un plan : (dx, dy) en part de la largeur par seconde."""
    import numpy as np
    from . import tri_rushes as TR
    m = projet.media(c["media"]) or {}
    if m.get("genre") != "video":
        return 0.0, 0.0
    d = float(c["src_fin"]) - 1.0 if quand == "fin" else float(c["src_debut"])
    d = max(0.0, d)
    imgs = TR._images_grises(m["chemin"], min(float(c["src_fin"]), d + 1.0), n_max=12, cadence=12.0, debut=d)
    if len(imgs) < 3:
        return 0.0, 0.0
    import cv2
    pas = []
    for x, y in zip(imgs, imgs[1:]):
        (dx, dy), r = cv2.phaseCorrelate(x, y)
        if r > 0.05:
            pas.append((dx / x.shape[1], dy / x.shape[1]))
    if not pas:
        return 0.0, 0.0
    v = np.median(np.array(pas), axis=0) * 12.0
    return float(v[0]), float(v[1])


def _direction(dx, dy):
    if abs(dx) < 0.03 and abs(dy) < 0.03:
        return ""
    if abs(dx) >= abs(dy):
        return "right" if dx < 0 else "left"                     # l'image glisse vers la gauche : la caméra va à droite
    return "down" if dy < 0 else "up"


def mesurer(projet, a, b, img_a, img_b):
    """Mesures du raccord : lumière (0-255), proximité des couleurs (0-1), mouvements de caméra."""
    import cv2
    ia, ib = cv2.imread(img_a), cv2.imread(img_b)
    if ia is None or ib is None:
        raise ErreurLiaison(_("Images du raccord illisibles."))
    la, lb = float(cv2.cvtColor(ia, cv2.COLOR_BGR2GRAY).mean()), float(cv2.cvtColor(ib, cv2.COLOR_BGR2GRAY).mean())
    ha = cv2.calcHist([cv2.cvtColor(ia, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
    hb = cv2.calcHist([cv2.cvtColor(ib, cv2.COLOR_BGR2HSV)], [0, 1], None, [16, 8], [0, 180, 0, 256])
    cv2.normalize(ha, ha)
    cv2.normalize(hb, hb)
    couleurs = max(0.0, float(cv2.compareHist(ha, hb, cv2.HISTCMP_CORREL)))
    ma, mb = _mouvement(projet, a, "fin"), _mouvement(projet, b, "debut")
    return {"lumiere_a": round(la), "lumiere_b": round(lb), "couleurs": round(couleurs, 2),
            "mouvement_a": _direction(*ma), "mouvement_b": _direction(*mb)}


# ---------------------------------------------------------------- propositions
def propositions_regles(mes):
    """Propositions sans IA, à partir des mesures : toujours au moins trois, de la plus douce à la plus marquée."""
    dir_a = mes.get("mouvement_a") or ""
    suite = {"right": _("la caméra continue vers la droite"), "left": _("la caméra continue vers la gauche"),
             "up": _("la caméra continue de monter"), "down": _("la caméra continue de descendre")}.get(dir_a, "")
    mvt_en = {"right": "continues panning right", "left": "continues panning left", "up": "keeps tilting up",
              "down": "keeps tilting down"}.get(dir_a, "glides slowly forward")
    out = [{"titre": _("Mouvement continu"),
            "idee": _("Le mouvement de la fin du premier rush se prolonge ({s}) et le décor se transforme peu à peu en celui du "
                      "second.", s=suite or _("la caméra avance doucement")),
            "consigne": f"Smooth cinematic transition shot. The camera {mvt_en} in one continuous move while the scenery gradually "
                        "and naturally transforms into the next location. No cuts, no text, realistic lighting.",
            "duree": 5}]
    ecart = abs(mes.get("lumiere_a", 128) - mes.get("lumiere_b", 128))
    if ecart > 50:
        sombre_vers_clair = mes.get("lumiere_b", 128) > mes.get("lumiere_a", 128)
        out.append({"titre": _("Passage par la lumière") if sombre_vers_clair else _("Passage par l'ombre"),
                    "idee": (_("La seconde image est bien plus claire : la caméra passe par une lumière vive qui emplit l'image, "
                               "puis le second lieu apparaît.") if sombre_vers_clair else
                             _("La seconde image est bien plus sombre : la caméra passe dans l'ombre, l'image s'assombrit, puis "
                               "le second lieu sort de la pénombre.")),
                    "consigne": ("Transition shot: the camera moves toward a bright light source, the frame briefly fills with soft "
                                 "light, then the next scene appears." if sombre_vers_clair else
                                 "Transition shot: the camera passes through a shadowed area, the frame briefly darkens, then the next "
                                 "scene emerges from the darkness."), "duree": 4})
    out.append({"titre": _("Envolée au-dessus"),
                "idee": _("La caméra s'élève au-dessus du premier lieu, survole, puis redescend vers le second : effet de voyage."),
                "consigne": "Transition shot: the camera rises up and away from the first place, flies smoothly above the landscape, "
                            "then descends toward the next location. Aerial, cinematic, no text.", "duree": 6})
    if mes.get("couleurs", 0) > 0.6:
        out.append({"titre": _("Fondu des formes"),
                    "idee": _("Les deux images ont des couleurs proches : les formes de la première se fondent lentement dans celles "
                              "de la seconde."),
                    "consigne": "Seamless match-cut transition: shapes and colors of the first image slowly morph into the second "
                                "image, the camera barely moving. Dreamlike but realistic.", "duree": 4})
    return out


CONSIGNE_IA = (
    "Tu es chef monteur. Voici deux images : la première est la dernière image d'un plan A, la seconde la première image "
    "du plan B qui suit. Il faut un court plan de liaison qui part exactement de A et arrive exactement sur B. "
    "Mesures : {mesures}. Réponds en JSON uniquement : {{\"a\": \"description courte de A en français\", "
    "\"b\": \"description courte de B en français\", \"propositions\": [{{\"titre\": \"2 à 4 mots en français\", "
    "\"idee\": \"une phrase en français : ce qu'on verra\", \"consigne\": \"prompt en anglais pour un générateur vidéo : "
    "décrire le chemin entre les deux images (mouvement de caméra, ce qui se transforme), pas les images elles-mêmes ; "
    "réaliste, sans texte à l'écran, sans changer l'identité des personnes\", \"duree\": nombre de secondes de 3 à 10}}]}}. "
    "Donne 3 propositions différentes, de la plus discrète à la plus spectaculaire.")


def lire_propositions(d):
    """Contrôle la réponse d'une IA : textes présents, durée bornée à 3-10 s."""
    out = []
    for p in (d.get("propositions") if isinstance(d, dict) else None) or []:
        try:
            titre, idee, consigne = str(p["titre"]).strip(), str(p["idee"]).strip(), str(p["consigne"]).strip()
        except (KeyError, TypeError):
            continue
        if titre and consigne:
            out.append({"titre": titre[:60], "idee": idee[:400], "consigne": consigne[:1200],
                        "duree": int(max(3, min(10, round(float(p.get("duree") or 5)))))})
    return out


def analyser_ia(img_a, img_b, mes, params, locale=True):
    """Descriptions et propositions par une IA qui regarde les deux images : sur ce poste (vision locale) ou cloud."""
    images = [open(img_a, "rb").read(), open(img_b, "rb").read()]
    consigne = CONSIGNE_IA.format(mesures=json.dumps(mes, ensure_ascii=False))
    if locale:
        from . import ia_locale, analyse_locale
        modele = ia_locale.modele_actif(params)
        if not modele:
            raise ErreurLiaison(_("Aucun modèle de vision sur ce poste : Edition › Préférences › IA locale."))
        d = analyse_locale.lire_json(ia_locale.generer(modele, consigne, images, json_attendu=True, params=params))
    else:
        from . import ia
        d = ia.demander(params, consigne, _("Analyse ces deux images de raccord."), images=images, json_attendu=True, max_jetons=1500)
    props = lire_propositions(d)
    if not props:
        raise ErreurLiaison(_("L'IA n'a pas fait de proposition utilisable."))
    return {"a": str((d or {}).get("a") or "")[:300], "b": str((d or {}).get("b") or "")[:300], "propositions": props}


# ---------------------------------------------------------------- fabrication
def dossier_sorties():
    from .config import dossier_donnees
    d = os.path.join(dossier_donnees(), "plans_liaison")
    os.makedirs(d, exist_ok=True)
    return d


def prix_omni(duree, params=None):
    """Prix maximal estimé en $ (Omni peut prendre jusqu'à 10 s, il est donc compté au plus haut)."""
    from . import generateurs_video as V
    return V.prix(V.modele(MODELE_OMNI, params), duree)


def texte_omni(consigne, duree):
    """Méthode de Google pour Omni 1.2 : la première et la dernière images se désignent par leur ordre et par cette phrase
    (plus de balises)."""
    return (consigne.strip().rstrip(".") + ". Use the first image as the starting frame and the second image as the final "
            f"frame. Duration about {int(max(3, min(10, duree)))} seconds.")


def omni_premiere_derniere(clef, img_a, img_b, consigne, sortie, duree=5, format_="16:9", progression=None,
                           arret=lambda: False, params=None):
    from . import fabrique, generateurs_video as V
    m = V.modele(MODELE_OMNI, params)
    duree = max(3, min(10, int(duree)))
    args = (clef, texte_omni(consigne, duree), sortie)
    try:
        return fabrique.generer_omni(*args, m["modele"], duree, format_, [img_a, img_b], m.get("resolution", "720p"),
                                     progression, arret, texte_apres=True)
    except InterruptedError:
        raise
    except Exception as e:                    # noqa: BLE001 : 1.2 pas encore ouvert à cette clef : la 1.1
        if m.get("repli") and any(x in str(e) for x in ("404", "NOT_FOUND", "not found", "not supported")):
            return fabrique.generer_omni(*args, m["repli"], duree, format_, [img_a, img_b], m.get("resolution", "720p"),
                                         progression, arret, texte_apres=True)
        raise


def fabriquer(mode, img_a, img_b, consigne, sortie, duree, params, format_="16:9", progression=None, arret=lambda: False):
    """Fabrique le plan de liaison ; renvoie le chemin du MP4."""
    import cv2
    from . import creatif, moteur
    if mode == "3d":
        a, b = cv2.imread(img_a), cv2.imread(img_b)
        return creatif.transition_3d(a, b, sortie, duree=max(1.0, min(4.0, float(duree))), params=params,
                                     progression=(lambda f: progression(f, _("Transition 3D"))) if progression else None)
    if mode == "omni":
        from . import generateurs_video as V
        clef = V.clef(params, "google")
        if not clef:
            raise ErreurLiaison(manque("omni", params))
        return omni_premiere_derniere(clef, img_a, img_b, consigne, sortie, duree, format_,
                                      progression=(lambda f: progression(f, _("Gemini Omni fabrique le plan…"))) if progression else None,
                                      arret=arret, params=params)
    if mode == "locale":
        d = tempfile.mkdtemp(prefix="philcut-liaison-")
        brut = os.path.join(d, "ia.mp4")
        secondes = max(2.0, min(5.0, float(duree)))
        creatif.video(consigne, brut, params, init=img_a, secondes=secondes,
                      progression=(lambda f, t="": progression(0.9 * f, t or _("L'IA de ce poste anime l'image A"))) if progression else None,
                      arret=arret)
        # arrivée sur l'image B : fondu de 0,8 s vers elle, puis 0,3 s d'image B fixe
        h, l = cv2.imread(img_a).shape[:2]
        moteur.lancer(["-y", "-i", brut, "-loop", "1", "-t", "1.1", "-i", img_b, "-filter_complex",
                       f"[0:v]scale={l}:{h}:force_original_aspect_ratio=decrease,pad={l}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24,format=yuv420p[a];"
                       f"[1:v]scale={l}:{h},setsar=1,fps=24,format=yuv420p[b];"
                       f"[a][b]xfade=transition=fade:duration=0.8:offset={max(0.2, secondes - 0.8):.3f}[v]",
                       "-map", "[v]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", sortie])
        if progression:
            progression(1.0, _("Terminé"))
        return sortie
    raise ErreurLiaison(mode)


def manque(mode, params):
    """Ce qui manque pour fabriquer de cette façon sur ce poste, sinon None."""
    from . import packs_ia as P
    if mode == "locale" and not P.modele_actif("video", params):
        return _("Installez un modèle vidéo : Edition › Préférences › IA locale (« Vidéo »).")
    if mode == "omni":
        from . import generateurs_video as V
        if not V.clef(params, "google"):
            return _("Clef Google (Gemini) à saisir : Préférences › IA › Connecter une IA.")
    return None


# ---------------------------------------------------------------- pose dans le film
def poser(projet, a, b, chemin, fiche=None, src=None):
    """Pose le plan de liaison juste après A ; s'il ne tient pas dans le vide avant B, toute la suite du film se décale
    d'autant (plans, marqueurs). Un seul Annuler revient en arrière. Renvoie le plan posé."""
    from . import moteur
    from .projet import fin_clip
    fiche = fiche or moteur.sonder(chemin)
    total = float(fiche.get("duree") or 0)
    s0, s1 = (max(0.0, float(src[0])), min(total, float(src[1]))) if src else (0.0, total)
    duree = s1 - s0
    if duree <= 0:
        raise ErreurLiaison(_("Plan de liaison vide."))
    projet.marquer()
    m = projet.ajouter_media(chemin, fiche)
    m["nom"] = _("Liaison — {a} → {b}", a=a.get("nom", ""), b=(b or {}).get("nom", ""))
    debut = fin_clip(a)
    vide = (float(b["debut"]) - debut) if b else duree
    decalage = max(0.0, duree - max(0.0, vide))
    if decalage > 1e-3:
        for c in projet.clips:
            if c["debut"] >= debut - 1e-6 and c is not a:
                c["debut"] = round(c["debut"] + decalage, 4)
        for mq in projet.marqueurs:
            if mq["t"] >= debut - 1e-6:
                mq["t"] = round(mq["t"] + decalage, 3)
        for el in list(projet.titres) + list(projet.goodies):        # titres et goodies de la suite suivent leurs plans
            if float(el.get("debut", 0)) >= debut - 1e-6:
                el["debut"] = round(float(el["debut"]) + decalage, 4)
                el["fin"] = round(float(el["fin"]) + decalage, 4)
    c = projet.ajouter_clip(m["id"], piste=a["piste"], debut=debut, src_debut=s0, src_fin=s1)
    c["liaison"] = {"a": a["id"], "b": (b or {}).get("id")}
    projet.modifie = True
    return c
