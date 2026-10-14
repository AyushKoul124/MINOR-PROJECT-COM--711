"""Ingestion adapters package.

Available adapters:
    BaseIngestionAdapter   Abstract interface for all platform adapters
    MessagePayload         Platform-agnostic message dataclass
    TelegramAdapter        Pyrofork MTProto adapter for Telegram public channels
"""

from ingestion_a.adapters.base import BaseIngestionAdapter, MessagePayload

__all__ = ["BaseIngestionAdapter", "MessagePayload"]
