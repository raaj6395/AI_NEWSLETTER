"""Pydantic response schemas for the API layer (Milestone 12)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    week_start: datetime | None
    week_end: datetime | None
    story_count: int
    created_at: datetime


class ReportDetail(ReportSummary):
    content: str  # full Markdown body


class StorySourceOut(BaseModel):
    source: str
    url: str
    title: str
    is_primary: bool


class StoryOut(BaseModel):
    id: int
    title: str
    summary: str | None
    category: str | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    source_count: int
    sources: list[StorySourceOut]
