"""RAG Layer — End-to-End Grounded Retrieval-Augmented Generation Engine.

Orchestrates semantic retrieval, cosine distance cutoff gating, dual-tier LLM
answer generation, and mandatory audit logging to ``rag_query_log``.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from rag.indexer import RAGIndexer
from rag.llm.client import RouterLLMClient
from rag.retriever import RAGRetriever
from storage.database import SyncSessionLocal
from storage.models.rag import RAGQueryLog

logger = logging.getLogger("rag.engine")


class RAGEngine:
    """Complete RAG pipeline: vector retrieval, LLM routing, and audit logging."""

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        indexer: RAGIndexer | None = None,
        llm_router: RouterLLMClient | None = None,
    ) -> None:
        self.retriever = retriever or RAGRetriever()
        self.indexer = indexer or RAGIndexer()
        self.llm = llm_router or RouterLLMClient()

    def query(
        self,
        question: str,
        source_component: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Process analyst query with semantic retrieval, LLM synthesis, and audit logging.

        Args:
            question: Analyst question or inquiry string.
            source_component: Optional component filter ('B', 'C', 'D', 'E').
            top_k: Number of relevant evidence snippets to retrieve.

        Returns:
            Dict containing answer_text, citations, documents, confidence, and audit ID.
        """
        t0 = time.perf_counter()
        clean_q = question.strip()
        logger.info("Executing RAG query: '%s'...", clean_q)

        # 1. Semantic retrieval with distance cutoff gating
        retrieval_res = self.retriever.retrieve(
            query=clean_q,
            source_component=source_component,
            top_k=top_k,
        )

        # 2. Check for short-circuit cutoff abort
        if retrieval_res.is_short_circuited:
            elapsed = round(time.perf_counter() - t0, 3)
            abort_msg = retrieval_res.abort_reason or "Confidence threshold cutoff exceeded."
            logger.info("RAG Query short-circuited: %s", abort_msg)

            # Persist non-bypassable audit record
            audit_id = self._log_audit(
                question=clean_q,
                retrieved_doc_ids=[],
                relevance_grade="INSUFFICIENT",
                llm_provider="short_circuit_gate",
                answer=abort_msg,
                cited_source_ids=[],
                confidence=0.0,
                is_grounded=False,
            )

            return {
                "question": clean_q,
                "answer": abort_msg,
                "is_grounded": False,
                "is_short_circuited": True,
                "confidence": 0.0,
                "provider": "short_circuit_gate",
                "citations": [],
                "documents": [],
                "audit_id": audit_id,
                "elapsed_seconds": elapsed,
            }

        # 3. Format context documents for LLM
        context_docs = [
            {
                "doc_id": d.doc_id,
                "source_component": d.source_component,
                "source_record_id": d.source_record_id,
                "content_text": d.content_text,
                "similarity_score": d.similarity_score,
                "cosine_distance": d.cosine_distance,
            }
            for d in retrieval_res.documents
        ]

        # 4. Generate grounded answer
        llm_resp = self.llm.generate_grounded_answer(clean_q, context_docs)
        elapsed = round(time.perf_counter() - t0, 3)

        # 5. Persist mandatory audit record to rag_query_log
        doc_ids = [d["doc_id"] for d in context_docs]
        audit_id = self._log_audit(
            question=clean_q,
            retrieved_doc_ids=doc_ids,
            relevance_grade="CORRECT" if llm_resp.is_grounded else "AMBIGUOUS",
            llm_provider=f"{llm_resp.provider}:{llm_resp.model_name}",
            answer=llm_resp.answer_text,
            cited_source_ids=llm_resp.cited_doc_ids,
            confidence=llm_resp.confidence,
            is_grounded=llm_resp.is_grounded,
        )

        return {
            "question": clean_q,
            "answer": llm_resp.answer_text,
            "is_grounded": llm_resp.is_grounded,
            "is_short_circuited": False,
            "confidence": llm_resp.confidence,
            "provider": f"{llm_resp.provider}:{llm_resp.model_name}",
            "citations": llm_resp.cited_doc_ids,
            "documents": context_docs,
            "audit_id": audit_id,
            "elapsed_seconds": elapsed,
        }

    def sync_knowledge_store(self) -> dict[str, int]:
        """Trigger indexer to sync latest agent summaries into pgvector."""
        return self.indexer.index_all_components()

    @staticmethod
    def _log_audit(
        question: str,
        retrieved_doc_ids: list[str],
        relevance_grade: str,
        llm_provider: str,
        answer: str,
        cited_source_ids: list[str],
        confidence: float,
        is_grounded: bool,
    ) -> str:
        """Persist immutable analyst query audit log entry."""
        with SyncSessionLocal() as session:
            stmt = (
                pg_insert(RAGQueryLog)
                .values(
                    question_text=question,
                    retrieved_doc_ids=retrieved_doc_ids,
                    relevance_grade=relevance_grade,
                    llm_provider=llm_provider,
                    answer_text=answer,
                    cited_source_ids=cited_source_ids,
                    confidence_rating=confidence,
                    is_grounded=is_grounded,
                    queried_at=datetime.now(timezone.utc),
                )
                .returning(RAGQueryLog.id)
            )
            row = session.execute(stmt).fetchone()
            session.commit()
            return str(row[0]) if row else ""
