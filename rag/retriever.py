"""RAG Layer — Semantic Document Retriever via PostgreSQL pgvector.

Retrieves top-k relevant intelligence documents based on cosine distance.
Enforces the cardinal zero-hallucination cutoff invariant:
If the nearest retrieved document has cosine distance > 0.65, the query
short-circuits with an explicit safe abort message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from rag.embedder import RAGEmbedder
from storage.database import SyncSessionLocal
from storage.models.rag import RAGDocument

logger = logging.getLogger("rag.retriever")

DEFAULT_TOP_K = 5
MAX_COSINE_DISTANCE_CUTOFF = 0.65  # Distance > 0.65 triggers short-circuit safe abort


@dataclass(frozen=True)
class RetrievedDoc:
    """Document record with calculated distance and similarity scores."""

    doc_id: str
    source_component: str
    source_record_id: str
    content_text: str
    cosine_distance: float
    similarity_score: float


@dataclass
class RetrievalResult:
    """Complete output of a semantic vector retrieval query."""

    query_text: str
    documents: list[RetrievedDoc]
    is_short_circuited: bool
    abort_reason: str | None = None


class RAGRetriever:
    """Semantic vector retriever using PostgreSQL pgvector cosine distance."""

    def __init__(
        self,
        embedder: RAGEmbedder | None = None,
        top_k: int = DEFAULT_TOP_K,
        distance_cutoff: float = MAX_COSINE_DISTANCE_CUTOFF,
    ) -> None:
        self.embedder = embedder or RAGEmbedder()
        self.top_k = top_k
        self.distance_cutoff = distance_cutoff

    def retrieve(
        self,
        query: str,
        source_component: str | None = None,
        top_k: int | None = None,
    ) -> RetrievalResult:
        """Embed user query and retrieve nearest intelligence documents from pgvector.

        Args:
            query: Analyst natural language inquiry string.
            source_component: Optional filter by component ('B', 'C', 'D', 'E').
            top_k: Optional override for number of documents.

        Returns:
            RetrievalResult containing ranked documents or short-circuit signal.
        """
        k = top_k or self.top_k
        query_vec = self.embedder.embed_text(query)

        with SyncSessionLocal() as session:
            # Cosine distance operator in pgvector: <=>
            dist_expr = RAGDocument.embedding.cosine_distance(query_vec).label("distance")

            stmt = select(
                RAGDocument.id,
                RAGDocument.source_component,
                RAGDocument.source_record_id,
                RAGDocument.content_text,
                dist_expr,
            ).where(RAGDocument.embedding.isnot(None))

            if source_component:
                stmt = stmt.where(RAGDocument.source_component == source_component.upper())

            stmt = stmt.order_by(dist_expr.asc()).limit(k)
            rows = session.execute(stmt).all()

        if not rows:
            return RetrievalResult(
                query_text=query,
                documents=[],
                is_short_circuited=True,
                abort_reason="No documents currently indexed in vector knowledge store.",
            )

        # Check nearest document distance for short-circuit gating
        nearest_distance = float(rows[0][4]) if rows[0][4] is not None else 1.0
        if nearest_distance > self.distance_cutoff:
            logger.info(
                "RAG Short-Circuit Triggered: Nearest document distance %.3f exceeds cutoff %.2f.",
                nearest_distance,
                self.distance_cutoff,
            )
            return RetrievalResult(
                query_text=query,
                documents=[],
                is_short_circuited=True,
                abort_reason=(
                    f"No grounded intelligence records found within confidence threshold "
                    f"(cosine distance {nearest_distance:.3f} > {self.distance_cutoff:.2f}). "
                    f"Request aborted to prevent hallucination."
                ),
            )

        docs: list[RetrievedDoc] = []
        for r in rows:
            dist = float(r[4]) if r[4] is not None else 1.0
            # Retain only items within distance cutoff
            if dist <= self.distance_cutoff:
                similarity = round(max(0.0, 1.0 - dist), 4)
                docs.append(
                    RetrievedDoc(
                        doc_id=str(r[0]),
                        source_component=r[1],
                        source_record_id=r[2],
                        content_text=r[3],
                        cosine_distance=round(dist, 4),
                        similarity_score=similarity,
                    )
                )

        return RetrievalResult(
            query_text=query,
            documents=docs,
            is_short_circuited=False,
            abort_reason=None,
        )
