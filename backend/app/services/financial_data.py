import yfinance as yf
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from cachetools import TTLCache

from app.models.schemas import FundamentalsData
from app.core.config import settings

logger = logging.getLogger(__name__)

fundamentals_cache = TTLCache(maxsize=50, ttl=settings.cache_ttl_fundamentals)


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
    """Get comprehensive fundamental data from yfinance."""
    cache_key = f"fund_{symbol.upper()}"
    if cache_key in fundamentals_cache:
        return fundamentals_cache[cache_key]

    try:
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

    except Exception as e:
        logger.error(f"Error fetching fundamentals for {symbol}: {e}")
        raise


async def get_quarterly_financials(symbol: str) -> Dict[str, List[Dict]]:
    """Get quarterly financial data for trend analysis."""
    try:
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
    except Exception as e:
        logger.error(f"Error fetching quarterly financials for {symbol}: {e}")
        return {'income_statement': [], 'balance_sheet': [], 'cash_flow': []}