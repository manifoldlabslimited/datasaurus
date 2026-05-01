import { useRef, useCallback, useEffect } from "react";
import { useGridStore } from "@/store/grid";
import { API_BASE } from "@/lib/api";
import type { BatchEvent } from "@/lib/types";

/** Steps between SSE snapshot frames. */
export const SNAPSHOT_EVERY = 1_000;

/** If no SSE message arrives within this time, assume the connection is dead. */
const CONNECTION_TIMEOUT_MS = 30_000;

export function useBatchSSE() {
  const esRef = useRef<EventSource | null>(null);
  const lastFrameMsRef = useRef(0);
  const frameIntervalRef = useRef(300);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearConnectionTimeout = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  const resetConnectionTimeout = () => {
    clearConnectionTimeout();
    timeoutRef.current = setTimeout(() => {
      // No data received in time — kill the connection
      esRef.current?.close();
      esRef.current = null;
      const { run, setRun, setError } = useGridStore.getState();
      if (run === "running") {
        setRun("idle");
        setError("Connection timed out. The server may be overloaded.");
      }
    }, CONNECTION_TIMEOUT_MS);
  };

  useEffect(() => {
    return () => {
      esRef.current?.close();
      esRef.current = null;
      clearConnectionTimeout();
    };
  }, []);

  const start = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    clearConnectionTimeout();

    const { cells, steps, nPoints, algorithm, setRun, setError, resetPoints } = useGridStore.getState();

    if (cells.length === 0) return;

    resetPoints();

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
    frameIntervalRef.current = 0;
    lastFrameMsRef.current = 0;

    const es = new EventSource(`${API_BASE}/generate/batch?${params}`);
    esRef.current = es;

    // Start the connection timeout — reset on each message
    resetConnectionTimeout();

    es.onmessage = (e) => {
      resetConnectionTimeout();

      try {
        const event: BatchEvent = JSON.parse(e.data);

        const now = performance.now();
        if (lastFrameMsRef.current > 0) {
          const elapsed = now - lastFrameMsRef.current;
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
          clearConnectionTimeout();
        }
      } catch (err) {
        console.warn("[SSE] malformed frame:", err);
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      clearConnectionTimeout();
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
    clearConnectionTimeout();
    useGridStore.getState().setRun("done");
  }, []);

  return { start, stop, frameIntervalRef };
}
