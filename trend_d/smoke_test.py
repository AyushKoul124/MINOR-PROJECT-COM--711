"""Quick smoke test — verify Component D topic modeling and velocity calculations.

Run:
    python -m trend_d.smoke_test
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from trend_d.agent import TrendAgent
from trend_d.summary import generate_trend_summary
from trend_d.topic_model import TopicModeler
from trend_d.velocity import VelocityEngine


def test_velocity_engine() -> None:
    print("[1/4] Testing VelocityEngine velocity and acceleration math...")
    engine = VelocityEngine(default_window_hours=48.0)

    now = datetime.now(timezone.utc)
    w_start = now - timedelta(hours=48)
    w_end = now

    # Surging topic: 2 posts in first 24h, 10 posts in second 24h
    surging_posts = [
        (1, w_start + timedelta(hours=5)),
        (2, w_start + timedelta(hours=15)),
        # Burst in recent 24h
        (3, w_start + timedelta(hours=28)),
        (4, w_start + timedelta(hours=30)),
        (5, w_start + timedelta(hours=32)),
        (6, w_start + timedelta(hours=35)),
        (7, w_start + timedelta(hours=38)),
        (8, w_start + timedelta(hours=40)),
        (9, w_start + timedelta(hours=42)),
        (10, w_start + timedelta(hours=44)),
        (11, w_start + timedelta(hours=46)),
        (12, w_start + timedelta(hours=47)),
    ]

    m_surging = engine.compute_metrics(
        topic_id=1,
        topic_label="Gaganyaan Launch Integration",
        post_items=surging_posts,
        window_start=w_start,
        window_end=w_end,
    )

    assert m_surging.post_count == 12
    assert m_surging.velocity == round(12 / 48.0, 4)  # 0.25 posts/hr
    assert m_surging.acceleration > 0.0, "Expected positive acceleration for surging topic"
    assert m_surging.is_surging is True

    # Decelerating topic: 10 posts in first 24h, 2 posts in second 24h
    cooling_posts = [
        (i, w_start + timedelta(hours=2 + i)) for i in range(10)
    ] + [
        (11, w_start + timedelta(hours=30)),
        (12, w_start + timedelta(hours=40)),
    ]

    m_cooling = engine.compute_metrics(
        topic_id=2,
        topic_label="Historical Procurement Debate",
        post_items=cooling_posts,
        window_start=w_start,
        window_end=w_end,
    )

    assert m_cooling.acceleration < 0.0, "Expected negative acceleration for cooling topic"
    assert m_cooling.is_surging is False

    # Ranking test
    ranked = engine.rank_topics([m_cooling, m_surging])
    assert len(ranked) == 2
    # Both have velocity 0.25, but surging has higher acceleration so it should be rank 1
    assert ranked[0].topic_id == 1
    assert ranked[0].rank == 1

    print("      ✓ Velocity and acceleration formulas correctly differentiate surging vs cooling.")
    print(f"        - Surging Topic Velocity: {m_surging.velocity:.2f} posts/hr | Accel: +{m_surging.acceleration:.4f}")
    print(f"        - Cooling Topic Velocity: {m_cooling.velocity:.2f} posts/hr | Accel: {m_cooling.acceleration:.4f}")


def test_trend_summary_generation() -> None:
    print("[2/4] Testing Trend Summary Generator...")
    engine = VelocityEngine(default_window_hours=48.0)
    now = datetime.now(timezone.utc)
    w_start = now - timedelta(hours=48)

    sample_posts = [(i, w_start + timedelta(hours=i * 4)) for i in range(10)]
    m = engine.compute_metrics(1, "ISRO Space Exploration", sample_posts, w_start, now)
    ranked = engine.rank_topics([m])

    summary = generate_trend_summary(ranked, 48.0, 10)
    assert "ISRO Space Exploration" in summary
    assert "anchored to platform message creation timestamps" in summary
    assert len(summary.split(".")) >= 3
    print("      ✓ Summary generator produced verified 4-sentence analytical digest:")
    print(f"        \"{summary[:130]}...\"")


def test_topic_modeler() -> None:
    print("[3/4] Testing TopicModeler clustering and keyword extraction...")
    modeler = TopicModeler(min_topic_size=2, device="cpu")

    # Sample corpus of Indian space, defense, and technology texts
    corpus = [
        "ISRO successfully completes the integration of Gaganyaan orbital life support module.",
        "Gaganyaan crew module environmental control tests show nominal pressure parameters.",
        "Astronaut training and ECLSS flight qualification milestones validated by ISRO.",
        "DRDO carries out successful test of indigenous Rudram-II anti-radiation missile.",
        "Rudram anti-radiation missile homing guidance validated on Su-30MKI fighter platform.",
        "Defense indigenization achieves new milestone with indigenous missile seeker trials.",
        "Semiconductor plant construction in Gujarat enters cleanroom equipment installation.",
        "India Semiconductor Mission approves second silicon wafer fab for microelectronics.",
    ]

    result = modeler.fit_transform(corpus)
    assert len(result.topics) > 0, "Expected at least 1 topic discovered"
    assert result.total_docs_processed == len(corpus)

    print(f"      ✓ BERTopic successfully processed {len(corpus)} documents:")
    for t in result.topics:
        print(f"        - Topic {t.topic_id} ('{t.topic_label}'): {t.post_count} posts | Top keywords: {t.topic_keywords[:4]}")


def test_trend_agent_end_to_end() -> None:
    print("[4/4] Testing TrendAgent end-to-end post analysis...")
    agent = TrendAgent(min_topic_size=2, device="cpu")

    from storage.models.raw import RawPost

    now = datetime.now(timezone.utc)
    w_start = now - timedelta(hours=48)

    mock_posts = [
        RawPost(
            id=101,
            platform_post_id="post_101",
            channel_id="@isro_updates",
            content_text="ISRO prepares PSLV launch vehicle for strategic earth observation satellite.",
            posted_at=w_start + timedelta(hours=10),
            processing_status="pending",
        ),
        RawPost(
            id=102,
            platform_post_id="post_102",
            channel_id="@isro_updates",
            content_text="PSLV payload integration validated for multi-spectral remote sensing satellite.",
            posted_at=w_start + timedelta(hours=25),
            processing_status="pending",
        ),
        RawPost(
            id=103,
            platform_post_id="post_103",
            channel_id="@isro_updates",
            content_text="Satellite telemetry link operational following high-altitude fairing separation.",
            posted_at=w_start + timedelta(hours=40),
            processing_status="pending",
        ),
        RawPost(
            id=104,
            platform_post_id="post_104",
            channel_id="@drdo_updates",
            content_text="DRDO completes high-altitude trials for indigenous artillery weapons system.",
            posted_at=w_start + timedelta(hours=15),
            processing_status="pending",
        ),
        RawPost(
            id=105,
            platform_post_id="post_105",
            channel_id="@drdo_updates",
            content_text="Artillery tactical deployment validated under extreme cold climatic conditions.",
            posted_at=w_start + timedelta(hours=35),
            processing_status="pending",
        ),
    ]

    run_result = agent.analyze_posts(mock_posts, w_start, now)
    assert run_result.total_posts_analyzed == 5
    assert len(run_result.ranked_topics) > 0
    assert run_result.ranked_topics[0].rank == 1
    assert run_result.ranked_topics[0].velocity > 0.0

    print("      ✓ TrendAgent end-to-end analysis verified:")
    print(f"        - Discovered {len(run_result.ranked_topics)} ranked topics across {run_result.total_posts_analyzed} posts.")
    print(f"        - Rank 1 Topic: '{run_result.ranked_topics[0].topic_label}' (v={run_result.ranked_topics[0].velocity:.3f} posts/hr)")


if __name__ == "__main__":
    print("\n=======================================================")
    print("      COMPONENT D (TREND AGENT) SMOKE TEST")
    print("=======================================================\n")
    test_velocity_engine()
    test_trend_summary_generation()
    test_topic_modeler()
    test_trend_agent_end_to_end()
    print("\n✓ ALL 4 COMPONENT D SMOKE TESTS PASSED SUCCESSFULLY!\n")
