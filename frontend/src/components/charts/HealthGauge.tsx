"use client";

import { clsx } from "clsx";

interface HealthGaugeProps {
  score: number;
  label: string;
  color: string;
  size?: number;
  showLabel?: boolean;
  className?: string;
}

export function HealthGauge({
  score,
  label,
  color,
  size = 120,
  showLabel = true,
  className,
}: HealthGaugeProps) {
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);

  const strokeColor =
    color === "green"
      ? "#10b981"
      : color === "yellow"
      ? "#f59e0b"
      : color === "red"
      ? "#ef4444"
      : "#3b82f6";

  const bgColor =
    color === "green"
      ? "rgba(16, 185, 129, 0.1)"
      : color === "yellow"
      ? "rgba(245, 158, 11, 0.1)"
      : color === "red"
      ? "rgba(239, 68, 68, 0.1)"
      : "rgba(59, 130, 246, 0.1)";

  return (
    <div className={clsx("flex flex-col items-center", className)}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform rotate-90">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#1f2937"
            strokeWidth={8}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={8}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
            style={{ filter: `drop-shadow(0 0 8px ${strokeColor})` }}
          />
          {/* Center text */}
          <text
            x={size / 2}
            y={size / 2 + 8}
            textAnchor="middle"
            dominantBaseline="middle"
            className="font-mono text-2xl font-bold"
            fill="#e5e7eb"
          >
            {score}
          </text>
          <text
            x={size / 2}
            y={size / 2 + 28}
            textAnchor="middle"
            dominantBaseline="middle"
            className="font-mono text-xs"
            fill="#9ca3af"
          >
            /100
          </text>
        </svg>
      </div>
      {showLabel && (
        <div className="mt-3 text-center">
          <p className="text-sm font-medium text-terminal-text">{label}</p>
          <div
            className={clsx(
              "mt-1 px-2 py-0.5 rounded-full text-xs font-medium inline-block",
              color === "green" && "bg-bull-900/50 text-bull-500",
              color === "yellow" && "bg-yellow-900/50 text-yellow-500",
              color === "red" && "bg-bear-900/50 text-bear-500"
            )}
          >
            {label}
          </div>
        </div>
      )}
    </div>
  );
}

// Horizontal bar gauge for sub-scores
export function HealthBar({
  score,
  label,
  color,
  showScore = true,
  className,
}: {
  score: number;
  label: string;
  color: string;
  showScore?: boolean;
  className?: string;
}) {
  const bgColor =
    color === "green"
      ? "bg-bull-500"
      : color === "yellow"
      ? "bg-yellow-500"
      : color === "red"
      ? "bg-bear-500"
      : "bg-blue-500";

  const textColor =
    color === "green"
      ? "text-bull-500"
      : color === "yellow"
      ? "text-yellow-500"
      : color === "red"
      ? "text-bear-500"
      : "text-blue-500";

  return (
    <div className={clsx("w-full", className)}>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-terminal-text">{label}</span>
        {showScore && (
          <span className={clsx("text-sm font-mono font-semibold", textColor)}>
            {score}/100
          </span>
        )}
      </div>
      <div className="h-2 bg-terminal-border rounded-full overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-1000 ease-out",
            bgColor
          )}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

// Score card with explanation
export function ScoreCard({
  score,
  label,
  color,
  explanation,
  metrics = {},
}: {
  score: number;
  label: string;
  color: string;
  explanation: string;
  metrics?: Record<string, any>;
}) {
  const iconMap: Record<string, string> = {
    "Financial Health": "💰",
    Growth: "📈",
    Momentum: "⚡",
    Valuation: "💎",
    "Market Sentiment": "📰",
    Risk: "⚠️",
  };

  return (
    <div className="bg-terminal-panel border border-terminal-border rounded-xl p-5 hover:border-terminal-accent/50 transition-colors">
      <div className="flex items-start gap-4">
        <HealthGauge score={score} label={label} color={color} size={80} showLabel={false} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{iconMap[label] || "📊"}</span>
            <h4 className="font-semibold text-terminal-text">{label}</h4>
            <span
              className={clsx(
                "px-2 py-0.5 rounded-full text-xs font-medium",
                color === "green" && "bg-bull-900/50 text-bull-500",
                color === "yellow" && "bg-yellow-900/50 text-yellow-500",
                color === "red" && "bg-bear-900/50 text-bear-500"
              )}
            >
              {score}/100
            </span>
          </div>
          <p className="text-sm text-terminal-textMuted leading-relaxed">{explanation}</p>
          {Object.keys(metrics).length > 0 && (
            <div className="mt-3 pt-3 border-t border-terminal-border">
              <div className="grid grid-cols-2 gap-2 text-xs">
                {Object.entries(metrics).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-terminal-textMuted">{key.replace(/_/g, " ")}:</span>
                    <span className="text-terminal-text font-mono">
                      {typeof value === "number" ? value.toFixed(2) : value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}