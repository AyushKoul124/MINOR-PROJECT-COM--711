"""Component E — Network Interaction Graph Construction via NetworkX.

Extracts directed interaction networks (forwards, replies, mentions, posts)
between Channels and Authors from raw posts and profiles.

Engineering Invariants:
    1. Entity Model: Distinguishes between 'channel' (broadcast entity) and
       'author' (commenter/participant), preventing null-author schema crashes.
    2. Directed Interactions: Graph is constructed as a ``networkx.DiGraph`` with
       aggregated edge weights representing interaction volume.
    3. Privacy Masking: Authors are masked as ``Actor-[Masked]-XXXX`` in public
       labels to comply with privacy invariants (no individual citizen surveillance).
    4. Graph Pruning Ceiling: Caps graph output at top 500 nodes by betweenness
       centrality with strictly induced edges for 60 FPS WebGL rendering.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import networkx as nx

from storage.models.raw import RawAuthor, RawPost

MAX_GRAPH_NODES = 500


@dataclass
class NodeData:
    """Network entity node data."""

    entity_id: str
    entity_type: str  # 'channel' or 'author'
    label: str


@dataclass
class EdgeData:
    """Directed interaction edge data."""

    source_id: str
    target_id: str
    interaction_type: str  # 'forward', 'reply', 'mention', 'post'
    weight: float = 1.0


class GraphBuilder:
    """Constructs and prunes directed interaction graphs from raw posts."""

    def __init__(self, max_nodes: int = MAX_GRAPH_NODES) -> None:
        self.max_nodes = max_nodes

    @staticmethod
    def mask_author_label(author_id: str, display_name: str | None = None) -> str:
        """Generate a privacy-preserving masked actor label for an author."""
        digest = hashlib.sha256(author_id.encode("utf-8")).hexdigest()[:4].upper()
        return f"Actor-[Masked]-{digest}"

    def build_interaction_graph(
        self,
        posts: list[RawPost],
        authors: list[RawAuthor] | None = None,
    ) -> nx.DiGraph:
        """Build a directed interaction graph from raw posts and authors.

        Args:
            posts: List of RawPost entities.
            authors: Optional list of RawAuthor entities for metadata lookups.

        Returns:
            networkx.DiGraph with nodes ('entity_type', 'label') and weighted edges.
        """
        G = nx.DiGraph()

        # Build author lookup for display names
        author_meta: dict[str, RawAuthor] = {}
        if authors:
            for a in authors:
                pid = getattr(a, "platform_author_id", str(getattr(a, "id", "")))
                author_meta[pid] = a

        # 1. Add all active channels as channel nodes
        for p in posts:
            ch_id = p.channel_id
            if ch_id and ch_id not in G:
                G.add_node(
                    ch_id,
                    entity_type="channel",
                    label=ch_id,
                )

        # 2. Extract interactions
        edge_weights: dict[tuple[str, str, str], float] = {}

        # Precompile mention regex (@handle)
        mention_regex = re.compile(r"@([a-zA-Z0-9_]{3,32})")

        # Map platform_post_id to author_id for reply tracing
        post_author_map: dict[str, str] = {
            p.platform_post_id: p.author_id for p in posts if p.author_id
        }

        for p in posts:
            ch_id = p.channel_id
            author_id = p.author_id

            # Node: Author (if present)
            if author_id:
                if author_id not in G:
                    masked_label = self.mask_author_label(
                        author_id,
                        getattr(author_meta.get(author_id), "display_name", None),
                    )
                    G.add_node(
                        author_id,
                        entity_type="author",
                        label=masked_label,
                    )

                # Interaction: Author posting in channel
                edge_key = (author_id, ch_id, "post")
                edge_weights[edge_key] = edge_weights.get(edge_key, 0.0) + 1.0

            # Interaction: Forward (forward_from_id -> channel_id)
            if p.forward_from_id:
                fwd_src = p.forward_from_id
                if fwd_src not in G:
                    # Treat unknown forward source as channel if starts with @, else author
                    is_ch = fwd_src.startswith("@")
                    etype = "channel" if is_ch else "author"
                    lbl = fwd_src if is_ch else self.mask_author_label(fwd_src)
                    G.add_node(fwd_src, entity_type=etype, label=lbl)

                edge_key = (fwd_src, ch_id, "forward")
                edge_weights[edge_key] = edge_weights.get(edge_key, 0.0) + 1.0

            # Interaction: Reply (author_id -> replied_to_author or channel_id)
            if p.reply_to_id and author_id:
                target_author = post_author_map.get(p.reply_to_id)
                target_id = target_author if target_author else ch_id
                if target_id not in G:
                    is_ch = target_id.startswith("@")
                    etype = "channel" if is_ch else "author"
                    lbl = target_id if is_ch else self.mask_author_label(target_id)
                    G.add_node(target_id, entity_type=etype, label=lbl)

                edge_key = (author_id, target_id, "reply")
                edge_weights[edge_key] = edge_weights.get(edge_key, 0.0) + 1.0

            # Interaction: Mentions in text
            if p.content_text:
                mentions = mention_regex.findall(p.content_text)
                src = author_id if author_id else ch_id
                for m in set(mentions):
                    mentioned_ch = f"@{m}"
                    if mentioned_ch != ch_id:
                        if mentioned_ch not in G:
                            G.add_node(mentioned_ch, entity_type="channel", label=mentioned_ch)
                        edge_key = (src, mentioned_ch, "mention")
                        edge_weights[edge_key] = edge_weights.get(edge_key, 0.0) + 1.0

        # Add edges to NetworkX DiGraph
        for (src, tgt, itype), weight in edge_weights.items():
            if src != tgt:  # Avoid self-loops in interaction graph
                G.add_edge(src, tgt, interaction_type=itype, weight=weight)

        return G

    def prune_to_top_nodes(
        self,
        G: nx.DiGraph,
        betweenness_scores: dict[str, float] | None = None,
    ) -> nx.DiGraph:
        """Prune graph to top MAX_GRAPH_NODES by betweenness centrality with strictly induced edges.

        Args:
            G: Input directed graph.
            betweenness_scores: Precomputed betweenness centrality dictionary.

        Returns:
            Sub-graph induced on the top nodes.
        """
        if G.number_of_nodes() <= self.max_nodes:
            return G

        if betweenness_scores is None:
            betweenness_scores = nx.betweenness_centrality(G, weight="weight")

        # Sort nodes by betweenness descending
        sorted_nodes = sorted(
            betweenness_scores.items(), key=lambda kv: kv[1], reverse=True
        )
        top_nodes = [node_id for node_id, _ in sorted_nodes[: self.max_nodes]]

        # Induce subgraph strictly on top nodes
        return G.subgraph(top_nodes).copy()

    @staticmethod
    def to_undirected_weighted(G: nx.DiGraph) -> nx.Graph:
        """Project directed graph into an undirected graph with summed bidirectional weights.

        Required invariant for Louvain community modularity (which is mathematically
        undefined for directed graphs).
        """
        undirected_G = nx.Graph()

        # Copy nodes with attributes
        for n, data in G.nodes(data=True):
            undirected_G.add_node(n, **data)

        # Sum bidirectional edge weights
        for u, v, data in G.edges(data=True):
            w = float(data.get("weight", 1.0))
            if undirected_G.has_edge(u, v):
                undirected_G[u][v]["weight"] += w
            else:
                undirected_G.add_edge(u, v, weight=w)

        return undirected_G
