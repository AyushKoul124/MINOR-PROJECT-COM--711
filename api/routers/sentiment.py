"""Router: Sentiment, Emotion & Policy Stance Analytics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas.models import SentimentTimelinePoint, SentimentTimelineResponse
from storage.database import SyncSessionLocal
from storage.models.derived_b import SentimentResultB
from storage.models.raw import RawPost

router = APIRouter(prefix="/sentiment", tags=["Sentiment Analytics"])


def get_sync_db():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.get("/timeline", response_model=SentimentTimelineResponse)
def get_sentiment_timeline(
    window_hours: int = Query(default=48, ge=1, le=168),
    db: Session = Depends(get_sync_db),
):
    """Retrieve chronological sentiment valence and Ekman emotion time series."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    stmt = (
        select(RawPost, SentimentResultB)
        .join(SentimentResultB, RawPost.id == SentimentResultB.raw_post_id)
        .where(RawPost.posted_at >= cutoff)
        .order_by(RawPost.posted_at.asc())
    )
    rows = db.execute(stmt).all()

    # Stance breakdown
    stance_counts: dict[str, int] = {}
    sarcasm_count = 0

    # Bucket posts into 4-hour intervals
    interval_hours = max(1, window_hours // 12)
    bucket_map: dict[datetime, list[SentimentResultB]] = {}

    for post, s_res in rows:
        st = s_res.stance or "neutral"
        stance_counts[st] = stance_counts.get(st, 0) + 1
        if s_res.sarcasm_flag:
            sarcasm_count += 1

        # Truncate to bucket interval
        dt = post.posted_at
        bucket_hour = (dt.hour // interval_hours) * interval_hours
        bucket_dt = dt.replace(hour=bucket_hour, minute=0, second=0, microsecond=0)
        bucket_map.setdefault(bucket_dt, []).append(s_res)

    points: list[SentimentTimelinePoint] = []
    for b_dt in sorted(bucket_map.keys()):
        b_res = bucket_map[b_dt]
        n_b = len(b_res)

        pos = sum(1 for r in b_res if r.valence == "positive")
        neg = sum(1 for r in b_res if r.valence == "negative")
        neu = sum(1 for r in b_res if r.valence in ("neutral", None))

        points.append(
            SentimentTimelinePoint(
                timestamp=b_dt.isoformat(),
                positive_count=pos,
                negative_count=neg,
                neutral_count=neu,
                joy_avg=round(sum(r.emotion_joy or 0.0 for r in b_res) / n_b, 3),
                anger_avg=round(sum(r.emotion_anger or 0.0 for r in b_res) / n_b, 3),
                fear_avg=round(sum(r.emotion_fear or 0.0 for r in b_res) / n_b, 3),
                sadness_avg=round(sum(r.emotion_sadness or 0.0 for r in b_res) / n_b, 3),
                surprise_avg=round(sum(r.emotion_surprise or 0.0 for r in b_res) / n_b, 3),
                disgust_avg=round(sum(r.emotion_disgust or 0.0 for r in b_res) / n_b, 3),
            )
        )

    return SentimentTimelineResponse(
        window_hours=window_hours,
        total_posts=len(rows),
        points=points,
        stance_breakdown=stance_counts,
        sarcasm_count=sarcasm_count,
    )


@router.get("/latest")
def get_latest_sentiment_posts(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Retrieve individual recent analyzed posts with emotion & stance breakdowns."""
    stmt = (
        select(RawPost, SentimentResultB)
        .join(SentimentResultB, RawPost.id == SentimentResultB.raw_post_id)
        .order_by(RawPost.posted_at.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()

    items = []
    for post, s_res in rows:
        items.append({
            "post_id": post.id,
            "channel_id": post.channel_id,
            "posted_at": post.posted_at.isoformat(),
            "content_text": (post.content_text or "").strip()[:240],
            "valence": s_res.valence,
            "dominant_emotion": s_res.dominant_emotion,
            "emotion_confidence": s_res.emotion_confidence,
            "stance": s_res.stance,
            "stance_confidence": s_res.stance_confidence,
            "sarcasm_flag": s_res.sarcasm_flag,
        })

    return {"count": len(items), "posts": items}
