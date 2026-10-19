"""Router: Grounded RAG Query Terminal & Vector Synchronization."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from api.schemas.models import RAGQueryRequest, RAGQueryResponse
from rag.engine import RAGEngine

router = APIRouter(prefix="/rag", tags=["Retrieval-Augmented Generation (RAG)"])
rag_engine = RAGEngine()


@router.post("/query", response_model=RAGQueryResponse)
def execute_rag_query(req: RAGQueryRequest):
    """Execute analyst natural language query with semantic retrieval and grounded citation."""
    res = rag_engine.query(
        question=req.question,
        source_component=req.source_component,
        top_k=req.top_k,
    )
    return RAGQueryResponse(**res)


@router.post("/sync")
def sync_vector_knowledge(background_tasks: BackgroundTasks):
    """Trigger background re-indexing of derived intelligence summaries into pgvector."""
    background_tasks.add_task(rag_engine.sync_knowledge_store)
    return {
        "status": "queued",
        "message": "Vector knowledge synchronization queued in background.",
    }
