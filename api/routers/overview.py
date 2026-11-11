"""Router: Overview KPIs, System Health, and Live Viva Demo Trigger."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import logging

import json
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

logger = logging.getLogger("api.routers.overview")
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas.models import (
    HealthResponse,
    OverviewMetrics,
    TriggerAnalysisRequest,
    TriggerAnalysisResponse,
)
from orchestrator.coordinator import AnalysisCoordinator
from storage.database import SyncSessionLocal
from storage.models.derived_b import SentimentResultB
from storage.models.raw import MonitoredChannel, RawAuthor, RawPost

router = APIRouter(tags=["Overview & Telemetry"])
coordinator = AnalysisCoordinator()
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_MEDIA_ROOT = (_PROJECT_ROOT / "Telegram Desktop").resolve()


def _photo_urls(media: object) -> list[str]:
    """Public image URLs for photos stored under Telegram Desktop."""
    if not isinstance(media, list):
        return []
    urls: list[str] = []
    for item in media:
        if not isinstance(item, dict):
            continue
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            continue
        target = (_PROJECT_ROOT / raw_path).resolve()
        try:
            target.relative_to(_MEDIA_ROOT)
        except ValueError:
            continue
        if target.is_file():
            urls.append("/api/media?path=" + quote(raw_path))
    return urls


def _telegram_message_id(platform_post_id: str) -> str | None:
    """The Telegram message id is the last segment of platform_post_id."""
    tail = platform_post_id.rsplit("_", 1)[-1]
    if tail.isdigit():
        return tail
    return None


def _reaction_chips(raw: object) -> list[dict]:
    """Emoji counts from the reaction bar, highest count first."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, dict):
        return []
    chips: list[dict] = []
    for key, value in raw.items():
        emoji = str(key).strip()
        if not emoji or emoji in {"?", "\ufffd"}:
            continue
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count > 0:
            chips.append({"emoji": emoji, "count": count})
    chips.sort(key=lambda item: (-item["count"], item["emoji"]))
    return chips[:12]


def _author_label(
    author_id: str | None,
    channel_id: str,
    people: dict[str, str],
    channels: dict[str, str],
) -> str:
    if author_id and author_id in people:
        return people[author_id]
    if author_id and author_id in channels:
        return channels[author_id]
    if author_id and author_id == channel_id:
        return channels.get(channel_id) or "Channel"
    return "Telegram user"


def _comment_payload(
    post: RawPost,
    people: dict[str, str],
    channels: dict[str, str],
) -> dict:
    return {
        "comment_id": post.id,
        "author": _author_label(post.author_id, post.channel_id, people, channels),
        "posted_at": post.posted_at.isoformat(),
        "content_text": (post.content_text or "").strip(),
        "photos": _photo_urls(post.media_urls),
        "reactions": _reaction_chips(post.reaction_counts),
        "replies": [],
    }


def _load_comments(
    db: Session,
    parents: list[tuple[str, str]],
    people: dict[str, str],
    channels: dict[str, str],
) -> dict[tuple[str, str], list[dict]]:
    """Replies saved in the same chat, plus one level of replies to those replies."""
    parent_keys = {(channel_id, message_id) for channel_id, message_id in parents if message_id}
    if not parent_keys:
        return {}
    channel_ids = {channel_id for channel_id, _ in parent_keys}
    message_ids = {message_id for _, message_id in parent_keys}
    direct_rows = db.execute(
        select(RawPost)
        .where(RawPost.channel_id.in_(channel_ids), RawPost.reply_to_id.in_(message_ids))
        .order_by(RawPost.posted_at.asc(), RawPost.id.asc())
    ).scalars().all()
    direct = [
        post for post in direct_rows
        if post.reply_to_id and (post.channel_id, post.reply_to_id) in parent_keys
    ]

    child_keys: set[tuple[str, str]] = set()
    direct_payloads: dict[tuple[str, str], dict] = {}
    grouped: dict[tuple[str, str], list[dict]] = {key: [] for key in parent_keys}
    for post in direct:
        message_id = _telegram_message_id(post.platform_post_id)
        payload = _comment_payload(post, people, channels)
        if message_id:
            child_keys.add((post.channel_id, message_id))
            direct_payloads[(post.channel_id, message_id)] = payload
        parent_key = (post.channel_id, post.reply_to_id or "")
        if len(grouped[parent_key]) < 40:
            grouped[parent_key].append(payload)

    if child_keys:
        child_channels = {channel_id for channel_id, _ in child_keys}
        child_ids = {message_id for _, message_id in child_keys}
        nested_rows = db.execute(
            select(RawPost)
            .where(RawPost.channel_id.in_(child_channels), RawPost.reply_to_id.in_(child_ids))
            .order_by(RawPost.posted_at.asc(), RawPost.id.asc())
        ).scalars().all()
        for post in nested_rows:
            if not post.reply_to_id or (post.channel_id, post.reply_to_id) not in child_keys:
                continue
            parent = direct_payloads.get((post.channel_id, post.reply_to_id))
            if parent is not None and len(parent["replies"]) < 20:
                parent["replies"].append(_comment_payload(post, people, channels))
    return grouped


def get_sync_db():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_sync_db)):
    """Health check endpoint validating PostgreSQL connection and runtime device."""
    db_connected = False
    try:
        db.execute(select(1)).scalar()
        db_connected = True
    except Exception:
        db_connected = False

    device = "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            device = "cuda"
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        database_connected=db_connected,
        device=device,
        version="4.8",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/overview", response_model=OverviewMetrics)
@router.get("/overview/summary", response_model=OverviewMetrics, include_in_schema=False)
def get_overview_metrics(db: Session = Depends(get_sync_db)):
    """Retrieve operational telemetry, queue metrics, and sentiment distribution."""
    # Active channels
    active_ch = db.query(func.count(MonitoredChannel.id)).filter(
        MonitoredChannel.is_active.is_(True)
    ).scalar() or 0

    # Post counts
    total_posts = db.query(func.count(RawPost.id)).scalar() or 0
    pending_posts = db.query(func.count(RawPost.id)).filter(
        RawPost.processing_status == "pending"
    ).scalar() or 0
    processed_posts = db.query(func.count(RawPost.id)).filter(
        RawPost.processing_status == "processed"
    ).scalar() or 0

    # Sentiment distribution
    sent_rows = (
        db.query(SentimentResultB.valence, func.count(SentimentResultB.id))
        .group_by(SentimentResultB.valence)
        .all()
    )
    sent_dist = {r[0]: r[1] for r in sent_rows if r[0]}

    # Top emotions
    emotion_rows = (
        db.query(SentimentResultB.dominant_emotion, func.count(SentimentResultB.id))
        .group_by(SentimentResultB.dominant_emotion)
        .order_by(func.count(SentimentResultB.id).desc())
        .limit(6)
        .all()
    )
    top_emotions = {r[0]: r[1] for r in emotion_rows if r[0]}

    telemetry = coordinator.get_pipeline_telemetry()
    last_run = telemetry.get("last_run_telemetry", {})
    last_time = last_run.get("completed_at")

    return OverviewMetrics(
        active_channels=active_ch,
        total_posts=total_posts,
        pending_posts=pending_posts,
        processed_posts=processed_posts,
        sentiment_distribution=sent_dist,
        top_emotions=top_emotions,
        last_analysis_time=last_time,
        viva_timing_invariant_satisfied=last_run.get("meets_demo_timing_invariant", True),
    )


@router.get("/overview/posts")
def recent_posts(
    limit: int = Query(default=24, ge=1, le=80),
    db: Session = Depends(get_sync_db),
):
    """Newest saved posts, including ones that have not been analysed yet."""
    rows = db.execute(
        select(RawPost, MonitoredChannel.display_name)
        .outerjoin(MonitoredChannel, MonitoredChannel.identifier == RawPost.channel_id)
        .where(~RawPost.platform_post_id.contains("_comment_"))
        .order_by(RawPost.posted_at.desc(), RawPost.id.desc())
        .limit(limit)
    ).all()
    channel_names = {
        identifier: name
        for identifier, name in db.execute(
            select(MonitoredChannel.identifier, MonitoredChannel.display_name)
        ).all()
        if name
    }
    people = {
        author_id: name
        for author_id, name in db.execute(
            select(RawAuthor.platform_author_id, RawAuthor.display_name)
            .where(RawAuthor.display_name.is_not(None))
            .order_by(RawAuthor.snapshot_at.asc())
        ).all()
        if name
    }
    parents = [
        (post.channel_id, _telegram_message_id(post.platform_post_id) or "")
        for post, _display_name in rows
    ]
    comments_by_post = _load_comments(db, parents, people, channel_names)
    posts = []
    for (post, display_name), (channel_id, message_id) in zip(rows, parents):
        text = (post.content_text or "").strip()
        photos = _photo_urls(post.media_urls)
        posts.append({
            "post_id": post.id,
            "channel": display_name or post.channel_id,
            "posted_at": post.posted_at.isoformat(),
            "content_text": text,
            "photos": photos,
            "kind": "picture" if photos else "text",
            "status": post.processing_status,
            "reactions": _reaction_chips(post.reaction_counts),
            "comments": comments_by_post.get((channel_id, message_id), []),
        })
    return {"count": len(posts), "posts": posts}


@router.get("/media")
def serve_photo(path: str = Query(..., min_length=1, max_length=500)):
    """Serve one saved Telegram photo. The path must stay inside Telegram Desktop."""
    target = (_PROJECT_ROOT / path).resolve()
    try:
        target.relative_to(_MEDIA_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Photo not found") from exc
    if not target.is_file() or target.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(target)


@router.post("/orchestrator/trigger", response_model=TriggerAnalysisResponse)
@router.post("/overview/trigger-analysis", response_model=TriggerAnalysisResponse, include_in_schema=False)
def trigger_analysis_now(req: TriggerAnalysisRequest):
    """Instant viva trigger: processes <= 50 pending posts and executes C/D/E window analytics."""
    try:
        report = coordinator.trigger_full_analysis(
            b_batch_limit=req.b_batch_limit,
            window_hours=req.window_hours,
        )
        return TriggerAnalysisResponse(**report)
    except Exception as exc:
        logger.error("trigger_full_analysis failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline error: {exc!s}",
        ) from exc
