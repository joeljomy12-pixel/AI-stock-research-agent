import logging
from typing import Optional, List, Dict, Any

import pandas as pd
import yfinance as yf
from cachetools import TTLCache

from app.models.schemas import QuoteData, PricePoint, HistoricalData, TimeFrame
from app.core.config import settings

logger = logging.getLogger(__name__)

quote_cache = TTLCache(maxsize=100, ttl=settings.cache_ttl_quote)
history_cache = TTLCache(maxsize=100, ttl=300)
stats_cache = TTLCache(maxsize=100, ttl=300)


def _safe_get(info: dict, key: str, default=None):
    try:
        value = info.get(key, default)

        if value is None:
            return default

        if isinstance(value, float) and pd.isna(value):
            return default

        return value
    except Exception:
        return default


def _get_ticker(symbol: str):
    return yf.Ticker(symbol.upper())


async def get_quote(symbol: str) -> QuoteData:
    """
    Get current stock quote.

    Yahoo Finance can return HTTP 429 when rate-limited.
    This function converts those failures into a clean error instead
    of allowing a JSON parsing error to reach the frontend.
    """

    symbol = symbol.upper().strip()
    cache_key = f"quote_{symbol}"

    if cache_key in quote_cache:
        return quote_cache[cache_key]

    try:
        ticker = _get_ticker(symbol)

        # Yahoo's ticker.info endpoint is the part most likely to
        # receive a 429 response.
        info = ticker.info

        if not info:
            raise ValueError(
                f"Unable to fetch quote data for {symbol}. "
                "Yahoo Finance returned no data."
            )

        price = _safe_get(info, "regularMarketPrice")

        # Some Yahoo responses don't contain regularMarketPrice.
        # Try currentPrice as a fallback.
        if price is None:
            price = _safe_get(info, "currentPrice")

        if price is None:
            raise ValueError(
                f"Unable to fetch quote data for {symbol}. "
                "Yahoo Finance did not return a current price."
            )

        quote = QuoteData(
            symbol=symbol,
            name=_safe_get(info, "longName", symbol),
            sector=_safe_get(info, "sector"),
            industry=_safe_get(info, "industry"),

            price=float(price),

            change=float(
                _safe_get(info, "regularMarketChange", 0) or 0
            ),

            change_percent=float(
                _safe_get(info, "regularMarketChangePercent", 0) or 0
            ),

            volume=int(
                _safe_get(info, "regularMarketVolume", 0) or 0
            ),

            avg_volume=int(
                _safe_get(info, "averageVolume", 0) or 0
            ),

            market_cap=_safe_get(info, "marketCap"),

            day_high=float(
                _safe_get(info, "regularMarketDayHigh", price) or price
            ),

            day_low=float(
                _safe_get(info, "regularMarketDayLow", price) or price
            ),

            year_high=float(
                _safe_get(info, "fiftyTwoWeekHigh", price) or price
            ),

            year_low=float(
                _safe_get(info, "fiftyTwoWeekLow", price) or price
            ),

            pe_ratio=_safe_get(info, "trailingPE"),

            dividend_yield=_safe_get(info, "dividendYield"),
        )

        quote_cache[cache_key] = quote
        return quote

    except Exception as e:
        error_text = str(e).lower()

        if "429" in error_text or "too many requests" in error_text:
            logger.error(
                f"Yahoo Finance rate limit reached for {symbol}"
            )

            raise ValueError(
                f"Unable to fetch quote data for {symbol}. "
                "Yahoo Finance is temporarily rate-limiting requests. "
                "Please try again shortly."
            )

        logger.error(
            f"Error fetching quote for {symbol}: {e}"
        )

        raise ValueError(
            f"Unable to fetch quote data for {symbol}. "
            "Yahoo Finance may be temporarily unavailable."
        )


async def get_historical(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.MONTH,
    period: Optional[str] = None,
) -> HistoricalData:

    symbol = symbol.upper().strip()
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

    interval_map = {
        "1d": "5m",
        "5d": "15m",
        "1mo": "1d",
        "3mo": "1d",
        "1y": "1d",
    }

    yf_period = period or period_map.get(timeframe, "1mo")
    interval = interval_map.get(yf_period, "1d")

    try:
        ticker = _get_ticker(symbol)

        hist = ticker.history(
            period=yf_period,
            interval=interval,
            auto_adjust=False,
            actions=False,
        )

        if hist is None or hist.empty:
            raise ValueError(
                f"No historical data available for {symbol}."
            )

        data_points = []

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
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"] or 0),
                    )
                )
            except Exception as row_error:
                logger.warning(
                    f"Skipping invalid historical row for {symbol}: "
                    f"{row_error}"
                )

        if not data_points:
            raise ValueError(
                f"No usable historical data available for {symbol}."
            )

        result = HistoricalData(
            symbol=symbol,
            timeframe=timeframe,
            data=data_points,
        )

        history_cache[cache_key] = result

        return result

    except Exception as e:
        error_text = str(e).lower()

        if "429" in error_text or "too many requests" in error_text:
            logger.error(
                f"Yahoo Finance rate limit reached while fetching "
                f"historical data for {symbol}"
            )

            raise ValueError(
                f"Unable to fetch historical data for {symbol}. "
                "Yahoo Finance is temporarily rate-limiting requests."
            )

        logger.error(
            f"Error fetching historical data for {symbol}: {e}"
        )

        raise ValueError(
            f"Unable to fetch historical data for {symbol}."
        )


async def get_key_stats(symbol: str) -> Dict[str, Any]:

    symbol = symbol.upper().strip()
    cache_key = f"stats_{symbol}"

    if cache_key in stats_cache:
        return stats_cache[cache_key]

    try:
        ticker = _get_ticker(symbol)
        info = ticker.info

        if not info:
            return {}

        stats = {
            "beta": _safe_get(info, "beta"),
            "shares_outstanding": _safe_get(
                info, "sharesOutstanding"
            ),
            "float_shares": _safe_get(
                info, "floatShares"
            ),
            "short_ratio": _safe_get(
                info, "shortRatio"
            ),
            "short_percent": _safe_get(
                info, "shortPercentOfFloat"
            ),
            "held_insiders": _safe_get(
                info, "heldPercentInsiders"
            ),
            "held_institutions": _safe_get(
                info, "heldPercentInstitutions"
            ),
            "book_value": _safe_get(
                info, "bookValue"
            ),
            "price_to_book": _safe_get(
                info, "priceToBook"
            ),
            "enterprise_value": _safe_get(
                info, "enterpriseValue"
            ),
            "ev_to_revenue": _safe_get(
                info, "enterpriseToRevenue"
            ),
            "ev_to_ebitda": _safe_get(
                info, "enterpriseToEbitda"
            ),
            "profit_margins": _safe_get(
                info, "profitMargins"
            ),
            "operating_margins": _safe_get(
                info, "operatingMargins"
            ),
            "return_on_equity": _safe_get(
                info, "returnOnEquity"
            ),
            "return_on_assets": _safe_get(
                info, "returnOnAssets"
            ),
            "revenue_growth": _safe_get(
                info, "revenueGrowth"
            ),
            "earnings_growth": _safe_get(
                info, "earningsGrowth"
            ),
            "current_ratio": _safe_get(
                info, "currentRatio"
            ),
            "quick_ratio": _safe_get(
                info, "quickRatio"
            ),
            "debt_to_equity": _safe_get(
                info, "debtToEquity"
            ),
            "total_cash": _safe_get(
                info, "totalCash"
            ),
            "total_debt": _safe_get(
                info, "totalDebt"
            ),
            "operating_cash_flow": _safe_get(
                info, "operatingCashflow"
            ),
            "free_cash_flow": _safe_get(
                info, "freeCashflow"
            ),
        }

        stats_cache[cache_key] = stats

        return stats

    except Exception as e:
        logger.error(
            f"Error fetching key stats for {symbol}: {e}"
        )

        return {}


async def search_tickers(
    query: str,
) -> List[Dict[str, str]]:

    try:
        query = query.strip()

        if not query:
            return []

        results = yf.Search(
            query,
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
                        "exchange", ""
                    ),
                    "type": result.get(
                        "quoteType", ""
                    ),
                }
            )

        return tickers

    except Exception as e:
        logger.error(
            f"Error searching tickers for {query}: {e}"
        )

        return []


async def get_multiple_quotes(
    symbols: List[str],
) -> Dict[str, QuoteData]:

    results = {}

    for symbol in symbols:
        symbol = symbol.upper().strip()

        if not symbol:
            continue

        try:
            results[symbol] = await get_quote(symbol)

        except Exception as e:
            logger.warning(
                f"Failed to get quote for {symbol}: {e}"
            )

    return results
