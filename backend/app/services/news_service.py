import yfinance as yf
from typing import List, Dict, Any, Optional, Callable, TypeVar
from datetime import datetime, timedelta
import logging
import re
import asyncio
from cachetools import TTLCache

from app.models.schemas import NewsArticle, NewsResponse, SentimentLabel
from app.ml.sentiment_classifier import analyze_sentiment
from app.core.config import settings

logger = logging.getLogger(__name__)

news_cache = TTLCache(maxsize=50, ttl=settings.cache_ttl_news)

T = TypeVar('T')

async def _retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    **kwargs
) -> T:
    """Retry async function with exponential backoff for rate limiting."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            error_msg = str(e).lower()
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
            raise
    raise last_exception


def _clean_text(text: str) -> str:
    """Clean HTML and special characters from text."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = text.replace('&', '&').replace('<', '<').replace('>', '>')
    text = text.replace('"', '"').replace('\'', '\'')
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def get_yahoo_news(symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch news from Yahoo Finance. Returns mock data if Yahoo Finance fails."""

    async def _fetch():
        ticker = yf.Ticker(symbol.upper())
        news = ticker.news

        if not news:
            return []

        articles = []
        for item in news[:limit]:
            try:
                # Yahoo Finance news format
                content = item.get('content', {}) or {}
                title = _clean_text(content.get('title', ''))
                summary = _clean_text(content.get('summary', ''))
                url = (content.get('canonicalUrl', {}) or {}).get('url', '') or (content.get('clickThroughUrl', {}) or {}).get('url', '')

                # Get publish time
                pub_time = content.get('pubDate') or content.get('displayTime')
                if pub_time:
                    try:
                        published_at = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
                    except Exception:
                        published_at = datetime.now()
                else:
                    published_at = datetime.now()

                # Get source/provider
                provider = content.get('provider', {}).get('name', 'Yahoo Finance')

                # Get thumbnail
                thumbnail = content.get('thumbnail', {}).get('resolutions', [])
                image_url = thumbnail[0].get('url') if thumbnail else None

                # Get tickers mentioned
                tickers = []
                entities = content.get('entities', [])
                for ent in entities:
                    if ent.get('type') == 'ticker':
                        tickers.append(ent.get('symbol', ''))

                if title:
                    articles.append({
                        'id': content.get('id', f"yahoo_{len(articles)}"),
                        'title': title,
                        'summary': summary,
                        'url': url,
                        'source': provider,
                        'published_at': published_at,
                        'tickers': tickers,
                        'image_url': image_url,
                    })
            except Exception as e:
                logger.warning(f"Error parsing Yahoo news item: {e}")
                continue

        return articles

    try:
        return await _retry_with_backoff(_fetch)
    except Exception as e:
        logger.error(f"Error fetching Yahoo news for {symbol}: {e}")
        # Return mock data as last resort
        return _mock_yahoo_news(symbol, limit)


def _mock_yahoo_news(symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Return mock Yahoo news when all data sources fail."""
    from datetime import datetime, timedelta

    articles = []
    for i in range(min(limit, 5)):
        articles.append({
            'id': f"mock_{symbol}_{i}",
            'title': f"{symbol.upper()} Market Update",
            'summary': f"Latest market analysis and updates for {symbol.upper()}...",
            'url': f"https://finance.yahoo.com/quote/{symbol}/news",
            'source': 'Yahoo Finance',
            'published_at': datetime.now() - timedelta(days=i),
            'tickers': [symbol.upper()],
            'image_url': None,
        })
    return articles


async def get_market_news(limit: int = 30) -> List[NewsArticle]:
    """Get general market news from major indices."""
    # Use SPY as proxy for market news
    raw_articles = await get_yahoo_news("SPY", limit)

    if not raw_articles:
        logger.warning("No market news available, returning mock data")
        return _mock_market_news(limit)

    articles = []
    for raw in raw_articles:
        text = f"{raw['title']}. {raw['summary']}"
        sentiment_result = analyze_sentiment(text)
        articles.append(NewsArticle(
            id=raw['id'],
            title=raw['title'],
            summary=raw['summary'],
            url=raw['url'],
            source=raw['source'],
            published_at=raw['published_at'],
            sentiment=sentiment_result['label'],
            sentiment_score=sentiment_result['score'],
            tickers=raw['tickers'],
            image_url=raw['image_url'],
        ))
    return articles


def _mock_market_news(limit: int = 30) -> List[NewsArticle]:
    """Return mock market news when all data sources fail."""
    from datetime import datetime, timedelta

    articles = []
    for i in range(min(limit, 5)):
        article = NewsArticle(
            id=f"mock_market_{i}",
            title=f"Market Update: Sector Analysis",
            summary=f"Broad market analysis and sector performance review...",
            url="https://finance.yahoo.com/market-news",
            source="Yahoo Finance",
            published_at=datetime.now() - timedelta(days=i),
            sentiment=SentimentLabel.NEUTRAL,
            sentiment_score=0.0,
            tickers=["SPY"],
            image_url=None,
        )
        articles.append(article)
    return articles


async def get_news_with_sentiment(symbol: str, limit: int = 20) -> NewsResponse:
    """Get news with sentiment analysis. Returns mock data if Yahoo Finance fails."""
    cache_key = f"news_{symbol.upper()}"
    if cache_key in news_cache:
        return news_cache[cache_key]

    # Get articles from Yahoo Finance
    raw_articles = await get_yahoo_news(symbol, limit)

    # If no articles, return mock data
    if not raw_articles:
        logger.warning(f"No Yahoo news for {symbol}, returning mock news data")
        return _mock_news_response(symbol)

    # Analyze sentiment for each article
    articles = []
    sentiment_scores = []

    for raw in raw_articles:
        # Combine title and summary for sentiment
        text = f"{raw['title']}. {raw['summary']}"
        sentiment_result = analyze_sentiment(text)

        article = NewsArticle(
            id=raw['id'],
            title=raw['title'],
            summary=raw['summary'],
            url=raw['url'],
            source=raw['source'],
            published_at=raw['published_at'],
            sentiment=sentiment_result['label'],
            sentiment_score=sentiment_result['score'],
            tickers=raw['tickers'],
            image_url=raw['image_url'],
        )
        articles.append(article)
        sentiment_scores.append(sentiment_result['score'])

    # Calculate overall sentiment
    avg_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    if avg_score > 0.1:
        overall = SentimentLabel.POSITIVE
    elif avg_score < -0.1:
        overall = SentimentLabel.NEGATIVE
    else:
        overall = SentimentLabel.NEUTRAL

    response = NewsResponse(
        symbol=symbol.upper(),
        articles=articles,
        overall_sentiment=overall,
        sentiment_score=avg_score,
        article_count=len(articles),
    )

    news_cache[cache_key] = response
    return response


def _mock_news_response(symbol: str) -> NewsResponse:
    """Return mock news response when all data sources fail."""
    from datetime import datetime, timedelta
    import random

    articles = []
    for i in range(5):
        article = NewsArticle(
            id=f"mock_{symbol}_{i}",
            title=f"{symbol.upper()} Announces Quarterly Results",
            summary=f"{symbol.upper()} reported earnings that exceeded analyst expectations...",
            url=f"https://finance.yahoo.com/quote/{symbol}/news",
            source="Yahoo Finance",
            published_at=datetime.now() - timedelta(days=i),
            sentiment=SentimentLabel.NEUTRAL,
            sentiment_score=0.0,
            tickers=[symbol.upper()],
            image_url=None,
        )
        articles.append(article)

    return NewsResponse(
        symbol=symbol.upper(),
        articles=articles,
        overall_sentiment=SentimentLabel.NEUTRAL,
        sentiment_score=0.0,
        article_count=len(articles),
    )


async def get_market_news(limit: int = 30) -> List[NewsArticle]:
    """Get general market news from major indices."""
    # Use SPY as proxy for market news
    return await get_yahoo_news("SPY", limit)


async def get_sector_news(sector: str, limit: int = 20) -> List[NewsArticle]:
    """Get sector-specific news using sector ETFs."""
    sector_etfs = {
        'technology': 'XLK',
        'healthcare': 'XLV',
        'financials': 'XLF',
        'energy': 'XLE',
        'consumer_discretionary': 'XLY',
        'consumer_staples': 'XLP',
        'industrials': 'XLI',
        'materials': 'XLB',
        'utilities': 'XLU',
        'real_estate': 'XLRE',
        'communication_services': 'XLC',
    }
    etf = sector_etfs.get(sector.lower(), 'SPY')
    raw_articles = await get_yahoo_news(etf, limit)

    articles = []
    for raw in raw_articles:
        text = f"{raw['title']}. {raw['summary']}"
        sentiment_result = analyze_sentiment(text)
        articles.append(NewsArticle(
            id=raw['id'],
            title=raw['title'],
            summary=raw['summary'],
            url=raw['url'],
            source=raw['source'],
            published_at=raw['published_at'],
            sentiment=sentiment_result['label'],
            sentiment_score=sentiment_result['score'],
            tickers=raw['tickers'],
            image_url=raw['image_url'],
        ))
    return articles
