"use client";

import { Card } from "@/components/ui/Card";
import { Loading, SkeletonCard } from "@/components/ui/Loading";
import { useStockOverview } from "@/hooks/useStockData";
import { clsx } from "clsx";
import { format, formatDistanceToNow } from "date-fns";

const sentimentStyles = {
  positive: "bg-bull-900/30 border-bull-800 text-bull-400",
  negative: "bg-bear-900/30 border-bear-800 text-bear-400",
  neutral: "bg-terminal-border/50 border-terminal-border text-terminal-textMuted",
};

const sentimentIcons = {
  positive: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
    </svg>
  ),
  negative: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
    </svg>
  ),
  neutral: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  ),
};

export function NewsTab({ symbol }: { symbol: string }) {
  const { news, isLoading, isError, error } = useStockOverview(symbol);

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
        <p>Failed to load news: {error?.message || "Unknown error"}</p>
      </div>
    );
  }

  if (!news || news.articles.length === 0) {
    return (
      <Card className="text-center py-12">
        <p className="text-terminal-textMuted">No recent news available for {symbol.toUpperCase()}</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Sentiment Summary */}
      <Card className={clsx("border-l-4", sentimentStyles[news.overall_sentiment])}>
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={clsx("w-10 h-10 rounded-full flex items-center justify-center", sentimentStyles[news.overall_sentiment])}>
              {sentimentIcons[news.overall_sentiment]}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-terminal-text">Overall Sentiment</h3>
              <p className="text-sm text-terminal-textMuted">
                {news.article_count} articles • Score: {news.sentiment_score.toFixed(2)}
              </p>
            </div>
          </div>
          <div className={clsx("px-4 py-2 rounded-full font-semibold text-sm", sentimentStyles[news.overall_sentiment])}>
            {news.overall_sentiment.charAt(0).toUpperCase() + news.overall_sentiment.slice(1)}
          </div>
        </div>
      </Card>

      {/* News Articles */}
      <div className="space-y-3">
        {news.articles.map((article, i) => (
          <Card key={i} className={clsx("hover:border-terminal-accent/50 transition-colors", sentimentStyles[article.sentiment])}>
            <div className="flex flex-col md:flex-row gap-4">
              {article.image_url && (
                <div className="w-24 h-24 md:w-32 md:h-32 flex-shrink-0 rounded-lg overflow-hidden bg-terminal-bg">
                  <img
                    src={article.image_url}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="font-medium text-terminal-text line-clamp-2">{article.title}</h4>
                  <span
                    className={clsx(
                      "px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0",
                      sentimentStyles[article.sentiment]
                    )}
                  >
                    {sentimentIcons[article.sentiment]}
                    {article.sentiment.charAt(0).toUpperCase() + article.sentiment.slice(1)}
                    {' '}
                    {article.sentiment_score.toFixed(2)}
                  </span>
                </div>
                <p className="text-sm text-terminal-textMuted mt-1 line-clamp-2">{article.summary}</p>
                <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-terminal-textMuted">
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {formatDistanceToNow(new Date(article.published_at), { addSuffix: true })}
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                    </svg>
                    {article.source}
                  </span>
                  {article.tickers.length > 0 && (
                    <span className="flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                      {article.tickers.join(", ")}
                    </span>
                  )}
                </div>
              </div>
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center px-4 py-2 bg-terminal-bg border border-terminal-border rounded-lg text-sm font-medium text-terminal-text hover:bg-terminal-panel transition-colors"
              >
                Read →
              </a>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}