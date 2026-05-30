# AI Weekly News Platform - Claude Code Instructions

## Your Role

You are a senior software engineer responsible for building an AI Weekly News Platform.

The platform will:

1. Fetch AI-related news daily from multiple providers.
2. Store articles in PostgreSQL.
3. Generate embeddings and store them using pgvector.
4. Deduplicate similar news.
5. Create canonical stories from multiple articles.
6. Generate weekly AI reports.
7. Expose APIs for accessing reports.
8. Run locally with Docker.
9. Deploy later (target platform to be decided — not committed to Render or Vercel yet).

---

# Critical Development Rules

## Rule 1

Only implement ONE milestone at a time.

Do not start the next milestone until the current milestone passes validation.

---

## Rule 2

After completing a milestone, stop coding and provide:

* Files created
* Files modified
* Commands to run
* Validation steps
* Expected output

Wait for user confirmation before moving forward.

---

## Rule 3

Maintain project state.

Create and continuously update:

project_state.md

This file must contain:

* Current milestone
* Completed milestones
* Pending milestones
* Architecture decisions
* Database schema decisions
* Known issues
* Environment variables

Whenever a milestone is completed, update project_state.md.

---

## Rule 4

Never generate placeholder production code.

Generate working code.

Avoid TODO implementations unless explicitly requested.

---

## Rule 5

Always check existing project files before modifying anything.

Avoid duplicate implementations.

---

# Technology Stack

Backend:

* Python 3.12
* FastAPI

AI Framework:

* LangGraph
* LangChain

Database:

* PostgreSQL
* pgvector

Task Queue:

* Celery

Broker:

* Redis

Containerization:

* Docker
* Docker Compose

Testing:

* Pytest

Deployment:

* To be decided (verify and harden locally first; platform not chosen yet)

LLM Provider:

* OpenAI

Embeddings:

* text-embedding-3-small

---

# Expected Folder Structure

backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── services/
│   ├── workers/
│   ├── graphs/
│   └── prompts/
│
├── tests/
│
├── migrations/
│
├── docker/
│
└── requirements/

---

# Development Milestones

## Milestone 1

Project Bootstrap

### Goal

Create:

* FastAPI app
* Docker setup
* PostgreSQL container
* pgvector
* Redis container
* Environment management

### Validation

User can run:

docker compose up

and see:

* API running
* Postgres running
* Redis running

### Deliverables

* Docker Compose
* FastAPI Health Endpoint
* Environment Loader

Stop after completion.

---

## Milestone 2

Database Layer

### Goal

Create:

Tables:

articles
stories
story_sources

Alembic migrations.

### Validation

User can:

Run migrations.

Verify tables exist.

Stop after completion.

---

## Milestone 3

pgvector Integration

### Goal

Enable pgvector.

Add embedding field.

### Validation

Insert and retrieve vectors.

Similarity query works.

Stop after completion.

---

## Milestone 4

News Source Framework

### Goal

Create provider architecture.

Providers:

* RSS
* NewsAPI
* GNews

Use adapter pattern.

### Validation

User can run:

fetch_news()

and receive articles.

Stop after completion.

---

## Milestone 5

Ingestion Pipeline

### Goal

Pipeline:

Fetch
→ Normalize
→ Save

### Validation

Articles appear in database.

Stop after completion.

---

## Milestone 6

Embedding Pipeline

### Goal

Generate embeddings.

Store vectors.

### Validation

New articles contain embeddings.

Stop after completion.

---

## Milestone 7

Deduplication Engine

### Goal

Use vector similarity.

Merge duplicate articles.

### Validation

Same story from multiple sources creates:

1 Story
Many Sources

Stop after completion.

---

## Milestone 8

LangGraph Daily Workflow

### Goal

Build graph:

Fetch
→ Normalize
→ Embed
→ Deduplicate
→ Save

### Validation

Graph executes successfully.

Stop after completion.

---

## Milestone 9

Weekly Clustering

### Goal

Cluster weekly stories.

Groups:

* OpenAI
* Anthropic
* Startups
* Funding
* Research

### Validation

Weekly clusters generated.

Stop after completion.

---

## Milestone 10

Weekly Report Generation

### Goal

Generate:

AI Weekly Report

Sections:

* Major Headlines
* Research
* Funding
* New Models
* Outlook

### Validation

Markdown report generated.

Stop after completion.

---

## Milestone 11

Scheduling

### Goal

Automate:

Daily ingestion

Weekly report

### Validation

Scheduled jobs execute locally.

Stop after completion.

---

## Milestone 12

API Layer

### Goal

Endpoints:

GET /reports

GET /reports/latest

GET /stories

GET /health

### Validation

All endpoints functional.

Stop after completion.

---

## Milestone 13

Deployment Preparation

### Goal

Deferred. Before any deployment work:

* Verify the full pipeline locally end-to-end.
* Improve / harden the existing milestones.

Once ready, decide on a deployment platform (NOT necessarily Render or Vercel)
and then prepare:

* Platform deployment configuration
* Environment configuration
* Deployment documentation

### Validation

To be defined when the deployment platform is chosen.

Stop after completion.

---

# Definition of Done

A milestone is complete only if:

1. Code compiles.
2. Docker containers start.
3. Validation steps pass.
4. Tests pass.
5. project_state.md updated.

If any requirement fails, milestone is not complete.
