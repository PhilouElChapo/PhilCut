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
            "donnees": d, "valeur": valeur, "textes_valeurs": [_insecable(M.nombre_texte(anim, v)) for _l, v in d],
            "texte_valeur": _insecable(M.nombre_texte(anim, valeur)), "prefixe": anim.get("prefixe") or "", "suffixe": anim.get("suffixe") or "",
            "decimales": anim.get("decimales") or 0, "langue": M._langue_ui(), "record": _("Record"),
            "police_titre": ch.get("police_titre") or "Poppins", "police_texte": ch.get("police_texte") or "Poppins",
            "horaire": M.horaire(anim), "coins": float(ch.get("coins", 0.6)), "panneau": (anim.get("genre") or "chiffres") not in M.HABILLAGE,
            "mots": anim.get("mots") or [], "style_st": anim.get("style_st") or "surligne", "majuscules": anim.get("majuscules", True),
            "lignes_st": M.lignes_st(anim.get("mots") or [], M.ST_VERTICAL_CAR if vertical else M.ST_HORIZONTAL_CAR),
            "st_taille": M.ST_VERTICAL_TAILLE if vertical else 1.0, "chapitres": anim.get("chapitres") or [],
            "image": anim.get("_html_image") or "", "image_ratio": float(anim.get("_html_ratio") or 0),
            "calques": [dict(c, src=(anim.get("_html_calques") or {}).get(c["n"], ""), chemin="") for c in M.calques_images(anim)],
            "elements": [[_insecable(str(l)), (float(v) if v is not None else None), _insecable(str(t or "")),
                          _insecable(M.nombre_texte(anim, v) if v is not None else "")] for l, v, t in M.elements(anim)],
            "palette": M.palette(ch, len(M.elements(anim))),
            "bouton": anim.get("bouton") or _("S'abonner"), "bouton_fait": anim.get("bouton_fait") or _("Abonné ✓")}


def _insecable(t):
    """L'espace fine insécable (U+202F) manque à certaines polices (Poppins) dans Chrome : espace insécable ordinaire."""
    return (t or "").replace("\u202f", "\u00a0")


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
  return A.prefixe + t.replace(/[\u202f ]/g, "\u00a0") + A.suffixe; }};
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
(A.calques || []).forEach((k) => {{                      // 1.1.16 : une ou deux images, sous les textes
  if (!k.src) return;
  const im = document.createElement("img");
  im.src = k.src;
  im.setAttribute("style", `position:absolute;left:${{k.x}}px;top:${{k.y}}px;width:${{k.w}}px;height:${{k.h}}px;` +
    `object-fit:${{k.cover ? "cover" : "contain"}};opacity:0`);
  document.getElementById(k.cover ? "fond" : "scenes").appendChild(im);
  tl.fromTo(im, {{ opacity: 0, scale: 0.92 }}, {{ opacity: k.op, scale: 1, duration: 0.5, ease: "power2.out", immediateRender: false }}, k.t0);
  tl.to(im, {{ opacity: 0, duration: 0.4 }}, k.t1);
}});
{scenes}
{logo}
tl.set({{}}, {{}}, D);
tl.seek(0);
</script>
</body>
</html>
"""


JS_SCENES = r'''
// 1.0.0 : tout suit l'horaire commun (A.horaire, en secondes de l'animation) : calé sur la voix ou la musique s'il le faut
const Hr = A.horaire, D = A.duree;
const ressortDe = (k) => (A.rebond > 0.05 ? "back.out(" + (0.6 + 2.4 * A.rebond).toFixed(2) + ")" : "power3.out");
const fins = Math.max(...Object.values(Hr.scenes).map((x) => x[1]));
function scene(debut, fin, dernier) {
  const s = $("div", "position:absolute;inset:0;opacity:0");
  tl.to(s, { opacity: 1, duration: T(0.5), ease: sortie }, debut);
  if (!dernier) tl.to(s, { opacity: 0, scale: 0.94, duration: T(0.5), ease: "power3.in" }, fin - T(0.5));
  if (A.transparent && A.panneau) { const p = $("div", "", s); p.className = "panneau"; }
  const z = $("div", "", s); z.className = "zone";
  if (A.source) { const q = $("div", "", z, A.source); q.className = "source"; }
  return z;
}
function compteur(debut, fin, dernier) {
  const h = Hr.compteur, z = scene(debut, fin, dernier);
  const bloc = $("div", "position:absolute;left:0;right:0;top:" + (A.vertical ? 0.42 : 0.48) * A.zh + "px;transform:translateY(-50%);text-align:center", z);
  const lab = $("div", `font-size:${34 * u}px;font-weight:600;letter-spacing:${6 * u}px;text-transform:uppercase;color:${C.doux}`, bloc, A.titre);
  const ch = $("div", `font-size:${260 * u * (A.vertical ? 0.8 : 1)}px;line-height:1;margin-top:${18 * u}px;` +
    `filter:drop-shadow(0 ${20 * u}px ${60 * u}px ${C.accent}${Math.round(85 * A.lueur).toString(16).padStart(2, "0")})`, bloc, nombre(0));
  ch.className = "chiffre";
  tl.from(lab, { opacity: 0, y: 20 * u, duration: T(0.6), ease: sortie }, debut);
  const o = { v: 0 };
  // modifiers (pas onUpdate) : appliqués à chaque rendu, même quand le moteur se place à un instant sans déclencher d'événements
  tl.to(o, { v: A.valeur, duration: Math.max(0.2, h.fin - h.debut), ease: "power3.out", modifiers: { v: (v) => { ch.textContent = nombre(v); return v; } } }, h.debut);
  if (A.badge) {
    const b = $("div", `margin-top:${36 * u}px;padding:${14 * u}px ${30 * u}px;font-size:${38 * u}px`, bloc, A.badge);
    b.className = "pastille";
    tl.from(b, { scale: 0, opacity: 0, duration: T(0.8), ease: ressort }, h.badge);
  }
}
function barres(debut, fin, dernier) {
  const h = Hr.barres, z = scene(debut, fin, dernier);
  const t = $("div", `position:absolute;left:0;top:0;font-size:${64 * u}px`, z, A.titre_barres); t.className = "titre";
  $("div", `position:absolute;left:0;top:${80 * u}px;font-size:${30 * u}px;color:${C.doux}`, z, A.sous_titre);
  const top = 190 * u, bas = A.zh - 60 * u, Hc = bas - top, gauche = 110 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1])));
  for (let i = 0; i < 5; i++) {
    const y = bas - (i / 4) * Hc;
    const l = $("div", `position:absolute;left:${gauche}px;right:0;top:${y}px;height:1px;background:${C.texte}1c;transform-origin:left`, z);
    const n = $("div", `position:absolute;left:0;top:${y - 14 * u}px;font-size:${22 * u}px;color:${C.doux}`, z, nombre(vmax * i / 4).replace(A.prefixe, "").replace(A.suffixe, ""));
    tl.from(l, { scaleX: 0, duration: T(0.7), ease: sortie }, h.grille + T(i * 0.1));
    tl.from(n, { opacity: 0, duration: T(0.7) }, h.grille + T(i * 0.1));
  }
  const nb = A.donnees.length, ecart = 46 * u * (nb > 8 ? 0.6 : 1);
  const larg = (A.zw - gauche - ecart * (nb - 1)) / nb, lb = larg * (0.45 + 0.55 * A.epaisseur);
  let rec = 0; A.donnees.forEach((d, i) => { if (d[1] > A.donnees[rec][1]) rec = i; });
  A.donnees.forEach((d, i) => {
    const x = gauche + i * (larg + ecart) + (larg - lb) / 2, hh = (d[1] / vmax) * Hc, record = i === rec;
    const b = $("div", `position:absolute;left:${x}px;width:${lb}px;top:${bas - hh}px;height:${hh}px;transform-origin:bottom;` +
      `border-radius:${18 * u}px ${18 * u}px ${6 * u}px ${6 * u}px;background:` +
      (record ? `linear-gradient(180deg, ${C.accent2}, ${C.accent})` : `linear-gradient(180deg, ${C.accent}cc, ${C.accent}44)`), z);
    const v = $("div", `position:absolute;left:${x - 40 * u}px;width:${lb + 80 * u}px;text-align:center;top:${bas - hh - 50 * u}px;` +
      `font-size:${32 * u * (nb > 8 ? 0.8 : 1)}px;color:${record ? C.accent2 : C.texte}`, z, A.textes_valeurs[i]); v.className = "titre";
    $("div", `position:absolute;left:${x - 40 * u}px;width:${lb + 80 * u}px;text-align:center;top:${bas + 12 * u}px;` +
      `font-size:${26 * u * (nb > 8 ? 0.8 : 1)}px;color:${C.doux}`, z, d[0]);
    const t0 = h.entrees[Math.min(i, h.entrees.length - 1)];
    tl.from(b, { scaleY: 0, duration: T(1.0), ease: ressort }, t0);
    tl.from(v, { y: hh, opacity: 0, duration: T(1.0), ease: ressort }, t0);
    if (record && A.lueur > 0) tl.to(b, { boxShadow: `0 0 ${60 * u * A.lueur}px ${C.accent2}88`, duration: T(0.6) }, h.halo);
  });
}
function courbe(debut, fin, dernier) {
  const h = Hr.courbe, z = scene(debut, fin, dernier);
  const t = $("div", `position:absolute;left:0;top:0;font-size:${64 * u}px`, z, A.titre_courbe); t.className = "titre";
  $("div", `position:absolute;left:0;top:${80 * u}px;font-size:${30 * u}px;color:${C.doux}`, z, A.sous_titre_courbe);
  const top = 230 * u, bas = A.zh - 90 * u, g = 20 * u, d_ = A.zw - 20 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1]))), nb = A.donnees.length;
  const pts = A.donnees.map((d, i) => [g + (i / Math.max(1, nb - 1)) * (d_ - g), bas - (d[1] / vmax) * (bas - top)]);
  let dd = `M ${pts[0][0]} ${pts[0][1]}`;
  for (let i = 1; i < nb; i++) { const [px, py] = pts[i - 1], [x, y] = pts[i], cx = (px + x) / 2; dd += ` C ${cx} ${py}, ${cx} ${y}, ${x} ${y}`; }
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg"); svg.setAttribute("width", A.zw); svg.setAttribute("height", A.zh);
  svg.setAttribute("style", "position:absolute;left:0;top:0;overflow:visible"); z.appendChild(svg);
  svg.innerHTML = `<defs><linearGradient id="trait" x1="0" x2="1"><stop offset="0%" stop-color="${C.accent}"/><stop offset="100%" stop-color="${C.accent2}"/></linearGradient>` +
    `<linearGradient id="aire" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="${C.accent}" stop-opacity="0.35"/><stop offset="100%" stop-color="${C.accent}" stop-opacity="0"/></linearGradient>` +
    `<clipPath id="revele"><rect id="rideau" x="0" y="-50" width="0" height="${A.zh + 100}"/></clipPath></defs>` +
    `<path d="${dd} L ${d_} ${bas} L ${g} ${bas} Z" fill="url(#aire)" clip-path="url(#revele)"/>` +
    `<path id="trace" d="${dd}" fill="none" stroke="url(#trait)" stroke-width="${8 * u * (0.5 + A.epaisseur)}" stroke-linecap="round" clip-path="url(#revele)"` +
    ` style="filter:drop-shadow(0 0 ${18 * u * A.lueur}px ${C.accent}aa)"/>`;
  const rideau = svg.querySelector("#rideau");
  const pointsSvg = pts.map(([x, y]) => { const c = document.createElementNS(ns, "circle"); c.setAttribute("cx", x); c.setAttribute("cy", y);
    c.setAttribute("r", 7 * u); c.setAttribute("fill", C.fond); c.setAttribute("stroke", C.texte); c.setAttribute("stroke-width", 3 * u);
    c.setAttribute("opacity", 0); svg.appendChild(c); return c; });
  A.donnees.forEach((d, i) => $("div", `position:absolute;left:${pts[i][0] - 60 * u}px;width:${120 * u}px;text-align:center;top:${bas + 18 * u}px;` +
    `font-size:${24 * u}px;color:${C.doux}`, z, d[0]));
  const pt = document.createElementNS(ns, "circle"); pt.setAttribute("r", 16 * u); pt.setAttribute("fill", C.accent2);
  pt.setAttribute("style", `filter:drop-shadow(0 0 ${20 * u}px ${C.accent2})`); pt.setAttribute("opacity", 0); svg.appendChild(pt);
  const o = { p: 0 };
  const placer = (p) => {
    const k = Math.min(nb - 1, p * (nb - 1)), i0 = Math.floor(k), f = k - i0, a = pts[i0], b = pts[Math.min(nb - 1, i0 + 1)];
    const x = a[0] + (b[0] - a[0]) * f, y = a[1] + (b[1] - a[1]) * f;
    rideau.setAttribute("width", x + 1); pt.setAttribute("cx", x); pt.setAttribute("cy", y); pt.setAttribute("opacity", p > 0 ? 1 : 0);
    pointsSvg.forEach((c, i) => c.setAttribute("opacity", p > 0 && k >= i - 1e-6 ? 1 : 0)); return p; };
  tl.to(o, { p: 1, duration: Math.max(0.2, h.fin - h.debut), ease: "power2.inOut", modifiers: { p: placer } }, h.debut);
  let rec = 0; A.donnees.forEach((d, i) => { if (d[1] > A.donnees[rec][1]) rec = i; });
  const w = 300 * u, hh = 96 * u, x = Math.min(Math.max(0, pts[rec][0] - w - 40 * u), A.zw - w), y = Math.max(130 * u, pts[rec][1] - 60 * u - hh);
  const carte = $("div", `position:absolute;left:${x}px;top:${y}px;width:${w}px;height:${hh}px;border-radius:${20 * u}px;` +
    `background:#ffffff12;border:1px solid #ffffff30;padding:${14 * u}px ${28 * u}px`, z);
  $("div", `font-size:${24 * u}px;color:${C.doux}`, carte, A.record);
  const cv = $("div", `font-size:${38 * u}px`, carte, A.textes_valeurs[rec]); cv.className = "titre";
  tl.from(carte, { opacity: 0, y: 30 * u, duration: T(0.8), ease: ressort }, h.record);
}
function titre(debut, fin, dernier) {
  const h = Hr.titre, z = scene(debut, fin, true);
  const bloc = $("div", "position:absolute;left:0;right:0;top:50%;transform:translateY(-50%);text-align:center", z);
  const mots = A.titre.split(/\s+/).filter(Boolean);
  const cle = mots.length > 2 ? mots.reduce((a, b) => (b.replace(/[.,;:!?«»"']/g, "").length > a.replace(/[.,;:!?«»"']/g, "").length ? b : a)) : "";
  const ligne = $("div", `font-size:${120 * u * (A.vertical ? 0.75 : 1)}px;line-height:1.05;white-space:normal`, bloc); ligne.className = "titre";
  mots.forEach((m, k) => { const s = $("span", `display:inline-block;margin:0 ${14 * u}px;color:${m === cle ? C.accent : C.texte}`, ligne, m);
    tl.from(s, { y: 60 * u, opacity: 0, duration: T(0.8), ease: ressort }, h.mots[Math.min(k, h.mots.length - 1)]); });
  const trait = $("div", `width:${A.zw * 0.22}px;height:${8 * u * (0.5 + A.epaisseur)}px;border-radius:${4 * u}px;background:${C.accent2};` +
    `margin:${30 * u}px auto 0;transform-origin:center`, bloc);
  tl.from(trait, { scaleX: 0, duration: T(0.8), ease: sortie }, h.trait);
  if (A.sous_titre) { const st = $("div", `font-size:${40 * u}px;color:${C.doux};margin-top:${24 * u}px`, bloc, A.sous_titre);
    tl.from(st, { opacity: 0, duration: T(0.6) }, h.sous_titre); }
  tl.to(bloc, { opacity: 0, duration: T(0.6), ease: "power3.in" }, fin - T(0.6));
}
function bandeau(debut, fin) {
  const h = Hr.bandeau, uu = u * 1.15;
  const b = $("div", `position:absolute;left:${A.zx}px;top:${A.zy + A.zh - 170 * uu}px;height:${150 * uu}px;overflow:hidden;` +
    `border-radius:${14 * uu * A.coins}px;background:${C.fond}db;padding:0 ${40 * uu}px;border-left:${10 * uu * (0.5 + A.epaisseur)}px solid ${C.accent};transform-origin:left`);
  const n = $("div", `font-size:${54 * uu}px;margin-top:${18 * uu}px;white-space:nowrap`, b, A.titre); n.className = "titre";
  const f = $("div", `font-size:${32 * uu}px;color:${C.accent2};white-space:nowrap`, b, A.sous_titre);
  tl.from(b, { scaleX: 0, duration: T(0.6), ease: ressort }, h.entree);
  tl.from(n, { y: 30 * uu, opacity: 0, duration: T(0.6), ease: ressort }, h.texte);
  tl.from(f, { y: 30 * uu, opacity: 0, duration: T(0.6), ease: ressort }, h.texte + T(0.15));
  tl.to(b, { opacity: 0, scaleX: 0.7, duration: T(0.5), ease: "power3.in" }, h.sortie);
}
function progression() {
  const e = Math.max(A.L, A.H) / 1920, hb = Math.max(4, 8 * e * (0.5 + A.epaisseur));
  const y = A.vertical ? A.zy + A.zh + 40 * e : A.H - hb - 18 * e;
  const fondB = $("div", `position:absolute;left:${24 * e}px;right:${24 * e}px;top:${y}px;height:${hb}px;border-radius:${hb}px;background:${C.texte}2e;overflow:hidden`);
  const plein = $("div", `position:absolute;left:0;top:0;bottom:0;width:100%;transform-origin:left;background:linear-gradient(90deg, ${C.accent}, ${C.accent2})`, fondB);
  tl.fromTo(plein, { scaleX: 0 }, { scaleX: 1, duration: D, ease: "none" }, 0);
  (A.chapitres || []).forEach(([tc, nom]) => {
    if (tc > 0 && tc < D) $("div", `position:absolute;left:${(tc / D) * 100}%;top:0;bottom:0;width:${3 * e}px;background:${C.fond}`, fondB);
    const l = $("div", `position:absolute;left:${24 * e}px;top:${y - 40 * e}px;font-size:${26 * e}px;font-weight:600;color:${C.texte};opacity:0`, null, nom);
    const suite = (A.chapitres.find((c) => c[0] > tc) || [D])[0];
    tl.to(l, { opacity: 0.9, duration: 0.3 }, Math.max(0, tc));
    tl.to(l, { opacity: 0, duration: 0.2 }, Math.max(0, suite - 0.2));
  });
}
function defilement(debut, fin) {
  const vert = A.vertical, cw = A.zw * (vert ? 0.92 : 0.62), chh = A.zh * 0.9, rayon = 28 * u * (0.4 + A.coins);
  const cadre = $("div", `position:absolute;left:${A.zx + (A.zw - cw) / 2}px;top:${A.zy + (A.zh - chh) / 2}px;width:${cw}px;height:${chh}px;` +
    `border-radius:${rayon}px;overflow:hidden;background:#fff;border:2px solid ${C.accent}e6;box-shadow:0 ${30 * u}px ${80 * u}px #0009`);
  if (A.image) {
    const im = $("img", `position:absolute;left:0;top:0;width:100%;`, cadre); im.src = A.image;
    const hi = A.image_ratio ? cw * A.image_ratio : chh;
    tl.to(im, { y: -Math.max(0, hi - chh), duration: Math.max(0.5, fin - debut - T(1.8)), ease: "power1.inOut" }, debut + T(0.9));
  }
  tl.from(cadre, { opacity: 0, y: 80 * u, scale: 0.85, duration: T(0.9), ease: ressort }, debut + T(0.1));
  tl.to(cadre, { opacity: 0, duration: T(0.5) }, fin - T(0.5));
}
function sous_titres() {
  const st = A.style_st || "surligne", maj = A.majuscules !== false, uu = u * 1.1;
  const txt = (w) => (maj ? w.toUpperCase() : w);
  const contour = `paint-order:stroke fill;-webkit-text-stroke:${10 * uu}px #000000c0`;
  if (st === "un_mot") {
    A.mots.forEach(([t0, t1, w]) => {
      const e = $("div", `position:absolute;left:${A.zx}px;width:${A.zw}px;text-align:center;top:${A.zy + A.zh * 0.62 - 90 * uu}px;` +
        `font-size:${150 * uu * (A.vertical ? 0.8 : 1)}px;font-weight:800;opacity:0;color:${txt(w).length > 6 ? C.accent2 : C.texte};${contour}`, null, txt(w));
      e.className = "titre";
      tl.fromTo(e, { opacity: 1, scale: 0.6 }, { scale: 1, duration: 0.25, ease: ressort }, t0);
      tl.set(e, { opacity: 0 }, Math.max(t1, t0 + 0.25));
    });
    return;
  }
  A.lignes_st.forEach((l) => {
    const y = A.zy + A.zh * (A.vertical ? 0.74 : 0.80);
    const box = $("div", `position:absolute;left:${A.zx}px;width:${A.zw}px;text-align:center;top:${y - 70 * uu}px;opacity:0;` +
      `font-size:${64 * uu * (A.st_taille || 1)}px;font-weight:800;white-space:nowrap`);
    box.className = "titre";
    tl.set(box, { opacity: 1 }, Math.max(0, l.t0 - 0.05));
    tl.set(box, { opacity: 0 }, l.t1 + 0.25);
    l.mots.forEach(([t0, t1, w], k) => {
      const s = $("span", `display:inline-block;margin:0 ${8 * uu}px;padding:0 ${8 * uu}px;border-radius:${10 * uu}px;color:${C.texte};${contour}`, box, txt(w));
      if (st === "saute") { tl.set(s, { opacity: 0 }, 0); tl.fromTo(s, { opacity: 0, scale: 0.5 }, { opacity: 1, scale: 1, duration: 0.25, ease: ressort, immediateRender: false }, t0); }
      if (st === "surligne") { tl.set(s, { backgroundColor: C.accent }, t0); tl.set(s, { backgroundColor: "transparent" }, Math.max(t1, t0 + 0.15)); }
      if (st === "karaoke") tl.set(s, { color: C.accent2 }, t0);
      if (st === "saute") { tl.set(s, { color: C.accent2 }, t0); tl.set(s, { color: C.texte }, Math.max(t1, t0 + 0.15)); }
    });
  });
}
// 1.0.1 : neuf types de plus
const pct = (v) => Number(v).toLocaleString(A.langue === "fr" ? "fr-FR" : A.langue, { maximumFractionDigits: 0 }) + " %";
const E = A.elements || [];
function titreHaut(z) {
  const t = $("div", `position:absolute;left:0;top:0;font-size:${64 * u}px`, z, A.titre); t.className = "titre";
  if (A.sous_titre) $("div", `position:absolute;left:0;top:${80 * u}px;font-size:${30 * u}px;color:${C.doux}`, z, A.sous_titre);
}
function camembert(debut, fin, dernier) {
  const h = Hr.camembert, z = scene(debut, fin, dernier); titreHaut(z);
  const tot = E.reduce((s, e) => s + e[1], 0) || 1;
  const cx = A.vertical ? A.zw / 2 : A.zw * 0.3, cy = A.vertical ? A.zh * 0.42 : A.zh * 0.58;
  const rr = A.vertical ? Math.min(A.zw * 0.36, A.zh * 0.22) : Math.min(A.zh * 0.32, A.zw * 0.22), ep = rr * (0.22 + 0.3 * A.epaisseur);
  const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", A.zw); svg.setAttribute("height", A.zh); svg.setAttribute("style", "position:absolute;left:0;top:0;overflow:visible"); z.appendChild(svg);
  const circ = 2 * Math.PI * rr;
  const fondC = document.createElementNS(ns, "circle"); [["cx", cx], ["cy", cy], ["r", rr], ["fill", "none"], ["stroke", C.texte + "14"], ["stroke-width", ep]]
    .forEach(([k, v]) => fondC.setAttribute(k, v)); svg.appendChild(fondC);
  let cumul = 0, rec = 0;
  E.forEach((e, i) => {
    if (e[1] > E[rec][1]) rec = i;
    const part = e[1] / tot, c = document.createElementNS(ns, "circle");
    [["cx", cx], ["cy", cy], ["r", rr], ["fill", "none"], ["stroke", A.palette[i]], ["stroke-width", ep], ["stroke-dasharray", `0 ${circ}`],
     ["transform", `rotate(${-90 + cumul * 360} ${cx} ${cy})`]].forEach(([k, v]) => c.setAttribute(k, v));
    svg.appendChild(c);
    const o = { k: 0 };
    tl.to(o, { k: 1, duration: T(0.7), ease: sortie, modifiers: { k: (k) => { c.setAttribute("stroke-dasharray", `${circ * part * k} ${circ}`); return k; } } }, h.entrees[i]);
    cumul += part;
    const lx = A.vertical ? (i % 2) * A.zw / 2 : A.zw * 0.6, ly = A.vertical ? cy + rr + ep + 60 * u + Math.floor(i / 2) * 56 * u : A.zh * 0.28 + i * 62 * u;
    const lg = $("div", `position:absolute;left:${lx}px;top:${ly - 30 * u}px;width:${A.vertical ? A.zw / 2 - 30 * u : A.zw * 0.4}px;height:${40 * u}px;` +
      `display:flex;align-items:center;font-size:${30 * u}px`, z);
    $("div", `width:${26 * u}px;height:${26 * u}px;border-radius:${6 * u}px;background:${A.palette[i]};margin-right:${18 * u}px;flex:none`, lg);
    $("div", `flex:1;white-space:nowrap`, lg, e[0]);
    $("div", `font-weight:700;color:${C.accent2}`, lg, pct(100 * e[1] / tot));
    tl.from(lg, { opacity: 0, duration: T(0.5) }, h.entrees[i]);
  });
  if (E.length) {
    const m = $("div", `position:absolute;left:${cx - rr}px;width:${2 * rr}px;top:${cy - 50 * u}px;text-align:center`, z);
    const g = $("div", `font-size:${72 * u}px;line-height:1.1`, m, pct(100 * E[rec][1] / tot)); g.className = "titre";
    $("div", `font-size:${26 * u}px;color:${C.doux}`, m, E[rec][0]);
    tl.from(m, { opacity: 0, duration: T(0.6) }, h.fin - T(0.4));
  }
}
function jauge(debut, fin, dernier) {
  const h = Hr.jauge, z = scene(debut, fin, dernier);
  const cx = A.zw / 2, cy = A.zh / 2, rr = Math.min(A.zw, A.zh) * 0.3, ep = rr * (0.12 + 0.18 * A.epaisseur);
  const v = Math.max(0, Math.min(100, A.valeur));
  const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", A.zw); svg.setAttribute("height", A.zh); svg.setAttribute("style", "position:absolute;left:0;top:0;overflow:visible"); z.appendChild(svg);
  const circ = 2 * Math.PI * rr;
  svg.innerHTML = `<defs><linearGradient id="jg" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stop-color="${C.accent2}"/><stop offset="100%" stop-color="${C.accent}"/></linearGradient></defs>` +
    `<circle cx="${cx}" cy="${cy}" r="${rr}" fill="none" stroke="${C.texte}1a" stroke-width="${ep}"/>` +
    `<circle id="arc" cx="${cx}" cy="${cy}" r="${rr}" fill="none" stroke="url(#jg)" stroke-width="${ep}" stroke-linecap="round" stroke-dasharray="0 ${circ}"` +
    ` transform="rotate(-90 ${cx} ${cy})" style="filter:drop-shadow(0 0 ${18 * u * A.lueur}px ${C.accent}aa)"/>`;
  const arc = svg.querySelector("#arc");
  const ch = $("div", `position:absolute;left:0;right:0;top:${cy - rr * 0.32}px;text-align:center;font-size:${rr * 0.55}px;line-height:1.1;color:${C.texte}`, z, nombre(0));
  ch.className = "titre";
  const o = { k: 0 };
  tl.to(o, { k: 1, duration: Math.max(0.2, h.fin - h.debut), ease: "power2.inOut", modifiers: { k: (k) => {
    arc.setAttribute("stroke-dasharray", k > 0 ? `${circ * v / 100 * k} ${circ}` : `0 ${circ}`); ch.textContent = nombre(Math.round(v * k)); return k; } } }, h.debut);
  const t = $("div", `position:absolute;left:0;right:0;top:${cy - rr - ep - 100 * u}px;text-align:center;font-size:${56 * u}px`, z, A.titre); t.className = "titre";
  if (A.sous_titre) { const st = $("div", `position:absolute;left:0;right:0;top:${cy + rr + ep + 24 * u}px;text-align:center;font-size:${32 * u}px;color:${C.doux}`, z, A.sous_titre);
    tl.from(st, { opacity: 0, duration: T(0.6) }, h.fin - 0.3); }
}
function comparaison(debut, fin, dernier) {
  const h = Hr.comparaison, z = scene(debut, fin, dernier); titreHaut(z);
  const el = E.slice(0, 2); while (el.length < 2) el.push(["", 0, "", nombre(0)]);
  const vmax = Math.max(1e-9, ...el.map((e) => e[1])), bas = A.zh - 60 * u, hb0 = A.zh * (A.vertical ? 0.3 : 0.38);
  el.forEach((e, i) => {
    const cx = A.zw * (i ? 0.73 : 0.27), hb = hb0 * e[1] / vmax, lb = A.zw * 0.16 * (0.6 + 0.6 * A.epaisseur);
    const b = $("div", `position:absolute;left:${cx - lb / 2}px;width:${lb}px;top:${bas - hb}px;height:${hb}px;border-radius:${16 * u}px;transform-origin:bottom;` +
      `background:linear-gradient(180deg, ${i ? C.accent2 : C.accent + "e6"}, ${C.accent}4d)`, z);
    const n = $("div", `position:absolute;left:${cx - A.zw / 4}px;width:${A.zw / 2}px;text-align:center;top:${bas - hb0 - 190 * u}px;font-size:${96 * u}px;color:${i ? C.accent2 : C.texte}`, z, nombre(0));
    n.className = "titre";
    $("div", `position:absolute;left:${cx - A.zw / 4}px;width:${A.zw / 2}px;text-align:center;top:${bas + 14 * u}px;font-size:${32 * u}px;font-weight:600;color:${C.doux}`, z, e[0]);
    const o = { k: 0 };
    tl.from(b, { scaleY: 0, duration: T(1.0), ease: ressort }, h.entrees[i]);
    tl.to(o, { k: 1, duration: T(1.0), ease: sortie, modifiers: { k: (k) => { n.textContent = nombre(e[1] * k); return k; } } }, h.entrees[i]);
  });
  if (el[0][1]) {
    const d = (el[1][1] - el[0][1]) / Math.abs(el[0][1]) * 100;
    const txt = (d >= 0 ? "▲ +" : "▼ ") + Number(d).toLocaleString(A.langue === "fr" ? "fr-FR" : A.langue, { maximumFractionDigits: Math.abs(d) >= 10 ? 0 : 1 }).replace("-", "") + " %";
    const p = $("div", `position:absolute;left:0;right:0;top:${bas - hb0 * 0.5 - 36 * u}px;text-align:center`, z);
    const q = $("div", `padding:${10 * u}px ${25 * u}px;font-size:${44 * u}px;font-weight:700`, p, txt); q.className = "pastille";
    if (d < 0) q.style.background = C.accent;
    tl.from(q, { scale: 0, opacity: 0, duration: T(0.8), ease: ressort }, h.fin);
  }
}
function classement(debut, fin, dernier) {
  const h = Hr.classement, z = scene(debut, fin, dernier); titreHaut(z);
  const n = Math.max(1, E.length), y0 = 170 * u, pas = Math.min(110 * u, (A.zh - 30 * u - y0) / n);
  const vmax = Math.max(1e-9, ...E.map((e) => e[1])), g0 = 90 * u + A.zw * 0.22, larg = A.zw - 170 * u - g0;
  E.forEach((e, i) => {
    const y = y0 + i * pas, hb = pas * (0.35 + 0.35 * A.epaisseur), w = larg * e[1] / vmax;
    const r = $("div", `position:absolute;left:0;top:${y}px;width:${A.zw}px;height:${hb}px`, z);
    const rond = $("div", `position:absolute;left:${4 * u}px;top:${hb / 2 - 26 * u}px;width:${52 * u}px;height:${52 * u}px;border-radius:50%;` +
      `background:${i ? C.accent : C.accent2};color:${C.fond};font-size:${30 * u}px;line-height:${52 * u}px;text-align:center`, r, String(i + 1)); rond.className = "titre";
    rond.style.color = C.fond;
    $("div", `position:absolute;left:${80 * u}px;top:${hb / 2 - 22 * u}px;font-size:${32 * u}px;font-weight:600;white-space:nowrap`, r, e[0]);
    const b = $("div", `position:absolute;left:${g0}px;top:0;width:${w}px;height:${hb}px;border-radius:${hb / 2}px;transform-origin:left;` +
      `background:linear-gradient(90deg, ${C.accent}, ${C.accent2})`, r);
    const v = $("div", `position:absolute;left:${g0 + w + 16 * u}px;top:${hb / 2 - 22 * u}px;font-size:${32 * u}px`, r, e[3]); v.className = "titre";
    tl.from(r, { opacity: 0, x: -40 * u, duration: T(0.6), ease: sortie }, h.entrees[i]);
    tl.from(b, { scaleX: 0, duration: T(0.9), ease: ressort }, h.entrees[i]);
    tl.from(v, { x: -w, duration: T(0.9), ease: ressort }, h.entrees[i]);
  });
}
function chiffres_cles(debut, fin, dernier) {
  const h = Hr.chiffres_cles, z = scene(debut, fin, dernier); titreHaut(z);
  const n = Math.max(1, E.length), top = 170 * u, gap = 30 * u;
  const [cols, rows] = A.vertical ? [1, n] : (n <= 3 ? [n, 1] : [2, 2]);
  const tw = (A.zw - gap * (cols - 1)) / cols, th = Math.min((A.zh - top - gap * (rows - 1)) / rows, 360 * u);
  E.forEach((e, i) => {
    const x = (i % cols) * (tw + gap), y = top + Math.floor(i / cols) * (th + gap);
    const c = $("div", `position:absolute;left:${x}px;top:${y}px;width:${tw}px;height:${th}px;border-radius:${24 * u}px;background:${C.texte}12;overflow:hidden`, z);
    $("div", `position:absolute;left:0;top:0;bottom:0;width:${10 * u}px;background:${i % 2 ? C.accent2 : C.accent}`, c);
    const taille = Math.min(th * 0.42, tw / Math.max(4, e[3].length) * 1.5);
    const ch = $("div", `position:absolute;left:0;right:0;top:${th * 0.55 - taille * 0.85}px;text-align:center;font-size:${taille}px;line-height:1.1`, c, nombre(0)); ch.className = "titre";
    $("div", `position:absolute;left:0;right:0;top:${th * 0.55 + 22 * u}px;text-align:center;font-size:${36 * u}px;font-weight:500;opacity:0.75`, c, e[0]);
    const o = { k: 0 };
    tl.from(c, { opacity: 0, y: 40 * u, duration: T(0.7), ease: ressort }, h.entrees[i]);
    tl.to(o, { k: 1, duration: T(1.4), ease: "power2.inOut", modifiers: { k: (k) => { ch.textContent = nombre(e[1] * k); return k; } } }, h.entrees[i]);
  });
}
function chronologie(debut, fin, dernier) {
  const h = Hr.chronologie, z = scene(debut, fin, dernier); titreHaut(z);
  const n = Math.max(1, E.length), ep = 6 * u * (0.5 + A.epaisseur), t0 = (h.entrees[0] || debut) - 0.3;
  if (A.vertical) {
    const x = 40 * u, y0 = 190 * u, y1 = A.zh - 40 * u;
    const l = $("div", `position:absolute;left:${x - ep / 2}px;top:${y0}px;width:${ep}px;height:${y1 - y0}px;border-radius:${ep}px;background:${C.accent};transform-origin:top`, z);
    tl.from(l, { scaleY: 0, duration: Math.max(0.3, h.fin - t0), ease: "power1.inOut" }, t0);
    E.forEach((e, i) => {
      const y = y0 + (y1 - y0) * (i + 0.5) / n;
      const pt = $("div", `position:absolute;left:${x - 14 * u}px;top:${y - 14 * u}px;width:${28 * u}px;height:${28 * u}px;border-radius:50%;background:${C.accent2}`, z);
      const b = $("div", `position:absolute;left:${x + 40 * u}px;top:${y - 44 * u}px;width:${A.zw - 80 * u}px`, z);
      const d = $("div", `font-size:${40 * u}px;color:${C.accent2}`, b, e[0]); d.className = "titre";
      $("div", `font-size:${30 * u}px;line-height:1.2`, b, e[2]);
      tl.from(pt, { scale: 0, duration: T(0.6), ease: ressort }, h.entrees[i]);
      tl.from(b, { opacity: 0, x: -30 * u, duration: T(0.6), ease: sortie }, h.entrees[i]);
    });
  } else {
    const y = A.zh * 0.52, x0 = 20 * u, x1 = A.zw - 20 * u, larg = (x1 - x0) / n;
    const l = $("div", `position:absolute;left:${x0}px;top:${y - ep / 2}px;width:${x1 - x0}px;height:${ep}px;border-radius:${ep}px;background:${C.accent};transform-origin:left`, z);
    tl.from(l, { scaleX: 0, duration: Math.max(0.3, h.fin - t0), ease: "power1.inOut" }, t0);
    E.forEach((e, i) => {
      const x = x0 + larg * (i + 0.5), haut_ = i % 2 === 0;
      const pt = $("div", `position:absolute;left:${x - 16 * u}px;top:${y - 16 * u}px;width:${32 * u}px;height:${32 * u}px;border-radius:50%;background:${C.accent2}`, z);
      const b = $("div", `position:absolute;left:${x - larg / 2 + 10 * u}px;width:${larg - 20 * u}px;text-align:center;` +
        (haut_ ? `bottom:${A.zh - y + 30 * u}px;display:flex;flex-direction:column-reverse` : `top:${y + 34 * u}px`), z);
      const d = $("div", `font-size:${44 * u}px;color:${C.accent2}`, b, e[0]); d.className = "titre";
      $("div", `font-size:${28 * u}px;line-height:1.2`, b, e[2]);
      tl.from(pt, { scale: 0, duration: T(0.6), ease: ressort }, h.entrees[i]);
      tl.from(b, { opacity: 0, y: (haut_ ? 30 : -30) * u, duration: T(0.6), ease: sortie }, h.entrees[i]);
    });
  }
}
function liste(debut, fin, dernier) {
  const h = Hr.liste, z = scene(debut, fin, dernier); titreHaut(z);
  const n = Math.max(1, E.length), y0 = 200 * u, pas = Math.min(120 * u, (A.zh - y0) / n);
  E.forEach((e, i) => {
    const r = $("div", `position:absolute;left:0;top:${y0 + i * pas - 52 * u}px;width:${A.zw}px;display:flex;align-items:center;` +
      `font-size:${40 * u * (A.vertical ? 0.9 : 1)}px;font-weight:600`, z);
    const c = $("div", `width:${48 * u}px;height:${48 * u}px;border-radius:50%;background:${C.accent};margin-right:${28 * u}px;flex:none;` +
      `color:${C.fond};font-size:${30 * u}px;font-weight:800;line-height:${48 * u}px;text-align:center`, r, "✓");
    $("div", "white-space:nowrap;overflow:hidden;text-overflow:clip", r, e[2]);
    tl.from(r, { opacity: 0, x: -60 * u, duration: T(0.6), ease: sortie }, h.entrees[i]);
    tl.from(c, { scale: 0, duration: T(0.6), ease: ressort }, h.entrees[i]);
  });
}
function citation(debut, fin, dernier) {
  const h = Hr.citation, z = scene(debut, fin, dernier);
  const bloc = $("div", `position:absolute;left:${A.zw * 0.07}px;right:${A.zw * 0.07}px;top:50%;transform:translateY(-50%);text-align:center`, z);
  const g = $("div", `position:absolute;left:${-A.zw * 0.02}px;top:${-150 * u}px;font-size:${220 * u}px;color:${C.accent};opacity:0.9`, bloc, "«"); g.className = "titre";
  tl.from(g, { opacity: 0, scale: 0.6, duration: T(0.8), ease: ressort }, debut + 0.1);
  const ligne = $("div", `font-size:${70 * u * (A.vertical ? 0.85 : 1)}px;font-weight:600;line-height:1.15;white-space:normal`, bloc); ligne.className = "titre";
  A.titre.split(/\s+/).filter(Boolean).forEach((m, k) => {
    const s = $("span", `display:inline-block;margin:0 ${10 * u}px`, ligne, m);
    tl.from(s, { opacity: 0, y: 30 * u, duration: T(0.6), ease: sortie }, h.mots[Math.min(k, h.mots.length - 1)] || debut);
  });
  if (A.sous_titre) {
    const a = $("div", `margin-top:${30 * u}px;font-size:${36 * u}px;color:${C.doux}`, bloc, "— " + A.sous_titre);
    tl.from(a, { opacity: 0, duration: T(0.6) }, h.auteur);
  }
}
function appel(debut, fin, dernier) {
  const h = Hr.appel, uu = u * 1.2;
  const z = $("div", ""); z.className = "zone";
  const cx = A.zw / 2, cy = A.zh * (A.vertical ? 0.55 : 0.62);
  if (A.transparent) { const lw = A.zw * (A.vertical ? 0.95 : 0.6);
    $("div", `position:absolute;left:${cx - lw / 2}px;top:${cy - 230 * uu}px;width:${lw}px;height:${360 * uu}px;border-radius:${30 * uu}px;background:${C.fond}bf`, z); }
  const t = $("div", `position:absolute;left:0;right:0;top:${cy - 190 * uu}px;text-align:center;font-size:${56 * uu}px`, z, A.titre); t.className = "titre";
  const b = $("div", `position:absolute;left:${cx}px;top:${cy}px;transform:translate(-50%,-50%);height:${100 * uu}px;padding:0 ${60 * uu}px;` +
    `border-radius:${50 * uu * A.coins + 8 * uu}px;background:${C.accent};color:${C.fond};font-size:${46 * uu}px;line-height:${100 * uu}px;white-space:nowrap`, z);
  b.className = "titre";
  const l1 = $("span", `color:${C.fond}`, b, A.bouton), l2 = $("span", `display:none;color:${C.texte}`, b, A.bouton_fait);
  if (A.sous_titre) $("div", `position:absolute;left:0;right:0;top:${cy + 80 * uu}px;text-align:center;font-size:${32 * uu}px;color:${C.doux}`, z, A.sous_titre);
  const fl = $("div", `position:absolute;left:${cx}px;top:${cy}px;width:${36 * uu}px;height:${54 * uu}px;opacity:0`, z);
  fl.innerHTML = `<svg viewBox="0 0 36 54" width="${36 * uu}" height="${54 * uu}"><path d="M0 0 L0 46 L12 35 L21 54 L29 50 L20 32 L36 32 Z" fill="#fff" stroke="#000c" stroke-width="3"/></svg>`;
  const onde = $("div", `position:absolute;left:${cx + 40 * uu}px;top:${cy + 10 * uu}px;width:${120 * uu}px;height:${120 * uu}px;margin:${-60 * uu}px 0 0 ${-60 * uu}px;` +
    `border-radius:50%;border:${4 * uu}px solid ${C.accent2};opacity:0`, z);
  tl.from(z, { opacity: 0, scale: 0.8, duration: T(0.6), ease: ressort }, h.entree);
  tl.fromTo(fl, { opacity: 1, x: A.zw * 0.35, y: A.zh * 0.3 }, { x: 40 * uu, y: 10 * uu, duration: Math.max(0.2, h.clic - h.curseur), ease: "power3.out", immediateRender: false }, h.curseur);
  tl.set(fl, { opacity: 0 }, 0);
  tl.set(fl, { opacity: 1 }, h.curseur);
  tl.to(b, { scale: 0.92, duration: 0.08 }, h.clic - 0.08);
  tl.to(b, { scale: 1, duration: 0.2, ease: ressort }, h.clic);
  tl.set(l1, { display: "none" }, h.clic); tl.set(l2, { display: "inline" }, h.clic);
  tl.set(b, { backgroundColor: C.doux + "80" }, h.clic);
  tl.fromTo(onde, { opacity: 1, scale: 0 }, { opacity: 0, scale: 1, duration: 0.5, immediateRender: false }, h.clic);
  tl.set(fl, { opacity: 0 }, h.clic + 0.9);
  tl.to(z, { opacity: 0, duration: T(0.5) }, fin - T(0.5));
}
Object.entries(Hr.scenes).sort((a, b) => a[1][0] - b[1][0]).forEach(([nom, [a, b]]) => {
  const f = { compteur, barres, courbe, titre, bandeau, progression, defilement, sous_titres, camembert, jauge, comparaison, classement,
    chiffres_cles, chronologie, liste, citation, appel }[nom];
  if (f) f(a, b, b >= fins - 1e-6);
});
'''


def composition(anim, gsap="gsap.min.js", polices=(), logo=""):
    """Le HTML de l'animation (une composition HyperFrames autonome)."""
    if anim.get("genre") == "libre":                  # 1.1.0 : écrite par l'IA d'après une description
        from . import motion_libre as ML
        return ML.composition(anim, gsap, polices, logo)
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
        donnees=json.dumps(m, ensure_ascii=False).replace("</", "<\\/"), logo=js_logo, scenes=JS_SCENES)


POLICES_LIVREES = {"Poppins": [("Poppins-Regular.ttf", 400), ("Poppins-SemiBold.ttf", 600), ("Poppins-Bold.ttf", 700)],
                   "Anton": [("Anton-Regular.ttf", 400)], "Bebas Neue": [("BebasNeue-Regular.ttf", 400)],
                   "Nunito": [("Nunito-400.ttf", 400), ("Nunito-600.ttf", 600), ("Nunito-800.ttf", 800)]}


def _dossier_polices():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "fonts")


def _copier_calques(anim, dossier, prefixe):
    """1.1.16 : les images de l'animation simple copiées à côté de la composition : {rang de l'image: adresse dans la page}."""
    out = {}
    for k, im in enumerate((anim.get("images") or [])[:M.MAX_IMAGES]):
        ch = (im or {}).get("chemin") or ""
        if os.path.exists(ch):
            nom = f"image{k + 1}" + os.path.splitext(ch)[1].lower()
            shutil.copy2(ch, os.path.join(dossier, nom))
            out[k] = prefixe + nom
    return out


def _ratio(chemin):
    """Hauteur / largeur d'une image (pour faire défiler une capture jusqu'en bas)."""
    try:
        import cv2
        img = cv2.imread(chemin, cv2.IMREAD_UNCHANGED)
        return img.shape[0] / img.shape[1] if img is not None else 0.0
    except Exception:      # noqa: BLE001
        return 0.0


def _ressources_libres(anim, dossier):
    """1.1.16 : dessins et plans vidéo du motion pro copiés dans assets/ ; chacun reçoit son chemin dans la page (src)."""
    import copy
    res = ((anim.get("libre") or {}).get("ressources") or {})
    if not (res.get("images") or res.get("videos")):
        return anim
    a = copy.deepcopy(anim)
    for genre in ("images", "videos"):
        for i, r in (a["libre"]["ressources"].get(genre) or {}).items():
            if r.get("chemin") and os.path.exists(r["chemin"]):
                nom = os.path.basename(r["chemin"])
                shutil.copy2(r["chemin"], os.path.join(dossier, "assets", nom))
                r["src"] = "assets/" + nom
    return a


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
    if anim.get("genre") == "defilement" and anim.get("image") and os.path.exists(anim["image"]):
        nom = "capture" + os.path.splitext(anim["image"])[1].lower()
        shutil.copy2(anim["image"], os.path.join(dossier, "assets", nom))
        anim = dict(anim, _html_image="assets/" + nom, _html_ratio=_ratio(anim["image"]))
    anim = dict(anim, _html_calques=_copier_calques(anim, os.path.join(dossier, "assets"), "assets/"))
    anim = _ressources_libres(anim, dossier)
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


def verifier(dossier):
    """1.1.0 : « hyperframes lint » du projet (gratuit, sur ce poste) : liste des erreurs (texte + conseil), vide si tout va.
    Sert surtout aux animations libres écrites par l'IA : l'erreur lui est renvoyée pour qu'elle corrige."""
    from . import moteur
    if not local_pret():
        return []
    try:
        r = subprocess.run([node(), cli_hyperframes(), "lint", "--json", dossier], cwd=dossier, env=_env(), capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120, **moteur._sans_console())
        d = json.loads(r.stdout[r.stdout.find("{"):])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []
    return [f"{x.get('message', '')} — {x.get('fixHint', '')} — {x.get('snippet', '')}"[:600]
            for x in d.get("findings", []) if x.get("severity") == "error"]


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
