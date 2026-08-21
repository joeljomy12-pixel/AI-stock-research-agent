from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class TimeFrame(str, Enum):
    DAY = "1d"
    WEEK = "1wk"
    MONTH = "1mo"
    THREE_MONTHS = "3mo"
    YEAR = "1y"


# Market Data Models
class QuoteData(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    price: float
    change: float
    change_percent: float
    volume: int
    avg_volume: int
    market_cap: Optional[float] = None
    day_high: float
    day_low: float
    year_high: float
    year_low: float
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PricePoint(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalData(BaseModel):
    symbol: str
    timeframe: TimeFrame
    data: List[PricePoint]


# Fundamentals Models
class FinancialMetric(BaseModel):
    label: str
    value: Optional[float] = None
    unit: str = ""
    period: str = ""
    change: Optional[float] = None


class FundamentalsData(BaseModel):
    symbol: str
    company_name: str
    sector: str
    industry: str
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None

    # Income Statement
    revenue: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    gross_profit: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_income: Optional[float] = None
    operating_margin: Optional[float] = None
    net_income: Optional[float] = None
    net_margin: Optional[float] = None
    eps: Optional[float] = None
    eps_growth_yoy: Optional[float] = None

    # Balance Sheet
    total_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    total_debt: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None

    # Cash Flow
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    fcf_margin: Optional[float] = None

    # Valuation
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None
    ev_to_ebitda: Optional[float] = None

    # Profitability
    roe: Optional[float] = None
    roa: Optional[float] = None
    roic: Optional[float] = None

    # Analyst
    analyst_rating: Optional[str] = None
    price_target: Optional[float] = None
    num_analysts: Optional[int] = None

    period: str = "TTM"
    updated_at: datetime = Field(default_factory=datetime.now)


# News Models
class NewsArticle(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    source: str
    published_at: datetime
    sentiment: SentimentLabel
    sentiment_score: float
    tickers: List[str] = []
    image_url: Optional[str] = None


class NewsResponse(BaseModel):
    symbol: str
    articles: List[NewsArticle]
    overall_sentiment: SentimentLabel
    sentiment_score: float
    article_count: int


# Health Score Models
class HealthSubScore(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)
    label: str  # "Excellent", "Good", "Fair", "Poor"
    color: str  # "green", "yellow", "red"
    explanation: str
    metrics: Dict[str, Any] = {}


class HealthScoreResponse(BaseModel):
    symbol: str
    overall_score: int = Field(ge=0, le=100)
    overall_label: str
    overall_color: str
    sub_scores: List[HealthSubScore]
    percentile_rank: Optional[int] = None
    calculated_at: datetime = Field(default_factory=datetime.now)


# Movement Models
class MovementDriver(BaseModel):
    driver: str
    confidence: int = Field(ge=0, le=100)
    category: str  # "evidence", "correlation", "possible", "high_confidence"
    evidence: List[str] = []
    description: str


class MovementAnalysis(BaseModel):
    symbol: str
    date: str
    price_change: float
    price_change_percent: float
    volume_ratio: float
    is_anomaly: bool
    anomaly_score: float
    drivers: List[MovementDriver]
    summary: str
    analyzed_at: datetime = Field(default_factory=datetime.now)


# Research Models
class ResearchSection(BaseModel):
    title: str
    content: str
    sources: List[str] = []


class InvestmentThesis(BaseModel):
    bull_case: List[str]
    bear_case: List[str]
    key_catalysts: List[str]
    key_risks: List[str]
    recent_developments: List[str]
    watch_items: List[str]


class ResearchReport(BaseModel):
    symbol: str
    company_name: str
    thesis: InvestmentThesis
    sections: List[ResearchSection]
    generated_at: datetime = Field(default_factory=datetime.now)
    disclaimer: str = "This is an educational/research tool, NOT financial advice. Do not present AI conclusions as guaranteed predictions or recommendations."


# Evidence Models
class SourceDocument(BaseModel):
    id: str
    type: str  # "filing", "news", "transcript", "report"
    title: str
    source: str
    date: datetime
    url: Optional[str] = None
    content_preview: str
    relevance_score: float
    highlighted_segments: List[str] = []


class EvidenceResponse(BaseModel):
    symbol: str
    documents: List[SourceDocument]
    total_count: int


# API Response Wrappers
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None


class SearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str
