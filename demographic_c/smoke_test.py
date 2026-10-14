"""Quick smoke test — verify Component C demographic profiling and k-anonymity.

Run:
    python -m demographic_c.smoke_test
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from demographic_c.agent import DemographicAgent
from demographic_c.bio_parser import AuthorProfileInput, BioParser
from demographic_c.cluster_guard import ClusterGuard
from demographic_c.pattern_analyzer import PatternAnalyzer
from demographic_c.summary import generate_demographic_summary


def test_cluster_guard() -> None:
    print("[1/5] Testing ClusterGuard k-anonymity checks...")
    guard_prod = ClusterGuard(min_cluster_size=50)
    assert guard_prod.is_below_threshold(12) is True, "Expected n=12 to be below k=50"
    assert guard_prod.is_below_threshold(50) is False, "Expected n=50 to meet k=50"
    assert guard_prod.is_below_threshold(150) is False, "Expected n=150 to meet k=50"

    assessment_small = guard_prod.assess(8)
    assert assessment_small.below_threshold is True
    assert "SUPPRESSED" in assessment_small.status_label

    guard_demo = ClusterGuard(min_cluster_size=15)
    assert guard_demo.is_below_threshold(20) is False, "Expected n=20 to pass demo k=15"
    print("      ✓ ClusterGuard correctly enforces k >= 50 and demo k >= 15.")


def test_bio_parser() -> None:
    print("[2/5] Testing BioParser heuristic extraction...")
    parser = BioParser()

    sample_profiles = [
        AuthorProfileInput(
            author_id="u1",
            display_name="Aarav Sharma",
            bio_text="Aerospace engineer & space policy enthusiast | Bengaluru",
        ),
        AuthorProfileInput(
            author_id="u2",
            display_name="Vikramaditya",
            bio_text="Defense analyst, ex-IAF enthusiast. Tracking indigenization | New Delhi",
        ),
        AuthorProfileInput(
            author_id="u3",
            display_name="Priya_Tech",
            bio_text="VLSI designer, semiconductor policy watcher | Hyderabad",
        ),
        AuthorProfileInput(
            author_id="u4",
            display_name="Sanjay Verma",
            bio_text="Geopolitics scholar, maritime strategist | Mumbai",
        ),
        AuthorProfileInput(
            author_id="u5",
            display_name="Rohan_K",
            bio_text="ISRO watcher, astrophysics student | Chennai",
        ),
        AuthorProfileInput(
            author_id="u6",
            display_name="DesiStrategist",
            bio_text="Senior strategist tracking South Asian deterrence and nuclear policy | Delhi NCR",
        ),
    ]

    result = parser.aggregate_profiles(sample_profiles)
    assert result.total_authors_analyzed == 6
    assert result.authors_with_bio_count == 6
    assert 0.0 < result.inference_confidence <= 1.0

    # Check distributions sum to 1.0 (approximate float sum)
    assert abs(sum(result.age_bracket_dist.values()) - 1.0) < 0.01
    assert abs(sum(result.interest_dist.values()) - 1.0) < 0.01
    assert abs(sum(result.geography_dist.values()) - 1.0) < 0.01
    assert abs(sum(result.language_dist.values()) - 1.0) < 0.01

    print(f"      ✓ Parsed {len(sample_profiles)} bios:")
    print(f"        - Top interest: {max(result.interest_dist, key=result.interest_dist.get)}")
    print(f"        - Top region:   {max(result.geography_dist, key=result.geography_dist.get)}")
    print(f"        - Confidence:   {result.inference_confidence:.2f}")


def test_pattern_analyzer() -> None:
    print("[3/5] Testing PatternAnalyzer diurnal rhythm extraction...")
    analyzer = PatternAnalyzer()

    # Create synthetic UTC timestamps corresponding to daytime in India (05:00-14:00 UTC = 10:30-19:30 IST)
    now = datetime.now(timezone.utc)
    base_ts = now.replace(hour=8, minute=0, second=0, microsecond=0)
    timestamps = [base_ts + timedelta(hours=i) for i in range(10)]

    rhythm = analyzer.analyze_timestamps(timestamps)
    assert rhythm.total_posts_analyzed == 10
    assert len(rhythm.peak_hours_ist) > 0
    assert rhythm.ist_alignment_score > 0.7

    print(f"      ✓ Diurnal rhythm identified:")
    print(f"        - Primary phase: {rhythm.primary_active_phase}")
    print(f"        - Peak IST hours: {rhythm.peak_hours_ist}")
    print(f"        - IST alignment: {rhythm.ist_alignment_score * 100:.1f}%")


def test_summary_generation() -> None:
    print("[4/5] Testing Summary Generator...")
    summary = generate_demographic_summary(
        cluster_label="Indian Space & Defense Audience",
        account_count=65,
        below_threshold=False,
        age_bracket_dist={"25-34": 0.55, "35-49": 0.30, "18-24": 0.15},
        interest_dist={"Aerospace & Space": 0.50, "Defense & Military": 0.35},
        geography_dist={"South India": 0.40, "North India": 0.35},
        language_dist={"en": 0.80, "hi": 0.20},
        confidence=0.82,
        primary_phase="Afternoon (12:00-18:00 IST)",
    )
    assert "Indian Space & Defense Audience" in summary
    assert "DPDP k-anonymity verified" in summary
    assert len(summary.split(".")) >= 3
    print("      ✓ Generated summary:")
    print(f"        \"{summary[:120]}...\"")


def test_demographic_agent_cohort() -> None:
    print("[5/5] Testing DemographicAgent end-to-end cohort profiling...")
    agent = DemographicAgent(min_cluster_size=50)

    # Sub-threshold test cohort (n=6 < 50)
    authors = [
        AuthorProfileInput("u1", "Aarav", "Aerospace engineer at Bengaluru"),
        AuthorProfileInput("u2", "Vikram", "Defense watcher in Delhi"),
        AuthorProfileInput("u3", "Priya", "Semiconductor designer in Hyderabad"),
    ]

    now = datetime.now(timezone.utc)
    res_sub = agent.profile_cohort(
        cluster_label="Test Sub-Threshold Cluster",
        authors=authors,
        posts=[],
        window_start=now - timedelta(hours=48),
        window_end=now,
    )

    assert res_sub.below_threshold is True
    assert res_sub.account_count == 3
    assert "suppressed" in res_sub.summary.lower()

    # Compliant test cohort (n=60 >= 50)
    compliant_authors = [
        AuthorProfileInput(f"user_{i}", f"User {i}", "Space & defense researcher")
        for i in range(60)
    ]
    res_compliant = agent.profile_cohort(
        cluster_label="Test Compliant Cluster",
        authors=compliant_authors,
        posts=[],
        window_start=now - timedelta(hours=48),
        window_end=now,
    )

    assert res_compliant.below_threshold is False
    assert res_compliant.account_count == 60
    assert "verified" in res_compliant.summary.lower()

    print("      ✓ DemographicAgent end-to-end cohort profiling passed.")
    print("        - Sub-threshold n=3 correctly sets below_threshold=True.")
    print("        - Compliant n=60 correctly sets below_threshold=False.")


if __name__ == "__main__":
    print("\n=======================================================")
    print("   COMPONENT C (DEMOGRAPHIC AGENT) SMOKE TEST")
    print("=======================================================\n")
    test_cluster_guard()
    test_bio_parser()
    test_pattern_analyzer()
    test_summary_generation()
    test_demographic_agent_cohort()
    print("\n✓ ALL 5 COMPONENT C SMOKE TESTS PASSED SUCCESSFULLY!\n")
