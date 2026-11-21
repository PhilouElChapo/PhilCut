import React from "react";
import { Composition } from "remotion";
import { PhilCut, Animation, EXEMPLE } from "./PhilCut";
import { Libre, EXEMPLE_LIBRE } from "./Libre";
import type { FicheLibre } from "./LibreTypes";

// Les réglages du film (taille, cadence, durée) viennent de la fiche envoyée par PhilCut (--props).
export const RemotionRoot: React.FC = () => (
  <>
  <Composition
    id="PhilCut"
    component={PhilCut}
    defaultProps={{ A: EXEMPLE }}
    durationInFrames={420}
    fps={30}
    width={1920}
    height={1080}
    calculateMetadata={({ props }) => {
      const A = (props as { A: Animation }).A;
      return { width: A.L, height: A.H, fps: A.cadence, durationInFrames: Math.max(1, Math.round(A.duree * A.cadence)) };
    }}
  />
  {/* 1.1.2 : l'animation libre écrite par l'IA (LibreCode.tsx) */}
  <Composition
    id="Libre"
    component={Libre}
    defaultProps={{ A: EXEMPLE_LIBRE }}
    durationInFrames={180}
    fps={30}
    width={1920}
    height={1080}
    calculateMetadata={({ props }) => {
      const A = (props as { A: FicheLibre }).A;
      return { width: A.W, height: A.H, fps: A.cadence, durationInFrames: Math.max(1, Math.round(A.D * A.cadence)) };
    }}
  />
  </>
);
