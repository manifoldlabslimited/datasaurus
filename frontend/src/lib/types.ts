export type Point = [number, number];

export type Algorithm = "sa" | "langevin" | "momentum";

export interface CellStats {
  mean_x: number;
  mean_y: number;
  std_x: number;
  std_y: number;
  correlation: number;
}

export interface CellSnapshot {
  shape: string;
  points: Point[];
  stats?: CellStats;
}

export interface BatchEvent {
  step: number;
  total: number;
  done?: boolean;
  cells: CellSnapshot[];
}

/** One cell in the grid — identified by a stable unique ID. */
export interface GridCell {
  id: string;
  shape: string;
  /** Latest point cloud for this cell, null before first event. */
  points: Point[] | null;
  stats: CellStats | null;
}

export type RunState = "idle" | "running" | "done";
