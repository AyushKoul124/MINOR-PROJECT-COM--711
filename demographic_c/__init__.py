"""Component C: Demographic Profiling & Audience Intelligence Agent.

Dual-Tier Sampling with DPDP Act 2023 k-Anonymity Privacy Guards:
    1. Tier 1 (Broadcast Level): Macro publishing schedules & diurnal rhythm heatmaps.
    2. Tier 2 (Audience Level): Heuristic bio-text keyword mining on active comment participants.
    3. Privacy Guard: Minimum cluster threshold (k >= 50) suppression via ``below_threshold = True``.
"""

from demographic_c.agent import DemographicAgent, DemographicClusterResult
from demographic_c.bio_parser import (
    AuthorProfileInput,
    BioParser,
    DemographicInferenceResult,
)
from demographic_c.cluster_guard import AnonymityAssessment, ClusterGuard
from demographic_c.pattern_analyzer import DiurnalRhythmResult, PatternAnalyzer
from demographic_c.summary import generate_demographic_summary

__all__ = [
    "DemographicAgent",
    "DemographicClusterResult",
    "BioParser",
    "AuthorProfileInput",
    "DemographicInferenceResult",
    "ClusterGuard",
    "AnonymityAssessment",
    "PatternAnalyzer",
    "DiurnalRhythmResult",
    "generate_demographic_summary",
]
