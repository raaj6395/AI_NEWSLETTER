"""Embedding pipeline: generate and store vectors for articles.

Finds articles whose `embedding` is NULL, builds an input text from each, calls
the active embedding provider in batches, and writes the vectors back. Designed
to run after ingestion (Milestone 5) and feed deduplication (Milestone 7).
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import Article
from app.services.embeddings import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    pending: int  # articles needing an embedding at the start
    embedded: int  # vectors successfully stored
    failed: int  # articles in batches that errored

    def as_dict(self) -> dict:
        return {"pending": self.pending, "embedded": self.embedded, "failed": self.failed}


def build_embedding_input(article: Article, max_chars: int) -> str:
    """Compose the text representing an article for embedding."""
    parts = [article.title or ""]
    body = article.description or article.content
    if body:
        parts.append(body)
    text = "\n\n".join(p for p in parts if p).strip()
    return text[:max_chars]


def embed_pending_articles(
    db: Session,
    limit: int | None = None,
    provider: EmbeddingProvider | None = None,
    settings: Settings | None = None,
) -> EmbeddingResult:
    """Embed all articles with a NULL embedding (optionally capped by `limit`)."""
    settings = settings or get_settings()
    provider = provider or get_embedding_provider(settings)

    stmt = (
        select(Article)
        .where(Article.embedding.is_(None))
        .order_by(Article.id)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    pending = list(db.scalars(stmt).all())

    if not pending:
        logger.info("No articles pending embedding")
        return EmbeddingResult(pending=0, embedded=0, failed=0)

    return embed_articles(db, pending, provider=provider, settings=settings)


def embed_articles(
    db: Session,
    articles: list[Article],
    provider: EmbeddingProvider | None = None,
    settings: Settings | None = None,
) -> EmbeddingResult:
    """Embed an explicit list of articles in batches, writing vectors back.

    Failures are isolated per batch (those articles keep a NULL embedding and
    are retried on the next run).
    """
    settings = settings or get_settings()
    provider = provider or get_embedding_provider(settings)

    if not articles:
        return EmbeddingResult(pending=0, embedded=0, failed=0)

    batch_size = settings.embedding_batch_size
    max_chars = settings.embedding_input_max_chars
    embedded = 0
    failed = 0

    for start in range(0, len(articles), batch_size):
        chunk = articles[start : start + batch_size]
        texts = [build_embedding_input(a, max_chars) for a in chunk]
        try:
            vectors = provider.embed_texts(texts)
        except Exception:  # noqa: BLE001 - skip this batch, retry on next run
            logger.exception("Embedding batch failed (%d articles)", len(chunk))
            failed += len(chunk)
            continue

        for article, vector in zip(chunk, vectors):
            article.embedding = vector
        db.commit()
        embedded += len(chunk)
        logger.info("Embedded %d/%d articles", embedded, len(articles))

    return EmbeddingResult(pending=len(articles), embedded=embedded, failed=failed)
