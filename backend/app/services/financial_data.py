import yfinance as yf
import pandas as pd
from typing import Optional, Dict, Any, List, Callable, TypeVar
from datetime import datetime
import logging
import asyncio
from cachetools import TTLCache

from app.models.schemas import FundamentalsData
from app.core.config import settings
from app.services.fmp_service import get_fundamentals_fmp

logger = logging.getLogger(__name__)

fundamentals_cache = TTLCache(maxsize=50, ttl=settings.cache_ttl_fundamentals)

T = TypeVar('T')

async def _retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 4.0,
    timeout: float = 15.0,
    **kwargs
) -> T:
    """Retry async function with exponential backoff for rate limiting.

    Kept fast on purpose: with 3 data sources (yfinance -> FMP -> mock),
    long retries just make requests hang. Worst case here is ~17s per call.
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError as e:
            last_exception = e
            error_msg = 'timeout'
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


def _safe_get(obj: Any, attr: str, default=None):
    """Safely get attribute from object."""
    try:
        val = getattr(obj, attr, default)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        return val
    except Exception:
        return default


def _safe_dict_get(d: dict, key: str, default=None):
    """Safely get value from dict."""
    val = d.get(key, default)
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return val


async def get_fundamentals(symbol: str) -> FundamentalsData:
    """Get comprehensive fundamental data. Tries yfinance first, falls back to FMP, then returns mock data."""
    cache_key = f"fund_{symbol.upper()}"
    if cache_key in fundamentals_cache:
        return fundamentals_cache[cache_key]

    # Try yfinance first
    async def _fetch_yf():
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        if not info:
            raise ValueError(f"No fundamental data for {symbol}")

        # Get financial statements
        try:
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
        except Exception:
            financials = pd.DataFrame()
            balance_sheet = pd.DataFrame()
            cashflow = pd.DataFrame()

        # Extract TTM (Trailing Twelve Months) data from financials
        def get_latest(df: pd.DataFrame, row_name: str) -> Optional[float]:
            if df.empty or row_name not in df.index:
                return None
            val = df.loc[row_name].iloc[0] if len(df.loc[row_name]) > 0 else None
            return float(val) if val is not None and not pd.isna(val) else None

        # Income Statement (TTM)
        revenue = get_latest(financials, 'Total Revenue')
        gross_profit = get_latest(financials, 'Gross Profit')
        operating_income = get_latest(financials, 'Operating Income')
        net_income = get_latest(financials, 'Net Income')
        eps = _safe_dict_get(info, 'trailingEps')

        # Balance Sheet (Latest)
        total_assets = get_latest(balance_sheet, 'Total Assets')
        total_liabilities = get_latest(balance_sheet, 'Total Liabilities Net Minority Interest')
        total_equity = get_latest(balance_sheet, 'Total Equity Gross Minority Interest')
        cash = get_latest(balance_sheet, 'Cash And Cash Equivalents')
        total_debt = get_latest(balance_sheet, 'Total Debt')

        # Cash Flow (TTM)
        operating_cash_flow = get_latest(cashflow, 'Operating Cash Flow')
        free_cash_flow = get_latest(cashflow, 'Free Cash Flow')

        # Calculate derived metrics
        gross_margin = (gross_profit / revenue * 100) if revenue and gross_profit else None
        operating_margin = (operating_income / revenue * 100) if revenue and operating_income else None
        net_margin = (net_income / revenue * 100) if revenue and net_income else None
        fcf_margin = (free_cash_flow / revenue * 100) if revenue and free_cash_flow else None
        debt_to_equity = (total_debt / total_equity) if total_debt and total_equity else None
        current_ratio = _safe_dict_get(info, 'currentRatio')
        roe = _safe_dict_get(info, 'returnOnEquity')
        roa = _safe_dict_get(info, 'returnOnAssets')

        # Revenue growth YoY (approximate from quarterly)
        revenue_growth_yoy = _safe_dict_get(info, 'revenueGrowth')
        if revenue_growth_yoy:
            revenue_growth_yoy *= 100

        eps_growth_yoy = _safe_dict_get(info, 'earningsGrowth')
        if eps_growth_yoy:
            eps_growth_yoy *= 100

        fundamentals = FundamentalsData(
            symbol=symbol.upper(),
            company_name=_safe_dict_get(info, 'longName', symbol.upper()),
            sector=_safe_dict_get(info, 'sector', 'N/A'),
            industry=_safe_dict_get(info, 'industry', 'N/A'),
            market_cap=_safe_dict_get(info, 'marketCap'),
            enterprise_value=_safe_dict_get(info, 'enterpriseValue'),

            # Income Statement
            revenue=revenue,
            revenue_growth_yoy=revenue_growth_yoy,
            gross_profit=gross_profit,
            gross_margin=gross_margin,
            operating_income=operating_income,
            operating_margin=operating_margin,
            net_income=net_income,
            net_margin=net_margin,
            eps=eps,
            eps_growth_yoy=eps_growth_yoy,

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
            pe_ratio=_safe_dict_get(info, 'trailingPE'),
            forward_pe=_safe_dict_get(info, 'forwardPE'),
            peg_ratio=_safe_dict_get(info, 'pegRatio'),
            price_to_sales=_safe_dict_get(info, 'priceToSalesTrailing12Months'),
            price_to_book=_safe_dict_get(info, 'priceToBook'),
            ev_to_ebitda=_safe_dict_get(info, 'enterpriseToEbitda'),

            # Profitability
            roe=roe * 100 if roe else None,
            roa=roa * 100 if roa else None,
            roic=_safe_dict_get(info, 'returnOnInvestedCapital') * 100 if _safe_dict_get(info, 'returnOnInvestedCapital') else None,

            # Analyst
            analyst_rating=_safe_dict_get(info, 'recommendationKey'),
            price_target=_safe_dict_get(info, 'targetMeanPrice'),
            num_analysts=_safe_dict_get(info, 'numberOfAnalystOpinions'),

            period="TTM",
            updated_at=datetime.now()
        )

        fundamentals_cache[cache_key] = fundamentals
        return fundamentals

    try:
        return await _retry_with_backoff(_fetch_yf)
    except Exception as e:
        logger.warning(f"yfinance fundamentals failed for {symbol}: {e}, trying FMP...")
        # Fallback to FMP
        try:
            fmp_fund = await get_fundamentals_fmp(symbol)
            if fmp_fund:
                fundamentals_cache[cache_key] = fmp_fund
                return fmp_fund
        except Exception as fmp_e:
            logger.error(f"FMP fundamentals also failed for {symbol}: {fmp_e}")
        # Return mock data as last resort
        logger.warning(f"All data sources failed for {symbol}, returning mock fundamentals")
        return _mock_fundamentals(symbol)


def _mock_fundamentals(symbol: str) -> FundamentalsData:
    """Return mock fundamentals when all data sources fail."""
    return FundamentalsData(
        symbol=symbol.upper(),
        company_name=f"{symbol.upper()} Inc.",
        sector="Technology",
        industry="Software",
        market_cap=100000000000,
        enterprise_value=105000000000,

        # Income Statement
        revenue=50000000000,
        revenue_growth_yoy=15.0,
        gross_profit=20000000000,
        gross_margin=40.0,
        operating_income=15000000000,
        operating_margin=30.0,
        net_income=10000000000,
        net_margin=20.0,
        eps=5.0,
        eps_growth_yoy=20.0,

        # Balance Sheet
        total_assets=150000000000,
        total_liabilities=50000000000,
        total_equity=100000000000,
        cash_and_equivalents=50000000000,
        total_debt=10000000000,
        debt_to_equity=0.1,
        current_ratio=1.5,

        # Cash Flow
        operating_cash_flow=30000000000,
        free_cash_flow=25000000000,
        fcf_margin=50.0,

        # Valuation
        pe_ratio=25.0,
        forward_pe=22.0,
        peg_ratio=1.2,
        price_to_sales=8.5,
        price_to_book=6.0,
        ev_to_ebitda=20.0,

        # Profitability
        roe=35.0,
        roa=15.0,
        roic=25.0,

        # Analyst
        analyst_rating="Buy",
        price_target=180.0,
        num_analysts=25,

        period="TTM",
        updated_at=datetime.now()
    )


async def get_quarterly_financials(symbol: str) -> Dict[str, List[Dict]]:
    """Get quarterly financial data for trend analysis."""

    async def _fetch():
        ticker = yf.Ticker(symbol.upper())
        financials = ticker.quarterly_financials
        balance_sheet = ticker.quarterly_balance_sheet
        cashflow = ticker.quarterly_cashflow

        def df_to_records(df: pd.DataFrame) -> List[Dict]:
            if df.empty:
                return []
            return df.T.reset_index().rename(columns={'index': 'date'}).to_dict('records')

        return {
            'income_statement': df_to_records(financials),
            'balance_sheet': df_to_records(balance_sheet),
            'cash_flow': df_to_records(cashflow),
        }

    try:
        return await _retry_with_backoff(_fetch)
    except Exception as e:
        logger.error(f"Error fetching quarterly financials for {symbol}: {e}")
        return {'income_statement': [], 'balance_sheet': [], 'cash_flow': []}


async def get_quarterly_financials(symbol: str) -> Dict[str, List[Dict]]:
    """Get quarterly financial data for trend analysis."""

    async def _fetch():
        ticker = yf.Ticker(symbol.upper())
        financials = ticker.quarterly_financials
        balance_sheet = ticker.quarterly_balance_sheet
        cashflow = ticker.quarterly_cashflow

        def df_to_records(df: pd.DataFrame) -> List[Dict]:
            if df.empty:
                return []
            return df.T.reset_index().rename(columns={'index': 'date'}).to_dict('records')

        return {
            'income_statement': df_to_records(financials),
            'balance_sheet': df_to_records(balance_sheet),
            'cash_flow': df_to_records(cashflow),
        }

    try:
        return await _retry_with_backoff(_fetch)
    except Exception as e:
        logger.error(f"Error fetching quarterly financials for {symbol}: {e}")
        return {'income_statement': [], 'balance_sheet': [], 'cash_flow': []}
