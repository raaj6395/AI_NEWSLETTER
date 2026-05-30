"""Story endpoints: list canonical stories with their source articles."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import StoryOut, StorySourceOut
from app.db.base import get_db
from app.models import Story, StorySource

router = APIRouter(prefix="/stories", tags=["stories"])


def _serialize(story: Story) -> StoryOut:
    sources = [
        StorySourceOut(
            source=link.article.source,
            url=link.article.url,
            title=link.article.title,
            is_primary=link.is_primary,
        )
        for link in story.sources
        if link.article is not None
    ]
    # Primary source first, then the rest.
    sources.sort(key=lambda s: not s.is_primary)
    return StoryOut(
        id=story.id,
        title=story.title,
        summary=story.summary,
        category=story.category,
        first_seen_at=story.first_seen_at,
        last_seen_at=story.last_seen_at,
        source_count=len(sources),
        sources=sources,
    )


@router.get("", response_model=list[StoryOut])
def list_stories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Story)
        .options(selectinload(Story.sources).selectinload(StorySource.article))
        .order_by(Story.last_seen_at.desc().nullslast(), Story.id.desc())
    )
    if category:
        stmt = stmt.where(Story.category == category)
    stmt = stmt.limit(limit).offset(offset)

    return [_serialize(s) for s in db.scalars(stmt).all()]
