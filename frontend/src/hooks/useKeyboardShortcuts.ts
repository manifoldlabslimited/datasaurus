import { useEffect } from "react";

export function useKeyboardShortcuts(onStart: () => void, onStop: () => void, running: boolean) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      // Don't trigger when focus is on interactive elements (buttons, links, etc.)
      if (e.target instanceof HTMLElement && (e.target.closest("button") || e.target.closest("a"))) return;
      if (e.key === "Enter" && !running) {
        e.preventDefault();
        onStart();
      } else if (e.key === "Escape" && running) {
        e.preventDefault();
        onStop();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onStart, onStop, running]);
}
