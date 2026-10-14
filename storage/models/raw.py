"""Raw ingested entities schema: channels, posts, authors, and ingestion run snapshots."""

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from storage.database import Base


class MonitoredChannel(Base):
    """Monitored Telegram public channels configuration."""

    __tablename__ = "monitored_channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    topic_tags: Mapped[list[str] | None] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_polled_message_id: Mapped[int | None] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )


class IngestionRun(Base):
    """Component A ingestion batch execution log."""

    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    platform: Mapped[str] = mapped_column(String(32), default="telegram", nullable=False)
    channel_ids: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    posts_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    posts: Mapped[list["RawPost"]] = relationship("RawPost", back_populates="ingestion_run")
    authors: Mapped[list["RawAuthor"]] = relationship("RawAuthor", back_populates="ingestion_run")


class RawPost(Base):
    """Component A: Raw ingested message entity. Immutable after creation."""

    __tablename__ = "raw_posts"
    __table_args__ = (
        UniqueConstraint("platform", "platform_post_id", name="uq_raw_posts_platform_post_id"),
        Index("idx_raw_posts_pending", "id", postgresql_where=text("processing_status = 'pending'")),
        Index("idx_raw_posts_posted_at", "posted_at"),
        Index("idx_raw_posts_channel_id", "channel_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), default="telegram", nullable=False)
    platform_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    media_urls: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, nullable=True)
    reply_to_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    forward_from_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    view_count: Mapped[int | None] = mapped_column(Integer, default=0)
    reaction_counts: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id"), nullable=True
    )
    processing_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    ingestion_run: Mapped[IngestionRun | None] = relationship("IngestionRun", back_populates="posts")
    sentiment_result: Mapped["SentimentResultB | None"] = relationship(
        "SentimentResultB", back_populates="raw_post", uselist=False
    )


class RawAuthor(Base):
    """Component A: Public author profile snapshots from linked discussion groups."""

    __tablename__ = "raw_authors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), default="telegram", nullable=False)
    platform_author_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bio_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    account_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id"), nullable=True
    )

    ingestion_run: Mapped[IngestionRun | None] = relationship("IngestionRun", back_populates="authors")
