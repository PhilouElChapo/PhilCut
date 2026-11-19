import React from "react";
import {
  AbsoluteFill,
  Composition,
  Easing,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as chargerInter } from "@remotion/google-fonts/Inter";
import { loadFont as chargerGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: inter } = chargerInter("normal", { weights: ["400", "600"], subsets: ["latin"] });
const { fontFamily: grotesk } = chargerGrotesk("normal", { weights: ["500", "700"], subsets: ["latin"] });

// Exemple neutre : la fréquentation d'un site, de janvier à juin
const MOIS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin"];
const VALEURS = [3120, 4380, 3960, 5870, 7240, 9820];
const TOTAL = 34390;

const ACCENT = "#8B7CFF";
const CYAN = "#3EE0F0";
const FOND = "#0B1020";
const TEXTE = "#EEF1FA";
const DOUX = "#8A93B2";

const sortie = Easing.bezier(0.16, 1, 0.3, 1);
const borne = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const nombre = (n: number) => Math.round(n).toLocaleString("fr-FR").replace(/ /g, " ");

const Fond: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: FOND, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          width: 1400,
          height: 1400,
          borderRadius: 700,
          left: -300 + Math.sin(f / 90) * 60,
          top: -700 + Math.cos(f / 110) * 50,
          background: `radial-gradient(circle, ${ACCENT}33 0%, transparent 60%)`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 1200,
          height: 1200,
          borderRadius: 600,
          right: -400 + Math.cos(f / 80) * 50,
          bottom: -700 + Math.sin(f / 100) * 40,
          background: `radial-gradient(circle, ${CYAN}22 0%, transparent 60%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: "linear-gradient(#ffffff08 1px, transparent 1px), linear-gradient(90deg, #ffffff08 1px, transparent 1px)",
          backgroundSize: "80px 80px",
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 75%)",
        }}
      />
    </AbsoluteFill>
  );
};

// Scène 1 : le chiffre qui monte, la pastille qui arrive
const Compteur: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const v = interpolate(f, [0.3 * fps, 2.6 * fps], [0, TOTAL], { ...borne, easing: Easing.bezier(0.22, 1, 0.36, 1) });
  const pastille = spring({ frame: f - 2.4 * fps, fps, config: { damping: 14, stiffness: 160 } });
  const sortieScene = interpolate(f, [3.6 * fps, 4.2 * fps], [0, 1], { ...borne, easing: Easing.in(Easing.cubic) });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        opacity: 1 - sortieScene,
        scale: String(1 - sortieScene * 0.08),
        filter: `blur(${sortieScene * 12}px)`,
      }}
    >
      <div
        style={{
          fontFamily: inter,
          fontSize: 34,
          fontWeight: 600,
          letterSpacing: 6,
          color: DOUX,
          textTransform: "uppercase",
          opacity: interpolate(f, [0, 0.6 * fps], [0, 1], borne),
          translate: `0px ${interpolate(f, [0, 0.6 * fps], [20, 0], { ...borne, easing: sortie })}px`,
        }}
      >
        Visiteurs, premier semestre
      </div>
      <div
        style={{
          fontFamily: grotesk,
          fontWeight: 700,
          fontSize: 260,
          lineHeight: 1,
          marginTop: 18,
          fontVariantNumeric: "tabular-nums",
          backgroundImage: `linear-gradient(100deg, ${TEXTE} 30%, ${ACCENT} 70%, ${CYAN})`,
          WebkitBackgroundClip: "text",
          color: "transparent",
          filter: `drop-shadow(0 20px 60px ${ACCENT}55)`,
        }}
      >
        {nombre(v)}
      </div>
      <div
        style={{
          marginTop: 36,
          padding: "14px 30px",
          borderRadius: 999,
          fontFamily: inter,
          fontWeight: 600,
          fontSize: 38,
          color: "#0B1020",
          background: `linear-gradient(90deg, ${CYAN}, ${ACCENT})`,
          scale: String(pastille),
          opacity: pastille,
        }}
      >
        ▲ +23 % sur un an
      </div>
    </AbsoluteFill>
  );
};

// Scène 2 : les barres qui poussent, chacune avec son chiffre
const Barres: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const max = 10000;
  const H = 520;
  const entree = interpolate(f, [0, 0.5 * fps], [0, 1], { ...borne, easing: sortie });
  const sortieScene = interpolate(f, [4.8 * fps, 5.3 * fps], [0, 1], { ...borne, easing: Easing.in(Easing.cubic) });
  return (
    <AbsoluteFill style={{ padding: "110px 160px", opacity: entree * (1 - sortieScene) }}>
      <div style={{ fontFamily: grotesk, fontWeight: 700, fontSize: 64, color: TEXTE }}>Mois après mois</div>
      <div style={{ fontFamily: inter, fontSize: 30, color: DOUX, marginTop: 8 }}>Visiteurs par mois</div>
      <div style={{ position: "relative", height: H, marginTop: 70 }}>
        {[0, 2500, 5000, 7500, 10000].map((g, i) => {
          const trace = interpolate(f, [0.2 * fps + i * 3, 0.9 * fps + i * 3], [0, 100], { ...borne, easing: sortie });
          return (
            <div key={g} style={{ position: "absolute", left: 0, right: 0, bottom: (g / max) * H, display: "flex", alignItems: "center" }}>
              <div style={{ width: 90, fontFamily: inter, fontSize: 22, color: DOUX, opacity: trace / 100 }}>{nombre(g)}</div>
              <div style={{ height: 1, width: `${trace}%`, backgroundColor: "#ffffff1c" }} />
            </div>
          );
        })}
        <div style={{ position: "absolute", left: 110, right: 0, bottom: 0, top: 0, display: "flex", alignItems: "flex-end", gap: 46 }}>
          {VALEURS.map((val, i) => {
            const p = spring({ frame: f - 0.6 * fps - i * 5, fps, config: { damping: 18, stiffness: 90 } });
            const record = i === VALEURS.length - 1;
            const halo = record ? interpolate(f, [2.6 * fps, 3.2 * fps], [0, 1], borne) : 0;
            return (
              <div key={MOIS[i]} style={{ flex: 1, height: "100%", position: "relative" }}>
                <div style={{ position: "absolute", left: 0, right: 0, bottom: (val / max) * H * p + 12, textAlign: "center", fontFamily: grotesk, fontWeight: 700, fontSize: 32, color: record ? CYAN : TEXTE, opacity: p, fontVariantNumeric: "tabular-nums" }}>
                  {nombre(val * p)}
                </div>
                <div
                  style={{
                    position: "absolute",
                    bottom: 0,
                    width: "100%",
                    height: (val / max) * H * p,
                    borderRadius: "18px 18px 6px 6px",
                    background: record ? `linear-gradient(180deg, ${CYAN}, ${ACCENT})` : `linear-gradient(180deg, ${ACCENT}cc, ${ACCENT}44)`,
                    boxShadow: record ? `0 0 ${60 * halo}px ${CYAN}88` : "none",
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ display: "flex", marginLeft: 110, gap: 46, marginTop: 18 }}>
        {MOIS.map((m) => (
          <div key={m} style={{ flex: 1, textAlign: "center", fontFamily: inter, fontSize: 26, color: DOUX }}>{m}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// Scène 3 : la courbe qui se trace, le point qui la suit, le record qui s'affiche
const Courbe: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const W = 1500;
  const H = 560;
  const pts = VALEURS.map((v, i) => [(i / (VALEURS.length - 1)) * W, H - (v / 10000) * H]);
  const d = pts.reduce((acc, [x, y], i) => {
    if (i === 0) return `M ${x} ${y}`;
    const [px, py] = pts[i - 1];
    const cx = (px + x) / 2;
    return `${acc} C ${cx} ${py}, ${cx} ${y}, ${x} ${y}`;
  }, "");
  const longueur = 2200;
  const p = interpolate(f, [0.4 * fps, 2.8 * fps], [0, 1], { ...borne, easing: Easing.bezier(0.65, 0, 0.35, 1) });
  const k = Math.min(pts.length - 1, p * (pts.length - 1));
  const i0 = Math.floor(k);
  const t = k - i0;
  const a = pts[i0];
  const b = pts[Math.min(pts.length - 1, i0 + 1)];
  const point = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  const record = spring({ frame: f - 2.8 * fps, fps, config: { damping: 12, stiffness: 140 } });
  const entree = interpolate(f, [0, 0.5 * fps], [0, 1], { ...borne, easing: sortie });
  return (
    <AbsoluteFill style={{ padding: "110px 160px", opacity: entree }}>
      <div style={{ fontFamily: grotesk, fontWeight: 700, fontSize: 64, color: TEXTE }}>La tendance</div>
      <div style={{ fontFamily: inter, fontSize: 30, color: DOUX, marginTop: 8 }}>Juin bat le record du semestre</div>
      <svg width={W + 40} height={H + 40} style={{ marginTop: 60, overflow: "visible" }}>
        <defs>
          <linearGradient id="trait" x1="0" x2="1">
            <stop offset="0%" stopColor={ACCENT} />
            <stop offset="100%" stopColor={CYAN} />
          </linearGradient>
          <linearGradient id="aire" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={ACCENT} stopOpacity={0.35} />
            <stop offset="100%" stopColor={ACCENT} stopOpacity={0} />
          </linearGradient>
          <clipPath id="revele">
            <rect x={0} y={-50} width={point[0]} height={H + 100} />
          </clipPath>
        </defs>
        <path d={`${d} L ${W} ${H} L 0 ${H} Z`} fill="url(#aire)" clipPath="url(#revele)" />
        <path
          d={d}
          fill="none"
          stroke="url(#trait)"
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={longueur}
          strokeDashoffset={longueur * (1 - p)}
          style={{ filter: `drop-shadow(0 0 18px ${ACCENT}aa)` }}
        />
        {pts.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={7} fill={FOND} stroke={TEXTE} strokeWidth={3} opacity={k >= i ? 1 : 0} />
        ))}
        <circle cx={point[0]} cy={point[1]} r={16} fill={CYAN} style={{ filter: `drop-shadow(0 0 20px ${CYAN})` }} />
        <g style={{ opacity: record, translate: `${pts[5][0] - 300}px ${pts[5][1] - 150 + (1 - record) * 30}px` }}>
          <rect width={300} height={96} rx={20} fill="#ffffff12" stroke="#ffffff30" />
          <text x={28} y={40} fill={DOUX} fontFamily={inter} fontSize={24}>Record</text>
          <text x={28} y={78} fill={TEXTE} fontFamily={grotesk} fontWeight={700} fontSize={38}>{nombre(VALEURS[5])}</text>
        </g>
      </svg>
    </AbsoluteFill>
  );
};

export const Chiffres: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      <Fond />
      <Sequence durationInFrames={Math.round(4.3 * fps)}>
        <Compteur />
      </Sequence>
      <Sequence from={Math.round(4 * fps)} durationInFrames={Math.round(5.4 * fps)}>
        <Barres />
      </Sequence>
      <Sequence from={Math.round(9.2 * fps)}>
        <Courbe />
      </Sequence>
    </AbsoluteFill>
  );
};

export const MyComposition = () => {
  return (
    <Composition id="Chiffres" component={Chiffres} durationInFrames={14 * 30} fps={30} width={1920} height={1080} />
  );
};
