import type { Metadata } from "next";
import { ThemeProvider } from "@/lib/theme";
import "./globals.css";

export const metadata: Metadata = {
  title: "Datasaurus",
  description: "Same stats, different shapes — animated simulated annealing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // dark class set statically so SSR always renders dark (our default).
    // ThemeProvider overrides it on mount if localStorage says "light".
    <html lang="en" className="h-full dark">
      <body className="h-full">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}

