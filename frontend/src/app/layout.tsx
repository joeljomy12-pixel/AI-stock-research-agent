import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "StockIntel — AI Stock Intelligence Platform",
  description: "AI-powered stock research platform with health scoring, movement analysis, and investment thesis generation",
  keywords: ["stocks", "investing", "AI", "research", "financial analysis", "health score"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-terminal-bg text-terminal-text antialiased font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}