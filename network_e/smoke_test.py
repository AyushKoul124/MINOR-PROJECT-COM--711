"""Quick smoke test — verify Component E network graph analytics and 3-signal CIB screening.

Run:
    python -m network_e.smoke_test
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import networkx as nx

from network_e.agent import NetworkAgent, NetworkRunResult
from network_e.centrality import CentralityEngine
from network_e.cib_signals import CIBDetector
from network_e.community import CommunityDetector
from network_e.graph_builder import GraphBuilder
from network_e.summary import generate_network_summary
from storage.models.raw import RawAuthor, RawPost


def _create_mock_post(
    id: int,
    channel_id: str,
    channel_title: str,
    author_id: str | None,
    content: str,
    posted_at: datetime,
    forward_from_chat_id: str | None = None,
    reply_to_msg_id: int | None = None,
) -> RawPost:
    post = MagicMock(spec=RawPost)
    post.id = id
    post.platform = "telegram"
    post.platform_post_id = str(id)
    post.channel_id = channel_id
    post.author_id = author_id
    post.content_text = content
    post.posted_at = posted_at
    post.forward_from_id = forward_from_chat_id
    post.reply_to_id = str(reply_to_msg_id) if reply_to_msg_id is not None else None
    return post


def _create_mock_author(
    id: int,
    platform_author_id: str,
    username: str | None = None,
    display_name: str | None = None,
    account_created_at: datetime | None = None,
) -> RawAuthor:
    author = MagicMock(spec=RawAuthor)
    author.id = id
    author.platform_author_id = platform_author_id
    author.username = username
    author.display_name = display_name
    author.account_created_at = account_created_at
    return author


def test_graph_builder_and_masking() -> None:
    print("[1/5] Testing GraphBuilder and Privacy Masking...")
    builder = GraphBuilder(max_nodes=500)

    now = datetime.now(timezone.utc)
    authors = [
        _create_mock_author(1, "123456789", "rahul_defense", "Rahul Sharma"),
        _create_mock_author(2, "987654321", "isro_tracker", "ISRO Analyst"),
    ]

    posts = [
        _create_mock_post(
            1, "@isro_updates", "ISRO Official Updates", "123456789",
            "Gaganyaan abort test success.", now - timedelta(hours=2)
        ),
        _create_mock_post(
            2, "@isro_updates", "ISRO Official Updates", "987654321",
            "Telemetry confirmed from Sriharikota.", now - timedelta(hours=1),
            reply_to_msg_id=1
        ),
        _create_mock_post(
            3, "@defense_talk", "Indian Defense News", "987654321",
            "Forwarded payload data.", now - timedelta(minutes=30),
            forward_from_chat_id="@isro_updates"
        ),
    ]

    G = builder.build_interaction_graph(posts, authors)
    assert G.number_of_nodes() >= 3, f"Expected at least 3 nodes, got {G.number_of_nodes()}"

    # Verify DPDP privacy masking on authors
    for node_id, data in G.nodes(data=True):
        if data.get("entity_type") == "author":
            label = data.get("label", "")
            assert label.startswith("Actor-[Masked]-"), (
                f"Author label '{label}' violates DPDP pseudonymisation invariant!"
            )
            assert len(label) == 19  # 'Actor-[Masked]-' (15 chars) + 4 hex chars = 19
        elif data.get("entity_type") == "channel":
            # Channels retain public names
            assert "@isro_updates" in [d.get("label") for _, d in G.nodes(data=True)]

    # Test undirected projection with summed weights
    undirected = builder.to_undirected_weighted(G)
    assert not undirected.is_directed()
    print("  ✓ Graph builder, privacy masking, and undirected projection verified.")


def test_centrality_and_louvain() -> None:
    print("[2/5] Testing CentralityEngine and Louvain Community Detection...")
    centrality_engine = CentralityEngine()
    community_detector = CommunityDetector()

    # Create a small kite network to verify hub/broker distinction
    # Kite graph: 0-1-2-3 (clique) with 3 connected to 4, 4 to 5 (broker)
    G = nx.Graph()
    # Cluster A
    G.add_edge("ch_1", "ch_2", weight=2.0)
    G.add_edge("ch_2", "ch_3", weight=2.0)
    G.add_edge("ch_1", "ch_3", weight=2.0)
    # Bridge / Broker node
    G.add_edge("ch_3", "broker_actor", weight=1.0)
    G.add_edge("broker_actor", "ch_4", weight=1.0)
    # Cluster B
    G.add_edge("ch_4", "ch_5", weight=2.0)
    G.add_edge("ch_5", "ch_6", weight=2.0)
    G.add_edge("ch_4", "ch_6", weight=2.0)

    scores = centrality_engine.compute_all(G)
    assert "broker_actor" in scores
    assert scores["broker_actor"].betweenness_centrality > scores["ch_1"].betweenness_centrality, (
        "Bridge node should have higher betweenness centrality than cluster peripheral node."
    )

    part = community_detector.detect_communities(G)
    assert part.total_communities >= 2, f"Expected >= 2 communities, got {part.total_communities}"
    assert -0.5 <= part.modularity <= 1.0, f"Modularity out of range: {part.modularity}"
    assert len(part.node_communities) == 7
    print(f"  ✓ Centrality and Louvain modularity (Q={part.modularity:.4f}, {part.total_communities} communities) verified.")


def test_cib_3_signals() -> None:
    print("[3/5] Testing 3-Signal Advisory CIB Detector...")
    detector = CIBDetector(anomaly_threshold=0.70)
    now = datetime.now(timezone.utc)

    # 1. Normal actor: spaced posts, old account, unique content
    normal_posts = [
        _create_mock_post(1, "ch_1", "News", "author_normal", "Discussion on rocket fuel types.", now - timedelta(hours=20)),
        _create_mock_post(2, "ch_1", "News", "author_normal", "Cryogenic upper stage specs.", now - timedelta(hours=10)),
        _create_mock_post(3, "ch_2", "Defense", "author_normal", "Budget allocation for space startups.", now - timedelta(hours=2)),
    ]
    normal_author = _create_mock_author(10, "author_normal", account_created_at=now - timedelta(days=200))

    res_normal = detector.compute_signals(
        entity_id="author_normal",
        entity_type="author",
        entity_posts=normal_posts,
        all_posts=normal_posts,
        author_meta=normal_author,
    )
    assert res_normal.anomaly_score < 0.70, f"Normal actor falsely flagged: {res_normal.anomaly_score}"
    assert res_normal.coordination_signal is False

    # 2. Coordinated Bot: high synchrony (<60s gap), new account (<7 days), duplicate copy-paste
    spam_text = "BREAKING: Secret radar base spotted in Himalayas! Check link http://spam.xyz"
    bot_posts = [
        _create_mock_post(101, "ch_1", "News", "author_bot", spam_text, now - timedelta(minutes=10, seconds=5)),
        _create_mock_post(102, "ch_2", "Defense", "author_bot", spam_text, now - timedelta(minutes=10)),
        _create_mock_post(103, "ch_3", "Tech", "author_bot", spam_text, now - timedelta(minutes=9, seconds=50)),
        _create_mock_post(104, "ch_4", "Policy", "author_bot", spam_text, now - timedelta(minutes=9, seconds=40)),
    ]
    all_swarm_posts = list(bot_posts)
    # Add identical duplicate post from a confederate
    all_swarm_posts.append(
        _create_mock_post(105, "ch_5", "General", "author_bot2", spam_text, now - timedelta(minutes=9, seconds=35))
    )

    new_bot_author = _create_mock_author(11, "author_bot", account_created_at=now - timedelta(days=2))

    res_bot = detector.compute_signals(
        entity_id="author_bot",
        entity_type="author",
        entity_posts=bot_posts,
        all_posts=all_swarm_posts,
        author_meta=new_bot_author,
    )

    assert res_bot.posting_synchrony_signal > 0.50, f"Synchrony signal too low: {res_bot.posting_synchrony_signal}"
    assert res_bot.age_volume_signal > 0.50, f"Age-volume signal too low: {res_bot.age_volume_signal}"
    assert res_bot.duplicate_content_signal > 0.50, f"Duplicate signal too low: {res_bot.duplicate_content_signal}"
    assert res_bot.anomaly_score >= 0.70, f"Expected anomaly >= 0.70, got {res_bot.anomaly_score}"
    assert res_bot.coordination_signal is True, "Bot should have coordination_signal=True"

    # Verify arithmetic mean invariance
    expected_composite = round(
        (res_bot.posting_synchrony_signal + res_bot.age_volume_signal + res_bot.duplicate_content_signal) / 3.0, 4
    )
    assert abs(res_bot.anomaly_score - expected_composite) < 1e-4, "Composite score must be unweighted mean"
    print(f"  ✓ CIB 3-signal detection verified (Normal: {res_normal.anomaly_score:.2f}, Bot: {res_bot.anomaly_score:.2f} flagged={res_bot.coordination_signal}).")


def test_summary_generation() -> None:
    print("[4/5] Testing Intelligence Summary Generation...")
    summary = generate_network_summary(
        total_nodes=45,
        total_edges=112,
        total_communities=4,
        modularity=0.6421,
        flagged_entities=[{"label": "Actor-[Masked]-a1b2", "anomaly_score": 0.88}],
        top_broker_labels=["Actor-[Masked]-c3d4", "ISRO Official Updates"],
    )
    assert "45 entities" in summary
    assert "112 directed interactions" in summary
    assert "4 Louvain behavioral communities" in summary
    assert "0.64" in summary
    assert "Actor-[Masked]-a1b2" in summary
    assert len(summary.split(". ")) >= 2, "Summary should be at least 2 sentences"
    print("  ✓ Intelligence summary generation verified.")


def test_network_agent_end_to_end() -> None:
    print("[5/5] Testing NetworkAgent end-to-end in-memory analysis...")
    agent = NetworkAgent(max_nodes=100, cib_threshold=0.70)
    now = datetime.now(timezone.utc)

    authors = [
        _create_mock_author(1, "auth_1", account_created_at=now - timedelta(days=100)),
        _create_mock_author(2, "auth_2", account_created_at=now - timedelta(days=5)),
    ]

    posts = [
        _create_mock_post(1, "ch_isro", "ISRO Feed", "auth_1", "Cryogenic stage static fire complete.", now - timedelta(hours=6)),
        _create_mock_post(2, "ch_defense", "Defense News", "auth_1", "Strategic radar deployment.", now - timedelta(hours=5)),
        _create_mock_post(3, "ch_defense", "Defense News", "auth_2", "Strategic radar deployment copy.", now - timedelta(hours=5, seconds=10)),
        _create_mock_post(4, "ch_isro", "ISRO Feed", "auth_2", "Cryogenic stage static fire complete.", now - timedelta(hours=4)),
    ]

    result: NetworkRunResult = agent.analyze_network(posts=posts, authors=authors)
    assert len(result.nodes) > 0
    assert len(result.edges) > 0
    assert result.summary != ""
    assert result.community_result.total_communities >= 1

    payload = result.to_webgl_payload()
    assert "nodes" in payload
    assert "links" in payload
    assert "modularity" in payload
    assert len(payload["nodes"]) == len(result.nodes)
    assert len(payload["links"]) == len(result.edges)

    # Verify node structure for react-force-graph-2d
    first_node = payload["nodes"][0]
    for key in ("id", "label", "entity_type", "community_id", "betweenness", "degree", "anomaly_score", "coordination_signal"):
        assert key in first_node, f"Missing key in WebGL node payload: {key}"

    print(f"  ✓ NetworkAgent end-to-end analysis succeeded: {len(result.nodes)} nodes, {len(result.edges)} edges.")


def main() -> None:
    print("=" * 65)
    print("Component E (Network & CIB Screening) Smoke Test Suite")
    print("=" * 65)
    test_graph_builder_and_masking()
    test_centrality_and_louvain()
    test_cib_3_signals()
    test_summary_generation()
    test_network_agent_end_to_end()
    print("=" * 65)
    print("ALL 5 TESTS PASSED SUCCESSFULLY! Component E is healthy.")
    print("=" * 65)


if __name__ == "__main__":
    main()
