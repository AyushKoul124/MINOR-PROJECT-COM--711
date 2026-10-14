"""Component C — Demographic Agent.

Orchestrates heuristic bio-text mining, diurnal posting rhythm extraction,
and DPDP Act 2023 k-anonymity privacy enforcement across rolling observation windows.

Operational Architecture:
    - Tier 1 (Broadcast Channel Level): Diurnal rhythm analysis across channel posts
      (peak hours, active phases, UTC to IST mapping).
    - Tier 2 (Audience Engagement Sampling): Inferred demographic distributions
      from public comment participants (raw_authors).
    - Privacy Guard: Enforces minimum cluster size (k >= 50, or k=15 in demo mode).
      Clusters with n < k return below_threshold=True.
    - Persistence: Writes aggregate distributions to ``demographic_aggregates_c``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from demographic_c.bio_parser import (
    AuthorProfileInput,
    BioParser,
    DemographicInferenceResult,
)
from demographic_c.cluster_guard import AnonymityAssessment, ClusterGuard
from demographic_c.pattern_analyzer import DiurnalRhythmResult, PatternAnalyzer
from demographic_c.summary import generate_demographic_summary
from storage.database import SyncSessionLocal
from storage.models.derived_c import DemographicAggregateC
from storage.models.raw import MonitoredChannel, RawAuthor, RawPost

logger = logging.getLogger("demographic_c.agent")


@dataclass
class DemographicClusterResult:
    """Complete demographic profile result for an audience cluster."""

    cluster_label: str
    window_start: datetime
    window_end: datetime
    account_count: int
    below_threshold: bool
    age_bracket_dist: dict[str, float]
    interest_dist: dict[str, float]
    geography_dist: dict[str, float]
    language_dist: dict[str, float]
    inference_confidence: float
    summary: str
    diurnal_rhythm: DiurnalRhythmResult
    privacy_assessment: AnonymityAssessment
    persisted_id: int | None = None


class DemographicAgent:
    """Component C agent orchestrating demographic profiling and privacy protection."""

    def __init__(
        self,
        min_cluster_size: int | None = None,
        use_demo_threshold: bool = False,
    ) -> None:
        """Initialize the demographic agent.

        Args:
            min_cluster_size: Minimum cluster size threshold. If None, reads from env.
            use_demo_threshold: If True, uses demo threshold (default 15).
        """
        self.guard = ClusterGuard(
            min_cluster_size=min_cluster_size,
            use_demo_threshold=use_demo_threshold,
        )
        self.bio_parser = BioParser()
        self.pattern_analyzer = PatternAnalyzer()

    def profile_cohort(
        self,
        cluster_label: str,
        authors: list[RawAuthor | AuthorProfileInput],
        posts: list[RawPost],
        window_start: datetime,
        window_end: datetime,
    ) -> DemographicClusterResult:
        """Profile an in-memory cohort of authors and messages.

        Args:
            cluster_label: Descriptive name for this cluster.
            authors: List of author profile records.
            posts: List of posts for diurnal rhythm extraction.
            window_start: Start of observation window (UTC).
            window_end: End of observation window (UTC).

        Returns:
            DemographicClusterResult with distributions, privacy flag, and summary.
        """
        # Convert raw authors to AuthorProfileInput if needed
        profile_inputs: list[AuthorProfileInput] = []
        for a in authors:
            if isinstance(a, AuthorProfileInput):
                profile_inputs.append(a)
            else:
                profile_inputs.append(
                    AuthorProfileInput(
                        author_id=getattr(a, "platform_author_id", str(getattr(a, "id", ""))),
                        display_name=getattr(a, "display_name", None),
                        bio_text=getattr(a, "bio_text", None),
                    )
                )

        account_count = len(profile_inputs)

        # 1. Privacy assessment (DPDP k-anonymity)
        assessment = self.guard.assess(account_count)

        # 2. Extract bio-text and author attributes
        inference = self.bio_parser.aggregate_profiles(profile_inputs)

        # 3. Analyze temporal diurnal rhythms
        post_timestamps = [p.posted_at for p in posts if getattr(p, "posted_at", None) is not None]
        rhythm = self.pattern_analyzer.analyze_timestamps(post_timestamps)

        # 4. Generate 2-4 sentence factual intelligence summary
        summary_text = generate_demographic_summary(
            cluster_label=cluster_label,
            account_count=account_count,
            below_threshold=assessment.below_threshold,
            age_bracket_dist=inference.age_bracket_dist,
            interest_dist=inference.interest_dist,
            geography_dist=inference.geography_dist,
            language_dist=inference.language_dist,
            confidence=inference.inference_confidence,
            primary_phase=rhythm.primary_active_phase,
        )

        return DemographicClusterResult(
            cluster_label=cluster_label,
            window_start=window_start,
            window_end=window_end,
            account_count=account_count,
            below_threshold=assessment.below_threshold,
            age_bracket_dist=inference.age_bracket_dist,
            interest_dist=inference.interest_dist,
            geography_dist=inference.geography_dist,
            language_dist=inference.language_dist,
            inference_confidence=inference.inference_confidence,
            summary=summary_text,
            diurnal_rhythm=rhythm,
            privacy_assessment=assessment,
        )

    def run_window_analysis(
        self,
        window_hours: int = 48,
        channel_id: str | None = None,
        persist: bool = True,
    ) -> list[DemographicClusterResult]:
        """Execute demographic profiling over a rolling database window.

        Args:
            window_hours: Trailing hours to query (default 48).
            channel_id: Optional channel filter. If None, analyzes both global
                audience and top individual channels.
            persist: If True, writes records to ``demographic_aggregates_c``.

        Returns:
            List of DemographicClusterResult objects.
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=window_hours)
        window_end = now

        results: list[DemographicClusterResult] = []

        with SyncSessionLocal() as session:
            # 1. Fetch raw authors from the window
            author_stmt = select(RawAuthor).order_by(RawAuthor.id.desc())
            authors = list(session.execute(author_stmt).scalars().all())

            # 2. Fetch raw posts from the window strictly using posted_at
            post_stmt = (
                select(RawPost)
                .where(RawPost.posted_at >= window_start)
                .order_by(RawPost.posted_at.desc())
            )
            if channel_id:
                post_stmt = post_stmt.where(RawPost.channel_id == channel_id)

            posts = list(session.execute(post_stmt).scalars().all())

            if not posts and not authors:
                logger.warning("No posts or authors found in the %d-hour window.", window_hours)
                return []

            # 3. Overall global audience cluster
            global_label = "Overall Monitored Audience" if not channel_id else f"{channel_id} Audience"
            global_result = self.profile_cohort(
                cluster_label=global_label,
                authors=authors,
                posts=posts,
                window_start=window_start,
                window_end=window_end,
            )
            results.append(global_result)

            # 4. If no specific channel was requested, also profile per-domain cohorts
            if not channel_id:
                # Group posts by channel to profile active channel cohorts
                channel_posts_map: dict[str, list[RawPost]] = {}
                for p in posts:
                    channel_posts_map.setdefault(p.channel_id, []).append(p)

                # Profile top 3 channels by message volume
                sorted_channels = sorted(
                    channel_posts_map.items(), key=lambda kv: len(kv[1]), reverse=True
                )[:3]

                for ch_id, ch_posts in sorted_channels:
                    # Match authors who contributed to this channel
                    ch_author_ids = {p.author_id for p in ch_posts if p.author_id}
                    ch_authors = [a for a in authors if a.platform_author_id in ch_author_ids]

                    ch_result = self.profile_cohort(
                        cluster_label=f"{ch_id} Audience",
                        authors=ch_authors,
                        posts=ch_posts,
                        window_start=window_start,
                        window_end=window_end,
                    )
                    results.append(ch_result)

            # 5. Persist to demographic_aggregates_c if requested
            if persist:
                for res in results:
                    record_id = self._persist_result(session, res)
                    res.persisted_id = record_id
                session.commit()

        return results

    def run_demo_analysis(self) -> list[DemographicClusterResult]:
        """Execute a quick analysis run for the live viva demo trigger.

        Uses the demo threshold (DEMO_MIN_CLUSTER_SIZE=15) so that sub-threshold
        privacy behavior and compliant clusters can both be demonstrated.
        """
        demo_agent = DemographicAgent(use_demo_threshold=True)
        return demo_agent.run_window_analysis(window_hours=48, persist=True)

    @staticmethod
    def _persist_result(session: Any, result: DemographicClusterResult) -> int:
        """Insert a demographic cluster record into demographic_aggregates_c.

        Returns:
            The primary key ID of the inserted record.
        """
        stmt = (
            pg_insert(DemographicAggregateC)
            .values(
                cluster_label=result.cluster_label,
                window_start=result.window_start,
                window_end=result.window_end,
                account_count=result.account_count,
                below_threshold=result.below_threshold,
                age_bracket_dist=result.age_bracket_dist,
                geography_dist=result.geography_dist,
                language_dist=result.language_dist,
                interest_dist=result.interest_dist,
                inference_confidence=result.inference_confidence,
                analyzed_at=datetime.now(timezone.utc),
            )
            .returning(DemographicAggregateC.id)
        )
        row = session.execute(stmt).fetchone()
        return row[0] if row else 0
