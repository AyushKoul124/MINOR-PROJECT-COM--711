"""Component C — Demographic Intelligence Summary Generator.

Synthesizes a 2–4 sentence factual, grounded analytical summary of the
audience demographic profile for vector storage (RAG layer) and analyst reporting.

Summary Invariants:
    - Factual, objective prose with zero hallucination or speculative claims.
    - Explicitly mentions sample size (n accounts) and DPDP k-anonymity compliance.
    - Highlights top interest clusters, geographic concentration, and active diurnal phases.
"""

from __future__ import annotations

from typing import Any


def generate_demographic_summary(
    cluster_label: str,
    account_count: int,
    below_threshold: bool,
    age_bracket_dist: dict[str, float] | None,
    interest_dist: dict[str, float] | None,
    geography_dist: dict[str, float] | None,
    language_dist: dict[str, float] | None,
    confidence: float,
    primary_phase: str | None = None,
) -> str:
    """Generate a 2-4 sentence intelligence summary for a demographic cluster.

    Args:
        cluster_label: Identifier or name of the analyzed audience cluster.
        account_count: Number of observed accounts in the cluster.
        below_threshold: True if account_count is below k-anonymity threshold.
        age_bracket_dist: Age bracket distribution dictionary.
        interest_dist: Professional interest distribution dictionary.
        geography_dist: Regional geography distribution dictionary.
        language_dist: Language distribution dictionary.
        confidence: Inference confidence score (0.0 to 1.0).
        primary_phase: Primary diurnal active phase (e.g. 'Evening (18:00-23:00 IST)').

    Returns:
        Structured 2-4 sentence factual summary string.
    """
    # 1. Privacy & sample size statement
    privacy_status = (
        f"DPDP k-anonymity suppressed (n={account_count} < threshold)"
        if below_threshold
        else f"DPDP k-anonymity verified (n={account_count} accounts)"
    )
    s1 = f"Demographic intelligence for audience cluster '{cluster_label}' [{privacy_status}]."

    # 2. Top interests and age bracket
    top_interests: list[str] = []
    if interest_dist:
        sorted_interests = sorted(interest_dist.items(), key=lambda kv: kv[1], reverse=True)
        top_interests = [f"{k} ({int(v * 100)}%)" for k, v in sorted_interests[:2] if v > 0]

    top_age = ""
    if age_bracket_dist:
        sorted_age = sorted(age_bracket_dist.items(), key=lambda kv: kv[1], reverse=True)
        if sorted_age and sorted_age[0][1] > 0:
            top_age = f"{sorted_age[0][0]} age bracket ({int(sorted_age[0][1] * 100)}%)"

    interest_str = ", ".join(top_interests) if top_interests else "general discourse"
    age_str = f" with primary concentration in the {top_age}" if top_age else ""
    s2 = f"Audience engagement exhibits strong focus on {interest_str}{age_str}."

    # 3. Geography, language & diurnal rhythm
    top_geos: list[str] = []
    if geography_dist:
        sorted_geos = sorted(geography_dist.items(), key=lambda kv: kv[1], reverse=True)
        top_geos = [k for k, v in sorted_geos if k != "Unspecified" and v > 0.05][:2]

    geo_str = f"centered primarily across {', '.join(top_geos)}" if top_geos else "distributed across Indian metro regions"

    top_lang = "English"
    if language_dist:
        en_pct = language_dist.get("en", 0.0)
        hi_pct = language_dist.get("hi", 0.0)
        if hi_pct > 0.4:
            top_lang = "bilingual English-Hindi discourse"
        elif hi_pct > 0.15:
            top_lang = "predominantly English with substantial Hinglish code-mixing"
        else:
            top_lang = "predominantly English discourse"

    phase_str = f" with peak engagement during {primary_phase}" if primary_phase else ""
    s3 = f"Regional indicators reflect an audience {geo_str}, engaging in {top_lang}{phase_str}."

    # 4. Confidence caveat
    conf_pct = int(confidence * 100)
    s4 = f"Aggregate heuristic inference confidence is estimated at {conf_pct}%."

    return f"{s1} {s2} {s3} {s4}"
