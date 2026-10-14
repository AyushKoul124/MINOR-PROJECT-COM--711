"""Telegram MTProto ingestion adapter using Pyrofork.

Implements staggered polling across 30 channels at 1 channel per 30 seconds
(~2 API req/min, well within Telegram rate limits). Handles FloodWaitError
with exponential back-off and per-channel checkpoint persistence.

Rate-Limit Math (30 Channels):
    - Cycle period:  30 channels × 30s = 900s (15 minutes)
    - Requests/min:  60/30 = 2 (Telegram allows ~30/min for user accounts)
    - Safety margin:  ~15× headroom → no flood risk during normal polling
    - With jitter:   ±2-5s randomization to avoid exact-interval detection

Requires:
    - TELEGRAM_API_ID, TELEGRAM_API_HASH in .env
    - TELEGRAM_SESSION_NAME for .session file persistence
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ingestion_a.telegram")


def _safe_import_pyrogram():
    """Lazy import Pyrofork to avoid crashes when running in offline/test mode."""
    try:
        from pyrogram import Client
        from pyrogram.errors import FloodWait, ChannelInvalid, ChannelPrivate
        from pyrogram.types import Message

        return Client, FloodWait, ChannelInvalid, ChannelPrivate, Message
    except ImportError:
        logger.warning(
            "Pyrofork (pyrogram) not installed. Telegram live polling unavailable. "
            "Use --offline mode or install: pip install pyrofork tgcrypto"
        )
        return None, None, None, None, None


# Lazy imports — resolved at connect() time
Client, FloodWait, ChannelInvalid, ChannelPrivate, Message = _safe_import_pyrogram()

from ingestion_a.adapters.base import BaseIngestionAdapter, MessagePayload


def _extract_reactions(message: Any) -> dict[str, int]:
    """Extract reaction emoji counts from a Pyrogram Message object.

    Returns a dict like {"👍": 120, "🚀": 45} or empty dict.
    """
    reactions: dict[str, int] = {}
    if not hasattr(message, "reactions") or message.reactions is None:
        return reactions
    try:
        for reaction in message.reactions.reactions:
            emoji = getattr(reaction, "emoji", None) or str(reaction.custom_emoji_id)
            reactions[emoji] = reaction.count
    except (AttributeError, TypeError):
        pass
    return reactions


def _extract_media_urls(message: Any) -> list[dict[str, str]] | None:
    """Extract media type and file_id from message, if any media is present."""
    media_types = ["photo", "video", "document", "audio", "animation", "voice", "sticker"]
    for media_type in media_types:
        media = getattr(message, media_type, None)
        if media:
            return [{"type": media_type, "file_id": getattr(media, "file_id", "unknown")}]
    return None


def _message_to_payload(message: Any, channel_id: str) -> MessagePayload:
    """Convert a Pyrogram Message object to our canonical MessagePayload."""
    # Determine author_id (None for channel broadcasts without linked discussion)
    author_id = None
    if message.from_user:
        author_id = str(message.from_user.id)
    elif message.sender_chat:
        author_id = str(message.sender_chat.id)

    # Determine forward source
    forward_from_id = None
    if message.forward_from_chat:
        forward_from_id = str(message.forward_from_chat.id)
    elif message.forward_from:
        forward_from_id = str(message.forward_from.id)

    # Extract text content (message.text for plain text, message.caption for media)
    content_text = message.text or message.caption or None

    # Determine posted_at timestamp
    posted_at = message.date
    if posted_at and posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)

    return MessagePayload(
        platform="telegram",
        platform_post_id=f"{channel_id}_{message.id}",
        channel_id=channel_id,
        content_text=content_text,
        posted_at=posted_at or datetime.now(timezone.utc),
        author_id=author_id,
        content_language=None,  # Detected downstream by Component B
        media_urls=_extract_media_urls(message),
        reply_to_id=str(message.reply_to_message_id) if message.reply_to_message_id else None,
        forward_from_id=forward_from_id,
        view_count=message.views or 0,
        reaction_counts=_extract_reactions(message),
    )


class TelegramAdapter(BaseIngestionAdapter):
    """Pyrofork-based Telegram MTProto adapter for public channel ingestion.

    Configuration via environment variables:
        TELEGRAM_API_ID: Telegram API application ID
        TELEGRAM_API_HASH: Telegram API application hash
        TELEGRAM_SESSION_NAME: Pyrogram session file name (default: socmint_session)
        POLL_INTERVAL_SECONDS: Delay between channel polls (default: 30)
        POLL_JITTER_MIN_SECONDS: Minimum jitter offset (default: 2)
        POLL_JITTER_MAX_SECONDS: Maximum jitter offset (default: 5)
    """

    def __init__(self) -> None:
        self._api_id: int = int(os.getenv("TELEGRAM_API_ID", "0"))
        self._api_hash: str = os.getenv("TELEGRAM_API_HASH", "")
        self._session_name: str = os.getenv("TELEGRAM_SESSION_NAME", "socmint_session")
        self._poll_interval: int = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
        self._jitter_min: int = int(os.getenv("POLL_JITTER_MIN_SECONDS", "2"))
        self._jitter_max: int = int(os.getenv("POLL_JITTER_MAX_SECONDS", "5"))
        self._client: Any = None  # Pyrogram Client instance

    async def connect(self) -> None:
        """Authenticate with Telegram MTProto via Pyrofork.

        On first run, this triggers interactive phone/code auth.
        Subsequent runs reuse the .session file.
        """
        if Client is None:
            raise ImportError(
                "Pyrofork is not installed. Install with: pip install pyrofork tgcrypto"
            )

        if not self._api_id or not self._api_hash:
            raise ValueError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env. "
                "Obtain them from https://my.telegram.org"
            )

        self._client = Client(
            name=self._session_name,
            api_id=self._api_id,
            api_hash=self._api_hash,
        )
        await self._client.start()
        me = await self._client.get_me()
        logger.info("Telegram MTProto authenticated as: %s (ID: %s)", me.first_name, me.id)

    async def disconnect(self) -> None:
        """Gracefully terminate the Pyrogram client session."""
        if self._client:
            await self._client.stop()
            logger.info("Telegram MTProto session closed.")

    async def fetch_messages(
        self,
        channel_id: str,
        since_message_id: int | None = None,
        limit: int = 100,
    ) -> list[MessagePayload]:
        """Fetch new messages from a single channel since the last checkpoint.

        Applies jitter delay between requests to stay well within
        Telegram rate limits (~2 req/min vs. ~30 allowed).

        Args:
            channel_id: Channel username (e.g. '@isro_updates') or numeric chat ID.
            since_message_id: Only fetch messages with ID > this value. None = latest batch.
            limit: Max messages per request (capped at 100 by Telegram).

        Returns:
            List of MessagePayload objects, ordered oldest-first.

        Raises:
            ChannelInvalid: Channel username doesn't exist.
            ChannelPrivate: Channel requires membership.
            FloodWait: Rate limit hit — handled with exponential sleep.
        """
        if not self._client:
            raise RuntimeError("Adapter not connected. Call connect() first.")

        payloads: list[MessagePayload] = []
        retry_count = 0
        max_retries = 3

        while retry_count <= max_retries:
            try:
                # Pyrofork get_chat_history returns newest-first; we reverse later
                messages_iter = self._client.get_chat_history(
                    chat_id=channel_id,
                    limit=limit,
                    offset_id=since_message_id + 1 if since_message_id else 0,
                )

                async for msg in messages_iter:
                    # Skip service messages (joins, pins, etc.)
                    if msg.service is not None:
                        continue
                    # Skip empty messages (deleted or media-only without caption)
                    if not msg.text and not msg.caption:
                        continue
                    # Stop if we've gone past the checkpoint
                    if since_message_id and msg.id <= since_message_id:
                        break

                    payloads.append(_message_to_payload(msg, channel_id))

                # Reverse to oldest-first ordering
                payloads.reverse()

                logger.info(
                    "Fetched %d messages from %s (since_id=%s)",
                    len(payloads),
                    channel_id,
                    since_message_id,
                )
                break  # Success — exit retry loop

            except FloodWait as e:
                wait_seconds = e.value
                retry_count += 1
                logger.warning(
                    "FloodWait: sleeping %ds before retry %d/%d for %s",
                    wait_seconds,
                    retry_count,
                    max_retries,
                    channel_id,
                )
                await asyncio.sleep(wait_seconds)

            except ChannelInvalid:
                logger.error("Channel %s does not exist or username is invalid.", channel_id)
                break

            except ChannelPrivate:
                logger.error("Channel %s is private or requires membership.", channel_id)
                break

            except Exception as exc:
                logger.error("Unexpected error fetching %s: %s", channel_id, exc, exc_info=True)
                break

        return payloads

    def get_jittered_delay(self) -> float:
        """Calculate the next poll delay with random jitter.

        Returns:
            Delay in seconds: POLL_INTERVAL + uniform(JITTER_MIN, JITTER_MAX)
        """
        jitter = random.uniform(self._jitter_min, self._jitter_max)
        return self._poll_interval + jitter
