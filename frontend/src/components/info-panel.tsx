"use client";

import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogTrigger, DialogContent } from "@/components/ui/dialog";

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
        <div className="space-y-5 px-6 py-5">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Same stats. Different shapes.
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              Every cell in the grid shares the same mean, standard deviation,
              and correlation — to two decimal places. The shapes look nothing
              alike. That&apos;s the point: summary statistics hide the structure
              of your data.
            </p>
          </div>

          <hr className="border-border" />

          <div>
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              The algorithm
            </h3>
            <div className="mt-2 space-y-2 text-xs leading-relaxed text-muted-foreground">
              <Step n="1">
                Start with random points that already have the target statistics.
              </Step>
              <Step n="2">
                Nudge one point at a time toward the target shape.
              </Step>
              <Step n="3">
                Reject any move that changes the statistics by more than ±0.01.
              </Step>
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

function Step({ n, children }: { n: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2.5">
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
        {n}
      </span>
      <span className="pt-0.5">{children}</span>
    </div>
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
