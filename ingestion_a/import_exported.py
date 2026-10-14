"""Import Telegram Desktop JSON chat exports into the SOCMINT database.

Telegram Desktop (Settings → Advanced → Export Chat History) exports
channel history as a `result.json` file containing messages in a
structured JSON format. This script parses that export and inserts
messages into the raw_posts table.

Usage:
    # Import a single exported channel
    python -m ingestion_a.import_exported --import-json path/to/result.json --channel @isro_updates

    # Import with custom ingestion run label
    python -m ingestion_a.import_exported --import-json path/to/result.json --channel @drdo_updates --label "drdo_export_oct2026"

    # Dry run (count messages without inserting)
    python -m ingestion_a.import_exported --import-json path/to/result.json --channel @isro_updates --dry-run

Telegram Desktop Export JSON Schema (simplified):
    {
      "name": "Channel Name",
      "type": "public_channel",
      "id": 1234567890,
      "messages": [
        {
          "id": 12345,
          "type": "message",
          "date": "2026-10-01T12:30:00",
          "from": "User Name",
          "from_id": "user123456",
          "text": "Message content here",
          "reply_to_message_id": 12344,
          "forwarded_from": "Other Channel",
          "views": 1500,
          "media_type": "photo",
          "photo": "(File not included...)"
        },
        ...
      ]
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from storage.database import SyncSessionLocal
from storage.models.raw import IngestionRun, RawPost

logger = logging.getLogger("ingestion_a.import_exported")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def _extract_text_content(text_field) -> str | None:
    """Extract plain text from Telegram export's text field.

    The text field can be either a plain string or a list of mixed
    string/dict elements (for formatted text with bold, links, etc.).
    """
    if text_field is None:
        return None

    if isinstance(text_field, str):
        return text_field if text_field.strip() else None

    if isinstance(text_field, list):
        parts: list[str] = []
        for element in text_field:
            if isinstance(element, str):
                parts.append(element)
            elif isinstance(element, dict):
                parts.append(element.get("text", ""))
        result = "".join(parts).strip()
        return result if result else None

    return str(text_field) if text_field else None


def _parse_datetime(date_str: str) -> datetime:
    """Parse Telegram export datetime string to timezone-aware UTC datetime.

    Telegram Desktop exports dates as 'YYYY-MM-DDTHH:MM:SS' in local time
    (no timezone info). We treat them as UTC for consistency.
    """
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _parse_from_id(from_id_str: str | None) -> str | None:
    """Normalize Telegram export from_id field.

    Format is typically 'user123456' or 'channel123456'.
    """
    if not from_id_str:
        return None
    # Strip prefix to get numeric ID
    return from_id_str.replace("user", "").replace("channel", "")


def import_json_export(
    json_path: Path,
    channel_id: str,
    label: str | None = None,
    dry_run: bool = False,
) -> int:
    """Parse and import a Telegram Desktop JSON export file.

    Args:
        json_path: Path to the result.json file from Telegram Desktop export.
        channel_id: Channel identifier to assign (e.g. '@isro_updates').
        label: Optional label for the ingestion run.
        dry_run: If True, parse and count without inserting.

    Returns:
        Number of messages imported (or that would be imported in dry-run).
    """
    if not json_path.exists():
        logger.error("Export file not found: %s", json_path)
        sys.exit(1)

    logger.info("Loading export file: %s", json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            export_data = json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in export file: %s", exc)
            sys.exit(1)

    messages = export_data.get("messages", [])
    if not messages:
        logger.warning("No messages found in export file.")
        return 0

    # Filter to actual messages (skip service messages like pin, join, etc.)
    text_messages = [
        msg for msg in messages
        if msg.get("type") == "message" and _extract_text_content(msg.get("text"))
    ]

    logger.info(
        "Found %d total messages, %d with text content for channel %s",
        len(messages),
        len(text_messages),
        channel_id,
    )

    if dry_run:
        logger.info("DRY RUN: Would import %d messages. No database changes.", len(text_messages))
        return len(text_messages)

    # ─── Database Insertion ───────────────────────────────────────────────
    session = SyncSessionLocal()
    run_id = uuid.uuid4()

    try:
        # Create ingestion run record
        session.execute(
            pg_insert(IngestionRun).values(
                id=run_id,
                started_at=datetime.now(timezone.utc),
                platform="telegram",
                channel_ids=[channel_id],
                posts_collected=0,
                status="running",
                error_message=label,
            )
        )

        imported = 0
        skipped = 0

        for msg in text_messages:
            content_text = _extract_text_content(msg.get("text"))
            if not content_text:
                skipped += 1
                continue

            post_date = _parse_datetime(msg.get("date", ""))
            platform_post_id = f"{channel_id}_{msg['id']}"

            # Determine media if present
            media_urls = None
            media_type = msg.get("media_type")
            if media_type:
                media_urls = [{"type": media_type, "file_id": "desktop_export"}]

            # Determine forwarded source
            forward_from = msg.get("forwarded_from")
            forward_from_id = forward_from if forward_from else None

            stmt = pg_insert(RawPost).values(
                platform="telegram",
                platform_post_id=platform_post_id,
                channel_id=channel_id,
                author_id=_parse_from_id(msg.get("from_id")),
                content_text=content_text,
                content_language=None,  # Detected by Component B
                media_urls=media_urls,
                reply_to_id=str(msg["reply_to_message_id"]) if msg.get("reply_to_message_id") else None,
                forward_from_id=forward_from_id,
                view_count=msg.get("views", 0) or 0,
                reaction_counts=None,  # Desktop exports don't include reactions
                ingested_at=datetime.now(timezone.utc),
                posted_at=post_date,
                ingestion_run_id=run_id,
                processing_status="pending",
            ).on_conflict_do_nothing(
                constraint="uq_raw_posts_platform_post_id"
            )

            result = session.execute(stmt)
            if result.rowcount > 0:
                imported += 1
            else:
                skipped += 1

        # Finalize ingestion run
        session.execute(
            update(IngestionRun)
            .where(IngestionRun.id == run_id)
            .values(
                posts_collected=imported,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
        )

        session.commit()

        logger.info(
            "Import complete: %d inserted, %d skipped (duplicates/empty), run_id=%s",
            imported,
            skipped,
            run_id,
        )
        return imported

    except Exception as exc:
        logger.error("Import failed: %s", exc, exc_info=True)
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """CLI entry point for Telegram Desktop JSON export importer."""
    parser = argparse.ArgumentParser(
        prog="import_exported",
        description="Import Telegram Desktop JSON exports into SOCMINT raw_posts table.",
    )
    parser.add_argument(
        "--import-json",
        type=Path,
        required=True,
        help="Path to Telegram Desktop result.json export file.",
    )
    parser.add_argument(
        "--channel",
        type=str,
        required=True,
        help="Channel identifier to assign (e.g. '@isro_updates').",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional label for the ingestion run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and count messages without inserting into database.",
    )

    args = parser.parse_args()

    count = import_json_export(
        json_path=args.import_json,
        channel_id=args.channel,
        label=args.label,
        dry_run=args.dry_run,
    )

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Processed {count} messages from {args.channel}")


if __name__ == "__main__":
    main()
