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
  instead of Math.random, which is forbidden), $(tag, style, parent, text) = creates an element (parent defaults to #scenes),
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
7. The whole animation must read well at {L}×{H} ({format}) and last about {duree} seconds unless the user says otherwise
   (max {dmax:g} s).

ANSWER FORMAT — exactly these sections, nothing before or after, no markdown fences:
===TITRE===
a short title in the user's language
===DUREE===
the duration in seconds (a number)
===PLAN===
the storyboard: one line per event the user asked for, in the order of the user's text, written "start-end s: what happens"
(e.g. "4.5-7 s: fireworks burst above the gift"). EVERY event, object and effect of the user's description must appear here,
none dropped or merged away; every end is at most the duration. The code must do exactly this plan.
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
7. The whole animation must read well at {L}×{H} ({format}) and last about {duree} seconds unless the user says otherwise
   (max {dmax:g} s).

ANSWER FORMAT — exactly these sections, nothing before or after, no markdown fences:
===TITRE===
a short title in the user's language
===DUREE===
the duration in seconds (a number)
===PLAN===
the storyboard: one line per event the user asked for, in the order of the user's text, written "start-end s: what happens"
(e.g. "4.5-7 s: fireworks burst above the gift"). EVERY event, object and effect of the user's description must appear here,
none dropped or merged away; every end is at most the duration. The code must do exactly this plan.
===TSX===
the whole file (imports, then helpers, then export const Animation)
===MESSAGE===
one or two sentences in the user's language: what you made, and what the user can ask to change"""

CONSIGNE_CORRIGER = """Here is the animation you wrote before (sections below). {pourquoi}
Rewrite the WHOLE animation with the same answer format and the same strict rules, keeping everything that was fine.
Re-read the user's original request first: every event it describes must be in the PLAN and really visible in the animation
(if something was missing, add it now), and nothing may happen after the duration.

{code}"""


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
                           dmax=DUREE_MAX)


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
        hist = (hist + [{k: lib.get(k, "") for k in ("css", "html", "js", "tsx", "moteur", "plan")}])[-5:]
    remotion = bool(s.get("tsx", "").strip()) and moteur_de(a) == "remotion"
    if remotion:
        lib.update(css="", html="", js="", tsx=s.get("tsx", ""), moteur="remotion")
    else:
        lib.update(css=s.get("css", ""), html=s.get("html", ""), js=s.get("js", ""), tsx="", moteur="hyperframes")
    lib.update(message=s.get("message", ""), historique=hist, plan=lire_plan(s.get("plan", "")))
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
            "\n".join(f"{a:g}-{b:g} s: {t}" for a, b, t in (lib.get("plan") or []))]
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
    v.setdefault("moteur", "remotion" if v.get("tsx") else "hyperframes")
    lib.update(v)
    if v["moteur"] in MOTEURS_LIBRES:
        a["moteur_libre"] = v["moteur"]
    return a


GABARIT = r"""<!doctype html>
<html lang="{langue}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={L}, height={H}" />
<script src="{gsap}"></script>
<style>
{polices}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {L}px; height: {H}px; overflow: hidden; background: {fond_page}; }}
#racine {{ position: relative; width: {L}px; height: {H}px; overflow: hidden; font-family: "{police_texte}", "Poppins", sans-serif;
  color: {texte}; }}
.clip {{ position: absolute; inset: 0; }}
{css}
</style>
</head>
<body>
<div id="racine" data-composition-id="philcut" data-start="0" data-duration="{duree}" data-width="{L}" data-height="{H}"
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
const $ = (tag, style, parent, texte) => {{ const e = document.createElement(tag); if (style) e.setAttribute("style", style);
  if (texte !== undefined) e.textContent = texte; (parent || document.getElementById("scenes")).appendChild(e); return e; }};
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
    lib = anim.get("libre") or {}
    duree = float(anim.get("duree") or 8)
    css_polices = "\n".join(f'@font-face {{ font-family: "{H_.escape(fam)}"; src: url("{H_.escape(f)}"); font-weight: {poids}; }}'
                            for fam, f, poids in polices)
    js_logo = ""
    if logo:
        h = int(70 * min(L, H) / 1080)
        js_logo = ("{ const im = document.createElement('img'); im.src = " + json.dumps(logo) + "; im.setAttribute('style', " +
                   json.dumps(f"position:absolute;height:{h}px;right:{int(L * 0.05)}px;top:{int(H * 0.05)}px;opacity:0.9") +
                   "); document.getElementById('racine').appendChild(im); }")
    return GABARIT.format(
        langue=H_.escape(_langue_ui()), L=L, H=H, gsap=H_.escape(gsap), polices=css_polices,
        fond_page="transparent" if anim.get("transparent") else H_.escape(ch["couleurs"]["fond"]),
        police_texte=H_.escape(ch.get("police_texte") or "Poppins"), texte=H_.escape(ch["couleurs"]["texte"]),
        css=lib.get("css", "").replace("</", "<\\/"), html=lib.get("html", ""), duree=f"{duree:g}",
        cadence=int(anim.get("cadence") or 30), transparent="true" if anim.get("transparent") else "false",
        langue_js=json.dumps(_langue_ui()), couleurs=json.dumps(ch["couleurs"]),
        polices_js=json.dumps({"titre": ch.get("police_titre") or "Poppins", "texte": ch.get("police_texte") or "Poppins"}),
        js=lib.get("js", "").replace("</script", "<\\/script"), logo=js_logo)


def apercu_leger(anim, echelle=0.5, cadence=15):
    """La même animation, plus petite et à 15 images par seconde : l'aperçu se rend en quelques secondes. Le code écrit en
    multiples de u s'adapte tout seul."""
    a = copy.deepcopy(anim)
    L, H = anim.get("taille") or (1920, 1080)
    a["taille"] = [int(L * echelle) // 2 * 2, int(H * echelle) // 2 * 2]
    a["cadence"] = cadence
    return a
