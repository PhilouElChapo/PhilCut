import React, { useMemo } from "react";
import { AbsoluteFill, Easing, interpolate, random, useCurrentFrame } from "remotion";
import type { Infos } from "./LibreTypes";

// Exemple écrit à la main comme l'IA doit l'écrire (contrat CONSIGNE_REMOTION) : le cadeau grandit pendant que le compteur
// monte de 0 à 40 avec les barres ; à 40, feu d'artifice ; puis tout part en confettis.
const C = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

type Etincelle = { cx: number; cy: number; angle: number; vitesse: number; couleur: string; debut: number };
type Confetti = { x: number; y: number; vx: number; vy: number; rot: number; couleur: string; l: number; h: number };

export const Animation: React.FC<{ A: Infos }> = ({ A }) => {
  const t = useCurrentFrame() / A.fps;
  const u = A.u;
  const vertical = A.H > A.W;
  const couleurs = [A.C.accent, A.C.accent2, "#ffd166", "#ff5d8f", "#ffffff"];
  const cx = A.W / 2;
  const cy = vertical ? A.H * 0.36 : A.H * 0.42;

  // 0 à 4 s : le cadeau grandit, le compteur monte, les barres aussi
  const montee = interpolate(t, [0.3, 4], [0, 1], { ...C, easing: Easing.inOut(Easing.cubic) });
  const valeur = Math.round(40 * montee);
  const echelle = interpolate(t, [0.3, 4], [0.08, 1], { ...C, easing: Easing.out(Easing.back(1.4)) });
  // 7 à 9 s : l'image part en confettis
  const fuite = interpolate(t, [7, 7.6], [1, 0], C);

  const etincelles = useMemo<Etincelle[]>(() => {
    const out: Etincelle[] = [];
    const centres = [[-0.25, -0.2, 4.2], [0.22, -0.28, 4.6], [0, -0.38, 5.1], [-0.12, -0.05, 5.6]];
    centres.forEach(([dx, dy, debut], k) => {
      for (let i = 0; i < 46; i++) {
        out.push({ cx: dx, cy: dy, angle: (i / 46) * Math.PI * 2 + random(`a${k}${i}`) * 0.2, vitesse: 0.6 + random(`v${k}${i}`) * 0.5,
          couleur: couleurs[Math.floor(random(`c${k}${i}`) * couleurs.length)], debut });
      }
    });
    return out;
  }, [A.C.accent, A.C.accent2]);

  const confettis = useMemo<Confetti[]>(() => Array.from({ length: 260 }, (_v, i) => ({
    x: (random(`x${i}`) - 0.5) * 0.5, y: (random(`y${i}`) - 0.5) * 0.4, vx: (random(`vx${i}`) - 0.5) * 0.9,
    vy: -0.2 - random(`vy${i}`) * 0.5, rot: random(`r${i}`) * 720 - 360, couleur: couleurs[i % couleurs.length],
    l: 10 + random(`l${i}`) * 12, h: 6 + random(`h${i}`) * 8,
  })), [A.C.accent, A.C.accent2]);

  const barres = 9;
  const largeurBarre = (vertical ? 46 : 40) * u;
  const hautMax = (vertical ? 300 : 240) * u;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: cx - 520 * u, top: cy - 520 * u, width: 1040 * u, height: 1040 * u, borderRadius: "50%",
        background: `radial-gradient(circle, ${A.C.accent2}55 0%, transparent 65%)`, opacity: fuite }} />
      {/* le cadeau */}
      <div style={{ position: "absolute", left: cx - 150 * u, top: cy - 170 * u, width: 300 * u, height: 300 * u, opacity: fuite,
        transform: `scale(${echelle})` }}>
        <svg viewBox="0 0 100 100" width={300 * u} height={300 * u}>
          <defs>
            <linearGradient id="boite" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor={A.C.accent2} /><stop offset="1" stopColor={A.C.accent} />
            </linearGradient>
          </defs>
          <rect x="16" y="40" width="68" height="52" rx="5" fill="url(#boite)" />
          <rect x="12" y="30" width="76" height="16" rx="4" fill={A.C.accent2} />
          <rect x="45" y="30" width="10" height="62" fill="#fff6d5" />
          <rect x="12" y="35" width="76" height="6" fill="#fff6d5" opacity="0.9" />
          <path d="M50 30 C 36 14, 24 22, 34 30 Z M50 30 C 64 14, 76 22, 66 30 Z" fill="#fff6d5" />
        </svg>
      </div>
      {/* le compteur */}
      <div style={{ position: "absolute", left: 0, width: A.W, top: cy + 150 * u, textAlign: "center", opacity: fuite }}>
        <div style={{ fontFamily: A.F.titre, fontWeight: 800, fontSize: 150 * u, lineHeight: 1, color: A.C.texte }}>{valeur}</div>
        <div style={{ fontFamily: A.F.texte, fontSize: 40 * u, letterSpacing: 8 * u, color: A.C.doux }}>ANS</div>
      </div>
      {/* le graphique qui monte en même temps */}
      <div style={{ position: "absolute", left: vertical ? cx - (barres * largeurBarre * 1.5) / 2 : A.W * 0.66,
        top: vertical ? A.H * 0.62 : cy - hautMax / 2, height: hautMax, width: barres * largeurBarre * 1.5, opacity: fuite }}>
        {Array.from({ length: barres }, (_v, i) => {
          const h = hautMax * (0.12 + 0.88 * ((i + 1) / barres)) * interpolate(montee, [i / (barres + 2), (i + 3) / (barres + 2)], [0, 1], C);
          return <div key={i} style={{ position: "absolute", left: i * largeurBarre * 1.5, bottom: 0, width: largeurBarre, height: hautMax,
            borderRadius: 6 * u, background: `linear-gradient(0deg, ${A.C.accent2}, ${A.C.accent})`, transformOrigin: "bottom",
            transform: `scaleY(${h / hautMax})` }} />;
        })}
      </div>
      {/* 4,2 à 7 s : feu d'artifice */}
      {etincelles.map((e, i) => {
        const p = interpolate(t, [e.debut, e.debut + 1.6], [0, 1], C);
        if (p <= 0 || p >= 1) return null;
        const d = Math.sqrt(p) * 380 * u * e.vitesse;
        const x = cx + e.cx * A.W * (vertical ? 1 : 0.6) + Math.cos(e.angle) * d;
        const y = cy + e.cy * A.H + Math.sin(e.angle) * d + 120 * u * p * p;
        return <div key={i} style={{ position: "absolute", left: 0, top: 0, width: 8 * u, height: 8 * u, borderRadius: "50%",
          background: e.couleur, boxShadow: `0 0 ${14 * u}px ${e.couleur}`, opacity: 1 - p, transform: `translate(${x}px, ${y}px)` }} />;
      })}
      {/* 7 à 9,5 s : l'image part en confettis */}
      {confettis.map((c, i) => {
        const p = interpolate(t, [7, 9.5], [0, 1], C);
        if (p <= 0) return null;
        const x = cx + c.x * A.W + c.vx * A.W * p;
        const y = cy + c.y * A.H + (c.vy * p + 1.1 * p * p) * A.H * 0.6;
        return <div key={i} style={{ position: "absolute", left: 0, top: 0, width: c.l * u, height: c.h * u, background: c.couleur,
          opacity: interpolate(p, [0, 0.05, 0.8, 1], [0, 1, 1, 0]), transform: `translate(${x}px, ${y}px) rotate(${c.rot * p}deg)` }} />;
      })}
    </AbsoluteFill>
  );
};
