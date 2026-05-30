"""Tests for the Milestone 9 weekly clustering (offline / no network).

A fake provider returns standard basis vectors as the category anchors, and
each story's primary article embedding is set to one basis vector, so the
nearest-anchor assignment is fully deterministic.
"""

from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.base import SessionLocal
from app.models import Article, Story, StorySource
from app.services.clustering import (
    WEEKLY_CATEGORIES,
    ClusterResult,
    cluster_weekly_stories,
)
from app.services.embeddings.base import EmbeddingProvider

_DIM = get_settings().embedding_dim
_TEST_TITLE = "clustering-test-story"


def _basis(i: int) -> list[float]:
    v = [0.0] * _DIM
    v[i] = 1.0
    return v


class BasisProvider(EmbeddingProvider):
    """Returns the i-th standard basis vector for the i-th input text."""

    name = "basis"

    def __init__(self):
        super().__init__(model="basis", dim=_DIM)

    def embed_texts(self, texts):
        return [_basis(i) for i in range(len(texts))]


def _cleanup(db):
    stories = db.query(Story).filter(Story.title == _TEST_TITLE).all()
    for s in stories:
        db.query(StorySource).filter(StorySource.story_id == s.id).delete()
    ids = [s.id for s in stories]
    db.query(Article).filter(Article.title == _TEST_TITLE).delete()
    if ids:
        db.query(Story).filter(Story.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


def test_cluster_weekly_assigns_each_category():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        _cleanup(db)

        # One story per category; its primary article embedding == basis[i].
        for i in range(len(WEEKLY_CATEGORIES)):
            story = Story(title=_TEST_TITLE, last_seen_at=now)
            db.add(story)
            db.flush()
            art = Article(
                url=f"https://cluster-test/{i}",
                title=_TEST_TITLE,
                source="cluster-test",
                embedding=_basis(i),
            )
            db.add(art)
            db.flush()
            db.add(
                StorySource(story_id=story.id, article_id=art.id, is_primary=True)
            )
        db.commit()

        # Scope to our test stories for isolation (matching is deterministic).
        rows = (
            db.query(Story).filter(Story.title == _TEST_TITLE).order_by(Story.id).all()
        )
        result = cluster_weekly_stories(db, stories=rows, provider=BasisProvider())
        assert isinstance(result, ClusterResult)
        assert result.total == len(WEEKLY_CATEGORIES)
        assert result.clustered == len(WEEKLY_CATEGORIES)
        assert result.skipped == 0
        for cat in WEEKLY_CATEGORIES:
            assert result.by_category[cat] == 1

        # Verify the actual category written to each test story (in id order).
        rows = (
            db.query(Story).filter(Story.title == _TEST_TITLE).order_by(Story.id).all()
        )
        assert [s.category for s in rows] == WEEKLY_CATEGORIES
    finally:
        _cleanup(db)
        db.close()
