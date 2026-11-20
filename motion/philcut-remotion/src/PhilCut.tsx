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
  // 1.0.1 : neuf types de plus
  elements?: [string, number | null, string, string][]; palette?: string[]; bouton?: string; bouton_fait?: string;
};

export type Horaire = {
  genre: string; duree: number; scenes: Record<string, [number, number]>;
  compteur?: { debut: number; fin: number; badge: number }; barres?: { grille: number; entrees: number[]; halo: number };
  courbe?: { debut: number; fin: number; record: number }; titre?: { mots: number[]; trait: number; sous_titre: number };
  bandeau?: { entree: number; texte: number; sortie: number };
  // 1.0.1
  jauge?: { debut: number; fin: number }; citation?: { mots: number[]; auteur: number };
  appel?: { entree: number; curseur: number; clic: number };
  camembert?: Entrees; comparaison?: Entrees; classement?: Entrees; chiffres_cles?: Entrees; chronologie?: Entrees; liste?: Entrees;
};
type Entrees = { entrees: number[]; fin: number };

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

// ---------------------------------------------------------------- 1.0.1 : neuf types de plus
const pct = (A: Animation, v: number) => v.toLocaleString(A.langue === "fr" ? "fr-FR" : A.langue, { maximumFractionDigits: 0 }) + " %";
const els = (A: Animation) => (A.elements || []).map(([l, v, x, tv]) => [l, v ?? 0, x, tv] as [string, number, string, string]);
const TitreHaut: React.FC<{ A: Animation }> = ({ A }) => (
  <>
    <div style={{ position: "absolute", left: 0, top: 0, fontFamily: titreF(A), fontWeight: 700, fontSize: 64 * A.u, whiteSpace: "nowrap" }}>{A.titre}</div>
    {A.sous_titre ? <div style={{ position: "absolute", left: 0, top: 80 * A.u, fontSize: 30 * A.u, color: A.couleurs.doux }}>{A.sous_titre}</div> : null}
  </>
);
const ent = (H: Entrees, i: number) => H.entrees[Math.min(i, H.entrees.length - 1)] ?? 0;

const Camembert: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, V = A.vitesse, H = h.camembert!, E = els(A), pal = A.palette || [];
  const tot = E.reduce((s, e) => s + e[1], 0) || 1;
  const cx = A.vertical ? A.zw / 2 : A.zw * 0.3, cy = A.vertical ? A.zh * 0.42 : A.zh * 0.58;
  const rr = A.vertical ? Math.min(A.zw * 0.36, A.zh * 0.22) : Math.min(A.zh * 0.32, A.zw * 0.22), ep = rr * (0.22 + 0.3 * A.epaisseur);
  const circ = 2 * Math.PI * rr;
  let cumul = 0, rec = 0;
  E.forEach((e, i) => { if (e[1] > E[rec][1]) rec = i; });
  const kf = entre(t, H.fin - 0.4 / V, H.fin + 0.2 / V);
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <TitreHaut A={A} />
      <svg width={A.zw} height={A.zh} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        <circle cx={cx} cy={cy} r={rr} fill="none" stroke={C.texte + "14"} strokeWidth={ep} />
        {E.map((e, i) => {
          const part = e[1] / tot, rot = -90 + cumul * 360; cumul += part;
          const k = entre(t, ent(H, i), ent(H, i) + 0.7 / V, SORTIE);
          return <circle key={i} cx={cx} cy={cy} r={rr} fill="none" stroke={pal[i] || C.accent} strokeWidth={ep}
            strokeDasharray={`${circ * part * k} ${circ}`} transform={`rotate(${rot} ${cx} ${cy})`} />;
        })}
      </svg>
      {E.map((e, i) => {
        const lx = A.vertical ? (i % 2) * A.zw / 2 : A.zw * 0.6, ly = A.vertical ? cy + rr + ep + 60 * u + Math.floor(i / 2) * 56 * u : A.zh * 0.28 + i * 62 * u;
        return (
          <div key={i} style={{ position: "absolute", left: lx, top: ly - 30 * u, width: A.vertical ? A.zw / 2 - 30 * u : A.zw * 0.4, height: 40 * u, display: "flex",
            alignItems: "center", fontSize: 30 * u, opacity: entre(t, ent(H, i), ent(H, i) + 0.5 / V) }}>
            <div style={{ width: 26 * u, height: 26 * u, borderRadius: 6 * u, background: pal[i] || C.accent, marginRight: 18 * u, flex: "none" }} />
            <div style={{ flex: 1, whiteSpace: "nowrap" }}>{e[0]}</div>
            <div style={{ fontWeight: 700, color: C.accent2 }}>{pct(A, (100 * e[1]) / tot)}</div>
          </div>
        );
      })}
      {E.length ? (
        <div style={{ position: "absolute", left: cx - rr, width: 2 * rr, top: cy - 50 * u, textAlign: "center", opacity: kf }}>
          <div style={{ fontFamily: titreF(A), fontWeight: 700, fontSize: 72 * u, lineHeight: 1.1 }}>{pct(A, (100 * E[rec][1]) / tot)}</div>
          <div style={{ fontSize: 26 * u, color: C.doux }}>{E[rec][0]}</div>
        </div>
      ) : null}
    </Scene>
  );
};

const Jauge: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, H = h.jauge!;
  const cx = A.zw / 2, cy = A.zh / 2, rr = Math.min(A.zw, A.zh) * 0.3, ep = rr * (0.12 + 0.18 * A.epaisseur), circ = 2 * Math.PI * rr;
  const v = Math.max(0, Math.min(100, A.valeur)), k = entre(t, H.debut, H.fin, Easing.inOut(Easing.quad));
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <svg width={A.zw} height={A.zh} style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}>
        <defs><linearGradient id="jg" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stopColor={C.accent2} /><stop offset="100%" stopColor={C.accent} /></linearGradient></defs>
        <circle cx={cx} cy={cy} r={rr} fill="none" stroke={C.texte + "1a"} strokeWidth={ep} />
        <circle cx={cx} cy={cy} r={rr} fill="none" stroke="url(#jg)" strokeWidth={ep} strokeLinecap="round" strokeDasharray={k > 0 ? `${(circ * v * k) / 100} ${circ}` : `0 ${circ}`}
          transform={`rotate(-90 ${cx} ${cy})`} style={{ filter: `drop-shadow(0 0 ${18 * u * A.lueur}px ${C.accent}aa)` }} />
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: cy - rr * 0.32, textAlign: "center", fontFamily: titreF(A), fontWeight: 700, fontSize: rr * 0.55, lineHeight: 1.1 }}>
        {nombre(A, Math.round(v * k))}</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: cy - rr - ep - 100 * u, textAlign: "center", fontFamily: titreF(A), fontWeight: 700, fontSize: 56 * u }}>{A.titre}</div>
      {A.sous_titre ? <div style={{ position: "absolute", left: 0, right: 0, top: cy + rr + ep + 24 * u, textAlign: "center", fontSize: 32 * u, color: C.doux,
        opacity: entre(t, H.fin - 0.3, H.fin + 0.3) }}>{A.sous_titre}</div> : null}
    </Scene>
  );
};

const Comparaison: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, H = h.comparaison!, E = els(A).slice(0, 2);
  while (E.length < 2) E.push(["", 0, "", ""]);
  const vmax = Math.max(1e-9, ...E.map((e) => e[1])), bas = A.zh - 60 * u, hb0 = A.zh * (A.vertical ? 0.3 : 0.38);
  const d = E[0][1] ? ((E[1][1] - E[0][1]) / Math.abs(E[0][1])) * 100 : null;
  const kb = res(A, t, H.fin, 160);
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <TitreHaut A={A} />
      {E.map((e, i) => {
        const k = res(A, t, ent(H, i), 110), cx = A.zw * (i ? 0.73 : 0.27), hb = (hb0 * e[1]) / vmax * Math.min(1, k), lb = A.zw * 0.16 * (0.6 + 0.6 * A.epaisseur);
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: cx - lb / 2, width: lb, top: bas - hb, height: hb, borderRadius: 16 * u,
              background: `linear-gradient(180deg, ${i ? C.accent2 : C.accent + "e6"}, ${C.accent}4d)` }} />
            <div style={{ position: "absolute", left: cx - A.zw / 4, width: A.zw / 2, textAlign: "center", top: bas - hb0 - 190 * u, fontFamily: titreF(A), fontWeight: 700,
              fontSize: 96 * u, color: i ? C.accent2 : C.texte, opacity: Math.min(1, k) }}>{nombre(A, e[1] * Math.min(1, k))}</div>
            <div style={{ position: "absolute", left: cx - A.zw / 4, width: A.zw / 2, textAlign: "center", top: bas + 14 * u, fontSize: 32 * u, fontWeight: 600, color: C.doux }}>{e[0]}</div>
          </React.Fragment>
        );
      })}
      {d !== null && kb > 0.001 ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: bas - hb0 * 0.5 - 36 * u, textAlign: "center" }}>
          <div style={{ display: "inline-block", padding: `${10 * u}px ${25 * u}px`, borderRadius: 999, fontWeight: 700, fontSize: 44 * u, color: C.fond,
            background: d >= 0 ? `linear-gradient(90deg, ${C.accent2}, ${C.accent})` : C.accent, scale: String(Math.min(1.2, kb)) }}>
            {(d >= 0 ? "▲ +" : "▼ ") + Math.abs(d).toLocaleString(A.langue === "fr" ? "fr-FR" : A.langue, { maximumFractionDigits: Math.abs(d) >= 10 ? 0 : 1 }) + " %"}
          </div>
        </div>
      ) : null}
    </Scene>
  );
};

const Classement: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, H = h.classement!, E = els(A);
  const n = Math.max(1, E.length), y0 = 170 * u, pas = Math.min(110 * u, (A.zh - 30 * u - y0) / n);
  const vmax = Math.max(1e-9, ...E.map((e) => e[1])), g0 = 90 * u + A.zw * 0.22, larg = A.zw - 170 * u - g0;
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <TitreHaut A={A} />
      {E.map((e, i) => {
        const k = res(A, t, ent(H, i), 100), ap = Math.max(0, Math.min(1, k)), hb = pas * (0.35 + 0.35 * A.epaisseur), w = ((larg * e[1]) / vmax) * Math.min(1, k);
        return (
          <div key={i} style={{ position: "absolute", left: 0, top: y0 + i * pas, width: A.zw, height: hb, opacity: ap }}>
            <div style={{ position: "absolute", left: 4 * u, top: hb / 2 - 26 * u, width: 52 * u, height: 52 * u, borderRadius: "50%", background: i ? C.accent : C.accent2,
              color: C.fond, fontFamily: titreF(A), fontWeight: 700, fontSize: 30 * u, lineHeight: `${52 * u}px`, textAlign: "center" }}>{i + 1}</div>
            <div style={{ position: "absolute", left: 80 * u, top: hb / 2 - 22 * u, fontSize: 32 * u, fontWeight: 600, whiteSpace: "nowrap" }}>{e[0]}</div>
            <div style={{ position: "absolute", left: g0, top: 0, width: Math.max(0, w), height: hb, borderRadius: hb / 2, background: `linear-gradient(90deg, ${C.accent}, ${C.accent2})` }} />
            <div style={{ position: "absolute", left: g0 + w + 16 * u, top: hb / 2 - 22 * u, fontFamily: titreF(A), fontWeight: 700, fontSize: 32 * u }}>{nombre(A, e[1] * Math.min(1, k))}</div>
          </div>
        );
      })}
    </Scene>
  );
};

const ChiffresCles: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, V = A.vitesse, H = h.chiffres_cles!, E = els(A);
  const n = Math.max(1, E.length), top = 170 * u, gap = 30 * u;
  const [cols, rows] = A.vertical ? [1, n] : n <= 3 ? [n, 1] : [2, 2];
  const tw = (A.zw - gap * (cols - 1)) / cols, th = Math.min((A.zh - top - gap * (rows - 1)) / rows, 360 * u);
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <TitreHaut A={A} />
      {E.map((e, i) => {
        const k = res(A, t, ent(H, i), 120), ap = Math.max(0, Math.min(1, k)), cpt = entre(t, ent(H, i), ent(H, i) + 1.4 / V, Easing.inOut(Easing.quad));
        const taille = Math.min(th * 0.42, (tw / Math.max(4, e[3].length)) * 1.5);
        return (
          <div key={i} style={{ position: "absolute", left: (i % cols) * (tw + gap), top: top + Math.floor(i / cols) * (th + gap) + (1 - Math.min(1, k)) * 40 * u,
            width: tw, height: th, borderRadius: 24 * u, background: C.texte + "12", overflow: "hidden", opacity: ap }}>
            <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 10 * u, background: i % 2 ? C.accent2 : C.accent }} />
            <div style={{ position: "absolute", left: 0, right: 0, top: th * 0.55 - taille * 0.85, textAlign: "center", fontFamily: titreF(A), fontWeight: 700,
              fontSize: taille, lineHeight: 1.1 }}>{nombre(A, e[1] * cpt)}</div>
            <div style={{ position: "absolute", left: 0, right: 0, top: th * 0.55 + 22 * u, textAlign: "center", fontSize: 36 * u, fontWeight: 500, opacity: 0.75 }}>{e[0]}</div>
          </div>
        );
      })}
    </Scene>
  );
};

const Chronologie: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, V = A.vitesse, H = h.chronologie!, E = els(A);
  const n = Math.max(1, E.length), ep = 6 * u * (0.5 + A.epaisseur), t0 = (H.entrees[0] ?? a) - 0.3;
  const prog = entre(t, t0, H.fin, Easing.inOut(Easing.quad));
  const pastille = (i: number) => res(A, t, ent(H, i), 140);
  if (A.vertical) {
    const x = 40 * u, y0 = 190 * u, y1 = A.zh - 40 * u;
    return (
      <Scene A={A} a={a} b={b} dernier={dernier}>
        <TitreHaut A={A} />
        <div style={{ position: "absolute", left: x - ep / 2, top: y0, width: ep, height: (y1 - y0) * prog, borderRadius: ep, background: C.accent }} />
        {E.map((e, i) => {
          const y = y0 + ((y1 - y0) * (i + 0.5)) / n, k = pastille(i), ap = Math.max(0, Math.min(1, k));
          return (
            <React.Fragment key={i}>
              <div style={{ position: "absolute", left: x - 14 * u, top: y - 14 * u, width: 28 * u, height: 28 * u, borderRadius: "50%", background: C.accent2, scale: String(Math.min(1.2, k)) }} />
              <div style={{ position: "absolute", left: x + 40 * u, top: y - 44 * u, width: A.zw - 80 * u, opacity: ap, translate: `${(1 - ap) * -30 * u}px 0px` }}>
                <div style={{ fontFamily: titreF(A), fontWeight: 700, fontSize: 40 * u, color: C.accent2 }}>{e[0]}</div>
                <div style={{ fontSize: 30 * u, lineHeight: 1.2 }}>{e[2]}</div>
              </div>
            </React.Fragment>
          );
        })}
      </Scene>
    );
  }
  const y = A.zh * 0.52, x0 = 20 * u, x1 = A.zw - 20 * u, larg = (x1 - x0) / n;
  void V;
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <TitreHaut A={A} />
      <div style={{ position: "absolute", left: x0, top: y - ep / 2, width: (x1 - x0) * prog, height: ep, borderRadius: ep, background: C.accent }} />
      {E.map((e, i) => {
        const x = x0 + larg * (i + 0.5), k = pastille(i), ap = Math.max(0, Math.min(1, k)), dessus = i % 2 === 0;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x - 16 * u, top: y - 16 * u, width: 32 * u, height: 32 * u, borderRadius: "50%", background: C.accent2, scale: String(Math.min(1.2, k)) }} />
            <div style={{ position: "absolute", left: x - larg / 2 + 10 * u, width: larg - 20 * u, textAlign: "center", opacity: ap,
              translate: `0px ${(1 - ap) * (dessus ? 30 : -30) * u}px`, display: "flex", flexDirection: dessus ? "column-reverse" : "column",
              ...(dessus ? { bottom: A.zh - y + 30 * u } : { top: y + 34 * u }) }}>
              <div style={{ fontFamily: titreF(A), fontWeight: 700, fontSize: 44 * u, color: C.accent2 }}>{e[0]}</div>
              <div style={{ fontSize: 28 * u, lineHeight: 1.2 }}>{e[2]}</div>
            </div>
          </React.Fragment>
        );
      })}
    </Scene>
  );
};

const Liste: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, H = h.liste!, E = els(A);
  const n = Math.max(1, E.length), y0 = 200 * u, pas = Math.min(120 * u, (A.zh - y0) / n);
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <TitreHaut A={A} />
      {E.map((e, i) => {
        const k = res(A, t, ent(H, i), 130), ap = Math.max(0, Math.min(1, k));
        return (
          <div key={i} style={{ position: "absolute", left: (1 - Math.min(1, k)) * -60 * u, top: y0 + i * pas - 52 * u, width: A.zw, display: "flex", alignItems: "center",
            fontSize: 40 * u * (A.vertical ? 0.9 : 1), fontWeight: 600, opacity: ap }}>
            <div style={{ width: 48 * u, height: 48 * u, borderRadius: "50%", background: C.accent, marginRight: 28 * u, flex: "none", color: C.fond, fontSize: 30 * u,
              fontWeight: 800, lineHeight: `${48 * u}px`, textAlign: "center" }}>✓</div>
            <div style={{ whiteSpace: "nowrap", overflow: "hidden" }}>{e[2]}</div>
          </div>
        );
      })}
    </Scene>
  );
};

const Citation: React.FC<SceneProps> = ({ A, h, a, b, dernier }) => {
  const t = useT(), u = A.u, C = A.couleurs, V = A.vitesse, H = h.citation!;
  const mots = A.titre.split(/\s+/).filter(Boolean), kq = res(A, t, a + 0.1, 120);
  return (
    <Scene A={A} a={a} b={b} dernier={dernier}>
      <div style={{ position: "absolute", left: A.zw * 0.07, right: A.zw * 0.07, top: "50%", transform: "translateY(-50%)", textAlign: "center" }}>
        <div style={{ position: "absolute", left: -A.zw * 0.02, top: -150 * u, fontFamily: titreF(A), fontWeight: 700, fontSize: 220 * u, color: C.accent,
          opacity: 0.9 * Math.max(0, Math.min(1, kq)) }}>«</div>
        <div style={{ fontFamily: titreF(A), fontWeight: 600, fontSize: 70 * u * (A.vertical ? 0.85 : 1), lineHeight: 1.15 }}>
          {mots.map((m, i) => {
            const k = entre(t, H.mots[Math.min(i, H.mots.length - 1)] ?? a, (H.mots[Math.min(i, H.mots.length - 1)] ?? a) + 0.6 / V, SORTIE);
            return <span key={i} style={{ display: "inline-block", margin: `0 ${10 * u}px`, opacity: k, translate: `0px ${(1 - k) * 30 * u}px` }}>{m}</span>;
          })}
        </div>
        {A.sous_titre ? <div style={{ marginTop: 30 * u, fontSize: 36 * u, color: C.doux, opacity: entre(t, H.auteur, H.auteur + 0.6 / V) }}>{"— " + A.sous_titre}</div> : null}
      </div>
    </Scene>
  );
};

const Appel: React.FC<SceneProps> = ({ A, h, b }) => {
  const t = useT(), uu = A.u * 1.2, C = A.couleurs, V = A.vitesse, H = h.appel!;
  const k = res(A, t, H.entree, 150);
  if (k <= 0.001) return null;
  const cx = A.zw / 2, cy = A.zh * (A.vertical ? 0.55 : 0.62), clique = t >= H.clic;
  const appui = 1 - 0.08 * Math.sin(Math.PI * entre(t, H.clic - 0.08, H.clic + 0.18));
  const kc = entre(t, H.curseur, H.clic - 0.05, SORTIE), onde = entre(t, H.clic, H.clic + 0.5);
  return (
    <div style={{ position: "absolute", left: A.zx, top: A.zy, width: A.zw, height: A.zh, opacity: Math.min(1, k) * (1 - entre(t, b - 0.5 / V, b)),
      fontFamily: `"${A.police_texte}", "Poppins", sans-serif`, color: C.texte }}>
      {A.transparent ? <div style={{ position: "absolute", left: cx - (A.zw * (A.vertical ? 0.95 : 0.6)) / 2, top: cy - 230 * uu, width: A.zw * (A.vertical ? 0.95 : 0.6),
        height: 360 * uu, borderRadius: 30 * uu, background: C.fond + "bf" }} /> : null}
      <div style={{ position: "absolute", left: 0, right: 0, top: cy - 190 * uu, textAlign: "center", fontFamily: titreF(A), fontWeight: 700, fontSize: 56 * uu }}>{A.titre}</div>
      <div style={{ position: "absolute", left: cx, top: cy, transform: "translate(-50%,-50%)", scale: String(Math.min(1.15, k) * appui), height: 100 * uu, padding: `0 ${60 * uu}px`,
        borderRadius: 50 * uu * (A.coins ?? 0.6) + 8 * uu, background: clique ? C.doux + "80" : C.accent, color: clique ? C.texte : C.fond, fontFamily: titreF(A),
        fontWeight: 700, fontSize: 46 * uu, lineHeight: `${100 * uu}px`, whiteSpace: "nowrap" }}>{clique ? A.bouton_fait : A.bouton}</div>
      {A.sous_titre ? <div style={{ position: "absolute", left: 0, right: 0, top: cy + 80 * uu, textAlign: "center", fontSize: 32 * uu, color: C.doux }}>{A.sous_titre}</div> : null}
      {kc > 0 && t < H.clic + 0.9 ? (
        <svg viewBox="0 0 36 54" width={36 * uu} height={54 * uu} style={{ position: "absolute", left: cx + 40 * uu + (1 - kc) * A.zw * 0.35, top: cy + 10 * uu + (1 - kc) * A.zh * 0.3 }}>
          <path d="M0 0 L0 46 L12 35 L21 54 L29 50 L20 32 L36 32 Z" fill="#fff" stroke="#000c" strokeWidth={3} />
        </svg>
      ) : null}
      {clique && onde < 1 ? <div style={{ position: "absolute", left: cx + 40 * uu - 60 * uu * onde, top: cy + 10 * uu - 60 * uu * onde, width: 120 * uu * onde, height: 120 * uu * onde,
        borderRadius: "50%", border: `${4 * uu}px solid ${C.accent2}`, opacity: 1 - onde }} /> : null}
    </div>
  );
};

const SCENES: Record<string, React.FC<SceneProps>> = { compteur: Compteur, barres: Barres, courbe: Courbe, titre: Titre, bandeau: Bandeau,
  progression: Progression, defilement: Defilement, sous_titres: SousTitres, camembert: Camembert, jauge: Jauge, comparaison: Comparaison,
  classement: Classement, chiffres_cles: ChiffresCles, chronologie: Chronologie, liste: Liste, citation: Citation, appel: Appel };

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
