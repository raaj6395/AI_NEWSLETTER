# Project State — AI Weekly News Platform

_Last updated: 2026-05-30_

## Current Milestone

**Milestone 1 — Project Bootstrap** (awaiting user validation)

## Completed Milestones

- _None yet confirmed._ Milestone 1 implemented, pending user confirmation.

## Pending Milestones

- Milestone 2 — Database Layer (articles, stories, story_sources + Alembic)
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

## Database Schema Decisions

- Postgres image is `pgvector/pgvector:pg16` so the `vector` extension is
  available without a custom build (used from Milestone 3 onward).
- No tables yet — schema and Alembic migrations land in Milestone 2.

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
