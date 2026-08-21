import { useQuery } from "@tanstack/react-query";
import type { TimeFrame } from "@/types";
import {
  searchStocks,
  getQuote,
  getHistorical,
  getFundamentals,
  getNews,
  getHealthScore,
  getMovementAnalysis,
  getResearchReport,
  getEvidence,
} from "@/lib/api";

// Search hook
export function useSearchStocks(query: string) {
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => searchStocks(query),
    enabled: query.length >= 1,
    staleTime: 60000,
  });
}

// Quote hook
export function useQuote(symbol: string | null) {
  return useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => getQuote(symbol!),
    enabled: !!symbol,
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

// Historical data hook
export function useHistorical(symbol: string | null, timeframe: TimeFrame = "1mo") {
  return useQuery({
    queryKey: ["historical", symbol, timeframe],
    queryFn: () => getHistorical(symbol!, timeframe),
    enabled: !!symbol,
    staleTime: 300000,
  });
}

// Fundamentals hook
export function useFundamentals(symbol: string | null) {
  return useQuery({
    queryKey: ["fundamentals", symbol],
    queryFn: () => getFundamentals(symbol!),
    enabled: !!symbol,
    staleTime: 600000,
  });
}

// News hook
export function useNews(symbol: string | null) {
  return useQuery({
    queryKey: ["news", symbol],
    queryFn: () => getNews(symbol!),
    enabled: !!symbol,
    staleTime: 180000,
  });
}

// Health score hook
export function useHealthScore(symbol: string | null) {
  return useQuery({
    queryKey: ["health", symbol],
    queryFn: () => getHealthScore(symbol!),
    enabled: !!symbol,
    staleTime: 300000,
  });
}

// Movement analysis hook
export function useMovementAnalysis(symbol: string | null) {
  return useQuery({
    queryKey: ["movement", symbol],
    queryFn: () => getMovementAnalysis(symbol!),
    enabled: !!symbol,
    staleTime: 180000,
  });
}

// Research report hook
export function useResearchReport(symbol: string | null) {
  return useQuery({
    queryKey: ["research", symbol],
    queryFn: () => getResearchReport(symbol!),
    enabled: !!symbol,
    staleTime: 600000,
  });
}

// Evidence hook
export function useEvidence(symbol: string | null) {
  return useQuery({
    queryKey: ["evidence", symbol],
    queryFn: () => getEvidence(symbol!),
    enabled: !!symbol,
    staleTime: 600000,
  });
}

// Combined hook for initial load
export function useStockOverview(symbol: string | null) {
  const quoteQuery = useQuote(symbol);
  const historicalQuery = useHistorical(symbol);
  const healthQuery = useHealthScore(symbol);
  const newsQuery = useNews(symbol);
  const movementQuery = useMovementAnalysis(symbol);

  return {
    quote: quoteQuery.data,
    historical: historicalQuery.data,
    health: healthQuery.data,
    news: newsQuery.data,
    movement: movementQuery.data,
    isLoading:
      quoteQuery.isLoading ||
      historicalQuery.isLoading ||
      healthQuery.isLoading ||
      newsQuery.isLoading ||
      movementQuery.isLoading,
    isError:
      quoteQuery.isError ||
      historicalQuery.isError ||
      healthQuery.isError ||
      newsQuery.isError ||
      movementQuery.isError,
    error:
      quoteQuery.error ||
      historicalQuery.error ||
      healthQuery.error ||
      newsQuery.error ||
      movementQuery.error,
  };
}

// Combined hook for research tab
export function useStockResearch(symbol: string | null) {
  const fundamentalsQuery = useFundamentals(symbol);
  const researchQuery = useResearchReport(symbol);
  const evidenceQuery = useEvidence(symbol);

  return {
    fundamentals: fundamentalsQuery.data,
    research: researchQuery.data,
    evidence: evidenceQuery.data,
    isLoading: fundamentalsQuery.isLoading || researchQuery.isLoading || evidenceQuery.isLoading,
    isError: fundamentalsQuery.isError || researchQuery.isError || evidenceQuery.isError,
    error: fundamentalsQuery.error || researchQuery.error || evidenceQuery.error,
  };
}
