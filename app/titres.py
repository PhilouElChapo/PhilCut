"""Titres, étiquettes et sous-titres : écrits en sous-titres ASS, rendus par FFmpeg (libass) à l'export.

ASS sait tout faire sans images intermédiaires : fondu, déplacement, rotation, zoom, machine à écrire, karaoké,
et une position par image pour une étiquette qui suit une personne. Un titre du projet :
  {"texte", "debut", "fin", "style", "x", "y" (0..1 : position du centre), "taille" (1 = normal), "couleur", "police",
   "animation": fondu | zoom | glisse | machine | neon | feu | tournoyant | cinetique | aucune,
   "suivi": {"positions": [(t, x, y), ...]} pour une étiquette accrochée}
"""
import html, os, re, sys

POLICE_DEFAUT = "Nunito"


def dossier_polices():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "fonts")


def _ass_couleur(hexa, alpha=0):
    hexa = (hexa or "#ffffff").lstrip("#")
    if len(hexa) == 3:
        hexa = "".join(c * 2 for c in hexa)
    r, g, b = hexa[0:2], hexa[2:4], hexa[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _t(s):
    s = max(0.0, float(s))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def _echapper(texte):
    return texte.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def ass(projet_titres, largeur, hauteur, cadence=30, sous_titres=()):
    """Fichier ASS complet (texte) pour tous les titres du projet + sous-titres optionnels [(debut, fin, texte)]."""
    base = int(hauteur * 0.055)
    lignes = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {largeur}", f"PlayResY: {hauteur}", "WrapStyle: 2",
              "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
              "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
              "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
              f"Style: Titre,{POLICE_DEFAUT},{base},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{max(2, base // 18)},{max(1, base // 24)},5,20,20,20,1",
              f"Style: SousTitre,{POLICE_DEFAUT},{int(base * 0.8)},&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,{max(2, base // 20)},0,2,40,40,{int(hauteur * 0.06)},1",
              f"Style: Etiquette,{POLICE_DEFAUT},{int(base * 0.7)},&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,1,0,0,0,100,100,0,0,3,{max(3, base // 10)},0,5,10,10,10,1",
              "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for t in projet_titres:
        lignes.extend(_evenements(t, largeur, hauteur, cadence))
    for st in sous_titres:
        d, f, texte = st[0], st[1], st[2]
        mots = st[3] if len(st) > 3 else None
        if mots:            # karaoké : chaque mot se colore quand il est prononcé
            lignes.append(f"Dialogue: 0,{_t(d)},{_t(f)},SousTitre,,0,0,0,,{{\\fad(80,80)\\1c{KARAOKE_CHANTE}\\2c{KARAOKE_A_VENIR}}}{karaoke(d, mots)}")
        else:
            lignes.append(f"Dialogue: 0,{_t(d)},{_t(f)},SousTitre,,0,0,0,,{{\\fad(120,120)}}{_echapper(texte)}")
    return "\n".join(lignes) + "\n"


KARAOKE_CHANTE = "&H0000D7FF&"     # jaune doré : mot déjà prononcé
KARAOKE_A_VENIR = "&H00FFFFFF&"    # blanc : mot à venir


def karaoke(debut, mots):
    """Balises ASS \\kf (remplissage progressif) à partir de [(debut_s, fin_s, mot)] ; les silences entre mots sont
    comptés dans le mot suivant pour rester calé sur la voix."""
    out, t = [], debut
    for md, mf, mot in mots:
        if md > t + 0.01:
            out.append(f"{{\\k{int(round((md - t) * 100))}}}")
        out.append(f"{{\\kf{max(1, int(round((mf - max(md, t)) * 100)))}}}{_echapper(mot)} ")
        t = max(t, mf)
    return "".join(out).rstrip()


EFFETS_TEXTE = [("aucun", "Simple"), ("contour", "Contour épais"), ("ombre", "Ombre portée"), ("contour_ombre", "Contour et ombre"),
                ("lueur", "Lueur"), ("relief", "Relief"), ("couleur_animee", "Couleur qui change")]


def tags_effet(t, fs, duree_ms):
    """Effets combinables du texte (cahier 17.2) en balises ASS : contour, ombre, lueur, relief, couleur animée.
    couleur2 = couleur du contour, de la lueur ou de la couleur d'arrivée."""
    e = t.get("effet_texte") or "aucun"
    c2 = _ass_couleur(t.get("couleur2") or ("#000000" if e in ("contour", "contour_ombre", "relief") else "#ffd24a"))
    if e == "contour":
        return f"\\bord{max(2, fs // 9)}\\3c{c2}\\shad0"
    if e == "ombre":
        return f"\\bord{max(1, fs // 40)}\\shad{max(2, fs // 11)}\\4c&H000000&\\4a&H50&"
    if e == "contour_ombre":
        return f"\\bord{max(2, fs // 10)}\\3c{c2}\\shad{max(2, fs // 12)}\\4c&H000000&\\4a&H60&"
    if e == "lueur":
        return f"\\bord{max(3, fs // 7)}\\3c{c2}\\blur{max(4, fs // 5)}\\shad0"
    if e == "relief":
        return f"\\bord{max(1, fs // 30)}\\3c&H202020&\\shad{max(2, fs // 16)}\\4c{c2}\\4a&H00&\\be1"
    if e == "couleur_animee":
        return f"\\t(0,{duree_ms},\\1c{c2})"
    return ""


def _evenements(t, L, H, cadence):
    x, y = int(float(t.get("x", 0.5)) * L), int(float(t.get("y", 0.85)) * H)
    taille = float(t.get("taille") or 1.0)
    coul = _ass_couleur(t.get("couleur"))
    police = t.get("police") or POLICE_DEFAUT
    fs = int(H * 0.055 * taille)
    anim = t.get("animation") or "fondu"
    style_nom = "Etiquette" if t.get("style") == "etiquette" else "Titre"
    texte = _echapper(t.get("texte", ""))
    d, f = float(t["debut"]), float(t["fin"])
    duree_ms = max(1, int((f - d) * 1000))
    fx = tags_effet(t, fs, duree_ms)
    base = f"\\fn{police}\\fs{fs}\\c{coul}\\pos({x},{y})" + fx
    out = []
    if t.get("suivi") and t["suivi"].get("positions"):
        # une position par pas de temps : plusieurs petits evenements consecutifs
        pos = t["suivi"]["positions"]
        for i, (ti, px, py) in enumerate(pos):
            tf = pos[i + 1][0] if i + 1 < len(pos) else f
            if tf <= ti or ti >= f or tf <= d:
                continue
            dx, dy = int(float(px) * L), int(float(py) * H) - int(fs * 1.4)
            out.append(f"Dialogue: 1,{_t(max(ti, d))},{_t(min(tf, f))},{style_nom},,0,0,0,,{{\\fn{police}\\fs{fs}\\c{coul}\\pos({dx},{dy}){fx}}}{texte}")
        return out
    if anim == "fondu":
        tags = base + "\\fad(300,300)"
    elif anim == "zoom":
        tags = base + "\\fad(150,250)\\fscx40\\fscy40\\t(0,350,\\fscx100\\fscy100)"
    elif anim == "glisse":
        tags = f"\\fn{police}\\fs{fs}\\c{coul}\\fad(150,250)\\move({x - int(L * 0.15)},{y},{x},{y},0,400)" + fx
    elif anim == "neon":
        tags = (base + f"\\bord{max(2, fs // 10)}\\3c{coul}\\blur{max(4, fs // 6)}\\fad(200,400)"
                f"\\t(0,120,\\alpha&H60&)\\t(120,220,\\alpha&H00&)\\t(300,380,\\alpha&H50&)\\t(380,480,\\alpha&H00&)")
    elif anim == "feu":
        tags = (base + f"\\c&H00A7FF&\\3c&H0028FF&\\bord{max(2, fs // 12)}\\blur{max(2, fs // 10)}\\fad(200,300)"
                f"\\t(0,{duree_ms},\\3c&H00D7FF&\\blur{max(3, fs // 8)})")
    elif anim == "tournoyant":
        tags = base + f"\\fad(100,300)\\frz-540\\fscx10\\fscy10\\t(0,700,\\frz0\\fscx100\\fscy100)"
    elif anim == "machine":
        brut = t.get("texte", "")
        n = max(1, len(brut))
        pas = min(90, duree_ms * 0.5 / n)
        morceaux = []
        for i, ch in enumerate(brut):
            morceaux.append(f"{{\\alpha&HFF&\\t({int(i * pas)},{int(i * pas + 1)},\\alpha&H00&)}}{_echapper(ch)}")
        return [f"Dialogue: 1,{_t(d)},{_t(f)},{style_nom},,0,0,0,,{{{base}\\fad(0,250)}}" + "".join(morceaux)]
    elif anim == "cinetique":
        mots = t.get("texte", "").split()
        if not mots:
            return []
        pas = (f - d) / (len(mots) + 1)
        for i, mot in enumerate(mots):
            ti = d + i * pas
            tf = f if i == len(mots) - 1 else min(f, ti + pas * 1.6)
            dec = (-1) ** i * int(L * 0.04)
            out.append(f"Dialogue: 1,{_t(ti)},{_t(tf)},{style_nom},,0,0,0,,{{\\fn{police}\\fs{int(fs * 1.25)}\\c{coul}"
                       f"\\pos({x + dec},{y})\\fad(80,160)\\fscx60\\fscy60\\t(0,160,\\fscx100\\fscy100)}}{_echapper(mot)}")
        return out
    else:
        tags = base
    out.append(f"Dialogue: 1,{_t(d)},{_t(f)},{style_nom},,0,0,0,,{{{tags}}}{texte}")
    return out


def filtre_ass(chemin_ass):
    """Filtre FFmpeg : le chemin doit etre echappe (Windows : C\\:/dossier/fichier.ass)."""
    p = chemin_ass.replace("\\", "/")
    p = p.replace(":", "\\:").replace("'", "\\'")
    polices = dossier_polices().replace("\\", "/").replace(":", "\\:")
    return f"subtitles='{p}':fontsdir='{polices}'"


def srt(sous_titres):
    """Fichier SRT a partir de [(debut, fin, texte)] : pour YouTube ou pour relecture."""
    out = []
    for i, st in enumerate(sous_titres, 1):
        d, f, texte = st[0], st[1], st[2]
        out.append(f"{i}\n{_srt_t(d)} --> {_srt_t(f)}\n{texte}\n")
    return "\n".join(out)


def _srt_t(s):
    s = max(0.0, float(s))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def lire_srt(texte):
    out = []
    for bloc in re.split(r"\n\s*\n", texte.strip()):
        lignes = [l_ for l_ in bloc.splitlines() if l_.strip()]
        if len(lignes) < 2:
            continue
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", lignes[1] if "-->" in lignes[1] else lignes[0])
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        d = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        f = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        txt = "\n".join(lignes[2:] if "-->" in lignes[1] else lignes[1:])
        out.append((d, f, html.unescape(txt)))
    return out
