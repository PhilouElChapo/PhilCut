"""Animations rendues par HyperFrames (0.9.99 / 1.0.0) : la même animation que le moteur maison, écrite en HTML + GSAP, rendue
- sur ce poste par HyperFrames (HeyGen, libre, Apache 2.0 : un Chrome invisible capture chaque image, FFmpeg encode), moteur
  « motion » installé une fois par PhilCut (Node portable, HyperFrames, GSAP, Chrome sans fenêtre) ;
- ou chez HeyGen (rendu cloud payé à la minute, clef HeyGen de l'utilisateur, prix demandé avant).

Le projet HyperFrames écrit par PhilCut est un dossier autonome (index.html, gsap.min.js, polices, logo) : le même dossier
part tel quel chez HeyGen (zip), s'ouvre dans HyperFrames Studio, ou dans Claude Code pour qui veut le retoucher à la main.
"""
import hashlib, html, json, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request, uuid, zipfile

from .langue import _
from . import motion as M

GSAP_CDN = "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"
HEYGEN = "https://api.heygen.com"


class ErreurMotion(Exception):
    pass


# ------------------------------------------------------------------ le moteur sur ce poste
def dossier_moteur():
    from . import packs_ia
    return packs_ia.dossier_moteur("motion")


def node():
    from . import packs_ia
    return packs_ia.executable("motion")


def cli_hyperframes():
    return os.path.join(dossier_moteur(), "app", "node_modules", "hyperframes", "bin", "hyperframes.mjs")


def navigateur():
    """Le Chrome sans fenêtre livré avec le moteur (chrome-headless-shell)."""
    base = os.path.join(dossier_moteur(), "chrome")
    nom = "chrome-headless-shell.exe" if sys.platform == "win32" else "chrome-headless-shell"
    for racine, _d, fichiers in os.walk(base):
        if nom in fichiers:
            return os.path.join(racine, nom)
    return ""


def gsap_local():
    f = os.path.join(dossier_moteur(), "app", "node_modules", "gsap", "dist", "gsap.min.js")
    return f if os.path.exists(f) else ""


def local_pret():
    from . import packs_ia
    try:
        return packs_ia.moteur_installe("motion") and os.path.exists(cli_hyperframes()) and bool(navigateur())
    except Exception:      # noqa: BLE001
        return False


# ------------------------------------------------------------------ la composition
def _css_couleur(c):
    return html.escape(c or "#000000")


def mise_en_page(anim):
    from . import charte as CH
    L, H = [int(x) // 2 * 2 for x in (anim.get("taille") or (1920, 1080))]
    zx, zy, zw, zh = M.zone_sure(dict(anim, taille=[L, H]))
    vertical = H > L
    base = min(zw / 950.0, zh / 1300.0) if vertical else min(zw / 1600.0, zh / 880.0)
    u = base * M.reglage(anim, "taille_texte")
    ch = CH.complete(anim.get("charte"))
    mouv = {"doux": 0.5, "vif": 1.0, "rebond": 1.6}.get(ch.get("mouvement"), 1.0)
    d = [[str(l), float(v)] for l, v in (anim.get("donnees") or M.EXEMPLE)]
    valeur = float(anim.get("valeur") if anim.get("valeur") is not None else sum(v for _l, v in d))
    return {"L": L, "H": H, "zx": zx, "zy": zy, "zw": zw, "zh": zh, "u": u, "vertical": vertical,
            "genre": anim.get("genre") or "chiffres", "duree": float(anim.get("duree") or M.duree_conseillee(anim.get("genre"))),
            "vitesse": M.reglage(anim, "vitesse"), "rebond": max(0.0, min(1.0, M.reglage(anim, "rebond") * mouv)),
            "decalage": 0.06 + 0.22 * M.reglage(anim, "decalage"), "epaisseur": M.reglage(anim, "epaisseur"),
            "lueur": M.reglage(anim, "lueur") * (0.0 if ch.get("allure") == "sobre" else 1.0),
            "fond_anime": not anim.get("transparent") and ch.get("allure") != "sobre" and anim.get("variante") != 2,
            "transparent": bool(anim.get("transparent")), "couleurs": ch["couleurs"],
            "titre": anim.get("titre") or "", "sous_titre": anim.get("sous_titre") or "", "badge": anim.get("badge") or "",
            "titre_barres": anim.get("titre_barres") or anim.get("titre") or "", "titre_courbe": anim.get("titre_courbe") or "",
            "sous_titre_courbe": anim.get("sous_titre_courbe") or anim.get("sous_titre") or "",
            "source": (_("Source : {s}", s=anim["source"]) if (anim.get("source") or "").strip() else ""),
            "donnees": d, "valeur": valeur, "textes_valeurs": [M.nombre_texte(anim, v) for _l, v in d],
            "texte_valeur": M.nombre_texte(anim, valeur), "prefixe": anim.get("prefixe") or "", "suffixe": anim.get("suffixe") or "",
            "decimales": anim.get("decimales") or 0, "langue": M._langue_ui(), "record": _("Record"),
            "police_titre": ch.get("police_titre") or "Poppins", "police_texte": ch.get("police_texte") or "Poppins"}


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
.tache {{ position: absolute; border-radius: 50%; }}
.grille {{ position: absolute; inset: 0; background-image: linear-gradient(#ffffff10 1px, transparent 1px),
  linear-gradient(90deg, #ffffff10 1px, transparent 1px); background-size: {pas}px {pas}px;
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%);
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 75%); }}
.zone {{ position: absolute; left: {zx}px; top: {zy}px; width: {zw}px; height: {zh}px; }}
.panneau {{ position: absolute; left: {px}px; top: {py}px; width: {pw}px; height: {ph}px; border-radius: {pr}px;
  background: {fond}b8; }}
.titre {{ font-family: "{police_titre}", "Poppins", sans-serif; font-weight: 700; color: {texte}; white-space: nowrap; }}
.doux {{ color: {doux}; }}
.chiffre {{ font-family: "{police_titre}", "Poppins", sans-serif; font-weight: 700; font-variant-numeric: tabular-nums;
  background-image: linear-gradient(100deg, {texte} 30%, {accent} 70%, {accent2}); -webkit-background-clip: text;
  background-clip: text; color: transparent; }}
.pastille {{ display: inline-block; border-radius: 999px; font-weight: 600; color: {fond};
  background: linear-gradient(90deg, {accent2}, {accent}); }}
.source {{ position: absolute; left: 0; bottom: -{s40}px; font-size: {s22}px; color: {doux}; }}
</style>
</head>
<body>
<div id="racine" data-composition-id="philcut" data-start="0" data-duration="{duree}" data-width="{L}" data-height="{H}"
  data-fps="{cadence}">
  <div id="fond" class="clip" data-start="0" data-duration="{duree}" data-track-index="0"></div>
  <div id="scenes" class="clip" data-start="0" data-duration="{duree}" data-track-index="1"></div>
</div>
<script>
const A = {donnees};
const tl = gsap.timeline({{ paused: true }});
window.__timelines = window.__timelines || {{}};
window.__timelines["philcut"] = tl;
const u = A.u, C = A.couleurs, V = A.vitesse;
const $ = (tag, style, parent, texte) => {{ const e = document.createElement(tag); if (style) e.setAttribute("style", style);
  if (texte !== undefined) e.textContent = texte; (parent || document.getElementById("scenes")).appendChild(e); return e; }};
const nombre = (v) => {{ const t = Number(v).toLocaleString(A.langue === "fr" ? "fr-FR" : A.langue,
  {{ minimumFractionDigits: A.decimales, maximumFractionDigits: A.decimales }});
  return A.prefixe + (A.langue === "fr" ? t.replace(/[  ]/g, " ") : t) + A.suffixe; }};
const haut = (v) => {{ if (v <= 0) return 1; const e = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * e >= v) return m * e; return 10 * e; }};
const ressort = A.rebond > 0.05 ? "back.out(" + (0.6 + 2.4 * A.rebond).toFixed(2) + ")" : "power3.out";
const sortie = "expo.out";
const T = (s) => s / V;
const fond = document.getElementById("fond");
if (!A.transparent) {{
  fond.style.background = C.fond;
  if (A.fond_anime) {{
    const e = Math.max(A.L, A.H) / 1920;
    const t1 = $("div", `width:${{1400 * e}}px;height:${{1400 * e}}px;left:${{-300 * e}}px;top:${{-700 * e}}px;` +
      `background:radial-gradient(circle, ${{C.accent}}${{Math.round(51 * Math.max(A.lueur, 0.3)).toString(16).padStart(2, "0")}} 0%, transparent 60%)`, fond);
    t1.className = "tache";
    const t2 = $("div", `width:${{1200 * e}}px;height:${{1200 * e}}px;right:${{-400 * e}}px;bottom:${{-700 * e}}px;` +
      `background:radial-gradient(circle, ${{C.accent2}}22 0%, transparent 60%)`, fond);
    t2.className = "tache";
    tl.to(t1, {{ x: 60 * e, y: 50 * e, duration: A.duree, ease: "sine.inOut" }}, 0);
    tl.to(t2, {{ x: -50 * e, y: -40 * e, duration: A.duree, ease: "sine.inOut" }}, 0);
    $("div", "", fond).className = "grille";
  }}
}}
function scene(debut, fin, dernier) {{
  const s = $("div", "position:absolute;inset:0;opacity:0");
  tl.to(s, {{ opacity: 1, duration: T(0.5), ease: sortie }}, debut);
  if (!dernier) tl.to(s, {{ opacity: 0, scale: 0.94, duration: T(0.5), ease: "power3.in" }}, fin - T(0.5));
  if (A.transparent) {{ const m = 30 * u; const p = $("div", "", s); p.className = "panneau"; }}
  const z = $("div", "", s); z.className = "zone";
  if (A.source) {{ const q = $("div", "", z, A.source); q.className = "source"; }}
  return z;
}}
function compteur(debut, fin, dernier) {{
  const z = scene(debut, fin, dernier);
  const bloc = $("div", "position:absolute;left:0;right:0;top:" + (A.vertical ? 0.42 : 0.48) * A.zh + "px;transform:translateY(-50%);" +
    "text-align:center", z);
  const lab = $("div", `font-size:${{34 * u}}px;font-weight:600;letter-spacing:${{6 * u}}px;text-transform:uppercase;color:${{C.doux}}`, bloc, A.titre);
  const ch = $("div", `font-size:${{260 * u * (A.vertical ? 0.8 : 1)}}px;line-height:1;margin-top:${{18 * u}}px;` +
    `filter:drop-shadow(0 ${{20 * u}}px ${{60 * u}}px ${{C.accent}}${{Math.round(85 * A.lueur).toString(16).padStart(2, "0")}})`, bloc, nombre(0));
  ch.className = "chiffre";
  tl.from(lab, {{ opacity: 0, y: 20 * u, duration: T(0.6), ease: sortie }}, debut);
  const o = {{ v: 0 }};
  // modifiers (pas onUpdate) : appliqués à chaque rendu, même quand le moteur se place à un instant sans déclencher d'événements
  tl.to(o, {{ v: A.valeur, duration: T(2.3), ease: "power3.out", modifiers: {{ v: (v) => {{ ch.textContent = nombre(v); return v; }} }} }}, debut + T(0.3));
  if (A.badge) {{
    const b = $("div", `margin-top:${{36 * u}}px;padding:${{14 * u}}px ${{30 * u}}px;font-size:${{38 * u}}px`, bloc, A.badge);
    b.className = "pastille";
    tl.from(b, {{ scale: 0, opacity: 0, duration: T(0.8), ease: ressort }}, debut + T(2.4));
  }}
}}
function barres(debut, fin, dernier) {{
  const z = scene(debut, fin, dernier);
  const t = $("div", `position:absolute;left:0;top:${{0}}px;font-size:${{64 * u}}px`, z, A.titre_barres); t.className = "titre";
  $("div", `position:absolute;left:0;top:${{80 * u}}px;font-size:${{30 * u}}px;color:${{C.doux}}`, z, A.sous_titre);
  const top = 190 * u, bas = A.zh - 60 * u, Hc = bas - top, gauche = 110 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1])));
  for (let i = 0; i < 5; i++) {{
    const y = bas - (i / 4) * Hc;
    const l = $("div", `position:absolute;left:${{gauche}}px;right:0;top:${{y}}px;height:1px;background:${{C.texte}}1c;transform-origin:left`, z);
    const n = $("div", `position:absolute;left:0;top:${{y - 14 * u}}px;font-size:${{22 * u}}px;color:${{C.doux}}`, z, nombre(vmax * i / 4).replace(A.prefixe, "").replace(A.suffixe, ""));
    tl.from(l, {{ scaleX: 0, duration: T(0.7), ease: sortie }}, debut + T(0.2 + i * 0.1));
    tl.from(n, {{ opacity: 0, duration: T(0.7) }}, debut + T(0.2 + i * 0.1));
  }}
  const nb = A.donnees.length, ecart = 46 * u * (nb > 8 ? 0.6 : 1);
  const larg = (A.zw - gauche - ecart * (nb - 1)) / nb, lb = larg * (0.45 + 0.55 * A.epaisseur);
  let rec = 0; A.donnees.forEach((d, i) => {{ if (d[1] > A.donnees[rec][1]) rec = i; }});
  A.donnees.forEach((d, i) => {{
    const x = gauche + i * (larg + ecart) + (larg - lb) / 2, h = (d[1] / vmax) * Hc, record = i === rec;
    const b = $("div", `position:absolute;left:${{x}}px;width:${{lb}}px;top:${{bas - h}}px;height:${{h}}px;transform-origin:bottom;` +
      `border-radius:${{18 * u}}px ${{18 * u}}px ${{6 * u}}px ${{6 * u}}px;background:` +
      (record ? `linear-gradient(180deg, ${{C.accent2}}, ${{C.accent}})` : `linear-gradient(180deg, ${{C.accent}}cc, ${{C.accent}}44)`), z);
    const v = $("div", `position:absolute;left:${{x - 40 * u}}px;width:${{lb + 80 * u}}px;text-align:center;top:${{bas - h - 50 * u}}px;` +
      `font-size:${{32 * u * (nb > 8 ? 0.8 : 1)}}px;color:${{record ? C.accent2 : C.texte}}`, z, A.textes_valeurs[i]); v.className = "titre";
    $("div", `position:absolute;left:${{x - 40 * u}}px;width:${{lb + 80 * u}}px;text-align:center;top:${{bas + 12 * u}}px;` +
      `font-size:${{26 * u * (nb > 8 ? 0.8 : 1)}}px;color:${{C.doux}}`, z, d[0]);
    const t0 = debut + T(0.6 + i * A.decalage);
    tl.from(b, {{ scaleY: 0, duration: T(1.0), ease: ressort }}, t0);
    tl.from(v, {{ y: h, opacity: 0, duration: T(1.0), ease: ressort }}, t0);
    if (record && A.lueur > 0) tl.to(b, {{ boxShadow: `0 0 ${{60 * u * A.lueur}}px ${{C.accent2}}88`, duration: T(0.6) }}, debut + T(2.6));
  }});
}}
function courbe(debut, fin, dernier) {{
  const z = scene(debut, fin, dernier);
  const t = $("div", `position:absolute;left:0;top:0;font-size:${{64 * u}}px`, z, A.titre_courbe); t.className = "titre";
  $("div", `position:absolute;left:0;top:${{80 * u}}px;font-size:${{30 * u}}px;color:${{C.doux}}`, z, A.sous_titre_courbe);
  const top = 230 * u, bas = A.zh - 90 * u, g = 20 * u, d_ = A.zw - 20 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1]))), nb = A.donnees.length;
  const pts = A.donnees.map((d, i) => [g + (i / Math.max(1, nb - 1)) * (d_ - g), bas - (d[1] / vmax) * (bas - top)]);
  let dd = `M ${{pts[0][0]}} ${{pts[0][1]}}`;
  for (let i = 1; i < nb; i++) {{ const [px, py] = pts[i - 1], [x, y] = pts[i], cx = (px + x) / 2; dd += ` C ${{cx}} ${{py}}, ${{cx}} ${{y}}, ${{x}} ${{y}}`; }}
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg"); svg.setAttribute("width", A.zw); svg.setAttribute("height", A.zh);
  svg.setAttribute("style", "position:absolute;left:0;top:0;overflow:visible"); z.appendChild(svg);
  svg.innerHTML = `<defs><linearGradient id="trait" x1="0" x2="1"><stop offset="0%" stop-color="${{C.accent}}"/><stop offset="100%" stop-color="${{C.accent2}}"/></linearGradient>` +
    `<linearGradient id="aire" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="${{C.accent}}" stop-opacity="0.35"/><stop offset="100%" stop-color="${{C.accent}}" stop-opacity="0"/></linearGradient>` +
    `<clipPath id="revele"><rect id="rideau" x="0" y="-50" width="0" height="${{A.zh + 100}}"/></clipPath></defs>` +
    `<path d="${{dd}} L ${{d_}} ${{bas}} L ${{g}} ${{bas}} Z" fill="url(#aire)" clip-path="url(#revele)"/>` +
    `<path id="trace" d="${{dd}}" fill="none" stroke="url(#trait)" stroke-width="${{8 * u * (0.5 + A.epaisseur)}}" stroke-linecap="round" clip-path="url(#revele)"` +
    ` style="filter:drop-shadow(0 0 ${{18 * u * A.lueur}}px ${{C.accent}}aa)"/>`;
  const rideau = svg.querySelector("#rideau");
  const pointsSvg = pts.map(([x, y]) => {{ const c = document.createElementNS(ns, "circle"); c.setAttribute("cx", x); c.setAttribute("cy", y);
    c.setAttribute("r", 7 * u); c.setAttribute("fill", C.fond); c.setAttribute("stroke", C.texte); c.setAttribute("stroke-width", 3 * u);
    c.setAttribute("opacity", 0); svg.appendChild(c); return c; }});
  A.donnees.forEach((d, i) => $("div", `position:absolute;left:${{pts[i][0] - 60 * u}}px;width:${{120 * u}}px;text-align:center;top:${{bas + 18 * u}}px;` +
    `font-size:${{24 * u}}px;color:${{C.doux}}`, z, d[0]));
  const pt = document.createElementNS(ns, "circle"); pt.setAttribute("r", 16 * u); pt.setAttribute("fill", C.accent2);
  pt.setAttribute("style", `filter:drop-shadow(0 0 ${{20 * u}}px ${{C.accent2}})`); pt.setAttribute("opacity", 0); svg.appendChild(pt);
  const o = {{ p: 0 }};
  const placer = (p) => {{
    const k = Math.min(nb - 1, p * (nb - 1)), i0 = Math.floor(k), f = k - i0, a = pts[i0], b = pts[Math.min(nb - 1, i0 + 1)];
    const x = a[0] + (b[0] - a[0]) * f, y = a[1] + (b[1] - a[1]) * f;
    rideau.setAttribute("width", x + 1); pt.setAttribute("cx", x); pt.setAttribute("cy", y); pt.setAttribute("opacity", p > 0 ? 1 : 0);
    pointsSvg.forEach((c, i) => c.setAttribute("opacity", p > 0 && k >= i - 1e-6 ? 1 : 0)); return p; }};
  tl.to(o, {{ p: 1, duration: T(2.4), ease: "power2.inOut", modifiers: {{ p: placer }} }}, debut + T(0.4));
  let rec = 0; A.donnees.forEach((d, i) => {{ if (d[1] > A.donnees[rec][1]) rec = i; }});
  const w = 300 * u, h = 96 * u, x = Math.min(Math.max(0, pts[rec][0] - w - 40 * u), A.zw - w), y = Math.max(130 * u, pts[rec][1] - 60 * u - h);
  const carte = $("div", `position:absolute;left:${{x}}px;top:${{y}}px;width:${{w}}px;height:${{h}}px;border-radius:${{20 * u}}px;` +
    `background:#ffffff12;border:1px solid #ffffff30;padding:${{14 * u}}px ${{28 * u}}px`, z);
  $("div", `font-size:${{24 * u}}px;color:${{C.doux}}`, carte, A.record);
  const cv = $("div", `font-size:${{38 * u}}px`, carte, A.textes_valeurs[rec]); cv.className = "titre";
  tl.from(carte, {{ opacity: 0, y: 30 * u, duration: T(0.8), ease: ressort }}, debut + T(2.8));
}}
function titre(debut, fin, dernier) {{
  const z = scene(debut, fin, true);
  const bloc = $("div", "position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);text-align:center", z);
  const mots = A.titre.split(/\s+/).filter(Boolean);
  const cle = mots.length > 2 ? mots.reduce((a, b) => (b.replace(/[.,;:!?«»"']/g, "").length > a.replace(/[.,;:!?«»"']/g, "").length ? b : a)) : "";
  const ligne = $("div", `font-size:${{120 * u * (A.vertical ? 0.75 : 1)}}px;line-height:1.05;white-space:normal`, bloc); ligne.className = "titre";
  mots.forEach((m, k) => {{ const s = $("span", `display:inline-block;margin:0 ${{14 * u}}px;color:${{m === cle ? C.accent : C.texte}}`, ligne, m);
    tl.from(s, {{ y: 60 * u, opacity: 0, duration: T(0.8), ease: ressort }}, debut + T(0.15 + k * A.decalage)); }});
  const trait = $("div", `width:${{A.zw * 0.22}}px;height:${{8 * u * (0.5 + A.epaisseur)}}px;border-radius:${{4 * u}}px;background:${{C.accent2}};` +
    `margin:${{30 * u}}px auto 0;transform-origin:center`, bloc);
  tl.from(trait, {{ scaleX: 0, duration: T(0.8), ease: sortie }}, debut + T(0.4 + mots.length * A.decalage * 0.5));
  if (A.sous_titre) {{ const st = $("div", `font-size:${{40 * u}}px;color:${{C.doux}};margin-top:${{24 * u}}px`, bloc, A.sous_titre);
    tl.from(st, {{ opacity: 0, duration: T(0.6) }}, debut + T(0.8)); }}
  tl.to(bloc, {{ opacity: 0, duration: T(0.6), ease: "power3.in" }}, fin - T(0.6));
}}
const D = A.duree;
if (A.genre === "compteur") compteur(0, D, true);
else if (A.genre === "barres") barres(0, D, true);
else if (A.genre === "courbe") courbe(0, D, true);
else if (A.genre === "titre") titre(0, D, true);
else {{ compteur(0, D * 4.3 / 14, false); barres(D * 4.0 / 14, D * 9.4 / 14, false); courbe(D * 9.2 / 14, D, true); }}
{logo}
tl.set({{}}, {{}}, D);
tl.seek(0);
</script>
</body>
</html>
"""


def composition(anim, gsap="gsap.min.js", polices=(), logo=""):
    """Le HTML de l'animation (une composition HyperFrames autonome)."""
    m = mise_en_page(anim)
    c = m["couleurs"]
    css_polices = "\n".join(f'@font-face {{ font-family: "{html.escape(fam)}"; src: url("{html.escape(f)}"); font-weight: {poids}; }}'
                            for fam, f, poids in polices)
    js_logo = ""
    if logo:
        h = int(70 * m["u"] * (1.3 if m["vertical"] else 1.0))
        js_logo = ("{ const im = document.createElement('img'); im.src = " + json.dumps(logo) + "; im.setAttribute('style', " +
                   json.dumps(f"position:absolute;height:{h}px;right:{m['L'] - m['zx'] - m['zw']}px;top:{max(0, int(m['zy'] - h * 1.2))}px;opacity:0.9") +
                   "); document.getElementById('racine').appendChild(im); }")
    m30 = 30 * m["u"]
    return GABARIT.format(
        langue=html.escape(m["langue"]), L=m["L"], H=m["H"], gsap=html.escape(gsap), polices=css_polices,
        fond_page="transparent" if m["transparent"] else _css_couleur(c["fond"]), police_texte=html.escape(m["police_texte"]),
        police_titre=html.escape(m["police_titre"]), texte=_css_couleur(c["texte"]), doux=_css_couleur(c["doux"]),
        accent=_css_couleur(c["accent"]), accent2=_css_couleur(c["accent2"]), fond=_css_couleur(c["fond"]),
        pas=max(20, int(80 * max(m["L"], m["H"]) / 1920)), zx=m["zx"], zy=m["zy"], zw=m["zw"], zh=m["zh"],
        px=int(m["zx"] - m30), py=int(m["zy"] - m30), pw=int(m["zw"] + 2 * m30), ph=int(m["zh"] + 2 * m30), pr=int(36 * m["u"]),
        s40=int(40 * m["u"]), s22=int(22 * m["u"]), duree=f"{m['duree']:g}", cadence=int(anim.get("cadence") or 30),
        donnees=json.dumps(m, ensure_ascii=False).replace("</", "<\\/"), logo=js_logo)


POLICES_LIVREES = {"Poppins": [("Poppins-Regular.ttf", 400), ("Poppins-SemiBold.ttf", 600), ("Poppins-Bold.ttf", 700)],
                   "Anton": [("Anton-Regular.ttf", 400)], "Bebas Neue": [("BebasNeue-Regular.ttf", 400)],
                   "Nunito": [("Nunito-400.ttf", 400), ("Nunito-600.ttf", 600), ("Nunito-800.ttf", 800)]}


def _dossier_polices():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "fonts")


def preparer_projet(anim, dossier, gsap_en_ligne=False):
    """Ecrit le projet HyperFrames autonome (index.html, gsap, polices livrées, logo) ; renvoie le dossier."""
    from . import charte as CH
    os.makedirs(os.path.join(dossier, "assets"), exist_ok=True)
    ch = CH.complete(anim.get("charte"))
    polices = []
    for fam in {ch.get("police_titre") or "Poppins", ch.get("police_texte") or "Poppins", "Poppins"}:
        for f, poids in POLICES_LIVREES.get(fam, []):
            src = os.path.join(_dossier_polices(), f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dossier, "assets", f))
                polices.append((fam, "assets/" + f, poids))
    gsap = GSAP_CDN
    if not gsap_en_ligne and gsap_local():
        shutil.copy2(gsap_local(), os.path.join(dossier, "assets", "gsap.min.js"))
        gsap = "assets/gsap.min.js"
    logo = ""
    if ch.get("logo") and os.path.exists(ch["logo"]) and anim.get("logo") is not False:
        nom = "logo" + os.path.splitext(ch["logo"])[1].lower()
        shutil.copy2(ch["logo"], os.path.join(dossier, "assets", nom))
        logo = "assets/" + nom
    with open(os.path.join(dossier, "index.html"), "w", encoding="utf-8") as f:
        f.write(composition(anim, gsap, polices, logo))
    json.dump({"id": "philcut", "name": anim.get("titre") or "PhilCut"}, open(os.path.join(dossier, "meta.json"), "w", encoding="utf-8"))
    json.dump(dict(anim), open(os.path.join(dossier, "philcut-animation.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return dossier


# ------------------------------------------------------------------ rendu sur ce poste
def _env():
    from . import moteur
    from .config import dossier_donnees
    env = dict(os.environ)
    nav = navigateur()
    env.update({"HYPERFRAMES_BROWSER_PATH": nav, "PRODUCER_HEADLESS_SHELL_PATH": nav, "HYPERFRAMES_FFMPEG_PATH": moteur.ffmpeg(),
                "HYPERFRAMES_NO_TELEMETRY": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1", "HYPERFRAMES_SKIP_SKILLS": "1",
                "HYPERFRAMES_CONFIG_DIR": os.path.join(dossier_donnees(), "hyperframes"), "NO_COLOR": "1", "CI": "1"})
    fp = getattr(moteur, "ffprobe", None)
    if callable(fp):
        env["HYPERFRAMES_FFPROBE_PATH"] = fp()
    env["PATH"] = os.path.dirname(node()) + os.pathsep + os.path.dirname(moteur.ffmpeg()) + os.pathsep + env.get("PATH", "")
    return env


def commande(dossier, sortie, anim):
    fmt = "mov" if anim.get("transparent") else "mp4"
    return [node(), cli_hyperframes(), "render", dossier, "-o", sortie, "--format", fmt, "--fps", str(int(anim.get("cadence") or 30)),
            "--quality", "delivery" if fmt == "mp4" else "looks", "--no-wait"]


def lire_progression(ligne):
    """Une ligne du rendu → fraction (0..1) ou None : « 45% », « frame 120/300 », « 120 / 300 frames »."""
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s?%", ligne)
    if m:
        return min(1.0, float(m.group(1)) / 100)
    m = re.search(r"(\d+)\s*/\s*(\d+)\s*(?:frames?|images?)?", ligne, re.I)
    if m and int(m.group(2)) > 0 and "frame" in ligne.lower():
        return min(1.0, int(m.group(1)) / int(m.group(2)))
    return None


def rendre_local(params, anim, sortie, progression=None, arret=lambda: False):
    from . import moteur
    if not local_pret():
        raise ErreurMotion(_("HyperFrames n'est pas installé sur ce poste : Préférences › IA locale › « Animations HyperFrames et "
                             "Remotion », ou choisissez le moteur maison."))
    sortie = os.path.splitext(sortie)[0] + (".mov" if anim.get("transparent") else ".mp4")
    d = os.path.join(M.dossier(), "projets", os.path.splitext(os.path.basename(sortie))[0])
    shutil.rmtree(d, ignore_errors=True)
    preparer_projet(anim, d)
    progression and progression(0.02, _("HyperFrames prépare le rendu"))
    proc = subprocess.Popen(commande(d, sortie, anim), cwd=d, env=_env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", **moteur._sans_console())
    dernieres = []
    try:
        for ligne in proc.stdout:
            dernieres = (dernieres + [ligne.rstrip()])[-40:]
            if arret():
                proc.kill()
                raise InterruptedError()
            f = lire_progression(ligne)
            if f is not None and progression:
                progression(0.05 + 0.93 * f, _("HyperFrames : rendu des images"))
        code = proc.wait()
    except BaseException:
        try:
            proc.kill()
        except OSError:
            pass
        raise
    if code != 0 or not os.path.exists(sortie):
        from .journal import ecrire
        ecrire("hyperframes", "\n".join(dernieres))
        raise ErreurMotion(_("Le rendu HyperFrames a échoué : {e}", e=" / ".join(x for x in dernieres[-3:] if x.strip())[-300:]))
    return sortie


# ------------------------------------------------------------------ rendu chez HeyGen
def _heygen(methode, chemin, cle, corps=None, delai=60):
    req = urllib.request.Request(HEYGEN + chemin, data=json.dumps(corps).encode() if corps is not None else None, method=methode,
                                 headers={"X-Api-Key": cle, "Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "PhilCut", "Idempotency-Key": str(uuid.uuid4())})
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        if e.code in (401, 403):
            raise ErreurMotion(_("Clef HeyGen refusée : {d}", d=detail)) from e
        if e.code == 402 or "insufficient" in detail.lower():
            raise ErreurMotion(_("Crédit HeyGen épuisé (rien n'a été rendu) : rechargez votre compte API HeyGen. {d}", d=detail)) from e
        raise ErreurMotion(f"HeyGen HTTP {e.code} : {detail}") from e


def zipper(dossier, archive):
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for racine, _d, fichiers in os.walk(dossier):
            for f in fichiers:
                if f.endswith(".zip"):
                    continue
                p = os.path.join(racine, f)
                z.write(p, os.path.relpath(p, dossier).replace(os.sep, "/"))
    return archive


def televerser_heygen(cle, archive):
    taille = os.path.getsize(archive)
    h = hashlib.sha256(open(archive, "rb").read()).hexdigest()
    r = _heygen("POST", "/v3/assets/direct-uploads", cle, {"filename": os.path.basename(archive), "content_type": "application/zip",
                                                           "size_bytes": taille, "checksum_sha256": h})
    d = r.get("data") or r
    entetes = dict(d.get("upload_headers") or {})
    with open(archive, "rb") as f:
        req = urllib.request.Request(d["upload_url"], data=f.read(), method="PUT", headers=entetes)
    with urllib.request.urlopen(req, timeout=600):
        pass
    _heygen("POST", f"/v3/assets/{d['asset_id']}/complete", cle, {"checksum_sha256": h})
    return d["asset_id"]


def rendre_cloud(params, anim, sortie, progression=None, arret=lambda: False):
    from . import generateurs_video as GV
    cle = GV.clef(params, "heygen")
    if not cle:
        raise ErreurMotion(_("Clef HeyGen absente : Préférences › Assistant et IA › Connecter une IA."))
    sortie = os.path.splitext(sortie)[0] + (".mov" if anim.get("transparent") else ".mp4")
    d = os.path.join(M.dossier(), "projets", os.path.splitext(os.path.basename(sortie))[0])
    shutil.rmtree(d, ignore_errors=True)
    preparer_projet(anim, d, gsap_en_ligne=not gsap_local())
    archive = zipper(d, d + ".zip")
    progression and progression(0.05, _("Envoi du projet à HeyGen"))
    asset = televerser_heygen(cle, archive)
    L, H = anim.get("taille") or (1920, 1080)
    corps = {"project": {"type": "asset_id", "asset_id": asset}, "fps": int(anim.get("cadence") or 30), "quality": "standard",
             "format": "mov" if anim.get("transparent") else "mp4", "resolution": "4k" if max(L, H) > 1920 else "1080p",
             "aspect_ratio": "9:16" if H > L else "16:9", "composition": "index.html", "title": (anim.get("titre") or "PhilCut")[:200]}
    r = _heygen("POST", "/v3/hyperframes/renders", cle, corps)
    rid = (r.get("data") or r).get("render_id")
    if not rid:
        raise ErreurMotion(_("HeyGen n'a pas accepté le rendu : {r}", r=str(r)[:300]))
    debut = time.time()
    while True:
        if arret():
            raise InterruptedError()
        time.sleep(3)
        e = _heygen("GET", f"/v3/hyperframes/renders/{rid}", cle).get("data") or {}
        st = e.get("status")
        if progression:
            progression(min(0.9, 0.1 + (time.time() - debut) / 240), _("HeyGen : {s}", s={"queued": _("en file d'attente"),
                                                                                         "rendering": _("rendu en cours")}.get(st, st or "…")))
        if st == "completed":
            break
        if st == "failed":
            raise ErreurMotion(_("Le rendu HeyGen a échoué : {m}", m=e.get("failure_message") or "?"))
        if time.time() - debut > 1800:
            raise ErreurMotion(_("HeyGen n'a pas fini en 30 minutes."))
    with urllib.request.urlopen(urllib.request.Request(e["video_url"], headers={"User-Agent": "PhilCut"}), timeout=600) as r, \
            open(sortie, "wb") as f:
        shutil.copyfileobj(r, f)
    return sortie


def credit_heygen(cle):
    """(montant, devise) : solde du portefeuille API HeyGen, ou None."""
    try:
        r = _heygen("GET", "/v3/users/me", cle, delai=15)
    except Exception:      # noqa: BLE001
        return None
    d = r.get("data") or r
    w = d.get("wallet") or {}
    if w.get("remaining_balance") is not None:
        return float(w["remaining_balance"]), "USD" if (w.get("currency") or "usd").lower() == "usd" else _("crédits")
    s = ((d.get("subscription") or {}).get("credits") or {}).get("premium_credits") or {}
    if s.get("remaining") is not None:
        return float(s["remaining"]), _("crédits")
    return None


def tester_heygen(cle):
    try:
        _heygen("GET", "/v3/users/me", cle, delai=20)
        return True, _("Clef HeyGen acceptée.")
    except ErreurMotion as e:
        return False, str(e)
    except Exception as e:      # noqa: BLE001
        return False, _("Test impossible : {e}", e=e)
