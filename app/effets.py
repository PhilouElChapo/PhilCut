"""Catalogue des effets de PhilCut et leur traduction en filtres FFmpeg.

Un effet est pose sur un clip : {"id": "glow", "params": {...}}. A l'export, `filtre(effet, contexte)` renvoie
la chaine de filtres video (ou None si l'effet est un calque genere : voir generateurs.py).

Le catalogue (CATALOGUE) est ce que l'on voit dans le volet Effets : famille, nom, description, parametres
reglables, et `pack` quand l'effet demande un telechargement (modele IA, images) qu'on coche pour l'obtenir.
Il est complete en ligne (catalogue_en_ligne) sans reinstaller.
"""
from .langue import _

FAMILLES = [
    ("look", _("Look et couleur")),
    ("wahou", _("Effets wahou")),
    ("mouvement", _("Vitesse et mouvement")),
    ("transition", _("Transitions")),
    ("personne", _("Sur une personne (IA)")),
    ("matrix", _("Matrix")),
    ("correction", _("Corrections")),
]

# id : famille, nom, description, parametres [(cle, libelle, type, defaut, min, max)], pack (None = livre avec PhilCut)
CATALOGUE = {
    # ---- look
    "ciel_altitude": ("look", _("Ciel et altitude"), _("Etalonnage aviation : ciel profond, contraste doux, bleus purs."),
                      [("force", _("Force"), "float", 1.0, 0.0, 2.0)], None),
    "nuit_chaude": ("look", _("Nuit chaude"), _("Eclaircit et débruite une vidéo de nuit, tons chauds pour les lumières."),
                    [("force", _("Force"), "float", 1.0, 0.0, 2.0)], None),
    "cinema": ("look", _("Cinéma"), _("Grain léger, bandes noires, contraste de film."),
               [("bandes", _("Bandes noires"), "bool", True, 0, 1), ("grain", _("Grain"), "float", 0.3, 0.0, 1.0)], None),
    "vintage": ("look", _("Vintage"), _("Couleurs passées, vignettage, un peu de grain."), [], None),
    "noir_blanc": ("look", _("Noir et blanc"), _("Noir et blanc contrasté."), [], None),
    "y2k": ("look", _("Y2K"), _("Saturé, lumineux, légère aberration colorée : le style des années 2000."), [], None),
    "cosy": ("look", _("Cosy"), _("Doux, chaud, contraste bas."), [], None),
    "epure": ("look", _("Epuré"), _("Clair, propre, blancs lumineux."), [], None),
    # ---- wahou
    "glow": ("wahou", _("Glow"), _("Lumière diffuse : les hautes lumières rayonnent, rendu rêveur."),
             [("rayon", _("Rayon"), "float", 12.0, 2.0, 40.0), ("intensite", _("Intensité"), "float", 0.6, 0.1, 1.0)], None),
    "glitch": ("wahou", _("Glitch numérique"), _("Décalage des couleurs, bruit, scintillement : interférences."),
               [("force", _("Force"), "float", 1.0, 0.2, 3.0)], None),
    "double_exposition": ("wahou", _("Double exposition"), _("Superpose un autre plan ou une image en transparence."),
                          [("media", _("Image ou vidéo à superposer"), "media", "", 0, 0), ("opacite", _("Opacité"), "float", 0.5, 0.1, 0.9)], None),
    "chroma_key": ("wahou", _("Fond vert (chroma key)"), _("Détoure sur fond uni et pose le sujet sur un autre décor."),
                   [("media", _("Nouveau décor"), "media", "", 0, 0), ("couleur", _("Couleur du fond"), "couleur", "#00ff00", 0, 0),
                    ("tolerance", _("Tolérance"), "float", 0.3, 0.05, 0.6)], None),
    "fuite_lumiere": ("wahou", _("Fuite de lumière"), _("Voile lumineux chaud qui traverse l'image."),
                      [("force", _("Force"), "float", 0.6, 0.1, 1.0)], None),
    "separation_rvb": ("wahou", _("Séparation RVB"), _("Les trois couleurs se décalent puis se rejoignent."),
                       [("force", _("Force"), "float", 1.0, 0.2, 3.0)], None),
    "feu_artifice": ("wahou", _("Feu d'artifice"), _("Gerbes de particules sur l'image (ou derrière la personne avec le pack IA)."),
                     [("quantite", _("Quantité"), "int", 6, 1, 20)], None),
    "eclairs": ("wahou", _("Eclairs"), _("Eclairs brefs et flashs."), [("quantite", _("Quantité"), "int", 4, 1, 12)], None),
    # ---- mouvement
    "flou_mouvement": ("mouvement", _("Flou de mouvement"), _("Rend les mouvements et les textes animés plus fluides."),
                       [("images", _("Images mélangées"), "int", 4, 2, 8)], None),
    "ralenti_fluide": ("mouvement", _("Ralenti fluide"), _("Images intermédiaires calculées : ralenti sans saccades (lent à exporter)."),
                       [], None),
    "stabiliser": ("correction", _("Stabiliser"), _("Supprime les tremblements d'un plan filmé à la main."),
                   [("force", _("Lissage"), "int", 10, 2, 30)], None),
    "hyperlapse": ("mouvement", _("Hyperlapse"), _("Accélération forte et stabilisée d'une phase longue."),
                   [("facteur", _("Facteur"), "int", 8, 2, 32)], None),
    # ---- corrections
    "debruiter": ("correction", _("Débruiter"), _("Réduit le grain des vidéos sombres."), [("force", _("Force"), "float", 1.0, 0.2, 3.0)], None),
    "eclaircir": ("correction", _("Eclaircir"), _("Remonte les basses lumières sans brûler les hautes."), [("force", _("Force"), "float", 1.0, 0.2, 2.0)], None),
    "nettete": ("correction", _("Netteté"), _("Accentue les détails d'un clip un peu mou (clips IA, proxys)."), [("force", _("Force"), "float", 0.8, 0.2, 2.0)], None),
    "horizon": ("correction", _("Redresser l'horizon"), _("Pivote légèrement l'image."), [("angle", _("Angle (°)"), "float", 0.0, -15.0, 15.0)], None),
    # ---- transitions (posees sur le clip qui ARRIVE ; sans changement de duree)
    "t_fondu_noir": ("transition", _("Fondu au noir"), _("Sortie au noir puis entrée du plan suivant."), [("duree", _("Durée (s)"), "float", 0.6, 0.2, 2.0)], None),
    "t_fondu_blanc": ("transition", _("Flash blanc"), _("Eclair blanc à la coupe."), [("duree", _("Durée (s)"), "float", 0.4, 0.1, 1.0)], None),
    "t_puzzle": ("transition", _("Puzzle"), _("Le plan arrive en morceaux inclinés qui se rassemblent puis zooment."),
                 [("pieces", _("Morceaux"), "int", 4, 2, 9), ("duree", _("Durée (s)"), "float", 1.2, 0.5, 3.0)], None),
    "t_explosion": ("transition", _("Explosion d'images"), _("Le plan précédent éclate en fragments."),
                    [("pieces", _("Morceaux"), "int", 16, 4, 36), ("duree", _("Durée (s)"), "float", 1.0, 0.4, 2.5)], None),
    "t_glitch": ("transition", _("Glitch"), _("Interférences brèves à la coupe."), [("duree", _("Durée (s)"), "float", 0.4, 0.1, 1.0)], None),
    "t_zoom": ("transition", _("Zoom"), _("Zoom rapide vers l'avant à la coupe."), [("duree", _("Durée (s)"), "float", 0.5, 0.2, 1.5)], None),
    "t_balayage": ("transition", _("Balayage"), _("Un volet traverse l'image."), [("duree", _("Durée (s)"), "float", 0.5, 0.2, 1.5)], None),
    "t_code": ("transition", _("Dissolution en code"), _("L'image se dissout en caractères verts (Matrix)."), [("duree", _("Durée (s)"), "float", 1.0, 0.4, 2.5)], None),
    # ---- transitions « fusion » : les deux plans se mélangent (FFmpeg xfade) ; la fin du plan précédent se prolonge
    #      pendant la transition (images suivantes du rush, ou dernière image figée) : la durée du montage ne change pas
    "t_fondu_enchaine": ("transition", _("Fondu enchaîné"), _("Les deux plans se mélangent en douceur."), [("duree", _("Durée (s)"), "float", 0.8, 0.2, 3.0)], None),
    "t_dissolution": ("transition", _("Dissolution"), _("Le plan suivant apparaît par petits points."), [("duree", _("Durée (s)"), "float", 0.8, 0.2, 3.0)], None),
    "t_glisse": ("transition", _("Glissé"), _("Le plan suivant pousse le précédent vers la gauche."), [("duree", _("Durée (s)"), "float", 0.6, 0.2, 2.0)], None),
    "t_cercle": ("transition", _("Cercle"), _("Le plan suivant s'ouvre en cercle depuis le centre."), [("duree", _("Durée (s)"), "float", 0.8, 0.2, 2.0)], None),
    "t_pixels": ("transition", _("Pixels"), _("L'image se pixellise puis se reforme sur le plan suivant."), [("duree", _("Durée (s)"), "float", 0.7, 0.2, 2.0)], None),
    "t_flou_fondu": ("transition", _("Fondu flou"), _("Passage flou et lumineux d'un plan à l'autre."), [("duree", _("Durée (s)"), "float", 0.7, 0.2, 2.0)], None),
    "t_diagonale": ("transition", _("Diagonale"), _("Le plan suivant arrive en biais depuis un coin."), [("duree", _("Durée (s)"), "float", 0.6, 0.2, 2.0)], None),
    # ---- personne (IA)
    "halo": ("personne", _("Halo"), _("Aura lumineuse autour de la personne détourée."),
             [("couleur", _("Couleur"), "couleur", "#ffd36b", 0, 0), ("force", _("Force"), "float", 1.0, 0.2, 2.0)], "segmentation"),
    "feu_artifice_derriere": ("personne", _("Feu d'artifice derrière"), _("Les gerbes passent derrière la personne."),
                              [("quantite", _("Quantité"), "int", 6, 1, 20)], "segmentation"),
    "detourage": ("personne", _("Changer le fond (détourage)"),
                  _("Enlève le fond sans fond vert et pose la personne sur un autre décor : une image ou une vidéo du projet "
                    "(un plan généré par la Fabrique, par exemple), le fond d'origine flouté, ou une couleur."),
                  [("fond", _("Nouveau fond"), "choix", "media", [("media", _("Image ou vidéo du projet")), ("flou", _("Fond d'origine flouté")),
                                                                   ("couleur", _("Couleur unie"))], 0),
                   ("media", _("Image ou vidéo"), "media", "", 0, 0), ("couleur", _("Couleur"), "couleur", "#1d2b3a", 0, 0),
                   ("adoucir", _("Bords adoucis"), "float", 1.0, 0.0, 4.0)], "segmentation"),
    "code_personne": ("matrix", _("Personne en code"), _("La silhouette se remplit de caractères qui défilent puis redevient réelle."),
                      [("duree", _("Durée (s)"), "float", 2.0, 0.5, 6.0)], "segmentation"),
    # ---- matrix
    "pluie_code": ("matrix", _("Pluie de code"), _("Caractères verts qui tombent en surimpression."),
                   [("densite", _("Densité"), "float", 1.0, 0.2, 3.0), ("opacite", _("Opacité"), "float", 0.7, 0.1, 1.0)], None),
    "matrix_vert": ("matrix", _("Etalonnage Matrix"), _("Vert numérique, contraste fort."), [], None),
    "bullet_time": ("matrix", _("Bullet time"), _("Image figée avec traînées et ralenti extrême."), [("duree", _("Durée (s)"), "float", 1.5, 0.5, 4.0)], None),
}

# Packs a telecharger (cases a cocher dans Preferences > Effets) : nom, description, taille indicative, comment l'obtenir
PACKS = {
    "segmentation": {"nom": _("Détourage de personne (IA locale)"), "taille": "≈ 5 à 170 Mo",
                     "description": _("Modèle qui sépare la personne du fond, sur ce poste, sans envoi. Nécessaire aux effets « sur une personne »."),
                     "ia": "detourage"},
    "whisper": {"nom": _("Sous-titres automatiques (Whisper local)"), "taille": "≈ 150 Mo à 600 Mo selon le modèle",
                "description": _("Transcrit la voix sur ce poste pour les sous-titres et l'assistant."), "ia": "whisper"},
    "suivi": {"nom": _("Suivi d'objet avancé"), "taille": "≈ 60 Mo", "description": _("Suivi plus robuste (CSRT) pour les étiquettes accrochées."),
              "pip": ["opencv-contrib-python-headless"]},
}

GENERES = {"feu_artifice", "eclairs", "fuite_lumiere", "t_puzzle", "t_explosion", "t_glitch", "t_balayage", "t_code",
           "pluie_code", "halo", "feu_artifice_derriere", "code_personne", "detourage"}


def pack_pret(cle, params=None):
    """Le pack demandé par un effet est-il prêt sur ce poste ?"""
    p = PACKS.get(cle) or {}
    if p.get("ia"):
        from . import packs_ia
        return packs_ia.modele_actif(p["ia"], params) is not None
    return cle in set((params or {}).get("effets_coches") or [])


def actif(effet):
    """Un effet ou une transition désactivé (case décochée dans l'Inspecteur) reste posé mais ne s'applique pas."""
    return bool(effet) and effet.get("actif", True)


def actifs(clip):
    """Effets vidéo actifs d'un plan, dans l'ordre."""
    return [e for e in (clip.get("effets") or []) if actif(e)]


def transition_active(clip):
    t = clip.get("transition")
    return t if actif(t) else None


def fiche(ident):
    e = CATALOGUE.get(ident)
    if not e:
        return None
    return {"id": ident, "famille": e[0], "nom": e[1], "description": e[2], "parametres": e[3], "pack": e[4], "genere": ident in GENERES}


def defauts(ident):
    e = CATALOGUE.get(ident)
    return {p[0]: p[3] for p in e[3]} if e else {}


def par_famille():
    out = {f: [] for f, _n in FAMILLES}
    for k, e in CATALOGUE.items():
        out.setdefault(e[0], []).append(k)
    return out


def _p(effet, cle):
    d = defauts(effet["id"])
    d.update(effet.get("params") or {})
    return d.get(cle)


def filtre(effet, ctx=None):
    """Chaine de filtres FFmpeg pour un effet « simple » (applique dans la chaine du clip). None pour un calque genere.
    ctx : {"cadence": 30, "largeur": .., "hauteur": .., "duree": duree du clip, "debut": position timeline}"""
    i = effet["id"]
    f = lambda k: float(_p(effet, k))
    ctx = ctx or {}
    if i == "ciel_altitude":
        s = f("force")
        return f"eq=saturation={1 + 0.25 * s:.3f}:contrast={1 + 0.08 * s:.3f},colorbalance=bs={0.08 * s:.3f}:gm={0.03 * s:.3f}:rh={-0.03 * s:.3f}"
    if i == "nuit_chaude":
        s = f("force")
        return (f"eq=brightness={0.06 * s:.3f}:gamma={1 + 0.3 * s:.3f}:saturation={1 + 0.1 * s:.3f},"
                f"colorbalance=rs={0.05 * s:.3f}:bs={-0.05 * s:.3f},hqdn3d={4 * s:.1f}:{3 * s:.1f}:{6 * s:.1f}:{4 * s:.1f}")
    if i == "cinema":
        out = ["eq=contrast=1.1:saturation=0.9", f"noise=alls={int(12 * f('grain'))}:allf=t"]
        if _p(effet, "bandes"):
            h = int(ctx.get("hauteur") or 1080)
            out.append(f"drawbox=y=0:w=iw:h={int(h * 0.12)}:c=black:t=fill,drawbox=y=ih-{int(h * 0.12)}:w=iw:h={int(h * 0.12)}:c=black:t=fill")
        return ",".join(out)
    if i == "vintage":
        return "curves=preset=vintage,vignette=PI/4,noise=alls=8:allf=t"
    if i == "noir_blanc":
        return "hue=s=0,eq=contrast=1.15"
    if i == "y2k":
        return "eq=saturation=1.5:brightness=0.04:contrast=1.05,rgbashift=rh=2:bh=-2"
    if i == "cosy":
        return "eq=contrast=0.92:saturation=1.05:brightness=0.03,colorbalance=rs=0.06:gs=0.02:bs=-0.04"
    if i == "epure":
        return "eq=brightness=0.05:contrast=1.02:saturation=0.95,curves=lighter"
    if i == "glow":
        r, a = f("rayon"), f("intensite")
        return f"split[g0][g1];[g1]gblur=sigma={r:.1f}[g1];[g0][g1]blend=all_mode=screen:all_opacity={a:.2f}"
    if i == "glitch":
        s = f("force")
        return f"rgbashift=rh={int(6 * s)}:bh={int(-6 * s)}:gv={int(2 * s)},noise=alls={int(18 * s)}:allf=t+u,tblend=all_mode=lighten:all_opacity=0.25"
    if i == "separation_rvb":
        s = f("force")
        return f"rgbashift=rh={int(10 * s)}:bh={int(-10 * s)}"
    if i == "flou_mouvement":
        n = int(_p(effet, "images"))
        return f"tmix=frames={n}"
    if i == "ralenti_fluide":
        return f"minterpolate=fps={int(ctx.get('cadence') or 30)}:mi_mode=mci:mc_mode=aobmc:vsbmc=1"
    if i == "hyperlapse":
        n = int(_p(effet, "facteur"))
        return f"setpts=PTS/{n},deshake"
    if i == "stabiliser":
        return f"deshake=rx=32:ry=32:blocksize=8"
    if i == "debruiter":
        s = f("force")
        return f"hqdn3d={4 * s:.1f}:{3 * s:.1f}:{6 * s:.1f}:{4 * s:.1f}"
    if i == "eclaircir":
        s = f("force")
        return f"eq=gamma={1 + 0.35 * s:.3f}:brightness={0.04 * s:.3f}"
    if i == "nettete":
        s = f("force")
        return f"unsharp=5:5:{0.8 * s:.2f}:5:5:0"
    if i == "horizon":
        a = f("angle")
        return f"rotate={a}*PI/180:ow=iw:oh=ih:c=black@0,crop=iw*0.94:ih*0.94,scale={int(ctx.get('largeur') or 1920)}:{int(ctx.get('hauteur') or 1080)}"
    if i == "matrix_vert":
        return "colorchannelmixer=.2:.6:.2:0:.3:.7:.3:0:.1:.4:.1,eq=contrast=1.25:brightness=-0.03"
    if i == "t_fondu_noir":
        d = f("duree")
        return f"fade=t=in:st=0:d={d:.2f}"
    if i == "t_fondu_blanc":
        d = f("duree")
        return f"fade=t=in:st=0:d={d:.2f}:c=white"
    if i == "t_zoom":
        d = max(0.1, f("duree"))
        L, H = int(ctx.get("largeur") or 1920), int(ctx.get("hauteur") or 1080)
        cad = int(ctx.get("cadence") or 30)
        n = max(1, int(d * cad))
        return (f"zoompan=z='if(lt(on,{n}),1.4-0.4*on/{n},1)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={L}x{H}:fps={cad}")
    if i == "bullet_time":
        return "tmix=frames=6,eq=contrast=1.15:saturation=0.85"
    return None


XFADE = {"t_fondu_enchaine": "fade", "t_dissolution": "dissolve", "t_glisse": "slideleft", "t_cercle": "circleopen",
         "t_pixels": "pixelize", "t_flou_fondu": "hblur", "t_diagonale": "diagbr"}


def fusion(effet):
    """(nom xfade, durée) pour une transition « fusion », sinon None."""
    if not effet or effet.get("id") not in XFADE:
        return None
    return XFADE[effet["id"]], max(0.1, float(_p(effet, "duree")))


def filtre_sortie_transition(effet):
    """Pour le clip PRECEDENT : la sortie au noir / au blanc qui precede l'entree."""
    i = effet["id"]
    d = float(_p(effet, "duree"))
    if i == "t_fondu_noir":
        return f"fade=t=out:st=max(0\\,{{fin}}-{d:.2f}):d={d:.2f}"
    if i == "t_fondu_blanc":
        return f"fade=t=out:st=max(0\\,{{fin}}-{d:.2f}):d={d:.2f}:c=white"
    return None


def filtre_audio(effet, ctx=None):
    i = effet["id"]
    d = float(_p(effet, "duree")) if "duree" in defauts(i) else 0.0
    if i in ("t_fondu_noir",):
        return f"afade=t=in:st=0:d={d:.2f}"
    return None


# ------------------------------------------------------------------ catalogue en ligne
URL_CATALOGUE = "https://raw.githubusercontent.com/PhilouElChapo/PhilCut/main/catalogue/effets.json"


def catalogue_en_ligne(delai=10):
    """Effets et packs ajoutes depuis la publication : fusionnes au catalogue local. Jamais bloquant."""
    import json, urllib.request
    try:
        with urllib.request.urlopen(URL_CATALOGUE, timeout=delai) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception:
        return 0
    n = 0
    for k, e in (d.get("effets") or {}).items():
        if k not in CATALOGUE and isinstance(e, dict) and e.get("ffmpeg"):
            CATALOGUE[k] = (e.get("famille", "wahou"), e.get("nom", k), e.get("description", ""), [], e.get("pack"))
            _EN_LIGNE[k] = e["ffmpeg"]
            n += 1
    for k, p in (d.get("packs") or {}).items():
        PACKS.setdefault(k, p)
    return n


_EN_LIGNE = {}


def filtre_en_ligne(ident):
    return _EN_LIGNE.get(ident)
