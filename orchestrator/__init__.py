"""Orchestrator package: dual-runner coordination engine, Celery Beat schedules, and viva demo trigger.

Exports:
    - AnalysisCoordinator: Central coordinator for row-level and window-level analytics.
    - purge_vram: GPU VRAM release and PyTorch cache clearing utility.
"""

from orchestrator.coordinator import AnalysisCoordinator, purge_vram

__all__ = [
    "AnalysisCoordinator",
    "purge_vram",
]
