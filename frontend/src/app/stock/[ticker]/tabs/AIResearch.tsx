"use client";

import { Card } from "@/components/ui/Card";
import { Loading, SkeletonCard } from "@/components/ui/Loading";
import { InlineDisclaimer } from "@/components/dashboard/Disclaimer";
import { useStockResearch } from "@/hooks/useStockData";
import { clsx } from "clsx";
import { format } from "date-fns";

export function AIResearchTab({ symbol }: { symbol: string }) {
  const { research, fundamentals, evidence, isLoading, isError, error } = useStockResearch(symbol);

  if (isLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 text-bear-500">
        <p>Failed to load research: {error?.message || "Unknown error"}</p>
      </div>
    );
  }

  if (!research) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Investment Thesis */}
      <Card>
        <h3 className="text-lg font-semibold text-terminal-text mb-4">Investment Thesis</h3>
        <div className="space-y-6">
          {/* Bull Case */}
          <div>
            <h4 className="text-sm font-semibold text-bull-500 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
              Bull Case
            </h4>
            <ul className="space-y-2">
              {research.thesis.bull_case.map((point, i) => (
                <li key={i} className="text-sm text-terminal-textMuted flex items-start gap-2">
                  <span className="text-bull-500 flex-shrink-0 mt-0.5">▸</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Bear Case */}
          <div>
            <h4 className="text-sm font-semibold text-bear-500 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
              Bear Case
            </h4>
            <ul className="space-y-2">
              {research.thesis.bear_case.map((point, i) => (
                <li key={i} className="text-sm text-terminal-textMuted flex items-start gap-2">
                  <span className="text-bear-500 flex-shrink-0 mt-0.5">▸</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Key Catalysts */}
          <div className="bg-bull-900/20 border border-bull-800 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-bull-500 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Key Catalysts
            </h4>
            <ul className="space-y-2">
              {research.thesis.key_catalysts.map((point, i) => (
                <li key={i} className="text-sm text-terminal-textMuted flex items-start gap-2">
                  <span className="text-bull-500 flex-shrink-0 mt-0.5">⚡</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Key Risks */}
          <div className="bg-bear-900/20 border border-bear-800 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-bear-500 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Key Risks
            </h4>
            <ul className="space-y-2">
              {research.thesis.key_risks.map((point, i) => (
                <li key={i} className="text-sm text-terminal-textMuted flex items-start gap-2">
                  <span className="text-bear-500 flex-shrink-0 mt-0.5">⚠</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Recent Developments */}
          <div>
            <h4 className="text-sm font-semibold text-terminal-info mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Recent Developments
            </h4>
            <ul className="space-y-2">
              {research.thesis.recent_developments.map((point, i) => (
                <li key={i} className="text-sm text-terminal-textMuted flex items-start gap-2">
                  <span className="text-terminal-info flex-shrink-0 mt-0.5">📌</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Watch Items */}
          <div className="bg-terminal-border/50 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-terminal-textMuted mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              What to Watch
            </h4>
            <ul className="space-y-2">
              {research.thesis.watch_items.map((point, i) => (
                <li key={i} className="text-sm text-terminal-textMuted flex items-start gap-2">
                  <span className="text-terminal-textMuted flex-shrink-0 mt-0.5">👁</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>

      {/* Detailed Sections */}
      <div className="space-y-4">
        {research.sections.map((section, i) => (
          <Card key={i}>
            <h4 className="text-base font-semibold text-terminal-text mb-3">{section.title}</h4>
            <div className="prose prose-invert max-w-none text-sm text-terminal-textMuted leading-relaxed">
              {section.content.split("\n").map((para, j) => (
                <p key={j} className="mb-2">{para}</p>
              ))}
            </div>
            {section.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-terminal-border">
                <p className="text-xs text-terminal-textMuted">
                  Sources: {section.sources.join(", ")}
                </p>
              </div>
            )}
          </Card>
        ))}
      </div>

      <InlineDisclaimer className="mt-4" />
    </div>
  );
}