"""Nouveautés du catalogue en ligne (0.9.26) : Goodies dessinés, modèles de montage, styles « à la manière de »,
modèles de tampons IA, ajoutés chaque mois par la veille (catalogue/nouveautes.json sur GitHub) sans réinstaller
PhilCut. Copie locale pour les jours sans réseau ; ce qui est nouveau depuis votre dernier regard porte ✦.

Le fichier ne contient que des données (textes, descriptions, dessins SVG) : jamais de code."""
from .catalogue_ligne import charger, localise
from .langue import _

FICHIER = "nouveautes.json"
CATEGORIES = {"goodies": _("Goodies"), "modeles_montage": _("Modèles de montage"), "presentations": _("Présentations de photos"),
              "styles": _("Styles « à la manière de »"), "tampons_ia": _("Modèles de tampons IA")}
_ARRIVES = []              # [{cat, id, nom, desc, ajoute}]
_INTEGRES = {"styles": set(), "tampons_ia": set()}      # déjà ajoutés par le catalogue (intégrer deux fois ne change rien)


def integrer(reseau=False, delai=8):
    """Lit le catalogue (en ligne si reseau) et ajoute son contenu à PhilCut ; renvoie la liste de ce qu'il contient."""
    from . import goodies as GO, goodies_svg as GS, modeles_montage as MM, styles_ia as S, tampons_ia as TI
    d = charger(FICHIER, reseau, delai)
    arrives = []
    for pk_id, pk in (d.get("packs_goodies") or {}).items():
        GO.PACKS.setdefault(pk_id, {"nom": localise(pk.get("nom")) or pk_id, "description": localise(pk.get("description")), "goodies": []})
    for gid, e in (d.get("goodies") or {}).items():
        if not isinstance(e, dict) or not e.get("svg") or not GS.valide(e["svg"]):
            continue
        GS.enregistrer(gid, {"nom": localise(e.get("nom")) or gid, "svg": e["svg"], "animation": e.get("animation", "pop"), "pack": e.get("pack")})
        genre = GS.genre(gid)
        GO.GENRES[genre] = (localise(e.get("nom")) or gid, "", (0, 0))
        pack = GO.PACKS.setdefault(e.get("pack") or "catalogue", {"nom": _("Nouveautés du catalogue"), "description": "", "goodies": []})
        if genre not in pack["goodies"]:
            pack["goodies"].append(genre)
        arrives.append({"cat": "goodies", "id": genre, "nom": localise(e.get("nom")) or gid, "desc": localise(e.get("description")),
                        "ajoute": e.get("ajoute", "")})
    MM.mettre_a_jour(d.get("mises_a_jour_modeles"))          # les modèles intégrés évoluent aussi (0.9.27)
    for ident, maj in (d.get("mises_a_jour_modeles") or {}).items():
        if ident in MM.MODELES:
            arrives.append({"cat": "modeles_montage", "id": ident + "@" + str(maj.get("ajoute", "")), "nom": MM.MODELES[ident]["nom"],
                            "desc": localise(maj.get("explication")) or _("Modèle mis à jour : nouvelles transitions ou animations."),
                            "ajoute": maj.get("ajoute", "")})
    from . import presentation as PR
    for v in d.get("presentations") or []:                     # variantes des présentations de photos
        if isinstance(v, dict) and v.get("id") and v.get("style") in PR.STYLES:
            PR.VARIANTES[v["id"]] = {"nom": localise(v.get("nom")) or v["id"], "desc": localise(v.get("desc")), "style": v["style"],
                                     "fond": v.get("fond", "flou") if v.get("fond") in PR.FONDS else "flou",
                                     "options": {k: v[k] for k in ("fragments",) if k in v}, "duree_image": v.get("duree_image")}
            arrives.append({"cat": "presentations", "id": v["id"], "nom": PR.VARIANTES[v["id"]]["nom"], "desc": PR.VARIANTES[v["id"]]["desc"],
                            "ajoute": v.get("ajoute", "")})
    MM._EN_LIGNE.clear()
    for m in d.get("modeles_montage") or []:
        if isinstance(m, dict) and m.get("id") and m.get("type") in __import__("app.recettes", fromlist=["TYPES"]).TYPES:
            MM._EN_LIGNE.append(m)
            arrives.append({"cat": "modeles_montage", "id": m["id"], "nom": localise(m.get("nom")) or m["id"], "desc": localise(m.get("desc")),
                            "ajoute": m.get("ajoute", "")})
    for nom, asp in (d.get("styles") or {}).items():
        if isinstance(asp, dict) and nom and (S._net(nom) not in S.REFERENCES or nom in _INTEGRES["styles"]):
            _INTEGRES["styles"].add(nom)
            noms = [S._net(nom)] + [S._net(a) for a in asp.get("autres_noms") or []]
            for n in noms:
                if n.endswith("*"):
                    n = n[:-1]
                    S.AVEC_LIEN.add(n)
                S.REFERENCES[n] = (noms[0].rstrip("*"), {k: v for k, v in asp.items() if k in ("voix", "musique", "image", "jeu") and isinstance(v, str)})
            arrives.append({"cat": "styles", "id": nom, "nom": nom, "desc": asp.get("image") or asp.get("voix") or asp.get("musique") or "",
                            "ajoute": asp.get("ajoute", "")})
    for m in d.get("tampons_ia") or []:
        if isinstance(m, dict) and m.get("id") and m.get("consigne") and (m["id"] not in TI.MODELES or m["id"] in _INTEGRES["tampons_ia"]):
            _INTEGRES["tampons_ia"].add(m["id"])
            TI.MODELES[m["id"]] = (localise(m.get("nom")) or m["id"], m["consigne"], m.get("mouvement", "zoom"),
                                   [b for b in m.get("bruitages") or [] if isinstance(b, str)], localise(m.get("phrase")), localise(m.get("texte")),
                                   m.get("voix", "normale"), float(m.get("duree", 3.0)))
            arrives.append({"cat": "tampons_ia", "id": m["id"], "nom": localise(m.get("nom")) or m["id"], "desc": localise(m.get("texte")) or "",
                            "ajoute": m.get("ajoute", "")})
    _ARRIVES[:] = arrives
    return arrives


def liste(params=None):
    vus = set((params or {}).get("nouveautes_vues") or [])
    return [dict(a, nouveau=f"{a['cat']}:{a['id']}" not in vus) for a in _ARRIVES]


def nombre_nouveaux(params=None):
    return sum(1 for a in liste(params) if a["nouveau"])


def est_nouveau(params, cat, ident):
    return f"{cat}:{ident}" not in set((params or {}).get("nouveautes_vues") or []) and any(a["cat"] == cat and a["id"] == ident for a in _ARRIVES)


def marquer_vus(params, cat=None):
    vus = set(params.get("nouveautes_vues") or [])
    vus |= {f"{a['cat']}:{a['id']}" for a in _ARRIVES if cat is None or a["cat"] == cat}
    params["nouveautes_vues"] = sorted(vus)
    try:
        params.enregistrer()
    except AttributeError:
        pass
