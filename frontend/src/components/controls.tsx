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
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-border bg-card px-4 py-2.5">

      {/* Grid size */}
      <ControlGroup>
        <Label hint="Number of rows in the grid">rows</Label>
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
        <span className="text-muted-foreground/30 text-xs">×</span>
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
        <Label hint="Number of columns in the grid">cols</Label>
      </ControlGroup>

      <Separator />

      {/* Points slider */}
      <ControlGroup>
        <Label hint="Points per dataset. Default 142, matching the original paper. More points = sharper shapes, slower simulation.">
          pts
        </Label>
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
          className="gap-0.5 rounded-md border border-border p-0.5"
        >
          <ToggleGroupItem value="sa" className="h-6 rounded px-2 text-[11px]" aria-label="Simulated Annealing — blind random walk. The original method from the paper.">SA</ToggleGroupItem>
          <ToggleGroupItem value="langevin" className="h-6 rounded px-2 text-[11px]" aria-label="Langevin Dynamics — points are nudged toward the shape boundary with thermal noise.">Langevin</ToggleGroupItem>
          <ToggleGroupItem value="momentum" className="h-6 rounded px-2 text-[11px]" aria-label="Momentum — points carry velocity that accumulates toward the shape. Overshoots and settles.">Momentum</ToggleGroupItem>
        </ToggleGroup>
      </ControlGroup>

      {/* Progress / status */}
      {(running || done) && (
        <>
          <Separator />
          <div className="flex items-center gap-2">
            {running && (
              <>
                <div className="h-1 w-24 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${progress * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-muted-foreground tabular-nums font-mono">
                  {step.toLocaleString()}
                </span>
              </>
            )}
            {done && (
              <span className="text-[10px] text-muted-foreground tabular-nums font-mono">
                {step.toLocaleString()} steps
              </span>
            )}
          </div>
        </>
      )}

      {/* Actions */}
      <div className="flex items-center gap-1.5 ml-auto">
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
          <Hint text="Run the simulation with the current shape selections (Enter)">
            <Button size="sm" onClick={onSimulate} className="text-xs h-7">Simulate</Button>
          </Hint>
        )}
        <div className="ml-1 flex items-center gap-0.5">
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
    </div>
  );
}

/** Visual group for related controls. */
function ControlGroup({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      {children}
    </div>
  );
}

/** Thin vertical separator between control groups. */
function Separator() {
  return <div className="h-5 w-px bg-border/60" />;
}

/** Label with tooltip on hover. */
function Label({ hint, children }: { hint: string; children: React.ReactNode }) {
  return (
    <Hint text={hint}>
      <span className="text-[9px] uppercase tracking-widest text-muted-foreground/50 cursor-help select-none">
        {children}
      </span>
    </Hint>
  );
}

/** Tooltip wrapper. */
function Hint({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side="bottom">{text}</TooltipContent>
    </Tooltip>
  );
}
