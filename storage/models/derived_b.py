"""Component B: Sentiment, Emotion & Stance derived intelligence models."""

from datetime import datetime
from typing import Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from storage.database import Base


class SentimentResultB(Base):
    """Component B: Derived sentiment, Ekman 6 emotions + neutral, zero-shot stance, and sarcasm flag."""

    __tablename__ = "sentiment_results_b"
    __table_args__ = (
        Index("idx_sentiment_b_post_id", "raw_post_id"),
        Index("idx_sentiment_b_analyzed_at", "analyzed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    raw_post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("raw_posts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    content_language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    dominant_emotion: Mapped[str | None] = mapped_column(String(64), nullable=True)
    emotion_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Core Ekman 6 emotions (0.0 to 1.0) + neutral
    emotion_joy: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_anger: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_sadness: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_disgust: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_surprise: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_neutral: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_fear: Mapped[float | None] = mapped_column(Float, default=0.0)

    # Extended fine-grained emotions (GoEmotions)
    emotion_anxiety: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_excitement: Mapped[float | None] = mapped_column(Float, default=0.0)
    emotion_extended: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Stance: 'supportive', 'against', 'neutral', 'unclear' (0.60 threshold)
    stance: Mapped[str | None] = mapped_column(String(32), default="neutral")
    stance_confidence: Mapped[float | None] = mapped_column(Float, default=0.0)

    # Sarcasm heuristic: advisory uncertainty penalty (never inverts valence)
    sarcasm_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    valence: Mapped[str | None] = mapped_column(String(16), default="neutral")

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    raw_post: Mapped["RawPost"] = relationship("RawPost", back_populates="sentiment_result")
