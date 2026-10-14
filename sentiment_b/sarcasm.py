"""Component B — Sarcasm Heuristic: Valence-Emoji Incongruity Detection.

A lightweight, rule-based advisory heuristic that flags potential sarcasm by
detecting incongruity between the sentiment valence (from Model 1) and the
emoji/punctuation signals present in the text.

**Key constraint:** The sarcasm flag is advisory only.  It NEVER inverts the
base sentiment valence.  It simply sets ``sarcasm_flag = True`` as an
uncertainty signal for downstream consumers.

Detection rules:
    1. Positive valence + negative emoji clusters (😢😡💀🤡🙄) → flag
    2. Negative valence + positive emoji clusters (😂🤣😍🥳👏🎉🔥) → flag
    3. Excessive punctuation incongruity (e.g., "Great work!!!" with negative valence)
    4. Explicit sarcasm markers ("/s", "sarcasm", "yeah right")

Usage::

    from sentiment_b.sarcasm import SarcasmDetector
    detector = SarcasmDetector()
    flag = detector.check("Great job government 🤡🤡🤡", valence="positive")
    # => True (positive valence contradicted by 🤡 cluster)
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("sentiment_b.sarcasm")

# ── Emoji Clusters ────────────────────────────────────────────────────────
# These are unicode codepoint ranges and individual emojis commonly associated
# with positive or negative sentiment in Indian social media discourse.

POSITIVE_EMOJIS = frozenset([
    "😂", "🤣", "😍", "🥳", "👏", "🎉", "🔥", "❤️", "💯", "🙌",
    "😊", "😁", "🥰", "👍", "✨", "💪", "🎊", "😎", "🤩", "💖",
    "❤", "♥", "👌", "🫡", "🇮🇳",
])

NEGATIVE_EMOJIS = frozenset([
    "😢", "😡", "💀", "🤡", "🙄", "😤", "😠", "👎", "💩", "🤮",
    "😒", "😑", "🤦", "😞", "😔", "😩", "😫", "☠️", "🤬", "😾",
    "☠", "🤦‍♂️", "🤦‍♀️",
])

# Explicit textual sarcasm markers (case-insensitive)
SARCASM_MARKERS = re.compile(
    r"(?i)\b(?:sarcasm|/s|yeah\s+right|oh\s+really|sure\s+sure|wah\s+wah"
    r"|kya\s+baat\s+hai|haan\s+haan)\b"
)


def _count_emojis(text: str, emoji_set: frozenset[str]) -> int:
    """Count occurrences of emojis from a given set in the text."""
    return sum(1 for char in text if char in emoji_set)


def _has_excessive_punctuation(text: str) -> bool:
    """Check for excessive exclamation/question marks (≥3 in a row)."""
    return bool(re.search(r"[!?]{3,}", text))


class SarcasmDetector:
    """Advisory sarcasm heuristic — never inverts valence.

    This is a stateless, zero-cost rule engine (no ML model loaded).
    """

    def check(self, text: str, valence: str) -> bool:
        """Evaluate whether a text exhibits sarcasm signals.

        Args:
            text: Raw post text.
            valence: Predicted valence from Model 1 ("positive", "negative", "neutral").

        Returns:
            True if sarcasm is suspected (advisory flag), False otherwise.
        """
        if not text or not text.strip():
            return False

        # Rule 1: Explicit sarcasm markers always flag
        if SARCASM_MARKERS.search(text):
            logger.debug("Sarcasm marker detected in text.")
            return True

        positive_count = _count_emojis(text, POSITIVE_EMOJIS)
        negative_count = _count_emojis(text, NEGATIVE_EMOJIS)

        # Rule 2: Positive valence + negative emoji cluster (≥2 negative emojis)
        if valence == "positive" and negative_count >= 2:
            logger.debug(
                "Valence-emoji incongruity: positive valence + %d negative emojis.",
                negative_count,
            )
            return True

        # Rule 3: Negative valence + positive emoji cluster (≥2 positive emojis)
        if valence == "negative" and positive_count >= 2:
            logger.debug(
                "Valence-emoji incongruity: negative valence + %d positive emojis.",
                positive_count,
            )
            return True

        # Rule 4: Excessive punctuation with counter-valence emoji
        if _has_excessive_punctuation(text):
            if valence == "positive" and negative_count >= 1:
                return True
            if valence == "negative" and positive_count >= 1:
                return True

        return False
