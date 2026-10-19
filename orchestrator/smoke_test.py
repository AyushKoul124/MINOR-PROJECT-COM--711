"""Quick smoke test — verify Orchestrator coordination engine and 'Run Analysis Now' live demo trigger.

Run:
    python -m orchestrator.smoke_test
"""

from __future__ import annotations

import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from orchestrator.coordinator import AnalysisCoordinator, purge_vram


def test_telemetry() -> None:
    print("[1/3] Testing Pipeline Telemetry Reporting...")
    coord = AnalysisCoordinator()
    telemetry = coord.get_pipeline_telemetry()

    assert "monitored_channels_active" in telemetry
    assert "raw_posts_total" in telemetry
    assert "raw_posts_pending" in telemetry
    assert "raw_posts_processed" in telemetry
    print(
        f"  ✓ Telemetry verified: {telemetry['monitored_channels_active']} active channels, "
        f"{telemetry['raw_posts_total']} total posts ({telemetry['raw_posts_pending']} pending, "
        f"{telemetry['raw_posts_processed']} processed)."
    )


def test_vram_purge() -> None:
    print("[2/3] Testing PyTorch VRAM Purge Utility...")
    # Should execute without errors regardless of whether CUDA is available
    purge_vram()
    print("  ✓ VRAM purge executed successfully.")


def test_trigger_full_analysis() -> None:
    print("[3/3] Testing 'Run Analysis Now' Live Demo Trigger...")
    coord = AnalysisCoordinator(demo_b_batch_size=50)

    t0 = time.perf_counter()
    report = coord.trigger_full_analysis(b_batch_limit=50, window_hours=48)
    elapsed = round(time.perf_counter() - t0, 3)

    assert report["status"] == "success"
    assert "component_b" in report
    assert "component_c" in report
    assert "component_d" in report
    assert "component_e" in report

    c_metrics = report["component_c"]
    d_metrics = report["component_d"]
    e_metrics = report["component_e"]

    print(f"  ✓ Full pipeline completed in {elapsed}s.")
    print(f"    - Component B: {report['component_b'].get('processed_count', 0)} posts processed in {report['component_b'].get('elapsed_seconds', 0)}s")
    print(f"    - Component C: {c_metrics.get('clusters_identified', 0)} demographic clusters in {c_metrics.get('elapsed_seconds', 0)}s")
    print(f"    - Component D: {d_metrics.get('topics_discovered', 0)} topics discovered ({d_metrics.get('total_posts_clustered', 0)} posts) in {d_metrics.get('elapsed_seconds', 0)}s")
    print(f"    - Component E: {e_metrics.get('nodes_count', 0)} nodes, {e_metrics.get('edges_count', 0)} edges, Q={e_metrics.get('modularity', 0)} in {e_metrics.get('elapsed_seconds', 0)}s")

    # Verify pipeline telemetry reflects the run
    telemetry = coord.get_pipeline_telemetry()
    assert telemetry["last_run_telemetry"].get("status") == "success"
    print("  ✓ Orchestrator telemetry updated with last run status.")


def main() -> None:
    print("=" * 65)
    print("Orchestrator Coordination Engine Smoke Test Suite")
    print("=" * 65)
    test_telemetry()
    test_vram_purge()
    test_trigger_full_analysis()
    print("=" * 65)
    print("ALL ORCHESTRATOR TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    main()
