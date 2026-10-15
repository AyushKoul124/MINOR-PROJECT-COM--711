"""Component D — Temporal Topic Velocity and Acceleration Calculator.

Critical Invariant:
    - ALWAYS anchors all temporal calculations strictly to platform ``raw_posts.posted_at``
      UTC timestamps.
    - NEVER uses ``ingested_at`` (which reflects scraper polling lag).

Velocity and Acceleration Math:
    - Given an observation window [W_start, W_end] of duration T hours (default 48h):
      Midpoint: W_mid = W_start + T/2
      Earlier half [W_start, W_mid]: n_earlier posts -> v_earlier = n_earlier / (T/2)
      Recent half  [W_mid, W_end]:   n_recent posts  -> v_recent  = n_recent / (T/2)
      Overall velocity:     v = (n_earlier + n_recent) / T  (posts/hour)
      Hourly acceleration:  a = (v_recent - v_earlier) / (T/2) (change in posts/hr per hour)
    - Positive acceleration indicates a breaking / surging trend.
    - Negative acceleration indicates a cooling / decaying trend.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class TopicVelocityMetrics:
    """Calculated velocity and acceleration metrics for a single topic."""

    topic_id: int
    topic_label: str
    post_count: int
    velocity: float       # Overall posts/hour across the window
    acceleration: float   # Rate of change in velocity (recent vs earlier sub-window)
    v_earlier: float      # Velocity in earlier half of window
    v_recent: float       # Velocity in recent half of window
    is_surging: bool      # True if acceleration > 0.05 and v_recent > v_earlier
    sample_post_ids: list[int]
    rank: int = 1


class VelocityEngine:
    """Calculates topic velocities, accelerations, and ranking over temporal windows."""

    def __init__(self, default_window_hours: float = 48.0) -> None:
        self.default_window_hours = max(1.0, float(default_window_hours))

    def compute_metrics(
        self,
        topic_id: int,
        topic_label: str,
        post_items: list[tuple[int, datetime]],  # list of (post_id, posted_at UTC)
        window_start: datetime,
        window_end: datetime,
    ) -> TopicVelocityMetrics:
        """Compute velocity and acceleration for a set of posts assigned to a topic.

        Args:
            topic_id: BERTopic cluster identifier (-1 for outliers, >=0 for valid topics).
            topic_label: Human-readable topic label / representation.
            post_items: List of tuples containing (post_id, posted_at_datetime).
            window_start: Window start timestamp (UTC).
            window_end: Window end timestamp (UTC).

        Returns:
            TopicVelocityMetrics with velocity, acceleration, and surging indicator.
        """
        # Ensure UTC timezone
        w_start = window_start if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)
        w_end = window_end if window_end.tzinfo else window_end.replace(tzinfo=timezone.utc)

        total_hours = max(1.0, (w_end - w_start).total_seconds() / 3600.0)
        half_hours = total_hours / 2.0
        w_mid = w_start + timedelta(hours=half_hours)

        total_posts = len(post_items)
        sample_ids = [pid for pid, _ in post_items[:10]]

        if total_posts == 0:
            return TopicVelocityMetrics(
                topic_id=topic_id,
                topic_label=topic_label,
                post_count=0,
                velocity=0.0,
                acceleration=0.0,
                v_earlier=0.0,
                v_recent=0.0,
                is_surging=False,
                sample_post_ids=[],
            )

        n_earlier = 0
        n_recent = 0

        for _, posted_at in post_items:
            ts = posted_at if posted_at.tzinfo else posted_at.replace(tzinfo=timezone.utc)
            if ts < w_mid:
                n_earlier += 1
            else:
                n_recent += 1

        v_earlier = n_earlier / half_hours
        v_recent = n_recent / half_hours
        velocity = total_posts / total_hours
        acceleration = (v_recent - v_earlier) / half_hours

        # Surging threshold: positive velocity growth with meaningful recent acceleration
        is_surging = acceleration > 0.005 and v_recent > v_earlier

        return TopicVelocityMetrics(
            topic_id=topic_id,
            topic_label=topic_label,
            post_count=total_posts,
            velocity=round(velocity, 4),
            acceleration=round(acceleration, 5),
            v_earlier=round(v_earlier, 4),
            v_recent=round(v_recent, 4),
            is_surging=is_surging,
            sample_post_ids=sample_ids,
        )

    def rank_topics(
        self,
        metrics_list: list[TopicVelocityMetrics],
        filter_outliers: bool = True,
    ) -> list[TopicVelocityMetrics]:
        """Rank topics by velocity (descending) and acceleration (descending).

        Args:
            metrics_list: List of TopicVelocityMetrics.
            filter_outliers: If True, excludes topic_id == -1 from ranking.

        Returns:
            Rank-ordered list of TopicVelocityMetrics with updated 1-based ranks.
        """
        valid = [m for m in metrics_list if not (filter_outliers and m.topic_id == -1)]

        # Primary sort: velocity descending; Secondary: acceleration descending
        sorted_metrics = sorted(
            valid,
            key=lambda m: (m.velocity, m.acceleration),
            reverse=True,
        )

        ranked: list[TopicVelocityMetrics] = []
        for rank_idx, m in enumerate(sorted_metrics, start=1):
            ranked.append(
                TopicVelocityMetrics(
                    topic_id=m.topic_id,
                    topic_label=m.topic_label,
                    post_count=m.post_count,
                    velocity=m.velocity,
                    acceleration=m.acceleration,
                    v_earlier=m.v_earlier,
                    v_recent=m.v_recent,
                    is_surging=m.is_surging,
                    sample_post_ids=m.sample_post_ids,
                    rank=rank_idx,
                )
            )

        return ranked
