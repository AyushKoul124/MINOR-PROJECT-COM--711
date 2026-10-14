"""Component D: BERTopic extracted topics, velocity, and acceleration models."""

from datetime import datetime
from typing import Any
from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from storage.database import Base


class TrendTopicD(Base):
    """Component D: Discovered topic clusters ranked by velocity and acceleration on posted_at."""

    __tablename__ = "trend_topics_d"
    __table_args__ = (
        Index("idx_trend_topics_d_window", "window_start", "window_end"),
        Index("idx_trend_topics_d_velocity", "velocity"),
        Index("idx_trend_topics_d_rank", "rank"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic_label: Mapped[str] = mapped_column(String(512), nullable=False)
    topic_keywords: Mapped[list[str] | dict[str, Any]] = mapped_column(JSONB, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Velocity (posts/hr) and acceleration (change in velocity) strictly anchored to posted_at
    velocity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    acceleration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_post_ids: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
