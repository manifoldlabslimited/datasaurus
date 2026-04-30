"use client";

import { GridCell } from "@/components/grid-cell";
import { useGridStore } from "@/store/grid";

export function Grid() {
  const { rows, cols, cells } = useGridStore();

  return (
    <div
      className="grid h-full gap-2 p-3"
      style={{
        gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
        gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
      }}
    >
      {cells.map((cell, i) => (
        <GridCell
          key={cell.id}
          cell={cell}
          index={i}
        />
      ))}
    </div>
  );
}
