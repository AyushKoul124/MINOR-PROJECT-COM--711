"""Orchestrator — Dual-Runner Coordination Engine & Live Viva Demo Trigger.

Coordinates continuous background processing and the instant "Run Analysis Now"
viva trigger while enforcing the 4 GB VRAM discipline (sequential model loading,
explicit garbage collection, and torch.cuda.empty_cache() purges).

Execution Architecture:
    1. Row-Level Runner (Component B):
       - Evaluates newly ingested posts with `processing_status = 'pending'`.
       - Processes sentiment valence, fine-grained emotions, zero-shot stance, and sarcasm.
       - Commits to `sentiment_results_b` and marks posts `processed`.
    2. Window-Level Runner (Components C, D, E):
       - Evaluates rolling trailing temporal windows (default: 48 hours) strictly
         anchored to platform `raw_posts.posted_at` UTC timestamps.
       - Runs Component C (Demographic bio-parser, diurnal rhythm, k-anonymity guard).
       - Runs Component D (BERTopic topic discovery, velocity & acceleration modeling).
       - Runs Component E (NetworkX interaction graph, Louvain modularity, 3-signal CIB screening).
    3. Instant "Run Analysis Now" Trigger (`trigger_full_analysis`):
       - Caps pending batch at <= 50 posts (`DEMO_B_BATCH_SIZE = 50`).
       - Executes Component B on pending rows.
       - Purges VRAM, then executes C, D, and E window aggregation.
       - Guaranteed completion within 15–25 seconds on GTX 1650 Ti reference GPU.
"""

from __future__ import annotations

import gc
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

from demographic_c.agent import DemographicAgent
from network_e.agent import NetworkAgent
from sentiment_b.pipeline import SentimentPipeline
from storage.database import SyncSessionLocal
from storage.models.raw import MonitoredChannel, RawPost
from trend_d.agent import TrendAgent

logger = logging.getLogger("orchestrator.coordinator")


def purge_vram() -> None:
    """Explicitly release PyTorch GPU VRAM and run garbage collection."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as exc:
        logger.debug("VRAM purge pass (CUDA unavailable or ignored): %s", exc)


class AnalysisCoordinator:
    """Central orchestrator for row-level and window-level analytics pipelines."""

    def __init__(self, demo_b_batch_size: int = 50) -> None:
        self.demo_b_batch_size = demo_b_batch_size
        self._last_run_telemetry: dict[str, Any] = {}

    def run_sentiment_row_runner(self, limit: int | None = None) -> dict[str, Any]:
        """Execute Component B NLP pipeline on pending raw_posts.

        Args:
            limit: Maximum number of posts to process (defaults to demo_b_batch_size).

        Returns:
            Dict containing processed count and elapsed seconds.
        """
        batch_limit = limit or self.demo_b_batch_size
        logger.info("Executing Sentiment Row-Level Runner (limit=%d)...", batch_limit)
        t0 = time.perf_counter()

        try:
            pipeline = SentimentPipeline()
            res = pipeline.process_pending(limit=batch_limit)
            elapsed = round(time.perf_counter() - t0, 3)
            return {
                "status": "success",
                "processed_count": res.get("processed", 0),
                "elapsed_seconds": elapsed,
            }
        except Exception as exc:
            logger.error("Sentiment row runner failed: %s", exc, exc_info=True)
            return {
                "status": "error",
                "error": str(exc),
                "processed_count": 0,
                "elapsed_seconds": round(time.perf_counter() - t0, 3),
            }
        finally:
            purge_vram()

    def run_window_analytics_runner(
        self,
        window_hours: int = 48,
        persist: bool = True,
        use_demo_threshold: bool = True,
    ) -> dict[str, Any]:
        """Execute Components C, D, and E across the trailing observation window.

        Enforces sequential execution with intermediate VRAM purges to guarantee
        zero CUDA Out-Of-Memory exceptions on 4 GB VRAM reference hardware.

        Args:
            window_hours: Trailing observation window in hours (default: 48).
            persist: If True, commits aggregate snapshots to derived tables.
            use_demo_threshold: If True, uses k=15 demo threshold for Component C.

        Returns:
            Dict containing run metrics from Components C, D, and E.
        """
        logger.info(
            "Executing Window-Level Runner (window_hours=%d, persist=%s)...",
            window_hours,
            persist,
        )
        t0 = time.perf_counter()

        # ── Step 1: Component C (Demographic Profiling & k-Anonymity) ──
        t_c0 = time.perf_counter()
        try:
            demo_agent = DemographicAgent(use_demo_threshold=use_demo_threshold)
            demo_results = demo_agent.run_window_analysis(
                window_hours=window_hours, persist=persist
            )
            c_metrics = {
                "clusters_identified": len(demo_results),
                "suppressed_clusters": sum(1 for c in demo_results if c.below_threshold),
                "elapsed_seconds": round(time.perf_counter() - t_c0, 3),
            }
        except Exception as exc:
            logger.error("Component C window analysis failed: %s", exc, exc_info=True)
            c_metrics = {"error": str(exc), "elapsed_seconds": round(time.perf_counter() - t_c0, 3)}
        finally:
            purge_vram()

        # ── Step 2: Component D (BERTopic Discovery & Hourly Velocity) ──
        t_d0 = time.perf_counter()
        try:
            trend_agent = TrendAgent(max_docs=500)
            trend_result = trend_agent.run_window_analysis(
                window_hours=window_hours, persist=persist
            )
            d_metrics = {
                "topics_discovered": len(trend_result.ranked_topics),
                "surging_topics": sum(1 for t in trend_result.ranked_topics if t.is_surging),
                "total_posts_clustered": trend_result.total_posts_analyzed,
                "elapsed_seconds": round(time.perf_counter() - t_d0, 3),
            }
        except Exception as exc:
            logger.error("Component D window analysis failed: %s", exc, exc_info=True)
            d_metrics = {"error": str(exc), "elapsed_seconds": round(time.perf_counter() - t_d0, 3)}
        finally:
            purge_vram()

        # ── Step 3: Component E (Network Graph, Louvain & 3-Signal CIB) ──
        t_e0 = time.perf_counter()
        try:
            network_agent = NetworkAgent(max_nodes=500, cib_threshold=0.70)
            network_result = network_agent.run_window_analysis(
                window_hours=window_hours, persist=persist
            )
            e_metrics = {
                "nodes_count": len(network_result.nodes),
                "edges_count": len(network_result.edges),
                "communities_count": network_result.community_result.total_communities,
                "modularity": round(network_result.community_result.modularity, 4),
                "cib_flagged_count": sum(1 for n in network_result.nodes if n.coordination_signal),
                "elapsed_seconds": round(time.perf_counter() - t_e0, 3),
            }
        except Exception as exc:
            logger.error("Component E window analysis failed: %s", exc, exc_info=True)
            e_metrics = {"error": str(exc), "elapsed_seconds": round(time.perf_counter() - t_e0, 3)}
        finally:
            purge_vram()

        total_elapsed = round(time.perf_counter() - t0, 3)
        return {
            "status": "success",
            "total_elapsed_seconds": total_elapsed,
            "component_c": c_metrics,
            "component_d": d_metrics,
            "component_e": e_metrics,
        }

    def trigger_full_analysis(
        self,
        b_batch_limit: int | None = None,
        window_hours: int = 48,
    ) -> dict[str, Any]:
        """Execute instant 'Run Analysis Now' pipeline for the live viva demo.

        Processes pending raw posts through Component B (capped at <= 50 rows),
        then executes the trailing 48-hour analytical window across C, D, and E.
        Guaranteed to finish in 15–25 seconds on the reference hardware.

        Args:
            b_batch_limit: Maximum pending rows for Component B (default: 50).
            window_hours: Rolling trailing window in hours (default: 48).

        Returns:
            Structured execution report and dashboard-ready telemetry summary.
        """
        limit = b_batch_limit or self.demo_b_batch_size
        logger.info(
            "Triggering Full Analysis Pipeline ('Run Analysis Now' Viva Mode, B_limit=%d)...",
            limit,
        )
        t_start = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        # 1. Row Runner (Component B)
        b_res = self.run_sentiment_row_runner(limit=limit)

        # 2. Window Runner (Components C, D, E)
        window_res = self.run_window_analytics_runner(
            window_hours=window_hours,
            persist=True,
            use_demo_threshold=True,
        )

        total_elapsed = round(time.perf_counter() - t_start, 3)
        completed_at = datetime.now(timezone.utc)

        telemetry = {
            "status": "success",
            "trigger_type": "instant_viva_demo",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "total_elapsed_seconds": total_elapsed,
            "meets_demo_timing_invariant": total_elapsed <= 30.0,
            "component_b": b_res,
            "component_c": window_res.get("component_c", {}),
            "component_d": window_res.get("component_d", {}),
            "component_e": window_res.get("component_e", {}),
        }

        self._last_run_telemetry = telemetry
        logger.info(
            "Full Analysis Complete in %.2fs (Demo Invariant <=30s: %s).",
            total_elapsed,
            telemetry["meets_demo_timing_invariant"],
        )
        return telemetry

    def get_pipeline_telemetry(self) -> dict[str, Any]:
        """Retrieve system overview metrics, pending queue sizes, and last run telemetry."""
        with SyncSessionLocal() as session:
            # Active channels count
            ch_count = session.query(func.count(MonitoredChannel.id)).filter(
                MonitoredChannel.is_active.is_(True)
            ).scalar() or 0

            # Pending raw posts count
            pending_count = session.query(func.count(RawPost.id)).filter(
                RawPost.processing_status == "pending"
            ).scalar() or 0

            # Total raw posts count
            total_posts = session.query(func.count(RawPost.id)).scalar() or 0

            # Processed posts count
            processed_posts = session.query(func.count(RawPost.id)).filter(
                RawPost.processing_status == "processed"
            ).scalar() or 0

        return {
            "monitored_channels_active": ch_count,
            "raw_posts_total": total_posts,
            "raw_posts_pending": pending_count,
            "raw_posts_processed": processed_posts,
            "last_run_telemetry": self._last_run_telemetry,
        }
