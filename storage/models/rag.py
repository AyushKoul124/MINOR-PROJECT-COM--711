"""RAG Layer: pgvector embedded agent intelligence summaries and query audit logging."""

import uuid
from datetime import datetime
from typing import Any
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from storage.database import Base


class RAGDocument(Base):
    """Component summaries embedded for semantic vector retrieval. Raw posts are never embedded."""

    __tablename__ = "rag_documents"
    __table_args__ = (
        Index("idx_rag_documents_created_at", "created_at"),
        Index("idx_rag_documents_component", "source_component"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_component: Mapped[str] = mapped_column(String(8), nullable=False)  # 'B', 'C', 'D', 'E'
    source_record_id: Mapped[str] = mapped_column(Text, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)

    # 384-dimensional dense vector (paraphrase-multilingual-MiniLM-L12-v2)
    embedding = mapped_column(Vector(384), nullable=True)

    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )


class RAGQueryLog(Base):
    """Mandatory, non-bypassable analyst query audit log for compliance and non-repudiation."""

    __tablename__ = "rag_query_log"
    __table_args__ = (
        Index("idx_rag_query_log_queried_at", "queried_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_doc_ids: Mapped[list[str] | dict[str, Any]] = mapped_column(JSONB, nullable=False)
    relevance_grade: Mapped[str] = mapped_column(String(16), nullable=False)  # 'CORRECT', 'AMBIGUOUS', 'INSUFFICIENT'
    llm_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    cited_source_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    confidence_rating: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_grounded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    queried_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
