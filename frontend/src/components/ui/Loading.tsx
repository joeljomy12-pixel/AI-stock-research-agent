"use client";

import { clsx } from "clsx";

interface LoadingProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  text?: string;
}

export function Loading({ size = "md", className, text }: LoadingProps) {
  const sizes = {
    sm: "h-4 w-4 border-2",
    md: "h-8 w-8 border-3",
    lg: "h-12 w-12 border-4",
  };

  return (
    <div className={clsx("flex flex-col items-center justify-center gap-2", className)}>
      <div
        className={clsx(
          "animate-spin rounded-full border-terminal-border border-t-terminal-accent",
          sizes[size]
        )}
      />
      {text && <p className="text-terminal-textMuted text-sm">{text}</p>}
    </div>
  );
}

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={clsx(
        "animate-pulse bg-terminal-border rounded",
        className
      )}
      {...props}
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-4 w-3/4 bg-terminal-border rounded" />
      <div className="h-8 w-1/2 bg-terminal-border rounded" />
      <div className="h-4 w-full bg-terminal-border rounded" />
      <div className="h-4 w-2/3 bg-terminal-border rounded" />
      <div className="h-4 w-1/3 bg-terminal-border rounded" />
    </div>
  );
}

export function SkeletonChart({ height = 200 }: { height?: number }) {
  return (
    <div className="animate-pulse">
      <div className="h-4 w-1/4 bg-terminal-border rounded mb-4" />
      <div style={{ height }} className="bg-terminal-bg rounded-lg border border-terminal-border" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-3">
      <div className="flex gap-4">
        <div className="h-4 w-24 bg-terminal-border rounded" />
        <div className="h-4 w-20 bg-terminal-border rounded" />
        <div className="h-4 w-20 bg-terminal-border rounded" />
        <div className="h-4 w-20 bg-terminal-border rounded" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <div className="h-4 w-24 bg-terminal-border rounded" />
          <div className="h-4 w-20 bg-terminal-border rounded" />
          <div className="h-4 w-20 bg-terminal-border rounded" />
          <div className="h-4 w-20 bg-terminal-border rounded" />
        </div>
      ))}
    </div>
  );
}