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
AUTOMATIQUE = {("musique", "locale")}         # le reste s'ouvre dans son outil, recette remplie, pour un dernier regard


def intention(recette):
    r = recette or {}
    return r.get("intention") or r.get("famille") or "image"


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
    """[(moteur, libellé, prix en euros ou 0, durée estimée en secondes)] : le gratuit d'abord."""
    it = ligne["intention"]
    out = []
    if (it, "locale") in AUTOMATIQUE:
        d = float((ligne["recette"].get("fiche") or {}).get("duree") or ligne["recette"].get("duree") or 60)
        out.append(("locale", MOTEURS["locale"][0], 0.0, max(60.0, d * 3)))
    out.append(("outil", MOTEURS["outil"][0], 0.0, 0.0))
    return out


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
    if (ligne["intention"], moteur) not in AUTOMATIQUE:
        raise RuntimeError(_("Cette création s'ouvre dans son outil pour être refaite."))
    import time
    from . import creations, musique_ia as MI
    sortie = os.path.join(creations.dossier(), f"musique_{time.strftime('%Y%m%d_%H%M%S')}.mp3")
    fiche = rec.get("fiche") or {"phrase": rec.get("prompt") or "", "duree": rec.get("duree") or 60, "instrumental": rec.get("instrumental", True),
                                 "paroles": rec.get("paroles") or "", "voix": rec.get("voix") or "auto", "langue": rec.get("langue") or "fr"}
    if rec.get("anglais") and not fiche.get("consigne_ia"):
        fiche = dict(fiche, consigne_ia=rec["anglais"], utiliser_ia=True)     # la consigne exacte d'origine, déjà en anglais
    chemin, c = MI.creer(fiche, sortie, params, progression, arret)
    nouvelle = MI.recette(fiche, c)
    nouvelle["empreinte"] = rec.get("empreinte") or empreinte(rec)
    nouvelle["moteur"] = "locale:ace-step"
    nouvelle["date"] = time.strftime("%Y-%m-%d %H:%M")
    creations.ecrire(chemin, nouvelle)
    return chemin
