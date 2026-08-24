import yfinance as yf
import pandas as pd
from typing import Optional, List, Dict, Any, Callable, TypeVar
from datetime import datetime, timedelta
import logging
import asyncio
from cachetools import TTLCache

from app.models.schemas import QuoteData, PricePoint, HistoricalData, TimeFrame
from app.core.config import settings

logger = logging.getLogger(__name__)

# In-memory cache
quote_cache = TTLCache(maxsize=100, ttl=settings.cache_ttl_quote)
history_cache = TTLCache(maxsize=100, ttl=300)

T = TypeVar('T')

async def _retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    **kwargs
) -> T:
    """Retry async function with exponential backoff for rate limiting."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()
            # Check for rate limiting - yfinance logs 429 but raises JSON decode error
            is_rate_limit = (
                '429' in error_msg or
                'too many requests' in error_msg or
                'rate limit' in error_msg or
                'expecting value' in error_msg or
                'json' in error_msg and 'decode' in error_msg or
                'possibly delisted' in error_msg or
                'no price data' in error_msg
            )
            if is_rate_limit and attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
                continue
            # Non-rate-limit error or max retries reached
            raise
    raise last_exception


def _get_ticker(symbol: str) -> yf.Ticker:
    """Get yfinance ticker object with error handling."""
    return yf.Ticker(symbol.upper())


def _safe_get(info: dict, key: str, default=None):
    """Safely get value from yfinance info dict."""
    val = info.get(key, default)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return val


async def get_quote(symbol: str) -> QuoteData:
    """Get current quote data for a symbol."""
    cache_key = f"quote_{symbol.upper()}"
    if cache_key in quote_cache:
        return quote_cache[cache_key]

    async def _fetch():
        ticker = _get_ticker(symbol)
        info = ticker.info

        if not info or 'regularMarketPrice' not in info:
            raise ValueError(f"No quote data found for {symbol}")

        quote = QuoteData(
            symbol=symbol.upper(),
            name=_safe_get(info, 'longName', symbol.upper()),
            sector=_safe_get(info, 'sector'),
            industry=_safe_get(info, 'industry'),
            price=float(_safe_get(info, 'regularMarketPrice', 0)),
            change=float(_safe_get(info, 'regularMarketChange', 0)),
            change_percent=float(_safe_get(info, 'regularMarketChangePercent', 0)) * 100,
            volume=int(_safe_get(info, 'regularMarketVolume', 0)),
            avg_volume=int(_safe_get(info, 'averageVolume', 0)),
            market_cap=_safe_get(info, 'marketCap'),
            day_high=float(_safe_get(info, 'regularMarketDayHigh', 0)),
            day_low=float(_safe_get(info, 'regularMarketDayLow', 0)),
            year_high=float(_safe_get(info, 'fiftyTwoWeekHigh', 0)),
            year_low=float(_safe_get(info, 'fiftyTwoWeekLow', 0)),
            pe_ratio=_safe_get(info, 'trailingPE'),
            dividend_yield=_safe_get(info, 'dividendYield'),
        )

        quote_cache[cache_key] = quote
        return quote

    try:
        return await _retry_with_backoff(_fetch)
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise


async def get_historical(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.MONTH,
    period: Optional[str] = None
) -> HistoricalData:
    """Get historical price data."""
    cache_key = f"hist_{symbol.upper()}_{timeframe.value}"
    if cache_key in history_cache:
        return history_cache[cache_key]

    async def _fetch():
        ticker = _get_ticker(symbol)

        # Map timeframe to yfinance period
        period_map = {
            TimeFrame.DAY: "1d",
            TimeFrame.WEEK: "5d",
            TimeFrame.MONTH: "1mo",
            TimeFrame.THREE_MONTHS: "3mo",
            TimeFrame.YEAR: "1y",
        }
        yf_period = period or period_map.get(timeframe, "1mo")

        # Get interval based on period
        interval_map = {
            "1d": "5m",
            "5d": "15m",
            "1mo": "1d",
            "3mo": "1d",
            "1y": "1d",
        }
        interval = interval_map.get(yf_period, "1d")

        hist = ticker.history(period=yf_period, interval=interval)

        if hist.empty:
            raise ValueError(f"No historical data for {symbol}")

        data_points = []
        for idx, row in hist.iterrows():
            data_points.append(PricePoint(
                timestamp=idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else idx,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume'])
            ))

        result = HistoricalData(
            symbol=symbol.upper(),
            timeframe=timeframe,
            data=data_points
        )

        history_cache[cache_key] = result
        return result

    try:
        return await _retry_with_backoff(_fetch)
    except Exception as e:
        logger.error(f"Error fetching historical for {symbol}: {e}")
        raise


async def get_key_stats(symbol: str) -> Dict[str, Any]:
    """Get key statistics for health scoring."""
    cache_key = f"stats_{symbol.upper()}"
    if cache_key in quote_cache:  # reuse quote cache
        return quote_cache[cache_key]

    async def _fetch():
        ticker = _get_ticker(symbol)
        info = ticker.info

        stats = {
            'beta': _safe_get(info, 'beta'),
            'shares_outstanding': _safe_get(info, 'sharesOutstanding'),
            'float_shares': _safe_get(info, 'floatShares'),
            'short_ratio': _safe_get(info, 'shortRatio'),
            'short_percent': _safe_get(info, 'shortPercentOfFloat'),
            'held_insiders': _safe_get(info, 'heldPercentInsiders'),
            'held_institutions': _safe_get(info, 'heldPercentInstitutions'),
            'book_value': _safe_get(info, 'bookValue'),
            'price_to_book': _safe_get(info, 'priceToBook'),
            'enterprise_value': _safe_get(info, 'enterpriseValue'),
            'ev_to_revenue': _safe_get(info, 'enterpriseToRevenue'),
            'ev_to_ebitda': _safe_get(info, 'enterpriseToEbitda'),
            'profit_margins': _safe_get(info, 'profitMargins'),
            'operating_margins': _safe_get(info, 'operatingMargins'),
            'return_on_equity': _safe_get(info, 'returnOnEquity'),
            'return_on_assets': _safe_get(info, 'returnOnAssets'),
            'revenue_growth': _safe_get(info, 'revenueGrowth'),
            'earnings_growth': _safe_get(info, 'earningsGrowth'),
            'current_ratio': _safe_get(info, 'currentRatio'),
            'quick_ratio': _safe_get(info, 'quickRatio'),
            'debt_to_equity': _safe_get(info, 'debtToEquity'),
            'total_cash': _safe_get(info, 'totalCash'),
            'total_debt': _safe_get(info, 'totalDebt'),
            'operating_cash_flow': _safe_get(info, 'operatingCashflow'),
            'free_cash_flow': _safe_get(info, 'freeCashflow'),
        }

        quote_cache[cache_key] = stats
        return stats

    try:
        return await _retry_with_backoff(_fetch)
    except Exception as e:
        logger.error(f"Error fetching key stats for {symbol}: {e}")
        return {}


async def search_tickers(query: str) -> List[Dict[str, str]]:
    """Search for tickers matching query."""
    try:
        # Use yfinance search
        results = yf.Search(query, max_results=10)
        tickers = []
        for r in results.quotes:
            tickers.append({
                'symbol': r.get('symbol', ''),
                'name': r.get('longname') or r.get('shortname', ''),
                'exchange': r.get('exchange', ''),
                'type': r.get('quoteType', ''),
            })
        return tickers
    except Exception as e:
        logger.error(f"Error searching tickers for {query}: {e}")
        return []


async def get_multiple_quotes(symbols: List[str]) -> Dict[str, QuoteData]:
    """Get quotes for multiple symbols efficiently."""
    results = {}
    for symbol in symbols:
        try:
            results[symbol.upper()] = await get_quote(symbol)
        except Exception as e:
            logger.warning(f"Failed to get quote for {symbol}: {e}")
    return results
