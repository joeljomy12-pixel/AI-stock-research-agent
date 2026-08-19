"use client";

import { Card } from "@/components/ui/Card";
import { Loading, SkeletonCard } from "@/components/ui/Loading";
import { useStockResearch } from "@/hooks/useStockData";
import { clsx } from "clsx";
import { format } from "date-fns";

const typeIcons: Record<string, React.ReactNode> = {
  filing: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  news: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
    </svg>
  ),
  transcript: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
  ),
  report: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
};

const typeColors: Record<string, string> = {
  filing: "bg-purple-900/30 border-purple-800 text-purple-400",
  news: "bg-blue-900/30 border-blue-800 text-blue-400",
  transcript: "bg-orange-900/30 border-orange-800 text-orange-400",
  report: "bg-green-900/30 border-green-800 text-green-400",
};

export function EvidenceTab({ symbol }: { symbol: string }) {
  const { evidence, isLoading, isError, error } = useStockResearch(symbol);

  if (isLoading) {
    return (
      <div className="space-y-4 animate-fade-in">
        {[1, 2, 3, 4, 5].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-12 text-bear-500">
        <p>Failed to load evidence: {error?.message || "Unknown error"}</p>
      </div>
    );
  }

  if (!evidence || evidence.documents.length === 0) {
    return (
      <Card className="text-center py-12">
        <p className="text-terminal-textMuted">No source documents available for {symbol.toUpperCase()}</p>
      </Card>
    );
  }

  // Group by type
  const grouped: Record<string, (typeof evidence.documents)[0][]> = {};
  for (const doc of evidence.documents) {
    if (!grouped[doc.type]) grouped[doc.type] = [];
    grouped[doc.type].push(doc);
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Summary */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-terminal-text">Source Documents</h3>
            <p className="text-sm text-terminal-textMuted mt-1">
              {evidence.total_count} documents retrieved from vector store
            </p>
          </div>
          <div className="flex gap-2">
            {Object.entries(grouped).map(([type, docs]) => (
              <span
                key={type}
                className={clsx(
                  "px-3 py-1 rounded-full text-xs font-medium",
                  typeColors[type] || "bg-terminal-border text-terminal-textMuted"
                )}
              >
                {typeIcons[type]}
                {type.charAt(0).toUpperCase() + type.slice(1)}: {docs.length}
              </span>
            ))}
          </div>
        </div>
      </Card>

      {/* Documents by Type */}
      <div className="space-y-6">
        {Object.entries(grouped).map(([type, docs]) => (
          <Card key={type}>
            <div className="flex items-center gap-2 mb-4">
              <div className={clsx("w-8 h-8 rounded-lg flex items-center justify-center", typeColors[type])}>
                {typeIcons[type]}
              </div>
              <h4 className="font-semibold text-terminal-text">
                {type.charAt(0).toUpperCase() + type.slice(1)}s ({docs.length})
              </h4>
            </div>
            <div className="space-y-3">
              {docs.map((doc, i) => (
                <div
                  key={doc.id}
                  className="group bg-terminal-bg border border-terminal-border rounded-lg p-4 hover:border-terminal-accent/50 transition-colors"
                >
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h5 className="font-medium text-terminal-text line-clamp-1">{doc.title}</h5>
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-terminal-textMuted">
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          {format(new Date(doc.date), "MMM d, yyyy")}
                        </span>
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                          </svg>
                          {doc.source}
                        </span>
                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded-full text-xs font-mono",
                            doc.relevance_score > 0.7 && "text-bull-500",
                            doc.relevance_score > 0.4 && "text-yellow-500",
                            doc.relevance_score <= 0.4 && "text-terminal-textMuted"
                          )}
                        >
                          Relevance: {(doc.relevance_score * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="mt-2 text-sm text-terminal-textMuted line-clamp-2">{doc.content_preview}</p>
                      {doc.highlighted_segments.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {doc.highlighted_segments.slice(0, 3).map((seg: string, j: number) => (
                            <div
                              key={j}
                              className="text-xs bg-yellow-900/30 border border-yellow-800 rounded p-2 text-yellow-300"
                            >
                              "..."{seg}"..."
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    {doc.url && (
                      <a
                        href={doc.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-shrink-0 px-3 py-2 bg-terminal-panel border border-terminal-border rounded-lg text-sm font-medium text-terminal-text hover:bg-terminal-accent/10 hover:border-terminal-accent/50 transition-colors"
                      >
                        Open Source
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}