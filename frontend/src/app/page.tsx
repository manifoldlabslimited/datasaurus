"use client";

import { useEffect } from "react";
import { StatsBar } from "@/components/stats-bar";
import { Controls } from "@/components/controls";
import { Grid } from "@/components/grid";
import { useBatchSSE } from "@/hooks/useBatchSSE";
import { useGridStore } from "@/store/grid";
import { AnimProvider } from "@/lib/anim-context";
import { API_BASE } from "@/lib/api";

export default function Home() {
  const { start, stop, frameIntervalRef } = useBatchSSE();
  const initShapes = useGridStore((s) => s.initShapes);
  const error = useGridStore((s) => s.error);
  const setError = useGridStore((s) => s.setError);

  useEffect(() => {
    fetch(`${API_BASE}/shapes`)
      .then((r) => r.json())
      .then((data: string[]) => initShapes(data))
      .catch((err) => {
        console.warn("[shapes] Failed to fetch shapes:", err);
      });
  }, [initShapes]);

  return (
    <AnimProvider value={frameIntervalRef}>
      <div className="flex h-screen flex-col overflow-hidden">
        <StatsBar />
        {error && (
          <div
            role="alert"
            className="flex items-center justify-between border-b border-destructive/30 bg-destructive/10 px-4 py-1.5 text-xs text-destructive"
          >
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              aria-label="Dismiss error"
              className="ml-4 text-destructive/60 transition-colors hover:text-destructive"
            >
              ✕
            </button>
          </div>
        )}
        <Controls onSimulate={start} onStop={stop} />
        <div className="min-h-0 flex-1">
          <Grid />
        </div>
      </div>
    </AnimProvider>
  );
}

