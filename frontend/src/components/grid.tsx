"use client";

import { GridCell } from "@/components/grid-cell";
import { useGridStore } from "@/store/grid";

export function Grid() {
  const { gridSize, cells } = useGridStore();

  return (
    <div
      className="grid h-full gap-2 p-3"
      style={{
        gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))`,
        gridTemplateRows: `repeat(${gridSize}, minmax(0, 1fr))`,
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
