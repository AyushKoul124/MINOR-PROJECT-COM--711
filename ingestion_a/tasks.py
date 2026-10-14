"""Celery task definitions for Component A: Ingestion Agent.

Provides two primary tasks:
1. poll_all_channels: Staggered continuous polling across 30 channels
   (1 channel every 30s, ~2 req/min, pinned to --concurrency=1).
2. poll_single_channel: Poll a single channel on-demand.

Worker Launch Command:
    celery -A ingestion_a.tasks worker --loglevel=info --concurrency=1 -Q ingestion

The --concurrency=1 constraint is CRITICAL: it ensures sequential
Telegram API access, preventing concurrent requests that would
trigger FloodWaitError.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

import yaml
from celery import Celery
from dotenv import load_dotenv
from sqlalchemy import text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from storage.database import SyncSessionLocal
from storage.models.raw import IngestionRun, MonitoredChannel, RawPost

load_dotenv()

logger = logging.getLogger("ingestion_a.tasks")

# ─── Celery App Configuration ────────────────────────────────────────────────
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery("ingestion_a")
app.conf.update(
    broker_url=BROKER_URL,
    result_backend=RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # One task at a time for rate-limit safety
    task_default_queue="ingestion",
    task_routes={
        "ingestion_a.tasks.poll_all_channels": {"queue": "ingestion"},
        "ingestion_a.tasks.poll_single_channel": {"queue": "ingestion"},
    },
    beat_schedule={
        # 20-minute cycle: 30 channels * ~33.5s (30s delay + 2-5s jitter) = ~16.8 min,
        # leaving a 3.2-minute safety buffer before the next cycle to prevent backlog queueing.
        "poll-telegram-channels-every-20-min": {
            "task": "ingestion_a.tasks.poll_all_channels",
            "schedule": 1200.0,
        },
    },
)


def _load_channel_identifiers() -> list[str]:
    """Load channel identifiers from config/channels.yaml.

    Returns:
        List of channel identifier strings (e.g. ['@isro_updates', ...]).
    """
    config_path = os.getenv("CHANNELS_CONFIG_PATH", "config/channels.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        channels = config.get("channels", [])
        return [ch["identifier"] for ch in channels if ch.get("identifier")]
    except FileNotFoundError:
        logger.error("Channel config not found at: %s", config_path)
        return []
    except Exception as exc:
        logger.error("Failed to load channel config: %s", exc)
        return []


def _get_channel_checkpoint(session, channel_id: str) -> int | None:
    """Get the last polled message ID for a channel from the database.

    Returns:
        Last polled message ID, or None if channel hasn't been polled.
    """
    result = session.execute(
        text(
            "SELECT last_polled_message_id FROM monitored_channels "
            "WHERE identifier = :channel_id AND is_active = true"
        ),
        {"channel_id": channel_id},
    )
    row = result.fetchone()
    return row[0] if row else None


def _update_channel_checkpoint(
    session, channel_id: str, last_message_id: int
) -> None:
    """Update the polling checkpoint for a channel after successful fetch."""
    session.execute(
        update(MonitoredChannel)
        .where(MonitoredChannel.identifier == channel_id)
        .values(
            last_polled_message_id=last_message_id,
            last_polled_at=datetime.now(timezone.utc),
        )
    )


def _upsert_messages(session, messages: list[dict], run_id: uuid.UUID) -> int:
    """Upsert fetched messages into raw_posts table.

    Uses INSERT ... ON CONFLICT DO NOTHING for idempotent re-ingestion.

    Returns:
        Number of new messages inserted.
    """
    inserted = 0
    for msg in messages:
        stmt = pg_insert(RawPost).values(
            platform=msg["platform"],
            platform_post_id=msg["platform_post_id"],
            channel_id=msg["channel_id"],
            author_id=msg.get("author_id"),
            content_text=msg.get("content_text"),
            content_language=msg.get("content_language"),
            media_urls=msg.get("media_urls"),
            reply_to_id=msg.get("reply_to_id"),
            forward_from_id=msg.get("forward_from_id"),
            view_count=msg.get("view_count", 0),
            reaction_counts=msg.get("reaction_counts"),
            ingested_at=datetime.now(timezone.utc),
            posted_at=msg["posted_at"],
            ingestion_run_id=run_id,
            processing_status="pending",
        ).on_conflict_do_nothing(
            constraint="uq_raw_posts_platform_post_id"
        )
        result = session.execute(stmt)
        if result.rowcount > 0:
            inserted += 1
    return inserted


def _run_async(coro):
    """Run an async coroutine from synchronous Celery task context.

    Creates a new event loop since Celery workers don't have one running.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _poll_channel_async(channel_id: str, since_id: int | None) -> list[dict]:
    """Async helper: connect to Telegram, fetch messages, disconnect.

    Returns list of message dicts (serializable for Celery JSON).
    """
    from ingestion_a.adapters.telegram import TelegramAdapter

    adapter = TelegramAdapter()
    try:
        await adapter.connect()
        payloads = await adapter.fetch_messages(
            channel_id=channel_id,
            since_message_id=since_id,
            limit=100,
        )
        # Convert MessagePayload dataclasses to dicts for JSON serialization
        return [
            {
                "platform": p.platform,
                "platform_post_id": p.platform_post_id,
                "channel_id": p.channel_id,
                "content_text": p.content_text,
                "posted_at": p.posted_at.isoformat(),
                "author_id": p.author_id,
                "content_language": p.content_language,
                "media_urls": p.media_urls,
                "reply_to_id": p.reply_to_id,
                "forward_from_id": p.forward_from_id,
                "view_count": p.view_count,
                "reaction_counts": p.reaction_counts,
            }
            for p in payloads
        ]
    finally:
        await adapter.disconnect()


@app.task(bind=True, name="ingestion_a.tasks.poll_single_channel", max_retries=2)
def poll_single_channel(self, channel_id: str) -> dict:
    """Poll a single Telegram channel for new messages.

    Fetches messages since the last checkpoint, upserts into raw_posts,
    and updates the channel checkpoint.

    Args:
        channel_id: Channel identifier (e.g. '@isro_updates').

    Returns:
        Dict with channel_id, messages_fetched, messages_inserted counts.
    """
    session = SyncSessionLocal()
    try:
        # Get last checkpoint
        since_id = _get_channel_checkpoint(session, channel_id)
        logger.info("Polling %s (since_id=%s)", channel_id, since_id)

        # Fetch messages via async Telegram adapter
        messages = _run_async(_poll_channel_async(channel_id, since_id))

        if not messages:
            logger.info("No new messages from %s", channel_id)
            return {
                "channel_id": channel_id,
                "messages_fetched": 0,
                "messages_inserted": 0,
            }

        # Parse ISO timestamps back to datetime for DB insertion
        for msg in messages:
            if isinstance(msg["posted_at"], str):
                msg["posted_at"] = datetime.fromisoformat(msg["posted_at"])

        # Create ingestion run
        run_id = uuid.uuid4()
        session.execute(
            pg_insert(IngestionRun).values(
                id=run_id,
                started_at=datetime.now(timezone.utc),
                platform="telegram",
                channel_ids=[channel_id],
                posts_collected=0,
                status="running",
            )
        )

        # Upsert messages
        inserted = _upsert_messages(session, messages, run_id)

        # Update checkpoint to highest message ID
        if messages:
            # Extract numeric part from platform_post_id (format: "@channel_12345")
            max_msg_id = max(
                int(m["platform_post_id"].rsplit("_", 1)[-1])
                for m in messages
                if m["platform_post_id"].rsplit("_", 1)[-1].isdigit()
            )
            _update_channel_checkpoint(session, channel_id, max_msg_id)

        # Finalize ingestion run
        session.execute(
            update(IngestionRun)
            .where(IngestionRun.id == run_id)
            .values(
                posts_collected=inserted,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
        )

        session.commit()
        logger.info(
            "Polled %s: %d fetched, %d inserted.",
            channel_id,
            len(messages),
            inserted,
        )

        return {
            "channel_id": channel_id,
            "messages_fetched": len(messages),
            "messages_inserted": inserted,
        }

    except Exception as exc:
        session.rollback()
        logger.error("Failed polling %s: %s", channel_id, exc, exc_info=True)
        raise self.retry(exc=exc, countdown=60)
    finally:
        session.close()


@app.task(bind=True, name="ingestion_a.tasks.poll_all_channels")
def poll_all_channels(self) -> dict:
    """Staggered polling of all 30 monitored channels.

    Iterates through channels sequentially with a 30s (+jitter) delay
    between each, completing a full cycle in ~15 minutes.

    This task is designed to be run as a periodic task via Celery Beat
    or triggered manually. The --concurrency=1 worker constraint
    ensures only one polling cycle runs at a time.

    Returns:
        Dict with total channels polled, messages fetched/inserted.
    """
    import time

    from ingestion_a.adapters.telegram import TelegramAdapter

    channels = _load_channel_identifiers()
    if not channels:
        logger.error("No channels loaded from config. Aborting poll cycle.")
        return {"error": "No channels configured"}

    adapter = TelegramAdapter()
    total_fetched = 0
    total_inserted = 0
    errors: list[str] = []

    logger.info("═" * 60)
    logger.info("Starting poll cycle for %d channels", len(channels))
    logger.info("═" * 60)

    for idx, channel_id in enumerate(channels, 1):
        try:
            result = poll_single_channel.apply(args=[channel_id])
            if result.successful():
                data = result.result
                total_fetched += data.get("messages_fetched", 0)
                total_inserted += data.get("messages_inserted", 0)
                logger.info(
                    "[%d/%d] %s → %d new",
                    idx,
                    len(channels),
                    channel_id,
                    data.get("messages_inserted", 0),
                )
            else:
                errors.append(f"{channel_id}: task failed")
                logger.warning("[%d/%d] %s → FAILED", idx, len(channels), channel_id)

        except Exception as exc:
            errors.append(f"{channel_id}: {str(exc)[:100]}")
            logger.error("[%d/%d] %s → ERROR: %s", idx, len(channels), channel_id, exc)

        # Staggered delay between channels (skip after last channel)
        if idx < len(channels):
            delay = adapter.get_jittered_delay()
            logger.debug("Sleeping %.1fs before next channel...", delay)
            time.sleep(delay)

    summary = {
        "channels_polled": len(channels),
        "total_fetched": total_fetched,
        "total_inserted": total_inserted,
        "errors": errors,
        "cycle_completed_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("═" * 60)
    logger.info(
        "Poll cycle complete: %d channels, %d fetched, %d inserted, %d errors",
        len(channels),
        total_fetched,
        total_inserted,
        len(errors),
    )
    logger.info("═" * 60)

    return summary
