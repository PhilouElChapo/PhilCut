"""Étalonnage simple (0.9.28) : exposition, contraste, saturation, température, teinte, et trois roues de couleur
(ombres, tons moyens, hautes lumières), comme les roues de Premiere ou de DaVinci, sans leur complexité. Le tout devient
une chaîne de filtres FFmpeg (eq, colortemperature, colorbalance), la même à l'aperçu et à l'export.

« Auto » corrige une dominante de couleur et des niveaux ternes ; « Accorder » donne à un plan la lumière et les
couleurs d'un autre (deux caméras, deux heures de la journée)."""
import math

CLEFS = ("exposition", "contraste", "saturation", "temperature", "teinte",
         "ombres_x", "ombres_y", "moyens_x", "moyens_y", "hautes_x", "hautes_y")
K = 0.25                    # amplitude d'une roue poussée au bord (colorbalance va de -1 à 1)


def neutre():
    return {k: 0.0 for k in CLEFS}


def roue_vers_rvb(x, y):
    """Position de la pastille (x, y dans le disque unité) → décalage (r, v, b), de somme nulle."""
    r = min(1.0, math.hypot(x, y))
    if r < 1e-4:
        return 0.0, 0.0, 0.0
    th = math.atan2(y, x)
    return tuple(K * r * math.cos(th - d) for d in (0.0, 2 * math.pi / 3, -2 * math.pi / 3))


def rvb_vers_roue(o):
    """Décalage (r, v, b) → position de la pastille (la composante grise est ignorée)."""
    r, v, b = o
    x = (r - 0.5 * (v + b)) / (1.5 * K)
    y = (math.sqrt(3) / 2) * (v - b) / (1.5 * K)
    n = math.hypot(x, y)
    if n > 1:
        x, y = x / n, y / n
    return x, y


def filtre(p):
    """Chaîne FFmpeg ; chaîne vide si tout est neutre."""
    g = {k: float((p or {}).get(k, 0.0) or 0.0) for k in CLEFS}
    out = []
    if any(abs(g[k]) > 1e-3 for k in ("exposition", "contraste", "saturation")):
        e = g["exposition"]
        out.append(f"eq=brightness={0.10 * e:.4f}:gamma={max(0.3, 1 + 0.45 * e):.4f}:contrast={max(0.2, 1 + 0.6 * g['contraste']):.4f}"
                   f":saturation={max(0.0, 1 + g['saturation']):.4f}")
    if abs(g["temperature"]) > 1e-3:
        out.append(f"colortemperature=temperature={int(6500 - 3500 * g['temperature'])}:mix=0.8")
    o = [roue_vers_rvb(g["ombres_x"], g["ombres_y"]), roue_vers_rvb(g["moyens_x"], g["moyens_y"]), roue_vers_rvb(g["hautes_x"], g["hautes_y"])]
    t = g["teinte"]                                         # teinte : + magenta, - vert (sur les tons moyens)
    o[1] = (o[1][0] + 0.06 * t, o[1][1] - 0.12 * t, o[1][2] + 0.06 * t)
    if any(abs(c) > 1e-3 for trio in o for c in trio):
        noms = (("rs", "gs", "bs"), ("rm", "gm", "bm"), ("rh", "gh", "bh"))
        parts = [f"{n}={max(-1, min(1, c)):.4f}" for trio, ns in zip(o, noms) for c, n in zip(trio, ns) if abs(c) > 1e-4]
        out.append("colorbalance=" + ":".join(parts))
    return ",".join(out)


# ---------------------------------------------------------------- mesures sur une image (numpy, tableau H×L×3 en 0-255)
def mesures(img):
    import numpy as np
    a = np.asarray(img, dtype=np.float32) / 255.0
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    sombres, claires = lum < np.percentile(lum, 30), lum > np.percentile(lum, 70)
    moy = lambda m: a[m].mean(axis=0) if m.any() else a.reshape(-1, 3).mean(axis=0)
    mx, mn = a.max(axis=2), a.min(axis=2)
    return {"lum": float(lum.mean()), "ecart": float(lum.std()), "p2": float(np.percentile(lum, 2)), "p98": float(np.percentile(lum, 98)),
            "moyenne": a.reshape(-1, 3).mean(axis=0).tolist(), "ombres": moy(sombres).tolist(), "hautes": moy(claires).tolist(),
            "sat": float(((mx - mn) / np.maximum(mx, 1e-3)).mean())}


def _dominante(rvb):
    m = sum(rvb) / 3
    return tuple(c - m for c in rvb)


def auto(img):
    """Réglages qui retirent la dominante (monde gris) et étirent des niveaux ternes."""
    s = mesures(img)
    p = neutre()
    for zone, cle in (("ombres", "ombres"), ("moyenne", "moyens"), ("hautes", "hautes")):
        d = _dominante(s[zone])
        x, y = rvb_vers_roue(tuple(-c * 0.9 for c in d))
        p[cle + "_x"], p[cle + "_y"] = round(x, 3), round(y, 3)
    etendue = max(0.05, s["p98"] - s["p2"])
    if etendue < 0.85:
        p["contraste"] = round(min(0.6, (0.9 / etendue - 1) * 0.5), 3)
    p["exposition"] = round(max(-0.6, min(0.6, (0.46 - s["lum"]) * 1.6)), 3)
    return p


def accorder(img, ref):
    """Réglages qui donnent à img la lumière et les couleurs de ref."""
    a, b = mesures(img), mesures(ref)
    p = neutre()
    p["exposition"] = round(max(-1, min(1, (b["lum"] - a["lum"]) * 1.8)), 3)
    if a["ecart"] > 1e-3:
        p["contraste"] = round(max(-0.8, min(0.8, (b["ecart"] / a["ecart"] - 1) / 0.6)), 3)
    if a["sat"] > 1e-3:
        p["saturation"] = round(max(-0.9, min(1.0, b["sat"] / a["sat"] - 1)), 3)
    for zone, cle in (("ombres", "ombres"), ("moyenne", "moyens"), ("hautes", "hautes")):
        da, db = _dominante(a[zone]), _dominante(b[zone])
        x, y = rvb_vers_roue(tuple((cb - ca) * 0.9 for ca, cb in zip(da, db)))
        p[cle + "_x"], p[cle + "_y"] = round(x, 3), round(y, 3)
    return p


def appliquer(clip, reglages):
    """Pose (ou remplace) l'effet « etalonnage » sur le plan ; le retire si tout est neutre."""
    effets = [e for e in clip.get("effets") or [] if e["id"] != "etalonnage"]
    if filtre(reglages):
        effets.insert(0, {"id": "etalonnage", "params": {k: float(reglages.get(k, 0.0)) for k in CLEFS}})
    clip["effets"] = effets
    return clip


def reglages_de(clip):
    e = next((e for e in clip.get("effets") or [] if e["id"] == "etalonnage"), None)
    p = neutre()
    if e:
        p.update({k: float(v) for k, v in (e.get("params") or {}).items() if k in CLEFS})
    return p
