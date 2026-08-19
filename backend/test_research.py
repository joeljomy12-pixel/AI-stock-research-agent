import asyncio
from app.services.research_agent import generate_research_report


async def main():
    try:
        r = await generate_research_report('AAPL')
        print('SUCCESS: sections=', len(r.sections))
    except Exception as e:
        import traceback
        traceback.print_exc()


asyncio.run(main())
