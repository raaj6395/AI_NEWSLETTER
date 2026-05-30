"""Tests for the Milestone 12 API layer.

Inserts a known report + story, exercises the endpoints via TestClient, then
cleans up so assertions are deterministic regardless of other DB contents.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.models import Article, Report, Story, StorySource

client = TestClient(app)

_TAG = "api-test"


def _cleanup(db):
    stories = db.query(Story).filter(Story.title == _TAG).all()
    ids = [s.id for s in stories]
    if ids:
        db.query(StorySource).filter(StorySource.story_id.in_(ids)).delete(
            synchronize_session=False
        )
        db.query(Story).filter(Story.id.in_(ids)).delete(synchronize_session=False)
    db.query(Article).filter(Article.title == _TAG).delete()
    db.query(Report).filter(Report.title == _TAG).delete()
    db.commit()


def test_reports_endpoints():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        _cleanup(db)
        report = Report(
            title=_TAG, content="## Major Headlines\nHi", story_count=1,
            week_start=now, week_end=now,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        report_id = report.id

        # List
        resp = client.get("/reports")
        assert resp.status_code == 200
        assert any(r["id"] == report_id for r in resp.json())

        # Latest (our report has the newest created_at)
        resp = client.get("/reports/latest")
        assert resp.status_code == 200
        assert resp.json()["id"] == report_id
        assert "Major Headlines" in resp.json()["content"]

        # By id
        resp = client.get(f"/reports/{report_id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == _TAG

        # Missing id -> 404
        assert client.get("/reports/99999999").status_code == 404
    finally:
        _cleanup(db)
        db.close()


def test_stories_endpoint():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        _cleanup(db)
        story = Story(title=_TAG, summary="s", category="OpenAI", last_seen_at=now)
        db.add(story)
        db.flush()
        art = Article(url="https://api-test/1", title=_TAG, source="APIWire")
        db.add(art)
        db.flush()
        db.add(StorySource(story_id=story.id, article_id=art.id, is_primary=True))
        db.commit()
        story_id = story.id

        resp = client.get("/stories", params={"category": "OpenAI", "limit": 100})
        assert resp.status_code == 200
        mine = [s for s in resp.json() if s["id"] == story_id]
        assert len(mine) == 1
        s = mine[0]
        assert s["category"] == "OpenAI"
        assert s["source_count"] == 1
        assert s["sources"][0]["source"] == "APIWire"
        assert s["sources"][0]["is_primary"] is True
    finally:
        _cleanup(db)
        db.close()
