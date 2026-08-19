"""
Stock Health Scoring Engine
Calculates health scores from quantitative metrics.
No LLM involvement - purely data-driven.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import numpy as np

from app.services.market_data import get_quote, get_key_stats, get_historical, TimeFrame
from app.services.financial_data import get_fundamentals
from app.services.news_service import get_news_with_sentiment
from app.models.schemas import HealthSubScore, HealthScoreResponse

logger = logging.getLogger(__name__)


def _clamp(value: float, min_val: float = 0, max_val: float = 100) -> float:
    """Clamp value to range."""
    return max(min_val, min(max_val, value))


def _get_score_label(score: int) -> tuple:
    """Get label and color for score."""
    if score >= 80:
        return "Excellent", "green"
    elif score >= 65:
        return "Good", "green"
    elif score >= 50:
        return "Fair", "yellow"
    elif score >= 35:
        return "Weak", "red"
    else:
        return "Poor", "red"


def _calculate_financial_health(fundamentals) -> HealthSubScore:
    """Calculate Financial Health score from balance sheet and cash flow."""
    score_components = []

    # 1. Debt-to-Equity (lower is better)
    dte = fundamentals.debt_to_equity
    if dte is not None:
        if dte < 0.5:
            dte_score = 95
        elif dte < 1.0:
            dte_score = 85
        elif dte < 1.5:
            dte_score = 70
        elif dte < 2.0:
            dte_score = 55
        else:
            dte_score = 40
        score_components.append(dte_score)

    # 2. Current Ratio (higher is better)
    cr = fundamentals.current_ratio
    if cr is not None:
        if cr > 2.0:
            cr_score = 95
        elif cr > 1.5:
            cr_score = 85
        elif cr > 1.0:
            cr_score = 70
        elif cr > 0.8:
            cr_score = 55
        else:
            cr_score = 40
        score_components.append(cr_score)

    # 3. Free Cash Flow positive
    fcf = fundamentals.free_cash_flow
    if fcf is not None:
        fcf_score = 90 if fcf > 0 else 30
        score_components.append(fcf_score)

    # 4. FCF Margin
    fcf_margin = fundamentals.fcf_margin
    if fcf_margin is not None:
        if fcf_margin > 20:
            margin_score = 95
        elif fcf_margin > 10:
            margin_score = 85
        elif fcf_margin > 0:
            margin_score = 65
        else:
            margin_score = 40
        score_components.append(margin_score)

    # 5. ROE
    roe = fundamentals.roe
    if roe is not None:
        if roe > 25:
            roe_score = 95
        elif roe > 15:
            roe_score = 85
        elif roe > 10:
            roe_score = 70
        elif roe > 0:
            roe_score = 55
        else:
            roe_score = 35
        score_components.append(roe_score)

    # 6. Net Margin
    nm = fundamentals.net_margin
    if nm is not None:
        if nm > 25:
            nm_score = 95
        elif nm > 15:
            nm_score = 85
        elif nm > 5:
            nm_score = 70
        elif nm > 0:
            nm_score = 55
        else:
            nm_score = 35
        score_components.append(nm_score)

    # Average
    score = int(_clamp(np.mean(score_components))) if score_components else 50
    label, color = _get_score_label(score)

    # Build explanation
    explanations = []
    if dte is not None:
        explanations.append(f"Debt-to-equity of {dte:.2f}")
    if cr is not None:
        explanations.append(f"current ratio of {cr:.2f}")
    if fcf is not None:
        explanations.append(f"free cash flow of ${fcf/1e9:.1f}B")
    if nm is not None:
        explanations.append(f"net margin of {nm:.1f}%")

    explanation = f"Financial health assessed from: {', '.join(explanations)}."

    return HealthSubScore(
        name="Financial Health",
        score=score,
        label=label,
        color=color,
        explanation=explanation,
        metrics={
            'debt_to_equity': dte,
            'current_ratio': cr,
            'free_cash_flow': fcf,
            'fcf_margin': fcf_margin,
            'roe': roe,
            'net_margin': nm,
        }
    )


def _calculate_growth(fundamentals) -> HealthSubScore:
    """Calculate Growth score from revenue and earnings growth."""
    score_components = []

    # Revenue growth YoY
    rg = fundamentals.revenue_growth_yoy
    if rg is not None:
        if rg > 30:
            rg_score = 95
        elif rg > 20:
            rg_score = 88
        elif rg > 10:
            rg_score = 78
        elif rg > 5:
            rg_score = 65
        elif rg > 0:
            rg_score = 55
        else:
            rg_score = 35
        score_components.append(rg_score)

    # EPS growth YoY
    eg = fundamentals.eps_growth_yoy
    if eg is not None:
        if eg > 40:
            eg_score = 95
        elif eg > 25:
            eg_score = 88
        elif eg > 15:
            eg_score = 78
        elif eg > 5:
            eg_score = 65
        elif eg > 0:
            eg_score = 55
        else:
            eg_score = 35
        score_components.append(eg_score)

    # Net income growth (estimated from revenue + margin)
    if rg is not None and eg is not None:
        avg_growth = (rg + eg) / 2
        if avg_growth > 25:
            growth_score = 90
        elif avg_growth > 15:
            growth_score = 80
        elif avg_growth > 5:
            growth_score = 65
        elif avg_growth > 0:
            growth_score = 55
        else:
            growth_score = 35
        score_components.append(growth_score)

    score = int(_clamp(np.mean(score_components))) if score_components else 50
    label, color = _get_score_label(score)

    explanations = []
    if rg is not None:
        explanations.append(f"revenue growth of {rg:+.1f}% YoY")
    if eg is not None:
        explanations.append(f"EPS growth of {eg:+.1f}% YoY")

    explanation = f"Growth assessed from: {', '.join(explanations)}." if explanations else "Growth data unavailable."

    return HealthSubScore(
        name="Growth",
        score=score,
        label=label,
        color=color,
        explanation=explanation,
        metrics={
            'revenue_growth': rg,
            'eps_growth': eg,
        }
    )


def _calculate_momentum(quote, hist_data) -> HealthSubScore:
    """Calculate Momentum score from price action."""
    score_components = []

    # 1. Recent returns (1M)
    if hist_data and len(hist_data.data) > 1:
        prices = [p.close for p in hist_data.data]
        if len(prices) >= 2:
            # 1M return approx (20 trading days)
            recent_return = (prices[-1] - prices[0]) / prices[0] * 100
            if recent_return > 15:
                ret_score = 90
            elif recent_return > 5:
                ret_score = 80
            elif recent_return > 0:
                ret_score = 70
            elif recent_return > -5:
                ret_score = 55
            elif recent_return > -15:
                ret_score = 40
            else:
                ret_score = 25
            score_components.append(ret_score)

            # Volatility (lower is better for momentum stability)
            if len(prices) >= 5:
                returns = np.diff(prices) / prices[:-1]
                volatility = np.std(returns) * np.sqrt(252) * 100
                if volatility < 20:
                    vol_score = 85
                elif volatility < 40:
                    vol_score = 70
                elif volatility < 60:
                    vol_score = 55
                else:
                    vol_score = 40
                score_components.append(vol_score)

    # 2. Position relative to 52-week range
    if quote.price > 0 and quote.year_high > 0 and quote.year_low > 0:
        range_position = (quote.price - quote.year_low) / (quote.year_high - quote.year_low)
        if range_position > 0.8:
            pos_score = 90
        elif range_position > 0.6:
            pos_score = 80
        elif range_position > 0.4:
            pos_score = 65
        elif range_position > 0.2:
            pos_score = 50
        else:
            pos_score = 35
        score_components.append(pos_score)

    # 3. Day change direction
    if quote.change_percent is not None:
        if quote.change_percent > 2:
            day_score = 80
        elif quote.change_percent > 0:
            day_score = 70
        elif quote.change_percent > -2:
            day_score = 55
        else:
            day_score = 45
        score_components.append(day_score)

    score = int(_clamp(np.mean(score_components))) if score_components else 50
    label, color = _get_score_label(score)

    explanation = f"Momentum assessed from recent price action, volatility, and position in 52-week range."

    return HealthSubScore(
        name="Momentum",
        score=score,
        label=label,
        color=color,
        explanation=explanation,
        metrics={
            'recent_return': recent_return if 'recent_return' in locals() else None,
            'range_position': range_position if 'range_position' in locals() else None,
            'volatility': volatility if 'volatility' in locals() else None,
        }
    )


def _calculate_valuation(fundamentals, quote) -> HealthSubScore:
    """Calculate Valuation score from valuation ratios."""
    score_components = []

    # P/E ratio (lower is better relative to growth)
    pe = fundamentals.pe_ratio or quote.pe_ratio
    if pe is not None and pe > 0:
        # Compare to typical "fair" PE of 15-25
        if pe < 15:
            pe_score = 90
        elif pe < 25:
            pe_score = 80
        elif pe < 35:
            pe_score = 65
        elif pe < 50:
            pe_score = 50
        else:
            pe_score = 35
        score_components.append(pe_score)

    # PEG ratio (P/E / growth)
    peg = fundamentals.peg_ratio
    if peg is not None and peg > 0:
        if peg < 1:
            peg_score = 90
        elif peg < 2:
            peg_score = 75
        elif peg < 3:
            peg_score = 60
        else:
            peg_score = 40
        score_components.append(peg_score)

    # EV/EBITDA
    ev_ebitda = fundamentals.ev_to_ebitda
    if ev_ebitda is not None and ev_ebitda > 0:
        if ev_ebitda < 10:
            ev_score = 90
        elif ev_ebitda < 15:
            ev_score = 78
        elif ev_ebitda < 20:
            ev_score = 65
        elif ev_ebitda < 30:
            ev_score = 50
        else:
            ev_score = 35
        score_components.append(ev_score)

    # P/S ratio
    ps = fundamentals.price_to_sales
    if ps is not None and ps > 0:
        if ps < 2:
            ps_score = 85
        elif ps < 5:
            ps_score = 70
        elif ps < 10:
            ps_score = 55
        else:
            ps_score = 40
        score_components.append(ps_score)

    score = int(_clamp(np.mean(score_components))) if score_components else 50
    label, color = _get_score_label(score)

    explanations = []
    if pe is not None:
        explanations.append(f"P/E of {pe:.1f}")
    if peg is not None:
        explanations.append(f"PEG of {peg:.1f}")
    if ev_ebitda is not None:
        explanations.append(f"EV/EBITDA of {ev_ebitda:.1f}")

    explanation = f"Valuation assessed from: {', '.join(explanations)}." if explanations else "Valuation data unavailable."

    return HealthSubScore(
        name="Valuation",
        score=score,
        label=label,
        color=color,
        explanation=explanation,
        metrics={
            'pe_ratio': pe,
            'peg_ratio': peg,
            'ev_to_ebitda': ev_ebitda,
            'price_to_sales': ps,
        }
    )


def _calculate_sentiment(news_response) -> HealthSubScore:
    """Calculate Sentiment score from news sentiment."""
    if news_response and news_response.article_count > 0:
        sentiment_score = news_response.sentiment_score  # -1 to 1

        # Map to 0-100
        score = int(_clamp((sentiment_score + 1) * 50))

        # Analyst rating bonus
        label, color = _get_score_label(score)

        explanation = f"Based on {news_response.article_count} recent news articles. Overall sentiment: {news_response.overall_sentiment} (score: {sentiment_score:.2f})."

        return HealthSubScore(
            name="Market Sentiment",
            score=score,
            label=label,
            color=color,
            explanation=explanation,
            metrics={
                'sentiment_score': sentiment_score,
                'article_count': news_response.article_count,
                'overall': news_response.overall_sentiment,
            }
        )
    else:
        return HealthSubScore(
            name="Market Sentiment",
            score=50,
            label="Fair",
            color="yellow",
            explanation="Insufficient news data to assess sentiment.",
            metrics={}
        )


def _calculate_risk(quote, stats) -> HealthSubScore:
    """Calculate Risk score (lower risk = higher score)."""
    score_components = []

    # Beta (closer to 1 is moderate risk)
    beta = stats.get('beta')
    if beta is not None:
        # Score: 1.0 beta = 75, 0.5 or 1.5 = 65, >2 or <0.2 = 35
        if 0.8 <= beta <= 1.2:
            beta_score = 80
        elif 0.5 <= beta <= 1.5:
            beta_score = 70
        elif 0.2 <= beta <= 2.0:
            beta_score = 55
        else:
            beta_score = 35
        score_components.append(beta_score)

    # Short interest (lower is better)
    short_pct = stats.get('short_percent')
    if short_pct is not None:
        if short_pct < 5:
            short_score = 85
        elif short_pct < 10:
            short_score = 70
        elif short_pct < 20:
            short_score = 55
        else:
            short_score = 35
        score_components.append(short_score)

    # Volatility (from price)
    if quote.price > 0 and quote.year_high > 0 and quote.year_low > 0:
        annual_vol_proxy = (quote.year_high - quote.year_low) / quote.year_low * 100
        if annual_vol_proxy < 30:
            vol_score = 85
        elif annual_vol_proxy < 50:
            vol_score = 70
        elif annual_vol_proxy < 80:
            vol_score = 55
        else:
            vol_score = 35
        score_components.append(vol_score)

    score = int(_clamp(np.mean(score_components))) if score_components else 50
    label, color = _get_score_label(score)

    explanations = []
    if beta is not None:
        explanations.append(f"beta of {beta:.2f}")
    if short_pct is not None:
        explanations.append(f"short interest of {short_pct:.1f}%")

    explanation = f"Risk assessed from: {', '.join(explanations)}." if explanations else "Risk data unavailable."

    return HealthSubScore(
        name="Risk",
        score=score,
        label=label,
        color=color,
        explanation=explanation,
        metrics={
            'beta': beta,
            'short_percentage': short_pct,
        }
    )


async def calculate_health_score(symbol: str) -> HealthScoreResponse:
    """Calculate comprehensive health score for a stock."""
    try:
        # Fetch all data in parallel
        quote = await get_quote(symbol)
        fundamentals = await get_fundamentals(symbol)
        stats = await get_key_stats(symbol)
        hist_data = await get_historical(symbol, TimeFrame.MONTH)
        news_response = await get_news_with_sentiment(symbol, limit=20)

        # Calculate sub-scores
        financial_health = _calculate_financial_health(fundamentals)
        growth = _calculate_growth(fundamentals)
        momentum = _calculate_momentum(quote, hist_data)
        valuation = _calculate_valuation(fundamentals, quote)
        sentiment = _calculate_sentiment(news_response)
        risk = _calculate_risk(quote, stats)

        sub_scores = [financial_health, growth, momentum, valuation, sentiment, risk]

        # Calculate weighted overall score
        weights = {
            'Financial Health': 0.30,
            'Growth': 0.20,
            'Momentum': 0.15,
            'Valuation': 0.15,
            'Market Sentiment': 0.10,
            'Risk': 0.10,
        }

        overall = sum(
            s.score * weights[s.name]
            for s in sub_scores
        )
        overall = int(_clamp(overall))
        overall_label, overall_color = _get_score_label(overall)

        # Estimate percentile (simplified - in production would compare to universe)
        percentile = int(min(99, overall + 10))

        return HealthScoreResponse(
            symbol=symbol.upper(),
            overall_score=overall,
            overall_label=overall_label,
            overall_color=overall_color,
            sub_scores=sub_scores,
            percentile_rank=percentile,
            calculated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Error calculating health score for {symbol}: {e}")
        raise