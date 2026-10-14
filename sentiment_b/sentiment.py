"""Component B — Model 1: Multilingual 3-class Sentiment Classification.

Uses ``cardiffnlp/twitter-xlm-roberta-base-sentiment`` to produce a valence
label (positive / negative / neutral) with a calibrated confidence score.

Handles English and code-mixed Hinglish text transparently via the XLM-RoBERTa
multilingual backbone.

Usage (standalone)::

    from sentiment_b.sentiment import SentimentClassifier
    clf = SentimentClassifier()
    result = clf.predict("ISRO ne shandar launch kiya! 🚀")
    # => {"valence": "positive", "confidence": 0.93}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger("sentiment_b.sentiment")

MODEL_ID = "cardiffnlp/twitter-xlm-roberta-base-sentiment"

# The model outputs 3 classes in this fixed order:
LABEL_MAP = {0: "negative", 1: "neutral", 2: "positive"}


@dataclass(frozen=True)
class SentimentResult:
    """Immutable result from the 3-class sentiment classifier."""

    valence: str          # "positive" | "negative" | "neutral"
    confidence: float     # softmax probability of the dominant class (0.0–1.0)
    score_positive: float
    score_negative: float
    score_neutral: float


class SentimentClassifier:
    """Lazy-loading multilingual sentiment classifier.

    Loads model weights on first call to :meth:`predict` and caches them for
    subsequent invocations.  Callers can explicitly call :meth:`unload` to
    release GPU/RAM before passing the baton to the next model in the
    sequential pipeline.
    """

    def __init__(self, device: str | None = None) -> None:
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._tokenizer = None
        self._model = None

    # ── Lifecycle ─────────────────────────────────────────────────────────
    def _load(self) -> None:
        """Load tokenizer and model weights into memory (lazy, one-shot)."""
        if self._model is not None:
            return
        logger.info("Loading sentiment model: %s → %s", MODEL_ID, self._device)
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_ID, local_files_only=True
        ).to(self._device)
        self._model.eval()
        logger.info("Sentiment model loaded successfully.")

    def unload(self) -> None:
        """Release model weights and free GPU memory."""
        if self._model is not None:
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("Sentiment model unloaded, GPU cache cleared.")

    # ── Inference ─────────────────────────────────────────────────────────
    @torch.inference_mode()
    def predict(self, text: str) -> SentimentResult:
        """Run sentiment classification on a single text string.

        Args:
            text: Raw post text (English, Hindi, or code-mixed Hinglish).

        Returns:
            SentimentResult with valence, confidence, and per-class scores.
        """
        self._load()

        if not text or not text.strip():
            return SentimentResult(
                valence="neutral",
                confidence=1.0,
                score_positive=0.0,
                score_negative=0.0,
                score_neutral=1.0,
            )

        # Truncate to model max length (512 tokens) to prevent OOM on long posts
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        ).to(self._device)

        outputs = self._model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1).squeeze().cpu().tolist()

        # Map index → label
        score_negative, score_neutral, score_positive = probs[0], probs[1], probs[2]
        dominant_idx = max(range(3), key=lambda i: probs[i])

        return SentimentResult(
            valence=LABEL_MAP[dominant_idx],
            confidence=round(probs[dominant_idx], 4),
            score_positive=round(score_positive, 4),
            score_negative=round(score_negative, 4),
            score_neutral=round(score_neutral, 4),
        )

    @torch.inference_mode()
    def predict_batch(self, texts: list[str]) -> list[SentimentResult]:
        """Classify a batch of texts in a single forward pass.

        Args:
            texts: List of raw post texts.

        Returns:
            List of SentimentResult, one per input text.
        """
        self._load()

        # Handle empty/blank texts by marking them and filtering
        results: list[SentimentResult | None] = [None] * len(texts)
        valid_indices = []
        valid_texts = []

        for i, t in enumerate(texts):
            if not t or not t.strip():
                results[i] = SentimentResult(
                    valence="neutral",
                    confidence=1.0,
                    score_positive=0.0,
                    score_negative=0.0,
                    score_neutral=1.0,
                )
            else:
                valid_indices.append(i)
                valid_texts.append(t)

        if valid_texts:
            inputs = self._tokenizer(
                valid_texts,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            ).to(self._device)

            outputs = self._model(**inputs)
            all_probs = torch.softmax(outputs.logits, dim=-1).cpu().tolist()

            for idx, probs in zip(valid_indices, all_probs):
                score_negative, score_neutral, score_positive = probs[0], probs[1], probs[2]
                dominant = max(range(3), key=lambda i: probs[i])
                results[idx] = SentimentResult(
                    valence=LABEL_MAP[dominant],
                    confidence=round(probs[dominant], 4),
                    score_positive=round(score_positive, 4),
                    score_negative=round(score_negative, 4),
                    score_neutral=round(score_neutral, 4),
                )

        return results  # type: ignore[return-value]
