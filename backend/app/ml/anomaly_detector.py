"""
Anomaly Detection for Stock Price/Volume Movements
Uses Isolation Forest for unsupervised anomaly detection.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.services.market_data import get_historical, get_quote, TimeFrame
from app.models.schemas import MovementDriver, MovementAnalysis
from app.services.news_service import get_yahoo_news
from app.ml.sentiment_classifier import analyze_sentiment

logger = logging.getLogger(__name__)


class MovementAnomalyDetector:
    """Detect unusual price and volume movements."""

    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self._is_fitted = False

    def _prepare_features(self, hist_data) -> np.ndarray:
        """Prepare features for anomaly detection."""
        if not hist_data or len(hist_data) < 10:
            return np.array([])

        df = pd.DataFrame([{
            'close': p.close,
            'volume': p.volume,
            'high': p.high,
            'low': p.low,
            'open': p.open,
        } for p in hist_data])

        # Calculate returns
        df['return'] = df['close'].pct_change()
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        df['volume_change'] = df['volume'].pct_change()
        df['volatility'] = df['return'].rolling(5).std()
        df['price_range'] = (df['high'] - df['low']) / df['close']
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)

        # Drop NaN
        df = df.dropna()

        if len(df) < 5:
            return np.array([])

        # Features for anomaly detection
        features = df[['return', 'volume_change', 'volatility', 'price_range', 'gap']].values
        return features

    async def detect_anomalies(self, symbol: str, timeframe: TimeFrame = TimeFrame.MONTH) -> Dict[str, Any]:
        """Detect anomalies in recent price/volume data."""
        try:
            hist = await get_historical(symbol, timeframe)
            features = self._prepare_features(hist.data)

            if len(features) == 0:
                return {'is_anomaly': False, 'anomaly_score': 0, 'details': {}}

            # Fit or use existing model
            if not self._is_fitted:
                self.scaler.fit(features)
                scaled_features = self.scaler.transform(features)
                self.model.fit(scaled_features)
                self._is_fitted = True
            else:
                scaled_features = self.scaler.transform(features)

            # Get anomaly scores (lower = more anomalous)
            scores = self.model.decision_function(scaled_features)
            predictions = self.model.predict(scaled_features)

            # Most recent point
            latest_score = scores[-1]
            latest_pred = predictions[-1]
            is_anomaly = latest_pred == -1

            # Normalize score to 0-1 (higher = more anomalous)
            # Isolation Forest scores are negative, more negative = more anomalous
            normalized_score = max(0, min(1, (-latest_score + 0.5) * 2))

            return {
                'is_anomaly': bool(is_anomaly),
                'anomaly_score': float(normalized_score),
                'raw_score': float(latest_score),
                'details': {
                    'recent_return': float(features[-1][0]) if len(features) > 0 else 0,
                    'recent_volume_change': float(features[-1][1]) if len(features) > 0 else 0,
                    'recent_volatility': float(features[-1][2]) if len(features) > 0 else 0,
                }
            }

        except Exception as e:
            logger.error(f"Error detecting anomalies for {symbol}: {e}")
            return {'is_anomaly': False, 'anomaly_score': 0, 'details': {}}


class MovementExplainer:
    """Explain why a stock moved by analyzing news and events."""

    def __init__(self):
        self.detector = MovementAnomalyDetector()

    async def analyze_movement(self, symbol: str) -> MovementAnalysis:
        """Full movement analysis with explanations."""
        # Get current quote
        quote = await get_quote(symbol)

        # Get historical for context
        hist = await get_historical(symbol, TimeFrame.MONTH)

        # Detect anomaly
        anomaly_result = await self.detector.detect_anomalies(symbol, TimeFrame.MONTH)

        # Get recent news
        raw_news = await get_yahoo_news(symbol, limit=30)

        # Analyze news for potential drivers
        drivers = await self._identify_drivers(symbol, quote, raw_news, anomaly_result)

        # Build summary
        summary = self._build_summary(symbol, quote, anomaly_result, drivers)

        return MovementAnalysis(
            symbol=symbol.upper(),
            date=datetime.now().strftime("%Y-%m-%d"),
            price_change=quote.change,
            price_change_percent=quote.change_percent,
            volume_ratio=quote.volume / quote.avg_volume if quote.avg_volume > 0 else 1.0,
            is_anomaly=anomaly_result['is_anomaly'],
            anomaly_score=anomaly_result['anomaly_score'],
            drivers=drivers,
            summary=summary,
        )

    async def _identify_drivers(
        self,
        symbol: str,
        quote,
        raw_news: List[Dict],
        anomaly_result: Dict
    ) -> List[MovementDriver]:
        """Identify potential drivers for the movement."""
        drivers = []

        # 1. Check for earnings/news events
        earnings_driver = self._check_earnings_event(raw_news, quote)
        if earnings_driver:
            drivers.append(earnings_driver)

        # 2. Check for analyst actions
        analyst_driver = self._check_analyst_actions(raw_news, quote)
        if analyst_driver:
            drivers.append(analyst_driver)

        # 3. Check for macro/sector news
        macro_driver = self._check_macro_sector(raw_news, quote)
        if macro_driver:
            drivers.append(macro_driver)

        # 4. Check for company-specific news
        company_driver = self._check_company_news(raw_news, quote)
        if company_driver:
            drivers.append(company_driver)

        # 5. Technical/profit-taking
        technical_driver = self._check_technical_factors(quote, anomaly_result)
        if technical_driver:
            drivers.append(technical_driver)

        # 6. Sector/peer movement
        sector_driver = await self._check_sector_movement(symbol, quote)
        if sector_driver:
            drivers.append(sector_driver)

        # Sort by confidence
        drivers.sort(key=lambda d: d.confidence, reverse=True)

        # If no drivers found, add generic
        if not drivers:
            drivers.append(MovementDriver(
                driver="No specific catalyst identified",
                confidence=10,
                category="possible",
                description="Price movement may be due to normal market volatility or unreported factors.",
            ))

        return drivers[:5]  # Top 5 drivers

    def _check_earnings_event(self, news: List[Dict], quote) -> Optional[MovementDriver]:
        """Check for earnings-related news."""
        earnings_keywords = ['earnings', 'quarterly', 'results', 'eps', 'revenue', 'guidance', 'forecast']
        earnings_articles = []

        for article in news:
            text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
            if any(kw in text for kw in earnings_keywords):
                earnings_articles.append(article)

        if not earnings_articles:
            return None

        # Analyze sentiment of earnings news
        sentiments = []
        for art in earnings_articles:
            text = art.get('title', '') + ' ' + art.get('summary', '')
            sent = analyze_sentiment(text)
            sentiments.append(sent['score'])

        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Determine direction match
        price_up = quote.change_percent > 0
        sentiment_positive = avg_sentiment > 0.1

        if (price_up and sentiment_positive) or (not price_up and not sentiment_positive):
            confidence = 70
            category = "high_confidence"
        else:
            confidence = 40
            category = "correlation"

        return MovementDriver(
            driver=f"Earnings announcement ({'positive' if sentiment_positive else 'negative'} surprise)",
            confidence=confidence,
            category=category,
            evidence=[a.get('title', '') for a in earnings_articles[:3]],
            description=f"Recent earnings news sentiment: {avg_sentiment:.2f}. {len(earnings_articles)} related articles found."
        )

    def _check_analyst_actions(self, news: List[Dict], quote) -> Optional[MovementDriver]:
        """Check for analyst upgrades/downgrades."""
        analyst_keywords = ['upgrade', 'downgrade', 'price target', 'rating', 'analyst', 'initiated', 'reiterated']
        analyst_articles = []

        for article in news:
            text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
            if any(kw in text for kw in analyst_keywords):
                analyst_articles.append(article)

        if not analyst_articles:
            return None

        # Count upgrades vs downgrades
        upgrades = sum(1 for a in analyst_articles if 'upgrade' in (a.get('title', '') + a.get('summary', '')).lower())
        downgrades = sum(1 for a in analyst_articles if 'downgrade' in (a.get('title', '') + a.get('summary', '')).lower())

        price_up = quote.change_percent > 0

        if upgrades > downgrades and price_up:
            confidence = 65
            category = "high_confidence"
            driver = "Analyst upgrades and positive rating changes"
        elif downgrades > upgrades and not price_up:
            confidence = 65
            category = "high_confidence"
            driver = "Analyst downgrades and negative rating changes"
        else:
            confidence = 35
            category = "correlation"
            driver = "Mixed analyst actions"

        return MovementDriver(
            driver=driver,
            confidence=confidence,
            category=category,
            evidence=[a.get('title', '') for a in analyst_articles[:3]],
            description=f"Found {upgrades} upgrades and {downgrades} downgrades in recent news."
        )

    def _check_macro_sector(self, news: List[Dict], quote) -> Optional[MovementDriver]:
        """Check for macro/sector-wide news."""
        macro_keywords = ['fed', 'federal reserve', 'interest rate', 'inflation', 'cpi', 'ppi',
                          'gdp', 'unemployment', 'jobs', 'treasury', 'yield', 'dollar',
                          'recession', 'economy', 'market', 'selloff', 'rally']
        sector_keywords = ['sector', 'industry', 'peers', 'competitors', 'semiconductor', 'tech',
                           'ai', 'artificial intelligence', 'chip', 'chips']

        macro_articles = []
        sector_articles = []

        for article in news:
            text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
            if any(kw in text for kw in macro_keywords):
                macro_articles.append(article)
            if any(kw in text for kw in sector_keywords):
                sector_articles.append(article)

        drivers = []

        if macro_articles:
            drivers.append(MovementDriver(
                driver="Macroeconomic headlines",
                confidence=30,
                category="correlation",
                evidence=[a.get('title', '') for a in macro_articles[:2]],
                description=f"Broad market news may be affecting sentiment. {len(macro_articles)} macro-related articles."
            ))

        if sector_articles:
            drivers.append(MovementDriver(
                driver="Sector/industry developments",
                confidence=35,
                category="correlation",
                evidence=[a.get('title', '') for a in sector_articles[:2]],
                description=f"Sector-specific news may be driving peer movements. {len(sector_articles)} related articles."
            ))

        return drivers[0] if drivers else None

    def _check_company_news(self, news: List[Dict], quote) -> Optional[MovementDriver]:
        """Check for company-specific news (non-earnings, non-analyst)."""
        # Filter out earnings and analyst articles
        other_keywords = ['partnership', 'acquisition', 'merger', 'buyback', 'dividend',
                          'product', 'launch', 'fda', 'approval', 'contract', 'deal',
                          'investigation', 'lawsuit', 'sec', 'probe', 'executive', 'ceo',
                          'cfo', 'resignation', 'appointment', 'guidance']

        other_articles = []
        for article in news:
            text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
            # Skip if already categorized
            if any(kw in text for kw in ['earnings', 'quarterly', 'eps', 'upgrade', 'downgrade', 'analyst', 'price target']):
                continue
            if any(kw in text for kw in other_keywords):
                other_articles.append(article)

        if not other_articles:
            return None

        # Analyze sentiment
        sentiments = []
        for art in other_articles:
            text = art.get('title', '') + ' ' + art.get('summary', '')
            sent = analyze_sentiment(text)
            sentiments.append(sent['score'])

        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        price_up = quote.change_percent > 0
        sentiment_positive = avg_sentiment > 0.1

        confidence = 50 if (price_up == sentiment_positive) else 25
        category = "evidence" if confidence > 40 else "possible"

        return MovementDriver(
            driver="Company-specific news and announcements",
            confidence=confidence,
            category=category,
            evidence=[a.get('title', '') for a in other_articles[:3]],
            description=f"Company news sentiment: {avg_sentiment:.2f}. {len(other_articles)} relevant articles."
        )

    def _check_technical_factors(self, quote, anomaly_result: Dict) -> Optional[MovementDriver]:
        """Check for technical factors like profit-taking, overbought/oversold."""
        drivers = []

        # Check if near highs/lows
        if quote.price > 0:
            from_high = (quote.year_high - quote.price) / quote.year_high * 100
            from_low = (quote.price - quote.year_low) / quote.year_low * 100

            # Profit taking after rally
            if from_high < 5 and quote.change_percent < -2:
                drivers.append(MovementDriver(
                    driver="Profit-taking after recent rally",
                    confidence=45,
                    category="possible",
                    evidence=[f"Stock within {from_high:.1f}% of 52-week high"],
                    description=f"Stock near 52-week high (${quote.year_high:.2f}), current: ${quote.price:.2f}. Pullback may be profit-taking."
                ))

            # Oversold bounce
            if from_low < 10 and quote.change_percent > 2:
                drivers.append(MovementDriver(
                    driver="Bounce from oversold levels",
                    confidence=40,
                    category="possible",
                    evidence=[f"Stock within {from_low:.1f}% of 52-week low"],
                    description=f"Stock near 52-week low (${quote.year_low:.2f}), current: ${quote.price:.2f}. May be technical bounce."
                ))

        # Volume spike without news
        volume_ratio = quote.volume / quote.avg_volume if quote.avg_volume > 0 else 1
        if volume_ratio > 3 and not anomaly_result.get('is_anomaly', False):
            drivers.append(MovementDriver(
                driver="Unusual volume spike",
                confidence=35,
                category="correlation",
                evidence=[f"Volume {volume_ratio:.1f}x average"],
                description="High volume without clear news catalyst may indicate institutional activity."
            ))

        return drivers[0] if drivers else None

    async def _check_sector_movement(self, symbol: str, quote) -> Optional[MovementDriver]:
        """Check if sector peers moved similarly."""
        # For hackathon, simplified - would need peer data in production
        sector_etfs = {
            'NVDA': 'XLK', 'AMD': 'XLK', 'INTC': 'XLK',  # Semiconductors
            'AAPL': 'XLK', 'MSFT': 'XLK', 'GOOGL': 'XLK',  # Tech
            'TSLA': 'XLY',  # Consumer Discretionary
            'JPM': 'XLF', 'BAC': 'XLF',  # Financials
            'XOM': 'XLE', 'CVX': 'XLE',  # Energy
        }

        etf = sector_etfs.get(symbol.upper())
        if not etf:
            return None

        try:
            etf_quote = await get_quote(etf)
            etf_change = etf_quote.change_percent

            # Same direction movement
            same_direction = (quote.change_percent > 0) == (etf_change > 0)
            magnitude_similar = abs(abs(quote.change_percent) - abs(etf_change)) < 2

            if same_direction:
                confidence = 40 if magnitude_similar else 30
                category = "correlation"
                return MovementDriver(
                    driver=f"Sector movement ({etf} moved {etf_change:+.2f}%)",
                    confidence=confidence,
                    category=category,
                    evidence=[f"Sector ETF {etf}: {etf_change:+.2f}%"],
                    description=f"Stock moving in line with sector ETF {etf}. Correlation suggests sector-driven move."
                )
        except Exception:
            pass

        return None

    def _build_summary(
        self,
        symbol: str,
        quote,
        anomaly_result: Dict,
        drivers: List[MovementDriver]
    ) -> str:
        """Build human-readable summary."""
        direction = "rose" if quote.change_percent > 0 else "fell"
        pct = abs(quote.change_percent)

        summary = f"{symbol.upper()} {direction} {pct:.2f}% today"

        if anomaly_result['is_anomaly']:
            summary += f" (unusual movement detected, anomaly score: {anomaly_result['anomaly_score']:.2f})"

        if drivers:
            top_driver = drivers[0]
            summary += f". Primary driver: {top_driver.driver.lower()} ({top_driver.confidence}% confidence)"

            if len(drivers) > 1:
                summary += f". Other factors: {', '.join(d.driver.lower() for d in drivers[1:3])}"

        summary += "."

        return summary


async def analyze_movement(symbol: str) -> MovementAnalysis:
    """Main entry point for movement analysis."""
    explainer = MovementExplainer()
    return await explainer.analyze_movement(symbol)