"""Celery tasks for scheduled automation (Milestone 11)."""

import logging

from app.db.base import SessionLocal
from app.graphs import run_daily_workflow
from app.services.clustering import cluster_weekly_stories
from app.services.report import generate_weekly_report
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.daily_ingestion")
def daily_ingestion(query: str | None = None, limit_per_provider: int | None = None) -> dict:
    """Run the daily LangGraph workflow: fetch -> ingest -> embed -> dedup."""
    summary = run_daily_workflow(query=query, limit_per_provider=limit_per_provider)
    logger.info("daily_ingestion task complete: %s", summary)
    return summary


@celery_app.task(name="tasks.weekly_report")
def weekly_report() -> dict:
    """Cluster the week's stories, then generate and persist the report."""
    db = SessionLocal()
    try:
        cluster = cluster_weekly_stories(db)
        report = generate_weekly_report(db)
        result = {
            "clustered": cluster.as_dict(),
            "report_id": report.id,
            "story_count": report.story_count,
        }
    finally:
        db.close()
    logger.info("weekly_report task complete: %s", result)
    return result
