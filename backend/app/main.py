from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.api.v1 import stocks
from app.ml.vector_store import vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Stock Intelligence API...")
    vector_store.initialize()
    logger.info("Vector store initialized")

    yield

    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="AI Stock Intelligence API",
    description="Hackathon-ready AI/ML stock research platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stocks.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": "AI Stock Intelligence API",
        "version": "1.0.0",
        "description": "Hackathon-ready AI/ML stock research platform",
        "endpoints": {
            "search": "/api/v1/stocks/search?q={query}",
            "quote": "/api/v1/stocks/{symbol}/quote",
            "historical": "/api/v1/stocks/{symbol}/historical",
            "fundamentals": "/api/v1/stocks/{symbol}/fundamentals",
            "news": "/api/v1/stocks/{symbol}/news",
            "health": "/api/v1/stocks/{symbol}/health",
            "movement": "/api/v1/stocks/{symbol}/movement",
            "research": "/api/v1/stocks/{symbol}/research",
            "evidence": "/api/v1/stocks/{symbol}/evidence",
            "market_news": "/api/v1/stocks/market/news",
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "stock-intelligence-api"}


@app.get("/debug/env")
async def debug_env():
    from app.core.config import settings
    return {
        "fmp_api_key_set": bool(settings.fmp_api_key),
        "fmp_api_key_length": len(settings.fmp_api_key) if settings.fmp_api_key else 0,
        "fmp_api_key_prefix": settings.fmp_api_key[:4] + "..." if settings.fmp_api_key and len(settings.fmp_api_key) > 4 else settings.fmp_api_key,
        "cors_origins": settings.cors_origins,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )