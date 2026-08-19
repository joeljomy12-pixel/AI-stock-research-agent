# GitHub Deployment & Free Cloud Hosting Guide

This document provides step-by-step instructions to deploy the AI Stock Research Agent to **GitHub** (securely) and then to **free cloud platforms** (Railway for backend, Vercel for frontend).

---

## 🔒 Security First: What NOT to Commit

### Files That Are Already Ignored (via `.gitignore`)
```
.env                          # ❌ NEVER commit - contains secrets
.env.local                    # ❌ NEVER commit
.env.*.local                  # ❌ NEVER commit
backend/.env                  # ❌ NEVER commit
backend/chroma_db/            # ❌ Local vector store
frontend/.env.local           # ❌ NEVER commit
```

### Files That ARE Safe to Commit (Templates)
```
backend/.env.example          # ✅ Template - no real secrets
frontend/.env.example         # ✅ Template - no real secrets
docker-compose.yml            # ✅ Uses ${VAR} substitution
```

---

## 📦 Step 1: Push to GitHub Securely

```bash
# 1. Initialize git (if not already)
cd "C:\Users\joelj\Projects\AI stock research agent"
git init

# 2. Add all files (respecting .gitignore)
git add .

# 3. Commit
git commit -m "Initial commit: AI Stock Research Agent - hackathon ready"

# 4. Create GitHub repo and push
# Option A: Via GitHub CLI (recommended)
gh repo create stock-intelligence --public --source=. --push

# Option B: Via GitHub website
# 1. Go to github.com/new
# 2. Create repo "stock-intelligence"
# 3. Run:
git remote add origin https://github.com/YOUR_USERNAME/stock-intelligence.git
git branch -M main
git push -u origin main
```

✅ **Verify**: Check GitHub repo - no `.env` files should appear!

---

## 🚀 Step 2: Deploy Backend to Railway (Free Tier)

### Why Railway?
- **$5/month free credit** (enough for hobby projects)
- Native Docker support
- Automatic HTTPS
- Easy environment variable management

### Deployment Steps:

#### Option A: Railway Dashboard (Easiest)
1. Go to [railway.app](https://railway.app) → Sign up with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `stock-intelligence` repo
4. Select the `backend` folder as root
5. Railway auto-detects `Dockerfile` and `railway.json`
6. **Add Environment Variables** in Railway dashboard:
   ```
   ANTHROPIC_API_KEY=your_key_here        # Optional - for LLM features
   FMP_API_KEY=your_key_here              # Optional - enhanced fundamentals
   NEWS_API_KEY=your_key_here             # Optional - additional news
   CHROMA_PERSIST_DIR=/app/chroma_db
   CORS_ORIGINS_STR=https://your-frontend.vercel.app
   BACKEND_HOST=0.0.0.0
   BACKEND_PORT=$PORT
   ```
7. Click "Deploy" → Wait for build → Get your URL (e.g., `https://stock-intelligence-api.railway.app`)

#### Option B: Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link
railway login
railway link

# Deploy
railway up

# Set environment variables
railway variables set ANTHROPIC_API_KEY=your_key
railway variables set CORS_ORIGINS_STR=https://your-frontend.vercel.app
```

### Verify Backend:
```bash
curl https://your-backend.railway.app/health
# Expected: {"status":"healthy","service":"stock-intelligence-api"}
```

---

## 🎨 Step 3: Deploy Frontend to Vercel (Free Tier)

### Why Vercel?
- **Unlimited personal projects free**
- Native Next.js support
- Automatic HTTPS
- Edge network globally

### Deployment Steps:

#### Option A: Vercel Dashboard (Easiest)
1. Go to [vercel.com](https://vercel.com) → Sign up with GitHub
2. Click "Add New..." → "Project"
3. Import your `stock-intelligence` repo
4. **Framework Preset**: Next.js (auto-detected)
5. **Root Directory**: `frontend`
6. **Environment Variables**:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   NEXT_PUBLIC_GA_ID=                  # Optional
   ```
7. Click "Deploy" → Get your URL (e.g., `https://stock-intelligence.vercel.app`)

#### Option B: Vercel CLI
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy from frontend folder
cd frontend
vercel

# Follow prompts:
# - Link to existing project? No
# - Project name: stock-intelligence
# - Directory: ./
# - Override settings? No

# Add environment variables
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://your-backend.railway.app
```

### Update Backend CORS:
After getting your Vercel URL, update Railway:
```bash
railway variables set CORS_ORIGINS_STR=https://your-frontend.vercel.app
```

---

## ⚙️ Step 4: Configure GitHub Actions CI/CD

The `.github/workflows/ci.yml` is already configured! It runs on every push to `main`:

### What It Does:
| Job | Purpose |
|-----|---------|
| `backend-lint` | Ruff + MyPy type checking |
| `backend-test` | Module import verification |
| `backend-verify` | Core feature tests (health, movement, research) |
| `frontend-lint` | ESLint + TypeScript check |
| `frontend-build` | Next.js production build |
| `docker-build` | Multi-stage Docker build test |
| `security-scan` | Trivy vuln scan + TruffleHog secret scan |

### Required GitHub Secrets:
Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value | Required |
|--------|-------|----------|
| `RAILWAY_TOKEN` | From Railway account settings | For auto-deploy |
| `VERCEL_TOKEN` | From Vercel account settings | For auto-deploy |
| `VERCEL_ORG_ID` | From Vercel project settings | For auto-deploy |
| `VERCEL_PROJECT_ID` | From Vercel project settings | For auto-deploy |
| `NEXT_PUBLIC_API_URL` | Your Railway backend URL | For frontend build |

---

## 🔧 Step 5: Local Development Setup

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with your keys (optional - core features work without)
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🐳 Step 6: Docker Compose (Alternative)

```bash
# From project root
cp backend/.env.example backend/.env
# Edit backend/.env

docker compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

---

## ✅ Verification Checklist

After deployment, verify all features work:

### Backend Health
- [ ] `GET /health` returns `{"status":"healthy"}`
- [ ] `GET /api/v1/stocks/AAPL/quote` returns price data
- [ ] `GET /api/v1/stocks/AAPL/health` returns 6-factor score (0-100)
- [ ] `GET /api/v1/stocks/AAPL/movement` returns anomaly detection
- [ ] `GET /api/v1/stocks/AAPL/research` returns thesis with citations

### Frontend Features
- [ ] Landing page loads with search
- [ ] Search finds tickers (AAPL, NVDA, TSLA)
- [ ] Stock dashboard loads 6 tabs
- [ ] Overview: Price chart + key metrics
- [ ] AI Research: Bull/Bear cases with citations
- [ ] Why It Moved: Anomaly + news drivers
- [ ] Stock Doctor: 6 circular gauges + overall score
- [ ] News: Sentiment-tagged articles
- [ ] Evidence: Source documents with relevance

### Security
- [ ] No `.env` files in GitHub repo
- [ ] HTTPS on both frontend and backend
- [ ] CORS configured correctly
- [ ] Security headers present (check browser dev tools)

---

## 💰 Cost Summary (Free Tier)

| Platform | Free Tier Limits | Estimated Cost |
|----------|------------------|----------------|
| GitHub | Unlimited public repos | $0 |
| Railway | $5/month credit | $0 (within credit) |
| Vercel | Unlimited personal | $0 |
| **Total** | | **$0/month** |

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend builds but crashes | Check Railway logs; ensure `PORT` env var used |
| Frontend can't reach backend | Verify `NEXT_PUBLIC_API_URL` and CORS origins |
| ChromaDB slow on first load | First run downloads ~80MB ONNX model; wait 30-60s |
| yfinance rate limited | Built-in TTLCache handles retries; wait 30-60s |
| Docker build fails | Check Dockerfile paths; ensure `output: 'standalone'` in next.config.js |
| TypeScript errors | Run `npm run lint` locally first |

---

## 📚 Key Files for Deployment

```
├── .github/workflows/ci.yml       # CI/CD pipeline
├── backend/
│   ├── Dockerfile                 # Multi-stage Python build
│   ├── railway.json               # Railway config
│   ├── render.yaml                # Render config (alternative)
│   ├── requirements.txt           # Python deps
│   └── .env.example               # Env template
├── frontend/
│   ├── Dockerfile                 # Multi-stage Next.js build
│   ├── vercel.json                # Vercel config
│   ├── next.config.js             # Standalone output config
│   ├── package.json               # Node deps
│   └── .env.example               # Env template
├── docker-compose.yml             # Local dev orchestration
└── .gitignore                     # Security - ignores all .env files
```

---

_Last updated: 2026-08-18_