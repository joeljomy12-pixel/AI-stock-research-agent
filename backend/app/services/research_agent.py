"""
AI Research Agent
Generates investment thesis using RAG + local rule-based synthesis.
Works without any API keys - uses quantitative data and rules for thesis generation.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.ml.vector_store import retrieve_relevant_docs, store_financial_documents
from app.services.market_data import get_quote, get_key_stats
from app.services.financial_data import get_fundamentals, get_quarterly_financials
from app.services.news_service import get_news_with_sentiment
from app.ml.health_scorer import calculate_health_score
from app.ml.anomaly_detector import analyze_movement
from app.models.schemas import (
    ResearchReport, InvestmentThesis, ResearchSection, SourceDocument
)

logger = logging.getLogger(__name__)


def _build_research_context(symbol: str, fundamentals, quote, stats, news, health, movement) -> str:
    """Build comprehensive context for LLM."""
    context_parts = []

    # Company Overview
    context_parts.append(f"=== COMPANY OVERVIEW ===")
    context_parts.append(f"Symbol: {symbol.upper()}")
    context_parts.append(f"Company: {fundamentals.company_name}")
    context_parts.append(f"Sector: {fundamentals.sector}")
    context_parts.append(f"Industry: {fundamentals.industry}")
    context_parts.append(f"Current Price: ${quote.price:.2f} ({quote.change_percent:+.2f}%)")
    context_parts.append(f"Market Cap: ${fundamentals.market_cap/1e9:.1f}B" if fundamentals.market_cap else "Market Cap: N/A")
    context_parts.append("")

    # Key Financial Metrics
    context_parts.append("=== KEY FINANCIAL METRICS (TTM) ===")
    if fundamentals.revenue:
        context_parts.append(f"Revenue: ${fundamentals.revenue/1e9:.2f}B")
    if fundamentals.revenue_growth_yoy:
        context_parts.append(f"Revenue Growth YoY: {fundamentals.revenue_growth_yoy:+.1f}%")
    if fundamentals.net_income:
        context_parts.append(f"Net Income: ${fundamentals.net_income/1e9:.2f}B")
    if fundamentals.net_margin:
        context_parts.append(f"Net Margin: {fundamentals.net_margin:.1f}%")
    if fundamentals.eps:
        context_parts.append(f"EPS: ${fundamentals.eps:.2f}")
    if fundamentals.eps_growth_yoy:
        context_parts.append(f"EPS Growth YoY: {fundamentals.eps_growth_yoy:+.1f}%")
    if fundamentals.free_cash_flow:
        context_parts.append(f"Free Cash Flow: ${fundamentals.free_cash_flow/1e9:.2f}B")
    if fundamentals.fcf_margin:
        context_parts.append(f"FCF Margin: {fundamentals.fcf_margin:.1f}%")
    if fundamentals.debt_to_equity:
        context_parts.append(f"Debt-to-Equity: {fundamentals.debt_to_equity:.2f}")
    if fundamentals.current_ratio:
        context_parts.append(f"Current Ratio: {fundamentals.current_ratio:.2f}")
    if fundamentals.roe:
        context_parts.append(f"ROE: {fundamentals.roe:.1f}%")
    if fundamentals.roa:
        context_parts.append(f"ROA: {fundamentals.roa:.1f}%")
    context_parts.append("")

    # Valuation
    context_parts.append("=== VALUATION ===")
    if fundamentals.pe_ratio:
        context_parts.append(f"P/E Ratio: {fundamentals.pe_ratio:.1f}")
    if fundamentals.forward_pe:
        context_parts.append(f"Forward P/E: {fundamentals.forward_pe:.1f}")
    if fundamentals.peg_ratio:
        context_parts.append(f"PEG Ratio: {fundamentals.peg_ratio:.1f}")
    if fundamentals.ev_to_ebitda:
        context_parts.append(f"EV/EBITDA: {fundamentals.ev_to_ebitda:.1f}")
    if fundamentals.price_to_sales:
        context_parts.append(f"P/S: {fundamentals.price_to_sales:.1f}")
    if fundamentals.price_to_book:
        context_parts.append(f"P/B: {fundamentals.price_to_book:.1f}")
    context_parts.append("")

    # Health Scores
    context_parts.append("=== AI HEALTH SCORES ===")
    context_parts.append(f"Overall: {health.overall_score}/100 ({health.overall_label})")
    for sub in health.sub_scores:
        context_parts.append(f"  {sub.name}: {sub.score}/100 ({sub.label}) - {sub.explanation}")
    context_parts.append("")

    # Movement Analysis
    if movement and movement.is_anomaly:
        context_parts.append("=== RECENT MOVEMENT ANALYSIS ===")
        context_parts.append(f"Anomaly detected: {movement.price_change_percent:+.2f}% move")
        context_parts.append(f"Summary: {movement.summary}")
        for driver in movement.drivers[:3]:
            context_parts.append(f"  - {driver.driver} ({driver.confidence}% confidence, {driver.category})")
            for ev in driver.evidence[:2]:
                context_parts.append(f"    Evidence: {ev}")
        context_parts.append("")

    # News Sentiment
    context_parts.append("=== NEWS SENTIMENT ===")
    context_parts.append(f"Overall: {news.overall_sentiment} (score: {news.sentiment_score:.2f})")
    context_parts.append(f"Article count: {news.article_count}")
    for article in news.articles[:5]:
        context_parts.append(f"  - [{article.sentiment}] {article.title[:100]}")
        context_parts.append(f"    Source: {article.source}, Date: {article.published_at.strftime('%Y-%m-%d')}")
    context_parts.append("")

    # Analyst Data
    if fundamentals.analyst_rating or fundamentals.price_target:
        context_parts.append("=== ANALYST DATA ===")
        if fundamentals.analyst_rating:
            context_parts.append(f"Consensus Rating: {fundamentals.analyst_rating}")
        if fundamentals.price_target:
            context_parts.append(f"Price Target: ${fundamentals.price_target:.2f}")
        if fundamentals.num_analysts:
            context_parts.append(f"Number of Analysts: {fundamentals.num_analysts}")
        context_parts.append("")

    # Key Stats
    context_parts.append("=== KEY STATISTICS ===")
    if stats.get('beta'):
        context_parts.append(f"Beta: {stats['beta']:.2f}")
    if stats.get('held_institutions'):
        context_parts.append(f"Institutional Ownership: {stats['held_institutions']:.1f}%")
    if stats.get('held_insiders'):
        context_parts.append(f"Insider Ownership: {stats['held_insiders']:.1f}%")
    if stats.get('short_percent'):
        context_parts.append(f"Short Interest: {stats['short_percent']:.1f}%")

    return "\n".join(context_parts)


def _generate_investment_thesis(symbol: str, fundamentals, quote, stats, news, health, movement) -> InvestmentThesis:
    """Generate investment thesis from quantitative data and rules."""
    bull_case = []
    bear_case = []

    # Revenue growth
    if fundamentals.revenue_growth_yoy is not None:
        if fundamentals.revenue_growth_yoy > 15:
            bull_case.append(f"Exceptional revenue growth of {fundamentals.revenue_growth_yoy:.1f}% YoY [Source: Financials, Revenue Growth]")
        elif fundamentals.revenue_growth_yoy > 5:
            bull_case.append(f"Solid revenue growth of {fundamentals.revenue_growth_yoy:.1f}% YoY [Source: Financials, Revenue Growth]")
        elif fundamentals.revenue_growth_yoy < 0:
            bear_case.append(f"Declining revenue at {fundamentals.revenue_growth_yoy:.1f}% YoY [Source: Financials, Revenue Growth]")
        elif fundamentals.revenue_growth_yoy < 5:
            bear_case.append(f"Slow revenue growth of {fundamentals.revenue_growth_yoy:.1f}% YoY [Source: Financials, Revenue Growth]")

    # Profitability
    if fundamentals.net_margin is not None:
        if fundamentals.net_margin > 20:
            bull_case.append(f"High net margin of {fundamentals.net_margin:.1f}% indicates strong pricing power [Source: Financials, Net Margin]")
        elif fundamentals.net_margin > 10:
            bull_case.append(f"Healthy net margin of {fundamentals.net_margin:.1f}% [Source: Financials, Net Margin]")
        elif fundamentals.net_margin < 0:
            bear_case.append(f"Negative net margin of {fundamentals.net_margin:.1f}% - company is unprofitable [Source: Financials, Net Margin]")
        elif fundamentals.net_margin < 5:
            bear_case.append(f"Low net margin of {fundamentals.net_margin:.1f}% suggests thin profitability [Source: Financials, Net Margin]")

    # Free cash flow
    if fundamentals.free_cash_flow is not None:
        if fundamentals.free_cash_flow > 0:
            bull_case.append(f"Positive free cash flow of ${fundamentals.free_cash_flow/1e9:.1f}B supports reinvestment and returns [Source: Financials, FCF]")
        else:
            bear_case.append(f"Negative free cash flow of ${fundamentals.free_cash_flow/1e9:.1f}B requires external funding [Source: Financials, FCF]")

    # Leverage
    if fundamentals.debt_to_equity is not None:
        if fundamentals.debt_to_equity < 0.5:
            bull_case.append(f"Conservative leverage with debt-to-equity of {fundamentals.debt_to_equity:.2f} [Source: Financials, D/E]")
        elif fundamentals.debt_to_equity < 1:
            bull_case.append(f"Moderate leverage with debt-to-equity of {fundamentals.debt_to_equity:.2f} [Source: Financials, D/E]")
        elif fundamentals.debt_to_equity > 2:
            bear_case.append(f"High leverage with debt-to-equity of {fundamentals.debt_to_equity:.2f} increases financial risk [Source: Financials, D/E]")
        elif fundamentals.debt_to_equity > 1:
            bear_case.append(f"Elevated leverage with debt-to-equity of {fundamentals.debt_to_equity:.2f} [Source: Financials, D/E]")

    # Valuation
    if fundamentals.pe_ratio is not None:
        if fundamentals.pe_ratio < 15:
            bull_case.append(f"Attractive P/E ratio of {fundamentals.pe_ratio:.1f} below market average [Source: Valuation, P/E]")
        elif fundamentals.pe_ratio > 40:
            bear_case.append(f"Elevated P/E ratio of {fundamentals.pe_ratio:.1f} implies high growth expectations [Source: Valuation, P/E]")
        elif fundamentals.pe_ratio > 25:
            bear_case.append(f"Above-average P/E ratio of {fundamentals.pe_ratio:.1f} [Source: Valuation, P/E]")

    # PEG ratio
    if fundamentals.peg_ratio is not None:
        if fundamentals.peg_ratio < 1:
            bull_case.append(f"PEG ratio of {fundamentals.peg_ratio:.1f} suggests undervaluation relative to growth [Source: Valuation, PEG]")
        elif fundamentals.peg_ratio > 2:
            bear_case.append(f"PEG ratio of {fundamentals.peg_ratio:.1f} suggests overvaluation relative to growth [Source: Valuation, PEG]")

    # Returns
    if fundamentals.roe is not None:
        if fundamentals.roe > 20:
            bull_case.append(f"Excellent ROE of {fundamentals.roe:.1f}% indicates efficient capital allocation [Source: Financials, ROE]")
        elif fundamentals.roe < 10:
            bear_case.append(f"Below-average ROE of {fundamentals.roe:.1f}% [Source: Financials, ROE]")

    # Current ratio
    if fundamentals.current_ratio is not None:
        if fundamentals.current_ratio < 1:
            bear_case.append(f"Current ratio of {fundamentals.current_ratio:.2f} below 1.0 indicates potential liquidity concerns [Source: Financials, Current Ratio]")
        elif fundamentals.current_ratio > 2:
            bull_case.append(f"Strong liquidity with current ratio of {fundamentals.current_ratio:.2f} [Source: Financials, Current Ratio]")

    # News sentiment
    if news.sentiment_score is not None:
        if news.sentiment_score > 0.3:
            bull_case.append(f"Positive news sentiment ({news.overall_sentiment}) from recent coverage [Source: News Sentiment]")
        elif news.sentiment_score < -0.3:
            bear_case.append(f"Negative news sentiment ({news.overall_sentiment}) from recent coverage [Source: News Sentiment]")

    # Health score
    if health.overall_score >= 70:
        bull_case.append(f"Strong overall health score of {health.overall_score}/100 ({health.overall_label}) [Source: AI Health Score]")
    elif health.overall_score <= 40:
        bear_case.append(f"Weak overall health score of {health.overall_score}/100 ({health.overall_label}) [Source: AI Health Score]")

    # Movement
    if movement and movement.is_anomaly:
        if movement.price_change_percent > 5:
            bull_case.append(f"Recent anomalous price surge of {movement.price_change_percent:+.1f}% detected [Source: Movement Analysis]")
        elif movement.price_change_percent < -5:
            bear_case.append(f"Recent anomalous price drop of {movement.price_change_percent:+.1f}% detected [Source: Movement Analysis]")

    # Analyst data
    if fundamentals.analyst_rating:
        if 'buy' in fundamentals.analyst_rating.lower() or 'overweight' in fundamentals.analyst_rating.lower():
            bull_case.append(f"Analyst consensus: {fundamentals.analyst_rating} with {fundamentals.num_analysts or 'multiple'} analysts [Source: Analyst Ratings]")
        elif 'sell' in fundamentals.analyst_rating.lower() or 'underweight' in fundamentals.analyst_rating.lower():
            bear_case.append(f"Analyst consensus: {fundamentals.analyst_rating} [Source: Analyst Ratings]")

    if fundamentals.price_target and quote.price:
        upside = (fundamentals.price_target - quote.price) / quote.price * 100
        if upside > 20:
            bull_case.append(f"Analyst price target implies {upside:.0f}% upside [Source: Analyst Price Target]")
        elif upside < -10:
            bear_case.append(f"Analyst price target implies {abs(upside):.0f}% downside [Source: Analyst Price Target]")

    # Default cases
    if not bull_case:
        bull_case.append("Sufficient data unavailable for detailed bull case - monitor fundamentals")
    if not bear_case:
        bear_case.append("Sufficient data unavailable for detailed bear case - monitor fundamentals")

    # Key catalysts
    key_catalysts = [
        "Next quarterly earnings report",
        "Product/technology announcements",
        "Macroeconomic data (interest rates, inflation)",
    ]
    if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 10:
        key_catalysts.insert(1, "Continued revenue acceleration")
    if movement and movement.is_anomaly:
        key_catalysts.insert(0, f"Follow-through on recent {movement.price_change_percent:+.1f}% move")

    # Key risks
    key_risks = [
        "Market volatility and sector rotation",
        "Competitive pressure and technology disruption",
        "Regulatory and geopolitical uncertainty",
    ]
    if fundamentals.debt_to_equity and fundamentals.debt_to_equity > 2:
        key_risks.insert(0, "High leverage limits financial flexibility")
    if fundamentals.pe_ratio and fundamentals.pe_ratio > 40:
        key_risks.insert(1, "Valuation leaves little margin for error")
    if news.sentiment_score and news.sentiment_score < -0.3:
        key_risks.insert(0, "Negative news flow and sentiment")

    # Recent developments
    recent_developments = [
        f"Current price: ${quote.price:.2f} ({quote.change_percent:+.2f}%) [Source: Market Data]",
        f"Health score: {health.overall_score}/100 ({health.overall_label}) [Source: AI Health Score]",
    ]
    if news.articles:
        recent_developments.append(f"Recent news: {news.articles[0].title[:80]}... [Source: {news.articles[0].source}]")
    if movement and movement.is_anomaly:
        recent_developments.append(f"Anomalous move: {movement.summary} [Source: Movement Analysis]")

    # Watch items
    watch_items = [
        "Quarterly revenue and EPS growth trajectory",
        "Gross and operating margin trends",
        "Free cash flow generation and capital allocation",
        "Competitive positioning and market share",
        "Guidance and management commentary",
    ]

    return InvestmentThesis(
        bull_case=bull_case[:5],
        bear_case=bear_case[:5],
        key_catalysts=key_catalysts[:4],
        key_risks=key_risks[:4],
        recent_developments=recent_developments[:3],
        watch_items=watch_items[:4],
    )


def _generate_detailed_sections(symbol: str, fundamentals, quote, stats, news, health, movement) -> List[ResearchSection]:
    """Generate detailed research sections from quantitative data."""
    sections = []

    # Business Overview
    sections.append(ResearchSection(
        title="Business Overview",
        content=f"{fundamentals.company_name} operates in the {fundamentals.sector} sector, {fundamentals.industry} industry. "
                f"The company generates revenue primarily through its core business operations. "
                f"Current market capitalization is ${fundamentals.market_cap/1e9:.1f}B." if fundamentals.market_cap else "Market cap data unavailable.",
        sources=["Company Profile", "Market Data", "Yahoo Finance"]
    ))

    # Financial Health Deep Dive
    fcf_text = "positive" if fundamentals.free_cash_flow and fundamentals.free_cash_flow > 0 else "negative"
    sections.append(ResearchSection(
        title="Financial Health Deep Dive",
        content=f"Profitability: Net margin of {fundamentals.net_margin:.1f}% with ROE of {fundamentals.roe:.1f}% and ROA of {fundamentals.roa:.1f}%. "
                f"Cash generation: {fcf_text.capitalize()} free cash flow (${fundamentals.free_cash_flow/1e9:.1f}B) with FCF margin of {fundamentals.fcf_margin:.1f}%. "
                f"Liquidity: Current ratio of {fundamentals.current_ratio:.2f}. "
                f"Leverage: Debt-to-equity of {fundamentals.debt_to_equity:.2f}." if fundamentals.net_margin and fundamentals.roe and fundamentals.roa and fundamentals.free_cash_flow and fundamentals.fcf_margin and fundamentals.current_ratio and fundamentals.debt_to_equity
                else "Key financial metrics partially unavailable.",
        sources=["Income Statement", "Balance Sheet", "Cash Flow Statement", "Financial Ratios"]
    ))

    # Growth Analysis
    sections.append(ResearchSection(
        title="Growth Analysis",
        content=f"Revenue growth (YoY): {fundamentals.revenue_growth_yoy:.1f}%. "
                f"EPS growth (YoY): {fundamentals.eps_growth_yoy:.1f}%. "
                f"The company's growth profile is {'accelerating' if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 15 else 'strong' if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 10 else 'moderate' if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 5 else 'slowing' if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 0 else 'contracting'}." if fundamentals.revenue_growth_yoy is not None
                else "Growth data unavailable.",
        sources=["Income Statement", "Analyst Estimates", "SEC Filings"]
    ))

    # Valuation Assessment
    pe_text = f"Current P/E: {fundamentals.pe_ratio:.1f}" if fundamentals.pe_ratio else "P/E: N/A"
    fwd_pe = f"Forward P/E: {fundamentals.forward_pe:.1f}" if fundamentals.forward_pe else ""
    peg = f"PEG: {fundamentals.peg_ratio:.1f}" if fundamentals.peg_ratio else ""
    ev_ebitda = f"EV/EBITDA: {fundamentals.ev_to_ebitda:.1f}" if fundamentals.ev_to_ebitda else ""
    ps = f"P/S: {fundamentals.price_to_sales:.1f}" if fundamentals.price_to_sales else ""
    pb = f"P/B: {fundamentals.price_to_book:.1f}" if fundamentals.price_to_book else ""

    val_parts = [pe_text, fwd_pe, peg, ev_ebitda, ps, pb]
    val_str = ", ".join([p for p in val_parts if p])

    if fundamentals.pe_ratio:
        if fundamentals.pe_ratio < 15:
            assessment = "appears undervalued relative to historical norms"
        elif fundamentals.pe_ratio < 25:
            assessment = "appears reasonably valued"
        elif fundamentals.pe_ratio < 40:
            assessment = "appears richly valued"
        else:
            assessment = "appears significantly overvalued"
        val_str += f". Valuation {assessment}."

    sections.append(ResearchSection(
        title="Valuation Assessment",
        content=val_str if val_str else "Valuation data unavailable.",
        sources=["Market Data", "Analyst Estimates", "Yahoo Finance"]
    ))

    # Competitive Position
    margin_desc = "strong" if fundamentals.net_margin and fundamentals.net_margin > 20 else "moderate" if fundamentals.net_margin and fundamentals.net_margin > 10 else "weak" if fundamentals.net_margin and fundamentals.net_margin > 0 else "negative"
    sections.append(ResearchSection(
        title="Competitive Position",
        content=f"Operates in {fundamentals.industry} with {margin_desc} profitability (net margin: {fundamentals.net_margin:.1f}%). "
                f"ROE of {fundamentals.roe:.1f}% {'exceeds' if fundamentals.roe and fundamentals.roe > 15 else 'is below' if fundamentals.roe and fundamentals.roe < 10 else 'is near'} typical cost of capital. "
                f"Market position assessment requires deeper competitive analysis including moat evaluation.",
        sources=["Industry Reports", "Financial Statements", "Competitive Analysis"]
    ))

    # Risk Factors
    beta = stats.get('beta', 'N/A')
    short_pct = stats.get('short_percent', 'N/A')
    inst_own = stats.get('held_institutions', 'N/A')

    risk_items = []
    if fundamentals.debt_to_equity and fundamentals.debt_to_equity > 2:
        risk_items.append(f"High financial leverage (D/E: {fundamentals.debt_to_equity:.2f})")
    if fundamentals.current_ratio and fundamentals.current_ratio < 1:
        risk_items.append(f"Liquidity risk (Current ratio: {fundamentals.current_ratio:.2f})")
    if fundamentals.pe_ratio and fundamentals.pe_ratio > 40:
        risk_items.append(f"Valuation risk (P/E: {fundamentals.pe_ratio:.1f})")
    if beta != 'N/A' and beta > 1.5:
        risk_items.append(f"High market sensitivity (Beta: {beta:.2f})")
    if short_pct != 'N/A' and short_pct > 5:
        risk_items.append(f"Elevated short interest ({short_pct:.1f}% of float)")

    if not risk_items:
        risk_items = ["Standard market and sector risks apply"]

    sections.append(ResearchSection(
        title="Risk Factors",
        content="Key risks: " + "; ".join(risk_items) + f". Additional risks include macroeconomic volatility, regulatory changes, competitive disruption, and execution risk. Institutional ownership: {inst_own}%. Short interest: {short_pct}%.",
        sources=["Market Data", "Risk Metrics", "SEC Filings"]
    ))

    return sections


def _create_fallback_report(symbol: str, fundamentals, quote, health) -> ResearchReport:
    """Create a basic report when LLM is unavailable."""
    # Build basic thesis from quantitative data
    bull_case = []
    bear_case = []

    if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 10:
        bull_case.append(f"Strong revenue growth of {fundamentals.revenue_growth_yoy:.1f}% YoY [Source: Financials, Revenue Growth]")
    elif fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy < 0:
        bear_case.append(f"Declining revenue at {fundamentals.revenue_growth_yoy:.1f}% YoY [Source: Financials, Revenue Growth]")

    if fundamentals.free_cash_flow and fundamentals.free_cash_flow > 0:
        bull_case.append(f"Positive free cash flow of ${fundamentals.free_cash_flow/1e9:.1f}B [Source: Financials, FCF]")
    else:
        bear_case.append(f"Negative or minimal free cash flow [Source: Financials, FCF]")

    if fundamentals.debt_to_equity and fundamentals.debt_to_equity < 1:
        bull_case.append(f"Low leverage with debt-to-equity of {fundamentals.debt_to_equity:.2f} [Source: Financials, D/E]")
    elif fundamentals.debt_to_equity and fundamentals.debt_to_equity > 2:
        bear_case.append(f"High leverage with debt-to-equity of {fundamentals.debt_to_equity:.2f} [Source: Financials, D/E]")

    if fundamentals.pe_ratio and fundamentals.pe_ratio > 50:
        bear_case.append(f"Elevated P/E ratio of {fundamentals.pe_ratio:.1f} suggests high expectations [Source: Valuation, P/E]")
    elif fundamentals.pe_ratio and fundamentals.pe_ratio < 15:
        bull_case.append(f"Reasonable P/E ratio of {fundamentals.pe_ratio:.1f} [Source: Valuation, P/E]")

    if not bull_case:
        bull_case.append("Data insufficient for detailed bull case")
    if not bear_case:
        bear_case.append("Data insufficient for detailed bear case")

    thesis = InvestmentThesis(
        bull_case=bull_case[:5],
        bear_case=bear_case[:5],
        key_catalysts=[
            "Next earnings report",
            "Product pipeline updates",
            "Macroeconomic environment"
        ],
        key_risks=[
            "Market volatility and sector rotation",
            "Competition and technology disruption",
            "Regulatory changes"
        ],
        recent_developments=[
            f"Latest price: ${quote.price:.2f} ({quote.change_percent:+.2f}%) [Source: Market Data]"
        ],
        watch_items=[
            "Quarterly earnings results",
            "Revenue growth trajectory",
            "Margin expansion/contraction",
            "Competitive developments"
        ]
    )

    sections = [
        ResearchSection(
            title="Business Overview",
            content=f"{fundamentals.company_name} operates in the {fundamentals.sector} sector, {fundamentals.industry} industry. The company generates revenue primarily through its core business operations. Current market capitalization is ${fundamentals.market_cap/1e9:.1f}B." if fundamentals.market_cap else "Market cap data unavailable.",
            sources=["Company Profile", "Market Data"]
        ),
        ResearchSection(
            title="Financial Health Deep Dive",
            content=f"The company shows {'strong' if fundamentals.free_cash_flow and fundamentals.free_cash_flow > 0 else 'weak'} free cash flow generation. Net margin stands at {fundamentals.net_margin:.1f}% with ROE of {fundamentals.roe:.1f}%. Debt-to-equity ratio is {fundamentals.debt_to_equity:.2f}." if fundamentals.net_margin and fundamentals.roe and fundamentals.debt_to_equity else "Key financial metrics unavailable.",
            sources=["Financial Statements", "Balance Sheet", "Cash Flow"]
        ),
        ResearchSection(
            title="Growth Analysis",
            content=f"Revenue growth YoY: {fundamentals.revenue_growth_yoy:.1f}%. EPS growth YoY: {fundamentals.eps_growth_yoy:.1f}%. The company's growth profile is {'accelerating' if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 15 else 'moderate' if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 5 else 'slowing'}." if fundamentals.revenue_growth_yoy else "Growth data unavailable.",
            sources=["Income Statement", "Analyst Estimates"]
        ),
        ResearchSection(
            title="Valuation Assessment",
            content=f"Current P/E: {fundamentals.pe_ratio:.1f}, Forward P/E: {fundamentals.forward_pe:.1f}, PEG: {fundamentals.peg_ratio:.1f}, EV/EBITDA: {fundamentals.ev_to_ebitda:.1f}. Valuation appears {'expensive' if fundamentals.pe_ratio and fundamentals.pe_ratio > 30 else 'reasonable' if fundamentals.pe_ratio and fundamentals.pe_ratio < 20 else 'cheap'} relative to historical norms." if fundamentals.pe_ratio else "Valuation data unavailable.",
            sources=["Market Data", "Analyst Estimates"]
        ),
        ResearchSection(
            title="Competitive Position",
            content=f"Operates in {fundamentals.industry} with {'strong' if fundamentals.net_margin and fundamentals.net_margin > 20 else 'moderate'} profitability. Market position assessment requires deeper competitive analysis.",
            sources=["Industry Reports"]
        ),
        ResearchSection(
            title="Risk Factors",
            content=f"Key risks include market volatility (Beta: {fundamentals.get('beta', 'N/A')}), sector cyclicality, and execution risk. Short interest at {fundamentals.get('short_percent', 'N/A')}% of float.",
            sources=["Market Data", "Risk Metrics"]
        ),
    ]

    return ResearchReport(
        symbol=symbol.upper(),
        company_name=fundamentals.company_name,
        thesis=thesis,
        sections=sections,
        generated_at=datetime.now(),
    )


async def generate_research_report(symbol: str) -> ResearchReport:
    """Main entry point for generating research report using local rule-based synthesis."""
    logger.info(f"Generating research report for {symbol}")

    try:
        # Fetch all data
        quote = await get_quote(symbol)
        fundamentals = await get_fundamentals(symbol)
        stats = await get_key_stats(symbol)
        news = await get_news_with_sentiment(symbol, limit=20)
        health = await calculate_health_score(symbol)
        movement = await analyze_movement(symbol)

        # Build context (for vector store)
        context = _build_research_context(symbol, fundamentals, quote, stats, news, health, movement)

        # Generate thesis and sections using local rule-based synthesis
        thesis = _generate_investment_thesis(symbol, fundamentals, quote, stats, news, health, movement)
        sections = _generate_detailed_sections(symbol, fundamentals, quote, stats, news, health, movement)

        report = ResearchReport(
            symbol=symbol.upper(),
            company_name=fundamentals.company_name,
            thesis=thesis,
            sections=sections,
            generated_at=datetime.now(),
        )

        # Store documents in vector store for future retrieval
        docs_to_store = [
            {
                'id': f"{symbol}_fundamentals_{datetime.now().isoformat()}",
                'type': 'fundamentals',
                'title': f'{symbol} Financial Fundamentals',
                'source': 'Yahoo Finance',
                'content': context,
                'date': datetime.now().isoformat(),
            }
        ]
        for article in news.articles[:10]:
            docs_to_store.append({
                'id': f"{symbol}_news_{article.id}",
                'type': 'news',
                'title': article.title,
                'source': article.source,
                'content': f"{article.title}. {article.summary}",
                'date': article.published_at.isoformat(),
                'url': article.url,
            })

        store_financial_documents(symbol, docs_to_store)

        return report

    except Exception as e:
        logger.error(f"Error generating research report for {symbol}: {e}")
        raise


async def get_evidence_documents(symbol: str) -> List[SourceDocument]:
    """Get source documents for evidence tab."""
    from app.ml.vector_store import vector_store

    docs = vector_store.search_by_symbol(symbol, "", n_results=20)

    evidence = []
    for d in docs:
        evidence.append(SourceDocument(
            id=d.get('id', ''),
            type=d['metadata'].get('type', 'unknown'),
            title=d['metadata'].get('title', ''),
            source=d['metadata'].get('source', ''),
            date=datetime.fromisoformat(d['metadata'].get('date', datetime.now().isoformat())),
            url=d['metadata'].get('url'),
            content_preview=d['document'][:300] + "..." if len(d['document']) > 300 else d['document'],
            relevance_score=1.0 - (d.get('distance', 0.5)) if d.get('distance') else 0.5,
        ))

    return evidence