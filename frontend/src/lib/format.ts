/** Convert snake_case shape names to Title Case for display. */
export function formatShapeName(name: string): string {
  return name
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
