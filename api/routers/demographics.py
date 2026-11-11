"""Router: Demographic Profiling & DPDP Act 2023 k-Anonymity Guard."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.models import DemographicClusterItem, DemographicsResponse
from demographic_c.pattern_analyzer import PatternAnalyzer
from storage.database import SyncSessionLocal
from storage.models.derived_c import DemographicAggregateC
from storage.models.raw import MonitoredChannel, RawPost

router = APIRouter(prefix="/demographics", tags=["Demographics & Privacy"])


def get_sync_db():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.get("", response_model=DemographicsResponse)
def get_demographics(
    window_hours: int = Query(default=48, ge=1, le=168),
    db: Session = Depends(get_sync_db),
):
    """Retrieve aggregate audience demographic clusters with Section 6 DPDP k-anonymity compliance."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    stmt = (
        select(DemographicAggregateC)
        .where(DemographicAggregateC.analyzed_at >= cutoff)
        .order_by(DemographicAggregateC.analyzed_at.desc())
    )
    clusters = db.execute(stmt).scalars().all()

    names = {
        row.identifier: row.display_name
        for row in db.execute(select(MonitoredChannel)).scalars().all()
    }

    def readable_label(raw: str) -> str:
        suffix = " Audience"
        if raw.endswith(suffix):
            key = raw[: -len(suffix)]
            if key in names:
                return names[key]
        return raw

    items: list[DemographicClusterItem] = []
    suppressed_count = 0
    seen_labels: set[str] = set()

    for c in clusters:
        # Each analysis run inserts a new copy. Keep the newest row for each group.
        if c.cluster_label in seen_labels:
            continue
        seen_labels.add(c.cluster_label)
        if c.below_threshold:
            suppressed_count += 1

        items.append(
            DemographicClusterItem(
                id=c.id,
                cluster_label=readable_label(c.cluster_label),
                account_count=c.account_count,
                below_threshold=c.below_threshold,
                age_bracket_dist=c.age_bracket_dist or {},
                geography_dist=c.geography_dist or {},
                language_dist=c.language_dist or {},
                interest_dist=c.interest_dist or {},
                inference_confidence=c.inference_confidence,
                analyzed_at=c.analyzed_at.isoformat(),
            )
        )

    posted = db.execute(
        select(RawPost.posted_at).where(RawPost.posted_at >= cutoff)
    ).scalars().all()
    rhythm = PatternAnalyzer().analyze_timestamps(list(posted))
    phases = rhythm.phase_distribution
    peak = rhythm.peak_hours_ist[0] if rhythm.peak_hours_ist else None
    diurnal_ist = {
        "morning_ist_ratio": phases.get("Morning (06:00-12:00 IST)", 0.0),
        "afternoon_ist_ratio": phases.get("Afternoon (12:00-18:00 IST)", 0.0),
        "evening_ist_ratio": phases.get("Evening (18:00-23:00 IST)", 0.0),
        "night_ist_ratio": phases.get("Night (23:00-06:00 IST)", 0.0),
        "peak_hour_ist": f"{peak:02d}:00 IST" if peak is not None else "No posts in this window",
        "hourly_counts": [rhythm.hourly_distribution_ist.get(hour, 0) for hour in range(24)],
        "posts": rhythm.total_posts_analyzed,
    }

    return DemographicsResponse(
        window_hours=window_hours,
        k_anonymity_threshold=50,
        total_clusters=len(items),
        suppressed_clusters=suppressed_count,
        clusters=items,
        diurnal_rhythm_ist=diurnal_ist,
    )
