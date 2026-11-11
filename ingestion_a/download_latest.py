"""Download the latest posts and photos from every Telegram channel and group.

Uses the saved Pyrofork session (socmint_session). Private one-to-one chats
are skipped. Photos are written under ``Telegram Desktop/<channel>/photos``.
Existing posts keep their text and processing status; a matching message
only gains its picture path and reaction counts.

    python -m ingestion_a.download_latest
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ingestion_a.import_exported import _ensure_monitored_channel, _slugify_channel_name
from ingestion_a.topics import is_middle_east, is_project_related, middle_east_rank
from storage.database import SyncSessionLocal
from storage.models.raw import IngestionRun, RawPost

load_dotenv()

logger = logging.getLogger("ingestion_a.download_latest")

ROOT = Path(__file__).resolve().parents[1]
EXPORT_ROOT = ROOT / "Telegram Desktop"
MAX_MESSAGES = 80
KEEP_TYPES = {ChatType.CHANNEL, ChatType.SUPERGROUP, ChatType.GROUP}


def _safe_dir(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    return (cleaned or "channel")[:80]


def _reactions(message) -> dict[str, int] | None:
    counts: dict[str, int] = {}
    reactions = getattr(message, "reactions", None)
    if reactions is None:
        return None
    try:
        for reaction in reactions.reactions:
            emoji = getattr(reaction, "emoji", None) or str(getattr(reaction, "custom_emoji_id", ""))
            if emoji:
                counts[str(emoji)] = int(reaction.count)
    except (AttributeError, TypeError, ValueError):
        return None
    return counts or None


async def _download_photo(message, folder: Path) -> str | None:
    if message.photo is None:
        return None
    photos = folder / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    dest = photos / f"{message.id}.jpg"
    if not dest.exists():
        await message.download(file_name=str(dest))
    relative = dest.relative_to(ROOT).as_posix()
    return relative


def _store(channel_id: str, channel_name: str, rows: list[dict]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    session = SyncSessionLocal()
    run_id = uuid.uuid4()
    inserted = 0
    try:
        _ensure_monitored_channel(session, channel_id, channel_name)
        session.execute(
            pg_insert(IngestionRun).values(
                id=run_id,
                started_at=datetime.now(timezone.utc),
                platform="telegram",
                channel_ids=[channel_id],
                posts_collected=0,
                status="running",
                error_message=f"Live photo download for {channel_name}",
            )
        )
        for row in rows:
            stmt = pg_insert(RawPost).values(**row, ingestion_run_id=run_id)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_raw_posts_platform_post_id",
                set_={
                    "media_urls": stmt.excluded.media_urls,
                    "reaction_counts": stmt.excluded.reaction_counts,
                    "view_count": stmt.excluded.view_count,
                },
            )
            result = session.execute(stmt)
            if result.rowcount:
                inserted += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return len(rows), inserted


def _row(channel_id: str, message, photo_path: str | None) -> dict:
    text = message.text or message.caption or ""
    posted_at = message.date
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    author_id = None
    if message.from_user:
        author_id = str(message.from_user.id)
    elif message.sender_chat:
        author_id = str(message.sender_chat.id)
    media = [{"type": "photo", "path": photo_path}] if photo_path else None
    return {
        "platform": "telegram",
        "platform_post_id": f"{channel_id}_{message.id}",
        "channel_id": channel_id,
        "author_id": author_id or channel_id,
        "content_text": text or None,
        "content_language": None,
        "media_urls": media,
        "reply_to_id": str(message.reply_to_message_id) if message.reply_to_message_id else None,
        "forward_from_id": None,
        "view_count": message.views or 0,
        "reaction_counts": _reactions(message),
        "ingested_at": datetime.now(timezone.utc),
        "posted_at": posted_at,
        "processing_status": "pending",
    }


async def _pull_chat(app: Client, chat, limit: int) -> None:
    title = chat.title or getattr(chat, "first_name", None) or str(chat.id)
    channel_id = _slugify_channel_name(title)
    folder = EXPORT_ROOT / _safe_dir(title)
    folder.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    photos = 0
    seen = 0
    offset_id = 0
    pulled = 0
    target = limit if limit > 0 else (1 << 31) - 1

    def flush() -> None:
        nonlocal rows, seen
        if not rows:
            return
        stored, _written = _store(channel_id, title, rows)
        seen += stored
        rows = []
        print(f"saved {title} | posts {seen} | photos {photos}", flush=True)

    while pulled < target:
        try:
            page = min(80, target - pulled)
            async for message in app.get_chat_history(chat.id, limit=page, offset_id=offset_id):
                offset_id = message.id
                pulled += 1
                if message.service:
                    continue
                text = message.text or message.caption or ""
                photo_path = await _download_photo(message, folder)
                if not text and not photo_path:
                    continue
                if photo_path:
                    photos += 1
                rows.append(_row(channel_id, message, photo_path))
                if len(rows) >= 40:
                    flush()
                if pulled >= target:
                    break
            break
        except FloodWait as wait:
            flush()
            logger.warning("Flood wait %ss on %s", wait.value, title)
            print(f"wait {wait.value}s {title}", flush=True)
            await asyncio.sleep(wait.value + 1)

    flush()
    print(f"chat {title} | posts {seen} | photos {photos}", flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Download recent public Telegram posts and photos.")
    parser.add_argument(
        "--middle-east",
        action="store_true",
        help="Download Middle East chats first, including Mediterranean Man and Middle East Spectator, with no 80-message cap.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    app = Client("socmint_session", api_id=api_id, api_hash=api_hash, workdir=str(ROOT))
    async with app:
        chats = []
        async for dialog in app.get_dialogs():
            chat = dialog.chat
            name = chat.title or getattr(chat, "first_name", None) or ""
            if not name:
                continue
            if chat.type in KEEP_TYPES or (chat.type == ChatType.PRIVATE and is_project_related(name)):
                chats.append(chat)
        if args.middle_east:
            chosen = [chat for chat in chats if is_middle_east(chat.title or getattr(chat, "first_name", "") or "")]
            chosen.sort(key=lambda chat: (middle_east_rank(chat.title or ""), (chat.title or "").lower()))
            print("order " + " | ".join(chat.title or "" for chat in chosen), flush=True)
        else:
            chosen = []
            for chat in chats:
                name = chat.title or getattr(chat, "first_name", "") or ""
                if is_project_related(name):
                    chosen.append(chat)
                else:
                    print(f"skip {name} | outside project scope", flush=True)
        print(f"chats {len(chosen)}", flush=True)
        for chat in chosen:
            limit = 0 if args.middle_east else MAX_MESSAGES
            try:
                await _pull_chat(app, chat, limit)
            except Exception as exc:
                print(f"skip {chat.title}: {exc}", flush=True)
            await asyncio.sleep(2)
    print("download_done", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
