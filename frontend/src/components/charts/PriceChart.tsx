"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
} from "recharts";
import type { PricePoint } from "@/types";
import { format } from "date-fns";
import { clsx } from "clsx";

interface PriceChartProps {
  data: PricePoint[];
  height?: number;
  showVolume?: boolean;
  className?: string;
  color?: "bull" | "bear" | "neutral";
}

export function PriceChart({
  data,
  height = 300,
  showVolume = false,
  className,
  color = "neutral",
}: PriceChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className={clsx("flex items-center justify-center h-64", className)}>
        <p className="text-terminal-textMuted">No price data available</p>
      </div>
    );
  }

  // Format data for recharts
  const chartData = data.map((point) => ({
    timestamp: point.timestamp,
    time: format(new Date(point.timestamp), "MMM dd"),
    open: point.open,
    high: point.high,
    low: point.low,
    close: point.close,
    volume: point.volume,
  }));

  const colors = {
    bull: { line: "#10b981", area: "rgba(16, 185, 129, 0.15)", grid: "#1f2937" },
    bear: { line: "#ef4444", area: "rgba(239, 68, 68, 0.15)", grid: "#1f2937" },
    neutral: { line: "#3b82f6", area: "rgba(59, 130, 246, 0.15)", grid: "#1f2937" },
  };

  const theme = colors[color];

  return (
    <div className={clsx("w-full", className)}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={chartData}
          margin={{ top: 10, right: 30, left: 10, bottom: showVolume ? 40 : 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} vertical={false} />
          <XAxis
            dataKey="time"
            tick={{ fill: "#9ca3af", fontSize: 11, fontFamily: "monospace" }}
            axisLine={false}
            tickLine={false}
            interval={Math.max(1, Math.floor(chartData.length / 8))}
          />
          <YAxis
            tick={{ fill: "#9ca3af", fontSize: 11, fontFamily: "monospace" }}
            axisLine={false}
            tickLine={false}
            width={60}
            tickFormatter={(value) => `$${value.toFixed(2)}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#111827",
              border: "1px solid #1f2937",
              borderRadius: "8px",
              color: "#e5e7eb",
            }}
            labelFormatter={(_, payload) => {
              const point = payload[0]?.payload;
              if (!point) return "";
              return format(new Date(point.timestamp), "MMM dd, yyyy HH:mm");
            }}
            formatter={(value: number, name: string) => {
              if (name === "volume") return [formatNumber(value), "Volume"];
              return [`$${value.toFixed(2)}`, name];
            }}
          />
          <Area
            type="monotone"
            dataKey="close"
            stroke={theme.line}
            fill={theme.area}
            strokeWidth={2}
            fillOpacity={0.6}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke={theme.line}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6, strokeWidth: 2, stroke: theme.line }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
  return num.toString();
}

// Mini sparkline chart for cards
export function SparklineChart({
  data,
  color = "neutral",
  height = 60,
}: {
  data: PricePoint[];
  color?: "bull" | "bear" | "neutral";
  height?: number;
}) {
  if (!data || data.length < 2) return null;

  const chartData = data.map((point, i) => ({
    value: point.close,
    index: i,
  }));

  const colors = {
    bull: "#10b981",
    bear: "#ef4444",
    neutral: "#3b82f6",
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <Line
          type="monotone"
          dataKey="value"
          stroke={colors[color]}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}