"""Tests for the Milestone 7 deduplication engine.

Embeddings are assigned by hand so cosine distances are deterministic and the
test never touches the network.
"""

from sqlalchemy import select

from app.core.config import get_settings
from app.db.base import SessionLocal
from app.models import Article, Story, StorySource
from app.services.dedup import deduplicate_articles
from app.services.embeddings.base import l2_normalize

_TEST_SOURCE_PREFIX = "dedup-test"
_DIM = get_settings().embedding_dim


def _vec(*head: float) -> list[float]:
    v = [0.0] * _DIM
    for i, x in enumerate(head):
        v[i] = float(x)
    return l2_normalize(v)


def _cleanup(db):
    arts = db.query(Article).filter(Article.source.like(f"{_TEST_SOURCE_PREFIX}%")).all()
    ids = [a.id for a in arts]
    if ids:
        story_ids = set(
            db.scalars(
                select(StorySource.story_id).where(
                    StorySource.article_id.in_(ids)
                )
            ).all()
        )
        if story_ids:
            db.query(Story).filter(Story.id.in_(story_ids)).delete(
                synchronize_session=False
            )
        db.query(Article).filter(Article.id.in_(ids)).delete(
            synchronize_session=False
        )
        db.commit()


def test_dedup_merges_duplicates_and_separates_distinct():
    db = SessionLocal()
    try:
        _cleanup(db)

        # Two near-identical articles from different sources + one distinct.
        a1 = Article(
            url="https://dedup-test/1", title="OpenAI launches model",
            source=f"{_TEST_SOURCE_PREFIX}-srcA", embedding=_vec(1.0, 0.0),
        )
        a2 = Article(
            url="https://dedup-test/2", title="OpenAI unveils new model",
            source=f"{_TEST_SOURCE_PREFIX}-srcB", embedding=_vec(1.0, 0.02),
        )
        a3 = Article(
            url="https://dedup-test/3", title="Quarterly earnings report",
            source=f"{_TEST_SOURCE_PREFIX}-srcC", embedding=_vec(0.0, 1.0),
        )
        db.add_all([a1, a2, a3])
        db.commit()

        # Restrict processing to these articles for test isolation; matching
        # still searches against all assigned articles globally.
        result = deduplicate_articles(db, articles=[a1, a2, a3])
        assert result.processed == 3
        assert result.stories_created == 2  # duplicate pair + distinct one
        assert result.sources_attached == 1  # a2 merged into a1's story

        # The duplicate pair share one story with two sources.
        def story_of(article):
            return db.scalar(
                select(StorySource.story_id).where(
                    StorySource.article_id == article.id
                )
            )

        s1, s2, s3 = story_of(a1), story_of(a2), story_of(a3)
        assert s1 == s2 != s3

        source_count = (
            db.query(StorySource).filter(StorySource.story_id == s1).count()
        )
        assert source_count == 2

        # Exactly one primary source per story.
        primaries = (
            db.query(StorySource)
            .filter(StorySource.story_id == s1, StorySource.is_primary.is_(True))
            .count()
        )
        assert primaries == 1

        # Idempotent: the processed articles are no longer "unassigned", so a
        # subsequent run would not pick them up again.
        from app.services.dedup import _unassigned_articles

        unassigned_ids = {a.id for a in _unassigned_articles(db, limit=None)}
        assert unassigned_ids.isdisjoint({a1.id, a2.id, a3.id})
    finally:
        _cleanup(db)
        db.close()
