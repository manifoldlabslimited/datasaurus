"use client";

import { ScatterCanvas } from "@/components/scatter-canvas";
import { ShapePicker } from "@/components/shape-picker";
import { useGridStore } from "@/store/grid";
import type { GridCell } from "@/lib/types";
import { cn } from "@/lib/cn";

interface Props {
  cell: GridCell;
  index: number;
}

export function GridCell({ cell, index }: Props) {
  const setShape = useGridStore((s) => s.setShape);
  const running = useGridStore((s) => s.run === "running");

  return (
    <div
      className={cn(
        "flex min-h-0 flex-col gap-1 rounded-lg border bg-card p-2",
        running ? "border-primary/50" : "border-border",
      )}
    >
      <ShapePicker
        value={cell.shape}
        onChange={(s) => setShape(index, s)}
        disabled={running}
      />
      <div className="relative min-h-0 flex-1 overflow-hidden rounded">
        <ScatterCanvas points={cell.points} />
        {cell.stats && (
          <div className="absolute inset-x-0 bottom-0 flex justify-center gap-3 bg-card/75 px-2 py-1 backdrop-blur-sm">
            <StatChip label="x̄" value={cell.stats.mean_x} />
            <StatChip label="ȳ" value={cell.stats.mean_y} />
            <StatChip label="σx" value={cell.stats.std_x} />
            <StatChip label="σy" value={cell.stats.std_y} />
            <StatChip label="r" value={cell.stats.correlation} />
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
