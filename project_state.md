# Project State — AI Weekly News Platform

_Last updated: 2026-05-30_

## Current Milestone

**Milestone 2 — Database Layer** (awaiting user validation)

## Completed Milestones

- **Milestone 1 — Project Bootstrap** ✅ (validated: containers up, `/health`
  and `/health/ready` return ok)

## Pending Milestones

- Milestone 3 — pgvector Integration
- Milestone 4 — News Source Framework (RSS, NewsAPI, GNews adapters)
- Milestone 5 — Ingestion Pipeline (Fetch → Normalize → Save)
- Milestone 6 — Embedding Pipeline
- Milestone 7 — Deduplication Engine
- Milestone 8 — LangGraph Daily Workflow
- Milestone 9 — Weekly Clustering
- Milestone 10 — Weekly Report Generation
- Milestone 11 — Scheduling
- Milestone 12 — API Layer
- Milestone 13 — Deployment Preparation

## Architecture Decisions

- **Layout:** All backend code lives under `backend/` following the prescribed
  structure (`app/{api,core,db,models,services,workers,graphs,prompts}`,
  `tests/`, `migrations/`, `docker/`, `requirements/`).
- **App factory:** `app.main:create_app()` builds the FastAPI instance and is
  the ASGI entrypoint (`app.main:app`).
- **Configuration:** Centralized in `app/core/config.py` via
  `pydantic-settings`. `get_settings()` is `lru_cache`-d. Derived
  `database_url` / `redis_url` properties feed all services.
- **Health checks:** `/health` (liveness) and `/health/ready` (readiness,
  pings Postgres + Redis). Readiness is the Milestone 1 validation surface.
- **Requirements split:** `requirements/base.txt` (runtime) and
  `requirements/dev.txt` (adds pytest, httpx).
- **ORM:** SQLAlchemy 2.0 (typed `Mapped`/`mapped_column`), sync engine bound
  to the psycopg v3 driver (`postgresql+psycopg://`). Shared `Base`, `engine`,
  `SessionLocal`, and a `get_db()` dependency live in `app/db/base.py`.
- **Migrations:** Alembic. `alembic.ini` has `script_location = migrations`;
  `migrations/env.py` injects the DB URL from settings and targets
  `Base.metadata` with all models imported (so autogenerate sees them).
- **Dev mount:** the `api` service mounts `.:/app` so code changes and
  generated migration files persist to the host without rebuilding.

## Database Schema Decisions

- Postgres image is `pgvector/pgvector:pg16` so the `vector` extension is
  available without a custom build (used from Milestone 3 onward).
- **Tables (initial migration `71636b66f5e3`):**
  - `articles` — fetched news items. `url` UNIQUE (exact-dup key); indexed on
    `source` and `published_at`; `raw` JSONB keeps the original payload.
    (An `embedding` vector column is added in Milestone 3.)
  - `stories` — canonical aggregated stories. `category` (filled M9),
    `first_seen_at`/`last_seen_at`; indexed on `category`, `last_seen_at`.
  - `story_sources` — association of a story to its source articles.
    `UNIQUE(article_id)` enforces one story per article; `UNIQUE(story_id,
    article_id)` prevents dup pairs; both FKs `ON DELETE CASCADE`.
- **Relationship model:** story↔article handled solely through `story_sources`
  (no `story_id` on `articles`) to avoid two competing sources of truth.

## Known Issues

- None.

## Environment Variables

Managed via `backend/.env` (template: `backend/.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | AI Weekly News Platform | Display name |
| `ENVIRONMENT` | local | Environment label |
| `DEBUG` | true | FastAPI debug flag |
| `API_V1_PREFIX` | /api/v1 | API route prefix (used later) |
| `POSTGRES_HOST` | localhost (`db` in compose) | Postgres host |
| `POSTGRES_PORT` | 5432 | Postgres port |
| `POSTGRES_USER` | ainews | Postgres user |
| `POSTGRES_PASSWORD` | ainews | Postgres password |
| `POSTGRES_DB` | ainews | Postgres database |
| `REDIS_HOST` | localhost (`redis` in compose) | Redis host |
| `REDIS_PORT` | 6379 | Redis port |
| `REDIS_DB` | 0 | Redis logical DB |
| `OPENAI_API_KEY` | _(empty)_ | Required from Milestone 6 |
