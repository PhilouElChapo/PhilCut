// 1.1.2 : ce que reçoit l'animation libre écrite par l'IA (fichier LibreCode.tsx, réécrit par PhilCut avant chaque rendu).
export type Infos = {
  W: number; H: number; D: number; fps: number; u: number;
  C: { fond: string; texte: string; doux: string; accent: string; accent2: string };
  F: { titre: string; texte: string };
  TRANSPARENT: boolean; LANG: string;
};

// La fiche passée par PhilCut (--props) : les infos, plus les polices et le logo copiés dans public/.
export type FicheLibre = Infos & { cadence: number; polices?: [string, string, number][]; logo?: string };
