"""Component E — Centrality Metrics Engine.

Computes degree centrality and shortest-path betweenness centrality
for entities in the interaction network.

Betweenness Centrality Invariant:
    Betweenness centrality is the primary metric used for ranking and
    pruning nodes to the 500-node visual budget. While degree centrality
    surfaces high-volume broadcasting accounts, betweenness surfaces
    information brokers and coordination bridges connecting distinct
    communities or channel clusters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import networkx as nx

logger = logging.getLogger("network_e.centrality")


@dataclass(frozen=True)
class CentralityScores:
    """Calculated centrality scores for an entity node."""

    degree_centrality: float
    betweenness_centrality: float


class CentralityEngine:
    """Computes normalized degree and betweenness centrality across graph nodes."""

    @staticmethod
    def compute_all(G: nx.DiGraph) -> dict[str, CentralityScores]:
        """Compute degree and betweenness centrality for all nodes in graph G.

        Args:
            G: Directed interaction graph.

        Returns:
            Dict mapping node_id -> CentralityScores(degree, betweenness).
        """
        n_nodes = G.number_of_nodes()
        if n_nodes == 0:
            return {}

        if n_nodes == 1:
            node = next(iter(G.nodes()))
            return {node: CentralityScores(degree_centrality=1.0, betweenness_centrality=0.0)}

        # Degree centrality (in-degree + out-degree for directed graphs, regular degree for undirected)
        try:
            if G.is_directed():
                in_deg = nx.in_degree_centrality(G)
                out_deg = nx.out_degree_centrality(G)
                # Composite normalized degree centrality
                degree_dict = {n: round((in_deg.get(n, 0.0) + out_deg.get(n, 0.0)) / 2.0, 4) for n in G.nodes()}
            else:
                deg = nx.degree_centrality(G)
                degree_dict = {n: round(deg.get(n, 0.0), 4) for n in G.nodes()}
        except Exception as exc:
            logger.warning("Error computing degree centrality: %s", exc)
            degree_dict = {n: 0.0 for n in G.nodes()}

        # Betweenness centrality (weighted by interaction edge volume)
        try:
            betweenness_dict = nx.betweenness_centrality(G, weight="weight", normalized=True)
            betweenness_dict = {n: round(val, 4) for n, val in betweenness_dict.items()}
        except Exception as exc:
            logger.warning("Error computing betweenness centrality: %s", exc)
            betweenness_dict = {n: 0.0 for n in G.nodes()}

        results: dict[str, CentralityScores] = {}
        for n in G.nodes():
            results[n] = CentralityScores(
                degree_centrality=degree_dict.get(n, 0.0),
                betweenness_centrality=betweenness_dict.get(n, 0.0),
            )

        return results
