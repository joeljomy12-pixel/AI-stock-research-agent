from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.services.market_data import get_quote, get_historical, get_key_stats, search_tickers, TimeFrame
from app.services.financial_data import get_fundamentals
from app.services.news_service import get_news_with_sentiment, get_market_news
from app.ml.health_scorer import calculate_health_score
from app.ml.anomaly_detector import analyze_movement
from app.services.research_agent import generate_research_report, get_evidence_documents
from app.models.schemas import (
    QuoteData, HistoricalData, FundamentalsData, NewsResponse,
    HealthScoreResponse, MovementAnalysis, ResearchReport,
    SearchResult, APIResponse
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/search", response_model=APIResponse)
async def search_stocks(q: str = Query(..., min_length=1)):
    """Search for stock tickers."""
    try:
        results = await search_tickers(q)
        return APIResponse(
            success=True,
            data=[SearchResult(**r) for r in results]
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.get("/{symbol}/quote", response_model=APIResponse)
async def get_stock_quote(symbol: str):
    """Get current quote for a stock."""
    try:
        quote = await get_quote(symbol)
        return APIResponse(success=True, data=quote)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{symbol}/historical", response_model=APIResponse)
async def get_stock_historical(
    symbol: str,
    timeframe: TimeFrame = Query(TimeFrame.MONTH)
):
    """Get historical price data."""
    try:
        hist = await get_historical(symbol, timeframe)
        return APIResponse(success=True, data=hist)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{symbol}/fundamentals", response_model=APIResponse)
async def get_stock_fundamentals(symbol: str):
    """Get fundamental financial data."""
    try:
        fundamentals = await get_fundamentals(symbol)
        return APIResponse(success=True, data=fundamentals)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{symbol}/key-stats", response_model=APIResponse)
async def get_stock_key_stats(symbol: str):
    """Get key statistics."""
    try:
        stats = await get_key_stats(symbol)
        return APIResponse(success=True, data=stats)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{symbol}/news", response_model=APIResponse)
async def get_stock_news(symbol: str, limit: int = Query(20, le=50)):
    """Get news with sentiment analysis."""
    try:
        news = await get_news_with_sentiment(symbol, limit)
        return APIResponse(success=True, data=news)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{symbol}/health", response_model=APIResponse)
async def get_stock_health(symbol: str):
    """Get AI health score."""
    try:
        health = await calculate_health_score(symbol)
        return APIResponse(success=True, data=health)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/movement", response_model=APIResponse)
async def get_stock_movement(symbol: str):
    """Get movement analysis (why did it move)."""
    try:
        movement = await analyze_movement(symbol)
        return APIResponse(success=True, data=movement)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/research", response_model=APIResponse)
async def get_stock_research(symbol: str):
    """Get AI research report."""
    try:
        report = await generate_research_report(symbol)
        return APIResponse(success=True, data=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/evidence", response_model=APIResponse)
async def get_stock_evidence(symbol: str):
    """Get source documents/evidence."""
    try:
        evidence = await get_evidence_documents(symbol)
        return APIResponse(success=True, data={"symbol": symbol.upper(), "documents": evidence, "total_count": len(evidence)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/news", response_model=APIResponse)
async def get_market_news_endpoint(limit: int = Query(30, le=50)):
    """Get general market news."""
    try:
        news = await get_market_news(limit)
        return APIResponse(success=True, data=news)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))