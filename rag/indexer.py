"""RAG Layer — Document Indexer.

Synchronizes agent analytical outputs from Components B, C, D, and E into
the ``rag_documents`` knowledge table as 384-dimensional dense vectors.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from rag.embedder import RAGEmbedder
from storage.database import SyncSessionLocal
from storage.models.derived_b import SentimentResultB
from storage.models.derived_c import DemographicAggregateC
from storage.models.derived_d import TrendTopicD
from storage.models.derived_e import NetworkNodeE
from storage.models.rag import RAGDocument
from storage.models.raw import RawPost

logger = logging.getLogger("rag.indexer")


class RAGIndexer:
    """Extracts, summarizes, embeds, and indexes analytical results across all components."""

    def __init__(self, embedder: RAGEmbedder | None = None) -> None:
        self.embedder = embedder or RAGEmbedder()

    def index_all_components(self) -> dict[str, int]:
        """Index latest unindexed or updated records across B, C, D, and E.

        Returns:
            Dict mapping component identifier -> number of documents indexed.
        """
        logger.info("Starting knowledge indexing across Components B, C, D, E...")
        counts = {
            "B": self.index_component_b(),
            "C": self.index_component_c(),
            "D": self.index_component_d(),
            "E": self.index_component_e(),
        }
        total = sum(counts.values())
        logger.info("Indexing complete: %d total documents added to rag_documents.", total)
        return counts

    def index_component_b(self, limit: int = 50) -> int:
        """Index recent post sentiment, emotion, and stance summaries."""
        with SyncSessionLocal() as session:
            # Query posts that have sentiment results
            stmt = (
                select(RawPost, SentimentResultB)
                .join(SentimentResultB, RawPost.id == SentimentResultB.raw_post_id)
                .order_by(RawPost.posted_at.desc())
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            if not rows:
                return 0

            # Find existing indexed record IDs for component B
            existing_stmt = select(RAGDocument.source_record_id).where(
                RAGDocument.source_component == "B"
            )
            existing_ids = set(session.execute(existing_stmt).scalars().all())

            docs_to_index: list[dict[str, Any]] = []
            for post, s_res in rows:
                rec_id = str(post.id)
                if rec_id in existing_ids:
                    continue

                text_snippet = (post.content_text or "").strip()[:280]
                valence_str = (s_res.valence or "neutral").upper()
                emotion_str = (s_res.dominant_emotion or "neutral").upper()
                em_conf = s_res.emotion_confidence or 0.0
                stance_str = (s_res.stance or "neutral").upper()
                st_conf = s_res.stance_confidence or 0.0
                summary = (
                    f"[Post Sentiment Analysis] Post #{post.id} from channel '{post.channel_id}' "
                    f"at {post.posted_at.isoformat()}. "
                    f"Valence: {valence_str}. "
                    f"Dominant Emotion: {emotion_str} ({em_conf:.2f}). "
                    f"Policy Stance: {stance_str} ({st_conf:.2f}). "
                    f"Sarcasm Flag: {s_res.sarcasm_flag}. Content: \"{text_snippet}\""
                )
                docs_to_index.append({
                    "component": "B",
                    "record_id": rec_id,
                    "content": summary,
                    "window_start": post.posted_at,
                    "window_end": post.posted_at,
                })

            return self._embed_and_save(session, docs_to_index)

    def index_component_c(self) -> int:
        """Index aggregate demographic profiles."""
        with SyncSessionLocal() as session:
            stmt = (
                select(DemographicAggregateC)
                .order_by(DemographicAggregateC.analyzed_at.desc())
                .limit(20)
            )
            clusters = session.execute(stmt).scalars().all()
            if not clusters:
                return 0

            existing_stmt = select(RAGDocument.source_record_id).where(
                RAGDocument.source_component == "C"
            )
            existing_ids = set(session.execute(existing_stmt).scalars().all())

            docs_to_index: list[dict[str, Any]] = []
            for c in clusters:
                rec_id = str(c.id)
                if rec_id in existing_ids:
                    continue

                age_top = sorted(
                    (c.age_bracket_dist or {}).items(), key=lambda x: x[1], reverse=True
                )[:2]
                geo_top = sorted(
                    (c.geography_dist or {}).items(), key=lambda x: x[1], reverse=True
                )[:2]
                lang_top = sorted(
                    (c.language_dist or {}).items(), key=lambda x: x[1], reverse=True
                )[:2]
                interest_top = sorted(
                    (c.interest_dist or {}).items(), key=lambda x: x[1], reverse=True
                )[:3]

                age_str = ", ".join(f"{k}: {v*100:.1f}%" for k, v in age_top) if age_top else "Unspecified"
                geo_str = ", ".join(f"{k}: {v*100:.1f}%" for k, v in geo_top) if geo_top else "Unspecified"
                lang_str = ", ".join(f"{k}: {v*100:.1f}%" for k, v in lang_top) if lang_top else "Unspecified"
                interest_str = ", ".join(f"{k}: {v*100:.1f}%" for k, v in interest_top) if interest_top else "Unspecified"

                threshold_note = (
                    "BELOW k-anonymity threshold (<50 accounts, coarse proxy only)"
                    if c.below_threshold
                    else "Meets k-anonymity privacy threshold"
                )

                summary = (
                    f"[Audience Demographic Intelligence] Cluster '{c.cluster_label}'. "
                    f"Sample size: {c.account_count} accounts ({threshold_note}). "
                    f"Age distribution: {age_str}. Geography distribution: {geo_str}. "
                    f"Language distribution: {lang_str}. Topical interests: {interest_str}. "
                    f"Heuristic inference confidence: {c.inference_confidence:.2f}."
                )
                docs_to_index.append({
                    "component": "C",
                    "record_id": rec_id,
                    "content": summary,
                    "window_start": c.window_start,
                    "window_end": c.window_end,
                })

            return self._embed_and_save(session, docs_to_index)

    def index_component_d(self) -> int:
        """Index trending conversational topics with velocity and acceleration."""
        with SyncSessionLocal() as session:
            stmt = (
                select(TrendTopicD)
                .order_by(TrendTopicD.analyzed_at.desc())
                .limit(30)
            )
            topics = session.execute(stmt).scalars().all()
            if not topics:
                return 0

            existing_stmt = select(RAGDocument.source_record_id).where(
                RAGDocument.source_component == "D"
            )
            existing_ids = set(session.execute(existing_stmt).scalars().all())

            docs_to_index: list[dict[str, Any]] = []
            for t in topics:
                rec_id = str(t.id)
                if rec_id in existing_ids:
                    continue

                kws = ", ".join(t.topic_keywords or []) if t.topic_keywords else "None"
                status = "SURGING (accelerating)" if t.acceleration > 0 else "COOLING"

                summary = (
                    f"[Emergent Trend Topic #{t.rank}] Theme: '{t.topic_label}'. "
                    f"Status: {status}. Total posts in window: {t.post_count}. "
                    f"Hourly publication velocity: {t.velocity:.4f} posts/hour. "
                    f"Hourly acceleration: {t.acceleration:.4f}. Key terms: {kws}."
                )
                docs_to_index.append({
                    "component": "D",
                    "record_id": rec_id,
                    "content": summary,
                    "window_start": t.window_start,
                    "window_end": t.window_end,
                })

            return self._embed_and_save(session, docs_to_index)

    def index_component_e(self) -> int:
        """Index network nodes, Louvain community bridges, and CIB screening signals."""
        with SyncSessionLocal() as session:
            stmt = (
                select(NetworkNodeE)
                .order_by(NetworkNodeE.betweenness_centrality.desc())
                .limit(40)
            )
            nodes = session.execute(stmt).scalars().all()
            if not nodes:
                return 0

            existing_stmt = select(RAGDocument.source_record_id).where(
                RAGDocument.source_component == "E"
            )
            existing_ids = set(session.execute(existing_stmt).scalars().all())

            docs_to_index: list[dict[str, Any]] = []
            for n in nodes:
                rec_id = str(n.id)
                if rec_id in existing_ids:
                    continue

                cib_status = (
                    f"FLAGGED for coordination anomaly (score: {n.anomaly_score:.2f} >= 0.70)"
                    if n.coordination_signal
                    else f"Within baseline (score: {n.anomaly_score:.2f})"
                )

                summary = (
                    f"[Network Interaction & CIB Screening] Entity '{n.label}' ({n.entity_type}). "
                    f"Louvain Community #{n.community_id}. "
                    f"Betweenness Centrality: {n.betweenness_centrality:.4f} (structural broker metric). "
                    f"Degree Centrality: {n.degree_centrality:.4f}. "
                    f"Advisory CIB Status: {cib_status} (posting synchrony: {n.posting_synchrony_signal:.2f}, "
                    f"age-volume incongruity: {n.age_volume_signal:.2f}, duplicate content: {n.duplicate_content_signal:.2f})."
                )
                docs_to_index.append({
                    "component": "E",
                    "record_id": rec_id,
                    "content": summary,
                    "window_start": n.window_start,
                    "window_end": n.window_end,
                })

            return self._embed_and_save(session, docs_to_index)

    def _embed_and_save(self, session: Any, items: list[dict[str, Any]]) -> int:
        """Embed document texts and persist to rag_documents."""
        if not items:
            return 0

        texts = [item["content"] for item in items]
        embeddings = self.embedder.embed_batch(texts)

        for item, emb in zip(items, embeddings):
            stmt = pg_insert(RAGDocument).values(
                source_component=item["component"],
                source_record_id=item["record_id"],
                content_text=item["content"],
                embedding=emb,
                window_start=item["window_start"],
                window_end=item["window_end"],
                created_at=datetime.now(timezone.utc),
            )
            session.execute(stmt)

        session.commit()
        logger.info("Persisted %d documents to rag_documents.", len(items))
        return len(items)
