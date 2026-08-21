import logging
import os
from typing import Optional, List, Dict, Any

import httpx
from cachetools import TTLCache

from app.models.schemas import QuoteData, PricePoint, HistoricalData, TimeFrame
from app.core.config import settings

logger = logging.getLogger(__name__)

quote_cache = TTLCache(maxsize=100, ttl=settings.cache_ttl_quote)
history_cache = TTLCache(maxsize=100, ttl=300)
stats_cache = TTLCache(maxsize=100, ttl=300)


def _get_fmp_key():
    """
    Gets the FMP API key from your Render environment variables.
    """
    key = os.getenv("FMP_API_KEY")

    if not key:
        raise ValueError(
            "FMP_API_KEY is missing. Add FMP_API_KEY to your Render "
            "environment variables."
        )

    return key


async def _fmp_get(endpoint: str, params: Dict[str, Any]):
    """
    Make a request to Financial Modeling Prep.
    """
    api_key = _get_fmp_key()

    params = dict(params)
    params["apikey"] = api_key

    url = f"https://financialmodelingprep.com/api/v3/{endpoint}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        raise ValueError(
            f"FMP request failed with HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except Exception:
        raise ValueError("FMP returned an invalid response.")

    if isinstance(data, dict) and data.get("Error Message"):
        raise ValueError(str(data["Error Message"]))

    return data


async def get_quote(symbol: str) -> QuoteData:
    """
    Get current quote from Financial Modeling Prep.
    """

    symbol = symbol.upper().strip()
    cache_key = f"quote_{symbol}"

    if cache_key in quote_cache:
        return quote_cache[cache_key]

    try:
        data = await _fmp_get(
            f"quote/{symbol}",
            {}
        )

        if not data or not isinstance(data, list):
            raise ValueError(
                f"No quote data found for {symbol}."
            )

        item = data[0]

        price = item.get("price")

        if price is None:
            raise ValueError(
                f"FMP did not return a price for {symbol}."
            )

        change = item.get("change") or 0
        change_percent = item.get("changesPercentage") or 0

        quote = QuoteData(
            symbol=symbol,

            name=item.get("name") or symbol,

            sector=None,
            industry=None,

            price=float(price),

            change=float(change),

            change_percent=float(change_percent),

            volume=int(item.get("volume") or 0),

            avg_volume=0,

            market_cap=None,

            day_high=float(
                item.get("dayHigh") or price
            ),

            day_low=float(
                item.get("dayLow") or price
            ),

            year_high=float(
                item.get("yearHigh") or price
            ),

            year_low=float(
                item.get("yearLow") or price
            ),

            pe_ratio=item.get("pe"),

            dividend_yield=None,
        )

        quote_cache[cache_key] = quote

        return quote

    except Exception as e:
        logger.error(
            f"Error fetching FMP quote for {symbol}: {e}"
        )

        raise ValueError(
            f"Unable to fetch quote data for {symbol}: {e}"
        )


async def get_historical(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.MONTH,
    period: Optional[str] = None,
) -> HistoricalData:

    symbol = symbol.upper().strip()

    cache_key = (
        f"hist_{symbol}_{timeframe.value}"
    )

    if cache_key in history_cache:
        return history_cache[cache_key]

    period_map = {
        TimeFrame.DAY: 5,
        TimeFrame.WEEK: 10,
        TimeFrame.MONTH: 40,
        TimeFrame.THREE_MONTHS: 100,
        TimeFrame.YEAR: 370,
    }

    days = period_map.get(
        timeframe,
        40
    )

    try:
        data = await _fmp_get(
            f"historical-price-full/{symbol}",
            {
                "timeseries": days
            }
        )

        historical = data.get("historical", [])

        if not historical:
            raise ValueError(
                f"No historical data found for {symbol}."
            )

        historical.reverse()

        data_points = []

        for row in historical:

            try:
                data_points.append(
                    PricePoint(
                        timestamp=row["date"],

                        open=float(
                            row.get("open") or 0
                        ),

                        high=float(
                            row.get("high") or 0
                        ),

                        low=float(
                            row.get("low") or 0
                        ),

                        close=float(
                            row.get("close") or 0
                        ),

                        volume=int(
                            row.get("volume") or 0
                        ),
                    )
                )

            except Exception as row_error:
                logger.warning(
                    f"Skipping historical row: {row_error}"
                )

        if not data_points:
            raise ValueError(
                f"No usable historical data for {symbol}."
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
            f"Error fetching historical data for {symbol}: {e}"
        )

        raise ValueError(
            f"Unable to fetch historical data for {symbol}: {e}"
        )


async def get_key_stats(
    symbol: str
) -> Dict[str, Any]:

    symbol = symbol.upper().strip()

    cache_key = f"stats_{symbol}"

    if cache_key in stats_cache:
        return stats_cache[cache_key]

    try:

        data = await _fmp_get(
            f"key-metrics-ttm/{symbol}",
            {}
        )

        if not data:
            return {}

        item = data[0] if isinstance(data, list) else data

        stats = {
            "beta": None,
            "shares_outstanding": None,
            "float_shares": None,
            "short_ratio": None,
            "short_percent": None,
            "held_insiders": None,
            "held_institutions": None,

            "book_value": item.get(
                "bookValuePerShareTTM"
            ),

            "price_to_book": item.get(
                "priceToBookRatioTTM"
            ),

            "enterprise_value": item.get(
                "enterpriseValueTTM"
            ),

            "ev_to_revenue": item.get(
                "evToSalesTTM"
            ),

            "ev_to_ebitda": item.get(
                "enterpriseValueOverEBITDATTM"
            ),

            "profit_margins": item.get(
                "netProfitMarginTTM"
            ),

            "operating_margins": item.get(
                "operatingProfitMarginTTM"
            ),

            "return_on_equity": item.get(
                "returnOnEquityTTM"
            ),

            "return_on_assets": item.get(
                "returnOnAssetsTTM"
            ),

            "revenue_growth": None,
            "earnings_growth": None,

            "current_ratio": item.get(
                "currentRatioTTM"
            ),

            "quick_ratio": item.get(
                "quickRatioTTM"
            ),

            "debt_to_equity": item.get(
                "debtToEquityTTM"
            ),

            "total_cash": None,
            "total_debt": None,

            "operating_cash_flow": item.get(
                "operatingCashFlowTTM"
            ),

            "free_cash_flow": item.get(
                "freeCashFlowTTM"
            ),
        }

        stats_cache[cache_key] = stats

        return stats

    except Exception as e:

        logger.error(
            f"Error fetching stats for {symbol}: {e}"
        )

        return {}


async def search_tickers(
    query: str
) -> List[Dict[str, str]]:

    # Keep search simple for now.
    # The important part is that stock quote/historical data
    # no longer depends on Yahoo Finance.

    return []


async def get_multiple_quotes(
    symbols: List[str]
) -> Dict[str, QuoteData]:

    results = {}

    for symbol in symbols:

        try:

            symbol = symbol.upper().strip()

            if symbol:
                results[symbol] = await get_quote(symbol)

        except Exception as e:

            logger.warning(
                f"Failed to get quote for {symbol}: {e}"
            )

    return results
