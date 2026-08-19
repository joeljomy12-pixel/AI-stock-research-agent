"""
Financial Sentiment Classifier
Uses VADER (rule-based) as primary with FinBERT as optional enhancement.
For hackathon, VADER is fast and requires no model download.
"""
from typing import Dict, Any
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

# Initialize VADER analyzer
_vader_analyzer = SentimentIntensityAnalyzer()

# Financial domain-specific lexicon enhancements
FINANCIAL_LEXICON = {
    # Positive financial terms
    'beat': 2.0,
    'beats': 2.0,
    'beating': 1.5,
    'exceeded': 2.0,
    'exceeds': 1.5,
    'surpassed': 2.0,
    'surpasses': 1.5,
    'strong': 1.5,
    'growth': 1.5,
    'growing': 1.2,
    'grew': 1.2,
    'increase': 1.0,
    'increased': 1.0,
    'increasing': 0.8,
    'rise': 1.0,
    'rising': 0.8,
    'rose': 0.8,
    'gain': 1.0,
    'gains': 1.0,
    'up': 0.5,
    'upgrade': 1.5,
    'upgraded': 1.5,
    'bullish': 1.5,
    'outperform': 1.5,
    'buy': 1.0,
    'accumulate': 1.0,
    'recommend': 1.0,
    'positive': 1.0,
    'improved': 1.2,
    'improving': 1.0,
    'recovery': 1.0,
    'rebound': 1.0,
    'rally': 1.2,
    'surge': 1.5,
    'soar': 1.5,
    'record': 1.0,
    'high': 0.5,
    'profit': 1.0,
    'profitable': 1.2,
    'earnings': 0.5,
    'revenue': 0.3,
    'margin': 0.3,
    'cash flow': 0.5,
    'dividend': 0.5,
    'buyback': 0.8,
    'guidance raised': 2.0,
    'raised guidance': 2.0,

    # Negative financial terms
    'miss': -2.0,
    'missed': -2.0,
    'missing': -1.5,
    'fell short': -2.0,
    'below': -1.0,
    'weak': -1.5,
    'weakness': -1.5,
    'decline': -1.0,
    'declining': -1.0,
    'declined': -1.0,
    'decrease': -1.0,
    'decreased': -1.0,
    'decreasing': -0.8,
    'fall': -1.0,
    'falling': -0.8,
    'fell': -0.8,
    'drop': -1.0,
    'dropping': -0.8,
    'dropped': -0.8,
    'loss': -1.0,
    'losses': -1.0,
    'downgrade': -1.5,
    'downgraded': -1.5,
    'bearish': -1.5,
    'underperform': -1.5,
    'sell': -1.0,
    'reduce': -0.8,
    'negative': -1.0,
    'deteriorated': -1.2,
    'deteriorating': -1.0,
    'crash': -2.0,
    'plunge': -2.0,
    'plummet': -2.0,
    'tumble': -1.5,
    'slide': -1.0,
    'slump': -1.5,
    'low': -0.5,
    'warning': -1.5,
    'warned': -1.5,
    'guidance cut': -2.0,
    'cut guidance': -2.0,
    'lowered guidance': -2.0,
    'bankruptcy': -3.0,
    'default': -2.5,
    'restructuring': -1.5,
    'layoffs': -1.5,
    'layoff': -1.5,
    'investigation': -1.5,
    'lawsuit': -1.0,
    'sec probe': -2.0,
    'fraud': -3.0,
    'scandal': -2.0,
}

# Update VADER lexicon
_vader_analyzer.lexicon.update(FINANCIAL_LEXICON)


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of financial text.
    Returns label and normalized score (-1 to 1).
    """
    if not text or not text.strip():
        return {'label': 'neutral', 'score': 0.0, 'compound': 0.0}

    try:
        scores = _vader_analyzer.polarity_scores(text)
        compound = scores['compound']

        # Normalize to -1 to 1 (VADER compound is already in this range)
        normalized_score = max(-1.0, min(1.0, compound))

        # Determine label with financial thresholds
        if normalized_score >= 0.15:
            label = 'positive'
        elif normalized_score <= -0.15:
            label = 'negative'
        else:
            label = 'neutral'

        return {
            'label': label,
            'score': normalized_score,
            'compound': compound,
            'positive': scores['pos'],
            'negative': scores['neg'],
            'neutral': scores['neu'],
        }

    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return {'label': 'neutral', 'score': 0.0, 'compound': 0.0}


def analyze_sentiment_batch(texts: list) -> list:
    """Analyze sentiment for multiple texts."""
    return [analyze_sentiment(text) for text in texts]


def get_sentiment_label(score: float) -> str:
    """Convert numeric score to label."""
    if score >= 0.15:
        return 'positive'
    elif score <= -0.15:
        return 'negative'
    return 'neutral'