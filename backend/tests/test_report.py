"""Tests for the Milestone 10 weekly report generation (offline / no network)."""

from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.models import Article, Report, Story, StorySource
from app.prompts.weekly_report import REPORT_SECTIONS, build_user_prompt
from app.services.llm.base import LLMProvider
from app.services.report import generate_weekly_report

_TEST_TITLE = "report-test-story"


class FakeLLM(LLMProvider):
    """Records the prompt and returns a fixed report with all sections."""

    name = "fake"

    def __init__(self):
        super().__init__(model="fake")
        self.last_prompt = None
        self.last_system = None

    def generate(self, prompt: str, system: str | None = None) -> str:
        self.last_prompt = prompt
        self.last_system = system
        body = "\n".join(f"## {s}\nContent for {s}." for s in REPORT_SECTIONS)
        return f"# AI Weekly Report\n\n{body}"


def test_build_user_prompt_includes_sections_and_stories():
    grouped = {"OpenAI": [{"title": "GPT-X released", "summary": "big", "sources": ["TC"]}]}
    prompt = build_user_prompt(grouped, "2026-05-23", "2026-05-30")
    for section in REPORT_SECTIONS:
        assert f"## {section}" in prompt
    assert "GPT-X released" in prompt
    assert "TC" in prompt


def _cleanup(db):
    stories = db.query(Story).filter(Story.title == _TEST_TITLE).all()
    ids = [s.id for s in stories]
    if ids:
        db.query(StorySource).filter(StorySource.story_id.in_(ids)).delete(
            synchronize_session=False
        )
        db.query(Story).filter(Story.id.in_(ids)).delete(synchronize_session=False)
    db.query(Article).filter(Article.title == _TEST_TITLE).delete()
    db.query(Report).filter(Report.title.like("AI Weekly Report —%")).delete()
    db.commit()


def test_generate_weekly_report_persists_markdown():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        _cleanup(db)

        story = Story(
            title=_TEST_TITLE, summary="A summary", category="OpenAI", last_seen_at=now
        )
        db.add(story)
        db.flush()
        art = Article(
            url="https://report-test/1", title=_TEST_TITLE, source="TestWire"
        )
        db.add(art)
        db.flush()
        db.add(StorySource(story_id=story.id, article_id=art.id, is_primary=True))
        db.commit()

        fake = FakeLLM()
        report = generate_weekly_report(db, provider=fake)

        # Persisted with a real id and the generated Markdown.
        assert report.id is not None
        assert report.story_count >= 1
        for section in REPORT_SECTIONS:
            assert f"## {section}" in report.content

        # The story made it into the prompt context.
        assert _TEST_TITLE in fake.last_prompt
        assert "TestWire" in fake.last_prompt

        # Readable back from the DB.
        again = db.get(Report, report.id)
        assert again is not None and again.content == report.content
    finally:
        _cleanup(db)
        db.close()
