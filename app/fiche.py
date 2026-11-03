"""La fiche video : ce que PhilCut comprend d'un rush, en local et gratuitement.

Duree, format, cadence reelle, rotation, HDR, son (niveau, muet, silences), luminosite dans le temps (nuit,
passages noirs), coupes, moments forts, couleurs dominantes, visages, texte lu dans l'image (si l'OCR est la),
date, lieu (GPS), appareil, et quelques vignettes clefs. C'est cette fiche, compacte, que l'assistant lit et
que l'on envoie a l'IA a la place de la video entiere.
"""
import datetime, json, os

from . import moteur

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None


def analyser(chemin, params=None, progression=None, vignettes=10, rapide=False):
    def prog(f, t=""):
        if progression:
            progression(f, t)
    prog(0.02, "fiche technique")
    f = moteur.sonder(chemin)
    fiche = {"chemin": chemin, "nom": os.path.basename(chemin), "duree": round(f["duree"], 2), "genre": f["genre"],
             "format": _format(f), "vertical": f.get("vertical"), "video": f.get("video"), "son": {}, "date": _date(f),
             "heure": _heure(f), "gps": f.get("gps"), "appareil": f.get("appareil"), "coupes": [], "lumiere": {}, "moments": [],
             "couleurs": [], "visages": {}, "textes": [], "vignettes": []}
    if f["genre"] != "video":
        return fiche
    d = f["duree"] or 1
    # ---- son
    prog(0.1, "son")
    niv = moteur.niveaux(chemin) if f.get("audio") else {"moyen": -91, "max": -91, "muet": True}
    fiche["son"] = {"muet": niv["muet"], "moyen_db": round(niv["moyen"], 1), "max_db": round(niv["max"], 1), "sature": niv["max"] > -0.5}
    if not niv["muet"] and not rapide:
        sil = moteur.silences(chemin, -40, 1.0)
        fiche["son"]["silences"] = [(round(a, 1), round(b, 1)) for a, b in sil[:40]]
        fiche["son"]["part_silence"] = round(sum(b - a for a, b in sil) / d, 2)
        fiche["son"]["voix_probable"] = niv["moyen"] > -35 and fiche["son"]["part_silence"] < 0.7
    # ---- coupes
    prog(0.3, "coupes")
    coupes = [] if rapide else moteur.coupes(chemin, 0.3)
    fiche["coupes"] = [round(c, 2) for c in coupes[:200]]
    fiche["plans"] = len(coupes) + 1
    fiche["duree_plan_moyenne"] = round(d / (len(coupes) + 1), 2)
    fiche["deja_monte"] = len(coupes) >= 3 and d / (len(coupes) + 1) < 8
    # ---- lumiere
    prog(0.5, "lumière")
    pas = 1.0 if d < 300 else 2.0
    lum = moteur.luminosite(chemin, pas)
    if lum:
        noirs = [(i * pas) for i, v in enumerate(lum) if v < 18]
        fiche["lumiere"] = {"moyenne": round(sum(lum) / len(lum), 1), "mini": round(min(lum), 1), "maxi": round(max(lum), 1),
                            "nuit": sum(lum) / len(lum) < 60, "part_noire": round(len(noirs) / len(lum), 2),
                            "passages_noirs": _plages(noirs, pas)[:20]}
    # ---- images clefs : couleurs, visages, mouvement
    prog(0.65, "images")
    instants = [d * (i + 0.5) / vignettes for i in range(vignettes)]
    fiche["instants_vignettes"] = [round(t, 2) for t in instants]
    if cv2 is not None:
        try:
            fiche.update(_images(chemin, instants, f))
        except Exception as e:            # noqa: BLE001
            fiche["erreur_images"] = str(e)
    # ---- moments forts : changement de decor, pic de son, pic de lumiere
    prog(0.9, "moments forts")
    moments = []
    for c in coupes[:30]:
        moments.append({"t": round(c, 2), "pourquoi": "changement de plan"})
    if lum:
        pics = sorted(range(len(lum)), key=lambda i: -lum[i])[:3]
        for i in pics:
            if lum[i] > 1.4 * (sum(lum) / len(lum)) + 10:
                moments.append({"t": round(i * pas, 2), "pourquoi": "pic de lumière"})
    fiche["moments"] = sorted(moments, key=lambda m: m["t"])[:40]
    # ---- resume en une ligne
    fiche["resume"] = resume(fiche)
    prog(1.0, "")
    return fiche


def _format(f):
    v = f.get("video") or {}
    if not v:
        return ""
    l, h = v.get("largeur") or 0, v.get("hauteur") or 0
    if not l or not h:
        return ""
    r = l / h
    if abs(r - 16 / 9) < 0.05:
        return "16:9"
    if abs(r - 9 / 16) < 0.05:
        return "9:16"
    if abs(r - 1) < 0.05:
        return "1:1"
    if abs(r - 4 / 5) < 0.05:
        return "4:5"
    return f"{l}:{h}"


def _date(f):
    t = f.get("date") or ""
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def _heure(f):
    t = f.get("date") or ""
    try:
        dt = datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
        try:                                   # heure locale : utile pour « crépuscule », « nuit »
            dt = dt.astimezone()
        except (ValueError, OSError):
            pass
        return dt.strftime("%H:%M")
    except ValueError:
        return ""


def _plages(instants, pas):
    out = []
    for t in instants:
        if out and t - out[-1][1] <= pas * 1.5:
            out[-1][1] = t + pas
        else:
            out.append([t, t + pas])
    return [(round(a, 1), round(b, 1)) for a, b in out if b - a >= 2 * pas]


def _images(chemin, instants, f):
    out = {"couleurs": [], "visages": {"nb_max": 0, "instants": []}, "mouvement": [], "vignettes": []}
    cap = cv2.VideoCapture(chemin)
    cascade = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    prec = None
    teintes = []
    for t in instants:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, img = cap.read()
        if not ok:
            continue
        rot = ((f.get("video") or {}).get("rotation") or 0)
        if rot == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rot == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rot == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        petit = cv2.resize(img, (320, int(320 * img.shape[0] / img.shape[1])))
        gris = cv2.cvtColor(petit, cv2.COLOR_BGR2GRAY)
        vis = cascade.detectMultiScale(gris, 1.2, 4, minSize=(20, 20))
        if len(vis):
            out["visages"]["nb_max"] = max(out["visages"]["nb_max"], len(vis))
            x, y, w, h = max(vis, key=lambda r: r[2] * r[3])
            out["visages"]["instants"].append({"t": round(t, 2), "nb": int(len(vis)),
                                               "boite": [round(x / petit.shape[1], 3), round(y / petit.shape[0], 3), round(w / petit.shape[1], 3), round(h / petit.shape[0], 3)]})
        hsv = cv2.cvtColor(petit, cv2.COLOR_BGR2HSV)
        teintes.append(hsv.reshape(-1, 3))
        if prec is not None:
            diff = cv2.absdiff(gris, prec).mean()
            out["mouvement"].append(round(float(diff), 1))
        prec = gris
        ok2, png = cv2.imencode(".png", petit, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        if ok2:
            out["vignettes"].append(png.tobytes())
    cap.release()
    if teintes:
        tout = np.concatenate(teintes)
        vifs = tout[tout[:, 1] > 60]
        noms = {"rouge": 0, "orange": 0, "jaune": 0, "vert": 0, "cyan": 0, "bleu": 0, "violet": 0, "rose": 0}
        for h in vifs[:, 0]:
            if h < 8 or h >= 170:
                noms["rouge"] += 1
            elif h < 20:
                noms["orange"] += 1
            elif h < 35:
                noms["jaune"] += 1
            elif h < 85:
                noms["vert"] += 1
            elif h < 100:
                noms["cyan"] += 1
            elif h < 130:
                noms["bleu"] += 1
            elif h < 150:
                noms["violet"] += 1
            else:
                noms["rose"] += 1
        total = max(1, len(vifs))
        out["couleurs"] = [(k, round(v / total, 2)) for k, v in sorted(noms.items(), key=lambda kv: -kv[1]) if v / total > 0.08][:4]
        out["saturation"] = round(float(tout[:, 1].mean()) / 255, 2)
    return out


def resume(fiche):
    parts = []
    v = fiche.get("video") or {}
    parts.append(moteur.duree_texte(fiche.get("duree", 0)))
    if fiche.get("format"):
        parts.append(fiche["format"] + (" vertical" if fiche.get("vertical") else ""))
    if v.get("cadence_variable"):
        parts.append("cadence variable")
    if v.get("hdr"):
        parts.append("HDR")
    l = fiche.get("lumiere") or {}
    if l.get("nuit"):
        parts.append("nuit")
    s = fiche.get("son") or {}
    if s.get("muet"):
        parts.append("sans son")
    elif s.get("voix_probable"):
        parts.append("voix")
    if fiche.get("deja_monte"):
        parts.append(f"déjà monté ({fiche.get('plans')} plans)")
    elif fiche.get("plans", 1) > 1:
        parts.append(f"{fiche['plans']} plans")
    vis = (fiche.get("visages") or {}).get("nb_max", 0)
    if vis:
        parts.append(f"{vis} visage(s)")
    if fiche.get("date"):
        parts.append(fiche["date"] + (" " + fiche["heure"] if fiche.get("heure") else ""))
    return " · ".join(parts)


def pour_ia(fiche):
    """Version texte compacte, sans les images, pour l'IA (et le journal)."""
    d = {k: v for k, v in fiche.items() if k not in ("vignettes", "chemin")}
    return json.dumps(d, ensure_ascii=False, default=str)


def depuis_media(m, params=None, progression=None):
    f = analyser(m["chemin"], params, progression)
    m["analyse"] = {k: v for k, v in f.items() if k != "vignettes"}
    return f
