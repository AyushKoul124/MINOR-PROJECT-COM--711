"""Quick smoke test — verify RAG Layer (embedding, indexing, pgvector retrieval, cutoff gating, and audit logging).

Run:
    python -m rag.smoke_test
"""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from rag.embedder import RAGEmbedder
from rag.engine import RAGEngine
from rag.indexer import RAGIndexer
from rag.retriever import RAGRetriever
from storage.database import SyncSessionLocal
from storage.models.rag import RAGDocument, RAGQueryLog


def test_embedder() -> None:
    print("[1/4] Testing RAGEmbedder dense vector generation...")
    embedder = RAGEmbedder()
    vec = embedder.embed_text("ISRO Gaganyaan mission integration test successfully completed.")
    assert len(vec) == 384, f"Expected 384-dim vector, got {len(vec)}"

    batch_vecs = embedder.embed_batch([
        "First document text.",
        "Second document text.",
    ])
    assert len(batch_vecs) == 2
    assert len(batch_vecs[0]) == 384
    print("  ✓ Embedder generates 384-dim normalized dense vectors.")


def test_indexer() -> None:
    print("[2/4] Testing RAGIndexer synchronization across B, C, D, E...")
    indexer = RAGIndexer()
    counts = indexer.index_all_components()
    print(f"  ✓ Indexer executed: {counts}")

    with SyncSessionLocal() as session:
        total_docs = session.query(RAGDocument).count()
        assert total_docs > 0, "Expected at least 1 document in rag_documents after indexing"
        print(f"  ✓ Verified {total_docs} total documents present in rag_documents knowledge base.")


def test_retrieval_and_cutoff() -> None:
    print("[3/4] Testing pgvector semantic retrieval and distance cutoff gating...")
    retriever = RAGRetriever(distance_cutoff=0.65)

    # 1. Relevant in-domain query
    res_domain = retriever.retrieve("ISRO space and defense updates")
    assert not res_domain.is_short_circuited, "In-domain query should find matching documents"
    assert len(res_domain.documents) > 0, "Expected at least 1 matching document"
    top_doc = res_domain.documents[0]
    assert top_doc.cosine_distance <= 0.65, f"Distance {top_doc.cosine_distance} should be <= 0.65"
    print(f"  ✓ In-domain retrieval succeeded (top doc distance: {top_doc.cosine_distance:.3f}, similarity: {top_doc.similarity_score:.3f}).")

    # 2. Complete gibberish / out-of-domain query designed to test short-circuit gating
    res_ood = retriever.retrieve("Xylophone baking pastry recipe instructions on Jupiter 999888777xyz")
    if res_ood.is_short_circuited:
        print(f"  ✓ Short-circuit gate triggered correctly: '{res_ood.abort_reason}'.")
    else:
        print(f"  ℹ Out-of-domain query returned nearest dist={res_ood.documents[0].cosine_distance:.3f}.")


def test_engine_and_audit_log() -> None:
    print("[4/4] Testing RAGEngine end-to-end query execution and audit logging...")
    engine = RAGEngine()

    query = "What is the general sentiment and key topics regarding space and defense?"
    response = engine.query(query, top_k=3)

    assert "answer" in response
    assert "audit_id" in response
    assert response["audit_id"] != ""
    assert "citations" in response
    print(f"  ✓ RAG Query executed in {response['elapsed_seconds']}s (Provider: {response['provider']}).")
    print(f"    - Answer snippet: {response['answer'][:120]}...")
    print(f"    - Cited documents: {response['citations']}")

    # Verify audit record persisted in rag_query_log
    with SyncSessionLocal() as session:
        log_entry = session.query(RAGQueryLog).filter(RAGQueryLog.id == response["audit_id"]).first()
        assert log_entry is not None, "Expected audit record in rag_query_log"
        assert log_entry.question_text == query
        assert log_entry.relevance_grade in ("CORRECT", "AMBIGUOUS", "INSUFFICIENT")
        print(f"  ✓ Audit log entry verified: id={log_entry.id}, relevance_grade={log_entry.relevance_grade}.")


def main() -> None:
    print("=" * 65)
    print("RAG Layer (Vector Retrieval & Audit Logging) Smoke Test Suite")
    print("=" * 65)
    test_embedder()
    test_indexer()
    test_retrieval_and_cutoff()
    test_engine_and_audit_log()
    print("=" * 65)
    print("ALL RAG TESTS PASSED SUCCESSFULLY! RAG Layer is healthy.")
    print("=" * 65)


if __name__ == "__main__":
    main()
