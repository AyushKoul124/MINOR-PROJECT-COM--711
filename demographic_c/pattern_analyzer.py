"""Component C — Temporal Diurnal Rhythm and Posting Pattern Analyzer.

Analyzes message and comment publishing schedules to extract diurnal posting
patterns, active hours, and timezone indicators.

Critical Invariant:
    - ALWAYS anchors calculations strictly to platform ``raw_posts.posted_at``
      UTC timestamps.
    - NEVER uses ``ingested_at`` (which reflects scraper polling lag).
    - Maps UTC timestamps to Indian Standard Time (IST, UTC+05:30) for localized
      audience behavior interpretation.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

IST_OFFSET = timedelta(hours=5, minutes=30)


@dataclass
class DiurnalRhythmResult:
    """Temporal diurnal rhythm profile for an audience or channel."""

    total_posts_analyzed: int
    hourly_distribution_ist: dict[int, int]
    hourly_percentages_ist: dict[int, float]
    phase_distribution: dict[str, float]
    peak_hours_ist: list[int]
    primary_active_phase: str
    ist_alignment_score: float  # High if posting drops during 01:00-05:00 IST (natural sleep cycle)


class PatternAnalyzer:
    """Analyzes temporal rhythms and diurnal phases from message timestamps."""

    DIURNAL_PHASES = {
        "Morning (06:00-12:00 IST)": (6, 12),
        "Afternoon (12:00-18:00 IST)": (12, 18),
        "Evening (18:00-23:00 IST)": (18, 23),
        "Night (23:00-06:00 IST)": (23, 6),
    }

    def analyze_timestamps(self, timestamps: list[datetime]) -> DiurnalRhythmResult:
        """Analyze a list of UTC datetime timestamps into diurnal rhythm metrics.

        Args:
            timestamps: List of datetime objects (assumed UTC if tz-aware or naive).

        Returns:
            DiurnalRhythmResult with hourly IST distributions and diurnal phases.
        """
        valid_ts = [ts for ts in timestamps if ts is not None]
        total = len(valid_ts)
        if total == 0:
            return self._empty_result()

        ist_hours: list[int] = []
        for ts in valid_ts:
            if ts.tzinfo is None:
                utc_dt = ts.replace(tzinfo=timezone.utc)
            else:
                utc_dt = ts.astimezone(timezone.utc)
            ist_dt = utc_dt + IST_OFFSET
            ist_hours.append(ist_dt.hour)

        hour_counter = Counter(ist_hours)
        hourly_dist = {h: hour_counter.get(h, 0) for h in range(24)}
        hourly_pct = {h: round(hourly_dist[h] / total, 4) for h in range(24)}

        # Phase distribution
        phase_counts: dict[str, int] = {p: 0 for p in self.DIURNAL_PHASES}
        for h, count in hourly_dist.items():
            if 6 <= h < 12:
                phase_counts["Morning (06:00-12:00 IST)"] += count
            elif 12 <= h < 18:
                phase_counts["Afternoon (12:00-18:00 IST)"] += count
            elif 18 <= h < 23:
                phase_counts["Evening (18:00-23:00 IST)"] += count
            else:
                phase_counts["Night (23:00-06:00 IST)"] += count

        phase_pct = {p: round(c / total, 4) for p, c in phase_counts.items()}
        primary_phase = max(phase_pct, key=lambda k: phase_pct[k])

        # Top 3 peak hours
        sorted_hours = sorted(hourly_dist.items(), key=lambda kv: kv[1], reverse=True)
        peak_hours = [h for h, c in sorted_hours[:3] if c > 0]

        # IST alignment score: proportion of posts during daytime/waking hours (07:00-24:00 IST)
        waking_count = sum(hourly_dist[h] for h in range(7, 24))
        ist_alignment = round(waking_count / total, 3)

        return DiurnalRhythmResult(
            total_posts_analyzed=total,
            hourly_distribution_ist=hourly_dist,
            hourly_percentages_ist=hourly_pct,
            phase_distribution=phase_pct,
            peak_hours_ist=peak_hours,
            primary_active_phase=primary_phase,
            ist_alignment_score=ist_alignment,
        )

    @staticmethod
    def _empty_result() -> DiurnalRhythmResult:
        """Return an empty default rhythm profile."""
        return DiurnalRhythmResult(
            total_posts_analyzed=0,
            hourly_distribution_ist={h: 0 for h in range(24)},
            hourly_percentages_ist={h: 0.0 for h in range(24)},
            phase_distribution={
                "Morning (06:00-12:00 IST)": 0.25,
                "Afternoon (12:00-18:00 IST)": 0.25,
                "Evening (18:00-23:00 IST)": 0.25,
                "Night (23:00-06:00 IST)": 0.25,
            },
            peak_hours_ist=[],
            primary_active_phase="Afternoon (12:00-18:00 IST)",
            ist_alignment_score=0.5,
        )
