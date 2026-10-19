"""Pydantic schemas for the FastAPI REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Health & Overview ────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "healthy"
    database_connected: bool = True
    device: str = "cpu"
    version: str = "4.8"
    timestamp: str


class OverviewMetrics(BaseModel):
    active_channels: int
    total_posts: int
    pending_posts: int
    processed_posts: int
    sentiment_distribution: dict[str, int]
    top_emotions: dict[str, int]
    last_analysis_time: str | None = None
    viva_timing_invariant_satisfied: bool = True


class TriggerAnalysisRequest(BaseModel):
    b_batch_limit: int = Field(default=50, ge=1, le=200)
    window_hours: int = Field(default=48, ge=1, le=168)


class TriggerAnalysisResponse(BaseModel):
    status: str
    trigger_type: str
    started_at: str
    completed_at: str
    total_elapsed_seconds: float
    meets_demo_timing_invariant: bool
    component_b: dict[str, Any]
    component_c: dict[str, Any]
    component_d: dict[str, Any]
    component_e: dict[str, Any]


# ── Sentiment & Emotion Timeline ─────────────────────────────────────────────
class SentimentTimelinePoint(BaseModel):
    timestamp: str
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    joy_avg: float = 0.0
    anger_avg: float = 0.0
    fear_avg: float = 0.0
    sadness_avg: float = 0.0
    surprise_avg: float = 0.0
    disgust_avg: float = 0.0


class SentimentTimelineResponse(BaseModel):
    window_hours: int
    total_posts: int
    points: list[SentimentTimelinePoint]
    stance_breakdown: dict[str, int]
    sarcasm_count: int


# ── Demographics & k-Anonymity ───────────────────────────────────────────────
class DemographicClusterItem(BaseModel):
    id: int
    cluster_label: str
    account_count: int
    below_threshold: bool
    age_bracket_dist: dict[str, float]
    geography_dist: dict[str, float]
    language_dist: dict[str, float]
    interest_dist: dict[str, float]
    inference_confidence: float
    analyzed_at: str


class DemographicsResponse(BaseModel):
    window_hours: int
    k_anonymity_threshold: int
    total_clusters: int
    suppressed_clusters: int
    clusters: list[DemographicClusterItem]
    diurnal_rhythm_ist: dict[str, Any] | None = None


# ── Trending Topics & Velocity ───────────────────────────────────────────────
class TrendTopicItem(BaseModel):
    id: int
    rank: int
    topic_label: str
    topic_keywords: list[str]
    post_count: int
    velocity: float
    acceleration: float
    is_surging: bool
    analyzed_at: str


class TrendsResponse(BaseModel):
    window_hours: int
    total_topics: int
    surging_count: int
    topics: list[TrendTopicItem]


# ── Network Graph & CIB Screening ────────────────────────────────────────────
class NetworkNodeItem(BaseModel):
    id: str
    label: str
    entity_type: str
    community_id: int
    betweenness: float
    degree: float
    anomaly_score: float
    coordination_signal: bool


class NetworkLinkItem(BaseModel):
    source: str
    target: str
    type: str
    weight: float


class NetworkGraphResponse(BaseModel):
    total_nodes: int
    total_edges: int
    total_communities: int
    modularity: float
    cib_flagged_count: int
    summary: str
    nodes: list[NetworkNodeItem]
    links: list[NetworkLinkItem]


# ── RAG Grounded Query Terminal ──────────────────────────────────────────────
class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    source_component: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    is_grounded: bool
    is_short_circuited: bool
    confidence: float
    provider: str
    citations: list[str]
    documents: list[dict[str, Any]]
    audit_id: str
    elapsed_seconds: float


# ── Data Sources ─────────────────────────────────────────────────────────────
class DataSourceItem(BaseModel):
    id: int
    identifier: str
    display_name: str
    topic_tags: list[str]
    is_active: bool
    last_polled_at: str | None
    total_posts_collected: int


class DataSourcesResponse(BaseModel):
    total_channels: int
    active_channels: int
    poll_schedule_seconds: int
    jitter_range: str
    channels: list[DataSourceItem]
