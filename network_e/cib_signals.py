"""Component E — 3-Signal Coordinated Inauthentic Behavior (CIB) Screening Engine.

Evaluates behavioral anomalies across participating entities to detect
coordinated influence campaigns, astro-turfing, and message amplification.

Critical Invariants & Defense Posture:
    1. Heuristic Arithmetic Mean:
       anomaly_score = (s1_synchrony + s2_age_volume + s3_duplicate_content) / 3
    2. Coordination Screening Cutoff:
       coordination_signal = TRUE if anomaly_score >= 0.70 (configurable).
    3. Advisory Signal Only:
       Outputs are explicitly labeled 'anomaly_score' and 'coordination_signal'.
       They are never presented as legal verdicts, attribution assertions, or 'bot' labels.
    4. Temporal Grounding:
       All synchrony metrics use platform ``raw_posts.posted_at`` UTC timestamps
       (never ``ingested_at``).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from storage.models.raw import RawAuthor, RawPost

logger = logging.getLogger("network_e.cib_signals")

DEFAULT_CIB_THRESHOLD = 0.70
SYNCHRONY_WINDOW_SECONDS = 120.0  # Posts within 2 minutes considered synchronized


@dataclass(frozen=True)
class CIBSignalsResult:
    """Calculated CIB anomaly signals and composite score for an entity."""

    entity_id: str
    posting_synchrony_signal: float   # s1: 0.0 to 1.0
    age_volume_signal: float          # s2: 0.0 to 1.0
    duplicate_content_signal: float   # s3: 0.0 to 1.0
    anomaly_score: float              # unweighted mean: (s1 + s2 + s3) / 3
    coordination_signal: bool         # True if anomaly_score >= threshold
    signal_details: dict[str, Any]    # Diagnostic breakdown


class CIBDetector:
    """Computes the 3 unweighted CIB anomaly screening signals."""

    def __init__(
        self,
        anomaly_threshold: float = DEFAULT_CIB_THRESHOLD,
        synchrony_window_seconds: float = SYNCHRONY_WINDOW_SECONDS,
    ) -> None:
        raw_thresh = os.getenv("CIB_ANOMALY_THRESHOLD", str(anomaly_threshold))
        self.threshold = float(raw_thresh)
        self.synchrony_window = float(synchrony_window_seconds)

    def compute_signals(
        self,
        entity_id: str,
        entity_type: str,
        entity_posts: list[RawPost],
        all_posts: list[RawPost],
        author_meta: RawAuthor | None = None,
    ) -> CIBSignalsResult:
        """Compute the 3 CIB signals for an individual entity.

        Args:
            entity_id: Channel or author platform identifier.
            entity_type: 'channel' or 'author'.
            entity_posts: All posts published by this entity in the window.
            all_posts: All posts published across the entire network in the window.
            author_meta: Optional author profile metadata (for account creation age).

        Returns:
            CIBSignalsResult with s1, s2, s3, composite anomaly_score, and boolean flag.
        """
        # Signal 1: Posting Synchrony (s1)
        s1 = self._compute_posting_synchrony(entity_posts, all_posts, entity_id)

        # Signal 2: Account Age vs Posting Volume (s2)
        s2 = self._compute_age_volume(entity_posts, author_meta, entity_type)

        # Signal 3: Duplicate Content Similarity (s3)
        s3 = self._compute_duplicate_content(entity_posts, all_posts, entity_id)

        # Composite Anomaly Score: unweighted arithmetic mean
        anomaly_score = round((s1 + s2 + s3) / 3.0, 4)
        is_coordinated = anomaly_score >= self.threshold

        details = {
            "post_count": len(entity_posts),
            "s1_synchrony_score": s1,
            "s2_age_volume_score": s2,
            "s3_duplicate_content_score": s3,
            "threshold": self.threshold,
        }

        return CIBSignalsResult(
            entity_id=entity_id,
            posting_synchrony_signal=s1,
            age_volume_signal=s2,
            duplicate_content_signal=s3,
            anomaly_score=anomaly_score,
            coordination_signal=is_coordinated,
            signal_details=details,
        )

    def _compute_posting_synchrony(
        self,
        entity_posts: list[RawPost],
        all_posts: list[RawPost],
        entity_id: str,
    ) -> float:
        """Calculate temporal synchrony (s1).

        Evaluates the fraction of entity posts that occur within a tight
        co-occurrence window (<= SYNCHRONY_WINDOW_SECONDS) of posts by *other* entities.
        """
        if not entity_posts:
            return 0.0

        entity_ts = [
            p.posted_at.timestamp()
            for p in entity_posts
            if p.posted_at is not None
        ]

        # Other entities' post timestamps
        other_ts = [
            p.posted_at.timestamp()
            for p in all_posts
            if p.posted_at is not None and (p.author_id != entity_id and p.channel_id != entity_id)
        ]

        if not entity_ts or not other_ts:
            return 0.0

        synchronized_count = 0
        for t_e in entity_ts:
            # Check if any other post occurred within +/- synchrony_window
            if any(abs(t_e - t_o) <= self.synchrony_window for t_o in other_ts):
                synchronized_count += 1

        sync_ratio = synchronized_count / len(entity_ts)
        return round(float(sync_ratio), 4)

    def _compute_age_volume(
        self,
        entity_posts: list[RawPost],
        author_meta: RawAuthor | None,
        entity_type: str,
    ) -> float:
        """Calculate account age vs volume incongruity (s2).

        High score for very young accounts (e.g. < 30 days) with high posting volume,
        or newly created accounts flooding discussion threads.
        """
        if entity_type == "channel":
            # Channels are established broadcast hubs; age volume heuristic is author-centric
            return 0.10

        if not author_meta or not author_meta.account_created_at:
            # Without explicit creation date, fall back to post burst heuristic
            volume = len(entity_posts)
            if volume > 20:
                return 0.40
            if volume > 10:
                return 0.25
            return 0.10

        now = datetime.now(timezone.utc)
        created_at = author_meta.account_created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age_days = max(1.0, (now - created_at).total_seconds() / 86400.0)
        volume = len(entity_posts)

        # Incongruity heuristic: posts per day of account age
        post_rate = volume / age_days

        if age_days < 14 and volume >= 10:
            return 0.95
        if age_days < 30 and volume >= 15:
            return 0.85
        if age_days < 60 and volume >= 20:
            return 0.70
        if post_rate > 1.0:
            return min(0.80, round(post_rate * 0.3, 4))

        return max(0.05, round(min(0.5, volume / 100.0), 4))

    def _compute_duplicate_content(
        self,
        entity_posts: list[RawPost],
        all_posts: list[RawPost],
        entity_id: str,
    ) -> float:
        """Calculate duplicate content similarity (s3).

        Evaluates maximum TF-IDF cosine similarity between entity posts and
        posts published by other entities across the network (copypasta detection).
        """
        entity_texts = [
            p.content_text.strip()
            for p in entity_posts
            if p.content_text and len(p.content_text.strip().split()) >= 4
        ]

        if not entity_texts:
            return 0.0

        other_texts = [
            p.content_text.strip()
            for p in all_posts
            if p.content_text
            and len(p.content_text.strip().split()) >= 4
            and (p.author_id != entity_id and p.channel_id != entity_id)
        ]

        if not other_texts:
            # If no other texts exist, check internal repetition across own posts
            if len(entity_texts) > 1:
                return self._internal_duplication_rate(entity_texts)
            return 0.0

        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=500,
            )
            all_corpus = entity_texts + other_texts
            tfidf_matrix = vectorizer.fit_transform(all_corpus)

            entity_vecs = tfidf_matrix[: len(entity_texts)]
            other_vecs = tfidf_matrix[len(entity_texts) :]

            sim_matrix = cosine_similarity(entity_vecs, other_vecs)

            # Max similarity for each entity post against any other post
            max_sims = sim_matrix.max(axis=1)

            # Fraction of posts that have high similarity (> 0.75) with other messages
            high_sim_count = sum(1 for sim in max_sims if sim >= 0.75)
            duplicate_ratio = high_sim_count / len(entity_texts)

            # Average maximum similarity score
            avg_max_sim = float(max_sims.mean())

            score = 0.5 * duplicate_ratio + 0.5 * avg_max_sim
            return round(min(1.0, max(0.0, score)), 4)

        except Exception as exc:
            logger.debug("TF-IDF duplicate content exception: %s", exc)
            return 0.0

    @staticmethod
    def _internal_duplication_rate(texts: list[str]) -> float:
        """Measure self-duplication (spammed identical text by same account)."""
        unique_texts = set(texts)
        repetition = 1.0 - (len(unique_texts) / len(texts))
        return round(float(repetition), 4)
