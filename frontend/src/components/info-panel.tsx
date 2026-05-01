"use client";

import { Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetTrigger, SheetContent } from "@/components/ui/sheet";

export function InfoPanel() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          aria-label="About Datasaurus"
        >
          <Info className="h-3.5 w-3.5" />
        </Button>
      </SheetTrigger>
      <SheetContent>
        <div className="flex h-full flex-col overflow-y-auto px-5 py-4 text-sm leading-relaxed text-foreground/90">
          <h2 className="mb-4 text-base font-semibold text-foreground">
            About Datasaurus
          </h2>

          <Section title="What am I looking at?">
            Each cell contains 142 points being rearranged into a target
            shape. The catch: five summary statistics — mean x, mean y,
            standard deviation x, standard deviation y, and correlation —
            stay the same across every cell, to two decimal places.
            A heart and a dinosaur are statistically identical.
          </Section>

          <Section title="Why does this matter?">
            Summary statistics compress a dataset into a few numbers.
            That compression throws away the shape of the data — where
            points cluster, what patterns they form. Two datasets can
            share the same mean, spread, and correlation while looking
            completely different. If you don&apos;t plot your data, you
            can&apos;t see what&apos;s actually there.
          </Section>

          <Section title="How it works">
            The algorithm starts with random noise that already has the
            right statistics. Then it nudges one point at a time toward
            the target shape. Any move that pushes a statistic outside
            ±0.01 tolerance is rejected. Moves that bring points closer
            to the shape are accepted; moves that don&apos;t are accepted
            with decreasing probability as the system cools.
          </Section>

          <Section title="Controls">
            <ControlItem label="Rows / Cols" desc="Grid size, up to 5×5." />
            <ControlItem label="Pts" desc="Points per dataset (50–500). Default 142, matching the original paper." />
            <ControlItem label="Algo" desc="SA (random walk), Langevin (directed), or Momentum (velocity-based)." />
            <ControlItem label="Shape pickers" desc="Click any cell's dropdown to choose its target shape." />
            <ControlItem label="Randomize" desc="Deal new random shapes into all cells." />
            <ControlItem label="Simulate" desc="Run the algorithm with current shapes." />
            <ControlItem label="Stop" desc="Freeze the simulation where it is." />
          </Section>

          <div className="mt-auto border-t border-border pt-3 text-[10px] text-muted-foreground">
            Based on{" "}
            <a
              href="https://www.autodesk.com/research/publications/same-stats-different-graphs"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-foreground"
            >
              Same Stats, Different Graphs
            </a>{" "}
            by Matejka &amp; Fitzmaurice (CHI 2017).
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      <div className="text-[13px]">{children}</div>
    </div>
  );
}

function ControlItem({ label, desc }: { label: string; desc: string }) {
  return (
    <div className="mt-1.5 flex gap-2">
      <span className="shrink-0 font-mono text-[11px] text-primary">{label}</span>
      <span className="text-[12px] text-muted-foreground">{desc}</span>
    </div>
  );
}
