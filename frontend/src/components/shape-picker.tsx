"use client";

import { useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { useGridStore } from "@/store/grid";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { cn } from "@/lib/cn";

interface Props {
  value: string;
  onChange: (shape: string) => void;
  disabled?: boolean;
}

export function ShapePicker({ value, onChange, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const shapes = useGridStore((s) => s.shapes);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        disabled={disabled}
        className={cn(
          "flex w-full items-center justify-between gap-1 rounded px-2 py-1 text-xs",
          "bg-secondary text-secondary-foreground hover:bg-accent hover:text-accent-foreground",
          "transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
          "disabled:pointer-events-none disabled:opacity-40",
        )}
      >
        <span className="truncate font-mono">{value}</span>
        <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
      </PopoverTrigger>
      <PopoverContent
        className="w-52 p-0"
        align="start"
        side="bottom"
        sideOffset={4}
      >
        <Command>
          <CommandInput placeholder="Search shapes…" className="h-8 text-xs" />
          <CommandList>
            <CommandEmpty className="py-4 text-xs text-muted-foreground">
              No shapes found.
            </CommandEmpty>
            <CommandGroup>
              {shapes.map((shape) => (
                <CommandItem
                  key={shape}
                  value={shape}
                  onSelect={(v) => {
                    onChange(v);
                    setOpen(false);
                  }}
                  className="text-xs"
                >
                  <Check
                    className={cn(
                      "mr-2 h-3 w-3",
                      value === shape ? "opacity-100" : "opacity-0",
                    )}
                  />
                  {shape}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
