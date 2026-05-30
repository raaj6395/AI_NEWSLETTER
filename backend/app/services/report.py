"""Weekly report generation (Milestone 10).

Gathers the week's stories (grouped by their clustering category), asks the
active LLM provider to write a Markdown report with the required sections, and
persists it as a `Report` row.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import Article, Report, Story, StorySource
from app.prompts.weekly_report import SYSTEM_PROMPT, build_user_prompt
from app.services.clustering import WEEKLY_CATEGORIES
from app.services.llm import LLMProvider, get_llm_provider

logger = logging.getLogger(__name__)


@dataclass
class WeeklyContext:
    week_start: datetime
    week_end: datetime
    grouped: dict[str, list[dict]]
    story_count: int


def _story_sources(db: Session, story_id: int) -> list[str]:
    """Distinct outlet names backing a story."""
    rows = db.scalars(
        select(Article.source)
        .join(StorySource, StorySource.article_id == Article.id)
        .where(StorySource.story_id == story_id)
    ).all()
    # Preserve order while de-duplicating.
    seen: dict[str, None] = {}
    for r in rows:
        if r:
            seen.setdefault(r, None)
    return list(seen)


def gather_weekly_context(
    db: Session,
    since: datetime | None = None,
    until: datetime | None = None,
    settings: Settings | None = None,
) -> WeeklyContext:
    """Collect weekly stories grouped by category (uncategorized -> 'Other')."""
    settings = settings or get_settings()
    until = until or datetime.now(timezone.utc)
    since = since or (until - timedelta(days=settings.weekly_window_days))

    stories = list(
        db.scalars(
            select(Story)
            .where(Story.last_seen_at >= since)
            .order_by(Story.last_seen_at.desc())
        ).all()
    )

    grouped: dict[str, list[dict]] = {c: [] for c in WEEKLY_CATEGORIES}
    for story in stories:
        category = story.category if story.category in grouped else "Other"
        grouped.setdefault(category, [])
        grouped[category].append(
            {
                "title": story.title,
                "summary": story.summary,
                "sources": _story_sources(db, story.id),
            }
        )

    return WeeklyContext(
        week_start=since, week_end=until, grouped=grouped, story_count=len(stories)
    )


def generate_weekly_report(
    db: Session,
    since: datetime | None = None,
    until: datetime | None = None,
    provider: LLMProvider | None = None,
    settings: Settings | None = None,
) -> Report:
    """Generate and persist the weekly Markdown report."""
    settings = settings or get_settings()
    provider = provider or get_llm_provider(settings)

    context = gather_weekly_context(db, since=since, until=until, settings=settings)

    week_start = context.week_start.date().isoformat()
    week_end = context.week_end.date().isoformat()
    prompt = build_user_prompt(context.grouped, week_start, week_end)
    content = provider.generate(prompt, system=SYSTEM_PROMPT)

    report = Report(
        title=f"AI Weekly Report — {week_start} to {week_end}",
        content=content,
        week_start=context.week_start,
        week_end=context.week_end,
        story_count=context.story_count,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info(
        "Generated report id=%s (%d stories, %d chars)",
        report.id,
        report.story_count,
        len(content),
    )
    return report
