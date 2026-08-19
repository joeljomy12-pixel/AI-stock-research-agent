"use client";

import { Card } from "@/components/ui/Card";
import { HealthGauge, ScoreCard } from "@/components/charts/HealthGauge";
import { Loading, SkeletonCard } from "@/components/ui/Loading";
import { useStockOverview } from "@/hooks/useStockData";
import { InlineDisclaimer } from "@/components/dashboard/Disclaimer";
import { clsx } from "clsx";
import { format } from "date-fns";

export function StockDoctorTab({ symbol }: { symbol: string }) {
  const { health, isLoading, isError, error } = useStockOverview(symbol);

  if (isLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <SkeletonCard />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 text-bear-500">
        <p>Failed to load health score: {error?.message || "Unknown error"}</p>
      </div>
    );
  }

  if (!health) return null;

  const scoreColors: Record<string, "green" | "yellow" | "red"> = {
    green: "green",
    yellow: "yellow",
    red: "red",
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Overall Score */}
      <Card>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div className="flex items-center gap-6">
            <HealthGauge
              score={health.overall_score}
              label="Overall Health"
              color={health.overall_color}
              size={140}
              showLabel={false}
            />
            <div>
              <h2 className="text-3xl font-bold text-terminal-text">
                {health.overall_score}/100
              </h2>
              <p className={clsx("text-lg font-medium mt-1", health.overall_color === "green" && "text-bull-500", health.overall_color === "yellow" && "text-yellow-500", health.overall_color === "red" && "text-bear-500")}>
                {health.overall_label}
              </p>
              <p className="text-sm text-terminal-textMuted mt-2">
                Percentile: Top {health.percentile_rank}% of stocks •{' '}
                Updated {format(new Date(health.calculated_at), "MMM d, yyyy HH:mm")}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-terminal-textMuted">Calculated from</p>
            <p className="font-mono text-lg text-terminal-accent">6 Quantitative Factors</p>
            <p className="text-xs text-terminal-textMuted mt-1">No LLM Hallucination</p>
          </div>
        </div>
      </Card>

      {/* Sub-scores Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {health.sub_scores.map((sub) => (
          <ScoreCard
            key={sub.name}
            score={sub.score}
            label={sub.name}
            color={sub.color}
            explanation={sub.explanation}
            metrics={sub.metrics}
          />
        ))}
      </div>

      {/* Detailed Breakdown */}
      <Card>
        <h3 className="text-lg font-semibold text-terminal-text mb-4">How Scores Are Calculated</h3>
        <div className="space-y-4 text-sm">
          <div className="bg-terminal-bg border border-terminal-border rounded-lg p-4">
            <h4 className="font-semibold text-terminal-text mb-2">Methodology</h4>
            <ul className="space-y-2 text-terminal-textMuted">
              <li>• <strong>Financial Health (30%):</strong> Debt-to-equity, current ratio, FCF, margins, ROE</li>
              <li>• <strong>Growth (20%):</strong> Revenue YoY, EPS YoY, composite growth metrics</li>
              <li>• <strong>Momentum (15%):</strong> Price returns, volatility, 52-week range position</li>
              <li>• <strong>Valuation (15%):</strong> P/E, PEG, EV/EBITDA, P/S ratios</li>
              <li>• <strong>Market Sentiment (10%):</strong> News sentiment analysis (VADER/FinBERT)</li>
              <li>• <strong>Risk (10%):</strong> Beta, short interest, price volatility proxy</li>
            </ul>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {health.sub_scores.map((sub) => (
              <div
                key={sub.name}
                className="bg-terminal-bg border border-terminal-border rounded-lg p-4"
              >
                <h4 className="font-semibold text-terminal-text mb-2 flex items-center gap-2">
                  <span
                    className={clsx(
                      "w-2 h-2 rounded-full",
                      sub.color === "green" && "bg-bull-500",
                      sub.color === "yellow" && "bg-yellow-500",
                      sub.color === "red" && "bg-bear-500"
                    )}
                  />
                  {sub.name} — {sub.score}/100
                </h4>
                <p className="text-terminal-textMuted text-xs">{sub.explanation}</p>
                {Object.keys(sub.metrics).length > 0 && (
                  <div className="mt-2 space-y-1">
                    {Object.entries(sub.metrics).map(([key, value]) => (
                      <div
                        key={key}
                        className="text-xs text-terminal-textMuted flex justify-between"
                      >
                        <span>{key.replace(/_/g, " ")}:</span>
                        <span className="font-mono text-terminal-text">
                          {typeof value === "number" ? value.toFixed(2) : value}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Interpretation Guide */}
      <Card variant="outlined">
        <h4 className="text-sm font-semibold text-terminal-textMuted mb-3">Score Interpretation Guide</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="p-3 bg-bull-900/20 border border-bull-800 rounded">
            <p className="font-semibold text-bull-500">80-100: Excellent</p>
            <p className="text-terminal-textMuted text-xs mt-1">Strong fundamentals, favorable metrics</p>
          </div>
          <div className="p-3 bg-bull-900/10 border border-bull-700 rounded">
            <p className="font-semibold text-bull-400">65-79: Good</p>
            <p className="text-terminal-textMuted text-xs mt-1">Above average, minor concerns</p>
          </div>
          <div className="p-3 bg-yellow-900/20 border border-yellow-800 rounded">
            <p className="font-semibold text-yellow-500">50-64: Fair</p>
            <p className="text-terminal-textMuted text-xs mt-1">Mixed signals, monitor closely</p>
          </div>
          <div className="p-3 bg-bear-900/20 border border-bear-800 rounded">
            <p className="font-semibold text-bear-500">Below 50: Weak</p>
            <p className="text-terminal-textMuted text-xs mt-1">Significant concerns, high risk</p>
          </div>
        </div>
      </Card>

      <InlineDisclaimer className="mt-4" />
    </div>
  );
}