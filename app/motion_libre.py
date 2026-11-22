"""1.1.0 : animation libre (Philippe, 21/11 18h50 : « on n'a pas de mode libre… à partir de phrases il faut que cela soit
construit » ; les types tout faits sont « hyper limités » et « un peu cheap »).

L'utilisateur décrit son animation en phrases ; l'IA (Claude de préférence) écrit une vraie composition HyperFrames (HTML,
CSS, SVG, GSAP), avec la charte (couleurs, polices, logo). PhilCut l'enveloppe dans le gabarit HyperFrames (même contrat que
les autres animations : une ligne de temps GSAP en pause, pilotée image par image), la rend sur ce poste en aperçu léger,
puis en qualité (HyperFrames sur ce poste, gratuit, ou chez HeyGen). Une remarque ou une erreur de rendu repart à l'IA avec
le code, qui le corrige ; rien n'est envoyé sans un clic, le prix est annoncé.
"""
import copy
import json
import re

from .langue import _

MOTEURS_LIBRES = ("hyperframes", "remotion")    # 1.1.2 : au choix de l'utilisateur (Préférences et fenêtre)
NOMS_MOTEURS = {"hyperframes": _("HyperFrames (HTML et GSAP ; libre, Apache 2.0 ; aussi rendu chez HeyGen)"),
                "remotion": _("Remotion (React ; gratuit pour un particulier, 3 personnes au plus ou une association)")}

PRIX_CREER = 0.12          # une composition écrite par Claude (environ 6 000 jetons de sortie), prix indicatif
PRIX_CORRIGER = 0.10
PRIX_VERIFIER = 0.03
DUREE_MAX = 60.0

CONSIGNE = """You are a senior motion designer and creative coder. You write ONE animation as an HyperFrames composition:
HTML + CSS + inline SVG + GSAP 3, rendered frame by frame by a headless Chrome into a video. Aim for the quality of a top
After Effects / Motion Canvas piece: deliberate composition, depth (layers, soft shadows, gradients, light), rich easing
(expo, back, elastic used with taste), overlapping motion, secondary animation, particles where they help, perfect typography,
nothing cheap or clip-art-like. Draw illustrations yourself with SVG paths and gradients (gift boxes, ribbons, charts,
fireworks, confetti…), never emoji as main graphics.

THE CANVAS (already in the page, do not recreate it):
- `#scenes` (position:absolute, inset 0, size W×H px) is where you put everything. A background is already painted unless
  transparent (see below).
- Variables available in JS: W, H (pixels), D (total duration in seconds), u = min(W, H) / 1080 (size unit: write every size
  as a multiple of u), C = colours {{fond, texte, doux, accent, accent2}} (hex), F = fonts {{titre, texte}} (CSS family names,
  already loaded), TRANSPARENT (boolean: the video will be laid over a film; then keep the background empty), LANG (text
  language code), `tl` = the GSAP timeline (already created, paused, registered), alea() = seeded random in [0, 1) (use it
  instead of Math.random, which is forbidden), $(tag, style, parent, text) = creates an element (parent defaults to #scenes; style = a CSS text "left:10px; …" or an
  object of camelCase properties {{left: 10 * u + "px", …}}, numbers become px),
  svg(markup, parent) = inserts an inline SVG string and returns the <svg> element.

STRICT RULES (the renderer seeks the timeline to each frame; anything else breaks the video):
1. Every movement is a tween ON `tl` with an explicit absolute position in seconds: tl.to(el, {{...}}, 1.2), tl.fromTo(...),
   tl.set(...). Everything must happen between 0 and D. No CSS animations/transitions, no requestAnimationFrame, no
   setTimeout/setInterval, no gsap.to outside tl, no repeat: -1 (finite repeats are fine), no onUpdate/onComplete callbacks
   (they are not called when the renderer seeks): for counters use a proxy object tweened with `modifiers` that writes the
   text, e.g. const o = {{v: 0}}; tl.to(o, {{v: 40, duration: 3, ease: "power2.inOut", modifiers: {{v: v => {{ el.textContent =
   Math.round(v); return v; }}}}}}, 0.5);
2. No network: no <img src="http…">, no web fonts, no external scripts. Only the fonts in F, inline SVG, CSS gradients.
3. Deterministic: same frame → same picture. Use alea() for particles, created once at build time.
4. Keep important things inside the safe area (8 % margin on each side; for vertical video, keep the bottom 20 % free).
5. Texts in the user's language ({langue}), short, correctly spelt, numbers written like the user. Do not invent facts or
   numbers the user did not give; you may write decorative words only if asked.
6. Animate ONLY transforms and opacity (x, y, scale, scaleX, scaleY, rotation, opacity) and SVG attributes (attr:{{...}},
   strokeDashoffset): never top, left, width, height, margin or font-size (they snap to whole pixels and stutter). Place
   elements with left/top once, then move them with x/y. At most ~400 animated elements.
7. Pitfalls that ruin a render: tl.fromTo() shows its FROM values from 0 s, so give a hidden start (opacity: 0) to anything
   that appears later; a mirror with scaleX(-1) flips around transform-origin (use transformOrigin "50% 50%" or draw the
   mirrored shape in the SVG), and a GSAP scale/rotation tween replaces a CSS transform; place objects that come in pairs
   (left/right) symmetrically and check both are inside the frame.
8. The whole animation must read well at {L}×{H} ({format}) and last about {duree} seconds unless the user says otherwise
   (max {dmax:g} s).{musique}

ANSWER FORMAT — exactly these sections, nothing before or after, no markdown fences:
===TITRE===
a short title in the user's language
===DUREE===
the duration in seconds (a number)
===PLAN===
the storyboard: one line per event the user asked for, in the order of the user's text, written "start-end s: what happens"
(e.g. "4.5-7 s: fireworks burst above the gift"). EVERY event, object and effect of the user's description must appear here,
none dropped or merged away; every end is at most the duration. The code must do exactly this plan.
===SONS===
the sound effects that go with the plan, one per line, written "time s: id" (e.g. "6.2 s: boom"), at the exact instant the
event happens on screen (an appearance, a burst, a typed text, a gust, an explosion…). Use ONLY these ids: {sons}. Usually
3 to 12 sounds; repeat an id if the same thing happens again; none if the user asked for silence.
===CSS===
the CSS (classes you use; #scenes already exists)
===HTML===
static HTML put inside #scenes (may be empty if you build everything in JS)
===JS===
the JavaScript that builds the elements and the timeline (it runs after the HTML is in place)
===MESSAGE===
one or two sentences in the user's language: what you made, and what the user can ask to change"""

CONSIGNE_REMOTION = """You are a senior motion designer and creative coder. You write ONE animation as a Remotion (React) component,
rendered frame by frame into a video. Aim for the quality of a top After Effects / Motion Canvas piece: deliberate composition,
depth (layers, soft shadows, gradients, light), rich easing (Easing.out(Easing.exp), Easing.back, spring() used with taste),
overlapping motion, secondary animation, particles where they help, perfect typography, nothing cheap or clip-art-like. Draw
illustrations yourself with inline SVG (paths, gradients: gift boxes, ribbons, charts, fireworks, confetti…), never emoji as main
graphics.

THE FILE YOU WRITE (TypeScript + JSX) must export exactly:
  export const Animation: React.FC<{{ A: Infos }}> = ({{ A }}) => {{ ... }};
Allowed imports ONLY: `import React from "react";`, named imports from "remotion" (AbsoluteFill, Sequence, interpolate,
interpolateColors, spring, Easing, random, useCurrentFrame, useVideoConfig) and `import type {{ Infos }} from "./LibreTypes";`.
Infos A = {{ W, H (pixels), D (total duration in seconds), fps, u = min(W, H) / 1080 (size unit: write every size as a multiple
of A.u), C: {{ fond, texte, doux, accent, accent2 }} (hex colours), F: {{ titre, texte }} (CSS font families, already loaded),
TRANSPARENT (boolean: the video will be laid over a film; then paint no background), LANG (text language code) }}.
PhilCut already paints the background colour (unless transparent), loads the fonts and adds the logo: you return the content,
usually an <AbsoluteFill> with absolutely positioned children.

STRICT RULES (Remotion renders each frame independently, in parallel; anything else breaks the video):
1. Every movement is computed from `const frame = useCurrentFrame()` (t = frame / A.fps) with interpolate(...,
   {{extrapolateLeft: "clamp", extrapolateRight: "clamp", easing}}) or spring({{frame, fps: A.fps, ...}}). No useState or useEffect
   for animation, no CSS animations/transitions, no requestAnimationFrame, setTimeout or setInterval, no Date.
2. No Math.random: use random("a seed string") from remotion (deterministic). Build particle lists with useMemo or at module
   level from random(...), never from the frame.
3. No network: no <img src="http…">, no fetch, no web fonts, no other npm package. Only the fonts in A.F, inline SVG, CSS
   gradients.
4. Keep important things inside the safe area (8 % margin on each side; for vertical video, keep the bottom 20 % free).
5. Texts in the user's language ({langue}), short, correctly spelt, numbers written like the user. Do not invent facts or
   numbers the user did not give; you may write decorative words only if asked. Counters: Math.round of an interpolated value.
6. Prefer transform (translate, scale, rotate) and opacity for motion; place elements with left/top once. At most ~400
   animated elements. Valid TypeScript: type your helper parameters (number, string, React.CSSProperties…).
7. Pitfalls: a mirror with scaleX(-1) flips around transform-origin (use "50% 50%" or draw the mirrored shape in the SVG);
   place objects that come in pairs (left/right) symmetrically and check both are inside the frame; anything that appears
   later is invisible (opacity 0) before its instant.
8. The whole animation must read well at {L}×{H} ({format}) and last about {duree} seconds unless the user says otherwise
   (max {dmax:g} s).{musique}

ANSWER FORMAT — exactly these sections, nothing before or after, no markdown fences:
===TITRE===
a short title in the user's language
===DUREE===
the duration in seconds (a number)
===PLAN===
the storyboard: one line per event the user asked for, in the order of the user's text, written "start-end s: what happens"
(e.g. "4.5-7 s: fireworks burst above the gift"). EVERY event, object and effect of the user's description must appear here,
none dropped or merged away; every end is at most the duration. The code must do exactly this plan.
===SONS===
the sound effects that go with the plan, one per line, written "time s: id" (e.g. "6.2 s: boom"), at the exact instant the
event happens on screen (an appearance, a burst, a typed text, a gust, an explosion…). Use ONLY these ids: {sons}. Usually
3 to 12 sounds; repeat an id if the same thing happens again; none if the user asked for silence.
===TSX===
the whole file (imports, then helpers, then export const Animation)
===MESSAGE===
one or two sentences in the user's language: what you made, and what the user can ask to change"""

CONSIGNE_CORRIGER = """Here is the animation you wrote before (sections below). {pourquoi}
Rewrite the WHOLE animation with the same answer format and the same strict rules, keeping everything that was fine.
Re-read the user's original request first: every event it describes must be in the PLAN and really visible in the animation
(if something was missing, add it now), and nothing may happen after the duration.

{code}"""


# 1.1.6 : les bruitages de PhilCut que l'IA peut placer (Philippe, 21/11 21h41 : « pour les bruitages, ça se passe comment ? »)
SONS_EN = {"whoosh": "fast whoosh, something passing", "whoosh_inverse": "reverse whoosh rising to a cut",
           "impact": "dull hit, landing", "boom": "deep cinematic boom", "pop": "small pop, something appears",
           "ding": "bright bell, good news", "declic": "camera shutter", "bip": "short beep", "montee": "2 s riser before the big moment",
           "descente": "falling tone", "tambour": "2 s drum roll before an announcement", "cymbale": "cymbal crash",
           "gong": "big gong", "machine": "typewriter keys (2 s)", "glitch": "digital glitch", "laser": "sci-fi laser",
           "boing": "cartoon spring", "validation": "two rising notes, success", "notification": "phone notification",
           "caisse": "cash register", "sonnette": "door chime", "coeur": "heartbeat", "vent": "wind (6 s background)",
           "tic_tac": "clock ticking", "sifflet": "whistle", "buzzer": "error buzzer"}


def _sons_permis():
    from . import bruitages
    return [k for k in SONS_EN if k in bruitages.SONS]


def lire_sons(texte, duree=None):
    """Les bruitages demandés par l'IA : [(instant, id)], ids connus seulement, dans la durée."""
    permis = set(_sons_permis())
    out = []
    for ligne in (texte or "").splitlines():
        m = re.match(r"\s*[-•*]?\s*(\d+(?:[.,]\d+)?)\s*s?\s*(?:[-–—à]\s*\d+(?:[.,]\d+)?\s*s?\s*)?(?:[:)\-–—=>→]+)\s*"
                     r"[«\"'`(\s]*([a-z_]+)", ligne.strip().lower())
        if m and m.group(2) in permis:
            t = float(m.group(1).replace(",", "."))
            if duree is None or t <= float(duree) + 0.05:
                out.append((round(t, 2), m.group(2)))
    return sorted(out)[:40]


_SONS_DU_PLAN = ((r"feu d.artifice|firework", "boom"), (r"confetti", "whoosh"),
                 (r"machine à écrire|machine a ecrire|lettre par lettre|typewriter|typed", "machine"),
                 (r"ouragan|tourbillon|tornade|hurricane|tornado|vortex|whirl", "vent"),
                 (r"fond|molle|liqu[eé]fi|dissou|melt|dissolv", "descente"),
                 (r"appara[iî]t|surgit|appear|pops? up", "pop"), (r"explos|deton|détona|burst|blast", "boom"),
                 (r"compteur|counter|monte jusqu|count", "montee"))


def sons_du_plan(plan):
    """1.1.8 : quand l'IA n'a pas écrit de sons, PhilCut les déduit de son plan (un par étape, au début de l'étape)."""
    out = []
    for a, _b, texte in plan or []:
        t = (texte or "").lower()
        for motif, ident in _SONS_DU_PLAN:
            if re.search(motif, t):
                out.append((round(float(a), 2), ident))
                break
    return out


def sons_texte(anim):
    from . import bruitages
    return " · ".join(f"{t:g} s {bruitages.SONS[i][0]}".replace(".", ",") for t, i in ((anim.get("libre") or {}).get("sons") or [])
                      if i in bruitages.SONS)


def musique_consigne(anim):
    """1.1.6 : la musique du film sous l'animation (temps forts en secondes de l'animation) : l'IA y cale les moments forts."""
    mu = (anim or {}).get("musique") or {}
    forts = [t for t in mu.get("forts") or [] if 0 <= t <= DUREE_MAX][:40]
    if len(forts) < 2:
        return ""
    return ("\n8. MUSIC: the film's music plays under this animation" + (f" (tempo {mu['bpm']:g} bpm)" if mu.get("bpm") else "") +
            ". Its strong beats fall at these seconds of the animation: " + ", ".join(f"{t:g}" for t in forts) +
            ". Put the main events (appearances, bursts, the explosion, scene changes) exactly on strong beats, and the end of the "
            "animation on a strong beat too.")


def fiche(description, taille=(1920, 1080), duree=0.0, charte=None, transparent=False, moteur="hyperframes"):
    return {"genre": "libre", "description": description.strip(), "taille": list(taille), "duree": float(duree or 0),
            "charte": charte, "transparent": bool(transparent), "cadence": 30, "titre": "",
            "moteur_libre": moteur if moteur in MOTEURS_LIBRES else "hyperframes",
            "libre": {"css": "", "html": "", "js": "", "tsx": "", "moteur": "", "message": "", "historique": []}}


def moteur_de(anim):
    """Le moteur pour lequel l'animation est (ou sera) écrite."""
    m = (anim or {}).get("moteur_libre")
    return m if m in MOTEURS_LIBRES else "hyperframes"


def code_de(anim):
    """Le moteur pour lequel le code présent a été écrit (« » s'il n'y a pas encore de code)."""
    lib = (anim or {}).get("libre") or {}
    if lib.get("tsx", "").strip() and lib.get("moteur") == "remotion":
        return "remotion"
    if lib.get("js", "").strip():
        return "hyperframes"
    return ""


def a_jour(anim):
    """Le code présent est écrit pour le moteur choisi (sinon il faut le faire réécrire)."""
    return code_de(anim) == moteur_de(anim)


def _format(L, H):
    if L == H:
        return "square 1:1"
    return "vertical 9:16" if H > L else "horizontal 16:9"


def consigne(anim):
    from .motion import _langue_ui
    L, H = anim.get("taille") or (1920, 1080)
    modele = CONSIGNE_REMOTION if moteur_de(anim) == "remotion" else CONSIGNE
    return modele.format(langue=_langue_ui(), L=L, H=H, format=_format(L, H), duree=f"{anim.get('duree') or 8:g}",
                           dmax=DUREE_MAX, sons=", ".join(f"{k} ({SONS_EN[k]})" for k in _sons_permis()),
                           musique=musique_consigne(anim))


def sections(texte):
    """Les sections de la réponse (===TITRE===, ===DUREE===, ===CSS===, ===HTML===, ===JS===, ===MESSAGE===)."""
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", (texte or "").strip())
    morceaux = re.split(r"^\s*===\s*([A-Z]+)\s*===\s*$", t, flags=re.M)
    out = {}
    for i in range(1, len(morceaux) - 1, 2):
        out[morceaux[i].lower()] = morceaux[i + 1].strip("\n")
    if not (out.get("js", "").strip() or out.get("tsx", "").strip()):
        raise ValueError(_("L'IA n'a pas rendu d'animation lisible (code absent). Réessayez."))
    for cle in ("css", "html", "js", "tsx"):                 # des balises de code oubliées dans une section
        out[cle] = re.sub(r"^```[a-z]*\s*|\s*```$", "", out.get(cle, "").strip())
    return out


def verifier_code(js, html=""):
    """Les fautes qui casseraient le rendu image par image : refusées avant de payer un rendu (renvoie la liste)."""
    fautes = []
    regles = ((r"Math\.random", _("Math.random (remplacer par alea())")),
              (r"requestAnimationFrame|setTimeout|setInterval", _("minuterie du navigateur (tout doit passer par tl)")),
              (r"repeat\s*:\s*-1", _("répétition infinie")),
              (r"\bonUpdate\b|\bonComplete\b", _("onUpdate / onComplete (non appelés quand le rendu se place à une image)")),
              (r"https?://", _("adresse internet (rien ne doit être chargé)")),
              (r"gsap\.(to|from|fromTo)\s*\(", _("animation hors de tl")))
    for motif, quoi in regles:
        if re.search(motif, js or "") or (motif == r"https?://" and re.search(motif, html or "")):
            fautes.append(quoi)
    return fautes


def lire_plan(texte):
    """1.1.2 : les étapes du plan de l'IA : [(début, fin, texte)] (Philippe, 21/11 20h13 : feu d'artifice et confettis absents)."""
    out = []
    for ligne in (texte or "").splitlines():
        m = re.match(r"\s*[-•*]?\s*(\d+(?:[.,]\d+)?)\s*(?:s\s*)?[-–—à]\s*(\d+(?:[.,]\d+)?)\s*s?\s*[:)\-–—]?\s*(.*)", ligne)
        if m:
            a, b = (float(x.replace(",", ".")) for x in m.group(1, 2))
            out.append((a, max(a, b), m.group(3).strip()))
    return out


def plan_texte(anim):
    plan = ((anim or {}).get("libre") or {}).get("plan") or []
    return "\n".join(_("{a}–{b} s : {t}", a=f"{a:g}".replace(".", ","), b=f"{b:g}".replace(".", ","), t=t) for a, b, t in plan)


def fautes_plan(anim):
    """Le plan qui dépasse la durée (la fin serait coupée)."""
    plan = ((anim or {}).get("libre") or {}).get("plan") or []
    d = float((anim or {}).get("duree") or 0)
    if plan and d and max(b for _a, b, _t in plan) > d + 0.25:
        coupe = [t for _a, b, t in plan if b > d + 0.25]
        return [_("le plan dure {p} s mais l'animation {d} s : coupé à la fin ({c})", p=f"{max(b for _a, b, _t in plan):g}",
                  d=f"{d:g}", c=" ; ".join(coupe)[:200])]
    return []


IMPORTS_PERMIS = ("react", "remotion", "./LibreTypes")


def verifier_tsx(tsx):
    """1.1.2 : les fautes qui casseraient le rendu Remotion (images rendues séparément, en parallèle) ou sortiraient du projet."""
    fautes = []
    regles = ((r"Math\.random", _("Math.random (remplacer par random(\"…\") de Remotion)")),
              (r"requestAnimationFrame|setTimeout|setInterval", _("minuterie du navigateur (tout doit venir de useCurrentFrame)")),
              (r"\buseEffect\b|\buseLayoutEffect\b", _("useEffect (le mouvement doit venir de useCurrentFrame)")),
              (r"\bDate\.now\b|\bnew Date\b", _("l'heure du poste (le rendu doit être le même à chaque fois)")),
              (r"https?://", _("adresse internet (rien ne doit être chargé)")),
              (r"\bfetch\s*\(|\brequire\s*\(|\bimport\s*\(", _("chargement de code ou de données")),
              (r"@keyframes|transition\s*:", _("animation CSS (non suivie par le rendu image par image)")))
    for motif, quoi in regles:
        if re.search(motif, tsx or ""):
            fautes.append(quoi)
    for m in re.finditer(r"""^\s*import\b[^;]*?from\s*["']([^"']+)["']""", tsx or "", flags=re.M | re.S):
        if m.group(1) not in IMPORTS_PERMIS:
            fautes.append(_("import de « {m} » (seuls react et remotion sont permis)", m=m.group(1)))
    if not re.search(r"export\s+const\s+Animation\b", tsx or ""):
        fautes.append(_("« export const Animation » absent"))
    return fautes


def fautes(anim):
    """Les règles non respectées par le code présent, selon son moteur."""
    lib = (anim or {}).get("libre") or {}
    if code_de(anim) == "remotion":
        return verifier_tsx(lib.get("tsx", "")) + fautes_plan(anim)
    return verifier_code(lib.get("js", ""), lib.get("html", "")) + fautes_plan(anim)


def appliquer(anim, s, demande=""):
    a = copy.deepcopy(anim)
    lib = a.setdefault("libre", {})
    hist = lib.get("historique") or []
    if code_de(a):
        hist = (hist + [{k: lib.get(k, "") for k in ("css", "html", "js", "tsx", "moteur", "plan", "sons")}])[-5:]
    remotion = bool(s.get("tsx", "").strip()) and moteur_de(a) == "remotion"
    if remotion:
        lib.update(css="", html="", js="", tsx=s.get("tsx", ""), moteur="remotion")
    else:
        lib.update(css=s.get("css", ""), html=s.get("html", ""), js=s.get("js", ""), tsx="", moteur="hyperframes")
    lib.update(message=s.get("message", ""), historique=hist, plan=lire_plan(s.get("plan", "")),
               sons=lire_sons(s.get("sons", "")))
    lib["sons_deduits"] = not lib["sons"]
    if not lib["sons"]:
        lib["sons"] = sons_du_plan(lib["plan"])
    if demande:
        lib.setdefault("demandes", []).append(demande)
    try:
        d = float(re.findall(r"[\d.]+", s.get("duree", ""))[0])
        if not a.get("duree_imposee"):
            fin_plan = max([b for _a, b, _t in lib["plan"]] or [0.0])
            a["duree"] = max(2.0, min(DUREE_MAX, max(d, fin_plan)))
    except (IndexError, ValueError):
        a["duree"] = a.get("duree") or 8.0
    a["titre"] = (s.get("titre") or "").strip()[:80] or a.get("titre") or _("Animation libre")
    return a


def _code(anim):
    lib = anim.get("libre") or {}
    tete = ["===TITRE===", anim.get("titre", ""), "===DUREE===", f"{anim.get('duree') or 8:g}", "===PLAN===",
            "\n".join(f"{a:g}-{b:g} s: {t}" for a, b, t in (lib.get("plan") or [])), "===SONS===",
            "\n".join(f"{t:g} s: {i}" for t, i in (lib.get("sons") or []))]
    if code_de(anim) == "remotion":
        corps = ["===TSX===", lib.get("tsx", "")]
    else:
        corps = ["===CSS===", lib.get("css", ""), "===HTML===", lib.get("html", ""), "===JS===", lib.get("js", "")]
    return "\n".join(tete + corps + ["===MESSAGE===", lib.get("message", "")])


def creer(params, anim):
    """La première écriture, d'après la description."""
    from . import ia
    t = ia.demander(params, consigne(anim), _("Ce que je veux : {d}", d=anim.get("description", "")), max_jetons=16000)
    return appliquer(anim, sections(t))


def corriger(params, anim, remarque="", erreur=""):
    """Une remarque de l'utilisateur ou une erreur de rendu : l'IA reprend son code et le corrige."""
    from . import ia
    pourquoi = []
    if remarque.strip():
        pourquoi.append("The user asks: " + remarque.strip())
    if erreur.strip():
        pourquoi.append("The render failed or the code broke a rule, fix it: " + erreur.strip()[:1500])
    if code_de(anim) and not a_jour(anim):            # 1.1.2 : écrite pour l'autre moteur : on la fait transposer
        vers = "a Remotion (React) component" if moteur_de(anim) == "remotion" else "an HyperFrames composition (HTML, CSS, GSAP)"
        pourquoi.insert(0, f"It was written for the other engine: translate it into {vers}, same look and timing, following "
                           "the new answer format.")
    texte = CONSIGNE_CORRIGER.format(pourquoi=" ".join(pourquoi) or "Improve it.", code=_code(anim))
    t = ia.demander(params, consigne(anim), _("Ce que je voulais au départ : {d}", d=anim.get("description", "")) + "\n\n" + texte,
                    max_jetons=16000)
    return appliquer(anim, sections(t), remarque or erreur[:200])


def revenir(anim):
    """La version d'avant (les cinq dernières sont gardées)."""
    a = copy.deepcopy(anim)
    lib = a.get("libre") or {}
    if not lib.get("historique"):
        return a
    v = lib["historique"].pop()
    v.setdefault("tsx", "")
    v["plan"] = [tuple(x) for x in (v.get("plan") or [])]
    v["sons"] = [tuple(x) for x in (v.get("sons") or [])]
    v.setdefault("moteur", "remotion" if v.get("tsx") else "hyperframes")
    lib.update(v)
    if v["moteur"] in MOTEURS_LIBRES:
        a["moteur_libre"] = v["moteur"]
    return a


GABARIT = r"""<!doctype html>
<html lang="{langue}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={RL}, height={RH}" />
<script src="{gsap}"></script>
<style>
{polices}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {RL}px; height: {RH}px; overflow: hidden; background: {fond_page}; }}
#racine {{ position: relative; width: {RL}px; height: {RH}px; overflow: hidden; font-family: "{police_texte}", "Poppins", sans-serif;
  color: {texte}; }}
.clip {{ position: absolute; inset: 0; }}
{css}{zoom_css}
</style>
</head>
<body>
<div id="racine" data-composition-id="philcut" data-start="0" data-duration="{duree}" data-width="{RL}" data-height="{RH}"
  data-fps="{cadence}">
  <div id="fond" class="clip" data-start="0" data-duration="{duree}" data-track-index="0"></div>
  <div id="scenes" class="clip" data-start="0" data-duration="{duree}" data-track-index="1">{html}</div>
</div>
<script>
const W = {L}, H = {H}, D = {duree}, u = Math.min(W, H) / 1080, TRANSPARENT = {transparent}, LANG = {langue_js};
const C = {couleurs};
const F = {polices_js};
const tl = gsap.timeline({{ paused: true }});
window.__timelines = window.__timelines || {{}};
window.__timelines["philcut"] = tl;
let __graine = 1234567;
const alea = () => {{ __graine = (__graine * 1103515245 + 12345) % 2147483648; return __graine / 2147483648; }};
const __sansUnite = /^(opacity|zIndex|fontWeight|lineHeight|flex|flexGrow|flexShrink|order)$/;
const __style = (e, style) => {{ if (!style) return; if (typeof style === "string") {{ e.setAttribute("style", style); return; }}
  for (const k in style) {{ let v = style[k]; if (v === undefined || v === null) continue;
    if (typeof v === "number" && !__sansUnite.test(k)) v = v + "px";
    if (k.indexOf("-") >= 0) e.style.setProperty(k, String(v)); else e.style[k] = String(v);
    if (k === "webkitBackgroundClip" || k === "WebkitBackgroundClip") e.style.backgroundClip = String(v);
    if (k === "webkitTextFillColor" || k === "WebkitTextFillColor") e.style.setProperty("-webkit-text-fill-color", String(v)); }} }};
const $ = (tag, style, parent, texte) => {{ const e = document.createElement(tag); __style(e, style);
  if (texte !== undefined) e.textContent = texte; (parent || document.getElementById("scenes")).appendChild(e); return e; }};
// 1.1.14 : tl.fromTo montre ses valeurs « de départ » dès 0 s ; un élément caché par son style (opacity 0) qui doit apparaître
// plus tard (flash, onde de choc, éclat) restait visible tout du long : il reste caché jusqu'à son instant.
const __fromTo = tl.fromTo.bind(tl);
tl.fromTo = (cible, de, vers, pos, ...r) => {{
  if (typeof pos === "number" && pos > 0 && de && vers && vers.immediateRender === undefined && de.opacity !== undefined && de.opacity > 0) {{
    const els = gsap.utils.toArray(cible);
    if (els.length && els.every(e => e && e.style && e.style.opacity === "0")) vers = Object.assign({{}}, vers, {{ immediateRender: false }});
  }}
  return __fromTo(cible, de, vers, pos, ...r);
}};
const svg = (markup, parent) => {{ const d = document.createElement("div"); d.innerHTML = markup.trim();
  const s = d.firstElementChild; (parent || document.getElementById("scenes")).appendChild(s); return s; }};
if (!TRANSPARENT) document.getElementById("fond").style.background = C.fond;
(function () {{
{js}
}})();
{logo}
tl.set({{}}, {{}}, D);
tl.seek(0);
</script>
</body>
</html>
"""


def composition(anim, gsap, polices, logo):
    """La page HyperFrames de l'animation libre (appelée par motion_html.composition)."""
    import html as H_
    from . import charte as CH
    from .motion import _langue_ui
    ch = CH.complete(anim.get("charte"))
    L, H = [int(x) // 2 * 2 for x in (anim.get("taille") or (1920, 1080))]
    # 1.1.9 : l'aperçu léger garde la taille logique (le code de l'IA place souvent en pixels : left:540px…) et la page est
    # réduite d'un bloc (zoom) ; avant, la page était à moitié de taille et tout sortait du cadre (Philippe, 21/11 23h14)
    k = float(anim.get("echelle_rendu") or 1.0)
    RL, RH = int(L * k) // 2 * 2, int(H * k) // 2 * 2
    lib = anim.get("libre") or {}
    duree = float(anim.get("duree") or 8)
    css_polices = "\n".join(f'@font-face {{ font-family: "{H_.escape(fam)}"; src: url("{H_.escape(f)}"); font-weight: {poids}; }}'
                            for fam, f, poids in polices)
    js_logo = ""
    if logo:
        h = int(70 * min(L, H) / 1080)
        js_logo = ("{ const im = document.createElement('img'); im.src = " + json.dumps(logo) + "; im.setAttribute('style', " +
                   json.dumps(f"position:absolute;height:{h}px;right:{int(L * 0.05)}px;top:{int(H * 0.05)}px;opacity:0.9") +
                   "); document.getElementById('scenes').appendChild(im); }")
    return GABARIT.format(
        langue=H_.escape(_langue_ui()), L=L, H=H, RL=RL, RH=RH, gsap=H_.escape(gsap), polices=css_polices,
        zoom_css=("" if k == 1.0 else "\n#fond, #scenes { left: 0 !important; top: 0 !important; right: auto !important; "
                  f"bottom: auto !important; width: {L}px !important; height: {H}px !important; zoom: {k:g}; }}"),
        fond_page="transparent" if anim.get("transparent") else H_.escape(ch["couleurs"]["fond"]),
        police_texte=H_.escape(ch.get("police_texte") or "Poppins"), texte=H_.escape(ch["couleurs"]["texte"]),
        css=lib.get("css", "").replace("</", "<\\/"), html=lib.get("html", ""), duree=f"{duree:g}",
        cadence=int(anim.get("cadence") or 30), transparent="true" if anim.get("transparent") else "false",
        langue_js=json.dumps(_langue_ui()), couleurs=json.dumps(ch["couleurs"]),
        polices_js=json.dumps({"titre": ch.get("police_titre") or "Poppins", "texte": ch.get("police_texte") or "Poppins"}),
        js=lib.get("js", "").replace("</script", "<\\/script"), logo=js_logo)


def apercu_leger(anim, echelle=0.5, cadence=15):
    """La même animation, plus petite et à 15 images par seconde : l'aperçu se rend en quelques secondes. 1.1.9 : la taille
    logique ne change pas (W, H, les pixels écrits par l'IA restent justes) ; seule l'image rendue est réduite."""
    a = copy.deepcopy(anim)
    a["echelle_rendu"] = echelle
    a["cadence"] = cadence
    return a


def mixer_sons(video, sons, sortie, volume=0.7):
    """L'aperçu avec ses bruitages (pour les entendre avant de poser) ; sans son à mettre, la vidéo telle quelle."""
    from . import bruitages, moteur
    sons = [(t, i) for t, i in sons or [] if i in bruitages.SONS]
    if not sons:
        return video
    args = ["-i", video]
    for _t, i in sons:
        args += ["-i", bruitages.chemin(i)]
    parts = [f"[{k + 1}:a]adelay={int(t * 1000)}|{int(t * 1000)},volume={volume}[s{k}]" for k, (t, _i) in enumerate(sons)]
    parts.append("".join(f"[s{k}]" for k in range(len(sons))) + f"amix=inputs={len(sons)}:normalize=0:duration=longest[a]")
    d = float(moteur.sonder(video).get("duree") or 0)
    args += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k"]
    if d:
        args += ["-t", f"{d:.3f}"]
    moteur.lancer(args + [sortie])
    return sortie


CONSIGNE_VERIFIER = """You check an animation render against its storyboard. You receive one frame taken in the middle of each step,
in order, and the list of steps (number, time span, what must happen). For each step, say whether what it describes is
clearly visible in its frame (a typewriter text may be partly typed; an explosion may be mid-burst). Be strict: if the main
object or effect of the step is absent, it is not visible. Answer in JSON only:
[{"n": step number, "vue": true or false, "remarque": "in the user's language ({langue}), what is missing or wrong, short"}]"""


def images_etapes(video, plan, dossier):
    """Une image au milieu de chaque étape (8 au plus), prise dans l'aperçu."""
    from . import moteur
    import os
    out = []
    for k, (a, b, _t) in enumerate(plan[:8]):
        f = os.path.join(dossier, f"etape_{k + 1}.jpg")
        moteur.lancer(["-ss", f"{(a + b) / 2:.2f}", "-i", video, "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "4", f])
        out.append(f)
    return out


def verifier_etapes(params, anim, video):
    """[{n, a, b, texte, vue, remarque}] : ce que l'IA voit de chaque étape du plan dans l'aperçu."""
    import tempfile
    from . import ia
    from .motion import _langue_ui
    plan = ((anim or {}).get("libre") or {}).get("plan") or []
    if not plan:
        raise ValueError(_("Pas de plan à vérifier : faites d'abord construire l'animation."))
    images = images_etapes(video, plan, tempfile.mkdtemp())
    etapes = "\n".join(f"{k + 1}. {a:g}-{b:g} s: {t}" for k, (a, b, t) in enumerate(plan[:8]))
    octets = []
    for f in images:
        with open(f, "rb") as x:
            octets.append(x.read())
    r = ia.demander(params, CONSIGNE_VERIFIER.replace("{langue}", _langue_ui()), "Steps:\n" + etapes, images=octets,
                    json_attendu=True, max_jetons=1500)
    vus = {int(x.get("n", 0)): x for x in (r if isinstance(r, list) else []) if isinstance(x, dict)}
    return [dict(n=k + 1, a=a, b=b, texte=t, vue=bool((vus.get(k + 1) or {}).get("vue", True)),
                 remarque=(vus.get(k + 1) or {}).get("remarque", "")) for k, (a, b, t) in enumerate(plan[:8])]
