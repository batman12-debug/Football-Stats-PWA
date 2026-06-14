# GoalMind

World Cup 2026 match prediction web app. Predicts match outcomes using team statistics and historical data from API-Football.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| Backend | Python FastAPI + Uvicorn |
| Database | Supabase (PostgreSQL) |
| Cache | Upstash Redis |
| Data | API-Football (api-sports.io) |

## Project Structure

```
.
├── backend/
│   └── app/
│       ├── main.py              # FastAPI entry point
│       ├── config.py            # Environment config (Pydantic)
│       ├── scheduler.py         # APScheduler cron jobs
│       ├── routers/             # API routes
│       ├── services/            # Business logic & integrations
│       ├── models/              # Pydantic data models
│       └── db/                  # Supabase client
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # React UI components
│   ├── lib/                     # API client
│   └── types/                   # TypeScript types
└── README.md
```

## Prerequisites

- Node.js 18+
- Python 3.11+
- API-Football API key ([api-sports.io](https://www.api-football.com/))
- Supabase project
- Upstash Redis instance

## Setup

### 1. Clone and configure environment

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Frontend
cp frontend/.env.example frontend/.env.local
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies (when requirements.txt is added)
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`. Health check: `GET /health`.

### 3. Frontend

```bash
cd frontend

# Install dependencies (when package.json is added)
npm install

# Run development server
npm run dev
```

Frontend will be available at `http://localhost:3000`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `API_FOOTBALL_KEY` | API-Football API key |
| `API_FOOTBALL_BASE_URL` | API-Football base URL |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon or service key |
| `UPSTASH_REDIS_URL` | Upstash Redis REST URL |
| `UPSTASH_REDIS_TOKEN` | Upstash Redis REST token |
| `ENVIRONMENT` | `development` or `production` |
| `CORS_ORIGINS` | Allowed frontend origins |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: `http://localhost:8000`) |

## API Routes (planned)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/teams` | List teams |
| `GET` | `/teams/{id}` | Team details |
| `GET` | `/matches` | List matches |
| `GET` | `/matches/{id}` | Match details |
| `GET` | `/predictions/{match_id}` | Get prediction |
| `POST` | `/predictions/{match_id}/generate` | Generate prediction |

## Database Setup

Run the initial migration in your Supabase SQL editor:

```bash
# File: backend/supabase/migrations/001_initial_schema.sql
```

This creates `teams` and `fixtures` tables used by the data sync layer.

## Development Status

The data layer (API-Football client, Redis cache, Supabase sync, scheduler) is implemented. Prediction engine and API routes are still placeholders.
