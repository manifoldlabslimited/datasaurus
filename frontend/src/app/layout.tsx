import type { Metadata } from "next";
import Script from "next/script";
import { ThemeProviderWrapper } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

export const metadata: Metadata = {
  title: "Datasaurus",
  description: "Same stats, different shapes — animated simulated annealing.",
};

// Inline script to set the theme class before first paint (avoids FOUC).
// Runs before React hydrates, so no flash of wrong theme.
const themeScript = `
(function(){
  try {
    var t = localStorage.getItem("theme") || "dark";
    document.documentElement.classList.add(t);
    document.documentElement.style.colorScheme = t;
  } catch(e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <Script id="theme-init" strategy="beforeInteractive">{themeScript}</Script>
      </head>
      <body className="h-full">
        <ThemeProviderWrapper>
          <TooltipProvider delayDuration={300}>
            {children}
          </TooltipProvider>
        </ThemeProviderWrapper>
      </body>
    </html>
  );
}
