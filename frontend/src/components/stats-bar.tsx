"use client";

import { useEffect, useState } from "react";
import { useTheme } from "@/components/theme-provider";
import { ModeToggle } from "@/components/mode-toggle";
import { InfoPanel } from "@/components/info-panel";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/cn";
import { TARGET_STATS } from "@/lib/constants";
import type { CellStats } from "@/lib/types";

interface Props {
  stats?: CellStats | null;
}

/**
 * Shared top bar: brand + mode toggle + stats + theme/info.
 * Stats are the invariant — always visible, always prominent.
 */
export function StatsBar({ stats: liveStats }: Props) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const stats = liveStats ?? TARGET_STATS;
  const dimmed = !liveStats;

  return (
    <div className="relative flex h-10 items-center border-b border-border/40 bg-card/80 px-4 text-[11px] backdrop-blur-sm">
      {/* Left: brand + stats */}
      <div className="flex items-center gap-4">
        <span className="text-primary font-semibold tracking-wider uppercase text-[10px]">
          Datasaurus
        </span>
        <div className={cn(
          "flex items-center gap-4",
          dimmed ? "opacity-30" : "text-muted-foreground",
        )}>
          <StatItem label="x̄" value={stats.mean_x.toFixed(2)} />
          <StatItem label="ȳ" value={stats.mean_y.toFixed(2)} />
          <StatItem label="σx" value={stats.std_x.toFixed(2)} />
          <StatItem label="σy" value={stats.std_y.toFixed(2)} />
          <StatItem label="r" value={stats.correlation.toFixed(2)} />
        </div>
      </div>

      {/* Center: mode toggle — absolutely centered */}
      <div className="absolute left-1/2 -translate-x-1/2">
        <ModeToggle />
      </div>

      {/* Right: theme + info */}
      <div className="flex items-center gap-1 ml-auto">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Toggle theme"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              {mounted && (theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />)}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Switch theme</TooltipContent>
        </Tooltip>
        <InfoPanel />
      </div>
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <span>
      <span className="opacity-60 mr-1">{label}</span>
      <span className="text-foreground font-mono">{value}</span>
    </span>
  );
}
