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
===CSS===
the CSS (classes you use; #scenes already exists)
===HTML===
static HTML put inside #scenes (may be empty if you build everything in JS)
===JS===
the JavaScript that builds the elements and the timeline (it runs after the HTML is in place)
===MESSAGE===
one or two sentences in the user's language: what you made, and what the user can ask to change"""

CONSIGNE_CORRIGER = """Here is the animation you wrote before (sections below). {pourquoi}
Rewrite the WHOLE animation with the same answer format and the same strict rules, keeping everything that was fine.

{code}"""


def fiche(description, taille=(1920, 1080), duree=0.0, charte=None, transparent=False):
    return {"genre": "libre", "description": description.strip(), "taille": list(taille), "duree": float(duree or 0),
            "charte": charte, "transparent": bool(transparent), "cadence": 30, "titre": "",
            "libre": {"css": "", "html": "", "js": "", "message": "", "historique": []}}


def _format(L, H):
    if L == H:
        return "square 1:1"
    return "vertical 9:16" if H > L else "horizontal 16:9"


def consigne(anim):
    from .motion import _langue_ui
    L, H = anim.get("taille") or (1920, 1080)
    return CONSIGNE.format(langue=_langue_ui(), L=L, H=H, format=_format(L, H), duree=f"{anim.get('duree') or 8:g}",
                           dmax=DUREE_MAX)


def sections(texte):
    """Les sections de la réponse (===TITRE===, ===DUREE===, ===CSS===, ===HTML===, ===JS===, ===MESSAGE===)."""
    t = re.sub(r"^```[a-z]*\s*|\s*```$", "", (texte or "").strip())
    morceaux = re.split(r"^\s*===\s*([A-Z]+)\s*===\s*$", t, flags=re.M)
    out = {}
    for i in range(1, len(morceaux) - 1, 2):
        out[morceaux[i].lower()] = morceaux[i + 1].strip("\n")
    if not out.get("js", "").strip():
        raise ValueError(_("L'IA n'a pas rendu d'animation lisible (section JS absente). Réessayez."))
    for cle in ("css", "html", "js"):                 # des balises de code oubliées dans une section
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


def appliquer(anim, s, demande=""):
    a = copy.deepcopy(anim)
    lib = a.setdefault("libre", {})
    hist = lib.get("historique") or []
    if lib.get("js"):
        hist = (hist + [{k: lib.get(k, "") for k in ("css", "html", "js")}])[-5:]
    lib.update(css=s.get("css", ""), html=s.get("html", ""), js=s.get("js", ""), message=s.get("message", ""), historique=hist)
    if demande:
        lib.setdefault("demandes", []).append(demande)
    try:
        d = float(re.findall(r"[\d.]+", s.get("duree", ""))[0])
        if not a.get("duree_imposee"):
            a["duree"] = max(2.0, min(DUREE_MAX, d))
    except (IndexError, ValueError):
        a["duree"] = a.get("duree") or 8.0
    a["titre"] = (s.get("titre") or "").strip()[:80] or a.get("titre") or _("Animation libre")
    return a


def _code(anim):
    lib = anim.get("libre") or {}
    return "\n".join(["===TITRE===", anim.get("titre", ""), "===DUREE===", f"{anim.get('duree') or 8:g}", "===CSS===",
                      lib.get("css", ""), "===HTML===", lib.get("html", ""), "===JS===", lib.get("js", ""), "===MESSAGE===",
                      lib.get("message", "")])


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
    lib.update(lib["historique"].pop())
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
