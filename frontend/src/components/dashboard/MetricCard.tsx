"use client";

import { clsx } from "clsx";
import { formatMarketCap, formatPercent, formatPrice, formatNumber } from "@/lib/api";

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number;
  prefix?: string;
  suffix?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function MetricCard({
  label,
  value,
  change,
  prefix = "",
  suffix = "",
  trend = "neutral",
  className,
}: MetricCardProps) {
  const displayValue = typeof value === "number" ? value.toFixed(2) : value;

  return (
    <div className={clsx("bg-terminal-panel border border-terminal-border rounded-xl p-4", className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-terminal-textMuted uppercase tracking-wider mb-1">
            {label}
          </p>
          <p className="text-xl font-mono font-semibold text-terminal-text">
            {prefix}{displayValue}{suffix}
          </p>
          {change !== undefined && (
            <p
              className={clsx(
                "mt-1 text-sm font-medium flex items-center gap-1",
                change > 0 ? "text-bull-500" : change < 0 ? "text-bear-500" : "text-terminal-textMuted"
              )}
            >
              {change > 0 && <span>▲</span>}
              {change < 0 && <span>▼</span>}
              {change > 0 ? "+" : ""}{change.toFixed(2)}%
            </p>
          )}
        </div>
        {trend !== "neutral" && (
          <div
            className={clsx(
              "w-2 h-2 rounded-full",
              trend === "up" ? "bg-bull-500" : "bg-bear-500"
            )}
          />
        )}
      </div>
    </div>
  );
}

export function KeyMetricsGrid({
  quote,
  fundamentals,
}: {
  quote: any;
  fundamentals: any;
}) {
  const metrics = [
    {
      label: "Market Cap",
      value: quote.market_cap ? formatMarketCap(quote.market_cap) : "N/A",
    },
    {
      label: "P/E Ratio",
      value: quote.pe_ratio ? formatNumber(quote.pe_ratio) : "N/A",
    },
    {
      label: "Volume",
      value: formatNumber(quote.volume),
      change: quote.avg_volume ? ((quote.volume / quote.avg_volume - 1) * 100) : undefined,
    },
    {
      label: "52W Range",
      value: `${formatPrice(quote.year_low)} - ${formatPrice(quote.year_high)}`,
    },
    {
      label: "Revenue (TTM)",
      value: fundamentals?.revenue ? formatMarketCap(fundamentals.revenue) : "N/A",
    },
    {
      label: "Rev Growth YoY",
      value: fundamentals?.revenue_growth_yoy ? formatPercent(fundamentals.revenue_growth_yoy) : "N/A",
      trend: (fundamentals?.revenue_growth_yoy && fundamentals?.revenue_growth_yoy > 0 ? "up" : "down") as "up" | "down",
    },
    {
      label: "Net Margin",
      value: fundamentals?.net_margin ? formatPercent(fundamentals.net_margin) : "N/A",
    },
    {
      label: "Free Cash Flow",
      value: fundamentals?.free_cash_flow ? formatMarketCap(fundamentals.free_cash_flow) : "N/A",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {metrics.map((m, i) => (
        <MetricCard key={i} {...m} />
      ))}
    </div>
  );
}