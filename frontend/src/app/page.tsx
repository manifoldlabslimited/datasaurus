"use client";

import { useEffect, useCallback } from "react";
import { useShallow } from "zustand/shallow";
import { StatsBar } from "@/components/stats-bar";
import { Controls } from "@/components/controls";
import { Grid } from "@/components/grid";
import { ErrorBanner } from "@/components/error-banner";
import { useBatchSSE } from "@/hooks/useBatchSSE";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useGridStore } from "@/store/grid";
import { AnimProvider } from "@/lib/anim-context";
import { API_BASE } from "@/lib/api";
import type { CellStats } from "@/lib/types";

export default function Home() {
  const { start, stop, frameIntervalRef } = useBatchSSE();
  const initShapes = useGridStore((s) => s.initShapes);
  const error = useGridStore((s) => s.error);
  const setError = useGridStore((s) => s.setError);
  const running = useGridStore((s) => s.run) === "running";

  const liveStats = useGridStore(useShallow((s) => {
    const withStats = s.cells.filter((c): c is typeof c & { stats: CellStats } => c.stats !== null);
    if (withStats.length === 0) return null;
    const n = withStats.length;
    return {
      mean_x: withStats.reduce((sum, c) => sum + c.stats.mean_x, 0) / n,
      mean_y: withStats.reduce((sum, c) => sum + c.stats.mean_y, 0) / n,
      std_x: withStats.reduce((sum, c) => sum + c.stats.std_x, 0) / n,
      std_y: withStats.reduce((sum, c) => sum + c.stats.std_y, 0) / n,
      correlation: withStats.reduce((sum, c) => sum + c.stats.correlation, 0) / n,
    };
  }));

  useEffect(() => {
    fetch(`${API_BASE}/shapes`)
      .then((r) => r.json())
      .then((data: string[]) => initShapes(data))
      .catch((err) => {
        console.warn("[shapes] Failed to fetch shapes:", err);
      });
  }, [initShapes]);

  const handleDismissError = useCallback(() => setError(null), [setError]);

  useKeyboardShortcuts(start, stop, running);

  return (
    <AnimProvider value={frameIntervalRef}>
      <div className="flex h-screen flex-col overflow-hidden">
        <StatsBar stats={liveStats} />
        {error && (
          <ErrorBanner message={error} onDismiss={handleDismissError} />
        )}
        <Controls onSimulate={start} onStop={stop} />
        <div className="min-h-0 flex-1">
          <Grid />
        </div>
      </div>
    </AnimProvider>
  );
}
