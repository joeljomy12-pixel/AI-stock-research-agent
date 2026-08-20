import axios from "axios";
import type {
  QuoteData,
  HistoricalData,
  FundamentalsData,
  NewsResponse,
  HealthScoreResponse,
  MovementAnalysis,
  ResearchReport,
  SearchResult,
  TimeFrame,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "https://stock-intelligence-api-tkkf.onrender.com";

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      "An unexpected error occurred";
    console.error("API Error:", message);
    throw new Error(message);
  }
);

// Stock API calls
export async function searchStocks(query: string): Promise<SearchResult[]> {
  const response: any = await api.get(`/stocks/search?q=${query}`);
  return response.success ? response.data : [];
}

export async function getQuote(symbol: string): Promise<QuoteData> {
  const response: any = await api.get(`/stocks/${symbol}/quote`);
  return response.data;
}

export async function getHistorical(
  symbol: string,
  timeframe: TimeFrame = "1mo"
): Promise<HistoricalData> {
  const response: any = await api.get(
    `/stocks/${symbol}/historical?timeframe=${timeframe}`
  );
  return response.data;
}

export async function getFundamentals(
  symbol: string
): Promise<FundamentalsData> {
  const response: any = await api.get(`/stocks/${symbol}/fundamentals`);
  return response.data;
}

export async function getNews(symbol: string): Promise<NewsResponse> {
  const response: any = await api.get(`/stocks/${symbol}/news`);
  return response.data;
}

export async function getHealthScore(
  symbol: string
): Promise<HealthScoreResponse> {
  const response: any = await api.get(`/stocks/${symbol}/health`);
  return response.data;
}

export async function getMovementAnalysis(
  symbol: string
): Promise<MovementAnalysis> {
  const response: any = await api.get(`/stocks/${symbol}/movement`);
  return response.data;
}

export async function getResearchReport(
  symbol: string
): Promise<ResearchReport> {
  const response: any = await api.get(`/stocks/${symbol}/research`);
  return response.data;
}

export async function getEvidence(symbol: string): Promise<any> {
  const response: any = await api.get(`/stocks/${symbol}/evidence`);
  return response.data;
}

// Helper to format large numbers
export function formatMarketCap(value?: number): string {
  if (value === undefined || value === null) return "N/A";
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
}

export function formatNumber(value?: number): string {
  if (value === undefined || value === null) return "N/A";
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatPercent(value?: number): string {
  if (value === undefined || value === null) return "N/A";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function formatPrice(value?: number): string {
  if (value === undefined || value === null) return "N/A";
  return `$${value.toFixed(2)}`;
}

export function formatRatio(value?: number): string {
  if (value === undefined || value === null) return "N/A";
  return value.toFixed(2);
}
