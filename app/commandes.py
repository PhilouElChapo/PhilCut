"""Registre des commandes de PhilCut (1.4.0, choix de Philippe le 27/11 après la comparaison avec FilmCraft).

Chaque commande est déclarée UNE fois : son nom, sa famille, son libellé, la ligne qui l'explique à l'IA, la phrase qui la
décrit avant de la faire, et ce qu'elle fait. « Dites-le en clair » (règles, IA locale, Claude ou Gemini) pilote PhilCut par
ce registre ; un serveur MCP pourra s'y brancher plus tard sans rien redéclarer. Rien n'est fait sans le clic de
l'utilisateur : les commandes comprises sont montrées, cochables, puis faites en une seule étape d'annulation.

Les plans se désignent par leur numéro sur leur piste (à partir de 1, dans l'ordre du temps) ; les pistes par « video »,
« video2 »…, « audio » (la musique), « audio2 »…, « voix ». Une piste verrouillée n'est jamais modifiée.
"""
import copy

from .langue import _

FAMILLES = {"montage": _("Montage"), "pistes": _("Pistes"), "son": _("Son"), "reperes": _("Repères"),
            "habillage": _("Textes et habillage"), "couleur": _("Couleur"), "rushes": _("Rushes")}
REGISTRE = {}


class Commande:
    def __init__(self, nom, famille, libelle, aide, decrire, faire):
        self.nom, self.famille, self.libelle, self.aide, self.decrire, self.faire = nom, famille, libelle, aide, decrire, faire


def declarer(nom, famille, libelle, aide, decrire):
    """Décorateur : la fonction décorée fait la commande, faire(ctx, a) -> vrai si quelque chose a changé."""
    def poser(f):
        REGISTRE[nom] = Commande(nom, famille, libelle, aide, decrire, f)
        return f
    return poser


def consigne():
    """Les lignes qui expliquent chaque commande à l'IA, par famille et par ordre alphabétique."""
    return "\n".join(f'- "{c.nom}" {c.aide}' for c in sorted(REGISTRE.values(), key=lambda c: (c.famille, c.nom)))


def par_famille():
    """{famille: [commandes par ordre alphabétique du libellé]} : pour une aide, une liste ou un serveur MCP."""
    out = {}
    for c in sorted(REGISTRE.values(), key=lambda c: str(c.libelle).lower()):
        out.setdefault(c.famille, []).append(c)
    return out


# ------------------------------------------------------------------ contexte
class Contexte:
    """Ce dont une commande a besoin : le projet, l'éditeur (ligne rouge, sélection)."""
    def __init__(self, ed):
        self.ed, self.projet = ed, ed.projet
        self.t0 = float(getattr(getattr(ed, "timeline", None), "position", 0.0) or 0.0)
        self.refuses = []                               # pistes verrouillées rencontrées

    def piste(self, a, defaut="video"):
        p = str(a.get("piste") or defaut).strip().lower()
        p = {"musique": "audio", "vidéo": "video", "son": "audio"}.get(p, p)
        return p if p in self.projet.toutes_pistes() else defaut

    def libre(self, piste):
        if self.projet.piste_verrouillee(piste):
            if piste not in self.refuses:
                self.refuses.append(piste)
            return False
        return True

    def plans(self, a, cle="plans"):
        """Les plans désignés (numéros sur la piste, "tous", ou un seul numéro sous « plan »)."""
        piste = self.piste(a)
        cs = self.projet.clips_piste(piste)
        v = a.get(cle, a.get("plan"))
        if v == "tous":
            return list(cs)
        if isinstance(v, (int, float)):
            v = [int(v)]
        if isinstance(v, list):
            return [cs[int(i) - 1] for i in v if isinstance(i, (int, float)) and 1 <= int(i) <= len(cs)]
        sel = self.ed._clip_selectionne() if hasattr(self.ed, "_clip_selectionne") else None
        return [sel] if sel and sel["piste"] == piste else []

    def media(self, v):
        ms = self.projet.medias
        if isinstance(v, (int, float)) and 1 <= int(v) <= len(ms):
            return ms[int(v) - 1]
        t = str(v or "").strip().lower()
        return next((m for m in ms if m["nom"].lower() == t), None) or next((m for m in ms if t and t in m["nom"].lower()), None)


def etat(projet, t0=0.0):
    """L'état du montage, en clair, pour l'IA : médias numérotés, pistes et plans numérotés, marqueurs, ligne rouge."""
    from .projet import fin_clip
    lignes = [f"Ligne rouge : {t0:.1f} s ; durée du montage : {projet.duree():.1f} s"]
    ms = [f"{i + 1}: {m['nom']} ({m['genre']}, {float((m.get('fiche') or {}).get('duree') or 0):.1f} s)"
          for i, m in enumerate(projet.medias[:60])]
    lignes.append("Médias : " + ("; ".join(ms) or "aucun"))
    for p in projet.toutes_pistes():
        cs = projet.clips_piste(p)
        marques = [x for x, oui in (("muette", projet.piste_muette(p)), ("verrouillée", projet.piste_verrouillee(p))) if oui]
        lignes.append(f"Piste {p}" + (f" ({', '.join(marques)})" if marques else "") + " : " +
                      ("; ".join(f"{i + 1}: {c.get('nom', '')} ({c['debut']:.1f}–{fin_clip(c):.1f} s"
                                 f"{', multicaméra angle ' + str(int(c.get('angle') or 0) + 1) if c.get('multicam') else ''})"
                                 for i, c in enumerate(cs[:80]))
                       or "vide"))
    for mc in (projet.d.get("multicams") or {}).values():
        lignes.append("Multicaméra : " + "; ".join(f"angle {k + 1} = {a.get('nom', '')}" for k, a in enumerate(mc["angles"])))
    if projet.marqueurs:
        lignes.append("Marqueurs : " + "; ".join(f"{m['t']:.1f} s {m.get('texte', '')}".strip() for m in projet.marqueurs[:40]))
    return "\n".join(lignes)


def _qui(a):
    v = a.get("plans", a.get("plan"))
    piste = a.get("piste") or "video"
    if v == "tous":
        return _("tous les plans de la piste {p}", p=piste)
    if isinstance(v, (int, float)):
        v = [int(v)]
    if isinstance(v, list):
        return _("plan(s) {l} de la piste {p}", l=", ".join(str(x) for x in v), p=piste)
    return _("le plan sélectionné")


def _decaler(projet, c, ecart):
    """Les plans qui suivent c sur sa piste avancent ou reculent de `ecart` secondes (la suite reste collée)."""
    for x in projet.clips_piste(c["piste"]):
        if x is not c and x["debut"] > c["debut"]:
            x["debut"] = max(0.0, x["debut"] + ecart)
    projet.ranger(c["piste"])


# ------------------------------------------------------------------ famille « montage »
@declarer("poser_media", "montage", _("Poser un rush sur la timeline"),
          '{"media": numéro ou nom du média, "piste": piste (facultatif), "debut": secondes | "fin" (à la suite, par défaut) | '
          '"ligne" (à la ligne rouge)}',
          lambda a: _("Poser le média « {m} » sur la piste {p}{d}", m=a.get("media"), p=a.get("piste") or _("qui lui convient"),
                      d=_(" à la ligne rouge") if a.get("debut") == "ligne" else
                      (_(" à {s} s", s=a["debut"]) if isinstance(a.get("debut"), (int, float)) else _(" à la suite"))))
def _poser_media(ctx, a):
    m = ctx.media(a.get("media"))
    if not m:
        return False
    piste = ctx.piste(a, "audio" if m["genre"] == "audio" else "video")
    if not ctx.libre(piste):
        return False
    d = a.get("debut")
    debut = ctx.t0 if d == "ligne" else (float(d) if isinstance(d, (int, float)) else None)
    ctx.projet.ajouter_clip(m["id"], piste, debut)
    ctx.projet.ranger(piste)
    return True


@declarer("supprimer_plan", "montage", _("Supprimer des plans"),
          '{"plans": [numéros] | "tous", "piste": piste, "refermer": true (la suite se recolle, par défaut) | false}',
          lambda a: _("Supprimer {q}{r}", q=_qui(a), r="" if a.get("refermer", True) else _(" en laissant le vide")))
def _supprimer_plan(ctx, a):
    piste = ctx.piste(a)
    if not ctx.libre(piste):
        return False
    cs = ctx.plans(a)
    for c in sorted(cs, key=lambda c: -c["debut"]):
        ctx.projet.retirer_clip(c["id"], bool(a.get("refermer", True)))
    return bool(cs)


@declarer("deplacer_plan", "montage", _("Déplacer un plan dans le temps"),
          '{"plan": numéro, "piste": piste, "debut": secondes}',
          lambda a: _("Déplacer {q} à {s} s", q=_qui(a), s=a.get("debut")))
def _deplacer_plan(ctx, a):
    cs = ctx.plans(a)
    if not cs or not ctx.libre(cs[0]["piste"]) or not isinstance(a.get("debut"), (int, float)):
        return False
    ctx.projet.deplacer(cs[0]["id"], float(a["debut"]))
    return True


@declarer("changer_ordre", "montage", _("Changer l'ordre des plans"),
          '{"plan": numéro, "position": nouveau numéro sur la piste, "piste": piste} (les plans se recollent)',
          lambda a: _("Mettre {q} en position {n}", q=_qui(a), n=a.get("position")))
def _changer_ordre(ctx, a):
    piste = ctx.piste(a)
    cs = ctx.projet.clips_piste(piste)
    sel = ctx.plans(a)
    if not sel or not ctx.libre(piste) or not isinstance(a.get("position"), (int, float)):
        return False
    from .projet import duree_clip
    ordre = [c for c in cs if c is not sel[0]]
    ordre.insert(max(0, min(len(ordre), int(a["position"]) - 1)), sel[0])
    t = min(c["debut"] for c in cs)
    for c in ordre:
        c["debut"] = t
        t += duree_clip(c)
    return True


@declarer("raccourcir_plan", "montage", _("Raccourcir un plan"),
          '{"plan": numéro, "piste": piste, "debut": secondes retirées au début, "fin": secondes retirées à la fin} (la suite se recolle)',
          lambda a: _("Raccourcir {q} : {d} s en moins au début, {f} s en moins à la fin", q=_qui(a), d=a.get("debut") or 0,
                      f=a.get("fin") or 0))
def _raccourcir_plan(ctx, a):
    from .projet import duree_clip
    cs = ctx.plans(a)
    if not cs or not ctx.libre(cs[0]["piste"]):
        return False
    c = cs[0]
    v = float(c.get("vitesse") or 1.0)
    avant = duree_clip(c)
    d, f = max(0.0, float(a.get("debut") or 0)), max(0.0, float(a.get("fin") or 0))
    if d + f <= 0 or d + f >= avant - 0.04:
        return False
    ctx.projet.rogner(c["id"], c["src_debut"] + d * v, c["src_fin"] - f * v)
    _decaler(ctx.projet, c, duree_clip(c) - avant)
    return True


@declarer("dupliquer_plan", "montage", _("Dupliquer un plan"),
          '{"plan": numéro, "piste": piste} (la copie se place juste après)',
          lambda a: _("Dupliquer {q} (la copie juste après)", q=_qui(a)))
def _dupliquer_plan(ctx, a):
    from .projet import _id, duree_clip, fin_clip
    cs = ctx.plans(a)
    if not cs or not ctx.libre(cs[0]["piste"]):
        return False
    c = cs[0]
    n = copy.deepcopy(c)
    n["id"], n["debut"] = _id(), fin_clip(c)
    _decaler(ctx.projet, c, duree_clip(c))
    ctx.projet.clips.append(n)
    ctx.projet.ranger(c["piste"])
    return True


@declarer("retirer_partie", "montage", _("Retirer une partie du film"),
          '{"de": secondes, "a": secondes} (toutes les pistes ; la suite se recolle)',
          lambda a: _("Retirer du film la partie de {a} s à {b} s (toutes les pistes, la suite se recolle)", a=a.get("de"), b=a.get("a")))
def _retirer_partie(ctx, a):
    if not all(isinstance(a.get(k), (int, float)) for k in ("de", "a")):
        return False
    return bool(ctx.projet.partie(float(a["de"]), float(a["a"]), False))


@declarer("garder_partie", "montage", _("Ne garder qu'une partie du film"),
          '{"de": secondes, "a": secondes} (tout le reste est retiré)',
          lambda a: _("Ne garder du film que la partie de {a} s à {b} s", a=a.get("de"), b=a.get("a")))
def _garder_partie(ctx, a):
    if not all(isinstance(a.get(k), (int, float)) for k in ("de", "a")):
        return False
    return bool(ctx.projet.partie(float(a["de"]), float(a["a"]), True))


@declarer("refermer_trous", "montage", _("Refermer les trous"),
          '{"piste": piste | "toutes"} (chaque plan colle au précédent)',
          lambda a: _("Refermer les trous de la piste {p}", p=a.get("piste") or "video") if a.get("piste") != "toutes"
          else _("Refermer les trous de toutes les pistes"))
def _refermer_trous(ctx, a):
    pistes = ctx.projet.toutes_pistes() if a.get("piste") == "toutes" else [ctx.piste(a)]
    fait = False
    for p in pistes:
        if ctx.libre(p) and ctx.projet.clips_piste(p):
            ctx.projet.resserrer(p)
            fait = True
    return fait


@declarer("changer_angle", "montage", _("Changer l'angle d'un plan multicaméra"),
          '{"plan": numéro sur la piste video, "angle": 1..4}',
          lambda a: _("Montrer l'angle {n} sur {q}", n=a.get("angle"), q=_qui(a)))
def _changer_angle(ctx, a):
    from . import multicam as MC
    cs = ctx.plans(a)
    if not cs or not ctx.libre(cs[0]["piste"]) or not isinstance(a.get("angle"), (int, float)):
        return False
    return MC.changer_angle(ctx.projet, cs[0], int(a["angle"]) - 1)


@declarer("couper_angle", "montage", _("Couper un plan multicaméra sur un angle"),
          '{"t": secondes de la timeline, "angle": 1..4} (à partir de t, le plan multicaméra montre cet angle)',
          lambda a: _("A {s} s, passer à l'angle {n}", s=a.get("t"), n=a.get("angle")))
def _couper_angle(ctx, a):
    from . import multicam as MC
    if not ctx.libre("video") or not all(isinstance(a.get(k), (int, float)) for k in ("t", "angle")):
        return False
    return MC.couper_angle(ctx.projet, float(a["t"]), int(a["angle"]) - 1) is not None


# ------------------------------------------------------------------ famille « son »
@declarer("son_plan", "son", _("Son d'un plan"),
          '{"plans": [numéros] | "tous", "piste": piste, "volume": 0..2 (facultatif), "muet": true|false (facultatif), '
          '"fondu_entree": secondes (facultatif), "fondu_sortie": secondes (facultatif)}',
          lambda a: _("Son de {q} : {r}", q=_qui(a), r=", ".join(
              x for x in ((_("volume {v} %", v=int(float(a["volume"]) * 100)) if isinstance(a.get("volume"), (int, float)) else ""),
                          (_("muet") if a.get("muet") else _("son remis")) if isinstance(a.get("muet"), bool) else "",
                          _("fondu d'entrée {s} s", s=a["fondu_entree"]) if isinstance(a.get("fondu_entree"), (int, float)) else "",
                          _("fondu de sortie {s} s", s=a["fondu_sortie"]) if isinstance(a.get("fondu_sortie"), (int, float)) else "")
              if x) or "—"))
def _son_plan(ctx, a):
    cs = [c for c in ctx.plans(a) if ctx.libre(c["piste"])]
    for c in cs:
        if isinstance(a.get("volume"), (int, float)):
            c["volume"] = max(0.0, min(2.0, float(a["volume"])))
        if isinstance(a.get("muet"), bool):
            c["muet"] = a["muet"]
        for k in ("fondu_entree", "fondu_sortie"):
            if isinstance(a.get(k), (int, float)):
                c[k] = max(0.0, min(30.0, float(a[k])))
    return bool(cs)


def _lib_cible(k):
    from . import niveau_sonore as NS
    return dict(NS.choix_cibles()).get(k, _("celle des Préférences"))


@declarer("cible_son", "son", _("Choisir le volume cible du film"),
          '{"cible": "youtube" | "instagram" | "ecran_led" | "television" | "podcast" | "auto" (selon la destination) | "" (celle des '
          'Préférences)}',
          lambda a: _("Volume cible du film : {c}", c=_lib_cible(a.get("cible"))))
def _cible_son(ctx, a):
    from . import niveau_sonore as NS
    k = a.get("cible") or ""
    if k and k != "auto" and k not in NS.CIBLES:
        return False
    if k:
        ctx.projet.d["son_cible"] = k
    else:
        ctx.projet.d.pop("son_cible", None)
    return True


@declarer("mesurer_son", "son", _("Mesurer le volume du film"), "{} (mesure EBU R128 sur ce poste, gratuite)",
          lambda a: _("Mesurer le volume du film (sur ce poste, gratuit)"))
def _mesurer_son(ctx, a):
    f = ctx.ed.window() if hasattr(ctx.ed, "window") else None
    if f is None or not hasattr(f, "mesurer_son"):
        return False
    f.mesurer_son(ctx.ed)
    return True


# ------------------------------------------------------------------ famille « pistes »
@declarer("ajouter_piste", "pistes", _("Ajouter une piste"), '{"genre": "video" | "audio"} (4 au plus de chaque)',
          lambda a: _("Ajouter une piste {g}", g=_("vidéo") if a.get("genre") == "video" else _("audio")))
def _ajouter_piste(ctx, a):
    genre = "video" if a.get("genre") == "video" else "audio"
    avant = len(ctx.projet.toutes_pistes())
    ctx.projet.ajouter_piste(genre)
    return len(ctx.projet.toutes_pistes()) > avant


@declarer("regler_piste", "pistes", _("Régler une piste"),
          '{"piste": piste, "quoi": "muette" | "solo" | "verrou" | "masquee", "etat": true | false}',
          lambda a: _("Piste {p} : {q} {e}", p=a.get("piste"),
                      q={"muette": _("muette"), "solo": _("en solo"), "verrou": _("verrouillée"), "masquee": _("masquée")}.get(a.get("quoi"), "?"),
                      e=_("(oui)") if a.get("etat", True) else _("(non)")))
def _regler_piste(ctx, a):
    p, quoi = ctx.piste(a, ""), a.get("quoi")
    lire = {"muette": lambda: p in (ctx.projet.d.get("pistes_muettes") or []), "solo": lambda: ctx.projet.piste_solo(p),
            "verrou": lambda: ctx.projet.piste_verrouillee(p), "masquee": lambda: ctx.projet.piste_masquee(p)}.get(quoi)
    if not p or not lire or lire() == bool(a.get("etat", True)):
        return False
    ctx.projet.basculer_piste(p, quoi)
    return True


@declarer("renommer_piste", "pistes", _("Renommer une piste"), '{"piste": piste, "nom": "..." (24 caractères au plus)}',
          lambda a: _("Renommer la piste {p} en « {n} »", p=a.get("piste"), n=a.get("nom", "")))
def _renommer_piste(ctx, a):
    p = ctx.piste(a, "")
    if not p:
        return False
    ctx.projet.renommer_piste(p, str(a.get("nom") or ""))
    return True


@declarer("retirer_piste", "pistes", _("Retirer une piste vide"), '{"piste": piste} (la dernière ajoutée, si elle est vide)',
          lambda a: _("Retirer la piste {p} (si elle est vide et la dernière ajoutée)", p=a.get("piste")))
def _retirer_piste(ctx, a):
    p = ctx.piste(a, "")
    return bool(p and ctx.projet.retirer_piste(p))


# ------------------------------------------------------------------ famille « repères »
@declarer("aller_a", "reperes", _("Placer la ligne rouge"), '{"t": secondes}',
          lambda a: _("Placer la ligne rouge à {s} s", s=a.get("t")))
def _aller_a(ctx, a):
    if not isinstance(a.get("t"), (int, float)) or not hasattr(ctx.ed, "aller_a"):
        return False
    ctx.ed.aller_a(max(0.0, float(a["t"])))
    return True


@declarer("retirer_marqueurs", "reperes", _("Retirer les marqueurs"), "{} (tous les marqueurs)",
          lambda a: _("Retirer tous les marqueurs"))
def _retirer_marqueurs(ctx, a):
    if not ctx.projet.marqueurs:
        return False
    ctx.projet.retirer_marqueur()
    return True


def faire(ctx, a):
    """Fait une commande du registre. Renvoie vrai si elle a changé quelque chose."""
    c = REGISTRE.get(a.get("action"))
    return bool(c and c.faire(ctx, a))
