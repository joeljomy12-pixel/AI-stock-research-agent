"""
AI Research Agent
Generates investment thesis with citations from multiple data sources.
Rule-based approach - no LLM hallucination.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.services.market_data import get_quote, get_key_stats, get_historical, TimeFrame
from app.services.financial_data import get_fundamentals
from app.services.news_service import get_news_with_sentiment, get_yahoo_news
from app.models.schemas import (
    ResearchReport, ResearchSection, InvestmentThesis,
    SourceDocument, EvidenceResponse
)

logger = logging.getLogger(__name__)


async def generate_research_report(symbol: str) -> ResearchReport:
    """Generate comprehensive AI research report with investment thesis."""
    try:
        # Fetch all data in parallel
        quote = await get_quote(symbol)
        fundamentals = await get_fundamentals(symbol)
        stats = await get_key_stats(symbol)
        hist_data = await get_historical(symbol, TimeFrame.MONTH)
        news_response = await get_news_with_sentiment(symbol, limit=20)

        # Build thesis
        thesis = _build_thesis(quote, fundamentals, stats, hist_data, news_response)

        # Build sections
        sections = _build_sections(quote, fundamentals, stats, hist_data, news_response)

        return ResearchReport(
            symbol=symbol.upper(),
            company_name=fundamentals.company_name,
            thesis=thesis,
            sections=sections,
            generated_at=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Error generating research report for {symbol}: {e}")
        raise


def _build_thesis(quote, fundamentals, stats, hist_data, news_response) -> InvestmentThesis:
    """Build investment thesis from quantitative data."""
    bull_case = []
    bear_case = []
    key_catalysts = []
    key_risks = []
    recent_developments = []
    watch_items = []

    # Financial Health analysis
    if fundamentals.debt_to_equity is not None:
        if fundamentals.debt_to_equity < 0.5:
            bull_case.append(f"Low debt-to-equity ({fundamentals.debt_to_equity:.2f}) indicates strong balance sheet")
        elif fundamentals.debt_to_equity > 2.0:
            bear_case.append(f"High debt-to-equity ({fundamentals.debt_to_equity:.2f}) increases financial risk")

    if fundamentals.free_cash_flow and fundamentals.free_cash_flow > 0:
        bull_case.append(f"Positive free cash flow (${fundamentals.free_cash_flow/1e9:.1f}B) supports reinvestment and returns")
    elif fundamentals.free_cash_flow and fundamentals.free_cash_flow < 0:
        bear_case.append(f"Negative free cash flow (${fundamentals.free_cash_flow/1e9:.1f}B) may require external funding")

    if fundamentals.net_margin and fundamentals.net_margin > 15:
        bull_case.append(f"Strong net margin ({fundamentals.net_margin:.1f}%) indicates pricing power")
    elif fundamentals.net_margin and fundamentals.net_margin < 5:
        bear_case.append(f"Thin net margin ({fundamentals.net_margin:.1f}%) leaves little room for error")

    # Growth analysis
    if fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy > 15:
        bull_case.append(f"Strong revenue growth ({fundamentals.revenue_growth_yoy:.1f}% YoY)")
        key_catalysts.append("Revenue growth accelerating")
    elif fundamentals.revenue_growth_yoy and fundamentals.revenue_growth_yoy < 0:
        bear_case.append(f"Revenue declining ({fundamentals.revenue_growth_yoy:.1f}% YoY)")
        key_risks.append("Revenue contraction trend")

    if fundamentals.eps_growth_yoy and fundamentals.eps_growth_yoy > 20:
        bull_case.append(f"EPS growing rapidly ({fundamentals.eps_growth_yoy:.1f}% YoY)")

    # Valuation analysis
    pe = fundamentals.pe_ratio or quote.pe_ratio
    if pe and pe < 15:
        bull_case.append(f"Attractive P/E ratio ({pe:.1f}x) vs historical averages")
    elif pe and pe > 40:
        bear_case.append(f"Elevated P/E ratio ({pe:.1f}x) prices in high growth expectations")

    if fundamentals.peg_ratio and fundamentals.peg_ratio < 1:
        bull_case.append(f"PEG ratio ({fundamentals.peg_ratio:.2f}) suggests undervaluation relative to growth")

    # Momentum analysis
    if hist_data and len(hist_data.data) > 1:
        prices = [p.close for p in hist_data.data]
        if len(prices) >= 2:
            recent_return = (prices[-1] - prices[0]) / prices[0] * 100
            if recent_return > 10:
                bull_case.append(f"Strong recent momentum (+{recent_return:.1f}% over period)")
            elif recent_return < -10:
                bear_case.append(f"Negative momentum ({recent_return:.1f}% over period)")
                watch_items.append("Monitor for trend reversal")

    # 52-week position
    if quote.price > 0 and quote.year_high > 0 and quote.year_low > 0:
        range_pos = (quote.price - quote.year_low) / (quote.year_high - quote.year_low)
        if range_pos > 0.8:
            bear_case.append("Trading near 52-week high - limited upside near-term")
            watch_items.append("Watch for pullback to add")
        elif range_pos < 0.2:
            bull_case.append("Trading near 52-week low - potential value opportunity")
            key_catalysts.append("Mean reversion potential")

    # Sentiment
    if news_response and news_response.article_count > 0:
        if news_response.overall_sentiment.value == "positive":
            bull_case.append(f"Positive news sentiment ({news_response.sentiment_score:.2f})")
        elif news_response.overall_sentiment.value == "negative":
            bear_case.append(f"Negative news sentiment ({news_response.sentiment_score:.2f})")
            key_risks.append("Negative media coverage")

    # Analyst rating
    if fundamentals.analyst_rating:
        if fundamentals.analyst_rating in ["buy", "strong_buy"]:
            bull_case.append(f"Analyst consensus: {fundamentals.analyst_rating}")
        elif fundamentals.analyst_rating in ["sell", "strong_sell"]:
            bear_case.append(f"Analyst consensus: {fundamentals.analyst_rating}")

    # Beta/Risk
    beta = stats.get('beta')
    if beta and beta > 1.5:
        key_risks.append(f"High beta ({beta:.2f}) - amplifies market moves")
        watch_items.append("High volatility expected")
    elif beta and beta < 0.7:
            bull_case.append(f"Low beta ({beta:.2f}) - defensive characteristics")

    # Default items if lists empty
    if not bull_case:
        bull_case.append("No strong quantitative bull signals identified")
    if not bear_case:
        bear_case.append("No strong quantitative bear signals identified")
    if not key_catalysts:
        key_catalysts.append("Monitor upcoming earnings and macro developments")
    if not key_risks:
        key_risks.append("General market risk applies")
    if not recent_developments:
        recent_developments.append("Review latest earnings and news for updates")
    if not watch_items:
        watch_items.append("Track quarterly results and guidance changes")

    return InvestmentThesis(
        bull_case=bull_case[:5],
        bear_case=bear_case[:5],
        key_catalysts=key_catalysts[:5],
        key_risks=key_risks[:5],
        recent_developments=recent_developments[:5],
        watch_items=watch_items[:5],
    )


def _build_sections(quote, fundamentals, stats, hist_data, news_response) -> List[ResearchSection]:
    """Build detailed research sections."""
    sections = []

    # 1. Company Overview
    sections.append(ResearchSection(
        title="Company Overview",
        content=f"{fundamentals.company_name} ({quote.symbol}) operates in the {fundamentals.sector} sector, "
                f"specifically in the {fundamentals.industry} industry. "
                f"Market cap: ${fundamentals.market_cap/1e9:.1f}B. "
                f"Current price: ${quote.price:.2f} ({quote.change_percent:+.2f}% today).",
        sources=[f"Yahoo Finance quote data for {quote.symbol}"]
    ))

    # 2. Financial Health
    fin_health = []
    if fundamentals.debt_to_equity is not None:
        fin_health.append(f"Debt-to-Equity: {fundamentals.debt_to_equity:.2f}")
    if fundamentals.current_ratio is not None:
        fin_health.append(f"Current Ratio: {fundamentals.current_ratio:.2f}")
    if fundamentals.free_cash_flow is not None:
        fin_health.append(f"Free Cash Flow: ${fundamentals.free_cash_flow/1e9:.1f}B")
    if fundamentals.fcf_margin is not None:
        fin_health.append(f"FCF Margin: {fundamentals.fcf_margin:.1f}%")
    if fundamentals.roe is not None:
        fin_health.append(f"Return on Equity: {fundamentals.roe:.1f}%")
    if fundamentals.net_margin is not None:
        fin_health.append(f"Net Margin: {fundamentals.net_margin:.1f}%")

    sections.append(ResearchSection(
        title="Financial Health",
        content="\n".join(fin_health) if fin_health else "Financial health metrics unavailable.",
        sources=["Yahoo Finance financial statements (TTM)"]
    ))

    # 3. Growth Profile
    growth_items = []
    if fundamentals.revenue_growth_yoy is not None:
        growth_items.append(f"Revenue Growth (YoY): {fundamentals.revenue_growth_yoy:+.1f}%")
    if fundamentals.eps_growth_yoy is not None:
        growth_items.append(f"EPS Growth (YoY): {fundamentals.eps_growth_yoy:+.1f}%")

    sections.append(ResearchSection(
        title="Growth Profile",
        content="\n".join(growth_items) if growth_items else "Growth data unavailable.",
        sources=["Yahoo Finance analyst estimates"]
    ))

    # 4. Valuation
    val_items = []
    if fundamentals.pe_ratio:
        val_items.append(f"P/E Ratio (TTM): {fundamentals.pe_ratio:.1f}x")
    if fundamentals.forward_pe:
        val_items.append(f"Forward P/E: {fundamentals.forward_pe:.1f}x")
    if fundamentals.peg_ratio:
        val_items.append(f"PEG Ratio: {fundamentals.peg_ratio:.2f}")
    if fundamentals.ev_to_ebitda:
        val_items.append(f"EV/EBITDA: {fundamentals.ev_to_ebitda:.1f}x")
    if fundamentals.price_to_sales:
        val_items.append(f"P/S Ratio: {fundamentals.price_to_sales:.1f}x")
    if fundamentals.price_to_book:
        val_items.append(f"P/B Ratio: {fundamentals.price_to_book:.1f}x")

    sections.append(ResearchSection(
        title="Valuation Metrics",
        content="\n".join(val_items) if val_items else "Valuation data unavailable.",
        sources=["Yahoo Finance valuation metrics"]
    ))

    # 5. Technical / Momentum
    tech_items = []
    if quote.price > 0 and quote.year_high > 0 and quote.year_low > 0:
        range_pos = (quote.price - quote.year_low) / (quote.year_high - quote.year_low) * 100
        tech_items.append(f"52-Week Range Position: {range_pos:.1f}% (${quote.year_low:.2f} - ${quote.year_high:.2f})")
    tech_items.append(f"Current Volume: {quote.volume:,} (Avg: {quote.avg_volume:,})")
    if quote.avg_volume > 0:
        tech_items.append(f"Volume Ratio: {quote.volume/quote.avg_volume:.1f}x")
    beta = stats.get('beta')
    if beta:
        tech_items.append(f"Beta: {beta:.2f}")

    sections.append(ResearchSection(
        title="Technical & Momentum",
        content="\n".join(tech_items) if tech_items else "Technical data unavailable.",
        sources=["Yahoo Finance price data"]
    ))

    # 6. News & Sentiment
    if news_response and news_response.article_count > 0:
        sentiment_desc = f"Overall: {news_response.overall_sentiment.value} ({news_response.sentiment_score:.2f})"
        top_articles = [f"• {a.title[:80]}... ({a.sentiment.value}, {a.sentiment_score:.2f})"
                       for a in news_response.articles[:5]]
        news_content = sentiment_desc + "\n\nTop Articles:\n" + "\n".join(top_articles)
        news_sources = [f"Yahoo Finance news ({news_response.article_count} articles)"]
    else:
        news_content = "No recent news data available."
        news_sources = []

    sections.append(ResearchSection(
        title="News & Sentiment",
        content=news_content,
        sources=news_sources
    ))

    # 7. Key Statistics
    stat_items = []
    stat_map = {
        'shares_outstanding': 'Shares Outstanding',
        'float_shares': 'Float Shares',
        'short_ratio': 'Short Ratio',
        'short_percent': 'Short % of Float',
        'held_insiders': 'Insider Ownership %',
        'held_institutions': 'Institutional Ownership %',
        'book_value': 'Book Value/Share',
        'profit_margins': 'Profit Margin %',
        'operating_margins': 'Operating Margin %',
        'return_on_assets': 'ROA %',
        'current_ratio': 'Current Ratio',
        'quick_ratio': 'Quick Ratio',
        'total_cash': 'Total Cash',
        'total_debt': 'Total Debt',
    }
    for key, label in stat_map.items():
        val = stats.get(key)
        if val is not None:
            if 'percent' in key.lower() or 'margin' in key.lower() or 'return' in key.lower():
                stat_items.append(f"{label}: {val*100:.1f}%" if val < 1 else f"{label}: {val:.1f}%")
            elif 'shares' in key.lower() or 'cash' in key.lower() or 'debt' in key.lower():
                stat_items.append(f"{label}: ${val/1e9:.1f}B")
            else:
                stat_items.append(f"{label}: {val:.2f}")

    sections.append(ResearchSection(
        title="Key Statistics",
        content="\n".join(stat_items) if stat_items else "Key statistics unavailable.",
        sources=["Yahoo Finance key statistics"]
    ))

    return sections


async def get_evidence_documents(symbol: str) -> List[SourceDocument]:
    """Get source documents/evidence for the research report."""
    try:
        # Get news articles as evidence
        raw_news = await get_yahoo_news(symbol, limit=30)
        fundamentals = await get_fundamentals(symbol)
        quote = await get_quote(symbol)

        documents = []

        # Add news articles as evidence
        for i, article in enumerate(raw_news[:15]):
            text = f"{article.get('title', '')}. {article.get('summary', '')}"
            from app.ml.sentiment_classifier import analyze_sentiment
            sentiment = analyze_sentiment(text)

            documents.append(SourceDocument(
                id=f"news_{symbol}_{i}",
                type="news",
                title=article.get('title', 'Untitled'),
                source=article.get('source', 'Yahoo Finance'),
                date=article.get('published_at', datetime.now()),
                url=article.get('url', ''),
                content_preview=article.get('summary', '')[:200],
                relevance_score=abs(sentiment['score']),
                highlighted_segments=[article.get('title', '')]
            ))

        # Add fundamental data as evidence
        documents.append(SourceDocument(
            id=f"fundamentals_{symbol}",
            type="filing",
            title=f"{fundamentals.company_name} - Financial Statements (TTM)",
            source="Yahoo Finance / SEC Filings",
            date=fundamentals.updated_at,
            url=f"https://finance.yahoo.com/quote/{symbol}/financials",
            content_preview=f"Revenue: ${fundamentals.revenue/1e9:.1f}B, Net Income: ${fundamentals.net_income/1e9:.1f}B, "
                           f"FCF: ${fundamentals.free_cash_flow/1e9:.1f}B, D/E: {fundamentals.debt_to_equity:.2f}",
            relevance_score=0.9,
            highlighted_segments=[
                f"Revenue: ${fundamentals.revenue/1e9:.1f}B",
                f"Net Margin: {fundamentals.net_margin:.1f}%",
                f"Free Cash Flow: ${fundamentals.free_cash_flow/1e9:.1f}B",
            ]
        ))

        # Add price data as evidence
        documents.append(SourceDocument(
            id=f"price_{symbol}",
            type="report",
            title=f"{symbol} - Price & Volume Data",
            source="Yahoo Finance",
            date=datetime.now(),
            url=f"https://finance.yahoo.com/quote/{symbol}/chart",
            content_preview=f"Price: ${quote.price:.2f} ({quote.change_percent:+.2f}%), "
                           f"Volume: {quote.volume:,}, 52W Range: ${quote.year_low:.2f}-${quote.year_high:.2f}",
            relevance_score=0.85,
            highlighted_segments=[
                f"Current: ${quote.price:.2f}",
                f"Change: {quote.change_percent:+.2f}%",
                f"Volume: {quote.volume:,}",
            ]
        ))

        return documents

    except Exception as e:
        logger.error(f"Error getting evidence documents for {symbol}: {e}")
        return []


async def analyze_movement(symbol: str):
    """Entry point for movement analysis."""
    from app.ml.anomaly_detector import analyze_movement as am
    return await am(symbol)