"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

interface ThemeContextValue {
  theme: string;
  setTheme: (theme: string) => void;
  resolvedTheme: string;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const STORAGE_KEY = "theme";
const DEFAULT_THEME = "dark";

/**
 * Lightweight theme provider that replaces next-themes to avoid the
 * React 19 "script tag inside component" console warning.
 *
 * FOUC prevention is handled by the inline <Script> in layout.tsx.
 */
export function ThemeProviderWrapper({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState(DEFAULT_THEME);

  // Sync from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored && (stored === "light" || stored === "dark")) {
        setThemeState(stored);
      }
    } catch {
      // localStorage unavailable
    }
  }, []);

  const setTheme = useCallback((next: string) => {
    setThemeState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // localStorage unavailable
    }
    // Apply to DOM immediately
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(next);
    root.style.colorScheme = next;
  }, []);

  // Listen for storage changes from other tabs
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        setThemeState(e.newValue);
        const root = document.documentElement;
        root.classList.remove("light", "dark");
        root.classList.add(e.newValue);
        root.style.colorScheme = e.newValue;
      }
    };
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, resolvedTheme: theme }),
    [theme, setTheme],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

/**
 * Drop-in replacement for next-themes' useTheme hook.
 */
export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    return { theme: DEFAULT_THEME, setTheme: () => {}, resolvedTheme: DEFAULT_THEME };
  }
  return ctx;
}
