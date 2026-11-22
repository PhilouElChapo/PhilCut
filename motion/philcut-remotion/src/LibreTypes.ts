// 1.1.2 : ce que reçoit l'animation libre écrite par l'IA (fichier LibreCode.tsx, réécrit par PhilCut avant chaque rendu).
// 1.1.16 : IMG = les dessins du motion pro (adresses prêtes pour <Img src={A.IMG.id} />).
export type Infos = {
  W: number; H: number; D: number; fps: number; u: number;
  C: { fond: string; texte: string; doux: string; accent: string; accent2: string };
  F: { titre: string; texte: string };
  TRANSPARENT: boolean; LANG: string;
  IMG: Record<string, string>;
};

export type VideoPosee = { fichier: string; debut: number; duree: number; largeur: number; cx: number; cy: number };

// La fiche passée par PhilCut (--props) : les infos, plus les polices, le logo, les dessins et les plans vidéo copiés dans public/.
export type FicheLibre = Omit<Infos, "IMG"> & { cadence: number; polices?: [string, string, number][]; logo?: string;
  IMG?: Record<string, string>; VID?: VideoPosee[] };
