"""RAG Layer: pgvector semantic retrieval, dual-tier LLM routing, and query audit logging.

Exports:
    - RAGEngine: Complete end-to-end RAG orchestrator.
    - RAGRetriever: Semantic vector retriever with distance cutoff gating.
    - RAGIndexer: Synchronizes agent summaries from B, C, D, E into pgvector.
    - RAGEmbedder: 384-dimensional dense sentence vector embedder.
"""

from rag.embedder import RAGEmbedder
from rag.engine import RAGEngine
from rag.indexer import RAGIndexer
from rag.retriever import RAGRetriever

__all__ = [
    "RAGEmbedder",
    "RAGEngine",
    "RAGIndexer",
    "RAGRetriever",
]
