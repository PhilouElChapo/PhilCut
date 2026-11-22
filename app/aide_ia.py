"""Aide par discussion (1.1.12) : « Comment faire… » en parlant, comme avec un formateur qui connaît PhilCut.

Demande de Philippe (22/11 01h03) : « Claude en général ne connaît pas PhilCut… il faut trouver une astuce ». L'astuce : à
chaque question, PhilCut donne lui-même à l'IA son propre manuel, tiré de l'écran tel qu'il est :
- les menus réels de la fenêtre (barre de menus, et clic droit sur un plan vidéo et sur un son), dans la langue choisie ;
- les guides pas à pas (intégrés et ceux du catalogue en ligne) ;
- les fiches d'aide du catalogue (catalogue/aide.json, mises à jour en ligne sans nouvelle version) ;
- l'état du montage (plan choisi, ligne rouge, partie jaune, fenêtres ouvertes, IA disponibles — jamais une clef) ;
- sur clic, une capture de PhilCut.
L'IA répond en JSON : texte, étapes avec ce qu'il faut montrer, et au plus une action « Le faire pour moi ». Tout chemin de
menu cité est vérifié dans les vrais menus : un chemin inventé n'est jamais montré ni fait.
"""
import json
import os
import re
import tempfile
import unicodedata

from .langue import _

PLAN_VIDEO, PLAN_SON = "plan_video", "plan_son"
MAX_MANUEL_LOCAL = 14000            # l'IA de ce poste lit moins : seulement les morceaux du manuel les plus proches
MAX_HISTORIQUE = 8                  # échanges gardés dans la discussion envoyée


def _norm(t):
    t = (t or "").replace("&", "").replace("…", "").replace("...", "").strip()
    return unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower()


def _texte_action(a):
    return re.sub(r"\s+", " ", (a.text() or "").replace("&&", "\0").replace("&", "").replace("\0", "&")).strip()


# ------------------------------------------------------------------ les menus réels
def parcourir_menu(menu, chemin=(), profondeur=0):
    """[(chemin, info-bulle)] de toutes les lignes d'un QMenu (sous-menus compris)."""
    out = []
    if menu is None or profondeur > 6:
        return out
    try:
        menu.aboutToShow.emit()                 # certains sous-menus (récents, Fabrique) se remplissent à l'ouverture
    except (RuntimeError, AttributeError):
        pass
    for a in menu.actions():
        if a.isSeparator() or not a.isVisible():
            continue
        t = _texte_action(a)
        if not t:
            continue
        c = tuple(chemin) + (t,)
        if a.menu() is not None:
            out += parcourir_menu(a.menu(), c, profondeur + 1)
        else:
            bulle = (a.toolTip() or a.statusTip() or "").strip()
            out.append((c, "" if _norm(bulle) == _norm(t) else bulle))
    return out


def menus_barre(fenetre):
    out = []
    for a in fenetre.menuBar().actions():
        if a.menu() is not None:
            out += parcourir_menu(a.menu(), (_texte_action(a),))
    return out


def menus_clic_droit(ed):
    """{PLAN_VIDEO: [...], PLAN_SON: [...]} : le menu du clic droit, construit pour de vrai sur un plan du projet (sans l'ouvrir)."""
    out = {}
    if ed is None or getattr(ed, "projet", None) is None:
        return out
    for cle, genre in ((PLAN_VIDEO, "video"), (PLAN_SON, "son")):
        c = _un_plan(ed, genre)
        if c is None:
            continue
        m = construire_menu_clip(ed, c)
        if m is not None:
            out[cle] = parcourir_menu(m)
    return out


def _un_plan(ed, genre):
    """Le plan à prendre pour le clic droit : celui choisi s'il est du bon genre, sinon celui sous la ligne rouge, sinon le premier."""
    p = ed.projet
    try:
        sel = ed._clip_selectionne()
    except Exception:
        sel = None
    if sel and _genre_piste(sel) == genre:
        return sel
    if genre == "video":
        c = p.clip_a(ed.timeline.position, "video")
        if c:
            return c
    pistes = p.pistes_video() if genre == "video" else p.pistes_audio() + ["voix"]
    for piste in pistes:
        cs = p.clips_piste(piste)
        if cs:
            return cs[0]
    return None


def _genre_piste(clip):
    return "video" if str(clip.get("piste", "")).startswith("video") else "son"


def construire_menu_clip(ed, clip):
    """Le QMenu du clic droit de ce plan, construit par la timeline mais pas ouvert (rien n'est fait)."""
    tl = ed.timeline
    pris = []
    tl._capture_menu = pris
    try:
        tl.menu_clip(clip, None)
    except Exception:
        return None
    finally:
        tl._capture_menu = None
    return pris[0] if pris else None


# ------------------------------------------------------------------ retrouver une ligne, la montrer, la faire
def _trouver(actions, texte):
    n = _norm(texte)
    for a in actions:
        if a.isSeparator() or not a.isVisible():
            continue
        if _norm(_texte_action(a)) == n:
            return a
    for a in actions:                        # l'IA a un peu abrégé : début de ligne, assez long pour ne pas se tromper
        if a.isSeparator() or not a.isVisible():
            continue
        t = _norm(_texte_action(a))
        if len(n) > 6 and (t.startswith(n) or n.startswith(t) and len(t) > 6):
            return a
    return None


def action_du_chemin(menu_ou_barre, chemin):
    actions = menu_ou_barre.actions()
    a = None
    for k, bout in enumerate(chemin):
        a = _trouver(actions, bout)
        if a is None:
            return None
        if k < len(chemin) - 1:
            if a.menu() is None:
                return None
            try:
                a.menu().aboutToShow.emit()
            except (RuntimeError, AttributeError):
                pass
            actions = a.menu().actions()
    return a


def chemin_valide(fenetre, ed, m):
    """La forme { "menu": [...] } ou { "clic_droit": [...], "plan": "video"|"son" } existe-t-elle vraiment ?"""
    if not isinstance(m, dict):
        return False
    if isinstance(m.get("menu"), list) and m["menu"]:
        a = action_du_chemin(fenetre.menuBar(), m["menu"])
        return a is not None and a.menu() is None
    if isinstance(m.get("clic_droit"), list) and m["clic_droit"] and ed is not None:
        c = _un_plan(ed, "son" if m.get("plan") == "son" else "video")
        menu = construire_menu_clip(ed, c) if c else None
        a = action_du_chemin(menu, m["clic_droit"]) if menu is not None else None
        return a is not None and a.menu() is None
    return False


def montrer(fenetre, ed, m):
    """Ouvre le menu et surligne la ligne (comme « Montrez-moi » des guides)."""
    from . import guides as G
    if m.get("menu"):
        return G.montrer_menu(fenetre, m["menu"])
    if m.get("clic_droit") and ed is not None:
        c = _un_plan(ed, "son" if m.get("plan") == "son" else "video")
        if c is None:
            return False
        return _montrer_clic(ed, c, m["clic_droit"])
    return False


def _montrer_clic(ed, c, chemin):
    from . import guides as G
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
    tl.menu_clip(c, pos)
    return True


def faire(fenetre, ed, m):
    """« Le faire pour moi » : la ligne du menu est déclenchée comme par un clic (la fenêtre de l'outil s'ouvre, rien de payant
    ne part sans les confirmations habituelles). Renvoie True si la ligne a été trouvée."""
    if m.get("menu"):
        a = action_du_chemin(fenetre.menuBar(), m["menu"])
    elif m.get("clic_droit") and ed is not None:
        c = _un_plan(ed, "son" if m.get("plan") == "son" else "video")
        if c is None:
            return False
        ed.timeline.selectionner(c["id"])
        menu = construire_menu_clip(ed, c)
        a = action_du_chemin(menu, m["clic_droit"]) if menu is not None else None
        if a is not None and a.menu() is None:
            a.trigger()
            menu.deleteLater()
            return True
        return False
    else:
        return False
    if a is None or a.menu() is not None:
        return False
    a.trigger()
    return True


# ------------------------------------------------------------------ l'état de l'écran
def etat(fenetre, ed, params):
    """Ce que voit l'utilisateur, en texte (jamais une clef ni un mot de passe)."""
    from .config import VERSION
    from . import langue
    lignes = [f"PhilCut {VERSION}, langue {langue.LANGUE or 'fr'}."]
    try:
        from PySide6.QtWidgets import QApplication
        fen = [w.windowTitle() for w in QApplication.topLevelWidgets()
               if w.isVisible() and w.windowTitle() and w is not fenetre and not w.inherits("QMenu")]
        if fen:
            lignes.append("Fenêtres ouvertes : " + " ; ".join(sorted(set(fen))[:8]) + ".")
    except Exception:
        pass
    if ed is None or getattr(ed, "projet", None) is None:
        lignes.append("Aucun projet ouvert (Accueil).")
    else:
        p = ed.projet
        try:
            nb = {"video": sum(len(p.clips_piste(x)) for x in p.pistes_video()),
                  "son": sum(len(p.clips_piste(x)) for x in p.pistes_audio() + ["voix"])}
            lignes.append(f"Projet « {p.d.get('nom') or os.path.basename(getattr(p, 'chemin', '') or '') or 'sans nom'} », "
                          f"format {p.d.get('format', '?')}, {nb.get('video', 0)} plan(s) vidéo, {nb.get('son', 0)} son(s), "
                          f"durée {p.duree():.1f} s, {len(p.d.get('medias', []))} média(s).")
        except Exception:
            pass
        try:
            lignes.append(f"Ligne rouge à {ed.timeline.position:.2f} s.")
            z = getattr(ed.timeline, "zone", None)
            if z:
                lignes.append(f"Partie jaune de {z[0]:.2f} à {z[1]:.2f} s.")
        except Exception:
            pass
        try:
            c = ed._clip_selectionne()
        except Exception:
            c = None
        if c:
            med = p.media(c.get("media")) if c.get("media") else None
            from .projet import duree_clip
            bouts = [f"Plan choisi : piste {c.get('piste')}, de {c['debut']:.2f} s, durée {duree_clip(c):.2f} s"]
            if med:
                bouts.append(f"média « {os.path.basename(med.get('chemin') or '')} » ({med.get('genre', '?')})")
            if c.get("effets"):
                bouts.append("effets : " + ", ".join(e.get("id", "?") for e in c["effets"][:6]))
            try:
                from .creations import lire as recette
                if med and recette(med.get("chemin") or ""):
                    bouts.append("création IA (recette gardée)")
            except Exception:
                pass
            lignes.append(", ".join(bouts) + ".")
        else:
            lignes.append("Aucun plan choisi.")
    try:
        from . import ia
        clefs = sorted({m for m, _k in ia.moteurs(dict(params, ia_moteur="deux"))})
        lignes.append("IA cloud avec clef : " + (", ".join(clefs) if clefs else "aucune") + ".")
        from . import generateurs_video as GV
        vids = [m["nom"] for m in GV.disponibles(params)][:6]
        if vids:
            lignes.append("Moteurs vidéo disponibles : " + ", ".join(vids) + ".")
    except Exception:
        pass
    try:
        from . import ia_locale
        lignes.append("IA locale : " + ("installée" if ia_locale.modele_actif(params) else "non installée") + ".")
    except Exception:
        pass
    return "\n".join(lignes)


def capture(fenetre):
    """Capture de PhilCut (fenêtre principale, et la fenêtre de travail au premier plan) : chemins de PNG."""
    from PySide6.QtWidgets import QApplication
    out = []
    vus = []
    actives = [QApplication.activeWindow(), fenetre]
    for w in actives:
        if w is None or w in vus or not w.isVisible() or w.inherits("DialogueAideIA"):
            continue
        vus.append(w)
        pm = w.grab()
        if pm.isNull():
            continue
        if pm.width() > 1600:
            from PySide6.QtCore import Qt
            pm = pm.scaledToWidth(1600, Qt.SmoothTransformation)
        ch = os.path.join(tempfile.gettempdir(), f"philcut_aide_{os.getpid()}_{len(out)}.png")
        pm.save(ch, "PNG")
        out.append(ch)
    return out[:2]


# ------------------------------------------------------------------ le manuel
def fiches_catalogue():
    """Fiches d'aide du catalogue en ligne (catalogue/aide.json) : textes par langue."""
    from . import catalogue_ligne as CL
    out = []
    for f in (CL.charger("aide.json").get("fiches") or []):
        try:
            out.append({"id": f["id"], "titre": CL.localise(f.get("titre")), "texte": CL.localise(f.get("texte")),
                        "mots": f.get("mots", "")})
        except (KeyError, TypeError, AttributeError):
            continue
    return out


def _guides_texte():
    from . import guides as G
    out = []
    for g in G.guides():
        lignes = [f"## Guide : {g['titre']} [{G.libelle_etat(g.get('etat', 'ok'))}]"]
        if g.get("intro"):
            lignes.append(g["intro"])
        for k, e in enumerate(g.get("etapes") or [], 1):
            mo = e.get("montrer") or {}
            ou = (" (menu : " + " › ".join(mo["menu"]) + ")") if mo.get("menu") else \
                 (" (clic droit sur le plan : " + " › ".join(mo["clic_droit"]) + ")") if mo.get("clic_droit") else \
                 (f" (volet {mo['volet']}, chercher « {mo.get('chercher', '')} »)" if mo.get("volet") else "")
            lignes.append(f"{k}. {e.get('texte', '')}{ou}")
        out.append(("\n".join(lignes), g["titre"] + " " + g.get("mots", "")))
    return out


def _menus_texte(barre, clic):
    def bloc(titre, liste, prefixe=""):
        lignes = [titre]
        for c, bulle in liste:
            lignes.append("- " + prefixe + " › ".join(c) + (f" — {bulle}" if bulle else ""))
        return "\n".join(lignes)
    out = [bloc("## Menus de la barre (chemins exacts)", barre)]
    if clic.get(PLAN_VIDEO):
        out.append(bloc("## Clic droit sur un plan vidéo de la timeline (chemins exacts, \"plan\": \"video\")", clic[PLAN_VIDEO]))
    if clic.get(PLAN_SON):
        out.append(bloc("## Clic droit sur un son de la timeline (chemins exacts, \"plan\": \"son\")", clic[PLAN_SON]))
    return "\n\n".join(out)


def manuel(fenetre, ed):
    """Les morceaux du manuel : [(texte, mots pour la recherche)] ; les menus d'abord (toujours envoyés)."""
    menus = _menus_texte(menus_barre(fenetre), menus_clic_droit(ed))
    fiches = [(f"## Fiche : {f['titre']}\n{f['texte']}", f["titre"] + " " + f["mots"]) for f in fiches_catalogue()]
    return menus, fiches + _guides_texte()


def choisir(question, morceaux, budget):
    """Les morceaux du manuel les plus proches de la question, dans la limite de `budget` caractères."""
    mots = {m for m in re.findall(r"[a-z0-9]{4,}", _norm(question))} - {"comment", "faire", "pour", "dans", "avec", "veux",
                                                                         "voudrais", "faut", "quoi", "est-ce", "philcut"}
    notes = []
    for i, (t, cles) in enumerate(morceaux):
        cible = _norm(t + " " + cles)
        note = sum(2 if m in _norm(cles) else 1 for m in mots if m in cible or (len(m) > 5 and m[:5] in cible))
        notes.append((-note, i))
    out, total = [], 0
    for note, i in sorted(notes):
        t = morceaux[i][0]
        if total + len(t) > budget:
            continue
        out.append(t)
        total += len(t)
    return out


CONSIGNE = """Tu es l'aide intégrée de PhilCut, un logiciel de montage vidéo (Windows, Linux) avec des outils d'IA. Tu guides
l'utilisateur comme un formateur patient : réponse courte, concrète, dans la langue de sa question, étapes numérotées.

Règles :
- Tu ne connais PhilCut QUE par le manuel ci-dessous (menus réels, guides, fiches) et l'état de l'écran. N'invente jamais
  un menu, un bouton ou une fonction. Si PhilCut ne sait pas le faire, dis-le franchement et propose le détour le plus proche
  (champ "manque").
- Les chemins de menu que tu cites dans "montrer" et "faire" doivent être recopiés EXACTEMENT depuis les listes « chemins
  exacts » (chaque élément du chemin est une ligne du menu, sans « › »). Pour le clic droit, précise "plan": "video" ou "son".
- Dans le texte, écris les chemins avec « › » (ex. « Fabrique IA › Vidéo › … »).
- Tiens compte de l'état de l'écran (plan choisi, fenêtres ouvertes, IA disponibles) et de la capture s'il y en a une : si
  l'utilisateur est déjà dans la bonne fenêtre, explique ce qu'il voit.
- Ce qui est payant : dis-le avec un ordre de prix si le manuel le donne ; PhilCut demande toujours avant de payer.
- "faire" : au plus UNE action, la première à faire (ouvrir le bon outil), seulement si elle est sûre ; sinon null.
- "dites_le" : si la demande est une action simple de montage (musique, volume, fondu, couper, texte, transition, effet,
  vitesse), une phrase courte à passer à « Dites-le en clair » ; sinon "".
- Ne demande jamais une clef d'API ni un mot de passe ; ne les écris jamais.

Réponds par un objet JSON :
{"reponse": "texte pour l'utilisateur",
 "etapes": [{"texte": "…", "montrer": {"menu": ["Fabrique IA", "Vidéo", "…"]} ou {"clic_droit": ["…"], "plan": "video"} ou null}],
 "faire": {"menu": [...]} ou {"clic_droit": [...], "plan": "video"} ou null,
 "dites_le": "",
 "manque": ""}
"""


def consignes(menus, extraits):
    return CONSIGNE + "\n\n# MANUEL DE PHILCUT\n\n" + menus + "\n\n" + "\n\n".join(extraits)


def texte_demande(question, historique, etat_texte):
    lignes = ["# ETAT DE L'ECRAN", etat_texte, ""]
    if historique:
        lignes.append("# DISCUSSION JUSQU'ICI")
        for q, r in historique[-MAX_HISTORIQUE:]:
            lignes.append(f"Utilisateur : {q}")
            lignes.append(f"Aide : {r}")
        lignes.append("")
    lignes.append("# QUESTION")
    lignes.append(question.strip())
    return "\n".join(lignes)


def lire_reponse(d):
    """Réponse bornée et nettoyée (l'IA peut renvoyer un peu n'importe quoi)."""
    if not isinstance(d, dict):
        d = {"reponse": str(d or "")}

    def forme(m):
        if not isinstance(m, dict):
            return None
        if isinstance(m.get("menu"), list) and m["menu"]:
            return {"menu": [str(x).strip() for x in m["menu"] if str(x).strip()][:6]}
        if isinstance(m.get("clic_droit"), list) and m["clic_droit"]:
            return {"clic_droit": [str(x).strip() for x in m["clic_droit"] if str(x).strip()][:6],
                    "plan": "son" if m.get("plan") == "son" else "video"}
        return None
    etapes = []
    for e in (d.get("etapes") or [])[:10]:
        if isinstance(e, dict) and str(e.get("texte", "")).strip():
            etapes.append({"texte": str(e["texte"]).strip()[:600], "montrer": forme(e.get("montrer"))})
        elif isinstance(e, str) and e.strip():
            etapes.append({"texte": e.strip()[:600], "montrer": None})
    return {"reponse": str(d.get("reponse") or "").strip()[:4000], "etapes": etapes, "faire": forme(d.get("faire")),
            "dites_le": str(d.get("dites_le") or "").strip()[:300], "manque": str(d.get("manque") or "").strip()[:600]}


def verifier(r, fenetre, ed):
    """Retire tout chemin qui n'existe pas dans les vrais menus (l'étape reste, sans bouton). Renvoie le nombre retiré."""
    retires = 0
    for e in r["etapes"]:
        if e["montrer"] and not chemin_valide(fenetre, ed, e["montrer"]):
            e["montrer"] = None
            retires += 1
    if r["faire"] and not chemin_valide(fenetre, ed, r["faire"]):
        r["faire"] = None
        retires += 1
    return retires


def prix_question(params, niveau, taille_consignes, images):
    """Coût indicatif d'une question en $ (0 pour l'IA de ce poste)."""
    if niveau == "locale":
        return 0.0
    from . import ia
    _m, _e, cout = ia.estimer_cout(dict(params, ia_moteur=niveau), taille_consignes // 4 + 600, images, 900)
    return cout


def preparer(fenetre, ed, params, question, historique=(), niveau="claude"):
    """Dans le fil de l'interface : lit menus, guides, état (rapide), renvoie (consignes, texte)."""
    menus, morceaux = manuel(fenetre, ed)
    budget = MAX_MANUEL_LOCAL if niveau == "locale" else 10 ** 7
    extraits = choisir(question + " " + " ".join(q for q, _r in historique[-2:]), morceaux, budget)
    if niveau != "locale":
        extraits = [t for t, _c in morceaux]          # cloud : tout le manuel, toujours dans le même ordre (cache du fournisseur)
    return consignes(menus, extraits), texte_demande(question, list(historique), etat(fenetre, ed, params))


def envoyer(params, consignes_, texte, images=(), niveau="claude"):
    """L'appel à l'IA (dans un fil) ; renvoie la réponse lue (non vérifiée)."""
    from . import assistant_creation as A
    return lire_reponse(A.demander(params, consignes_, texte, list(images), niveau, max_jetons=1800))
