"""Article model — a single news item as fetched from a provider."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.db.base import Base

# Vector dimension is structural (changing it requires a migration), so it is
# read once from settings — the default matches OpenAI text-embedding-3-small.
EMBEDDING_DIM = get_settings().embedding_dim


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

    # Semantic embedding of the article (pgvector). Populated by the embedding
    # pipeline in Milestone 6; used for dedup/similarity from Milestone 7.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
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
