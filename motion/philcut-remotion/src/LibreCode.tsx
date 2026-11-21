// Fichier réécrit par PhilCut avant chaque rendu : l'animation libre écrite par l'IA. Celui-ci n'est qu'un exemple sobre.
import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import type { Infos } from "./LibreTypes";

export const Animation: React.FC<{ A: Infos }> = ({ A }) => {
  const t = useCurrentFrame() / A.fps;
  const o = interpolate(t, [0.2, 1.2], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.exp) });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontFamily: A.F.titre, fontWeight: 800, fontSize: 120 * A.u, color: A.C.texte, opacity: o,
        transform: `translateY(${(1 - o) * 40 * A.u}px)` }}>PhilCut</div>
    </AbsoluteFill>
  );
};
