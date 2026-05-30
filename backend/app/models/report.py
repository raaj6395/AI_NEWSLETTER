"""Report model — a generated weekly AI report (Markdown)."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Rendered Markdown body of the report.
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Week window the report covers.
    week_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    week_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    story_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_reports_created_at", "created_at"),)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Report id={self.id} title={self.title!r} stories={self.story_count}>"
