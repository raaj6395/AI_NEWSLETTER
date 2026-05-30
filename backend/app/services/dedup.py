"""Deduplication engine.

Groups near-duplicate articles (the same news event reported by multiple
sources) into a single canonical `Story` with many `StorySource` rows.

Strategy — incremental, greedy nearest-neighbour by cosine distance:
  For each unassigned article (has an embedding, no story yet), find the
  nearest already-assigned article. If it is within
  `dedup_distance_threshold`, attach the article to that article's story;
  otherwise start a new story with this article as the primary source.

Running it again only processes newly-unassigned articles, so it composes with
ongoing ingestion.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import Article, Story, StorySource

logger = logging.getLogger(__name__)


@dataclass
class DedupResult:
    processed: int  # unassigned articles considered
    stories_created: int  # new canonical stories
    sources_attached: int  # articles merged into an existing story

    def as_dict(self) -> dict:
        return {
            "processed": self.processed,
            "stories_created": self.stories_created,
            "sources_attached": self.sources_attached,
        }


def _unassigned_articles(db: Session, limit: int | None) -> list[Article]:
    """Articles that have an embedding but are not yet a source of any story."""
    stmt = (
        select(Article)
        .outerjoin(StorySource, StorySource.article_id == Article.id)
        .where(Article.embedding.is_not(None))
        .where(StorySource.id.is_(None))
        .order_by(Article.published_at.nulls_last(), Article.id)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def find_matching_story(
    db: Session, embedding: list[float], threshold: float
) -> int | None:
    """Return the story id of the nearest assigned article within threshold."""
    row = db.execute(
        select(
            StorySource.story_id,
            Article.embedding.cosine_distance(embedding).label("distance"),
        )
        .join(StorySource, StorySource.article_id == Article.id)
        .where(Article.embedding.is_not(None))
        .order_by("distance")
        .limit(1)
    ).first()

    if row is not None and row.distance <= threshold:
        return row.story_id
    return None


def _extend_story_window(story: Story, article: Article) -> None:
    """Widen a story's first/last seen window to include the article."""
    published = article.published_at
    if published is None:
        return
    if story.first_seen_at is None or published < story.first_seen_at:
        story.first_seen_at = published
    if story.last_seen_at is None or published > story.last_seen_at:
        story.last_seen_at = published


def deduplicate_articles(
    db: Session,
    articles: list[Article] | None = None,
    threshold: float | None = None,
    limit: int | None = None,
    settings: Settings | None = None,
) -> DedupResult:
    """Cluster articles into stories by embedding similarity.

    By default processes every unassigned article (embedding set, no story
    yet). Pass an explicit `articles` list to restrict processing to those.
    Matching always searches against *all* already-assigned articles, so new
    articles correctly merge into pre-existing stories.
    """
    settings = settings or get_settings()
    threshold = threshold if threshold is not None else settings.dedup_distance_threshold

    to_process = articles if articles is not None else _unassigned_articles(db, limit)
    if not to_process:
        logger.info("No articles to deduplicate")
        return DedupResult(processed=0, stories_created=0, sources_attached=0)

    created = 0
    attached = 0

    for article in to_process:
        story_id = find_matching_story(db, article.embedding, threshold)

        if story_id is None:
            story = Story(
                title=article.title,
                summary=article.description,
                first_seen_at=article.published_at,
                last_seen_at=article.published_at,
            )
            db.add(story)
            db.flush()  # assign story.id
            db.add(
                StorySource(
                    story_id=story.id, article_id=article.id, is_primary=True
                )
            )
            created += 1
        else:
            db.add(
                StorySource(
                    story_id=story_id, article_id=article.id, is_primary=False
                )
            )
            story = db.get(Story, story_id)
            _extend_story_window(story, article)
            attached += 1

        # Flush so this assignment is visible to subsequent nearest-neighbour
        # lookups within the same run.
        db.flush()

    db.commit()
    result = DedupResult(
        processed=len(to_process),
        stories_created=created,
        sources_attached=attached,
    )
    logger.info("Dedup result: %s", result.as_dict())
    return result
