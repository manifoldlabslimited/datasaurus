import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { GridCell, RunState, CellStats, Algorithm } from "@/lib/types";

/** Fisher-Yates shuffle — returns a new shuffled copy. */
function shuffle<T>(arr: readonly T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** Pick `count` shapes from `pool`, cycling through a shuffled copy. */
function pickShapes(pool: readonly string[], count: number): string[] {
  if (pool.length === 0) return [];
  const shuffled = shuffle(pool);
  return Array.from({ length: count }, (_, i) => shuffled[i % shuffled.length]);
}

interface GridState {
  rows: number;
  cols: number;
  /** All available shapes from the backend. Empty until fetched. */
  shapes: string[];
  cells: GridCell[];
  run: RunState;
  step: number;
  total: number;
  steps: number;
  nPoints: number;
  algorithm: Algorithm;
  error: string | null;

  setShape: (idx: number, shape: string) => void;
  /** Called once on boot with the backend shape list. Populates dropdowns AND deals initial cell shapes. */
  initShapes: (shapes: string[]) => void;
  setRows: (rows: number) => void;
  setCols: (cols: number) => void;
  setNPoints: (n: number) => void;
  setAlgorithm: (algorithm: Algorithm) => void;
  setError: (msg: string | null) => void;
  applyBatchEvent: (step: number, total: number, cellUpdates: Array<{ shape: string; points: [number, number][]; stats?: CellStats }>, done?: boolean) => void;
  setRun: (state: RunState) => void;
  /** Clear points/stats from all cells, reset step counters. Shapes are preserved. */
  resetPoints: () => void;
  /** Re-deal random shapes into all cells, clear points, back to idle. */
  randomizeShapes: () => void;
}

let nextCellId = 0;

function buildCells(shapes: string[]): GridCell[] {
  return shapes.map((shape) => ({ id: `cell-${nextCellId++}`, shape, points: null, stats: null }));
}

export const useGridStore = create<GridState>()(
  immer((set) => ({
    rows: 3,
    cols: 3,
    shapes: [],
    cells: [],  // empty until shapes are fetched
    run: "idle",
    step: 0,
    total: 0,
    steps: 1_000_000,
    nPoints: 142,
    algorithm: "sa" as Algorithm,
    error: null,

    setShape: (idx, shape) =>
      set((s) => {
        if (s.cells[idx]) s.cells[idx].shape = shape;
      }),

    initShapes: (shapes) =>
      set((s) => {
        s.shapes = shapes;
        // Deal random shapes into the current grid
        const count = s.rows * s.cols;
        s.cells = buildCells(pickShapes(shapes, count));
      }),

    setRows: (rows) =>
      set((s) => {
        const total = rows * s.cols;
        // Keep existing cell shapes, fill new slots with random picks
        const existing = s.cells.map((c) => c.shape);
        const newShapes = pickShapes(s.shapes, total);
        const merged = Array.from({ length: total }, (_, i) =>
          i < existing.length ? existing[i] : newShapes[i]
        );
        s.rows = rows;
        s.cells = buildCells(merged);
        s.run = "idle";
      }),

    setCols: (cols) =>
      set((s) => {
        const total = s.rows * cols;
        const existing = s.cells.map((c) => c.shape);
        const newShapes = pickShapes(s.shapes, total);
        const merged = Array.from({ length: total }, (_, i) =>
          i < existing.length ? existing[i] : newShapes[i]
        );
        s.cols = cols;
        s.cells = buildCells(merged);
        s.run = "idle";
      }),

    setNPoints: (n) => set((s) => { s.nPoints = n; }),
    setAlgorithm: (algorithm) => set((s) => { s.algorithm = algorithm; }),
    setError: (msg) => set((s) => { s.error = msg; }),

    applyBatchEvent: (step, total, cellUpdates, done) =>
      set((s) => {
        s.step = step;
        s.total = total;
        cellUpdates.forEach((u, i) => {
          if (s.cells[i]) {
            s.cells[i].points = u.points;
            if (u.stats) s.cells[i].stats = u.stats;
          }
        });
        if (done) s.run = "done";
      }),

    setRun: (state) => set((s) => { s.run = state; }),

    resetPoints: () =>
      set((s) => {
        s.cells.forEach((c: GridCell) => { c.points = null; c.stats = null; });
        s.step = 0;
        s.total = 0;
        s.run = "idle";
        s.error = null;
      }),

    randomizeShapes: () =>
      set((s) => {
        const count = s.rows * s.cols;
        s.cells = buildCells(pickShapes(s.shapes, count));
        s.step = 0;
        s.total = 0;
        s.run = "idle";
        s.error = null;
      }),
  }))
);
