"""Component E — Network Interaction & CIB Intelligence Summary Generator.

Synthesizes a 2–4 sentence factual, grounded analytical summary of network
topology, Louvain communities, and CIB anomaly screening signals for RAG
indexing and intelligence reporting.
"""

from __future__ import annotations

from typing import Any


def generate_network_summary(
    total_nodes: int,
    total_edges: int,
    total_communities: int,
    modularity: float,
    flagged_entities: list[dict[str, Any]],
    top_broker_labels: list[str],
) -> str:
    """Generate a 2-4 sentence factual intelligence summary for network & CIB analysis.

    Args:
        total_nodes: Number of entities in the interaction network.
        total_edges: Number of interaction edges (replies, forwards, mentions).
        total_communities: Count of behavioral sub-communities detected via Louvain.
        modularity: Louvain modularity score Q.
        flagged_entities: List of entity dicts with anomaly_score >= threshold.
        top_broker_labels: Labels of entities with highest betweenness centrality.

    Returns:
        Structured 2-4 sentence factual summary string.
    """
    if total_nodes == 0:
        return "Network analysis observed zero interaction edges across the observation window."

    # 1. Network topology statement
    brokers_str = ", ".join(top_broker_labels[:2]) if top_broker_labels else "primary broadcast channels"
    s1 = (
        f"Interaction network analysis evaluated {total_nodes} entities and {total_edges} directed interactions, "
        f"identifying {total_communities} Louvain behavioral communities (modularity Q={modularity:.2f}). "
        f"Key structural bridging brokers include {brokers_str}."
    )

    # 2. CIB Anomaly screening statement
    n_flagged = len(flagged_entities)
    if n_flagged > 0:
        highest = max(flagged_entities, key=lambda x: x.get("anomaly_score", 0.0))
        highest_score = highest.get("anomaly_score", 0.0)
        highest_label = highest.get("label", "Unknown")
        s2 = (
            f"Advisory CIB screening flagged {n_flagged} entities exhibiting anomalous behavioral coordination "
            f"(composite anomaly score >= 0.70, peak anomaly score: {highest_score:.2f} on {highest_label})."
        )
    else:
        s2 = "Advisory CIB screening detected no coordinated inauthentic behavioral clusters meeting the 0.70 anomaly threshold."

    # 3. Compliance and disclaimer statement
    s3 = (
        "Entity labels preserve analyst privacy via pseudonymization, and anomaly scores represent "
        "probabilistic screening signals rather than legal attribution verdicts."
    )

    return f"{s1} {s2} {s3}"
