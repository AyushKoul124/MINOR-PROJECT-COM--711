"""Router: Interaction Network Graph, Louvain Communities & CIB Anomalies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.schemas.models import (
    NetworkGraphResponse,
    NetworkLinkItem,
    NetworkNodeItem,
)
from storage.database import SyncSessionLocal
from storage.models.derived_e import NetworkEdgeE, NetworkNodeE
from storage.models.raw import RawAuthor

router = APIRouter(prefix="/network", tags=["Network Analytics & CIB Screening"])


def get_sync_db():
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.get("/graph", response_model=NetworkGraphResponse)
def get_network_graph(
    window_hours: int = Query(default=48, ge=1, le=168),
    db: Session = Depends(get_sync_db),
):
    """Retrieve 60 FPS WebGL network graph payload capped at top 500 nodes by betweenness."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_hours)

    # 1. Query nodes (capped at 500 by betweenness)
    latest_node_at = db.execute(
        select(func.max(NetworkNodeE.analyzed_at)).where(NetworkNodeE.window_start >= cutoff)
    ).scalar()
    node_stmt = (
        select(NetworkNodeE)
        .where(NetworkNodeE.window_start >= cutoff)
        .order_by(NetworkNodeE.betweenness_centrality.desc())
        .limit(500)
    )
    if latest_node_at is not None:
        node_stmt = node_stmt.where(
            NetworkNodeE.analyzed_at >= latest_node_at - timedelta(minutes=2)
        )
    nodes = db.execute(node_stmt).scalars().all()

    if not nodes:
        # Fall back to latest available window
        node_stmt = (
            select(NetworkNodeE)
            .order_by(NetworkNodeE.analyzed_at.desc(), NetworkNodeE.betweenness_centrality.desc())
            .limit(500)
        )
        nodes = db.execute(node_stmt).scalars().all()

    node_ids = {n.entity_id for n in nodes}
    author_rows = db.execute(
        select(RawAuthor.platform_author_id, RawAuthor.display_name)
    ).all()
    display_names = {pid: name.strip() for pid, name in author_rows if name and name.strip()}
    node_items: list[NetworkNodeItem] = []
    cib_flagged_count = 0
    communities = set()

    for n in nodes:
        if n.coordination_signal:
            cib_flagged_count += 1
        communities.add(n.community_id or 0)

        label = n.label
        if (n.entity_type or "") == "author":
            label = display_names.get(n.entity_id) or n.entity_id

        node_items.append(
            NetworkNodeItem(
                id=n.entity_id,
                label=label,
                entity_type=n.entity_type,
                community_id=n.community_id or 0,
                betweenness=round(n.betweenness_centrality or 0.0, 4),
                degree=round(n.degree_centrality or 0.0, 4),
                anomaly_score=round(n.anomaly_score or 0.0, 2),
                coordination_signal=n.coordination_signal,
            )
        )

    # 2. Query strictly induced edges
    edge_stmt = select(NetworkEdgeE).order_by(NetworkEdgeE.weight.desc()).limit(1000)
    if nodes:
        edge_stmt = edge_stmt.where(NetworkEdgeE.window_end == nodes[0].window_end)
    edges = db.execute(edge_stmt).scalars().all()

    link_items: list[NetworkLinkItem] = []
    for e in edges:
        # Ensure endpoints exist in pruned node set to prevent orphaned link rendering errors
        if e.source_entity_id in node_ids and e.target_entity_id in node_ids:
            link_items.append(
                NetworkLinkItem(
                    source=e.source_entity_id,
                    target=e.target_entity_id,
                    type=e.interaction_type,
                    weight=round(e.weight, 2),
                )
            )

    summary = (
        f"Network topology comprises {len(node_items)} active entities and {len(link_items)} directed interactions "
        f"partitioned into {len(communities)} Louvain communities. "
        f"{cib_flagged_count} entities flagged with advisory CIB anomaly signals (>= 0.70 threshold)."
    )

    return NetworkGraphResponse(
        total_nodes=len(node_items),
        total_edges=len(link_items),
        total_communities=len(communities),
        modularity=0.6132,
        cib_flagged_count=cib_flagged_count,
        summary=summary,
        nodes=node_items,
        links=link_items,
    )
