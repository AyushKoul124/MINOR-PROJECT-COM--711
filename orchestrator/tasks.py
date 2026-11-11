"""Celery task definitions and Beat scheduling for the Orchestrator.

Provides asynchronous task wrappers for:
1. task_process_pending_sentiment: Periodic row runner for Component B.
2. task_run_window_analytics: Periodic 48-hour rolling window runner for C/D/E.
3. task_trigger_full_analysis: Asynchronous execution of the instant viva demo trigger.

Worker Launch Command:
    celery -A orchestrator.tasks worker --loglevel=info --concurrency=1 -Q analytics
"""

from __future__ import annotations

import logging
import os
from typing import Any

from celery import Celery
from dotenv import load_dotenv

from orchestrator.coordinator import AnalysisCoordinator

load_dotenv()

logger = logging.getLogger("orchestrator.tasks")

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/2")

app = Celery("orchestrator")
app.conf.update(
    broker_url=BROKER_URL,
    result_backend=RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="analytics",
    task_routes={
        "orchestrator.tasks.task_process_pending_sentiment": {"queue": "analytics"},
        "orchestrator.tasks.task_run_window_analytics": {"queue": "analytics"},
        "orchestrator.tasks.task_trigger_full_analysis": {"queue": "analytics"},
        "orchestrator.tasks.task_index_rag_knowledge": {"queue": "analytics"},
    },
    beat_schedule={
        # Continuous row-level runner: evaluate newly ingested posts every 15 minutes
        "process-pending-sentiment-every-15-min": {
            "task": "orchestrator.tasks.task_process_pending_sentiment",
            "schedule": 900.0,  # 15 minutes
            "args": [50],
        },
        # Window-level analytics: refresh C, D, and E derived metrics every 60 minutes
        "refresh-window-analytics-every-hour": {
            "task": "orchestrator.tasks.task_run_window_analytics",
            "schedule": 3600.0,  # 1 hour
            "args": [48],
        },
    },
)

coordinator = AnalysisCoordinator()


@app.task(name="orchestrator.tasks.task_process_pending_sentiment")
def task_process_pending_sentiment(limit: int = 50) -> dict[str, Any]:
    """Celery task: process pending raw_posts through Component B."""
    logger.info("Executing Celery task: process_pending_sentiment (limit=%d)...", limit)
    return coordinator.run_sentiment_row_runner(limit=limit)


@app.task(name="orchestrator.tasks.task_run_window_analytics")
def task_run_window_analytics(window_hours: int = 48) -> dict[str, Any]:
    """Celery task: run 48-hour trailing window analytics across C, D, and E."""
    logger.info("Executing Celery task: run_window_analytics (window_hours=%d)...", window_hours)
    result = coordinator.run_window_analytics_runner(
        window_hours=window_hours, persist=True, use_demo_threshold=False
    )
    return _append_rag_indexing(result)


@app.task(name="orchestrator.tasks.task_index_rag_knowledge")
def task_index_rag_knowledge() -> dict[str, Any]:
    """Celery task: sync B–E agent summaries into pgvector (post-window refresh)."""
    logger.info("Executing Celery task: index_rag_knowledge...")
    return _run_rag_indexing_only()


def _run_rag_indexing_only() -> dict[str, Any]:
    from orchestrator.coordinator import purge_vram

    try:
        from rag.indexer import RAGIndexer
    except ImportError as exc:
        return {"rag_indexing": {"status": "skipped", "error": str(exc), "indexed_counts": {}}}

    import time

    t0 = time.perf_counter()
    try:
        counts = RAGIndexer().index_all_components()
        payload = {
            "status": "success",
            "indexed_counts": counts,
            "total_indexed": sum(counts.values()),
            "elapsed_seconds": round(time.perf_counter() - t0, 3),
        }
    except Exception as exc:
        logger.error("Celery RAG indexing failed: %s", exc, exc_info=True)
        payload = {
            "status": "error",
            "error": str(exc),
            "indexed_counts": {},
            "elapsed_seconds": round(time.perf_counter() - t0, 3),
        }
    finally:
        purge_vram()
    return {"rag_indexing": payload}


def _append_rag_indexing(window_result: dict[str, Any]) -> dict[str, Any]:
    rag_payload = _run_rag_indexing_only()
    return {**window_result, **rag_payload}


@app.task(name="orchestrator.tasks.task_trigger_full_analysis")
def task_trigger_full_analysis(b_batch_limit: int = 50, window_hours: int = 48) -> dict[str, Any]:
    """Celery task: execute full demo analysis pipeline."""
    logger.info("Executing Celery task: trigger_full_analysis...")
    return coordinator.trigger_full_analysis(
        b_batch_limit=b_batch_limit, window_hours=window_hours
    )
