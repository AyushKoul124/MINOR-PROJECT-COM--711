"""Router: Overview KPIs, System Health, and Live Viva Demo Trigger."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
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
from storage.models.raw import MonitoredChannel, RawPost

router = APIRouter(tags=["Overview & Telemetry"])
coordinator = AnalysisCoordinator()


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


@router.post("/orchestrator/trigger", response_model=TriggerAnalysisResponse)
def trigger_analysis_now(req: TriggerAnalysisRequest):
    """Instant viva trigger: processes <= 50 pending posts and executes C/D/E window analytics."""
    report = coordinator.trigger_full_analysis(
        b_batch_limit=req.b_batch_limit,
        window_hours=req.window_hours,
    )
    return TriggerAnalysisResponse(**report)
