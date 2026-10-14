"""Component B — Model 3: Zero-Shot Stance Detection via Natural Language Inference.

Uses ``valhalla/distilbart-mnli-12-3`` to classify the stance of a post
towards defence/space policy topics via hypothesis entailment.

For each post, the model evaluates:
    Premise:  <post text>
    Hypothesis: "This text expresses support for {topic}."
    Hypothesis: "This text expresses opposition to {topic}."

The stance is resolved as follows:
    - If max(entailment) ≥ 0.60 → "supportive" or "against"
    - If both below 0.60 but neutral-like → "neutral"
    - Otherwise → "unclear"

The 0.60 threshold is mandated by the architecture spec to prevent
overconfident stance assignments on ambiguous social media text.

Usage (standalone)::

    from sentiment_b.stance import StanceDetector
    sd = StanceDetector()
    result = sd.predict("ISRO's budget should be doubled", topic="space funding")
    # => StanceResult(stance='supportive', confidence=0.82, ...)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger("sentiment_b.stance")

MODEL_ID = "valhalla/distilbart-mnli-12-3"

# Minimum entailment confidence to assign a directional stance
STANCE_THRESHOLD = 0.60

# Default policy topics derived from the channel topic_tags in channels.yaml.
# The pipeline injects per-channel topics when available; these are fallbacks.
DEFAULT_TOPICS = [
    "Indian space programme and ISRO missions",
    "defence technology and military modernisation",
    "government science and technology policy",
]


@dataclass(frozen=True)
class StanceResult:
    """Immutable result from the zero-shot stance detector."""

    stance: str          # "supportive" | "against" | "neutral" | "unclear"
    confidence: float    # entailment probability for the winning hypothesis (0.0–1.0)
    topic_evaluated: str # the policy topic the stance was assessed against


class StanceDetector:
    """Lazy-loading zero-shot stance detector using NLI entailment.

    Loads model weights on first call to :meth:`predict` and caches them.
    Callers should call :meth:`unload` between models in the sequential
    pipeline to honour the 4 GB VRAM budget.
    """

    def __init__(self, device: str | None = None) -> None:
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = None
        self._model = None

    # ── Lifecycle ─────────────────────────────────────────────────────────
    def _load(self) -> None:
        if self._model is not None:
            return
        logger.info("Loading stance model: %s → %s", MODEL_ID, self._device)
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID, local_files_only=True
        ).to(self._device)
        self._model.eval()
        logger.info("Stance model loaded successfully.")

    def unload(self) -> None:
        """Release model weights and free GPU memory."""
        if self._model is not None:
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Stance model unloaded, GPU cache cleared.")

    # ── NLI Entailment Helper ─────────────────────────────────────────────
    @torch.inference_mode()
    def _nli_entailment(self, premise: str, hypothesis: str) -> float:
        """Return entailment probability for a premise-hypothesis pair.

        DistilBART-MNLI outputs 3 classes: [contradiction, neutral, entailment].
        We return the entailment probability (index 2).
        """
        self._load()

        inputs = self._tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        ).to(self._device)

        outputs = self._model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1).squeeze().cpu().tolist()

        # Index 2 = entailment
        return probs[2]

    # ── Inference ─────────────────────────────────────────────────────────
    def predict(
        self,
        text: str,
        topic: str | None = None,
        channel_topics: list[str] | None = None,
    ) -> StanceResult:
        """Detect the stance of a post toward a policy topic.

        The method picks the best topic to evaluate against:
        1. Explicit ``topic`` argument (highest priority).
        2. First item from ``channel_topics`` (from channels.yaml topic_tags).
        3. Falls back to DEFAULT_TOPICS[0].

        Args:
            text: Raw post text.
            topic: Explicit policy topic to evaluate stance against.
            channel_topics: List of topic tags from the post's channel config.

        Returns:
            StanceResult with stance label, confidence, and evaluated topic.
        """
        self._load()

        if not text or not text.strip():
            return StanceResult(
                stance="neutral",
                confidence=0.0,
                topic_evaluated="none",
            )

        # Resolve the evaluation topic
        eval_topic = topic
        if not eval_topic and channel_topics:
            # Build a natural-language topic phrase from channel tags
            eval_topic = " and ".join(channel_topics[:3])
        if not eval_topic:
            eval_topic = DEFAULT_TOPICS[0]

        # Evaluate support hypothesis
        support_hypothesis = f"This text expresses support for {eval_topic}."
        oppose_hypothesis = f"This text expresses opposition to {eval_topic}."

        support_score = self._nli_entailment(text, support_hypothesis)
        oppose_score = self._nli_entailment(text, oppose_hypothesis)

        # Decision logic with 0.60 threshold
        if support_score >= STANCE_THRESHOLD and support_score > oppose_score:
            stance = "supportive"
            confidence = support_score
        elif oppose_score >= STANCE_THRESHOLD and oppose_score > support_score:
            stance = "against"
            confidence = oppose_score
        elif max(support_score, oppose_score) < 0.30:
            # Very low signal in both directions → genuinely neutral
            stance = "neutral"
            confidence = 1.0 - max(support_score, oppose_score)
        else:
            # Some signal but below threshold → unclear
            stance = "unclear"
            confidence = max(support_score, oppose_score)

        return StanceResult(
            stance=stance,
            confidence=round(confidence, 4),
            topic_evaluated=eval_topic,
        )
