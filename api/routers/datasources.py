"""Router: Monitored Data Sources & Ingestion Telemetry."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas.models import DataSourceItem, DataSourcesResponse
from storage.database import SyncSessionLocal
from storage.models.raw import MonitoredChannel, RawPost

router = APIRouter(prefix="/datasources", tags=["Data Sources & Ingestion"])


def get_sync_db():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.get("", response_model=DataSourcesResponse)
def get_datasources(db: Session = Depends(get_sync_db)):
    """Retrieve monitored public Telegram channels, polling schedules, and collection stats."""
    channels = db.execute(select(MonitoredChannel).order_by(MonitoredChannel.id.asc())).scalars().all()

    # Post count per channel
    post_counts = dict(
        db.query(RawPost.channel_id, func.count(RawPost.id)).group_by(RawPost.channel_id).all()
    )

    items: list[DataSourceItem] = []
    active_count = 0

    for ch in channels:
        if ch.is_active:
            active_count += 1

        p_count = post_counts.get(ch.identifier, 0)
        items.append(
            DataSourceItem(
                id=ch.id,
                identifier=ch.identifier,
                display_name=ch.display_name,
                topic_tags=ch.topic_tags or [],
                is_active=ch.is_active,
                last_polled_at=ch.last_polled_at.isoformat() if ch.last_polled_at else None,
                total_posts_collected=p_count,
            )
        )

    poll_sched = int(os.getenv("POLL_SCHEDULE_SECONDS", "1200"))
    jitter_min = os.getenv("POLL_JITTER_MIN_SECONDS", "2")
    jitter_max = os.getenv("POLL_JITTER_MAX_SECONDS", "5")

    return DataSourcesResponse(
        total_channels=len(items),
        active_channels=active_count,
        poll_schedule_seconds=poll_sched,
        jitter_range=f"{jitter_min}-{jitter_max}s",
        channels=items,
    )
