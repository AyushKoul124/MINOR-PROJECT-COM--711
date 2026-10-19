"""Component E — Louvain Community Modularity Detection.

Identifies behavioral sub-communities and coordination clusters within the
interaction network using the Louvain modularity optimization algorithm.

Engineering Invariants:
    1. Import Invariant: The library is installed via ``pip install python-louvain``
       but imported strictly as ``import community as community_louvain``.
    2. Undirected Projection Invariant: Louvain modularity is mathematically undefined
       for directed graphs. The directed DiGraph must be projected into an undirected
       graph with summed bidirectional edge weights before execution:
       ``undirected_G = G.to_undirected(as_view=False)`` or via GraphBuilder.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import community as community_louvain
import networkx as nx

logger = logging.getLogger("network_e.community")


@dataclass(frozen=True)
class CommunityPartitionResult:
    """Result of Louvain community partition detection."""

    node_communities: dict[str, int]  # node_id -> integer community_id (0, 1, 2...)
    total_communities: int
    modularity: float                 # Modularity score Q (-0.5 to 1.0; higher = denser communities)


class CommunityDetector:
    """Louvain community detection with undirected projection safety."""

    @staticmethod
    def detect_communities(G: nx.DiGraph | nx.Graph) -> CommunityPartitionResult:
        """Partition network nodes into communities via Louvain modularity.

        Args:
            G: Directed or undirected interaction graph.

        Returns:
            CommunityPartitionResult with node-to-community assignments and modularity.
        """
        if G.number_of_nodes() == 0:
            return CommunityPartitionResult(node_communities={}, total_communities=0, modularity=0.0)

        # 1. Enforce undirected projection if DiGraph
        if isinstance(G, nx.DiGraph):
            undirected_G = nx.Graph()
            for n, data in G.nodes(data=True):
                undirected_G.add_node(n, **data)
            for u, v, data in G.edges(data=True):
                w = float(data.get("weight", 1.0))
                if undirected_G.has_edge(u, v):
                    undirected_G[u][v]["weight"] += w
                else:
                    undirected_G.add_edge(u, v, weight=w)
        else:
            undirected_G = G

        if undirected_G.number_of_nodes() == 1:
            node = next(iter(undirected_G.nodes()))
            return CommunityPartitionResult(
                node_communities={node: 0},
                total_communities=1,
                modularity=0.0,
            )

        # 2. If graph has no edges, each node is in its own community
        if undirected_G.number_of_edges() == 0:
            communities = {node: idx for idx, node in enumerate(undirected_G.nodes())}
            return CommunityPartitionResult(
                node_communities=communities,
                total_communities=len(communities),
                modularity=0.0,
            )

        # 3. Execute Louvain partition with weighted modularity
        try:
            partition = community_louvain.best_partition(
                undirected_G,
                weight="weight",
                random_state=42,
            )
            modularity_score = community_louvain.modularity(
                partition,
                undirected_G,
                weight="weight",
            )
            total_comm = len(set(partition.values()))
            return CommunityPartitionResult(
                node_communities=partition,
                total_communities=total_comm,
                modularity=round(float(modularity_score), 4),
            )
        except Exception as exc:
            logger.warning("Louvain community partition fallback: %s", exc)
            fallback_partition = {node: 0 for node in undirected_G.nodes()}
            return CommunityPartitionResult(
                node_communities=fallback_partition,
                total_communities=1,
                modularity=0.0,
            )
