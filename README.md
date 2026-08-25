# AI Stock Research Agent 📈

A hackathon-ready AI/ML stock intelligence platform with three core features:
- **AI Stock Research Agent** — Investment thesis with citations
- **Why Did This Stock Move?** — Anomaly detection + news correlation
- **AI Stock Doctor** — 6-factor quantitative health scoring (0-100)

Built with FastAPI + Next.js 14 + Tailwind CSS, featuring a Bloomberg-style dark dashboard with interactive charts, score gauges, and evidence citations.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js 14)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Overview  │ │AI Research│ │Why Moved │ │Stock Doc │ │ News   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                              │                                    │
│                    TanStack Query                                 │
└──────────────────────────────┼────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Market    │ │Financial │ │Health    │ │Anomaly   │ │Research│ │
│  │Data      │ │Data      │ │Scorer    │ │Detector  │ │Agent   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│        │             │            │            │          │       │
│        └─────────────┴────────────┴────────────┴──────────┘       │
│                              │                                    │
│                        yfinance + VADER +                         │
│                        IsolationForest + ChromaDB                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 1. AI Stock Research Agent
- Generates structured investment thesis with **bull/bear cases**
- Identifies **catalysts**, **risks**, and **watch items**
- Provides **detailed sections**: Financial Health, Valuation, Growth, Competitive Position, Technical, Sentiment
- Every claim includes **evidence citations** with source links
- Rule-based (no LLM hallucination for core analysis)

### 2. Why Did This Stock Move?
- **Isolation Forest** anomaly detection on price/volume/z-score
- **6 driver categories**: Earnings, Analyst, Macro, Company, Technical, Sector
- **Confidence tiers**: High Confidence → Evidence → Correlation → Possible
- Links anomalies to **news events** with sentiment analysis
- Timeline visualization of price movements

### 3. AI Stock Doctor (6-Factor Health Score)
| Factor | Weight | Metrics |
|--------|--------|---------|
| Financial Health | 30% | Current Ratio, Debt/Equity, Interest Coverage, FCF Margin |
| Growth | 20% | Revenue YoY, EPS YoY, FCF YoY, 3Y CAGR |
| Momentum | 15% | 1M/3M/6M/12M returns, RSI, 50/200 DMA |
| Valuation | 15% | P/E vs Sector, PEG, P/FCF, EV/EBITDA |
| Sentiment | 10% | News sentiment, Analyst revisions, Short interest |
| Risk | 10% | Beta, Volatility, Max Drawdown, VaR, Altman Z |

- **Score breakdown** with gauges and horizontal bars
- **Detailed metric cards** with percentile rankings
- **Traffic light** status indicators (green/yellow/red)

---

## 🚀 Quick Start

### Prerequisites
- **Docker** & **Docker Compose** (recommended)
- OR: Python 3.11+, Node.js 20+, npm

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd "AI stock research agent"

# Copy environment files
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys (ANTHROPIC_API_KEY required for LLM features)

# Start all services
docker-compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

#### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
cp .env.local.example .env.local  # or create manually

# Run development server
npm run dev
```

---

## 📁 Project Structure

```
AI stock research agent/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   └── stocks.py          # 10 API endpoints
│   │   ├── core/
│   │   │   └── config.py          # Settings management
│   │   ├── ml/
│   │   │   ├── health_scorer.py   # 6-factor scoring engine
│   │   │   ├── sentiment_classifier.py  # VADER + financial lexicon
│   │   │   ├── anomaly_detector.py      # Isolation Forest
│   │   │   └── vector_store.py          # ChromaDB wrapper
│   │   ├── models/
│   │   │   └── schemas.py         # Pydantic models
│   │   ├── services/
│   │   │   ├── market_data.py     # yfinance integration
│   │   │   ├── financial_data.py  # Fundamentals from SEC
│   │   │   ├── news_service.py    # News + sentiment
│   │   │   └── research_agent.py  # Thesis generation
│   │   └── main.py                # FastAPI app entry
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                    # Landing page
│   │   │   └── stock/[ticker]/page.tsx     # Dashboard
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   │   ├── PriceChart.tsx          # Recharts price chart
│   │   │   │   └── HealthGauge.tsx         # SVG gauge + bars
│   │   │   └── dashboard/
│   │   │       ├── OverviewTab.tsx
│   │   │       ├── ResearchTab.tsx
│   │   │       ├── MovementTab.tsx
│   │   │       ├── DoctorTab.tsx
│   │   │       ├── NewsTab.tsx
│   │   │       └── EvidenceTab.tsx
│   │   └── hooks/
│   │       └── useStockData.ts             # TanStack Query hooks
│   ├── package.json
│   ├── next.config.js
│   ├── Dockerfile
│   └── .env.local
├── docker-compose.yml
└── README.md
```

---

## 🔧 Configuration

### Backend Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | For LLM-powered research synthesis |
| `FMP_API_KEY` | No | Financial Modeling Prep for enhanced fundamentals |
| `NEWS_API_KEY` | No | NewsAPI for additional news sources |
| `CHROMA_PERSIST_DIR` | No | Vector store path (default: `./chroma_db`) |
| `CORS_ORIGINS` | No | Allowed origins (default: `http://localhost:3000`) |
| `BACKEND_HOST` | No | Server host (default: `0.0.0.0`) |
| `BACKEND_PORT` | No | Server port (default: `8000`) |

*Required only for LLM synthesis features; core quantitative features work without it.

### Frontend Environment Variables (`.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | No | Backend URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_GA_ID` | No | Google Analytics ID for demo tracking |

---

## 📡 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/stocks/search?q={query}` | Search tickers |
| `GET /api/v1/stocks/{symbol}/quote` | Real-time quote |
| `GET /api/v1/stocks/{symbol}/historical?period=1y` | Price history |
| `GET /api/v1/stocks/{symbol}/fundamentals` | TTM financials |
| `GET /api/v1/stocks/{symbol}/key-stats` | Key ratios & stats |
| `GET /api/v1/stocks/{symbol}/news?limit=20` | News with sentiment |
| `GET /api/v1/stocks/{symbol}/health` | 6-factor health score |
| `GET /api/v1/stocks/{symbol}/movement` | Anomaly + news correlation |
| `GET /api/v1/stocks/{symbol}/research` | AI research report |
| `GET /api/v1/stocks/{symbol}/evidence` | Source documents |
| `GET /api/v1/stocks/market-news` | General market news |

**Interactive docs**: `http://localhost:8000/docs`

---

## 🎨 UI/UX Highlights

- **Bloomberg-style dark theme** with green/red/amber semantics
- **6-tab dashboard**: Overview → AI Research → Why It Moved → Stock Doctor → News → Evidence
- **Interactive charts**: Price charts with volume, anomalies, technical overlays
- **Circular gauge** + horizontal bars for health score breakdown
- **Evidence panel** with expandable citations and source links
- **Responsive**: Mobile-first, works on all screen sizes
- **Loading states**: Skeletons, spinners, error boundaries
- **Financial disclaimer** prominently displayed

---

## ⚠️ Disclaimer

> **This platform is for educational and informational purposes only. It does not constitute financial advice, investment recommendations, or an offer to buy/sell securities. The quantitative scores and analysis are derived from historical data and rule-based models — past performance does not guarantee future results. Always conduct your own due diligence and consult a qualified financial advisor before making investment decisions.**

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.11 |
| **Frontend** | Next.js 14, React 18, TypeScript |
| **Styling** | Tailwind CSS |
| **Charts** | Recharts |
| **Data Fetching** | TanStack Query (React Query) |
| **Market Data** | yfinance |
| **Sentiment** | VADER + Financial Lexicon (100+ terms) |
| **ML/Anomaly** | scikit-learn (Isolation Forest) |
| **Vector Store** | ChromaDB |
| **Caching** | TTLCache (cachetools) |
| **Containerization** | Docker, Docker Compose |

---

## 📝 Development Notes

### Adding New Features
1. Backend: Add endpoint in `backend/app/api/v1/stocks.py`
2. Backend: Add service logic in `backend/app/services/`
3. Frontend: Add hook in `frontend/src/hooks/useStockData.ts`
4. Frontend: Add component in `frontend/src/components/dashboard/`
5. Frontend: Add tab to dashboard page

### Testing API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Get quote
curl http://localhost:8000/api/v1/stocks/AAPL/quote

# Get health score
curl http://localhost:8000/api/v1/stocks/AAPL/health

# Get movement analysis
curl http://localhost:8000/api/v1/stocks/AAPL/movement
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `yfinance` rate limited | Add delay, use caching (TTLCache built-in) |
| ChromaDB import error | Use `chromadb.PersistentClient` without deprecated Settings |
| CORS errors | Check `CORS_ORIGINS` in backend `.env` |
| Frontend can't reach API | Verify `NEXT_PUBLIC_API_URL` in frontend `.env.local` |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

MIT License - feel free to use for hackathons, learning, or commercial projects.

---

## 🙏 Acknowledgments

- **yfinance** for free market data
- **VADER Sentiment** for sentiment analysis
- **ChromaDB** for vector storage
- **Recharts** for beautiful visualizations
- **Tailwind CSS** for rapid UI development
- **FastAPI** for high-performance Python APIs# Trigger Vercel rebuild
