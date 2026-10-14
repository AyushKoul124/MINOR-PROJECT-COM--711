"""Component B — Sequential Pipeline Orchestrator.

Runs the 3-model sentiment analysis pipeline in strict sequential order to
honour the 4 GB VRAM budget on GTX 1650 Ti:

    1. SentimentClassifier  (XLM-RoBERTa, ~1.1 GB)
       → torch.cuda.empty_cache()
    2. EmotionClassifier    (RoBERTa GoEmotions, ~500 MB)
       → torch.cuda.empty_cache()
    3. StanceDetector       (DistilBART MNLI, ~700 MB)
       → torch.cuda.empty_cache()
    4. SarcasmDetector      (rule-based, no GPU)

Results are written to the ``sentiment_results_b`` table via SQLAlchemy.

Usage from the orchestrator::

    from sentiment_b.pipeline import SentimentPipeline
    pipeline = SentimentPipeline()
    processed = pipeline.process_posts(post_ids=[1, 2, 3])

Usage for the "Run Analysis Now" demo trigger::

    from sentiment_b.pipeline import SentimentPipeline
    pipeline = SentimentPipeline()
    processed = pipeline.process_pending(limit=50)  # ≤50 posts in 15-25s
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import yaml
from sqlalchemy import text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from sentiment_b.emotion import EmotionClassifier
from sentiment_b.sarcasm import SarcasmDetector
from sentiment_b.sentiment import SentimentClassifier
from sentiment_b.stance import StanceDetector
from storage.database import SyncSessionLocal
from storage.models.derived_b import SentimentResultB
from storage.models.raw import RawPost

logger = logging.getLogger("sentiment_b.pipeline")


def _load_channel_topics() -> dict[str, list[str]]:
    """Load channel topic_tags from config/channels.yaml.

    Returns:
        Dict mapping channel identifier → list of topic tag strings.
    """
    try:
        with open("config/channels.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        channels = config.get("channels", [])
        return {
            ch["identifier"]: ch.get("topic_tags", [])
            for ch in channels
            if ch.get("identifier")
        }
    except Exception as exc:
        logger.warning("Could not load channel topics: %s (using defaults)", exc)
        return {}


class SentimentPipeline:
    """Sequential 3-model + sarcasm heuristic pipeline for Component B.

    Enforces the 4 GB VRAM invariant by loading/unloading models one at a
    time with explicit ``torch.cuda.empty_cache()`` between transitions.

    Attributes:
        device: Target device string ("cuda" or "cpu").
    """

    def __init__(self, device: str | None = None) -> None:
        import torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._channel_topics = _load_channel_topics()
        self._sarcasm_detector = SarcasmDetector()
        logger.info(
            "SentimentPipeline initialised (device=%s, %d channel topic mappings).",
            self.device,
            len(self._channel_topics),
        )

    def _get_channel_topics(self, channel_id: str) -> list[str]:
        """Retrieve topic tags for a channel, falling back to empty list."""
        return self._channel_topics.get(channel_id, [])

    # ── Core Processing ──────────────────────────────────────────────────
    def analyze_text(
        self,
        text: str,
        channel_id: str | None = None,
        content_language: str = "en",
    ) -> dict:
        """Run the full pipeline on a single text string.

        This method loads each model sequentially, performs inference, then
        unloads before moving to the next model.

        Args:
            text: Raw post text.
            channel_id: Optional channel identifier for topic-aware stance.
            content_language: ISO language code for the post.

        Returns:
            Dict with all SentimentResultB column values.
        """
        t0 = time.perf_counter()

        # ── Step 1: Sentiment (valence) ──────────────────────────────────
        sentiment_clf = SentimentClassifier(device=self.device)
        sentiment_result = sentiment_clf.predict(text)
        sentiment_clf.unload()
        logger.debug(
            "Sentiment: %s (%.3f) in %.2fs",
            sentiment_result.valence,
            sentiment_result.confidence,
            time.perf_counter() - t0,
        )

        # ── Step 2: Emotion (Ekman 6 + neutral) ─────────────────────────
        t1 = time.perf_counter()
        emotion_clf = EmotionClassifier(device=self.device)
        emotion_result = emotion_clf.predict(text)
        emotion_clf.unload()
        logger.debug(
            "Emotion: %s (%.3f) in %.2fs",
            emotion_result.dominant_emotion,
            emotion_result.emotion_confidence,
            time.perf_counter() - t1,
        )

        # ── Step 3: Stance (zero-shot NLI) ───────────────────────────────
        t2 = time.perf_counter()
        channel_topics = self._get_channel_topics(channel_id) if channel_id else []
        stance_detector = StanceDetector(device=self.device)
        stance_result = stance_detector.predict(text, channel_topics=channel_topics)
        stance_detector.unload()
        logger.debug(
            "Stance: %s (%.3f) re '%s' in %.2fs",
            stance_result.stance,
            stance_result.confidence,
            stance_result.topic_evaluated,
            time.perf_counter() - t2,
        )

        # ── Step 4: Sarcasm heuristic (no model, instant) ───────────────
        sarcasm_flag = self._sarcasm_detector.check(text, sentiment_result.valence)

        elapsed = time.perf_counter() - t0
        logger.info(
            "Pipeline complete: valence=%s, emotion=%s, stance=%s, sarcasm=%s (%.2fs total)",
            sentiment_result.valence,
            emotion_result.dominant_emotion,
            stance_result.stance,
            sarcasm_flag,
            elapsed,
        )

        return {
            "content_language": content_language or "en",
            "dominant_emotion": emotion_result.dominant_emotion,
            "emotion_confidence": emotion_result.emotion_confidence,
            "emotion_joy": emotion_result.emotion_joy,
            "emotion_anger": emotion_result.emotion_anger,
            "emotion_sadness": emotion_result.emotion_sadness,
            "emotion_disgust": emotion_result.emotion_disgust,
            "emotion_surprise": emotion_result.emotion_surprise,
            "emotion_neutral": emotion_result.emotion_neutral,
            "emotion_fear": emotion_result.emotion_fear,
            "stance": stance_result.stance,
            "stance_confidence": stance_result.confidence,
            "sarcasm_flag": sarcasm_flag,
            "valence": sentiment_result.valence,
        }

    # ── Batch Processing with Warm Models ────────────────────────────────
    def analyze_batch(
        self,
        texts: list[str],
        channel_ids: list[str | None] | None = None,
        content_languages: list[str] | None = None,
    ) -> list[dict]:
        """Run the full pipeline on a batch of texts.

        More efficient than calling :meth:`analyze_text` in a loop because
        each model is loaded once for the entire batch, then unloaded.

        Args:
            texts: List of raw post texts.
            channel_ids: Optional channel identifiers per post.
            content_languages: Optional language codes per post.

        Returns:
            List of dicts with all SentimentResultB column values.
        """
        n = len(texts)
        if not channel_ids:
            channel_ids = [None] * n
        if not content_languages:
            content_languages = ["en"] * n

        t0 = time.perf_counter()
        logger.info("Starting batch pipeline for %d posts...", n)

        # ── Step 1: Batch Sentiment ──────────────────────────────────────
        sentiment_clf = SentimentClassifier(device=self.device)
        sentiment_results = sentiment_clf.predict_batch(texts)
        sentiment_clf.unload()
        logger.info("Batch sentiment complete (%.2fs).", time.perf_counter() - t0)

        # ── Step 2: Batch Emotion ────────────────────────────────────────
        t1 = time.perf_counter()
        emotion_clf = EmotionClassifier(device=self.device)
        emotion_results = emotion_clf.predict_batch(texts)
        emotion_clf.unload()
        logger.info("Batch emotion complete (%.2fs).", time.perf_counter() - t1)

        # ── Step 3: Stance (per-post, requires per-channel topic) ────────
        t2 = time.perf_counter()
        stance_detector = StanceDetector(device=self.device)
        stance_results = []
        for text_item, ch_id in zip(texts, channel_ids):
            ch_topics = self._get_channel_topics(ch_id) if ch_id else []
            stance_results.append(
                stance_detector.predict(text_item, channel_topics=ch_topics)
            )
        stance_detector.unload()
        logger.info("Batch stance complete (%.2fs).", time.perf_counter() - t2)

        # ── Step 4: Sarcasm (instant, no model) ──────────────────────────
        sarcasm_flags = [
            self._sarcasm_detector.check(text_item, sr.valence)
            for text_item, sr in zip(texts, sentiment_results)
        ]

        elapsed = time.perf_counter() - t0
        logger.info("Batch pipeline complete: %d posts in %.2fs.", n, elapsed)

        # Assemble results
        results = []
        for i in range(n):
            results.append({
                "content_language": content_languages[i] or "en",
                "dominant_emotion": emotion_results[i].dominant_emotion,
                "emotion_confidence": emotion_results[i].emotion_confidence,
                "emotion_joy": emotion_results[i].emotion_joy,
                "emotion_anger": emotion_results[i].emotion_anger,
                "emotion_sadness": emotion_results[i].emotion_sadness,
                "emotion_disgust": emotion_results[i].emotion_disgust,
                "emotion_surprise": emotion_results[i].emotion_surprise,
                "emotion_neutral": emotion_results[i].emotion_neutral,
                "emotion_fear": emotion_results[i].emotion_fear,
                "stance": stance_results[i].stance,
                "stance_confidence": stance_results[i].confidence,
                "sarcasm_flag": sarcasm_flags[i],
                "valence": sentiment_results[i].valence,
            })

        return results

    # ── Database-Integrated Processing ───────────────────────────────────
    def process_pending(self, limit: int = 50) -> dict:
        """Fetch pending raw_posts, run the pipeline, and write results to DB.

        This is the primary entry point for the orchestrator's row-level runner
        and the "Run Analysis Now" demo trigger.

        Args:
            limit: Maximum number of posts to process (default 50 for demo).

        Returns:
            Summary dict with counts and timing.
        """
        t0 = time.perf_counter()
        session = SyncSessionLocal()

        try:
            # Fetch pending posts
            pending_posts = (
                session.query(RawPost)
                .filter(RawPost.processing_status == "pending")
                .filter(RawPost.content_text.isnot(None))
                .filter(RawPost.content_text != "")
                .order_by(RawPost.id.asc())
                .limit(limit)
                .all()
            )

            if not pending_posts:
                logger.info("No pending posts to process.")
                return {"processed": 0, "elapsed_seconds": 0.0}

            logger.info("Processing %d pending posts...", len(pending_posts))

            # Extract data for batch processing
            texts = [p.content_text for p in pending_posts]
            channel_ids = [p.channel_id for p in pending_posts]
            content_languages = [p.content_language or "en" for p in pending_posts]

            # Run batch pipeline
            results = self.analyze_batch(texts, channel_ids, content_languages)

            # Write results to sentiment_results_b
            for post, result in zip(pending_posts, results):
                stmt = pg_insert(SentimentResultB).values(
                    raw_post_id=post.id,
                    **result,
                    analyzed_at=datetime.now(timezone.utc),
                ).on_conflict_do_update(
                    index_elements=["raw_post_id"],
                    set_=result,
                )
                session.execute(stmt)

                # Mark post as processed
                session.execute(
                    update(RawPost)
                    .where(RawPost.id == post.id)
                    .values(processing_status="processed")
                )

            session.commit()

            elapsed = time.perf_counter() - t0
            logger.info(
                "═" * 60 + "\n"
                "Component B pipeline complete: %d posts in %.2fs (%.2f posts/sec)\n"
                + "═" * 60,
                len(pending_posts),
                elapsed,
                len(pending_posts) / elapsed if elapsed > 0 else 0,
            )

            return {
                "processed": len(pending_posts),
                "elapsed_seconds": round(elapsed, 2),
                "posts_per_second": round(len(pending_posts) / elapsed, 2) if elapsed > 0 else 0,
            }

        except Exception as exc:
            session.rollback()
            logger.error("Pipeline failed: %s", exc, exc_info=True)
            raise
        finally:
            session.close()

    def process_posts(self, post_ids: list[int]) -> dict:
        """Process specific raw_posts by ID.

        Args:
            post_ids: List of raw_posts.id values to process.

        Returns:
            Summary dict with counts and timing.
        """
        t0 = time.perf_counter()
        session = SyncSessionLocal()

        try:
            posts = (
                session.query(RawPost)
                .filter(RawPost.id.in_(post_ids))
                .filter(RawPost.content_text.isnot(None))
                .filter(RawPost.content_text != "")
                .all()
            )

            if not posts:
                logger.info("No valid posts found for IDs: %s", post_ids)
                return {"processed": 0, "elapsed_seconds": 0.0}

            texts = [p.content_text for p in posts]
            channel_ids = [p.channel_id for p in posts]
            content_languages = [p.content_language or "en" for p in posts]

            results = self.analyze_batch(texts, channel_ids, content_languages)

            for post, result in zip(posts, results):
                stmt = pg_insert(SentimentResultB).values(
                    raw_post_id=post.id,
                    **result,
                    analyzed_at=datetime.now(timezone.utc),
                ).on_conflict_do_update(
                    index_elements=["raw_post_id"],
                    set_=result,
                )
                session.execute(stmt)

                session.execute(
                    update(RawPost)
                    .where(RawPost.id == post.id)
                    .values(processing_status="processed")
                )

            session.commit()

            elapsed = time.perf_counter() - t0
            logger.info(
                "Processed %d specific posts in %.2fs.",
                len(posts),
                elapsed,
            )

            return {
                "processed": len(posts),
                "elapsed_seconds": round(elapsed, 2),
            }

        except Exception as exc:
            session.rollback()
            logger.error("Pipeline failed for post_ids %s: %s", post_ids, exc, exc_info=True)
            raise
        finally:
            session.close()
