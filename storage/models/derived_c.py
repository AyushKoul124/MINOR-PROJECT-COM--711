"""Component C: Demographic cluster distributions (aggregate only, k-anonymity guarded)."""

from datetime import datetime
from typing import Any
from sqlalchemy import (
    BigInteger,
    Boolean,
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


class DemographicAggregateC(Base):
    """Component C: Macro audience aggregates. Enforces k-anonymity (k >= 50) suppression."""

    __tablename__ = "demographic_aggregates_c"
    __table_args__ = (
        Index("idx_demographics_c_window", "window_start", "window_end"),
        Index("idx_demographics_c_threshold", "below_threshold"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cluster_label: Mapped[str] = mapped_column(String(255), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    account_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # DPDP 2023 k-Anonymity Guard: TRUE if account_count < MIN_CLUSTER_SIZE (50)
    below_threshold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Inferred heuristic distribution dictionaries
    age_bracket_dist: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    geography_dist: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    language_dist: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    interest_dist: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    inference_confidence: Mapped[float | None] = mapped_column(Float, default=0.0)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
