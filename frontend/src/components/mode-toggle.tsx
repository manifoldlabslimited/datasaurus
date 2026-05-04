"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

/**
 * Two-mode toggle in the top bar.
 * Highlights the active mode based on the current route.
 */
export function ModeToggle() {
  const pathname = usePathname();
  const isMorph = pathname === "/loop";

  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-border/40 bg-secondary/30 p-0.5 text-[11px]">
      <Link
        href="/"
        aria-label="Playground mode"
        className={cn(
          "rounded-md px-3 py-0.5 font-medium transition-all",
          !isMorph
            ? "bg-primary text-primary-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        Playground
      </Link>
      <Link
        href="/loop"
        aria-label="Morph mode"
        className={cn(
          "rounded-md px-3 py-0.5 font-medium transition-all",
          isMorph
            ? "bg-primary text-primary-foreground shadow-sm"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        Morph
      </Link>
    </div>
  );
}
