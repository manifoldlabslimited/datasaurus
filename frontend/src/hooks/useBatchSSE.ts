import { useRef, useCallback, useEffect } from "react";
import { useGridStore } from "@/store/grid";
import { API_BASE } from "@/lib/api";
import type { BatchEvent } from "@/lib/types";

/** Steps between SSE snapshot frames. Drives adaptive spring stiffness in ScatterCanvas. */
export const SNAPSHOT_EVERY = 1_000;

export function useBatchSSE() {
  const esRef = useRef<EventSource | null>(null);
  const lastFrameMsRef = useRef(0);
  /** Smoothed inter-frame interval (ms). Passed via AnimProvider — not stored in Zustand. */
  const frameIntervalRef = useRef(300);

  useEffect(() => {
    return () => { esRef.current?.close(); esRef.current = null; };
  }, []);

  const start = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;

    const { cells, steps, nPoints, algorithm, setRun, setError, resetPoints } = useGridStore.getState();

    // Nothing to simulate if shapes haven't loaded yet
    if (cells.length === 0) return;

    // Clear previous run's points — fresh start
    resetPoints();

    // Use whatever shapes the user has selected in the grid pickers.
    const shapes = cells.map((c) => c.shape).join(",");
    const params = new URLSearchParams({
      shapes,
      steps: String(steps),
      snapshot_every: String(SNAPSHOT_EVERY),
      n_points: String(nPoints),
      algorithm,
    });

    setRun("running");
    setError(null);
    frameIntervalRef.current = 0; // 0 = not yet measured; first frame snaps
    lastFrameMsRef.current = 0;

    const es = new EventSource(`${API_BASE}/generate/batch?${params}`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event: BatchEvent = JSON.parse(e.data);

        // EMA of inter-frame interval — written to a ref, not the store
        const now = performance.now();
        if (lastFrameMsRef.current > 0) {
          const elapsed = now - lastFrameMsRef.current;
          // Seed EMA with first real measurement; blend subsequent ones in
          frameIntervalRef.current = frameIntervalRef.current === 0
            ? elapsed
            : frameIntervalRef.current * 0.7 + elapsed * 0.3;
        }
        lastFrameMsRef.current = now;

        const { applyBatchEvent } = useGridStore.getState();
        applyBatchEvent(event.step, event.total, event.cells, event.done);
        if (event.done) {
          es.close();
          esRef.current = null;
        }
      } catch (err) {
        console.warn("[SSE] malformed frame:", err);
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      const { run, setRun: sr, setError: se } = useGridStore.getState();
      if (run === "running") {
        sr("idle");
        se("Connection to backend lost. Is it running?");
      }
    };
  }, []);

  const stop = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    useGridStore.getState().setRun("done");
  }, []);

  return { start, stop, frameIntervalRef };
}

