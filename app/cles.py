"""Images clefs (0.3.4) : une incrustation, un texte ou un Goodie qui bouge, grossit ou s'efface dans le temps.

Une image clef fixe les réglages à un instant : {"t": secondes depuis le début de l'élément, "x": .., "y": .., ...}.
Entre deux images clefs, les valeurs passent de l'une à l'autre en ligne droite ; avant la première et après la
dernière, elles restent fixes. Sans image clef, l'élément garde ses réglages fixes (comme avant).

Règle d'usage : dès qu'un élément a une image clef, chaque réglage fait à la ligne rouge (curseur de l'Inspecteur,
glisser dans l'image) pose ou modifie l'image clef de cet instant. Les losanges ◆ sur la timeline les montrent.
"""
from .projet import fin_clip

PROPRIETES = {
    "incrustation": [("echelle", 1.0), ("x", 0.5), ("y", 0.5), ("opacite", 1.0)],
    "texte": [("x", 0.5), ("y", 0.85), ("taille", 1.0), ("opacite", 1.0)],
    "goodie": [("x", 0.88), ("y", 0.85), ("angle", 0.0)],
}
TOLERANCE = 0.04            # deux images clefs plus proches que cela sont la même


def genre(elem):
    if "media" in elem and "piste" in elem:
        return "incrustation"
    if "texte" in elem and "genre" not in elem:
        return "texte"
    return "goodie"


def base(elem):
    """Instant (montage) où commence l'élément : les images clefs sont comptées depuis là."""
    return float(elem["debut"])


def duree(elem):
    return (fin_clip(elem) if genre(elem) == "incrustation" else float(elem["fin"])) - float(elem["debut"])


def fixes(elem):
    """Les réglages fixes de l'élément (sans images clefs)."""
    g = genre(elem)
    src = (elem.get("incrust") or {}) if g == "incrustation" else elem
    v = {k: float(src.get(k, d) if src.get(k) is not None else d) for k, d in PROPRIETES[g] if k != "angle"}
    if g == "goodie":          # l'angle d'un Goodie (flèche, bandeau, post-it…) est rangé dans ses options
        o = elem.get("options") or {}
        v["angle"] = float(o.get("angle", 0.0) or 0.0)
    return v


def liste(elem):
    return sorted(elem.get("cles") or [], key=lambda c: c["t"])


def valeurs(elem, t_rel):
    """Toutes les valeurs à l'instant t_rel (secondes depuis le début de l'élément)."""
    v = fixes(elem)
    cl = liste(elem)
    if not cl:
        return v
    for k in v:
        pts = [(c["t"], c[k]) for c in cl if k in c]
        if not pts:
            continue
        if t_rel <= pts[0][0]:
            v[k] = pts[0][1]
        elif t_rel >= pts[-1][0]:
            v[k] = pts[-1][1]
        else:
            for (ta, va), (tb, vb) in zip(pts, pts[1:]):
                if ta <= t_rel <= tb:
                    v[k] = va + (vb - va) * (t_rel - ta) / max(1e-6, tb - ta)
                    break
    return v


def valeurs_a(elem, t_montage):
    return valeurs(elem, t_montage - base(elem))


def a_cle(elem, t_rel):
    return next((c for c in liste(elem) if abs(c["t"] - t_rel) <= TOLERANCE), None)


def poser(elem, t_rel, **changes):
    """Pose (ou modifie) l'image clef à t_rel : elle prend les valeurs actuelles à cet instant, plus les changements."""
    t_rel = round(max(0.0, min(duree(elem), t_rel)), 3)
    c = a_cle(elem, t_rel)
    if c is None:
        c = dict(valeurs(elem, t_rel), t=t_rel)
        elem.setdefault("cles", []).append(c)
    for k, v in changes.items():
        c[k] = round(float(v), 4)
    elem["cles"] = liste(elem)
    return c


def retirer(elem, t_rel):
    c = a_cle(elem, t_rel)
    if c is not None:
        elem["cles"] = [x for x in liste(elem) if x is not c]
        if not elem["cles"]:
            elem.pop("cles", None)
    return c is not None


def regler(elem, t_montage, **changes):
    """Un réglage fait par l'utilisateur à la ligne rouge : image clef si l'élément est animé, sinon réglage fixe."""
    if elem.get("cles"):
        poser(elem, t_montage - base(elem), **changes)
        return True
    if genre(elem) == "incrustation":
        elem.setdefault("incrust", {}).update({k: round(float(v), 4) for k, v in changes.items()})
    elif genre(elem) == "goodie" and "angle" in changes:
        elem.setdefault("options", {})["angle"] = round(float(changes.pop("angle")), 2)
        elem.update({k: round(float(v), 4) for k, v in changes.items()})
    else:
        elem.update({k: round(float(v), 4) for k, v in changes.items()})
    return False


def voisine(elem, t_rel, sens):
    """Instant (relatif) de l'image clef précédente (sens -1) ou suivante (+1), ou None."""
    ts = [c["t"] for c in liste(elem)]
    if sens < 0:
        avant = [t for t in ts if t < t_rel - TOLERANCE]
        return avant[-1] if avant else None
    apres = [t for t in ts if t > t_rel + TOLERANCE]
    return apres[0] if apres else None


def decaler(elem, delta, duree_nouvelle):
    """Le début de l'élément a avancé de delta (coupe, extrait) : les images clefs suivent, en gardant la valeur au
    nouveau début s'il en tombe une avant."""
    cl = liste(elem)
    if not cl:
        return
    v0 = valeurs(elem, delta)
    v1 = valeurs(elem, delta + duree_nouvelle)
    out = [dict(c, t=round(c["t"] - delta, 3)) for c in cl if delta - 1e-6 <= c["t"] <= delta + duree_nouvelle + 1e-6]
    if not out or out[0]["t"] > TOLERANCE:
        out.insert(0, dict(v0, t=0.0))
    if out[-1]["t"] < duree_nouvelle - TOLERANCE:
        out.append(dict(v1, t=round(duree_nouvelle, 3)))
    elem["cles"] = out


# ------------------------------------------------------------------ export
def expr(elem, k, decalage=0.0, var="t"):
    """Valeur de la propriété k en expression FFmpeg du temps du montage (morceaux linéaires)."""
    from . import suivi
    cl = liste(elem)
    v = fixes(elem)[k]
    pts = [(c["t"] + base(elem) - decalage, c[k]) for c in cl if k in c]
    if not pts:
        return f"{v:.4f}"
    return suivi.expr(pts, var)


def commandes_echelle_opacite(elem, iw, ih, nom_scale, nom_mix, cadence=25):
    """Lignes d'un fichier sendcmd qui font varier la taille (filtre scale nommé) et l'opacité (colorchannelmixer
    nommé) d'une incrustation, deux fois par image ; temps du montage."""
    lignes = []
    d0 = base(elem)
    pas = 2.0 / max(1, cadence)
    n = int(duree(elem) / pas) + 2
    derniere = None
    for i in range(n):
        tr = min(duree(elem), i * pas)
        v = valeurs(elem, tr)
        e = max(0.02, min(1.0, v["echelle"]))
        w, h = max(2, int(iw * e) // 2 * 2), max(2, int(ih * e) // 2 * 2)
        a = max(0.0, min(1.0, v["opacite"]))
        cle = (w, h, round(a, 3))
        if cle == derniere:
            continue
        derniere = cle
        cmd = [f"[enter] {nom_scale} w {w}", f"[enter] {nom_scale} h {h}"]
        if nom_mix:
            cmd.append(f"[enter] {nom_mix} aa {a:.3f}")
        lignes.append(f"{d0 + tr:.3f} " + ", ".join(cmd) + ";")
    return lignes


def angle_goodie(g, t_montage):
    """Angle (°) d'un Goodie à cet instant : animé par les images clefs s'il en a, sinon celui de ses options."""
    if g.get("cles") and any("angle" in c for c in g["cles"]):
        return float(valeurs_a(g, t_montage)["angle"])
    return float((g.get("options") or {}).get("angle", 0.0) or 0.0)
