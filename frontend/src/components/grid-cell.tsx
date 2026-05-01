"use client";

import { ScatterCanvas } from "@/components/scatter-canvas";
import { ShapePicker } from "@/components/shape-picker";
import { useGridStore } from "@/store/grid";
import type { GridCell } from "@/lib/types";
import { cn } from "@/lib/cn";
import { formatShapeName } from "@/lib/format";

interface Props {
  cell: GridCell;
  index: number;
}

/** Target stats — shown dimmed before simulation starts. */
const TARGET = { mean_x: 54.26, mean_y: 47.83, std_x: 16.76, std_y: 26.93, correlation: -0.06 };

export function GridCell({ cell, index }: Props) {
  const setShape = useGridStore((s) => s.setShape);
  const running = useGridStore((s) => s.run === "running");
  const hasPoints = cell.points !== null && cell.points.length > 0;

  const stats = cell.stats ?? (hasPoints ? null : TARGET);
  const dimmed = !cell.stats;

  return (
    <div
      className={cn(
        "group flex min-h-0 flex-col gap-1 rounded-lg border bg-card p-2 transition-colors",
        running
          ? "border-primary/50"
          : "border-border hover:border-primary/30",
      )}
    >
      <ShapePicker
        value={cell.shape}
        onChange={(s) => setShape(index, s)}
        disabled={running}
      />
      <div className="relative min-h-0 flex-1 overflow-hidden rounded">
        <ScatterCanvas points={cell.points} />

        {/* Empty state — show shape name as watermark */}
        {!hasPoints && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-semibold text-muted-foreground/15 select-none">
              {formatShapeName(cell.shape)}
            </span>
          </div>
        )}

        {/* Stats overlay */}
        {stats && (
          <div
            className={cn(
              "absolute inset-x-0 bottom-0 flex justify-center gap-3 px-2 py-1",
              dimmed
                ? "opacity-30"
                : "bg-card/75 backdrop-blur-sm",
            )}
          >
            <StatChip label="x̄" value={stats.mean_x} />
            <StatChip label="ȳ" value={stats.mean_y} />
            <StatChip label="σx" value={stats.std_x} />
            <StatChip label="σy" value={stats.std_y} />
            <StatChip label="r" value={stats.correlation} />
          </div>
        )}
      </div>
    </div>
  );
}

function StatChip({ label, value }: { label: string; value: number }) {
  return (
    <span className="font-mono text-[9px] text-muted-foreground">
      <span className="opacity-60">{label} </span>
      <span className="tabular-nums">{value.toFixed(2)}</span>
    </span>
  );
}
