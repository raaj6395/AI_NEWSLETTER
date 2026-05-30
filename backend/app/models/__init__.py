"""ORM models package.

Importing the models here ensures they are registered on the shared
`Base.metadata`, which Alembic relies on for autogeneration.
"""

from app.models.article import Article
from app.models.report import Report
from app.models.story import Story
from app.models.story_source import StorySource

__all__ = ["Article", "Story", "StorySource", "Report"]
