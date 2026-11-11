"""Component B — reaction heuristic for Telegram emoji reactions.

Scores ``raw_posts.reaction_counts`` (the reaction bar under a post).
This is separate from the text classifier. It never changes ``valence``.

Unmapped emoji, including ones the HTML export stored as ``?``, count as
``other`` and do not pull the score positive or negative.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# Polarity of common Telegram reaction emoji. Ambiguous marks (👀 🤯 🗿)
# are left unmapped on purpose.
_POSITIVE = frozenset({
    "👍", "🔥", "🎯", "💪", "🤣", "😂", "🇮🇳", "❤", "❤️", "♥",
    "❤‍🔥", "❤️‍🔥", "💡", "🚀", "👏", "💯", "😁", "👌", "😍", "🫡",
    "🤩", "🙏", "🎉", "🥰", "😎", "🙌", "✨", "💖", "🏆", "😘",
    "🤝", "😇", "🤗", "💘", "💋", "🍾", "⚡", "🕊", "🕊️", "🥳",
    "😊", "🥰", "💖",
})
_NEGATIVE = frozenset({
    "👎", "🤬", "🤡", "💔", "😭", "😢", "😡", "💩", "🤮", "😤",
    "😠", "😒", "💀", "🙄", "🖕", "☠️", "☠", "😾", "😑", "😞",
    "😔", "😩", "😫",
})

_SCORE_CUTOFF = 0.15


def _polarity(emoji: str) -> str:
    """Return positive, negative, or other for one reaction emoji."""
    if emoji in _POSITIVE:
        return "positive"
    if emoji in _NEGATIVE:
        return "negative"
    stripped = emoji.replace("\ufe0f", "")
    if stripped in _POSITIVE:
        return "positive"
    if stripped in _NEGATIVE:
        return "negative"
    return "other"


def _as_counts(raw: Any) -> dict[str, int]:
    """Normalize a JSONB reaction map to positive integer counts."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict):
        return {}
    counts: dict[str, int] = {}
    for key, value in raw.items():
        if not key:
            continue
        try:
            count = int(value)
        except (TypeError, ValueError):
            continue
        if count > 0:
            counts[str(key)] = count
    return counts


@dataclass(frozen=True)
class ReactionScore:
    """Advisory reaction reading. ``valence`` is none when nobody reacted."""

    valence: str
    score: float
    total: int
    positive: int
    negative: int
    other: int
    top: list[dict[str, Any]]

    def as_columns(self) -> dict[str, Any]:
        """Column values for ``sentiment_results_b``."""
        return {
            "reaction_valence": self.valence,
            "reaction_score": self.score,
            "reaction_total": self.total,
            "reaction_positive": self.positive,
            "reaction_negative": self.negative,
            "reaction_other": self.other,
            "reaction_top": self.top,
        }


def score_reactions(raw: Any, top_n: int = 5) -> ReactionScore:
    """Score a post's reaction bar.

    Score is (positive - negative) / (positive + negative), in [-1, 1].
    Emoji with no polarity mapping are ``other`` and stay out of that ratio.
    """
    counts = _as_counts(raw)
    positive = negative = other = 0
    ranked: list[tuple[str, int, str]] = []
    for emoji, count in counts.items():
        polarity = _polarity(emoji)
        if polarity == "positive":
            positive += count
        elif polarity == "negative":
            negative += count
        else:
            other += count
        if emoji.replace("?", "").replace("\ufffd", "").strip():
            ranked.append((emoji, count, polarity))

    total = positive + negative + other
    if total == 0:
        return ReactionScore("none", 0.0, 0, 0, 0, 0, [])

    directed = positive + negative
    score = 0.0 if directed == 0 else (positive - negative) / directed
    if directed == 0:
        valence = "neutral"
    elif score >= _SCORE_CUTOFF:
        valence = "positive"
    elif score <= -_SCORE_CUTOFF:
        valence = "negative"
    else:
        valence = "neutral"

    ranked.sort(key=lambda item: item[1], reverse=True)
    top = [
        {"emoji": emoji, "count": count, "polarity": polarity}
        for emoji, count, polarity in ranked[:top_n]
    ]
    return ReactionScore(
        valence=valence,
        score=round(score, 3),
        total=total,
        positive=positive,
        negative=negative,
        other=other,
        top=top,
    )
