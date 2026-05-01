"use client";

import { useShallow } from "zustand/shallow";
import { useGridStore } from "@/store/grid";
import type { CellStats } from "@/lib/types";
import { cn } from "@/lib/cn";
import { TARGET_STATS } from "@/lib/constants";

export function StatsBar() {
  const run = useGridStore((s) => s.run);
  const step = useGridStore((s) => s.step);
  const total = useGridStore((s) => s.total);
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

  const stats = liveStats ?? TARGET_STATS;
  const dimmed = !liveStats;
  const running = run === "running";

  return (
    <div className="flex h-9 items-center justify-between border-b border-border bg-card px-4 text-[11px]">
      <span className="text-primary font-semibold tracking-wider uppercase text-[10px]">
        Datasaurus
      </span>

      <div className={cn("flex items-center gap-6", dimmed ? "opacity-30" : "text-muted-foreground")}>
        <StatItem label="x̄" value={stats.mean_x.toFixed(2)} />
        <StatItem label="ȳ" value={stats.mean_y.toFixed(2)} />
        <StatItem label="σx" value={stats.std_x.toFixed(2)} />
        <StatItem label="σy" value={stats.std_y.toFixed(2)} />
        <StatItem label="r" value={stats.correlation.toFixed(2)} />
      </div>

      <div className="text-[10px] text-muted-foreground tabular-nums min-w-16 text-right">
        {running
          ? `${step.toLocaleString()} / ${total.toLocaleString()}`
          : step > 0
            ? `${step.toLocaleString()} steps`
            : "ready"}
      </div>
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <span>
      <span className="opacity-60 mr-1">{label}</span>
      <span className="text-foreground font-mono">{value}</span>
    </span>
  );
}
