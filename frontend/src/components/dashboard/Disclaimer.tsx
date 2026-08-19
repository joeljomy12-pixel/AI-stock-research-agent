"use client";

import { clsx } from "clsx";

export function Disclaimer({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "fixed bottom-0 left-0 right-0 z-50 bg-terminal-panel border-t border-terminal-border px-4 py-2 text-center",
        className
      )}
    >
      <p className="text-xs text-terminal-textMuted max-w-4xl mx-auto">
        <strong className="text-terminal-text">Disclaimer:</strong> This is an educational/research tool, NOT financial advice.
        AI-generated analysis may contain errors. Do not make investment decisions based solely on this information.
        Always conduct your own research and consult a qualified financial advisor.
      </p>
    </div>
  );
}

export function InlineDisclaimer({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "bg-yellow-900/20 border border-yellow-800 rounded-lg p-3 text-sm text-yellow-300",
        className
      )}
    >
      <p className="flex items-center gap-2">
        <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
        <strong>Not Financial Advice:</strong> This analysis is for educational purposes only. Data may be delayed or inaccurate. Always verify independently and consult a financial advisor before investing.
      </p>
    </div>
  );
}