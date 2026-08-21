import asyncio
import logging
from typing import Optional, List, Dict, Any

import pandas as pd
import yfinance as yf
from cachetools import TTLCache

from app.models.schemas import (
    QuoteData,
    PricePoint,
    HistoricalData,
    TimeFrame,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# CACHE
# ============================================================

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


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_get(info: dict, key: str, default=None):
    """Safely get a value from a yfinance dictionary."""
    try:
        if not isinstance(info, dict):
            return default

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
        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    """Safely convert a value to int."""
    try:
        if value is None:
            return default

        if pd.isna(value):
            return default

        return int(float(value))

    except (TypeError, ValueError):
        return default


# ============================================================
# YAHOO HELPERS
# ============================================================

async def _get_history_with_retry(
    symbol: str,
    period: str,
    interval: str,
    retries: int = 3,
) -> pd.DataFrame:
    """
    Get historical data from Yahoo with retry/backoff.

    This is intentionally used instead of ticker.info for quotes.
    Yahoo has been returning 429 Too Many Requests on Render.
    """

    symbol = symbol.upper().strip()

    for attempt in range(retries):
        try:
            ticker = yf.Ticker(symbol)

            history = ticker.history(
                period=period,
                interval=interval,
                auto_adjust=False,
                actions=False,
            )

            if history is not None and not history.empty:
                return history

            logger.warning(
                "Yahoo returned empty history for %s "
                "(attempt %s/%s)",
                symbol,
                attempt + 1,
                retries,
            )

        except Exception as e:
            error_text = str(e).lower()

            if (
                "429" in error_text
                or "too many requests" in error_text
                or "rate limit" in error_text
            ):
                logger.warning(
                    "Yahoo rate limit for %s "
                    "(attempt %s/%s)",
                    symbol,
                    attempt + 1,
                    retries,
                )
            else:
                logger.warning(
                    "Yahoo history error for %s "
                    "(attempt %s/%s): %s",
                    symbol,
                    attempt + 1,
                    retries,
                    e,
                )

        if attempt < retries - 1:
            await asyncio.sleep(2 * (attempt + 1))

    return pd.DataFrame()


async def _get_info_with_retry(
    symbol: str,
    retries: int = 1,
) -> dict:
    """
    Get optional company information.

    This is NOT required for the quote to work.
    If Yahoo blocks this request, we simply return {}.
    """

    symbol = symbol.upper().strip()

    for attempt in range(retries):
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if isinstance(info, dict) and info:
                return info

        except Exception as e:
            logger.warning(
                "Optional Yahoo info request failed for %s: %s",
                symbol,
                e,
            )

        if attempt < retries - 1:
            await asyncio.sleep(2)

    return {}


# ============================================================
# QUOTE
# ============================================================

async def get_quote(symbol: str) -> QuoteData:
    """
    Get current stock quote.

    IMPORTANT:
    We use historical price data first instead of ticker.info.
    This avoids making the quote depend on Yahoo's quoteSummary
    endpoint, which has been returning 429 errors on Render.
    """

    symbol = symbol.upper().strip()

    if not symbol:
        raise ValueError("Stock symbol is required")

    cache_key = f"quote_{symbol}"

    # Return cached quote if available.
    if cache_key in quote_cache:
        return quote_cache[cache_key]

    try:
        # --------------------------------------------------------
        # Get price data
        # --------------------------------------------------------

        history = await _get_history_with_retry(
            symbol,
            "5d",
            "1d",
            retries=3,
        )

        if history.empty:
            raise ValueError(
                f"Unable to fetch quote data for {symbol}. "
                "Yahoo Finance may be temporarily "
                "rate-limiting requests."
            )

        # Remove rows without prices.
        history = history.dropna(
            subset=["Close"]
        )

        if history.empty:
            raise ValueError(
                f"No usable price data available for {symbol}"
            )

        # Latest trading day.
        latest = history.iloc[-1]

        price = _to_float(
            latest.get("Close"),
            0,
        )

        if price <= 0:
            raise ValueError(
                f"Invalid price returned for {symbol}"
            )

        # --------------------------------------------------------
        # Calculate change
        # --------------------------------------------------------

        if len(history) >= 2:
            previous_close = _to_float(
                history.iloc[-2].get("Close"),
                price,
            )
        else:
            previous_close = price

        change = price - previous_close

        if previous_close > 0:
            change_percent = (
                change / previous_close
            ) * 100
        else:
            change_percent = 0.0

        # --------------------------------------------------------
        # Volume
        # --------------------------------------------------------

        volume = _to_int(
            latest.get("Volume"),
            0,
        )

        if "Volume" in history.columns:
            volumes = pd.to_numeric(
                history["Volume"],
                errors="coerce",
            ).dropna()

            if not volumes.empty:
                avg_volume = int(
                    volumes.mean()
                )
            else:
                avg_volume = volume
        else:
            avg_volume = volume

        # --------------------------------------------------------
        # Day high / low
        # --------------------------------------------------------

        day_high = _to_float(
            latest.get("High"),
            price,
        )

        day_low = _to_float(
            latest.get("Low"),
            price,
        )

        # --------------------------------------------------------
        # Optional company information
        #
        # If this fails because Yahoo is rate limiting us,
        # the quote STILL works.
        # --------------------------------------------------------

        info = await _get_info_with_retry(
            symbol,
            retries=1,
        )

        name = _safe_get(
            info,
            "longName",
            symbol,
        )

        sector = _safe_get(
            info,
            "sector",
            None,
        )

        industry = _safe_get(
            info,
            "industry",
            None,
        )

        market_cap = _safe_get(
            info,
            "marketCap",
            None,
        )

        year_high = _safe_get(
            info,
            "fiftyTwoWeekHigh",
            price,
        )

        year_low = _safe_get(
            info,
            "fiftyTwoWeekLow",
            price,
        )

        pe_ratio = _safe_get(
            info,
            "trailingPE",
            None,
        )

        dividend_yield = _safe_get(
            info,
            "dividendYield",
            None,
        )

        # --------------------------------------------------------
        # Build response
        # --------------------------------------------------------

        quote = QuoteData(
            symbol=symbol,

            name=name,
            sector=sector,
            industry=industry,

            price=price,
            change=change,
            change_percent=change_percent,

            volume=volume,
            avg_volume=avg_volume,

            market_cap=market_cap,

            day_high=day_high,
            day_low=day_low,

            year_high=_to_float(
                year_high,
                price,
            ),

            year_low=_to_float(
                year_low,
                price,
            ),

            pe_ratio=pe_ratio,
            dividend_yield=dividend_yield,
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


# ============================================================
# HISTORICAL DATA
# ============================================================

async def get_historical(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.MONTH,
    period: Optional[str] = None,
) -> HistoricalData:
    """Get historical stock price data."""

    symbol = symbol.upper().strip()

    cache_key = (
        f"hist_{symbol}_{timeframe.value}"
    )

    if cache_key in history_cache:
        return history_cache[cache_key]

    period_map = {
        TimeFrame.DAY: "1d",
        TimeFrame.WEEK: "5d",
        TimeFrame.MONTH: "1mo",
        TimeFrame.THREE_MONTHS: "3mo",
        TimeFrame.YEAR: "1y",
    }

    yf_period = period or period_map.get(
        timeframe,
        "1mo",
    )

    interval_map = {
        "1d": "5m",
        "5d": "15m",
        "1mo": "1d",
        "3mo": "1d",
        "1y": "1d",
    }

    interval = interval_map.get(
        yf_period,
        "1d",
    )

    try:
        history = await _get_history_with_retry(
            symbol,
            yf_period,
            interval,
            retries=3,
        )

        # Fallback to daily data.
        if history.empty:
            logger.warning(
                "Trying daily history fallback for %s",
                symbol,
            )

            history = await _get_history_with_retry(
                symbol,
                yf_period,
                "1d",
                retries=2,
            )

        if history.empty:
            raise ValueError(
                f"No historical data for {symbol}"
            )

        data_points: List[PricePoint] = []

        for timestamp, row in history.iterrows():

            try:
                if hasattr(
                    timestamp,
                    "to_pydatetime",
                ):
                    timestamp = (
                        timestamp.to_pydatetime()
                    )

                data_points.append(
                    PricePoint(
                        timestamp=timestamp,

                        open=_to_float(
                            row.get("Open"),
                        ),

                        high=_to_float(
                            row.get("High"),
                        ),

                        low=_to_float(
                            row.get("Low"),
                        ),

                        close=_to_float(
                            row.get("Close"),
                        ),

                        volume=_to_int(
                            row.get("Volume"),
                        ),
                    )
                )

            except Exception as e:
                logger.warning(
                    "Skipping invalid historical row "
                    "for %s: %s",
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


# ============================================================
# KEY STATISTICS
# ============================================================

async def get_key_stats(
    symbol: str,
) -> Dict[str, Any]:
    """Get statistics used by the health scorer."""

    symbol = symbol.upper().strip()

    cache_key = f"stats_{symbol}"

    if cache_key in stats_cache:
        return stats_cache[cache_key]

    try:
        info = await _get_info_with_retry(
            symbol,
            retries=1,
        )

        if not info:
            logger.warning(
                "No Yahoo statistics available for %s",
                symbol,
            )
            return {}

        stats = {
            "beta": _safe_get(
                info,
                "beta",
            ),

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


# ============================================================
# SEARCH
# ============================================================

async def search_tickers(
    query: str,
) -> List[Dict[str, str]]:
    """Search for stock tickers."""

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
                    "symbol": result.get(
                        "symbol",
                        "",
                    ),

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


# ============================================================
# MULTIPLE QUOTES
# ============================================================

async def get_multiple_quotes(
    symbols: List[str],
) -> Dict[str, QuoteData]:
    """
    Get multiple quotes sequentially.

    Sequential requests are intentional so we don't hammer
    Yahoo with parallel requests and trigger another 429.
    """

    results: Dict[str, QuoteData] = {}

    for symbol in symbols:

        clean_symbol = (
            symbol.upper().strip()
        )

        if not clean_symbol:
            continue

        try:
            results[clean_symbol] = (
                await get_quote(clean_symbol)
            )

            # Small delay between requests.
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.warning(
                "Failed to get quote for %s: %s",
                clean_symbol,
                e,
            )

    return results
