"""Ingestion pipeline: Fetch -> Normalize -> Save.

`ingest_news()` pulls articles from all enabled providers (Milestone 4),
normalizes each `FetchedArticle` onto the `Article` ORM shape, and persists
new rows — skipping URLs that already exist. Embeddings are intentionally left
NULL here; they are populated by the embedding pipeline in Milestone 6.
"""

import json
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Article
from app.services.news import fetch_news
from app.services.news.schemas import FetchedArticle

logger = logging.getLogger(__name__)

# Column limits for VARCHAR fields on the Article model.
_SOURCE_MAX = 255
_AUTHOR_MAX = 255


@dataclass
class IngestionResult:
    fetched: int  # total articles returned by providers
    unique: int  # distinct URLs in this batch
    saved: int  # new rows inserted
    duplicates: int  # fetched - saved (within-batch + already-in-db)

    def as_dict(self) -> dict:
        return {
            "fetched": self.fetched,
            "unique": self.unique,
            "saved": self.saved,
            "duplicates": self.duplicates,
        }


def _truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


def _json_safe(value: dict) -> dict:
    """Coerce a provider payload into JSON-serializable form for JSONB.

    Provider payloads (e.g. feedparser entries) can contain time.struct_time
    and datetime objects; `default=str` renders those losslessly enough for
    traceability without breaking serialization.
    """
    if not value:
        return {}
    return json.loads(json.dumps(value, default=str))


def normalize(fetched: FetchedArticle) -> dict:
    """Map a provider's FetchedArticle onto Article column values."""
    return {
        "url": fetched.url,
        "title": fetched.title,
        "source": _truncate(fetched.source, _SOURCE_MAX),
        "author": _truncate(fetched.author, _AUTHOR_MAX),
        "description": fetched.description,
        "content": fetched.content,
        "url_to_image": fetched.url_to_image,
        "published_at": fetched.published_at,
        "raw": _json_safe(fetched.raw),
    }


def save_articles(db: Session, fetched: list[FetchedArticle]) -> IngestionResult:
    """Persist new articles, skipping URLs already in the batch or the DB."""
    # De-duplicate within the batch, keeping the first occurrence of each URL.
    by_url: dict[str, FetchedArticle] = {}
    for item in fetched:
        by_url.setdefault(item.url, item)

    if not by_url:
        return IngestionResult(fetched=len(fetched), unique=0, saved=0, duplicates=0)

    existing = set(
        db.scalars(select(Article.url).where(Article.url.in_(list(by_url)))).all()
    )

    new_rows = [
        Article(**normalize(item))
        for url, item in by_url.items()
        if url not in existing
    ]
    db.add_all(new_rows)
    db.commit()

    saved = len(new_rows)
    result = IngestionResult(
        fetched=len(fetched),
        unique=len(by_url),
        saved=saved,
        duplicates=len(fetched) - saved,
    )
    logger.info("Ingestion result: %s", result.as_dict())
    return result


def ingest_news(
    db: Session,
    query: str | None = None,
    limit_per_provider: int | None = None,
    settings: Settings | None = None,
) -> IngestionResult:
    """Run the full pipeline: fetch from providers, normalize, and save."""
    fetched = fetch_news(
        query=query, limit_per_provider=limit_per_provider, settings=settings
    )
    return save_articles(db, fetched)
