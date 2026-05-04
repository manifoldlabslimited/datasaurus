import type { CellStats } from "@/lib/types";

/** Target statistics from the original Datasaurus paper. */
export const TARGET_STATS: CellStats = {
  mean_x: 54.26,
  mean_y: 47.83,
  std_x: 16.76,
  std_y: 26.93,
  correlation: -0.06,
};

/** Shapes used in the continuous morph mode — curated for visual impact. */
export const LOOP_SHAPES = [
  "dino", "heart", "star", "circle", "bullseye", "spiral",
  "cross", "infinity", "figure_eight", "smiley", "pac_man",
  "fish", "crown", "lightning", "house", "parabola",
  "hourglass", "bowtie", "eye", "arch",
] as const;
