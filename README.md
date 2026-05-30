# AI Weekly News Platform

An automated pipeline that fetches AI news from multiple sources, deduplicates
it semantically, clusters it into topics, and generates a weekly AI report —
all served over a REST API and scheduled to run on its own.

> **Status:** Milestones 1–12 complete (core platform). Milestone 13
> (deployment) is deferred — verifying & hardening locally first; the
> deployment platform is not yet chosen.

---

## What it does

```
            ┌──────────── daily (Celery beat) ────────────┐
            ▼                                              │
  RSS / NewsAPI / GNews                                    │
            │  fetch                                       │
            ▼                                              │
        Normalize ──► Save (Postgres)                      │
            │                                              │
            ▼  embed (Gemini, 1536-dim, pgvector)          │
        Embeddings                                         │
            │                                              │
            ▼  deduplicate (cosine similarity)             │
   Canonical Stories ◄── many Sources                      │
            │                                              │
            ▼  weekly (Celery beat)                        │
     Cluster into topics ──► Generate Markdown report ─────┘
            │
            ▼
        REST API  (/reports, /reports/latest, /stories, /health)
```

1. **Fetch** AI news from RSS (no key), and optionally NewsAPI / GNews.
2. **Ingest** — normalize and store articles in PostgreSQL (dedup by URL).
3. **Embed** — generate 1536-dim embeddings (Gemini) stored via **pgvector**.
4. **Deduplicate** — merge near-identical articles into one canonical **Story**
   with many **Sources** using cosine similarity.
5. **Cluster** the week's stories into topics (OpenAI, Anthropic, Funding,
   Research, Startups).
6. **Report** — an LLM writes a Markdown weekly report (Major Headlines,
   Research, Funding, New Models, Outlook).
7. **Serve** everything over a FastAPI REST API.
8. **Schedule** daily ingestion and the weekly report via Celery + Redis.

---

## Tech stack

| Area | Choice |
| --- | --- |
| Language / API | Python 3.12, FastAPI |
| Orchestration | LangGraph |
| Database | PostgreSQL 16 + **pgvector** |
| ORM / migrations | SQLAlchemy 2.0, Alembic |
| Task queue / scheduler | Celery + Redis (broker, beat) |
| Embeddings + LLM | **Gemini free tier** (`gemini-embedding-001`, `gemini-2.5-flash`) — swappable to OpenAI |
| Containers | Docker, Docker Compose |
| Tests | Pytest |

> **AI provider:** Currently Gemini (free tier). The embedding dimension is
> fixed at **1536** so the pgvector column works for both Gemini and OpenAI —
> switching to OpenAI later needs no migration.

---

## Prerequisites

- **Docker Desktop** (running).
- A **Gemini API key** — free at https://aistudio.google.com/apikey
  (needed for embeddings + report generation; RSS fetching works without it).

---

## Quick start

```bash
cd backend

# 1. Configure environment
cp .env.example .env
#   then edit .env and set:  GEMINI_API_KEY=your_key_here

# 2. Build & start everything (api, postgres+pgvector, redis, worker, beat)
docker compose up --build -d

# 3. Apply database migrations
docker compose exec api alembic upgrade head

# 4. Verify
curl http://localhost:8000/health          # liveness
curl http://localhost:8000/health/ready     # checks Postgres + Redis
```

Open the interactive API docs at **http://localhost:8000/docs**.

> All `docker compose` commands must be run from the `backend/` directory
> (that's where `docker-compose.yml` lives).

---

## Running the pipeline manually

Run the whole daily pipeline as one LangGraph workflow:

```bash
docker compose exec api python -c "import json; from app.graphs import run_daily_workflow; print(json.dumps(run_daily_workflow(limit_per_provider=10), indent=2))"
```

Or run individual stages:

```bash
# Fetch (no DB writes) — see what providers return
docker compose exec api python -c "from app.services.news import fetch_news; print(len(fetch_news(limit_per_provider=5)), 'articles')"

# Ingest (fetch -> normalize -> save)
docker compose exec api python -c "from app.db.base import SessionLocal; from app.services.ingestion import ingest_news; print(ingest_news(SessionLocal(), limit_per_provider=10).as_dict())"

# Embed pending articles (Gemini)
docker compose exec api python -c "from app.db.base import SessionLocal; from app.services.embedding_pipeline import embed_pending_articles; print(embed_pending_articles(SessionLocal()).as_dict())"

# Deduplicate into stories
docker compose exec api python -c "from app.db.base import SessionLocal; from app.services.dedup import deduplicate_articles; print(deduplicate_articles(SessionLocal()).as_dict())"

# Cluster the week's stories into topics
docker compose exec api python -c "from app.db.base import SessionLocal; from app.services.clustering import cluster_weekly_stories; print(cluster_weekly_stories(SessionLocal()).as_dict())"

# Generate the weekly report (LLM)
docker compose exec api python -c "from app.db.base import SessionLocal; from app.services.report import generate_weekly_report; r=generate_weekly_report(SessionLocal()); print(r.title, '|', r.story_count, 'stories')"
```

---

## Scheduling (Celery)

The `worker` and `beat` containers run automatically. Beat schedule (UTC,
configurable in `.env`):

- **Daily ingestion** — 06:00 (`tasks.daily_ingestion`)
- **Weekly report** — Mon 07:00 (`tasks.weekly_report`)

Trigger a job on demand through the broker:

```bash
docker compose exec api python -c "from app.workers.celery_app import celery_app; print(celery_app.send_task('tasks.daily_ingestion', kwargs={'limit_per_provider':10}).get(timeout=180))"

# Watch worker logs
docker compose logs -f worker
```

---

## API endpoints

| Method & path | Description |
| --- | --- |
| `GET /health` | Liveness probe |
| `GET /health/ready` | Readiness — checks Postgres + Redis |
| `GET /reports` | List report summaries (`?limit=&offset=`) |
| `GET /reports/latest` | Latest report with full Markdown |
| `GET /reports/{id}` | A specific report |
| `GET /stories` | List stories + source articles (`?category=&limit=&offset=`) |

Examples:

```bash
curl "http://localhost:8000/reports/latest"
curl "http://localhost:8000/stories?category=OpenAI&limit=5"
```

---

## Testing

```bash
cd backend
docker compose exec -T api pip install -r requirements/dev.txt
docker compose exec -T -e PYTHONPATH=/app api python -m pytest tests/ -q
```

The suite is offline/deterministic (no live network or LLM calls) and uses the
running Postgres for the DB-backed tests.

---

## Configuration

Settings are loaded from `backend/.env` (template: `.env.example`) via
pydantic-settings. Key variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | _(empty)_ | **Required** for embeddings + reports |
| `EMBEDDING_PROVIDER` / `LLM_PROVIDER` | `gemini` | `gemini` or `openai` |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model |
| `GEMINI_CHAT_MODEL` | `gemini-2.5-flash` | Report model |
| `EMBEDDING_DIM` | `1536` | Vector dimension (structural) |
| `DEDUP_DISTANCE_THRESHOLD` | `0.15` | Max cosine distance to merge articles |
| `WEEKLY_WINDOW_DAYS` | `7` | Window for clustering / reports |
| `NEWS_QUERY` | `artificial intelligence` | Search query for NewsAPI/GNews |
| `NEWSAPI_API_KEY` / `GNEWS_API_KEY` | _(empty)_ | Enable those providers |
| `RSS_FEEDS` | 3 AI feeds | JSON list override |
| `DAILY_INGESTION_HOUR` / `WEEKLY_REPORT_HOUR` | `6` / `7` | Beat schedule (UTC) |

**Switching to OpenAI later:** set `EMBEDDING_PROVIDER=openai`,
`LLM_PROVIDER=openai`, add `OPENAI_API_KEY`, and add `openai` to
`requirements/base.txt`. No migration needed (dim stays 1536).

---

## Project structure

```
backend/
├── app/
│   ├── api/            # FastAPI routers (health, reports, stories) + schemas
│   ├── core/           # config.py (pydantic-settings)
│   ├── db/             # SQLAlchemy engine, session, Base
│   ├── models/         # Article, Story, StorySource, Report
│   ├── services/
│   │   ├── news/       # provider adapters (RSS, NewsAPI, GNews) + fetch_news
│   │   ├── embeddings/ # embedding providers (Gemini/OpenAI) + factory
│   │   ├── llm/        # LLM providers (Gemini/OpenAI) + factory
│   │   ├── ingestion.py
│   │   ├── embedding_pipeline.py
│   │   ├── dedup.py
│   │   ├── clustering.py
│   │   └── report.py
│   ├── graphs/         # LangGraph daily workflow
│   ├── workers/        # Celery app + tasks
│   ├── prompts/        # weekly report prompt
│   └── main.py         # FastAPI app factory
├── migrations/         # Alembic migrations
├── tests/              # Pytest suite
├── docker/Dockerfile
├── docker-compose.yml
└── requirements/       # base.txt, dev.txt
```

---

## Common commands

```bash
cd backend
docker compose up --build -d     # start (rebuild if deps/code changed)
docker compose ps                # service status
docker compose logs -f api       # tail API logs
docker compose exec api alembic upgrade head   # run migrations
docker compose down              # stop (keeps DB volume)
docker compose down -v           # stop + wipe DB volume (fresh start)
```

---

## Data model

- **articles** — fetched news items (`url` unique; `embedding vector(1536)`).
- **stories** — canonical stories aggregated from articles; carry a `category`.
- **story_sources** — links a story to its source articles (one story per
  article; one is `is_primary`).
- **reports** — generated weekly Markdown reports.

---

## Notes & known limitations

- **Gemini free-tier quotas** apply. `gemini-2.0-flash` had a 0 free-tier quota
  for text generation on the test key, so the default chat model is
  `gemini-2.5-flash`. Embeddings use a separate, more generous quota.
- Dedup/cluster thresholds are heuristic and tunable via env vars.
- Ingestion assumes a single scheduled job (no concurrent-run guard).
- Deployment (Milestone 13) is intentionally deferred — see
  `project_state.md`.
