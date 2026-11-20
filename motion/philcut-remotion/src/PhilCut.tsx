// Le moteur Remotion de PhilCut : la fiche de l'animation (mise_en_page de app/motion_html.py) dessinée avec le look de
// l'étalon « Chiffres » validé le 19/11 : fond qui respire, chiffre qui monte, barres qui poussent, courbe qui se trace.
import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
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
  return A.prefixe + (A.langue === "fr" ? t.replace(/[  ]/g, " ") : t) + A.suffixe;
};
const haut = (v: number) => {
  if (v <= 0) return 1;
  const e = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * e >= v) return m * e;
  return 10 * e;
};
const hex2 = (x: number) => Math.round(Math.max(0, Math.min(255, x))).toString(16).padStart(2, "0");

// Ressort : rebond 0 = sans dépassement, 1 = très élastique
const ressort = (A: Animation, f: number, fps: number, raideur = 120) =>
  spring({ frame: f, fps, config: { stiffness: raideur, damping: 2 * Math.sqrt(raideur) * (1 - 0.7 * A.rebond) } });

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

const Scene: React.FC<{ A: Animation; duree: number; dernier: boolean; children: React.ReactNode }> = ({ A, duree, dernier, children }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (f / fps) * A.vitesse;
  const D = duree * A.vitesse;
  const entree = interpolate(t, [0, 0.5], [0, 1], { ...borne, easing: SORTIE });
  const sortie = dernier ? 0 : interpolate(t, [D - 0.5, D], [0, 1], { ...borne, easing: Easing.in(Easing.cubic) });
  const m = 30 * A.u;
  return (
    <AbsoluteFill style={{ opacity: entree * (1 - sortie), scale: String(1 - 0.06 * sortie) }}>
      {A.transparent ? <div style={{ position: "absolute", left: A.zx - m, top: A.zy - m, width: A.zw + 2 * m, height: A.zh + 2 * m,
        borderRadius: 36 * A.u, background: A.couleurs.fond + "b8" }} /> : null}
      <div style={{ position: "absolute", left: A.zx, top: A.zy, width: A.zw, height: A.zh, fontFamily: A.police_texte, color: A.couleurs.texte }}>
        {children}
        {A.source ? <div style={{ position: "absolute", left: 0, bottom: -40 * A.u, fontSize: 22 * A.u, color: A.couleurs.doux }}>{A.source}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

const Compteur: React.FC<{ A: Animation; duree: number; dernier: boolean }> = ({ A, duree, dernier }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = A.u, C = A.couleurs, V = A.vitesse;
  const v = interpolate(f * V, [0.3 * fps, 2.6 * fps], [0, A.valeur], { ...borne, easing: Easing.bezier(0.22, 1, 0.36, 1) });
  const p = ressort(A, f * V - 2.4 * fps, fps, 160);
  const lab = interpolate(f * V, [0, 0.6 * fps], [0, 1], borne);
  return (
    <Scene A={A} duree={duree} dernier={dernier}>
      <div style={{ position: "absolute", left: 0, right: 0, top: (A.vertical ? 0.42 : 0.48) * A.zh, transform: "translateY(-50%)", textAlign: "center" }}>
        <div style={{ fontSize: 34 * u, fontWeight: 600, letterSpacing: 6 * u, color: C.doux, textTransform: "uppercase", opacity: lab,
          translate: `0px ${(1 - SORTIE(lab)) * 20 * u}px` }}>{A.titre}</div>
        <div style={{ fontFamily: A.police_titre, fontWeight: 700, fontSize: 260 * u * (A.vertical ? 0.8 : 1), lineHeight: 1, marginTop: 18 * u,
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

const Barres: React.FC<{ A: Animation; duree: number; dernier: boolean }> = ({ A, duree, dernier }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = A.u, C = A.couleurs, V = A.vitesse;
  const top = 190 * u, bas = A.zh - 60 * u, Hc = bas - top, gauche = 110 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1])));
  const nb = A.donnees.length, ecart = 46 * u * (nb > 8 ? 0.6 : 1);
  const larg = (A.zw - gauche - ecart * (nb - 1)) / nb, lb = larg * (0.45 + 0.55 * A.epaisseur);
  let rec = 0;
  A.donnees.forEach((d, i) => { if (d[1] > A.donnees[rec][1]) rec = i; });
  return (
    <Scene A={A} duree={duree} dernier={dernier}>
      <div style={{ position: "absolute", left: 0, top: 0, fontFamily: A.police_titre, fontWeight: 700, fontSize: 64 * u, whiteSpace: "nowrap" }}>{A.titre_barres}</div>
      <div style={{ position: "absolute", left: 0, top: 80 * u, fontSize: 30 * u, color: C.doux }}>{A.sous_titre}</div>
      {[0, 1, 2, 3, 4].map((i) => {
        const tr = interpolate(f * V, [(0.2 + i * 0.1) * fps, (0.9 + i * 0.1) * fps], [0, 1], { ...borne, easing: SORTIE });
        const y = bas - (i / 4) * Hc;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: 0, top: y - 14 * u, fontSize: 22 * u, color: C.doux, opacity: tr }}>{nombre({ ...A, prefixe: "", suffixe: "" }, (vmax * i) / 4)}</div>
            <div style={{ position: "absolute", left: gauche, top: y, height: 1, width: (A.zw - gauche) * tr, background: C.texte + "1c" }} />
          </React.Fragment>
        );
      })}
      {A.donnees.map((d, i) => {
        const p = ressort(A, f * V - (0.6 + i * A.decalage) * fps, fps, 90);
        const x = gauche + i * (larg + ecart) + (larg - lb) / 2, h = (d[1] / vmax) * Hc * p, record = i === rec;
        const halo = record ? interpolate(f * V, [2.6 * fps, 3.2 * fps], [0, 1], borne) * A.lueur : 0;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x - 40 * u, width: lb + 80 * u, textAlign: "center", top: bas - h - 50 * u, opacity: Math.min(1, p),
              fontFamily: A.police_titre, fontWeight: 700, fontSize: 32 * u * (nb > 8 ? 0.8 : 1), color: record ? C.accent2 : C.texte }}>
              {nombre(A, d[1] * Math.min(1, p))}
            </div>
            <div style={{ position: "absolute", left: x, width: lb, top: bas - h, height: Math.max(0, h), borderRadius: `${18 * u}px ${18 * u}px ${6 * u}px ${6 * u}px`,
              background: record ? `linear-gradient(180deg, ${C.accent2}, ${C.accent})` : `linear-gradient(180deg, ${C.accent}cc, ${C.accent}44)`,
              boxShadow: halo > 0 ? `0 0 ${60 * u * halo}px ${C.accent2}88` : "none" }} />
            <div style={{ position: "absolute", left: x - 40 * u, width: lb + 80 * u, textAlign: "center", top: bas + 12 * u, fontSize: 26 * u * (nb > 8 ? 0.8 : 1), color: C.doux }}>{d[0]}</div>
          </React.Fragment>
        );
      })}
    </Scene>
  );
};

const Courbe: React.FC<{ A: Animation; duree: number; dernier: boolean }> = ({ A, duree, dernier }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = A.u, C = A.couleurs, V = A.vitesse;
  const top = 230 * u, bas = A.zh - 90 * u, g = 20 * u, dr = A.zw - 20 * u;
  const vmax = haut(Math.max(...A.donnees.map((d) => d[1]))), nb = A.donnees.length;
  const pts = A.donnees.map((d, i) => [g + (i / Math.max(1, nb - 1)) * (dr - g), bas - (d[1] / vmax) * (bas - top)]);
  const d = pts.reduce((acc, [x, y], i) => {
    if (i === 0) return `M ${x} ${y}`;
    const [px, py] = pts[i - 1];
    const cx = (px + x) / 2;
    return `${acc} C ${cx} ${py}, ${cx} ${y}, ${x} ${y}`;
  }, "");
  const p = interpolate(f * V, [0.4 * fps, 2.8 * fps], [0, 1], { ...borne, easing: Easing.bezier(0.65, 0, 0.35, 1) });
  const k = Math.min(nb - 1, p * (nb - 1)), i0 = Math.floor(k), t = k - i0;
  const a = pts[i0], b = pts[Math.min(nb - 1, i0 + 1)];
  const point = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  let rec = 0;
  A.donnees.forEach((x, i) => { if (x[1] > A.donnees[rec][1]) rec = i; });
  const r = ressort(A, f * V - 2.8 * fps, fps, 140);
  const w = 300 * u, h = 96 * u;
  const cx = Math.min(Math.max(0, pts[rec][0] - w - 40 * u), A.zw - w), cy = Math.max(130 * u, pts[rec][1] - 60 * u - h);
  return (
    <Scene A={A} duree={duree} dernier={dernier}>
      <div style={{ position: "absolute", left: 0, top: 0, fontFamily: A.police_titre, fontWeight: 700, fontSize: 64 * u, whiteSpace: "nowrap" }}>{A.titre_courbe}</div>
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
      <div style={{ position: "absolute", left: cx, top: cy + (1 - Math.min(1, r)) * 30 * u, width: w, height: h, borderRadius: 20 * u, background: "#ffffff12",
        border: "1px solid #ffffff30", padding: `${14 * u}px ${28 * u}px`, opacity: Math.min(1, r) }}>
        <div style={{ fontSize: 24 * u, color: C.doux }}>{A.record}</div>
        <div style={{ fontFamily: A.police_titre, fontWeight: 700, fontSize: 38 * u }}>{A.textes_valeurs[rec]}</div>
      </div>
    </Scene>
  );
};

const Titre: React.FC<{ A: Animation; duree: number }> = ({ A, duree }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = A.u, C = A.couleurs, V = A.vitesse;
  const mots = A.titre.split(/\s+/).filter(Boolean);
  const nu = (m: string) => m.replace(/[.,;:!?«»"']/g, "");
  const cle = mots.length > 2 ? mots.reduce((a, b) => (nu(b).length > nu(a).length ? b : a)) : "";
  const fin = interpolate(f * V, [(duree - 0.6) * V * fps, duree * V * fps], [1, 0], borne);
  const trait = interpolate(f * V, [(0.4 + mots.length * A.decalage * 0.5) * fps, (1.2 + mots.length * A.decalage * 0.5) * fps], [0, 1], { ...borne, easing: SORTIE });
  return (
    <Scene A={A} duree={duree} dernier>
      <div style={{ position: "absolute", left: 0, right: 0, top: "50%", transform: "translateY(-50%)", textAlign: "center", opacity: fin }}>
        <div style={{ fontFamily: A.police_titre, fontWeight: 700, fontSize: 120 * u * (A.vertical ? 0.75 : 1), lineHeight: 1.05 }}>
          {mots.map((m, i) => {
            const p = ressort(A, f * V - (0.15 + i * A.decalage) * fps, fps, 150);
            return <span key={i} style={{ display: "inline-block", margin: `0 ${14 * u}px`, color: m === cle ? C.accent : C.texte, opacity: Math.min(1, p),
              translate: `0px ${(1 - Math.min(1, p)) * 60 * u}px` }}>{m}</span>;
          })}
        </div>
        <div style={{ width: A.zw * 0.22 * trait, height: 8 * u * (0.5 + A.epaisseur), borderRadius: 4 * u, background: C.accent2, margin: `${30 * u}px auto 0` }} />
        {A.sous_titre ? <div style={{ fontSize: 40 * u, color: C.doux, marginTop: 24 * u, opacity: interpolate(f * V, [0.8 * fps, 1.4 * fps], [0, 1], borne) }}>{A.sous_titre}</div> : null}
      </div>
    </Scene>
  );
};

export const PhilCut: React.FC<{ A: Animation }> = ({ A }) => {
  const { fps } = useVideoConfig();
  if (!policesChargees && A.polices) {
    policesChargees = true;
    for (const [famille, fichier, poids] of A.polices) loadFont({ family: famille, url: staticFile(fichier), weight: String(poids) });
  }
  const D = A.duree;
  const fr = (s: number) => Math.round(s * fps);
  let scenes: React.ReactNode;
  if (A.genre === "compteur") scenes = <Compteur A={A} duree={D} dernier />;
  else if (A.genre === "barres") scenes = <Barres A={A} duree={D} dernier />;
  else if (A.genre === "courbe") scenes = <Courbe A={A} duree={D} dernier />;
  else if (A.genre === "titre") scenes = <Titre A={A} duree={D} />;
  else
    scenes = (
      <>
        <Sequence durationInFrames={fr((D * 4.3) / 14)}><Compteur A={A} duree={(D * 4.3) / 14} dernier={false} /></Sequence>
        <Sequence from={fr((D * 4.0) / 14)} durationInFrames={fr((D * 5.4) / 14)}><Barres A={A} duree={(D * 5.4) / 14} dernier={false} /></Sequence>
        <Sequence from={fr((D * 9.2) / 14)}><Courbe A={A} duree={D - (D * 9.2) / 14} dernier /></Sequence>
      </>
    );
  return (
    <AbsoluteFill>
      <Fond A={A} />
      {scenes}
      {A.logo ? <Img src={staticFile(A.logo)} style={{ position: "absolute", height: 70 * A.u * (A.vertical ? 1.3 : 1), right: A.L - A.zx - A.zw,
        top: Math.max(0, A.zy - 70 * A.u * 1.2), opacity: 0.9 }} /> : null}
    </AbsoluteFill>
  );
};
