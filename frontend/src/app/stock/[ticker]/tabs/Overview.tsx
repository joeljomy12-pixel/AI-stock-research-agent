"use client";

import { useState } from "react";
import { PriceChart } from "@/components/charts/PriceChart";
import { HealthGauge, HealthBar } from "@/components/charts/HealthGauge";
import { KeyMetricsGrid } from "@/components/dashboard/MetricCard";
import { InlineDisclaimer } from "@/components/dashboard/Disclaimer";
import { useStockOverview } from "@/hooks/useStockData";
import { Loading, SkeletonChart, SkeletonCard } from "@/components/ui/Loading";
import { Card } from "@/components/ui/Card";
import { clsx } from "clsx";
import { format } from "date-fns";

export function OverviewTab({ symbol }: { symbol: string }) {
  const [timeframe, setTimeframe] = useState<"1d" | "1wk" | "1mo" | "3mo" | "1y">("1mo");

  const { quote, historical, health, news, movement, isLoading, isError, error } =
    useStockOverview(symbol);

  if (isLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <SkeletonChart height={300} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonCard />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 text-bear-500">
        <p>Failed to load data: {error?.message || "Unknown error"}</p>
      </div>
    );
  }

  if (!quote) return null;

  const isBullish = quote.change_percent > 0;
  const priceColor = isBullish ? "bull" : "bear";

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Price Chart Section */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-4">
          <div>
            <h2 className="text-xl font-semibold text-terminal-text">
              {quote.name} ({quote.symbol})
            </h2>
            <p className="text-sm text-terminal-textMuted">{quote.sector} • {quote.industry}</p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value as any)}
              className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm text-terminal-text focus:outline-none focus:ring-2 focus:ring-terminal-accent"
            >
              <option value="1d">1D</option>
              <option value="1wk">1W</option>
              <option value="1mo">1M</option>
              <option value="3mo">3M</option>
              <option value="1y">1Y</option>
            </select>
          </div>
        </div>
        <PriceChart
          data={historical?.data || []}
          height={300}
          color={priceColor}
        />
        <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
          <span className={clsx("font-mono font-semibold", isBullish ? "text-bull-500" : "text-bear-500")}>
            ${quote.price.toFixed(2)}
          </span>
          <span className={clsx("font-mono", isBullish ? "text-bull-500" : "text-bear-500")}>
            {quote.change >= 0 ? "+" : ""}{quote.change.toFixed(2)} ({quote.change_percent >= 0 ? "+" : ""}{quote.change_percent.toFixed(2)}%)
          </span>
          <span className="text-terminal-textMuted">Vol: {formatNumber(quote.volume)}</span>
          <span className="text-terminal-textMuted">Avg Vol: {formatNumber(quote.avg_volume)}</span>
        </div>
      </Card>

      {/* Health Score & Key Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Health Score Gauge */}
        <Card className="lg:col-span-1">
          <h3 className="text-lg font-semibold text-terminal-text mb-4">AI Health Score</h3>
          {health ? (
            <div className="space-y-4">
              <HealthGauge
                score={health.overall_score}
                label="Overall"
                color={health.overall_color}
                size={140}
              />
              <div className="space-y-3">
                {health.sub_scores.map((sub) => (
                  <HealthBar
                    key={sub.name}
                    score={sub.score}
                    label={sub.name}
                    color={sub.color}
                  />
                ))}
              </div>
              <p className="text-xs text-terminal-textMuted text-center">
                Percentile: Top {health.percentile_rank}% • Updated {format(new Date(health.calculated_at), "HH:mm")}
              </p>
            </div>
          ) : (
            <Loading text="Calculating health score..." />
          )}
        </Card>

        {/* Key Metrics */}
        <Card className="lg:col-span-2">
          <h3 className="text-lg font-semibold text-terminal-text mb-4">Key Metrics</h3>
          <KeyMetricsGrid quote={quote} fundamentals={health?.sub_scores[0]?.metrics} />
        </Card>
      </div>

      {/* Bull/Bear Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card variant="outlined">
          <h4 className="text-sm font-semibold text-bull-500 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-bull-500" />
            Bullish Signals
          </h4>
          <ul className="space-y-2 text-sm text-terminal-textMuted">
            {quote.change_percent > 0 && <li>• Positive price momentum today</li>}
            {health?.sub_scores.find((s) => s.name === "Momentum") && health.sub_scores.find((s) => s.name === "Momentum")!.score > 70 && (
              <li>• Strong momentum score ({health.sub_scores.find((s) => s.name === "Momentum")!.score}/100)</li>
            )}
            {health?.sub_scores.find((s) => s.name === "Growth") && health.sub_scores.find((s) => s.name === "Growth")!.score > 70 && (
              <li>• Solid growth profile ({health.sub_scores.find((s) => s.name === "Growth")!.score}/100)</li>
            )}
            {news?.overall_sentiment === "positive" && <li>• Positive news sentiment</li>}
            {movement?.is_anomaly && movement.price_change_percent > 0 && <li>• Unusual upward movement detected</li>}
          </ul>
        </Card>

        <Card variant="outlined">
          <h4 className="text-sm font-semibold text-bear-500 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-bear-500" />
            Bearish Signals
          </h4>
          <ul className="space-y-2 text-sm text-terminal-textMuted">
            {quote.change_percent < 0 && <li>• Negative price momentum today</li>}
            {health?.sub_scores.find((s) => s.name === "Valuation") && health.sub_scores.find((s) => s.name === "Valuation")!.score < 60 && (
              <li>• Valuation concerns ({health.sub_scores.find((s) => s.name === "Valuation")!.score}/100)</li>
            )}
            {health?.sub_scores.find((s) => s.name === "Risk") && health.sub_scores.find((s) => s.name === "Risk")!.score < 60 && (
              <li>• Elevated risk score ({health.sub_scores.find((s) => s.name === "Risk")!.score}/100)</li>
            )}
            {news?.overall_sentiment === "negative" && <li>• Negative news sentiment</li>}
            {movement?.is_anomaly && movement.price_change_percent < 0 && <li>• Unusual downward movement detected</li>}
          </ul>
        </Card>
      </div>

      {/* Major Recent Event */}
      {movement?.is_anomaly && (
        <Card className="border-terminal-warning/50 bg-yellow-900/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-terminal-text">Significant Movement Detected</h4>
              <p className="text-sm text-terminal-textMuted mt-1">{movement.summary}</p>
              {movement.drivers.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {movement.drivers.slice(0, 3).map((d, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 text-xs rounded bg-terminal-panel border border-terminal-border"
                    >
                      {d.driver} ({d.confidence}%)
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      <InlineDisclaimer className="mt-4" />
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
  return num.toString();
}