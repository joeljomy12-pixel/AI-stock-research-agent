"use client";

import { Card } from "@/components/ui/Card";
import { Loading, SkeletonCard } from "@/components/ui/Loading";
import { useStockOverview } from "@/hooks/useStockData";
import { clsx } from "clsx";
import { format } from "date-fns";

const categoryStyles = {
  high_confidence: "bg-bull-900/30 border-bull-800 text-bull-400",
  evidence: "bg-blue-900/30 border-blue-800 text-blue-400",
  correlation: "bg-yellow-900/30 border-yellow-800 text-yellow-400",
  possible: "bg-terminal-border/50 border-terminal-border text-terminal-textMuted",
};

const categoryLabels = {
  high_confidence: "High Confidence",
  evidence: "Direct Evidence",
  correlation: "Correlation",
  possible: "Possible",
};

export function WhyItMovedTab({ symbol }: { symbol: string }) {
  const { movement, isLoading, isError, error } = useStockOverview(symbol);

  if (isLoading) {
    return (
      <div className="space-y-4 animate-fade-in">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 text-bear-500">
        <p>Failed to load movement analysis: {error?.message || "Unknown error"}</p>
      </div>
    );
  }

  if (!movement) return null;

  const isPositive = movement.price_change_percent > 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Summary Header */}
      <Card className={clsx("border-l-4", isPositive ? "border-bull-500" : "border-bear-500")}>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h3 className="text-xl font-semibold text-terminal-text">
              Why Did {symbol.toUpperCase()} Move?
            </h3>
            <p className="text-sm text-terminal-textMuted mt-1">
              {format(new Date(movement.analyzed_at), "MMMM d, yyyy")} •
              {movement.price_change_percent >= 0 ? "▲" : "▼"}
              {Math.abs(movement.price_change_percent).toFixed(2)}% •
              Vol: {movement.volume_ratio.toFixed(1)}x avg
            </p>
          </div>
          <div className={clsx("flex items-center gap-3", isPositive ? "text-bull-500" : "text-bear-500")}>
            <div className="text-right">
              <p className="text-2xl font-mono font-bold">
                {movement.price_change_percent >= 0 ? "+" : ""}{movement.price_change_percent.toFixed(2)}%
              </p>
              <p className="text-xs text-terminal-textMuted">
                ${movement.price_change >= 0 ? "+" : ""}{movement.price_change.toFixed(2)}
              </p>
            </div>
            {movement.is_anomaly && (
              <div className="px-3 py-1 bg-terminal-warning/20 border border-terminal-warning rounded-full text-xs font-medium text-terminal-warning">
                ⚠ Unusual Movement Detected
              </div>
            )}
          </div>
        </div>
        <p className="mt-4 text-terminal-textMuted">{movement.summary}</p>
      </Card>

      {/* Drivers */}
      <Card>
        <h3 className="text-lg font-semibold text-terminal-text mb-4">Likely Drivers</h3>

        {movement.drivers.length === 0 ? (
          <p className="text-terminal-textMuted text-center py-8">No specific drivers identified</p>
        ) : (
          <div className="space-y-4">
            {movement.drivers.map((driver, i) => (
              <div
                key={i}
                className={clsx(
                  "rounded-lg p-4 border transition-all hover:border-terminal-accent/50",
                  categoryStyles[driver.category]
                )}
              >
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-semibold text-terminal-text">{driver.driver}</h4>
                      <span
                        className={clsx(
                          "px-2 py-0.5 rounded-full text-xs font-medium uppercase",
                          categoryStyles[driver.category]
                        )}
                      >
                        {categoryLabels[driver.category]}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-xs font-mono font-medium bg-terminal-bg border border-terminal-border">
                        {driver.confidence}% Confidence
                      </span>
                    </div>
                    <p className="text-sm text-terminal-textMuted">{driver.description}</p>
                    {driver.evidence.length > 0 && (
                      <div className="mt-3 space-y-1">
                        {driver.evidence.map((ev, j) => (
                          <div
                            key={j}
                            className="text-xs text-terminal-textMuted pl-3 border-l-2 border-terminal-border/50"
                          >
                            📰 {ev}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-center">
                    <div className="w-16 h-16 rounded-full bg-terminal-bg border border-terminal-border flex items-center justify-center">
                      <span className="text-3xl font-mono font-bold">{driver.confidence}%</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Confidence Legend */}
      <Card variant="outlined">
        <h4 className="text-sm font-semibold text-terminal-textMuted mb-3">Confidence Categories</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="flex items-center gap-2 p-2 bg-bull-900/30 border border-bull-800 rounded">
            <div className="w-3 h-3 rounded-full bg-bull-500" />
            <span className="text-bull-400">High Confidence</span>
          </div>
          <div className="flex items-center gap-2 p-2 bg-blue-900/30 border border-blue-800 rounded">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-blue-400">Direct Evidence</span>
          </div>
          <div className="flex items-center gap-2 p-2 bg-yellow-900/30 border border-yellow-800 rounded">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-yellow-400">Correlation</span>
          </div>
          <div className="flex items-center gap-2 p-2 bg-terminal-border/50 border border-terminal-border rounded">
            <div className="w-3 h-3 rounded-full bg-terminal-textMuted" />
            <span className="text-terminal-textMuted">Possible</span>
          </div>
        </div>
        <p className="mt-3 text-xs text-terminal-textMuted">
          <strong>High Confidence:</strong> Strong evidence directly linking event to move.<br />
          <strong>Direct Evidence:</strong> Specific news/filings with clear causal link.<br />
          <strong>Correlation:</strong> Sector/macro moves correlated but not proven causal.<br />
          <strong>Possible:</strong> Plausible but insufficient evidence.
        </p>
      </Card>
    </div>
  );
}