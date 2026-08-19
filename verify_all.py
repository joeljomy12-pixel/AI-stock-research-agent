import sys
sys.path.insert(0, 'backend')
import asyncio
from app.services.research_agent import generate_research_report
from app.ml.anomaly_detector import analyze_movement
from app.ml.health_scorer import calculate_health_score

async def test():
    try:
        r = await generate_research_report('AAPL')
        print('RESEARCH OK:', r.symbol, '-', len(r.sections), 'sections')
        m = await analyze_movement('AAPL')
        print('MOVEMENT OK:', m.is_anomaly, '-', len(m.drivers), 'drivers')
        h = await calculate_health_score('AAPL')
        print('HEALTH OK:', h.overall_score, '/ 100')
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
