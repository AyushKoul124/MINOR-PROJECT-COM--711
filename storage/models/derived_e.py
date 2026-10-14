"""Component E: Network interaction graph nodes, edges, Louvain communities & CIB anomaly signals."""

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from storage.database import Base


class NetworkNodeE(Base):
    """Component E: Network graph nodes (channels and authors) with centrality and CIB anomaly scores."""

    __tablename__ = "network_nodes_e"
    __table_args__ = (
        Index("idx_network_nodes_e_window", "window_start", "window_end"),
        Index("idx_network_nodes_e_betweenness", "betweenness_centrality"),
        Index("idx_network_nodes_e_anomaly", "anomaly_score"),
        Index("idx_network_nodes_e_coordination", "coordination_signal"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'channel' or 'author'
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Graph metrics
    degree_centrality: Mapped[float | None] = mapped_column(Float, default=0.0)
    betweenness_centrality: Mapped[float | None] = mapped_column(Float, default=0.0)
    community_id: Mapped[int | None] = mapped_column(Integer, default=0)

    # 3-Signal CIB Heuristics & Anomaly Score: (s1 + s2 + s3) / 3
    anomaly_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    posting_synchrony_signal: Mapped[float | None] = mapped_column(Float, default=0.0)
    age_volume_signal: Mapped[float | None] = mapped_column(Float, default=0.0)
    duplicate_content_signal: Mapped[float | None] = mapped_column(Float, default=0.0)

    # Coordination screening flag (TRUE if anomaly_score >= 0.70)
    coordination_signal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )


class NetworkEdgeE(Base):
    """Component E: Network graph directed interaction edges (reply, forward, mention)."""

    __tablename__ = "network_edges_e"
    __table_args__ = (
        Index("idx_network_edges_e_window", "window_start", "window_end"),
        Index("idx_network_edges_e_source", "source_entity_id"),
        Index("idx_network_edges_e_target", "target_entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'reply', 'forward', 'mention'
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
