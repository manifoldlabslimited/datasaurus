"use client";

import { useEffect, useState, useCallback } from "react";

import { Button } from "@/components/ui/button";
import { ScatterCanvas } from "@/components/scatter-canvas";
import { StatsBar } from "@/components/stats-bar";
import { ErrorBanner } from "@/components/error-banner";
import { useLoopSSE } from "@/hooks/useLoopSSE";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { AnimProvider } from "@/lib/anim-context";
import { API_BASE } from "@/lib/api";
import { LOOP_SHAPES } from "@/lib/constants";
import { formatShapeName } from "@/lib/format";

export default function MorphPage() {
  const {
    start, stop, points, stats, shape, step, total,
    run, error, clearError, frameIntervalRef,
  } = useLoopSSE();

  const [availableShapes, setAvailableShapes] = useState<string[]>([...LOOP_SHAPES]);

  const running = run === "running";
  const progress = total > 0 ? step / total : 0;

  useEffect(() => {
    fetch(`${API_BASE}/shapes`)
      .then((r) => r.json())
      .then((data: string[]) => {
        const valid = LOOP_SHAPES.filter((s) => data.includes(s));
        if (valid.length > 0) setAvailableShapes(valid);
      })
      .catch((err) => {
        console.warn("[morph] Failed to fetch shapes:", err);
      });
  }, []);

  const handleStart = useCallback(() => start(availableShapes), [start, availableShapes]);

  useKeyboardShortcuts(handleStart, stop, running);

  return (
    <AnimProvider value={frameIntervalRef}>
      <div className="flex h-screen flex-col overflow-hidden">
        <StatsBar stats={stats} />

        {/* Error banner */}
        {error && (
          <ErrorBanner message={error} onDismiss={clearError} />
        )}

        {/* Full-bleed scatter plot with overlaid controls */}
        <div className="relative min-h-0 flex-1">
          <ScatterCanvas points={points} />

          {/* Shape label with progress ring — top left overlay */}
          {shape && (
            <div className="absolute left-4 top-3 flex items-center gap-2 rounded-lg bg-card/70 px-2.5 py-1 backdrop-blur-sm">
              <ProgressRing progress={progress} size={18} />
              <span className="text-xs font-medium text-muted-foreground">
                {formatShapeName(shape)}
              </span>
            </div>
          )}

          {/* Step counter — top right overlay */}
          {running && (
            <div className="absolute right-4 top-3 rounded-lg bg-card/70 px-2.5 py-1 backdrop-blur-sm">
              <span className="text-[10px] text-muted-foreground tabular-nums font-mono">{step.toLocaleString()}</span>
            </div>
          )}

          {/* Simulate / Stop overlay */}
          {run === "idle" ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <Button
                size="lg"
                onClick={() => start(availableShapes)}
                className="text-sm px-10 py-2.5 rounded-xl shadow-lg shadow-primary/20"
              >
                Simulate
              </Button>
            </div>
          ) : running ? (
            <div className="absolute bottom-4 right-4">
              <Button variant="outline" size="sm" onClick={stop} className="text-xs rounded-lg bg-card/70 backdrop-blur-sm">
                Stop
              </Button>
            </div>
          ) : (
            <div className="absolute bottom-4 right-4">
              <Button size="sm" onClick={() => start(availableShapes)} className="text-xs rounded-lg shadow-sm bg-card/70 backdrop-blur-sm border border-primary/30 text-primary hover:bg-primary hover:text-primary-foreground">
                Simulate
              </Button>
            </div>
          )}
        </div>
      </div>
    </AnimProvider>
  );
}


/** Tiny SVG ring that fills clockwise as progress goes 0→1. */
function ProgressRing({ progress, size = 18 }: { progress: number; size?: number }) {
  const stroke = 2;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - Math.min(1, Math.max(0, progress)));

  return (
    <svg width={size} height={size} className="shrink-0 -rotate-90">
      {/* Track */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        className="text-border/40"
      />
      {/* Fill */}
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="currentColor"
        strokeWidth={stroke}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="text-primary transition-[stroke-dashoffset] duration-300"
      />
    </svg>
  );
}
