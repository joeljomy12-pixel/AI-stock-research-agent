"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { searchStocks } from "@/lib/api";
import { SearchResult } from "@/types";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Loading } from "@/components/ui/Loading";
import { clsx } from "clsx";

const POPULAR_TICKERS = [
  { symbol: "NVDA", name: "NVIDIA Corporation" },
  { symbol: "AAPL", name: "Apple Inc." },
  { symbol: "TSLA", name: "Tesla Inc." },
  { symbol: "MSFT", name: "Microsoft Corporation" },
  { symbol: "GOOGL", name: "Alphabet Inc." },
  { symbol: "AMZN", name: "Amazon.com Inc." },
  { symbol: "META", name: "Meta Platforms Inc." },
  { symbol: "AMD", name: "Advanced Micro Devices" },
  { symbol: "JPM", name: "JPMorgan Chase & Co." },
  { symbol: "V", name: "Visa Inc." },
];

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);

  // Search on input change
  useEffect(() => {
    if (query.length >= 1) {
      setIsSearching(true);
      searchStocks(query)
        .then((data) => {
          setResults(data);
          setShowResults(true);
          setSelectedIndex(-1);
        })
        .catch(() => {
          setResults([]);
          setShowResults(true);
        })
        .finally(() => setIsSearching(false));
    } else {
      setResults([]);
      setShowResults(false);
    }
  }, [query]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults || results.length === 0) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, -1));
        break;
      case "Enter":
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSelect(results[selectedIndex]);
        } else if (query.trim()) {
          router.push(`/stock/${query.trim().toUpperCase()}`);
        }
        break;
      case "Escape":
        setShowResults(false);
        break;
    }
  };

  const handleSelect = (result: SearchResult) => {
    setQuery(result.symbol);
    setShowResults(false);
    router.push(`/stock/${result.symbol}`);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/stock/${query.trim().toUpperCase()}`);
    }
  };

  const patternUrl = `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`;

  return (
    <div className="min-h-screen bg-terminal-bg text-terminal-text">
      {/* Background Pattern */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-terminal-panel/50 via-terminal-bg to-terminal-bg" />
      <div className="fixed inset-0" style={{ backgroundImage: patternUrl, opacity: 0.5 }} />

      <main className="relative min-h-screen flex items-center justify-center px-4">
        <div className="w-full max-w-2xl">
          {/* Logo & Title */}
          <div className="text-center mb-12 animate-fade-in">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-terminal-panel border border-terminal-border mb-6">
              <svg className="w-12 h-12 text-terminal-accent" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-terminal-text mb-3">
              StockIntel
            </h1>
            <p className="text-lg text-terminal-textMuted max-w-md mx-auto">
              AI-powered stock intelligence platform. Understand any company in seconds — not hours.
            </p>
          </div>

          {/* Search Bar */}
          <Card className="mb-8 animate-slide-up">
            <form onSubmit={handleSubmit} className="relative">
              <div className="relative">
                <svg
                  className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-terminal-textMuted"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onFocus={() => setShowResults(query.length >= 1)}
                  onBlur={(e) => setTimeout(() => setShowResults(false), 200)}
                  onKeyDown={handleKeyDown}
                  placeholder="Enter ticker (e.g., NVDA, AAPL, TSLA)..."
                  className="w-full bg-terminal-bg border border-terminal-border rounded-lg px-12 py-4 text-lg text-terminal-text placeholder-terminal-textMuted focus:outline-none focus:ring-2 focus:ring-terminal-accent focus:border-transparent"
                  autoComplete="off"
                  autoFocus
                />
                {isSearching && (
                  <div className="absolute right-4 top-1/2 -translate-y-1/2">
                    <Loading size="sm" />
                  </div>
                )}
              </div>
            </form>

            {/* Dropdown Results */}
            {showResults && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-terminal-panel border border-terminal-border rounded-lg shadow-xl z-50 overflow-hidden animate-slide-down">
                {results.length > 0 ? (
                  <ul className="max-h-60 overflow-y-auto">
                    {results.map((result, i) => (
                      <li
                        key={result.symbol}
                        onClick={() => handleSelect(result)}
                        onMouseEnter={() => setSelectedIndex(i)}
                        className={clsx(
                          "px-4 py-3 hover:bg-terminal-accent/10 cursor-pointer transition-colors border-b border-terminal-border last:border-0",
                          selectedIndex === i && "bg-terminal-accent/10"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-mono font-semibold text-terminal-text">{result.symbol}</p>
                            <p className="text-sm text-terminal-textMuted truncate max-w-xs">{result.name}</p>
                          </div>
                          <span className="text-xs text-terminal-textMuted px-2 py-0.5 bg-terminal-bg rounded">
                            {result.exchange}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : query.length >= 1 && (
                  <div className="px-4 py-6 text-center text-terminal-textMuted">
                    No results found for "{query}"
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* Popular Tickers */}
          <div className="animate-fade-in">
            <p className="text-sm text-terminal-textMuted text-center mb-4">Popular tickers</p>
            <div className="flex flex-wrap justify-center gap-2">
              {POPULAR_TICKERS.map((ticker) => (
                <button
                  key={ticker.symbol}
                  onClick={() => router.push(`/stock/${ticker.symbol}`)}
                  className="px-4 py-2 bg-terminal-panel border border-terminal-border rounded-lg text-sm font-medium text-terminal-text hover:bg-terminal-accent/10 hover:border-terminal-accent/50 hover:text-terminal-accent transition-all"
                >
                  {ticker.symbol}
                </button>
              ))}
            </div>
          </div>

          {/* Feature Highlights */}
          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 animate-fade-in">
            <FeatureCard
              icon="🤖"
              title="AI Research Agent"
              description="Deep analysis of financials, earnings, news, and SEC filings with citations"
            />
            <FeatureCard
              icon="🔍"
              title="Why It Moved"
              description="Anomaly detection + news correlation to explain unusual price movements"
            />
            <FeatureCard
              icon="🏥"
              title="Stock Doctor"
              description="6-factor health scoring from quantitative metrics — no LLM hallucination"
            />
          </div>

          {/* Disclaimer */}
          <div className="mt-12 text-center">
            <p className="text-xs text-terminal-textMuted max-w-md mx-auto">
              <strong>Disclaimer:</strong> Educational/research tool only. Not financial advice.
              Data from Yahoo Finance. AI analysis may contain errors. Always verify independently.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <Card className="text-center hover:border-terminal-accent/50 transition-colors">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-terminal-text mb-2">{title}</h3>
      <p className="text-sm text-terminal-textMuted">{description}</p>
    </Card>
  );
}