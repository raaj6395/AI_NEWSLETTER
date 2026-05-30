"""Story model — a canonical story aggregated from one or more articles."""

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cluster/category label is populated in Milestone 9 (weekly clustering).
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Source articles attached to this story (via story_sources).
    sources: Mapped[list["StorySource"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_stories_category", "category"),
        Index("ix_stories_last_seen_at", "last_seen_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Story id={self.id} title={self.title!r}>"


from app.models.story_source import StorySource  # noqa: E402  (resolve relationship)
