"""StorySource model — association between a Story and its source Articles.

Each article belongs to at most one story (enforced by a unique constraint on
`article_id`), while a story can aggregate many articles. The dedup engine
(Milestone 7) creates one Story and many StorySource rows from duplicate
articles across providers.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StorySource(Base):
    __tablename__ = "story_sources"

    id: Mapped[int] = mapped_column(primary_key=True)

    story_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    article_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Marks the representative article chosen for the story.
    is_primary: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    story: Mapped["Story"] = relationship(back_populates="sources")
    article: Mapped["Article"] = relationship(back_populates="story_links")

    __table_args__ = (
        # An article can be a source of only one story.
        UniqueConstraint("article_id", name="uq_story_sources_article_id"),
        # No duplicate (story, article) pairs.
        UniqueConstraint(
            "story_id", "article_id", name="uq_story_sources_story_article"
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<StorySource story_id={self.story_id} "
            f"article_id={self.article_id} primary={self.is_primary}>"
        )


from app.models.article import Article  # noqa: E402  (resolve relationship)
from app.models.story import Story  # noqa: E402  (resolve relationship)
