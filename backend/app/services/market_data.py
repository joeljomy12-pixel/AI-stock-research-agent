import yfinance as yf
import pandas as pd
from typing import Optional, List, Dict, Any
import logging
from cachetools import TTLCache

from app.models.schemas import QuoteData, PricePoint, HistoricalData, TimeFrame
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Caches
# ---------------------------------------------------------------------------

quote_cache = TTLCache(
    maxsize=100,
    ttl=settings.cache_ttl_quote
)

history_cache = TTLCache(
    maxsize=100,
    ttl=300
)

stats_cache = TTLCache(
    maxsize=100,
    ttl=settings.cache_ttl_quote
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ticker(symbol: str) -> yf.Ticker:
    """Create a yfinance ticker."""
    return yf.Ticker(symbol.upper().strip())


def _safe_get(info: dict, key: str, default=None):
    """Safely retrieve a value from a yfinance dictionary."""
    try:
        if not info:
            return default

        value = info.get(key, default)

        if value is None:
            return default

        if isinstance(value, float) and pd.isna(value):
            return default

        return value

    except Exception:
        return default


def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    try:
        if value is None:
            return default

        if isinstance(value, float) and pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    """Safely convert a value to int."""
    try:
        if value is None:
            return default

        if isinstance(value, float) and pd.isna(value):
            return default

        return int(value)

    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------

async def get_quote(symbol: str) -> QuoteData:
    """
    Get current quote data.

    Uses yfinance .info first and falls back to .fast_info when Yahoo
    blocks the regular info endpoint.
    """

    symbol = symbol.upper().strip()
    cache_key = f"quote_{symbol}"

    # Cache
    if cache_key in quote_cache:
        return quote_cache[cache_key]

    ticker = _get_ticker(symbol)

    info = {}

    # ---------------------------------------------------------------
    # Try normal .info
    # ---------------------------------------------------------------

    try:
        info = ticker.info or {}

    except Exception as e:
        logger.warning(
            f"Yahoo .info failed for {symbol}: {e}"
        )

    # ---------------------------------------------------------------
    # Normal info succeeded
    # ---------------------------------------------------------------

    if info and "regularMarketPrice" in info:

        try:
            price = _safe_float(
                _safe_get(info, "regularMarketPrice")
            )

            previous_close = _safe_float(
                _safe_get(info, "regularMarketPreviousClose"),
                price
            )

            change = _safe_float(
                _safe_get(info, "regularMarketChange"),
                price - previous_close
            )

            # Yahoo's regularMarketChangePercent is already a percentage.
            change_percent = _safe_float(
                _safe_get(info, "regularMarketChangePercent"),
                (
                    (change / previous_close) * 100
                    if previous_close
                    else 0
                )
            )

            quote = QuoteData(
                symbol=symbol,

                name=_safe_get(
                    info,
                    "longName",
                    symbol
                ),

                sector=_safe_get(
                    info,
                    "sector"
                ),

                industry=_safe_get(
                    info,
                    "industry"
                ),

                price=price,

                change=change,

                change_percent=change_percent,

                volume=_safe_int(
                    _safe_get(
                        info,
                        "regularMarketVolume",
                        0
                    )
                ),

                avg_volume=_safe_int(
                    _safe_get(
                        info,
                        "averageVolume",
                        0
                    )
                ),

                market_cap=_safe_get(
                    info,
                    "marketCap"
                ),

                day_high=_safe_float(
                    _safe_get(
                        info,
                        "regularMarketDayHigh",
                        0
                    )
                ),

                day_low=_safe_float(
                    _safe_get(
                        info,
                        "regularMarketDayLow",
                        0
                    )
                ),

                year_high=_safe_float(
                    _safe_get(
                        info,
                        "fiftyTwoWeekHigh",
                        0
                    )
                ),

                year_low=_safe_float(
                    _safe_get(
                        info,
                        "fiftyTwoWeekLow",
                        0
                    )
                ),

                pe_ratio=_safe_get(
                    info,
                    "trailingPE"
                ),

                dividend_yield=_safe_get(
                    info,
                    "dividendYield"
                ),
            )

            quote_cache[cache_key] = quote

            return quote

        except Exception as e:
            logger.error(
                f"Error creating quote from info for {symbol}: {e}"
            )

    # ---------------------------------------------------------------
    # Fallback: fast_info
    # ---------------------------------------------------------------

    logger.warning(
        f"Falling back to Yahoo fast_info for {symbol}"
    )

    try:
        fast_info = ticker.fast_info

        price = _safe_float(
            fast_info.get("last_price", 0)
        )

        previous_close = _safe_float(
            fast_info.get("previous_close", price),
            price
        )

        change = price - previous_close

        change_percent = (
            (change / previous_close) * 100
            if previous_close
            else 0
        )

        if price <= 0:
            raise ValueError(
                f"No valid price returned for {symbol}"
            )

        quote = QuoteData(
            symbol=symbol,

            name=symbol,

            sector=None,

            industry=None,

            price=price,

            change=change,

            change_percent=change_percent,

            volume=_safe_int(
                fast_info.get("last_volume", 0)
            ),

            avg_volume=0,

            market_cap=None,

            day_high=_safe_float(
                fast_info.get("day_high", 0)
            ),

            day_low=_safe_float(
                fast_info.get("day_low", 0)
            ),

            year_high=_safe_float(
                fast_info.get("year_high", 0)
            ),

            year_low=_safe_float(
                fast_info.get("year_low", 0)
            ),

            pe_ratio=None,

            dividend_yield=None,
        )

        quote_cache[cache_key] = quote

        return quote

    except Exception as e:
        logger.error(
            f"Yahoo fast_info also failed for {symbol}: {e}"
        )

        raise ValueError(
            f"Unable to fetch quote data for {symbol}. "
            f"Yahoo Finance may be temporarily rate-limiting requests."
        )


# ---------------------------------------------------------------------------
# Historical data
# ---------------------------------------------------------------------------

async def get_historical(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.MONTH,
    period: Optional[str] = None
) -> HistoricalData:

    symbol = symbol.upper().strip()

    cache_key = f"hist_{symbol}_{timeframe.value}"

    if cache_key in history_cache:
        return history_cache[cache_key]

    try:

        ticker = _get_ticker(symbol)

        # -----------------------------------------------------------
        # Period mapping
        # -----------------------------------------------------------

        period_map = {
            TimeFrame.DAY: "1d",
            TimeFrame.WEEK: "5d",
            TimeFrame.MONTH: "1mo",
            TimeFrame.THREE_MONTHS: "3mo",
            TimeFrame.YEAR: "1y",
        }

        yf_period = period or period_map.get(
            timeframe,
            "1mo"
        )

        # -----------------------------------------------------------
        # Interval mapping
        # -----------------------------------------------------------

        interval_map = {
            "1d": "5m",
            "5d": "15m",
            "1mo": "1d",
            "3mo": "1d",
            "1y": "1d",
        }

        interval = interval_map.get(
            yf_period,
            "1d"
        )

        # -----------------------------------------------------------
        # Fetch history
        # -----------------------------------------------------------

        try:
            hist = ticker.history(
                period=yf_period,
                interval=interval,
                auto_adjust=False
            )

        except Exception as e:
            logger.error(
                f"Yahoo historical request failed for {symbol}: {e}"
            )
            hist = pd.DataFrame()

        # -----------------------------------------------------------
        # If Yahoo gave us nothing, retry with a simpler request
        # -----------------------------------------------------------

        if hist.empty:

            logger.warning(
                f"Retrying historical data for {symbol}"
            )

            try:

                hist = ticker.history(
                    period=yf_period,
                    interval="1d",
                    auto_adjust=False
                )

            except Exception as e:
                logger.error(
                    f"Historical retry failed for {symbol}: {e}"
                )
                hist = pd.DataFrame()

        # -----------------------------------------------------------
        # Still no data
        # -----------------------------------------------------------

        if hist.empty:

            raise ValueError(
                f"No historical data available for {symbol}"
            )

        # -----------------------------------------------------------
        # Convert dataframe to API objects
        # -----------------------------------------------------------

        data_points: List[PricePoint] = []

        for idx, row in hist.iterrows():

            try:

                timestamp = (
                    idx.to_pydatetime()
                    if hasattr(idx, "to_pydatetime")
                    else idx
                )

                open_price = _safe_float(
                    row.get("Open")
                )

                high_price = _safe_float(
                    row.get("High")
                )

                low_price = _safe_float(
                    row.get("Low")
                )

                close_price = _safe_float(
                    row.get("Close")
                )

                volume = _safe_int(
                    row.get("Volume")
                )

                # Skip completely invalid rows
                if close_price <= 0:
                    continue

                data_points.append(
                    PricePoint(
                        timestamp=timestamp,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume
                    )
                )

            except Exception as e:

                logger.warning(
                    f"Skipping invalid historical row for {symbol}: {e}"
                )

        if not data_points:

            raise ValueError(
                f"No valid historical data for {symbol}"
            )

        result = HistoricalData(
            symbol=symbol,
            timeframe=timeframe,
            data=data_points
        )

        history_cache[cache_key] = result

        return result

    except Exception as e:

        logger.error(
            f"Error fetching historical for {symbol}: {e}"
        )

        raise


# ---------------------------------------------------------------------------
# Key statistics
# ---------------------------------------------------------------------------

async def get_key_stats(
    symbol: str
) -> Dict[str, Any]:

    symbol = symbol.upper().strip()

    cache_key = f"stats_{symbol}"

    if cache_key in stats_cache:
        return stats_cache[cache_key]

    try:

        ticker = _get_ticker(symbol)

        try:
            info = ticker.info or {}

        except Exception as e:

            logger.warning(
                f"Yahoo info failed while fetching stats for {symbol}: {e}"
            )

            info = {}

        # If Yahoo is rate limiting us, return an empty dictionary
        # instead of causing the health-score endpoint to crash.

        if not info:

            logger.warning(
                f"No statistics available for {symbol}"
            )

            return {}

        stats = {

            "beta": _safe_get(
                info,
                "beta"
            ),

            "shares_outstanding": _safe_get(
                info,
                "sharesOutstanding"
            ),

            "float_shares": _safe_get(
                info,
                "floatShares"
            ),

            "short_ratio": _safe_get(
                info,
                "shortRatio"
            ),

            "short_percent": _safe_get(
                info,
                "shortPercentOfFloat"
            ),

            "held_insiders": _safe_get(
                info,
                "heldPercentInsiders"
            ),

            "held_institutions": _safe_get(
                info,
                "heldPercentInstitutions"
            ),

            "book_value": _safe_get(
                info,
                "bookValue"
            ),

            "price_to_book": _safe_get(
                info,
                "priceToBook"
            ),

            "enterprise_value": _safe_get(
                info,
                "enterpriseValue"
            ),

            "ev_to_revenue": _safe_get(
                info,
                "enterpriseToRevenue"
            ),

            "ev_to_ebitda": _safe_get(
                info,
                "enterpriseToEbitda"
            ),

            "profit_margins": _safe_get(
                info,
                "profitMargins"
            ),

            "operating_margins": _safe_get(
                info,
                "operatingMargins"
            ),

            "return_on_equity": _safe_get(
                info,
                "returnOnEquity"
            ),

            "return_on_assets": _safe_get(
                info,
                "returnOnAssets"
            ),

            "revenue_growth": _safe_get(
                info,
                "revenueGrowth"
            ),

            "earnings_growth": _safe_get(
                info,
                "earningsGrowth"
            ),

            "current_ratio": _safe_get(
                info,
                "currentRatio"
            ),

            "quick_ratio": _safe_get(
                info,
                "quickRatio"
            ),

            "debt_to_equity": _safe_get(
                info,
                "debtToEquity"
            ),

            "total_cash": _safe_get(
                info,
                "totalCash"
            ),

            "total_debt": _safe_get(
                info,
                "totalDebt"
            ),

            "operating_cash_flow": _safe_get(
                info,
                "operatingCashflow"
            ),

            "free_cash_flow": _safe_get(
                info,
                "freeCashflow"
            ),
        }

        stats_cache[cache_key] = stats

        return stats

    except Exception as e:

        logger.error(
            f"Error fetching key stats for {symbol}: {e}"
        )

        return {}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

async def search_tickers(
    query: str
) -> List[Dict[str, str]]:

    try:

        query = query.strip()

        if not query:
            return []

        results = yf.Search(
            query,
            max_results=10
        )

        tickers = []

        for result in results.quotes:

            try:

                tickers.append(
                    {
                        "symbol": result.get(
                            "symbol",
                            ""
                        ),

                        "name": (
                            result.get("longname")
                            or result.get("shortname")
                            or ""
                        ),

                        "exchange": result.get(
                            "exchange",
                            ""
                        ),

                        "type": result.get(
                            "quoteType",
                            ""
                        ),
                    }
                )

            except Exception:
                continue

        return tickers

    except Exception as e:

        logger.error(
            f"Error searching tickers for {query}: {e}"
        )

        return []


# ---------------------------------------------------------------------------
# Multiple quotes
# ---------------------------------------------------------------------------

async def get_multiple_quotes(
    symbols: List[str]
) -> Dict[str, QuoteData]:

    results: Dict[str, QuoteData] = {}

    for symbol in symbols:

        symbol = symbol.upper().strip()

        if not symbol:
            continue

        try:

            results[symbol] = await get_quote(
                symbol
            )

        except Exception as e:

            logger.warning(
                f"Failed to get quote for {symbol}: {e}"
            )

    return results
