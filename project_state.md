# Project State — AI Weekly News Platform

_Last updated: 2026-05-30_

## Current Milestone

**Milestone 12 — API Layer** (awaiting user validation) — final core milestone.
Only Milestone 13 (Deployment Preparation) remains.

## Completed Milestones

- **Milestone 1 — Project Bootstrap** ✅ (validated: containers up, `/health`
  and `/health/ready` return ok)
- **Milestone 2 — Database Layer** ✅ (committed `dc5e1b5`; tables migrated,
  downgrade/upgrade roundtrip verified)
- **Milestone 3 — pgvector Integration** ✅ (committed `7ffad2b`; extension
  enabled, embedding column + HNSW index, similarity verified)
- **Milestone 4 — News Source Framework** ✅ (committed `f5daca8`; adapter
  pattern, `fetch_news()` validated live against RSS). Same commit set the
  AI provider to Gemini free tier.
- **Milestone 5 — Ingestion Pipeline** ✅ (committed `c8c05d4`; 15 real
  articles ingested, re-run idempotent)
- **Milestone 6 — Embedding Pipeline** ✅ (committed `a6596fc`; 15 articles
  embedded via Gemini, 1536-dim, real cosine distances)
- **Milestone 7 — Deduplication Engine** ✅ (committed `20b8dc0`; deterministic
  merge test + real run with no false merges)
- **Milestone 8 — LangGraph Daily Workflow** ✅ (committed `af084b9`; graph
  runs end-to-end and is idempotent)
- **Milestone 9 — Weekly Clustering** ✅ (committed `88172b1`; 23 stories →
  all 5 categories)
- **Milestone 10 — Weekly Report Generation** ✅ (committed `bce0be5`; real
  report with all 5 sections persisted)
- **Milestone 11 — Scheduling** ✅ (committed `0fa5b92`; task executed via
  worker through the broker; beat running)

## Pending Milestones

- Milestone 13 — Deployment Preparation

## Architecture Decisions

- **AI provider (Gemini now, OpenAI later):** `embedding_provider` /
  `llm_provider` settings select the active provider; both Gemini and OpenAI
  settings are present. Currently **Gemini free tier** (`gemini-embedding-001`
  for embeddings, `gemini-2.0-flash` for chat). `embedding_dim` is fixed at
  **1536** so the `articles.embedding vector(1536)` column and HNSW index are
  identical across providers — Gemini emits 1536-dim vectors on request and
  OpenAI `text-embedding-3-small` is natively 1536, so switching providers
  needs **no migration**. Provider client wiring lands with Milestone 6.
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
- **News framework (adapter pattern):** lives in `app/services/news/`.
  `NewsProvider` (ABC) defines `_fetch()`; `fetch()` wraps it so one provider's
  failure can't abort the batch. Adapters: `RSSProvider` (feedparser, no key),
  `NewsAPIProvider`, `GNewsProvider` (httpx). All emit a normalized
  `FetchedArticle` (pydantic) — distinct from the `Article` ORM model.
  `build_providers()` enables providers from config (RSS if feeds set; NewsAPI/
  GNews only if their key is set). `fetch_news()` runs all enabled providers
  and de-duplicates by URL. Validated live: RSS returned real articles.
- **Ingestion pipeline:** `app/services/ingestion.py`. `normalize()` maps a
  `FetchedArticle` onto `Article` columns (truncates `source`/`author` to 255;
  makes `raw` JSON-safe for JSONB via `json.dumps(..., default=str)`).
  `save_articles()` de-dups by URL within the batch and against existing rows,
  bulk-inserts the new ones, and returns an `IngestionResult`
  (fetched/unique/saved/duplicates). `ingest_news(db)` chains
  fetch → normalize → save. Embeddings left NULL (filled in M6). Single-job
  use assumed; check-then-insert (no concurrent-run guard yet). Validated:
  15 real articles saved, re-run saved 0.
- **Embedding pipeline (provider-agnostic):** `app/services/embeddings/`
  defines `EmbeddingProvider` (returns unit-normalized vectors), with
  `GeminiEmbeddingProvider` (google-genai `embed_content`, explicit
  `output_dimensionality=1536`, `SEMANTIC_SIMILARITY` task) and a lazy-import
  `OpenAIEmbeddingProvider` for later. `get_embedding_provider()` picks by
  `embedding_provider`. `app/services/embedding_pipeline.py`:
  `build_embedding_input()` (title + description/content, truncated to
  `embedding_input_max_chars`), `embed_articles()` (embed an explicit list,
  per-batch failure isolation, commit per batch), and `embed_pending_articles()`
  (queries `embedding IS NULL` then delegates). Vectors L2-normalized.
  Validated: all 15 articles embedded via Gemini (1536-dim), real cosine
  distances (~0.22). google-genai pinned at 2.7.0.
- **Deduplication engine:** `app/services/dedup.py`. Incremental greedy
  nearest-neighbour by cosine distance: for each article, `find_matching_story`
  finds the nearest already-assigned article (join articles↔story_sources,
  `embedding <=> q` ordered, limit 1); if distance ≤ `dedup_distance_threshold`
  (default 0.15) the article is attached as a non-primary `StorySource` of that
  story, otherwise a new `Story` is created with the article as primary.
  Story `first/last_seen_at` window widened on attach. `flush()` per article
  so within-run assignments are matchable. `deduplicate_articles(db)` processes
  all unassigned (embedding set, no story); pass an explicit `articles` list to
  scope (used for test isolation) — matching always searches all assigned
  articles so new items merge into pre-existing stories.
  Validated: deterministic test (2 near-identical + 1 distinct → 1 story with
  2 sources + 1 separate story, exactly 1 primary). On the 15 real articles at
  threshold 0.15 → 15 stories, 0 false merges (nearest ~0.22 > threshold).
- **LangGraph daily workflow:** `app/graphs/daily_workflow.py`. A compiled
  `StateGraph[DailyWorkflowState]` with nodes fetch → ingest → embed →
  deduplicate (START→…→END). Each node opens its own `SessionLocal` and reuses
  a service from M4–M7 (pure orchestration; no business logic in the graph).
  Realizes the milestone's Fetch→Normalize→Embed→Deduplicate→Save where
  Normalize+Save = the ingest step, run before Embed/Dedup since those operate
  on persisted rows. `run_daily_workflow(query, limit)` invokes it and returns
  per-step count summary. langgraph pinned at 1.2.2. Validated end-to-end:
  fetched 30 → saved 15 → embedded 15 → 13 stories created + 2 sources merged.
- **Weekly clustering:** `app/services/clustering.py`. Embedding-based
  zero-shot categorization into fixed `WEEKLY_CATEGORIES` (OpenAI, Anthropic,
  Funding, Research, Startups). Each category has a text anchor
  (`CATEGORY_ANCHORS`) embedded once via the active provider; each story's
  representative embedding (its primary source article) is assigned to the
  nearest anchor by cosine (= dot product on normalized vectors); written to
  `stories.category`. `cluster_weekly_stories(db)` covers stories with
  last_seen_at within `weekly_window_days` (7); accepts an explicit `stories`
  list for test isolation. Chosen over per-story LLM calls (free, deterministic,
  reuses embeddings). Validated: 23 real stories → all 5 categories
  (OpenAI 7 / Anthropic 1 / Funding 1 / Research 2 / Startups 12).
- **LLM provider abstraction:** `app/services/llm/` mirrors the embeddings
  design — `LLMProvider.generate(prompt, system)`, `GeminiLLMProvider`
  (google-genai `generate_content`) and lazy `OpenAILLMProvider`,
  `get_llm_provider()` selects by `llm_provider`.
- **Weekly report:** `app/services/report.py` + prompt in
  `app/prompts/weekly_report.py`. `gather_weekly_context()` collects weekly
  stories grouped by clustering category (with source outlets);
  `generate_weekly_report()` builds the prompt (fixed sections: Major
  Headlines, Research, Funding, New Models, Outlook), calls the LLM, and
  persists a `Report` row (title, Markdown content, week window, story_count).
  Accepts an injectable provider for tests. Validated: real report (id=2,
  23 stories, all 5 sections) generated via Gemini.
- **Gemini chat model = `gemini-2.5-flash`.** `gemini-2.0-flash` returned
  free-tier quota 0 for generate_content on this key (embeddings unaffected);
  2.5-flash has free quota. Switched the default.
- **Scheduling (Celery + Redis):** `app/workers/celery_app.py` (broker+backend
  = Redis) and `app/workers/tasks.py`. Tasks: `tasks.daily_ingestion`
  (runs the LangGraph daily workflow) and `tasks.weekly_report` (cluster →
  generate+persist report). Beat schedule (UTC, configurable via settings):
  daily ingestion at 06:00, weekly report Mon 07:00. Compose adds `worker`
  (`celery … worker`) and `beat` (`celery … beat`) services reusing the api
  image. celery pinned at 5.6.3. Validated: task sent through the broker was
  received + succeeded on the worker; beat runs with the schedule loaded.
- **API layer:** routers in `app/api/` wired in `main.py`. `GET /health` +
  `/health/ready` (M1); `GET /reports` (paginated summaries), `GET
  /reports/latest` (full Markdown; 404 if none — defined before `/{id}` so
  "latest" isn't parsed as an id), `GET /reports/{id}`; `GET /stories`
  (paginated, optional `category` filter, each with source articles via
  `selectinload`, primary source first). Response schemas in
  `app/api/schemas.py` (`from_attributes` for reports; stories built
  manually for nested sources + source_count). Validated via TestClient
  (isolated inserts) and live curl against all endpoints.

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
- **reports** (migration `4226f6cde25c`) — generated weekly reports: `title`,
  `content` (Markdown), `week_start`/`week_end`, `story_count`, `created_at`
  (indexed). NOTE: the migration was hand-corrected to NOT drop the HNSW index
  (autogenerate proposed dropping it since it isn't declared on the model).
- **pgvector (migration `b7f9ed6623f0`):** `CREATE EXTENSION vector` (v0.8.2),
  `articles.embedding vector(1536)` (nullable), and an HNSW index
  `ix_articles_embedding_hnsw` using `vector_cosine_ops` (m=16,
  ef_construction=64) for cosine ANN search via the `<=>` operator.
  Dimension 1536 matches `text-embedding-3-small`; sourced from
  `Settings.embedding_dim` via the `EMBEDDING_DIM` constant in the model.
  Verified: insert/retrieve of 1536-dim vectors and a cosine-distance
  nearest-neighbour ordering all work.

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
| `EMBEDDING_PROVIDER` | gemini | Active embedding provider (gemini/openai) |
| `LLM_PROVIDER` | gemini | Active LLM provider (gemini/openai) |
| `EMBEDDING_DIM` | 1536 | Vector dimension (structural; shared) |
| `EMBEDDING_BATCH_SIZE` | 100 | Texts per embed API call / DB commit |
| `EMBEDDING_INPUT_MAX_CHARS` | 8000 | Max chars of article text per embed |
| `DEDUP_DISTANCE_THRESHOLD` | 0.15 | Max cosine distance to merge articles |
| `WEEKLY_WINDOW_DAYS` | 7 | Window for weekly clustering / report |
| `DAILY_INGESTION_HOUR` / `_MINUTE` | 6 / 0 | Beat: daily ingestion time (UTC) |
| `WEEKLY_REPORT_DAY_OF_WEEK` | mon | Beat: weekly report day |
| `WEEKLY_REPORT_HOUR` / `_MINUTE` | 7 / 0 | Beat: weekly report time (UTC) |
| `SCHEDULED_FETCH_LIMIT` | 50 | Per-provider cap for the scheduled daily job |
| `GEMINI_API_KEY` | _(empty)_ | Gemini free-tier key (active) |
| `GEMINI_EMBEDDING_MODEL` | gemini-embedding-001 | Gemini embedding model |
| `GEMINI_CHAT_MODEL` | gemini-2.5-flash | Gemini chat model (2.0-flash had 0 free quota) |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI key (for later switch) |
| `OPENAI_EMBEDDING_MODEL` | text-embedding-3-small | OpenAI embedding model |
| `OPENAI_CHAT_MODEL` | gpt-4o-mini | OpenAI chat model |
| `NEWS_QUERY` | artificial intelligence | Default search query |
| `FETCH_MAX_PER_PROVIDER` | 50 | Max articles per provider per run |
| `RSS_FEEDS` | _(3 AI feeds)_ | JSON list override for RSS feeds |
| `NEWSAPI_API_KEY` | _(empty)_ | Enables NewsAPI when set |
| `GNEWS_API_KEY` | _(empty)_ | Enables GNews when set |
| `HTTP_TIMEOUT_SECONDS` | 15 | HTTP client timeout |
