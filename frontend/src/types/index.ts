// Frontend TypeScript types matching backend schemas

export interface QuoteData {
  symbol: string;
  name: string;
  sector?: string;
  industry?: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  avg_volume: number;
  market_cap?: number;
  day_high: number;
  day_low: number;
  year_high: number;
  year_low: number;
  pe_ratio?: number;
  dividend_yield?: number;
  timestamp: string;
}

export interface PricePoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoricalData {
  symbol: string;
  timeframe: string;
  data: PricePoint[];
}

export interface FundamentalsData {
  symbol: string;
  company_name: string;
  sector: string;
  industry: string;
  market_cap?: number;
  enterprise_value?: number;
  revenue?: number;
  revenue_growth_yoy?: number;
  gross_profit?: number;
  gross_margin?: number;
  operating_income?: number;
  operating_margin?: number;
  net_income?: number;
  net_margin?: number;
  eps?: number;
  eps_growth_yoy?: number;
  total_assets?: number;
  total_liabilities?: number;
  total_equity?: number;
  cash_and_equivalents?: number;
  total_debt?: number;
  debt_to_equity?: number;
  current_ratio?: number;
  operating_cash_flow?: number;
  free_cash_flow?: number;
  fcf_margin?: number;
  pe_ratio?: number;
  forward_pe?: number;
  peg_ratio?: number;
  price_to_sales?: number;
  price_to_book?: number;
  ev_to_ebitda?: number;
  roe?: number;
  roa?: number;
  roic?: number;
  analyst_rating?: string;
  price_target?: number;
  num_analysts?: number;
  period: string;
  updated_at: string;
}

export type SentimentLabel = "positive" | "negative" | "neutral";

export interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  url: string;
  source: string;
  published_at: string;
  sentiment: SentimentLabel;
  sentiment_score: number;
  tickers: string[];
  image_url?: string;
}

export interface NewsResponse {
  symbol: string;
  articles: NewsArticle[];
  overall_sentiment: SentimentLabel;
  sentiment_score: number;
  article_count: number;
}

export interface HealthSubScore {
  name: string;
  score: number;
  label: string;
  color: string;
  explanation: string;
  metrics: Record<string, any>;
}

export interface HealthScoreResponse {
  symbol: string;
  overall_score: number;
  overall_label: string;
  overall_color: string;
  sub_scores: HealthSubScore[];
  percentile_rank?: number;
  calculated_at: string;
}

export interface MovementDriver {
  driver: string;
  confidence: number;
  category: "evidence" | "correlation" | "possible" | "high_confidence";
  evidence: string[];
  description: string;
}

export interface MovementAnalysis {
  symbol: string;
  date: string;
  price_change: number;
  price_change_percent: number;
  volume_ratio: number;
  is_anomaly: boolean;
  anomaly_score: number;
  drivers: MovementDriver[];
  summary: string;
  analyzed_at: string;
}

export interface InvestmentThesis {
  bull_case: string[];
  bear_case: string[];
  key_catalysts: string[];
  key_risks: string[];
  recent_developments: string[];
  watch_items: string[];
}

export interface ResearchSection {
  title: string;
  content: string;
  sources: string[];
}

export interface ResearchReport {
  symbol: string;
  company_name: string;
  thesis: InvestmentThesis;
  sections: ResearchSection[];
  generated_at: string;
  disclaimer: string;
}

export interface SourceDocument {
  id: string;
  type: string;
  title: string;
  source: string;
  date: string;
  url?: string;
  content_preview: string;
  relevance_score: number;
  highlighted_segments: string[];
}

export interface SearchResult {
  symbol: string;
  name: string;
  exchange: string;
  type: string;
}

export type TimeFrame = "1d" | "1wk" | "1mo" | "3mo" | "1y";

export type TabType = "overview" | "research" | "movement" | "doctor" | "news" | "evidence";

export interface TabConfig {
  id: TabType;
  label: string;
  icon: string;
  description: string;
}

export const TABS: TabConfig[] = [
  { id: "overview", label: "Overview", icon: "📊", description: "Price, metrics, health score" },
  { id: "research", label: "AI Research", icon: "🤖", description: "Investment thesis & analysis" },
  { id: "movement", label: "Why It Moved", icon: "🔍", description: "Movement drivers & catalysts" },
  { id: "doctor", label: "Stock Doctor", icon: "🏥", description: "Health scores & diagnosis" },
  { id: "news", label: "News", icon: "📰", description: "Sentiment-analyzed news feed" },
  { id: "evidence", label: "Evidence", icon: "📋", description: "Source documents & citations" },
];