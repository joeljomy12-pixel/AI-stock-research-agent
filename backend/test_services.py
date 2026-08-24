import asyncio
from app.services.market_data import get_quote, get_historical, get_key_stats
from app.services.financial_data import get_fundamentals
from app.services.news_service import get_news_with_sentiment
from app.ml.health_scorer import calculate_health_score
from app.services.research_agent import generate_research_report, get_evidence_documents

async def test():
    print('Testing quote...')
    q = await get_quote('AAPL')
    print(f'  Quote: {q.symbol} = ${q.price}')

    print('Testing historical...')
    h = await get_historical('AAPL')
    print(f'  Historical: {len(h.data)} points')

    print('Testing key stats...')
    ks = await get_key_stats('AAPL')
    print(f'  Key stats: {len(ks)} fields')

    print('Testing fundamentals...')
    f = await get_fundamentals('AAPL')
    print(f'  Fundamentals: {f.company_name}')

    print('Testing news...')
    n = await get_news_with_sentiment('AAPL')
    print(f'  News: {n.article_count} articles, sentiment: {n.overall_sentiment}')

    print('Testing health score...')
    h = await calculate_health_score('AAPL')
    print(f'  Health: {h.overall_score} ({h.overall_label})')

    print('Testing research report...')
    r = await generate_research_report('AAPL')
    print(f'  Research: {r.thesis.bull_case[:2]}...')

    print('Testing evidence...')
    e = await get_evidence_documents('AAPL')
    print(f'  Evidence: {len(e)} documents')

    print('ALL TESTS PASSED!')

asyncio.run(test())