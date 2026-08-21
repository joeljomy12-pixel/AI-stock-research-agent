from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""
    fmp_api_key: str = ""
    news_api_key: str = ""

    # Vector Store
    chroma_persist_dir: str = "./chroma_db"

    # CORS - parse comma-separated string
    cors_origins_str: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Cache TTL (seconds)
    cache_ttl_quote: int = 60
    cache_ttl_fundamentals: int = 900
    cache_ttl_news: int = 300
    cache_ttl_health: int = 600

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
