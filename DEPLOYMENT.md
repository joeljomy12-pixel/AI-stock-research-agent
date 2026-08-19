# Deployment Guide

This guide covers deploying the AI Stock Research Agent for a hackathon demo or production use.

---

## Option 1: Docker Compose (Recommended)

### Prerequisites
- Docker Engine 20.10+
- Docker Compose v2

### Steps

1. **Clone and configure environment**:
   ```bash
   cp backend/.env.example backend/.env
   ```

2. **Edit `backend/.env`** with your API keys:
   - `ANTHROPIC_API_KEY` (required for LLM synthesis)
   - `FMP_API_KEY` (optional, enhances fundamentals)
   - `NEWS_API_KEY` (optional, additional news sources)

3. **Start services**:
   ```bash
   docker compose up --build
   ```

4. **Access**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Stopping
```bash
docker compose down
```

### With Redis caching (optional)
Uncomment the `redis` service in `docker-compose.yml` for production caching.

---

## Option 2: Manual Deployment

### Backend (FastAPI)

1. **Setup Python environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

3. **Run with uvicorn**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Production (gunicorn + uvicorn workers)**:
   ```bash
   pip install gunicorn
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```

### Frontend (Next.js)

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.local.example .env.local
   # Or create manually with NEXT_PUBLIC_API_URL
   ```

3. **Build for production**:
   ```bash
   npm run build
   npm run start
   ```

4. **Or use development server**:
   ```bash
   npm run dev
   ```

---

## Option 3: Cloud Deployment

### Backend on Railway / Render / Fly.io

1. Connect your repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `.env.example`
5. Deploy

### Frontend on Vercel / Netlify

1. Connect your repository
2. Set framework preset: Next.js
3. Set build command: `npm run build`
4. Set environment variable: `NEXT_PUBLIC_API_URL` = your backend URL
5. Deploy

---

## Environment Variables Reference

### Backend
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | - | Anthropic API key for LLM synthesis |
| `FMP_API_KEY` | No | - | Financial Modeling Prep API key |
| `NEWS_API_KEY` | No | - | NewsAPI.org key |
| `CHROMA_PERSIST_DIR` | No | `./chroma_db` | Vector store persistence path |
| `CORS_ORIGINS_STR` | No | `http://localhost:3000` | Comma-separated allowed origins |
| `BACKEND_HOST` | No | `0.0.0.0` | Server bind host |
| `BACKEND_PORT` | No | `8000` | Server port |

*Only required for LLM-powered research synthesis; core quantitative features work without it.

### Frontend
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend API URL |
| `NEXT_PUBLIC_GA_ID` | No | - | Google Analytics ID |

---

## Health Checks

### Backend
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"stock-intelligence-api"}
```

### Frontend
```bash
curl http://localhost:3000
# Expected: HTML response with 200 status
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 already in use | Kill existing process: `lsof -ti:8000 \| xargs kill -9` |
| yfinance rate limit | Wait 30-60s; built-in TTLCache handles retries |
| ChromaDB download slow | First run downloads ONNX model (~80MB); subsequent runs are fast |
| CORS errors | Verify `CORS_ORIGINS_STR` matches frontend URL in backend `.env` |
| Module not found | Run `pip install -r requirements.txt` and `npm install` |
| Build fails (frontend) | Clear `.next`: `rm -rf .next && npm run build` |
| TypeError: 'coroutine' object | Ensure all `get_historical()` calls use `await` |
| interest_coverage AttributeError | Fixed; ensure clean `__pycache__` (run `find . -name "*.pyc" -delete`) |

---

## Production Considerations

1. **Security**:
   - Never commit `.env` files
   - Use secrets manager in cloud
   - Enable HTTPS (reverse proxy / load balancer)
   - Rate-limit API endpoints

2. **Performance**:
   - Use Redis for caching (uncomment in docker-compose.yml)
   - Scale backend with multiple gunicorn workers
   - CDN for static assets

3. **Monitoring**:
   - Add logging (structlog / loguru)
   - Health check endpoints
   - Error tracking (Sentry)

4. **Reliability**:
   - Retry logic for external APIs (yfinance)
   - Graceful degradation when APIs fail
   - Circuit breakers for rate limits

---

## Demo Tips for Hackathon

1. **Pre-warm cache**: Hit `/api/v1/stocks/AAPL/health` and `/research` before demo
2. **Popular tickers**: AAPL, MSFT, GOOGL, TSLA, NVDA, AMZN
3. **Showcase features**:
   - AI Research Agent: Bull/Bear cases with citations
   - Why It Moved: Anomaly detection + news correlation
   - Stock Doctor: 6-factor health score with gauges
4. **Disclaimer**: Always show financial disclaimer prominently
5. **Offline fallback**: Core features work without API keys (rule-based)

---

_Last updated: 2026-08-18_
