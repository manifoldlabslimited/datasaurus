"use client";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useGridStore } from "@/store/grid";
import { Shuffle } from "lucide-react";

interface Props {
  onSimulate: () => void;
  onStop: () => void;
}

export function Controls({ onSimulate, onStop }: Props) {
  const { gridSize, nPoints, algorithm, run, step, total, setGridSize, setNPoints, setAlgorithm, randomizeShapes } = useGridStore();

  const progress = total > 0 ? step / total : 0;
  const running = run === "running";
  const done = run === "done";

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-border/40 bg-card/80 px-4 py-2.5 backdrop-blur-sm">

      {/* Grid size */}
      <ControlGroup>
        <Label hint="Square grid size — number of rows and columns">grid</Label>
        <ToggleGroup
          type="single"
          value={String(gridSize)}
          onValueChange={(v) => { if (v) setGridSize(Number(v)); }}
          disabled={running}
          className="gap-0.5 rounded-lg border border-border/40 bg-secondary/30 p-0.5"
        >
          {["1", "2", "3", "4"].map((n) => (
            <ToggleGroupItem
              key={n}
              value={n}
              className="h-6 w-7 rounded-md text-[11px]"
              aria-label={`${n}×${n} grid`}
            >
              {n}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </ControlGroup>

      <Separator />

      {/* Points slider */}
      <ControlGroup>
        <Label hint="Points per dataset. Default 142, matching the original paper.">pts</Label>
        <Slider
          min={50}
          max={500}
          step={10}
          value={[nPoints]}
          onValueChange={([v]) => setNPoints(v)}
          disabled={running}
          className="w-24"
        />
        <span className="text-xs font-mono tabular-nums text-foreground w-8">{nPoints}</span>
      </ControlGroup>

      <Separator />

      {/* Algorithm */}
      <ControlGroup>
        <Label hint="Algorithm for moving points toward the target shape">algo</Label>
        <ToggleGroup
          type="single"
          value={algorithm}
          onValueChange={(v) => { if (v) setAlgorithm(v as typeof algorithm); }}
          disabled={running}
          className="gap-0.5 rounded-lg border border-border/40 bg-secondary/30 p-0.5"
        >
          <ToggleGroupItem value="sa" className="h-6 rounded-md px-2.5 text-[11px]" aria-label="Simulated Annealing">Annealing</ToggleGroupItem>
          <ToggleGroupItem value="langevin" className="h-6 rounded-md px-2.5 text-[11px]" aria-label="Langevin Dynamics">Langevin</ToggleGroupItem>
          <ToggleGroupItem value="momentum" className="h-6 rounded-md px-2.5 text-[11px]" aria-label="Momentum">Momentum</ToggleGroupItem>
        </ToggleGroup>
      </ControlGroup>

      {/* Progress */}
      {(running || done) && (
        <>
          <Separator />
          <div className="flex items-center gap-2">
            {running && (
              <>
                <div className="h-1 w-24 rounded-full bg-secondary overflow-hidden">
                  <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progress * 100}%` }} />
                </div>
                <span className="text-[10px] text-muted-foreground tabular-nums font-mono">{step.toLocaleString()}</span>
              </>
            )}
            {done && (
              <span className="text-[10px] text-muted-foreground tabular-nums font-mono">{step.toLocaleString()} steps</span>
            )}
          </div>
        </>
      )}

      {/* Actions — pushed right */}
      <div className="flex items-center gap-1.5 ml-auto">
        <Hint text="Deal new random shapes into all cells">
          <Button variant="ghost" size="sm" onClick={randomizeShapes} disabled={running} className="text-xs h-7 gap-1" aria-label="Randomize shapes">
            <Shuffle className="h-3 w-3" />
            Randomize
          </Button>
        </Hint>
        {running ? (
          <Button variant="outline" size="sm" onClick={onStop} className="text-xs h-7 rounded-lg">Stop</Button>
        ) : (
          <Hint text="Run the simulation (Enter)">
            <Button size="sm" onClick={onSimulate} className="text-xs h-7 rounded-lg px-4 shadow-sm">Simulate</Button>
          </Hint>
        )}
      </div>
    </div>
  );
}

function ControlGroup({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center gap-2">{children}</div>;
}

function Separator() {
  return <div className="h-5 w-px bg-border/60" />;
}

function Label({ hint, children }: { hint: string; children: React.ReactNode }) {
  return (
    <Hint text={hint}>
      <span className="text-[9px] uppercase tracking-widest text-muted-foreground/50 cursor-help select-none">{children}</span>
    </Hint>
  );
}

function Hint({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side="bottom">{text}</TooltipContent>
    </Tooltip>
  );
}
