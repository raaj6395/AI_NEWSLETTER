"""Tests for the Milestone 11 Celery scheduling (offline; no broker)."""

import app.workers.tasks as tasks
from app.workers.celery_app import celery_app


def test_tasks_are_registered():
    assert "tasks.daily_ingestion" in celery_app.tasks
    assert "tasks.weekly_report" in celery_app.tasks


def test_beat_schedule_has_both_jobs():
    schedule = celery_app.conf.beat_schedule
    assert schedule["daily-ingestion"]["task"] == "tasks.daily_ingestion"
    assert schedule["weekly-report"]["task"] == "tasks.weekly_report"


def test_daily_ingestion_task_invokes_workflow(monkeypatch):
    captured = {}

    def fake_workflow(query=None, limit_per_provider=None):
        captured["query"] = query
        captured["limit"] = limit_per_provider
        return {"fetched": 0, "ingest": {}, "embed": {}, "dedup": {}}

    monkeypatch.setattr(tasks, "run_daily_workflow", fake_workflow)

    # Calling the task runs it synchronously in-process.
    result = tasks.daily_ingestion(limit_per_provider=7)
    assert captured["limit"] == 7
    assert result["fetched"] == 0


def test_weekly_report_task_clusters_then_reports(monkeypatch):
    calls = []

    class _R:
        def as_dict(self):
            return {"total": 1, "clustered": 1, "skipped": 0, "by_category": {}}

    class _Report:
        id = 99
        story_count = 1

    monkeypatch.setattr(
        tasks, "cluster_weekly_stories", lambda db: (calls.append("cluster"), _R())[1]
    )
    monkeypatch.setattr(
        tasks, "generate_weekly_report", lambda db: (calls.append("report"), _Report())[1]
    )
    monkeypatch.setattr(tasks, "SessionLocal", lambda: _FakeSession())

    result = tasks.weekly_report()
    assert calls == ["cluster", "report"]  # cluster before report
    assert result["report_id"] == 99


class _FakeSession:
    def close(self):
        pass
