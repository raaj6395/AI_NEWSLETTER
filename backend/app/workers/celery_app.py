"""Celery application and Beat schedule.

Broker and result backend are both Redis (configured from settings). Two
periodic jobs are scheduled: daily ingestion (the LangGraph workflow) and the
weekly clustering + report. Tasks live in `app.workers.tasks`.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ainews",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
)

celery_app.conf.beat_schedule = {
    "daily-ingestion": {
        "task": "tasks.daily_ingestion",
        "schedule": crontab(
            hour=settings.daily_ingestion_hour,
            minute=settings.daily_ingestion_minute,
        ),
        "kwargs": {"limit_per_provider": settings.scheduled_fetch_limit},
    },
    "weekly-report": {
        "task": "tasks.weekly_report",
        "schedule": crontab(
            day_of_week=settings.weekly_report_day_of_week,
            hour=settings.weekly_report_hour,
            minute=settings.weekly_report_minute,
        ),
    },
}
