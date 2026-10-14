"""Base adapter interface for platform-agnostic message ingestion.

All platform adapters must subclass BaseIngestionAdapter and implement:
- connect(): Authenticate and initialize client session
- disconnect(): Gracefully terminate client session
- fetch_messages(): Retrieve new messages since last checkpoint

MessagePayload is the canonical intermediate representation passed from
adapters into the storage layer, decoupling platform wire format from
our RawPost ORM model.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MessagePayload:
    """Platform-agnostic message representation.

    Immutable dataclass emitted by adapters and consumed by the
    storage upsert pipeline. All fields map 1:1 to RawPost columns.
    """

    platform: str
    platform_post_id: str
    channel_id: str
    content_text: str | None
    posted_at: datetime
    author_id: str | None = None
    content_language: str | None = None
    media_urls: list[dict[str, Any]] | None = None
    reply_to_id: str | None = None
    forward_from_id: str | None = None
    view_count: int = 0
    reaction_counts: dict[str, int] | None = field(default_factory=dict)


class BaseIngestionAdapter(abc.ABC):
    """Abstract base class for all platform ingestion adapters.

    Lifecycle:
        adapter = TelegramAdapter(...)
        await adapter.connect()
        messages = await adapter.fetch_messages(channel_id, since_message_id)
        await adapter.disconnect()
    """

    @abc.abstractmethod
    async def connect(self) -> None:
        """Authenticate and initialize the platform client session."""
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the platform client session and release resources."""
        ...

    @abc.abstractmethod
    async def fetch_messages(
        self,
        channel_id: str,
        since_message_id: int | None = None,
        limit: int = 100,
    ) -> list[MessagePayload]:
        """Fetch new messages from a channel since the last checkpoint.

        Args:
            channel_id: Platform-specific channel identifier (e.g. '@isro_updates').
            since_message_id: Fetch only messages newer than this ID. None = fetch latest batch.
            limit: Maximum number of messages to retrieve per call.

        Returns:
            List of MessagePayload objects, ordered oldest-first.
        """
        ...
