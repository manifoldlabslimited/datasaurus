"use client";

import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogTrigger, DialogContent, DialogTitle } from "@/components/ui/dialog";

export function InfoPanel() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="About Datasaurus"
        >
          <Info className="h-3.5 w-3.5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogTitle className="sr-only">About Datasaurus</DialogTitle>
        <div className="space-y-5 px-6 py-5">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Same stats. Different shapes.
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              Every dataset shares the same mean, standard deviation,
              and correlation — to two decimal places. The shapes look nothing
              alike. That&apos;s the point: summary statistics hide the structure
              of your data.
            </p>
          </div>

          <hr className="border-border" />

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Two modes
            </h3>
            <div className="mt-2 space-y-2 text-xs leading-relaxed text-muted-foreground">
              <p>
                <span className="font-medium text-foreground">Playground</span> — pick shapes, tweak points and algorithms, run up to 16 cells side by side.
              </p>
              <p>
                <span className="font-medium text-foreground">Morph</span> — sit back and watch 10,000 points flow through 20 shapes automatically. Same stats, every frame.
              </p>
            </div>
          </div>

          <hr className="border-border" />

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              The invariant
            </h3>
            <div className="mt-2 grid grid-cols-5 gap-1 text-center font-mono text-[11px]">
              <StatBox label="x̄" value="54.26" />
              <StatBox label="ȳ" value="47.83" />
              <StatBox label="σx" value="16.76" />
              <StatBox label="σy" value="26.93" />
              <StatBox label="r" value="−0.06" />
            </div>
          </div>

          <hr className="border-border" />

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Keyboard
            </h3>
            <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
              <span><kbd className="rounded bg-secondary/60 px-1.5 py-0.5 text-[10px] font-mono">Enter</kbd> Simulate</span>
              <span><kbd className="rounded bg-secondary/60 px-1.5 py-0.5 text-[10px] font-mono">Esc</kbd> Stop</span>
            </div>
          </div>

          <hr className="border-border" />

          <p className="text-[10px] text-muted-foreground/60">
            Based on{" "}
            <a
              href="https://www.autodesk.com/research/publications/same-stats-different-graphs"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-muted-foreground"
            >
              Matejka &amp; Fitzmaurice (CHI 2017)
            </a>
            . Original Datasaurus by Alberto Cairo.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded bg-secondary/50 px-1.5 py-1.5">
      <div className="text-[9px] text-muted-foreground/60">{label}</div>
      <div className="text-xs text-foreground">{value}</div>
    </div>
  );
}
