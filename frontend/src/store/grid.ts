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
  /** Grid is always square: gridSize × gridSize. */
  gridSize: number;
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
  initShapes: (shapes: string[]) => void;
  setGridSize: (size: number) => void;
  setNPoints: (n: number) => void;
  setAlgorithm: (algorithm: Algorithm) => void;
  setError: (msg: string | null) => void;
  applyBatchEvent: (step: number, total: number, cellUpdates: Array<{ shape: string; points: [number, number][]; stats?: CellStats }>, done?: boolean) => void;
  setRun: (state: RunState) => void;
  resetPoints: () => void;
  randomizeShapes: () => void;
}

let nextCellId = 0;

function buildCells(shapes: string[]): GridCell[] {
  return shapes.map((shape) => ({ id: `cell-${nextCellId++}`, shape, points: null, stats: null }));
}

export const useGridStore = create<GridState>()(
  immer((set) => ({
    gridSize: 3,
    shapes: [],
    cells: [],
    run: "idle",
    step: 0,
    total: 0,
    steps: 400_000,
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
        const count = s.gridSize * s.gridSize;
        s.cells = buildCells(pickShapes(shapes, count));
      }),

    setGridSize: (size) =>
      set((s) => {
        const total = size * size;
        const existing = s.cells.map((c) => c.shape);
        const newShapes = pickShapes(s.shapes, total);
        const merged = Array.from({ length: total }, (_, i) =>
          i < existing.length ? existing[i] : newShapes[i]
        );
        s.gridSize = size;
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
        const count = s.gridSize * s.gridSize;
        s.cells = buildCells(pickShapes(s.shapes, count));
        s.step = 0;
        s.total = 0;
        s.run = "idle";
        s.error = null;
      }),
  }))
);
