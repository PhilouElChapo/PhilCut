"""Recettes IA et « Créations à refaire ou à calculer » (0.9.37) : brique commune à PhilCut, PhilMusic et, plus tard,
au téléphone.

Une recette décrit une INTENTION (une musique, une image retouchée, une voix…), pas un outil : ce qui a été demandé, avec
quels réglages, par quel moteur, quand, et ce qu'elle a coûté. Elle voyage avec le projet (le média garde « recette »)
et à côté du fichier (« .ia.json »).

La liste rassemble ce qui reste à faire : une création demandée « à calculer sur le PC » (depuis le téléphone), une
création dont le fichier n'est ni ici ni sur le Drive (à refaire). Chaque ligne est PROPOSÉE, jamais lancée seule :
calculer sur ce poste (gratuit) ou refaire avec un service payant (coût annoncé, déjà payé signalé), puis comparer
avant / après et choisir.
"""
import hashlib
import json
import os

from .langue import _

INTENTIONS = {"musique": _("Musique"), "image": _("Image retouchée"), "logo": _("Logo, intro, miniature"), "video": _("Vidéo IA"),
              "voix": _("Voix, réplique"), "sequence": _("Séquence IA")}
# moteur : (nom, gratuit, intentions qu'il sait faire, ce que PhilCut sait relancer seul)
MOTEURS = {"locale": (_("Sur ce poste (gratuit)"), True), "gemini": (_("Gemini (votre clef, payant)"), False),
           "outil": (_("Ouvrir l'outil avec la recette"), True)}
AUTOMATIQUE = {("musique", "locale"), ("image", "locale"), ("image", "gemini"), ("logo", "locale"), ("logo", "gemini"),
               ("voix", "locale"), ("voix", "gemini")}
PRIX_GEMINI = {"image": 0.04, "logo": 0.04, "voix": 0.01}      # euros, indicatif (relevé novembre 2026) ; affiché avant


def intention(recette):
    r = recette or {}
    if r.get("intention"):
        return r["intention"]
    if r.get("replique") and not r.get("prompt"):
        return "voix"
    return r.get("famille") or "image"


def empreinte(recette):
    """Ce qui identifie une demande (pas son résultat) : deux demandes identiques ont la même empreinte. Sert à ne
    jamais payer deux fois la même chose."""
    r = dict(recette or {})
    for k in ("moteur", "date", "cout", "paye", "empreinte", "appareil", "qualite"):
        r.pop(k, None)
    texte = json.dumps(r, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(texte.encode("utf-8")).hexdigest()[:20]


def _recettes_dans(dossier):
    try:
        noms = os.listdir(dossier)
    except OSError:
        return
    for n in noms:
        if n.endswith(".ia.json"):
            p = os.path.join(dossier, n)
            try:
                with open(p, encoding="utf-8") as f:
                    yield p[:-len(".ia.json")], json.load(f)
            except (OSError, ValueError):
                continue


def deja_fait(recette, params=None):
    """Un résultat de la même demande, ici (créations de ce poste) ou sur le Drive (déposé par un autre appareil) :
    (chemin, recette) ou None. Il est repris au lieu d'être refait — et jamais repayé."""
    e = empreinte(recette)
    dossiers = []
    try:
        from .creations import dossier
        dossiers.append(dossier())
    except Exception:      # noqa: BLE001
        pass
    try:
        from . import drive_philcut as DP
        r = DP.racine(params or {})
        if r:
            dossiers.append(os.path.join(r, "Creations"))
    except Exception:      # noqa: BLE001
        pass
    for d in dossiers:
        for chemin, rec in _recettes_dans(d) or ():
            if os.path.exists(chemin) and (rec.get("empreinte") == e or empreinte(rec) == e):
                return chemin, rec
    return None


def noter_recette(m, chemin=None):
    """Le média garde sa recette dans le projet (pour la refaire ailleurs, même sans le fichier)."""
    from . import creations
    rec = creations.lire(chemin or m.get("chemin") or "")
    if rec and m.get("recette") != rec:
        rec.setdefault("empreinte", empreinte(rec))
        m["recette"] = rec
    return m.get("recette")


def a_traiter(projet, params=None):
    """Lignes de la liste : {"media", "recette", "intention", "etat": a_calculer | a_refaire, "pourquoi", "existant"}."""
    out = []
    for m in projet.medias:
        rec = m.get("recette")
        if not rec:
            continue
        present = os.path.exists(m.get("chemin") or "") and not m.get("copie_legere")
        if m.get("a_calculer"):
            etat, pourquoi = "a_calculer", _("demandée sur {a}, à calculer sur un PC", a=m["a_calculer"].get("appareil") or _("un autre appareil"))
        elif not present:
            etat, pourquoi = "a_refaire", _("le fichier n'est ni sur ce poste ni sur le Drive")
        else:
            continue
        existant = deja_fait(rec, params)
        out.append({"media": m, "recette": rec, "intention": intention(rec), "etat": etat, "pourquoi": pourquoi,
                    "existant": existant[0] if existant else None, "paye": bool(rec.get("paye"))})
    return out


def moteurs_possibles(ligne, params=None):
    """[(moteur, libellé, prix en euros ou 0, durée estimée en secondes)] : le gratuit d'abord, puis Gemini (tableau des
    recettes validé le 9 novembre 2026), puis l'outil avec la recette."""
    it, rec = ligne["intention"], ligne["recette"]
    out = []
    if (it, "locale") in AUTOMATIQUE and (it not in ("image",) or source_image(ligne) or rec.get("sans_source")):
        d = float((rec.get("fiche") or {}).get("duree") or rec.get("duree") or 60) if it == "musique" else 60.0
        out.append(("locale", MOTEURS["locale"][0], 0.0, max(60.0, d * 3) if it == "musique" else 120.0))
    if (it, "gemini") in AUTOMATIQUE and _a_clef(params):
        prix = PRIX_GEMINI.get(it, 0.05)
        if it == "voix":
            from . import diction
            prix = diction.prix(rec.get("replique") or "", "gemini") or prix
        out.append(("gemini", MOTEURS["gemini"][0], prix, 30.0))
    out.append(("outil", MOTEURS["outil"][0], 0.0, 0.0))
    return out


def source_image(ligne):
    """L'image de départ gardée à côté de la création (« <création>.source.png »), si elle existe sur ce poste ou au Drive."""
    rec, m = ligne["recette"], ligne["media"]
    nom = rec.get("source_image")
    if not nom:
        return None
    for d in filter(None, (os.path.dirname(m.get("chemin") or ""), _dossier_creations())):
        p = os.path.join(d, nom)
        if os.path.exists(p):
            return p
    return None


def _dossier_creations():
    try:
        from .creations import dossier
        return dossier()
    except Exception:      # noqa: BLE001
        return ""


def _a_clef(params):
    try:
        from . import ia
        return any(k == "gemini" for k, *_r in ia.moteurs(params or {}))
    except Exception:      # noqa: BLE001
        return False


def calculer(ligne, moteur, params=None, progression=None, arret=lambda: False):
    """Refait la création (moteur « locale » pour la musique) ; renvoie le nouveau chemin. Le résultat déjà présent ici ou
    sur le Drive est repris tel quel, sans rien recalculer ni payer."""
    rec = ligne["recette"]
    deja = deja_fait(rec, params)
    if deja:
        return deja[0]
    it = ligne["intention"]
    if (it, moteur) not in AUTOMATIQUE:
        raise RuntimeError(_("Cette création s'ouvre dans son outil pour être refaite."))
    import time
    from . import creations
    horo = time.strftime("%Y%m%d_%H%M%S")
    if it == "musique":
        return _musique(rec, params, progression, arret, horo)
    nouvelle = dict(rec, moteur=f"{moteur}", date=time.strftime("%Y-%m-%d %H:%M"), empreinte=rec.get("empreinte") or empreinte(rec))
    if it in ("image", "logo"):
        sortie = os.path.join(creations.dossier(), f"{rec.get('effet') or it}_{horo}.png")
        src = source_image(ligne)
        consigne = rec.get("anglais") or rec.get("prompt") or ""
        if moteur == "locale":
            from . import creatif as C
            C.image(consigne, sortie, params, init=None if rec.get("sans_source") else src, force=float(rec.get("force") or 0.55),
                    progression=progression, arret=arret)
        else:
            from . import ia
            if progression:
                progression(0.2, _("Envoi à Gemini…"))
            if src:
                with open(src, "rb") as f:
                    png = ia.retoucher_image(params, f.read(), consigne)
            else:
                png = ia.generer_image(params, consigne)
            with open(sortie, "wb") as f:
                f.write(png)
            nouvelle["paye"] = True
        if src:
            import shutil
            shutil.copy2(src, sortie + ".source.png")
            nouvelle["source_image"] = os.path.basename(sortie + ".source.png")
    elif it == "voix":
        from . import diction
        sortie = os.path.join(creations.dossier(), f"replique_{horo}.wav")
        if progression:
            progression(0.2, _("La voix dit la réplique…"))
        diction.dire(rec.get("replique") or "", sortie, params, style=rec.get("diction") or "naturel",
                     moteur_voix="gemini" if moteur == "gemini" else "local")
        nouvelle["paye"] = moteur == "gemini"
    else:
        raise RuntimeError(_("Cette création s'ouvre dans son outil pour être refaite."))
    creations.ecrire(sortie, nouvelle)
    if progression:
        progression(1.0, _("Terminé."))
    return sortie


def _musique(rec, params, progression, arret, horo):
    import time
    from . import creations, musique_ia as MI
    sortie = os.path.join(creations.dossier(), f"musique_{horo}.mp3")
    fiche = rec.get("fiche") or {"phrase": rec.get("prompt") or "", "duree": rec.get("duree") or 60, "instrumental": rec.get("instrumental", True),
                                 "paroles": rec.get("paroles") or "", "voix": rec.get("voix") or "auto", "langue": rec.get("langue") or "fr"}
    if rec.get("anglais") and not fiche.get("consigne_ia"):
        fiche = dict(fiche, consigne_ia=rec["anglais"], utiliser_ia=True)     # la consigne exacte d'origine, déjà en anglais
    chemin, c = MI.creer(fiche, sortie, params, progression, arret)
    nouvelle = MI.recette(fiche, c)
    nouvelle["empreinte"] = rec.get("empreinte") or empreinte(rec)
    nouvelle["date"] = time.strftime("%Y-%m-%d %H:%M")
    creations.ecrire(chemin, nouvelle)
    return chemin
