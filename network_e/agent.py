"""Component E — Network Agent.

Orchestrates interaction graph construction, centrality ranking, Louvain
community detection, 3-signal CIB anomaly screening, and PostgreSQL persistence
to ``network_nodes_e`` and ``network_edges_e``.

Engineering Invariants:
    1. Privacy Masking: Authors are masked as 'Actor-[Masked]-XXXX'.
    2. Undirected Projection: Directed interaction graphs are projected to
       undirected weighted graphs before Louvain modularity execution.
    3. 500-Node Visual Ceiling: Prunes graph to top 500 nodes by betweenness
       centrality with strictly induced edges for WebGL rendering performance.
    4. Advisory CIB Signals: Composite anomaly scores are unweighted arithmetic
       means: (s1_synchrony + s2_age_volume + s3_duplicate_content) / 3.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import networkx as nx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from network_e.centrality import CentralityEngine, CentralityScores
from network_e.cib_signals import CIBDetector, CIBSignalsResult
from network_e.community import CommunityDetector, CommunityPartitionResult
from network_e.graph_builder import GraphBuilder
from network_e.summary import generate_network_summary
from storage.database import SyncSessionLocal
from storage.models.derived_e import NetworkEdgeE, NetworkNodeE
from storage.models.raw import RawAuthor, RawPost

logger = logging.getLogger("network_e.agent")


@dataclass
class NetworkNodeResult:
    """Enriched node data with centrality, community, and CIB signals."""

    entity_id: str
    entity_type: str
    label: str
    degree_centrality: float
    betweenness_centrality: float
    community_id: int
    anomaly_score: float
    posting_synchrony_signal: float
    age_volume_signal: float
    duplicate_content_signal: float
    coordination_signal: bool


@dataclass
class NetworkEdgeResult:
    """Directed interaction edge between two entities."""

    source_entity_id: str
    target_entity_id: str
    interaction_type: str
    weight: float


@dataclass
class NetworkRunResult:
    """Complete output of a Component E network and CIB analysis run."""

    window_start: datetime
    window_end: datetime
    nodes: list[NetworkNodeResult]
    edges: list[NetworkEdgeResult]
    community_result: CommunityPartitionResult
    summary: str
    persisted_node_ids: list[int] = field(default_factory=list)
    persisted_edge_ids: list[int] = field(default_factory=list)

    def to_webgl_payload(self) -> dict[str, Any]:
        """Convert graph to format consumable by react-force-graph-2d."""
        return {
            "nodes": [
                {
                    "id": n.entity_id,
                    "label": n.label,
                    "entity_type": n.entity_type,
                    "community_id": n.community_id,
                    "betweenness": n.betweenness_centrality,
                    "degree": n.degree_centrality,
                    "anomaly_score": n.anomaly_score,
                    "coordination_signal": n.coordination_signal,
                }
                for n in self.nodes
            ],
            "links": [
                {
                    "source": e.source_entity_id,
                    "target": e.target_entity_id,
                    "type": e.interaction_type,
                    "weight": e.weight,
                }
                for e in self.edges
            ],
            "summary": self.summary,
            "modularity": self.community_result.modularity,
            "total_communities": self.community_result.total_communities,
        }


class NetworkAgent:
    """Component E agent orchestrating graph analytics and CIB screening."""

    def __init__(
        self,
        max_nodes: int = 500,
        cib_threshold: float = 0.70,
    ) -> None:
        self.builder = GraphBuilder(max_nodes=max_nodes)
        self.centrality_engine = CentralityEngine()
        self.community_detector = CommunityDetector()
        self.cib_detector = CIBDetector(anomaly_threshold=cib_threshold)

    def analyze_network(
        self,
        posts: list[RawPost],
        authors: list[RawAuthor] | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> NetworkRunResult:
        """Perform complete graph construction, community detection, and CIB screening.

        Args:
            posts: List of RawPost entities.
            authors: Optional list of RawAuthor entities.
            window_start: Optional window start (defaults to min posted_at or now - 48h).
            window_end: Optional window end (defaults to max posted_at or now).

        Returns:
            NetworkRunResult containing nodes, edges, partitions, and summary.
        """
        now = datetime.now(timezone.utc)
        w_start = window_start or (now - timedelta(hours=48))
        w_end = window_end or now

        # 1. Build directed interaction DiGraph
        raw_G = self.builder.build_interaction_graph(posts, authors)

        if raw_G.number_of_nodes() == 0:
            empty_part = CommunityPartitionResult({}, 0, 0.0)
            empty_sum = generate_network_summary(0, 0, 0, 0.0, [], [])
            return NetworkRunResult(
                window_start=w_start,
                window_end=w_end,
                nodes=[],
                edges=[],
                community_result=empty_part,
                summary=empty_sum,
            )

        # 2. Compute centrality on the full interaction graph
        centrality_map = self.centrality_engine.compute_all(raw_G)
        betweenness_scores = {n: s.betweenness_centrality for n, s in centrality_map.items()}

        # 3. Prune graph to visual ceiling (top 500 nodes by betweenness)
        pruned_G = self.builder.prune_to_top_nodes(raw_G, betweenness_scores)

        # 4. Louvain community detection on undirected projection
        community_res = self.community_detector.detect_communities(pruned_G)

        # 5. Build author lookup map
        author_lookup: dict[str, RawAuthor] = {}
        if authors:
            for a in authors:
                pid = getattr(a, "platform_author_id", str(getattr(a, "id", "")))
                author_lookup[pid] = a

        # Group posts by entity (author or channel)
        entity_posts_map: dict[str, list[RawPost]] = {}
        for p in posts:
            ch_id = p.channel_id
            entity_posts_map.setdefault(ch_id, []).append(p)
            if p.author_id:
                entity_posts_map.setdefault(p.author_id, []).append(p)

        # 6. Compute CIB anomaly signals for each node
        node_results: list[NetworkNodeResult] = []
        flagged_entities: list[dict[str, Any]] = []

        for node_id in pruned_G.nodes():
            ndata = pruned_G.nodes[node_id]
            etype = ndata.get("entity_type", "author")
            lbl = ndata.get("label", node_id)
            c_scores = centrality_map.get(node_id, CentralityScores(0.0, 0.0))
            comm_id = community_res.node_communities.get(node_id, 0)

            e_posts = entity_posts_map.get(node_id, [])
            cib_res = self.cib_detector.compute_signals(
                entity_id=node_id,
                entity_type=etype,
                entity_posts=e_posts,
                all_posts=posts,
                author_meta=author_lookup.get(node_id),
            )

            if cib_res.coordination_signal:
                flagged_entities.append({
                    "entity_id": node_id,
                    "label": lbl,
                    "anomaly_score": cib_res.anomaly_score,
                })

            node_results.append(
                NetworkNodeResult(
                    entity_id=node_id,
                    entity_type=etype,
                    label=lbl,
                    degree_centrality=c_scores.degree_centrality,
                    betweenness_centrality=c_scores.betweenness_centrality,
                    community_id=comm_id,
                    anomaly_score=cib_res.anomaly_score,
                    posting_synchrony_signal=cib_res.posting_synchrony_signal,
                    age_volume_signal=cib_res.age_volume_signal,
                    duplicate_content_signal=cib_res.duplicate_content_signal,
                    coordination_signal=cib_res.coordination_signal,
                )
            )

        # 7. Extract edge results from the pruned graph
        edge_results: list[NetworkEdgeResult] = []
        for u, v, data in pruned_G.edges(data=True):
            edge_results.append(
                NetworkEdgeResult(
                    source_entity_id=u,
                    target_entity_id=v,
                    interaction_type=data.get("interaction_type", "post"),
                    weight=float(data.get("weight", 1.0)),
                )
            )

        # 8. Identify top broker labels for summary
        sorted_by_betweenness = sorted(
            node_results, key=lambda n: n.betweenness_centrality, reverse=True
        )
        top_brokers = [n.label for n in sorted_by_betweenness[:2] if n.betweenness_centrality > 0]

        summary = generate_network_summary(
            total_nodes=len(node_results),
            total_edges=len(edge_results),
            total_communities=community_res.total_communities,
            modularity=community_res.modularity,
            flagged_entities=flagged_entities,
            top_broker_labels=top_brokers,
        )

        return NetworkRunResult(
            window_start=w_start,
            window_end=w_end,
            nodes=node_results,
            edges=edge_results,
            community_result=community_res,
            summary=summary,
        )

    def run_window_analysis(
        self,
        window_hours: int = 48,
        persist: bool = True,
    ) -> NetworkRunResult:
        """Run network analysis over the trailing observation window in PostgreSQL.

        Args:
            window_hours: Trailing hours to query (default: 48).
            persist: If True, commits records to network_nodes_e and network_edges_e.

        Returns:
            NetworkRunResult with persisted record IDs.
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=window_hours)
        window_end = now

        with SyncSessionLocal() as session:
            # Query posts strictly on posted_at
            post_stmt = (
                select(RawPost)
                .where(RawPost.posted_at >= window_start)
                .order_by(RawPost.posted_at.desc())
            )
            posts = list(session.execute(post_stmt).scalars().all())

            # Query authors
            author_stmt = select(RawAuthor)
            authors = list(session.execute(author_stmt).scalars().all())

            result = self.analyze_network(
                posts=posts,
                authors=authors,
                window_start=window_start,
                window_end=window_end,
            )

            if persist and result.nodes:
                # 1. Insert nodes into network_nodes_e
                persisted_node_ids: list[int] = []
                for n in result.nodes:
                    node_stmt = (
                        pg_insert(NetworkNodeE)
                        .values(
                            entity_id=n.entity_id,
                            entity_type=n.entity_type,
                            label=n.label,
                            window_start=window_start,
                            window_end=window_end,
                            degree_centrality=n.degree_centrality,
                            betweenness_centrality=n.betweenness_centrality,
                            community_id=n.community_id,
                            anomaly_score=n.anomaly_score,
                            posting_synchrony_signal=n.posting_synchrony_signal,
                            age_volume_signal=n.age_volume_signal,
                            duplicate_content_signal=n.duplicate_content_signal,
                            coordination_signal=n.coordination_signal,
                            analyzed_at=now,
                        )
                        .returning(NetworkNodeE.id)
                    )
                    row = session.execute(node_stmt).fetchone()
                    if row:
                        persisted_node_ids.append(row[0])

                # 2. Insert edges into network_edges_e
                persisted_edge_ids: list[int] = []
                for e in result.edges:
                    edge_stmt = (
                        pg_insert(NetworkEdgeE)
                        .values(
                            source_entity_id=e.source_entity_id,
                            target_entity_id=e.target_entity_id,
                            interaction_type=e.interaction_type,
                            weight=e.weight,
                            window_start=window_start,
                            window_end=window_end,
                        )
                        .returning(NetworkEdgeE.id)
                    )
                    row = session.execute(edge_stmt).fetchone()
                    if row:
                        persisted_edge_ids.append(row[0])

                session.commit()
                result.persisted_node_ids = persisted_node_ids
                result.persisted_edge_ids = persisted_edge_ids

                logger.info(
                    "Persisted %d nodes and %d edges to network_nodes_e and network_edges_e.",
                    len(persisted_node_ids),
                    len(persisted_edge_ids),
                )

        return result

    def run_demo_analysis(self) -> NetworkRunResult:
        """Fast demonstration run for the 'Run Analysis Now' viva trigger."""
        return self.run_window_analysis(window_hours=48, persist=True)
