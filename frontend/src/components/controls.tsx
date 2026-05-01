"use client";

import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useGridStore } from "@/store/grid";
import { useTheme } from "@/lib/theme";
import { Sun, Moon, Shuffle } from "lucide-react";
import { InfoPanel } from "@/components/info-panel";

interface Props {
  onSimulate: () => void;
  onStop: () => void;
}

const GRID_SIZES = ["1", "2", "3", "4", "5"];

export function Controls({ onSimulate, onStop }: Props) {
  const { rows, cols, nPoints, algorithm, run, step, total, setRows, setCols, setNPoints, setAlgorithm, randomizeShapes } = useGridStore();
  const { theme, setTheme } = useTheme();

  const progress = total > 0 ? step / total : 0;
  const running = run === "running";
  const done = run === "done";

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-border bg-card px-4 py-2.5">

      {/* Grid size */}
      <div className="flex items-center gap-2">
        <Hint text="Number of rows in the grid">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wide cursor-help">rows</span>
        </Hint>
        <Select
          value={String(rows)}
          onValueChange={(v) => setRows(Number(v))}
          disabled={running}
        >
          <SelectTrigger className="h-7 w-14 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {GRID_SIZES.map((s) => (
              <SelectItem key={s} value={s} className="text-xs">{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Hint text="Number of columns in the grid">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wide cursor-help">cols</span>
        </Hint>
        <Select
          value={String(cols)}
          onValueChange={(v) => setCols(Number(v))}
          disabled={running}
        >
          <SelectTrigger className="h-7 w-14 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {GRID_SIZES.map((s) => (
              <SelectItem key={s} value={s} className="text-xs">{s}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Points slider */}
      <div className="flex items-center gap-2">
        <Hint text="Points per dataset. Default 142, matching the original paper. More points = sharper shapes, slower simulation.">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wide cursor-help">
            pts
          </span>
        </Hint>
        <Slider
          min={50}
          max={500}
          step={10}
          value={[nPoints]}
          onValueChange={([v]) => setNPoints(v)}
          disabled={running}
          className="w-28"
        />
        <span className="text-xs font-mono tabular-nums w-8">{nPoints}</span>
      </div>

      {/* Algorithm */}
      <div className="flex items-center gap-2">
        <Hint text="Algorithm for moving points toward the target shape">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wide cursor-help">algo</span>
        </Hint>
        <ToggleGroup
          type="single"
          value={algorithm}
          onValueChange={(v) => { if (v) setAlgorithm(v as typeof algorithm); }}
          disabled={running}
          className="gap-0.5"
        >
          <ToggleGroupItem value="sa" className="h-7 px-2 text-xs" aria-label="Simulated Annealing — blind random walk. The original method from the paper.">SA</ToggleGroupItem>
          <ToggleGroupItem value="langevin" className="h-7 px-2 text-xs" aria-label="Langevin Dynamics — points are nudged toward the shape boundary with thermal noise.">Langevin</ToggleGroupItem>
          <ToggleGroupItem value="momentum" className="h-7 px-2 text-xs" aria-label="Momentum — points carry velocity that accumulates toward the shape. Overshoots and settles.">Momentum</ToggleGroupItem>
        </ToggleGroup>
      </div>

      {/* Progress / status */}
      {(running || done) && (
        <div className="flex items-center gap-2">
          {running && (
            <>
              <div className="h-1 w-24 rounded-full bg-secondary overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${progress * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground tabular-nums">
                {step.toLocaleString()}
              </span>
            </>
          )}
          {done && (
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {step.toLocaleString()} steps
            </span>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 ml-auto">
        <Hint text="Deal new random shapes into all cells">
          <Button
            variant="ghost"
            size="sm"
            onClick={randomizeShapes}
            disabled={running}
            className="text-xs h-7 gap-1"
            aria-label="Randomize shapes"
          >
            <Shuffle className="h-3 w-3" />
            Randomize
          </Button>
        </Hint>
        {running ? (
          <Button variant="outline" size="sm" onClick={onStop} className="text-xs h-7">Stop</Button>
        ) : (
          <Hint text="Run the simulation with the current shape selections">
            <Button size="sm" onClick={onSimulate} className="text-xs h-7">Simulate</Button>
          </Hint>
        )}
        <Hint text="Switch between light and dark theme">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Toggle theme"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </Button>
        </Hint>
        <InfoPanel />
      </div>
    </div>
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
