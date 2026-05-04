import { useState, useRef, useCallback, useEffect } from "react";
import { API_BASE } from "@/lib/api";
import type { Point, CellStats, RunState } from "@/lib/types";

/** Steps between SSE snapshot frames (matches backend default). */
export const LOOP_SNAPSHOT_EVERY = 20;

/** If no SSE message arrives within this time, assume the connection is dead. */
const CONNECTION_TIMEOUT_MS = 30_000;

interface LoopEvent {
  shape: string;
  step: number;
  total: number;
  points: Point[];
  stats: CellStats;
}

/** Fisher–Yates shuffle (returns a new array). */
function shuffle<T>(arr: readonly T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export function useLoopSSE() {
  const [points, setPoints] = useState<Point[] | null>(null);
  const [stats, setStats] = useState<CellStats | null>(null);
  const [shape, setShape] = useState("");
  const [step, setStep] = useState(0);
  const [total, setTotal] = useState(0);
  const [run, setRun] = useState<RunState>("idle");
  const [error, setError] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const lastFrameMsRef = useRef(0);
  const frameIntervalRef = useRef(300);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearConnectionTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const resetConnectionTimeout = useCallback(() => {
    clearConnectionTimeout();
    timeoutRef.current = setTimeout(() => {
      esRef.current?.close();
      esRef.current = null;
      setRun("idle");
      setError("Connection timed out. The server may be overloaded.");
    }, CONNECTION_TIMEOUT_MS);
  }, [clearConnectionTimeout]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
      esRef.current = null;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, []);

  const start = useCallback(
    (shapes: string[]) => {
      // Close any existing connection
      esRef.current?.close();
      esRef.current = null;
      clearConnectionTimeout();

      const shuffled = shuffle(shapes);

      const params = new URLSearchParams({
        shapes: shuffled.join(","),
        snapshot_every: String(LOOP_SNAPSHOT_EVERY),
      });

      // Reset state
      setError(null);
      setRun("running");
      setShape("");
      setStep(0);
      setTotal(0);
      frameIntervalRef.current = 0;
      lastFrameMsRef.current = 0;

      const es = new EventSource(`${API_BASE}/generate/loop?${params}`);
      esRef.current = es;

      resetConnectionTimeout();

      es.onmessage = (e) => {
        resetConnectionTimeout();

        try {
          const event: LoopEvent = JSON.parse(e.data);

          // Exponential smoothing for frame interval
          const now = performance.now();
          if (lastFrameMsRef.current > 0) {
            const elapsed = now - lastFrameMsRef.current;
            frameIntervalRef.current =
              frameIntervalRef.current === 0
                ? elapsed
                : frameIntervalRef.current * 0.7 + elapsed * 0.3;
          }
          lastFrameMsRef.current = now;

          setPoints(event.points);
          setStats(event.stats);
          setShape(event.shape);
          setStep(event.step);
          setTotal(event.total);
        } catch (err) {
          console.warn("[LoopSSE] malformed frame:", err);
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        clearConnectionTimeout();
        // If we received frames, the server finished the cycle — not an error.
        if (lastFrameMsRef.current > 0) {
          setRun("done");
        } else {
          setRun("idle");
          setError("Connection to backend lost. Is it running?");
        }
      };
    },
    [clearConnectionTimeout, resetConnectionTimeout],
  );

  const stop = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    clearConnectionTimeout();
    setRun("done");
  }, [clearConnectionTimeout]);

  const clearError = useCallback(() => setError(null), []);

  return {
    start,
    stop,
    points,
    stats,
    shape,
    step,
    total,
    run,
    error,
    clearError,
    frameIntervalRef,
  };
}
