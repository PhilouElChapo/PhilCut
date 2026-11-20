// Le moteur Remotion de PhilCut : la fiche de l'animation (mise_en_page de app/motion_html.py) dessinée avec le look de
// l'étalon « Chiffres » validé le 19/11 : fond qui respire, chiffre qui monte, barres qui poussent, courbe qui se trace.
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/fonts";

export type Animation = {
  L: number; H: number; cadence: number; duree: number; zx: number; zy: number; zw: number; zh: number; u: number;
  vertical: boolean; genre: string; vitesse: number; rebond: number; decalage: number; epaisseur: number; lueur: number;
  fond_anime: boolean; transparent: boolean;
  couleurs: { fond: string; texte: string; doux: string; accent: string; accent2: string };
  titre: string; sous_titre: string; badge: string; titre_barres: string; titre_courbe: string; sous_titre_courbe: string;
  source: string; donnees: [string, number][]; valeur: number; textes_valeurs: string[]; prefixe: string; suffixe: string;
  decimales: number; langue: string; record: string; police_titre: string; police_texte: string;
  polices?: [string, string, number][]; logo?: string;
  // 1.0.0 : horaire commun (secondes de l'animation), sous-titres animés, habillage
  horaire?: Horaire; coins?: number; panneau?: boolean; mots?: [number, number, string][]; style_st?: string; majuscules?: boolean;
  lignes_st?: { t0: number; t1: number; mots: [number, number, string][] }[]; chapitres?: [number, string][]; image?: string;
  image_ratio?: number;
};

export type Horaire = {
  genre: string; duree: number; scenes: Record<string, [number, number]>;
  compteur?: { debut: number; fin: number; badge: number }; barres?: { grille: number; entrees: number[]; halo: number };
  courbe?: { debut: number; fin: number; record: number }; titre?: { mots: number[]; trait: number; sous_titre: number };
  bandeau?: { entree: number; texte: number; sortie: number };
};

export const EXEMPLE: Animation = {
  L: 1920, H: 1080, cadence: 30, duree: 14, zx: 153, zy: 97, zw: 1612, zh: 885, u: 1, vertical: false, genre: "chiffres",
  vitesse: 1, rebond: 0.35, decalage: 0.17, epaisseur: 0.7, lueur: 0.6, fond_anime: true, transparent: false,
  couleurs: { fond: "#0B1020", texte: "#EEF1FA", doux: "#8A93B2", accent: "#8B7CFF", accent2: "#3EE0F0" },
  titre: "Visiteurs, premier semestre", sous_titre: "Visiteurs par mois", badge: "▲ +23 % sur un an",
  titre_barres: "Mois après mois", titre_courbe: "La tendance", sous_titre_courbe: "Juin bat le record du semestre", source: "",
  donnees: [["Janv.", 3120], ["Févr.", 4380], ["Mars", 3960], ["Avr.", 5870], ["Mai", 7240], ["Juin", 9820]], valeur: 34390,
  textes_valeurs: ["3 120", "4 380", "3 960", "5 870", "7 240", "9 820"], prefixe: "", suffixe: "", decimales: 0,
  langue: "fr", record: "Record", police_titre: "Poppins", police_texte: "Poppins",
};

const borne = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const SORTIE = Easing.bezier(0.16, 1, 0.3, 1);
let policesChargees = false;

const nombre = (A: Animation, v: number) => {
  const t = v.toLocaleString(A.langue === "fr" ? "fr-FR" : A.langue, { minimumFractionDigits: A.decimales, maximumFractionDigits: A.decimales });
  return A.prefixe + t.replace(/[\u202f ]/g, "\u00a0") + A.suffixe;
};
const haut = (v: number) => {
  if (v <= 0) return 1;
  const e = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * e >= v) return m * e;
  return 10 * e;
};
const hex2 = (x: number) => Math.round(Math.max(0, Math.min(255, x))).toString(16).padStart(2, "0");


const Fond: React.FC<{ A: Animation }> = ({ A }) => {
  const f = useCurrentFrame();
  if (A.transparent) return null;
  const C = A.couleurs;
  const e = Math.max(A.L, A.H) / 1920;
  return (
    <AbsoluteFill style={{ backgroundColor: C.fond, overflow: "hidden" }}>
      {A.fond_anime ? (
        <>
          <div style={{ position: "absolute", width: 1400 * e, height: 1400 * e, borderRadius: 700 * e, left: -300 * e + Math.sin(f / 90) * 60 * e,
            top: -700 * e + Math.cos(f / 110) * 50 * e, background: `radial-gradient(circle, ${C.accent}${hex2(51 * Math.max(A.lueur, 0.3))} 0%, transparent 60%)` }} />
          <div style={{ position: "absolute", width: 1200 * e, height: 1200 * e, borderRadius: 600 * e, right: -400 * e + Math.cos(f / 80) * 50 * e,
            bottom: -700 * e + Math.sin(f / 100) * 40 * e, background: `radial-gradient(circle, ${C.accent2}22 0%, transparent 60%)` }} />
          <AbsoluteFill style={{ backgroundImage: "linear-gradient(#ffffff10 1px, transparent 1px), linear-gradient(90deg, #ffffff10 1px, transparent 1px)",
            backgroundSize: `${80 * e}px ${80 * e}px`, maskImage: "radial-gradient(ellipse at center, black 30%, transparent 75%)" }} />
        </>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- l'horaire (le même que app/motion.py : horaire())
const horaireDefaut = (A: Animation): Horaire => {
  const D = A.duree, V = A.vitesse, dec = A.decalage, n = A.donnees.length, g = A.genre;
  const h: Horaire = { genre: g, duree: D, scenes: {} };
  const compteur = (a: number, b: number) => { h.scenes.compteur = [a, b]; h.compteur = { debut: a + 0.3 / V, fin: a + 2.6 / V, badge: a + 2.4 / V }; };
  const barres = (a: number, b: number) => { h.scenes.barres = [a, b];
    h.barres = { grille: a + 0.2 / V, entrees: A.donnees.map((_d, i) => a + (0.6 + i * dec) / V), halo: a + 2.6 / V }; };
  const courbe = (a: number, b: number) => { h.scenes.courbe = [a, b]; h.courbe = { debut: a + 0.4 / V, fin: a + 2.8 / V, record: a + 2.8 / V }; };
  if (g === "compteur") compteur(0, D);
  else if (g === "barres") barres(0, D);
  else if (g === "courbe") courbe(0, D);
  else if (g === "titre") { const m = A.titre.split(/\s+/).filter(Boolean); h.scenes.titre = [0, D];
    h.titre = { mots: m.map((_x, k) => (0.15 + k * dec) / V), trait: (0.4 + m.length * dec * 0.5) / V, sous_titre: 0.8 / V }; }
  else if (g === "bandeau") { h.scenes.bandeau = [0, D]; h.bandeau = { entree: 0.1 / V, texte: 0.35 / V, sortie: Math.max(0.8, D - 0.7 / V) }; }
  else if (["progression", "defilement", "sous_titres"].includes(g)) h.scenes[g] = [0, D];
  else { compteur(0, (D * 4.3) / 14); barres((D * 4.0) / 14, (D * 9.4) / 14); courbe((D * 9.2) / 14, D); }
  void n;
  return h;
};

const useT = () => { const f = useCurrentFrame(); const { fps } = useVideoConfig(); return f / fps; };
const entre = (t: number, a: number, b: number, easing?: (x: number) => number) =>
  b <= a ? (t >= b ? 1 : 0) : interpolate(t, [a, b], [0, 1], easing ? { ...borne, easing } : borne);
const res = (A: Animation, t: number, debut: number, raideur = 120) => ressortT(A, (t - debut) * A.vitesse, raideur);
const ressortT = (A: Animation, s: number, raideur: number) =>
  s <= 0 ? 0 : spring({ frame: s * 60, fps: 60, config: { stiffness: raideur, damping: 2 * Math.sqrt(raideur) * (1 - 0.7 * A.rebond) } });

type SceneProps = { A: Animation; h: Horaire; a: number; b: number; dernier: boolean };

const Scene: React.FC<{ A: Animation; a: number; b: number; dernier: boolean; children: React.ReactNode }> = ({ A, a, b, dernier, children }) => {
  const t = useT(), V = A.vitesse;
  const op = entre(t, a, a + 0.5 / V, SORTIE) * (1 - (dernier ? 0 : entre(t, b - 0.5 / V, b, Easing.in(Easing.cubic))));
  const m = 30 * A.u;
  return (
    <AbsoluteFill style={{ opacity: op }}>
      {A.transparent && A.panneau !== false ? <div style={{ position: "absolute", left: A.zx - m, top: A.zy - m, width: A.zw + 2 * m, height: A.zh + 2 * m,
        borderRadius: 36 * A.u, background: A.couleurs.fond + "b8" }} /> : null}
      <div style={{ position: "absolute", left: A.zx, top: A.zy, width: A.zw, height: A.zh, fontFamily: `"${A.police_texte}", "Poppins", sans-serif`, color: A.couleurs.texte }}>
        {children}
        {A.source ? <div style={{ position: "absolute", left: 0, bottom: -40 * A.u, fontSize: 22 * A.u, color: A.couleurs.doux }}>{A.source}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
const titreF = (A: Animation) => `"${A.police_titre}", "Poppins", sans-serif`;

const Compteur: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, H = h.compteur!;
  const v = A.valeur * entre(t, H.debut, H.fin, Easing.bezier(0.22, 1, 0.36, 1));
  const p = res(A, t, H.badge, 160);
  const lab = entre(t, a, a + 0.6 / A.vitesse);
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <div style={{ position: "absolute", left: 0, right: 0, top: (A.vertical ? 0.42 : 0.48) * A.zh, transform: "translateY(-50%)", textAlign: "center" }}>
        <div style={{ fontSize: 34 * u, fontWeight: 600, letterSpacing: 6 * u, color: C.doux, textTransform: "uppercase", opacity: lab,
          translate: `0px ${(1 - SORTIE(lab)) * 20 * u}px` }}>{A.titre}</div>
        <div style={{ fontFamily: titreF(A), fontWeight: 700, fontSize: 260 * u * (A.vertical ? 0.8 : 1), lineHeight: 1, marginTop: 18 * u,
          fontVariantNumeric: "tabular-nums", backgroundImage: `linear-gradient(100deg, ${C.texte} 30%, ${C.accent} 70%, ${C.accent2})`,
          WebkitBackgroundClip: "text", color: "transparent", filter: `drop-shadow(0 ${20 * u}px ${60 * u}px ${C.accent}${hex2(85 * A.lueur)})` }}>
          {nombre(A, v)}
        </div>
        {A.badge ? (
          <div style={{ display: "inline-block", marginTop: 36 * u, padding: `${14 * u}px ${30 * u}px`, borderRadius: 999, fontWeight: 600,
            fontSize: 38 * u, color: C.fond, background: `linear-gradient(90deg, ${C.accent2}, ${C.accent})`, scale: String(p), opacity: Math.min(1, p) }}>
            {A.badge}
          </div>
        ) : null}
      </div>
    </Scene>
  );
};

const Barres: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, V = A.vitesse, H = h.barres!;
  const top = 190 * u, bas = A.zh - 60 * u, Hc = bas - top, gauche = 110 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1])));
  const nb = A.donnees.length, ecart = 46 * u * (nb > 8 ? 0.6 : 1);
  const larg = (A.zw - gauche - ecart * (nb - 1)) / nb, lb = larg * (0.45 + 0.55 * A.epaisseur);
  let rec = 0;
  A.donnees.forEach((d, i) => { if (d[1] > A.donnees[rec][1]) rec = i; });
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <div style={{ position: "absolute", left: 0, top: 0, fontFamily: titreF(A), fontWeight: 700, fontSize: 64 * u, whiteSpace: "nowrap" }}>{A.titre_barres}</div>
      <div style={{ position: "absolute", left: 0, top: 80 * u, fontSize: 30 * u, color: C.doux }}>{A.sous_titre}</div>
      {[0, 1, 2, 3, 4].map((i) => {
        const g0 = H.grille + (i * 0.1) / V, tr = entre(t, g0, g0 + 0.7 / V, SORTIE), y = bas - (i / 4) * Hc;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: 0, top: y - 14 * u, fontSize: 22 * u, color: C.doux, opacity: tr }}>{nombre({ ...A, prefixe: "", suffixe: "" }, (vmax * i) / 4)}</div>
            <div style={{ position: "absolute", left: gauche, top: y, height: 1, width: (A.zw - gauche) * tr, background: C.texte + "1c" }} />
          </React.Fragment>
        );
      })}
      {A.donnees.map((d, i) => {
        const p = res(A, t, H.entrees[Math.min(i, H.entrees.length - 1)], 90);
        const x = gauche + i * (larg + ecart) + (larg - lb) / 2, hh = (d[1] / vmax) * Hc * p, record = i === rec;
        const halo = record ? entre(t, H.halo, H.halo + 0.6 / V) * A.lueur : 0;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x - 40 * u, width: lb + 80 * u, textAlign: "center", top: bas - hh - 50 * u, opacity: Math.min(1, p),
              fontFamily: titreF(A), fontWeight: 700, fontSize: 32 * u * (nb > 8 ? 0.8 : 1), color: record ? C.accent2 : C.texte }}>
              {nombre(A, d[1] * Math.min(1, p))}
            </div>
            <div style={{ position: "absolute", left: x, width: lb, top: bas - hh, height: Math.max(0, hh), borderRadius: `${18 * u}px ${18 * u}px ${6 * u}px ${6 * u}px`,
              background: record ? `linear-gradient(180deg, ${C.accent2}, ${C.accent})` : `linear-gradient(180deg, ${C.accent}cc, ${C.accent}44)`,
              boxShadow: halo > 0 ? `0 0 ${60 * u * halo}px ${C.accent2}88` : "none" }} />
            <div style={{ position: "absolute", left: x - 40 * u, width: lb + 80 * u, textAlign: "center", top: bas + 12 * u, fontSize: 26 * u * (nb > 8 ? 0.8 : 1), color: C.doux }}>{d[0]}</div>
          </React.Fragment>
        );
      })}
    </Scene>
  );
};

const Courbe: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, H = h.courbe!;
  const top = 230 * u, bas = A.zh - 90 * u, g = 20 * u, dr = A.zw - 20 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1]))), nb = A.donnees.length;
  const pts = A.donnees.map((d, i) => [g + (i / Math.max(1, nb - 1)) * (dr - g), bas - (d[1] / vmax) * (bas - top)]);
  const d = pts.reduce((acc, [x, y], i) => {
    if (i === 0) return `M ${x} ${y}`;
    const [px, py] = pts[i - 1];
    const cx = (px + x) / 2;
    return `${acc} C ${cx} ${py}, ${cx} ${y}, ${x} ${y}`;
  }, "");
  const p = entre(t, H.debut, H.fin, Easing.bezier(0.65, 0, 0.35, 1));
  const k = Math.min(nb - 1, p * (nb - 1)), i0 = Math.floor(k), f = k - i0;
  const pa = pts[i0], pb = pts[Math.min(nb - 1, i0 + 1)];
  const point = [pa[0] + (pb[0] - pa[0]) * f, pa[1] + (pb[1] - pa[1]) * f];
  let rec = 0;
  A.donnees.forEach((x, i) => { if (x[1] > A.donnees[rec][1]) rec = i; });
  const r = res(A, t, H.record, 140);
  const w = 300 * u, hh = 96 * u;
  const cx = Math.min(Math.max(0, pts[rec][0] - w - 40 * u), A.zw - w), cy = Math.max(130 * u, pts[rec][1] - 60 * u - hh);
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <div style={{ position: "absolute", left: 0, top: 0, fontFamily: titreF(A), fontWeight: 700, fontSize: 64 * u, whiteSpace: "nowrap" }}>{A.titre_courbe}</div>
      <div style={{ position: "absolute", left: 0, top: 80 * u, fontSize: 30 * u, color: C.doux }}>{A.sous_titre_courbe}</div>
      <svg width={A.zw} height={A.zh} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        <defs>
          <linearGradient id="trait" x1="0" x2="1"><stop offset="0%" stopColor={C.accent} /><stop offset="100%" stopColor={C.accent2} /></linearGradient>
          <linearGradient id="aire" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={C.accent} stopOpacity={0.35} /><stop offset="100%" stopColor={C.accent} stopOpacity={0} /></linearGradient>
          <clipPath id="revele"><rect x={0} y={-50} width={point[0] + 1} height={A.zh + 100} /></clipPath>
        </defs>
        <path d={`${d} L ${dr} ${bas} L ${g} ${bas} Z`} fill="url(#aire)" clipPath="url(#revele)" />
        <path d={d} fill="none" stroke="url(#trait)" strokeWidth={8 * u * (0.5 + A.epaisseur)} strokeLinecap="round" clipPath="url(#revele)"
          style={{ filter: `drop-shadow(0 0 ${18 * u * A.lueur}px ${C.accent}aa)` }} />
        {pts.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={7 * u} fill={C.fond} stroke={C.texte} strokeWidth={3 * u} opacity={p > 0 && k >= i - 1e-6 ? 1 : 0} />)}
        <circle cx={point[0]} cy={point[1]} r={16 * u} fill={C.accent2} opacity={p > 0 ? 1 : 0} style={{ filter: `drop-shadow(0 0 ${20 * u}px ${C.accent2})` }} />
      </svg>
      {A.donnees.map((x, i) => <div key={i} style={{ position: "absolute", left: pts[i][0] - 60 * u, width: 120 * u, textAlign: "center", top: bas + 18 * u, fontSize: 24 * u, color: C.doux }}>{x[0]}</div>)}
      <div style={{ position: "absolute", left: cx, top: cy + (1 - Math.min(1, r)) * 30 * u, width: w, height: hh, borderRadius: 20 * u, background: "#ffffff12",
        border: "1px solid #ffffff30", padding: `${14 * u}px ${28 * u}px`, opacity: Math.min(1, r) }}>
        <div style={{ fontSize: 24 * u, color: C.doux }}>{A.record}</div>
        <div style={{ fontFamily: titreF(A), fontWeight: 700, fontSize: 38 * u }}>{A.textes_valeurs[rec]}</div>
      </div>
    </Scene>
  );
};

const Titre: React.FC<SceneProps> = ({ A, h, a, b }) => {
  const t = useT(), u = A.u, C = A.couleurs, V = A.vitesse, H = h.titre!;
  const mots = A.titre.split(/\s+/).filter(Boolean);
  const nu = (m: string) => m.replace(/[.,;:!?«»"']/g, "");
  const cle = mots.length > 2 ? mots.reduce((x, y) => (nu(y).length > nu(x).length ? y : x)) : "";
  const fin = 1 - entre(t, b - 0.6 / V, b);
  const trait = entre(t, H.trait, H.trait + 0.8 / V, SORTIE);
  return (
    <Scene A={A} a={a} b={b} dernier>
      <div style={{ position: "absolute", left: 0, right: 0, top: "50%", transform: "translateY(-50%)", textAlign: "center", opacity: fin }}>
        <div style={{ fontFamily: titreF(A), fontWeight: 700, fontSize: 120 * u * (A.vertical ? 0.75 : 1), lineHeight: 1.05 }}>
          {mots.map((m, i) => {
            const p = res(A, t, H.mots[Math.min(i, H.mots.length - 1)], 150);
            return <span key={i} style={{ display: "inline-block", margin: `0 ${14 * u}px`, color: m === cle ? C.accent : C.texte, opacity: Math.min(1, p),
              translate: `0px ${(1 - Math.min(1, p)) * 60 * u}px` }}>{m}</span>;
          })}
        </div>
        <div style={{ width: A.zw * 0.22 * trait, height: 8 * u * (0.5 + A.epaisseur), borderRadius: 4 * u, background: C.accent2, margin: `${30 * u}px auto 0` }} />
        {A.sous_titre ? <div style={{ fontSize: 40 * u, color: C.doux, marginTop: 24 * u, opacity: entre(t, H.sous_titre, H.sous_titre + 0.6 / V) }}>{A.sous_titre}</div> : null}
      </div>
    </Scene>
  );
};

// ---------------------------------------------------------------- 1.0.0 : habillage
const Bandeau: React.FC<SceneProps> = ({ A, h }) => {
  const t = useT(), u = A.u * 1.15, C = A.couleurs, V = A.vitesse, H = h.bandeau!;
  const k = res(A, t, H.entree, 160), kt = res(A, t, H.texte, 140), kf = res(A, t, H.texte + 0.15 / V, 140);
  const sortie = entre(t, H.sortie, H.sortie + 0.5 / V);
  if (k <= 0.001) return null;
  return (
    <div style={{ position: "absolute", left: A.zx, top: A.zy + A.zh - 170 * u, height: 150 * u, overflow: "hidden", opacity: 1 - sortie,
      borderRadius: 14 * u * (A.coins ?? 0.6), background: C.fond + "db", padding: `0 ${40 * u}px`, transformOrigin: "left", scale: `${Math.min(1, k) * (1 - 0.3 * sortie)} 1`,
      borderLeft: `${10 * u * (0.5 + A.epaisseur)}px solid ${C.accent}` }}>
      <div style={{ fontFamily: titreF(A), fontWeight: 700, fontSize: 54 * u, marginTop: 18 * u, whiteSpace: "nowrap", color: C.texte,
        opacity: Math.min(1, kt), translate: `0px ${(1 - Math.min(1, kt)) * 30 * u}px` }}>{A.titre}</div>
      <div style={{ fontFamily: `"${A.police_texte}", "Poppins", sans-serif`, fontSize: 32 * u, whiteSpace: "nowrap", color: C.accent2,
        opacity: Math.min(1, kf), translate: `0px ${(1 - Math.min(1, kf)) * 30 * u}px` }}>{A.sous_titre}</div>
    </div>
  );
};

const Progression: React.FC<SceneProps> = ({ A }) => {
  const t = useT(), C = A.couleurs, e = Math.max(A.L, A.H) / 1920, hb = Math.max(4, 8 * e * (0.5 + A.epaisseur));
  const y = A.vertical ? A.zy + A.zh + 40 * e : A.H - hb - 18 * e, prog = Math.min(1, Math.max(0, t / A.duree));
  const chap = (A.chapitres || []).filter((c) => c[0] < A.duree);
  const actif = [...chap].reverse().find((c) => c[0] <= t);
  return (
    <>
      <div style={{ position: "absolute", left: 24 * e, right: 24 * e, top: y, height: hb, borderRadius: hb, background: C.texte + "2e", overflow: "hidden" }}>
        <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${prog * 100}%`, background: `linear-gradient(90deg, ${C.accent}, ${C.accent2})` }} />
        {chap.filter((c) => c[0] > 0).map((c, i) => <div key={i} style={{ position: "absolute", left: `${(c[0] / A.duree) * 100}%`, top: 0, bottom: 0, width: 3 * e, background: C.fond }} />)}
      </div>
      {actif ? <div style={{ position: "absolute", left: 24 * e, top: y - 40 * e, fontSize: 26 * e, fontWeight: 600, color: C.texte, opacity: 0.9,
        fontFamily: `"${A.police_texte}", "Poppins", sans-serif` }}>{actif[1]}</div> : null}
    </>
  );
};

const Defilement: React.FC<SceneProps> = ({ A, a, b }) => {
  const t = useT(), u = A.u, C = A.couleurs, V = A.vitesse;
  const cw = A.zw * (A.vertical ? 0.92 : 0.62), chh = A.zh * 0.9, rayon = 28 * u * (0.4 + (A.coins ?? 0.6));
  const k = res(A, t, a + 0.1, 110);
  const hi = A.image_ratio ? cw * A.image_ratio : chh;
  const dy = -Math.max(0, hi - chh) * entre(t, a + 0.9 / V, b - 0.9 / V, Easing.bezier(0.65, 0, 0.35, 1));
  return (
    <div style={{ position: "absolute", left: A.zx + (A.zw - cw) / 2, top: A.zy + (A.zh - chh) / 2, width: cw, height: chh, borderRadius: rayon, overflow: "hidden",
      background: "#fff", border: `2px solid ${C.accent}e6`, boxShadow: `0 ${30 * u}px ${80 * u}px #0009`, opacity: Math.min(1, k) * (1 - entre(t, b - 0.5 / V, b)),
      scale: String(0.85 + 0.15 * Math.min(1.2, k)), translate: `0px ${(1 - Math.min(1, k)) * 80 * u}px` }}>
      {A.image ? <Img src={staticFile(A.image)} style={{ position: "absolute", left: 0, top: dy, width: "100%" }} /> : null}
    </div>
  );
};

const SousTitres: React.FC<SceneProps> = ({ A }) => {
  const t = useT(), C = A.couleurs, u = A.u * 1.1, st = A.style_st || "surligne", maj = A.majuscules !== false;
  const txt = (w: string) => (maj ? w.toUpperCase() : w);
  const contour = { paintOrder: "stroke fill", WebkitTextStroke: `${10 * u}px #000000c0` } as React.CSSProperties;
  if (st === "un_mot") {
    const m = (A.mots || []).find((x) => x[0] <= t && t < Math.max(x[1], x[0] + 0.25));
    if (!m) return null;
    const k = ressortT(A, (t - m[0]) * 1.4, 220);
    return <div style={{ position: "absolute", left: A.zx, width: A.zw, textAlign: "center", top: A.zy + A.zh * 0.62 - 90 * u, fontFamily: titreF(A), fontWeight: 800,
      fontSize: 150 * u * (A.vertical ? 0.8 : 1), color: txt(m[2]).length > 6 ? C.accent2 : C.texte, scale: String(0.6 + 0.4 * Math.min(1.2, k)), ...contour }}>{txt(m[2])}</div>;
  }
  const l = (A.lignes_st || []).find((x) => x.t0 - 0.05 <= t && t < x.t1 + 0.25);
  if (!l) return null;
  return (
    <div style={{ position: "absolute", left: A.zx, width: A.zw, textAlign: "center", top: A.zy + A.zh * (A.vertical ? 0.74 : 0.8) - 70 * u, fontFamily: titreF(A),
      fontWeight: 800, fontSize: 64 * u * (A.vertical ? 0.95 : 1), whiteSpace: "nowrap" }}>
      {l.mots.map(([t0, t1, w], i) => {
        const dit = t0 <= t, courant = t0 <= t && t < Math.max(t1, t0 + 0.15);
        const k = st === "saute" ? (dit ? ressortT(A, (t - t0) * 1.3, 260) : 0) : 1;
        const coul = st === "karaoke" ? (dit ? C.accent2 : C.texte) : st === "surligne" ? C.texte : courant ? C.accent2 : C.texte;
        return <span key={i} style={{ display: "inline-block", margin: `0 ${8 * u}px`, padding: `0 ${8 * u}px`, borderRadius: 10 * u, color: coul,
          background: st === "surligne" && courant ? C.accent : "transparent", opacity: st === "saute" && !dit ? 0 : 1,
          scale: String(st === "saute" ? Math.min(1.25, 0.5 + 0.5 * k) : 1), ...contour }}>{txt(w)}</span>;
      })}
    </div>
  );
};

const SCENES: Record<string, React.FC<SceneProps>> = { compteur: Compteur, barres: Barres, courbe: Courbe, titre: Titre, bandeau: Bandeau,
  progression: Progression, defilement: Defilement, sous_titres: SousTitres };

export const PhilCut: React.FC<{ A: Animation }> = ({ A }) => {
  const t = useT();
  if (!policesChargees && A.polices) {
    policesChargees = true;
    for (const [famille, fichier, poids] of A.polices) loadFont({ family: famille, url: staticFile(fichier), weight: String(poids) });
  }
  const h = A.horaire && A.horaire.genre === A.genre ? A.horaire : horaireDefaut(A);
  const fins = Math.max(...Object.values(h.scenes).map((x) => x[1]));
  return (
    <AbsoluteFill>
      <Fond A={A} />
      {Object.entries(h.scenes).sort((x, y) => x[1][0] - y[1][0]).map(([nom, [a, b]]) => {
        const S = SCENES[nom] as React.FC<SceneProps> | undefined;
        return S && t >= a - 0.01 && t <= b + 0.01 ? <S key={nom} A={A} h={h} a={a} b={b} dernier={b >= fins - 1e-6} /> : null;
      })}
      {A.logo ? <Img src={staticFile(A.logo)} style={{ position: "absolute", height: 70 * A.u * (A.vertical ? 1.3 : 1), right: A.L - A.zx - A.zw,
        top: Math.max(0, A.zy - 70 * A.u * 1.2), opacity: 0.9 }} /> : null}
    </AbsoluteFill>
  );
};
