"""Tests for the Milestone 5 ingestion pipeline.

`normalize` is tested in isolation; the save path runs against the live
Postgres provided by docker compose and cleans up after itself.
"""

import json
from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.models import Article
from app.services.ingestion import normalize, save_articles
from app.services.news.schemas import FetchedArticle

_TEST_SOURCE = "ingest-test-source"


def _make(url: str, title: str = "T") -> FetchedArticle:
    return FetchedArticle(
        url=url, title=title, source=_TEST_SOURCE, provider="rss"
    )


def test_normalize_truncates_and_jsonifies():
    fetched = FetchedArticle(
        url="https://x/1",
        title="Title",
        source="S" * 400,  # longer than the 255 column limit
        provider="rss",
        author="A" * 400,
        raw={"when": datetime(2026, 1, 1, tzinfo=timezone.utc), "n": 1},
    )
    row = normalize(fetched)
    assert len(row["source"]) == 255
    assert len(row["author"]) == 255
    # raw must be fully JSON-serializable for JSONB; datetime -> str.
    assert isinstance(row["raw"]["when"], str)
    assert row["raw"]["n"] == 1
    assert json.dumps(row["raw"])  # does not raise
    # Embeddings are populated later (Milestone 6), not during normalize.
    assert "embedding" not in row


def test_save_articles_inserts_and_dedups():
    db = SessionLocal()
    try:
        db.query(Article).filter(Article.source == _TEST_SOURCE).delete()
        db.commit()

        batch = [
            _make("https://ingest-test/1"),
            _make("https://ingest-test/2"),
            _make("https://ingest-test/1"),  # within-batch duplicate
        ]
        result = save_articles(db, batch)
        assert result.fetched == 3
        assert result.unique == 2
        assert result.saved == 2
        assert result.duplicates == 1

        # Re-ingesting the same URLs saves nothing (already in DB).
        again = save_articles(db, [_make("https://ingest-test/1")])
        assert again.saved == 0
        assert again.duplicates == 1

        count = (
            db.query(Article).filter(Article.source == _TEST_SOURCE).count()
        )
        assert count == 2
    finally:
        db.query(Article).filter(Article.source == _TEST_SOURCE).delete()
        db.commit()
        db.close()
