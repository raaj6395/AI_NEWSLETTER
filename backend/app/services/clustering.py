"""Weekly clustering: assign each recent story to a topical category.

Uses embedding-based zero-shot categorization. A short description of each
category is embedded once (via the active embedding provider); every story in
the weekly window is then assigned to the category whose anchor is most similar
to the story's representative (primary source article) embedding. The result is
written to `stories.category`.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import Article, Story, StorySource
from app.services.embeddings import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)

# Ordered category labels and the text each one is matched against.
WEEKLY_CATEGORIES = ["OpenAI", "Anthropic", "Funding", "Research", "Startups"]

CATEGORY_ANCHORS = {
    "OpenAI": "News about OpenAI, ChatGPT, GPT models, Sam Altman, and OpenAI products.",
    "Anthropic": "News about Anthropic and its Claude family of AI models.",
    "Funding": "Startup funding rounds, venture capital, investments, valuations, and money raised.",
    "Research": "AI research papers, scientific studies, model architectures, benchmarks, and breakthroughs.",
    "Startups": "AI startups, new companies, product launches, and emerging technology ventures.",
}


@dataclass
class ClusterResult:
    total: int  # stories in the weekly window
    clustered: int  # stories assigned a category
    skipped: int  # stories with no usable embedding
    by_category: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "clustered": self.clustered,
            "skipped": self.skipped,
            "by_category": self.by_category,
        }


def _representative_embedding(db: Session, story_id: int):
    """The primary source article's embedding represents the story."""
    return db.scalar(
        select(Article.embedding)
        .join(StorySource, StorySource.article_id == Article.id)
        .where(
            StorySource.story_id == story_id,
            StorySource.is_primary.is_(True),
            Article.embedding.is_not(None),
        )
    )


def _cosine(a, b) -> float:
    # Provider vectors are L2-normalized, so cosine similarity == dot product.
    return sum(float(x) * float(y) for x, y in zip(a, b))


def weekly_stories(db: Session, since: datetime) -> list[Story]:
    """Stories whose last_seen_at falls within the weekly window."""
    return list(db.scalars(select(Story).where(Story.last_seen_at >= since)).all())


def cluster_weekly_stories(
    db: Session,
    since: datetime | None = None,
    stories: list[Story] | None = None,
    provider: EmbeddingProvider | None = None,
    settings: Settings | None = None,
) -> ClusterResult:
    """Categorize stories in the weekly window (or an explicit `stories` list)."""
    settings = settings or get_settings()
    provider = provider or get_embedding_provider(settings)

    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=settings.weekly_window_days)

    anchor_vectors = provider.embed_texts(
        [CATEGORY_ANCHORS[c] for c in WEEKLY_CATEGORIES]
    )

    if stories is None:
        stories = weekly_stories(db, since)

    by_category = {c: 0 for c in WEEKLY_CATEGORIES}
    clustered = 0
    skipped = 0

    for story in stories:
        emb = _representative_embedding(db, story.id)
        if emb is None:
            skipped += 1
            continue
        sims = [_cosine(emb, anchor) for anchor in anchor_vectors]
        best = max(range(len(sims)), key=lambda i: sims[i])
        category = WEEKLY_CATEGORIES[best]
        story.category = category
        by_category[category] += 1
        clustered += 1

    db.commit()
    result = ClusterResult(
        total=len(stories),
        clustered=clustered,
        skipped=skipped,
        by_category=by_category,
    )
    logger.info("Weekly clustering result: %s", result.as_dict())
    return result
