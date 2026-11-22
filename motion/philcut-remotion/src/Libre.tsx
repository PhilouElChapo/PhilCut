// 1.1.2 : l'enveloppe de l'animation libre : polices, fond (sauf transparent), animation de l'IA, logo.
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile } from "remotion";
import { loadFont } from "@remotion/fonts";
import { Animation } from "./LibreCode";
import type { FicheLibre } from "./LibreTypes";

let policesChargees = false;

export const EXEMPLE_LIBRE: FicheLibre = {
  W: 1920, H: 1080, D: 6, fps: 30, cadence: 30, u: 1, TRANSPARENT: false, LANG: "fr",
  C: { fond: "#0b1020", texte: "#ffffff", doux: "#9aa4c0", accent: "#22d3ee", accent2: "#a78bfa" },
  F: { titre: "Poppins", texte: "Poppins" }, polices: [],
};

export const Libre: React.FC<{ A: FicheLibre }> = ({ A }) => {
  if (!policesChargees && A.polices) {
    policesChargees = true;
    for (const [famille, fichier, poids] of A.polices) loadFont({ family: famille, url: staticFile(fichier), weight: String(poids) });
  }
  // 1.1.16 : les dessins (adresses résolues) et les plans vidéo réalistes posés en mode écran (le noir disparaît)
  const IMG: Record<string, string> = {};
  for (const [k, v] of Object.entries(A.IMG || {})) IMG[k] = staticFile(v);
  return (
    <AbsoluteFill style={{ backgroundColor: A.TRANSPARENT ? "transparent" : A.C.fond, color: A.C.texte, fontFamily: A.F.texte,
      overflow: "hidden" }}>
      <Animation A={{ ...A, IMG }} />
      {(A.VID || []).map((v, i) => (
        <Sequence key={i} from={Math.round(v.debut * A.fps)} durationInFrames={Math.max(1, Math.round(v.duree * A.fps))}>
          <OffthreadVideo src={staticFile(v.fichier)} muted style={{ position: "absolute", width: v.largeur,
            left: v.cx - v.largeur / 2, top: v.cy - (v.largeur * 9) / 32, mixBlendMode: "screen" }} />
        </Sequence>
      ))}
      {A.logo ? <Img src={staticFile(A.logo)} style={{ position: "absolute", height: 70 * A.u, right: A.W * 0.05, top: A.H * 0.05,
        opacity: 0.9 }} /> : null}
    </AbsoluteFill>
  );
};
