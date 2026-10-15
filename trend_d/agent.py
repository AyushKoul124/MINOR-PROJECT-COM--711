"""Component D — Trend & Velocity Agent.

Orchestrates neural topic modeling (BERTopic), hourly velocity and acceleration
calculations strictly anchored to ``raw_posts.posted_at``, and database persistence
to ``trend_topics_d``.

Operational Architecture:
    - Queries raw_posts across trailing rolling windows (default: 48 hours).
    - Clusters discourse using multilingual sentence embeddings and HDBSCAN.
    - Applies outlier reduction via c-TF-IDF to prevent unassigned posts.
    - Computes hourly velocity (v = Δposts / Δt) and acceleration (a = Δv / Δt).
    - Persists ranked topic snapshots to PostgreSQL.
    - Produces factual intelligence summary strings for RAG indexing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from storage.database import SyncSessionLocal
from storage.models.derived_d import TrendTopicD
from storage.models.raw import RawPost
from trend_d.summary import generate_trend_summary
from trend_d.topic_model import (
    TopicDefinition,
    TopicModeler,
    TopicModelingResult,
)
from trend_d.velocity import TopicVelocityMetrics, VelocityEngine

logger = logging.getLogger("trend_d.agent")


@dataclass
class TrendRunResult:
    """Complete results of a trend analysis execution run."""

    window_start: datetime
    window_end: datetime
    total_posts_analyzed: int
    ranked_topics: list[TopicVelocityMetrics]
    modeling_result: TopicModelingResult
    summary: str
    persisted_ids: list[int]


class TrendAgent:
    """Component D agent orchestrating topic clustering, velocity modeling, and persistence."""

    def __init__(
        self,
        embedding_model_name: str | None = None,
        min_topic_size: int = 3,
        max_docs: int = 500,
        device: str | None = None,
    ) -> None:
        """Initialize the trend agent."""
        self.modeler = TopicModeler(
            embedding_model_name=embedding_model_name,
            min_topic_size=min_topic_size,
            max_docs=max_docs,
            device=device,
        )
        self.velocity_engine = VelocityEngine(default_window_hours=48.0)

    def analyze_posts(
        self,
        posts: list[RawPost],
        window_start: datetime,
        window_end: datetime,
    ) -> TrendRunResult:
        """Analyze an in-memory collection of posts for topics and velocity.

        Args:
            posts: List of RawPost instances.
            window_start: Window start timestamp (UTC).
            window_end: Window end timestamp (UTC).

        Returns:
            TrendRunResult with discovered topics, velocity metrics, and RAG summary.
        """
        valid_posts = [
            p for p in posts
            if p.content_text and p.content_text.strip() and p.posted_at is not None
        ]

        total_posts = len(valid_posts)
        if total_posts == 0:
            empty_modeling = self.modeler.fit_transform([])
            empty_summary = generate_trend_summary([], 48.0, 0)
            return TrendRunResult(
                window_start=window_start,
                window_end=window_end,
                total_posts_analyzed=0,
                ranked_topics=[],
                modeling_result=empty_modeling,
                summary=empty_summary,
                persisted_ids=[],
            )

        texts = [p.content_text for p in valid_posts]
        post_ids = [p.id for p in valid_posts]

        # 1. Fit BERTopic and assign documents to topics
        modeling_result = self.modeler.fit_transform(texts, post_ids)

        # 2. Group posts by assigned topic ID
        topic_posts_map: dict[int, list[tuple[int, datetime]]] = {}
        for post, assigned_tid in zip(valid_posts, modeling_result.doc_topics):
            topic_posts_map.setdefault(assigned_tid, []).append((post.id, post.posted_at))

        # 3. Calculate velocity and acceleration for each discovered topic
        raw_metrics: list[TopicVelocityMetrics] = []
        for topic_def in modeling_result.topics:
            tid = topic_def.topic_id
            post_items = topic_posts_map.get(tid, [])

            metrics = self.velocity_engine.compute_metrics(
                topic_id=tid,
                topic_label=topic_def.topic_label,
                post_items=post_items,
                window_start=window_start,
                window_end=window_end,
            )
            raw_metrics.append(metrics)

        # 4. Rank topics by velocity & acceleration
        ranked_topics = self.velocity_engine.rank_topics(raw_metrics, filter_outliers=True)

        # 5. Generate factual analytical summary
        window_hours = max(1.0, (window_end - window_start).total_seconds() / 3600.0)
        summary_text = generate_trend_summary(ranked_topics, window_hours, total_posts)

        return TrendRunResult(
            window_start=window_start,
            window_end=window_end,
            total_posts_analyzed=total_posts,
            ranked_topics=ranked_topics,
            modeling_result=modeling_result,
            summary=summary_text,
            persisted_ids=[],
        )

    def run_window_analysis(
        self,
        window_hours: int = 48,
        channel_id: str | None = None,
        persist: bool = True,
    ) -> TrendRunResult:
        """Execute topic discovery and velocity calculations over a rolling database window.

        Args:
            window_hours: Trailing observation window in hours (default: 48).
            channel_id: Optional channel identifier filter.
            persist: If True, commits records to ``trend_topics_d``.

        Returns:
            TrendRunResult with persisted record IDs.
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=window_hours)
        window_end = now

        with SyncSessionLocal() as session:
            # Query posts strictly using posted_at
            stmt = (
                select(RawPost)
                .where(RawPost.posted_at >= window_start)
                .where(RawPost.content_text.isnot(None))
                .order_by(RawPost.posted_at.desc())
            )
            if channel_id:
                stmt = stmt.where(RawPost.channel_id == channel_id)

            posts = list(session.execute(stmt).scalars().all())

            result = self.analyze_posts(posts, window_start, window_end)

            if persist and result.ranked_topics:
                # Map topic_id to keywords from modeling result
                keywords_map = {
                    t.topic_id: t.topic_keywords for t in result.modeling_result.topics
                }

                persisted_ids: list[int] = []
                for topic in result.ranked_topics:
                    kws = keywords_map.get(topic.topic_id, [])
                    insert_stmt = (
                        pg_insert(TrendTopicD)
                        .values(
                            topic_label=topic.topic_label,
                            topic_keywords=kws,
                            window_start=window_start,
                            window_end=window_end,
                            post_count=topic.post_count,
                            velocity=topic.velocity,
                            acceleration=topic.acceleration,
                            rank=topic.rank,
                            sample_post_ids=topic.sample_post_ids,
                            analyzed_at=datetime.now(timezone.utc),
                        )
                        .returning(TrendTopicD.id)
                    )
                    row = session.execute(insert_stmt).fetchone()
                    if row:
                        persisted_ids.append(row[0])

                session.commit()
                result.persisted_ids = persisted_ids
                logger.info(
                    "Persisted %d topics to trend_topics_d for window %s to %s.",
                    len(persisted_ids),
                    window_start.isoformat(),
                    window_end.isoformat(),
                )

        return result

    def run_demo_analysis(self, limit: int = 50) -> TrendRunResult:
        """Fast demonstration run for the 'Run Analysis Now' viva trigger."""
        return self.run_window_analysis(window_hours=48, persist=True)
