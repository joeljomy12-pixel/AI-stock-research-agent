"""
Financial Modeling Prep (FMP) Service
Provides reliable financial data as fallback when yfinance fails.
Uses both v3 (legacy) and stable endpoints for compatibility.
Free tier: 250 requests/day, requires API key.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
from cachetools import TTLCache

from app.models.schemas import QuoteData, HistoricalData, FundamentalsData, PricePoint, TimeFrame
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cache
fmp_quote_cache = TTLCache(maxsize=100, ttl=60)
fmp_fundamentals_cache = TTLCache(maxsize=50, ttl=900)
fmp_historical_cache = TTLCache(maxsize=100, ttl=300)

# Try both v3 (legacy) and stable endpoints
BASE_URL_V3 = "https://financialmodelingprep.com/api/v3"
BASE_URL_STABLE = "https://financialmodelingprep.com/stable"


async def _get_api_key() -> Optional[str]:
    """Get FMP API key from settings."""
    return settings.fmp_api_key if settings.fmp_api_key else None


async def _make_request_v3(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """Make request to FMP v3 API (legacy)."""
    api_key = await _get_api_key()
    if not api_key:
        logger.warning("FMP_API_KEY not configured, skipping FMP")
        return None

    params = params or {}
    params["apikey"] = api_key

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BASE_URL_V3}/{endpoint}", params=params)
            if response.status_code == 429:
                logger.warning("FMP v3 rate limited")
                return None
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"FMP v3 request error for {endpoint}: {e}")
            return None


async def _make_request_stable(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """Make request to FMP stable API (new)."""
    api_key = await _get_api_key()
    if not api_key:
        logger.warning("FMP_API_KEY not configured, skipping FMP stable")
        return None

    params = params or {}
    params["apikey"] = api_key

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BASE_URL_STABLE}/{endpoint}", params=params)
            if response.status_code == 429:
                logger.warning("FMP stable rate limited")
                return None
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"FMP stable request error for {endpoint}: {e}")
            return None


async def _make_request(endpoint: str, params: Dict = None) -> Optional[Dict]:
    """Try v3 first, then stable."""
    # Try v3 first
    result = await _make_request_v3(endpoint, params)
    if result is not None:
        return result
    # Try stable
    return await _make_request_stable(endpoint, params)


def _safe_get(d: dict, key: str, default=None):
    """Safely get value from dict."""
    val = d.get(key, default)
    if val is None or (isinstance(val, float) and val != val):  # NaN check
        return default
    return val


async def get_quote_fmp(symbol: str) -> Optional[QuoteData]:
    """Get quote from FMP."""
    cache_key = f"fmp_quote_{symbol.upper()}"
    if cache_key in fmp_quote_cache:
        return fmp_quote_cache[cache_key]

    # Try v3 quote endpoint
    data = await _make_request_v3(f"quote/{symbol.upper()}")
    if data and isinstance(data, list) and len(data) > 0:
        q = data[0]
        quote = QuoteData(
            symbol=symbol.upper(),
            name=_safe_get(q, 'name', symbol.upper()),
            sector=_safe_get(q, 'sector'),
            industry=_safe_get(q, 'industry'),
            price=float(_safe_get(q, 'price', 0)),
            change=float(_safe_get(q, 'change', 0)),
            change_percent=float(_safe_get(q, 'changesPercentage', 0)),
            volume=int(_safe_get(q, 'volume', 0)),
            avg_volume=int(_safe_get(q, 'avgVolume', 0)),
            market_cap=_safe_get(q, 'marketCap'),
            day_high=float(_safe_get(q, 'dayHigh', 0)),
            day_low=float(_safe_get(q, 'dayLow', 0)),
            year_high=float(_safe_get(q, 'yearHigh', 0)),
            year_low=float(_safe_get(q, 'yearLow', 0)),
            pe_ratio=_safe_get(q, 'pe'),
            dividend_yield=_safe_get(q, 'dividendYield'),
        )
        fmp_quote_cache[cache_key] = quote
        return quote

    # Try stable quote endpoint
    data = await _make_request_stable(f"quote/{symbol.upper()}")
    if data and isinstance(data, list) and len(data) > 0:
        q = data[0]
        quote = QuoteData(
            symbol=symbol.upper(),
            name=_safe_get(q, 'name', symbol.upper()),
            sector=_safe_get(q, 'sector'),
            industry=_safe_get(q, 'industry'),
            price=float(_safe_get(q, 'price', 0)),
            change=float(_safe_get(q, 'change', 0)),
            change_percent=float(_safe_get(q, 'changesPercentage', 0)),
            volume=int(_safe_get(q, 'volume', 0)),
            avg_volume=int(_safe_get(q, 'avgVolume', 0)),
            market_cap=_safe_get(q, 'marketCap'),
            day_high=float(_safe_get(q, 'dayHigh', 0)),
            day_low=float(_safe_get(q, 'dayLow', 0)),
            year_high=float(_safe_get(q, 'yearHigh', 0)),
            year_low=float(_safe_get(q, 'yearLow', 0)),
            pe_ratio=_safe_get(q, 'pe'),
            dividend_yield=_safe_get(q, 'dividendYield'),
        )
        fmp_quote_cache[cache_key] = quote
        return quote

    # Try stable quote-short endpoint
    data = await _make_request_stable(f"quote-short/{symbol.upper()}")
    if data and isinstance(data, list) and len(data) > 0:
        q = data[0]
        quote = QuoteData(
            symbol=symbol.upper(),
            name=_safe_get(q, 'name', symbol.upper()),
            sector=_safe_get(q, 'sector'),
            industry=_safe_get(q, 'industry'),
            price=float(_safe_get(q, 'price', 0)),
            change=float(_safe_get(q, 'change', 0)),
            change_percent=float(_safe_get(q, 'changesPercentage', 0)),
            volume=int(_safe_get(q, 'volume', 0)),
            avg_volume=0,
            market_cap=_safe_get(q, 'marketCap'),
            day_high=0.0,
            day_low=0.0,
            year_high=0.0,
            year_low=0.0,
            pe_ratio=_safe_get(q, 'pe'),
            dividend_yield=_safe_get(q, 'dividendYield'),
        )
        fmp_quote_cache[cache_key] = quote
        return quote

    return None


async def get_historical_fmp(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.MONTH
) -> Optional[HistoricalData]:
    """Get historical data from FMP."""
    cache_key = f"fmp_hist_{symbol.upper()}_{timeframe.value}"
    if cache_key in fmp_historical_cache:
        return fmp_historical_cache[cache_key]

    # Map timeframe to FMP period
    period_map = {
        TimeFrame.DAY: "1day",
        TimeFrame.WEEK: "5day",
        TimeFrame.MONTH: "1month",
        TimeFrame.THREE_MONTHS: "3month",
        TimeFrame.YEAR: "1year",
    }
    period = period_map.get(timeframe, "1month")

    # Try v3
    data = await _make_request_v3(f"historical-price-full/{symbol.upper()}", {"timeseries": period})
    if not data or "historical" not in data or not data["historical"]:
        # Try stable
        data = await _make_request_stable(f"historical-price-full/{symbol.upper()}", {"timeseries": period})

    if not data or "historical" not in data or not data["historical"]:
        return None

    data_points = []
    for item in data["historical"][:200]:  # Limit points
        try:
            data_points.append(PricePoint(
                timestamp=datetime.strptime(item["date"], "%Y-%m-%d"),
                open=float(item["open"]),
                high=float(item["high"]),
                low=float(item["low"]),
                close=float(item["close"]),
                volume=int(item["volume"]),
            ))
        except Exception:
            continue

    if not data_points:
        return None

    # Reverse to chronological order
    data_points.reverse()

    result = HistoricalData(
        symbol=symbol.upper(),
        timeframe=timeframe,
        data=data_points,
    )

    fmp_historical_cache[cache_key] = result
    return result


async def get_fundamentals_fmp(symbol: str) -> Optional[FundamentalsData]:
    """Get fundamentals from FMP."""
    cache_key = f"fmp_fund_{symbol.upper()}"
    if cache_key in fmp_fundamentals_cache:
        return fmp_fundamentals_cache[cache_key]

    # Get profile for company info - try v3 then stable
    profile_data = await _make_request_v3(f"profile/{symbol.upper()}")
    if not profile_data or not isinstance(profile_data, list) or len(profile_data) == 0:
        profile_data = await _make_request_stable(f"profile/{symbol.upper()}")
    if not profile_data or not isinstance(profile_data, list) or len(profile_data) == 0:
        return None
    profile = profile_data[0]

    # Get financial ratios
    ratios_data = await _make_request_v3(f"ratios/{symbol.upper()}")
    if not ratios_data or not isinstance(ratios_data, list) or len(ratios_data) == 0:
        ratios_data = await _make_request_stable(f"ratios/{symbol.upper()}")
    ratios = ratios_data[0] if ratios_data and isinstance(ratios_data, list) and len(ratios_data) > 0 else {}

    # Get key metrics
    metrics_data = await _make_request_v3(f"key-metrics/{symbol.upper()}")
    if not metrics_data or not isinstance(metrics_data, list) or len(metrics_data) == 0:
        metrics_data = await _make_request_stable(f"key-metrics/{symbol.upper()}")
    metrics = metrics_data[0] if metrics_data and isinstance(metrics_data, list) and len(metrics_data) > 0 else {}

    # Get income statement
    income_data = await _make_request_v3(f"income-statement/{symbol.upper()}", {"period": "annual", "limit": 1})
    if not income_data or not isinstance(income_data, list) or len(income_data) == 0:
        income_data = await _make_request_stable(f"income-statement/{symbol.upper()}", {"period": "annual", "limit": 1})
    income = income_data[0] if income_data and isinstance(income_data, list) and len(income_data) > 0 else {}

    # Get balance sheet
    bs_data = await _make_request_v3(f"balance-sheet-statement/{symbol.upper()}", {"period": "annual", "limit": 1})
    if not bs_data or not isinstance(bs_data, list) or len(bs_data) == 0:
        bs_data = await _make_request_stable(f"balance-sheet-statement/{symbol.upper()}", {"period": "annual", "limit": 1})
    bs = bs_data[0] if bs_data and isinstance(bs_data, list) and len(bs_data) > 0 else {}

    # Get cash flow
    cf_data = await _make_request_v3(f"cash-flow-statement/{symbol.upper()}", {"period": "annual", "limit": 1})
    if not cf_data or not isinstance(cf_data, list) or len(cf_data) == 0:
        cf_data = await _make_request_stable(f"cash-flow-statement/{symbol.upper()}", {"period": "annual", "limit": 1})
    cf = cf_data[0] if cf_data and isinstance(cf_data, list) and len(cf_data) > 0 else {}

    # Calculate derived metrics
    revenue = _safe_get(income, 'revenue')
    gross_profit = _safe_get(income, 'grossProfit')
    operating_income = _safe_get(income, 'operatingIncome')
    net_income = _safe_get(income, 'netIncome')

    total_assets = _safe_get(bs, 'totalAssets')
    total_liabilities = _safe_get(bs, 'totalLiabilities')
    total_equity = _safe_get(bs, 'totalStockholdersEquity')
    cash = _safe_get(bs, 'cashAndCashEquivalents')
    total_debt = _safe_get(bs, 'totalDebt')

    operating_cash_flow = _safe_get(cf, 'operatingCashFlow')
    free_cash_flow = _safe_get(cf, 'freeCashFlow')

    gross_margin = (gross_profit / revenue * 100) if revenue and gross_profit else None
    operating_margin = (operating_income / revenue * 100) if revenue and operating_income else None
    net_margin = (net_income / revenue * 100) if revenue and net_income else None
    fcf_margin = (free_cash_flow / revenue * 100) if revenue and free_cash_flow else None
    debt_to_equity = (total_debt / total_equity) if total_debt and total_equity else None
    current_ratio = _safe_get(ratios, 'currentRatio')
    roe = _safe_get(ratios, 'returnOnEquity')
    roa = _safe_get(ratios, 'returnOnAssets')

    fundamentals = FundamentalsData(
        symbol=symbol.upper(),
        company_name=_safe_get(profile, 'companyName', symbol.upper()),
        sector=_safe_get(profile, 'sector', 'N/A'),
        industry=_safe_get(profile, 'industry', 'N/A'),
        market_cap=_safe_get(profile, 'mktCap'),
        enterprise_value=_safe_get(profile, 'enterpriseValue'),

        # Income Statement
        revenue=revenue,
        revenue_growth_yoy=_safe_get(metrics, 'revenueGrowth') * 100 if _safe_get(metrics, 'revenueGrowth') else None,
        gross_profit=gross_profit,
        gross_margin=gross_margin,
        operating_income=operating_income,
        operating_margin=operating_margin,
        net_income=net_income,
        net_margin=net_margin,
        eps=_safe_get(income, 'eps'),
        eps_growth_yoy=_safe_get(metrics, 'epsGrowth') * 100 if _safe_get(metrics, 'epsGrowth') else None,

        # Balance Sheet
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        cash_and_equivalents=cash,
        total_debt=total_debt,
        debt_to_equity=debt_to_equity,
        current_ratio=current_ratio,

        # Cash Flow
        operating_cash_flow=operating_cash_flow,
        free_cash_flow=free_cash_flow,
        fcf_margin=fcf_margin,

        # Valuation
        pe_ratio=_safe_get(ratios, 'priceEarningsRatio'),
        forward_pe=_safe_get(ratios, 'forwardPE'),
        peg_ratio=_safe_get(ratios, 'pegRatio'),
        price_to_sales=_safe_get(ratios, 'priceToSalesRatio'),
        price_to_book=_safe_get(ratios, 'priceToBookRatio'),
        ev_to_ebitda=_safe_get(ratios, 'enterpriseValueOverEBITDA'),

        # Profitability
        roe=roe * 100 if roe else None,
        roa=roa * 100 if roe else None,
        roic=_safe_get(ratios, 'returnOnInvestedCapital') * 100 if _safe_get(ratios, 'returnOnInvestedCapital') else None,

        # Analyst
        analyst_rating=None,
        price_target=None,
        num_analysts=None,

        period="TTM",
        updated_at=datetime.now(),
    )

    fmp_fundamentals_cache[cache_key] = fundamentals
    return fundamentals


async def get_key_stats_fmp(symbol: str) -> Dict[str, Any]:
    """Get key stats from FMP."""
    ratios_data = await _make_request_v3(f"ratios/{symbol.upper()}")
    if not ratios_data or not isinstance(ratios_data, list) or len(ratios_data) == 0:
        ratios_data = await _make_request_stable(f"ratios/{symbol.upper()}")
    ratios = ratios_data[0] if ratios_data and isinstance(ratios_data, list) and len(ratios_data) > 0 else {}

    metrics_data = await _make_request_v3(f"key-metrics/{symbol.upper()}")
    if not metrics_data or not isinstance(metrics_data, list) or len(metrics_data) == 0:
        metrics_data = await _make_request_stable(f"key-metrics/{symbol.upper()}")
    metrics = metrics_data[0] if metrics_data and isinstance(metrics_data, list) and len(metrics_data) > 0 else {}

    profile_data = await _make_request_v3(f"profile/{symbol.upper()}")
    if not profile_data or not isinstance(profile_data, list) or len(profile_data) == 0:
        profile_data = await _make_request_stable(f"profile/{symbol.upper()}")
    profile = profile_data[0] if profile_data and isinstance(profile_data, list) and len(profile_data) > 0 else {}

    stats = {
        'beta': _safe_get(ratios, 'beta'),
        'shares_outstanding': _safe_get(profile, 'sharesOutstanding'),
        'float_shares': _safe_get(profile, 'floatShares'),
        'short_ratio': None,
        'short_percent': None,
        'held_insiders': None,
        'held_institutions': None,
        'book_value': _safe_get(metrics, 'bookValuePerShare'),
        'price_to_book': _safe_get(ratios, 'priceToBookRatio'),
        'enterprise_value': _safe_get(profile, 'enterpriseValue'),
        'ev_to_revenue': _safe_get(ratios, 'enterpriseValueOverRevenue'),
        'ev_to_ebitda': _safe_get(ratios, 'enterpriseValueOverEBITDA'),
        'profit_margins': _safe_get(ratios, 'netProfitMargin'),
        'operating_margins': _safe_get(ratios, 'operatingProfitMargin'),
        'return_on_equity': _safe_get(ratios, 'returnOnEquity'),
        'return_on_assets': _safe_get(ratios, 'returnOnAssets'),
        'revenue_growth': _safe_get(metrics, 'revenueGrowth'),
        'earnings_growth': _safe_get(metrics, 'epsGrowth'),
        'current_ratio': _safe_get(ratios, 'currentRatio'),
        'quick_ratio': _safe_get(ratios, 'quickRatio'),
        'debt_to_equity': _safe_get(ratios, 'debtEquityRatio'),
        'total_cash': _safe_get(profile, 'cashAndCashEquivalents'),
        'total_debt': _safe_get(profile, 'totalDebt'),
        'operating_cash_flow': None,
        'free_cash_flow': None,
    }

    return stats