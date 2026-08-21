import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import pandas as pd
import yfinance as yf
from cachetools import TTLCache

from app.models.schemas import QuoteData, PricePoint, HistoricalData, TimeFrame
from app.core.config import settings

logger = logging.getLogger(__name__)

# Longer caches help prevent Yahoo rate limiting on Render.
quote_cache = TTLCache(
    maxsize=100,
    ttl=max(getattr(settings, "cache_ttl_quote", 60), 120),
)

history_cache = TTLCache(
    maxsize=100,
    ttl=600,
)

stats_cache = TTLCache(
    maxsize=100,
    ttl=600,
)


def _safe_get(info: dict, key: str, default=None):
    """Safely get a value from yfinance."""
    try:
        value = info.get(key, default)

        if value is None:
            return default

        if isinstance(value, float) and pd.isna(value):
            return default

        return value

    except Exception:
        return default


def _to_float(value, default=0.0):
    """Safely convert a value to float."""
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    """Safely convert a value to int."""
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


async def _get_info_with_retry(symbol: str, retries: int = 3) -> dict:
    """
    Fetch ticker.info with retry/backoff.

    Yahoo sometimes returns HTTP 429 when Render makes too many
    requests. Waiting between attempts reduces the chance of
    immediately hitting the rate limit again.
    """
    symbol = symbol.upper()

    for attempt in range(retries):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if isinstance(info, dict) and info:
                return info

            logger.warning(
                "Yahoo returned empty info for %s (attempt %s/%s)",
                symbol,
                attempt + 1,
                retries,
            )

        except Exception as e:
            error_text = str(e).lower()

            if "429" in error_text or "too many requests" in error_text:
                logger.warning(
                    "Yahoo rate limited %s (attempt %s/%s)",
                    symbol,
                    attempt + 1,
                    retries,
                )
            else:
                logger.warning(
                    "Yahoo info request failed for %s (attempt %s/%s): %s",
                    symbol,
                    attempt + 1,
                    retries,
                    e,
                )

        if attempt < retries - 1:
            await asyncio.sleep(2 * (attempt + 1))

    return {}


async def _get_history_with_retry(
    symbol: str,
    period: str,
    interval: str,
    retries: int = 3,
) -> pd.DataFrame:
    """Fetch historical data with retry/backoff."""
    symbol = symbol.upper()

    for attempt in range(retries):
        try:
            ticker = yf.Ticker(symbol)

            hist = ticker.history(
                period=period,
                interval=interval,
                auto_adjust=False,
                actions=False,
            )

            if hist is not None and not hist.empty:
                return hist

            logger.warning(
                "Yahoo returned empty history for %s (attempt %s/%s)",
                symbol,
                attempt + 1,
                retries,
            )

        except Exception as e:
            error_text = str(e).lower()

            if "429" in error_text or "too many requests" in error_text:
                logger.warning(
                    "Yahoo rate limited historical request for %s",
                    symbol,
                )
            else:
                logger.warning(
                    "Historical request failed for %s: %s",
                    symbol,
                    e,
                )

        if attempt < retries - 1:
            await asyncio.sleep(2 * (attempt + 1))

    return pd.DataFrame()


async def get_quote(symbol: str) -> QuoteData:
    """Get current quote data safely."""
    symbol = symbol.upper()
    cache_key = f"quote_{symbol}"

    # Return cached result first.
    if cache_key in quote_cache:
        return quote_cache[cache_key]

    try:
        info = await _get_info_with_retry(symbol)

        if not info:
            raise ValueError(
                f"Yahoo Finance temporarily unavailable for {symbol}. "
                "Please try again in a moment."
            )

        price = _safe_get(info, "regularMarketPrice")

        # Some Yahoo responses don't contain regularMarketPrice.
        # Try currentPrice as a fallback.
        if price is None:
            price = _safe_get(info, "currentPrice")

        if price is None:
            raise ValueError(f"No current price available for {symbol}")

        change = _safe_get(
            info,
            "regularMarketChange",
            _safe_get(info, "change", 0),
        )

        change_percent = _safe_get(
            info,
            "regularMarketChangePercent",
            _safe_get(info, "changePercent", 0),
        )

        # yfinance generally returns this as a percentage already.
        change_percent = _to_float(change_percent)

        quote = QuoteData(
            symbol=symbol,
            name=_safe_get(info, "longName", symbol),
            sector=_safe_get(info, "sector"),
            industry=_safe_get(info, "industry"),

            price=_to_float(price),
            change=_to_float(change),
            change_percent=change_percent,

            volume=_to_int(
                _safe_get(info, "regularMarketVolume", 0)
            ),
            avg_volume=_to_int(
                _safe_get(info, "averageVolume", 0)
            ),

            market_cap=_safe_get(info, "marketCap"),

            day_high=_to_float(
                _safe_get(info, "regularMarketDayHigh", 0)
            ),
            day_low=_to_float(
                _safe_get(info, "regularMarketDayLow", 0)
            ),

            year_high=_to_float(
                _safe_get(info, "fiftyTwoWeekHigh", 0)
            ),
            year_low=_to_float(
                _safe_get(info, "fiftyTwoWeekLow", 0)
            ),

            pe_ratio=_safe_get(info, "trailingPE"),
            dividend_yield=_safe_get(info, "dividendYield"),
        )

        quote_cache[cache_key] = quote

        return quote

    except Exception as e:
        logger.error(
            "Error fetching quote for %s: %s",
            symbol,
            e,
        )
        raise


async def get_historical(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.MONTH,
    period: Optional[str] = None,
) -> HistoricalData:
    """Get historical price data safely."""
    symbol = symbol.upper()

    cache_key = f"hist_{symbol}_{timeframe.value}"

    if cache_key in history_cache:
        return history_cache[cache_key]

    period_map = {
        TimeFrame.DAY: "1d",
        TimeFrame.WEEK: "5d",
        TimeFrame.MONTH: "1mo",
        TimeFrame.THREE_MONTHS: "3mo",
        TimeFrame.YEAR: "1y",
    }

    yf_period = period or period_map.get(timeframe, "1mo")

    interval_map = {
        "1d": "5m",
        "5d": "15m",
        "1mo": "1d",
        "3mo": "1d",
        "1y": "1d",
    }

    interval = interval_map.get(yf_period, "1d")

    try:
        hist = await _get_history_with_retry(
            symbol,
            yf_period,
            interval,
        )

        if hist.empty:
            # Try a safer daily fallback.
            logger.warning(
                "Primary history request failed for %s. "
                "Trying daily fallback.",
                symbol,
            )

            hist = await _get_history_with_retry(
                symbol,
                yf_period,
                "1d",
                retries=2,
            )

        if hist.empty:
            raise ValueError(
                f"No historical data currently available for {symbol}"
            )

        data_points: List[PricePoint] = []

        for idx, row in hist.iterrows():
            try:
                timestamp = (
                    idx.to_pydatetime()
                    if hasattr(idx, "to_pydatetime")
                    else idx
                )

                data_points.append(
                    PricePoint(
                        timestamp=timestamp,
                        open=_to_float(row.get("Open")),
                        high=_to_float(row.get("High")),
                        low=_to_float(row.get("Low")),
                        close=_to_float(row.get("Close")),
                        volume=_to_int(row.get("Volume")),
                    )
                )

            except Exception as e:
                logger.warning(
                    "Skipping invalid historical row for %s: %s",
                    symbol,
                    e,
                )

        if not data_points:
            raise ValueError(
                f"No usable historical data for {symbol}"
            )

        result = HistoricalData(
            symbol=symbol,
            timeframe=timeframe,
            data=data_points,
        )

        history_cache[cache_key] = result

        return result

    except Exception as e:
        logger.error(
            "Error fetching historical for %s: %s",
            symbol,
            e,
        )
        raise


async def get_key_stats(symbol: str) -> Dict[str, Any]:
    """Get key statistics for health scoring."""
    symbol = symbol.upper()
    cache_key = f"stats_{symbol}"

    if cache_key in stats_cache:
        return stats_cache[cache_key]

    try:
        info = await _get_info_with_retry(symbol)

        if not info:
            logger.warning(
                "No statistics available for %s",
                symbol,
            )
            return {}

        stats = {
            "beta": _safe_get(info, "beta"),
            "shares_outstanding": _safe_get(
                info,
                "sharesOutstanding",
            ),
            "float_shares": _safe_get(
                info,
                "floatShares",
            ),
            "short_ratio": _safe_get(
                info,
                "shortRatio",
            ),
            "short_percent": _safe_get(
                info,
                "shortPercentOfFloat",
            ),
            "held_insiders": _safe_get(
                info,
                "heldPercentInsiders",
            ),
            "held_institutions": _safe_get(
                info,
                "heldPercentInstitutions",
            ),
            "book_value": _safe_get(
                info,
                "bookValue",
            ),
            "price_to_book": _safe_get(
                info,
                "priceToBook",
            ),
            "enterprise_value": _safe_get(
                info,
                "enterpriseValue",
            ),
            "ev_to_revenue": _safe_get(
                info,
                "enterpriseToRevenue",
            ),
            "ev_to_ebitda": _safe_get(
                info,
                "enterpriseToEbitda",
            ),
            "profit_margins": _safe_get(
                info,
                "profitMargins",
            ),
            "operating_margins": _safe_get(
                info,
                "operatingMargins",
            ),
            "return_on_equity": _safe_get(
                info,
                "returnOnEquity",
            ),
            "return_on_assets": _safe_get(
                info,
                "returnOnAssets",
            ),
            "revenue_growth": _safe_get(
                info,
                "revenueGrowth",
            ),
            "earnings_growth": _safe_get(
                info,
                "earningsGrowth",
            ),
            "current_ratio": _safe_get(
                info,
                "currentRatio",
            ),
            "quick_ratio": _safe_get(
                info,
                "quickRatio",
            ),
            "debt_to_equity": _safe_get(
                info,
                "debtToEquity",
            ),
            "total_cash": _safe_get(
                info,
                "totalCash",
            ),
            "total_debt": _safe_get(
                info,
                "totalDebt",
            ),
            "operating_cash_flow": _safe_get(
                info,
                "operatingCashflow",
            ),
            "free_cash_flow": _safe_get(
                info,
                "freeCashflow",
            ),
        }

        stats_cache[cache_key] = stats

        return stats

    except Exception as e:
        logger.error(
            "Error fetching key stats for %s: %s",
            symbol,
            e,
        )
        return {}


async def search_tickers(query: str) -> List[Dict[str, str]]:
    """Search for stock tickers."""
    try:
        if not query or not query.strip():
            return []

        results = yf.Search(
            query.strip(),
            max_results=10,
        )

        tickers = []

        for result in results.quotes:
            tickers.append(
                {
                    "symbol": result.get("symbol", ""),
                    "name": (
                        result.get("longname")
                        or result.get("shortname")
                        or ""
                    ),
                    "exchange": result.get(
                        "exchange",
                        "",
                    ),
                    "type": result.get(
                        "quoteType",
                        "",
                    ),
                }
            )

        return tickers

    except Exception as e:
        logger.error(
            "Error searching tickers for %s: %s",
            query,
            e,
        )
        return []


async def get_multiple_quotes(
    symbols: List[str],
) -> Dict[str, QuoteData]:
    """Get quotes for multiple symbols."""
    results: Dict[str, QuoteData] = {}

    # Sequential requests are intentional here.
    # Parallel requests can trigger Yahoo's rate limiter.
    for symbol in symbols:
        try:
            clean_symbol = symbol.upper().strip()

            if not clean_symbol:
                continue

            results[clean_symbol] = await get_quote(
                clean_symbol
            )

            # Small delay between uncached requests.
            await asyncio.sleep(0.25)

        except Exception as e:
            logger.warning(
                "Failed to get quote for %s: %s",
                symbol,
                e,
            )

    return results
