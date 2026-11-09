"""Eléments animés (0.9.36) : réactions, emoji, flèches qui se tracent, météo, fête, vlog… au format Lottie (dessins
vectoriels animés). Le même fichier catalogue/elements.json est lu par le PC (rlottie) et, plus tard, par Android
(lottie-android) : nets à toute taille, couleurs modifiables, sans vidéo à transparence (mal lue par certains téléphones).

Un élément posé est un Goodie de genre « lottie:<id> » : il se place, se redimensionne, suit une personne, porte des
images clefs et s'exporte comme les autres. Options : « couleurs » (liste, remplace les couleurs principales dans
l'ordre), « fin » : boucle (recommence), tenir (reste sur la dernière image) ou une_fois (disparaît à la fin).

Le catalogue est mis à jour chaque mois (veille) sans réinstaller ; il ne contient que des données, jamais de code."""
import json
import threading

from .catalogue_ligne import charger, localise
from .langue import _

FICHIER = "elements.json"
PREFIXE = "lottie:"
FINS = [("boucle", _("En boucle")), ("tenir", _("S'arrête à la fin")), ("une_fois", _("Disparaît à la fin"))]
ELEMENTS = {}              # id -> {"nom", "pack", "fin", "couleurs", "lottie", "source", "ajoute"}
_ANIMS = {}                # (id, couleurs) -> (LottieAnimation, nb_images, cadence)
_VERROU = threading.Lock()


def disponible():
    try:
        import rlottie_python  # noqa: F401
        return True
    except Exception:          # noqa: BLE001 : bibliothèque absente ou non chargeable
        return False


def raison():
    try:
        import rlottie_python  # noqa: F401
        return ""
    except Exception as e:     # noqa: BLE001
        return str(e)


def genre(ident):
    return PREFIXE + ident


def est_element(g):
    return str((g or {}).get("genre", "")).startswith(PREFIXE)


def _valide(e):
    lt = (e or {}).get("lottie")
    return isinstance(lt, dict) and isinstance(lt.get("layers"), list) and lt.get("op", 0) > 0 and lt.get("w") and lt.get("h")


def integrer(reseau=False, delai=8):
    """Ajoute les éléments du catalogue aux familles de Goodies ; renvoie la liste pour les nouveautés."""
    from . import goodies as GO
    d = charger(FICHIER, reseau, delai)
    arrives = []
    for pk_id, pk in (d.get("packs") or {}).items():
        k = "el_" + pk_id
        if k not in GO.PACKS:
            GO.PACKS[k] = {"nom": "✶ " + (localise(pk.get("nom")) or pk_id), "description": localise(pk.get("description")), "goodies": []}
    for eid, e in (d.get("elements") or {}).items():
        if not isinstance(e, dict) or not _valide(e):
            continue
        nom = localise(e.get("nom")) or eid
        ancien = ELEMENTS.get(eid)
        ELEMENTS[eid] = {"nom": nom, "pack": e.get("pack") or "divers", "fin": e.get("fin") if e.get("fin") in dict(FINS) else "boucle",
                         "couleurs": [c for c in e.get("couleurs") or [] if isinstance(c, str)], "lottie": e["lottie"],
                         "source": e.get("source", ""), "ajoute": e.get("ajoute", ""), "description": localise(e.get("description"))}
        if ancien and ancien["lottie"] != e["lottie"]:
            for cle in [c for c in _ANIMS if c[0] == eid]:
                _ANIMS.pop(cle, None)
        g = genre(eid)
        GO.GENRES[g] = (nom, "", (0, 0))
        GO.FLUIDES.add(g)
        pack = GO.PACKS.setdefault("el_" + ELEMENTS[eid]["pack"], {"nom": "✶ " + _("Eléments animés"), "description": "", "goodies": []})
        if g not in pack["goodies"]:
            pack["goodies"].append(g)
        arrives.append({"cat": "goodies", "id": g, "nom": nom, "desc": localise(GO.PACKS["el_" + ELEMENTS[eid]["pack"]].get("description")),
                        "ajoute": e.get("ajoute", "")})
    return arrives


# ------------------------------------------------------------------ couleurs
def _rvb(h):
    h = (h or "").lstrip("#")
    try:
        return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError:
        return None


def recolorer(lottie, anciennes, nouvelles):
    """Copie de l'animation où chaque couleur principale est remplacée (remplissages et traits)."""
    paires = []
    for a, n in zip(anciennes or [], nouvelles or []):
        ra, rn = _rvb(a), _rvb(n)
        if ra and rn and a.lower() != n.lower():
            paires.append((ra, rn))
    if not paires:
        return lottie
    out = json.loads(json.dumps(lottie))

    def parcourir(x):
        if isinstance(x, dict):
            if x.get("ty") in ("fl", "st") and isinstance(x.get("c"), dict) and x["c"].get("a") == 0:
                k = x["c"].get("k")
                if isinstance(k, list) and len(k) >= 3:
                    for ra, rn in paires:
                        if all(abs(k[i] - ra[i]) < 0.006 for i in range(3)):
                            x["c"]["k"] = [round(v, 4) for v in rn] + list(k[3:4] or [1])
                            break
            for v in x.values():
                parcourir(v)
        elif isinstance(x, list):
            for v in x:
                parcourir(v)
    parcourir(out)
    return out


def couleurs_de(g):
    e = ELEMENTS.get(str(g.get("genre", ""))[len(PREFIXE):]) or {}
    choisies = list((g.get("options") or {}).get("couleurs") or [])
    return [choisies[i] if i < len(choisies) and choisies[i] else c for i, c in enumerate(e.get("couleurs") or [])]


# ------------------------------------------------------------------ rendu
def _animation(ident, couleurs):
    cle = (ident, tuple(couleurs))
    a = _ANIMS.get(cle)
    if a is None:
        import rlottie_python as R
        e = ELEMENTS[ident]
        lt = recolorer(e["lottie"], e["couleurs"], couleurs)
        an = R.LottieAnimation.from_data(json.dumps(lt, separators=(",", ":")))
        a = (an, max(1, an.lottie_animation_get_totalframe()), float(an.lottie_animation_get_framerate() or 30))
        if len(_ANIMS) > 60:
            _ANIMS.clear()
        _ANIMS[cle] = a
    return a


def image_numero(g, u):
    """Numéro de l'image Lottie à u secondes du début de l'élément (None : rien à dessiner)."""
    ident = str(g.get("genre", ""))[len(PREFIXE):]
    e = ELEMENTS.get(ident)
    if not e:
        return None
    _an, n, fr = _animation(ident, couleurs_de(g))
    vitesse = float((g.get("options") or {}).get("vitesse", 1.0) or 1.0)
    i = int(max(0.0, u) * fr * vitesse)
    fin = (g.get("options") or {}).get("fin") or e["fin"]
    if fin == "tenir":
        return min(i, n - 1)
    if fin == "une_fois":
        return i if i < n else None
    return i % n


def image(g, u, taille):
    """QImage carrée transparente de l'élément à u secondes de son début ; None s'il n'y a rien à dessiner."""
    from PySide6.QtGui import QImage
    ident = str(g.get("genre", ""))[len(PREFIXE):]
    if ident not in ELEMENTS or not disponible():
        return None
    num = image_numero(g, u)
    if num is None:
        return None
    an, _n, _fr = _animation(ident, couleurs_de(g))
    taille = max(8, int(taille))
    with _VERROU:             # rlottie : une image à la fois par animation
        buf = an.lottie_animation_render(frame_num=num, width=taille, height=taille, bytes_per_line=taille * 4)
    return QImage(buf, taille, taille, taille * 4, QImage.Format_ARGB32_Premultiplied).copy()


def dessiner(p, g, t, taille):
    from . import goodies as GO
    u = float(t) - GO.bornes(g)[0]
    img = image(g, u, taille)
    if img is not None:
        p.drawImage(0, 0, img)
    elif not disponible():                # pas de moteur Lottie : un repère discret, jamais d'erreur
        from PySide6.QtCore import Qt, QRectF
        from PySide6.QtGui import QColor, QPen
        p.setPen(QPen(QColor(255, 255, 255, 160), max(1, taille // 60), Qt.DashLine))
        p.drawRoundedRect(QRectF(taille * 0.1, taille * 0.1, taille * 0.8, taille * 0.8), taille * 0.08, taille * 0.08)


def duree(ident):
    e = ELEMENTS.get(ident)
    if not e:
        return 3.0
    lt = e["lottie"]
    return (lt.get("op", 90) - lt.get("ip", 0)) / float(lt.get("fr", 30) or 30)
