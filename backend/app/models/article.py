"""Article model — a single news item as fetched from a provider."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Canonical identity / dedup key for exact duplicates.
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_to_image: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Original provider payload, kept for traceability / reprocessing.
    raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # NOTE: an `embedding` vector column is added in Milestone 3 (pgvector).

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Links to the stories this article is a source of (via story_sources).
    story_links: Mapped[list["StorySource"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_articles_source", "source"),
        Index("ix_articles_published_at", "published_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Article id={self.id} source={self.source!r} title={self.title!r}>"


from app.models.story_source import StorySource  # noqa: E402  (resolve relationship)
