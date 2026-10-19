"""Router: Emergent Trends, Hourly Velocity & Acceleration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.models import TrendTopicItem, TrendsResponse
from storage.database import SyncSessionLocal
from storage.models.derived_d import TrendTopicD

router = APIRouter(prefix="/trends", tags=["Trend & Velocity Engine"])


def get_sync_db():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.get("", response_model=TrendsResponse)
def get_trends(
    window_hours: int = Query(default=48, ge=1, le=168),
    db: Session = Depends(get_sync_db),
):
    """Retrieve emergent conversational clusters ranked by hourly publication velocity and acceleration."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    stmt = (
        select(TrendTopicD)
        .where(TrendTopicD.analyzed_at >= cutoff)
        .order_by(TrendTopicD.velocity.desc())
    )
    topics = db.execute(stmt).scalars().all()

    items: list[TrendTopicItem] = []
    surging_count = 0

    for t in topics:
        is_surging = t.acceleration > 0.0
        if is_surging:
            surging_count += 1

        items.append(
            TrendTopicItem(
                id=t.id,
                rank=t.rank,
                topic_label=t.topic_label,
                topic_keywords=t.topic_keywords or [],
                post_count=t.post_count,
                velocity=round(t.velocity, 4),
                acceleration=round(t.acceleration, 4),
                is_surging=is_surging,
                analyzed_at=t.analyzed_at.isoformat(),
            )
        )

    return TrendsResponse(
        window_hours=window_hours,
        total_topics=len(items),
        surging_count=surging_count,
        topics=items,
    )
