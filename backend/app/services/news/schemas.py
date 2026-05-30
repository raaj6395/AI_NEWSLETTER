"""Normalized representation of a fetched news article.

This is the common output shape every provider adapter produces, decoupling
the rest of the pipeline from provider-specific payloads. It is distinct from
the persisted `Article` ORM model — the ingestion pipeline (Milestone 5) maps
`FetchedArticle` onto `Article`.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FetchedArticle(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Canonical link to the article — used as the exact-duplicate key.
    url: str
    title: str

    # Outlet / publication name (e.g. "TechCrunch").
    source: str
    # Adapter that produced this item ("rss" | "newsapi" | "gnews").
    provider: str

    author: str | None = None
    description: str | None = None
    content: str | None = None
    url_to_image: str | None = None
    published_at: datetime | None = None

    # Original provider payload, retained for traceability.
    raw: dict = Field(default_factory=dict)
