"""Component E: Network Analytics, Louvain Community Detection & 3-Signal CIB Screening.

Exports:
    - NetworkAgent: High-level orchestrator for graph building, metrics, and persistence.
    - GraphBuilder: NetworkX DiGraph builder with privacy masking and pruning.
    - CentralityEngine: Degree and betweenness centrality calculator.
    - CommunityDetector: Louvain community partitioning engine.
    - CIBDetector: 3-signal advisory CIB anomaly detector.
    - generate_network_summary: 2-4 sentence factual intelligence summary generator.
"""

from network_e.agent import (
    NetworkAgent,
    NetworkEdgeResult,
    NetworkNodeResult,
    NetworkRunResult,
)
from network_e.centrality import CentralityEngine, CentralityScores
from network_e.cib_signals import CIBDetector, CIBSignalsResult
from network_e.community import CommunityDetector, CommunityPartitionResult
from network_e.graph_builder import GraphBuilder
from network_e.summary import generate_network_summary

__all__ = [
    "CentralityEngine",
    "CentralityScores",
    "CIBDetector",
    "CIBSignalsResult",
    "CommunityDetector",
    "CommunityPartitionResult",
    "GraphBuilder",
    "NetworkAgent",
    "NetworkEdgeResult",
    "NetworkNodeResult",
    "NetworkRunResult",
    "generate_network_summary",
]
