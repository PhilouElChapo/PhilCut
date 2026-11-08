"""Modèles de montage tout faits (0.9.25), comme les modèles de CapCut, mais avec VOS rushes et sans rien de payant :
on choisit « Vlog voyage 30 s », « Short dynamique 15 s »…, PhilCut analyse les rushes du projet sur ce poste et
monte : format, durée, rythme des coupes, transitions, look, titre animé, Goodies, écran de fin ; la musique du projet
est calée sur les temps forts. Tout reste modifiable ensuite (et Ctrl+Z revient au montage d'avant).

Le catalogue en ligne (catalogue/modeles.json) ajoute des modèles sans réinstaller PhilCut.
"""
import copy

from .langue import _

# id : nom, description, format, durée (s), type de recette, réglages qui remplacent ceux du type, animation du titre
MODELES = {
    "vlog_30": dict(nom=_("Vlog voyage, 30 s vertical"), desc=_("Coupes vives de 1,5 à 3 s, transitions glissées, titre néon, pour Reels et Shorts."),
                    format="9:16", duree=30, type="visite", titre="neon",
                    reglages=dict(plan_s=(1.5, 3.0), transitions=["t_glisse", "t_zoom_avant", "t_file", "t_flou_fondu"], look="cosy",
                                  musique={"ambiance": "energique", "bpm": 120, "energie": 0.8}, goodies=[], logo="slam")),
    "vlog_2min": dict(nom=_("Vlog voyage, 2 min horizontal"), desc=_("Plans de 3 à 6 s, fondus doux, date des prises, pour YouTube."),
                      format="16:9", duree=120, type="visite", titre="fondu",
                      reglages=dict(plan_s=(3.0, 6.0), transitions=["t_fondu_enchaine", "t_flou_fondu", "t_glisse"], look="cosy",
                                    musique={"ambiance": "chaleureuse", "bpm": 95, "energie": 0.5}, logo="lumiere")),
    "short_15": dict(nom=_("Short dynamique, 15 s"), desc=_("Très rapide : coupes de 0,8 à 1,8 s sur les temps forts, glitch et zooms."),
                     format="9:16", duree=15, type="clip_ia", titre="cinetique",
                     reglages=dict(plan_s=(0.8, 1.8), transitions=["t_glitch", "t_zoom_avant", "t_choc", "t_pixels"], look="glow",
                                   musique={"ambiance": "energique", "bpm": 128, "energie": 0.9}, goodies=[], logo="glitch_net")),
    "vol_1min": dict(nom=_("Vol en avion, 1 min"), desc=_("Ciel retravaillé, altimètre et anémomètre, transitions de ciel, pour une chaîne aviation."),
                     format="16:9", duree=60, type="vol", titre="neon",
                     reglages=dict(plan_s=(3.0, 6.0))),
    "famille": dict(nom=_("Souvenirs de famille"), desc=_("Doux et chaleureux : plans longs, fondus, look cosy, écran de fin."),
                    format="16:9", duree=90, type="portrait", titre="machine",
                    reglages=dict(plan_s=(3.5, 7.0), transitions=["t_fondu_enchaine", "t_fondu_blanc", "t_flou_fondu"], look="cosy",
                                  musique={"ambiance": "douce", "bpm": 85, "energie": 0.4})),
    "anniversaire": dict(nom=_("Anniversaire, fête"), desc=_("Festif : coupes de 2 à 4 s, zooms, transitions colorées, titre qui tournoie."),
                         format="16:9", duree=60, type="portrait", titre="tournoyant",
                         reglages=dict(plan_s=(2.0, 4.0), transitions=["t_zoom", "t_cercle", "t_explosion", "t_glisse"], look="glow",
                                       musique={"ambiance": "energique", "bpm": 115, "energie": 0.8}, logo="slam")),
    "cinema": dict(nom=_("Bande-annonce cinéma"), desc=_("Plans lents, bandes cinéma, fondus au noir, titre sobre : l'effet film."),
                   format="16:9", duree=45, type="generique", titre="fondu",
                   reglages=dict(plan_s=(2.5, 5.0), transitions=["t_fondu_noir", "t_flou_fondu", "t_fondu_enchaine"], look="cinema",
                                 musique={"ambiance": "cinema", "bpm": 90, "energie": 0.6}, logo="cinema")),
    "lieu": dict(nom=_("Présentation d'un lieu"), desc=_("Visite posée : plans de 3 à 5 s, look épuré, horloge, pour une maison, un commerce, une ville."),
                 format="16:9", duree=60, type="visite", titre="fondu",
                 reglages=dict(plan_s=(3.0, 5.0), transitions=["t_glisse", "t_fondu_enchaine"], look="epure", logo="espacement")),
    "annonce_20": dict(nom=_("Annonce, publicité 20 s"), desc=_("Court et clair : coupes de 2 à 3 s, look épuré, pour un écran ou les réseaux."),
                       format="9:16", duree=20, type="annonce", titre="glisse",
                       reglages=dict(plan_s=(2.0, 3.0))),
    "photos_cartes": dict(nom=_("Photos : lancer de cartes"), desc=_("Vos photos lancées comme des cartes sur une table, qui s'empilent ; "
                                                                     "titre et musique du projet."),
                          format="16:9", duree=40, type="clip_ia", titre="glisse", presentation="cartes", fond="table"),
    "photos_explosion": dict(nom=_("Photos : explosion de particules"), desc=_("Chaque photo éclate en fragments, la suivante se reforme : "
                                                                               "énergique, pour un Short ou un Reel."),
                             format="9:16", duree=25, type="clip_ia", titre="cinetique", presentation="explosion", fond="sombre"),
    "photos_mur": dict(nom=_("Photos : mur de souvenirs"), desc=_("Un mur de toutes vos photos ; la caméra plonge sur chacune puis "
                                                                  "recule : idéal pour un anniversaire, un départ, une année."),
                       format="16:9", duree=50, type="clip_ia", titre="neon", presentation="mur", fond="sombre"),
    "photos_corde": dict(nom=_("Photos : polaroïds sur une corde"), desc=_("Des polaroïds suspendus qui se balancent ; la caméra longe la "
                                                                           "corde : vacances, mariage, souvenirs."),
                         format="16:9", duree=45, type="clip_ia", titre="machine", presentation="corde", fond="flou"),
    "diaporama": dict(nom=_("Diaporama de photos"), desc=_("Photos animées une à une (léger zoom), fondus, musique calée sur les temps."),
                      format="16:9", duree=60, type="clip_ia", titre="fondu",
                      reglages=dict(plan_s=(3.0, 4.0), transitions=["t_fondu_enchaine", "t_zoom", "t_glisse"], look="vintage",
                                    musique={"ambiance": "douce", "bpm": 90, "energie": 0.5}, logo="lumiere")),
}


_EN_LIGNE = []             # modèles du catalogue en ligne (nouveautes.integrer)


def tous(params=None):
    """Modèles intégrés + ceux du catalogue en ligne (✦ tant qu'ils sont nouveaux pour vous)."""
    from .langue import LANGUE
    from . import nouveautes as NV
    out = {k: (dict(m, nouveau=NV.est_nouveau(params, "modeles_montage", f"{k}@{m['mis_a_jour']}")) if m.get("mis_a_jour") else m)
           for k, m in MODELES.items()}
    for m in list(_EN_LIGNE) + list((params or {}).get("modeles_montage_en_ligne") or []):
        if m.get("id") and m["id"] not in out and m.get("type"):
            nom = m.get("nom") or {}
            desc = m.get("desc") or {}
            nom = nom if isinstance(nom, dict) else {"fr": nom}
            desc = desc if isinstance(desc, dict) else {"fr": desc}
            out[m["id"]] = dict(m, nom=nom.get(LANGUE) or nom.get("fr") or m["id"], desc=desc.get(LANGUE) or desc.get("fr") or "",
                                nouveau=NV.est_nouveau(params, "modeles_montage", m["id"]))
    return out


def recette(projet, modele_id, params=None, duree=None, format_=None):
    """La recette du modèle avec les rushes du projet (chacun déjà analysé : media["analyse"])."""
    from . import recettes
    m = tous(params).get(modele_id) or MODELES["vlog_2min"]
    reg = copy.deepcopy(m.get("reglages") or {})
    if "plan_s" in reg:
        reg["plan_s"] = tuple(reg["plan_s"])
    r = recettes.proposer(projet.medias, params, format_=format_ or m["format"], duree_cible=duree or m["duree"], type_force=m["type"],
                          reglages=reg)
    if r["textes"]:
        r["textes"][0]["animation"] = m.get("titre", "fondu")
    r["modele"] = modele_id
    r["resume"] = m["nom"] + " · " + r.get("resume", "")
    return r


def appliquer(projet, modele_id, params=None, duree=None, format_=None):
    from . import recettes
    r = recette(projet, modele_id, params, duree, format_)
    recettes.appliquer(r, projet, params)
    return r


def mettre_a_jour(maj):
    """Le catalogue en ligne fait évoluer les modèles intégrés (0.9.27) : nouvelles transitions ajoutées à la liste, autre
    look, autre animation de photos… ; {id: {"reglages": {...}, "presentation": ..., "titre": ...}}. Les listes s'ajoutent
    (sans doublon), le reste remplace."""
    for ident, d in (maj or {}).items():
        m = MODELES.get(ident)
        if not m or not isinstance(d, dict):
            continue
        reg = m.setdefault("reglages", {})
        for k, v in (d.get("reglages") or {}).items():
            if isinstance(v, list) and isinstance(reg.get(k), list) and k != "plan_s":
                reg[k] = reg[k] + [x for x in v if x not in reg[k]]
            else:
                reg[k] = v
        for k in ("presentation", "fond", "titre", "duree", "format"):
            if k in d:
                m[k] = d[k]
        m["mis_a_jour"] = d.get("ajoute", True)


def duree_par_photo(modele, n):
    return max(1.2, min(5.0, float(modele.get("duree", 40)) / max(1, n)))


def appliquer_presentation(projet, chemin, modele_id, params=None):
    """Modèle à photos : la présentation fabriquée devient le montage, avec la musique du projet et le titre animé."""
    from . import moteur
    m = tous(params).get(modele_id) or MODELES["photos_cartes"]
    projet.marquer()
    projet.d["format"] = m.get("format", projet.d.get("format"))
    projet.clips[:] = []
    projet.titres[:] = []
    projet.goodies[:] = []
    info = moteur.sonder(chemin)
    duree = float(info.get("duree") or 0)
    mi = projet.ajouter_media(chemin, info)
    mi["nom"] = m["nom"]
    projet.ajouter_clip(mi["id"], "video", 0.0, 0.0, duree)
    mus = next((x for x in projet.medias if x.get("genre") == "audio"), None)
    if mus:
        dm = float((mus.get("fiche") or {}).get("duree") or duree)
        c = projet.ajouter_clip(mus["id"], "audio", 0.0, 0.0, min(dm, duree))
        c["fondu_sortie"] = 1.5
    t = projet.ajouter_titre(projet.nom or m["nom"], 0.2, min(3.2, duree))
    if isinstance(t, dict):
        t["animation"] = m.get("titre", "fondu")
    projet.d["recette"] = {"modele": modele_id, "presentation": m.get("presentation")}
    projet.modifie = True
    return mi
