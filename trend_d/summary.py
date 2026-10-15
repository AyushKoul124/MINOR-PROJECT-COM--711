"""Component D — Trend & Velocity Intelligence Summary Generator.

Synthesizes a 2–4 sentence factual, grounded analytical summary of discovered
topics, hourly velocity rankings, and accelerating narrative bursts for RAG
vectorization and intelligence dashboards.
"""

from __future__ import annotations

from trend_d.velocity import TopicVelocityMetrics


def generate_trend_summary(
    ranked_topics: list[TopicVelocityMetrics],
    window_hours: float,
    total_posts: int,
) -> str:
    """Generate a 2-4 sentence factual analytical summary for trend topics.

    Args:
        ranked_topics: List of TopicVelocityMetrics sorted by velocity descending.
        window_hours: Duration of observation window in hours (e.g. 48.0).
        total_posts: Total number of posts analyzed in the window.

    Returns:
        Structured 2-4 sentence intelligence summary string.
    """
    if not ranked_topics:
        return (
            f"Trend analysis across the trailing {int(window_hours)}-hour window evaluated "
            f"{total_posts} public posts. No statistically significant topic clusters or "
            "narrative velocity surges were detected."
        )

    # 1. Macro scope
    s1 = (
        f"Topic discovery over the trailing {int(window_hours)}-hour observation window "
        f"clustered {total_posts} posts into {len(ranked_topics)} primary narrative threads."
    )

    # 2. Leading topic by velocity
    top_topic = ranked_topics[0]
    s2 = (
        f"The leading discourse topic is '{top_topic.topic_label}' with {top_topic.post_count} posts "
        f"at a velocity of {top_topic.velocity:.2f} posts/hour."
    )

    # 3. Surging / accelerating topic
    surging_candidates = [t for t in ranked_topics if t.is_surging]
    if surging_candidates:
        fastest = max(surging_candidates, key=lambda t: t.acceleration)
        s3 = (
            f"The most rapidly accelerating narrative is '{fastest.topic_label}' "
            f"exhibiting an acceleration rate of +{fastest.acceleration:.3f} posts/hr²."
        )
    else:
        # Check secondary rank
        if len(ranked_topics) > 1:
            second_topic = ranked_topics[1]
            s3 = (
                f"Secondary active discourse focuses on '{second_topic.topic_label}' "
                f"({second_topic.post_count} posts, {second_topic.velocity:.2f} posts/hr)."
            )
        else:
            s3 = "Narrative momentum remains steady across the evaluated temporal window."

    # 4. Invariant statement
    s4 = "All velocity and acceleration metrics are anchored to platform message creation timestamps."

    return f"{s1} {s2} {s3} {s4}"
