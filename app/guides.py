"""Guides pas à pas (0.9.52) : « Comment faire… » pour des cas concrets de montage.

Chaque guide a des étapes ; une étape peut avoir :
- « montrer » : ce que fait le bouton « Montrez-moi » — ouvrir un menu de la barre en surlignant la bonne ligne
  ({"menu": [...]}), ouvrir le menu du clic droit sur le plan sous la ligne rouge ({"clic_droit": [...]}), ou ouvrir
  un onglet du volet de droite et y chercher un mot ({"volet": "effets", "chercher": "..."}) ;
- « fait » : comment PhilCut voit que l'étape est faite (« plan_choisi », « partie_jaune », « fenetre:NomDeClasse »,
  « effet:id », « suivi ») ; sans cela, l'utilisateur coche lui-même « C'est fait ».
Un guide dit honnêtement ce qui manque encore (« etat » : ok, partiel, a_venir) et propose le détour le plus proche.
Les textes des menus sont ceux de PhilCut (traduits par _()) : le guide suit la langue choisie.
"""
import unicodedata

from .langue import _


def _norm(t):
    t = (t or "").replace("&", "").replace("…", "").replace("...", "").strip()
    return unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()


def _version(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def guides_catalogue():
    """Guides livrés par le catalogue en ligne (0.9.55), comme les Goodies : ajoutés ou corrigés sans nouvelle version.
    Textes par langue ; chemins de menus en français, traduits ici ; un guide qui demande une version plus récente de
    PhilCut est laissé de côté."""
    from . import catalogue_ligne as CL
    from .config import VERSION
    out = []
    for g in (CL.charger("guides.json").get("guides") or []):
        try:
            if _version(g.get("philcut_min", "0")) > _version(VERSION):
                continue
            etapes = []
            for e in g.get("etapes") or []:
                n = {"texte": CL.localise(e.get("texte"))}
                mo = e.get("montrer") or {}
                if mo.get("menu"):
                    n["montrer"] = {"menu": [_(x) for x in mo["menu"]]}
                elif mo.get("clic_droit"):
                    n["montrer"] = {"clic_droit": [_(x) for x in mo["clic_droit"]]}
                elif mo.get("volet"):
                    n["montrer"] = {"volet": mo["volet"], "chercher": CL.localise(mo.get("chercher", ""))}
                if e.get("fait"):
                    n["fait"] = e["fait"]
                etapes.append(n)
            if not g.get("id") or not etapes:
                continue
            out.append({"id": g["id"], "etat": g.get("etat", "ok") if g.get("etat") in ETATS else "ok",
                        "titre": CL.localise(g.get("titre")), "intro": CL.localise(g.get("intro")), "mots": g.get("mots", ""),
                        "etapes": etapes, "catalogue": True})
        except (TypeError, AttributeError, KeyError):
            continue                                       # un guide mal formé ne gêne pas les autres
    return out


def guides():
    """Les guides intégrés et ceux du catalogue (qui remplacent un guide de même id), par ordre alphabétique."""
    tous = {g["id"]: g for g in _guides_integres()}
    for g in guides_catalogue():
        tous[g["id"]] = g
    return sorted(tous.values(), key=lambda g: _norm(g["titre"]))


def _guides_integres():
    G = [
        {"id": "fond", "etat": "partiel",
         "titre": _("Changer le fond (décor, paysage) d'un rush"),
         "mots": "fond decor paysage arriere-plan detourer remplacer chroma vert",
         "intro": _("Un rush tourné devant un fond uni (vert, bleu) se détoure déjà. Un rush filmé n'importe où ne se détoure pas "
                    "encore : c'est prévu. En attendant, on peut flouter le fond."),
         "etapes": [
             {"texte": _("Rush tourné devant un fond uni : cliquez le plan dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Dans le volet Effets, cherchez « Fond vert » et glissez « Fond vert (chroma key) » sur le plan."),
              "montrer": {"volet": "effets", "chercher": _("Fond vert")}, "fait": "effet:chroma_key"},
             {"texte": _("Dans l'Inspecteur, « Nouveau décor » : choisissez l'image ou la vidéo du paysage ; réglez la couleur du "
                         "fond et la tolérance jusqu'à ce que le sujet soit net.")},
             {"texte": _("Rush filmé n'importe où : flouter le fond (le sujet reste net). Ligne rouge sur le plan, puis Fabrique IA › "
                         "Vidéo › Effet IA sur le film… › « Flou d'arrière-plan (effet portrait) » › Créer."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Effet IA sur le film (dessin animé, ralenti, agrandir, photo 3D…)…")]},
              "fait": "fenetre:DialogueAtelierIA"},
         ]},
        {"id": "suite_voix", "etat": "ok",
         "titre": _("Continuer un commentaire avec la même voix"),
         "mots": "voix commentaire continuer suite clone ma voix narration phrase dire",
         "intro": _("PhilCut fait dire une nouvelle phrase avec la voix d'un extrait de 5 à 15 secondes du film : votre voix, ou "
                    "celle d'une personne qui vous a donné son accord (case à cocher), jamais une personne connue. Tout se fait sur "
                    "ce poste, gratuitement (modèle d'environ 1,6 Go à installer une fois)."),
         "etapes": [
             {"texte": _("Placez la ligne rouge là où le commentaire doit reprendre (juste après la voix à continuer).")},
             {"texte": _("Clic droit sur le plan qui porte la voix › « Continuer avec cette voix… » (ou Montage › Son › « Continuer "
                         "avec ma voix… »)."),
              "montrer": {"clic_droit": [_("Continuer avec cette voix…")]}, "fait": "fenetre:DialogueVoixSuite"},
             {"texte": _("Ecoutez l'extrait proposé (les dernières secondes de voix avant la ligne rouge) ; déplacez-le si besoin. "
                         "Musique derrière ? Cochez « Isoler d'abord la voix ».")},
             {"texte": _("Cochez l'accord, écrivez la phrase (ex. : « Et maintenant, passons à autre chose. »), puis « Fabriquer la "
                         "voix ». Ecoutez ; refabriquez en changeant la ponctuation ou l'expressivité si besoin.")},
             {"texte": _("« Poser dans le film » : la phrase va sur la piste Voix à la ligne rouge. Après un plan de liaison, le bouton "
                         "« Une phrase avec ma voix sur ce plan… » la pose au début du plan de liaison."), "fait": "voix_ia"},
         ]},
        {"id": "couper", "etat": "ok",
         "titre": _("Couper des images dans un rush"),
         "mots": "couper coupe retirer supprimer passage morceau partie jaune enlever",
         "intro": _("Couper un plan en deux, ou retirer un passage : la suite se recolle toute seule."),
         "etapes": [
             {"texte": _("Placez la ligne rouge au début du passage à retirer (clic sur la règle des temps).")},
             {"texte": _("Clic droit sur le plan › « Couper ici » coupe le plan en deux à la ligne rouge."),
              "montrer": {"clic_droit": [_("Couper ici")]}},
             {"texte": _("Pour retirer tout un passage : posez la partie jaune (fanions [ et ] sur la règle, ou Montage › Pistes et "
                         "passage choisi › « Partie jaune : la faire commencer à la ligne rouge », puis « … finir à la ligne "
                         "rouge »)."),
              "montrer": {"menu": [_("Montage"), _("Pistes et passage choisi (partie jaune)"),
                                   _("Partie jaune : la faire commencer à la ligne rouge")]},
              "fait": "partie_jaune"},
             {"texte": _("Montage › Pistes et passage choisi › « Partie jaune : supprimer ce passage »."),
              "montrer": {"menu": [_("Montage"), _("Pistes et passage choisi (partie jaune)"), _("Partie jaune : supprimer ce passage")]}},
             {"texte": _("Un vide est resté entre deux plans ? Clic droit dans le vide › « Refermer ce vide : recoller les plans ».")},
         ]},
        {"id": "personnages", "etat": "partiel",
         "titre": _("Faire jouer et parler des personnages d'un rush"),
         "mots": "personnage personne jouer parler replique dialogue visage acteur histoire sequence",
         "intro": _("Seulement des personnes qui ont donné leur accord : vous le certifiez en cochant une case. « A la manière de » "
                    "décrit un style, jamais le visage ou la voix d'une personne connue. Garder le même visage d'un plan à "
                    "l'autre passe aujourd'hui par Gemini (coût affiché avant) ; l'IA de ce poste part de l'image du personnage "
                    "mais ne garde pas aussi bien le visage."),
         "etapes": [
             {"texte": _("Ligne rouge sur un moment où le personnage est bien visible, puis clic droit sur le plan › « Enregistrer "
                         "l'image à cet endroit… »."),
              "montrer": {"clic_droit": [_("Enregistrer l'image à cet endroit…")]}},
             {"texte": _("Fabrique IA › Vidéo › « Histoire en plusieurs plans (Séquence IA)… » : écrivez la petite scène (ce qu'ils "
                         "font, ce qu'ils disent)."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Histoire en plusieurs plans (Séquence IA)…")]},
              "fait": "fenetre:DialogueSequence"},
             {"texte": _("Onglet des personnages : cliquez la ligne du personnage › « Images du personnage… » › l'image enregistrée "
                         "(cochez l'accord de la personne).")},
             {"texte": _("Vérifiez chaque plan et ses répliques, choisissez le moteur (ce poste, Gemini, Flow), puis fabriquez : "
                         "chaque plan se regarde avant d'être posé.")},
         ]},
        {"id": "liaison", "etat": "ok",
         "titre": _("Lier deux rushes par un plan de passage"),
         "mots": "liaison lier raccord passage transition entre deux rushes plans enchainer vide trou",
         "intro": _("Un plan de liaison part de la dernière image du premier rush et arrive à la première image du suivant. "
                    "PhilCut mesure les deux images et propose des passages ; une IA peut aussi les regarder pour proposer mieux. "
                    "Trois façons de fabriquer : transition 3D (gratuite), IA de ce poste (gratuite), Gemini Omni (prix annoncé)."),
         "etapes": [
             {"texte": _("Cliquez le premier des deux plans dans la timeline (ou faites un clic droit dans le vide entre eux : "
                         "« Remplir ce vide par un plan de liaison… »)."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur ce plan › « Plan de liaison avec le plan suivant… ». La fenêtre montre les deux images "
                         "du raccord et des propositions."),
              "montrer": {"clic_droit": [_("Plan de liaison avec le plan suivant…")]}, "fait": "fenetre:DialogueLiaison"},
             {"texte": _("Ou par le menu : Montage › Pistes et passage choisi › « Plan de liaison entre deux plans… » (la ligne "
                         "rouge sur le premier plan)."),
              "montrer": {"menu": [_("Montage"), _("Pistes et passage choisi (partie jaune)"), _("Plan de liaison entre deux plans…")]},
              "fait": "fenetre:DialogueLiaison"},
             {"texte": _("Choisissez une proposition, ou « Analyser avec l'IA de ce poste » pour des idées qui tiennent compte de ce "
                         "que montrent les images. La consigne reste modifiable.")},
             {"texte": _("Choisissez comment fabriquer, cochez l'accord des personnes visibles si c'est une IA, puis « Fabriquer le "
                         "plan ». Regardez le résultat ; refabriquez si besoin.")},
             {"texte": _("« Poser entre les deux plans » : la suite du film se décale d'autant. Edition › Annuler revient en arrière."),
              "fait": "liaison"},
         ]},
        {"id": "musique_maniere", "etat": "ok",
         "titre": _("Créer une musique à la manière de… (style, voix, passage d'un morceau)"),
         "mots": "musique maniere style comme metal compositeur groupe chanteur voix chanter inspirer passage refrain morceau decrire",
         "intro": _("La Fabrique musique crée sur ce poste, gratuitement. « À la manière de » décrit un style ou une manière de "
                    "chanter, jamais un nom ni une voix copiée ; la liste s'enrichit en ligne. On peut aussi s'inspirer d'un passage "
                    "d'un morceau, ou décrire la voix d'une chanson."),
         "etapes": [
             {"texte": _("Fabrique IA › Musique › « Créer une musique par IA (Fabrique musique)… »."),
              "montrer": {"menu": [_("Fabrique IA"), _("Musique"), _("Créer une musique par IA (Fabrique musique)…")]},
              "fait": "fenetre:DialogueFabriqueMusique"},
             {"texte": _("Ligne Phrase › « Style « à la manière de »… » : choisissez une famille ou tapez (« metal », « Einaudi »…), "
                         "double-cliquez un nom. Absent de la liste ? « Utiliser », puis « Améliorer avec l'IA ».")},
             {"texte": _("Ligne Voix › « À la manière de… » : une manière de chanter connue, ou « Décrire la voix d'un morceau » : "
                         "choisissez le passage où la voix chante, PhilCut l'isole de la musique et la décrit (registre, vibrato, "
                         "timbre).")},
             {"texte": _("« S'inspirer d'un morceau » › Choisir un morceau : un fichier, ou en ligne (« S'inspirer de ce morceau » "
                         "télécharge tout seul ; « Plus de résultats » si besoin). Gardez tout le morceau ou seulement un passage.")},
             {"texte": _("Relisez la consigne anglaise en bas, puis « Créer la musique ».")},
         ]},
        {"id": "voix_musique", "etat": "ok",
         "titre": _("Retirer la voix d'une musique (garder la musique)"),
         "mots": "retirer enlever voix chant musique instrumental karaoke separer bruit vent ambiance isoler",
         "intro": _("PhilCut sépare le son en voix, musique et bruits de fond, sur ce poste. Les trois pistes ensemble redonnent le "
                    "son d'origine : on garde ce qu'on veut. Il faut une fois le modèle « Séparer voix, musique et bruits » "
                    "(Préférences › IA locale, environ 170 Mo)."),
         "etapes": [
             {"texte": _("Cliquez le plan (ou la musique) dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur le plan › « Séparer voix, musique et bruits… »."),
              "montrer": {"clic_droit": [_("Séparer voix, musique et bruits…")]}, "fait": "fenetre:DialogueSeparation"},
             {"texte": _("« Retirer la voix » (ou « Garder la voix seule », ou « Les trois pistes »), puis « Séparer » : la progression "
                         "s'affiche. Ecoutez chaque piste.")},
             {"texte": _("« Poser dans le film » : les pistes se posent sous le plan, le son d'origine est coupé. Edition › Annuler "
                         "pour revenir."), "fait": "separe"},
             {"texte": _("Pour un fichier qui n'est pas dans le film : Fabrique IA › Musique › « Séparer voix, musique et bruits… »."),
              "montrer": {"menu": [_("Fabrique IA"), _("Musique"), _("Séparer voix, musique et bruits…")]}},
         ]},
        {"id": "suivi", "etat": "ok",
         "titre": _("Suivre une personne et recadrer"),
         "mots": "suivre suivi personne recadrer recadrage cadrage vertical short reel 9:16",
         "intro": _("Le cadre suit la personne tout seul ; utile surtout pour un film vertical (Shorts, Reels)."),
         "etapes": [
             {"texte": _("Cliquez le plan dans la timeline."), "fait": "plan_choisi"},
             {"texte": _("Clic droit sur le plan › Cadrage › « Suivre la personne (recadrage automatique)… »."),
              "montrer": {"clic_droit": [_("Cadrage"), _("Suivre la personne (recadrage automatique)…")]}, "fait": "suivi"},
             {"texte": _("Le suivi se trompe à un moment ? Ligne rouge à cet instant, clic droit sur le plan › Cadrage › « Corriger "
                         "le suivi à la ligne rouge… », retracez la zone : la suite est refaite."),
              "montrer": {"clic_droit": [_("Cadrage"), _("Corriger le suivi à la ligne rouge…")]}},
         ]},
        {"id": "projets_cloud", "etat": "ok",
         "titre": _("Retrouver mes projets et mes rushes sur un autre PC (cloud)"),
         "mots": "cloud pcloud drive nas projet autre pc poste ordinateur ouvrir enregistrer retrouver rushes original copie",
         "intro": _("Chaque compte a son rôle : un pour les réglages, un pour déposer et retrouver les projets, un pour les rushes "
                    "(gros fichiers). Un projet ouvert depuis un compte y retourne à chaque Enregistrer ; sur un autre PC, chaque rush "
                    "absent se télécharge au choix en copie légère ou en original."),
         "etapes": [
             {"texte": _("Edition › Préférences › Comptes et synchro : ajoutez vos comptes (pCloud, Google Drive, NAS…), puis, dans "
                         "« Rôle de chaque compte », choisissez le compte des projets et celui des rushes."),
              "montrer": {"menu": [_("&Edition"), _("Préférences…")]}},
             {"texte": _("Projet ouvert : Fichier › « Enregistrer le projet vers un emplacement (cloud, NAS)… ». Ensuite, chaque "
                         "Enregistrer le renvoie là-bas (☁ devant son nom)."),
              "montrer": {"menu": [_("&Fichier"), _("Enregistrer le projet vers un emplacement (cloud, NAS)…")]}},
             {"texte": _("Pour l'autre PC : après l'enregistrement, cochez « Les originaux » (ou la copie légère) des rushes à "
                         "déposer.")},
             {"texte": _("Sur l'autre PC : Fichier › « Ouvrir un projet depuis un emplacement (cloud, NAS)… », ou double-clic sur le "
                         "projet dans l'Accueil (☁)."),
              "montrer": {"menu": [_("&Fichier"), _("Ouvrir un projet depuis un emplacement (cloud, NAS)…")]}},
             {"texte": _("Rushes absents : Fichier › « Médias introuvables sur ce poste… » : « Télécharger la copie légère » ou "
                         "« Télécharger l'original », rush par rush."),
              "montrer": {"menu": [_("&Fichier"), _("Médias introuvables sur ce poste…")]}},
         ]},
        {"id": "derniere_image", "etat": "ok",
         "titre": _("Passer d'un rush à l'autre par la dernière image ou une animation"),
         "mots": "derniere image figer arret sur image animer animation photo 3d transition fin",
         "intro": _("Arrêt sur la dernière image, image qui s'anime, ou transition classique entre les deux plans."),
         "etapes": [
             {"texte": _("Placez la ligne rouge sur la dernière image du premier rush.")},
             {"texte": _("Arrêt sur image : clic droit sur le plan › « Figer l'image à cet endroit (cadre photo, légende)… »."),
              "montrer": {"clic_droit": [_("Figer l'image à cet endroit (cadre photo, légende)…")]}},
             {"texte": _("Ou l'animer : Fabrique IA › Vidéo › Effet IA sur le film… › « Animer l'image » ou « Photo 3D à partir de "
                         "l'image (3 s) » › Créer, regarder, Poser."),
              "montrer": {"menu": [_("Fabrique IA"), _("Vidéo"), _("Effet IA sur le film (dessin animé, ralenti, agrandir, photo 3D…)…")]},
              "fait": "fenetre:DialogueAtelierIA"},
             {"texte": _("Ou une transition : volet Effets, cherchez « transition », glissez-la sur le début du plan qui arrive. "
                         "Montage › Montage automatique › « Transitions automatiques… » en pose une à chaque coupe."),
              "montrer": {"volet": "effets", "chercher": _("transition")}},
         ]},
    ]
    return G


ETATS = {"ok": ("✓", "#3fb950"), "partiel": ("◐", "#e3b341"), "a_venir": ("…", "#8a94a6")}


def libelle_etat(etat):
    return {"ok": _("Faisable aujourd'hui"), "partiel": _("En partie (avec un détour)"), "a_venir": _("Pas encore : prévu")}.get(etat, "")


def chercher(phrase):
    """Les guides qui répondent à une question (« comment retirer la voix »), du plus proche au moins proche."""
    mots = [m for m in _norm(phrase).replace("'", " ").split() if len(m) > 3 and m not in
            ("comment", "faire", "pour", "dans", "avec", "veux", "voudrais", "faut", "est-ce", "quoi", "rush", "rushes")]
    res = []
    for g in guides():
        cible = _norm(g["titre"] + " " + g.get("mots", ""))
        score = sum(1 for m in mots if m in cible or (len(m) > 5 and m[:5] in cible))
        if score:
            res.append((score, g))
    return [g for _s, g in sorted(res, key=lambda x: -x[0])]


# ---------------------------------------------------------------- « Montrez-moi »
def _trouver(actions, texte):
    n = _norm(texte)
    for a in actions:
        if a.isSeparator():
            continue
        t = _norm(a.text())
        if t == n or (n and t.startswith(n)) or (t and n.startswith(t) and len(t) > 6):
            return a
    return None


def surligner(menu, chemin, delai=180):
    """Dans un menu ouvert : surligne la ligne voulue, en ouvrant les sous-menus du chemin un par un."""
    from PySide6.QtCore import QTimer
    if not chemin or menu is None:
        return
    a = _trouver(menu.actions(), chemin[0])
    if a is None:
        return
    menu.setActiveAction(a)
    if a.menu() is not None and len(chemin) > 1:
        sous = a.menu()
        r = menu.actionGeometry(a)
        sous.popup(menu.mapToGlobal(r.topRight()))
        QTimer.singleShot(delai, lambda: surligner(sous, chemin[1:], delai))


def montrer_menu(fenetre, chemin):
    """Ouvre le menu de la barre (Montage, Fabrique IA…) et surligne la ligne du chemin. Renvoie False si introuvable."""
    from PySide6.QtCore import QTimer
    mb = fenetre.menuBar()
    top = _trouver(mb.actions(), chemin[0]) if chemin else None
    if top is None or top.menu() is None:
        return False
    mb.setActiveAction(top)
    QTimer.singleShot(200, lambda: surligner(top.menu(), chemin[1:]))
    return True


def clip_a_montrer(ed):
    """Le plan vidéo sous la ligne rouge (sinon celui choisi, sinon le premier)."""
    p = ed.projet
    c = p.clip_a(ed.timeline.position, "video") or ed._clip_selectionne()
    if not c:
        vs = sorted(p.clips_piste("video"), key=lambda x: x["debut"])
        c = vs[0] if vs else None
    return c


def montrer_clic_droit(ed, chemin):
    """Ouvre le menu du clic droit sur le plan sous la ligne rouge, ligne du chemin surlignée."""
    c = clip_a_montrer(ed)
    if not c:
        return False
    tl = ed.timeline
    tl.selectionner(c["id"])
    it = tl.items_clips.get(c["id"])
    if it is None:
        return False
    from PySide6.QtCore import QPointF
    r = it.sceneBoundingRect()
    x = min(max(r.left() + 20, tl.mapToScene(0, 0).x() + 20), r.right() - 10)
    pos = tl.viewport().mapToGlobal(tl.mapFromScene(QPointF(x, r.center().y())))
    tl.surligner_menu = list(chemin)
    t = tl.position if c["debut"] <= tl.position <= c["debut"] + 1e9 else c["debut"]
    tl.menu_clip(c, pos, t)
    return True


def montrer_volet(ed, onglet, chercher=""):
    noms = {"effets": ed.catalogue, "inspecteur": ed.inspecteur}
    w = noms.get(onglet)
    if w is None:
        return False
    i = ed.volet.indexOf(w)
    if i < 0:
        return False
    ed._ouvrir_volet(i)
    if chercher and hasattr(w, "recherche"):
        w.recherche.setText(chercher)
        w.recherche.setFocus()
    return True


def montrer(fenetre, ed, m):
    if not m:
        return False
    if "menu" in m:
        return montrer_menu(fenetre, m["menu"])
    if "clic_droit" in m and ed is not None:
        return montrer_clic_droit(ed, m["clic_droit"])
    if "volet" in m and ed is not None:
        return montrer_volet(ed, m["volet"], m.get("chercher", ""))
    return False


# ---------------------------------------------------------------- étapes faites
def est_fait(cond, ed):
    """PhilCut voit-il que l'étape est faite ?"""
    if not cond or ed is None:
        return False
    try:
        if cond == "plan_choisi":
            return ed._clip_selectionne() is not None
        if cond == "partie_jaune":
            return bool(ed.timeline.zone_valide())
        if cond == "separe":
            return any(c.get("separe_de") for c in ed.projet.clips)
        if cond == "voix_ia":
            return any(c.get("voix_ia") for c in ed.projet.clips)
        if cond == "liaison":
            return any(c.get("liaison") for c in ed.projet.clips)
        if cond == "suivi":
            return any(c.get("ajustement") == "suivi" for c in ed.projet.clips_piste("video"))
        if cond.startswith("effet:"):
            eid = cond.split(":", 1)[1]
            return any(any(e.get("id") == eid for e in (c.get("effets") or [])) for c in ed.projet.clips)
        if cond.startswith("fenetre:"):
            from PySide6.QtWidgets import QApplication
            nom = cond.split(":", 1)[1]
            return any(w.isVisible() and type(w).__name__ == nom for w in QApplication.topLevelWidgets())
    except (RuntimeError, AttributeError, TypeError):
        return False
    return False
